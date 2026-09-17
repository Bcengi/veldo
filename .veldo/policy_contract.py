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
     "refusal": "raises IntentCorpusError naming the refusal"},
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
# and never calls them, so it is listed here only to make the exclusion an explicit decision the
# suite can see rather than a silent regex accident.
LOADER_SCAN_EXCLUDED = (".veldo/validate.py",)


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
