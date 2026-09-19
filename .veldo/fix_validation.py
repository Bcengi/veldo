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
DEFAULT_DEADLINE = 900        # the capsule's first run (on the reviewed commit) when the plan sets none
MIN_DERIVED_DEADLINE = 60     # the capsule's SECOND run gets twice the first's duration, never less than this
DEFAULT_ROW_DEADLINE = 1800   # a row run execs a whole suite fragment, so it gets its own budget, never
                              # a number measured from a few-line capsule (plan: row_deadline_seconds)
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


def _run(cmd: list, cwd: Path, deadline: int, env: dict | None = None, pass_fds=()) -> dict:
    """One subprocess in its own process group. On the deadline the whole group is killed; the wait for
    the group's pipes after the kill is bounded, and a helper that escaped the group and still holds
    them is recorded as children_left_running rather than waited for."""
    t0 = time.monotonic()
    e = dict(os.environ) if env is None else dict(env)
    e.pop("PWD", None)
    p = subprocess.Popen(cmd, cwd=str(cwd), env=e, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         start_new_session=True, pass_fds=pass_fds)
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


def _positive_seconds(plan: dict, key: str):
    """A number of seconds a plan may set, or None when it does not. Anything that is not a whole
    positive number is refused BY NAME before any run starts: a text value, a list, a boolean (true is
    not one second), zero and a negative are each a plan nobody can execute as written, and a negative
    would otherwise reach communicate() and turn every run into an instant deadline."""
    raw = plan.get(key)
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or isinstance(raw, float) and raw != int(raw):
        raise ValidationError(f"{key} must be a whole number of seconds, not {raw!r}")
    seconds = int(raw)
    if seconds <= 0:
        raise ValidationError(f"{key} must be positive, not {seconds}")
    return seconds


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

# The record leaves the child on a PRIVATE channel, not on its stdout, and the child ends with
# os._exit so that nothing registered to run at exit can speak after it. The rows live in a closure
# cell rather than a module global, so rebinding a name in the recorder's globals does not reach them.
# WHAT THIS DOES NOT DEFEND AGAINST, said plainly: the fragment is arbitrary code in the same process.
# It can enumerate the open descriptors, find the channel and write its own record there, and nothing
# in a process can stop code in that process. The pin is evidence about a row an author wrote
# carelessly, not a guarantee against an author who forges deliberately; that one is caught by the
# fragment being a committed file a reviewer reads. What IS closed is every accident and every cheap
# route: the fragment's own output is not the channel, the rows are not a global it can rebind, the
# record is built from references taken before it ran, and the process ends before anything registered
# at exit can speak.
RECORD_MARKER = "veldo.fixval-rows/v1"

ROW_RUNNER = r"""
import json, os, sys, types
from pathlib import Path

RECORD_MARKER = "veldo.fixval-rows/v1"


def _main():
    suites = Path(sys.argv[1]); fragment = Path(sys.argv[2]); channel = int(sys.argv[3])
    # Everything the record is built with is captured HERE, before any fragment code runs: the
    # fragment shares these module objects and can replace their attributes, and a reference taken
    # after it ran would be the fragment's. The rows live in a cell, not a module global.
    _dumps, _write, _exit, _list = json.dumps, os.write, os._exit, list
    rows = []
    def expect(name, condition):
        rows.append({"label": name, "passed": bool(condition)})
    shared = types.ModuleType("fixval_shared")
    shared.__dict__["__file__"] = str(suites / "shared.py")
    exec(compile((suites / "shared.py").read_text(), str(suites / "shared.py"), "exec"), shared.__dict__)
    shared.__dict__["expect"] = expect
    shared.__dict__["__suite_file__"] = str(fragment)
    status = "ok"
    try:
        exec(compile(fragment.read_text(), str(fragment), "exec"), shared.__dict__)
    except BaseException as e:                   # the fragment raised: the rows it reached still stand
        status = f"{type(e).__name__}: {e}"[:400]
    _write(channel, (_dumps({"marker": RECORD_MARKER, "status": status, "rows": _list(rows)}) + "\n").encode())
    sys.stdout.flush(); sys.stderr.flush()
    _exit(0)                                     # nothing at exit gets to speak after the record

_main()
"""
# The child script carries its own copy of the marker, because it runs as a file of its own; the two
# must be the same string or every record would be discarded as unmarked.
assert f'RECORD_MARKER = "{RECORD_MARKER}"' in ROW_RUNNER


