---
schema: veldo.spec/v1
id: WARP-1502
title: A declaration diff flows the ordinary loop, with exactly two extra mechanics - plan is separate
  from apply, and a plan computed against a world that has since moved refuses rather than guessing
status: shipped
risk: standard - a pure planner and an applier whose only shipped adapter does nothing. It reaches no
  network, holds no credential and runs at no gate stage. It is not low because the staleness check is
  what stands between a reviewed plan and an apply against a world that moved, and getting that wrong
  in the permissive direction is how infrastructure tools destroy things nobody asked them to touch.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0015
work: W2
depends_on: [WARP-1501]
placement: [contracts]
footprint:
  - ".veldo/substrate_change.py"
  - "engine/.veldo/substrate_change.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-1502-infrastructure-change-type.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      PLAN IS PURE AND SEPARATE FROM APPLY. `plan()` compares two declarations and returns the
      operations that would reconcile them, reaching nothing and changing nothing; the same pair
      returns the same plan every time. A selftest drives create, update, replace and delete in one
      diff and checks each, and asserts two runs over one pair are identical.
  - id: AC2
    text: >
      A CHANGE THAT CANNOT BE MADE IN PLACE IS A REPLACE, NOT AN UPDATE, and the classifier fails
      toward REPLACE. `REPLACE_TRIGGERS` names the fields whose change destroys and recreates a
      resource; getting that list wrong in the permissive direction means an "update" that silently
      deletes something, so an ambiguous case must land on the destructive side. The plan says WHY
      ("kind changed, which cannot be done in place") rather than leaving a reader to infer it.
  - id: AC3
    text: >
      A STALE PLAN REFUSES, AND THIS IS THE SAFETY PROPERTY. The plan carries digests of the from-
      and to-declarations it was computed from; if either no longer matches at apply, it refuses
      `stale_plan` and applies nothing. A plan computed against a world that has since moved is a
      guess with a formatting convention. A selftest drives both directions of staleness separately,
      with the matching case beside them as the control.
  - id: AC4
    text: >
      ADOPTION-SAFE BY CONSTRUCTION. A repository with no substrate declarations plans nothing and
      applies nothing: an empty diff yields an EMPTY PLAN, which is a success rather than an error,
      and nothing in this module runs at gate time. Adopting the method must not opt a repository
      into infrastructure management. A selftest drives the empty case and asserts no gate stage
      references the module.
  - id: AC5
    text: >
      THE EXECUTION SEAM IS PLUGGABLE AND THE SHIPPED ADAPTER DOES NOTHING. `Adapter` is the
      interface and `FakeAdapter` records calls without acting, so every property here is proven
      offline and a real adapter is something an operator wires deliberately - the same shape as the
      action executor's target system, for the same reason: a module that can reach production in its
      default configuration is one nobody can safely test.
  - id: AC6
    text: >
      A FAILED APPLY REPORTS EXACTLY HOW FAR IT GOT. Apply stops at the first adapter failure and
      returns what had already been applied plus the operation it failed on, because an adapter that
      failed once is not trustworthy for the next call, and a partial apply that lies about its
      extent is worse than one that fails. A selftest drives a mid-plan failure and checks the
      completed count and the named failure.
required_evidence: [unit]
rollback: >
  Delete the module and its capability entry. Nothing reads it, no gate stage runs it, it writes no
  state and the only adapter it ships does nothing.
---

## Outcome

A declaration diff should be an ordinary change: specified, proven, gated, merged. What makes
infrastructure different is not the process but that the effect lands somewhere the repository
cannot see, and that some effects cannot be undone. So the loop gains two mechanics and no more.

**Plan then apply.** A human has to be able to read what will happen before it happens. Every
infrastructure tool worth using has this separation and this one is no exception.

**The plan is bound to what it was computed from.** This is the property that matters. A plan whose
from- or to-state has changed since it was computed describes a world that no longer exists, and
applying it anyway is the precise mechanism by which infrastructure tooling deletes things nobody
asked it to touch. It refuses and says re-plan.

## Adoption safety is a construction, not a promise

An empty declaration set produces an empty plan, and an empty plan is a no-op rather than an error.
Nothing here runs at gate time. A repository that adopts the method and never declares any
substrate is in a fully supported state and never touches a line of this.

## Out of scope

- Real adapters. The seam is the deliverable; a real one is an operator's deliberate act.
- The destructive floor. `irreversible_ops` is exposed here so there is ONE answer to which
  operations destroy something, but classifying and gating them is W4.
- Cost projection (W3), promotion (W5), drift (W6), ephemeral environments (W7).
