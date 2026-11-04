# VELDO-0232 proof: Antigravity's CLI as a third Veldo engine

Branch agent/claude/veldo-0232 from main 043c2ef6; the owner approved the spec in Telegram 39065.
The binary was read only: its bytes, `agy --help` and `agy --version` (in an empty HOME, no account, no prompt,
no model call, no paid API). The suites run fakes only. What is still open is in OPEN.md.

## What was built

- `.veldo/control_engine_antigravity.py` (and its byte-identical canon copy in engine/.veldo): the engine module.
  It implements control_launch.ENGINE_PROTOCOL with the same signatures (PROVIDER, CREDENTIALS, SETTINGS,
  REGISTRATION, Meter, Refused, bind, command, environment, Terminal, baseline, profile_problem, login_problem,
  Guard), plus pin, tool_options, account_login and the tool-call readers control_account_limit uses.
- `proof/VELDO-0232/extract_agy.py`: the committed extractor (bytes and help); its table is agy-tables.json.
- `.veldo/qualify.py`: `--antigravity <version or path>` (default: the `agy` on PATH) and `--state-root`.
- `.veldo/runtime/antigravity-qualification.json`, the `antigravity` entry of runtime/engines.json (both runtime
  copies), written from the real agy 1.5.0 (sha256:b9043860...6081862) by qualify's own functions.