def read_record(blob: str, row_label_fragment: str) -> dict:
    """The pinned row's outcome, read from the child's private channel. The record taken is the LAST
    well-formed one carrying the marker, because the runner writes its own after the fragment has
    finished and then ends the process. The pin must match exactly ONE row: none is absent, more than
    one is ambiguous, and neither is ever passed. A fragment that RAISED reports the rows it reached,
    and a pinned row it never reached is absent, not passed."""
    record = None
    for line in (blob or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict) and obj.get("marker") == RECORD_MARKER and isinstance(obj.get("rows"), list):
            record = obj
    if record is None:
        return {"row_status": "absent", "reason": "the row runner produced no record"}
    hits = [r for r in record["rows"] if isinstance(r, dict) and row_label_fragment in str(r.get("label", ""))]
    if not hits:
        return {"row_status": "absent", "fragment_status": record.get("status"),
                "reason": f"the label fragment matched none of the {len(record['rows'])} row(s) the fragment produced"}
    if len(hits) > 1:
        return {"row_status": "ambiguous", "fragment_status": record.get("status"),
                "reason": f"the label fragment matched {len(hits)} rows; the pin must name exactly one"}
    return {"row_status": "passed" if hits[0].get("passed") else "failed", "fragment_status": record.get("status")}


