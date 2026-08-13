#!/usr/bin/env python3
"""The estimate record and the structural proxy (WARP-1402, W2 of PLAN-0014).

WHAT THIS IS. Two things that belong together. First, the record: a validated estimate
committed BESIDE a spec before the work starts, always a RANGE and never a point, carrying
which estimating layers contributed and exactly what each one contributed. Second, the first
of those layers: a deterministic structural proxy over the spec's own mechanical features,
which needs no history, no model call and no network.

Three later items in this plan write into this record (W3 the sizing pass, W4 historical
analogy, W5 reconciliation and recalibration) and one reads it (W8 the roll-up to plan
budgets and dollars), so the schema is defined here in full rather than left to be discovered.

***

THE SCHEMA: veldo.estimate/v1. One record per spec, one file per record, at
`.veldo/estimates/<SPEC-ID>.yaml`. The filename IS the key, so two estimates for one spec
cannot exist, and the record's `spec` field is checked against the filename rather than
trusted. Records are the front-matter subset and are read with the ONE parser
(validate.parse_yamlish); nothing here is a second parser.

  AND THE CLAIM ABOVE IS ONLY TRUE BECAUSE AN ID THAT IS NOT ITS OWN FILENAME IS REFUSED.
  Measured 2026-08-13 by the independent review of this item: with `spec` validated as nothing
  more than a non-empty string, `../policy` was a VALID key, two ids could name one file, and
  the writer replaced `.veldo/policy.yaml` with an estimate record. `validate_record` now asks
  the claim ledger's ONE definition of an id that cannot be stored faithfully
  (`claim.unit_id_problem`), so the filename-is-the-key premise is enforced rather than assumed,
  and every reader and writer here inherits it from the one place that defines it.

  schema        veldo.estimate/v1, exactly.
  spec          the spec id this estimate is for.
  unit          the unit BOTH bounds are in. Declared ONCE, at the top level, and a layer
                that spells a unit of its own is REFUSED: two spellings of one unit is the
                second-spelling defect this repository has a named rule about. v1 declares
                `tokens` and nothing else, because raw tokens are the recorded ground truth
                (PLAN-0014 C2); normalized points (W6) and dollars (W8) are DISPLAY layers
                computed over a token record and get their own fields when those items land.
  committed_at  the date the estimate was committed, YYYY-MM-DD. Supplied by the caller: no
                function in this module reads a clock, so the same spec produces the same
                bytes on any machine on any day.
  calibration   `uncalibrated` or `calibrated`, and it is DERIVED, never asserted: it must
                equal what the contributing layers' bases support, so a record cannot
                present a declared prior as a measurement. See the honesty note below.
  combination   the rule by which the record's own range follows from its layers. v1
                declares `envelope` and nothing else.
  low, high     the committed range, integers in `unit`, with low STRICTLY less than high.
                They must equal what `combination` computes over `layers`, so a
                hand-widened or hand-narrowed committed range is refused by name.
  layers        one or more layer contributions, each carrying:
                  layer   one of the declared layer ids (LAYERS below), unique in a record
                  basis   how that layer arrived at its numbers (BASES below)
                  low     that layer's own lower bound, in the record's unit
                  high    that layer's own upper bound, strictly greater than its low
                  inputs  the numbers that layer actually read or used, so a later
                          reconciliation can attribute error rather than only measure it
                  note    optional, one line
  note          optional, one line.

WHY EVERY LAYER CARRIES ITS OWN RANGE AND ITS OWN INPUTS, which is the whole reason this
record is worth committing rather than a single pair of numbers. At reconciliation (W5) the
actual is one number, and a record holding only a combined range can say nothing more than
"in" or "out". A record holding each layer's range can say WHICH layer was right, and a
record holding each layer's INPUTS can say whether a right answer came from the right
reasoning: this proxy multiplies a structural weight it derives from the spec by a token
SCALE it does not derive from anything, and both are in `inputs`, so W5 can tell a good
estimate (weight right, scale right) from a lucky one (weight wrong, scale wrong the other
way). That distinction is the difference between an estimator that improves and one that
merely keeps score.

WHY THE COMBINATION IS AN ENVELOPE AND NEVER AN AVERAGE. `envelope` is the union: the lowest
low and the highest high of the layers present. So adding a layer can only ever WIDEN the
committed range, never narrow it. That is deliberate and it is NG6 (no false precision) in
arithmetic: two layers that disagree are evidence that the answer is uncertain, and averaging
them into a narrower band than either layer supports manufactures confidence out of
disagreement. A range gets SHARPER here by a stronger layer REPLACING a weaker one, which is
a judgement W4 makes when it decides the analogy supersedes the prior, not something this
module's arithmetic does behind anyone's back.

***

THE HONESTY THIS MODULE IS BUILT AROUND, and it is inherited measurement rather than caution.

WARP-1401 built the actuals corpus and MEASURED that its spend inputs are empty: 904 events
in this repository, 148 shipped specs, 95.3% cycle coverage and 0% spend coverage, because a
token count is not knowable from inside a repository and nothing has ever emitted one. That
finding travels with every number this module produces.

The consequence is precise. The structural proxy derives a dimensionless structural WEIGHT
from the spec's mechanics, and that part is fully determined by the spec. Turning a weight
into TOKENS needs a scale, tokens per structural unit, and this repository has no actuals to
fit one from. So the scale below is a DECLARED PRIOR: a stated number, not a measurement.
Every record this module produces therefore says `calibration: uncalibrated`, carries
`basis: uncalibrated_prior` on the proxy layer, and records the scale it used in that layer's
inputs. When W5 has actuals it refits the scale and the coefficients and writes a layer whose
basis is `recalibrated`; until then no reader can mistake this for a measured number, because
the record says what it is.

WHAT IS DELIBERATELY NOT ENFORCED, which is PLAN-0014 C3 and NG1. An estimate lives beside a
spec, never inside it. It is not an acceptance criterion, it does not change risk, and its
ABSENCE NEVER INVALIDATES A SPEC. Nothing in the gate calls this module; a spec with no
estimate, or with a malformed one beside it, validates exactly as it did before. With no
records present every function here stands down silently and a repository that never uses
this is byte-identically unaffected. If budget caps ever enforce anything, that is D4 and a
separate spec.
"""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

