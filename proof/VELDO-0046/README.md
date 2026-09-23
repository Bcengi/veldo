# VELDO-0046 proof

Release 1 revision 3 normal notification delivery. The historical title includes cursor
replay; the current criteria and History explicitly defer replay, reconnect and crash
recovery. Those functions were not implemented. Specification status and policy are unchanged.

## Implementation and integration seam

`control_notify.Delivery` uses in-process signals permitted by design R28. An explicit
store path, domain/repository/store identities, enabled consumer names and matching
handlers configure one authority-owned event loop. `execute` calls the existing store,
then queues its committed journal identity. Refused transactions and identical command
retries do not create new notifications. Other authority commit paths can call `notify`
with `hint(result)` after their store commit. The caller owns the loop and calls
`run_once()`; quiet waits never query the database. `close()` wakes a waiting loop.

The condition lock serializes queue insertion, the idle predicate and wake-up. Delivery
opens an independent read-only store connection and resolves command id, record digest
and exact sequence watermark before selecting handlers from stored event kinds. Supplied
payloads grant no authority. Handlers receive independent copies of the resolved event
and retain responsibility for their own domain authorization checks. Reservation records
also wake budget subscribers. Ordinary unavailable-store and handler-failure outcomes
are named; a failed handler is `unknown_outcome`, retained for a later subscriber-specific
retry (see the F02 review fix below).

Registrations cover settlement, assignment, dependency, completion and budget. Intake
and PM are optional explicit subscribers; PM observes the five core kinds and intake.
The suite compares all twelve installed producer/consumer pairs, exercises all of them,
and checks the five-pair installation without optional consumers. Missing enabled
handlers refuse installation. Observations join coordinates, event identity, watermark,
accepted versions and delivered consumers without copying transport or journal payloads;
metrics expose accepted/refused operations and queued work.

Both declared dependencies (the VELDO-0023 store and VELDO-0107 IPC foundation) exist.
This implementation uses the allowed in-process signal path and does not add another IPC
protocol. The VELDO-0047 authority loop and the domain handlers being built separately
are not implemented here: the narrow seam is `Delivery.execute`/`notify`, explicit
registrations and handler callbacks. The checks prove notification delivery to those
callbacks, not settlement, assignment, intake, PM or Telegram business behavior.

Canonical and installed module/scaffold copies are byte-identical. `init_scaffold._FILES`
installs the module; `REQUIRED_SUBSTRATE` does not list it because no validator loads it.
The suite uses the actual scaffold file writer to install the declared notification and
store assets in a temporary directory. The full existing packaging stage remains the
installation gate; every-pack qualification is not added to Release 1.

## Criteria and falsification

Suite: `scripts/suites/58_veldo_0046_notifications.py`. All rows run over a real SQLite
store with real OpenSSH Ed25519 journal signatures, independently verified. Temporary
keys, databases and modules are removed. Every mutation completes its assertion run;
exceptions, missing rows and worker timeouts do not count as detections.

| Criterion | Named row | Observed contract | Driven mutations (retained `.diff` files) |
| --- | --- | --- | --- |
| AC1 | `VELDO-0046 notify/committed-event` | Every enabled pair handles a committed event, with stored identity visible independently; precommit events and refused transactions cannot act. | `notify-before-commit` accepts the signer's uncommitted event payload; `notify-omit-committed-wakeup` drops the postcommit signal. Both turn this row red. |
| AC2 | `VELDO-0046 notify/event-in-the-gap` | Real loop barriers place a commit immediately before taking the idle lock and after entering the wait; both deliver, and a quiet wait performs zero reads. | `notify-check-outside-idle-lock` reads queue state before the transition; `notify-wait-without-queue-predicate` waits despite pending work. Both turn this row red. |
| AC3 | `VELDO-0046 notify/fabricated-event` | Every consumer receives stored identity/watermark; invented ids/digests, missing sequences and foreign coordinates refuse. Transport payloads cannot change the event. | `notify-trust-invented-event-identity` skips command identity resolution; `notify-trust-invented-event-digest` skips digest resolution. Both turn this row red. |

The mutation registry is `scripts/check_teeth_mutations.py`, finding 46. Its footprint
addition is recorded in the specification's prose History. `mutations.json` retains
actual baseline, no-op and mutant observations, source digests and named failing rows
from the full gate. The unmutated controls keep all three rows green. The omit-wakeup
mutation additionally turns AC2 and AC3 red because their positive delivery controls
also require ordinary commit notification. Bounded waits and joined threads ensure the
idle defects fail assertions rather than hang.

