---
schema: veldo.spec/v1
id: VELDO-0176
title: The factory keeps each conversation's engine session and history, so a turn resumes it on any account of its engine, after an account limit and after a restart
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W136
plan_revision: 4
depends_on: [VELDO-0141, VELDO-0154, VELDO-0155, VELDO-0156, VELDO-0160, VELDO-0172, VELDO-0174]
placement: [engine, fleet, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_conversation*.py"
  - ".veldo/control_conversation*.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "engine/.veldo/control_engine_claude*.py"
  - ".veldo/control_engine_claude*.py"
  - "engine/.veldo/control_engine_codex*.py"
  - ".veldo/control_engine_codex*.py"
  - "engine/runtime/claude-qualification*.json"
  - ".veldo/runtime/claude-qualification*.json"
  - "engine/runtime/codex-qualification*.json"
  - ".veldo/runtime/codex-qualification*.json"
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_service*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0176_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0176-conversation-history-kept-by-the-factory.md"
  - "specs/index.md"
  - "proof/VELDO-0176/*"
behavior_bearing: true
observability:
  logs: >
    Record each session capture and placement with the conversation id, turn sequence, engine, session
    id, account and digest, each resumption with the session id the engine reported, and each history
    rendering with its turn count and digest; never session content.
  metrics: >
    Count turns resumed from a held session, turns started from a rendering, captures, and turns stopped
    by a history that is too large or a held session whose digest differs.
  traces: >
    Join each turn to the held session it resumed and the capture it produced, across accounts.
  error_taxonomy: >
    Distinguish a held session whose digest differs from its turn record
    (binding_mismatch:conversation_session), an engine that reported another session than the one placed
    (binding_mismatch:conversation_resume), and a rendering beyond the engine's qualified input bound
    (invalid_input:conversation_history:too_large).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The factory keeps each conversation's engine session itself, so every turn resumes it on
      whichever account of its engine the pool picks, and no session stays in an account profile. Set and
      completeness: After each turn the receiver captures the session state the engine wrote in the account
      profile: for Claude Code the session transcript of the result event's session id under the profile's
      projects directory for the workspace; for Codex the thread's rollout file under the profile's sessions
      directory. It keeps the capture under the conversation's directory at mode 0600, binds its digest to
      the turn record, and removes it from the profile. Before the next turn it checks the digest, places
      the capture at the same relative place in the chosen account's profile and launches with the engine's
      resume option naming the session id (Claude Code's `resume`, Codex's `exec resume`), each qualified
      on the pinned version and recorded in its qualification record; the meter's `resumes` then charges
      only the difference. An engine that reports another session id is stopped by name
      (binding_mismatch:conversation_resume). The suite runs turn 1 on account A and turn 2 on account B,
      with fake engines that read the placed file. Falsifier: Skip placing the held session in B's profile,
      and the any-account row must fail on the new session id turn 2 reports.
    falsified_by: >
      Skip placing the held session in B's profile, and the any-account row must fail on the new session
      id turn 2 reports.
  - id: AC2
    text: >
      Claim: A turn stopped at its account's limit continues on another account of its engine from where it
      stopped, and after a factory restart the owner's next message resumes the conversation. Set and
      completeness: For a turn that ended `account_limit`, AC1's capture is taken as for any turn, and the
      loop's re-run of VELDO-0154 AC3, under VELDO-0160 AC3's re-run-or-ask decision, dispatches the same
      turn under a new dispatch identity on another account, resuming that capture with an input saying the
      previous run stopped at an account limit. When every account of the engine is at its limit, the turn
      waits for the first reset (VELDO-0154's reset wake), and the owner is told the reset time on his
      channel. At a restart, a turn that was running is `outcome_unknown` (VELDO-0154 AC2) and the owner is
      told; the last capture stays, and his next message resumes from it. The suite limits account A in the
      middle of a turn, then restarts the service between two turns. Falsifier: Discard the capture of a
      turn that ended `account_limit`, and the continues-after-a-limit row must fail on a fresh session in
      place of the captured one.
    falsified_by: >
      Discard the capture of a turn that ended `account_limit`, and the continues-after-a-limit row must
      fail on a fresh session in place of the captured one.
  - id: AC3
    text: >
      Claim: A conversation changes engine only when the owner changes its role to one on the other engine,
      and that engine's first turn starts from the factory's history of the conversation, built from the
      redacted execution records. Set and completeness: The owner's `set_conversation_role` command (from
      the API or a message route) names a role of his team; a role on the same engine keeps resuming the
      held session. For a role on the other engine, the next turn starts a fresh session whose first input
      is the rendering: every earlier turn in order, with the owner's message, the tool calls with their
      inputs and results and the reply, all as their execution records keep them after redaction (VELDO-0141
      AC4), never from the held session. A rendering beyond the engine's qualified input bound stops the
      turn by name (invalid_input:conversation_history:too_large) and tells the owner, launching nothing.
      The earlier engine's held session is kept, so a change back resumes it. A held session whose digest
      differs from its turn record is refused by name (binding_mismatch:conversation_session) and never
      replaced by a rendering. The suite's fake Claude Code tool result prints a resolved credential value.
      Falsifier: Build the rendering from the held session, and the redaction row must fail on the
      credential value in the Codex turn's first input.
    falsified_by: >
      Build the rendering from the held session, and the redaction row must fail on the credential value in
      the Codex turn's first input.
required_evidence: [unit, integration]
rollback: >
  Stop placing held sessions and start every turn from the rendering while keeping every capture and
  record. No automatic rollback is authorized.
---

## Intent

A conversation keeps its whole context for as long as the owner wants, whichever of his accounts runs
the next turn, when an account reaches its limit in the middle of a turn, and after the factory restarts.

## Context

W136 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. Each account is a
separate engine profile (VELDO-0160; Claude Code's CLAUDE_CONFIG_DIR, Codex's CODEX_HOME), and both engines
keep a session inside the profile that ran it, so without this a conversation would forget everything
when the pool moves it to another account. The launch contract already carries the session a follow-on
resumes (`resume`), and the meters charge only the difference (control_engine_claude and
control_engine_codex), but nothing places a session for another account or launches with the resume
option. The rendering reads VELDO-0141's execution records. A draft: only the owner marks it ready.

## Out of scope

Compacting a history that is too large for a fresh session (Release 2; the engine's own compaction
applies inside a held session); moving a conversation to the other engine without the owner's role
change, which would change its tools silently (C15); recovery matrices for a capture interrupted by a
crash (Release 2).

## What the reviewer judges

- Normal use: turn 1 runs on the first Claude Code account, turn 2 on the third, and the reply shows it
  remembers turn 1; the second account hits its weekly limit in the middle of turn 5, which continues on
  another account; after a restart the next message continues; later the owner moves the conversation to
  his Codex role and the first Codex turn knows the earlier turns.
- Threat model: a turn resuming another conversation's session; a session left in an account profile, so
  that account's later runs see it; a held session swapped or edited between turns; a credential value
  carried into another engine's input; a limited turn restarted from nothing.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); forged rows in
  our own store and files planted in the state root; engine versions other than the pinned ones.

## Notes

The held session is kept only under the state root with the store's file rules, never served by the API,
never exported and never in proof; it holds what the engine kept, as the profile holds it today. What
crosses to the other engine is only the redacted record.

## History

2026-09-27: new draft for the owner's conversation requirement (Telegram, 2026-09-27). Only the owner
marks a specification ready.
