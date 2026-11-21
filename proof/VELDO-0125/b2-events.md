# B2 round 9: event-driven delivery and retained measurement

Implementation: `b57f7bea`, hardened in `1f016386`. This is an implementation and
targeted regression record, not independent approval, native-host qualification,
or a canonical gate stamp. The owner reserved the full gate and mutation gates
for the reviewer. No historical proof record was replaced.

## Delivery and release protocol

The Mac receiver durably indexes each accepted delivery event in
`runs/.pending/<dispatch-sha256>.json`, under an interprocess index lock. The
per-dispatch execution lock is acquired without waiting. A release that arrives
while the original receiver owns that lock is saved in the index before the
transport returns; it does not wait for the engine or lose the wake at the SSH
timeout. A release event upgrades an ordinary result event and cannot be erased
by an older result acknowledgement that does not authorize release.

The installed launch agent uses `RunAtLoad` and `QueueDirectories` for this index.
It has no `KeepAlive`, `StartInterval`, or calendar timer. Installation replaces
an already loaded older agent when its definition changes. Startup reads only
the pending index. A drain exits when the index is empty. Completed run
directories are never enumerated by this path. Atomic-write staging lives
outside the watched directory so an interrupted write cannot leave a temporary
file that repeatedly launches an empty drain.

Each receiver delivery makes one transport attempt. Transient failures retain
their own durable attempt count, reason, and retry deadline, with exponential
backoff capped at 300 seconds. The drain catches errors per dispatch and visits
the other due deliveries before waiting for the next deadline. A permanent
refusal is moved to `runs/.parked/`, including its reason, and logged to
`runs/delivery-errors.log` by the installed launch agent. It is not retried
automatically. After repairing the cause, an operator can replay the named
dispatch to the configured receiver with action `resume` or its already
authorized `release` request. This explicitly re-enqueues that dispatch. Old
pre-index deliveries can likewise be explicitly re-enqueued by identity; this
change does not discover them by scanning history.

Parked files are retained evidence, and one dispatch can have several. The first
park keeps `<sha256(dispatch_id)>.json`; later parks use
`<sha256(dispatch_id)>.<sequence padded to eight digits>.json`. Inspect and count
every `*.json` file in `runs/.parked/`, including numbered siblings. A corrupt
record may not contain readable JSON; its filename still identifies the dispatch
hash. Replaying a dispatch does not remove or overwrite its parked evidence.
Publication refuses an occupied filename and syncs the file and directory before
removing the live queue entry. An interrupted publication can retain both copies.

A result acknowledgement removes the pending entry even when cleanup is absent
and the authority still holds capacity. There is no repeated `worker_status`
query while waiting for an operator. A later committed authority release sends
a new event. Unconfirmed retirements stay indexed until the Mac's signed
`worker_retired` command is acknowledged. Local retirement precedes that command.

Linux uses one release sender and a deadline queue. SSH exit 255, other nonzero
exits, and timeouts keep the wake pending with bounded exponential backoff.
Other ready wakes can run before a failed wake's next deadline. A successful
handoff transfers delivery responsibility to the Mac's durable index; a signed
retirement confirmation cancels queued retries. The existing transactional
partial index replays unconfirmed releases on authority restart.

## Measured usage

Both exited and unknown outcomes report measured usage to the original reserved
invocation. Cleanup-only messages cannot erase a previous measurement. Replayed
results and unchanged cumulative measurements do not create another spend
report. A later measured report replaces an earlier unknown placeholder through
the existing cumulative revision protocol, without creating another invocation.

Before starting an engine the receiver retains its binding and engine reader
identity. If the receiver crashes before saving result evidence, a release or
resume reads the dispatch's exact supervisor directory. It verifies the wrapper
and authority bindings, requires an authenticated release before treating the
output as final, reads retained `engine.out` through the configured engine meter,
and saves/delivers result evidence before retiring either side's capacity.
Already acknowledged signed final measurements are preserved. Collection files
are not deleted by this recovery path.

## Targeted checks and negative controls

`b2-events-verification/` retains the final serial suite logs and implementation
digests. `105_veldo_0125_relay` passed 17 rows; `106_veldo_0125_routing` passed 48.
Their shared preamble adds 26 checks to each reported total. Exit status 2 is the
selftest dispatcher's deliberate partial-run status, with zero failed rows.

The new routing rows cover:

- `AC3/event-index-idle-and-history`: a pending delivery beside 500 completed
  historical directories, no historical directory enumeration, no idle sleep,
  and removal after acknowledgement.
- `AC3/event-dispatch-error-isolation`: a permanent binding refusal, an available
  peer, and a transient failure across three passes; the permanent refusal is
  parked once, its reason retained, and the transient delivery independently
  completes. An explicit replay can reopen the parked event.
- `AC3/unknown-measured-usage-once`: accepted and running unknown outcomes retain
  21 measured tokens through cleanup and retirement on one spend report.
- `AC3/crash-before-evidence-usage`: the actual worker orchestration crashes
  before result evidence, retains 21 tokens in wrapper output, then flushes the
  measurement before Mac retirement and signed Linux release. Replaying the
  release leaves one placeholder and one measured revision, with no double charge.
- `AC3/failed-release-wake-retry`: SSH exit 255 followed by a timeout followed by
  repaired transport, without an authority restart, ending with host pending zero
  and the Linux reservation retired.
- `AC3/busy-release-durable-event`: a held execution lock does not block the wake;
  the saved release is subsequently drained and removed.

Existing launch-agent, outbox restart, failed cleanup, incomplete retirement,
unknown cleanup, operator release, release replay, and seven-pack composition
rows remain exercised. Unknown collector outcomes now assert the same measured
usage as normal exits. The relay row distinguishes absent measurement from an
explicit measured zero.

`event_falsifiers.py` makes ten isolated single-defect copies and runs only
`python3 scripts/selftest.py --suite 106_veldo_0125_routing`, one at a time. Each
retained patch, log, source digest, and named rejection is recorded under
`b2-events-falsifiers/`. The mutations restore idle polling, enumerate history,
abort on one refusal, retry permanent refusals, discard failed SSH wakes,
discard timed-out wakes, discard unknown usage, skip crash-output recovery,
forget busy releases, or leave acknowledged entries pending. All ten mutations were rejected by their named regression rows. These exercise
real regression assertions, not source-text rejection checks.

The OS backend and transport fault injection are synthetic. Signed commands,
authority transactions, spend reporting, receiver entrypoints, persistence,
subprocess handoff, and pack composition are exercised. Real macOS launchd,
live SSH, and provider-engine qualification were not run here. The reviewer
still owns the canonical gate and the merged-checkout verification stamp.
