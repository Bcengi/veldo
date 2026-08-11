---
schema: veldo.spec/v1
id: WARP-0103
title: /veldo:run plan integration - context bundle and refusals (W3 of PLAN-0001)
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0001
work: W3
plan_revision: 3
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: plan.py run-check refuses to build a planned spec whose declared
      dependencies are not all shipped, naming each unshipped dependency, and
      clears a spec whose dependencies are all shipped (exercised live -
      WARP-0111 refused on WARP-0103, WARP-0103 clear on shipped WARP-0102).
  - id: AC2
    text: run-check also refuses when the spec's plan_revision is older than
      the plan's current revision (stale context - the plan changed under it),
      and clears when they match; demonstrated with a stale then current spec.
  - id: AC3
    text: plan.py bundle emits the plan context bundle for a work item - the
      iteration's outcomes, this item's feature and dependency status, the
      inherited constraints, and the regression active for this spec - so the
      agent building the part sees the whole without the plan being copied.
  - id: AC4
    text: plan.py hash produces a stable content hash of the plan (excluding
      volatile keys) for binding a proof to the plan state it was built
      against; /veldo:run enforces run-check, loads the bundle, and records the
      hash before building a planned spec; capabilities marks
      plan_run_integration mechanical.
required_evidence: [unit, operational]
rollback: git revert; bundle/run-check/hash are additive plan.py verbs, the
  run skill gains a planned-spec preflight, the template gains an optional
  plan_revision field, and the only gate coupling is added selftest; the 94
  prior cases pass within the 97.
---

## Intent

The plan stops being advisory at build time. Before an agent builds a planned
spec, the layer enforces deliberate order mechanically: it refuses a spec
whose dependencies have not shipped and a spec whose plan context has gone
stale under a revision, and it hands the agent the whole iteration as a
context bundle so the part is built with the whole in view. The proof records
the plan hash, binding the change to the exact plan state it was built
against. This is the run-time half of the planning layer; W2 was the
authoring half.

## Context

W3 of PLAN-0001, depends on W2 (shipped). Uses the plan contract (W1) and the
plan-ops module (W2). This spec is itself pulled at plan revision 3 and
carries plan_revision: 3, so run-check clears it; it demonstrates the very
mechanism it introduces.

## Out of scope

Automatic invocation from a hook (the run skill enforces run-check; there is
no separate pre-build hook). Regression execution (W4 computes the active
suite; running it is per-repo). Docs integration (W11).
