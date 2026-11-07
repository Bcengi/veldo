# VELDO-0274 proof: the 0127 factory removes every slice it creates

Status: run by the lead under the gate lock on 2026-11-07 at 00c77d58
(proof/VELDO-0274/lead-run-2026-11-07.md). All suites were green, and five of the six falsifier cases
behaved as expected. exit-skips-stop also turned slices/sweep-dead red, so its targets now include that row
(see Falsifiers). Two runs are still owed: that case again with the corrected targets, and
`selftest.py --suite 129_veldo_0274_factory_slices` now that requires.json has a closure for 129. The second
session waited 20 minutes for the lock (09:52 to 10:12Z) and never got it. Both runs are in
proof/VELDO-0274/pending_runs.sh and neither has been observed.

## What was built, per AC

AC1. proof/VELDO-0127/factory.py: factory() now returns a `Factory` (a SimpleNamespace, so every existing
attribute caller keeps working) that is a context manager. `__enter__` starts veldo0127-<pid>.slice;
`__exit__` restores the signal handlers, runs `systemctl --user stop` on the slice, and polls
`systemctl --user list-units --all` for up to 10 s until the slice is no longer listed. If it is still
listed, it raises `SliceLeft` naming the slice. Suites 88, 89 and 90 use `with factory.factory(...) as f:`
inside their existing try, so a SliceLeft turns every row red with the slice's name. Suite 86 enters the
factory through a contextlib.ExitStack that its finally block closes. Its two systemctl stop lines are
gone, and a SliceLeft there turns all its rows red. When no user manager answers (no systemctl, or a
nonzero list), the factory treats nothing as loaded.

AC2. While the factory is open, `__enter__` installs handlers for SIGTERM, SIGINT and SIGHUP (main thread
only). A handler stops the slice, resets the signal to SIG_DFL and re-sends it to its own process.
`__enter__` first stops every listed veldo0127-<pid>.slice whose pid is not a live process
(os.kill(pid, 0) raising ProcessLookupError) and prints one line naming it. The slice of a live process,
or of the current one, is never touched.

AC3. New suite scripts/suites/129_veldo_0274_factory_slices.py. It is the last suite in the manifest. Its
`slices/end-of-run` row requires that no veldo0127-<this process's pid>.slice is listed.

Unit rows (suite 129):
- `slices/return`: a child process starts the factory and launches a fake engine as a transient service
  in the slice; the body returns.
- `slices/raise`: the same, but the body raises.
- `slices/sigterm`: SIGTERM is sent to a child that is inside the factory.
- `slices/sweep-dead` and `slices/sweep-live`: one slice is planted for a dead pid and one for a live
  sleeper.
- `slices/end-of-run`: as described under AC3.

Each child row also requires that the slice was loaded and the engine was active during the body, so a
row cannot pass vacuously. When no manager answers, the five child rows stand down with a printed line.

Manifest: entry for 129 (resources systemd_user_manager 1). Suites 88, 89 and 90 also declare
systemd_user_manager 1, because entering the factory now starts a slice.

## Falsifiers (driver: proof/VELDO-0274/falsify.py)

Each case copies the checkout without .git, applies one exact replacement, runs the selected suites
through selftest (VELDO_SUITE_ORDER plus --upto), and prints one JSON line. The anchors were checked:
each one occurs exactly once.

- exit-skips-stop (AC1): `__exit__` drops its stop call. Expected red: slices/return, slices/raise,
  slices/sweep-dead. The sweep-dead row's 'enter' child also leaves the factory, whose exit now raises
  SliceLeft, so that child exits nonzero and the row's `code == 0` check is red. sweep-live has no
  exit-code check and stays green. The lead's run showed exactly these three rows red.
- no-signal-handler (AC2.1): `signal.signal(n, self._interrupted)` becomes `signal.getsignal(n)`.
  Expected red: slices/sigterm.
- sweep-ignores-liveness (AC2.2): the sweep condition drops `not live(pid)`. Expected red:
  slices/sweep-live.
- defaults-without-context-manager (AC3): suite 88's `with factory.factory(...) as f:` becomes
  `for f in [factory.factory(...).__enter__()]:`, which enters the factory and never leaves it. Runs 88
  then 129. Expected red: slices/end-of-run.
- baseline and baseline-88: no mutation. Expected all green.

Red then green: observed by the lead (lead-run-2026-11-07.md). exit-skips-stop with the three targets is
not yet observed; see pending_runs.sh.

## Open: needs a change outside the footprint (not made)

1. Resolved: requires.json joined the footprint at 0dfa2188. It was regenerated with
   `python3 scripts/run_scope.py --emit-requires`, and the only change is the new entry for 129 (its closure
   is itself, from manifest.json). No other entry changed.
2. "Registered mutation" means cases in scripts/check_teeth_mutations.py, which is outside the footprint.
   The four cases exist only in falsify.py.
3. scripts/gate_unconfined.json (protected) does not list 129. In the gate's confined leg there is no
   user manager, so the slice rows stand down. They only assert if 129 is listed whole for the unconfined
   leg, where it runs after 86.
4. The spec's premise does not hold. Suites 88, 89 and 90 never launched into the slice: they call
   Receiver._baseline with no containment profile. Only suite 86 created the slice. The AC3 mutation
   therefore holds because entering the factory now starts the slice.
5. Two other users of the factory still call factory() without the context manager:
   proof/VELDO-0127/delivery_fixture.py (suites 87 and 103) and proof/VELDO-0127/live.py. Both are outside
   the footprint. Construction alone creates no slice, so this change does not make them leak.

## Inherited reds

None recorded: no suite was run.
