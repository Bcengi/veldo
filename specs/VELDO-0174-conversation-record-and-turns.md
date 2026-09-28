---
schema: veldo.spec/v1
id: VELDO-0174
title: A conversation is a second kind of work beside projects, open until the owner closes it, and each of his messages in it is one turn the factory loop runs in order
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W134
plan_revision: 4
depends_on: [VELDO-0039, VELDO-0127, VELDO-0154, VELDO-0160, VELDO-0162]
placement: [contracts, loop, fleet]
protected_paths: []
footprint:
  - "engine/.veldo/control_conversation*.py"
  - ".veldo/control_conversation*.py"
  - "engine/.veldo/control_dispatch.py"
  - ".veldo/control_dispatch.py"
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_service*.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0174_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0174-conversation-record-and-turns.md"
  - "specs/index.md"
  - "proof/VELDO-0174/*"
behavior_bearing: true
observability:
  logs: >
    Record each conversation command (open, close) and each turn's lifecycle (waiting, dispatched,
    ended with its outcome) with the conversation id, turn sequence, dispatch id, role revision and
    account; never the message text or a credential.
  metrics: >
    Count open conversations, turns by outcome, turns waiting, and turns offered before project stations
    in a pass.
  traces: >
    Join each turn to the owner's intake command that caused it, its dispatch, its account and the loop
    pass that offered it.
  error_taxonomy: >
    Distinguish a command on a conversation that does not exist (invalid_input:conversation:unknown), a
    command by anyone but its owner (missing_authority:conversation_owner), a turn for a closed
    conversation (stale_subject:conversation_closed) and a second active turn of one conversation
    (stale_subject:conversation_turn_active).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The owner opens a conversation by a typed authority command, and it is a record of its own
      beside projects, owned by him, that stays open across days and factory restarts until he closes it.
      Set and completeness: The authority's `open_conversation` command, reached from intake (VELDO-0175)
      and the API (VELDO-0178), writes one conversation record in the store: its id, domain, owner
      principal, role name (a role of his team, VELDO-0162: the one he names, else `assistant`), status
      `open`, the digest of the intake command that opened it, and its directory under the state root. The `close_conversation` command sets `closed` and is accepted only from the
      conversation's owner; anyone else is refused by name (missing_authority:conversation_owner) and
      nothing changes. A conversation is not a project: it has no repository, backlog, charter or trunk,
      and no project command accepts its id. The suite opens a conversation, stops and starts the
      authority service over the same store, and reads the record back unchanged and open; it closes it as
      another member and then as the owner. Falsifier: Keep conversation records in the service's memory
      instead of the store, and the after-restart row must fail on the absent record.
    falsified_by: >
      Keep conversation records in the service's memory instead of the store, and the after-restart row
      must fail on the absent record.
  - id: AC2
    text: >
      Claim: Each owner message in an open conversation becomes one turn, and the factory loop runs a
      conversation's turns one at a time in the order of his messages, each on the account pool with the
      role's current accepted revision. Set and completeness: A turn record names its conversation, its
      sequence, the intake command of the message, and once dispatched its dispatch id, role revision,
      account and outcome. A turn is dispatched through the Runner as a VELDO-0039 dispatch whose subject
      kind is `conversation` and whose station is `turn`, so the one active dispatch per subject and station
      holds one running turn per conversation; a message that arrives while a turn runs waits as the next
      turn. A loop pass (VELDO-0154 AC1, woken by the message's commit or the running turn's end) offers
      the next waiting turn of every open conversation; the dispatch binds the role's accepted revision at
      that moment (VELDO-0127 AC3), so an edit the owner saves applies from the next turn. Before spawn the
      dispatch checks the conversation is still open, and a closed one is refused by name
      (stale_subject:conversation_closed) with nothing started. The suite sends three messages to one
      conversation within one running turn: three turns with sequences 1 to 3, each dispatched only after
      the one before ended, on fake `claude` and `codex` executables that print the installed CLI's
      output shape (VELDO-0172). Falsifier: Offer every waiting turn of a conversation in the same pass,
      and the one-at-a-time row must fail on two running dispatches of one conversation.
    falsified_by: >
      Offer every waiting turn of a conversation in the same pass, and the one-at-a-time row must fail on
      two running dispatches of one conversation.
  - id: AC3
    text: >
      Claim: Several conversations run at the same time, with each other and with project work, on the
      shared account pool, and a waiting turn is offered before project stations because the owner is
      waiting on it. Set and completeness: In a pass, the waiting turns of all open conversations are
      offered first, in the order their messages arrived, then every eligible unit and next station as
      VELDO-0154 AC1 offers them; no running run is stopped to make room, and one conversation's turn never
      waits on another conversation's turn, only on a free account slot (VELDO-0160 AC4). The suite opens
      three conversations with three free slots and one project unit waiting: all three turns run at once;
      with one free slot and both a waiting turn and a waiting build station, the turn takes the slot and
      the build station takes the next free slot. Falsifier: Order the pass by unit order alone, and the
      turn-first row must fail when the one free slot goes to the build station.
    falsified_by: >
      Order the pass by unit order alone, and the turn-first row must fail when the one free slot goes to
      the build station.
