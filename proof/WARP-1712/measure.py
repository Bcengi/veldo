#!/usr/bin/env python3
"""Read-only corpus comparison; executable code comes only from this Veldo worktree."""
import argparse
import collections
import contextlib
import hashlib
import io
import json
import re
from pathlib import Path
import subprocess
import sys
import types

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = "d49581b4"


def validators():
    path = ROOT / "engine/.veldo/validate.py"
    source = subprocess.check_output(
        ["git", "show", BASE + ":engine/.veldo/validate.py"], cwd=ROOT, text=True)
    old = types.ModuleType("baseline_validator")
    old.__file__ = str(path)
    exec(compile(source, str(path), "exec"), old.__dict__)
    new = types.ModuleType("proposed_validator")
    new.__dict__.update(old.__dict__)
    proposal = Path(__file__).with_name("proposed_check.py").read_text()
    exec(compile(proposal, "proposed_check.py", "exec"), new.__dict__)
    return old, new, source, proposal


def outcome(entry):
    return {k: entry[k] for k in ("status", "result") if k in entry}


def measure(root):
    old, new, source, proposal = validators()
    specs = sorted(p for p in (root / "specs").glob("*.md")
                   if p.name != "index.md" and not p.name.startswith("TEMPLATE"))
    manifests = old._CORPUS.corpus_in_dir(root / "proof", old._CORPUS.MANIFEST_PATTERN)
    reviews = old._CORPUS.corpus_in_dir(root / "proof", old._CORPUS.DESIGN_VERDICT_PATTERN)
    inputs = sorted(set(specs + list(manifests) + list(reviews)))

    def snapshot():
        return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}

    before = snapshot()
    by_id, parse_errors = {}, []
    for p in specs:
        try:
            fm = old.front_matter(p.read_text(), str(p))
        except ValueError as exc:
            parse_errors.append({"spec": str(p.relative_to(root)), "error": str(exc)})
            # Join even malformed specs, then run BOTH actual checks and record their errors.
            match = re.search(r"^id:\s*([^\s]+)\s*$", p.read_text(), re.M)
            fm = {"id": match.group(1)} if match else None
        if fm and fm.get("id"):
            if fm["id"] in by_id:
                raise ValueError("duplicate spec id: " + fm["id"])
            by_id[fm["id"]] = p
    rows, skipped = [], []
    groups = collections.defaultdict(list)
    for p in sorted(manifests):
        data = json.loads(p.read_text())
        sid = data.get("spec_id")
        if sid not in by_id:
            skipped.append({"proof": str(p.relative_to(root)), "spec_id": sid, "reason": "no matching spec"})
            continue
        spec = by_id[sid]
        verdicts, diagnostics = [], []
        for validator in (old, new):
            log = io.StringIO()
            with contextlib.redirect_stdout(log):
                try:
                    errors = validator.check_required_evidence(spec, p)
                    verdict = "pass" if errors == 0 else "fail"
                except ValueError as exc:
                    verdict = "parse_error"
                    print(str(exc))
            verdicts.append(verdict)
            diagnostics.append(log.getvalue().splitlines())
        row = {"spec": str(spec.relative_to(root)), "proof": str(p.relative_to(root)),
               "spec_id": sid, "old": verdicts[0], "new": verdicts[1]}
        if verdicts[0] != verdicts[1]:
            declared = old.front_matter(spec.read_text()).get("required_evidence", [])
            present_old, present_new = (v.evidence_kinds_in_proof(data) for v in (old, new))
            causes, losses = set(), []
            for kind in declared:
                if kind not in old.CANONICAL_KINDS:
                    continue
                if kind == "design_review":
                    if any("required design_review" in line for line in diagnostics[1]):
                        causes.add("design review without passing verdict")
                        losses.append({"kind": kind, "witnesses": []})
                    continue
                if not (old.EVIDENCE_KIND_ALIASES[kind] & present_old) or new.EVIDENCE_KIND_ALIASES[kind] & present_new:
                    continue
                witnesses = []
                entries = [("evidence", e) for c in data.get("criteria", []) for e in c.get("evidence", [])]
                entries += [("check", ch) for ch in data.get("checks", [])]
                for category, entry in entries:
                    name = entry.get("type" if category == "evidence" else "name")
                    if name not in old.EVIDENCE_KIND_ALIASES[kind]:
                        continue
                    reasons = []
                    if kind == "integration" and name == "test":
                        reasons.append("unit test presented as integration")
                    if not outcome(entry):
                        reasons.append("result absent")
                    elif not new.evidence_passed(entry):
                        reasons.append("result failed or pending")
                    if category == "check" and not new.evidence_passed(entry):
                        reasons.append("check name only")
                    causes.update(reasons)
                    witnesses.append({"entry": category, "kind": name, "outcome": outcome(entry),
                                      "ref": entry.get("ref"), "causes": reasons})
                losses.append({"kind": kind, "witnesses": witnesses})
            assert causes, row
            row.update(causes=sorted(causes), losses=losses, diagnostics=diagnostics)
            for cause in causes:
                groups[cause].append({k: row[k] for k in ("spec", "proof", "spec_id")})
        rows.append(row)
    assert before == snapshot(), "corpus input bytes changed during measurement"
    assert set(manifests) == set(old._CORPUS.corpus_in_dir(root / "proof", old._CORPUS.MANIFEST_PATTERN))
    assert len(manifests) == len(rows) + len(skipped)
    changes = [row for row in rows if row["old"] != row["new"]]
    report = {"root": str(root), "baseline": BASE,
              "baseline_validator_sha256": hashlib.sha256(source.encode()).hexdigest(),
              "proposed_check_sha256": hashlib.sha256(proposal.encode()).hexdigest(),
              "method": "Actual old and proposed check_required_evidence; declared corpus membership; spec_id join. Groups overlap. Non-passing includes all unknown outcomes, not just failed/pending. Check name only means a named check without a passing outcome.",
              "inputs_unchanged": True, "input_sha256": before,
              "totals": {"specs": len(specs), "manifests": len(manifests), "matched_pairs": len(rows),
                         "unmatched": len(skipped), "changed_pairs": len(changes),
                         "spec_parse_errors": len(parse_errors),
                         "pair_parse_errors": sum(r["old"] == "parse_error" for r in rows),
                         "old_pass": sum(r["old"] == "pass" for r in rows),
                         "new_pass": sum(r["new"] == "pass" for r in rows),
                         "by_cause": {k: len(v) for k, v in sorted(groups.items())}},
              "groups": dict(sorted(groups.items())), "skipped": skipped,
              "spec_parse_errors": parse_errors, "pairs": rows}
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    if output.is_relative_to(root):
        parser.error("report must be outside the measured repository")
    result = measure(root)
    output.write_text(json.dumps(result, indent=2) + "\n")
    lines = ["# Required-evidence impact", "", result["method"], "", "```json",
             json.dumps(result["totals"], indent=2), "```", ""]
    for cause, pairs in result["groups"].items():
        lines += ["## " + cause, "", "| Spec | Proof | Verdict |", "| --- | --- | --- |"]
        lines += ["| " + p["spec"] + " | " + p["proof"] + " | pass -> fail |" for p in pairs]
        lines.append("")
    output.with_suffix(".md").write_text("\n".join(lines))
    print(json.dumps(result["totals"], indent=2))
