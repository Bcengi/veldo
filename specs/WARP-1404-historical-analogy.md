---
schema: veldo.spec/v1
id: WARP-1404
title: Historical analogy - the strongest estimating layer, and the one that declines when the
  corpus cannot support a number
status: ready
risk: standard - a new module that reads the actuals corpus and a spec and writes nothing at all.
  No gate stage is added, nothing is enforced, and a repository with no recorded actuals gets a
  byte-identical estimate record to the one W2 alone produces. It is not low because this is the
  layer whose basis flips a record to `calibration: calibrated`, so a range this layer produces is
  the one number in the plan that later surfaces are entitled to trust; a matcher that read outcome
  data, or a stand-down that returned a zero instead of nothing, would put a confident figure into
  the budget roll-up (W8) and the reconciliation (W5) with no evidence under it and no reader able
  to tell.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0014
work: W4
depends_on: [WARP-1401, WARP-1402]
placement: [metrics]
footprint:
  - ".veldo/toe_analogy.py"
  - "engine/.veldo/toe_analogy.py"
  - "scripts/suites/16_warp_1404_historical_analogy.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/WARP-1404-historical-analogy.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      WITH NO RECORDED ACTUALS IT PRODUCES NO NUMBER, AND THE REFUSAL CARRIES NO BOUND AT ALL. The
      layer stands down with a reason code from a CLOSED declared vocabulary and a sentence naming
      why, and the stand-down report has NO `low` and NO `high` key: not zero, not null, ABSENT, so
      a consumer that skips `predicted` gets a KeyError rather than a confident figure. Driven over
      four distinct zero-evidence shapes, each required to give its OWN code and not a generic one:
      an empty corpus, a corpus whose records carry no spend (measured: THIS repository, 174
      shipped records, 0 with spend), a corpus measured entirely in an earlier model era, and a
      corpus whose only record is the target's own. Paired with the positive control that a seeded
      corpus through the SAME function does produce a range, so the refusals are the evidence's
      doing and not a function that always declines.
  - id: AC2
    text: >
      IT MATCHES ON PRE-BUILD FEATURES ONLY, AND THAT IS MEASURED RATHER THAN PROMISED. The declared
      match set is exactly the mechanical features knowable before the work starts (risk tier,
      acceptance-criteria count, declared regression surface, protected-path touch), read through
      WARP-1401's ONE feature reader so target and comparable are the same shape by construction.
      Nothing in a record's `cycles`, `spend` or `git` blocks may influence which specs are
      comparable, because predicting an outcome from an outcome scores well on history and is
      useless on the only spec anybody needs an estimate for. Proven behaviourally: two records
      with IDENTICAL features and wildly different cycles, git and cost are the same distance from
      the target and both match, while a record differing only in a PRE-BUILD feature by more than
      the radius does not. The target never matches its own record, and that exclusion is counted.
  - id: AC3
    text: >
      THE RANGE IS AN OBSERVED ENVELOPE THAT CITES ITS EVIDENCE, AND THE SMALL-SAMPLE ALLOWANCE
      TIGHTENS STRICTLY AS HISTORY ACCUMULATES. The layer's bounds are the lowest and highest token
      count among the matched changes, pushed out by a declared allowance of SMALL_SAMPLE_SLACK over
      the number of matches and floored so it never reaches zero; no mean, no median, no trimming.
      The layer NAMES the shipped specs it matched in its inputs, together with the observed
      envelope, the widening it applied, the radius, the era window and the target features it
      matched on, so a later reconciliation can attribute an error instead of only scoring it.
      Driven: holding the observed actuals fixed, more matched changes give a STRICTLY narrower
      range at every step until the floor, the allowance is non-increasing in the sample size
      across a swept range, and below the declared minimum of comparables there is no range at all.
      Bounds land on WARP-1402's rounding grid, and rounding may coarsen a range and never collapse
      it into a point.
  - id: AC4
    text: >
      MODEL IDENTITY WINDOWS THE EVIDENCE, THROUGH THE ONE ERA READER AND NOT A SECOND ONE (D5).
      Comparables are restricted to the planning era, which is the latest era the WARP-1406 ledger
      declares, and actuals from an earlier era are EXCLUDED AND COUNTED rather than blended, with
      no cross-era conversion factor invented anywhere. Proven twice over: with an injected era
      reader, and end to end over a hermetic repository root carrying a real capability-shift
      ledger and real spend events, where a spec whose spend predates the shift is excluded and one
      after it is not. With no ledger recorded there is exactly one era, so the windowing excludes
      nothing and a repository that records no shift is unaffected, which is the control that
      proves the exclusion is the LEDGER's doing.
  - id: AC5
    text: >
      ADOPTION SAFE, ADVISORY, AND IT CAN ONLY EVER WIDEN WHAT W2 COMMITTED. On a stand-down the
      estimate record this module produces is BYTE-IDENTICAL to the one estimate.propose produces
      alone, asserted as an equality of the rendered bytes, so adding this layer to a repository
      with no actuals changes nothing that gets committed. When the layer IS present the committed
      range is the envelope of both layers, never narrower than the proxy's own on either bound,
      and the record's calibration flips to `calibrated` only because a corpus-grounded basis is
      present. Nothing in scripts/verify.sh names this module, the module writes no file and starts
      no process, a malformed corpus is REFUSED BY NAME while a merely unusable record is counted,
      and the real validate.check_spec returns the identical result for a spec with and without
      this layer's record beside it. Paired with the negative control that the same validator does
      refuse a genuinely broken spec under the same root.
