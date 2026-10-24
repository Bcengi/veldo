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
  - scripts/suites/99_veldo_0205_reuse.py
  - scripts/suites/112_veldo_0215_case_deadlines.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - specs/VELDO-0215-measured-mutation-case-deadlines.md
  - specs/index.md
  - proof/VELDO-0215/*
behavior_bearing: true
observability:
  logs: Worker outcomes name the enforced deadline and elapsed seconds; invalid baseline details identify the failing control rows.
  metrics: Largest passing fresh case seconds within 30 days in the authority's case-time store.
  traces: Case measurement keys bind the authority checkout, case definition, execution sources and confinement leg.
  error_taxonomy: An expired worker or combined deadline is mutation_budget_exceeded; a completed failing control is invalid_baseline with its row details; malformed or missing measurements use the floor.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: each worker uses min(1800, max(120, 3 x seconds)) from its case's largest passing
      fresh measurement within 30 days; without a valid measurement it uses 120. Set: a measured case driven
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
      cases record nothing. Library/fixture calls cannot write the owner's store. The authority CLI
      records even when verifying a candidate in another root (case-deadlines/candidate-authority). Changed
      case definitions, suite, target, shared harness, runner or leg do not inherit the old time.
      Completeness: case-deadlines/authority-recording and case-deadlines/key-binding drive these
      boundaries; case-deadlines/bounds covers missing, malformed and extreme measurements.
    falsified_by: >
      Remove the authority-entry guard, drop the CLI recording flag, record failed cases or omit a key input. The corresponding
      registered deadline215 mutants must fail the matching rows.
  - id: AC4
    text: >
      Claim: after writing, the store uses VELDO-0214 pruning: gone authority checkouts and files
      older than 30 days are removed, including stale pending files, sparing the just-written
      file, live files and foreign files. Completeness: case-deadlines/store-pruned exercises
      these with a scratch store, never the owner's actual cache. The rolling-maximum row
      proves a smaller subsequent sample cannot lower a live peak, and expired peaks disappear.
    falsified_by: >
      Remove pruning or overwrite a live peak with the latest sample. Registered mutants
      deadline215-no-prune and deadline215-latest-sample must fail their respective rows.
  - id: AC5
    text: >
      Claim: budget_for bounds each scheduling phase using worker load, its final tail and
      resource admission chains, plus setup allowance, never below the old count-based cap. Shared controls use the maximum of their member deadlines.
      Completeness: case-deadlines/combined-budget and case-deadlines/shared-controls check
      the combined alarm and worker deadline and the shared control deadline respectively.
    falsified_by: >
      Restore the old count-only combined cap, sum all deadlines serially, or use the first
      member's control deadline. Registered mutants deadline215-old-stage-cap,
      deadline215-serial-stage-cap and deadline215-first-control must fail.
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
execution sources and confined/unconfined declaration. It stores the rolling maximum and timestamped candidate peaks for the last 30 days.
A newer sample removes older samples no larger than itself; older larger samples keep their
original timestamps, so quiet runs neither lower a live peak nor renew its expiry. Readers
also discard expired samples. Legacy single samples use their file modification time. Only the authority CLI opts into the owner store, including when checking
a landing candidate in another root; library calls stand down and tests use scratch stores. Workers never record and receive only a deadline, not a writable store path.
Pruning reuses VELDO-0214's store pruning policy: 30 days or a gone checkout, sparing the file
just written and foreign names.

Shared baseline/no-op controls use the largest member deadline. Reused cases create no jobs
and no measurements. Each worker still has its own hard deadline.

### Combined bound derived from admission

Controls finish before mutant admission starts, so calculate and add two phase bounds.
For each phase let W be the sum of job deadlines, L the largest deadline (zero if empty),
and m the worker count. The phase bound is min(W, W/m + L + sum(R_r)). The stage cap is
max(old count/parallelism cap, BUDGET + sum(phase bounds)). BUDGET remains 120 seconds
for setup; the old cap is 2 * inventory_count * 8 / max(1, min(m, 8)).

SuiteResources reserves each job's declared slot demand for its entire process lifetime,
resolves exclusive to the effective capacity C_r, and bars later users of every resource of
a blocked request. Workers fills available worker slots using select(), then polls completions.
Whenever pending work exists, either all m workers are occupied (charge at most W/m), or
the first pending job cannot obtain a resource. That first job cannot be barred by an earlier
pending request. If resource r is full, charge its occupied time to
sum(demand_jr * deadline_j) / C_r. If it is partially occupied but still cannot admit the
first job, that job needs more than one slot. No later user of r can pass it. All earlier
users have already started, so this partial-occupancy wait lasts at most the largest deadline
of preceding users of r. Charge that prefix maximum once for each request needing more
than one slot. Thus R_r is the capacity-normalized slot-time plus these prefix tails.
This handles exclusive requests, arbitrary positive slot demands, capacity overrides and
jobs using multiple resources. A simple sum(deadlines)/capacity alone misses exclusive
reservations and the draining time imposed by admission barriers.

After the final pending job starts, all active jobs finish within L. Summing the charges is
conservative even where they overlap. The serial W is also a valid phase bound because a
nonempty pending queue with no active workers always admits its first valid job; taking the
smaller bound avoids charging more than serialization on small or resource-heavy phases.
The bound assumes coordinator launch, polling and cleanup overhead fit the setup/count
margin, as does the individual worker timing contract; scheduling faults still hit the cap.


### Round 2 full inventory

Read-only planning after the round 2 targeted runs, with the current authority store and
16 workers, produces 53,800.03908249566 seconds (14.94 hours). All 2,571 cases are planned
fresh: 744 control jobs and 2,571 mutant jobs. The phase bounds are 10,541.692777487835 and
43,138.34630500783 seconds, plus 120 seconds setup. The old count-only cap is 5,142 seconds;
the serial formula on these same inputs would be 403,020.9012210875 seconds (4.66 days).
46 current-key measurements exceed the floor. Changes to the coordinator invalidate earlier
keys by design; no old-key samples were transplanted. The calculation and per-resource
breakdown are in proof/VELDO-0215/round2/full-inventory-cap.json, reproducible with
`python3 proof/VELDO-0215/round2/calculate_cap.py`. No full gate ran for this calculation.

## Limits

This is a duration hint, not result reuse. Keys bind case execution sources, not every transitive
runtime input. Unconfined code already has the owner's permissions under VELDO-0208, so the
store is not a security boundary against that code. The hard ceiling still bounds every worker.
Only undominated samples within 30 days are retained, not a percentile. Machine load can exceed even
the measured allowance; that remains a visible timeout, never a silently retried case.

## Protected paths and approval

scripts/check_gate_mutations.py and engine/scripts/check_gate_mutations.py are protected.
Landing requires separate commit-bound human approval. The implementing agent authors none.
