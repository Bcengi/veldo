# VELDO-0125 b2 round 22

Starting revision: `6eec919a`. Regression/diagnostic commit: `9ecbb901`.
Parking implementation: `8a12d9f3`; diagnostic/fault-injection follow-up:
`d6efaf09`. No full gate, mutation runner, merge or push was run.

## Parking repair

All three writers now converge on `park_path`: corrupt-content quarantine,
non-retryable delivery failure through `move`, and recorder-failure parking.
The first park retains the legacy dispatch hash filename. Later parks use
numbered siblings ending in `.json`. `os.link` publishes a name exclusively;
an occupied name, including a symlink, causes another number to be tried.
There is no check-then-replace race and no replace operation into `.parked`.

The destination directory is created and its parent synced. The source file is
fsynced before linking; the destination directory is fsynced before unlinking
the source; the source directory is then fsynced. A failure before durable
publication retains the source. An interruption after publication may retain
both copies, and retry preserves the already published record. A failed dequeue
reports both source and destination and retains the published evidence.

Seven regression rows cover corrupt bytes followed by a permanent failure or
recorder failure; three successive quarantine, failure and recorder parks of
one dispatch; file/directory sync before dequeue; and interrupted publication
followed by retry. They enumerate every parked JSON filename and check counts
and content, including raw invalid bytes. The baseline run recorded six failing
rows. The durability row was subsequently strengthened to also assert the
published file's inode was fsynced, so it cannot pass merely because an old
rename bypassed its unlink observation.

The first implementation run exposed two existing rows. The round 14 fault
injector now also denies the new `os.link` operation for the exact same source
path; its existing `os.replace` injection, assertions, deadlines and row names
remain unchanged. The round 13 real-permission-denial row was left unchanged;
production now preserves the two-path failure diagnostic when dequeue fails
after linking. Its source still survives for recovery.

`park-all-readers.txt` records the repository-wide Python/Markdown inventory,
including hidden directories. Production has no worker parked-directory status
counter or operator reader. `control_assignment.parked_units` is an unrelated
database disposition. Outbox `locate`/`entries`/recovery deliberately read only
live queue states. Existing single-park fixtures in event, lifecycle, crash,
round 12-17 and round 21 helpers can still address their first record by its
legacy name; their assertions are retained. New multi-park rows enumerate all
files. The operator instructions in `b2-events.md` now explicitly require
counting and inspecting every parked file, including numbered siblings.

The `receive` branch checking `enqueue_locked(...) is None` was removed in both
copies. `enqueue_locked` always constructs a non-None entry dictionary and
passes it explicitly to `move`. Thus `move` cannot take its None-entry return:
it returns a Path or raises. Corrupt previous content is quarantined before
constructing that fresh entry; operational read/park/write failures raise.

## WARP-1404 investigation and remaining limitation

The suite now prints its existing audit result and the filenames of code
executed inside the same windows. No assertion, allowlist, window, selector,
deadline or expected result changed.

The ordinary sandbox baseline passes: `pure=[]`, `repo_writes=[]`, and
`repo_spawn=["git log", "git show"]`. All eight drives complete, including the
CLI, with 190 repository records. `audit-before.json` records the result.
`import-closure-comparison.json` compares Git blob identities for all 15
repository modules actually executed in the audit windows. Every one is
identical at `9763249e`, `d2288a28` and `6eec919a`; no new worker module appears
in this closure. This is a measured closure for these drives, not a claim about
every possible repository input.

A cold, unwritable cache probe DOES reproduce the exact single AC5 failure:
63 passed, 1 failed. Only the ignored `.veldo/__pycache__` directory was moved
aside and replaced with an empty mode-0555 directory for this invocation:

`python3 scripts/selftest.py --suite 15_warp_1404_historical_analogy`

An EXIT trap restored the original cache. No tracked source, audit window or
test condition changed for the probe. `sandbox-cache-probe.json` records the
confinement indicators and restoration. This adds a permission-denial condition
inside the existing sandbox; it is not a run of the owner's canonical gate leg.

The hook observed 35 attempted write-mode opens of temporary `.pyc` files:
20 in the pure bucket and 15 in the combined import/repository/CLI bucket.
Flags were 524481 (write/create/exclusive/close-on-exec). There were no sockets
or unexpected spawns; git log/show remained the only spawns. The full paths
are in `audit-cold-readonly-before.json`. One attempt is the audit driver's
own import of `toe_analogy.py`, before that module's code executes; others
are importlib loading its unchanged dependencies. Cache denial makes these
attempts repeat in the audited subprocess instead of reusing cached bytecode.

This establishes a reproducible cache-dependent failure, but does not identify
a VELDO-0125 code change responsible for the owner's gate failure. Normal runs
have no prohibited event before or after the parking repair. No speculative
production change or global bytecode suppression was made to turn this probe
green. The owner's failing hook observations were requested to establish
whether its cause matches. The second defect remains unresolved pending that
evidence; this bundle does not claim an audit code fix or canonical gate pass.

## Selected-suite evidence

`results.json` records each actual run's command, exit code, counts and log
digest. The `106-before` run uses the original production code plus regression
rows; `106-after` is the intermediate implementation with two existing failures;
`106-final` includes their fixes. All logs, including unsuccessful runs, remain
unaltered. `15-after` records the final ordinary-sandbox audit observations.

| Final suite | Suite assertions passed | Failures | Exit |
| --- | ---: | ---: | ---: |
| 103_veldo_0124_macos | 23 | 0 | 2 |
| 104_veldo_0124_control | 6 | 0 | 2 |
| 105_veldo_0125_relay | 17 | 0 | 2 |
| 106_veldo_0125_routing | 246 | 0 | 2 |
| 15_warp_1404_historical_analogy | 38 | 0 | 2 |

Each run also passed 26 shared assertions. Before and after the parking repair,
the ordinary audit reports no prohibited events; git log/show are the only
spawns. The cold-cache failure remains documented separately and unresolved.

Only suites 103/104 for VELDO-0124, 105/106 for VELDO-0125, and WARP-1404 were
run, one at a time. Exit 2 with zero failed assertions is the dispatcher's
mandatory `PARTIAL_RUN_CANNOT_VERIFY` status, not full verification. Native Mac
qualification and the merged-tree gate remain the reviewer's responsibility.
`template-sync.json` verifies both canonical/installed pairs. The checkout's
gate byproducts are restored before the final evidence commit and excluded.
