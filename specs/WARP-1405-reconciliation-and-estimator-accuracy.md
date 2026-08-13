---
schema: veldo.spec/v1
id: WARP-1405
title: Reconciliation and the estimator's own accuracy - the estimate, the actual and the variance
  stored at ship, the scale refitted from the growing ledger, and the estimator's own hit rate and
  calibration curve open to anyone
status: ready
risk: standard - a new module that reads the committed estimates, the actuals corpus and its own
  record ledger, and whose only write is a create-only record per shipped spec. No gate stage is
  added, nothing is enforced, and a repository that reconciles nothing is byte-identically
  unaffected. It is not low because this is the module that tells everyone how much an estimate is
  worth: a variance a record could edit after the fact, a hit rate computed over only the changes
  that happened to work, or a refit scored on the same records it was fitted from would each look
  exactly like a working measurement while making every number above it more confident and less
  true.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0014
work: W5
depends_on: [WARP-1402]
placement: [metrics]
footprint:
  - ".veldo/toe_reconcile.py"
  - "engine/.veldo/toe_reconcile.py"
  - ".veldo/examples/toe-reconciliation-example.yaml"
  - "engine/.veldo/examples/toe-reconciliation-example.yaml"
  - "scripts/suites/15_warp_1405_reconciliation.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/WARP-1405-reconciliation-and-estimator-accuracy.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      THE RECORD HOLDS THE ESTIMATE, THE ACTUAL AND THE VARIANCE, AND IT CANNOT LIE ABOUT ANY OF
      THEM. veldo.toe_reconciliation/v1 stores one record per spec, keyed by filename, carrying the
      committed range, its commit date and calibration, the recorded actual with a declared source,
      the spec's mechanical features and the structural weight and both token scales. Four fields
      are DERIVED and RECOMPUTED by the validator rather than trusted: `outcome`, `error_pct`,
      `implied_scale` and `scale_error_pct`, so a variance edited after the actual was known is
      refused by name. The variance is measured against the BOUND THE ACTUAL MISSED and is zero
      inside the range, never against a midpoint the estimate schema refuses to have (NG6). A point
      or inverted range, a non-integer or zero actual, a reconciliation dated before the estimate it
      scores, an unknown key, an unknown vocabulary value and a half-present block are each refused
      by name; the unit, calibration, bounds, rounding and scalar-rendering rules are all
      estimate.py's, never a second spelling. Selftests drive each refusal, pair each with the
      positive control that the same record validates once corrected, and add the tightness control
      that a legal optional edit is ACCEPTED. The committed example record is checked as real bytes
      with its derived fields recomputated from its own numbers.
  - id: AC2
    text: >
      EXACTLY ONE RECONCILIATION PER SHIPPED ESTIMATED SPEC, IDEMPOTENTLY, AND EVERY UNRECONCILED
      ESTIMATE EXPLAINED. Pairing is deterministic and pure over the estimates and the corpus it is
      handed, reads no clock, and writing is IDEMPOTENT BY BYTES: the second pass creates nothing
      and reports every record unchanged, so the pass needs no bookkeeping about whether it already
      ran. A record whose bytes differ is refused by name unless replace is asked for explicitly,
      because a recorded variance that quietly rewrites itself is a scoreboard, and a SPEC ID THAT
      CANNOT BE A FILENAME is refused BEFORE it becomes a path, by delegation to the claim ledger's
      one definition of an id that cannot be stored faithfully rather than by a second copy of that
      rule, with the existence question asked after the directory exists because a guard consulted
      before the path can resolve is not a guard. Every estimate that
      does NOT reconcile is a named standdown row, never a silent omission: not shipped, no spend
      recorded, an actual that is not an integer token count, or an estimate the estimate module
      itself refuses. Selftests drive all four standdown reasons in one pass, require the ledger to
      exclude exactly those, and add the control that the same specs DO reconcile once the data is
      there, so the standdowns are the data's doing and not a reconciler that refuses what it does
      not recognise.
  - id: AC3
    text: >
      THE ESTIMATOR'S OWN ACCURACY IS MEASURED AND INSPECTABLE, AND AN EMPTY LEDGER SAYS SO RATHER
      THAN SCORING ZERO - the AC that matters most. `accuracy` reports the hit rate, the mean and
      mean-absolute variance, the worst miss, the bias direction and the MEAN RANGE WIDTH (because a
      hit rate alone is gameable by widening), over the whole ledger or a trailing window, and
      `curve` renders one point per reconciliation carrying the cumulative and trailing figures, so
      a converging estimator and a drifting one look different on the page. With NO records every
      figure is None, `measured` is False and the reason says the estimator has no measured accuracy
      yet; the curve is empty rather than a flat line at zero; the refit and the comparison stand
      down with reasons. MEASURED OVER THIS REPOSITORY, WITH THE BRANCH CHOSEN BY WHAT THE
      MEASUREMENT FINDS AND NEVER PINNED TO TODAY'S ABSENCE OF DATA: the live event log is
      non-empty, the raw spend predicate and toe_corpus's own reader AGREE over every spec id that
      log names on which of them carry tokens, cost_usd or human_minutes and on the figures
      themselves, EVERY PROBLEM THE LEDGER READER REPORTS NAMES THE RECORD IT IS ABOUT - driven over
      records planted malformed in the suite, never by requiring the tree to hold none, because a
      present-but-malformed record is AC5's named finding and not a red gate - and the honesty rule
      above is
      then required on the arm the live ledger puts it on - the stand-down when nothing is recorded,
      which is the branch running here today, and the measured, internally reproducible figures when
      something is - with the paired control that the same predicate DOES find spend in a seeded
      event. Recording spend and recording a reconciliation are the SANCTIONED uses of this layer, so
      no criterion here may require the measured set to be empty. Selftests
      also drive a seeded mixed ledger where all three outcomes appear with a 40 percent hit rate
      (the anti-vacuity control that the scorer is not a constant), require every curve point to
      equal the accuracy function over the same prefix, and require the curve to MOVE.
  - id: AC4
    text: >
      RECALIBRATION SEPARATES A WRONG SCALE FROM A WRONG STRUCTURE, IS SCORED OUT OF SAMPLE, AND
      REFUSES TO OVERSTATE ITSELF. Because WARP-1402 records the structural weight and the token
      scale separately, every record yields the IMPLIED SCALE that would have put its point on its
      actual; `fit` takes the lower median as the refitted scale, names the change it came from,
      reports the DISPERSION of the sample, stands down below a declared minimum sample and refuses
      to blend two eras (D5). The refit is delivered as a `recalibrated` layer in estimate.py's
      existing vocabulary through its own record assembler, its range is the OBSERVED envelope of
      implied scales floored so that agreement cannot become false precision, and its inputs
      reproduce its own bounds. THE FLOOR IS A PROPERTY OF THE TOKEN BOUNDS A READER SEES AND IS
      TESTED THERE, not only of the scale envelope they were fitted from: applying it to the scales
      and then rounding the bounds recollapsed the range at small structural weights and low fitted
      scales, which produced the exact sentence this floor exists to refuse (a range ONE ROUNDING
      STEP wide) on a layer whose own inputs recorded that the floor had been applied. It is
      asserted as a TOTAL property over a swept grid of weights and envelopes rather than at one
      point, with the grid required to reach the region where a returned range is only a few
      rounding steps wide, and with both floor arms present in it. It is scored LEAVE-ONE-OUT: on
      a ledger with a planted 3x bias the held-out refit takes the hit rate from 0 to 100 percent
      and the mean absolute error to zero.
      Three controls sit beside that claim: on an already-calibrated ledger the refit recovers the
      declared scale and reports NO improvement; on a ledger whose implied scales span 16x the
      improvement is bought with WIDTH and the width delta says so on the same line; and the
      envelope still only widens, so sharpening a range stays the caller's explicit judgement.
  - id: AC5
    text: >
      ADOPTION SAFE, AND NEVER A BLOCKER - PLAN-0014's C3 and NG1. With no records present every
      reader stands down silently, creating nothing and reporting nothing as a finding, and the
      CLI's check exits 0 saying so; a record that is PRESENT and malformed is named rather than
      quietly dropped, so an accuracy number is never computed over a silently smaller ledger.
      Nothing in scripts/verify.sh or the contract validator names this module, and the module names
      no subprocess, socket or urllib import and no clock. THAT LAST CLAUSE IS ABOUT THIS FILE'S OWN
      BYTES AND NOT ABOUT ITS CALL GRAPH, and the difference is measured rather than reasoned from
      the import list: the PURE surfaces (pair, accuracy, curve, fit, holdout, compare,
      validate_record, load_dir, check_dir, recalibrated_layer, render) are counted spawning ZERO
      processes with subprocess.run wrapped, while build_view, which is the body of the report CLI,
      reaches git through toe_corpus at one `git log` per spec, so the fan-out of one report is
      O(specs) git invocations and the module may not claim it cannot spawn a process. And the
      load-bearing pair: a spec with NO
      reconciliation, a spec with a VALID one beside it, and a spec with a MALFORMED one beside it
      all return the identical result from the real validate.check_spec, with the negative control
      that the same validator DOES refuse a genuinely broken spec under the same hermetic root - so
      absence or breakage of a reconciliation provably cannot invalidate a spec, and the pass is a
      measurement rather than an absence.
