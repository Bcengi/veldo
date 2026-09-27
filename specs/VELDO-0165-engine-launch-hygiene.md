---
schema: veldo.spec/v1
id: VELDO-0165
title: A worker engine inherits nothing from a parent Claude Code or Codex session, and a Claude Code run is offered its launch tool set with every other registered tool switched off
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
  - "engine/.veldo/control_engine_codex*.py"
  - ".veldo/control_engine_codex*.py"
  - "engine/runtime/claude-qualification*.json"
  - ".veldo/runtime/claude-qualification*.json"
  - "engine/runtime/codex-qualification*.json"
  - ".veldo/runtime/codex-qualification*.json"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0165_*.py"
  - "scripts/suites/78_veldo_0060_claude_adapter.py"
  - "scripts/suites/79_veldo_0061_codex_adapter.py"
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
      Claim: No variable a parent Claude Code or Codex session sets for its children reaches a worker
      engine. Set and completeness: The trusted wrapper removes, just before it execs either engine and
      beside VELDO-0155 AC4's names, every inherited variable whose name starts with CLAUDE, CLAUDECODE,
      AI_AGENT or CODEX, whatever the name, and only then sets the baseline's own variables and the
      account's login variable. The prefixes, not a list of names, decide the strip. A committed
      extractor reads every environment variable name each pinned binary (Claude Code 2.1.281, Codex
      0.154.0) holds in its bytes into proof/VELDO-0165, as evidence that the prefixes cover what the
      binaries read: the suite requires each extracted name that a parent session can set to match a
      prefix or be on VELDO-0155 AC4's list, so a new name a later version reads fails the suite until it
      is placed. Plant the eleven names the live run of 2026-09-26 inherited (CLAUDECODE,
      CLAUDE_CODE_CHILD_SESSION, CLAUDE_CODE_SESSION_ID, CLAUDE_CODE_SESSION_ATTENDED,
      CLAUDE_CODE_ENTRYPOINT, CLAUDE_CODE_EXECPATH, CLAUDE_CODE_MESSAGING_SOCKET,
      CLAUDE_CODE_MESSAGING_TOKEN, CLAUDE_PID, CLAUDE_EFFORT and AI_AGENT), a CODEX_ name, and one name
      per prefix that no extracted list holds, launch a Claude Code run and a Codex run, and read back each
      engine's environment: no planted name is present, and the baseline's own variables are. Falsifier:
      Strip only the extracted names in place of every name matching a prefix, and the row planting a
      CLAUDE_CODE_ name no extracted list holds must fail.
    falsified_by: >
      Strip only the extracted names in place of every name matching a prefix, and the row planting a
      CLAUDE_CODE_ name no extracted list holds must fail.
  - id: AC2
    text: >
      Claim: An inherited CLAUDE_AGENT_SDK_MCP_NO_PREFIX never renames a run's MCP tools. Set and
      completeness: The variable is removed by AC1's CLAUDE prefix and is also named in the baseline on
      its own, because VELDO-0160's call decision reads MCP tools by their `mcp__<server>__<tool>` names.
      Plant it with a configured fake MCP server, launch a Claude Code run, and read the init event's tool
      list: every tool of that server carries the prefix. Falsifier: Pass CLAUDE_AGENT_SDK_MCP_NO_PREFIX
      through to the engine, and the prefixed-tool row must fail.
    falsified_by: >
      Pass CLAUDE_AGENT_SDK_MCP_NO_PREFIX through to the engine, and the prefixed-tool row must fail.
  - id: AC3
    text: >
      Claim: A Claude Code run is offered exactly its launch tool set, and every other tool the binary
      registers is switched off at launch, not only caught. The launch tool set is a default, never a
      ceiling on the owner's grant. Set and completeness: When a role revision is bound, the launch tool
      set is that revision's native tools (VELDO-0127, the owner's grant, which may go beyond the in-run
      list); until then it is the in-run list of the pinned version. The launch passes the `tools` option
      naming exactly the launch tool set, and the `disallowedTools` option naming every tool in the
      binary's full tool registry that falls outside it; the registry is every tool the binary registers,
      read from its bytes by the committed extractor, not the 22-name BUILTIN_TOOL_NAMES table of
      proof/VELDO-0062/cli-formats.json. Before anything is switched off, a classification step records in
      proof/VELDO-0165 every tool of the pinned 2.1.281 registry as in-run or outward, each with the reason
      read from its definition (the live init of 2026-09-26 offered 25, among them CronList, CronDelete,
      EnterWorktree, ExitWorktree, ListAgents, ScheduleWakeup and ReportFindings), and the in-run list is
      the classification's in-run tools, which the suite requires to equal VELDO-0160's
      claude_code.tool_forms.in_run list.
      Launch a run with no revision bound and read the init event's tool list: it equals the in-run list,
      and RemoteTrigger, SendMessage, PushNotification, the Artifact and other claude.ai-writing tools and
      self_hosted_runner are absent. Launch a run bound to a revision that grants PushNotification: the
      init event lists it, and `disallowedTools` does not name it. Falsifier: Launch with neither the
      `tools` nor the `disallowedTools` option, and the no-revision init-tools row must fail on
      RemoteTrigger.
    falsified_by: >
      Launch with neither the `tools` nor the `disallowedTools` option, and the no-revision init-tools
      row must fail on RemoteTrigger.
  - id: AC4
    text: >
      Claim: The session strip, the tool registry and its classification are part of the qualified
      baseline, so a version without them launches nothing. Set and completeness: The Claude Code
      qualification record's baseline for a version carries the strip prefixes and the names extracted
      (AC1 and AC2), the tool registry and the classification of every registry tool (AC3), all read from
      that version's bytes; the receiver derives the `tools` and `disallowedTools` options from the record
      and the bound revision, never from a list in the code. A record whose baseline lacks any of them, or
      whose classification leaves a registry tool unclassified, refuses every launch of that version by
      name before anything is spawned (missing_evidence:engine_baseline:<version>); the Codex record
      carries its strip prefixes the same way. Falsifier: Accept a record whose classification leaves one
      registry tool unclassified, and the baseline-required row must fail.
    falsified_by: >
      Accept a record whose classification leaves one registry tool unclassified, and the
      baseline-required row must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new Claude Code and Codex launches while preserving accepted records and unresolved work; no run
  launches without these guards. No automatic rollback is authorized.
