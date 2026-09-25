---
schema: veldo.spec/v1
id: VELDO-0141
title: Every worker run's full live execution record, and the UI's live terminal view of it
status: draft
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0039, VELDO-0043, VELDO-0045, VELDO-0130]
placement: [engine, contracts, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_execution_record*.py"
  - ".veldo/control_execution_record*.py"
  - "packs/*/.veldo/control_execution_record*.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "packs/*/.veldo/control_launch*.py"
  - "engine/.veldo/control_api*.py"
  - ".veldo/control_api*.py"
  - "packs/*/.veldo/control_api*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0141_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0141-live-execution-record.md"
  - "specs/VELDO-0131-factory-phone-desktop-ui.md"
  - "specs/index.md"
  - "proof/VELDO-0141/*"
behavior_bearing: true
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every worker run's engine output is kept, as it happens and in order, as that run's
      execution record: every message, tool call with its input, tool result, command output, file
      change and error the engine emits, and its error stream, with nothing dropped. Set and
      completeness: Run real Claude Code and Codex workers (their structured event output) through the
      launcher on a unit whose work calls tools, runs a command that writes to its error stream and
      edits a file; compare the kept record, line by line and in order, with what the engine emitted.
      Secrets are redacted by the secret scanner before anything is kept. Falsifier: Discard the
      worker's error stream; the complete-record check must fail.
    falsified_by: >
      Discard the worker's error stream; the complete-record check must fail.
  - id: AC2
    text: >
      Claim: The authenticated API serves a run's execution record live, from a cursor, and after the
      run ends, only to a current member whose scope covers the run's project, and never serves an
      unredacted line. Set and completeness: Follow a record while the run writes it and after it ends;
      resume from a cursor; refuse a member outside the project's scope, an ended session and an
      unknown run by name. Falsifier: Serve a record line before redaction; the no-secret-served check
      must fail.
    falsified_by: >
      Serve a record line before redaction; the no-secret-served check must fail.
  - id: AC3
    text: >
      Claim: The UI's run view shows the execution record as a live terminal, with the same detail and
      order the engine produced, following as it grows, on phone and desktop. Set and completeness:
      VELDO-0131's screen contract gains the run's live terminal view, reached from the run and unit
      screens, readable at 360px and 1440px, searchable, and never a summary in place of the record.
      Falsifier: Show a summarized step list in place of the record; the full-detail check must fail.
    falsified_by: >
      Show a summarized step list in place of the record; the full-detail check must fail.
required_evidence: [unit, integration]
rollback: >
  Stop keeping new records and remove the route; kept records remain for the owner to delete by hand.
---

## Intent

The owner watches the execution detail of each worker run in the Claude Code or Codex terminal today:
every tool call, command, edit and output. The factory keeps none of it (the launcher reads a worker's
output only for its protocol messages and discards its error stream), so the UI could show only a
summary and he could not stop using the terminal. This keeps each run's full live execution record and
shows it in the UI as a live terminal.

## Context

The owner's requirement, Telegram 29122 and 29126 (2026-09-25): "I very frequently need to look at
terminal as I need to see all the execution details ... without it, I can't stop using terminal."
VELDO-0130 named tool-call records as a gap no specification wrote; VELDO-0131 AC2 consumes them.

## Out of scope

Replaying or editing a record; retention limits and archival (Release 2); runs outside the factory.

## What the reviewer judges

- Normal use: a worker runs a unit; everything its engine emits (messages, tool calls and results,
  command output, file changes, errors, its error stream) is kept in order as that run's execution
  record, redacted before it is kept. The owner opens the run in the UI on his phone or desktop and
  watches it live as a terminal, or reads it after the run; the API serves it only to members whose
  scope covers the project.
- Threat model: output dropped, reordered or summarized; the error stream discarded; a secret kept or
  served unredacted; a record served to a member outside the project's scope or to an ended session;
  a record shown for another run. The owner's account, the store and the engines are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); the items in
  Out of scope above; forged rows in our own store.

## Notes

Capture the engines' own structured event output where they offer it (Claude Code stream-json, Codex
JSON events) and keep the raw error stream beside it; do not reinterpret the engine's content. The
execution record is bound to the dispatch and run it belongs to. VELDO-0131's screen contract gains
the live terminal view; its build reads this API.

## History

2026-09-25: written by the lead at the owner's request (Telegram 29122, 29126). Draft; the owner
decides readiness.
