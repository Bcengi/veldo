# VELDO-0124 build and pending qualification

Round 2 update, 2026-10-28: evidence reference validation is fixed and the real
Codex signal ignoring child row passed. Complete qualification remains blocked
on Claude login. See [the current round](round2-2026-10-28/README.md),
[owner actions and remaining blockers](OPEN.md), and [the manifest](manifest.json).
Earlier observations below retain their original scope and dates.


Historical round: [batch 2, 2026-10-15](ROUND-batch2.md). Suite catalog conflicts
are resolved; nine local falsifiers were rejected and the owning suites rerun.
Static contract defects were repaired. Real engine qualification remains blocked.

This is a build observation, not a shipped specification, gate stamp,
native qualification, activation approval or independent review. The selected
machine is the SSH tailnet alias `dmitrys-mac-mini`: hostname `dmitrys-mini.lan`,
macOS 26.5.1 (25F80), arm64, uid 501. The 22 synthetic engine native rows and
14 native falsifiers ran there on 2026-10-10 (see "Native results" below). The real CLI rows did not run:
no login, live capture or provider invocation was attempted. All three ACs remain
pending real CLI evidence and the canonical gate. Status and criteria are unchanged.

## Implementation and installation

Five canonical assets live in `engine/.veldo` and are identical to `.veldo`:

* `project_runner_macos_profile.py`: versioned finite settings, pinned interpreter,
  host/version and configuration qualification binding, binary digest, Seatbelt policy.
* `project_runner_macos_os.py`: launchctl bootstrap/bootout, plist generation,
  kqueue NOTE_EXIT, libproc coalition membership, user temp, interpreter version,
  accepted clean Git clone inspection.
* `project_runner_macos_wrapper.py`: trusted launchd job, held release, binary
  recheck, sandboxed engine in its own process group, independent heartbeat,
  elapsed deadline backstop over the coalition, waitpid receipt.
* `project_runner_macos.py`: concurrency lock and slots, run environment, elapsed
  deadlines, stop escalation over the coalition, unknown retention, recovery from
  `slot.json` and explicit release.
* `project_runner_macos_control.py`: accepted authority contract, registered
  subscription profile, current eligibility seam, pre-call InvocationGuard and
  guarded retirement through the real reservation service.

All five map to the existing `project_runner` architecture area and its governed
process exception. This checkout has no Linux `project_runner` or `control_host`
files: the reference lifecycle is in `control_launch`, `control_containment`,
`control_heartbeat`, `control_retirement` and `control_clone`. Those are unchanged.
No existing suite imports a changed production file. The two new suites own every
new runtime module. `AC1/template-sync` enumerates the actual pack engine inventory
and assembles each of the seven packs, checking all five installed assets against
the canon. Packs inherit engine assets; absent checked-in pack copies are correct
under `packs/README.md`.

The authority remains on Linux. Call the ordinary Runner's `prepare`, then
`project_runner_macos_control.Receiver.start(contract, clone, scratch)` using a
trusted Mac host endpoint. `Receiver.wait(dispatch)` commits the bound termination
or unknown observation. The host endpoint is a `Supervisor`; network transport and
routing are VELDO-0125, deliberately not activated here. The existing Linux
receiver, its reported-worker branch and its Linux retirement observer are not
silently replaced by a Mac observer. Supply the existing current eligibility
check and the accepted clone's cleanup callback to this receiver. Settlement uses
the retained InvocationGuard through the existing 0062 receipt ingestion path;
no counter is invented from elapsed time, cancellation or OS exit. `retire` checks
the whole group, known dispatch outcome, clone cleanup and accounting before the
authority slot and then the host slot can be released.

This profile accepts full isolated clones at the accepted commit/tree and rejects
dirty clones, shared worktree metadata and unqualified object alternates. Shared
cache qualification on macOS is not asserted. APFS aliases are resolved before rule
generation; overlap checks conservatively fold case and Unicode normalization.

## Containment profile (Seatbelt)

`project_runner_macos_profile.sandbox` emits `(allow default)` followed by one deny
rule per line, inherited by the engine and every descendant:

