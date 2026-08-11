---
schema: veldo.spec/v1
id: WARP-0203
title: Companion home owner-scoping and zero-trip grace (CH3 of PLAN-0002)
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0002
work: CH3
plan_revision: 1
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: An explicit itinerary_id that the caller does not own (a foreign or
      unknown id) returns 404, never another user's trip - the home is
      owner-scoped.
  - id: AC2
    text: A user with no trips returns 200 with phase none and null sections, not
      a 404 - a calm empty state, not an error.
required_evidence: [operational]
rollback: product-side (a tripdesk revert); this is a retrospective spec of
  already-delivered behavior. Verified live via PLAN-0002 regression journey CJ3,
  reproduced in the PLAN-0001 W12 proof (proof/WARP-0112).
---

## Intent

The home never leaks across owners and never punishes a new user with an error:
a foreign trip is invisible (404), and a traveler with no trips sees a calm
empty home (200, phase none), not a failure.

## Context

Backend HomeSummaryView owner-scoped lookup and zero-trip branch. This is the
CH3 work item of PLAN-0002 (the W12 dogfood of PLAN-0001), verified live against
the running backend.

## Out of scope

Any product change. The spec drives the live backend as the system under test.
