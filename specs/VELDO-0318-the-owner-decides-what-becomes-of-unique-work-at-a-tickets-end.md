---
schema: veldo.spec/v1
id: VELDO-0318
title: "The owner decides what becomes of unique work at a ticket's end"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0327, VELDO-0345]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space_signal.py"
  - ".veldo/control_space_signal.py"
  - "engine/.veldo/control_space_remove.py"
  - ".veldo/control_space_remove.py"
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "scripts/suites/*_veldo_0318_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0318-the-owner-decides-what-becomes-of-unique-work-at-a-tickets-end.md"
  - "specs/index.md"
  - "proof/VELDO-0318/**"
behavior_bearing: true
observability:
  logs: >
    The item's deferral records the decision request. Each answer's effect is one outcome: the commit and
    the kept branch for Save, kept for Keep, the forced remove for Discard.
  error_taxonomy: >
    space_deferred:unique_work with one request per item. A Discard whose file list no longer equals the
    list the owner was shown does not run. space_deferred:keep_failed when the snapshot cannot be saved,
    and when an ignored file that is work is new or changed at Save's remove.
acceptance_criteria:
  - id: AC1
    text: >
      A worktree deferred for unique work at ticket ended, project ended, worktree abandoned or released
      by its creator, and a worktree owned by a run that is not a review deferred at run finished, raises
      one request on the space disposition touchpoint with the three answers and the list of files; a
      later event for the same item raises no second one
    falsified_by: >
      Raise a request at every event; the row counts two requests and fails
  - id: AC2
    text: >
      Save commits the changes on a kept branch named for the ticket, or for the owning run when the
      worktree has no ticket, authored as the owner's configured identity, and then removes the worktree
      without force. Ignored files that are work go to the snapshot store, outside git, and never to the
      branch, and the remove runs only while those files still equal the snapshot by path, mode and
      digest: a new or changed one refuses it, and the worktree stays with everything in it. Before that
      last look the worktree is moved to a marked name beside itself by git's worktree move, without
      force, and the in-use probe, rule 5 and the comparison are made under that name; a user or a
      difference moves it back to its path. Without a settled Save answer Veldo makes no commit
    falsified_by: >
      Each of these turns a row of its own red. Commit at the deferral: the row finds a commit with no
      settled answer. Run Save's remove without the comparison: the row adds a local settings file between
      the snapshot and the remove, and finds it neither in place nor in the snapshot. Make the last look
      at the worktree's own path: the row writes an ignored settings file by that path between the look
      and git's remove, and finds it neither in place nor in the snapshot
  - id: AC3
    text: >
      Discard removes that one worktree with git's force option, only on a settled discard answer, only
      while the file list equals the list shown and rules 1, 2, 3, 4 and 6 pass. It first writes the
      snapshot of the uncommitted state to the snapshot store (VELDO-0345), runs only while the worktree
      still equals that snapshot, and does not run when the snapshot cannot be written, synced, read back
      or renamed into place. Before the remove the worktree is moved to a marked name beside itself by
      git's worktree move, without force; the in-use probe and the comparison with the snapshot are made
      again under that name, and a user or a difference moves it back to its path with everything in it. A
      Discard raised again after such a refusal saves under the next attempt number and leaves the earlier
      folder as it is. The branch and its commits are still there afterwards, and no commit is lost
      (VELDO-0343)
    falsified_by: >
      Each of these turns a row of its own red. Skip the list comparison: the row that adds a file after
      the request was shown loses it. Force the remove at the worktree's own path after the last look: the
      row writes a file by that path between the look and git's remove, and finds it neither in place nor
      restored
  - id: AC4
    text: >
      Keep sets the item to kept; no later event retries it and no second request is raised until the
      owner presses Abandon
    falsified_by: >
      Leave a kept item deferred; the next event's row raises a second request and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. A worktree with unique work stays deferred and raises no request.
---

## Intent

A worktree with uncommitted or unlanded work at its ticket's end is never removed by itself. Veldo raises
one request to the owner with three answers. Save commits the changes on a kept branch and removes the
worktree without force. Keep leaves it and asks nothing more. Discard is the one forced removal, and only
for the list of files the owner was shown. Veldo makes no commit without a settled Save answer.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 7 (unique work at a ticket's end,
and the Save, Keep and Discard answers), 6.5 (the discard remover) and 5 (the worktree rows). Section 12
of the design holds the ticket itself; its acceptance criteria and falsifiers are copied here word for
word.

What section 12 says about this ticket:

> Components: Signal, Removers (discard), Ledger (the effects). Depends on 0327 for the touchpoint and on
> 0345 for the snapshot. Review
> worktrees are VELDO-0336, VELDO-0340 and VELDO-0342. The kept branch Discard makes for a detached worktree
> is VELDO-0343.

Build order. It is in the closing sequence 0315, 0316, 0334, 0317, 0327, 0318, 0343, 0340, 0342, 0319,
0320, 0332, 0325, 0339, 0321, 0322. depends_on holds the dependencies the design states for this ticket.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-13: amended for the owner's rule that no work is ever lost (Telegram 41209), design section 0.
  AC2: Save writes ignored files that are work to the saved ref and never to the branch. AC3: Discard
  first writes the snapshot of the uncommitted state to the saved ref, runs only while the worktree still
  equals it, and does not run when the snapshot cannot be written, so a Discard can be undone with veldo
  space restore. Both falsifiers are unchanged. depends_on gains VELDO-0345, which builds the snapshot.
- 2026-11-13: amended for the lead's answers to the six questions of design section 15 (section 13 records
  them). A snapshot of uncommitted, untracked or ignored files is stored outside git, in the snapshot
  store under the state root, and never in a repository's object store, so a secret in an ignored file
  does not enter git; commits stay on kept refs (design 0.3). AC2: Save writes ignored files that are work
  to the snapshot store. AC3: Discard writes its snapshot to the snapshot store. Both said the saved ref.
  Both falsifiers are unchanged.
- 2026-11-13: amended from the validation of design section 0
  (design-veldo-nowork-0344r2-validation-2026-11-14.md, verdict CHANGES; design 14.7), under the owner's
  rule that no work is ever lost. N2.5: AC2 says Save's remove runs only while the worktree's ignored
  files that are work equal the snapshot by path, mode and digest; rule 5's case 3 counts exactly those
  files as saved, for that one remove. Without it Save could never finish, or lost an ignored file written
  after its snapshot. AC2 gains a second falsifier: a local settings file added between the snapshot and
  the remove. N2.1 and N2.2: AC3 lists the failures of the save that refuse the Discard, and a Discard
  raised again saves under the next attempt number and leaves the earlier folder as it is. AC3's falsifier
  is unchanged.
- 2026-11-13: amended for the two points of the final check of design section 0 that the amendment before
  this one left out (design-veldo-nowork-r2-validation-2026-11-14.md, F3 and F4; design 14.8), by the
  lead's word that both are required under the owner's rule that no work is ever lost. F4: Discard and
  Save each looked at the worktree once more and then ran one git command, and a file written between the
  two was lost by Discard, or deleted without a word by Save when git ignores it. AC2 and AC3: the
  worktree is first moved to a marked name beside itself by git's worktree move, without force, and the
  in-use probe and the last look are made under that name; a user or a difference moves it back to its
  path. A crash while it is under the marked name is set right with git's worktree repair at reconcile
  (VELDO-0315 AC2). AC2 gains a third falsifier and AC3 a second: the last look made at the worktree's own
  path. What stays outside is in design 0.9: a process that finds the marked name. Still four criteria.
