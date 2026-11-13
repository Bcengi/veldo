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
depends_on: [VELDO-0327]
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
    list the owner was shown does not run.
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
      without force. Without a settled Save answer Veldo makes no commit
    falsified_by: >
      Commit at the deferral; the row finds a commit with no settled answer and fails
  - id: AC3
    text: >
      Discard removes that one worktree with git's force option, only on a settled discard answer, only
      while the file list equals the list shown and rules 1, 2, 3, 4 and 6 pass; the branch and its
      commits are still there afterwards, and no commit is lost (VELDO-0343)
    falsified_by: >
      Skip the list comparison; the row that adds a file after the request was shown loses it and fails
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

> Components: Signal, Removers (discard), Ledger (the effects). Depends on 0327 for the touchpoint. Review
> worktrees are VELDO-0336, VELDO-0340 and VELDO-0342. The kept branch Discard makes for a detached worktree
> is VELDO-0343.

Build order. It is in the closing sequence 0315, 0316, 0334, 0317, 0327, 0318, 0343, 0340, 0342, 0319,
0320, 0332, 0325, 0339, 0321, 0322. depends_on holds the dependencies the design states for this ticket.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
