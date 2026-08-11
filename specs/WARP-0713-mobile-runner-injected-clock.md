---
schema: veldo.spec/v1
id: WARP-0713
title: The gate sleeps 46 real seconds waiting for a user interface that does not exist to settle - give the
  mobile runners the injected waiter this repository already uses in two other modules, and turn those waits
  from unobservable delay into asserted behaviour
status: shipped
risk: high - the footprint crosses the engine area in fourteen files (two runner modules across seven copies
  each), and it changes modules that SHIP to adopters, so the first duty is that an adopter's WALL-CLOCK
  WAITING is unchanged: the seam defaults to the real time.sleep and time.monotonic, and every settle constant
  keeps its numeric value. ONE ADOPTER-VISIBLE BEHAVIOUR DOES CHANGE, and it is named here rather than left
  inside a claim of byte-identity, because that claim was measured FALSE for it: the runners used to reach
  `time.sleep` through the module ATTRIBUTE at each call, so a harness that patched `time.sleep` AFTER import
  intercepted every wait. The seam binds the default at def time to the function OBJECT, so it no longer does.
  MEASURED on the shipped copy: construct `SettleWaiter()` with a post-import patch installed and
  `_sleep is the real time.sleep` is True while `_sleep is the patched attribute` is False. Wall-clock waiting
  is identical; INTERCEPTION is not, and an adopter relying on monkeypatching to speed or observe these waits
  must pass a waiter instead. The way this could go wrong is subtle rather than loud - shortening a constant, or
  defaulting to a fake clock in production, would make the gate faster and the shipped runner wrong. Both are
  closed by assertion rather than by care. It is high and not critical because no protected path is touched, no
  process-runner assertion is affected (proven: a global virtual clock breaks exactly seven, and they are all in
  the OTHER runner), and the change is prototype-measured at zero assertion impact
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: []
placement: [engine]
footprint:
  - engine/scripts/runners/mobile/veldo_android_runner.py
  - engine/scripts/runners/mobile/veldo_ios_runner.py
  - packs/*/scripts/runners/mobile/veldo_android_runner.py
  - packs/*/scripts/runners/mobile/veldo_ios_runner.py
  - scripts/selftest.py
  - specs/WARP-0713-mobile-runner-injected-clock.md
  - specs/index.md
protected_paths: []
behavior_bearing: true
observability:
  logs: The recording clock used inside the gate reports the total simulated time it absorbed and the ordered
    list of durations requested, so a reader can tell a fast gate from a gate that stopped waiting for something
    it should wait for. In production the seam is the real clock and there is no new output.
  error_taxonomy: No new failure names and none renamed. A runner step that fails today fails identically, with
    the same message, because only the waiting mechanism changes and never the decision to wait.
