---
schema: veldo.spec/v1
id: WARP-0112
title: Dogfood release - the companion control-tower home delivered through the layer (W12 of PLAN-0001)
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0001
work: W12
plan_revision: 4
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A real product iteration (the companion control-tower home) is expressed
      as a valid Product Plan (PLAN-0002) that passes the plan contract - outcomes
      with measures, a feature tree, an ordered acyclic work DAG, and regression
      journeys - and decomposes into specs with two-way mirroring intact
      (validate.py all exits 0).
  - id: AC2
    text: The iteration's regression journeys are driven LIVE against the running
      tripdesk backend and all pass - one owner-scoped call returns every section
      under the read budget, a missing user is 401, a foreign trip is 404, a
      zero-trip user is 200 with phase none, and the auto-selected trip is the
      owner's own - proving the layer's verification works on real product
      behavior, not fixtures.
  - id: AC3
    text: The layer's mechanics accept the iteration end to end - PLAN-0002 status
      burn-down shows 4/4 shipped, its release-check reports releasable, and the
      veldo gate stays green - with ZERO changes to the product under test (the
      dogfood drives the live backend and records VELDO artifacts only).
  - id: AC4
    text: Decision D1 is resolved (PLAN-0001 revision 4, open_decisions empty), so
      W12 is unblocked; shipping it makes PLAN-0001's twelve work items all shipped
      and its release-check releasable - VELDO 1.0 delivered through its own layer.
required_evidence: [operational]
rollback: git revert; the dogfood adds only VELDO artifacts (PLAN-0002, its four
  specs, this receipt spec, and the live journey proof) plus the D1 resolution in
  PLAN-0001. Reverting removes the receipt and restores open_decisions; no product
  code is involved because none was ever changed.
---

## Intent

VELDO 1.0 is not done when its machinery merges - it is done when a real product
iteration has been planned, decomposed, ordered, verified, and released through
the layer. This is that receipt: the companion control-tower home, an already
delivered, many-permutation product iteration, run through the whole method with
its journeys driven live against the running backend.

## Context

The iteration is captured as PLAN-0002 (companion home, four work items
WARP-0201..0204). Its behavior is verified by live API journeys against GET
/api/v1/home/ on the tripdesk backend (proof/WARP-0112/run_companion_journeys.py
+ companion_home_journeys.json, results in journey-results.txt). This exercises
the planning layer (F1), planned regression (F2), and the verification the method
promises - on a real product surface. It closes PLAN-0001's O1 (a real iteration
planned and delivered through the layer) and contributes O3/O4 evidence.

## Out of scope

Any change to the product. The dogfood drives the live tripdesk backend as the
system under test and touches no product code in tripdesk or mobile-android. A
general HTTP/API journey runner as shipped machinery (this one is dogfood
evidence, not a template) is a natural follow-up, noted not built.
