---
schema: veldo.plan/v1
id: PLAN-0001
title: Starter plan - replace with the first real increment
kind: iteration
status: draft
revision: 1
owner: set-an-owner

outcomes:
  - id: O1
    becomes_true: Replace with the observable product change your first increment delivers for users.
    measure: How anyone verifies it happened.

non_goals:
  - id: NG1
    text: Name what this first increment deliberately does not do, so scope drift has a wall to hit.

constraints:
  - id: C1
    text: A cross-cutting rule every work item below inherits.

feature_tree:
  - id: F1
    title: The first capability a user can name
    outcome_refs: [O1]

work:
  - item: W1
    spec: VELDO-0000
    title: The first small, independently provable increment
    feature_refs: [F1]
    depends_on: []
    order: 10

regression:
  journeys:
    - id: RJ1
      title: The journey that must stay green across every item of this plan
      activation: {when: start}
      suite: where it runs

release:
  milestone: First increment shipped
  mode: continuous
  require_all_work_shipped: true
  require_full_regression: true
  rollback: How the increment retreats if observation says it should.
  observation:
    duration: what watching it in production means here

open_decisions:
  - id: D1
    text: Replace with the first open decision, or delete this block once nothing waits on a human answer.
    blocks: []
---

## Intent

This is the starter plan that veldo init lays down so a fresh repository holds a
valid plan the moment it is initialized. Replace it with the real increment:
the holistic view of why this increment, for whom, and what the product is
afterward. Every spec pulled from this plan inherits this context, so write it
for the agent who will see one work item at a time.

## Ordered delivery rationale

Explain why the work graph has this shape: what genuinely blocks what, what is
deliberately parallel, and what the ready frontier looks like at each stage.
Until you edit it, this plan declares a single unstarted work item so the plan
validates and the burn-down renders while you shape the real decomposition.
