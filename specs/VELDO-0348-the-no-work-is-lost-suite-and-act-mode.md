---
schema: veldo.spec/v1
id: VELDO-0348
title: "The no-work-is-lost suite, and act mode"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0320, VELDO-0339, VELDO-0344, VELDO-0346, VELDO-0347]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/bin/veldo"
  - "bin/veldo"
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "engine/.veldo/control_space_signal.py"
  - ".veldo/control_space_signal.py"
  - "scripts/suites/*_veldo_0348_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0348-the-no-work-is-lost-suite-and-act-mode.md"
  - "specs/index.md"
  - "proof/VELDO-0348/**"
behavior_bearing: true
observability:
  logs: >
    One proof record per run of veldo space prove: the host, the digest of the space modules, git's
    version, the result, the number of rows and the name of each row that failed.
  error_taxonomy: >
    space_act_unbuilt naming VELDO-0348 until this ticket lands. Then the switch to act is refused, naming
    what does not match, when no proof record passed for the space modules and the git in use.
acceptance_criteria:
  - id: AC1
    text: >
      The suite drives every removal path of section 0.7 at every kind of work of section 0.1, in every
      shape of that section's table: nested, adopted, an agent worktree and then its repository, linked,
      locked, unreadable, main repository gone, snapshot store, retry and restore. After each drive every
      planted thing is in its place byte for byte, or comes back byte for byte through veldo space restore
      from what the removal left; a restore that says it succeeded while a planted file is absent fails
      the row; the suite's own copies are never read. The paths, kinds and shapes are data, and a remover
      or a kind of work with no row fails the suite
    falsified_by: >
      Run Discard without the snapshot; the Discard rows find the untracked file neither in place nor
      restored and fail
  - id: AC2
    text: >
      A file added after the probe, a process that opens a file after the first probe, a branch moved
      between the probe and the remove, a file added between the snapshot and the forced remove, an
      ignored file added between Save's snapshot and its remove, and a file of review scratch or of a dead
      run's worker clone rewritten between the snapshot and its own delete each leave the work in place. A
      write by the worktree's path between the last look and git's remove, in a Discard and in a Save,
      either fails for the writer or leaves its file in place or in the snapshot. A worker clone whose
      removal the comparison stopped is back at its locator, and reconcile run afterwards does not mark it
      gone. With the process killed at each step boundary of section 0.2, the two snapshot boundaries
      included, and of the folder remover, and reconcile run afterwards, every planted thing is in place
      or comes back
    falsified_by: >
      Complete a removing item at reconcile without its keep record; the row killed before the refs were
      written finds the worktree gone and its commit unreachable, and fails
  - id: AC3
    text: >
      Each mutation of section 0.7 turns a row of the suite red and is registered with the gate's mutation
      check: a kept child that does not hold, a stash counted as a holding ref, no look beneath a
      worktree, a private repository compared with itself, an unreadable worktree read as unlocked, an
      unopenable scratch read as free, the keep step skipped, the remove run after a failed keep, Discard
      without the snapshot, a snapshot written into a repository's object store, a removing item completed
      with no keep record, the remove run after a failed snapshot, review scratch deleted without the
      snapshot, a file deleted without the comparison with its manifest, an existing snapshot folder
      replaced on a retry, Save's remove run with an ignored file the snapshot does not hold, a restore
      that applies the snapshot only when its folder is there, a clone adopted as scratch, no look at an
      item's own folder, an agent worktree's kept refs written into its agent repository, a clean clone
      read without its logs, a keep record that holds only the newest attempt, a folder left under its
      marked name when the comparison stops its removal, and a Discard or a Save that removes the worktree
      at its own path
    falsified_by: >
      Drop the nested rows from the suite's data; the mutation that skips the look beneath a worktree
      leaves the suite green and the mutation check fails
  - id: AC4
    text: >
      The switch to act is refused as space_act_unbuilt naming VELDO-0348 until this ticket lands. From
      then it is refused unless the ledger holds a proof record that passed, written by the owner's veldo
      space prove on this host, whose digest of the space modules and whose git version are the ones in
      use; the refusal names what does not match. A scope already in act with no matching record writes
      due and removes nothing
    falsified_by: >
      Accept any proof record that passed; the row changes one space module after the proof, switches a
      scope to act and fails
required_evidence: [unit, integration]
rollback: >
  Switch every scope back to report, then revert the change. The suite leaves the gate, and the ledger
  again refuses every switch to act that the other conditions refuse. Proof records stay in the journal.
---

## Intent

