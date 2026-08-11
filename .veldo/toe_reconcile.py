#!/usr/bin/env python3
"""Reconciliation and the estimator's own accuracy (WARP-1405, W5 of PLAN-0014).

WHAT THIS IS. The piece that turns estimating into a learning loop instead of a forever biased
guess. Three things, in the order they depend on each other:

  1. THE RECORD. At ship, one validated record per spec holding the committed ESTIMATE, the
     recorded ACTUAL and the VARIANCE between them, beside the spec's mechanical features and
     the structural weight and token scale the estimate was built from. One file per spec at
     `.veldo/reconciliations/<SPEC-ID>.yaml`, so a spec reconciles exactly once and re-running
     the derivation is a no-op rather than a second row.
  2. THE ESTIMATOR'S OWN ACCURACY. Hit rate, mean error and a calibration curve over time,
     derived from that ledger and nothing else, so the trust owed to any estimate is a measured
     number anyone can inspect rather than a feeling.
  3. THE REFIT. The token scale the structural proxy multiplies by is a declared prior with no
     evidence behind it (WARP-1402 says so in the record itself). This module fits it from the
     accumulating history and writes a `recalibrated` layer through the estimate module's own
     seam, correcting systematic bias without touching the structure.

*** THE MEASURED FACT THAT SHAPES EVERY OUTPUT HERE ***

WARP-1401 measured this repository's corpus: 904 events, 148 shipped specs, 95.3 percent cycle
coverage and 0 PERCENT SPEND COVERAGE. `spend.py` exists as the emitter and nothing has ever
called it. So this repository has recorded zero spend, and the consequence is precise: THE
LEDGER IS EMPTY, THE ESTIMATOR HAS NO MEASURED ACCURACY YET, AND EVERY FUNCTION HERE SAYS SO
INSTEAD OF RETURNING A NUMBER. `accuracy([])` is `measured: False` with a reason, never a hit
rate of zero, because zero means it missed every time and unmeasured means it was never scored.
`curve([])` is an empty curve and not a flat line along the bottom. `fit([])` is
`fitted: False`, so no recalibrated layer exists and the estimator honestly keeps its declared
prior. The method's companion writing promises a line like "81 percent of the last 50 units in
range"; this renders exactly that shape, and today the honest rendering is that there is
nothing to render.

ERROR IS MEASURED AGAINST THE RANGE, NEVER AGAINST A MIDPOINT. An estimate here is a range and
never a point (NG6), so scoring it against the middle of its own range would invent the
forbidden point and then grade the estimator on it. The variance is therefore ZERO when the
actual lands inside the committed range, and otherwise the signed distance past the bound it
missed, as a percentage of that bound. Two facts stay separable that one number usually blurs:
how OFTEN the range held the truth, and how WRONG it was when it did not.

STRUCTURE ERROR VERSUS SCALE ERROR, the distinction the whole plan was shaped to buy. The proxy
computes `point = structural_weight_tenths * scale / 10` and WARP-1402 records both numbers in
the layer's inputs, so every record here derives the IMPLIED SCALE: the tokens per structural
unit that would have put that spec's point exactly on its actual. Implied scales AGREEING
across specs means the structure ranks work correctly and one multiplier is wrong, which is
refittable; DISAGREEING means the structure does not explain the variance and no single scale
will fix it. `fit` reports the fitted scale and the DISPERSION it was fitted from, and never
labels the structure right or wrong, because that threshold is nobody's measurement. Instead
the refitted layer's range IS the observed envelope of implied scales, so disagreement widens
the range rather than hiding in it.

THE REFIT IS SCORED OUT OF SAMPLE. Fitting on a set and then scoring that same set measures
nothing: the fit has already seen the answers. `holdout` refits for each record from all the
OTHERS and scores that record against the range it would have been given, and `compare` puts
the ledger's own accuracy (the prior estimator) beside it.

WHY A NEW LAYER AND NOT A NEW RANGE. The committed range is the ENVELOPE of its layers and an
envelope only widens (WARP-1402 AC2, which is NG6 in arithmetic). So nothing here narrows a
range behind a caller's back: this module contributes a `recalibrated` layer from the
vocabulary WARP-1402 already declares, and a caller who judges the refit strong enough to
REPLACE the prior says so explicitly (`supersede`).

ADVISORY, AND NEVER A BLOCKER (PLAN-0014 C3, NG1). No gate stage calls this module. A spec with
no reconciliation is ordinary and a MALFORMED one beside a spec does not invalidate the spec.
With no records present every reader stands down silently and creates nothing. Reading is pure:
nothing here writes to the event log, the corpus, a spec or an estimate. The only writer is
`write_record`, create-only unless a caller explicitly asks to replace, because a variance
quietly rewritten afterwards is a scoreboard rather than a measurement.

NO CLOCK, NO SUBPROCESS, NO NETWORK. Every date is passed in, so one ledger renders the same
bytes on any machine on any day, and this module names no subprocess, socket or urllib import
(NG5). The spend predicate is toe_corpus's, the record vocabulary and the bounds and rounding
rules are estimate.py's, the parser and failure reporter are validate.py's, and the era stamp is
handed in: nothing here is a second spelling of a decision another module already made.
"""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

SCHEMA = "veldo.toe_reconciliation/v1"
ROOT = Path(__file__).resolve().parent.parent
RECORDS_DIR = ".veldo/reconciliations"

# THE OUTCOME VOCABULARY, and it is DERIVED from the three numbers rather than asserted, so a
# record cannot file itself under a kinder outcome than its own arithmetic supports.
OUTCOMES = {
    "below": "the actual came in under the committed low",
    "in_range": "the actual landed inside the committed range: the only outcome that is a hit",
    "above": "the actual came in over the committed high",
}
HIT = "in_range"

# WHERE THE ACTUAL CAME FROM. Required, for the reason spend.py gives about its own basis
# field: a number with no stated provenance is one a later analysis will over-trust.
ACTUAL_SOURCES = {
    "corpus": "summed from the recorded event stream by toe_corpus.spend_for, which is the "
              "ONE reader of what an event's spend is",
    "supplied": "handed to the reconciler by its caller (a fixture, or a harness outside this "
                "repository) rather than read from the log",
}

# WHICH WAY THE ESTIMATOR IS WRONG WHEN IT IS WRONG. A mean error above zero means actuals
# landed above the committed highs, so the ESTIMATOR was too low.
BIAS = {
    "under_estimating": "actuals land above the committed range more than below it",
    "over_estimating": "actuals land below the committed range more than above it",
    "balanced": "the mean error is zero: the misses cancel, which is not the same as no misses",
}

# The trailing window the accuracy line is quoted over, so a long-stale history cannot flatter
# a currently drifting estimator. 50 is a declared choice, not a measurement, and every
# accuracy block reports the window it used and how many records actually fell inside it.
WINDOW = 50

# The smallest set a scale may be fitted from. Below this a median is one or two numbers
# wearing a statistic's clothes and a dispersion figure is undefined, so `fit` stands down and
# says so rather than producing a confident multiplier from a single data point. The same
# argument judgment_load.py's MIN_POPULATION makes, for the same reason.
MIN_REFIT_SAMPLE = 3

# THE FLOOR UNDER A FITTED RANGE, and it exists because a measured range can be dishonestly
# narrow. The refitted range is the observed envelope of implied scales, so a handful of
# records that happen to AGREE EXACTLY would produce a range one rounding step wide: an
# estimator claiming a change to within a tenth of a percent because three earlier changes
# agreed. That is false precision arriving through the back door, and NG6 refuses it however it
# arrives. So a fitted range spans at least this much above its own low, widened symmetrically
# in ratio about the fitted scale (HALF_SPREAD_PCT each way, which is 56 percent of spread and
# clears the floor). Both numbers are DECLARED, exactly as estimate.py's SPREAD_PCT is
# declared, and a layer records whether the floor was applied so a reader can see that its
# range is wider than the sample looked.
MIN_FITTED_SPREAD_PCT = 50
HALF_SPREAD_PCT = 125

