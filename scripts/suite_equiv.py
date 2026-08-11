#!/usr/bin/env python3
"""Standalone-and-aggregate equivalence: does a suite prove the SAME THING both ways?

DOMAIN. A manifest of suites, each a file runnable on its own; the aggregate run of all of
them through one entry point; and the aggregate run again under a different suite ORDER.

PROMISE. For every suite the manifest enumerates, the labels it produced INSIDE the
aggregate run are compared with the labels it produced ALONE in a fresh interpreter, by
identity, in BOTH directions, with multiplicity and with each label's counter-delta
signature. Exit codes are compared too but they are the weak part and never the finding: the
named failure mode is a suite that passes in aggregate and fails alone, and its dangerous
twin is a suite that passes alone while proving strictly less, which is two green exit codes
and a shorter label set. That twin is what PROVES_LESS_ALONE names.

OBSERVATION POINT. suite_labels' recorder, in a fresh subprocess per run, with the suites
directory as an instrument root so the assertion primitive is wrapped wherever the fixture
module defines it. A label is attributed to a suite by the INNERMOST module-level frame that
lies in an enumerated suite file, so the dispatcher importing a suite does not claim the
suite's labels, and a helper in the fixture module does not either.

COMPLETENESS ARGUMENT, in both directions and as SET RELATIONS, never as counts.
  1. The suite files present on disk under the manifest's own directory and the files the
     manifest enumerates are compared as sets. A file on disk and not in the manifest is
     SUITE_NOT_ENUMERATED: it would silently not run. A file in the manifest and not on disk
     is SUITE_FILE_MISSING.
  2. Every record of the aggregate run attributes to an enumerated suite. One that does not
     is SUITE_NOT_ENUMERATED in its second form: a label produced by something the manifest
     does not name.
  3. Every enumerated suite is run alone, and the union of the per-suite aggregate
     projections is compared with the whole aggregate profile in both directions, so a label
     no suite claims and a label two suites claim both surface. The second of those is
     SUITE_LABEL_COLLISION, which is what would let one suite mask another inside an
     identity proof.

BLINDNESS, named:
  1. Labels, multiplicities and counter deltas are compared. A suite that asserts the SAME
     labels against different data alone versus in company, both passing, is invisible.
     Nothing short of comparing the asserted values would see it, and the values are not
     observable at this seam.
  2. A suite that is vacuous in both runs is equivalent to itself. Anti-vacuity is a
     different item and this harness does not stand in for it.
  3. Order independence is proven over the orders it is GIVEN. It is a falsification
     instrument, not a proof over all permutations: a dependency between two suites that
     both orders happen to preserve is not caught. The reverse order plus a seeded shuffle
     is what is run, and the reverse order is the one that breaks a linear chain.
  4. It observes runs. A suite whose file is never imported by the dispatcher and never
     named in the manifest is outside the domain of every comparison here; that hole is
     closed by the on-disk set relation above and by nothing else.
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_HERE = Path(__file__).resolve().parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, _HERE / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


L = _load("suite_labels")

SCHEMA = "veldo.suites/v1"
ORDER_ENV = "VELDO_SUITE_ORDER"

# The closed defect vocabulary. A defect this harness cannot name is a defect it does not
# report, so the list is the honest statement of what it can find.
DEFECTS = (
    "SUITE_NOT_ENUMERATED",
    "SUITE_FILE_MISSING",
    "SUITE_LABEL_COLLISION",
    "PASSES_IN_AGGREGATE_FAILS_ALONE",
    "PROVES_LESS_ALONE",
    "PROVES_MORE_ALONE",
    "MULTIPLICITY_DIFFERS",
    "OUTCOME_DIFFERS",
    "ORDER_DEPENDENT",
    "ATTRIBUTION_INCOMPLETE",
)

REFUSALS = ("MANIFEST_MISSING", "MANIFEST_MALFORMED", "AGGREGATE_CRASHED")


class EquivRefusal(Exception):
    def __init__(self, code, detail=""):
        if code not in REFUSALS:
            raise ValueError("unknown refusal %r" % (code,))
        super().__init__("%s: %s" % (code, detail) if detail else code)
        self.code = code
        self.detail = detail


# --------------------------------------------------------------------------- manifest


class Manifest:
    def __init__(self, path):
        self.path = Path(path)
        if not self.path.is_file():
            raise EquivRefusal("MANIFEST_MISSING", str(self.path))
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        except ValueError as e:
            raise EquivRefusal("MANIFEST_MALFORMED", "%s: %s" % (self.path, e))
        if self.data.get("schema") != SCHEMA:
            raise EquivRefusal("MANIFEST_MALFORMED",
                               "schema must be %s, got %r" % (SCHEMA, self.data.get("schema")))
        if not isinstance(self.data.get("suites"), list) or not self.data["suites"]:
            raise EquivRefusal("MANIFEST_MALFORMED", "suites must be a non-empty list")
        self.root = self.path.parent
        self.entry = self.root.parent / self.data.get("entry", "selftest.py")
        self.suites = []
        seen = set()
        for s in self.data["suites"]:
            if not isinstance(s, dict) or "name" not in s or "file" not in s:
                raise EquivRefusal("MANIFEST_MALFORMED", "each suite needs name and file")
            if s["name"] in seen:
                raise EquivRefusal("MANIFEST_MALFORMED", "duplicate suite name %r" % s["name"])
            seen.add(s["name"])
            self.suites.append({"name": s["name"], "file": (self.root / s["file"]).resolve(),
                                "declared": s["file"]})
        self.ordering = self.data.get("ordering_dependencies", [])

    def names(self):
        return [s["name"] for s in self.suites]

    def files(self):
        return {s["file"] for s in self.suites}

    def name_of(self, path):
        p = Path(path).resolve()
        for s in self.suites:
            if s["file"] == p:
                return s["name"]
        return None

    def on_disk(self):
        """Every candidate suite file present in the manifest's own directory."""
        return {p.resolve() for p in self.root.glob("*.py")
                if not p.name.startswith("_")}


