---
schema: veldo.spec/v1
id: VELDO-0091
title: Budgeted requirements elaboration
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W76
plan_revision: 1
depends_on: [VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0088, VELDO-0090]
placement: [contracts, loop, metrics, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/tasks.py"
  - ".veldo/tasks.py"
  - "packs/*/.veldo/tasks.py"
  - "engine/.veldo/control_elaboration*.py"
  - ".veldo/control_elaboration*.py"
  - "packs/*/.veldo/control_elaboration*.py"
  - "engine/.veldo/control_reservation*.py"
  - ".veldo/control_reservation*.py"
  - "packs/*/.veldo/control_reservation*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0091_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0091-budgeted-requirements-elaboration.md"
  - "specs/index.md"
  - "proof/VELDO-0091/*"
behavior_bearing: true
observability:
  logs: >
    Elaboration receipts identify accepted objective revision, governing contract, source mapping,
    assumptions/questions and request-level reserved exposure.
  metrics: >
    Measure cycles, tokens, elapsed time, unchanged proposals, settled charges and unresolved
    maximum-charge allocations.
  traces: >
    Join bounded elaboration assignment through each billable request to versioned requirements
    artifacts and open decision obligations.
  error_taxonomy: >
    Distinguish scope question unresolved, cycle/token/time limit, repeated unchanged proposal,
    unknown charge bound and signed-ceiling exhaustion.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Elaboration publishes versioned requirements, assumptions, alternatives, proposed
      specs, dependencies and questions without admission authority. Set: control_elaboration
      outputs using request.validate_record and W70 decomposition publication for accepted
      objectives and governing coordination specs. Completeness: Compare output roles to R19 and
      allocation mappings. Run concurrent authors and duplicate retries; require
      source-revision/role identity reuse and distinct artifacts for distinct sources. Scope or
      acceptance questions create enrolled decision requests and block the applicable
      admission/execution boundary; a prepared spec cannot authorize itself. Falsifier: Mark a
      generated feature admitted when its objective was accepted; elaboration/no-feature-admission
      must detect unauthorized backlog progress.
    falsified_by: >
      Mark a generated feature admitted when its objective was accepted;
      elaboration/no-feature-admission must detect unauthorized backlog progress.
  - id: AC2
    text: >
      Claim: Finite cycle, token, elapsed-time and unchanged-proposal limits bound self-triggered
      elaboration. Set: Every control_elaboration continuation, retry, no-action and failure
      result under the governing budget contract. Completeness: Derive limits from the accepted
      policy and test below/at/above each independently using real adapter processes and trusted
      accounting. Repeated unchanged proposals reach a named stop and E escalation; each cycle
      retains its receipt. Waiting on an answer holds no model or claim, and deleting checkpoints
      cannot reset the durable limit counters. Falsifier: Reset unchanged-proposal count on
      checkpoint deletion; elaboration/repetition-bound must detect extra unauthorized cycles.
    falsified_by: >
      Reset unchanged-proposal count on checkpoint deletion; elaboration/repetition-bound must
      detect extra unauthorized cycles.
  - id: AC3
    text: >
      Claim: Every billable request allocates an enforceable maximum charge before calling the
      provider. Set: B control_reservation consumed by elaboration trusted adapters, across
      initial, retry and follow-on requests and account/project/unit ceilings. Completeness: Use D
      qualified price/request-limit profiles; race real allocations at remaining ceilings after
      settled charges and outstanding exposure. Test unknown maximum, above-bound request,
      timeout, cancellation and delayed usage. No refused call reaches the provider; exposure
      persists until reconciled usage or authoritative no-charge evidence. Exhaustion produces a
      stop rather than a larger model budget. Falsifier: Release outstanding request exposure on
      timeout; elaboration/timeout-exposure must detect a second call spending the same remainder.
    falsified_by: >
      Release outstanding request exposure on timeout; elaboration/timeout-exposure must detect a
      second call spending the same remainder.
required_evidence: [unit, integration]
rollback: >
  Stop further elaboration calls, retain unresolved exposure and question requests, and resume
  only under a current bounded contract.
---

## Intent

Bound requirements preparation and its provider costs while keeping unresolved decisions and admission authority explicit.

## Context

Package G, W76 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R19, R45 as reviewed and R62 require durable limits at every reasoning and billable-request boundary. Overspend and implicit admission make this concern critical. Risk is critical; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

New provider pricing models, discretionary budget expansion and automatic question settlement are excluded.

## Notes

D1/D2 block durable elaboration and charge allocation; D3/D4 block production adapter containment and clones. Dmitry must ratify the coordination budget and designate authorities for unresolved scope/acceptance questions. D qualification supplies exact enforceable request limits; unknown cost is a blocker, not an estimate treated as permission. Confirm the B reservation module footprint before ready, map control_elaboration under loop/contracts/metrics and inventory it through W30. Preserve provider-call counts and maximum exposure before and after each timeout.
