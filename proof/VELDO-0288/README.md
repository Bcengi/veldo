# VELDO-0288 build proof

Commit cc94b45f makes settle_stopped fail immediately when the runner never asked the receiver to
stop. It calls runner.wait with timeout zero before returning the failure. Commit 1fd2f48c fixes the
capture helper to read only the two engine entries in engines.json. Deadlines, thresholds, guards,
acceptance criteria, and the footprint are unchanged.

On 1fd2f48c, suite 62 passed all 69 rows. All six mutations were killed in one command, with every
baseline and no-op control passing 69 rows. launch131-stop-recorded-unasked took 17.34 seconds,
below its unchanged 120-second floor. suite62.json, teeth.json, and fix1-teeth-details.json contain
the results, commands, and individual mutation times. The old timeout and cleanup refusal remain in
commit f5c14ac9; this run had neither failure.

All 20 consecutive suite 62 runs passed 69 rows. Each of dispatch/stop-during-exit,
dispatch/stop-during-natural-end, and dispatch/stop-during-accept-run passed 20 of 20. repeated.json
includes the command, commit, host, and load averages. These runs used host_heavy.sh, which excludes
a concurrent gate run. AC3's full gate load condition therefore remains pending.

The four VELDO-0127 resource records were retaken with .veldo/qualify.py. codex-live.json was retaken
with live.py, selecting only Codex and using CODEX_HOME set to the codex2 profile. The Codex capture
reports no problems. captures.json gives the commands and hashes of the five records. Home paths
are normalized in the committed records. claude-live.json is unchanged and remains the lead's task.

The selected related suites passed: 71_veldo_0130_api had 45 green rows,
83_veldo_0154_factory_loop had 14, and 124_veldo_0131_factory_reads_commands had 8. Suite 86 passed
27 of 28; live/claude failed because its capture is stale. related-suites.json retains this partial
run's exit 1, counts, and failure. Suite 86 still needs the lead's fresh Claude capture before review.

Every heavy or repeated run in this round used host_heavy.sh. No gate, verify.sh, policy_check.py,
or push was run. Both runtime module pairs still match the hashes in mirrors.json.
