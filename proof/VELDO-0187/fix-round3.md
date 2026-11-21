# VELDO-0187 fix round 3 (the first independent review, 2026-11-11, FIX)

Branch agent/claude/veldo-0187, from 5627f1cc. Every suite run below is `python3 scripts/selftest.py --suite <name>`
alone, offline, under `systemd-run --user --scope -p MemoryMax=10G -p MemorySwapMax=0`; a PARTIAL run's exit 2 is its
green. scripts/verify.sh, the gate, the teeth stage and scripts/check_gate_mutations.py were not run (OPEN.md item 7).
claude-mem itself and the plugin folders were read only: its hook code, never its store or its worker.

## F1: the reader and the request model match claude-mem 10.6.2

What 10.6.2's hook code is, as read from the installed plugin:
- hooks/hooks.json commands assign the root to a variable (`_R="${CLAUDE_PLUGIN_ROOT}"`) and run
  `node "$_R/scripts/bun-runner.js" "$_R/scripts/worker-service.cjs" hook claude-code <subcommand>`.
- One bundle serves every hook. Its handler table maps session-init, observation, summarize and session-complete
  to one handler each; each handler posts through one wrapper called with a literal path:
  /api/sessions/init (contentSessionId, project, prompt), /api/sessions/observations (contentSessionId, tool_name,
  tool_input, tool_response, cwd), /api/sessions/summarize (contentSessionId, last_assistant_message) and
  /api/sessions/complete (contentSessionId). There is no session-start request. A file-edit handler posts a second
  observation, and the session-init handler posts once more to a path it computes (OPEN.md item 4b).
- The worker's address is the bundle's defaults (CLAUDE_MEM_WORKER_HOST 127.0.0.1, CLAUDE_MEM_WORKER_PORT 37777)
  unless the data directory's settings.json says otherwise; the hooks ask the worker its version at /api/version.

What changed:
- `qualify` resolves a command's scripts through the variable the command assigns the root to, takes the bundle and
  subcommand of each event's hook, finds the bundle's one handler table, the one definition of each handler and its
  one wrapper call with a literal `/api/...` path, and reads method and fields there. It also reads the one version
  request of the same wrapper and the address defaults. Anything missing is refused
  `missing_evidence:claude_mem_request:<kind>`; anything not unique is refused
  `missing_evidence:claude_mem_request:<kind>:ambiguous`. Each request entry keeps its event, subcommand, script,
  the digest of its handler's text, and what the handler posts to a computed path (`not_sent`).
- The request set is prompt, observation, summary and complete, plus the version request. The prompt starts the
  session; the completion is sent once, at the conversation's close, after every pending turn's feed
  (`Feed.close`, called by `Conversations.close`).
- The fixture plugin (fixtures.py) is laid out as 10.6.2: one bundle, the wrapper, `_R`, the handler table, a
  file-edit handler, the computed second post, the address defaults and the version request. The fixture worker
  answers the version request and the four routes as 10.6.2's worker does (init answers the session's id, the
  prompt's number and whether the session is already active).
- claude-mem-10.6.2-hooks.json is a byte copy of 10.6.2's hooks/hooks.json; claude-mem-10.6.2-excerpts.json holds
  byte excerpts of its bundle at their offsets (address defaults, version request, the four handlers, the handler
  table) with the bundle's digest. Row AC1/claude-mem-10.6.2 qualifies them and compares every request, its
  handler digest included, the address and both file digests with the shipped record's entry.
- The shipped record lists 10.6.2. It was written by
  `python3 .veldo/control_memory_feed.py qualify <the installed 10.6.2 plugin directory>` with the record option
  naming engine/runtime/claude-mem-qualification.json, which answered
  `{"outcome": "qualified", "versions": ["10.6.2"]}`; .veldo/runtime holds the same bytes. Before this round the
  same command answered refused, missing_evidence:claude_mem_request:start.
- Row AC1/installed qualifies the claude-mem installed on the machine the suite runs on (read only) against the
  shipped record. On this machine it printed `installed claude-mem: {'10.6.2': 'qualified'}`. With none installed
  the row passes and says so.
- AC1 is amended as the review words it (spec History, 2026-11-11; the owner marks it, OPEN.md item 4a).

## F2: a worker's refusal no longer stalls a conversation's feed

