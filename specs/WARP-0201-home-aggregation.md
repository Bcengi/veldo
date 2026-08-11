---
schema: veldo.spec/v1
id: WARP-0201
title: Companion home aggregation endpoint - one owner-scoped call, every section (CH1 of PLAN-0002)
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0002
work: CH1
plan_revision: 1
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A GET /api/v1/home/ with a valid X-Bcengi-User-Id returns 200 with every
      home section present in one response (active_trip, phase, countdown_days,
      now_next, today, to_book, checklist, ideas_gaps, connectivity, insurance,
      weather, discover, next_action, suggested_chips) - the client never fans out
      into a request per section.
  - id: AC2
    text: A request with no X-Bcengi-User-Id is rejected with 401, not served a
      partial or unscoped home.
  - id: AC3
    text: The response is a single aggregation and returns under the 500ms read
      budget when measured against the running backend.
required_evidence: [operational]
rollback: product-side (a tripdesk revert); this is a retrospective spec of an
  already-delivered endpoint. Verified live via PLAN-0002 regression journeys CJ1
  and CJ2, reproduced in the PLAN-0001 W12 proof (proof/WARP-0112).
---

## Intent

The companion home is one owner-scoped aggregation: a single call returns every
section the dashboard needs, so the client makes one request, not one per
section (RULE #6). A caller without an identity gets nothing.

## Context

Backend endpoint GET /api/v1/home/ (HomeSummaryView). This spec is the CH1 work
item of PLAN-0002 (the W12 dogfood of PLAN-0001), recording delivered behavior
and verifying it live against the running backend. No product code is changed.

## Out of scope

Any product change. The spec drives the live backend as the system under test.