Reproduce targeted falsification with:

```sh
python3 -B scripts/check_teeth_mutations.py --finding 46
```

## Measurement and gate

The measurement driver in this directory executes two normal suite invocations (unit
and first-use integration), the mutation stage's shared baseline/no-op controls and
all six mutants serially, including interpreter startup and the shared preamble. This
is a conservative measurement of added test work, not a claim about whole-gate wall-time
difference under concurrent machine load. The real mutation gate runs workers in parallel.
See `measurements.json` for each measured duration and assertion observation.

Measured added serial test work: **7.451 seconds**, below the 60-second stop threshold.

The canonical gate started with a clean tree at `f66710cd1124e356731e359b5cb81a883f9cff0d` and exited 0.

```text
VELDO-0046 suite seconds: 0.325
selftest: 5681 passed, 0 failed
   mutated(spend_recorded) run: 5681 passed, 0 failed (320s)
mutations: passed registered=90 executed=90 rejected=90 workers=120 elapsed=61.698s
catalog: 8 run, 15 not-applicable (reasons on record), 0 waived, 0 undeclared
GATE: GREEN (f66710cd1124e356731e359b5cb81a883f9cff0d)
```

`gate-summary.json` retains summary lines and the SHA-256 of the full uncommitted gate
log. No full gate log, fixture credentials, private keys, bytecode, encoded/compressed
blobs or gate stamps are committed. The checkout's `.veldo/last_verify` and
`.veldo/events.jsonl` are restored before the evidence commit. Source/test commits and
this evidence are for independent review; this proof is not a self-approval.

## Review fixes: F01 watermark range

The supplied F01 capsule reproduced at `c645167`: an uncaught `OverflowError`, zero
callbacks, one committed notification pending. Before changing production code,
`notify/watermark-range` ran the same JSON hint followed by a signed real commit and
failed its assertion (29 passed, 1 failed). The fixed targeted suite passed all 30 rows.
`F01-tests.json` records these observations; the canonical gate is recorded below after
both review fixes. Targeted runs alone are not landing evidence.

Resolution now requires an integer watermark in `1..2**63-1` and returns `invalid_input`
for out-of-range values before opening SQLite. The row also drives zero, negative,
boolean and string inputs and confirms the valid maximum reaches journal lookup
(`missing_evidence`). The registered `notify-unbounded-watermark` mutation restores
F01; `notify-reject-valid-max-watermark` introduces a different boundary defect.
Both fail this named assertion, with exact diffs retained beside this README.

## Review fixes: F02 subscriber isolation

The F02 capsule reproduced at `c645167`: settlement raised, PM received nothing, and
pending work was zero. Before fixing dispatch, `notify/subscriber-isolation` failed its
assertion. The final regression row was also run against the exact module bytes read
with `git show c645167:.veldo/control_notify.py`; both F01 and F02 assertions were RED,
with no worker exception. `F02-tests.json` retains all observations and the source digest.

Each queue entry now retains its remaining subscribers. Dispatch records each failed
handler by `stopped_consumer`, attempts all other subscribers, then appends only failed
recipients to the queue for a later `run_once`. The aggregate receipt identifies
`failed_consumers` and successful `consumers`; any failure remains `unknown_outcome`.
Retries resolve the journal again, retain pending recipients through read failures,
and rotate behind queued events. Healthy subscribers are not retried. Retry pacing is
the caller's responsibility; callbacks must tolerate a retry after acting and raising.
This is in-process retention, not crash recovery or durable replay.

The row drives the capsule, reversed registration order, two failing subscribers,
repeated failures followed by recovery, temporary store unavailability, and later
commits during failure. Each subscriber ultimately receives each committed identity
once successfully. Exception text stays out of observations, and callbacks still get
independent journal-derived payloads. The targeted suite passes 31 assertions.

`notify-stop-after-handler-failure` reintroduces the original early return and lost work;
`notify-retry-successful-subscribers` independently retries healthy callbacks. Both
registered mutations fail `notify/subscriber-isolation`. All ten VELDO-0046 mutations
complete their assertions and are rejected. The four new diffs and per-finding test
records are retained here; the original proof records above remain historical.

## Review fixes: R1 ordering, R2 backoff, R3 first-attempt retention

