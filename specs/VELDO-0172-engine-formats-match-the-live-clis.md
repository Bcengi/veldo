---
schema: veldo.spec/v1
id: VELDO-0172
title: The engine stream-format tables and every fake engine match the real Claude Code and Codex output recorded in the live runs of 2026-09-26
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W132
plan_revision: 4
depends_on: [VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0155, VELDO-0156]
placement: [fleet, engine]
protected_paths: []
footprint:
  - "proof/VELDO-0062/extract_formats.py"
  - "proof/VELDO-0062/cli-formats.json"
  - "proof/VELDO-0062/README.md"
  - "scripts/suites/75_veldo_0062_accounts.py"
  - "scripts/suites/78_veldo_0060_claude_adapter.py"
  - "scripts/suites/79_veldo_0061_codex_adapter.py"
  - "scripts/suites/80_veldo_0155_claude_baseline.py"
  - "scripts/suites/81_veldo_0156_codex_baseline.py"
  - "scripts/suites/*_veldo_0172_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0172-engine-formats-match-the-live-clis.md"
  - "specs/index.md"
  - "proof/VELDO-0172/*"
behavior_bearing: true
observability:
  logs: >
    Record, for each table regeneration, the binary versions and digests read, the capture's digest, and
    each field the capture added or made optional; for each comparison row, the event, the field path and
    which side (table, fake or capture) disagreed; never a captured value.
  metrics: >
    Count fields known and optional per event, fields taken from the capture, and fake lines compared per
    suite.
  traces: >
    Join each table field taken from the capture to the capture line and event it came from, and each
    fake line compared to the suite and row that printed it.
  error_taxonomy: >
    Distinguish a table field the capture contradicts (known but absent where required, or present and
    unknown) from a fake field the capture lacks, a capture field no fake prints, a fake printing on the
    wrong stream, and a capture whose digest no longer matches the one the table records.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: extract_formats.py and cli-formats.json record each field as known or optional exactly as
      the binary's own schema and the recorded live capture show. Set and completeness: A field is known
      when the schema or the capture has it, and optional when the schema marks it optional or a capture
      line of its event omits it; a field taken from the capture names the capture as its source. So
      Claude Code's `assistant.message.usage.server_tool_use` is optional; `system/init`'s
      `messaging_socket_path` and the assistant message's `input_transformations` and `diagnostics` are
      known; `rate_limit_event`'s `rate_limit_info.unifiedWindows` is known with its windows' fields; the
      handshake answer (the control_response to initialize) is in the table with every field the capture
      shows, `account.email` among them; and Codex `turn.completed` usage has its 5 fields,
      `cache_write_input_tokens` among them. Check every capture line against the table: none has an
      unknown field or misses a required one. `--check` still passes after a regeneration. Falsifier:
      Regenerate the table from the binary alone, dropping the capture, and the table-against-capture
      row must fail on `server_tool_use` required and `messaging_socket_path` unknown.
    falsified_by: >
      Regenerate the table from the binary alone, dropping the capture, and the table-against-capture row
      must fail on `server_tool_use` required and `messaging_socket_path` unknown.
  - id: AC2
    text: >
      Claim: Every fake Claude Code and Codex engine prints the shapes the live capture recorded.
      Set and completeness: The set is every fake in the suites that prints a Claude Code or Codex line,
      found by a census of the suites, never a fixed list. For each event the capture recorded, the
      field paths a fake prints for it equal the capture's, none missing and none added (a record keyed by
      model name read as one key), and every line of every event conforms to the table. Across the fakes,
      a Claude Code handshake names the `Claude Team` subscription label; an assistant message streams an
      output token count lower than its result's, as the live run did (3 streamed, 4 in the result); a
      rate-limit event carries `unifiedWindows`; a Codex fake prints `login status` on stderr with stdout
      empty; and a Codex `turn.completed` usage has the 5 fields. Falsifier:
      Revert suite 79's fake to print its login status on stdout, and the fake-against-capture row must
      fail on the stream.
    falsified_by: >
      Revert suite 79's fake to print its login status on stdout, and the fake-against-capture row must
      fail on the stream.
  - id: AC3
    text: >
      Claim: The live capture the rows compare against is committed as the runs recorded it, keeping every
      field and dropping every identifying value. Set and completeness: proof/VELDO-0172 holds the
      2026-09-26 Claude Code and Codex stream lines (the Claude handshake answer among them) and the Codex
      login status with the stream it came on, taken from the runs' recorded stream and tap captures, each
      value that is an identity, credential, path or free text (the account email, session and message
      ids, paths, the model's reply) replaced by a placeholder of the same type, every key and every
      value's type kept; its digest
      and the binary versions it came from are recorded in cli-formats.json. The repository secret scan
      finds nothing in it, and a check reads every field path of it back against the source capture.
      Falsifier: Commit the capture with the account email left in, and the identifying-value row must
      fail.
    falsified_by: >
      Commit the capture with the account email left in, and the identifying-value row must fail.
required_evidence: [unit, integration]
rollback: >
  Restore cli-formats.json, extract_formats.py and the fakes from before this change; no engine code or
  record changes. No automatic rollback is authorized.
---

## Intent

The fake engines the suites run against print what the real CLIs print, so a check that passes against a
fake would pass against the real binary, and a real line never meets a table that calls it malformed.

## Context

W132 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1. The live Claude
Code 2.1.281 and Codex 0.154.0 runs of 2026-09-26 (approved Telegram 29207) were compared with the table
VELDO-0062 extracts from the binaries and with the fakes of suites 78, 79, 80 and 81. The binary's schema
marks `server_tool_use` nullable but not optional, and the real assistant message omitted it; the real
init and assistant lines carried fields the schema does not name; the handshake answer is not in the table
at all, and the fakes print two of its many fields. The Codex table already lists 5 usage fields, but the
fakes print 4; the real `login status` wrote to stderr, and the fakes write to stdout; every fake uses the
`Claude Max` label, where the real account was `Claude Team`; and every fake streams the same output count
it later reports in the result. A fake that differs from the real binary in these ways lets a defect pass,
such as reading only stdout for the login or taking a streamed count as final. This new specification is
draft; authoring it supplies neither implementation proof nor operational activation.

## Out of scope

How the adapters read these fields (metering every window is VELDO-0166, the launch hygiene VELDO-0165);
later CLI versions (a requalification re-records a capture); events the live runs did not print, which
the fakes still check against the table alone.

## What the reviewer judges

- Normal use: after a CLI update the lead regenerates the table and records one live run; the suites then
  compare the fakes and the table with it and name each field that moved.
- Threat model: a fake that prints a shape the real CLI never prints, or leaves out one it does; a table
  that calls a real line malformed or accepts a field the real CLI never sends; a capture that leaks the
  owner's email or another identifying value into the repository. The installed binaries and the owner's
  account are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); fields a real
  run prints only in states the live runs did not reach (an error result, a tool call); capture files
  planted in the proof directory.

## Notes

The captures are the ones the lead's live-run driver recorded (real-claude and real-codex, each a stream
and a tap file), and compare.json is the comparison that found these differences.
They keep the shapes, not the values: a placeholder keeps a key's type, so the comparison reads the same
paths the real lines had.

## History

2026-09-27: new draft from the live engine runs of 2026-09-26 (the format-table item of the follow-up
list). A draft: only the owner marks a specification ready.
