---
schema: veldo.spec/v1
id: VELDO-0208
title: Single-user agent confinement permits authenticated landing reuse
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0205, VELDO-0207]
placement: [enforcement]
protected_paths: ["scripts/gate_candidate.py", "scripts/reuse_worker.py", "scripts/mutation_observer.py", "scripts/mutation_ownership.py", "engine/scripts/mutation_ownership.py", ".veldo/candidate_git.py", "engine/.veldo/candidate_git.py", "engine/scripts/agent_sandbox.py", "engine/scripts/agent_sandbox.json", "engine/scripts/mutation_sandbox.py", "engine/scripts/gate_candidate.py", "engine/scripts/reuse_worker.py", "engine/scripts/mutation_observer.py", "engine/scripts/check_gate_mutations.py", "engine/scripts/case_reuse.py", "engine/scripts/case_inputs.py", "engine/scripts/case_trace.py", "engine/scripts/mutation_reuse.py", "engine/scripts/gate_reuse.py", "engine/scripts/reuse_stamp.py", "scripts/agent_sandbox.py", "scripts/agent_sandbox.json", "scripts/gate_reuse.py", "scripts/mutation_reuse.py", "scripts/case_reuse.py", "scripts/case_inputs.py", "scripts/reuse_stamp.py", "scripts/verify.sh", "scripts/veldo-guard.sh", "engine/scripts/veldo-guard.sh", "engine/.veldo/control_verification.py", ".veldo/control_verification.py", "engine/.veldo/reuse_evidence.py", ".veldo/reuse_evidence.py", ".veldo/policy.yaml", "scripts/gate_unconfined.json", "scripts/gate_legs.py", "scripts/selftest.py", "scripts/run_scope.py", "scripts/suites/shared.py", "scripts/check_first_use.py", "engine/scripts/gate_legs.py", "engine/scripts/gate_unconfined.json"]
footprint:
  - ".veldo/candidate_git.py"
  - "engine/.veldo/candidate_git.py"
  - "engine/scripts/*.py"
  - "engine/scripts/agent_sandbox.json"
  - "engine/scripts/gate_unconfined.json"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - "scripts/case_trace.py"
  - "scripts/mutation_sandbox.py"
  - "scripts/mutation_observer.py"
  - "scripts/gate_candidate.py"
  - "scripts/reuse_worker.py"
  - "scripts/mutation_ownership.py"
  - "scripts/check_gate_mutations.py"
  - "engine/scripts/verify.sh"
  - "scripts/agent_sandbox.py"
  - "scripts/agent_sandbox.json"
  - "scripts/gate_reuse.py"
  - "scripts/mutation_reuse.py"
  - "scripts/case_reuse.py"
  - "scripts/case_inputs.py"
  - "scripts/reuse_stamp.py"
  - "scripts/verify.sh"
  - "scripts/gate_legs.py"
  - "scripts/gate_unconfined.json"
  - "scripts/selftest.py"
  - "scripts/check_first_use.py"
  - "scripts/veldo-guard.sh"
  - "engine/scripts/veldo-guard.sh"
  - "packs/claude/scripts/veldo-guard.sh"
  - "engine/.veldo/control_verification.py"
  - ".veldo/control_verification.py"
  - "engine/.veldo/reuse_evidence.py"
  - ".veldo/reuse_evidence.py"
  - ".veldo/policy.yaml"
  - "scripts/suites/101_veldo_0208_landing_reuse.py"
  - "scripts/suites/99_veldo_0205_reuse.py"
  - "scripts/suites/100_veldo_0207_case_reuse.py"
  - "scripts/suites/98_veldo_0204_mutation_receipts.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0205-mutation-result-reuse.md"
  - "specs/VELDO-0207-declared-case-reuse.md"
  - "specs/VELDO-0123-mutation-drivers-in-every-gate.md"
  - "specs/VELDO-0208-single-user-landing-reuse.md"
  - "specs/VELDO-0209-confined-control-plane.md"
  - "specs/index.md"
  - "proof/VELDO-0208/*"
  - "scripts/check_generated.sh"
  - "scripts/update_index.py"
  - "engine/scripts/update_index.py"
  - "scripts/run_scope.py"
  - "scripts/suites/shared.py"
  - "proof/WARP-0716/crossing-state.md"
  - "scripts/check_install_and_run.py"
  - "scripts/suites/*.py"
  - "proof/VELDO-0088/fixture.py"
  - "proof/VELDO-0152/fixture.py"
  - "proof/VELDO-0162/base_fixture.py"
