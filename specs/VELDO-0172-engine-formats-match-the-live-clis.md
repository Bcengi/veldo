---
schema: veldo.spec/v1
id: VELDO-0172
title: The engine stream-format tables and every fake engine match the real Claude Code and Codex output recorded in the live runs of 2026-09-26
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W132
plan_revision: 4
depends_on: [VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0155, VELDO-0156, VELDO-0160]
placement: [fleet, engine]
protected_paths: []
footprint:
  - "proof/VELDO-0062/extract_formats.py"
  - "proof/VELDO-0062/cli-formats.json"
  - "proof/VELDO-0062/README.md"
  - "scripts/suites/75_veldo_0062_accounts.py"
  - "scripts/suites/78_veldo_0060_claude_adapter.py"
  - "scripts/suites/78_veldo_0160_account_pool.py"
  - "scripts/suites/79_veldo_0061_codex_adapter.py"
  - "scripts/suites/80_veldo_0155_claude_baseline.py"
  - "scripts/suites/81_veldo_0156_codex_baseline.py"
  - "scripts/suites/82_veldo_0129_worker_wiring.py"
  - "scripts/suites/82_veldo_0141_execution_record.py"
  - "scripts/suites/82_veldo_0165_launch_hygiene.py"
  - "scripts/suites/83_veldo_0154_factory_loop.py"
  - "scripts/suites/*_veldo_0172_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "proof/VELDO-0172/drive.py"
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
      Claim: The live capture the rows compare against is committed with every key and every value's type
      kept, and no value survives unless it is a named schema constant or a token count. Set and
      completeness: proof/VELDO-0172 holds the 2026-09-26 Claude Code and Codex stream lines and, of the
      runs' tap records, only the Claude handshake answer (the control_response to initialize) and the
      Codex login status with the stream it came on; no other tap record is ever committed. The committed
      scrubber is an allowlist: every string value becomes a placeholder naming its type unless its field
      is on the named list of schema constants committed beside it (type, subtype, stop_reason, the CLI
      and schema versions, model ids, apiKeySource and the subscription label), and a number is kept only
      in a token-count field, every other number becoming a numeric placeholder. The capture's digest and
      the binary versions it came from are recorded in cli-formats.json. The suite checks the committed
      capture (each string on the list or a placeholder, each kept number in a token-count field, no tap
      record but the two, and the repository secret scan finding nothing) and runs the scrubber over a
      fixture line planted with values of kinds the source really has, a host name, a pid and a home path,
      in fields off the list: none survives. The one read-back of every field path against the source
      capture, which is never committed, is a proof step the lead runs once on the host and records in
      proof/VELDO-0172, not a suite row. Falsifier: Have the scrubber keep a string whose field is off the
      list when it matches no known identity pattern, as a denylist would, and the planted-value row must
      fail on the host name.
    falsified_by: >
      Have the scrubber keep a string whose field is off the list when it matches no known identity
      pattern, as a denylist would, and the planted-value row must fail on the host name.
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

How the adapters read these fields (metering every window is VELDO-0166, the environment strip VELDO-0165
and launch tool registry VELDO-0173);
later CLI versions (a requalification re-records a capture); events the live runs did not print, which
the fakes still check against the table alone.

## What the reviewer judges

- Normal use: after a CLI update the lead regenerates the table and records one live run; the suites then
  compare the fakes and the table with it and name each field that moved.
- Threat model: a fake that prints a shape the real CLI never prints, or leaves out one it does; a table
  that calls a real line malformed or accepts a field the real CLI never sends; a capture that leaks the
  owner's email, a host name, a pid, a path or any other value that is not a schema constant or a token
  count into the repository; a tap record beyond the two named ones committed. The installed binaries and
  the owner's account are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); fields a real
  run prints only in states the live runs did not reach (an error result, a tool call); capture files
  planted in the proof directory.

## Notes

