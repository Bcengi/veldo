---
schema: veldo.spec/v1
id: VELDO-0290
title: Suites that measure wall-clock time declare it, and the gate ledger keeps CPU headroom while one of them runs
status: draft
risk: high
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: [VELDO-0216, VELDO-0219]
placement: [enforcement]
protected_paths: []
footprint:
  - scripts/gate_schedule.py
  - engine/scripts/gate_schedule.py
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - scripts/mutation_ownership.py
  - engine/scripts/mutation_ownership.py
  - scripts/gate_graph.json
  - scripts/suites/manifest.json
  - scripts/suites/114_veldo_0216_concurrent_stages.py
  - scripts/suites/115_veldo_0219_measured_admission.py
  - scripts/check_teeth_mutations.py
  - specs/VELDO-0290-wall-clock-suites-run-with-cpu-headroom-in-the-gate.md
  - specs/VELDO-0219-mutation-workers-admitted-by-measured-cpu-and-memory.md
  - specs/index.md
  - proof/VELDO-0290/**
behavior_bearing: true
observability:
  logs: >
    Each ledger grant and refusal line says whether the wall-clock ceiling was in force. A claim refused
    by the ceiling or by a waiting wall-clock claim names resource wall_clock.
  metrics: >
    Each worker outcome carries stall_seconds, the time its cgroup and the units it accounts spent with
    a task waiting for a CPU. Each admission event carries the ceiling state it was granted under. The
    receipt carries the ceiling value and the seconds the stage spent under it.
  traces: >
    A worker's stall_seconds sits in the same outcome as its cpu_seconds and elapsed, so a red control
    is read beside its own starvation figure.
  error_taxonomy: >
    A wall_clock claim larger than the ceiling, a ceiling above the CPU capacity, and a manifest
    wall_clock value that is not a non-empty string are invalid_resource_requirement (RED). No verdict
    changes: stall_seconds never excuses or reruns a red control.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: while a wall_clock claim is held, or is the claim being admitted, the ledger grants CPU
      only up to wall_clock_ceiling.cpu from scripts/gate_graph.json, and the refusal names resource
      wall_clock. With no wall_clock claim held or waiting, the ledger grants to its full capacity as
      it does today. Set: a Ledger of 20 cores with a ceiling of 11, driven with one-core claims.
      Completeness: row admission/wall-clock-ceiling (suite 115, or the ledger's suite 114) holds one
      wall_clock claim of 1 core and requires ten more one-core claims granted, the eleventh refused
      with resource wall_clock, and a wall_clock claim arriving with 15 cores held refused the same
      way. Row admission/full-capacity-without-wall-clock requires twenty one-core claims granted and
      the twenty-first refused naming cpu. The first row is red at 646ff7c8, where all claims are
      granted to 20; the second is green before and after and guards throughput.
    falsified_by: >
      Apply the ceiling only to wall_clock claims, so other claims are granted beside a held one up to
      capacity. Registered mutant admission290-ceiling-not-for-others must turn
      admission/wall-clock-ceiling red.
  - id: AC2
    text: >
      Claim: a wall_clock claim refused for CPU bars every later CPU grant to a claim that is not
      wall_clock until it is granted or its claimant withdraws, so bulk work cannot keep it waiting.
      Set: a Ledger of 20 cores with a ceiling of 11 and 15 cores held by ordinary claims.
      Completeness: row admission/wall-clock-waiting-bars requires the wall_clock claim refused, a
      following one-core ordinary claim refused with resource wall_clock although 5 cores are free,
      the wall_clock claim granted once releases bring the total under the ceiling, and the ordinary
      claim granted after that up to the ceiling. A second leg withdraws the waiting claimant and
      requires the ordinary claim granted. Red at 646ff7c8, where the ordinary claim is granted at once.
    falsified_by: >
      Do not record the waiting wall_clock claim. Registered mutant admission290-no-waiting-bar must
      turn admission/wall-clock-waiting-bars red.
  - id: AC3
    text: >
      Claim: the manifest declares the class and the mutation coordinator carries it to the ledger.
      Every suite in scripts/suites/manifest.json with a wall_clock field names a non-empty bound in
      it; the seven suites that have failed a control this way are declared; every job of a declared
      suite, baseline, noop and mutant, is claimed as wall_clock; and the declared suites' jobs are
      adjacent in the pending order. Set: the real manifest, and Workers.run over a fixture inventory
      with a recording ledger client and a manifest that declares one of three suites.
      Completeness: row admission/declared-bounds requires the seven named suites declared and no
      empty or non-string value. Row admission/wall-clock-end-to-end requires every acquire for the
      declared suite sent with wall_clock true and none for the others, every admission granted
      while one of that suite's jobs was held at or under the ceiling, and no undeclared job between
      the first and last declared job in the order submitted. Both rows are red at 646ff7c8.
    falsified_by: >
      Stop passing the declaration from SuiteResources to the ledger client. Registered mutant
      admission290-declaration-not-passed must turn admission/wall-clock-end-to-end red.
  - id: AC4
    text: >
      Claim: with the ceiling on, the declared suites' controls stop losing their CPU under the
      stage's own load, and each worker outcome says how long it stalled. Set: a replay on the
      qualification host, outside the gate, of the declared suites' baseline controls beside real
      bulk mutant jobs from the current inventory, through the coordinator and a scratch ledger, in
      two arms: ceiling off (claims admitted to 20 of 20 cores, as at 646ff7c8) and ceiling on. Each
      arm has at least 150 control runs. Completeness: proof/VELDO-0290/replay.json records, per arm,
      the control runs, every failed row by name, the stall_seconds of every control (minimum,
      median, 95th percentile, maximum), peak workers, the stage wall time and the admission record's
      seconds under the ceiling. The fix is shown when the off arm has a timing-row failure or
      clearly higher stall_seconds in declared suites, and the on arm has no timing-row failure and
      a 95th percentile stall in declared suites under 1 second. If the off arm shows neither, the
      replay did not reach the stage's load: the round says so and does not claim the fix. Row
      admission/stall-recorded (suite 115) runs WorkerMeter over a fixture cgroup tree whose
      cpu.pressure "some" total moves by a known amount in the worker cgroup and in one accounted
      unit, and requires stall_seconds equal to the sum, each cgroup counted once, and a red control
      with a large stall_seconds still judged red and not rerun.
    falsified_by: >
      The off arm of the replay is the red-before for the behavior. For the measurement, read only
      the worker's own cgroup and leave out its units. Registered mutant
      admission290-stall-skips-units must turn admission/stall-recorded red.
required_evidence: [unit, integration]
rollback: >
  Remove wall_clock_ceiling from scripts/gate_graph.json and revert the commit. The ledger again grants
  to full capacity for every claim. The manifest's wall_clock fields and the recorded stall_seconds are
  inert without the ceiling, and no stored record depends on them.
---

## Intent

Six gates in a row on landing-c went red in the mutation stage, each on a different control. The analysis
(landing-c-flake-pattern-2026-11-11.md in the lead's research notes) traces them to one cause. Since the
stage began claiming from measured CPU use, it fills the host: up to 40 workers and 19.4 of 20 cores
claimed, where the earlier gates ran 14 workers. A claim is a worker's average core use, so the sum of
claims says nothing about the seconds when many held workers want a CPU at once. Suites whose rows hold a
bound of 1 to 8 seconds lose that bound now and then. The failing rows so far: suite 63's 1.2 s runtime cap
and 4 s and 8 s stop deadlines, suite 83's reset-timer wait, 0189's 5 s readiness wait, 0039's owner stop,
0129's contained live review, 0047's one instance under the lock, and 0254's canary process.

Each of those rows fails rarely, about 2.4 percent per control run for 0189, and many such rows exist, so
each gate hits a different one. Rounds 9d, 9f and 11 widened one bound at a time and the next gate failed
on a row nobody had touched. Several of the bounds are the product contract under test and can't be
widened without weakening the row.

The same starvation can also hide a surviving mutant. A mutant whose target is a timing row counts as
killed when that row fails, whatever made it fail.

## What this supersedes in VELDO-0219

VELDO-0219's Design says: "the gate never oversubscribes CPU itself, so a case's elapsed time under the
gate's own load stays near its measurement." That claim is superseded here. It holds well enough for the
case deadline, which is three times the measurement. It doesn't hold for a bound of a few seconds inside a
row: admitting by average use up to all 20 cores, 12 of them slower efficient cores, keeps the average
honest and leaves the delay a single row can see unbounded. The same controls burned about the same CPU
before and after measured claims, and their wall time rose 35 to 140 percent.

The rest of VELDO-0219 stands: measured claims, the ledger, the deadlines and the mutation floor. The
build adds a dated note under VELDO-0219's Design that points here.

## Design

Admission gets a third rule beside the CPU and memory sum and the manager slots. A suite that measures
wall-clock time says so, and the ledger keeps CPU free while any such suite runs.

### Declaration

In scripts/suites/manifest.json a suite whose rows hold a wall-clock bound carries a field wall_clock.
Its value is a sentence naming the bound, for example "the 5 s stand-in readiness wait and setup's 30 s
answer wait". The value is for the reader; any non-empty string declares the suite.

Declared from the start, because each has failed a control this way:

- 62_veldo_0039_dispatch
- 63_veldo_0040_containment
- 66_veldo_0047_authority
- 82_veldo_0129_worker_wiring
- 83_veldo_0154_factory_loop
- 86_veldo_0189_engine_upgrade
- 129_veldo_0254_canary_launch

The build then surveys the other suites on the unconfined list (scripts/gate_unconfined.json, read only,
49 entries at 646ff7c8) for a readiness wait, deadline or window under 30 s, and declares each suite that
has one. proof/VELDO-0290/survey.json lists every suite surveyed, the bounds found with file and line, and
the decision. The manifest's resource_note gains a sentence describing the class.

### Ledger

In engine/scripts/gate_schedule.py and its copy in scripts/:

- validate_claim accepts an optional boolean wall_clock. Client.acquire and the server pass it through.
- read_graph accepts a new optional top-level key wall_clock_ceiling with the single field cpu, a number
  above 0 and at most the CPU capacity. Without the key there is no ceiling and the ledger behaves as it
  does today.
- Ledger.acquire limits the CPU total to the ceiling whenever the claim being admitted is wall_clock or a
  wall_clock claim is held. The limit applies to every claimant, the mutation stage and the other graph
  nodes alike, and it is taken together with the existing limits, whichever is lower. Memory, manager,
  ports and the host lock are unchanged.
- A wall_clock claim refused for CPU is remembered as waiting. Until it is granted, no claim that is not
  wall_clock gets CPU. This is the rule SuiteResources already applies to a waiting exclusive job. The
  waiting entry is dropped when the claim is granted, when the claimant releases or withdraws, and when
  its channel closes, so a claimant that never retries cannot stall the gate.
- A refusal caused by the ceiling or by a waiting wall_clock claim names resource wall_clock.
- A graph node may carry wall_clock: true. The node unit.unconfined is marked, because it runs the same
  suites serially beside the mutation stage.

### Mutation coordinator

In engine/scripts/check_gate_mutations.py and its copy: SuiteResources reads the wall_clock field, and
Admission.acquire passes wall_clock for every job of a declared suite. Controls and mutants are treated
alike, since a starved mutant is a false kill.

Pending jobs are ordered so that a declared suite's controls and mutants are adjacent, and the declared
suites follow one another. The ceiling then holds for one stretch of the stage instead of being switched
on and off across all of it. The existing rules still decide inside that order: slots, exclusive holds and
the waiting bar of SuiteResources apply first, and the ledger decides last.

### Measurement

mutation_ownership.WorkerMeter reads cpu.pressure from the worker cgroup and from the cgroups of the units
it accounts, at start and at the end, before cleanup. The change in the "some" total, in seconds, is
recorded as stall_seconds in the worker outcome. Disjoint roots are counted once, as for CPU. Each
admission event records whether the ceiling was in force.

This is diagnostic only. stall_seconds never excuses a red control, never causes a rerun and enters no
verdict. Its purpose is that the next red control carries its own starvation figure, where today the
cause has to be inferred from averages.

### The ceiling value

The build starts at 11 cores. That is the mutation_floor cpu already in gate_graph.json and VELDO-0219's
measured need of the stage (10.8 cores). The replay of AC4 decides whether 11 is low enough. If it is
not, the build lowers it, reruns the on arm, and records the value it lands on and the runs behind it in
this spec's History and in proof/VELDO-0290/replay.json. The value is not chosen from the analysis's
averages.

### Cost

The analysis estimates under 2,000 s added to a stage of about 7,200 s, because the declared suites take
8.3 percent of the stage's worker time (10,655 of 128,680 worker seconds). That estimate covers the
declared suites inside the mutation stage only. It doesn't count the time unit.unconfined holds its claim
(about 890 s by the graph's estimate) or suites the survey adds. The replay reports the measured cost from
its admission record, and the first gate after landing records the stage wall time beside it.

### Proof

Every summary under proof/VELDO-0290/ is veldo.proof-summary/v1 with its command, environment, host load
and discarded list. Raw replay output is discarded after its names, sizes and digests are recorded.

## Rejected alternatives

A manifest slot resource such as wall_clock: exclusive would limit how many timing suites run together.
It leaves the bulk work beside them alone, and the bulk work is what starves them.

Raising cpu.weight on the timing workers' cgroups helps their CPU share. It doesn't reach processes a
suite starts in user-manager scopes outside the worker cgroup (suites 63 and 82_0129), doesn't keep them
off the efficient cores and doesn't cover the unit stage. It could be added later.

## Related, separate

The analysis found two defects in suite 86_veldo_0189_engine_upgrade, row restart/adoption-signer-kill.
They are a second small item with its own spec and are not built here.

- without_signer doesn't check the result of its service start. The row should check it and put the tail
  of the stand-in's unit log in the check's detail, so a late start and a failed bind can be told apart.
- The service's API port is picked once by binding port 0 and closing the socket, then reused across every
  stop and start in the suite. Nothing holds it between a stop and the next start, and it lies in the
  ephemeral range, so another process can be handed it.

## Out of scope

Any change to a suite's bound or to a product constant. The case deadline formula (VELDO-0215). The
manifest's slot capacities. Pinning workers to performance cores. cpu.weight. Load from other jobs on the
host (VELDO-0220, VELDO-0223). Changes to scripts/gate_unconfined.json.

## What the reviewer judges

- The ceiling binds every claimant while a wall_clock claim is held, and nothing binds when none is held
  or waiting.
- The waiting bar cannot deadlock: a claimant that leaves frees it, and a wall_clock claim always fits
  under the ceiling or is refused as invalid.
- stall_seconds reaches no verdict, deadline or rerun decision.
- The replay's off arm reached the stage's load. If it didn't, the round says the fix is not proven.
- The survey's decisions match the bounds it lists.

## History

2026-11-10: drafted from section 3 of the landing-c flake analysis. Ceiling value: 11 to start; the
measured value is recorded here by the build.