behavior_bearing: true
observability:
  logs: Launcher names unavailable confinement and invalid configuration; landing names missing authenticated evidence.
  metrics: Preserve exact fresh and reused counts and the force-fresh control.
  traces: HMAC binds non-agent provenance, declared case keys, observations and landing commit.
  error_taxonomy: Unavailable confinement refuses agent startup; absent provenance misses reuse and refuses positive landing counts.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Implementing agents and descendants cannot read or write the store or key, plant a
      record, or write trusted machinery and runner scripts. Set: direct Python access, children,
      symlinks, replacement, inherited descriptors and IPC escape paths. Completeness: one config
      defines paths; an unprivileged Landlock launcher grants only worktree and private scratch
      writes and refuses unsupported kernels before executing the command. Test sandbox rows.
    falsified_by: Grant store access or start an agent after confinement fails; sandbox rows fail.
  - id: AC2
    text: >
      Claim: Reusable records authenticate publication by the authority-checkout reuse stage.
      Set: gate-written records, edited records, validly signed records missing provenance and a
      confined writer. Completeness: only the authority stage launches and observes workers; its engine digest
      enters case keys and authenticated records and receipts, checked by landing. Test provenance rows without root.
    falsified_by: Accept a record without authenticated non-agent provenance; provenance rows fail.
  - id: AC3
    text: >
      Claim: Landing accepts positive reuse only for authenticated records matching declared case
      inputs and the gated commit. Set: valid, missing provenance, wrong key, wrong commit, tampered
      counts, mixed fresh/reused and force-fresh receipts. Completeness: the reducer, fleet judge
      and shipped guard enforce one evidence contract; forced fresh still requires zero reuse.
      Test landing rows with controlled observations, never a mutation stage.
    falsified_by: Accept positive reuse without authenticated record evidence; landing rows fail.
required_evidence: [unit, integration]
rollback: Restore force-fresh landing policy and stop launching implementing agents until the confinement configuration is reviewed again.
---

## Authority and amendment

Owner Telegram 31911 requests landing reuse; 31916 requires a single-user setup.
No separate OS account, system service, root step, push or merge is involved. This amends
VELDO-0205 AC4 and its landing policy and VELDO-0123's landing/release freshness requirement:
landing may accept authenticated non-agent results with the VELDO-0207 per-case declared key.
VELDO_GATE_FORCE_FRESH remains an explicit bypass, and qualification fixtures remain fresh.
The merged tree still requires a complete gate and honest fresh/reused counts.

## Trust boundary and deployment

Trusted: the owner, orchestrator, kernel/system tools, and the reuse stage loaded from
an authority checkout or its installed engine snapshot. Untrusted: everything executed
from a candidate tree, including suites, registries, drivers and worker entry points.
The gate routes candidate commands through the authority launcher before execution.
Registry enumeration runs confined. The authority coordinator launches each worker,
observes its exit and output, validates baseline/noop/mutant observations, and alone
performs lookup and publication. It never accepts a candidate-produced stage receipt.
Workers start with authority bootstrap/driver code and install confinement before
executing candidate suites. The coordinator's receipt is outside candidate write grants.
An unconfined owner can write records; HMAC is not a defense against that owner.
The store probe is only a kernel access check, not evidence of code identity.

Provenance is the authority engine digest over the shipped reuse coordinator, worker,
observer, confinement, configuration and signing modules. It enters per-case keys,
record HMACs and landing receipt HMACs. Landing recomputes its own authority identity;
a valid signature from another engine is insufficient. Changes invalidate reuse.
This proves publication by machinery with the matching authority under the confinement
assumption, not that assertions are adequate or the unconfined owner is honest.
The generic mutation observer ships with the engine; candidate driver code is used
only for confined registry enumeration, never as the authority worker entry.

