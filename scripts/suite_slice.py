#!/usr/bin/env python3
"""Order dependence, DRIVEN: does each region of the monolith still prove what it proves?

DOMAIN. The marker regions of a monolithic assertion suite, under the SAME partition
WARP-0716's survey uses (imported from it rather than re-derived, so the two tools cannot
disagree about what a region is), and the labels each region produces.

PROMISE. For every region in the partition, a DRIVEN answer to one question: run with only
the preamble in front of it, in a fresh interpreter, does it produce exactly the labels it
produces inside the full run? Three outcomes, and each is a reproduction rather than a
reading. CLEAN, the label multiset is identical in both directions. CRASHES_ALONE, it dies,
with the exception and the line quoted. PROVES_DIFFERENTLY, it survives and the labels move.
And for the suite as a whole: run the regions in a deliberately different ORDER and compare
the whole label multiset, because a suite whose result depends on its order has not been
decomposed.

OBSERVATION POINT. suite_labels' recorder, in a fresh subprocess per experiment. The
program a region runs is SELECTED ON THE AST by top-level statement index and compiled with
its original line numbers: the file on disk is never edited, and its sha256 is asserted
unchanged after every run. Attribution of a label to a region is by the MODULE-LEVEL frame
that was executing, not by the call site, so a helper defined in region A and called from
region B counts against B.

COMPLETENESS ARGUMENT. Every region of the partition is run, and the set of regions
attempted is asserted EQUAL AS A SET to the set the survey enumerates, never as a count. In
the other direction, every label of the full run is attributed to exactly one region, and
the union of the per-region label multisets from the alone-runs is compared against the full
run's own multiset in both directions, so a label that no region claims and a label two
regions claim both surface. Nothing here asserts how many regions there are: the suite is
expected to grow.

BLINDNESS, named:
  1. The PREAMBLE is treated as the shared fixture and is present in every alone-run. This
     measures dependence on OTHER REGIONS, not dependence on the preamble. A split must
     carry the preamble into every suite (or into an imported fixture module) and this
     experiment says nothing about whether that is easy.
  2. A region that is CLEAN here can still be reading state the preamble happens to leave
     behind in a way that a later refactor of the preamble would break. Clean means
     independent of other regions, today.
  3. Labels are compared, not conditions. A region asserting the same labels against
     different data alone versus in company is invisible; that is the same hole named in
     suite_labels, and it is why the shared-fixture ownership work of AC3 is not discharged
     by this tool alone.
  4. Regions are run one at a time. A dependency between two regions that BOTH have to be
     absent to matter (region C needs A or B) shows as CRASHES_ALONE for C and would be
     mis-read as a dependency on the nearest one. The reproduction quotes the missing name,
     which is what disambiguates it.
"""
import argparse
import ast
import bisect
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_HERE = Path(__file__).resolve().parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, _HERE / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


L = _load("suite_labels")
SURVEY = _load("suite_survey")

SCHEMA = "veldo.slice/v1"
OUTCOMES = ("CLEAN", "CRASHES_ALONE", "PROVES_DIFFERENTLY", "TIMED_OUT", "REFUSED")
ALONE_TIMEOUT = 900
_EXC = re.compile(r"^(\w+(?:Error|Exception|Exit|Interrupt|Warning))\b", re.M)


_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda,
           ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


def _bound_names(st):
    """Every MODULE-LEVEL name one top-level statement binds. Scope-aware, from the AST.

    Traversal stops at every nested scope, because a name a nested function assigns is that
    function's local and not a module binding. A `global X` declaration inside a nested
    function IS a module binding and is collected, since that is how this suite's assertion
    helper writes its counters.
    """
    out = set()

    def targets(node):
        if isinstance(node, ast.Name):
            out.add(node.id)
        elif isinstance(node, (ast.Tuple, ast.List)):
            for e in node.elts:
                targets(e)
        elif isinstance(node, ast.Starred):
            targets(node.value)

    def globals_in(node):
        for n in ast.walk(node):
            if isinstance(n, ast.Global):
                out.update(n.names)

    def visit(node):
        if isinstance(node, _SCOPES):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                out.add(node.name)
            globals_in(node)
            return
        if isinstance(node, ast.Assign):
            for t in node.targets:
                targets(t)
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            targets(node.target)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            targets(node.target)
        elif isinstance(node, ast.withitem):
            if node.optional_vars is not None:
                targets(node.optional_vars)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                out.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.ExceptHandler) and node.name:
            out.add(node.name)
        elif isinstance(node, ast.NamedExpr):
            targets(node.target)
        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(st)
    return out


