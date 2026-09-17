---
schema: veldo.spec/v1
id: VELDO-0079
title: Grooming and admission requests through enrolled decision surfaces
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W64
plan_revision: 1
depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0078]
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
  - "engine/.veldo/control_grooming*.py"
  - ".veldo/control_grooming*.py"
  - "packs/*/.veldo/control_grooming*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0079_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0079-grooming-enrolled-decision-surfaces.md"
  - "specs/index.md"
  - "proof/VELDO-0079/*"
behavior_bearing: true
observability:
  logs: >
    Grooming receipts name request/version, rendered presentation, admission and priority rulings,
    rationale, actor and originating channel.
  metrics: >
    Count returned elaborations, rejected proposals, pending priorities and stale grooming answers
    per channel.
  traces: >
    Join exact request and decomposition bytes to the presentation seen, canonical answer and
    single authoritative admission settlement.
  error_taxonomy: >
    Distinguish unsigned prepared draft, changed brief, unauthorized groomer, absent priority and
    conflicting terminal ruling.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Grooming presents the complete authorization material and binds the answer to what
      the person saw. Set: request.request_digest/validate_record, request_projection.build_brief
      and control_grooming for R09/R12 material on every enrolled E surface. Completeness: Compare
      fields to A: class, outcome, comparable scope, exclusions, priority, ceiling, lane, policy,
      spec revisions, protected paths, release authority, expiry, evidence, decomposition,
      alternatives and questions. Publish actual briefs, mutate each field with an answer pending,
      and require E presentation-bound refusal including rejection. Telegram, Jira and signed CLI
      work independently; email requires its own enrollment proof. Falsifier: Omit decomposition
      digest from grooming presentation binding; grooming/changed-decomposition must detect
      admission from a superseded proposal.
    falsified_by: >
      Omit decomposition digest from grooming presentation binding; grooming/changed-decomposition
      must detect admission from a superseded proposal.
  - id: AC2
    text: >
      Claim: A person with current admission authority admits, rejects or returns work;
      preparation cannot authorize it. Set: request_reconcile._reconcile_one and
      authorization.is_authorized consuming control_grooming actions for RAW through
      AWAITING_GROOMING. Completeness: Cross every preparatory state with principal kinds and
      allowed rulings. Run real signed commands and E assertions, including a project manager
      claiming the owner role. Require actor-authored reasoning and distinct admission/priority
      decisions even when settled together; unresolved scope or acceptance questions block the
      applicable boundary. Falsifier: Accept a preparation-agent admission assertion because its
      project-manager role is present; grooming/preparer-cannot-admit must detect the transition.
    falsified_by: >
      Accept a preparation-agent admission assertion because its project-manager role is present;
      grooming/preparer-cannot-admit must detect the transition.
  - id: AC3
    text: >
      Claim: Concurrent grooming answers settle once and cannot expand the signed command or mint
      priority. Set: E settlement transaction used by control_grooming, across same-channel and
      cross-channel answers and retries. Completeness: Race actual authority clients over one
      request revision. Alter operation, target and priority/ceiling parameters under a retained
      CLI signature and require canonical digest refusal. Kill after commit before acknowledgment;
      retry original identity and require one replicated ruling, nonce and delivery obligation,
      with rejected preparation retained and zero floor capacity. Falsifier: Reuse a valid
      admission signature after changing the priority parameter without digest verification;
      grooming/signed-priority-substitution must fail.
    falsified_by: >
      Reuse a valid admission signature after changing the priority parameter without digest
      verification; grooming/signed-priority-substitution must fail.
required_evidence: [unit, integration]
rollback: >
  Suspend new grooming settlements, preserve request and presentation versions, and obtain a
  current authorized replacement ruling.
---

## Intent

Make grooming an attributable authorization act on the enrolled surface where the admission authority answers.

## Context

Package F, W64 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R09/R12, R61 and R72 supersede tracker-only wording. E supplies presentation and settlement; this item supplies grooming semantics. Its authority grant is critical. Risk is critical; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

New edge keys, channel activation, cryptography and discretionary machine admission are excluded.

## Notes

D1/D2 block durable grooming settlements and success replies; D3/D4 are inherited C boundaries. Dmitry must identify admission and priority authorities under R37/R64 before additional principals decide. A missing ruling remains a named blocker, never inferred from project ownership. Reuse the E full request digest, canonical source evidence and per-request quorum; map control_grooming into contracts/tracker/engine and W30 inventory before ready. Preserve rendered briefs and conflicting answer results without private signing material.
