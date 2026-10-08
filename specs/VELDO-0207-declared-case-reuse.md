---
schema: veldo.spec/v1
id: VELDO-0207
title: Declared case inputs enforced by isolated mutation snapshots
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0205]
placement: [enforcement]
protected_paths: ["scripts/check_gate_mutations.py", ".veldo/policy.yaml", "scripts/gate_reuse.py", "scripts/mutation_reuse.py", "scripts/mutation_sandbox.py", "scripts/case_reuse.py", "scripts/case_inputs.py", "scripts/case_trace.py", "scripts/propose_case_inputs.py", "scripts/mutation_case_inputs.json"]
footprint:
  - ".veldo/policy.yaml"
  - "scripts/check_gate_mutations.py"
  - "scripts/gate_reuse.py"
  - "scripts/mutation_reuse.py"
  - "scripts/mutation_sandbox.py"
  - "scripts/case_reuse.py"
  - "scripts/case_inputs.py"
  - "scripts/case_trace.py"
  - "scripts/propose_case_inputs.py"
  - "scripts/suites/53_veldo_0123_mutations.py"
  - "scripts/mutation_case_inputs.json"
  - "scripts/suites/100_veldo_0207_case_reuse.py"
  - "scripts/suites/99_veldo_0205_reuse.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0207-declared-case-reuse.md"
  - "specs/VELDO-0205-mutation-result-reuse.md"
  - "specs/index.md"
  - "proof/VELDO-0207/*"
behavior_bearing: true
observability:
  logs: Name each case, its declared closure, cache decision and undeclared access refusal.
  metrics: Measured source fan-in, elapsed trace time, executed and reused counts.
  traces: Preserve per-case source identities and per-driver runtime identity in authenticated receipts.
  error_taxonomy: Missing declaration runs fresh; denied or incomplete declared input fails loudly; corrupt cache is a miss.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Measurement precedes narrowing. Set: about thirty individual cases spanning both
      drivers and modules. Completeness: record Python audit and descendant syscall file traces,
      source file fan-in, shared helper reach, failed observations and limits in proof/VELDO-0207.
      Tracing proposes reviewable inputs only; it never certifies determinism or completeness.
    falsified_by: Report failed or unobserved reads as a complete passing closure.
  - id: AC2
    text: >
      Claim: A reusable worker sees only its declared repository files and runtime paths.
      Set: module, loaded helpers, suite, shared harness, worker code and its own registry entry.
      Completeness: build a fresh per-case snapshot without Git history or unrelated files;
      apply inherited Landlock and audit descendant file syscalls outside the worker; reject
      undeclared repository reads even if caught. Test Python and child reads in case/sandbox.
    falsified_by: Expose the original checkout to a reusable worker; case/sandbox must fail.
  - id: AC3
    text: >
      Claim: Case keys have no whole-tree or HEAD dependency. Set: declared input content and mode,
      individual registry entry, worker environment, per-driver toolchain and unrelated edits.
      Completeness: case/keys drives a shared helper edit, an unrelated commit, another case's
      registry change and a toolchain change. Only dependent cases miss; the driver's runtime
      change misses every case of that driver.
    falsified_by: Include HEAD or the entire registry in a case key; case/keys must fail.
  - id: AC4
    text: >
      Claim: VELDO-0205 authentication, result validation, honest receipts and force-fresh rules
      survive the change. Set: cold, warm, mixed, tampered, planted stale, force-fresh and undeclared
      cases. Completeness: case/receipts exercises the coordinator with controlled workers and
      case/store exercises real authenticated records; no fresh survivor becomes a pass.
    falsified_by: Publish a result with a different case input digest; case/store must fail.
required_evidence: [unit, integration]
rollback: Revert per-case reuse and its declarations together; force-fresh remains available; VELDO-0208 governs authenticated landing reuse.
---

## Design and authority

