#!/usr/bin/env python3
"""The project-layer policy contract (PLAN-0019 W1, VELDO-0016): the registries and pure
predicates that say what may activate effective policy, what the governed runner owes in
place of the process bans it retires, how architecture loading is allowed to answer, and
which design clauses bound the whole layer.

WHAT THIS MODULE IS. A contract organ in the exact sense arch.py, decision.py and
release_contract.py are: registries a suite can enumerate, predicates that REFUSE by name,
and nothing that runs. It owns no state, opens no connection, starts no process, thread or
timer, and imports the standard library only (the stdlib_only_enforcement pattern and R35:
an enforcement entry may never need the execution environment to decide eligibility).

WHAT IT IS NOT. It activates nothing. A registry entry, a draft decision record, a source
landing and a capability label are each exactly as much authority as a comment: none. The
activation predicates here answer "may this record activate this boundary", and the
answer is enforced by the consumers that ask (later packages), never by this file.

THE LOADING REGISTRY (AC3). Every public entry point through which the engine reads the
architecture contract is enumerated in LOADER_ADAPTERS, with the shape its refusal takes.
The suite derives the set of modules that actually call the loader from the source and
compares it with this registry in both directions, and then drives every registered adapter
across every contract state (absent, unreadable, malformed, invalid, valid) under both
settings of the required flag, so an adapter that maps a broken contract to "no contract"
is found by the product, not remembered by a person.
"""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCHEMA = "veldo.policy_contract/v1"

# ---------------------------------------------------------------------------------------------
# AC3: the architecture loading registry.
# ---------------------------------------------------------------------------------------------

# The five contract STATES a fixture can put the artifact in. `absent` is nothing at the path;
# `unreadable` is something at the path that cannot be read as a file (a directory, a dangling
# symlink, a file the reader may not open); `malformed` is a readable file outside the contract
# subset or not a mapping; `invalid` parses but fails structural validation; `valid` is a
# contract check_arch accepts. These are the fixture's vocabulary; the LOADER's vocabulary is
# validate_checks.CONTRACT_KINDS, and LOADER_KIND_FOR_STATE is the join between them.
LOADER_STATES = ("absent", "unreadable", "malformed", "invalid", "valid")

# What the loader must report for each fixture state, by (state, required). Optional absence is
# the ONE state that stands down; required absence refuses; every present-but-not-valid state
# refuses whatever the flag says, because the flag is about absence and presence is never
# optional.
LOADER_KIND_FOR_STATE = {
    ("absent", False): ("absent", "optional_absence"),
    ("absent", True): ("absent", "required_absence"),
    ("unreadable", False): ("invalid", "unreadable"),
    ("unreadable", True): ("invalid", "unreadable"),
    ("malformed", False): ("invalid", "parse_failure"),
    ("malformed", True): ("invalid", "parse_failure"),
    ("invalid", False): ("invalid", "invalid_structure"),
    ("invalid", True): ("invalid", "invalid_structure"),
    ("valid", False): ("valid", "valid"),
    ("valid", True): ("valid", "valid"),
}

# `own_presence_guard` marks an adapter whose delegation boundary asks the kind question of the
# artifact BEFORE handing the read to the loader (metrics_read_closure.delegated refuses a
# directory or a present file that declares no area by itself). Such an adapter refuses an
# unreadable or malformed contract even when the loader is wrong, so a loader mutant on those
# states cannot turn its row red; the required-absence mutant still can, because absence is the
# one state its boundary cannot see. The suite excludes exactly these adapters from the
# every-row-red demand for those two mutants and says why.

# The two OUTCOMES a consumer can show a fixture: it REFUSED (by whatever shape its row below
# declares) or it PROCEEDED (stood down as adoption safe, or enforced a valid contract; the
# consumer's own contract says which, and the loader row pins the distinction exactly).
REFUSED, PROCEEDED = "refused", "proceeded"


def expected_loader_outcome(state, required):
    """The outcome every registered adapter owes a fixture in `state` under `required`: a
    valid contract proceeds, an optional absence proceeds (adoption safe), and everything
    else refuses. This is the statement the product test compares each adapter against, so
    the expectation is written once here and not once per row."""
    if state not in LOADER_STATES:
        raise ValueError("unknown contract state %r (known: %s)" % (state, LOADER_STATES))
    if state == "valid":
        return PROCEEDED
    if state == "absent":
        return REFUSED if required else PROCEEDED
    return REFUSED


