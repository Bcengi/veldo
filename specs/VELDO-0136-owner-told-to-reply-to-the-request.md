---
schema: veldo.spec/v1
id: VELDO-0136
title: Tell the owner to reply to the request when an answer does not reply to a presentation
status: draft
risk: standard
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W99
plan_revision: 3
depends_on: [VELDO-0065, VELDO-0066]
placement: [contracts, loop]
protected_paths: []
footprint:
  - "plans/PLAN-0019-dark-factory.md"
  - "engine/.veldo/control_channel_presentation.py"
  - ".veldo/control_channel_presentation.py"
  - "packs/*/.veldo/control_channel_presentation.py"
  - "engine/.veldo/control_channel_attribution.py"
  - ".veldo/control_channel_attribution.py"
  - "packs/*/.veldo/control_channel_attribution.py"
  - "scripts/suites/*_veldo_0136_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0136-owner-told-to-reply-to-the-request.md"
  - "specs/index.md"
  - "proof/VELDO-0136/*"
behavior_bearing: true
observability:
  logs: >
    Record each owner message that is not a reply to a presentation, the hint sent, and the pending
    requests it names, without message text.
  metrics: >
    Count hints sent, and owner messages refused as not a reply.
  traces: >
    Join each hint to the owner message and the pending presentations it names, by identity.
  error_taxonomy: >
    Distinguish not a reply, reply to a non-presentation message, and unavailable service; a hint never
    records an answer.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: When the current enrolled owner sends a message that does not reply to a presentation while
      a request of his is pending, the bot answers once with how to answer: reply to the request message,
      naming the pending request. Set and completeness: a plain message, a reply to the bot's help
      message, and a reply to another bot message, each with one and with two pending requests.
      Falsifier: send nothing for a plain message; the hint check must fail.
    falsified_by: >
      Send nothing for a plain message; the hint check must fail.
  - id: AC2
    text: >
      Claim: A hint never records an answer and never reaches anyone but the current enrolled owner.
      Set and completeness: the owner, a stranger, a revoked owner and a bot sender, each sending a plain
      message. Falsifier: record the plain message as the answer; the no-answer check must fail.
    falsified_by: >
      Record the plain message as the answer; the no-answer check must fail.
  - id: AC3
    text: >
      Claim: Repeated plain messages do not flood the owner: one hint per pending request until he
      answers it. Set and completeness: three plain messages for one pending request. Falsifier: hint on
      every message; the one-hint check must fail.
    falsified_by: >
      Hint on every message; the one-hint check must fail.
required_evidence: [unit, integration]
rollback: >
  Stop sending hints; owner messages that are not replies are refused silently, as before.
---

## Intent

An owner who types an answer without pressing Reply today gets silence while his request waits. He
should be told, once, to reply to the request message.

## Context

W99 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 3. Found by the
scoped review of VELDO-0066 on 2026-09-24: a message with no reply reference is refused as
`missing_reply_reference`, and a reply to a non-presentation bot message as `unknown_presentation`,
and neither tells the owner anything.

## Out of scope

Accepting an answer that is not a reply (binding stays exactly as VELDO-0066 defines it). Redelivery and
recovery (Release 2).

## What the reviewer judges

- Normal use: the owner answering in Telegram, sometimes without pressing Reply.
- Threat model: a stranger, a revoked owner or a bot receiving a hint, and a hint recorded as an answer.
  The owner's account, the bot's credentials and our store are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), Telegram outages
  and redelivery (Release 2).

## Notes

The hint is sent through the presenter's existing send path, so its receipt is kept like any other
message.

## History

2026-09-24: new draft, from the scoped review of VELDO-0066 (an owner who does not press Reply gets
silence).
