---
schema: veldo.spec/v1
id: VELDO-0086
title: Release-execution ownership and contribution binding
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W71
plan_revision: 1
depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0076, VELDO-0077]
placement: [contracts, engine, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/release_contract.py"
  - ".veldo/release_contract.py"
  - "packs/*/.veldo/release_contract.py"
  - "engine/.veldo/plan.py"
  - ".veldo/plan.py"
  - "packs/*/.veldo/plan.py"
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/control_release_execution*.py"
  - ".veldo/control_release_execution*.py"
  - "packs/*/.veldo/control_release_execution*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0086_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0086-release-execution-ownership-contributions.md"
  - "specs/index.md"
  - "proof/VELDO-0086/*"
behavior_bearing: true
observability:
  logs: >
    Release-execution receipts bind owning project, accepted release revision, recursive member
    digests, outcomes, regression and acceptance authority.
  metrics: >
    Count unresolved members, duplicate ownership, pending regression and canceled execution
    obligations.
  traces: >
    Trace objective contributions through the typed release forest and plans to exact accepted
    member outcomes.
  error_taxonomy: >
    Distinguish double ownership, missing member digest, stale release revision, absent regression
    receipt and rollout confusion.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Projects own release trees and plans once, while objectives reference contributions
      without acquiring ownership. Set:
      release_contract.record_problems/member_cycles/member_claims/release_problems and proposed
      control_release_execution ownership commands. Completeness: Enumerate release/plan member
      kinds and cross-project contribution cases. Exercise nested releases terminating at plans,
      cycles, duplicate parents and owners, multiple trees owned by one project and standalone
      plans. Preserve veldo.release/v1 and legacy identifiers; membership implies no execution
      order and another project consumes only accepted artifact dependencies. Falsifier: Grant a
      contributing objective project ownership of an already owned plan;
      release-binding/single-owner must detect duplicate ownership.
    falsified_by: >
      Grant a contributing objective project ownership of an already owned plan;
      release-binding/single-owner must detect duplicate ownership.
  - id: AC2
    text: >
      Claim: Release execution acceptance binds recursively resolved revisions and actual
      outcome/regression evidence. Set: control_release_execution for PLANNED, ACTIVE, BLOCKED,
      ACCEPTED, CANCELED, FAILED; release_contract.member_digest/release_report and
      plan.cmd_release_check/cmd_regression. Completeness: Generate all state-pair tests from A.
      Persist accepted release revision, recursive member digests, required outcomes, regression
      obligations and authority. Change a member after snapshot, omit a required outcome or
      observed journey receipt, and set declaration status released; refuse acceptance. A current
      enrolled acceptance decision and complete exact-revision evidence is the positive control.
      Falsifier: Accept a release execution because plan.cmd_release_check sees journey
      declarations without execution receipts; release-binding/observed-regression must detect
      unsupported acceptance.
    falsified_by: >
      Accept a release execution because plan.cmd_release_check sees journey declarations without
      execution receipts; release-binding/observed-regression must detect unsupported acceptance.
  - id: AC3
    text: >
      Claim: Cancellation stops uncompleted authorized release work without claiming success or
      activating rollout. Set: Project/release-execution cancellation and objective contribution
      disposition under R65. Completeness: Cancel at each nonterminal state with running and
      completed members. Require project cancellation to subsume its release stop, preserve landed
      receipts and explicit backlog disposition for objective cancellation. Observe zero
      deployment calls when accepting a release artifact; .veldo/release.py remains separately
      authorized. Falsifier: Call rollout machinery on ACCEPTED release execution;
      release-binding/no-implicit-rollout must detect the deployment invocation.
    falsified_by: >
      Call rollout machinery on ACCEPTED release execution; release-binding/no-implicit-rollout
      must detect the deployment invocation.
required_evidence: [unit, integration]
rollback: >
  Block affected release executions, preserve accepted revisions and receipts, and seek a current
  authority disposition for unfinished work.
---

## Intent

Bind project accountability to release execution without changing the existing release membership hierarchy.

## Context

Package F, W71 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R05/R06, R61 and R65 distinguish ownership, contribution, release declaration and execution acceptance. Acceptance controls critical completion authority. Risk is critical; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

Production rollout implementation and replacement of veldo.release/v1 are excluded.

## Notes

D1/D2 block release-execution state and acceptance replication; D3/D4 remain inherited for cancellation of running units. Dmitry must name release acceptance authorities beyond himself. The current release_report computes member digests but permits unelaborated targets; enrolled execution must block missing members. Map control_release_execution into contracts/engine/fleet and inventory it before ready. Use real installed release_contract and plan consumers in evidence, keeping release membership and execution dependency matrices separate.