# EVERY PUBLIC ENTRY THROUGH WHICH THE ENGINE READS THE CONTRACT, with the module that owns it,
# whether it takes the required flag itself (the others read the repository's policy flag through
# the loader), and the SHAPE its refusal takes, so a consumer of that entry knows what to look
# for. `via` names the engine call the entry reaches the loader through when it is not the loader
# itself. A module that calls the loader and is not here is a registry defect the suite reports;
# an entry here whose module does not call the loader is the same defect in the other direction.
LOADER_ADAPTERS = (
    {"id": "validate_checks.load_contract_state", "module": ".veldo/validate_checks.py",
     "entry": "load_contract_state", "takes_required": True, "via": None,
     "refusal": "ContractLoad with refused True and every problem by name"},
    {"id": "validate_checks.load_repo_contract", "module": ".veldo/validate_checks.py",
     "entry": "load_repo_contract", "takes_required": True, "via": "load_contract_state",
     "refusal": "raises ContractRefused carrying the ContractLoad"},
    {"id": "validate_checks.check_arch", "module": ".veldo/validate_checks.py",
     "entry": "check_arch", "takes_required": True, "via": "load_contract_state",
     "refusal": "a nonzero error count, one fail line per problem"},
    {"id": "validate_checks.placement_gate_problems", "module": ".veldo/validate_checks.py",
     "entry": "placement_gate_problems", "takes_required": False, "via": "load_repo_contract",
     "refusal": "a problem naming the architecture contract refusal"},
    {"id": "validate_checks.placement_gate_ok", "module": ".veldo/validate_checks.py",
     "entry": "placement_gate_ok", "takes_required": False, "via": "placement_gate_problems",
     "refusal": "False"},
    {"id": "validate_checks.check_placement", "module": ".veldo/validate_checks.py",
     "entry": "check_placement", "takes_required": False, "via": "load_repo_contract",
     "refusal": "a nonzero error count naming the refusal (the declaration cannot be validated)"},
    {"id": "validate_checks.check_observability", "module": ".veldo/validate_checks.py",
     "entry": "check_observability", "takes_required": False, "via": "load_repo_contract",
     "refusal": "a nonzero error count naming the refusal"},
    {"id": "validate_checks.check_ready", "module": ".veldo/validate_checks.py",
     "entry": "check_ready", "takes_required": False, "via": "load_repo_contract",
     "refusal": "a nonzero error count naming the refusal at the ready transition"},
    {"id": "validate_checks.check_shape_review", "module": ".veldo/validate_checks.py",
     "entry": "check_shape_review", "takes_required": False, "via": "load_repo_contract",
     "refusal": "a nonzero error count naming the refusal"},
    {"id": "frontier.claimable", "module": ".veldo/frontier.py",
     "entry": "claimable", "takes_required": False, "via": "load_repo_contract",
     "refusal": "no offers of any kind; frontier.contract_refusal names why and the CLI prints it"},
    {"id": "plan.cmd_run_check", "module": ".veldo/plan.py",
     "entry": "cmd_run_check", "takes_required": False, "via": "placement_gate_problems",
     "refusal": "REFUSED with the contract refusal among its reasons, exit 1"},
    {"id": "shape_gate.run", "module": ".veldo/shape_gate.py",
     "entry": "run", "takes_required": False, "via": "load_contract_state",
     "refusal": "(standdown False, problems naming the refusal, notes), never the adoption-safe stand-down"},
    {"id": "observability._cli", "module": ".veldo/observability.py",
     "entry": "_cli", "takes_required": False, "via": "load_repo_contract",
     "refusal": "exit 1 naming the refusal"},
    {"id": "intent_corpus.open_corpus", "module": ".veldo/intent_corpus.py",
     "entry": "open_corpus", "takes_required": False, "via": "load_repo_contract",
     "refusal": "the corpus opens (its own reads are its own) and every area join, area_of and trace, "
                "raises IntentCorpusError naming the refusal; stats() says contract_refused"},
    {"id": "entropy.entropy_report", "module": ".veldo/entropy.py",
     "entry": "entropy_report", "takes_required": False, "via": "load_repo_contract",
     "refusal": "raises ContractRefused; the dashboard's delegation boundary names it as the cause"},
    {"id": "cost_to_change.repo_report", "module": ".veldo/cost_to_change.py",
     "entry": "repo_report", "takes_required": False, "via": "load_repo_contract",
     "refusal": "a report with refused True and the reason, never the stand-down shape"},
    {"id": "metrics_shape_readers._read_contract", "module": ".veldo/metrics_shape_readers.py",
     "entry": "_read_contract", "takes_required": False, "via": "load_repo_contract",
     "own_presence_guard": True,
     "refusal": "the contract problem named, with the delegated cause"},
)

# The calls whose presence in a module's source makes it a loader caller: the two loader entry
# points and the two pure placement predicates that embed the loader. A module reaching the
# contract only through a registered adapter's RESULT (the dashboard reading an entropy report)
# is a consumer of that adapter, not of the loader, and is not a caller here.
_LOADER_CALL = re.compile(r"\b(?:load_repo_contract|load_contract_state|"
                          r"placement_gate_problems|placement_gate_ok)\(")

# Modules the scan finds that are NOT adapters: validate.py re-exports the names by assignment
# and never calls them, and contract_loader.py DEFINES the loader; each is listed here to make the
# exclusion an explicit decision the suite can see rather than a silent regex accident.
LOADER_SCAN_EXCLUDED = (".veldo/validate.py", ".veldo/contract_loader.py")


def guarded_adapters():
    """The adapter ids whose boundary guards presence itself (see own_presence_guard)."""
    return sorted(a["id"] for a in LOADER_ADAPTERS if a.get("own_presence_guard"))


def loader_adapter_modules():
    """The set of engine modules the registry says read the contract."""
    return sorted({a["module"] for a in LOADER_ADAPTERS})


def loader_callers(root=None):
    """The set of engine modules whose SOURCE calls the loader or a placement predicate,
    derived from the tree under root, never remembered. Comments and docstrings that mention a
    call are counted: a mention with an open parenthesis is either a call or a doc that shows
    one, and a doc that shows a call it does not make is itself worth a registry look."""
    base = Path(root) if root else ROOT
    out = set()
    for p in sorted((base / ".veldo").glob("*.py")):
        rel = ".veldo/" + p.name
        if rel in LOADER_SCAN_EXCLUDED:
            continue
        try:
            text = p.read_text()
        except OSError:
            continue
        if _LOADER_CALL.search(text):
            out.add(rel)
    return sorted(out)


def loader_registry_problems(root=None):
    """The registry compared with the source in BOTH directions: a module that calls the loader
    and is registered under no adapter, and an adapter whose module does not call the loader.
    Empty iff the registry is exactly the set of callers. Also refuses a registry with a
    duplicate id or an entry missing a field, so a half-written row cannot pass as coverage."""
    problems = []
    fields = ("id", "module", "entry", "takes_required", "via", "refusal")
    ids = []
    for a in LOADER_ADAPTERS:
        missing = [f for f in fields if f not in a]
        if missing:
            problems.append("adapter %r is missing %s" % (a.get("id"), ", ".join(missing)))
        ids.append(a.get("id"))
    for i in sorted(set(ids)):
        if ids.count(i) > 1:
            problems.append("duplicate adapter id %r" % i)
    registered = set(loader_adapter_modules())
    callers = set(loader_callers(root))
    for m in sorted(callers - registered):
        problems.append("%s calls the architecture loader and no adapter registers it: a "
                        "consumer the product test cannot reach" % m)
    for m in sorted(registered - callers):
        problems.append("%s is registered as a loader adapter and its source calls no loader "
                        "entry: a registry row about nothing" % m)
    return problems


def loader_matrix():
    """The full product the suite drives: every adapter id crossed with every state and both
    settings of the required flag, as (adapter_id, state, required, expected_outcome) rows.
    Written as a function so the suite and a reader ask the contract for the rows instead of
    each composing their own product."""
    rows = []
    for a in LOADER_ADAPTERS:
        for state in LOADER_STATES:
            for required in (False, True):
                rows.append((a["id"], state, required, expected_loader_outcome(state, required)))
    return rows


# ---------------------------------------------------------------------------------------------
# AC1: decision-to-policy activation.
# ---------------------------------------------------------------------------------------------