class Slicer:
    """The region partition of one monolithic suite, and the programs its regions form."""

    def __init__(self, target=None):
        self.target = Path(target or (ROOT / "scripts" / "selftest.py"))
        self.survey = SURVEY.Survey(str(self.target))
        self.body = self.survey.body
        # statement index -> region id, straight from the survey's own partition
        self.region_of = list(self.survey._region)
        self.marker_lines = [ln for ln, _ in self.survey.markers]
        self.by_region = {}
        for si, rid in enumerate(self.region_of):
            self.by_region.setdefault(rid, []).append(si)

    def region_ids(self):
        """Every region id in the partition. Region 0 is the preamble."""
        return sorted(self.by_region)

    def content_regions(self):
        return [r for r in self.region_ids() if r != 0]

    def label(self, rid):
        return self.survey.region_label(rid)

    def region_for_line(self, lineno):
        return bisect.bisect_right(self.marker_lines, lineno)

    def markers_inside_statements(self):
        """Markers that are NOT candidate suite boundaries, because a top-level statement
        straddles them. A split moves whole statements, so a boundary here is impossible."""
        out = []
        spans = [(st.lineno, getattr(st, "end_lineno", None) or st.lineno, si)
                 for si, st in enumerate(self.body)]
        for rid, ln in enumerate(self.marker_lines, start=1):
            for start, end, si in spans:
                if start < ln <= end:
                    out.append({"marker_region": rid, "marker_line": ln,
                                "statement_lines": [start, end],
                                "statement_region": self.region_of[si]})
                    break
        return out

    def binders(self):
        """module-level name -> the regions that BIND it. Used to resolve a NameError."""
        out = {}
        for si, st in enumerate(self.body):
            rid = self.region_of[si]
            for name in _bound_names(st):
                out.setdefault(name, set()).add(rid)
        return {k: sorted(v) for k, v in out.items()}

    # ---- the programs ----

    def alone_spec(self, rid):
        """Preamble + one region. Nothing else."""
        idx = sorted(self.by_region.get(0, []) + self.by_region.get(rid, []))
        return {"indices": idx, "drop_exit": True, "append_summary": True}

    def permuted_spec(self, order):
        """Preamble first, then the content regions in the order given."""
        idx = list(self.by_region.get(0, []))
        for rid in order:
            idx += self.by_region.get(rid, [])
        return {"indices": idx, "drop_exit": True, "append_summary": True}

    def full_spec(self):
        return {"indices": list(range(len(self.body))), "drop_exit": True,
                "append_summary": True}


# --------------------------------------------------------------------- experiments


def _profile_of(records):
    prof = {}
    for r in records:
        sig = ",".join("%s%+d" % (c, d) for c, d in sorted(r["delta"].items()))
        prof.setdefault(r["label"], Counter())[sig] += 1
    return prof


def _attribute(records, slicer):
    """region id -> the region's own label profile.

    A label is attributed to the TOP-LEVEL STATEMENT that was executing, and that statement
    to its region. Attributing by the executing LINE alone is wrong, and measurably so: a
    `# --- ` marker can sit INSIDE a top-level statement that began before it, so the line
    lands in the next marker region while the statement that emits the label belongs to the
    previous one. That disagreement made a first version of this tool report a region as
    silently proving two assertions less, when the truth was that the two assertions were
    never that region's to prove. Slicing moves STATEMENTS, so attribution follows statements.
    """
    target = str(Path(slicer.target).resolve())
    starts = [st.lineno for st in slicer.body]
    out = {}
    unattributed = []
    for r in records:
        line = None
        for fname, lno in r.get("module_frames") or []:
            if str(Path(fname).resolve()) == target:
                line = lno
        si = None
        if line is not None:
            i = bisect.bisect_right(starts, line) - 1
            if i >= 0:
                end = getattr(slicer.body[i], "end_lineno", None) or slicer.body[i].lineno
                if line <= end:
                    si = i
        if si is None:
            unattributed.append(r["label"])
            continue
        out.setdefault(slicer.region_of[si], []).append(r)
    return {rid: _profile_of(rs) for rid, rs in out.items()}, unattributed


def _run_one(job):
    """One alone-run. Runs in a worker process; returns a plain dict."""
    target, rid, spec, expected = job
    t0 = time.time()
    try:
        cap = L.capture(target, select=spec, tag="r%d" % rid, timeout=ALONE_TIMEOUT)
    except L.LabelRefusal as e:
        return {"region": rid, "outcome": "REFUSED", "refusal": e.code, "detail": e.detail,
                "diff": None}
    except subprocess.TimeoutExpired:
        # A hang is not a pass. It gets its own outcome so it cannot be read as CLEAN.
        return {"region": rid, "outcome": "TIMED_OUT",
                "detail": "no result in %ds" % ALONE_TIMEOUT, "diff": None}
    got = _profile_of(cap.records)
    exp = {lab: Counter(sig) for lab, sig in expected.items()}
    diff = L.compare(exp, got)
    crashed = "Traceback (most recent call last)" in cap.stderr
    exc = _EXC.findall(cap.stderr)
    where = ""
    message = ""
    if crashed:
        lines = [x for x in cap.stderr.strip().splitlines() if x.strip().startswith("File ")]
        where = lines[-1].strip() if lines else ""
        # The exception MESSAGE is the finding: for a NameError it names the symbol that
        # crosses, which is what decides whether the split is hours or days.
        tail = [x for x in cap.stderr.strip().splitlines() if x.strip()]
        message = tail[-1].strip() if tail else ""
    if crashed:
        outcome = "CRASHES_ALONE"
    elif diff["identical"]:
        outcome = "CLEAN"
    else:
        outcome = "PROVES_DIFFERENTLY"
    return {"region": rid, "outcome": outcome, "returncode": cap.returncode,
            "exception": exc[-1] if exc else "", "where": where, "message": message,
            "elapsed_s": round(time.time() - t0, 2),
            "records": len(cap.records),
            "expected_records": sum(sum(c.values()) for c in exp.values()),
            "diff": {k: (v if k in ("identical",) else v[:6]) for k, v in diff.items()},
            "diff_sizes": {k: len(v) for k, v in diff.items() if k != "identical"}}


def _map(jobs, fn, workers, verbose, fmt):
    """Run the cells. workers=0 runs them INLINE, which is what a caller inside the suite
    itself wants: forking a process pool out of a running suite is a cost and a hazard the
    two-region fixtures do not need."""
    out = []
    if workers == 0:
        for job in jobs:
            res = fn(job)
            out.append(res)
            if verbose:
                print(fmt(res), flush=True)
        return out
    with ProcessPoolExecutor(max_workers=workers or min(16, (os.cpu_count() or 4))) as ex:
        for res in ex.map(fn, jobs):
            out.append(res)
            if verbose:
                print(fmt(res), flush=True)
    return out


