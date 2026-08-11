---
schema: veldo.spec/v1
id: WARP-1408
title: Budgets - the roll-up, the dollar range and pacing, advisory by design, and the one place a
  number could have stopped work
status: ready
risk: standard - a new reader that sums records already committed beside specs, converts them at a
  declared rate and writes nothing at all. No gate stage is added and a repository with no
  estimates and no rate is byte-identically unaffected. It is not low for one reason: this is the
  item that hands a derived number to the PACING GOVERNOR, whose desired_workers returns ZERO
  WORKERS when a window's budget is spent, so a wrong bound or a zero-token window here would
  stall real work on an estimate, which is exactly what PLAN-0014's NG1 forbids and what no later
  item would be able to tell had happened.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0014
work: W8
depends_on: [WARP-1402]
placement: [metrics]
footprint:
  - ".veldo/toe_budget.py"
  - "engine/.veldo/toe_budget.py"
  - ".veldo/examples/toe-token-price-example.yaml"
  - "engine/.veldo/examples/toe-token-price-example.yaml"
  - "scripts/suites/15_warp_1408_budget_rollup.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/WARP-1408-budget-rollup-dollars-and-pacing.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      SUMMING RANGES IS NOT SUMMING POINTS, AND THE RULE IS DECLARED, RECOMPUTED AND NEVER
      NARROWING. v1 declares ONE roll-up rule, `sum_bounds`: the total low is the sum of the item
      lows and the total high the sum of the item highs, which is the only combination that
      assumes nothing about how the item errors relate. `mean`, `midpoint`, `pert` and
      `root_sum_square` are refused BY NAME from a declared table, each with its own reason
      (the first three produce a POINT; quadrature narrows a total by assuming an independence
      between estimates that all came from one estimator under one declared prior, which nobody
      has measured), and a rule named nowhere is refused with the declared set. THE PROPERTY THAT
      MAKES THE SUM SAFE TO READ: a range's spread is high over low, and under sum_bounds the
      total's spread is a weighted mediant of the item spreads, so it is SANDWICHED between the
      tightest and the widest item and can never be tighter than the narrowest thing inside it.
      A selftest drives a wide range (625 percent) against a narrow one (110 percent) and
      requires both sides of that sandwich, requires the exact bound sums separately so the
      sandwich cannot be reached by fudging the bounds, requires strict monotonicity in the item
      count with the anti-vacuity control that three item sets give three DISTINCT totals, and
      requires that a record which is malformed or in another unit is EXCLUDED and NAMED rather
      than silently added or silently dropped.
  - id: AC2
    text: >
      A PARTIAL SUM IS NEVER PRESENTED AS A PLAN'S RANGE, AND AN EMPTY ONE IS NOT A ZERO. A
      plan's coverage is counted, `complete` is a field, the unestimated items are named, and a
      plan with no estimates at all gets NO range: None, never 0, with a reason that names the
      confident zero it is refusing. A partial roll-up says PARTIAL and says which DIRECTION it
      is wrong in, because a partial sum read as a plan's range is not merely incomplete, it is
      biased low. Calibration travels with the sum and the weakest link governs it: a total is
      `calibrated` only when every contributing estimate is. The program roll-up is the same rule
      over plan ranges, propagates partiality upward, and refuses to blend money across two
      different rates. MEASURED over this repository: PLAN-0014 declares 10 work items and
      `.veldo/estimates/` does not exist, so the roll-up over real bytes reads 0 of 10 with no
      range; a selftest asserts that against the item count read from the plan itself, so a parse
      that found nothing reds instead of passing over an empty set.
  - id: AC3
    text: >
      THE DOLLAR RANGE NEEDS A DECLARED RATE WHOSE PROVENANCE IS RECORDED, AND AN UNPRICED RANGE
      READS UNPRICED. `veldo.toe_token_price/v1` carries an INTEGER micro-USD rate per 1000
      tokens plus a REQUIRED model, source and observed_at; each missing field, a non-integer
      rate, a rate of zero, an unknown key and a wrong schema are refused by name, and the
      command-line path is exactly as strict as the committed one, so money cannot be obtained
      without saying where the rate came from. With no rate the money block reads `priced: false`
      with every figure None and the word unpriced where a number would go, never a zero; a
      malformed rate record present on disk is refused by name and does NOT fall back to a
      default. The conversion and the display both round DIRECTIONALLY (floor the low, ceil the
      high), so the money interval contains the exact one and a non-zero amount under a cent
      renders `<0.01` rather than `0.00`. A selftest drives each refusal with its positive
      control, drives containment on a deliberately inexact rate, and requires the money caveat
      to name both the rate's model and the range's calibration.
  - id: AC4
    text: >
      PACING READS RECORDED SPEND THROUGH ITS OWNER AND STANDS DOWN ON AN EMPTY LEDGER, AND THE
      GOVERNOR CONSUMES THE NUMBER UNCHANGED. The spend total comes from `budget.plan_spend`
      (which reads metrics.compute, the one spend aggregation, and owns which correlations belong
      to a plan) and the recorded FLAG from `toe_corpus.spend_for`; nothing is recomputed here and
      a selftest asserts the two agree on one seeded event set. With nothing recorded the position
      is None with a reason, because "0 percent consumed" would read as a measurement of being on
      track: MEASURED, this repository's stream carries over a thousand events and not one token,
      so the standdown is driven on real data. The declared cap is read through
      `budget.parse_budgets`, never parsed a second way, and a malformed block is reported with
      that module's own refusal. The pacing seam emits PLAIN DICTS carrying the HIGH bound only,
      emits NOTHING when there is no range or the roll-up is partial, and this module never
      imports or calls the governor; a selftest builds the real `governor.Window` from what it
      emits, drives the real `desired_workers` both under and over the window, asserts the loader
      cache contains no governor, and asserts the four pacing boundaries exactly.
  - id: AC5
    text: >
      ADVISORY BY DESIGN, PROVEN AS A MEASUREMENT, AND ADOPTION SAFE - the AC that matters most,
      because it is PLAN-0014's NG1 and D4. The real `frontier.claimable` is driven over a
      hermetic repository root three times - with no estimates, with estimates whose roll-up is
      hundreds of times the plan's declared cap, and with a malformed price record present - and
      must return the IDENTICAL claimable set, with the negative control that the same frontier
      over the same root DOES shrink when a spec declares an unshipped prerequisite; the real
      `validate.check_spec` returns the identical zero across the same three states, with its own
      negative control on a genuinely broken spec. The report CLI, driven as a real process over a
      plan hundreds of times over its cap, exits 0 and prints ADVISORY, paired with the control
      that the pre-existing `budget.check` over the same plan front matter with recorded spend
      past the same cap DOES return a violation. Nothing in scripts/verify.sh names this module.
      Every shape the module produces carries the advisory marker as a FIELD. And it is adoption
      safe on both axes: over a root holding only a plan every reader stands down and the tree is
      unchanged afterwards (no directory, no record, no log created), the view is deterministic
      and reads no clock, and the engine twin imports in a tree that ships no `budget.py` and
      STANDS DOWN BY NAME there rather than recomputing a plan's spend attribution under a second
      rule of its own.
