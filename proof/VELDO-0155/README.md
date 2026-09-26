# VELDO-0155 proof: every Claude Code run on the everything-off baseline, behind the paid-API guard and the environment strip

Built on branch build-veldo-0155-0156 from 45ee21bb, together with VELDO-0156, because both engines share
the trusted wrapper and its strip.

## The design as built

**The baseline, qualified on the pinned version.** `control_engine_claude.BASELINE` names every switch, each
the 2.1.281 binary's own (`claude-baseline.json`, below): `--setting-sources` with no source, the run's
generated `--settings` file holding `{"disableAllHooks": true}` and `--mcp-config` file holding
`{"mcpServers": {}}` (the run's servers; none until VELDO-0127 lists them), `--strict-mcp-config`,
`--disable-slash-commands` (no skill is listed yet), CLAUDE_CODE_DISABLE_CLAUDE_MDS=1 and
CLAUDE_CODE_DISABLE_AUTO_MEMORY=1. Neither bare mode nor safe mode is used. The version's entry in the
qualification record must carry `baseline` equal to it; `bind` refuses one that does not by name before
acceptance (`missing_evidence:engine_baseline:<version>`), so an upgrade is a requalification. The shipped
record (`engine/runtime/claude-qualification.json`, installed at `.veldo/runtime/`) carries it.

**Where it goes.** The protocol gains `baseline(binding, run, environment)`, `profile_problem(binding,
environment, cwd)`, `login_problem(binding, environment, cwd)` and `Guard` with `opening`, `release` and
`feed` (both engines implement all of them). At the spawn the receiver makes the run's own
directories, `<runs>/<digest of the dispatch>/{config,runtime}` (0700, fresh, outside every clone; the
config's `runs`, else the state root's `runs`, else beside the store), writes the generated files 0600
into `config`, splices the baseline right after the qualified flags (`baseline_at`, so an adapter's own
trailing arguments stay last), sets the baseline's environment, and removes the directories once the
engine has ended, before its end is recorded (a group that could not be emptied keeps them). It reports
each launch's baseline options, environment names, files and removed names in a `baseline` event, never a
value.

**The paid-API guard.** The names were already removed from every engine environment by VELDO-0062's strip
(by family and by the binary's lists); an adapter configuring one is refused. An account the receiver's
`subscription_tokens` names (account to a 0600 file of this account's own) runs with that token as
CLAUDE_CODE_OAUTH_TOKEN, the one login variable it then carries; a token file another account could read,
or not a regular file of this account's, is refused by name before acceptance
(`missing_authority:subscription_token:<account>`). The file is opened once (O_NOFOLLOW, O_NONBLOCK) and
checked and read on that one descriptor at binding, so what is checked is what reaches the engine.

**The handshake that holds the prompt.** The version is qualified with stream JSON input
(`--input-format stream-json` among its flags, which the binary accepts only with stream JSON output in
print mode); a record without it is refused by name before acceptance
(`missing_evidence:engine_input_protocol:<version>`). The receiver writes the engine's input from
`Guard.opening(packet)`: for Claude Code the initialize control request alone, the input left open and the
packet held. The binary answers with a control response whose `account` is its Kfe(): the backend
(`apiProvider`), `apiKeySource` only when an API key is in use, `tokenSource` for a token login that is not
a claude.ai subscription (the account's own CLAUDE_CODE_OAUTH_TOKEN among them), `subscriptionType` for a
claude.ai subscription, and neither for an Anthropic profile. `Guard.feed` confirms the login only when the
answer is a success on the first-party backend, with no API key, and a claude.ai subscription (a
`subscriptionType` of the binary's Enterprise, Team, Max and Pro labels, `SUBSCRIPTIONS`; its default label for
any other tier, "Claude API", is not one, from the check of 2026-09-26) or the account's own subscription
token; anything else stops the worker by name before any prompt is written
(`paid_api:apiKeySource:<v>`, `paid_api:apiProvider:<v>`, `paid_api:tokenSource:<v>`,
`paid_api:subscriptionType:<label or None>`, `paid_api:initialize:<subtype>`; stop cause `paid_api`, the invocation
cancelled, the artifact's `login` naming it, the verdict `stopped`). Only then does `Guard.release()` hand
the receiver the packet as the user message of stream JSON input, which it writes before closing the input;
a stopped run's input is closed with nothing more written. Every init event of the stream (one per turn) is
read as well: one whose apiKeySource is not `none` stops the worker by name before that turn. Codex's
`Guard.opening` is its packet whole, the input closed, and nothing is held. Before acceptance,
`login_problem` refuses the login no answer or init event shows ahead of the claude.ai login (below).

**The environment strip.** The trusted wrapper, just before it execs, removes SSH_AUTH_SOCK, SSH_AGENT_PID,
DBUS_SESSION_BUS_ADDRESS, GH_TOKEN and GITHUB_TOKEN from what it execs and makes the run's empty `runtime`
directory the engine's XDG_RUNTIME_DIR (`engine_environment`, applied only to an environment naming
VELDO_ENGINE_RUNTIME_DIR, which the receiver sets for an engine launch and the wrapper removes). The
receiver's own environment keeps all of them.

## What the binary's own code says, and what it means for the criteria

Read from the bytes of 2.1.281 (`extract_baseline.py`, `claude-baseline.json`, each anchor the exact text):

- `--setting-sources` with an empty list leaves only the `--settings` file and managed policy
  (`KIr("")` is no source; the binary spawns itself with `--setting-sources=` for the same).
- The profile's and the clone's MCP servers (user, project and local scopes), skills, CLAUDE.md files and
  the hooks of their settings are each gated by their setting source AND by their own switch. With no
  source, dropping `--strict-mcp-config`, `--disable-slash-commands`, CLAUDE_CODE_DISABLE_CLAUDE_MDS or
  `disableAllHooks` alone loads none of them. What only each switch keeps out: the claude.ai connectors
  of the account's login (strict MCP: `HZe(){return!VI()&&...}`), the bundled skills (slash commands:
  `this.disableSlashCommands?this.noCommands`), the managed CLAUDE.md under /etc/claude-code and
  `--add-dir` directories (not relocatable, not used), and hooks of the `--settings` file itself,
  `--plugin-dir` plugins and skill or agent frontmatter (none in a baseline run). Auto memory is gated by
  its switch only.
- So AC1's placement "each where only its own switch keeps it out" holds for settings, the server (the
  login's claude.ai connector), the skill (a bundled one) and memory. For the instruction file and the
  hook no location in the profile or the clone exists: their falsifier mutants
  (`claude-baseline-claude-mds-unset`, `claude-baseline-hooks-kept`) leave the planted rows green
  (`survivors.json`) and are held by `baseline/qualified`, which reads the switch itself. This is a
  finding for the owner: the spec's two falsifiers cannot be met against this binary.
- The init event's apiKeySource is the API KEY source (`zrn(){return Yf().source}`): a claude.ai
  subscription, CLAUDE_CODE_OAUTH_TOKEN, ANTHROPIC_AUTH_TOKEN and an Anthropic profile all report `none`.
  The review's case (a profile under XDG_CONFIG_HOME or HOME) is therefore invisible to the stream stop;
  the binary takes an implicit profile ahead of the claude.ai login (always for oidc_federation, for
  user_oauth when no usable claude.ai login exists). `login_problem` resolves the store as the binary does
  (XDG_CONFIG_HOME/anthropic, else HOME/.config/anthropic; ANTHROPIC_CONFIG_DIR and ANTHROPIC_PROFILE are
  stripped), reads only the active profile's configuration (never its credentials, whose size alone
  decides a user_oauth one) and refuses either type by name (`paid_api:anthropic_profile:<type>`). It
  refuses a user_oauth profile even when the claude.ai login would win, which the receiver cannot see
  without reading the login. A relative XDG_CONFIG_HOME, HOME or `credentials_path` is the binary's
  relative to its own working directory (it joins the path and reads it as given), so the receiver
  resolves it against the engine's: the work tree of the dispatch's clone, which the clone entrance
  changes into, else the receiver's own; one whose working directory is unknown (another host's engine)
  is refused by name (`paid_api:anthropic_profile:unresolved`).
- The init event is built per turn, after the prompt and just before the model request (`Tn` then `Sh`
  inside `submitMessage`), so on the real binary a stream stop alone races the first request. The stream
  JSON input's `initialize` control request is answered before any prompt (`input_protocol` in
  `claude-baseline.json`: the request and response schemas, the answer built by `Tc` with `account` from
  `Kfe()`, the token sources of `Mc()`, the subscription names of `wBn()`), so the receiver checks the login
  there and writes the prompt only after it. This changes VELDO-0060's input binding: its qualified flags
  gain `--input-format stream-json`, the prompt reaches the engine as a user message, and the VELDO-0060
  suite's fake, test record and argv, shipped-record and stream line-count rows follow (its History).

