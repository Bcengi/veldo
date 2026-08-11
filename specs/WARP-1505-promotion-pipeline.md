---
schema: veldo.spec/v1
id: WARP-1505
title: Promotion is a proven change moving one step through declared environments, and no rollback plan
  means no promotion
status: shipped
risk: standard - a pure decision function that promotes nothing and reaches no environment. It is not
  low because a rule wrong in the permissive direction lets an unproven or un-undoable change into
  production, and the whole point of the pipeline is that this is the one place that cannot happen.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0015
work: W5
depends_on: [WARP-1502]
placement: [enforcement]
footprint:
  - ".veldo/substrate_promote.py"
  - "engine/.veldo/substrate_promote.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-1505-promotion-pipeline.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      ONE STEP AT A TIME, ALONG THE DECLARED ORDER. Environments come from
      `substrate.ENVIRONMENT_ORDER`, the same list the declaration validator uses, so the pipeline
      and the validator cannot disagree about which way is forward. Skipping refuses `not_adjacent`
      and names what was skipped; going backwards refuses `backwards`, because that is a rollback and
      a different act with a different plan. An undeclared environment refuses.
  - id: AC2
    text: >
      NO ROLLBACK PLAN, NO PROMOTION - a refusal, not a warning. The plan must name a recognised
      METHOD and describe something specific, so the string "rollback" does not pass. It is checked
      BEFORE any other ceremony, because a change nobody can undo should be refused whether or not it
      would otherwise have qualified. A selftest drives absent, malformed and too-thin separately.
  - id: AC3
    text: >
      THE RISK CLASS DECIDES THE CEREMONY, NOT THE DESTINATION, and the table is DATA. Keying on the
      destination would make every typo into production critical and every database drop into staging
      trivial. `GATING` is a readable table rather than a chain of conditionals, and AN UNKNOWN RISK
      CLASS GETS THE STRICTEST ROW rather than the loosest - a class nobody has defined must not be
      the cheapest way to promote.
  - id: AC4
    text: >
      A FAILED CANARY HALTS, AND HALTED IS NAMED DIFFERENTLY FROM FAILED. `canary_unhealthy` stops the
      promotion where it is; the distinction is operational, because a halted promotion has a known
      position to roll back from while one reported as merely failed leaves somebody guessing how far
      it got. `canary_required` (none run) is a separate refusal from `canary_unhealthy` (ran, sick).
  - id: AC5
    text: >
      IT DECIDES AND DOES NOT ACT. No environment is reached, nothing is promoted, no adapter is
      called - the caller acts through the W2 seam. That separation is what lets every rule here be
      proven offline against fake environments, which is this item's entire evidence, and a decision
      function that could also act is one nobody can safely test.
required_evidence: [unit]
rollback: >
  Delete the module and its capability entry. It is pure, reads nothing, writes nothing and runs at
  no gate stage.
---

## Outcome

A release is not an event. It is a proven change moving through declared environments in order,
carrying whatever its risk class demands, with a way back written down before it starts.

## The four rules, and why each is where it is

**Order is the declared order and you may not skip.** Straight to production is the move everyone
regrets, and "we tested it in dev" is what gets said afterwards.

**No rollback plan, no promotion.** A rollback plan written after something breaks is written by
someone panicking. A promotion whose author could not say how to undo it has not finished being
designed. It is checked first, before any other requirement, because that refusal should not depend
on whether the change would otherwise have qualified.

**The risk class decides the ceremony, not the destination.** Otherwise every typo into production
is a critical event and every database drop into staging is trivial. And an unknown class takes the
strictest row: a class nobody has defined must never be the cheap way through.

**A failed canary halts.** Halted and failed are different words on purpose. Halted has a known
position to roll back from.

## What it is not

It promotes nothing. It decides, and the caller acts through the adapter seam from W2. Keeping the
decision away from the act is exactly what makes every rule above provable offline.
