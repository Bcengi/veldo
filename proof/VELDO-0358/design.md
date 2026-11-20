# Veldo gates never fail because the machine is busy

Design, 2026-11-20, revision 2. Owner request: Telegram 42829 ("I want to stop failing veldo gates due to
performance that is caused by machine load"). Supersedes VELDO-0223. Revision 2 applies the independent
validation (validation.md, verdict CHANGES); revision-notes.md lists every finding, what changed, and the
three places where this revision keeps a different fix, with evidence. Read against the worktree space-0329b
at f5055400 (revision 1 read 0f15ecd3; the one commit between is a VELDO-0127 recapture and moves no cited
line).

Paths are short forms: `suites/` is `scripts/suites/` in the Veldo repository, `teeth.md` is
`proof/0329b-gate-fix/teeth.md`, `live state` is `myday/playbooks/veldo_live_state.md`, `runner.log` and
`logs/` are under `myday/research/lock-queue/`.

## 1. The decision

A Veldo test must give the same answer on an idle machine and on a machine that is ten times slower. That
is achieved at the source, in the tests and in the product, and not by controlling the machine.

Four things follow, and they are the whole design.

1. No test waits for time to pass. A test waits for the event it needs (a process exit, a message, a file,
   a row in the store) and for the event that proves the first one can no longer come. The clock is left
   with one job: to notice a hang, and a hang is measured as time without progress, never as total time.
2. No test judges a duration. A real latency requirement is measured in its own stage as candidate against
   the last landed build in one run, and judged on the difference.
3. The gate refuses new clock dependencies mechanically (the census check), and it proves the result on
   every run by running the suites once under a deliberate heavy load (the load-proof leg).
4. A red on a busy machine is a defect and is fixed: in the product when the product raced or gave up on a
   short timer (the follower and its pidfd in gate 11), in the test when the test raced. It is never rerun,
   never voided, and never classified by how busy the machine was.

Nothing in this design measures the host's load to decide a verdict, waits for a quiet host, or reruns a
red. Section 12 lists what is deliberately absent.

## 2. What made the last gates red

Gates 7 to 12 of space-0329b each took between 2 h 18 min and 3 h 20 min (runner.log:1063-1065 for gate 7,
1075-1077, 1095-1098, 1101-1103, 1120-1121, 1154-1156). Gate 12 started with the host at load 29.93
(runner.log:1155). Every red that was not a stale record came from one of six mechanisms.

| Gate | Red | Mechanism | Evidence |
| - | - | - | - |
| 99zzL (before 7) | One mutation worker killed at 120.2 s with 8.8 s of CPU; five cancelled; 977 cases never started | A suite waited out a 90 s bound for something a mutant had removed; the case sat at 87 to 91 percent of the driver's 120 s floor | teeth.md:161-184; suites/106_veldo_0185_dispatch_setup.py:819; scripts/check_gate_mutations.py:37 |
| 99zzL | Two cases at 97 to 102 s of 120 | Nine waits of 10 s each for workers whose dispatch was already refused | teeth.md:225-238; suites/62_veldo_0039_dispatch.py:282, 419 |
| 99zzL | Cases at 82 s and 52.5 s of 120, not yet red | A suite budget of 80 s with 20 s waits (suite 71 of VELDO-0138); a mutant that moves a deadline 30 s late, waited out (suite 62) | teeth.md:203-206, 237-238, 263 |
| 99zzL | reservation/principals red once in 81 runs | The suite stopped the service between a commit and the loop pass that returns the slot | teeth.md:240-261 |
| 7 | 3596 of 3597; one control unjudged | A port number read and released, then bound seconds later; another bind took it | teeth.md:265-291; live state:8942, 8956 |
| 8 | One row, VELDO-0143 activation/name-taken; and service/pm-settled-due once in 241 runs under load | Cause not found in 300 runs. Threads left by suites 66 and 86 were alive while suite 110 ran in the same interpreter | teeth.md:293-342; live state:8999, 9051; logs/99zzN4-veldo-space-0329b-gate8.out:27-29 |
| 9 | 5 cases voided | /proc/locks read in pages while other processes took and dropped locks; one lock listed twice | teeth.md:344-386; live state:9067, 9080; logs/99zzN5-veldo-space-0329b-gate9.out:28-29 |
| 10 | 23 cases voided | A "no wake in at least 1.5 s" window stretched to 6.9 s under load and then held a 10 s heartbeat | teeth.md:409-427; suites/63_veldo_0040_containment.py:1010, 1066 |
| 10 | 16 cases voided | Product: Launch.wait read no messages when the run had ended before the settle | teeth.md:429-450; engine/.veldo/control_launch.py:2149-2163 |
| 10 | 1 case voided | A browser test moved state while a second read was still in flight | teeth.md:461-474; engine/ui/e2e/factory.spec.ts:271-281 |
| 10 (while proving) | runtime-cap 1 of 280 and cooperative-stop 5 of 280 at twice the gate's load | A 1.2 s runtime cap ended a worker before it had started its descendant | teeth.md:488-491; suites/63_veldo_0040_containment.py:327 |
| 11 | First-use red and 43 cases voided, supervisor_ended False | Product: the follower took a closed pipe for the supervisor's exit | teeth.md:508-544; engine/bin/veldo:1217-1226; live state:9115, 9157 |
| 11 | 2 cases voided, backlog not visible | A fixed 10 s visibility wait; cause not reproduced (the live state line says 1000 ms, the record and the configuration say 10000 ms) | teeth.md:546-575; engine/ui/playwright.config.ts:11; live state:9115 |
| 11 (while proving) | stop-after-the-command-ends-nothing, invalid baseline in 3 runs of 4 | A fixture process that lived for an instant was listed under load (fixed in the fixture); the row still asks again after a 1.5 s window | teeth.md:577-592; suites/151_veldo_0313_space_run.py:1010, 1020 |
| 12 | driver_error, ownership ledger | A path resolved while a link on it was swapped | teeth.md:631-652; live state:9199 |

Two things stand out. First, the mutation stage is itself the heaviest load on the host (36 to 48 workers
on 20 cores; logs/99zzN8-veldo-space-0329b-gate12.out:8, 14, 20), so most of these reds needed no other
work on the machine: the gate loaded itself. A quiet host would not have removed them. Second, in gates 9,
10 and 11 no mutant survived. What failed was a control, the unmutated suite, and every case that shared it
was voided two hours into the gate.

Two of the product reds were races (Launch.wait, the follower), not timers. The product also has short
timers on the same paths (section 4.7); under load they give up on work that was merely slow, and a suite
row then fails for a reason that is the product's. They are in scope where a wave 1 suite crosses them.

VELDO-0223 names one more that has not yet been fixed: the factory loop's rows deadline of 45 s with waits
of 8 s (specs/VELDO-0223-a-red-under-others-load-is-rerun-quietly-before-it-counts.md:110-114;
suites/83_veldo_0154_factory_loop.py:109), whose ten mutants were invalid baselines in one run and valid
rejections in another with byte-identical inputs.

The gate itself states that it has no timing thresholds (scripts/verify.sh:241, performance: "no
performance thresholds declared"). Every timing assertion inside a suite is therefore an undeclared one.

## 3. The classes of wall-clock dependency

Every site in the inventory belongs to one of twelve classes. The class decides the replacement. D1, D2
and F are sites the census still counts (they read the clock or sleep) but that are not synchronization;
their replacement is not the wait primitive.

| Class | What it is | How load breaks it | Replacement |
| - | - | - | - |
| S1 settle sleep | A sleep of fixed length before reading a result ("give it time") | Too short when slow: false red. Sometimes too short the other way: a false green on an absence check | Wait for the event (section 5, C1 and C2) |
| S2 poll interval | A short sleep inside a loop that re-reads a condition | Harmless alone; it only exists to serve a bounded poll | Disappears into the wait primitive |
| S3 holder | A fixture process that stays alive by sleeping 30, 60, 120 or 600 s | Exits by itself when the test runs longer than the sleep | A holder that blocks on a latch the test owns (C3) |
| P bounded poll | Loop until a condition or until a deadline of a few seconds | The deadline is a guess about speed; expiry reads as "false" | Wait primitive: condition, terminal condition, hang bound |
| T short timeout | A timeout on a child process, join, socket, queue, select, page expectation | Same as P | A hang bound by name (section 6) |
| A timing assertion | A row that requires a duration under a number | Slowness alone makes it red | Assert the cause and the order; lower bounds may stay; a real latency goes to the paired stage (section 8) |
| W absence window | "Nothing happened for N seconds" | The window stretches and takes in events that are legitimate; or ends before a slow fault shows | Absence is proven between two events, not over a span (section 5, pattern W) |
| TR timer race | Two timers in one scenario whose order decides the row (a 2 s deadline against a 10 s heartbeat; a 1.2 s cap against a descendant's start) | Slowness reorders them | One timer under test per scenario; every other timer disabled or at the hang bound; virtual time where the product reads a clock (C4) |
| R race shown by load | No clock in the test at all: a non-atomic read, a released port, a leftover thread, a short-lived process, a product race | Load widens the window | Fix the race: atomic source, held resource, one process per suite, the kernel's own notification. In the product when the product raced |
| D1 timestamp as data | A clock read whose value is stored in a record, a fixture field or a future date ("revoked at now plus an hour") | It does not; but it is a clock read the census must account for | The support module's stamp, or a supplied clock where the product reads it |
| D2 deadline as product input | A clock read plus a number passed to the product as its deadline (for example a Workers object built with now plus 60) | The product judges the deadline; a slow run reaches it | A supplied clock passed to the product, with the deadline an hour away and moved by the test (C4) |
| F fixture pacing | A sleep inside a fake server, fake engine or scripted output that simulates work, not synchronization | Usually not; it can widen a race elsewhere | A latch where something waits on it; otherwise an exception of kind subject (section 9) |

A lower bound on real time ("it did not act before two seconds had passed") is not load dependent: slowness
only makes it more true. Lower bounds stay. A comparison over values from a supplied fixture clock is not a
real-time comparison and stays (for example suites/63_veldo_0040_containment.py:722, whose values come from
the fake manager clock at lines 467-492).

## 4. Inventory

### 4.1 How it was made, and its limits

Method, revision 2: a syntax-tree reading of every Python file in scope, applying the census rules of
section 9 as they are now written (calls resolved through the file's imports, the closed table of
positional timeouts, constant names resolved within the module), plus a text reading of strings that hold a
sleep, followed by reading the files behind every red in section 2, every sleep in suites, and every
comparison of a duration with a number. The class of each clock read is assigned by its use: compared
inside a loop (P), passed into a product constructor or a keyword named as a deadline (D2), otherwise
stored (D1). The counts:

| Scope | Python files | Files with a site | R1 sleep calls | Sleeps in source text | R2 clock reads | R3 timeouts |
| - | - | - | - | - | - | - |
| scripts/suites | 249 | 183 | 119 | 112 | 914 | 890 |
| scripts (gate and mutation tooling, top level) | 49 | 15 | 9 | not counted | 64 | 26 |
| engine/.veldo | 265 | 87 | 13 | not counted | 232 | 154 |
| proof (all Python, not only what suites open) | 346 | 199 | 17 | not counted | 341 | 218 |

In scripts/suites the R3 count splits into 761 keyword timeouts and the positional forms the earlier rule
missed: 33 joins, 32 waits, 30 settimeout, 24 select calls (for example
suites/153_veldo_0314_session_hooks.py:144 and suites/71_veldo_0138_channel_service.py:228), 8 wait_for and
2 Timer. The rule flags none of the 19,846 `.get` calls and none of the 871 `.join` calls that are not a
thread or process join. The R2 reads in suites split into 201 bounded polls (P), 85 deadlines as product
input (D2) and 628 timestamps as data (D1).

So the first baseline holds about 2,035 suite sites, not the 1,505 of revision 1, and most of the growth is
D1, which is mechanical to convert. The census tool's first run is the authoritative list (section 9,
"First run"), and these numbers are the check on it: a first run that differs from them by more than a few
percent is investigated before its baseline is accepted.

### 4.2 The sites behind gates 7 to 12 (work first)

| Site | Class | State today | Replacement |
| - | - | - | - |
| scripts/check_gate_mutations.py:37, 175-187, 789-794 (120 s floor, three times the measured time, worker killed at its deadline) | T | In force. Killed a worker with 8.8 s of CPU | Every worker runs under the progress watchdog of section 6. Measured times order admission only (section 7) |
| scripts/check_gate_mutations.py:518, 828 (5 s to reap a killed group) | T | In force | Wait on the group's cgroup.events (empty) under the wait hang bound |
| scripts/check_first_use.py:135-138, 342 (nested run killed at twice its measured time, floor 1800 s, ceiling 21,600 s) | T | In force | The nested run is a selftest process with its own progress watchdog; the parent waits on its pidfd with no total bound (section 6) |
| suites/106_veldo_0185_dispatch_setup.py:819-840 (90 s journey bound, 1 s poll) | P | Idle exit added in gate fix 7; the 90 s bound remains | Wait on the service's own "nothing more will come" answer as the terminal condition; bound becomes the wait hang bound |
| suites/62_veldo_0039_dispatch.py:282, 419 (10 s marker wait), 188 (60 s) | P | Ends on the dispatch record since gate fix 7; 10 s remains | Terminal condition is the record leaving prepared, accepted or running; bound becomes the wait hang bound |
| suites/62_veldo_0039_dispatch.py:673 (elapsed under 6) | A | In force | Assert deadline_stop and the order of the recorded steps; drop the upper bound |
| suites/62_veldo_0039_dispatch.py, row deadline-after-closed-output (mutant dispatch-closed-output-late-deadline, scripts/check_teeth_mutations.py:2973-2976, waited out at 52.5 s) | P | In force | The dispatch is given a supplied clock and a deadline already past when its output closes; the row waits on the stop record, and the mutant's receiver answers the check request with "nothing due" (terminal) |
| suites/71_veldo_0138_channel_service.py:89-100 (suite budget 80 s, wait of 20 s that returns the last value on expiry), 225-228 (30 s readiness loop, select 0.2) | P, T | In force. owner-command-unrouted (scripts/check_teeth_mutations.py:5622) waited out at 82 s of 120 (teeth.md:263) | wait() becomes C1 with the channel's processed-command record as terminal condition; readiness waits on the READY=1 notification with the wait hang bound; the budget is deleted |
| suites/83_veldo_0154_factory_loop.py:109, 465-499, 1008 (budget 100 s, rows 45 s, wait 8 s) | P, TR | In force; not yet red in gates 8 to 12, named by VELDO-0223 | Each wait ends on the loop's pass counter or on the service's idle answer; the 45 s and 8 s numbers are deleted |
| suites/83_veldo_0154_factory_loop.py:734, 840 (sleep to booted plus 1.5 s; sleep 2.0) | W, S1 | In force | Pattern W: the next pass of the loop is the closing event |
| suites/63_veldo_0040_containment.py:1010, 1066 (idle window of at least 1.5 s, zero wakes) | W | Heartbeat moved out of the window in gate fix 10; the window remains | Count wakes between two events the test causes (the first and the last refused launch), with every periodic timer of the profile disabled |
| suites/63_veldo_0040_containment.py:1069 (exit recorded within 0.75 s, real clock) | A | In force | Converted in wave 1: the row asserts that the receiver recorded the exit from its pidfd wake (one wake, zero poll intervals, read by the row's existing wake counting) and that recorded_at is after exit_at. The latency is written as data for the paired stage (section 8) |
| suites/63_veldo_0040_containment.py:722 (0.75 s on the fake manager clock) | none | Values come from the supplied clock of lines 467-492 | Stays; declared as an exception of kind supplied_clock so R4 does not count it |
| suites/63_veldo_0040_containment.py:327 (runtime cap 1.2 s, kill grace 0.5 s) | TR | 1 of 280 red at twice the gate's load (teeth.md:488-491) | The capped worker starts its descendant and signals a latch before its work; the cap is armed on the supplied clock and moved by the test after the latch; the real 1.2 s firing stays only in the one timer_fires row, asserting the cause with a lower bound |
| suites/63_veldo_0040_containment.py:1266-1268 (grace arithmetic with upper bound 2.7 s) | A | In force; cooperative-stop red 5 of 280 at twice the gate's load (teeth.md:488-491) | Order of term, hidden term and kill from the record; lower bound stays |
| suites/63_veldo_0040_containment.py:364-369, 1005, 1121, 1129, 1219, 1226 (marker absent after 0.05 s) | W | In force | Absence read after the launch's terminal record, with no wait |
| suites/66_veldo_0047_authority.py:282-308 (lock holders) | R | Fixed (fdinfo) | None. Same defect remains in scripts/gate_host.py |
| scripts/gate_host.py:136-139 (holders of the gate lock read from /proc/locks) | R | Open (teeth.md:385-386) | Read the lock from the fdinfo of the holder's descriptor, as suite 66 does |
| suites/66_veldo_0047_authority.py:820-821 (sleep 1.5 "longer than any restart delay") | W | In force | Read the unit's restart counter and its final state after the stop has completed |
| suites/78_veldo_0060_claude_adapter.py:594-612, 1169 (marker waits of 15 s, 2 s, 0.3 s) | P, W | In force | Wait on the launch's end message; absence read after it |
| engine/.veldo/control_launch.py:2149-2163 (Launch.wait) | R, product | Fixed by the launch-wait change (live state:9126) | Low follow-up "unknown at settle" stays a product ticket |
| engine/ui/e2e/harness.py:70-78, 239 (port held until bound) | R | Fixed | Same pattern is open at suites/support/v171_tailscale.py:123-128; C11 is lifted from this harness |
| engine/ui/e2e/factory.spec.ts:271-281, 443 (requests not yet answered) | R | Fixed for one test | Make it the fixture's standing "page settled" signal for every test (C10) |
| engine/ui/e2e/factory.spec.ts:764-773; engine/ui/playwright.config.ts:10-11 (test 90 s, expectation 10 s) | T | Panel state awaited in one test; the 10 s default governs every other expectation | Expectations wait on the page's own state (loading, ready, empty, error); the expectation timeout becomes the wait hang bound, the per-test limit becomes the process hang bound measured from the test's last step |
| engine/bin/veldo:1217-1226 (follower waits on a pidfd) | R, product | Fixed. A kernel without pidfd still falls back to the pipe | Decided: pidfd required (live state:9173); its spec is queued |
| suites/151_veldo_0313_space_run.py:1119-1123, 1198, 1205 (2 s sleeps, a window, took under 4.0) | W, A | In force | Count the supervisor's reads between the churn events the test causes; drop the upper bound, keep the lower |
| suites/151_veldo_0313_space_run.py:1010, 1020 (LINGER holder; "still there 1.5 s after SIGTERM and SIGHUP") | S3, W | The fixture race was fixed (teeth.md:584-592); the 1.5 s window remains | Holder becomes C3. Pattern W: the closing event is the supervisor's acknowledgement of each signal on its report; if it writes none today, the acknowledgement line is added to engine/bin/veldo as part of the conversion; presence is read after it |
| suites/151_veldo_0313_space_run.py:903, 1287, 1594, 1611, 1702 (bounds of 5, 15, 30 s) | P | In force | Wait primitive with pidfd or path events |
| suites/66_veldo_0042_clones.py:553-585 (listener thread left in accept; 25 s poll; 2 s socket timeout) | R, P | Open; seen alive during suite 110 (teeth.md:329-331) | Close and join the listener before the suite ends; residue check (C7) |
| suites/86_veldo_0189_engine_upgrade.py (Bridge.serve threads left) | R | Open (teeth.md:331) | Same |
| suites/110_veldo_0143_new_project.py:1997, 2059, 2094, 2193 (join 5 s; three 120 s loops) | T, P | Cause of gate 8 not found | Residue check and one process per suite remove the only anomaly seen; the row's detail already names which report failed |
| suites/110_veldo_0143_new_project.py:2151-2210 (service/pm-settled-due, 1 in 241 with twelve copies at once; teeth.md:333-339) | R | Cause unknown; the row's detail now names each report's outcome | Its two refusals (push_refused:remote, not_taken_on:authority_unavailable) are both answers of a product client under a short timer; the wave 1 timers of 4.8 (control_client and the store's busy wait) are set to the wait hang bound under the profile. Not claimed fixed; the leg's 20 runs of a changed suite 110 are the test |
| scripts/mutation_ownership.py:599-603 (5 s cleanup poll) | P | In force | Wait on the unit's cgroup becoming empty (cgroup.events) |
| scripts/mutation_ownership.py (link swapped during resolve) | R | Fixed (0b767d26) | None |

### 4.3 Timing assertions (class A): all that were found

Upper bounds on a real duration, each of which slowness alone can turn red:

| Site | Bound | Replacement |
| - | - | - |
| suites/102_veldo_0210_agent_profile_runtime.py:1074 | waited between 0.9 and 3 s, twice | Lower bound stays; the upper bound is replaced by the cause the product recorded |
| suites/102_veldo_0210_agent_profile_runtime.py:1896 | took under 20 s | Exit status and no leftovers already assert the outcome; drop the bound |
| suites/105_veldo_0182_memory.py:398 | waited under 5 s | Assert the "no progress" message and its stated interval |
| suites/150_veldo_0329_hook_install.py:781, 832, 926, 940 | hook holds under 20, 30, 15, 12, 20 s | Assert that the hook line is armed with the hold constant and that the hook ended by its own timer; lower bounds stay |
| suites/153_veldo_0314_session_hooks.py:143, 163, 318, 346, 350; suites/150_veldo_0329_hook_install.py:386 | elapsed under 15 s | Same |
| suites/38_veldo_0025_membership.py:522 | took between 0.3 and 5 s | Lower bound stays |
| suites/40_veldo_0101_capsules.py:251, 353 | duration under 30 s; under 2 plus KILL_WAIT plus 4 | Assert timed_out and the kill path recorded |
| suites/42_veldo_0102_fixval.py:166, 492 | under 25 s; under 60 s | Assert status "deadline" and the derived deadline value |
| suites/53_veldo_0123_mutations.py:319 | under 5.4 s | Assert the worker inactive and the child dead |
| suites/62_veldo_0039_dispatch.py:673 | elapsed under 6 s | Section 4.2 |
| suites/63_veldo_0040_containment.py:1069, 1268 | 0.75 s; 2.7 s | Section 4.2 (line 722 is on a supplied clock and is not in this table) |
| suites/75_veldo_0062_accounts.py:1109; suites/78_veldo_0060_claude_adapter.py:1221; suites/86_veldo_0127_agent_configuration.py:728 | elapsed under 20, 20, 15 s | Assert that the stop was begun before the work ended, from the record's order |
| suites/78_veldo_0060_claude_adapter.py:1418, 1425; suites/79_veldo_0061_codex_adapter.py:938, 948 | took under 5 s; within twice GRACE plus 4 s | Assert the step sequence (cooperative, then term, then kill); lower bound stays |
| suites/79_veldo_0061_codex_adapter.py:1083 | wall seconds under 60 | Assert the charge is positive |
| suites/151_veldo_0313_space_run.py:1198 | took under 4.0 s | Section 4.2 |
| suites/19_veldo_0002_work_state.py:238, 295 | heartbeat age under 30 s | Supply the reader's clock, as the stale row of the same suite already does (line 228) |

Lower bounds that stay as they are: suites/113_veldo_0220_gate_host.py:236, suites/111_veldo_0214_first_use_budget.py:304,
suites/58_veldo_0028_effects.py:974, suites/62_veldo_0039_dispatch.py:676, suites/67_veldo_0041_heartbeat.py:509,
suites/75_veldo_0062_accounts.py:1463, suites/86_veldo_0148_re_land.py:1456, suites/151_veldo_0313_space_run.py:1205.

Already on a supplied clock, and correct: suites/112_veldo_0215_case_deadlines.py:203-264,
suites/115_veldo_0219_measured_admission.py:356, 542, suites/97_veldo_0204_gate_resources.py:116,
suites/98_veldo_0204_mutation_receipts.py:123, suites/63_veldo_0040_containment.py:700-722. These show the
pattern the product timers need. (The clock read at suites/97_veldo_0204_gate_resources.py:79 builds a
Workers deadline from the real clock; it is class D2, not a poll, and moves to a supplied clock in wave 4.)

### 4.4 Sleeps in suites, by kind

Settle sleeps and absence windows (S1, W), each replaced by an event or by pattern W:
102:266, 443, 448, 1041, 1066, 1115, 1872, 1913; 105:407, 481, 483, 515; 106:840; 113:75; 114_veldo_0220:104;
141:686, 736; 151:1119, 1123; 47:515; 56:536; 58_veldo_0046:454, 456; 59:1153; 62:703; 63:185, 215, 1010;
66_veldo_0047:821; 71_veldo_0130:3047; 71_veldo_0138:95; 73:91; 74:588; 75:941; 78_veldo_0060:375;
79:303; 82_veldo_0144:161; 83:734, 840, 1052, 1136; 40:244. (Numbers are the suite file prefix and line.)

Holders (S3), each replaced by a latch-held process: 02:324-333, 368; 102:453, 609, 664, 1036, 1813, 1816, 1847;
103_veldo_0211:57; 104:154-155; 112:338; 113:207, 231; 114_veldo_0220:93; 146:759; 150_veldo_0329:868, 882, 886;
150_veldo_0350:508, 588; 151:1010, 1072, 1160, 1272; 153_veldo_0309:196; 153_veldo_0323:554; 153_veldo_0337:664;
40:220, 334; 42:468; 53:50, 54; 58_veldo_0036:291, 356; 59:93; 63:1285; 64:132; 67:705; 98:368.

Sleeps of a length the test computes from the product's own timer (TR): 74:588 (until a delegation lapses),
83:734, 63:1010, 86_veldo_0148:1382, 1395 (5.25 s, a deliberate late step with a lower bound: stays),
75:375, 78_veldo_0060:343, 78_veldo_0160:290, 79:299, 82_veldo_0165:268, 82_veldo_0141:330, 80:536 (fixture
engines that pace their own output: stay as holders of a scripted length only where a lower bound reads them,
otherwise they take the latch).

Fixture pacing (F), not synchronization: 04:761 (a fake gate's 3 ms of simulated work), and in fixture
source text 105:563, 111:45, 114_veldo_0216:86. Not a sleep at all, removed from the list: 06:981 (the
sleep method of a fake clock), 20:398 and 23:707 (the word sleep in a set of names). Stepping past a coarse
clock, a lower bound: 115:132.

Poll intervals (S2): the S2 count of appendix A.1. They go when their loop becomes a wait.

### 4.5 Gate and mutation tooling

| Site | Class | Replacement |
| - | - | - |
| scripts/check_gate_mutations.py:37-39 (WORKER_BUDGET 120, WORKER_CEILING 1800, multiplier 3) | T | Every worker runs under the progress watchdog (section 6); the stage's combined deadline (lines 760-790, 1136-1167, 1264-1297) is removed, since every worker is bounded by its progress and the stage stops at the first hang |
| scripts/check_gate_mutations.py:1047 (0.02 s poll of completions) | S2 | Wait on the workers' pidfds |
| scripts/check_first_use.py:135-139, 342 (nested run killed at a measured budget, floor 1800 s, ceiling 21,600 s) | T | Section 4.2: no total bound; the nested selftest's own progress watchdog |
| scripts/agent_sandbox.py:134, 293, 1072, 2727, 2762 (60 s to start a namespace) | T | Wait hang bound |
| scripts/agent_sandbox.py:2056 (10 s grace) | product timer of the sandbox | Stays; listed in the timers table |
| scripts/gate_host.py:226, 284-288, 330, 384, 391 (polls for the lock and the scope, 30 s) | P | Lock: a blocking flock on a descriptor. Scope: wait on the cgroup directory event |
| scripts/gate_host.py:136-139 | R | Section 4.2 |
| scripts/gate_schedule.py:358; scripts/mutation_ownership.py:599-603 | S2, P | Wait primitive |
| scripts/mutation_ownership.py:286, 361, 517 (60, 10, 5 s on systemctl and tools) | T | Wait hang bound |
| scripts/propose_case_inputs.py:68 (traced worker at the ceiling) | T | Process hang bound (heavy child) |
| scripts/suite_slice.py:79; scripts/suite_labels.py:457; scripts/suite_equiv.py:194 (900, 1800 s) | T | Process hang bound (heavy child: each runs suites) |

### 4.6 Browser tests

| Site | Class | Replacement |
| - | - | - |
| engine/ui/playwright.config.ts:10-11 (test 90 s, expectation 10 s) | T | Expectation: the wait hang bound. Test: the process hang bound, measured as time without a completed step (section 6) |
| engine/ui/e2e/factory.spec.ts:295, 337, 467, 485, 541, 624-717, 795, 835, 881; layout.spec.ts:375; screens.spec.ts:38 (per-test limits of 120 to 600 s) | T | Removed; the configuration's bound governs |
| engine/ui/e2e/layout.spec.ts:663, 673; screens.spec.ts:32, 61 (waitForTimeout 250 to 600 ms) | S1 | Wait for the animation or layout event the page reports (transition end, or the settled signal) |
| engine/ui/e2e/run.spec.ts:107, 108, 174 (15 s, 15 s, 5 s) | T | Wait on the terminal's own reconnect and line-count state |
| engine/ui/e2e/fixtures.ts:36; factory-fixtures.ts:34; team-fixtures.ts:31 (harness must start in 60 or 90 s) | T | Wait on the harness's ready line or on its exit (pidfd), whichever comes first; wait hang bound |
| engine/ui/e2e/fixtures.ts:160; factory-fixtures.ts:73; team-fixtures.ts:69 | T | Same, for stop |
| suites/120, 121, 124 (run limits of 300, 900, 3000 s; for example suites/120_veldo_0131_factory_ui.py:117, 193, 207) | T | Process hang bound (a browser run is a heavy child) |

### 4.7 Engine timers: three kinds

The product's timers are of three kinds, and only one of them is a load hazard.

- Cadence: the interval at which a loop wakes when nothing else woke it. Its expiry decides nothing; the
  loop just looks again. Example: the service's accept interval of 0.25 s, the timeout of its select over
  the listener and the pipes (engine/.veldo/control_service.py:378, 4485, 4505). A cadence is not a load
  hazard. Where it stands in for a missing event it is product polling, a product ticket of its own (the
  channel poll of 1.0 s, engine/.veldo/control_service_channel.py:118).
- Contract timer: a duration the product promises and a user can see (heartbeat 10 s, liveness 30 s, stop 10
  s then 5 s, leadership fence 2 s, engine/.veldo/policy_contract.py:504-508; hook hold 10 s then kill 2 s,
  engine/.veldo/control_space_install.py:86-100). It stays. A scenario arms one of them and sets the rest
  to the wait hang bound through the profile; one row per timer lets it fire for real.
- Giving-up deadline: a bound on an internal operation whose expiry changes the outcome (a receiver killed
  instead of exiting, a release refused, a request refused, "unknown" recorded). Under load it fails work
  that was merely slow, on the user's machine as in the gate. These are the load hazard.

A lower bound in the product ("never sooner than five seconds after a fault",
engine/.veldo/control_service.py:159, 381) is none of these and is not a hazard.

### 4.8 Giving-up deadlines on the path of the wave 1 suites (in scope for VELDO-0358)

Each row below is crossed by at least one wave 1 suite (found by the modules each suite loads and the
processes it starts). A wave 1 suite that went red in the load-proof leg because one of these fired would
have no fix inside a specification that leaves them out, so they are in wave 1. Two replacements are
allowed: the event (the product waits for what it actually needs, under the wait hang bound), or a named
entry of the timers table (C17) whose value the suite's profile sets to the wait hang bound. The event is
used where the kernel already offers it; the table entry where the event needs a larger product change,
and that event then moves to wave 5.

| Constant and site | Kind of expiry | Wave 1 suites | Wave 1 replacement |
| - | - | - | - |
| RECEIVER_EXIT_SECONDS 2, engine/.veldo/control_launch.py:3939, used at 2083 | A receiver whose output has ended is killed if it has not exited in 2 s | 62, 63, 78, 151 | Event: its output end means it is exiting; wait on its exit (the child's pidfd) under the wait hang bound, then kill only at the bound |
| ORPHAN_SECONDS 5 with a 0.02 s poll, engine/.veldo/control_launch.py:1898-1902, 1924 | The account release is refused and stays pending | 62, 83 | Event: the worker's cgroup.events showing it empty, under the wait hang bound |
| Launch ACCEPT_SECONDS 30, engine/.veldo/control_launch.py:260, 2157, 3196, 3254 | A worker that has not reported in 30 s is refused | 62, 63, 78, 106 | Table entry (an accept bound the operator may want short); event (the worker's report or its exit as terminal) in wave 5 |
| Containment SETTLE_SECONDS 5 and TOOL_SECONDS 20, engine/.veldo/control_containment.py:79-80, 576, 621-622 | A group still settling after 5 s is recorded not empty, its result unknown | 63, 66_veldo_0042, 78 | Table entry; the manager's state-change signal in wave 5. The populated read already waits on cgroup.events (line 570) |
| Heartbeat SETTLE_SECONDS 1, SETUP_SECONDS 5, engine/.veldo/control_heartbeat.py:64-65 | The receiver stops what is left of a heartbeat that has not ended in 1 s | 62, 63, 78 (through the launch wrapper) | Table entry |
| serve_one read deadline 1.0 s and REPLY_SECONDS 1.0, engine/.veldo/control_client.py:477-485; engine/.veldo/control_service.py:379, 1851 | A client that has not finished sending in 1 s is refused; a reply not taken in 1 s is dropped | 66_veldo_0047, 83, 86_veldo_0189, 110 | Table entry. (The reply bound fires only when the client's receive buffer is full; it is in the table because it shares the constant, not because it was seen) |
| Client send and inspect 30 s, engine/.veldo/control_client.py:265, 333; engine/.veldo/control_client_api.py:81 | The command fails as unavailable | 66_veldo_0047, 83, 86_veldo_0189, 110 | Table entry (the parameter already exists; the default reads the table) |
| SQLite busy wait 30 s, engine/.veldo/control_store.py:409, 413 | A write that waited 30 s for the store's lock fails | every wave 1 suite | Table entry |
| LOGIN_SECONDS 30 and the 5 s initialization deadline, engine/.veldo/control_engine_claude.py:1631, 1759; engine/.veldo/control_engine_codex.py:553, 572 | Login status reads as unreadable; initialization fails | 78, 86_veldo_0189, 106 | Table entry |
| ANSWER_SECONDS 30 with a 0.2 s poll, engine/.veldo/control_factory_setup_upgrade.py:64, 436-446 | The upgrade's answer is taken as absent | 86_veldo_0189 | Table entry; the answer's own event in wave 5 |
| Role budget as the dispatch deadline, engine/.veldo/control_workflow_cycle_pm.py:378 | A product contract (the role's wall budget) | 110 | Contract: the suite's role budget is set by its profile to the wait hang bound except in the row that tests the budget |

Not changed in wave 1, with the reason: the service's accept interval (cadence), ADOPTION_RETRY_SECONDS (a
lower bound), the channel poll (cadence; product ticket), and the memory adapter's 5 s SQLite wait
(engine/.veldo/control_memory_adapter.py:354), which no wave 1 suite reaches (suite 105 does, in wave 4).

The timers table is the only place these values live. It reports its effective values: an in-process suite
reads them from the table, and the service and the launch wrapper write them into their start record. That
report is what a suite row checks (spec AC15), so a seam that is ignored is seen, not assumed.

### 4.9 Engine timers outside wave 1

The remaining timers and the tool guards (git 15 to 120 s at about 40 sites, for example
engine/.veldo/control_document.py:69, control_readset.py:44-116, dispatch.py:754-772; ssh-keygen and openssl
10 to 30 s; systemctl 20 s; the handoff's 15 s and 45 s, control_agent_config_handoff.py:103, 613; spool
5 s and 60 s, control_space_spool.py:177-185, 619; effect executor 20, 30, 5 s,
control_effect_executor.py:34-36; capsule and fix validation kill wait 5 s) become table entries or events
in wave 5, ordered by the suites that enter the proven set and would otherwise cross them. A wave 2 to 4
specification that converts a suite takes the table entries its suite crosses, by the same rule as 4.8.

Kernel waits already done right, for reference: engine/bin/veldo:962-1006 and 1217-1237 (pidfd and poll with
no time limit, no interval).

## 5. Components

| Id | Component | Where | Responsibility | Consumes | Offers |
| - | - | - | - | - | - |
| C1 | Wait primitive | suites/support/waits.py (new); it replaces suites/shared.py wait_for (lines 98-121) and the pipe barrier (lines 173-205) | The only place a suite may block. Waits for a done condition and a terminal condition; reports done, impossible or hung, in the report shape shared.wait_for already returns (what was waited for, the bound and its source, the last observation) plus the terminal condition and the event sources | C2 sources, the hang constants | One call for tests; a result with the name of the wait and what was last seen |
| C2 | Event sources | same module | Turn kernel notifications into wakes: a pidfd, a readable descriptor (pipe, socket), a path event (inotify on the nearest existing ancestor of the path, re-armed one level down on each creation), a store change (inotify on the store's write-ahead file, then the condition re-read), a cgroup becoming empty (cgroup.events), a unit's state (the unit's cgroup) | Linux | Wake-ups with no interval and no timer |
| C3 | Latch holder | suites/support/holders.py (new) | A fixture process that stays alive until the test releases it or exits: it blocks on a pipe the test holds, so the kernel releases it when the test dies | none | Replaces every sleeping holder |
| C4 | Supplied clock and check acknowledgment | the timers table plus the seams of 4.8 and 4.9 | Lets a suite move the product's clock past a timer and ask "did you check?", so a timer that never fires is seen as an answer and not as silence | The product's existing clock parameters (for example the offsets at engine/ui/e2e/harness.py:257 and suites/71_veldo_0130_api.py:631) | Deterministic timer rows |
| C5 | Row outcome model | scripts/selftest.py, scripts/suite_labels.py | A row is passed, failed or hung. A hung row carries the wait's name and source line. The first hang ends the suite's process; rows not reached print as not run | C1 results | Three-valued rows to the legs and to the mutation driver, in one line format both read |
| C6 | Progress watchdog | scripts/selftest.py (in the suite process), scripts/check_gate_mutations.py and scripts/check_first_use.py (around a child) | Ends a process only after the process hang bound has passed with no progress evidence: in a suite process, a row starting or ending re-arms it; around a heavy child, a line on the child's output re-arms it. Before ending, every thread's stack is written to the log. In the suite process it is the standard library's faulthandler timer, re-armed at each row event, which writes stacks and exits even when the interpreter is stuck | faulthandler; the row events of C5 | A hang that names where it hung; no bound on total time anywhere |
| C7 | Residue check | scripts/selftest.py | At the end of each suite: threads still alive, child processes, listening sockets. Any of them is a failed row of that suite | /proc/self | Removes cross-suite leftovers (gate 8) |
| C8 | Suite per process | the load-proof runner now; the functional legs when VELDO-0221 is built | One interpreter per suite | The existing suite selector | Isolation without ordering luck |
| C9 | Verdict rule | scripts/check_gate_mutations.py, scripts/mutation_observer.py | Decides rejected, survived, hung_not_killed, control_failed; records kill_by per case as assertion, terminal or unproven | C5 rows; the baseline (which suites are unconverted) | Receipt fields per case (section 7) |
| C10 | Page settled signal | engine/ui/e2e fixtures (and engine/ui/src where a panel does not yet expose its state) | Counts requests sent and not answered, and exposes each panel's state; a test acts when the page is settled | The page | Replaces fixed visibility waits and waitForTimeout |
| C11 | Port holder | suites/support/ports.py (new), from engine/ui/e2e/harness.py:70-78 | Keeps a chosen port bound until its server binds it | none | Replaces read-and-release at suites/support/v171_tailscale.py:123 |
| C12 | Census check | scripts/check_wallclock.py (new; canon in engine/scripts) | Finds every site by the rules of section 9 in the observed scope, compares the multisets, refuses growth | Syntax trees; the opened-files record (C18); both lists from the authority and the candidate | A gate stage; a report listing every site |
| C13 | Baseline and exceptions | scripts/suites/wallclock_baseline.json, scripts/suites/wallclock.json (new, protected) | The baseline is a multiset of unconverted sites that can only shrink; the exceptions are a multiset of declared sites that only the owner can grow | Owner approval for any exception or any baseline growth | Input to C12, to the proven set of C15, and to kill_by of C9 |
| C14 | Load generator | scripts/gate_load.py (new) | Applies the stated CPU, memory and disk load by construction inside the gate's own scope, and proves that its generators lived for the whole leg | The delegated scope of VELDO-0220; sched_setaffinity | A load record: generator liveness and counters, probe readings as data |
| C15 | Load-proof leg | scripts/gate_legs.py, scripts/verify.sh | Runs the proven set once, and changed suites repeatedly, under C14; any failed or hung row is the gate's red | C8, C14, C13, C18 | Stage result and the load record in the stamp |
| C16 | Paired performance stage | follow-on specification | Candidate against last landed, interleaved, judged on the difference | The authority checkout as the base build | The only place a latency is judged |
| C17 | Timers table | engine/.veldo/timers.py (new), read by policy_contract and by every module of 4.8 | One row per contract timer and per giving-up deadline: name, value, where armed, how a profile sets it; reports effective values | none | What C4, the profiles and the suites set and read |
| C18 | Opened-files record | scripts/selftest.py (an audit hook on open and import in every suite process) | Records, per suite, every file under scripts/ and proof/ the suite opened or imported, however the path was computed | The interpreter's audit hooks | The census scope (C12), the proven set and "changed suite" (C15), written beside the gate stamp |

### 5.1 Run trace: one wait

1. A row needs "the worker of dispatch D wrote its marker". The test names the done condition (the marker
   file exists) and the terminal condition (the dispatch's record has left prepared, accepted and running).
2. C1 opens a path watch and a store watch. If the marker's directory does not exist yet, the watch is set
   on its nearest existing ancestor and moved one level down on each creation event until it reaches the
   directory. It then reads both conditions once (the event may already have happened).
3. The process sleeps in one poll call over those descriptors with the wait hang bound as its only timeout.
4. A wake re-reads both conditions. Done returns the marker. Terminal returns "impossible" with the record's
   state, and the row fails at once with that evidence. This is the case that used to cost ten seconds nine
   times over (teeth.md:225-238).
5. If the bound passes, C1 returns "hung" with the wait's name and the last reading of both conditions. C5
   prints the row as hung, C6 writes the stacks, and the suite's process ends.

### 5.2 Run trace: pattern W, absence between two events

1. The row claims "an idle receiver is not woken while other launches are refused".
2. The test reads the receiver's wake counter, then causes its own first event (the first refused launch)
   and its last (the sixth), waiting for each refusal's record through C1.
3. It reads the counter again. The claim is the difference being zero.
4. No number of seconds appears. Every periodic timer of the profile is disabled for this worker, so nothing
   legitimate can wake it between the two readings however long the six refusals take.

### 5.3 Run trace: a product timer, with the supplied clock

1. The row claims "a worker past its deadline is stopped with deadline_stop true".
2. The test launches the worker held by a latch, with a deadline one hour away and a supplied clock.
3. It waits for the launch's running message, moves the clock two hours ahead, and sends the receiver a
   check request.
4. The unmutated product stops the worker; the test waits for the end message and reads the record.
5. A mutant that ignores the deadline answers the check request with "nothing due". That answer is the
   terminal condition: the row fails by evidence in milliseconds and nothing waits for a bound.

Where a timer cannot take a supplied clock (the hook's hold, enforced by the coreutils timeout program), the
row asserts that the timer is armed with the right value, and one row lets it fire for real and asserts the
cause, with a lower bound only.

### 5.4 Run trace: a slow leg that is not hung

1. The confined unit leg runs 160 suites in one interpreter (until VELDO-0221) and takes 1,913 s idle.
2. At each row's start and end, selftest re-arms the faulthandler timer at the process hang bound.
3. Under the load-proof generator the leg takes three times as long, about 96 minutes. No row is ever 3,600 s
   without a successor event, so the timer never fires and nothing is ended.
4. If one row blocks forever outside the wait primitive, the timer fires 3,600 s after that row's start,
   writes every thread's stack (the blocking line is in it), and the process exits; the leg is red with the
   row and the line named.

## 6. Hang bounds

There are two constants and one rule, and no other duration is allowed in a suite or in the gate's tooling.

The rule: a hang bound measures time since the last progress evidence of the thing it bounds, never total
time. A wait has no progress other than its event, so its bound runs from its start. A process makes
progress in steps (rows, lines, completed cases), so its bound runs from its last step. Nothing bounds a
whole gate, a stage, a leg, the mutation stage, or a nested gate or selftest run as a total: each of those is
made of processes and waits that are bounded by progress, so a hang inside it is always caught where it is,
and slowness of the whole is never "hung".

| Constant | Value | Measured from | Applies to | Why this value |
| - | - | - | - | - |
| Wait hang bound | 600 s | The start of one wait | Every single wait: C1, joins, sockets, queues, select, page expectations, and every light child call (a git, systemctl, ssh-keygen, openssl or similar tool call) | The longest legitimate single wait seen under twice the gate's own load is 15 s (suite 63's window with 80 suite processes on 20 cores, teeth.md:420-421). 600 s is forty times that. It is already the largest value in common use (35 deadline sites in suites) |
| Process hang bound | 3600 s | The last progress evidence: a row starting or ending in a suite process (re-armed per row, so a shared interpreter running many suites is bounded per row, not per leg); a line on a heavy child's output | A suite process, a mutation worker, and a heavy child: a child that runs a suite or a selftest, a gate stage, a browser run, a package install, or qualify | The longest suite alone is about 240 s (specs/VELDO-0221-a-gate-leg-runs-its-suites-as-parallel-closure-shards.md:160-161), and no single row is longer. At ten times slower a whole suite is 2,400 s, still under one bound, and a row far less. It is above the wait bound so that the inner wait always names itself first. Children given 900 to 3,000 s today (suites/120_veldo_0131_factory_ui.py:117, 193, 207; suites/126_veldo_0230_qualify_reproduces.py:124; suites/24_veldo_0007_install_and_run.py:1186) are all heavy children by this rule |

The light or heavy decision is by what the child runs, from that closed list, and not by how long it is
expected to take, so a builder does not pick. The census enforces it: R3 accepts the process constant only
as the timeout of a call whose command runs one of the heavy kinds (section 9).

The existing 21,600 s ceiling of scripts/check_first_use.py:137 goes, with the measured budget beside it
(lines 135-138: twice the measured time, floor 1,800 s): both are claims about speed. The nested selftest it
bounds has its own progress watchdog, and the parent watches the child's output lines under the process hang
bound.

Uniform matters more than the exact numbers. A per-site number is a claim about speed, and every per-site
number in section 2 was eventually wrong. With one value per kind there is nothing to tune and nothing for a
builder to shorten "because this one is fast".

A large bound is affordable only because a wait almost never reaches it. That is what the terminal condition
is for: a thing that will not come is recognized by an event, in milliseconds. And when a wait does reach
the bound, the suite's process ends there, so one hang costs ten minutes once, not ten minutes per later row.
A gate with a genuine hang is ten minutes longer and red with the wait named and the stacks written.

## 7. Mutation: what counts as a kill

Today the driver has the right instinct at one level only: a worker that passes its deadline is reported as
mutation_budget_exceeded and the stage fails (scripts/check_gate_mutations.py:789-794). Inside a suite,
though, a row that fails because a bounded poll ran out reads exactly like a row that failed on evidence.
A mutant can then be "rejected" because the machine was slow, and a slow control voids every case that
shares it.

A case is rejected only when all of these hold:

1. Its baseline and no-op controls passed every row, with no hung row.
2. The mutant's process ended by itself, without its progress watchdog firing.
3. At least one of the case's declared target rows failed, and that row failed on evidence: an assertion
   over state the test read, or a wait that ended on its terminal condition.
4. No target row is hung or not run.

The outcomes:

| Outcome | Meaning | Gate |
| - | - | - |
| rejected | The four conditions hold. The receipt records, per case, which row and kill_by | Counts |
| mutation_survived | Every target row passed | Red, as today |
| hung_not_killed | The only failing target rows are hung; or a target row was not run because an earlier row hung; or the worker's progress watchdog fired | Red. The message names the wait. The fix is a terminal condition in the test, or a real hang fixed in the product |
| control_failed | A control failed or hung on the unmutated suite | Red, reported as the suite's own red and not as "voided cases". The load-proof leg runs every proven control before the stage, so this should be found there |

kill_by, per rejected case: "assertion" (the failing target row is an assertion over state); "terminal"
(it is a wait that ended on its terminal condition); "unproven" (the suite or a file it opens still has a
baseline entry, so its failed row may still be the expiry of a legacy bounded poll that reads as a failed
assertion). An unproven kill counts as rejected today, as it does now, and it is the wave 2 work list: every
case with kill_by unproven, read from the receipts, by suite. The list shrinks as suites leave the baseline
and reaches zero when the baseline is empty. No separate reporting run is needed to produce it.

The worker deadline of VELDO-0215 (three times the measured time, floor 120 s) stops being a verdict. The
measured times stay and are used for what they are good at: ordering admission and estimating the stage.
Every worker runs under its progress watchdog.

## 8. Real performance requirements

One declared latency was found: VELDO-0040's exit notification, "the 0.75 second latency bound"
(specs/VELDO-0040-process-containment.md:232), asserted as an absolute number on the real clock at
suites/63_veldo_0040_containment.py:1069. (The 0.75 at line 722 is on the fake manager clock and asserts the
product's own arithmetic, not a latency.) The hook's hold (10 s) and the session hook's 15 s are not
latencies; they are timers the product arms, and section 4.3 asserts the arming. No other specification
declares a latency the product must meet, and the gate's own catalog says so (scripts/verify.sh:241).

The functional property VELDO-0040 needs is "the exit is recorded by notification, not found by a poll".
That is asserted without a number in wave 1: the receiver recorded the exit from its pidfd wake, with one
wake and zero poll intervals between the exit and the record, and recorded_at is after exit_at. A product
change back to polling breaks the row by its wake count however fast the machine is. The latency
(recorded_at minus exit_at) is written into the row's observed data on every run and is the input of the
paired stage when it exists. Until then no absolute number about it is judged anywhere.

A latency requirement is measured like this and in no other way:

1. It lives in the performance stage, not in a suite. The functional row keeps the part that is not about
   speed.
2. The stage builds nothing new: the base is the authority checkout the gate already runs from, which is
   the last landed build; the candidate is the tree under test.
3. It runs thirty pairs. In each pair the two builds run the same scenario one after the other on the same
   cores, and the order alternates from pair to pair, so that whatever the machine is doing falls on both.
4. The verdict is on the difference only: red when the candidate's median is more than 25 percent slower
   than the base's across the pairs and the candidate was the slower one in at least 24 of the 30 pairs.
   Otherwise green. No absolute number is compared with anything.
5. A requirement that has no base to compare with (a new scenario) records its measurements and judges
   nothing until the next landing.

The pair count and the two thresholds are starting values. The core timing pilot uses the same shape
(live state:9082, 9184) and its results should set them.

## 9. The census check

The check is a gate stage that reads source, runs in seconds, and has no notion of load.

### 9.1 Scope, by observation

The scope is observed, not inferred, because suites load fixtures by computed path (803 uses of
spec_from_file_location, exec or runpy in scripts/suites). It is the union of:

- every file the authority's last opened-files record (C18) lists for any suite: every file under scripts/
  and proof/ a suite process opened or imported, however the path was made;
- every file under scripts/, proof/ and engine/ui/e2e the candidate changed (so a new fixture is in scope
  before any record has seen it);
- engine/ui/e2e, engine/ui/playwright.config.ts and the gate tooling of section 4.5, always;
- for R3 only, the engine files of section 4.8, where the timers table constants are the allowed names (so a
  new short giving-up deadline on the wave 1 path is refused).

Until the first record exists, the scope is every file under scripts/ and proof/.

### 9.2 The rules

On the syntax tree for Python, with every call resolved through the file's own imports and aliases
(including a module bound by an `__import__` call) and every name resolved to a module-level numeric
constant where it is one; on tokens for TypeScript; on text for strings that are run as a command or as
source. A site is any of:

| Rule | Site |
| - | - |
| R1 sleep | A call that resolves to time.sleep or asyncio.sleep; a command list or string whose program is sleep with a number; the word sleep followed by a number inside a string that a suite runs as source; waitForTimeout; a setTimeout whose callback rejects or fails |
| R2 clock | Any read that resolves to time.time, time.monotonic, time.perf_counter, their _ns forms, datetime.now, datetime.utcnow, Date.now or performance.now. A suite that needs a timestamp as data takes a stamp from the support module, which is the one allowed reader |
| R3 timeout | A timeout given as anything other than zero, None (unbounded; the watchdog bounds it) or one of the two named constants, at: the keyword timeout on any call; and the positional places of this closed table: threading.Thread.join argument 0, threading.Event.wait 0, threading.Condition.wait 0 and wait_for 1, queue.Queue.get 1 (when argument 0 is a literal block flag) and put 2, subprocess.Popen.wait 0 and communicate 1, socket.socket.settimeout 0, socket.create_connection 1, select.select 3, a selectors selector's select 0, select.poll's poll 0, signal.alarm 0, signal.setitimer 1, threading.Timer 0, asyncio.wait_for 1, a Barrier's timeout, and in TypeScript the timeout option of a page expectation or action, test.setTimeout and the configuration's timeout fields. The process constant is accepted only on a call whose command is a heavy child (section 6) |
| R4 duration bound | A comparison that puts an upper bound, against a number, on a value named or derived as a duration (elapsed, took, waited, seconds, duration, latency, window, or the difference of two values ending in _at) |

A method call whose receiver is not resolvable is matched by method name and position only when the
argument at that position is numeric (a literal, a numeric constant name, or arithmetic over them). String
join takes an iterable and dict get takes a key, so `", ".join(parts)`, `os.path.join(a, b)`, `d.get(k)` and
`d.get(k, 5)` are never sites; measured on scripts/suites, this rule flags 33 of the 871 `.join` calls (all
thread and process joins) and none of the 19,846 `.get` calls.

There is no "missing timeout" rule. An unbounded blocking call is bounded by the progress watchdog, which
names the stack where it blocked; flagging the 1,432 suite calls with no timeout would add noise and no
safety.

R4 is a name rule and can be evaded by naming a duration something else. Two things close it. The support
module's stamp is an object that supports ordering and at_least(start, seconds) for a lower bound, and no
subtraction; since R2 refuses every other clock read, an upper bound on a real duration cannot be written in
a suite without a site R2 already counts. And the load-proof leg catches a timing assertion that is evaded
anyway.

The wait primitive's own module and the stamp are the one place R1 to R3 do not apply.

### 9.3 Baseline and exceptions: multisets, read from both trees

A site's key is (file, rule, normalized source text, qualified name of the enclosing function). A list is a
multiset: each key carries a count. The baseline (scripts/suites/wallclock_baseline.json) records every
unconverted site; the exceptions (scripts/suites/wallclock.json) record the sites that are right to keep, each
with its kind, reason and approving specification.

The stage reads the baseline and the exceptions from the authority checkout and the baseline also from the
candidate, finds the candidate's sites, and for each key computes:

- allowed = authority baseline count plus authority exceptions count;
- red (wallclock_site) when the candidate has more sites for the key than allowed. So a duplicated line is
  refused even when an identical line is baselined in the same function, and a copy of an excepted line is
  refused unless the exception's count is raised by the owner;
- required candidate baseline count = the smaller of (candidate sites minus authority exceptions, floored at
  zero) and the authority baseline count;
- red (baseline_stale) when the candidate's baseline count for the key differs from the required count.
  A candidate that converts a site must lower the entry with the fix in the same change, and a candidate
  that raises an entry is refused, because the required count can never exceed the authority's.

So the baseline shrinks without any approval (a candidate subset of the authority), and it can grow only
by an owner-approved change to the protected file. Exceptions are read from the authority alone; a candidate
cannot grant itself one.

A consequence, deliberate: moving or rewriting an unconverted line (another function, other text) makes it a
new key and is refused. Touching a legacy site means converting it.

Exception kinds, closed: lower_bound (a real wait whose only reader is a lower bound, for example the 5.25 s
late step of suites/86_veldo_0148_re_land.py:1382); timer_fires (the one row per contract timer that lets
the real timer fire); subject (source text that is the subject of a test or fixture pacing that nothing
waits on, for example suites/13_warp_0623_codified_live.py:6742-7354, suites/42_veldo_0102_fixval.py:400,
suites/04_run_status_reader_veldo.py:761); supplied_clock (a comparison over values from a fixture clock the
test controls, for example suites/63_veldo_0040_containment.py:722). An entry of any other shape is refused.

### 9.4 First run and bootstrap

The census tool's first run, at the commit VELDO-0358 is built on, is the authoritative inventory and
replaces appendix A. It is run in report mode and writes the baseline from what it found, with each key's
class (by the use rule of 4.1). The counts of section 4.1 are the check on it. The landing that introduces
the stage carries that baseline as a protected file and is owner-approved; while the authority has no
baseline file the stage is in report mode and judges nothing. From the next landing on it is required.

### 9.5 Falsifiers

Registered mutants of the check: one per rule, each of which stops reporting that rule's sites
(wall358-sleep-admitted, wall358-clock-admitted, wall358-timeout-admitted, wall358-duration-bound-admitted),
one for the positional table (wall358-positional-ignored); and for the lists: the baseline read from the
candidate only (wall358-baseline-from-candidate), a stale entry tolerated (wall358-stale-entry-tolerated),
counts ignored so that a duplicate matches (wall358-count-ignored), and the scope taken from the import
statements instead of the record (wall358-scope-inferred).

## 10. The load-proof leg

The census removes the classes that can be seen in source. The leg proves the result by running the suites
on a machine that is deliberately far busier than any gate has been.

Where it runs. After the functional unit and integration stages are green and before the mutation stage.
Its red ends the gate before the two-hour mutation stage starts. Gates 9, 10 and 11 would each have ended
about two hours earlier and with the failing suite named, instead of with 5, 51 and 45 voided cases.

What it runs. Each suite in its own process (C8), through the same confinement split as the functional
legs, eight suites at a time.

- Every suite of the proven set runs once. The proven set is computed: a suite is in it when neither the
  suite nor any file in its opened-files record has a baseline entry. The baseline cannot grow, so the set
  cannot shrink. At the end of the work of section 11 it is every suite.
- Every changed suite of the proven set runs repeatedly. A suite is changed when its own file is in the
  gate's diff against its base, or when a changed file appears in the opened-files record of at most three
  suites (a fixture of its own). A change to a file that more suites open (scripts/suites/shared.py,
  suites/support/waits.py) adds no repetition: the whole proven set already runs once.
- The repetition count of a changed suite is twenty, lowered so that the repetitions of all changed suites
  fit in the leg's repetition allowance: thirty minutes of loaded time at eight slots, computed from each
  suite's loaded time in the previous leg's record, with a floor of five. The allowance is a figure for the
  owner to confirm; it decides how many runs are made, never a verdict.

### 10.1 The load, by construction

On this host the user manager delegates only the cpu, memory and pids controllers (scripts/gate_host.py:26-27;
the user manager's cgroup.controllers reads "cpu memory pids"), so a cpuset for the leg is not available
without a change to the host's systemd configuration. The CPU level is therefore built with CPU affinity,
which needs no controller.

| Kind | Level | How it is made | How it is known to have been applied |
| - | - | - | - |
| CPU | Each CPU the suites may use carries three always-runnable spinners beside them | The leg's suites and the spinners are bound by affinity to the same set of K CPUs (K = 8 on this host, as many as the leg's slots); three spinners per CPU of the set (24 here) | Every spinner's pidfd stays unreadable (alive) from the leg's start to its end, and each consumed CPU time. A suite process on a CPU of the set gets at most a quarter of it while the spinners run; that is a property of the scheduler's fair share, not a measured ratio |
| Memory | The suites run under reclaim | The leg's cgroup gets a memory.high of 60 percent of the peak the previous load-proof leg recorded for the same proven set at the same concurrency. The first leg sets none and records its peak. memory.max is not lowered, so nothing is killed by design | Recorded as data: the memory.events high counter |
| Disk | Writes and flushes compete on the file systems the suites write | One writer per four CPUs of the set (2 here), each writing, flushing and removing a 256 MiB file on the file system of the scratch root and of the checkout | Every writer alive for the whole leg and its byte counter above zero at the end |

All generators run inside the gate's own delegated scope (scripts/gate_host.py:26, 270), in a cgroup beside
the leg's, and are removed with the scope. Memory pressure is made inside the leg's own cgroup, so the leg
cannot push other work on the machine out of memory (the incident at live state:2853 is the reason). The
CPU load is confined to K of the host's CPUs by affinity. The disk load cannot be confined without the io
controller, which is not delegated; it is bounded by its count (two writers) and it is the price of
exercising the store's flushes and busy waits under contention.

The slowdown probe (a fixed loop of one CPU-second, wall time over CPU time, run on a CPU of the set) is
recorded in the load record as data. It is not a verdict: a reading that depends on the host's speed would
be a load-sampled verdict under another name. The leg is red as load_not_applied only when a generator
process was not alive for the whole leg, which is a defect of the leg like any other failed check. Nothing is
rerun and nothing is voided.

Verdict. Any failed row and any hung row is the gate's red. The fix is in the test or in the product.

### 10.2 Cost

The functional unit legs take 1,913 s (confined) and 1,252 s (unconfined) of about one core each
(specs/VELDO-0221-a-gate-leg-runs-its-suites-as-parallel-closure-shards.md:132; teeth.md:317-319), about 3,200
CPU-seconds, and about 3,800 with one interpreter per suite. At a quarter of a CPU per suite and eight slots
that is about 32 minutes for the whole proven set, never less than the longest suite (240 s alone, 16 minutes
loaded). Repetitions add at most the thirty-minute allowance; the worst single suite today is suite 101,
whose twenty runs would cost about 80 minutes at eight slots, so it runs eight times. While the proven set
is small, after wave 1, the leg costs about 10 to 15 minutes plus repetitions. At full coverage a typical
gate grows by 35 to 60 minutes on a gate of 2 h 18 min to 3 h 20 min, and it saves the two-hour mutation
stage on every red the leg finds first. The numbers are estimates from recorded leg times; the first leg
records the real ones and the record replaces them.

### 10.3 Falsifiers

A canary fixture suite in which a child does a tenth of a CPU-second of work and writes a marker, and the
parent sleeps 0.2 s and then reads the marker, must be green alone and red in the leg: alone the work takes
0.1 s; at a quarter of a CPU it takes at least 0.4 s. If it is green in the leg, the leg is not loading.
Registered mutants: the generator started with no spinners and reported alive; the leg's suites not bound to
the spinners' CPUs; a red row of the leg not blocking the gate; a red suite run a second time.

## 11. Order of work

The order is by what has actually made gates red. Waves 0 and 1 are one specification (the draft beside
this document); each later wave is its own.

| Wave | Work | Effect on the next gates |
| - | - | - |
| 0 | C1, C2, C3, C5, C6, C7, C11, C17 (the table and its effective-values report, empty of entries), C18; the census (C12, C13) with the baseline from its first run; the verdict rule (C9) with kill_by; the generator and the leg (C14, C15) | No new clock dependency can land. A hang names itself and slowness never reads as a hang. Leftover threads are a red of the suite that left them |
| 1 | Every site of section 4.2: suites 62, 63, 66 (both), 71_veldo_0138, 78, 83, 86_veldo_0189, 106, 110, 120, 121, 124, 151; the browser fixtures and configuration; scripts/gate_host.py:136; scripts/check_first_use.py's budget; the mutation driver's worker deadline; suites/support/v171_tailscale.py:123; and the giving-up deadlines of section 4.8 these suites cross | The mechanisms behind every red of gates 7 to 12 are gone, these suites enter the proven set, and the product no longer gives up on their paths because the machine was slow |
| 2 | The cases with kill_by unproven, by suite | Every kill is by evidence |
| 3 | The timing assertions of section 4.3 and the settle sleeps and windows of section 4.4 | The classes that give false reds and false greens are gone from suites |
| 4 | The remaining bounded polls, timeouts, holders and D1 and D2 clock reads, suite by suite, largest count first (appendix A.1), each with the timer table entries its suite crosses | The proven set reaches every suite and the baseline is empty |
| 5 | The remaining giving-up deadlines and tool guards (4.9), the events that replace the wave 1 table entries, and the supplied clock where a timer row needs it (C4) | The product no longer fails a user's command because a local tool or the machine was slow |
| 6 | The paired performance stage (C16), fed by the latency data suite 63 records from wave 1 | Latency is judged, by difference only |

Waves 2 to 4 can run in parallel by suite. A suite leaves the baseline only whole (all its sites and those
of the files it opens), because entering the proven set is what proves the conversion. The build order
inside waves 0 and 1, split into briefs for parallel builders, is at the end of revision-notes.md.

## 12. What is deliberately not built

- No quiet window, no waiting for a quiet host, no machine-wide pause. The owner rejected these on
  2026-11-18 (Telegram 42171).
- No rerun of a red, quiet or otherwise, and no "invalid" or "not judged" verdict for a result under load.
- No sampling of host load, pressure or other tenants' CPU to classify a red, and no verdict on a measured
  speed ratio (the slowdown probe is data). VELDO-0223 is superseded whole: its sampler, its quiet rerun, its
  INVALID exit and its "contended run records no measurement".
- No bound on the total time of a gate, a stage, a leg or a nested run.
- No per-site tuned deadline and no deadline derived from a measured time.
- No retry inside a test. A bounded retry of an operation that reported a transient failure by name (the
  resolve of a path whose link is being swapped, 0b767d26) is the operation's own contract and stays.

The host lock of VELDO-0220 is unchanged and is not relied on. It keeps two heavy gates from running at
once, which is about memory and elapsed time; with this design it is no longer what keeps a gate green.

## 13. Open points, and what was not verified

- Appendix A is a mechanical reading with the rules of section 9; the class of each clock read is assigned
  by its use, and a builder reading a site may move it (a P that is really a D2). The census tool's first run
  is the authoritative list (9.4).
- The cause of the gate 8 red, and of service/pm-settled-due, is not known (teeth.md:334-342). This design
  removes the one anomaly observed, sets the product timers on that path to the hang bound, and makes a hang
  or a leftover name itself; it does not claim to have fixed those rows.
- The cause of the gate 11 browser red was not reproduced (teeth.md:546-575). The page settled signal
  removes fixed visibility waits; whether that was the cause is not shown.
- The load levels (three spinners per CPU of a set of eight, 60 percent memory.high, one writer per four
  CPUs) and the leg's cost are design values. No loaded run was made for this document. The canary of 10.3
  is what shows the level exposes a sleep-synchronized test; the first build step also runs the pre-fix
  follower row under it, which failed 105 and 109 runs of 200 under 40 processes and 20 busy loops
  (teeth.md:511-513).
- Whether every contract timer of 4.7 can already be set by a suite was not checked constant by constant
  outside wave 1. For wave 1, 4.8 names each constant and its replacement.
- One run under load does not find a race that shows once in a thousand runs (suite 78's row was caught 5
  times in 1,000, teeth.md:436-437). The leg finds the frequent ones and the repetition of changed suites
  finds more; the rare ones are removed by class, through the census, and not by repetition.
- Specification numbers 0351 to 0357 are already taken in other worktrees, so the draft is VELDO-0358.

## Appendix A. Every site found, by file and line

### A.0 How to read it

Worktree space-0329b at f5055400. Suites (A.1) are read with the rules of section 9.2 and classed by use
(4.1). Columns: S1 (a sleep outside a loop, settle or window; read each), S3 (a sleep of 30 s or more, or a
sleep command), P (a clock read used in a bounded poll), F (fixture pacing inside a fake class); then counts
of S2 (poll intervals), D1 (timestamps as data), D2 (deadlines as product input) and T (R3 timeouts). Class
totals for scripts/suites: S1 28, S2 83, S3 7, F 1, P 201, D1 628, D2 85, T 890, in 183 files. Sleeps inside
fixture source text (112 in 43 files) are listed after the table; most are holders (S3) or subject text.

The 40-site sample of the validation is reflected: the lines it found to be deadlines as product input
(100:148, 101:551, 97:79, 113_veldo_0112:201, 123:179) are now D2; the future timestamps (58_veldo_0028:1355,
60_veldo_0052:520, 65_veldo_0067:231, 72_veldo_0075:373, 96:248) are D1; 04:761 is F; 06:981, 20:398 and
23:707 are not sites; 139:565 (a fixture clock) and 115:132 (a lower bound) are no longer listed as polls;
13:6742 is subject text.

A.2 to A.5 are from revision 1's pattern scan and are kept for their line lists; their P column counts any
line that builds a deadline from the clock, so it includes D1 and D2 sites. The census's first run
supersedes them.

### A.1 Suites (scripts/suites/)

| File | S1 lines | S3 lines | P lines | F lines | S2 | D1 | D2 | T |
| - | - | - | - | - | - | - | - | - |
| 04_run_status_reader_veldo.py | - | - | - | 761 | 0 | 0 | 0 | 3 |
| 09_action_whitelist_warp_1205.py | - | - | - | - | 0 | 0 | 0 | 2 |
| 12_warp_1210_hardening_four.py | - | - | - | - | 0 | 0 | 0 | 1 |
| 13_warp_0623_codified_live.py | - | - | - | - | 0 | 0 | 0 | 2 |
| 19_veldo_0002_work_state.py | - | - | - | - | 0 | 2 | 0 | 0 |
| 23_veldo_0006_budget_state.py | - | - | - | - | 0 | 1 | 0 | 0 |
| 24_veldo_0007_install_and_run.py | - | - | - | - | 0 | 0 | 0 | 4 |
| 26_veldo_0009_install_stamp.py | - | - | - | - | 0 | 0 | 0 | 1 |
| 27_veldo_0010_evidence_provenance.py | - | - | - | - | 0 | 0 | 0 | 1 |
| 28_veldo_0015_clock_standdown.py | - | - | - | - | 0 | 2 | 0 | 0 |
| 36_veldo_0023_journal.py | - | - | - | - | 0 | 0 | 0 | 7 |
| 37_veldo_0024_replica.py | - | - | - | - | 0 | 0 | 0 | 1 |
| 38_veldo_0025_membership.py | - | - | - | - | 0 | 2 | 0 | 4 |
| 39_veldo_0026_revocation.py | - | - | - | - | 0 | 0 | 0 | 5 |
| 40_veldo_0101_capsules.py | - | - | 226, 240, 242 | - | 1 | 0 | 0 | 16 |
| 41_veldo_0103_assessor.py | - | - | - | - | 0 | 0 | 0 | 5 |
| 42_veldo_0102_fixval.py | - | - | - | - | 0 | 4 | 0 | 0 |
| 43_veldo_0104_proofcheck.py | - | - | - | - | 0 | 0 | 0 | 1 |
| 47_veldo_0107_ipc.py | 515 | - | - | - | 1 | 0 | 0 | 11 |
| 48_veldo_0108_relay.py | - | - | - | - | 1 | 0 | 0 | 16 |
| 49_veldo_0109_unavailable.py | - | - | - | - | 1 | 0 | 0 | 4 |
| 53_veldo_0123_mutations.py | - | - | 293, 319 | - | 1 | 2 | 2 | 3 |
| 54_veldo_0118_grammar.py | - | - | - | - | 0 | 2 | 0 | 0 |
| 55_veldo_0119_agreement.py | - | - | - | - | 0 | 2 | 0 | 0 |
| 56_veldo_0027_signing.py | 536 | - | 118 | - | 0 | 9 | 2 | 8 |
| 57_veldo_0120_policygrammar.py | - | - | - | - | 0 | 2 | 0 | 0 |
| 58_veldo_0028_effects.py | - | - | - | - | 0 | 10 | 2 | 10 |
| 58_veldo_0031_claims.py | - | - | - | - | 0 | 3 | 0 | 11 |
| 58_veldo_0035_snapshots.py | - | - | - | - | 0 | 2 | 0 | 4 |
| 58_veldo_0036_reservations.py | - | - | - | - | 0 | 0 | 0 | 6 |
| 58_veldo_0046_notifications.py | 454, 456 | - | - | - | 0 | 2 | 0 | 7 |
| 59_veldo_0031_review.py | - | - | - | - | 0 | 8 | 0 | 7 |
| 59_veldo_0037_aliases.py | - | - | - | - | 0 | 2 | 0 | 7 |
| 59_veldo_0043_graph.py | 1153 | - | - | - | 0 | 2 | 0 | 1 |
| 60_veldo_0052_eligibility.py | - | - | - | - | 0 | 1 | 0 | 2 |
| 60_veldo_0053_architecture.py | - | - | - | - | 0 | 2 | 0 | 4 |
| 60_veldo_0064_inbox.py | - | - | - | - | 0 | 7 | 0 | 6 |
| 62_veldo_0039_dispatch.py | 703 | - | 419, 420 | - | 1 | 32 | 1 | 6 |
| 62_veldo_0054_decisions.py | - | - | - | - | 0 | 0 | 0 | 1 |
| 62_veldo_0065_presentations.py | - | - | 749, 980 | - | 0 | 10 | 0 | 4 |
| 63_veldo_0040_containment.py | 1010 | 1284 | 368, 369, 1288, 1290, 1303, 1304 | - | 3 | 9 | 2 | 9 |
| 63_veldo_0049_floor.py | - | - | - | - | 0 | 4 | 2 | 4 |
| 63_veldo_0066_attribution.py | - | - | - | - | 0 | 3 | 0 | 4 |
| 64_veldo_0050_proof.py | - | - | - | - | 1 | 3 | 3 | 6 |
| 65_veldo_0067_edges.py | - | - | 407 | - | 0 | 9 | 1 | 6 |
| 65_veldo_0132_workflow.py | - | - | - | - | 0 | 4 | 0 | 2 |
| 66_veldo_0042_clones.py | - | - | 390, 391, 402, 403, 567, 573 | - | 3 | 4 | 0 | 12 |
| 66_veldo_0047_authority.py | 821 | - | 818, 819 | - | 1 | 3 | 1 | 15 |
| 66_veldo_0051_events.py | - | - | - | - | 0 | 0 | 2 | 2 |
| 67_veldo_0041_heartbeat.py | - | 704 | 330, 331, 436, 437 | - | 2 | 5 | 1 | 17 |
| 67_veldo_0056_candidates.py | - | - | - | - | 0 | 5 | 2 | 5 |
| 67_veldo_0135_offers.py | - | - | - | - | 0 | 3 | 2 | 4 |
| 68_veldo_0126_intake.py | - | - | - | - | 0 | 0 | 0 | 2 |
| 68_veldo_0134_acceptance.py | - | - | - | - | 0 | 0 | 0 | 2 |
| 68_veldo_0136_hints.py | - | - | - | - | 0 | 3 | 0 | 2 |
| 69_veldo_0058_gate_output.py | - | - | 159, 160, 839, 840 | - | 3 | 0 | 0 | 7 |
| 69_veldo_0068_settlement.py | - | - | - | - | 0 | 8 | 1 | 6 |
| 69_veldo_0133_dispositions.py | - | - | - | - | 0 | 2 | 0 | 3 |
| 70_veldo_0057_landing.py | - | - | - | - | 0 | 0 | 0 | 5 |
| 70_veldo_0069_bindings.py | - | - | - | - | 0 | 3 | 2 | 5 |
| 70_veldo_0073_activation.py | - | - | - | - | 0 | 2 | 0 | 3 |
| 71_veldo_0076_projects.py | - | - | 298, 299, 308, 309 | - | 2 | 6 | 1 | 13 |
| 71_veldo_0130_api.py | - | - | 1074, 2182, 2183, 2385, 2389, 3018, 3042, 3045 | - | 1 | 15 | 1 | 27 |
| 71_veldo_0138_channel_service.py | - | - | 93, 227 | - | 1 | 5 | 1 | 10 |
| 72_veldo_0075_andon.py | - | - | - | - | 0 | 5 | 0 | 3 |
| 72_veldo_0077_objectives.py | - | - | - | - | 0 | 1 | 1 | 4 |
| 72_veldo_0128_reports.py | - | - | - | - | 0 | 19 | 0 | 1 |
| 73_veldo_0078_backlog.py | - | - | - | - | 0 | 3 | 1 | 3 |
| 73_veldo_0089_team.py | - | - | - | - | 0 | 3 | 1 | 3 |
| 73_veldo_0139_factory_setup.py | - | - | 89, 238 | - | 1 | 4 | 1 | 10 |
| 74_veldo_0140_standing_delegation.py | 588 | - | - | - | 0 | 8 | 4 | 2 |
| 75_veldo_0062_accounts.py | 941 | - | 514, 516, 546, 549, 554, 555, 1100, 1103 | - | 2 | 21 | 1 | 5 |
| 75_veldo_0150_own_message_acceptance.py | - | - | - | - | 0 | 2 | 1 | 2 |
| 76_veldo_0079_grooming.py | - | - | - | - | 0 | 1 | 1 | 2 |
| 77_veldo_0149_adopted_activation.py | - | - | - | - | 0 | 3 | 1 | 3 |
| 78_veldo_0060_claude_adapter.py | - | - | 596, 597, 607, 610, 1279, 1282, 1548, 1550 | - | 3 | 10 | 1 | 8 |
| 78_veldo_0160_account_pool.py | - | - | 449, 450 | - | 1 | 21 | 1 | 3 |
| 79_veldo_0061_codex_adapter.py | - | - | 465, 466, 523, 524 | - | 2 | 9 | 1 | 6 |
| 80_veldo_0155_claude_baseline.py | - | - | - | - | 0 | 6 | 1 | 6 |
| 81_veldo_0156_codex_baseline.py | - | - | - | - | 0 | 6 | 1 | 6 |
| 82_veldo_0085_decomposition.py | - | - | - | - | 0 | 1 | 1 | 7 |
| 82_veldo_0129_worker_wiring.py | - | - | - | - | 0 | 7 | 0 | 2 |
| 82_veldo_0141_execution_record.py | - | - | 774, 784 | - | 0 | 10 | 2 | 27 |
| 82_veldo_0144_mcp_catalog.py | - | - | - | - | 1 | 1 | 0 | 5 |
| 82_veldo_0165_launch_hygiene.py | - | - | - | - | 0 | 6 | 1 | 5 |
| 82_veldo_0173_tool_registry.py | - | - | - | - | 0 | 6 | 1 | 2 |
| 83_veldo_0154_factory_loop.py | 734, 840, 1052, 1136 | - | 110, 475, 480, 486, 487, 666, 1008, 1010 | - | 4 | 17 | 6 | 6 |
| 83_veldo_0166_usage_windows.py | - | - | - | - | 0 | 11 | 0 | 0 |
| 84_veldo_0169_project_handouts.py | 746 | - | - | - | 0 | 0 | 0 | 2 |
| 85_veldo_0158_credential_delivery.py | - | - | 838, 839, 940, 941, 1010, 1011 | - | 3 | 7 | 2 | 10 |
| 85_veldo_0171_setup_api.py | - | - | - | - | 0 | 5 | 1 | 15 |
| 86_veldo_0127_agent_configuration.py | - | - | - | - | 0 | 0 | 0 | 1 |
| 86_veldo_0148_re_land.py | - | - | 866, 873 | - | 0 | 8 | 2 | 8 |
| 86_veldo_0168_text.py | - | - | - | - | 0 | 1 | 0 | 0 |
| 86_veldo_0189_engine_upgrade.py | - | - | - | - | 0 | 5 | 0 | 7 |
| 87_veldo_0127_codex_delivery.py | - | - | - | - | 0 | 2 | 0 | 0 |
| 87_veldo_0170_receiver_trust.py | - | - | - | - | 0 | 3 | 1 | 1 |
| 91_veldo_0151_specialists.py | - | - | - | - | 0 | 1 | 1 | 3 |
| 91_veldo_0167_setup_records.py | - | - | - | - | 0 | 7 | 2 | 8 |
| 92_veldo_0088_pm_cycles.py | - | - | - | - | 0 | 3 | 0 | 6 |
| 93_veldo_0152_intake_routes.py | - | - | - | - | 0 | 1 | 0 | 1 |
| 94_veldo_0162_configuration_routes.py | - | - | - | - | 0 | 0 | 0 | 2 |
| 95_veldo_0203_owner_revisions.py | - | - | - | - | 0 | 3 | 0 | 0 |
| 96_veldo_0204_reservation_policies.py | - | - | - | - | 0 | 2 | 0 | 0 |
| 97_veldo_0204_gate_resources.py | - | - | - | - | 0 | 0 | 1 | 0 |
| 98_veldo_0204_mutation_receipts.py | - | - | 378, 379 | - | 1 | 0 | 0 | 1 |
| 99_veldo_0205_reuse.py | - | - | - | - | 0 | 2 | 0 | 2 |
| 100_veldo_0207_case_reuse.py | - | - | - | - | 0 | 0 | 1 | 3 |
| 101_veldo_0208_landing_reuse.py | - | - | - | - | 0 | 0 | 1 | 35 |
| 102_veldo_0210_agent_profile_runtime.py | 1041, 1066, 1872, 1913 | 1036 | 544, 545, 665, 666, 1058, 1063, 1103, 1104, 1107, 1114, 1321, 1322, 1864, 1865, 1935, 1936, 1943, 1944 | - | 8 | 5 | 0 | 17 |
| 103_veldo_0142_git_identities.py | - | - | - | - | 0 | 0 | 0 | 4 |
| 103_veldo_0211_borrowed_login.py | - | - | - | - | 0 | 0 | 0 | 7 |
| 104_veldo_0210_mutation_workers.py | - | - | - | - | 1 | 0 | 0 | 3 |
| 105_veldo_0182_memory.py | 481, 515 | - | 403, 404 | - | 4 | 10 | 0 | 3 |
| 106_veldo_0185_dispatch_setup.py | 840 | - | 820 | - | 0 | 6 | 0 | 1 |
| 107_veldo_0153_identity_push.py | - | - | - | - | 0 | 0 | 0 | 3 |
| 109_veldo_0161_adoption.py | - | - | 482, 483, 515, 516, 1705 | - | 2 | 5 | 1 | 10 |
| 110_veldo_0143_new_project.py | - | - | 2059, 2060, 2094, 2095, 2193, 2194 | - | 0 | 2 | 0 | 8 |
| 112_veldo_0215_case_deadlines.py | - | - | - | - | 0 | 2 | 1 | 0 |
| 113_veldo_0112_registered_clients.py | - | - | - | - | 0 | 15 | 1 | 2 |
| 113_veldo_0145_ui.py | - | - | - | - | 0 | 0 | 0 | 4 |
| 113_veldo_0220_gate_host.py | 231 | 207 | 143, 144 | - | 1 | 0 | 0 | 1 |
| 114_veldo_0220_gate_scope.py | - | - | 171, 172 | - | 1 | 0 | 0 | 0 |
| 115_veldo_0219_measured_admission.py | - | - | - | - | 1 | 1 | 0 | 0 |
| 116_veldo_0188_project_lines.py | - | - | 479, 480, 550, 551 | - | 2 | 2 | 0 | 2 |
| 117_veldo_0227_ui_location.py | - | - | - | - | 0 | 2 | 0 | 1 |
| 118_veldo_0159_mcp_credential_form.py | - | - | - | - | 0 | 2 | 0 | 0 |
| 119_veldo_0163_role_team_form.py | - | - | - | - | 0 | 2 | 0 | 2 |
| 120_veldo_0131_factory_ui.py | - | - | - | - | 0 | 2 | 0 | 2 |
| 121_veldo_0131_factory_screens_narrow.py | - | - | - | - | 0 | 2 | 0 | 1 |
| 122_veldo_0131_factory_screens_wide.py | - | - | - | - | 0 | 2 | 0 | 1 |
| 123_veldo_0174_conversations.py | - | - | - | - | 0 | 8 | 2 | 6 |
| 124_veldo_0131_factory_reads_commands.py | - | - | - | - | 0 | 2 | 0 | 1 |
| 126_veldo_0230_qualify_reproduces.py | - | - | - | - | 0 | 0 | 0 | 1 |
| 127_veldo_0234_https_port.py | - | - | - | - | 0 | 2 | 0 | 2 |
| 127_veldo_0241_unit_workflows.py | - | - | - | - | 0 | 0 | 0 | 2 |
| 127_veldo_0254_secret_scan.py | - | - | - | - | 0 | 0 | 0 | 4 |
| 127_veldo_0259_installation.py | - | - | - | - | 0 | 0 | 0 | 1 |
| 128_veldo_0235_land_locally.py | - | - | - | - | 0 | 2 | 0 | 5 |
| 128_veldo_0247_check_join.py | - | - | - | - | 0 | 2 | 0 | 1 |
| 128_veldo_0254_confined_runner.py | - | - | - | - | 0 | 0 | 0 | 2 |
| 129_veldo_0239_batch_landing.py | - | - | - | - | 0 | 2 | 0 | 5 |
| 129_veldo_0247_line.py | - | - | - | - | 0 | 0 | 0 | 1 |
| 129_veldo_0254_canary_launch.py | - | - | 709, 710, 736, 737, 765, 784, 785 | - | 4 | 9 | 2 | 9 |
| 129_veldo_0260_checkout_in_step.py | - | - | - | - | 0 | 2 | 0 | 5 |
| 133_veldo_0326_space_principals.py | - | - | - | - | 0 | 15 | 0 | 6 |
| 134_veldo_0331_space_mode.py | - | - | - | - | 0 | 0 | 0 | 2 |
| 136_veldo_0299_space_probe.py | - | - | - | - | 0 | 0 | 0 | 3 |
| 137_veldo_0330_space_rules.py | - | - | - | - | 0 | 0 | 0 | 5 |
| 138_veldo_0300_space_remove.py | - | - | - | - | 0 | 0 | 0 | 12 |
| 139_veldo_0301_space_signal.py | - | - | - | - | 0 | 0 | 0 | 4 |
| 140_veldo_0345_space_keep.py | - | - | - | - | 0 | 0 | 0 | 10 |
| 141_veldo_0344_process_reader.py | 686, 736 | - | 1141, 1142, 1148, 1149 | - | 3 | 0 | 0 | 24 |
| 142_veldo_0303_space_paths.py | - | - | - | - | 0 | 0 | 0 | 4 |
| 143_veldo_0305_space_census.py | - | - | - | - | 0 | 0 | 0 | 6 |
| 144_veldo_0306_space_docker.py | - | - | - | - | 0 | 2 | 0 | 5 |
| 145_veldo_0307_space_docker_ownership.py | - | - | - | - | 0 | 0 | 0 | 3 |
| 146_veldo_0308_run_finished.py | - | - | - | - | 0 | 0 | 0 | 4 |
| 147_veldo_0310_landed_contained.py | - | - | - | - | 0 | 4 | 0 | 5 |
| 148_veldo_0311_git_hooks.py | - | - | 405, 406, 688, 689, 754, 759 | - | 2 | 5 | 2 | 8 |
| 149_veldo_0312_ticket_ended.py | - | - | - | - | 0 | 19 | 0 | 5 |
| 150_veldo_0329_hook_install.py | - | - | 385, 386, 771, 774, 796, 797, 823, 827, 828, 909, 910, 915, 933 | - | 3 | 5 | 0 | 6 |
| 150_veldo_0350_end_write.py | - | - | - | - | 0 | 8 | 3 | 7 |
| 151_veldo_0313_space_run.py | 1119, 1123, 1270 | 1160 | 903, 904, 905, 973, 974, 1287, 1288, 1595, 1611, 1612, 1702, 1703 | - | 5 | 16 | 1 | 15 |
| 152_veldo_0313_house_group.py | - | - | - | - | 0 | 0 | 0 | 3 |
| 153_veldo_0302_space_creators.py | - | - | - | - | 0 | 2 | 2 | 0 |
| 153_veldo_0309_gate_space.py | - | - | 372, 373 | - | 1 | 0 | 0 | 5 |
| 153_veldo_0314_session_hooks.py | - | - | 142, 143, 299, 300, 318 | - | 2 | 5 | 0 | 11 |
| 153_veldo_0323_hook_events.py | - | 554 | 128, 129, 318, 319, 448, 449 | - | 0 | 7 | 0 | 9 |
| 153_veldo_0328_images.py | - | - | - | - | 0 | 0 | 0 | 3 |
| 153_veldo_0333_leg_time_store.py | - | - | - | - | 0 | 1 | 0 | 0 |
| 153_veldo_0336_run_worktree.py | - | - | - | - | 0 | 0 | 0 | 6 |
| 153_veldo_0337_verdict_recorded.py | - | 664 | - | - | 0 | 0 | 0 | 4 |
| 153_veldo_0341_docker_protection.py | - | - | - | - | 0 | 0 | 0 | 3 |
| 154_veldo_0324_batch_sandbox.py | - | - | - | - | 0 | 3 | 0 | 1 |
| 154_veldo_0335_released.py | - | - | 125, 126 | - | 0 | 3 | 0 | 4 |
| 156_veldo_0315_reconcile.py | - | - | 667, 668, 835, 836, 994, 995 | - | 0 | 2 | 0 | 13 |
| shared.py | - | - | 109, 114, 195 | - | 1 | 1 | 0 | 0 |
| support/identity_wire.py | - | - | - | - | 0 | 0 | 0 | 1 |
| support/setup_runtime.py | - | - | 133, 138 | - | 0 | 0 | 0 | 1 |
| support/v107_authority_runner.py | - | - | - | - | 0 | 0 | 0 | 1 |
| support/v174_journey.py | - | - | 23, 24 | - | 1 | 1 | 0 | 3 |
| support/v73_authority.py | - | - | - | - | 0 | 4 | 1 | 3 |

Sleeps in fixture source text (prefix: lines where the string starts): 02_mobile_ios: 324, 325, 327, 331, 333, 368, 371, 373; 13_warp_0623: 6742, 6744, 7163, 7172, 7267, 7268, 7317; 40_veldo_0101: 209, 217, 219, 331, 333; 42_veldo_0102: 153, 400, 404, 464; 53_veldo_0123: 41, 679; 58_veldo_0028: 954; 58_veldo_0036: 291, 356; 59_veldo_0043: 46; 62_veldo_0039: 153; 63_veldo_0040: 161, 188, 228; 64_veldo_0050: 132; 66_veldo_0042: 221; 67_veldo_0041: 191, 211; 69_veldo_0058: 234; 71_veldo_0076: 222; 78_veldo_0060: 277, 1507; 78_veldo_0160: 247; 79_veldo_0061: 259, 270; 82_veldo_0141: 478; 82_veldo_0144: 121; 82_veldo_0165: 201; 83_veldo_0154: 192; 84_veldo_0169: 13; 85_veldo_0158: 351; 86_veldo_0148: 1378, 1395; 92_veldo_0088: 108; 98_veldo_0204: 357; 102_veldo_0210: 254, 311, 609, 664, 1187, 1801, 1847, 1909; 103_veldo_0211: 55; 104_veldo_0210: 151; 111_veldo_0214: 45; 112_veldo_0215: 338; 113_veldo_0220: 39; 114_veldo_0216: 86, 267, 360; 114_veldo_0220: 44; 116_veldo_0188: 112; 146_veldo_0308: 758; 150_veldo_0329: 750, 816, 857; 150_veldo_0350: 508, 521, 588; 151_veldo_0313: 527, 546, 867, 954, 1072, 1231, 1312, 1331, 1655, 1720, 1753; 152_veldo_0313: 98; 153_veldo_0309: 196, 197; support/v174_journey: 32.

### A.2 Gate and mutation tooling (scripts/)

11 files with a hit. Sleeps 9, bounded polls 11, timeouts under 600 s 13, timeouts of 600 s or more 5.

| File | S: sleep lines | P: bounded poll lines | T: timeout under 600 s, lines | T of 600 s or more, count |
| - | - | - | - | - |
| scripts/agent_sandbox.py | - | 293, 1072 | 2689, 2762 | 1 |
| scripts/check_gate_mutations.py | 1047 | 789 | 518, 828 | 0 |
| scripts/check_install_and_run.py | - | - | - | 1 |
| scripts/check_personal_setup.py | - | - | 147 | 0 |
| scripts/drive.py | - | - | - | 1 |
| scripts/gate_host.py | 226, 288, 330, 384, 391 | 284, 286 | 235, 278, 316 | 0 |
| scripts/gate_schedule.py | 358 | - | - | 0 |
| scripts/mutation_ownership.py | 603 | 599, 601 | 286, 361, 517 | 0 |
| scripts/render_pdfs.py | 154 | 146, 147, 169, 170 | 149 | 0 |
| scripts/suite_equiv.py | - | - | 573 | 1 |
| scripts/suite_labels.py | - | - | - | 1 |

### A.3 Browser tests and harnesses (engine/ui/)

7 files with a hit. Sleeps 4, bounded polls 3, timeouts under 600 s 28, timeouts of 600 s or more 1.

| File | S: sleep lines | P: bounded poll lines | T: timeout under 600 s, lines | T of 600 s or more, count |
| - | - | - | - | - |
| e2e/factory.spec.ts | - | - | 337, 467, 485, 541, 624, 650, 666, 687, 702, 717, 771, 795, 835, 881 | 1 |
| e2e/harness.py | - | 257, 341, 542 | 109, 111, 113, 119, 304, 310 | 0 |
| e2e/layout.spec.ts | 663, 673 | - | 375 | 0 |
| e2e/run.spec.ts | - | - | 107, 108, 174 | 0 |
| e2e/screens.spec.ts | 32, 61 | - | 38 | 0 |
| e2e/team_harness.py | - | - | 81 | 0 |
| playwright.config.ts | - | - | 10, 11 | 0 |

### A.4 Engine (engine/.veldo/ and engine/bin/veldo)

62 files with a hit. Sleeps 15, bounded polls 53, timeouts under 600 s 127, timeouts of 600 s or more 4.
engine/bin/veldo has none: its waits are pidfd and poll with no time limit.

| File | S: sleep lines | P: bounded poll lines | T: timeout under 600 s, lines | T of 600 s or more, count |
| - | - | - | - | - |
| .veldo/authority_contract.py | - | - | 245 | 0 |
| .veldo/capsule.py | - | - | 193, 196, 268 | 0 |
| .veldo/control_agent_config_handoff.py | - | 103, 119, 160 | 140, 613, 659 | 0 |
| .veldo/control_andon.py | - | - | 215 | 0 |
| .veldo/control_architecture.py | - | - | 213, 499 | 0 |
| .veldo/control_channel_activation.py | - | - | 711, 830 | 0 |
| .veldo/control_channel_attribution.py | - | - | 264 | 0 |
| .veldo/control_channel_ingress.py | - | - | 164, 189 | 0 |
| .veldo/control_channel_presentation.py | - | - | 511 | 0 |
| .veldo/control_channel_projection.py | - | - | 256 | 0 |
| .veldo/control_claim_client.py | - | - | 37 | 0 |
| .veldo/control_client.py | - | 483 | 265, 333, 477 | 0 |
| .veldo/control_client_api.py | - | 217 | 81, 254, 287, 308 | 0 |
| .veldo/control_containment.py | 599 | 558, 576 | - | 0 |
| .veldo/control_credential_keystore.py | - | - | 28 | 0 |
| .veldo/control_document.py | - | - | 69 | 0 |
| .veldo/control_effect_executor.py | - | 358, 364, 368 | 371, 377 | 0 |
| .veldo/control_effect_executor_adoption.py | - | - | 128 | 0 |
| .veldo/control_effects.py | - | 141, 153, 166 | - | 0 |
| .veldo/control_engine_claude.py | - | 1759 | - | 0 |
| .veldo/control_engine_codex.py | - | - | 553, 572 | 0 |
| .veldo/control_enrollment.py | - | - | 75 | 0 |
| .veldo/control_factory_setup.py | - | - | 175, 182, 1085, 1214, 1743, 1888 | 0 |
| .veldo/control_factory_setup_api.py | - | - | 125, 131, 158, 479 | 0 |
| .veldo/control_factory_setup_upgrade.py | 444 | 438, 442 | - | 0 |
| .veldo/control_graph.py | 619 | 615, 617 | 420, 633, 688, 697 | 0 |
| .veldo/control_graph_isolation.py | - | - | 122 | 0 |
| .veldo/control_heartbeat.py | - | 152 | - | 0 |
| .veldo/control_launch.py | 1901 | 1898, 1900, 2129, 2156, 2157, 3196, 3218, 3254, 3478, 3494, 3856, 3903, 3919 | 191, 456, 508, 510, 1428, 1430, 2086, 3530, 3607 | 0 |
| .veldo/control_launch_work.py | - | 222 | 214, 263, 286, 291, 321, 323 | 0 |
| .veldo/control_memory_adapter.py | 226, 237, 345, 447 | 222, 224, 235, 471, 472 | 272, 286, 354 | 2 |
| .veldo/control_memory_check.py | 65, 147 | - | - | 1 |
| .veldo/control_project_proposal.py | - | - | 433 | 0 |
| .veldo/control_proof.py | - | - | 178 | 0 |
| .veldo/control_readset.py | - | - | 44, 84, 105, 116 | 0 |
| .veldo/control_relay.py | - | 76 | 70 | 0 |
| .veldo/control_replica.py | - | - | 84, 191, 273 | 0 |
| .veldo/control_repository.py | - | - | 372, 464 | 0 |
| .veldo/control_runtime.py | - | - | 344, 398, 504 | 0 |
| .veldo/control_service.py | - | 2448, 2468, 3647, 3961, 4543, 4545, 4600 | 919, 1128, 1251, 1557, 3192, 3663, 3900, 3977, 3996, 4604 | 0 |
| .veldo/control_signer.py | - | - | 49, 94, 275, 284 | 0 |
| .veldo/control_snapshot.py | - | - | 53, 64 | 0 |
| .veldo/control_space.py | - | - | 2452 | 0 |
| .veldo/control_space_docker.py | - | - | 1135 | 0 |
| .veldo/control_space_install.py | 592 | 583, 589 | - | 0 |
| .veldo/control_space_spool.py | 619 | 610, 616, 968, 1341 | - | 0 |
| .veldo/control_store.py | - | - | 409, 413 | 0 |
| .veldo/control_workflow_cycle.py | - | - | 242 | 0 |
| .veldo/control_workflow_cycle_pm.py | - | 378 | - | 0 |
| .veldo/dispatch.py | - | - | 754, 760, 766, 772 | 0 |
| .veldo/fix_assessor.py | - | - | 282 | 0 |
| .veldo/fix_validation.py | - | - | 83, 86, 115 | 0 |
| .veldo/fix_validation_record.py | - | - | 83, 88, 130, 135, 139, 154, 572 | 0 |
| .veldo/git_process.py | - | - | 140 | 0 |
| .veldo/installation.py | - | - | 240 | 0 |
| .veldo/lander.py | 331 | - | 337 | 1 |
| .veldo/qualify.py | - | - | 124, 265 | 0 |
| .veldo/runstatus.py | 462 | - | - | 0 |
| .veldo/secret_scan.py | - | - | 275, 278 | 0 |
| .veldo/status_server.py | 258 | - | - | 0 |
| .veldo/tracker_intake.py | - | - | 433, 633 | 0 |
| .veldo/version.py | - | - | 257 | 0 |

### A.5 Proof fixtures (proof/), files with a sleep or a bounded poll only

152 files with a hit. Sleeps 24, bounded polls 41, timeouts under 600 s 137, timeouts of 600 s or more 83.
Only the files a suite opens are in the census's scope (9.1); the opened-files record decides which.

| File | S: sleep lines | P: bounded poll lines | T: timeout under 600 s, lines | T of 600 s or more, count |
| - | - | - | - | - |
| VELDO-0040/exit_notified_replay.py | 119, 120 | - | 150, 160, 164, 165, 180 | 0 |
| VELDO-0042/drive.py | 264 | 259 | 194, 228, 241 | 1 |
| VELDO-0073/qualify_live.py | 150 | 139, 141 | - | 0 |
| VELDO-0080/fixture.py | - | 172, 344 | 142, 147 | 0 |
| VELDO-0088/fixture.py | - | 174 | 126, 147 | 0 |
| VELDO-0123/drive.py | - | 77, 78, 79, 80 | - | 0 |
| VELDO-0127/factory.py | - | 284 | 52, 294 | 0 |
| VELDO-0142/mutation_followups.py | - | 37 | - | 0 |
| VELDO-0148/runtime_parallel.py | - | 171 | 177 | 1 |
| VELDO-0152/fixture.py | - | 202 | 140, 175 | 0 |
| VELDO-0159/replay-set-at.py | 56, 65 | - | - | 0 |
| VELDO-0161/inprocess_transport.py | 95 | 91, 93 | 99 | 0 |
| VELDO-0162/base_fixture.py | - | 166 | 118, 139 | 0 |
| VELDO-0162/fixture.py | - | 116 | - | 0 |
| VELDO-0182/chroma_rust_copy.py | 43, 82, 86, 106, 107 | 104, 105 | 114 | 0 |
| VELDO-0182/integration_fixtures.py | 72, 648, 652 | 67, 70, 233, 235, 650, 651, 841 | 261, 267, 271, 480, 630 | 0 |
| VELDO-0182/worker_fixture.py | 37 | - | - | 0 |
| VELDO-0188/round2/served_scenario.py | 205 | 200, 201 | 94, 213, 325, 335 | 0 |
| VELDO-0203/journey.py | - | 81 | - | 0 |
| VELDO-0204/host.py | - | 134, 441, 442 | 93, 398, 408, 432 | 0 |
| VELDO-0216/kernel_scope_check.py | 39, 43 | - | - | 0 |
| VELDO-0219/kernel_check.py | 50, 71, 96 | 49 | - | 0 |
| VELDO-0219/round2/check.py | 143 | 82, 140, 141 | 43, 144, 158, 170, 177, 180, 197, 201, 202 | 0 |
| VELDO-0219/round2/lifecycle_check.py | 101 | 40, 80, 97, 99 | 44, 61, 113, 122 | 0 |