def run_alone(slicer, full_attr, regions=None, workers=None, verbose=True):
    jobs = []
    # The alone-run carries the PREAMBLE, so the preamble's own assertions are part of what
    # it must reproduce. Expecting only the region's labels would report every run as having
    # grown by the preamble's assertions, which is an artefact of the harness, not a finding.
    pre = full_attr.get(0, {})
    for rid in (regions if regions is not None else slicer.content_regions()):
        expected = {lab: dict(sigs) for lab, sigs in pre.items()}
        for lab, sigs in full_attr.get(rid, {}).items():
            expected.setdefault(lab, {})
            for s, n in sigs.items():
                expected[lab][s] = expected[lab].get(s, 0) + n
        jobs.append((str(slicer.target), rid, slicer.alone_spec(rid), expected))
    out = _map(jobs, _run_one, workers, verbose,
               lambda r: "  region %3d %-19s %s" % (r["region"], r["outcome"],
                                                    r.get("exception") or ""))
    return sorted(out, key=lambda r: r["region"])


_NAME_RE = re.compile(r"name '([^']+)' is not defined")
# The cap on the prerequisite search. It is a BOUND on cost, not a claim about the file: a
# region that hits it has a closure that is a LOWER bound, which the report says of each such
# row rather than leaving the reader to infer it.
CLOSURE_MAX_ROUNDS = 14


def _run_closure(job):
    """The MINIMAL prerequisite set of one region, found by driving it rather than reading.

    Run the region with only the preamble. If it dies on an undefined name, look up the
    regions that BIND that name, add them, and run again. What comes back is the region's
    own dependency closure, the names that had to be resolved to get there, and, when the
    closure is reached, a per-group label-identity result against the full run.
    """
    target, rid, spec_of, binders, expected_of, cap_rounds = job
    need = []
    resolved = []
    unbound = []
    rounds = []
    for _ in range(cap_rounds):
        try:
            cap = L.capture(target, select=spec_of(need), tag="c%d" % rid,
                            timeout=ALONE_TIMEOUT)
            # reconcile() is what turns a traceback into a named refusal. Without it a run
            # that died after N assertions returns a short label set and reads as a deletion.
            cap.reconcile()
        except subprocess.TimeoutExpired:
            return {"region": rid, "outcome": "TIMED_OUT", "closure": sorted(need),
                    "resolved_names": resolved, "unbound_names": unbound, "rounds": rounds}
        except L.LabelRefusal as e:
            if e.code != "SUBJECT_CRASHED":
                return {"region": rid, "outcome": "REFUSED", "refusal": e.code,
                        "detail": e.detail, "closure": sorted(need),
                        "resolved_names": resolved, "unbound_names": unbound,
                        "rounds": rounds}
            m = _NAME_RE.search(e.detail)
            if not m:
                return {"region": rid, "outcome": "CRASHES_NOT_A_NAME", "detail": e.detail,
                        "closure": sorted(need), "resolved_names": resolved,
                        "unbound_names": unbound, "rounds": rounds}
            missing = m.group(1)
            rounds.append(missing)
            owners = [r for r in binders.get(missing, []) if r not in need and r != rid]
            # Prefer the LATEST binder that precedes this region: that is the one whose value
            # the full run actually saw. Pulling every binder of a rebound name would inflate
            # the closure, and pulling a LATER one would hand the region a value the full run
            # never gave it - which the label comparison at the end would then report.
            earlier = [r for r in owners if r < rid]
            if earlier:
                owners = [max(earlier)]
            if not owners:
                unbound.append(missing)
                return {"region": rid, "outcome": "UNRESOLVABLE", "missing": missing,
                        "closure": sorted(need), "resolved_names": resolved,
                        "unbound_names": unbound, "rounds": rounds}
            resolved.append(missing)
            need.extend(owners)
            continue
        # It ran. Does the GROUP prove exactly what those regions prove in the full run?
        got = _profile_of(cap.records)
        exp = {lab: Counter(sig) for lab, sig in expected_of(need).items()}
        diff = L.compare(exp, got)
        return {"region": rid,
                "outcome": "CLOSED" if diff["identical"] else "CLOSED_PROVES_DIFFERENTLY",
                "closure": sorted(need), "resolved_names": resolved,
                "unbound_names": unbound, "rounds": rounds,
                "elapsed_s": None, "records": len(cap.records),
                "diff_sizes": {k: len(v) for k, v in diff.items() if k != "identical"},
                "diff": {k: (v if k == "identical" else v[:4]) for k, v in diff.items()}}
    return {"region": rid, "outcome": "NOT_CONVERGED", "closure": sorted(need),
            "resolved_names": resolved, "unbound_names": unbound, "rounds": rounds,
            "round_cap": cap_rounds}


class _SpecOf:
    """Picklable: preamble + a region + a set of prerequisite regions."""

    def __init__(self, by_region, rid):
        self.by_region = by_region
        self.rid = rid

    def __call__(self, need):
        idx = set(self.by_region.get(0, [])) | set(self.by_region.get(self.rid, []))
        for r in need:
            idx |= set(self.by_region.get(r, []))
        return {"indices": sorted(idx), "drop_exit": True, "append_summary": True}


