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
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITES = HERE / "suites"
sys.path.insert(0, str(SUITES))
sys.path.insert(0, str(HERE))

import run_scope as RS  # noqa: E402 - what a run of this suite is allowed to claim

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

SCOPE = RS.RunScope(SELECTOR, [s["name"] for s in RUN], ORDER)
if SCOPE.partial:
    print(SCOPE.banner(), flush=True)

import shared  # noqa: E402 - the shared namespace every fragment runs in

# THE ONE SCOPE FOR THIS RUN, handed to the module that owns the counters and the summary
# line. shared.report() emits THROUGH it, so a partial run reaching the aggregate line
# raises instead of printing one. Nothing else constructs a scope on this path.
shared.SCOPE = SCOPE

T0 = time.monotonic()
PER_SUITE = []
for _s in RUN:
    _p = SUITES / _s["file"]
    # A fragment's own path, bound before it runs. Its `__file__` is shared.py's, because that
    # is the namespace it executes in, so an assertion whose SUBJECT is its own file needs this.
    shared.__dict__["__suite_file__"] = str(_p)
    _before, _t = shared.PASS, time.monotonic()
    exec(compile(_p.read_text(), str(_p), "exec"), shared.__dict__)
    PER_SUITE.append((_s["name"], shared.PASS - _before, time.monotonic() - _t))

if SCOPE.partial:
    # Per-suite counts and times, so a reader sees WHERE the run went and what the SELECTED
    # suite proved on its own, not only the union.
    for _name, _passed, _el in PER_SUITE:
        print("  %-44s %5d passed  %6.2fs" % (_name, _passed, _el))
    print(SCOPE.partial_line(shared.PASS, shared.FAIL, time.monotonic() - T0))
    print(SCOPE.footer())
    sys.exit(SCOPE.exit_code(shared.FAIL))
sys.exit(shared.report())
