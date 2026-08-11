#!/usr/bin/env python3
"""VELDO observability criteria vocabulary and the diagnosability gate (the W9 organ
of PLAN-0012): diagnosability becomes a gate concern.

The method ends at the merge and says nothing about two in the morning. When agents
author everything, the five-minute diagnosis that used to be a free byproduct of
authorship is gone: whoever gets paged is a stranger to the code, and so the code has
to explain itself from outside. This module makes that a check. Observability
(structured logs at decision points, metrics, traces, an honest error taxonomy)
enters acceptance criteria for behavior-bearing changes, because every future
responder is a stranger.

THE LOAD-BEARING PRODUCT (C1, the refusals are the product): the validator REFUSES a
behavior-bearing spec that declares NO observability criteria. That refusal is the
point. A behavior-bearing change that ships undiagnosable code is exactly what the
responder plan exists to prevent, so the gate stops it at the cheapest moment - the
ready transition, before anything is built.

TWO HALVES, honestly separated (NG5, the over-attestation lesson):

  MECHANICAL. Whether a behavior-bearing spec declares observability criteria AT ALL,
  and whether the criteria it declares use the recognized VOCABULARY, is checked and
  fails closed. A behavior-bearing spec with no observability block, or one whose
  block names no recognized criterion, is refused; a declared criterion outside the
  vocabulary is refused; an empty description is refused.

  REVIEW LANE. WHETHER the declared criteria are SUFFICIENT - do the logs sit at the
  real decision points, is the error taxonomy honest, would a stranger actually
  diagnose this from outside - is a reviewer's judgment, not mechanizable, and is
  never silently passed and never falsely mechanized. The gate enforces the floor
  (at least one recognized criterion, or exactly the criteria a system's contract
  requires); the reviewer judges the ceiling.

WHO IS behavior-bearing. A spec declares itself with the behavior_bearing field
during elaboration (true or false), the same move that turned intent into the spec,
the shape into a contract, and placement into a checked field: a memory an agent
carries becomes a declared field. Only an explicit true is gated; absent or false is
exempt, so the already-shipped corpus (which declares no such field) is never gated
and a reviewer backstops an dishonest false the way a reviewer backstops a
mis-declared risk. WHETHER a spec is truly behavior-bearing is itself a review-lane
judgment; the field records the decision.

THE C7 SOFT JOIN. Where a PLAN-0011 architecture contract declares a system's
observability rules (the optional contract-level observability.required list), those
criteria are what a behavior-bearing change must declare - a system's observability
rules live in the contract. Where no such rules exist (or no contract exists) the gate
STANDS DOWN honestly to the spec-level floor (at least one recognized criterion). The
join is never faked: an absent section yields the floor, never an invented rule; a
malformed section is refused, never silently ignored.

TWO POSTURES, shared with the sibling organs (arch.py placement, incident.py, ...):
  ADOPTION SAFE. A repository with no architecture contract, and a spec that declares
  neither behavior_bearing nor observability, stand down (byte-identically
  unaffected). The mandatory rule binds at the ready TRANSITION (validate.check_ready),
  never as a static sweep of every spec, so the shipped corpus is never re-evaluated.
  FAIL CLOSED. The moment a behavior-bearing spec is promoted to ready against a
  contract, a missing or malformed observability declaration refuses by name.

Dependency free by construction: the structural validator and the gate are PURE over
a spec's parsed front-matter dict (from the one parser, validate.parse_yamlish) and
the parsed architecture contract, and report through the caller's fail reporter, the
way arch.validate_placement receives its parser and reporter. This module adds no
second parser and no import cycle, and it starts no process, thread, or timer.

The metrics HALF of outcome O6 (time-to-diagnosis, recurrence, the diagnosability
score, incidents-per-area) is a SEPARATE work item, WARP-1210 (W10); nothing here
derives a metric. Landing the gate into the /veldo:init lay-down and any release doc is
WARP-1211 (W11). This module is the vocabulary and the gate, and only those.
"""
from pathlib import Path

SCHEMA = "veldo.observability/v1"

# The recognized observability criteria (outcome O6): the closed vocabulary a
# behavior-bearing change declares from. The description is the honest phrasing the
# refusal messages and the elaboration skill use; the KEYS are what a spec declares.
OBSERVABILITY_CRITERIA = {
    "logs": "structured logs at decision points",
    "metrics": "metrics",
    "traces": "traces",
    "error_taxonomy": "an honest error taxonomy",
}


