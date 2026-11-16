# VELDO-0347 proof

Implementation 1f8aaebb059e759d982f4eb50e727d7c6ab02940 (the fix round; the build was f347196e), on base
7e457e85 (the blocker commit of the first run). Builder evidence, not independent review. All five
criteria remain pending the lead gate and independent review. The accepted rows that were pinned and red
after the build are green: see "Fix round" below. One inherited row is red; suites 151 and up were not run.

## What was built

- AC1. Rule 5 reads the paths git ignores. A loose ignored file, a path only a personal rule covers and a
  path whose rule cannot be traced are untracked work, case 3, and the deferral names each with its rule.
  A folder a committed ignore file of the work tree or a declared build output pattern covers is build
  output; in an adopted worktree only the pattern counts (probe, ignored_work; Signal, rule 5).
- AC2. Rule 6 looks beneath a scratch and a build output item. A repository there holds the item, as
  unrecorded, unless the probe reads it as a clean clone now (probe, clean_clone): no file in no commit,
  no stash, no linked worktree, every ref and the HEAD reached by a remote-tracking ref of a configured
  remote, no log entry those refs do not reach, and for a remote that is a path on this host each of
  those commits held by a ref of that repository now. What cannot be read holds the item, as unread. The
  folder remover reads every repository again under the marked name before it deletes.
- AC3. The three clones are agent repository items with their form (declared so since VELDO-0302). A
  batch clone or a candidate workspace with a file in no commit is deferred as unique work and raises
  one request that names it as a clone and offers Keep alone. An ended worker clone, shown to be one by
  its manifest under the state root, is saved by the keep step's snapshot, each file is compared with
  the manifest immediately before its delete, the git folder goes last, and a stop renames the folder
  back before the item is deferred.
- AC4. The evidence remover (action remove_held) reads each file's digest at the removal through one
  descriptor and deletes it only when the store holds a blob with that digest or a commit the trunk or
  a kept ref reaches holds the file, and the file is unchanged since it was read. Nothing recorded
  earlier is read. A store or a commit that cannot be read is no copy.
- AC5. Rule 6 starts at the item's own folder: an item of a kind other than worktree and agent
  repository whose folder is a repository holds itself. Table 2 of the kind registry is table 1 and the
  row agent_repository_clone; the form picks the row and the events, and an item with no form reads the
  agent repository's own.

## Rows

27 green in the ticket suite, scripts/suites/150_veldo_0347_unseen_work.py (rows.json): AC1 4, AC2 8, AC3
7, AC4 4, AC5 3, and the canon row. Rows of six accepted suites were updated as the lead decided, in the
build and in the fix round, and one was added, all green (rows.json, other_suite; the spec History and
each suite's own History name each row and the criterion that supersedes it).

## Falsifiers and teeth

Finding 347: 19 registered, 19 executed, 19 rejected, no reuse, no invalid result, no surviving worker,
75 s. The run of the fix round, last, on the clean committed tree of 1f8aaebb; no mutant was applied by
hand (teeth-run.json, teeth-receipt.json, falsifiers.json). The run of the build, at e76e97b4, gave the
same 19 of 19, with the same rows red under each mutant.

The eleven declared falsifiers, each red on a row of its own:

| AC | Falsifier | Row turned red |
| :- | :- | :- |
| AC1 | ignored paths left out of case 3 | ac1/loose-ignored-file, ac1/personal-rule, ac1/untraced-rule |
| AC2 | look beneath worktrees and agent repositories only | ac2/unpushed-commit, ac2/build-output |
| AC2 | the logs left out | ac2/log-only-commit |
| AC2 | a remote-tracking ref taken at its word | ac2/hand-written-ref |
| AC3 | a clone removed with no keep step | ac3/keep-first |
| AC3 | a worker clone removed without the snapshot | ac3/worker-clone-saved |
| AC3 | a worker clone's files deleted without the comparison | ac3/changed-after-snapshot |
| AC3 | the folder left under its marked name at that stop | ac3/renamed-back |
| AC4 | the digest of the first measurement used | ac4/changed-after-measure |
| AC5 | look beneath the item only | ac5/own-folder-holds |
| AC5 | an item with no form given the clone's row | ac5/no-form |

Eight guards beside them: any traced rule taken for build output; the remover taking any repository in
the folder with no last look; a clone with files deferred and nobody asked; the Ledger taking a
worktree's terms for a clone; any item with the form taken for a worker clone; an evidence file written
while it was read; the trunk guessed; the registry giving an item with no form the clone's row.

How each is red, said plainly. For AC1, the look beneath scratch, the worker clone without its snapshot
and AC5's own-folder look, a later guard still keeps the work in place under the mutant (the remover's own
last look, or its refusal of any repository in a folder): the row is red because the rule that must
refuse did not, and not because work was lost. For the logs, the remote-tracking ref, the missing keep
step, the missing comparison, the remover with no last look and the evidence digest, the mutant does lose the row's work and the row
finds it gone. Four mutants make a row raise, and the rows after it are red with it, never absent. The
store keeps no digest at a measurement, so the AC4 mutant stands in for one: it remembers the digest of
the first time the remover read the file.

