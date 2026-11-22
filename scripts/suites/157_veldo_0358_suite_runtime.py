# VELDO-0358 brief A: the suite runtime. The wait primitive's three outcomes (AC1), its event sources and
# the absence of idle wakes (AC2), the latch holder (AC3), the residue row (AC4) and the suite process's
# progress watchdog (AC5), each driven through the real dispatcher (scripts/selftest.py) over a fixture
# tree whose suites are written here. Nothing in this suite waits for time to pass: every wait is on an
# event, and the only number of seconds it names is the bound it hands the primitive's and the
# watchdog's own test parameters.
import json as _v358_json
import os as _v358_os
import select as _v358_select
import shutil as _v358_shutil
import signal as _v358_signal
import subprocess as _v358_subprocess
import sys as _v358_sys
import tempfile as _v358_tempfile
import threading as _v358_threading
from pathlib import Path as _v358_Path

# The subjects, each named once so the mutation driver can put a mutant copy in its place.
_v358_WAITS = ROOT / "scripts/suites/support" / "waits.py"
_v358_HOLDERS = ROOT / "scripts/suites/support" / "holders.py"
_v358_PORTS = ROOT / "scripts/suites/support" / "ports.py"
_v358_SELFTEST = ROOT / "scripts" / "selftest.py"


def _v358_load(name, path):
    import importlib.util as _iu
    spec = _iu.spec_from_file_location(name, str(path))
    module = _iu.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _v358_clean_env(**extra):
    """The environment of a fixture run: none of a gate leg's variables, no record unless asked."""
    env = {k: v for k, v in _v358_os.environ.items()
           if not k.startswith("VELDO_GATE_") and k not in ("VELDO_OPENED_FILES", "VELDO_SUITE_ORDER")}
    env.update(extra)
    return env


def _v358_tree(base, suites):
    """A fixture repository: the real dispatcher, run_scope and shared.py, the support modules under test,
    and a manifest of the fixture suites given as {name: source}, in order."""
    base = _v358_Path(base)
    support = base / "scripts" / "suites" / "support"
    support.mkdir(parents=True)
    _v358_shutil.copyfile(str(_v358_SELFTEST), str(base / "scripts" / "selftest.py"))
    _v358_shutil.copyfile(str(ROOT / "scripts" / "run_scope.py"), str(base / "scripts" / "run_scope.py"))
    _v358_shutil.copyfile(str(ROOT / "scripts" / "suites" / "shared.py"), str(base / "scripts" / "suites" / "shared.py"))
    for path in (_v358_WAITS, _v358_HOLDERS, _v358_PORTS):
        _v358_shutil.copyfile(str(path), str(support / _v358_os.path.basename(str(path))))
    _v358_os.symlink(str(ROOT / ".veldo"), str(base / ".veldo"))
    entries = []
    for name, source in suites.items():
        (base / "scripts" / "suites" / (name + ".py")).write_text(source)
        entries.append({"name": name, "file": name + ".py", "requires": [name], "regions": "fixture",
                        "requires_note": "fixture"})
    (base / "scripts" / "suites" / "manifest.json").write_text(_v358_json.dumps(
        {"schema": "veldo.suites/v1", "entry": "selftest.py", "shared": "shared.py", "suites": entries}))
    (base / "scripts" / "suites" / "requires.json").write_text(_v358_json.dumps(
        {"schema": "veldo.requires/v1", "requires": {name: [name] for name in suites}}))
    return base


def _v358_run(base, names, **env):
    """Run the fixture dispatcher over the named suites, to its end (it has its own watchdog)."""
    argv = [_v358_sys.executable, str(_v358_Path(base) / "scripts" / "selftest.py")]
    for name in names:
        argv += ["--suite", name]
    return _v358_subprocess.run(argv, cwd=str(base), capture_output=True, text=True,
                                stdin=_v358_subprocess.DEVNULL, env=_v358_clean_env(**env))


_v358_PASSED = _v358_load("v358_run_scope", ROOT / "scripts" / "run_scope.py").PARTIAL_PASSED_EXIT


def _v358_suite_counts(text):
    """{suite: rows passed} from a partial run's per-suite lines (its own rows, not its residue row)."""
    out = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[2] == "passed" and parts[0].startswith("fx_"):
            out[parts[0]] = int(parts[1])
    return out


def _v358_lines(text, prefix):
    return [line for line in text.splitlines() if line.startswith(prefix)]


# --------------------------------------------------------------------------------- AC1: three outcomes

