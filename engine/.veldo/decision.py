#!/usr/bin/env python3
"""VELDO foundational decision record (veldo.decision/v1): a foundational choice as
a first-class, versioned, human-decided unit of work, and its structural validator.

This is the W5 organ of PLAN-0011. Some choices pass every test while being wrong:
the wrong technology, the wrong architecture style, the wrong communication shape,
the wrong tool, chosen silently inside a feature's implementation and unfixable by
refactoring because the flaw is the foundation, not the code on top. VELDO makes
that choice a first-class artifact: a readable record under .veldo/decisions/ that
states the decision to make, the OPTION SPACE the machine elaborates (each option
with the condition where it dead-ends and when), the reversal-cost class and the
risk tier it maps to, the assumptions that become living tripwires (each with a
measurable signal and a stated breach condition), and, only when a human has
decided, a decision block naming the chosen option and the human who decided.

This module validates the artifact STRUCTURALLY, the same way .veldo/arch.py
validates the architecture contract and .veldo/plan.py validates a plan: required
fields present, closed vocabularies honored, an option without its dead-end
condition rejected at record time, and every internal reference resolving. Two
properties are load bearing here and enforced fail closed:

  HUMAN DECIDES (O4, NG2). A record whose status is decided must carry a recorded
  human decider (decided_by, decided_at) and a chosen option that resolves to a
  declared option. A draft needs no decider: draft is the un-decided state, the
  option space before a human commits. No machine-decided state is representable.

  SCRUTINY SCALES WITH REVERSAL COST (D5). The reversal-cost class maps to the
  existing risk tiers, and an irreversible decision must sit at the critical tier
  (the slowest, most independent judgment the policy can express). An irreversible
  choice recorded below critical is refused.

This module builds the RECORD and its validator only. The adversarial decision
REVIEW that attacks a proposal before a human decides is WARP-1106 (W6), and the
in-session TRIPWIRE pass that monitors each assumption's signal for an approaching
breach is WARP-1107 (W7); both are honestly later items and nothing here pretends
to do their work.

Two postures, both shared with the contract organ:
  ADOPTION SAFE. A repository with no .veldo/decisions/ directory is untouched:
  check_decisions_dir on an absent directory stands down and returns clean, so
  adding this module changes no existing gate. The moment a record exists it is
  validated and fails closed.
  FAIL CLOSED. A malformed record, an out-of-vocabulary status or reversal-cost
  class or risk tier, an option missing its dead-end condition, an assumption
  missing its signal or breach, a decided record with no recorded human decider,
  or a chosen option that does not resolve each refuse by name.

Dependency free by construction: the caller (.veldo/validate.py) passes in the
front-matter parser and the failure reporter it already owns, so this module adds
no second YAML parser and no import cycle.
"""
from pathlib import Path

SCHEMA = "veldo.decision/v1"
STATUSES = {"draft", "decided", "superseded"}
REVERSAL_COSTS = {"reversible", "costly", "irreversible"}
# The existing risk tiers (mirrors validate.RISKS); D5 maps reversal cost onto them.
RISKS = {"low", "standard", "high", "critical"}


class DecisionRecordError(ValueError):
    """A decision record is malformed. Raised by name so a bad record never
    silently no-ops (parallels ArchContractError and PackManifestError)."""


def default_decisions_dir(root=None):
    return Path(root or ".") / ".veldo" / "decisions"


def load_record(path, parse):
    """Parse the record at path into a dict using the caller's front-matter parser
    (the VELDO yamlish subset), raising DecisionRecordError on unreadable or
    unparseable input. The single place a record is read, so W6 and W7 reuse it
    rather than parsing the file a second way."""
    p = Path(path)
    try:
        text = p.read_text()
    except OSError as e:
        raise DecisionRecordError("decision record unreadable: %s" % e)
    try:
        data = parse(text)
    except ValueError as e:
        raise DecisionRecordError("decision record outside the record subset: %s" % e)
    if not isinstance(data, dict):
        raise DecisionRecordError("decision record must be a mapping at the top level")
    return data


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _as_list(v):
    return v if isinstance(v, list) else []


def _is_pos_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 1


