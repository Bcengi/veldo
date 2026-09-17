---
schema: veldo.spec/v1
id: VELDO-0076
title: Project ownership, charter, lifecycle, and transfers
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W61
plan_revision: 1
depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075]
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
  - "engine/.veldo/control_project*.py"
  - ".veldo/control_project*.py"
  - "packs/*/.veldo/control_project*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0076_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0076-project-ownership-charter-lifecycle.md"
  - "specs/index.md"
  - "proof/VELDO-0076/*"
behavior_bearing: true
observability:
  logs: >
    Project transitions name charter digest, owner, execution repository, authority binding,
    old/new versions and settlement receipt.
  metrics: >
    Count blocked activations, paused assignments, unreconciled terminal obligations and rejected
    ownership collisions.
  traces: >
    Join the enrolled charter or transfer presentation to one settlement, project transition and
    affected running-work stop receipts.
  error_taxonomy: >
    Distinguish unsigned charter, unresolved owner, absent authority policy, unbounded budget,
    terminal continuation and stale transfer.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Activation establishes one accountable project with a signed charter and bounded
      coordination authority. Set: Proposed control_project commands consuming
      request.validate_record and authorization.is_authorized for R04/R05 fields and DRAFT,
      ACTIVE, PAUSED, COMPLETED, CANCELED. Completeness: Compare the A field/state registry with
      command coverage. Omit each activation requirement in turn; sign current and stale charter
      presentations through each enrolled E surface. Race activation in real B transactions and
      require one version with an owner, one execution repository, authority policy and finite
      reservation. Falsifier: Skip the bounded coordination budget predicate;
      project/unbounded-activation must detect an ACTIVE project without a ceiling.
    falsified_by: >
      Skip the bounded coordination budget predicate; project/unbounded-activation must detect an
      ACTIVE project without a ceiling.
  - id: AC2
    text: >
      Claim: Pause and terminal transitions close future authorization while preserving effects
      and unresolved obligations. Set: Every project transition pair and frontier.claimable
      consumers, including running assignments, decisions, dispatches, release executions and
      reservations. Completeness: Generate the full state-pair matrix from A. Pause or cancel
      during real running work, restart after commit, and inspect stop-policy execution and no new
      dispatch. Complete only with terminal objectives and all listed obligations reconciled.
      Terminal continuation creates a linked project; landed history remains unchanged. Falsifier:
      Allow frontier.claimable to return a new assignment after project pause;
      project/pause-dispatch must detect fresh execution.
    falsified_by: >
      Allow frontier.claimable to return a new assignment after project pause;
      project/pause-dispatch must detect fresh execution.
  - id: AC3
    text: >
      Claim: Ownership transfer is an authorized versioned act and never conveys admission
      authority implicitly. Set: control_project transfer commands, project-to-repository
      ownership and unit ownership under R04. Completeness: Race transfers to two enrolled
      principals from one version, alter target-owner parameters beneath a retained signed CLI
      envelope, and try claiming the same unit for two projects. Require canonical command-digest
      verification, one winner and historical owner retention. The new owner without an admission
      delegation cannot admit work. Falsifier: Copy admission authority from the old owner to the
      new owner automatically; project/transfer-no-admission must reject the new owner admission
      attempt.
    falsified_by: >
      Copy admission authority from the old owner to the new owner automatically;
      project/transfer-no-admission must reject the new owner admission attempt.
required_evidence: [unit, integration]
rollback: >
  Pause affected projects, preserve ownership and effect history, and restore a compatible project
  reader before authorized resumption.
---

## Intent

Give continuing projects explicit ownership and lifecycle controls without conflating them with releases or plans.

## Context

Package F, W61 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R04/R05 and R61 govern project commands. The existing frontier selects specifications, so a new project predicate must reach its enrolled path. Ownership and pause defects can authorize unintended execution. Risk is critical; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

Release grouping, objective assessment and live enrollment policy are separate items.

## Notes

D1 blocks project storage and D2 its success acknowledgment; D3 blocks the running-work stop profile and D4 the inherited C clone path. Dmitry must rule on additional project owners and admission authorities under R37/R64 before those bindings can activate. Map control_project into contracts/engine and its scheduling consumer into fleet through A, and register its distribution via W30 before ready. Keep the state-pair matrix and transfer signature mutation with the failing proof row.
