---
schema: veldo.spec/v1
id: VELDO-0319
title: "The console's Space screen"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0342]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_api.py"
  - ".veldo/control_api.py"
  - "engine/ui/src/api/routes.json"
  - "engine/ui/src/features/space/**"
  - "engine/ui/src/views/SpaceView.vue"
  - "engine/ui/src/app/navigation.ts"
  - "scripts/suites/*_veldo_0319_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0319-the-consoles-space-screen.md"
  - "specs/index.md"
  - "proof/VELDO-0319/**"
behavior_bearing: true
observability:
  logs: >
    Each owner action is a signed command in the journal. Reads write nothing.
  error_taxonomy: >
    An owner action from a session without the owner's passkey is refused.
acceptance_criteria:
  - id: AC1
    text: >
      The usage table's figures per project, ticket and kind equal the sums of the fixture's item records,
      with each plain repository and "No project" as rows of their own
    falsified_by: >
      Sum only present items and leave out deferred ones; the totals row fails
  - id: AC2
    text: >
      Pending removal lists every due and deferred item with its reason in words, its retry event and its
      open decision request; Removed lists every removal with its event, size and free space before and
      after
    falsified_by: >
      Hide deferred items; the row that expects the in-use folder finds nothing and fails
  - id: AC3
    text: >
      Reconcile, Adopt, Abandon, Confirm, Wrong and the mode switch are signed owner commands; a session
      without the owner's passkey is refused each
    falsified_by: >
      Accept Abandon as a plain read route; the unsigned row succeeds and fails
  - id: AC4
    text: >
      A waiting run, and in report mode a run that would have waited, shows need, free, held and floor on
      the runs list and the Pools section, and the screen updates from the record stream without a reload
    falsified_by: >
      Poll on an interval; the row that stops the fixture clock sees no update and fails
required_evidence: [unit, integration, ui_states]
rollback: >
  Revert the change. The console has no Space screen; the ledger and the CLI are unaffected.
---

## Intent

The owner needs to see where the space is and what Veldo is about to do with it. The Space screen shows
usage by project, ticket and kind, what is pending removal and why, what was removed and by which event,
and the pools with the runs waiting on them. Every figure is read from ledger records, and every action is
a signed owner command.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 10 (console) and 6.6 (API and
console actions). Section 12 of the design holds the ticket itself; its acceptance criteria and falsifiers
are copied here word for word.

What section 12 says about this ticket:

> Components: API, Console.

Build order. It is in the closing sequence 0315, 0316, 0334, 0317, 0327, 0318, 0343, 0340, 0342, 0319,
0320, 0332, 0325, 0339, 0321, 0322. The design states no dependency for this ticket, so depends_on holds
the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
