---
schema: veldo.spec/v1
id: VELDO-0080
title: Ordinary defect dispatch through normal admission
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W65
plan_revision: 3
depends_on: [VELDO-0079, VELDO-0126]
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
      Claim: An ordinary "fix this bug" message enters the normal shaping, specification,
      owner admission and priority path in Release 1. Set and completeness: Submit a defect
      through Telegram and authenticated API intake, retain its source and severity, and inspect
      the proposed POLICY_DEFECT item, shaped specification and exact owner decision binding.
      The label alone grants no execution. Falsifier: Admit a defect from its label without
      the owner decision; defects/ordinary-admission must fail.
    falsified_by: >
      Admit a defect from its label without the owner decision; defects/ordinary-admission
      must fail.
  - id: AC2
    text: >
      Claim: An admitted and prioritized ordinary defect uses the normal build, proof, gate,
      independent review and exact-tree landing path. Set and completeness: Drive a real
      admitted bug-fix unit through those stages and inspect the completion receipt; withhold
      admission, priority, passing gate or independent review separately and require refusal.
      Falsifier: Complete a bug fix with its independent review missing;
      defects/ordinary-completion must fail.
    falsified_by: >
      Complete a bug fix with its independent review missing; defects/ordinary-completion
      must fail.
  - id: AC3
    text: >
      Claim: Ordinary defect handling does not activate automatic reproduction-based admission
      or standing/emergency policies. Set and completeness: Submit an agent reproduction claim,
      a standing occurrence and a security emergency without their governing authority;
      require no automatic executable unit. An ordinary defect may proceed after normal
      shaping, owner admission and priority without a trusted automatic reproduction service.
      Preserve severity and return scope-changing restoration to grooming.
      Falsifier: Treat a model reproduction claim as automatic admission;
      defects/no-automatic-admission must fail.
    falsified_by: >
      Treat a model reproduction claim as automatic admission; defects/no-automatic-admission
      must fail.
required_evidence: [unit, integration]
rollback: >
  Disable automatic defect admission, retain severity and reproduction evidence, and route
  affected proposals to current authorized grooming.
---

## Intent

Take an ordinary bug-fix request from message to spec, build, review and land through the
same deliberate admission path as other ordinary work.

## Context

W65 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4.
R08 permits POLICY_DEFECT admission by the admission authority; trusted automatic reproduction
is a separate later path. Normal owner admission and priority remain mandatory.
Risk, approval requirements and draft status are unchanged.

## Out of scope

Trusted automatic defect reproduction and admission, the full seven-class policy dispatch
matrix, quarantine qualification, standing maintenance (VELDO-0082) and security emergency
admission (VELDO-0083) remain Release 3. Their deferral cannot block ordinary admitted bug fixes.

## Notes

Use VELDO-0126's common Telegram/API intake and VELDO-0079's ordinary grooming/admission path.
VELDO-0078 supplies priority-controlled execution and VELDO-0052 the ordinary engineering floor.
A defect label, reproduction assertion or severity never bypasses owner admission or review.

## History

2026-09-22: the owner requires ordinary defect work in Release 1. Dependencies now name its
actual intake and grooming consumers. The former criteria below remain Release 3 obligations;
they are not Release 1 prerequisites and have not been implemented or qualified by this edit.
No status or existing proof changed.

### Deferred Release 3 contract

The full class matrix still requires each class's authority predicates, W67/W68 handlers before
activation, and qualified quarantine before automatic runtime admission. D1-D4 recovery and
containment follow-ups retain their plan release assignments. The Admission Service policy
identity and any additional authority must be enrolled before automatic admission is enabled.

```yaml
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The dispatcher requires exactly one of seven classes and its complete authority
      policy. Set: control_admission dispatch using request.validate_record and
      authorization.is_authorized for PRODUCT_CHANGE, POLICY_DEFECT, SECURITY_EMERGENCY,
      INCIDENT_CONTAINMENT, STANDING_MAINTENANCE, TECHNICAL_CHANGE and COMPLIANCE_EXPIRY.
      Completeness: Require equality of R08/A classes and registered handlers, with unknown and
      multiple-class input held in quarantine. Exercise each handler with every required predicate
      removed and a valid control. Product/technical and non-standing compliance work require
      deliberate shaping and priority; absent compliance obligation or qualified target blocks.
      W67/W68 supply standing/emergency handlers before activation. Falsifier: Route
      TECHNICAL_CHANGE through automatic defect admission solely from its label;
      classes/technical-authority must detect unauthorized admission.
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
```
