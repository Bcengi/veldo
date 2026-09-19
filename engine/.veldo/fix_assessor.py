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

    python3 .veldo/fix_assessor.py run <inputs.json> <out-dir> [--checkout <fixed-checkout>] [--harness CMD...]
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

SCHEMA_BRIEF = "veldo.assessor-brief/v1"
SCHEMA_RECORD = "veldo.assessment/v1"
STATUSES = ("closed", "not_closed", "new_defect")
# Every variable that would route the run to a paid or foreign endpoint instead of the logged-in
# subscription: direct API keys, proxy base URLs, and the cloud-provider switches with their credentials.
API_KEY_VARIABLES = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "OPENAI_API_KEY",
                     "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
                     "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_PROFILE",
                     "GOOGLE_APPLICATION_CREDENTIALS", "ANTHROPIC_VERTEX_PROJECT_ID")
KILL_WAIT = 5
CAPSULE_RESULT_KEYS = {"finding_id", "reviewed", "fixed", "reviewed_exit_code", "fixed_exit_code"}
COMMIT_ISH = re.compile(r"[0-9a-f]{7,40}")
# A finding id names a finding. It is rendered into the brief the second reader follows, so it is a
# plain name and nothing else: free text in an id is a message to that reader from the author.
FINDING_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._\-]{0,79}")
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
    for k in ("reviewed_commit", "fixed_commit"):
        if not isinstance(inputs[k], str) or not COMMIT_ISH.fullmatch(inputs[k]):
            raise AssessorError(f"{k} must be a commit id (7 to 40 hex characters), not free text: {str(inputs[k])[:60]!r}")
    findings = inputs["findings"]
    if not isinstance(findings, list) or not findings or not all(isinstance(f, dict) and f.get("id") and f.get("text") for f in findings):
        raise AssessorError("findings must be a non-empty list of {id, text}")
    for f in findings:
        extra = sorted(set(f) - {"id", "text"})
        if extra or not isinstance(f["id"], str) or not isinstance(f["text"], str):
            raise AssessorError(f"finding {f.get('id')!r} carries fields outside {{id, text}}: {extra}; only the reviewer's finding text travels")
        if not FINDING_ID.fullmatch(f["id"]):
            raise AssessorError(f"finding id must be a plain name (letters, digits, . _ -), not {f['id'][:60]!r}")
    results = inputs["capsule_results"]
    if not isinstance(results, list):
        raise AssessorError("capsule_results must be a list of the runner's results")
    for r in results:
        if not isinstance(r, dict) or not isinstance(r.get("finding_id"), str):
            raise AssessorError("every capsule result must be an object with a finding_id")
        if not FINDING_ID.fullmatch(r["finding_id"]):
            raise AssessorError(f"capsule result finding_id must be a plain name, not {r['finding_id'][:60]!r}")
        if r["finding_id"] not in {f["id"] for f in findings}:
            raise AssessorError(f"capsule result names {r['finding_id']!r}, which is not one of the findings")
        extra = sorted(set(r) - CAPSULE_RESULT_KEYS)
        if extra:
            raise AssessorError(f"capsule result for {r['finding_id']} carries fields outside {sorted(CAPSULE_RESULT_KEYS)}: {extra}; free text has no place in the brief")
        for k in ("reviewed", "fixed"):
            if k in r and not isinstance(r[k], bool):
                raise AssessorError(f"capsule result for {r['finding_id']}: {k} must be true or false")
        for k in ("reviewed_exit_code", "fixed_exit_code"):
            if k in r and r[k] is not None and not isinstance(r[k], int):
                raise AssessorError(f"capsule result for {r['finding_id']}: {k} must be an integer or null")
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


