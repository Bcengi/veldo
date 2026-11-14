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
- 2026-11-13: from the owner's rule that no work is ever lost (Telegram 41209), design section 0. No
  acceptance criterion changed. A clone and a candidate workspace are private repositories: VELDO-0347 AC3
  has the keep step record their commits in the main repository before the folder goes, and defers one
  whose work tree holds uncommitted work.
- 2026-11-14: built. No acceptance criterion changed. What the build decided, recorded here because
  the criteria do not say it:
  - The seam. Each of the five modules is given `space`, a mapping with the Ledger and the arguments
    Signal takes (probe, kinds, remover, free, keep, owner_live and the rest), or None. Each module
    carries the same small function, space_signal: it finds the live items the ledger records at or
    beneath the paths of the removal, signals the event once for each owner among them with every
    part of that owner as the subject, and answers with the state of each path's item. It deletes
    nothing. The function is carried five times because no shared module is in this footprint.
    Nothing in the engine builds `space` yet: the service holds no Ledger, and the creators declare
    nothing until VELDO-0302. Until both are wired the five paths run as before.
  - With no ledger each path removes as it did, as a creator with no central installation creates as
    it did (design 6.1). So the direct deletes are still in the files, in the branch that runs only
    when `space` is None; the existing suites of the clone, the run directory and the landing line
    drive that branch and are unchanged. The boundary check of VELDO-0304 has to name those branches.
    One thing differs with no ledger: the fleet never passes git's force option. It runs git's
    non-forced remove, and only for a worktree this provisioner added whose checked-out commit has
    not moved since, because with no ledger there is no keep step and a commit made on the detached
    head would be named by nothing. Anything else stays and is listed, never swallowed.
  - The events. A fleet worktree: worktree abandoned. A clone at teardown and at a failed
    provisioning, a run directory at the receiver's end and at the sweep, a candidate folder at the
    landing line's close and the lander's candidate workspace at discard: run finished. Design
    section 5 names run finished for a worker clone and leaves the landing line's event unnamed; the
    lander's discard is the sibling of the batch's discard, which 6.10 gives run finished.
  - A private repository is not removed at run finished by today's table. The row of an agent
    repository whose form is a worker clone or a candidate workspace is VELDO-0347. Until it is built
    the ledger does not make a clone's work tree or a candidate folder due at run finished: it stays,
    it holds its root, its pins stay held, and the teardown is refused. The suite adds that one cell
    to a copy of the registry, as a stand-in.
  - Rule 3. Where a module has just read from the kernel that the run is over (the clone's users
    have ended, the sweep's kernel test, a receiver whose group is known to be empty or whose engine
    never started), rule 3 is answered conclusive for the runs that own the items of that removal,
    and for no other owner. A receiver whose group nobody could read does not answer; the wired
    answer does.
  - The pins. They are released only when the work tree's item is removed or gone, or when no live
    item records the work tree and the kernel says nothing is at its path. Not found is the only
    answer that counts: a path that could not be read releases nothing.
  - A failed provisioning confirms the items still in state declared, so that the event reaches
    them, and then signals. What was never made is marked gone by Signal.
  - The fleet signals only for its own worktree: when the worktree's owner also owns another
    worktree or agent repository the event would end, nothing is signalled and the worktree stays.
  - A refusal is space_deferred and the rule's name. For an item no rule deferred it is the state the
    item is in: due (report mode), removing (left under its marked name), kept, present; and
    not_in_ledger when no item records the thing. space_deferred is in the clone's taxonomy as
    stale_subject, beside clone_in_use.
  - For the lead, not built here because control_retirement.py is not in this footprint: a clone
    whose teardown is refused keeps its dispatch's worker slot, since the clone obligation stays open
    while its root is on disk or a pin is held. In report mode every clone is left due, so once a
    ledger is wired every dispatch would keep its slot until the owner's Confirm. The same holds for
    a clone a rule defers. This needs a decision before `space` is wired into the clone provisioner.
