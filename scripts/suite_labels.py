#!/usr/bin/env python3
"""Assertion-label identity: the instrument that makes a suite restructure falsifiable.

DOMAIN. The set of assertion labels a RUN of a suite actually produces, each with its
multiplicity, its counter-delta signature and the file it was called from. Not the set of
string literals sitting in `expect(` call sites: that is a DESCRIPTION of the labels, and
guarding a description is not guarding the property. A label built by an f-string, by a
loop variable or by a helper is invisible to a literal scan and is measured here.

PROMISE. For two runs, this reports every label present in one and absent from the other,
IN BOTH DIRECTIONS, every label whose multiplicity moved, and every label whose
counter-delta signature moved. It reports LISTS, never counts, so a stray difference names
itself instead of hiding inside a total. It never asserts a cardinality: two runs of a
growing suite are compared against each other, never against a number typed here.

OBSERVATION POINT. The assertion primitive itself, at call time, in the running
interpreter of a fresh subprocess. The primitive is located STRUCTURALLY - a module-level
function that declares module globals and writes them, which is what a pass/fail counter
pair is - so a rename does not blind the instrument. The target file on disk is never
modified: the injection happens on the AST in the child's memory, and the target's sha256
is asserted unchanged across the run.

COMPLETENESS ARGUMENT, and it is a reconciliation rather than a claim. Every recorded
label carries the delta of every counter the primitive writes. At exit the instrument
asserts, per counter, that the sum of the recorded deltas EQUALS the counter's final value
in the subject's own globals, and that the integers the subject printed in its own summary
line are exactly those final values. An assertion that bypassed the primitive, a
double-counted wrapper, or a summary line that prints something other than what the
counters hold, all turn into a refusal rather than into a quietly short label set.

BLINDNESS, named rather than left to silence:
  1. Label identity says NOTHING about what a label asserts. An assertion whose condition
     is weakened while its label is untouched is invisible here. This instrument bounds a
     MOVE; it does not police a rewrite.
  2. It observes what RAN. An assertion inside a branch taken in neither run is absent
     from both label sets and compares equal.
  3. A label that varies run to run (a timestamp, a temp path, a set iteration order)
     would differ with no change at all. Determinism is therefore MEASURED, not assumed:
     `--determinism` runs the unchanged target twice and compares it to itself.
  4. It sees only the target it is pointed at. A suite file that nothing runs produces no
     labels and cannot be missed by a comparison of runs; that hole is SUITE_NOT_ENUMERATED
     in suite_equiv.py, not here.
"""
import argparse
import ast
import atexit
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCHEMA = "veldo.labels/v1"

REFUSALS = (
    "TARGET_MISSING",
    "TARGET_DOES_NOT_PARSE",
    "NO_PRIMITIVE",
    "INJECTION_NOT_APPLIED",
    "NO_RECORDS",
    "SUBJECT_CRASHED",
    "COUNTER_RECONCILIATION",
    "SUMMARY_RECONCILIATION",
    "TARGET_MUTATED_ON_DISK",
)

HOOK_NAME = "__veldo_label_hook__"
RECORDS_ENV = "VELDO_LABEL_RECORDS"
# The summary line's integers. Deliberately not anchored to the word "selftest": the
# reconciliation compares the integers a subject prints against the counters it holds,
# and a subject free to name its own line is a subject this instrument can still check.
SUMMARY_INT = re.compile(r"-?\d+")


class LabelRefusal(Exception):
    """A named structural refusal. The names are closed; see REFUSALS."""

    def __init__(self, code, detail=""):
        if code not in REFUSALS:
            raise ValueError("unknown refusal %r" % (code,))
        super().__init__("%s: %s" % (code, detail) if detail else code)
        self.code = code
        self.detail = detail


# --------------------------------------------------------------------------- primitive