required_evidence: [unit]
rollback: >
  Delete the module, its engine copy, the example record and the suite fragment, and remove the
  suite from the manifest (regenerating scripts/suites/requires.json and specs/index.md). Nothing
  reads it, no gate stage runs it, and it writes nothing unless explicitly asked to; committed
  records are inert data and keep their history whether the module is present or not.
---

## Outcome

PLAN-0014's W1 built the corpus of what changes actually cost and W2 built the record of what a
change was expected to cost. This is the item that puts the two together and makes the estimator
improve instead of merely keeping score: at ship the estimate, the actual and the variance are
stored beside the spec's features; the one number in the estimator that was never measured is
refitted from that accumulating ledger; and the estimator's own accuracy becomes a measured,
inspectable, converging number rather than a feeling.

Legacy estimates never reconciled against a real unit, so they never improved. That is the whole
difference this item exists to make, and it is why the honesty of its empty case matters more than
the elegance of its full one.

## What the reconciliation has to make possible

An actual is one number and a committed estimate is a range, so a naive reconciliation can say
nothing better than "in" or "out". Two decisions make it say more.

The first is how the variance is measured. Grading a range by its own midpoint would invent the
point estimate the schema refuses (NG6) and then hold the estimator to it, so the variance here is
ZERO inside the range and otherwise the signed distance past the bound that was missed. That keeps
two facts apart which a single number blurs: how OFTEN the range held the truth, and how WRONG it
was when it did not.

