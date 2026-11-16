---
schema: veldo.spec/v1
id: VELDO-0343
title: "Discard keeps every commit"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0318, VELDO-0345]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space_remove.py"
  - ".veldo/control_space_remove.py"
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "scripts/suites/*_veldo_0343_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0343-discard-keeps-every-commit.md"
  - "specs/index.md"
  - "proof/VELDO-0343/**"
behavior_bearing: true
observability:
  logs: >
    The kept branch is recorded as a branch item in state kept, with its name and commit, before the
    discard outcome.
  error_taxonomy: >
    When the kept branch cannot be created the discard does not run, and the worktree is deferred as
    space_deferred:remove_refused with everything in it.
acceptance_criteria:
  - id: AC1
    text: >
      Discard of a detached worktree whose checked-out commit no ref holds first creates a kept branch at
      that commit, named as Save names one, and records it as a branch item in state kept; afterwards the
      commit is reachable from that branch, and the worktree's uncommitted file is gone from disk and is
      in the saved snapshot (VELDO-0345)
    falsified_by: >
      Discard without creating the branch; the row finds the commit unreachable and fails
  - id: AC2
    text: >
      When the kept branch cannot be created, because the name is taken by a branch that does not hold the
      commit or git refuses the ref, the discard does not run: the worktree and its files are still there,
      deferred as remove_refused
    falsified_by: >
      Run the remove after the failed branch write; the row finds the worktree gone and the commit
      unreachable and fails
  - id: AC3
    text: >
      Discard of an agent's worktree leaves the agent repository and its branch in place, kept, with every
      commit on that branch
    falsified_by: >
      Remove the agent repository with the worktree; the row finds the branch's commit in no repository
      and fails
  - id: AC4
    text: >
      Creating the kept branch makes no commit, Discard makes no commit, and neither sends a landing
      event: the row counts the same commits in the repository and the same event records before and after
    falsified_by: >
      Commit the worktree's files on the kept branch in Discard as Save does; the row finds a new commit
      on a branch and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. Discard of a detached worktree removes it without first making a branch, so a commit
  no ref holds becomes unreachable. Kept branches already made stay.
---

## Intent

A detached worktree can hold a commit that no ref reaches. Before Discard removes such a worktree, the
Ledger creates a kept branch at the checked-out commit, and the remove runs only after that. Discard loses
uncommitted work only.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.5 (Discard never loses a commit,
and the paragraphs after it), 7 (the Discard answer) and 13 (the decision that Discard never loses
commits). Section 12 of the design holds the ticket itself; its acceptance criteria and falsifiers are
copied here word for word.

What section 12 says about this ticket:

> Components: Removers (discard), Ledger. Depends on 0318 and 0345; the group answers are 0340 and 0342.

Build order. It is in the closing sequence 0315, 0316, 0334, 0317, 0327, 0318, 0343, 0340, 0342, 0319,
0320, 0332, 0325, 0339, 0321, 0322. depends_on holds the dependencies the design states for this ticket.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-13: amended for the owner's rule that no work is ever lost (Telegram 41209), design section 0.
  AC1: the worktree's uncommitted file is gone from disk and is in the saved snapshot. AC4: Discard makes
  no commit on any branch; its snapshot is a commit on a kept ref, so the row counts the commits reachable
  from branches, and the falsifier commits on the kept branch. depends_on gains VELDO-0345.
- 2026-11-13: amended for the lead's answers to the six questions of design section 15 (section 13 records
  them). A snapshot of uncommitted, untracked or ignored files is stored outside git, in the snapshot
  store under the state root, and never in a repository's object store, so a secret in an ignored file
  does not enter git; commits stay on kept refs (design 0.3). AC4: Discard makes no commit at all, where
  it said none on any branch, because its snapshot is no longer a commit; the row counts the commits in
  the repository. The falsifier is unchanged.
- 2026-11-16: built. No acceptance criterion changed.
  Where it runs: in the settled Discard, after the keep step and the snapshot have been compared
  with the terms the owner was shown, and before the worktree is moved to its marked name. Design
  6.5 names the branch first and the keep step after it; the branch is made once the commit is
  known to be the one the owner was shown, so a Discard refused for changed terms writes no ref.
  The remove still runs only after the branch, the kept refs and the snapshot.
  Which worktree: one with no branch whose checked-out commit no branch, tag or remote-tracking ref
  of its repository reaches (rule 5's holding refs; a kept ref and a stash hold nothing). A worktree
  on a branch gets none, in an agent repository as anywhere else. A read that fails refuses.
  The name is the one the terms showed (VELDO-0327, VELDO-0318 fix round 1), else the next free
  one. The ref is written create-only at the commit, read back, and then recorded by the Ledger's
  new command space_keep_branch as a branch item in state kept, with its commit and the worktree it
  was made for. The Ledger reads the worktree's HEAD and the branch itself before it writes. A name
  taken by a branch that does not hold the commit, a ref git refuses, and a branch the Ledger did
  not record are each remove_refused, with the worktree and everything in it in place; the refusal
  spends the answer and the next request names the next free name (VELDO-0318).
  Rows: ac1/name, ac1/kept-branch, ac1/branch-item, ac1/snapshot, ac1/only-unheld, ac2/name-taken,
  ac2/next-name, ac2/git-refuses, ac2/not-recorded, ac2/ledger-reads, ac3/agent, ac4/no-commit,
  ac4/no-event. Eight teeth cases under finding 343: the four declared falsifiers and four guards.
  Reported, not changed: VELDO-0326's row ac2/observer-refused-by-name (suite 133, outside this
  footprint) lists the ledger commands by hand and is red on the base d0e2461a, where it does not
  list space_disposition_request; space_keep_branch is one more name it does not list.
