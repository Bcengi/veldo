---
schema: veldo.spec/v1
id: WARP-1401
title: The Tokens of Effort ground-truth corpus - and the measured finding that its spend inputs do not
  exist, because nothing in the loop emits a token count and nothing inside a repository can
status: shipped
risk: standard - a new derivation module that reads specs, git and the event log and writes nothing.
  No behaviour changes, no gate stage is added, nothing is enforced. It is not low because the number
  it produces is what every later TOE layer would estimate against, and a corpus that quietly reports
  zeros as data would teach an estimator from nothing while looking like it worked.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0014
work: W1
depends_on: []
placement: [metrics]
footprint:
  - ".veldo/toe_corpus.py"
  - "engine/.veldo/toe_corpus.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-1401-toe-ground-truth-corpus.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      ONE PER-SPEC ACTUALS RECORD, DERIVED AND NEVER TYPED. For every shipped spec the corpus carries
      its mechanical features (acceptance-criteria count, risk tier, plan, lane, human_approval,
      declared footprint size, dependency count, spec size), whether its footprint touches a protected
      path, its gate and review CYCLES from the lifecycle events, whatever spend the log holds, and the
      commits and files git says the change actually touched. Every field is read off a spec, off git
      or off the event log; none is judged, because a feature a human has to assess is an estimate
      wearing a feature's clothes. A selftest builds the corpus over seeded specs and events and
      checks each group.
  - id: AC2
    text: >
      DETERMINISTIC AND IDEMPOTENT. Same inputs, same records, every run. The module mints no id, reads
      no clock and appends to nothing; the caller owns reading the event log and passes it in, so the
      corpus can be driven from seeded events and cannot reach for the real log behind a test's back.
      A selftest builds twice over identical inputs and requires byte-identical output.
  - id: AC3
    text: >
      GATE FAILURES ARE COUNTED SEPARATELY FROM PASSES, because they are the rework signal. A change
      that went red three times before green cost three gate runs, and an estimator that cannot see
      that cannot ever learn it. A selftest seeds a spec with two failures and one pass and requires
      both counts distinctly.
  - id: AC4
    text: >
      THE SPEND GAP IS REPORTED AS A NUMBER, NOT HIDDEN BEHIND A ZERO, and this is the AC that matters
      most. `spend_recorded` distinguishes "summed to zero because nothing was spent" from "summed to
      zero because nothing was ever emitted", and `coverage()` reports `spend_known`, `spend_coverage`
      and a blunt `usable_as_ground_truth` boolean. **Measured over this repository: 174 shipped
      specs, 81.03% cycle coverage (141 of 174), 0% spend coverage, usable_as_ground_truth False.
      These figures MOVE as the repository grows, and the first version of this criterion pinned
      148 and 95.3% into print where they went 14 points stale and overstated the corpus in the
      direction a reader would quote. The suite asserts the SHAPE and the honesty of the report,
      never these numbers; they are dated evidence, not a contract.** A selftest
      requires that a corpus built from events carrying no spend reports exactly that rather than a
      confident zero.
  - id: AC5
    text: >
      ONE FOOTPRINT READER. `spec_features` counts the declared footprint and `build` tests it against
      the protected set, and both go through `footprint_of`. The first draft of this module spelled the
      same regex out in both places, which is this repository's named second-spelling defect, and the
      selftest asserts the single reader handles a spec with no footprint block by returning an empty
      list rather than raising - which is exactly how the duplicated version failed.
required_evidence: [unit]
rollback: >
  Delete the module and its capability entry. Nothing reads it yet, nothing depends on it, no gate
  stage runs it and it writes no state.
---

## Outcome

PLAN-0014 estimates effort in the machine's own unit. Everything in it - the structural proxy, the
sizing pass, historical analogy, reconciliation, normalization - estimates against a ground-truth
corpus of what changes actually cost. This is that corpus.

## The finding, which is the real output of this item

**PLAN-0014 W1 says "every input is already recorded today". For spend, that is false.**

Measured over this repository's own event log: **904 events - 658 `gate.passed`, 171
`verdict.recorded`, 75 `gate.failed` - and not one carries `tokens`, `cost_usd` or `human_minutes`.**

The capability has been there the whole time and is not the problem. The envelope has always allowed
those fields. `events.py` accepts `--tokens` and `--cost-usd`. Three separate readers aggregate them:
`metrics.py`, `entropy.py`, `metrics_support_report.py`. **Nothing anywhere emits them.**

**And the reason is architectural rather than an oversight.** A token count is not knowable from
inside a repository. The gate script cannot see how many tokens an agent spent; that number lives in
the agent's harness, outside anything this codebase can reach. The missing emitter is not a forgotten
line, it is an integration nobody has decided on.

## What that means for the rest of PLAN-0014

The corpus is real and useful today for features and cycles: 174 shipped specs at 81.03% cycle
coverage. **What it cannot do is be ground truth for cost, because 0% of it has any.**

So the later layers divide cleanly:

- **W2 (structural proxy)** estimates from features alone and does not need spend. Buildable.
- **W3 (sizing pass)**, **W4 (historical analogy)**, **W5 (reconciliation and estimator accuracy)**,
  **W6 (normalization to a reference change)**, **W8 (budgets in dollars)** all require actuals.
  Building them now would produce machinery that learns from nothing while looking like it works,
  which is the exact failure this repository's owner named: paper rather than output.

**The decision this surfaces, and it is his:** either wire an emitter so agents record their own
spend at ship time, or accept that TOE estimates from structure and cycles only and drop the layers
that need cost. Both are defensible. Guessing which one and building six specs on the guess is not.

## Out of scope

- The emitter itself. It is an integration decision, not a refactor, and it is not in PLAN-0014's
  work list at all - the plan assumed the data existed.
- Any estimator layer. This item is the dataset and its honest coverage report, nothing more.
