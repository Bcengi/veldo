---
schema: veldo.spec/v1
id: VELDO-0232
title: Antigravity's CLI runs as a third Veldo engine on the same terms as Claude Code and Codex
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0127, VELDO-0141, VELDO-0155, VELDO-0156, VELDO-0160, VELDO-0165, VELDO-0172, VELDO-0173, VELDO-0185, VELDO-0230]
placement: [fleet, loop, distribution]
protected_paths: [".veldo/control_engine_claude.py", "engine/.veldo/control_engine_claude.py", ".veldo/control_engine_codex.py", "engine/.veldo/control_engine_codex.py"]
footprint:
  - ".veldo/control_engine_antigravity.py"
  - "engine/.veldo/control_engine_antigravity.py"
  - ".veldo/qualify.py"
  - "engine/.veldo/qualify.py"
  - ".veldo/control_launch.py"
  - "engine/.veldo/control_launch.py"
  - ".veldo/control_account_limit.py"
  - "engine/.veldo/control_account_limit.py"
  - ".veldo/accounts.py"
  - "engine/.veldo/accounts.py"
  - ".veldo/control_accounts.py"
  - "engine/.veldo/control_accounts.py"
  - ".veldo/control_reservation_runtime.py"
  - "engine/.veldo/control_reservation_runtime.py"
  - ".veldo/control_agent_config.py"
  - "engine/.veldo/control_agent_config.py"
  - ".veldo/control_agent_config_handoff.py"
  - "engine/.veldo/control_agent_config_handoff.py"
  - ".veldo/control_factory_setup_engines.py"
  - "engine/.veldo/control_factory_setup_engines.py"
  - ".veldo/control_factory_setup_dispatch.py"
  - "engine/.veldo/control_factory_setup_dispatch.py"
  - "packs/*/.veldo/**"
  - "engine/runtime/**"
  - ".veldo/runtime/**"
  - "packs/*/runtime/**"
  - "scripts/engine_census.py"
  - "scripts/suites/**"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "scripts/mutation_case_inputs.json"
  - "specs/VELDO-0232-antigravity-is-a-third-engine.md"
  - "specs/index.md"
  - "proof/VELDO-0232/**"
behavior_bearing: true
observability:
  logs: >
    The qualify command prints the Antigravity engine it qualified (version, pinned path, digest), each file
    it wrote, and every new item the binary brings with its decision, as it does for the other two engines.
    The launch receiver logs each Antigravity refusal and stop by its name (the same names as the other
    engines, plus the Antigravity-specific ones in error_taxonomy), with the dispatch id and account, never
    a credential value or the prompt.
  metrics: >
    None added. Antigravity runs are counted in the existing per-engine usage, limit and outcome counts
    under the engine name `antigravity`.
  traces: >
    Each Antigravity run's execution record (VELDO-0141) keeps every stdout line the binary printed, joined
    to its dispatch, account and the qualification (version, digest) it was bound against; each limit
    observation carries the line it was read from and that line's digest, as the other engines' do.
  error_taxonomy: >
    The shared names apply unchanged (stale_subject:engine_version, stale_subject:engine_digest,
    missing_evidence:engine_qualification, missing_evidence:engine_baseline:<version>, paid_api:<kind>,
    account_limit). Added: invalid_input:engine_profile:<entry> (an account folder holding something the
    qualified binary loads into every run and no option turns off), invalid_input:engine_clone:<entry> (the
    same in the clone), invalid_input:agent_mcp_servers:antigravity (a role for this engine that selects an
    MCP server, limit L1), configuration_stop:tool_outside_role (a tool call outside the role's set read
    from the stream, limit L2), and paid_api:antigravity_login:<kind> (an API-key, Cloud project,
    application-default, gateway, pay-as-you-go or AI-credits path).
