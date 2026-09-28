---
schema: veldo.spec/v1
id: VELDO-0178
title: The authenticated API serves the owner's conversations and their turns, and every turn's execution record is kept and served live only to the conversation's owner
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W138
plan_revision: 4
depends_on: [VELDO-0130, VELDO-0141, VELDO-0164, VELDO-0174, VELDO-0175, VELDO-0176, VELDO-0177]
placement: [contracts, engine, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_api*.py"
  - ".veldo/control_api*.py"
  - "engine/.veldo/control_conversation*.py"
  - ".veldo/control_conversation*.py"
  - "engine/.veldo/control_execution_record*.py"
  - ".veldo/control_execution_record*.py"
  - "engine/.veldo/control_service_api*.py"
  - ".veldo/control_service_api*.py"
  - "engine/.veldo/control_client_api*.py"
  - ".veldo/control_client_api*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0178_*.py"
  - "scripts/suites/71_veldo_0130_api.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0178-conversation-api-and-turn-records.md"
  - "specs/index.md"
  - "proof/VELDO-0178/*"
behavior_bearing: true
observability:
  logs: >
    Record each conversation route call with its principal, route, conversation id and outcome, and each
    record read of a turn with its dispatch; never message text, record payloads or a session cookie.
  metrics: >
    Count conversation route calls by route and outcome, and turn record reads refused for scope.
  traces: >
    Join each route call to the authority command it sent and each turn record read to its conversation.
  error_taxonomy: >
    Distinguish a caller who is not the conversation's owner (missing_authority:conversation_owner), an
    unknown conversation (invalid_input:conversation:unknown) and a stale version on a conversation command
    (stale_version).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The authenticated API lists the owner's conversations, serves each one's turns and replies,
      and sends his conversation commands, only for the conversation's owner. Set and completeness: The
      published ROUTES table gains `conversations.read` (GET, optional `conversation`), which lists the
      caller's conversations with id, status, role, turn count and last activity, or serves one with every
      turn's sequence, message, reply, outcome, dispatch id and account; and `conversations.open`,
      `conversations.close`, `conversations.set_role` and `conversations.attach_project` (POST, each with
      the conversation's version where it names one), which send VELDO-0174's, VELDO-0176's and VELDO-0177's
      typed commands; `messages.send` carries VELDO-0175's `conversation` field. Every conversation event
      (opened, turn waiting, turn started, turn ended, reply kept, closed) is on the events stream for the
      owner. Any other caller, a member of the same domain among them, is refused by name
      (missing_authority:conversation_owner) and sees no conversation. Falsifier: Scope conversation reads
      by domain membership, as project reads were before VELDO-0164, and the other-member row must fail on
      the served conversation.
    falsified_by: >
      Scope conversation reads by domain membership, as project reads were before VELDO-0164, and the
      other-member row must fail on the served conversation.
  - id: AC2
    text: >
      Claim: Every turn's run is kept in the execution record exactly as a project run is, redacted the same
      way, bound to its conversation and turn, and served live on the existing record routes only to the
      conversation's owner. Set and completeness: A turn's dispatch writes VELDO-0141's execution record with
      nothing dropped, with the record's header naming the conversation id and turn sequence, and the
      receiver's resolved-value replacement before the scanner (VELDO-0141 AC4). `runs.record` and
      `runs.record_stream` serve a turn's record from a cursor, live and after the run ends, to the
      conversation's owner; VELDO-0164's read scope, which decides a run by its project, decides a turn's
      record by its conversation, and a run with neither is served to nobody. The suite runs a turn whose
      fake engine prints a tool call, a command output with a resolved credential value and an error line,
      and reads the record as the owner and as another member. Falsifier: Decide a turn's record read by
      project alone, treating a run with no project as readable by every member, and the owner-only row
      must fail on the record served to the other member.
    falsified_by: >
      Decide a turn's record read by project alone, treating a run with no project as readable by every
      member, and the owner-only row must fail on the record served to the other member.
required_evidence: [unit, integration]
rollback: >
  Remove the conversation routes from the published table while keeping every record; the record routes
  keep serving project runs. No automatic rollback is authorized.
---

## Intent

Everything a conversation does is visible to the owner and to no one else: its turns, its replies and the
full live execution of each turn, through the same API the UI uses.

## Context

W138 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. VELDO-0130 owns
the API and its published ROUTES table, VELDO-0141 the execution record and its record routes, and
VELDO-0164 scopes reads to the reader's projects; a conversation has no project, so its scope is its
owner. The conversion route `conversations.make_project` is VELDO-0180's, and the UI screens are
VELDO-0179. A draft: only the owner marks it ready.

## Out of scope

Sharing a conversation with another member (Release 3); exporting a conversation; the UI (VELDO-0179).

## What the reviewer judges

- Normal use: the owner's phone lists his open conversations, opens one, shows each turn and its reply,
  and follows the running turn's record live.
- Threat model: another member of the domain reading the owner's conversation or a turn's record; a turn's
  record served unredacted or with lines dropped; a conversation command sent on a stale version.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); forged rows in
  our own store.

## Notes

The record is the same record every run keeps; only its binding and its read scope are new.

## History

2026-09-27: new draft for the owner's conversation requirement (Telegram, 2026-09-27). Only the owner
marks a specification ready.

2026-09-27, review of the drafts: the conversion route is VELDO-0180's own, since a conversation becomes a
project only on the owner's typed command; the commands' version is VELDO-0174 AC1's. Criteria unchanged.
Still a draft.
