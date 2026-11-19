---
schema: veldo.spec/v1
id: VELDO-0347
title: "Work the first rules did not see: ignored files, repositories in any folder, evidence"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0302, VELDO-0303, VELDO-0305, VELDO-0324, VELDO-0345]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space_probe.py"
  - ".veldo/control_space_probe.py"
  - "engine/.veldo/control_space_signal.py"
  - ".veldo/control_space_signal.py"
  - "engine/.veldo/control_space_remove.py"
  - ".veldo/control_space_remove.py"
  - "engine/.veldo/control_space_kinds.py"
  - ".veldo/control_space_kinds.py"
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "engine/.veldo/control_clone.py"
  - ".veldo/control_clone.py"
  - "engine/.veldo/control_batch.py"
  - ".veldo/control_batch.py"
  - "engine/.veldo/lander.py"
  - ".veldo/lander.py"
  - "engine/.veldo/control_launch_work.py"
  - ".veldo/control_launch_work.py"
  - "engine/.veldo/control_request_settlement.py"
  - ".veldo/control_request_settlement.py"
  - "scripts/suites/*_veldo_0347_*.py"
  - "scripts/suites/135_veldo_0298_space_kinds.py"
  - "scripts/suites/136_veldo_0299_space_probe.py"
  - "scripts/suites/138_veldo_0300_space_remove.py"
  - "scripts/suites/139_veldo_0301_space_signal.py"
  - "scripts/suites/140_veldo_0345_space_keep.py"
  - "scripts/suites/142_veldo_0303_space_paths.py"
  - "scripts/suites/134_veldo_0331_space_mode.py"
  - "scripts/suites/141_veldo_0344_process_reader.py"
  - "scripts/suites/143_veldo_0305_space_census.py"
  - "scripts/suites/144_veldo_0306_space_docker.py"
  - "scripts/suites/145_veldo_0307_space_docker_ownership.py"
  - "scripts/suites/146_veldo_0308_run_finished.py"
  - "scripts/suites/147_veldo_0310_landed_contained.py"
  - "scripts/suites/151_veldo_0313_space_run.py"
  - "scripts/suites/153_veldo_*.py"
  - "scripts/suites/154_veldo_*.py"
  - "scripts/suites/155_veldo_0304_space_boundary.py"
  - "scripts/suites/156_veldo_0315_reconcile.py"
  - "scripts/suites/support/space_owner_keep.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0347-work-the-first-rules-did-not-see-ignored-files-repositories-in-any-folder-evidence.md"
  - "specs/index.md"
  - "proof/VELDO-0347/**"
behavior_bearing: true
observability:
  logs: >
    A deferral names the ignored path and the rule that covers it or the fact that none could be traced,
    the repository found beneath a scratch or build output item and what in it is not pushed, or the
    evidence file whose copy was not found.
  error_taxonomy: >
    space_deferred:unique_work for an ignored file that is not build output and for a private repository
    whose work tree holds uncommitted work; space_deferred:in_use, by children, for a repository beneath a
    scratch or build output item, and for an item of another kind whose own folder is a repository;
    space_deferred:keep_failed for a worker clone's file that changed after its snapshot.
