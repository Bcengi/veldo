---
schema: veldo.spec/v1
id: VELDO-0087
title: Project dependency invalidation and outcome-to-evidence traceability
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W72
plan_revision: 1
depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0084, VELDO-0085, VELDO-0086]
placement: [contracts, fleet, tracker, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/release_contract.py"
  - ".veldo/release_contract.py"
  - "packs/*/.veldo/release_contract.py"
  - "engine/.veldo/plan.py"
  - ".veldo/plan.py"
  - "packs/*/.veldo/plan.py"
  - "engine/.veldo/frontier.py"
  - ".veldo/frontier.py"
  - "packs/*/.veldo/frontier.py"
  - "engine/.veldo/decision.py"
  - ".veldo/decision.py"
  - "packs/*/.veldo/decision.py"
  - "engine/.veldo/decision_review.py"
  - ".veldo/decision_review.py"
  - "packs/*/.veldo/decision_review.py"
  - "engine/.veldo/tripwire.py"
  - ".veldo/tripwire.py"
  - "packs/*/.veldo/tripwire.py"
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/control_project_dependency*.py"
  - ".veldo/control_project_dependency*.py"
  - "packs/*/.veldo/control_project_dependency*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0087_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0087-project-dependency-invalidation-traceability.md"
  - "specs/index.md"
  - "proof/VELDO-0087/*"
behavior_bearing: true
observability:
  logs: >
    Graph amendments name typed edge, exact outcome/artifact revision, graph version, affected
    closure and accepted or rejected ruling.
  metrics: >
    Count unresolved references, mixed-edge cycles, withdrawn queued permissions, running
    publication stops and completed impact records.
  traces: >
    Expose
    outcome-to-request-to-contribution-to-spec-to-assignment-to-dispatch-to-decision-to-cost-to-acceptance
    links at one published watermark.
  error_taxonomy: >
    Distinguish combined cycle, ambiguous target, withdrawn prerequisite, stale assumption,
    missing floor settlement and inaccessible evidence.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: One combined acyclic dependency graph governs project execution independently of
      release membership. Set: control_project_dependency and plan.item_state/cmd_run_check,
      frontier.dependency_gate/claimable, release_contract.member_cycles plus E decision bindings.
      Completeness: Require edge coverage equal to A: plan work, spec dependencies, project
      dependencies, decision prerequisites and release-execution ordering. Build graphs
      individually acyclic but cyclic in combination, missing/ambiguous/inaccessible targets and
      rejected amendments revealing actual prerequisites. Block affected items with references and
      require technical-authority resolution; rejection cannot leave an unsafe old graph
      executable. Falsifier: Validate each edge family separately instead of the combined graph;
      project-graph/mixed-cycle must detect granted authorization through a cycle.
    falsified_by: >
      Validate each edge family separately instead of the combined graph;
      project-graph/mixed-cycle must detect granted authorization through a cycle.
  - id: AC2
    text: >
      Claim: Prerequisite and floor invalidation withdraw current permission while preserving
      historical observations. Set: Queued, running and completed dependents;
      decision.validate_record, decision_review.bind_review, tripwire.evaluate_readings and C
      shared eligibility. Completeness: Independently compute reverse closure, withdraw an
      accepted prerequisite, expire a governing reading, change a floor pin or remove a required
      floor/settlement while claims/publication race. Require queued readiness removal, running
      publication refusal and completed impact records. Only a current baseline-authority
      settlement through E can resolve changed pins; it grants no unrelated scope. Falsifier: Keep
      running publication permission after prerequisite withdrawal;
      project-graph/running-invalidation must detect an unauthorized landing attempt.
    falsified_by: >
      Keep running publication permission after prerequisite withdrawal;
      project-graph/running-invalidation must detect an unauthorized landing attempt.
  - id: AC3
    text: >
      Claim: An authorized reader can reconstruct the full outcome evidence chain without a
      conversation or mutable status. Set: control_project_dependency trace views using
      plan.cmd_impact, release_contract.release_report and published B snapshot references.
      Completeness: Enumerate every accepted objective contribution and all request, release/plan,
      spec, assignment, dispatch, decision, cost and acceptance links at a fixed watermark.
      Compare returned links bidirectionally to authoritative records, restart with checkpoints
      deleted, and remove each required receipt in turn. Missing evidence is named and cannot
      establish completion; access restrictions remain explicit. Falsifier: Drop cost records from
      an otherwise complete outcome trace; project-graph/trace-closure must detect the missing
      authoritative links.
    falsified_by: >
      Drop cost records from an otherwise complete outcome trace; project-graph/trace-closure must
      detect the missing authoritative links.
required_evidence: [unit, integration]
rollback: >
  Withdraw affected dependency permissions, preserve rejected amendments and historical receipts,
  and revalidate the complete graph after authorized repair.
---

## Intent

Invalidate project execution on changed prerequisites and make every accepted outcome traceable to its authority and evidence.

## Context

Package F, W72 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R14, R61, R65 and R70/R71 extend C/E dependency consumers. Mixed cycles or stale floor permission can authorize critical publication. Risk is critical; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

Automatic technical conflict resolution, rewriting completed history and deriving execution order from release membership are excluded.

## Notes

D1/D2 block graph transactions and replicated eligibility; D3/D4 govern affected execution and recovery. Dmitry must designate technical and baseline authorities under R37/R64/R65 before they resolve cycles or floor changes. W54-W56 own decision/review/observation repairs; this item consumes their accepted results. No floor or settlement policy files are edited here, so protected_paths is empty; any newly required protected change needs a revised footprint and approval. Map control_project_dependency and inventory it before ready; retain mixed-cycle, withdrawal and missing-link proof matrices.
