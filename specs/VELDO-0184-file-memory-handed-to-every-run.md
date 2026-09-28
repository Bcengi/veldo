---
schema: veldo.spec/v1
id: VELDO-0184
title: The file memory directory is handed to every run whose role lists it, on either engine and any account, and its index load and every memory file read and write are in the record
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W144
plan_revision: 4
depends_on: [VELDO-0127, VELDO-0141, VELDO-0155, VELDO-0156, VELDO-0177, VELDO-0182]
placement: [fleet, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_memory*.py"
  - ".veldo/control_memory*.py"
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
  - "engine/.veldo/control_agent_config*.py"
  - ".veldo/control_agent_config*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0184_*.py"
  - "scripts/suites/80_veldo_0155_claude_baseline.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0184-file-memory-handed-to-every-run.md"
  - "specs/index.md"
  - "proof/VELDO-0184/*"
behavior_bearing: true
observability:
  logs: >
    Record each run's file memory handoff (the directory, the engine form used, the index digest) bound to
    the memory record revision and the qualification record; never memory content.
  metrics: >
    Count runs handed the file memory per engine and runs stopped for a memory path mismatch.
  traces: >
    Join each memory file read or write line to its run and the handoff record.
  error_taxonomy: >
    Distinguish a Claude Code init event whose memory paths are not the handed directory
    (binding_mismatch:engine_memory), a qualified baseline lacking the memory form for a version
    (missing_evidence:engine_baseline:<version>) and a missing memory directory at launch
    (invalid_input:memory:file:absent).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A Claude Code run whose role lists the file memory has auto-memory on in exactly the memory
      record's directory, whichever account runs it, and one whose role does not list it keeps auto-memory
      off. Set and completeness: VELDO-0127's capability configuration gains a `file_memory` item, and the
      seeded assistant roles list it `always`. For a run that lists it, the generated settings (VELDO-0155)
      set `autoMemoryEnabled` true and `autoMemoryDirectory` to the record's file memory directory, and the
      launch leaves `CLAUDE_CODE_DISABLE_AUTO_MEMORY` unset; every other part of the baseline is unchanged.
      Both settings are qualified on 2.1.281 and recorded in its qualification record, and a version whose
      baseline lacks them launches no run that lists the item (missing_evidence:engine_baseline:<version>).
      The init event's `memory_paths` must name exactly that directory, else the run is stopped by name
      before its first turn (binding_mismatch:engine_memory). The suite runs the item on two accounts and a
      role without it. Falsifier: Leave `autoMemoryDirectory` unset, and the memory-path row must fail on
      the account profile's directory in `memory_paths`.
    falsified_by: >
      Leave `autoMemoryDirectory` unset, and the memory-path row must fail on the account profile's
      directory in `memory_paths`.
  - id: AC2
    text: >
      Claim: A Codex run whose role lists the file memory reads and writes the same directory, with its
      index in its instructions, and Codex's own memory feature is not used. Set and completeness: For a
      Codex run that lists the item, the generated configuration (VELDO-0156) adds the record's file memory
      directory to the workspace-write sandbox's writable roots and puts the index file's content, with one
      paragraph naming the layout (one fact per file, the index kept current), into the developer
      instructions; Codex's own memory feature stays off, since it keeps memory in the account profile. Both
      forms are qualified on 0.154.0 and recorded in its qualification record, and a version without them
      launches no run that lists the item. The suite's fake Codex writes a new memory file and updates the
      index, and a later Claude Code run reads it. Falsifier: Hand the index in the instructions without the
      writable root, and the write row must fail on the refused write.
    falsified_by: >
      Hand the index in the instructions without the writable root, and the write row must fail on the
      refused write.
  - id: AC3
    text: >
      Claim: What a run loads from the file memory at launch, and every memory file it reads or writes, is in
      its execution record. Set and completeness: The record's launch line names the handed directory, the
      form used and the digest of the index file as loaded, since the engine reads the index into its
      context without a tool call; every read, write or edit of a file in the directory is a tool call line
      with its input and result (VELDO-0141 AC1), redacted as every line is. The suite compares the launch
      line's digest with the index before and after a run that edits it. Falsifier: Omit the index digest
      from the launch line, and the loaded-at-launch row must fail on the missing digest.
    falsified_by: >
      Omit the index digest from the launch line, and the loaded-at-launch row must fail on the missing
      digest.
required_evidence: [unit, integration]
rollback: >
  Stop handing the file memory (auto-memory off again for every run) while keeping the memory and the
  record. No automatic rollback is authorized.
---

## Intent

The file memory the owner's assistant keeps, one fact per file with an index, is there in every
conversation on either engine and any account, and he can see what a run read from it and wrote to it.

## Context

W144 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. VELDO-0155's
baseline turns Claude Code's auto-memory off for every run, so each account profile adds nothing; the
pinned 2.1.281 binary carries the `autoMemoryEnabled` and `autoMemoryDirectory` settings, and its init
event's `memory_paths` names the memory directories it loaded (operating-model design, section 6). Codex
0.154.0 has no auto-memory layout of this kind, so the directory reaches it as a writable root and its index
as instructions. The one location is VELDO-0182's record. A draft: only the owner marks it ready.

## Out of scope

Project runs' use of the file memory (a role may list it; this specification proves the conversation
roles); team memory; the Mac leg (VELDO-0147).

## What the reviewer judges

- Normal use: a conversation on the second Claude Code account saves a new rule as a memory file and
  updates the index; the next turn on the Codex account follows it; the owner's assistant sees it too.
- Threat model: a run whose auto-memory lands in its account profile; a role without the item that loads
  memory anyway; a Codex run writing memory where Claude Code never reads it; a memory load or write missing
  from the record.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), such as two turns
  editing the index at the same moment (Release 2 concurrency); other engine versions.

## Notes

The switch and settings are qualified on the pinned version before use, as the operating-model design
requires for every environment switch and setting; a new version is requalified.

## History

2026-09-27: new draft for the owner's memory requirement (Telegram 29294). Only the owner marks a
specification ready.
