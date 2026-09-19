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
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCHEMA = "veldo.fix-validation/v1"
RESULT_KEYS = ("capsule_reviewed", "capsule_fixed", "row_mutant_red", "row_fresh_green")
DEFAULT_DEADLINE = 900      # for the first run (the capsule on the reviewed commit) when the plan sets none
MIN_DERIVED_DEADLINE = 60   # the other three runs get twice the reviewed run's duration, never less than this
KILL_WAIT = 5               # seconds to wait for the killed group's pipes before recording a survivor
INVALID_MUTATION = "INVALID_MUTATION"
FINDING_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")


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
    """One subprocess in its own process group. On the deadline the whole group is killed; the wait for
    the group's pipes after the kill is bounded, and a helper that escaped the group and still holds
    them is recorded as children_left_running rather than waited for."""
    t0 = time.monotonic()
    e = dict(os.environ) if env is None else dict(env)
    e.pop("PWD", None)
    p = subprocess.Popen(cmd, cwd=str(cwd), env=e, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    survivors = False
    try:
        out, err = p.communicate(timeout=deadline)
        timed_out = False
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            out, err = p.communicate(timeout=KILL_WAIT)
        except subprocess.TimeoutExpired:
            survivors, out, err = True, b"", b""
            p.kill()
            try:
                p.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
        timed_out = True
    return {"exit_code": None if timed_out else p.returncode, "timed_out": timed_out, "children_left_running": survivors,
            "stdout": out.decode("utf-8", "replace")[-6000:], "stderr": err.decode("utf-8", "replace")[-6000:],
            "duration_seconds": round(time.monotonic() - t0, 3)}


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _confined(tree: Path, rel: str):
    """The path rel names inside the copy, or None when it would leave it: an absolute path, a `..`
    segment, or a symbolic link that resolves elsewhere. Nothing a plan names may reach outside the
    copy it is meant for."""
    if not isinstance(rel, str) or not rel or rel.startswith(("/", "\\")) or ".." in Path(rel).parts:
        return None
    target = tree / rel
    return target if _inside(target, tree) else None


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
    target = _confined(tree, rel)
    if target is None:
        return {"applied": False, "status": INVALID_MUTATION, "reason": f"{rel!r} is not a path inside the copy; a mutant may not name a path outside it", "file": rel}
    if not target.is_file():
        return {"applied": False, "status": INVALID_MUTATION, "reason": f"{rel} is not a file in the fixed commit", "file": rel}
    try:
        src = target.read_text()
    except (OSError, UnicodeDecodeError) as e:
        return {"applied": False, "status": INVALID_MUTATION, "reason": f"{rel} cannot be read as text: {e}", "file": rel}
    if not all(isinstance(e, (list, tuple)) and len(e) == 2 and all(isinstance(x, str) for x in e) and e[0] for e in edits):
        return {"applied": False, "status": INVALID_MUTATION, "reason": "every edit must be a pair of strings [old, new] with a non-empty old", "file": rel}
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
    """passed, failed, absent or ambiguous for the pinned row, read from the row runner's record of one
    run of the fragment (every row recorded, none counted). The record is the LAST FIXVAL-ROWS line,
    which the runner prints after the fragment has finished, so a line the fragment itself prints
    earlier is not read. The fragment must match exactly ONE row: none is absent, more than one is
    ambiguous, and neither is ever passed."""
    record = None
    for line in runner_output.splitlines():
        if line.startswith("FIXVAL-ROWS "):
            record = line[len("FIXVAL-ROWS "):]
    if record is None:
        return "absent"
    try:
        rows = json.loads(record)
    except ValueError:
        return "absent"
    hits = [r for r in rows if isinstance(r, dict) and row_label_fragment in str(r.get("label", ""))]
    if not hits:
        return "absent"
    if len(hits) > 1:
        return "ambiguous"
    return "passed" if hits[0].get("passed") else "failed"


def run_row(tree: Path, suite: str, row_label_fragment: str, deadline: int) -> dict:
    """Run the suite fragment in the copy with a recording expect, the way drive.py does, so the named
    row's own pass or fail is read rather than inferred from a count."""
    suites = tree / "scripts" / "suites"
    fragment = _confined(suites, suite if suite.endswith(".py") else suite + ".py")
    if fragment is None:
        return {"row": row_label_fragment, "suite": suite, "row_status": "absent", "reason": "suite name is not a path inside scripts/suites"}
    runner = tree.parent / (tree.name + ".row_runner.py")   # beside the copy, not inside it
    runner.write_text(ROW_RUNNER)
    r = _run([sys.executable, str(runner), str(suites), str(fragment)], tree, deadline)
    st = "deadline" if r["timed_out"] else ("absent" if not fragment.is_file() else row_status(r["stdout"], row_label_fragment))
    return {**r, "row": row_label_fragment, "suite": suite, "row_status": st}


# --------------------------------------------------------------------------------------------------
# The four results
# --------------------------------------------------------------------------------------------------

def _row_result(r: dict, want: str) -> dict:
    """A row run turned into a result: want is the row status that counts as passed ("passed" for the
    fresh copy, "failed" for the mutant copy). A row that was not found (absent), matched more than one
    row (ambiguous) or hit the deadline is never passed; absent and ambiguous are missing, named."""
    st = r.get("row_status")
    if st == "deadline":
        status = "deadline"
    elif st in ("absent", "ambiguous"):
        status = "missing"
    elif r.get("children_left_running"):
        status = "failed"
    else:
        status = "passed" if st == want else "failed"
    out = {"status": status, "row_status": st, "duration_seconds": r.get("duration_seconds")}
    if st in ("absent", "ambiguous"):
        out["reason"] = r.get("reason") or (f"the label fragment matched no row" if st == "absent" else "the label fragment matched more than one row; the pin must name exactly one")
    if r.get("children_left_running"):
        out["children_left_running"] = True
    return out


def _capsule_result(r: dict, want_reproduced: bool) -> dict:
    """A capsule run turned into a result. On the reviewed commit the defect must reproduce; on the
    fixed commit it must not, AND the reproduction must have run to completion: a script that crashed
    (non-zero exit with no observation) has not shown that the defect is gone, so that result is
    missing, never passed. A run that left processes behind is failed."""
    base = {"reproduced": r.get("reproduced"), "exit_code": r.get("exit_code"), "duration_seconds": r.get("duration_seconds")}
    if r.get("timed_out"):
        return {"status": "deadline", **base}
    if r.get("children_left_running"):
        return {"status": "failed", "reason": "child-processes-left-running", **base}
    if r.get("reproduced") is want_reproduced:
        if not want_reproduced and r.get("exit_code") not in (0, None) and r.get("expected_kind") != "exit_code":
            return {"status": "missing", "reason": f"the reproduction did not run to completion on the fixed commit (exit {r.get('exit_code')}); a crash is not a pass", **base}
        return {"status": "passed", **base}
    return {"status": "failed", **base}


def validate_finding(finding: dict, repo: str | os.PathLike, reviewed: str, fixed: str, workdir: Path, capsule_mod, deadline) -> dict:
    """The four results for one finding. Nothing here touches the repository or the worktree: every
    run happens in a copy under workdir. Any error while producing a result is that result, recorded as
    missing with its reason; nothing here aborts the validation of the other findings."""
    fid = str(finding.get("id"))
    out = {"finding_id": fid, "results": {k: {"status": "missing"} for k in RESULT_KEYS}}
    if not FINDING_ID.fullmatch(fid):
        for k in RESULT_KEYS:
            out["results"][k] = {"status": "missing", "reason": "finding id is not a plain name (letters, digits, . _ -); it names run directories and may not leave them"}
        out["closed"] = False
        return out
    first_deadline = deadline or DEFAULT_DEADLINE
    rest_deadline = deadline
    cap_dir = finding.get("capsule")
    if cap_dir and Path(cap_dir).is_dir():
        for key, commit, want in (("capsule_reviewed", reviewed, True), ("capsule_fixed", fixed, False)):
            dl = first_deadline if key == "capsule_reviewed" else (rest_deadline or MIN_DERIVED_DEADLINE)
            try:
                r = capsule_mod.run_capsule(cap_dir, repo, commit, timeout=dl, workdir=workdir / f"{fid}_{key}")
                r["expected_kind"] = capsule_mod.load_capsule(cap_dir)["expected"].get("kind")
                out["results"][key] = {**_capsule_result(r, want), "deadline_seconds": dl}
                if key == "capsule_reviewed" and rest_deadline is None:
                    rest_deadline = max(MIN_DERIVED_DEADLINE, int(2 * (r.get("duration_seconds") or 0)) + 1)
            except capsule_mod.CapsuleError as e:
                out["results"][key] = {"status": "missing", "reason": f"capsule refused: {e}"}
            except Exception as e:  # noqa: BLE001 - a result that could not be produced is missing, by name
                out["results"][key] = {"status": "missing", "reason": f"could not run the capsule: {type(e).__name__}: {e}"}
    else:
        for key in ("capsule_reviewed", "capsule_fixed"):
            out["results"][key] = {"status": "missing", "reason": "no capsule for this finding"}
    row_deadline = rest_deadline or MIN_DERIVED_DEADLINE
    row = finding.get("row") or {}
    suite, label, mutant = row.get("suite"), row.get("label"), row.get("mutant")
    if suite and label and isinstance(suite, str) and isinstance(label, str):
        try:
            fresh = workdir / f"{fid}_row_fresh"
            _checkout(repo, fixed, fresh)
            out["results"]["row_fresh_green"] = _row_result(run_row(fresh, suite, label, row_deadline), "passed")
        except Exception as e:  # noqa: BLE001
            out["results"]["row_fresh_green"] = {"status": "missing", "reason": f"could not run the row: {type(e).__name__}: {e}"}
        if mutant:
            try:
                mut = workdir / f"{fid}_row_mutant"
                _checkout(repo, fixed, mut)
                applied = apply_mutant(mut, mutant) if isinstance(mutant, dict) else {"applied": False, "status": INVALID_MUTATION, "reason": "mutant must be an object {file, edits}"}
                if not applied["applied"]:
                    out["results"]["row_mutant_red"] = {"status": INVALID_MUTATION, **{k: v for k, v in applied.items() if k != "applied"}}
                else:
                    out["results"]["row_mutant_red"] = {**_row_result(run_row(mut, suite, label, row_deadline), "failed"), "mutant": applied}
            except Exception as e:  # noqa: BLE001
                out["results"]["row_mutant_red"] = {"status": "missing", "reason": f"could not run the mutant row: {type(e).__name__}: {e}"}
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
    deadline = int(plan["deadline_seconds"]) if plan.get("deadline_seconds") else None   # None: derived per finding
    capsule_mod = _load("fixval_capsule", Path(__file__).resolve().parent / "capsule.py")
    before = _tree_digest(worktree)
    findings = [validate_finding(f, repo, plan["reviewed_commit"], plan["fixed_commit"], wd, capsule_mod, deadline) for f in plan["findings"]]
    after = _tree_digest(worktree)
    return {
        "schema": SCHEMA,
        "repo": str(repo),
        "reviewed_commit": plan["reviewed_commit"],
        "fixed_commit": plan["fixed_commit"],
        "deadline_seconds": deadline if deadline is not None else f"derived: {DEFAULT_DEADLINE} for the reviewed run, then twice its duration, at least {MIN_DERIVED_DEADLINE}",
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
        # The RUNS happen in a temporary directory outside every worktree; only the RECORD is written to
        # <out-dir>, which may be the proof bundle's validation directory inside the repository.
        runs = Path(tempfile.mkdtemp(prefix="fixval-runs-"))
        try:
            rec = validate(plan, workdir=runs)
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
