---
schema: veldo.spec/v1
id: VELDO-0362
title: Completed clean workers teach resource admission even when another case fails
status: ready
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0219]
placement: [enforcement]
protected_paths: [scripts/check_gate_mutations.py, engine/scripts/check_gate_mutations.py]
footprint:
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - scripts/check_teeth_mutations.py
  - scripts/suites/115_veldo_0219_measured_admission.py
  - specs/VELDO-0362-completed-worker-resource-admission.md
  - specs/index.md
  - proof/VELDO-0362/*
behavior_bearing: true
observability:
  logs: Resource store failures are diagnostic; stage errors retain their original verdict.
  metrics: Authority CPU seconds, elapsed seconds, anonymous and total memory peaks for each clean valid completed worker.
  traces: Samples bind platform, case, execution key, mode, and worker identity; admission reports contributing keys.
  error_taxonomy: Invalid, cancelled, stale or unclean workers supply no samples; missing or corrupt hints use the default.
acceptance_criteria:
  - id: AC1
    text: >
      Every completed clean valid control or mutant contributes its authority measurement after input
      and runtime stability checks, including partial red stages. Resources occupy a separate store
      from elapsed estimates and reusable verdicts. Fixture coverage includes independent controls,
      valid kills, failed controls, survivors, cancellation, cleanup failure, stale input and runtime races.
    falsified_by: Moving resource recording behind stage success fails learning/red-stage; accepting an unclean worker fails learning/invalid-workers.
  - id: AC2
    text: >
      On the same platform admission uses the per-case maximum CPU rate and memory across all live
      execution keys. No peer median lowers an unmeasured case. Until all three worker modes have
      samples the default is a floor. Existing ledger capacity, reserve, coordinator overhead and
      manager admission remain in force. Fixtures cover key churn, foreign platforms, corrupt records,
      partial coverage and unmeasured outliers.
    falsified_by: Selecting only the newest key fails learning/conservative-max; using peer hints fails learning/unmeasured-default.
  - id: AC3
    text: >
      An identical selected set of approximately 150 real cases spanning the expensive suites is
      measured with default and calibrated admission, sequentially with no gate running. Evidence
      compares every verdict, wall time, cgroup memory peaks and timeout outcomes under the unchanged
      host cap. All new guard rows have registered mutants killed at their named assertion.
    falsified_by: A changed verdict, excess memory or timeout makes the bounded comparison fail; each guard mutation must make its named row red.
required_evidence: [unit, integration]
rollback: Revert this ticket to restore stage-success-only recording and prior admission selection.
---

Owner intent: Telegram 43610, "I need to speedup veldo work". Rank 2 of the supplied speed analysis.
This amends VELDO-0219's whole-stage recording and peer-median fallback only. It authorizes no
verdict reuse, host cap increase, deadline change, live capture, full gate or full leg. Protected
path approval is reserved for landing. Targeted evidence is not a full gate claim.
