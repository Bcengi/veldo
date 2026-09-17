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
import re
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
     "refusal": "the corpus opens (its own reads are its own) and every area join, area_of first, "
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


def activation_authority(boundary_id, record, bound_supporting_reviews, required_reviews):
    """(accepted, refusal_class, reason): may `record` activate `boundary_id`? PURE over its
    arguments; the caller supplies the parsed veldo.decision/v1 record (None when none resolves),
    the number of structurally valid, bound, SUPPORTING adversarial reviews the record carries
    (decision_review._valid_bound_reviews_by_decision) and the number its risk tier requires
    (decision_review.required_reviews_for). Accepts ONLY a record that is the registered one,
    at the registered version, decided by a named person, choosing the activating option, with
    enough bound reviews. Everything else is refused by class and by name: a missing record, a
    malformed one, a record for another decision, a draft, a superseded record, a record whose
    version moved past the registry (stale: the registry must be re-read against the new
    version, never assumed), a decided record that chose a different option, a decided record
    without a decider, and a decided record with fewer bound supporting reviews than its tier
    requires. Draft, superseded and stale are refused BEFORE the option is looked at, so a draft
    that already names the activating option in prose is still a draft."""
    b = boundary(boundary_id)
    if b is None:
        return False, "unknown_boundary", "no policy boundary %r is registered" % (boundary_id,)
    if record is None:
        return False, "missing", "decision record %s for boundary %s does not resolve" % (b["decision"], boundary_id)
    if not isinstance(record, dict) or record.get("schema") != DECISION_SCHEMA:
        return False, "malformed", "the record offered for boundary %s is not a %s record" % (boundary_id, DECISION_SCHEMA)
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
    records = []
    if Path(ddir).is_dir():
        for p in sorted(Path(ddir).glob("*.yaml")):
            try:
                records.append(D.load_record(p, V.parse_yamlish))
            except Exception:
                continue
    counts, _seen, _errs = DR._valid_bound_reviews_by_decision(
        DR.default_reviews_dir(base), ddir, base, V.parse_yamlish, quiet, D.load_record)
    policy_path = base / ".veldo" / "policy.yaml"
    by_id = {r.get("id"): r for r in records if isinstance(r, dict)}
    rows = []
    for b in POLICY_BOUNDARIES:
        rec = by_id.get(b["decision"])
        need = DR.required_reviews_for(rec.get("risk") if isinstance(rec, dict) else None, policy_path)
        accepted, refusal, reason = activation_authority(b["id"], rec, counts.get(b["decision"], 0), need)
        rows.append({"boundary": b["id"], "decision": b["decision"], "accepted": accepted,
                     "refusal": refusal, "reason": reason})
    return {"schema": SCHEMA, "boundaries": rows, "matrix_problems": boundary_matrix_problems(records),
            "activated": sorted(r["boundary"] for r in rows if r["accepted"])}