class _ExpectedOf:
    """Picklable: the full run's label profile for the preamble, a region and its needs."""

    def __init__(self, attr, rid):
        self.attr = attr
        self.rid = rid

    def __call__(self, need):
        out = {}
        for r in [0, self.rid] + list(need):
            for lab, sigs in self.attr.get(r, {}).items():
                d = out.setdefault(lab, {})
                for s, n in sigs.items():
                    d[s] = d.get(s, 0) + n
        return out


def run_closures(slicer, full_attr, regions, workers=None, rounds=None, verbose=True):
    binders = slicer.binders()
    attr = {rid: {lab: dict(sigs) for lab, sigs in prof.items()}
            for rid, prof in full_attr.items()}
    jobs = [(str(slicer.target), rid, _SpecOf(slicer.by_region, rid), binders,
             _ExpectedOf(attr, rid), rounds or CLOSURE_MAX_ROUNDS) for rid in regions]
    out = _map(jobs, _run_closure, workers, verbose,
               lambda r: "  region %3d %-26s needs %-28s resolved %s"
               % (r["region"], r["outcome"], r["closure"], r["resolved_names"]))
    return sorted(out, key=lambda r: r["region"])


def run_permutation(slicer, full_profile, order, name):
    try:
        cap = L.capture(slicer.target, select=slicer.permuted_spec(order), tag=name)
    except L.LabelRefusal as e:
        return {"name": name, "outcome": "REFUSED", "refusal": e.code, "detail": e.detail}
    got = _profile_of(cap.records)
    diff = L.compare(full_profile, got)
    crashed = "Traceback (most recent call last)" in cap.stderr
    exc = _EXC.findall(cap.stderr)
    lines = [x for x in cap.stderr.strip().splitlines() if x.strip().startswith("File ")]
    tail = [x for x in cap.stderr.strip().splitlines() if x.strip()]
    return {"name": name,
            "outcome": ("CRASHES_ALONE" if crashed
                        else "CLEAN" if diff["identical"] else "PROVES_DIFFERENTLY"),
            "exception": exc[-1] if exc else "", "where": lines[-1].strip() if lines else "",
            "message": (tail[-1].strip() if tail and crashed else ""),
            "records": len(cap.records),
            "diff_sizes": {k: len(v) for k, v in diff.items() if k != "identical"},
            "diff": {k: (v if k == "identical" else v[:6]) for k, v in diff.items()}}


# --------------------------------------------------------------------- report


def summarize(slicer, full_cap, alone, perms, unattributed, attr):
    by = Counter(r["outcome"] for r in alone)
    return {
        "schema": SCHEMA,
        "target": str(slicer.target.relative_to(ROOT)) if slicer.target.is_relative_to(ROOT)
        else str(slicer.target),
        "digest": full_cap.digest,
        "lines": len(slicer.survey.src.splitlines()),
        "top_level_statements": len(slicer.body),
        "regions_in_partition": slicer.survey.region_count(),
        "regions_with_statements": slicer.region_ids(),
        "regions_without_statements": sorted(
            set(range(slicer.survey.region_count())) - set(slicer.region_ids())),
        "regions_attempted": sorted(r["region"] for r in alone),
        "markers_inside_statements": slicer.markers_inside_statements(),
        "full_records": len(full_cap.records),
        "full_distinct_labels": len(full_cap.profile()),
        "duplicate_labels": L.duplicates(full_cap.profile()),
        "unattributed_labels": sorted(set(unattributed)),
        "regions_with_no_assertions": sorted(set(slicer.content_regions()) - set(attr)),
        "alone": alone,
        "alone_outcomes": dict(by),
        "permutations": perms,
        # Per-region data the split plan is DERIVED from, recorded here so the plan emitter
        # needs only this file and never the moving target it was measured off.
        "region_labels": {str(rid): sum(sum(c.values()) for c in prof.values())
                          for rid, prof in attr.items()},
        "region_statements": {str(rid): len(sis) for rid, sis in slicer.by_region.items()},
        "region_label_text": {str(rid): slicer.label(rid) for rid in slicer.region_ids()},
        "region_elapsed": {str(a["region"]): a.get("elapsed_s") for a in alone},
    }


REPORT_WRAP = 98
MEASUREMENT_PATH = "proof/WARP-0712/order-dependence.json"
REPORT_PATH = "proof/WARP-0712/order-dependence.md"

_P_GENERATED = """\
THIS DOCUMENT IS GENERATED from the measurement beside it. `python3 scripts/suite_slice.py
--emit-report --from %s` emits it whole, and the gate's CHECK_generated stage
regenerates it and DIFFS, exactly as it does for the specs index and for WARP-0716's survey. A
stale document cannot reach a green gate.

THE MEASUREMENT ITSELF IS NOT REGENERATED BY THE GATE, AND THAT IS A DELIBERATE LIMIT WITH A
REASON. Producing it runs the suite once and then runs one subset per region and per closure
round, which costs minutes rather than milliseconds. Worse, it is a measurement OF
scripts/selftest.py, the one file every work item edits, so a freshness check that pinned its
digest would redden the gate on every single item and leave a minutes-long re-measurement as
the only remedy - which is precisely the trap WARP-0716's first version built and had to
undo. The digest of the measured file is recorded below so a reader can tell what these
figures were read off. Round 2 promised a successor check here, an equivalence run over the
suites once they existed; the suites now exist and that check does not pass over them, so the
promise is deleted rather than restated and this limit stands unmitigated.

ONE CAVEAT THAT OUTRANKS EVERY FIGURE BELOW: THE SUBJECT NO LONGER EXISTS AT THAT PATH. This
measurement was taken over the monolithic unit suite, and WARP-0712 has since cut that monolith
into scripts/suites/, leaving a dispatcher that holds no assertion of its own at the path named
below. Every figure here describes the PRE-SPLIT MONOLITH, which is the point: this is the
measurement the decomposition was derived from and the record of what it had to be derived from.
It is not a description of today's suite, and the digest below is what pins which bytes it read.
"""

