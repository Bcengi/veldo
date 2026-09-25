---
schema: veldo.spec/v1
id: VELDO-0155
title: Every Claude Code run starts on the everything-off baseline, behind the paid-API guard and the environment strip
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W115
plan_revision: 4
depends_on: [VELDO-0039, VELDO-0060]
placement: [fleet, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "packs/*/.veldo/control_launch*.py"
  - "engine/.veldo/control_engine_claude*.py"
  - ".veldo/control_engine_claude*.py"
  - "packs/*/.veldo/control_engine_claude*.py"
  - "engine/runtime/claude-qualification*.json"
  - ".veldo/runtime/claude-qualification*.json"
  - "packs/*/runtime/claude-qualification*.json"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0155_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0155-claude-code-run-baseline-and-guards.md"
  - "specs/index.md"
  - "proof/VELDO-0155/*"
behavior_bearing: true
observability:
  logs: >
    Record each launch's baseline options, the variable names removed from the engine environment, the
    init event's reported `apiKeySource` and any named stop; never a variable's value.
  metrics: >
    Count launches, runs stopped before their first turn by reason, and removed variables by name.
  traces: >
    Join each launch to its dispatch, account profile and the pinned executable digest it ran.
  error_taxonomy: >
    Distinguish a profile source that loaded, a paid-API variable present, a login that is not a
    subscription, and a stripped variable present; none lets the run take a first turn.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every Claude Code run starts with every profile source off, so the account profile supplies
      only the login and the same role behaves the same on every account. Set and completeness: Launch the
      pinned executable (VELDO-0060 AC1) with the `setting-sources` option restricted to one generated
      file passed through the `settings` option, the `strict-mcp-config` option with a generated
      `mcp-config` file, the `disable-slash-commands` option when no skill is listed,
      `CLAUDE_CODE_DISABLE_CLAUDE_MDS`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY` and `disableAllHooks`; neither
      bare mode nor safe mode is used. Plant settings, an MCP server, a skill, an instruction file, memory
      and a hook in the account profile and the clone, each where only its own switch keeps it out, and
      require none of them in the run, read from the init event's lists and the debug log, one row per
      planted item. Each switch that is an environment variable or internal setting is qualified on the
      pinned version before use. Falsifier: Six mutants, one per switch, each dropping that switch with
      the others in place: drop the `setting-sources` restriction, and the planted-settings row must fail;
      drop `strict-mcp-config`, and the planted-server row must fail; drop `disable-slash-commands`, and
      the planted-skill row must fail; unset `CLAUDE_CODE_DISABLE_CLAUDE_MDS`, and the
      planted-instruction-file row must fail; unset `CLAUDE_CODE_DISABLE_AUTO_MEMORY`, and the
      planted-memory row must fail; drop `disableAllHooks`, and the planted-hook row must fail.
    falsified_by: >
      Six mutants, one per switch, each dropping that switch with the others in place: drop the
      `setting-sources` restriction, and the planted-settings row must fail; drop `strict-mcp-config`, and
      the planted-server row must fail; drop `disable-slash-commands`, and the planted-skill row must
      fail; unset `CLAUDE_CODE_DISABLE_CLAUDE_MDS`, and the planted-instruction-file row must fail; unset
      `CLAUDE_CODE_DISABLE_AUTO_MEMORY`, and the planted-memory row must fail; drop `disableAllHooks`, and
      the planted-hook row must fail.
  - id: AC2
    text: >
      Claim: No paid-API credential variable reaches a Claude Code engine environment. Set and
      completeness: Plant `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, the Bedrock, Vertex and Foundry
      switches and `CLAUDE_CODE_OAUTH_TOKEN` in the caller's environment, launch a run, and read back the
      engine's environment: the receiver removed every one of them, except `CLAUDE_CODE_OAUTH_TOKEN` for
      an account configured to use a subscription token, where only that account's token is present.
      Falsifier: Leave a planted `ANTHROPIC_API_KEY` in the engine environment; the engine-environment
      read-back row must fail.
    falsified_by: >
      Leave a planted `ANTHROPIC_API_KEY` in the engine environment; the engine-environment read-back row
      must fail.
  - id: AC3
    text: >
      Claim: A Claude Code run that is not on a subscription login is stopped by name before its first
      turn. Set and completeness: Feed the adapter the init event of a real run, and init events whose
      `apiKeySource` is each value other than `none` the installed version reports; the run with `none`
      (or the configured subscription token for an account configured to use one) takes its first turn,
      and every other is stopped by name before its first turn with no model turn sent. Falsifier: Let a
      run whose init event reports an `apiKeySource` other than `none` take its first turn; the paid-API
      stop row must fail.
    falsified_by: >
      Let a run whose init event reports an `apiKeySource` other than `none` take its first turn; the
      paid-API stop row must fail.
  - id: AC4
    text: >
      Claim: The trusted wrapper strips the SSH agent, the session bus and the Git tokens from the
      environment it execs Claude Code with, and the engine gets a runtime directory of its own. Set and
      completeness: Plant `SSH_AUTH_SOCK`, `SSH_AGENT_PID`, `DBUS_SESSION_BUS_ADDRESS`, `GH_TOKEN` and
      `GITHUB_TOKEN` in the receiver's environment, launch a contained run, and read back the engine's
      environment: none of them is present (the strip read-back row), and `XDG_RUNTIME_DIR` names an empty
      directory of the run's own, never the receiver's and never the one holding the run's generated
      configuration (the private-runtime-directory row); the receiver's own `systemd-run` and `systemctl`
      calls still reach the user manager (the user-manager row). Falsifier: Leave a planted
      `SSH_AUTH_SOCK` in the environment the wrapper execs the engine with, and the strip read-back row
      must fail; pass the receiver's own `XDG_RUNTIME_DIR` to the engine, and then the directory holding
      the run's generated configuration, and the private-runtime-directory row must fail each time; strip
      the session bus from the receiver's own environment instead of the one it execs, and the
      user-manager row must fail.
    falsified_by: >
      Leave a planted `SSH_AUTH_SOCK` in the environment the wrapper execs the engine with, and the strip
      read-back row must fail; pass the receiver's own `XDG_RUNTIME_DIR` to the engine, and then the
      directory holding the run's generated configuration, and the private-runtime-directory row must fail
      each time; strip the session bus from the receiver's own environment instead of the one it execs,
      and the user-manager row must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new Claude Code launches while preserving accepted records and unresolved work; no run
  launches without these guards. No automatic rollback is authorized.
---

## Intent

Every Claude Code run the factory starts behaves the same on every account, never reaches a paid model
API, and never carries the owner's SSH agent, session bus or Git tokens into the engine.

## Context

W115 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1. Section 6 of the
approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner Telegram
29162) designs the everything-off baseline and the paid-API guard, and section 3 the environment strip;
its section 12 builds them with the Claude Code adapter (item 2). They were VELDO-0060 AC5, one
criterion under one falsifier that tested only the paid-API stop, and are split out so each guard has
its own criterion and a falsifier that breaks exactly that guard. VELDO-0060 keeps the adapter
lifecycle, the pinned executable, stopping and the usage caps. This new specification is draft;
authoring it supplies neither implementation proof nor operational activation.

