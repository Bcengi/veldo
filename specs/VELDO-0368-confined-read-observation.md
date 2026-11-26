---
schema: veldo.spec/v1
id: VELDO-0368
title: Record file reads inside the sandbox without a tracer
status: draft
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0367, VELDO-0210, VELDO-0208]
placement: [enforcement]
protected_paths:
  - scripts/agent_sandbox.py
  - engine/scripts/agent_sandbox.py
  - scripts/confined_reads.py
  - engine/scripts/confined_reads.py
  - scripts/mutation_observer.py
  - engine/scripts/mutation_observer.py
  - scripts/reuse_worker.py
  - engine/scripts/reuse_worker.py
  - scripts/case_reuse.py
  - engine/scripts/case_reuse.py
  - scripts/gate_legs.py
  - engine/scripts/gate_legs.py
  - scripts/gate_changes.py
  - engine/scripts/gate_changes.py
  - scripts/gate_execution.py
  - engine/scripts/gate_execution.py
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - scripts/suites/shared.py
  - .veldo/policy.yaml
  - engine/.veldo/policy.yaml
footprint:
  - scripts/agent_sandbox.py
  - engine/scripts/agent_sandbox.py
  - scripts/confined_reads.py
  - engine/scripts/confined_reads.py
  - scripts/mutation_observer.py
  - engine/scripts/mutation_observer.py
  - scripts/reuse_worker.py
  - engine/scripts/reuse_worker.py
  - scripts/case_reuse.py
  - engine/scripts/case_reuse.py
  - scripts/gate_legs.py
  - engine/scripts/gate_legs.py
  - scripts/gate_changes.py
  - engine/scripts/gate_changes.py
  - scripts/gate_execution.py
  - engine/scripts/gate_execution.py
  - scripts/suites/shared.py
  - scripts/suites/*0368*.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - scripts/check_teeth_mutations.py
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - .veldo/policy.yaml
  - engine/.veldo/policy.yaml
  - .veldo/init_scaffold.py
  - engine/.veldo/init_scaffold.py
  - specs/VELDO-0368-confined-read-observation.md
  - proof/VELDO-0368/*
behavior_bearing: true
observability:
  logs: Name the item, observer version, coverage state and first reason coverage became unknown.
  metrics: Notification counts by syscall, service time, worker elapsed time, memory use and newly reusable items.
  traces: Authority certificates bind the dependency digest to the launch, listener and completed process tree.
  error_taxonomy: Missing coverage runs the item again; observer failure cannot issue a complete certificate.
acceptance_criteria:
  - id: AC1
    text: >
      A native file reader starts through worker_tree with TracerPid zero and one combined
      notification listener. The AC7 traced-launch refusal and confinement denials still hold.
      The same fixture runs through the gate profile and both repository script copies.
    falsified_by: Skip tracer_problem in agent_sandbox.py; the traced-worker refusal fixture must fail.
  - id: AC2
    text: >
      Focused native fixtures cover every syscall family in this spec, inherited descriptors,
      failed probes, directory discovery and implicit executable inputs. Each input appears
      in the dependency record or the entire item stays unknown with a specific reason.
    falsified_by: Omit statx in confined_reads.py; the stat-only dependency fixture must fail.
  - id: AC3
    text: >
      Relative paths, directory descriptors, intermediate symlinks, missing components,
      renamed directories and namespace roots produce correct dependencies or unknown.
      An addition at a previously missing component selects the item again.
    falsified_by: Resolve relative paths against the supervisor cwd; the foreign-dirfd fixture must fail.
  - id: AC4
    text: >
      A shared argument buffer, shared cwd, shared descriptor table and concurrent symlink
      replacement each prevent certification. Ordinary independent fork children remain
      observable through exec, double fork and reparenting. Thread creation stays unknown
      under the initial certification rules even when sampled arguments look unchanged.
    falsified_by: Certify after CLONE_VM in confined_reads.py; the swapped-path fixture must fail.
  - id: AC5
    text: >
      Listener loss, receive or send failure, invalid IDs, truncated paths, capacity exhaustion,
      early supervisor exit and missing descendant cleanup each leave incomplete evidence.
      Repeated notifications cannot hide a gap or count a request twice.
    falsified_by: Seal complete after a listener error; the interrupted-observer fixture must fail.
  - id: AC6
    text: >
      Existing seccomp and Landlock denials remain effective. Nested tracer, namespace and
      filter-installation workloads stay unknown. Unknown syscall numbers and unsupported
      executable formats cannot pass through as known empty dependencies.
    falsified_by: Ignore a candidate seccomp installation; the stacked-filter fixture must fail.
  - id: AC7
    text: >
      Only an authority supervisor certificate can establish complete confined coverage.
      Forged worker claims, missing setup coverage, wrong item or commit, stale certificates
      and omitted control observations cannot authorize carry. A dependency edit selects
      a certified item and an unrelated edit carries it through the existing selector.
    falsified_by: Accept the worker complete flag without a certificate; the forged-complete fixture must fail.
  - id: AC8
    text: >
      Paired Linux measurements report wall and CPU cost for three confined suites of
      different shapes, with three repetitions per mode and one generator at a time.
      A historical worker inventory reports the cases and worker seconds still unknown.
      Certification requires a separate demonstration that the threading races are closed.
    falsified_by: Drop notifications after a service-time budget; the budget-exhaustion fixture must fail.
required_evidence: [unit, integration]
rollback: Disable confined certification and retain unknown dependency records. Keep confinement and existing unconfined observation active. Repair with focused fixtures only.
---

## Intent

The measured design provides no new carry eligibility for the historical mutation
inventory. All 2,925 confined or tracing-excluded cases remain unknown, accounting
for 91,034.33 worker-seconds, or 55.01% of all worker time. Keep this spec in draft.
The listener can record calls, but the current certification rules exclude the
mandatory watchdog thread in every confined mutation worker. Product implementation
as a savings feature needs a different way to establish complete observations.

Let the sandbox supervisor supply VELDO-0367 with file dependencies from confined
workers. Use seccomp user notification, which stops a syscall until the supervisor
answers it. Extend the sandbox's existing listener and keep file operations in the
confined task. A complete dependency record requires a supervisor certificate.

This is part 6 of VELDO-0367. AC7 of VELDO-0210 stays intact: `tracer_problem`
still refuses a traced worker-tree entry, and the child profile still denies tracing.
No AppArmor permission, Landlock grant or namespace-helper privilege changes here.
The owner rule remains: no full gates; test only the changed behavior.

The historical mutation measurement contains 2,925 always-run cases out of 4,023,
accounting for 55.01% of mutant-plus-control worker seconds. Of those, 2,874 cases
and 47.89% of worker seconds are confined. The remaining 51 cases and 7.12% are
unconfined tracing exclusions. Those exclusions remain unknown under this spec.
These numbers describe elapsed worker time, including waits. The eligibility
measurement below applies this design's rules to those same workers. Source: the
measurement table in `myday/research/claude-runs/veldo-0367-i45.md`.

## Decision and evidence

The prototype uses one seccomp listener with separate IPC and file-observation handlers.
File observation records attempted dependencies before answering `CONTINUE`.
This keeps the kernel's original permission checks and syscall behavior. It also
requires conservative certification rules: a pathname copied before continuation
can differ from the pathname the kernel consumes. Re-reading it afterward does
not close that race. The [notification API](https://man7.org/linux/man-pages/man2/seccomp_unotify.2.html)
documents this limitation. A general multithreaded read logger based on copying
arguments and continuing calls cannot certify complete observations.

Certification requires stable argument memory, path resolution and descriptor
identities. The measurements show that these restrictions exclude the target
workload. Supporting threads is a prerequisite for useful mutation savings.
Do not weaken these rules to meet a reuse target or replace missing observations
with a dependency on the entire checkout.

The code inspection used main `68b1c45206b7b2efd1a887820834fb99e4f725f6` and
the VELDO-0367 context at `63039fb88` in `change-scoped-i45`. In
`scripts/agent_sandbox.py`, `Handoff.install` already requests `NEW_LISTENER`
and `WAIT_KILLABLE_RECV`. `Broker.attach` duplicates the listener outside the
tree. `Broker._read` reads task memory and `_descriptor` duplicates descriptors.
These operations use kernel ptrace permission checks without attaching a tracer.
Their existence does not establish that every new observation will be permitted.

`confined_agent` installs the worker IPC filter before executing the authority
bootstrap; the bootstrap then installs worker Landlock restrictions. The gate
profile installs its restrictions before exec. `Broker._serve` currently returns
on several errors and creates a daemon thread per request. `Broker._answer`
does not check the response ioctl result. Those behaviors need explicit failure
accounting before this listener can certify observations.

Local inspection on November 26, 2026 found x86_64 Linux `7.0.0-38-generic`,
UID 1000, no effective capabilities, `TracerPid: 0`, an unconfined AppArmor label,
Yama ptrace scope 1 and unprivileged BPF disabled with value 2.
Read-only seccomp queries accepted `USER_NOTIF` and returned notification,
response and syscall-data sizes of 80, 24 and 64 bytes. The Landlock ABI query
returned 8. These establish available interfaces on this host. They do not prove
notification delivery, memory access across the worker profile or pc2 behavior.

The round 2 experiment ran on pc1 through `myday/scripts/remote_run.sh` with
Linux-only node selection. Its paired suite measurements and native watchdog
probe are below. They establish notification delivery and argument inspection
across the worker Landlock layer. They do not establish complete dependencies
or inspection through the full worker-tree namespace and AppArmor path.

Other mechanisms do not supply the required observations:

* Unprivileged fanotify supports a restricted file-handle mode. It cannot request
  permission events or mark a whole mount or filesystem, and another process's
  PID is unavailable in that mode. Its event set does not establish all failed
  lookups or metadata queries. Mapped accesses and recursive mark races add gaps.
  It cannot be the completeness authority. See [fanotify initialization](https://man7.org/linux/man-pages/man2/fanotify_init.2.html)
  and [fanotify limitations](https://man7.org/linux/man-pages/man7/fanotify.7.html).
* Landlock enforces access restrictions. Its audit controls concern denied
  accesses; it offers no complete stream of allowed reads. Keep it as enforcement.
  See [Landlock audit controls](https://docs.kernel.org/userspace-api/landlock.html).
* eBPF tracing requires privileges or host policy beyond this unprivileged
  launcher. This host disables unprivileged BPF, and tracing access has separate
  performance-monitoring permissions. Do not add capabilities or a privileged
  service. See [kernel monitoring permissions](https://docs.kernel.org/admin-guide/perf-security.html).
* Python audit hooks and preload wrappers miss native or direct syscalls.
  Inotify misses failed probes and metadata-only reads. A new FUSE view would
  require routing every input through a different filesystem, controlling its
  caches and eliminating inherited descriptor bypasses. That changes the tested
  filesystem and does not solve this supervisor extension.

## Listener ownership and confinement

Install the combined filter in the single-threaded trusted child before its first
exec of worker code. Keep the existing architecture check and x32 rejection.
Query notification sizes and supported flags at startup. No feature inferred
from a kernel version alone may establish coverage.

Use `Handoff`, including its host PID mapping, to transfer custody to the trusted
launcher outside the confinement. The task closes its listener copy before the
bootstrap runs. Candidate code receives neither a listener nor Store credentials.
Bind the listener to an authority-created item and launch nonce. An environment
variable or worker-supplied path cannot opt a run into complete coverage.
Load the supervisor and its syscall table from the trusted authority, never from
the candidate checkout. Bind their versions to the certificate and dependency
record so editing observation code invalidates its consumers.

Extend `ipc_program` to dispatch file observations through the same listener.
A second listener is not a solution to the existing `EBUSY` nested-domain path.
Preserve strict fallback for nested IPC confinement, but report observation
coverage as unknown. The outer listener may retain useful observations; the
nested launcher cannot certify a separate item from them.

Keep IPC emulation under its existing rules. For file syscalls the observer
copies arguments, records dependencies and continues the original call. It
does not open files for the worker or inject replacement descriptors. An outside
open followed by `ADDFD` would require reproducing the task's Landlock, AppArmor,
credentials, mount view and flags. This spec does not authorize that change.

Existing filter denials take precedence over notifications. Calls denied by the
fixed authority filter cannot read files; retain the filter digest as evidence
for excluding them. A candidate attempt to install another filter through
`seccomp` or `prctl(PR_SET_SECCOMP)` makes the item unknown before continuation.
Stronger actions can hide notifications, and later listeners can supersede a
notification handler. Preserve the kernel's filter precedence and inheritance
rules described in [seccomp filtering](https://docs.kernel.org/userspace-api/seccomp_filter.html).
Only an authority-verified bootstrap sequence may install the expected confinement
filters without setting unknown. Account for its exact filter bytes and the
transition to candidate execution; a worker-supplied phase marker is insufficient.
Changes to mounts, root directories or namespaces outside that trusted sequence
also make the item unknown, including changes through an inherited namespace handle.

Use a reviewed syscall classification for the supported ABI. Every number is
either an observed dependency operation, a stability hazard, a fixed denial or
a reviewed operation with no external input. The default is a notification
that marks the item unknown, then preserves its normal behavior. This prevents
a newly added syscall from silently acquiring an empty dependency set.

## What the supervisor records

A dependency set may contain extra paths. An attempted lookup can affect later
execution even when it fails, so record it without waiting for a success result.
`CONTINUE` supplies no syscall-exit event. Do not invent return values or infer
successful opens from request counts. Record existing candidates in `paths`,
missing candidates in `absent_paths`, and affected directory membership in
`directories`. An uncertain result stays conservative or makes the item unknown.

The syscall classification covers the following operations and their ABI variants:

* `open`, `openat`, `openat2` and `creat`: copy the full path and open options,
  including the sized `open_how` structure. Record even write-only opens because
  their existence checks affect results. Unknown option bits or truncated
  structures mean unknown. Record `O_PATH` handles as possible lookup inputs.
* `stat`, `lstat`, `fstat`, `newfstatat`, `statx`, `statfs` and `fstatfs`: record
  the object or descriptor, including flags that change link following or allow
  an empty pathname. Filesystem properties that lack a stable runtime identity
  make the item unknown.
* `access`, `faccessat`, `faccessat2`, `readlink` and `readlinkat`: record the
  lookup and each relevant symlink. Permission checks require stable mode,
  ownership, ACL and credential inputs or an unknown runtime reason.
* `getdents` and `getdents64`: identify the directory from its descriptor and
  record membership. Additions, removals and renames select the item again.
  Opening a directory can conservatively record membership before enumeration.
* `read`, `pread64`, `readv`, `preadv`, `preadv2`, `sendfile`, `splice` and
  `copy_file_range`: record source descriptors, including those inherited at
  launch. Readable mappings through `mmap` record the whole file at mapping time,
  even before a page fault. Track `mprotect`, `pkey_mprotect`, `mremap` and
  `munmap` so later permission changes cannot hide a file input. Initial mappings
  and executable images require an authority inventory.
* `execve` and `execveat`: record the executable, its symlink chain and any
  descriptor form, including `AT_EMPTY_PATH`. Account for the kernel's implicit
  shebang interpreter and ELF `PT_INTERP` reads. The initial format decoder
  supports reviewed ELF and shebang forms with bounded recursion. Unaccounted
  binary-format handlers, loaders or unreadable headers make the item unknown.
  Dynamic library opens are observed normally.
* `rename`, `renameat`, `renameat2`, `unlink`, `unlinkat`, `rmdir`, `link`,
  `linkat`, `symlink`, `symlinkat`, `mkdir`, `mkdirat`, `mknod` and `mknodat`:
  record source and destination lookups and parent membership. An attempted
  mutation also triggers the stability rules. Permission and ownership changes,
  timestamps, truncation and file writes belong to that mutation classification.
* Extended-attribute queries, `getcwd`, descriptor duplication and transfer,
  `chdir`, `fchdir`, `close`, `close_range` and relevant `fcntl` commands:
  account for their inputs or state changes. Unknown device `ioctl` commands,
  file-handle opens and unclassified filesystem interfaces make the item unknown.

Keep io_uring and the existing asynchronous alternatives denied. Review legacy
AIO, shared memory and descriptor-receiving calls explicitly. A preexisting
asynchronous request or an unexplained inherited handle makes launch coverage
unknown. Network, service and process-state inputs retain VELDO-0367's unknown
rules. File observation cannot erase an external-input reason. Brokered IPC
operations must contribute their own dependency or unknown evidence because
their syscalls execute outside the worker.

## Paths and stability

Resolve in the requesting task's filesystem view. An absolute path starts at
its root; a relative path starts at its cwd for `AT_FDCWD`, otherwise at its
directory descriptor. Pin the task identity and relevant root or directory
objects while reading. Account for host and namespace PID differences, mount
identity and task exit. Never use the supervisor's cwd or normalize away `..`
before walking symlinks.

Record every symlink component and resolved target, including an intermediate
link outside the repository. Respect no-follow flags, trailing slashes, empty
paths and `openat2` resolution restrictions. A failed lookup records its first
missing component and enough parent membership to detect its later creation.
Raw path bytes need a lossless representation. Deleted, disconnected or magic
links that cannot be tied to stable input identities make the item unknown.
Mapping a worker checkout path to a repository path uses authority-established
root identity, never a string prefix alone. External targets belong in the
runtime dependency inventory and must be revalidated before carry.

Notification IDs identify live requests, not immutable arguments. The supervisor
checks ID validity around argument reads and before responding. This prevents
using a stale request but does not stop another thread from changing memory.
The [kernel notification definitions](https://raw.githubusercontent.com/torvalds/linux/master/include/uapi/linux/seccomp.h)
make the distinction explicit. The following are certification requirements:

1. The authority starts with known descriptors and mappings and observes from
   before candidate execution. All initial readable regular files and mappings
   become dependencies. Opaque descriptors, shared argument memory and unknown
   preexisting state make the item unknown.
2. Each certified task has its own address space, cwd state and descriptor table.
   Intercept `clone`, `clone3`, `fork` and `vfork`. Any attempt to share memory,
   filesystem state or descriptors makes the item unknown before it proceeds.
   This includes threads and `vfork`, even if the attempted call later fails.
   Writable shared mappings, shared-memory attachment and unmodeled memory
   writers do the same. Merely sampling one thread in `/proc` is insufficient.
3. Repository and runtime inputs remain immutable for the observation interval
   under authority custody. Read-only mounts or equivalent enforced isolation
   must establish that property, including aliases and external symlink targets.
   A clean status or matching hashes at the beginning and end cannot rule out a
   temporary change. If the launch cannot establish custody, it stays unknown.
   Existing writable fixture grants do not establish input custody. An authority
   may prepare a private input snapshot before launch, record its source dependencies
   and exclude writers from that copy. Mutant content must be fixed in that snapshot
   before observation starts. Preserve expected path semantics; no new helper
   privilege or silently substituted runtime is authorized here.
4. Private generated files are usable only when the authority knows their initial
   state and their producers' dependencies. A single task may change its private
   files between observations. With multiple live tasks, an attempted filesystem
   mutation that could affect another task's lookup makes the whole item unknown.
   The first implementation may conservatively treat every such mutation as a
   hazard. External writers or shared writable input files always mean unknown.
5. Read task state at each request, including descriptor identity and cwd. A
   prior `chdir` request does not prove that the change succeeded. Without shared
   state, a task blocked in notification cannot change its own path arguments or
   descriptor table. Signal cancellation, unreadable memory, unsupported exec
   behavior or any failure to establish that premise leaves the item unknown.

These rules support independent fork children reading stable inputs. They do
not claim complete observation for arbitrary threads or mutable shared trees.
Adding that support requires a separate design and race fixtures. Freezing a
tree while copying arguments and then unfreezing it before `CONTINUE` leaves
the same gap. A general syscall emulator would be a separate confinement project.

## Measured eligibility and the threading limit

The current design leaves 100% of the target cases and worker time unknown.
The table uses the same receipt as VELDO-0367: admissions JSON at line 44525 of
`myday/research/gate-stamps/cand-1122-55b511908-verify.log`. The source method is
`proof/VELDO-0367/measure-confinement.py` on branch `veldo-0367-i45`, read from
`/home/dmitry/projects/veldo-worktrees/change-scoped-i45`. The extension in
`proof/VELDO-0368/measure-eligibility.py` reconciles all 4,023 case registrations
and 5,495 worker outcomes. It uses each worker's actual leg and the unchanged
tracing exclusions. It counts each control by its own suite and leg once.

| Reason still unknown | Cases | Controls | Mutant seconds | Control seconds | Share of target worker time | Share of all worker time |
| :- | :-: | :-: | :-: | :-: | :-: | :-: |
| Mandatory confined-worker watchdog thread | 2,874 | 1,000 | 57,707.38 | 21,543.91 | 87.06% | 47.89% |
| Unconfined tracing exclusions | 51 | 32 | 4,845.66 | 6,937.38 | 12.94% | 7.12% |
| Total still unknown | 2,925 | 1,032 | 62,553.04 | 28,481.29 | 100.00% | 55.01% |
| Newly carry-eligible under this design | 0 | 0 | 0.00 | 0.00 | 0.00% | 0.00% |

This is a classification of measured worker time using an unconditional code
path, not a replay of historical syscall traces. At receipt commit `55b511908`,
the coordinator launches `reuse_worker.py`, which calls
`mutation_observer.worker`. Before the shared preamble or suite fragment runs,
that function calls `faulthandler.dump_traceback_later`. Python implements this
timer with a native watchdog thread, as its
[documentation](https://docs.python.org/3.12/library/faulthandler.html#dumping-the-tracebacks-after-a-timeout)
states. The call also remains in the i45 observer. The separate selftest path
starts this native timer and a Python progress-watchdog thread.

All 148 confined suites therefore encounter a sharing attempt before their
ordinary rows. Every confined case maps to both confined controls in the receipt.
Even a mutant that removes a timer cannot remove the thread from its required
baseline and no-op observations. The spec unions those observations, so the
combined item stays unknown. This conclusion does not depend on whether an
individual suite starts more threads or whether a sharing attempt succeeds.

A confined pc1 probe confirms the native behavior: one call to
`dump_traceback_later` changed the task count from one to two in both modes.
The listener recorded `clone3` flags `0x3d0f00`, including `CLONE_VM`,
`CLONE_FS`, `CLONE_FILES` and `CLONE_THREAD`. TracerPid stayed zero and the
write-denial probe passed. `proof/VELDO-0368/watchdog-probe.json` contains the
results. The eligibility JSON records the receipt and source hashes and all
148 suite totals. Reproduce the classification with
`python3 -B proof/VELDO-0368/measure-eligibility.py`; it launches no workers.

Shared filesystem mutations, unresolved paths, external inputs and nested
sandboxes can add reasons to these already unknown cases. They add zero cases
to the union because the thread rule has excluded every confined case first.
The receipt contains no syscall histories from which to count those overlapping
reasons separately. Removing the watchdog exclusion alone would not establish
that the remaining 87.06% of target worker time could be certified.

A notification identifies the requesting tid, but that identity does not freeze
the task's shared state. Suppose thread A calls `openat` with a pointer to `a`.
The supervisor copies `a`. Thread B then overwrites the buffer with `b` using
ordinary memory stores. The kernel can open `b` after `CONTINUE` without any
notification for the buffer change. A second sample can miss a change back to
`a`. Immutable input files do not prevent choosing a different immutable file.
The [kernel API warning](https://raw.githubusercontent.com/torvalds/linux/master/include/uapi/linux/seccomp.h)
describes this argument race.

Shared cwd and fd tables have another problem. Reading `/proc/<tid>/cwd` or
`/proc/<tid>/fd` gives the supervisor a view at inspection time. A sibling can
finish `chdir`, replace an fd with `dup2`, close and reuse an fd, or rename a
directory before the continued syscall resolves its path. Pinning the observed
object protects that observer handle; it does not make the kernel use that
handle for the worker's numeric fd. A correct design must keep the relevant
state stable until the kernel has consumed it.

Serializing notifications cannot provide that interval: `CONTINUE` has no
syscall-exit acknowledgment. Allowing the next queued state change immediately
can race with the continued lookup. Holding siblings until completion requires
a reliable completion event and must handle calls that wait for those siblings.
Freezing and then releasing the whole tree leaves the same gap. A Python lock
does not constrain native code, direct syscalls or candidate memory writes.
Labeling a thread as the trusted watchdog also cannot protect its shared
address space from candidate code running in the same process.

This spec therefore does not certify multithreaded processes. Doing so with
unchanged worker semantics needs observation of the objects consumed in the
kernel, or confinement-preserving syscall execution from stable arguments with
reliable completion. The former is unavailable through this unprivileged
notification API. The latter requires substantially more than continuing the
original call. Opening files outside the worker and injecting descriptors would
also require reproducing its Landlock, AppArmor, credentials and filesystem
view, which the existing constraints prohibit. These are limits of this
mechanism and scope, not evidence that all possible observers must fail.

The expected newly eligible share is zero. The target of making most of the
55.01% eligible is unmet. A replacement must demonstrate complete observation
with threads, shared cwd and fd tables, and concurrent generated-file activity
before claiming savings. It must then classify the same inventory and show
more than 45,517.17 of its 91,034.33 target worker-seconds eligible. The existing
44.99% tracing-compatible share retains its own completeness requirements.

## Children, failures and the certificate

Filters follow descendants across fork and exec. Keep observation active until
the namespace init or existing subreaper has finished descendant cleanup.
An early parent exit, a double fork or `setsid` cannot end observation. Use task
identities that include lifetime and namespace information; a reused PID is not
the same task. Unresolved membership or an unaccounted interval means unknown.

The supervisor starts each item as incomplete. Its journal accounts for received
requests, responses, canceled IDs and terminal failures. IDs need not be consecutive;
sequence numbers assigned by the supervisor detect journal gaps, not unseen
kernel events. Seccomp blocks the caller rather than providing a lossy audit ring,
but transport failure, unhandled cancellation and lost application records still
invalidate completeness. Handle `EINTR` retries explicitly. Initially, an invalid
ID or `ENOENT` cancellation conservatively makes the item unknown.

Use a bounded service queue with backpressure and checked response results.
Do not retain the current unbounded thread-per-request pattern for file traffic.
Capacity exhaustion makes the item unknown before any observation is discarded.
After coverage is lost, a functioning supervisor can continue file requests while
retaining the unknown reason. It must still enforce IPC policy. A dead supervisor
or unusable listener terminates and cleans up the tree through existing custody.
Do not reinterpret changed worker results as passing after such a failure.

Only seal a certificate after the worker result, journal settlement and descendant
cleanup are complete. Include the observer schema and code digest, ABI and filter
digest, launch nonce, item identity, observed commit, input-root identities,
runtime digest, request accounting, dependency digest, cleanup outcome and unknown
reasons. Store it through the authority's existing authenticated Store. The
certificate is evidence for one launch, never a reusable capability held by a worker.

## Joining VELDO-0367

Keep the dependency fields `item_id`, `observed_commit`, `paths`, `directories`,
`absent_paths`, `runtime_digest`, `complete`, `unknown_reason` and `record_digest`.
Add a versioned authority observation envelope naming the backend and certificate
digest. Old dependency records do not acquire confined certification retroactively.

Extend `mutation_observer.native_dependency` to consume validated supervisor
evidence as well as the existing authority strace evidence. Python observations
can add paths and attribution. They cannot establish completeness or remove a
reason the supervisor reported. Validate item identity as well as commit and
launch identity before combining sources.

The complete item includes authority setup, fixture preparation and bootstrap
reads before the listener boundary. Record those through the existing authority
observer or explicit immutable authority inputs with their own coverage evidence.
For a confined launch, keep any authority tracer off the process entering
`worker_tree`; launching that entry under strace would still violate AC7.
There must be a checked handoff between setup observation and the sandbox
certificate. Missing setup coverage keeps the whole item unknown.

Combine baseline, no-op and mutant dependencies. Keep shared control identities
and fixture groups from VELDO-0367. A row-only run unions its new observations
with the prior full-suite dependencies; it cannot shrink that set. A parent stage
unions its own setup and every selected child's evidence. Any required incomplete
piece leaves the combined record incomplete. Atomically publish dependencies,
certificate references and results after cleanup through the existing Store.

Keep `case_trace.compatible` and the unconfined declarations unchanged. A separate
authority decision selects this backend only for ordinary confined launches.
Existing exclusions naming ptrace, strace, namespace or confinement workloads
stay unknown. At runtime, a nested sandbox or candidate filter installation also
sets unknown. Do not relabel an excluded unconfined case as confined to make it
eligible. `complete: true` requires both the certificate and all existing
VELDO-0367 conditions; a green execution may still have unknown dependencies.

## Measured recording cost

The prototype added 51.8% to 165.4% to median wall time on three confined suites.
These are recording costs, not measurements of a complete certifying observer.
The experiment ran on November 26, 2026, on pc1, Linux `7.0.0-38-generic`,
x86_64, with system Python 3.12.3. The remote wrapper selected pc1 in exclusive
mode; Linux-only selection excluded the Mac. The one-minute host load ranged
from 1.37 to 1.75. Scheduling used the wrapper's nice 19 and idle IO priority.

The disposable prototype is `.local/0368/prototype.py`. It imports the existing
`agent_sandbox` and extends its IPC filter in memory with file and state-change
notifications. It uses one serial file handler instead of creating a thread
for each file request. Each event records the notification ID, tid, syscall
number and arguments. Path calls also copy pathname bytes and record the
requesting task's root and relative-path base. Descriptor operations record
the target in that task's fd table. The handler reads `open_how` and `clone3`
flags, checks IDs and responses, writes a buffered JSON journal, and answers
`CONTINUE`. Existing IPC handling and fixed denials remain in place.

Both modes run the unmodified suite through `fork_gate_domain`,
`mutation_sandbox.worker_grants` and `landlock` with the worker profile. The
checkout and runtime are readable; only the private scratch is writable.
Observation off retains the existing IPC listener. Observation on adds the file
notifications to that same listener. This exercises the production confinement
functions but does not run the outer worker-tree namespace launcher. The
prototype is uncommitted experiment code and cannot issue certificates.

The suites have different measured shapes:

* IO: `108_veldo_0153_executor_profile` copies the installation's Python files
  into fixtures. Each observed run made 1,200 `sendfile` attempts and nine
  `vfork` attempts. It passed 33 assertions including the shared preamble.
* Process: `15_warp_1405_reconciliation` runs the metrics report over the
  repository corpus. Each observed run made 578 `vfork` attempts. It passed
  87 assertions including the shared preamble.
* Typical small Python suite: `61_scope_covers` loads membership code and checks
  scope matching. Each observed run made two `vfork` attempts and passed 29
  assertions including the shared preamble. It represents this common suite
  structure; it is not a statistical estimate of the average mutation worker.

Each suite ran three times per mode, in paired order off/on, on/off, off/on.
Only one suite ran at a time. Earlier smoke pairs warmed the suites; these are
warm-cache results. Each repetition used new scratch directories. Wall time
starts before the confined fork and ends after the worker and broker cleanup.
CPU seconds sum the supervisor's process CPU and the change in
`RUSAGE_CHILDREN` after cleanup. That includes user and system CPU for the
worker, its waited descendants and the existing bind helper. Repository clone,
environment setup and result serialization are outside the interval.

| Suite and repetition | Wall off, s | Wall on, s | CPU off, s | CPU on, s | File and state notifications |
| :- | :-: | :-: | :-: | :-: | :-: |
| IO 1 | 0.251456 | 0.595364 | 0.252383 | 0.544153 | 16,101 |
| IO 2 | 0.251740 | 0.606951 | 0.251879 | 0.604021 | 16,115 |
| IO 3 | 0.241142 | 0.637188 | 0.241612 | 0.630063 | 16,103 |
| Process 1 | 2.498400 | 6.694840 | 2.519951 | 6.642408 | 197,717 |
| Process 2 | 2.435083 | 6.509016 | 2.453311 | 6.488484 | 197,727 |
| Process 3 | 2.452422 | 6.287301 | 2.462181 | 6.180808 | 197,732 |
| Typical 1 | 0.160200 | 0.235418 | 0.160808 | 0.230246 | 3,312 |
| Typical 2 | 0.155556 | 0.243135 | 0.156019 | 0.243905 | 3,312 |
| Typical 3 | 0.162774 | 0.252504 | 0.162679 | 0.252535 | 3,314 |

| Suite | Median wall off/on, s | Added wall | Median CPU off/on, s | Added CPU | Median supervisor CPU on, s |
| :- | :-: | :-: | :-: | :-: | :-: |
| IO | 0.251456 / 0.606951 | 141.4% | 0.251879 / 0.604021 | 139.8% | 0.297824 |
| Process | 2.452422 / 6.509016 | 165.4% | 2.462181 / 6.488484 | 163.5% | 3.274232 |
| Typical | 0.160200 / 0.243135 | 51.8% | 0.160808 / 0.243905 | 51.7% | 0.073085 |

Percentages compare the mode medians. Added wall time divided by the median
notification count is 22.08, 20.52 and 25.04 microseconds per notification for
IO, process and typical respectively. This includes scheduling and worker
effects; it is not pure handler latency. Maximum observed worker RSS was
34,588, 32,448 and 25,104 KiB respectively. Supervisor maxima were 21,620,
21,400 and 20,836 KiB. These are per-process maxima, not simultaneous tree
memory. The raw repetitions provide the ranges; the JSON also stores them.

All 18 runs returned the expected partial-suite status 2, with zero failed
assertions and matching assertion totals between modes. TracerPid was zero.
An attempted write outside scratch was denied in every run. All observed runs
had zero argument-read or response errors. Output comparison used assertion
totals, failures and status; temporary paths and printed elapsed times differ.
Every run remained unknown. Passing these suites establishes neither complete
dependencies nor the namespace entry's AC7 refusal fixture.

The prototype records every requested syscall family on the reviewed x86_64
list, subject to existing denials. A bootstrap write to its dedicated handoff
fd, allocated at 10,000 or above, is exempt so the listener can be transferred.
An arbitrary later reuse of that fd number is a known coverage hole. Unknown
syscall numbers are not given the spec's future default notification treatment.
The prototype does not walk every symlink component, inventory implicit ELF
or shebang inputs, freeze inputs, close sharing races, or seal certificates.
It therefore measures a subset of the work required by the design. These
numbers cannot serve as an upper bound on the completed observer's cost.

The measured commit is `bcee6b606327ff61028da27e8805f1de4f951c40` and the final
remote run is `rr20261126121302-294a`. Data, syscall counts, source digest,
output digests, CPU components and journal sizes are in
`proof/VELDO-0368/paired-measurements.json`. The local raw outputs are in
`.local/0368/results-3-108_veldo_0153_executor_profile/.local/0368/results.json`.
The prototype and launcher remain under `.local/0368/`; their files were sent
as command data to the clean remote clone. Reproduce the paired run with
`python3 .local/0368/launch.py 3 108_veldo_0153_executor_profile 15_warp_1405_reconciliation 61_scope_covers`.

## Conditions for further implementation

The measurements do not justify enabling this design for mutation savings.
Resolve multithreaded certification and remeasure eligible worker time before
starting the product increments below. Keep the existing certificate and
failure rules as requirements for any replacement. A notification budget must
never silently truncate coverage. Use selected native race fixtures and the
actual worker and gate entries to test the replacement; no full mutation stage
is needed for this decision.

Each increment below is conditional on that revision. A script pair means both `scripts/`
and `engine/scripts/`. Fixtures and registered falsifiers accompany the increment
that changes the behavior. Do not enable certification until increments 1 through
5 have their focused evidence. No increment requests a seed or weekly full run.

1. Add the certificate contract, unknown reasons and syscall classification to
   a new `confined_reads.py` pair, disabled by default. Protect the pair through
   the policy pair and add installation entries. Prove unprivileged listener
   handoff, zero TracerPid, original Landlock denial and the shared-buffer race
   on a Linux compute node. Test unsupported features and malformed certificates. No carry changes.
2. Extend the `agent_sandbox.py` pair with the combined listener, bounded service,
   checked responses and lifecycle journal. Keep certification off. Exercise
   startup failure, listener loss, canceled calls, descendant exit and IPC policy
   with tiny native fixtures. Run the existing targeted AC7 refusal fixtures.
3. Implement path and descriptor observation in the new pair, including implicit
   exec inputs and stability checks. Use one fixture per syscall family and race.
   Prove independent fork coverage and explicit unknown for threads, shared state,
   mutable inputs and unsupported paths. Keep real runs in observation-only mode.
4. Join supervisor evidence through the `mutation_observer.py`, `reuse_worker.py`,
   `case_reuse.py` and `gate_legs.py` pairs and `scripts/suites/shared.py`.
   Extend the `gate_changes.py` and `gate_execution.py` pairs for certificate
   validation and settlement. Test setup handoff, forged claims, shared controls,
   row unions, mismatched identities and missing cleanup. Selection remains unchanged.
5. Repeat the paired Linux measurements and selected worker/gate fixtures. Enable
   certification in a separate small change only for launches satisfying every
   stability rule. Demonstrate dependency-edit execution and unrelated carry on
   a tiny authenticated inventory. Report the newly complete fraction and the
   remaining unknown reasons before claiming savings. If custody or races cannot
   be resolved, retain observation-only mode and narrow the implementation claim.

Immutable runtime custody, inspection across AppArmor and PID namespaces,
implicit executable inputs and complete multithreaded observation remain
unresolved. The focused measurements do not resolve those requirements.
