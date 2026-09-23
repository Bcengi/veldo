---
schema: veldo.spec/v1
id: VELDO-0073
title: Per-channel live ingress activation and real sandbox qualification
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W58
plan_revision: 3
depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068]
placement: [tracker, engine, contracts, distribution]
protected_paths: [.veldo/policy.yaml]
footprint:
  - "engine/.veldo/request_doorbell.py"
  - ".veldo/request_doorbell.py"
  - "packs/*/.veldo/request_doorbell.py"
  - "engine/.veldo/request_projection.py"
  - ".veldo/request_projection.py"
  - "packs/*/.veldo/request_projection.py"
  - "engine/.veldo/request_reconcile.py"
  - ".veldo/request_reconcile.py"
  - "packs/*/.veldo/request_reconcile.py"
  - "engine/.veldo/control_channel_ingress*.py"
  - ".veldo/control_channel_ingress*.py"
  - "packs/*/.veldo/control_channel_ingress*.py"
  - "engine/.veldo/control_channel_activation*.py"
  - ".veldo/control_channel_activation*.py"
  - "packs/*/.veldo/control_channel_activation*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - ".veldo/policy.yaml"
  - "engine/.veldo/policy.yaml"
  - "packs/*/.veldo/policy.yaml"
  - "scripts/suites/*_veldo_0073_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0073-channel-ingress-activation.md"
  - "specs/index.md"
  - "proof/VELDO-0073/*"
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
      Claim: Telegram ingress and decision sends require separately authorized activation bound to
      enrollment and proof. Set and completeness: Enumerate installed Telegram send and receive
      entry points; invoke before activation and after source landing alone, then with valid sandbox
      qualification and current key/enrollment. Only the latter may operate. Falsifier: Allow
      TelegramSink.send merely because a token resolves; the no-implicit-activation check must fail.
    falsified_by: >
      Allow TelegramSink.send merely because a token resolves; the no-implicit-activation check must
      fail.
  - id: AC2
    text: >
      Claim: Actual Telegram presentation, canonical answer acquisition and restricted signing reach
      one authoritative settlement. Set and completeness: In the real sandbox send a decision,
      answer as enrolled owner and unauthorized actor, retrieve sender/message/time and presentation
      relation, and inspect the real settlement. Fixtures cannot certify this row. Falsifier: Accept
      fixture-only sandbox evidence for activation; the real-platform-proof check must fail.
    falsified_by: >
      Accept fixture-only sandbox evidence for activation; the real-platform-proof check must fail.
  - id: AC3
    text: >
      Claim: Notifications wake acquisition and never substitute for an authenticated answer. Set
      and completeness: Deliver an ordinary real Telegram event and an invented notification
      payload; preserve returned message identifiers and acquire canonical platform evidence before
      assertion. Falsifier: Settle from the notification payload alone; the unsupported-answer check
      must fail.
    falsified_by: >
      Settle from the notification payload alone; the unsupported-answer check must fail.
  - id: AC4
    text: >
      Claim: Explicit stop and current authorization control the active Telegram edge. Set and
      completeness: Stop the edge normally and attempt send/answer acceptance, then present stale
      key/configuration bindings; inspect no fresh authority and retained pending requests.
      Falsifier: Ignore the explicit stopped activation record; the stopped-edge request must
      succeed and fail the check.
    falsified_by: >
      Ignore the explicit stopped activation record; the stopped-edge request must succeed and fail
      the check.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Per-channel live ingress activation and real sandbox qualification. Deliver the normal function needed by the running factory journey.

## Context

W58 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 3.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Qualify only the actual Telegram send/receive edge here, using a real sandbox and known
enrolled identities. Capture redacted platform evidence with verifiable provenance. Arbitrary
new message intake and ordinary progress reporting are separate new specifications. A bot
token alone is not activation.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 3: owner Telegram 28848 moves
recovery/robustness to Release 2. Drop other-channel qualification, AC2 interrupted
settlement, AC3 retention/reconnect/reordering matrix, and AC4 restart/rollback qualification;
retain real Telegram activation, send/receive, and canonical answer acquisition. Jira-specific
intake/decision/projection work is dropped under 28857/28859; additional non-Jira channel
breadth is Release 4. UI/API support is supplied by 0130/0131 against the retained settlement
contract. Removed recovery, durability and failure-matrix obligations belong to Release 2;
additional host/channel/version and full distribution breadth belongs to Release 4. Normal
function and the checks stated above remain Release 1.
