---
schema: veldo.spec/v1
id: VELDO-0089
title: Versioned team configuration
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W74
plan_revision: 1
depends_on: [VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0088]
placement: [contracts, engine, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/decision_review.py"
  - ".veldo/decision_review.py"
  - "packs/*/.veldo/decision_review.py"
  - "engine/.veldo/control_team*.py"
  - ".veldo/control_team*.py"
  - "packs/*/.veldo/control_team*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0089_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0089-versioned-team-configuration.md"
  - "specs/index.md"
  - "proof/VELDO-0089/*"
behavior_bearing: true
observability:
  logs: >
    Team configuration receipts identify project, revision, approving authority, manager role and
    each role capability/budget/independence digest.
  metrics: >
    Count missing mandatory roles, stale team revisions, refused permission growth and staffing
    requests.
  traces: >
    Trace a presented team amendment through enrolled approval to the roster version read by each
    cycle and assignment.
  error_taxonomy: >
    Distinguish missing manager, malformed role, unauthorized roster edit, stale assignment
    predicates and review-policy conflict.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A versioned team configuration declares one project-manager role and every role
      required by the project work. Set: control_team validation with request.validate_record for
      responsibilities, allowed proposals, capabilities, engine eligibility, context restrictions,
      budgets and independence under R17. Completeness: Compare required field and role coverage
      to the accepted team schema and project requirements, including elaboration, implementation
      and independent review. Test missing/multiple manager definitions, omitted expertise and
      malformed bounds; generate a durable owner staffing request instead of inventing a role or
      substituting an ineligible worker. Falsifier: Accept a team configuration without
      independent review capability required by its work; team/missing-review-role must detect an
      executable incomplete roster.
    falsified_by: >
      Accept a team configuration without independent review capability required by its work;
      team/missing-review-role must detect an executable incomplete roster.
  - id: AC2
    text: >
      Claim: Team amendments require current scoped authority and cannot promote roster membership
      into admission rights. Set: control_team amendment transactions and
      authorization.is_authorized across all enrolled E decision surfaces. Completeness: Race two
      accepted amendments from one revision, change role permissions beneath a signed CLI
      envelope, and submit a manager-authored self-promotion. Require full canonical
      command-digest checks, one version winner and current E presentation/quorum. An approved
      role entry still requires separately enrolled admission or named-authority predicates.
      Falsifier: Grant admission authority to every member of an approved manager role;
      team/roster-not-authority must detect an unauthorized grooming decision.
    falsified_by: >
      Grant admission authority to every member of an approved manager role;
      team/roster-not-authority must detect an unauthorized grooming decision.
  - id: AC3
    text: >
      Claim: Assignment creation and reassignment preserve team restrictions and the repository
      independent-review policy. Set: control_team consumers of E assignment predicates and
      decision_review.required_reviews_for/bind_review. Completeness: Derive role-to-station
      coverage, then remove a capability, shrink a budget, change engine eligibility or
      independence during a cycle. Require complete read-set refusal for stale assignments,
      explicit new version on reassignment and unchanged actor-kind/named-authority predicates.
      Exercise every effective review tier without allowing a team amendment to lower repository
      policy. Falsifier: Use the cycle cached roster after its independent-review restriction
      changes; team/stale-roster must detect acceptance of an obsolete assignment.
    falsified_by: >
      Use the cycle cached roster after its independent-review restriction changes;
      team/stale-roster must detect acceptance of an obsolete assignment.
required_evidence: [unit, integration]
rollback: >
  Suspend assignments affected by the team revision, preserve prior configurations, and accept a
  current authorized replacement without widening permissions.
---

## Intent

Make project teams configurable and versioned while keeping role definitions separate from authority grants.

## Context

Package G, W74 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R17/R18, R30 and R62 replace a fixed roster with bounded role requirements. Team configuration can weaken separation of duties unless the authority boundary is enforced. Risk is critical; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

A fixed roster of people, new real enrollment and changes to repository review/model-selection policy are excluded.

## Notes

D1/D2 block durable configuration and published amendments; D3/D4 remain inherited worker prerequisites. Dmitry must rule on additional named authorities and who may approve project team amendments under R37/R64. Missing policy or expertise blocks the assignment. Map control_team into contracts/engine with loop consumers and inventory it before ready. Exercise existing decision_review consumers after E repairs; do not preserve their baseline permissive fallback as an enrolled policy. Save the effective policy and team revisions beside stale-roster proof.
