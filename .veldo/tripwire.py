#!/usr/bin/env python3
"""VELDO decision tripwires (veldo.readings/v1): a foundational decision's assumptions are
LIVING TRIPWIRES monitored IN-SESSION, and the pure evaluator that fires when one breaches.

This is the W7 organ of PLAN-0011 and the fifth move of the method's "wrong foundations"
invention. WARP-1105 made a foundational choice a first-class decision RECORD whose every
assumption carries a measurable SIGNAL and a stated BREACH condition; WARP-1106 shipped the
adversarial review that lets a record move to `decided`. But a decided record is not a memo:
each assumption is a living tripwire, and this module is the mechanism that WATCHES those
assumptions and FIRES when one breaches, so a wrong foundational choice is discovered by
ASSUMPTION BREACH while there is still time to re-decide deliberately, not by an outage
months later (a static ADR never did this).

The evaluation reads a RECORDED-READINGS source and compares each assumption's signal against
its breach. Per resolved decision D3 the readings are a small file the session updates in
session at the weekly pass, homed per-repo under .veldo/readings/*.yaml (a directory the engine
glob does not sweep), naming the decision it measures and recording, for one or more of that
decision's assumptions, the latest measurement in one of two shapes:

  MEASURED. kind: measured, a `value` and a machine-comparable `breach_when` condition (a
  comparator and a threshold, e.g. ">= 40") that operationalizes the assumption's prose breach,
  an optional `approaching_when` early-warning, and an `at` timestamp. The evaluator mechanically
  parses the comparator and compares the recorded value: the comparison is a genuine mechanical
  evaluation, not a recorder-set flag echoed back.

  MANUAL_REVIEW. kind: manual_review, a `reviewed_at`, a `valid_days` expiry window, a `holds`
  finding, and an `at` timestamp (the manual-review-with-expiry shape D3 names). A review whose
  finding is false breaches; a review past its expiry is STALE and fires, forcing a re-attestation.

Two properties are load bearing and enforced fail closed:

  IN-SESSION ONLY, NOTHING DETACHED (NG1, the contract invariant no_detached_processes, and this
  codebase's feedback_no_rogue_processes). The evaluation is a PURE function that reads recorded
  files and takes the current date as an INJECTED parameter; it starts no process and no thread,
  installs no timer, and never polls in the background. It runs only where the gate, the tripwires
  CLI mode, and the weekly pass invoke it, and nothing outlives the session. This module imports
  only pathlib and datetime; a selftest string-scan of the source proves it contains no spawn
  primitive, with mutation teeth.

  FAIL CLOSED, ADOPTION SAFE. A malformed readings set (a wrong schema, an unknown assumption
  reference, an out-of-vocabulary kind, a measured reading missing its value or its breach_when or
  carrying an unparseable comparator, a manual-review missing its fields, a readings file naming a
  decision no record declares) each refuse by name; a FIRED tripwire (breach or lapse) over a
  DECIDED record refuses (the anti-vacuity teeth). A repository with no .veldo/decisions/ directory
  stands down and returns clean, so it is byte-identically unaffected.

A fired tripwire surfaces the breached assumption for human attention and drafts exactly ONE
veldo.redecision/v1 DRAFT for the human to promote (the machine drafts, never decides, never
re-platforms). The ENTROPY restoration loop for the decay class (cost-to-change per area and its
restoration spec) is WARP-1108/WARP-1109 (W8/W9), honestly later work; nothing here does its job.

Dependency free by construction: the caller (.veldo/validate.py) passes in the front-matter parser,
the failure reporter, and the decision loader (.veldo/decision.py's load_record, the one place a
decision record is read), so this module adds no second YAML parser and no import cycle.
"""
from datetime import date, timedelta
from pathlib import Path

SCHEMA = "veldo.readings/v1"
REDECISION_SCHEMA = "veldo.redecision/v1"
DECISION_SCHEMA = "veldo.decision/v1"
KINDS = {"measured", "manual_review"}
# a manual-review finding is recorded as one of these strings (parse_yamlish yields
# strings, never Python booleans, for a bare true/false scalar).
HOLDS_VALUES = {"true", "false"}

# tripwire states, from the pure evaluation of one assumption.
OK = "ok"
APPROACHING = "approaching"
BREACHED = "breached"
STALE = "stale"
UNMONITORED = "unmonitored"
# the states that FIRE: a broken or lapsed foundation, which refuses the gate and drafts a
# re-decision unit. approaching and unmonitored surface as warnings; ok is silent.
FIRED = ("breached", "stale")
WARN = ("approaching", "unmonitored")

