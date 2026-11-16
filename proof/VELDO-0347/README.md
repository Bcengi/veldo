# VELDO-0347 proof

Implementation e76e97b493b481705fb575e5242a6645a6e25fc0, on base 7e457e85 (the blocker commit of the first run).
Builder evidence, not independent review. All five criteria remain pending the lead gate and independent
review. THE BUILD IS NOT GREEN AS A WHOLE: see "Still pinned and red" below.

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
7, AC4 4, AC5 3, and the canon row. Six rows of four accepted suites were updated as the lead decided
and one was added, all green (rows.json, other_suite; the spec History names each and why).

## Falsifiers and teeth

Finding 347: 19 registered, 19 executed, 19 rejected, no reuse, no invalid result, no surviving worker,
83 s. One run, last, on the clean committed tree; no mutant was applied by hand before it, so each
was applied once (teeth-run.json, teeth-receipt.json, falsifiers.json).

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

## Still pinned and red

Accepted rows outside the ones the lead named pin what AC1, AC5 and table 2 replace. They were not
changed (the decision says only those rows) and they are red. The spec History lists them for the lead:

- 135_veldo_0298: 95 rows. 92 cell rows assert version 1; two AC4 rows build a fixture table under the
  number 2; kinds/ledger-accepts asserts version 1 and the kinds only. All from issuing table 2.
- 138_veldo_0300: work/worktree-second-probe, work/adopted-build-output (AC1), work/repository-in-a-folder
  (AC5).
- 139_veldo_0301: ac5/keep-failed-passed-through (AC1). Not in the footprint.
- 140_veldo_0345: 19 rows, two causes (ac4/outside-git, ac5/failed-save-removes-nothing; AC1), the rest
  empty after a raise. Not in the footprint.

Red and inherited, the same on an exported copy of the base: 0330 rules/write-nothing, 0301 ac4/no-clock,
0305 review/scratch-apart-from-run-directory, three rows of 0308, 0310 keep/kept-item-not-named.

Green neighbours: 0299 (suite 136), 0303 (142), 0343, 0318, 0327, 0297 (132), 0326 (133), 0312 (149),
0317. Fast checks passed: validation, docs, template sync, lint, space boundary, git boundary.

## Not built, not run

- No Save and no Discard remover for a batch clone or a candidate workspace: no criterion asks for one,
  so the request offers Keep alone. A follow-up for the lead to file.
- No caller gives Signal the declared trunk yet (the callers are outside the footprint); until one does,
  evidence goes only on a copy in the store or on a kept ref.
- With no ledger there is no snapshot store: the standalone path leaves a worker clone with uncommitted
  files in place, as before.
- Not run: scripts/verify.sh and suites 151 and up, so the rows of 0302 (suite 153) and 0324 (suite 154)
  were not run, and neither was 156_veldo_0315_reconcile. They may pin the same things.
