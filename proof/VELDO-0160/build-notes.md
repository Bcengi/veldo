# VELDO-0160 build notes (builder's working notes)

Base: 52f817d5 (main, VELDO-0062 landed). Branch build-veldo-0160.

## Design decisions

- Selection lives in a new module `control_account_pool.py` (footprint `control_account*.py`). It is
  called INSIDE the VELDO-0036 reservation transaction: `Reservations.reserve_pooled` is a new worker
  action whose transition chooses the account and reserves its slot atomically, so two preparations
  cannot both take an account's last slot.
- The Runner takes a `Pool` as its `account` (duck-typed: an object with `reserve`). control_launch.py
  changes are two small separate hunks: Runner.prepare (pool branch) and Metering.settle
  (classification). The VELDO-0060/0061 branch rewrites the engine hooks elsewhere in that file.
- Candidates: active accounts of the adapter's engine with a profile on the adapter's host, outside
  every reported rate-limit window (control_accounts.blocking), under their concurrency; an account
  with no observation (no window on its record and no CLI-reported usage in the ledger) is bounded at
  one run. Order: lowest last reported utilization on the tightest window (unknown sorts after every
  known one: unknown is never zero), then fewest active runs, then least recently used, then id.
  The account's VELDO-0036 account caps are checked per candidate; a project or unit cap refuses.
- No candidate: refused `no_account_until:<earliest reset>` (or `no_account`), each account passed
  over with its reason on the refusal.
- One registration per account: an id already registered, or a profile directory (per host) that is
  already another account's, is refused `duplicate_account:<existing id>`.
- account_limit: each engine meter keeps the last limit its stream stated (`limit()`: window, reset,
  signal `stream` or `result`). Claude Code: a `rate_limit_event` rejected (stream) or a `result` with
  `is_error` whose text is the usage-limit message "You've hit your <limit> ... resets <time> (<zone>)"
  (result; window from the binary's limit-name table, reset parsed from the stated time and zone, end
  of the stated minute). Codex: the usage-limit / exhaustion message in an `error` event (stream) or a
  `turn.failed` (result). `control_accounts.classify` turns the outcome into `account_limit` with the
  window and reset: a result signal always, a stream signal unless the run completed. The final ledger
  report carries outcome `account_limit` and `limit`.
- The re-run-or-ask decision is `control_account_limit.decide(record, servers, marks, provider)` over
  the fixture record form of the spec's Notes; MCP calls read by each engine module's `mcp_calls`.
- extract_formats.py (VELDO-0062 proof) extended: Claude's usage-limit message pieces and limit names,
  Codex's exec `mcp_tool_call` item. Footprint gains proof/VELDO-0062/extract_formats.py and
  cli-formats.json (the lead allowed extending it).

## Progress log
- 2026-09-26T11:57:42Z suite 78 written, 14 rows green in 9.8 s; next: red record, mutations
- 2026-09-26T12:18:41Z consumer suites green (47); next: validate, footprint, anchors, drive, README, History
- 2026-09-26T13:07:51Z done: finding 160 35 rejected; 36/39/40/41/62 reject; proof complete

## Review round 1 (reviewer notes rv160/notes.md, probe probe_decide.py, extra_mutants.py)

- BLOCKING fixed: `control_account_limit` no longer decides `rerun` over an engine line it cannot read.
  A readable event is a JSON object (or its JSON text) naming its `type`; any other engine payload, and
  any block the engine module cannot read as a tool call (Claude Code: an assistant message whose
  content is not a list, a block that is not an object naming its type, a `tool_use` whose name is not a
  string; Codex: an item that is not an object naming its type, an `mcp_tool_call` whose server or tool
  is not a name), is named in `calls` by its sequence, reason `unreadable`, or `redacted_unreadable`
  when the line's `redacted` field is set. The decision is then `ask`. A structurally malformed record
  (fields, sequence, stream, receive time) stays refused by name. `mcp_calls` counts the calls read.
  The probe now prints ask for truncated JSON, a redacted span, '[redacted]', a list payload and a
  non-string name.
