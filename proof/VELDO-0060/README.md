# VELDO-0060 proof: the Claude Code adapter, from its pinned executable, returning validated artifacts

## The design as built

**The pinned executable.** A Claude Code adapter names the version it runs (`executable: {version}`),
never a path, and the receiver config names the factory state root (`state_root`). The qualification
record `engine/runtime/claude-qualification.json` (installed at `.veldo/runtime/`, laid by the scaffold
as a runtime asset beside `control_engine_claude.py`) lists the one qualified version, 2.1.281, with its
digest, the flags of print mode with stream JSON output (`--print --output-format stream-json
--verbose`), the environment it always runs with (`DISABLE_AUTOUPDATER=1`), its terminal protocol (the
`result` event, `success` and the four error subtypes), its subscription login (`CLAUDE_CONFIG_DIR`,
`apiKeySource` `none`), its usage units and its six rate-limit windows. Every one of those values is the
binary's own (below). `control_engine_claude.pin` copies the installer's versioned file
(`~/.local/share/claude/versions/<version>`) to `<state root>/engines/claude_code/<version>` as a new
0555 regular file and refuses a source that is a link, an unqualified version or a copy of another
digest, leaving nothing in place. `bind` is the check the receiver makes before acceptance
(`control_launch.Receiver._executable`, after the login check): an unqualified version
(`invalid_input:engine_version:<v>`), a receiver with no state root
(`missing_authority:engine_state_root`), a pinned copy that is missing
(`missing_evidence:engine_executable`), a link or not a regular file
(`binding_mismatch:engine_executable`) or of another digest (`binding_mismatch:engine_digest`), and an
adapter configuring `DISABLE_AUTOUPDATER` otherwise (`invalid_input:adapter_environment:...`) are each
refused by name, so nothing is spawned or reserved. The auto-updating `~/.local/bin/claude` link is never
read. The engine's argv is the adapter's `argv` (its wrapper, transport or clone prefix) followed by the
pinned path and the qualified flags; its environment is VELDO-0062's login environment plus the
version's settings. An engine module without `bind` (Codex today) launches as before, so VELDO-0061 plugs
its own pin into the same seam.

**The lifecycle.** `control_engine_claude.LIFECYCLE` is the adapter's registration: launch
(`Receiver._spawn`), accept (`Receiver.launch` records the acceptance before the spawn), observe
(`Meter.feed` and `Terminal.feed` over the stream), stop (`Launch.stop`), exit (`Receiver._reap`) and
artifacts (`Terminal.artifact`). The input binding is the dispatch packet on standard input, the prompt
of print mode; the source binding is the VELDO-0042 clone at the accepted commit; the tool bindings are
the recorded configuration, handed through unchanged (their flags are VELDO-0127's).

**The artifact.** `Terminal` decodes the same stream the Meter reads and returns, at the final report,
the invocation's artifact: the verdict, every problem, the decoded `result` (subtype, error flag, turns,
session, stop reason, the digest of its result text, its errors), the digest of the line it came from,
the stream's line and malformed counts, the receiver's own output digest and size, and the exit. The
verdict is `complete` only for a zero exit with no signal, stop or deadline, a stream of well-formed
events and a `success` result that is not an error; otherwise it names the first of `stopped`, `timeout`,
`signal`, `nonzero_exit`, `malformed_output`, `missing_result` and `engine_error`. The receiver writes it
0600 beside the invocation's receipts, returns it to the runner (an `artifact` event before the end) and
sets the outcomes from it: the invocation's final report and the worker slot are `completed` only when
the artifact is complete, so a zero exit without its terminal record is `failed`. The dispatch record
itself still carries only the exit status and output digest; completion stays VELDO-0021's and
VELDO-0052's.

**Stop and caps** are the existing machinery, qualified here with the pinned adapter: the stop request
reaches the receiver, the worker's session is killed and its invocation records the stop; every initial,
retry and follow-on invocation is checked and reserved against its caps and the account's windows before
the spawn (VELDO-0062), and a reached cap stops the worker.

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
installed `.veldo` copy the suite loads and the receiver executes. Real: a SQLite control store with
OpenSSH journal signatures, two account records the owner registers over profiles the helper prepares,
VELDO-0036 reservations under their production authorization, VELDO-0052's Gate, VELDO-0031 claims, a Git
source bound to the store, a VELDO-0042 clone confined with Landlock, the VELDO-0039 Runner and receiver
processes and the trusted wrapper. The engine is a fake `claude` written into a versions directory of the
installer's shape as 2.1.281 and copied by the production `pin` under the state root; the suite's
installed qualification record names its digest. It records its argv, environment, working directory,
process identity and the invocation record the store holds at its start, then prints what its packet
scripts: stream lines, perturbed bytes, a sleep, a descendant (in its session or one that leaves it) or a
signal to itself. Launches use the wrapper without a containment group, since a contained launch needs
the systemd user manager, which the suite never touches. Each row is reported once.

| Criterion | Rows |
|---|---|
| AC1 | `lifecycle/registration`, `lifecycle/pinned-launch`, `pin/unexpected-launch` (declared falsifier), `pin/copy`, `pin/shipped-qualification` |
| AC2 | `artifact/complete`, `artifact/missing-result` (declared falsifier), `artifact/exits`, `artifact/malformed-output`, `artifact/missing-usage` |
| AC3 | `stop/requested`, `stop/descendant-alive` (declared falsifier) |
| AC4 | `caps/before-launch` (declared falsifier), `caps/allowance-states`, `caps/stop-at-cap` |
| Fixtures | `format/fake-lines`, `format/fake-argv` |

