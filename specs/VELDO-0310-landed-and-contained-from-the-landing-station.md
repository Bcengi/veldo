---
schema: veldo.spec/v1
id: VELDO-0310
title: "Landed and contained, from the landing station"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0301]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_landing.py"
  - ".veldo/control_landing.py"
  - "engine/.veldo/control_landing_station.py"
  - ".veldo/control_landing_station.py"
  - "scripts/suites/*_veldo_0310_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0310-landed-and-contained-from-the-landing-station.md"
  - "specs/index.md"
  - "proof/VELDO-0310/**"
behavior_bearing: true
observability:
  logs: >
    Each landing records the items it removed and each branch it marked contained, joined to the unit's
    completion receipt.
  error_taxonomy: >
    A worktree git refuses to remove is deferred as space_deferred:remove_refused, and one with unique
    work as space_deferred:unique_work. A branch is never deleted.
acceptance_criteria:
  - id: AC1
    text: >
      Landed is sent after the completion receipt is recorded and never before
    falsified_by: >
      Send it when the landing starts; the row that fails the landing after that finds the worktree gone
      and fails
  - id: AC2
    text: >
      At landed the unit's worktree is removed after its build output, its branch is kept and marked
      contained, and its image tags go
    falsified_by: >
      Remove the branch with the worktree; the row finds no branch and fails
  - id: AC3
    text: >
      Every other recorded branch of the project that has moved past its start commit and that the new
      trunk tip contains is marked contained and its worktree removed; a branch still at its start commit
      is left
    falsified_by: >
      Drop the start commit test; the row's fresh worktree on a new branch is removed and the row fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. A landing removes nothing, and the worktrees of landed branches stay until another
  event ends them.
---

## Intent

When a unit lands, its worktree has done its work. After the completion receipt is recorded the landing
station sends landed: the unit's build output goes, then its worktree, its image tags go, and its branch
is kept and marked contained. Every other recorded branch the new trunk tip contains is treated the same,
unless it has not moved past its start commit.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 5 (landed and contained, and the
start commit rule) and 8.3 (a landing by the landing station). Section 12 of the design holds the ticket
itself; its acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Landing.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
