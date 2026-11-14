---
schema: veldo.spec/v1
id: VELDO-0315
title: "Reconcile at start and on demand"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0304]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space_reconcile.py"
  - ".veldo/control_space_reconcile.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "scripts/suites/*_veldo_0315_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0315-reconcile-at-start-and-on-demand.md"
  - "specs/index.md"
  - "proof/VELDO-0315/**"
behavior_bearing: true
observability:
  logs: >
    One reconcile record per run with what started it, the roots and engines read, and the counts:
    matched, adopted, reported, gone and completed.
  metrics: >
    Per reconcile: things matched, adopted, reported, gone and completed.
  error_taxonomy: >
    A failed reconcile is reported by name while the service serves everything else. A thing with no
    provable owner is a report, never an item.
acceptance_criteria:
  - id: AC1
    text: >
      Each row of the table in 8.8 gives its result, including the agent repository, the build root folder
      named for a worktree, the plain repository and the session scratch
    falsified_by: >
      Adopt every folder under a root; the row with no provable owner gets an item and fails
  - id: AC2
    text: >
      Reconcile completes a removing item and marks a missing one gone, and removes nothing else that was
      not already due. A removing worktree or private repository is completed only when its keep record
      exists and every ref in it resolves; otherwise it is deferred as keep_failed
    falsified_by: >
      Remove reported things; the reported fixture folder is gone and the row fails
  - id: AC3
    text: >
      The service replays the spool and reconciles before it accepts its first dispatch, and a failed
      reconcile is reported by name while everything else is served
    falsified_by: >
      Reconcile in the background; the row that sends a dispatch at once is admitted against an empty
      ledger and fails
  - id: AC4
    text: >
      Nothing runs reconcile on a schedule: the only callers are service start, the API action and the
      CLI. The row advances the fixture clock by a year with no event and counts one reconcile
    falsified_by: >
      Add a periodic call with any period; the row counts more than one and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. The ledger is no longer compared with the disk, and existing things are not adopted.
---

## Intent

At service start and on demand Veldo compares what is on disk and in Docker with the ledger. A thing with
a record is matched, a record with no thing is marked gone, and a thing with no record is adopted when a
stated rule proves its owner and reported otherwise. Reconcile removes nothing that was not already due,
and nothing runs it on a schedule.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 8.8 (reconcile), 4.4 (reconcile
record), 4.1 (what a crash leaves) and 6.6 (space.reconcile). Section 12 of the design holds the ticket
itself; its acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Reconciler, Authority service.

Build order. It is in the closing sequence 0315, 0316, 0334, 0317, 0327, 0318, 0343, 0340, 0342, 0319,
0320, 0332, 0325, 0339, 0321, 0322. The design states no dependency for this ticket, so depends_on holds
the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-13: amended for the owner's rule that no work is ever lost (Telegram 41209), design section 0.
  AC2: reconcile completes a removing worktree or private repository only when its keep record exists and
  every ref in it resolves (design 0.2); otherwise it is deferred as keep_failed and what is left of it
  stays. The falsifier is unchanged.