required_evidence: [unit]
rollback: >
  Delete the module, its engine copy, the example rate record and the suite fragment, and remove
  the suite from the manifest (regenerating scripts/suites/requires.json and specs/index.md).
  Nothing reads it, no gate stage runs it, and it writes no file at all; a repository that
  committed no estimates and no rate is unaffected either way.
---

## Outcome

W2 built the record that says what one change is expected to cost. This is the item that makes
those records add up: a plan's Tokens of Effort range is the sum of its items' ranges, a program's
is the sum of its plans', the total converts to a dollar range at a declared rate, and the whole
thing is held against what has actually been spent so far.

It is the first estimate-to-dollars line in this method that is derived rather than guessed, and
it is the last place PLAN-0014 could have accidentally built an enforcement mechanism, so both
halves get equal weight here.

## What already existed, and the division of labour

`.veldo/budget.py` has held a plan's HAND-DECLARED cap against RECORDED SPEND since PLAN-0004, and
it ENFORCES: over the cap it exits non-zero naming the overage. That question is not re-asked here
and its machinery is untouched (NG4).

This item asks the other question - what does the plan's own committed estimate say it will cost,
and where is it against that - and it ADVISES. So that the two can never disagree about their
shared inputs, this module does not recompute them. It reads `budget.parse_budgets` for what cap a
plan declares, `budget.plan_work_specs` for which specs are its work items, and
`budget.plan_spend` for what it has spent. The recorded-versus-zero distinction, which the enforcer
has no reason to make because a zero and an absence enforce identically, comes from
`toe_corpus.spend_for`, the module that owns it. The suite asserts the two readers agree on the
total, so a divergence reds a test rather than quietly producing two numbers for one plan.

