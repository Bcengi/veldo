# VELDO-0343 proof

Implementation 25da645b27e98720fbfcd9fe736cbccc0e664d0a (fix round 2; fix round 1 at c8a68865, first built at 8e43624d).
Builder evidence, not independent review. All four criteria remain pending the lead gate and independent
review.

## Fix round 2, 2026-11-16

The three LOW findings of the same review. Where this section gives counts they replace the ones below.

- Finding 4 (teeth), rows only, no code changed. ac2/ledger-reads gains a worktree on a branch,
  refused space_keep_branch_attached. Row ac2/create-only: another branch takes the kept name
  between the remover's look and its write; git refuses the create-only write, the Discard is
  remove_refused and the other branch is not moved. Falsifiers: the Ledger's attached check dropped
  (ac2/ledger-reads red), and the write made without the empty old value (ac2/create-only red).
- Finding 5, lead decision. Only refs/heads count as holders for the "already held" test; a commit
  that only a tag or a remote-tracking ref reaches gets a kept branch like any other (remover,
  HOLDING_REFS). Row ac1/only-a-branch-holds. Falsifier: tags and remote-tracking refs counted
  again; the row went red. Spec History and design 6.5 record the decision.
- Finding 6, first part. A kept name whose branch item is due, deferred or removing is taken
  (remover, _free_branch): the request names the next name, where every Discard under the first
  was refused space_keep_branch_item. Row ac2/name-of-a-leaving-item. Falsifier: such an item's
  name counted free; the row went red.
- Finding 6, second part. The branch a stopped Discard left is recorded by reconcile as it defers
  the removing worktree (remover record_left_branch, called from the Reconciler's defer), so an
  owner's Keep leaves no unrecorded branch. It writes no ref and removes nothing; the Ledger reads
  the HEAD, the attachment and the branch as for any kept branch. Row ac1/reconcile-records.
  Falsifiers: the branch found and not recorded, and reconcile deferring without the call; each
  turned the row red. The review's R6 is left as it is, the lead's call.
- Footprint. The lead's instruction puts the record in reconcile, so the spec's footprint now
  names control_space_reconcile.py and its synced copy: one call, three lines. That module's own
  suite, 156_veldo_0315_reconcile, is above the limit this round was given and was NOT run.
- ac1/stopped-before-record now also requires that the Discard itself answered with the kept
  branch: with reconcile recording the branch first, the round 1 holder mutant would otherwise
  have survived. It is rejected in the final run.

Rows: 20 green in the ticket suite. Neighbours, all run this round: 0318 45, 0345 31, 0300 39, 0327
27, suite 133 30, 0312 41, 0297 31, 0317 23, 0329 21, all green; 0301 17 green and ac4/no-clock red,
inherited. Two more suites that load the reconcile module were run and are red exactly as on an
exported copy of the base 48af7f64: 0307 ownership/removes-nothing (1 row) and 0331 (14 rows, its
own temporary state folder is missing). Inherited, left. Fast checks passed: validation, docs,
template sync, lint, space boundary, git boundary. All 188 registered teeth cases that mutate the
three engine modules find their anchor exactly once (counted).

Teeth, finding 343, final run, last, on the clean committed tree: 20 registered, 20 executed, 20
rejected, no reuse, no invalid result, no surviving worker, 255 s. It was not the only run
(teeth-run.json, earlier_runs). The first start, on c7f824c0, stopped with a driver error before
any mutant, because the suite did not load the reconcile module from the tree (fixed in e126530f).
The second applied all 20 and rejected 19: the declared AC1 falsifier was an invalid result,
because three new rows read a branch that mutant never makes, and the rows after them were absent
instead of red. The new rows now read a missing branch as missing (the commit named above), and
the whole finding ran again. So the harness applied each of the 20 mutants twice, where the brief
asked for once. Before the first commit each of the six
new mutants and the round 1 holder mutant was applied once by hand and seen red (teeth-run.json,
hand_checks).

The sections below describe fix round 1 and the first build; the holding refs, the row and
falsifier counts and the suites run are as this section says.

## Fix round 1, 2026-11-16

Independent review of 62a511f5, verdict FIX, no path that loses work. Where this section gives counts
they replace the ones below.

- Finding 1, fixed. A detached worktree inside an agent repository had its kept branch written and
  recorded in the agent repository, which is private and goes later. It is now written, read back
  and recorded in the main repository of the worktree's scope, where the keep step has already put
  the commit on a kept ref (remover _kept_home; the Ledger's keep_branch reads and records there).
  A ref of either repository that holds the commit still means no branch. With no main repository
  at its path, or a name taken there by other work, the Discard is remove_refused and nothing is
  written in the agent repository instead. The name shown for such a worktree is free in both
  repositories, because Save writes it in the agent one. Rows ac3/detached and
  ac3/detached-refused. Falsifiers: the branch written in the agent repository, and the Ledger
  recording there; each turned ac3/detached red.
- Finding 2, row added, no code changed. ac1/stopped-before-record stops the Discard inside
  keep_branch after the ref write, writes reconcile's deferral, and requires that the next Discard
  names the same branch and leaves one branch, one kept branch item and no -2 name. Falsifier: the
  reviewer's mutation, a branch left by the stopped Discard counted a holder; it turned the row red.
- Lead decision (a). The built order is kept: the branch is made after the keep step and the
  snapshot were compared with the terms, before the move. Design 6.5 is reworded to it, with the
  crash points and finding 1's placement (docs/design/VELDO-0295-design.md is not a protected
  path; that one section only). The spec History records it.
- Lead decision (b). VELDO-0326 ac2/observer-refused-by-name (suite 133) now sends
  space_disposition_request, space_disposition and space_keep_branch as the observer and requires
  each refused by its name. Suite 133 is 30 green, where it was 29 and that row red. Falsifiers: the
  observer let through for each of the three commands; each turned the row red.
- Not taken up, the lead's call: review findings 4, 5 and 6. VELDO-0301 ac4/no-clock is inherited
  and left; suite 139 was not run again.

Rows: 16 green in the ticket suite. Neighbours run again: 0318 45, 0345 31, 0300 39, 0327 27, suite
133 30, all green. Not run again: 0312, 0297, 0317, 0301 (checks.json keeps their earlier results).
Fast checks passed: validation, docs, template sync, lint, space boundary, git boundary. All 155
registered teeth cases that mutate the two engine modules find their anchor exactly once (counted).
One 0318 anchor (space318-second-worktree-takes-the-first-name) sits on a line this round first
rewrote; the line was put back as it was, so that case is unchanged.

Teeth, finding 343, final run, last, on the clean committed tree: 14 registered, 14 executed, 14
rejected, no reuse, no invalid result, no surviving worker, 200 s. It was not the only run
(teeth-run.json, earlier_runs). The first start stopped with a driver error before any mutant,
because the builder had made the log folder. The second applied all 14 and rejected 13: the
declared AC3 falsifier, which deletes the agent repository, was an invalid result, because the two
new agent rows were absent instead of red. The suite now marks both red when the agent repository
is gone (c8a68865), and the whole finding ran again. So 13 mutants were applied twice and one three
times, where the brief asked for once.

The sections below describe the first build; the kept branch's repository for an agent's detached
worktree, the row and falsifier counts, and the suite 133 row are as this section says.

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