# comparators, longest first so a two-character operator is matched before a one-character one.
_COMPARATORS = (">=", "<=", "==", "!=", ">", "<")
_ORDER_OPS = (">=", "<=", ">", "<")


class TripwireError(ValueError):
    """A readings file is malformed. Raised by name so a bad readings set never silently
    no-ops (parallels DecisionRecordError and DecisionReviewError)."""


def default_readings_dir(root=None):
    return Path(root or ".") / ".veldo" / "readings"


def default_decisions_dir(root=None):
    return Path(root or ".") / ".veldo" / "decisions"


def default_redecisions_dir(root=None):
    return Path(root or ".") / ".veldo" / "redecisions"


def load_readings(path, parse):
    """Parse the readings file at path into a dict using the caller's front-matter parser
    (the VELDO yamlish subset), raising TripwireError on unreadable or unparseable input. The
    single place a readings file is read, so every consumer reuses it rather than parsing the
    file a second way."""
    p = Path(path)
    try:
        text = p.read_text()
    except OSError as e:
        raise TripwireError("readings file unreadable: %s" % e)
    try:
        data = parse(text)
    except ValueError as e:
        raise TripwireError("readings file outside the readings subset: %s" % e)
    if not isinstance(data, dict):
        raise TripwireError("readings file must be a mapping at the top level")
    return data


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _as_list(v):
    return v if isinstance(v, list) else []


def _is_pos_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 1