required_evidence: [unit]
rollback: >
  Delete the module, its engine copy and the suite fragment, and remove the suite from the manifest
  (regenerating scripts/suites/requires.json and specs/index.md). Nothing reads it, no gate stage
  runs it, it writes no state at all, and every estimate record already committed stays valid
  because this layer is optional in the schema W2 declared. A repository that recorded no actuals
  is unaffected either way, because this layer produced nothing there in the first place.
---

## Outcome

The plan's three estimating layers run weakest to strongest. W2 built the record and the structural
proxy, whose token scale is a declared prior with nothing behind it. W3 adds an agent's own reading
of the spec. This is the strong one: the only layer whose numbers come from changes that actually
happened, and therefore the only one that can make a record read `calibration: calibrated`.

It is also the only layer that can be entitled to nothing. The other two can always speak: a spec
always has acceptance criteria to count and an agent can always read a spec. An analogy needs
history, and history either exists or it does not.

## The measured situation this ships into, which is the whole difficulty

WARP-1401 measured this repository's corpus: 148 shipped specs at the time, 95.3 percent cycle
coverage, and **0 percent spend coverage**, because a token count is not knowable from inside a
repository and nothing had ever emitted one. W1b shipped `.veldo/spend.py` as the emitter; nothing
has used it yet.

**Measured again by this item, over the corpus as it stands today: 174 shipped records, and not one
carries recorded token spend.** So the honest output of this layer in this repository, today, is no
number at all. That is not a degraded mode to be apologised for, it is the correct answer, and the
design problem of this item is making the correct answer impossible to mistake for a small one.

Hence the shape of the refusal. A stand-down returns `None` for the layer and a report whose
`predicted` is false, and that report **carries no `low` and no `high` key at all**. A null bound is
a value a consumer formats as 0, or sums into a budget; an absent key is a KeyError, which is a
refusal a caller cannot walk past. The reason is a code from a closed vocabulary, so a consumer
switching on it has a complete set of cases, and the exclusion breakdown rides along so the sentence
a reader gets and the counts behind it can never tell different stories.

## The leakage rule, which decides what a comparable even is

An estimate is committed before the work. So the features that choose comparables have to be the
features a spec has before anything has been built: the risk tier, the acceptance-criteria count,
the declared regression surface, and whether the footprint touches a protected path.

Everything in the corpus record's `cycles`, `spend` and `git` blocks is excluded, and the exclusion
is declared in the module rather than left to discipline. Those blocks are what the work COST. A
matcher that read them would find "similar" specs by how much trouble they turned out to be, score
beautifully against history, and be unusable on the only spec anybody ever needs an estimate for:
the one not yet built. The one place outcome data legitimately appears is as the thing predicted
FROM once a comparable has been chosen.

The target also never matches its own record, so a re-estimate of a shipped spec cannot predict its
own cost perfectly and call that accuracy.

## What tightens and what does not

The plan asks for a layer that tightens as history accumulates. Two different things could mean
that, and only one of them is honest.

The SMALL-SAMPLE ALLOWANCE tightens: the observed envelope is pushed out by a declared allowance
that shrinks strictly with the number of matched changes, down to a floor it never passes, because a
converged estimator is still an estimator.

The OBSERVED ENVELOPE is data and may widen. When the fifth comparable costs three times the first
four, the range gets wider, and that is the corpus reporting a spread that was always there and had
not yet been seen. A module that narrowed the observed envelope as its sample grew would be
manufacturing confidence out of ignorance, which is exactly what NG6 forbids. So there is no mean,
no median and no outlier trimming: a mean of three changes is a number nobody spent, and trimming an
outlier is a judgement that one recorded cost was wrong, which nothing here has evidence for.

## Model identity, delegated rather than re-derived (D5)

A token stops meaning what it meant when the model changes, so actuals from either side of a
capability shift are not in the same unit. That judgement already has a home: WARP-1406 records
capability shifts as a durable era ledger, turns them into half-open intervals and stamps every
actual with the era its spend was measured in. This layer reuses that reader and windows its
evidence to the planning era, which is the latest era the ledger declares, on the same argument
WARP-1406's peg uses: planning happens in the era you are in. Earlier eras are excluded and counted.
No cross-era conversion factor is invented anywhere, because a multiplier claiming to convert one
model's tokens into another's is a guess wearing a measurement's clothes.

With no ledger recorded there is exactly one era and the windowing excludes nothing, which is the
control that makes the exclusion attributable to the ledger rather than to this module.

## Out of scope

- **Superseding the structural prior.** WARP-1402's schema notes that a range gets sharper by a
  strong layer REPLACING a weak one, and assigns that judgement to this item. This item declines to
  take it, on the evidence: replacing the proxy NARROWS the committed range, and the only thing that
  could justify a narrowing is a measurement that the analogy is more accurate than the prior. That
  measurement is W5's, the estimator's own mean error and calibration curve. Until it exists both
  layers ride, so this module can only ever widen what W2 committed. A narrowing taken on the
  strength of an argument rather than a measurement is the false precision this plan forbids.
- Any enforcement. Nothing here gates, blocks, deprioritizes or delays work on an estimate (NG1,
  D4). No gate stage is added and scripts/verify.sh is untouched.
- Reconciliation, recalibration and the estimator's accuracy curve (W5); the normalized display
  point (W6); the judgement-load pair (W7); the plan roll-up and dollar conversion (W8); the
  per-area map (W9).
- A shared validator for the actuals record. This layer refuses structural garbage over exactly the
  three fields it reads and counts everything else as unusable evidence, which is a different
  question from "is this record well formed". The shared home for the latter would be WARP-1401's
  own module, which this item does not own; the note is recorded with this item's delivery notes
  rather than acted on here.
- The capability manifest entry. `.veldo/capabilities.yaml` is integrated separately; the exact line
  to add is recorded with this item's delivery notes.