_P_METHOD = """\
NOTHING HERE WAS READ OFF THE SOURCE. Each region was RUN. The program a region runs is its
own top-level statements plus the file's preamble, selected on the AST by statement index and
compiled with the original line numbers, in a fresh interpreter, with the assertion primitive
wrapped so every label it emits is recorded. The file on disk is never edited and its sha256
is asserted unchanged after every run. A region that dies is reported with the exception and
the line; a region that survives is compared against the labels the FULL run attributes to it,
by identity in both directions, with multiplicity and with each label's counter delta.
"""

_P_CLOSURE = """\
THE CLOSURE COLUMN IS THE COST OF THE SPLIT, DRIVEN. For a region that will not run alone, the
undefined name is looked up among the regions that BIND it, the latest binder that precedes the
region is added, and the region is run again. What comes back is the prerequisite set that
region actually needs and the names that had to be resolved to get there. The union of those
names is the hoist list: the shared fixtures the decomposition has to lift out before any file
moves.
"""

_P_SILENT = """\
THE SILENT CLASS IS THE ONE THIS ITEM LIVES OR DIES ON. A region whose prerequisite set is
satisfied, which then runs to completion and exits zero, and whose LABEL SET is not the one the
full run attributes to it, has stopped proving what it proved. There are two kinds and they are
not equally dangerous. SILENT: a label MISSING or ADDED, which means an assertion did not run or
ran that should not have, with nothing going red. LOUD: the same labels with a different counter
delta, which means an assertion FAILED, and a failure is a red. Each region below is classified
by which kind its differences are, derived from the differences themselves rather than asserted
in this paragraph, because a paragraph that named a classification its own table contradicted is
the exact defect WARP-0716 shipped at a green gate.
"""

_P_BLIND = """\
BLIND SPOTS, named rather than left to silence.
"""

_BLIND_SPOTS = (
    "The preamble is in every run, so this measures dependence on OTHER REGIONS and not on the"
    " preamble. Whatever the preamble binds is the shared fixture by assumption, and the split"
    " still has to carry it into every suite.",
    "Labels are compared, not asserted values. A region that emits the same labels against"
    " different data alone and in company, both passing, is invisible here.",
    "Order independence is falsified over the orders that were RUN, not proven over all"
    " permutations. The reverse order is the one that breaks a linear chain, which is why it is"
    " one of them.",
    "A region that did not converge inside the round cap has a closure that is a LOWER BOUND:"
    " more prerequisites remain and the cap stopped the search, so its row understates the"
    " work.",
    "The prerequisite search follows undefined NAMES. A dependency carried by a mutated shared"
    " object, an environment variable or a file left on disk does not raise NameError and would"
    " show up here only as a label difference, or not at all.",
)


def _wrap(text, indent=""):
    import textwrap
    out = []
    for para in text.split("\n\n"):
        out.append("\n".join(textwrap.wrap(" ".join(para.split()), REPORT_WRAP,
                                           initial_indent=indent,
                                           subsequent_indent=indent)))
    return "\n\n".join(out)


def _table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def _short(label, n=110):
    s = " ".join(str(label).split())
    return s if len(s) <= n else s[:n - 3] + "..."