required_evidence: [unit, integration]
rollback: >
  Stop offering conversation turns in the loop while keeping every conversation and turn record; project
  work is unchanged. No automatic rollback is authorized.
---

## Intent

The owner works with his assistant in back and forth conversations that keep their context and solve a
problem without becoming a project. The factory needs that as a second kind of work beside projects: he
opens a conversation, each of his messages in it is one turn, and it stays open as long as he wants.

## Context

W134 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. The owner's
requirement (Telegram, 2026-09-27): "just like I work with Ava now, I need to be able to do the same. A
lot of stuff happens as back and forth retaining context, without becoming a project but solving a
problem I want it to solve. So not just a question, but more." It supersedes and contains the smaller
"the factory answers a question from a project's code and history" draft he agreed to earlier that day
(a conversation attached to a project, VELDO-0177 AC3). This specification owns the conversation record,
its turns and their place in the factory loop. Starting and continuing from Telegram and the UI is
VELDO-0175; history and resumption on any account VELDO-0176; the workspace and tools VELDO-0177; the API
VELDO-0178; the UI VELDO-0179; turning one into a project VELDO-0180; decisions and authority VELDO-0181;
memory VELDO-0182 to VELDO-0184. A draft: only the owner marks it ready.

## Out of scope

A priority between conversations beyond message order; a limit on how many conversations are open;
archiving or deleting a closed conversation (its records stay); recovery of a turn interrupted by a
crash beyond VELDO-0154 AC2's `outcome_unknown` (Release 2).

## What the reviewer judges

- Normal use: the owner opens a conversation, sends several messages over two days with a factory
  restart between them, and each becomes one turn run in order; two other conversations and a project
  build run at the same time.
- Threat model: two turns of one conversation running at once and writing the same workspace; a turn
  dispatched for a closed conversation; a conversation closed or opened by someone other than its owner;
  a conversation id accepted by a project command; a conversation lost at a restart.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), such as the
  owner closing a conversation while its turn is being spawned (the turn runs and its reply is kept);
  forged rows in our own store.

## Notes

A conversation turn is not a unit: it is never claimed, has no station contract of a pipeline, and the
project check of VELDO-0169 does not apply to it; its own check is the conversation's status and owner.
Offering turns first is a choice for the owner's waiting time; it never pre-empts running work.
VELDO-0177 AC2 seeds the `assistant` role; until it lands, this specification's suite supplies a fixture
role.

## History

2026-09-27: new draft for the owner's conversation requirement (Telegram, 2026-09-27). Only the owner
marks a specification ready.
