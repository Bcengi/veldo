# VELDO-0231 proof: a running agent flags the lead without stopping

Producer: the Claude implementation agent (not an independent reviewer). Branch agent/claude/veldo-0231, on top of
VELDO-0230 (8da5d061). Owner approval: Telegram 38897-38901 (2026-11-04). Fake engines only: no real Claude Code or
Codex model run, no login. Suites 86 and 87, as they always do, forward the fake Codex's model request to the
qualified binary on loopback; nothing else ran a real binary, and the qualify command was not run (see OPEN.md).

The test is suite 127 (scripts/suites/127_veldo_0231_run_flags.py, support scripts/suites/support/v231_fake_engines.py):
a real signed authority store, the production conversation authority, VELDO-0174's conversation Line with real
receiver subprocesses over fake pinned engines, and the service loop's poll over the launch pipes. 17 rows.

Evidence files:
- `red-at-8da5d061.txt`: suite 127 against the modules before this change: 0 of 17 rows pass.
- `suites.txt`: suites 127 (17 of 17), 86, 123, 87, 125, 82_0173, 88, 90 and 78_0160 at the final code.
- `falsify.py`, `falsifiers.txt`: each spec falsifier applied to the checkout's module, suite 127 run, the module
  restored byte for byte.
- `mutation-flag231-*.txt`: each registered mutation case run alone through scripts/check_teeth_mutations.py
  (baseline and no-op green, the mutant killed by its row).

## AC1: the flag reaches the lead's conversation at once, and the run goes on

Built:
- control_launch `Flags`: the receiver's poll loop (`_reap`, `take`) feeds each chunk it reads from the engine to the
  reader, which reads whole lines through the engine module's `flags` and writes one `flag` event on the launch pipe
  at once (dispatch, engine, account, means, text cut to 2000 characters, its length, the execution record sequence
  of the line, when it was read). No wait or timer of its own. `Launch._take` keeps flag and question events in
  `launch.flags`.
- control_service `FactoryLoop.readable` delivers what the pump read (`deliver`) before anything else; `saw_end`
  delivers whatever is left. `deliver` writes each flag through `Conversations.flag` with the loop's clock and logs it
  (kind `flag`) without its text: dispatch, engine, means, length, conversation, the run's flag count and held back
  count, sequence, account; a question's outcome is logged too.
- control_conversation `flag_conversation` (the service principal): a flag record (`conversation_flag`) into the
  lead's conversation, `lead_conversation`: the run's own for a conversation turn, else the open conversation
  attached to the run's project, the most recently opened; none: kept with no conversation, counted,
  `undelivered:no_conversation`. Text kept to 2000 characters. `flags`, `flag_summary`, `flag_counts` (read,
  delivered, held back, undelivered per engine and means, each delivered flag's latency).

Test (rows AC1/at-once, AC1/run-goes-on, AC1/lead-conversation, AC1/observability): a fake Claude Code stamps the
time immediately before each of 10 SendUserMessage flags, prints for 5 seconds after the last, ends normally. Every
flag's commit time (wall clock, taken as the commit returns) minus its stamp is under 2 seconds, each committed while
the dispatch is running, each in the run's own conversation naming the dispatch, engine and text; the outcome equals
a run with no flag (`completed`). The service's rate window runs on the suite's clock (61 s per reading) so all ten
are deliverable. Measured latencies (suites.txt): 0.005 to 0.022 s.

Falsifier (`flag231-delivered-at-end`, readable no longer delivers, only saw_end): latencies 5.06 to 7.73 s, every
commit after the dispatch `exited`; AC1/at-once red. Mutation case killed alone.

## AC2: each engine flags with what it has, and the wire set still equals the role's

Built:
- Claude Code: SendUserMessage on VELDO-0160's in-run list (proof/VELDO-0062/extract_formats.py CLAUDE_IN_RUN,
  regenerated cli-formats.json and proof/VELDO-0173/claude-tools.json by the static extractors; the qualification
  record's classification and `stream_forms.in_run_tools` written to match, both runtimes). The anchor also matches
  2.1.317 (checked by a static extract). runtime/capability-decisions.json: SendUserMessage granted with its reason,
  PushNotification off under VELDO-0160 AC3 (it can notify a phone; the flag already reaches the lead).
  control_engine_claude `flags`: SendUserMessage's `message` (attachments not carried), AskUserQuestion's questions
  (synchronous), marked lines of assistant text blocks.
- Codex: request_user_input_async granted (the decision turned from off). control_engine_codex
  NATIVE_TOOL_MAPPING names both tools the switch delivers (`request_user_input_async`, `request_user_input`), in the
  module and the shipped record. The handoff sets tools.experimental_request_user_input on only for a role that lists
  the grant. qualify.py `flag_probe` (loopback, input closed after the prompt; proof/VELDO-0127/loopback.py can
  answer with one model call): the model calls each tool with a token; the record's `flag_means` holds the form in
  which each call reaches the exec JSON stream (event type, item type, path to the tool name, path to the text), or
  the marked line with the reason when the asynchronous call does not reach it. `flag_grant` holds only with a form.
  control_engine_codex `flags` reads calls only in the recorded form, marked lines only from agent_message items.
- Marked line: a line beginning `VELDO-FLAG:` of the agent's own message text, never a tool result, a file or the
  prompt.

Test (rows AC2/codex-launch, AC2/decisions, AC2/switch, AC2/probe, AC2/marked-line): a Codex role listing the grant
launches through the receiver's VELDO-0127 AC4 wire comparison (the fake declares both tools when the switch is on)
and completes; its flags arrive in the recorded form. The probe over three fake Codex binaries records the stream form
(grant holds), the marked line with its reason (call not in the stream), and a non-answering binary.

Falsifier (`flag231-question-unmapped`, request_user_input left out of the mapping): the Codex run is stopped
`configuration_stop:codex_unexpected_tool`; AC2/codex-launch red. Mutation case killed alone.

## AC3: a synchronous question can never hang an unattended run

Built:
- control_agent_config: AskUserQuestion (Claude Code) and request_user_input (Codex) refused at save by name,
  `invalid_input:agent_native_tools:wait_question`.
- The probe records the binary's own answer to request_user_input, how long it took, whether immediate (at most
  5 s) and whether it gave answers; `flag_grant` holds only for an immediate answer with no answers; a role saved or
  launched with the grant where it does not hold is refused (`unsupported_configuration:codex_tool:...`).