def _criteria_phrase():
    """The vocabulary rendered for a human-facing refusal: the keys and what they mean,
    in a stable order, so a refusal names exactly what to declare."""
    return ", ".join("%s (%s)" % (k, OBSERVABILITY_CRITERIA[k]) for k in sorted(OBSERVABILITY_CRITERIA))


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _as_bool(v):
    """The value as a real boolean, or None when it is neither. The one front-matter
    parser (validate.parse_yamlish) leaves an unquoted true/false as the string
    "true"/"false" (it only coerces integers), so a boolean contract field arrives as
    that string; this accepts the string forms and a real bool and refuses anything
    else, so a truthy-looking value like "yes" or 1 is not silently accepted (the same
    discipline incident.py uses for its boolean fields)."""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        s = v.strip().lower()
        if s == "true":
            return True
        if s == "false":
            return False
    return None


def behavior_bearing(fm):
    """Whether a spec declares itself behavior-bearing. The value is a DECLARED field
    set during elaboration (behavior_bearing: true|false): True when it says true,
    False when it says false, and None when it is absent or unparseable. The gate
    treats ONLY an explicit True as behavior-bearing (absent or false is exempt), so
    the already-shipped corpus, which declares no such field, is never gated. WHETHER a
    spec is truly behavior-bearing is a review-lane judgment; the field records the
    decision the way risk and placement record theirs."""
    return _as_bool(fm.get("behavior_bearing"))


def declared_criteria(fm):
    """The set of RECOGNIZED, non-empty observability criteria a spec declares in its
    observability block. A criterion outside the vocabulary, or one with an empty
    description, is not counted here (the structural validator refuses it separately);
    this is the set that satisfies the mandatory floor and the contract-required set."""
    block = fm.get("observability")
    if not isinstance(block, dict):
        return set()
    return {k for k, v in block.items() if k in OBSERVABILITY_CRITERIA and _is_str(v)}


def validate_observability(fm, where, fail):
    """Structural validation of a spec's OBSERVABILITY declaration, at spec-validation
    (elaboration) time. Reports each problem through fail(where, msg) and returns the
    error count. Pure over the front-matter dict.

    OPTIONAL by design (adoption safe): a spec that declares neither behavior_bearing
    nor an observability block stands down (returns 0) - nothing is forced onto a spec
    here, and the mandatory rule lives at the ready transition. Once a declaration is
    present it is validated fail closed:
      - behavior_bearing, when present, must be true or false (a diagnosability
        decision is recorded, never a truthy-looking near-miss);
      - observability, when present, must be a MAPPING of criteria;
      - every observability key must be in the recognized vocabulary (a criterion the
        method does not recognize is refused, not silently accepted - anti-vacuity);
      - every observability value must be a non-empty description (an empty criterion
        declares nothing).

    HONEST BOUNDARY. This validates the DECLARATION's shape only. WHETHER the criteria
    are SUFFICIENT for a stranger to diagnose the change is a review-lane judgment,
    never graded here (NG5); and the MANDATORY rule (a behavior-bearing spec must
    declare criteria) is enforced by observability_gate at the ready transition, not by
    this present-only structural check."""
    errs = 0
    bb = fm.get("behavior_bearing")
    if bb is not None and _as_bool(bb) is None:
        errs += fail(where, "behavior_bearing, when present, must be true or false (got %r): "
                            "whether a change is behavior-bearing is a recorded decision, not a near-miss" % bb)
    block = fm.get("observability")
    if block is None:
        return errs
    if not isinstance(block, dict):
        errs += fail(where, "observability, when present, must be a mapping of criteria "
                            "(one or more of %s), each a non-empty description" % _criteria_phrase())
        return errs
    for key, val in block.items():
        if key not in OBSERVABILITY_CRITERIA:
            errs += fail(where, "observability criterion %r is not in the vocabulary %s: the recognized "
                                "criteria are structured logs at decision points, metrics, traces, and an "
                                "honest error taxonomy" % (key, sorted(OBSERVABILITY_CRITERIA)))
        elif not _is_str(val):
            errs += fail(where, "observability.%s must be a non-empty description (what is logged, measured, "
                                "or traced, and at which decision point)" % key)
    return errs


def contract_observability(contract):
    """The C7 SOFT JOIN reader: where a PLAN-0011 architecture contract declares a
    system's observability rules, they live in the contract's OPTIONAL top-level
    observability section (observability.required, a list of criteria). Returns a
    (status, required) pair:

      ("absent", set())      no contract, or the contract declares no observability
                             rules -> the gate STANDS DOWN to the spec-level floor (at
                             least one recognized criterion). The join is never faked:
                             an absent section yields the floor, never an invented rule.
      ("present", {...})     the contract declares a non-empty list of recognized
                             criteria -> a behavior-bearing change must declare each.
      ("malformed", set())   the section is present but not well formed (not a mapping,
                             an empty or non-list required, or a criterion outside the
                             vocabulary) -> the gate REFUSES (a malformed join is not
                             silently ignored).

    This never invents a required criterion the contract did not declare, and never
    pretends a contract has rules it does not (C7: stand down honestly when absent)."""
    if not isinstance(contract, dict):
        return "absent", set()
    section = contract.get("observability")
    if section is None:
        return "absent", set()
    if not isinstance(section, dict):
        return "malformed", set()
    required = section.get("required")
    if required is None:
        return "absent", set()  # a section that declares no required list declares no rule
    if not isinstance(required, list) or not required:
        return "malformed", set()
    crits = set()
    for c in required:
        if not _is_str(c) or c not in OBSERVABILITY_CRITERIA:
            return "malformed", set()
        crits.add(c)
    return "present", crits


