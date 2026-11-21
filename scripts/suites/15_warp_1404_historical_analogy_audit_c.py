"""WARP-1404 AC5 AUDIT, cases [12:] of the audit table: part C of three.

SPLIT FROM 15_warp_1404_historical_analogy BY VELDO-0221 (fix round 1, lead decision 2026-11-21).
That suite took 634 seconds alone, of which 545 were its twenty audit cases, about 27 seconds
each: as one shard of a gate leg it was the floor of the whole leg's time. Each case has two rows
of its own (the injected defect makes AC5 red with its event recorded; restored is green) and
needs nothing of the other rows, so the cases are cut into three suites: the first four stay in
15_warp_1404_historical_analogy, eight are here and eight in the other part. NO ROW CHANGED: the
loop below is that suite's loop over a slice of the same table, and everything above it is the
part of that suite's own preparation the loop reads, copied byte for byte. The three files hold
the one table, and suite 157 (suite-shards/long-suite-split) requires the three tables equal and
the three slices to cover it exactly once. What each statement is for is explained where it was
written, in 15_warp_1404_historical_analogy.
"""
import shutil as _w1404_shutil

# The audit-hook driver, run as a FRESH PROCESS over this repository's module. It asks CPython what
# the module actually did rather than asking the source what it says: `sys.addaudithook` sees every
# write-mode open by any spelling, every mkdir, rename and unlink, every process spawn and every
# socket, at any depth and under any alias. The hook records into a list and refuses nothing, so
# this measures and never gates. `watching` gates the hook to the drive window only, so loading the
# module and reading the payload are not mistaken for the module's own behaviour.
#
# THE DRIVE IS IN TWO WINDOWS, and the reason is a fact this measurement found rather than a
# convenience: the PURE surface (the layer, the refusals, the rendering, augment through W2's seam)
# must produce NO event of any kind, while `repo_basis` legitimately delegates to WARP-1401's corpus
# reader, which shells out to git per spec to read what a change touched. So the pure window is
# required to be EMPTY, and the repo window is required to write nothing and to spawn NOTHING BUT
# `git log` and `git show`, asserted as a set equality on the argv rather than as a tolerance.
_W1404_NO_WRITER_DRIVER = r'''
import ast, importlib.util, io as _io, json, os, sys
from contextlib import redirect_stdout as _redirect

# CPython cache writes are not module side effects. Disable them before installing the hook:
# a cold, read-only checkout must be measured identically to a checkout with warm .pyc files.
# Keep every audited write, spawn and socket event (including failed attempts) observable.
sys.dont_write_bytecode = True

ROOT = sys.argv[1]
payload = json.loads(sys.stdin.read())
pure, repo_writes, repo_spawn = [], [], set()
watching = [None]
WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC
SPAWN = ("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.fork",
         "os.forkpty", "pty.spawn", "os.startfile", "webbrowser.open")
# Names checked against https://docs.python.org/3.12/library/audit_events.html.
# os.replace emits os.rename; os.lchown emits os.chown. Neither API name is an event.
WRITES = ("os.mkdir", "os.rmdir", "os.remove", "os.rename", "os.link",
          "os.symlink", "os.truncate", "os.chmod", "os.chown", "os.chflags", "os.utime",
          "os.setxattr", "os.removexattr", "os.putenv", "os.unsetenv",
          "os.kill", "os.killpg", "tempfile.mkstemp", "shutil.copyfile", "shutil.copymode",
          "shutil.copystat", "shutil.move", "shutil.rmtree", "shutil.chown",
          "shutil.make_archive", "shutil.unpack_archive", "socket.__new__",
          "socket.connect", "socket.bind", "socket.sendto", "socket.sendmsg",
          "socket.getaddrinfo", "socket.sethostname", "urllib.Request",
          "ctypes.dlopen", "ctypes.dlsym", "ctypes.dlsym/handle",
          "ctypes.call_function", "ctypes.cdata",
          "ftplib.connect", "smtplib.connect", "sqlite3.connect", "signal.pthread_kill")


def hook(event, args):
    where = watching[0]
    if where is None:
        return
    seen = None
    if event == "open":
        mode = args[1] if len(args) > 1 else None
        flags = args[2] if len(args) > 2 else 0
        if mode is not None and any(c in str(mode) for c in "wax+"):
            seen = "open %s mode %s" % (args[0], mode)
        elif mode is None and isinstance(flags, int) and flags & WRITE_FLAGS:
            seen = "os.open %s flags %d" % (args[0], flags)
    elif (event == "import" and args and isinstance(args[0], str)
          and args[0].split(".", 1)[0] in ("ctypes", "_ctypes")):
        # A raw-address _ctypes function pointer can run without a ctypes.* event.
        # Treat access to either module family as strict in EVERY active window.
        seen = "import " + args[0]
    elif event in WRITES:
        seen = event
    elif event in SPAWN:
        argv = args[1] if len(args) > 1 and isinstance(args[1], (list, tuple)) else args[:1]
        seen = " ".join(str(a) for a in list(argv)[:2])
        if where in ("repo", "cli"):
            # The CLI's report path delegates to the same corpus reader repo_basis uses, so its
            # spawns are the same read-only git argvs and face the same allowlist. An import-time
            # spawn is never legitimate and falls through to the strict bucket below.
            repo_spawn.add(seen)
            return
    if seen is None:
        return
    (pure if where == "pure" else repo_writes).append(seen)


sys.addaudithook(hook)
# THE IMPORT IS A WINDOW TOO. The hook was installed here and the module was then imported with
# watching[0] still None, so a writer at import time was invisible: a review inserted one beside
# UNWINDOWED and it wrote 9 bytes into the repository while the fragment stayed fully green. Module
# scope runs exactly once and is the easiest place to hide a side effect, so it is watched first.
watching[0] = "import"
_spec = importlib.util.spec_from_file_location(
    "w1404_driven", os.path.join(ROOT, ".veldo", "toe_analogy.py"))
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)
watching[0] = None

# THE IMPORT SURFACE, from the parsed AST rather than from a search for forbidden spellings, and
# reported as a set for the caller to assert an EQUALITY over. `import os as _o`, `from shutil
# import copy` and a dotted `import urllib.request` all appear here under their top-level name.
_tree = ast.parse(open(os.path.join(ROOT, ".veldo", "toe_analogy.py")).read())
imports, named_calls = set(), set()
for _node in ast.walk(_tree):
    if isinstance(_node, ast.Import):
        imports.update(_a.name.split(".")[0] for _a in _node.names)
    elif isinstance(_node, ast.ImportFrom):
        imports.add((_node.module or "").split(".")[0])
    elif isinstance(_node, ast.Call) and isinstance(_node.func, ast.Name):
        named_calls.add(_node.func.id)

corpus, vec = payload["corpus"], A.vector(payload["features"])
reports, drives, repo_records = [], 0, 0
watching[0] = "pure"
try:
    for _c, _v in ((corpus, vec), (corpus, None), ([], vec),
                   (payload["nospend"], vec), (corpus[:2], vec)):
        _layer, _report = A.analogy(payload["target"], _v, _c)
        A.render_lines(_report)
        reports.append(_report)
        drives += 1
    A.augment(payload["spec"], payload["at"], corpus)
    drives += 1
    watching[0] = "repo"
    _basis = A.repo_basis()
    A.analogy("WARP-1404", vec, _basis[0], era_of=_basis[1], era=_basis[2])
    repo_records = len(_basis[0])
    drives += 1
    watching[0] = "cli"
    # THE ARGV MUST BE THE REAL ONE. Written first as ["report", spec], which argparse rejects
    # because the flag is --spec, so the window opened, raised at the parser, and measured nothing:
    # a vacuous window is worse than no window, and it is the defect this whole suite hunts. The
    # report path is REQUIRED to be reached, which the assertion checks through cli_reported rather
    # than trusting this call not to have exited early.
    # Its report goes to stdout, which is this driver's JSON channel, so it is captured rather than
    # left to interleave. Found by running the driver by hand: the mixed stream was a JSON decode
    # error in the caller, not a failing assertion, which is the confusing kind of red.
    cli_reported = False
    _cli_out = _io.StringIO()
    try:
        with _redirect(_cli_out):
            A._cli(["report", "--spec", payload["spec"]])
        cli_reported = True
    except SystemExit as _e:
        cli_reported = (getattr(_e, "code", 1) in (0, None))
    drives += 1
finally:
    watching[0] = None
sys.stdout.write(json.dumps({
    "pure": pure, "repo_writes": repo_writes, "repo_spawn": sorted(repo_spawn),
    "cli_reported": cli_reported,
    "drives": drives, "repo_records": repo_records, "imports": sorted(imports),
    "named_calls": sorted(named_calls),
    "predicted": [bool(r.get("predicted")) for r in reports]}))
'''

