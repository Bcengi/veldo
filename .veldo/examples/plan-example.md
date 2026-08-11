---
schema: veldo.plan/v1
id: PLAN-9001
title: Example - saved searches across web and email
kind: iteration
status: ready
revision: 1
owner: example-pm
approved_by: example-pm
approved_at: 2026-01-15

outcomes:
  - id: O1
    becomes_true: A signed-in user saves a search and reruns it from anywhere,
      including a weekly email digest.
    measure: journey RJ1 green on release build; digest opens tracked

non_goals:
  - id: NG1
    text: No shared or team-visible searches in this iteration.

constraints:
  - id: C1
    text: No new external services; digest rides the existing mailer.

feature_tree:
  - id: F1
    title: Save and rerun a search
    outcome_refs: [O1]
  - id: F2
    title: Weekly digest email
    outcome_refs: [O1]

work:
  - item: W1
    spec: WARP-9101
    title: Saved-search storage and API
    feature_refs: [F1]
    depends_on: []
    order: 10
  - item: W2
    spec: WARP-9102
    title: Save/rerun UI on the results screen
    feature_refs: [F1]
    depends_on: [WARP-9101]
    order: 20
  - item: W3
    spec: WARP-9103
    title: Weekly digest assembly and send
    feature_refs: [F2]
    depends_on: [WARP-9101]
    order: 30

regression:
  journeys:
    - id: RJ1
      title: Save a search, sign out, sign in, rerun it, get identical results
      activation: {when: after:WARP-9102}
      suite: e2e/saved-search.spec.ts

release:
  milestone: Saved Searches v1
  mode: continuous
  require_all_work_shipped: true
  require_full_regression: true
  rollback: feature flag saved_searches off; storage is additive
  observation:
    duration: 7 days of digest sends before the flag defaults on

open_decisions:
  - id: D1
    text: Digest send hour - product picks before W3 implementation starts.
    blocks: [WARP-9103]
---

## Intent

Users repeat the same searches daily and lose them between devices. After
this iteration a search is a durable object: saved once, rerun anywhere,
delivered weekly by email. The product becomes sticky through recall
rather than through notification volume.

## Ordered delivery rationale

Storage first because both surfaces consume it; UI and digest are then
deliberately parallel. The digest waits only on the send-hour decision,
which blocks nothing else.
