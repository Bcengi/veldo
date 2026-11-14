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
      named for a worktree, the plain repository and the session scratch. A clone folder's work tree, a
      batch clone and a candidate workspace are adopted as agent repository items with their form, and a
      folder that is itself a git repository is never adopted as scratch or as build output
    falsified_by: >
      Each of these turns a row of its own red. Adopt every folder under a root: the row with no provable
      owner gets an item. Adopt a batch clone as scratch: the row's clone holds a commit its main
      repository does not, its batch has ended and its scope is in act, and after reconcile the clone is
      gone and the commit is in no repository
  - id: AC2
    text: >
      Reconcile completes a removing item and marks a missing one gone, and removes nothing else that was
      not already due. An item is marked gone only when nothing is at its locator and nothing is beside it
      under its marked name. A removing worktree or private repository is completed only when its keep
      record exists, every ref in it resolves and every snapshot attempt it lists is there with its
      digest; otherwise it is deferred as keep_failed. A folder under its marked name that the comparison
      with its manifest stops is renamed back to its locator, and a worktree under its marked name that is
      in use or no longer equals its snapshot is moved back to its path; each is deferred as keep_failed.
      An item that is due or removing with a keep record, and whose thing is still whole at its locator,
      is attempted again from rule 1 (VELDO-0345 AC5)
    falsified_by: >
      Each of these turns a row of its own red. Remove reported things: the reported fixture folder is
      gone. Mark gone by the locator alone: the row's worker clone was left under its marked name holding
      a file its snapshot does not, and after reconcile the item is gone while that folder is on disk
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
  - id: AC5
    text: >
      Reconcile reads the carrier a removing item's removal record holds: the process id, its start time
      and the signal record (VELDO-0301 AC8). When the kernel shows that process live with that start
      time, the item is being removed now and reconcile leaves it as it is: it completes nothing, defers
      nothing, moves nothing back and attempts nothing. An item whose carrier is no longer the same live
      process, or whose record holds no carrier, is finished as AC2 says. A carrier that cannot be read
      is a live one. Reconcile's own attempt writes its own carrier. And an item is marked gone only
      when os.lstat said not found at its locator and at its marked name; any other answer defers it
      (VELDO-0301 AC6)
    falsified_by: >
      Each of these turns a row of its own red. Finish every removing item: the row's item is removing
      with a live process as its carrier, its remover stopped between the keep record and the tool, and
      after reconcile a second remover was handed it. Read a path with a look that answers nothing for
      an error: the row's folder is under a parent of mode 000 and its item is marked gone with the
      folder on disk
  - id: AC6
    text: >
      Reconcile carries out, through Signal's rules and removers and no other way, each item left due
      that may now be carried out: the installation's switch is on, and its scope is in act mode or the
      item carries the owner's confirmation. An item left due under a switch that is off, or unconfirmed
      in a scope in report mode, stays due. When a live Signal call is carrying the same item, the
      ledger's one removing write decides which of the two removes it, and the other writes nothing
    falsified_by: >
      Leave due items alone; the row's folder was left due with the switch off, the switch is on, and
      after reconcile the folder is still on disk and the row fails
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
- 2026-11-13: amended from the validation of design section 0
  (design-veldo-nowork-0344r2-validation-2026-11-14.md, verdict CHANGES; design 14.7), under the owner's
  rule that no work is ever lost. N1: AC1 says that a clone folder's work tree, a batch clone and a
  candidate workspace are adopted as agent repository items with their form, and that a folder that is
  itself a git repository is never adopted as scratch or build output; its second falsifier is the row the
  validation asked for, a batch clone with an unpushed commit, its batch ended and its scope in act,
  adopted as scratch. N2: AC2 completes a removing item only when the snapshot its keep record names is
  there with its digest, and an item that is due or removing with a keep record and still whole at its
  locator is attempted again from rule 1, which is how a crash between the save and the removal is
  recovered. AC2's falsifier is unchanged.
- 2026-11-13: amended from the final check of design section 0
  (design-veldo-nowork-r2-validation-2026-11-14.md, verdict CHANGES; design 14.8). F1: the keep record
  lists every snapshot attempt (VELDO-0345 AC5). AC2 completes a removing item only when every attempt its
  keep record lists is there with its digest, where it said the snapshot the record names. The falsifier
  is unchanged.
- 2026-11-13: amended for the two points of the final check of design section 0 that the amendment before
  this one left out (design-veldo-nowork-r2-validation-2026-11-14.md, F3 and F4; design 14.8), by the
  lead's word that both are required under the owner's rule that no work is ever lost. F3 and F4: AC2
  marks an item gone only when nothing is at its locator and nothing is beside it under its marked name. A
  folder under its marked name that the comparison with its manifest stops is renamed back to its locator,
  and a worktree under its marked name that is in use or no longer equals its snapshot is moved back to
  its path; each is deferred as keep_failed. Before, a worker clone's folder left under its marked name
  read as nothing at the locator and its item was marked gone. AC2 gains a second falsifier: gone by the
  locator alone. Still four criteria.
- 2026-11-14: from the independent review of VELDO-0300 (finding 8). No acceptance criterion changed: AC2
  already has reconcile look under the marked name before it marks an item gone. What the removers now
  give it: control_space_remove.left(path, id) returns the marked name when something is there,
  marked(path, id) writes the id without loss so that two items never share a name, and
  unmarked(name) reads the path and the id back. Since that review every worktree removal, not only
  the one after a Save or a Discard, moves the worktree to its marked name with git's worktree move
  before git's remove, so a removal killed in between leaves a whole worktree there with git's record
  pointing at it: reconcile reads it there, and moves it back with git's non-forced worktree move
  unless it completes the removal as AC2 says. Nothing in the tree calls left yet.
- 2026-11-14: from the independent review of VELDO-0301 (review-veldo-0301.md, findings 1, 3 and 4). Four
  criteria became six. AC5: Signal now writes the carrier of a removal on the item (process id, start
  time, signal record), so reconcile can tell a removing item a live process is removing now from one
  whose carrier died, and it leaves the first alone; before, both read the same and the design's row
  "attempted again from rule 1" (8.8) would have started a second remover on an item whose first was
  between its keep record and its tool. AC5 also binds reconcile to the same reading of not found as
  Signal: os.lstat's not found and nothing else; control_space_probe.there and control_space_remove.left
  read that way since that fix, and left raises on any other answer. AC6: an item Signal leaves due
  (the switch off, report mode, a caller with no removers) is matched by no later event, so reconcile
  carries those that may now be carried out; the owner's Confirm (VELDO-0320 AC1) carries the confirmed
  ones. AC5 and AC6 are not in section 12 of the design, whose text this change does not edit.
