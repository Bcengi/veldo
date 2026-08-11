---
schema: veldo.spec/v1
id: WARP-0105
title: Web journey, state, and accessibility reference runner (W5 of PLAN-0001)
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0001
work: W5
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A real web runner drives a browser (Playwright chromium) through a
      journey, asserting behavior at every step, and exits 0 only when every
      asserted step passes; the passing fixture journey runs green end to end.
  - id: AC2
    text: The runner captures named UI states as screenshots reached by
      DRIVING the flow (not static renders), and on a failed assertion stops,
      captures a FAILURE screenshot, and exits 1 - a broken flow is unproven
      from that point; the deliberately-failing fixture demonstrates this.
  - id: AC3
    text: A dependency-free accessibility scan flags missing image alt text,
      unlabeled inputs, controls without an accessible name, a missing
      document language, and duplicate ids; with a11y_fail_on it fails the
      run. The broken fixture triggers four real violations; the good fixture
      is clean.
  - id: AC4
    text: The runner ships as a reference with a self-test (pass fixture exits
      0, fail fixture exits 1), a README, and a portable Playwright resolver;
      capabilities.yaml marks journeys_runner, ui_state_runner, and
      accessibility_scan reference (wired per-repo into the journeys gate
      slot), not overclaimed as mechanical in the every-commit gate, and not
      run in the veldo repo's own gate (it has no user interface).
required_evidence: [journeys, ui_states, operational]
rollback: git revert; the runner and fixtures are additive new files under
  scripts/runners/web/, touch none of the synced core, and are not wired into
  the veldo gate; the 77-case selftest is unchanged.
---

## Intent

Product iterations need their user interface proven by DRIVEN flows, not
screenshots of a page that loaded. This ships the flows-and-states layer of
the method's UI-proof hierarchy as a real, self-testing runner: it drives a
browser through a journey, asserts each step, captures the states it reaches
by driving to them, and scans for the accessibility failures that most often
ship silently. A journey that cannot complete fails loudly with the failing
step named, because a perfect screenshot of a broken flow is not evidence.

## Context

W5 of PLAN-0001, no dependencies, pulled from the ready frontier. This
environment has Playwright chromium, so the runner is genuinely mechanical
where it runs; it ships as a reference because a consuming repo wires it to
its own app and journeys and points the gate journeys slot at the active
per-spec regression suite (W4). The veldo repo has no user interface, so the
runner is exercised in this spec's proof and by its self-test, not in the
veldo gate. Visual fidelity (render vs design composite) is the separate
veldo-visual.py; the Android runner is W7.

## Out of scope

Wiring a browser launch into the every-commit veldo gate (proportionality: no
UI here, and a per-commit browser launch is heavy and environment-dependent).
Token linting and visual baselines (W6). Mobile (W7).