# --------------------------------------------------------------------------- attribution


def attribute(records, manifest):
    """suite name -> profile, from the INNERMOST enumerated-suite module frame."""
    per = {}
    orphans = []
    for r in records:
        name = None
        for fname, _ in r.get("module_frames") or []:
            n = manifest.name_of(fname)
            if n is not None:
                name = n
        if name is None:
            orphans.append({"label": r["label"], "file": r["file"]})
            continue
        sig = ",".join("%s%+d" % (c, d) for c, d in sorted(r["delta"].items()))
        per.setdefault(name, {}).setdefault(r["label"], Counter())[sig] += 1
    return per, orphans


def union_of(per):
    out = {}
    for prof in per.values():
        for lab, sigs in prof.items():
            out.setdefault(lab, Counter()).update(sigs)
    return out


def collisions(per):
    """Labels produced by more than one suite. One would mask the other in an identity set."""
    owners = {}
    for name, prof in per.items():
        for lab in prof:
            owners.setdefault(lab, set()).add(name)
    return sorted((lab, sorted(ns)) for lab, ns in owners.items() if len(ns) > 1)


# --------------------------------------------------------------------------- the harness


def run(manifest_path, orders=("reverse",), timeout=1800):
    m = Manifest(manifest_path)
    report = {"schema": "veldo.equiv/v1", "manifest": str(m.path), "entry": str(m.entry),
              "suites": m.names(), "defects": [], "per_suite": {}, "orders": []}

    # (1) the on-disk / manifest set relation, both directions
    disk = m.on_disk()
    declared = m.files()
    for extra in sorted(disk - declared):
        report["defects"].append({"defect": "SUITE_NOT_ENUMERATED", "suite": None,
                                 "detail": "%s is on disk and not in the manifest, so it"
                                 " would silently not run" % extra.name})
    for gone in sorted(declared - disk):
        report["defects"].append({"defect": "SUITE_FILE_MISSING", "suite": m.name_of(gone),
                                 "detail": "%s is enumerated and absent" % gone.name})

    # A manifest that does not agree with the disk is a malformed subject, and running an
    # equivalence experiment over one would compare two arbitrary things. The structural
    # relation is a PRECONDITION, so it reports and stops rather than reporting a crash.
    if report["defects"]:
        report["verdict"] = "DEFECTIVE"
        report["defect_names"] = sorted({d["defect"] for d in report["defects"]})
        report["note"] = ("structural defects in the manifest; the equivalence experiment"
                          " was not run because its subject is not well formed")
        return report

    # (2) the aggregate run
    roots = [m.root]
    try:
        agg = L.capture(m.entry, roots=roots, tag="agg", timeout=timeout)
        agg.reconcile()
        agg.reconcile_summary()
    except L.LabelRefusal as e:
        raise EquivRefusal("AGGREGATE_CRASHED", "%s: %s" % (m.entry, e))
    per_agg, orphans = attribute(agg.records, m)
    report["aggregate_records"] = len(agg.records)
    report["aggregate_returncode"] = agg.returncode
    for o in orphans:
        report["defects"].append({"defect": "SUITE_NOT_ENUMERATED", "suite": None,
                                 "detail": "label %r came from %s, which the manifest does"
                                 " not enumerate" % (o["label"][:80], o["file"])})
    rt = L.compare(agg.profile(), union_of(per_agg))
    if not rt["identical"]:
        report["defects"].append({"defect": "ATTRIBUTION_INCOMPLETE", "suite": None,
                                 "detail": "the per-suite projections do not re-form the"
                                 " aggregate profile: %s"
                                 % {k: len(v) for k, v in rt.items() if k != "identical"}})
    for lab, owners in collisions(per_agg):
        report["defects"].append({"defect": "SUITE_LABEL_COLLISION", "suite": ",".join(owners),
                                 "detail": "label %r is declared by %s" % (lab[:80], owners)})

    # (3) every suite alone, in a fresh interpreter
    for s in m.suites:
        entry = {"file": s["declared"], "aggregate_labels": None, "standalone_labels": None}
        if s["file"] not in disk:
            report["per_suite"][s["name"]] = dict(entry, outcome="MISSING")
            continue
        exp = per_agg.get(s["name"], {})
        try:
            alone = L.capture(s["file"], roots=roots, tag="s-" + s["name"], timeout=timeout)
            alone.reconcile()
        except L.LabelRefusal as e:
            report["per_suite"][s["name"]] = dict(
                entry, outcome="CRASHED_ALONE", refusal=e.code, detail=e.detail,
                aggregate_labels=sum(sum(c.values()) for c in exp.values()))
            report["defects"].append(
                {"defect": "PASSES_IN_AGGREGATE_FAILS_ALONE", "suite": s["name"],
                 "detail": "%s: %s" % (e.code, e.detail[:300])})
            continue
        got, _ = attribute(alone.records, m)
        got = got.get(s["name"], {})
        d = L.compare(exp, got)
        entry.update(outcome="EQUIVALENT" if d["identical"] else "DIFFERS",
                     returncode=alone.returncode,
                     aggregate_labels=sum(sum(c.values()) for c in exp.values()),
                     standalone_labels=sum(sum(c.values()) for c in got.values()),
                     missing=d["missing"][:20], added=d["added"][:20],
                     multiplicity_changed=d["multiplicity_changed"][:20],
                     signature_changed=[x[0] for x in d["signature_changed"]][:20])
        report["per_suite"][s["name"]] = entry
        if d["missing"]:
            report["defects"].append(
                {"defect": "PROVES_LESS_ALONE", "suite": s["name"],
                 "detail": "%d label(s) the aggregate proved are absent alone, first: %r"
                 % (len(d["missing"]), d["missing"][0][:120])})
        if d["added"]:
            report["defects"].append(
                {"defect": "PROVES_MORE_ALONE", "suite": s["name"],
                 "detail": "%d label(s) appear alone and not in the aggregate, first: %r"
                 % (len(d["added"]), d["added"][0][:120])})
        if d["multiplicity_changed"]:
            report["defects"].append(
                {"defect": "MULTIPLICITY_DIFFERS", "suite": s["name"],
                 "detail": "%s" % (d["multiplicity_changed"][:3],)})
        if d["signature_changed"]:
            report["defects"].append(
                {"defect": "OUTCOME_DIFFERS", "suite": s["name"],
                 "detail": "%r proved a different outcome alone"
                 % (d["signature_changed"][0][0][:120],)})

    # (4) order independence, by identity and not by exit code
    names = m.names()
    for spec in orders:
        if spec == "reverse":
            order = list(reversed(names))
        elif spec.startswith("shuffle:"):
            import random
            order = list(names)
            random.Random(int(spec.split(":", 1)[1])).shuffle(order)
        else:
            order = [x for x in spec.split(",") if x]
        rec = {"order": spec, "sequence": order}
        try:
            other = L.capture(m.entry, roots=roots, tag="ord",
                              env={ORDER_ENV: ",".join(order)}, timeout=timeout)
            other.reconcile()
            d = L.compare(agg.profile(), other.profile())
            rec.update(outcome="IDENTICAL" if d["identical"] else "DIFFERS",
                       sizes={k: len(v) for k, v in d.items() if k != "identical"},
                       missing=d["missing"][:5], added=d["added"][:5],
                       signature_changed=[x[0] for x in d["signature_changed"]][:5])
            if not d["identical"]:
                report["defects"].append(
                    {"defect": "ORDER_DEPENDENT", "suite": None,
                     "detail": "order %s changed what the run proved: %s" % (spec, rec["sizes"])})
        except L.LabelRefusal as e:
            rec.update(outcome="CRASHED", refusal=e.code, detail=e.detail[:300])
            report["defects"].append({"defect": "ORDER_DEPENDENT", "suite": None,
                                     "detail": "order %s: %s" % (spec, e.code)})
        report["orders"].append(rec)

    report["verdict"] = "EQUIVALENT" if not report["defects"] else "DEFECTIVE"
    report["defect_names"] = sorted({d["defect"] for d in report["defects"]})
    return report


