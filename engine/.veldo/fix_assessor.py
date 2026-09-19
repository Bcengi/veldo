"""The assessor: a fresh headless run of the logged-in Claude Code subscription that reads the whole
diff from the reviewed commit to the fixed commit, together with the review findings and the capsule
results, and answers per finding (VELDO-0103).

Three rules make it a second reader rather than an echo of the author. The brief is assembled from an
allowlist of inputs (findings, capsule results, the diff, the two commits) and nothing else; the
author's own conclusions have no field to travel in. The harness is a separate process with a clean
context and read-only tools, started through the subscription's command line, never a paid API, and
the environment it gets carries no API key variable. The verdict is parsed per finding, a finding the
verdict does not mention is not_closed, an unparseable verdict closes nothing, and a run that reports
no provenance (harness, model, wall time, tokens) closes nothing either.

Standard library only. The real harness command is `claude -p` with read-only tools; tests pass a
fake harness through the `harness` argument so that nothing is spent and the contract is what is
checked.

    python3 .veldo/fix_assessor.py run <inputs.json> <out-dir> [--harness CMD...]
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

SCHEMA_BRIEF = "veldo.assessor-brief/v1"
SCHEMA_RECORD = "veldo.assessment/v1"
STATUSES = ("closed", "not_closed", "new_defect")
API_KEY_VARIABLES = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_AUTH_TOKEN")
DEFAULT_TIMEOUT = 1800

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string"}, "status": {"type": "string", "enum": list(STATUSES)}, "reason": {"type": "string"}},
            "required": ["id", "status", "reason"]}},
        "new_defects": {"type": "array", "items": {"type": "object", "properties": {
            "title": {"type": "string"}, "file": {"type": "string"}, "reason": {"type": "string"}}, "required": ["title", "reason"]}},
    },
    "required": ["findings"],
}

QUESTIONS = (
    "For each finding: does the change restore the required behavior, or does it special-case the reproduction?",
    "Does every changed hunk belong to a listed finding? A hunk that belongs to none is a new_defect candidate.",
    "Did the change touch error handling, persistence, transaction boundaries, signatures or process coordination "
    "in a way that needs another look? Say where.",
)


class AssessorError(Exception):
    """An assessor run that cannot be trusted: a brief input outside the allowlist, a harness that did
    not run, or a verdict that cannot be read."""


# --------------------------------------------------------------------------------------------------
# The brief: assembled from an allowlist, and only from it
# --------------------------------------------------------------------------------------------------

BRIEF_INPUTS = ("reviewed_commit", "fixed_commit", "findings", "capsule_results", "diff")


def assemble_brief(inputs: dict) -> dict:
    """Build the brief record from the allowlisted inputs. Any other key is refused, so an author's
    summary, verdict or opinion has no path into the assessor's context."""
    extra = sorted(set(inputs) - set(BRIEF_INPUTS))
    if extra:
        raise AssessorError(f"brief inputs outside the allowlist: {extra}")
    for k in BRIEF_INPUTS:
        if k not in inputs:
            raise AssessorError(f"brief input missing: {k}")
    findings = inputs["findings"]
    if not isinstance(findings, list) or not findings or not all(isinstance(f, dict) and f.get("id") and f.get("text") for f in findings):
        raise AssessorError("findings must be a non-empty list of {id, text}")
    diff = inputs["diff"]
    if not isinstance(diff, str) or not diff.strip():
        raise AssessorError("diff must be the non-empty text of git diff reviewed..fixed")
    return {
        "schema": SCHEMA_BRIEF,
        "reviewed_commit": inputs["reviewed_commit"],
        "fixed_commit": inputs["fixed_commit"],
        "findings": [{"id": f["id"], "text": f["text"]} for f in findings],
        "capsule_results": inputs["capsule_results"],
        "diff": diff,
        "diff_sha256": hashlib.sha256(diff.encode("utf-8")).hexdigest(),
        "questions": list(QUESTIONS),
    }