def validate_record(data, root, record_path, fail):
    """Structural validation of one parsed veldo.decision/v1 record. Reports each
    problem through fail(name, msg) and returns the error count. Pure over the
    dict (no filesystem access), so it is trivially reused by the directory scan
    and the single-file entry point."""
    errs = 0
    name = str(record_path)

    if data.get("schema") != SCHEMA:
        errs += fail(name, "schema must be %r (got %r)" % (SCHEMA, data.get("schema")))
    for field in ("id", "title", "status", "problem_class", "owner"):
        if not _is_str(data.get(field)):
            errs += fail(name, "missing or empty required field: %s" % field)
    if not _is_pos_int(data.get("version")):
        errs += fail(name, "version must be an integer >= 1: a decision record is versioned")

    status = data.get("status")
    if _is_str(status) and status not in STATUSES:
        errs += fail(name, "bad status %r (allowed: %s)" % (status, sorted(STATUSES)))

    # Reversal cost and the risk tier it maps to (D5). Both are closed vocabularies,
    # and an irreversible choice must sit at the critical tier: scrutiny scales with
    # reversal cost, so the irreversible choices get the slowest judgment the policy
    # can express, never a lower tier that would let them through with less.
    rc = data.get("reversal_cost")
    if rc not in REVERSAL_COSTS:
        errs += fail(name, "reversal_cost must be one of %s (got %r)" % (sorted(REVERSAL_COSTS), rc))
    risk = data.get("risk")
    if risk not in RISKS:
        errs += fail(name, "risk must be one of %s (got %r)" % (sorted(RISKS), risk))
    if rc == "irreversible" and risk != "critical":
        errs += fail(name, "reversal_cost irreversible must map to risk critical (D5): the irreversible choices carry the highest tier, with recorded human approval and the most independent verdicts")

    # The option space: the real options the machine elaborates against the problem
    # class, each with a summary and its dead-end condition (where and when it stops
    # working). An option without a dead_end is a candidate nobody stress tested;
    # rejecting it at record time is the anti-vacuity move for the option space.
    options = _as_list(data.get("options"))
    if not options:
        errs += fail(name, "no options: a decision record without an elaborated option space is a conclusion, not a decision")
    opt_ids = []
    for o in options:
        if not isinstance(o, dict) or not _is_str(o.get("id")) or not _is_str(o.get("summary")):
            errs += fail(name, "each option needs an id and a summary")
            continue
        if not _is_str(o.get("dead_end")):
            errs += fail(name, "option %s: a dead_end condition is required (where and when this option stops working)" % o.get("id"))
        opt_ids.append(o["id"])
    for oid in sorted(set(opt_ids)):
        if opt_ids.count(oid) > 1:
            errs += fail(name, "duplicate option id %r" % oid)
    known_options = set(opt_ids)

    # Assumptions become living tripwires: each carries a measurable signal (what a
    # later in-session pass watches) and a stated breach condition (when it is
    # considered broken). A record with no assumptions, or an assumption with no
    # signal or no breach, is a memo, not a tripwire; the monitoring pass (W7) would
    # have nothing to check.
    assumptions = _as_list(data.get("assumptions"))
    if not assumptions:
        errs += fail(name, "no assumptions: a decision record carries the assumptions that become living tripwires, each with a signal and a breach condition")
    asm_ids = []
    for a in assumptions:
        if not isinstance(a, dict) or not _is_str(a.get("id")) or not _is_str(a.get("statement")):
            errs += fail(name, "each assumption needs an id and a statement")
            continue
        if not _is_str(a.get("signal")):
            errs += fail(name, "assumption %s: a measurable signal is required (what the tripwire watches)" % a.get("id"))
        if not _is_str(a.get("breach")):
            errs += fail(name, "assumption %s: a breach condition is required (when the assumption is considered broken)" % a.get("id"))
        asm_ids.append(a["id"])
    for aid in sorted(set(asm_ids)):
        if asm_ids.count(aid) > 1:
            errs += fail(name, "duplicate assumption id %r" % aid)

    # Governance: only a human decides, on the record (O4, NG2). status decided
    # requires a decision block with a recorded human decider and a chosen option
    # that resolves to a declared one; a draft needs no decider, and a non-decided
    # record may not smuggle a decider or a chosen option (no machine-decided state).
    decision = data.get("decision")
    if status == "decided":
        if not isinstance(decision, dict):
            errs += fail(name, "status decided requires a decision block (chosen, decided_by, decided_at): only a human decides, on the record")
        else:
            for field in ("decided_by", "decided_at", "chosen"):
                if not _is_str(decision.get(field)):
                    errs += fail(name, "status decided requires decision.%s: a foundational choice is decided by a human on the record, never machine-decided" % field)
            chosen = decision.get("chosen")
            if _is_str(chosen) and chosen not in known_options:
                errs += fail(name, "decision.chosen %r is not a declared option (referenced but absent)" % chosen)
    elif isinstance(decision, dict) and any(_is_str(decision.get(f)) for f in ("decided_by", "chosen")):
        errs += fail(name, "status %r carries a decision block with a decider or a chosen option: a record is decided only when its status says so, never by smuggling a decision under a draft" % status)

    # Re-decision lifecycle: a superseded record names the decision that replaces it,
    # so a reader is never left at a dead reference (the successor is W7's re-decision
    # draft once a tripwire breaches).
    if status == "superseded" and not _is_str(data.get("superseded_by")):
        errs += fail(name, "status superseded requires superseded_by: a re-decision names the decision that replaces it")

    return errs


def check_record(path, root, required, parse, fail):
    """Single-file entry point. Absent file: stand down (adoption safe) unless it is
    required, in which case fail closed (referenced but absent). Present file: parse
    and validate structurally, failing closed on anything malformed."""
    p = Path(path)
    if not p.is_file():
        if required:
            return fail(str(p), "decision record is referenced as required but absent (fail closed)")
        return 0
    try:
        data = load_record(p, parse)
    except DecisionRecordError as e:
        return fail(str(p), str(e))
    return validate_record(data, root, p, fail)


def check_decisions_dir(ddir, root, parse, fail):
    """The gate entry point over the per-repo decision records. Adoption safe: an
    absent .veldo/decisions/ directory stands down and returns clean, so a repository
    with no decision records is byte-identically unaffected. Present records each
    fail closed on anything malformed, and a decision id declared by more than one
    record is refused (a duplicate id is an ambiguous reference across the set)."""
    d = Path(ddir)
    if not d.is_dir():
        return 0
    errs = 0
    ids = {}
    for p in sorted(d.glob("*.yaml")):
        errs += check_record(p, root, False, parse, fail)
        try:
            data = load_record(p, parse)
        except DecisionRecordError:
            continue  # already reported by check_record above
        rid = data.get("id")
        if _is_str(rid):
            ids.setdefault(rid, []).append(p.name)
    for rid, files in sorted(ids.items()):
        if len(files) > 1:
            errs += fail(str(d), "duplicate decision id %r across records: %s" % (rid, ", ".join(sorted(files))))
    return errs
