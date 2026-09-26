# VELDO-0061 proof: the Codex adapter qualified on Linux

## The design as built

**The adapter is a registration.** `control_engine_codex.REGISTRATION` is the Codex adapter as the
launch receiver runs it: its six lifecycle operations (`accept`, `launch`, `observe`, `stop`, `exit`,
`artifacts`) each with the code that implements it, the flags of the qualified configuration
(`exec --json`, the prompt on stdin) and the environment the engine is pinned with
(`DISABLE_AUTOUPDATER=1`). A receiver configuration names a Codex adapter as `engine: codex`, the
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
engine module's `bind` (`Receiver._pin`): the configured executable must be an absolute path with no
link on the way to it, appear once in the argv followed by the recorded flags, be a regular executable
file inside an `@openai/codex` package of the recorded version at the recorded path, and have the
recorded digest. Otherwise the dispatch is refused by name (`invalid_input:engine_executable`,
`invalid_input:engine_flags`, `invalid_input:engine_link`, `unavailable_service:engine_executable`,
`invalid_input:engine_package`, `stale_subject:engine_version`, `stale_subject:engine_digest`,
`missing_evidence:engine_qualification`) and nothing is accepted, reserved or spawned. The package
manager's own `codex` (a link to a Node shim the next install replaces) is refused as a link. The engine
module's `ENVIRONMENT` is set in the engine environment last. This binary does not name
`DISABLE_AUTOUPDATER`; its upgrade is a new package installed over this one, and the version and digest
checks refuse what that install leaves.

**Terminal output is an artifact document, never a completion.** `control_engine_codex.Artifacts` is fed
every chunk the meter is fed. Each stdout line is kept as printed and checked against exec's events and
fields (`EVENTS`, `USAGE_FIELDS`, `ITEM_KINDS`); an item is read only for its `id` and `type`, the fields
the binary ties to exec's items, and is returned whole. The verdict is `result` only for a well-formed
stream whose last turn closed with `turn.completed` and a zero exit; otherwise `signal`, `deadline`,
`malformed_output`, `turn_failed`, `missing_result` or `nonzero_exit`, in that order. At the end
`Metering` keeps the document (the verdict, terminal record, thread, turns, items, malformed line
indices, termination, every line, the dispatch, invocation, account and pinned executable) in a private
file (0600 in a 0700 directory, beside the store unless the config names `artifacts`) and the receiver
reports its path, digest and verdict with the exit (`Launch.artifacts`). The invocation's final report
settles `completed` only when the verdict is `result`, and `Runner.wait` returns the worker slot as
completed only when the invocation's recorded outcome is `completed`: an exit code completes nothing.
`control_engine_codex.verify(document)` recomputes a document from its own lines. An engine module with
no decoder (Claude Code until VELDO-0060) is judged by its exit as before.

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

`scripts/suites/78_veldo_0061_codex_adapter.py`
(`python3 scripts/selftest.py --suite 78_veldo_0061_codex_adapter`). One temporary tree in the owner's
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
| AC1 | `lifecycle/registered`, `lifecycle/normal-run`, `lifecycle/actual-binary`, `pin/unexpected-launch` (declared falsifier), `pin/qualified-record` |
| AC2 | `artifacts/normal-exit`, `artifacts/missing-result` (declared falsifier), `artifacts/malformed-output`, `artifacts/missing-usage`, `artifacts/nonzero-and-signal` |
| AC3 | `stop/cooperative`, `stop/forced`, `stop/termination` (declared falsifier) |
| AC4 | `caps/boundaries`, `caps/refused-before-launch` (declared falsifier), `caps/stop-at-cap`, `caps/observed` |
| Fixtures | `format/codex-fake-lines` |

`lifecycle/*`: the installed registration enumerates exactly the six operations the criterion names,
its flags are the installed record's and every adapter's, and each operation is observed on the
qualified configuration (acceptance before running, one spawn whose recorded process is the engine that
printed, the usage line kept as a receipt, a requested stop recorded exited, the exit, the artifact
document). The normal run is accepted, running and exited under one dispatch, in its own clone at the
accepted commit, as the pinned vendor binary with `exec --json`, handed exactly the accepted source,
input and tool configuration, with its dispatch, acceptance digest, account profile and
`DISABLE_AUTOUPDATER=1` in its environment, and returns a private artifact document naming the pinned
executable's digest. The installed Codex 0.154.0 binary is launched through the same runner, receiver,
wrapper, scope and clone entrance, pinned by the installed record: it enters its own clone as the
recorded process inside the dispatch's scope, exits 0, prints byte for byte what the binary prints for
the same arguments, and its zero exit with no terminal record is malformed output, a failed invocation
and a slot returned failed. `pin/*`: a binary with one byte changed after qualification, a newer
package version, a link to the qualified binary, the package manager's `codex` link and an argv without
`--json` are each refused by name before acceptance, with zero spawns, no invocation and no engine; the
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
document naming it with no result. `caps/*`: the initial, retry and follow-on invocations are each
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

Plain run: 44 passed (26 preamble, 18 rows) in about 8 seconds. Stage environment run (`env -i`, the
stage's variables, TZ=UTC): 44 passed in 10 seconds.

## Red record

`red-at-b39a0fdc.json`: the current suite over `git archive b39a0fdc`, unchanged. All 17 behavior rows
fail by their own assertion: that tree has no registration or qualification record, binds no executable
(the changed, newer and linked binaries and the other flags each launch), sets no `DISABLE_AUTOUPDATER`,
returns no artifact document and completes an invocation, and its slot, on its exit code. The
`format/codex-fake-lines` row is green there, as it must be.

## Mutations (finding 61)

Registered in `scripts/check_teeth_mutations.py` with the `adapter-` prefix, each declared falsifier
first; `drive.py` records `mutations.json` and one applied diff per mutant. All 26 turn their named row
red by assertion; the baseline and the no-op copies are green.
`check_teeth_mutations.py --finding 61 --jobs 2`: 26 rejected.

| Mutant | Module | Named row |
|---|---|---|
| adapter-digest-unbound (AC1 falsifier) | control_engine_codex.py | pin/unexpected-launch |
| adapter-pin-skipped | control_launch.py | pin/unexpected-launch |
| adapter-version-unbound | control_engine_codex.py | pin/unexpected-launch |
| adapter-link-accepted | control_engine_codex.py | pin/unexpected-launch |
| adapter-flags-unbound | control_engine_codex.py | pin/unexpected-launch |
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
| adapter-qualification-not-scaffolded | init_scaffold.py | pin/qualified-record |

The other findings with mutations in the modules this changes still reject: see the History entry of
the specification for the counts of this build.