# THE GOVERNED POLICY BOUNDARIES, each with the ONE decision record that may activate it, the
# record VERSION this registry was written against, and the option whose choice activates the
# boundary. The boundaries are the ones R03 names (repository placement, orchestrator process
# ownership, operational authority and persistence, LangGraph's replaceable execution boundary,
# review and completion semantics) plus the worker repository access rule of D4, so every one of
# the four open PLAN-0019 choices is on this table: D1 and D2 under operational_persistence, D3
# inside process_lifetime (host profiles plural, C12), D4 under worker_repository_access.
#
# A ROW HERE IS NOT ACTIVATION. It says which record would have to be DECIDED, at which version,
# choosing which option, before a consumer may treat the boundary as effective. Every record named
# below is a draft on the day this table was written, and activation_authority refuses each of
# them by name until Dmitry decides it on the record with its adversarial reviews bound.
POLICY_BOUNDARIES = (
    {"id": "repository_placement", "clause": "R03",
     "decision": "VELDO-DEC-0003", "version": 1,
     "activating_option": "same-repository-canonical-engine",
     "effect": "the project layer lives in canonical engine/ of this repository"},
    {"id": "process_lifetime", "clause": "R03, R43, R44",
     "decision": "VELDO-DEC-0004", "version": 1,
     "activating_option": "governed-service-and-runner",
     "architecture_version": 2,
     "effect": "no_detached_processes and agent-mediated launch are replaced for the governed "
               "project runner by the R43/R44 obligations (D3: host profiles plural, C12)"},
    {"id": "operational_persistence", "clause": "R03, R21",
     "decision": "VELDO-DEC-0005", "version": 1,
     "activating_option": "sqlite-authority-signed-git-replica",
     "effect": "one SQLite authority per repository with a signed Git replica; acknowledgement "
               "only after off-host publication (D1, D2)"},
    {"id": "replaceable_execution", "clause": "R03, R21, R35",
     "decision": "VELDO-DEC-0006", "version": 1,
     "activating_option": "langgraph-adapter-veldo-owned-state",
     "effect": "LangGraph runs the graph behind a replaceable adapter over state Veldo owns"},
    {"id": "review_and_completion", "clause": "R03, R46, R50",
     "decision": "VELDO-DEC-0007", "version": 1,
     "activating_option": "gate-and-owner-authorize-review-informs",
     "effect": "a passing review informs; the gate, the receipt and the owner decide completion"},
    {"id": "worker_repository_access", "clause": "R44, R45, C13",
     "decision": "VELDO-DEC-0008", "version": 1,
     "activating_option": "isolated-clones-contract-named-attachments",
     "effect": "isolated per-run clones; other repositories only through contract-named, "
               "commit-pinned, read-only attachments (D4)"},
)

DECISION_SCHEMA = "veldo.decision/v1"

# THE MACHINE ACTORS THAT ARE NOT A PERSON, mirrored from authorization.MACHINE_ACTORS (the human
# authorization refusal of the safety core) and bound to it by the suite so the two sets cannot
# drift. A decided record whose decider normalizes to one of these activates nothing.
MACHINE_ACTORS = frozenset({
    "veldo-executor", "veldo-responder", "executor", "responder", "machine",
    "agent", "bot", "ava", "automation",
    "service", "service_account", "service-account",
})

# The refusal classes activation_authority can answer with, one word each, so a consumer's
# diagnostic and a suite row name the class rather than parse prose.
ACTIVATION_REFUSALS = ("unknown_boundary", "missing", "malformed", "wrong_record", "draft",
                       "superseded", "stale", "wrong_option", "undecided_by_a_person",
                       "under_reviewed")


def boundary(boundary_id):
    """The registry row for boundary_id, or None."""
    for b in POLICY_BOUNDARIES:
        if b["id"] == boundary_id:
            return b
    return None


def activation_authority(boundary_id, record, bound_supporting_reviews, required_reviews, record_problems=()):
    """(accepted, refusal_class, reason): may `record` activate `boundary_id`? PURE over its
    arguments; the caller supplies the parsed veldo.decision/v1 record (None when none resolves),
    the number of structurally valid, bound, SUPPORTING adversarial reviews the record carries
    (decision_review._valid_bound_reviews_by_decision), the number its risk tier requires
    (decision_review.required_reviews_for) and the problems the canonical record validator
    (decision.validate_record) reported for it, which activation_report computes. Accepts ONLY a
    record that validates, is the registered one, at the registered version, decided by a named
    PERSON (a decider that normalizes to a machine actor is no decider), with a decided_at,
    choosing the activating option, with enough bound reviews. Everything else is refused by
    class and by name: a missing record, a malformed one, a record for another decision, a
    draft, a superseded record, a record whose version moved past the registry (stale: the
    registry must be re-read against the new version, never assumed), a decided record that
    chose a different option, a decided record without a person as decider, and a decided record
    with fewer bound supporting reviews than its tier requires. Draft, superseded and stale are
    refused BEFORE the option is looked at, so a draft that already names the activating option
    in prose is still a draft."""
    b = boundary(boundary_id)
    if b is None:
        return False, "unknown_boundary", "no policy boundary %r is registered" % (boundary_id,)
    if record is None:
        return False, "missing", "decision record %s for boundary %s does not resolve" % (b["decision"], boundary_id)
    if not isinstance(record, dict) or record.get("schema") != DECISION_SCHEMA:
        return False, "malformed", "the record offered for boundary %s is not a %s record" % (boundary_id, DECISION_SCHEMA)
    if record_problems:
        return False, "malformed", ("the record offered for boundary %s fails the decision validator: %s"
                                    % (boundary_id, "; ".join(str(p) for p in record_problems)))
    if record.get("id") != b["decision"]:
        return False, "wrong_record", ("boundary %s is activated by %s, not by %r"
                                       % (boundary_id, b["decision"], record.get("id")))
    status = record.get("status")
    if status == "superseded":
        return False, "superseded", ("%s is superseded%s: a superseded record activates nothing; "
                                     "re-read the registry against its successor"
                                     % (b["decision"], (" by %s" % record.get("superseded_by")) if record.get("superseded_by") else ""))
    if status != "decided":
        return False, "draft", ("%s is %r, not decided: a draft records a supplied direction and "
                                "activates nothing" % (b["decision"], status))
    version = record.get("version")
    if version != b["version"]:
        return False, "stale", ("%s is at version %r and the registry was written against version %d: "
                                "a re-decided record activates nothing until the registry is re-read "
                                "against it" % (b["decision"], version, b["version"]))
    decision = record.get("decision") if isinstance(record.get("decision"), dict) else {}
    decided_by = decision.get("decided_by")
    if not (isinstance(decided_by, str) and decided_by.strip()):
        return False, "undecided_by_a_person", ("%s is decided but names no decider: only a person "
                                                "decides, on the record" % b["decision"])
    if decided_by.strip().lower() in MACHINE_ACTORS:
        return False, "undecided_by_a_person", ("%s names %r as its decider, a machine actor: only a person "
                                                "decides, on the record" % (b["decision"], decided_by))
    decided_at = decision.get("decided_at")
    if not (isinstance(decided_at, str) and decided_at.strip()):
        return False, "undecided_by_a_person", ("%s is decided but carries no decided_at: a decision without "
                                                "a date is not on the record" % b["decision"])
    chosen = decision.get("chosen")
    if chosen != b["activating_option"]:
        return False, "wrong_option", ("%s chose %r; boundary %s is activated only by %r"
                                       % (b["decision"], chosen, boundary_id, b["activating_option"]))
    try:
        have, need = int(bound_supporting_reviews), int(required_reviews)
    except (TypeError, ValueError):
        return False, "under_reviewed", "the bound review count for %s is not a number" % b["decision"]
    if need < 1:
        need = 1  # the floor decision_review.required_reviews_for keeps: a decided record needs one review
    if have < need:
        return False, "under_reviewed", ("%s carries %d bound supporting adversarial review(s); its risk "
                                         "tier requires %d" % (b["decision"], have, need))
    return True, None, ("%s v%d decided by %s choosing %s activates boundary %s"
                        % (b["decision"], b["version"], decided_by, chosen, boundary_id))


