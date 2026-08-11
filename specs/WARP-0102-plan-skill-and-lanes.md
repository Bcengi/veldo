---
schema: veldo.spec/v1
id: WARP-0102
title: /veldo:plan skill, spec lane fields, and the promotion rule (W2 of PLAN-0001)
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0001
work: W2
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A spec may declare lane planned or standalone; validate.py enforces
      that planned requires both plan and work, standalone forbids both, an
      unknown lane value is rejected, and an absent lane stays valid
      (inference, back-compat). Unit-tested.
  - id: AC2
    text: The promotion rule holds mechanically - a spec promoted from
      standalone to planned validates only when the plan's work list and the
      spec's lane/plan/work agree in both directions; a half-promoted spec is
      red. Demonstrated against a real plan (negative test).
  - id: AC3
    text: .veldo/plan.py provides status (per-item burn-down + frontier),
      release-check (declared release conditions, non-zero with reasons when
      not met), and impact (transitive downstream dependents of a work item,
      warning on already-shipped dependents), all derived from spec status;
      exercised live against PLAN-0001 and unit-tested for the state logic.
  - id: AC4
    text: The /veldo:plan skill documents create, refine, approve, pull,
      revise (with impact), status, release, and the two-lane/promotion
      boundary, deferring the run-time context bundle and refusal to W3; the
      spec TEMPLATE carries the lane field and capabilities.yaml reflects
      plan_dialogue as procedure and plan_lane_fields / plan_ops as
      mechanical.
required_evidence: [unit, operational]
rollback: git revert; lane enforcement fires only when lane is declared
  (older specs unaffected), plan.py is additive, and the skill is prose; the
  63-case selftest includes all prior cases unmodified.
---

## Intent

The layer above specs gets its authoring surface and its two lanes. A
product iteration is defined and stewarded through /veldo:plan; a bug or
isolated change stays on the direct standalone path. The mechanical teeth -
lane consistency, promotion mirroring, and the computed status / release /
impact answers - make the plan real rather than narrated, while the dialogue
itself stays a skill (a procedure), keeping the layer light.

## Context

W2 of PLAN-0001, pulled from the ready frontier (depends only on W1, the
plan contract, which is shipped). Run-time integration (the plan context
bundle handed to the implementing agent, stale-revision and
unshipped-dependency refusal) is deliberately W3; regression mechanics are
W4. This spec is itself a planned, lane-tagged spec, so it exercises the
lane field it introduces.

## Out of scope

Run-time context bundle and dependency refusal (W3). Regression journey
activation wired into the gate (W4). No change to the plan contract itself.
