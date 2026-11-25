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
  - proof/VELDO-0219/round2/check.py
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
      and runtime stability checks, including partial red stages. Before marking a control or mutant
      resource-valid, the latest worker outcome must have the callback worker name. Resources occupy
      a separate store from elapsed estimates and reusable verdicts. Fixture coverage includes independent controls,
      valid kills, failed controls, survivors, cancellation, cleanup failure, stale input and runtime races.
    falsified_by: Moving resource recording behind stage success fails learning/red-stage; accepting an unclean worker fails learning/invalid-workers.
  - id: AC2
    text: >
      On the same platform admission uses the per-case maximum CPU rate and memory across all live
      execution keys, with a 1.15 multiplier on measured memory. No peer median lowers an unmeasured
      case. Until all three worker modes have samples the default is a floor. Existing ledger capacity, reserve, coordinator overhead and
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

## Bounded implementation evidence

Implementation commit 987b93183245b013c5a86c4bd7710e29d529aadd. The 150-case comparison
passed with identical validated verdicts and 272 clean workers per drive. Default admission
took 3543.82 seconds; calibrated admission took 3259.29 seconds (284.53 seconds, 8.03 percent saved).
Peak workers increased from 14 to 32. Scope total-memory peaks were 11.37 and 15.21 GiB under
the unchanged 16 GiB cap; worker anonymous-memory bounds were 10.78 and 11.68 GiB. No CPU
quota throttling, memory-high events, OOMs or worker errors occurred. Socket-throttling
counters are retained in the comparison, not omitted or described as zero.

All 25 registered guard falsifiers were killed at their named rows. The census is green,
personal-setup findings and stale-mutant count are zero, and engine copies are identical.
See proof/VELDO-0362/manifest.json and comparison.json. This is bounded evidence only; the
canonical gate, full legs and landing approval were not performed. No full-gate speedup
is inferred from this single pair, whose tail includes long UI mutants.
