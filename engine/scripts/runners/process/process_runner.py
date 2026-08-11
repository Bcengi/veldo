#!/usr/bin/env python3
"""VELDO process / daemon lifecycle runner (reference).

Drives a REAL child process through its lifecycle and proves the four things a
daemon or worker must actually do, not just that it started once: it spawns
(a live pid), it honors a termination signal (SIGTERM within a grace window, or
it is force-killed and that is reported), a respawn yields a DIFFERENT pid, and
a kill of the parent process group leaves no orphaned descendant. A happy-path
check that the process came up misses the daemon that ignores SIGTERM and hangs
forever, and the worker that leaks a detached child on every restart. This runner
sends real signals to a real process group and asserts what happened.

  process_runner.py <fixture.json>

The fixture names a target command to spawn and the lifecycle assertions to make.
The target is spawned in a NEW SESSION so it is a process-group leader; the runner
then signals the whole group with os.killpg. For the kill-tree assertion the
target reports its child-of-child pid(s) by appending them (one per line) to the
file named in the VELDO_PIDFILE environment variable the runner sets, so the runner
can confirm every descendant is gone after the group is killed. This is the seam
an adopting repo keeps: point spawn at your daemon and have it record its worker
pids to VELDO_PIDFILE, or wire the assertions to your own supervisor.

Fixture format (JSON):
  {
    "name": "well-behaved daemon",
    "spawn": ["python3", "-c", "..."],       # argv array, run WITHOUT a shell
    "env": {"EXTRA": "value"},               # optional extra environment
    "assertions": ["spawn", "graceful_signal", "respawn", "kill_tree"],
    "grace_seconds": 5.0,                     # window to exit after SIGTERM
    "spawn_settle_seconds": 0.3,             # window to confirm a live pid
    "descendant_timeout_seconds": 3.0,       # window for the target to report a child
    "kill_tree_window_seconds": 6.0          # window for descendants to die
  }

Lifecycle assertions (the fixture must declare at least one, or it asserts
nothing and is a fixture error - a check that asserts nothing is not proof):
  spawn            the target comes up and stays alive (a live pid); a command
                   that cannot be spawned or that exits immediately fails named
  graceful_signal  SIGTERM is sent to the group; the target must exit within the
                   grace window. A target that ignores SIGTERM is force-killed
                   with SIGKILL and THAT is reported as the failure (never a hang)
  respawn          spawn, terminate, spawn again; the second pid must be a
                   different live pid (a fresh process, not the old one reused)
  kill_tree        the target must report a child-of-child; the parent group is
                   killed; any descendant left alive is a named orphan failure
                   (a setsid-escaped grandchild that survives a group kill is
                   exactly the leak this catches)

Exit 0 = every declared assertion held. Exit 1 = at least one failed (or the
fixture asserts nothing / names an unknown assertion / cannot be read), with the
failing assertion and what was observed named on stdout. The control logic is
driven over real short-lived subprocesses with no external dependency in
scripts/selftest.py, so the runner is gate-tested without the daemon under test.
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

POLL = 0.05  # seconds between liveness polls; the windows are the real bounds


def _alive(pid):
    """True if pid names a live (non-zombie) process. Signal 0 is the portable
    liveness probe; where /proc is available a zombie (exited but not yet reaped
    by its reparented init) is reported dead so a briefly-unreaped descendant is
    never mistaken for a leaked orphan."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # it exists; it just is not ours to signal
    try:
        with open("/proc/%d/stat" % pid, "r") as fh:
            after_comm = fh.read().rsplit(")", 1)[1].split()
            if after_comm and after_comm[0] == "Z":
                return False
    except (FileNotFoundError, IndexError, OSError):
        pass
    return True


def _signal_group(pgid, sig):
    try:
        os.killpg(pgid, sig)
    except (ProcessLookupError, PermissionError):
        pass


def _kill_pid(pid, sig):
    try:
        os.kill(pid, sig)
    except (ProcessLookupError, PermissionError):
        pass


