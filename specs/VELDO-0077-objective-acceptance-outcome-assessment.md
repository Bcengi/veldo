---
schema: veldo.spec/v1
id: VELDO-0077
title: Objective acceptance and signed outcome assessment
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W62
plan_revision: 1
depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0076]
placement: [contracts, engine, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/control_objective*.py"
  - ".veldo/control_objective*.py"
  - "packs/*/.veldo/control_objective*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0077_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0077-objective-acceptance-outcome-assessment.md"
  - "specs/index.md"
  - "proof/VELDO-0077/*"
behavior_bearing: true
observability:
  logs: >
    Objective receipts identify accepted revision, beneficiary, scope, exclusions, acceptance
    principal and assessment evidence digests.
  metrics: >
    Measure objectives awaiting acceptance, unproven outcome obligations and stale assessment
    refusals.
  traces: >
    Trace proposed objective through enrolled acceptance to bounded elaboration and the exact
    signed satisfaction assessment.
  error_taxonomy: >
    Distinguish missing beneficiary, unauthorized acceptance, stale outcome revision, absent
    evidence and contribution-only completion.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Acceptance binds the exact objective outcome and permits only bounded elaboration.
      Set: control_objective commands using request.request_digest/validate_record and
      authorization.is_authorized for all R06 fields and seven objective states. Completeness:
      Require field and transition-pair coverage equal to A. Accept through each enrolled channel,
      change scope with an answer pending, and reject stale settlement. After valid acceptance
      propose a later feature and assert that neither admission nor priority nor an executable
      unit exists without its own request. Falsifier: Grant backlog admission when its parent
      objective is accepted; objective/later-feature must catch unauthorized engineering
      eligibility.
    falsified_by: >
      Grant backlog admission when its parent objective is accepted; objective/later-feature must
      catch unauthorized engineering eligibility.
  - id: AC2
    text: >
      Claim: Satisfaction requires a signed evidence assessment against the accepted objective
      revision. Set: SATISFIED entry for objectives supported by release executions, plans and
      standalone specification outcomes. Completeness: Enumerate all contribution kinds and
      accepted evidence requirements. Supply shipped specs with an unproven outcome, missing
      evidence, an ineligible signer, and a superseded objective; each refuses satisfaction. A
      current enrolled presentation and authorized signed assessment of every required outcome
      succeeds and replays once. Falsifier: Treat all contributed specifications shipped as
      sufficient for SATISFIED; objective/unproven-outcome must detect unsupported satisfaction.
    falsified_by: >
      Treat all contributed specifications shipped as sufficient for SATISFIED;
      objective/unproven-outcome must detect unsupported satisfaction.
  - id: AC3
    text: >
      Claim: Cancellation and contribution links preserve singular ownership and require explicit
      work disposition. Set: control_objective contribution/cancellation paths over one-project
      objectives and backlog-owned units. Completeness: Attempt duplicate objective ownership,
      cross-project contribution consumption and cancellation with active units. Require exactly
      one owning project, explicit artifact dependency for consumption, and an authorized
      disposition of owning backlog items before unit cancellation. Compare history before and
      after restart; rejected and canceled objectives cannot silently reopen. Falsifier: Cancel
      every contributing unit solely because an objective is canceled;
      objective/explicit-disposition must detect an unapproved stop.
    falsified_by: >
      Cancel every contributing unit solely because an objective is canceled;
      objective/explicit-disposition must detect an unapproved stop.
required_evidence: [unit, integration]
rollback: >
  Withdraw affected satisfaction permissions, append impact records and obtain a current
  assessment without rewriting prior receipts.
---

## Intent

Separate an accepted objective, authorized elaboration and demonstrated satisfaction of its promised outcome.

## Context

Package F, W62 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R06, R61 and R65 require outcome evidence beyond source delivery. An incorrect satisfaction or acceptance path grants authority or claims an unproven result. Risk is critical; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

Automatic feature admission and production deployment are excluded.

## Notes

D1/D2 block accepted objective records and replicated assessments; D3/D4 remain transitive C execution prerequisites. The named acceptance authority beyond Dmitry is a R37/R64 product ruling for Dmitry, not the project manager or a default owner role. Missing enrollment blocks acceptance and satisfaction by that principal. Assign control_objective to contracts/engine and inventory its copies before ready. Retain the later-feature refusal and exact assessment artifact bytes as independent proof observations.
