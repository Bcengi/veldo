---
schema: veldo.spec/v1
id: VELDO-0181
title: A decision a conversation raises goes through the existing Telegram decision flow, only the conversation's owner drives it, and nothing a turn produces carries authority
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W141
plan_revision: 4
depends_on: [VELDO-0065, VELDO-0066, VELDO-0068, VELDO-0073, VELDO-0136, VELDO-0160, VELDO-0175, VELDO-0180]
placement: [contracts, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_conversation*.py"
  - ".veldo/control_conversation*.py"
  - "engine/.veldo/control_intake*.py"
  - ".veldo/control_intake*.py"
  - "engine/.veldo/control_request_settlement*.py"
  - ".veldo/control_request_settlement*.py"
  - "engine/.veldo/control_channel_presentation*.py"
  - ".veldo/control_channel_presentation*.py"
  - "engine/.veldo/control_account_limit*.py"
  - ".veldo/control_account_limit*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0181_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0181-conversation-decisions-and-owner-authority.md"
  - "specs/index.md"
  - "proof/VELDO-0181/*"
behavior_bearing: true
observability:
  logs: >
    Record each decision a conversation raises with its kind, request, presentation and settlement, and
    each refused conversation message or turn output with the rule that refused it; never message text.
  metrics: >
    Count conversation decisions by kind and settlement, messages refused for authority, and turn outputs
    refused as authority.
  traces: >
    Join each conversation decision to its turn, its presentation receipt and the answer that settled it.
  error_taxonomy: >
    Distinguish a message from anyone but the conversation's owner (missing_authority:conversation_owner),
    an answer or approval found in a turn's output (invalid_input:turn_output:authority) and an answer that
    does not reply to the presentation (VELDO-0136's refusal).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every factory decision a conversation raises is presented through the existing decision flow
      and settles only on the owner's reply to that presentation or his inline answer in the UI, at most
      once. Set and completeness: The decisions a conversation raises are the re-run-or-ask of a turn
      stopped at its account limit (VELDO-0160 AC3), the unclear route question (VELDO-0175 AC2) and a new
      project's one answer (VELDO-0143 through VELDO-0180 AC1). Each is a versioned presentation (VELDO-0065)
      sent on the chat he wrote from and served in the decisions screen, attributed canonically
      (VELDO-0066) and settled once (VELDO-0068) across Telegram and the UI. A Telegram reply to a decision
      presentation is an answer to that decision, never a turn of the conversation; an answer that replies
      to no presentation gets VELDO-0136's reply-to-the-request message. The turn it concerns waits until it
      settles. Falsifier: Treat a reply to a decision presentation sent in a conversation as the
      conversation's next turn, and the settles-by-reply row must fail on the unsettled request.
    falsified_by: >
      Treat a reply to a decision presentation sent in a conversation as the conversation's next turn, and
      the settles-by-reply row must fail on the unsettled request.
  - id: AC2
    text: >
      Claim: Only the conversation's owner opens, continues, changes or closes it, and nothing a turn
      produces settles a decision, accepts an objective, admits work or widens a role. Set and completeness:
      Every conversation command and continuing message is checked against the canonical attribution of the
      message or API session (VELDO-0066) and the conversation's owner; any other principal is refused by
      name (missing_authority:conversation_owner) and starts nothing. A turn's outputs (its reply, its tool
      results and its protocol messages) never reach a settlement, an acceptance, an admission or a role
      save: the only proposal a turn makes is VELDO-0180's route document, taken under that criterion's own
      check, and an answer or approval document found in a turn's output is refused by name
      (invalid_input:turn_output:authority) and kept as text. The suite's fake engine ends a turn with a
      valid answer document for a pending request, an objective acceptance and a role save, and a second
      member replies to the conversation. Falsifier: Accept an answer document found in a turn's final
      message, and the no-authority-from-output row must fail on the settled request.
    falsified_by: >
      Accept an answer document found in a turn's final message, and the no-authority-from-output row must
      fail on the settled request.
required_evidence: [unit, integration]
rollback: >
  Stop raising conversation decisions and hold each affected turn stopped by name while keeping every
  record. No automatic rollback is authorized.
---

## Intent

A conversation gets no new power: every decision it needs is asked the way the factory already asks, the
owner answers it the way he already answers, and a model's output never stands in for his answer.

## Context

W141 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. The factory's
threat model and owner-only authority apply unchanged: models reason and propose, and authenticated
deterministic services authorize and commit (PLAN-0019 Intent). Decisions already present through
VELDO-0065, attribute through VELDO-0066 and settle through VELDO-0068 on Telegram (VELDO-0073) and the UI.
A draft: only the owner marks it ready.

## Out of scope

Approvals the owner gives in plain words inside the conversation, such as "yes, send it" in reply to a
question the turn asked: that reply is his next turn and the tool acts through its own configured
credentials, as for his assistant today, with no factory decision; decisions of other members (Release 3).

## What the reviewer judges

- Normal use: a turn stopped at an account limit after a write call asks the owner whether to re-run; he
  replies "yes" to that message and the turn continues on another account; later a turn asks "shall I
  send it?" in its reply, and his "yes" is simply his next turn.
- Threat model: a tool result or web page carrying text that imitates the owner's approval; a turn's
  output shaped as an answer document; another member continuing or closing the owner's conversation; a
  reply to a decision presentation taken as a turn, so the decision never settles.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); forged rows in
  our own store.

## Notes

The owner's plain-word approvals stay conversational on purpose: they are how he works with his assistant
today, and turning each into a factory decision would add friction the terminal does not have.

## History

2026-09-27: new draft for the owner's conversation requirement (Telegram, 2026-09-27). Only the owner
marks a specification ready.