def boundary_matrix_problems(records):
    """The registry compared with the decision records in BOTH directions. `records` is the
    list of parsed veldo.decision/v1 records under .veldo/decisions/ (the caller reads them
    through decision.load_record, the one reader). Each record that may activate a boundary
    declares it as `policy_boundary`; the matrix derived from those declarations must equal
    the registry: a registered boundary no record claims, a record claiming an unregistered
    boundary, a registered decision id that resolves to no record, a record claiming a boundary
    the registry assigns to another record, a registered activating option the record does not
    declare, and two records claiming one boundary are each a problem by name."""
    problems = []
    by_id = {}
    claims = {}
    for r in records:
        if not isinstance(r, dict) or r.get("schema") != DECISION_SCHEMA:
            continue
        rid = r.get("id")
        by_id[rid] = r
        pb = r.get("policy_boundary")
        if pb is not None:
            claims.setdefault(pb, []).append(rid)
    registered = {b["id"]: b for b in POLICY_BOUNDARIES}
    ids = [b["id"] for b in POLICY_BOUNDARIES]
    for i in sorted(set(ids)):
        if ids.count(i) > 1:
            problems.append("duplicate boundary id %r in the registry" % i)
    for bid, b in registered.items():
        rec = by_id.get(b["decision"])
        if rec is None:
            problems.append("boundary %s names %s, which resolves to no decision record" % (bid, b["decision"]))
            continue
        if rec.get("policy_boundary") != bid:
            problems.append("boundary %s names %s, but that record claims %r" % (bid, b["decision"], rec.get("policy_boundary")))
        options = {o.get("id") for o in (rec.get("options") or []) if isinstance(o, dict)}
        if b["activating_option"] not in options:
            problems.append("boundary %s is activated by option %r, which %s does not declare (declared: %s)"
                            % (bid, b["activating_option"], b["decision"], sorted(o for o in options if o)))
        if bid not in claims:
            problems.append("boundary %s is registered and no record claims it" % bid)
    for pb, rids in sorted(claims.items()):
        if pb not in registered:
            problems.append("record(s) %s claim boundary %r, which the registry does not know" % (", ".join(sorted(map(str, rids))), pb))
        elif len(rids) > 1:
            problems.append("boundary %s is claimed by %d records: %s" % (pb, len(rids), ", ".join(sorted(map(str, rids)))))
        elif registered[pb]["decision"] != rids[0]:
            problems.append("record %s claims boundary %s, which the registry assigns to %s" % (rids[0], pb, registered[pb]["decision"]))
    return problems


def activation_report(root=None, load_modules=None):
    """The activation state of every registered boundary over THIS repository's records and
    reviews: [{boundary, decision, accepted, refusal, reason}], plus the matrix problems. Wires
    decision.load_record for the records and decision_review's bound-review count and tier
    requirement, each loaded by path from the engine beside this file (the way the sibling
    organs load one another), with a silent failure reporter: this is a READ, never a gate pass,
    and the gate's own decision checks report the malformed records. Nothing here activates
    anything; it says what would be refused and why."""
    import importlib.util
    base = Path(root) if root else ROOT
    here = Path(__file__).resolve().parent

    def _load(name, rel):
        spec = importlib.util.spec_from_file_location("veldo_policy_contract_" + name, here / rel)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    load_modules = load_modules or _load
    V = load_modules("validate", "validate.py")
    D = load_modules("decision", "decision.py")
    DR = load_modules("decision_review", "decision_review.py")
    quiet = lambda _name, _msg: 1
    ddir = D.default_decisions_dir(base)
    records, problems_by_id = [], {}
    if Path(ddir).is_dir():
        for p in sorted(Path(ddir).glob("*.yaml")):
            try:
                rec = D.load_record(p, V.parse_yamlish)
            except Exception as e:
                problems_by_id.setdefault(p.stem, []).append(str(e))
                continue
            records.append(rec)
            # THE CANONICAL VALIDATOR JUDGES THE RECORD, never this module: a decided record that
            # decision.validate_record refuses (no decided_at, a chosen option that does not resolve,
            # a smuggled decision block) is malformed here whatever else it says.
            found = []
            D.validate_record(rec, base, p, lambda _n, m: (found.append(m), 1)[1])
            if found and isinstance(rec, dict):
                problems_by_id[rec.get("id")] = found
    counts, _seen, review_errs = DR._valid_bound_reviews_by_decision(
        DR.default_reviews_dir(base), ddir, base, V.parse_yamlish, quiet, D.load_record)
    if review_errs:
        # A REVIEW SET WITH A PROBLEM VOUCHES FOR NOTHING. The reader counts a review before it reports
        # that a second file carries the same id, so two copies of one supporting review would count
        # as two; an error anywhere in the set zeroes every count until the set is repaired.
        counts = {}
    policy_path = base / ".veldo" / "policy.yaml"
    by_id = {r.get("id"): r for r in records if isinstance(r, dict)}
    rows = []
    for b in POLICY_BOUNDARIES:
        rec = by_id.get(b["decision"])
        need = DR.required_reviews_for(rec.get("risk") if isinstance(rec, dict) else None, policy_path)
        accepted, refusal, reason = activation_authority(
            b["id"], rec, counts.get(b["decision"], 0), need, record_problems=problems_by_id.get(b["decision"], ()))
        if review_errs and refusal == "under_reviewed":
            reason += " (the review set carries %d problem(s), so no review counts until it is repaired)" % review_errs
        rows.append({"boundary": b["id"], "decision": b["decision"], "accepted": accepted,
                     "refusal": refusal, "reason": reason})
    return {"schema": SCHEMA, "boundaries": rows, "matrix_problems": boundary_matrix_problems(records),
            "review_set_problems": review_errs, "record_problems": problems_by_id,
            "activated": sorted(r["boundary"] for r in rows if r["accepted"])}