---

## Intent

A worker run behaves the same whether the factory was started from a terminal or from inside a Claude
Code or Codex session, and a Claude Code worker is offered the tools its role was granted, or by default
only the tools that act inside its run, with every other tool the binary registers switched off.

## Context

W125 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1. The owner
approved two live engine runs on 2026-09-26 (Telegram 29207 and 29211). The receiver ran inside a Claude
Code session, and eleven of that session's variables would have reached the engine, among them the
messaging socket and token through which a child reaches its parent session. The reviews of VELDO-0160
found outward tools one at a time (RemoteTrigger, durable CronCreate, SendMessage to another session,
remote Agent isolation, the claude.ai-writing tools, PushNotification, self_hosted_runner), and the lead
decided on a fail-closed allowlist in VELDO-0160's call decision, with the same list passed to the engine
at launch so those tools are off and not only caught. The live init offered 25 tools, more than the
22-name built-in table names, so the tools switched off are read from the binary's full registry, and each
registry tool is classified before any is switched off. The launch list is a default: a role revision the
owner grants more tools (VELDO-0127) is launched with its own native tools, which is why VELDO-0127 depends
on this specification. The strip goes by prefix, so a session variable a later version adds is removed
before anyone lists it. CLAUDE_AGENT_SDK_MCP_NO_PREFIX drops the MCP prefix
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
  names; a registered tool that acts outside the run being offered to a run whose role did not grant it; a
  tool the owner granted being switched off by the launch; a registry tool left unclassified; a version
  launched without the strip, the registry or the classification. The owner's account and the installed
  engine are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); variables whose
  names do not match the prefixes and that a later version adds (a requalification reads them); other
  versions and host kinds (Release 4).

## Notes

The strip belongs to the trusted wrapper beside VELDO-0155 AC4's names, so the receiver's own
`systemd-run` and `systemctl` keep their environment. The extractor records every environment name and
every registered tool with the byte offset it was read at, so a reviewer can check both against the bytes.
The classification is data in the proof directory, one row per registry tool with its reason, and the
lead reviews it before the switch-off is built. Only the owner widens a role's tools, through
VELDO-0127; the launch then passes that revision's native tools in place of the in-run list.

## History

2026-09-27: new draft from the live engine runs of 2026-09-26 and the VELDO-0160 reviews rv160f and
rv160g. It holds four criteria, so the brief's two halves stay one specification. A draft: only the owner
marks a specification ready.

2026-09-27: amended on the independent check of this batch and the lead's decisions. AC1 strips by
prefix (CLAUDE, CLAUDECODE, AI_AGENT, and CODEX for the equivalent Codex strip) and then sets the
baseline's own variables; the extractor stays as evidence the prefixes cover what the binaries read. AC3's
launch list is a default, not a ceiling: `tools` carries the bound role revision's native tools
(VELDO-0127) when one is bound and the in-run list until then, and `disallowedTools` is every tool of the
binary's full registry outside that set, after a classification step records every registry tool as
in-run or outward; its falsifier drops both options, since dropping `tools` alone leaves
`disallowedTools` switching RemoteTrigger off. AC4 carries the registry and the classification in the
baseline. VELDO-0127 now depends on this specification. Still a draft.
