# VELDO-0160 proof: every registered account at once, off an account at its limit, and a limited run classified and decided re-run or ask

## The design as built

**The pool is chosen inside the worker reservation.** `control_account_pool` is the account pool. The
Runner takes a `Pool` as its account (`control_launch.Runner(..., account=Pool(adapters))`, where
`adapters` names the engine and host of each adapter), and `Runner.prepare` asks it to reserve the
dispatch's slot: `Pool.reserve` calls VELDO-0036's new `Reservations.reserve_pooled`, whose store
transition runs `control_account_pool.choose` inside the same transaction that takes the slot. The
account records (VELDO-0062's `control_accounts`) and the slots held are read in that transaction, so
two preparations never both take an account's last slot, and the pool is read at every dispatch: an
account the owner registers while work runs is a candidate at the next dispatch, with nothing
restarted. A Runner given an account id, as before, reserves on that account unchanged.

**The candidates and the order.** The candidates are the accounts of the adapter's engine that are
active, have a profile on the adapter's host, are outside every rate-limit window their CLI reported
(`control_accounts.blocking`) and are under their concurrency. An account with no observation (no
window on its record and no usage its CLI reported in the ledger) admits one run at a time until its
first observation. Each candidate's VELDO-0036 account caps are checked in turn; a project or unit cap
refuses the dispatch. The order is the lowest last reported utilization on the tightest window (the
highest utilization among the windows whose reported reset has not passed; unknown after every known
one), then the fewest active runs, then the least recently used (the latest slot or invocation the
ledger holds for the account), then the id. The worker record keeps the choice: the engine and host,
every candidate with its utilization, active runs and last use, the reason each other account was
passed over, and the windows read at selection.

**No candidate: the dispatch waits.** The reservation refuses `no_account_until:<earliest reset>`
(`no_account` when no reset is known), and the refusal carries each account's reason:
`account_limit:<window>` (at its limit), `account_unobserved:one_run` (no observation yet, at its
one-run bound), `account_concurrency`, `account_status:<status>`, `account_profile:<host>` or the
VELDO-0036 account cap. The reservation's observation of the refusal names the same reasons.

**One registration per account.** `control_accounts` refuses an id already registered, and a profile
directory already registered for another account on the same host (the same login under another
name), by name: `duplicate_account:<the registered id>`. The local helper already refuses a second
`account add` of one name.

**A run stopped by its account's limit ends `account_limit`.** Each engine meter keeps the last limit
its stream stated (`limit()`: window, reset and signal). Claude Code: a `rate_limit_event` whose status
is `rejected` is the stream reporting its window exhausted (`stream`); a `result` with `is_error` whose
text is the binary's usage-limit message is the engine's rate-limit result (`result`), its window read
from the binary's own table of limit names and its reset from the time and zone the message states (the
end of the stated minute), and it is recorded on the account as a window too. The binary's other
rejected-status texts, which do not start "You've hit your" (out of usage credits, with the reset it may
state; the org, seat, service, admin and $0-group texts), are the `unified` window the same way. A later event reporting
the same window open again ends the stream's limit. The binary's other 429 message ("Server is
temporarily limiting requests (not your usage limit)") is not the account's limit. Codex: the
usage-limit or exhaustion message in an `error` event is `stream`, in a `turn.failed` it is `result`
(VELDO-0062 already read both as windows). At the end, `control_accounts.classify` turns the outcome into
`account_limit` with the window and reset: a `result` signal always, a `stream` signal unless the run
completed. The receiver's one final report (`Metering.settle`) carries the outcome and its `limit`
({window, reset_at, signal}) to the ledger (`Reservations.report` accepts `account_limit` only with a
limit, on a final report). `control_account_pool.metrics` counts dispatches per account and runs ended
`account_limit` per account and window.

**The re-run-or-ask decision is over a record.** `control_account_limit.decide(record, servers,
marks, provider)` reads a fixture record in the form of the specification's Notes (each line's gapless
`sequence`, `received_at`, `stream`, `redacted` and `payload`), finds each MCP tool call on the engine
lines with the engine module's own reader (`tool_calls`: Claude Code's `tool_use` block named
`mcp__<server>__<tool>`, Codex's `mcp_tool_call` item), each call once by its id, and decides `rerun`
when every call is to a tool the call's server's configured revision marks read-only, else `ask`,
naming exactly the other calls with their sequence, server, tool, catalog id, revision and reason
(`not_marked_read_only`, `server_not_configured`). A revision that marks nothing marks no tool. A call
is one id with one server and tool, so an id shown read-only and then naming a write counts the write.
An engine line the decision cannot read asks, never re-runs: a payload that is not a readable event (a
JSON object, or its JSON text, naming its `type`), or a block the engine module cannot read as a tool
call (Claude Code: an assistant message without a content list, a block that is not an object naming its
type, a `tool_use` whose name is not a string; Codex: an item that is not an object naming its type, an
`mcp_tool_call` whose server or tool is not a name), is named by its sequence with reason `unreadable`,
or `redacted_unreadable` when the line's `redacted` field is set (VELDO-0141 AC4 redacts spans inside
the payload text, which can break the JSON). A structurally malformed record or configuration is refused
by name, never decided. Carrying the decision out is VELDO-0154 AC3.

