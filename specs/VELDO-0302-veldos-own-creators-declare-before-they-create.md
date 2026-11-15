---
schema: veldo.spec/v1
id: VELDO-0302
title: "Veldo's own creators declare before they create"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0301]
placement: [engine, loop]
protected_paths: ["engine/scripts/agent_sandbox.py", "scripts/agent_sandbox.py"]
footprint:
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "engine/.veldo/control_clone.py"
  - ".veldo/control_clone.py"
  - "engine/.veldo/fleet.py"
  - ".veldo/fleet.py"
  - "engine/.veldo/control_batch.py"
  - ".veldo/control_batch.py"
  - "engine/scripts/agent_sandbox.py"
  - "scripts/agent_sandbox.py"
  - "engine/.veldo/control_launch.py"
  - ".veldo/control_launch.py"
  - "engine/.veldo/lander.py"
  - ".veldo/lander.py"
  - "engine/.veldo/control_launch_work.py"
  - ".veldo/control_launch_work.py"
  - "scripts/suites/*_veldo_0302_*.py"
  - "scripts/suites/142_veldo_0303_space_paths.py"
  - "specs/VELDO-0347-work-the-first-rules-did-not-see-ignored-files-repositories-in-any-folder-evidence.md"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0302-veldos-own-creators-declare-before-they-create.md"
  - "specs/index.md"
  - "proof/VELDO-0302/**"
behavior_bearing: true
observability:
  logs: >
    Each creation is two journal records, declared and present, with project, ticket, run and lane as
    owner and the creator's name. A creation that fails is marked gone.
  error_taxonomy: >
    unavailable_service:space_ledger when a creator cannot reach the ledger; it then creates nothing. With
    no central installation the seam stands down and things are created as today.
acceptance_criteria:
  - id: AC1
    text: >
      Each creator's thing has a declared item before it exists and a present item after, with project,
      ticket, run and lane as owner; the rows cover the clone, the fleet worktree, the run directory, the
      candidate workspace, the batch clone and the batch's observation folder. The clone's work tree, the
      batch clone and the candidate workspace are declared as items of the kind agent repository, each
      with its form and its main repository, and never as scratch. The receiver's artifacts, receipts and
      token records are declared as evidence, never as scratch
    falsified_by: >
      Each of these turns a row of its own red. Declare after creating: the row that kills the creator
      between the two finds a folder with no item. Declare the batch clone as scratch: the row that reads
      the item finds the kind scratch and no main repository
  - id: AC2
    text: >
      The sandbox's prepare leaves three items: the agent repository, its worktree as the repository's
      child, and the branch with its start commit
    falsified_by: >
      Declare the worktree only; the row finds the agent repository with no item and fails
  - id: AC3
    text: >
      A creator that cannot reach the ledger creates nothing and refuses unavailable_service:space_ledger;
      with no central installation it creates as today
    falsified_by: >
      Create anyway on a refused declare; the row finds the folder and fails
  - id: AC4
    text: >
      A creator that provisions a ticket's next run in another worktree calls the service's
      space_provisioned for that ticket before it confirms the new worktree's item, so the ticket's
      earlier worktree is sent worktree abandoned (VELDO-0312)
    falsified_by: >
      Provision the second worktree without the call; the row's first worktree, clean and landed
      nowhere else, stays present with no event sent, and the row fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. Creators create without declaring, as before. Items already recorded stay in the
  ledger.
---

## Intent

Everything Veldo itself creates gets a ledger record before it exists. This ticket puts the declare and
confirm calls around each creator: the clone provisioner, the fleet's worktrees, the batch, the sandbox's
prepare, the receiver's run folders and the landing line's candidate workspaces. A creator that cannot
reach the ledger creates nothing.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 3 (components), 6.1 (declare,
confirm, gone), 6.2 (the seam a creator calls) and 8.1 (steps 3 and 4). Section 12 of the design holds the
ticket itself; its acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Clone provisioner, Fleet worktrees, Batch, Sandbox (protected), Receiver's run folders,
> Landing line.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

The sandbox (engine/scripts/agent_sandbox.py and its synced copy) is a protected path, policy.yaml:22 and
35. The owner's recorded approval, bound to the commit and the proof, is required.

## History

- 2026-11-15: fix round after the review (verdict FIX). Finding 1: the row ac2/three-items always
  reports; under the declare-after-creating mutation it fails and no longer disappears. Finding 2: the
  ledger accepts the form agent, so the accepted forms are exactly the four of design 4.1. Finding 3:
  a creator's source that is a linked worktree of the main repository is read through git's common
  directory and accepted; a source outside the main repository, and a folder beneath it that is no
  work tree, stay refused. Note N1: the sandbox's prepare no longer writes veldo-space.json, which had
  no reader and no criterion; the creator module is still loaded on every prepare. Three cases were
  added to the mutation registry, twelve in all for this ticket.

- 2026-11-15: the VELDO-0303 removal fixture still supplied predeclared items to creators.
  Its footprint is included for fixture adaptation: manual fleet setup uses an unwired creator,
  and the failed-clone row reads the items the creator now declares. Every removal assertion stays.

- 2026-11-15: lead decision, the ledger's repository form field and its validation are built here; VELDO-0347 builds on it

- 2026-11-15: build dependency found at base 8ef46604. AC1 requires the repository form on
  declared agent repository items, but Ledger.declare in engine/.veldo/control_space.py has no
  form parameter and its item writer records no form. Design section 0.8 assigns that ledger
  field to VELDO-0347, which is not built at this base; the ledger files are outside this
  ticket's footprint. The build instruction excludes later tickets. Implementation is pending
  the lead's decision to supply that dependency or authorize the minimal ledger field and
  validation here. No runtime code was changed and no acceptance criterion was weakened.
  Separately, VELDO-0315's service startup wiring and proof bundle are absent at this base,
  despite its inclusion in the build handoff's completed list. Service.space still starts as
  None. This observation needs reconciliation before claiming installed creator integration.

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-13: amended for the owner's rule that no work is ever lost (Telegram 41209), design section 0.
  AC1: a clone, a batch clone and a candidate workspace are declared with their main repository, because
  each is a private repository whose commits the keep step must bring across before it goes; the
  receiver's artifacts, receipts and token records are declared as evidence and never as scratch. The
  falsifier is unchanged.
- 2026-11-13: amended from the validation of design section 0
  (design-veldo-nowork-0344r2-validation-2026-11-14.md, verdict CHANGES; design 14.7), under the owner's
  rule that no work is ever lost. N1: AC1 names the kind. The clone's work tree, the batch clone and the
  candidate workspace are declared as items of the kind agent repository, each with its form and its main
  repository, and never as scratch; the design still said scratch in four places an implementer builds
  from. AC1 gains a second falsifier: the batch clone declared as scratch.
- 2026-11-14: AC4 added, from the review of VELDO-0312 (finding F4), by the lead's decision. VELDO-0312
  built the entry space_provisioned and nothing called it: the creators of this ticket (the fleet
  worktrees, the sandbox's prepare) are what provision a ticket's next run in a worktree. The call comes
  before the new worktree's item is confirmed; a declared item is not signalled, so the order is safe. A
  worktree the owner marked Keep is sent nothing by it. No code in that round.