# ---------------------------------------------------------------------------------------------
# AC2: the governed runner's obligations, in place of the lexical ban.
# ---------------------------------------------------------------------------------------------

# THE FIVE OBLIGATION GROUPS are the keys of VELDO-DEC-0004's replacement_obligations block, so
# the registry and the record are compared in both directions: every group has an obligation here,
# every obligation belongs to a group the record names.
OBLIGATION_GROUPS = ("containment", "resource_limits", "lifecycle", "liveness_and_stop", "retirement")

# THE VERSIONED POLICY DEFAULTS R44 names, in one place, so a test and a runner read one number.
HEARTBEAT_SECONDS = 10
LIVENESS_DEADLINE_SECONDS = 30
STOP_TERMINATE_AFTER_SECONDS = 10
STOP_KILL_AFTER_SECONDS = 5
LEADERSHIP_FENCE_SECONDS = 2

# THE PROOFS RETIREMENT NEEDS, every one of them: capacity is released only when containment is
# proven EMPTY and the outcome, the accounting and the resource cleanup are durably recorded (R43,
# R44, VELDO-DEC-0004 retirement). Silence is not proof of death; an unproven slot is quarantined.
RETIREMENT_PROOFS = ("containment_empty", "outcome_recorded", "accounting_recorded", "cleanup_done")

# EVERY R43/R44 OBLIGATION the governed runner owes, each with its group, its clause and a
# `test_registration` slot a later package fills with the real failure test that qualifies it
# (Package B implements, Package D qualifies engines). A slot that is None is an obligation NOBODY
# HAS TESTED, and runner_profile_eligible refuses the profile while any slot is None. The lexical
# scan in scripts/suites/06_capabilities_manifest_honesty_veldo.py is NOT one of these: it stays
# exactly as it is for fleet.py, protecting the floor, and is never extended to the runner.
RUNNER_OBLIGATIONS = (
    {"id": "containment_group_per_dispatch", "group": "containment", "clause": "R43",
     "text": "one dedicated containment group and trusted wrapper per dispatch; forks, new sessions "
             "and grandchildren cannot escape it", "test_registration": None},
    {"id": "containment_controls_unreachable", "group": "containment", "clause": "R43",
     "text": "worker credentials and namespaces cannot modify containment controls, reach the "
             "authority's service manager or signal authority processes; OS privileges for identities "
             "and namespaces live only in an operations-installed, narrowly scoped helper",
     "test_registration": None},
    {"id": "hard_memory_limit", "group": "resource_limits", "clause": "R43",
     "text": "a hard, non-worker-writable aggregate memory limit per containment group before launch",
     "test_registration": None},
    {"id": "cumulative_cpu_time_limit", "group": "resource_limits", "clause": "R43",
     "text": "a hard cumulative CPU-time limit across all descendants before launch",
     "test_registration": None},
    {"id": "writable_storage_limits", "group": "resource_limits", "clause": "R43",
     "text": "hard limits on all writable storage in bytes AND inodes, covering temporary files, clone "
             "output and captured logs", "test_registration": None},
    {"id": "admission_reserves_capacity", "group": "resource_limits", "clause": "R43",
     "text": "host admission keeps aggregate limits within qualified capacity with resources reserved "
             "for the authority and unrelated projects; missing or unenforceable limits refuse activation",
     "test_registration": None},
    {"id": "exhaustion_stops_and_quarantines", "group": "resource_limits", "clause": "R43",
     "text": "exhaustion closes effect permissions, stops the group and quarantines its slot until "
             "containment, outcome, accounting and cleanup are reconciled; it never crashes the authority "
             "or exhausts another project's resources", "test_registration": None},
    {"id": "supervisor_retires_on_authority_loss", "group": "lifecycle", "clause": "R43",
     "text": "on authority death, control-channel failure or service stop the trusted supervisor retires "
             "every affected containment group before a replacement schedules", "test_registration": None},
    {"id": "exit_identity_boot_and_start", "group": "lifecycle", "clause": "R43",
     "text": "exit detection uses OS notifications; process identity includes boot identity and start "
             "identity, so a reused PID cannot revive a prior invocation", "test_registration": None},
    {"id": "wrapper_heartbeat", "group": "liveness_and_stop", "clause": "R44",
     "text": "the trusted wrapper emits a heartbeat every %d seconds independent of model output; claim "
             "renewal never depends on a blocking engine call returning" % HEARTBEAT_SECONDS,
     "test_registration": None},
    {"id": "liveness_deadline_closes_effects", "group": "liveness_and_stop", "clause": "R44",
     "text": "a %d-second missed-heartbeat deadline marks liveness uncertain and closes effect "
             "permissions" % LIVENESS_DEADLINE_SECONDS, "test_registration": None},
    {"id": "stop_escalation", "group": "liveness_and_stop", "clause": "R44",
     "text": "cooperative stop, then termination of the containment group after %d seconds, then a kill "
             "of remaining descendants after %d more" % (STOP_TERMINATE_AFTER_SECONDS, STOP_KILL_AFTER_SECONDS),
     "test_registration": None},
    {"id": "leadership_loss_fences_dispatch", "group": "liveness_and_stop", "clause": "R44",
     "text": "loss of leadership closes new-dispatch acceptance within %d seconds" % LEADERSHIP_FENCE_SECONDS,
     "test_registration": None},
    {"id": "checkpoint_holder_cancellation", "group": "liveness_and_stop", "clause": "R44",
     "text": "the trusted checkpoint boundary cancels a checkpoint lock holder within the declared "
             "contention budget (sqlite3 interrupt, rollback or termination of the owning process); a "
             "busy timeout alone does not satisfy it", "test_registration": None},
    {"id": "retirement_requires_proof", "group": "retirement", "clause": "R43, R44",
     "text": "capacity is released only when containment is proven empty and outcome, accounting and "
             "cleanup are durably recorded; unproven emptiness quarantines the slot", "test_registration": None},
)

