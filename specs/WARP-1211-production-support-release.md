---
schema: veldo.spec/v1
id: WARP-1211
title: PLAN-0012 release - the production support organ is shipped code and honest capability records
  but the two documents a reader learns the method from never mention it, so the docs are made true and
  the plan is released
status: shipped
risk: standard - documentation and a version bump over code that is already shipped, already in the
  canonical engine and already recorded in capabilities. Nothing executable changes. It is not low
  because a method document that describes a capability the implementation lacks, or omits one it has,
  is the failure this item exists to fix, and getting it wrong in the permissive direction means
  publishing a claim the code does not support.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0012
work: W11
depends_on: [WARP-1204, WARP-1207, WARP-1208, WARP-1209, WARP-1210]
acceptance_criteria:
  - id: AC1
    text: >
      THE CANONICAL ENGINE ALREADY CARRIES THE ORGAN, AND THIS AC ASSERTS IT RATHER THAN ASSUMING IT.
      Every module PLAN-0012 built exists at `engine/.veldo/` as well as `.veldo/`:
      `evidence.py`, `incident.py`, `incident_reconcile.py`, `responder.py`, `action.py`,
      `action_executor.py`, `executor.py`, `two_key.py`, `authorization.py`. A selftest enumerates
      that list and requires both homes, so a later engine change cannot quietly drop one from the
      copy `/veldo:init` lays down and the packs assemble from.
  - id: AC2
    text: >
      `docs/method.md` GAINS THE ORGAN AS SHIPPED BEHAVIOUR, FULLY GENERIC. A new numbered section
      describes production support as part of the method: an incident is intent, diagnosis is derived
      from artifacts by a reader that structurally cannot write, remediation is a proposal a human
      authorises, and the action executor is a separate organ behind a whitelist with a two-key rule
      for anything irreversible. Zero company, product, person or path references, per the genericity
      rule the docs sweep already enforces. The later sections are renumbered and the four existing
      internal section references (to 4, 6 and 7) are verified still correct.
  - id: AC3
    text: >
      `docs/setup.md` GAINS THE OPERATOR SIDE, AND LIVE ENABLEMENT IS DOCUMENTED AS A SEPARATE HUMAN
      ACT. Wiring a real evidence plane, a real action whitelist and real credentials is NOT something
      adopting the method turns on: the shipped default is offline and inert, and going live is a
      deliberate, human-performed configuration step with its own risk. Saying this is the point of the
      AC. A setup document that reads as though the organ is live on install would be worse than no
      documentation at all.
  - id: AC4
    text: >
      THE CAPABILITY RECORDS STAY HONEST AND ARE NOT INFLATED BY THIS ITEM. The ten PLAN-0012 entries
      in `.veldo/capabilities.yaml` already carry `status: mechanical` with their real homes. This item
      adds no entry and upgrades no status; documentation is not a capability. A selftest asserts the
      entries still name modules that exist.
  - id: AC5
    text: >
      THE PLUGIN VERSION IS BUMPED AND THE PLAN IS MARKED RELEASED, in that order and only after the
      gate is green. The plan's status moves `ready` to `released`, which is what makes the plan list
      stop reporting finished work as outstanding - the specific confusion that caused this item to be
      found in the first place.
required_evidence: [unit]
rollback: >
  Revert the commit. Nothing executable changes: the diff is two documents, a version string and a plan
  status field. No migration, no persisted state, no behaviour.
---

## Outcome

PLAN-0012 built a production support organ and shipped ten of its eleven work items. The code is in
the canonical engine, the capability records are honest, and the regression journeys pass. What never
happened is the last item: the two documents a reader learns the method from do not mention any of it.
`docs/method.md` names "incident response" exactly once, in a list of things the method does NOT
eliminate, and `docs/setup.md` does not mention it at all.

So the method as documented is a method without production support, while the method as implemented has
one. That gap is the whole of this item.

## Why this was found late, which is worth recording

The plan list reported PLAN-0012 as `ready`. Asked what work remained, the first count was taken by
grepping which specs MENTION a plan id rather than reading the plan's own declared work list. Those are
different sets. The wrong one reported this plan as finished and reported PLAN-0013, which has zero of
eleven specs written, as finished too.

**A plan's completion is defined by its work list and nothing else.** Recorded here because the same
error had already been made once that day against `specs/index.md` and was not generalised.

## Why this spec declares no footprint, which is deliberate

The architecture contract declares nine areas - contracts, engine, enforcement, loop, fleet,
metrics, tracker, distribution, runners - and **none of them is documentation**. The contract also
refuses a footprint without a placement, on the sound principle that a footprint with no area is
placeless. This change is two documents, a version string, a suite file and a plan status, and it
lands in no area the contract models.

The options were to invent a placement or to declare neither, and **a false placement is worse than
an absent footprint**: `distribution` would have been the closest and it is simply not true, since
this item touches neither the pack assembler nor its conformance check. So this follows the
precedent already set by `WARP-0111-planning-layer-docs`, which declares neither.

**The cost is real and is stated rather than hidden:** the footprint-versus-diff dogfood does not
cover this change, and that check caught two genuine mistakes in this very item before the footprint
was removed. A documentation area in the architecture contract would fix the general case and is not
in scope here.

## Out of scope

- Any behaviour change. The organ ships exactly as it is.
- Live enablement. AC3 documents it as a separate human act precisely so that it stays out of scope.
- The other five `ready` plans. PLAN-0013, 0014, 0015 and 0017 have no specs written at all, and
  PLAN-0016 has three outstanding; each is its own work.
