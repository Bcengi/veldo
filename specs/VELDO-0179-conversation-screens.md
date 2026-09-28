---
schema: veldo.spec/v1
id: VELDO-0179
title: The UI's conversation screens let the owner start, continue, change the role of, attach a project to and close conversations on phone and desktop and watch every turn live as a terminal
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W139
plan_revision: 4
depends_on: [VELDO-0131, VELDO-0145, VELDO-0178]
placement: [loop, distribution]
protected_paths: []
footprint:
  - "engine/ui/**"
  - "packs/*/ui/**"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0179_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0179-conversation-screens.md"
  - "specs/index.md"
  - "proof/VELDO-0179/*"
behavior_bearing: true
observability:
  logs: >
    Record each conversation screen's API calls with route, outcome and latency in the UI's client log;
    never message text or a session cookie.
  metrics: >
    Count messages sent from the conversation screen, conversations opened and closed there, role changes
    and project attaches sent from it, and live terminal reconnects.
  traces: >
    Join each message sent from the screen to the turn it became and the record the screen followed.
  error_taxonomy: >
    Show each API refusal by its name on the screen (for example missing_authority:conversation_owner or
    stale_version) and never as a generic failure.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The owner starts, continues, changes the role of, attaches a project to and closes
      conversations in the UI, and every message and reply is shown as written, with the running turn's
      state, entirely through the API. Set and completeness: The
      React shell of VELDO-0145 gains a conversations list (open first, then closed, each with its opening
      words, role and last activity) and a conversation screen showing every turn in order with the owner's
      message, the reply and the outcome, a waiting or running marker on the current turn, and a message box
      that posts through `messages.send` with the `conversation` field; "New conversation" posts through
      `conversations.open`, and closing through `conversations.close`. A role control lists the default
      team's roles with the current one marked and sends `conversations.set_role`, and a project control
      lists the projects in his scope and sends `conversations.attach_project`, each with the conversation's
      version, so a stale one shows `stale_version`. The screen follows the events stream,
      so a reply to a turn sent from Telegram appears without a reload. Text is shown as the API serves it,
      never rendered as markup. The suite drives the built UI against the API with fake engines: open, send
      two messages, see both replies, reply once from a fake Telegram edge and see it, change the role
      (once on an older version), attach a fixture project, close. Falsifier: Render replies as HTML, and the shown-as-written row must
      fail on a reply holding a `<b>` tag; show the role control's refusal as a generic failure, and the
      stale-version row must fail on a screen that never names `stale_version`.
    falsified_by: >
      Render replies as HTML, and the shown-as-written row must fail on a reply holding a `<b>` tag; show
      the role control's refusal as a generic failure, and the stale-version row must fail on a screen that
      never names `stale_version`.
  - id: AC2
    text: >
      Claim: Each turn opens as a live terminal of its execution record, following the running turn as it
      happens, never a summary. Set and completeness: Selecting a turn opens VELDO-0145's run terminal on the
      turn's dispatch, read through `runs.record` and `runs.record_stream` from a cursor, with every line in
      sequence with its stream, receive time and redaction marks, live during the turn and complete after it
      with the record's line count and digest; the running turn's terminal opens from the conversation
      screen in one tap. The suite runs a turn whose fake engine prints a tool call, a command output and an
      error line slowly, and reads the screen's lines against the record. Falsifier: Show only the turn's
      reply in place of its record, and the terminal row must fail on the missing tool call line.
    falsified_by: >
      Show only the turn's reply in place of its record, and the terminal row must fail on the missing tool
      call line.
  - id: AC3
    text: >
      Claim: The conversation screens meet VELDO-0131's phone, desktop, accessibility and dependency rules,
      as VELDO-0145 AC4 applies them. Set and completeness: Render the list and the conversation screen at
      360px and 390px phone widths and 1280px and 1440px desktop widths in loading, empty, waiting, running,
      error and populated states, with no clipped primary action, overlapping controls or page-wide
      horizontal overflow and the message box reachable above the phone keyboard; run keyboard-only desktop
      and touch phone tasks with 44px primary touch targets, labeled controls, sufficient contrast and
      screen-reader names from the actual accessibility tree; check the lockfile and served assets against
      VELDO-0131 AC4's origin, license and tier rules. Falsifier: Hide the send action at 360px width, and
      the phone conversation check must fail.
    falsified_by: >
      Hide the send action at 360px width, and the phone conversation check must fail.
required_evidence: [unit, integration, ui_states]
rollback: >
  Hide the conversation screens while keeping every conversation; Telegram and the API are unchanged. No
  automatic rollback is authorized.
---

## Intent

The owner works in a conversation from his phone or desktop as easily as on Telegram, and watches what
each turn does, as he watches his assistant in the terminal today.

## Context

W139 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. VELDO-0145 owns
the React shell, the run terminal and the decisions screen under PLAN-0019 C16; VELDO-0178 the API it
reads. A draft: only the owner marks it ready.

## Out of scope

Attachments, search across conversations, and editing a sent message; the rest of VELDO-0131's screens.

## What the reviewer judges

- Normal use: on his phone the owner opens a conversation, writes, watches the running turn's terminal,
  reads the reply and writes again, attaches veldo and moves the conversation to his Codex role; later he continues the same conversation from Telegram and the screen
  shows it.
- Threat model: a reply rendered as markup, so text runs as page content; a screen that shows a summary in
  place of the record; a screen that reads anything other than the API; a role or project change applied
  over a newer record.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); browsers older
  than VELDO-0131's supported set.

## Notes

The terminal is VELDO-0145's component, reused; this specification adds the list and conversation screen.

## History

2026-09-27: new draft for the owner's conversation requirement (Telegram, 2026-09-27). Only the owner
marks a specification ready.

2026-09-27, review of the drafts: AC1 adds the role and project controls, which had only an API route;
depends_on adds VELDO-0131, whose rules AC3 applies. Still a draft.

2026-09-27: marked ready by the owner (Telegram 29301, "All ready otherwise"), with his two points applied: plain-words commands (29299) and smart add on the subscription instead of a paid API (29300).