One suite asks one question of every removal path: was work lost. It plants each kind of work in each
awkward shape, drives the removal, and looks for the work in its place or through restore. No scope can be
switched to act until it has passed in the gate and on the host that will remove.

## Design

This is one of the four tickets added to VELDO-0295 for the owner's rule that no work is ever lost
(Telegram 41209: "It's very important no work is ever lost. Space management needs to ensure this very
clearly"). The design is docs/design/VELDO-0295-design.md, and the rule is its section 0. Design sections
this ticket builds: 0.7 (the suite, its paths, kinds, shapes and mutations, and the conditions of act),
0.6, the proof record of 4.10, the proved command and the mode command of 6.1, and step 8 of section 11.
Section 12 of the design holds the ticket itself; its acceptance criteria and falsifiers are copied here
word for word.

What section 12 says about this ticket:

> Components: the suite, CLI (space prove), Ledger (the proof record, mode), Signal. Depends on 0320, 0339,
> 0344, 0346 and 0347. It builds section 0.7. It joins VELDO-0332, VELDO-0339 and VELDO-0344 as what must
> be there before any scope can be switched to act.

Build order. It is the last ticket, because it drives every removal path the others build. depends_on
holds the dependencies the design states for this ticket.

The host form runs in a scratch root of its own, with repositories and a ledger it makes for itself and
Docker objects only under its own label. It touches no item of the live ledger. A row's oracle is the
planted work itself: in its place byte for byte, or back byte for byte through veldo space restore. A copy
the suite kept proves nothing and is never read.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design section 0, added that day for the owner's rule (Telegram 41209). The
  number follows VELDO-0344, the highest a spec file or a proof folder held on any ref or in any worktree;
  nothing on any ref named 0345 to 0349. Status ready.
- 2026-11-13: amended for the lead's answers to the six questions of design section 15 (section 13 records
  them). A snapshot of uncommitted, untracked or ignored files is stored outside git, in the snapshot
  store under the state root, and never in a repository's object store, so a secret in an ignored file
  does not enter git; commits stay on kept refs (design 0.3). AC3 gains one mutation: a snapshot written
  into a repository's object store. The suite plants a marker in the ignored file and searches every
  repository's objects for it after each drive (design 0.7). The falsifier is unchanged.
- 2026-11-13: amended from the validation of design section 0
  (design-veldo-nowork-0344r2-validation-2026-11-14.md, verdict CHANGES; design 14.7), under the owner's
  rule that no work is ever lost. N-R3: AC1 names every shape of design 0.7's table, with the ones this
  validation added: an adopted batch clone, an agent worktree and then its repository, a main repository
  that is gone, a snapshot store that is full or not writable, a retry onto an existing snapshot folder,
  and a restore whose snapshot or kept ref is missing or changed. A restore that says it succeeded while a
  planted file is absent fails its row. AC2 gains three mid-removal cases (Save's ignored file, review
  scratch and a worker clone rewritten after the snapshot) and the two kill points around the snapshot.
  AC3 gains ten mutations: the remove run after a failed snapshot, review scratch deleted without the
  snapshot, a file deleted without the comparison with its manifest, an existing snapshot folder replaced
  on a retry, Save's remove run with an ignored file the snapshot does not hold, a restore that applies
  the snapshot only when its folder is there, a clone adopted as scratch, no look at an item's own folder,
  an agent worktree's kept refs written into its agent repository, and a clean clone read without its
  logs. The three falsifiers are unchanged.
- 2026-11-13: amended from the final check of design section 0
  (design-veldo-nowork-r2-validation-2026-11-14.md, verdict CHANGES; design 14.8). F1: AC3 gains one
  mutation, a keep record that holds only the newest attempt, and design 0.7's Retry shape gains the case
  that turns it red: a review worktree whose scratch removal stopped after its first delete, is retried
  and is then restored. The falsifier is unchanged.
- 2026-11-13: amended for the two points of the final check of design section 0 that the amendment before
  this one left out (design-veldo-nowork-r2-validation-2026-11-14.md, F3 and F4; design 14.8), by the
  lead's word that both are required under the owner's rule that no work is ever lost. AC2 gains two
  cases: a write by the worktree's path between the last look and git's remove, in a Discard and in a
  Save, which either fails for the writer or leaves its file in place or in the snapshot (F4), and a
  worker clone whose removal the comparison stopped, which is back at its locator and is not marked gone
  by reconcile (F3). AC3 gains two mutations: a folder left under its marked name when the comparison
  stops its removal, and a Discard or a Save that removes the worktree at its own path. Design 0.7's
  Mid-removal shape gains the cases that turn them red. The falsifiers are unchanged.
