# Round 11 crash and event corrections

This evidence is limited to VELDO-0125 Linux logic and synthetic macOS interfaces.
The canonical gate and native Mac/SSH qualification remain with the reviewer.
Historical proof files are unchanged. New revisions of the lifecycle and process
fixtures carry the changed clock seam and blocking-exit model.

Slot writes use a durable write-ahead live index. Startup and every admission
reconcile indexed candidates against slot records, removing missing and retired
records and correcting their states. Only new protocol-2 `starting` records can
be safely retired before launch intent. Legacy `starting`, `launching`, and
`unknown` records retain capacity because bootstrap may already have happened.
The new `launching` record precedes bootstrap; an uncertain launch is never
silently retried or freed. Migration reads historical records once at supervisor
construction. Upgraded admissions inspect only potentially live records.

Crash rows interrupt both sides of every write from request creation through
engine release, then exercise restart and same-process reconciliation. Retirement
rows interrupt both local and authority retirement before/after index removal and
admit new work without a separate status or authority repair call. Migration rows
seed 500 historical slots before constructing an upgraded supervisor and forbid
history reads or enumeration during its first admission and subsequent startup.

SIGKILL rows cover a receiver and a drain that own active entries. The next worker
start replays them through the existing execution lock. Busy live owners remain
active and do not acquire a delivery timer. Recorder and finalizer failures log
to stderr and stop the drain. Launchd captures stderr in delivery-errors.log.

The supervisor blocks on the wrapper's NOTE_EXIT, bounded by the runtime deadline
or a stop-stage deadline. Startup files use directory vnode events registered
before checking the file. The wrapper reaps its child with blocking waitpid in a
thread and waits on that exit event; descendant exits use NOTE_EXIT, with scans
only after exit events or shutdown deadlines. There are no heartbeat writes.
Legacy profile heartbeat fields remain accepted so existing qualifications do
not change solely because the health timer was removed. The former simulated
heartbeat-loss row still requires bounded termination, now at the runtime cap.

The release/evidence row checks that an unauthorized release stays in .waiting
without repeated status calls. The operator-wait row patches only the worker's
sleep and runs a real subprocess timeout wait inside that patch, so a return to
process-wide time.sleep patching fails deterministically.

Commands use `python3 scripts/selftest.py --suite 106_veldo_0125_routing` and
`python3 scripts/selftest.py --suite 105_veldo_0125_relay`. Selected suites report
PARTIAL and exit 2 when all selected rows pass; this is not a gate claim.

Initial validation logs are retained, including failures and an interrupted
invocation. The first used a temporary directory under .veldo and correctly hit
sandbox protected-path refusals; /tmp is not writable in this run. Later runs use
a temporary directory outside .veldo. One corrected rerun was mistakenly started
before the preceding suite finished and was stopped immediately on detection;
its partial output is retained as routing-corrected.log and is not evidence.
Subsequent validation and falsifier invocations run serially.