# WHAT THE LEXICAL SCAN IS AND IS NOT: the floor's detach-token scan stays on fleet.py; the runner
# area is governed by the obligations above and is never added to the scan's targets. The suite
# checks both halves against the suite file's source.
LEXICAL_SCAN_SCOPE = {"suite": "scripts/suites/06_capabilities_manifest_honesty_veldo.py",
                      "target": ".veldo/fleet.py", "never_targets": "project_runner"}

EXCEPTION_RULE = "no_detached_processes"
EXCEPTION_AREA = "project_runner"
EXCEPTION_BOUNDARY = "process_lifetime"


def obligation_registry_problems(process_record):
    """The obligation registry compared with VELDO-DEC-0004's replacement_obligations block in
    both directions, plus its own well-formedness: duplicate ids, an obligation in no declared
    group, a group with no obligation, a clause outside R43/R44, a registration slot missing, and a
    group the record names that the registry does not (or the reverse)."""
    problems = []
    ids = [o["id"] for o in RUNNER_OBLIGATIONS]
    for i in sorted(set(ids)):
        if ids.count(i) > 1:
            problems.append("duplicate obligation id %r" % i)
    for o in RUNNER_OBLIGATIONS:
        if o.get("group") not in OBLIGATION_GROUPS:
            problems.append("obligation %s is in group %r, which is not one of %s" % (o["id"], o.get("group"), OBLIGATION_GROUPS))
        if not set(o.get("clause", "").replace(",", " ").split()) <= {"R43", "R44"}:
            problems.append("obligation %s cites %r; the replacement obligations are R43 and R44" % (o["id"], o.get("clause")))
        if "test_registration" not in o:
            problems.append("obligation %s has no test_registration slot" % o["id"])
    for g in OBLIGATION_GROUPS:
        if not any(o.get("group") == g for o in RUNNER_OBLIGATIONS):
            problems.append("group %s has no obligation" % g)
    block = process_record.get("replacement_obligations") if isinstance(process_record, dict) else None
    named = set(block) if isinstance(block, dict) else set()
    for g in sorted(named - set(OBLIGATION_GROUPS)):
        problems.append("the process decision names obligation group %r that the registry does not" % g)
    for g in sorted(set(OBLIGATION_GROUPS) - named):
        problems.append("the registry has group %s that the process decision's replacement_obligations does not name" % g)
    return problems


def runner_profile_eligible(registrations=None, obligations=RUNNER_OBLIGATIONS):
    """(eligible, missing): the governed runner profile is eligible ONLY when every obligation has a
    registered real failure test, either in its slot or in `registrations` (a mapping obligation id
    to test reference, the form a later package supplies). A profile with one untested obligation is
    refused with that obligation named; there is no partial eligibility."""
    registrations = registrations or {}
    missing = [o["id"] for o in obligations
               if not (o.get("test_registration") or registrations.get(o["id"]))]
    return (not missing), missing


def retirement_allowed(evidence, proofs=RETIREMENT_PROOFS):
    """(allowed, missing): capacity may be released only when EVERY retirement proof is present and
    true in `evidence` (a mapping proof name to bool). Empty containment is one of them and never
    optional: a slot whose emptiness is unproven is quarantined, whatever the outcome says."""
    missing = [p for p in proofs if evidence.get(p) is not True]
    return (not missing), missing


def exception_clauses(contract):
    """Every (rule_id, clause) an architecture contract carries, over patterns and invariants."""
    out = []
    for block in ("patterns", "invariants"):
        for r in contract.get(block) or []:
            if isinstance(r, dict):
                for ex in r.get("exceptions") or []:
                    if isinstance(ex, dict):
                        out.append((r.get("id"), ex))
    return out


def exception_clause_problems(contract):
    """The scoped exception this spec permits, and no other: exactly one clause, on
    no_detached_processes, for the project_runner area, activated by the process_lifetime
    boundary, which must be a registered boundary. A clause on any other rule, for any other
    area, or naming a boundary the registry does not know is a problem by name; so is a contract
    that declares the runner area without the clause or the clause without the area."""
    problems = []
    clauses = exception_clauses(contract)
    areas = {a.get("id") for a in (contract.get("areas") or []) if isinstance(a, dict)}
    if EXCEPTION_AREA in areas and not clauses:
        problems.append("the %s area is declared and no rule carries its exception clause" % EXCEPTION_AREA)
    for rule_id, ex in clauses:
        if rule_id != EXCEPTION_RULE:
            problems.append("rule %r carries an exception; only %s may (VELDO-0016 AC2)" % (rule_id, EXCEPTION_RULE))
        if ex.get("area") != EXCEPTION_AREA:
            problems.append("exception on %r names area %r; only %s is excepted" % (rule_id, ex.get("area"), EXCEPTION_AREA))
        elif EXCEPTION_AREA not in areas:
            problems.append("the exception names area %s, which the contract does not declare" % EXCEPTION_AREA)
        if boundary(ex.get("activated_by")) is None:
            problems.append("exception on %r is activated_by %r, which is not a registered policy boundary" % (rule_id, ex.get("activated_by")))
        elif ex.get("activated_by") != EXCEPTION_BOUNDARY:
            problems.append("exception on %r is activated_by %r; the process exception is activated by %s" % (rule_id, ex.get("activated_by"), EXCEPTION_BOUNDARY))
    if len(clauses) > 1:
        problems.append("%d exception clauses; this spec permits exactly one" % len(clauses))
    return problems


