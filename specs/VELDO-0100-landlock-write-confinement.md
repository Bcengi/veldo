---
schema: veldo.spec/v1
id: VELDO-0100
title: Kernel-enforced write confinement for the install-and-run observation
status: draft
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0099]
placement: [enforcement]
protected_paths: []
footprint:
  # stdlib_only_enforcement applies here; ctypes is allowed, third-party Landlock packages are not.
  - "scripts/suites/24_veldo_0007_install_and_run.py"
  - "specs/VELDO-0100-landlock-write-confinement.md"
  - "specs/index.md"
  - "proof/VELDO-0100/*"
behavior_bearing: true
observability:
  logs: Named rows record confinement setup, denied mutations, successful stage completion, and recorded stand-down with its fallback.
  metrics: Record each checkout shape and mutation result, stage exit status, errno, detected ABI, and pass, fail, and stand-down counts separately.
  traces: Bind commands, implementation commit, allowed roots, attempted target paths, and mutation diffs to criterion evidence.
  error_taxonomy: Distinguish unavailable capability, insufficient ABI, setup failure, denied outside write, and unrelated stage failure; only capability limitations stand down.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The install-and-run write-scope observation launches the stage under an
      unprivileged Linux Landlock ruleset before any stage code executes. Write access
      is granted only beneath the sandbox's working-tree copy, HOME, and TMPDIR,
      plus the device nodes enumerated in Notes through file-specific rules;
      never grant the /dev directory. Writes to every other path under /dev are denied.
      Read and execute access elsewhere remain subject to existing host permissions.
      A prohibited write-open fails at the syscall with EACCES, and its propagated
      stage failure makes the confinement row fail. Set: The observed stage and all
      descendants it launches, for the filesystem data operations and ABI coverage
      declared in Notes, in primary and linked checkout shapes. Completeness: Construct
      the ruleset with all required handled write rights denied by default, the three
      fixture root grants, and only the enumerated device file grants. Assert the
      handled-rights mask against the full data-write set for the detected ABI in
      Notes rather than inferring coverage from passing probes. Record successful
      no_new_privs and restrict_self before exec.
      Drive writes beneath each allowed root, an outside read, and outside writes by
      both the stage and a spawned child, plus an EACCES write-open control for
      /dev/zero and the destructive-operation controls in AC2. Record the actual ABI
      and rights mask; do not infer support from a kernel version string.
      Setup failure after a supported
      probe fails the row and never launches an unrestricted substitute. Falsifier:
      Bypass restrict_self and the named confinement-enforcement row must fail because
      the outside-write control succeeds instead of returning EACCES.
    falsified_by: >
      Bypass restrict_self and the confinement-enforcement row must fail when the
      outside-write control succeeds instead of returning EACCES.
  - id: AC2
    text: >
      Claim: A mutant stage attempting a write outside the sandbox fails observably
      for every declared target while the unmodified compose-install-gate stage
      completes. Set: In each checkout shape, independent mutants target an arbitrary
      external file, the original checkout, the caller's global git configuration,
      and the shared git store including its veldo claim ledger and run registry.
      Completeness: Drive the Cartesian product of both shapes and all target classes
      with a separate run for each, so the first denial cannot mask later targets.
      Use disposable caller fixtures with writable external sentinels, a private
      caller HOME, and primary and linked repositories at the same commit. Resolve
      original private and common git paths before copying. Exercise direct absolute
      paths, a symlink from an allowed root to an external sentinel, and an attempted
      write followed by restoration. In both shapes also drive separate denial runs
      for unlink, rmdir, same-directory rename, cross-directory rename, hard link,
      and mkdir outside the allowed roots, using the disposable fixtures in Notes.
      Record EACCES for write-open and the actual denial errno for each operation
      (including EXDEV for rename/link where returned), nonzero stage exit, and the
      named outside-write row failing for every mutant; unchanged sentinels are
      corroboration, not the detector. An unrestricted disposable control must
      demonstrate that each operation can otherwise succeed. For each destructive
      operation, pair its denial with a launcher mutant omitting the corresponding
      handled right as specified in Notes: the operation must succeed and the named
      denial-control row must fail. The clean confined control must exit zero, report
      install-and-run pass, install more than ten files, and run the nested gate.
      Falsifier: Add the disposable external target parent to the write grants and
      the denied-mutation matrix row must fail when its outside write succeeds;
      omit each destructive control's handled right and its denial-control row must
      fail when that operation succeeds.
    falsified_by: >
      Add the disposable external target parent to the write grants and the
      denied-mutation matrix row must fail when its outside write succeeds; omit
      each destructive control's handled right and its denial-control row must
      fail when that operation succeeds.
  - id: AC3
    text: >
      Claim: A host without usable Landlock records the confinement row as STANDS DOWN,
      recorded rather than passed, and retains VELDO-0099's inventory observation.
      Set: Non-Linux hosts, kernels before Landlock, Landlock disabled at build or boot,
      insufficient ABI coverage, and a supported host as the paired control.
      Completeness: Drive each capability branch, including ENOSYS and EOPNOTSUPP,
      and match the exact recorded-stand-down line in Notes, its reason, a recorded
      stand-down entry, and no confinement pass count. Require the inventory branch
      to execute and its existing metadata-write mutant to fail; preserve its own
      recorded stand-down for a non-self-contained checkout without relabeling it a
      pass. Keep independent process and network rows active on every branch. On a
      supported Linux host run real denial controls; simulated capability results
      prove routing only. An unexpected probe or setup error fails by name rather
      than being treated as absence. Falsifier: Return silently on unavailable
      Landlock and the recorded-stand-down row must fail for missing output, missing
      record, and missing inventory fallback.
    falsified_by: >
      Return silently on unavailable Landlock and the recorded-stand-down row must
      fail for missing output, missing record, and missing inventory fallback.
  - id: AC4
    text: >
      Claim: For the confined observation the checkout copy is only isolation and
      current executable input, never the observation surface for the outside-write
      claim; the kernel denial and stage result decide that claim. Set: Every launch
      used by the write-scope observation, its copy preparation, and its decision path
      in both checkout shapes. Completeness: Enumerate these call sites and drive an
      unstaged stage mutation to show that current bytes are executed. Force empty
      before-and-after inventory differences while driving an external-write mutant;
      the confinement row must still fail with EACCES. Copy contents and normalized
      git paths must not substitute for restriction of the process. The supported
      observation must not rerun the stage unconfined against the live checkout.
      Preserve narrower existing repository and HOME immutability assertions as
      separate claims, and retain VELDO-0099's inventory authority only for the
      explicitly recorded fallback in AC3. Falsifier: Replace the confinement
      decision with inventory equality and the copy-isolation-only row must fail
      when empty differences would hide the mutant's denied outside write.
    falsified_by: >
      Replace the confinement decision with inventory equality and the
      copy-isolation-only row must fail for the external-write mutant with empty differences.
