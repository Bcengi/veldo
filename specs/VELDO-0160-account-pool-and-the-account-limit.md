---
schema: veldo.spec/v1
id: VELDO-0160
title: Work runs on every registered subscription account at once, moves off an account at its limit, and a limited run is classified and decided re-run or ask
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W120
plan_revision: 4
depends_on: [VELDO-0036, VELDO-0062]
placement: [fleet, engine, metrics, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/accounts.py"
  - ".veldo/accounts.py"
  - "packs/*/.veldo/accounts.py"
  - "engine/.veldo/control_account*.py"
  - ".veldo/control_account*.py"
  - "packs/*/.veldo/control_account*.py"
  - "engine/.veldo/control_reservation*.py"
  - ".veldo/control_reservation*.py"
  - "packs/*/.veldo/control_reservation*.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "packs/*/.veldo/control_launch*.py"
  - "engine/.veldo/control_engine_claude*.py"
  - ".veldo/control_engine_claude*.py"
  - "packs/*/.veldo/control_engine_claude*.py"
  - "engine/.veldo/control_engine_codex*.py"
  - ".veldo/control_engine_codex*.py"
  - "packs/*/.veldo/control_engine_codex*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0160_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0160-account-pool-and-the-account-limit.md"
  - "specs/index.md"
  - "proof/VELDO-0160/*"
  - "proof/VELDO-0062/extract_formats.py"
  - "proof/VELDO-0062/cli-formats.json"
behavior_bearing: true
observability:
  logs: >
    Record each account selection with its candidates and the reason each other was passed over, each
    run classified `account_limit` with its window and reset time, and each re-run-or-ask decision with
    the calls it named; no secrets.
  metrics: >
    Count dispatches per account, runs ended `account_limit` per account and window, and decisions by
    outcome.
  traces: >
    Join each dispatch to its account, the rate-limit windows read at selection, and each limited run to
    its decision.
  error_taxonomy: >
    Distinguish no candidate account (with the earliest reset), an account at its limit, an account with
    no observation yet at its one-run bound, and a decision that must ask; none is recorded as success.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The owner registers any number of logged-in subscription accounts for each provider, each
      once with its own login, and the factory runs work on all of them at the same time, each with its
      own credentials, usage and rate-limit windows. Set and completeness: Register three Claude Code
      accounts and one Codex account (each its own profile: Claude Code's config directory, Codex's
      home), run concurrent work across them, and read back that each invocation used exactly its own
      account's profile and was charged to that account (the per-account isolation row), that a second
      registration of an already registered account is refused by name (the one-registration row), and
      that the runs' recorded start and end times overlap (the concurrency row). Moving work off an
      account at its limit, adding an account while work runs and the one-run bound of an account with
      no observation are AC4. Falsifier: Launch two accounts' work with one shared profile, and the
      per-account isolation row must fail; accept a second registration of one account, and the
      one-registration row must fail; serialize the pool's launches, and the concurrency row must fail.
    falsified_by: >
      Launch two accounts' work with one shared profile, and the per-account isolation row must fail;
      accept a second registration of one account, and the one-registration row must fail; serialize the
      pool's launches, and the concurrency row must fail.
  - id: AC2
    text: >
      Claim: A run stopped by its account's limit is classified `account_limit` with its window and reset
      time, and no other run is. Set and completeness: Feed the receiver's classification a stream that
      reports its window exhausted, an engine that ends with its rate-limit result, and an ordinary
      nonzero exit, for Claude Code and Codex, and read back `account_limit` with the window and reset
      time recorded on the account for the first two only, and the third ending as the ordinary failure it
      is. Falsifier: Classify a run whose engine ends with its rate-limit result as an ordinary failure;
      the rate-limit classification row must fail.
    falsified_by: >
      Classify a run whose engine ends with its rate-limit result as an ordinary failure; the rate-limit
      classification row must fail.
  - id: AC3
    text: >
      Claim: For a run classified `account_limit`, a re-run-or-ask decision is made over its record:
      re-run on another account only when the record shows no call to an MCP tool not marked read-only,
      and otherwise ask the owner, naming the calls. Set and completeness: Feed the decision fixture
      records in the form the Notes give, with the read-only marks of catalog revisions in the same
      form: one with no MCP call, one with only calls to tools marked read-only, one with a call to a
      tool not marked read-only, and one with a call to a tool of a server whose revision marks nothing;
      the first two decide re-run and the others decide ask with exactly those calls named. Carrying out
      the decision (the new dispatch, or the question to the owner) is VELDO-0154 AC3. Falsifier: Decide
      re-run for a record that shows a call to an MCP tool not marked read-only; the ask-decision row
      must fail.
    falsified_by: >
      Decide re-run for a record that shows a call to an MCP tool not marked read-only; the ask-decision
      row must fail.
  - id: AC4
    text: >
      Claim: New work moves off an account that has reached its limit, an account added while work runs
      takes work with nothing restarted, and an account with no usage observation admits one run at a
      time until its first observation, because unknown is never zero. Set and completeness: With the
      accounts of AC1, exhaust one Claude Code account's allowance and require every new dispatch to go
      to another Claude Code account while nothing is sent to the exhausted one until its reported
      reset. While runs are active, register and log in a fourth Claude Code account and, with the
      other Claude Code accounts at their concurrency, require the next dispatch to launch on it, while
      the process that prepares dispatches and every running worker keep their process identity and
      start time. Before the new account's first observation, offer it two units at once and require one
      launched and the other waiting until that run reports its first observation. Falsifier: Choose an
      account inside its reported rate-limit window, and the moved-off row must fail; read the account
      pool only when the Runner starts, and the added-account row must fail; admit a second concurrent
      run on an account with no observation, and the one-run-while-unknown row must fail.
    falsified_by: >
      Three mutants, one per claim: choose an account inside its reported rate-limit window, and the
      moved-off row must fail; read the account pool only when the Runner starts, and the added-account
      row must fail; admit a second concurrent run on an account with no observation, and the
      one-run-while-unknown row must fail.
required_evidence: [unit, integration]
rollback: >
  Run on one account per provider, as before, and stop every account-limited run for the owner; account
  records, usage and rate-limit windows are kept. No automatic rollback is authorized.
---

## Intent

The owner has several logged-in subscription accounts per provider and wants all of them working:
work spreads across them, moves off one at its limit, and a run stopped by a limit is started again on
another account when that is safe, or put to him when it may already have written somewhere.

## Context

W120 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1. The owner widened
VELDO-0062 on 2026-09-25 (Telegram 29127 asked, 29128 "yes, widen"), and section 8 of the approved
[operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner Telegram 29162)
designs the pool, the selection order, the limit and the re-run rule; its section 12 builds this with
VELDO-0062 as item 1. AC1 is VELDO-0062's former AC5 and AC2 and AC3 its former AC6, split out on the
third review of revision 4 because VELDO-0062 held six criteria; VELDO-0062 keeps the login per
dispatch, the pre-launch caps, settlement and attribution. This new specification is draft; authoring
it supplies neither implementation proof nor operational activation.

## Out of scope

Carrying a session over to another account mid-run; automatic login; predictive pacing; sharing
accounts between factories; the re-dispatch and the owner question themselves (VELDO-0154 AC3); the
Mac read-back (VELDO-0147).

## What the reviewer judges

- Normal use: the owner registers his three Claude Code accounts and one Codex account and logs in to
  each once; dispatches spread across them, an account at its limit takes no new work until its reported
  reset, and a run stopped by a limit is decided re-run or ask from its record.
- Threat model: two accounts' work under one profile; work sent to an account at its limit before its
  reported reset; an account with no observation given more than one run; a rate-limited run left
  unclassified or an ordinary failure classified as a limit; a run that wrote through an MCP server
  decided for a re-run instead of asking. The owner's account and the installed engines are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); CLI report
  formats the installed CLIs do not produce; lost reports after a crash (Release 2); carrying a session
  over to another account mid-run.

## Notes

Choosing an account is part of preparing a dispatch, inside the VELDO-0036 reservation. The candidates
are the active accounts of an engine the role allows, with a profile on the chosen host, outside every
reported rate-limit window and under their concurrency. The Runner picks the lowest last reported
utilization on the tightest window, then the fewest active runs, then the least recently used. With
no candidate the unit waits, the UI shows "no account until" the earliest reset, and the factory loop
sets a timer for that time (VELDO-0154 AC1). The account records are VELDO-0062's registry.

**The fixture record form for AC3.** The decision reads a record, never a live run, so its checks need
neither the execution record (VELDO-0141) nor the catalog (VELDO-0144) built. A fixture record is an
ordered list of lines, each with a gapless `sequence`, a `received at` time, a `stream` (`engine`,
`stderr` or `wrapper`), a `redacted` field and a `payload`, the shape VELDO-0141 writes. An MCP tool call
is an `engine` line whose payload is the engine's own tool-call event naming the server and the tool (for
Claude Code a `tool_use` block whose name is `mcp__<server>__<tool>`, for Codex its MCP tool-call item
with server and tool). Beside the record the fixture gives the dispatch's configuration as a list of
servers, each with its catalog id and revision, and for each such revision the set of tools the owner
marks read-only, the `read-only tools` field of VELDO-0144's `mcp_server`; a revision that marks nothing
has an empty set. A server named in a call maps to the catalog id and revision the dispatch's
configuration lists, and a call whose server is not listed counts as not read-only. VELDO-0154 AC3 feeds
the decision each real run's record and catalog marks in the same form. Each server of the configuration may
also give the tools the dispatch selects for the run (VELDO-0127's selection, `all` tools or a list); a server
that gives no list gives all its tools.

**The structural rule for the re-run-or-ask decision (the lead's decision).** Three rounds of checks each found
a new way Claude Code keeps a nested MCP call out of the stream (the REPL tool's inner calls, an agent a
sub-agent starts, a skill a sub-agent forks, whose messages are dropped and whose end reports no count), so
rebuilding the calls from the stream cannot be made complete, and the configuration decides first. First of all, a
call that starts an agent outside the run asks whatever the configuration, since that agent may act through the
account's claude.ai connectors, which no configuration of the run governs: for Claude Code any RemoteTrigger call
(a deferred tool whose create, update and run start a cloud agent routine) and a durable CronCreate (its prompt
persists to the project's scheduled tasks and fires after the run; a CronCreate named where its input is not given
may be durable), read from the binary's bytes into `cli-formats.json` (`nested_work` `remote_agent`); the decision is
ask, naming each such line (reason `remote_agent`, basis `remote_agent`) beside the calls that contradict the
configuration. Next, before rule 1, a visible call that contradicts the configuration asks: an MCP call the record shows to a server the run's
configuration does not list, or to a tool the configuration does not give the run, shows the run did not have the
configuration the decision reads, so the decision is ask, naming each such line (reason `unconfigured_call`, basis
`unconfigured_call`), even when every configured server is read-only. Rule 1: when
the configuration gives the run no MCP server with a tool not marked read-only (no server, or each lists its
tools and its revision marks every one read-only), the run could not have written through MCP, and the
decision is re-run whatever the stream shows; a structurally malformed record is still refused by name. Rule 2:
otherwise, when the record shows any construct that can run nested work the stream may not show, the decision
is ask, naming each such line and its construct: for Claude Code an Agent tool call (or its old name Task, or
SendMessage to a teammate), a Skill tool call, the REPL tool or its inner call, the Workflow tool or a
workflow's task frames, a RemoteTrigger call, a CronCreate call, any task frame (`task_started`, `task_progress`, `task_notification`,
`task_updated`), a message a sub-agent or a forked skill produced (it names its task in `parent_tool_use_id`,
how the CLI forwards `agent_progress` and `skill_progress`) and a forked skill's result; for Codex a collab
agent call (exec's `collab_tool_call`, the core's `collab_agent_tool_call`) and a sub-agent's activity. The
construct list is read from the binaries' bytes into `cli-formats.json` (`nested_work`). Rule 3: otherwise the
call-by-call rules above decide, unchanged: a visible call to a tool not marked read-only asks, an engine line
that cannot be read asks, a form the decision does not recognize asks. The authoritative evidence later is a
factory-side log of the MCP calls themselves, which no engine stream can hide (filed for VELDO-0158).

Use canonical engine assets and synchronize installed copies. Inventory every asset the selected
journey installs. Compare executable registrations to each criterion's declared universe, observe the
real named interfaces, and retain the driven negative-control diff and named failed row. Fixtures
cannot certify real engine or host behavior. Required evidence labels describe future implementation
proof, not tests run by this writing revision.

## History

2026-09-25: split from VELDO-0062 on the third review of PLAN-0019 revision 4, because VELDO-0062 held six
criteria. AC1 is its former AC5, text and falsifier unchanged. Its former AC6 is two criteria here, so
each half has a falsifier of its own: AC2 the `account_limit` classification, whose falsifier is new,
and AC3 the re-run-or-ask decision with its former falsifier, and the Notes now give the fixture record
form in this specification, since VELDO-0141 and VELDO-0144 come later. The selection order moves here
from VELDO-0062's Notes. A draft: only the owner marks a specification ready.

2026-09-25, PLAN-0019 revision 4, fourth review: AC1 held four claims under one falsifier that broke only
the per-account isolation, so AC1 keeps registration, concurrency and isolation with that falsifier, and
the new AC4 carries moving off an exhausted account, adding an account without a restart and the one-run
bound while usage is unknown, with one mutant for each. It is AC4 rather than AC2 so the references to
AC2 and AC3 elsewhere stay right. Criterion meaning unchanged. A draft.

2026-09-25, lead: AC1's registration and concurrency claims each get their own falsifier beside
isolation.

2026-09-26, built (Release 1, Linux): the account pool (`control_account_pool`) chooses each dispatch's
account inside its VELDO-0036 worker reservation (`Reservations.reserve_pooled`), reading the account
records at every dispatch: candidates are the active accounts of the adapter's engine with a profile on
its host, outside every reported window and under their concurrency, one run at a time until an
account's first observation, in the Notes' order; with none the dispatch is refused
`no_account_until:<earliest reset>` naming each account's reason. The Runner takes the pool as its
account (two small `control_launch.py` hunks, the pool branch in `Runner.prepare` and the classification
in `Metering.settle`). A second registration of an account, by id or by its profile under another name,
is refused `duplicate_account:<id>`. Each engine meter keeps the limit its stream stated (Claude Code's
rejected `rate_limit_event` or its rate-limit result, whose usage-limit message gives the window and
reset; Codex's usage-limit message in an `error` event or a `turn.failed`), and the final report ends
such a run `account_limit` with its window and reset. `control_account_limit.decide` makes the re-run-or-
ask decision over a fixture record in the Notes' form. Proof in `proof/VELDO-0160/`: suite
`78_veldo_0160_account_pool` (13 rows), the red record at 52f817d5 (all 11 behavior rows red by
assertion, the two format rows green) and 35 finding 160 mutations, each red on its named row. The
footprint adds `proof/VELDO-0062/extract_formats.py` and `cli-formats.json`: the extractor now also
reads Claude Code's usage-limit message and Codex's MCP tool-call item out of the binaries, so every
fake line comes from the real formats. Status unchanged.

2026-09-26, review fixes: the re-run-or-ask decision now asks, naming the line, for an engine line it
cannot read (a payload that is not a JSON object naming its type, or a tool call the engine module cannot
read), reason `unreadable` or `redacted_unreadable` when the line's `redacted` field is set, since
VELDO-0141 AC4's redaction can break a line; a structurally malformed record is still refused by name. One
call id seen read-only and then naming a write counts the write. Claude Code's other rejected-status texts
(out of usage credits, the org, seat, service, admin and $0-group forms), read out of the binary into
`cli-formats.json`, classify `account_limit`. New rows `limit/claude-rejected-texts`,
`decision/unreadable-asks`, `decision/same-id-write`, `pool/usage-observes`, `pool/selection-order` and
`pool/until-earliest` pin these and the Notes' selection order and earliest reset; 13 more finding 160
mutations. Status unchanged.

2026-09-26, merged with main (VELDO-0060 and VELDO-0061) and the lead's fail-closed decision: the final
report now closes the meter, takes the exit's outcome, keeps the engine's artifact and makes a zero exit
without its terminal record a failure before it classifies the account limit, so a limit the stream
stated on such a run is still `account_limit`; the engine protocol names each meter's `limit()`. The
re-run-or-ask decision reads only the tool-call forms the binaries' own tables list (the extractor now
reads Claude Code's stream message union, its assistant and user content block unions, its streaming
events and its built-in tool list, and Codex exec's and the core's item types into `cli-formats.json`)
and counts any other form as an unknown call that asks, naming its line and form (reason
`unknown_call`): a Claude Code `mcp_tool_use` or other server-tool block, a `stream_event` carrying a
`tool_use`, a user `tool_result`, a `tool_progress` or a `tool_use_summary` for a call id no earlier line
showed, a Codex `dynamic_tool_call`, `collab_agent_tool_call` or `sub_agent_activity`, and any message,
subtype, block, item or event type the tables do not list. On a redacted line a Claude Code tool name
that is neither `mcp__...` nor a built-in tool is `redacted_unreadable`. New rows
`decision/unknown-forms`, `decision/redacted-name`, `decision/tool-free-forms` (the negative control)
and `format/tool-forms`, and 17 more finding 160 mutations. Status unchanged.

2026-09-26, the second check's fixes: an MCP write made through Claude Code's REPL tool is now decided
ask. Its inner calls reach the stream only as a `tool_progress` of the REPL call carrying a `repl_call`
the binary's emitters write and its schema omits; an `mcp__` inner name is that MCP call, a name neither
`mcp__` nor built in an unknown call, and a malformed `repl_call` unreadable. The other fields that name
a tool that ran count the same way: a `tool_progress`'s own tool, a `system/task_progress`'s
`last_tool_name` and its workflow agents' `lastToolName`, and an assistant message's MCP attribution and
batch tool names; the reader's table of every tool-named field, declared or emitted, is the binary's.
The binary's `BUILTIN_TOOL_NAMES` lists the Agent tool under its old name `Task`, so its current name
`Agent`, read from the tool's definition, is built in and an Agent call on a redacted line re-runs. The
frames the CLI writes outside the message union whose schema provably carries no tool call (`keep_alive`,
`control_cancel_request`, `active_goal`, `autocompact_state`, `post_turn_summary`, `task_summary`) are no
call; a control request or response and the transcript mirror cannot be shown tool-free and still ask.
Codex exec's own `collab_tool_call` is in exec's item table, an unknown call. The extractor reads each
of these out of the binaries into `cli-formats.json`. New rows `decision/repl-inner-call`,
`decision/task-progress-tool` and `decision/frame-tool-names`; `decision/redacted-name`,
`decision/unknown-forms`, `decision/tool-free-forms` and `format/tool-forms` extended; 13 more finding
160 mutations (78 in all, each rejected). Status unchanged.

2026-09-26, the lead's decision on a nested agent's hidden call (fail closed): in Claude Code 2.1.281 an
agent that a sub-agent starts (depth 2 or more) has its messages dropped unless the SDK's
`forwardSubagentText` option is set, so its `tool_use` blocks never reach the stream and its task's progress
names only the last tool of each message; a depth-2 reply of an MCP write then `Read` showed only `Read` and
was decided re-run. The decision now reads, for every task the stream reports (`system/task_started`,
`task_progress` and `task_notification`, keyed by the task's `tool_use_id`), the task's count of its own
calls (`usage.tool_uses`, which the binary raises by one for each `tool_use` block of the task's own
messages) against the distinct `tool_use` blocks the record shows under it (`parent_tool_use_id`); any
shortfall is that many calls the record cannot name, an unknown call of form `task_tool_uses` that asks,
naming the task and the shortfall (`unshown`). A count frame whose count cannot be read, and a count lower
than the task reported before, are unreadable and ask. Every field, frame and the forwarding gate were read
from the 2.1.281 bytes, and the extractor now records them in `cli-formats.json` (`task_counts`). New row
`decision/subagent-calls`; `decision/task-progress-tool`, `decision/tool-free-forms` and `format/tool-forms`
follow the reading; 8 more finding 160 mutations (86 in all). Forwarding sub-agent text
(`forwardSubagentText`), which would put a nested agent's own blocks in the stream, is filed for VELDO-0141's
live view, not set here. Status unchanged.

2026-09-26, the lead's structural rule for the re-run-or-ask decision: a third check found a skill forked by a
sub-agent whose `skill_progress` is dropped and whose fork reports no count of its calls, so its MCP write left
no trace in the stream and was decided re-run. Rebuilding the calls from the stream cannot be made complete, so
the configuration now decides first (the Notes): a configuration with no MCP server giving a tool not marked
read-only re-runs whatever the stream shows (basis `no_write_capable_server`); otherwise any construct that can
run hidden nested work asks, naming its line and construct (reason `nested_work`, basis `nested_work`); otherwise
the call-by-call rules decide as before (`decide_by_calls`, basis `calls`). The fixture configuration's servers
may list the tools they give the run. The extractor reads the construct list out of both binaries into
`cli-formats.json` (`nested_work`). New rows `decision/no-write-server-reruns`, `decision/nested-work-asks` and
`decision/nested-constructs`; the rows that judge how the call-by-call rules read a record holding such a
construct drive `decide_by_calls`, since `decide` now answers those records by the structural rule, and the
others check they were decided by the calls; `format/tool-forms` compares the construct tables. 15 more finding
160 mutations (rule 1 skipped, rule 2 skipped, each construct class dropped, and the configuration's tool list
misread). The authoritative evidence later is a factory-side log of the MCP calls (filed for VELDO-0158). Status
unchanged.

2026-09-26, the lead's decision on a call the configuration does not give the run: before rule 1, a visible MCP
call to a server the run's configuration does not list, or to a tool the configuration does not give the run,
decides ask, naming the line (reason `unconfigured_call`, basis `unconfigured_call`), since it contradicts the
configuration rule 1 trusts; before this a run configured with only read-only servers that visibly called an
unlisted server was re-run. The call-by-call rules keep `server_not_configured` for their own callers. New row
`decision/unconfigured-call-asks` (an unlisted server's call and an unselected read-only tool's call ask with only
read-only servers configured; the same record calling a listed read-only tool re-runs); `decision/ask` now expects
the unlisted server's call to be decided by this rule and checks the call-by-call rules still name it. 2 more
finding 160 mutations (the check skipped, the configuration's tool list ignored). Status unchanged.

2026-09-26, merged with main (VELDO-0155 and VELDO-0156) and the lead's decision on work outside the run: the
suite's fake Claude Code is qualified with stream JSON input and main's everything-off baseline and answers the
initialize handshake with a subscription login, and its fake Codex prints `login status` on stderr as 0.154.0
does, as main's suites do. A call that starts an agent outside the run now asks first, whatever the configuration
(basis and reason `remote_agent`): any Claude Code RemoteTrigger call (create, update and run start a cloud agent
routine that keeps the account's claude.ai connectors) and a durable CronCreate (a prompt that fires after the
run; `durable` true or the text "true", or a CronCreate named where its input is not given), each named beside the
calls that contradict the configuration; before this a routine created and run with no MCP server configured was
re-run. RemoteTrigger and CronCreate are also rule 2's constructs (`remote`, `cron`). The extractor reads both
tools, RemoteTrigger's actions and CronCreate's `durable` field with its default and semantic boolean out of the
2.1.281 bytes into `cli-formats.json`. New row `decision/remote-agent-asks` (the checker's routine and durable
cron ask under no server, only read-only tools and a write-capable server; a non-durable cron and the checker's
normal runs keep their decisions); `decision/nested-constructs` and `format/tool-forms` cover the two
constructs; 10 more finding 160 mutations. Status unchanged.
