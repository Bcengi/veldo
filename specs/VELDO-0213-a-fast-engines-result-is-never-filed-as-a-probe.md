---
schema: veldo.spec/v1
id: VELDO-0213
title: A fast engine's result is never filed as a probe
status: ready
risk: standard
owner: Dmitry Grinberg
human_approval: not_required
lane: standalone
placement: [engine, fleet]
protected_paths: []
footprint:
  - engine/.veldo/control_launch.py
  - .veldo/control_launch.py
  - scripts/suites/80_veldo_0155_claude_baseline.py
  - scripts/check_teeth_mutations.py
  - specs/VELDO-0213-a-fast-engines-result-is-never-filed-as-a-probe.md
  - specs/index.md
  - proof/VELDO-0213/*
behavior_bearing: true
observability:
  logs: Retain the engine result and its receipt in the existing terminal artifact.
  metrics: Existing complete, missing_result and configuration_stop verdicts.
  traces: The prompt write and terminal result belong to the same dispatch.
  error_taxonomy: Preserve configuration_stop:prompt_write_failed on failed input.
acceptance_criteria:
  - id: AC1
    text: >
      A held prompt counts as written from the start of its write. A named write
      helper marks it before calling stdin.write and flushing. The suite 80 row
      paid-api/prompt-write feeds a well-formed one-turn result synchronously
      inside a fake stdin.write, and requires that exact decoded result and
      receipt as Terminal.result with verdict complete, without timing or threads.
    falsified_by: >
      Move the mark after write and flush in the helper. Mutation
      prompt213-mark-after-write must fail paid-api/prompt-write with missing_result.
  - id: AC2
    text: >
      Actual probe results remain probes, including zero-turn results after the
      prompt starts. The write helper propagates write and flush errors to the
      existing input_failed and configuration_stop path. Suite 80 checks probes
      and error propagation; suite 86's review/probe-terminal retains the full
      receiver failure check.
    falsified_by: >
      Disable Terminal's probe guard: role127-probe-is-terminal must still fail
      review/probe-terminal, and suite 80 must reject the probe as a completion.
      Suppress input_failed at receiver exit: the existing
      role127-prompt-write-failure-swallowed case must fail review/probe-terminal.
required_evidence: [unit, integration]
rollback: Revert the prompt write helper and its call site in both production copies.
---

## Intent

Prevent a fast engine response from being mistaken for the capability probe.
The feeder currently writes and flushes before marking the prompt, while the
stdout reader classifies results concurrently. Host suite 106 exposed a build
with exit status zero and a one-turn result but verdict missing_result.

## Approval

Telegram 33105 "I approve tickets now, don't need to rubberstamp later."

## Scope

Only the ordering of the held prompt write and its terminal mark changes.
Login validation, probe classification and input failure handling retain their
existing contracts. Host integration and mutation commands are recorded in
proof/VELDO-0213/HOST_RUNS.md; local Python checks require no user manager.