| Rule | What it denies |
| --- | --- |
| write | every file write outside the run grants: clone, scratch, run home, run temp and the run's own login profile, plus `/dev/null` and `/dev/tty`. Authority keys and store, the slot root (`slot.json`, `result.json`, other dispatches) and the installed `.veldo` code must never overlap a grant, so this rule denies them. |
| read ssh, claude, codex | `file-read-data` of the account's real `~/.ssh`, `~/.claude*` and `~/.codex*` (profile field `home`) |
| read accounts, projects, dispatches | `file-read-data` of `account_roots`, `project_roots` and the slot root, except through a run grant |
| launchctl exec | `process-exec` of `/bin/launchctl` |
| job-creation | the Seatbelt `job-creation` operation |
| keychain | `mach-lookup` of `com.apple.SecurityServer`, `com.apple.securityd`, `com.apple.securityd.xpc` |
| signal | signals to any process outside this sandbox instance, so only the engine's own descendants |

Reads deny data, not metadata: `stat` of an ancestor such as a project root still
works so a clone inside it resolves. Existence and size of denied files stay visible.
The run's own login directory (`CLAUDE_CONFIG_DIR` or `CODEX_HOME`) stays readable
and writable because the engine refreshes its own session there; every other
account directory is denied. Keychain access is denied until VELDO-0147 decides what
a run's own engine account may use. Network is not restricted: that is a Release 2
open item, as are launchd spawned helpers (XPC services, the Simulator's
CoreSimulatorService), which run in their own launchd jobs outside this sandbox
and coalition and may write to the owner's real `~/Library/Developer`.

Engines run with their own sandboxes off inside this one, because a nested Seatbelt
fails with `sandbox_apply: Operation not permitted`. Codex argv must carry its no
sandbox mode (`--sandbox danger-full-access`, `-s danger-full-access` or
`--dangerously-bypass-approvals-and-sandbox`), else `unsupported_configuration:nested_sandbox`.
Claude Code admission now checks `sandbox.enabled` and refuses an enabling source
with `unsupported_configuration:claude_bash_sandbox`. The trusted wrapper repeats
the check immediately before engine execution and records a named `refusal.json`
if settings changed after admission. When the run's `settings.json` does not exist,
Veldo creates it with `{"sandbox":{"enabled":false}}`; existing settings are
validated and preserved. Preflight itself does not write settings.

### Claude settings discovery and admission

[claude-settings.json](claude-settings.json) records byte offsets, excerpts and the
SHA-256 of the installed Linux Claude Code 2.1.281 binary inspected for this change.
No CLI or login was invoked. It confirms the false default, the exact key and these
sources:

* `CLAUDE_CONFIG_DIR/settings.json`, bound to the request's own `login_profile`.
* The accepted clone's `.claude/settings.json` and `.claude/settings.local.json`.
  Claude launches at a standalone clone root; alternate project roots and worktree
  flags refuse. Its source-selection flag can disable project/local reads.
* `/Library/Application Support/ClaudeCode/managed-settings.json` and visible JSON
  files in `managed-settings.d`, plus `CLAUDE_CONFIG_DIR/remote-settings.json`.
* CLI settings JSON or files, including relative paths resolved against the clone,
  and CLI managed settings JSON.

