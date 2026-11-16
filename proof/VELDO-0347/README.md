# VELDO-0347 proof

Implementation e422b65863a56b777edc9eea8777bd28d9aa9cbe (fix round 2, on the independent review of
25f56001; the first fix round was 1f8aaebb, the build f347196e), on base 7e457e85 (the blocker commit of the first run). Builder evidence, not
independent review. All five criteria remain pending the lead gate and independent review. No row of a
suite run in this round is red; suites 151 and up were not run. Read "Fix round 2" first: it is the
state of the bundle. The sections before it are the record of the build and the first fix round.

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

## Fix round 2

On the independent review of 25f56001 (verdict FIX, no path that loses work). What changed, by finding.

Finding 1, the table ruling was not kept by the code. The clone's handling (rule 5 reading a clone's work
tree, the request, the worker clone's snapshot removal) was chosen by the item's form alone. It is now
chosen by the row the kind registry answers for the item from the table of the item's own version: rules
is given the row, Signal tells the remover the row only when it is agent_repository_clone, the remover
saves and compares a worker clone only when told, and the Ledger takes a clone's request only for an
item of the table it was given whose form that table names. Reconcile chooses no handling (it declares
through the Ledger and ends items through Signal) and did not change. Rows: ac3/table-1-clone (a batch
clone and a worker clone declared under table 1: no reading by rule 5, the remover refuses keep_failed,
no request, the Ledger refuses a clone's request, nothing in the snapshot store, every file in place; a
clean one is removed keep step first) and ac3/table-2-clone (the same two clones under table 2 at the
same event: the request, and the snapshot removal). Five teeth cases, one for each place that chooses
and one for the other side of Signal's hand-over. The request has no case of its own: it is raised only
on rule 5's word work_tree, said for the clone's row alone, so a row test there changes nothing.

Finding 3, the Ledger's Keep alone had no row. ac3/ledger-keep-only plants a settled Discard and a
settled Save of a requested clone in the store, past the settlement path, and the Ledger refuses each as
space_disposition_choice with the item unchanged; the same planted Discard of a worktree is taken. One
teeth case (the reviewer's M5), which left the suite green before and reds this row now.

Finding 4, the rows were not independent. Every row of the ticket suite runs under its own guard and
builds its own state, or asks for the fixture of its criterion (AC4). Measured by hand in a copy of the
tree: the reviewer's M2 reds six rows, all of AC2 (it reddened about twenty); M3 reds one row. In the
teeth run each of the 25 mutants reds rows of one criterion only, six rows at most.

The reviewer's question on AC4, evidence whose only copy is on the trunk. No criterion requires that
removal: AC4 says an evidence file is removed only when a copy is held. No caller of Signal passes the
declared trunk and every caller is outside the footprint, so such a file is kept: space is not freed
and no work is lost. The follow-up is named in the spec History for the lead.

Finding 2, the teeth of finding 301 (teeth-301.json). Two anchors had moved: VELDO-0334 (c638ab1f) had
removed the line of space301-returns-after-marking-due and VELDO-0318 (a9628b86) had moved the line of
space301-refused-item-not-deferred. Both cases name the code as it is and make the same defects. With
the anchors repaired the cases ran and none could be judged: the baseline held the inherited red row
ac4/no-clock, because VELDO-0317 (e8c903d4) had put an import and a read of the store in Signal's rule 5.
That read is now the Ledger's (no_space_ends); the line the 0317 teeth case changes is as it was. After
it: 0301 ac4/no-clock and 0330 rules/write-nothing are green, and finding 301 is 14 registered, 14
executed, 14 rejected.

Found by reading every teeth case of the changed modules against the code: five anchors this ticket's own
build had moved. space327-target-another-item is repaired and rejected (finding 327, 16 of 16). The
other four (space336-scratch-is-unique-work, space302-agent-form-refused,
space324-ledger-drops-ticket-end, space324-failed-keep-still-deletes) are repaired, each matches once
and each changed module parses, but their suites are 153 and 154: NOT SHOWN RED, for the lead to run.
space306-volumes-first anchors a line that was not on the base either and was not changed.

Runs, all on %s, the clean committed tree, nice -n 10 (checks.json, rows.json):

- Ticket suite: 30 rows green (AC1 4, AC2 8, AC3 10, AC4 4, AC5 3, canon).
- 135 (0298) 143, 136 (0299) 46, 138 (0300) 39, 139 (0301) 18, 140 (0345) 31, 142 (0303) 38, 0343 20,
  0318 45, 137 (0330) 23, 0317 23, 0327 27: all green.
- Fast checks passed: validation, docs, template sync, lint, space boundary, git boundary.
- Teeth, as checks, in this order: 317, 9 of 9; 327, 16 of 16; 345, 22 of 22; 300, 26 of 26. Then
  301, 14 of 14, and 347 last, 25 registered, 25 executed, 25 rejected (teeth-run.json,
  teeth-receipt.json, falsifiers.json). Nothing was written in the worktree while they ran; no process
  with the arguments space and supervise from this run was found after any run.

Not recounted: keep-step-0345.json is the count of the first fix round. Suite 140 changed in one line of
its fixture since (the row handed to the remover) and its 31 rows are green.

## Not built, not run

- No Save and no Discard remover for a batch clone or a candidate workspace: no criterion asks for one,
  so the request offers Keep alone. A follow-up for the lead to file.
- No caller gives Signal the declared trunk yet (the callers are outside the footprint); until one does,
  evidence goes only on a copy in the store or on a kept ref.
- With no ledger there is no snapshot store: the standalone path leaves a worker clone with uncommitted
  files in place, as before.
- Not run: scripts/verify.sh and suites 151 and up, so the rows of 0302 (suite 153) and 0324 (suite 154)
  were not run, and neither was 156_veldo_0315_reconcile. They may pin the same things, and the teeth of
  findings 336, 302 and 324 were not run.
- A clone declared under table 1 keeps table 1's handling for good: a dirty one stays, keep_failed, with
  no request, as before this ticket. The Ledger is given one table, so a table 3 must give it what it
  needs to go on asking about table 2 clones.
