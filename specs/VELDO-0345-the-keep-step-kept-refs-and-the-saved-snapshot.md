---
schema: veldo.spec/v1
id: VELDO-0345
title: "The keep step: kept refs and the saved snapshot"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0297, VELDO-0299, VELDO-0300, VELDO-0330]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space_keep.py"
  - ".veldo/control_space_keep.py"
  - "engine/.veldo/control_space_remove.py"
  - ".veldo/control_space_remove.py"
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "engine/.veldo/control_space_probe.py"
  - ".veldo/control_space_probe.py"
  - "engine/.veldo/control_space_signal.py"
  - ".veldo/control_space_signal.py"
  - "scripts/suites/*_veldo_0345_*.py"
  - "scripts/suites/132_veldo_0297_space_ledger.py"
  - "scripts/suites/133_veldo_0326_space_principals.py"
  - "scripts/suites/139_veldo_0301_space_signal.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0345-the-keep-step-kept-refs-and-the-saved-snapshot.md"
  - "specs/index.md"
  - "proof/VELDO-0345/**"
behavior_bearing: true
observability:
  logs: >
    The keep record on the item, one journal record: the main repository, each kept ref with its commit,
    the list of snapshot attempts, each with its path, its number, its size and its manifest digest, and
    the path the item had. Each kept ref's own log names the event that wrote it. A later write adds refs
    and attempts to the record and removes none.
  error_taxonomy: >
    space_deferred:keep_failed, with the ref and what git said, when a kept ref or a snapshot cannot be
    written or read back, when the fetch from a private repository fails, when the main repository is not
    at its path, and when a private repository names no main repository. For the snapshot: an unwritable
    store, a full pool, a short write, a read back that differs, a failed sync or rename, and an item that
    changed after it was saved. Nothing is removed in any of these cases.
