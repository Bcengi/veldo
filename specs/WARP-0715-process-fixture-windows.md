---
schema: veldo.spec/v1
id: WARP-0715
title: The process runner waits out real kernel windows because that is what it exists to test - shorten only
  the FIXTURE parameters, and only behind a 50-run proof that the shorter windows are not flaky
status: ready
risk: high - this item trades wall clock for FLAKINESS RISK, which is the one trade that can make a gate worse
  while every measurement says it got better. An intermittently red gate is worse than a slow one: it teaches
  people to re-run instead of to read, and it destroys the only signal the method has. So the reliability proof
  is not a nicety here, it IS the item, and the acceptance criteria are written so that failing the proof moves
  the TARGET rather than moving the bar. No shipped constant changes, no protected path is touched, and no
  assertion is removed
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: [WARP-0713]
placement: [engine]
footprint:
  - engine/scripts/runners/process/fixtures/pass.lifecycle.json
  - engine/scripts/runners/process/fixtures/fail.lifecycle.json
  - packs/*/scripts/runners/process/fixtures/pass.lifecycle.json
  - packs/*/scripts/runners/process/fixtures/fail.lifecycle.json
  - scripts/selftest.py
  - proof/WARP-0715/flake-proof.md
  - specs/WARP-0715-process-fixture-windows.md
  - specs/index.md
protected_paths: []
behavior_bearing: true
observability:
  logs: The flake proof records, per candidate value, the number of consecutive runs, the observed failures and
    the slowest observed margin between the window and the event it waits for, so a later reader can judge
    whether the chosen value has headroom rather than only whether it passed once.
  error_taxonomy: No new failure names and none renamed. The seven process-runner assertions keep their exact
    labels and messages, because this item changes only how long their fixtures wait.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Replace the spawned child with a subprocess double in the process-runner block, and the assertion that
      all seven of those assertions drive a REAL subprocess must go red; that is the load-bearing leg, since a
      double is the tempting speedup that deletes the operating-system coverage entirely, while the lesser leg
      falsifies by moving the shipped POLL constant off 0.05 and reddening its numeric pin.
    text: >
      ONLY FIXTURE PARAMETERS MOVE, AND NO SHIPPED CONSTANT DOES. The values under consideration are test inputs
      in the two lifecycle fixtures: grace_seconds 3.0, kill_tree_window_seconds 4.0 and spawn_settle_seconds
      0.3. POLL (0.05 in the process runner module) is the only SHIPPED constant in that module and it does NOT
      change, asserted numerically. Faking or stubbing the subprocess is EXPLICITLY REFUSED: those seven
      assertions exist to prove real signal delivery, real force-kill after a grace window and real orphan
      reaping, which are operating-system properties, and replacing the process with a double would delete the
      only coverage they provide. A selftest asserts all seven assertions still drive a REAL subprocess.
  - id: AC2
    falsified_by: >
      Lower the consecutive-run count the flake harness drives from 50 to 5 while keeping the recorded
      verdict, and the assertion requiring at least 50 consecutive runs with ZERO flaky results per candidate
      value, with the slowest observed margin recorded in proof/WARP-0715/flake-proof.md, must go red;
      dropping the run under concurrent load falsifies the same criterion from the other side.
    text: >
      THE RELIABILITY PROOF IS THE ITEM, AND FAILING IT MOVES THE TARGET RATHER THAN THE BAR. For each proposed
      value, the process-runner block is run AT LEAST 50 CONSECUTIVE TIMES and asserted to produce ZERO flaky
      results, and proof/WARP-0715/flake-proof.md records the run count, the failures observed and the SLOWEST
      OBSERVED MARGIN between each window and the event it waits for, so the headroom is visible rather than
      implied. If 50 runs are not clean at a candidate value, THE VALUE GOES BACK UP and the wall-clock target
      moves - that direction is stated here so that a later pass cannot quietly choose the other one. The runs
      must include at least one under concurrent load, because a window that is reliable on an idle machine and
      marginal on a busy one is exactly the flake this criterion exists to prevent.
  - id: AC3
    falsified_by: >
      Change one of the two lifecycle fixtures in a single pack copy so it diverges from the engine copy, and
      scripts/check_pack_drift.py must go red naming that path: canon is the leg with a mechanical check here,
      while the honest-figure leg reddens by shortening a window past its proof, which breaks the seven
      process-runner assertions under their original labels.
    text: >
      THE SAVING IS REPORTED HONESTLY AGAINST THE COMMITTED BAR. The suite's elapsed time is measured by the
      baseline method and recorded; the committed bar for the whole gate is UNDER 20 SECONDS from 117.1, and the
      UNDER-12 STRETCH DEPENDS ENTIRELY ON THIS ITEM'S PROOF HOLDING. If the proof supports only a modest
      reduction, the manifest states the real figure and names the shortfall rather than rounding toward the
      stretch. Engine canon holds: both fixtures re-synced byte-identical across engine and all six
      packs. No protected path is touched, scripts/verify.sh and the stage list are byte-UNCHANGED, the frozen
      safety core is byte-UNCHANGED, all seven process-runner assertions still pass with their original labels,
      the full gate is GREEN, and RULE #1 is clean.
