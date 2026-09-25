---
schema: veldo.spec/v1
id: VELDO-0141
title: Every worker run's full live execution record, served for the UI's live terminal view
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W101
plan_revision: 4
depends_on: [VELDO-0039, VELDO-0043, VELDO-0045, VELDO-0060, VELDO-0061, VELDO-0130]
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
  - "specs/index.md"
  - "proof/VELDO-0141/*"
behavior_bearing: true
observability:
  logs: >
    Record each record's dispatch and run identity, line and byte counts, redaction kinds applied and
    any named refusal to serve; never a credential value or an unredacted line.
  metrics: >
    Count kept lines and bytes per run and stream, redactions by kind, and live followers per record.
  traces: >
    Join each record to its dispatch, run, account and host, and each served page to its session and cursor.
  error_taxonomy: >
    Distinguish unauthenticated, out of scope, ended session, unknown run, cursor past the end and a
    record whose committed digest does not match; none is served as an empty record.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every worker run's engine output is kept, as it happens and in order, as that run's
      execution record: every message, tool call with its input, tool result, command output, file
      change and error the engine emits, and its error stream, with nothing dropped. Set and
      completeness: Run real Claude Code and Codex workers (their structured event output) through the
      launcher on a unit whose work calls tools, runs a command that writes to its error stream and
      edits a file, on Linux; compare the kept record, line by line and in order, with what the engine
      emitted, with every line redacted as AC4 requires before it is kept. Falsifier: Discard the
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
      Claim: The record route serves the live terminal view everything it shows, as the engine produced
      it and never summarized: every kept line in sequence, with its stream, receive time, redaction
      marks and payload, live after each hint and from any cursor, and after the run ends the record's
      committed line count and digest. Set and completeness: For a real run whose work calls tools, runs
      a command that writes to its error stream and edits a file, read the route from the first cursor
      while the run writes, from a cursor in the middle, and after the run ends; compare the served lines
      with the kept record in count, order, sequence, stream and payload, with every tool call's input
      and result, every command's output, every edit and every error present as the engine emitted it,
      and nothing merged, dropped, reordered or replaced; after termination require the served line
      count and digest to equal the termination record's. The screen that renders these lines is
      VELDO-0145 AC2. Falsifier: Serve a summarized step list in place of the record's lines; the
      served-lines comparison must fail.
    falsified_by: >
      Serve a summarized step list in place of the record's lines; the served-lines comparison must
      fail.
  - id: AC4
    text: >
      Claim: Before a line is kept, the receiver replaces the exact credential values it resolved for
      that run, and only then does the secret scanner redact known patterns and high-entropy spans, so a
      credential value the scanner alone would miss never reaches the record. Set and completeness:
      Resolve for a real run a credential whose value has no known pattern and low entropy, and have the
      run print it alone, inside a command's output, in its error stream, and joined to a high-entropy
      span that the scanner redacts only in part; also print a token of a known pattern. Read back the
      record: every occurrence of the planted value is replaced by the marker naming its kind, the
      known-pattern token is redacted by the scanner, each line's redaction field names the kinds
      replaced, and no line holds any part of the planted value. Falsifier: Run the scanner before
      exact-value replacement; the planted-value row must fail.
    falsified_by: >
      Run the scanner before exact-value replacement; the planted-value row must fail.
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

W101 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. The owner's
requirement, Telegram 29122 and 29126 (2026-09-25): "I very frequently need to look at terminal as I
need to see all the execution details ... without it, I can't stop using terminal." VELDO-0130 named
tool-call records as a gap no specification wrote; VELDO-0131 AC2 consumes them. Section 7 of the
approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) designs the
record, its capture and its serving.

## Out of scope

Replaying or editing a record; retention limits and archival (Release 2); runs outside the factory.

## What the reviewer judges

- Normal use: a worker runs a unit; everything its engine emits (messages, tool calls and results,
  command output, file changes, errors, its error stream) is kept in order as that run's execution
  record, redacted before it is kept. The owner opens the run in the UI on his phone or desktop and
  watches it live as a terminal, or reads it after the run; the API serves it only to members whose
  scope covers the project.
- Threat model: output dropped, reordered or summarized; the error stream discarded; a credential value the run resolved kept because the scanner did not
  recognize its shape; a secret kept or served unredacted; a record served to a member outside the
  project's scope or to an ended session; a record shown for another run. The owner's account, the
  store and the engines are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); the items in
  Out of scope above; forged rows in our own store.

## Notes

Capture the engines' own structured event output where they offer it and keep the raw error stream
beside it; do not reinterpret the engine's content. The adapters launch Claude Code in print mode with
stream JSON output and its `verbose`, `include-partial-messages` and `forward-subagent-text` options,
and Codex exec with its `json` option, because without partial messages and subagent text a
subagent's work would be hidden. The record is one append-only file per dispatch on the Linux host,
under the factory state root, mode 0600, written only by the launch receiver; each line carries a
gapless sequence, the receive time, the stream (`engine`, `stderr` or `wrapper`), what was redacted
and the payload unchanged except for redacted spans. After each batch the receiver sends the API a
hint naming the dispatch and the last sequence, so the live route never polls. The termination record
commits the record's line count, byte count and digest. The execution record is bound to the dispatch
and run it belongs to. VELDO-0131's screen contract gains the live terminal view; VELDO-0145 builds
it first and reads this API, and its AC2 owns that screen.

A Mac run's streams arrive over SSH into the same receiver, so every record is written on Linux; that
Mac leg is VELDO-0147 AC3, built once VELDO-0124 and VELDO-0125 land.

## History

2026-09-25: written by the lead at the owner's request (Telegram 29122, 29126). Draft; the owner
decides readiness.

2026-09-25: ready, on the owner's approval of the operating-model design (Telegram 29162, "all 6 are
yes"), whose section 7(e) moves this specification to ready with four amendments, applied here:
depends_on adds VELDO-0060 and VELDO-0061; AC1's set adds a Mac run through the relay; exact-value
redaction runs before the scanner (AC1); and the Notes name the hint to the API, the digest committed
at termination and the stream options. AC3 now replaces VELDO-0131's "Live agent run" row, and
VELDO-0145 is the first UI slice that shows it. Bound to PLAN-0019 revision 4 as W101 (lane planned);
an observability block is added, which the ready transition requires.

2026-09-25, PLAN-0019 revision 4 review: a specification ships whole and the run-check refuses one whose
dependencies are not shipped, so the Mac leg of this Linux-first qualification moves to VELDO-0147,
which is built after VELDO-0124 and VELDO-0125. Status unchanged.

2026-09-25, PLAN-0019 revision 4 review: AC3 was a screen contract that VELDO-0145's build had to
drive, while VELDO-0145 depends on this specification, so neither could ship first. AC3 is now the
record route's contract for the live view (every line in sequence, as emitted, from any cursor, with the
committed count and digest after the run), with its own falsifier, and VELDO-0145 AC2 owns the screen.
The title says so, and the footprint no longer names VELDO-0131's specification, whose row the plan's
revision 4 already amended. Status unchanged.

2026-09-25, PLAN-0019 revision 4 review: exact-value redaction before the scanner moves from AC1 into new
AC4, with its own falsifier (run the scanner before exact-value replacement; the planted-value row must
fail), and its set plants the value joined to a span the scanner redacts only in part, where the order
decides the result. AC1 keeps the complete record and its error-stream falsifier. Status unchanged.