def brief_text(brief: dict) -> str:
    """Render the brief the harness reads. Every finding id and the diff digest appear verbatim."""
    lines = [
        "You are the second reader of a fix. You did not write it and you have not seen the author's account of it.",
        "Read the whole diff from the reviewed commit to the fixed commit, then answer per finding.",
        f"Reviewed commit: {brief['reviewed_commit']}",
        f"Fixed commit: {brief['fixed_commit']}",
        f"Diff digest (sha256): {brief['diff_sha256']}",
        "",
        "FINDINGS (from the independent review of the reviewed commit):",
    ]
    for f in brief["findings"]:
        lines.append(f"- {f['id']}: {f['text']}")
    lines += ["", "CAPSULE RESULTS (the reviewer's reproduction run against both commits by a runner, not by the author):"]
    for r in brief["capsule_results"]:
        lines.append(f"- {json.dumps(r, sort_keys=True)}")
    lines += ["", "QUESTIONS:"]
    lines += [f"{i}. {q}" for i, q in enumerate(brief["questions"], 1)]
    lines += ["",
              "Answer as JSON matching the schema you were given: one entry per finding id with status closed, not_closed or "
              "new_defect and a one-line reason, plus new_defects for hunks that belong to no finding. A finding you cannot "
              "judge is not_closed.",
              "", "THE DIFF:", brief["diff"]]
    return "\n".join(lines)


# --------------------------------------------------------------------------------------------------
# The harness: a separate headless Claude Code process, read-only, clean context, no API key
# --------------------------------------------------------------------------------------------------

def harness_command(schema_path: str) -> list:
    """The real command. A fresh session (no persistence), print mode, JSON output constrained to the
    verdict schema, read-only tools only."""
    return ["claude", "-p", "--output-format", "json", "--json-schema", schema_path,
            "--no-session-persistence", "--allowedTools", "Read,Grep,Glob", "--disallowedTools", "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch"]


def clean_environment(env: dict | None = None) -> dict:
    """The environment the harness gets: the current one without any API key variable."""
    base = dict(os.environ if env is None else env)
    for k in API_KEY_VARIABLES:
        base.pop(k, None)
    return base