In `Feed.flush` a 5xx, 408 or 429 answer keeps the feed pending as unavailable_service:claude_mem_worker, as a
worker that does not answer does. Any other answer outside 2xx is the worker's refusal: the turn is recorded not
captured as `invalid_input:claude_mem_worker:<status>` (added to the spec's error taxonomy), the feed is moved to
`claude-mem/refused/<turn>.json` with the reason, and the next pending feed is sent. Redirects are never followed.
Row AC3/worker-refusal: the fixture worker answers 400 to turn 1's observation; turn 1 is not captured by that
name, the refused request is sent once and not again, turn 2 is captured and found, nothing stays pending.
Mutation case feed187-refusal-pending (a refusal taken for a worker that is away).

## F3: the running worker's version is asked before anything is sent

Each pass asks GET /api/version first, the request the record qualifies (`requests.version`), and logs it in the
conversation's feed log. A worker that reports another version than the setting's is sent nothing: every pending
feed stays pending and each pending turn is recorded not captured as
`missing_evidence:claude_mem_version:<running version>`, once, until the qualified version answers or setup runs
again. A feed kept under another qualification is built again from the redacted turn it keeps, so nothing is sent
by an interface that is no longer the qualified one. Row AC1/running-version: the fixture worker reports
10.7.0-v187; only version requests reach it; the turn shows pending, not captured, then captured once the
qualified version answers. Mutation case feed187-version-unasked (the version never asked).

## F4: a feed the feed itself refuses is kept

The Refused branch of `Feed.flush` (an address that is not loopback, a paid-API name) moves the feed to
`claude-mem/refused/` with the reason instead of deleting it. Row AC1/loopback has the check: a pending feed under
a setting whose address is no longer loopback is moved there with its requests, and nothing is sent.

## F5: behaviour rows for the batch-fix project check

- Suite 128 row AC3/project-check: an attach of the owner's own paused project, in his scope, is refused
  project_not_active:PAUSED; no clone directory, no attachment, the version unchanged.
- Suite 136 row AC1/project-check: a pointing at a project its owner activated and then paused is refused
  project_not_active:PAUSED in the conversation organ and at intake's plan (Conversing._point_plan); the same
  pointing at his active project is planned by both; a new-project pointing whose name the store holds is refused
  stale_subject:project_exists in the organ and through intake; a new name is planned; nothing is written.
- Mutation cases attach187-check-ignored (the review's edit), point187-check-ignored and
  point187-existing-as-new. Intake's own check has no case (OPEN.md item 6).

## F6: record keeping

OPEN.md items 1 and 2 are marked resolved by 3855caea and item 4 is rewritten. The spec's History records the
lead's batch-fix rulings with the files they took outside the footprint, and this round. The mutation receipts are
proof/VELDO-0187/heavy_runs.sh, for the lead's lock queue: all eight finding 187 cases through
scripts/check_gate_mutations.py with the committed unconfined entry.

## Runs

Suites, each alone, all green:

| suite | rows | passed, failed |
| :- | :- | :- |
| 138_veldo_0187_claude_mem_feed | 18 | 44, 0 |
| 128_veldo_0177_conversation_workspace | 16 | 42, 0 |
| 136_veldo_0180_conversation_projects | 22 | 48, 0 |
| 84_veldo_0169_project_handouts | 27 | 53, 0 |
| 86_veldo_0186_setup_assets | 11 | 37, 0 |
| 82_veldo_0172_live_formats | 4 | 30, 0 |
| 123_veldo_0174_conversations | 38 | 64, 0 |
| 133_veldo_0178_conversation_api | 16 | 42, 0 |
| 130_veldo_0176_conversation_history | 17 | 43, 0 |
| 130_veldo_0183_memory_servers | 19 | 45, 0 |
| 131_veldo_0175_conversation_replies | 16 | 42, 0 |
| 132_veldo_0175_conversation_routes | 21 | 47, 0 |
| 137_veldo_0181_conversation_decisions | 19 | 45, 0 |
| 105_veldo_0182_memory | 127 | 153, 0 |
| 50_git_environment | 4 | 30, 0 |
| 51_parser_boundary | 25 | 51, 0 |
| 53_veldo_0123_mutations | 14 | 40, 0 |
| 55_veldo_0119_agreement | 3 | 29, 0 |
| 98_veldo_0204_mutation_receipts | 45 | 71, 0 |

Also: `python3 .veldo/validate.py all` exit 0; scripts/check_template_sync.sh pass (311 pairs).

Each mutation case applied by hand to the working .veldo copy with check_teeth_mutations.mutate, its suite run
alone, the file restored. All eight killed, each on its named row:

| case | suite | red rows |
| :- | :- | :- |
| feed187-any-version | 138 | AC1/unqualified |
| feed187-held-session | 138 | AC2/redaction, AC2/record-order, AC3/pending |
| feed187-dropped | 138 | AC3/pending and 7 others |
| feed187-refusal-pending | 138 | AC3/worker-refusal, observability |
| feed187-version-unasked | 138 | AC1/running-version and 5 others |
| attach187-check-ignored | 128 | AC3/project-check, AC3/scope, AC3/attach-again, AC3/observability |
| point187-check-ignored | 136 | AC1/project-check |
| point187-existing-as-new | 136 | AC1/project-check |

These are hand runs, not the gate's driver: no baseline and no-op legs. The driver's receipts are heavy_runs.sh.
