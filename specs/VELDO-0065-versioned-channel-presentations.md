---
schema: veldo.spec/v1
id: VELDO-0065
title: Versioned presentation receipts for every enrolled channel
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W50
plan_revision: 1
depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0064]
placement: [contracts, tracker, engine, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/request_projection.py"
  - ".veldo/request_projection.py"
  - "packs/*/.veldo/request_projection.py"
  - "engine/.veldo/request_reconcile.py"
  - ".veldo/request_reconcile.py"
  - "packs/*/.veldo/request_reconcile.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/control_channel_presentation*.py"
  - ".veldo/control_channel_presentation*.py"
  - "packs/*/.veldo/control_channel_presentation*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0065_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0065-versioned-channel-presentations.md"
  - "specs/index.md"
  - "proof/VELDO-0065/*"
behavior_bearing: true
observability:
  logs: >
    Presentation receipts record full request and subject digests, rendered brief digest,
    channel/object/message identifiers, publication time, and superseded receipt.
  metrics: >
    Count current and superseded presentations, request-content mismatches, absent answer
    references, and refused stale answers per enrolled channel.
  traces: >
    Trace exact rendered bytes through publication acknowledgment to a restricted assertion naming
    that presentation and the accepted or refused request revision.
  error_taxonomy: >
    Distinguish changed brief, changed choices, wrong channel, wrong presentation, unpublished
    receipt, expired request, and stale subject.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Immutable presentation receipts bind everything R72 says the person saw and preserve
      distinct request-content and settlement-subject identities. Set:
      request.request_digest/validate_record, request_projection.build_brief, and proposed
      presentation receipt encoding for Telegram chat, Jira, signed CLI, and email when enrolled.
      Completeness: Compare encoded fields to the A/R72 schema in both directions: request
      ID/version/full digest, subject digests, rendered brief bytes, risk and authority
      statements, choices, channel, conversation/issue and presentation IDs, and publication time.
      Render actual bytes, persist and sign receipts in separate processes, mutate each field, and
      recompute digests. Request versions participate in content identity; historical truncated
      hashes remain labeled legacy rather than silently reinterpreted. Falsifier: Leave request
      version out of the enrolled request digest and issue two otherwise equal revisions;
      presentation/version-digest must detect identical content identities.
    falsified_by: >
      Leave request version out of the enrolled request digest and issue two otherwise equal
      revisions; presentation/version-digest must detect identical content identities.
  - id: AC2
    text: >
      Claim: Every answer explicitly binds its ruling and rationale to the exact current
      presentation, including rejection. Set: request_reconcile._reconcile_one/_build_attestation
      and authorization._attestation_ok/is_authorized on each enrolled channel, consuming
      protected canonical evidence and B signed assertions. Completeness: Drive valid answers
      through real authority clients and signature verification, then hold subject digest fixed
      while altering brief/risk/choices or referencing another channel presentation. Also omit the
      reference, expire the request, supersede the subject, and submit status/text/timestamp-only
      answers. No stale, unpublished, or mismatched answer may settle; test acceptance and
      rejection equally. Falsifier: Restore _reconcile_one checking only bound_artifact.digest
      while an answer names a replaced brief; presentation/answer-binding must detect the accepted
      stale answer.
    falsified_by: >
      Restore _reconcile_one checking only bound_artifact.digest while an answer names a replaced
      brief; presentation/answer-binding must detect the accepted stale answer.
  - id: AC3
    text: >
      Claim: Presentation replacement is an explicit versioned operation and interrupted
      publication cannot fabricate evidence of what was shown. Set:
      request_projection.build_brief/_project_one and channel presentation publication using B
      effect and delivery obligations for each enrolled channel. Completeness: Publish two
      revisions with changed rendered content, retaining the first immutable receipt and a visible
      supersession link. Kill after send before receipt commit and before send after obligation
      commit; query real receiver evidence and current authority on restart. Mark uncertain
      deliveries pending and forbid answers until exact publication is established. Compare every
      channel adapter registration to receipt/replacement coverage. Falsifier: Create a published
      presentation receipt before receiver acknowledgment and kill before send;
      presentation/not-shown must detect acceptance of an answer to unseen content.
    falsified_by: >
      Create a published presentation receipt before receiver acknowledgment and kill before send;
      presentation/not-shown must detect acceptance of an answer to unseen content.
required_evidence: [unit, integration]
rollback: >
  Stop new presentations and answer acceptance for the affected contract, preserve old rendered
  bytes and receipts, and publish a clearly superseding qualified version.
---

## Intent

Bind every decision answer to the exact version and presentation shown on its originating channel.

## Context

Package E, W50 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A/B/C contracts govern implementation. This draft grants no implementation or activation authority.

R09, R36, R40, R60, and R72 expose the baseline digest-only binding defect. A correct subject digest cannot prove which risk statement or offered choice a person answered. The declared risk floor is critical; required approval must bind the eventual change and proof. This declaration records no approval.

## Out of scope

Canonical platform identity acquisition, quorum accumulation, tracker comment deduplication implementation, and ingress activation are owned by W51, W53, W57, and W58.

## Notes

D1/D2 block authoritative receipts and their publication; D3/D4 remain inherited C prerequisites without adding a channel-specific host decision. AC2 owns the reproduced answer-not-bound-to-presentation defect. Keep request content, rendered presentation, and polymorphic bound_artifact digests separate; do not break historical approval/two-key readers by substituting one for another. W57 AC1 owns the permanent Jira brief-comment key repair and consumes this receipt contract. This item defines channel-neutral receipt creation; W58 proves actual platform publication before activation. Canonicalize new engine copies for repository-only projection/reconcile modules and inventory the narrow presentation module under W30; map it before ready. Retain field-mutation diffs and their failing rows.