acceptance_criteria:
  - id: AC1
    text: >
      THE SEAM DEFAULTS TO THE REAL CLOCK, SO SHIPPED BEHAVIOUR IS BYTE-IDENTICAL, and that is asserted rather
      than reasoned. Both mobile runners take a clock and a sleep as parameters DEFAULTING to time.monotonic and
      time.sleep, which is exactly the shape this repository already uses at .veldo/fleet.py:377
      (clock=time.time, sleep=time.sleep) and at the OAuth token manager .veldo/tracker_mirror_runner.py:172, so
      this is an existing house pattern applied to two modules written without it. AMENDED BY ROUND 2, ON THE
      RECORD, BECAUSE THE ORIGINAL WORDING NAMED THE WRONG OBJECT AND ROUND 1 SATISFIED IT WITHOUT CLOSING THE
      RISK: this criterion asked for a selftest that "constructs each runner with NO arguments" and asserts the
      resolved sleep IS time.sleep. Round 1 met that by constructing a SettleWaiter, which establishes the CLASS
      DEFAULT and says nothing about what the RUNNER resolves. Measured: a fake waiter installed at the runner's
      own resolution sites in all seven shipped android copies left the suite at 3261 passed / 0 failed, so
      adopter waiting was gone and nothing reddened, which is exactly the "default to a fake clock in
      production" outcome this item's risk note forbids, shipping green. THE CRITERION IS THEREFORE THAT THE
      ASSERTION BINDS THE RUNNER'S OWN RESOLUTION: the selftest DRIVES each runner with the waiter argument
      OMITTED, at every resolution site the module's own AST declares, in EVERY tracked copy of both runners,
      and asserts BY IDENTITY that the waiter THE RUNNER CONSTRUCTED has sleep IS time.sleep, clock IS
      time.monotonic and no recording hook. Identity is required because a lookalike cannot satisfy `is`, and a
      construction this suite makes for itself no longer counts as evidence about the runner. Proven able to
      fire one site at a time, at every site of every tracked copy.
  - id: AC2
    text: >
      EVERY SETTLE CONSTANT KEEPS ITS NUMERIC VALUE, asserted numerically, because the seam is what changes and
      the values are part of what ships. AMENDED BY THE BUILD, ON THE RECORD, BECAUSE THE ORIGINAL COUNT WAS
      MEASURED TO BE FALSE: this criterion said "21 literal sleep sites (12 android, 9 iOS)", and those are LINE
      counts, not call counts (`grep -c "time\.sleep" <file>` counts LINES; `grep -o "time\.sleep" | wc -l`
      counts CALLS). Three android lines and one iOS line each carried two calls, so the call count is 25. THE
      CRITERION IS THEREFORE 23 ROUTED CALLS ON 21 LINES - 13 calls in the android runner and 10 in the iOS
      runner - and the TWO REMAINING CALLS ARE DELIBERATELY LEFT RAW because they are CONDITION waits inside the
      android driver class, not settles: AdbDriver.wait_boot's `while time.time() < end` poll of
      sys.boot_completed, and AdbDriver.stop_recording's wait while an external screen recorder flushes its
      file. Routing either through the seam would let the gate fast-forward a wait that exists because another
      agent must reach a state, which is the exact defect this item is warned about. A selftest asserts each of
      the 23 surviving constants equals its pre-change value: the launch settle default of 2, the tap settle
      default of 1, the 0.5 after a text, key or type event, the 1 of an undeclared wait, and each value in the
      redrive sequences. A reviewer must be able to confirm no constant was quietly shortened, so the assertion
      enumerates them rather than sampling, and it compares three independently produced sides (a frozen table,
      the module AST, and what the runner actually requests at run time). SHORTENING A WAIT TO MAKE THE GATE
      FASTER IS EXPLICITLY FORBIDDEN by this item: that would make the gate faster by testing something other
      than what ships.
  - id: AC3
    text: >
      THE WAITS BECOME ASSERTED BEHAVIOUR, WHICH IS WHY THIS IS A COVERAGE ITEM AND NOT ONLY A SPEED ITEM.
      Today the gate drives these runners against FAKE drivers that return instantly, then sleeps two real
      seconds waiting for a user interface that does not exist to settle, and the ONLY thing it establishes
      about that wait is that time passed. With an injected clock that RECORDS what was asked of it, the
      requested durations and their ORDER become assertable for the first time: a launch requests its settle
      window, a tap requests one second, a type requests half a second, and a redrive requests
      terminate-then-launch in that order. Each of those is a NEW assertion over behaviour that is currently
      invisible. If this item lands with 46 seconds removed and no new assertions, it has thrown away the only
      thing those sleeps were buying, and that is the outcome to refuse.
  - id: AC4
    text: >
      IT IS FASTER, THE PROCESS RUNNER IS UNTOUCHED, AND THE FIGURE IS THE REAL ONE. The suite's elapsed time is
      recorded against the baseline; the prototype measured about 46 seconds recoverable here with ZERO assertion
      impact, and if the real saving is smaller, the real figure is what the manifest states. THE PROCESS RUNNER
      IS EXPLICITLY OUT OF SCOPE and asserted unchanged by sha256, because a globally injected clock breaks
      exactly SEVEN process-runner assertions - that runner spawns REAL subprocesses and asserts real signal
      delivery, force-kill and orphan reaping, which are operating-system properties a jumped clock invalidates.
      Engine canon holds: both runners re-synced byte-identical across engine and all six packs (7
      copies each, there is no root copy). No protected path is touched, scripts/verify.sh and the stage list are
      byte-UNCHANGED, the frozen safety core is byte-UNCHANGED, the full gate is GREEN, and RULE #1 is clean.
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds a clock-and-sleep parameter pair defaulting to the real functions to two
  mobile runner modules (a SettleWaiter seam), routes 23 unconditional settle calls on 21 lines through it while
  leaving the two condition waits in the android driver class raw, and adds the selftest block that asserts the
  requested durations and their order, re-synced byte-identical across engine and the packs. Because
  the defaults ARE the real clock, a revert makes no difference to any adopter running these runners; it only
  restores 46 seconds of gate time and removes the new coverage of the waiting behaviour. That is a cost and
  coverage regression rather than a return to a good state, and there is no migration.
