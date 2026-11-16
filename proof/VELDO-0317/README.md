# VELDO-0317 proof

Implementation: 41610308d2b7dbd91a89388734c52d19fd8b42eb. This is builder evidence, not independent review or aggregate verification.
The manifest leaves AC1 to AC4 pending the lead's canonical gate and review.

The receiver searches stdout and stderr incrementally, including split errors and the final drain.
An unsuccessful end with that error reads each pool before the census and Signal, in report and act
modes. The dispatch transaction records the classification and free/floor snapshot. Confirmed space
failures refund the attempt atomically and release the unit for admission. The first unconfirmed end
suppresses the verdict and repeats once; the repeat records its own failure. Dispatch sequence and
end sequence preserve ordering when refunded attempts have the same number or clocks stand still.
Rule 5 retains the recorded worktree, including a review scratch tree, and holds its containing
repository. The next prepared payload identifies the worktree and its uncommitted changes.
Two consecutive environment failures record an andon and block further preparation. The factory
queues its notice to the existing owner inbox on the space worker. Delivery failure does not permit
another dispatch. Space disposition and resumption belong to later tickets.

## Rows and fixture boundaries

18 ticket rows passed, with 26 shared checks, zero failures, partial exit 2. rows.json maps every AC.
The suite uses real temporary SQLite, dispatch transitions, reservations, Runner preparation,
Receiver reap and finish, a real Python child, real Git worktrees, Ledger, Signal, keep, removers,
and the serial Consumer. Pool free bytes, eligibility, source binding, the process table, and the
owner inbox delivery seam are fixtures. The owner notice row stores the child PID on the reopened
SQLite connection and observes the completion wake. No live engine or other account's processes
are used. No production data, protected containers, volumes, or images are touched.

The five adjacent suites passed: admission 25 rows, waiting 18, dispatch 25, run-finished 38,
factory 14. Each also ran 26 shared checks. Validation, docs, template sync, space boundary and
lint passed with nice -n 10. checks.json contains the final summaries and process audits.
The first two diagnostic runs failed in fixture setup because temporary paths were outside the
fixture's declared roots; the fixture was corrected to use its declared scratch and worktree roots.
No production root policy was relaxed. Earlier and final checks left no own supervisor alive.
Suite 86_veldo_0127 was left alone. No suite numbered 151 or above, policy check, or full gate ran.

## Falsifiers

Finding 317 ran last, on the committed implementation, with two workers and nice -n 10.
Five registered, five executed once, five rejected, zero reused, zero invalid results, zero surviving
workers. Every baseline and no-change control was green. The four specification falsifiers each
turned its named row red: charge the failed attempt; classify by text alone; remove the failed
worktree; repeat without a bound. A fifth removes the kept-work message from the next brief.
The unbounded mutant runs additional real fixture dispatches; the row observes more than two.
The removal mutant passes through the real keeper and remover, so the row finds the edit absent
from its worktree even though the snapshot protects the underlying work.

The tracked-file digest before and after teeth was 702c853cc88c9c106db0658e74ff27169a719dbdd4af41e82c4d2f9d319b8c16. The worktree was clean both times.
No worktree write occurred during teeth. No test or check ran after it. Only this proof bundle
was written after the result returned. Each proof file is below 1 MB. Full transient logs and exact
mutation diffs remain in /tmp/veldo0317-build; the full receipt and compact red-row summaries are here.

The verify command is ./scripts/verify.sh, to be run by the lead through the gate lock.
Rollback: revert the implementation. Existing retained worktrees, journal records and snapshots stay.

## Fix round 1 (review of f8a66f9d, verdict FIX)

Implementation after the round: 4b4f8ebbe6c98a6cb5bc9ffee56a643d14651e43. Builder evidence of the fix round, not independent review.

F1 (high). A refunded rerun asks under the attempt number of the run that just ended, and found that
run's hold still admitted until its receiver released it. Prepare now passes over an identity a
dispatch record carries, under the admission lock, as reconcile does, and judges a fresh hold with a
free read. This was chosen over keying the hold by dispatch sequence, which would change the hold
identity in the contract, the Requests key and reconcile's leaving keys; the carried test is one
condition where the hold is handed out. The factory line also spends its kept answer once a dispatch
record carries its hold, since a fast end could otherwise be answered from the service's kept answer
without reaching prepare. Rows fix1/rerun-before-release (the reviewer's P1: exit committed, rerun
before the receiver's release, answer space_wait:host, a free read, one dispatch record, and after the
release the rerun is admitted on its own hold) and fix1/spent-answer.

F2 (medium). Only a delivered owner notice is kept. A failed delivery is reported once and dropped,
and the pass after that submits it again. Row fix2/andon-redelivery (the reviewer's P2): one failing
delivery, then a healthy inbox, exactly one notice, two worker completions, no third run.

F3 (low). The recovery brief names the no-space ends since the unit's last completed dispatch. The
unit's ends and rule 5's kept worktrees are selected in the store (by the quoted unit, by the no-space
classification), so other dispatch records are not parsed on each judgment; SQLite still walks the
dispatch rows, there is no new index entity. The kept worktree stays pinned after recovery: the spec
History records that releasing it is VELDO-0327's. Rows fix3/brief-ends and fix3/bounded-scan.

F4 (low). The spec History records that the lead accepted the footprint widening on 2026-11-16.

Rows: 23 ticket rows passed, 26 shared, zero failures, partial exit 2. Suites 150_veldo_0334_space_wait
(24) and 150_veldo_0316_admission (29) passed, and validation, docs, template sync, space boundary and
lint passed, all with nice -n 10; those ran at d4410d55, before a repair of the F1 row that changed
only the 0317 suite file, and the 0317 suite ran again after it. The three other adjacent suites of
the build (dispatch, run-finished, factory) were not rerun in this round. The reviewer's probe file was
not run; the two rows above are its P1 and P2. No own supervisor survived any run.

Teeth: finding 317 ran last on the committed tree, two workers, nice -n 10: 9 registered, 9 executed,
9 rejected, 0 reused, 0 invalid, 0 surviving workers. Four are new: the rerun takes the carried hold
(F1), the kept answer outlives its dispatch (F1), a failed notice is kept (F2), the brief never ends
(F3). A first run at d4410d55 failed with missing_target: under the F1 mutant the F1 row raised and
removed the later rows. The row was repaired (4b4f8ebb) and the whole finding was run again.
The digest of git ls-files -s before and after was 318e26d278312c756153e2c6a4ea1b6515e8136a7279b8c35eabe5cb684cdd3b; the worktree was clean both
times. Nothing ran after teeth; only this proof bundle was written. Logs are in /tmp/v317-fix1.
