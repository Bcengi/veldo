---
schema: veldo.spec/v1
id: VELDO-0260
title: A local landing keeps every working tree that has the trunk checked out in step with the trunk, updating a clean one with the move and refusing the landing when one has local changes
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0148, VELDO-0235]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_landing.py"
  - ".veldo/control_landing.py"
  - "engine/.veldo/control_landing_station.py"
  - ".veldo/control_landing_station.py"
  - "docs/runbook.md"
  - "scripts/suites/*_veldo_0260_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0260-a-local-landing-keeps-every-checked-out-trunk-working-tree-in-step.md"
  - "specs/index.md"
  - "proof/VELDO-0260/**"
behavior_bearing: true
observability:
  logs: >
    Each local publication records the working trees found with the trunk checked out (path, and whether
    it was clean), and for each one whether it was moved with the trunk, left as it was, or the reason the
    landing was refused. A working tree's local changes are named by path and count only, never by
    content.
  metrics: >
    Count local landings by working-tree outcome (none checked out, moved with the trunk, refused for
    local changes, restored after a lost swap).
  traces: >
    Join each working-tree outcome to the landing dispatch and to its publication effect, so a refused
    landing and the re-land that follows it are one chain.
  error_taxonomy: >
    Keep the landing's names (VELDO-0057, VELDO-0148, VELDO-0235). A working tree with the trunk checked
    out and local changes refuses the publication before the swap as trunk_checkout_dirty:<working tree>;
    a working tree that cannot be moved for another reason (its index is locked, a file cannot be written)
    refuses as trunk_checkout_unmovable:<working tree>; both are re-landed under VELDO-0148 once the cause
    is gone.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: before a local landing swaps the trunk, it finds every working tree of the project's repository
      that has the trunk checked out. Set: the repository's main working tree and every linked working tree
      are read from the repository's own list of working trees, each one whose HEAD is the symbolic ref
      refs/heads/<trunk> is taken, and a detached HEAD at the same commit, another branch or a bare
      repository is not. The set is recorded in the publication effect before the swap. Rows: a repository
      with the trunk checked out in its main working tree, one with it checked out only in a linked working
      tree, and one with a detached HEAD at the trunk's tip each record exactly the working trees that hold
      the trunk.
    falsified_by: >
      Check only the repository's main working tree; the linked-working-tree row records nothing and its
      later assertion that the tree moved with the trunk fails.
  - id: AC2
    text: >
      Claim: a clean working tree with the trunk checked out moves with the trunk, so after the landing its
      HEAD, index and tracked files are the candidate commit. Set: clean means no staged or unstaged change
      to a tracked file against the old tip; the working tree is moved from the old tip to the candidate
      with a two-tree merge that touches only the files the two commits differ in, and untracked and
      ignored files are left as they were. A swap that loses the compare-and-swap (trunk_moved) puts every
      working tree it moved back on the old tip, so a refused landing leaves each tree as it found it. Rows:
      after a local landing the clean tree's status shows no change and its files equal the candidate's
      tree; an untracked and an ignored file planted before the landing are byte for byte unchanged; a
      swap made to lose restores the tree to the old tip.
    falsified_by: >
      Move the ref only, as VELDO-0235 does today; the clean tree's status then shows the candidate's
      changes reversed as staged changes and the row fails.
  - id: AC3
    text: >
      Claim: a working tree with the trunk checked out and local changes refuses the landing before
      anything moves. Set: any staged or unstaged change to a tracked file, or a merge, rebase or
      cherry-pick in progress, in a working tree of AC1 refuses the publication as
      trunk_checkout_dirty:<working tree> before the swap; the trunk ref, every working tree and every file
      are unchanged; the owner's landing brief names the working tree and says the landing waits until it
      is clean, and the landing is re-landed under VELDO-0148 then. Rows: an edited tracked file and a
      staged change each refuse by name with the ref and the file byte for byte unchanged; after the change
      is committed elsewhere or discarded, the re-land lands.
    falsified_by: >
      Skip the clean check and swap anyway; the edited-file row finds the trunk moved and its local change
      shown against the wrong base, and fails.
  - id: AC4
    text: >
      Claim: nothing else changes. Set: a local landing into a repository where no working tree has the
      trunk checked out is byte for byte VELDO-0235's (no working tree is read or written); land_and_push is
      untouched; the landing suites of VELDO-0057, VELDO-0148, VELDO-0153 and VELDO-0235 pass unchanged.
    falsified_by: >
      Move the main working tree whenever the repository has one, whatever its HEAD; the no-checkout row,
      whose main working tree holds another branch, finds that branch's files rewritten and fails.
required_evidence: [unit, integration]
rollback: >
  Revert the change. Local landings move the trunk ref only again, as VELDO-0235 built it, and a working
  tree with the trunk checked out is again left behind. Landings already made are ordinary commits on the
  local trunk and stay. No automatic rollback, retry or recovery is authorized.
---

## Intent

A project that lands locally moves its trunk branch in place. When someone has that branch checked out,
moving the branch alone leaves their working tree on the old commit while the branch says the new one: the
tree then shows the landed change backwards as if it were their own edit, and the next commit made there
can silently undo the landing. A mature version control host handles a push to a checked-out branch the
same way: it moves the working tree with the branch when the tree is clean, and refuses when it is not.
Local landing does the same.

## Context

- VELDO-0235 lands locally by a compare-and-swap of refs/heads/<trunk> from the recorded watermark to the
  candidate. It reads and writes no working tree; its independent review and its proof notes record that
  a working tree with the trunk checked out is not updated (the suites use a detached checkout).
- VELDO-0148 re-lands a landing refused because its subject moved; a refusal for a dirty working tree is
  re-landed the same way once the tree is clean.

## Design

Find the checked-out trees from the repository's own working-tree list, refuse on local changes before
the swap, move each clean tree together with the ref, and restore the trees if the swap loses. The check
and the move are one step of the publication effect VELDO-0235 records.

## Out of scope

- Pushing a locally landed commit (VELDO-0235 out of scope).
- Stashing, merging or otherwise preserving a person's local changes: the landing refuses and the person
  decides.
- Working trees of other repositories, and land_and_push.

## What the reviewer judges

- Normal use: a project lands locally while its trunk is checked out in a clean working tree, and that
  tree shows the landed commit with nothing to commit.
- Threat model: a landing that overwrites a person's uncommitted work, or that leaves a checked-out tree
  out of step with its branch so the next commit there reverts the landing.

## History

2026-11-04: new draft on the owner's request, Telegram 39145, the follow-up for finding E13 of the plan
consistency review (research/veldo-plan-consistency-review-2026-11-04.md) on VELDO-0235: a local landing
moves refs/heads/<trunk> without updating a working tree that has the trunk checked out. VELDO-0235 is
built and its criteria stay unchanged; this ticket carries the fix. Standalone; no plan work item.

2026-11-05: the review amendments and new tickets approved by the owner, Telegram 39157 ("Yes", to 39156). Status ready.
