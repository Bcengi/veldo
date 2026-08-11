---
schema: veldo.spec/v1
id: WARP-1506
title: Drift tripwires - declared versus running, in three directions, and the destructive one is the
  only direction a human has to choose
status: shipped
risk: standard - a pure comparison that acquires nothing and changes nothing. It is not low because a
  drift tool that drafts a deletion is a drift tool that removes the undeclared resource keeping
  production alive, and avoiding that is the whole safety content here.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0015
work: W6
depends_on: [WARP-1501]
placement: [metrics]
footprint:
  - ".veldo/substrate_drift.py"
  - "engine/.veldo/substrate_drift.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-1506-drift-tripwires.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      THREE NAMED DIRECTIONS, NOT ONE COUNT. `missing` (declared, not running), `unmanaged` (running,
      not declared) and `modified` (both, not matching) are distinct findings. A modification names
      the FIELDS that differ with declared and running values, because "drifted" sends somebody
      diffing by hand and "version declared 15.4, running 14.2" does not.
  - id: AC2
    text: >
      NO DIRECTION EVER DRAFTS A DELETION, and this is the AC that matters. An unmanaged resource
      drafts `adopt_or_decide` and is flagged for a human; it is never drafted for removal. Deleting
      a resource nobody declared is exactly how a drift tool destroys the thing keeping production
      alive. `drafts_no_deletion` exposes the property so a selftest asserts it over generated drift
      rather than reading the table by eye.
  - id: AC3
    text: >
      RECONCILIATION UNITS ARE IDEMPOTENT. The unit id derives from environment, direction and
      resource, so running the comparison twice over unchanged drift yields the same units rather
      than a growing pile. A tripwire that manufactures new work on every pass trains everybody to
      ignore it, which is how drift detection becomes worthless in practice.
  - id: AC4
    text: >
      IN-SESSION ONLY, NEVER A DAEMON (D4). No process, no socket, no timer. It runs when the gate
      runs, when status is asked, and in the weekly pass. Noticing drift three hours sooner is not
      worth an always-on component with its own credentials. A selftest asserts the module starts
      nothing.
  - id: AC5
    text: >
      THE SNAPSHOT IS AN ARGUMENT, NOT AN ACQUISITION. How real state is read is per-system wiring
      the plan places outside itself, and taking it as data is exactly what lets every rule here be
      proven offline against fake snapshots.
required_evidence: [unit]
rollback: >
  Delete the module and its capability entry. Pure comparison, no state, no gate stage yet.
---

## Outcome

Declaring infrastructure in the repository only helps if somebody notices when reality stops
matching it. This compares the two and reports named findings, each drafting one reconciliation unit
a human can promote.

## The direction rule, which is the part most easily got wrong

Drift is not symmetrical.

**Missing** - declared but not running. The declaration is the intent, so the fix is to create it.

**Unmanaged** - running but not declared. The fix is emphatically NOT to delete it. Somebody made
it by hand for a reason, or the declaration lost it, and either way the resource may be load
bearing. It drafts `adopt_or_decide` and is flagged for a person.

**Modified** - both exist and disagree. Bring the running one back to the declaration, with the
differing fields named.

**No direction drafts a deletion.** The one destructive move is the one a human has to choose. A
drift tool that tidies away undeclared resources is a drift tool that eventually removes the thing
production depended on, and the incident report reads "the automation cleaned it up".

## Why it is not a daemon

The tripwire pattern, per D4: it runs inside sessions that were happening anyway. A continuous
detector is a service with credentials, uptime and an on-call story, bought to learn about drift
three hours earlier. That trade is not worth making.
