#!/usr/bin/env python3
"""Normalization: the stable planning unit over raw-token ground truth (WARP-1406, W6 of PLAN-0014).

WHAT THIS IS. A token count is a terrible planning number and a fine ground truth. It moves when
the model changes, when the price changes, and when a harness changes how it counts, so a plan
sized in raw tokens is re-sized by events that have nothing to do with the work. This module
renders the Tokens of Effort corpus as a NORMALIZED POINT: one point is one reference change, and
every number a planner reads is a ratio against that reference. Raw tokens stay underneath, on the
same row, one field away (D2: both, with the point primary on planning surfaces).

THE PEG IS A CORPUS STATISTIC, NOT A HAND-PICKED FAVOURITE (D1). It is the MEDIAN standard-risk
shipped change that carries recorded spend, and the LOWER median is taken deliberately: for an even
sample the average of two changes is a change nobody made, and a peg has to be an OBSERVED change
so a reader can go and look at it. `peg` therefore names the spec it is pegged to. A founder may
replace it with a declared record (`veldo.toe_peg/v1`), and the view says which basis it used.

*** THE PROPERTY THIS MODULE EXISTS TO HOLD ***

RE-PEGGING RE-RENDERS AND STORES NOTHING. Every function here is pure over the corpus it is handed:
`resolve_peg`, `normalize` and `render_lines` read, compute and return, and NOTHING in this module
writes to the event log, to the corpus, or to a spec. The only writer is `record_shift`, which
appends ONE new file to the era ledger and is create-only. So a new peg, a new price, or a new
display unit changes what a planner sees and cannot change a single recorded actual. That is why
this is the display layer and not a conversion of the data: the recorded number is the evidence,
and evidence is not re-written when the ruler changes.

ERAS, AND WHY MIXING THEM SILENTLY IS THE FAILURE THIS PREVENTS. When a new model does more work
per token, a token stops meaning what it meant, and two numbers measured either side of that change
are not in the same unit. That is a fact about the world, so it is RECORDED: one entry per
capability shift in the era ledger (`veldo.toe_capability_shift/v1` under `.veldo/toe_eras/`),
carrying when it took effect, which model, and which direction the work per token moved. The ledger
turns into half-open intervals, every actual is stamped with the era its spend was measured in, and
a row from an era other than the peg's gets NO POINT AT ALL, with the reason naming both eras. A
change whose own spend events straddle a shift gets no era either, because that total is itself a
mixture. Per D5 normalization stays a DISPLAY concern: no cross-era conversion factor is invented
here, because a single multiplier claiming to convert one model's tokens into another's would be a
guess wearing a measurement's clothes, and it would silently rewrite history's meaning.

WHY THE LEDGER IS A RECORD DIRECTORY AND NOT A NEW ENVELOPE EVENT TYPE. `.veldo/events.py`
EVENT_TYPES is the vocabulary of things THE LOOP DID: a plan was approved, a gate ran, a spec
shipped. A model vendor shipping a better model is not something this loop did, it has no commit
and no spec, and it is effective from a date rather than emitted at an instant. It is the same
species as a decision record or a substrate declaration, and this repository already records that
species as validated yamlish under `.veldo/`. So the shift is a durable ledger entry, reviewable in
a diff, refused by name when malformed, and read through the ONE front-matter parser
(`validate.parse_yamlish`, handed in, never a second parser).

ADOPTION SAFE. No ledger directory and no peg file means the whole surface stands down: the ledger
is empty, the peg is derived if the corpus can support one and honestly absent if it cannot, and
nothing here is wired into any gate stage. A repository that never records a shift and never
records spend is byte-identically unaffected, and `report` says it has nothing rather than printing
zeros as if they were data. In THIS repository, measured by WARP-1401, spend coverage is 0 percent,
so the view stands down and says so; that is the honest output and not a defect in this module.
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCHEMA_PEG = "veldo.toe_peg/v1"
SCHEMA_SHIFT = "veldo.toe_capability_shift/v1"

# Where the records live when a repository chooses to keep them. Both are OPTIONAL, and their
# absence is the adoption-safe path rather than an error.
ERAS_DIR = ".veldo/toe_eras"
PEG_FILE = ".veldo/toe_peg.yaml"

# The era before the first recorded shift. It is named rather than left as None because "measured
# before anybody recorded a capability shift" is a real, comparable era, and a null there would
# read as "unknown", which is a different fact this module reports separately.
ERA_UNSTAMPED = "pre-ledger"

PEG_DERIVED = "median_standard_risk_shipped"
PEG_DECLARED = "declared"
PEG_RISK = "standard"

# How the work per token moved at a shift. Declared as a direction and NOT as a multiplier: a
# number claiming to convert one model's tokens into another's is a guess, and this module refuses
# to blend eras rather than pretending it can.
WORK_PER_TOKEN = {
    "increased": "the new model does MORE work per token, so later numbers read smaller",
    "decreased": "the new model does LESS work per token, so later numbers read larger",
    "unknown": "the direction was not measured; the era is still recorded so nothing is blended",
}

SHIFT_REQUIRED = ("schema", "id", "at", "model", "work_per_token")
# The key order one ledger entry is written in, so a written record and a hand-written one look the
# same in a diff. Only these keys are written; `id` doubles as the file name.
SHIFT_ORDER = ("schema", "id", "at", "model", "previous_model", "work_per_token", "note")

POINT_DIGITS = 3


def _sibling(name, relpath):
    """One sibling organ, loaded BY PATH the way every other organ here loads one, so there is no
    import cycle and no package layout to install."""
    spec = importlib.util.spec_from_file_location(name, ROOT / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _validate_module():
    """The contract module, for its ONE front-matter parser and its ONE failure reporter. Loaded
    lazily and only by the CLI: a caller that injects its own (the selftest, or any other organ)
    never pays for it, and a repository with no records never loads it at all."""
    return _sibling("veldo_validate_toe_norm", ".veldo/validate.py")


def _corpus_module():
    """The TOE corpus (WARP-1401). Reused rather than re-derived: what counts as "this event
    carried spend" is that module's decision, including which fields spend lives in."""
    return _sibling("veldo_toe_corpus_norm", ".veldo/toe_corpus.py")