## Suite

`scripts/suites/80_veldo_0155_claude_baseline.py` (`python3 scripts/selftest.py --suite
80_veldo_0155_claude_baseline`). Real: a SQLite store with OpenSSH journal signatures, account records the
owner registers over profiles the helper prepares, VELDO-0036 reservations, VELDO-0052's Gate, VELDO-0031
claims, a Git source bound to the store, VELDO-0042 clones confined with Landlock, the VELDO-0039 Runner
and receiver processes, the trusted wrapper and VELDO-0040 transient scopes in a slice of the run's own.
The engine is a fake `claude` pinned by the production `pin`, whose loading is the binary's gate table
written into it; a fixture in the profile stands in for the claude.ai service's list of the login's
connectors, and another for what the binary's key lookup and backend switches find (a key, a key helper, a
cloud backend). It speaks stream JSON input as the binary does: it answers the initialize request with the
account Kfe() would build, takes the prompt from the user message, and prints one init event per turn. The receiver's environment carries every planted name: the five the wrapper strips (the real
session bus address) and the six paid-API names.

| Criterion | Rows |
|---|---|
| AC1 | `baseline/qualified`, `baseline/planted-settings`, `baseline/planted-server`, `baseline/planted-skill`, `baseline/planted-instructions`, `baseline/planted-memory`, `baseline/planted-hook` |
| AC2 | `paid-api/read-back` (declared falsifier), `paid-api/token-file` |
| AC3 | `paid-api/stop` (declared falsifier), `paid-api/every-init`, `paid-api/profile-login` |
| AC4 | `strip/read-back`, `strip/private-runtime-directory`, `strip/user-manager` |
| Fixtures | `fixture/planted-control`, `format/fake-lines` |

