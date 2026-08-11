#!/usr/bin/env python3
"""ONE-TIME migration: cut the monolithic unit suite into per-module suite files.

THIS IS NOT A GENERATOR THE GATE RUNS. It ran once, to perform WARP-0712's decomposition,
and the files it produced are ordinary hand-owned source from that moment on. It is kept
because a reviewer is entitled to re-derive the cut rather than read 27,000 moved lines, and
because its own structural check is the strongest statement available that nothing was lost.

DOMAIN. The top-level statements of one monolithic assertion suite, and the LINES of the file
that carries them.

PROMISE, and it is a partition rather than a copy. Every line of the original file lands in
exactly one emitted file, in its original order relative to its neighbours, with its comments
and blank lines attached to the statement they precede. The tool asserts that before writing:
the concatenation of the emitted spans, in original statement order, is byte-identical to the
original file minus the epilogue that becomes the dispatcher's. Nothing is reformatted and
nothing is unparsed, because ast.unparse would rewrite 27,000 lines of source text that a
reviewer has to trust.

OBSERVATION POINT. Line spans, taken from the AST. Span i is lines
(end_lineno[i-1] + 1) .. end_lineno[i], so the spans tile the whole file with no gap and no
overlap, and every comment travels with the statement below it.

COMPLETENESS ARGUMENT. Two independent checks, both mechanical. Structurally, the span
partition above. Behaviourally, the shared module is driven to a FIXED POINT rather than
reasoned about: it is executed, and if it dies on an undefined name the statement that binds
that name is added and it is executed again, until it runs clean. What comes out is the
smallest shared set this method can find, not a set someone judged to be enough.

BLINDNESS, named.
  1. Hoisting a statement moves it EARLIER relative to statements that stay behind. Nothing
     here can see a dependency on that relative order. The label-identity proof
     (scripts/suite_labels.py) and the per-suite equivalence proof (scripts/suite_equiv.py)
     are what catch it, and they are the landing condition rather than this tool.
  2. The fixed point follows undefined NAMES. A dependency carried by a mutated shared
     object, an environment variable or a file on disk does not raise NameError.
  3. It cannot see an assertion whose SUBJECT is the file being cut. An assertion that reads
     scripts/selftest.py and measures its shape measures a different thing afterwards, and
     that is a property of the assertion, not of this tool.
"""
import argparse
import ast
import json
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_HERE = Path(__file__).resolve().parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, _HERE / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


L = _load("suite_labels")
S = _load("suite_slice")

_NAME_RE = re.compile(r"name '([^']+)' is not defined")
FIXED_POINT_MAX = 400

SHARED_NAME = "shared"
SUITE_DIR = "scripts/suites"

# HISTORICAL TEMPLATE. DO NOT RE-APPLY. This is the shared preamble WARP-0712's one-time
# decomposition emitted, and its report() is the OLD UNCONDITIONAL one. WARP-0717 replaced it:
# the shipped scripts/suites/shared.py emits through a RunScope, so a PARTIAL run cannot print
# the aggregate summary line at all. Re-running this tool over the shipped tree would overwrite
# that and silently revert the whole mechanism, and nothing holds the two in step, because
# scripts/selftest.py and scripts/suites/shared.py are not in scripts/check_generated.sh. That
# freshness binding is review 1's cross-item finding X2 and belongs to its own item; this
# header is the cheap half. If you are decomposing a suite again, take the shipped files as the
# starting point, never these strings.
SHARED_PRELUDE = '''

def report():
    """The aggregate summary line, in the monolith's exact format, and the exit code."""
    print(f"selftest: {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


def suite_source():
    """The whole unit suite's source: every file the manifest enumerates, concatenated.

    It exists because a handful of assertions have the SUITE ITSELF as their subject - they
    check that a retired assertion label is gone and that its replacement is present. Before
    the decomposition they read one file. Reading scripts/selftest.py after it would read a
    dispatcher and pass vacuously, so they read this instead, and their labels are untouched.
    """
    import json as _json
    _here = Path(__file__).resolve().parent
    _m = _json.loads((_here / "manifest.json").read_text())
    _parts = [(_here / s["file"]).read_text() for s in _m["suites"]]
    return "".join(_parts)


'''