## Summing ranges is not summing points

The arithmetic is interval addition and the module says so, in a declared table the reader
recomputes through:

    total low  = sum of the item lows
    total high = sum of the item highs

What is deliberately NOT offered matters more than what is. `mean`, `midpoint` and `pert` collapse
a range to a point, and `veldo.estimate/v1` has no field for a point. `root_sum_square` is the
tempting one: quadrature is the standard way to add uncertainties and it would produce a visibly
tighter total. It is refused because it assumes the item errors are INDEPENDENT, and every range
in this repository comes out of one estimator under one declared prior, so their errors are
correlated by construction. Narrowing a total on an independence nobody has measured is
manufacturing confidence, and the refusal says that rather than only saying no.

THE PROPERTY THAT ANSWERS "does a wide range and a narrow one average into false confidence".
Define spread as high over low. Under sum_bounds the total's spread is `sum(high)/sum(low)`, a
weighted mediant of the item spreads, so

    min(item spreads) <= total spread <= max(item spreads)

The total can never be tighter than the tightest item inside it, and adding a wide item to narrow
ones moves the total TOWARD the wide one. Both sides of that sandwich are asserted over a
625-percent range summed with a 110-percent one, with the exact bound sums asserted separately so
the sandwich cannot be satisfied by fudging the bounds. The measured red that shaped those two
assertions is recorded in the suite fragment: with `sum` mutated to `min` on the lows, the SPREAD
assertion alone would not have caught it (a min-low widens the ratio), and the money-containment
assertion stayed green because it converts the same mutated number it compares against. Only the
assertion that recomputes the sum from the items catches that class.

## The rate, and why an unpriced unit reads unpriced

A token count times a price is the easiest number in this plan to get wrong quietly, in two ways.

The first is a missing rate treated as zero. `.veldo/substrate_cost.py` already refuses that for
infrastructure kinds ("an unpriced resource kind is NOT free"), and this module holds the same
posture: no rate means `priced: false`, every money field None, and the word unpriced where a
figure would go. A malformed rate record is refused by name and does NOT fall back to a default,
because substituting a guess for the number a human wrote down turns a typo into a silently
different bill.

The second is a rate with no provenance. A rate is the only number in this whole chain that comes
from outside the repository entirely, so `model`, `source` and `observed_at` are required, and the
command-line path is exactly as strict as the committed one. You cannot get money out of this
without saying where the rate came from.

Money is INTEGER micro-USD per 1000 tokens rather than a float, for two mechanical reasons: the
front-matter subset has no float, so a fractional rate written into a record comes back as a
string and gets coerced by whoever reads it next; and a dollar figure derived from an uncalibrated
token range has no business carrying binary rounding on top of the uncertainty it already has.
Rounding is directional in the conversion and again in the display, floor on the low and ceil on
the high, so the printed interval contains the exact one; a rounding that narrowed a money range
would be the same false precision the token schema already refuses.

## The one place a number could have stopped work

`.veldo/governor.py` paces workers against rolling `Window(name, seconds, tokens)` budgets and
returns ZERO WORKERS when a window's budget is spent. Handing it a number derived from estimates is
therefore the one place in this item where an advisory figure could throttle real work, and three
rules close it:

- the seam emits the HIGH bound and never the low, because a range's low bound is its optimistic
  end and not a limit;
