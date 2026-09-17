---
schema: veldo.spec/v1
id: VELDO-0070
title: Independent decision review bound to full framing and distinct principals
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W55
plan_revision: 1
depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0069]
placement: [contracts, engine, tracker, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/decision_review.py"
  - ".veldo/decision_review.py"
  - "packs/*/.veldo/decision_review.py"
  - "engine/.veldo/decision.py"
  - ".veldo/decision.py"
  - "packs/*/.veldo/decision.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/request_reconcile.py"
  - ".veldo/request_reconcile.py"
  - "packs/*/.veldo/request_reconcile.py"
  - "engine/.veldo/control_decision_review*.py"
  - ".veldo/control_decision_review*.py"
  - "packs/*/.veldo/control_decision_review*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0070_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0070-independent-decision-review.md"
  - "specs/index.md"
  - "proof/VELDO-0070/*"
behavior_bearing: true
observability:
  logs: >
    Review receipts identify reviewer principal and assignment, full framing digest, challenged
    options/assumptions, disposition, and unresolved objections.
  metrics: >
    Count distinct eligible reviewers, duplicate-principal submissions, stale framing reviews,
    blocked dispositions, and requests awaiting independent review.
  traces: >
    Join accepted review assignment and exact input bytes to reviewer output, independent
    validation, scoped objection disposition, and decision settlement.
  error_taxonomy: >
    Distinguish unwired reviewer, incomplete attack, changed framing, same-principal duplicate,
    independence failure, unauthorized override, and unresolved objection.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Production decision review binds the full framing content and challenges the entire
      accepted option and assumption set. Set:
      decision_review.LiveAdversarialReviewer.review/validate_review/bind_review and
      decision.load_record for each accepted decision risk tier and enrolled review delivery
      channel. Completeness: Obtain substantive review artifacts from independently assigned
      reviewers through actual production submission/validation processes. Enumerate framing
      fields and declared option/assumption IDs; compare challenge coverage in both directions and
      mutate text while retaining ID/version. Require signed assignment/source digests and named
      refusal of stale, missing or fabricated review output; an unwired reviewer remains blocked.
      Falsifier: Retain bind_review comparing only ID/version after changing a dead_end text;
      review/full-framing must detect acceptance of the stale review.
    falsified_by: >
      Retain bind_review comparing only ID/version after changing a dead_end text;
      review/full-framing must detect acceptance of the stale review.
  - id: AC2
    text: >
      Claim: Required reviews count distinct authenticated principals satisfying policy
      independence, never supporting files or channel identities. Set:
      decision_review._valid_bound_reviews_by_decision/required_reviews_for/decided_requires_review
      and authorization._tally using the accepted policy and membership snapshot. Completeness:
      Derive review requirements from every risk tier and request-level strengthening. Submit
      several valid reviews by one principal through Telegram, Jira, signed CLI and email when
      enrolled; then use distinct eligible principals as a positive control. Race revocation and
      membership changes with review acceptance in real SQLite; missing policy or independence
      cannot fall back to a permissive count. Preserve person-required quorum separately from
      independent machine confirmation. Falsifier: Increment bound_counts for every supporting
      file from one reviewer as the baseline does; review/distinct-principals must detect a
      falsely satisfied multi-review requirement.
    falsified_by: >
      Increment bound_counts for every supporting file from one reviewer as the baseline does;
      review/distinct-principals must detect a falsely satisfied multi-review requirement.
  - id: AC3
    text: >
      Claim: Blocking objections require explicit current authorized disposition and cannot
      disappear behind a later supporting review or a self-declared override. Set:
      decision_review.decided_requires_review/_override_problems/check_reviews and
      request_reconcile settlement for review-disposition touchpoints on each enrolled channel.
      Completeness: Create conflicting real review artifacts, then submit a later defensible
      result, an unsigned review_override, an override naming the wrong review, and a
      presentation-bound authorized disposition. Enumerate objection states and both race orders
      with framing supersession; require immutable prior findings, no decision permission while
      unresolved, and exactly the accepted scoped disposition afterward. Falsifier: Skip
      unresolved objection checks whenever supporting count reaches the required number;
      review/objection-survives-pass must catch the incorrectly permitted decision.
    falsified_by: >
      Skip unresolved objection checks whenever supporting count reaches the required number;
      review/objection-survives-pass must catch the incorrectly permitted decision.
required_evidence: [unit, integration]
rollback: >
  Stop affected decision acceptance, retain review artifacts and unresolved findings, and obtain
  fresh independently bound reviews or authorized dispositions under current framing.
---

## Intent

Produce and consume independent decision reviews over exact framing without inflating reviewer counts or erasing objections.

## Context

Package E, W55 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A/B/C contracts govern implementation. This draft grants no implementation or activation authority.

R37, R40, R46, R60 and R71 extend decision_review.py, whose live reviewer refuses, binding checks only version and IDs, and supporting count increments per file. These gaps can authorize a foundation without the required scrutiny. The declared risk floor is critical; required approval must bind the eventual change and proof. This declaration records no approval.

## Out of scope

Changing the repository review/model-selection policy, enrolling new real reviewers, and production engine qualification are excluded.

## Notes

D1/D2 block accepted review/settlement storage and publication; D3/D4 are inherited C prerequisites. Only actually enrolled principals satisfy named requirements; missing additional reviewers blocks the relevant quorum. E remains independent of D: channel review can use eligible enrolled people, while any model reviewer must use an already qualified engine and applicable repository model/independence policy. A passing model assertion never supplies a personal decision. Wire the existing LiveAdversarialReviewer seam without manufacturing results or implementing a second gate. Map decision_review and control_decision_review into effective contracts/engine areas and inventory new assets before ready. Save each framing/count/objection mutation diff and its failing row; fixtures alone cannot certify the production review delivery path.
