#!/usr/bin/env python3
"""Contract-system self-test: the unit suite of this repository.

THIS FILE HOLDS NO ASSERTION OF ITS OWN. It is a dispatcher over scripts/suites/manifest.json.
The invocation, the aggregate summary line and the exit semantics are UNCHANGED from the
monolith it replaced, which is what keeps the decomposition out of the protected set:
scripts/verify.sh is byte-identical and every run record still parses the same line.

WHY THE SUITES SHARE ONE NAMESPACE, stated here because it is the load-bearing decision and it
was reached by measurement rather than by taste. The monolith carried cross-region dependencies
through MUTATED OBJECTS and through the FILESYSTEM, not only through names: two were driven out
of a candidate split, one a directory made inside a temporary tree another region created, one a
dict a later region fills that an earlier one reads through a defensive `or` fallback which turns
the missing input into a silent None instead of a NameError. No mechanical analysis this
repository has finds that class, so no membership rule for a set of independent modules can be
PROVEN closed. Executing the fragments in ONE namespace in the ORIGINAL ORDER needs no such rule:
every statement sees exactly what it saw in the monolith, so the decomposition cannot change what
any assertion proves, and that is asserted by label identity rather than argued here.

What the split buys is the thing it was for: N files instead of one, so two lanes editing
different suites do not collide, plus the selectors below.

  python3 scripts/selftest.py                 the whole suite; the only thing that means green
  python3 scripts/selftest.py --suite NAME    one suite plus its measured prerequisite closure
  python3 scripts/selftest.py --upto NAME     everything up to and including one suite
  python3 scripts/selftest.py --list          the manifest order, with each closure's size

A FLAG TAKES ITS VALUE AS THE NEXT WORD, AND AN UNRECOGNISED FLAG IS A REFUSAL. `--suite=NAME`
is not `--suite`, and until this was corrected it was recognised by nothing, so the equals form
of either selector fell through to a FULL run at exit 0 with the aggregate line printed. Every
argument beginning with `--` is now checked against the table below, and one that is not in it
exits 2 as UNRECOGNISED_FLAG. Measured in review 1: the safe direction, since a real full run
happened, but a person chasing a fast loop paid the whole suite and read a green line as theirs.

--suite IS NOT --upto AND THE DIFFERENCE IS MEASURED. --upto runs the whole PREFIX. --suite runs
the named suite plus its measured prerequisite CLOSURE (scripts/suites/requires.json), which for
11 of the 13 fragments present when this was written is a strict subset of the prefix. Recorded in
proof/WARP-0717/inner-loop-measurement.json: fragment 05 costs 0.04s against the prefix's MODELLED
21.35s, and fragment 13 costs 46.85s against a modelled 93.45s because its closure excludes
fragment 12, which is 46.37s of the whole run on its own. THE PREFIX FIGURES THERE ARE MODELLED,
summed from per-fragment times measured inside one full run; the measured wall-clock timings of
these commands as a person pays them are in proof/WARP-0717/timings.txt, where `--suite 05` is
0.07s against a MEASURED `--upto 05` of 21.84s. It is NOT uniformly fast: two fragments carry most
of the cost, so iterating on fragment 12 still pays about 59s.

NO SELECTOR CAN COUNT AS A GATE PASS, and that is structural rather than advisory. Every run gets
a RunScope (scripts/run_scope.py). A scope built from a selector RAISES PARTIAL_RUN_CANNOT_VERIFY
when asked for the aggregate summary line, the verify stamp or a passed unit-evidence record, and
its exit code is never 0. Selecting a name the manifest does not enumerate is a REFUSAL that names
what is available, never a silent zero-assertion pass.
"""
import os
import sys

# What this process was started with and where, before anything it runs can change either: the
# process an isolated suite runs in (VELDO-0206) is started with exactly these.
_ENVIRONMENT, _DIRECTORY = dict(os.environ), os.getcwd()

# NO FILE IN scripts/ OR scripts/suites/ CAN SHADOW THE STANDARD LIBRARY HERE (VELDO-0208). The
# gate runs this file as `python3 scripts/selftest.py`, which puts scripts/ first on sys.path, so an
# unprotected scripts/json.py would run inside this protected dispatcher before it reads its leg,
# and a suites/tempfile.py inside shared.py. os and sys are loaded before any script runs, so they
# are the interpreter's; the script directory is dropped before the next import, and the two
# repository directories go back AFTER the standard library, never ahead of it.
_SCRIPTS = os.path.dirname(os.path.realpath(__file__))
sys.path[:] = [p for p in sys.path if os.path.realpath(p or os.curdir) != _SCRIPTS]


