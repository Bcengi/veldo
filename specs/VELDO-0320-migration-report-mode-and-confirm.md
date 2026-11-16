---
schema: veldo.spec/v1
id: VELDO-0320
title: "Migration: report mode and Confirm"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0315, VELDO-0319, VELDO-0331]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space_reconcile.py"
  - ".veldo/control_space_reconcile.py"
  - "engine/ui/src/features/space/**"
  - "engine/ui/src/views/SpaceView.vue"
  - "engine/ui/src/app/navigation.ts"
  - "scripts/suites/*_veldo_0320_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0320-migration-report-mode-and-confirm.md"
  - "specs/index.md"
  - "proof/VELDO-0320/**"
behavior_bearing: true
observability:
  logs: >
    Each Confirm writes the owner's command on every item it covered. Each removal that follows is an
    ordinary outcome.
  error_taxonomy: >
    Confirm is refused when it is not signed by the owner, and for a scope in act mode. A confirmed item
    that a rule refuses is deferred with the rule's name, and the rest of the group is removed.
acceptance_criteria:
  - id: AC1
    text: >
      For a project in report mode a reconcile over a fixture with 20 worktrees, their build folders, an
      agent repository and labelled Docker objects adopts them and removes nothing
    falsified_by: >
      Act on due items in report mode; the row finds a folder gone and fails
  - id: AC2
    text: >
      Confirm for one project and kind removes exactly that group's due items, through all seven rules
    falsified_by: >
      Confirm everything pending; the other project's folder is gone and the row fails
  - id: AC3
    text: >
      A confirmed item that a rule refuses stays, deferred with the rule's name, and the rest of the group
      is removed
    falsified_by: >
      Stop the group at the first refusal; the row's second removable folder is still there and the row
      fails
  - id: AC4
    text: >
      The confirmation stands through a deferral: while the project is still in report mode the deferred
      item's next event removes it without a second Confirm, and an unconfirmed item at the same event
      stays
    falsified_by: >
      Drop the confirmation at the deferral; after the holding process exits and the next event runs, the
      row finds the folder present and fails
required_evidence: [unit, integration, ui_states]
rollback: >
  Revert the change. The due items of a project in report mode stay listed and cannot be confirmed, so
  nothing is removed.
---

## Intent

The things that exist today are adopted without removing any of them. For a project in report mode a
reconcile adopts and lists what Veldo would remove; the owner confirms one project and kind at a time, and
only that group is removed, through all seven rules. A confirmation stands through a deferral.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 11 (migration), 6.1 (confirm group)
and 6.6 (space.confirm). Section 12 of the design holds the ticket itself; its acceptance criteria and
falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Reconciler (mode), Console (Confirm). Depends on 0315, 0319 and 0331. The switch to act is
> VELDO-0332.

Build order. It is in the closing sequence 0315, 0316, 0334, 0317, 0327, 0318, 0343, 0340, 0342, 0319,
0320, 0332, 0325, 0339, 0321, 0322. depends_on holds the dependencies the design states for this ticket.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-16: the lead's decision on VELDO-0319 (no dead routes): this ticket now carries the console's
  Confirm button with its command. VELDO-0319 built the Space screen and its Pending removal section
  without it; the route space.confirm, its operation and its place on that screen come with this ticket.
