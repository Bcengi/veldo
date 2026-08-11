---
schema: veldo.spec/v1
id: WARP-0202
title: Companion home active-trip auto-selection with anti-shadowing (CH2 of PLAN-0002)
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0002
work: CH2
plan_revision: 1
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: For a user with trips and no explicit itinerary_id, the home auto-selects
      the traveler's own active trip and returns it in active_trip, scoped to that
      user (never another user's trip).
  - id: AC2
    text: Selection follows a deterministic priority - a dated trip whose window
      contains today, then an open-ended started trip, then the soonest upcoming,
      then the most recently touched - so a stale open-ended trip cannot shadow a
      dated current trip. Evidenced by the _auto_select implementation.
  - id: AC3
    text: An explicit owner-scoped ?itinerary_id= selects that trip; a valid
      owned id returns 200 for the named trip.
required_evidence: [operational]
rollback: product-side (a tripdesk revert); this is a retrospective spec of
  already-delivered behavior. Verified live via PLAN-0002 regression journey CJ4
  plus code inspection of _auto_select, reproduced in the PLAN-0001 W12 proof.
---

## Intent

The dashboard must always be about the RIGHT trip - the one the traveler is on
or heading to next - and never a stale open-ended trip that shadows a real dated
one. The selection order is deterministic and owner-scoped.

## Context

Backend HomeSummaryView._auto_select. This is the CH2 work item of PLAN-0002
(the W12 dogfood of PLAN-0001). AC2 names the specific anti-shadowing rule the
code documents; a live journey confirms the selected trip is the owner's own.

## Out of scope

Any product change, and constructing synthetic shadowing fixtures in the live
data. AC2 is evidenced by the code's ordering plus live owner-scoping.
