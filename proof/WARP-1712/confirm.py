#!/usr/bin/env python3
"""Confirm the round 3 predicate preserves corpus predictions with the explicit exit-code guard."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
report = json.loads((HERE / "core-blast-radius.json").read_text())
core = Path(report["root"])
for relative, digest in report["input_sha256"].items():
    assert hashlib.sha256((core / relative).read_bytes()).hexdigest() == digest, relative
proposal = (HERE / "proposed_check.py").read_text()
assert hashlib.sha256(proposal.encode()).hexdigest() == report["proposed_check_sha256"]
results = []
for relative in ("engine/.veldo/validate.py", ".veldo/validate.py"):
    path = ROOT / relative
    source = path.read_text()
    start = source.index("EVIDENCE_KIND_ALIASES =")
    end = source.index("\ndef spec_criterion_ids", start)
    expected = proposal.replace("    return bool(outcomes) and all(outcomes)",
        '    exit_ok = "exit_code" not in entry or (\n'
        '        type(entry["exit_code"]) is int and entry["exit_code"] == 0)\n'
        '    return bool(outcomes) and all(outcomes) and exit_ok')
    assert source[start:end] == expected, relative
    loader = importlib.util.spec_from_file_location("confirmed_validator", path)
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    manifests = {str(p.relative_to(core)) for p in module._CORPUS.corpus_in_dir(
        core / "proof", module._CORPUS.MANIFEST_PATTERN)}
    assert manifests == {p["proof"] for p in report["pairs"]} | {p["proof"] for p in report["skipped"]}
    for pair in report["pairs"]:
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                errors = module.check_required_evidence(core / pair["spec"], core / pair["proof"])
                verdict = "pass" if errors == 0 else "fail"
            except ValueError:
                verdict = "parse_error"
                # These existing syntax errors do not mask any declared evidence requirement.
                assert not re.search(r"^required_evidence:", (core / pair["spec"]).read_text(), re.M)
        assert verdict == pair["new"], pair
    results.append({"validator": relative, "pairs_confirmed": len(report["pairs"])})
print(json.dumps({"core_inputs_unchanged": len(report["input_sha256"]),
                  "proposal_plus_exit_guard_matches_both_copies": True, "results": results}, indent=2))