# The record's declared key set. An unknown key is REFUSED BY NAME rather than ignored, the
# same posture veldo.estimate/v1 takes, so a later reader cannot be handed a field it does not
# know about while every existing reader keeps working and means something different.
RECORD_REQUIRED = ("schema", "spec", "reconciled_at", "unit", "estimate_committed_at",
                   "estimate_calibration", "estimate_low", "estimate_high", "actual",
                   "actual_source", "outcome", "error_pct")
# THE FEATURES the estimate was made from, copied off the estimate's own structural-proxy layer
# so the ledger is a feature-to-actual dataset on its own terms (PLAN-0014 O3: "the variance is
# stored with the spec's features"). ALL OR NONE: a half-present block is refused, because a
# later feature-level analysis would silently skip a record that looks complete.
FEATURE_KEYS = ("acceptance_criteria", "risk", "protected_touch", "regression_surface",
                "expected_review_cycles")
# THE DECOMPOSITION that separates a wrong structure from a wrong scale. Also all or none, and
# for a sharper reason: `fit` reads exactly these, so a record missing one of them contributes
# nothing to a refit and has to say so by being refused rather than by being quietly dropped.
DECOMP_KEYS = ("structural_weight_tenths", "declared_scale", "implied_scale", "scale_error_pct")
RECORD_OPTIONAL = ("era", "note") + FEATURE_KEYS + DECOMP_KEYS
RECORD_ORDER = ("schema", "spec", "reconciled_at", "unit", "estimate_committed_at",
                "estimate_calibration", "estimate_low", "estimate_high", "actual",
                "actual_source", "era", "outcome", "error_pct") + FEATURE_KEYS \
               + DECOMP_KEYS + ("note",)

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_MODS = {}


def _mod(rel, name):
    """One of this engine's modules, loaded from THIS engine's location, cached. The same
    importlib shape estimate.py and cost_to_change.py use, for the same reason: reuse the one
    implementation instead of spelling it again, and no package layout to install."""
    if name not in _MODS:
        spec = importlib.util.spec_from_file_location(name, ROOT / rel)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MODS[name] = mod
    return _MODS[name]


def _validate():
    """The ONE parser and the ONE failure reporter (.veldo/validate.py)."""
    return _mod(".veldo/validate.py", "veldo_validate_toe_reconcile")


def _estimate():
    """The estimate record and the structural proxy (WARP-1402). EVERYTHING about an estimate
    comes from here: the unit vocabulary, the layer and basis vocabularies, the bounds rule, the
    rounding step and the record assembler. This module adds a layer to that vocabulary and
    never widens it, and it does not own a second opinion about what a valid estimate is."""
    return _mod(".veldo/estimate.py", "veldo_estimate_toe_reconcile")


def _corpus():
    """The actuals corpus (WARP-1401), for the ONE definition of what counts as recorded
    spend. Re-spelling that predicate here is how two readers of one log start disagreeing."""
    return _mod(".veldo/toe_corpus.py", "veldo_toe_corpus_toe_reconcile")


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


# ---------------------------------------------------------------------------------------
# The arithmetic. Integer only, so the same ledger produces identical bytes and identical
# numbers on every machine, and every derived field the validator recomputes is recomputed
# through THESE functions rather than through a second spelling of the same formula.
# ---------------------------------------------------------------------------------------

