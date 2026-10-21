#!/usr/bin/env python3
"""Drive the actual suite matrix against production, the base, or bounded mutations."""
import ast
import contextlib
import io
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from measure import validators, ROOT

mode = sys.argv[1] if len(sys.argv) > 1 else "current"
suite = ROOT / "scripts/suites/106_warp_1712_required_evidence.py"
rows = []


def report(label, ok, old_refusal=False):
    rows.append({"label": label, "passed": bool(ok), "new_refusal": old_refusal})
    print(("PASS " if ok else "FAIL ") + label)


if mode == "current":
    namespace = {"ROOT": ROOT, "expect": report}
    exec(compile(suite.read_text(), str(suite), "exec"), namespace)
else:
    # Reuse the exact assertion function without executing the live-copy loop.
    tree = ast.parse(suite.read_text())
    tree.body = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef))]
    namespace = {}
    exec(compile(tree, str(suite), "exec"), namespace)
    if mode.startswith("ratchet-"):
        import difflib
        original = (ROOT / "engine/.veldo/evidence_debt.py").read_text()
        mutations = {
            "ratchet-touch": ("if touched:", "if False:"),
            "ratchet-global": ('touched = row["spec"] in changed or any(p.startswith(proof_dir) for p in changed)', 'touched = True'),
            "ratchet-register": ("if actual != expected:", "if False:"),
            "ratchet-growth": ("if previous is not None:", "if False:"),
            "ratchet-range": ("for push_range in policy._range_specs():", 'for push_range in ["HEAD~1..HEAD"]:'),
            "ratchet-reset": ("if previous is not None and not path.exists():", "if False:"),
        }
        before, after = mutations[mode]
        assert original.count(before) == 1
        mutated = original.replace(before, after)
        print("".join(difflib.unified_diff(original.splitlines(True), mutated.splitlines(True),
                                           fromfile="evidence_debt.py", tofile=mode + ".py", n=0)))
        namespace["_w1712_ratchet"](ROOT, report, mutated)
        failed = sum(not row["passed"] for row in rows)
        print(json.dumps({"mode": mode, "passed": len(rows) - failed, "failed": failed}))
        sys.exit(1 if failed else 0)
    old, new, source, proposal = validators()
    if mode == "base":
        validator = old
    else:
        needles = {
            "integration-alias": ('"integration": {"integration"}', '"integration": {"integration", "test"}'),
            "evidence-outcome": ('e.get("type") and evidence_passed(e)', 'e.get("type")'),
            "check-outcome": ('ch.get("name") and evidence_passed(ch)', 'ch.get("name")'),
            "conflicting-outcome": ('all(outcomes)', 'any(outcomes)'),
            "design-existence": ('if not passed:', 'if not reviews:'),
        }
        before, after = needles[mode]
        assert proposal.count(before) == 1
        mutated = proposal.replace(before, after)
        import difflib
        print("".join(difflib.unified_diff(proposal.splitlines(True), mutated.splitlines(True),
                                           fromfile="proposed_check.py", tofile=mode + ".py", n=0)))
        exec(compile(mutated, mode, "exec"), new.__dict__)
        validator = new
    namespace["_w1712_exercise"](validator, report)
    if mode == "base":
        namespace["_w1712_cli"](ROOT, report, source)
        assert all(not row["passed"] if row["new_refusal"] else row["passed"] for row in rows), rows
        print("Every new refusal is red on old code; every compatibility control is green.")

failed = sum(not row["passed"] for row in rows)
print(json.dumps({"mode": mode, "passed": len(rows) - failed, "failed": failed}))
sys.exit(1 if failed else 0)
