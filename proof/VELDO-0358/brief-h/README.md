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

RESULTS_PLACEHOLDER
