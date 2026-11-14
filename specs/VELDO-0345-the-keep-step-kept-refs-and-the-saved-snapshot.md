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
  - "scripts/suites/*_veldo_0345_*.py"
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
