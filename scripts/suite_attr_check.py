#!/usr/bin/env python3
"""Refuse a suite reference to a module attribute that does not exist (repo-only check).

    python3 scripts/suite_attr_check.py

**THE BUG THIS EXISTS FOR IS A GREEN TEST OF NOTHING.** A conformance fake wrote
`TA_RR.TrackerError(...)` where the adapter's class is `TrackerAdapterError`. The name resolved to
nothing, raised `AttributeError`, the reconcile's broad `except Exception` caught it, the assertion
saw a held request and passed. The scenario was named "the tracker is unreachable" and was testing a
typo. It was written twice, a night apart, because nothing mechanical was looking.

That failure is invisible to the suite itself by construction: the test passes. Only something
reading the source against the real module can see it.

**WHY IT CHECKS ONLY UNIQUELY-BOUND ALIASES, AND WHY THAT IS THE WHOLE DESIGN.** Every suite
fragment execs into ONE shared namespace, so a module alias is a global. But `mod`, `m` and `CLI`
are also rebound in loops and function bodies, and static analysis that ignores scope reports every
one of those as missing. A first cut did exactly that: 40-odd findings, all false, which is a check
somebody switches off within a week - and then the real one ships.

So the rule is: an alias assigned EXACTLY ONCE anywhere in the corpus is unambiguous, and only those
are checked. That covers 138 aliases and ~3,900 references at ZERO false positives, and it still
catches the real bug, which was verified by seeding it back in. Narrowing the SCOPE to keep the
signal clean is right; lowering the BAR by allowlisting the noisy names would not be.

A module that cannot be imported standalone (one that needs helpers injected by its caller) is
UNVERIFIABLE, not passed, and is reported as such.
"""
import ast
import collections
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUITES = ROOT / "scripts/suites"


def _rel_of_spec_call(node):
    """`spec_from_file_location(<name>, ROOT / "rel")` -> `"rel"`, including `ROOT / "a" / "b"`."""
    f = node.func
    if not (isinstance(f, ast.Attribute) and f.attr == "spec_from_file_location"):
        return None
    if len(node.args) < 2:
        return None
    parts, cur = [], node.args[1]
    while isinstance(cur, ast.BinOp) and isinstance(cur.op, ast.Div):
        if isinstance(cur.right, ast.Constant) and isinstance(cur.right.value, str):
            parts.append(cur.right.value)
        cur = cur.left
    if isinstance(cur, ast.Name) and cur.id == "ROOT" and parts:
        return "/".join(reversed(parts))
    return None


def _spec_var_of_module_call(node):
    f = node.func
    if isinstance(f, ast.Attribute) and f.attr == "module_from_spec" and node.args:
        if isinstance(node.args[0], ast.Name):
            return node.args[0].id
    return None


def binding_counts(trees):
    """How many times each NAME is bound anywhere, in any scope. An alias bound more than once is
    ambiguous to a scope-free reader and is deliberately not checked."""
    counts = collections.Counter()
    for tree in trees.values():
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        counts[t.id] += 1
            elif isinstance(n, (ast.For, ast.comprehension)):
                tgt = getattr(n, "target", None)
                if isinstance(tgt, ast.Name):
                    counts[tgt.id] += 1
            elif isinstance(n, (ast.FunctionDef, ast.Lambda)):
                for a in getattr(n.args, "args", []):
                    counts[a.arg] += 1
    return counts


def references(order, trees, counts):
    """(file, line, alias, attr, module_rel) for every attribute read on a uniquely-bound alias.

    Spec variables are resolved IN LINE ORDER and carried ACROSS fragments, because that is what the
    runtime does: one namespace, fragments exec'd in manifest order. A temp name like `_icspec`
    genuinely is reused for two different modules in one file, and last-assignment-wins reports the
    wrong module - which was the second false-positive source before this ordered."""
    spec_paths, mod_paths, out = {}, {}, []
    for fname in order:
        events = []
        for n in ast.walk(trees[fname]):
            if (isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) and n.targets
                    and isinstance(n.targets[0], ast.Name)):
                rel = _rel_of_spec_call(n.value)
                if rel:
                    events.append((n.lineno, "spec", n.targets[0].id, rel))
                    continue
                sv = _spec_var_of_module_call(n.value)
                if sv:
                    events.append((n.lineno, "mod", n.targets[0].id, sv))
            elif isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
                events.append((n.lineno, "ref", n.value.id, n.attr))
        for line, kind, a, b in sorted(events, key=lambda e: e[0]):
            if kind == "spec":
                spec_paths[a] = b
            elif kind == "mod":
                if b in spec_paths:
                    mod_paths[a] = spec_paths[b]
            elif a in mod_paths and counts[a] == 1:
                out.append((fname, line, a, b, mod_paths[a]))
    return out


def audit():
    """Returns (missing, checked, unverifiable). `missing` is the refusal set."""
    manifest = json.loads((SUITES / "manifest.json").read_text())
    order = [s["file"] for s in manifest["suites"]]
    trees = {f: ast.parse((SUITES / f).read_text()) for f in order}
    refs = references(order, trees, binding_counts(trees))

    cache, unverifiable = {}, {}
    def load(rel):
        if rel not in cache:
            try:
                spec = importlib.util.spec_from_file_location(
                    "suiteattr_" + rel.replace("/", "_").replace(".", "_"), ROOT / rel)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                cache[rel] = mod
            except Exception as exc:                     # a module needing injected helpers
                cache[rel] = None
                unverifiable[rel] = type(exc).__name__
        return cache[rel]

    missing, checked = [], 0
    for fname, line, alias, attr, rel in refs:
        mod = load(rel)
        if mod is None:
            continue
        checked += 1
        if not hasattr(mod, attr):
            missing.append((fname, line, alias, attr, rel))
    return missing, checked, unverifiable


def main():
    missing, checked, unverifiable = audit()
    print("suite attr check: %d reference(s) on uniquely-bound module aliases" % checked)
    if unverifiable:
        print("  unverifiable (needs injected helpers, NOT passed): %s"
              % ", ".join("%s (%s)" % kv for kv in sorted(unverifiable.items())))
    for fname, line, alias, attr, rel in missing:
        print("  %s:%d  %s.%s does not exist on %s - this reference raises AttributeError, and a "
              "broad except upstream turns that into a test that passes while proving nothing"
              % (fname, line, alias, attr, rel))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