acceptance_criteria:
  - id: AC1
    text: >
      Rule 5 refuses a worktree that holds an ignored file which is not build output: a loose ignored file
      outside every build output folder, and a path only a personal ignore rule covers. A path whose rule
      cannot be traced is counted the same way
    falsified_by: >
      Leave ignored paths out of case 3; the row's local settings file goes with git's non-forced remove
      and the row fails
  - id: AC2
    text: >
      A git repository beneath a scratch item or a build output item holds it, as unrecorded, unless it is
      a clean clone: no uncommitted and no untracked file, no stash, every ref and its HEAD held by one of
      its own remote-tracking refs, no log entry whose commit those refs do not reach, and, for a remote
      that is a path on this host, each of those commits present in that repository now. One that cannot
      be read, one whose local remote cannot be read, and a folder that cannot be listed, hold the item
    falsified_by: >
      Each of these turns a row of its own red. Look beneath worktrees and agent repositories only: the
      row's clone with an unpushed commit in a session's scratch is deleted. Leave the logs out: the row's
      clone whose only unpushed commit a reset left in its HEAD log is deleted. Take a remote-tracking ref
      at its word: the row writes one by hand for a commit its local remote does not hold, and the clone
      is deleted
  - id: AC3
    text: >
      A worker clone, a batch clone and a candidate workspace are items of the kind agent repository with
      their form, never scratch, and are removed as private repositories: the keep step records every
      commit in the main repository first. A batch clone or a candidate workspace whose work tree holds an
      uncommitted or untracked file that is work is deferred as unique work and raises one request on the
      space disposition touchpoint, as a worktree does. A worker clone of a run that has ended is not
      deferred for such files: they are saved in the snapshot store, each file is compared with the
      manifest immediately before it is deleted, and the clone is removed with no request. When that
      comparison stops the removal, the folder remover renames the folder back to its locator before the
      item is deferred, so the item keeps its id, the next attempt saves what is left, and reconcile does
      not mark it gone
    falsified_by: >
      Each of these turns a row of its own red. Remove a clone by the folder remover alone: the row's
      commit that the runner never brought across is in no repository. Remove a worker clone without the
      snapshot: the row's uncommitted file is neither in place nor restored. Delete a worker clone's files
      without the comparison: the row rewrites a file after the snapshot, and finds the new content
      neither in place nor in the snapshot. Leave the folder under its marked name at that stop: the row
      runs reconcile, and finds the item marked gone and the rewritten file in a folder no item names
  - id: AC4
    text: >
      An evidence file is removed only when its digest, read again at the removal, is the digest of a blob
      the store holds or of a file in a commit the trunk or a kept ref reaches; a store or a commit that
      cannot be read is no copy
    falsified_by: >
      Use the digest recorded at the last measurement; the row changes the file after it was measured,
      finds the changed file gone and fails
  - id: AC5
    text: >
      The look of rule 6 starts at the item's own folder: an item whose folder is a git repository and
      whose kind is neither worktree nor agent repository holds itself, as unrecorded. The kind registry
      has a row for an agent repository item whose form is a worker clone, a batch clone or a candidate
      workspace, which ends at the events its creator sends; an item with no form ends only on the agent
      repository's own events
    falsified_by: >
      Each of these turns a row of its own red. Look beneath the item only: the row's scratch item whose
      own folder is a repository with an unpushed commit is deleted. Give an item with no form the clone's
      row: the row's agent repository with its worktree still in place is made due at run finished
required_evidence: [unit, integration]
rollback: >
  Revert the change. Ignored files are then no longer read by rule 5, a repository beneath scratch or
  build output no longer holds it, and clones are removed by the folder remover alone, as before this
  ticket.
---

## Intent

Four places where the first design could remove work without seeing it are closed: an ignored file that is
not build output, a git repository beneath a scratch or build output folder, a clone removed as scratch,
and an evidence file removed on a digest read earlier.

## Design