def primitive_sites(tree):
    """Every module-level assertion primitive, located by SHAPE not by name.

    A primitive is a module-level function that declares module globals and assigns to
    them, and that takes at least two parameters (the label and the condition). That is
    the shape of a pass/fail counter helper. Returning the counters it writes is what lets
    the recorder derive an outcome without knowing that "FAIL" means failure.
    """
    out = []
    for st in tree.body:
        if not isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        declared = set()
        written = set()
        for n in ast.walk(st):
            if isinstance(n, ast.Global):
                declared.update(n.names)
            elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
                written.add(n.target.id)
            elif isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        written.add(t.id)
            elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
                written.add(n.target.id)
        counters = sorted(declared & written)
        params = [a.arg for a in st.args.args]
        if counters and len(params) >= 2:
            out.append({"name": st.name, "line": st.lineno, "counters": counters,
                        "params": params, "index": tree.body.index(st)})
    return out


def inject(tree, sites):
    """Insert one wrapper rebinding after each primitive definition. Returns the count."""
    inserted = 0
    for site in sorted(sites, key=lambda s: s["index"], reverse=True):
        call = ast.Call(
            func=ast.Name(id=HOOK_NAME, ctx=ast.Load()),
            args=[ast.Name(id=site["name"], ctx=ast.Load()),
                  ast.Constant(value=tuple(site["counters"]))],
            keywords=[])
        stmt = ast.Assign(targets=[ast.Name(id=site["name"], ctx=ast.Store())], value=call)
        ast.copy_location(stmt, tree.body[site["index"]])
        ast.fix_missing_locations(stmt)
        tree.body.insert(site["index"] + 1, stmt)
        inserted += 1
    return inserted


def parse_target(path):
    p = Path(path)
    if not p.is_file():
        raise LabelRefusal("TARGET_MISSING", str(p))
    src = p.read_text(encoding="utf-8")
    try:
        return src, ast.parse(src, filename=str(p))
    except SyntaxError as e:
        raise LabelRefusal("TARGET_DOES_NOT_PARSE", "%s line %s: %s" % (p, e.lineno, e.msg))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# --------------------------------------------------------------------------- the child


class _Recorder:
    """Lives in the child. Appends one record per assertion, reconciles at exit."""

    def __init__(self, out_path, entry):
        self.out = Path(out_path)
        self.entry = str(entry)
        self.records = []
        self.wrapped = {}          # primitive name -> counters it writes
        self.globals_of = {}       # primitive name -> its module globals
        self.installed_roots = []
        atexit.register(self.flush)

    def hook(self, fn, counters):
        g = fn.__globals__
        name = fn.__name__
        self.wrapped[name] = list(counters)
        self.globals_of[name] = g
        rec = self.records
        # The label is the primitive's FIRST parameter, whatever it is called there.
        first = fn.__code__.co_varnames[0] if fn.__code__.co_argcount else None

        def wrapped(*a, **kw):
            before = [g.get(c, 0) for c in counters]
            label = a[0] if a else kw.get(first)
            frame = sys._getframe(1)
            # The MODULE-LEVEL frames on the stack, outermost first. A label emitted from
            # inside a helper is attributed to its own call site by (file, line) and to the
            # top-level statement that is actually executing by this chain, because a
            # helper defined in one region and called from another would otherwise be
            # attributed to the region that merely defines it.
            mods = []
            f = frame
            while f is not None:
                if f.f_code.co_name == "<module>":
                    mods.append([f.f_code.co_filename, f.f_lineno])
                f = f.f_back
            mods.reverse()
            entry = {"label": label if isinstance(label, str) else repr(label),
                     "file": frame.f_code.co_filename, "line": frame.f_lineno,
                     "module_frames": mods, "primitive": name, "raised": False}
            rec.append(entry)
            try:
                return fn(*a, **kw)
            except BaseException:
                entry["raised"] = True
                raise
            finally:
                entry["delta"] = {c: (g.get(c, 0) or 0) - (b or 0)
                                  for c, b in zip(counters, before)}
        wrapped.__veldo_label_wrapper__ = True
        wrapped.__name__ = name
        return wrapped

    def flush(self):
        finals = {}
        for name, counters in self.wrapped.items():
            g = self.globals_of[name]
            for c in counters:
                finals[c] = g.get(c)
        applied = {name: bool(getattr(g.get(name), "__veldo_label_wrapper__", False))
                   for name, g in self.globals_of.items()}
        payload = {"schema": SCHEMA, "entry": self.entry, "records": self.records,
                   "counters_final": finals, "wrapped": self.wrapped,
                   "injection_applied": applied,
                   "instrumented": sorted(set(self.installed_roots))}
        tmp = self.out.with_suffix(self.out.suffix + ".part")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(tmp, self.out)


