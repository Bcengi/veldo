---
schema: veldo.spec/v1
id: VELDO-0360
title: Stop doomed gate stages at the first red
status: ready
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0216, VELDO-0358]
placement: [enforcement]
protected_paths: [scripts/gate_schedule.py, engine/scripts/gate_schedule.py, scripts/suites/wallclock_baseline.json]
footprint:
  - scripts/gate_schedule.py
  - engine/scripts/gate_schedule.py
  - scripts/check_teeth_mutations.py
  - scripts/suites/114_veldo_0216_concurrent_stages.py
  - scripts/suites/160_veldo_0358_load_leg.py
  - scripts/suites/161_veldo_0360_failfast.py
  - scripts/suites/wallclock_baseline.json
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - specs/VELDO-0360-gate-fails-fast.md
  - specs/index.md
  - proof/VELDO-0360/*
behavior_bearing: true
observability:
  logs: Preserve stage output and name the first failure in cancellation reasons.
  metrics: Existing stage measurements and grant/release events; no new clocks.
  traces: Scheduler receipt records first_failure and collect_all, with held and cancelled nodes.
  error_taxonomy: Failed prerequisites hold descendants; cancellation cannot be pass; cleanup failure refuses a successful receipt.
acceptance_criteria:
  - id: AC1
    text: Default held propagation blocks every nonpassing prerequisite, including load not_run and arbitrarily deep descendants. No pending stage starts after the first observed red.
    falsified_by: Remove the generic prerequisite guard or the first-failure pending guard; held-chain and early-red rows must fail.
  - id: AC2
    text: First red cancels active siblings, reaps their processes and descendants, removes their cgroups and releases all grants only after cleanup. Keep the first failure and partial logs/receipts. Never report green for incomplete work.
    falsified_by: Registered failfast360-cancel, failfast360-reap and failfast360-first-red remove cancellation, reaping or first-failure retention; their stopped, error-cleanup and first-red rows must fail. Native controls additionally cancel or kill an active mutation coordinator and inject a scheduler sampling exception, requiring every descendant PID, node cgroup and worker cgroup gone before any grant release.
  - id: AC3
    text: Explicit VELDO_GATE_COLLECT_ALL=1 restores diagnostic inventory execution, including mutation after load not_run. Default is fail-fast. A green control has identical stage verdicts and no cancellations in either mode.
    falsified_by: Invert the diagnostic mode guard or cancel passing nodes; collect-all and green rows must fail.
  - id: AC4
    text: Engine mirrors match, scheduler suites pass alone, wall-clock census passes with no new sites, personal setup and stale mutant scans report zero, and gate_unconfined.json is unchanged.
    falsified_by: Introduce mirror drift or a stale mutation target; the corresponding check must fail.
---

Owner intent: Telegram 43610, speed up gate work. Gate 13 and gate 15 continued mutation after an earlier red.
All graph stages are mandatory: after one fails, no sibling can produce a green gate.
The first failure is the first the scheduler observes, not a reconstructed wall-time ordering.

Diagnostic invocation: set VELDO_GATE_COLLECT_ALL=1 on the gate command. Only exact 1 opts in.
Held nodes retain not_run for load and not_started otherwise; stopped active nodes are cancelled.
The original failing node retains its verdict, return code, error and output; existing mutation receipts are untouched.

Scope is scheduler fail-fast, not admission tuning, reuse, load-fixture optimization, or changes inside mutation verdict collection.
No host load, full leg or canonical gate is authorized for this branch task. Targeted proof is partial;
independent fresh-context review, a full gate and owner approval bound to the landing commit remain required.
No independent reviewer is launched in this task because the owner prohibits sub-agents.