- Same id read-only then write: a call is keyed by (id, server, tool), so the write counts (ask).
- Claude Code rejected texts: the binary's nFn `overageStatus === "rejected"` branch returns six texts
  that do not start "You've hit your" (eight strings: out of usage credits, org out of usage twice, seat
  type twice, service disabled, admin allocation, $0 group). extract_formats.py reads each by its exact
  return inside that branch, plus the kke() admin suffix; cli-formats.json gains `rejected`,
  `admin_suffix`, `admin_suffixed`, `rejected_source`. `control_engine_claude.LIMIT_REJECTED` holds the
  same eight prefixes; each is the `unified` window with the reset it states, if any.
- The four surviving extra mutants each have a row now: `pool/usage-observes` (a Codex account observed
  by usage alone admits its concurrency of two), `pool/selection-order` (0.7 / 0.1 / 0.1 / unknown: the
  lowest utilization, least recently used among equals, unknown last; the trace's candidate order),
  `pool/until-earliest` (four accounts limited, one with two windows: the refusal names the earliest
  account reopening, not the latest and not a first-window reset).
- Main is still 52f817d5 (the branch's base): the merge is a no-op.

## Rule A, the lead's allowlist (fail closed on built-in tools)

- Each check round found another Claude Code built-in tool acting outside the run (SendMessage to another session,
  Agent with isolation remote, the claude.ai-writing tools, self_hosted_runner_spawn_local, PushNotification), none
  caught with no write-capable MCP server. Listing outward tools is never complete, so the decision now fails closed on
  an allowlist read from the 2.1.281 and 0.154.0 bytes into cli-formats.json (`tool_forms.in_run`).
- Claude Code allowlist (each name's binding and the tool's definition read from the bytes, with its aliases): Read,
  Write, Edit, NotebookEdit, Glob, Grep, TodoWrite, ToolSearch; Bash, TaskStop (KillShell, KillBash), Monitor; WebFetch,
  WebSearch; Agent (Task), Skill, REPL, Workflow (RunWorkflow), CronCreate. The binary has no LS tool. An allowlisted
  call still asks when: the Agent tool's input has isolation remote, or names an agent definition that is not built in
  (the binary resolves `input.isolation ?? definition.isolation`, and an agent file may set remote; no built-in
  definition sets isolation), or its input is shown nowhere (a depth-2 agent: a task's last tool with no shown call); a
  file tool or Bash names another machine in `_host` (routed only when the remote-tools gate is on; `cNn()` returns
  false in this build, so it is inert today); a task frame's type is not an allowlisted tool's (`remote_agent`, `dream`,
  `auto_mode_scan`, any unlisted one); a workflow agent reports isolation remote; any tool-call block that is not
  `tool_use` (a server tool, an API-side MCP call); a tool name that cannot be read. A CronCreate that may be durable
  and any RemoteTrigger call stay the remote_agent rule's (named once).
- Codex: exec's own items are the known in-run kinds; `collab_tool_call` only for the collab tools of exec's CollabTool
  enum (spawn_agent, send_input, close_agent: the variant run between its usage fields and ThreadEvent). A `wait` tool,
  if exec prints one, is not in that run and asks.
- Left to the rules after A (named for the lead): an engine line that is not a readable event at all (a redaction
  that breaks the JSON) and an unknown message or event type are still rule 1's (re-run with no write-capable server);
  a project agent file that overrides a built-in agent's name with isolation remote is not visible in the record.
- FOLLOW-UP for the lead (VELDO-0155 baseline): pass the same allowlist to the engine (Claude Code's tool selection,
  so every tool off the allowlist is OFF for the run, nested agents included, and not only caught afterwards; and
  Codex's collab and feature switches likewise). Rule A catches what the stream shows; only the engine-side allowlist
  covers a depth-2 agent's or a workflow agent's calls, which the stream does not show.