One reviewed JSON config supplies the store (including authentication.key), read roots,
writable roots and protected runner paths. The launcher fails closed on missing paths,
unsafe overlaps, unsupported confinement or invalid config. Private scratch holds CLI state;
only selected authentication/configuration files are copied there, never written back.
Inherited nonstandard descriptors are closed. Filesystem grants exclude /proc, /run and
unnecessary devices; IPC restrictions prevent asking a same-user service to escape the domain.
The authority checkout, runner scripts, their configuration and installed tools are read-only.
Changes inside an agent worktree are proposals, consumed by the trusted orchestrator only
after review. The orchestrator must not execute candidate launcher or verification code as
trusted machinery before that review. The agent/gate profile permits TCP/TLS, including
remote Codex and Claude model APIs. It denies AF_UNIX service sockets (including the
user bus and systemd private socket), inherited socket descriptors, abstract cross-domain
sockets and io_uring alternatives. The worker profile additionally denies all network
sockets and socket dispatch. Agent network access is necessary for normal CLI operation.

The owner wires the command prefix into myday's codex_work.sh and claude_work.sh after review.
Those external files are not edited here. This checkout is not retroactively confined.
Existing agent sessions must finish and the owner must rotate exposed signing keys before reuse
is trusted. The default v2 store is a new rollout namespace, not an upgrade of the old v1 key. Old records without provenance
are misses and must be removed by the owner or left to run fresh; they are never upgraded.

## Git boundary

Before any Git command on a candidate, the authority checks its .git marker without
running Git. Linked markers must resolve under the expected shared gitdir/worktrees,
with matching commondir and backlink. The expected directory comes from the authority,
never from the candidate. Installed authorities retain the original trusted directory.
All orchestrator Git queries strip inherited GIT_* settings, disable global/system
configuration, set core.hooksPath=/dev/null and core.fsmonitor=false, and pin git-dir,
work-tree and common-dir after validation. External runners must use this same boundary
before their status queries (exact invocation in the follow-up report).

