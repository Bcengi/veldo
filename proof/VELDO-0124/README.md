# VELDO-0124 build and pending qualification

This is a build observation, not a shipped specification, gate stamp,
native qualification, activation approval or independent review. The selected
machine is the SSH tailnet alias `dmitrys-mac-mini`: hostname `dmitrys-mini.lan`,
macOS 26.5.1 (25F80), arm64, uid 501. The ten synthetic engine native rows ran
there on 2026-10-10 (see "Native results" below). The real CLI rows did not run:
no login, live capture or provider invocation was attempted. All three ACs remain
pending real CLI evidence and the canonical gate. Status and criteria are unchanged.

## Implementation and installation

Five canonical assets live in `engine/.veldo` and are identical to `.veldo`:

* `project_runner_macos_profile.py`: versioned finite settings, host/version and
  configuration qualification binding, binary digest, canonical filesystem policy.
* `project_runner_macos_os.py`: launchctl bootstrap/bootout, plist generation,
  kqueue NOTE_EXIT, ps process groups, accepted clean Git clone inspection.
* `project_runner_macos_wrapper.py`: trusted launchd job, held release, binary
  recheck, sandboxed engine child, independent heartbeat, waitpid receipt.
* `project_runner_macos.py`: concurrency lock and slots, elapsed deadlines, stop
  escalation, complete group observation, unknown retention and explicit release.
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
cache qualification on macOS is not asserted. Writable paths are the clone,
scratch and explicitly registered account profile. The authority directories,
host slot records and installed code must be outside all grants. APFS aliases are
resolved before rule generation; overlap checks conservatively fold case and
Unicode normalization. Native checks still have to verify kernel path semantics.
No aggregate resource, setsid escape, PID reuse or machine-loss recovery claim is
made. Python 3.11 or newer is required by these assets.

## Rows and single-change falsifiers

| AC | Main Linux row | Driven single change | Additional rows |
| --- | --- | --- | --- |
| AC1 | `AC1/qualification` | Accept fixture qualification as native | `profile`, `bindings`, `apfs-policy`, `apple-interfaces`, `template-sync`, `native-declared`, `accepted-store`, `refusals` |
| AC2 | `AC2/deadline` | Ignore the elapsed deadline | `capacity`, `contract-deadline`, `precall-caps`, `invocation-boundaries` |
| AC3 | `AC3/descendant` | Declare the group ended after only parent exit | `natural`, `cooperative`, `ignoring`, `notification-lost`, `heartbeat`, `unknown`, `retirement-obligations`, `unknown-charge` |

The extra falsifiers disable capacity, launch before the pre-call check, bypass
the unknown-outcome retirement refusal and drop the launchd Background session type
(`AC1-session-type`, failing `AC1/apple-interfaces`). `negative-controls.json` names
each source hash, single-change patch, log and failed row. All seven were rejected. The scripts
use only these suites, sequentially:

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
real account, dispatch and reservation services. Its Mac is a fixture. The OS
fixture models a non restarting launchd job, a separate parent exit event, ps
group membership, cooperative TERM, group TERM and KILL. KILL cannot create a
wrapper receipt. Absent signals or observations retain unknown outcome. None of
these fixtures qualify macOS or either provider CLI.

## Native handoff, all rows still not run

Run from this reviewed worktree when the Mac is reachable. This exports files into
a separate probe directory; it neither switches nor changes a Mac Git worktree.
Do not copy authority keys, the authority database or real login files into it.

```
git archive HEAD .veldo proof/VELDO-0124 | ssh dmitrys-mac-mini 'mkdir -p ~/veldo-0124-check && tar -x -C ~/veldo-0124-check'
ssh dmitrys-mac-mini 'cd ~/veldo-0124-check && /opt/homebrew/bin/python3.12 proof/VELDO-0124/native_checks.py lifecycle > proof/VELDO-0124/native-lifecycle.json 2>&1'
ssh dmitrys-mac-mini 'cd ~/veldo-0124-check && /opt/homebrew/bin/python3.12 proof/VELDO-0124/native_checks.py containment > proof/VELDO-0124/native-containment.json 2>&1'
```

`/usr/bin/python3` on this Mac is 3.9.6, below the required 3.11, and lacks
`hashlib.file_digest`; use the owner's existing Homebrew 3.12. Nothing is installed.