acceptance_criteria:
  - id: AC1
    text: >
      Antigravity is pinned and qualified by the one command, with every new item decided (VELDO-0230 for
      a third engine). The engines record (runtime/engines.json and its byte-identical mirrors) names the
      qualified Antigravity version, binary and digest beside Codex and Claude Code; python3
      .veldo/qualify.py takes an Antigravity argument (a version or a path) and with none qualifies the
      binary `agy` on PATH resolves to. It copies that binary under the factory state root at
      engines/antigravity/<version> (mode 0555, digest checked), and every launch runs that copy, never
      ~/.local/bin/agy, which the binary's own updater replaces in place. The engine's environment carries
      AGY_CLI_DISABLE_AUTO_UPDATE, the switch the binary names. The command runs a committed extractor
      against the binary's own bytes and help (no prompt, no model call) and writes the Antigravity
      qualification record to every runtime copy: options, environment and credential names, the stream
      vocabulary (event types, step types, result fields, finished reasons, exit codes), the tool registry
      with each tool classified in_run or outward with its reason, the limit and refusal texts, and the
      places the binary loads instructions, rules, skills, plugins and hooks from. Every item the binary
      brings that the replaced record did not have is listed by name in the output and in the record
      (`new_capabilities`) with its decision from runtime/capability-decisions.json (granted, off with the
      written rule it breaks, or not applicable); an item with none is unevaluated and not granted, and
      nothing new stops a launch. Run twice on the same binary, the command rewrites every file with the
      bytes it holds. bind refuses a pinned copy whose version or digest differs from the record by the
      shared names before anything is accepted.
    falsified_by: >
      A fake agy that adds one step type and one registry tool to the qualified 1.5.0 tables: the qualify
      row fails if either is missing from `new_capabilities` with its decision, or if the launch of the
      newly qualified fake is refused; and launching ~/.local/bin/agy instead of the pinned copy makes
      the pinned-path row fail when the suite changes the unpinned file's digest.
  - id: AC2
    text: >
      An Antigravity run launches headless in the run's containment with only its role's grant, on the
      everything-off baseline (VELDO-0155, 0156, 0165 for this engine). The launch receiver spawns the
      pinned copy through the trusted wrapper, in the run's clone and containment group, with the
      qualified flags: print mode with stream-json output and stream-json input (the prompt is written on
      stdin, never in argv), the run's generated settings file passed through the settings option (used
      for that session only, never saved), slash commands and skill expansion off, permission prompts
      skipped (there is no human to answer one), no print timeout (Veldo's own deadline and stop apply),
      and never the remote-agent or remote-control options. The wrapper strips every inherited variable
      whose name starts with CLAUDE, CLAUDECODE, AI_AGENT or CODEX, and with ANTIGRAVITY, AGY or JETSKI (the
      names a parent Antigravity session sets), before it sets HOME to the account folder and the
      baseline's own variables. The generated settings deny every registry tool outside the role's native
      tools (VELDO-0127; the in-run classification when no revision is bound), the init event's tool list
      is kept in the run record, and a tool call the stream shows outside the role's set stops the run by
      name (configuration_stop:tool_outside_role, limit L2). A role for this engine that selects an MCP
      server is refused when saved (invalid_input:agent_mcp_servers:antigravity, limit L1). Each place the
      qualified binary loads instructions, rules, skills, plugins, hooks or MCP servers from that no
      option of that version turns off (the account folder's .gemini tree, the clone's and its parents'
      instruction files and .agents folders, as the record lists them; the binary's own built-in skills
      only if no option keeps them out) is refused by name before acceptance when it holds anything
      (invalid_input:engine_profile:<entry>, invalid_input:engine_clone:<entry>); nothing is deleted.
    falsified_by: >
      Remove the stream check for tool calls outside the role, and the suite's fake engine that calls a
      denied tool ends `complete` instead of stopped by name; plant ANTIGRAVITY_LS_ADDRESS and an AGY_ name
      no list holds in the parent environment, and the launched fake engine's environment row fails if
      either is present; plant a rule file in the account folder's .gemini/config, and the acceptance row
      fails if the run is accepted.
  - id: AC3
    text: >
      The output stream is read into the run record, the meter and the verdict exactly as the other
      engines' are (VELDO-0060, 0061, 0062, 0141, 0160, 0172). Every stdout line goes into the execution
      record as printed. The Meter charges tokens only from what the stream reports (the result's usage,
      cache reads counted once); a run whose result is missing leaves its usage unknown and its reservation
      retained. The Terminal is `complete` only when the stream is well formed against the qualified
      vocabulary, it ends with a result whose finished reason is absent, the exit is 0 and nothing stopped
      the run; a result with finished reason print_timeout, interrupted or error, exit 3 with its AGY_ERROR
      line, any other nonzero exit, a signal or a deadline each get their own verdict, and a line outside
      the vocabulary is malformed_output. tool_calls names each MCP or tool call from a step's tool_info by
      its canonical name, fails closed on a form the tables do not list (unknown, unreadable), and
      nested_work names the binary's subagent tools and subagent_info. The individual quota message ("Individual
      quota reached" with "Resets in <hours>h<minutes>m") is an `account_limit` window whose reset is the
      line's observation time plus the stated duration, rounded up to the minute; "Your AI credits balance
      is too low to continue." and the binary's other plan refusals are windows with no reset. VELDO-0172's
      rule holds: every Antigravity fake engine in the suites prints the forms of a recorded real 1.5.0
      stream-json run (one run the owner approves, kept in the proof with the account's identity redacted
      before commit).
    falsified_by: >
      Classify the individual quota line as an ordinary failure, and the limit row fails (no
      `account_limit`, no reset on the account); accept a zero exit whose result line is removed, and the
      missing-result row fails.
  - id: AC4
    text: >
      Antigravity accounts are in the pool with their limits and leases, subscription only (VELDO-0062,
      0160, 0185). accounts.PROFILE_ENV names HOME for `antigravity` (the binary has no configuration
      directory variable; it keeps .gemini under HOME), so an account is one folder (the folder the installation's
      model account names), registered once, and its login command is the binary run interactively with HOME set to it.
      Antigravity accounts run concurrently with each other and with the other engines' accounts, each run
      reserved and charged to the account its dispatch recorded, moved off an account at its limit, with
      the re-run-or-ask decision, as for the other engines. CREDENTIALS is every name the binary makes a
      login or a paid path, read from its bytes: GEMINI_API_KEY, GOOGLE_API_KEY,
      GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_GENAI_USE_VERTEXAI, GOOGLE_CLOUD_PROJECT,
      GOOGLE_CLOUD_LOCATION, GOOGLE_GEMINI_BASE_URL, AGY_ADC_AUTH, AGY_BUSINESS_PAYGO_TIER and the
      AGY_LLM_GATEWAY_ family on 1.5.0; none reaches the engine from the inherited environment and an
      adapter configuring one is refused by name. login_problem refuses, before acceptance, an account
      folder whose settings select a model API provider, a Google Cloud or pay-as-you-go billing model, or
      AI credits use (paid_api:antigravity_login:<kind>), so a run at its plan quota stops at the limit and
      never spends credits. Where the qualified binary's init event names the sign-in kind, the receiver
      writes the prompt only after it names a Google subscription sign-in (the Guard); the qualify command
      records whether it does (limit L3).
    falsified_by: >
      Pass GEMINI_API_KEY from the adapter's configuration, and the refusal row fails if the run is
      accepted; give an account folder settings that turn AI credits use on, and the paid-path row fails if
      the run is accepted; share one folder between two registrations, and the one-registration row fails.
required_evidence: [unit, integration]
rollback: >
  Revert the change: the engine module, its records and the `antigravity` entries leave the engines record,
  the account registry and the role schema; Claude Code and Codex are untouched (their modules are
  protected here). Registered Antigravity accounts become unknown providers that no dispatch selects; their
  folders are not touched.
---

## Intent

Google Antigravity's CLI (agy) runs on a Google AI subscription and is already used for reviews outside
Veldo. This specification makes it a third Veldo engine beside Claude Code and Codex, on exactly their terms and nothing more: pinned and
qualified by the one command, launched headless in the run's containment with only the role's grant, its
stream read into the run record, its accounts in the pool, subscription only.

## Context

Read for this specification: control_engine_claude.py, control_engine_codex.py and qualify.py at main
043c2ef6, the engine protocol in control_launch.py (ENGINE_PROTOCOL: PROVIDER, CREDENTIALS, SETTINGS,
REGISTRATION, Meter, Refused, bind, command, environment, Terminal, baseline, profile_problem,
login_problem, Guard), accounts.PROFILE_ENV and the engine tables in control_account_limit.py and
control_launch.py. The new module implements that protocol with the same signatures; nothing else in
the protocol changes.

The binary, probed read-only on 2026-11-04 (help, `agy models` on one subscription account, its bytes and
its embedded changelog; no prompt was run): the brief named 1.4.12, but ~/.local/bin/agy reported 1.5.0, its
file rewritten at 03:16 that day by its own updater. It is one 238 MB executable outside any package
manager, so it is pinned the way Claude Code's versioned copy is (VELDO-0060), not the way Codex's
vendor binary is. Its headless mode is print mode with text, json or stream-json output; stream-json is a
typed NDJSON stream of `init`, `step_update` (a closed `step_type` vocabulary, `tool_info` per tool call,
`subagent_info` per subagent) and a terminal `result` (with `usage`, including cache reads, and
`finished_reason`); stream-json input reads one prompt per line from stdin. Exit codes: 1 and 2 for usage
errors, 3 for a model or agent error with an AGY_ERROR line. Its options include a per-session settings
object that is never saved, disable-slash-commands, sandbox, mode, effort and model; it has no option that
names the tools offered, no per-run MCP server option (servers live in the account's
.gemini/config/mcp_config.json), and its subcommands (acp, agent, agents, changelog, help, install, mcp,
mic-serve, models, plugin, plugins, remote-control, update) include no login status. `agy models` fetches
the account's model list over the network (13 slugs on the probed account: Gemini 4 Argon, Gemini 3.8 Flash, Claude Opus
5.5 and Sonnet 5.5, GPT-OSS 120B, each at several efforts). Its quota is per model group with a five-hour
and a weekly window; the stream reports exhaustion as "Individual quota reached ... Resets in 4h23m"
(observed 2026-10-23) and, after plan quota with credits too low, "Your AI credits balance is too
low to continue." Its changelog also names a billing choice after a Google Cloud sign-in (a Gemini
subscription or pay as you go) and a "Use AI Credits" setting: both are paid paths AC4 refuses.

