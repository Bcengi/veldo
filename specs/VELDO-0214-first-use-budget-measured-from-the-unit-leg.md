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
  - scripts/suites/101_veldo_0208_landing_reuse.py
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
  error_taxonomy: No measurement, a value outside a gate leg, a value bound to another leg or declaration, a malformed value and a value whose budget is not finite all fall back to 1800s by name; a budget over 6 hours is capped and says so; a run over budget is CANNOT ANSWER, as before.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: the first-use check's budget per nested run is max(1800, 2.0 x the measured seconds
      of the unit stage's same leg) under the AC5 ceiling, it is the timeout of every nested run
      main() makes, and it is printed with where the number came from. Set: an authority-recorded
      unit confined leg of 1138.4s handed through gate_legs.py's own environment, and main()
      driven over a fixture tree whose nested run reports one failure, so the mutated run and the
      lazy baseline run both happen. Completeness: the suite 111 row
      first-use-budget/measured-budget-used requires a budget of 2276.8s, that exact timeout on
      both nested runs main() makes, the timeout message naming it, and the printed line naming
      the formula, the leg and "this gate run".
    falsified_by: >
      Restore the fixed 1800 (budget = RUN_TIMEOUT_S): mutation budget214-fixed-1800-restored.
      Drop the budget at both of main()'s nested call sites, so they run on the 1800s default
      while the line still prints the measured budget: mutation budget214-main-drops-the-budget.
      Each must fail first-use-budget/measured-budget-used (and, since the capped budget is a
      nested timeout too, first-use-budget/ceiling-caps-the-budget).
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
  - id: AC5
    text: >
      Claim: the budget has a ceiling: min(max(1800, 2.0 x s), 21600), so no stored value removes
      the bound on a nested run; the cap is printed when it applies; a value whose budget is not a
      finite number of seconds is ignored by name and the check answers without a traceback.
      Set: bound values of 20000s, 10799s, 1e9s and 1e308s. Completeness: the rows
      first-use-budget/ceiling-caps-the-budget (21600s and "CAPPED" for 20000s, 21598s uncapped
      for 10799s, every nested timeout of main() 21600s for 1e9s) and
      first-use-budget/non-finite-budget-refused (1800s, "not a finite number of seconds", every
      nested timeout 1800s, no traceback for 1e308s).
    falsified_by: >
      Remove the ceiling (budget = max(RUN_TIMEOUT_S, derived)), or skip the finiteness check;
      the matching row must fail (checked by hand in round 2, proof/VELDO-0214/hand_falsifiers.json).
  - id: AC6
    text: >
      Claim: the leg-time store stays bounded and holds only gate measurements. After each
      recording, files whose recorded authority checkout no longer exists or that are older than
      30 days are removed, never the file named as the one just written or a file that is not the
      store's own. The owner's store records only the authority's own list; a fixture list is said
      and not recorded. Where the authority checkout lives is no test: an authority under the
      system temporary directory over its own list, as the lander's installation
      (tempfile.mkdtemp(prefix="veldo-observation-") / "installed") is, records its unit legs and
      hands them to its own integration stage. A suite that drives a temporary authority copy over
      its own list keeps out of the owner's store from the suite side, with a scratch HOME in that
      driver's environment (suite 101). There is no environment override for the store's path. Set:
      a scratch store with a file of a deleted checkout, a 31-day-old file, a live file, an
      abandoned pending file and a foreign file; a scratch store whose only file, 31 days old and of
      a deleted checkout, is the one named to keep; a unit stage over a fixture list with the
      module's owner store pointed at a scratch directory; a unit and an integration stage of a
      copy of gate_legs.py and its own list laid down under the system temporary directory, with
      that copy's owner store pointed at a scratch directory. Completeness: the rows
      first-use-budget/leg-time-store-pruned, first-use-budget/suites-stay-out-of-the-owner-store,
      first-use-budget/installed-authority-under-temp-is-measured and suite 101's
      unconfined-leg/authority-copy-records-under-its-scratch-home.
    falsified_by: >
      Refuse an authority under the system temporary directory again: mutation
      budget214-temporary-authority-refused must fail
      first-use-budget/installed-authority-under-temp-is-measured. Stop sparing the file named to
      keep: mutation budget214-keep-not-spared must fail first-use-budget/leg-time-store-pruned.
      Remove the prune call, or the gone-checkout test, or the owner-store guard, or its own-list
      test; the matching row must fail (checked by hand, proof/VELDO-0214/hand_falsifiers.json).
      Drop home=authority_home from suite 101's through_stage: suite 101 must fail
      unconfined-leg/authority-copy-records-under-its-scratch-home (checked by hand on the host,
      proof/VELDO-0214/host-runs.json; suite 101 cannot run in the mutation worker).
required_evidence: [unit, integration]
rollback: Revert the five protected files, the suite, its manifest entry, suite 101's scratch HOME for its authority copy and the seven mutation cases; the check returns to a fixed 1800s.
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
  nothing and the last passing measurement stands. After each recording the store drops the
  files of checkouts that no longer exist and every file older than 30 days. The owner's store
  takes only the authority's own list, so a suite that drives the runner over a fixture list
  leaves it alone, and says so on the leg line. Where the authority lives is no test: the lander
  runs the gate from an installation it lays down under the system temporary directory, and that
  gate must hand its unit leg to its own integration stage like any other. Its per-land file goes
  with the gone-checkout prune once the observation directory is deleted, or at 30 days. Suite
  101, which drives a temporary authority copy over that copy's own list, gives those drivers a
  scratch HOME, so its measurements land in its own scratch store, not the owner's.
- Each integration leg receives VELDO_GATE_UNIT_SECONDS beside VELDO_GATE_LEG and
  VELDO_GATE_DECLARATION: the matching unit leg's last fresh measurement, bound to the leg and the
  digest, marked "this gate run" when the record of this verify.sh run (its mktemp file) produced
  it and "an earlier gate run" otherwise. A future reused unit stage (VELDO-0206) records nothing,
  so it is handed the last fresh measurement by construction. With nothing recorded, nothing is
  handed.
- The variable is protected as the declaration digest is: gate_legs.py drops a caller's value
  always and sets it only for an integration leg; verify.sh's veldo_candidate, in both copies,
  unsets it with the leg variables.
- scripts/check_first_use.py computes min(max(1800, 2.0 x seconds), 21600) when the value is
  bound to the leg and declaration it runs under, uses it as every nested run's timeout, and
  prints the budget and its source before any run, with the cap named when it applies. A value
  whose budget is not finite, and anything else, is the 1800s floor, stated with the reason.

## Limits

- The candidate cannot set the variable, and the confined leg cannot reach the store. The
  unconfined leg runs with the owner's own authority (VELDO-0208), so its code can rewrite the
  store like anything else the owner can write, including the confined entry between the unit
  and the integration stage. This adds no reach it lacked, and the budget it can choose is held
  between the 1800s floor and the 6-hour ceiling; a run over it is red.
- Candidate code can make its own unit leg slower and so raise its own budget; the budget only
  bounds how long the gate waits, and a slow unit leg is visible on the leg line.
- The store holds the last passing measurement only; there is no history or percentile.

## Protected paths and approval

Every implementation file except the suite, the manifest and the mutation registry is a protected
path: scripts/check_first_use.py, scripts/gate_legs.py, engine/scripts/gate_legs.py,
scripts/verify.sh, engine/scripts/verify.sh. Landing needs the owner's commit-bound approval; no
approval is authored by the implementing agent. scripts/gate_unconfined.json is unchanged.
