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
      and require the copied stage, index, private git directory, shared store, worktree,
      config paths, and object alternates to resolve inside the observation sandbox before
      executing the copied stage. Before copying, refuse nested .git files or directories
      below the top level and .gitmodules: record AC4 as STANDS DOWN with the reason
      "nested repository present; the copied observation is not self-contained", never as
      passed. Drive a submodule with an absolute git pointer and an unstaged edit; require
      byte-identical original contents and zero git operations inside nested repositories.
      Skipping detection must red the recorded-stand-down row. Treat only each copied
      object store's info/alternates and info/http-alternates as alternates metadata;
      a branch and reflog named alternates must copy and pass AC4. Matching the basename
      anywhere must red that control. Drive core.worktree pointing at the original dirty checkout
      and require checkout-index in the sandbox to preserve the original edit byte for byte;
      skipping config normalization must red that row. The fixture supplies its own fixed commit identity;
      drive the controls with an empty HOME and no configured identity. Falsifier: Restore the .git is_dir requirement and the
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
      Set: The whole common directory except worktrees/, the copied private directory and working
      tree, and the live checkout-owned inventory in both git layouts, using content digests,
      not timestamps. Completeness: Copy the whole common directory except worktrees/, retaining
      config normalization, alternates materialization and containment assertions. Inventory all
      three sandbox roots using content digests, not timestamps, plus size and existence; plant writes in the private
      directory and common store in disposable fixtures; require each write to appear in the
      changed entries and a clean control to stay unchanged. Drive sibling staging during the
      live observation and require it to stay green, while a real stage write into the copied
      common store reds the sandbox row. Falsifier: Inventory only the working tree and the
      linked metadata-write row must fail; restore shared live inventory and sibling staging
      must red the live row. Include sharedindex.*, pseudorefs, operation state, logs/HEAD,
      private refs, and config.worktree in primary private-state observation. Corrupt a real
      split index base and require its changed entry to be observed. A clean split-index AC4 run
      must pass all 14 rows in both shapes. Stage deletion of a copied branch reflog and of an
      additional file selected randomly per run from the copied common directory must red the
      sandbox-write row; reflog deletion must also red it with a split index. Copy this checkout's
      private state separately, never sibling private state; tolerate entries vanishing
      during traversal. Drive 50 copies per shape during concurrent sibling staging and
      unstaging with zero raises, and a deterministic disappearing-file control.
    falsified_by: >
      Inventory only the working tree and the linked metadata-write row must fail.
  - id: AC4
    text: >
      Claim: Proof demonstrates full green gates in this linked worktree and a disposable
      primary checkout of the same implementation commit, with the regression controls driven.
      Set: Both full gate invocations, all original and review code mutations, and the suite-wide
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

Second review correction: sandbox configs retain only repository storage semantics;
external config includes and execution paths are discarded, git pointer files are rewritten,
and object alternates are copied into the sandbox. Containment is checked before the copied
stage runs. Common-store copies exclude sibling worktree state and tolerate vanished entries.
Primary private-state observation includes split indexes and lowercase operation state.

Third review correction: the write observation's surface is the isolated sandbox
copy, over the working tree, private git directory, and copied common store,
including veldo/ claims and runs and materialized object alternates. C-quoted
alternate entries are decoded as path bytes and rewritten with C quoting after
resolution; malformed quotes and missing alternate directories fail by name. Shared stores
that other worktrees and workers write are deliberately not inventoried live;
their writes are observed only through the sandbox copy, where changes during the
stage run belong to that run. The live inventory covers this checkout's working
tree and private git state, so a sibling heartbeat is not attributed to the stage.

This is a before-and-after inventory of those surfaces, not a trace of the process's
file operations or an operating system confinement boundary. It depends on copy
fidelity and path normalization. It does not establish absence of writes to arbitrary
absolute paths, external working-tree symlink targets, shared live stores, or writes
whose inventoried state is completely restored before the second snapshot. The
separate sandbox HOME inventory does not extend the claim to the host filesystem.

Fourth review correction (round five): the sandbox copies the whole common directory
except worktrees/, with no store allowlist. This includes branch reflogs and unknown
future stores. Config normalization, alternate materialization and containment checks
still apply before the stage runs. Both inventories compare content digests and sizes,
entry kinds, symlink targets and existence, not timestamps. Git's split-index timestamp
refresh is a read for this observation. Identical-byte rewrites, timestamp-only changes,
permission-only changes and writes fully restored before the second snapshot are not
observed. Copying mutable shared state is not an atomic snapshot. The before-and-after
boundary above remains in force; this construction is not a process trace.

Final design closure (round six): this observation is a before-and-after content
inventory of an isolated copy. It stands down when the checkout is not self-contained;
its remaining boundary is as stated above. The follow-up that replaces it is
kernel-enforced write confinement of the stage process using Linux Landlock,
unprivileged, on kernel 5.13 and later, with recorded stand-down on other hosts.
That turns "no writes outside the sandbox" from an inventory into an enforced
property. That follow-up is not implemented here.