## Out of scope

The role's own selections (VELDO-0127); separating the engine login from the worker's tools (Release 2,
owner Telegram 29163); the Mac leg (VELDO-0147); the Codex guards (VELDO-0156).

## What the reviewer judges

- Normal use: the Runner launches Claude Code for a dispatched unit on Linux; the account profile gives
  the login and nothing else, the engine environment holds no paid-API key, SSH agent, session bus or
  Git token, and the run takes its first turn on a subscription login.
- Threat model: a run that picks up the account's own settings, instruction files, skills, memory or
  hooks; a paid-API key reaching the engine; a run that is not on a subscription login getting a first
  turn; the SSH agent, the session bus or a Git token reaching the engine environment, or the engine
  sharing the receiver's runtime directory. The owner's account and the installed engine are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); a worker's
  tools reading their own engine login (Release 2, owner Telegram 29163); a worker deliberately
  reaching the keystore or the agent through the owner's unconfined keyring daemon (the stated MVP
  boundary of the design's section 3); other versions and host kinds (Release 4).

## Notes

The strip is applied by the trusted wrapper just before it execs the engine, not by the receiver, so
`systemd-run` and `systemctl` keep the receiver's environment and still reach the user manager. It is
the same wrapper for both engines; VELDO-0156 AC4 reads back the Codex engine's environment against the
same list. It removes the accidental routes to the keystore and the SSH agent, not the deliberate ones,
as the design's section 3 states.

Use canonical engine assets and synchronize installed copies. Inventory every asset the selected
journey installs. Compare executable registrations to each criterion's declared universe, observe the
real named interfaces, and retain the driven negative-control diff and named failed row. Fixtures
cannot certify real engine or host behavior. Required evidence labels describe future implementation
proof, not tests run by this writing revision.

## History

2026-09-25: split from VELDO-0060 AC5 on the third review of PLAN-0019 revision 4, so the everything-off
baseline, the paid-API guard and the environment strip each have their own criterion and a falsifier
that breaks exactly that guard: a planted profile item that must not load (AC1), a planted key that must
be absent from the engine environment read-back (AC2), the stop that must fire on an `apiKeySource`
other than `none` (AC3), and a planted agent socket the strip must remove (AC4). The paid-API guard's two
checks, the removal and the stop, are AC2 and AC3. The criteria carry VELDO-0060 AC5's text, and AC4
also checks that the user manager stays reachable, which is why the design's section 3 puts the strip
in the wrapper; no function is added or cut. A draft: only the owner marks a specification ready.

2026-09-25, PLAN-0019 revision 4, fourth review: AC1's falsifier dropped one of its six switches, so it
now drives one mutant per switch, each against its own planted item placed where only that switch keeps
it out; the planted set adds an MCP server, which `strict-mcp-config` keeps out. AC4's private runtime
directory and the user manager staying reachable get falsifiers of their own beside the strip's.
Criterion meaning unchanged. A draft.
