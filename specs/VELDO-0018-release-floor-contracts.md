---
schema: veldo.spec/v1
id: VELDO-0018
title: Release and behavior-floor integration contracts
status: shipped
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W3
plan_revision: 1
depends_on: [VELDO-0017]
placement: [contracts]
protected_paths: []
footprint:
  - ".veldo/release_contract.py"
  - "engine/.veldo/release_contract.py"
  - ".veldo/plan.py"
  - "engine/.veldo/plan.py"
  - ".veldo/validate_checks.py"
  - "engine/.veldo/validate_checks.py"
  - "engine/.veldo/*contract*.py"
  - ".veldo/*contract*.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - "scripts/suites/*"
  - "packs/**/.veldo/*contract*.py"
  - "specs/VELDO-0018-release-floor-contracts.md"
  - "specs/index.md"
  - "proof/VELDO-0018/*"
behavior_bearing: true
observability:
  logs: These pure release and floor predicates emit no runtime logs; refusal results name the member revision, journey, floor pin, or cancellation relation that blocks acceptance.
  metrics: Proof reports required versus evidenced release members and journeys, plus affected floor pins with missing or unresolved settlements; runtime counters are outside this contract.
  traces: Acceptance evidence joins the release snapshot and recursive member digests to regression receipts, floor revisions, affected pins, settlement subjects, and acceptance authority.
  error_taxonomy: Distinguish invalid membership, duplicate project owner, missing or stale regression receipt, wrong candidate/environment, unresolved floor pin, stale settlement, and unauthorized rollout.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The existing release membership forest remains typed and projects have unique ownership
      without duplicating it through objective contributions. Set: Release-to-release and release-to-
      plan membership, standalone plans, project ownership, and objective contribution links.
      Completeness: Enumerate relation types from veldo.release/v1 and the new ownership schema; test
      all permitted endpoints, forbidden endpoints, cycles, duplicate parents, multiple project
      owners, and non-owning contributions. Falsifier: Treat an objective contribution as a second
      project owner; the release-ownership/contribution row must fail.
    falsified_by: >
      Treat an objective contribution as a second project owner; the release-ownership/contribution
      row must fail.
  - id: AC2
    text: >
      Claim: Release execution accepts exact accepted member revisions only after all required
      outcomes and observed regression receipts are present. Set: Every recursively resolved required
      member and declared journey of a release execution, across PLANNED, ACTIVE, BLOCKED, ACCEPTED,
      CANCELED, and FAILED. Completeness: Derive the member and journey universe from the accepted
      release snapshot; require set equality with receipt coverage and test deletion, staleness,
      duplication, wrong candidate/environment, and a released status string without receipts.
      Falsifier: Accept a journey declaration without an execution receipt; the release-
      acceptance/missing-regression row must fail.
    falsified_by: >
      Accept a journey declaration without an execution receipt; the release-acceptance/missing-
      regression row must fail.
  - id: AC3
    text: >
      Claim: Applicable behavior floors and affected pins block on missing revisions or unresolved
      dispositions until the designated authority settles the exact version. Set: All applicable floor
      revisions and affected pins named by an execution snapshot, including changed observations and
      changed settlement subjects. Completeness: Join the floor registry and affected scope to derive
      the required pin set, assert no unexamined member, and exercise missing floors, stale pins,
      wrong authority, expanded scope, and correctly bound settlements. Falsifier: Accept a settlement
      for an earlier floor digest; the floor-eligibility/stale-settlement row must fail.
    falsified_by: >
      Accept a settlement for an earlier floor digest; the floor-eligibility/stale-settlement row must
      fail.
  - id: AC4
    text: >
      Claim: Cancellation follows ownership disposition and release acceptance never activates
      deployment. Set: Project, objective, backlog, and release-execution cancellation relationships
      plus the separate release.py rollout boundary. Completeness: Enumerate cancellation relation
      types from the ownership schema; prove project cancellation stops unfinished owned release work,
      objective cancellation requires explicit backlog disposition, and every release-acceptance path
      leaves deployment unauthorized. Falsifier: Invoke rollout authorization on release-artifact
      acceptance; the release-boundary/no-deployment row must fail.
    falsified_by: >
      Invoke rollout authorization on release-artifact acceptance; the release-boundary/no-deployment
      row must fail.
required_evidence: [unit, integration]
rollback: >
  Retain the prior accepted contract and compatible reader. Refuse new project-layer activation
  until corrected contracts are accepted; preserve accepted history and refuse implicit schema
  downgrade. Revert only unactivated contract changes through the ordinary reviewed path.
---

## Intent

**Outcome.** Keep projects, release executions, plans, and behavior floors distinct while making their accepted evidence part of eligibility.

## Context

**Authority.** Package A of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R14, R52, R56, R65, R70, and R76. The later decision-surface ruling in its provenance header takes precedence over retained tracker-only wording.

**Risk.** Release and baseline predicates protect accepted behavior and can otherwise admit unreviewed changes, so the declared floor is high. No approval is asserted by human_approval: required; this draft must obtain its applicable approval and independent review before implementation or activation.

## Out of scope

**Boundary.** Actual release-regression consumption in floor execution belongs to C; runtime release-execution operations belong to F. No deployment adapter, floor settlement, or release activation is authored here.

## Notes

Use the accepted release snapshot to derive member and journey coverage, and the applicable floor registry to derive affected pins. Fixture receipts exercise acceptance predicates; they do not certify a real regression run or settle a floor. Keep release.py rollout authorization outside every release-artifact acceptance path.
