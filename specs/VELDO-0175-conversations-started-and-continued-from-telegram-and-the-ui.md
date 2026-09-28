---
schema: veldo.spec/v1
id: VELDO-0175
title: The owner starts a conversation from Telegram or the UI, continues it by replying to any of its messages or writing in its screen, steers it by typed commands, and gets every reply where he wrote
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W135
plan_revision: 4
depends_on: [VELDO-0126, VELDO-0128, VELDO-0130, VELDO-0136, VELDO-0152, VELDO-0168, VELDO-0174, VELDO-0176, VELDO-0177]
placement: [contracts, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_intake*.py"
  - ".veldo/control_intake*.py"
  - "engine/.veldo/control_conversation*.py"
  - ".veldo/control_conversation*.py"
  - "engine/.veldo/control_project*.py"
  - ".veldo/control_project*.py"
  - "engine/.veldo/control_workflow_cycle*.py"
  - ".veldo/control_workflow_cycle*.py"
  - "engine/.veldo/control_telegram_report*.py"
  - ".veldo/control_telegram_report*.py"
  - "engine/.veldo/control_service_channel*.py"
  - ".veldo/control_service_channel*.py"
  - "engine/.veldo/control_api.py"
  - ".veldo/control_api.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0175_*.py"
  - "scripts/suites/68_veldo_0126_intake.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0175-conversations-started-and-continued-from-telegram-and-the-ui.md"
  - "specs/index.md"
  - "proof/VELDO-0175/*"
behavior_bearing: true
observability:
  logs: >
    Record how intake decided each conversation message (a reply, a conversation field, a typed command,
    or a factory PM route) with the conversation id and turn sequence or command, and each reply part sent
    with its chat and message id; never the text.
  metrics: >
    Count conversation messages by how they were decided, typed commands by kind and outcome,
    conversations opened by route, reply parts sent, and replies to a closed or foreign conversation
    refused.
  traces: >
    Join each sent reply part to its turn, and each continuing message to the sent message it replied to.
  error_taxonomy: >
    Distinguish a reply or conversation field naming a conversation the sender does not own
    (missing_authority:conversation_owner), one naming a closed conversation
    (stale_subject:conversation_closed), a route naming an open conversation that is not the sender's
    (invalid_input:route:conversation) and a typed command that replies to no conversation message or
    names no role or project of his (invalid_input:conversation_command:<reason>).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A Telegram reply to any message the factory sent in a conversation, or an API message naming
      the conversation, continues that conversation at intake as its next turn, with no factory PM run and
      no question. Set and completeness: The factory records every message it sends in a conversation (AC3)
      with its bot, chat and message id, bound to the conversation and turn. Intake resolves a Telegram
      message's `reply_to_message_id` against those records before the proposal and question records it
      reads today, and the `messages.send` route gains an optional `conversation` field beside `project` and
      `clarifies`. Either one, from the conversation's owner, becomes the next turn of VELDO-0174 AC2 and
      nothing else; from anyone else it is refused by name (missing_authority:conversation_owner) and a
      closed conversation's is refused (stale_subject:conversation_closed), each with one line to the sender
      on the channel he wrote on and no turn. The suite replies to the second of three reply parts, and posts
      with the field. Falsifier: Resolve a reply only against proposals and questions, as intake does
      today, and the reply-continues row must fail on an inbox proposal in place of the turn.
    falsified_by: >
      Resolve a reply only against proposals and questions, as intake does today, and the reply-continues
      row must fail on an inbox proposal in place of the turn.
  - id: AC2
    text: >
      Claim: A message that no ticket key, project field, conversation field or reply decides goes to the
      factory project's PM, whose routes now include a new conversation and one of the sender's open
      conversations, and such a route opens or continues that conversation with the message as its turn.
      Set and completeness: VELDO-0152 AC3's three routes become five: a new project, an existing project, a
      new conversation, an open conversation named by id, and unclear. The PM run's input lists the
      sender's open conversations with their first message's opening words as candidates, beside his
      projects. A new-conversation route runs VELDO-0174 AC1's open command with the message as turn 1; an
      open-conversation route makes it that conversation's next turn; in both the inbox proposal is retired
      in state `ROUTED`, pointing at the conversation. The unclear question also offers "a new conversation"
      and his open conversations. A route naming a conversation that is not an open one of the sender's is
      refused by name (invalid_input:route:conversation) and changes nothing. The suite drives each of the
      five routes from `AWAITING_ROUTE` with the route document supplied as the fake PM run's final message.
      Falsifier: Carry out a new-conversation route as a new-project route, and the new-conversation row
      must fail on the `NEW_PROJECT` state.
    falsified_by: >
      Carry out a new-conversation route as a new-project route, and the new-conversation row must fail on
      the `NEW_PROJECT` state.
  - id: AC3
    text: >
      Claim: Every turn's reply reaches the owner as the engine wrote it, on Telegram when his message came
      from Telegram and always in the conversation's API read, as messages he can reply to. Set and
      completeness: A turn's reply is its engine's final result text (VELDO-0060 and VELDO-0061 terminal
      records). It is kept on the turn record and, for a turn whose message came from Telegram, sent to the
      chat he wrote from through the Telegram edge with VELDO-0168's text rules, split in order into parts
      that fit one Telegram message, the first a reply to his message; every part is recorded as AC1 reads.
      A turn that ends with no result text (failed, `account_limit`, `outcome_unknown`) sends one status
      line naming the outcome and what happens next in place of a reply. The suite's fake engine prints a
      reply longer than two Telegram messages. Falsifier: Record only the first part's message id, and the
      reply-to-the-last-part row must fail on an inbox proposal in place of the next turn.
    falsified_by: >
      Record only the first part's message id, and the reply-to-the-last-part row must fail on an inbox
      proposal in place of the next turn.
  - id: AC4
    text: >
      Claim: The owner changes a conversation's role, attaches one of his projects to it or closes it from
      Telegram by a command in reply to any of its messages, typed as a slash command or said in his own
      words, and a command is never a turn and is taken from no one else. Set and completeness: A Telegram message that replies to one of the
      conversation's sent messages (AC1) and whose text starts with `/role <role>`, `/attach <project>` or
      `/close`, or whose words the factory project's PM (VELDO-0152, Claude Code or Codex) reads as meaning
      one of them (owner, Telegram 29299: "you should understand if same meaning"), is that conversation's
      command; the PM reads only the owner's own message, never a turn's output, and a reply it reads as
      none of them is the next turn: intake sends the owner's `set_conversation_role`
      (VELDO-0176 AC3), `attach_project` (VELDO-0177 AC3) or `close_conversation` (VELDO-0174 AC1) with the
      conversation's current version and the name exactly as he typed it, answers with one line naming
      what changed, and makes no turn. `/project <name>` is VELDO-0180 AC1's. A command from anyone but
      the owner is refused by name (missing_authority:conversation_owner), and one that replies to no
      conversation message or names no role of the default team or project in his scope is refused by name
      (invalid_input:conversation_command:<reason>), each with one line and nothing changed. The suite
      sends each command as the owner, in slash form and in plain words ("switch this to Codex", "we are
      done here"), as another member, with no reply and with an unknown role.
      Falsifier: Take every reply to a conversation message as its next turn, as AC1 alone does, and the
      command row must fail on a turn whose message is `/role assistant_codex` in place of the role change.
    falsified_by: >
      Take every reply to a conversation message as its next turn, as AC1 alone does, and the command row
      must fail on a turn whose message is `/role assistant_codex` in place of the role change.
required_evidence: [unit, integration]
rollback: >
  Stop resolving replies and routes to conversations while keeping every record; messages then go to the
  factory project's PM as before. No automatic rollback is authorized.
---

## Intent

The owner starts a conversation the way he writes to his assistant today, by writing, and continues it by
replying, from Telegram or the UI, and each reply comes back where he wrote. From his phone he also
changes its role, attaches a project and closes it without leaving the chat.

## Context

W135 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. Intake already
resolves a Telegram reply to a presentation it sent (control_intake `_replied_proposal`), and VELDO-0152
sends every undecided message to the factory project's PM, which records one of three routes. This
specification adds the conversation to both: a reply or field decides a conversation deterministically,
and the PM gains two routes. Telegram has no other place to change a conversation, so AC4's typed
commands carry the role change, the project attach and the close that the API and the UI send as routes
(VELDO-0178, VELDO-0179). The UI's message box posts through `messages.send` (VELDO-0179). A draft: only
the owner marks it ready.

## Out of scope

Channels other than Telegram and the API; attachments and images in a conversation message (filed for
Release 4 channels); editing a sent message; the UI screen (VELDO-0179).

## What the reviewer judges

- Normal use: the owner writes "why did yesterday's Google Ads spend jump?" on Telegram; the factory PM
  routes it to a new conversation; the reply comes back as a reply to his message; he replies to it with a
  follow-up, and that continues the same conversation with no PM run; later he replies `/role
  assistant_codex` and the next turn runs on Codex.
- Threat model: a reply from another member continuing the owner's conversation; a reply to a closed
  conversation starting work; a route that puts a message into someone else's conversation; a reply part
  whose reply is not recognized, so the follow-up loses its conversation; a reply shown altered; a typed
  command run as a turn, or sent by another member.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), such as a reply
  to a message sent before a Telegram edge re-enrollment; forged rows in our own store.

## Notes

A reply to a decision presentation inside a conversation stays an answer to that decision (VELDO-0181
AC1); only the conversation's own reply parts continue it, and a typed command in such a reply is the
command, never a turn.

## History

2026-09-27: new draft for the owner's conversation requirement (Telegram, 2026-09-27). Only the owner
marks a specification ready.

2026-09-27, review of the drafts: AC4 adds the Telegram typed commands `/role`, `/attach` and `/close`,
since the role change and the project attach had only an API route; depends_on adds VELDO-0176 and
VELDO-0177, whose commands they send. Still a draft.

2026-09-27: marked ready by the owner (Telegram 29301, "All ready otherwise"), with his two points applied: plain-words commands (29299) and smart add on the subscription instead of a paid API (29300).
