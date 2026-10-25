---
schema: veldo.spec/v1
id: VELDO-0219
title: Mutation workers are admitted by measured CPU and memory from the gate-wide ledger, not a fixed count of 16
status: draft
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0123, VELDO-0215, VELDO-0216, VELDO-0220]
placement: [enforcement]
protected_paths: ["scripts/check_gate_mutations.py", "engine/scripts/check_gate_mutations.py", "scripts/reuse_worker.py", "engine/scripts/reuse_worker.py"]
footprint:
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - scripts/reuse_worker.py
  - engine/scripts/reuse_worker.py
  - scripts/mutation_ownership.py
  - engine/scripts/mutation_ownership.py
  - scripts/check_teeth_mutations.py
  - scripts/suites/53_veldo_0123_mutations.py
  - scripts/suites/*_veldo_0215_*.py
  - scripts/suites/*_veldo_0219_*.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - specs/VELDO-0123-mutation-drivers-in-every-gate.md
  - specs/VELDO-0219-mutation-workers-admitted-by-measured-cpu-and-memory.md
  - specs/index.md
  - proof/VELDO-0219/*
behavior_bearing: true
observability:
  logs: Each admission names the job, its CPU and memory claim and where the claim came from (this key, the previous key, the suite median or the default), the ledger state it fit under, and how long it waited and for which resource.
  metrics: Per case CPU seconds, elapsed seconds and peak anonymous memory per passing fresh run in the VELDO-0215 case store; per stage peak concurrent workers, mean busy cores and peak memory against the ledger's capacities.
  traces: A case's resource record uses the same key as its VELDO-0215 time record; a claim derived from a previous key or a suite median says so.
  error_taxonomy: A claim larger than the whole capacity is invalid_resource_requirement (RED); a worker cgroup that cannot be created stops the stage as worker_launch_error.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: the authority records, for every passing fresh run of a case, each worker's CPU
      seconds, elapsed seconds and peak anonymous memory, measured from a cgroup of its own under
      the gate's delegated scope (VELDO-0220) and including the cgroups of units it started, read
      before cleanup; the store keeps them beside VELDO-0215's elapsed peaks with the same key,
      30-day window and pruning. A worker's CPU claim is its CPU seconds divided by the fastest
      passing elapsed in the window (the highest rate, so demand is never undercounted); its memory
      claim is the largest peak in the window. Set: a fixture case with a CPU-bound child, one with a
      memory-heavy child, one that starts a user unit, one measured twice at different speeds, and a
      failing case. Completeness: row admission/measured-per-case requires each value within 10
      percent of the fixture's known load, the unit's share included, the claim taken from the
      faster run, and nothing recorded for the failing case.
    falsified_by: >
      Divide by the slowest elapsed instead of the fastest. Registered mutant
      admission219-slowest-rate must fail admission/measured-per-case.
  - id: AC2
    text: >
      Claim: the coordinator claims every worker from the gate-wide ledger of VELDO-0216 and starts
      it only when the ledger grants the claim; there is no fixed ceiling of 16 (the ceiling is
      twice the usable CPUs, the floor stays 2), and the manifest's capacities
      (systemd_user_manager, new_project_fixture) still apply. A case with no record under its
      current key claims, in order, its record under the previous key of the same case identity, the
      median of its suite's recorded cases, the median of all recorded cases, or one core and 1 GiB
      when the store is empty. Set: ledger capacities of 4, 20
      and 40 cores and of 4, 16 and 31 GiB over a fixture inventory with known measurements, and
      the real 2,689-case inventory with every current key unmeasured and the previous keys'
      records present. Completeness: row
      admission/fits-ledger requires the summed granted claims within capacity at every instant and
      the stage at capacity while work is pending; row admission/unmeasured-inventory requires the
      all-unmeasured inventory to admit at least 16 workers on the qualification host's
      capacities.
    falsified_by: >
      Restore the clamp to 16 workers. Registered mutant admission219-fixed-sixteen must fail
      admission/fits-ledger at the 40-core capacity.
  - id: AC3
    text: >
      Claim: admission changes neither a verdict nor a budget rule. Every worker keeps the VELDO-0215
      deadline, min(1800, max(120, 3 x its case's largest passing fresh seconds)). The combined cap
      stays max(VELDO-0123's 2 seconds per registered case at 8 reference workers, VELDO-0215's 120
      seconds plus the two phase bounds); in VELDO-0215's phase bound min(W, W/m + L + sum(R_r)),
      m is the smallest number of workers the ledger is guaranteed to admit at once (the CPU
      capacity divided by the largest CPU claim, and the memory capacity divided by the largest
      memory claim, whichever is smaller, never below 2), and cpu and memory join the resources r,
      each charged sum(claim_j x deadline_j) / capacity like any other resource. Set: one fixture
      inventory run at 2, 8, 16 and measured admission. Completeness: row admission/same-verdicts
      requires identical verdict fields in all four receipts, every enforced deadline equal to its
      measured deadline, and the recorded cap equal to the formula with the stated m and charges.
    falsified_by: >
      Use the peak admitted worker count as m. Registered mutant admission219-optimistic-m must fail
      admission/same-verdicts.
  - id: AC4
    text: >
      Claim: on the qualification host a fresh full mutation stage under measured admission finishes
      in at most 4,000 seconds against the measured 5,207, with zero worker deadline expiries and zero
      invalid baselines, on a quiet host held by the VELDO-0220 lock. Set: one force-fresh canonical
      gate at the landing candidate. Completeness: the proof records the stage's elapsed time, peak
      workers, mean busy cores, peak memory, and for every case its elapsed time against its deadline
      and against its quiet measurement.
    falsified_by: >
      Run the canonical gate with the fixed 16 workers; the stage takes about 5,200 seconds and the
      4,000-second check fails.
required_evidence: [unit, integration]
rollback: Revert to worker_count(); the stage runs 2 to 16 workers by CPU count, as before.
---

## Intent

The 2026-10-25 canonical mutation stage ran 16 workers for 5,207 seconds. Its 3,481 workers summed
82,740 worker seconds against 83,312 available slot seconds, so the 16 slots were 99 percent busy,
while the stage used 56,170 CPU seconds: 10.8 of the host's 20 cores. Each running worker used 0.68
of a core on average, because fixtures wait on child processes, services and sockets. The limit was
the fixed count of 16 in worker_count(), not the host. The stage's cgroup memory peaked at 8.25 GiB,
page cache included, under a 16 GiB scope.

## Design

Measure, then claim. VELDO-0215 keeps, per case and key, the largest passing fresh elapsed time over
30 days. This spec adds per run the CPU seconds, elapsed seconds and peak anonymous memory. Each
worker runs in its own cgroup under the gate's delegated scope: the authority's worker bootstrap
(scripts/reuse_worker.py) moves itself into it before it loads any candidate code, and the
coordinator reads cpu.stat and memory.stat when the worker ends. Units the case starts are already
in its ownership ledger; their cgroups are read before cleanup removes them.

Claims come from the fastest passing run's rate so a run slowed by load never lowers the claim. A
key reset (any change to a case's inputs) would otherwise leave every changed case at the default; the
previous key's record for the same case identity is the next best estimate, and the suite median
after that. Baseline and no-op controls claim their group's largest member, as VELDO-0215 does for
deadlines.

The ledger is VELDO-0216's: the coordinator, the shard dispatchers of VELDO-0221 and the stage
nodes draw from the same CPU, memory and manager capacities, so the mutation stage takes the cores
the other nodes leave and gives them back as they finish. The coordinator's own admission rules
(slots, exclusive holds, the rule that a waiting job bars later users of its resource) apply first;
the ledger decides last.

Deadlines are VELDO-0215's, ready on its own branch: min(1800, max(120, 3 x measured)), so a case
measured at 63 seconds on a quiet host gets 189 seconds instead of missing 120 under load. Admission
keeps that multiple honest: the gate never oversubscribes CPU itself, so a case's elapsed time under
the gate's own load stays near its measurement. A rejection that rests on a worker that ran far
slower than its measurement, or ran while other work contended, counts only when it repeats; that
rule is VELDO-0223's, and AC4 requires that it never fires on a quiet host.

Expected time: at 0.68 cores per worker, 18 usable cores admit about 26 workers; the stage becomes
CPU bound at about 56,170 / 18 = 3,100 seconds, about 3,300 with the control-phase tail: a saving of
about 1,900 to 2,100 seconds on a full fresh run, and proportionally on every landing's mutation
work. Memory is the other bound: at 0.52 GiB per worker (the cgroup figure, an upper estimate), 26
workers need about 13.5 GiB inside the 16 GiB scope the other nodes share; the measured anonymous
figures decide.

VELDO-0123's notes describe workers clamped to 2..16 (row gate/workers-follow-the-host). This spec
amends that note and that row: the floor of 2 and the cgroup quota stay; the ceiling of 16 becomes
the ledger's grant under twice the usable CPUs. VELDO-0123's AC3, the 2 seconds per case cap, is
unchanged.

## Out of scope

The case deadlines' formula (VELDO-0215); the manifest's capacities; the pre-mutation stages
(VELDO-0216, VELDO-0221); host load from other jobs (VELDO-0220, VELDO-0223).

## What the reviewer judges

Normal use: the canonical and landing gates on the qualification host, in the gate's scope. Threat
model: as in VELDO-0208; measurements are written only by the authority, as in VELDO-0215. Out of
review scope: hosts without cgroup v2 delegation (the stage refuses by name rather than guessing).

## Notes

Numbers are from /tmp/veldo-mutation-throughput-20261025 (full-gate-result.json, final-summary.json,
canonical-mutations.json). Written to apply after the pending stack (3ab6e90d) and VELDO-0215 land.