The Linux binary omits the Mac MDM reader. Anthropic's
[MDM example](https://github.com/anthropics/claude-code/tree/main/examples/mdm)
supplies the `com.anthropic.claudecode` preference domain and direct dictionary
format. The check reads its system and per-user managed preference files, system
preferences, and the account and run-home preference files. This is local settings
inspection, not native MDM qualification or observation of future server policy
updates. Real engine qualification still requires the selected Mac.

Admission is deliberately conservative: any inspected true value refuses even if
another source says false. Invalid JSON, ambiguous duplicate keys, invalid sandbox
types, missing CLI files and unreadable settings fail closed. Policy helpers and
settings-supplied environments refuse because they can change settings sources at
startup. Only the finite print-mode CLI options and Claude environment variables
listed in `project_runner_macos_profile.py` are admitted. Unknown options, source
redirects and duplicate settings flags refuse by name. False or absent sandbox
settings remain accepted. A permission-skip flag does not disable the bash sandbox.

The new Linux rows are `AC1/claude-sandbox-refused`, `claude-sandbox-disabled`,
`claude-settings-sources`, `claude-invocation`, `claude-settings-unreadable`,
`claude-wrapper-recheck`, and the control-store row `claude-sandbox-store-refused`.
The store row observes refusal before acceptance, invocation reservation or
bootstrap. The existing `accepted-store` row checks the generated false setting.
Template-sync assembles all packs and compares their Mac assets with the engine
and repository copies. Suites 103 and 104 are the only suite files loading these
changed assets or the VELDO-0124 check helpers.

The diagnostic record is [claude-negative-control.json](claude-negative-control.json):

| Partial run | Selected suite rows passed | Total passed | Failed |
| --- | ---: | ---: | ---: |
| 103, check intact | 28 | 54 | 0 |
| 104, check intact | 7 | 33 | 0 |
| 103, check removed in isolated copy | 23 | 49 | 5 |

The totals include the dispatcher's prerequisite checks. Passing partial runs exit
2 by repository design; the mutant exits 1. Raw logs are
[103](claude-suite-103.log), [104](claude-suite-104.log), and
[mutant](claude-negative-control.log). The single-change
[patch](claude-sandbox-check-removed.patch) removes the `sandbox.enabled` refusal
from `claude_document`. With `VELDO_0124_MODULES` selecting that isolated copy,
`AC1/claude-sandbox-refused` fails with `expected refusal:
unsupported_configuration:claude_bash_sandbox`; source, CLI, malformed-value and
wrapper rows fail too. The wrapper test intercepts the native boundary, so the
mutant cannot launch an engine. Production files retain the check throughout.

These are partial diagnostic results, not a proof-manifest, full-gate or landing
claim. The reviewer runs the gate; no native captures or real-login runs occurred
for this follow-up. The earlier native observations below remain historical.


## Run environment, process structure and recovery

`Supervisor.run_environment`, called by `project_runner_macos_control.engine_environment`
for every dispatch, sets `HOME` to `<scratch>/home` and `TMPDIR`, `TMP`, `TEMP` to
`/private/var/folders/.../T/veldo-<label hash>`, the user's own temp. Admission
refuses any other value (`binding_mismatch:run_environment`). The supervisor creates
the run temp plus `Library/Developer/Xcode/DerivedData` and `Library/Developer/CoreSimulator`
under the run home; release removes the run temp.

launchd runs the wrapper with the interpreter pinned in the profile (`interpreter`,
`/opt/homebrew/bin/python3.12` on this Mac). A missing interpreter or one older than
3.11 refuses with `unsupported_configuration:interpreter` before launch;
`/usr/bin/python3` (3.9.6) is never used. The engine runs in its own process group
under the wrapper, so a group SIGKILL of the engine leaves the wrapper alive to reap
it and write `result.json`. The wrapper enforces the elapsed deadline itself (TERM
the engine group and every other coalition member at the deadline, KILL after the
kill grace), so a dead supervisor cannot leave the engine unbounded, and it waits
until its coalition is otherwise empty before it exits.

Descendants are tracked by the launchd job's resource coalition, read with libproc
`proc_pidinfo(PROC_PIDCOALITIONINFO)`. Observed on macOS 26.5.1: each `user/501`
Background job gets its own coalition, and a setsid child and a double forked orphan
reparented to pid 1 stay in it; `kqueue NOTE_TRACK` returns ENOTSUP; `launchctl
bootout` leaves setsid children running. Stop escalation signals the engine group and
every other coalition member; release is refused while any member lives. Admission
refuses a wrapper that shares the supervisor's coalition. PID reuse between listing
and signalling is Release 2.

`slot.json` now records label, coalition, wall deadline, cause and run temp.
`Supervisor.recover(dispatch)` rebuilds a running or exited Run after a supervisor
restart; starting and unknown slots stay stopped (`unknown_outcome:slot_<state>`).

## Rows and single-change falsifiers

| AC | Main Linux row | Driven single change | Additional rows |
| --- | --- | --- | --- |
| AC1 | `AC1/qualification` | Accept fixture qualification as native | `profile`, `bindings`, `apfs-policy`, `apple-interfaces`, `run-environment`, `interpreter`, `nested-sandbox`, `template-sync`, `native-declared`, `accepted-store`, `refusals` |
| AC2 | `AC2/deadline` | Ignore the elapsed deadline | `capacity`, `contract-deadline`, `precall-caps`, `invocation-boundaries` |
| AC3 | `AC3/descendant` | Declare the group ended after only parent exit | `natural`, `cooperative`, `ignoring`, `hard-kill-unknown`, `recover`, `notification-lost`, `heartbeat`, `unknown`, `retirement-obligations`, `unknown-charge` |

The fake models launchd's coalition: the engine has its own group under the
wrapper, a setsid survivor lives outside that group and ignores TERM, a KILL of the
engine leaves the wrapper to record it, and mode `killed` loses the wrapper with it.
The extra falsifiers disable capacity, launch before the pre-call check, drop the
launchd Background session type (`AC1-session-type`, failing `AC1/apple-interfaces`),
signal only the engine group (`AC3-group-only`, the survivor lives and `AC3/descendant`
fails) and bypass the unknown outcome retirement guard (`AC3-unknown-retire`). That
last one drives the case the guard alone owns: exit seen, coalition empty, cleanup
and accounting done, result missing after SIGKILL; the mutant retires the
reservation and `AC3/unknown-charge` fails on "reservation retired with an unknown
outcome". `negative-controls.json` names each source hash, patch, log and failed row.
All eight were rejected. The scripts use only these suites, sequentially:

```
python3 scripts/selftest.py --suite 103_veldo_0124_macos
python3 scripts/selftest.py --suite 104_veldo_0124_control
python3 proof/VELDO-0124/negative_controls.py
```

The selected suites intentionally return 2 with zero failed rows: the dispatcher
marks every selected run PARTIAL. Their logs are development observations only.
No full gate, global mutation checker or live qualification ran. The reviewer must
run the canonical gate on the merged checkout and land its own stamp.

The store suite uses real SQLite, real OpenSSH journal signatures, real Git and
real account, dispatch and reservation services. Its Mac is a fixture. Absent
signals or observations retain unknown outcome. None of these fixtures qualify
macOS or either provider CLI.

## Native rows

Run from this reviewed worktree when the Mac is reachable. This exports files into
a separate probe directory; it neither switches nor changes a Mac Git worktree.
Do not copy authority keys, the authority database or real login files into it.

```
git archive HEAD .veldo proof/VELDO-0124 | ssh dmitrys-mac-mini 'mkdir -p ~/veldo-0124-check && tar -x -C ~/veldo-0124-check'
ssh dmitrys-mac-mini 'cd ~/veldo-0124-check && /opt/homebrew/bin/python3.12 proof/VELDO-0124/native_checks.py lifecycle > proof/VELDO-0124/native-lifecycle.json 2>&1'
ssh dmitrys-mac-mini 'cd ~/veldo-0124-check && /opt/homebrew/bin/python3.12 proof/VELDO-0124/native_checks.py containment > proof/VELDO-0124/native-containment.json 2>&1'
ssh dmitrys-mac-mini 'cd ~/veldo-0124-check && /opt/homebrew/bin/python3.12 proof/VELDO-0124/native_falsifiers.py > proof/VELDO-0124/native-falsifiers.json'
```

These drive real launchd, coalitions, kqueue, sandbox-exec, Git and processes through
the production admission (`Supervisor.admit`), engine environment
(`engine_environment`, so the run home and temp are the production ones) and
Seatbelt policy. Only qualification is skipped, because it is what these rows
measure. Work directories live under `~/veldo-0124-check/runs` and are removed.
Containment decoys (`.ssh/id_ed25519`, `.claude/settings.json`, `.claude.json`,
`.claude-accounts/other`, `.codex/auth.json`, another account profile, another
project, another dispatch's `request.json`) are files the check creates under a test
owner home given as the profile's `home`; the owner's real files, logins and
Keychain items are never named. On Linux the drivers return 2 and `not_run`.

For each of `claude_code` and `codex` synthetic engines:

* lifecycle `natural`, `cooperative`, `deadline` (also attempts excess concurrency),
  `descendant` (the engine ignores TERM and starts a child that calls setsid and
  ignores TERM; the row checks that the PID the child wrote is in the job coalition,
  outside the engine's group and session, and dead after the supervisor's KILL),
  `hard-kill` (the check SIGKILLs the engine's process group from outside; the
  wrapper survives and records -9, the slot is released), `supervisor-loss` (the
  supervisor process is SIGKILLed mid run; the wrapper stops the engine at the
  deadline; a new supervisor rebuilds the Run from `slot.json` and releases it).
* containment `write`, `read`, `launchd`, `keychain`, `signal`, all from one
  sandboxed engine run that tries each denied action and the allowed ones.

## Native results, 2026-10-10

Synthetic engines, Python 3.12.13, `native-lifecycle.json` and `native-containment.json`:

| Row | claude_code | codex |
| --- | --- | --- |
| `natural` | passed, exit 0, no stop steps, released | passed |
| `cooperative` | passed, exit -15 after wrapper TERM | passed |
| `deadline` | passed, runtime_cap, TERM at about 1.2 s, excess launch refused | passed |
| `descendant` | passed, setsid PID found in coalition, cooperative, terminate, kill, PID dead, exit -9, released | passed |
| `hard-kill` | passed, group SIGKILL from outside, wrapper recorded -9, released | passed |
| `supervisor-loss` | passed, supervisor killed about 2.7 s before the deadline, engine stopped within 0.13 s after it, recovered and released | passed |
| `write` | passed: owner home, authority, installed code, `slot.json`, `result.json` and a child through a symlink denied; clone, scratch, login, run home, run temp, DerivedData, CoreSimulator, `/dev/null` allowed; `/dev/tty` ENXIO (no terminal) | passed |
| `read` | passed: every decoy class and `.CLAUDE.json` (case variant) denied; own login, clone and other owner files readable | passed |
| `launchd` | passed: `launchctl submit` and `bootstrap` refused at exec (EPERM); a copy of launchctl in scratch executes and is killed with SIGKILL (-9); no job exists; rules present | passed |
| `keychain` | passed: all three lookups 1100 (not privileged) inside; outside SecurityServer and securityd.xpc resolve (0), securityd is unknown (1102) | passed |
| `signal` | passed: SIGCONT to the supervisor and the wrapper denied, own child allowed | passed |

Native falsifiers (`native-falsifiers.json`), each one line removed or disabled in
a copy of `.veldo` and run for claude_code; all 14 rejected, each failing its row:

| Mutant | Failed row | Observed |
| --- | --- | --- |
| write rule | `write` | owner home, authority, code and `result.json` writes allowed |
| read ssh, claude, codex, accounts, projects, dispatches (six mutants) | `read` | exactly that class readable |
| launchctl exec | `launchd` | launchctl executed; launchd itself refused: `submit` rc 1, `bootstrap` EIO 5, no job |
| job-creation | `launchd` | still refused at exec; fails on the missing rule |
| keychain | `keychain` | SecurityServer and securityd.xpc lookups 0 inside |
| signal | `signal` | supervisor and wrapper signalled |
| wrapper deadline backstop | `supervisor-loss` | engine outlived its deadline without a supervisor |
| supervisor signals only the engine group | `descendant` | setsid survivor, outcome unknown |
| engine in the wrapper's group | `hard-kill` | wrapper killed with the engine, outcome unknown |

launchd's own refusal of jobs from sandboxed callers matches the kernel log the
previous attempt observed, `Sandbox: launchctl deny(1) job-creation`; why the copied binary is
killed was not researched (Release 2 escape matrix). Earlier on 2026-10-10 the first
native run failed `natural` with `unknown_outcome:launch`: on macOS 26
`launchctl bootstrap user/501` refuses a plist without
`LimitLoadToSessionType=Background` with EIO 5, and `gui/501` takes only Aqua jobs
and exists only with a console login. Dropping the key still fails `natural`
(`native-falsifier-session-type.json`); the Linux falsifier is `AC1-session-type`.

## What the engines check needs from the owner

Not run. It launches the real CLIs with a real prompt, so every probe is a real
subscription model call (six calls: natural, cooperative, deadline per engine).
Observed without executing anything: Claude Code 2.1.285 at
`~/.local/share/claude/versions/2.1.285`, reached through the symlink
`~/.local/bin/claude`. No Codex CLI was found in `/opt/homebrew`, `/usr/local`,
`~/.local/bin`, npm, bun, volta or `/Applications`; its install path and version
are unknown. The owner must provide:

1. Codex: whether it is installed, its absolute binary path and version, or
   permission to install it under the user account only.
2. For each engine, the absolute versioned binary for `argv[0]` (not the
   auto-updating symlink, which would turn an update into `stale_version:engine_binary`),
   the supported noninteractive argv, and the configuration digest from the
   authority's accepted adapter configuration.
3. A fresh, dedicated subscription profile directory per engine, separate from
   `~/.claude` and `~/.codex`, passed as `CLAUDE_CONFIG_DIR` or `CODEX_HOME`,
   and which already qualified account each one is. Logging it in is the owner's
   act; this harness never logs in or reads existing logins.
4. Explicit consent for six model calls, and the authority's accepted contracts
   and pre-call reservation receipts for them (six slots in a qualification pool).
5. The profile's pinned `interpreter` (`/opt/homebrew/bin/python3.12` worked); admission
   refuses a missing one or one older than 3.11.
6. The directories that hold other account profiles (`account_roots`) and other
   projects (`project_roots`) on that Mac, so the sandbox denies reading them.
   The engines rows then show whether each engine runs inside this profile with its
   own sandbox off (Codex `--sandbox danger-full-access`) and Keychain lookups denied;
   a login that needs the Keychain fails them, and VELDO-0147 decides that access.

Real CLI rows are `native/qualified-<engine>/natural`, `cooperative`, `deadline`
for both installed engines. Before running them, the owner's assistant must record
the native facts, installed versions, binary/configuration identities and previously
qualified subscription accounts. Prepare `~/veldo-0124-candidate.json` from the
authority's accepted contracts and its actual pre-call reservations. No fabricated
receipt, login discovery, login command or paid API key is permitted. Then run:

```
ssh dmitrys-mac-mini 'cd ~/veldo-0124-check && /opt/homebrew/bin/python3.12 proof/VELDO-0124/native_checks.py engines ~/veldo-0124-candidate.json > proof/VELDO-0124/native-engines.json 2>&1'
```

Candidate JSON has `host`, `os_version`, `profile`, and `probes`. The profile is
`veldo.macos_worker_profile/v1`, with positive `revision`, `max_workers`, absolute
existing `root`, nonempty `protected` directory list, absolute `interpreter`
(`/opt/homebrew/bin/python3.12`), existing `home` (the account's real home),
`account_roots` and `project_roots` lists of existing directories, and positive finite seconds:
`runtime_seconds`, `startup_seconds`, `stop_grace_seconds`, `kill_grace_seconds`,
`settle_seconds`, `heartbeat_seconds`, `heartbeat_window_seconds`. Window exceeds
heartbeat interval. Both `engines` entries contain absolute `argv`, `version`,
`binary_digest`, `configuration_digest`. Use the real supported CLI argv for the
accepted configuration, with Codex in its no sandbox mode and Claude Code's bash
sandbox not enabled. The deadline request must actually outlive its deadline;
an engine that exits early fails that row rather than supplying a fake cap pass.

Each of six `probes` keys is `<engine>/<mode>`, with `request` and
`reservation_receipt`. The request has the full prepared dispatch `contract`,
`contract_digest`, committed `acceptance` digest, `engine`, accepted `clone`,
`scratch`, account `login_profile`, and sanitized `environment` with only that
provider's registered login variable; the probe adds the production run `HOME`
and `TMPDIR`. A receipt names `dispatch_id`, `invocation`,
positive `accepted_seq`, bounded `wall_seconds`, `host`, `engine`, and `account`.
The accepted deadline must still be in the future and no larger than the reserved
time. Each probe needs a distinct dispatch/clone/scratch. Its isolated qualification
pool needs six slots because unsettled calls remain charged; receipts are settled
through the authority afterwards, never by this probe. Keep raw outputs private.

Candidate probes deliberately use the supervisor's private qualification path.
The public launch path still refuses an unqualified profile. No native driver
creates a production qualification stamp or changes eligibility. An operator must
review all observations against the exact profile digest and populate a
`veldo.macos_worker_qualification/v1` record: `kind: native`, actual `host` and
`os_version`, `profile_digest`, and evidence references for every engine's `launch`,
`write`, `read`, `launchd`, `keychain`, `signal`, `capacity`, `deadline`, `natural`,
`cooperative`, `descendant`, `hard-kill`, `supervisor-loss` row.
Do not promote the synthetic engine profiles or substitute their receipts for the
real CLI rows. Missing real-engine/account qualification is still a blocker.

## Apple interface basis

The fake's launchd process-group cleanup and stop timeout follow Apple's
[launchd.plist manual source](https://github.com/apple-oss-distributions/launchd/blob/main/man/launchd.plist.5).
Elapsed runtime is enforced by this supervisor, not by launchd's idle `TimeOut`.
The exit notification follows Apple's
[kqueue manual](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/kqueue.2.html).
Archive the target machine's `launchctl`, `launchd.plist`, `sandbox-exec`, `ps` and
`kqueue` manuals with native observations. Apple's old manual pages are interface
references, not evidence of the current host's behavior. Seatbelt is chosen as a
candidate only: absence, deprecation incompatibility or rejected profile syntax
must fail qualification, never fall back to an unconfined worker.