The source capture lives at /home/dmitry/projects/veldo-live-captures/2026-09-27/, outside any
repository: real-claude/, real-codex/, compare.json and the tap scripts; it is never committed.
Only the allowlist-scrubbed capture of AC3 is committed. The lead's live-run driver recorded the
streams and tap files, and compare.json is the comparison that found these differences.
Suite scripts/suites/78_veldo_0160_account_pool.py is in the footprint because its fake prints
rate_limit_event lines.
They keep the shapes, not the values: a placeholder keeps a key's type, so the comparison reads the same
paths the real lines had. The scrub is an allowlist because a denylist keeps whatever nobody thought to
name, and the source held values of kinds no list named in advance. The source capture stays on the host
and is never committed, so the read-back against it can only be a recorded proof step; the suite checks
what is committed. This specification depends on VELDO-0160 because VELDO-0160 extends the same table and
extractor (claude_code.tool_forms in cli-formats.json, read by extract_formats.py), so this change
regenerates and checks the table as VELDO-0160 leaves it.

## History

2026-09-27: new draft from the live engine runs of 2026-09-26 (the format-table item of the follow-up
list). A draft: only the owner marks a specification ready.

2026-09-27: amended on the independent check of this batch. AC3 scrubs the committed capture with an
allowlist: each string value becomes a typed placeholder unless its field is on a named list of schema
constants, numbers are kept only in token-count fields, and no tap record but the handshake answer and the
Codex login status is committed. The read-back against the source is a recorded proof step, not a suite
row. The falsifier plants a value of a kind the source really has, which must not survive. depends_on adds
VELDO-0160. Still a draft.

2026-09-27: marked ready by the owner (Telegram 29229, "all ready").

2026-09-27, implementation on build-veldo-0172: the allowlist scrubber selects the two engine streams
and exactly the two named tap answers. Host read-back preserves every selected key and value type and
checks all non-allowlisted source strings by literal grep. The extractor reconciles the binary schemas
with the scrubbed capture and records its digest, versions and field-level line provenance. Proof and
fake-engine comparisons are in progress; status unchanged.

2026-09-27: footprint adds `proof/VELDO-0172/drive.py`, absent at the base commit, for the required red-record
and mutation proof commands. This driver records only VELDO-0172 and uses the existing mutation registry
and Git process boundary. No production engine module changes.

2026-09-27: completed the six-suite fake census and comparison rows. Nine selected suites pass normally
and in the clean gate environment. The unchanged base at 65125030 fails all four behavior rows by
assertion. Finding 0172 rejects five mutations on their named rows, with a green baseline and three
green no-op controls. The host read-back records 462 matching typed paths and no literal matches among
810 non-allowlisted source strings. The final whole selftest passes all 122 suites, with 6864 assertions
passed and zero failed. Git boundary, footprint, anchor and validation checks pass; all 198 Python engine
copies remain byte-identical. The canonical gate was not run, as instructed. Status unchanged.

2026-09-27, integration: the proof driver moved from scripts/drive.py to proof/VELDO-0172/drive.py, because VELDO-0085 and VELDO-0165 used the same file name for their own drivers; its behavior is unchanged.

2026-09-27, integration with VELDO-0165 on batch-0165-0172: the extractor now also reads the binary's
system/init and initialize-answer emitters, and a field an emitter writes only under a condition is
optional in the table, whatever the schema or the capture shows. The capture's init carried
messaging_socket_path because that run bound its own cross-session inbox; the binary writes the field only
when an inbox is bound (`if(e.messagingSocketPath!==void 0)`), and start-up unsets any inherited
CLAUDE_CODE_MESSAGING_SOCKET first, so the stripped parent variable was not the cause. The same reading makes
the initialize answer's fast_mode_disabled_reason (`??void 0`) optional. The table was regenerated by the
extractor. `table/capture` now also requires each captured line, with such a field removed, to conform to the
committed and the rebuilt table, and mutation `formats172-emitter-required` must red it. Status unchanged.

