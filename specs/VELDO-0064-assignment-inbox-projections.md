---
schema: veldo.spec/v1
id: VELDO-0064
title: Assignment inbox and durable projections on enrolled input surfaces
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W49
plan_revision: 3
depends_on: [VELDO-0025, VELDO-0035, VELDO-0046]
placement: [contracts, tracker, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/request_projection.py"
  - ".veldo/request_projection.py"
  - "packs/*/.veldo/request_projection.py"
  - "engine/.veldo/request_doorbell.py"
  - ".veldo/request_doorbell.py"
  - "packs/*/.veldo/request_doorbell.py"
  - "engine/.veldo/control_assignment*.py"
  - ".veldo/control_assignment*.py"
  - "packs/*/.veldo/control_assignment*.py"
  - "engine/.veldo/control_channel_projection*.py"
  - ".veldo/control_channel_projection*.py"
  - "packs/*/.veldo/control_channel_projection*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0064_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0064-assignment-inbox-projections.md"
  - "specs/index.md"
  - "proof/VELDO-0064/*"
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
      Claim: The inbox exposes person-required assignments without holding a worker while awaiting
      the answer. Set and completeness: Enumerate enabled pending, answered, declined and canceled
      states from the assignment schema; drive real commands and Telegram projection and compare
      owner, scope, deadline and budget to current authority state, with no waiting model process or
      claim. Falsifier: Retain a worker claim while waiting for the person; the waiting-resource
      check must fail.
    falsified_by: >
      Retain a worker claim while waiting for the person; the waiting-resource check must fail.
  - id: AC2
    text: >
      Claim: Telegram projection retains the actual external message identity and request
      correlation. Set and completeness: Send each enabled assignment kind through the qualified
      Telegram edge; persist the returned chat/message identifiers and compare them with retrieved
      presentation bytes and the inbox request version. Falsifier: Discard the returned message
      identifier; the projection-correlation check must fail.
    falsified_by: >
      Discard the returned message identifier; the projection-correlation check must fail.
  - id: AC3
    text: >
      Claim: Inbox views describe current assignments but do not grant authority. Set and
      completeness: Read pending and changed assignment versions through the actual index/brief
      readers, including an invalid record; require visible invalid state or current accepted
      content, never authority from assignee or display status. Falsifier: Admit work from a
      displayed assigned status alone; the unauthorized-admission check must fail.
    falsified_by: >
      Admit work from a displayed assigned status alone; the unauthorized-admission check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Assignment inbox and durable projections on enrolled input surfaces. Deliver the normal function needed by the running factory journey.

## Context

W49 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 3.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Use one authoritative inbox and ordinary Telegram projection; invalid accepted records must be
visible rather than silently skipped. The waiting owner decision must release model workers
and execution claims. The same inbox is read by the later authenticated UI/API.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 3: owner Telegram 28848 moves
recovery/robustness to Release 2. Drop AC2 lost-create-ack recovery and AC3 concurrent
reassignment/channel-removal matrix; narrow all criteria to Telegram, keeping the inbox and
release of workers while waiting. Jira-specific intake/decision/projection work is dropped
under 28857/28859; additional non-Jira channel breadth is Release 4. UI/API support is
supplied by 0130/0131 against the retained settlement contract. Removed recovery, durability
and failure-matrix obligations belong to Release 2; additional host/channel/version and full
distribution breadth belongs to Release 4. Normal function and the checks stated above remain
Release 1.