def _metrics_module():
    """The metrics organ, for `parse_iso`, THE one timestamp reader in this system. A second date
    parser would be a second answer to "what is an unreadable timestamp", and that answer must stay
    None rather than becoming a zero."""
    return _sibling("veldo_metrics_toe_norm", ".veldo/metrics.py")


def read_at(value, parse_iso):
    """One timestamp as a timezone-AWARE datetime, or None when it is absent, unreadable, or
    carries no zone.

    THE ZONE REQUIREMENT IS NOT PEDANTRY, IT IS THE COMPARISON. Era boundaries are compared against
    event timestamps, and Python raises TypeError when an aware datetime meets a naive one, so a
    zoneless value would turn a mislabelled era into a crash instead of a named refusal. Every
    envelope timestamp this repository writes carries Z, so requiring it costs nothing real."""
    t = parse_iso(value)
    if t is None or t.tzinfo is None:
        return None
    return t


def _named(rec, key):
    v = rec.get(key)
    return isinstance(v, str) and v.strip() != ""


def validate_shift(rec, parse_iso):
    """Every problem with ONE capability-shift record, as a list of messages that NAME the field.
    Empty means recordable.

    Fail closed and by name, because the alternative is a ledger entry that half applies: an era
    with an unreadable boundary would silently swallow every actual on one side of it, and a
    normalized view built on that would look exactly like a working one."""
    if not isinstance(rec, dict):
        return ["a capability-shift record must be a map of fields, got %s" % type(rec).__name__]
    out = []
    for k in SHIFT_REQUIRED:
        if k not in rec:
            out.append("missing required field %r (a shift with no %s cannot place an actual in "
                       "an era, and an era nobody can place is worse than none)" % (k, k))
    if "schema" in rec and rec.get("schema") != SCHEMA_SHIFT:
        out.append("schema must be %r, got %r" % (SCHEMA_SHIFT, rec.get("schema")))
    if "id" in rec:
        if not _named(rec, "id"):
            out.append("id must be a non-empty string, got %r" % (rec.get("id"),))
        elif any(c in rec["id"] for c in "/\\ ") or rec["id"].startswith("."):
            out.append("id %r is not usable as a ledger file name: no slash, no backslash, no "
                       "space, and no leading dot" % (rec["id"],))
    if "at" in rec and read_at(rec.get("at"), parse_iso) is None:
        out.append("at must be a UTC timestamp this repository can read and compare, for example "
                   "2026-08-10T00:00:00Z, got %r" % (rec.get("at"),))
    if "model" in rec and not _named(rec, "model"):
        out.append("model must name the model the era runs on, got %r" % (rec.get("model"),))
    if "work_per_token" in rec and rec.get("work_per_token") not in WORK_PER_TOKEN:
        out.append("work_per_token must be one of %s, got %r"
                   % (sorted(WORK_PER_TOKEN), rec.get("work_per_token")))
    for k, v in sorted(rec.items()):
        if isinstance(v, str) and ("\n" in v or "\r" in v):
            out.append("field %r carries a newline, which the record format cannot round trip" % k)
    return out


