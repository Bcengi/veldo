# VELDO-0316 proof

Implementation: aa1c5560. Test robustness fix: 42ea5a5a. This bundle describes the latter tree.
The four ACs remain pending the lead's aggregate gate and independent review.

Runner.prepare asks admission after its sweep and eligibility checks, before reserving an account.
A waiting answer carries pool, need, free, held and floor. The factory lists it under waiting.
Report mode admits or advises and starts the run. Contracts carry hold and needs in their digest;
acceptance re-reads the hold. Stored legacy contracts keep their original digest.
Needs come from the current project file, then the maximum of the last five finished dispatches
of that project and station with measurements for that pool, then the installation default.
An unmeasured finished run leaves the pool on its default. Declared zero remains a declaration.

Initial factory judgments run as coalesced tasks of the existing serial Consumer. Completion wakes
the factory. A repeated waiting offer reads its recorded answer without reading free space or
writing another hold. No freeing-event retry, Signal admission request or full-pool outcome
classification is added: those belong to the later tickets. control_service.py and its synced copy
were added to the ticket footprint for the factory branch explicitly cited in design 6.7.
The admission lock also serializes existing gate and wrapped-run callers using this module.

25 targeted rows passed, plus 26 shared preamble rows. The selftest selector deliberately exits 2:
it is a diagnostic run and does not establish aggregate unit or integration verification.
rows.json lists every row; teeth-receipt.json records baseline, no-op and mutated observations.
The suite uses a real temporary Ledger, SQLite, reservations, dispatch transitions, serial child
worker and a receiver seam that accepts through Dispatches and starts a real short process.
Eligibility, source resolution, configuration binding and accepted mode setup are fixture inputs.
No live Docker engine or other account's processes are read. Engine free-space behavior is exercised
through the existing injected reader, not a real engine. The pool defaults are applied per configured
pool. The metrics function exposes pool free, floor and held, and the three active hold counts.

The final teeth stage ran last on a clean worktree, with one worker at a time and no worktree writes
while it ran. All eight mutations were executed once in that stage and rejected, with zero reuse
and zero surviving workers. The four ticket falsifiers are ignore-floor, admission-at-acceptance,
block-report and measured-after-one. Additional mutations cover factory classification, accepting
a released hold, the completion wake and releasing another preparation's winning promise.
The first teeth stage is retained in earlier-teeth.json: six rejected and two invalid because a
floor-mutant test exception and a report-mutant conditional removed baseline rows. The test fix
keeps the checks runnable and makes the digest fixture independent of report-mode admission.
Earlier exploratory suite runs also exposed fixture setup mistakes (expect argument order, the
empty YAML spelling, missing claim setup, policy command reuse and creator spelling); none is
presented as a passing verification result.

Validation, docs hygiene and template sync passed on the final tree. Generated-file and lint checks
passed before the four-line test-only fix. Every recorded run was nice -n 10 and followed by an
exact argv check for space supervise processes; none survived. The existing mode suite has 14 red
rows on both this change and the unchanged base; mode-baseline.json records the comparison.
Suite 86_veldo_0127, suites numbered 151 and above, the full gate and the policy checker were not run.
The lead owns ./scripts/verify.sh through the gate lock, independent review and landing approval.

No removal primitive was added. The existing keep steps and removers remain the removal path.
No real-data database volume, protected data, engine image or minio image was touched. The spec stays
ready. Rollback reverts this implementation; persisted contracts and their digests are not rewritten.

## Fix round 1 (after the independent review, verdict FIX)

A different builder made this round. fix-round-1.json is its record; rows.json and targeted-run.txt
are its final run: 29 rows passed, 0 failed.

F1: Requests.prepare keeps only an answer that carries a hold. An answer with no hold is returned
once and dropped, and the next pass submits the judgment again, in act and in report mode.
F2: the space worker releases dispatch holds that are admitted or advised, that no dispatch record
carries and that have no live offer: one task at service start, and one when an answered offer is
not asked again in a line pass. The service loop only takes the snapshot and queues the task.
F3: ac1/concurrent holds each preparation inside judge until the other arrives or two seconds pass.
Under the lock the second never arrives; without it both are admitted and the row is red. The
lock-less mutant is the ninth teeth case.
F4: a no_account refusal keeps the admitted hold, so repeated passes use one hold and write nothing.
The ac2/reservation-failure row now uses another reservation failure for the release.

Teeth, run last on a clean tree: 9 registered, 9 executed, 9 rejected, 0 reused, one worker at a
time. An earlier stage of this round was invalid (0 rejected, every baseline failed at setup) because
the first barrier needed a shared semaphore that the confined teeth worker cannot create; it is
recorded in fix-round-1.json and is not a passing result. The files that describe the tree at
42ea5a5a (teeth-receipt.json, falsifiers.json, checks.json, sources.json) are kept unchanged.
Not run in this round: the full gate, suites 151 and up, suite 86_veldo_0127, the policy checker.
