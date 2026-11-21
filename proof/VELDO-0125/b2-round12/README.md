# Round 12 worker and event lifetime corrections

Scope: VELDO-0125 logic regressions on Linux with simulated Apple interfaces.
No native macOS, SSH or engine qualification is asserted. The owner reserves the
canonical gate and other suites for the reviewer. All prior proof files remain
unchanged; the new fixture revisions preserve their earlier assertions except
for the explicitly superseded startup replay ordering, which now additionally
asserts scheduled replay after the incoming request has completed.

The recorder-failure path parks the original bytes by rename without invoking
the failed recorder. It removes launchd's immediate relaunch condition. A drain
contains failures per entry before reporting recorder errors. Normal receivers
read and handle the incoming request without network replay of old deliveries.
Their post-response recovery only schedules orphaned active entries. Orphans
retain their retry deadlines and attempt counts, including future-due retries.
The execution lock keeps live owners out of the watched pending queue.

Run `python3 .veldo/control_worker.py CONFIG --install` before enabling dispatch
eligibility. It initializes/migrates the slot index before installing launchd's
resumer. The resumer also initializes it at worker start. Receiver construction
explicitly disables migration and refuses an absent index before admission.lock.
An installation and v2 qualification are prerequisites for receiving work.

Profile v2 removes both heartbeat fields and rejects v1 or retired fields.
Qualification must bind the new profile digest. NOTE_EXIT and the runtime cap
provide liveness. A cooperative stop waits for the earlier grace/runtime deadline.
The original 0124 test file is restored byte-for-byte from 277045cc's parent;
its v1 heartbeat row is historical and is explicitly superseded for v2 in the
0125 specification. The new stalled-wrapper row asserts both natural NOTE_EXIT
completion and runtime termination of a blocked wrapper. This is not a claim
that the historical 0124 suite qualifies the new profile version.

ExitWatch closes its kqueue and any allocated pipe ends on initialization failure.
A lock serializes pipe writes with close, and close is idempotent. A late stop
cannot write to recycled descriptors; Run.stop captures the watch reference once.

`routing-correction.json` corrects the round 11 README without altering it or its
log: `routing-corrected.log` is the completed corrected routing invocation,
reporting 112 routing rows plus 26 prerequisite rows, 138 passed and zero failed
in 107.07 seconds. It is not partial output from a stopped invocation. The record
binds that statement to the log bytes and does not invent overlap-stop timing.

New regression rows are registered in 106_veldo_0125_routing through
round12_checks.py. round12_falsifiers.py runs each isolated mutation serially
through that same suite and requires its named regression row to fail. Mutation
diffs, source digests and actual suite logs are retained in its output directory.
Selected all-pass suites deliberately return 2 (PARTIAL); they are not gate proof.
Earlier local validation failures are retained in the numbered routing logs.
Final counts and commit binding will be recorded separately after execution.