# --------------------------------------------------------------------------- fixtures
# The fixture tree is the SHAPE the decomposition will take, so building it here is also
# how the shape is checked before any real file moves. Every variant is DERIVED from the
# clean tree by substitutions whose counts are asserted, so a variant cannot silently
# become a copy of the clean tree and score a false green.

FIX_FIXTURES = '''\
"""Shared fixtures and the assertion primitive. The one file every suite imports."""
PASS = 0
FAIL = 0
LOG = []


def expect(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print("  SELFTEST FAIL: %s" % name)


def report():
    print("selftest: %d passed, %d failed" % (PASS, FAIL))
    return 1 if FAIL else 0
'''

FIX_SUITE_A = '''\
import _fixtures as F

F.LOG.append("a")
F.PRIMED = True
F.expect("a: the shared fixture is importable", F.PASS >= 0)
F.expect("a: its own local holds", 1 + 1 == 2)

if __name__ == "__main__":
    raise SystemExit(F.report())
'''

FIX_SUITE_B = '''\
import _fixtures as F

F.LOG.append("b")
F.expect("b: its own local holds", "x" * 2 == "xx")
F.expect("b: a second local", sorted([2, 1]) == [1, 2])

if __name__ == "__main__":
    raise SystemExit(F.report())
'''

FIX_SUITE_C = '''\
import _fixtures as F

F.expect("c: a third suite exists", True)

if __name__ == "__main__":
    raise SystemExit(F.report())
'''

