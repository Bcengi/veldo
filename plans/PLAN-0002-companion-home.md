---
schema: veldo.plan/v1
id: PLAN-0002
title: Companion control-tower home (backend) - the dashboard aggregation, delivered
kind: iteration
status: released
revision: 1
owner: dmitry
approved_by: dmitry
approved_at: 2026-07-16
risk: standard

outcomes:
  - id: O1
    becomes_true: A traveler opening the app gets one owner-scoped call that
      returns every home section, so the client never fans out into a request
      per section.
    measure: GET /api/v1/home/ returns all sections in a single 200 response
  - id: O2
    becomes_true: The dashboard is always about the RIGHT trip - the one the
      traveler is on or heading to next - never a stale open-ended trip that
      shadows a real dated one.
    measure: auto-selection picks the dated current trip; a live journey asserts
      the selected trip against the owner's data
  - id: O3
    becomes_true: The home is owner-scoped and graceful - a foreign trip is
      invisible and a user with no trips gets a calm empty state, not an error.
    measure: a foreign itinerary_id returns 404 and a zero-trip user returns 200
      with phase none
  - id: O4
    becomes_true: The home feels instant - it is a pure read with no model call,
      well under the read budget.
    measure: the response is under 500ms and no LLM is on the path

non_goals:
  - id: NG1
    text: The home never WRITES trip state - booking and edits go through their
      own endpoints; the dashboard only reads.
  - id: NG2
    text: The home never calls an LLM - every section is derived from stored data.

constraints:
  - id: C1
    text: One aggregation call, never one call per section (RULE #6).
  - id: C2
    text: The read stays under the 500ms budget.

feature_tree:
  - id: F1
    title: Single-call home aggregation - every section in one owner-scoped
      response, missing user rejected
    outcome_refs: [O1, O4]
  - id: F2
    title: Active-trip auto-selection - dated current beats stale open-ended,
      then upcoming, then most-recent
    outcome_refs: [O2]
  - id: F3
    title: Owner-scoping and empty-state grace
    outcome_refs: [O3]
  - id: F4
    title: Derived home content - phase, countdown, next action, chips, discover
      from stored data
    outcome_refs: [O1]

work:
  - item: CH1
    spec: WARP-0201
    title: Home aggregation endpoint - one owner-scoped GET returns every section;
      a missing user header is 401; the read stays under budget
    feature_refs: [F1]
    depends_on: []
    order: 10
  - item: CH2
    spec: WARP-0202
    title: Active-trip auto-selection with anti-shadowing - a dated trip whose
      window contains today beats a stale open-ended trip
    feature_refs: [F2]
    depends_on: [WARP-0201]
    order: 20
  - item: CH3
    spec: WARP-0203
    title: Owner-scoping and zero-trip grace - a foreign itinerary_id is 404 and
      a user with no trips is 200 with phase none
    feature_refs: [F3]
    depends_on: [WARP-0201]
    order: 30
  - item: CH4
    spec: WARP-0204
    title: Derived content - phase, countdown, next action, suggested chips, and
      discover derived from stored data with no LLM
    feature_refs: [F4]
    depends_on: [WARP-0201]
    order: 40

regression:
  journeys:
    - id: CJ1
      title: Home returns every section for a user with a trip - 200, all sections
        present, under the read budget
      activation: {when: start}
      owner_spec: WARP-0201
      profiles: [per_spec, release]
      suite: proof/WARP-0112 companion home journeys (live GET /api/v1/home/)
    - id: CJ2
      title: A missing user header is rejected with 401
      activation: {when: start}
      owner_spec: WARP-0201
      profiles: [release]
      suite: proof/WARP-0112 companion home journeys (live GET /api/v1/home/)
    - id: CJ3
      title: A foreign itinerary_id is 404 and a zero-trip user is 200 with phase
        none
      activation: {when: start}
      owner_spec: WARP-0203
      profiles: [per_spec, release]
      suite: proof/WARP-0112 companion home journeys (live GET /api/v1/home/)
    - id: CJ4
      title: The auto-selected trip is owner-scoped and is the traveler's own
        active trip
      activation: {when: start}
      owner_spec: WARP-0202
      profiles: [release]
      suite: proof/WARP-0112 companion home journeys (live GET /api/v1/home/)

release:
  milestone: Companion control-tower home delivered
  version: product-side (tracked in the tripdesk repository)
  mode: continuous
  require_all_work_shipped: true
  require_full_regression: true
  rollback: product-side (a tripdesk revert); this plan is a retrospective
    record of an iteration already delivered
  observation:
    duration: delivered and live-verified against the running backend (this plan
      is the W12 dogfood of PLAN-0001, not a timer)

open_decisions: []
---

## Intent

The companion home is the traveler's control tower: one screen that answers
"what is my trip and what do I do next." This plan records that iteration as it
was delivered, expressed through the VELDO layer so the dashboard's real contract
is planned, decomposed, and verified by journeys driven against the running
backend. It is the W12 dogfood of PLAN-0001: a real, many-permutation product
iteration proven end to end through the method, with zero changes to the product
under test.

## Context

The backend endpoint is GET /api/v1/home/ (HomeSummaryView), an owner-scoped
aggregation that returns every home section in one response, auto-selects the
trip the dashboard is about, is owner-scoped and graceful for edge cases, and
stays a fast read with no model call. Each work item below maps to a real,
observable behavior of that endpoint, verified live in the PLAN-0001 W12 proof.

## Out of scope

Any change to the product. This plan drives the live backend as the system
under test and records the VELDO artifacts only; the product code is untouched.
