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
    scratch or build output item.
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
      a clean clone: no uncommitted and no untracked file, no stash, and every ref and its HEAD held by
      one of its own remote-tracking refs. One that cannot be read, and a folder that cannot be listed,
      hold the item
    falsified_by: >
      Look beneath worktrees and agent repositories only; the row's clone with an unpushed commit in a
      session's scratch is deleted and the row fails
  - id: AC3
    text: >
      A worker clone, a batch clone and a candidate workspace are removed as private repositories: the
      keep step records every commit in the main repository first. A batch clone or a candidate workspace
      whose work tree holds an uncommitted or untracked file that is work is deferred as unique work and
      raises one request on the space disposition touchpoint, as a worktree does. A worker clone of a run
      that has ended is not deferred for such files: they are saved in the snapshot store, and the clone
      is removed with no request
    falsified_by: >
      Each of these turns a row of its own red. Remove a clone by the folder remover alone: the row's
      commit that the runner never brought across is in no repository. Remove a worker clone without the
      snapshot: the row's uncommitted file is neither in place nor restored
  - id: AC4
    text: >
      An evidence file is removed only when its digest, read again at the removal, is the digest of a blob
      the store holds or of a file in a commit the trunk or a kept ref reaches; a store or a commit that
      cannot be read is no copy
    falsified_by: >
      Use the digest recorded at the last measurement; the row changes the file after it was measured,
      finds the changed file gone and fails
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

> Components: Probes, Signal (rules 5 and 6), Removers, Clone provisioner, Batch, Landing line. Depends on
> 0302, 0303, 0305, 0324 and 0345. It builds section 0.1 and 0.4 where they go past what VELDO-0299 and
> VELDO-0330 built.

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