What parity means for this CLI, concretely: the pinned copy and qualification of VELDO-0060 and 0230; the
receiver's lifecycle of VELDO-0061; the subscription login and live usage of VELDO-0062; the role's grant
of VELDO-0127 and 0173 as far as the binary can enforce it (L1, L2); the run record of VELDO-0141; the
everything-off baseline and environment strip of VELDO-0155, 0156 and 0165; the pool, limit and re-run
decision of VELDO-0160; fakes that match a recorded real stream (VELDO-0172); setup giving the service its
adapter (VELDO-0185).

What Antigravity cannot do that Claude Code and Codex can, as qualified on 1.5.0. These are stated limits
of the engine; each is re-read by the qualify command on every new version, and one a later version lifts
is lifted by that version's decisions, not by this specification.

- L1. No per-run MCP servers. The binary reads servers only from the account folder, shared by every run
  of that account; Claude Code takes the run's own server file with every other source off, Codex takes
  the run's servers as overrides. An Antigravity role selects no MCP server.
- L2. No launch tool set. Claude Code removes every tool outside the role's set from what the model is
  offered (VELDO-0173) and Codex switches features off; Antigravity offers its whole registry. Veldo
  denies every call outside the role's set and stops a run that makes one, but the model still sees the
  denied tools, so VELDO-0127 AC4's comparison of the offered set with the role's does not hold for this
  engine; the enforced equality is of the calls.
