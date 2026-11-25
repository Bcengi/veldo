---
schema: veldo.spec/v1
id: VELDO-0364
title: Smaller mutation hosts have bounded reservations and explicit native qualification
status: ready
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0219, VELDO-0220]
placement: [enforcement]
protected_paths: [scripts/gate_schedule.py, engine/scripts/gate_schedule.py]
footprint:
  - scripts/gate_schedule.py
  - engine/scripts/gate_schedule.py
  - scripts/qualify_mutation_host.py
  - engine/scripts/qualify_mutation_host.py
  - scripts/suites/114_veldo_0216_concurrent_stages.py
  - scripts/check_teeth_mutations.py
  - specs/VELDO-0364-host-relative-mutation-qualification.md
  - specs/index.md
  - proof/VELDO-0364/*
behavior_bearing: true
observability:
  logs: Each native qualification reports all required checks and concrete failures.
  metrics: Receipts record kernel capacity, configured and effective reservation, tool identities and worker cleanup.
  traces: Qualification binds the authority source and actual runtime; selected results retain normal coordinator receipts.
  error_taxonomy: Missing kernel features, delegation, tracing or tools refuse qualification; oversized individual claims still refuse admission.
acceptance_criteria:
  - id: AC1
    text: >
      For every positive measured CPU and memory capacity the mutation reservation is capped at that
      capacity. Only the aggregate startup reservation is fitted; actual coordinator and individual
      worker claims remain checked. Capacities at least as large as the configured reservation retain
      identical behavior. Fixtures exercise large, eight-core, memory-limited and impossible-worker hosts.
    falsified_by: Restoring the absolute floor refusal fails host-relative/eight-core; fitting an individual worker fails host-relative/worker-too-large.
  - id: AC2
    text: >
      An explicit native qualification requires delegated cgroup-v2 accounting and cleanup, Landlock
      allow and deny behavior, the installed namespace helper self-test, ptrace and pidfd operation,
      and concrete toolchain identities. Every required probe records success or failure; no missing
      probe or failed probe can qualify. A selected diagnostic batch starts only after all probes pass.
    falsified_by: Treating a failed or missing probe as qualified fails host-relative/qualification-fail-closed.
  - id: AC3
    text: >
      On the owner's second Linux host, approximately 100 immutable selected cases run wholly through
      the existing single-host coordinator after qualification. Compare every baseline, no-op and
      target-row rejection with existing first-host gate receipts, requiring exact inventory coverage,
      no invalid result and complete cleanup. A missing prerequisite is recorded as blocked with the
      exact owner setup step, never installed by the agent.
    falsified_by: Changing, omitting or duplicating any selected verdict fails the bounded receipt comparison.
required_evidence: [unit, integration]
rollback: Revert this ticket; no host installation or persistent qualification authorization is created.
---

Owner intent: Telegram 43610, "I need to speedup veldo work"; rank 5 phase 1 of the speed analysis.
This is admission and explicit diagnostic qualification only. No shard transport, aggregator,
full-gate claim, live capture, host installation, new wall-clock sites or confinement exemption.
The qualification receipt is evidence for its invocation, not a reusable admission token; later
transport must define and protect its own trust boundary. Existing gate ownership stays unchanged.

Normal use: a reviewed authority runs the qualification command on the prospective Linux host,
under the existing host lock and memory cap. The native probes and selected worker run are local
to that host. Threat model: accidental unsupported hosts and incomplete evidence, not malicious
same-account replacement of authority code or forged local receipts. Independent review and a
canonical gate remain outstanding; the owner explicitly excludes running that gate in this task.
