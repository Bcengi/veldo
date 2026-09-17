---
schema: veldo.spec/v1
id: VELDO-0090
title: Capability-bound specialist selection
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W75
plan_revision: 1
depends_on: [VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0089]
placement: [contracts, fleet, engine, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/tasks.py"
  - ".veldo/tasks.py"
  - "packs/*/.veldo/tasks.py"
  - "engine/.veldo/claim.py"
  - ".veldo/claim.py"
  - "packs/*/.veldo/claim.py"
  - "engine/.veldo/frontier.py"
  - ".veldo/frontier.py"
  - "packs/*/.veldo/frontier.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/control_specialist*.py"
  - ".veldo/control_specialist*.py"
  - "packs/*/.veldo/control_specialist*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0090_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0090-capability-bound-specialist-selection.md"
  - "specs/index.md"
  - "proof/VELDO-0090/*"
behavior_bearing: true
observability:
  logs: >
    Selection receipts identify assignment/station, required actor and capabilities, roster
    revision, eligible engine/host profile and chosen principal.
  metrics: >
    Count eligible candidates, capability/independence refusals, missing-specialist blockers and
    owner staffing obligations.
  traces: >
    Join current team requirements through deterministic candidate filtering to a bounded
    assignment and its receiving authority recheck.
  error_taxonomy: >
    Distinguish no qualified specialist, wrong actor kind, revoked membership, engine mismatch,
    self-review and budget unavailable.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Selection uses current capabilities, authority, engine eligibility, context and
      independence requirements conjunctively. Set: control_specialist selection integrating
      tasks.claim_answer/claim_task, claim.capability_ok, frontier.claimable and
      authorization.is_authorized. Completeness: Construct the complete role/station predicate
      matrix from team and assignment schemas. Vary each predicate independently, including model
      version/host qualification, required person/named principal, revocation and independence.
      Use real assignments and receiver rechecks; satisfying capabilities alone cannot satisfy
      authority or review separation. Falsifier: Select an agent for an assignment requiring a
      named person because capabilities match; specialists/actor-predicate must detect the
      substitution.
    falsified_by: >
      Select an agent for an assignment requiring a named person because capabilities match;
      specialists/actor-predicate must detect the substitution.
  - id: AC2
    text: >
      Claim: Missing mandatory expertise produces a blocker or staffing request, never invented
      permissions or an automatic fallback. Set: Every configured required specialist role and
      empty, unavailable, expired or ineligible roster outcomes. Completeness: Compare role
      requirements to returned candidate/blocker rows in both directions. Remove the only eligible
      reviewer or technical specialist, run a manager cycle and observe one durable E owner
      request with no dispatch or held worker while waiting. Reassignment preserves expected
      artifact, deadline, budget and actor/authority predicates. Falsifier: Fall back to the
      implementation agent when no independent reviewer is eligible;
      specialists/no-review-fallback must detect self-review dispatch.
    falsified_by: >
      Fall back to the implementation agent when no independent reviewer is eligible;
      specialists/no-review-fallback must detect self-review dispatch.
  - id: AC3
    text: >
      Claim: Selection is a proposal; committed assignment and dispatch use current bounded
      reservations and versions. Set: control_specialist assignment acceptance and B
      reservation/receiver predicates after candidate selection. Completeness: Race roster
      revocation, owner reassignment and account/project/unit capacity exhaustion between proposal
      and commit. Require named stale/refused outcomes, no double reservation and no launch under
      the obsolete assignment. A permitted reassignment records a new version without increasing
      scope or admission priority. Falsifier: Skip roster-version revalidation when accepting a
      selected candidate; specialists/revoked-after-selection must detect a granted assignment.
    falsified_by: >
      Skip roster-version revalidation when accepting a selected candidate;
      specialists/revoked-after-selection must detect a granted assignment.
required_evidence: [unit, integration]
rollback: >
  Stop affected assignments, retain candidate and refusal evidence, and request eligible staffing
  through the enrolled owner surface.
---

## Intent

Choose qualified specialists for bounded assignments without inventing expertise, authority or review independence.

## Context

Package G, W75 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R17/R18, R30 and R62 require selection to preserve all assignment predicates. Incorrect selection can confer forbidden authority, requiring critical risk. Risk is critical; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

Recruiting real principals, silently changing engine policy and a fixed specialist roster are excluded.

## Notes

D1/D2 block atomic assignment/reservation publication; D3/D4 block actual qualified specialist launches. Dmitry must enroll any additional named specialist authority and decide staffing requests; a model may only propose a candidate. Keep tasks.capability checks as one predicate, not the whole admission test. Register control_specialist in fleet/engine with plain contracts and W30 distribution before ready. Proof must retain the no-candidate observation even when that means the assignment stays blocked.
