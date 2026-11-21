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

Implementation commit: 7a42f196 (fix round 1; the original implementation was b2105d64).
All six selected suites have zero failing rows: admission (25 ticket rows), dispatch (25), factory
loop (14), space mode (16), run finished (38) and end write (11). Each diagnostic exits 2 by the
selftest dispatcher's partial-run contract; the shared preamble adds 26 checks to each printed total.
The logs and checks.json preserve both the counts and the exit codes.

The gate-mutation coordinator executed finding 316: 16 registered, 16 executed, 16 rejected, zero
reuse, zero surviving workers. Every baseline and no-op control is green and the complete row
inventory survives every mutant. Three existing mutations were also rejected: exit without releasing
the hold, release before Signal, and omitting advised holds from held bytes. mutations.json and
regression-mutations.json are the exact coordinator receipts; mutations/ holds the exact 0316 diffs,
regenerated at the fix commit (only line numbers moved for the eleven original cases).

Lint, template sync, generated-file freshness and the spec validator pass; the personal-setup check
finds zero, its diagnostic paths replaced by <home>. The gate is not run and no independent review
or landing approval is claimed. Acceptance statuses remain pending that gate.

## Fix round 1 (review: one medium, three lows)

- Orphan hold after a crash (medium). prepare() commits admitted or advised before the Runner reserves
  and writes the dispatch; a service killed between the two left a counted hold that nothing named, so
  the unit was refused with space_hold_state on every offer and its need stayed held. The factory
  loop's start (the existing start sweep, beside sweep_runs) now calls Runner.recover_holds, which runs
  control_space_admission.recover under the admission lock: each admitted or advised hold of this
  domain and repository that no dispatch record binds is released through the ledger, and the result
  is logged under holds_recovered in the runs_swept record. The unit's next preparation places the next
  generation and is judged again. Waiting holds and dispatch-bound holds are kept. No timer.
  Rows recovery/orphan-released and recovery/next-offer; falsifiers space316-start-keeps-orphan-holds
  (both rows red: the hold stays admitted and the offer is refused) and space316-recover-releases-bound.
- Five-run boundary (low). The history row's first five runs are small, so a need measured after four
  runs admits early; ac4/measured-at-five pins the other side. Falsifier space316-measure-after-four.
- Legacy history (low). Row ac4/legacy-history: five runs exited without a space binding, with measured
  items, give a measured need, and four give the default. finished()'s docstring now says so.
  Falsifier space316-legacy-history-ignored.
- Metrics (low). FactoryLoop.status carries space_admission (per pool free, floor, held; holds
  admitted, waiting, advised), None without an enabled ledger. Row metrics/exposed; falsifier
  space316-metrics-unexposed.

## Code map

- engine/.veldo/control_space_admission.py:63: pool boundary arithmetic; :75 serialized admission;
  :94 measured item totals; :111 finished-run order; :144 need precedence; :160 preparation;
  :217 start recovery of orphan holds; :248 metrics.
- engine/.veldo/control_launch.py:1715: Runner.prepare, admission before reservation; :1707: recover_holds;
  :1502: refused dispatch release; Receiver._space_end, measured bytes saved with hold release.
- engine/.veldo/control_dispatch.py:217: space validation with legacy compatibility; :361: transactional
  hold recheck; :548: its acceptance call. The existing digest covers the entire contract unchanged.
- engine/.veldo/control_service.py: Line.offer, wired service ledger and waiting report; :4213
  FactoryLoop.start's hold recovery; :4366 the space_admission status.
- scripts/suites/157_veldo_0316_space_admission.py: the independent fragment and its fixture boundaries.
- scripts/check_teeth_mutations.py: finding 316 and the adjusted existing 0308 release-call anchor.

Saved diagnostic logs trim trailing whitespace. Mutation diffs use zero context; the exact before/after
content digests and all control and mutant observations remain in the unchanged coordinator receipts.