class _RewritingLoader(importlib.machinery.SourceFileLoader):
    """Injects the recorder into any instrumented module at import, in memory."""

    recorder = None

    def source_to_code(self, data, path, *, _optimize=-1):
        src = data.decode("utf-8") if isinstance(data, bytes) else data
        tree = ast.parse(src, filename=path)
        sites = primitive_sites(tree)
        if sites:
            inject(tree, sites)
            if _RewritingLoader.recorder is not None:
                _RewritingLoader.recorder.installed_roots.append(path)
        return compile(tree, path, "exec", dont_inherit=True, optimize=_optimize)

    def get_code(self, fullname):
        # Always compile from SOURCE. Serving an instrumented module from a bytecode
        # cache would run the uninstrumented code and report an empty label set.
        return self.source_to_code(self.get_data(self.path), self.path)

    def set_data(self, path, data, *, _mode=0o666):
        return None  # never write a .pyc for a rewritten module


class _RewritingFinder:
    """Swaps in the rewriting loader for modules whose file lies under a root."""

    def __init__(self, roots, recorder):
        self.roots = [Path(r).resolve() for r in roots]
        self.recorder = recorder
        _RewritingLoader.recorder = recorder

    def find_spec(self, fullname, path=None, target=None):
        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        if spec is None or not spec.origin or not spec.origin.endswith(".py"):
            return None
        origin = Path(spec.origin).resolve()
        if not any(str(origin).startswith(str(r) + os.sep) for r in self.roots):
            return None
        spec.loader = _RewritingLoader(fullname, spec.origin)
        # A rewritten module must never be served from a bytecode cache. The loader
        # above compiles from source and refuses to write one; bytecode writing is NOT
        # disabled process-wide, because a suite is entitled to depend on the ordinary
        # interpreter behaviour of the machine it runs on and this one measurably does.
        spec.cached = None
        return spec


def _is_exit_call(st):
    if not isinstance(st, ast.Expr) or not isinstance(st.value, ast.Call):
        return False
    f = st.value.func
    if isinstance(f, ast.Name) and f.id in ("exit", "quit"):
        return True
    return (isinstance(f, ast.Attribute) and f.attr == "exit"
            and isinstance(f.value, ast.Name) and f.value.id == "sys")


def apply_selection(tree, spec):
    """Keep only the named top-level statements, in the named order. Counts every edit.

    This is how a SUBSET of a monolith is run without editing the monolith: the statements
    are selected on the AST, in the child's memory, and compiled with their ORIGINAL line
    numbers intact so every record still points at the real file. Each transformation
    returns its own count, because a selection that silently matched nothing would produce
    a clean-looking run of nothing.
    """
    counts = {"selected": 0, "dropped_exit": 0, "appended_summary": 0}
    idx = list(spec["indices"])
    body = [tree.body[i] for i in idx]
    counts["selected"] = len(body)
    if spec.get("drop_exit"):
        keep = [st for st in body if not _is_exit_call(st)]
        counts["dropped_exit"] = len(body) - len(keep)
        body = keep
    tree.body = body
    if spec.get("append_summary"):
        counters = sorted({c for s in primitive_sites(tree) for c in s["counters"]})
        if counters:
            pr = ast.Expr(ast.Call(func=ast.Name(id="print", ctx=ast.Load()),
                                   args=[ast.Constant(value="veldo-slice:")]
                                   + [ast.Name(id=c, ctx=ast.Load()) for c in counters],
                                   keywords=[]))
            ast.copy_location(pr, tree.body[-1])
            ast.fix_missing_locations(pr)
            tree.body.append(pr)
            counts["appended_summary"] = 1
    return counts


