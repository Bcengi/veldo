---
schema: veldo.spec/v1
id: VELDO-0165
title: A worker engine inherits nothing from a parent Claude Code session and is offered only the tools that act inside its run
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W125
plan_revision: 4
depends_on: [VELDO-0155, VELDO-0156, VELDO-0160]
placement: [fleet, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "engine/.veldo/control_engine_claude*.py"
  - ".veldo/control_engine_claude*.py"
  - "engine/runtime/claude-qualification*.json"
  - ".veldo/runtime/claude-qualification*.json"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0165_*.py"
  - "scripts/suites/78_veldo_0060_claude_adapter.py"
  - "scripts/suites/80_veldo_0155_claude_baseline.py"
  - "scripts/suites/81_veldo_0156_codex_baseline.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0165-engine-launch-hygiene.md"
  - "specs/index.md"
  - "proof/VELDO-0165/*"
behavior_bearing: true
observability:
  logs: >
    Record each launch's removed session variable names and the tool options it passed, as names only;
    never a variable's value.
  metrics: >
    Count launches, session variables removed by name, and launches refused for a baseline without the
    strip or the tool list.
  traces: >
    Join each launch to its dispatch, the pinned executable digest and the qualification record version
    whose strip and tool list it applied.
  error_taxonomy: >
    Distinguish a version whose qualified baseline lacks the session strip or the tool list
    (missing_evidence:engine_baseline) from a stripped variable found in the engine environment and a
    tool outside the list found in the init event; none lets the run take a first turn.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: No variable a parent Claude Code session sets for its children reaches a worker engine. Set
      and completeness: The set is every environment variable name the pinned 2.1.281 binary reads whose
      name starts with CLAUDE, CLAUDECODE or AI_AGENT, less the names the baseline itself sets and the
      account's login variable, extracted from the binary's own bytes by a committed extractor into
      proof/VELDO-0165 and carried in the version's qualified baseline; it includes CLAUDECODE,
      CLAUDE_CODE_CHILD_SESSION, CLAUDE_CODE_SESSION_ID, CLAUDE_CODE_SESSION_ATTENDED,
      CLAUDE_CODE_ENTRYPOINT, CLAUDE_CODE_EXECPATH, CLAUDE_CODE_MESSAGING_SOCKET,
      CLAUDE_CODE_MESSAGING_TOKEN, CLAUDE_PID, CLAUDE_EFFORT and AI_AGENT, the eleven the live run of
      2026-09-26 inherited. The trusted wrapper removes the set just before it execs either engine, as it
      removes VELDO-0155 AC4's names. Plant every name of the set in the receiver's environment, launch a
      Claude Code run and a Codex run, and read back each engine's environment: none is present.
      Falsifier: Leave CLAUDE_CODE_MESSAGING_TOKEN out of the strip, and the engine-environment read-back
      row must fail.
    falsified_by: >
      Leave CLAUDE_CODE_MESSAGING_TOKEN out of the strip, and the engine-environment read-back row must
      fail.
  - id: AC2
    text: >
      Claim: An inherited CLAUDE_AGENT_SDK_MCP_NO_PREFIX never renames a run's MCP tools. Set and
      completeness: The variable is in AC1's set by its prefix and is also named in the baseline on its
      own, because VELDO-0160's call decision reads MCP tools by their `mcp__<server>__<tool>` names. Plant
      it with a configured fake MCP server, launch a Claude Code run, and read the init event's tool list:
      every tool of that server carries the prefix. Falsifier: Pass CLAUDE_AGENT_SDK_MCP_NO_PREFIX through
      to the engine, and the prefixed-tool row must fail.
    falsified_by: >
      Pass CLAUDE_AGENT_SDK_MCP_NO_PREFIX through to the engine, and the prefixed-tool row must fail.
  - id: AC3
    text: >
      Claim: A Claude Code run is offered only the built-in tools that act inside the run, so an outward
      tool is off, not only caught. Set and completeness: The launch passes the `tools` option naming
      exactly the in-run tool list of the pinned version (proof/VELDO-0062/cli-formats.json,
      claude_code.tool_forms.in_run.tools, VELDO-0160), and the `disallowedTools` option naming every
      other built-in tool the binary's tool table lists, as a second layer. Launch a run and read the init
      event's tool list: every built-in tool in it is on the in-run list, and RemoteTrigger, SendMessage,
      PushNotification, the Artifact and other claude.ai-writing tools and self_hosted_runner are absent.
      A tool a role's configuration grants (VELDO-0127) is that configuration's decision, not this
      baseline's. Falsifier: Launch without the `tools` option, and the init-tools row must fail on
      RemoteTrigger.
    falsified_by: >
      Launch without the `tools` option, and the init-tools row must fail on RemoteTrigger.
  - id: AC4
    text: >
      Claim: The session strip and the tool list are part of the qualified baseline, so a version without
      them launches nothing. Set and completeness: The Claude Code qualification record's baseline for a
      version carries the session strip (AC1 and AC2) and the tool list (AC3), both read from that
      version's bytes; the receiver applies them from the record, never from a list in the code. A record
      whose baseline lacks either refuses every launch of that version by name before anything is spawned
      (missing_evidence:engine_baseline:<version>). Falsifier: Accept a record whose baseline has no tool
      list, and the baseline-required row must fail.
    falsified_by: >
      Accept a record whose baseline has no tool list, and the baseline-required row must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new Claude Code and Codex launches while preserving accepted records and unresolved work; no run
  launches without these guards. No automatic rollback is authorized.
---

## Intent

A worker run behaves the same whether the factory was started from a terminal or from inside a Claude
Code session, and a Claude Code worker cannot reach a tool that acts outside its run.

## Context

W125 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1. The owner
approved two live engine runs on 2026-09-26 (Telegram 29207 and 29211). The receiver ran inside a Claude
Code session, and eleven of that session's variables would have reached the engine, among them the
messaging socket and token through which a child reaches its parent session. The reviews of VELDO-0160
found outward tools one at a time (RemoteTrigger, durable CronCreate, SendMessage to another session,
remote Agent isolation, the claude.ai-writing tools, PushNotification, self_hosted_runner), and the lead
decided on a fail-closed allowlist in VELDO-0160's call decision, with the same list passed to the engine
at launch so those tools are off and not only caught. CLAUDE_AGENT_SDK_MCP_NO_PREFIX drops the MCP prefix
that decision reads. This new specification is draft; authoring it supplies neither implementation proof
nor operational activation.

## Out of scope

VELDO-0160's call decision, which stays as the second check; input-dependent outward forms of an in-run
tool (remote Agent isolation, durable CronCreate), which that decision governs; a Bash tool starting
another CLI (filed for VELDO-0127 and VELDO-0158); the Codex tool surface; the Mac leg (VELDO-0147).

## What the reviewer judges

- Normal use: the Runner launches Claude Code or Codex for a dispatched unit on Linux, with the authority
  service started from a terminal or from a Claude Code session.
- Threat model: a parent session's variable reaching the engine; an inherited variable changing MCP tool
  names; a built-in tool that acts outside the run being offered to it; a version launched without the
  strip or the tool list. The owner's account and the installed engine are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); variables whose
  names do not match the prefixes and that a later version adds (a requalification reads them); other
  versions and host kinds (Release 4).

## Notes

The strip belongs to the trusted wrapper beside VELDO-0155 AC4's names, so the receiver's own
`systemd-run` and `systemctl` keep their environment. The extractor records every matching name with the
byte offset it was read at, so a reviewer can check the set against the bytes. Only the owner may widen
the baseline's tool list for a role, through VELDO-0127.

## History

2026-09-27: new draft from the live engine runs of 2026-09-26 and the VELDO-0160 reviews rv160f and
rv160g. It holds four criteria, so the brief's two halves stay one specification. A draft: only the owner
marks a specification ready.
