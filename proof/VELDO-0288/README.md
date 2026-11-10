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
a concurrent gate run, so AC3 stays pending until the same 20 runs pass while a full gate runs on the
host.

Commit 9a0585ca changes repeat.py for that run. It reads the gate's process id from V0288_GATE_PID
and refuses to start when the variable is unset or the process is not alive. It records gate_alive
before every run and checks again after it. If the gate ends before the 20 runs finish, it writes the
runs so far and exits 2, which is not a pass. A process that has exited but not been reaped counts as
ended. The lead runs it as one lock-queue job that starts verify.sh in a clone and then the 20 runs.

The four VELDO-0127 resource records were retaken with .veldo/qualify.py. codex-live.json was retaken
with live.py, selecting only Codex and using CODEX_HOME set to the codex2 profile. The Codex capture
reports no problems. captures.json gives the commands and hashes of the five records. Home paths
are normalized in the committed records. The lead retook claude-live.json in commit 40cd9775; it
reports no problems and captures.json has its hash.

The selected related suites passed: 71_veldo_0130_api had 45 green rows,
83_veldo_0154_factory_loop had 14, and 124_veldo_0131_factory_reads_commands had 8. In that run suite
86 passed 27 of 28 because the Claude capture was stale. Run again on 9a0585ca with the new capture,
suite 86 passed all 28 rows, live/claude included. related-suites.json has both runs. A partial
selftest run exits 2 when nothing fails; it never exits 0.

Every heavy or repeated run in fix 1 used host_heavy.sh. The fix 2 suite 86 run used a systemd scope
with a 10G memory limit. No gate, verify.sh, policy_check.py, or push was run. Both runtime module pairs still match the hashes in mirrors.json.
