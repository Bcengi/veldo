# VELDO-0343 proof

Implementation 8e43624de12a5ae17d01f9103b2fa991aebbd6c5. Builder evidence, not independent review. All
four criteria remain pending the lead gate and independent review.

## What was built

A detached worktree can hold a commit no ref reaches. The settled Discard now makes a kept branch
at that commit before anything is moved or removed (control_space_remove.py, _discard_branch):

- It runs after the keep step and the snapshot were compared with the terms the owner was shown,
  so the commit is the one shown, and before the worktree is moved to its marked name. Design 6.5
  names the branch first and the keep step second; a Discard refused for changed terms therefore
  writes no ref here. The remove runs only after the branch, the kept refs and the snapshot.
- It applies to a worktree with no branch whose checked-out commit no branch, tag or
  remote-tracking ref of its repository reaches (rule 5's holding refs). A worktree on a branch,
  an agent's included, gets none: Discard removes the worktree and never the branch.
- The name is the one the terms showed, as Save uses it. The ref is written create-only, read
  back, and recorded by the new Ledger command space_keep_branch as a branch item in state kept,
  with its commit and the worktree it was made for. The Ledger reads the worktree's HEAD and the
  branch itself inside the transaction.
- A name taken by a branch that does not hold the commit, a ref git refuses, a read that fails and
  a branch the Ledger did not record are each remove_refused. The worktree stays with everything
  in it; the refusal spends the answer and the next request names the next free name.
- No commit is made, nothing is removed by it, and no event record is written.

## Rows

13 ticket rows green in suite 150_veldo_0343_discard_keeps_commits (rows.json says what each
holds). The fixture is the one of VELDO-0318: temporary Git repositories and worktrees, real
SQLite, generated signatures, the ordinary inbox, presentation and settlement chain, the real keep
step, snapshots and removers. Telegram delivery, the process table, pool free bytes and Docker
reads are fixture inputs.

## Falsifiers

Finding 343 ran once, last, on the clean committed tree: 8 registered, 8 executed, 8 rejected, no
reuse, no invalid result, no surviving worker (teeth-run.json, falsifiers.json, teeth-receipt.json).
Each mutant was applied once and its target rows were seen red; baseline and no-op runs were green.

- AC1, declared: Discard without creating the branch. ac1/kept-branch and ac1/branch-item red.
- AC2, declared: the remove runs after the failed branch write. ac2/name-taken and ac2/git-refuses red.
- AC3, declared: the agent repository is removed with the worktree. ac3/agent red.
- AC4, declared: Discard commits the files on the kept branch as Save does. ac4/no-commit red.
- Guards, not in the specification: a branch made and not recorded (ac2/not-recorded), a branch
  for a commit a ref already holds (ac1/only-unheld), a Ledger that trusts the branch and one that
  trusts the commit (ac2/ledger-reads).

## Other runs (checks.json)

Green: 0318 45 rows, 0345 31, 0300 39, 0327 27, 0312 41, 0297 31, 0317 23. Validation, docs,
template sync, lint and the two boundary checks passed. No space supervisor survived any run. All
132 registered teeth cases that mutate the two engine modules still find their anchor exactly once
(checked by counting, not by running them).

Red and left:
- VELDO-0301 ac4/no-clock (suite 139): red on the base, inherited.
- VELDO-0326 ac2/observer-refused-by-name (suite 133): red on the base d0e2461a as well, run there
  from an exported copy. The row lists the ledger commands by hand and lacks
  space_disposition_request; space_keep_branch is one more name it lacks. Suite 133 is outside
  this footprint, so it is reported and not changed.

Not run: scripts/verify.sh, suites 151 and up, any live engine. Not built: nothing of the four
criteria; the group answers are VELDO-0340 and VELDO-0342.

Every artifact is smaller than 1 MB. This bundle was written from the teeth run's output after it
ended; the worktree was unchanged while it ran.