## Fix round

After the build 118 accepted rows were red. The lead's triage found every one a pin of behaviour AC1 or
AC5 replaces and none a regression, and the lead widened the footprint row by row. No production file
changed in the fix round. Rows fixed, per suite (checks.json, rows.json):

- 135_veldo_0298: 95 rows (92 cell rows, two AC4 rows, kinds/ledger-accepts). The fixture items are
  declared under table 1 by its number; the AC4 fixture's own table takes the next unused number;
  ledger-accepts expects the current version and the form names. 143 green.
- 138_veldo_0300: work/worktree-second-probe, work/repository-in-a-folder, work/adopted-build-output; and
  one statement added to work/probes-through-the-boundary. 39 green.
- 139_veldo_0301: ac5/keep-failed-passed-through, its cause now a kept ref that cannot be written. 17
  green, and ac4/no-clock red as on the base.
- 140_veldo_0345: 19 rows were red, two causes and a raise that emptied the rows after it. Seven rows
  now drive the keep step's snapshot with a worker clone of a run that has ended; ac6/removing-put-back
  writes its file after the keep step answered; ac5/kill-points reds its own row on a missing folder.
  31 green.

The table ruling stands: table 2 is kept. The reason is in the spec History.

The keep step of VELDO-0345 still runs in every row it ran in (keep-step-0345.json). Counted on an
exported copy of the base and of the changed suite, row by row: the same number of keep step calls, of
calls that answered ok and of snapshots written, in all 31 rows; kept refs written are as many or more.
Of the 19 rows that were red, 13 call the keep step and 6 never did. The teeth of finding 345 on the
changed suite: 22 of 22 rejected.

Two defects of this ticket's build were found by running the teeth of the changed suites, and fixed:
the second last look added to the remover repeated the anchor line of the teeth case
space300-tips-not-read-again, so no case of finding 300 could run (the case now names the line before
it too); and under AC1 the case space300-probe-reads-outside-the-boundary was no longer rejected (the
row gains one statement). Finding 300 after both: 26 of 26. Finding 298: 6 of 6. The teeth of finding
301 cannot start: an anchor is missing from control_space_signal.py, on the base too; not changed.

Red and inherited, the same on an exported copy of the base: 0330 rules/write-nothing, 0301 ac4/no-clock,
0305 review/scratch-apart-from-run-directory, three rows of 0308, 0310 keep/kept-item-not-named. Of
these only 0301 was run again in the fix round.

Green in the fix round: the ticket suite, 0298 (135), 0299 (136), 0300 (138), 0303 (142), 0345 (140),
0343, 0318. Fast checks passed: validation, docs, template sync, lint, space boundary, git boundary.
Green neighbours of the build, not run again: 0327, 0297 (132), 0326 (133), 0312 (149), 0317.

## Not built, not run

- No Save and no Discard remover for a batch clone or a candidate workspace: no criterion asks for one,
  so the request offers Keep alone. A follow-up for the lead to file.
- No caller gives Signal the declared trunk yet (the callers are outside the footprint); until one does,
  evidence goes only on a copy in the store or on a kept ref.
- With no ledger there is no snapshot store: the standalone path leaves a worker clone with uncommitted
  files in place, as before.
- Not run: scripts/verify.sh and suites 151 and up, so the rows of 0302 (suite 153) and 0324 (suite 154)
  were not run, and neither was 156_veldo_0315_reconcile. They may pin the same things.