FIX_DISPATCHER = '''\
"""Thin dispatcher: it holds no assertion of its own. It reads the manifest and runs it."""
import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITES = HERE / "suites"
sys.path.insert(0, str(SUITES))
MANIFEST = json.loads((SUITES / "manifest.json").read_text())

order = [s["name"] for s in MANIFEST["suites"]]
override = os.environ.get("VELDO_SUITE_ORDER")
if override:
    order = [n for n in override.split(",") if n]
byname = {s["name"]: s["file"] for s in MANIFEST["suites"]}

import _fixtures as F

for name in order:
    spec = importlib.util.spec_from_file_location("suite_" + name, SUITES / byname[name])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

sys.exit(F.report())
'''

FIX_MANIFEST = {
    "schema": SCHEMA,
    "entry": "selftest.py",
    "fixtures": "_fixtures.py",
    "suites": [{"name": "a", "file": "a.py"}, {"name": "b", "file": "b.py"},
               {"name": "c", "file": "c.py"}],
    "ordering_dependencies": [],
}

# variant -> (list of edits, expected defect names). Ground truth BY CONSTRUCTION: each
# expectation below is derived from what the edit makes true, and where a variant carries a
# second defect the reason is written next to it. An expectation list shorter than the truth
# would make the selfcheck fail on a correct tool, which is how the first draft of this table
# was wrong.
_B2 = 'F.expect("b: a second local", sorted([2, 1]) == [1, 2])'
VARIANTS = {
    "clean": ([], []),
    # b reads a name only a binds. Alone: AttributeError. Reversed (c,b,a): b runs before a,
    # so the AGGREGATE dies too, which is order dependence and not only a standalone defect.
    "fails_alone": ([
        ("suites/b.py", 'F.expect("b: its own local holds", "x" * 2 == "xx")',
         'F.expect("b: reads what a bound", F.SET_BY_A == "a")', 1),
        ("suites/a.py", 'F.PRIMED = True', 'F.PRIMED = True\nF.SET_BY_A = "a"', 1),
    ], ["ORDER_DEPENDENT", "PASSES_IN_AGGREGATE_FAILS_ALONE"]),
    # THE DANGEROUS ONE: two green exit codes and a shorter label set. Reversed order loses
    # the same label inside the aggregate, so ORDER_DEPENDENT is equally true.
    "proves_less_alone": ([
        ("suites/b.py", _B2,
         'if getattr(F, "PRIMED", False):\n    ' + _B2, 1),
    ], ["ORDER_DEPENDENT", "PROVES_LESS_ALONE"]),
    # b emits an EXTRA label only when a did not run: growth, which a rename battery cannot
    # see. Its aggregate label set also changes under the reversed order.
    "proves_more_alone": ([
        ("suites/b.py", _B2,
         'if not getattr(F, "PRIMED", False):\n'
         '    F.expect("b: only when a did not run", True)', 1),
    ], ["ORDER_DEPENDENT", "PROVES_MORE_ALONE"]),
    # Same label, opposite outcome alone. Reversed order flips it inside the aggregate too.
    "outcome_differs": ([
        ("suites/b.py", _B2,
         'F.expect("b: a second local", getattr(F, "PRIMED", False) is True)', 1),
    ], ["ORDER_DEPENDENT", "OUTCOME_DIFFERS"]),
    # One label emitted twice in company and once alone: invisible to a SET comparison.
    "multiplicity_differs": ([
        ("suites/b.py", _B2,
         'for _i in range(2 if getattr(F, "PRIMED", False) else 1):\n'
         '    F.expect("b: a second local", True)', 1),
    ], ["MULTIPLICITY_DIFFERS", "ORDER_DEPENDENT"]),
    # Order dependence AND a standalone outcome change, because ["a","b"] holds in neither
    # the reversed aggregate nor the standalone run.
    "order_dependent": ([
        ("suites/b.py", _B2, 'F.expect("b: a second local", F.LOG == ["a", "b"])', 1),
    ], ["ORDER_DEPENDENT", "OUTCOME_DIFFERS"]),
    # ORDER DEPENDENCE ALONE, with standalone equivalence intact: sorted(LOG) == LOG holds
    # for ["b"] alone and for ["a","b"] in canonical order, and fails for ["c","b"] under the
    # reversed order. This is the variant that proves the order probe is not a restatement of
    # the standalone probe.
    "order_only": ([
        ("suites/b.py", _B2, 'F.expect("b: a second local", F.LOG == sorted(F.LOG))', 1),
        ("suites/c.py", 'import _fixtures as F\n',
         'import _fixtures as F\n\nF.LOG.append("c")\n', 1),
    ], ["ORDER_DEPENDENT"]),
    # THE DISPATCHER ASSERTING SOMETHING OF ITS OWN, which AC2 forbids outright. Its label
    # comes from a module-level frame in a file the manifest does not enumerate, which is the
    # SECOND form of SUITE_NOT_ENUMERATED, and it also breaks the attribution round trip,
    # because a label no suite claims cannot be re-formed from the per-suite projections.
    "dispatcher_asserts": ([
        ("selftest.py", "for name in order:",
         'F.expect("the dispatcher asserts something of its own", True)\n'
         "for name in order:", 1),
    ], ["ATTRIBUTION_INCOMPLETE", "SUITE_NOT_ENUMERATED"]),
    "not_enumerated": ([
        ("MANIFEST", '{"name": "c", "file": "c.py"}', "", 1),
    ], ["SUITE_NOT_ENUMERATED"]),
    "file_missing": ([
        ("DELETE", "suites/c.py", "", 1),
    ], ["SUITE_FILE_MISSING"]),
    "label_collision": ([
        ("suites/c.py", 'F.expect("c: a third suite exists", True)',
         'F.expect("b: its own local holds", True)', 1),
    ], ["SUITE_LABEL_COLLISION"]),
}