def validate_peg(rec):
    """Every problem with a DECLARED peg record, as named messages. Empty means usable.

    A declared peg is the founder overriding a corpus statistic (D1), so it is validated at least
    as hard as the derivation: a peg of zero or of nothing at all would divide every displayed
    number by zero or by a guess."""
    if not isinstance(rec, dict):
        return ["a peg record must be a map of fields, got %s" % type(rec).__name__]
    out = []
    if rec.get("schema") != SCHEMA_PEG:
        out.append("schema must be %r, got %r" % (SCHEMA_PEG, rec.get("schema")))
    if rec.get("basis") != PEG_DECLARED:
        out.append("basis must be %r for a declared peg (a derived peg is not written down, it is "
                   "computed from the corpus), got %r" % (PEG_DECLARED, rec.get("basis")))
    tokens = rec.get("tokens")
    if isinstance(tokens, bool) or not isinstance(tokens, (int, float)):
        out.append("tokens must be a number, got %r" % (tokens,))
    elif tokens <= 0:
        out.append("tokens must be greater than zero: every displayed point is divided by it, "
                   "got %r" % (tokens,))
    if not _named(rec, "era"):
        out.append("era must name the era the peg was measured in, because a peg from one era does "
                   "not size work in another, got %r" % (rec.get("era"),))
    return out


def load_ledger(eras_dir, parse, report, parse_iso=None):
    """(shifts sorted by effective time, problem count) for the era ledger.

    ADOPTION SAFE: an absent directory is an empty ledger and zero problems, so a repository that
    records no shift is unaffected and nothing here is optional-but-really-required. PRESENT AND
    FAIL CLOSED: a record outside the parser subset, a malformed record, a duplicate id, or two
    shifts claiming the same instant is REFUSED through `report` (validate.fail), naming the file
    and what is wrong, and is left out of the ledger rather than half applied.

    `parse` is the ONE front-matter parser and `report` the ONE failure reporter, both handed in
    exactly as `arch.py` and `observability.py` receive them, so this module ships no second
    parser."""
    parse_iso = parse_iso or _metrics_module().parse_iso
    d = Path(eras_dir)
    if not d.is_dir():
        return [], 0
    errs, keep = 0, []
    for p in sorted(d.glob("*.yaml")):
        try:
            rec = parse(p.read_text())
        except (OSError, ValueError) as e:
            errs += report(str(p), "capability-shift record is outside the parser subset: %s" % e)
            continue
        problems = validate_shift(rec, parse_iso)
        if problems:
            for m in problems:
                errs += report(str(p), m)
            continue
        keep.append(rec)
    seen_ids, seen_at = {}, {}
    ordered = []
    for rec in sorted(keep, key=lambda r: (read_at(r["at"], parse_iso), r["id"])):
        if rec["id"] in seen_ids:
            errs += report(str(d), "duplicate shift id %r: two entries claiming one era boundary "
                                   "cannot both be it" % rec["id"])
            continue
        if rec["at"] in seen_at:
            errs += report(str(d), "shifts %r and %r both take effect at %s, so no actual at that "
                                   "instant has one era" % (seen_at[rec["at"]], rec["id"], rec["at"]))
            continue
        seen_ids[rec["id"]] = True
        seen_at[rec["at"]] = rec["id"]
        ordered.append(rec)
    return ordered, errs