def observability_gate(fm, contract=None):
    """The MANDATORY diagnosability gate (the O6/C1 property), as a PURE predicate:
    return the list of problems (empty iff the spec passes). Enforced at the ready
    TRANSITION and never as a static sweep of the already-shipped corpus, exactly as
    arch.placement_gate is - so the mandatory rule binds new work at the transition
    while the shipped corpus, past ready, is untouched (RJ6, zero regressions).

    A spec that is NOT behavior-bearing (behavior_bearing absent or false) is EXEMPT:
    the gate returns no problem, so a non-behavior-bearing change is never a false
    positive. A behavior-bearing spec (behavior_bearing: true) MUST declare
    observability criteria:
      - where the architecture contract declares a system's observability rules (C7),
        the spec must declare each required criterion;
      - where no such rules exist, the spec must declare at least one recognized
        criterion (the spec-level floor).

    The structural rules (recognized vocabulary, non-empty descriptions, a valid
    behavior_bearing value) are reused from validate_observability so the declaration's
    shape is defined once. Pure over the two dicts: the caller (the ready transition)
    renders these problems."""
    problems = []
    # Structural rules first (shared with the present-only check), recording each
    # problem so a malformed declaration is refused at the transition too. The recorder
    # returns 1 per problem to honor the fail-callback contract.
    validate_observability(fm, "observability", lambda where, msg: (problems.append(msg), 1)[1])
    # Only an explicit behavior-bearing declaration is gated; absent or false is exempt
    # (so the shipped corpus and non-behavior-bearing changes are never a false positive).
    if behavior_bearing(fm) is not True:
        return problems
    declared = declared_criteria(fm)
    status, required = contract_observability(contract)
    if status == "malformed":
        problems.append("the architecture contract's observability rules are malformed "
                        "(observability.required must be a non-empty list of %s): where a system's "
                        "observability rules live in the contract (C7) they must be well formed, or the "
                        "join is refused rather than faked" % sorted(OBSERVABILITY_CRITERIA))
        return problems
    if status == "present":
        for crit in sorted(required):
            if crit not in declared:
                problems.append("a behavior-bearing spec must declare the observability criterion %r that the "
                                "architecture contract requires for this system (C7: a system's observability "
                                "rules live in the contract), and this spec does not declare it (%s)"
                                % (crit, OBSERVABILITY_CRITERIA[crit]))
    elif not declared:
        problems.append("a behavior-bearing spec declares NO observability criteria: observability - one or "
                        "more of %s - becomes acceptance criteria for a behavior-bearing change, because "
                        "every future responder is a stranger to the code. Declare an observability: block "
                        "naming at least one criterion (the sufficiency of the criteria is a review-lane "
                        "judgment; declaring none is refused here)" % _criteria_phrase())
    return problems


def _cli(argv):
    """Standalone runner: validate a spec's observability declaration and run the
    diagnosability gate over it, reusing validate.py's ONE front-matter parser and
    failure reporter (no second parser), and the one contract loader for the C7 join.
    This mirrors how the sibling organs expose a standalone runner; wiring the gate
    into the /veldo:init lay-down is WARP-1211 (W11)."""
    import importlib.util
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("veldo_validate", here / "validate.py")
    V = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(V)
    arg = argv[1] if len(argv) > 1 else None
    if not arg or not Path(arg).is_file():
        print("usage: python3 .veldo/observability.py <spec.md>")
        print("       validates the observability declaration and runs the diagnosability gate")
        print("vocabulary: %s" % _criteria_phrase())
        return 2
    text = Path(arg).read_text()
    import re as _re
    m = _re.match(r"^---\n(.*?)\n---", text, _re.S)
    if m is None:
        print("  %s: no YAML front matter" % arg)
        return 1
    try:
        fm = V.parse_yamlish(m.group(1))
    except ValueError as e:
        print("  %s: front matter outside the parser subset: %s" % (arg, e))
        return 1
    _arch, contract = V.load_repo_contract(repo_root=str(here.parent))
    errs = validate_observability(fm, arg, V.fail)
    for msg in observability_gate(fm, contract):
        errs += V.fail(arg, msg)
    if errs:
        print("veldo observability: %d problem(s)" % errs)
        return 1
    bb = behavior_bearing(fm)
    print("veldo observability: clean (%s; declared criteria: %s)"
          % ("behavior-bearing" if bb is True else "not behavior-bearing (exempt)",
             sorted(declared_criteria(fm)) or "none"))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_cli(sys.argv))
