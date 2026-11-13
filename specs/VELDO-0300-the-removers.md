---
schema: veldo.spec/v1
id: VELDO-0300
title: "The removers"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0326, VELDO-0331]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space_remove.py"
  - ".veldo/control_space_remove.py"
  - "scripts/suites/*_veldo_0300_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0300-the-removers.md"
  - "specs/index.md"
  - "proof/VELDO-0300/**"
behavior_bearing: true
observability:
  logs: >
    Each outcome records the method, the item's bytes just before, and the pool's free space before and
    after; for an engine image pool the host figure apart.
  error_taxonomy: >
    A refusal by git or by the engine is the deferral space_deferred:remove_refused with the thing
    untouched. A second probe that finds a user puts the folder back under its own name, and the item is
    deferred as space_deferred:in_use.
acceptance_criteria:
  - id: AC1
    text: >
      A folder is removed by rename, second probe, delete. The row injects an open file between the first
      probe and the rename through the probe's test seam, so the order is fixed; the folder comes back
      under its own name
    falsified_by: >
      Delete after the first probe; the row finds the folder gone and fails
  - id: AC2
    text: >
      A worktree is removed only by git's non-forced remove, and a refusal by git is the deferral
      remove_refused with the worktree untouched
    falsified_by: >
      Pass the force option; the row with an untracked file loses it and fails
  - id: AC3
    text: >
      No remover runs a prune command, and none but the discard remover passes a force option; the row
      reads every command each remover ran
    falsified_by: >
      Use the engine's volume prune for volumes; the command row fails
  - id: AC4
    text: >
      Each remover returns the item's bytes just before and the pool's free space before and after, and
      for an engine image pool the host figure apart
    falsified_by: >
      Report the engine's own reclaimable figure as freed; the row that compares it with the measured free
      space fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. Removers are called only through Signal, so without them nothing is removed.
---

## Intent

Each removal action has one remover, and it uses the owning tool's own remove: a rename, a second probe
and a delete for a folder, git's non-forced remove for a worktree, the engine's non-forced remove for a
Docker object. No remover runs a prune command.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.5 (removers). Section 12 of the
design holds the ticket itself; its acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Removers.

> The builder verifies with a test what git's non-forced worktree remove does with ignored files, and
> records the result in the proof. The design does not depend on the answer, because build output is removed
> before the worktree.

Build order. It is built together with 0298, 0299, 0330 and 0300, after the first five tickets. The design
states no dependency for this ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
