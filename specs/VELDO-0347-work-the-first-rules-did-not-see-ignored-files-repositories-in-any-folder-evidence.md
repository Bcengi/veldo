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
  - "scripts/suites/*_veldo_0347_*.py"
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
