# VELDO-0358 brief E: the launch and containment path

Scope: revision-notes section 3.3, brief E. Suites 62_veldo_0039_dispatch, 63_veldo_0040_containment,
78_veldo_0060_claude_adapter and 106_veldo_0185_dispatch_setup; engine modules control_launch,
control_containment, control_heartbeat, control_engine_claude, control_engine_codex and policy_contract
(the canon in engine/.veldo, each with its synced copy in .veldo). Criteria AC10 and AC15 for these suites.
Built on fb7705e1 (wave 0 integrated). Nothing here ran scripts/verify.sh.

## What was built

| Part | Where | What it does |
| - | - | - |
| Timers table entries (AC15) | the six engine modules | Every giving-up deadline of the launch path is an entry of engine/.veldo/timers.py, read where it is armed: control_launch ACCEPT, RECEIVER_EXIT, ORPHAN, REQUEST, CENSUS, SOURCE, IDENTITY, NAMESPACE, FEEDER_SETTLE, FEEDER; control_containment SETTLE, TOOL; control_heartbeat SETTLE, SETUP; control_engine_claude LOGIN, INIT; control_engine_codex LOGIN, CATALOG; policy_contract's five contract timers (kind contract). The census finds no numeric timeout left in the six files |
| One table per installation | each module's `_timers()` | Engine modules load each other as separate instances (`_organ`), so the table is shared by its path in sys.modules: a profile set once reaches every arming site of that installation. policy_contract is also read alone by the policy tooling (suite 29 copies it by itself); with no timers.py beside it, its contract values are its own |
| Profile across processes | control_launch | The receiver takes the profile from its configuration (`timers_profile: {except, hang_seconds}`) before any timer is armed and passes it to the trusted wrapper (`exec --timers`). The wrapper's start record (its identity line, the first line of the execution record) carries `timers`, the effective values; the receiver's running message carries both its own and the wrapper's |
| Receiver exit (4.8, event) | Launch._end_receiver | A receiver whose output ended, or that sent its last report (`exited`, `unknown`), is awaited on its pidfd, bounded by RECEIVER_EXIT_SECONDS of the table (production 2 s, kept), and killed only after it; the wait is recorded on the launch (`receiver_exit`: awaited, bound, ended_by) |
| Orphan release (4.8, event) | Runner.release_orphans, `_await_gone` | The 0.02 s poll is gone: the runner waits on the worker group's cgroup.events and the worker's pidfd, bounded by ORPHAN_SECONDS of the table; the observation records what woke it |
| Supplied clock and check request (design C4) | Receiver, honoured only under VELDO_CONTROL_TEST_HARNESS=1 | `{"advance": s}` on the control channel moves the wall clock the contract deadline is judged on; `{"check": id}` is answered, after the timers are evaluated, by a `checked` message naming the cause of the stop begun (None: nothing was due). A timer that never fires is an answer, not silence |
| .veldo/timers.py | repository copy | The repository's .veldo had no timers.py; suites install .veldo, so it is added, byte-identical to the canon (template sync passes) |

## The suites

