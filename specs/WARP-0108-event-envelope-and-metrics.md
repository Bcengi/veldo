---
schema: veldo.spec/v1
id: WARP-0108
title: Event envelope v1 and metrics derivation (W8 of PLAN-0001)
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0001
work: W8
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: The event envelope v1 is defined and validated - every line in
      .veldo/events.jsonl must be JSON with schema veldo.event/v1, a type from
      the fixed vocabulary (the loop's real steps), and a timestamp; unknown
      types, missing timestamps, and non-JSON lines are rejected. The check
      runs in the gate and the existing gate/emergency events conform.
  - id: AC2
    text: .veldo/events.py emits conforming envelopes for the human-driven loop
      steps - each with a generated id, a correlation_id (defaulting to the
      spec id so a change's events tie together), and an optional
      human_minutes field; an unknown event type is refused at emit time.
  - id: AC3
    text: .veldo/metrics.py derives the numbers that matter from the event
      stream by correlation_id - spec-to-ship latency, proof latency, total
      human minutes (the scarce-resource metric), gate pass rate, and open
      emergency debt; computed values are verified on a synthetic stream.
  - id: AC4
    text: The envelope, emitter, and metrics reader are exercised in the
      gate's unit self-test; /veldo:status surfaces the metrics; capabilities
      marks event_envelope_v1 and metrics_derivation mechanical and keeps
      human_minutes emission honestly procedure (skill-instructed, field and
      aggregation mechanical). No protected path is touched (verify.sh and
      veldo-guard.sh already emit the envelope, unchanged).
required_evidence: [unit, operational]
rollback: git revert; events.py and metrics.py are additive, the event check
  accepts what the gate and guard already emit, and the only gate coupling is
  the events check plus added selftest cases; the 84 prior cases pass within
  the 94.
---

## Intent

Events stop being a thin log and become the analyzable spine of the method:
a stable envelope with ids and correlation, a fixed vocabulary of the loop's
real steps, and human_minutes on the steps that cost human attention. From
that stream the metrics that actually indicate health are derived - how long
a change takes to ship, how fast it is proven, and how many human minutes it
cost - never lines of code. The numbers are computed, never reported.

## Context

W8 of PLAN-0001, no dependencies, pulled from the frontier. Backward
compatible by design: verify.sh and veldo-guard.sh already write
veldo.event/v1 lines with schema, type, and timestamp, so the envelope check
passes on history and neither protected script is touched. The emitter adds
ids and correlation for the human-driven steps the skills instruct. This
underpins W9's closure work, which consumes the event stream.

## Out of scope

Automatic emission at every loop step from mechanical code (the skills
instruct emission; only the gate and guard emit mechanically today). The
core-loop closure that consumes events (W9).
