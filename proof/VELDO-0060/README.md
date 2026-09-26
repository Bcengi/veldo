# VELDO-0060 proof: the Claude Code adapter, from its pinned executable, returning validated artifacts

Built on branch build-veldo-0060, then integrated with VELDO-0061 on build-veldo-0060-0061, where the
review's two blockers were fixed and the filed hardening of both reviews was done. This README describes
the integrated tree.

## The design as built

**One engine protocol.** `control_launch.ENGINE_PROTOCOL` is what every subscription engine module
implements with the same signatures: `Refused` (a named refusal), `bind(adapter, state_root)` (the pinned
executable, checked before acceptance), `command(binding, adapter)` (the engine argv),
`environment(binding)` (the settings the engine always runs with), `Terminal()` (the terminal output
decoder, `feed`, `close`, `document(termination, cause)`), `Meter` (VELDO-0062) and `REGISTRATION` (the
lifecycle operations). `control_engine_claude` and `control_engine_codex` both implement it, and the
receiver drives every engine through one path, `Receiver._bind`, after the login check: the bind (a
`Refused` is the dispatch's refusal, nothing accepted, reserved or spawned), the engine's own command, the
one argv check below, and the engine's settings set last in its environment, an adapter configuring one
of them otherwise refused by name (`invalid_input:adapter_environment:DISABLE_AUTOUPDATER`). An engine
module missing any protocol name is refused before acceptance
(`unregistered_adapter:engine_protocol:<engine>:<name>`).

**The pinned executable.** A Claude Code adapter names the version it runs (`executable: {version}`),
never a path, and the receiver config names the factory state root (`state_root`). The qualification
record `engine/runtime/claude-qualification.json` (installed at `.veldo/runtime/`, laid by the scaffold
beside `control_engine_claude.py`) lists 2.1.281 with its digest, the flags of print mode with stream JSON
output (`--print --output-format stream-json --verbose`), `DISABLE_AUTOUPDATER=1`, its terminal protocol,
its subscription login, its usage units and its six rate-limit windows, every value the binary's own
(below). `pin` copies the installer's versioned file (`~/.local/share/claude/versions/<version>`) to
`<state root>/engines/claude_code/<version>` as a new 0555 regular file and refuses a linked source, an
unqualified version or a copy of another digest, leaving nothing in place. `bind` refuses by name an
unqualified version (`invalid_input:engine_version:<v>`), no state root
(`missing_authority:engine_state_root`), a missing copy (`missing_evidence:engine_executable`), a link or
a file that is not regular (`binding_mismatch:engine_executable`), a linked directory on the way to it
(`binding_mismatch:engine_path`), a copy that is not this account's own
(`binding_mismatch:engine_owner`), one that is writable or carries a setuid, setgid or sticky bit
(`binding_mismatch:engine_mode`) and one of another digest (`binding_mismatch:engine_digest`). The
auto-updating `~/.local/bin/claude` link is never read. `command` is the adapter's prefix (its clone
entrance, or a transport's trusted wrapper) followed by the pinned path and the qualified flags.

**The pin binds what runs.** For every engine the receiver checks (`pinned_argv_problem`) that what the
trusted wrapper will exec (a local adapter's whole argv; a reported adapter's argv after its transport's
`control_launch.py exec`) is the pinned path itself, or the installed clone entrance
(`<python> -B control_clone.py enter <clones> --`, beside the receiver for a local adapter) followed by the
pinned path, and that the qualified flags follow it. The pinned path somewhere in the argv is not enough:
a shell or a package manager's link before it is refused `invalid_input:engine_executable`. The engine's
environment names the pinned path and digest (`VELDO_ENGINE_PATH`, `VELDO_ENGINE_SHA256`); whichever
trusted program execs the engine (the wrapper, when no entrance stands before it, or the clone entrance)
re-hashes the file immediately before the exec, refuses a changed one (exit 70, the engine never runs)
and passes neither name to the engine. The clone provisioner takes `engines`, directories every clone's
users may read and execute but never write (`Clones(engines=...)`, recorded in the manifest's protected
write targets): the pinned copies' directory and the engine packages, so no worker replaces what the
next dispatch runs.

**The lifecycle.** `control_engine_claude.REGISTRATION['lifecycle']` is the adapter's registration: accept
(`Receiver.launch`: bound, then the acceptance recorded before the spawn), launch (`Receiver._spawn`, the
pinned command in the dispatch's wrapper), observe (`Meter.feed` and `Terminal.feed`), stop
(`Launch.stop`), exit (`Receiver._reap`) and artifacts (`Terminal.document`, the exit record's artifact).
The input binding is the dispatch packet on standard input, the prompt of print mode; the source binding
is the VELDO-0042 clone at the accepted commit; the tool bindings are the recorded configuration, handed
through unchanged (their flags are VELDO-0127's).

**The artifact and completion.** `Terminal` decodes the stream the Meter reads. Its document, one shape
for every engine (`veldo.engine_artifact/v1`: schema, engine, verdict, complete, then this engine's
problems, the decoded `result` with its subtype, error flag, turns, session, stop reason, result digest,
errors and tokens, the digest of the line it came from, and the stream's counts), is bound to the
dispatch, invocation, account and pinned executable and kept 0600 in a 0700 directory (the config's
`artifacts`, else beside the store). The verdict is `complete` only for a zero exit with no signal, stop
or deadline, a stream of well-formed events and a `success` result that is not an error; otherwise it
names the first of `stopped`, `timeout`, `signal`, `nonzero_exit`, `malformed_output`, `missing_result`
and `engine_error`. The terminal record's tokens are the result's `modelUsage` total over every model;
without a readable `modelUsage` they are unknown (`None`), never the result's `usage`, which is the main
agent loop's alone. The receiver sends the report {path, digest, verdict, complete} to the runner before
the end (`Launch.artifact`), settles the invocation `completed` only when it is complete, and the exit
record binds the report's verdict, completeness and digest (`control_dispatch`'s exit transition,
`artifact`). `control_dispatch.completed(record)` is the one completion gate: an exited record, exit 0,
no signal, no deadline stop and, when it binds an artifact, a complete one. The runner's worker slot
(`Runner.wait`) and the floor's build and review checks (`dispatch._clean_exit`) both read it, so a zero
exit without its terminal record is never a completed build.

**Stop and caps** are the existing machinery on this configuration. On the local contained launch the
stop is VELDO-0040's and 0041's: SIGTERM to the engine, SIGTERM to its group after the stop grace,
cgroup.kill after the kill grace, and the exit recorded only once the group is empty; on the reported
path the worker's session is killed and the dispatch recorded unknown, since that path cannot confirm the
far engine ended. Every initial, retry and follow-on invocation is checked and reserved against its caps
and the account's windows before the spawn (VELDO-0062), and a reached cap stops the worker.

Out of this build: the everything-off baseline, the paid-API guard and the environment strip
(VELDO-0155); the role's own selections (VELDO-0127); the Mac leg (VELDO-0147); separating the login from
the worker's tools (Release 2); and the live run of the real CLI on the owner's subscription, which the
build's rules forbid (no model runs, nothing logs in). `live_usage` in the qualification record is
therefore `null`.

## Where each format comes from

The fake engine is built from the installed 2.1.281 binary's own tables, never from our reader (the
VELDO-0062 lesson). `extract_cli.py` reads the binary's bytes and nothing else (nothing is executed, no
model runs, nothing logs in, no profile or credential file is opened) and writes `cli-options.json`: the
96 option names of the main `claude` command (the commander chain from `.name("claude")` to its
`.action(`), each with its flags, whether it takes a value and its declared choices (`--output-format`:
text, json, stream-json), the check print mode makes (`Error: When using --print,
--output-format=stream-json requires --verbose`) and the updater switch the binary reads
(`DISABLE_AUTOUPDATER`). `python3 -B proof/VELDO-0060/extract_cli.py --check` compares it with a fresh
extraction and exits 1 when a CLI update moved anything. The stream formats are VELDO-0062's
`cli-formats.json`, unchanged. Both tables carry the binary's digest
(`sha256:56fe3da8...a6dce1`), which is the shipped qualification record's.

## Suite

`scripts/suites/78_veldo_0060_claude_adapter.py`
(`python3 scripts/selftest.py --suite 78_veldo_0060_claude_adapter`). One temporary tree in the owner's
runtime directory (so the clone's protected targets are not beneath a temporary directory) holds the
installed `.veldo` copy the suite loads and the receiver, wrapper and clone entrance execute. Real: a
SQLite control store with OpenSSH journal signatures, three account records the owner registers over
profiles the helper prepares (two Claude Code, one Codex), VELDO-0036 reservations under their production
authorization, VELDO-0052's Gate, VELDO-0031 claims, a Git source bound to the store, VELDO-0042 clones
confined with Landlock, the VELDO-0039 Runner and receiver processes and the trusted wrapper, VELDO-0040
transient scopes under the owner's systemd user manager in a slice of the run's own (stopped, and its
failed units cleared, at the end; no unit is installed) and VELDO-0049's FloorAuthority over the same
store. The engine is a fake `claude` written into a versions directory of the installer's shape as
2.1.281 and copied by the production `pin` under the state root; the same fake laid out as a Codex
vendor package and qualified by `control_engine_codex.qualification` is the Codex engine of the
contained rows. It records its argv, environment, working directory, cgroup, process identity and the
invocation record the store holds at its start, then prints what its packet scripts: stream lines,
perturbed bytes, a sleep, a descendant (cooperative, ignoring SIGTERM, or leaving its session, each
saying when its signal disposition is set), a write probe, SIGTERM ignored, or a signal to itself. The
contained profile's `systemd_run` is a shim that records each spawn by its dispatch and, for a unit a
request file names, changes the bound executable after its bind and before its exec. Each row is
reported once.

| Criterion | Rows |
|---|---|
| AC1 | `lifecycle/registration`, `lifecycle/pinned-launch`, `pin/unexpected-launch` (declared falsifier), `pin/copy`, `pin/shipped-qualification`, `pin/argv-binds-what-runs`, `pin/rehash-before-exec`, `contained/bind`, `contained/scope`, `contained/clone-entry`, `contained/pinned-exec`, `contained/engines-protected`, `contained/rehash-before-exec` |
| AC2 | `artifact/complete`, `artifact/missing-result` (declared falsifier), `artifact/exits`, `artifact/malformed-output`, `artifact/missing-usage`, `artifact/exit-record`, `floor/missing-result`, `contained/artifact`, `contained/exit-record` |
| AC3 | `stop/requested`, `stop/descendant-alive`, `contained/stop-cooperative`, `contained/stop-forced`, `contained/stop-descendant` (declared falsifier) |
| AC4 | `caps/before-launch` (declared falsifier), `caps/allowance-states`, `caps/stop-at-cap` |
| Fixtures | `format/fake-lines`, `format/fake-argv` |

`lifecycle/*`: the registration lists exactly accept, launch, observe, stop, exit and artifacts, each
observed on the runs; the engine ran once from the pinned copy (a regular file of the qualified digest,
not the installer's file, not a link) with exactly the qualified flags, `DISABLE_AUTOUPDATER=1` and the
recorded account's profile, in its isolated clone at the accepted commit. `pin/unexpected-launch`: the
pinned copy's bytes changed, an unknown version, the pinned path a link to the qualified bytes, a missing
copy, no state root, a copy its owner can write, a state root reached through a link and an adapter
configuring the updater on are each refused by name with nothing spawned or reserved; the restored copy
launches again, and the copy the launches ran is this account's own, 0555. `pin/copy`,
`pin/shipped-qualification`: as built on build-veldo-0060 (the production pin's copy; the shipped record
against the binary's own tables). `pin/argv-binds-what-runs`: the pinned path in the argv behind a shell
(no entrance, after the entrance, after a transport's wrapper) and, for Codex, behind a shell after the
entrance or behind a package manager's link, each refused `invalid_input:engine_executable` with nothing
run. `pin/rehash-before-exec` (the wrapper) and `contained/rehash-before-exec` (the clone entrance, both
engines): the bound executable changed after its bind and before its exec is refused at the exec, exit
70, the engine never ran, the artifact is not complete, the invocation and slot failed. `artifact/*`:
the live exits and perturbed bytes of build-veldo-0060, plus the terminal record's tokens (the
`modelUsage` total for a complete run, unknown for a result without `modelUsage`, which still carries
its main-loop `usage`); `artifact/exit-record`: the exit record binds the verdict, completeness and
digest of the artifact the runner was given, and the completion gate reads it (complete for the normal
run, not complete for the zero exit without its result); `floor/missing-result`: the floor refuses to
accept the build whose dispatch exited 0 without its terminal record (`missing_evidence:build_dispatch`),
while the complete run's build passes that check and is refused next for its absent proof.
`contained/*`, each for Claude Code and for Codex: bound before acceptance and launched once (an unknown
version, a changed Codex binary refused with no scope spawned); the engine in its dispatch's own scope in
the run's slice, the group the receiver reported, empty at the end; entered through the Landlock
entrance as the recorded process, in its scope, at the accepted commit, its writes into the clone root,
the pinned copies' directory and the Codex package denied (all three in the manifest's protected write
targets); the recorded process the pinned executable with exactly its flags, the updater off, its
account's profile and neither re-hash name; a complete artifact bound to the pinned executable (the Codex
document verifying from its own lines); the exit recorded for the recorded process, exit 0, binding the
complete artifact, invocation and slot completed; a cooperative stop ending before any kill, a forced
stop killing the engine that ignores it after the configured graces, and a descendant that outlives the
group's SIGTERM ended only by the kill, the dispatch recorded ended after it, every process gone when
that end was read, the original invocation cancelled with its usage retained. `stop/*` and `caps/*`: as
on build-veldo-0060 (the reported path's stop recorded unknown; the caps before the spawn). `format/*`:
every scripted Claude Code line conforms to the binary's schema, every Codex line is an exec event of the
binary's with its item a declared kind, each perturbed line is exactly its perturbation, and every Claude
Code start used only the binary's options with exactly the qualified flags.

Plain run: 58 passed (26 preamble, 32 rows) in about 16 seconds. Stage environment run (`env -i`, the
stage's variables, TZ=UTC): 58 passed in about 21 seconds. No scope, slice or process of the run is left.

## Red record

`red-at-b39a0fdc.json`: the current suite over `git archive b39a0fdc`, unchanged. All 31 behavior rows
fail by their own assertion (no row raised): that tree's engine modules pin nothing, decode no terminal
record and register no lifecycle, its receiver launches each adapter's argv as configured and returns no
artifact, its exit record binds none and its floor completes a build on the exit code, its clones protect
no engines and nothing re-hashes an engine before its exec, and no qualification record ships.
`format/fake-lines` is green there, as it must be: it checks the suite's own scripted lines against the
binary's tables.

## Mutations (finding 60)

Registered in `scripts/check_teeth_mutations.py` with the `claude-` prefix, each declared falsifier
first; `drive.py` records `mutations.json` and one applied diff per mutant. All 32 turn their named row
red by assertion; the baseline and the no-op copies are green. `check_teeth_mutations.py --finding 60
--jobs 2`: 32 rejected.

| Mutant | Module | Named row |
|---|---|---|
| claude-pin-digest-unchecked (AC1 falsifier) | control_engine_claude.py | pin/unexpected-launch |
| claude-binding-skipped | control_launch.py | lifecycle/pinned-launch |
| claude-unknown-version-accepted | control_engine_claude.py | pin/unexpected-launch |
| claude-link-followed | control_engine_claude.py | pin/unexpected-launch |
| claude-updater-left-on | control_engine_claude.py | lifecycle/pinned-launch |
| claude-updater-configured-accepted | control_launch.py | pin/unexpected-launch |
| claude-pin-unverified | control_engine_claude.py | pin/copy |
| claude-qualification-not-installed | init_scaffold.py | pin/shipped-qualification |
| claude-lifecycle-stop-unregistered | control_engine_claude.py | lifecycle/registration |
| claude-missing-result-complete (AC2 falsifier) | control_engine_claude.py | artifact/missing-result |
| claude-invocation-completed-on-exit | control_launch.py | artifact/missing-result |
| claude-slot-completed-on-exit | control_launch.py | artifact/missing-result |
| claude-floor-exit-code-completes | dispatch.py | floor/missing-result |
| claude-completion-gate-exit-only | control_dispatch.py | floor/missing-result |
| claude-exit-artifact-unbound | control_launch.py | artifact/exit-record |
| claude-artifact-unreturned | control_launch.py | artifact/complete |
| claude-signal-ignored | control_engine_claude.py | artifact/exits |
| claude-nonzero-ignored | control_engine_claude.py | artifact/exits |
| claude-error-result-complete | control_engine_claude.py | artifact/exits |
| claude-malformed-ignored | control_engine_claude.py | artifact/malformed-output |
| claude-stop-leaves-descendant (AC3 falsifier) | control_launch.py | contained/stop-descendant |
| claude-stop-recorded-ended | control_launch.py | stop/descendant-alive |
| claude-stopped-invocation-released | control_launch.py | stop/requested |
| claude-cap-checked-after-launch (AC4 falsifier) | control_launch.py | caps/before-launch |
| claude-argv-position-unchecked | control_launch.py | pin/argv-binds-what-runs |
| claude-wrapper-rehash-skipped | control_launch.py | pin/rehash-before-exec |
| claude-entrance-rehash-skipped | control_clone.py | contained/rehash-before-exec |
| claude-engines-unprotected | control_clone.py | contained/engines-protected |
| claude-mode-unchecked | control_engine_claude.py | pin/unexpected-launch |
| claude-parent-link-followed | control_engine_claude.py | pin/unexpected-launch |
| claude-terminal-main-loop-usage | control_engine_claude.py | artifact/missing-usage |
| claude-usage-cap-stop-ignored | control_launch.py | caps/stop-at-cap |

The AC3 falsifier is `claude-stop-leaves-descendant`: it breaks the contained path's empty-group check
(the worker's exit ends the stop, whatever is left in its group), and `contained/stop-descendant` reds for
both engines because the dispatch is recorded ended while a descendant that ignores SIGTERM still lives.
The build-veldo-0060 falsifier, `claude-stop-recorded-ended`, mutated the reported path's own rule (a
stop it cannot confirm is recorded unknown); it stays as that path's check, not as the falsifier. The
owner check of `bind` (`binding_mismatch:engine_owner`) has no negative row and no mutant: making a copy
another account owns needs root or a second account, which this build does not have (user namespaces
are refused on this host).

The other findings with mutations in the modules this changes still reject: 61 (28), 62 (50), 39 (30),
40 (22), 41 (34), 42 (21) and 45 (23). Suites run plain, all green: this one, `79_veldo_0061_codex_adapter`,
`75_veldo_0062_accounts` and every suite that loads a module this changes (48 of them, the floor's
among them), `50_git_environment` and `24_veldo_0007_install_and_run`; under the stage environment, all green: this one and the VELDO-0061,
0062, 0039, 0040, 0041 and 0042 suites.