_v358_THREE = '''import os, subprocess, sys
import waits
_d = os.environ["V358_DIR"]
_marker = os.path.join(_d, "marker")
_writer = subprocess.Popen([sys.executable, "-c", "open(%r, 'w').close()" % _marker])
_first = waits.wait("marker written", lambda: os.path.exists(_marker), sources=[waits.PathAppears(_marker)])
_writer.wait()
expect("fx/done", _first.outcome == "done")
_never = os.path.join(_d, "never")
_quitter = subprocess.Popen([sys.executable, "-c", "pass"])
_second = waits.wait("a marker the quitter never writes", lambda: os.path.exists(_never),
                     terminal=lambda: (_quitter.poll() is not None, {"exit": _quitter.poll()}),
                     sources=[waits.PathAppears(_never), waits.Pidfd(_quitter)])
expect("fx/impossible", _second.outcome == "impossible")
print("FX OUTCOMES %s %s" % (_first.outcome, _second.outcome), flush=True)
_third = waits.wait("a file nobody writes", lambda: os.path.exists(_never),
                    sources=[waits.PathAppears(_never)], row="fx/hung", hang_bound_for_test=2)
print("FX AFTER HANG %s" % (_third.outcome,), flush=True)
expect("fx/hung", False)
expect("fx/after-one", True)
expect("fx/after-two", True)
'''

_v358_LATER = '''expect("fx/later-suite-row", True)
'''


def _v358_three_outcomes():
    with _v358_tempfile.TemporaryDirectory(prefix="v358-three-") as d:
        base = _v358_tree(_v358_Path(d) / "repo", {"fx_three": _v358_THREE, "fx_later": _v358_LATER})
        work = _v358_Path(d) / "work"
        work.mkdir()
        hang_dir = _v358_Path(d) / "hang"
        hang_dir.mkdir()
        run = _v358_run(base, ["fx_three", "fx_later"], V358_DIR=str(work), VELDO_HANG_DIR=str(hang_dir))
        source = base / "scripts" / "suites" / "fx_three.py"
        hang_line = 1 + source.read_text().splitlines().index(
            '_third = waits.wait("a file nobody writes", lambda: os.path.exists(_never),')
        hung = _v358_lines(run.stdout, "SELFTEST HUNG")
        not_run = [line.split("SELFTEST NOT RUN ", 1)[1] for line in _v358_lines(run.stdout, "SELFTEST NOT RUN")]
        stacks = list(hang_dir.iterdir())
        facts = {
            "outcomes": _v358_lines(run.stdout, "FX OUTCOMES"),
            "no_return_after_hang": not _v358_lines(run.stdout, "FX AFTER HANG"),
            "hung": hung,
            "names_row_wait_and_line": len(hung) == 1 and hung[0].startswith("SELFTEST HUNG fx/hung:")
            and "wait a file nobody writes at %s:%d" % (source, hang_line) in hung[0],
            "not_run": not_run,
            "fails": _v358_lines(run.stdout, "  SELFTEST FAIL"),
            "rc": run.returncode,
            "stack_file": [p.name for p in stacks],
            "stack_names_line": bool(stacks) and ("line %d" % hang_line) in stacks[0].read_text(),
        }
        return facts


def _v358_shared_keeps_no_wait():
    """No clock read, sleep or timed select left in shared.py: its waits are calls into the primitive."""
    import ast as _ast
    tree = _ast.parse((ROOT / "scripts" / "suites" / "shared.py").read_text())
    found = []
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.Import, _ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, _ast.Import) else [node.module]
            if "time" in names:
                found.append("imports time at line %d" % node.lineno)
        if isinstance(node, _ast.Call) and isinstance(node.func, _ast.Attribute):
            if node.func.attr in ("sleep", "monotonic", "time", "perf_counter"):
                found.append("%s at line %d" % (node.func.attr, node.lineno))
            if node.func.attr == "select" and len(node.args) > 3 and not (
                    isinstance(node.args[3], _ast.Constant) and node.args[3].value == 0):
                found.append("timed select at line %d" % node.lineno)
    return found


_v358_f1 = _v358_three_outcomes()
_v358_f1_shared = _v358_shared_keeps_no_wait()
expect("waits/three-outcomes: %r; shared.py waits of its own: %r" % (_v358_f1, _v358_f1_shared),
       _v358_f1["outcomes"] == ["FX OUTCOMES done impossible"]
       and _v358_f1["no_return_after_hang"]
       and _v358_f1["names_row_wait_and_line"]
       and _v358_f1["not_run"] == ["fx/after-one", "fx/after-two", "fx/later-suite-row"]
       and _v358_f1["fails"] == []
       and _v358_f1["rc"] != 0
       and _v358_f1["stack_names_line"]
       and _v358_f1_shared == [])


# ------------------------------------------------------------------------------- AC2: no idle wake

