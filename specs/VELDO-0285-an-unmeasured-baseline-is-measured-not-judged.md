---
schema: veldo.spec/v1
id: VELDO-0285
title: An unmeasured case's baseline is a measurement bounded only against a hang, and its noop and mutant are held to a multiple of it
status: ready
risk: high
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: [VELDO-0215]
placement: [enforcement]
protected_paths: ["scripts/check_gate_mutations.py", "engine/scripts/check_gate_mutations.py"]
footprint:
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - scripts/suites/112_veldo_0215_case_deadlines.py
  - scripts/check_teeth_mutations.py
  - specs/VELDO-0285-an-unmeasured-baseline-is-measured-not-judged.md
  - specs/index.md
  - proof/VELDO-0285/**
behavior_bearing: true
observability:
  logs: The receipt's case_deadlines names each case's enforced mutant deadline; for an unmeasured case it is the one derived in this stage. unmeasured_cases lists the cases that had no live sample.
  metrics: Each worker outcome keeps its budget_seconds, so an unmeasured baseline shows the ceiling and its noop and mutant show the derived deadline.
  traces: The sample recorded after a passing fresh stage is unchanged (the largest of baseline, noop and mutant), so the next stage measures the case from its store.
  error_taxonomy: Unchanged. A worker past its deadline, including a noop that finished before its baseline and is judged afterwards, is mutation_budget_exceeded and the stage is red.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: a case with no live sample under this checkout's key runs its baseline under
      WORKER_CEILING (1800 s), not the 120-second floor, because that baseline is this stage's
      measurement, not a judged run. A 150-second baseline completes and the stage passes.
      Set: the suite 112 in-process stage with a simulated clock and no sample in the store.
      Completeness: case-deadlines/unmeasured-slow-baseline requires the baseline's budget to be
      the ceiling and its elapsed over the floor, the stage to pass and record 150 seconds, and the
      combined budget planned at the ceiling to bound the stage.
    falsified_by: >
      Restore the floor for an unmeasured case. Registered mutant deadline285-unmeasured-floor
      must turn case-deadlines/unmeasured-slow-baseline red.
  - id: AC2
    text: >
      Claim: the same case's noop and mutant take their deadline from that baseline as measured
      in this stage, WORKER_MULTIPLIER times it within floor and ceiling: a pending worker launches
      under it, a running one is held to it, and one that already finished is judged by it. A
      noop shared with measured cases serves the larger of their recorded deadlines and the
      derived one. Once derived, the rest of the stage's combined budget is bounded by the derived
      mutant deadlines, never above the plan. Completeness: case-deadlines/unmeasured-mutant-deadline
      requires a hung mutant (one worker) and a hung running noop (two workers) to end at 450
      seconds after a 150-second baseline, and a finished 500-second noop to be judged red by a
      450-second derivation.
    falsified_by: >
      Drop the same-stage derivation. Registered mutant deadline285-no-same-stage-derivation must
      turn case-deadlines/unmeasured-mutant-deadline red.
  - id: AC3
    text: >
      Claim: nothing else is loosened. A hung unmeasured baseline still ends at the ceiling with
      the stage red and no sample recorded; a measured case keeps the VELDO-0215 rule from its
      recorded samples (3 x the rolling peak within floor and ceiling, 30-day window) and its
      combined budget is computed as before; the floor still bounds setup commands.
      Completeness: case-deadlines/unmeasured-hang, and the unchanged VELDO-0215 rows
      measured-worker, slow-pass, hang-timeout, bounds, combined-budget and setup-timeout.
    falsified_by: >
      The VELDO-0215 registered mutants deadline215-no-expiry, deadline215-fixed-worker,
      deadline215-no-ceiling and deadline215-setup-timeout-is-driver-error keep guarding these rows.
required_evidence: [unit]
rollback: Revert both coordinator copies, the suite rows and the two registered mutants; an unmeasured case's baseline returns to the 120-second floor.
---

## Intent

Status ready by the lead: test machinery is the lead's call under owner decision 39708.

Two canonical gates of a fresh worktree (landing-b, at 30befb53 and e1c60829) stopped the mutation
stage with mutation_budget_exceeded, 0 of 2851 executed, because one confined baseline ran past
the 120-second floor its case gets when this checkout has no sample. Several cases legitimately
take 115 to 150 seconds. The first gate after any rekey (a fresh checkout, or any change to the
driver, which rekeys every case) is therefore a draw against host load: a flaky gate, not a defect
in the code under test. Owner rule: fix flaky tests, never loosen a check.

## Findings this spec rests on

- The record key, case_time_key, digests the authority checkout's path and the case inputs,
  including the execution machinery (check_gate_mutations.py itself). Two checkouts never share a
  key, and any change to the coordinator rekeys every case, so no store read can cover the first
  stage after a rekey. Round 1 of this spec built a cross-checkout read and found exactly that; it
  is removed.
- A baseline is not judged by the deadline: its purpose is to observe the unmutated rows. Bounding
  it at the floor judges a measurement against a guess. The hang it must still be bounded against
  is bounded by the ceiling.
- The judged runs are the noop and the mutant. They keep a measured deadline: the baseline just
  measured in the same stage, under the same load, is a better measurement than a recorded one.

## Design

case_deadlines(keys, times) returns each case's recorded deadline, or None when the case has no
live sample. The stage plans an unmeasured case at WORKER_CEILING for its baseline, noop and
mutant, so the combined budget planned before any worker runs bounds the whole stage. When a
control group's baseline completes, measured_baseline sets each unmeasured member's deadline to
scaled_deadline(elapsed), updates its mutant job, and retargets the group's noop to the largest
member deadline (Workers.retarget: pending, running or finished). After the controls, if any
unmeasured case ran fresh, the combined budget is reduced to the elapsed time plus budget_for of
the mutant phase at the derived deadlines, never above the plan. A measured case's path is
unchanged, and WORKER_BUDGET still bounds setup commands (inventory and Git).

## History

2026-11-07: drafted and built as a cross-checkout read of case measurements (round 1, commits
cb5b3439 to b02bfb2a). Round 1 found the read cannot cover the case it was for: the key binds the
checkout's path and the coordinator's bytes, so a fresh checkout or any coordinator change has no
peer sample at its key.

2026-11-07: amended under owner decision Telegram 39708 (test machinery is the lead's call) to the
lead's design: an unmeasured baseline is bounded by the ceiling, its noop and mutant by 3 x that
baseline as measured in the same stage. The peer read, its rows and its three mutants are removed;
the spec file is renamed to match.
