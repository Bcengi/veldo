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
plan_revision: 3
depends_on: [VELDO-0054, VELDO-0068]
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
    Record the operation, domain, repository, unit or request identity, accepted input versions,
    outcome and named refusal without secrets.
  metrics: >
    Count accepted and refused operations and expose current pending work for this specification.
  traces: >
    Join accepted inputs, actual service observations and resulting authority records by identity.
  error_taxonomy: >
    Distinguish invalid input, missing authority, stale subject, unavailable service,
    missing evidence and unknown outcome where applicable; never label unknown as success.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A current settlement updates its exact governing decision and subject binding
      atomically. Set and completeness: Drive real signed Telegram settlement for a blocking
      specification question and plan decision; read chosen option, decider, time, framing and
      subject digests plus eligibility from another process. Falsifier: Commit only a receipt
      without the governing binding; the resolved-request-to-eligibility check must fail.
    falsified_by: >
      Commit only a receipt without the governing binding; the resolved-request-to-eligibility check
      must fail.
  - id: AC2
    text: >
      Claim: Wrong framing, subject or current version cannot unblock governed work. Set and
      completeness: Alter each of those three bindings independently under an otherwise valid
      settlement through decision/request reconciliation; inspect unchanged permissions and a named
      blocker in plan and direct floor entry. Falsifier: Ignore subject digest during binding; the
      wrong-subject refusal check must fail.
    falsified_by: >
      Ignore subject digest during binding; the wrong-subject refusal check must fail.
  - id: AC3
    text: >
      Claim: Only the accepted binding resolves a referenced decision at every enabled consumer. Set
      and completeness: Enumerate plan._decision_blocks/item_state/cmd_run_check and shared floor
      consumers; compare unresolved, valid current and inline-status-only cases using real
      snapshots. Falsifier: Treat inline open_decisions text as authority; the inline-bypass check
      must fail.
    falsified_by: >
      Treat inline open_decisions text as authority; the inline-bypass check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Governing decision binding, supersession, and eligibility updates. Deliver the normal function needed by the running factory journey.

## Context

W54 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 3.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

The actual settlement producer updates 0054 decision consumers. Ordinary spec/plan bindings
are in this slice; unsupported subject kinds stop. A detached receipt and inline resolved text
grant no eligibility. UI/API answers later share this binding operation.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 3: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC1 commit-
barrier crashes and AC2/AC3 concurrent/restart matrices moved to Release 2; expiry, reopening,
tripwires and reverse invalidation moved to Release 3. Normal settlement updates its exact
governing binding. The criteria, declared evidence universe, Context and Notes above now carry
only the retained function. No specification status or historical proof was changed.
