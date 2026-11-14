---
schema: veldo.spec/v1
id: VELDO-0346
title: "Getting removed work back: kept, restore and drop"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0319, VELDO-0345]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/bin/veldo"
  - "bin/veldo"
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "engine/.veldo/control_space_keep.py"
  - ".veldo/control_space_keep.py"
  - "engine/.veldo/control_space_reconcile.py"
  - ".veldo/control_space_reconcile.py"
  - "engine/.veldo/control_api.py"
  - ".veldo/control_api.py"
  - "engine/ui/src/api/routes.json"
  - "engine/ui/src/features/space/**"
  - "engine/ui/src/views/SpaceView.vue"
  - "scripts/suites/*_veldo_0346_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0346-getting-removed-work-back-kept-restore-and-drop.md"
  - "specs/index.md"
  - "proof/VELDO-0346/**"
behavior_bearing: true
observability:
  logs: >
    A restore is one journal record with the item, the path and the refs it used. A drop is one journal
    record with the item and every ref it deleted, with the commit each one held. A report of kept work
    missing names the item, its ticket, the path it had and the ref or the snapshot that is missing.
  error_taxonomy: >
    restore is refused when it is not signed by the owner, when something is at the path, for an item
    with no keep record, when a kept ref does not resolve, when the snapshot the keep record names is
    missing or does not match its recorded digest or its manifest, and when a manifest path leads outside
    the target. Each refusal says what is missing and adds nothing. drop kept is refused when it is not
    signed by the owner.
acceptance_criteria:
  - id: AC1
    text: >
      veldo space kept lists, for each removed worktree and private repository, its ticket, the path it
      had, the event that removed it and each kept ref with its commit, and says of each ref whether it
      still resolves and of each snapshot whether it is still there and whole. With no ledger reachable it
      lists the same refs from the repository alone
    falsified_by: >
      Read the ledger only; the row with the authority down gets an empty list and fails
  - id: AC2
    text: >
      veldo space restore adds a worktree at the path the item had, or at the path given, at the kept
      head, and applies the snapshot the keep record names: after a Discard and a restore the tracked
      edits, the staged state, the untracked files and the ignored files that are work are back byte for
      byte with their modes. Whether there is a snapshot is read from the keep record alone. It refuses,
      adding nothing and saying what is missing, when something is at the path, when the record names a
      snapshot whose folder or manifest is missing or whose manifest has another digest than the record
      holds, when a saved file does not match its manifest, and when a manifest path is absolute, holds a
      .. part or resolves outside the target path. It leaves the kept refs and the snapshot in place
    falsified_by: >
      Each of these turns a row of its own red. Restore the head without the snapshot: the row's untracked
      file is missing. Apply the snapshot only when the folder is there: the row deletes the snapshot,
      restores, finds the head without the untracked file, and the command said success. Copy a manifest
      path as it is written: the row's manifest names a path with a .. part, and a file is written outside
      the target
  - id: AC3
    text: >
      Only veldo space kept drop removes a kept ref or a snapshot. It is the owner's signed command, it
      lists the commits that would no longer be reachable and the snapshot's files before it acts, and it
      is refused from every host principal
    falsified_by: >
      Accept drop from space-runner; the row that sends it finds the refs gone and fails
  - id: AC4
    text: >
      The console's Removed section and the space.kept read show, for each removal, the number of kept
      refs, whether a snapshot was saved and its size, and the restore command with the item filled in;
      and for the installation the count and the size of all kept refs and of all snapshots
    falsified_by: >
      Leave the kept refs out of the read; the row that expects the restore command beside the removed
      worktree finds none and fails
  - id: AC5
    text: >
      Reconcile and veldo space kept check every keep record against the disk: each kept ref resolves to
      its recorded commit, the snapshot folder the record names is there, and its manifest has the
      recorded digest. What fails is reported under space.reports as kept work missing, with the item, and
      is shown at the top of the console's Space screen until the ref or the snapshot is back or the owner
      drops that item's kept work. A snapshot store that is gone, or whose owner or mode is not the
      installation owner's and 0700, is reported the same way. Snapshot folders no keep record names are
      listed with their sizes, and nothing is proposed for them
    falsified_by: >
      Check the kept refs only; the row deletes the snapshot store, runs reconcile, finds no report and
      fails
