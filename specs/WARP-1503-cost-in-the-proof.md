---
schema: veldo.spec/v1
id: WARP-1503
title: An infrastructure change declares what it will cost, held against the environment's budget, so
  the number is read at review rather than discovered on next month's bill
status: shipped
risk: standard - a pure projection over a plan, with a declared price table and no network. It is not
  low because a cost check that is wrong in the permissive direction certifies a change as affordable,
  which is worse than having no check at all.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0015
work: W3
depends_on: [WARP-1502]
placement: [contracts]
footprint:
  - ".veldo/substrate_cost.py"
  - "engine/.veldo/substrate_cost.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-1503-cost-in-the-proof.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      THE COST DELTA IS PROJECTED FROM THE PLAN, WITH A SIGN CONVENTION THAT IS STATED. A create adds,
      a delete subtracts, a replace is the difference between the two kinds, and an update is zero
      because changing a parameter does not change what the resource IS. Getting this backwards is
      silent, so each case is driven by a selftest rather than assumed.
  - id: AC2
    text: >
      AN UNPRICED KIND IS NOT FREE, and this is the AC that keeps the check honest. A resource kind
      absent from the table yields `unpriced`, and any plan containing one refuses `unpriced_resources`
      rather than producing a total. Costing an unknown at zero is exactly how a budget check waves
      through the change that doubles the bill.
  - id: AC3
    text: >
      OVER BUDGET REFUSES AND NAMES THE NUMBERS. The refusal carries the environment, the projected
      total, the declared budget, the current spend, the delta, and the three resources that drove it,
      so it can be acted on in one read rather than sending somebody to the source.
  - id: AC4
    text: >
      AN ENVIRONMENT WITH NO DECLARED BUDGET IS REPORTED, NOT PASSED. Silence is not permission: with
      no budget there is nothing to hold the change to, and that is a distinct named outcome from
      being within one.
  - id: AC5
    text: >
      DECLARED STATIC ESTIMATES FIRST, PRICING ADAPTERS AS A SLOT (D2), AND THE LIMITS ARE IN THE
      MODULE. `PriceSource` is the seam a live adapter arrives at; the shipped source is a
      repo-committed table so a price change is a diff somebody reads. The module states plainly that
      a static table is an estimate and not a bill, and that a parameter change which resizes a
      machine is invisible to a table that prices KINDS. Overstating this would be worse than the
      estimate being rough.
required_evidence: [unit]
rollback: >
  Delete the module and its capability entry. Nothing reads it yet, no gate stage runs it, it writes
  no state and it changes no behaviour.
---

## Outcome

Infrastructure spend is discovered on a monthly bill, weeks after the change that caused it, by
which time nobody remembers which change it was. Meanwhile that change went through a review where
the one number that mattered was never on the page.

So the cost delta becomes a proof element: computed from the plan, held against a declared budget
for the environment, read by a human before the change lands.

## Why a table and not a pricing API

A live pricing API is a dependency, a credential and a network call inside the gate, and it buys
precision nobody needs at review time. The question being asked is "is this ten dollars or ten
thousand", not "is this $412.60 or $418.90". A repo-committed table makes a price change a diff
somebody reads, which is a property the API would take away. `PriceSource` is where a real adapter
arrives if that trade ever changes.

## The two limits, stated because this module invites over-trust

**A static table is an estimate, not a bill.** It is wrong whenever the table is stale, or a
resource's real cost depends on usage the declaration cannot see: egress, request volume, storage
growth. This is a guard against an obvious mistake, not a forecast.

**An unpriced kind is not free.** The check refuses rather than totalling around it. That single
decision is what stops the whole thing from being decorative.
