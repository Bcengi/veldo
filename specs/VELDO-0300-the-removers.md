---
schema: veldo.spec/v1
id: VELDO-0300
title: "The removers"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0326, VELDO-0331]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space_remove.py"
  - ".veldo/control_space_remove.py"
  - "scripts/suites/*_veldo_0300_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0300-the-removers.md"
  - "specs/index.md"
  - "proof/VELDO-0300/**"
behavior_bearing: true
observability:
  logs: >
    Each outcome records the method, the item's bytes just before, and the pool's free space before and
    after; for an engine image pool the host figure apart.
  error_taxonomy: >
    A refusal by git or by the engine is the deferral space_deferred:remove_refused with the thing
    untouched. A second probe that finds a user puts the folder back under its own name, and the item is
    deferred as space_deferred:in_use.
acceptance_criteria:
  - id: AC1
    text: >
      A folder is removed by rename, second probe, delete. The row injects an open file between the first
      probe and the rename through the probe's test seam, so the order is fixed; the folder comes back
      under its own name
    falsified_by: >
      Delete after the first probe; the row finds the folder gone and fails
  - id: AC2
    text: >
      A worktree is removed only by git's non-forced remove, and a refusal by git is the deferral
      remove_refused with the worktree untouched
    falsified_by: >
      Pass the force option; the row with an untracked file loses it and fails
  - id: AC3
    text: >
      No remover runs a prune command, and none but the discard remover passes a force option; the row
      reads every command each remover ran
    falsified_by: >
      Use the engine's volume prune for volumes; the command row fails
  - id: AC4
    text: >
      Each remover returns the item's bytes just before and the pool's free space before and after, and
      for an engine image pool the host figure apart
    falsified_by: >
      Report the engine's own reclaimable figure as freed; the row that compares it with the measured free
      space fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. Removers are called only through Signal, so without them nothing is removed.
---

## Intent

Each removal action has one remover, and it uses the owning tool's own remove: a rename, a second probe
and a delete for a folder, git's non-forced remove for a worktree, the engine's non-forced remove for a
Docker object. No remover runs a prune command.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.5 (removers). Section 12 of the
design holds the ticket itself; its acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Removers.

> The builder verifies with a test what git's non-forced worktree remove does with ignored files, and
> records the result in the proof. The design does not depend on the answer, because build output is removed
> before the worktree.

Build order. It is built together with 0298, 0299, 0330 and 0300, after the first five tickets. The design
states no dependency for this ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-13: from the owner's rule that no work is ever lost (Telegram 41209), design section 0. No
  acceptance criterion changed. The keep step is added inside the worktree remover and the private
  repository remover by VELDO-0345, which is built after this ticket: each records the item's commits on
  kept refs and has the keep record written before it calls its tool, and a failure is the deferral
  keep_failed. The discard remover and the review scratch remover write the snapshot first (VELDO-0318
  AC3, VELDO-0336 AC3).
- 2026-11-14: fixed after the independent review (verdict FIX; review-veldo-0300.md, nine findings), under the
  owner's rule that no work is ever lost (Telegram 41209). No acceptance criterion changed. The reviewer
  planted work and lost four kinds of it through the whole rule chain with a keep step that answered ok.
  Each now has a row that plants that work and a registered falsifier that loses it:
  - Finding 1, ignored files that are work. The worktree remover enforces the save itself, as design 0.3
    has Save and Discard do: after the keep step it moves the worktree to its marked name with git's
    non-forced worktree move, runs the in-use probe there, and reads git's status with every ignored
    path. An ignored folder that a committed ignore file or a declared build output pattern covers is
    build output; every other ignored path (a file only info/exclude ignores, a loose ignored file) is
    work and must be in the keep step's snapshot with the same mode and digest. Otherwise the worktree is
    moved back and deferred keep_failed. git's remove then runs on the marked name; its refusal moves
    the worktree back. Row work/ignored-files; row work/worktree-second-probe for the probe there.
  - Finding 2, a commit made after the keep step. The keep step answers {ok, tips}, tips being what
    control_space_remove.tips read in the item (head, branch, the commits an operation names, its own
    refs, its log; for a private repository every ref, stash entry and log). The remover reads them
    again as its last look under the marked name; any difference is keep_failed. An answer with no tips
    is keep_failed with nothing touched. Row work/commit-in-the-gap.
  - Finding 3, an agent repository's files. Under its marked name, after the second probe, a repository
    with a work tree is refused keep_failed on any modified, staged or untracked entry and on any
    ignored path that is work. The exception for a worker clone with a snapshot is VELDO-0347's and is
    not built: until then every such repository waits. Row work/agent-repository-files.
  - Finding 4, a repository in a folder. The walk that measures a folder before the first delete stops
    on a folder that holds a .git entry or is a git folder; the folder is put back, remove_refused.
    Scratch, build output and a cache hold none; an agent repository and a worktree hold their own and no
    other. The clean clone of design 0.1 is not excepted here: that is VELDO-0347. Row
    work/repository-in-a-folder.
  - Finding 5, a link or .. in the path. Every remover refuses a path that is not absolute, plain and
    free of links, by itself and before the keep step; the folder remover opens the folder's parent from
    / down with no link followed and renames, deletes and puts back by name inside that descriptor. Row
    work/link-and-dotdot.
  - Finding 8, a folder left under its marked name. The marked name now writes the item's id without
    loss (two ids never share one), unmarked reads it back and left(path, id) finds what a killed
    removal left. Looking there before an item is marked gone is reconcile's, VELDO-0315 AC2, which
    already says so; its History has the pointer. Row work/marked-name.
  - Finding 7 is VELDO-0299's and is fixed with this change (its History). The removers' own runner
    sends the probes' git reads through the Git boundary too. Row work/probes-through-the-boundary.
  - Finding 6 (Signal names every tool refusal remove_refused) is recorded in VELDO-0301's History:
    its spec did not say it, and control_space_signal.py is not this ticket's.
  - Finding 9 (the Docker removers do not read the object's label again at the remove; low) is NOT
    fixed here. What an engine says of an object is VELDO-0341; it stays open and is named in the proof.
  What changed for a caller: a worktree is on disk under <name>.veldo-removing.<id> between git's move
  and git's remove, so a kill there leaves a whole worktree under that name (design 0.2's table row for
  Save and Discard now holds for every worktree removal); and the plain remove of a worktree asks for a
  snapshot where the design's 6.5 row asks for one only after a Save. The design text is not edited by
  this change. Outside the footprint above, on the lead's instruction: .veldo/control_space_probe.py
  with its engine copy, scripts/check_git_boundary.py, suite 136 and proof/VELDO-0299.