def _num(v):
    """The float value of v, or None when v is not a number or a numeric string. A boolean is
    never a number here (parse_yamlish does not produce booleans, but guard anyway)."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except ValueError:
            return None
    return None


def _as_date(s):
    """The date parsed from an ISO string, or None when s is absent or not an ISO date."""
    if not _is_str(s):
        return None
    try:
        return date.fromisoformat(s.strip())
    except ValueError:
        return None


def parse_condition(expr):
    """Parse a machine-comparable condition 'OP THRESHOLD' (for example '>= 40') into
    (op, threshold_text). Raises TripwireError when expr is not a string, carries no
    recognized comparator, or has a comparator with no threshold."""
    if not _is_str(expr):
        raise TripwireError("must be a non-empty condition string like '>= 40'")
    s = expr.strip()
    for op in _COMPARATORS:
        if s.startswith(op):
            thr = s[len(op):].strip()
            if thr == "":
                raise TripwireError("condition %r has a comparator but no threshold" % expr)
            return op, thr
    raise TripwireError("condition %r has no recognized comparator (one of %s)" % (expr, list(_COMPARATORS)))


def condition_met(value, op, threshold):
    """True iff the recorded value satisfies 'value OP threshold'. An ordering comparator
    requires a numeric value and threshold (raising TripwireError otherwise); an equality
    comparator compares numerically when both sides are numeric, else as trimmed strings."""
    if op in _ORDER_OPS:
        v, t = _num(value), _num(threshold)
        if v is None or t is None:
            raise TripwireError("ordering comparator %r needs a numeric value and threshold (got value %r, threshold %r)"
                                % (op, value, threshold))
        if op == ">=":
            return v >= t
        if op == "<=":
            return v <= t
        if op == ">":
            return v > t
        return v < t
    v, t = _num(value), _num(threshold)
    eq = (v == t) if (v is not None and t is not None) else (str(value).strip() == str(threshold).strip())
    return eq if op == "==" else (not eq)


def _validate_reading(r, declared_asm, fail, where):
    """Structural checks for one reading entry, fail closed. Returns the error count. A
    reading that passes with zero errors is safe to evaluate (an ordering comparator is
    proven numeric here, so the later comparison never raises for a validated reading)."""
    if not isinstance(r, dict) or not _is_str(r.get("assumption")):
        return fail(where, "each reading needs an assumption id")
    aid = r["assumption"]
    errs = 0
    if aid not in declared_asm:
        errs += fail(where, "reading references assumption %r the decision does not declare (referenced but absent)" % aid)
    kind = r.get("kind")
    if kind not in KINDS:
        return errs + fail(where, "reading %s: kind must be one of %s (got %r)" % (aid, sorted(KINDS), kind))
    if not _is_str(r.get("at")):
        errs += fail(where, "reading %s: an at timestamp is required (when the reading was recorded)" % aid)
    if kind == "measured":
        if r.get("value") is None:
            errs += fail(where, "reading %s: a measured reading requires a value" % aid)
        bw = r.get("breach_when")
        if not _is_str(bw):
            errs += fail(where, "reading %s: a measured reading requires a machine-comparable breach_when (for example '>= 40')" % aid)
        else:
            try:
                op, _thr = parse_condition(bw)
                if op in _ORDER_OPS and r.get("value") is not None and _num(r.get("value")) is None:
                    errs += fail(where, "reading %s: breach_when uses an ordering comparator but the value %r is not numeric" % (aid, r.get("value")))
            except TripwireError as e:
                errs += fail(where, "reading %s: breach_when %s" % (aid, e))
        aw = r.get("approaching_when")
        if aw is not None:
            if not _is_str(aw):
                errs += fail(where, "reading %s: approaching_when must be a condition string when present" % aid)
            else:
                try:
                    parse_condition(aw)
                except TripwireError as e:
                    errs += fail(where, "reading %s: approaching_when %s" % (aid, e))
    else:  # manual_review
        if _as_date(r.get("reviewed_at")) is None:
            errs += fail(where, "reading %s: a manual_review requires reviewed_at as an ISO date (when a human last attested)" % aid)
        if not _is_pos_int(r.get("valid_days")):
            errs += fail(where, "reading %s: a manual_review requires valid_days as a positive integer (the expiry window)" % aid)
        if r.get("holds") not in HOLDS_VALUES:
            errs += fail(where, "reading %s: a manual_review requires holds as one of %s (the human's finding at review time)" % (aid, sorted(HOLDS_VALUES)))
    return errs


def _state_for(assumption, reading, today):
    """The tripwire state of one assumption given its latest reading (or None) at `today`.
    Pure; the reading has already passed _validate_reading, so no comparison raises here."""
    if reading is None:
        return UNMONITORED, "no reading recorded for this assumption"
    if reading.get("kind") == "measured":
        val = reading.get("value")
        op, thr = parse_condition(reading.get("breach_when"))
        if condition_met(val, op, thr):
            return BREACHED, "measured value %r meets breach_when %r" % (val, reading.get("breach_when"))
        aw = reading.get("approaching_when")
        if _is_str(aw):
            aop, athr = parse_condition(aw)
            if condition_met(val, aop, athr):
                return APPROACHING, "measured value %r meets approaching_when %r" % (val, aw)
        return OK, "measured value %r is within limits (breach_when %r)" % (val, reading.get("breach_when"))
    # manual_review
    if reading.get("holds") == "false":
        return BREACHED, "the manual review found the assumption no longer holds"
    reviewed = _as_date(reading.get("reviewed_at"))
    expiry = reviewed + timedelta(days=reading.get("valid_days")) if reviewed else None
    if expiry is not None and today > expiry:
        return STALE, "the manual review lapsed on %s (reviewed %s, valid %s days)" % (
            expiry.isoformat(), reading.get("reviewed_at"), reading.get("valid_days"))
    return OK, "manually attested %s, valid through %s" % (
        reading.get("reviewed_at"), expiry.isoformat() if expiry else "?")


def evaluate_readings(decision, readings, today, fail, where):
    """PURE evaluation of one decision's assumptions against its readings at date `today`.
    Returns (findings, errs). findings is one dict per DECLARED assumption with its state and a
    human-readable detail; errs counts only STRUCTURAL problems (fail closed). A FIRED tripwire
    is a finding, not a structural error: the caller decides whether firing refuses. Reads and
    computes only, over two dicts and a date; touches no filesystem and starts nothing."""
    errs = 0
    did = decision.get("id")
    declared = {a.get("id"): a for a in _as_list(decision.get("assumptions"))
                if isinstance(a, dict) and _is_str(a.get("id"))}
    latest = {}
    if readings is not None:
        if readings.get("schema") != SCHEMA:
            errs += fail(where, "readings schema must be %r (got %r)" % (SCHEMA, readings.get("schema")))
        rdec = readings.get("decision")
        if _is_str(rdec) and _is_str(did) and rdec != did:
            errs += fail(where, "readings name decision %r but were evaluated against %r" % (rdec, did))
        for r in _as_list(readings.get("readings")):
            e = _validate_reading(r, set(declared), fail, where)
            errs += e
            if e == 0:
                aid = r["assumption"]
                prev = latest.get(aid)
                if prev is None or str(r.get("at")) >= str(prev.get("at")):
                    latest[aid] = r
    findings = []
    for aid, a in sorted(declared.items()):
        state, detail = _state_for(a, latest.get(aid), today)
        findings.append({
            "decision": did, "assumption": aid,
            "statement": a.get("statement"), "signal": a.get("signal"),
            "breach": a.get("breach"), "state": state, "detail": detail,
        })
    return findings, errs


def resolve_decision(decision_id, decisions_dir, parse, load_decision):
    """The parsed veldo.decision/v1 record whose id is decision_id under decisions_dir, or None
    when none resolves. Reads each record through the injected load_decision (decision.py's
    load_record) and matches on the decision schema and id, so a readings-shaped file is never
    mistaken for a decision."""
    d = Path(decisions_dir)
    if not d.is_dir():
        return None
    for p in sorted(d.glob("*.yaml")):
        try:
            data = load_decision(p, parse)
        except Exception:
            continue
        if isinstance(data, dict) and data.get("schema") == DECISION_SCHEMA and data.get("id") == decision_id:
            return data
    return None


def _index_readings(readings_dir, parse, fail):
    """Map decision id -> (readings dict, path) over .veldo/readings/*.yaml, reporting a
    malformed readings file, a readings file that names no decision, and an ambiguous duplicate
    binding once each. Returns (index, errs)."""
    idx = {}
    errs = 0
    d = Path(readings_dir)
    if not d.is_dir():
        return idx, errs
    for p in sorted(d.glob("*.yaml")):
        try:
            data = load_readings(p, parse)
        except TripwireError as e:
            errs += fail(str(p), str(e))
            continue
        dec = data.get("decision")
        if not _is_str(dec):
            errs += fail(str(p), "a readings file must name the decision it measures (decision: <id>)")
            continue
        if dec in idx:
            errs += fail(str(p), "more than one readings file binds to decision %r (ambiguous)" % dec)
            continue
        idx[dec] = (data, str(p))
    return idx, errs


def evaluate_tripwires(decisions_dir, readings_dir, now, parse, fail, load_decision):
    """The IN-SESSION pass, PURE over the recorded files: read the DECIDED decision records and
    the recorded readings and return (findings, errs) for every monitored assumption. Only a
    DECIDED record is monitored (a draft has no chosen foundation to watch). Adoption safe: an
    absent decisions directory stands down and returns empty. `now` is the injected in-session
    date (an ISO string, or None for today). Reads only: writes nothing and starts nothing."""
    findings = []
    errs = 0
    dd = Path(decisions_dir)
    if not dd.is_dir():
        return findings, errs
    today = _as_date(now) or date.today()
    all_decs = {}
    for p in sorted(dd.glob("*.yaml")):
        try:
            dec = load_decision(p, parse)
        except Exception:
            continue  # a malformed record is reported by decision.check_decisions_dir, not here
        if isinstance(dec, dict) and dec.get("schema") == DECISION_SCHEMA and _is_str(dec.get("id")):
            all_decs.setdefault(dec["id"], dec)
    idx, e = _index_readings(readings_dir, parse, fail)
    errs += e
    for dec_id, (_data, path) in sorted(idx.items()):
        if dec_id not in all_decs:
            errs += fail(path, "readings name decision %r which no record declares (referenced but absent)" % dec_id)
    for did, dec in sorted(all_decs.items()):
        if dec.get("status") != "decided":
            continue
        rd = idx.get(did)
        readings = rd[0] if rd else None
        where = rd[1] if rd else "decision %s (no readings recorded)" % did
        f, e2 = evaluate_readings(dec, readings, today, fail, where)
        findings += f
        errs += e2
    return findings, errs


def check_readings(path, decisions_dir, parse, fail, load_decision, now=None):
    """Single-file entry point over one readings file: validate it structurally and, when a
    decisions_dir is given, evaluate it against the decision it names. Returns STRUCTURAL errs
    only (a fired tripwire is not an error here; the gate pass decides whether firing refuses).
    Adoption safe: an absent file stands down."""
    p = Path(path)
    if not p.is_file():
        return 0
    try:
        data = load_readings(p, parse)
    except TripwireError as e:
        return fail(str(p), str(e))
    errs = 0
    if data.get("schema") != SCHEMA:
        errs += fail(str(p), "readings schema must be %r (got %r)" % (SCHEMA, data.get("schema")))
    dec_id = data.get("decision")
    if not _is_str(dec_id):
        return errs + fail(str(p), "a readings file must name the decision it measures (decision: <id>)")
    decision = resolve_decision(dec_id, decisions_dir, parse, load_decision) if decisions_dir is not None else None
    if decisions_dir is not None and decision is None:
        return errs + fail(str(p), "readings name decision %r which is malformed or absent (referenced but absent)" % dec_id)
    if decision is not None:
        _f, e = evaluate_readings(decision, data, _as_date(now) or date.today(), fail, str(p))
        errs += e
    return errs


def check_tripwires(decisions_dir, readings_dir, root, parse, fail, load_decision, now=None):
    """The gate entry point (W7). Adoption safe: an absent .veldo/decisions/ directory stands
    down and returns 0 (a repository with no decision records is byte-identically unaffected).
    Otherwise evaluate every DECIDED decision's assumptions against the recorded readings and
    FAIL CLOSED on a malformed readings set or a FIRED tripwire (a breached measured reading or a
    lapsed manual-review), surfacing each as a named finding; an approaching-breach or an
    unmonitored assumption surface as a warning without failing (there is still time to
    re-decide). Reads only: writes nothing and starts nothing."""
    dd = Path(decisions_dir)
    if not dd.is_dir():
        return 0
    findings, errs = evaluate_tripwires(dd, readings_dir, now, parse, fail, load_decision)
    for f in findings:
        if f["state"] in FIRED:
            errs += fail("tripwire %s/%s" % (f["decision"], f["assumption"]),
                         "FIRED (%s): %s; assumption: %s. Re-decide the foundation against the problem class "
                         "(W7 drafts one re-decision unit: run tripwires --draft)" % (f["state"], f["detail"], f["statement"]))
        elif f["state"] in WARN:
            print("  tripwire %s/%s: %s - %s (assumption: %s)" % (f["decision"], f["assumption"], f["state"], f["detail"], f["statement"]))
    return errs


def _render_redecision(decision_id, fired, today):
    """Render one veldo.redecision/v1 DRAFT naming the breached decision and its fired
    assumptions, for a human to promote and elaborate into a full decision record."""
    lines = [
        "# VELDO re-decision draft (veldo.redecision/v1): a foundational decision's assumption",
        "# breached its in-session tripwire, so the foundation must be re-decided against the",
        "# problem class, never today's scale. This is a DRAFT the tripwire pass wrote for a",
        "# HUMAN to promote and elaborate into a full veldo.decision/v1 record; the machine",
        "# drafts, it never decides and never re-platforms anything itself.",
        "schema: %s" % REDECISION_SCHEMA,
        "redecides: %s" % decision_id,
        "status: draft",
        "drafted_by: veldo-tripwire-pass (machine draft; a human elaborates and decides)",
        "drafted_at: %s" % today.isoformat(),
        "reason: one or more assumptions of %s breached their in-session tripwire; re-decide the foundation against the stated problem class." % decision_id,
        "breached_assumptions:",
    ]
    for f in fired:
        lines.append("  - id: %s" % f["assumption"])
        lines.append("    state: %s" % f["state"])
        lines.append("    statement: %s" % f.get("statement"))
        lines.append("    detail: %s" % f["detail"])
    return "\n".join(lines) + "\n"


def draft_redecisions(decisions_dir, readings_dir, redecisions_dir, parse, fail, load_decision, now=None):
    """Draft exactly ONE veldo.redecision/v1 DRAFT per decision that has a FIRED tripwire, for a
    HUMAN to promote (NG2: the machine drafts, never decides, never re-platforms). Homed per-repo
    under .veldo/redecisions/<decision-id>.yaml. IDEMPOTENT: an existing draft is never overwritten,
    so re-running never drafts a duplicate. This writes a file (an explicit in-session action a CLI
    or the weekly pass invokes), but starts NO process and NO thread. Returns a list of
    (decision_id, 'created' | 'exists')."""
    today = _as_date(now) or date.today()
    findings, _errs = evaluate_tripwires(Path(decisions_dir), readings_dir, now, parse, fail, load_decision)
    fired_by_dec = {}
    for f in findings:
        if f["state"] in FIRED:
            fired_by_dec.setdefault(f["decision"], []).append(f)
    out = []
    rdir = Path(redecisions_dir)
    for did in sorted(fired_by_dec):
        dst = rdir / ("%s.yaml" % did)
        if dst.exists():
            out.append((did, "exists"))
            continue
        rdir.mkdir(parents=True, exist_ok=True)
        dst.write_text(_render_redecision(did, fired_by_dec[did], today))
        out.append((did, "created"))
    return out
