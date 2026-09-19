"""The capsule runner for fix validation: four results per finding, each produced in a fresh copy of a
commit, never in the author's worktree (VELDO-0102).

For a finding F of a review at commit R, fixed at commit X, with a capsule (the reviewer's own
reproduction, see .veldo/capsule.py) and a pinned suite row (the author's row named by a label
fragment, with a declared mutant of one file), the four results are:

  capsule_reviewed   the capsule reproduces the defect on a fresh copy of R
  capsule_fixed      the same capsule does not reproduce it on a fresh copy of X
  row_mutant_red     the pinned row fails on a fresh copy of X with the declared mutant applied
  row_fresh_green    the pinned row passes on a fresh, unmutated copy of X

A result that could not be produced is recorded as missing, never as passed. A declared mutant whose
anchor does not match exactly once in the fixed commit is INVALID_MUTATION and the finding is not
closed; the runner never searches for another anchor. Every run is one subprocess in its own
temporary copy with a deadline; on the deadline the process group is killed and the result is
deadline. A finding is closed only when all four results hold.

Standard library only.

    python3 .veldo/fix_validation.py run <plan.json> <out-dir>
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCHEMA = "veldo.fix-validation/v1"
RESULT_KEYS = ("capsule_reviewed", "capsule_fixed", "row_mutant_red", "row_fresh_green")
DEFAULT_DEADLINE = 900
MIN_DEADLINE = 1
INVALID_MUTATION = "INVALID_MUTATION"


class ValidationError(Exception):
    """A plan the runner cannot execute as written: a missing capsule, a row without a label, a run
    directory inside the worktree."""


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _checkout(repo: str | os.PathLike, commit: str, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    ar = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", commit], capture_output=True, timeout=120)
    if ar.returncode != 0:
        raise ValidationError(f"git archive {commit} failed: {ar.stderr.decode('utf-8', 'replace')[:300]}")
    tar = subprocess.run(["tar", "-x", "-C", str(dest)], input=ar.stdout, capture_output=True, timeout=120)
    if tar.returncode != 0:
        raise ValidationError(f"untar failed: {tar.stderr.decode('utf-8', 'replace')[:300]}")


def _run(cmd: list, cwd: Path, deadline: int, env: dict | None = None) -> dict:
    """One subprocess in its own process group. On the deadline the whole group is killed."""
    t0 = time.monotonic()
    p = subprocess.Popen(cmd, cwd=str(cwd), env=env or dict(os.environ), stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        out, err = p.communicate(timeout=deadline)
        timed_out = False
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        out, err = p.communicate()
        timed_out = True
    return {"exit_code": None if timed_out else p.returncode, "timed_out": timed_out,
            "stdout": out.decode("utf-8", "replace")[-6000:], "stderr": err.decode("utf-8", "replace")[-6000:],
            "duration_seconds": round(time.monotonic() - t0, 3)}


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


# --------------------------------------------------------------------------------------------------
# Mutants
# --------------------------------------------------------------------------------------------------

def apply_mutant(tree: Path, mutant: dict) -> dict:
    """Apply a declared mutant to a fresh copy. The mutant names a file and a list of (old, new)
    edits; every old must occur exactly once. Anything else is INVALID_MUTATION, recorded with the
    file and the anchor, and the runner does not look for another anchor."""
    rel = mutant.get("file")
    edits = mutant.get("edits") or []
    if not rel or not edits:
        return {"applied": False, "status": INVALID_MUTATION, "reason": "mutant names no file or no edits"}
    target = tree / rel
    if not target.is_file():
        return {"applied": False, "status": INVALID_MUTATION, "reason": f"{rel} is not a file in the fixed commit", "file": rel}
    src = target.read_text()
    for old, new in edits:
        n = src.count(old)
        if n != 1:
            return {"applied": False, "status": INVALID_MUTATION, "reason": f"anchor matches {n} times in {rel}, expected exactly 1", "file": rel, "anchor": old[:120], "matches": n}
        src = src.replace(old, new)
    target.write_text(src)
    return {"applied": True, "status": "applied", "file": rel, "edits": len(edits)}


# --------------------------------------------------------------------------------------------------
# Rows: run the suite in the copy and read the named row
# --------------------------------------------------------------------------------------------------

ROW_RUNNER = r"""
import json, sys, types
from pathlib import Path
suites = Path(sys.argv[1]); fragment = Path(sys.argv[2])
shared = types.ModuleType("fixval_shared")
shared.__dict__["__file__"] = str(suites / "shared.py")
exec(compile((suites / "shared.py").read_text(), str(suites / "shared.py"), "exec"), shared.__dict__)
rows = []
def expect(name, condition):
    rows.append({"label": name, "passed": bool(condition)})
