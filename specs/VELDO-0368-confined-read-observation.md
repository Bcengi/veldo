---
schema: veldo.spec/v1
id: VELDO-0368
title: Record file reads inside the sandbox without a tracer
status: ready
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
      Paired pc2 measurements report the cost and coverage of this observer on small native
      workloads and selected confined fixtures. Output and confinement results match with
      observation off and on. Every build increment uses focused fixtures only.
    falsified_by: Drop notifications after a service-time budget; the budget-exhaustion fixture must fail.
required_evidence: [unit, integration]
rollback: Disable confined certification and retain unknown dependency records. Keep confinement and existing unconfined observation active. Repair with focused fixtures only.
---

## Intent

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
These numbers describe elapsed worker time, including waits. They do not predict
the fraction this observer can certify or its speedup. Source: the measurement
table in `myday/research/claude-runs/veldo-0367-i45.md`.

## Decision and evidence

Choose one seccomp listener with separate IPC and file-observation handlers.
File observation records attempted dependencies before answering `CONTINUE`.
This keeps the kernel's original permission checks and syscall behavior. It also
requires conservative certification rules: a pathname copied before continuation
can differ from the pathname the kernel consumes. Re-reading it afterward does
not close that race. The [notification API](https://man7.org/linux/man-pages/man2/seccomp_unotify.2.html)
documents this limitation. A general multithreaded read logger based on copying
arguments and continuing calls cannot certify complete observations.

The initial implementation certifies only runs whose argument memory, path
resolution and descriptor identities meet the stability rules below. It observes
other runs but leaves them unknown. Supporting arbitrary threads is an open
extension requiring stronger evidence about the objects the kernel used. Do not
weaken these rules to meet a reuse target or replace missing observations with a
dependency on the entire checkout.

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

A small probe was queued through `myday/scripts/remote_run.sh pc2` against the
unchanged main commit. pc2 had an existing exclusive reservation. The request
was canceled after 61 seconds before the probe ran. No overhead was measured,
and no live sandbox observation is claimed by this spec. The first increment
must establish these facts on pc2 before any certification code is enabled.

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

## Cost and build order

The main cost is a supervisor round trip per observed syscall, plus argument and
path inspection. Metadata-heavy Python startup may dominate notification volume.
Cache decoded immutable inputs and deduplicate dependency storage, but observe
every operation needed for coverage. Measure memory and service contention as
well as elapsed time. A notification budget must never silently truncate coverage.

On pc2, compare observation off and on for 2,000 repeated open/read/close
operations, stat and absent-path loops, directory enumeration, file mappings and
small fork trees. Use at least five alternating pairs after warmup. Report raw
counts, medians, ranges, added microseconds per notification, supervisor CPU,
peak memory, worker elapsed time and completion state. Then use selected confined
fixtures through the actual worker and gate entries, with matching exit status,
output and confinement denials. Keep prototype files in temporary directories
and the checked-out repository read-only. No full mutation stage is a benchmark.

Each increment lands independently. A script pair below means both `scripts/`
and `engine/scripts/`. Fixtures and registered falsifiers accompany the increment
that changes the behavior. Do not enable certification until increments 1 through
5 have their focused evidence. No increment requests a seed or weekly full run.

1. Add the certificate contract, unknown reasons and syscall classification to
   a new `confined_reads.py` pair, disabled by default. Protect the pair through
   the policy pair and add installation entries. Prove unprivileged listener
   handoff, zero TracerPid, original Landlock denial and the shared-buffer race
   on pc2. Test unsupported features and malformed certificates. No carry changes.
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
5. Run the paired pc2 measurements and selected worker/gate fixtures. Enable
   certification in a separate small change only for launches satisfying every
   stability rule. Demonstrate dependency-edit execution and unrelated carry on
   a tiny authenticated inventory. Report the newly complete fraction and the
   remaining unknown reasons before claiming savings. If custody or races cannot
   be resolved, retain observation-only mode and narrow the implementation claim.

Open risks are the fraction of existing fixtures that meet the stability rules,
the enforcement of immutable runtime inputs, task inspection across AppArmor and
PID namespaces, implicit executable inputs, and notification service cost. The
kernel queries and code inspection do not resolve those risks. Each has a focused
fixture or measurement above; none can be waived by a clean full gate.