This is one of the four tickets added to VELDO-0295 for the owner's rule that no work is ever lost
(Telegram 41209: "It's very important no work is ever lost. Space management needs to ensure this very
clearly"). The design is docs/design/VELDO-0295-design.md, and the rule is its section 0. Design sections
this ticket builds: 0.1 (what work is, the two changes it names), 0.4 (evidence), 0.6 (the fail-closed
table) and the census step of 6.3. Section 12 of the design holds the ticket itself; its acceptance
criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Probes, Signal (rules 5 and 6), Removers, Kind registry (one row), Ledger (the form of an
> agent repository item), Clone provisioner, Batch, Landing line. Depends on 0302, 0303, 0305, 0324 and
> 0345. It builds section 0.1 and 0.4 where they go past what VELDO-0299 and VELDO-0330 built.

Build order. It is built after the creators and the census it corrects (0302, 0303, 0305, 0324) and before
0304. depends_on holds the dependencies the design states for this ticket.

VELDO-0299 and VELDO-0330 are built and have proof bundles, so their criteria are not edited; this ticket
carries what the rule adds to their modules. Measured on this repository's 79 worktrees on 2026-11-13: two
hold a loose ignored file, and 76 hold ignored folders that the committed ignore file covers.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-19: V1 preparation, the teeth of every finding whose suite the suite repair below changed
  and that were not yet run: 304, 305, 306, 307, 308, 309, 310, 313, 315, 328, 331, 337 and 341, each
  whole, alone, on the clean committed tree (proof/VELDO-0347/teeth-v1b.json). No rule, remover or
  Ledger file changed, and no statement of any row was taken out or loosened.
  - Lead decision, footprint: the product line of the entry below that was outside the footprint
    (init_scaffold.py, both copies, lists control_space_admission.py, 87fce757, which 153_0323
    compatibility/installed-closure needs) is accepted. It is a lead-authorized widening of the
    footprint of 2026-11-19; the two files are in the footprint list above.
  - Two anchors of the teeth registry that other tickets had moved, so that neither finding could
    start: space306-volumes-first (the order of removal gained the review kinds in the VELDO-0337
    fix, 8f99aeaa; fix round 2 had seen it and left it) and
    space308-exit-without-releasing-the-hold (VELDO-0316, aa1c5560, gave the release its run). Each
    names its line as it is now and makes the same defect; each is rejected by its row.
  - Two cases of finding 308 survived, both on row 146 ac4/pins-held-while-deferred:
    space308-pins-released-at-hand-over and space308-pins-released-while-the-item-is-not-removed.
    Not caused by this ticket and not by the suite repair: since VELDO-0304 (fb5d0f89) a pin is
    released through the ref remover, which refuses a pin whose item has not ended, so a release
    asked for too early leaves the pin where it is and the row, which read only that the pin is
    held, stayed green. The suite had three red rows until the repair, so nobody could see it. The
    row keeps every statement and gains two: after the hand-over and the sweeps, and again after
    the sweep over a work tree that is not at its path, the provisioner holds no answer for the pin
    and the retirement observed no release, so nobody asked. Both cases, unchanged, now red the
    row. This is a statement about a deletion: one was added, none weakened.
  - The other twelve findings rejected every case on the first run. With the four of the entry
    below (336, 324, 302, 323) all seventeen findings of the changed suites are whole.
  - For the join of V1: scripts/suites/153_veldo_0336_run_worktree.py is taken from
    veldo-space-0319 (lead decision), which repairs the same two rows on top of VELDO-0340.

- 2026-11-18: suite repair for landing batch V1 (space stack 2: 0343, 0347, 0319), on the lead's
  decisions after the fix check of 837fa81a (fixcheck-veldo-0347.md). For this round the lead widened the
  footprint to suites 134, 141, 143, 144, 145, 146, 147, 151, 153_*, 154, 155 and 156 with their fixtures
  and support modules. No rule, remover or Ledger file changed. No assertion that guards the owner's
  authority or a deletion was weakened: every row that marked Keep the old way now also requires the
  Ledger's refusal of it.
  - Superseded by AC2 of this ticket: scripts/suites/154_veldo_0324_batch_sandbox.py row ac2/recorded
    pinned that a run's scratch holding a mode 0 folder is removed with its parent. AC2 holds an item
    with a folder that cannot be listed as unread. The row keeps its point with folders shut against
    writing that the reader can list, which are removed; new row ac2/unlistable-held: the mode 0 folder
    holds the scratch and its parent, deferred by rule 6 as unread, and what is in it is whole.
  - Left stale by VELDO-0318 (a9628b86: the owner's Keep is the signed space_disposition command and
    nothing else): the fixtures of 0302, 0323, 0328, 0336, 0337, 0341, 0324 and 0315, and the same
    kind in 0308 (suite 146, three rows), 0310 (147 keep/kept-item-not-named), 0309 (153
    suite/completed) and 0313 (151 ac1/only-the-runs-own-items). The owner's desk VELDO-0343 fix 3
    built inside suite 156 moved, unchanged in what it does, to
    scripts/suites/support/space_owner_keep.py, and every one of these calls it: the whole production
    path (request, settled answer, the owner's packet) for a worktree or a clone its table gives a
    request, and the owner's packet over a planted request for a kind the Ledger raises no request
    for, as VELDO-0318 did for suites 149 and 154_0335. Suites 153_0302 and 153_0323, which stopped at
    that Keep, run whole.
  - Fixtures other tickets left behind, each repaired where it broke: 134 (VELDO-0315's item lock
    opens the state root, which the fixture never made: 14 rows); 143
    review/scratch-apart-from-run-directory (since VELDO-0302 the receiver declares the run directory
    for the owner its contract names; the row's contract had none); 144 ac4/poll-set (VELDO-0323 put
    the space spool's listener in the service's poll set); 145 ownership/removes-nothing (VELDO-0329
    put the hook installer in the reconciler's file; the row passes exactly its one delete of the
    file it made itself, and nothing more); 155 service/unique-work (since VELDO-0315 the shutdown
    block stops the space workers; the stand-in service had no such call). 156 ac3/startup was
    repaired by VELDO-0343 fix 3, which this branch is built on.
  - One product line outside that footprint, for the lead to confirm: init_scaffold.py (both copies)
    lists control_space_admission.py, which the service loads since VELDO-0316. Row 153_0323
    compatibility/installed-closure was hidden while its suite stopped on the owner's Keep, and is red
    without the line: an installed repository would lack a module its service loads. The same kind
    of line as 75f78d5f for control_space_docker.py.
  - Suite 151, the rows called timing rows: not stale rows and not timing. Outside the gate's
    confinement, on a host other sessions share, processes of other accounts that this account cannot
    read start after a run began and hold it, fail closed, as the wrapper must without the process
    reader; which rows go red follows that process table from run to run (5, 10 and 10 rows in three
    runs, different sets). In a process table of its own, as the gate's confined leg runs it, the
    suite is 63 passed, 0 failed, twice. Nothing in the suite was changed for this but the Keep row
    above. On a shared host it stays so until the owner pins the process reader.
  - Left as it is, known: 141 ac6/installed, refused:no_pin. The owner pins the reader after landing.
  - The teeth of findings 336, 324 and 302, which fix round 2 could not run, now have green baselines
    and were run whole; the four anchors fix round 2 repaired each match and each red their rows. The
    counts are in proof/VELDO-0347/teeth-v1.json.
  - Found by that run, superseded by AC2 of this ticket: teeth case space324-nested-repository-deleted
    (the remover's walk no longer stops at a repository) survived. Its row, 154
    safety/sandbox-repository, plants a repository beneath a launcher scratch; since AC2 the look
    beneath a scratch holds that item before the remover's walk is reached, in Signal and in the
    remover alike, so the row stayed green with the walk's stop taken out. The row keeps its
    statement and gains two: a launcher scratch that is a repository itself, which no look beneath it
    reads, is held by the rules, and the remover asked past the rules (as suite 138 asks it in
    work/repository-in-a-folder) refuses it, remove_refused, for the repository, with its commit and
    file whole. The case is unchanged and reds the row.
  - The same line of the remover has one more case, space323-session-repository-deleted, and it
    survived for the same kind of reason: its row, 153_0323 safety/session-work-kept, plants a session
    scratch that is a repository, which rule 6 holds since AC5 before the remover is reached. The row
    keeps its statement and gains the remover asked past the rules, which refuses it for the
    repository with its commit and file whole. The case is unchanged and reds the row; finding 323
    was run whole for it.

- 2026-11-16: fix round 2, on the independent review of 25f56001 (review-veldo-0347.md, verdict FIX, no
  path that loses work). Four findings, each fixed or decided, and two defects found on the way.
  - Finding 1, the table ruling was not kept by the code. Signal's rule 5, Signal's hand-over to the
    remover and the remover chose the clone's handling by the item's form alone, and the Ledger took a
    clone's request by the form alone, so an item with a clone form that was declared under table 1
    was judged by table 2. Now each is chosen by the row the kind registry answers for the item from
    the table of the item's own version: rule 5 reads a clone's work tree only when that row is
    agent_repository_clone (rules is given the row); Signal tells the remover the row only then, and
    the remover saves and compares a worker clone only when told; the Ledger takes a clone's request
    only for an item whose version is the version of the table it was given and whose form that
    table names. A clone declared under table 1 is judged, asked about and removed as before this
    ticket: no reading of its work tree by rule 5, no request, and a dirty one is refused by the
    remover, keep_failed, in place. The request needs no test of its own: it is raised only on rule
    5's word work_tree, which rule 5 says for the clone's row alone (a mutant that adds or drops a
    row test there changes nothing, so none is written). Reconcile chooses no handling: it declares
    through the Ledger and ends items through Signal, and was not changed (it is outside the
    footprint). The Ledger is given one table, so of an item of any other version it reads no
    clone's row; whoever issues a table 3 gives the Ledger what it needs for table 2 items. Rows:
    ac3/table-1-clone and ac3/table-2-clone, the same two clones at the same event under each table.
  - Finding 3, the Ledger's own refusal of a settled Save or Discard of a clone had no row. Row
    ac3/ledger-keep-only plants the settled answer in the store, past the settlement path that would
    refuse to write it, and expects space_disposition_choice with the item unchanged; the same
    planted Discard of a worktree is taken, which shows the refusal is the guard's.
  - Finding 4, the rows of the ticket suite were not independent. Every row now runs under its own
    guard and builds its own state, or asks for the fixture of its criterion (AC4's copies), so a
    row that raises is red with what was raised and the rows after it run. Measured with the
    reviewer's mutants: the look beneath scratch left out reds six rows, all of AC2, where it reddened
    about twenty; the logs left out reds one row.
  - Trunk-only evidence (the reviewer's note on AC4). No criterion requires a removal: AC4 says an
    evidence file is removed ONLY when a copy is held, and names the trunk as one place a copy may
    be. No caller of Signal passes the declared trunk (control_space_worker.py, control_service.py,
    dispatch.py, control_space_reconcile.py and scripts/gate_space.py, all outside the footprint), so
    a file whose only copy is in a commit of the trunk is KEPT. That is the safe direction: space is
    not freed, no work is lost. Follow-up for the lead to file: pass trunk(repository) to Signal from
    the callers that know the declared trunk, with a row of its own in the caller's suite; the
    remover already takes it (ac4/held-files-go, ac4/unreadable-is-no-copy, ac4/trunk-never-guessed).
  - Finding 2, the teeth of finding 301 could not start. This repairs VELDO-0334's anchor: its commit
    c638ab1f replaced the line "... if carried else []" of control_space_signal.py with a loop over
    the due items grouped by ending event and left the teeth case space301-returns-after-marking-due
    as it was. The case now changes "if selected:" of that loop to "if False:", the same defect (the
    call returns after marking due and removes nothing), and reds ac1/removes-before-return. Found
    with it, the same kind: the anchor of space301-refused-item-not-deferred was moved by VELDO-0318
    (a9628b86, the written deferral is kept in a name); repaired on the same write.
  - Found on the way, a defect of VELDO-0317 (e8c903d4) in a file of this footprint: rule 5 imported
    json and read the store itself, so 0301 ac4/no-clock and 0330 rules/write-nothing ("Signal imports
    nothing") were red on every base since, and with a red baseline no teeth case of finding 301 can
    be judged. The read is now the Ledger's (no_space_ends) and rule 5 asks for it; the line the teeth
    case space317-remove-failed-worktree changes is as it was and still reds its rows. Both rows are
    green; suite 0317 is green.
  - scripts/suites/140_veldo_0345_space_keep.py: the fixture's own call of the remover (the attempt
    that stands in for the next event) names the registry row of the item, as Signal does. Nothing a
    row asserts changed.
  - Five more anchors, moved by this ticket's own build (each matched once on the base 0a80f89b and
    matched nothing at 25f56001), found by reading every teeth case of the changed modules against
    the code: space336-scratch-is-unique-work (AC1 added a clause to the condition it changes),
    space302-agent-form-refused (the forms were given a name), space324-ledger-drops-ticket-end (the
    form picks the events) and space324-failed-keep-still-deletes (the worker clone's branch follows
    the two lines it names). Each case now names its line as it is and makes the same defect; each
    anchor matches once and each changed module still parses. NOT SHOWN RED: their suites are 153
    and 154, which this round must not run, so the teeth of findings 336, 302 and 324 are for the
    lead to run. A fifth, the same kind, whose suite this round may run:
    space327-target-another-item (the terms name a worktree or a clone through space_target); it
    names its line as it is, and its mutant reds space327/fix3/target-item. For the lead as well,
    not changed: space306-volumes-first anchors a line of
    control_space_kinds.py that was not on the base either (the ORDER line, changed by VELDO-0337).

- 2026-11-16: fix round, on the lead's decisions after the triage of the red accepted rows
  (triage-veldo-0347-reds.md: every red row pinned behaviour AC1 or AC5 replaces, none was a regression).
  No production file changed in this round; only rows of accepted suites, each with a History line in its
  own suite that names the row and the criterion that supersedes it.
  - The table ruling stands: table 2 is kept and table 1 gains no row. Adding the clone's row to table 1
    would change how items already declared under table 1 are judged: since VELDO-0302 the batch, the
    launch, the landing line, the clone provisioner and reconcile adoption declare agent repositories
    with a form under table 1, and the form would route those items to the new row, with another
    requires and another handling of unique work. That breaks "decided under table N, judged by table
    N". VELDO-0337 is not a precedent: it added rows for two new kinds that no existing item could read,
    so no judgment changed.
  - The footprint is widened, row by row, to the suites the triage names; it gains
    scripts/suites/139_veldo_0301_space_signal.py and scripts/suites/140_veldo_0345_space_keep.py.
  - scripts/suites/135_veldo_0298_space_kinds.py, superseded by AC5 (table 2 is current): the 92 rows
    ac1/<row>/<event> declare their fixture item under table 1 by its number and still prove the table
    of design section 5 at version 1; ac4/keeps-its-version and ac4/action-of-its-version file the
    fixture's second table under the next number no table has; kinds/ledger-accepts expects the current
    version and the names <kind>:<form>.
  - scripts/suites/138_veldo_0300_space_remove.py: work/worktree-second-probe, superseded by AC1 (it
    plants build output rule 5 lets through where it planted a loose ignored file; in_use as before);
    work/repository-in-a-folder, superseded by AC5 (rule 6 holds a scratch folder that is a repository,
    as unrecorded; the remover asked past the rules refuses as before) and, for its two statements on a
    repository deep inside a scratch folder, by AC2 (the remover's last look defers in_use where any
    repository was remove_refused; the folder is whole). These two statements were not in the triage:
    the row's first failure hid them. work/adopted-build-output, superseded by AC1 (rule 5 refuses and
    names build/ with its rule; the remover asked past the rules refuses keep_failed as before; a
    snapshot alone does not pass rule 5, and by the rules of a settled answer the worktree goes).
  - scripts/suites/139_veldo_0301_space_signal.py, ac5/keep-failed-passed-through, superseded by AC1: its
    cause was a file only info/exclude ignores, which rule 5 now refuses; the cause is now a kept ref
    that cannot be written, which rule 5 lets through. Signal still writes the remover's keep_failed as
    keep_failed.
  - scripts/suites/140_veldo_0345_space_keep.py, superseded by AC1: the rows that drove the keep step's
    snapshot with a worktree holding a loose ignored file (ac4/outside-git, and with it the snapshot
    ac4/store-protected reads; ac5/failed-save-removes-nothing; ac5/kill-points; ac5/retry-compares;
    ac5/folders-synced; ac4/modes-kept) drive it with a worker clone of a run that has ended, which
    production still saves and removes with no answer by the same keep step. ac6/removing-put-back
    writes its file after the keep step answered. ac4/modes-kept and ac6/removing-put-back were not in
    the triage: the raise in ac5/kill-points hid them. ac5/kill-points now reds its own row when a
    folder of the store is not there. The suite hands the remover the keeper module it loaded, the same
    file, so the failing disk and the kill seams it plants are in the keep step that runs. Measured row
    by row on the base (7e457e85) and after: the same number of keep step calls, of calls that answered
    ok and of snapshots written in every row, and as many kept refs written or more (a clone keeps
    every ref it has); proof/VELDO-0347/keep-step-0345.json.
  - Two defects of this ticket's own build, found by running the teeth of the suites whose rows changed,
    and fixed. The second last look this ticket added to the remover repeats a line that the teeth case
    space300-tips-not-read-again used as its anchor, so the anchor matched twice and none of the 26 cases
    of finding 300 could run; the case now names the line before it too
    (scripts/check_teeth_mutations.py). And with AC1 the case space300-probe-reads-outside-the-boundary
    was no longer rejected: rule 5 refuses a file a personal rule ignores as well, so
    work/probes-through-the-boundary in suite 138 stayed green; the row gains one statement, that no
    ignore rule is named for the file. Teeth after both: finding 300, 26 of 26 rejected; finding 345, 22
    of 22; finding 298, 6 of 6.
  - Still red and inherited, the same on the base: 0301 ac4/no-clock. The teeth of finding 301 cannot
    start: the anchor of space301-returns-after-marking-due is not in control_space_signal.py, and was
    not on the base (7e457e85) either; not changed here. Suites 151 and up were not run.

- 2026-11-16: built, on the lead's three decisions for the blocker below. All five criteria are built and
  the ticket suite has 27 green rows. The build is NOT green as a whole: accepted rows the decisions do not
  name pin what AC1, AC5 and table 2 replace, they were left as they are, and they are red (listed last).
  The decisions, and what was done under each:
  - Decision 1, the footprint is extended to four accepted suites, for the rows named and no other. Each
    row now asserts the new behaviour:
    - scripts/suites/135_veldo_0298_space_kinds.py, ac1/whole-table: superseded by AC5. It read the
      current table; it now reads table 1 by its number, so it says that table 1 stays exactly the
      fourteen rows it was issued with. A new row beside it, ac1/table-2, asserts table 2.
    - scripts/suites/136_veldo_0299_space_probe.py, ac2/case-3-untracked: superseded by AC1. It said a
      file git ignores is not unique work; it now says a loose ignored file is, case 3, named with the
      rule that covers it.
    - scripts/suites/138_veldo_0300_space_remove.py, work/ignored-files (the row with notes-private.md
      and settings.local): superseded by AC1. It said rules 1 to 6 pass and the remover refuses; rule 5
      now refuses first, as unique work, naming the two files. The remover's own refusals in that row
      are asked of the remover directly, past the rules, and are as they were.
    - scripts/suites/142_veldo_0303_space_paths.py, ac2/uncommitted-stays: superseded by AC3. An ended
      worker clone with an uncommitted file was deferred keep_failed and its teardown refused; the file
      is now saved in the snapshot store, the clone removed with no request, and the teardown goes
      through. And ac4/candidate-with-work-stays: superseded by AC3. A candidate workspace with an
      unsaved file was deferred keep_failed; it is now deferred as unique work and one request is raised
      that names it as a clone. For these two rows the fixture declares the item with its form, as the
      creators do, and the fixture's remover stand-in passes on the two functions Signal asks of the
      removers for a clone's request.
  - Decision 2, table 2 is issued. Neither the registry nor the design has a line that allows a row to be
    added to an issued table: the registry says "A table is never edited once issued: a change is a new
    version beside the old one", and design section 5 and 0.8 say only that "the table gains one row".
    So table 1 is byte for byte as it was (a row of the ticket suite pins its digest), table 2 is table 1
    and the row agent_repository_clone, and table 2 is the table a new item is declared under. The form
    picks the row and the events: an item with no form, or with the form agent, reads the agent
    repository's own row.
  - Decision 3, a clone's request names a clone. The footprint is extended to
    control_request_settlement.py and its synced copy. Terms with the field clones (and no worktrees)
    are a clone's: the item, its path, its form and the files in no commit. A clone is never listed as a
    worktree, and the Ledger refuses a worktree's terms for a clone and a clone's for a worktree. No
    criterion asks for a remover that carries a Save or a Discard of a private repository, so a clone's
    request offers Keep and nothing else, its terms say that nothing is removed, and the Ledger refuses
    any other settled choice for a clone. Worktree and group terms are unchanged.
  Follow-ups for the lead to file, none built here:
  - A Save and a Discard remover for a batch clone and a candidate workspace. Until one exists such a
    clone with files in no commit stays, deferred, with its request, and no work is lost.
  - Nothing in the footprint gives Signal the declared trunk: the callers of Signal are outside it. The
    evidence remover takes trunk(repository) and never guesses, so until a caller passes it, a file is
    removed only on a copy in the store or in a commit a kept ref reaches. That errs toward keeping.
  - With no ledger (the standalone remover) there is no snapshot store, so a worker clone with
    uncommitted files still stays, keep_failed, as before this ticket.
  Read as built, and worth a reviewer's eye: "a blob the store holds" is read as a row of the store's
  entities whose digest is the file's and whose own content, encoded again, has that digest; the store
  has no other blob table. The clone provisioner, the batch and the landing line already declare their
  repositories with the form (VELDO-0302), so those four files of the footprint did not change. A defect
  of the stopped run was found by the ticket's rows and fixed: the evidence remover asked git to hash a
  file through a descriptor path the git process cannot see, so no copy in a commit was ever found.
  STILL PINNED AND RED, not changed, because the lead's decision names other rows: for the lead to decide
  (extend the footprint row by row, as for the four above, or amend).
  - scripts/suites/135_veldo_0298_space_kinds.py: 92 rows ac1/<row>/<event>, one per cell of the table,
    each assert that the item reads version 1; ac4/keeps-its-version and ac4/action-of-its-version build
    their fixture's second table under the number 2, which is now taken; kinds/ledger-accepts asserts
    that LIFECYCLE names version 1 and holds the kinds and nothing else. All follow from decision 2: with
    table 2 current, a new item carries version 2. Every cell these rows read is unchanged.
  - scripts/suites/138_veldo_0300_space_remove.py: work/worktree-second-probe (its worktree holds an
    ignored settings.local so that the remover is reached; rule 5 now refuses first, AC1),
    work/repository-in-a-folder (a scratch folder that is a repository: "rules 1 to 6 pass and the
    remover refuses"; rule 6 now holds it, AC5) and work/adopted-build-output (an adopted worktree with a
    committed-ignore folder: the remover refused keep_failed; rule 5 now refuses first, AC1).
  - scripts/suites/139_veldo_0301_space_signal.py, ac5/keep-failed-passed-through: a worktree with a
    file only info/exclude ignores is deferred keep_failed by the remover; rule 5 now refuses first, AC1.
    This suite is not in the footprint at all.
  - scripts/suites/140_veldo_0345_space_keep.py, not in the footprint: ac4/outside-git ("a worktree whose
    only work is that ignored file is removed once the file is saved", at landed, with no owner's answer)
    and ac5/failed-save-removes-nothing (the same worktree, expected keep_failed from the remover). Under
    AC1 rule 5 refuses both first. The second raises in its fixture, and the 17 rows after it in that
    suite are then empty and red with it: 19 red rows, two causes.
  - Suites 151 and up were not run (the lead runs them): 153_veldo_0302, 154_veldo_0324, 156_veldo_0315
    and others may pin the same three things. Not known.

- 2026-11-16: build blocked by the declared footprint, on base 0a80f89b. No production change, no suite
  change and no AC amendment was made; nothing was built. Four accepted suites that the footprint does not
  name pin the behaviour AC1, AC3 and AC5 replace, so each of these rows turns red the moment the
  criterion is built, and no row of this ticket can be green beside it:
  - scripts/suites/135_veldo_0298_space_kinds.py, ac1/whole-table: the rows of the current table are
    exactly the fourteen it lists, and checked_lifecycle returns LIFECYCLE at version 1. AC5 adds a row
    for an agent repository with a form. A row kept outside the table's rows, so that this check does not
    see it, would be a workaround of the pin and was not written. To decide with it: the registry says a
    table is never edited once issued, and VELDO-0337 added its two rows to table 1.
  - scripts/suites/136_veldo_0299_space_probe.py, ac2/case-3-untracked: "an untracked file git ignores
    is not unique work", read on a loose ignored file. AC1 says it is. The row stays green only if the
    probe reads ignored paths when the rule asks and not by default, which leaves a default that sees
    less: the lead's call, not the builder's.
  - scripts/suites/138_veldo_0300_space_remove.py, the row with notes-private.md and settings.local:
    "rules 1 to 6 pass and the remover refuses, keep_failed", order 6. With AC1, rule 5 refuses first, as
    unique_work.
  - scripts/suites/142_veldo_0303_space_paths.py, ac2/uncommitted-stays: an ended worker clone with an
    uncommitted file is deferred keep_failed and its teardown refused. AC3 saves the file and removes the
    clone. And ac4/candidate-with-work-stays: a candidate workspace with an unsaved file is deferred
    keep_failed. AC3 defers it as unique_work and raises a request.
  Two more things outside the footprint, for the same decision. The request's signed terms are built by
  control_request_settlement.space_presentation, which names one worktree ("Worktree:", the Discard
  sentence, the restore command): a batch clone's or a candidate workspace's request would be shown as a
  worktree's. And no remover carries a Save or a Discard of a private repository; no criterion here asks
  for one, so a clone's request could be raised and answered but not carried out. Not blocked, read and
  ready to build: AC2 and AC4 touch no pinned row that was found, and the keeper's snapshot (VELDO-0345)
  already saves a private repository's work tree with no change. Asked of the lead: extend the footprint
  to the four suites (and say whether table 1 gains the row or a table 2 is issued), or amend the
  criteria.
- 2026-11-15: lead decision, the repository form field and its validation are delivered by VELDO-0302.

- 2026-11-13: written from design section 0, added that day for the owner's rule (Telegram 41209). The
  number follows VELDO-0344, the highest a spec file or a proof folder held on any ref or in any worktree;
  nothing on any ref named 0345 to 0349. Status ready.
- 2026-11-13: amended for the lead's answers to the six questions of design section 15 (section 13 records
  them). A snapshot of uncommitted, untracked or ignored files is stored outside git, in the snapshot
  store under the state root, and never in a repository's object store, so a secret in an ignored file
  does not enter git; commits stay on kept refs (design 0.3). AC3, from the lead's answer on worker
  clones: a worker clone of a run that has ended is not deferred for uncommitted or untracked files. They
  are saved in the snapshot store and the clone is removed with no request, as review scratch is. The
  answer names worker clones, so a batch clone and a candidate workspace still raise one request. AC3
  gains a second falsifier: a worker clone removed without the snapshot.
- 2026-11-13: amended from the validation of design section 0
  (design-veldo-nowork-0344r2-validation-2026-11-14.md, verdict CHANGES; design 14.7), under the owner's
  rule that no work is ever lost. N1: AC3 says a worker clone, a batch clone and a candidate workspace are
  items of the kind agent repository with their form, never scratch. There is no eleventh kind; the form
  picks a new row of the kind registry, because the agent repository's own row does nothing at run
  finished, the event a clone's teardown sends. New AC5: the look of rule 6 starts at the item's own
  folder, so an item of another kind that is itself a repository holds itself, and an item with no form
  ends only on the agent repository's events. The row for a batch clone that reconcile adopts is
  VELDO-0315 AC1, which is built after this ticket. N2.3: AC3 compares each file of a dead run's worker
  clone with the manifest just before it is deleted, with a third falsifier. N-R2: AC2's clean clone also
  has no log entry whose commit its remote-tracking refs do not reach, and for a remote that is a path on
  this host each commit is in that repository now; two more falsifiers. A remote on another host is a
  residual the design states in 0.9. The footprint gains the kind registry and the ledger. Four criteria
  became five.
- 2026-11-13: amended for the two points of the final check of design section 0 that the amendment before
  this one left out (design-veldo-nowork-r2-validation-2026-11-14.md, F3 and F4; design 14.8), by the
  lead's word that both are required under the owner's rule that no work is ever lost. F3: when the
  comparison with the manifest stopped a worker clone's removal, the folder stayed under the folder
  remover's marked name; the item then had nothing at its locator, reconcile marked it gone, and the file
  that was not saved sat in a folder no item names. AC3: on that stop the folder remover renames the
  folder back to its locator before the item is deferred, so the item keeps its id, the next attempt saves
  what is left, and reconcile does not mark it gone. AC3 gains a fourth falsifier: the folder left under
  its marked name. The reconcile side is VELDO-0315 AC2. Still five criteria.
- 2026-11-14: from the independent review of VELDO-0300 (findings 3 and 4). No acceptance criterion changed.
  Two things this ticket builds are now refused outright by the removers, so that nothing depends on
  the order the tickets land in, and this ticket opens them again where its criteria say so. The folder
  remover stops on any folder that is a git repository or holds one (an agent repository and a
  worktree hold their own and no other): the clean clone of design 0.1 is not excepted there, and the
  own-folder look of rule 6 is still this ticket's. The agent repository remover refuses, keep_failed,
  a repository whose work tree has any modified, staged or untracked entry or any ignored path that is
  work: a dead run's worker clone with a snapshot (AC3) needs the per-file comparison with the manifest
  before each delete, which this ticket adds to that remover together with the exception.