shared.__dict__["expect"] = expect
shared.__dict__["__suite_file__"] = str(fragment)
exec(compile(fragment.read_text(), str(fragment), "exec"), shared.__dict__)
print("FIXVAL-ROWS " + json.dumps(rows))
"""


def row_status(runner_output: str, row_label_fragment: str) -> str:
    """passed, failed or absent for the named row, read from the row runner's record of one run of the
    fragment (every row recorded, none counted). A row the fragment never produced is absent, and
    absent is never passed."""
    for line in runner_output.splitlines():
        if line.startswith("FIXVAL-ROWS "):
            try:
                rows = json.loads(line[len("FIXVAL-ROWS "):])
            except ValueError:
                return "absent"
            hits = [r for r in rows if row_label_fragment in r.get("label", "")]
            if not hits:
                return "absent"
            return "failed" if any(not r["passed"] for r in hits) else "passed"
    return "absent"


def run_row(tree: Path, suite: str, row_label_fragment: str, deadline: int) -> dict:
    """Run the suite fragment in the copy with a recording expect, the way drive.py does, so the named
    row's own pass or fail is read rather than inferred from a count."""
    suites = tree / "scripts" / "suites"
    fragment = suites / (suite if suite.endswith(".py") else suite + ".py")
    runner = tree / ".fixval_row_runner.py"
    runner.write_text(ROW_RUNNER)
    r = _run([sys.executable, str(runner), str(suites), str(fragment)], tree, deadline)
    st = "deadline" if r["timed_out"] else ("absent" if not fragment.is_file() else row_status(r["stdout"], row_label_fragment))
    return {**r, "row": row_label_fragment, "suite": suite, "row_status": st}


# --------------------------------------------------------------------------------------------------
# The four results
# --------------------------------------------------------------------------------------------------

def validate_finding(finding: dict, repo: str | os.PathLike, reviewed: str, fixed: str, workdir: Path, capsule_mod, deadline: int) -> dict:
    """The four results for one finding. Nothing here touches the repository or the worktree: every
    run happens in a copy under workdir."""
    fid = finding["id"]
    out = {"finding_id": fid, "results": {k: {"status": "missing"} for k in RESULT_KEYS}}
    cap_dir = finding.get("capsule")
    if cap_dir and Path(cap_dir).is_dir():
        for key, commit, want in (("capsule_reviewed", reviewed, True), ("capsule_fixed", fixed, False)):
            try:
                r = capsule_mod.run_capsule(cap_dir, repo, commit, timeout=deadline, workdir=workdir / f"{fid}_{key}")
                status = "deadline" if r["timed_out"] else ("passed" if r["reproduced"] is want else "failed")
                out["results"][key] = {"status": status, "reproduced": r["reproduced"], "exit_code": r["exit_code"], "duration_seconds": r["duration_seconds"]}
            except capsule_mod.CapsuleError as e:
                out["results"][key] = {"status": "missing", "reason": f"capsule refused: {e}"}
    else:
        for key in ("capsule_reviewed", "capsule_fixed"):
            out["results"][key] = {"status": "missing", "reason": "no capsule for this finding"}
    row = finding.get("row") or {}
    suite, label, mutant = row.get("suite"), row.get("label"), row.get("mutant")
    if suite and label:
        fresh = workdir / f"{fid}_row_fresh"
        _checkout(repo, fixed, fresh)
        r = run_row(fresh, suite, label, deadline)
        out["results"]["row_fresh_green"] = {"status": "passed" if r["row_status"] == "passed" else ("deadline" if r["row_status"] == "deadline" else "failed"), "row_status": r["row_status"], "duration_seconds": r["duration_seconds"]}
        if mutant:
            mut = workdir / f"{fid}_row_mutant"
            _checkout(repo, fixed, mut)
            applied = apply_mutant(mut, mutant)
            if not applied["applied"]:
                out["results"]["row_mutant_red"] = {"status": INVALID_MUTATION, **{k: v for k, v in applied.items() if k != "applied"}}
            else:
                r2 = run_row(mut, suite, label, deadline)
                out["results"]["row_mutant_red"] = {"status": "passed" if r2["row_status"] == "failed" else ("deadline" if r2["row_status"] == "deadline" else "failed"), "row_status": r2["row_status"], "mutant": applied, "duration_seconds": r2["duration_seconds"]}
        else:
            out["results"]["row_mutant_red"] = {"status": "missing", "reason": "no declared mutant for this finding"}
    else:
        for key in ("row_fresh_green", "row_mutant_red"):
            out["results"][key] = {"status": "missing", "reason": "no pinned row for this finding"}
    out["closed"] = all(out["results"][k]["status"] == "passed" for k in RESULT_KEYS)
    return out