# The waiter runs alone in its own single-threaded process, so nothing but its own wait can block it. Its
# done condition writes one token per reading to the test, and records the thread's voluntary context
# switches as it begins and as it ends each reading: the switches between the end of one reading and the
# start of the next are the ones the wait made while waiting (a reading's own file reads, and the Store
# source's wait for a writer's lock, are work on an event and are reported apart). Each event is caused
# only after the token of the reading before it, and only after the causing side has done a fixed amount
# of hashing, so that a waiter which woke on a timer of any interval shorter than that work would show it.
# Nothing here waits on time.
_v358_WAITER = r'''import json, os, sys
sys.path.insert(0, sys.argv[1])
import waits
kind, arg, token, need = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])

def switches():
    with open("/proc/thread-self/status") as f:
        for line in f:
            if line.startswith("voluntary_ctxt_switches:"):
                return int(line.split()[1])

readings = []
lock_switches = [0]

def counted(read):
    def reading():
        begin = switches()
        value = read()
        readings.append((begin, switches()))
        os.write(token, b".")
        return value
    return reading

if kind == "pidfd":
    sources = [waits.Pidfd(int(p)) for p in arg.split(",")]
    done = counted(lambda: len(__import__("select").select([s.fd for s in sources], [], [], 0)[0]) >= need)
elif kind == "readable":
    source = waits.Readable(int(arg))
    sources = [source]
    done = counted(lambda: len(source.data) >= need)
elif kind == "path":
    a, b = arg.split(",")
    sources = [waits.PathAppears(a), waits.PathAppears(b)]
    done = counted(lambda: os.path.exists(a) and os.path.exists(b))
elif kind == "deep":
    sources = [waits.PathAppears(arg)]
    done = counted(lambda: os.path.exists(arg))
elif kind == "store":
    import sqlite3
    source = waits.Store(arg)
    sources = [source]
    original = source._writer_done
    def measured():
        before = switches()
        original()
        lock_switches[0] += switches() - before
    source._writer_done = measured
    done = counted(lambda: sqlite3.connect(arg).execute("select count(*) from t").fetchone()[0] >= need)
elif kind == "cgroup":
    groups = arg.split(",")
    sources = [waits.CgroupEmpty(g) for g in groups]
    done = counted(lambda: all(waits.cgroup_populated(g) is not True for g in groups))
result = waits.wait("no-idle-wake " + kind, done, sources=sources)
print(json.dumps({"outcome": result.outcome, "readings": readings, "lock_switches": lock_switches[0]}))
'''

_v358_WORK = b"v358" * (1 << 18)  # one MiB, hashed a fixed number of times before each event


def _v358_work():
    import hashlib as _h
    digest = _h.sha256()
    for _ in range(384):
        digest.update(_v358_WORK)
    return digest.hexdigest()


def _v358_own_cgroup():
    with open("/proc/self/cgroup") as f:
        line = f.read().strip().split("::", 1)[1]
    return _v358_Path("/sys/fs/cgroup") / line.lstrip("/")


class _v358_Latched:
    """A child that ends when its stdin is closed: this row's own latch, independent of the holder module
    another row tests, so a defect there cannot hold this row."""

    def __init__(self):
        self.proc = _v358_subprocess.Popen([_v358_sys.executable, "-c", "import sys; sys.stdin.buffer.read()"],
                                           stdin=_v358_subprocess.PIPE)
        self.pid = self.proc.pid

    def release(self):
        self.proc.stdin.close()