def emit_report(rep, source=MEASUREMENT_PATH):
    """The whole document, derived. Every figure below is read out of `rep`."""
    o = []
    o.append("# WARP-0712 order dependence in the unit suite, measured by running it")
    o.append("")
    o.append(_wrap(_P_GENERATED % source))
    o.append("")
    o.append("Measured from: `%s`" % rep["target"])
    o.append("Content digest: sha256 %s" % rep["digest"])
    o.append("Lines: %s. Top-level statements: %s. Marker regions in the partition: %s."
             % (rep["lines"], rep["top_level_statements"], rep["regions_in_partition"]))
    o.append("Regions carrying top-level statements: %s. Regions carrying none: %s."
             % (len(rep["regions_with_statements"]), rep["regions_without_statements"]))
    o.append("Markers a top-level statement STRADDLES, which therefore cannot be suite"
             " boundaries: %s."
             % ([m["marker_region"] for m in rep.get("markers_inside_statements", [])]
                or "none"))
    o.append("Full run: %s assertion records, %s distinct labels, %s label(s) emitted more"
             " than once." % (rep["full_records"], rep["full_distinct_labels"],
                              len(rep["duplicate_labels"])))
    o.append("Attribution round trip identical: %s. Labels attributed to no region: %s."
             % (rep["attribution_round_trip_identical"], len(rep["unattributed_labels"])))
    o.append("")
    o.append("Reproduce: `python3 scripts/suite_slice.py --closure --permute reverse"
             " --permute shuffle:1712 --permute blocks:20 --json %s`" % source)
    o.append("")
    o.append(_wrap(_P_METHOD))
    o.append("")
    o.append("## Does each region prove what it proves, on its own?")
    o.append("")
    by = {}
    for a in rep["alone"]:
        by.setdefault(a["outcome"], []).append(a["region"])
    o.append(_table(["outcome", "regions"],
                    [(k, ", ".join(str(x) for x in sorted(v)))
                     for k, v in sorted(by.items())]))
    o.append("")
    o.append("## Suite order")
    o.append("")
    o.append(_table(["permutation", "outcome", "exception", "first failure"],
                    [(p["name"], p["outcome"], p.get("exception", "") or "-",
                      _short(p.get("message", "") or "-", 70)) for p in rep["permutations"]]))
    o.append("")
    if "closures" in rep:
        o.append(_wrap(_P_CLOSURE))
        o.append("")
        o.append("## The prerequisite closure of every region that would not run alone")
        o.append("")
        o.append(_table(["outcome", "regions"],
                        [(k, ", ".join(str(c["region"]) for c in rep["closures"]
                                       if c["outcome"] == k))
                         for k in sorted(rep["closure_outcomes"])]))
        o.append("")
        o.append(_table(["region", "outcome", "prerequisite regions", "names resolved"],
                        [(c["region"], c["outcome"],
                          ", ".join(str(x) for x in c["closure"]) or "-",
                          ", ".join(c["resolved_names"]) or "-")
                         for c in rep["closures"]]))
        o.append("")
        o.append("## The hoist list: every name a region had to be given before it would run")
        o.append("")
        o.append(_table(["name", "regions that needed it"],
                        [(n, rep["hoist_demand"][n]) for n in rep["hoist_names"]]))
        o.append("")
        o.append("Names read by a region and bound nowhere at module level: %s"
                 % (rep.get("unbound_names") or "none"))
        o.append("")
        silent = [c for c in rep["closures"] if c["outcome"] == "CLOSED_PROVES_DIFFERENTLY"]
        o.append("## The silent class")
        o.append("")
        o.append(_wrap(_P_SILENT))
        o.append("")
        if not silent:
            o.append("No region reached its closure and then proved a different label set.")
        else:
            for c in silent:
                d = c["diff_sizes"]
                kinds = []
                if d.get("missing") or d.get("added"):
                    kinds.append("SILENT")
                if d.get("signature_changed") or d.get("multiplicity_changed"):
                    kinds.append("LOUD")
                o.append("Region %s, %s, prerequisites %s, differences %s"
                         % (c["region"], "+".join(kinds), c["closure"], d))
                o.append("")
                for kind in ("missing", "added"):
                    for lab in c["diff"].get(kind) or []:
                        o.append("- %s: %s" % (kind, _short(lab, 150)))
                for entry in c["diff"].get("signature_changed") or []:
                    o.append("- outcome changed, %s -> %s: %s"
                             % (entry[1], entry[2], _short(entry[0], 150)))
                for entry in c["diff"].get("multiplicity_changed") or []:
                    o.append("- multiplicity %s -> %s: %s"
                             % (entry[1], entry[2], _short(entry[0], 150)))
                o.append("")
            o.append("Regions in the SILENT kind: %s. In the LOUD kind only: %s."
                     % (sorted(c["region"] for c in silent
                               if c["diff_sizes"].get("missing")
                               or c["diff_sizes"].get("added")) or "none",
                        sorted(c["region"] for c in silent
                               if not (c["diff_sizes"].get("missing")
                                       or c["diff_sizes"].get("added"))) or "none"))
            o.append("")
    o.append("## Blind spots")
    o.append("")
    o.append(_wrap(_P_BLIND))
    for i, b in enumerate(_BLIND_SPOTS, 1):
        body = _wrap(b, "   ")
        o.append("%d.%s" % (i, body[len(str(i)) + 1:] if len(str(i)) < 3 else body))
        o.append("")
    return "\n".join(o).rstrip() + "\n"


PLAN_PATH = "proof/WARP-0712/split-plan.md"
# The one judgement in the partition, published next to what it decides exactly as WARP-0716
# publishes its three constants: the assertion budget a single suite file may hold. It trades
# the inner-loop cost of running one suite against the number of files a reader has to hold.
SUITE_ASSERTION_TARGET = 250

_P_PLAN = """\
THIS PLAN IS GENERATED FROM THE MEASUREMENT, not drawn around topic names. `python3
scripts/suite_slice.py --emit-plan --from %s` emits it whole and the gate
regenerates it and DIFFS. The boundaries below come from where data actually stops crossing,
which is the criterion AC1 sets, and the ORDER comes from each region's measured dependency
closure. Nothing in this document is executed by this round: WARP-0712 round 1 builds the
proofs and records the plan, and moves no file.
"""

_P_PLAN_PHASES = """\
PHASE 1 IS THE WHOLE COST AND IT IS NOT OPTIONAL. Every name in the hoist list is a module-level
binding one region creates and another reads, measured by running the reader without the writer
and watching it die. Until they live in one importable fixture module with a declared owner,
every suite that reads one is a suite that only passes in company. The owner column is DERIVED
from the binding, so no ownership is assigned by judgement.

PHASE 2 IS CHEAP ONCE PHASE 1 IS DONE, and it is where the throughput comes from. The
partition below walks the regions in file order and closes a suite when its assertion budget
is reached, and it NEVER closes at a marker a top-level statement straddles, because a split
moves whole statements and those markers are not boundaries at all.

PHASE 3 IS WHATEVER IS NOT SETTLED, LAST AND ON ITS OWN. A region belongs here if its
prerequisite search did not converge inside the round cap, so its closure is a LOWER bound, or
if it DID converge and then proved a different label set than the full run attributes to it.
Either way its independence is not established, and moving it behind the rest keeps the unknown
in one place instead of spread across the partition. The regions that put a suite in phase 3 are
named under the partition, so this paragraph is not the only place a reader learns of them.
"""


