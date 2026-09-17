---
schema: veldo.spec/v1
id: VELDO-0069
title: Governing decision binding, supersession, and eligibility updates
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W54
plan_revision: 1
depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0068]
placement: [contracts, tracker, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/decision.py"
  - ".veldo/decision.py"
  - "packs/*/.veldo/decision.py"
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/request_reconcile.py"
  - ".veldo/request_reconcile.py"
  - "packs/*/.veldo/request_reconcile.py"
  - "engine/.veldo/plan.py"
  - ".veldo/plan.py"
  - "packs/*/.veldo/plan.py"
  - "engine/.veldo/control_decision_dependency*.py"
  - ".veldo/control_decision_dependency*.py"
  - "packs/*/.veldo/control_decision_dependency*.py"
  - "engine/.veldo/control_request_settlement*.py"
  - ".veldo/control_request_settlement*.py"
  - "packs/*/.veldo/control_request_settlement*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0069_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0069-governing-decision-bindings.md"
  - "specs/index.md"
  - "proof/VELDO-0069/*"
behavior_bearing: true
observability:
  logs: >
    Decision transitions name framing and subject digests, exact affected entities, old/new
    binding versions, settlement receipt, and invalidation cause.
  metrics: >
    Measure unresolved bindings, withdrawn queued permissions, stopped running dependents,
    completed impact records, and pending replacement requests.
  traces: >
    Join channel-originating settlement to the governing decision and reverse dependency closure,
    then to plan eligibility and published replacement presentations.
  error_taxonomy: >
    Distinguish absent binding, stale framing, wrong subject, superseded ruling, expired decision,
    invalid graph, and pending eligibility update.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Settlement updates the exact governing decision and all bound dependency permissions
      atomically. Set: decision.validate_record/check_record,
      request_reconcile._settlement_record/_reconcile_one,
      plan._decision_blocks/item_state/cmd_run_check, and C control_decision_dependency
      integration. Completeness: Enumerate R71 subject kinds from A: projects, release executions,
      plans, backlog items, specs and contracts. Drive real signed channel assertions through W53
      settlement against each binding, inspect chosen option/decider/time and current
      subject/framing digests, and read eligibility in another process. Kill at binding-update and
      settlement commit barriers; a receipt alone cannot unblock an unresolved or wrong-subject
      dependency. Falsifier: Commit a settlement receipt without updating the exact decision
      binding; binding/settlement-effects must detect a resolved request whose dependent plan
      remains incorrectly bound.
    falsified_by: >
      Commit a settlement receipt without updating the exact decision binding;
      binding/settlement-effects must detect a resolved request whose dependent plan remains
      incorrectly bound.
  - id: AC2
    text: >
      Claim: Supersession, expiry, changed framing, or failed assumptions reopen the obligation
      and withdraw affected readiness without rewriting historical outcomes. Set:
      decision.validate_record, request.request_digest, plan._decision_blocks, and the enrolled
      supersession path through control_decision_dependency and request settlement. Completeness:
      Build mixed real dependency graphs from every A edge family and compute reverse closure
      independently. Change framing bytes under the same displayed ID/version, expire a ruling,
      and supersede a subject while claims and publication checks race. Require a new immutable
      request revision, queued withdrawal, running permission removal, and impact records for
      completed dependents; restart after invalidation commit and verify the same closure.
      Falsifier: Cache a resolved decision across framing supersession while project version stays
      unchanged; binding/framing-invalidation must catch surviving publication permission.
    falsified_by: >
      Cache a resolved decision across framing supersession while project version stays unchanged;
      binding/framing-invalidation must catch surviving publication permission.
  - id: AC3
    text: >
      Claim: Replacement decisions resolve only their authorized current bindings and cannot
      restore readiness from inline status or a stale channel answer. Set:
      plan._decision_blocks/cmd_run_check, request_reconcile.reconcile_requests and
      decision.load_record consumers over accepted snapshots and inline open_decisions references.
      Completeness: Enumerate missing, ambiguous, cyclic, withdrawn and current decision targets.
      Settle a valid replacement through each enrolled channel, race a new prerequisite insertion
      at commit, and retain prior ruling evidence. Compare shared eligibility at selection, direct
      review and publication; unresolved references and stale complete read sets refuse, while a
      valid current ruling unblocks only the authorized closure. Falsifier: Treat an inline
      open_decisions status edit as resolution without an accepted replacement settlement;
      binding/inline-bypass must detect unauthorized eligibility.
    falsified_by: >
      Treat an inline open_decisions status edit as resolution without an accepted replacement
      settlement; binding/inline-bypass must detect unauthorized eligibility.
required_evidence: [unit, integration]
rollback: >
  Withdraw affected permissions, preserve all old bindings and settlements, and request an
  authorized version-bound replacement without restoring stale readiness.
---

## Intent

Make a settled governing decision change the exact permissions it governs and reopen them when its framing ceases to hold.

## Context

Package E, W54 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A/B/C contracts govern implementation. This draft grants no implementation or activation authority.

R14, R39-R40, R60, R70 and R71 require actual decision transitions to drive C dependency consumers. A detached receipt or an inline plan edit cannot establish an authorized governing choice. The declared risk floor is critical; required approval must bind the eventual change and proof. This declaration records no approval.

## Out of scope

New project graph authoring, standalone architecture ratification, and live channel activation are outside this binding repair.

## Notes

D1/D2 block atomic bindings and published eligibility. D3/D4 remain C prerequisites for execution affected by these bindings until Dmitry rules. C W39 supplied decision consumption using fixtures; this item supplies its actual settlement producer through the existing decision/request path. Do not edit this plan D1-D4 as though drafting settled them. Preserve immutable framing, accepted subject digests and reverse graph versions; actor-facing projections are not authoritative. Existing decision and plan functions are known integration sites, while narrow dependency/settlement modules inherit their A/B/C architecture mappings and W30 inventory. Retain mutation diffs and failed eligibility observations. W56 adds trusted observation production and invokes this invalidation path.