**A tool-call form the decision does not recognize asks (the lead's decision, fail closed).** Each
engine module reads only the forms its binary's own tables list (`cli-formats.json`, `tool_forms`) and
names any other an unknown call, which the decision names by its sequence with its `form`, reason
`unknown_call`. Claude Code: the stream's message types and the subtypes of `system` and `result`
(`MESSAGES`), the content blocks of an assistant message and of a user message, of which text,
reasoning, compaction and (in a user message) images, documents and search results are tool-free; a
`tool_use` is read (an `mcp__` name is an MCP call, every id is remembered), and an `mcp_tool_use`,
`mcp_tool_result`, `server_tool_use` or other server-tool block is unknown; a user `tool_result`, a
`tool_progress` or a `tool_use_summary` for an id no earlier line showed is unknown, as is a `tool_use`
in a user message; a `stream_event` carrying any block that is not tool-free (a `tool_use` first) is
unknown, and so is a streaming event the schema does not name. On a line whose `redacted` field is set,
a `tool_use` name that is neither `mcp__...` nor in the binary's `BUILTIN_TOOL_NAMES` (a partial list,
so an omitted built-in asks) is `redacted_unreadable`. Codex: exec's event types and item types; its
messages, reasoning, to-do lists and errors are tool-free, its commands, file changes and web searches
are its own tools whose effects stay in the clone, `mcp_tool_call` is read, and every other item type
(the core's `dynamic_tool_call`, `collab_agent_tool_call` and `sub_agent_activity` among them) and every
other event type is unknown.

**The tool names a Claude Code frame carries beside its content blocks count (the second check).** The
REPL tool's inner calls reach the stream only as a `tool_progress` of the REPL call carrying a
`repl_call` {inner_tool_name, inner_tool_input, inner_tool_use_id, phase} that the binary's two emitters
write and its schema omits, never as `tool_use` blocks: an `mcp__` inner name is that MCP call, a
built-in one no call, any other an unknown call (`repl_call:<name>`), and a `repl_call` that is not an
object naming its inner tool is `unreadable`. The other fields that name a tool that ran are read the
way a `tool_use` name is (`mcp__<server>__<tool>` is that call; on a redacted line a name neither
`mcp__...` nor built in is `redacted_unreadable`): a `tool_progress`'s own `tool_name` (a heartbeat of
an MCP call), a `system/task_progress`'s `last_tool_name` and its `workflow_progress` entries'
`lastToolName` (the workflow agents' progress, which the schema omits), and an assistant message's
`attribution_mcp_server` / `attribution_mcp_tool` and `batch_tool_uses` names. `TOOL_FIELDS` lists every
field of the binary's messages whose name names a tool, declared or emitted, with how it is read (`call`,
`id`, or `free`: a count, a display or input copy of a block read in the content, a tool the run offers
or discovered, a call denied or deferred and never run). The binary's `BUILTIN_TOOL_NAMES` lists the
Agent tool under its old name `Task`; the tool's definition (`name:mt ... aliases:[am]`, with
`mt="Agent"` and `am="Task"` bound beside its own description) gives its current name, so `Agent` is
built in (`BUILTIN_RENAMED`). The frames the CLI writes outside the SDK message union (the StdoutMessage
members) are read by the binary's table: `keep_alive`, `control_cancel_request`, `active_goal`,
`autocompact_state` and the `post_turn_summary` and `task_summary` system messages carry only literals,
enums, strings, numbers and booleans and no field naming a tool, so they are no call; a
`control_request` (a `can_use_tool` names a tool and its input), a `control_response` (a free-form
record) and the `transcript_mirror` (transcript entries of any shape) cannot be shown tool-free and stay
unknown calls. Codex: exec's own `collab_tool_call` (its sub-agent call; the agents' own calls are not in
exec's stream) is now in exec's item table and is an unknown call (`SUBAGENT_ITEMS`).

