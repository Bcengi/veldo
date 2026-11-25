---
schema: veldo.spec/v1
id: VELDO-0365
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
  - scripts/suites/162_veldo_0365_host_relative.py
  - scripts/suites/56_veldo_0027_signing.py
  - scripts/suites/wallclock_baseline.json
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - scripts/check_teeth_mutations.py
  - specs/VELDO-0365-host-relative-mutation-qualification.md
  - specs/index.md
  - proof/VELDO-0365/*
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
      and concrete toolchain identities from worker-visible tools, including Node and npm.
      Every required probe records success or failure; no missing
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
  - id: AC4
    text: >
      Signing crash-after-rotation observations use an injected clock and retain every assertion.
      Baseline and no-op pass; the truncated-clock mutant deterministically fails historical
      receipt verification and the named transition-clock row on both hosts. Light serial
      single-case repeats record all observations and timestamp operands. A regression control
      fails with the former wall-clock-dependent fixture. No live-capture module or confinement
      exemption changes; census green, personal-setup findings and stale anchors zero.
    falsified_by: Restoring the former fixture fails the deterministic timestamp and verdict regression.
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

## Bounded evidence and remaining blockers

Admission is implemented. On the second host the 100-case drive at `27d3d2630` completed
in 286.08 seconds with 100 rejections, 136 cleaned workers and seven peak workers. All
named case verdicts and controls match gate 15. The stricter full-observation comparator
remains red: the `signing-truncated-clock` mutant has one different off-target
`signing/kill-after-rotation` assertion (false on the first host, true on the second).
No assertion, comparison or baseline was relaxed to hide that difference.

Final native qualification at `f3b2f3739` passes cgroups, Landlock and the confined child
interpreter, namespaces, ptrace and pidfds, but refuses the worker toolchain: Node and
npm exist only for the remote supervisor, not for workers. Owner installation and a fresh
qualification are required. The five guard mutants are killed; census, personal setup,
stale anchors and template sync pass. The ticket stays ready, with partial proof; no
canonical gate, independent review or landing approval is claimed.

## Ticket identity

Renumbered from this branch's former VELDO-0364 to VELDO-0365 because speed-reuse owns
VELDO-0364. Existing commits and raw receipts retain their historical identities and bytes.
All current source registrations, commands and proof paths use VELDO-0365.