| Suite | Converted (design 4.2) | New rows |
| - | - | - |
| 62_veldo_0039_dispatch | marker waits on the markers directory and the store, impossible on the dispatch's terminal record (no 10 s bound); packet wait on its path and the worker's pidfd; the fixture worker released by inotify; the closed-output deadline judged on the supplied clock with a check request, no `elapsed < 6`; the stop rows end on the record, a `checked` answer of nothing begun, or the receiver's end (no ACCEPT_SECONDS bound); joins and the barrier at the wait hang bound; wall time as data from the support stamp; the absence after re-invocation read after both receivers ended | timers/profile-applied, wave1/no-sites |
| 63_veldo_0040_containment | markers waited on events, absences read after the terminal record (no 0.05 s waits); fixtures held on inotify latches or until a signal (no beat sleeps); the idle window counts the receiver's wakes between the first and last refused launch (pattern W, heartbeat far out); exit-notified asserts the pidfd cause, the order, zero wakes, latency as data (no 0.75 s); the runtime cap fires for real in its one row (20 s cap) with a lower bound only; escalation by the order term, hidden term, kill (no 2.7 s); contract deadlines an hour away; the scope holder is a latch holder; the fake-manager budget rows assert the supplied clock exactly | timers/profile-applied, wave1/no-sites |
| 78_veldo_0060_claude_adapter | the fake engine's holds and descendants block until a signal, a descendant says it is ready on a pipe; engine markers waited on events; absences after refusal read after the terminal record; stop rows by cause and order, the forced grace as a lower bound only (Stamp.at_least), no `took < 5`, no `elapsed < 20`; the held receiver released by inotify and awaited on its pidfd | timers/profile-applied |
| 106_veldo_0185_dispatch_setup | the journey wait wakes on the store and the observations file, done on the evidence, impossible on two idle inspect answers in a row at the same pass (no 90 s bound, no 1 s poll); wall time from the stamp | timers/profile-applied (reads every exited run's wrapper start record) |

Each suite sets the profile in process (every entry at the wait hang bound; no row of these suites tests a
table timer) and in its receivers' configuration. Suite 63's fake-manager rows run on a supplied clock and
test the production settling values, so they run with the table's own values and the live part with the profile.

Row labels: rows-kept.txt. Every suite keeps every base row and adds its new ones.

## Mutation registry

Brief E's block (`VELDO-0358 BRIEF E`) registers the specification's falsifiers:

| Mutant | Suite | Target rows |
| - | - | - |
| wave358-bound-restored (suite 62's marker_for back to a ten second clock-bounded poll) | 63 (its census row reads suite 62 through the anchor) | wave1/no-sites |
| wave358-latency-asserted (suite 63's 0.75 s real-clock assertion restored) | 62 | wave1/no-sites |
| timers358-literal-kept (RECEIVER_EXIT read as the literal 2) | 62 | timers/profile-applied, wave1/no-sites |

Restated outside the block, because the engine lines they anchor moved or because a hang is never a kill:
five anchors moved by the table reads (containment-exit-leaves-descendants, receiver148-report-wait-unbounded,
receiver148-placement-wait-unbounded, role127-init-unbounded, end350-ending-receiver-killed-for-its-status);
dispatch-closed-output-late-deadline now anchors the deadline's judgment (a late wake alone is answered at the
check); dispatch261-stop-leaves-record-running made the receiver sleep forever on a stop, which can only be
waited out, and is restated as a receiver that ends on the stop without recording the end (the row's wait is
impossible: the receiver has ended with the record open). The retired mutant's baseline entry is lowered.

## Baseline

By the landing order rule the entries this change removed are lowered (149 sites in 140 entries: the four
suites, control_launch, control_engine_claude, control_engine_codex, and the retired mutant text). The census
passes on the full tree (checks.txt).

## Runs

See runs.md (idle suites, the registered cases through the gate's driver, the affected suites, fifty loaded
runs per suite under the generator).

## Not done here, for the lead

See lead-items.md.

## Round 2 (2026-11-21)

| Commit | What |
| - | - |
| 69961820 | Two launch-path races. `_await_gone` takes the worker's pidfd exit as its end and never polls an empty set (brief F's lead item 6b: suite 83 hung at loop/receiver-death on every run with brief E). `Runner._stop_result`: a stop result refused stale_version because the asked receiver's exit commit landed between its version read and its commit is committed again at the version now there (round 1's open red, suite 62 dispatch/owner-stop) |
| 3d7e2307 | Suite 62 row dispatch/owner-stop-ends-first: makes that order on every run; red on the old runner, green on the fix |
| 190c4e90 | Lead decision: the files suites 78 and 106 open wait on events (85_veldo_0171, support/setup_runtime, support/v73_authority, proof/VELDO-0172/compare_formats); 38 baseline sites lowered |
| d1b18d13 | `_await_gone` tolerates a group removed between its open and its first read (ENODEV; suite 62 red once in 50 loaded runs at 190c4e90) |
| 481bd6fc | Suite 86_veldo_0168 freezes v73_authority's wall-time reader instead of its removed time module |

Runs, causes and the combination with brief F: runs.md, round 2. The mutation stage again: mutants.md, round 2.
The census passes on the full tree (no site in the four suites or the files they open).
