# VELDO-0124 build and pending qualification

This is a Linux build observation, not a shipped specification, gate stamp,
native qualification, activation approval or independent review. The selected
machine is the SSH tailnet alias `dmitrys-mac-mini`. Its actual hostname, macOS
version, Python installation and Claude Code/Codex versions remain unobserved.
Access is expected on 2026-10-10. No SSH connection, live capture, login or provider
invocation was attempted during this build. All three ACs remain pending native
evidence. The specification's status and criteria are unchanged.

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

The extra falsifiers disable capacity, launch before the pre-call check, and bypass
the unknown-outcome retirement refusal. `negative-controls.json` names each source
hash, single-change patch, log and failed row. All six were rejected. The scripts
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
ssh dmitrys-mac-mini 'cd ~/veldo-0124-check && python3 proof/VELDO-0124/native_checks.py lifecycle > proof/VELDO-0124/native-lifecycle.json 2>&1'
ssh dmitrys-mac-mini 'cd ~/veldo-0124-check && python3 proof/VELDO-0124/native_checks.py containment > proof/VELDO-0124/native-containment.json 2>&1'
```

These drive real launchd, kqueue, ps, sandbox-exec, Git and processes on the Mac.
For each of `claude_code` and `codex` fixture configurations, lifecycle declares
`native/<engine>/natural`, `cooperative`, `deadline`, `descendant`. The deadline row
also attempts excess concurrency. Containment declares
`native/<engine>/containment`: the actual worker and its child try writes to a
protected directory, including through a symlink, while their scratch write must
succeed. These ten rows require the real Mac and use synthetic engines, openly.
They establish native primitives, not real CLI qualification. On Linux the driver
returns 2 and `not_run`, not a skip counted as a native pass.

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
