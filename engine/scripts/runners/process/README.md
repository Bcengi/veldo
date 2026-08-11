# Veldo process / daemon lifecycle runner (reference)

Real proof for a long-running process: it drives a genuine child process through
its lifecycle and asserts the four things a daemon or worker must actually do,
not just that it started once. A happy-path "the process came up" check misses
the daemon that ignores SIGTERM and hangs forever on shutdown, and the worker
that leaks a detached child on every restart. This runner sends real signals to
a real process group and asserts what happened. It uses only the Python standard
library (subprocess, os, signal).

## Use

```
process_runner.py <fixture.json>   # exit 0 = spawn, signal, respawn, kill-tree hold
test_process_runner.sh              # self-contained regression over the fixture pair
```

Stdlib only, so a reviewer reruns it with no setup. The runner is
process-agnostic: the fixture names the argv, so a repo points it at its own
daemon.

## The lifecycle seam

The target is spawned in a NEW SESSION, so it leads its own process group; the
runner signals the whole group with `os.killpg`. For the kill-tree assertion the
target reports its child-of-child pid(s) by appending them, one per line, to the
file named in the `VELDO_PIDFILE` environment variable the runner sets. That is
the seam an adopting repo keeps: point `spawn` at your daemon and have it record
its worker pids to `VELDO_PIDFILE`, or wire the assertions to your own supervisor.

## Fixture format

```json
{
  "name": "well-behaved daemon",
  "spawn": ["python3", "-c", "..."],
  "env": {"EXTRA": "value"},
  "assertions": ["spawn", "graceful_signal", "respawn", "kill_tree"],
  "grace_seconds": 5.0,
  "spawn_settle_seconds": 0.3,
  "descendant_timeout_seconds": 3.0,
  "kill_tree_window_seconds": 6.0
}
```

`spawn` is an argv array run WITHOUT a shell. `env` (optional) adds environment
variables. The window fields are optional and default to generous values. The
fixture must declare at least one assertion, or it asserts nothing and is a
fixture error.

## Lifecycle assertions

- `spawn` - the target comes up and stays alive (a live pid). A command that
  cannot be spawned, or one that exits immediately, fails named (never a crash).
- `graceful_signal` - SIGTERM is sent to the group; the target must exit within
  the grace window. A target that ignores SIGTERM is force-killed with SIGKILL
  and THAT is reported as the failure, so the runner never hangs on a stuck
  daemon.
- `respawn` - spawn, terminate, spawn again; the second pid must be a different
  live pid, proving a fresh process was created rather than the old one reused.
- `kill_tree` - the target must report a child-of-child; the parent group is
  killed; any descendant left alive is a named orphan failure. A grandchild that
  called `setsid()` to escape the parent group survives a group kill and is
  exactly the leak this catches.

Exit 0 = every declared assertion held. Exit 1 = at least one failed (or the
fixture asserts nothing, names an unknown assertion, or cannot be read), with the
failing assertion and what was observed named on stdout.

The `fixtures/` pair demonstrates both outcomes: `pass.lifecycle.json` (a
well-behaved sleeper that spawns a child, dies on SIGTERM, and whose child is
reaped with the group) exits 0, and `fail.lifecycle.json` (a target that ignores
SIGTERM and leaks a setsid-escaped child) exits 1 with graceful-exit and
kill-tree both named. Both fixtures drive `python3`, so they run anywhere python
is present with nothing to install.

## Why it is a reference

The runner drives a real process, but a repository wires it to ITS daemon or
worker and points the lifecycle or integration gate slot at it. Its control logic
(spawning in a new session, signalling the group, confirming exit or force-kill,
requiring a fresh pid on respawn, and detecting an orphaned descendant) is
unit-tested in `scripts/selftest.py` by driving real short-lived `python -c`
sleepers with generous windows, so the every-commit gate proves the logic with no
external dependency. It is marked `reference` in `capabilities.yaml`: the veldo
home repository ships no long-running process of its own, so it does not run the
runner in its own gate; it ships it for repos that do.
