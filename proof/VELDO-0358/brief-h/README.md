# VELDO-0358 brief H: browser tests

Branch veldo-0358-h, built on fb7705e1 (wave 0 integrated). Scope: revision notes 3.3, "Brief H". Criteria:
AC10 and AC15 for suites 120, 121 and 124 of VELDO-0131 and the browser tests' own files; AC5 for a browser run.
The canonical gate was not run (the brief forbids it); nothing here is a landing claim.

## What was built

| Where | Before | Now |
| - | - | - |
| engine/ui/playwright.config.ts | test limit 90 s, expectation 10 s, action 10 s | No limit on a test's total time (timeout 0). Expectation, action and navigation bounded by WAIT_HANG_MS. The Progress reporter is on |
| engine/ui/e2e/fixtures.ts: the two durations | none named | WAIT_HANG_MS 600 000 and PROCESS_HANG_MS 3 600 000, the only durations of the browser tests |
| fixtures.ts: harness start (also factory-fixtures.ts, team-fixtures.ts) | a 60 or 90 s timer rejected the start | startHarness waits for the ready line or the exit, whichever event comes first, under an abort signal at the wait hang bound; at the bound the harness is killed and the error says hung, with what it wrote |
| fixtures.ts: harness stop (all three) | 10 s, then SIGTERM, and the test went on in silence | stopHarness closes the input and waits for the exit event; at the wait hang bound it kills the harness and fails as hung |
| fixtures.ts: page settled signal (C10) | one test of factory.spec.ts counted its own requests | Standing: every context a test makes (the page fixture's and browser.newContext's) carries the request count; settled(page) waits for no request unanswered (to the end of each answer's body), no StatePanel loading and no finite animation or transition running. No change was needed in engine/ui/src: StatePanel already says loading, ready, empty and error |
| fixtures.ts: Progress (the configuration's reporter) | none | Re-arms the process hang bound at every test and step beginning or ending; when none happened for that long it ends the run and names what it last saw and every test and step in flight with its source line. With VELDO_E2E_PROGRESS it writes one line per event, which a suite's heavy-child bound counts from |
| factory.spec.ts | 14 test.setTimeout of 120 to 600 s; a 120 s waitForFunction limit; 13 Date.now reads (aliases, a record's times, a trace's milliseconds) | Limits removed. Aliases from unique(); the gate observation's times from the factory's clock (factory.now()); the backlog trace keeps its order and drops its milliseconds. Its own request counter is replaced by the standing settled(page) |
| layout.spec.ts | test.setTimeout 300 s; waitForTimeout 250 and 300 ms; 4 Date.now aliases | Limit removed; both fixed waits are settled(page) (the page's transitions have ended); aliases from unique() |
| screens.spec.ts | test.setTimeout 240 s; waitForTimeout 400 and 600 ms | Limit removed; both are settled(page) |
| run.spec.ts | expectation limits of 15, 15 and 5 s | Removed: each expectation already waits on the terminal's own state (the reconnect notice, the line count, the elapsed text) |
| engine/ui/e2e/harness.py | 12 time.time reads; 6 tool calls with timeout 10 | Wall time as data is the suites' support stamp (wall(), as briefs E and F do); tool calls bounded by WAIT_HANG_SECONDS; the timers profile selected in the organs' timers table before any organ is loaded, with a sentinel entry, and reported in the ready line; a /clock control route gives the tests the factory's clock |
| suites 120, 121, 124 | subprocess limits of 300, 900 and 3000 s; two monotonic reads each | Every child through WAITS.run_heavy (no total bound; ended only after the process hang bound with no output); the start and end are stamps. New rows: timers/profile-applied and wave1/no-sites in each, browser/hang-by-progress in 121 |
| engine/ui/docs/patterns/testing.md | no rule on time | "Time in browser tests" |

The code follows the rule it builds: it has no sleep and no clock read; its only timers are the abort signal at the
wait hang bound around an event wait, and the reporter's bound, re-armed at each progress event.

## Criteria and their falsifiers

Registered in the block "VELDO-0358 BRIEF H" of scripts/check_teeth_mutations.py. All six run in suite 121.

| Criterion | Row | Falsifier | Red for |
| - | - | - | - |
| AC10, expectation limit | wave1/no-sites | wave358-browser-expectation-restored (the configuration's expectation back to 10 s) | wallclock_site, R3 timeout option |
| AC10, fixed wait | wave1/no-sites | wave358-browser-fixed-wait-restored (waitForTimeout(250) after the hover in layout.spec.ts) | wallclock_site, R1 waitForTimeout |
| AC10, per-test limit | wave1/no-sites | wave358-browser-test-limit-restored (test.setTimeout(600_000) in factory.spec.ts) | wallclock_site, R3 setTimeout |
| AC15 | timers/profile-applied | timers358-browser-profile-skipped (the harness reports the profile and never selects it) | timer_unset: the sentinel entry is at 1 s |
| AC5, browser run | browser/hang-by-progress | wait358-browser-watchdog-total-time (the bound armed once) | the bound is not armed anew at each event |
| AC5, browser run | browser/hang-by-progress | wait358-browser-watchdog-silent (the run ended with nothing in flight named) | the hung report names no step and no test |

All six are rejected by the gate's own mutation stage entry (scripts/check_gate_mutations.py; the three suites are
of the unconfined leg, so the registry's developer entry, which confines every worker, cannot install their
dependencies): mutants-h.txt, kill_by assertion each, controls green. What each mutant's row said, and that it is the
stated reason, is in mutants-h-reasons.txt; the applied diffs are in mutant-diffs.txt.

## Done criteria of the wave 1 briefs

| Criterion | Evidence | Result |
| - | - | - |
| The census finds no site in its files or the files they open | row wave1/no-sites in suites 120, 121 and 124; scripts/check_wallclock.py over the checkout (checks.txt) | No site. 63 baseline entries removed (12 files), none lowered, none added; the stage passes |
| Row labels the same set or a superset | rows-kept.txt (the mutation worker's own reading at fb7705e1 and here) | 120: 40 to 42; 121: 28 to 31; 124: 34 to 36; none missing |
| Every registered case of its suites rejected with kill_by assertion or terminal | mutants-131.txt (finding 131, 21 cases) and mutants-h.txt | The 14 cases of suites 120, 121 and 124 and brief H's 6: rejected, assertion. The other 7 cases of finding 131 belong to suites of other briefs and read unproven on this branch |
| Each suite fifty times under the generator, no failed and no hung row | load50.txt | 121: 50 of 50. 124: 50 of 50. 120: 49 of 50 at first, one red that was a race in the test, fixed; then 50 of 50 on the fixed tree (below) |
| timers/profile-applied in each suite | the three suites; affected-suites.txt | Green; the report holds the harness's sentinel only on this branch (see lead item 2) |

Other runs: every browser specification, 71 passed and the screenshots specification skipped (e2e-all.txt); the
screenshots specification on request, passed, its images restored (e2e-screens.txt); the twenty suites that drive a
browser harness or read the mutation registry or the baseline, each alone, all green (affected-suites.txt).
scripts/check_personal_setup.py: 0 findings (checks.txt).

## Loaded runs

Through the builders' host wrapper, under scripts/gate_load.py with 4 slots (12 spinners and 1 writer bound to 4
CPUs with the runs; no delegated scope, so no memory.high), four runs at a time, each its own dispatcher process
(loaded_runs.py.txt). Every generator process was alive to the end of both batches (load_not_applied never).

| Batch | Tree | Runs | Probe slowdown (data) | Result |
| - | - | - | - | - |
| load50.txt | 09a960f6; the fix of 60bc58dd was in the working tree from 18:28:29Z | 120, 121 and 124, fifty each | 4.3 | 121 50 of 50, 124 50 of 50, no hung row. 120 49 of 50: run 14 red on ac2/metadata-only (red-120-run14.txt) |
| load50b.txt | 60bc58dd | 120, fifty | 5.2 | 50 of 50, no failed and no hung row |

The red: the test's response listener stored an empty string when an answer's body could not be read, and under load
the page's re-read of the screen it was leaving arrived late, was abandoned by the navigation, and overwrote the body
already read; JSON.parse of the empty string failed. The test raced, not the product, so the test is fixed (60bc58dd):
it keeps only the bodies it read whole and still waits for one of each route before judging them. No bound, retry or
exception was added, and what the row asserts of a served body is unchanged.

The six falsifiers, the finding 131 stage, the affected suites and the row labels were taken at 09a960f6, before that
fix. The fix changes one listener of one test in factory.spec.ts; after it suite 120 ran fifty times green, the
census passes and every registered case still applies to its subject (checks.txt).

## For the lead

1. Sites left in engine/ui/e2e and beside it, in files that are not brief H's and not in the specification's
   footprint: decisions.spec.ts:12 (a Date.now alias; unique() replaces it), factory_harness.py:126 (time.time;
   H.wall() replaces it), team_harness.py:80 (timeout=10; H.WAIT_HANG_SECONDS replaces it), and suite
   122_veldo_0131_factory_screens_wide (two monotonic reads, limits of 900 and 3000 s; the conversion of suite 121
   applies line for line). Their baseline entries stay. AC10 names "the browser fixtures, specifications and
   configuration under engine/ui", so these four are wanted before the census is required of the whole tree.
2. The checkout's .veldo/timers.py is not added by this brief (briefs E and F both add it, with the scaffold change
   it needs). Suites 120, 121 and 124 lay engine/.veldo/timers.py among the harness's organs, so their timers row
   does not depend on which brief lands first. On this branch the table has no product entry, so the row's teeth are
   the harness's own sentinel entry (e2e_harness.SENTINEL_SECONDS, 1 s, armed by nothing); once E and F land, the
   store's, the client's and the launch's entries appear in the same report and are held to the same bound. The
   sentinel is registered at run time in the harness's process only; engine/.veldo/timers.py is untouched.
3. A browser expectation that will never hold now takes the wait hang bound to say so. Ten of the fourteen
   VELDO-0131 cases of these suites took 637 to 654 s and two took about 1,255 s (mutants-131.txt), against about a
   minute before; the stage's 21 cases took 47 minutes. The verdicts are unchanged (assertion). A general terminal
   condition is not sound here: the page settled signal cannot end an expectation that waits for an event stream.
   Per test, "settled and still not shown" could be made a terminal condition where the expectation follows a read
   the page itself made; that is a later change, test by test.
4. The census's TypeScript rules do not read AbortSignal.timeout(n), nor a plain setTimeout used as a sleep (one
   whose callback only resolves). Brief H's files have neither with a number of their own, but a later change could
   add one unseen. A rule for both belongs to scripts/check_wallclock.py (brief B's file).
5. Progress, the reporter, is the default export of e2e/fixtures.ts because the footprint names no new file under
   engine/ui/e2e. It would read better as its own file if the footprint is widened.
6. When the reporter ends a run it names every test and step in flight with its source line. It cannot write the
   stacks of the worker and the browser, as the Python watchdog does for a suite process.
7. Host: the builders' three slots were held for about 1 h 40 min before this brief's batch started, so the light
   steps (the browser run, the six falsifiers, the row labels) were first run directly, with the same results; the
   files here are the batch's, taken inside the host slot.
