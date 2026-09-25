---
schema: veldo.spec/v1
id: VELDO-0073
title: Per-channel live ingress activation and real sandbox qualification
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W58
plan_revision: 4
depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0126]
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
  - "engine/.veldo/control_channel_projection.py"
  - ".veldo/control_channel_projection.py"
  - "packs/*/.veldo/control_channel_projection.py"
  - "engine/.veldo/control_channel_presentation.py"
  - ".veldo/control_channel_presentation.py"
  - "packs/*/.veldo/control_channel_presentation.py"
  - "engine/.veldo/control_channel_attribution.py"
  - ".veldo/control_channel_attribution.py"
  - "packs/*/.veldo/control_channel_attribution.py"
  - "scripts/suites/support/v73_*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - ".veldo/policy.yaml"
  - "engine/.veldo/policy.yaml"
  - "packs/*/.veldo/policy.yaml"
  - "scripts/suites/*_veldo_0073_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
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

## What the reviewer judges

- Normal use: the owner activates the Telegram edge with an explicit, separately authorized activation
  record bound to the current VELDO-0067 enrollment and to real qualification evidence from the test
  bot. Only then can the edge send a decision and receive answers. A received update wakes acquisition;
  the answer is read from the platform's own fields and signed by the restricted signer before the
  VELDO-0068 settlement takes it. The owner can stop the edge explicitly; pending requests stay pending.
- Threat model: the edge sending or receiving because a token resolves or because the source landed,
  without activation; fixture-only or invented qualification evidence accepted as real; a settlement
  made from a notification payload rather than from acquired platform evidence; an answer from someone
  who is not the enrolled owner; a stopped edge, a stale key or a stale configuration binding still
  producing authority. The owner's account, the bot token's custody, the signer and the store are
  trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); interrupted
  settlement, retention, reconnect, reordering, restart and rollback qualification (Release 2); other
  channels (Release 4); a second real person as the unauthorized actor (the owner has none, Telegram
  29047; the refusal is driven with an update from an unenrolled sender id, as in VELDO-0066); a
  compromised Telegram account or bot token.

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

2026-09-22, PLAN-0019 revision 3, Release 1 stage 3: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC2 interrupted
settlement, AC3 retention/reconnect/reordering and AC4 restart/rollback qualification moved to
Release 2; additional channels moved to Release 4. Jira activation is dropped. Real Telegram
activation/send/receive/canonical answers remain. The criteria, declared evidence universe,
Context and Notes above now carry only the retained function. No specification status or
historical proof was changed.

2026-09-24, implementation: every installed Telegram send and receive entry point now asks the
activation gate before each exchange (control_channel_activation.ENTRY_POINTS: TelegramEdge.send,
TelegramPresentationEdge.send, TelegramAcquisitionEdge getMe and getUpdates, and the doorbell's
TelegramSink.send), so the footprint gains the three VELDO-0064 to VELDO-0066 edge modules whose
exchange lines changed; nothing else in them changed. It also gains
scripts/suites/support/v73_*.py, the real authority the suite and the live qualification runner
share, so the runner exercises exactly what the rows exercise. Only a loopback stand-in Bot API is
reached without a gate, which keeps the earlier suites' stand-ins working unchanged.

2026-09-24, review finding from VELDO-0069: nothing in production constructed the VELDO-0068
settlement service, so a real Telegram answer had no production path to one authoritative settlement.
control_channel_ingress.open_ingress now constructs the ingress from host configuration (the store,
the journal signer, the host trust whose settlement signers VELDO-0054 readers verify against, the
VELDO-0067 protected answer signer and the token file), with the settlement service on the same
connection, and a row drives that construction. VELDO-0069 is added to depends_on: after it landed
(1b8edfe) the construction passes the settlement service its decision signer from the configuration,
a principal that must be one of the host's settlement signers and a 0600 key outside the workspace
whose probe signature must verify under those signers, so governing bindings are signed by the key
the reading side trusts.

2026-09-24, review 1 fix (blocking): a listener at the configured loopback origin could answer with a redirect and
urllib followed it, token in the path, to any host, including api.telegram.org, with no activation, on the
ungated edge and through the gate's own opener. Every Bot API exchange now uses one opener
(control_channel_projection.bot_opener) with no proxy and no redirect. Row activation/no-redirect, red at ad856ac
(proof/VELDO-0073/red-at-ad856ac.json), and three mutations in finding 73.

2026-09-24, review 2 (blocking, withdrawn claim): the row that checked the live run's committed record
accepted a hand-written record, because a file cannot show where it came from; the reviewer forged one and
the row passed. The claim is withdrawn: the row is now qualification/live-record-consistent, a consistency
check only. The live run's witness is the owner, who can confirm on his phone the reply whose message id
and date the record names; the binding real-platform proof is the running factory's own qualification and
activation under VELDO-0138, where the gate records every exchange in the factory's store and his enrolled
key signs the activation over it. Also from review 2: a Bot API origin is parsed, not prefix-matched
(http://127.0.0.1:80@api.telegram.org is no stand-in), with row checks and two mutations.
