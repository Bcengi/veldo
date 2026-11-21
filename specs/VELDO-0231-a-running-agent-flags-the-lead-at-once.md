---
schema: veldo.spec/v1
id: VELDO-0231
title: A running agent can flag something to the lead without stopping, and the flag reaches the lead's conversation at once
status: ready
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0127, VELDO-0154, VELDO-0160, VELDO-0173, VELDO-0174, VELDO-0230]
placement: [contracts, loop, fleet]
protected_paths: []
footprint:
  - ".veldo/control_launch.py"
  - "engine/.veldo/control_launch.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_conversation.py"
  - "engine/.veldo/control_conversation.py"
  - ".veldo/control_engine_claude.py"
  - "engine/.veldo/control_engine_claude.py"
  - ".veldo/control_engine_codex.py"
  - "engine/.veldo/control_engine_codex.py"
  - ".veldo/control_agent_config.py"
  - "engine/.veldo/control_agent_config.py"
  - ".veldo/control_agent_config_handoff.py"
  - "engine/.veldo/control_agent_config_handoff.py"
  - ".veldo/qualify.py"
  - "engine/.veldo/qualify.py"
  - "packs/*/.veldo/**"
  - "engine/runtime/**"
  - ".veldo/runtime/**"
  - "packs/*/runtime/**"
  - "proof/VELDO-0062/extract_formats.py"
  - "proof/VELDO-0062/cli-formats.json"
  - "proof/VELDO-0173/claude-tools.json"
  - "proof/VELDO-0127/**"
  - "scripts/suites/86_veldo_0127_agent_configuration.py"
  - "scripts/suites/127_veldo_0231_run_flags.py"
  - "scripts/suites/support/v231_fake_engines.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "scripts/mutation_case_inputs.json"
  - "specs/VELDO-0231-a-running-agent-flags-the-lead-at-once.md"
  - "specs/index.md"
  - "proof/VELDO-0231/**"
  - "scripts/suites/78_veldo_0160_account_pool.py"
