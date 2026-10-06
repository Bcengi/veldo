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
protected_paths: ["scripts/gate_candidate.py", "scripts/reuse_worker.py", "scripts/mutation_observer.py", "scripts/mutation_ownership.py", "engine/scripts/mutation_ownership.py", ".veldo/candidate_git.py", "engine/.veldo/candidate_git.py", "engine/scripts/agent_sandbox.py", "engine/scripts/agent_sandbox.json", "engine/scripts/mutation_sandbox.py", "engine/scripts/gate_candidate.py", "engine/scripts/reuse_worker.py", "engine/scripts/mutation_observer.py", "engine/scripts/check_gate_mutations.py", "engine/scripts/case_reuse.py", "engine/scripts/case_inputs.py", "engine/scripts/case_trace.py", "engine/scripts/mutation_reuse.py", "engine/scripts/gate_reuse.py", "engine/scripts/reuse_stamp.py", "scripts/agent_sandbox.py", "scripts/agent_sandbox.json", "scripts/gate_reuse.py", "scripts/mutation_reuse.py", "scripts/case_reuse.py", "scripts/case_inputs.py", "scripts/reuse_stamp.py", "scripts/verify.sh", "scripts/veldo-guard.sh", "engine/scripts/veldo-guard.sh", "engine/.veldo/control_verification.py", ".veldo/control_verification.py", "engine/.veldo/reuse_evidence.py", ".veldo/reuse_evidence.py", ".veldo/policy.yaml"]
footprint:
  - ".veldo/candidate_git.py"
  - "engine/.veldo/candidate_git.py"
  - "engine/scripts/*.py"
  - "engine/scripts/agent_sandbox.json"
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
  - "scripts/suites/98_veldo_0204_mutation_receipts.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0205-mutation-result-reuse.md"
  - "specs/VELDO-0207-declared-case-reuse.md"
  - "specs/VELDO-0123-mutation-drivers-in-every-gate.md"
  - "specs/VELDO-0208-single-user-landing-reuse.md"
  - "specs/index.md"
  - "proof/VELDO-0208/*"
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

The agent retains writable index/HEAD/logs for its own linked worktree, shared objects,
and its branch ref/log parent directories; shared config and hooks remain read-only.
Directory grants expose sibling loose refs and shared objects to reads and some writes.
Trusted authority storage must therefore live outside every gitdir the agent can read.
These grants are not isolation between mutually hostile branches in a shared object store.

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

Worktree Git persistence also grants the worktree's own gitdir, shared objects and the parent
directories of its branch ref and reflog. Git needs sibling .lock files, so Landlock necessarily
grants sibling loose refs in those directories as well. A dedicated branch namespace narrows
that exposure. Shared objects and refs are candidate-controlled data, not trusted machinery:
never install trusted verification code from that mutable object store. The authority's
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