required_evidence: [unit, integration]
rollback: Revert the confinement launcher and rows, restore VELDO-0099's inventory observation with its stated limits, and regenerate the index; retain historical proof.
---

## Intent

Turn the install-and-run observation's outside-write claim into a property enforced
at the process boundary. Path inventories cannot answer that question over the host
filesystem. A write denied by the kernel cannot damage the original checkout before
a later comparison notices it.

This is a draft specification only. Implementation, proof, independent review, and
promotion are future work. High risk reflects that an incorrect confinement claim
can conceal writes to source, git configuration, and shared repository state.

## Context

VELDO-0099 repaired checkout copying and git resolution through nine independent
review rounds. Those rounds found redirection and omitted-state classes involving
worktree pointers, core.worktree, alternates, sibling state, the claim ledger,
reflogs, submodule pointers, a branch named alternates, split-index timestamps,
sockets, repeated identical writes, global git configuration written by the live
rerun, and symlink cycles. Two classes could lose data in the original checkout.
Its Notes explicitly name Landlock as the follow-up.

The footprint centers on scripts/suites/24_veldo_0007_install_and_run.py, the suite
VELDO-0099 changes. The architecture's stdlib_only_enforcement rule applies to the
launcher and controls: Python ctypes calling Landlock syscalls is acceptable;
a third-party Landlock package is not. No engine or pack change is needed for this
repository-local observation. The real stage remains scripts/check_install_and_run.py.