An agent never writes the shared repository. Each agent works in a linked worktree of its own
bare repository: its objects are private and the shared object store is at most a read-only
alternate. The orchestrator names that repository (VELDO_EXPECTED_GIT_COMMON); it is never
derived from the worktree's writable marker. The agent may write its worktree gitdir, its private
object store and refs/heads/agent/<id>/ (with the matching reflog directory) only. Every other ref
of its repository, including refs/heads/main, and that repository's config and hooks stay
read-only. The launcher refuses to start an agent in a worktree of the shared repository, one with
no named private repository, or one whose branch is outside refs/heads/agent/<id>/.
`agent_sandbox.py prepare` creates the layout. Agent work enters the shared repository only through
`agent_sandbox.py integrate`, a fetch of refs/heads/agent/<id>/* with transfer.fsckObjects=true,
so every received object is re-hashed. The gate then runs on the integrated branch from the shared
repository, or on the agent worktree with VELDO_EXPECTED_GIT_COMMON naming the agent repository.
Trusted authority storage still lives outside every gitdir the agent can read.

## Build and evidence limits

Only suite 101_veldo_0208_landing_reuse is run for this specification, sequentially in the
foreground. It may call controlled fixture workers but never the mutation stage. The reviewer
runs the fresh full gate, prior suites and mutation qualifications and lands the real stamp.
No fabricated full-gate proof, review or exact-commit protected-path approval is recorded here.

## Kernel and workflow limits

The launcher requires x86_64 Linux with Landlock ABI 6 or newer plus unprivileged seccomp.
Both are available on the build host (Landlock ABI 8). Other hosts refuse to start; there is
no unsandboxed fallback. Landlock restricts file content and directory operations, not stat
metadata or chmod. Changing a mode cannot override the content restrictions. The IPC filter
blocks pathname Unix services and asynchronous syscall alternatives; Landlock scopes signals
and abstract Unix sockets and restricts ptrace across domains. See the Linux kernel's
[Landlock documentation](https://www.kernel.org/doc/html/v6.16/userspace-api/landlock.html).

Worktree Git persistence grants the worktree's own gitdir, the private object store and the
agent's own namespace directories. Git's sibling .lock files therefore stay inside that namespace.
The trusted verifier installation (control_verification.installation_at) does not trust any object
store to map ids to content. It re-hashes every object from the trusted commit down and refuses on
any mismatch, so a planted pack that remaps an existing id is never installed. The authority's
working files, common Git configuration/hooks, other worktree gitdirs, store/key and external
runners remain denied writes. This does not change this checkout's Git layout. Private scratch
contains selected copied CLI credentials. A trusted supervisor waits for the confined
child, terminates its remaining process group and removes scratch on success or refusal.
The default grants contain no broad home or /tmp read. CLI executable directories are
optional read roots; original credentials, .ssh and all ~/.cache/veldo stores remain denied.
The CLI receives only its selected credential/config copies in private scratch; gate
commands receive no CLI credential copies.

## Review correction contract, 2026-10-06

The landing environment explicitly selects authenticated reuse by default and preserves a
requested force-fresh mode. Both reused and force_fresh are mandatory on stamps and events.
Both profiles deny Unix service connections, preopened socket descriptors and io_uring
alternatives. Only mutant workers deny TCP/TLS; agent network connections are allowed. Suite 100 plants missing fields, service-socket attempts and denied
writes, and drives a real commit in a disposable linked worktree through the launcher.

Authority startup loads no candidate Python. Worker file tracing begins at the observed
successful Landlock restriction syscall, after authority bootstrap imports and before any
candidate execution. Missing boundary evidence is red, and all later accesses (including
failed probes and descendants) remain checked against the declared closure. Bootstrap
code is covered by the authority engine digest; candidate code cannot opt out of tracing.

## Review correction contract, 2026-10-06 (second review)

Worker ownership: the coordinator creates each worker's ownership ledger in its own directory,
outside every worker grant, and the worker inherits only an append descriptor to it. Candidate
code shares the worker process, so every ledger line is a claim. Cleanup acts only on entries of
the exact shapes the Tracker produces for that worker: a directory strictly beneath that worker's
home after resolving links, a veldo-authority-<hex>.service file directly in
/run/user/<uid>/systemd/user, or a slice matching the Tracker pattern. It reaps those, and any other
entry turns the stage red (worker_cleanup_error) without being acted on. Suite 101 plants an outside
directory, an arbitrary service file and an arbitrary slice through real workers under the real
coordinator. It also plants a ledger in the old in-home location, which is never read.

Developer diff directory: the case directory, module and name joined into --diff-dir paths come
from the candidate registry. Each passes safe_name, and a name must be a single component. A
traversing part is incomplete_inventory before anything is written. Suite 98 plants each part.

Publication race: two gates with the same declared inputs can both miss and both publish. The
stored record drops the observers' free-text failure details, so equivalent runs publish identical
bytes. When different bytes already exist, an authenticated record that passes the stage's own
result validation for this case and input digest is kept. Only an existing record that fails that
validation (or a store-level write with no validation supplied) is a conflict. Suite 99 drives
identical bytes, a kept earlier valid record and a poisoned invalid one.

Agent Git isolation: see Git boundary. Suite 101 commits through the launcher in a prepared
private repository, and checks that writes to refs/heads/main, another agent's namespace, the
shared object store, shared refs and private config are refused. It integrates through the fsck
fetch, and shows that a remapped object in the private store fails integration without moving a
shared ref. It refuses start for a shared worktree, an unnamed repository and an out-of-namespace
branch. It also plants a pack remapping the verifier's blob id and shows installation refuses it,
while the same installer without the hash check would install the forged bytes.

## Gate stage corrections, 2026-10-07

The first full confined gate (e7d68c72) went red in five stages while every suite passed alone,
because nothing ran a stage the way the gate runs it. Corrections, each kept inside AC1:

- Generated: every generator writes into a private temporary file and the committed file is
  compared with it. A stale file is red with its one-command remedy and is never rewritten.
- Unix sockets and terminals (unit, integration, mutation workers): Landlock ABI 8 does not
  mediate connect to a pathname socket, so the gate and worker profiles keep refusing every
  call that could reach a service and have the launcher's trusted parent perform the rest
  through a seccomp user-notification listener the confined child hands over and closes before
  any candidate code runs. Unix sockets may be created; connect, bind, addressed sendto, sendmsg
  and TIOCGPTPEER are performed by the parent with its own copy of the arguments. An address
  must be absolute and resolve beneath the domain's writable roots with no symlink, magic link
  or mount crossing; abstract names are refused; bind runs in a helper confined to create
  socket files only beneath those roots; only SCM_RIGHTS crosses at socket level; workers get
  no other address family. /dev/ptmx is granted and /dev/pts is not, so a domain reaches only
  terminals it created. A launcher nested in a brokered domain is strict (no Unix sockets): the
  outer broker answers for its own domain's roots, never a nested one's. The agent profile is
  unchanged.
- /proc is readable (never writable) in the gate and worker profiles: the suites and the control
  plane read mounts, process identity and cgroups. Another domain's environ, fd, root, cwd, mem
  and maps are ptrace-mode accesses, which Landlock refuses across domains (measured).
- The account's locked graph runtime (~/.local/share/veldo/langgraph) is an optional read root,
  like the CLI directories. Its stage (~/.local/state/veldo/graph-stage) is never granted:
  production executes the runner copies it holds.
- A nested launcher closes inherited descriptors with close_range, not a /proc listing, and does
  not hand VELDO_EXPECTED_GIT_COMMON to confined commands; install-and-run names each adopter
  repository's own common directory to its gate.
- A failed mutation receipt is a one-line RED in the requested mode with reused.mutation null.
- Suite fixtures choose /dev/shm by trying it, and signal across forks on pipes: /dev/shm (POSIX
  semaphores) is not granted, since it holds every same-user process's shared memory.

Suite 101 runs these stages under the gate's launcher (rows confined-stage/*).

## Suites the confined gate cannot run, 2026-10-07

With the corrections above the unit stage reaches every suite, and two classes stay red by the
design of this specification, not by a defect in how the gate runs them:

- The systemd user manager. The control-plane suites start transient units and slices through
  systemctl --user, place runtime directories in /run/user/<uid>, and refuse a host whose
  profile lacks the user manager (unavailable_service:profile:user_manager). A unit the manager
  starts runs outside the Landlock domain, which is exactly the same-user service escape this
  specification denies. Affected (some rows only in several): 62_0039, 63_0040, 63_0049,
  64_0050, 66_0042, 67_0041, 67_0135, 71_0076, 71_0130, 71_0138, 73_0139, 78_0060, 79_0061,
  80_0155, 81_0156, 82_0129, 82_0141, 83_0154, 85_0158, 85_0171, 86_0127, 86_0148, 86_0189,
  87_0170, 91_0167, 92_0088, 93_0152, 94_0162, 96_0204. Module-level failures in several of
  them stop the unit run, and with it the integration stage's nested run.
- Nested tracing. Suites 100 and 101 drive authority workers under strace; ptrace is refused
  inside the domain, so those rows cannot run when the unit stage itself is confined.

Classified 2026-10-07: 62_0045 and 82_0085 were simple confinement mismatches and are fixed in
their suites: pip's uninstall stash fell back to an ungranted /tmp because the fixture's pip
environment dropped TMPDIR, and multiprocessing's Barrier, Lock and Queue need /dev/shm (shared.py
gains ForkLock and ForkBarrier on pipes). 65_0067 is not: the product's custody wrapper builds its
allowlist by listing every ancestor of the protected directory up to /, which the domain cannot list.
It joins the classes above.

Neither class can turn green inside the confinement without granting the escape it denies.
VELDO-0209 proposed running the unit and integration stages in a KVM guest instead. The owner
rejected it (Telegram 32403-32407, 2026-10-07: "VM is shit... do not do it") and decided what
follows; VELDO-0209 is withdrawn and keeps its measurements as the record of why.

## Unconfined leg (owner decision, Telegram 32403-32407, 2026-10-07)

The suites above run the way they ran before this specification's confinement existed: outside
it, in a separate, named leg of the unit and integration stages. Every other stage and every other
suite stays confined. The owner confirmed this design ("Yes"). It is a deliberate exception to AC1
for these suites only: their code runs with the owner's own authority, as it did before VELDO-0208.

- One declared list, scripts/gate_unconfined.json, names each suite and its reason, and the exact
  stage commands it applies to (unit: `python3 scripts/selftest.py`, integration:
  `python3 scripts/check_first_use.py`). A suite listed with `rows` leaves the domain for those
  rows only; the rest of that suite stays in the confined leg. The list, with its reasons:
  - systemd user manager, whole suite: the 29 control-plane suites above (62_0039 through 96_0204),
    each entry naming what it starts or reads through the manager;
  - nested custody confinement, whole suite: 65_0067;
  - nested strace, rows `strace` only: 100_0207 (sandbox-valid-worker, the *-caught-undeclared-*
    rows and startup-runtime-boundary) and 101_0208 (authority-worker-* and
    authority-observes-kill).
- The list is the authority's: verify.sh reads it from its own installation
  ($VELDO_AUTHORITY/scripts), never from the candidate, so a candidate's own copy of the list or a
  leg variable it sets decides nothing. The candidate's dispatcher applies the list:
  scripts/selftest.py picks each leg's suites, scripts/run_scope.py and scripts/suites/shared.py
  (leg_runs) pick the rows, and scripts/check_first_use.py, the integration stage's command, runs
  whole in the unconfined leg and hands the leg to its nested selftest.py. The list, its runner
  scripts/gate_legs.py and those four dispatcher files are protected paths.
- No file in scripts/ or scripts/suites/ can shadow a standard-library module the dispatcher
  imports. selftest.py and check_first_use.py drop the script directory from sys.path before any
  import beyond os and sys (which the interpreter loads before a script runs), and selftest.py puts
  scripts/ and scripts/suites/ back after the standard library, so shared.py's imports are the
  standard library's too. gate_legs.py runs from the authority as python3 -I -S.
- What holds: a suite the authority's list does not name, or a row it does not list, runs only in
  the confined leg unless a protected file changes, which needs the owner's approval. The bound is
  by suite name as scripts/suites/manifest.json enumerates it.
- A declared stage runs as two legs through scripts/gate_legs.py: the confined leg through
  scripts/gate_candidate.py with VELDO_GATE_LEG=confined, then the unconfined leg directly with
  VELDO_GATE_LEG=unconfined; VELDO_GATE_UNCONFINED carries the list. The stage passes only when both
  legs pass. A stage the list does not declare, or a command other than the declared one, runs
  confined whole, and the caller's leg variables are dropped. An invalid list runs nothing.
- Visible, never silent: the gate prints each leg on the stage lines, the unconfined one as
  "UNCONFINED LEG - runs outside the confinement by owner decision" followed by its entries, and
  the dispatcher prints each leg's banner with its list. The stamp and the gate event carry
  `"unconfined": {"declaration": "sha256:<list digest>", "legs": {"<stage>": [<entries>]}}` whenever
  a leg was expected; the field is absent only when no stage expected one (an authority with no
  list, or a catalog with no declared stage). verify.sh asks the authority's list whether a stage
  expects a leg before the stage runs; when one was expected and the leg record is missing, empty,
  unreadable or short of an expected stage, the gate is RED with the field null. The record is a
  file candidate code in the unconfined leg can reach, so its absence never reads as "no unconfined
  leg ran".
- The list and its runner are authority files: both are in reuse_evidence.AUTHORITY_FILES, so a
  reused result is bound to the list and runner it ran under, and in init_scaffold's
  _REUSE_AUTHORITY, so they install with the rest of the authority (canon copies in
  engine/scripts). The shipped engine gate declares no unit command and does not call them.
- Accepted residuals. The list and the protected dispatcher bound which suites and rows run
  unconfined, not what the code of a listed suite does once it runs: that code runs with the
  owner's full permissions, exactly as every suite did before VELDO-0208. In particular:
  - unconfined suite code can forge the leg record (a missing, empty, unreadable or short record is
    RED, but a well-formed forged one is not detected);
  - the listed suite files and scripts/suites/manifest.json are not protected, so a candidate, or
    unconfined suite code while it runs, can edit them and change which code a listed name runs;
  - anything else code run by the owner can do.
  Review of the candidate guards that code. The confined legs keep refusing every escape the
  confined-stage rows plant.
- Tests (suite 101, rows unconfined-leg/*): the declared list and its reasons; the list and runner
  and the dispatcher files are protected, and the list is read from the authority (a candidate copy
  naming another suite is ignored); a candidate scripts/json.py or suites/tempfile.py is never
  imported by the dispatcher in either leg, nor by check_first_use.py; verify.sh's own stamp and event lines carry the leg
  when it was expected, omit it when none was, and are RED with null when an expected leg's record
  is deleted, empty or unreadable; the row ownership
  of each leg; a fixture candidate through the real runner, launcher and dispatcher in which a
  listed suite runs unconfined and is named, a suite the candidate asks for stays confined, only the
  listed rows leave, an undeclared stage or command is confined whole whatever the caller sets, and
  an invalid list runs nothing.
