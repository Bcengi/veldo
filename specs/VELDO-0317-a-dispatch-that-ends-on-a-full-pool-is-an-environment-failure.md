---
schema: veldo.spec/v1
id: VELDO-0317
title: "A dispatch that ends on a full pool is an environment failure"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0334]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_launch.py"
  - ".veldo/control_launch.py"
  - "engine/.veldo/control_space_admission.py"
  - ".veldo/control_space_admission.py"
  - "scripts/suites/*_veldo_0317_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0317-a-dispatch-that-ends-on-a-full-pool-is-an-environment-failure.md"
  - "specs/index.md"
  - "proof/VELDO-0317/**"
behavior_bearing: true
observability:
  logs: >
    The end records the classification, the pool, and its free space and floor at that moment.
  error_taxonomy: >
    environment_failure:no_space, in the unavailable_service class, when the error is there and free space
    is under the floor. unknown_outcome:no_space_unconfirmed when the error is there and free space is
    above the floor; that end is repeated once.
acceptance_criteria:
  - id: AC1
    text: >
      An unsuccessful end with the no-space error in its output and free space under the floor is
      environment_failure:no_space: no failed attempt charged, the unit back behind admission
    falsified_by: >
      Charge the attempt; the row finds the unit's attempt count raised and fails
  - id: AC2
    text: >
      The error with free space above the floor is unknown_outcome:no_space_unconfirmed and is repeated
      once; a test that prints the error text and then fails for its own reason ends red on the repeat
    falsified_by: >
      Treat the text alone as an environment failure; the row's failing test never records its red and
      fails
  - id: AC3
    text: >
      The worktree of a run that ended this way is kept with its uncommitted changes, and the next brief
      for the ticket says so
    falsified_by: >
      Remove the worktree at run finished; the row finds the edit lost and fails
  - id: AC4
    text: >
      Two environment failures in a row for one unit raise an andon and stop the repeats
    falsified_by: >
      Repeat without a bound; the row counts a third attempt and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. A run that ends on a full pool is charged as a failed attempt again.
---

## Intent

A run that dies because the disk filled says nothing about the change it was building. When an
unsuccessful end has the no-space error in its output and the pool is under its floor, the end is an
environment failure: no failed attempt is charged and the unit goes back behind admission. The worktree is
kept with its uncommitted changes. Two such failures in a row raise an andon.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 8.9 (a run that hits a full pool)
and 6.7 (admission). Section 12 of the design holds the ticket itself; its acceptance criteria and
falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Receiver, Admission. The gate's half is VELDO-0309 AC2.

Build order. It is in the closing sequence 0315, 0316, 0334, 0317, 0327, 0318, 0343, 0340, 0342, 0319,
0320, 0332, 0325, 0339, 0321, 0322. The design states no dependency for this ticket, so depends_on holds
the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