2026-09-27, integration port on batch-0165-0172: the census found nine suites, because
82_veldo_0129_worker_wiring, 82_veldo_0141_execution_record and 82_veldo_0165_launch_hygiene came after
the build. Their fake engines now use the shared constructors, and each suite has the observer hook and a
`format/` row (new `format/fake-lines` in 0129 and 0165). The 0129 fake prints the init and streamed
message the live run printed. The 0141 fake names an organization only when its profile's login has one,
as the binary's `organization:ie?.organization` does. The 0165 launches print a whole normal turn. The
observer now takes each engine's source separately, reads a suite's own packet (`readback_packet`) and
reports a source it cannot read as a named problem instead of raising. Whole-line expectations updated:
0129 `installation/assets` routes init and assistant lines to the Claude Code table; 0141
`format/fake-lines` reads the reconciled Codex item table; 0165 `mcp/prefixed-tools` and
`fixture/mcp-control` expect the built-in tools ahead of the MCP ones. New mutation
`formats172-hygiene-answer-drops-provider` reds `fake/capture`. The footprint adds the three suite files.
Status unchanged.

2026-09-27, census redesign on batch-0165-0172: the observation now happens where each fake runs, once.
The `fake/capture` census executed every other fake-engine suite in full inside this suite (136 s with
nine suites, growing with each new one), past the gate's 120-second mutation worker budget. Each suite
that builds a fake Claude Code or Codex engine now calls `conform_fake` from
proof/VELDO-0172/compare_formats.py at its own teardown and reports `VELDO-0172 fake/capture:<suite>`
from its own run: equal field paths per captured event, every line conforming to the table, and the
suite-level facts of AC2 where that suite prints the event. This suite runs no other suite. Its
`fake/census` row reads every suite's syntax tree, requires each fake-building suite to make that call in
a `finally` and report that row, and requires the suites' declared events to cover every captured event,
each with the capture's exact field paths in the shared templates. The suite takes about 1 s. The AC2
falsifier is now registered on suite 79 and reds its own `fake/capture` row on the stream; new mutation
`formats172-census-drops-conform` removes suite 79's call and reds `fake/census`; the hygiene mutation
reds suite 0165's own row. Criteria text unchanged. Status unchanged.

2026-09-28, integration with VELDO-0154 on batch-0165-0172: the static census found a tenth fake-building
suite, 83_veldo_0154_factory_loop, written before this design. Its fake Codex vendor binary prints the lines
its script files name, and those lines now come from the shared constructors (`live_step` over its thread,
turn, completion, failure and MCP call lines), so every line matches the capture. At its teardown, once its
services have stopped, it calls `conform_fake` with its locals, driving the installed executable once with a
script of its own read-back packet, and reports `VELDO-0172 fake/capture:0154_factory_loop`; its new
`format/fake-lines` row checks every scripted line, the usage-limit failures and MCP tool-call items
included, against the binary's table. VELDO-0154's rows keep their checks. The footprint adds the suite file.
Status unchanged.

2026-09-28, independent review of the census redesign on batch-0165-0172: the census's event coverage
credited any dict with a `type` key, whatever its engine, so it counted non-events and credited 0165 with an
`item.completed` its conform run never printed; a fake that stopped printing an event left the row green.
The census now credits a suite, per engine, only with a captured event its own dict displays or installed
executables name, and each suite's `fake/capture` row requires its conform trace to have compared every event
credited to it. The 0165 read-back prints its agent message; the 0129 read-back drives its Claude Code fake,
which now lists the built-in tools in its init. New mutation `formats172-credited-event-not-printed` keeps
suite 81's agent-message display but stops printing it; suite 81's own row reds while the census stays green.
Suite 0165 registers the claim organ as `transaction_transition`, as VELDO-0169's store now requires.
Criteria text unchanged. Status unchanged.