**control_launch.py has two small hunks.** `Runner.prepare` (the pool branch; the contract records the
chosen account id, never the pool) and `Metering.settle` (the classification and its `limit`). Merged
with main (VELDO-0060 and VELDO-0061), settle runs: close the meter, take the exit's outcome, keep the
artifact (`self.report = self._artifact(...)`), make a completion without a complete terminal record
`failed`, then `ACC.classify(outcome, self.meter.limit())`, then the guard's final report with the
`limit`; so a limit the stream stated on a run whose terminal record is missing is still
`account_limit`. THE ENGINE PROTOCOL's docstring names the meters' `limit()`; `ENGINE_PROTOCOL` stays
the ten module names it checks.

Out of this build: the re-dispatch and the question to the owner (VELDO-0154 AC3), the timer at the
earliest reset (VELDO-0154 AC1), a count of decisions by outcome (the decision is a pure function; its
caller records it), the Mac read-back (VELDO-0147), and the live run of the real CLIs on the owner's
subscriptions.

## Where each format comes from

`proof/VELDO-0062/extract_formats.py` now also reads, from the same binaries' bytes and without running
either: Claude Code's usage-limit message (the template "You've hit your ${limit}${suffix}", the
" · resets " piece, the table of limit names by window, the en-US time formats with the
resolved zone in parentheses, and the 429 text that is not the account's limit), and Codex exec's
`mcp_tool_call` item (its type name, the field names server, arguments and result, and the status
values in the binary's literal runs; `id`, `type` and `tool` are names of four bytes or fewer that the
compiler keeps out of the literal pool). `cli-formats.json` is regenerated and `--check` matches the
installed binaries. The review round added Claude Code's other rejected-status texts: each return of the
message builder's `overageStatus === "rejected"` branch that is not the template, read by its exact text
inside that branch, and the admin suffix two of them take (`rejected`, `admin_suffix`,
`admin_suffixed`). The fail-closed round added `tool_forms` for both engines: Claude Code's SDK message
union (each member's type and subtype), the content block unions of an assistant and of a user message
(the modelled blocks and the type tags the binary lists), the streaming events the `stream_event` schema
names and the binary's `BUILTIN_TOOL_NAMES`; Codex exec's ThreadItem tags (its literal run, and `error`)
and the core's ThreadItem tags (its literal run, where `dynamic_tool_call`, `collab_agent_tool_call`
and `sub_agent_activity` are listed). The second check's round added: `builtin_renamed` (the Agent
tool's current name and its alias on `BUILTIN_TOOL_NAMES`, from its definition and the statement binding
its names), `tool_fields` (each SDK message's fields whose name names a tool, from its zod schema),
`emitted_tool_fields` (the REPL `repl_call` from both of its emitters, a task's `workflow_progress`
entries' `lastToolName` from the task_progress emitter and the workflow agent progress), `frames` (the
StdoutMessage members outside the SDK union, each with whether its schema is provably tool-free) and, for
Codex, exec's `collab_tool_call` (the literal after exec's `ItemUpdatedEvent` and `ThreadErrorEvent`
names). `format/tool-forms` requires the readers' tables to equal these. Every line the suite's fakes print and every engine payload of the fixture records
conforms to that table (the two format rows).

## Suite