The second is what the record carries. WARP-1402's proxy multiplies a structural WEIGHT it derives
from the spec by a token SCALE it derives from nothing, and records both. So this ledger derives the
IMPLIED SCALE for every change: the tokens per structural unit that would have put that spec's point
exactly on its actual. Implied scales agreeing across specs means the structure ranks work correctly
and one multiplier is wrong, which is refittable. Implied scales disagreeing means the structure does
not explain the variance, and no single scale will ever fix it. The module reports the dispersion and
refuses to draw that line for a reader, because the threshold would be invented; what it does
instead is carry the disagreement INTO the refitted range, so uncertainty is visible rather than
footnoted.

## The measured finding of this item

`fit` and `accuracy` over this repository return nothing, and that is the honest output.

**Measured against today's bytes: the event log is non-empty and NOT ONE recorded event carries
`tokens`, `cost_usd` or `human_minutes`.** That is WARP-1401's 0 percent spend coverage re-measured
rather than quoted, and it is measured in the suite rather than asserted here, with the control that
the same predicate does find spend in a seeded event. So no shipped change has an actual, no
reconciliation record can be derived, the ledger is empty, and every surface reports that the
estimator has NO MEASURED ACCURACY YET.

The distinction that decides whether this module is honest is one line wide: `accuracy([])` returns
`measured: False` with a reason, never a hit rate of zero. A hit rate of zero means the estimator
missed every time. An unmeasured estimator has never been scored. The method's companion writing
promises a line like "81 percent of the last 50 units in range"; this module renders exactly that
shape, and today the true rendering of it is that there is nothing to render.

**That finding is DATED, and it is not an invariant.** The first revision of AC3 and of the suite
wrote it down as one: two assertions required the live spend set to be EMPTY and the live ledger to
be an EMPTY MAP, so the check held only while nobody used the layer. MEASURED, in a scratch copy of this
repository: one legitimate `spend.py record --spec WARP-0100 --basis harness_reported --tokens
750000`, the sanctioned writer doing the exact thing this layer exists for, took the suite from 53
passed to 52 passed and 1 failed. A gate that reddens on the first real use of the feature it
measures is worse than a missing check, because whoever hits it learns that the gate is noise. So the
criterion and the assertions now keep the partition and the reader agreement unconditional and make
only the arm that NEEDS there to be no data conditional. The teeth were re-measured on both arms:
with the spend recorded, an `accuracy` that scores an empty ledger 0 instead of standing down is 3
RED; with a real reconciliation record present in the tree, an `error_pct_of` that reports 0 for an
actual above the committed high is 9 RED where the same mutation over an empty ledger is 8, and a
`render` that reports a measured ledger as NOT MEASURED is 1 RED.

## Two things the build changed on purpose