def validate(plan: dict, workdir: str | os.PathLike | None = None) -> dict:
    """plan: {repo, worktree, reviewed_commit, fixed_commit, findings: [{id, capsule, row: {suite, label,
    mutant: {file, edits}}}], deadline_seconds}. The run directory must lie outside the worktree."""
    repo = plan["repo"]
    worktree = Path(plan.get("worktree") or repo)
    wd = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="fixval-"))
    if _inside(wd, worktree):
        raise ValidationError(f"run directory {wd} lies inside the worktree {worktree}; refusing")
    deadline = max(MIN_DEADLINE, int(plan.get("deadline_seconds") or DEFAULT_DEADLINE))
    capsule_mod = _load("fixval_capsule", Path(__file__).resolve().parent / "capsule.py")
    before = _tree_digest(worktree)
    findings = [validate_finding(f, repo, plan["reviewed_commit"], plan["fixed_commit"], wd, capsule_mod, deadline) for f in plan["findings"]]
    after = _tree_digest(worktree)
    return {
        "schema": SCHEMA,
        "repo": str(repo),
        "reviewed_commit": plan["reviewed_commit"],
        "fixed_commit": plan["fixed_commit"],
        "deadline_seconds": deadline,
        "run_directory": str(wd),
        "worktree_unchanged": before == after,
        "findings": findings,
        "closed": [f["finding_id"] for f in findings if f["closed"]],
        "open": [f["finding_id"] for f in findings if not f["closed"]],
    }


def _tree_digest(worktree: Path) -> str:
    """Digest of the worktree's tracked and untracked files (names, sizes, mtimes) so a run that
    touched it is caught."""
    import hashlib
    h = hashlib.sha256()
    if not worktree.is_dir():
        return ""
    for p in sorted(worktree.rglob("*")):
        if ".git" in p.parts or "__pycache__" in p.parts:
            continue
        if p.is_file():
            st = p.stat()
            h.update(f"{p.relative_to(worktree)}|{st.st_size}|{st.st_mtime_ns}\n".encode())
    return h.hexdigest()


def main(argv: list) -> int:
    if len(argv) >= 4 and argv[1] == "run":
        plan = json.loads(Path(argv[2]).read_text())
        out = Path(argv[3]); out.mkdir(parents=True, exist_ok=True)
        try:
            rec = validate(plan, workdir=out / "runs")
        except ValidationError as e:
            print(f"REFUSED: {e}")
            return 2
        (out / "fix-validation.json").write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
        print(json.dumps({"closed": rec["closed"], "open": rec["open"], "worktree_unchanged": rec["worktree_unchanged"]}))
        return 0 if not rec["open"] else 1
    print(__doc__)
    return 64


if __name__ == "__main__":
    sys.exit(main(sys.argv))
