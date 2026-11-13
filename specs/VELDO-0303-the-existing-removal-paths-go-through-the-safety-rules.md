---
schema: veldo.spec/v1
id: VELDO-0303
title: "The existing removal paths go through the safety rules"
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
  - "engine/.veldo/fleet.py"
  - ".veldo/fleet.py"
  - "engine/.veldo/control_clone.py"
  - ".veldo/control_clone.py"
  - "engine/.veldo/control_launch.py"
  - ".veldo/control_launch.py"
  - "engine/.veldo/lander.py"
  - ".veldo/lander.py"
  - "engine/.veldo/control_launch_work.py"
  - ".veldo/control_launch_work.py"
  - "scripts/suites/*_veldo_0303_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0303-the-existing-removal-paths-go-through-the-safety-rules.md"
  - "specs/index.md"
  - "proof/VELDO-0303/**"
behavior_bearing: true
observability:
  logs: >
    Each of these removals is an outcome record like any other. A refusal that was swallowed before is a
    deferral with its rule's name.
  error_taxonomy: >
    clone_in_use is unchanged and stays first. Every other refusal is space_deferred with the rule's name.
acceptance_criteria:
  - id: AC1
    text: >
      A fleet worktree is removed through Signal without git's force option; one with an untracked file
      stays, and the refusal is a deferral on the record
    falsified_by: >
      Leave the force option in place; the row's untracked file is lost and the row fails
  - id: AC2
    text: >
      A clone's teardown and its failed-provision cleanup go through Signal; the clone_in_use refusal is
      unchanged; the pins are released after the removal outcome
    falsified_by: >
      Leave the direct delete in place; the row with a process holding an open file in the work tree finds
      the folder gone and fails
  - id: AC3
    text: >
      A run directory is removed through Signal, both at the receiver's end and for a leftover the sweep
      finds
    falsified_by: >
      Leave either direct delete in place; the item stays present after its folder is gone and the row
      fails
  - id: AC4
    text: >
      The landing line's candidate folders and the lander's candidate workspace are removed through Signal
    falsified_by: >
      Leave the direct delete in place; the same row for a candidate item fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. The seven paths delete directly again, the fleet's with git's force option.
---

## Intent

Seven places in the engine delete a folder or a worktree directly today, one with git's force option and
several with errors swallowed. This ticket sends each of them through Signal, so the safety rules apply
and a refusal is a deferral on the record.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.10 (existing removal paths: the
first seven rows of the Replaced table). Section 12 of the design holds the ticket itself; its acceptance
criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Fleet worktrees, Clone provisioner, Receiver, Landing line. The first seven rows of the table
> of 6.10 are the list; the batch and sandbox rows are VELDO-0324.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