These drive real launchd, kqueue, ps, sandbox-exec, Git and processes on the Mac.
For each of `claude_code` and `codex` fixture configurations, lifecycle declares
`native/<engine>/natural`, `cooperative`, `deadline`, `descendant`. The deadline row
also attempts excess concurrency. Containment declares
`native/<engine>/containment`: the actual worker and its child try writes to a
protected directory, including through a symlink, while their scratch write must
succeed. These ten rows require the real Mac and use synthetic engines, openly.
They establish native primitives, not real CLI qualification. On Linux the driver
returns 2 and `not_run`, not a skip counted as a native pass.

## Native results, 2026-10-10

Synthetic engines on real launchd, kqueue, ps, sandbox-exec and Git, Python 3.12.13:

| Row | claude_code | codex |
| --- | --- | --- |
| `natural` | passed, exited 0, no stop steps | passed |
| `cooperative` | passed, exited after wrapper TERM | passed |
| `deadline` | passed, runtime_cap, group TERM at 1.16 s, excess launch refused | passed |
| `descendant` | passed, cooperative, terminate, kill; group empty; outcome unknown, slot retained, release refused | passed |
| `containment` | passed, scratch write allowed, direct and symlinked protected writes denied to worker and child | passed |

Results: `native-lifecycle.json`, `native-containment.json`. The descendant row
ends `unknown` by design: KILL leaves no wrapper receipt, so the slot stays held.

The first native run failed `native/claude_code/natural` with
`unknown_outcome:launch`. On macOS 26, `launchctl bootstrap user/501` refuses a
plist without `LimitLoadToSessionType=Background` with EIO 5. `gui/501` accepts
only Aqua jobs and exists only with a console login, so it is wrong for a headless
worker. The job now declares the Background session type in `user/<uid>`. The
launchd job ran as pgid leader with ppid 1, so `AbandonProcessGroup=False`
and `killpg` cover ordinary descendants. Native falsifiers, each a single change
in a scratch copy on the Mac: dropping the session key fails `natural` with
`unknown_outcome:launch` (`native-falsifier-session-type.json`); removing the
Seatbelt deny fails `containment` with the protected write succeeding, exit 91
(`native-falsifier-sandbox.json`). The Linux falsifier is `AC1-session-type`.

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
5. A Python 3.11+ path for the run (`/opt/homebrew/bin/python3.12` worked).

Real CLI rows are `native/qualified-<engine>/natural`, `cooperative`, `deadline`
for both installed engines. Before running them, the owner's assistant must record
the native facts, installed versions, binary/configuration identities and previously
qualified subscription accounts. Prepare `~/veldo-0124-candidate.json` from the
authority's accepted contracts and its actual pre-call reservations. No fabricated
receipt, login discovery, login command or paid API key is permitted. Then run:

```
ssh dmitrys-mac-mini 'cd ~/veldo-0124-check && python3 proof/VELDO-0124/native_checks.py engines ~/veldo-0124-candidate.json > proof/VELDO-0124/native-engines.json 2>&1'
```

Candidate JSON has `host`, `os_version`, `profile`, and `probes`. The profile is
`veldo.macos_worker_profile/v1`, with positive `revision`, `max_workers`, absolute
existing `root`, nonempty `protected` directory list, and positive finite seconds:
`runtime_seconds`, `startup_seconds`, `stop_grace_seconds`, `kill_grace_seconds`,
`settle_seconds`, `heartbeat_seconds`, `heartbeat_window_seconds`. Window exceeds
heartbeat interval. Both `engines` entries contain absolute `argv`, `version`,
`binary_digest`, `configuration_digest`. Use the real supported CLI argv for the
accepted configuration. The deadline request must actually outlive its deadline;
an engine that exits early fails that row rather than supplying a fake cap pass.

Each of six `probes` keys is `<engine>/<mode>`, with `request` and
`reservation_receipt`. The request has the full prepared dispatch `contract`,
`contract_digest`, committed `acceptance` digest, `engine`, accepted `clone`,
`scratch`, account `login_profile`, and sanitized `environment` with only that
provider's registered login variable. A receipt names `dispatch_id`, `invocation`,
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
`containment`, `capacity`, `deadline`, `natural`, `cooperative`, `descendant` row.
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