- L3. No login status before work. Claude Code's `auth status` and Codex's `login status` let setup and
  the receiver confirm the account's subscription login before any run (VELDO-0185 AC4); Antigravity
  1.5.0 has no such command, so its account's login is known only from the stream (and from its init
  event if that names the sign-in kind) and from the pre-acceptance checks of AC4.
- L4. No offline model catalog. Codex's qualification records its bundled catalog; Antigravity's model
  list is per account and fetched over the network, so the qualification records no catalog and a role's
  model is checked against the account's list when the account is set up.
- L5. No stated utilization, and a relative reset. Claude Code's stream reports utilization and an
  absolute reset; Antigravity states only "Resets in" a duration (its usage screen is interactive only),
  so the reset is derived from the observation time.
- L6. The login folder is the worker's HOME. Claude Code and Codex name their login folder in a variable
  of their own, separate from HOME; Antigravity has none, so the worker's tools run with the account
  folder as their home (the Release 2 separation of login from tools, VELDO-0061 and 0062, applies here
  too and is not added by this specification). The engine's own model login stays where it is today; no
  new confinement of the engine or its tools is required (revised ruling R7).

VELDO-0231 (on its own branch) names Antigravity's means of flagging the lead as the marked line; that is
VELDO-0231's to carry, not this specification's.