def _after_stdlib(*paths):
    """Insert paths just after the standard library's entries on sys.path (at the end when none
    is found), so a repository module never shadows one of the standard library's."""
    std = os.path.dirname(os.path.realpath(os.__file__))
    at = [i + 1 for i, p in enumerate(sys.path) if "-packages" not in p
          and (os.path.realpath(p) == std or os.path.realpath(p).startswith(std + os.sep))]
    at = max(at) if at else len(sys.path)
    sys.path[at:at] = paths


import importlib.util  # noqa: E402 - only after the script directory is gone
import json  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
SUITES = HERE / "suites"
_after_stdlib(str(HERE), str(SUITES))


# NOR CAN ANY FILE STAND IN FOR A PROTECTED MODULE THIS DISPATCHER IMPORTS (VELDO-0208). Behind the
# standard library, scripts/ and scripts/suites/ still race each other for a name: an unprotected
# scripts/shared.py came ahead of the protected suites/shared.py and was the namespace both legs ran
# in. So the two protected modules are loaded from their fixed paths and registered under the names
# the suites and shared.py import them by, and a later `import run_scope` finds the protected one.
def _protected(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RS = _protected("run_scope", HERE / "run_scope.py")  # what a run of this suite is allowed to claim

MANIFEST = json.loads((SUITES / "manifest.json").read_text())
FRAGMENTS = RS.fragments(MANIFEST)
ORDER = [s["name"] for s in FRAGMENTS]

ON_DISK = sorted(p.name for p in SUITES.glob("*.py"))
DECLARED = sorted([MANIFEST["shared"]] + [s["file"] for s in FRAGMENTS])
if ON_DISK != DECLARED:
    print("selftest: SUITE_NOT_ENUMERATED: on disk %s, manifest %s"
          % (sorted(set(ON_DISK) - set(DECLARED)), sorted(set(DECLARED) - set(ON_DISK))))
    sys.exit(2)


# THE ONE DECLARED SET OF ARGUMENTS THIS DISPATCHER RECOGNISES, name to the number of
# words each consumes after itself. It exists as a TABLE because review 1 measured what
# testing each flag with a separate `in sys.argv` costs: `--suite=05_...` is not the string
# `--suite`, so the equals form was recognised by nothing, fell through every selector test,
# and RAN THE WHOLE SUITE AT EXIT 0 while printing the aggregate line. That fails in the safe
# direction, because a genuine full run happened and the line it printed was true, but
# someone chasing a fast inner loop silently paid the entire suite and read a green line as
# their subset's. So an argument beginning with `--` that is not in this table is a REFUSAL.
FLAGS = {"--list": 0, "--suite": 1, "--upto": 1}
UNRECOGNISED_FLAG = "UNRECOGNISED_FLAG"


def _parse_argv(argv):
    """(values per flag, flags seen in order, unrecognised arguments), in ONE pass.

    A flag's VALUE is taken POSITIONALLY, so a value may be any word at all, and a flag
    with nothing following it yields the empty string rather than an IndexError: `--suite`
    alone then refuses down the same unknown-NAME path as `--suite ''` instead of crashing,
    and a crash prints no verdict line at all, which reads like a run that found nothing
    wrong. Every other token beginning with `--` lands in the unrecognised list, which is
    what closes the equals form for BOTH selectors at once rather than one spelling at a
    time. A bare word that is not a flag's value is left alone and ignored, exactly as
    before, because refusing those is a separate question this item did not measure.
    """
    values = {f: [] for f in FLAGS}
    seen, unknown, i = [], [], 0
    while i < len(argv):
        a = argv[i]
        if a in FLAGS:
            seen.append(a)
            if FLAGS[a]:
                values[a].append(argv[i + 1] if i + 1 < len(argv) else "")
            i += 1 + FLAGS[a]
            continue
        if a.startswith("--"):
            unknown.append(a)
        i += 1
    return values, seen, unknown


VALUES, SEEN, UNKNOWN_ARGS = _parse_argv(sys.argv[1:])
if UNKNOWN_ARGS:
    print("selftest: %s: %s. This dispatcher recognises exactly %s, and a flag takes its "
          "value as the NEXT WORD, so `--suite=NAME` is not `--suite`. Refusing rather than "
          "ignoring it, because an ignored selector runs the WHOLE suite and exits 0, which "
          "reads in a log as a green fast run."
          % (UNRECOGNISED_FLAG, ", ".join(repr(a) for a in UNKNOWN_ARGS),
             ", ".join(sorted(FLAGS))))
    sys.exit(2)

if "--list" in SEEN:
    try:
        REQ = RS.load_requires()
    except (OSError, ValueError, KeyError):
        REQ = {}
    for s in FRAGMENTS:
        print("%-44s %-44s closure %d" % (s["name"], s["file"], len(REQ.get(s["name"]) or [])))
    sys.exit(0)

SUITE_VALUES = VALUES["--suite"]
UPTO_VALUES = VALUES["--upto"]
if SUITE_VALUES and UPTO_VALUES:
    print("selftest: AMBIGUOUS_SELECTOR: --suite and --upto together do not name one run; "
          "give one or the other")
    sys.exit(2)

ENV_ORDER = os.environ.get("VELDO_SUITE_ORDER")
RUN = list(FRAGMENTS)
if ENV_ORDER:
    named = [n for n in ENV_ORDER.split(",") if n]
    unknown = [n for n in named if n not in ORDER]
    if unknown:
        print("selftest: VELDO_SUITE_ORDER names unknown suites: %s" % unknown)
        sys.exit(2)
    byname = {s["name"]: s for s in FRAGMENTS}
    RUN = [byname[n] for n in named] + [s for s in FRAGMENTS if s["name"] not in named]

SELECTOR = None
if UPTO_VALUES:
    UPTO = UPTO_VALUES[-1]
    if UPTO not in ORDER:
        print("selftest: unknown suite %r (see --list)" % UPTO)
        sys.exit(2)
    RUN = RUN[:[s["name"] for s in RUN].index(UPTO) + 1]
    SELECTOR = "--upto %s" % UPTO
elif SUITE_VALUES:
    try:
        ASKED, WANTED = RS.resolve(SUITE_VALUES, manifest=MANIFEST)
    except (RS.UnknownSuite, RS.ClosureUnavailable) as e:
        print("selftest: %s" % e)
        sys.exit(2)
    RUN = [s for s in RUN if s["name"] in WANTED]
    SELECTOR = "--suite %s" % " ".join(ASKED)

# SUITE RESULT REUSE (VELDO-0206). The gate's authority may hand the unit stage's dispatcher a
# plan: the qualified suites, each of which runs in a process of its own, and of those the ones
# for which the authority holds an authenticated passing record under exactly their present
# inputs. This dispatcher opens no store and computes no key. With a plan it starts one process
# per isolated suite BEFORE any suite has run here, so nothing a suite of the shared namespace
# leaves behind (names, modules, environment, working directory, process state) can reach one;
# that process runs the suite's prerequisite closure in manifest order and nothing else. A suite
# the plan lets it leave out is not run at all. It honors a plan only as the full manifest in
# manifest order, at the plan's own root, outside the unconfined leg and writing to the unit
# stage's own output. It says, on its own lines, what it ran, where, and what it left out, so the
# authority can account for every suite. Without a plan it runs as it always has.
REUSE, REUSED, ISOLATED, CHILD = None, [], [], None
try:
    REUSE = RS.reuse_plan(os.environ)
    _ENVIRONMENT.pop(RS.REUSE_VARIABLE, None)
except RS.ReuseRefused as e:
    _ENVIRONMENT.pop(RS.REUSE_VARIABLE, None)
    print("selftest reuse: %s; every suite runs fresh" % e, flush=True)
if REUSE and REUSE["child"] is not None:
    # THE PROCESS OF ONE ISOLATED SUITE: the suite and its prerequisite closure, in manifest order.
    CHILD = REUSE["child"]
    if SELECTOR is not None or ENV_ORDER or CHILD not in ORDER:
        print("selftest isolated: %r with a selector or an order is not a run this dispatcher starts" % CHILD)
        sys.exit(2)
    try:
        _closure = RS.resolve([CHILD], manifest=MANIFEST)[1]
    except (RS.UnknownSuite, RS.ClosureUnavailable) as e:
        print("selftest isolated: %s" % e)
        sys.exit(2)
    RUN = [s for s in RUN if s["name"] in _closure]  # the whole prerequisite closure runs here
    SELECTOR = "isolated %s" % CHILD

# THE GATE'S LEG (VELDO-0208, owner decision 2026-10-07), set only by the authority's
# scripts/gate_legs.py: the confined leg runs every suite but the ones the authority listed whole,
# the unconfined leg only the listed ones. A suite listed for some rows runs in both, and its rows
# ask run_scope.leg_runs which leg owns them. Both legs say so first, with the list, so a leg is
# never mistaken for the whole suite. Leg variables that are not the complete set gate_legs.py sets
# are refused, and a leg that runs no suite or no row is refused after it, never a pass.
try:
    LEG, LISTED = RS.gate_leg(os.environ)
except RS.LegRefused as e:
    print("selftest: %s" % e)
    sys.exit(2)
if LEG:
    _whole = [n for n, rows in LISTED.items() if rows is None]
    _rows = ["%s:%s" % (n, rows) for n, rows in LISTED.items() if rows is not None]
    _absent = sorted(n for n in LISTED if n not in ORDER)
    if LEG == "confined":
        RUN = [s for s in RUN if s["name"] not in _whole]
        _what = "skips the %d suite(s) and runs all but the rows the unconfined leg owns" % len(_whole)
    else:
        RUN = [s for s in RUN if s["name"] in LISTED]
        _what = "runs only the %d listed suite(s) present, and of a row-scoped one only its rows" % len(RUN)
    if CHILD is None:
        print("selftest leg %s: %s. Whole: %s. Rows: %s.%s Declaration: %s."
              % (LEG, _what, ", ".join(_whole) or "none", ", ".join(_rows) or "none",
                 " Not in this manifest: %s." % ", ".join(_absent) if _absent else "",
                 os.environ[RS.GATE_DECLARATION]), flush=True)
    if not RUN:
        print("selftest leg %s: LEG_RAN_NOTHING: no suite of this manifest is in the %s leg; "
              "refusing rather than reporting a pass for a leg that tested nothing" % (LEG, LEG))
        sys.exit(2)

SCOPE = RS.RunScope(SELECTOR, [s["name"] for s in RUN], ORDER)
if CHILD is not None:
    print("selftest isolated %s: a process of its own, running the %d suite(s) of its prerequisite "
          "closure and nothing else" % (CHILD, len(RUN)), flush=True)
elif SCOPE.partial:
    print(SCOPE.banner(), flush=True)

if REUSE and CHILD is None:
    _isolated, _reusable, _why = RS.reuse_honored(REUSE, HERE.parent, SELECTOR, ENV_ORDER, LEG, LISTED, ORDER,
                                                  RS.output_identity(sys.stdout))
    if _why:
        print("selftest reuse: %s; every suite runs fresh" % _why, flush=True)
    if _isolated:
        try:
            _closures = RS.load_requires()
        except (OSError, ValueError, KeyError):
            _closures = {}
        _, ISOLATED, REUSED = RS.reuse_execution([s["name"] for s in RUN], _closures, _isolated, _reusable)


def _account(kind, **payload):
    """One whole line in one write, so no other process's output can land inside it."""
    if REUSE:
        sys.stdout.flush()
        os.write(sys.stdout.fileno(), RS.reuse_line(
            REUSE["nonce"], kind, leg=LEG, isolated=CHILD,
            scope="isolated" if CHILD is not None else "partial" if SCOPE.partial else "full",
            **payload).encode())


def _isolate(name):
    """Run one isolated suite in its own process and return (rows it passed, rows that failed there).

    The process is started with what this dispatcher was started with, not with what it has
    become, and it writes to this dispatcher's output. Its counts come back in a file of this
    run; this waits for the process to exit and for nothing else. A process that reports nothing
    counts as one failed row."""
    import subprocess
    import tempfile
    _fd, _report = tempfile.mkstemp(prefix="veldo-suite-")
    os.close(_fd)
    try:
        sys.stdout.flush()
        _code = subprocess.call(
            [sys.executable, *subprocess._args_from_interpreter_flags(), str(HERE / "selftest.py")],
            cwd=_DIRECTORY, env=dict(_ENVIRONMENT, **{RS.REUSE_VARIABLE: RS.reuse_child(REUSE, name, _report)}))
        try:
            _counts = json.loads(Path(_report).read_text())
            if (_counts.get("suite") != name or type(_counts.get("passed")) is not int
                    or type(_counts.get("failed")) is not int or _counts["passed"] < 0 or _counts["failed"] < 0):
                raise ValueError("malformed")
        except (OSError, ValueError, AttributeError):
            print("  SELFTEST FAIL: %s: its isolated process exited %s and reported no result" % (name, _code),
                  flush=True)
            return 0, 1
        if _code != 0 and not _counts["failed"]:
            print("  SELFTEST FAIL: %s: its isolated process exited %s" % (name, _code), flush=True)
            return _counts["passed"], 1
        return _counts["passed"], _counts["failed"]
    finally:
        try:
            os.unlink(_report)
        except OSError:
            pass


_account("begin", suites=len(RUN))

# ISOLATED SUITES RUN FIRST, before the shared namespace exists in this process.
_ISOLATED_ROWS = [0, 0]
for _s in RUN:
    if _s["name"] in REUSED:
        # Not executed: the authority holds this suite's passing record under its present inputs.
        # Its rows are NOT added to this run's count; the line says what was left out.
        _account("result", suite=_s["name"], source="reused", passed=REUSE["reuse"][_s["name"]], failed=0)
    elif _s["name"] in ISOLATED:
        _p, _f = _isolate(_s["name"])
        _ISOLATED_ROWS = [_ISOLATED_ROWS[0] + _p, _ISOLATED_ROWS[1] + _f]

shared = _protected("shared", SUITES / "shared.py")  # the shared namespace every fragment runs in

# THE ONE SCOPE FOR THIS RUN, handed to the module that owns the counters and the summary
# line. shared.report() emits THROUGH it, so a partial run reaching the aggregate line
# raises instead of printing one. Nothing else constructs a scope on this path.
shared.SCOPE = SCOPE

T0 = time.monotonic()
PER_SUITE = []
_LEG_FLOOR = shared.PASS + shared.FAIL
_OWN = (0, 0)
for _s in RUN:
    if _s["name"] in REUSED or _s["name"] in ISOLATED:
        continue  # left out on its record, or already run in its own process
    _p = SUITES / _s["file"]
    # A fragment's own path, bound before it runs. Its `__file__` is shared.py's, because that
    # is the namespace it executes in, so an assertion whose SUBJECT is its own file needs this.
    shared.__dict__["__suite_file__"] = str(_p)
    _before, _failed, _t = shared.PASS, shared.FAIL, time.monotonic()
    exec(compile(_p.read_text(), str(_p), "exec"), shared.__dict__)
    PER_SUITE.append((_s["name"], shared.PASS - _before, time.monotonic() - _t))
    _account("result", suite=_s["name"], source="fresh", passed=shared.PASS - _before,
             failed=shared.FAIL - _failed)
    if _s["name"] == CHILD:
        _OWN = (shared.PASS - _before, shared.FAIL - _failed)

# The rows the isolated suites asserted in their own processes are this run's rows.
shared.PASS, shared.FAIL = shared.PASS + _ISOLATED_ROWS[0], shared.FAIL + _ISOLATED_ROWS[1]
if CHILD is not None:
    # One isolated suite's process: its own passed rows, and every row that failed here, since a
    # prerequisite that fails here leaves no passing observation of the suite. Never the aggregate.
    print("selftest isolated %s: %d passed, %d failed (%d passed row(s) of its prerequisites are "
          "theirs, not counted)" % (CHILD, _OWN[0], shared.FAIL, shared.PASS - _OWN[0]), flush=True)
    _code = 1 if shared.FAIL else 0
    Path(REUSE["report"]).write_text(json.dumps({"suite": CHILD, "passed": _OWN[0], "failed": shared.FAIL}))
    _account("end", exit=_code, passed=_OWN[0], failed=shared.FAIL)
    sys.exit(_code)

if LEG and shared.PASS + shared.FAIL == _LEG_FLOOR and not REUSED:
    print("selftest leg %s: LEG_RAN_NOTHING: the %d suite(s) of this leg asserted no row; "
          "refusing rather than reporting a pass for a leg that tested nothing" % (LEG, len(RUN)))
    sys.exit(2)

if SCOPE.partial:
    # Per-suite counts and times, so a reader sees WHERE the run went and what the SELECTED
    # suite proved on its own, not only the union.
    for _name, _passed, _el in PER_SUITE:
        print("  %-44s %5d passed  %6.2fs" % (_name, _passed, _el))
    print(SCOPE.partial_line(shared.PASS, shared.FAIL, time.monotonic() - T0))
    print(SCOPE.footer())
    _account("end", exit=SCOPE.exit_code(shared.FAIL), passed=shared.PASS, failed=shared.FAIL)
    sys.exit(SCOPE.exit_code(shared.FAIL))
if REUSED:
    # A reused suite is never described as run: the aggregate line below counts only the rows this
    # run asserted, and a fresh failure is red whatever was left out.
    print("selftest reuse: %d of %d suites left out on authenticated passing records (%d rows not "
          "run again); %d ran fresh" % (len(REUSED), len(RUN), sum(REUSE["reuse"][n] for n in REUSED),
                                        len(RUN) - len(REUSED)), flush=True)
if ISOLATED:
    print("selftest reuse: %d suite(s) ran fresh, each in a process of its own" % len(ISOLATED), flush=True)
_CODE = shared.report()
_account("end", exit=_CODE, passed=shared.PASS, failed=shared.FAIL)
sys.exit(_CODE)
