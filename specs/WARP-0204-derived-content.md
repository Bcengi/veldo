---
schema: veldo.spec/v1
id: WARP-0204
title: Companion home derived content - phase, next action, chips, discover, no LLM (CH4 of PLAN-0002)
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0002
work: CH4
plan_revision: 1
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: For a user with a trip, the response carries a derived phase (before,
      during, or after) and a countdown_days consistent with the trip dates and
      the caller's local now.
  - id: AC2
    text: For an active trip, next_action, suggested_chips, and discover are
      derived and present (a concrete next step, contextual chips, and discovery
      items), not empty placeholders.
  - id: AC3
    text: The path invokes no LLM - it is a pure read derived from stored data,
      evidenced by the sub-500ms live timing and by the absence of any model call
      in HomeSummaryView.
required_evidence: [operational]
rollback: product-side (a tripdesk revert); this is a retrospective spec of
  already-delivered behavior. Verified live via PLAN-0002 regression journey CJ1
  plus code inspection, reproduced in the PLAN-0001 W12 proof (proof/WARP-0112).
---

## Intent

The home is not a raw data dump: it derives the phase of the trip, the countdown,
the single most useful next action, contextual chips, and discovery - all from
stored data, with no model call on the path, so it stays instant.

## Context

Backend HomeSummaryView section derivation. This is the CH4 work item of
PLAN-0002 (the W12 dogfood of PLAN-0001), verified live against the running
backend.

## Out of scope

Any product change. The spec drives the live backend as the system under test.
