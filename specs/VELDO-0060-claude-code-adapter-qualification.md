---
schema: veldo.spec/v1
id: VELDO-0060
title: Claude Code production adapter qualification
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W45
plan_revision: 4
depends_on: [VELDO-0028, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0062]
placement: [fleet, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/fleet.py"
  - ".veldo/fleet.py"
  - "packs/*/.veldo/fleet.py"
  - "engine/.veldo/control_runner*.py"
  - ".veldo/control_runner*.py"
  - "packs/*/.veldo/control_runner*.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "packs/*/.veldo/control_launch*.py"
  - "engine/.veldo/control_engine_claude*.py"
  - ".veldo/control_engine_claude*.py"
  - "packs/*/.veldo/control_engine_claude*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/runtime/claude-qualification*.json"
  - ".veldo/runtime/claude-qualification*.json"
  - "packs/*/runtime/claude-qualification*.json"
  - "scripts/suites/*_veldo_0060_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0060-claude-code-adapter-qualification.md"
  - "specs/index.md"
  - "proof/VELDO-0060/*"
behavior_bearing: true
observability:
  logs: >
    Record the operation, domain, repository, unit or request identity, accepted input versions,
    outcome and named refusal without secrets.
  metrics: >
    Count accepted and refused operations and expose current pending work for this specification.
  traces: >
    Join accepted inputs, actual service observations and resulting authority records by identity.
  error_taxonomy: >
    Distinguish invalid input, missing authority, stale subject, unavailable service,
    missing evidence and unknown outcome where applicable; never label unknown as success.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The real Claude Code adapter implements normal launch, acceptance, observation
      streaming, stop, exit and artifact return through the trusted runner, from the pinned
      executable, on the everything-off baseline, behind the paid-API guard and the environment
      strip. Set and completeness: Enumerate these lifecycle operations from installed adapter
      registrations for the chosen configuration and explicit accepted source/input/tool bindings;
      invoke the actual binary in an isolated clone. Pinned executable: the adapter launches the
      versioned executable copied from `~/.local/share/claude/versions/` and kept under the factory
      state root, never the auto-updating `~/.local/bin/claude` link, sets `DISABLE_AUTOUPDATER`,
      and rejects an unknown version or changed digest before spawn. Baseline: every profile source
      is off (the `setting-sources` option restricted to one generated file passed through the
      `settings` option, the `strict-mcp-config` option with a generated `mcp-config` file, the
      `disable-slash-commands` option when no skill is listed, `CLAUDE_CODE_DISABLE_CLAUDE_MDS`,
      `CLAUDE_CODE_DISABLE_AUTO_MEMORY` and `disableAllHooks`), so the account profile supplies only
      the login and the same role behaves the same on every account; neither bare mode nor safe mode
      is used. Paid-API guard: the receiver removes `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, the
      Bedrock, Vertex and Foundry switches and `CLAUDE_CODE_OAUTH_TOKEN` (kept only for an account
      configured to use a subscription token) from the engine environment, and a run whose init
      event reports an `apiKeySource` other than `none` (or the configured token) is stopped by name
      before its first turn. Environment strip: the trusted wrapper removes `SSH_AUTH_SOCK`,
      `SSH_AGENT_PID`, `DBUS_SESSION_BUS_ADDRESS`, `GH_TOKEN` and `GITHUB_TOKEN` just before it
      execs the engine, and the engine's `XDG_RUNTIME_DIR` is an empty directory of its own. Each
      switch that is an environment variable or internal setting is qualified on the pinned version
      before use. The role's own selections arrive with VELDO-0127. Falsifier: Skip executable
      binding after its digest changes; the unexpected-launch check must fail.
    falsified_by: >
      Skip executable binding after its digest changes; the unexpected-launch check must fail.
  - id: AC2
    text: >
      Claim: Terminal output yields independently validated artifacts, never automatic completion.
      Set and completeness: Capture live normal/nonzero/signal exits and perturb actual stream bytes
      for absent terminal record, malformed output and missing usage; feed the production decoder,
      inspect resulting artifacts and retained unknown usage reservations. Falsifier: Accept zero exit
      with its terminal record removed; the missing-result check must fail.
    falsified_by: >
      Accept zero exit with its terminal record removed; the missing-result check must fail.
  - id: AC3
    text: >
      Claim: Ordinary stop terminates the adapter worker and records its original invocation
      outcome. Set and completeness: Use the real chosen configuration to perform cooperative and
      bounded forced stop through the host wrapper; compare OS exit, descendant termination and
      invocation identity. A stopped invocation with missing usage retains its reservation. Falsifier: Report
      stopped when a real worker descendant remains alive; the termination check must fail.
    falsified_by: >
      Report stopped when a real worker descendant remains alive; the termination check must fail.
  - id: AC4
    text: >
      Claim: Each subscription CLI invocation checks its usage caps before launch. Set and
      completeness: Exercise initial/retry/follow-on invocations with available, exhausted and
      unknown allowance under 0062. Observe invocation counts, wall time, CLI-reported
      tokens/messages and rate-limit windows; require worker stop at the cap and zero launches on
      refusal. No price or per-request monetary maximum is required. Separating the provider login
      from the worker's tools is Release 2 hardening for both engines (owner, Telegram 29163): in
      Release 1 a tool may read its own engine login, the same as an interactive session today.
      Falsifier: Check the cap after launch instead of before; the zero-launch refusal check must
      fail.
    falsified_by: >
      Check the cap after launch instead of before; the zero-launch refusal check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Claude Code production adapter qualification. Deliver the normal function needed by the running factory journey.

## Context

W45 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
Section 6 of the approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md)
designs the baseline, the paid-API guard and the pinned engine; section 3 the environment strip.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## What the reviewer judges

- Normal use: the Runner launches the pinned Claude Code executable for a dispatched unit in an isolated clone,
  on Linux in delivery and on the Mac in the host stage, with the account profile the dispatch
  selected; the adapter streams its events, stops it on request and returns its artifacts, and every
  invocation checks its usage caps first.
- Threat model: a launch of a changed or unknown executable, or of the auto-updating link; a run that picks up the
  account's own settings, instruction files, skills, memory or hooks; a paid API key reaching the
  engine, or a run that is not on a subscription login getting a first turn; the SSH agent, session
  bus or a Git token reaching the engine environment; a zero exit accepted without its terminal
  record; a worker descendant left alive after a reported stop; a launch after its cap is reached or
  while its allowance is unknown. The owner's account and the installed engine are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); separating the engine login from the worker's tools (Release 2, owner Telegram 29163); recovery
  and exhaustive escape or resource matrices (Release 2); other versions and host kinds (Release 4);
  files planted in the installed directory.

## Notes

Models run only through logged-in Claude Code and Codex subscriptions, never paid model APIs.
Use invocation and wall-time caps plus tokens/messages as the CLI reports them and its exposed
rate-limit windows. Check applicable remaining allowance before every invocation and stop the
worker at its cap. Missing usage retains conservative reservations under 0036/0062; unknown is
never zero. Qualification does not require a price, hidden CLI telemetry or a per-call charge.

In Release 1 the engine login is readable by the worker's tools, the same as an interactive session,
on the owner's decision (Telegram 29163); keeping it from them is Release 2 hardening. The mechanisms
found for that work are recorded in section 6 of the operating-model design.

Qualify one actual Claude Code version/configuration on Linux in delivery, then that
configuration on the Mac in the host stage. Record executable digest, flags, terminal
protocol, subscription authentication mode, exposed usage units/rate-limit windows and live usage. 0062 supplies provider
custody/caps; 0063 recovery/governor matrices are not prerequisites. Worker configuration is
handed through exactly, never silently reduced.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, pre-invocation subscription usage caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 1: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC3 recovery
and AC4 exhaustive escape/resource/quarantine qualification moved to Release 2; AC1 extra-
version/host matrix moved to Release 4, except Mac retained by 28852. One real configuration,
artifacts, custody, stop and caps remain. The criteria, declared evidence universe, Context
and Notes above now carry only the retained function. No specification status or historical
proof was changed.

2026-09-25, PLAN-0019 revision 4: amended on the approved operating-model design
(docs/design/PLAN-0019-operating-model-design.md, owner Telegram 29162), sections 3 and 6(e), and
the owner's answer to its section 15 (Telegram 29163). AC1 now qualifies the everything-off
baseline, the paid-API guard, the environment strip and the pinned executable with the adapter, and
the footprint adds the launch receiver and wrapper (`control_launch`), where the environment is
prepared; role selections arrive with VELDO-0127. AC4 keeps the pre-launch usage caps, and its
login-separation clause moves to Release 2 as hardening, for both engines; its falsifier is now the
cap order. A What the reviewer judges section is added. Status unchanged.