- with no range, or a PARTIAL one, it emits nothing at all with the reason named. This is the
  dangerous shape rather than the safe one: `governor.Window` refuses a non-positive budget, so an
  empty estimate ledger would either crash a pacer or stall every worker in it;
- it emits DATA and never a `Window`. This module does not import the governor and nothing in this
  repository wires the two together, so whoever hands an advisory number to an enforcing consumer
  does it in the open. That is D4.

Measured on this repository: PLAN-0014 carries no estimates, so `pacing_windows` over it returns
nothing, and today's data cannot reach a pacer even by accident.

## The advisory proof, driven rather than argued

RJ4 asks for a conformance test that no code path in this plan refuses, blocks or delays work on
estimate or budget grounds. A grep for the absence of a call cannot show that, so two REAL
surfaces are driven over a hermetic repository root in three states (no estimates; estimates whose
roll-up is hundreds of times the plan's declared cap; a malformed price record present):

- `frontier.claimable`, which is the surface that decides what work may be pulled, returns the
  identical claimable set in all three, with the negative control that the same frontier over the
  same root DOES shrink when a spec declares an unshipped prerequisite;
- `validate.check_spec` returns the identical zero in all three, with the negative control that it
  DOES refuse a genuinely broken spec under the same root.

Then the exit code, which is where an advisory tool usually turns into a gate by accident: the CLI
over a plan hundreds of times past its declared cap exits 0 and prints ADVISORY, paired with the
control that the pre-existing enforcer over the same plan front matter with recorded spend past
the same cap DOES return a violation. Same overage, two modules, one enforcing and one advising,
measured side by side.

## The measured findings of this item

**This repository can produce no range and no dollar figure today, and says so.** PLAN-0014
declares 10 work items and `.veldo/estimates/` does not exist; `.veldo/toe_token_price.yaml` does
not exist either. So the roll-up reads 0 of 10 estimated with NO range and UNPRICED money. That is
the honest output of a working module over an empty input, and the selftest asserts it against the
item count read from the plan itself so an empty result cannot come from a failed parse.

**Exactly one plan in this repository declares a budget at all.** PLAN-0004, at 20,000,000 tokens
and 400.0 USD. It is read here through `budget.py` from real bytes, and the roll-up still reports
no range against it, because none of its work items carries an estimate either. A cap that is read
and a range that is absent is the state this repository is actually in, and the report prints both
rather than filling the gap.

**The engine canon ships no `budget.py`.** Measured 2026-08-10: `engine/.veldo` carries 83 modules
and that is not one of them, so a hard import would make this module unimportable in the tree
`/veldo:init` lays down. It is therefore an OPTIONAL owner: absent, every reading that needs it
stands down BY NAME rather than being recomputed here under a second attribution rule. The suite
drives that over a copy of the engine tree with the file deliberately removed, so the assertion
keeps its teeth whatever the engine ships later. The line for the release item is in this item's
delivery notes.

## Out of scope

- Any enforcement. Nothing here gates, blocks, deprioritizes or delays work on a roll-up, a dollar
  figure or a cap (NG1, D4). No gate stage is added and verify.sh is untouched.
- Re-implementing budget governance or the pacing governor. Both are read and reused exactly as
  they ship (NG4); `budget.py` keeps its enforcing posture and its exit codes, and `governor.py` is
  not imported here at all.
- Committing an estimate for any spec of this plan, including this one. An estimate is a commitment
  made BEFORE the work, and writing one now would be a fabricated commitment; the roll-up ships
  reporting the honest zero-coverage state instead, and the record shapes ship as a validated
  example.
- Declaring a token price in this repository. The rate is per model and comes from outside the
  repository, so choosing one is a founder act, not a build act; the shape ships as a validated
  example and every dollar figure reads unpriced until somebody declares one.
- The normalized display point (W6), the judgment-load pair (W7), reconciliation and the
  estimator's own accuracy (W5), and the per-area cost map (W9). This item sums the committed
  token ranges and converts them; it adds no second axis and no display unit of its own.
- The capability manifest entry. `.veldo/capabilities.yaml` is integrated separately; the exact
  line to add is recorded with this item's delivery notes.