SCHEMA = "veldo.estimate/v1"
ROOT = Path(__file__).resolve().parent.parent
ESTIMATES_DIR = ".veldo/estimates"

# THE UNIT VOCABULARY, declared once. Raw tokens are the recorded ground truth (C2), so they
# are the only unit an estimate may be committed in; a normalized point (W6) or a dollar
# figure (W8) is a DISPLAY computed over a token record and does not replace it.
UNITS = {"tokens": "model tokens to carry the work from specification to a merged, proven "
                   "change, across implementation, the gate, the proof, the independent "
                   "review and every fix-and-recheck cycle"}

# THE LAYER VOCABULARY, the three layers PLAN-0014 declares, weakest to strongest, plus the
# recalibrated layer W5 writes. Declared here rather than in each item so W3, W4 and W5 add
# a record to an existing vocabulary instead of widening it, and so a typo in a layer id is a
# refusal rather than a silently unrecognised contribution.
LAYERS = {
    "structural_proxy": (1, "deterministic mechanical features of the spec itself; no "
                            "history, no model call, no network (W2)"),
    "sizing_pass": (2, "an in-session agent reads the spec and the code it will touch and "
                       "predicts a range with stated reasoning; noisy, self-costed (W3)"),
    "historical_analogy": (3, "matched shipped specs in the actuals corpus, predicted from "
                              "their recorded actuals; strongest, needs history (W4)"),
    "recalibrated": (4, "the estimator refitted from the accumulating feature-to-actual "
                        "history, correcting systematic bias (W5)"),
}

# HOW A LAYER ARRIVED AT ITS NUMBERS. Required, and the reason is the same one spend.py gives
# for its own basis field: a number with no stated provenance is one a later analysis will
# over-trust. The split that matters is which of these are grounded in recorded actuals.
BASES = {
    "uncalibrated_prior": "declared coefficients, never fitted to recorded actuals",
    "agent_judgement": "an agent's own prediction, reasoned but not measured",
    "corpus_analogy": "predicted from the recorded actuals of similar shipped specs",
    "recalibrated": "refitted from the accumulating feature-to-actual history",
}
CALIBRATED_BASES = ("corpus_analogy", "recalibrated")
CALIBRATIONS = ("uncalibrated", "calibrated")

# HOW THE COMMITTED RANGE FOLLOWS FROM THE LAYERS. One rule in v1. A rule added later must be
# declared here, because the validator recomputes the committed range through this table and
# refuses a record whose bounds do not follow from its own layers.
COMBINATIONS = {"envelope": "the union of the contributing layers: the lowest low and the "
                            "highest high, so a layer can only widen the range and never "
                            "narrow it (NG6: disagreement is not confidence)"}

# The record's declared key set. An unknown key is REFUSED BY NAME rather than ignored, so a
# later item extends this schema deliberately instead of smuggling a field past every reader
# that does not know about it.
RECORD_REQUIRED = ("schema", "spec", "unit", "committed_at", "calibration", "combination",
                   "low", "high", "layers")
RECORD_OPTIONAL = ("note",)
RECORD_ORDER = RECORD_REQUIRED[:-1] + RECORD_OPTIONAL + ("layers",)
LAYER_REQUIRED = ("layer", "basis", "low", "high")
LAYER_OPTIONAL = ("inputs", "note")
LAYER_ORDER = LAYER_REQUIRED + LAYER_OPTIONAL

# The front-matter subset has no boolean: `true` parses back as the STRING "true", so a
# record that wrote one would be storing a word while looking like it stored a value. Boolean
# facts therefore use this declared pair, which is a word on purpose.
YES, NO = "yes", "no"

# ABSENT versus PRESENT-AND-NULL, which `dict.get(key)` CANNOT TELL APART, and which this schema
# must: optional here means present-or-absent, and null is neither. The distinction is not
# hypothetical. The ONE front-matter parser reads a bare `inputs:` line - a key with nothing after
# it and nothing indented under it - as the value None, so a record on disk really does carry keys
# that are present and null, and every reader that reached for one through `.get` read that null as
# an absence, called the record VALID, and handed it to a writer that correctly tests PRESENCE.
# Every optional key below is therefore read through `_optional` and never through `.get`.
_ABSENT = object()

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# ---------------------------------------------------------------------------------------
# THE DECLARED PRIOR: the structural model's coefficients. Every number here is a stated
# judgement and not a measurement, for the reason the module docstring gives (0% spend
# coverage in the corpus this would otherwise be fitted from). They are integers and the
# arithmetic below is integer arithmetic, so the proxy is exactly reproducible everywhere.
# ---------------------------------------------------------------------------------------
# Work is counted in TENTHS of a structural unit, so the coefficients stay integral.
BASE_TENTHS = 10       # every change pays a fixed cost: read the spec, run the gate, prove it
AC_TENTHS = 10         # per acceptance criterion: a thing to build AND a thing to prove
SURFACE_TENTHS = 5     # per declared footprint glob: a path to read and re-prove, cheaper
                       # than a criterion, which is why it is half

# THE NAME OF THIS COEFFICIENT SET, recorded in every layer it produces. Raised by the independent
# review 2026-08-13: the layer recorded its WEIGHT and its SCALE but not the coefficients the weight
# was built from, so the docstring's promise that W5 can "refit the scale without touching the
# structure" held only while these three numbers never changed. The day one of them does, an old
# record's weight cannot be decomposed and no reader can tell which model produced which record.
# So the three coefficients go INTO the layer's inputs beside the weight, and this name goes with
# them: BUMP IT whenever BASE_TENTHS, AC_TENTHS or SURFACE_TENTHS changes, so a reader comparing
# records across a coefficient change sees two model names rather than one silent discontinuity.
WEIGHT_MODEL = "structural/v1"
TOKENS_PER_STRUCTURAL_UNIT = 25000   # THE SCALE, and the one number with no evidence at all
SPREAD_PCT = 250       # the range is the point divided by and multiplied by 2.50, a ratio of
                       # 6.25. An uncalibrated prior is not entitled to a narrow range, and
                       # NG6 asks for early ranges that are wide AND say so.
ROUND_STEP = 1000      # bounds are rounded to this, because a token estimate carrying five
                       # significant figures is precision the model does not have

