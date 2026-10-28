# VELDO-0161 round 8: the two findings of the fix check of rounds 6 and 7

Branch agent/claude/agent/claude/veldo-0161, from 6b2805e6. The check is
proof/VELDO-0161/REVIEW-claude-r6r7-2026-10-23.md, added here as written. Nothing here is a gate result, a review
verdict or an approval. This sandbox refuses AF_UNIX sockets and has no systemd user manager, so suites 86, 73 and
85 and the gate mutations cannot run here. Those runs are the host's, listed at the end.

Host results at 6b2805e6, as given: suite 86 59/0, 73 43/0, 85 44/0, 109 81/0, gate mutations finding 161 56/56.

## R6R7-1 (medium): the restart a laid adoption signer owes was lost on a kill

A host whose installed engine is already current can still lack the adoption signer (a host upgraded by a setup
from before round 6). setup lays the signer in the engine upgrade's prepare step and makes the restart due, because
the service reads its enrollment signers only at its start (`Service.__init__`). That due restart was held only in
memory. If the run was killed after the `adoption_signers` points and before the `restart` point, or the restart
failed, the next run found both files laid (`adoption_laying` `due` False) and a step log owing nothing
(`recovery` counted only `exchanged` and `switched_back`). It took the short path and restarted nothing. The
service kept the old signers and refused every adoption while setup reported the factory complete.

The fix (control_factory_setup_upgrade.py, engine/.veldo and the synced .veldo copy byte-identical): `recovery`
treats an `adoption_signers` point as a restart owed (`due=True`). As with an exchange's restart, a `restart` point
with a successful outcome or `done` clears it. inspect_engine's `restart_due` (`switched_without_restart(log)`) now
carries the debt into the next run, which restarts the service. On the upgrade path nothing changes: the points
come after `exchanged`, which already owes the restart, and the same outcomes clear both.

Suite 86 gains the row `restart/adoption-signer-kill`. It starts from the fresh host (current engine), removes the
adoption key and the adoption line from both signers files, and starts its service on the owner-only signers.
- A whole run lays the key and both signers files, with no exchange, and restarts before `done`.
- A run SIGKILLed right after the last `adoption_signers` point leaves both files laid, no restart point, the same
  service process still serving, and a step log that owes the restart.
- The next run is accepted, restarts the service exactly once, and leaves a new process serving and nothing owed.
- Adoption then works: an enrollment binding signed by the adoption signer verifies under the signers the
  restarted service read (`control_service.Service(...).verify`, the judgment the take-on makes). The same binding
  does not verify under the owner-only signers the killed run left the old process holding.

Finding 161 adds `upgrade161-adoption-restart-not-owed`, which drops the `adoption_signers` branch from
`recovery`. It targets the new row: under it, the step log owes nothing after the kill and the next run restarts
nothing.

## R6R7-2 (low): round 7 changed the suite's count, not the product

The check is right. setup loads each module once per run (`_one_setup`), so round 6's second
`organ('control_factory_setup_upgrade')` returned the module inspect_engine had loaded. The product never loaded
it twice. The double count came from suite 86's kill driver, which wrapped `module.point` in one more counter on
every fetch. Round 7's README said as much, but its commit subject presented the change as a product fix.

- The fix: the kill driver marks its wrapper (`point.counted = True`) and wraps a module's `point` only when it
  is not already wrapped. The count is one per step-log line however often setup fetches the module.
- Round 7's product change stays. The prepare step lays the signer with the module whose plan it is carrying out
  instead of asking organ again. That reads plainly and costs nothing, but it has no product effect, and the
  specification's history now says so.
- The specification history is corrected: the round 7 paragraph gains a note that round 7 changed how the driver
  counts and nothing in the product. Round 8's paragraph records both fixes.

## Evidence here

- `drive_debt.py` (`drive-debt.json`) runs setup's own `upgrade_engine` and the upgrade module's own `run` over a
  scratch host with a current engine, no adoption key, and the owner's line alone in both signers files.
  - The service manager is a stand-in that records calls, with the unit active.
  - A run's `restart_due` is computed as setup computes it: `switched_without_restart(log)`, then setup's
    adoption rule.
  - A kill is a BaseException raised right after the Nth step-log line.
  - Result on engine/.veldo: 18 passed, 0 failed:
    - A whole run restarts once and leaves nothing owed, and a further run writes and restarts nothing.
    - For each kill point before the restart, the next run restarts once and leaves nothing owed. After the
      kill at 4 (the last `adoption_signers`), the files are laid and the log owes the restart.
    - A run whose restart fails is refused `unavailable_service:authority:upgrade_start` with the restart owed,
      and the next run restarts.
- `drive_driver.py` (`drive-driver.json`) takes suite 86's kill-driver counting code from the suite file,
  unchanged, and runs it over a stand-in setup whose organ caches one upgrade module per run. It fetches the
  module twice and writes three step-log lines.
  - Suite 86 now: 5 passed, 0 failed, three counts for three lines.
  - Suite 86 at 6b2805e6: 1 passed, 4 failed, six counts for three lines.
- `run_falsifier.py` (`falsifier.json`): `killed_here: true`.
  - drive_debt baseline 18/0, and drive_driver now 5/0.
  - The fix reverted (the `adoption_signers` branch removed, anchor matched once): drive_debt 14/4. It is red
    on the kill at 4 (no restart owed, the next run restarts nothing) and on the failed-restart rows.
  - The registered `upgrade161-adoption-restart-not-owed`, made by check_teeth_mutations.py's own materialize
    (replacement count 1): drive_debt 14/4, red on the same rows.
  - drive_driver over suite 86 at 6b2805e6: red on the count.
- All 57 finding-161 cases materialize with exactly one replacement each, and every mutant compiles.
- Sandbox runs:
  - suite 109: 75 passed, 4 failed (the four AC2 rows, AF_UNIX), as in rounds 5 to 7;
  - `.veldo/validate.py all` exits 0, the template sync check passes (288 pairs), and lint passes.

Not run here: suite 86 itself, so the new row has not run anywhere yet. Its first run is the host's.

An observation outside this round's findings: on a current engine whose restart is due, `announce` prints "Finishing
the upgrade of the installed factory engine that was interrupted after its switch", which does not describe
laying the adoption signer. This is unchanged since round 6 and is not touched here.

## Host runs (required before review)

1. `python3 scripts/selftest.py --suite 86_veldo_0189_engine_upgrade`: every row green (60), including the new
   restart/adoption-signer-kill and the kill-point rows under the once-per-module driver.
2. `python3 scripts/selftest.py --suite 73_veldo_0139_factory_setup`: every row green (43).
3. `python3 scripts/selftest.py --suite 85_veldo_0171_setup_api`: every row green (44).
4. `python3 scripts/selftest.py --suite 109_veldo_0161_adoption`: every row green (81), no HermeticViolation.
5. `python3 scripts/check_gate_mutations.py --finding 161`: 57 of 57 killed, including
   upgrade161-adoption-restart-not-owed on restart/adoption-signer-kill in the unconfined leg.
6. `./scripts/verify.sh`: green.
