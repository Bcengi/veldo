---
schema: veldo.spec/v1
id: VELDO-0336
title: "A worktree a run owns"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0311, VELDO-0313, VELDO-0345]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/hooks/post-checkout"
  - "engine/hooks/reference-transaction"
  - "engine/.veldo/control_space_kinds.py"
  - ".veldo/control_space_kinds.py"
  - "engine/.veldo/control_space_spool.py"
  - ".veldo/control_space_spool.py"
  - "engine/.veldo/control_space_signal.py"
  - ".veldo/control_space_signal.py"
  - "engine/.veldo/control_space_remove.py"
  - ".veldo/control_space_remove.py"
  - "engine/.veldo/control_space_keep.py"
  - ".veldo/control_space_keep.py"
  - "engine/bin/veldo"
  - "bin/veldo"
  - "scripts/suites/*_veldo_0336_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0336-a-worktree-a-run-owns.md"
  - "specs/index.md"
  - "proof/VELDO-0336/**"
behavior_bearing: true
observability:
  logs: >
    The worktree's item records the owning run and its station. Each review scratch path removed is part
    of the worktree's outcome.
  error_taxonomy: >
    A stray file a live process holds open keeps its worktree, space_deferred:in_use. A path that resolves
    outside the worktree, or is on the protect list, is not removed. A file that is not in the snapshot's
    manifest, or differs from it, stops the removal, space_deferred:keep_failed.
acceptance_criteria:
  - id: AC1
    text: >
      A worktree added detached with plain git inside a wrapped run is recorded with that run as owner, a
      review worktree when the run's station is review, and is removed at the run's run finished by git's
      non-forced remove, after its build output
    falsified_by: >
      Record it with the project as its only owner; the row finds the review worktree present after run
      finished and fails
  - id: AC2
    text: >
      A worktree added on a branch inside a wrapped run keeps the owner its branch pattern gives and is
      still there after run finished
    falsified_by: >
      Give every worktree made inside a wrapped run to the run; the row's ticket worktree is removed at
      run finished and fails
  - id: AC3
    text: >
      A review worktree with an untracked file git does not ignore is removed at run finished with no
      decision request and no force option; the file is saved in the snapshot store (VELDO-0345) and then
      deleted, as review scratch. Each file is compared with the snapshot's manifest immediately before it
      is deleted, and one that is not in the manifest or differs from it stops the removal, with the
      worktree deferred as keep_failed
    falsified_by: >
      Each of these turns a row of its own red. Defer it as unique work: the row finds the worktree
      present and a request raised. Delete the scratch without the snapshot: the row's stray file is
      neither in place nor restored. Delete without the comparison: the row rewrites the stray file after
      the snapshot, and finds the new content neither in place nor in the snapshot
  - id: AC4
    text: >
      Review scratch is removed path by path under rules 1, 2, 3, 4 and 6, with no force option and no
      clean command: a stray file a live process holds open keeps its worktree, deferred as in_use, and a
      stray link is deleted without its target being touched
    falsified_by: >
      Follow the link; the row's target file outside the worktree is gone and the row fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. A detached worktree made inside a wrapped run is recorded with the project as its
  only owner and ends on nothing its run does.
---

## Intent

A review's throwaway checkout is added detached, so it follows no branch and no ticket. A detached
worktree added inside a wrapped run is recorded with that run as owner and goes at the run's run finished.
In a review worktree a stray untracked file is review scratch: it is deleted path by path, with no request
and no force option, and then the worktree goes by git's non-forced remove.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 5 (the two rows for a worktree a run
owns), 6.5 (the review scratch remover), 6.9 (the throwaway worktree row), 7 (review scratch) and 8.5.
Section 12 of the design holds the ticket itself; its acceptance criteria and falsifiers are copied here
word for word.

What section 12 says about this ticket:

> Components: Git hooks, Kind registry, CLI (the run wrapper). Depends on 0311, 0313 and 0345.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). depends_on holds the dependencies the
design states for this ticket.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-13: amended for the owner's rule that no work is ever lost (Telegram 41209), design section 0.
  AC3: review scratch is saved on a kept ref before it is deleted. No request is raised, as before; the
  lead's decision (e) stands. The falsifier is unchanged. depends_on gains VELDO-0345, which builds the
  snapshot. Design section 15 puts the stricter reading, a request for every stray file, to the owner.
- 2026-11-13: amended for the lead's answers to the six questions of design section 15 (section 13 records
  them). A snapshot of uncommitted, untracked or ignored files is stored outside git, in the snapshot
  store under the state root, and never in a repository's object store, so a secret in an ignored file
  does not enter git; commits stay on kept refs (design 0.3). AC3: review scratch is saved in the snapshot
  store before it is deleted, where it said on a kept ref. The lead confirmed decision (e): saved first,
  then removed with no request, because saved means not lost. The falsifier is unchanged.
- 2026-11-13: amended from the validation of design section 0
  (design-veldo-nowork-0344r2-validation-2026-11-14.md, verdict CHANGES; design 14.7), under the owner's
  rule that no work is ever lost. N2.3: AC3 says each file of review scratch is compared with the
  snapshot's manifest immediately before it is deleted, and one that is not in it or differs from it stops
  the removal with the worktree deferred as keep_failed; the remover deletes path by path after one
  snapshot, and a file rewritten in between went unsaved. N2.4: AC3 gains two falsifiers, the scratch
  deleted without the snapshot, which nothing caught, and the delete without the comparison.

- 2026-11-15: footprint names the hook transport, Signal, existing remover and keeper with their synced copies. The hook already inherits the run label; its transport resolves the station from the wrapper record. Signal supplies the scratch rules reader, the keeper saves review scratch, and the existing remover compares each file before deletion. No later ticket is implemented.