def eras(shifts):
    """The ledger as ordered half-open intervals, JSON-serializable so a view can be dumped and
    compared byte for byte. The first era is always ERA_UNSTAMPED and reaches back forever; each
    shift closes the era before it and opens its own, which is named by the shift's id."""
    out = [{"era": ERA_UNSTAMPED, "model": None, "from": None, "to": None, "work_per_token": None}]
    for s in shifts:
        out[-1]["to"] = s["at"]
        out.append({"era": s["id"], "model": s["model"], "from": s["at"], "to": None,
                    "work_per_token": s["work_per_token"]})
    return out


def era_at(era_list, at, parse_iso):
    """The era one timestamp falls in, or None when the timestamp is unreadable. Half open on the
    right, so an actual recorded at the exact instant of a shift belongs to the NEW era."""
    t = read_at(at, parse_iso)
    if t is None:
        return None
    for e in era_list:
        lo = read_at(e["from"], parse_iso) if e["from"] else None
        hi = read_at(e["to"], parse_iso) if e["to"] else None
        if (lo is None or t >= lo) and (hi is None or t < hi):
            return e["era"]
    return None


def spend_ats(events, spec_id, corpus_mod):
    """The timestamps of the events that carried spend for one spec.

    WHAT COUNTS AS "CARRIED SPEND" IS NOT DECIDED HERE. Each event is put through the corpus
    module's own `spend_for`, so the field set and the numeric test stay in the one module that
    owns them; re-spelling that predicate is how two readers of one log start disagreeing."""
    return [e.get("at") for e in events
            if corpus_mod.spend_for([e], spec_id)["spend_recorded"]]


def era_of(spec_id, events, era_list, corpus_mod, parse_iso):
    """(era, reason) for one spec's recorded spend. The era is None whenever it cannot be READ,
    and the reason says which of the three ways it failed, because they are different facts:
    nothing was recorded, a timestamp is unreadable, or the spend STRADDLES a capability shift and
    the total is therefore itself a mixture of two units."""
    ats = spend_ats(events, spec_id, corpus_mod)
    if not ats:
        return None, "no recorded spend, so there is no era to read it from"
    found = [era_at(era_list, a, parse_iso) for a in ats]
    if any(f is None for f in found):
        return None, ("at least one spend event carries no readable UTC timestamp, so the era it "
                      "was measured in is unknown rather than assumed")
    uniq = sorted(set(found))
    if len(uniq) > 1:
        return None, ("spend spans %d eras (%s), so this total is itself a mixture of units and is "
                      "not normalized" % (len(uniq), ", ".join(uniq)))
    return uniq[0], None