# Expected review CYCLES, the multiplier on the build. Risk enters the model HERE AND ONLY
# HERE, deliberately: a higher tier does not make an acceptance criterion bigger, it makes
# the change get checked more times. Counting risk twice, once as a multiplier and once as
# cycles, would double a factor the model cannot even measure yet.
#
# The review count and the gate depth are READ FROM `.veldo/policy.yaml`, this repository's
# own declared policy, so they are not numbers this module invented. GATE_REWORK is the one
# invented table: how many extra gate-and-fix cycles a gate depth is expected to cost.
GATE_REWORK = {"standard": 0, "full": 1, "expanded": 2}
PROTECTED_REWORK = 1   # a protected path forces a recorded human approval bound to the exact
                       # commit, so ANY later fix invalidates it and costs a whole cycle again

# The fallback when the policy cannot be read for a tier, which is not hypothetical: see
# `policy_tier`. Keyed by the same tier names validate.RISKS declares.
DEFAULT_REVIEWS = {"low": 1, "standard": 1, "high": 1, "critical": 2}
DEFAULT_GATE = {"low": "standard", "standard": "full", "high": "expanded",
                "critical": "expanded"}

_MODS = {}


def _mod(rel, name):
    """One of this engine's modules, loaded from THIS engine's location, cached. The same
    importlib shape spend.py uses to reach events.py, for the same reason: reuse the one
    implementation instead of spelling it again."""
    if name not in _MODS:
        spec = importlib.util.spec_from_file_location(name, ROOT / rel)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MODS[name] = mod
    return _MODS[name]


def _validate():
    """The ONE parser and the ONE failure reporter (.veldo/validate.py)."""
    return _mod(".veldo/validate.py", "veldo_validate_estimate")


def _ledger():
    """The claim ledger, for its ONE definition of an id that cannot be stored faithfully.

    NOT a second spelling of that rule. `claim.unit_id_problem` already answers "why this id
    cannot be a key", and it was hardened on 2026-08-12 when two task ids were found to collapse
    into one claim record. An estimate record is keyed by a spec id in exactly the same way, so it
    inherits the same rule from the same place rather than growing a near-miss copy of it."""
    return _mod(".veldo/claim.py", "veldo_claim_estimate")


def _corpus():
    """The ONE spec-feature reader and the ONE footprint reader (.veldo/toe_corpus.py). The
    proxy reads its features THROUGH this rather than re-deriving them, so the features an
    estimate was made from are the same features the actuals corpus records against it, and a
    change to either one cannot silently split them apart."""
    return _mod(".veldo/toe_corpus.py", "veldo_toe_corpus_estimate")


# ---------------------------------------------------------------------------------------
# The record: validation, rendering, reading.
# ---------------------------------------------------------------------------------------

def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def combine(layers, rule="envelope"):
    """The committed range implied by the layers present, under one declared rule.

    Raises on an unknown rule and on an empty layer set, because a record with no layer is a
    range nobody can attribute, which is the pair of naked numbers this schema exists to
    refuse."""
    if rule not in COMBINATIONS:
        raise ValueError("unknown combination rule %r: v1 declares %s"
                         % (rule, sorted(COMBINATIONS)))
    lows = [l.get("low") for l in layers]
    highs = [l.get("high") for l in layers]
    if not layers or not all(_is_int(v) for v in lows + highs):
        raise ValueError("cannot combine: every layer needs an integer low and high, got "
                         "%d layer(s) %r" % (len(layers), [(l.get("layer"), l.get("low"),
                                                            l.get("high")) for l in layers]))
    return min(lows), max(highs)


def calibration_of(layers):
    """`calibrated` when any contributing layer is grounded in recorded actuals, else
    `uncalibrated`. DERIVED, so no record can claim a calibration its layers do not
    support."""
    return "calibrated" if any(l.get("basis") in CALIBRATED_BASES for l in layers) \
        else "uncalibrated"


