---
schema: veldo.spec/v1
id: VELDO-0080
title: Section 2 work-class dispatch and trusted defect reproduction
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W65
plan_revision: 1
depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0079]
placement: [contracts, engine, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/frontier.py"
  - ".veldo/frontier.py"
  - "packs/*/.veldo/frontier.py"
  - "engine/.veldo/control_admission*.py"
  - ".veldo/control_admission*.py"
  - "packs/*/.veldo/control_admission*.py"
  - "engine/.veldo/control_defect*.py"
  - ".veldo/control_defect*.py"
  - "packs/*/.veldo/control_defect*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0080_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0080-work-class-dispatch-defect-reproduction.md"
  - "specs/index.md"
  - "proof/VELDO-0080/*"
behavior_bearing: true
observability:
  logs: >
    Admission evaluations identify work class, accepted behavior revision, failing criterion,
    reproduction receipt, policy signer/digest and priority source.
  metrics: >
    Count class-specific refusals, failed reproductions by cause, policy admissions and
    severity-preserving grooming returns.
  traces: >
    Trace quarantined input to trusted reproduction, exact policy evaluation and separately
    authorized priority.
  error_taxonomy: >
    Distinguish unknown class, changed contract, untrusted reproduction, unsupported version,
    cross-repository defect and expired policy.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The dispatcher requires exactly one of seven classes and its complete authority
      policy. Set: control_admission dispatch using request.validate_record and
      authorization.is_authorized for PRODUCT_CHANGE, POLICY_DEFECT, SECURITY_EMERGENCY,
      INCIDENT_CONTAINMENT, STANDING_MAINTENANCE, TECHNICAL_CHANGE and COMPLIANCE_EXPIRY.
      Completeness: Require equality of R08/A classes and registered handlers, with unknown and
      multiple-class refusals. Exercise each handler with every required predicate removed and a
      valid control. Product/technical and non-standing compliance work require deliberate shaping
      and priority; absent compliance obligation or qualified target blocks. W67/W68 supply
      standing/emergency handlers before activation. Falsifier: Route TECHNICAL_CHANGE through
      automatic defect admission solely from its label; classes/technical-authority must detect
      unauthorized admission.
    falsified_by: >
      Route TECHNICAL_CHANGE through automatic defect admission solely from its label;
      classes/technical-authority must detect unauthorized admission.
  - id: AC2
    text: >
      Claim: Only clean trusted reproduction of accepted behavior can originate discretionary
      automatic engineering admission. Set: control_defect reproduction and control_admission
      evaluation over every R66 predicate. Completeness: Execute quarantined reproductions and
      compare baseline, environment digest, steps, expected/actual observations and artifacts to
      accepted revision, failing criterion, supported version, bounded surface and envelope. Test
      duplicate, obsolete, destructive, production-data-dependent, expected-behavior and
      cross-repository cases; none auto-admits. An agent assertion cannot replace an Evidence
      Service observation. Falsifier: Accept a model reproduction assertion without a trusted
      observation receipt; defects/trusted-reproduction must detect automatic admission.
    falsified_by: >
      Accept a model reproduction assertion without a trusted observation receipt;
      defects/trusted-reproduction must detect automatic admission.
  - id: AC3
    text: >
      Claim: Failed reproduction or scope-changing restoration routes to grooming or bounded
      security handling without lowering severity. Set: R66 contract/criterion, public
      behavior/interface, data model, dependency policy, protected scope, release policy and
      compatibility changes. Completeness: Maintain clause-to-fixture equality and change each
      dimension separately. Preserve severity and source receipts while reclassifying into an
      applicable class and AWAITING_GROOMING, or seeking W68 authority. Valid policy admission
      records identity, digest, signer, version, inputs, result and expiry and confers no queue
      precedence without signed priority policy. Falsifier: Lower severity on an unreproduced
      security defect before grooming; defects/severity-preserved must detect the downgrade.
    falsified_by: >
      Lower severity on an unreproduced security defect before grooming;
      defects/severity-preserved must detect the downgrade.
required_evidence: [unit, integration]
rollback: >
  Disable automatic defect admission, retain severity and reproduction evidence, and route
  affected proposals to current authorized grooming.
---

## Intent

Dispatch all seven classes under their own admission rules and constrain automatic defects to observed restoration of accepted behavior.

## Context

Package F, W65 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R08, R61 and R66 prohibit relabeling desired functionality as a defect. Policy evaluation can grant execution, requiring critical risk. Risk is critical; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

Scanner installation and standing or emergency policy implementation remain W66-W68 concerns.

## Notes

D1/D2 block stored policy evaluations and acknowledgment; D3 blocks trusted reproduction containment and D4 its accepted-source clone path. Dmitry must enroll the Admission Service policy identity and any additional admission, priority, security or operations authority. Failed scanner qualification is an explicit reproduction blocker. The plan orders this before W66 without depending on it: bounded local fixtures can develop dispatch, but automatic runtime admission must stay disabled until W66 qualification. Map and inventory control_admission/control_defect before ready; preserve R66 predicate coverage and actual negative-control diffs.
