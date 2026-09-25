---
schema: veldo.spec/v1
id: VELDO-0128
title: Telegram progress and completion from journal events
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W91
plan_revision: 3
depends_on: [VELDO-0046, VELDO-0051, VELDO-0073, VELDO-0075]
placement: [metrics, tracker]
protected_paths: []
footprint:
  - "engine/.veldo/control_telegram_report*.py"
  - ".veldo/control_telegram_report*.py"
  - "packs/*/.veldo/control_telegram_report*.py"
  - "engine/.veldo/request_doorbell.py"
  - ".veldo/request_doorbell.py"
  - "packs/*/.veldo/request_doorbell.py"
  - "scripts/suites/*_veldo_0128_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0128-telegram-journal-reporting.md"
  - "specs/index.md"
  - "proof/VELDO-0128/*"
behavior_bearing: true
observability:
  logs: >
    Record operation, domain/repository, actor or role, input/configuration versions,
    resulting record identity and named refusal; exclude secrets.
  metrics: >
    Count accepted/refused operations and pending work, with bounded run duration and
    charge attribution where this concern uses a worker.
  traces: >
    Correlate input request, configuration/host, dispatched work and resulting authority evidence.
  error_taxonomy: >
    Distinguish unauthenticated, unauthorized, stale version, unsupported configuration,
    unavailable service, missing evidence and unknown outcome; none is successful completion.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Enabled journal progress, stop and completion events generate correlated owner Telegram
      reports. Set and completeness: Enumerate reporting event registrations for accepted objective,
      grooming/admission wait, assignment/worker progress, gate/review result, stop and completion;
      commit each in the real authority and observe actual sandbox sends with project/unit/run and
      source event identity retained. Falsifier: Omit the completion event handler; the registry-to-
      delivery comparison must fail.
    falsified_by: >
      Omit the completion event handler; the registry-to-delivery comparison must fail.
  - id: AC2
    text: >
      Claim: Report content reflects the committed fact and provides the relevant next action or
      evidence link. Set and completeness: Compare delivered bytes to stored events and receipts for
      running, awaiting decision, gate/review rejected and exact-landing-completed examples;
      unknown/unavailable state stays explicit. Completion includes the confirmed revision/proof,
      and a pending decision links to its current presentation. Falsifier: Report complete from a
      build-only event; the completion-receipt check must fail.
    falsified_by: >
      Report complete from a build-only event; the completion-receipt check must fail.
  - id: AC3
    text: >
      Claim: Reports go only to the configured enrolled recipient and record actual send outcome.
      Set and completeness: Send to the configured owner chat, substitute another chat and simulate
      a normal send refusal at the boundary; require refused substitution and visible unsent status
      without losing the source event or fabricating a decision. Falsifier: Mark a refused send as
      delivered; the send-result observation must fail.
    falsified_by: >
      Mark a refused send as delivered; the send-result observation must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern while preserving accepted records, configuration
  revisions and unresolved work. No automatic rollback, retry or recovery is authorized.
---

## Intent

Keep the owner informed on Telegram about ordinary progress, stops and completion using
authoritative journal facts.

## Context

W91 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 3.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its 2026-09-22
scope amendments. This new specification is draft; authoring it supplies neither implementation
proof nor operational activation. Implementation still requires readiness and applicable approval.

## Out of scope

Automatic recovery, durability/scale qualification and additional host/channel types beyond
this declared concern. These belong to later releases as assigned by the plan. No existing
specification status, implementation, test, runtime policy or deployed service changes in this draft.

## What the reviewer judges

- Normal use: when the authority commits an enabled journal event (accepted objective, a grooming or
  admission wait, assignment or worker progress, a gate or review result, a stop, a completion), the
  owner gets one correlated Telegram report through the activated edge, naming the project, unit, run
  and source event. The report states the committed fact and the next action or evidence: a pending
  decision links to its current presentation, and a completion names the confirmed revision and proof.
  Unknown or unavailable state is said plainly. Reports go only to the configured enrolled chat, and
  each records its real send outcome.
- Threat model: an enabled event with no report, or a report with no committed event behind it; a
  completion reported from a build-only event or anything short of the confirmed-landing receipt; a
  report that grants admission or asserts completion; a report sent to another chat; a refused send
  recorded as delivered, or the source event lost when a send fails. The owner's account, the store
  and the activated Telegram edge are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); reconnect,
  replay, lost-send lookup and delivery recovery (Release 2); forged rows in our own store and files
  planted in the installed directory. The real-Telegram send is run once by the lead with the owner
  through the running factory; the rows use a loopback stand-in.

## Notes

This fills the ordinary reporting gap between internal wake-ups and the andon decision path.
Use the enrolled Telegram edge and accepted project/owner/chat mapping. A report is a
projection and never grants admission or asserts completion from model output. Reconnect,
replay, lost-send lookup and delivery recovery belong to Release 2.

Use canonical engine assets and synchronize installed copies. Resolve the proposed footprint's
architecture mapping before ready, including the new UI assets where applicable; this draft does
not amend the architecture contract. Inventory every asset the selected journey installs. Compare
executable registrations to each criterion's declared universe, observe the real named interfaces,
and retain the driven negative-control diff and named failed row. Fixtures cannot certify real
platform, engine or host behavior. Required evidence labels describe future implementation proof,
not tests run by this writing revision.

## History

2026-09-22: new draft for PLAN-0019 revision 3, Release 1 stage 3, under the owner's
complete-factory MVP decisions. Simple function and its meaningful refusal checks are in this
release; recovery and robustness are Release 2, governance depth Release 3, broader hosts/channels,
installation, adoption, migration and rollback Release 4.