def brief_text(brief: dict, checkout=None) -> str:
    """Render the brief the harness reads. Every finding id and the diff digest appear verbatim, and
    when a checkout of the fixed commit is reachable the brief NAMES it, because a directory the reader
    is allowed to open but never told about is a directory it will not open."""
    lines = [
        "You are the second reader of a fix. You did not write it and you have not seen the author's account of it.",
        "Read the whole diff from the reviewed commit to the fixed commit, then answer per finding.",
        (f"The fixed commit is checked out at {checkout}; you may read files there." if checkout else
         "You have the diff below and no checkout to read; judge from the diff alone."),
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

def harness_command(schema: dict | None = None, checkout: str | os.PathLike | None = None) -> list:
    """The real command: the logged-in Claude Code subscription in print mode, a fresh session with no
    persistence, JSON output constrained to the verdict schema (passed INLINE: --json-schema takes the
    schema text, not a path), restricted mode (no command-running tools, no user or project settings
    files), no MCP servers at all (an empty inline config with --strict-mcp-config), read-only tools
    allowed and every writing or fetching tool disallowed."""
    cmd = ["claude", "-p", "--output-format", "json", "--json-schema", json.dumps(schema or VERDICT_SCHEMA, sort_keys=True),
           "--no-session-persistence", "--restricted",
           "--strict-mcp-config", "--mcp-config", json.dumps({"mcpServers": {}})]
    if checkout:
        # Restricted mode confines the file tools to the working directories. The assessor is asked to
        # read the code it is judging, so the checkout of the fixed commit is named as one; without
        # this the read-only tools can reach nothing but the directory the record is written in.
        cmd += ["--add-dir", str(checkout)]
    return cmd + ["--allowedTools", "Read,Grep,Glob", "--disallowedTools", "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch"]


def clean_environment(env: dict | None = None) -> dict:
    """The environment the harness gets: the current one without any API key variable."""
    base = dict(os.environ if env is None else env)
    for k in API_KEY_VARIABLES:
        base.pop(k, None)
    return base


def run_harness(brief: dict, workdir: str | os.PathLike, harness: list | None = None, timeout: int = DEFAULT_TIMEOUT,
                checkout: str | os.PathLike | None = None) -> dict:
    """Start the harness as a separate process, feed it the brief on stdin, and return what it printed
    together with what the controller measured (wall time, exit code). It runs in the work directory,
    where the schema and the record live; the checkout of the fixed commit, when one is given, is named
    to the harness as a directory its read-only tools may reach."""
    wd = Path(workdir)
    (wd / ".assessor-verdict-schema.json").write_text(json.dumps(VERDICT_SCHEMA))   # kept beside the record for the reader
    if checkout is not None and not Path(checkout).is_dir():
        raise AssessorError(f"the checkout named for the assessor is not a directory: {checkout}")
    cmd = list(harness) if harness else harness_command(VERDICT_SCHEMA, checkout)
    env = clean_environment()
    env.pop("PWD", None)
    t0 = time.monotonic()
    try:
        # A process-group leader, so the deadline kills everything the harness started, and the wait
        # after the kill is bounded: a child that escaped the group and holds the pipes is recorded.
        p = subprocess.Popen(cmd, cwd=str(wd), env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)  # noqa: E501
    except FileNotFoundError as e:
        raise AssessorError(f"harness not available: {e}")
    survivors = False
    try:
        out, err = p.communicate(input=brief_text(brief, checkout), timeout=timeout)
        timed_out, exit_code = False, p.returncode
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            out, err = p.communicate(timeout=KILL_WAIT)
        except subprocess.TimeoutExpired:
            survivors, out, err = True, "", ""
            p.kill()
            try:
                p.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
        timed_out, exit_code = True, None
        err = (err or "") + "\ntimed out"
    return {"stdout": out or "", "stderr": err or "", "exit_code": exit_code, "wall_seconds": round(time.monotonic() - t0, 3),
            "command": cmd, "timed_out": timed_out, "children_left_running": survivors,
            "checkout": str(checkout) if checkout else None}


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
    text = (run.get("stdout") or "").strip()
    try:
        obj = json.loads(text)
    except ValueError:
        # The envelope may be surrounded by stray lines; the verdict reader tolerates that, and so
        # does the provenance reader, from the same outermost object.
        start, end = text.find("{"), text.rfind("}")
        try:
            obj = json.loads(text[start:end + 1]) if 0 <= start < end else None
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
        "checkout": run.get("checkout"),
        "closed": [fid for fid, v in per.items() if v["status"] == "closed"],
    }


def assess(inputs: dict, workdir: str | os.PathLike, harness: list | None = None, timeout: int = DEFAULT_TIMEOUT,
           checkout: str | os.PathLike | None = None) -> dict:
    brief = assemble_brief(inputs)
    run = run_harness(brief, workdir, harness=harness, timeout=timeout, checkout=checkout)
    return assessment_record(brief, run)


def main(argv: list) -> int:
    if len(argv) >= 4 and argv[1] == "run":
        inputs = json.loads(Path(argv[2]).read_text())
        out = Path(argv[3]); out.mkdir(parents=True, exist_ok=True)
        # --harness takes the REST of the argument list, so anything else is read from what precedes it.
        head = argv[:argv.index("--harness")] if "--harness" in argv else argv
        harness = argv[argv.index("--harness") + 1:] if "--harness" in argv else None
        checkout = None
        if "--checkout" in head:
            i = head.index("--checkout")
            if i + 1 >= len(head):
                print("REFUSED: --checkout needs a directory")
                return 2
            checkout = head[i + 1]
        try:
            rec = assess(inputs, out, harness=harness, checkout=checkout)
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