- 2026-11-14: fixed after the re-review (verdict FIX; review2-veldo-0300.md), under the owner's rule that
  no work is ever lost (Telegram 41209). No acceptance criterion changed. The nine findings of the first
  review were found resolved or recorded; the reviewer planted three new kinds of work and lost each with
  a keep step that answered ok. Each now has a row that plants that work and a registered falsifier that
  loses it:
  - A, an edit git was told not to look at. A tracked file with the assume-unchanged or the skip-worktree
    bit shows in no status, so neither the last look nor git's own remove saw its edit. The last look now
    lists the index with its bits, and for each such file that is on disk compares git's hash of the
    file with the index's; another content, another type or a file that cannot be read is work. It is
    never left to git: an agent repository is refused keep_failed, and a worktree is refused keep_failed
    unless the keep step's snapshot holds the file with the same mode and digest, as for an ignored file
    that is work. Row work/hidden-edits, both bits in both kinds; falsifier: the read is skipped.
  - B, an agent repository with linked worktrees. The index, the HEAD and git's record of a linked
    worktree are files inside the repository's folder, so staged content in no commit went with it and
    the outside worktree was left orphaned. For a private repository, bare or not, the last look reads
    git's worktree list; any entry besides the repository's own, one whose folder is gone included, is
    keep_failed with the repository put back. This holds until a keep step saves each linked worktree's
    index, which is VELDO-0345's to add; nothing here removes such a repository. Rule 6 refuses the same
    thing earlier in the chain; the remover does not rest on it. Row work/linked-worktrees; falsifier: the
    list is not acted on.
  - C, an adopted worktree. Design 6.3 lets a committed ignore file name build output only in a worktree
    recorded when it was made; in one reconcile adopted only the project's declared build output
    patterns count. The last look now reads the item's adopted field and, when it is set, counts no
    committed ignore file as a source. Row work/adopted-build-output; falsifier: the field is not read.
  - D, the two findings recorded where nothing bound them. Finding 6 is now VELDO-0301 AC5 (the
    remover's deferral passed through; left_at keeps the item removing) and the ledger's part of it is
    VELDO-0345 AC6. Finding 9 is fixed here in code and is no longer pointed at VELDO-0341: each Docker
    remover has the engine show the object first and compares it with the item's record, the Id when
    the locator holds one and the compose project label when the locator holds one; an object the
    engine cannot show, one with another Id and one without that label is remove_refused and the engine
    is asked to remove nothing. Row work/docker-object-made-again, on a volume; falsifier: the
    comparison is skipped. What it cannot see: an engine gives a volume no Id of its own, so a volume
    recorded by its name alone, with no compose project, has nothing to be compared with.
  Not a finding, for the owner to know (the re-review's last table row): in a worktree recorded when it
  was made, a folder a committed rule such as *.local or .vscode/ covers is build output by design 0.1
  and 6.3 and goes with the worktree; a project keeps such a folder by its keep list.