acceptance_criteria:
  - id: AC1
    text: >
      Before git's worktree remove runs, the worktree's checked-out commit, each of its own refs, each
      commit an operation in progress names and each commit only its HEAD log names is on a kept ref under
      refs/veldo/kept/<ticket>/<item>/ in the main repository, read back, and listed on the item's keep
      record; the ledger refuses the outcome removed for a worktree or a private repository that has no
      keep record. For an agent's worktree the main repository is the shared repository: the commits are
      fetched from the agent repository and the kept refs are written there, and none is written in the
      agent repository
    falsified_by: >
      Each of these turns a row of its own red. Write the refs after the remove: the row kills the remover
      between the two and finds the commit the HEAD log named in no ref. Write an agent worktree's kept
      refs in its agent repository: the row removes the worktree and then the agent repository, and finds
      the worktree's kept head under its own item's name in no repository
  - id: AC2
    text: >
      Before a private repository is removed, every ref it has, every stash entry, its HEAD and each
      commit only a log names is fetched into the main repository under the item's kept refs, and
      afterwards each of those commits is read from the main repository alone
    falsified_by: >
      Fetch the branches only; the row's second stash entry is in no repository after the removal and the
      row fails
  - id: AC3
    text: >
      When a ref cannot be written, exists at another commit or reads back as another commit, when the
      fetch fails, when the main repository is not at its path any more, or when a private repository
      names no main repository, nothing is removed, by an event or by reconcile, and the item is deferred
      as keep_failed with the ref and git's words. A second attempt after a crash finds the refs it wrote
      and passes. Rule 5 does not count a kept ref as a ref that holds a commit
    falsified_by: >
      Each of these turns a row of its own red. Call the remover after a failed write: the row makes the
      main repository's refs unwritable, and finds the worktree gone and its commit unreachable. Go on
      when the main repository is gone: the row moves the main repository away, sends the ending event,
      runs reconcile, and finds the worktree gone
  - id: AC4
    text: >
      The saved snapshot is plain files with a manifest in the snapshot store under the state root,
      outside every repository: the tracked edits, the staged state and the untracked files, the ignored
      ones that are work included, each with its mode and its SHA-256. Writing it changes neither the
      worktree, nor its index, nor the repository's stash entries, and adds no object to any repository's
      object store. It is read back and compared before the keep record is written. The snapshot store is
      protected in every installation, and no rule lets a remover take a path in it
    falsified_by: >
      Each of these turns a row of its own red. Write it as a commit on a kept ref: the row plants a
      marker in an ignored settings file and finds the marker in an object of the main repository after
      the Discard. Write it with git's stash command: the row compares the worktree and the stash entries
      before and after, and finds the worktree emptied and an entry added. Leave the store off the protect
      list: the row declares a folder of the store as scratch, sends its ending event and finds the
      snapshot gone
  - id: AC5
    text: >
      A save that fails or stops half way removes nothing: when the store cannot be written, when its pool
      fills in the middle of a file, when a write is short, when a read back differs, when a sync or the
      rename fails, the item is deferred as keep_failed with everything in place, and what the attempt
      wrote stays under its temporary name. Each attempt writes a numbered folder of its own, <state
      root>/space-saved/<ticket>/<item>/<n>/, that is never replaced and never deleted; the keep record
      lists every attempt it was given, a later keep write for the item adds refs and attempts and removes
      none, and a folder no record lists and a temporary one are kept and counted. A retry uses the newest
      attempt the keep record lists when its manifest has the recorded digest and the item still equals
      it, and otherwise writes the next number and adds that attempt to the record. With the process
      killed inside the snapshot write, after the rename and before the keep record, and after the record
      and before the remover, the next attempt ends with the item removed once and its snapshot whole, or
      with the item in place; reconcile's part in that is VELDO-0315 AC2
    falsified_by: >
      Each of these turns a row of its own red. Go on after a short write: the row fills the store's pool
      in the middle of a file, and finds the worktree gone and the file in no place. Make room for a retry
      by deleting the existing snapshot folder: the row kills the remover between the delete and the
      rename and finds no copy of the file. Use the snapshot the record names without comparing: the row
      changes a file after the kill, and finds the new content neither in place nor restored. Keep only
      the newest attempt on the record: the row stops a review scratch removal after its first delete,
      retries, restores, and finds the first deleted file missing while restore said success
  - id: AC6
    text: >
      The ledger accepts the outcome deferred for a removing item with each of the three deferrals a
      remover names, remove_refused, in_use and keep_failed, records the one it was given, and refuses
      every other deferral and the outcome kept for a removing item as before. So an item whose remover
      put it back because it was in use, or because the last look found work the keep step did not
      save, is recorded as that and is not completed to the end by reconcile
    falsified_by: >
      Accept remove_refused alone, as control_space.TOOL_REFUSAL does today; the row writes the outcome
      deferred with keep_failed for a removing worktree that is back at its path with an unsaved file,
      finds the outcome refused and the item still removing, and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. Removers then run without the keep step, as before this ticket. Kept refs already
  written stay in their repositories and are still read by plain git.
---

## Intent

Before a worktree or a private repository is removed, every commit it reaches is recorded on a kept ref in
its main repository, and before a Discard, a review's scratch removal or the removal of a dead run's
worker clone the uncommitted state is saved as a snapshot outside git. When either write fails, nothing
is removed. This is the part of the owner's
rule, no work is ever lost, that every remover runs.

## Design