def _v358_no_idle_wake():
    """{source: facts}: each waiter held across the events this test causes, with the switches it made."""
    results = {}
    with _v358_tempfile.TemporaryDirectory(prefix="v358-wake-") as d:
        d = _v358_Path(d)
        support = d / "support"
        support.mkdir()
        _v358_shutil.copyfile(str(_v358_WAITS), str(support / "waits.py"))
        script = d / "waiter.py"
        script.write_text(_v358_WAITER)

        def drive(kind, arg, need, events, pass_fds=()):
            token_r, token_w = _v358_os.pipe()
            waiter = _v358_subprocess.Popen(
                [_v358_sys.executable, str(script), str(support), kind, arg, str(token_w), str(need)],
                pass_fds=(token_w,) + tuple(pass_fds), stdout=_v358_subprocess.PIPE, text=True)
            _v358_os.close(token_w)
            for event in events:
                _v358_os.read(token_r, 1)  # the reading before this event has been made
                _v358_work()
                event()
            out, _ = waiter.communicate()
            _v358_os.close(token_r)
            try:
                record = _v358_json.loads(out.strip().splitlines()[-1])
            except (ValueError, IndexError):
                return {"error": out}
            readings = record["readings"]
            waiting = sum(readings[i + 1][0] - readings[i][1] for i in range(len(readings) - 1))
            return {"outcome": record["outcome"], "events": len(events),
                    "switches": waiting - record["lock_switches"], "lock_switches": record["lock_switches"],
                    "in_readings": sum(b - a for a, b in readings), "readings": len(readings)}

        # A process exit, twice: two holders released one after the other.
        pair = [_v358_Latched(), _v358_Latched()]
        results["pidfd"] = drive("pidfd", "%d,%d" % (pair[0].pid, pair[1].pid), 2,
                                 [pair[0].release, pair[1].release])
        for h in pair:
            h.proc.wait()
        # A readable descriptor, twice: two writes to a pipe.
        pr, pw = _v358_os.pipe()
        results["readable"] = drive("readable", str(pr), 2,
                                    [lambda: _v358_os.write(pw, b"a"), lambda: _v358_os.write(pw, b"b")],
                                    pass_fds=(pr,))
        _v358_os.close(pr)
        _v358_os.close(pw)
        # A path appearing, twice: two entries made in a watched directory (each one creation event).
        a, b = d / "paths" / "a", d / "paths" / "b"
        (d / "paths").mkdir()
        results["path"] = drive("path", "%s,%s" % (a, b), 0, [a.mkdir, b.mkdir])
        # A directory made two levels deep after the wait began, then the path in it: three events.
        (d / "deep").mkdir()
        deep = d / "deep" / "one" / "two" / "end"
        results["deep"] = drive("deep", str(deep), 0, [
            (d / "deep" / "one").mkdir, (d / "deep" / "one" / "two").mkdir, deep.mkdir])
        # A store, twice: two commits by a writer that keeps its connection.
        import sqlite3 as _sq
        db = d / "store.db"
        writer = _sq.connect(str(db))
        writer.execute("pragma journal_mode=wal")
        writer.execute("create table t(x)")
        writer.commit()

        def commit():
            writer.execute("insert into t values (1)")
            writer.commit()
        results["store"] = drive("store", str(db), 2, [commit, commit])
        writer.close()
        # A cgroup becoming empty, twice: two child cgroups, each holding one holder, released in turn.
        try:
            own = _v358_own_cgroup()
            groups = []
            members = []
            for i in range(2):
                g = own / ("v358-wake-%d-%d" % (_v358_os.getpid(), i))
                g.mkdir()
                groups.append(g)
                h = _v358_Latched()
                (g / "cgroup.procs").write_text(str(h.pid))
                members.append(h)
            results["cgroup"] = drive("cgroup", ",".join(str(g) for g in groups), 0,
                                      [members[0].release, members[1].release])
            for h in members:
                h.proc.wait()
            for g in groups:
                g.rmdir()
        except OSError as error:
            results["cgroup"] = {"error": "a child cgroup could not be made here: %s" % error}
    return results


_v358_f2 = _v358_no_idle_wake()
expect("waits/no-idle-wake: %r" % (_v358_f2,),
       set(_v358_f2) == {"pidfd", "readable", "path", "deep", "store", "cgroup"}
       and all(f.get("outcome") == "done" and 0 <= f["switches"] <= f["events"] for f in _v358_f2.values()))


# ---------------------------------------------------------------------------------- AC3: latch holder

_v358_TEST_PROCESS = r'''import os, sys
sys.path.insert(0, sys.argv[1])
import holders
h = holders.Holder()
print("%d %d" % (h.pid, h.inode), flush=True)
os.read(0, 1)  # held by its own test (the suite) until it is killed
'''


def _v358_exited(pidfd):
    return bool(_v358_select.select([pidfd], [], [], 0)[0])


def _v358_holders():
    holders_mod = _v358_load("v358_holders_under_test", _v358_HOLDERS)
    waits_mod = holders_mod.waits
    facts = {}
    released = holders_mod.Holder()
    facts["alive_before_release"] = released.proc.poll() is None
    with released:
        released.release()
        end = released.ended("the released holder to end")
        facts["released"] = {"outcome": end.outcome, "exit": released.proc.poll(),
                             "terminal": end.terminal_observation}
    with _v358_tempfile.TemporaryDirectory(prefix="v358-holder-") as d:
        support = _v358_Path(d) / "support"
        support.mkdir()
        for path in (_v358_WAITS, _v358_HOLDERS):
            _v358_shutil.copyfile(str(path), str(support / _v358_os.path.basename(str(path))))
        script = _v358_Path(d) / "test_process.py"
        script.write_text(_v358_TEST_PROCESS)
        test = _v358_subprocess.Popen([_v358_sys.executable, str(script), str(support)],
                                      stdin=_v358_subprocess.PIPE, stdout=_v358_subprocess.PIPE, text=True)
        pid, inode = (int(x) for x in test.stdout.readline().split())
        pidfd = _v358_os.pidfd_open(pid)
        test.kill()
        test.wait()
        test.stdin.close()
        test.stdout.close()
        end = waits_mod.wait("the holder of a killed test process to end",
                             lambda: _v358_exited(pidfd),
                             terminal=lambda: (bool(holders_mod._write_ends(pid, inode)),
                                               {"holder_write_ends": holders_mod._write_ends(pid, inode)}),
                             sources=[waits_mod.Pidfd(pid)])
        _v358_os.close(pidfd)
        facts["orphaned"] = {"outcome": end.outcome, "terminal": end.terminal_observation}
        if end.outcome != "done":
            _v358_os.kill(pid, _v358_signal.SIGKILL)
    import ast as _ast
    me = _ast.parse(suite_file().read_text())
    facts["sleeps_in_this_suite"] = sorted({n.lineno for n in _ast.walk(me) if isinstance(n, _ast.Call)
                                            and isinstance(n.func, _ast.Attribute) and n.func.attr == "sleep"})
    return facts