def child_main(entry, records, roots, argv, select=None):
    """Execute the entry point with the recorder installed. Never writes to the target."""
    # `python3 <script>` puts the script's own directory first on sys.path. The child must
    # reproduce that or a suite that imports its sibling fixture module fails here and
    # nowhere else, which would be the harness inventing a defect.
    sys.path.insert(0, str(Path(entry).resolve().parent))
    src, tree = parse_target(entry)
    edits = {}
    if select:
        edits = apply_selection(tree, json.loads(Path(select).read_text(encoding="utf-8")))
    sites = primitive_sites(tree)
    rec = _Recorder(records, entry)
    rec.edits = edits
    # The hook lives on builtins, not in one module's globals: after the decomposition the
    # primitive is defined in an IMPORTED fixture module, whose globals the entry point's
    # namespace cannot reach. One resolution point works for both shapes.
    import builtins as _b
    setattr(_b, HOOK_NAME, rec.hook)
    if roots:
        sys.meta_path.insert(0, _RewritingFinder(roots, rec))
    n = inject(tree, sites)
    if not sites and not roots:
        # With no instrument roots the entry is the only place a primitive could be, so
        # finding none means this run would record nothing and compare equal to anything.
        # With roots, the primitive is expected to live in an imported fixture module.
        raise LabelRefusal("NO_PRIMITIVE", str(entry))
    if n != len(sites):
        raise LabelRefusal("INJECTION_NOT_APPLIED",
                           "%d sites, %d injections" % (len(sites), n))
    code = compile(tree, str(entry), "exec", dont_inherit=True)
    g = {"__name__": "__main__", "__file__": str(entry), HOOK_NAME: rec.hook,
         "__builtins__": __builtins__}
    sys.argv = [str(entry)] + list(argv)
    try:
        exec(code, g)
    except SystemExit as e:
        rec.flush()
        raise
    return 0


# --------------------------------------------------------------------------- the parent


class Capture:
    """One measured run: its records, its reconciliation, its provenance."""

    def __init__(self, payload, stdout, stderr, returncode, entry, digest):
        self.payload = payload
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.entry = entry
        self.digest = digest
        self.records = payload["records"]

    # ---- the reconciliation that is this instrument's completeness argument ----

    def reconcile(self):
        """Refuse unless the recorded deltas explain the subject's own arithmetic."""
        # A CRASH IS WORSE THAN A RED, and it is checked FIRST: a run that died looks exactly
        # like a run that found nothing wrong, and diagnosing it as "no records" would hide
        # the traceback that says why.
        if "Traceback (most recent call last)" in self.stderr:
            tail = self.stderr.strip().splitlines()
            raise LabelRefusal("SUBJECT_CRASHED",
                               "%s died: %s" % (self.entry, " | ".join(tail[-3:])))
        if not self.records:
            raise LabelRefusal("NO_RECORDS", "%s produced no assertion records" % self.entry)
        if not self.payload["wrapped"]:
            raise LabelRefusal("NO_PRIMITIVE",
                               "%s: nothing was instrumented, so an empty label set here"
                               " would compare equal to any other empty one" % self.entry)
        for name, ok in self.payload["injection_applied"].items():
            if not ok:
                raise LabelRefusal("INJECTION_NOT_APPLIED",
                                   "%s was rebound away from the wrapper" % name)
        if any(r["raised"] for r in self.records):
            bad = [r["label"] for r in self.records if r["raised"]]
            raise LabelRefusal("SUBJECT_CRASHED", "assertion raised: %s" % bad[:3])
        sums = Counter()
        for r in self.records:
            for c, d in r["delta"].items():
                sums[c] += d
        for c, final in self.payload["counters_final"].items():
            if sums.get(c, 0) != final:
                raise LabelRefusal(
                    "COUNTER_RECONCILIATION",
                    "counter %s: recorded deltas sum to %s, subject holds %s"
                    % (c, sums.get(c, 0), final))
        return dict(sums)

    def reconcile_summary(self):
        """The integers the subject printed must be the counters it holds."""
        finals = sorted(v for v in self.payload["counters_final"].values() if v is not None)
        best = None
        for line in self.stdout.splitlines():
            ints = sorted(int(m) for m in SUMMARY_INT.findall(line))
            if ints and ints == finals:
                best = line.strip()
        if best is None:
            raise LabelRefusal(
                "SUMMARY_RECONCILIATION",
                "no printed line carries exactly the counter values %s" % (finals,))
        return best

    # ---- the comparable profile ----

    def profile(self):
        """label -> Counter of delta signatures. The multiset, not the set.

        A SET of labels is blind to a duplicate label losing one of its occurrences, and
        the real suite does carry duplicates. The multiset is what a move preserves.
        """
        prof = {}
        for r in self.records:
            sig = ",".join("%s%+d" % (c, d) for c, d in sorted(r["delta"].items()))
            prof.setdefault(r["label"], Counter())[sig] += 1
        return prof

    def by_file(self):
        out = {}
        for r in self.records:
            out.setdefault(r["file"], []).append(r)
        return out

    def to_json(self):
        return {"schema": SCHEMA, "entry": self.entry, "digest": self.digest,
                "returncode": self.returncode,
                "counters_final": self.payload["counters_final"],
                "profile": {lab: dict(sigs) for lab, sigs in self.profile().items()}}