def _w1404_rec(spec, risk="standard", acs=2, globs=2, protected=False, tokens=None,
               cycles=None, git=None):
    """One veldo.toe_actuals/v1 record in the shape WARP-1401's build produces. Built rather
    than pinned, because every matching assertion below needs two records differing in exactly
    ONE feature, and `tokens=None` is the record shape of a change whose spend was never
    recorded, which is every record in this repository today."""
    return {
        "schema": "veldo.toe_actuals/v1",
        "spec": spec,
        "features": {"spec_id": spec, "status": "shipped", "risk": risk,
                     "acceptance_criteria": acs, "footprint_declared": globs,
                     "protected_touch": protected, "plan": None, "lane": None,
                     "human_approval": None, "depends_on": 0, "spec_bytes": 4096},
        "cycles": cycles or {"gate_passes": 1, "gate_failures": 0, "review_verdicts": 1,
                             "events_seen": 2},
        "spend": {"tokens": tokens or 0, "cost_usd": 0.0, "human_minutes": 0,
                  "spend_recorded": tokens is not None},
        "git": git or {"commits": 1, "files_touched": 3},
    }

def _w1404_spec_text(spec_id="WARP-9404", risk="standard", acs=2, status="ready",
                     footprint=(".veldo/nothing_a.py", ".veldo/nothing_b.py")):
    """A fixture spec carrying exactly the mechanical features under test."""
    lines = ["---", "schema: veldo.spec/v1", "id: %s" % spec_id,
             "title: analogy fixture", "status: %s" % status, "risk: %s" % risk,
             "owner: selftest"]
    if footprint:
        lines.append("placement: [metrics]")
        lines.append("footprint:")
        for f in footprint:
            lines.append('  - "%s"' % f)
    lines.append("acceptance_criteria:")
    for i in range(1, acs + 1):
        lines.append("  - id: AC%d" % i)
        lines.append("    text: observable thing %d happens." % i)
    lines += ["required_evidence: [unit]", "rollback: git revert", "---", "body", ""]
    return "\n".join(lines)

