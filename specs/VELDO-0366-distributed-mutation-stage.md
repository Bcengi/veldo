---
schema: veldo.spec/v1
id: VELDO-0366
title: One gate distributes exact mutation identities to qualified host authorities
status: ready
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0363, VELDO-0365]
placement: [enforcement]
protected_paths: [scripts/check_gate_mutations.py, engine/scripts/check_gate_mutations.py, scripts/mutation_shards.py, engine/scripts/mutation_shards.py, scripts/mutation_transport.py, engine/scripts/mutation_transport.py, scripts/mutation_hosts.json, scripts/reuse_worker.py, engine/scripts/reuse_worker.py, .veldo/policy.yaml, engine/.veldo/policy.yaml]
footprint:
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - scripts/mutation_shards.py
  - engine/scripts/mutation_shards.py
  - scripts/mutation_transport.py
  - engine/scripts/mutation_transport.py
  - scripts/mutation_hosts.json
  - scripts/reuse_worker.py
  - engine/scripts/reuse_worker.py
  - .veldo/policy.yaml
  - engine/.veldo/policy.yaml
  - scripts/check_teeth_mutations.py
  - scripts/suites/163_veldo_0366_shards.py
  - scripts/suites/support/v366_nodes.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - specs/VELDO-0366-distributed-mutation-stage.md
  - specs/index.md
  - proof/VELDO-0366/*
behavior_bearing: true
observability:
  logs: Preserve the first refusal and every returned shard receipt, including partial failures.
  metrics: Registered identities, assignments, measured group costs, host capacity and cleanup.
  traces: Authenticated session, commit, exact inputs, inventory, qualification and assignment bindings.
  error_taxonomy: Unqualified, forged, missing, duplicate, foreign, failed, cancelled and disconnected shards are red.
acceptance_criteria:
  - id: AC1
    text: >
      The sole gate coordinator retains pc1 lock ownership and its existing ledger. A remote
      authority takes that host's lock and creates a separate measured ledger and delegated scope.
      Every remote session freshly qualifies before assignment. Controls travel with immutable
      identities, and indivisible suite/module groups balance by measured cost and host capacity.
      Native and unconfined cases stay on pc1 unless their execution boundary is qualified.
    falsified_by: An unqualified or busy host accepting work, split controls, changed definitions or lost manager and port exclusions fail named fixture rows.
  - id: AC2
    text: >
      Only authenticated exact-input receipts can contribute results. The full registered identity
      multiset equals the assignment and result multisets exactly once. Selected runs remain selected.
      Failed, missing, duplicate, foreign, forged, replayed and cancelled receipts cannot pass.
    falsified_by: Each malformed receipt is independently injected by fake nodes and must keep aggregation red.
  - id: AC3
    text: >
      The gate owns its SSH transport, ships committed clean bytes and authenticates the host using
      strict SSH host keys. Session signing material stays outside worker files and environments.
      Remote workers retain no-network confinement and cannot reach the result store. EOF or
      cancellation tears down owned processes, scopes, grants and scratch before releasing custody.
    falsified_by: A local directory node and stub transport disconnect during execution and prove cleanup and red status; leaked signing material or worker network/store access fails boundary checks.
  - id: AC4
    text: >
      Existing per-group early release and fail-fast validation are retained on each host; the first
      failed shard cancels siblings, while explicit collect-all remains diagnostic and red.
      No full gate, full leg, pc1 load, nested gate fixtures, live-capture modules, new clock sites,
      confinement exemptions or assertion weakening are part of validation. Engine copies match;
      census passes, personal setup and stale-mutant findings are zero.
    falsified_by: Fake-node early-release and cancellation rows, census, template comparison and hygiene checks fail any regression.
required_evidence: [unit, integration]
rollback: Disable distributed opt-in and revert this ticket; single-host scheduling remains available.
---

Owner: Telegram 43610, "I need to speedup veldo work". Rank 5 phase 2 follows section 3
of the speed analysis. Gate 18 owns pc1; this task runs only lightweight fake-node proofs.
A bounded real pc2 drive is permitted only after fresh green qualification. The phase 1
receipt is red for worker-visible Node/npm and is never promoted to admission.

Transport decision: use a gate-owned SSH stream, not a runtime dependency on the personal
myday wrapper. The latter has useful clean-checkout, slot and disconnect supervision, but
does not implement the gate's session authentication or exact coverage contract. The new
protected transport uses strict host keys, committed bundles, the existing host lock and
scope teardown primitives. No personal script or machine installation changes are needed.

The trust boundary is reviewed gate authority code on owner-controlled hosts and SSH host
keys. Workers and their output are untrusted. Same-account replacement of the reviewed
authority is outside this contract, as it is for the existing gate. Remote unconfined work
is deliberately inadmissible: the existing protected exemption list is unchanged.

This ticket records bounded evidence only. Independent review and a later canonical gate
remain outstanding; a local directory node is never evidence of native qualification.

The initial remote eligibility declaration names the nine suites used in phase 1; whole
registered control groups from those suites are eligible, and all other identities remain
local. Their declared runtime uses the required qualification tools; manager services and
additional C/Rust/browser toolchains are not assumed available. This is an explicit rollout
boundary, not a reduction in full-stage coverage. Measured group histories drive placement;
missing samples use the existing conservative estimate and cannot authorize a verdict.

Remote workers add an AF_UNIX-only seccomp filter after namespace setup, before candidate
imports. The ordinary worker boundary permits TCP, so merely reusing it would not meet this
contract. The stricter filter is inherited by descendants, preserves scratch Unix IPC and
is separately probed by the remote authority. Authentication material never enters a job,
worker environment or input tree. The existing Landlock grants keep the result store outside
workers. Qualification helpers are newly protected in policy, without changing their bytes.

Enable only through VELDO_GATE_DISTRIBUTED=1 on a clean, committed full gate. No selected CLI
scope can use that path; internally each shard is explicitly selected and only the aggregate
can claim full coverage. Force-fresh shard execution does not change the outer gate's requested
reuse policy. Remote unavailability and qualification failure refuse rather than silently
falling back. VELDO_GATE_COLLECT_ALL=1 retains diagnostic collection while still returning red.