def capture(entry, roots=(), argv=(), cwd=None, env=None, timeout=1800, select=None,
            tag=""):
    """Run `entry` in a FRESH interpreter with the recorder installed.

    `select` is an optional selection spec (see apply_selection) which runs a SUBSET of the
    entry's top-level statements. The file on disk is never touched: the subset is taken on
    the AST in the child, and the digest is asserted unchanged after the run.
    """
    entry = Path(entry)
    digest_before = sha256(entry)
    workdir = Path(cwd) if cwd else entry.resolve().parent.parent
    scratch = Path(os.environ.get("TMPDIR", "/tmp"))
    stem = "veldo-labels-%d-%s%s" % (os.getpid(), hashlib.sha256(
        str(entry.resolve()).encode()).hexdigest()[:12], ("-" + tag) if tag else "")
    recfile = scratch / (stem + ".json")
    if recfile.exists():
        recfile.unlink()
    selfile = None
    cmd = [sys.executable, str(Path(__file__).resolve()), "--child",
           "--entry", str(entry.resolve()), "--records", str(recfile)]
    if select is not None:
        selfile = scratch / (stem + ".select.json")
        selfile.write_text(json.dumps(select), encoding="utf-8")
        cmd += ["--select", str(selfile)]
    for r in roots:
        cmd += ["--instrument-root", str(Path(r).resolve())]
    if argv:
        cmd += ["--"] + list(argv)
    e = dict(os.environ)
    if env:
        e.update(env)
    try:
        proc = subprocess.run(cmd, cwd=str(workdir), env=e, timeout=timeout,
                              capture_output=True, text=True)
    finally:
        if selfile is not None and selfile.exists():
            selfile.unlink()
    if sha256(entry) != digest_before:
        raise LabelRefusal("TARGET_MUTATED_ON_DISK", str(entry))
    if not recfile.exists():
        raise LabelRefusal("SUBJECT_CRASHED",
                           "no records from %s (rc=%d): %s"
                           % (entry, proc.returncode, proc.stderr[-400:]))
    payload = json.loads(recfile.read_text(encoding="utf-8"))
    recfile.unlink()
    return Capture(payload, proc.stdout, proc.stderr, proc.returncode,
                   str(entry), digest_before)


# --------------------------------------------------------------------------- comparison