- control_launch (engine registered, the parent-session strip prefixes, the meter, terminal and guard given the
  binding, engine stops and refusals logged with dispatch and account, the engine's own credential list),
  accounts (`antigravity: HOME`), control_accounts (HOME never stripped from or refused for another engine; the
  gateway family stripped), control_agent_config (L1 refusal at save, native tools from the registry),
  control_account_limit and control_reservation_runtime (the engine registered), factory setup (pins the
  qualified copy when the host holds it and gives the service an `antigravity` adapter), the engine census.
- Suites 127_veldo_0232_antigravity (25 rows) and 128_veldo_0232_live_forms (1 row), the fake's stream forms in
  scripts/suites/support/v232_agy_forms.py; suites 126, 85_0171 and 86_0186 adapted.

## AC1: pinned and qualified by the one command

Built: the extractor reads, from the binary, its options and subcommands (help), its stream events and finished
reasons (the changelog's own sentences in the bytes), its 118 step types (the CortexStepType enum's values in the
protobuf descriptor, length-prefixed names), its 17 registry tools (the antigravity.localharness fields typed
<Name>ToolConfig, plus the subagent and MCP step tools), the credential names, the refusal texts and the load
places. qualify writes the record to every runtime copy, the engines entry (version, the pinned copy, digest),
copies the binary to <state root>/engines/antigravity/<version> (0555, digest checked), and lists every new item
(tools, step types, events, finished reasons, credentials, options, subcommands) in `new_capabilities` and its
output with its decision from runtime/capability-decisions.json; one with none is unevaluated: a new tool is
outward, a new step type stays out of the reader's vocabulary, nothing new stops a launch. bind refuses another
version (`stale_subject:engine_version`) and a changed copy (`stale_subject:engine_digest`).

Test: suite 127 rows qualify/record, qualify/new-items, qualify/rerun-bytes, qualify/output, pin/copy,
pin/pinned-path, bind/stale. Red before (suite127-before.txt, run at 6ab78d54: 26 of 26 rows red), green after
(suite127-after.txt: 25 passed). Suite 126 (the whole command against the real binaries) reproduces the
Antigravity record, the agy tables and the engines record byte for byte (suite126-after.txt; its one red row is
OPEN.md item 2).

Falsifier applied: a fake agy adding one step type and one tool (qualify/new-items lists both, unevaluated);
mutants agy232-new-items-unlisted (both left out of new_capabilities) and agy232-new-tool-refused (a new tool
left unclassified, so its launch is refused) turn qualify/new-items red; agy232-launch-unpinned (bind runs the
source the updater rewrites) turns pin/pinned-path red (the suite rewrites the unpinned source between launches).

## AC2: headless, contained, only the role's grant, everything off

Built: FLAGS `--print --output-format stream-json --input-format stream-json --disable-slash-commands
--dangerously-skip-permissions --print-timeout 0s`, never --remote-agent or --remote-control; the prompt is one
stream-json message on stdin. The baseline adds `--settings <run config>/settings.json` whose `permissions.deny`
names every registry tool outside the role's native tools (the in-run classification with no revision). The
trusted wrapper strips CLAUDE, CLAUDECODE, AI_AGENT, CODEX and ANTIGRAVITY, AGY, JETSKI before HOME (the account
folder) and the baseline's own values are set. The Guard stops a step whose tool is outside the role's set
(`configuration_stop:tool_outside_role`, logged by name with dispatch and account); an MCP role is refused at save
and before acceptance (`invalid_input:agent_mcp_servers:antigravity`); profile_problem refuses, by name and before
acceptance, the account folder's .gemini places (`invalid_input:engine_profile:<entry>`) and the clone's and its
parents' GEMINI.md, AGENTS.md, .agents and .agent (`invalid_input:engine_clone:<entry>`); nothing is deleted.

Test: suite 127 rows launch/flags, launch/settings, launch/environment, launch/tool-outside-role, launch/role-mcp,
launch/profile, launch/clone (real Runner, receiver and reported-identity wrapper). Red before, green after.

Falsifier applied: agy232-outside-tool-unstopped (the stream check removed: the run ends complete) turns
launch/tool-outside-role red; agy232-parent-names-reach (ANTIGRAVITY_LS_ADDRESS and an AGY_ name planted in the
parent reach the engine) turns launch/environment red; agy232-profile-rule-accepted (a rule file planted in
.gemini/config, accepted) turns launch/profile red.

## AC3: the stream into the run record, the meter and the verdict

Built: every stdout line is kept (the execution record and the artifact's lines); the Meter charges input plus
output tokens from the result's usage (cache reads are part of the input, counted once), and a run with no
result leaves usage unknown; the Terminal is `complete` only for a well-formed stream ending in a result with no
finished reason, exit 0 and no stop; `finished:<reason>`, `agent_error` (exit 3, its AGY_ERROR line kept),
`nonzero_exit`, `signal`, `deadline`, `malformed_output`, `missing_result` and `stopped` are each their own.
tool_calls names MCP steps by server and tool and fails closed (unknown, unreadable); nested_work names the
subagent tools and subagent_info. "Individual quota reached ... Resets in <h>h<m>m" is an `individual_quota`
window whose reset is the observation time plus the duration rounded up to the minute; "Your AI credits balance
is too low to continue." is an `ai_credits` window with no reset.

Test: suite 127 rows stream/record, stream/meter, stream/missing-result, stream/verdicts, stream/limit,
stream/tool-calls; suite 128 row stream/live-forms (red: no recorded real run yet, OPEN.md item 1).

Falsifier applied: agy232-quota-ordinary (the quota line an ordinary failure: no window, no reset) turns
stream/limit red; agy232-missing-result-complete (a zero exit whose result line is removed completes) turns
stream/missing-result red.

## AC4: accounts in the pool, subscription only

Built: accounts.PROFILE_ENV names HOME for `antigravity`; the login step is `HOME=<folder> agy`. The engine's
CREDENTIALS (21 names on 1.5.0, read from its bytes, the gateway family included) never reach its run and an
adapter configuring one is refused by name. login_problem refuses, before acceptance, an account folder whose
settings select an API key, a model API provider, a Cloud project, the application-default login, a gateway, pay
as you go or AI credits (`paid_api:antigravity_login:<kind>`). One folder is registered once; the pool chooses
Antigravity accounts like the others and moves off one at its limit; the re-run-or-ask decision reads an
Antigravity record; its invocations are reserved on the three boundaries. The init event names no sign-in kind
on 1.5.0, so the record's `init_sign_in` is null (L3) and the Guard writes the prompt at once; a record naming
one makes the Guard hold the prompt until init names a subscription.

Test: suite 127 rows accounts/profile, accounts/credential-refused, accounts/paid-path, accounts/one-registration,
accounts/pool. Red before, green after.

Falsifier applied: agy232-adapter-key-accepted (GEMINI_API_KEY from the adapter's configuration) turns
accounts/credential-refused red; agy232-ai-credits-accepted (settings turning AI credits on) turns
accounts/paid-path red; agy232-folder-twice (one folder under two registrations) turns accounts/one-registration
red.

## Mutation cases

Eleven, registered in scripts/check_teeth_mutations.py as finding 232 against suite 127, each run alone through
the gate's driver (`python3 scripts/check_teeth_mutations.py --case <name>`): baseline and no-op green, the mutant
red on its rows, status passed for all eleven (mutations.txt).

## Evidence files

suite127-before.txt, suite127-after.txt, suite128-after.txt, suite126-after.txt, neighbours.txt, mutations.txt,
agy-tables.json (the extractor's table of agy 1.5.0), extract_agy.py.