A second independent check at `1dc0dde` found three defects, each with a reproduction
script. **R1:** a failing subscriber's retry was appended behind later events, so it
received `[2, 3, 1]`. **R2:** a permanently failing subscriber turned the blocking
`run_once()` into a hot loop (6,359 journal reads in 0.5 seconds while quiet, breaking AC2's
no-polling claim) and grew observations without bound. **R3:** a first attempt refused as
`service_unavailable` was dropped, because only retry items were requeued; the same
script also showed a callback `BaseException` dropping the event for every subscriber
not yet called. Fixed in commit order R3 (`0f4cc85`), R2 (`05ec4a9`), R1 (`4f7b193`).
Each commit added its row first and recorded it RED by assertion before the fix.

**Design.** Pending events stay in one queue in commit order. Each entry records the
subscribers still owed it; that set is unknown until the journal is first resolved.
A subscriber owed an earlier event is never offered a later one, so its retry goes
ahead of its later events. An unresolved event may be owed to anyone, so it holds every
subscriber behind it. A failing subscriber gets a per-subscriber delay; a failed
journal read gets a per-event delay. Both use bounded exponential backoff
(`retry_initial` 0.1 s, doubling, capped at `retry_cap` 30 s), and the loop waits for
the next due time on the same condition commits signal, so nothing reads the store
while quiet. Healthy subscribers keep receiving during another subscriber's delay.
A first attempt that meets an unavailable store is retained exactly like a retry;
other first-attempt refusals (invented or foreign hints) are still not events. An
interrupt propagates but leaves the event owed to the interrupted subscriber and to
those not yet called. `observations` is a bounded recent window (`observation_limit`,
default 1024) while `metrics()` counts every operation. The clock is injectable. This
supersedes the F02 section's "retry pacing is the caller's responsibility" and
"rotate behind queued events".

| Finding | Named row | Scenario | Registered mutations |
| --- | --- | --- | --- |
| R1 | `VELDO-0046 notify/subscriber-order` | The script's backlog and commit-after-failure orders, with one and three failures, plus an unresolved first event: each subscriber receives `[1, 2, 3]`, the failing one is never offered a later event early, and the healthy one is not held. | `notify-requeue-failed-at-tail` restores the defect; `notify-skip-head-of-line` drops the earlier-event hold. |
| R2 | `VELDO-0046 notify/retry-backoff` | The script's documented blocking loop over a real clock allows at most four journal reads in 0.3 s (expected: first attempt, a later commit, retries at 0.1 s and 0.3 s), still serves another subscriber, and exits cleanly. On an injected clock the reads fall exactly at 0, 0.125, 0.375, 0.875, 1.375 and 1.875 s (cap 0.5 s), each reached only by waiting on the condition; observations stay at the limit of 8 while 12 refusals are counted; unbounded settings are refused. | `notify-retry-without-backoff` restores the hot loop; `notify-uncapped-backoff`, `notify-retry-not-woken-when-due` and `notify-unbounded-observations` break the cap, the timed wake and the bound. |
| R3 | `VELDO-0046 notify/first-attempt-retained` | The script's flaky store failing one and three first reads, delivered exactly once; a callback `KeyboardInterrupt` propagates and both subscribers still receive the event once. | `notify-drop-unavailable-first-attempt` restores the defect; `notify-accept-before-callback` acknowledges before the callback returns. |

The final suite was also run over the exact `1dc0dde` module bytes (SHA-256 recorded):
every row completed its assertion with no worker exception, and the three new rows were
RED. `subscriber-isolation` was RED as well, because this change rewrote that row to
require the retry delay and to hold only the failing subscriber. The pre-existing
finding-46 mutations were re-anchored to the new dispatch and wait loop with the same
defects. All 18 finding-46 mutations complete their assertions and are rejected;
every retained `.diff` was regenerated from the current registry. The targeted suite passes 34
assertions in about 0.9 seconds. The serial measurement driver now reports 26.864
seconds for the suite and all 18 mutants, below the 60-second threshold.

The three reviewer scripts were rerun with their harness pointed at this worktree.
Because retries now wait, their non-blocking `run_once(0)` calls that expected an
immediate retry became `run_once(1)`; no BUG condition was changed. The adapted copies
still print all four BUG lines against `1dc0dde` and print none against the final code.
`R1-R3-tests.json` retains the RED and green observations, per-commit RED rows, script
output, measurement and mutation result lines. Targeted runs are not landing evidence;
the canonical gate is run by the lead.