def build_fixture_tree(dest, variant="clean"):
    """Write the fixture tree. Returns the manifest path and the substitution counts."""
    if variant not in VARIANTS:
        raise ValueError("unknown variant %r" % (variant,))
    dest = Path(dest)
    (dest / "suites").mkdir(parents=True, exist_ok=True)
    files = {"selftest.py": FIX_DISPATCHER, "suites/_fixtures.py": FIX_FIXTURES,
             "suites/a.py": FIX_SUITE_A, "suites/b.py": FIX_SUITE_B,
             "suites/c.py": FIX_SUITE_C}
    manifest = json.loads(json.dumps(FIX_MANIFEST))
    edits, _expected = VARIANTS[variant]
    counts = []
    for where, find, repl, want in edits:
        if where == "MANIFEST":
            keep = [s for s in manifest["suites"]
                    if json.dumps(s, separators=(", ", ": ")) != find]
            n = len(manifest["suites"]) - len(keep)
            manifest["suites"] = keep
            counts.append({"where": where, "found": n, "wanted": want})
            continue
        if where == "DELETE":
            counts.append({"where": where, "found": 1, "wanted": want, "path": find})
            files.pop(find, None)
            continue
        src = files[where]
        n = src.count(find)
        files[where] = src.replace(find, repl)
        counts.append({"where": where, "found": n, "wanted": want})
    for rel, text in files.items():
        (dest / rel).write_text(text, encoding="utf-8")
    (dest / "suites" / "manifest.json").write_text(json.dumps(manifest, indent=1),
                                                   encoding="utf-8")
    bad = [c for c in counts if c["found"] != c["wanted"]]
    if bad:
        raise AssertionError("fixture variant %s: substitution counts wrong: %s"
                             % (variant, bad))
    return dest / "suites" / "manifest.json", counts


