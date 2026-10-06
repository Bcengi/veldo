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
protected_paths: ["scripts/agent_sandbox.py", "scripts/agent_sandbox.json", "scripts/gate_reuse.py", "scripts/mutation_reuse.py", "scripts/case_reuse.py", "scripts/case_inputs.py", "scripts/reuse_stamp.py", "scripts/verify.sh", "scripts/veldo-guard.sh", "engine/scripts/veldo-guard.sh", "engine/.veldo/control_verification.py", ".veldo/control_verification.py", "engine/.veldo/reuse_evidence.py", ".veldo/reuse_evidence.py", ".veldo/policy.yaml"]
footprint:
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
  - "scripts/suites/100_veldo_0208_landing_reuse.py"
  - "scripts/suites/98_veldo_0205_reuse.py"
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
      Claim: Reusable records authenticate provenance from a gate outside the agent domain.
      Set: gate-written records, edited records, validly signed records missing provenance and a
      confined writer. Completeness: actual store access probes precede publication, and HMAC
      covers provenance and the per-case input key. Test provenance rows without root.
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

The threat is an implementing Codex or Claude process launched by the owner's orchestrator
editing records, stealing the signing key or replacing trusted reuse/landing code or runners.
Every implementing process tree must start through the reviewed launcher from the authority
checkout, outside its own editable worktree. The owner and the orchestrator session itself are
unconfined and trusted, as are the kernel and installed system tools. An unconfined owner can
write records; HMAC is not a defense against that owner. The store probe demonstrates absence
of the configured agent restrictions, not absence of every possible Landlock domain.

One reviewed JSON config supplies the store (including authentication.key), read roots,
writable roots and protected runner paths. The launcher fails closed on missing paths,
unsafe overlaps, unsupported confinement or invalid config. Private scratch holds CLI state;
only selected authentication/configuration files are copied there, never written back.
Inherited nonstandard descriptors are closed. Filesystem grants exclude /proc, /run and
unnecessary devices; IPC restrictions prevent asking a same-user service to escape the domain.
The authority checkout, runner scripts, their configuration and installed tools are read-only.
Changes inside an agent worktree are proposals, consumed by the trusted orchestrator only
after review. The orchestrator must not execute candidate launcher or verification code as
trusted machinery before that review. The launcher denies network sockets as well as local service sockets. Live CLIs needing
remote model APIs need a separately reviewed, narrowly scoped transport; none is provided here.

The owner wires the command prefix into myday's codex_work.sh and claude_work.sh after review.
Those external files are not edited here. This checkout is not retroactively confined.
Existing agent sessions must finish and the owner must rotate exposed signing keys before reuse
is trusted. The default v2 store is a new rollout namespace, not an upgrade of the old v1 key. Old records without provenance
are misses and must be removed by the owner or left to run fresh; they are never upgraded.

## Build and evidence limits

Only suite 100_veldo_0208_landing_reuse is run for this specification, sequentially in the
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
contains copied credentials; the trusted orchestrator removes it after all descendants end.

## Review correction contract, 2026-10-06

The landing environment explicitly selects authenticated reuse by default and preserves a
requested force-fresh mode. Both reused and force_fresh are mandatory on stamps and events.
Both sandboxes deny Unix service connections and network, including preopened sockets and
io_uring alternatives. Suite 100 plants missing fields, service-socket attempts and denied
writes, and drives a real commit in a disposable linked worktree through the launcher.