def _spawn(argv, env_extra, pidfile):
    """Spawn the target in a new session so it leads its own process group.
    start_new_session makes the child a session and process-group leader, so its
    pgid equals its pid and os.killpg(pid, sig) reaches the whole tree. Raises
    FileNotFoundError/OSError when the command cannot be spawned; the caller
    turns that into a named spawn failure rather than a crash."""
    env = dict(os.environ)
    if env_extra:
        env.update({str(k): str(v) for k, v in env_extra.items()})
    env["VELDO_PIDFILE"] = str(pidfile)
    proc = subprocess.Popen(
        argv, start_new_session=True, env=env,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return proc, proc.pid  # pgid == pid because the child called setsid


def _stayed_alive(proc, settle):
    """True if the process is still running after a short settle window (it did
    not spawn-then-immediately-exit)."""
    deadline = time.monotonic() + settle
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False
        time.sleep(POLL)
    return proc.poll() is None and _alive(proc.pid)


def _wait_exit(proc, window):
    """Poll until the direct child exits or the window elapses. Returns True if
    it exited."""
    deadline = time.monotonic() + window
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return True
        time.sleep(POLL)
    return proc.poll() is not None


def _read_pids(pidfile):
    try:
        text = Path(pidfile).read_text()
    except OSError:
        return []
    return [int(line.strip()) for line in text.split("\n") if line.strip().isdigit()]


def _await_pidfile(pidfile, window):
    """Wait for the target to report at least one descendant pid. Returns the
    list (possibly empty if it never reported one)."""
    deadline = time.monotonic() + window
    while time.monotonic() < deadline:
        pids = _read_pids(pidfile)
        if pids:
            return pids
        time.sleep(POLL)
    return _read_pids(pidfile)


def _await_all_dead(pids, window):
    """Wait for every pid to die. Returns the list still alive when the window
    elapses (empty = the whole tree was reaped)."""
    deadline = time.monotonic() + window
    while time.monotonic() < deadline:
        living = [p for p in pids if _alive(p)]
        if not living:
            return []
        time.sleep(POLL)
    return [p for p in pids if _alive(p)]


def _terminate(pgid, proc, grace):
    """Bring an instance down: SIGTERM the group, escalate to SIGKILL if it does
    not exit within the grace window, and reap the direct child."""
    _signal_group(pgid, signal.SIGTERM)
    if not _wait_exit(proc, grace):
        _signal_group(pgid, signal.SIGKILL)
        _wait_exit(proc, grace)
    try:
        proc.wait(timeout=1)
    except Exception:
        pass


def _spawn_or_err(spawn):
    """Call the run-scoped spawn helper, turning a bad command into a named error
    instead of a crash. Returns ((proc, pgid, pidfile), None) or (None, error)."""
    try:
        return spawn(), None
    except (FileNotFoundError, OSError) as e:
        return None, "cannot spawn target: %s" % e


def assert_spawn(spawn, cfg):
    res, err = _spawn_or_err(spawn)
    if err:
        return False, err
    proc, _pgid, _pf = res
    if not _stayed_alive(proc, cfg["settle"]):
        return False, "target did not stay alive after spawn (exited rc=%s)" % proc.returncode
    return True, "spawned a live process (pid %d)" % proc.pid


def assert_graceful_signal(spawn, cfg):
    res, err = _spawn_or_err(spawn)
    if err:
        return False, err
    proc, pgid, _pf = res
    if not _stayed_alive(proc, cfg["settle"]):
        return False, "target exited before it could be signalled (rc=%s)" % proc.returncode
    _signal_group(pgid, signal.SIGTERM)
    if _wait_exit(proc, cfg["grace"]):
        return True, "exited within %.3gs of SIGTERM (rc=%s)" % (cfg["grace"], proc.returncode)
    _signal_group(pgid, signal.SIGKILL)
    _wait_exit(proc, cfg["grace"])
    return False, ("ignored SIGTERM: still running after %.3gs, had to be force-killed "
                   "with SIGKILL (force-kill reported)" % cfg["grace"])


def assert_respawn(spawn, cfg):
    res1, err = _spawn_or_err(spawn)
    if err:
        return False, err
    proc1, pgid1, _pf1 = res1
    if not _stayed_alive(proc1, cfg["settle"]):
        return False, "first spawn did not stay alive (rc=%s)" % proc1.returncode
    pid1 = proc1.pid
    _terminate(pgid1, proc1, cfg["grace"])
    res2, err = _spawn_or_err(spawn)
    if err:
        return False, err
    proc2, _pgid2, _pf2 = res2
    if not _stayed_alive(proc2, cfg["settle"]):
        return False, "respawn did not yield a live process (rc=%s)" % proc2.returncode
    pid2 = proc2.pid
    if pid1 == pid2:
        return False, "respawn returned the same pid %d; no fresh process was created" % pid1
    return True, "respawn produced a different live pid (%d -> %d)" % (pid1, pid2)


def assert_kill_tree(spawn, cfg):
    res, err = _spawn_or_err(spawn)
    if err:
        return False, err
    proc, pgid, pf = res
    if not _stayed_alive(proc, cfg["settle"]):
        return False, "target exited before it spawned a child-of-child (rc=%s)" % proc.returncode
    descendants = _await_pidfile(pf, cfg["readiness"])
    if not descendants:
        return False, ("target reported no child-of-child within %.3gs; kill_tree cannot "
                       "be verified" % cfg["readiness"])
    _signal_group(pgid, signal.SIGTERM)
    if not _wait_exit(proc, cfg["grace"]):
        _signal_group(pgid, signal.SIGKILL)
        _wait_exit(proc, cfg["grace"])
    orphans = _await_all_dead(descendants, cfg["kill_window"])
    if orphans:
        for pid in orphans:
            _kill_pid(pid, signal.SIGKILL)
        return False, ("kill-tree left orphaned descendant(s) %s alive after the parent "
                       "process group was killed" % orphans)
    return True, "killing the parent group reaped all %d descendant(s); no orphans" % len(descendants)


ASSERTIONS = {
    "spawn": assert_spawn,
    "graceful_signal": assert_graceful_signal,
    "respawn": assert_respawn,
    "kill_tree": assert_kill_tree,
}


def _teardown(tracked):
    """Guarantee the harness itself leaks nothing: force-kill every spawned group
    and every descendant it recorded (some deliberately escaped their group), then
    reap the direct children."""
    for proc, pgid, pf in tracked:
        _signal_group(pgid, signal.SIGKILL)
        for pid in _read_pids(pf):
            _kill_pid(pid, signal.SIGKILL)
    for proc, pgid, pf in tracked:
        try:
            proc.wait(timeout=2)
        except Exception:
            pass


def run(fixture):
    """Drive the target through its declared lifecycle assertions and return a
    machine-readable result. Real subprocesses are spawned and torn down; passed
    is False on any failed assertion or on a fixture error (no spawn argv, no
    assertions, or an unknown assertion)."""
    result = {"name": fixture.get("name"), "passed": True,
              "assertions": [], "failures": [], "error": None}

    argv = fixture.get("spawn")
    if not isinstance(argv, list) or not argv or not all(isinstance(a, str) for a in argv):
        result["passed"] = False
        result["error"] = "fixture has no 'spawn' argv list of strings"
        result["failures"].append(result["error"])
        return result

    names = fixture.get("assertions")
    if not isinstance(names, list) or not names:
        result["passed"] = False
        result["error"] = ("fixture asserts nothing: declares no lifecycle assertions "
                           "(spawn, graceful_signal, respawn, kill_tree)")
        result["failures"].append(result["error"])
        return result

    unknown = [n for n in names if n not in ASSERTIONS]
    if unknown:
        result["passed"] = False
        result["error"] = ("unknown lifecycle assertion(s) %s; known: %s"
                           % (unknown, sorted(ASSERTIONS)))
        result["failures"].append(result["error"])
        return result

    cfg = {
        "grace": float(fixture.get("grace_seconds", 5.0)),
        "settle": float(fixture.get("spawn_settle_seconds", 0.3)),
        "readiness": float(fixture.get("descendant_timeout_seconds", 3.0)),
        "kill_window": float(fixture.get("kill_tree_window_seconds", 6.0)),
    }
    env_extra = fixture.get("env")

    tmp = tempfile.mkdtemp(prefix="veldo-lifecycle-")
    tracked = []
    counter = [0]

    def spawn():
        counter[0] += 1
        pf = Path(tmp) / ("descendants_%d.pids" % counter[0])
        pf.write_text("")
        proc, pgid = _spawn(argv, env_extra, pf)
        tracked.append((proc, pgid, pf))
        return proc, pgid, pf

    try:
        for name in names:
            passed, detail = ASSERTIONS[name](spawn, cfg)
            result["assertions"].append({"name": name, "passed": passed, "detail": detail})
            if not passed:
                result["passed"] = False
                result["failures"].append("%s: %s" % (name, detail))
    finally:
        _teardown(tracked)
        shutil.rmtree(tmp, ignore_errors=True)

    return result


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    path = Path(argv[1])
    try:
        fixture = json.loads(path.read_text())
    except Exception as e:
        print("cannot read fixture %s: %s" % (path, e))
        return 2
    result = run(fixture)
    print("process lifecycle: %r" % result["name"])
    for a in result["assertions"]:
        print("%s  %s: %s" % ("PASS" if a["passed"] else "FAIL", a["name"], a["detail"]))
    if result["error"] and not result["assertions"]:
        print("FAIL  %s" % result["error"])
    if result["passed"]:
        print("lifecycle PASSED: spawn, signal, respawn, and kill-tree all hold")
        return 0
    print("lifecycle FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
