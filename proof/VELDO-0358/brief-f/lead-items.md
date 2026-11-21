# Brief F: items for the lead

1. Suite 66's `authority/installed-assets` is red on this branch alone: the scaffold's `_FILES` lacks
   `.veldo/timers.py`, which the installer's closure now contains (control_service loads the table). Brief E
   fixed it in its own branch (a48602c9, `_FILES += [".veldo/timers.py"]`). With brief E's engine changes
   applied to a scratch copy of this branch, suite 66 is green (61 passed, 0 failed). Nothing to do but land E
   with or before F. The falsifier and loaded runs here used a scratch copy with the equivalent one line.

1b. BLOCKER for suite 36_veldo_0023_journal, outside every brief's files: its row journal/replay-determinism
   requires control_store's imports to be a subset of {hashlib, importlib, json, os, signal, sqlite3, subprocess,
   time}. The table loader brief F added to control_store (as every module of 4.8 has one) imports `sys` for the
   installation's shared table (sys.modules). `sys` is standard library and the row's stated intent ("only the
   standard library, no execution runtime") still holds; adding "sys" to that set makes the suite green
   (verified in a scratch copy: 44 passed, 0 failed). Not edited here: the suite is in no brief's files and not
   in the footprint. The alternative, leaving the store's busy wait outside the table, would break AC15.

2. Opened-files record gap (brief A's hook in scripts/selftest.py): a module loaded through
   spec_from_file_location whose `__pycache__` entry is fresh is read from the .pyc only, and the hook drops
   every path containing `__pycache__`, so the .py is never recorded. Measured: suite 71's record named only
   itself until the base tree's caches were removed; then it named scripts/suites/support/v73_authority.py.
   Suites 86 and 110 lost about half their opened files the same way. The census scope, the proven set and
   "changed suite" read that record. Mapping `__pycache__/NAME.cpython-XY.pyc` to `NAME.py` in the hook closes it.

3. Files my suites open that are in no brief's files and outside the footprint, each with census sites, so
   these suites cannot be in the proven set yet and their mutation kills read `unproven`:
   scripts/suites/support/v73_authority.py (71, 86), scripts/suites/support/setup_runtime.py (86),
   proof/VELDO-0172/compare_formats.py (83, 86, 110), scripts/suites/support/identity_wire.py (110).
   Not touched. Suite 86 no longer calls setup_runtime's short ready/wait bounds (it waits on events itself);
   only `runtime.install` and `wake_authority` are still used from it.

4. Two accept intervals stay as census sites: `listener.settimeout(ACCEPT_SECONDS)` in control_service.serve
   and `self.server.settimeout(0.25)` in control_client_api.Hints. Design 4.8 keeps them ("the service's accept
   interval (cadence)"): a lap of a serving loop, not a giving-up deadline, and a profile at the hang bound would
   stop the laps (the channel pass and the hint retry run once per lap). They remain baseline entries; the
   wave1/no-sites rows name these two keys exactly. AC15's "no numeric timeout in those engine files outside the
   table" therefore holds for every giving-up deadline but not for these two cadences: an exception kind for a
   cadence, or the cadence's own event (wave 5), is the lead's and owner's decision.

5. Product additions on the service, all in control_service.py: the configuration's `timers_profile`, or the
   manager environment's `VELDO_TIMERS_PROFILE` when the configuration names none, applied before anything is
   armed (suite 86 compares installation records byte for byte, so its stand-in managers use the environment);
   the start record (observation `timers`, the effective values); `STATUS=... channel passes N` after each channel
   pass (sd_notify, errors ignored), which suite 71 waits on; `pending_wakes` in the loop status, which suite 83's
   idle answer reads. A real user manager receives a STATUS line per channel pass (about one a second).

6. Suite 83's reset row keeps a real minute reset (the product reads its own clock for the account reset).
   LEAD was raised from 5 s to 30 s: the reset is stated before the unit's run starts, so the time between
   stating it and the unit's wait pass must stay well under it; with 5 s a slowed launch could put the reset in
   the past. Its two lower bounds are kept (no pass for more than twice the longest interval, read from the
   passes' own recorded times; voluntary context switches at least half the accept laps). The second is a lower
   bound on wakes per second of the service's accept lap; it held in every loaded run (Runs).

6b. BLOCKER FOR LANDING E WITH F (brief E's file, not edited here): with brief E's engine changes, suite 83's
   loop/receiver-death hangs every time, loaded or not (with-brief-e.txt: 9 of 50 loaded runs, 8 of 8 parallel, 2 of 2
   alone). The service is inside control_launch._await_gone: after the orphaned worker's pidfd fires it is unregistered
   but kept in `fds`, containment.alive still sees the unreaped zombie, and the loop polls with nothing registered
   until ORPHAN_SECONDS has passed, which suite 83's timers profile sets to the hang bound. With the production 5 s
   the same path refuses the release and delays the pass by 5 s; that also fits the single loaded red of brief F
   alone (run 9, loop/reset-timer-wake, an account still busy at the reset), still unproven. Fix in brief E: take
   the pidfd's exit as terminated, or never poll an empty set.

7. Removed as data that read the clock: suite 86's VELDO_ROW_TIMINGS row timing (suite 85 keeps its own), the
   "suite seconds" prints of 66, 71, 83, 86 and 110. No row read them.

8. Full unit leg at 5bc570a0 (unit-leg.txt): 10770 passed, 20 failed. Every red is named there: items 1, 1b and 9,
   brief G's (66_veldo_0042 residue, 151_veldo_0313) and inherited (102_veldo_0210). Brief F's own reds were the
   three ipc rows of suite 113 (item 9), fixed at aa7918fd. Not re-run as a whole after the fixes.

9. Suite 113_veldo_0115_authority_store holds a census of control_client's public functions; brief F's public
   `timer()` broke it (3 ipc rows red). Each module's reader is now `_timer` (aa7918fd): 113 green alone
   (reruns.txt). Suite 153_veldo_0323's compatibility/installed-closure is item 1's cause (the scaffold's `_FILES`
   lacks `.veldo/timers.py`): green with that line (reruns.txt).

10. A hung row ends its process (waits.hung: before_exit hooks, then os._exit), so a hung suite leaves what it
   started running: each hung run of suite 83 left its services, receivers and fake workers in their transient
   scopes (with-brief-e.txt, point 7). Suite 83 registers no before_exit hook; whether suites should (brief A's
   runtime) or the dispatcher should stop a hung suite's scopes is the lead's decision.
