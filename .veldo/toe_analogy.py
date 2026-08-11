#!/usr/bin/env python3
"""Historical analogy: the strongest estimating layer, and the one that DECLINES (WARP-1404, W4).

WHAT THIS IS. The third estimating layer of PLAN-0014, and the only one grounded in anything
that actually happened. It takes a spec that has not been built, finds the shipped specs in
the Tokens of Effort actuals corpus (WARP-1401) whose MECHANICAL FEATURES are closest to it,
and predicts a range from what those changes ACTUALLY COST. It produces one layer
contribution for the estimate record WARP-1402 defined: layer `historical_analogy`, basis
`corpus_analogy`, which is the basis that makes a record read `calibration: calibrated`.

*** THE PROPERTY THIS MODULE EXISTS TO HOLD ***

WITH NO RECORDED ACTUALS IT PRODUCES NO NUMBER AT ALL, AND SAYS WHY. That is not a defensive
flourish, it is the measured situation in this repository today: WARP-1401 built the corpus
and measured 0 percent spend coverage over 148 shipped specs, because a token count is not
knowable from inside a repository and nothing had ever emitted one. An analogy layer over an
empty ledger has exactly one honest output, and it is not a range.

So the stand-down is structural rather than polite. When the evidence is not there this module
returns `None` for the layer and a report whose `predicted` is false, and THAT REPORT CARRIES
NO `low` AND NO `high` KEY AT ALL. Not zero, not null: absent. A null bound is a value a
consumer formats as 0 or coerces into arithmetic; an absent key is a KeyError, which is a
refusal. A caller reads `predicted` first or it gets nothing.

THE ESTIMATE RECORD IS STILL PRODUCED, WITHOUT THIS LAYER, and it is byte-identical to what
W2 alone would have written. An estimator that declines is not an estimator that fails: the
structural proxy still speaks, the record still commits a range, and the range is wider for
having one fewer layer, which is NG6 working as designed.

***

WHAT IT MATCHES ON, AND THE LEAKAGE RULE THAT DECIDES THE SET.

Only features that are KNOWABLE BEFORE THE WORK STARTS. An estimate is made before a build,
so a matcher that reads how many times a change went round the gate, or how many files it
touched, would be predicting an outcome from an outcome: it would score beautifully on history
and be unusable on the only spec anybody ever needs an estimate for, the one not yet built.

  risk                  the declared tier, as an ordinal distance over the declared tiers
  acceptance_criteria   how many things are to be built and proven
  footprint_declared    the declared regression surface, in globs
  protected_touch       whether the footprint touches a protected path

DELIBERATELY EXCLUDED, and enumerated here so the exclusion is a contract rather than an
oversight: everything in the corpus record's `cycles`, `spend` and `git` blocks. Those are
what the work COST, and they are the target of the prediction, never an input to the match.
The one exception is definitional: `spend.tokens` of a MATCHED record is what the prediction
is made FROM. Predicting from the target variable of similar cases is the method; matching on
the target variable of the case in hand is leakage.

THE TARGET NEVER MATCHES ITSELF. A record for the same spec id is excluded and counted, so a
re-estimate of an already shipped spec cannot be a perfect prediction of its own cost.

***

HOW THE RANGE IS BUILT, and why it is an observed envelope rather than a mean.

  observed  = the lowest and the highest token count among the matched changes
  widening  = a small-sample allowance, SMALL_SAMPLE_SLACK / n percent, floored
  low, high = the observed envelope pushed out by that allowance, rounded

No mean, no median, no trimming. A mean of three changes is a number nobody spent, and
trimming an outlier is a judgement that one recorded cost was wrong, which is a judgement
nothing here has evidence for. The recorded costs are the evidence and the envelope is what
they say.

THE WIDENING IS THE PART THAT TIGHTENS AS HISTORY ACCUMULATES, and the distinction matters
because it is easy to promise the wrong thing. The small-sample allowance shrinks strictly and
monotonically as the number of matched changes grows, down to MIN_WIDEN_PCT and never to zero,
because an estimator is never entitled to claim it has finished converging. The OBSERVED
envelope is data: more history can widen it, and when it does that is the corpus reporting a
spread that was always there and had not yet been seen. A module that narrowed the observed
envelope as the sample grew would be manufacturing confidence, which is the exact failure NG6
names.

BELOW MIN_MATCHES THERE IS NO PREDICTION. One matched change is an anecdote and two are an
anecdote and its gap; neither says anything about the spread of the population, and a range
drawn from them would carry a confidence the evidence cannot support.

***

MODEL IDENTITY (D5), WINDOWED THROUGH THE ONE ERA READER RATHER THAN A SECOND ONE.

A token stops meaning what it meant when the model changes, so actuals measured either side of
a capability shift are not in the same unit and must not be averaged into one range. That
judgement already has a home: WARP-1406 records capability shifts as a durable era ledger and
turns them into half-open intervals, stamping every actual with the era its spend was measured
in. This module REUSES that reader (`era_of`, handed in) and windows the evidence set to the
PLANNING ERA, which is the latest era the ledger declares, on the same argument WARP-1406's peg
uses: planning happens in the era you are in. Actuals from an earlier era are excluded and
COUNTED, and if every actual is in an earlier era this layer stands down naming that fact.
With no ledger recorded there is exactly one era, so the windowing is a no-op and nothing is
silently dropped. No cross-era conversion factor is invented here, for the reason WARP-1406
gives: a multiplier claiming to convert one model's tokens into another's is a guess wearing a
measurement's clothes.

***

WHAT IS DELIBERATELY NOT DONE HERE.

THE ANALOGY DOES NOT SUPERSEDE THE PRIOR IN v1. WARP-1402's schema notes that a range gets
sharper by a strong layer REPLACING a weak one, and that the judgement belongs to this item.
This item declines to take it, on the evidence: replacing the structural proxy NARROWS the
committed range, and the only thing that could justify a narrowing is a measurement that the
analogy is actually more accurate than the prior. That measurement is W5's, the estimator's own
mean error and calibration curve. Until it exists, both layers ride and the committed range is
the envelope of the two, so this module can only ever WIDEN what W2 committed, never narrow it.
A narrowing taken on the strength of an argument rather than a measurement is precisely the
false precision this plan forbids.

Not done either: reconciliation, recalibration and the accuracy curve (W5); normalization to a
display point (W6); the judgement-load pair (W7); the plan roll-up and dollars (W8).

***

ADVISORY, PURE, AND ADOPTION SAFE. Nothing in scripts/verify.sh calls this module. Every
function is pure over data the caller passes in - the corpus, the era reader, the parsed
features - so it reads no clock, mints no id, starts no process and writes nothing at all;
this module has no writer. The CLI at the bottom is the only place the real corpus, the real
event log and the real era ledger are wired together. A repository with no actuals records is
byte-identically unaffected and the report says it has nothing rather than printing a zero.

FAIL CLOSED AND BY NAME on structural garbage: a corpus that is not a list, a record that is
not a mapping, a record of some other schema, or a record with no spec id is REFUSED with a
message naming it, because a record quietly skipped makes a smaller evidence set look
complete. A record that is well formed but UNUSABLE as evidence (no recorded spend, no
readable features, wrong era) is a different fact and is counted and named, never refused.

  python3 .veldo/toe_analogy.py report                     what evidence this repository has
  python3 .veldo/toe_analogy.py propose --spec S --at DATE  the record, with the layer or without
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCHEMA = "veldo.toe_analogy/v1"

# The layer id and basis this module produces. Both come from WARP-1402's DECLARED vocabulary
# (estimate.LAYERS and estimate.BASES) rather than being invented here, which is the whole
# reason that vocabulary was declared for the plan up front instead of per item. Asserted
# against that module in the suite, so a typo here is a red rather than a layer no reader
# recognises.
LAYER = "historical_analogy"
BASIS = "corpus_analogy"

# The corpus schema this reads. Named so a corpus of some other shape is refused rather than
# silently matched into a plausible-looking range.
CORPUS_SCHEMA = "veldo.toe_actuals/v1"

# ---------------------------------------------------------------------------------------
# THE MATCH: which features, how far apart, and how close is close enough.
# Every number below is a DECLARED judgement. None is fitted to anything, because fitting a
# similarity metric needs the same actuals the metric is there to find, and this repository
# has none. They are integers and the arithmetic is integer arithmetic, so a match is exactly
# reproducible on every machine.
# ---------------------------------------------------------------------------------------

# The declared risk tiers in order, so a tier difference is an ORDINAL distance. Checked
# against validate.RISKS as a set equality in the suite: a tier added to the contract reds
# there rather than silently becoming unmatchable.
RISK_ORDER = ("low", "standard", "high", "critical")

# The pre-build features the matcher reads, and what a unit of difference in each is worth.
# ONE tier apart is worth two acceptance criteria; a protected-path touch is worth three,
# because it forces a recorded human approval bound to the exact commit and is the single
# mechanical feature of a spec that reliably predicts a wait on a person.
FEATURE_WEIGHTS = {
    "risk": 2,
    "acceptance_criteria": 1,
    "footprint_declared": 1,
    "protected_touch": 3,
}
# Globs per unit of surface distance. A footprint is a coarser signal than a criterion, so two
# globs of difference are worth one criterion of difference.
GLOBS_PER_UNIT = 2

# THE FEATURE BLOCKS THE MATCHER MUST NEVER READ, declared rather than left to discipline.
# These are what the work COST; reading them to choose comparables would be predicting an
# outcome from an outcome, and it would score beautifully on history while being unusable on
# the only spec anybody needs an estimate for. The suite drives this behaviourally: records
# whose cycles, spend and git blocks differ wildly but whose features are identical must be
# the same distance away.
OUTCOME_BLOCKS = ("cycles", "spend", "git")

# How far apart two specs may be and still be comparables. Four is two tiers, or four
# criteria, or a protected-path difference plus one criterion.
MATCH_RADIUS = 4

# The smallest evidence set that may produce a range. One matched change is an anecdote and
# two are an anecdote and its gap: neither carries information about the spread of the
# population, and a range drawn from them would claim a confidence the evidence cannot give.
MIN_MATCHES = 3

# The small-sample allowance, in percent-points spread over the number of matched changes, and
# the floor it can never go below. At 3 matches the envelope is pushed out by 50 percent, at 15
# by 10, and no amount of history takes it under MIN_WIDEN_PCT, because an estimator is never
# entitled to claim it has finished converging.
SMALL_SAMPLE_SLACK = 150
MIN_WIDEN_PCT = 10

# ---------------------------------------------------------------------------------------
# WHY THIS LAYER DECLINED, as a closed vocabulary. Closed on purpose: a consumer switching on
# the code has a complete set of cases, and a reason outside this set cannot be produced.
# ---------------------------------------------------------------------------------------
NO_CORPUS = "no_corpus"
NO_RECORDED_ACTUALS = "no_recorded_actuals"
NO_COMPARABLE_RECORDS = "no_comparable_records"
NO_SAME_ERA_ACTUALS = "no_same_era_actuals"
TOO_FEW_MATCHES = "too_few_matches"
UNREADABLE_TARGET = "unreadable_target_features"

REASONS = {
    NO_CORPUS: ("the actuals corpus is empty, so there is nothing to reason from and this "
                "layer produces no number rather than a default"),
    NO_RECORDED_ACTUALS: ("the corpus has records but not one carries recorded token spend, "
                          "so every analogy would be drawn from zeros; WARP-1401 measured "
                          "this repository at 0 percent spend coverage and .veldo/spend.py is "
                          "the emitter that changes it"),
    NO_COMPARABLE_RECORDS: ("no record in the corpus can serve as a comparable: what is there "
                            "is this spec's own record, or records whose mechanical features "
                            "cannot be read, and a spec is not an analogy for itself"),
    NO_SAME_ERA_ACTUALS: ("every recorded actual was measured in an earlier model era than "
                          "the one this work will run in, and tokens across a capability "
                          "shift are not the same unit, so they are reported apart rather "
                          "than blended"),
    TOO_FEW_MATCHES: ("fewer comparable shipped changes than the declared minimum, so any "
                      "range would be an anecdote wearing a measurement's clothes"),
    UNREADABLE_TARGET: ("the target spec's own mechanical features cannot be read (an "
                        "undeclared risk tier, or no acceptance criteria), so there is "
                        "nothing to match on; declining blocks nothing, because a spec stands "
                        "without an estimate"),
}

# Why a well-formed record was not usable as evidence. Counted and reported, never refused:
# these are ordinary facts about a corpus, not defects in it.
EXCLUSIONS = ("self", "no_spend", "zero_tokens", "unreadable_era", "other_era",
              "unreadable_features")

# THE ONE WORD FOR "windowed by no era at all". Reported in every place an era is reported, so a
# reader of the text and a consumer of the JSON can never see the same fact spelled two ways. It
# used to be `None` in the report and this word in the layer's inputs, which rendered as the
# literal text "era None" beside a record that said "unwindowed".
UNWINDOWED = "unwindowed"


def era_label(window):
    """The era to REPORT: the one actually windowed by, or the one word for none.

    The single place that spelling is decided, so no report path can invent a second one."""
    return window if window is not None else UNWINDOWED


_MODS = {}


def _mod(rel, name):
    """One of this engine's modules, loaded from THIS engine's location, cached. The same
    importlib shape estimate.py and cost_to_change.py use, for the same reason: reuse the one
    implementation instead of spelling it again."""
    if name not in _MODS:
        spec = importlib.util.spec_from_file_location(name, ROOT / rel)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MODS[name] = mod
    return _MODS[name]


def _estimate():
    """WARP-1402's estimate module: the declared layer vocabulary, the record assembly seam
    (`build_record`), the rounding grid and the YES/NO words. Every one of those is REUSED
    rather than respelled, so a layer this module produces is the same species of thing as the
    layer W2 produces and both sit on one grid."""
    return _mod(".veldo/estimate.py", "veldo_estimate_analogy")


def _corpus():
    """WARP-1401's corpus module: the ONE spec-feature reader, the ONE footprint reader and
    the ONE protected-touch test. The target's features are read through exactly the readers
    that produced the corpus records' features, so target and comparable are the same shape by
    construction and a change to either cannot split them apart."""
    return _mod(".veldo/toe_corpus.py", "veldo_toe_corpus_analogy")


def _normalize():
    """WARP-1406's normalization module: the ONE era ledger reader and the ONE era stamper.
    D5's windowing is delegated to it rather than re-derived, because two organs disagreeing
    about which era an actual was measured in is worse than either answer."""
    return _mod(".veldo/toe_normalize.py", "veldo_toe_normalize_analogy")


def _validate():
    """The ONE front-matter parser and the ONE failure reporter."""
    return _mod(".veldo/validate.py", "veldo_validate_analogy")


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


# ---------------------------------------------------------------------------------------
# Reading the corpus: refuse garbage, count what is merely unusable.
# ---------------------------------------------------------------------------------------

def refuse_malformed(corpus):
    """Return the corpus unchanged, or raise ValueError naming every structural problem.

    STRUCTURAL ONLY, and the boundary is deliberate. A corpus that is not a list, a record
    that is not a mapping, a record of another schema and a record with no spec id are all
    REFUSED, because a record silently skipped makes a smaller evidence set look complete and
    an evidence set is exactly the thing somebody quotes without asking how big it was. A
    record that is well formed but carries no spend, or whose features cannot be read, is NOT
    a defect: it is an ordinary fact about a young corpus, and it is counted in the report's
    exclusions instead."""
    if not isinstance(corpus, list):
        raise ValueError("refusing to reason from an actuals corpus that is not a list, got %s"
                         % type(corpus).__name__)
    problems = []
    seen = {}
    for i, rec in enumerate(corpus):
        where = "record %d" % i
        if not isinstance(rec, dict):
            problems.append("%s must be a mapping, got %s" % (where, type(rec).__name__))
            continue
        if rec.get("schema") != CORPUS_SCHEMA:
            problems.append("%s has schema %r, but this layer reasons from %r and nothing else"
                            % (where, rec.get("schema"), CORPUS_SCHEMA))
        if not _is_str(rec.get("spec")):
            problems.append("%s names no spec in `spec`, so it can be neither matched nor "
                            "excluded from itself, got %r" % (where, rec.get("spec")))
        elif not isinstance(rec.get("features"), dict):
            problems.append("%s (spec %s) has no `features` mapping, and features are the only "
                            "thing this layer is allowed to match on" % (where, rec["spec"]))
        else:
            seen.setdefault(rec["spec"], []).append(i)
    for spec in sorted(seen):
        if len(seen[spec]) > 1:
            problems.append("spec %s appears in %d records (indices %s): a duplicate comparable "
                            "would weight one change twice in the evidence set"
                            % (spec, len(seen[spec]), seen[spec]))
    if problems:
        raise ValueError("refusing to reason from this actuals corpus: " + "; ".join(problems))
    return corpus


def tokens_of(rec):
    """The recorded token count of one actuals record, or None when there is not one.

    None and 0 are DIFFERENT FACTS here and the distinction is the whole reason WARP-1401 put
    `spend_recorded` on the record: a sum of zero because nothing was spent and a sum of zero
    because nothing was ever emitted look identical, and an estimator that cannot tell them
    apart will confidently learn from nothing."""
    spend = rec.get("spend") or {}
    if not spend.get("spend_recorded"):
        return None
    t = spend.get("tokens")
    if not _is_num(t) or t <= 0:
        return None
    return t


# ---------------------------------------------------------------------------------------
# The feature vector and the distance.
# ---------------------------------------------------------------------------------------

def target_features(spec_path, corpus_mod=None, protected=()):
    """The pre-build features of the spec being estimated, read through WARP-1401's readers.

    Three ONE-readers and no fourth: `spec_features` for the mechanical counts,
    `footprint_of` for the declared surface and `protected_touch` for the policy test, exactly
    as estimate.structural_proxy assembles them. `protected` is passed IN rather than read from
    the policy here, so a test drives this with a seeded set and it cannot reach for the real
    policy behind a caller's back."""
    C = corpus_mod if corpus_mod is not None else _corpus()
    text = Path(spec_path).read_text()
    f = dict(C.spec_features(spec_path))
    f["protected_touch"] = bool(C.protected_touch(C.footprint_of(text), tuple(protected)))
    return f