_W1404_AT = "2026-08-10"

_W1404_TARGET = "WARP-9404"

# Two clusters of shipped history: cheap standard-risk changes and expensive critical ones. The
# clusters exist so the anti-vacuity assertion has something to say - a layer that returned one
# constant range would satisfy every refusal in this file and be worthless.
_W1404_CHEAP = [_w1404_rec("WARP-0001", acs=2, globs=2, tokens=300000),
                _w1404_rec("WARP-0002", acs=3, globs=2, tokens=420000),
                _w1404_rec("WARP-0003", acs=2, globs=3, tokens=360000),
                _w1404_rec("WARP-0004", acs=1, globs=1, tokens=250000)]

_W1404_DEAR = [_w1404_rec("WARP-0101", risk="critical", acs=8, globs=12, protected=True,
                          tokens=2400000),
               _w1404_rec("WARP-0102", risk="critical", acs=9, globs=11, protected=True,
                          tokens=3100000),
               _w1404_rec("WARP-0103", risk="critical", acs=8, globs=13, protected=True,
                          tokens=2800000)]

_W1404_NOSPEND = [_w1404_rec("WARP-0201"), _w1404_rec("WARP-0202"), _w1404_rec("WARP-0203")]

_W1404_SEEDED = _W1404_CHEAP + _W1404_DEAR + _W1404_NOSPEND