## Out of scope

Anything beyond parity: new roles, staffing Antigravity into a team, choosing which work it does, model
selection policy, the Mac read-back (VELDO-0147), the terminal sandbox option (an item the
qualify command decides like any other), and buying or enabling AI credits (never; spend gate).
Migrating any script that runs the CLI outside Veldo onto Veldo.

## What the reviewer judges

- Normal use: on a host with agy 1.5.0 and one Antigravity account, the one command qualifies all three engines
  and a review role bound to `antigravity` runs a fake-backed and then one owner-approved real run inside
  containment, its stream in the run record and its usage on that account.
- Threat model: a paid path reached through an environment variable, a settings file, a Cloud sign-in or
  AI credits; a self-updated binary run unqualified; the account folder's rules, skills, plugins, hooks or
  MCP servers loaded into a run; a tool outside the role called and not stopped; a parent session's
  variables reaching the engine.
- Out of review scope (filed, not blocking): whether a later Antigravity version lifts L1 to L6; that is
  that version's qualification.

## History

2026-11-04: drafted from Telegram 39045. The binary was probed read-only (help, models on agy1, bytes,
embedded changelog); no prompt, no paid API, no settings change. The installed version was 1.5.0, not the
1.4.12 the brief named: the self-update observed that day is why AC1 pins a copy.

2026-11-04: approved by the owner, Telegram 39065 ("Yes approve all four"), with VELDO-0232, VELDO-0234, VELDO-0235 and core VELDO-3340. Status ready.

2026-11-04: amended under the plan consistency review (veldo-plan-consistency-review-2026-11-04.md) and the
lead's rulings (veldo-plan-rulings-2026-11-04.md), owner request Telegram 39145: the qualification record
declares the model hosts and whether the binary honours the outside gate's proxy settings, and a version
that ignores them fails closed and waits (A12, R5, R13); no role grants Antigravity until its login files are
unreadable to the run's tools (A7, R7); no personal account label, path or project outside History, and the
recorded run is redacted (B2, B7). The code on this branch is not changed; what it lacks is listed in
proof/VELDO-0232/OPEN.md items 5 to 9. Status stays ready; the owner approves the amendments in one message.
Dispositions: proof/VELDO-0236/review-dispositions-2026-11-04.md on the veldo-parity-a branch.

2026-11-05: Telegram 39154 and 39155, revised rulings R5, R7 and R14 (no mandatory sandbox): the old R13
requirements are removed, since they served only the sandbox: the qualification record no longer declares
model hosts or whether the binary honours the outside gate's proxy settings, and no version fails closed or
waits for proxy support (AC1, AC2, the engine_proxy refusal name). AC4 and L6 no longer hold roles back until
the login files are readable by the engine process only. Open items 5 and 6 in proof/VELDO-0232/OPEN.md are
withdrawn. Status stays ready; code unchanged.