## Out of scope

Implementation during this draft, proof production, ready promotion, changes to
VELDO-0099, changes to the stage's product behavior, new package dependencies,
engine or pack changes, policy changes, landing, publishing, and changes to other
branches or existing worktrees. All destructive controls use disposable fixtures;
the actual caller's checkout, global configuration, and shared store are never
mutation targets.

## Notes

The boundary this closes is VELDO-0099's dependence on copy fidelity and path
normalization for a before-and-after inventory. That observation cannot establish
absence of writes to arbitrary absolute paths, external working-tree symlink
targets, shared live stores, or writes whose complete inventoried state is restored
before the second snapshot. Its sandbox HOME inventory does not extend the claim
to the host filesystem. Landlock closes that boundary for the mediated operations
of the confined process tree, including attempted identical-byte writes, regardless
of whether a snapshot would change. It does not turn the copy into a process trace.

The three writable roots must be fresh directories owned by the fixture, with all
copied private and common git storage beneath the working-tree copy. Copy bytes,
not hard links to original files; never grant the sandbox parent, the caller's
HOME, the original checkout, or a live shared store. Retain VELDO-0099's copy
safety checks. Confinement begins after trusted copy preparation, which remains
outside the stage's claim. A bad copy can still corrupt state during preparation;
this specification does not certify the copier as kernel-confined.

The complete device write exception set is:

| Device | File-specific grant | Reason |
|---|---|---|
| /dev/null | WRITE_FILE | The publisher's git ls-files opens it for reading and writing, and the nested gate opens it for shell output redirections. |

The independent review's disposable clean run passed with this single device
exception. No other device write grant is justified. Reads remain governed by host
permissions. Grant the device itself, never /dev or an ancestor, and require the
clean compose-install-gate run to pass with exactly this exception set. A write-open
to /dev/zero must fail with EACCES under confinement and succeed in an unrestricted
control; this harmless sink needs no persistent data mutation. Any other path under
/dev remains outside the write grants. A mutant granting WRITE_FILE on /dev must
make this denial-control row fail because the /dev/zero write-open succeeds.

For supported runs, the copy remains only isolation, never the observation surface
for confinement. Inventories may corroborate fixture integrity or enforce separate
in-sandbox immutability claims. They cannot decide that no outside write occurred.
The AC3 fallback deliberately retains the old inventory observation and its limits.