SHARED_HEADER = '''\
"""Shared fixtures and the assertion primitive: the one module every suite imports.

THIS FILE IS THE SUITE'S PREAMBLE PLUS EVERY MODULE-LEVEL BINDING THAT CROSSED A REGION
BOUNDARY in the monolith WARP-0712 cut up. Its membership was not chosen: it is the fixed
point of "run it, and if it dies on an undefined name, add the statement that binds that
name". It is enumerated as the FIRST suite in suites/manifest.json, because it carries
assertions of its own and a label produced by a file no manifest names is exactly what
SUITE_NOT_ENUMERATED exists to refuse.

THERE IS ONE NAMESPACE AND IT IS THIS MODULE'S. scripts/selftest.py execs every fragment into
this module's __dict__, in manifest order; no fragment imports this module and none has a
namespace of its own. So a fragment that REBINDS a name here changes what every later fragment
sees, which is exactly what the monolith did and is why the decomposition cannot change what any
assertion proves. The dispatcher's docstring states the measurement that decision came from.
"""
'''

SUITE_HEADER = '''\
"""%(title)s

ONE SUITE OF THE UNIT SUITE, AND A FRAGMENT RATHER THAN A MODULE. It is compiled and executed
into scripts/suites/shared.py's namespace by scripts/selftest.py, in manifest order, so every
suite sees exactly the state the monolith gave it and this decomposition cannot change what any
assertion proves. That is the whole reason for the design: the monolith carries cross-region
dependencies through MUTATED objects and through the filesystem, not only through names, and no
mechanical analysis finds those. Sharing one namespace in the original order means no membership
rule has to be closed and correctness is a property of the construction.

Run it: `python3 scripts/selftest.py --upto %(name)s` runs everything up to and including this
file, which is the inner loop for a change here. `python3 scripts/selftest.py` runs everything
and is the only thing that means green.

Regions %(regions)s of the pre-split monolith.
"""
'''

SUITE_FOOTER = ""

# HISTORICAL TEMPLATE. DO NOT RE-APPLY. This is the PRE-WARP-0717 dispatcher: no RunScope, no
# `--suite`, no partial-run banner, and an `--upto` that prints its own line without one. The
# shipped scripts/selftest.py is the corrected one, where NO selector can emit the aggregate
# line and every run's authority to claim anything lives in scripts/run_scope.py. Re-running
# this tool over the shipped tree would overwrite it and silently revert AC2's entire
# mechanism while leaving the fragments intact, and nothing holds the two in step, because
# scripts/selftest.py is not in scripts/check_generated.sh. That freshness binding is review
# 1's cross-item finding X2 and belongs to its own item; this header is the cheap half. Kept
# rather than deleted because it is the record of what the dispatcher was at the cut, and this
# tool is still the documented way a decomposition is done: start from the shipped files.
DISPATCHER = '''\
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
different suites do not collide, plus a prefix inner loop.

  python3 scripts/selftest.py                 the whole suite; the only thing that means green
  python3 scripts/selftest.py --upto NAME     everything up to and including one suite
  python3 scripts/selftest.py --list          the manifest order

--upto CANNOT COUNT AS A GATE PASS and is built so it cannot be mistaken for one: it prints a
different final line, `selftest (PARTIAL, N of M suites): ...`, so nothing that parses the
aggregate line can read a partial run as a full one, and it exits 2 on success rather than 0.
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITES = HERE / "suites"
sys.path.insert(0, str(SUITES))

MANIFEST = json.loads((SUITES / "manifest.json").read_text())
FRAGMENTS = [s for s in MANIFEST["suites"] if s["file"] != MANIFEST["shared"]]
ORDER = [s["name"] for s in FRAGMENTS]

ON_DISK = sorted(p.name for p in SUITES.glob("*.py"))
DECLARED = sorted([MANIFEST["shared"]] + [s["file"] for s in FRAGMENTS])
if ON_DISK != DECLARED:
    print("selftest: SUITE_NOT_ENUMERATED: on disk %s, manifest %s"
          % (sorted(set(ON_DISK) - set(DECLARED)), sorted(set(DECLARED) - set(ON_DISK))))
    sys.exit(2)

if "--list" in sys.argv:
    for s in FRAGMENTS:
        print("%-44s %s" % (s["name"], s["file"]))
    sys.exit(0)

UPTO = None
if "--upto" in sys.argv:
    UPTO = sys.argv[sys.argv.index("--upto") + 1]
    if UPTO not in ORDER:
        print("selftest: unknown suite %r (see --list)" % UPTO)
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
if UPTO:
    RUN = RUN[:[s["name"] for s in RUN].index(UPTO) + 1]

import shared  # noqa: E402 - the shared namespace every fragment runs in

for _s in RUN:
    _p = SUITES / _s["file"]
    # A fragment's own path, bound before it runs. Its `__file__` is shared.py's, because that
    # is the namespace it executes in, so an assertion whose SUBJECT is its own file needs this.
    shared.__dict__["__suite_file__"] = str(_p)
    exec(compile(_p.read_text(), str(_p), "exec"), shared.__dict__)

if UPTO:
    print("selftest (PARTIAL, %d of %d suites): %d passed, %d failed"
          % (len(RUN), len(FRAGMENTS), shared.PASS, shared.FAIL))
    sys.exit(2 if not shared.FAIL else 1)
sys.exit(shared.report())
'''