def run_harness(brief: dict, workdir: str | os.PathLike, harness: list | None = None, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Start the harness as a separate process in the fixed checkout, feed it the brief on stdin, and
    return what it printed together with what the controller measured (wall time, exit code)."""
    wd = Path(workdir)
    schema_path = wd / ".assessor-verdict-schema.json"
    schema_path.write_text(json.dumps(VERDICT_SCHEMA))
    cmd = list(harness) if harness else harness_command(str(schema_path))
    env = clean_environment()
    t0 = time.monotonic()
    try:
        p = subprocess.run(cmd, input=brief_text(brief), cwd=str(wd), env=env, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as e:
        raise AssessorError(f"harness not available: {e}")
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "timed out", "exit_code": None, "wall_seconds": round(time.monotonic() - t0, 3), "command": cmd, "timed_out": True}
    return {"stdout": p.stdout, "stderr": p.stderr, "exit_code": p.returncode, "wall_seconds": round(time.monotonic() - t0, 3), "command": cmd, "timed_out": False}


# --------------------------------------------------------------------------------------------------
# The verdict and the record
# --------------------------------------------------------------------------------------------------

def _extract_json(text: str):
    """The harness prints a JSON envelope in print mode; the verdict may be the whole output, a
    'structured_output' field, or a 'result' string holding JSON. Return the verdict object or None."""
    text = text.strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
    except ValueError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            obj = json.loads(text[start:end + 1])
        except ValueError:
            return None
    if isinstance(obj, dict):
        if "findings" in obj:
            return obj
        for key in ("structured_output", "result"):
            inner = obj.get(key)
            if isinstance(inner, dict) and "findings" in inner:
                return inner
            if isinstance(inner, str):
                got = _extract_json(inner)
                if got is not None:
                    return got
    return None


def parse_verdict(text: str, finding_ids: list) -> dict:
    """Per finding: closed, not_closed or new_defect with a reason. A finding the verdict does not
    mention is not_closed. Output that cannot be read closes nothing and is marked unparseable."""
    obj = _extract_json(text)
    per = {}
    if obj is None:
        for fid in finding_ids:
            per[fid] = {"status": "not_closed", "reason": "verdict unparseable"}
        return {"per_finding": per, "new_defects": [], "unparseable": True}
    seen = {}
    for entry in obj.get("findings", []) or []:
        if isinstance(entry, dict) and entry.get("id") in finding_ids and entry.get("status") in STATUSES:
            seen[entry["id"]] = {"status": entry["status"], "reason": str(entry.get("reason", ""))[:400]}
    for fid in finding_ids:
        per[fid] = seen.get(fid, {"status": "not_closed", "reason": "finding missing from the verdict"})
    new = [d for d in (obj.get("new_defects") or []) if isinstance(d, dict) and d.get("title")]
    return {"per_finding": per, "new_defects": new, "unparseable": False}


def extract_provenance(run: dict) -> dict:
    """The harness reports the model it used and its token count in its JSON envelope (print mode);
    the controller measured the wall time. Fields the run did not report are absent, not guessed."""
    prov = {"harness": "claude-code-headless", "wall_seconds": run.get("wall_seconds")}
    try:
        obj = json.loads((run.get("stdout") or "").strip())
    except ValueError:
        obj = None
    if isinstance(obj, dict):
        model = obj.get("model") or (obj.get("modelUsage") and next(iter(obj["modelUsage"]), None))
        usage = obj.get("usage") or {}
        tokens = None
        if isinstance(usage, dict) and usage:
            tokens = sum(int(v) for k, v in usage.items() if k.endswith("_tokens") and isinstance(v, (int, float)))
        if model:
            prov["model"] = str(model)
        if tokens is not None:
            prov["tokens"] = tokens
        if obj.get("duration_ms") is not None:
            prov["harness_duration_ms"] = obj.get("duration_ms")
    return prov


def provenance_complete(prov: dict) -> bool:
    return bool(prov.get("harness")) and bool(prov.get("model")) and prov.get("tokens") is not None and prov.get("wall_seconds") is not None


def assessment_record(brief: dict, run: dict) -> dict:
    """The record written into the proof bundle. Without complete provenance the record is
    provenance_missing and every finding is not_closed, whatever the verdict said."""
    ids = [f["id"] for f in brief["findings"]]
    verdict = parse_verdict(run.get("stdout") or "", ids)
    prov = extract_provenance(run)
    complete = provenance_complete(prov) and not run.get("timed_out")
    per = verdict["per_finding"]
    if not complete:
        per = {fid: {"status": "not_closed", "reason": "provenance missing from the run"} for fid in ids}
    return {
        "schema": SCHEMA_RECORD,
        "reviewed_commit": brief["reviewed_commit"],
        "fixed_commit": brief["fixed_commit"],
        "diff_sha256": brief["diff_sha256"],
        "finding_ids": ids,
        "per_finding": per,
        "new_defects": verdict["new_defects"] if complete else [],
        "unparseable": verdict["unparseable"],
        "provenance": prov,
        "provenance_missing": not provenance_complete(prov),
        "timed_out": bool(run.get("timed_out")),
        "exit_code": run.get("exit_code"),
        "closed": [fid for fid, v in per.items() if v["status"] == "closed"],
    }


def assess(inputs: dict, workdir: str | os.PathLike, harness: list | None = None, timeout: int = DEFAULT_TIMEOUT) -> dict:
    brief = assemble_brief(inputs)
    run = run_harness(brief, workdir, harness=harness, timeout=timeout)
    return assessment_record(brief, run)


def main(argv: list) -> int:
    if len(argv) >= 4 and argv[1] == "run":
        inputs = json.loads(Path(argv[2]).read_text())
        out = Path(argv[3]); out.mkdir(parents=True, exist_ok=True)
        harness = argv[argv.index("--harness") + 1:] if "--harness" in argv else None
        try:
            rec = assess(inputs, out, harness=harness)
        except AssessorError as e:
            print(f"REFUSED: {e}")
            return 2
        (out / "assessment.json").write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
        print(json.dumps({k: rec[k] for k in ("closed", "provenance_missing", "unparseable", "timed_out")}))
        return 0
    print(__doc__)
    return 64


if __name__ == "__main__":
    sys.exit(main(sys.argv))