def _components(rep):
    """Undirected connected components over the measured prerequisite edges."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    regions = [r for r in rep["regions_with_statements"] if r != 0]
    for r in regions:
        find(r)
    for c in rep.get("closures", []):
        for p in c["closure"]:
            if p != 0:
                union(c["region"], p)
    comps = {}
    for r in regions:
        comps.setdefault(find(r), []).append(r)
    return sorted((sorted(v) for v in comps.values()), key=lambda v: (-len(v), v[0]))


def _partition(rep):
    """Contiguous suites, closed on an assertion budget, never at a straddled marker."""
    straddled = {m["marker_region"] for m in rep.get("markers_inside_statements", [])}
    labels = rep.get("region_labels", {})
    out = []
    cur = []
    load = 0
    for r in [x for x in rep["regions_with_statements"] if x != 0]:
        cur.append(r)
        load += labels.get(str(r), 0)
        if load >= SUITE_ASSERTION_TARGET and (r + 1) not in straddled:
            out.append({"regions": cur, "assertions": load})
            cur, load = [], 0
    if cur:
        out.append({"regions": cur, "assertions": load})
    return out


def _slug(text):
    keep = []
    for ch in text.replace("# ---", " ").strip().lower():
        keep.append(ch if ch.isalnum() else " ")
    words = [w for w in "".join(keep).split() if w not in ("the", "a", "of", "and")]
    return "_".join(words[:4]) or "suite"


def emit_plan(rep, source=MEASUREMENT_PATH):
    o = []
    o.append("# WARP-0712 the decomposition plan, derived from the measurement")
    o.append("")
    o.append(_wrap(_P_PLAN % source))
    o.append("")
    o.append("Measured from: `%s`, content digest sha256 %s" % (rep["target"], rep["digest"]))
    o.append("Assertion budget per suite file: %s. This is a JUDGEMENT, published here next to"
             " what it decides." % SUITE_ASSERTION_TARGET)
    o.append("")
    o.append(_wrap(_P_PLAN_PHASES))
    o.append("")
    o.append("## Phase 1: the shared fixtures to hoist, with their owners")
    o.append("")
    owners = rep.get("hoist_owners", {})
    o.append(_table(["name", "owning region(s)", "regions that needed it"],
                    [(n, ", ".join(str(x) for x in owners.get(n, [])) or "-",
                      rep["hoist_demand"].get(n, 0)) for n in rep.get("hoist_names", [])]))
    o.append("")
    o.append("Names read and bound nowhere at module level: %s"
             % (rep.get("unbound_names") or "none"))
    o.append("")
    o.append("## The measured coupling, before the hoist")
    o.append("")
    comps = _components(rep)
    o.append(_table(["component size", "regions"],
                    [(len(c), ", ".join(str(x) for x in c)) for c in comps]))
    o.append("")
    o.append("## Phase 2: regions to files")
    o.append("")
    nc = {c["region"]: c["outcome"] for c in rep.get("closures", [])
          if c["outcome"] != "CLOSED"}
    rows = []
    part = _partition(rep)
    for i, s in enumerate(part, 1):
        first = s["regions"][0]
        name = "%02d_%s" % (i, _slug(rep.get("region_label_text", {}).get(str(first), "")))
        unsettled = sorted(set(s["regions"]) & set(nc))
        rows.append((name, "%s-%s" % (s["regions"][0], s["regions"][-1]),
                     len(s["regions"]), s["assertions"], 3 if unsettled else 2,
                     ", ".join("%s (%s)" % (r, nc[r]) for r in unsettled) or "-"))
    o.append(_table(["suite file", "regions", "regions held", "assertions", "move in phase",
                     "unsettled regions"],
                    [("scripts/suites/%s.py" % r[0], r[1], r[2], r[3], r[4], r[5])
                     for r in rows]))
    o.append("")
    o.append("Observation point for every suite above: its own `selftest: N passed, M failed`"
             " line and its own assertion-LABEL multiset, compared against the projection of"
             " the full run onto it by scripts/suite_equiv.py. The dispatcher's aggregate line"
             " keeps its exact current format, which is what AC2 holds it to.")
    o.append("")
    o.append("## The order")
    o.append("")
    o.append("1. `scripts/suites/_fixtures.py` and `scripts/suites/manifest.json` first,"
             " carrying the assertion primitive, the counters and every hoisted name above."
             " Nothing else can move before this exists.")
    o.append("2. The phase 2 suites, in the order listed, one commit each, with"
             " `scripts/suite_equiv.py` run after each one and the label identity re-checked"
             " against the recorded baseline after each one.")
    o.append("3. The phase 3 suites last: %s"
             % (", ".join("scripts/suites/%s.py" % r[0] for r in rows if r[4] == 3) or "none"))
    o.append("4. `scripts/selftest.py` reduced to the dispatcher only, which is the point at"
             " which AC2's assertion that it holds no assertion of its own can pass.")
    o.append("")
    o.append("## What this plan does NOT establish")
    o.append("")
    for i, b in enumerate((
        ("That the phase 3 regions are independent: %s. Each either did not converge inside"
         " the round cap, so its closure is a lower bound, or converged and then proved a"
         " different label set."
         % (", ".join("%s (%s)" % (r, o_) for r, o_ in sorted(nc.items()))))
        if nc else
        "Nothing is in phase 3 in this measurement: every region that would not run alone"
        " converged on a prerequisite set and then proved an identical label set. That is a"
        " property of THIS measurement at the digest above and not a standing guarantee.",
        "That hoisting a name is behaviour-preserving. A name bound by a statement with side"
        " effects moves those side effects with it, and only the label identity proof and the"
        " per-suite equivalence run can say whether that mattered.",
        "That the assertion budget is the right one. It is a judgement, and a different budget"
        " changes only how many files the same regions land in.",
    ), 1):
        body = _wrap(b, "   ")
        o.append("%d.%s" % (i, body[len(str(i)) + 1:]))
        o.append("")
    return "\n".join(o).rstrip() + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--emit-plan", action="store_true",
                    help="emit the decomposition plan from a recorded measurement")
    ap.add_argument("--emit-report", action="store_true",
                    help="emit the markdown report from a recorded measurement")
    ap.add_argument("--from", dest="frm", default=MEASUREMENT_PATH)
    ap.add_argument("--target", default=str(ROOT / "scripts" / "selftest.py"))
    ap.add_argument("--regions", help="comma list or A-B range; default every region")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--permute", action="append", default=[],
                    help="reverse | shuffle:SEED | blocks:N")
    ap.add_argument("--closure", action="store_true",
                    help="resolve each crashing region's prerequisite regions by driving it")
    ap.add_argument("--closure-rounds", type=int, default=CLOSURE_MAX_ROUNDS,
                    help="cap on prerequisite resolution rounds per region")
    ap.add_argument("--json", dest="out")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args(argv)

    if args.emit_report or args.emit_plan:
        rep = json.loads(Path(args.frm).read_text(encoding="utf-8"))
        render = emit_plan if args.emit_plan else emit_report
        sys.stdout.write(render(rep, source=args.frm))
        return 0

    sl = Slicer(args.target)
    if args.list:
        for rid in sl.region_ids():
            print("%4d  %s" % (rid, sl.label(rid)))
        return 0

    regions = None
    if args.regions:
        if "-" in args.regions and "," not in args.regions:
            a, b = args.regions.split("-")
            regions = [r for r in sl.content_regions() if int(a) <= r <= int(b)]
        else:
            regions = [int(x) for x in args.regions.split(",")]

    print("slice: full run of %s (%d regions, %d top-level statements)"
          % (sl.target, len(sl.region_ids()), len(sl.body)), flush=True)
    full = L.capture(sl.target, select=sl.full_spec(), tag="full")
    full.reconcile()
    full.reconcile_summary()
    attr, unattributed = _attribute(full.records, sl)
    # Both directions: every label the full run produced is attributed to exactly one
    # region, and the union of the per-region profiles is the full profile.
    union = {}
    for rid, prof in attr.items():
        for lab, sigs in prof.items():
            union.setdefault(lab, Counter()).update(sigs)
    round_trip = L.compare(full.profile(), union)
    print("slice: full run %d records, %d distinct labels; attribution round-trip %s"
          % (len(full.records), len(full.profile()),
             "IDENTICAL" if round_trip["identical"] else "DIFFERS"), flush=True)

    alone = run_alone(sl, attr, regions=regions, workers=args.workers)

    closures = []
    if args.closure:
        crashing = [r["region"] for r in alone if r["outcome"] != "CLEAN"]
        print("slice: closure over %d region(s) that did not run alone, round cap %d"
              % (len(crashing), args.closure_rounds), flush=True)
        closures = run_closures(sl, attr, crashing, workers=args.workers,
                                rounds=args.closure_rounds)

    perms = []
    content = sl.content_regions()
    for p in args.permute:
        if p == "reverse":
            order = list(reversed(content))
        elif p.startswith("shuffle:"):
            import random
            order = list(content)
            random.Random(int(p.split(":", 1)[1])).shuffle(order)
        elif p.startswith("blocks:"):
            n = int(p.split(":", 1)[1])
            chunks = [content[i:i + n] for i in range(0, len(content), n)]
            order = [r for ch in reversed(chunks) for r in ch]
        else:
            raise SystemExit("unknown permutation %r" % p)
        print("slice: permutation %s" % p, flush=True)
        perms.append(run_permutation(sl, full.profile(), order, p))
        print("  %s -> %s %s" % (p, perms[-1]["outcome"], perms[-1].get("exception", "")),
              flush=True)

    rep = summarize(sl, full, alone, perms, unattributed, attr)
    rep["attribution_round_trip_identical"] = round_trip["identical"]
    if closures:
        rep["closures"] = closures
        rep["closure_outcomes"] = dict(Counter(c["outcome"] for c in closures))
        # The HOIST LIST: every name a region had to be given before it would run. This is
        # the split's actual preparatory work, driven rather than estimated.
        hoist = Counter()
        for c in closures:
            hoist.update(c["resolved_names"])
        rep["hoist_names"] = sorted(hoist)
        rep["hoist_demand"] = dict(hoist.most_common())
        rep["unbound_names"] = sorted({n for c in closures for n in c["unbound_names"]})
        # Each hoisted name gets a DECLARED OWNER: the regions that bind it. AC3 requires an
        # owner per shared fixture, and an owner derived from the binding is not a judgement.
        _w_binders = sl.binders()
        rep["hoist_owners"] = {n: _w_binders.get(n, []) for n in rep["hoist_names"]}
        rep["closure_sizes"] = {str(c["region"]): len(c["closure"]) for c in closures}
        rep["closure_round_cap"] = args.closure_rounds
    if args.out:
        Path(args.out).write_text(json.dumps(rep, indent=1, sort_keys=True), encoding="utf-8")
        print("slice: wrote %s" % args.out)
    print("slice: outcomes %s" % rep["alone_outcomes"])
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except L.LabelRefusal as e:
        print("REFUSED %s" % e, file=sys.stderr)
        sys.exit(2)
