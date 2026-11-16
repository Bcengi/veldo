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