_v358_f3 = _v358_holders()
expect("holders/ends-with-its-test: %r" % (_v358_f3,),
       _v358_f3["alive_before_release"]
       and _v358_f3["released"]["outcome"] == "done" and _v358_f3["released"]["exit"] == 0
       and _v358_f3["orphaned"]["outcome"] == "done"
       and _v358_f3["sleeps_in_this_suite"] == [])


# ------------------------------------------------------------------------------------- AC4: residue

_v358_RESIDUE = {
    "fx_thread": '''import os, threading
_r, _w = os.pipe()
threading.Thread(target=os.read, args=(_r, 1), name="v358-leftover-thread", daemon=True).start()
expect("fx/thread-suite", True)
''',
    "fx_child": '''_left_holder = HOLDERS.Holder()
expect("fx/child-suite", True)
''',
    "fx_listener": '''import socket
_left_listener = socket.socket()
_left_listener.bind(("127.0.0.1", 0))
_left_listener.listen()
expect("fx/listener-suite", True)
''',
    "fx_clean": '''import threading
_t = threading.Thread(target=lambda: None)
_t.start()
_t.join()
with HOLDERS.Holder() as _h:
    _h.release()
    _h_end = _h.ended()
expect("fx/clean-suite", _h_end.done)
''',
}


def _v358_residue():
    with _v358_tempfile.TemporaryDirectory(prefix="v358-residue-") as d:
        base = _v358_tree(_v358_Path(d) / "repo", _v358_RESIDUE)
        run = _v358_run(base, list(_v358_RESIDUE))
        rows = {}
        for line in run.stdout.splitlines():
            if line.startswith("  SELFTEST FAIL: residue/"):
                name, _, detail = line.split("residue/", 1)[1].partition(": ")
                rows[name] = detail
        return {"failed": rows, "rc": run.returncode,
                "passed_line": _v358_lines(run.stdout, "selftest (PARTIAL")}


_v358_f4 = _v358_residue()
_v358_f4r = _v358_f4["failed"]
expect("residue/named: %r" % (_v358_f4,),
       sorted(_v358_f4r) == ["fx_child", "fx_listener", "fx_thread"]
       and "thread 'v358-leftover-thread' alive" in _v358_f4r["fx_thread"]
       and _v358_f4r["fx_child"].startswith("child ") and "running" in _v358_f4r["fx_child"]
       and _v358_f4r["fx_listener"].startswith("listening socket tcp ")
       and "fx_clean" not in _v358_f4r
       and _v358_f4["rc"] != 0)


# ---------------------------------------------------------------------------- AC5: progress watchdog

_v358_BLOCKS = '''import os
WAITS.arm_watchdog(bound=3)
_r, _w = os.pipe()
expect("fx/before-block", True)
os.read(_r, 1)
expect("fx/after-block", True)
'''

_v358_LEG = {
    "fx_leg_one": '''V358_CLOCK = WAITS.SuppliedClock()
WAITS.arm_watchdog(bound=3, clock=V358_CLOCK)
for _i in range(3):
    V358_CLOCK.advance(1)
    expect("fx/leg-one-%d" % _i, True)
''',
    "fx_leg_two": '''for _i in range(3):
    V358_CLOCK.advance(1)
    expect("fx/leg-two-%d" % _i, True)
''',
    "fx_leg_three": '''for _i in range(3):
    V358_CLOCK.advance(1)
    expect("fx/leg-three-%d" % _i, True)
print("FX LEG CLOCK %s" % V358_CLOCK(), flush=True)
''',
}


def _v358_watchdog():
    facts = {}
    with _v358_tempfile.TemporaryDirectory(prefix="v358-watchdog-") as d:
        hang_dir = _v358_Path(d) / "hang"
        hang_dir.mkdir()
        base = _v358_tree(_v358_Path(d) / "blocks", {"fx_blocks": _v358_BLOCKS})
        run = _v358_run(base, ["fx_blocks"], VELDO_HANG_DIR=str(hang_dir))
        source = base / "scripts" / "suites" / "fx_blocks.py"
        line = 1 + source.read_text().splitlines().index("os.read(_r, 1)")
        stacks = [p.read_text() for p in hang_dir.iterdir()]
        hung = _v358_lines(run.stdout, "SELFTEST HUNG")
        facts["blocking"] = {
            "rc": run.returncode, "hung": hung,
            "reported_hung": len(hung) == 1 and hung[0].startswith("SELFTEST HUNG fx/after-block:")
            and "wait progress-watchdog at %s:%d" % (source, line) in hung[0],
            "stack_names_read": bool(stacks) and 'File "%s", line %d' % (source, line) in stacks[0],
            "stderr_stack": 'File "%s", line %d' % (source, line) in run.stderr,
            "not_run": _v358_lines(run.stdout, "SELFTEST NOT RUN")}
        base = _v358_tree(_v358_Path(d) / "leg", _v358_LEG)
        run = _v358_run(base, list(_v358_LEG))
        facts["leg"] = {"rc": run.returncode, "hung": _v358_lines(run.stdout, "SELFTEST HUNG"),
                        "clock": _v358_lines(run.stdout, "FX LEG CLOCK"),
                        "fails": _v358_lines(run.stdout, "  SELFTEST FAIL"),
                        "rows": _v358_suite_counts(run.stdout)}
    return facts