def vector(features):
    """One feature mapping as the comparable tuple (risk index, criteria, globs, protected),
    or None when it cannot be read.

    None is returned rather than a default because a default would make an unreadable spec
    silently comparable to every other unreadable spec, which is the shape of a match that
    looks like evidence and is not. Reads ONLY the pre-build features: nothing in
    OUTCOME_BLOCKS is reachable from here, since this function is handed the features mapping
    and never the record."""
    if not isinstance(features, dict):
        return None
    risk = features.get("risk")
    if risk not in RISK_ORDER:
        return None
    ac = features.get("acceptance_criteria")
    globs = features.get("footprint_declared")
    if not _is_int(ac) or ac < 0 or not _is_int(globs) or globs < 0:
        return None
    return (RISK_ORDER.index(risk), ac, globs, bool(features.get("protected_touch")))


def distance(a, b):
    """How far apart two comparable tuples are, in declared feature units. Integer arithmetic,
    symmetric, and zero exactly when the two specs are mechanically identical.

    Nothing here reads a record, so nothing here CAN read what a change cost. That is the
    leakage rule made structural rather than promised: the only way to give this function
    outcome data is to put outcome data in the pre-build feature vector, which the suite
    checks by driving records whose cycles, spend and git blocks differ wildly and requiring
    an identical distance."""
    if a is None or b is None:
        return None
    return (FEATURE_WEIGHTS["risk"] * abs(a[0] - b[0])
            + FEATURE_WEIGHTS["acceptance_criteria"] * abs(a[1] - b[1])
            + FEATURE_WEIGHTS["footprint_declared"] * (abs(a[2] - b[2]) // GLOBS_PER_UNIT)
            + FEATURE_WEIGHTS["protected_touch"] * (1 if a[3] != b[3] else 0))


# ---------------------------------------------------------------------------------------
# The evidence set.
# ---------------------------------------------------------------------------------------

def planning_era(era_list):
    """The era this work will be measured in: the LATEST the ledger declares.

    The same argument WARP-1406's peg makes, for the same reason: planning happens in the era
    you are in, and older eras keep their own numbers rather than being converted into this
    one. With no ledger there is exactly one era, so this is `pre-ledger` and the windowing
    below excludes nothing."""
    if not era_list:
        return None
    return era_list[-1]["era"]


def evidence(corpus, target_spec, target_vector, era_of=None, era=None,
             radius=MATCH_RADIUS):
    """(matched, excluded, candidates) for one target: the whole evidence decision.

    `matched` is a list of (distance, record) sorted by distance then spec id, so the result
    is deterministic. `excluded` counts every well-formed record that was not usable, by the
    declared reason. `candidates` is how many records were usable before the radius was
    applied, which is the number that separates "no history" from "history about different
    work".

    `era_of` is a callable spec id -> (era, reason), which is WARP-1406's own reader handed
    in; None means no era windowing was requested and every era is accepted, which is the
    honest reading when a caller has no ledger to window with."""
    refuse_malformed(corpus)
    excluded = {k: 0 for k in EXCLUSIONS}
    matched = []
    candidates = 0
    for rec in corpus:
        if rec["spec"] == target_spec:
            # A record for the target itself would let a re-estimate of a shipped spec predict
            # its own cost perfectly, which is a measurement of nothing.
            excluded["self"] += 1
            continue
        toks = tokens_of(rec)
        if toks is None:
            spend = rec.get("spend") or {}
            excluded["zero_tokens" if spend.get("spend_recorded") else "no_spend"] += 1
            continue
        v = vector(rec.get("features"))
        if v is None:
            excluded["unreadable_features"] += 1
            continue
        if era_of is not None:
            got, _why = era_of(rec["spec"])
            if got is None:
                excluded["unreadable_era"] += 1
                continue
            if era is not None and got != era:
                excluded["other_era"] += 1
                continue
        candidates += 1
        d = distance(target_vector, v)
        if d is not None and d <= radius:
            matched.append((d, rec))
    matched.sort(key=lambda pair: (pair[0], pair[1]["spec"]))
    return matched, excluded, candidates


# ---------------------------------------------------------------------------------------
# The prediction.
# ---------------------------------------------------------------------------------------

def widening_pct(n):
    """The small-sample allowance for n matched changes, in percent.

    STRICTLY NON-INCREASING IN n AND FLOORED. This is the part of the range that tightens as
    history accumulates; the observed envelope is data and is allowed to widen when the corpus
    turns out to be more varied than the first few changes suggested. The floor is there
    because a converged estimator is still an estimator."""
    if not _is_int(n) or n < 1:
        raise ValueError("the small-sample allowance is defined for a positive number of "
                         "matched changes, got %r" % (n,))
    return max(MIN_WIDEN_PCT, SMALL_SAMPLE_SLACK // n)


def predict(matched, round_tokens=None, step=None):
    """(low, high, observed_low, observed_high, widening) from a non-empty matched set.

    The observed envelope of what those changes actually cost, pushed out by the small-sample
    allowance and rounded onto WARP-1402's grid. THE SAME GRID ON PURPOSE: two layers of one
    record whose bounds sit on different grids would make the envelope's provenance ambiguous,
    and a reader could not tell which layer a committed bound came from.

    Rounding may coarsen a range and is never allowed to collapse one: a point estimate is the
    one thing this schema refuses, so the guard widens rather than accepting it."""
    if not matched:
        raise ValueError("cannot predict from an empty matched set: this is the stand-down "
                         "path and it returns no number at all, by design")
    E = _estimate()
    rt = round_tokens if round_tokens is not None else E._round_tokens
    st = step if step is not None else E.ROUND_STEP
    toks = [tokens_of(rec) for _d, rec in matched]
    obs_low, obs_high = min(toks), max(toks)
    widen = widening_pct(len(matched))
    low = rt(int(obs_low) * 100 // (100 + widen))
    high = rt(int(obs_high) * (100 + widen) // 100)
    if high <= low:
        high = low + st
    return low, high, obs_low, obs_high, widen


def _standdown(code, corpus_len, excluded, candidates, era, matched=0, detail=None):
    """The stand-down report, in ONE shape.

    NO `low` AND NO `high` KEY, which is the load-bearing property of this module: a null
    bound is a value a consumer formats as 0 or feeds into arithmetic, and an absent key is a
    KeyError. Everything a reader needs to understand the refusal is here instead - the code,
    the sentence, the corpus size, the exclusions and how many comparables were found."""
    rep = {
        "schema": SCHEMA,
        "predicted": False,
        "reason_code": code,
        "reason": REASONS[code],
        "layer": LAYER,
        "basis": BASIS,
        "corpus_records": corpus_len,
        "candidates": candidates,
        "matched": matched,
        "matched_specs": [],
        "min_matches_required": MIN_MATCHES,
        "match_radius": MATCH_RADIUS,
        "era": era,
        "excluded": dict(excluded),
    }
    if detail:
        rep["detail"] = detail
    return rep


def analogy(target_spec, target_vector, corpus, era_of=None, era=None,
            radius=MATCH_RADIUS, min_matches=MIN_MATCHES):
    """(layer or None, report): the whole of this item, as one pure function.

    The layer is a contribution for WARP-1402's estimate record, ready to hand to
    `estimate.build_record`. It is None whenever the evidence does not support a number, and
    the report always says which of the declared reasons applied.

    Pure over what it is handed: no clock, no file, no process, no write."""
    corpus = corpus if corpus is not None else []
    refuse_malformed(corpus)
    # THE ERA THIS LAYER REPORTS IS THE ONE IT ACTUALLY WINDOWED BY, and never the one it was
    # merely told about. An era name with no reader behind it would put a model identity into a
    # committed record that nothing had checked a single actual against, which is the same
    # species of dishonesty as a declared prior presented as a measurement.
    #
    # `window` IS THEREFORE THE ONLY ERA ANY PATH BELOW MAY REPORT - all six of them, the two
    # early stand-downs, the two evidence stand-downs, the layer's own inputs and the success
    # report - because the one whose output gets COMMITTED is the success path, and a rule applied
    # to the paths that commit nothing is not a rule. `era` is read exactly once more, in the
    # `era_of is not None` test on the next line, and never reported.
    window = era if era_of is not None else None
    empty = {k: 0 for k in EXCLUSIONS}
    if target_vector is None:
        return None, _standdown(UNREADABLE_TARGET, len(corpus), empty, 0, era_label(window))
    if not corpus:
        return None, _standdown(NO_CORPUS, 0, empty, 0, era_label(window))
    matched, excluded, candidates = evidence(
        corpus, target_spec, target_vector, era_of=era_of, era=window, radius=radius)
    if candidates == 0:
        # WHICH KIND OF NOTHING IT IS. Four different facts wear the same shape here, and
        # collapsing them would hide the only one a reader can act on: a corpus that is empty,
        # a corpus whose loop never recorded spend (this repository today), a corpus measured
        # entirely in an earlier model era, and a corpus holding nothing this spec could be
        # compared with. The exclusion breakdown rides along as the detail either way, so the
        # sentence a reader gets and the counts behind it can never tell different stories.
        if excluded["other_era"] or excluded["unreadable_era"]:
            code = NO_SAME_ERA_ACTUALS
        elif excluded["no_spend"] or excluded["zero_tokens"]:
            code = NO_RECORDED_ACTUALS
        elif excluded["self"] or excluded["unreadable_features"]:
            code = NO_COMPARABLE_RECORDS
        else:
            code = NO_CORPUS
        return None, _standdown(
            code, len(corpus), excluded, 0, era_label(window),
            detail="not one of %d record(s) is usable as a comparable: %s"
                   % (len(corpus), ", ".join("%s=%d" % (k, excluded[k]) for k in EXCLUSIONS)))
    if len(matched) < min_matches:
        return None, _standdown(
            TOO_FEW_MATCHES, len(corpus), excluded, candidates, era_label(window),
            matched=len(matched),
            detail=("%d comparable change(s) inside a match radius of %d, and %d are required; "
                    "%d recorded actual(s) were available but describe work too far from this "
                    "spec to reason from" % (len(matched), radius, min_matches, candidates)))
    low, high, obs_low, obs_high, widen = predict(matched)
    specs = [rec["spec"] for _d, rec in matched]
    E = _estimate()
    layer = {
        "layer": LAYER,
        "basis": BASIS,
        "low": low,
        "high": high,
        "note": "observed envelope of %d comparable shipped change(s), widened %d percent for "
                "sample size; no mean and no trimming, because a mean of a few changes is a "
                "number nobody spent" % (len(matched), widen),
        "inputs": {
            "matched_specs": len(matched),
            "matched_spec_ids": " ".join(specs),
            "max_matched_distance": matched[-1][0],
            "match_radius": radius,
            "min_matches_required": min_matches,
            "candidates": candidates,
            "corpus_records": len(corpus),
            "era": era_label(window),
            "observed_low": int(obs_low),
            "observed_high": int(obs_high),
            "sample_widening_pct": widen,
            "target_risk": RISK_ORDER[target_vector[0]],
            "target_acceptance_criteria": target_vector[1],
            "target_regression_surface": target_vector[2],
            "target_protected_touch": E.YES if target_vector[3] else E.NO,
        },
    }
    report = {
        "schema": SCHEMA,
        "predicted": True,
        "reason_code": None,
        "reason": None,
        "layer": LAYER,
        "basis": BASIS,
        "corpus_records": len(corpus),
        "candidates": candidates,
        "matched": len(matched),
        "matched_specs": specs,
        "min_matches_required": min_matches,
        "match_radius": radius,
        "era": era_label(window),
        "excluded": dict(excluded),
        "low": low,
        "high": high,
        "observed_low": int(obs_low),
        "observed_high": int(obs_high),
        "sample_widening_pct": widen,
        "distances": [d for d, _rec in matched],
    }
    return layer, report


# ---------------------------------------------------------------------------------------
# The seam to the estimate record.
# ---------------------------------------------------------------------------------------

def augment(spec_path, at, corpus, era_of=None, era=None, protected=(), root=None,
            corpus_mod=None):
    """(record, report): the committed estimate for one spec with this layer added when the
    evidence supports it, and WITHOUT it when it does not.

    ON A STAND-DOWN THE RECORD IS BYTE-IDENTICAL TO WHAT W2 ALONE PRODUCES. That is the
    adoption-safety property stated as an equality rather than a promise: adding this layer to
    a repository with no actuals changes nothing at all about what gets committed.

    The record is assembled by `estimate.build_record` through `estimate.propose`, which is the
    seam WARP-1402 declared for exactly this: the derived fields are computed and checked in one
    place, so this module cannot commit a range its own layers do not support."""
    E = _estimate()
    C = corpus_mod if corpus_mod is not None else _corpus()
    feats = target_features(spec_path, C, protected)
    layer, report = analogy(feats.get("spec_id"), vector(feats), corpus,
                            era_of=era_of, era=era)
    extra = [layer] if layer is not None else []
    return E.propose(spec_path, at, protected=protected, root=root,
                     extra_layers=extra), report


# ---------------------------------------------------------------------------------------
# Wiring the real repository, and reporting. The only place the real corpus, the real event
# log and the real era ledger meet; every function above stays pure over injected data.
# ---------------------------------------------------------------------------------------

def repo_basis(root=None):
    """(corpus, era_of, era) for a real repository, assembled from the shipped organs.

    Reads only. The corpus comes from toe_corpus.build over the recorded event stream, the
    protected set from estimate.protected_paths and the era window from toe_normalize's ledger
    reader and era stamper. Nothing here is a second implementation of any of it.

    EVERY ONE OF THOSE READS IS ROOTED AT `root`, including the protected set. That is why the
    protected paths come from estimate.protected_paths, which takes a root and goes through the
    ONE parser, rather than from policy_check.protected_patterns, which reads the module's own
    repository whatever root it is asked about. A wiring function that silently mixed one
    repository's policy into another repository's corpus would make a hermetic test measure this
    repository instead of its fixture."""
    base = Path(root) if root else ROOT
    V = _validate()
    C = _corpus()
    N = _normalize()
    E = _estimate()
    M = _mod(".veldo/metrics.py", "veldo_metrics_analogy")
    events = N.read_events(base / ".veldo" / "events.jsonl")
    shifts, _errs = N.load_ledger(base / N.ERAS_DIR, V.parse_yamlish, V.fail, M.parse_iso)
    era_list = N.eras(shifts)
    corpus = C.build(specs_dir=base / "specs", events=events,
                     protected=E.protected_paths(base))
    era_of = (lambda spec_id: N.era_of(spec_id, events, era_list, C, M.parse_iso))
    return corpus, era_of, planning_era(era_list)


def render_lines(report):
    """The report as text, every figure drawn from the report so a reader and a consumer of the
    JSON can never see two different numbers."""
    if not report.get("predicted"):
        out = ["analogy: STANDING DOWN, no number produced (%s)" % report["reason_code"],
               "  %s" % report["reason"]]
        if report.get("detail"):
            out.append("  %s" % report["detail"])
        out.append("  corpus %d record(s), %d usable comparable(s), %d matched, %d required"
                   % (report["corpus_records"], report["candidates"], report["matched"],
                      report["min_matches_required"]))
        out.append("  excluded: %s" % ", ".join(
            "%s=%d" % (k, report["excluded"][k]) for k in EXCLUSIONS))
        out.append("  this is not a finding: a layer with no evidence produces no range, and "
                   "the estimate still commits the layers that do have one")
        return out
    return [
        "analogy: %d to %d tokens from %d comparable shipped change(s), era %s"
        % (report["low"], report["high"], report["matched"], report["era"]),
        "  matched: %s" % ", ".join(report["matched_specs"]),
        "  observed %d to %d, widened %d percent for sample size (distances %s)"
        % (report["observed_low"], report["observed_high"],
           report["sample_widening_pct"], report["distances"]),
        "  corpus %d record(s), %d usable comparable(s) inside radius %d"
        % (report["corpus_records"], report["candidates"], report["match_radius"]),
    ]


def _cli(argv):
    ap = argparse.ArgumentParser(
        prog="toe_analogy.py",
        description="Predict a range for a spec from what similar shipped specs ACTUALLY cost, "
                    "or decline and say why. Advisory only: nothing here gates, blocks or "
                    "delays any work, and with no recorded actuals it produces no number.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    rp = sub.add_parser("report", help="the analogy for one spec over this repository")
    rp.add_argument("--spec", required=True, help="path to the spec file")
    rp.add_argument("--json", action="store_true", help="machine-readable")
    pr = sub.add_parser("propose", help="the estimate record with this layer where it applies")
    pr.add_argument("--spec", required=True, help="path to the spec file")
    pr.add_argument("--at", required=True,
                    help="the date this estimate is committed, YYYY-MM-DD. REQUIRED and never "
                         "read from a clock, so the same spec on the same date is the same bytes")
    sub.add_parser("model", help="the declared features, weights and stand-down reasons")
    a = ap.parse_args(argv)

    if a.cmd == "model":
        print("matched on (pre-build features only):")
        for k in sorted(FEATURE_WEIGHTS):
            print("  %-22s weight %d" % (k, FEATURE_WEIGHTS[k]))
        print("never matched on (these are what the work COST): %s" % ", ".join(OUTCOME_BLOCKS))
        print("match radius %d, minimum comparables %d, small-sample slack %d percent-points "
              "with a floor of %d" % (MATCH_RADIUS, MIN_MATCHES, SMALL_SAMPLE_SLACK,
                                      MIN_WIDEN_PCT))
        print("stand-down reasons:")
        for k in sorted(REASONS):
            print("  %-26s %s" % (k, REASONS[k]))
        return 0

    E = _estimate()
    try:
        corpus, era_of, era = repo_basis()
        if a.cmd == "report":
            feats = target_features(a.spec, _corpus(), E.protected_paths())
            _layer, rep = analogy(feats.get("spec_id"), vector(feats), corpus,
                                  era_of=era_of, era=era)
            if a.json:
                print(json.dumps(rep, indent=1, sort_keys=True))
            else:
                for line in render_lines(rep):
                    print(line)
            return 0
        rec, rep = augment(a.spec, a.at, corpus, era_of=era_of, era=era,
                           protected=E.protected_paths())
    except (ValueError, OSError) as e:
        print(str(e), file=sys.stderr)
        return 1
    for line in render_lines(rep):
        print(line)
    print(E.render_record(rec), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
