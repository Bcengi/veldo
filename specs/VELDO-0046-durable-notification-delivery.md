---
schema: veldo.spec/v1
id: VELDO-0046
title: Durable wake-up, cursor replay, and notification delivery
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W31
plan_revision: 3
depends_on: [VELDO-0023, VELDO-0107]
placement: [fleet, metrics, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_notify*.py"
  - ".veldo/control_notify*.py"
  - "packs/*/.veldo/control_notify*.py"
  - "engine/.veldo/control_cursor*.py"
  - ".veldo/control_cursor*.py"
  - "packs/*/.veldo/control_cursor*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0046_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0046-durable-notification-delivery.md"
  - "specs/index.md"
  - "proof/VELDO-0046/*"
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
      Claim: Committed journal events wake each enabled consumer through signals or authenticated
      IPC. Set and completeness: Compare enabled producer/consumer registrations to the installed
      journey, drive each event into the real store, and observe its handler only after local
      commit. Falsifier: Notify and accept an action before its transaction commits; the committed-
      event check must fail.
    falsified_by: >
      Notify and accept an action before its transaction commits; the committed-event check must
      fail.
  - id: AC2
    text: >
      Claim: Entering idle cannot lose an ordinary committed wake-up. Set and completeness: Use real
      event-loop barriers to deliver an event immediately before and after idle entry; both orders
      must invoke the consumer, with no periodic database discovery polling while quiet. Falsifier:
      Check the queue outside the idle transition; the event-in-the-gap check must leave a sleeping
      consumer and fail.
    falsified_by: >
      Check the queue outside the idle transition; the event-in-the-gap check must leave a sleeping
      consumer and fail.
  - id: AC3
    text: >
      Claim: Consumers receive the committed event identity and watermark and cannot treat transport
      as authority. Set and completeness: For each enabled consumer submit a genuine notification
      and an invented event identity; read the actual stored event before acting, and reject the
      invented identity. Falsifier: Trust an invented IPC event payload without resolving its
      journal entry; the fabricated-event check must fail.
    falsified_by: >
      Trust an invented IPC event payload without resolving its journal entry; the fabricated-event
      check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Durable wake-up, cursor replay, and notification delivery. Deliver the normal function needed by the running factory journey.

## Context

W31 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

The active event consumers include settlement, assignment, dependency, completion and budget
updates; the common intake and PM subscribe when installed. Telegram reporting is a separate
projection. No Jira discovery polling or replay/reconnect qualification is required.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 1: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC1 off-host
failures, AC2 notifier-death recovery and AC3 startup/reconnect/cursor replay moved to Release
2. Enabled event wake-up and lost-wakeup check remain. The criteria, declared evidence
universe, Context and Notes above now carry only the retained function. No specification
status or historical proof was changed.