def expected_defects(variant):
    return list(VARIANTS[variant][1])


# --------------------------------------------------------------------------- cli


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", default=str(ROOT / "scripts" / "suites" / "manifest.json"))
    ap.add_argument("--order", action="append", default=None,
                    help="reverse | shuffle:SEED | a,b,c; repeatable")
    ap.add_argument("--json", dest="out")
    ap.add_argument("--selfcheck", action="store_true",
                    help="drive this harness over its own fixture variants")
    ap.add_argument("--emit-fixture", metavar="DIR")
    ap.add_argument("--variant", default="clean")
    args = ap.parse_args(argv)

    if args.emit_fixture:
        mp, counts = build_fixture_tree(args.emit_fixture, args.variant)
        print("fixture %s -> %s (%s)" % (args.variant, mp, counts))
        return 0

    if args.selfcheck:
        import tempfile
        bad = []
        for variant in VARIANTS:
            d = tempfile.mkdtemp(prefix="veldo-equiv-" + variant + "-")
            try:
                mp, _ = build_fixture_tree(d, variant)
                try:
                    rep = run(mp, orders=("reverse",), timeout=120)
                    got = rep["defect_names"]
                except EquivRefusal as e:
                    got = ["REFUSED:" + e.code]
                want = expected_defects(variant)
                ok = got == sorted(set(want))
                print("  %-22s want=%s got=%s %s"
                      % (variant, sorted(set(want)), got, "ok" if ok else "MISMATCH"))
                if not ok:
                    bad.append((variant, want, got))
            finally:
                shutil.rmtree(d, ignore_errors=True)
        print("selfcheck: %s" % ("all variants as declared" if not bad else "MISMATCH %s" % bad))
        return 1 if bad else 0

    rep = run(args.manifest, orders=tuple(args.order or ("reverse",)))
    if args.out:
        Path(args.out).write_text(json.dumps(rep, indent=1, sort_keys=True), encoding="utf-8")
    print("equiv: %s" % rep["verdict"])
    for d in rep["defects"]:
        print("  %s [%s] %s" % (d["defect"], d.get("suite"), d["detail"][:200]))
    return 0 if rep["verdict"] == "EQUIVALENT" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except EquivRefusal as e:
        print("REFUSED %s" % e, file=sys.stderr)
        sys.exit(2)