with tempfile.TemporaryDirectory() as _d:
    # ---------------------------------------------------------------------------------------
    # AC5. ADOPTION SAFE, ADVISORY, AND IT CAN ONLY EVER WIDEN WHAT W2 COMMITTED.
    # ---------------------------------------------------------------------------------------
    _w1404_fix = tmpfile(_d, "WARP-9404-fixture.md", _w1404_spec_text())

    # MEASUREMENT ONE: a fresh interpreter with a CPython audit hook installed, driving the whole
    # surface (five analogy paths, augment through W2's real writer-free seam, and repo_basis over
    # this repository) and reporting every write-mode open, every process spawn and every socket
    # the interpreter saw. A subprocess rather than this process on purpose: an audit hook cannot
    # be removed once added, and a permanent interpreter-wide hook installed by one suite fragment
    # would be a side effect on every fragment after it.
    _w1404_wdir = Path(_d) / "auditcwd"

    _w1404_wdir.mkdir()

    _w1404_payload = json.dumps({
        "corpus": list(_W1404_SEEDED), "nospend": list(_W1404_NOSPEND),
        "features": {"risk": "standard", "acceptance_criteria": 2,
                     "footprint_declared": 2, "protected_touch": False},
        "target": _W1404_TARGET, "spec": str(_w1404_fix), "at": _W1404_AT})

    # MEASUREMENT TWO, reported by the same driver from the parsed AST: what the module IMPORTS, as
    # a set to be asserted by EQUALITY rather than searched for four forbidden spellings. `import os
    # as _o`, `from shutil import copy` and `import urllib.request` all show up in it; a blacklist
    # sees none of them. Both allowlists are declared here, beside the assertion that uses them.
    _W1404_READONLY_GIT = {"git log", "git show"}   # all WARP-1401's corpus reader may spawn

    _W1404_IMPORTS = {"argparse", "importlib", "json", "sys", "pathlib"}

    # Cold-cache regression and falsifiers use the SAME driver and all four windows. Copy only
    # runtime source; link the repository's read-only evidence and git metadata so repo_basis and
    # the CLI still consume the real corpus. Mutations never touch the checkout's product code.
    _w1404_auditroot = Path(_d) / "auditrepo"

    _w1404_auditroot.mkdir()

    for _w1404_entry in ROOT.iterdir():
        if _w1404_entry.name != ".veldo":
            (_w1404_auditroot / _w1404_entry.name).symlink_to(_w1404_entry)

    (_w1404_auditroot / ".veldo").mkdir()

    for _w1404_entry in (ROOT / ".veldo").iterdir():
        _w1404_dest = _w1404_auditroot / ".veldo" / _w1404_entry.name
        if _w1404_entry.suffix == ".py":
            _w1404_shutil.copyfile(_w1404_entry, _w1404_dest)
        elif _w1404_entry.name != "__pycache__":
            _w1404_dest.symlink_to(_w1404_entry)

    _w1404_cache = Path(_d) / "readonly-pycache"

    _w1404_cache.mkdir(mode=0o555)

    _w1404_auditenv = dict(os.environ, PYTHONPYCACHEPREFIX=str(_w1404_cache))

    # The fixture must expose the pre-fix bug even when the outer gate disables bytecode itself.
    _w1404_auditenv.pop("PYTHONDONTWRITEBYTECODE", None)

    def _w1404_audit_trial(case, phase):
        """Require a complete AC5 drive; a missing report cannot be a clean restoration."""
        run = subprocess.run(
            [sys.executable, "-c", _W1404_NO_WRITER_DRIVER, str(_w1404_auditroot)],
            input=_w1404_payload, capture_output=True, text=True,
            cwd=str(_w1404_wdir), env=_w1404_auditenv)
        report = json.loads(run.stdout) if run.stdout.strip() else {}
        complete = (
            run.returncode == 0
            and report.get("drives") == 8
            and report.get("cli_reported") is True
            and report.get("repo_records", 0) > 100
            and report.get("predicted") == [True, False, False, False, False]
            and isinstance(report.get("pure"), list)
            and isinstance(report.get("repo_writes"), list)
            and bool(report.get("repo_spawn"))
            and set(report.get("repo_spawn", [])) <= _W1404_READONLY_GIT
            and set(report.get("imports", [])) == _W1404_IMPORTS
            and not (set(report.get("named_calls", []))
                     & {"open", "__import__", "eval", "exec", "compile", "input", "breakpoint"}))
        print("WARP-1404 AC5 AUDIT REPORT " + json.dumps({
            "case": case, "phase": phase, "complete": complete,
            "ac5_green": complete and report.get("pure") == []
            and report.get("repo_writes") == [],
            "report": report, "stderr": run.stderr[-400:]}))
        return complete, report.get("pure", []) + report.get("repo_writes", [])

    # Mutate a dependency at module scope, as in the independent review. This leaves the
    # toe_analogy AST allowlist satisfied, so only the actual audit event can reject it.
    # All paths are scratch files. Failed OS attempts still emit events and must be caught.
    (_w1404_wdir / "audit-target").write_text("timestamp, ownership and xattr target")

    (_w1404_wdir / "archive-input").mkdir()

    (_w1404_wdir / "archive-input" / "member.txt").write_text("archive member")

    _w1404_shutil.make_archive(str(_w1404_wdir / "archive-source"), "zip",
                              str(_w1404_wdir / "archive-input"))

    # chflags is unavailable on Linux. Exercise its documented event explicitly there;
    # never label that fallback as a native syscall test or silently skip the row.
    _w1404_chflags_native = hasattr(os, "chflags")

    _w1404_cases = (
        ("os.utime", "os.utime", "_ao.utime('audit-target', ns=(1000000000, 2000000000))"),
        ("os.chflags" + (" native" if _w1404_chflags_native else " synthetic (unavailable)"),
         "os.chflags", "_ao.chflags('audit-target', 0)" if _w1404_chflags_native else
         "_asys.audit('os.chflags', 'audit-target', 0)"),
        ("os.lchown", "os.chown", "_ao.lchown('audit-target', -1, -1)"),
        ("os.setxattr", "os.setxattr", "_ao.setxattr('audit-target', 'user.w1404', b'caught')"),
        ("os.removexattr", "os.removexattr", "_ao.removexattr('audit-target', 'user.w1404')"),
        ("shutil.make_archive", "shutil.make_archive",
         "_ash.make_archive('archive-made', 'zip', 'archive-input')"),
        ("shutil.unpack_archive", "shutil.unpack_archive",
         "_ash.unpack_archive('archive-source.zip', 'archive-output', 'zip')"),
        ("socket.__new__", "socket.__new__", "_aso.socket().close()"),
        ("socket.sendto", "socket.sendto",
         "_s = _aso.socket(type=_aso.SOCK_DGRAM)\n_s.close()\n"
         "_s.sendto(b'caught', ('127.0.0.1', 9))"),
        ("socket.sendmsg", "socket.sendmsg",
         "_s = _aso.socket(type=_aso.SOCK_DGRAM)\n_s.close()\n"
         "_s.sendmsg([b'caught'], [], 0, ('127.0.0.1', 9))"),
        ("os.replace", "os.rename", "_ao.replace('audit-target', 'audit-replaced')"),
        ("os.truncate", "os.truncate", "_ao.truncate('audit-replaced', 0)"),
        # Invalid signal and oversized hostname fail even with elevated privileges.
        # Require failure as well as the audit event; neither may change the machine.
        ("os.killpg", "os.killpg", "_ao.killpg(_ao.getpgrp(), -1)\n"
         "raise AssertionError('invalid signal unexpectedly accepted')"),
        ("socket.sethostname", "socket.sethostname", "_aso.sethostname(b'x' * 65536)\n"
         "raise AssertionError('oversized hostname unexpectedly accepted')"),
        # A real libc call in estimate.py bypasses the toe_analogy import allowlist.
        # getpid is harmless and its checked result proves the foreign call ran.
        ("ctypes.dlopen", "ctypes.dlopen", "import ctypes as _act\n"
         "assert _act.CDLL(None).getpid() == _ao.getpid()"),
        # Ordinary CDLL function calls need not emit call_function. Exercise the
        # low-level entry point explicitly and demand its own event, not just dlopen.
        ("ctypes.call_function", "ctypes.call_function",
         "import ctypes as _act, _ctypes as _acraw\n"
         "_libc = _act.CDLL(None)\n"
         "_getpid = _act.cast(_libc.getpid, _act.c_void_p).value\n"
         "assert _acraw.call_function(_getpid, ()) == _ao.getpid()"),
        # Raw-address function pointers need not emit any ctypes.* event. Use only
        # _ctypes and copy zero bytes between valid byte strings: the call is real
        # but changes no memory. The generic import must be sufficient on its own.
        ("_ctypes raw address call", "import _ctypes", "import _ctypes as _acraw\n"
         "class _CharP(_acraw._SimpleCData):\n    _type_ = 'z'\n"
         "class _Size(_acraw._SimpleCData):\n    _type_ = 'L'\n"
         "class _Memmove(_acraw.CFuncPtr):\n"
         "    _flags_ = _acraw.FUNCFLAG_CDECL\n"
         "    _argtypes_ = (_CharP, _CharP, _Size)\n"
         "    _restype_ = None\n"
         "assert _Memmove(_acraw._memmove_addr)(b'', b'', 0) is None"),
        ("ctypes.dlsym", "ctypes.dlsym", "import ctypes as _act\n"
         "assert _act.CDLL(None).getpid() == _ao.getpid()"),
        ("ctypes.dlsym/handle", "ctypes.dlsym/handle",
         "import ctypes as _act, _ctypes as _acraw\n"
         "_libc = _act.CDLL(None)\n"
         "_getpid = _acraw.dlsym(_libc._handle, 'getpid')\n"
         "assert _act.CFUNCTYPE(_act.c_int)(_getpid)() == _ao.getpid()"),
        ("ctypes.cdata", "ctypes.cdata", "import ctypes as _act\n"
         "_owned = _act.c_int(1404)\n"
         "assert _act.c_int.from_address(_act.addressof(_owned)).value == 1404"),
    )

    _w1404_dependency = _w1404_auditroot / ".veldo" / "estimate.py"

    _w1404_dependency_source = _w1404_dependency.read_text()

    try:
        for _w1404_case, _w1404_event, _w1404_call in _w1404_cases[12:]:
            _w1404_injection = (
                "\nimport os as _ao, sys as _asys, shutil as _ash, socket as _aso\ntry:\n"
                + "\n".join("    " + line for line in _w1404_call.splitlines())
                + "\nexcept OSError:\n    pass\n")
            try:
                _w1404_dependency.write_text(_w1404_dependency_source + _w1404_injection)
                _w1404_complete, _w1404_events = _w1404_audit_trial(_w1404_case, "injected")
                expect("WARP-1404 AC5 AUDIT: " + _w1404_case
                       + " makes AC5 red with " + _w1404_event + " recorded",
                       _w1404_complete and _w1404_event in (_w1404_events or [])
                       and (_w1404_case != "_ctypes raw address call"
                            or all(e == "import _ctypes" for e in _w1404_events)))
            finally:
                _w1404_dependency.write_text(_w1404_dependency_source)
            _w1404_complete, _w1404_events = _w1404_audit_trial(_w1404_case, "restored")
            expect("WARP-1404 AC5 AUDIT: " + _w1404_case + " restored is green",
                   _w1404_complete and _w1404_events == [])
    finally:
        _w1404_dependency.write_text(_w1404_dependency_source)
        _w1404_cache.chmod(0o755)

del _w1404_shutil