def validate_record(rec, spec_id=None):
    """Every problem with an estimate record, as a list of strings that NAME what is wrong.
    Empty means the record is valid. Fail closed: an unrecognised key, an unrecognised
    vocabulary value and a bound that does not follow from the layers are all refusals, never
    silently-ignored input.

    `spec_id`, when given, is the id the record is expected to be for (the filename's stem
    where records are read from disk), so a record filed under the wrong name is caught."""
    out = []
    if not isinstance(rec, dict):
        return ["an estimate record must be a mapping, got %s" % type(rec).__name__]

    unknown = sorted(set(rec) - set(RECORD_REQUIRED) - set(RECORD_OPTIONAL))
    if unknown:
        out.append("unknown key(s) %s: veldo.estimate/v1 declares %s (required) and %s "
                   "(optional), and an unknown key is refused rather than ignored so a later "
                   "item extends the schema deliberately"
                   % (unknown, list(RECORD_REQUIRED), list(RECORD_OPTIONAL)))
    for k in RECORD_REQUIRED:
        if k not in rec:
            out.append("missing required key %r" % k)

    if "schema" in rec and rec["schema"] != SCHEMA:
        out.append("schema must be %r, got %r" % (SCHEMA, rec.get("schema")))
    if "spec" in rec and not (isinstance(rec["spec"], str) and rec["spec"].strip()):
        out.append("spec must name the spec this estimate is for, got %r" % (rec.get("spec"),))
    elif "spec" in rec:
        # THE ID IS THE KEY AND THE KEY IS A FILENAME, SO AN ID THAT CANNOT BE A FILENAME IS
        # REFUSED HERE - in the ONE gate every reader and every writer in this module already asks,
        # so no route can reach a record whose key is a path. Until 2026-08-13 this was checked
        # nowhere and `../policy` was a VALID key: see the schema note in the module docstring.
        # DELEGATED, NEVER RESPELLED. `claim.unit_id_problem` is this repository's ONE definition
        # of an id that cannot be stored faithfully, hardened on 2026-08-12 when two task ids were
        # found to collapse into one claim record. A second character rule here would be the
        # second-spelling defect this repository has a named rule about, and it would drift.
        _id_problem = _ledger().unit_id_problem(rec["spec"])
        if _id_problem is not None:
            out.append("spec %r cannot be this record's key: %s. An estimate is keyed by a spec id "
                       "exactly the way a claim is keyed by a unit id - the id becomes a filename "
                       "under %s - so it obeys that rule from the ONE place that states it"
                       % (rec["spec"], _id_problem, ESTIMATES_DIR))
    if spec_id is not None and rec.get("spec") != spec_id:
        out.append("this record is filed as %r but says spec: %r; the filename is the key, so "
                   "a record cannot be for a different spec than the one it is filed under"
                   % (spec_id, rec.get("spec")))
    if "unit" in rec and rec["unit"] not in UNITS:
        out.append("unit must be one of %s (raw tokens are the recorded ground truth; a "
                   "normalized point or a dollar figure is a display over a token record, "
                   "not a unit an estimate is committed in), got %r"
                   % (sorted(UNITS), rec.get("unit")))
    if "committed_at" in rec and not (isinstance(rec["committed_at"], str)
                                      and DATE_RE.match(rec["committed_at"])):
        out.append("committed_at must be a YYYY-MM-DD date, got %r" % (rec.get("committed_at"),))
    if "combination" in rec and rec["combination"] not in COMBINATIONS:
        out.append("combination must be one of %s, got %r"
                   % (sorted(COMBINATIONS), rec.get("combination")))
    if "calibration" in rec and rec["calibration"] not in CALIBRATIONS:
        out.append("calibration must be one of %s, got %r"
                   % (list(CALIBRATIONS), rec.get("calibration")))

    out.extend(_bounds_problems(rec, "the committed range"))
    out.extend(_note_problems(_optional(rec, "note"), "the record's note"))

    layers = rec.get("layers")
    if not isinstance(layers, list) or not layers:
        out.append("layers must be a non-empty list: a range with no layer behind it is a "
                   "pair of naked numbers, and a reconciliation could never attribute it")
        return out

    seen = []
    for i, l in enumerate(layers):
        where = "layer %d" % (i + 1)
        if not isinstance(l, dict):
            out.append("%s must be a mapping, got %s" % (where, type(l).__name__))
            continue
        unknown = sorted(set(l) - set(LAYER_REQUIRED) - set(LAYER_OPTIONAL))
        if unknown:
            out.append("%s has unknown key(s) %s: a layer declares %s (required) and %s "
                       "(optional). A layer may NOT declare `unit`: the unit is declared once "
                       "at the top level, and two spellings of one unit is exactly the "
                       "second-spelling defect this repository has a rule about"
                       % (where, unknown, list(LAYER_REQUIRED), list(LAYER_OPTIONAL)))
        for k in LAYER_REQUIRED:
            if k not in l:
                out.append("%s is missing required key %r" % (where, k))
        lid = l.get("layer")
        if lid not in LAYERS:
            out.append("%s names layer %r, which is not one of the declared layers %s"
                       % (where, lid, sorted(LAYERS)))
        elif lid in seen:
            out.append("%s repeats layer %r: one contribution per layer, or a reconciliation "
                       "cannot say which one was right" % (where, lid))
        else:
            seen.append(lid)
        if l.get("basis") not in BASES:
            out.append("%s has basis %r, which is not one of %s (a number with no stated "
                       "provenance is one a later analysis will over-trust)"
                       % (where, l.get("basis"), sorted(BASES)))
        out.extend(_bounds_problems(l, where))
        out.extend(_note_problems(_optional(l, "note"), "%s's note" % where))
        out.extend(_inputs_problems(_optional(l, "inputs"), "%s inputs" % where))

    # The two DERIVED fields, recomputed rather than trusted. This is the pair that makes the
    # record unable to lie about itself: a hand-edited committed range that does not follow
    # from the layers is refused, and so is a calibration the layers do not support.
    if all(_is_int(l.get("low")) and _is_int(l.get("high"))
           for l in layers if isinstance(l, dict)) and rec.get("combination") in COMBINATIONS:
        try:
            low, high = combine([l for l in layers if isinstance(l, dict)], rec["combination"])
        except ValueError as e:
            out.append("the committed range cannot be recomputed from the layers: %s" % e)
        else:
            if (rec.get("low"), rec.get("high")) != (low, high):
                out.append("the committed range (%r, %r) is not what combination %r computes "
                           "over the layers present, which is (%d, %d): the committed range "
                           "is DERIVED from the layers and a record may not widen or narrow "
                           "it by hand"
                           % (rec.get("low"), rec.get("high"), rec["combination"], low, high))
    derived = calibration_of([l for l in layers if isinstance(l, dict)])
    if "calibration" in rec and rec["calibration"] in CALIBRATIONS \
            and rec["calibration"] != derived:
        out.append("calibration says %r but the layer bases support %r: calibration is "
                   "DERIVED from whether any layer is grounded in recorded actuals (%s), so a "
                   "declared prior cannot be presented as a measurement"
                   % (rec["calibration"], derived, list(CALIBRATED_BASES)))
    return out


def _bounds_problems(d, where):
    """low and high of one record or one layer: integers, positive, and low STRICTLY less
    than high. The strict inequality is the schema's refusal of a point estimate (NG6): a
    single number is not an estimate, it is a claim to a precision nothing here has."""
    out = []
    for k in ("low", "high"):
        if k in d and not _is_int(d[k]):
            out.append("%s: %s must be an integer number of units, got %r" % (where, k, d[k]))
        elif k in d and d[k] <= 0:
            out.append("%s: %s must be positive, got %r" % (where, k, d[k]))
    lo, hi = d.get("low"), d.get("high")
    if _is_int(lo) and _is_int(hi):
        if lo == hi:
            out.append("%s is a POINT (%d == %d): veldo.estimate/v1 has no point estimate, "
                       "because false precision is the one thing an estimator is never "
                       "entitled to. Widen it and say how much you do not know" % (where, lo, hi))
        elif lo > hi:
            out.append("%s is inverted: low %d is above high %d" % (where, lo, hi))
    return out


def _optional(d, key):
    """One optional key's value, or _ABSENT when the key is not there at all. This exists for the
    third state `d.get(key)` erases - a key PRESENT with a null value - and it is the only way any
    optional key in this module is read, so no later key can reintroduce that conflation."""
    return d[key] if key in d else _ABSENT


def _null_problem(where):
    """THE ONE SPELLING OF THE NULL REFUSAL, shared by every optional key, so the rule is stated
    once and a key added to this schema tomorrow inherits it instead of restating it."""
    return ("%s is PRESENT with a null value, which is not a state this schema has: optional here "
            "means PRESENT OR ABSENT, and null is neither. A bare `key:` line, with nothing after "
            "it and nothing indented under it, is exactly what the ONE front-matter parser reads "
            "as null, so this shape arrives from a record on disk and not only from a fixture. It "
            "is refused rather than read as an absence because the writer tests PRESENCE, which is "
            "what optional means, and would then be handed a value that is not there: a record "
            "called VALID and unable to survive its own write. Say it by OMITTING THE KEY" % where)


