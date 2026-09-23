---
schema: veldo.spec/v1
id: VELDO-0079
title: Grooming and admission requests through enrolled decision surfaces
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W64
plan_revision: 3
depends_on: [VELDO-0065, VELDO-0068, VELDO-0069, VELDO-0073, VELDO-0078]
placement: [contracts, tracker, engine, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/request_projection.py"
  - ".veldo/request_projection.py"
  - "packs/*/.veldo/request_projection.py"
  - "engine/.veldo/request_reconcile.py"
  - ".veldo/request_reconcile.py"
  - "packs/*/.veldo/request_reconcile.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/control_grooming*.py"
  - ".veldo/control_grooming*.py"
  - "packs/*/.veldo/control_grooming*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0079_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0079-grooming-enrolled-decision-surfaces.md"
  - "specs/index.md"
  - "proof/VELDO-0079/*"
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
      Claim: Grooming presents the exact complete authorization material. Set and completeness:
      Compare real Telegram briefs to the request schema: class, outcome, scope/exclusions,
      priority, ceiling, lane, policy/spec revisions, protected paths, release authority,
      expiry/evidence, decomposition, alternatives and questions. Change each bound field and refuse
      the earlier presentation. Falsifier: Omit decomposition digest from presentation binding; the
      changed-decomposition refusal check must fail.
    falsified_by: >
      Omit decomposition digest from presentation binding; the changed-decomposition refusal check
      must fail.
  - id: AC2
    text: >
      Claim: Only current admission and priority authorities may admit or prioritize prepared work.
      Set and completeness: Exercise owner admit/reject/return choices and a PM self-admission
      attempt through actual authenticated assertions; require actor-authored reasoning, separate
      authority predicates and no execution while required questions remain unresolved. Falsifier:
      Accept a PM role label as admission authority; the preparer-cannot-admit check must fail.
    falsified_by: >
      Accept a PM role label as admission authority; the preparer-cannot-admit check must fail.
  - id: AC3
    text: >
      Claim: The accepted ruling authorizes only its exact operation, target and parameters. Set and
      completeness: Change priority, ceiling and target separately beneath a retained valid signed
      command, and submit an unchanged ordinary duplicate; inspect refusal of changes and one bound
      settlement for the duplicate. Falsifier: Reuse an admission signature after changing priority
      without digest validation; the parameter-binding check must fail.
    falsified_by: >
      Reuse an admission signature after changing priority without digest validation; the parameter-
      binding check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Grooming and admission requests through enrolled decision surfaces. Deliver the normal function needed by the running factory journey.

## Context

W64 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Telegram is the first presentation channel; UI/API later consumes the same full request and
settlement contract. No Jira intake, tracker projection or signed-CLI decision channel is
built. Admission and priority remain distinct decisions even when the owner settles them
together.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 4: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC3
concurrent/lost-ack qualification moved to Release 2; extra-channel coverage moved to Release
4. Jira-specific grooming is dropped. Exact material, owner ruling and distinct
admission/priority remain. The criteria, declared evidence universe, Context and Notes above
now carry only the retained function. No specification status or historical proof was changed.