def compare(before, after):
    """Identity in BOTH directions. Lists, never counts.

    `before` and `after` are profiles (label -> Counter of delta signatures) or Captures.
    """
    if isinstance(before, Capture):
        before = before.profile()
    if isinstance(after, Capture):
        after = after.profile()
    b, a = set(before), set(after)
    both = b & a
    mult = sorted((lab, sum(before[lab].values()), sum(after[lab].values()))
                  for lab in both
                  if sum(before[lab].values()) != sum(after[lab].values()))
    sig = sorted((lab, sorted(before[lab].items()), sorted(after[lab].items()))
                 for lab in both
                 if before[lab] != after[lab]
                 and sum(before[lab].values()) == sum(after[lab].values()))
    out = {
        "missing": sorted(b - a),
        "added": sorted(a - b),
        "multiplicity_changed": mult,
        "signature_changed": sig,
    }
    out["identical"] = not (out["missing"] or out["added"]
                            or out["multiplicity_changed"] or out["signature_changed"])
    return out


def duplicates(profile):
    """Labels a single run emits more than once. A set comparison is blind to these."""
    if isinstance(profile, Capture):
        profile = profile.profile()
    return sorted(lab for lab, sigs in profile.items() if sum(sigs.values()) > 1)


# --------------------------------------------------------------------------- cli


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--entry", default=str(ROOT / "scripts" / "selftest.py"))
    ap.add_argument("--records")
    ap.add_argument("--select", help=argparse.SUPPRESS)
    ap.add_argument("--instrument-root", action="append", default=[])
    ap.add_argument("--capture", metavar="OUT", help="write the run's profile as JSON")
    ap.add_argument("--capture-records", metavar="OUT",
                    help="write the run's RAW records, including frame attribution")
    ap.add_argument("--against", metavar="JSON", help="compare a fresh run to a captured one")
    ap.add_argument("--determinism", action="store_true",
                    help="run the target twice and compare it to ITSELF")
    ap.add_argument("--sites", action="store_true",
                    help="report the primitive sites without running anything")
    ap.add_argument("rest", nargs="*", default=[])
    args = ap.parse_args(argv)

    if args.child:
        return child_main(args.entry, args.records, args.instrument_root,
                          [a for a in args.rest if a != "--"], select=args.select)

    if args.sites:
        src, tree = parse_target(args.entry)
        sites = primitive_sites(tree)
        if not sites:
            print("NO_PRIMITIVE in %s" % args.entry)
            return 1
        for s in sites:
            print("%s:%d %s(%s) counters=%s"
                  % (args.entry, s["line"], s["name"], ", ".join(s["params"]),
                     ",".join(s["counters"])))
        return 0

    cap = capture(args.entry, roots=args.instrument_root)
    cap.reconcile()
    summary = cap.reconcile_summary()
    prof = cap.profile()
    print("labels: %d distinct, %d assertion records, reconciled against %r"
          % (len(prof), len(cap.records), summary))
    dups = duplicates(prof)
    if dups:
        print("labels: %d label(s) emitted more than once (a SET comparison is blind to"
              " losing one occurrence; this instrument compares the MULTISET)" % len(dups))
    if args.capture:
        Path(args.capture).write_text(json.dumps(cap.to_json(), indent=1, sort_keys=True),
                                      encoding="utf-8")
        print("labels: wrote %s" % args.capture)
    if args.capture_records:
        Path(args.capture_records).write_text(
            json.dumps({"schema": SCHEMA, "entry": cap.entry, "digest": cap.digest,
                        "counters_final": cap.payload["counters_final"],
                        "records": cap.records}), encoding="utf-8")
        print("labels: wrote %s" % args.capture_records)
    if args.determinism:
        again = capture(args.entry, roots=args.instrument_root)
        again.reconcile()
        d = compare(prof, again.profile())
        print("labels: determinism %s" % ("IDENTICAL" if d["identical"] else "DIFFERS"))
        if not d["identical"]:
            print(json.dumps(d, indent=1)[:4000])
            return 1
    if args.against:
        old = json.loads(Path(args.against).read_text(encoding="utf-8"))
        oldprof = {lab: Counter(sigs) for lab, sigs in old["profile"].items()}
        d = compare(oldprof, prof)
        print("labels: identity vs %s: %s"
              % (args.against, "IDENTICAL" if d["identical"] else "DIFFERS"))
        if not d["identical"]:
            print(json.dumps(d, indent=1)[:8000])
            return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except LabelRefusal as e:
        print("REFUSED %s" % e, file=sys.stderr)
        sys.exit(2)