_v358_f5 = _v358_watchdog()
expect("watchdog/progress-not-total: %r" % (_v358_f5,),
       _v358_f5["blocking"]["rc"] != 0
       and _v358_f5["blocking"]["reported_hung"]
       and _v358_f5["blocking"]["stack_names_read"]
       and _v358_f5["blocking"]["stderr_stack"]
       and _v358_f5["blocking"]["not_run"] == []
       and _v358_f5["leg"]["rc"] == _v358_PASSED and _v358_f5["leg"]["hung"] == []
       and _v358_f5["leg"]["fails"] == []
       and _v358_f5["leg"]["clock"] == ["FX LEG CLOCK 9.0"]
       and _v358_f5["leg"]["rows"] == {"fx_leg_one": 3, "fx_leg_two": 3, "fx_leg_three": 3})


# ------------------------------------------------------------------------ the opened-files claims
# The dispatcher writes NO record (the authority takes it: scripts/gate_legs.py TakeOpened, suite 160). Handed
# an append descriptor in VELDO_OPENED_LEDGER_FD, it claims there what each suite opened; without one it
# claims nothing anywhere, whatever an old variable names; and no process a suite starts sees the descriptor.

_v358_OPENS = {
    "fx_opens": '''_name = "v358" + "_computed"
exec(compile((ROOT / "scripts" / "suites" / (_name + ".txt")).read_text(), "computed", "exec"))
expect("fx/opened", V358_COMPUTED == 1)
''',
    "fx_quiet": '''import os as _fx_os, subprocess as _fx_sp, sys as _fx_sys
_fx_code = ("import os\\n"
            "links = []\\n"
            "for f in os.listdir('/proc/self/fd'):\\n"
            "    try:\\n"
            "        links.append(os.path.basename(os.readlink('/proc/self/fd/' + f)))\\n"
            "    except OSError:\\n"
            "        pass\\n"
            "print(sorted(k for k in os.environ if 'OPENED' in k), 'ledger' in links)\\n")
_fx_child = _fx_sp.run([_fx_sys.executable, "-c", _fx_code], capture_output=True, text=True)
print("FX CHILD " + _fx_child.stdout.strip())
expect("fx/quiet", "VELDO_OPENED_LEDGER_FD" not in _fx_os.environ)
''',
}


def _v358_record():
    import os as _o
    with _v358_tempfile.TemporaryDirectory(prefix="v358-record-") as d:
        base = _v358_tree(_v358_Path(d) / "repo", _v358_OPENS)
        (base / "scripts" / "suites" / "v358_computed.txt").write_text("V358_COMPUTED = 1\n")
        ledger = _v358_Path(d) / "ledger"
        fd = _o.open(str(ledger), _o.O_WRONLY | _o.O_CREAT | _o.O_APPEND | _o.O_CLOEXEC, 0o600)
        argv = [_v358_sys.executable, str(base / "scripts" / "selftest.py"), "--suite", "fx_opens", "--suite", "fx_quiet"]
        try:
            run = _v358_subprocess.run(argv, cwd=str(base), capture_output=True, text=True, stdin=_v358_subprocess.DEVNULL,
                                       env=_v358_clean_env(VELDO_OPENED_LEDGER_FD=str(fd)), pass_fds=(fd,))
        finally:
            _o.close(fd)
        claims = {}
        try:
            for line in ledger.read_text().splitlines():
                item = _v358_json.loads(line)
                claims.setdefault(item["suite"], []).extend(item["paths"])
        except (OSError, ValueError, KeyError) as error:
            claims = {"error": str(error)}
        child = [l for l in run.stdout.splitlines() if l.startswith("FX CHILD ")]
        # The old writer's variable, with no descriptor: nothing is written there or anywhere.
        old = _v358_Path(d) / "old-record.json"
        quiet = _v358_run(base, list(_v358_OPENS), VELDO_OPENED_FILES=str(old))
        return {"rc": run.returncode, "claims": claims, "child": child,
                "old_rc": quiet.returncode, "old_written": old.exists() or _v358_Path(str(old) + ".lock").exists(),
                "old_stderr": quiet.stderr[-400:]}


