---
schema: veldo.spec/v1
id: VELDO-0083
title: Bounded security emergency and incident containment admission
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W68
plan_revision: 1
depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0079, VELDO-0081]
placement: [contracts, engine, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/supervisor.py"
  - ".veldo/supervisor.py"
  - "packs/*/.veldo/supervisor.py"
  - "engine/.veldo/control_emergency*.py"
  - ".veldo/control_emergency*.py"
  - "packs/*/.veldo/control_emergency*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0083_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0083-security-emergency-incident-containment.md"
  - "specs/index.md"
  - "proof/VELDO-0083/*"
behavior_bearing: true
observability:
  logs: >
    Emergency records bind responder, incident, policy/target/action scope, priority, deadline,
    blast radius and owner-notification obligation.
  metrics: >
    Measure unratified exposure, deadlines, isolated patches, failed reversals and outstanding
    adversarial reviews.
  traces: >
    Trace enrolled break-glass authority through atomic incident admission, qualified effect,
    independent expiry and later ratification.
  error_taxonomy: >
    Distinguish ineligible emergency, unlisted target/action, missing enforcer, ratification
    overdue and forbidden permanent expansion.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Emergency and containment admission require their distinct signed authority and
      bounded action policy. Set: control_emergency and authorization.is_authorized for
      SECURITY_EMERGENCY and INCIDENT_CONTAINMENT under R08/R68. Completeness: Derive
      trigger/action matrices from accepted policy: active/imminent exploitation, credential
      compromise, severe privacy exposure or urgent security obligation, plus operations
      containment. Try every missing repository/target/action/duration/blast-radius/responder
      binding. Reject permanent features, public API changes, irreversible migrations, new
      dependencies and collection expansion; unqualified production targets remain unavailable.
      Falsifier: Treat INCIDENT_CONTAINMENT classification as sufficient operations authority;
      emergency/containment-policy must detect an unauthorized effect.
    falsified_by: >
      Treat INCIDENT_CONTAINMENT classification as sufficient operations authority;
      emergency/containment-policy must detect an unauthorized effect.
  - id: AC2
    text: >
      Claim: Before or atomically with an emergency effect, its complete admission and
      notification chain is durable. Set: control_emergency commands over backlog item, admission
      request, priority, incident, receipt and owner-notification obligation. Completeness: Crash
      real processes at each transaction/effect boundary and replay B history. Require all six
      records before dispatch, original effect identity on retry, and current enrolled
      presentation-bound policy or responder authority. Alter target/action under a retained CLI
      signature; canonical command-digest verification must refuse before an effect. Falsifier:
      Dispatch containment before inserting the owner-notification obligation;
      emergency/atomic-admission must detect an effect with an incomplete record chain.
    falsified_by: >
      Dispatch containment before inserting the owner-notification obligation;
      emergency/atomic-admission must detect an effect with an incomplete record chain.
  - id: AC3
    text: >
      Claim: Independent deadline enforcement bounds unratified effects even when the orchestrator
      is stopped. Set: Qualified reversible actions, four-hour ratification, one-business-day
      adversarial review/decision and R68 isolated-patch limits. Completeness: Run real
      action/enforcer processes with deterministic test time across deadlines and configured
      calendar boundaries, then suspend or kill coordination. Require expiry or rollback, no
      general distribution of an unratified patch, and authority stop if reversal/enforcement is
      unavailable. Enrolled security ratification settles the exact current incident; lateness
      never manufactures prior authority. Falsifier: Run the deadline timer only inside the
      stopped project manager; emergency/independent-expiry must detect an unexpired unratified
      effect.
    falsified_by: >
      Run the deadline timer only inside the stopped project manager; emergency/independent-expiry
      must detect an unexpired unratified effect.
required_evidence: [unit, integration]
rollback: >
  Close new emergency grants, preserve outstanding incidents, and let the independent enforcer
  expire or reverse each authorized effect.
---

## Intent

Permit only narrowly authorized emergency containment with durable admission and independently enforced expiry.

## Context

Package F, W68 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R61/R68 grant exceptional effects, so critical risk and prepare/execute policy apply. PLAN-0019 supplies no live production rollout target for a percentage canary. Risk is critical; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

Production deployment, permanent remediation without grooming and blanket break-glass privileges are excluded.

## Notes

D1/D2 block atomic emergency records and published dispatch; D3 blocks the independent deadline supervisor and D4 inherited worker clones. Dmitry must rule on security authority, operations authority, named responders, permitted reversible targets and the operations calendar under R37/R64/R68. Missing rulings or an unqualified deadline enforcer block emergency activation. Map control_emergency and its action-specific assets before ready and inventory them through W30. Proof must drive a real reversible test action with the manager stopped, retaining ratification timing and rollback receipts.
