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
