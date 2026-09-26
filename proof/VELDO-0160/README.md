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
lines with the engine module's own reader (`mcp_calls`: Claude Code's `tool_use` block named
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

**control_launch.py has two small hunks.** `Runner.prepare` (the pool branch and the account the
contract records) and `Metering.settle` (the classification and its `limit`). The VELDO-0060/0061
integration rewrites the receiver's engine hooks elsewhere in that file; its `Metering.settle` hunk
sets `outcome = 'failed'` for a completed run without a complete terminal record, and on merge that
line belongs before the classification so a stream-reported limit on such a run is still classified.

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
`admin_suffixed`). Every line the suite's fakes print and every engine payload of the fixture records
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
| AC3 | `decision/ask` (declared), `decision/rerun`, `decision/unreadable-asks`, `decision/same-id-write` |
| AC4 | `pool/moved-off`, `pool/added-account`, `pool/one-run-while-unknown` (each declared), `pool/usage-observes`, `pool/selection-order`, `pool/until-earliest` |
| Install | `install/assets` |
| Fixtures | `format/claude-fake-lines`, `format/codex-fake-lines` |

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
the write. `limit/claude-rejected-texts` (AC2): each of the binary's eight rejected-status texts (the
two admin ones with their suffix, and the out-of-credits one again with a reset and the progress
piece) ends a run `account_limit`, the `unified` window with the reset it states, recorded exhausted.
`pool/usage-observes` (AC4): a Codex account whose one run reported usage and no window admits its
concurrency of two (three Codex dispatches at once, two on it). `pool/selection-order`: with the idle
Claude Code accounts at 0.7, 0.1, 0.1 (used last) and unknown, the dispatch goes to the 0.1 account used
least recently and the trace ranks them in exactly that order, unknown last. `pool/until-earliest`: with
all four limited (resets 900, 600, 1200 s ahead, and one at 300 s on its five-hour window with its weekly
window to 1500 s) the dispatch is refused `no_account_until` the 600 s reset. `install/assets`: the scaffold lays down both new
modules (not validator substrate) and every engine copy of a module this work touches is identical.

Plain run: 45 passed (26 preamble, 19 rows) in 24.4 s. Stage environment run (`env -i`, the stage's
variables, TZ=UTC): 45 passed in 23.9 s.

## Red record

`red-at-52f817d5.json`: the current suite over `git archive 52f817d5` (main before this work),
unchanged. All 17 behavior rows fail by their own assertion: there is no account pool (the Runner given
a pool refuses `invalid_input` and nothing is dispatched), the same login registers twice under two
names and a second record of an id is refused unnamed, no run is classified `account_limit` (each limited
run ends `failed`), Claude Code's rate-limit result records no window, there is no decision module, and
the scaffold lays down neither new module. The two `format/*` rows are green there, as they must be:
they check the suite's own fixtures against the extracted table, not production.

## Mutations (finding 160)

Registered in `scripts/check_teeth_mutations.py`, each criterion's declared falsifier first;
`drive.py` records `mutations.json` and one applied diff per mutant. All 48 turn their named rows red by assertion; the baseline and the no-op copy of every module are green (serial 1425 s).

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
| pool-not-scaffolded | init_scaffold.py | `install/assets` |
| decision-not-scaffolded | init_scaffold.py | `install/assets` |

Finding 36's `reservation-report-before-enforcement` now copies the guard's report call with its
`limit` argument. `check_teeth_mutations.py --finding 160 --jobs 2`: 48 rejected (the review round re-ran 36: 20 and 62: 50, both rejecting). The other findings with mutations in the modules this changes still reject: 36 (20), 39 (30), 40 (22), 41 (34) and 62 (50).

Suites run, plain, all green: `78_veldo_0160_account_pool`, `75_veldo_0062_accounts`, the suites of
every module this touches (VELDO-0036, 0039, 0040, 0041, 0047, 0049, 0050, 0052, 0053, 0056, 0076, 0128,
0132, 0135) and every suite that reads `init_scaffold.py` (32 more, `50_git_environment` among them).
Under the stage environment: `78_veldo_0160_account_pool`, `75_veldo_0062_accounts`,
`58_veldo_0036_reservations`, `62_veldo_0039_dispatch` and `50_git_environment`.
