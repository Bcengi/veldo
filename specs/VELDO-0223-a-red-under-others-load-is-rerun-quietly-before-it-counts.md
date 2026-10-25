---
schema: veldo.spec/v1
id: VELDO-0223
title: A result under someone else's load is rerun quietly before it counts, and an unconfirmed red is invalid
status: ready
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0214, VELDO-0215, VELDO-0216, VELDO-0219, VELDO-0220]
placement: [enforcement]
protected_paths: ["scripts/verify.sh", "engine/scripts/verify.sh", "scripts/gate_legs.py", "engine/scripts/gate_legs.py", "scripts/check_gate_mutations.py", "engine/scripts/check_gate_mutations.py", "scripts/gate_host.py", "engine/scripts/gate_host.py", "scripts/gate_schedule.py", "engine/scripts/gate_schedule.py", "scripts/gate_host.json"]
footprint:
  - scripts/verify.sh
  - engine/scripts/verify.sh
  - scripts/gate_host.py
  - engine/scripts/gate_host.py
  - scripts/gate_host.json
  - scripts/gate_schedule.py
  - engine/scripts/gate_schedule.py
  - scripts/gate_legs.py
  - engine/scripts/gate_legs.py
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - scripts/mutation_ownership.py
  - engine/scripts/mutation_ownership.py
  - .veldo/control_event_vocabulary.py
  - engine/.veldo/control_event_vocabulary.py
  - .veldo/metrics.py
  - engine/.veldo/metrics.py
  - .veldo/executor.py
  - engine/.veldo/executor.py
  - .veldo/lander.py
  - engine/.veldo/lander.py
  - .veldo/control_proof.py
  - engine/.veldo/control_proof.py
  - scripts/check_teeth_mutations.py
  - scripts/suites/*_veldo_0223_*.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - specs/VELDO-0223-a-red-under-others-load-is-rerun-quietly-before-it-counts.md
  - specs/index.md
  - proof/VELDO-0223/*
behavior_bearing: true
observability:
  logs: The gate prints, per failing stage, leg, shard or case, whether its span was contended, the quiet rerun and its result; at the end the share of contended samples and the worst one.
  metrics: Five-second samples of host busy cores, the gate's own cores (its scope plus the cgroups of units in its ownership ledgers), the scope's CPU and memory pressure; counts of quiet reruns, confirmed reds, unconfirmed reds and repeated rejections.
  traces: The stamp and the gate event carry the contention summary and the list of reruns with both results.
  error_taxonomy: A red confirmed by a quiet rerun is RED; a red not confirmed is INVALID (exit 3, status invalid, event gate.invalid); a rejection that does not repeat is mutation_survived (RED); a contended run records no measurement.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: the gate measures contention from counters it can attribute: other work is contending
      in a sample when busy cores not the gate's exceed the tolerance in scripts/gate_host.json
      (2 cores or 10 percent of the host, whichever is larger), where the gate's cores are its
      scope's plus the cgroups of every unit and slice in its workers' ownership ledgers (units the
      user manager starts run outside the scope but are the gate's load), or when the scope's own
      memory pressure, not the host's, exceeds the tolerance. Set: a quiet fixture run, one whose
      workers start user units that burn CPU, one with a synthetic CPU load and one with a memory
      load outside the scope. Completeness: row contention/attributed requires only the last two to
      count as contending.
    falsified_by: >
      Count the gate's own user units as outside load. Registered mutant contention223-units-external
      must fail contention/attributed.
  - id: AC2
    text: >
      Claim: a failure whose span was contended is not reported yet: the gate waits until the host
      is quiet (or the configured wait expires) and reruns exactly the failing units of work within
      the same gate (a failing shard, leg or stage, or a failing mutation case with its controls);
      a failure that repeats on a quiet host is RED; a failure that does not repeat, or whose rerun
      itself ran contended because the wait for a quiet host expired, makes the gate INVALID (exit
      3, status invalid, event gate.invalid, terminal GATE: INVALID), never GREEN; a failure on a
      quiet host is RED at once; a pass is a pass. Set: a fixture failure under synthetic load that
      repeats quietly, one that does not repeat, one whose rerun stays under load past the wait, and
      one on a quiet host. Completeness: row contention/quiet-rerun drives the four through
      verify.sh and requires RED, INVALID, INVALID and RED.
    falsified_by: >
      Report an unconfirmed contended failure as RED without rerunning. Registered mutant
      contention223-no-rerun must fail contention/quiet-rerun.
  - id: AC3
    text: >
      Claim: a load can never make a mutant look killed. A rejection counts only when its mutant
      worker's span was quiet and its elapsed time was within twice its case's quiet measurement
      (VELDO-0215); otherwise the mutant is run again once on a quiet host, and only a repeated
      rejection counts; a mutant that survives the repeat is mutation_survived, RED. Set: a fixture
      mutant whose target row fails only when its worker is slowed, run under synthetic load, and the
      same mutant whose target row fails on its own. Completeness: row contention/rejection-repeats
      requires the first to be repeated and reported mutation_survived and the second accepted.
    falsified_by: >
      Accept a contended rejection without repeating it. Registered mutant
      contention223-contended-kill-counts must fail contention/rejection-repeats.
  - id: AC4
    text: >
      Claim: a contended run records no measurement (no leg time of VELDO-0214, no case time of
      VELDO-0215, no case CPU or memory of VELDO-0219), and INVALID is never recorded or charged as
      a red: the executor, the lander and the proof store treat it as a gate that has not decided.
      Set: a passing run under synthetic load followed by a quiet one; an INVALID result met by the
      executor, a landing attempt and a proof capture. Completeness: rows
      contention/no-measurement and contention/invalid-not-red require the stores unchanged by the
      first run and updated by the second, and no red recorded anywhere for the INVALID result.
    falsified_by: >
      Record leg and case times from a contended run. Registered mutant
      contention223-records-contended must fail contention/no-measurement.
required_evidence: [unit, integration]
rollback: Remove the contention section of scripts/gate_host.json; the gate then judges every result as it does today.
---

## Intent

Two loaded gates on 2026-10-23 and 2026-10-24 were red while a quiet rerun passed (VELDO-0215's
intent records a worker past 120 seconds at host load 15 to 23). Suites also carry their own timing
assertions: the factory loop's scenario deadline is 45 seconds with 8-second waits, and its ten
mutants were invalid baselines in one run and valid rejections in another with the suite and its
targets byte-identical; scheduling sensitivity is the plausible cause, not a proven one. Each such
red cost a full rerun, three hours today, and was reported as the change's red. Load can also err
the other way: a target row that fails because its worker was slowed would count as a killed
mutant, a false green. VELDO-0220 makes other gates wait; this spec judges what still contends.

## Design

The sampler lives in scripts/gate_host.py and reads, every 5 seconds, /proc/stat, the scope's
cpu.stat and memory.pressure, and the cpu.stat of every cgroup named in the workers' ownership
ledgers (VELDO-0208 already records each unit and slice a worker starts). Host-wide memory pressure
is not used: it rises with the gate's own memory use.

The rerun is narrow and inside the same gate. With VELDO-0221 a failing unit or integration result
is a shard, so only that shard reruns; a failing mutation case reruns with its own controls. The
scheduler holds new work while it waits for a quiet window, so the rerun runs on a quiet host.

What does not change: every assertion, every case and every confinement rule. A pass under load is
still a pass, because every assertion held; a rejection is the exception, because a rejection is the
absence of a pass, and AC3 requires it to repeat when it may be load.

Expected time: none on a quiet host; on a contended one, the rerun of the failing work instead of a
three-hour gate.

## Out of scope

The lock and the scope (VELDO-0220); changing any suite's own timing assertion.

## What the reviewer judges

Normal use: gates on this host with the lock held. Threat model: as in VELDO-0208. Candidate code
cannot set the classification: it is computed by the authority from counters outside the candidate's
write grants, and an unconfined leg that forged load could only turn its own red into a rerun or
INVALID, neither of which lands. Out of review scope: load that shows in no sampled counter (for
example disk input and output without CPU or memory pressure).
