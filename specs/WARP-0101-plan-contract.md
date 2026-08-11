---
schema: veldo.spec/v1
id: WARP-0101
title: Product Plan contract, validator, and plan index (W1 of PLAN-0001)
status: shipped
risk: standard
owner: dmitry
plan: PLAN-0001
work: W1
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: python3 .veldo/validate.py all validates plans/ against veldo.plan/v1 and
      exits 0 with PLAN-0001 and the plan example both valid.
  - id: AC2
    text: The validator rejects each planted-bad plan shape - dependency cycle,
      dangling depends_on, unknown outcome/feature ref, undeclared depends_on,
      ready without recorded approval, open decision without an explicit blocks
      list, decision blocking an unknown spec, duplicate work specs, bad release
      mode - and rejects broken spec-plan mirroring in both directions
      (selftest, all red paths exercised).
  - id: AC3
    text: specs/index.md carries a generated Product Plans section - per-item
      state derived from spec files, ready frontier computed from shipped
      dependencies, decision-blocked items named - and the generated check keeps
      it derived.
  - id: AC4
    text: This specification itself binds to PLAN-0001 work W1 and the two-way
      mirroring passes in the gate; mis-declaring the binding turns the gate red
      (negative demonstration).
  - id: AC5
    text: capabilities.yaml (template and instance) lists plan_contract_validation
      and plan_index as mechanical, names the still-absent plan capabilities
      (dialogue W2, run integration W3, regression mechanics W4), and the plugin
      version is 2.1.0.
required_evidence: [unit, operational]
rollback: git revert; the plan contract is additive to the validator and index
  generator, and no existing contract behavior changed (26-test selftest green).
---

## Intent

The layer above specs becomes mechanical: a product iteration is a
repository-native Product Plan (holistic intent, outcomes, feature tree,
ordered work DAG, planned regression, release definition), and the validator
makes its promises real - references resolve, the DAG is acyclic,
dependencies are declared decisions, approval is recorded the moment a plan
leaves draft, open decisions name exactly what they block, and every spec
pulled from a plan binds back to it two-way. The index renders the burn-down
from the same truth, so plan status is generated, never reported.

## Context

W1 of PLAN-0001 (VELDO 1.0), pulled from the ready frontier. The contract
follows the reconciled design (docs/design/05 + in-session): flat plans/,
validator-style enforcement, no schema stack, one parser with one home
(validate.py) that update_index.py imports. The front-matter subset is
parsed by a deliberately dependency-free parser so behavior is identical on
every machine; anything outside the subset fails closed with a line hint.

## Out of scope

The /veldo:plan dialogue skill (W2), run-time dependency refusal and the plan
context bundle (W3), regression activation wiring into gate slots (W4). Doc
integration lands with W11 after the mechanics it describes exist.
