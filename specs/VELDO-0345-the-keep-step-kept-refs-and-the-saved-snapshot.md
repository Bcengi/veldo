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
    the saved ref when a snapshot was written, and the path the item had. Each kept ref's own log names
    the event that wrote it.
  error_taxonomy: >
    space_deferred:keep_failed, with the ref and what git said, when a kept ref or a snapshot cannot be
    written or read back, when the fetch from a private repository fails, and when a private repository
    names no main repository. Nothing is removed in any of these cases.
acceptance_criteria:
  - id: AC1
    text: >
      Before git's worktree remove runs, the worktree's checked-out commit, each of its own refs, each
      commit an operation in progress names and each commit only its HEAD log names is on a kept ref under
      refs/veldo/kept/<ticket>/<item>/ in the main repository, read back, and listed on the item's keep
      record; the ledger refuses the outcome removed for a worktree or a private repository that has no
      keep record
    falsified_by: >
      Write the refs after the remove; the row kills the remover between the two, finds the commit the
      HEAD log named in no ref, and fails
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
      fetch fails, or when a private repository names no main repository, nothing is removed and the item
      is deferred as keep_failed with the ref and git's words. A second attempt after a crash finds the
      refs it wrote and passes. Rule 5 does not count a kept ref as a ref that holds a commit
    falsified_by: >
      Call the remover after a failed write; the row makes the main repository's refs unwritable, finds
      the worktree gone and its commit unreachable, and fails
  - id: AC4
    text: >
      The saved snapshot is a commit in git's stash layout on the item's saved ref, holding the tracked
      edits, the staged state and the untracked files, the ignored ones that are work included. Writing it
      changes neither the worktree, nor its index, nor the repository's stash entries, and git's stash
      apply with the index option brings every file back byte for byte with its mode
    falsified_by: >
      Write it with git's stash command; the row compares the worktree and the stash entries before and
      after, finds the worktree emptied and an entry added, and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. Removers then run without the keep step, as before this ticket. Kept refs already
  written stay in their repositories and are still read by plain git.
---

## Intent

Before a worktree or a private repository is removed, every commit it reaches is recorded on a kept ref in
its main repository, and before a Discard or a review's scratch removal the uncommitted state is saved as
one commit on a kept ref. When either write fails, nothing is removed. This is the part of the owner's
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
> remover of 0300.

Build order. It is built straight after 0301 and before every ticket that removes a worktree or a private
repository on a real host. depends_on holds the dependencies the design states for this ticket.

Measured on git 2.43.0 on 2026-11-13, and to be repeated as rows: a commit left behind by a reset in a
detached worktree is named only by that worktree's HEAD log, and git's worktree remove takes the log; a
fetch by hash from a local path works when the call sets uploadpack.allowAnySHA1InWant for itself; a
commit built in the stash layout through index files of the caller's own leaves the worktree's status
unchanged, and git's stash apply with the index option restores a tracked edit, a staged file, an
untracked file with its executable bit and an ignored file from it.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design section 0, added that day for the owner's rule (Telegram 41209). The
  number follows VELDO-0344, the highest a spec file or a proof folder held on any ref or in any worktree;
  nothing on any ref named 0345 to 0349. Status ready.
