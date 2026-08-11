#!/usr/bin/env python3
"""VELDO static-invariant guardrail runner (reference).

An architecture invariant is a rule that must hold across the whole source,
not at one call site: the service layer never imports the database module
directly, no file carries a forbidden token, a layer boundary is never
crossed. This runner reads a rules fixture and asserts that NO source file
violates any rule. It drives the real surface (the actual source tree on
disk) and fails on the first violating line, so a broken invariant cannot
slip through green.

  guardrail_runner.py <rules.json> <target_root>

rules.json:
  {
    "rules": [
      {
        "name": "no-db-import-outside-repository",
        "glob": "**/*.py",
        "exclude": "repository/**",
        "pattern": "^\\s*(?:import\\s+db|from\\s+db\\s+import)\\b"
      },
      {
        "name": "no-legacy-global-singleton",
        "glob": "**/*.py",
        "pattern": "\\bGLOBAL_STATE\\b"
      }
    ]
  }

Each rule needs three things: a name, a glob of files to scan (relative to
target_root, standard recursive glob so ** spans directories), and a
forbidden regex pattern. An optional exclude glob removes files the rule does
not govern (the repository layer is where the db import is allowed to live, so
"no db import outside the repository layer" is one rule over the whole tree
with the repository layer excluded). A line matching the pattern is a
violation, printed as file:line: rule-name. Exit 0 = every rule holds across
every scanned file, 1 = at least one violation, 2 = the rules file is invalid.

This is a reference artifact: an adopting repo points a guardrail gate slot at
its own rules file and source root. Stdlib only, so a reviewer reruns it with
no setup.
"""
import glob as globlib
import json
import os
import re
import sys
from pathlib import Path


def load_rules(path):
    """Parse and compile a rules file. Raises ValueError on a malformed rule so
    a broken guardrail config fails loud, never scanning nothing and passing."""
    data = json.loads(Path(path).read_text())
    rules = data.get("rules") if isinstance(data, dict) else data
    if not isinstance(rules, list) or not rules:
        raise ValueError('rules file must be a non-empty list, or {"rules": [...]}')
    out = []
    for i, r in enumerate(rules):
        if not isinstance(r, dict):
            raise ValueError(f"rule {i} is not an object")
        for key in ("name", "glob", "pattern"):
            if not r.get(key):
                raise ValueError(f"rule {i} missing required field: {key}")
        out.append({
            "name": r["name"],
            "glob": r["glob"],
            "pattern": re.compile(r["pattern"]),
            "exclude": r.get("exclude"),
        })
    return out


def _match_files(root, pattern):
    """Files under root matching a recursive glob, as absolute paths."""
    hits = globlib.glob(os.path.join(str(root), pattern), recursive=True)
    return {os.path.abspath(p) for p in hits if os.path.isfile(p)}


def scan(rules, root):
    """Return violations as (relpath, lineno, rule_name, matched_text).
    Deterministic order: by rule declaration, then file path, then line."""
    root = str(root)
    violations = []
    for rule in rules:
        targets = _match_files(root, rule["glob"])
        if rule["exclude"]:
            targets -= _match_files(root, rule["exclude"])
        for fpath in sorted(targets):
            try:
                lines = Path(fpath).read_text(errors="replace").splitlines()
            except OSError:
                continue
            for n, line in enumerate(lines, 1):
                m = rule["pattern"].search(line)
                if m:
                    rel = os.path.relpath(fpath, root)
                    violations.append((rel, n, rule["name"], m.group(0)))
    return violations


def run(rules_path, root):
    """Scan root against the rules file and report. Return an exit code."""
    try:
        rules = load_rules(rules_path)
    except (ValueError, json.JSONDecodeError, re.error) as e:
        print(f"guardrail: invalid rules file: {e}")
        return 2
    violations = scan(rules, root)
    for rel, n, name, matched in violations:
        print(f"{rel}:{n}: {name}: {matched.strip()!r}")
    if violations:
        print(f"guardrail: {len(violations)} violation(s) across {len(rules)} rule(s)")
        return 1
    print(f"guardrail: clean ({len(rules)} rule(s) hold)")
    return 0


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    return run(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    sys.exit(main())
