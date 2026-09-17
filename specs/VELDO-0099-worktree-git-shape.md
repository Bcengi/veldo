---
schema: veldo.spec/v1
id: VELDO-0099
title: Install-and-run observations resolve git metadata in either checkout shape
status: ready
risk: standard
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: []
placement: [enforcement]
protected_paths: []
footprint:
  - "scripts/suites/24_veldo_0007_install_and_run.py"
  - "specs/VELDO-0099-worktree-git-shape.md"
  - "specs/index.md"
  - "proof/VELDO-0099/*"
  - ".veldo/events.jsonl"
  - ".veldo/last_verify"
behavior_bearing: true
observability:
  logs: Named selftest rows distinguish copy fidelity, git resolution, and writes outside the temporary directory.
  metrics: Proof records exit codes and full gate counts for primary and linked checkout shapes at the same implementation commit.
  traces: Proof binds commands, checkout shape, commit, and mutation results to recorded logs.
  error_taxonomy: Missing git metadata, lost working bytes, and changed inventory entries fail named rows rather than standing down.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The VELDO-0007 AC4 substrate check accepts a working-tree copy from either valid
      checkout shape and resolves metadata through git rev-parse --git-dir and --git-common-dir.
      Set: Primary checkout with a .git directory and linked checkout with a .git pointer file,
      both at the same commit. Completeness: Drive both in isolated fixtures, assert equal HEADs,
      and require the copied stage, index, private git directory, and shared store to resolve
      inside the observation sandbox. Falsifier: Restore the .git is_dir requirement and the
      linked-checkout substrate row must fail while the primary control passes.
    falsified_by: >
      Restore the .git is_dir requirement and the linked-checkout substrate row must fail while
      the primary control passes.
  - id: AC2
    text: >
      Claim: The observation executes a copy of current working bytes, including uncommitted
      changes, rather than substituting a clone of HEAD. Set: A committed stage, an unstaged
      edit to that stage, a staged-only file, and an untracked sentinel in each checkout shape.
      Completeness: Compare the copied stage and sentinels with the source and compare index
      contents; drive a real clone as a paired negative control for both shapes. Falsifier:
      Replace the working-tree copy with a clone of HEAD and the copy-fidelity row must fail.
    falsified_by: >
      Replace the working-tree copy with a clone of HEAD and the copy-fidelity row must fail.
  - id: AC3
    text: >
      Claim: The sandbox no-write observation includes resolved private and common git stores
      even when those stores are outside the working tree; the live observation covers only
      this checkout's working tree and private git state, excluding sibling-owned shared data.
      Set: The sandbox and live-tree inventories in VELDO-0007 AC4, with primary and linked git
      layouts. Completeness: Inventory all three sandbox roots and plant writes in the private
      directory and common store in disposable fixtures; require each write to appear in the
      changed entries and a clean control to stay unchanged. Drive sibling staging during the
      live observation and require it to stay green, while a real stage write into the copied
      common store reds the sandbox row. Falsifier: Inventory only the working tree and the
      linked metadata-write row must fail; restore shared live inventory and sibling staging
      must red the live row.
    falsified_by: >
      Inventory only the working tree and the linked metadata-write row must fail.
  - id: AC4
    text: >
      Claim: Proof demonstrates full green gates in this linked worktree and a disposable
      primary checkout of the same implementation commit, with the regression controls driven.
      Set: Both full gate invocations, all three declared code mutations, and the suite-wide
      search for sibling .git directory assumptions. Completeness: Record commands, commit,
      exit codes, counts, and failing mutation rows in proof/VELDO-0099; map every criterion in
      its manifest and distinguish diagnostics from full gate evidence. Falsifier: Restore the
      original shape assertion in a disposable linked fixture and the recorded baseline must
      show the named VELDO-0007 AC4 row red.
    falsified_by: >
      Restore the original shape assertion in a disposable linked fixture and the recorded
      baseline must show the named VELDO-0007 AC4 row red.
required_evidence: [unit, integration]
rollback: Revert the suite changes and regenerate the index; retain historical proof and event records.
---

## Intent

Remove a live-state pin on checkout shape without weakening the observation of what the
install-and-run stage executes or where it writes.

## Context

On 2026-09-16, b4a1d19 passed in the primary checkout but reported 4807 passed and one failed
in a linked worktree. The failing VELDO-0007 AC4 row requires .git to be a directory. The
_range_specs comment in .veldo/policy_check.py describes the same class: byte-identical code
must not get different gate decisions merely because it is checked out as a linked worktree.

The sibling sandbox and live-tree inventories implicitly treat .git as embedded metadata.
Copying a linked pointer verbatim also points the observation outside its sandbox. Resolve
and copy the necessary metadata, then inventory the resolved roots. Engine and pack files
are outside this defect's footprint because the affected assertions live only in this suite.

## Out of scope

Independent review, approval, landing, publishing, policy changes, and changes to existing
branches or worktrees other than this task branch. Shape fixtures are disposable repositories.

## Notes

Keep the specification ready pending independent review. No implementation self-approval is
part of this work. Full gate output is evidence; selected suite runs are diagnostics only.

The initial draft used VELDO-0023, the next number after specs/. Contract validation
revealed that PLAN-0019 reserves VELDO-0023 through VELDO-0098 for uncreated work.
This standalone item therefore uses VELDO-0099, the first unreserved ID, leaving the
plan and its reservations intact. The ready check is repeated after renumbering.

Review correction: shared live metadata is not attributable to this stage. The sandbox
still inventories every resolved root; the live inventory excludes shared objects, refs,
and sibling indexes. For a primary checkout, private HEAD, index, and operation state
are selected from the otherwise shared .git directory. Disposable sibling staging and
private-state writes exercise both layouts. This corrects AC3's attribution boundary
without dropping the original sandbox metadata-write controls.
