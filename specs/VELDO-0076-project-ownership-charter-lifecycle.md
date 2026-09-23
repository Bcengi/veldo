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
plan_revision: 3
depends_on: [VELDO-0025, VELDO-0035, VELDO-0036, VELDO-0068, VELDO-0073]
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
      Claim: Project activation binds owner, charter, execution repository, authority policy and
      finite coordination budget. Set and completeness: Enumerate those required schema fields and
      omit each in a real signed activation command; valid current owner acceptance creates one
      active project, while missing authority or budget refuses. Falsifier: Skip the budget
      predicate; the unbounded-project check must fail.
    falsified_by: >
      Skip the budget predicate; the unbounded-project check must fail.
  - id: AC2
    text: >
      Claim: Pause and cancellation stop new assignments and dispatch while preserving accepted
      history. Set and completeness: Activate, pause and cancel a real project with pending and
      running work; observe the ordinary host stop policy, no new dispatch and unchanged landed
      receipts. Falsifier: Permit frontier to assign work after pause; the paused-project check must
      fail.
    falsified_by: >
      Permit frontier to assign work after pause; the paused-project check must fail.
  - id: AC3
    text: >
      Claim: Project completion requires terminal objectives and disposition of its ordinary
      outstanding obligations. Set and completeness: Attempt completion with an open objective,
      assignment, decision, dispatch or reservation separately, then with all required records
      resolved; compare accepted project state and preserved history. Falsifier: Complete with a
      pending objective; the incomplete-project refusal check must fail.
    falsified_by: >
      Complete with a pending objective; the incomplete-project refusal check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Project ownership, charter, lifecycle, and transfers. Deliver the normal function needed by the running factory journey.

## Context

W61 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Release 1 establishes the enrolled owner, one execution repository, charter and bounded
project coordination. The roster does not grant admission authority. Additional owners and
transfer require the Release 3 governance work rather than a default inferred delegation.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 4: owner Telegram 28848 moves
recovery/robustness to Release 2. Defer AC3 multi-owner transfer and AC1 concurrent/multi-
channel activation qualification; remove restart and unused release-execution cases from AC2,
retaining owner, charter, budget, pause, and cancellation. Removed recovery, durability and
failure-matrix obligations belong to Release 2; additional host/channel/version and full
distribution breadth belongs to Release 4. Normal function and the checks stated above remain
Release 1.
