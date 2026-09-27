---
schema: veldo.spec/v1
id: VELDO-0165
title: A worker engine inherits nothing from a parent Claude Code or Codex session
status: ready
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
  - "scripts/suites/75_veldo_0062_accounts.py"
  - "scripts/suites/78_veldo_0160_account_pool.py"
  - "scripts/drive.py"
  - "scripts/suites/78_veldo_0060_claude_adapter.py"
  - "scripts/suites/79_veldo_0061_codex_adapter.py"
  - "scripts/suites/80_veldo_0155_claude_baseline.py"
  - "scripts/suites/81_veldo_0156_codex_baseline.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0165-engine-launch-hygiene.md"
  - "specs/VELDO-0062-provider-credentials-and-usage.md"
  - "specs/index.md"
  - "proof/VELDO-0165/*"
behavior_bearing: true
observability:
  logs: >
    Record each launch's removed session variable names as names only;
    never a variable's value.
  metrics: >
    Count launches, session variables removed by name, and launches refused for a baseline without the
    strip.
  traces: >
    Join each launch to its dispatch, the pinned executable digest and the qualification record version
    whose strip it applied.
  error_taxonomy: >
    Distinguish a version whose qualified baseline lacks the session strip
    (missing_evidence:engine_baseline) from a stripped variable found in the engine environment;
    neither lets the run take a first turn.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: No variable a parent Claude Code or Codex session sets for its children reaches a worker
      engine. Set and completeness: The trusted wrapper removes, just before it execs either engine and
      beside VELDO-0155 AC4's names, every inherited variable whose name starts with CLAUDE, CLAUDECODE,
      AI_AGENT or CODEX, whatever the name, and only then sets the baseline's own variables and the
      account's login variable. Each engine's qualification record carries its strip prefixes and
      extracted names; a version missing that evidence refuses launch as
      missing_evidence:engine_baseline:<version> before spawn. The prefixes, not a list of names, decide
      the strip. A committed extractor reads every environment variable name each pinned binary (Claude Code 2.1.281, Codex
      0.154.0) holds in its bytes into proof/VELDO-0165, as evidence that the prefixes cover what the
      binaries read: the suite requires each extracted name that a parent session can set to match a
      prefix or be on VELDO-0155 AC4's list, so a new name a later version reads fails the suite until it
      is placed. Plant the eleven names the live run of 2026-09-26 inherited (CLAUDECODE,
      CLAUDE_CODE_CHILD_SESSION, CLAUDE_CODE_SESSION_ID, CLAUDE_CODE_SESSION_ATTENDED,
      CLAUDE_CODE_ENTRYPOINT, CLAUDE_CODE_EXECPATH, CLAUDE_CODE_MESSAGING_SOCKET,
      CLAUDE_CODE_MESSAGING_TOKEN, CLAUDE_PID, CLAUDE_EFFORT and AI_AGENT), a CODEX_ name, and one name
      per prefix that no extracted list holds, launch a Claude Code run and a Codex run, and read back each
      engine's environment: no planted name is present, and the baseline's own variables are.
      Launch each engine under a record lacking the strip prefixes: each refuses missing_evidence:engine_baseline:<version>, nothing spawned.
      Falsifiers:
      Strip only the extracted names in place of every name matching a prefix, and the row planting a
      CLAUDE_CODE_ name no extracted list holds must fail.
      Drop the Codex strip evidence check; the Codex refusal row must fail.
    falsified_by: >
      Strip only the extracted names in place of every name matching a prefix, and the row planting a
      CLAUDE_CODE_ name no extracted list holds must fail.
      Drop the Codex strip evidence check; the Codex refusal row must fail.
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
required_evidence: [unit, integration]
rollback: >
  Disable new Claude Code and Codex launches while preserving accepted records and unresolved work; no run
  launches without these guards. No automatic rollback is authorized.
---

## Intent

A worker run behaves the same whether the factory was started from a terminal or from inside a Claude
Code or Codex session, without inheriting the parent's session variables or changing MCP tool names.

## Context

W125 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1. The owner
approved two live engine runs on 2026-09-26 (Telegram 29207 and 29211). The receiver ran inside a Claude
Code session, and eleven of that session's variables would have reached the engine, among them the
messaging socket and token through which a child reaches its parent session. The strip goes by prefix,
so a session variable a later version adds is removed before anyone lists it.
CLAUDE_AGENT_SDK_MCP_NO_PREFIX drops the MCP prefix VELDO-0160's call decision reads. The tool registry
and its qualified classification are VELDO-0173, split from this specification's former AC3 and AC4.
This new specification is draft; authoring it supplies neither implementation proof nor activation.