required_evidence: [unit, integration, ui_states]
rollback: >
  Revert the change. The kept refs and the snapshots stay. They are restored by hand: git worktree add
  at the kept head, then a copy of the snapshot's work folder into it.
---

## Intent

The owner gets any removed item's work back with one command. veldo space kept lists what every removal
left, veldo space restore brings a worktree back with its uncommitted state, and veldo space kept drop is
the one way a kept ref is ever deleted.

## Design

This is one of the four tickets added to VELDO-0295 for the owner's rule that no work is ever lost
(Telegram 41209: "It's very important no work is ever lost. Space management needs to ensure this very
clearly"). The design is docs/design/VELDO-0295-design.md, and the rule is its section 0. Design sections
this ticket builds: 0.5 (getting it back), the restore and drop kept commands of 6.1, the space.kept read
and the space.restore and space.kept.drop actions of 6.6, and the Removed row of section 10. Section 12 of
the design holds the ticket itself; its acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: CLI, Ledger (restore, drop kept), Keeper (the check of keep records), Reconciler, API,
> Console. Depends on 0319 and 0345. It builds section 0.5 and the watch on the snapshot store of 0.3.

Build order. It is in the closing sequence, after 0319, whose console it extends. depends_on holds the
dependencies the design states for this ticket.

The listing must work with the authority down, because the day the owner needs it may be the day the
service does not start. The ref names carry the ticket and the item, and each ref's log carries the event.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design section 0, added that day for the owner's rule (Telegram 41209). The
  number follows VELDO-0344, the highest a spec file or a proof folder held on any ref or in any worktree;
  nothing on any ref named 0345 to 0349. Status ready.
- 2026-11-13: amended for the lead's answers to the six questions of design section 15 (section 13 records
  them). A snapshot of uncommitted, untracked or ignored files is stored outside git, in the snapshot
  store under the state root, and never in a repository's object store, so a secret in an ignored file
  does not enter git; commits stay on kept refs (design 0.3). AC2: restore applies the snapshot from the
  snapshot store, with modes, and refuses when a saved file does not match its manifest; it leaves the
  snapshot in place. AC3: drop also removes the item's snapshot and lists its files first. AC4, from the
  lead's answer on growth: the read and the console also show each snapshot's size and, for the
  installation, the count and the size of all kept refs and of all snapshots; nothing drops them without
  the owner's rule. The three falsifiers are unchanged. Plain git no longer restores a snapshot; without
  Veldo its working files are copied back by hand (design 0.5).
- 2026-11-13: amended from the validation of design section 0
  (design-veldo-nowork-0344r2-validation-2026-11-14.md, verdict CHANGES; design 14.7), under the owner's
  rule that no work is ever lost. N3.1: AC2 reads whether there is a snapshot from the keep record alone,
  and refuses, adding nothing and saying what is missing, when the folder or the manifest the record names
  is missing, when the manifest has another digest, and when a manifest path is absolute, holds a .. part
  or resolves outside the target; read from the disk, a deleted snapshot gave a worktree at the kept head
  and the word success. AC2 gains two falsifiers. N3.2: AC1 says of each snapshot whether it is still
  there and whole, and new AC5 has reconcile and veldo space kept check every keep record and report kept
  work missing until it is back or dropped, so the loss of the store or of a kept ref is never silent. The
  footprint gains the reconciler, which calls the check. The guard hook the validation recommended is put
  to the lead in design section 15 and is not in this ticket. Four criteria became five.
