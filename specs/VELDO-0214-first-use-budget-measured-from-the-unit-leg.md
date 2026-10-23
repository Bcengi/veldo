---
schema: veldo.spec/v1
id: VELDO-0214
title: The first-use check's budget is measured from the unit leg
status: ready
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0208]
placement: [enforcement]
protected_paths: ["scripts/check_first_use.py", "scripts/gate_legs.py", "engine/scripts/gate_legs.py", "scripts/verify.sh", "engine/scripts/verify.sh"]
footprint:
  - scripts/check_first_use.py
  - scripts/gate_legs.py
  - engine/scripts/gate_legs.py
  - scripts/verify.sh
  - engine/scripts/verify.sh
  - scripts/check_teeth_mutations.py
  - scripts/suites/111_veldo_0214_first_use_budget.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - specs/VELDO-0214-first-use-budget-measured-from-the-unit-leg.md
  - specs/index.md
  - proof/VELDO-0214/*
behavior_bearing: true
observability:
  logs: Each leg line carries its wall time; each integration leg prints its budget input; the check prints its budget and source.
  metrics: Seconds per unit leg in the authority's leg-time store.
  traces: The handed value names its leg, declaration digest, time of measurement and whether it is this gate run's.
  error_taxonomy: No measurement, a value outside a gate leg, a value bound to another leg or declaration, and a malformed value all fall back to 1800s by name; a run over budget is CANNOT ANSWER, as before.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: the first-use check's budget per nested run is max(1800, 2.0 x the measured seconds
      of the unit stage's same leg), it is the timeout of every nested run, and it is printed with
      where the number came from. Set: an authority-recorded unit confined leg of 1138.4s handed
      through gate_legs.py's own environment. Completeness: the suite 111 row
      first-use-budget/measured-budget-used requires a budget of 2276.8s, that exact timeout on
      the nested run, the timeout message naming it, and the printed line naming the formula,
      the leg and "this gate run".
    falsified_by: >
      Restore the fixed 1800 (budget = RUN_TIMEOUT_S). Mutation budget214-fixed-1800-restored
      must fail first-use-budget/measured-budget-used.
  - id: AC2
    text: >
      Claim: only the authority's leg runner sets VELDO_GATE_UNIT_SECONDS; a caller's or
      candidate's value is ignored. Set: a forged value in the leg runner's environment with and
      without a recorded measurement; a value outside a gate leg; a value bound to another leg or
      declaration; verify.sh's fallback path in both copies. Completeness: the row
      first-use-budget/candidate-set-value-ignored requires the forged value to reach no
      integration leg, the check to fall back to 1800 and say "ignored" for each mis-bound value,
      and both veldo_candidate functions to unset the variable with the leg variables.
    falsified_by: >
      Keep the caller's value in gate_legs._env. Mutation budget214-caller-value-kept must fail
      first-use-budget/candidate-set-value-ignored.
  - id: AC3
    text: >
      Claim: the leg runner times every leg, records a passing unit leg's time in the authority's
      leg-time store and hands each integration leg its matching unit leg's last fresh
      measurement; when the unit leg did not run fresh in this gate run (reused, skipped or
      failed) that is the last fresh measurement recorded, said to be from an earlier gate run,
      and a failing unit leg records nothing. Set: a passing unit stage followed by integration in
      the same run, then a later run whose unit legs fail. Completeness: the rows
      first-use-budget/stage-runner-hands-the-matching-leg and
      first-use-budget/reused-stage-uses-last-fresh.
    falsified_by: >
      Record failing unit legs too. Mutation budget214-failed-leg-recorded must fail
      first-use-budget/reused-stage-uses-last-fresh.
  - id: AC4
    text: >
      Claim: with no measurement at all (the check run by hand) the budget is 1800s and the check
      says so, and the docstring no longer claims a nested run takes about 90 seconds. Set: an
      empty environment. Completeness: the row first-use-budget/by-hand-uses-1800-and-says-so.
    falsified_by: >
      Put "measured at about 90 seconds" back in the docstring; the row must fail.
required_evidence: [unit, integration]
rollback: Revert the five protected files, the suite, its manifest entry and the three mutation cases; the check returns to a fixed 1800s.
---

## Intent

Measured on 2026-10-23 at base b44736c0: the confined leg's nested selftest, run exactly as
scripts/check_first_use.py runs it inside the gate's confinement, took 2276.8s for 7849 rows. The
machine was under load (1-minute load average 14.2 mean, 25.5 peak on 20 cores; the first six
minutes were quiet). The unconfined leg's 873 rows take 870 to 885s. RUN_TIMEOUT_S = 1800 is the
budget per nested run, and the confined leg ended "FIRST USE: CANNOT ANSWER: the
mutated(spend_recorded) run did not finish inside 1800s" on two gate runs (22e330b7 and 928918a5)
while the suite was healthy. The docstring still said one nested run takes about 90 seconds.

A fixed budget is a guess about a suite that grows. The integration stage's nested run is the unit
stage's same leg over again, run just before it under the identical confinement, so the gate
already measures what the budget should be. Build that measured budget the way a mature gate
would: measured by the authority, out of the candidate's reach, with a stated floor and a stated
source.

## Design

- scripts/gate_legs.py (and its engine copy) times each leg it runs and prints the time on the
  leg line. A unit leg that passed is recorded in the authority's leg-time store,
  ~/.cache/veldo/gate-leg-seconds/, one file per authority checkout and declaration digest; the
  confined leg cannot write there. A failing unit leg may have stopped early, so it records
  nothing and the last passing measurement stands.
- Each integration leg receives VELDO_GATE_UNIT_SECONDS beside VELDO_GATE_LEG and
  VELDO_GATE_DECLARATION: the matching unit leg's last fresh measurement, bound to the leg and the
  digest, marked "this gate run" when the record of this verify.sh run (its mktemp file) produced
  it and "an earlier gate run" otherwise. A future reused unit stage (VELDO-0206) records nothing,
  so it is handed the last fresh measurement by construction. With nothing recorded, nothing is
  handed.
- The variable is protected as the declaration digest is: gate_legs.py drops a caller's value
  always and sets it only for an integration leg; verify.sh's veldo_candidate, in both copies,
  unsets it with the leg variables.
- scripts/check_first_use.py computes max(1800, 2.0 x seconds) when the value is bound to the leg
  and declaration it runs under, uses it as every nested run's timeout, and prints the budget and
  its source before any run. Anything else is the 1800s floor, stated with the reason.

## Limits

- The unconfined leg runs with the owner's own authority (VELDO-0208), so its code can write the
  owner's ~/.cache like anything else the owner can write. This adds no reach it lacked.
- Candidate code can make its own unit leg slower and so raise its own budget; the budget only
  bounds how long the gate waits, and a slow unit leg is visible on the leg line.
- The store holds the last passing measurement only; there is no history or percentile.

## Protected paths and approval

Every implementation file except the suite, the manifest and the mutation registry is a protected
path: scripts/check_first_use.py, scripts/gate_legs.py, engine/scripts/gate_legs.py,
scripts/verify.sh, engine/scripts/verify.sh. Landing needs the owner's commit-bound approval; no
approval is authored by the implementing agent. scripts/gate_unconfined.json is unchanged.