def _note_problems(note, where):
    if note is _ABSENT:
        return []
    if note is None:
        return [_null_problem(where)]
    if not isinstance(note, str) or not note.strip():
        return ["%s must be a non-empty single-line string, got %r" % (where, note)]
    return []


def _inputs_problems(ins, where):
    """One layer's inputs map, checked against exactly what the writer writes and the ONE parser
    reads back, so that VALID means WRITABLE for every state this key can be in.

    THE REASON THIS IS NOT JUST `isinstance(ins, dict)`, which is what it was: validate_record is
    the single gate every reader and every writer in this module asks, and a record it calls valid
    must survive its own render and parse. An inputs map is the one place in the schema where the
    KEYS and the VALUES are open, so it is the one place the validator can bless something the
    writer cannot write. Four shapes did exactly that:

      - an EMPTY map, which the renderer silently dropped, so the record read back from disk was a
        DIFFERENT record than the one validated, with no error anywhere. Refused here rather than
        given a spelling, because the front-matter subset has no block form for an empty map, and
        a layer that read no numbers says so by omitting the key. Silent is the worst of the four.
      - the key PRESENT with a NULL value, which is what a bare `inputs:` line parses to and which
        `l.get("inputs")` could not tell from an absent key. The validator read that null as an
        ABSENCE and blessed the record; the writer, testing PRESENCE as optional means, then met
        the None and died with an UNCAUGHT TypeError out of `sorted(None)`. Refused through the
        shared `_null_problem` above, so the same rule covers `note` in both scopes and covers the
        next optional key without that key having to remember it.
      - a key the parser cannot read back AS a key (a hyphen, a space, a leading digit, empty),
        which wrote a line the parser then refused, turning a valid record into an unreadable file.
      - a value outside the subset's scalars, refused by the ONE writer below.

    The key rule is READ FROM the parser's own key pattern rather than spelled a second time here,
    and the value rule is the ONE renderer called for its refusal, so neither can drift from the
    thing it is protecting."""
    if ins is _ABSENT:
        return []
    if ins is None:
        return [_null_problem(where)]
    if not isinstance(ins, dict):
        return ["%s must be a mapping of the numbers that layer read, got %s"
                % (where, type(ins).__name__)]
    if not ins:
        return ["%s is present but EMPTY: a layer that read no numbers omits the key, because the "
                "front-matter subset this record is written in has no spelling for an empty map, "
                "so the key would be dropped on the way to disk and the record read back would "
                "not be the record that was validated" % where]
    key_re = _validate()._KEY_RE
    out = []
    for k in sorted(ins, key=repr):
        m = key_re.match("%s:" % (k,)) if isinstance(k, str) else None
        if m is None or m.group(1) != k:
            out.append("%s has key %r, which the ONE front-matter parser cannot read back as a "
                       "key (it reads %s): an input name is a bare identifier, and a name that "
                       "writes a line the parser refuses makes the whole record unreadable"
                       % (where, k, key_re.pattern))
            continue
        try:
            _render_scalar(ins[k], "%s %r" % (where, k))
        except ValueError as e:
            out.append(str(e))
    return out


def _render_scalar(value, where):
    """One scalar as the front-matter subset spells it, refusing anything that would not read
    back as itself. The writer is bound to the reader by that refusal plus the round-trip
    assertion in the selftest: a value the ONE parser would turn into something else is
    refused HERE, rather than written and discovered by whoever reads the record next."""
    if _is_int(value):
        return str(value)
    if not isinstance(value, str):
        raise ValueError("%s: cannot render %r (%s); the record holds integers and single-line "
                         "strings only" % (where, value, type(value).__name__))
    if value != value.strip() or not value:
        raise ValueError("%s: refusing to render %r: the parser strips surrounding whitespace, "
                         "so this would not read back as itself" % (where, value))
    if "\n" in value or "\t" in value:
        raise ValueError("%s: refusing to render a multi-line or tab-bearing value %r: notes "
                         "are one line" % (where, value))
    if re.fullmatch(r"-?\d+", value):
        raise ValueError("%s: refusing to render %r as a string: it would read back as the "
                         "integer %s" % (where, value, value))
    if value[0] in "[{#-\"'" or value.lstrip().startswith("- "):
        raise ValueError("%s: refusing to render %r: a value opening with %r is structure to "
                         "the parser, not text" % (where, value, value[0]))
    return value


def render_record(rec):
    """The record as the front-matter subset, in a declared key order so the same record is
    always the same bytes. `validate.parse_yamlish` of this returns the record.

    EVERY KEY PRESENT IS WRITTEN. This writer tests PRESENCE and never truthiness: it used to
    write a layer's inputs under `if l.get("inputs")`, which dropped an EMPTY map without a word,
    so a record validate_record had just called valid came back from disk missing a key. What the
    schema means by optional is present-or-absent, and a falsy value is present.

    WHAT MAKES THAT SAFE, because presence-testing alone is not: a key present with a NULL value is
    also present, and this writer would take `sorted(None)` straight into an uncaught TypeError. It
    never sees one, because the validator this function runs FIRST refuses a present null by name
    (_null_problem) - which is the whole reason the refusal lives in the validator and not here. A
    writer defending itself would give the same record two different verdicts depending on which
    door it came through."""
    problems = validate_record(rec)
    if problems:
        raise ValueError("refusing to render an invalid estimate record: "
                         + "; ".join(problems))
    lines = []
    for k in RECORD_ORDER:
        if k == "layers" or k not in rec:
            continue
        lines.append("%s: %s" % (k, _render_scalar(rec[k], "record key %r" % k)))
    lines.append("layers:")
    for i, l in enumerate(rec["layers"]):
        first = True
        for k in LAYER_ORDER:
            if k not in l or k == "inputs":
                continue
            lead = "  - " if first else "    "
            lines.append("%s%s: %s" % (lead, k, _render_scalar(
                l[k], "layer %d key %r" % (i + 1, k))))
            first = False
        if "inputs" in l:
            lines.append("    inputs:")
            for ik in sorted(l["inputs"]):
                lines.append("      %s: %s" % (ik, _render_scalar(
                    l["inputs"][ik], "layer %d input %r" % (i + 1, ik))))
    return "\n".join(lines) + "\n"