def exception_effective(contract, activation_rows, registrations=None):
    """(effective, reason): whether the process exception is IN FORCE. It is, only when the contract
    carries the clause without problems, the contract is APPROVED on the record (status approved
    with approved_by and approved_at), its version is the accepted architecture revision the
    process_lifetime boundary is registered against, that boundary is ACTIVATED
    (activation_authority accepted its decided record), and the runner profile is eligible (every
    obligation has a registered test). Editing the yaml changes nothing here: the clause is a
    declaration, the activation is the authority."""
    problems = exception_clause_problems(contract)
    if problems:
        return False, "exception clause refused: " + "; ".join(problems)
    if not exception_clauses(contract):
        return False, "the contract carries no exception clause: the invariant binds everywhere"
    if contract.get("status") != "approved" or not all(
            isinstance(contract.get(k), str) and contract.get(k).strip() for k in ("approved_by", "approved_at")):
        return False, ("the contract is %r and not approved on the record (approved_by and approved_at): a "
                       "revision nobody approved makes no exception effective" % contract.get("status"))
    b = boundary(EXCEPTION_BOUNDARY)
    if contract.get("version") != b.get("architecture_version"):
        return False, ("the contract is version %r; the %s boundary is registered against architecture "
                       "revision %r, and a clause on another revision is not the accepted one"
                       % (contract.get("version"), EXCEPTION_BOUNDARY, b.get("architecture_version")))
    row = next((r for r in activation_rows if r.get("boundary") == EXCEPTION_BOUNDARY), None)
    if row is None or not row.get("accepted"):
        return False, ("the %s boundary is not activated (%s)"
                       % (EXCEPTION_BOUNDARY, (row or {}).get("reason", "no activation row")))
    eligible, missing = runner_profile_eligible(registrations)
    if not eligible:
        return False, ("the runner profile is not eligible: %d obligation(s) have no registered test (%s)"
                       % (len(missing), ", ".join(missing)))
    return True, "the process exception is in force for the %s area" % EXCEPTION_AREA


# ---------------------------------------------------------------------------------------------
# AC4: the boundary table. One clause, one refusing predicate, one seeded violation each.
# ---------------------------------------------------------------------------------------------

# THE DOMAIN TABLES R21 names as Veldo's own, which no checkpoint operation may read or write. The
# authority's schema (Package A's entity specs, Package B's store) grows this tuple; the predicate
# refuses by table NAME, so a table added here is guarded the moment it is named.
DOMAIN_TABLES = ("journal", "entities", "accepted_documents", "dispatches", "assignments", "decisions",
                 "nonces", "reservations", "receipts", "publication_cursors", "claims", "leases")
CHECKPOINT_PREFIX = "langgraph_"
# The statement verbs checkpoint work consists of, and nothing else: no transaction control (a
# ROLLBACK or BEGIN EXCLUSIVE from the adapter's connection reaches every table in the file), no
# PRAGMA, ATTACH, DETACH, VACUUM, REINDEX or ANALYZE, no view or trigger (they read domain tables
# under a checkpoint name), no temporary objects.
_CHECKPOINT_VERBS = ("SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP")
_CHECKPOINT_REFUSED_WORDS = ("BEGIN", "COMMIT", "END", "ROLLBACK", "SAVEPOINT", "RELEASE", "PRAGMA", "ATTACH",
                             "DETACH", "VACUUM", "REINDEX", "ANALYZE", "VIEW", "TRIGGER", "TEMP", "TEMPORARY")
# The keywords a table name follows in the verbs above; every identifier in one of these positions
# must carry the checkpoint prefix.
_CHECKPOINT_TABLE_AFTER = ("FROM", "INTO", "JOIN", "UPDATE", "TABLE", "ON")
_CHECKPOINT_SKIP = ("IF", "NOT", "EXISTS", "OR", "REPLACE", "UNIQUE", "INDEX")


def _sql_words(statement):
    """The statement's words with comments and string literals removed, so a token hidden in a
    comment or a value can neither qualify nor disqualify it (a `-- langgraph_checkpoint` comment on
    a ROLLBACK is the reviewer's reproduction)."""
    text = re.sub(r"/\*.*?\*/", " ", str(statement), flags=re.S)
    text = re.sub(r"--[^\n]*", " ", text)
    text = re.sub(r"'(?:[^']|'')*'", " 'lit' ", text)
    text = re.sub(r'"(?:[^"]|"")*"', ' "lit" ', text)
    return re.findall(r"[A-Za-z_][A-Za-z0-9_.]*|[();,*=<>]", text)


def checkpoint_statement_allowed(statement, domain_tables=DOMAIN_TABLES, prefix=CHECKPOINT_PREFIX):
    """(allowed, reason) for one SQL statement the checkpoint adapter wants to run (R21). The
    statement is READ, not searched: comments and string literals are removed first; the first word
    must be a checkpoint verb (SELECT, INSERT, UPDATE, DELETE, CREATE TABLE or INDEX, DROP TABLE or
    INDEX); no transaction-control, PRAGMA, ATTACH, VACUUM, view, trigger or temporary word may appear
    anywhere; every table position (after FROM, INTO, JOIN, UPDATE, TABLE, ON) must name a
    checkpoint-prefixed table; a domain table named anywhere refuses; and at least one checkpoint
    table must be named. A lexical guard for a contract organ, deliberately strict: what it cannot
    read as checkpoint work it refuses, and the store's real boundary (Package B) may only narrow it."""
    words = _sql_words(statement)
    if not words:
        return False, "empty statement (R21)"
    upper = [w.upper() for w in words]
    if upper[0] not in _CHECKPOINT_VERBS:
        return False, "statement begins with %s, not a checkpoint verb %s (R21)" % (upper[0], _CHECKPOINT_VERBS)
    for w in upper:
        if w in _CHECKPOINT_REFUSED_WORDS:
            return False, "statement uses %s, which reaches past the checkpoint namespace (R21)" % w
    if upper[0] in ("CREATE", "DROP") and not any(w in ("TABLE", "INDEX") for w in upper[1:4]):
        return False, "%s of anything but a TABLE or INDEX is refused (R21)" % upper[0]
    bare = [w.split(".")[-1].lower() for w in words]
    hit = sorted(t for t in domain_tables if t.lower() in bare)
    if hit:
        return False, "statement names domain table(s) %s: checkpoint writes cannot touch domain tables (R21)" % ", ".join(hit)
    tables = []
    for i, w in enumerate(upper[:-1]):
        if w in _CHECKPOINT_TABLE_AFTER or (w == "INDEX" and upper[0] in ("CREATE", "DROP")):
            j = i + 1
            while j < len(upper) and upper[j] in _CHECKPOINT_SKIP:
                j += 1
            if j < len(words) and re.match(r"[A-Za-z_]", words[j]):
                tables.append(bare[j])
    if upper[0] == "UPDATE" and len(bare) > 1:
        tables.append(bare[1])
    unprefixed = sorted({t for t in tables if not t.startswith(prefix)})
    if unprefixed:
        return False, "statement names table(s) %s outside the %s* namespace (R21)" % (", ".join(unprefixed), prefix)
    if not any(t.startswith(prefix) for t in tables):
        return False, "statement names no %s* table: the boundary admits only visible checkpoint work (R21)" % prefix
    return True, "checkpoint-namespace statement"


