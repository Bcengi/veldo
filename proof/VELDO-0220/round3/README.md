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

The first coordinator drive after the split is retained in red-runtime/.
It admits and executes all seven cases, rejecting the four confined mutants,
but refuses the scope results as invalid_baseline: its clean worker environment
has no XDG_RUNTIME_DIR or DBUS_SESSION_BUS_ADDRESS. The ordinary selected suite
run passes all four rows because the interactive environment has the runtime
path. Suite 114 now supplies /run/user/<uid> when XDG_RUNTIME_DIR is absent, as
the other systemd suites do. This is fixture setup; the coordinator's environment
and confinement policy stay unchanged.

## Final results

Implementation commit 0b25e78e was checked through the real coordinator CLI under
the owner's blocking host flock. red-coordinator.json records the original
seven-case refusal. green-suites.log records three passing suite 113 rows and
one passing suite 114 row (exit 2, a passing partial run). green-coordinator.json
records seven registered, seven executed, seven rejected, zero reused, 13 worker
invocations and zero surviving workers in 50.72 seconds. Every baseline and no-op
control is green. The source hashes in summary.json match the implementation.

| Falsifier | Suite | Target row | Mutant |
| :--- | :--- | :--- | :--- |
| host220-forged-holder | 113 | host-lock/held-not-started | red |
| host220-ignores-lock | 113 | host-lock/held-not-started | red |
| host220-lock-inherited | 113 | host-lock/released-on-exit | red |
| host220-lock-not-retained | 114 | host-scope/own-scope | red |
| host220-no-scope | 114 | host-scope/own-scope | red |
| host220-no-scope-kill | 114 | host-scope/own-scope | red |
| host220-not-started-is-red | 113 | host-lock/not-started-not-red | red |

The coordinator receipt places the four suite 113 cases in the confined leg and
the three suite 114 cases in the unconfined leg. Its resource and ownership
receipts show cleanup completed; every directory named in its ownership ledgers
is absent after the driver exits. The temporary original checkout was removed.

green-clean-runtime.log and clean-runtime.json record the additional single-file
check with XDG_RUNTIME_DIR and DBUS_SESSION_BUS_ADDRESS removed: suite 114's scope
row passes through its runtime fallback, with zero failed rows and partial exit 2.
This single-file check used the owner's allowance; the combined suites and all
coordinator drives used blocking flock. A fresh independent review and the owner's
canonical gate remain before landing, as OPEN.md records.
