---
schema: veldo.spec/v1
id: VELDO-0187
title: Every conversation turn reaches claude-mem's session history through a factory-side feed built from the redacted record, so the owner's assistant and later conversations find it
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W147
plan_revision: 4
depends_on: [VELDO-0141, VELDO-0155, VELDO-0174, VELDO-0176, VELDO-0182, VELDO-0183]
placement: [contracts, engine, fleet]
protected_paths: []
footprint:
  - "engine/.veldo/control_memory*.py"
  - ".veldo/control_memory*.py"
  - "engine/.veldo/control_conversation*.py"
  - ".veldo/control_conversation*.py"
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_service*.py"
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "engine/runtime/claude-mem-qualification*.json"
  - ".veldo/runtime/claude-mem-qualification*.json"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0187_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0187-conversation-turns-captured-into-claude-mem.md"
  - "specs/index.md"
  - "proof/VELDO-0187/*"
behavior_bearing: true
observability:
  logs: >
    Record each feed of a turn with the conversation id, turn sequence, claude-mem session, the requests
    sent with their digests and the worker's answers, and each turn's capture state (pending, captured, not
    captured with its reason); never turn content.
  metrics: >
    Count turns captured, turns pending, turns not captured by reason, requests sent by kind, and feeds
    sent late after the worker returned.
  traces: >
    Join each feed to its turn, the execution record it was built from and the claude-mem qualification
    record it used.
  error_taxonomy: >
    Distinguish an installed claude-mem version the qualification record does not list
    (missing_evidence:claude_mem_version:<version>), a worker address that is not a loopback address
    (invalid_input:claude_mem:not_loopback) and a worker that does not answer
    (unavailable_service:claude_mem_worker), which leaves the feed pending, never dropped.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The feed writes to claude-mem only through the interface claude-mem's own hooks use, qualified
      on the installed version, and a version that is not qualified gets no feed. Set and completeness: A
      qualification record `runtime/claude-mem-qualification.json` lists each qualified claude-mem version
      with the digests of its hook scripts, every request those hooks send its worker (the session's start,
      each user prompt, each tool observation and the end-of-session summary request) with its fields, and
      the worker's loopback address; each is read from that version's own hook code at qualification. The
      feed sends only those requests, only to a loopback address (else invalid_input:claude_mem:not_loopback)
      and never with a credential or any name VELDO-0183 AC2 refuses as a paid API. Setup reads the
      installed version from VELDO-0182's claude-mem part; for a version the record does not list, every
      turn is recorded not captured by name (missing_evidence:claude_mem_version:<version>) and nothing is
      sent. The suite runs a fixture worker on loopback at a qualified and an unqualified version. Falsifier:
      Send the feed whatever the installed version, and the unqualified-version row must fail on the
      requests the fixture worker received.
    falsified_by: >
      Send the feed whatever the installed version, and the unqualified-version row must fail on the
      requests the fixture worker received.
  - id: AC2
    text: >
      Claim: After every turn, on either engine and any account, the feed sends the turn to claude-mem as
      part of its conversation's one claude-mem session, built from the turn's redacted execution record and
      never from the held session. Set and completeness: At each turn's end, whatever its outcome, the feed
      sends the owner's message as the prompt, each tool call with its input and result as an observation
      and the reply with the summary request, in the record's order, under one claude-mem session per
      conversation that the conversation's first feed starts, so turns run on different accounts or engines
      (VELDO-0176) join the same session. Every value comes from the execution record after redaction
      (VELDO-0141 AC4), and each request is kept in the conversation's feed log under its directory with
      its digest and the worker's answer. The suite runs turn 1 on a Claude Code account and turn 2 on the
      Codex account, whose fake tool result prints a resolved credential value, against the fixture worker.
      Falsifier: Build the feed from the held session, and the redaction row must fail on the credential
      value in the fixture worker's observation.
    falsified_by: >
      Build the feed from the held session, and the redaction row must fail on the credential value in the
      fixture worker's observation.
  - id: AC3
    text: >
      Claim: What the feed sent is found by claude-mem's own search from a later conversation and from the
      owner's assistant, and a turn the worker could not take is sent later in order, never lost. Set and
      completeness: A later conversation's claude-mem search tool (VELDO-0183 AC1's catalog server) and the
      fixture's own search server, started as the owner's assistant starts it, both find turn 1's content.
      When the worker does not answer, the turn's feed stays pending in the conversation's directory
      (unavailable_service:claude_mem_worker) and is sent, in turn order, at the next turn's end or the next
      loop pass after the worker answers; the turn record shows `pending`, then `captured`. The suite stops
      the fixture worker during turn 1 and starts it before turn 2 ends. Falsifier: Drop a feed the worker
      did not take, and the pending row must fail on turn 2 found while turn 1 is not.
    falsified_by: >
      Drop a feed the worker did not take, and the pending row must fail on turn 2 found while turn 1 is
      not.
required_evidence: [unit, integration]
rollback: >
  Stop sending feeds while keeping every feed log and pending feed; what claude-mem already holds is the
  owner's and is never changed by a rollback. No automatic rollback is authorized.
---

## Intent

The owner's assistant finds what happened in his factory conversations the same way it finds what
happened in its own sessions, and a later conversation finds it too, because every turn lands in the
session history claude-mem keeps.

## Context

W147 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. The owner's memory
requirement (Telegram 29294, lead agreed) makes claude-mem one of the memory parts conversations use, and
the review of the drafts on 2026-09-27 ruled that capturing conversation turns into it is MVP function,
not a later release. claude-mem is a Claude Code plugin: its code is not in our repositories, and it
captures a session from Claude Code hooks, which VELDO-0155's everything-off baseline switches off for
every run, so a factory run never triggers them. The factory therefore feeds the same store itself, through
the same worker interface the hooks use, so claude-mem remains the one writer of its own store; nothing
writes its database directly. The interface is read from the installed version's hook code when it is
qualified (AC1), the way engine options are qualified on a pinned version. The feed is built from the
execution record (VELDO-0141), which already holds every prompt, tool call and reply after redaction.
VELDO-0183 makes claude-mem's search server a catalog server and VELDO-0182 names where it lives. A draft:
only the owner marks it ready.

## Out of scope

Feeding project runs' turns (a later specification may give a role the feed); how claude-mem's worker
summarizes what it receives, which is its own, as it is for the owner's assistant today; starting or
supervising claude-mem's worker (VELDO-0183's filed note); requalifying a new claude-mem version beyond
recording it (the same rule as the engines).

## What the reviewer judges

- Normal use: the owner works through a problem in a factory conversation in the morning; that evening
  his assistant's claude-mem search finds what was tried and what worked, and the next day a new
  conversation finds it too; one turn ran while claude-mem's worker was down, and it appears once the
  worker is back.
- Threat model: a credential value carried into claude-mem through the held session; a feed sent to a
  non-loopback address or with a paid-API name; a feed sent to an unqualified version whose interface
  differs; a turn silently lost when the worker is down; turns of one conversation split across sessions
  when it moves accounts or engines; the factory writing claude-mem's database around its worker.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); faults inside
  claude-mem's own code; forged rows in our own store.

## Notes

The feed is engine-independent because it reads the record, not an engine's hook, so a Codex turn is
captured exactly as a Claude Code turn is.

## History

2026-09-27: new draft from the review of the conversation drafts, which ruled claude-mem's capture of
factory turns MVP function (the lead's decision). Only the owner marks a specification ready.