---

## Intent

Measured on this gate: 117.1 seconds total, of which the selftest is 102.4, and 84.2 of that is the process
BLOCKING rather than computing (77.4s in time.sleep across 829 calls, plus 6.8s in select.poll). The sleeps are
not in the tests. They are literals in the bodies of the reference runner modules, and the gate drives those
runners against FAKE drivers that return instantly. So the gate sleeps two real seconds waiting for a user
interface that does not exist to settle, several hundred times.

This item takes the MOBILE half of that, which a prototype measured at about 46 seconds with zero assertion
impact. The process-runner half is a different item and a different argument, because that runner waits on a
real kernel.

The fix is not to shorten the constants. That would make the gate faster by making it test something other than
what ships, which is the kind of shortcut this repository exists to refuse. The fix is a seam the house ALREADY
USES TWICE: `.veldo/fleet.py:377` takes `clock=time.time, sleep=time.sleep`, and the OAuth token manager takes an
injected clock. These two runners were simply written without a pattern that already existed.

The best part of the change is not the speed. Today those settle windows are UNOBSERVABLE: the gate waits two
seconds and learns nothing except that two seconds passed. An injected clock that records what was asked of it
makes the requested durations and their order assertable for the first time. So the same item that removes 46
seconds also adds the only coverage those sleeps were ever supposed to provide.

## Context

- Why the identity assertion on the defaults matters more than it looks: the failure mode nobody would notice is
  a default that resolves to a fake clock, because the gate would pass and every adopter's runner would stop
  waiting. Asserting `is time.sleep` by identity closes it in one line.
- Why the constants are enumerated rather than sampled: an item with a speed target has an obvious incentive to
  shave a settle window, and a reviewer needs to confirm the absence of that cheaply.
- Why the process runner is asserted UNCHANGED here rather than merely left alone: the two runners live side by
  side and a well-meaning edit could easily generalize the seam into both. The sha256 assertion makes that a
  gate failure rather than a review finding.
- What the prototype actually established, so it is not overstated: with sleep neutralized the suite still passed
  3112 of 3112, and with a global virtual clock exactly seven assertions failed, ALL of them the process runner
  and NONE of them mobile. That is why this split is measured rather than chosen.

## Out of scope

- The process runner and its fixture windows. That is WARP-0715, it is contested, and faking its subprocess is
  refused because it would delete the only coverage those seven assertions provide.
- The lint stage (WARP-0711) and the repeated derivations inside the suite (WARP-0714).
- Any change to POLL, to any process-runner constant, or to any shipped default value anywhere.
- Any change to what a runner step DOES, to its failure messages, or to the driver interface.
- No protected path, no change to verify.sh or the stage list.

## Notes

- Write the AC3 duration assertions as part of the same change, not afterwards. The temptation is to land the
  speed and add the coverage later, and later does not arrive.
- Assert the defaults by IDENTITY, not by equality of behaviour. `is time.sleep` cannot be satisfied by a
  lookalike.
- Do not touch the process runner. If the seam looks like it generalizes, that is WARP-0715's argument to have.
- NO UNBACKED UNIVERSAL: "every settle constant keeps its value" and "behaviour outside the gate is
  byte-identical" each need the assertion that enumerates them. MEASURE FIRST, then write the sentence from the
  output.
- RULE #1 clean (ASCII hyphen only, no em dash, no en dash, no prose double-hyphen).