The full filesystem data-write set is LANDLOCK_ACCESS_FS_WRITE_FILE, REMOVE_DIR,
REMOVE_FILE, MAKE_CHAR, MAKE_DIR, MAKE_REG, MAKE_SOCK, MAKE_FIFO, MAKE_BLOCK, and
MAKE_SYM (all names use the LANDLOCK_ACCESS_FS_ prefix), plus REFER on ABI 2 or
later and TRUNCATE on ABI 3 or later. Assert the launcher's handled-rights mask
against this enumerated set for the detected ABI, independently of its grant mask
and of observed denials. These rights cover write-open, creation, removal, and
rename/link operations, plus truncation where supported. Device ioctl operations
are outside this data-write claim. Apply no_new_privs and Landlock in a fresh
single-threaded launcher before exec; descendants inherit it.
Reads and execution elsewhere are not newly restricted. These choices follow the
[Linux 6.2 Landlock interface](https://docs.kernel.org/6.2/userspace-api/landlock.html).

Linux 5.13 introduced Landlock, but availability must be probed. ABI 1 and 2 cannot
restrict truncate; ABI 1 also denies cross-directory reparenting. Thus "kernel
5.13 and later" is the probe range, not evidence of complete write coverage.
Apply available confinement there, record its partial coverage, and stand down
the full data-write claim with the inventory fallback when ABI is below 3.
Never silently omit TRUNCATE and report full confinement. Drive a truncate-only
control on ABI 3 or later as well as the write-open controls. This qualification
is necessary for a truthful draft of the proposed 5.13 baseline.
The [ABI documentation](https://docs.kernel.org/6.2/userspace-api/landlock.html#landlock-abi-versions)
and [kernel support requirements](https://docs.kernel.org/userspace-api/landlock.html#kernel-support)
define the capability boundary.

Destructive controls use fresh external files and directories owned by the fixture,
including source-file and claim-record sentinels for unlink. Prepare empty
directories for rmdir and absent destination names for rename, link, and mkdir.
Keep rename and hard-link operands on the same filesystem so an unrestricted
success excludes an unrelated EXDEV. Run every operation independently in both
checkout shapes; a denial of one operation must not skip any other operation.

| Denial control outside the allowed roots | Handled right omitted by its launcher mutant |
|---|---|
| Unlink a regular file | REMOVE_FILE |
| Remove an empty directory with rmdir | REMOVE_DIR |
| Rename a regular file within one directory | REMOVE_FILE |
| Rename a regular file across directories | REMOVE_FILE |
| Hard-link a regular file to an absent name | MAKE_REG |
| Create a directory with mkdir | MAKE_DIR |

First run each control under the exact AC1 grants. Then isolate the table's right
in a separate sensitivity pair: narrowly grant other prerequisites on disposable
external fixture directories only, keeping the tested right denied. For rename,
grant MAKE_REG at the destination; for cross-directory rename also grant REFER at
both parents and keep their other rights equal to avoid a gain of access. Use a
same-directory hard link to isolate MAKE_REG. The handled-right variant must deny;
its otherwise identical mutant removes only the tested right from the handled mask
and from any rule masks and must succeed, making the denial-control row fail.
These auxiliary grants belong only to the sensitivity controls, never the clean
stage or the AC1 confinement launcher. Record both masks, grants, errno, and result.

Accept EACCES for the destructive denials and EXDEV for rename/link when returned
by Landlock, recording the actual errno; any other error is a failed control.
REFER is exceptional: omitting it still denies reparenting, so omission alone is
not a success mutant for cross-directory rename. The mask assertion covers REFER
explicitly, while the isolated REMOVE_FILE mutant proves rename-control sensitivity.
See the kernel's [filesystem rights](https://docs.kernel.org/userspace-api/landlock.html#filesystem-flags).

Use the existing suite's exact recorded-stand-down wording, with a distinct row:

```text
   VELDO-0100: AC1 STANDS DOWN, recorded rather than passed: <reason>.
```

Record the row and reason as well as printing it, and identify VELDO-0099's
inventory as the remaining observation. Reasons distinguish non-Linux, ENOSYS,
EOPNOTSUPP, and insufficient ABI. A missing capability does not excuse a failed
supported setup. Nested-repository fallback retains its existing wording:

```text
   VELDO-0007: AC4 STANDS DOWN, recorded rather than passed: nested repository present; the copied observation is not self-contained.
```

This is filesystem confinement, not network confinement. It cannot see writes
performed by an existing helper outside the ruleset, including requests over IPC.
Already-open or externally supplied writable file descriptors are another boundary;
close inherited file descriptors except controlled standard streams, using pipes
for output rather than caller-owned files. Metadata operations such as chmod,
chown, timestamps, and extended attributes are not covered by this data-write
claim. See the kernel's [filesystem limitations](https://docs.kernel.org/userspace-api/landlock.html#filesystem-flags)
and [file descriptor rules](https://docs.kernel.org/userspace-api/landlock.html#rights-associated-with-file-descriptors).

The launcher does not produce a syscall trace. A stage can catch EACCES and return
zero: the write remains prevented, but that suppressed attempt is not reported by
exit status alone. The required mutants propagate their denial and must fail the
stage; no claim is made to detect every caught attempt. Rename/link refusals may
use EXDEV rather than EACCES, so exact EACCES assertions target write-open probes.
Writes inside the three allowed roots and the enumerated device write exception
are permitted by confinement; unchanged repository or HOME contents remain separate
assertions. Other suite invocations,
unconfined fallback runs, external processes, and interrupted-run cleanup are
outside this confined observation's guarantee. Existing network and process rows
remain active and retain their own, narrower meanings.
