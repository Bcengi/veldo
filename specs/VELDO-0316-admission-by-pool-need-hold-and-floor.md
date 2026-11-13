---
schema: veldo.spec/v1
id: VELDO-0316
title: "Admission by pool, need, hold and floor"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0315]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space_admission.py"
  - ".veldo/control_space_admission.py"
  - "engine/.veldo/control_launch.py"
  - ".veldo/control_launch.py"
  - "engine/.veldo/control_dispatch.py"
  - ".veldo/control_dispatch.py"
  - "scripts/suites/*_veldo_0316_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0316-admission-by-pool-need-hold-and-floor.md"
  - "specs/index.md"
  - "proof/VELDO-0316/**"
behavior_bearing: true
observability:
  logs: >
    Each hold records its needs and their source per pool, and for a waiting or advised hold the numbers:
    pool, need, free, held by others and floor.
  metrics: >
    Per pool: free, floor and held. Holds admitted, waiting and advised.
  error_taxonomy: >
    space_wait:<pool> when prepare must wait in act mode; the factory loop lists the unit under waiting
    and not under refused. In report mode nothing is refused.
acceptance_criteria:
  - id: AC1
    text: >
      A run is admitted only when free space minus what others hold is at least its need plus the floor;
      the rows are the boundary values on both sides
    falsified_by: >
      Ignore the floor; the row between need and need plus floor is admitted and fails
  - id: AC2
    text: >
      In act mode a unit that must wait has no dispatch record, no slot, no reservation and no deadline,
      and the factory loop's pass lists it under waiting with its numbers and not under refused. What
      judges it again is VELDO-0334
    falsified_by: >
      Ask admission at acceptance; the row finds a prepared dispatch holding a slot while it waits and
      fails
  - id: AC3
    text: >
      In report mode the same unit is prepared and started, and its hold is recorded as advised with the
      numbers
    falsified_by: >
      Block in report mode; the row's unit is left waiting and the row fails
  - id: AC4
    text: >
      The need comes from the project's space file, else from the last five finished runs of the project
      and station once there are five, else from the pool default; the contract's space field carries it
      and is covered by the contract digest
    falsified_by: >
      Use measured sizes after one run; the row with a single small run is admitted too early and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. Runs are prepared without a space check. A contract stored with the space field keeps
  the digest it was written with.
---

## Intent

A run states the space it needs per pool and starts only when free space, minus what admitted runs still
hold, covers the need plus the pool's floor. The question is asked in Runner.prepare before anything is
reserved, so a unit that must wait holds no slot and has no deadline. In report mode the run starts and
the hold is recorded as advised.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.7 (admission), 4.2 (pool), 4.3
(hold) and 8.1 (steps 1 and 2). Section 12 of the design holds the ticket itself; its acceptance criteria
and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Admission, Runner, Dispatch contract.

Build order. It is in the closing sequence 0315, 0316, 0334, 0317, 0327, 0318, 0343, 0340, 0342, 0319,
0320, 0332, 0325, 0339, 0321, 0322. The design states no dependency for this ticket, so depends_on holds
the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