def peg_from_corpus(corpus, events, era_list, corpus_mod, parse_iso, risk=PEG_RISK):
    """The provisional peg, DERIVED (D1): the median shipped change of the given risk tier that
    carries recorded token spend, within one era.

    THE LOWER MEDIAN, ON PURPOSE. For an even sample the arithmetic middle is a change nobody made,
    and this peg has to be a change a reader can open and inspect, so the lower of the two middle
    changes is taken and `spec` names it.

    THE LATEST ERA WITH CANDIDATES WINS, because planning happens in the era you are in; older eras
    keep their own numbers and are simply not normalized against this peg.

    An unpeggable corpus returns `pegged: False` with the reason, never a fabricated one."""
    order = {e["era"]: i for i, e in enumerate(era_list)}
    cands = []
    for r in corpus:
        if (r.get("features") or {}).get("risk") != risk:
            continue
        spend = r.get("spend") or {}
        if not spend.get("spend_recorded"):
            continue
        tokens = spend.get("tokens")
        if isinstance(tokens, bool) or not isinstance(tokens, (int, float)) or tokens <= 0:
            continue
        era, _why = era_of(r["spec"], events, era_list, corpus_mod, parse_iso)
        if era is None:
            continue
        cands.append((era, tokens, r["spec"]))
    if not cands:
        return {"schema": SCHEMA_PEG, "pegged": False, "basis": PEG_DERIVED, "risk": risk,
                "era": None, "tokens": None, "spec": None, "sample": 0,
                "reason": ("no shipped %s-risk change in the corpus carries recorded token spend "
                           "in a readable era, so there is nothing to peg to and this view stands "
                           "down rather than presenting a zero" % risk)}
    era = max({c[0] for c in cands}, key=lambda name: (order.get(name, -1), name))
    inside = sorted((t, s) for e, t, s in cands if e == era)
    tokens, spec = inside[(len(inside) - 1) // 2]
    return {"schema": SCHEMA_PEG, "pegged": True, "basis": PEG_DERIVED, "risk": risk,
            "era": era, "tokens": tokens, "spec": spec, "sample": len(inside), "reason": None}


def resolve_peg(corpus, events, era_list, corpus_mod, parse_iso, declared=None, report=None):
    """The peg in force: a valid DECLARED record if one is supplied, otherwise the derived corpus
    statistic. A declared record that is malformed is REFUSED by name and does NOT fall back to the
    derivation, because silently substituting a different peg for the one a human wrote down is how
    a planning number stops meaning what its owner thinks it means."""
    if declared is None:
        return peg_from_corpus(corpus, events, era_list, corpus_mod, parse_iso)
    problems = validate_peg(declared)
    if not problems:
        # THE ERA HAS TO BE ONE THE LEDGER DECLARES, checked here rather than in `validate_peg`
        # because only this call knows the ledger. A typo'd era name would otherwise leave every
        # single row saying "measured in another era" - named, but for the wrong reason, and a whole
        # surface of nulls traced to a spelling mistake is a bad afternoon.
        known = [e["era"] for e in era_list]
        if declared["era"] not in known:
            problems = ["era %r is not one the era ledger declares (it declares %s), so this peg "
                        "would leave every row unnormalized" % (declared["era"], known)]
    if problems:
        if report is not None:
            for m in problems:
                report(PEG_FILE, m)
        return {"schema": SCHEMA_PEG, "pegged": False, "basis": PEG_DECLARED, "risk": None,
                "era": declared.get("era") if isinstance(declared, dict) else None,
                "tokens": None, "spec": None, "sample": 0,
                "reason": "the declared peg is malformed: " + "; ".join(problems)}
    return {"schema": SCHEMA_PEG, "pegged": True, "basis": PEG_DECLARED, "risk": None,
            "era": declared["era"], "tokens": declared["tokens"],
            "spec": declared.get("spec"), "sample": None, "reason": None}


def normalize(corpus, peg, events, era_list, corpus_mod, parse_iso):
    """The view: one row per corpus record, the normalized point primary and the RAW tokens on the
    same row one field away (D2).

    PURE. The corpus handed in is read and never touched, no file is opened, and nothing is
    appended; re-running with a different peg produces a different view over identical data, which
    is the whole property this item exists to hold.

    A row gets NO POINT, with the reason named, when its spend was never recorded (a point there
    would be a confident zero), when there is no peg at all, when its era cannot be read, or when
    its era is not the peg's era."""
    rows = []
    for r in corpus:
        spend = r.get("spend") or {}
        era, why = era_of(r["spec"], events, era_list, corpus_mod, parse_iso)
        row = {"spec": r["spec"], "tokens": spend.get("tokens", 0),
               "cost_usd": spend.get("cost_usd", 0),
               "spend_recorded": bool(spend.get("spend_recorded")),
               "era": era, "points": None, "reason": None}
        if not row["spend_recorded"]:
            row["reason"] = ("no recorded spend, so a point here would be a confident zero rather "
                             "than a measurement")
        elif not peg.get("pegged"):
            row["reason"] = "no peg in force: %s" % peg.get("reason")
        elif era is None:
            row["reason"] = why
        elif era != peg.get("era"):
            row["reason"] = ("measured in era %r while the peg is in era %r: a model that does "
                             "different work per token makes these different units, so they are "
                             "reported apart rather than blended" % (era, peg.get("era")))
        else:
            row["points"] = round(row["tokens"] / float(peg["tokens"]), POINT_DIGITS)
        rows.append(row)
    return {"peg": peg, "eras": era_list, "rows": rows, "summary": summary(rows, era_list)}


def summary(rows, era_list):
    """The roll-up of one view. Both units are present, because a normalized total with no raw
    total underneath is a number nobody can audit."""
    pointed = [r for r in rows if r["points"] is not None]
    return {
        "rows": len(rows),
        "pointed": len(pointed),
        "unpointed": len(rows) - len(pointed),
        "points_total": round(sum(r["points"] for r in pointed), POINT_DIGITS),
        "tokens_total": sum(r["tokens"] for r in rows),
        "eras_present": sorted({r["era"] for r in rows if r["era"]}),
        "eras_declared": [e["era"] for e in era_list],
    }


def render_lines(view, price_per_1k_tokens=None):
    """The display: the point first, the raw tokens beside it, and a dollar column ONLY when a
    price is supplied.

    THE DOLLAR COLUMN IS DERIVED FROM RAW TOKENS AND THE POINT IS NOT. That is the design: a point
    is a ratio of tokens to tokens, so a price change moves the money and cannot move a single
    point, and neither one touches a stored actual."""
    peg = view["peg"]
    if peg.get("pegged"):
        out = ["peg: %s tokens = 1.000 pt (%s, era %s, spec %s, sample %s)"
               % (peg["tokens"], peg["basis"], peg["era"], peg["spec"], peg["sample"])]
    else:
        out = ["peg: NONE, standing down. %s" % peg.get("reason")]
    for r in view["rows"]:
        cell = "%9.3f pt" % r["points"] if r["points"] is not None else "        - pt"
        line = "%-14s %s %10d tok" % (r["spec"], cell, r["tokens"])
        if price_per_1k_tokens is not None:
            line += " %10.2f usd" % (r["tokens"] / 1000.0 * price_per_1k_tokens)
        if r["points"] is None:
            line += "  (%s)" % r["reason"]
        out.append(line)
    s = view["summary"]
    out.append("total: %s pt over %d change(s), %d raw tokens, %d row(s) with no point, eras %s"
               % (s["points_total"], s["pointed"], s["tokens_total"], s["unpointed"],
                  s["eras_present"] or "none"))
    return out


def render_shift(rec):
    """One ledger entry as yamlish text, in a fixed key order, which `validate.parse_yamlish` reads
    back unchanged. Only declared keys are written, so a stray field cannot ride along."""
    return "".join("%s: %s\n" % (k, rec[k]) for k in SHIFT_ORDER if rec.get(k) is not None)


def record_shift(rec, eras_dir, parse_iso=None):
    """Append ONE capability shift to the era ledger and return its path.

    THE ONLY WRITER IN THIS MODULE, and it writes only to the ledger: never to the event log, never
    to the corpus, never to a spec. CREATE ONLY, because the ledger is history: a shift recorded
    wrongly is corrected by recording a NEW entry, not by editing the one a past view was rendered
    against."""
    problems = validate_shift(rec, parse_iso or _metrics_module().parse_iso)
    if problems:
        raise ValueError("refusing to record a capability shift: " + "; ".join(problems))
    d = Path(eras_dir)
    d.mkdir(parents=True, exist_ok=True)
    p = d / ("%s.yaml" % rec["id"])
    if p.exists():
        raise ValueError("refusing to overwrite %s: the era ledger is append only, and a shift "
                         "that needs correcting is recorded as a NEW entry" % p)
    p.write_text(render_shift(rec))
    return p


def read_events(path=None):
    """The event log as parsed lines. A line that is not JSON is SKIPPED here and not refused,
    because the gate's own event validator (`validate.check_events`) owns that judgement and two
    organs refusing the same line differently is how one of them becomes unrunnable."""
    p = Path(path) if path else ROOT / ".veldo" / "events.jsonl"
    if not p.is_file():
        return []
    out = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def read_declared_peg(path, parse):
    """The declared peg record, or None when the repository declares none (the adoption-safe
    path). A file that exists but is outside the parser subset returns the ValueError to the
    caller rather than being swallowed into None, which would look exactly like "no peg declared".
    """
    p = Path(path)
    if not p.is_file():
        return None
    return parse(p.read_text())


def build_view(root=None, price_per_1k_tokens=None, report=None):
    """The whole view over a real repository, assembled from the shipped organs. Reads only."""
    base = Path(root) if root else ROOT
    V = _validate_module()
    corpus_mod = _corpus_module()
    parse_iso = _metrics_module().parse_iso
    report = report or V.fail
    shifts, _errs = load_ledger(base / ERAS_DIR, V.parse_yamlish, report, parse_iso)
    era_list = eras(shifts)
    events = read_events(base / ".veldo" / "events.jsonl")
    corpus = corpus_mod.build(specs_dir=base / "specs", events=events)
    try:
        declared = read_declared_peg(base / PEG_FILE, V.parse_yamlish)
    except ValueError as e:
        report(str(base / PEG_FILE), "declared peg is outside the parser subset: %s" % e)
        declared = None
    peg = resolve_peg(corpus, events, era_list, corpus_mod, parse_iso,
                      declared=declared, report=report)
    view = normalize(corpus, peg, events, era_list, corpus_mod, parse_iso)
    view["lines"] = render_lines(view, price_per_1k_tokens)
    return view


def _cli(argv):
    ap = argparse.ArgumentParser(
        prog="toe_normalize.py",
        description="Render Tokens of Effort as a normalized point pegged to a reference change, "
                    "with raw tokens underneath. Reads; never rewrites a recorded actual.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report", help="the normalized view over this repository")
    r.add_argument("--price-per-1k-tokens", type=float,
                   help="display only: adds a dollar column derived from RAW tokens; it cannot "
                        "move a single point, because a point is a ratio of tokens to tokens")
    sub.add_parser("peg", help="the peg in force and where it came from")
    sub.add_parser("eras", help="the recorded capability shifts as era intervals")
    s = sub.add_parser("record-shift", help="append one capability shift to the era ledger")
    s.add_argument("--id", required=True, help="the era this shift opens; also the file name")
    s.add_argument("--at", required=True, help="when it took effect, e.g. 2026-08-10T00:00:00Z")
    s.add_argument("--model", required=True)
    s.add_argument("--previous-model")
    s.add_argument("--work-per-token", required=True, choices=sorted(WORK_PER_TOKEN),
                   help="; ".join("%s: %s" % (k, v) for k, v in sorted(WORK_PER_TOKEN.items())))
    s.add_argument("--note")
    a = ap.parse_args(argv)
    if a.cmd == "record-shift":
        rec = {"schema": SCHEMA_SHIFT, "id": a.id, "at": a.at, "model": a.model,
               "previous_model": a.previous_model, "work_per_token": a.work_per_token,
               "note": a.note}
        try:
            print(record_shift(rec, ROOT / ERAS_DIR))
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 1
        return 0
    view = build_view(price_per_1k_tokens=getattr(a, "price_per_1k_tokens", None))
    if a.cmd == "peg":
        print(json.dumps(view["peg"], sort_keys=True))
    elif a.cmd == "eras":
        print(json.dumps(view["eras"], sort_keys=True))
    else:
        for line in view["lines"]:
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