`baseline/qualified`: the engine started from the pinned copy with the qualified flags and then exactly
the baseline, every option one the binary declares, neither `--bare` nor `--safe-mode`; the generated
files as the engine read them; the two environment switches; the shipped record carrying the module's
baseline, every switch in the binary's table; a record without it refused before acceptance. Each
`baseline/planted-*` row reads the init event (output style, MCP servers, skills and slash commands,
memory paths) and the fake's debug log (settings files, instruction files, memory, hooks) of the normal
run, with items planted in the profile (settings with a style and a hook, a user server, the login's
connector, a user skill, a user CLAUDE.md, auto memory for the clone) and the clone (project and local
settings, a project server, a project skill, a project CLAUDE.md). `fixture/planted-control` starts the
same fake with the qualified flags alone in the same clone and profile: it loads every planted item, so
no row passes for an item that could not load. `paid-api/read-back`: none of the six planted names in the
plain account's engine, the token account's own token and no other, the receiver's report naming the
removed names and holding no value. `paid-api/token-file`: a 0644 token file refused by name, nothing
spawned. `paid-api/stop`: one contained run per login the initialize answer can name that is not a
subscription (23: each apiKeySource other than `none`, each backend but firstParty, each token source but
the account's own subscription token, an Anthropic profile, and the "Claude API" label), each stopped by name with the fake having
received the initialize request and nothing else (no prompt, no init, no turn), the invocation cancelled;
the subscription and token runs received the request first and then the dispatch packet as the prompt, and
complete; each of the four subscription labels, fed to the production Guard, confirms the login; a record without stream JSON input is refused before acceptance. `paid-api/every-init`: a run
confirmed on its login whose second init event names an API key is stopped by name before that turn, one
turn taken. `paid-api/profile-login`: a user_oauth profile under HOME, an oidc_federation one under
XDG_CONFIG_HOME, one under a relative XDG_CONFIG_HOME and a user_oauth one whose credentials_path is
relative (both reaching files in the clone), each refused by name before acceptance; started without the
guard in a clone, the fake takes each profile and reports `none`. `format/fake-lines` also checks the
initialize answer of the fake's own handshake control against the binary's control response and account
fields. `strip/read-back`:
the five names absent from the engine and reported removed. `strip/private-runtime-directory`: an empty
0700 directory of this account's, the one reported, not the receiver's, not the configuration directory
nor above it, another for the next run, both removed. `strip/user-manager`: the run in its own scope in
the run's slice, the scope's result read by systemctl, and no session bus in the engine.

Plain run: 43 passed (26 preamble, 17 rows) in about 9 seconds; under the gate's environment the same.

## Red record

`red-at-45ee21bb.json`: the current suite over `git archive 45ee21bb`, unchanged. All 15 behavior rows fail
by their own assertions (none raised): that tree qualifies no baseline and no stream JSON input, adds
nothing after the flags, has no token route, no handshake, no login guard and no profile check, and its
wrapper strips nothing and names no runtime directory. The two fixture rows are green there, as they must
be.

## Mutations (finding 155)

Registered in `scripts/check_teeth_mutations.py` with the `claude-` prefix, each declared falsifier first;
`drive.py` records `mutations.json` and one applied diff per mutant; `drive.py --survivors` records
`survivors.json`. `check_teeth_mutations.py --finding 155 --jobs 2`: all rejected.

| Mutant | Module | Named row |
|---|---|---|
| claude-baseline-sources-kept (AC1) | control_engine_claude.py | baseline/planted-settings |
| claude-baseline-strict-mcp-dropped (AC1) | control_engine_claude.py | baseline/planted-server |
| claude-baseline-slash-commands-kept (AC1) | control_engine_claude.py | baseline/planted-skill |
| claude-baseline-claude-mds-unset (AC1, planted row unreachable) | control_engine_claude.py | baseline/qualified |
| claude-baseline-hooks-kept (AC1, planted row unreachable) | control_engine_claude.py | baseline/qualified |
| claude-baseline-auto-memory-kept (AC1) | control_engine_claude.py | baseline/planted-memory |
| claude-paid-api-key-left (AC2 falsifier) | control_launch.py | paid-api/read-back |
| claude-paid-api-stop-skipped (AC3 falsifier) | control_engine_claude.py | paid-api/stop |
| claude-strip-agent-left (AC4) | control_launch.py | strip/read-back |
| claude-runtime-receivers (AC4) | control_launch.py | strip/private-runtime-directory |
| claude-runtime-config-directory (AC4) | control_launch.py | strip/private-runtime-directory |
| claude-strip-receiver-side (AC4) | control_launch.py | strip/user-manager |
| claude-profile-login-unchecked | control_engine_claude.py | paid-api/profile-login |
| claude-token-file-unchecked | control_launch.py | paid-api/token-file |
| claude-token-not-delivered | control_launch.py | paid-api/read-back |
| claude-baseline-unqualified-accepted | control_engine_claude.py | baseline/qualified |
| claude-prompt-before-login-check (AC3, the prompt sent before the check) | control_engine_claude.py | paid-api/stop |
| claude-backend-unchecked | control_engine_claude.py | paid-api/stop |
| claude-token-source-unchecked | control_engine_claude.py | paid-api/stop |
| claude-subscription-unchecked | control_engine_claude.py | paid-api/stop |
| claude-subscription-label-unchecked (the check of 2026-09-26: any label accepted, "Claude API" among them) | control_engine_claude.py | paid-api/stop |
| claude-input-protocol-unqualified-accepted | control_engine_claude.py | paid-api/stop |
| claude-stream-first-init-only | control_engine_claude.py | paid-api/every-init |
| claude-profile-relative-receiver-cwd | control_engine_claude.py | paid-api/profile-login |
| claude-engine-cwd-receivers | control_launch.py | paid-api/profile-login |

No row holds the single descriptor of the token file: between the binding and the spawn the receiver has
no seam a row can hold open without racing it, so the change is argued from the code (one open, fstat and
read on it, no second open by path), not falsified.

`claude-strip-receiver-side` applies the whole strip (the five names and the private runtime directory)
to the environment the receiver hands systemd-run instead of the one the wrapper execs: systemd-run then
names an empty runtime directory and cannot reach the user manager. Measured on this host, removing only
DBUS_SESSION_BUS_ADDRESS from the receiver's environment would not break it: `systemd-run --user --scope`
and `systemctl --user show` reach the manager through XDG_RUNTIME_DIR/systemd/private without the bus
variable. The literal reading of the falsifier ("strip the session bus") therefore cannot red the row;
what keeps the receiver's tools working is its runtime directory.