This is one of the four tickets added to VELDO-0295 for the owner's rule that no work is ever lost
(Telegram 41209: "It's very important no work is ever lost. Space management needs to ensure this very
clearly"). The design is docs/design/VELDO-0295-design.md, and the rule is its section 0. Design sections
this ticket builds: 0.2 (the kept refs, how they are written, the crash table) and 0.3 (the snapshot), the
keep step paragraph of section 7, the kept field of 4.1 and the keep command of 6.1. Section 12 of the
design holds the ticket itself; its acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Keeper, Removers, Ledger (the keep record). Depends on 0297, 0299, 0300 and 0330. It builds
> sections 0.2 and 0.3, and it adds the keep step inside the worktree remover and the private repository
> remover of 0300. Since the validation of section 0 it has five criteria: AC5 holds the snapshot's
> failure, crash and retry paths.

Build order. It is built straight after 0301 and before every ticket that removes a worktree or a private
repository on a real host. depends_on holds the dependencies the design states for this ticket.

Measured on git 2.43.0 on 2026-11-13, and to be repeated as rows: a commit left behind by a reset in a
detached worktree is named only by that worktree's HEAD log, and git's worktree remove takes the log; a
fetch by hash from a local path works when the call sets uploadpack.allowAnySHA1InWant for itself. The
third measurement of the first form, a commit built in git's stash layout, no longer applies: the
snapshot is not a commit (History).

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design section 0, added that day for the owner's rule (Telegram 41209). The
  number follows VELDO-0344, the highest a spec file or a proof folder held on any ref or in any worktree;
  nothing on any ref named 0345 to 0349. Status ready.
- 2026-11-13: amended for the lead's answers to the six questions of design section 15 (section 13 records
  them). A snapshot of uncommitted, untracked or ignored files is stored outside git, in the snapshot
  store under the state root, and never in a repository's object store, so a secret in an ignored file
  does not enter git; commits stay on kept refs (design 0.3). AC4 is rewritten: the snapshot is plain
  files with a manifest (each file's mode and SHA-256) in <state root>/space-saved/<ticket>/<item>/,
  written without adding an object to any repository, read back before the keep record is written, and the
  store is protected in every installation. The first form, a commit in git's stash layout on a saved ref,
  is withdrawn. AC4 has three falsifiers: the snapshot written as a commit (a marker planted in an ignored
  settings file is then found in the main repository's objects), the snapshot written with git's stash
  command, and the store left off the protect list. The keep record holds the snapshot's path, size and
  manifest digest. The same snapshot is written for a dead run's worker clone (VELDO-0347 AC3).
- 2026-11-13: amended from the validation of design section 0
  (design-veldo-nowork-0344r2-validation-2026-11-14.md, verdict CHANGES; design 14.7), under the owner's
  rule that no work is ever lost. N-R1: AC1 writes an agent worktree's kept refs in the shared repository,
  fetched from the agent repository, and none in the agent repository, which is removed later; written
  there they were carried across under another name and the worktree could not be restored. AC1 gains that
  falsifier. N-R3: AC3 refuses when the main repository is no longer at its path, by an event or by
  reconcile, with a falsifier. N2: new AC5 holds the snapshot's failure, crash and retry paths. A save
  that fails or stops half way removes nothing; each attempt writes a numbered folder, <state
  root>/space-saved/<ticket>/<item>/<n>/, never replaced and never deleted; the keep record names the one
  used; a retry uses it only when it still equals the item; the three kill points around the snapshot are
  rows. AC5 has three falsifiers: the remove after a short write, an existing folder deleted to make room,
  and the recorded snapshot used without comparing. AC4 is unchanged. Four criteria became five.
- 2026-11-13: amended from the final check of design section 0
  (design-veldo-nowork-r2-validation-2026-11-14.md, verdict CHANGES; design 14.8). F1: the keep record
  named one snapshot, and a retry wrote the record again. After a review scratch removal that had deleted
  one file and stopped at the next, the retry's snapshot replaced the first in the record, and a restore
  brought back only the second. AC5: the keep record lists every attempt it was given, and a later keep
  write for the item adds refs and attempts and removes none, also a write that saves nothing; a retry
  uses the newest listed attempt when it still equals the item, and otherwise adds the next number to the
  record. AC5 gains a fourth falsifier, the newest attempt alone on the record. Still five criteria.
- 2026-11-14: from the independent review of VELDO-0300 (findings 1 and 2). No acceptance criterion changed.
  The removers now hold the keep step to its answer, so the answer has a form this ticket must give:
  {ok: True, tips: ..., snapshot: ...}. tips is what control_space_remove.tips(path, kind) read in the
  item at the moment its commits were recorded; the keeper calls that one function, because the
  remover reads the same thing again under the marked name and refuses, keep_failed, on any difference
  (a commit made after the keep step). An answer with no tips is keep_failed. snapshot, when the step
  saved files, is {files: {path relative to the item: {mode: the st_mode, sha256}}}; the worktree
  remover refuses while any ignored file that is work is not in it with the same mode and digest.
- 2026-11-14: from the re-review of VELDO-0300 (review2-veldo-0300.md, finding D; the first review's
  finding 6). New AC6: the ledger's refusal of any deferral but remove_refused for a removing item
  (control_space.TOOL_REFUSAL) has to accept the three deferrals a remover names, remove_refused, in_use
  and keep_failed. It was a sentence in VELDO-0301's History and bound nobody; control_space.py is in
  this ticket's footprint. Signal's part, passing the remover's deferral through, is VELDO-0301 AC5.
  Until both are built a keep_failed or in_use refusal of a removing item is recorded as remove_refused.
  Five criteria became six. AC6 is not in section 12 of the design, whose text this change does not
  edit. Also from that re-review (finding B): the removers refuse, keep_failed, an agent repository
  that has any linked worktree, because the index of a linked worktree lives inside the repository's
  folder and nothing saves it. Removing such a repository needs a keep step that saves each linked
  worktree's index; until this ticket or a later one adds it, such a repository waits.
- 2026-11-14: built. No acceptance criterion changed. What the build decided, recorded here because
  a reviewer will meet each of them:
  - Footprint. On the lead's instruction this ticket also puts VELDO-0301 back at design 4.1, so
    control_space_signal.py (both copies) is added. Three older suites are added because this ticket
    changes what they assert: 132 (a removing item deferred as in_use was a refusal; AC6 accepts it),
    133 (its row sends every ledger command the observer may not sign, and keep is a new one) and 139
    (its keep step was a stand-in; since AC1 the ledger refuses the outcome removed for a worktree
    with no keep record, so the suite now runs the keeper itself, and its journal count holds the
    removing outcome). No check of those suites was removed.
  - Signal (design 4.1). When rules 1 to 6 have passed for an action that takes the item away, the
    outcome removing is written and only then is the remover called. A remover that refuses leaves
    the item deferred with its own deferral, which AC6 lets the ledger accept; a process killed inside
    the remover leaves the item removing. When the ledger refuses that write the remover is not
    called. The row is signal/removing-while-the-remover-runs in this ticket's suite and its
    falsifier is space345-due-while-the-remover-runs.
  - The ledger accepts the outcome removing for an item that is already removing only when the facts
    hold left_at, so Signal can still record where a thing was left (VELDO-0301 AC5). Every other
    second write of removing is refused as before.
  - The keep command is the ledger's own: neither host principal may sign it. It checks the refs, the
    repository and the manifest itself, inside its transaction, with git run through the one Git
    boundary. The main repository must be the one the declarations name for the item's scope.
  - A snapshot is written when the keeper is made with snapshot=True. The removals that ask for it
    (Discard, review scratch, a dead run's worker clone) are VELDO-0318, 0336 and 0347; no remover of
    this ticket forces a removal. Signal's plain removal asks for none, so a worktree with an ignored
    file that is work is still deferred as keep_failed by the remover's last look.
  - What reconcile asks before it completes a removing item is control_space_keep.verify; reconcile
    itself is VELDO-0315. The AC3 row that "runs reconcile" calls verify and makes the second attempt
    the way reconcile will: the remover with the keeper, on the removing item.
  - A kept ref is created and never moved (design 0.2). So an item whose head moved after an attempt
    that wrote its kept head and was then deferred is keep_failed at every later attempt, until the
    owner drops that item's kept refs (VELDO-0346). Nothing is lost by it, and it is the design's
    word, but it can leave a worktree waiting. A later ticket may want a numbered head.
  - How three falsifiers were applied. The agent worktree's refs written in its agent repository:
    the ledger's own check refuses that keep record, so the row goes red one step before the story
    the falsifier tells (the worktree is not removed at all). The snapshot as a commit on a kept ref:
    applied as the snapshot's files written into the main repository's object store, which is what
    the row detects (the marker in an object). A full pool and a kill are made inside the suite's own
    process: the keeper's write returns short or raises no space left, and a kill is an exception no
    handler catches, raised at the named point.
  - Found and left alone: the registered case space331-signal-reads-no-mode (VELDO-0331) has had no
    anchor in control_space_signal.py since VELDO-0301 rewrote that line. It is not this ticket's.
- 2026-11-14: every attempt writes its own kept refs (the lead's decision, from the builder's report
  above that a kept ref is never moved and so a worktree whose head moves after a deferred attempt
  stays keep_failed until its kept refs are dropped). No acceptance criterion's text changed. The name
  is now refs/veldo/kept/<ticket>/<item>/<attempt>/<what>, the attempt numbered from 1, which is
  still under the item's prefix as AC1 says. An attempt reads the item's refs: when the newest
  attempt already holds every ref it would write, each at the same commit, it writes nothing (AC3: a
  second attempt after a crash finds the refs it wrote and passes); in every other case it writes
  its whole set under the next number and touches no ref of an earlier attempt. This is the design's
  append-only rule (0.2: created and never moved; 0.3 says the same of a snapshot attempt). So a
  later attempt with a new head keeps and proceeds, and the head the item had before is still on its
  own ref. AC3's "exists at another commit" now reads on the attempt's own names: one that turns up
  at another commit between the read and the write is keep_failed and is not moved. The keep record
  lists the refs of every attempt (AC5: a later keep write adds refs and removes none), and verify
  reads them all. No ledger code changed. Row ac3/kept-ref-per-attempt; falsifier
  space345-attempt-takes-the-newest-names-again (the attempt takes the newest attempt's names
  again: the row finds the worktree keep_failed at its new head). The row ac3/ref-at-another-commit
  now plants the ref between the attempt's read and its write. The case space345-branches-only
  keeps its meaning and is anchored at the renamed call. VELDO-0346 reads these names (its History).
  Design sections 0.2 and 0.5 still show the name without the attempt; this change does not edit the
  design's text.
- 2026-11-14: from the independent review of this ticket (review-veldo-0345.md, verdict FIX, findings 1
  to 4), under the owner's rule that no work is ever lost. No acceptance criterion's text changed. Each
  finding has a row and a registered falsifier.
  - Finding 1, a stale keep record passed. The keep record now holds its attempt, {number, head}: the
    number of the keep attempt whose refs the last keep write named. The Ledger clears it when the
    item is marked due and when the outcome removing is written for a due item, and only a keep write
    sets it. The outcome removed is refused, space_keep_stale, while it is clear. verify refuses a
    record that is of no attempt, and for an item that is at its locator or under its marked name it
    reads the item's tips now (control_space_remove.tips) and refuses, naming each one, unless every
    commit they name is at a kept ref of that attempt. So a process killed after removing was written
    and before its keep step leaves nothing reconcile may complete: the record of the earlier attempt
    does not stand for this removal, and a commit made since is named. An item at neither name has
    nothing left to read, and one the ledger holds as removed is not read. Rows
    ac3/record-of-this-attempt and ac3/verify-reads-current-tips; falsifiers
    space345-removal-keeps-the-old-record, space345-removed-on-a-stale-record and
    space345-verify-reads-no-tips.
  - Finding 2, the ledger accepted an empty keep record. keep now runs git in the item, at its
    locator, reads the commit HEAD names, and refuses the write, space_keep_head, unless it names
    <attempt>/head at that commit, a ref the Ledger has just read in the main repository. An empty
    record is accepted only for an item git reads no HEAD commit in; an item git cannot read there is
    space_keep_item. The refs of one write are those of one attempt (invalid_input:refs otherwise).
    Row ac1/ledger-reads-the-head; falsifier space345-empty-keep-record-accepted.
  - Finding 3, saved files were 0600. A file of work/ has the permission bits of the item's file and a
    file of staged/ those of its index entry, set before the file's sync and read back; the owner's
    read bit is always set, because the store reads its files back, and set-id and sticky bits are
    never set there; the manifest holds the whole mode as before. An attempt one of whose files has
    other bits is not used by a retry and verify reports it missing. The row restores the design's
    plain way (0.5: a worktree at the kept head, cp -a of the attempt) and finds every mode and every
    byte. Row ac4/modes-kept; falsifier space345-saved-files-0600. An attempt written before this
    change has files of mode 0600 and so reads as missing: a retry saves it again under the next
    number, and nothing is deleted.
  - Finding 4, new store folders were not synced into the folder above them. The folder above each
    folder of the store (the state root, the store, the ticket's folder) is synced each time an
    attempt begins, the item's folder when the temporary folder is made in it and again after the
    rename, and every file, after its mode is set, and every folder of the attempt before the rename.
    A failed sync is keep_failed. Row ac5/folders-synced; falsifier space345-new-folder-not-synced.
    The row ac5/failed-save-removes-nothing now fails a sync of the attempt's own files, since a
    failing sync of a store folder stops the attempt before it has a temporary folder (the new row).
  - VELDO-0315 and VELDO-0346 each have a History line of this date for what they read from here.
