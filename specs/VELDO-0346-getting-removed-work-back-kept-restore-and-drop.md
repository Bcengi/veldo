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
    record with the item and every ref it deleted, with the commit each one held.
  error_taxonomy: >
    restore is refused when it is not signed by the owner, when something is at the path, and for an item
    with no keep record. drop kept is refused when it is not signed by the owner.
acceptance_criteria:
  - id: AC1
    text: >
      veldo space kept lists, for each removed worktree and private repository, its ticket, the path it
      had, the event that removed it and each kept ref with its commit, and says of each ref whether it
      still resolves. With no ledger reachable it lists the same refs from the repository alone
    falsified_by: >
      Read the ledger only; the row with the authority down gets an empty list and fails
  - id: AC2
    text: >
      veldo space restore adds a worktree at the path the item had, or at the path given, at the kept
      head, and applies the saved snapshot: after a Discard and a restore the tracked edits, the staged
      state, the untracked files and the ignored files that are work are back byte for byte. It refuses
      when something is at the path, and it leaves the kept refs in place
    falsified_by: >
      Restore the head without the snapshot; the row's untracked file is missing and the row fails
  - id: AC3
    text: >
      Only veldo space kept drop removes a kept ref. It is the owner's signed command, it lists the
      commits that would no longer be reachable before it acts, and it is refused from every host
      principal
    falsified_by: >
      Accept drop from space-runner; the row that sends it finds the refs gone and fails
  - id: AC4
    text: >
      The console's Removed section and the space.kept read show, for each removal, the number of kept
      refs, whether a snapshot was saved and the restore command with the item filled in
    falsified_by: >
      Leave the kept refs out of the read; the row that expects the restore command beside the removed
      worktree finds none and fails
required_evidence: [unit, integration, ui_states]
rollback: >
  Revert the change. The kept refs stay and are restored with plain git: git worktree add at the kept
  head, then git stash apply with the index option on the saved ref.
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

> Components: CLI, Ledger (restore, drop kept), API, Console. Depends on 0319 and 0345. It builds section
> 0.5.

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
