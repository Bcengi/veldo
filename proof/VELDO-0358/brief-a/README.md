# VELDO-0358 brief A: the suite runtime

Scope: revision-notes section 3.2, brief A. Criteria AC1, AC2, AC3, AC4 (fixture suites only) and AC5 for
the suite process. Files: scripts/suites/support/waits.py, holders.py, ports.py, scripts/suites/shared.py,
scripts/selftest.py, scripts/suite_labels.py, the fixture suite 157_veldo_0358_suite_runtime, and this
brief's own block of scripts/check_teeth_mutations.py. The suite's entry was added to
scripts/suites/manifest.json and requires.json (no brief owns them; every new suite needs its entry).

## What was built

| Component | Where | What it does |
| - | - | - |
| Hang constants | waits.py | WAIT_HANG_SECONDS 600, PROCESS_HANG_SECONDS 3600, HEAVY_CHILDREN (design 6), as the contract fixes |
| C1 wait primitive | waits.wait | done, impossible (terminal condition) or hung. Hung is never returned: SELFTEST HUNG with row, wait name and source line, the last reading of both conditions and the stack file; every thread's stack written; SELFTEST NOT RUN for every row not reached; the process exits red. A wait with no source is refused (it could only wake on the clock) |
| C2 sources | waits.py | Pidfd, Readable, PathAppears (inotify on the directory or on the nearest existing ancestor, moved down on each creation), Store (inotify on the -wal file; on each wake the writer's WAL write lock is awaited with a blocking OFD read lock on SQLite's lock byte before the condition is read, because a commit is several writes and is visible only after the writer updates the index, so the last write's wake could otherwise read too early and never wake again), CgroupEmpty (cgroup.events, POLLPRI) |
| Stamp | waits.Stamp | ordering, at_least(start, seconds), iso() for data; no subtraction |
| C3 latch holder | holders.py | blocks on a pipe whose write end only the test holds; ended() waits on its pidfd with "the holder holds a write end of its own latch" as the terminal condition (it could then never see the latch close) |
| C11 port holder | ports.py | lifted from engine/ui/e2e/harness.py reserve_port |
| shared.py | wait_for, ForkFlag.wait, ForkBarrier.wait | calls into the primitive; the caller's former bound is kept in the report as data and bounds nothing. A caller with no source is read on waits.LegacyInterval until its wave converts it (shared.wait_for has two callers: 38 and 62) |
| C5 rows | shared.expect, waits.row_event | each row is a progress event and is marked reached |
| C6 watchdog | waits.Watchdog, armed by selftest.py | ends the process only after the process hang bound with no row starting or ending; one thread waits for the bound since the last event (it wakes once per bound, not per row); faulthandler's timer, re-armed at that thread's wakes to one bound beyond, writes the stacks and exits if the interpreter is stuck. With a supplied clock (its own test) the time between events is judged at each event on that clock |
| C7 residue | waits.residue, selftest.py | after each suite: threads alive, children not reaped or running, listening sockets that were not there before it, as a failed row residue/<suite> naming each |
| C18 opened-files record | selftest.py | an audit hook on open and import; per suite, every path under scripts/ and proof/ (bytecode caches excluded); what shared.py opens is under "shared". Written, merged under a file lock, to the path in VELDO_OPENED_FILES; also written before a hung process exits |
| Heavy child | waits.run_heavy, suite_labels.capture | no total bound; ended (SIGABRT first, so a -X faulthandler child writes its stacks) only after the process hang bound with no output. suite_labels refuses a hung subject as SUBJECT_HUNG and no longer has its 1800 s bound |

Contracts kept as written: the result lines begin SELFTEST HUNG and SELFTEST NOT RUN; FAIL and pass lines
are unchanged; the record is one JSON object, suite name to sorted repository-relative paths.

For brief B and D: the record's path is whatever the gate puts in VELDO_OPENED_FILES (selftest.py writes
nothing when it is unset). Hung exit status is 1 (waits.HUNG_EXIT_STATUS). VELDO_HANG_DIR, when set,
holds the stack files.

## Rows and their falsifiers

Suite 157_veldo_0358_suite_runtime drives each criterion through the real dispatcher (a fixture
repository holding copies of selftest.py, run_scope.py, shared.py and the support modules under test,
with .veldo linked) over fixture suites the suite writes.

