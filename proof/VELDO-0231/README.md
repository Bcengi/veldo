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

Test (rows AC1/at-once, AC1/run-goes-on, AC1/lead-conversation, AC1/observability). Since the bring-up line
(2026-11-21, lead decision Telegram 42829) "at once" is an ordering criterion, never a number of seconds: a fake
Claude Code writes 10 SendUserMessage flags and, after each, writes nothing more until it reads that flag's commit
on a FIFO (the suite acknowledges as the commit returns, or writes 'n' at once when the cycle that took the flag
ends without committing it). The row requires each flag committed in the same dispatch cycle that took its flag
event off the launch pipe, before the next is taken, while the dispatch is running, in the run's own conversation
naming the dispatch, engine and text; the outcome equals a run with no flag (`completed`). The service's rate
window runs on the suite's clock (61 s per reading) so all ten are deliverable. Measured latencies are kept as
recorded data only (round 0, suites.txt: 0.005 to 0.022 s); the earlier 2 second bound and the 5 second
after-last-flag window are gone.

Falsifier (`flag231-delivered-at-end`, readable no longer delivers, only saw_end): no flag is committed in the cycle
that took it, every commit after the dispatch `exited`; AC1/at-once red by event order. Mutation case killed alone
(bringup-2026-11-21/mutations.txt).

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
- The probe records the binary's own answer to request_user_input, whether it was immediate and whether it gave
  answers. Since the bring-up line's fix round 2 (review F6, 2026-11-21) "immediate" is an event, never a time:
  the answer is the call's output in the binary's very next request to the model, recorded as
  `answered_in: next_request` (the old `within_seconds: 5` and its 5 s rule, `IMMEDIATE_SECONDS`, are gone;
  `PROBE_SECONDS`, 120, only ends a hung probe run and is never a verdict). `flag_grant` holds only for an
  immediate answer with no answers; a role saved or launched with the grant where it does not hold is refused
  (`unsupported_configuration:codex_tool:...`).
- The handoff adds one fixed text (`FLAG_INSTRUCTIONS`) to a role that lists a flag tool: nobody answers questions in
  this run; continue, and flag instead.
- The receiver delivers every synchronous question as a flag; after one, an engine that writes nothing within the
  question window (`question_window_seconds`, receiver setting, 60 by default) is stopped by name
  (`configuration_stop:wait_question`, a `question` event on the launch pipe, logged by the service).

Test (rows AC3/save-refused, AC3/instructions, AC3/probe-answer, AC3/answered, AC3/blocking): two fake Codex runs
with the window at 2 s: one gets the immediate empty answer, written in one read with the question, and ends
`completed` (question delivered, logged `answered`); one blocks and is stopped by name, its question delivered.
Since the bring-up line the blocking run is stepped by events, not a deadline: once its own monotonic moment after
the question's commit plus the window has passed, the engine writes a line on its error stream, and once that line
is in the run's execution record (the receiver's pass after the window) it writes on.

Falsifier (`flag231-question-window-dropped`): the receiver records the question answered and the run ends
`completed` at once instead of `configuration_stop:wait_question`; AC3/blocking red (the earlier 15 s deadline is
gone). Mutation case killed alone (bringup-2026-11-21/mutations.txt).

## AC4: nothing outward, and a flagging loop is rate limited with the count kept

Built: `flag_conversation` delivers a run's first flag at once, after it at most one per 60 s and 20 per run; one
beyond is counted on the run's flag summary (`run_flag_summary`, `rate_limited:run_flag`), and the next delivered
flag names `held_back_since_last`. Summary and records are store records.

Test (rows AC4/flood, AC4/per-run-cap, AC4/nothing-outward): a fake Codex raises 500 flags (spread over 5 s; since the bring-up
line the service's clock stands still through the flood, so the verdict does not depend on how long the machine
takes to carry them): exactly one delivered, the summary counts 499 held back; over a new store connection (a restarted service) a flag 61 s later on
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

## Fix round 1: qualify reproduces (VELDO-0230 AC2)

Suite 126 was red: qualify/reproduces on both Codex records and the five VELDO-0127 resource files (the row
prints the first six). Run into a scratch copy of the tree and diffed against the checkout, two causes:

- The Codex record still carried the UNPROBED flag means: the shipped files were never regenerated after the
  probe landed. And the probe recorded `seconds`, the measured time from the loopback's call to the binary's
  answer (0.014 in one run), a per-run value. The probe now records what it established: the forms (none reach
  the stream on this binary, so the means is the marked line and the grant does not hold), the answer, whether it
  was immediate, whether it gave answers, and `within_seconds`, the bound it answered within (5), never the
  measured time. Suite 127's AC3/probe-answer row required `within_seconds` and no `seconds` (superseded on the
  bring-up line: the record names `answered_in: next_request`, see AC3 above).
- The resource fixtures were stale, not per-run: this ticket added request_user_input to the grant's mapping
  and changed the production modules whose digests they record. Regenerated, not normalized.

The one command (the branch's binaries: Codex musl x86_64 under node v22.22.0, Claude Code 2.1.281) was run
twice in the checkout: the first rewrote the seven files (commit c45f89df), the second left the tree byte-clean
(`git status` empty; the command still reports all 26 files it writes).

After: suite 126 28 of 28; suite 127 43 of 43; suite 86 52 of 54, red only live/claude and live/codex (stale
captures the lead retakes); suite 88 51 of 51. The four mutation cases run alone: each baseline and no-op green,
each mutant red on its target row.

## Bring-up line, 2026-11-21

The ticket came onto the bring-up line (line-bringup-1120) and its review there restated AC1 and AC3 under the
owner's rule that no gate depends on machine speed (Telegram 42829; specification History, 2026-11-21): both are
judged by events, never seconds, as described above. Evidence: bringup-2026-11-21/ (suites.txt, falsifiers.txt,
mutations.txt) and the live captures that suite 86's live rows bind, retaken on the line's modules
(bringup-2026-11-21/live-capture.md, owner approval Telegram 42874): Codex 4 of 5 runs, Claude Code 5 of 5 runs,
suite 86 28 of 28.
