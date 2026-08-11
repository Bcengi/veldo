---
schema: veldo.spec/v1
id: WARP-0107
title: Android emulator journey runner with lifecycle re-drives (W7 of PLAN-0001)
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0001
work: W7
plan_revision: 3
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A real Android runner drives an emulator/device over adb through a
      journey (launch, tap, text, key, waits) and asserts against live device
      state (focused window and uiautomator dump); the passing fixture journey
      runs green end to end and exits 0.
  - id: AC2
    text: After the happy path the runner RE-DRIVES the flow through rotation,
      process death, background/foreground, and network loss, re-checking a
      recovery assertion each time; a failure in any re-drive fails the run.
      All four re-drives are exercised against a live emulator.
  - id: AC3
    text: The runner captures named UI states as screencaps and the whole run
      as a video, and on a failed assertion captures a FAILURE screencap and
      exits 1; the deliberately-failing fixture demonstrates the failure path.
  - id: AC4
    text: The journey declares a device matrix (device_profiles) and the runner
      fails if a declared profile is not covered (no silent partial matrix).
      The control logic - sequencing, re-drive orchestration, matrix
      completeness, assertion evaluation - is unit-tested with a fake driver
      so the gate needs no emulator; capabilities marks mobile_emulator_driving
      and device_matrix_execution reference, and the runner is not in the veldo
      gate.
required_evidence: [journeys, ui_states, interaction_recording, device_matrix, operational]
rollback: git revert; the runner and fixtures are additive files under
  scripts/runners/mobile/, touch no synced core, and are not wired into the
  veldo gate; the fake-driver selftest is the only gate coupling; the 97 prior
  cases pass within the 104.
---

## Intent

The founder named poor mobile AI testing as the single biggest gap; this
closes it for Android. The runner drives a real device the way a user does,
asserts on real device state, and - the part that matters most - re-drives
the flow through the lifecycle events mobile apps actually die on. Proof is
not a happy-path screenshot; it is a flow that survives rotation, being
killed, being backgrounded, and losing the network, captured as states and a
video, across a declared device matrix.

## Context

W7 of PLAN-0001, depends on W5 (the web runner, shipped) as the sibling
flows-and-states runner. This environment has an Android SDK, KVM, and an
AVD, so the runner was proven against a live emulator (happy path plus all
four re-drives, screencaps, and a 5.8 MB video). It ships as a reference: a
repo wires it to its own APK and matrix, and the gate stays emulator-free by
unit-testing the control logic with a fake adb driver.

## Out of scope

iOS (a later runner; stated absent). Building an app under test (the fixture
drives the built-in Settings app; consuming repos point at their APK). Wiring
an emulator launch into the every-commit veldo gate (proportionality).