**A fitted range needs a floor, and the floor belongs on the bounds rather than on the inputs.**
The refitted range is the observed envelope of implied scales, which is the right instinct: records
that disagree should produce a wide range. But the first version of that arithmetic, driven over a
seeded ledger where every actual sat at exactly 3x its point, produced a range ONE ROUNDING STEP
wide. Five records agreeing exactly is not evidence that a sixth change is predictable to a tenth of
a percent, so a declared minimum spread floors the range and every layer records whether the floor
was applied. False precision arriving through measured data is still false precision.

THAT FIRST FIX WAS APPLIED IN THE WRONG PLACE AND AN INDEPENDENT REVIEW REFUTED AC4 FOR IT. The
floor widened the SCALE envelope and the bounds were then rounded to the step, so the rounding
recollapsed exactly the ranges the floor exists to widen: driven through five real specs at the
smallest structural weight the proxy can produce and a fitted scale well under the declared prior,
the shipped layer was 3000..4000, one rounding step wide, a 33 percent spread, while its own
recorded inputs said the floor had been applied and the estimate validator accepted it. A floor on
an input is not a floor on the output whenever anything between them rounds. The floor is now tested
and enforced again on the rounded token bounds, raised to the step ABOVE the minimum rather than
rounded to the nearer one, and the flag is decided after the rounding, so a layer that says it was
floored was floored. The check that names it is a property over a swept grid, because the version
that missed this evaluated one point where the bounds were hundreds of thousands of tokens apart and
rounding could not bite.

**A hit rate is gameable, so the width is never reported without it.** An estimator answering
"between one token and a billion" hits every time and reports zero error. The accuracy block
therefore carries the mean range WIDTH beside the hit rate, and the before/after comparison carries
the width delta, which is what turns "the refit improved the hit rate" over a wildly dispersed
ledger into the true sentence: it bought the hit rate with width. That pair was found by a negative
control failing, not by review.

## One residual, measured and recorded rather than claimed away

AC5's title says NEVER A BLOCKER, and for this item's own suite fragment that is now measured both
ways: a malformed record present in the tree leaves this fragment green, because the assertion over
it requires each reported problem to NAME its record rather than requiring there to be none.

THERE IS A REMAINING PATH TO A RED GATE AND IT IS NOT IN THIS ITEM'S FOOTPRINT, so it is stated here
instead of being fixed here. `scripts/suites/12_warp_1210_hardening_four.py` builds a relocated
engine fixture by copying `.veldo` out of this repository and then calling
`(root / ".veldo" / "reconciliations").mkdir()` with no `exist_ok`. So the FIRST reconciliation
record this repository records - valid or malformed, written by the sanctioned writer - makes that
copy carry the directory and that mkdir raise FileExistsError, which takes the whole unit stage down
with a traceback. MEASURED: with one valid record present, this fragment is green and suite 12 dies.
The one-word repair belongs to that item's owner, and until it lands, "never a blocker" is true of
this module and its fragment and not yet true of the gate.

## Out of scope

- Any enforcement. Nothing here gates, blocks, deprioritizes or delays work on a variance or on an
  estimator's accuracy (NG1, D4). There is no new gate stage and verify.sh is untouched.
- Emitting spend. The actual comes from whatever the loop recorded, through toe_corpus's one spend
  reader; making the loop record more is not this item's work and cannot be, since a token count is
  not knowable from inside a repository.
- The judgment-load axis (W7), normalization to a display point (W6), the plan roll-up and dollar
  conversion (W8) and the per-area map (W9). This item reports in raw tokens, which is the recorded
  ground truth (C2), and leaves every display layer to the items that own one.
- The era ledger. The era stamp is optional and HANDED IN, so a repository keeping W6's ledger can
  window a refit by model identity (D5) without this module importing that organ or inventing an era
  of its own.
- Committing a reconciliation for this spec itself. It would need an actual this repository does not
  record, and inventing one to demonstrate the shape is exactly the fabrication the module refuses;
  the shape ships as a validated example record instead.
- The capability manifest entry. `.veldo/capabilities.yaml` is integrated separately; the exact line
  to add is recorded with this item's delivery notes.

## A note on module size

`.veldo/toe_reconcile.py` is 1401 lines, over the architecture contract's 1000-line `module_lines`
budget, which is declared `enforcement: review` by an explicit founder decision (2026-08-01)
precisely because module length is a reviewer's judgement rather than a fact a gate can settle. It
is stated here rather than left for a reviewer to discover. The item is three jobs the plan
deliberately put in one place (the ledger, the accuracy surface, the refit), a quarter of the file
is docstring at this repository's usual ratio, and splitting a schema from the derivation over it
would break the pattern estimate.py established for exactly this pairing. A reviewer who disagrees
has a clean seam to point at: the record and its writer on one side, the accuracy and the refit on
the other, with `_repo_inputs` already the single wiring point between them.
