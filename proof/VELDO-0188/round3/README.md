# VELDO-0188 round 3

Response to fixcheck-2026-10-28.md. Every run below used the blocking host gate lock
(/home/dmitry/.local/state/core-gates/.gate.lock). The mutation coordinator takes no lock of its own on this
branch, so no inner lock was needed. scripts/verify.sh was not run (owner rule 37191).

| Finding | Change | Evidence |
| :--- | :--- | :--- |
| 4 INFO, suite number | Suite 113_veldo_0188_project_lines renamed to 116_veldo_0188_project_lines. 115 was the highest suite number on main, on every branch in the home repository and in every veldo worktree. The manifest, check_teeth_mutations.py and the suite were updated, and requires.json was regenerated with run_scope.py --emit-requires. | Commit b6015654 |
| 1 HIGH, gate declaration | Owner approval: Telegram 37451 and 37452. scripts/gate_unconfined.json lists suite 116 whole, with no rows, and the reason from round2/proposed-gate-entry.patch. The spec's footprint and protected paths name the file, in a dated History amendment. | Red: gate-entry-red.log and gate-entry-red-receipt.json. Without the entry, lines188-paused-omitted is refused as invalid_baseline in the confined leg. Green: see the next row. |
| 2 MEDIUM, mutation receipt | The coordinator ran all nine registered cases: six in suite 116 and the consumer cases for suites 92, 93 and 110. The first green run (falsifiers-green.log) passed eight cases. lines188-pm-receiver-authority-missing was refused as missing_target because suite 92 runs four variants and each one reported a line/store-staffing row. Now only the full variant reports that row; the other three still take their Line from factory.lines, so they still depend on it. | falsifiers-green.log and its receipt (red for the pm case). suite-92-green.log: 30 rows, 0 failed. pm-falsifier-green.log: passed. Final: falsifiers-final.log, with ../falsifiers-receipt.json and ../falsifiers.json. Status passed: 9 executed, 9 rejected, every baseline and no-op green, and each mutant reds its declared row. |
| 3 LOW, docstring | The control_service.py module docstring now says the work configuration's roles staff only a repository that no project names. Both copies were changed and are byte-identical. | Commit c342e33e |