def _pct(numer, denom):
    """One signed integer percentage, truncated toward zero. Raises on a non-positive
    denominator rather than returning a number nobody can interpret."""
    if not _is_int(numer) or not _is_int(denom):
        raise ValueError("a percentage needs two integers, got %r and %r" % (numer, denom))
    if denom <= 0:
        raise ValueError("cannot take a percentage of %r: the denominator is the bound the "
                         "actual missed, and a non-positive bound is not a bound" % (denom,))
    sign = -1 if numer < 0 else 1
    return sign * (abs(numer) * 100 // denom)


def _mean_int(values):
    """The mean of some integers, rounded half away from zero, as an integer. Percentages
    carried to five decimal places would be false precision over a handful of records; the
    values themselves stay on every record for anyone who wants to recompute this."""
    if not values:
        raise ValueError("no values to average: an empty mean is not zero, it is unmeasured")
    s, n = sum(values), len(values)
    sign = -1 if s < 0 else 1
    return sign * ((abs(s) * 2 + n) // (2 * n))


def outcome_of(low, high, actual):
    """Which of the three declared outcomes one actual is, against one committed range."""
    if actual < low:
        return "below"
    if actual > high:
        return "above"
    return HIT


def error_pct_of(low, high, actual):
    """THE VARIANCE: zero inside the range, otherwise the signed miss past the bound it missed,
    as a percentage of that bound.

    MEASURED AGAINST THE RANGE AND NEVER AGAINST A MIDPOINT. The schema this scores has no
    point estimate (NG6), so grading it against the middle of its own range would invent the
    forbidden point and then hold the estimator to it. A positive error means the actual was
    above the committed high, which means the ESTIMATE WAS TOO LOW."""
    if actual > high:
        return _pct(actual - high, high)
    if actual < low:
        return -_pct(low - actual, low)
    return 0


def implied_scale_of(actual, weight_tenths):
    """The token scale that would have put this spec's structural point exactly on its actual.

    THIS IS THE WHOLE SEPARATION OF STRUCTURE FROM SCALE. WARP-1402's proxy computes
    `point = weight_tenths * scale / 10` and records both numbers, so inverting it against the
    actual gives the scale that WOULD have been right for this one change. Across records those
    implied scales agreeing means the structure ranks work correctly and one multiplier is
    wrong; disagreeing means the structure itself does not explain the variance."""
    if not _is_int(actual) or actual <= 0:
        raise ValueError("an implied scale needs a positive integer actual, got %r" % (actual,))
    if not _is_int(weight_tenths) or weight_tenths <= 0:
        raise ValueError("an implied scale needs a positive structural weight, got %r"
                         % (weight_tenths,))
    return (actual * 10 + weight_tenths // 2) // weight_tenths


# ---------------------------------------------------------------------------------------
# The record: validation, rendering, reading, writing.
# ---------------------------------------------------------------------------------------

def validate_record(rec, spec_id=None):
    """Every problem with a reconciliation record, as a list of strings that NAME what is
    wrong. Empty means the record is valid.

    FAIL CLOSED. An unrecognised key, an unrecognised vocabulary value, a half-present block
    and a derived field that does not follow from the record's own numbers are all refusals,
    never silently ignored input.

    THE DERIVED FIELDS ARE RECOMPUTED RATHER THAN TRUSTED, which is what makes the ledger
    unable to lie about itself: `outcome`, `error_pct`, `implied_scale` and `scale_error_pct`
    are all recomputed from `estimate_low`, `estimate_high`, `actual` and the structural weight,
    so a variance edited to look better after the fact is refused by name.

    `spec_id`, when given, is the id the record is expected to be for (the filename's stem
    where records are read from disk), so a record filed under the wrong name is caught."""
    out = []
    if not isinstance(rec, dict):
        return ["a reconciliation record must be a mapping, got %s" % type(rec).__name__]
    EST = _estimate()

    unknown = sorted(set(rec) - set(RECORD_REQUIRED) - set(RECORD_OPTIONAL))
    if unknown:
        out.append("unknown key(s) %s: %s declares %s (required) and %s (optional), and an "
                   "unknown key is refused rather than ignored so a later item extends this "
                   "ledger deliberately"
                   % (unknown, SCHEMA, list(RECORD_REQUIRED), list(RECORD_OPTIONAL)))
    for k in RECORD_REQUIRED:
        if k not in rec:
            out.append("missing required key %r" % k)

    if "schema" in rec and rec["schema"] != SCHEMA:
        out.append("schema must be %r, got %r" % (SCHEMA, rec.get("schema")))
    if "spec" in rec and not (isinstance(rec["spec"], str) and rec["spec"].strip()):
        out.append("spec must name the spec this reconciliation is for, got %r"
                   % (rec.get("spec"),))
    if spec_id is not None and rec.get("spec") != spec_id:
        out.append("this record is filed as %r but says spec: %r; the filename is the key, so a "
                   "spec cannot be reconciled twice under two names"
                   % (spec_id, rec.get("spec")))
    if "unit" in rec and rec["unit"] not in EST.UNITS:
        out.append("unit must be one of %s, the unit the estimate was committed in (raw tokens "
                   "are the recorded ground truth), got %r" % (sorted(EST.UNITS), rec["unit"]))
    if "actual_source" in rec and rec["actual_source"] not in ACTUAL_SOURCES:
        out.append("actual_source must be one of %s (a number with no stated provenance is one a "
                   "later analysis will over-trust), got %r"
                   % (sorted(ACTUAL_SOURCES), rec.get("actual_source")))
    if "estimate_calibration" in rec and rec["estimate_calibration"] not in EST.CALIBRATIONS:
        out.append("estimate_calibration must be one of %s, copied from the estimate this record "
                   "scores, got %r" % (list(EST.CALIBRATIONS), rec.get("estimate_calibration")))
    for k in ("reconciled_at", "estimate_committed_at"):
        if k in rec and not (isinstance(rec[k], str) and DATE_RE.match(rec[k])):
            out.append("%s must be a YYYY-MM-DD date, got %r" % (k, rec.get(k)))
    if isinstance(rec.get("reconciled_at"), str) and isinstance(rec.get("estimate_committed_at"),
                                                               str) \
            and DATE_RE.match(rec["reconciled_at"]) \
            and DATE_RE.match(rec["estimate_committed_at"]) \
            and rec["reconciled_at"] < rec["estimate_committed_at"]:
        out.append("reconciled_at %s is BEFORE estimate_committed_at %s: an estimate committed "
                   "after the work it sizes was already reconciled is not a commitment, and "
                   "scoring one would flatter the estimator with hindsight"
                   % (rec["reconciled_at"], rec["estimate_committed_at"]))
    if "era" in rec and not (isinstance(rec["era"], str) and rec["era"].strip()):
        out.append("era, when present, must name the era this actual was measured in, got %r"
                   % (rec.get("era"),))
    out.extend(_note_problems(rec.get("note"), "the record's note"))

    # THE COMMITTED RANGE IS CHECKED BY THE ONE BOUNDS RULE, estimate.py's, rather than by a
    # second spelling of it here: integers, positive, and low STRICTLY below high, so a POINT
    # estimate cannot be smuggled into a reconciliation either.
    if "estimate_low" in rec or "estimate_high" in rec:
        bounds = {}
        for src, dst in (("estimate_low", "low"), ("estimate_high", "high")):
            if src in rec:
                bounds[dst] = rec[src]
        out.extend(EST._bounds_problems(
            bounds, "the reconciled estimate range (estimate_low, estimate_high)"))
    if "actual" in rec and (not _is_int(rec["actual"]) or rec["actual"] <= 0):
        out.append("actual must be a positive integer number of %s: a reconciliation never "
                   "rounds, rescales or defaults a recorded actual, and a zero actual is the "
                   "absence of a measurement rather than a cheap change"
                   % (rec.get("unit") or "units"))

    out.extend(_group_problems(rec, FEATURE_KEYS, "the features block",
                              "a later feature-level analysis would silently skip a record "
                              "that looks complete"))
    out.extend(_group_problems(rec, DECOMP_KEYS, "the structure-and-scale block",
                              "fit() reads exactly these keys, so a record missing one "
                              "contributes nothing to a refit and must say so"))
    out.extend(_feature_value_problems(rec, EST))
    out.extend(_derived_problems(rec))
    return out


def _group_problems(rec, keys, where, why):
    """A declared block is ALL PRESENT OR ALL ABSENT. Half a block is refused, never
    half-applied, because every reader of it would then have to guess."""
    present = [k for k in keys if k in rec]
    if present and len(present) != len(keys):
        return ["%s is half present: %s given, %s missing. It is all or none, because %s"
                % (where, present, [k for k in keys if k not in rec], why)]
    return []


def _feature_value_problems(rec, EST):
    """The feature values, against the vocabularies the ESTIMATOR declares. The risk tiers come
    from estimate.DEFAULT_REVIEWS and the yes/no pair from estimate.YES and estimate.NO, so
    there is no second risk table and no second spelling of a boolean this format cannot hold."""
    out = []
    for k in ("acceptance_criteria", "regression_surface", "expected_review_cycles",
              "structural_weight_tenths", "declared_scale", "implied_scale"):
        if k in rec and (not _is_int(rec[k]) or rec[k] < 0):
            out.append("%s must be a non-negative integer, got %r" % (k, rec[k]))
    for k in ("expected_review_cycles", "structural_weight_tenths", "declared_scale",
              "implied_scale"):
        if k in rec and _is_int(rec[k]) and rec[k] == 0:
            out.append("%s must be positive: a zero there is a division nobody can do or a "
                       "structure with no work in it" % k)
    if "risk" in rec and rec["risk"] not in EST.DEFAULT_REVIEWS:
        out.append("risk %r is not one of the tiers the estimator declares (%s)"
                   % (rec["risk"], sorted(EST.DEFAULT_REVIEWS)))
    if "protected_touch" in rec and rec["protected_touch"] not in (EST.YES, EST.NO):
        out.append("protected_touch must be %r or %r (this record format has no boolean, so a "
                   "true would be stored as the WORD true while looking like a value), got %r"
                   % (EST.YES, EST.NO, rec["protected_touch"]))
    if "scale_error_pct" in rec and not _is_int(rec["scale_error_pct"]):
        out.append("scale_error_pct must be an integer percentage, got %r"
                   % (rec["scale_error_pct"],))
    return out


def _derived_problems(rec):
    """The four DERIVED fields, recomputed from the record's own numbers instead of trusted.
    This is the pair of checks that makes a variance impossible to edit after the fact."""
    out = []
    if "outcome" in rec and rec["outcome"] not in OUTCOMES:
        out.append("outcome must be one of %s, got %r" % (sorted(OUTCOMES), rec.get("outcome")))
    lo, hi, actual = rec.get("estimate_low"), rec.get("estimate_high"), rec.get("actual")
    if _is_int(lo) and _is_int(hi) and _is_int(actual) and 0 < lo < hi and actual > 0:
        want = outcome_of(lo, hi, actual)
        if rec.get("outcome") != want:
            out.append("outcome says %r but %d against the range %d..%d is %r: the outcome is "
                       "DERIVED from the three numbers and a record may not file itself under a "
                       "kinder one" % (rec.get("outcome"), actual, lo, hi, want))
        want_err = error_pct_of(lo, hi, actual)
        if rec.get("error_pct") != want_err:
            out.append("error_pct says %r but the variance of %d against %d..%d is %d percent: "
                       "it is DERIVED, measured against the bound the actual missed and never "
                       "against a midpoint this schema refuses to have"
                       % (rec.get("error_pct"), actual, lo, hi, want_err))
    weight, declared = rec.get("structural_weight_tenths"), rec.get("declared_scale")
    if _is_int(weight) and weight > 0 and _is_int(actual) and actual > 0:
        want_implied = implied_scale_of(actual, weight)
        if rec.get("implied_scale") != want_implied:
            out.append("implied_scale says %r but the scale that would have put a structural "
                       "weight of %d exactly on an actual of %d is %d: it is DERIVED, and it is "
                       "the number a refit is fitted from"
                       % (rec.get("implied_scale"), weight, actual, want_implied))
        elif _is_int(declared) and declared > 0:
            want_serr = _pct(declared - want_implied, want_implied)
            if rec.get("scale_error_pct") != want_serr:
                out.append("scale_error_pct says %r but the declared scale %d against the "
                           "implied scale %d is %d percent: it is DERIVED, and it is how a wrong "
                           "SCALE is told apart from a wrong STRUCTURE"
                           % (rec.get("scale_error_pct"), declared, want_implied, want_serr))
    return out


def _note_problems(note, where):
    if note is None:
        return []
    if not isinstance(note, str) or not note.strip():
        return ["%s must be a non-empty single-line string, got %r" % (where, note)]
    return []


def render_record(rec):
    """The record as the front-matter subset, in a declared key order so one record is always
    the same bytes. `validate.parse_yamlish` of this returns the record.

    THE SCALAR RENDERER IS estimate.py's, handed the same refusals: a value the ONE parser
    would read back as something else is refused HERE rather than written and discovered by
    whoever reads the ledger next. A second renderer would be a second answer to what this
    format can hold."""
    problems = validate_record(rec)
    if problems:
        raise ValueError("refusing to render an invalid reconciliation record: "
                         + "; ".join(problems))
    EST = _estimate()
    lines = []
    for k in RECORD_ORDER:
        if k not in rec:
            continue
        lines.append("%s: %s" % (k, EST._render_scalar(rec[k], "record key %r" % k)))
    return "\n".join(lines) + "\n"


def parse_record(text):
    """One record's text through the ONE parser. A parse failure is a refusal naming the
    parser's own line hint, never a silently empty record."""
    try:
        rec = _validate().parse_yamlish(text)
    except ValueError as e:
        raise ValueError("reconciliation record is outside the front-matter parser subset: %s"
                         % e)
    if not isinstance(rec, dict):
        raise ValueError("reconciliation record must be a mapping, got %s" % type(rec).__name__)
    return rec


def read_record(path, spec_id=None):
    """One record from disk, fail closed. Raises ValueError naming every problem."""
    path = Path(path)
    if spec_id is None:
        spec_id = path.stem
    rec = parse_record(path.read_text())
    problems = validate_record(rec, spec_id=spec_id)
    if problems:
        raise ValueError("refusing the reconciliation record at %s: %s"
                         % (path, "; ".join(problems)))
    return rec


def records_dir(root=None):
    return (Path(root) if root else ROOT) / RECORDS_DIR


def load_dir(dirpath=None, root=None):
    """Every valid record present, keyed by spec id, plus the problems found.

    ADOPTION SAFE: an absent directory is not an error, it is a repository that does not use
    this, and it yields ({}, []) without creating anything. FAIL CLOSED: a record that is
    present and malformed is NOT silently dropped from the ledger, it is reported by name, so
    an accuracy number can never be computed over a quietly smaller set than the one on disk."""
    d = Path(dirpath) if dirpath else records_dir(root)
    if not d.is_dir():
        return {}, []
    out, problems = {}, []
    for p in sorted(d.glob("*.yaml")):
        try:
            rec = read_record(p)
        except (ValueError, OSError) as e:
            problems.append(str(e))
            continue
        if rec["spec"] in out:
            problems.append("two records claim spec %r: %s" % (rec["spec"], p))
            continue
        out[rec["spec"]] = rec
    return out, problems


def record_for(spec_id, dirpath=None, root=None):
    """The reconciliation for one spec, or None. None is an ordinary answer."""
    d = Path(dirpath) if dirpath else records_dir(root)
    p = d / ("%s.yaml" % spec_id)
    if not p.is_file():
        return None
    return read_record(p, spec_id=spec_id)


def write_record(rec, dirpath=None, root=None, replace=False):
    """Write one record and return (path, action) where action is `created` or `unchanged`.

    IDEMPOTENT BY BYTES: re-deriving the same reconciliation and writing it again is a no-op
    that reports `unchanged`, which is what makes "exactly once per shipped spec" hold without
    anybody tracking whether the pass already ran.

    CREATE ONLY OTHERWISE: a record whose bytes DIFFER from the one on disk is refused by name
    unless replace is asked for explicitly. A variance that quietly rewrites itself when the
    actual moves is a scoreboard, not a measurement, and the whole point of this ledger is that
    the estimator cannot improve its own grade after the fact."""
    problems = validate_record(rec)
    if problems:
        raise ValueError("refusing to write an invalid reconciliation record: "
                         + "; ".join(problems))
    text = render_record(rec)
    d = Path(dirpath) if dirpath else records_dir(root)
    p = d / ("%s.yaml" % rec["spec"])
    if p.exists():
        existing = p.read_text()
        if existing == text:
            return p, "unchanged"
        if not replace:
            raise ValueError("%s already carries a reconciliation for %s whose bytes DIFFER from "
                             "the one now derived: refusing to rewrite a recorded variance. If "
                             "the actual was genuinely corrected, say so explicitly (replace), "
                             "so the change is a decision in a diff rather than a silent regrade"
                             % (p, rec["spec"]))
    d.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p, "created"


# ---------------------------------------------------------------------------------------
# The reconciliation itself: an estimate, an actual, and what fell between them.
# ---------------------------------------------------------------------------------------

def build_record(spec_id, at, estimate, actual, actual_source="corpus", era=None, note=None):
    """One reconciliation record from one committed estimate and one recorded actual.

    THE ESTIMATE IS VALIDATED BEFORE IT IS SCORED, through estimate.validate_record, so a
    broken estimate cannot be graded into a number that looks like a measurement.

    The features and the structure-and-scale block are copied from the estimate's own
    structural_proxy layer when it carries one. An estimate with no such layer (an
    analogy-only or sizing-only record) still reconciles: it gets the estimate, the actual and
    the variance, and simply contributes nothing to a scale refit, which the ledger states by
    the absence of the block rather than by a zero."""
    EST = _estimate()
    problems = EST.validate_record(estimate, spec_id=spec_id)
    if problems:
        raise ValueError("refusing to reconcile %s against an invalid estimate: %s"
                         % (spec_id, "; ".join(problems)))
    if not _is_int(actual) or actual <= 0:
        raise ValueError("refusing to reconcile %s: the actual is %r, and a reconciliation never "
                         "rounds, rescales or defaults a recorded actual. An unmeasured change "
                         "has no reconciliation, which is a different fact from a cheap one"
                         % (spec_id, actual))
    if actual_source not in ACTUAL_SOURCES:
        raise ValueError("unknown actual_source %r: declared sources are %s"
                         % (actual_source, sorted(ACTUAL_SOURCES)))
    lo, hi = estimate["low"], estimate["high"]
    rec = {"schema": SCHEMA, "spec": spec_id, "reconciled_at": at, "unit": estimate["unit"],
           "estimate_committed_at": estimate["committed_at"],
           "estimate_calibration": estimate["calibration"],
           "estimate_low": lo, "estimate_high": hi, "actual": actual,
           "actual_source": actual_source,
           "outcome": outcome_of(lo, hi, actual), "error_pct": error_pct_of(lo, hi, actual)}
    if era:
        rec["era"] = era
    proxy = next((l for l in estimate["layers"] if l.get("layer") == "structural_proxy"), None)
    ins = (proxy or {}).get("inputs") or {}
    if all(k in ins for k in ("acceptance_criteria", "risk", "protected_touch",
                              "regression_surface", "expected_review_cycles")):
        for k in FEATURE_KEYS:
            rec[k] = ins[k]
    weight, scale = ins.get("structural_weight_tenths"), ins.get("tokens_per_structural_unit")
    if _is_int(weight) and weight > 0 and _is_int(scale) and scale > 0:
        implied = implied_scale_of(actual, weight)
        rec["structural_weight_tenths"] = weight
        rec["declared_scale"] = scale
        rec["implied_scale"] = implied
        rec["scale_error_pct"] = _pct(scale - implied, implied)
    if note:
        rec["note"] = note
    problems = validate_record(rec)
    if problems:
        raise ValueError("refusing to build a reconciliation record: " + "; ".join(problems))
    return rec


def actual_from_corpus(corpus_record):
    """(actual, reason) for one corpus record: the recorded token total, or None with the reason
    it is not usable.

    WHAT COUNTS AS RECORDED SPEND IS NOT DECIDED HERE. `spend_recorded` is toe_corpus's own
    flag, and the distinction it exists for is exactly the one that matters at this seam: a sum
    of zero because nothing was spent and a sum of zero because nothing was ever EMITTED are
    different facts, and scoring an estimator against the second one is scoring it against
    nothing while looking like a measurement."""
    spend = corpus_record.get("spend") or {}
    if not spend.get("spend_recorded"):
        return None, ("no spend was ever recorded for this shipped change, so there is no actual "
                      "to reconcile against; a zero here would score the estimator against a "
                      "number nobody measured")
    tokens = spend.get("tokens")
    if not _is_int(tokens) or tokens <= 0:
        return None, ("the recorded spend carries %r tokens, which is not a positive integer "
                      "token count; a reconciliation refuses rather than rounding a recorded "
                      "actual" % (tokens,))
    return tokens, None


def pair(estimates, corpus, at, actual_source="corpus", era_of=None):
    """(records, standdowns) for a whole repository: every committed estimate matched to the
    shipped actual for the same spec.

    DETERMINISTIC AND PURE. It reads the two collections it is handed, opens no file, spawns
    nothing and reads no clock (`at` is passed in), so the same inputs give the same records in
    the same order every run. That is what makes writing them idempotent.

    EVERY UNRECONCILED ESTIMATE IS EXPLAINED, never dropped. A standdown is a row with a
    reason: not shipped yet, no spend recorded, an actual that is not a token count, or an
    estimate the estimate module itself refuses. An estimator's accuracy that silently omitted
    the changes it could not score would be a hit rate over the subset that happened to work.

    `era_of` is an optional callable from spec id to an era name, so a repository that keeps
    WARP-1406's era ledger can stamp each actual with the model identity it was measured under
    (D5) WITHOUT this module importing that organ or inventing an era of its own."""
    by_spec = {}
    for r in corpus:
        if isinstance(r, dict) and isinstance(r.get("spec"), str):
            by_spec[r["spec"]] = r
    records, standdowns = [], []
    for spec_id in sorted(estimates):
        est = estimates[spec_id]
        cr = by_spec.get(spec_id)
        if cr is None:
            standdowns.append({"spec": spec_id, "reason":
                               "no shipped actuals record in the corpus: a reconciliation "
                               "happens at ship, so an estimate for work not yet shipped is a "
                               "pending row and not a miss"})
            continue
        actual, why = actual_from_corpus(cr)
        if actual is None:
            standdowns.append({"spec": spec_id, "reason": why})
            continue
        try:
            records.append(build_record(spec_id, at, est, actual, actual_source=actual_source,
                                        era=era_of(spec_id) if era_of else None))
        except ValueError as e:
            standdowns.append({"spec": spec_id, "reason": str(e)})
    return records, standdowns


def write_all(records, dirpath=None, root=None):
    """Write a set of records, reporting what each one did. Returns
    (created, unchanged, refused) where refused is a list of messages.

    THE IDEMPOTENCE IS THE POINT: running the pass twice over an unchanged repository creates
    nothing the second time and refuses nothing, so "exactly one reconciliation per shipped
    estimated spec" needs no bookkeeping to hold."""
    created, unchanged, refused = [], [], []
    for rec in records:
        try:
            p, action = write_record(rec, dirpath=dirpath, root=root)
        except (ValueError, OSError) as e:
            refused.append(str(e))
            continue
        (created if action == "created" else unchanged).append(str(p))
    return created, unchanged, refused


# ---------------------------------------------------------------------------------------
# The estimator's own accuracy: the number that says how much any estimate is worth.
# ---------------------------------------------------------------------------------------

def ordered(records):
    """The ledger in reconciliation order, ties broken by spec id so the order is total and the
    curve below is reproducible."""
    return sorted(records, key=lambda r: (r.get("reconciled_at") or "", r.get("spec") or ""))


def _scored(records):
    """The (outcome, error_pct, width_pct) triples, refusing a record that carries less than that
    rather than treating it as a hit. Fail closed: a record this function cannot read is a defect
    in the caller, not a row to skip.

    THE WIDTH IS IN HERE BECAUSE A HIT RATE ALONE IS GAMEABLE. An estimator that answered "between
    one token and a billion" would hit every time and report zero error, so the width of the range
    it hit with belongs on the same line as the hit rate, always."""
    out = []
    for r in records:
        o, e = r.get("outcome"), r.get("error_pct")
        lo, hi = r.get("estimate_low"), r.get("estimate_high")
        if o not in OUTCOMES or not _is_int(e) or not (_is_int(lo) and _is_int(hi) and 0 < lo < hi):
            raise ValueError("cannot score %r: outcome %r, error_pct %r and the range %r..%r are "
                             "what an accuracy number is made of, and a record missing any of "
                             "them would be counted as something" % (r.get("spec"), o, e, lo, hi))
        out.append((o, e, _pct(hi - lo, lo)))
    return out


def accuracy(records, window=None):
    """The estimator's measured accuracy over a ledger, or an honest statement that it has none.

    AN EMPTY LEDGER IS NOT A SCORE OF ZERO. With no records this returns `measured: False` and
    the reason, with every figure None. A hit rate of zero means the estimator missed every
    time; an unmeasured estimator has not been scored at all, and printing the first when the
    second is true is the exact dishonesty this whole item is built against. In THIS repository
    that is not a hypothetical: WARP-1401 measured 0 percent spend coverage, so this is the
    branch that runs today.

    `window`, when given, quotes the figures over the LAST that many records, which is the
    shape of the line the method's companion writing promises ("N percent of the last 50 units
    in range"). The window and the number of records that actually fell inside it are both
    reported, so a window wider than the history cannot read as a fuller one."""
    rows = ordered(records)
    total = len(rows)
    if window is not None:
        if not _is_int(window) or window <= 0:
            raise ValueError("a window must be a positive integer number of records, got %r"
                             % (window,))
        rows = rows[-window:]
    out = {"measured": False, "n": len(rows), "ledger": total, "window": window,
           "counts": {k: 0 for k in sorted(OUTCOMES)}, "hit_rate_pct": None,
           "mean_error_pct": None, "mean_abs_error_pct": None, "worst_error_pct": None,
           "mean_width_pct": None, "bias": None, "first": None, "last": None, "reason": ""}
    if not rows:
        out["reason"] = ("no reconciliation records: the estimator has NO MEASURED ACCURACY yet, "
                         "which is a fact about the ledger rather than a hit rate of zero (a "
                         "hit rate of zero would mean it missed every time)")
        return out
    triples = _scored(rows)
    for o, _e, _w in triples:
        out["counts"][o] += 1
    errs = [e for _o, e, _w in triples]
    hits = out["counts"][HIT]
    out["measured"] = True
    out["hit_rate_pct"] = (hits * 100 * 2 + len(rows)) // (2 * len(rows))
    out["mean_error_pct"] = _mean_int(errs)
    out["mean_abs_error_pct"] = _mean_int([abs(e) for e in errs])
    out["worst_error_pct"] = max(errs, key=abs)
    # THE WIDTH THE HIT RATE WAS BOUGHT WITH, always beside it, because a hit rate on its own is
    # gameable by widening: "between one token and a billion" never misses.
    out["mean_width_pct"] = _mean_int([w for _o, _e, w in triples])
    out["bias"] = ("balanced" if out["mean_error_pct"] == 0 else
                   "under_estimating" if out["mean_error_pct"] > 0 else "over_estimating")
    out["first"], out["last"] = rows[0].get("reconciled_at"), rows[-1].get("reconciled_at")
    out["reason"] = ("%d of %d record(s) in range%s"
                     % (hits, len(rows),
                        ", over the last %d of %d" % (len(rows), total) if window else ""))
    return out


def curve(records, window=WINDOW):
    """THE CALIBRATION CURVE: one point per reconciliation, in order, carrying the hit rate and
    the mean error as of that point.

    WHAT ANYONE CAN INSPECT. Each point holds the cumulative figures (every record up to here)
    and the trailing-window figures (the last `window` records), so a reader sees both the
    long-run accuracy and whether it is currently drifting. A converging estimator shows the
    window hit rate rising and the window mean error approaching zero; a drifting one shows the
    cumulative figure staying flat while the window figure falls, which a single lifetime
    average hides completely.

    AN EMPTY LEDGER IS AN EMPTY CURVE, not a line along the bottom. Each point is computed by
    the same `accuracy` function the headline number uses, so the curve and the headline can
    never disagree about what a hit rate is."""
    rows = ordered(records)
    points = []
    for k in range(1, len(rows) + 1):
        prefix = rows[:k]
        cum = accuracy(prefix)
        win = accuracy(prefix, window=window)
        points.append({
            "n": k,
            "through": rows[k - 1].get("reconciled_at"),
            "spec": rows[k - 1].get("spec"),
            "outcome": rows[k - 1].get("outcome"),
            "error_pct": rows[k - 1].get("error_pct"),
            "cumulative_hit_rate_pct": cum["hit_rate_pct"],
            "cumulative_mean_error_pct": cum["mean_error_pct"],
            "window": window,
            "window_n": win["n"],
            "window_hit_rate_pct": win["hit_rate_pct"],
            "window_mean_error_pct": win["mean_error_pct"],
        })
    return points


# ---------------------------------------------------------------------------------------
# The refit: correcting the one number in the estimator that was never measured.
# ---------------------------------------------------------------------------------------

def fittable(records, exclude=None):
    """The records a scale can be fitted from: those carrying the whole structure-and-scale
    block. `exclude` drops one spec, which is what makes the held-out scoring below possible."""
    out = []
    for r in ordered(records):
        if exclude is not None and r.get("spec") == exclude:
            continue
        if all(_is_int(r.get(k)) and r[k] > 0
               for k in ("structural_weight_tenths", "declared_scale", "implied_scale")):
            out.append(r)
    return out


def fit(records, exclude=None, min_sample=MIN_REFIT_SAMPLE):
    """Refit the token scale from the accumulating history: the number the structural proxy had
    to declare because nothing had measured it.

    THE STRUCTURE IS NOT TOUCHED. Only the scale is refitted, which is possible only because
    WARP-1402 recorded the structural WEIGHT and the SCALE separately in every layer. The
    fitted scale is the LOWER MEDIAN of the implied scales, and `spec` names the change it came
    from, for the same reason WARP-1406's peg is a lower median: on an even sample the
    arithmetic middle is a change nobody made, and a fitted number a reader can go and open is
    worth more than one nobody can trace.

    THE DISPERSION IS REPORTED AND NEVER JUDGED. `dispersion_pct` is the highest implied scale
    as a percentage of the lowest. Tight means the structure ranks work correctly and one
    multiplier was wrong; wide means the structure itself does not explain the variance and no
    single scale will fix it. This function refuses to draw that line for a reader, because the
    threshold would be invented; what it does instead is carry the dispersion INTO the refitted
    layer's range, so disagreement shows up as a wider range rather than as a footnote.

    IT STANDS DOWN RATHER THAN GUESSING. Fewer than `min_sample` records, or records from more
    than one era (D5: two models' tokens are not one unit and are never blended), and this
    returns `fitted: False` with the reason."""
    usable = fittable(records, exclude=exclude)
    out = {"fitted": False, "sample": len(usable), "min_sample": min_sample, "scale": None,
           "scale_low": None, "scale_high": None, "dispersion_pct": None, "spec": None,
           "era": None, "excluded": exclude, "declared_scales": [], "specs": [],
           "reason": ""}
    eras = sorted({(r.get("era") or "") for r in usable})
    if len(eras) > 1:
        out["reason"] = ("the %d fittable record(s) span %d eras (%s): two models do different "
                         "work per token, so their actuals are not one unit and a single fitted "
                         "scale over both would be a guess wearing a measurement's clothes (D5)"
                         % (len(usable), len(eras),
                            ", ".join(e or "(unstamped)" for e in eras)))
        return out
    if len(usable) < min_sample:
        out["reason"] = ("%d record(s) carry the structure and scale a refit needs; a fitted "
                         "scale needs at least %d, or the median is one or two numbers wearing a "
                         "statistic's clothes. The estimator keeps its declared prior and says "
                         "so" % (len(usable), min_sample))
        return out
    implied = sorted((r["implied_scale"], r["spec"]) for r in usable)
    scale, spec = implied[(len(implied) - 1) // 2]
    lo, hi = implied[0][0], implied[-1][0]
    out.update({
        "fitted": True,
        "scale": scale,
        "spec": spec,
        "scale_low": lo,
        "scale_high": hi,
        # HOW MUCH THE SAMPLE DISAGREES WITH ITSELF, as a percentage of its lowest implied
        # scale. ZERO means the records agree exactly, which is a statement about the sample
        # and not a licence to quote a narrow range: the floor in `recalibrated_range` is what
        # keeps agreement from becoming false precision.
        "dispersion_pct": _pct(hi - lo, lo),
        "era": eras[0] or None,
        "declared_scales": sorted({r["declared_scale"] for r in usable}),
        "specs": [s for _t, s in implied],
        "reason": ("fitted from %d record(s); the implied scales span %d to %d, a spread of %d "
                   "percent above the lowest"
                   % (len(usable), lo, hi, _pct(hi - lo, lo))),
    })
    return out


def recalibrated_range(weight_tenths, fitted):
    """(low, high, floor_applied) for one structural weight under a fitted scale.

    THE RANGE IS THE OBSERVED ENVELOPE OF IMPLIED SCALES, not a declared spread around a point,
    so the estimator's uncertainty becomes MEASURED: records that disagree give a wide range and
    the disagreement cannot hide in a footnote.

    AND IT HAS A FLOOR, because a measured range can be dishonestly narrow. Records that agree
    exactly would otherwise produce a range one rounding step wide, which is an estimator
    claiming a change to within a tenth of a percent on the strength of three earlier changes
    agreeing. Below MIN_FITTED_SPREAD_PCT the range is widened symmetrically in ratio about the
    fitted scale, and the caller is told the floor was applied so the record can say so.

    Rounding is allowed to coarsen a range and never to collapse it (NG6), and the rounding step
    is estimate.py's, because two rounding rules for one unit is one decision spelled twice."""
    if not fitted.get("fitted"):
        raise ValueError("no fitted scale: %s" % (fitted.get("reason") or "nothing to fit from"))
    if not _is_int(weight_tenths) or weight_tenths <= 0:
        raise ValueError("a recalibrated range needs a positive structural weight, got %r"
                         % (weight_tenths,))
    EST = _estimate()
    lo_scale, hi_scale = fitted["scale_low"], fitted["scale_high"]
    floor_applied = (hi_scale - lo_scale) * 100 < lo_scale * MIN_FITTED_SPREAD_PCT
    if floor_applied:
        mid = fitted["scale"]
        lo_scale = min(lo_scale, mid * 100 // HALF_SPREAD_PCT)
        hi_scale = max(hi_scale, mid * HALF_SPREAD_PCT // 100)
    low = EST._round_tokens(weight_tenths * lo_scale // 10)
    high = EST._round_tokens(weight_tenths * hi_scale // 10)
    if high <= low:
        high = low + EST.ROUND_STEP
    return low, high, floor_applied


def recalibrated_layer(weight_tenths, fitted, note=None):
    """ONE layer contribution for the estimate record: the estimator refitted from history.

    It uses the layer id `recalibrated` and the basis `recalibrated` that WARP-1402 already
    declares for exactly this item, so this extends a vocabulary rather than widening one, and
    a record carrying it reads `calibration: calibrated` because that basis is grounded in
    recorded actuals. Every number the fit rested on is in `inputs`, including the declared
    scale it replaced and the dispersion of the sample, so the next reconciliation can attribute
    THIS layer's error the same way this one attributed the prior's."""
    low, high, floored = recalibrated_range(weight_tenths, fitted)
    EST = _estimate()
    ins = {
        "structural_weight_tenths": weight_tenths,
        "fitted_scale": fitted["scale"],
        "fitted_scale_low": fitted["scale_low"],
        "fitted_scale_high": fitted["scale_high"],
        "fitted_from_records": fitted["sample"],
        "dispersion_pct": fitted["dispersion_pct"],
        "fitted_scale_spec": fitted["spec"],
        "refit_basis": "lower_median_implied_scale",
        # WHETHER THE SAMPLE'S OWN AGREEMENT WAS TAKEN AT FACE VALUE. `yes` means the observed
        # envelope was narrower than the declared floor and the range was widened, so a reader
        # knows this range is not as tight as the records looked.
        "spread_floor_applied": EST.YES if floored else EST.NO,
        "min_fitted_spread_pct": MIN_FITTED_SPREAD_PCT,
    }
    if fitted.get("era"):
        ins["era"] = fitted["era"]
    if fitted.get("declared_scales"):
        ins["declared_scale_replaced"] = fitted["declared_scales"][0]
    return {
        "layer": "recalibrated",
        "basis": "recalibrated",
        "low": low,
        "high": high,
        "note": note or ("the STRUCTURE is unchanged and only the SCALE is refitted, from the "
                         "implied scales of reconciled changes; the range is the observed "
                         "envelope of those scales, so disagreement widens it rather than "
                         "hiding in it"),
        "inputs": ins,
    }


def propose_recalibrated(spec_path, at, fitted, protected=(), root=None, supersede=False):
    """The committed estimate for one spec with the refitted layer on it.

    THE SEAM WARP-1402 DECLARED. The structure comes from that module's own structural proxy,
    the record is assembled by its `build_record`, and the layer vocabulary is its own; this
    module contributes one layer and no second opinion about what an estimate is.

    `supersede` is the CALLER'S JUDGEMENT and it is off by default. The committed range is the
    envelope of the layers present, and an envelope never narrows, so keeping both layers
    produces a range as wide as the prior's. Replacing the prior with the refit is the
    judgement that sharpens it, and it is made explicitly by a caller rather than quietly by
    this module's arithmetic."""
    EST = _estimate()
    proxy = EST.structural_proxy(spec_path, protected, root)
    layer = recalibrated_layer(proxy["inputs"]["structural_weight_tenths"], fitted)
    layers = [layer] if supersede else [proxy, layer]
    spec_id = _corpus().spec_features(spec_path)["spec_id"]
    if not spec_id:
        raise ValueError("refusing to estimate %s: it declares no spec id" % spec_path)
    return EST.build_record(spec_id, at, layers)


def holdout(records, min_sample=MIN_REFIT_SAMPLE):
    """THE REFITTED ESTIMATOR'S ACCURACY, MEASURED OUT OF SAMPLE.

    For every record carrying a structure, the scale is refitted from all the OTHER records and
    that record's actual is scored against the range the refit would have given it. Fitting on
    a set and then scoring the same set measures nothing, because the fit has already seen the
    answers; leave-one-out is the cheapest honest alternative and the ledger is small enough
    that the cost is arithmetic.

    A record whose remaining set is too small to fit from is SKIPPED AND COUNTED, never scored
    as a miss and never as a hit. The figures are computed by the same `accuracy` function the
    ledger's own headline uses, so before and after are the same measurement."""
    rows, skipped = [], []
    for r in fittable(records):
        f = fit(records, exclude=r["spec"], min_sample=min_sample)
        if not f["fitted"]:
            skipped.append({"spec": r["spec"], "reason": f["reason"]})
            continue
        low, high, _floored = recalibrated_range(r["structural_weight_tenths"], f)
        rows.append({"spec": r["spec"], "reconciled_at": r.get("reconciled_at"),
                     "estimate_low": low, "estimate_high": high, "actual": r["actual"],
                     "outcome": outcome_of(low, high, r["actual"]),
                     "error_pct": error_pct_of(low, high, r["actual"]),
                     "fitted_scale": f["scale"], "fitted_from_records": f["sample"]})
    out = accuracy(rows)
    out["scored"] = len(rows)
    out["skipped"] = skipped
    out["rows"] = rows
    out["min_sample"] = min_sample
    if not rows:
        out["reason"] = ("no record could be scored out of sample: %s"
                         % (skipped[0]["reason"] if skipped else
                            "no record carries the structure and scale a refit needs, so there "
                            "is nothing to refit and nothing to score"))
    return out


def compare(records, min_sample=MIN_REFIT_SAMPLE):
    """The prior estimator and the refitted one, side by side, and the deltas between them.

    THIS IS THE CLAIM THE ITEM HAS TO BE ABLE TO MAKE AND HAS TO BE ABLE TO REFUSE. `before` is
    the accuracy of the estimates as they were actually committed; `after` is the held-out
    accuracy of the refitted estimator. A negative `mean_abs_error_delta_pct` with a hit rate
    that did not fall is recalibration measurably reducing bias. When either side is unmeasured,
    `measured` is False and no delta is reported, because a comparison against nothing is the
    most flattering number an estimator could publish.

    AND THE WIDTH DELTA IS ON THE SAME LINE, because an improvement bought by widening the range
    is not the same achievement as one bought by centring it. A refit over records that disagree
    wildly WILL raise the hit rate, simply by producing ranges wide enough to contain anything;
    `width_delta_pct` is what makes that visible instead of letting it read as calibration."""
    before = accuracy(records)
    after = holdout(records, min_sample=min_sample)
    out = {"before": before, "after": after, "measured": False,
           "hit_rate_delta_pct": None, "mean_abs_error_delta_pct": None,
           "mean_error_delta_pct": None, "width_delta_pct": None, "improved": None,
           "reason": ""}
    if not before["measured"]:
        out["reason"] = ("the ledger reports no measured accuracy, so there is no prior to "
                         "improve on and nothing to compare a refit against")
        return out
    if not after["measured"]:
        out["reason"] = "the refit scored nothing out of sample: %s" % after["reason"]
        return out
    out["measured"] = True
    out["hit_rate_delta_pct"] = after["hit_rate_pct"] - before["hit_rate_pct"]
    out["mean_abs_error_delta_pct"] = (after["mean_abs_error_pct"]
                                      - before["mean_abs_error_pct"])
    out["mean_error_delta_pct"] = abs(after["mean_error_pct"]) - abs(before["mean_error_pct"])
    out["width_delta_pct"] = after["mean_width_pct"] - before["mean_width_pct"]
    out["improved"] = (out["mean_abs_error_delta_pct"] < 0
                       and out["hit_rate_delta_pct"] >= 0)
    out["reason"] = ("held-out refit over %d of %d record(s): mean absolute error %d to %d "
                     "percent, hit rate %d to %d percent, mean range width %d to %d percent"
                     % (after["scored"], before["n"], before["mean_abs_error_pct"],
                        after["mean_abs_error_pct"], before["hit_rate_pct"],
                        after["hit_rate_pct"], before["mean_width_pct"],
                        after["mean_width_pct"]))
    return out


# ---------------------------------------------------------------------------------------
# Reporting. Through validate.fail, the ONE failure reporter, so a problem here reads exactly
# like every other contract problem in this repository. A REPORT and never a gate stage.
# ---------------------------------------------------------------------------------------

def check_dir(dirpath=None, root=None):
    """Validate every recorded reconciliation. Returns (count, errs).

    ADOPTION SAFE AND SILENT ABOUT IT: with no directory there is nothing to say. This is a
    REPORT and never a gate stage: nothing in scripts/verify.sh calls it, because PLAN-0014's
    C3 says a record's absence, or even its breakage, may never invalidate a spec."""
    V = _validate()
    d = Path(dirpath) if dirpath else records_dir(root)
    if not d.is_dir():
        return 0, 0
    n = errs = 0
    for p in sorted(d.glob("*.yaml")):
        n += 1
        try:
            rec = parse_record(p.read_text())
        except (ValueError, OSError) as e:
            errs += V.fail(str(p), str(e))
            continue
        for problem in validate_record(rec, spec_id=p.stem):
            errs += V.fail(str(p), problem)
    return n, errs


def render(view):
    """The whole surface as lines a person reads, every stand-down stated rather than printed as
    a zero. This is the "anyone can inspect" half of the item: the ledger, the accuracy, the
    curve, the fit and the before/after comparison, in one place, with the reason on every
    figure that is missing."""
    acc, cur, f, cmp_ = view["accuracy"], view["curve"], view["fit"], view["compare"]
    out = ["reconciliations: %d record(s) under %s" % (view["records"], view["dir"])]
    for m in view["problems"]:
        out.append("  REFUSED: %s" % m)
    if acc["measured"]:
        win = view["window_accuracy"]
        out.append("accuracy: %d percent of the last %d unit(s) in range"
                   % (win["hit_rate_pct"], win["n"]))
        out.append("  over the whole ledger: %d percent in range of %d, mean error %+d percent, "
                   "mean absolute error %d percent, worst %+d percent, bias %s, mean range width "
                   "%d percent (a hit rate is gameable by widening, so the width is beside it)"
                   % (acc["hit_rate_pct"], acc["n"], acc["mean_error_pct"],
                      acc["mean_abs_error_pct"], acc["worst_error_pct"], acc["bias"],
                      acc["mean_width_pct"]))
    else:
        out.append("accuracy: NOT MEASURED. %s" % acc["reason"])
    out.append("calibration curve: %d point(s)%s"
               % (len(cur), "" if cur else " (empty: a curve with no points is not a flat line "
                                          "at zero, it is an unmeasured estimator)"))
    for p in cur:
        out.append("  %3d  %s  %-14s %-8s %+5d%%  cumulative %3d%% hit / %+d%% err   window "
                   "%d of %s: %3d%% hit / %+d%% err"
                   % (p["n"], p["through"], p["spec"], p["outcome"], p["error_pct"],
                      p["cumulative_hit_rate_pct"], p["cumulative_mean_error_pct"],
                      p["window_n"], p["window"], p["window_hit_rate_pct"],
                      p["window_mean_error_pct"]))
    if f["fitted"]:
        out.append("refit: scale %d tokens per structural unit (from %s), implied scales %d to "
                   "%d, spread %d percent over %d record(s), declared prior(s) %s"
                   % (f["scale"], f["spec"], f["scale_low"], f["scale_high"],
                      f["dispersion_pct"], f["sample"], f["declared_scales"]))
    else:
        out.append("refit: NOT FITTED. %s" % f["reason"])
    if cmp_["measured"]:
        out.append("recalibration: %s; %s"
                   % (cmp_["reason"],
                      "the refit reduces the error out of sample" if cmp_["improved"]
                      else "the refit does NOT improve on the prior out of sample"))
    else:
        out.append("recalibration: NOT COMPARABLE. %s" % cmp_["reason"])
    for s in view["pending"]:
        out.append("pending: %-14s %s" % (s["spec"], s["reason"]))
    return out


def build_view(root=None, at=None, window=WINDOW):
    """The whole surface over a real repository, assembled from the shipped organs. READS ONLY:
    nothing here writes a record, and `at` is only used to derive what a reconciliation WOULD
    be for a spec that has none, so the view can name the pending rows.

    Every input is assembled by `_repo_inputs`, the one wiring point, so not one organ is
    reimplemented here and the pure functions above never reach for a real file."""
    base = Path(root) if root else ROOT
    recs, problems = load_dir(root=base)
    estimates, corpus, est_problems = _repo_inputs(base)
    ledger = list(recs.values())
    pending = []
    if at:
        derived, standdowns = pair(estimates, corpus, at)
        pending = [{"spec": r["spec"], "reason": "shipped and estimated, not yet reconciled"}
                   for r in derived if r["spec"] not in recs] + standdowns
    return {
        "dir": str(records_dir(base)),
        "records": len(ledger),
        "problems": problems + est_problems,
        "ledger": ledger,
        "accuracy": accuracy(ledger),
        "window_accuracy": accuracy(ledger, window=window) if ledger else accuracy(ledger),
        "curve": curve(ledger, window=window),
        "fit": fit(ledger),
        "compare": compare(ledger),
        "pending": pending,
        "estimates": len(estimates),
    }


def _cli(argv):
    ap = argparse.ArgumentParser(
        prog="toe_reconcile.py",
        description="Reconcile committed estimates against recorded actuals and report the "
                    "estimator's own accuracy. Advisory only: nothing here gates, blocks or "
                    "delays any work, and an empty ledger reports that the estimator has no "
                    "measured accuracy rather than a score of zero.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    rp = sub.add_parser("report", help="the ledger, the accuracy, the curve and the refit")
    rp.add_argument("--at", help="a date, YYYY-MM-DD, to also list what is pending reconciliation")
    rp.add_argument("--window", type=int, default=WINDOW)
    rp.add_argument("--json", action="store_true")
    rc = sub.add_parser("reconcile", help="derive the reconciliation records for this repository")
    rc.add_argument("--at", required=True,
                    help="the date these reconciliations are recorded, YYYY-MM-DD. REQUIRED and "
                         "never read from a clock, so the same ledger is the same bytes")
    rc.add_argument("--write", action="store_true", help="write them to " + RECORDS_DIR)
    ck = sub.add_parser("check", help="validate every recorded reconciliation")
    ck.add_argument("--dir")
    fp = sub.add_parser("fit", help="the refitted token scale and the dispersion behind it")
    fp.add_argument("--json", action="store_true")
    pr = sub.add_parser("propose", help="an estimate for one spec carrying the refitted layer")
    pr.add_argument("--spec", required=True, help="path to the spec file")
    pr.add_argument("--at", required=True, help="the date this estimate is committed, YYYY-MM-DD")
    pr.add_argument("--supersede", action="store_true",
                    help="replace the declared prior with the refit instead of keeping both; the "
                         "envelope never narrows, so this is the judgement that sharpens a range")
    sub.add_parser("vocabulary", help="the declared outcomes, sources and windows")
    a = ap.parse_args(argv)

    if a.cmd == "vocabulary":
        for title, table in (("outcomes (derived, never asserted)", OUTCOMES),
                             ("actual sources", ACTUAL_SOURCES), ("bias", BIAS)):
            print("%s:" % title)
            for k in sorted(table):
                print("  %-18s %s" % (k, table[k]))
        print("window: %d record(s); minimum refit sample: %d record(s)"
              % (WINDOW, MIN_REFIT_SAMPLE))
        return 0

    if a.cmd == "check":
        d = Path(a.dir) if a.dir else records_dir()
        n, errs = check_dir(d)
        if n == 0:
            print("reconciliations: none recorded under %s - standing down (this is not a "
                  "finding)" % d)
            return 0
        print("reconciliations: %d record(s) checked, %d problem(s)" % (n, errs))
        return 1 if errs else 0

    if a.cmd == "reconcile":
        estimates, corpus, _problems = _repo_inputs()
        recs, standdowns = pair(estimates, corpus, a.at)
        for rec in recs:
            print(render_record(rec), end="")
        for s in standdowns:
            print("standing down on %s: %s" % (s["spec"], s["reason"]))
        if not recs:
            print("nothing to reconcile: %d committed estimate(s), and no shipped change carries "
                  "a recorded actual. That is this repository's measured state (WARP-1401 "
                  "measured 0 percent spend coverage), not a failure" % len(estimates))
        if a.write:
            created, unchanged, refused = write_all(recs)
            print("wrote %d, unchanged %d, refused %d" % (len(created), len(unchanged),
                                                          len(refused)))
            for m in refused:
                print("  REFUSED: %s" % m)
            return 1 if refused else 0
        return 0

    if a.cmd == "propose":
        view = build_view()
        try:
            rec = propose_recalibrated(a.spec, a.at, view["fit"],
                                       protected=_estimate().protected_paths(),
                                       supersede=a.supersede)
        except (ValueError, OSError) as e:
            print(str(e), file=sys.stderr)
            return 1
        print(_estimate().render_record(rec), end="")
        return 0

    if a.cmd == "fit":
        view = build_view()
        if a.json:
            print(json.dumps(view["fit"], sort_keys=True, indent=1))
        else:
            print("refit: %s" % ("fitted" if view["fit"]["fitted"] else "NOT FITTED"))
            print("  %s" % view["fit"]["reason"])
        return 0

    view = build_view(at=getattr(a, "at", None), window=a.window)
    if a.json:
        print(json.dumps(view, sort_keys=True, indent=1, default=str))
    else:
        for line in render(view):
            print(line)
    return 0


def _repo_inputs(root=None):
    """(estimates, corpus, estimate problems) for one repository, through the shipped organs.

    THE ONE WIRING POINT, so every function above stays pure over injected data and nothing here
    is a second implementation: the estimates come from estimate.load_dir, the actuals from
    toe_corpus.build over metrics.load (the ONE loop read of the event stream), and the
    protected paths from policy_check."""
    base = Path(root) if root else ROOT
    EST, C = _estimate(), _corpus()
    M = _mod(".veldo/metrics.py", "veldo_metrics_toe_reconcile")
    PC = _mod(".veldo/policy_check.py", "veldo_policy_check_toe_reconcile")
    estimates, problems = EST.load_dir(root=base)
    corpus = C.build(specs_dir=base / "specs", events=M.load(),
                     protected=PC.protected_patterns())
    return estimates, corpus, problems


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