class Cut:
    def __init__(self, target, measurement, budget=250):
        self.target = Path(target)
        self.src = self.target.read_text()
        self.lines = self.src.splitlines(keepends=True)
        self.slicer = S.Slicer(str(self.target))
        self.body = self.slicer.body
        self.budget = budget
        self.meas = json.loads(Path(measurement).read_text())
        self.spans = self._spans()
        self.binders = self._stmt_binders()

    # ---- the line partition ----

    def _spans(self):
        """statement index -> (first_line, last_line), 1-based, tiling the whole file."""
        out = []
        prev_end = 0
        for st in self.body:
            end = getattr(st, "end_lineno", None) or st.lineno
            out.append((prev_end + 1, end))
            prev_end = end
        return out

    def text_of(self, idx):
        a, b = self.spans[idx]
        return "".join(self.lines[a - 1:b])

    def _stmt_binders(self):
        out = {}
        for si, st in enumerate(self.body):
            for name in S._bound_names(st):
                out.setdefault(name, []).append(si)
        return out

    # ---- membership ----

    def epilogue(self):
        """The trailing statements that become the dispatcher's: the summary and the exit."""
        out = []
        for si in range(len(self.body) - 1, -1, -1):
            st = self.body[si]
            if S._EXC and isinstance(st, ast.Expr) and isinstance(st.value, ast.Call):
                f = st.value.func
                if isinstance(f, ast.Name) and f.id == "print":
                    out.append(si)
                    break
            if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call):
                f = st.value.func
                if isinstance(f, ast.Attribute) and f.attr == "exit":
                    out.append(si)
                    continue
            break
        return sorted(out)

    def seed_shared(self):
        """The preamble, plus every statement binding a name the measurement saw cross.

        STATEMENT GRANULARITY. Tried first and ABANDONED, with the reason recorded because it
        is the more attractive design and someone will try it again: it produces a shared
        module of about 180 statements instead of 89 whole regions, but its membership rule
        follows NAMES and the monolith's cross-region dependencies are not all names. Driving
        it to a fixed point resolved seven module specs and two module loads and then died on
        a FileNotFoundError, because one hoisted statement makes a directory inside a
        temporary tree another statement created. That tail is unbounded by inspection, so
        the region rule below is what shipped.
        """
        crossing = set(self.meas.get("hoist_names", []))
        idx = set(self.slicer.by_region.get(0, []))
        for si, st in enumerate(self.body):
            if S._bound_names(st) & crossing:
                idx.add(si)
        return idx

    def shared_regions(self):
        """The PREAMBLE, and nothing else.

        WHY IT IS NOT THE UNION OF THE MEASURED CLOSURES, which is what an earlier version of
        this tool used and what the split plan proposed. That rule made a shared module of 89
        regions and 16,800 lines, which is still a god file two lanes collide on, and it was
        justified by an argument that turned out to be FALSE: the union of the closures is
        closed under "needs" only if every dependency is a NAME. Driven, it is not. Running the
        89-region set alone died on a dict a LATER region fills, read through a defensive
        `or` fallback that turns the missing input into a silent None instead of a NameError.
        A membership rule whose closure cannot be proven is not a membership rule.

        Because the fragments execute in ONE namespace in the ORIGINAL ORDER, no membership
        rule is needed at all: the cut can fall anywhere between two top-level statements and
        every statement still sees exactly what the monolith gave it. So the shared module
        holds only what has to exist BEFORE the first fragment runs (the preamble: the
        imports, the module loads, the assertion primitive and its counters), and every region
        after it is free to land in any file.

        WHAT THAT BUYS IS NOT BALANCE. The emitted fragments are nowhere near equal in size and
        this rule does not make them so. What it buys is that the cut is an EXACT PARTITION:
        every line of the monolith lands in exactly one emitted file, which is the property
        verify_partition asserts before anything is written, and it is the property that makes
        the decomposition checkable at all.
        """
        return {0}

    def seed_shared_by_region(self):
        idx = set()
        for rid in self.shared_regions():
            idx |= set(self.slicer.by_region.get(rid, []))
        return idx

    def _root_names_read(self, st):
        """Every module-level name the statement reads, over-approximated on purpose."""
        out = set()
        bound = S._bound_names(st)
        for n in ast.walk(st):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                out.add(n.id)
        return out - bound

    def _has_assertion(self, st):
        for n in ast.walk(st):
            if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "expect":
                return True
        return False

    def complete_adjacent(self, idx):
        """Pull in the SIDE-EFFECTING COMPLETIONS of shared state, and only those.

        A three-statement module load is the reason this exists: `spec = ...` binds a name,
        `MOD = module_from_spec(spec)` binds a name, and `spec.loader.exec_module(MOD)` binds
        NOTHING. A membership rule that follows bindings takes the first two and leaves the
        module unexecuted, which is not a NameError but an AttributeError on a module that
        never ran. The rule here is deliberately narrow: the statement must sit IMMEDIATELY
        after a statement already in the set, bind nothing, hold no assertion, and read only
        names the set already has. Anything looser would start dragging late side effects
        forward.
        """
        idx = set(idx)
        added = []
        changed = True
        while changed:
            changed = False
            for si in sorted(idx):
                nxt = si + 1
                if nxt >= len(self.body) or nxt in idx:
                    continue
                st = self.body[nxt]
                if S._bound_names(st) or self._has_assertion(st):
                    continue
                if not self._root_names_read(st) <= self._names_in(idx):
                    continue
                idx.add(nxt)
                added.append(nxt)
                changed = True
        return idx, added

    def _names_in(self, idx):
        out = set(dir(__builtins__)) | {"__file__", "__name__", "__doc__"}
        import builtins
        out |= set(dir(builtins))
        for si in idx:
            out |= S._bound_names(self.body[si])
        return out

    def _region_of_crash(self, detail):
        """The region of the DEEPEST frame of the traceback that lies in the target file."""
        want = 'File "%s", line ' % self.target
        line = None
        for part in detail.split("|"):
            part = part.strip()
            if part.startswith(want):
                try:
                    line = int(part[len(want):].split(",")[0])
                except ValueError:
                    pass
        if line is None:
            return None
        for si, (a, b) in enumerate(self.spans):
            if a <= line <= b:
                return self.slicer.region_of[si]
        return None

    def drive_shared(self, idx, verbose=True):
        """Run the shared set and add binders until it runs clean. Returns (idx, added)."""
        idx = set(idx)
        added = []
        for _ in range(FIXED_POINT_MAX):
            idx, comp = self.complete_adjacent(idx)
            if comp and verbose:
                print("  shared += %d adjacent completion(s) %s"
                      % (len(comp), comp[:6]), flush=True)
            spec = {"indices": sorted(idx), "drop_exit": True, "append_summary": True}
            try:
                cap = L.capture(self.target, select=spec, tag="shared")
                cap.reconcile()
                return sorted(idx), added
            except L.LabelRefusal as e:
                if e.code != "SUBJECT_CRASHED":
                    raise
                m = _NAME_RE.search(e.detail)
                if m:
                    name = m.group(1)
                    owners = [s for s in self.binders.get(name, []) if s not in idx]
                    if not owners:
                        raise SystemExit("no module-level binder for %r" % name)
                    idx.add(min(owners))
                    added.append(name)
                    if verbose:
                        print("  shared += stmt %d for %s" % (min(owners), name), flush=True)
                    continue
                # NOT A NAME. The dependency is carried by something else: a directory another
                # statement made, an environment variable, a mutated object. There is no
                # binding to follow, so the resolution falls back to the unit the measurement
                # DID prove: the whole REGION containing the statement that died. Bounded,
                # automatic, and it names what it pulled in.
                rid = self._region_of_crash(e.detail)
                if rid is None:
                    raise SystemExit("cannot locate the crash in the target: %s"
                                     % e.detail[:400])
                new = set(self.slicer.by_region.get(rid, [])) - idx
                if not new:
                    raise SystemExit("region %d is already whole and still dies: %s"
                                     % (rid, e.detail[:400]))
                idx |= new
                added.append("region:%d" % rid)
                if verbose:
                    print("  shared += region %d (%d stmts) for a non-name dependency"
                          % (rid, len(new)), flush=True)
        raise SystemExit("shared set did not reach a fixed point in %d rounds"
                         % FIXED_POINT_MAX)

    def partition(self, shared_idx, epilogue):
        """The remaining statements, grouped into contiguous region runs by an assertion
        budget. A suite boundary never falls inside a top-level statement, because the unit
        being grouped IS the statement."""
        labels = {int(k): v for k, v in self.meas.get("region_labels", {}).items()}
        left = [si for si in range(len(self.body))
                if si not in shared_idx and si not in epilogue]
        by_region = {}
        for si in left:
            by_region.setdefault(self.slicer.region_of[si], []).append(si)
        groups = []
        cur, load = [], 0
        for rid in sorted(by_region):
            cur.append(rid)
            load += labels.get(rid, 0)
            if load >= self.budget:
                groups.append((cur, load))
                cur, load = [], 0
        if cur:
            groups.append((cur, load))
        return [{"regions": rs, "assertions": n,
                 "indices": sorted(si for r in rs for si in by_region[r])}
                for rs, n in groups]

    # ---- emission ----

    def emit(self, dest, shared_idx, groups, epilogue):
        dest = Path(dest)
        sdir = dest / SUITE_DIR
        sdir.mkdir(parents=True, exist_ok=True)
        written = {}

        shared_text = "".join(self.text_of(i) for i in sorted(shared_idx))
        # ROOT is computed from __file__ and the file moved one directory deeper.
        old = "ROOT = Path(__file__).resolve().parent.parent\n"
        new = "ROOT = Path(__file__).resolve().parent.parent.parent\n"
        n = shared_text.count(old)
        if n != 1:
            raise SystemExit("expected exactly one ROOT binding in shared, found %d" % n)
        shared_text = shared_text.replace(old, new)
        written[str(sdir / (SHARED_NAME + ".py"))] = (
            SHARED_HEADER + shared_text + SHARED_PRELUDE)

        suites = [{"name": SHARED_NAME, "file": SHARED_NAME + ".py",
                   "regions": "preamble and every crossing binding"}]
        for i, g in enumerate(groups, 1):
            first = g["regions"][0]
            label = self.meas.get("region_label_text", {}).get(str(first), "")
            slug = S._slug(label)
            name = "%02d_%s" % (i, slug)
            body = "".join(self.text_of(si) for si in g["indices"])
            head = SUITE_HEADER % {
                "title": (label.replace("# ---", "").strip().rstrip("-").strip()
                          or "unit suite %s" % name),
                "name": name,
                "regions": "%s-%s" % (g["regions"][0], g["regions"][-1])}
            written[str(sdir / (name + ".py"))] = head + "\n" + body + SUITE_FOOTER
            suites.append({"name": name, "file": name + ".py",
                           "regions": "%s-%s" % (g["regions"][0], g["regions"][-1])})

        manifest = {
            "schema": "veldo.suites/v1",
            "entry": "selftest.py",
            "shared": SHARED_NAME + ".py",
            "note": ("Every suite here runs standalone and inside the aggregate and is "
                     "asserted by scripts/suite_equiv.py to prove the same thing both ways. "
                     "A file present in this directory and absent from this list turns the "
                     "gate RED as SUITE_NOT_ENUMERATED rather than silently not running."),
            "ordering_dependencies": [],
            "suites": suites,
        }
        written[str(sdir / "manifest.json")] = json.dumps(manifest, indent=1) + "\n"
        written[str(dest / "scripts" / "selftest.py")] = DISPATCHER
        return written

    # ---- the structural check, run BEFORE anything is written ----

    def verify_partition(self, shared_idx, groups, epilogue):
        used = list(shared_idx) + [si for g in groups for si in g["indices"]] + list(epilogue)
        if sorted(used) != list(range(len(self.body))):
            dup = sorted({x for x in used if used.count(x) > 1})
            missing = sorted(set(range(len(self.body))) - set(used))
            raise SystemExit("partition is not exact: %d duplicated %s, %d missing %s"
                             % (len(dup), dup[:5], len(missing), missing[:5]))
        rebuilt = "".join(self.text_of(i) for i in range(len(self.body)))
        if rebuilt != self.src:
            raise SystemExit("span reconstruction is not byte-identical to the source")
        return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", default=str(ROOT / "scripts" / "selftest.py"))
    ap.add_argument("--measurement",
                    default=str(ROOT / "proof/WARP-0712/order-dependence.json"))
    ap.add_argument("--dest", default=str(ROOT))
    ap.add_argument("--budget", type=int, default=250)
    ap.add_argument("--mode", choices=("region", "statement"), default="region",
                    help="region is what shipped; statement is the abandoned attempt")
    ap.add_argument("--apply", action="store_true", help="write the files")
    ap.add_argument("--report", dest="report_to")
    args = ap.parse_args(argv)

    cut = Cut(args.target, args.measurement, budget=args.budget)
    epi = cut.epilogue()
    print("epilogue statements (become the dispatcher's): %s" % epi)
    added = []
    if args.mode == "statement":
        seed = cut.seed_shared() - set(epi)
        print("shared seed: %d statements (preamble %d + crossing binders)"
              % (len(seed), len(cut.slicer.by_region.get(0, []))))
        shared_idx, added = cut.drive_shared(seed)
        print("shared fixed point: %d statements, %d name(s) added by driving it"
              % (len(shared_idx), len(added)))
    else:
        srs = cut.shared_regions()
        shared_idx = sorted(cut.seed_shared_by_region() - set(epi))
        print("shared: %d regions (the preamble plus every region another region needs),"
              " %d statements" % (len(srs), len(shared_idx)))
    groups = cut.partition(set(shared_idx), set(epi))
    print("suites: %d" % len(groups))
    cut.verify_partition(set(shared_idx), groups, set(epi))
    print("partition: exact, and the spans rebuild the source byte-identically")
    files = cut.emit(args.dest, shared_idx, groups, epi)
    for path, text in sorted(files.items()):
        print("  %-58s %6d lines" % (path, len(text.splitlines())))
    if args.report_to:
        Path(args.report_to).write_text(json.dumps(
            {"shared_indices": sorted(shared_idx), "added_names": added,
             "epilogue": epi,
             "groups": [{"regions": g["regions"], "assertions": g["assertions"],
                         "statements": len(g["indices"])} for g in groups]},
            indent=1), encoding="utf-8")
    if args.apply:
        for path, text in files.items():
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(text, encoding="utf-8")
        print("applied")
    else:
        print("dry run; pass --apply to write")
    return 0


if __name__ == "__main__":
    sys.exit(main())