behavior_bearing: true
observability:
  logs: >
    The launch receiver records each flag it reads with the dispatch id, engine, means (the tool name or
    the marked line) and the length of the text, never the text itself; the service records each flag it
    delivers or holds back with the conversation id, the run's flag count and its held back count, and each
    synchronous question it sees with the dispatch id, engine and what happened to it (answered by the
    binary, or the run stopped by name).
  metrics: >
    Count flags read, delivered, held back by the rate limit and kept undelivered for want of a
    conversation, per engine and means; record each delivered flag's latency from the receiver reading it
    to its commit.
  traces: >
    Join each flag record to its dispatch, its account, the engine stream line it was read from (the
    execution record's sequence) and the conversation it was delivered to.
  error_taxonomy: >
    Distinguish a flag held back by the rate limit (rate_limited:run_flag), a flag with no conversation to
    receive it (undelivered:no_conversation), a role that lists a wait-for-answer tool
    (invalid_input:agent_native_tools:wait_question), and a run stopped because its engine kept waiting
    on a synchronous question (configuration_stop:wait_question).
acceptance_criteria:
  - id: AC1
    text: >
      A flag a running agent raises reaches the lead's conversation within 2 seconds of the engine writing
      it, naming the run id (the dispatch id), the engine and the text, and the run goes on. The path has
      no wait or timer of its own: the launch receiver's poll loop reads the engine's stream as it comes
      (control_launch), reads a flag in it through the engine's module, and writes one flag event on its
      launch pipe at once; the service's factory loop has that pipe in its poll set (VELDO-0154) and writes
      the flag through one new conversation command (flag_conversation, the service principal, in
      control_conversation) as a flag record in the store, so the time is two pipe wakeups and one store
      commit. The 2 second bound is that path's measured time with margin for a loaded gate host, and the
      suite measures it: a fake engine stamps the time immediately before it writes each of 10 flags, keeps
      running and printing for 5 seconds after the last, then ends normally; the suite requires every
      flag's commit time minus its stamp under 2 seconds, each flag committed while the dispatch is still
      running, and the run's outcome the same as with no flag; the measured values are kept in the proof.
      The lead's conversation is the run's own conversation for a conversation turn, and for a project run
      the open conversation attached to the run's project (VELDO-0174's attach command), the most recently
      opened one when several are; with none, the flag is kept as a record with no conversation, counted,
      and named undelivered:no_conversation. Text is kept to its first 2000 characters.
    falsified_by: >
      Deliver flags only when the run's end is read (in saw_end) instead of when the flag event arrives,
      and the suite's row fails: no flag record exists while the dispatch is still running.
  - id: AC2
    text: >
      Each engine flags with what it has, each granted through runtime/capability-decisions.json with its
      reason, and the role's tool list names the tool, so VELDO-0127 AC4 (the tools at launch equal the
      role's, compared on the wire) still holds. Claude Code 2.1.317: SendUserMessage, granted and moved
      onto VELDO-0160's in-run list (the allowlist of proof/VELDO-0062/extract_formats.py, regenerated into
      cli-formats.json and claude-tools.json), because in a print-mode run its message goes only into the
      stream the receiver reads; its text is the flag and any attachments it names are not carried.
      PushNotification stays off under VELDO-0160 AC3, with that reason: it can notify a phone, which
      leaves the host, and the flag already reaches the lead. Codex 0.166.0: request_user_input_async,
      whose decision this specification turns from off to granted; the handoff sets
      tools.experimental_request_user_input on only for a role that lists it, and the qualified record's
      tool mapping for that grant names both tools the switch delivers on that binary
      (request_user_input_async and request_user_input), so the wire set still equals the role's. The
      qualify command's loopback probe records, for each Codex binary, the form in which an asynchronous
      call reaches the exec JSON stream; a binary on which it does not reach the stream gets the marked
      line as its means, recorded with that reason, never a grant the receiver cannot read. An engine with
      neither tool (and Antigravity, if Veldo ever runs it) uses the marked line: a line of the agent's own
      message text that begins with `VELDO-FLAG:`, read only from assistant message text (Claude Code text
      blocks, Codex agent_message items), never from a tool result, a file or the prompt.
    falsified_by: >
      Leave request_user_input out of the grant's tool mapping, and the suite's Codex launch row fails:
      the run is stopped by VELDO-0127 AC4's wire comparison on a tool the role does not name.
  - id: AC3
    text: >
      A synchronous question that waits for an answer can never hang an unattended run. No role may list a
      wait-for-answer tool (Claude Code's AskUserQuestion, Codex's request_user_input): saving one is
      refused by name (invalid_input:agent_native_tools:wait_question), so on Claude Code it is never in the
      launch set (VELDO-0173) and a call of it in the stream asks under rule A as today. On Codex, where
      the asynchronous grant also delivers request_user_input, the qualify loopback probe has the model call
      it under Veldo's launch (input closed after the prompt) and records the binary's own answer and how
      long it took; the grant holds only when that answer is immediate and gives no answers (Codex's own
      instructions then tell the model to continue on its judgment). The flag instructions the handoff adds
      to a role that holds a flag means say, as one fixed text, that nobody answers questions in this run and
      that the agent continues and flags instead. Every synchronous question the receiver reads is also
      delivered as a flag with its text, so the lead sees it. As the last guard, an engine that writes
      nothing within the receiver's question window (60 seconds, a receiver setting) after a synchronous
      question is stopped by name (configuration_stop:wait_question), never left waiting. The suite runs two
      fake Codex engines: one that writes the question call, gets the immediate empty answer and goes on to
      end normally, and one that writes the call and then blocks forever, which is stopped by name within
      the window (set to 2 seconds in the suite) with its question flag delivered.
    falsified_by: >
      Drop the receiver's question window, and the blocking fake engine's row fails: the run is still
      running when the suite's deadline passes.
  - id: AC4
    text: >
      Nothing outward, and a run that flags in a loop is rate limited with the count kept. A flag is written
      only as a record in this host's authority store, into the lead's own conversation (VELDO-0174); the
      receiver and the service make no network call and start no process for it other than the store's
      existing local journal signer (ssh-keygen -Y sign, which every store record uses), and no tool that leaves
      the host (PushNotification, SendUserFile, a remote trigger) is granted for it (VELDO-0160 AC3). The
      flag_conversation transition delivers a run's first flag at once and after it at most one flag per 60
      seconds and 20 per run; a flag beyond that is not delivered but counted on the run's flag summary
      (rate_limited:run_flag), and the next delivered flag names how many were held back since the one
      before. The counts are in the store, so they survive a service restart. The suite drives a fake
      engine that raises 500 flags in 5 seconds: exactly one is delivered, the summary counts 499 held back,
      and a flag 61 seconds later (on the suite's clock) is delivered naming 499; with socket creation and
      every process start except that local signer made to raise in the receiver and the service, a flag is
      still delivered.
    falsified_by: >
      Remove the per-run window from the flag_conversation transition, and the suite's flood row fails on
      500 delivered flags instead of one.
required_evidence: [unit, integration]
rollback: >
  Revert the change: the decisions return to off (SendUserMessage outward, request_user_input_async off
  under VELDO-0127 AC4), the receiver stops reading flags and no flag record is written. Stored flag records
  stay and are read by nothing.
---

## Intent

Owner direction, Telegram 38897-38901 (2026-11-04), approved "Ok". A running agent can flag something the
lead must know right now ("I am blocked", "a check needs a lock it cannot get", "found something the brief
did not expect") without stopping, and Veldo delivers it to the lead at once, instead of the lead learning
it when the run ends. The motivating case: a Codex run sat six hours on gate lock timeouts and nobody knew
until it finished.

## Context

VELDO-0230 evaluated everything Codex 0.166.0 and Claude Code 2.1.317 bring
(proof/VELDO-0230/new-capabilities-0.166-2.1.317.md, runtime/capability-decisions.json). There
request_user_input_async is off under VELDO-0127 AC4, because on 0.166.0 it reaches the model only with
tools.experimental_request_user_input on, which also delivers the synchronous request_user_input that no
role lists; this specification grants it, with the role naming both tools the switch delivers. The Claude
Code record classifies SendUserMessage and PushNotification as outward, not on VELDO-0160's in-run list
(proof/VELDO-0062/extract_formats.py CLAUDE_IN_RUN, read into proof/VELDO-0173/claude-tools.json).

The code path, read for this specification: the launch receiver (control_launch) reads the engine's stdout in its
poll loop chunk by chunk and feeds the execution record and the meter; it reports to the service on its
own stdout as JSON lines (emit), and the service's factory loop keeps every launch pipe in its poll set
(FactoryLoop.pipes and readable, Launch.pump in control_launch), today acting only on a run's end. The
conversation authority (control_conversation) writes conversations and turns through typed commands; it
has no entry for anything but the owner's messages, so the flag is a new record kind there, written by the
service principal. VELDO-0175 (Telegram and the UI) and VELDO-0178 (the API) carry a conversation's records
to where the owner reads them; once they land, a flag is one of those records.

## Out of scope

Answering a flag back into the running agent; flags from runs not launched by the factory's receiver;
presenting the flag in Telegram, the API or the screens beyond the conversation record (VELDO-0175,
VELDO-0178, VELDO-0179); running Antigravity.

## What the reviewer judges

- Normal use: a Codex build run that cannot get the gate lock flags it in its first minute; the lead's
  conversation holds the flag within seconds with the run id, engine and text, and the run keeps going.
- Threat model: a flag used to carry data off the host; a run that flags in a loop flooding the lead; a
  synchronous question hanging an unattended run; a marker planted in a file or tool output read as a
  flag; the async grant widening the tool set beyond the role's.
- Out of review scope (filed, not blocking): the exact wording of the fixed flag instructions.

## History

2026-11-04: written by the lead from Telegram 38897-38901 (owner approved "Ok"). Depends on VELDO-0230,
whose branch had not landed when this was written.

2026-11-04: amended by the lead after the build (proof/VELDO-0231/OPEN.md items 1 and 2). AC4's "start
no process" now names the one exception every store record already has: the authority store signs each
record with the local ssh-keygen journal signer, and Veldo is standard library only, so an in-process
signature is not available. The intent, nothing outward, is unchanged. Footprint adds
scripts/suites/78_veldo_0160_account_pool.py, whose allowlist row lists the in-run tools literally and
gains SendUserMessage.