def run_row(tree: Path, suite: str, row_label_fragment: str, deadline: int) -> dict:
    """Run the suite fragment in the copy with a recording expect, the way drive.py does, so the named
    row's own pass or fail is read rather than inferred from a count."""
    suites = tree / "scripts" / "suites"
    fragment = _confined(suites, suite if suite.endswith(".py") else suite + ".py")
    if fragment is None:
        return {"row": row_label_fragment, "suite": suite, "row_status": "absent", "reason": "suite name is not a path inside scripts/suites"}
    if not fragment.is_file():
        return {"row": row_label_fragment, "suite": suite, "row_status": "absent", "reason": f"{suite} is not a fragment of this commit"}
    runner = tree.parent / (tree.name + ".row_runner.py")   # beside the copy, not inside it
    runner.write_text(ROW_RUNNER)
    # The channel is a FILE, never a pipe. The parent drains the child's output while it runs but reads
    # this channel only after it has exited, and a pipe holds about 64KB: a fragment with enough rows
    # would fill it and block in its write, and a process that inherited the descriptor and outlived
    # the runner would hold the parent's read open with no deadline over it. A file has neither
    # problem. It lives beside the copy, never inside it.
    channel_path = tree.parent / (tree.name + ".row_record")
    channel_fd = os.open(channel_path, os.O_RDWR | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        r = _run([sys.executable, str(runner), str(suites), str(fragment), str(channel_fd)], tree, deadline, pass_fds=(channel_fd,))
        blob = channel_path.read_bytes()
    finally:
        os.close(channel_fd)
    if r["timed_out"]:
        return {**r, "row": row_label_fragment, "suite": suite, "row_status": "deadline", "deadline_seconds": deadline}
    return {**r, "row": row_label_fragment, "suite": suite, "deadline_seconds": deadline,
            **read_record(blob.decode("utf-8", "replace"), row_label_fragment)}


# --------------------------------------------------------------------------------------------------
# The four results
# --------------------------------------------------------------------------------------------------

def _row_result(r: dict, want: str) -> dict:
    """A row run turned into a result: want is the row status that counts as passed ("passed" for the
    fresh copy, "failed" for the mutant copy). A row that was not found (absent), matched more than one
    row (ambiguous) or hit the deadline is never passed; absent and ambiguous are missing, named. A
    deadline carries children_left_running when the kill left a process behind."""
    st = r.get("row_status")
    raised = r.get("fragment_status") not in (None, "ok")
    if st == "deadline":
        status = "deadline"
    elif st in ("absent", "ambiguous"):
        status = "missing"
    elif raised:
        # The fragment stopped before its end. The rows it reached are recorded for the reader, but a
        # fragment that blew up is not evidence that the pinned row is green on a clean copy, nor that
        # the mutant is what turned it red. Stopping early is not evidence, here as for a capsule.
        status = "missing"
    else:
        status = "passed" if st == want else "failed"
    out = {"status": status, "row_status": st, "duration_seconds": r.get("duration_seconds"),
           "deadline_seconds": r.get("deadline_seconds")}
    if r.get("reason"):
        out["reason"] = r["reason"]
    if raised:
        out["fragment_status"] = r["fragment_status"]
        out.setdefault("reason", f"the fragment did not run to its end: {r['fragment_status']}")
    if r.get("children_left_running"):
        out["children_left_running"] = True
    return out


def _capsule_result(r: dict, want_reproduced: bool, reviewed_exit_code=None) -> dict:
    """A capsule run turned into a result: on the reviewed commit the defect must reproduce, on the
    fixed commit it must not.

    WHAT THIS DOES NOT DECIDE. Whether the reproduction actually exercised the fix, or died before it
    could, is not decidable from an exit code: a capsule that reports through its exit status exits
    non-zero when it works, and a capsule that crashed exits non-zero too. Two rules were written here
    and both were wrong, one refusing correct fixes forever and one closing a finding whose
    reproduction never ran. So the runner stops guessing and REPORTS: both exit codes are in the
    result, and exit_code_changed marks the fixed run whose exit status differs from the reviewed one.
    The question is a judgment, and the design already has a judge: VELDO-0103's fresh reader sees the
    diff and these results, and VELDO-0104 closes a finding only when the four results AND that
    reader's verdict agree. A finding is never closed by this function alone.

    A run whose deadline passed is deadline, and it carries children_left_running when the kill left a
    process behind; neither ever passes."""
    base = {"reproduced": r.get("reproduced"), "exit_code": r.get("exit_code"), "duration_seconds": r.get("duration_seconds")}
    if r.get("children_left_running"):
        base["children_left_running"] = True
    if r.get("timed_out"):
        return {"status": "deadline", **base}
    if not want_reproduced:
        base["reviewed_exit_code"] = reviewed_exit_code
        base["exit_code_changed"] = reviewed_exit_code is not None and r.get("exit_code") != reviewed_exit_code
    if r.get("reproduced") is want_reproduced:
        return {"status": "passed", **base}
    return {"status": "failed", **base}


def validate_finding(finding: dict, repo: str | os.PathLike, reviewed: str, fixed: str, workdir: Path, capsule_mod, deadline, row_deadline_seconds=None) -> dict:
    """The four results for one finding. Nothing here touches the repository or the worktree: every
    run happens in a copy under workdir. Any error while producing a result is that result, recorded as
    missing with its reason; nothing here aborts the validation of the other findings."""
    raw_id = finding.get("id") if isinstance(finding, dict) else None
    fid = raw_id if isinstance(raw_id, str) else f"<finding {id(finding):x}>"
    out = {"finding_id": fid, "results": {k: {"status": "missing"} for k in RESULT_KEYS}}
    if not isinstance(raw_id, str) or not FINDING_ID.fullmatch(raw_id):
        for k in RESULT_KEYS:
            out["results"][k] = {"status": "missing", "reason": "a finding needs an id that is a plain name (letters, digits, . _ -); it names run directories and may not leave them"}
        out["closed"] = False
        return out
    first_deadline = deadline or DEFAULT_DEADLINE
    rest_deadline = deadline
    row_deadline = row_deadline_seconds or deadline or DEFAULT_ROW_DEADLINE
    reviewed_exit = None
    cap_dir = finding.get("capsule")
    if isinstance(cap_dir, str) and cap_dir and Path(cap_dir).is_dir():
        for key, commit, want in (("capsule_reviewed", reviewed, True), ("capsule_fixed", fixed, False)):
            dl = first_deadline if key == "capsule_reviewed" else (rest_deadline or MIN_DERIVED_DEADLINE)
            try:
                r = capsule_mod.run_capsule(cap_dir, repo, commit, timeout=dl, workdir=workdir / f"{fid}_{key}")
                out["results"][key] = {**_capsule_result(r, want, reviewed_exit), "deadline_seconds": dl}
                if key == "capsule_reviewed":
                    reviewed_exit = r.get("exit_code")
                    if rest_deadline is None:
                        rest_deadline = max(MIN_DERIVED_DEADLINE, int(2 * (r.get("duration_seconds") or 0)) + 1)
            except capsule_mod.CapsuleError as e:
                out["results"][key] = {"status": "missing", "reason": f"capsule refused: {e}"}
            except Exception as e:  # noqa: BLE001 - a result that could not be produced is missing, by name
                out["results"][key] = {"status": "missing", "reason": f"could not run the capsule: {type(e).__name__}: {e}"}
    else:
        for key in ("capsule_reviewed", "capsule_fixed"):
            out["results"][key] = {"status": "missing", "reason": "no capsule for this finding"}
    row = finding.get("row") if isinstance(finding.get("row"), dict) else {}
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
    deadline = _positive_seconds(plan, "deadline_seconds")        # None: derived per finding
    capsule_mod = _load("fixval_capsule", Path(__file__).resolve().parent / "capsule.py")
    before = _tree_digest(worktree)
    declared = plan.get("findings")
    if not isinstance(declared, list):
        raise ValidationError("the plan's findings must be a list of objects")
    row_deadline = _positive_seconds(plan, "row_deadline_seconds")
    findings = []
    for f in declared:
        if not isinstance(f, dict):
            findings.append({"finding_id": f"<not an object: {type(f).__name__}>", "closed": False,
                             "results": {k: {"status": "missing", "reason": "the plan entry is not an object"} for k in RESULT_KEYS}})
            continue
        try:
            findings.append(validate_finding(f, repo, plan["reviewed_commit"], plan["fixed_commit"], wd, capsule_mod, deadline, row_deadline))
        except Exception as e:  # noqa: BLE001 - one finding that cannot be validated is not the others' problem
            findings.append({"finding_id": str(f.get("id")), "closed": False,
                             "results": {k: {"status": "missing", "reason": f"the finding could not be validated: {type(e).__name__}: {e}"} for k in RESULT_KEYS}})
    after = _tree_digest(worktree)
    return {
        "schema": SCHEMA,
        "repo": str(repo),
        "reviewed_commit": plan["reviewed_commit"],
        "fixed_commit": plan["fixed_commit"],
        "deadline_seconds": deadline,
        "deadline_derivation": None if deadline is not None else f"the reviewed run gets {DEFAULT_DEADLINE}s, the second twice its duration and at least {MIN_DERIVED_DEADLINE}s; rows get {DEFAULT_ROW_DEADLINE}s",
        "row_deadline_seconds": row_deadline,
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
            shutil.rmtree(runs, ignore_errors=True)
            return 2
        # The checkouts are kept. They are the evidence behind every result, the closures most of all,
        # and a record naming a directory that has been deleted is worth less than the disk it saved.
        # The record names the directory; whoever runs this removes it when they are done with it.
        (out / "fix-validation.json").write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
        print(json.dumps({"closed": rec["closed"], "open": rec["open"], "worktree_unchanged": rec["worktree_unchanged"]}))
        return 0 if not rec["open"] else 1
    print(__doc__)
    return 64


if __name__ == "__main__":
    sys.exit(main(sys.argv))
