---
schema: veldo.spec/v1
id: VELDO-0018
title: Release and behavior-floor integration contracts
status: draft
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
  - "scripts/suites/*"
  - "packs/**/.veldo/*contract*.py"
  - "specs/VELDO-0018-release-floor-contracts.md"
  - "specs/index.md"
  - "proof/VELDO-0018/*"
behavior_bearing: true
observability:
  logs: Contract refusals name the predicate, subject revision, and offending reference without including private keys or credentials.
  metrics: Proof reports required and exercised schema, transition, or boundary sets and coverage gaps; an unknown result never counts as zero failures.
  traces: Evidence joins the criterion, fixture or observation, input digests, and exact contract revision; runtime receipt production belongs to later packages.
  error_taxonomy: Distinguish missing input, malformed input, stale revision, unauthorized actor, forbidden transition, and unavailable evidence with named refusals.
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

**Proof discipline.** This is one contract concern, with four criteria. The named check rows above are implementation obligations, not claims that those checks exist today. Proof must show its tested set equals the declared schema or policy universe and must drive each stated mutation, demonstrate the changed bytes, require the named row to fail, and restore the implementation. Removing a failure fixture cannot reduce the declared universe.

**Implementation boundary.** Define pure versioned data and named transition refusals in canonical engine/, synchronize shipped counterparts, and record every new asset in the distribution inventory. The draft footprint lists existing integration points and contract/test additions; refine it to exact new modules and synchronized counterparts before ready. Do not build the B-H runtime under this spec. Future runtime observations and receipts are required by their own specifications.