## Out of scope

The full tool registry, its classification and launch tool options (VELDO-0173); role grants
(VELDO-0127); VELDO-0160's call decision; a Bash tool starting another CLI (filed for VELDO-0127 and
VELDO-0158); the Mac leg (VELDO-0147).

## What the reviewer judges

- Normal use: the Runner launches Claude Code or Codex for a dispatched unit on Linux, with the authority
  service started from a terminal or from an engine session.
- Threat model: a parent session's variable reaching the engine; an inherited variable changing MCP tool
  names; a version launched without the qualified strip. The owner's account and the installed engine
  are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); variables whose
  names do not match the prefixes and that a later version adds (a requalification reads them); other
  versions and host kinds (Release 4).

## Notes

The strip belongs to the trusted wrapper beside VELDO-0155 AC4's names, so the receiver's own
`systemd-run` and `systemctl` keep their environment. The extractor records every environment name
with its byte offset, so a reviewer can check it against the pinned binary.

## History

2026-09-27: new draft from the live engine runs of 2026-09-26 and the VELDO-0160 reviews rv160f and
rv160g; the original draft combined environment and tool registry guards.

2026-09-27: the independent check made AC1 strip by prefix (CLAUDE, CLAUDECODE, AI_AGENT and CODEX),
then set the baseline's own variables, with extraction as evidence that the prefixes cover the binary.

2026-09-27: on the lead's follow-up decision, this draft keeps AC1 and AC2, the environment strip;
the former AC3 and AC4 move to VELDO-0173, which depends on this specification and VELDO-0160.
The bound role's PushNotification grant row moves to VELDO-0127 AC4, whose dependency now names
VELDO-0173. Only the owner marks a specification ready.

2026-09-27: marked ready by the owner (Telegram 29229, "all ready").

2026-09-27: implemented the wrapper's prefix strip, then restored only the qualified baseline and
registered account's own profile and optional subscription token. Both qualification records carry
the prefixes and extracted session names; missing evidence refuses before spawn. The baseline names
the MCP override explicitly. The committed byte extractor records identifier candidates with offsets
and the SDK naming expression from both pinned binaries, without executing either. Suite
82_veldo_0165_launch_hygiene has eight behavior rows and two fixture controls; all eight behavior rows
are red by assertion at 65125030, and all nine finding 165 mutations are rejected. The new suite and
VELDO-0160's account pool suite pass normally and in the empty gate environment. The footprint adds
scripts/drive.py for the requested red entry point, and the VELDO-0062 and VELDO-0160 suites for their
fake qualification writers. The whole selftest and contained-launch suites are pending because their
real user service manager access conflicts with this task's safety restriction. No gate or real engine
run was performed. Status unchanged; evidence and remaining checks are in proof/VELDO-0165/README.md.

2026-09-27, review fixes: empty extracted evidence is present; missing or null evidence refuses.
The adapter's checked configuration is carried through the trusted wrapper after the inherited
strip. Approval of VELDO-0165 (Telegram 29229) supersedes VELDO-0062's inherited non-login setting
exception: CLAUDE_CODE_MAX_OUTPUT_TOKENS reaches the engine only when configured. Existing login
checks remain. The byte extractor locates Claude Code's child-environment array and unconditional
startup assignments by content; their unprefixed names join AC4's wrapper list. New rows cover
configured values, unprefixed parent names, empty evidence, extraction completeness, matching
prefixes, accurate removed-name reports and the refused-baseline metric.

2026-09-27, review-fix validation complete: the whole selftest ran once with no checkout edits while
it ran, 6,877 rows passed and zero failed. VELDO-0061 passes 20/20 with unchanged assertions;
VELDO-0062 passes 22/22 and VELDO-0165 passes 17/17. Finding 165 rejects all 15 mutations, finding 62
all 50, finding 61 all 30 and finding 155 all 25, each with two jobs. Both base red records were
regenerated and fail by assertion. Proof records and exact diffs are in proof/VELDO-0165.
No canonical gate, real engine run or push was performed. Status remains ready for independent review.