def parse_record(text):
    """One record's text through the ONE parser. A parse failure is a refusal that names the
    parser's own line hint, never a silently empty record."""
    try:
        rec = _validate().parse_yamlish(text)
    except ValueError as e:
        raise ValueError("estimate record is outside the front-matter parser subset: %s" % e)
    if not isinstance(rec, dict):
        raise ValueError("estimate record must be a mapping, got %s" % type(rec).__name__)
    return rec


def read_record(path, spec_id=None):
    """One record from disk, fail closed. Raises ValueError naming every problem."""
    path = Path(path)
    if spec_id is None:
        spec_id = path.stem
    rec = parse_record(path.read_text())
    problems = validate_record(rec, spec_id=spec_id)
    if problems:
        raise ValueError("refusing the estimate record at %s: %s" % (path, "; ".join(problems)))
    return rec


def records_dir(root=None):
    return (Path(root) if root else ROOT) / ESTIMATES_DIR


def _record_path(d, spec_id):
    """The ONE place a spec id becomes a record path, for READING and for WRITING both, and the
    second half of the traversal defence.

    THE FIRST HALF IS THE ID RULE IN `validate_record`, which refuses an id that is not its own
    filename. This is the half that does not depend on any character rule being right: whatever the
    id, the file this module touches RESOLVES INSIDE the records directory, or nothing is touched
    and the refusal names both paths. Defence in depth on purpose - the review that found the
    traversal found it through an id nothing had thought about, and the next one will be an id
    nobody has thought about either.

    IT COVERS THE READ AS WELL AS THE WRITE. `estimate_for` used to join the id into a path and
    open whatever was there, so a poisoned id read a file outside the directory back as an
    estimate. A reader that answers from outside its own store is a wrong answer, not a crash, and
    it is the quieter half of the same defect."""
    p = Path(d) / ("%s.yaml" % spec_id)
    base = Path(d).resolve()
    if p.resolve().parent != base:
        raise ValueError("refusing to treat %r as an estimate key: it resolves to %s, which is "
                         "OUTSIDE the records directory %s. A record's id is a filename in one "
                         "directory, and an id that escapes it could read or destroy a file this "
                         "module was never asked to touch" % (spec_id, p.resolve(), base))
    return p


def load_dir(dirpath=None, root=None):
    """Every valid record present, keyed by spec id, plus the problems found.

    ADOPTION SAFE: an absent directory is not an error, it is a repository that does not use
    this, and it yields ({}, []) without creating anything. FAIL CLOSED: a record that is
    present and malformed is NOT silently dropped from the set - it is reported by name."""
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


def estimate_for(spec_id, dirpath=None, root=None):
    """The committed estimate for one spec, or None. None is an ordinary answer: an estimate
    is opt-in per plan (D3) and its absence never invalidates anything."""
    d = Path(dirpath) if dirpath else records_dir(root)
    p = _record_path(d, spec_id)
    if not p.is_file():
        return None
    return read_record(p, spec_id=spec_id)


def write_record(rec, dirpath=None, root=None, replace=False):
    """Write one record, refusing to overwrite unless asked. The refusal is the point: an
    estimate is a commitment made BEFORE the work, and silently rewriting one afterwards is
    how a reconciliation ends up scoring a number that was edited to fit."""
    problems = validate_record(rec)
    if problems:
        raise ValueError("refusing to write an invalid estimate record: " + "; ".join(problems))
    # THE ID BECOMES A PATH HERE. Measured 2026-08-13 by the independent review of WARP-1402 and
    # reproduced: a spec whose `id:` is `../policy` is accepted by validate.check_spec with ZERO
    # errors, and this function then wrote an estimate record OVER .veldo/policy.yaml - 3977 bytes
    # down to 848 - with no `replace` and no refusal. That file declares which paths are PROTECTED
    # and what the risk tiers are, so the writer could delete the policy that governs the writer.
    # THE ID RULE IS THE `validate_record` CALL ABOVE, asked in the ONE gate every reader and every
    # writer in this module already asks, so ONE statement covers this write, `build_record`,
    # `read_record` and `estimate_for` instead of four copies of the same delegation. What is left
    # here is this function's OWN half: the CONTAINMENT question in `_record_path`, which holds
    # whatever the character rule turns out to have missed.
    # AND THE OVERWRITE GUARD BELOW DID NOT FAIL, IT WAS ASKED TOO EARLY. `p.exists()` ran before the
    # `d.mkdir()` two lines down, so for `.veldo/estimates/../policy.yaml` it answered about a path
    # that could not resolve yet and returned False; the write then ran after mkdir, when the same
    # path resolved perfectly. A guard that is correct and consulted at the wrong moment is not a
    # guard, and that ordering is fixed too.
    d = Path(dirpath) if dirpath else records_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    p = _record_path(d, rec["spec"])
    if p.exists() and not replace:
        raise ValueError("%s already carries a committed estimate for %s: refusing to "
                         "overwrite it, because an estimate edited after the work is not an "
                         "estimate. Pass replace to say you mean it" % (p, rec["spec"]))
    p.write_text(render_record(rec))
    return p


# ---------------------------------------------------------------------------------------
# The first layer: the structural proxy.
# ---------------------------------------------------------------------------------------

def policy_tier(risk, root=None):
    """(reviews, gate_depth, source) for one risk tier: read from this repository's declared
    `.veldo/policy.yaml` where it is readable, from the declared default table where it is
    not, and the source SAYS WHICH.

    MEASURED, AND THE REASON THIS RETURNS A SOURCE AT ALL: in this repository the `critical`
    tier is written across two lines, and the ONE front-matter parser folds a deeper-indented
    continuation into the preceding scalar, so that tier arrives as a STRING rather than a
    map and its review count is not readable there. Falling back is right, and hiding the
    fallback would put a default into a record that looks like a policy reading."""
    tiers = {}
    base = Path(root) if root else ROOT
    p = base / ".veldo" / "policy.yaml"
    if p.is_file():
        try:
            doc = _validate().parse_yamlish(p.read_text())
        except (ValueError, OSError):
            doc = {}
        if isinstance(doc, dict) and isinstance(doc.get("risk_tiers"), dict):
            tiers = doc["risk_tiers"]
    t = tiers.get(risk)
    if isinstance(t, dict):
        reviews, gate = t.get("reviews"), t.get("gate")
        if _is_int(reviews) and reviews > 0 and gate in GATE_REWORK:
            return reviews, gate, "policy"
    if risk not in DEFAULT_REVIEWS:
        raise ValueError("no declared expectation for risk tier %r: the proxy knows %s"
                         % (risk, sorted(DEFAULT_REVIEWS)))
    return DEFAULT_REVIEWS[risk], DEFAULT_GATE[risk], "default"


