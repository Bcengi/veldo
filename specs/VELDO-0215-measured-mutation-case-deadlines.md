---
schema: veldo.spec/v1
id: VELDO-0215
title: Mutation workers use their own passing case measurements
status: ready
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0214]
placement: [enforcement]
protected_paths: ["scripts/check_gate_mutations.py", "engine/scripts/check_gate_mutations.py"]
footprint:
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - scripts/check_teeth_mutations.py
  - scripts/suites/112_veldo_0215_case_deadlines.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - specs/VELDO-0215-measured-mutation-case-deadlines.md
  - specs/index.md
  - proof/VELDO-0215/*
behavior_bearing: true
observability:
  logs: Worker outcomes name the enforced deadline and elapsed seconds; invalid baseline details identify the failing control rows.
  metrics: Last passing fresh case seconds in the authority's case-time store.
  traces: Case measurement keys bind the authority checkout, case definition, execution sources and confinement leg.
  error_taxonomy: An expired worker or combined deadline is mutation_budget_exceeded; a completed failing control is invalid_baseline with its row details; malformed or missing measurements use the floor.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: each worker uses min(1800, max(120, 3 x seconds)) from its case's last passing
      fresh measurement; without a valid measurement it uses 120. Set: a measured case driven
      through real coordinator admission and child completion with a controlled monotonic clock.
      Completeness: case-deadlines/measured-worker and case-deadlines/slow-pass prove the
      deadline reaches the actual check and a worker beyond its floor but within it completes.
    falsified_by: >
      Restore the fixed deadline or drop the measured deadline at admission. Registered mutants
      deadline215-fixed-worker and deadline215-drop-measurement must fail these rows.
  - id: AC2
    text: >
      Claim: a hanging worker is killed and reaped at its own deadline, reports
      mutation_budget_exceeded and never invalid_baseline; no retry happens. Set: hanging
      baseline, no-op and mutant children. Completeness: case-deadlines/hang-timeout requires
      the timeout, cleanup and one invocation; case-deadlines/setup-timeout proves inventory
      subprocess expiry has the same taxonomy. case-deadlines/baseline-details distinguishes
      a completed false row from a timeout and retains its explanation.
    falsified_by: >
      Disable the worker check or classify its expiry as invalid_baseline. Registered mutants
      deadline215-no-expiry and deadline215-timeout-is-baseline must fail hang-timeout.
      deadline215-setup-timeout-is-driver-error must fail setup-timeout.
  - id: AC3
    text: >
      Claim: only authority coordination records fresh validated passing cases, using the maximum
      elapsed time of baseline, no-op and mutant, after input stability checks. Failed and reused
      cases record nothing. Fixtures and candidate roots cannot write the owner's store. Changed
      case definitions, suite, target, shared harness, runner or leg do not inherit the old time.
      Completeness: case-deadlines/authority-recording and case-deadlines/key-binding drive these
      boundaries; case-deadlines/bounds covers missing, malformed and extreme measurements.
    falsified_by: >
      Remove the authority-root guard, record failed cases or omit a key input. The corresponding
      registered deadline215 mutants must fail the matching rows.
  - id: AC4
    text: >
      Claim: after writing, the store uses VELDO-0214 pruning: gone authority checkouts and files
      older than 30 days are removed, including stale pending files, sparing the just-written
      file, live files and foreign files. Completeness: case-deadlines/store-pruned exercises
      these with a scratch store, never the owner's actual cache.
    falsified_by: >
      Remove pruning. Registered mutant deadline215-no-prune must fail store-pruned.
  - id: AC5
    text: >
      Claim: budget_for covers every admitted job deadline plus setup allowance even if resource
      admission serializes every job. Shared controls use the maximum of their member deadlines.
      Completeness: case-deadlines/combined-budget and case-deadlines/shared-controls check
      the combined alarm and worker deadline and the shared control deadline respectively.
    falsified_by: >
      Restore the old count-only combined cap or use the first member's control deadline.
      Registered mutants deadline215-old-stage-cap and deadline215-first-control must fail.
required_evidence: [unit, integration]
rollback: Revert both coordinator copies, suite and registry changes; workers return to the fixed 120-second deadline.
---

## Intent

Two loaded gates (2026-10-23 and 2026-10-24, 16 workers, load 15 to 23) were red while a quiet
rerun passed. receiver148-setup-clock-before-release exceeded its 120-second worker deadline;
a standalone passing run took 152 seconds. A separate gate reported invalid_baseline for
claude-completion-gate-exit-only; investigate rather than assume that verdict was a timeout.
The coordinator currently reports its deadline as mutation_budget_exceeded, while
invalid_baseline comes from completed false observations or unequal no-op observations.

## Design

The authority times workers and records the maximum baseline, no-op and mutant duration for each
fresh validated case after a passing, input-stable stage. The next deadline is
min(1800, max(120, 3 x seconds)). Missing, invalid or non-finite measurements use 120 seconds.
A genuinely slow first run can still exceed the floor; there is no retry or invented measurement.

The store is ~/.cache/veldo/mutation-case-seconds, with no environment override. Each atomic file
binds the authority checkout, full case definition, suite, target module, shared harness, authority
execution sources and confined/unconfined declaration. It stores the last passing duration and
measurement timestamp. The authority's own root alone may record to its owner store; tests use
scratch stores. Workers never record and receive only a deadline, not a writable store path.
Pruning reuses VELDO-0214's store pruning policy: 30 days or a gone checkout, sparing the file
just written and foreign names.

Shared baseline/no-op controls use the largest member deadline. The combined cap is the larger
of the previous count/parallelism cap and setup allowance plus the sum of actual job deadlines.
This conservative serial upper bound remains valid under exclusive resource admission. Reused
cases create no jobs and no measurements. Each worker still has its own hard deadline.

## Limits

This is a duration hint, not result reuse. Keys bind case execution sources, not every transitive
runtime input. Unconfined code already has the owner's permissions under VELDO-0208, so the
store is not a security boundary against that code. The hard ceiling still bounds every worker.
One last passing sample is retained, not a history or percentile. Machine load can exceed even
the measured allowance; that remains a visible timeout, never a silently retried case.

## Protected paths and approval

scripts/check_gate_mutations.py and engine/scripts/check_gate_mutations.py are protected.
Landing requires separate commit-bound human approval. The implementing agent authors none.
