# VELDO-0334 build proof

Implementation e1513571efd49290eef98d94091594d50d6b8356 on b8fb73f7. Built by Codex; no independent review is claimed.
All acceptance criteria remain pending the lead's aggregate gate and independent review.
The spec stays ready. No protected path was changed.

## Behavior

Factory admission sends its one admission_requested Signal before it finishes the first short
judgment. The retry is claimed on the hold before Signal, so a lost worker cannot send it twice.
The request selects deferred items on that pool and carries each through its original ending,
the existing rules, keep step and removers. A removal that frees enough permits immediate admission.
No new remover or safety exception was added.

Waiting answers are unchanged on unrelated offers: no free-space read, Signal or ledger write.
A positive removal delta, a released hold, and reconcile write the freed marks in the same
transaction as their cause. Image removals can also mark a backing pool when that pool's measured
delta is positive. Failed writes mark nothing. Optimistic version checks retry a conflicting
waiting-set snapshot or admission judgment; no clock or polling retry was added.

The service reads committed marks at existing journal and worker-pipe notifications and wakes
space. Requests invalidates a cached waiting answer only when the recorded hold is marked.
The new judgment runs on the serial space worker. A mark arriving before delivery of an older
waiting answer survives in the ledger and invalidates that answer on the next offer.

The existing one-shot gate and wrapped-run adapter interface is preserved. Factory prepare supplies
the Signal context. This ticket does not add a queue or a new protocol to those standalone callers.

## Rows and boundaries

18 ticket rows passed, with 26 shared checks: 44 passed, zero failed, partial exit 2.
VELDO-0316 regression: 25 own rows, 51 total passed, zero failed, partial exit 2.
Ledger regression: 31 own rows, 57 total passed, zero failed, partial exit 2.
These selected runs are diagnostic observations, not aggregate unit evidence or a landing decision.
rows.json lists every row; the final teeth receipt records their actual boolean observations.

AC1: one Signal on an initial offer and three more real FactoryLoop passes, including account
reset; its flag persists.
A real deferred scratch removal through Signal can admit immediately, while present scratch stays.
AC2: hand-freed fixture capacity remains ignored on a timer pass; repeated offers and public admit
read no free space and write nothing while the mark is clear.
AC3: removal, release and reconcile each set a mark and raise space; the mark clears after judgment.
The stopped-clock row uses a real Consumer child, real Signal and scratch remover, real worker pipe,
real FactoryLoop and Runner.prepare. With no timer advance, the freeing completion alone prepares
the unit and reserves its slot. Other rows cover pool isolation, nonpositive deltas, backing-pool
deltas, atomic refusal, a new hold during a freeing write, a freeing write during judgment,
a mark before delivery of an older answer, and replay of a release affecting multiple holds.
One compatibility row checks the existing standalone adapter's method signature.

Each fixture has its own SQLite store, state root and project directory. Free-space amounts,
eligibility, source resolution, process table, empty Docker answers and the scope's act prerequisite
outcome are fixtures. Only suite-created scratch is physically removed. Ledger unit rows also write
synthetic outcomes to exercise transaction behavior. No live Docker object or real-data path is
changed. No claim is made about installing the host process reader or live-engine qualification.

## Checks and teeth

All commands used nice -n 10. Validation, docs and template sync passed on the final implementation.
Generated files, lint and the space-boundary check also passed before the last defensive type check
of optional host facts in the outcome reader. checks.json records commands, timings and log digests.
After each run the runner checked actual process argument tokens for space supervise: none remained.
The known 86_veldo_0127 recapture and suites numbered 151 and above were not run or changed.
The lead's policy check and canonical verify command were not run.

Finding 334 ran last, at e1513571efd49290eef98d94091594d50d6b8356 with a clean worktree, jobs 2:
8 registered, 8 executed once, 8 rejected, zero reused, zero invalid, zero surviving workers.
Every baseline and no-change control passed. The three specification falsifiers were each applied
once: request on every pass, read on every pass, and mark without wake. Each turned its specified
row red. The other five cases exercise mark setting, clearing, a stale judgment, stale answer
caching and loss of the original ending. falsifiers.json keeps each actual red row and mutation.

The tracked-file digest before and after teeth was 4921ce47625bfda7f37ab354e3bf54a3db704211882fe46ccd55b7768c8a9bdc.
The worktree was clean both times. No worktree writes occurred during teeth, and no test ran after
it. This proof was written only after the receipt returned. The full receipt is below 1 MB;
all other artifacts are small summaries. Full transient logs and exact applied diffs remain in
/tmp/veldo0334-results on the build host.

## Review handoff

Run ./scripts/verify.sh through the lead's gate lock. The proof manifest intentionally records
pending criteria and no aggregate evidence claim. Roll back by reverting the implementation commit;
stored holds and their recorded numbers remain data, with no deletion or migration involved.

## Fix round 1 (2026-11-16)

After the independent review (verdict FIX) the branch was rebased onto the fixed VELDO-0316 (a03b9b73)
and six findings were answered, one commit each. fix-round-1.json is the record; the sections above
describe the first build and are superseded where they differ. Fixes by Claude, a different builder; no
independent review of this round is claimed.

Rebase: one conflict, Requests.prepare, resolved keeping both rules. An answer with no hold is returned
once and judged afresh; a waiting answer whose hold is marked freed is dropped. The VELDO-0316 reconcile
releases through Ledger.release, so marks and the space wake follow it.

1. Report mode never blocks. The claim before Signal writes advised with retry_asked in one write for a
   report-mode scope, and a refused Signal is not raised. Rows fix1/report-refused-signal (refused
   Signal and a worker lost inside Signal) and fix1/act-refused-signal.
2. A release marks freed only on pools where an admitted or advised hold still held bytes. Rows
   fix2/waiting-release-no-mark and fix2/release-marks-per-pool; teeth case space334-waiting-release-marks.
3. Three unrelated passes through a wired Requests: no consumer submit, no free read, no journal
   record. Row fix3/requests-unrelated-passes; the reviewer's M4 is teeth case
   space334-requests-resubmit-every-pass.
4. Mark set, one failing free read, the next offer judges again and clears the mark. Row
   fix4/failed-read-rejudges; teeth case space334-failed-judgment-kept.
5. Boundary, recorded in the spec History: gate and wrapped runs do not send admission_requested yet.
   The one-shot admit callers carry no Signal context and the gate wiring answers ledger_unreachable
   until VELDO-0323, so the path is unreachable today. Follow-up: VELDO-0323, and VELDO-0325 at the latest.
6. The lead accepted the footprint widening (Signal and its copy) on 2026-11-16; the owner approves at
   landing.

Rows: 24 own rows, 50 with shared checks, zero failed, partial exit 2. VELDO-0316: 29 own rows, 55
passed, zero failed. Fast checks passed: validation, docs, template sync, lint, generated, space boundary.

Teeth ran last on a clean worktree at af65a0be, jobs 2, tracked-file digest equal before and after.
Finding 316: 9 registered, 9 executed, 9 rejected. Finding 334: 11 registered, 11 executed, 11 rejected.
Zero reused, zero invalid, zero surviving workers. falsifiers.json, teeth-receipt.json and teeth-run.json
are this round's finding 334 run; fix-round-1.json summarizes both findings. checks.json is the first
build's record. The space ledger suite, suites 151 and up, the policy check and the canonical verify
command were not run.
