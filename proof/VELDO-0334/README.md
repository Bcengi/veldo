# VELDO-0334 implementation proof

Built on VELDO-0316 at 1f325393. Full gate and independent review remain with the lead.

Admission records its one request, retries deferred items on the short pool through Signal,
and returns a recorded wait without reading space until a freeing write marks it. Removal,
release and reconcile journal the mark atomically; the service consumes those transitions
as the space wake source, including commits from its child worker. Admission uses the
version it judged so a later freeing write cannot be silently cleared.

The footprint adds Signal and its synced copy because admission requested was not an
existing Signal event. It retries the deferred item's original ending action through the
existing registry, probes and removers. No lifecycle table is changed.

Read before implementation: repository CLAUDE.md, VELDO.md, engine instructions, policy,
the whole spec, the wave-2 build queue and design sections 4.3 and 6.7. Entry points traced
in the starting tree: control_space_admission.py:76,155; control_space.py:1086,1248,1302,
1369,1382,1389,1424,2093,2126,2288,2308,2331,2340; control_service.py:1715,2245,2655,
2669,3629,4290,4496; control_launch.py:779,1736,2458; gate_space.py:239;
control_space_signal.py:210,291,347; control_space_reconcile.py:729;
control_space_consumer.py:118,129; control_store.py:616-649. Paths are relative to
engine/.veldo except gate_space.py (engine/scripts). The 0316 suite, suite registries,
mutation drivers and dispatcher were read as the testing contracts.

The new suite uses real SQLite, signed mode commands, Git, Runner, FactoryLoop, Signal,
filesystem removal and a child worker. Eligibility, free-byte readings, the process table
and act prerequisites are fixture seams. A stopped fixture clock and worker pipe readiness
synchronize the integration rows; 120-second deadlines only detect hung subprocesses.

Selected selftest exit 2 means all selected rows passed, but is deliberately not a full
unit-gate success. The first diagnostic caught a fixture syntax error; the final suite
log records its correction. The mutation controls supply the criterion evidence; all criteria remain pending the lead gate.

Final diagnostics: 13 affected suites have zero failed rows, including the installed factory
loop, reconcile, gate admission, run end, ledger, mode, Signal and removal suites. These
selected selftest runs are diagnostics only, never aggregate unit verification.

The final mutation run rejected 21/21 cases (finding 334 and all of finding 316). Three
older cases were rejected in regression-mutations.json; that stage also correctly reported
one invalid no-op control because an isolated admission copy lacked its new sibling modules.
Registering siblings for both affected mode cases resolved that: mode-mutations.json rejects
both with green baseline and no-op controls. Thus 26 distinct cases have valid red/green
results, itemized in mutation-summary.json. No surviving workers and no reused results.
Every recorded mutation source digest was compared with the final production file.

Corrections during verification: the first suite diagnostic caught a fixture syntax error;
the first mutation attempt caught two incorrectly quoted production-copy anchors; the installed
factory-loop suite caught dynamically composed import names that the closure scanner cannot
resolve. Literal imports fix the installation, whose suite then passes. The ticket-ending
suite's exact call count now includes the additional journal-hint entry point. Existing
new-project and Signal mutation anchors were updated without changing their target defects.

Proof paths in captured output are redacted to <checkout> and <home>. Structured receipts
keep all observations and source digests; their duplicate JSON lines are omitted from text
logs. The shared host-heavy wrapper serialized every test and mutation run. No test in the
new suite sleeps or asserts a speed bound; all hang detectors are at least 120 seconds.
The canonical gate was not run and no independent review is claimed.
