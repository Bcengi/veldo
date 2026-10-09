# VELDO-0061 proof: the Codex adapter qualified on Linux

## Codex 0.162.0 qualified beside the 0.154.0 pin (2026-10-09)

The production pin and the global install stay 0.154.0. 0.162.0 is qualified beside it: its record,
tables, fixtures and fixes are in the tree, and moving the pin is one reviewed change (below). It is
**not** ready to pin yet: one owner decision is open and the live captures are not run.

### The 0.155 to 0.162 audit

No changelog ships in the package (`@openai/codex` and `@openai/codex-linux-x64` hold only a README),
so the audit is the two binaries side by side, offline: `--help`, `exec --help`, `exec resume --help`,
`sandbox --help`, `app-server --help`, `login --help`, `login status`, `features list` and
`debug models --bundled` under an empty temporary HOME and CODEX_HOME; their literal pools
(`strings -a -n 6`, and the extractors below); and what each binary prints on `exec --json` against a
loopback model endpoint with no login (`loopback_lines.py`, every other connection denied).

| Change in 0.162.0 | Veldo assumption | What was done |
|---|---|---|
| The usage-limit message prints its apostrophe as U+2019 (`You` U+2019 `ve`); its usage URL moved | `LIMIT_MESSAGE` with an ASCII apostrophe | Broke: an exhausted account would stay launchable. The Meter reads either apostrophe (`APOSTROPHES`); suite 75 reads all 44 messages of 0.162.0's error table |
| An exhausted quota now prints `Quota exceeded. Check your plan and billing details.` (was a retry-limit text) | `EXHAUSTED` | Already the `quota` window; seen on loopback |
| Exec event and payload shapes | `EVENTS`, `USAGE_FIELDS`, `ITEM_KINDS` | Unchanged: same eight events, payload fields and item kinds, in the bytes and on loopback (normal turn, usage limit, quota, request error) |
| Item literals: `command` (command item), `results` (web search), `result` beside `id`; `model` and `HighRiskCyberActivity` with no named owner | items read for `id` and `type` only | No break. Recorded in `codex-exec-0.162.0.json` (`unplaced` lists the last two; no fake prints them) |
| The binary keeps no exec struct names and no exec JSON source path; CollabTool is serialized as a quoted string | the extractors' anchors | Per-version anchors (`CODEX_ANCHORS`, `VERSIONS`, `QUOTED_CASE`); 0.154.0's tables are byte for byte unchanged |
| New credential table: `OPENAI_WORKLOAD_IDENTITY_CONTEXT`, `CODEX_GUARDIAN_DECISIONS_API_KEY` | `CREDENTIALS` | Both refused when an adapter configures them (the families strip them from the inherited environment already) |
| Bundled models: `gpt-6.1-sol`, `gpt-6-sol`, `gpt-6-luna` added, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.2` gone | `MODEL_TOOL_MODES` was 0.154.0's only, so a 0.162.0 record could not bind | Per version (`QUALIFIED_MODEL_TOOL_MODES`); a record binds only with its own version's table. `gpt-6.1-sol` is `code_mode_only` with the clock and asynchronous input, like `gpt-6-astra` |
| `gpt-6-sol`'s entry sets `default_service_tier: priority` ("2x speed, increased usage") | no role chooses a tier | Named stop `configuration_stop:codex_service_tier:<model>:<tier>`; `gpt-6.1-sol` sets none |
| Eleven features newly default on: `api_key_model_discovery`, `browser_annotation_api`, `daemon_auto_start`, `guardian_reuse_parent_compaction`, `in_app_voice`, `instant_interrupt`, `realtime_conversation`, `system_proxy_fallback`, `ultrafast_mode`, `worktrees`, `write_stdin_approval` | an unknown default-on feature stops every launch | All forced off, so 0.162.0 runs with 0.154.0's qualified feature set (among them a shared background server that outlives the run and its updater, git worktrees beside the clone, the faster tier). Suite 88 has a row each |
| Global `--no-daemon`; `daemon_auto_start` | the engine's processes stay in its scope | `exec` left no daemon on loopback, and `daemon_auto_start` is forced off. `--no-daemon` is not an exec option, so it is not added |
| `exec --cyber-access-program <standard\|daybreak_blue\|daybreak_red>` (also `exec resume`) | the argv is the record's flags exactly | No change: the receiver's argv check refuses any flag the record does not list; omitted means server defaults |
| `cli_auth_credentials_store`: still `file` by default, still `file`, `keyring`, `ephemeral`; a new encrypted secrets store (`codex_auth.age`, its key in the keyring) and new keyring guidance | the baseline forces `file`, so the login is the profile's `auth.json` | No break: VELDO-0156's baseline extraction passes on 0.162.0 (same options, keys, values and the eight `login status` messages). The write-back of a refreshed login is the live capture's to show |
| Auto-update: `check_for_update_on_startup` still named; new managed daemon updater (`codex app-server daemon update`) | FLAGS turn the startup check off | The flag is unchanged; the daemon updater runs only with the daemon, which is off |
| Code Mode now offers `list_mcp_resources`, `list_mcp_resource_templates` and `read_mcp_resource` with no MCP server selected | readers only with a selected server (owner, Telegram 29400/29401) | **Open owner decision**, below. Veldo refuses each such launch (`configuration_stop:codex_unexpected_tool`) |

### The open owner decision

Under 0.162.0 every Code Mode model (`gpt-6.1-sol` included) offers the three MCP resource readers even
when the role selects no MCP server. No 0.162.0 switch was found (the readers stay with every listed
feature off and with `tools.*` overrides). Veldo fails closed: such a launch is refused, so a 0.162.0
pin can run Code Mode roles only when they select an MCP server. With no server the readers have nothing
to read (their sources are configured MCP servers; the apps connectors are off). The two choices are to
keep refusing, or to amend the rule for Code Mode on 0.162.0 (the readers come with the runner, as `exec`
and `wait` do). A probe of the second choice in the working tree only (never committed) turned suites 87,
88 and 90 fully green on 0.162.0; the only rows left red were the ones that state the rule (86
`wire/no-server`, 89's `{exec, wait}` oracle).

### Selecting the binary

`VELDO_CODEX_BINARY` names a vendor executable (never `node_modules/.bin/codex`); unset, the installed
global binary is used. Suite 79 selects its record and tables through `qualification.py`; the VELDO-0127
suites through `proof/VELDO-0127/wire_fixture.py`, which reads the version from the vendor package and
serves that version's captures (0.162.0's in `proof/VELDO-0127/codex-0.162.0/`). The fake engines carry
the selection in their source: before that, a launch environment dropped the variable and suites 87 to
89 forwarded to 0.154.0 unnoticed.

    VELDO_CODEX_BINARY=/home/dmitry/.local/share/veldo-engines/codex-0.162.0/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex \
        python3 scripts/selftest.py --suite 79_veldo_0061_codex_adapter

### Evidence for 0.162.0

- `codex-qualification-0.162.0.json`: the production writer's record (`qualification(binary, catalog=True)`),
  package `@openai/codex` `0.162.0-linux-x64`, `vendor/x86_64-unknown-linux-musl/bin/codex`,
  `sha256:50ed828f357c655a3c82054d346cab8434f24901f14ec19b8267571bdd008b38`; flags, environment,
  baseline and terminal protocol identical to 0.154.0's.
- `codex-formats-0.162.0.json` (`extract_formats.py --codex-table`, reconciled with
  `codex-loopback-0.162.0.json`), `codex-exec-0.162.0.json` (`extract_items.py --output`).
- `proof/VELDO-0127/codex-0.162.0/`: features listing, bundled catalog, model-mode probe (loopback).

### Results (2026-10-09, `python3 scripts/selftest.py --suite <name>`, serial)

| Suite | 0.154.0 (installed) | 0.162.0 (`VELDO_CODEX_BINARY`) |
|---|---|---|
| 79_veldo_0061_codex_adapter | 51 passed | 51 passed |
| 86_veldo_0127_agent_configuration | 51 passed, 2 failed: `live/claude`, `live/codex` | 50 passed, 3 failed: the two `live/*`, `wire/no-server` |
| 87_veldo_0127_codex_delivery | 203 passed | 85 passed, 88 failed: all the reader refusal |
| 88_veldo_0127_feature_defaults | 62 passed | 27 passed, 35 failed: all the reader refusal |
| 89_veldo_0127_feature_listing | 37 passed | 26 passed, 11 failed: all the reader refusal |
| 90_veldo_0127_feature_profile | 28 passed | 27 passed, 1 failed: the reader refusal |

`live/*` is red on 0.154.0 because the live captures bind the digests of the five production modules
this change edits; they need the recapture below. Every other suite that loads a changed module ran on
0.154.0: green, except three failures that are identical at the base commit 273313ff (82_veldo_0165
and 82_veldo_0173: the host no longer has Claude Code 2.1.281; 101_veldo_0208: two sandbox rows) and
102_veldo_0210 `scratch/stop-during-fork-forwarded-to-child`, which also fails at the base (two of
three runs).

Falsifiers (`check_teeth_mutations.py`, confined): `account-codex-limit-apostrophe-ignored`,
`account-codex-0162-credentials-dropped`, `role127-default-0162-omitted-daemon_auto_start`,
`role127-default-0162-omitted-worktrees`, `role127-service-tier-unchecked`, the existing
`account-codex-limit-unobserved` and all 19 other mutants of suites 87 to 90: all rejected. Finding 61's
and the suite 86 mutants need the gate's unconfined leg (`/run/user/1000`), and suite 86's baseline is
red until the recapture.

### Moving the pin to 0.162.0 (one reviewed change, after the decision and the captures)

1. Upgrade the global install to 0.162.0 (the owner's act) and check the installed binary is the
   qualified one: `python3 -B proof/VELDO-0061/extract_items.py --check --codex <global vendor codex>
   --output proof/VELDO-0061/codex-exec-0.162.0.json` and the same `--check` of `extract_formats.py
   --codex-table` (both compare everything but the absolute path).
2. Copy `proof/VELDO-0061/codex-qualification-0.162.0.json` over `engine/runtime/codex-qualification.json`
   and `.veldo/runtime/codex-qualification.json` (suite 79 requires the three identical).
3. Recapture the VELDO-0127 live evidence on the new pin (below), then run the gate.

### Live captures for the owner's assistant (not run here)

Nothing here ran against a real login. After the login write-back fix lands:

1. Now, on the 0.154.0 pin: the VELDO-0127 live evidence must be recaptured because this change edits
   the production modules it is bound to (`control_engine_codex.py`, `control_agent_config_handoff.py`),
   for both engines, with the models the current captures used. The driver's `--claude` is the pinned Claude Code 2.1.281, which is no longer under
   `~/.local/share/claude/versions` on this host (2.1.286 to 2.1.295 are).

```bash
python3 proof/VELDO-0127/live.py \
  --claude /home/dmitry/.local/share/claude/versions/2.1.281 \
  --codex /home/dmitry/.nvm/versions/node/v22.22.0/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex \
  --claude-profile /home/dmitry/.claude --codex-profile /home/dmitry/.codex \
  --claude-model claude-haiku-4-5-20251001 --codex-model gpt-6-astra \
  > /run/user/1000/veldo-0127-0.154.0-live.log 2>&1
```

2. At the pin move (after step 2 above): the 0.162.0 capture with `gpt-6.1-sol`. Its roles select the
   `jira` MCP server, so the open reader decision does not stop them. The resolver checks the private
   vendor binary against the reviewed record:

```bash
codex_vendor=$(python3 - <<'PYCODEX'
import hashlib, json
from pathlib import Path
record = json.loads(Path('proof/VELDO-0061/codex-qualification-0.162.0.json').read_text())
package = Path('/home/dmitry/.local/share/veldo-engines/codex-0.162.0/node_modules')
matches = [p for p in package.rglob('codex')
           if p.is_file() and not p.is_symlink()
           and p.as_posix().endswith('/' + record['executable'])]
assert len(matches) == 1, matches
binary = matches[0]
assert 'sha256:' + hashlib.sha256(binary.read_bytes()).hexdigest() == record['sha256']
print(binary)
PYCODEX
)
test -n "$codex_vendor" || exit 1
python3 proof/VELDO-0127/live.py \
  --claude /home/dmitry/.local/share/claude/versions/2.1.281 \
  --codex "$codex_vendor" \
  --claude-profile /home/dmitry/.claude \
  --codex-profile /home/dmitry/.codex \
  --claude-model claude-haiku-4-5-20251001 \
  --codex-model gpt-6.1-sol --only codex \
  > /run/user/1000/veldo-0127-codex-0.162.0-live.log 2>&1
```

   The capture is judged against the pinned record's digest, so it is evidence only once the pin is
   0.162.0. What it shows that loopback cannot: the real model's stream (items beyond `agent_message`,
   whether `model` or `HighRiskCyberActivity` ever appear on a line), the usage-limit line from the
   real backend, and that the file login is read and written back to `auth.json` under the new
   keyring guidance.
3. The 0061 bundle has no subscription-capture driver; none was added.


Built on branch build-veldo-0061, then integrated with VELDO-0060 on build-veldo-0060-0061, where both
engine modules were put on one engine protocol and both reviews' filed items were done. This README
describes the integrated tree.

**One engine protocol.** `control_launch.ENGINE_PROTOCOL` is what every subscription engine module
implements with the same signatures: `Refused`, `bind(adapter, state_root)`, `command(binding, adapter)`,
`environment(binding)`, `Terminal()` (`feed`, `close`, `document(termination, cause)`), `Meter` and
`REGISTRATION`. The receiver drives Codex and Claude Code through the one path `Receiver._bind`: the bind
before acceptance, the engine's own argv composition (this one's: the adapter's argv exactly, nothing
appended), one argv check for every engine, and the engine's settings set last. `Unbound` became
`Refused`, `Artifacts` became `Terminal`, and the document's completion verdict is `complete` (was
`result`), in the one document shape `veldo.engine_artifact/v1` both engines return.

## The design as built

**The adapter is a registration.** `control_engine_codex.REGISTRATION` is the Codex adapter as the
launch receiver runs it: its six lifecycle operations (`accept`, `launch`, `observe`, `stop`, `exit`,
`artifacts`) each with the code that implements it, the flags of the qualified configuration
(`exec --json -c check_for_update_on_startup=false`, the prompt on stdin: the config override turns the
binary's own startup update check off, a key the binary names) and the environment the engine is pinned
with (`DISABLE_AUTOUPDATER=1`, which this binary does not read). A receiver configuration names a Codex adapter as `engine: codex`, the
`executable` it launches and its `argv` (the clone entrance, then that executable and its flags).

**The executable is pinned before acceptance.** `control_engine_codex.qualification(executable)` writes
the record of one installed vendor binary from its package manifest and its bytes, never running it:
package `@openai/codex`, package version `0.154.0-linux-x64`, version `0.154.0`, the package-relative path
`vendor/x86_64-unknown-linux-musl/bin/codex`, its digest, the flags, the terminal protocol (the eight exec
events, `turn.completed` as the terminal record, `turn.failed`, the item kinds), the subscription login
(`CODEX_HOME`), the usage units (invocations, wall seconds, tokens, messages) and the windows Codex
reports (`usage_limit`, `workspace_credits`, `workspace_spend_cap`, `quota`, `plan`). That record is
`engine/runtime/codex-qualification.json`, installed at `.veldo/runtime/codex-qualification.json` by
init (`_RUNTIME_ASSETS`), beside the module that reads it. Before acceptance the receiver calls the
engine module's `bind` (`Receiver._bind`): the configured executable must be an absolute path with no
link on the way to it, be a regular executable file inside an `@openai/codex` package of the recorded
version at the recorded path, and have the recorded digest. The receiver's own argv check, the same for
both engines (`control_launch.pinned_argv_problem`), then requires the executable to be what runs: the
first argument after the installed clone entrance's `--` (or, with no entrance, the first argument the
wrapper execs), followed by the recorded flags; a shell or the package manager's link standing first is
refused. Otherwise the dispatch is refused by name (`invalid_input:engine_executable`,
`invalid_input:engine_flags`, `invalid_input:engine_link`, `unavailable_service:engine_executable`,
`invalid_input:engine_package`, `stale_subject:engine_version`, `stale_subject:engine_digest`,
`missing_evidence:engine_qualification`) and nothing is accepted, reserved or spawned. The package
manager's own `codex` (a link to a Node shim the next install replaces) is refused as a link. The engine
module's `environment` is set in the engine environment last. This binary does not name
`DISABLE_AUTOUPDATER`, so its startup update check is turned off by the flag above; its upgrade is a new
package installed over this one, and the version and digest checks refuse what that install leaves. The
engine's environment also names the pinned path and digest (`VELDO_ENGINE_PATH`, `VELDO_ENGINE_SHA256`):
the clone entrance, which execs the engine, re-hashes the file immediately before the exec and refuses a
changed one (exit 70), and passes neither name on. Clones may write-protect the engine packages
(`Clones(engines=...)`), which VELDO-0060's suite drives for this engine too.

**Terminal output is an artifact document, never a completion.** `control_engine_codex.Terminal` is fed
every chunk the meter is fed. Each stdout line is kept as printed and checked against exec's events and
fields (`EVENTS`, `USAGE_FIELDS`, `ITEM_KINDS`); an item is read only for its `id` and `type`, the fields
the binary ties to exec's items, and is returned whole. The verdict is `complete` only for a well-formed
stream whose last turn closed with `turn.completed` and a zero exit, when nothing stopped it; otherwise
`stopped` (its `cause`: a stop on request, at the usage cap or for a missed heartbeat, whatever it printed
and however it exited, as Claude Code's is), `signal`, `deadline`, `malformed_output`, `turn_failed`,
`missing_result` or `nonzero_exit`, in that order. At the end
`Metering` keeps the document (the verdict, terminal record, thread, turns, items, malformed line
indices, termination, stop cause, every line, the dispatch, invocation, account and pinned executable) in a private
file (0600 in a 0700 directory, beside the store unless the config names `artifacts`) and the receiver
sends its report {path, digest, verdict, complete} before the end (`Launch.artifact`). The invocation's
final report settles `completed` only when the document is complete; the exit record binds the report's
verdict, completeness and digest, and `control_dispatch.completed` (the one completion gate, which the
runner's worker slot and the build and review floor both read) is true only when that artifact is
complete: an exit code completes nothing. `control_engine_codex.verify(document)` recomputes a document
from its own lines and cause. A module that lacks one of the protocol's names is refused
`unregistered_adapter:engine_protocol:<engine>:<name>` before acceptance, nothing spawned.

**Stop and caps are the machinery VELDO-0039 to 0041 and 0062 built, on this configuration.** A stop is
`Launch.stop`: SIGTERM to the engine, SIGTERM to its group after the stop grace, cgroup.kill after the kill
grace, and the exit recorded only once the group is empty; the stopped invocation settles `cancelled`
with its unknown usage retained. Every invocation (initial, retry, follow-on) is reserved against every
cap and the account's reported windows before its spawn, and a report that reaches a cap stops the
worker.

Out of this build: the everything-off baseline, the paid-API guard and the environment strip
(VELDO-0156); the role's own selections (VELDO-0127); separating the login from the worker's tools
(Release 2, owner Telegram 29163); the Mac (VELDO-0147); wiring the clone into the production launch
path (VELDO-0129; the suite composes it); the live model run on the owner's registered subscription,
which this build never makes (the installed binary runs through the whole lifecycle with `--help`).
`fleet.py` is unchanged: it runs Claude Code sessions only.

## Where each format comes from

Every line a fake engine prints is built in a shape the installed binary declares, and the format row
checks each against the tables, so the fakes cannot drift into matching only our reader:

- the exec events and their payloads, the usage-limit message forms: VELDO-0062's
  `proof/VELDO-0062/cli-formats.json`, unchanged;
- the items: `codex-exec.json`, written by `extract_items.py` from the Codex 0.154.0 vendor binary's bytes
  (digest in the table). It reads exec's literal runs: the ThreadItem kinds (`agent_message`,
  `reasoning`, `command_execution`, `file_change`, `mcp_tool_call`, `web_search`, `todo_list`,
  `collab_tool_call`, and `error`), the long field names only exec's items use (`aggregated_output`,
  `exit_code`, `changes`, `server`, `arguments`, `result`, `query`, `action`, `items`, `receiver_thread_ids`,
  `prompt`, `agents_states`, `message`, `id`) and the status and change-kind values. Short names such as
  `text`, `tool`, `path`, `kind` and `command` are merged with the same text elsewhere in the binary and
  cannot be tied to exec, so they are listed as `unbound` and no fake prints them.
  `python3 -B proof/VELDO-0061/extract_items.py --check` exits 1 when the installed binary moved.

Nothing was executed to make either table. The only runs of the real binary are `codex exec --json
--help` with a fixture `CODEX_HOME`: no model runs, nothing logs in, and `~/.codex` is never read.

## Suite

`scripts/suites/79_veldo_0061_codex_adapter.py`
(`python3 scripts/selftest.py --suite 79_veldo_0061_codex_adapter`; renumbered from 78, which VELDO-0060's
suite also had). One temporary tree in the owner's
runtime directory holds the installed `.veldo` copy with its qualification record, which the suite loads
and the receiver, wrapper and clone entrance execute. Real: a SQLite control store with OpenSSH journal
signatures, Codex account records registered by the owner over profiles `accounts.py` prepares, VELDO-0036
reservations, VELDO-0052's Gate, VELDO-0031 claims, a Git source bound in the store, a VELDO-0042 clone per
dispatch entered through its Landlock entrance, the VELDO-0039 Runner and receiver processes, VELDO-0040
transient scopes under the owner's systemd user manager in a slice of the run's own (stopped at the end;
no unit is installed) and the kernel's cgroup, pidfd and /proc files. The engine is the installed vendor
binary (help only) or a fake Codex laid out as a vendor package and qualified by the production writer.
The profile's `systemd_run` is a shim that records each spawn by its dispatch before it becomes the real
systemd-run, so a spawn for a refused invocation is seen. Each row is reported once.

| Criterion | Rows |
|---|---|
| AC1 | `lifecycle/registered`, `lifecycle/normal-run`, `lifecycle/actual-binary`, `lifecycle/engine-protocol`, `pin/unexpected-launch` (declared falsifier), `pin/qualified-record` |
| AC2 | `artifacts/normal-exit`, `artifacts/missing-result` (declared falsifier), `artifacts/malformed-output`, `artifacts/missing-usage`, `artifacts/nonzero-and-signal` |
| AC3 | `stop/cooperative`, `stop/forced`, `stop/termination` (declared falsifier), `stop/stopped-not-complete` |
| AC4 | `caps/boundaries`, `caps/refused-before-launch` (declared falsifier), `caps/stop-at-cap`, `caps/observed` |
| Fixtures | `format/codex-fake-lines` |

`lifecycle/*`: the installed registration enumerates exactly the six operations the criterion names,
its flags are the installed record's and every adapter's and turn the binary's startup update check off
(a config key the installed binary names), and each operation is observed on the
qualified configuration (acceptance before running, one spawn whose recorded process is the engine that
printed, the usage line kept as a receipt, a requested stop recorded exited, the exit, the artifact
document). The normal run is accepted, running and exited under one dispatch, in its own clone at the
accepted commit, as the pinned vendor binary with `exec --json`, handed exactly the accepted source,
input and tool configuration, with its dispatch, acceptance digest, account profile and
`DISABLE_AUTOUPDATER=1` in its environment and neither re-hash name, and returns a private artifact document naming the pinned
executable's digest. The installed Codex 0.154.0 binary is launched through the same runner, receiver,
wrapper, scope and clone entrance, pinned by the installed record: it enters its own clone as the
recorded process inside the dispatch's scope, exits 0, prints byte for byte what the binary prints for
the same arguments, and its zero exit with no terminal record is malformed output, a failed invocation
and a slot returned failed. `lifecycle/engine-protocol`: both installed engine modules implement all ten
protocol names, and a receiver installed with a Codex module lacking `REGISTRATION`, or `Terminal`, refuses
the dispatch `unregistered_adapter:engine_protocol:codex:<name>` before acceptance, with zero spawns, no
invocation and no engine. `pin/*`: a binary with one byte changed after qualification, a newer
package version, a link to the qualified binary, the package manager's `codex` link, an argv without
`--json`, the pinned binary behind a shell and behind a link to it are each refused by name before
acceptance, with zero spawns, no invocation and no engine; the
qualified binary launches once. The installed record is what the production writer makes of the
installed binary now, it carries the digest both extracted tables read, and init lays it down from an
identical engine copy. `artifacts/*`: the normal stream is a result (its thread, turn and items as
printed), settled and returned completed, and its document verifies while one with a changed verdict
does not; the same stream with its terminal record removed exits 0 as `missing_result`, the invocation
failed, the slot returned failed and its tokens and messages unknown and retained; a line that is not
JSON and an event exec never prints are both named `malformed_output`; a completion with its usage left
out is a result whose tokens stay unknown, never zero; a failed turn exiting 1, a nonzero exit after a
completed turn and a SIGKILL mid-turn are `turn_failed`, `nonzero_exit` and `signal`, each failed.
`stop/*`: a cooperative engine and descendant end on the request with no kill step; an engine and
descendant that ignore it are killed with their group after the configured graces (0.4 s each), within
their bound; an engine that leaves a descendant ignoring the request is recorded exited only after that
descendant was killed. In each, every process is gone, the exit recorded is the engine's own under its
process identity, and the original invocation is cancelled, its usage unknown and retained, its
document naming it, `stopped`, never complete. `stop/stopped-not-complete`: an engine that answers the
request with `turn.completed` and exits 0 is `stopped`, not complete, in its document (which verifies) and
in its exit record; the completion gate reads it as not complete, its invocation and slot are cancelled,
and the floor refuses the build `missing_evidence:build_dispatch`, while a unit whose one build completed
passes the floor's dispatch check and is refused next for its absent proof. `caps/*`: the initial, retry and follow-on invocations are each
reserved before the running record and ran the pinned binary; a fourth invocation of a unit capped at
three, a retry under a token cap whose earlier usage is unknown and a launch on an account whose Codex
usage limit was reported are each refused by name with zero spawns (the account carries the rejected
`usage_limit` window with no reset, from the invocation that saw it); the report that reached a
1000-token cap stopped the worker before its next turn, and its document is the output up to the stop,
not a completion; each invocation's count, wall time, tokens and messages are those of the stream the
adapter returned, and the unit's balance is their sum. `format/*`: every one of the fakes' JSON lines is
a declared event whose item is a declared kind with only exec's own fields, the fakes print every event
the adapter reads, the usage-limit message is one of the binary's forms, and the item table matches the
installed binary. It checks the fixtures, not production, so it is green at the pre-change commit too.

Plain run: 46 passed (26 preamble, 20 rows) in about 9 seconds. Stage environment run (`env -i`, the
stage's variables, TZ=UTC): 46 passed in 12 seconds.

## Red record

`red-at-b39a0fdc.json`: the current suite over `git archive b39a0fdc`, unchanged. All 19 behavior rows
fail by their own assertion: that tree has no registration or qualification record, binds no executable
(the changed, newer and linked binaries and the other flags each launch), sets no `DISABLE_AUTOUPDATER`,
returns no artifact document and completes an invocation, and its slot, on its exit code. The
`format/codex-fake-lines` row is green there, as it must be.

## Mutations (finding 61)

Registered in `scripts/check_teeth_mutations.py` with the `adapter-` prefix, each declared falsifier
first; `drive.py` records `mutations.json` and one applied diff per mutant. All 30 turn their named row
red by assertion; the baseline and the no-op copies are green.
`check_teeth_mutations.py --finding 61 --jobs 2`: 30 rejected.

| Mutant | Module | Named row |
|---|---|---|
| adapter-digest-unbound (AC1 falsifier) | control_engine_codex.py | pin/unexpected-launch |
| adapter-pin-skipped | control_launch.py | pin/unexpected-launch |
| adapter-version-unbound | control_engine_codex.py | pin/unexpected-launch |
| adapter-link-accepted | control_engine_codex.py | pin/unexpected-launch |
| adapter-flags-unbound | control_launch.py | pin/unexpected-launch |
| adapter-autoupdater-unset | control_engine_codex.py | lifecycle/normal-run |
| adapter-engine-environment-ignored | control_launch.py | lifecycle/normal-run |
| adapter-stop-unregistered | control_engine_codex.py | lifecycle/registered |
| adapter-artifacts-unreported | control_launch.py | lifecycle/normal-run |
| adapter-missing-result-accepted (AC2 falsifier) | control_engine_codex.py | artifacts/missing-result |
| adapter-exit-code-completes | control_launch.py | artifacts/missing-result |
| adapter-runner-exit-completes | control_launch.py | artifacts/missing-result |
| adapter-malformed-accepted | control_engine_codex.py | artifacts/malformed-output |
| adapter-undeclared-event-accepted | control_engine_codex.py | artifacts/malformed-output |
| adapter-missing-usage-zero | control_engine_codex.py | artifacts/missing-usage |
| adapter-failed-turn-unnamed | control_engine_codex.py | artifacts/nonzero-and-signal |
| adapter-signal-unnamed | control_engine_codex.py | artifacts/nonzero-and-signal |
| adapter-nonzero-exit-result | control_engine_codex.py | artifacts/nonzero-and-signal |
| adapter-artifacts-unverified | control_engine_codex.py | artifacts/normal-exit |
| adapter-stop-leaves-descendant (AC3 falsifier) | control_launch.py | stop/termination |
| adapter-stop-graces-ignored | control_launch.py | stop/forced |
| adapter-stop-outcome-lost | control_launch.py | stop/cooperative |
| adapter-cap-checked-after-launch (AC4 falsifier) | control_launch.py | caps/refused-before-launch |
| adapter-cap-stop-ignored | control_launch.py | caps/stop-at-cap |
| adapter-window-unchecked | control_reservations.py | caps/refused-before-launch |
| adapter-argv-position-unchecked | control_launch.py | pin/unexpected-launch |
| adapter-update-check-left-on | control_engine_codex.py | pin/qualified-record |
| adapter-qualification-not-scaffolded | init_scaffold.py | pin/qualified-record |
| adapter-stop-cause-ignored | control_engine_codex.py | stop/stopped-not-complete |
| adapter-engine-protocol-unchecked | control_launch.py | lifecycle/engine-protocol |

The other findings with mutations in the modules this changes still reject: 60 (35), 62 (50, over its
suite with the fake Codex and the fake Claude Code both pinned), 39 (30), 40 (22), 41 (34), 42 (21) and
45 (23). Suites run plain, all green: `79_veldo_0061_codex_adapter`, `78_veldo_0060_claude_adapter` (whose
contained rows run this adapter on the local Linux contained launch too), `75_veldo_0062_accounts` and
every suite that loads a module this changes (48 of them), `50_git_environment` and
`24_veldo_0007_install_and_run`; under the stage environment, all green: this one and the VELDO-0060,
0062, 0039, 0040, 0041 and 0042 suites.

After the integration fixes (which change `control_launch.py` and `control_engine_codex.py` only), the
final commit was run again, all green: plain, the 14 suites that load either module, `50_git_environment`
and `24_veldo_0007_install_and_run`; under the stage environment, the VELDO-0060, 0061, 0062, 0039,
0040, 0041 and 0042 suites.
