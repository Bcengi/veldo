---
schema: veldo.spec/v1
id: WARP-0308
title: iOS mobile runner (reference, macOS-gated) - B8 of PLAN-0003
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0003
work: B8
plan_revision: 2
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: An iOS journey runner ships at
      engine/scripts/runners/mobile/veldo_ios_runner.py. It reads a
      journey (a name, a bundle_id, a device udid, and steps of launch, tap,
      type, wait, expect_text, expect_label, and state, plus optional
      device_profiles, optional lifecycle_redrives, and an optional
      recovery_assertion) and drives a SimctlDriver (xcrun simctl - boot,
      launch, terminate, screenshot, plus an accessibility state read for
      assertions) through a driver seam, so the control logic runs against a
      FakeDriver with no simulator. It exits 0 when every asserted step and
      every lifecycle re-drive passes on every declared device profile, and
      exits 1 with the failing step or re-drive named and a failure screenshot
      captured.
  - id: AC2
    text: The lifecycle re-drives are first-class and honest. process_death
      terminates the app, re-launches it, and re-asserts the recovery_assertion
      still holds, and it proves a REAL restart via a launch token (the pid
      simctl returns from launch) that must change, so a no-op terminate whose
      relaunch returns the same token is caught as a failure and never a vacuous
      pass. background_foreground backgrounds the app (the home screen) and
      re-launches and re-asserts, and appearance toggles the interface style and
      re-asserts. A re-drive whose recovery assertion fails names the re-drive
      and the failure. Only the re-drives xcrun simctl can honestly drive are
      offered; rotation and network loss are out of scope here because they need
      the accessibility bridge or host manipulation, not simctl.
  - id: AC3
    text: Device-matrix completeness. A journey may declare device_profiles; the
      runner records the connected and driven profile and FAILS if any declared
      profile is uncovered, naming the missing profile, so a partial matrix
      cannot pass silently.
  - id: AC4
    text: The control logic is unit-tested in scripts/selftest.py with a FAKE
      driver and NO simulator, mirroring the Android block. A happy journey
      passes; a journey with a failing assertion exits 1, names the step, and
      records a failure screenshot via the fake; a no-op process death (a
      stubborn fake whose launch token does not change) is caught as a re-drive
      failure; and a declared-but-uncovered device profile fails naming the
      missing profile. All prior selftest cases keep passing and the gate stays
      green.
  - id: AC5
    text: The runner is generic - zero company or product names in the runner,
      fixtures, wrapper, or README - and .veldo/capabilities.yaml (template and
      repository instance, kept byte-identical) declares it status reference (a
      shipped reference that REQUIRES macOS and a live iOS simulator to drive;
      the veldo home repo is Linux and does not run it), never mechanical. The
      docs-hygiene, secret, lint, and template-sync gates stay green.
required_evidence: [unit]
rollback: git revert; B8 adds a new runner file, a fixture pair, a wrapper and a
  README section under engine, a selftest block, and an honest
  capabilities entry (template and instance) - no protected gate script or
  enforcer is touched, so reverting removes the reference artifact and its unit
  block with no effect on any running gate; the prior selftest cases are
  unchanged.
---

## Intent

PLAN-0003 (the batteries) ships a reference runner for every common product
surface. B8 is the iOS mobile surface. The outcome that should become true is
that a repository on macOS can drop in a generic runner, point it at its own
app and a booted simulator, drive a journey of steps, and get proof that the
flow survives the lifecycle events that actually break mobile apps: process
death, backgrounding, and an interface-style change. A flow that passes once
but does not come back after the process is killed is not proven. The runner
re-drives those events and re-asserts, and it proves the restart is real (the
launch token must change) so a terminate that quietly did nothing cannot pass.

## Context

B8 of PLAN-0003, feature F3 (mobile and device surfaces), pulled against plan
revision 2, with no dependency. It follows the shipped runners' pattern: a
generic reference under engine/scripts/runners/, a fixture PAIR, and
a unit test that gate-tests the control logic with a fake driver. It is the iOS
sibling of the shipped Android runner (WARP-0307 in the same family shipped the
integration surface; the Android runner shipped earlier), mirroring its
structure exactly: a driver class wrapping the real tool with thin named
methods so a FakeDriver can stand in, assert_step / apply_step / redrive /
run(journey, driver, outdir), first-class lifecycle re-drives, device-matrix
completeness, screenshot on failure, and exit 0 all-pass / exit 1
first-failure-named. The one honest difference from Android: this machine (the
veldo home repo) is Linux with no macOS and no iOS simulator, so the live
SimctlDriver ships and is documented but is NOT run in the home gate; the
control logic is what is gate-tested, via the fake driver.

## Out of scope

Real-device farms and cloud device labs. XCUITest harness generation (the
runner uses XCUITest or WebDriverAgent as the accessibility bridge for tap,
type, and UI reads on macOS, but it does not generate that harness). Driving a
live simulator in the home gate, because that needs macOS which is not present
here. Rotation and network-loss re-drives, which xcrun simctl cannot honestly
induce on its own (they need the accessibility bridge or host-network control);
the runner offers only the re-drives simctl genuinely supports.

## Notes

Why reference-honest: there is no macOS in the veldo home environment, so a live
simulator cannot be driven here and the honest evidence is the fake-driver unit
tests, not an operational run. required_evidence is therefore [unit], NOT
operational: claiming an operational or live-simulator run on a Linux box would
be a lie the reviewer will (correctly) reject. The live SimctlDriver is shipped
and documented, but only its CONTROL LOGIC (journey sequencing, lifecycle
re-drive orchestration with a provable restart, device-matrix completeness, and
first-failure-named) is gate-tested, driven against a FakeDriver with no
simulator. An adopting repo on macOS runs the same runner against a real booted
simulator (and wires the accessibility bridge for tap, type, and UI-state
assertions). capabilities.yaml states the honest status: reference, never
mechanical, because the veldo repo does not itself run it against a live
simulator.
