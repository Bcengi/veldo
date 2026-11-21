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

## Fix round 1 (2026-11-21)

The independent review returned FIX with three findings. Code commit 82b7db04, on 870c43ea.

F1 (medium-high). A release, a removed outcome with freed bytes and a reconcile commit against the
versions of the holds waiting on their pools, read before the store transaction. A hold changed or
placed by another writer in that window refused the whole command stale_version: a finished run's
hold stayed admitted, a removed item stayed unrecorded. Ledger._send now reads the waiters again and
sends the command again: compare-and-swap on the store's own versions, at most FREEING_ATTEMPTS (8)
attempts, no clock and no wait. Each refused attempt is one committed write of another writer. A
stale_version while the caller's own entity moved is still the caller's refusal and is sent once.
A caller's command id and a packet's nonce are kept: a refused attempt commits nothing. The review's
optional point 2 (leave a hold placed later unmarked) was not taken: a hold placed and judged inside
the window of a release would then wait unmarked.

F2 (low). A refused admission requested Signal returned before the answer was written, so a
report-mode hold stayed on the reserved wait. The hold is now judged all the same and its scope's
answer written (advised in report mode, waiting in act mode); the answer names the refusal as
retry_refused.

F3 (low). The space wake is raised only for a waiting hold that carries the mark. A released hold
that still carries an older mark wakes nobody.

Rows added to suite 158 (14 to 22 rows). The racing writer is a second Ledger on its own store
connection, as the forked space worker is, and it commits inside the first writer's own store call:
an event, never a delay. No row sleeps or reads a clock.

| Row | Finding | Falsifier (mutations/) | Red because |
|---|---|---|---|
| race/release-resent, race/removal-resent, race/reconcile-resent | F1 | space334-freeing-without-resend | the command is refused stale_version, the hold stays admitted or the item unrecorded |
| race/own-version-refused | F1 | space334-resend-when-own-version-moved | the caller's stale command is sent a second time |
| race/resend-bounded | F1 | space334-resend-unbounded | the command commits after more attempts than the bound |
| report/signal-refused-advised (and act/signal-refused-waits) | F2 | space334-signal-refusal-leaves-waiting | the report-mode hold stays waiting and no run starts |
| ac3/released-mark-no-wake | F3 | space334-wake-for-released-mark | releasing the marked hold raises a space wake |

Runs of this round, all on a scratch clone of 82b7db04 through the shared host-heavy wrapper in one
batch: the 13 affected suites (regressions.json, the suite logs here; every one 0 failed, exit 2 by
design) and one mutation stage of 31 cases, 31 rejected, 0 reused, no surviving worker
(mutations-final.json, itemized in mutation-summary.json): the 15 cases of finding 334, the 11 of
finding 316, and the five older cases whose anchors or sibling modules this ticket touched.
mutations-final.json replaces the earlier 21-case receipt. regression-mutations.* and
mode-mutations.* are the first round's receipts, kept as history: their five cases are in the new
receipt against the current sources. A first wrapper attempt waited two hours for a slot and was
stopped by its time limit before anything ran; the second attempt ran the batch. Before it, each new
falsifier was also driven once by hand on a second scratch clone, with the same red rows.

Still not run: the canonical gate (the lead's). No independent review of this round is claimed.
The older paragraphs above describe the first round; where they give counts (13 suites, 21 and 26
cases, 40 rows) the figures of this section are the current ones.