def expected_review_cycles(reviews, gate_depth, protected_touch):
    """How many times this change is expected to go round the gate and the review. The
    multiplier on the build, and the only place risk enters the model."""
    if gate_depth not in GATE_REWORK:
        raise ValueError("no rework allowance declared for gate depth %r: the proxy knows %s"
                         % (gate_depth, sorted(GATE_REWORK)))
    return reviews + GATE_REWORK[gate_depth] + (PROTECTED_REWORK if protected_touch else 0)


def _round_tokens(n):
    """Bounds rounded to ROUND_STEP, in integer arithmetic so it is identical everywhere."""
    return max(ROUND_STEP, (int(n) + ROUND_STEP // 2) // ROUND_STEP * ROUND_STEP)


def protected_paths(root=None):
    """This repository's declared protected paths, through the ONE parser. Only the CLI
    reaches for this: the pure functions take `protected` as an argument, exactly as
    toe_corpus.build does, so a test drives them with a seeded set and they cannot reach for
    the real policy behind a caller's back."""
    base = Path(root) if root else ROOT
    p = base / ".veldo" / "policy.yaml"
    if not p.is_file():
        return ()
    try:
        doc = _validate().parse_yamlish(p.read_text())
    except (ValueError, OSError):
        return ()
    paths = doc.get("protected_paths") if isinstance(doc, dict) else None
    if not isinstance(paths, list):
        return ()
    return tuple(e["path"] for e in paths
                 if isinstance(e, dict) and isinstance(e.get("path"), str))


def structural_proxy(spec_path, protected=(), root=None):
    """ONE layer contribution: the deterministic structural proxy over a spec's mechanical
    features. No history, no model call, no network, no clock, no subprocess.

    THE MODEL, stated in full because a coefficient nobody can see is a coefficient nobody
    can correct:

        work_tenths   = BASE + AC_TENTHS * acceptance_criteria
                             + SURFACE_TENTHS * regression_surface
        cycles        = policy reviews for the tier
                             + the gate depth's rework allowance
                             + one more if the footprint touches a protected path
        weight_tenths = work_tenths * cycles
        point         = weight_tenths * TOKENS_PER_STRUCTURAL_UNIT / 10
        low, high     = point / 2.50, point * 2.50, rounded

    REGRESSION SURFACE is the declared footprint: every glob in it is a path this change may
    touch and therefore a path the gate re-proves. Read through toe_corpus's ONE footprint
    reader, which is also why a spec with no footprint block gives a surface of 0 instead of
    raising.

    A SURFACE OF 0 MEANS ONE THING ONLY: THE SPEC DECLARED NO BLOCK. A block that is present and
    reads as nothing is a REFUSAL here, not a zero, and that distinction is the whole finding the
    independent review raised on 2026-08-13: the footprint reader stopped at the first line that was
    not a list item, so a comment inside a block truncated it and a comment on its first line
    emptied it, and this layer then stated `regression_surface: 0` and `protected_touch: no` as
    MEASUREMENTS. Measured over this repository: 8 of 215 specs got a materially wrong record and 3
    of them said protected_touch: no about a spec that does touch a declared protected path -
    the one feature this model calls the strongest mechanical predictor of a wait on a person.
    The reader is repaired; this refusal is the part that keeps the next unreadable shape from
    arriving as a confident zero instead of a question.

    THE FEATURES ARE READ AND NEVER JUDGED, the same rule WARP-1401 states for the corpus: a
    feature a human has to assess is an estimate wearing a feature's clothes, and it would
    make this layer unfalsifiable. Every input the layer used is returned inside it, including
    the scale, so W5 can tell a structure error from a scale error."""
    C = _corpus()
    text = Path(spec_path).read_text()
    f = C.spec_features(spec_path)
    risk = f.get("risk")
    if risk not in DEFAULT_REVIEWS:
        raise ValueError("refusing to estimate %s: risk %r is not a declared tier (%s). An "
                         "estimate is never produced from a feature the proxy cannot read, "
                         "and refusing to estimate blocks nothing: the spec stands without "
                         "one" % (spec_path, risk, sorted(DEFAULT_REVIEWS)))
    footprint = C.footprint_of(text)
    if not footprint and C.footprint_block_present(text):
        raise ValueError("refusing to estimate %s: it DECLARES a footprint block that the ONE "
                         "footprint reader reads as EMPTY, so both features this layer takes from "
                         "it - the regression surface and the protected touch - would be stated as "
                         "0 and 'no' without being measured. A spec that declares no footprint at "
                         "all is a surface of 0 and estimates fine; a block nobody can read is a "
                         "question, and refusing to estimate blocks nothing because the spec "
                         "stands without one" % (spec_path,))
    touch = bool(C.protected_touch(footprint, tuple(protected)))
    reviews, gate, source = policy_tier(risk, root)
    cycles = expected_review_cycles(reviews, gate, touch)
    ac, surface = f["acceptance_criteria"], f["footprint_declared"]
    work_tenths = BASE_TENTHS + AC_TENTHS * ac + SURFACE_TENTHS * surface
    weight_tenths = work_tenths * cycles
    point = weight_tenths * TOKENS_PER_STRUCTURAL_UNIT // 10
    low = _round_tokens(point * 100 // SPREAD_PCT)
    high = _round_tokens(point * SPREAD_PCT // 100)
    if high <= low:
        # Rounding that collapsed a range into a point would be the exact false precision
        # this schema refuses, so the guard WIDENS rather than accepts it.
        high = low + ROUND_STEP
    return {
        "layer": "structural_proxy",
        "basis": "uncalibrated_prior",
        "low": low,
        "high": high,
        "note": "declared-prior structural model; the token scale is NOT fitted to recorded "
                "actuals because this repository records none (WARP-1401 measured 0 percent "
                "spend coverage), so the structure is derived and the scale is stated",
        "inputs": {
            "acceptance_criteria": ac,
            "risk": risk,
            "protected_touch": YES if touch else NO,
            "regression_surface": surface,
            "reviews_declared": reviews,
            "reviews_source": source,
            "gate_depth": gate,
            "gate_rework": GATE_REWORK[gate],
            "protected_rework": PROTECTED_REWORK if touch else 0,
            "expected_review_cycles": cycles,
            "structural_weight_tenths": weight_tenths,
            # THE COEFFICIENTS THE WEIGHT WAS BUILT FROM, and the name of the set they belong to.
            # Without these the weight is one number a later reader cannot decompose: it could
            # recompute the weight only by importing TODAY's constants, which is to say it could
            # never tell a record made under different coefficients from one made under these.
            # Raised by the independent review 2026-08-13 as the cheap-now, expensive-later half of
            # the reconciliation this schema exists for, and it is cheap now because no record
            # written under the old shape exists.
            "weight_model": WEIGHT_MODEL,
            "base_tenths": BASE_TENTHS,
            "ac_tenths": AC_TENTHS,
            "surface_tenths": SURFACE_TENTHS,
            "tokens_per_structural_unit": TOKENS_PER_STRUCTURAL_UNIT,
            "spread_pct": SPREAD_PCT,
        },
    }


def build_record(spec_id, at, layers, unit="tokens", combination="envelope", note=None):
    """Assemble a validated record from any set of layer contributions. THE SEAM the later
    items use: W3, W4 and W5 produce a layer and hand it here rather than each assembling a
    record of its own, so there is one place the derived fields are computed and one place
    they are checked."""
    low, high = combine(layers, combination)
    rec = {"schema": SCHEMA, "spec": spec_id, "unit": unit, "committed_at": at,
           "calibration": calibration_of(layers), "combination": combination,
           "low": low, "high": high, "layers": [dict(l) for l in layers]}
    if note:
        rec["note"] = note
    problems = validate_record(rec)
    if problems:
        raise ValueError("refusing to build an estimate record: " + "; ".join(problems))
    return rec


def propose(spec_path, at, protected=(), root=None, extra_layers=()):
    """The committed estimate for one spec from the layers available today, which for W2 is
    the structural proxy alone. `at` is passed in and never read from a clock, so the same
    spec on the same date is the same bytes on every machine."""
    layers = [structural_proxy(spec_path, protected, root)] + [dict(l) for l in extra_layers]
    C = _corpus()
    spec_id = C.spec_features(spec_path)["spec_id"]
    if not spec_id:
        raise ValueError("refusing to estimate %s: it declares no spec id" % spec_path)
    return build_record(spec_id, at, layers)


# ---------------------------------------------------------------------------------------
# Reporting. Uses validate.fail, the ONE failure reporter, so a problem here reads exactly
# like every other contract problem in this repository.
# ---------------------------------------------------------------------------------------

def check_dir(dirpath=None, root=None, out=None):
    """Validate every committed record. Returns (count, errs).

    Adoption safe and SILENT about it: with no directory and no records there is nothing to
    say and nothing is printed except one standdown line by the caller. This is a REPORT and
    never a gate stage: nothing in scripts/verify.sh calls it, and PLAN-0014 C3 is the reason
    (an estimate's absence, or its breakage, may never invalidate a spec)."""
    V = _validate()
    d = Path(dirpath) if dirpath else records_dir(root)
    if not d.is_dir():
        return 0, 0
    errs = 0
    n = 0
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


def _cli(argv):
    ap = argparse.ArgumentParser(
        prog="estimate.py",
        description="Commit an estimate beside a spec before the work starts: always a range, "
                    "never a point, with every layer's contribution on record. Advisory only: "
                    "nothing here gates, blocks or delays any work.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("propose", help="derive the structural-proxy estimate for one spec")
    pr.add_argument("--spec", required=True, help="path to the spec file")
    pr.add_argument("--at", required=True,
                    help="the date this estimate is committed, YYYY-MM-DD. REQUIRED and never "
                         "read from a clock, so the same spec on the same date is the same "
                         "bytes: `--at $(date -u +%%F)`")
    pr.add_argument("--write", action="store_true", help="write it to " + ESTIMATES_DIR)
    pr.add_argument("--replace", action="store_true",
                    help="overwrite an estimate already committed for this spec")
    ck = sub.add_parser("check", help="validate every committed estimate record")
    ck.add_argument("--dir")
    sh = sub.add_parser("show", help="one committed record as json, for a roll-up to read")
    sh.add_argument("--spec", required=True, help="the spec id")
    sub.add_parser("layers", help="the declared layers, bases and units")
    a = ap.parse_args(argv)

    if a.cmd == "layers":
        print("units:")
        for k in sorted(UNITS):
            print("  %-20s %s" % (k, UNITS[k]))
        print("layers (weakest to strongest):")
        for k in sorted(LAYERS, key=lambda k: LAYERS[k][0]):
            print("  %-20s %s" % (k, LAYERS[k][1]))
        print("bases:")
        for k in sorted(BASES):
            print("  %-20s %s%s" % (k, BASES[k],
                                    "  [grounded in actuals]" if k in CALIBRATED_BASES else ""))
        print("combination rules:")
        for k in sorted(COMBINATIONS):
            print("  %-20s %s" % (k, COMBINATIONS[k]))
        return 0

    if a.cmd == "propose":
        try:
            rec = propose(a.spec, a.at, protected=protected_paths())
            if a.write:
                p = write_record(rec, replace=a.replace)
                print("wrote %s" % p)
            print(render_record(rec), end="")
        except (ValueError, OSError) as e:
            print(str(e), file=sys.stderr)
            return 1
        return 0

    if a.cmd == "show":
        try:
            rec = estimate_for(a.spec)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 1
        if rec is None:
            print("no committed estimate for %s (which invalidates nothing: an estimate is "
                  "opt-in and its absence is an ordinary state)" % a.spec)
            return 0
        print(json.dumps(rec, sort_keys=True, indent=1))
        return 0

    d = Path(a.dir) if a.dir else records_dir()
    n, errs = check_dir(d)
    if n == 0:
        print("estimates: none committed under %s - standing down (this is not a finding)" % d)
        return 0
    print("estimates: %d record(s) checked, %d problem(s)" % (n, errs))
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
