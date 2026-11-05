# VELDO-0236 evidence (build; the full gate was not run)

Suite 139_veldo_0236_account_pacing, 12 rows, run as `python3 scripts/selftest.py --suite NAME`.
Red before: suite-139-red-before.txt (the synced .veldo copies at the parent commit: 12 of 12 rows fail).
Green after: suite-139-green.txt (38 passed, 0 failed). UI: ui-pacing-spec-red-before.txt (spec fails: no
component) and ui-specs-green.txt (usage and api specs, 25 passed); vue-tsc clean.

| AC | Rows | Falsifier (registered, check_teeth_mutations finding 236) | Result |
|---|---|---|---|
| AC1 | pause/ends, pause/no-reset | pace236-pause-outlives-reset: pause in force until a resume | red on pause/ends |
| AC2 | ceiling/relative, ceiling/lapse, resume/early, ceiling/no-utilization | pace236-ceiling-outlives-reset | red on ceiling/lapse |
| AC3 | route/telegram, route/ui, route/other | pace236-telegram-indefinite: /pause sets the indefinite status | red on route/telegram |
| AC4 | journal/history, journal/once | pace236-end-unrecorded | red on journal/history |

Each falsifier applied by hand (falsifiers.txt, falsifier-*.txt) and through the gate's driver
(mutations-finding-236.txt: passed, registered 4, executed 4, all 4 mutants killed); restored green
(suite-139-restored-green.txt, then suite-139-green.txt after the history moved to its own read).
observability/counts covers the logs, metrics and pass-over reasons.

Existing suites run (proof/VELDO-0236/suites/): 75_0062, 78_0160, 83_0166, 83_0154, 96_0204, 106_0185,
68_0126, 93_0152, 131_0175, 132_0175, 133_0178, 104_0164, 124_0131, 113_0145, 120_0131, 84_0169: all green.
71_0130: 69 passed, 2 failed, both from its write-route body table lacking the new routes (OPEN.md item 1).
