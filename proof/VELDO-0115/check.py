#!/usr/bin/env python3
"""Run only VELDO-0115 checks. Invoke this driver inside the host flock.

Each mutant runs the same complete suite against disposable source copies. A
missing result, exception or incomplete case census is an invalid drive, never a
successful falsification. The real checkout is never mutated by this driver.
"""
import difflib
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PROOF = ROOT / "proof/VELDO-0115"
SUITE = ROOT / "scripts/suites/113_veldo_0115_authority_store.py"
FIXTURE = ROOT / "scripts/fixtures/authority_store.py"
LABELS = (
    "ipc/configured-store-really-changes",
    "ipc/only-the-bound-store-changes",
    "ipc/accepted-state-survives-reopen",
    "ipc/fixture-unit-controls",
)
APPLY = '        return store.execute(conn, cmd, "fixture", signer.sign, 1, committed_at=2)'
MUTANTS = {
    "AC1": (FIXTURE, APPLY,
            '        with open(Path(cfg["path"]).with_suffix(".log"), "a") as log:\n'
            '            log.write(json.dumps(cmd) + "\\n")\n'
            '        return {"committed": True, "command_id": cmd["command_id"]}', LABELS[0]),
    "AC2": (FIXTURE, APPLY, APPLY.replace("execute(conn,", "execute(peer_conn,"), LABELS[1]),
    "AC3": (ROOT / ".veldo/control_store.py",
            '        conn.execute("COMMIT")\n        conn.set_progress_handler(None, 0)',
            '        conn.execute("ROLLBACK")\n        conn.set_progress_handler(None, 0)', LABELS[2]),
}


def case(fixture, runtime, report):
    rows = {}

    def expect(name, passed):
        rows[name] = bool(passed)
        print(("PASS " if passed else "FAIL ") + name, flush=True)

    scope = {"ROOT": ROOT, "expect": expect, "V115_FIXTURE": fixture,
             "V115_RUNTIME": runtime, "V115_REPORT": report}
    exec(compile(SUITE.read_text(), str(SUITE), "exec"), scope)
    if set(rows) != set(LABELS):
        raise RuntimeError("acceptance row census differs")
    return 0 if all(rows.values()) else 1


def run(name, fixture, runtime, expected_red=None):
    report = PROOF / (name + ".json")
    report.unlink(missing_ok=True)
    proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "case",
                           str(fixture), str(runtime), str(report)], capture_output=True, text=True)
    (PROOF / (name + ".log")).write_text(proc.stdout + proc.stderr)
    if not report.is_file():
        raise RuntimeError(name + ": invalid drive, no completed report; see log")
    result = json.loads(report.read_text())
    if (not result["census_matches"] or result["completed_cases"] != result["expected_cases"]
            or result["completed_cases"] != 16 or set(result["rows"]) != set(LABELS)):
        raise RuntimeError(name + ": invalid drive, incomplete census")
    if expected_red:
        if proc.returncode != 1 or result["rows"][expected_red] is not False:
            raise RuntimeError(name + ": declared falsifier did not turn its row red")
        if not all(r["response"].get("accepted") is True for r in result["records"]):
            raise RuntimeError(name + ": falsifier did not complete accepted commands")
    elif proc.returncode != 0 or not all(result["rows"].values()):
        raise RuntimeError(name + ": unmutated checks failed; see log")
    print(name + ": " + json.dumps(result["rows"], sort_keys=True), flush=True)
    return {"exit_code": proc.returncode, "rows": result["rows"],
            "completed_cases": result["completed_cases"], "report_sha256": sha(report)}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    summary = {"base_head": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "inputs": {}, "runs": {}}
    inputs = [FIXTURE, SUITE, Path(__file__).resolve(), ROOT / "scripts/suites/manifest.json",
              ROOT / "scripts/suites/requires.json"]
    module_names = runpy.run_path(str(FIXTURE))["module_names"]
    inputs += [ROOT / ".veldo" / name for name in module_names(ROOT / ".veldo")]
    summary["inputs"] = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    # Red first, then green on the original implementation for each criterion.
    with tempfile.TemporaryDirectory(prefix="v115-mut-") as scratch:
        for name, (path, old, new, label) in MUTANTS.items():
            directory = Path(scratch) / name
            runtime = directory / "runtime"
            runtime.mkdir(parents=True)
            for source in inputs:
                if source.parent == ROOT / ".veldo":
                    shutil.copyfile(source, runtime / source.name)
            fixture = directory / "authority_store.py"
            shutil.copyfile(FIXTURE, fixture)
            original = path.read_text()
            if original.count(old) != 1:
                raise RuntimeError(name + ": mutation anchor is not unique")
            changed = original.replace(old, new)
            target = fixture if path == FIXTURE else runtime / path.name
            target.write_text(changed)
            (PROOF / (name + ".diff")).write_text("".join(difflib.unified_diff(
                original.splitlines(True), changed.splitlines(True),
                fromfile="a/" + str(path.relative_to(ROOT)),
                tofile="b/" + str(path.relative_to(ROOT)))))
            summary["runs"][name + "-red"] = run(name + "-red", fixture, runtime, label)
            # Restore even the disposable copy, then measure that exact restored source.
            target.write_text(original)
            summary["runs"][name + "-green"] = run(name + "-green", fixture, runtime)
    if summary["inputs"] != {str(p.relative_to(ROOT)): sha(p) for p in inputs}:
        raise RuntimeError("implementation changed during proof run")
    (PROOF / "results.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["case"]:
        raise SystemExit(case(*sys.argv[2:]))
    raise SystemExit(main())