| Row | Criterion | Mutant (finding 358, brief A block) | Result |
| - | - | - | - |
| waits/three-outcomes | AC1: done, impossible, hung with the bound at 2 s through hang_bound_for_test; the hung row's name and source line, later rows (also of the next suite) NOT RUN, red exit, stack file naming the line; shared.py has no clock, sleep or timed select | wait358-expiry-reads-false | rejected, assertion |
| waits/no-idle-wake | AC2: one waiter process per source, two events each (pidfd, readable, path, store, cgroup) and a path made two levels deep after the wait began (three events); switches made while waiting at most the events | wait358-path-polled | rejected, assertion |
| holders/ends-with-its-test | AC3: a released holder ends; a holder whose test process is SIGKILLed ends; this suite has no sleep | wait358-holder-outlives-test | rejected, terminal (the holder's own write end) |
| residue/named | AC4: fixture suites leaving a thread, a running child and a listener each fail residue/<suite> naming it; the clean one passes | wait358-threads-not-counted | rejected, assertion |
| watchdog/progress-not-total | AC5 (suite process): a suite blocked in a read outside the primitive, bound 3 s: ended, SELFTEST HUNG naming the read's line, stacks in the file and on stderr; a three-suite leg on a supplied clock, rows one supplied second each, 9 in total: green, nothing ended | wait358-watchdog-silent, wait358-watchdog-total-time | both rejected, assertion |
| record/opened-files | C18: a file loaded by a computed path is recorded for its suite | (none registered; not a criterion of this brief) | green |
| ports/held-until-bound | C11 | (none registered) | green |

mutants.txt is the driver's own worker run for each case in baseline, no-op and mutant mode, with the
diff that shows each mutant landed and the failed row's detail; drive_mutants.py.txt is the script.
All six: baseline and no-op green, mutant red on its target row.

How AC2 counts: the waiter runs alone in its own single-threaded process. Its done condition records the
thread's voluntary context switches as each reading begins and ends and writes a token to the test. The
switches between the end of one reading and the start of the next are the wait's own (one poll block per
event: measured equal to the events in every run); a reading's own file reads and the store's wait for the
writer's lock are reported apart (in_readings, lock_switches). The test causes each event only after the
token of the reading before it and after hashing 384 MiB, a fixed amount of work (about 0.1 s on this
host), so a waiter on any timer shorter than that wakes several times per gap: the 20 ms mutant made
3 to 8 waits where 2 or 3 were allowed. Nothing in the row waits on time.

## Runs

- suite-157.txt: the suite alone through the dispatcher, 7 rows green.
- affected-suites.txt: 58_veldo_0031_claims, 59_veldo_0031_review, 82_veldo_0085_decomposition (ForkFlag,
  ForkBarrier) green; 38 crashes (below).
- full-unit-run.txt: every suite but 38 in one dispatcher process with the watchdog, the residue rows and
  the record on, through scripts/host_heavy.sh. See that file.

## Reported to the lead (not fixed here: outside this brief's files)

1. Suite 38_veldo_0025_membership, row "VELDO-0261 AC2 wait/expiry-report" (lines 493-522), and its
   registered mutant wait261-expiry-returns-none (scripts/check_teeth_mutations.py, finding 261 block)
   test exactly the behavior AC1 removes: wait_for returning a report when a 0.3 s bound runs out. The row
   execs shared.py's wait_for alone in an empty namespace, which now raises NameError (WAITS), and that
   crash ends the dispatcher, so every later suite of the leg is not run. The mutant's anchor text no
   longer exists in shared.py ("mutation anchor moved"). Suite 38 is in no brief and not in the spec's
   footprint. A fix consistent with AC1: restate the row as "an expired wait is hung, never false"
   (it is covered by waits/three-outcomes) and retire or re-anchor the 261 mutant. The design's section
   4.3 lists 38:522 as a lower bound that stays; that line is this row.
2. Suite 62_veldo_0039_dispatch (brief E) calls shared.wait_for twice with no source: it now runs on
   waits.LegacyInterval with the wait hang bound in place of its 10 s and computed bounds, until E converts
   it.
3. Residue reds seen in the full run, by suite, are listed in full-unit-run.txt for briefs F and G (the
   brief expects 66_veldo_0042_clones and 86_veldo_0189_engine_upgrade).