required_evidence: [unit]
rollback: >
  Revert the commit. The change lowers three fixture window values and adds a flake-proof artifact and its
  selftest, re-synced byte-identical across engine and the packs. Reverting restores the longer
  windows, which is a pure cost regression with no behavioural difference to any adopter, since these are test
  inputs and no shipped constant changed. Reverting is also the CORRECT response to any observed flake in these
  seven assertions, and this item is deliberately written so that reverting is cheap and obvious.
---

## Intent

Of the gate's 117.1 seconds, 84.2 is the process BLOCKING rather than computing. WARP-0713 takes the mobile
half, about 46 seconds, for free: those runners drive fake drivers, so an injected clock costs nothing.

This item takes what is left, and it is the hard part. A prototype with a GLOBAL virtual clock broke EXACTLY
SEVEN assertions, and all seven are the process runner: the well-behaved target, the SIGTERM-ignoring target,
kill_tree reaping the child, naming an escaped orphan, and the three lifecycle fixture cases. The reason is
structural rather than a bug. That runner spawns REAL subprocesses and asserts that a real kernel delivered a
signal, that a process ignoring SIGTERM was force-killed after its grace window, and that no orphan escaped.
Jump the clock and the runner concludes a deadline passed while the process is still alive.

So those seven are not slow by accident. They are slow because they are waiting for a real operating system to
do a real thing, and that waiting is the coverage. Faking the subprocess would make them instant and worthless,
which is why this spec refuses it in writing rather than leaving it to judgement.

What CAN move is the fixture parameters: `grace_seconds` 3.0, `kill_tree_window_seconds` 4.0,
`spawn_settle_seconds` 0.3. Those are test inputs, not shipped values, and a real kernel delivers a signal in
milliseconds, not three seconds. The 3.0 is a generous safety margin for a loaded machine.

And that is precisely the risk. Shortening a margin trades wall clock for flakiness, and an intermittently red
gate is worse than a slow one, because it teaches everyone to re-run rather than to read, and the method's only
signal is a green gate that means something. So the proof is the deliverable and the speed is the side effect.

## Context

- Why 50 runs and a load condition rather than a single clean pass: a marginal window fails on a busy machine
  and passes on an idle one, so a single pass proves nothing about the case that will actually bite.
- Why the slowest observed MARGIN is recorded and not just pass or fail: the next person needs to know whether
  the chosen value has ten times headroom or one point one times headroom, and pass or fail does not say.
- Why the direction of failure is written into the criterion: an item with a speed target, when its proof does
  not hold, has two options and only one of them is honest. Naming the honest one in advance removes the
  judgement call from the moment of temptation.
- Why this depends on WARP-0713: that item establishes the injected-waiter pattern in the sibling runners and
  proves the mobile half is free. Doing this one first would invite generalizing the clock into the process
  runner, which is the thing that breaks the seven.

## Out of scope

- Any change to POLL or to any other shipped constant in the process runner module.
- Faking, stubbing, mocking or otherwise replacing the real subprocess. Refused, with the reason.
- Any change to the seven assertions themselves, their labels or their messages.
- The mobile runners (WARP-0713), the lint stage (WARP-0711) and the repeated derivations (WARP-0714).
- No protected path, no change to verify.sh or the stage list.

## Notes

- Run the proof BEFORE choosing the value, not to justify a value already chosen. That ordering is the whole
  difference between a measurement and a rationalization, and this project has paid for the wrong one today.
- If the numbers say the windows must stay long, say so and let the gate stay slower. That is a successful
  outcome for this item, not a failure of it.
- Include a loaded-machine run. The idle-machine result is the optimistic one and it is not the one that will
  page someone.
- NO UNBACKED UNIVERSAL: "zero flaky results", "no shipped constant changes" and "all seven still drive a real
  subprocess" each need the assertion that enumerates them.
- RULE #1 clean (ASCII hyphen only, no em dash, no en dash, no prose double-hyphen).
