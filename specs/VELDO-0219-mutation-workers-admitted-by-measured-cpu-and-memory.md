---
schema: veldo.spec/v1
id: VELDO-0219
title: Mutation workers are admitted by measured CPU and memory, not a fixed count of 16
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
  logs: Each admission names the job, its measured CPU rate and memory, the allowance it fit under, and how long it waited and for which resource.
  metrics: Per case CPU seconds and peak anonymous memory in the VELDO-0215 case store; per stage peak concurrent workers, mean busy cores and peak memory against the allowance.
  traces: A case's resource measurement uses the same key as its VELDO-0215 time measurement, so a changed case starts from defaults again.
  error_taxonomy: A job whose measured need exceeds the whole allowance is invalid_resource_requirement (RED); an unmeasured job uses the stated defaults; a worker cgroup that cannot be created stops the stage as worker_launch_error.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: the authority records, for every fresh validated case, the CPU seconds and peak
      anonymous memory of each of its workers, measured from a cgroup of its own under the
      gate's delegated scope (VELDO-0220) and including the cgroups of units it started through
      the user manager, read before cleanup; the values are stored beside VELDO-0215's elapsed
      peaks with the same key, rolling 30-day maximum and pruning. Set: a fixture case with a
      CPU-bound child, one with a memory-heavy child, one that starts a user unit, and a failing
      case. Completeness: row admission/measured-per-case requires each measured value within 10
      percent of the fixture's known load, the unit's share included, and nothing recorded for the
      failing case.
    falsified_by: >
      Read CPU from the worker process alone, without its descendants and units. Registered
      mutant admission219-parent-cpu-only must fail admission/measured-per-case.
  - id: AC2
    text: >
      Claim: the coordinator admits a job only while the summed measured CPU rate of running jobs
      plus its own fits the CPU allowance (the CPUs it may use, bounded by the cgroup quota and by
      the share VELDO-0216's scheduler hands it) and the summed measured memory plus its own fits
      the memory allowance; an unmeasured job counts as one core and the largest measured memory
      of any case (or 1 GiB with none). There is no fixed ceiling of 16; the ceiling is twice the
      usable CPUs, the floor stays 2, and resource capacities (systemd_user_manager,
      new_project_fixture) still apply. Set: allowances of 4, 20 and 40 cores and of 4, 16 and 31
      GiB over a fixture inventory with known measurements. Completeness: row
      admission/fits-allowance requires the peak summed demand never to exceed either allowance
      and the stage to reach the allowance when work is pending.
    falsified_by: >
      Restore the clamp to 16 workers. Registered mutant admission219-fixed-sixteen must fail
      admission/fits-allowance at the 40-core allowance.
  - id: AC3
    text: >
      Claim: admission changes neither a verdict nor a budget. Every worker keeps the VELDO-0215
      deadline, min(1800, max(120, 3 x its case's largest passing fresh seconds)), and the combined
      cap keeps VELDO-0123's 2 seconds per registered case at 8 reference workers (and
      VELDO-0215's phase bound where larger), so more workers buy margin, never a tighter cap.
      Set: one fixture inventory run at admissions of 2, 8, 16 and measured. Completeness: row
      admission/same-verdicts requires identical verdict fields in all four receipts, the same
      budget_seconds, and every worker's enforced deadline equal to its measured deadline.
    falsified_by: >
      Scale the combined cap down with the admitted worker count. Registered mutant
      admission219-cap-shrinks must fail admission/same-verdicts.
  - id: AC4
    text: >
      Claim: on the qualification host a fresh full mutation stage under measured admission
      finishes in at most 4,000 seconds against the measured 5,207, with zero worker deadline
      expiries and zero invalid baselines. Set: one force-fresh canonical gate at the landing
      candidate, on a host the VELDO-0220 lock holds. Completeness: the proof records the stage's
      elapsed time, peak workers, mean busy cores, peak memory, and for every case its elapsed time
      against its deadline.
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
the fixed count of 16 in worker_count(), not the host. The stage's memory peaked at 8.25 GiB
(cgroup memory, which includes reclaimable page cache) under a 16 GiB scope.

## Design

Measure, then admit. VELDO-0215 already keeps, per case and key, the largest passing fresh
elapsed time over 30 days. This spec adds CPU seconds and peak anonymous memory to the same
record. Each worker runs in its own cgroup under the gate's delegated user scope: the authority's
worker bootstrap (scripts/reuse_worker.py) moves itself into it before it loads any candidate code,
and the coordinator reads cpu.stat and memory.stat when the worker ends. Units the case starts
through the user manager are already in its ownership ledger; their cgroups are read before
cleanup removes them.

Admission replaces the count. The coordinator's existing SuiteResources admission (positive slots
and exclusive holds) gains two more resources, cpu and memory, whose capacities are the allowances
and whose per-job demand is the case's measured rate (CPU seconds over elapsed seconds, from the
case's slowest passing run) and memory. Baseline and no-op controls use their group's largest
member, as VELDO-0215 does for deadlines. The existing rule that a waiting job bars later users of
the resource it waits for keeps a large job from starving.

Deadlines are VELDO-0215's. That spec, ready on its own branch, replaces the flat 120-second worker
deadline with min(1800, max(120, 3 x measured)); a case measured at 63 seconds on a quiet host then
gets 189 seconds instead of missing 120 under load. Admission is what keeps that multiple honest:
CPU is never oversubscribed by the gate itself, so a case's elapsed time under the gate's own load
stays near its measurement. (A 16-worker sample on 2026-10-25 at about 91 percent host busy did
reach a worker deadline; it is excluded from the measurement as incomplete.)

Expected time: at 0.68 cores per worker, 18 usable cores admit about 26 workers; the stage becomes
CPU bound at about 56,170 / 18 = 3,100 seconds, or about 3,300 with the control-phase tail, a saving
of about 1,900 to 2,100 seconds. Memory is the other bound: if anonymous memory per worker is near
the cgroup figure (0.52 GiB), 26 workers need about 13.5 GiB, inside the 16 GiB scope with
VELDO-0216 sharing it; the measured values decide. Together with VELDO-0216 the whole gate becomes
CPU bound; see the full-run estimate there and in VELDO-0221.

VELDO-0123's notes describe workers clamped to 2..16 (row gate/workers-follow-the-host). This spec
amends that note and that row: the floor of 2 and the cgroup quota stay; the ceiling of 16 becomes
measured admission under twice the usable CPUs. AC3 of VELDO-0123, the combined cap, is unchanged.

## Out of scope

The case deadlines' formula (VELDO-0215); the resource capacities declared in the manifest; the
pre-mutation stages (VELDO-0216, VELDO-0221); host load from other jobs (VELDO-0220).

## What the reviewer judges

Normal use: the canonical gate and landing gates on the qualification host, in the owner's gate
scope. Threat model: as in VELDO-0208; measurements are written only by the authority, as in
VELDO-0215. Out of review scope: a case whose resource use jumps far beyond its 30-day peak in one
run (its deadline and the memory limit of the gate scope still bound it), and hosts without cgroup
v2 delegation (the stage refuses by name rather than guessing).

## Notes

Numbers are from /tmp/veldo-mutation-throughput-20261025 (full-gate-result.json, final-summary.json,
canonical-mutations.json). Written to apply after the pending stack (3ab6e90d) and VELDO-0215 land.