`scripts/suites/78_veldo_0160_account_pool.py`
(`python3 scripts/selftest.py --suite 78_veldo_0160_account_pool`). Real: a SQLite control store with
OpenSSH journal signatures, the account records the owner registers over profiles the helper prepares,
VELDO-0036 reservations under their production authorization with the pool choosing inside them, the
VELDO-0052 Gate, VELDO-0031 claims, a Git source, the VELDO-0039 Runner and receiver processes and the
trusted wrapper. The engines are fake `claude` and `codex` executables that record their birth
environment and print scripted lines in the installed CLIs' formats, waiting on files the suite creates
where the script says, so concurrency is observed rather than timed. No real engine runs.

| Criterion | Rows |
|---|---|
| AC1 | `pool/per-account-isolation` (declared falsifier), `pool/one-registration` (declared), `pool/concurrent` (declared) |
| AC2 | `limit/rate-limit-result` (declared), `limit/stream-exhausted`, `limit/claude-rejected-texts` |
| AC3 | `decision/ask` (declared), `decision/rerun`, `decision/unreadable-asks`, `decision/same-id-write`, `decision/unknown-forms`, `decision/redacted-name`, `decision/tool-free-forms`, `decision/repl-inner-call`, `decision/task-progress-tool`, `decision/frame-tool-names` |
| AC4 | `pool/moved-off`, `pool/added-account`, `pool/one-run-while-unknown` (each declared), `pool/usage-observes`, `pool/selection-order`, `pool/until-earliest` |
| Install | `install/assets` |
| Fixtures | `format/claude-fake-lines`, `format/codex-fake-lines`, `format/tool-forms` |

