# VELDO-0274 proof: the 0127 factory removes every slice it creates

Status: earlier runs are in lead-run-2026-11-07.md (the lead's run at 00c77d58 and job 12 at a44aaf1a). The
lead's runs at 05c05b62 and job 28 at 8ee0e2e2 are under "Fix round 4" and "Fix round 5" below, with their raw
summary lines in pending-summary.txt. Fix round 5 (this round) registers AC3's mutation; its runs are under
"Fix round 5".

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

AC3. New suite scripts/suites/129_veldo_0274_factory_slices.py. It is the last suite in the manifest and
is listed whole in scripts/gate_unconfined.json, so in the gate it runs in the unconfined leg (the leg with a
user manager), in the same selftest process as suite 86 and after it (selftest runs a leg's suites in
manifest order in one process). Its `slices/end-of-run` row requires that no veldo0127-<pid>.slice whose pid
belongs to this run is loaded: this process, a live descendant of it, or a gone process whose slice became
active (ActiveEnterTimestampMonotonic) after this process started. A slice of a live process outside this
process's tree is another run's and is never judged.

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

Manifest: entry for 129 (resources systemd_user_manager exclusive: the entry sweep, and its mutation that
ignores liveness, read every veldo0127 slice loaded there). Suites 88, 89 and 90 also declare
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

Red then green: observed by the lead (lead-run-2026-11-07.md), including exit-skips-stop with the three
targets at a44aaf1a.

Registered in scripts/check_teeth_mutations.py (finding 274), so the mutation stage runs them against suite
129, which loads the factory by `ROOT / "proof/VELDO-0127" / "factory.py"`, the anchor the stage's worker
replaces with the mutant copy, and passes that path to its children: slices274-exit-skips-stop (AC1,
targets slices/return, slices/raise, slices/sweep-dead), slices274-no-signal-handler (AC2.1, slices/sigterm),
slices274-sweep-ignores-liveness (AC2.2, slices/sweep-live). Each anchor occurs exactly once in factory.py.
AC3's mutation is registered there too: slices274-factory-user-without-exit-stack makes suite 86 enter the
factory without its ExitStack (target slices/end-of-run). Suite 129 names suite 86 by
`ROOT / "scripts/suites" / "86_veldo_0127_agent_configuration.py"`, the anchor the worker replaces, and runs
the replaced copy in its own process before the end-of-run row, as the gate's unconfined leg runs 86 before
129; the no-op copy is the control. Unreplaced, 129 does not run 86. Suite 86's rows are counted but never
reported as 129's, so the control's rows equal the baseline's. A leaked slice is stopped after it is judged.
falsify.py's defaults-without-context-manager case (suite 88) stays as a developer falsifier.

## Open items

1. Resolved: requires.json joined the footprint at 0dfa2188. It was regenerated with
   `python3 scripts/run_scope.py --emit-requires`, and the only change is the new entry for 129 (its closure
   is itself, from manifest.json). No other entry changed.
2. Resolved: scripts/check_teeth_mutations.py is in the footprint since 0dfa2188; the AC1 and AC2 cases
   are registered there, and since fix round 5 the AC3 case too, through suite 129's anchor for suite 86
   (no change to scripts/mutation_observer.py).
3. Resolved: scripts/gate_unconfined.json joined the footprint and protected_paths at a8040f9b and lists
   129 whole (a607b443).
4. The spec's premise does not hold. Suites 88, 89 and 90 never launched into the slice: they call
   Receiver._baseline with no containment profile. Only suite 86 created the slice. The AC3 mutation
   therefore holds because entering the factory now starts the slice.
5. Two other users of the factory still call factory() without the context manager:
   proof/VELDO-0127/delivery_fixture.py (suites 87 and 103) and proof/VELDO-0127/live.py. Both are outside
   the footprint. Construction alone creates no slice, so this change does not make them leak.

## Inherited reds

None: every recorded run of suites 86, 88, 89, 90 and 129 was green.

## Fix round 3 (2026-11-07)

Commits: a607b443 (end-of-run row judges every slice of this run; 129 joins the unconfined leg), 7d2fbcd0
(AC1 and AC2 mutations registered; 129 loads the factory by the worker's anchor), f4f281f6 (AC3 mutation's
comment; pending_runs.sh flock -w).

Runs of this round: pending. The gate lock was not free from 11:56Z to 12:16Z (flock -w 1200), so no suite,
falsifier or mutation case ran in this round. Every remaining run is in proof/VELDO-0274/pending_runs.sh
(no flock and no systemd-run inside; the lead runs it inside the lock; one line per step to
proof/VELDO-0274/pending-summary.txt, logs under /tmp/v274-pending). `bash -n` on it passed. Owed:
1. `python3 scripts/selftest.py --suite 129_veldo_0274_factory_slices` (the new end-of-run row and the
   factory loaded by the worker's anchor).
2. `python3 proof/VELDO-0274/falsify.py baseline exit-skips-stop defaults-without-context-manager`
   (AC3's falsifier against the new end-of-run row).
3. `python3 scripts/check_teeth_mutations.py --finding 274` (the three registered cases: baseline green,
   mutant red on its targets).
Not runnable outside the gate: the unit stage's unconfined leg (its variables are set only by
scripts/gate_legs.py). The mutation stage's unconfined leg is runnable through
`check_gate_mutations.py --finding 274` (found in fix round 4).

## Fix round 4 (2026-11-07)

The lead's run of round 3's pending_runs.sh at 05c05b62: suite 129 32 passed, 0 failed; falsify.py baseline,
exit-skips-stop and defaults-without-context-manager as expected; no veldo0127 unit loaded after.
`check_teeth_mutations.py --finding 274` failed with missing_target (slices/return and the others): every
worker ran in leg "confined", where no user manager answers, so the slice rows stood down.

Cause: the case's leg is chosen by in_leg in scripts/check_gate_mutations.py from scripts/gate_unconfined.json
(129 is listed whole), but only the coordinator's own CLI (check_gate_mutations.py main, legs.mutation_leg)
passes that leg to run_stage. check_teeth_mutations.py's main passes none, so it runs every case confined.
In the gate the 274 cases already run unconfined; no registration change is needed. The entry that runs them
as the gate does is `python3 scripts/check_gate_mutations.py --finding 274`.

unknown_closure: the reuse reason of a case with no closure profile, not an error. An unconfined case is never
declared (the coordinator refuses a declared unconfined case as driver_error) and its reason becomes
unconfined_leg, so no requires.json or mutation_case_inputs.json entry is added.

Commit: 58c578bc (the 274 cases' comment names the unconfined leg and the coordinator entry).

Runs of this round: pending. The gate lock was not free from 13:34Z to 13:54Z (flock -w 1200). The owed runs
are in proof/VELDO-0274/pending_runs.sh (rewritten for this round, `bash -n` passed; logs under
/tmp/v274-pending): `check_gate_mutations.py --finding 274` (expected: three cases unconfined, baseline green,
mutant red on its targets) and `selftest.py --suite 129_veldo_0274_factory_slices`.

## Fix round 5 (2026-11-07)

The lead's job 28 at 8ee0e2e2 (pending-summary.txt): suite 129 via --suite 32 passed, 0 failed; falsify.py as
expected; `check_gate_mutations.py --finding 274` passed, 3 of 3 cases in the unconfined leg, 3 rejected;
`check_teeth_mutations.py --finding 274` fails confined, as expected (fix round 4); no veldo0127 unit loaded
after.

The spec now names suite 86 in AC3's falsifier (lead, 4228b098). Commit b54d5520 registers that mutation
(slices274-factory-user-without-exit-stack, described under Falsifiers) and removes the claim that the
protected worker blocks it.

Runs of this round, at f19fbeb0 (code as at b54d5520), inside the gate lock (pending-summary.txt):
`check_gate_mutations.py --finding 274` passed, 4 of 4 cases in the unconfined leg, 4 rejected, including
slices274-factory-user-without-exit-stack (its no-op control, suite 86's unmutated copy run inside 129,
equal to the baseline; the mutant red on slices/end-of-run). `selftest.py --suite
129_veldo_0274_factory_slices` 32 passed, 0 failed (exit 2 is the partial-run code). No veldo0127 or
veldo0274 unit loaded after. pending_runs.sh is updated for these two runs (failing row names added to its
summary lines, `bash -n` passed) but nothing is owed.
