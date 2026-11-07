# VELDO-0274 proof: the 0127 factory removes every slice it creates

Status: built, NOT yet run. The one batch that would run every suite and falsifier waited about 2 hours
for the core-gates lock (/home/dmitry/.local/state/core-gates/.gate.lock) and was stopped by the session's
time limit before it got the lock. No row outcome and no falsifier result has been observed. Nothing below
claims a red or a green.

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

- exit-skips-stop (AC1): `__exit__` drops its stop call. Expected red: slices/return, slices/raise.
- no-signal-handler (AC2.1): `signal.signal(n, self._interrupted)` becomes `signal.getsignal(n)`.
  Expected red: slices/sigterm.
- sweep-ignores-liveness (AC2.2): the sweep condition drops `not live(pid)`. Expected red:
  slices/sweep-live.
- defaults-without-context-manager (AC3): suite 88's `with factory.factory(...) as f:` becomes
  `for f in [factory.factory(...).__enter__()]:`, which enters the factory and never leaves it. Runs 88
  then 129. Expected red: slices/end-of-run.
- baseline and baseline-88: no mutation. Expected all green.

Red then green: NOT OBSERVED (the run never got the lock). The commands to run are in
/tmp/v274-runs/batch.sh: suites 86, 88, 89 and 90 each with --suite, then 129, then falsify.py with all
cases. Run them under the gate lock.

## Open: needs a change outside the footprint (not made)

1. scripts/suites/requires.json (derived, held fresh by check_generated.sh) has no closure for 129. As a
   result, `selftest.py --suite 129_veldo_0274_factory_slices` refuses, and check_generated goes red until
   someone runs `python3 scripts/run_scope.py --emit-requires`.
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
