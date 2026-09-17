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
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024]
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
    Notification records identify consumer, durable sequence, cursor, delivery obligation, and
    reconnect reason.
  metrics: >
    Measure pending delivery count and age, cursor lag, replayed events, duplicate notifications,
    and bounded reconnect attempts.
  traces: >
    Join command commit and published watermark to signal emission, authenticated IPC delivery,
    consumer handling, and cursor acknowledgment.
  error_taxonomy: >
    Distinguish notification gap, notifier death, unauthenticated peer, stale cursor, unpublished
    event, and delivery still pending.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Committed history and delivery obligations wake consumers through in-process signals
      and authenticated IPC, with publication-dependent actions held until durable
      acknowledgment. Set: Intake, settlement, assignment, dependency, completion, revocation,
      and budget-availability events in real control.sqlite3. Completeness: Compare R28 causes
      with the producer registry and drive each through real command and consumer processes.
      Disconnect IPC and withhold Git export acknowledgment; obligations persist, notification
      cannot grant unpublished authority, and consumers do not periodically query storage to
      discover changes. Falsifier: Authorize a dependent consumer action on a local notification
      before its export acknowledgment; notifications/unpublished-event must detect that action.
    falsified_by: >
      Authorize a dependent consumer action on a local notification before its export
      acknowledgment; notifications/unpublished-event must detect that action.
  - id: AC2
    text: >
      Claim: Commit notification and entering idle serialize so a committed event cannot leave a
      live consumer asleep indefinitely. Set: Real event loop, notifier process or channel, and
      idle consumer across commit, signal send, and idle-transition barriers. Completeness: Race
      an event with idle entry in both orders; SIGKILL the notifier after commit before signal and
      require channel closure plus recovery replay within the declared reconnect deadline. Count
      storage reads during quiet idle to exclude discovery polling. Falsifier: Enter idle after
      checking the queue outside the notification boundary and commit in that gap;
      notifications/lost-wakeup must detect the sleeping consumer.
    falsified_by: >
      Enter idle after checking the queue outside the notification boundary and commit in that
      gap; notifications/lost-wakeup must detect the sleeping consumer.
  - id: AC3
    text: >
      Claim: Durable cursors replay startup, reconnect, and explicit resynchronization without
      duplicating committed consumer effects or losing delivery obligations. Set: Real consumer
      cursor transactions and idempotent handlers, including terminal projection obligations and
      out-of-order notifications. Completeness: Kill consumers before handler commit, after effect
      commit before cursor acknowledgment, and after cursor commit. Restart from each stored
      cursor, duplicate notifications, and compare logical effects and complete journal-sequence
      coverage to the retained event range. Falsifier: Advance the cursor before the handler
      transaction and kill the consumer in that window; notifications/cursor-before-effect must
      detect the skipped event.
    falsified_by: >
      Advance the cursor before the handler transaction and kill the consumer in that window;
      notifications/cursor-before-effect must detect the skipped event.
required_evidence: [unit, integration]
rollback: >
  Pause affected consumers, retain delivery obligations and cursors, and replay from the last
  acknowledged cursor through a compatible handler without discarding unsignaled commits.
---

## Intent

Wake consumers reliably from durable events and replay cursor gaps without polling storage for rare changes.

## Context

Package B, W31 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R23, R28, R41, R57. Package A contracts must be accepted before implementation; this draft grants no implementation or activation authority.

Lost notifications or premature cursors could strand committed work or skip revocation and stop obligations. The declared risk floor is high. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

Live tracker doorbells, channel projection creation, and model project cycles are separate work.

## Notes

D1 and D2 are inherited from the store and replica. Notification is transport, SQLite is durable history, and timers are limited to real deadlines, heartbeat, and bounded reconnect backoff. Define the reconnect bound in configuration before ready. Existing tracker session-start pull remains visibly limited until E qualifies its ingress; this transport does not silently activate it.