- The handoff adds one fixed text (`FLAG_INSTRUCTIONS`) to a role that lists a flag tool: nobody answers questions in
  this run; continue, and flag instead.
- The receiver delivers every synchronous question as a flag; after one, an engine that writes nothing within the
  question window (`question_window_seconds`, receiver setting, 60 by default) is stopped by name
  (`configuration_stop:wait_question`, a `question` event on the launch pipe, logged by the service).

Test (rows AC3/save-refused, AC3/instructions, AC3/probe-answer, AC3/answered, AC3/blocking): two fake Codex runs
with the window at 2 s: one gets the immediate empty answer and ends `completed` (question delivered, logged
`answered`); one blocks forever and is stopped by name within the window, its question delivered.

Falsifier (`flag231-question-window-dropped`): the blocking run is still running when the suite's 15 s deadline
passes; AC3/blocking red. Mutation case killed alone.

## AC4: nothing outward, and a flagging loop is rate limited with the count kept

Built: `flag_conversation` delivers a run's first flag at once, after it at most one per 60 s and 20 per run; one
beyond is counted on the run's flag summary (`run_flag_summary`, `rate_limited:run_flag`), and the next delivered
flag names `held_back_since_last`. Summary and records are store records.

Test (rows AC4/flood, AC4/per-run-cap, AC4/nothing-outward): a fake Codex raises 500 flags in 5 s: exactly one
delivered, the summary counts 499 held back; over a new store connection (a restarted service) a flag 61 s later on
the suite's clock is delivered naming 499. 25 flags 61 s apart: 20 delivered. With socket creation and every process
start raising, the receiver's reader reads a flag and the service delivers it; the one process let through is the
store's own journal signature for every commit (`ssh-keygen -Y sign`), named in the row (see OPEN.md). No tool that
leaves the host is granted (PushNotification, SendUserFile, RemoteTrigger outward; none a Codex capability).

Falsifier (`flag231-run-window-removed`): 500 of 500 delivered; AC4/flood red (and AC4/per-run-cap). Mutation case
killed alone.

## Other suites

Suite 86: 26 of 28; live/claude and live/codex are stale live captures (they bind module digests this change edits,
and the Codex mapping changed); the lead retakes them. Its catalog/grants row now expects a flag grant the qualified
binary does not hold refused at save; the role fixture (proof/VELDO-0127/factory.py) carries the shipped flag means.
Suite 87: its delivery fixture expects the same. Suite 123: 38 of 38. Suite 78_0160: one row red, see OPEN.md.

## Commits

237851d1 production, b62a4cf4 loopback and suite 86, c204f6de suite 127, then the mutation cases, suite fixes, the
delivery fixture and this proof.
