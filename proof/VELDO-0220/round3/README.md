# VELDO-0220 round 3 evidence

Finding A is a suite boundary error: the coordinator refuses every mutation case
whose suite is listed for only some rows. Suite 113 now contains the three lock
and not-started rows. Suite 114 contains the scope row, including scope creation
and teardown on kill, termination, normal completion and a red stage. The one
approved unconfined entry names suite 114 whole. The mutation registry sends its
three scope cases to 114 and retains four confined cases in 113.

All four row bodies are AST-identical to 6d879aae after moving and dedenting.
Only fixture setup and probes were trimmed for the separate suites. Suite 113
contains no systemd invocation or scope configuration read. No production gate
helper or coordinator policy changes are needed.

The reproducible driver is check.py. Pass a clean temporary worktree at 6d879aae
as its sole argument and invoke it through blocking flock on
/home/dmitry/.local/state/core-gates/.gate.lock. It runs, in order:

1. The old checkout's real mutation coordinator, selecting finding 220. Expected:
   seven registered, none executed, rows_scoped_unconfined_case.
2. The current checkout's selftest dispatcher, selecting only suites 113 and 114.
   Expected: four passing ticket rows. Exit 2 denotes a passing partial run.
3. The current checkout's real mutation coordinator, selecting finding 220 and
   forcing fresh execution. Expected: seven executed and rejected, no reuse,
   every baseline and no-op green, each mutant red on its exact target row.
   The driver checks four confined cases and three unconfined cases explicitly.

The coordinator runs in its normal CLI path, including worker confinement and
ownership accounting. This driver never calls teeth.worker directly. Worker
logs and receipts are collected outside the working tree to avoid changing the
coordinator's input snapshot. Only logs, ledgers and job descriptors are retained,
not temporary worker homes. summary.json records commands, exits, source digests,
commit identities and per-case row observations.

The test fixtures execute copies of the gate with stub stages and scratch locks.
The repository's canonical verify command is not run. These targeted results
cannot replace the owner's canonical gate or an independent review.
