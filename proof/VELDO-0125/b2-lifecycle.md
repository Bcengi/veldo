# VELDO-0125 B2 receiver lifecycle correction

Implementation commit: `b7a06bb6` (Dmitry Grinberg). This is additional evidence;
previous proof records are unchanged. The owner reserves the full gate, independent
review, merged-checkout stamp and real Mac/SSH qualification for the reviewer.

The receiver now persists active work in `.active`, outside launchd's watched
`.pending` directory. Execution-lock acquisition, busy-event storage and completion
transitions are serialized by the outbox lock. A busy event returns immediately;
there is no delivery error or retry deadline for a healthy running receiver.
Completion unlocks execution and publishes any remaining delivery into `.pending`.
Startup or an explicit resume considers indexed interrupted receivers once. It
never enumerates completed dispatch directories. Operator holds live in `.waiting`;
only a new receiver event reopens them. Missing output and an authority status
response cannot acknowledge a result or erase that hold.

An incoming release upgrades the stored request. A failure of the older result
attempt preserves that release as pending. If the release attempt encounters a
permanent result refusal, the receiver retains `result-refusal.json` and the
original result evidence, queries the signed authority release, retires the Mac
slot and sends the signed Linux retirement confirmation. A later repaired replay
can still report retained usage. Transient delivery failures keep bounded retries.
Replayed original dispatch requests perform the same retained-output recovery as
release/resume requests before retiring capacity. Execution-lock directory/open
errors reach the same error recorder and retry deadline as delivery errors.

Parking creates and syncs the destination directory's parent before relocating
the recovery entry. Both directories are synced after the rename. Mac capacity
uses `.live-slots.json` under `admission.lock`. Existing pools migrate their old
slot records once when the index is absent; subsequent admission and status read
only live slots. A live slot is indexed before its slot record and bootstrap;
a retired slot is persisted before index removal. Interrupted transitions can
conservatively retain capacity, and an idempotent release removes that hold.

`lifecycle_checks.py`, registered in `106_veldo_0125_routing`, adds these rows:

| Review defect | Regression row |
| --- | --- |
| Healthy receivers trigger busy retry timers | AC3/active-receiver-no-timer |
| Operator holds repeatedly query worker_status | AC3/operator-wait-no-status-timer |
| Status without output dequeues unfinished work | AC3/status-is-not-result-ack |
| Original dispatch replay loses retained tokens | AC3/original-replay-retains-usage |
| A result refusal parks an unattempted release | AC3/upgraded-release-attempted |
| Lock opening errors cause silent immediate retries | AC3/lock-errors-bounded-recorded |
| Admission scans completed slot history | AC2/live-slot-admission-index |
| Parking can lose its parent directory on crash | AC3/park-parent-durable |

The routing run in `b2-lifecycle-routing.log` reports 56 routing rows and 26 shared
checks, with zero failures. As required by the repository selector, this partial
run exits 3 and is not a full-gate or landing claim. The rows exercise 15 drain
attempts against a held receiver, 15 attempts while waiting on an operator, actual
signed authority/result/release transactions, retained 21-token measurements,
permanent result refusal during a release upgrade, lock-open fault injection,
500 historical slots with enumeration/read guards, and directory-sync ordering.
OS and transport seams remain synthetic; no native qualification is claimed.

`lifecycle_falsifiers.py` runs isolated source mutations using only the routing
suite, serially. It retains source digests, mutation diffs, full logs and the named
row that rejected each mutation in `b2-lifecycle-falsifiers/`. The release regression
has two controls: parking the upgraded event and failing to attempt signed release
after a permanent result refusal. The parking control restores the old direct
write/unlink ordering without syncing the parent of the newly created directory.
Results are recorded in that directory's `results.json`.

The first active-entry control (`healthy-run-enqueued`) survived: it changed the
initial insertion, which the following acquisition transition moved back to active
before execution. That result remains in the original falsifier log. The replacement
`lifecycle_active_falsifier.py` changes the acquisition transition itself so the
entry stays pending throughout execution. Its separate output is retained in
`b2-lifecycle-active-falsifier/`; no earlier evidence is overwritten.

Final targeted results: `105_veldo_0125_relay` reports 17 relay rows plus 26
shared checks (43 passed, zero failed); `106_veldo_0125_routing` reports 82 passed,
zero failed. Both partial selectors exit 3 by design. Eight original effective
mutations and the replacement active-receiver mutation each fail their named row
with exit 1. `b2-lifecycle-results.json` binds the implementation source digests
and all nine effective controls, and separately records the superseded control.
The initial nine-case driver exits 1 because it preserves that surviving control;
the replacement driver exits 0 after confirming its mutant was rejected.
