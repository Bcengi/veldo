---
schema: veldo.spec/v1
id: VELDO-0293
title: An unmeasured mutant and its noop get a 360 s floor, so a mutant that drives its suite into bounded product waits is judged instead of cut off at the 120 s hang floor
status: ready
risk: standard
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: [VELDO-0285, VELDO-0290]
placement: [enforcement]
protected_paths: []
footprint:
  - engine/scripts/check_gate_mutations.py
  - scripts/check_gate_mutations.py
  - scripts/suites/112_veldo_0215_case_deadlines.py
  - scripts/check_teeth_mutations.py
  - specs/VELDO-0293-an-unmeasured-mutant-gets-a-floor-above-the-hang-floor.md
  - specs/index.md
  - proof/VELDO-0293/**
behavior_bearing: true
observability:
  logs: >
    No new log line. The receipt's case_deadlines already shows each case's budget, so an unmeasured
    mutant shows 360 where it showed 120.
  metrics: >
    None new. unmeasured_cases and case_deadlines in the stage receipt carry the effect.
  traces: >
    None.
  error_taxonomy: >
    No new refusal. mutation_budget_exceeded keeps its meaning; it now fires for an unmeasured mutant
    at 360 s instead of 120 s.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: when a case has no recorded time, its mutant and its group's noop get a deadline of the
      larger of 360 s and the VELDO-0285 scaled deadline of the group's baseline measured in this stage.
      A measured case keeps its recorded deadline, the baseline keeps the 120 s floor, and nothing
      changes in how samples are recorded. Both copies, engine/scripts/check_gate_mutations.py and
      scripts/check_gate_mutations.py, carry the same change and stay byte-identical. Proven in suite 112
      by a new row, printed with the prefix VELDO-0293: an unmeasured case whose baseline takes under
      120 s and whose mutant takes about 150 s is judged (killed or survived by its rows) with
      budget_seconds 360, and its noop is retargeted to at least 360. The existing rows
      unmeasured-slow-baseline and unmeasured-mutant-deadline (150 s baseline, 450 s deadline) stay
      green unchanged, and every measured-case row stays green. Red at 6ee5bb5f, where the new row's
      mutant is cut off at 120 s with mutation_budget_exceeded.
    falsified_by: >
      Remove the max with the 360 s floor so the unmeasured deadline is the scaled baseline alone.
      Registered mutant floor293-removed in scripts/check_teeth_mutations.py must turn the new suite 112
      row red, because its mutant is cut off at 120 s.
  - id: AC2
    text: >
      Claim: the two suite 62 mutants that stopped landing-c gates 13 and 14,
      dispatch-receiver-store-only-gate and dispatch-spawn-before-contract, are both judged killed with
      no case measured. Proven once, as a measurement and not a gate, by running those two cases through
      scripts/check_teeth_mutations.py with the case-time store empty for them, recording each case's
      elapsed seconds and verdict in a small summary under proof/VELDO-0293/. Both are killed and each
      elapsed is under 360 s. The run is made once; a red stands and goes to the lead.
    falsified_by: >
      Run the same two cases at 6ee5bb5f: dispatch-receiver-store-only-gate ends in
      mutation_budget_exceeded at 120 s, as in gate 14's receipt.
required_evidence: [unit, integration]
rollback: >
  Revert the commit. The 120 s floor returns for unmeasured mutants, and a stage whose cases are all
  unmeasured can again stop on a mutant that waits past 120 s.
---

## Intent

Landing-c gate 14 (6ee5bb5f) went red in the mutation stage only. No mutant survived: the stage judged
843 cases, killed all 829 valid ones, and stopped at its first invalid result, the suite 62 mutant
dispatch-receiver-store-only-gate, killed by its 120 s worker deadline after a 120.04 s run with 8.6 CPU
seconds and 0.04 s of stall. The diagnosis is in the lead's research notes
(landing-c-gate14-check-2026-11-11.md).

Two things lined up. VELDO-0290 changed scripts/check_gate_mutations.py, and a case's time key includes
that file's digest, so every case became unmeasured (unmeasured_cases 2962). Samples are written only
after a passing fresh stage, so none have been written since. An unmeasured mutant gets the VELDO-0285
deadline: three times its group's baseline from this stage, floored at WORKER_BUDGET, 120 s. Suite 62's
baseline is about 18.5 s, so its mutants got 120 s. VELDO-0288 then added rows to suite 62 that each
bound a wait at 30 s. Two dispatch mutants, which drive the suite into those product waits, grew from
99.5 and 104.1 s to past 120 s. When samples existed they had measured deadlines of 293 and 305 s.

The 0285 rule assumes a mutant runs about as long as its baseline. A mutant that breaks acceptance can
run five to seven times longer, because it walks the suite into every bounded wait the baseline never
reaches. 120 s is a hang floor for a baseline, not a fair budget for such a mutant. 360 s is three times
the hang floor, above the 293 to 305 s these cases got when measured, and about 2.5 times the longest
recent run.

## What this spec leaves alone

The measured rule, the baseline's 120 s floor, sample recording, and suite 62's rows from VELDO-0288. A
test-only change shortening those rows would weaken a reviewed spec and fix only the two cases seen
today. Dropping or narrowing the two mutants would remove teeth.

The cost is stated: a mutant that truly hangs while unmeasured now takes up to 360 s instead of 120 s,
and only until the next passing stage records samples.

## History

2026-11-11: written by the lead from the gate 14 check (Telegram approval not required: gate machinery
left protected_paths under VELDO-0272).