# THE ENFORCEMENT MODULES R35 keeps standard-library only: gate imports, contract validators,
# authorization, journal replay and recovery. The contracts and enforcement areas of the
# architecture contract plus this module and the loader; Package B adds the store and replay.
ENFORCEMENT_MODULES = (".veldo/validate.py", ".veldo/validate_checks.py", ".veldo/arch.py", ".veldo/plan.py",
                       ".veldo/request.py", ".veldo/release_contract.py", ".veldo/authorization.py",
                       ".veldo/policy_check.py", ".veldo/decision.py", ".veldo/decision_review.py",
                       ".veldo/contract_loader.py", ".veldo/policy_contract.py")


def _imported_names(source):
    names = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def enforcement_imports_stdlib_only(root=None, modules=ENFORCEMENT_MODULES):
    """(clean, problems): every enforcement module imports the standard library and nothing else
    (R35, stdlib_only_enforcement), decided by an AST walk that EXECUTES NOTHING, so it gives the
    same answer with the execution environment installed or absent. Sibling organs are loaded by
    path (importlib.util.spec_from_file_location), never imported by name, so a bare import of any
    non-stdlib name is a violation by name. A module that does not exist is a problem too: an
    enforcement entry that vanished is not clean, it is missing."""
    base = Path(root) if root else ROOT
    problems = []
    for rel in modules:
        p = base / rel
        if not p.is_file():
            problems.append("%s is missing" % rel)
            continue
        try:
            names = _imported_names(p.read_text())
        except (SyntaxError, ValueError, OSError) as e:
            problems.append("%s cannot be walked: %s" % (rel, e))
            continue
        for n in sorted(names):
            if n not in sys.stdlib_module_names:
                problems.append("%s imports %s, which is not the standard library (R35)" % (rel, n))
    return (not problems), problems


# R46: the receipt a landing needs. A passing verdict is a FINDING; these are the AUTHORITY.
LANDING_REQUIREMENTS = ("review_ran", "review_inputs_match_candidate", "blocking_findings_disposed",
                        "approvals_valid", "proof_valid", "gate_green", "builder_differs_from_reviewer")


def landing_authorized(receipt):
    """(authorized, missing): a landing is authorized only when EVERY requirement in the receipt is
    literally True (R46, R50): independent review ran against the candidate's exact inputs, every
    blocking finding is disposed by a person, the protected-path approvals are valid, the proof is
    valid, the candidate gate is green, and the builder is not the reviewer. The receipt's `verdict`
    is read for nothing: a passing model verdict is an assertion that the reviewer found no blocker,
    never a credential or landing permission, so a receipt that carries verdict pass and nothing
    else is refused with all seven requirements missing."""
    missing = [k for k in LANDING_REQUIREMENTS if receipt.get(k) is not True]
    return (not missing), missing


def verifier_independent(verifier_path, candidate_root):
    """(independent, reason): the enforcement authorizing a candidate's publication runs from an
    INSTALLED verifier the candidate cannot replace (R50). A verifier whose path lies inside the
    candidate's tree is the candidate's own code judging itself, refused; a verifier outside it is
    independent by location, which is the half a path can decide (digest binding is the Evidence
    Service's, Package E)."""
    v = Path(verifier_path).resolve()
    c = Path(candidate_root).resolve()
    if v == c or c in v.parents:
        return False, ("the verifier at %s lies inside the candidate tree %s: a candidate cannot supply the "
                       "enforcement that authorizes its own publication (R50)" % (v, c))
    return True, "the verifier runs from outside the candidate tree"


# R53: exclusive responsibilities. Only the store commits, only the runner launches, only the
# lander publishes source, only the Evidence Service signs trusted observations.
RESPONSIBILITIES = {"commit_transition": "store", "launch_engine": "runner",
                    "publish_source": "lander", "sign_observation": "evidence_service"}


def responsibility_allowed(role, action):
    """(allowed, reason): `role` may perform `action` only when the table assigns that action to that
    role and no other (R53). An action the table does not know is refused: an exclusive
    responsibility nobody has been given is not one anybody may take."""
    owner = RESPONSIBILITIES.get(action)
    if owner is None:
        return False, "action %r is assigned to no role: nobody may take an unassigned exclusive responsibility (R53)" % (action,)
    if role != owner:
        return False, "only the %s may %s; %r may not (R53)" % (owner, action, role)
    return True, "%s is the %s's own responsibility" % (action, owner)


# THE TABLE: one clause, one predicate, one seeded violation the suite drives. Read by the suite so
# the coverage question ("does every clause AC4 names have a predicate and a violation?") is asked
# of the contract, not remembered by the test.
BOUNDARY_TABLE = (
    {"clause": "R21", "boundary": "checkpoint tables cannot touch domain tables",
     "predicate": "checkpoint_statement_allowed",
     "seeded_violation": "INSERT INTO langgraph_checkpoints SELECT * FROM claims"},
    {"clause": "R35", "boundary": "enforcement imports are standard library only, decided without executing",
     "predicate": "enforcement_imports_stdlib_only",
     "seeded_violation": "an enforcement module that imports langgraph"},
    {"clause": "R46", "boundary": "a passing review assertion is not landing authorization",
     "predicate": "landing_authorized",
     "seeded_violation": "a receipt carrying verdict pass and nothing else"},
    {"clause": "R50", "boundary": "the installed verifier is independent of the candidate",
     "predicate": "verifier_independent",
     "seeded_violation": "a verifier path inside the candidate tree"},
    {"clause": "R53", "boundary": "store, runner, lander and evidence responsibilities are exclusive",
     "predicate": "responsibility_allowed",
     "seeded_violation": "the runner publishing source"},
)
