---
schema: veldo.spec/v1
id: WARP-1508
title: PLAN-0015 release - seven substrate modules are shipped code in the canonical engine and the two
  documents a reader learns the method from never mentioned any of it
status: shipped
risk: standard - documentation, a version bump and a plan status over code already shipped, engine-
  synced and recorded in capabilities. Nothing executable changes. It is not low because a method
  document that omits a capability the implementation has is the failure this item exists to fix, and
  the permissive error is publishing a claim the code does not support.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0015
work: W8
depends_on: [WARP-1503, WARP-1504, WARP-1505, WARP-1506, WARP-1507]
placement: [docs]
footprint:
  - "docs/method.md"
  - "docs/setup.md"
  - "packs/claude/.claude-plugin/plugin.json"
  - ".claude-plugin/marketplace.json"
  - "plans/PLAN-0015-substrate-and-release.md"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-1508-substrate-release.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      ALL SEVEN SUBSTRATE MODULES EXIST IN BOTH ENGINE HOMES AND ARE BYTE-IDENTICAL, asserted rather
      than assumed: `substrate`, `substrate_change`, `substrate_cost`, `substrate_floor`,
      `substrate_promote`, `substrate_drift`, `substrate_ephemeral`. A later engine change cannot
      silently drop one from the copy `/veldo:init` lays down and the packs assemble from.
  - id: AC2
    text: >
      `docs/method.md` GAINS INFRASTRUCTURE AND RELEASE AS SHIPPED BEHAVIOUR, FULLY GENERIC. The
      section states each load-bearing rule with its reason: the plan binds to what it was computed
      from, cost is a proof element and an unpriced resource is refused rather than counted free,
      destruction is classified with the strict direction as the default, promotion is one step with a
      rollback plan, drift is reported both ways but only one direction is safe to automate, and
      teardown is verified against the provider rather than a return code. Sections renumbered.
  - id: AC3
    text: >
      `docs/setup.md` GAINS THE OPERATOR SIDE, AND GOING LIVE IS FIVE ORDERED HUMAN STEPS. The point
      of the section is that everything ships INERT: every module decides, none acts, the adapters
      are fakes, and a repository declaring no substrate is untouched. The ordering is the content -
      declarations before adapters, the read-only drift comparator before the applier, one
      non-production environment before production - because each step is safe only if the one
      before it is done.
  - id: AC4
    text: >
      THE PLUGIN VERSION IS BUMPED IN BOTH MANIFESTS AND PLAN-0015 IS MARKED RELEASED, only after the
      gate is green. Both manifests, because they drifted apart once already and the marketplace copy
      is the one an adopter actually installs from.
required_evidence: [unit]
rollback: >
  Revert the commit. Two documents, two version strings and a plan status field; nothing executable,
  no migration, no state.
---

## The footprint is back, because the gap it named got fixed

An earlier pass of this item declared no footprint, because the architecture contract had nine
areas, none of them documentation, and it refuses a footprint without a placement. That was the
second release item in one night to pay that cost, and paying it twice is what made it worth
fixing rather than working around.

`WARP-0735` added a `docs` area. This item now declares `placement: [docs]` and its real footprint,
so the footprint-versus-diff dogfood - which caught four genuine mistakes in a single night -
covers it after all.

## Outcome

PLAN-0015 built seven modules that govern what runs the software the same way the method governs the
software. They are shipped code, engine-synced and honestly recorded in capabilities. The two
documents a reader learns the method from did not mention any of it.

That is the same gap WARP-1211 closed for production support, found the same way and fixed the same
way: a method as documented that is smaller than the method as implemented.

## What the setup section is actually for

Not to explain how to use the machinery. To say, clearly enough that nobody misreads it, that
**everything ships inert** - every module decides and none acts, every adapter is a fake, and a
repository that declares no substrate never touches a line of it.

And then to give the five steps for going live IN ORDER, because the order is the content.
Declarations before adapters, so the first real adapter run is against something a human has read.
The read-only drift comparator before the applier, because drift you did not know about is the
normal first result and finding it read-only beats finding it with an apply. One non-production
environment before production. Budgets and prices before the check can protect anything. Production
last, through the pipeline, precisely when it feels slow.