_v358_f6 = _v358_record()
expect("record/opened-files: %r" % (_v358_f6,),
       _v358_f6["rc"] == _v358_PASSED
       and _v358_f6["claims"].get("fx_opens") == ["scripts/suites/fx_opens.py", "scripts/suites/v358_computed.txt"]
       and _v358_f6["claims"].get("fx_quiet") == ["scripts/suites/fx_quiet.py"]
       and "scripts/suites/support/waits.py" in _v358_f6["claims"].get("shared", [])
       and not any("__pycache__" in p for paths in _v358_f6["claims"].values() for p in paths)
       and _v358_f6["child"] == ["FX CHILD [] False"]
       and _v358_f6["old_rc"] == _v358_PASSED and not _v358_f6["old_written"])


# ------------------------------------------------------------------------- the port holder (C11)

def _v358_port():
    ports_mod = _v358_load("v358_ports_under_test", _v358_PORTS)
    import socket as _socket
    hold = ports_mod.reserve()
    taken = []
    for _ in range(64):
        s = _socket.socket()
        s.bind(("127.0.0.1", 0))
        taken.append(s)
    collided = any(s.getsockname()[1] == hold.port for s in taken)
    for s in taken:
        s.close()
    server = _socket.socket()
    server.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", hold.port))
    server.listen()
    hold.release()
    bound = server.getsockname()[1] == hold.port
    server.close()
    return {"collided": collided, "server_bound": bound}


_v358_f7 = _v358_port()
expect("ports/held-until-bound: %r" % (_v358_f7,), _v358_f7 == {"collided": False, "server_bound": True})


# ------------------------------------------------- wave 1: a cgroup that is gone, however the kernel says it

def _v358_cgroup_gone():
    """A cgroup removed before the open answers ENOENT; one removed between the open and the read answers
    ENODEV (the kernel's own answer here, made by removing the group once its events file is open). Both
    are the same fact for every caller: populated is None, the source is gone and is not polled, and a
    wait for the group to be empty is done at its first reading."""
    w = _v358_load("v358_waits_gone", _v358_WAITS)
    facts = {}

    def tried(read):
        try:
            return read()
        except OSError as error:
            return "raised errno %d" % error.errno

    try:
        own = _v358_own_cgroup()

        def group(tag):
            g = own / ("v358-gone-%d-%s" % (_v358_os.getpid(), tag))
            g.mkdir()
            return g

        opened = w._cgroup_events

        def removed_once_open(cgroup):
            fd = opened(cgroup)
            _v358_os.rmdir(str(cgroup))
            return fd

        g = group("kernel")
        fd = opened(g)
        g.rmdir()
        facts["kernel_read"] = tried(lambda: _v358_os.read(fd, 16))
        _v358_os.close(fd)
        w._cgroup_events = removed_once_open
        try:
            facts["populated"] = tried(lambda: w.cgroup_populated(group("populated")))
            g = group("source")
            source = tried(lambda: w.CgroupEmpty(g))
            facts["source"] = source if isinstance(source, str) else (source.gone, source.fileno())
            g = group("wait")
            source = tried(lambda: w.CgroupEmpty(g))
        finally:
            w._cgroup_events = opened
        facts["wait"] = source if isinstance(source, str) else tried(lambda: w.wait(
            "a removed group to be empty", lambda: w.cgroup_populated(g) is not True, sources=[source]).outcome)
        g = group("watched")
        source = w.CgroupEmpty(g)
        g.rmdir()
        facts["watched"] = tried(lambda: (source.fired(), source.gone))
        source.close()
        never = own / ("v358-gone-%d-never" % _v358_os.getpid())
        facts["absent"] = tried(lambda: (w.cgroup_populated(never), w.CgroupEmpty(never).gone))
        # Any other error stays an error: a path under a file is not a cgroup that went away.
        facts["other"] = tried(lambda: w.cgroup_populated("/proc/self/stat"))
    except OSError as error:
        facts["error"] = "a child cgroup could not be made here: %s" % error
    return facts


_v358_f8 = _v358_cgroup_gone()
expect("waits/cgroup-gone-is-empty: %r" % (_v358_f8,),
       _v358_f8 == {"kernel_read": "raised errno 19", "populated": None, "source": (True, None), "wait": "done",
                    "watched": (False, True), "absent": (None, True), "other": "raised errno 20"})


# ------------------------------------------- wave 1: a run that does not finish leaves no process behind

_v358_HOLD = '''import os, subprocess, sys
fifo, d, name, how = sys.argv[1:5]
if how == "orphan":
    if os.fork():
        os._exit(0)
    os.setsid()
elif how == "parent":
    subprocess.Popen([sys.executable, __file__, fifo, d, "below", "none"], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)
with open(os.path.join(d, name + ".tmp"), "w") as f:
    f.write(str(os.getpid()))
os.rename(os.path.join(d, name + ".tmp"), os.path.join(d, name))
open(fifo).read()  # held until a writer has opened the latch and closed it; this run's suite never does
'''

