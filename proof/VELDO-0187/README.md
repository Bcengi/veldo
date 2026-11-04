# VELDO-0187 proof: every conversation turn fed to claude-mem's session history from its redacted record

Suite: scripts/suites/138_veldo_0187_claude_mem_feed.py, 13 rows, 39 checks, run alone:
python3 scripts/selftest.py with the suite option naming 138_veldo_0187_claude_mem_feed (needs the systemd user manager, OPEN.md item 1).
Fixtures: proof/VELDO-0187/fixtures.py (a claude-mem plugin whose four hook scripts post to its worker, a fixture
worker on loopback that writes claude-mem.db, an MCP stdio client) and VELDO-0183's claude-mem search server.
No real engine, login, claude-mem store, worker or plugin is touched.

Receipts: red-before.txt (all 13 rows red at 2cdc1dd3, both with no feed module and with the module but none of
the wiring), falsifiers.txt (each spec falsifier applied by hand, red, restored), mutation-*.txt (each case killed
alone through the gate's driver, baseline and no-op green), suites-after.txt (neighbouring suites), merge-step1.txt
(step 1, the merge). Open items: OPEN.md.

## What was built

- `.veldo/control_memory_feed.py` (engine copy byte-identical): the qualification reader (`qualify`, and the
  `qualify` command that writes an entry into the record), setup's feed setting (`setup`, `read_setting`), the
  requests of one turn (`build`), the sender (`send`: loopback only, content type only, no paid-API field), the
  per-conversation `Feed` (pending feeds under `<conversation>/claude-mem/pending/`, the feed log
  `claude-mem/feed.jsonl`, the session in `claude-mem/session.json`) and the metrics.
- `runtime/claude-mem-qualification.json` (schema `veldo.claude_mem_qualification/v1`, no version listed yet:
  OPEN.md item 4), installed by init_scaffold's runtime assets and setup's asset closure.
- control_conversation: `Conversations.ended` feeds every ended turn (`feed_turn`, from `record_lines` through
  `turn_from_record`, never the held session); `feed_pending` sends pending feeds in turn order; a new operation
  `capture_conversation_turn` keeps the turn's capture state (`claude_mem`, with every change in
  `claude_mem_states`); `status()['claude_mem']` carries the metrics.
- control_service: `ConversationLine.run` sends pending feeds at the start of every loop pass.
- control_factory_setup_memory: setup's memory step (`apply`, first run and rerun) reads the installed version from
  the memory record's claude-mem part and writes the feed setting (`claude_mem_feed`), reported as
  `claude_mem_feed`.

## AC1: only through the hooks' interface, qualified on the installed version

Rows `AC1/record`, `AC1/qualified`, `AC1/unqualified`, `AC1/loopback`, `AC1/no-credential`: green after, red
before (red-before.txt).
- The fixture version is qualified by `record_qualified` from its own hook code: the digest of hooks.json and of
  each script it names, the four requests (start, prompt, observation, summary) with method, path and fields, and
  the loopback address. Hook code with a paid-API field, a non-loopback default or a missing request is refused
  by name.
- Setup's memory step records the installed version qualified (setting 0600 under the state root); only its four
  qualified routes reach its worker.
- An unlisted version (10.9.9-v187), and a listed version whose hook scripts differ, are refused
  `missing_evidence:claude_mem_version:<version>`; every turn is recorded not captured by that name and the fixture
  worker at that version receives nothing.
- A worker address that is not loopback (settings.json naming 192.0.2.9) is refused
  `invalid_input:claude_mem:not_loopback` at setup and in `send`; its turn is not captured, nothing is sent.
- Requests carry no header but the content type and the transport's own, and no field named as a paid API.
- Falsifier (feed sent whatever the installed version): `AC1/unqualified` red, the unqualified worker received 7
  requests. Mutation case `feed187-any-version` killed.

## AC2: every turn, either engine, any account, one session, from the redacted record

Rows `AC2/one-session`, `AC2/record-order`, `AC2/redaction`, `AC2/feed-log`: green after, red before.
- Turn 1 runs on the Claude Code account (its tool result prints the resolved subscription token), turn 2 on the
  Codex account after a role change (its tool result prints the keystore credential delivered to its catalog
  server). Both join the conversation's one claude-mem session, started once by the conversation's first feed.
- The worker receives each turn's prompt, each tool call as an observation and the reply with the summary request,
  in the record's order, every value equal to `turn_from_record` over the redacted execution record.
- Each held session itself carries its credential value; neither value reaches the worker or the feed log, and the
  observed tool results are the records' `[REDACTED` ones.
- Each request is kept in the conversation's feed log (0600) with its digest and the worker's answer; attempts the
  down worker did not take are kept too, by name.
- Falsifier (feed built from the held session): `AC2/redaction` red on the credential value in the worker's
  observation. Mutation case `feed187-held-session` killed.

## AC3: found by claude-mem's own search; a turn the worker could not take is sent later, in order

Rows `AC3/found`, `AC3/pending`, `AC3/loop-pass`: green after, red before.
- With the fixture worker down, turn 1 ends `pending` (`unavailable_service:claude_mem_worker`) with its feed in the
  conversation's directory; the worker is started while turn 2 runs, and turn 1's feed is sent, in order, before
  turn 2's. The turn record shows pending, then captured; nothing stays pending.
- The catalog record a later conversation is given (control_memory_servers.definitions, VELDO-0183 AC1) and the
  assistant's own search server as the plugin's .mcp.json starts it both find turn 1's message and reply, and
  turn 2's.
- A turn that ended while the worker was down is captured by the next loop pass after the worker answers, with no
  new turn (`late`).
- Falsifier (a feed the worker did not take dropped): `AC3/pending` red with turn 2 found while turn 1 is not.
  Mutation case `feed187-dropped` killed.

## Observability

Row `observability`: each feed is an event (`claude_mem_feed`) naming the conversation, turn, dispatch, session,
request kinds and digests, each answer's status and each capture state with its reason, joined to the execution
record's committed digest and the qualification entry's digest; no turn content or credential value appears in any
event. `status()['claude_mem']` counts turns captured, pending and not captured by reason, requests by kind, and
feeds sent late.

## Mutation cases (scripts/check_teeth_mutations.py, finding 187)

| case | module | edit | row |
| :- | :- | :- | :- |
| feed187-any-version | control_memory_feed.py | an unlisted version takes a listed entry | AC1/unqualified |
| feed187-held-session | control_conversation.py | the feed's observation built from the held session | AC2/redaction |
| feed187-dropped | control_memory_feed.py | a feed the worker did not take is removed | AC3/pending |

Each killed alone through `scripts/check_gate_mutations.py`, baseline and no-op green, in the unconfined leg with
the entry OPEN.md item 1 names.
