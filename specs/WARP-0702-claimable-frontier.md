---
schema: veldo.spec/v1
id: WARP-0702
title: Global claimable frontier - what a worker may claim across the whole repo
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0007
work: Y2
plan_revision: 2
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A claimable() function computes the BUILD work claimable across the whole repo -
      a ready spec whose plan dependencies are all shipped (the per-plan frontier, reusing
      the plan machinery's item_state, shipped set, and decision blocks) across every active
      plan, plus standalone or bug specs (lane standalone) that are ready.
  - id: AC2
    text: It also surfaces REVIEW work - a spec in status review awaiting its independent
      verdict - as a claimable unit tagged kind review, so a worker with no claimable build
      can pick up a review instead of idling.
  - id: AC3
    text: It excludes any unit that already has a live claim (via the claim ledger's
      claimed_units), so two workers never see the same unit as claimable.
  - id: AC4
    text: It excludes work whose requirements are not a subset of the worker's capabilities
      (via the claim ledger's capability_ok) and work outside the worker's scope (a plan id
      or a label), so capability-gated work only surfaces to a capable worker and grouping by
      plan or label works.
  - id: AC5
    text: A selftest drives claimable() over a temporary repo tree and a temporary claims
      root - asserting a ready build with deps met, a standalone ready spec, and a pending
      review are claimable, while a dependency-blocked build, capability-gated work without
      the capability, an already-claimed unit, and out-of-scope work are excluded - and is
      non-tautological: with the capability the gated work appears, and after a claim the unit
      drops out.
required_evidence: [unit]
rollback: git revert; additive - a new .veldo/frontier.py, a selftest block, one capability
  entry (both copies), and the WARP-0702 spec; no protected path; read-only.
---

## Intent

The read side of the fleet's self-division: given a worker's capabilities and optional
scope, compute exactly what it may claim right now, drawn from the whole repo (every
active plan plus standalone specs plus pending reviews) rather than one plan, so an idle
worker always finds ready work if any exists and never sees work it cannot run or that
another worker already holds.

## Context

Y2 of PLAN-0007. It sits between the claim ledger (WARP-0701, which grants an atomic
capability-matched claim) and the worker loop (WARP-0703, which repeatedly claims the next
claimable unit and dispatches it). It reuses the pure plan logic (item_state, shipped set,
decision blocks) and the claim ledger (capability_ok, claimed_units); repo reading is
parametrized by repo_root so it is testable over a temporary tree, and a worker can also be
scoped to a plan or a label for grouping.

## Notes

Spec front matter is parsed with parse_yamlish (not the simple reader) so requires and
labels come through as real lists. BUILD candidates come only from ACTIVE plans (status ready or in_progress) and are frontier
items whose spec status is ready - a draft (unapproved) plan yields nothing claimable and a
released/closed plan has no frontier; standalone candidates are lane standalone and ready;
REVIEW candidates are any spec in status review. The function is read-only. Scoping across multiple repos (a workspace) is
the worker/launcher's concern (Y3, Y7); this item scopes within a repo by plan or label.