`pool/*` (AC1): three Claude Code accounts and one Codex account, registered once each, take four
pooled dispatches at once: the three Claude Code dispatches go to the three Claude Code accounts and the
Codex one to the Codex account, each engine on exactly its own registered profile and no other
provider's, the four profiles different, each invocation reserved and settled on its account with the
tokens its own CLI reported, the shown usage per account equal to its run's, the slot's selection trace
naming the choice, and the dispatch counts one per account; all four were accepted and running before
any ended, their recorded start and end times overlap and the four engine processes were alive at once;
a second record of an id, the same Claude Code and Codex login under another name (the Codex one with a
trailing separator) are refused by name with no second record, and a new login registers.
`pool/moved-off` (AC4): after acct-c1's CLI reports its five-hour window exhausted with a reset 12 s
ahead, the next two dispatches go to acct-c2 and acct-c3, and a third, with both busy, is refused before
anything is prepared as `no_account_until:<that reset>` with acct-c1 passed over at its limit (the
observation names the same reasons); no slot and no process reach acct-c1 before its reset, and at the
reset acct-c1 takes the next dispatch while the other two are busy. `pool/added-account`: with the three
Claude Code accounts running, the owner registers a fourth (concurrency two) and the next dispatch
launches on it, while the preparing process and all three running workers keep their pid, start time
and boot id. `pool/one-run-while-unknown`: before the new account's first observation a second unit is
refused `no_account` with the new account at `account_unobserved:one_run`; once its running unit
reports a window the waiting unit launches on it as its second run. `limit/*` (AC2): for Claude Code
and Codex, a stream reporting its window exhausted and an engine ending with its rate-limit result are
each classified `account_limit` with exactly the window, reset and signal the stream stated, recorded on
the account (exhausted, the source dispatch) and counted per account and window; an ordinary nonzero
exit of each engine, a Claude Code window reported exhausted and then open again, and Claude Code's 429
that is not the account's limit each end `failed` with no limit and no exhausted window. `decision/*`
(AC3): for both engines, a record with no MCP call and one with only calls to tools marked read-only
decide re-run naming nothing; a call to a tool not marked read-only, a call to a tool of a server whose
revision marks nothing and a call to a server the configuration does not list each decide ask naming
exactly that call (sequence, server, tool, catalog id, revision, reason), a call shown twice named once;
a record with a sequence gap is refused by name. `decision/unreadable-asks`: for both engines, an engine
line holding a write whose JSON text is truncated, whose input is a `[REDACTED:high_entropy]` span that
breaks the JSON, that is wholly `[redacted]`, that is wrapped in a list, or whose tool name (Claude Code)
or server (Codex) is not a string decides ask naming exactly that line (`redacted_unreadable` for the
two redacted forms, `unreadable` for the rest), and a redacted line whose event still reads is decided by
its calls. `decision/same-id-write`: one id shown read-only and then naming a write decides ask naming
the write. `decision/unknown-forms`: each of 16 Claude Code forms (an `mcp_tool_use`, an `mcp_tool_result`
and a `server_tool_use` block, a `stream_event` starting a `tool_use` block, one starting a message that
holds a `tool_use`, a streaming event the schema does not name, a user `tool_result` for an id never
seen, a `tool_use` in a user message, a `tool_progress` and a `tool_use_summary` for an id never seen,
a block, message and system subtype no table lists, and the `control_request`, `control_response` and
`transcript_mirror` frames outside the message union) and 6 Codex forms (exec's own `collab_tool_call`,
the core's `dynamic_tool_call`, `collab_agent_tool_call`, `sub_agent_activity`, an item and an event type
no table lists) decides ask,
naming exactly that line as `unknown_call` with its form and counting no MCP call.
`decision/redacted-name`: on a redacted line a `tool_use` named `[REDACTED:known_pattern]` or
`NotebookRead` (a name neither `mcp__` nor built in) decides ask as `redacted_unreadable`, one named
`Agent` (the Agent tool's current name, built in), `Read` or `mcp__tracker__get_issue` (read-only)
decides re-run. `decision/repl-inner-call`: after a REPL `tool_use`, a `tool_progress` of it whose
`repl_call` names `mcp__tracker__add_comment` (the checker's reproduction) or, in its end phase only,
`mcp__wiki__write_page` decides ask naming that line, server and tool; an inner tool neither `mcp__` nor
built in asks as `unknown_call` form `repl_call:RemoteTrigger`; a `repl_call` that is not an object, has
no inner name or a non-string one asks `unreadable`; an inner read-only MCP call (counted) and an inner
`Read` decide re-run. `decision/task-progress-tool`: after an `Agent` call and its `task_started`, a
`task_progress` whose `last_tool_name` is an MCP write (the checker's reproduction) asks naming it, the
same last tool on two lines is one call, a workflow agent's `lastToolName` naming a write asks; a
non-string last tool, a `workflow_progress` that is not a list and an entry that is not an object ask
`unreadable`; a read-only last tool and `Bash` decide re-run. `decision/frame-tool-names`: a
`tool_progress` of a shown call naming an MCP write asks naming it, an MCP write and its heartbeat are
one call, an assistant message whose `attribution_mcp_server` and `attribution_mcp_tool` name a write,
and one whose `batch_tool_uses` holds a write, ask naming them; an attribution that is not a name asks
`unreadable`; a heartbeat of the shown REPL call decides re-run. `decision/tool-free-forms` (the negative control):
21 Claude Code lines of tool-free forms, of a `Bash` call's result, progress, heartbeat and summary, of
the six tool-free frames outside the message union, of a REPL call whose inner tool is `Read` and of a
task whose last tool and workflow agent's are built in, and 7 Codex items of exec's tool-free and
own-tool types, decide re-run naming nothing. `format/tool-forms`: the
readers' tables equal the binaries' (`cli-formats.json`): the message, block, streaming event and
built-in tables, the built-in names with the Agent tool's current one, every tool-named field declared
or emitted (the six read as calls named), the tool-free frames, and exec's items with `collab_tool_call`
a sub-agent call; each named fixture form is one the binaries list and each unlisted one is in no
table. `limit/claude-rejected-texts` (AC2): each of the binary's eight rejected-status texts (the
two admin ones with their suffix, and the out-of-credits one again with a reset and the progress
piece) ends a run `account_limit`, the `unified` window with the reset it states, recorded exhausted.
`pool/usage-observes` (AC4): a Codex account whose one run reported usage and no window admits its
concurrency of two (three Codex dispatches at once, two on it). `pool/selection-order`: with the idle
Claude Code accounts at 0.7, 0.1, 0.1 (used last) and unknown, the dispatch goes to the 0.1 account used
least recently and the trace ranks them in exactly that order, unknown last. `pool/until-earliest`: with
all four limited (resets 900, 600, 1200 s ahead, and one at 300 s on its five-hour window with its weekly
window to 1500 s) the dispatch is refused `no_account_until` the 600 s reset. `install/assets`: the scaffold lays down both new
modules (not validator substrate) and every engine copy of a module this work touches is identical.

Plain run after the merge with main: 49 passed (26 preamble, 23 rows) in 19.3 s. Stage environment run
(`env -i`, the stage's variables, TZ=UTC): 49 passed in 24.5 s. After the merge the fake `claude` is
installed, pinned and qualified as version 2.1.281 under the factory state root and the fake Codex is a
qualified vendor package (VELDO-0060, VELDO-0061), as suite 75 does.

## Red record

`red-at-52f817d5.json`: the current suite over `git archive 52f817d5` (main before this work),
unchanged, regenerated after the merge and the fail-closed round. All 21 behavior rows fail by their own
assertion: there is no account pool (the Runner given
a pool refuses `invalid_input` and nothing is dispatched), the same login registers twice under two
names and a second record of an id is refused unnamed, no run is classified `account_limit` (each limited
run ends `failed`), Claude Code's rate-limit result records no window, there is no decision module, the
readers have no tool-call form tables, and the scaffold lays down neither new module. The two `format/*` rows are green there, as they must be:
they check the suite's own fixtures against the extracted table, not production.

## Mutations (finding 160)

Registered in `scripts/check_teeth_mutations.py`, each criterion's declared falsifier first;
`drive.py` records `mutations.json` and one applied diff per mutant. All 65 turn their named rows red by assertion; the baseline and the no-op copy of every module are green (serial 1878 s, after the merge with main).

| Mutant | Module | Named rows |
|---|---|---|
| pool-shared-profile (AC1 falsifier: one shared profile) | control_accounts.py | `pool/per-account-isolation` |
| pool-second-registration-accepted (AC1 falsifier) | control_accounts.py | `pool/one-registration` |
| pool-duplicate-id-unnamed | control_accounts.py | `pool/one-registration` |
| pool-launches-serialized (AC1 falsifier) | control_account_pool.py | `pool/concurrent` |
| pool-selection-untraced | control_reservations.py | `pool/per-account-isolation` |
| limit-result-ordinary (AC2 falsifier) | control_accounts.py | `limit/rate-limit-result` |
| limit-claude-result-unread | control_engine_claude.py | `limit/rate-limit-result` |
| limit-claude-any-error-result | control_engine_claude.py | `limit/rate-limit-result` |
| limit-claude-reset-minute-start | control_engine_claude.py | `limit/rate-limit-result` |
| limit-codex-failed-turn-unread | control_engine_codex.py | `limit/rate-limit-result` |
| limit-stream-unclassified | control_accounts.py | `limit/stream-exhausted` |
| limit-claude-rejected-unread | control_engine_claude.py | `limit/stream-exhausted` |
| limit-reopened-window-kept | control_engine_claude.py | `limit/stream-exhausted` |
| limit-every-failure | control_accounts.py | `limit/stream-exhausted`, `limit/rate-limit-result` |
| limit-unreported | control_launch.py | `limit/stream-exhausted`, `limit/rate-limit-result` |
| decision-ask-reruns (AC3 falsifier) | control_account_limit.py | `decision/ask` |
| decision-unlisted-server-read-only | control_account_limit.py | `decision/ask` |
| decision-unmarked-revision-read-only | control_account_limit.py | `decision/ask` |
| decision-claude-calls-unread | control_engine_claude.py | `decision/ask` |
| decision-codex-calls-unread | control_engine_codex.py | `decision/ask` |
| decision-call-named-twice | control_account_limit.py | `decision/ask` |
| decision-read-only-asks | control_account_limit.py | `decision/rerun` |
| decision-gap-accepted | control_account_limit.py | `decision/ask` |
| pool-inside-window (AC4 falsifier) | control_account_pool.py | `pool/moved-off` |
| pool-read-at-start (AC4 falsifier) | control_account_pool.py | `pool/added-account` |
| pool-unobserved-unbounded (AC4 falsifier) | control_account_pool.py | `pool/one-run-while-unknown` |
| pool-usage-unobserved | control_account_pool.py | `pool/one-run-while-unknown` |
| pool-concurrency-ignored | control_account_pool.py | `pool/moved-off` |
| pool-reset-unnamed | control_account_pool.py | `pool/moved-off` |
| pool-read-once-per-runner | control_launch.py | `pool/concurrent`, `pool/added-account` |
| pool-refusal-reasons-unobserved | control_reservations.py | `pool/moved-off` |
| pool-limit-uncounted | control_account_pool.py | `limit/stream-exhausted`, `limit/rate-limit-result` |
| pool-dispatches-uncounted | control_account_pool.py | `pool/per-account-isolation` |
| decision-unreadable-line-skipped (review, blocking) | control_account_limit.py | `decision/unreadable-asks` |
| decision-unreadable-call-skipped (review, blocking) | control_account_limit.py | `decision/unreadable-asks` |
| decision-event-any-object | control_account_limit.py | `decision/unreadable-asks` |
| decision-claude-nameless-call-skipped | control_engine_claude.py | `decision/unreadable-asks` |
| decision-codex-serverless-call-skipped | control_engine_codex.py | `decision/unreadable-asks` |
| decision-redaction-unread | control_account_limit.py | `decision/unreadable-asks` |
| decision-same-id-first-wins | control_account_limit.py | `decision/same-id-write` |
| limit-claude-rejected-texts-unread | control_engine_claude.py | `limit/claude-rejected-texts` |
| pool-observed-by-window-only | control_account_pool.py | `pool/usage-observes` |
| pool-highest-utilization-first | control_account_pool.py | `pool/selection-order` |
| pool-most-recently-used-first | control_account_pool.py | `pool/selection-order` |
| pool-until-latest-reset | control_account_pool.py | `pool/until-earliest` |
| pool-until-first-window-reset | control_account_pool.py | `pool/until-earliest` |
| decision-unknown-call-skipped (the lead's decision) | control_account_limit.py | `decision/unknown-forms` |
| decision-claude-server-tool-blocks-free | control_engine_claude.py | `decision/unknown-forms` |
| decision-claude-unseen-result-free | control_engine_claude.py | `decision/unknown-forms` |
| decision-claude-streamed-tool-use-free | control_engine_claude.py | `decision/unknown-forms` |
| decision-claude-unlisted-message-free | control_engine_claude.py | `decision/unknown-forms` |
| decision-claude-unlisted-stream-event-free | control_engine_claude.py | `decision/unknown-forms` |
| decision-claude-unseen-progress-free | control_engine_claude.py | `decision/unknown-forms` |
| decision-codex-unlisted-item-free | control_engine_codex.py | `decision/unknown-forms` |
| decision-codex-unlisted-event-free | control_engine_codex.py | `decision/unknown-forms` |
| decision-redacted-name-trusted | control_engine_claude.py | `decision/redacted-name` |
| decision-redaction-not-passed | control_account_limit.py | `decision/redacted-name` |
| decision-shown-ids-per-line | control_account_limit.py | `decision/tool-free-forms` |
| decision-claude-tool-ids-unremembered | control_engine_claude.py | `decision/tool-free-forms` |
| decision-codex-builtin-items-ask | control_engine_codex.py | `decision/tool-free-forms` |
| decision-claude-thinking-asks | control_engine_claude.py | `decision/tool-free-forms` |
| format-claude-builtin-table-drifts | control_engine_claude.py | `decision/redacted-name`, `format/tool-forms` |
| format-codex-dynamic-item-builtin | control_engine_codex.py | `decision/unknown-forms`, `format/tool-forms` |
| pool-not-scaffolded | init_scaffold.py | `install/assets` |
| decision-not-scaffolded | init_scaffold.py | `install/assets` |

Finding 36's `reservation-report-before-enforcement` now copies the guard's report call with its
`limit` argument. `check_teeth_mutations.py --finding 160 --jobs 2`: 65 rejected. After the merge with main: 36 (20), 60 (35), 61 (30) and 62 (50) reject, and every mutation of every registry applies exactly once. Before the merge 39 (30), 40 (22) and 41 (34) also rejected; they were not re-run after it.

Suites run after the merge, plain and under the stage environment, all green:
`78_veldo_0160_account_pool` (23 rows), `78_veldo_0060_claude_adapter` (34), `79_veldo_0061_codex_adapter`
(20), `75_veldo_0062_accounts` (22) and `58_veldo_0036_reservations` (10). Before the merge the suites of
every module this touches and every suite that reads `init_scaffold.py` were run green as well.