`lifecycle/*`: the registration lists exactly launch, accept, observe, stop, exit and artifacts, and each
is observed on the runs (one spawn from the pinned path, the acceptance journaled before the run record,
settled usage reports, the stop run, the exited record, the artifact file equal to the returned one);
the engine ran once from the pinned copy under the state root (a regular file of the qualified digest,
not the installer's file, not a link) with exactly the qualified flags, `DISABLE_AUTOUPDATER=1` and the
recorded account's profile, in its isolated clone at the accepted commit. `pin/unexpected-launch`: the
pinned copy's bytes changed after pinning, an unknown version, the pinned path a link to the qualified
bytes, a missing copy, a receiver with no state root and an adapter configuring the updater on are each
refused by name with nothing spawned or reserved, and the restored copy launches again. `pin/copy`: the
production pin made a new 0555 regular file of the qualified digest; another build of the version, a
versioned path that is a link and an unqualified version are refused with nothing left in place.
`pin/shipped-qualification`: the shipped record and its installed copy are identical and the scaffold
lays it; its digest is the binary's as both tables read it; its flags are options of the binary's main
command with the output format among the choices and verbose beside stream JSON; its updater switch,
error subtypes, login and rate-limit windows are the binary's. `artifact/*`: live runs of a normal exit
(complete; the terminal record is the printed result, bound to its line's digest and to the receiver's
output digest; kept 0600; invocation and slot completed), a zero exit with the result removed
(`missing_result`, invocation and slot failed, tokens unknown and the next invocation under the cap
refused `unknown_allowance`), a nonzero exit, a signal, an error result with exit 1 and with exit 0, a
truncated line and a line that is not JSON in an otherwise complete stream (`malformed_output`), and a
result with its `modelUsage` removed (the terminal record kept, the tokens unknown and the reservation
retained). `stop/requested`: a stop of a running worker kills it and the descendant in its session
(read from `/proc` with their start times), the same invocation of the same dispatch and account records
`cancelled` with its tokens unknown and the next invocation refused, the artifact is `stopped` by a
signal, and the wrapper path records the dispatch unknown. `stop/descendant-alive`: a descendant that left
the worker's session survives the stop, and the dispatch is never recorded as ended while it lives (it is
unknown and the slot is held). `caps/*`: initial, retry and follow-on each reserved as such before the
engine started (the engine saw its pending reservation; the reservation's journal sequence precedes the
run record), a retry and a follow-on past the unit's invocation cap refused with nothing spawned;
available allowance settled with the CLI's tokens and messages, one invocation and its wall time;
exhausted, unknown and rate-limited allowance each refused with nothing launched; the report that reached
the token cap stopped the worker, whose artifact is `stopped`. `format/*`: every scripted line (over 60) conforms
to the binary's schema and cover every event the adapter reads; each perturbed line is exactly its
perturbation (cut short, not JSON, a result without the `modelUsage` the schema requires) of a conforming
line; every one of the fake's starts used only options the binary's main command declares, values among
their choices, verbose beside stream JSON, and exactly the qualified flags.

Plain run: 43 passed (26 preamble, 17 rows) in 11 seconds. Stage environment run (`env -i`, the stage's
variables, TZ=UTC): 43 passed in 13 seconds.

## Red record

`red-at-b39a0fdc.json`: the current suite over `git archive b39a0fdc`, unchanged. All 15 behavior rows
fail by their own assertion: the engine module pins nothing, decodes no terminal record and registers no
lifecycle, the receiver launches the adapter's argv as configured (here the wrapper alone, refused
`spawn_failed:ENOENT`) and returns no artifact, and no qualification record ships. `format/fake-lines` is
green there, as it must be (it checks the suite's own scripted lines against the table);
`format/fake-argv` is red because that tree never starts the fake, so there is no argv to check.

## Mutations (finding 60)

Registered in `scripts/check_teeth_mutations.py` with the `claude-` prefix, each declared falsifier
first; `drive.py` records `mutations.json` and one applied diff per mutant. All 21 turn their named row
red by assertion; the baseline and the no-op copies are green. `check_teeth_mutations.py --finding 60`:
21 rejected.

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
| claude-artifact-unreturned | control_launch.py | artifact/complete |
| claude-signal-ignored | control_engine_claude.py | artifact/exits |
| claude-nonzero-ignored | control_engine_claude.py | artifact/exits |
| claude-error-result-complete | control_engine_claude.py | artifact/exits |
| claude-malformed-ignored | control_engine_claude.py | artifact/malformed-output |
| claude-stop-recorded-ended (AC3 falsifier) | control_launch.py | stop/descendant-alive |
| claude-stopped-invocation-released | control_launch.py | stop/requested |
| claude-cap-checked-after-launch (AC4 falsifier) | control_launch.py | caps/before-launch |
| claude-usage-cap-stop-ignored | control_launch.py | caps/stop-at-cap |

The AC3 falsifier is driven on the wrapper path, the only stop path the suite can run without the
systemd user manager: there the receiver cannot see a descendant that left the session, so a requested
stop must record the dispatch unknown, and the mutant that records it ended reds the row while the
descendant lives. The contained path's own check (the group must be empty before an exit is recorded) is
VELDO-0040's and VELDO-0041's, qualified by their suites.

The other findings with mutations in the modules this changes still reject: 62 (50), 39 (30), 40 (22)
and 41 (34). Suites run plain, all green: this one, `75_veldo_0062_accounts` and every suite that loads
`control_launch.py` or `init_scaffold.py` (42 of them) and `50_git_environment`; under the stage
environment, all green: this one and the VELDO-0062, 0039, 0040, 0041, 0042, 0045 and 0009 suites and
`50_git_environment`.
