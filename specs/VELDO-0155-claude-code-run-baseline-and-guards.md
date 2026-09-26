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
  - "scripts/suites/75_veldo_0062_accounts.py"
  - "scripts/suites/78_veldo_0060_claude_adapter.py"
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
      the planted-skill row must fail; unset `CLAUDE_CODE_DISABLE_AUTO_MEMORY`, and the planted-memory row
      must fail; unset `CLAUDE_CODE_DISABLE_CLAUDE_MDS`, and drop `disableAllHooks`, each a second layer
      behind the `setting-sources` restriction, which already keeps the profile's and the clone's
      instruction files and hooks out, and the baseline row, which reads the baseline the run launched
      with, must fail each time.
    falsified_by: >
      Six mutants, one per switch, each dropping that switch with the others in place: drop the
      `setting-sources` restriction, and the planted-settings row must fail; drop `strict-mcp-config`, and
      the planted-server row must fail; drop `disable-slash-commands`, and the planted-skill row must
      fail; unset `CLAUDE_CODE_DISABLE_AUTO_MEMORY`, and the planted-memory row must fail; unset
      `CLAUDE_CODE_DISABLE_CLAUDE_MDS`, and drop `disableAllHooks`, each a second layer behind the
      `setting-sources` restriction, which already keeps the profile's and the clone's instruction files
      and hooks out, and the baseline row, which reads the baseline the run launched with, must fail each
      time.
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

2026-09-26, built on branch build-veldo-0155-0156 with VELDO-0156, which shares the wrapper. The version
is qualified with the baseline (the record's `baseline`, else `missing_evidence:engine_baseline:<version>`
before acceptance) and every run adds it right after its qualified flags: `--setting-sources` with no
source, the run's generated `--settings` file (`disableAllHooks`) and `--mcp-config` file (no server),
`--strict-mcp-config`, `--disable-slash-commands`, CLAUDE_CODE_DISABLE_CLAUDE_MDS and
CLAUDE_CODE_DISABLE_AUTO_MEMORY, the files 0600 in the run's own configuration directory, removed with
the run; every name is read from the 2.1.281 bytes (proof/VELDO-0155/claude-baseline.json). AC2: the
paid-API names were already stripped (VELDO-0062); an account the receiver's `subscription_tokens` names
runs with its own token as CLAUDE_CODE_OAUTH_TOKEN, an unreadable token file refused by name. AC3: an
init event whose apiKeySource is not `none` stops the run by name (stop cause `paid_api`); the review's
Anthropic profile case cannot be caught there (the binary reports `none` for it, and takes the profile
ahead of the claude.ai login), so the receiver refuses it by name before acceptance. AC4: the wrapper
strips the five names just before its exec and gives the engine the run's own empty runtime directory.
Two findings for the owner, from the binary's own code: with no setting source, the profile's and the
clone's MCP servers, skills, instruction files and hooks are also kept out by the sources restriction, so
the falsifiers that unset CLAUDE_CODE_DISABLE_CLAUDE_MDS or drop disableAllHooks cannot red a planted row
(their mutants are held by the baseline row and driven as survivors; strict MCP and slash commands are
falsified on what only they keep out, the login's claude.ai connectors and the bundled skills); and the
init event comes with the first turn, so the stream stop races the first model request on the real
binary. The footprint adds the VELDO-0062 and VELDO-0060 suites, whose exact argv checks and test records
the baseline changes. Proof: suite `80_veldo_0155_claude_baseline` (16 rows), the red record at
45ee21bb, finding 155's mutations. Status unchanged.

2026-09-26, lead decision (a) on the review of build-veldo-0155-0156 at 18644a43: AC1's falsifiers for
CLAUDE_CODE_DISABLE_CLAUDE_MDS and `disableAllHooks` now say what the 2.1.281 bytes allow. With
`--setting-sources` empty the binary gates the profile's and the clone's instruction files and hooks by
their source, so neither switch alone keeps a planted item out, and a mutant dropping one cannot red a
planted row (proof/VELDO-0155/survivors.json). Both switches stay in the baseline as a second layer (they
also keep out the managed instruction files and the flag, plugin and session hooks, which no source
covers), and their mutants are held by the baseline row, which reads the baseline the run launched with.
The planted instruction-file and hook rows stay. Criterion meaning unchanged; the specification stays
ready.

2026-09-26, fix round on the review of build-veldo-0155-0156 at 18644a43, AC3 and the filed findings. The
stream stop raced the first model request (the init event comes with the turn), so the run now holds its
prompt: the version is qualified with stream JSON input (`--input-format stream-json`, else
`missing_evidence:engine_input_protocol:<version>` before acceptance), the receiver writes the initialize
control request first, and the binary's answer (its Kfe() account, read from the 2.1.281 bytes into
proof/VELDO-0155/claude-baseline.json, `input_protocol`) must name the first-party backend, no API key, and
a claude.ai subscription or the account's own subscription token; anything else stops the run by name
before any prompt is written (`paid_api:apiKeySource|apiProvider|tokenSource|subscriptionType:<value>`),
and only a confirmed login gets the packet as the user message. Every init event of the stream is read,
not only the first. A relative XDG_CONFIG_HOME, HOME or credentials_path resolves against the engine's
working directory (the clone's work tree the entrance changes into), as the binary resolves it, through a
new `cwd` argument of the engine protocol's `profile_problem` and `login_problem`; one whose working
directory is unknown is refused by name. The token file is opened once and checked and read on that
descriptor. The VELDO-0060 footprint changes with it (the qualified flags, the receiver's input path and
suite 78's fake and rows; its History records it); the VELDO-0062 suite's fake and test record follow.
Proof: suite `80_veldo_0155_claude_baseline` (17 rows: `paid-api/stop` per login the answer can name,
`paid-api/every-init` new, `paid-api/profile-login` with the relative cases), the red record at 45ee21bb
(15 behavior rows), finding 155's 24 mutations (the new ones include the prompt sent before the check); 25 with the subscription-label mutant of the check below.
Criterion meaning unchanged; the specification stays ready.

2026-09-26, the check of build-veldo-0155-0156 at 04bbe2c2 (rv155b, filed): the guard took any non-empty
subscriptionType as a claude.ai subscription, and "Claude API" is the binary's own default label for a tier
that is not one (its wBn(): Enterprise, Team, Max and Pro, else "Claude API"; proof/VELDO-0155/claude-baseline.json,
subscriptions). `Guard` now accepts only the four subscription labels (`SUBSCRIPTIONS`) and stops any other by
name (`paid_api:subscriptionType:<label>`) before the prompt is written. Suite 80's `paid-api/stop` adds the
"Claude API" run and each of the four labels fed to the production Guard; finding 155's new mutant
(`claude-subscription-label-unchecked`, the pre-fix check) reds it. Criterion meaning unchanged; the
specification stays ready.
