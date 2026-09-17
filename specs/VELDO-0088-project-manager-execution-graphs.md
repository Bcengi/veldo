---
schema: veldo.spec/v1
id: VELDO-0088
title: Project-manager execution graphs
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W73
plan_revision: 1
depends_on: [VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087]
placement: [contracts, loop, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/tasks.py"
  - ".veldo/tasks.py"
  - "packs/*/.veldo/tasks.py"
  - "engine/.veldo/frontier.py"
  - ".veldo/frontier.py"
  - "packs/*/.veldo/frontier.py"
  - "engine/.veldo/control_graph*.py"
  - ".veldo/control_graph*.py"
  - "packs/*/.veldo/control_graph*.py"
  - "engine/.veldo/control_project_cycle*.py"
  - ".veldo/control_project_cycle*.py"
  - "packs/*/.veldo/control_project_cycle*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0088_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0088-project-manager-execution-graphs.md"
  - "specs/index.md"
  - "proof/VELDO-0088/*"
behavior_bearing: true
observability:
  logs: >
    Cycle receipts identify project/version, journal and published watermarks, coordination
    contract, complete snapshot digest, reservation and graph result.
  metrics: >
    Count cycles returning proposals, no action, suspension, cancellation or failure, with elapsed
    time and reconciled usage.
  traces: >
    Join authoritative cycle inputs and supplied command results through graph advancement to
    typed proposals and Veldo commit results.
  error_taxonomy: >
    Distinguish missing coordination contract, unavailable adapter, stale input, invalid proposal,
    exhausted cycle budget and unsupported graph progress.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The project manager reconciles an immutable authorized snapshot and returns proposals
      under a bounded coordination contract. Set: Proposed control_project_cycle graph execution
      using B control_graph start/advance/suspend/cancel/result interface and
      request.validate_record. Completeness: Enumerate all adapter operations and cycle input
      fields from R29/R34/R70. Run actual installed LangGraph with fixed model outputs, bind
      project version, journal/published watermark, accepted source commit, complete input
      versions/digests and reservation. Drive proposal, no-action and failure cycles; each
      consumes its own operation unit and produces an evidence receipt without claiming source
      landing. Falsifier: Omit a receipt when the graph returns no action;
      manager/no-action-receipt must detect the unaccounted cycle.
    falsified_by: >
      Omit a receipt when the graph returns no action; manager/no-action-receipt must detect the
      unaccounted cycle.
  - id: AC2
    text: >
      Claim: Graph execution cannot admit, prioritize, assign, dispatch, sign observations or
      complete work directly. Set: Every graph node and adapter output reaching F services,
      frontier.claimable and tasks.claim_task through Veldo commands. Completeness: Compare
      node/output registrations with the typed proposal registry and inspect real
      process/file/authority effects. Submit shell text, SQL, invented roles, completion
      assertions and a node that tries store access. Require named refusal and no domain change
      except independently validated Veldo commands; waiting for a person releases worker/claim
      resources while retaining the assignment. Falsifier: Allow a graph node to set backlog
      priority directly; manager/no-direct-priority must detect a transition lacking an authorized
      Veldo command.
    falsified_by: >
      Allow a graph node to set backlog priority directly; manager/no-direct-priority must detect
      a transition lacking an authorized Veldo command.
  - id: AC3
    text: >
      Claim: The same supplied results and authorized proposals have identical domain meaning
      under a deterministic replacement adapter. Set: LangGraph and the B deterministic adapter,
      across all allowed proposal/result and graph terminal forms. Completeness: Run both on
      cloned verified authority fixtures with identical cycle identities, inputs and logical
      proposals. Compare canonical accepted/refused transitions and effect identities, excluding
      only execution telemetry by explicit schema fields. Repeat advancement and cancel the cycle
      holder; committed command results replay without fresh identities or repeated effects.
      Falsifier: Allocate a new logical action ID when a LangGraph node retries;
      manager/retry-identity must detect a second committed transition.
    falsified_by: >
      Allocate a new logical action ID when a LangGraph node retries; manager/retry-identity must
      detect a second committed transition.
required_evidence: [unit, integration]
rollback: >
  Stop starting project-manager cycles, fence outstanding proposals, and retain command results
  for deterministic reconciliation.
---

## Intent

Run the project manager as a bounded reconciler over Veldo state with a replaceable graph implementation.

## Context

Package G, W73 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R19, R29/R30, R34 and R62 place reasoning outside authority. B supplies the adapter boundary; this item supplies project coordination graphs. Bypassing F authorization warrants critical risk. Risk is critical; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

New storage, a LangGraph server, direct model shell execution and replacement of deterministic services are excluded.

## Notes

D1/D2 block authoritative cycles and published proposals; D3/D4 block qualified runner and clone activation inherited from D/C. Dmitry must approve the governing coordination authority and any additional named deciders; a cycle cannot infer them. Assign control_project_cycle to loop/fleet and keep domain schemas in contracts under A effective architecture before ready. Inventory graph assets through W30. W78 supplies final serialized/checkpoint journey qualification; preserve actual node-to-command evidence here, including empty-cycle accounting.