_v358_TREE = '''import os, subprocess, sys
import waits
_d = os.environ["V358_DIR"]
def _hold(name, how):
    # A holder keeps none of this run's output open: the test reads that output to its end.
    return subprocess.Popen([sys.executable, os.path.join(_d, "hold.py"), os.path.join(_d, "latch"), _d, name, how],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
_direct = _hold("direct", "none")
_parent = _hold("parent", "parent")
_hold("orphan", "orphan").wait()
_go = os.path.join(_d, "go")
_seen = waits.wait("the test to hold every holder", lambda: os.path.exists(_go), sources=[waits.PathAppears(_go)])
expect("fx/holders-held", _seen.done)
if os.environ.get("V358_HANGS"):
    waits.wait("an end nobody makes", lambda: False, sources=[waits.Pidfd(_direct)], row="fx/hung",
               hang_bound_for_test=2)
expect("fx/hung", True)
'''

_v358_HELD = ("direct", "parent", "below", "orphan")


def _v358_tree_of(hangs):
    """One run of the fixture suite: four holders it never releases (a child, a child with a child below it,
    and a process in a session of its own whose parent ended at once). The test opens each one's pidfd
    while it is held, lets the suite go on, and reads after the dispatcher ended whether each was reaped."""
    import signal as _signal
    with _v358_tempfile.TemporaryDirectory(prefix="v358-tree-") as d:
        base = _v358_tree(_v358_Path(d) / "repo", {"fx_tree": _v358_TREE})
        work = _v358_Path(d) / "work"
        work.mkdir()
        (work / "hold.py").write_text(_v358_HOLD)
        latch = work / "latch"
        _v358_os.mkfifo(str(latch))
        hang_dir = _v358_Path(d) / "hang"
        hang_dir.mkdir()
        env = {"V358_DIR": str(work), "VELDO_HANG_DIR": str(hang_dir)}
        if hangs:
            env["V358_HANGS"] = "1"
        run = _v358_subprocess.Popen(
            [_v358_sys.executable, str(base / "scripts" / "selftest.py"), "--suite", "fx_tree"], cwd=str(base),
            stdout=_v358_subprocess.PIPE, stderr=_v358_subprocess.PIPE, text=True,
            stdin=_v358_subprocess.DEVNULL, env=_v358_clean_env(**env))
        started = WAITS.wait("the fixture's holders to state their pids",
                             lambda: all((work / name).exists() for name in _v358_HELD),
                             terminal=lambda: run.poll() is not None,
                             sources=[WAITS.PathAppears(work / name) for name in _v358_HELD] + [WAITS.Pidfd(run)])
        if not started.done:
            out, err = run.communicate()
            return {"error": "the fixture ended before its holders started", "stdout": out, "stderr": err[-2000:]}
        pids = {name: int((work / name).read_text()) for name in _v358_HELD}
        held = {name: _v358_os.pidfd_open(pid) for name, pid in pids.items()}  # each is held: none has ended
        (work / "go").write_text("")
        out, err = run.communicate()

        def reaped(fd):
            try:
                _signal.pidfd_send_signal(fd, 0)
            except ProcessLookupError:
                return True
            return False

        facts = {"rc": run.returncode, "hung": [line.split(":", 1)[0] for line in _v358_lines(out, "SELFTEST HUNG")],
                 "reaped": sorted(name for name, fd in held.items() if reaped(fd)),
                 "named": sorted(name for name, pid in pids.items()
                                 if any("child %d (" % pid in line
                                        for line in _v358_lines(out, "SELFTEST TREE ended and reaped"))),
                 "said": len(_v358_lines(out, "SELFTEST TREE: the run ended without finishing; 4 process(es)"))}
        # Release whatever is still held (all of them after an orderly end), and see each one end.
        try:
            _v358_os.close(_v358_os.open(str(latch), _v358_os.O_WRONLY | _v358_os.O_NONBLOCK))
        except OSError:
            pass  # no reader is left
        for fd in held.values():
            _v358_select.select([fd], [], [])
            _v358_os.close(fd)
        return facts


_v358_f9 = {"hung": _v358_tree_of(True), "orderly": _v358_tree_of(False)}
expect("watchdog/hung-tree-ended: %r" % (_v358_f9,),
       _v358_f9["hung"] == {"rc": 1, "hung": ["SELFTEST HUNG fx/hung"], "reaped": sorted(_v358_HELD),
                            "named": sorted(_v358_HELD), "said": 1}
       and _v358_f9["orderly"].get("rc") not in (None, 0) and _v358_f9["orderly"]["hung"] == []
       and _v358_f9["orderly"]["reaped"] == [] and _v358_f9["orderly"]["named"] == []
       and _v358_f9["orderly"]["said"] == 0)
