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
log records its correction. Mutation results will supply the criterion evidence.
