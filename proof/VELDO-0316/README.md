# VELDO-0316 implementation evidence

The implementation adds admission before account reservation, stable holds for waiting units, per-pool
need provenance, and the space binding in newly generated contracts. The factory Line reports space
waits with their numbers. Acceptance re-reads a bound hold in the dispatch transaction. Refused
preparations and cancelled dispatches release their hold; the receiver saves measured sizes at run end.

Read before implementation: CLAUDE.md, VELDO.md, the complete specification and build queue; design
sections 4.2, 4.3, 6.7 and 8.1; admission judge/admit, Runner.prepare/submit/retirement and Receiver.launch/
_space_end, dispatch contract validation and transition, Line.offer and the service's space bootstrap;
ledger hold/admit/release, mode authorization, measurement and pool declarations; the project declaration
reader; the existing dispatch, mode and run-finished suites; mutation materialization and inventory.
The service pair was added to the footprint because AC2 explicitly requires changing Line.offer.

The dedicated suite uses temporary Git, SQLite, a real Ledger, real reservations and dispatch transitions,
and signed mode commands. Eligibility, claim authority, configuration binding, containment, free-byte
readings and act prerequisites are fixture seams. A real child reads its committed acceptance at birth.
No test uses sleeps or speed-dependent deadlines; child-process hangs have a 120-second detector.
The receiver measurement row supplies its census/Signal result; existing run-finished tests exercise
those components together. Host Docker free-space acquisition is an injected reader, not a live capture.

The filesystem/engine pool arithmetic is unchanged. Admission calls serialize through the ledger's host
lock. Need selection reads the current project file; absent per-pool declarations use the maximum of
the last five exited runs in durable journal order, or defaults when five measurements are unavailable.
Coordination uses the installation's build default (the declaration schema has build/review/gate).
Stored contracts without space remain readable with their original digest. New Runner contracts always
include space, null when the installation has no enabled ledger or for repository-free conversations.

VELDO-0334 owns the admission-requested event and the freed-mark retry policy. This ticket preserves the
hold identity across offers and does not implement that later ticket's retry scheduler.

Validation logs will be recorded here. Selected selftest runs are diagnostics, not a full-gate verdict.
The canonical gate and independent review belong to the lead and are not run or claimed here.
The shared host-heavy wrapper is supplied by the build-queue repository; this worktree has no copy.

## Results

Implementation commit: b2105d64f8b21ac5f1fbf2b9715e0e7df9941c0e.
All six selected suites have zero failing rows: admission (20 ticket rows), dispatch (25), factory
loop (14), space mode (16), run finished (38) and end write (11). Each diagnostic exits 2 by the
selftest dispatcher's partial-run contract; the shared preamble adds 26 checks to each printed total.
The logs and checks.json preserve both the counts and the exit codes.

The gate-mutation coordinator executed finding 316: 11 registered, 11 executed, 11 rejected, zero
reuse, zero surviving workers. Every baseline and no-op control is green and the complete row
inventory survives every mutant. Three existing mutations were also rejected: exit without releasing
the hold, release before Signal, and omitting advised holds from held bytes. mutations.json and
regression-mutations.json are the exact coordinator receipts; mutations/ holds the exact 0316 diffs.
The new cases cover each declared falsifier plus other-held bytes, the waiting pass, oldest instead
of newest runs, declared needs, digest coverage, acceptance after release, and run-end measurements.

Lint passes (1247 Python, 40 shell files); template sync passes (325 pairs). All 410 existing and new
mutation anchors in the four changed modules resolve exactly once. Generated-file freshness passes.
Spec and proof validators pass. The personal-setup check against the starting commit finds zero;
its diagnostic paths are replaced by <home> in the saved output. The gate is not run and no
independent review or landing approval is claimed. Acceptance statuses remain pending that gate.

## Code map

- engine/.veldo/control_space_admission.py:63: pool boundary arithmetic; :75 serialized admission;
  :94 measured item totals; :111 finished-run order; :142 need precedence; :158 preparation; :203 metrics.
- engine/.veldo/control_launch.py:1707: Runner.prepare, admission before reservation; :1502: refused
  dispatch release; :2412: Receiver._space_end, measured bytes saved with hold release.
- engine/.veldo/control_dispatch.py:217: space validation with legacy compatibility; :361: transactional
  hold recheck; :548: its acceptance call. The existing digest covers the entire contract unchanged.
- engine/.veldo/control_service.py:3623: Line.offer, wired service ledger and waiting report.
- scripts/suites/157_veldo_0316_space_admission.py: the independent fragment and its fixture boundaries.
- scripts/check_teeth_mutations.py: finding 316 and the adjusted existing 0308 release-call anchor.