The owner explicitly accepted the reviewer's per-case sandbox design on 2026-10-06.
This ready contract prepares protected changes for separate exact-commit owner approval.
No push, merge, full gate or full mutation registry execution occurs during this build.
Suite 99 and suite 98 are the only selftest selections permitted here, sequentially.

The coordinator enumerates current registry definitions. A deterministic AST projection keeps
imports, constants and worker functions while replacing registry construction with the one
selected case. Projection code itself is a mandatory declared input. Thus another registry
entry does not invalidate this case, while any change to executable worker code does.

A declaration names repository files, expected absent paths where needed, and a per-driver
runtime profile. The snapshot contains only those files and projected drivers. It has no .git
or original checkout link. Snapshots are materialized only when a worker is admitted and
removed on completion or failure, so disk use is bounded by active workers. Repository-relative names, modes and contents, the selected registry
entry, worker implementation and fixed environment form the input digest. HEAD is receipt
provenance only. Runtime identity covers the interpreter, stdlib, git, shell, libc and explicitly
allowed tools/configuration; the worker's Landlock allowlist is exactly that runtime set.

An external syscall trace belongs to the coordinator, outside writable worker scratch. It is
checked before accepting worker output. It detects open, metadata, access, readlink and directory-listing probes of undeclared repository
paths, including a child or a caught read error. Expected absent declarations are keyed too;
adding such a file invalidates admission. Runtime changes invalidate all cases sharing that
profile. Successful interpreter-startup reads are traced and checked as well; system site
initialization is disabled in declared workers, and preloaded native libraries must be keyed. Snapshot and runtime bytes are checked again before publication. Unsupported tracing
or sandbox hosts fail closed. No tracing-derived declaration becomes an approval or a claim
that clock, random, network, mount or service dependencies are deterministic: declarations start
as proposals, and only reviewed file-only cases are admitted to reuse. Cases needing host
services or repository history remain fresh until a separate explicit closure can enforce them.

The Linux kernel, tracer and coordinator account are trusted. Landlock confines file contents and seccomp denies service sockets;
the tracer is the additional fail-loud boundary for absent reads. Non-file nondeterminism is
explicitly outside a file-only qualification and requires review. The HMAC key is readable by
the coordinator account, never by a confined worker. An arbitrary hostile process already
running as the coordinator account outside the sandbox remains outside the threat model.

## Review correction contract, 2026-10-06

Amended by VELDO-0210 AC7 (owner decision, 2026-10-07). A suite that starts a gate is never
eligible for declaration: a declared case reads only its declared inputs, so it starts a gate only
when they hold a gate entry (verify.sh, gate_candidate.py, gate_legs.py or agent_sandbox.py, any
copy), and case_reuse refuses such a declaration with the reason starts_a_gate in the case's
receipt; its cases always run fresh, because the gate nests in a fresh worker's tree, which no
tracer may follow. Declared cases are otherwise unchanged: confined in place by
mutation_sandbox.confine and traced by the coordinator.

Metadata probes (including absent exists/is_file/stat/access/readlink) are inputs too.
Directory listings require explicit directory declarations, keyed with their complete subtree.
The proposer captures the same syscall family. Expected absent runtime paths are explicit,
keyed, and checked again before publication. Forced runs enforce identical snapshot rules.
Workers and implementing agents may use TCP/TLS; Unix service sockets, inherited socket
descriptors, abstract cross-domain sockets and io_uring are denied in both, and mutation
workers take exactly the gate profile's network rule (VELDO-0208, Worker network rule:
owner decision, Telegram 32421, 2026-10-07); unsupported filtering refuses execution. Timings belong in receipts, never keyed
records; conflicting content for one key makes the stage fail.

The original open-only measurement has 21 of 30 unclean baselines and 19 universal shared
files. About 10% time-weighted savings for single-module edits is an optimistic upper bound,
not a measured speedup. The full-call-family sequential rerun and per-file reach are retained
in proof/VELDO-0207; no failed baseline is a qualified declaration.
