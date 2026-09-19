"""VELDO-0102: the capsule runner, four results per finding in fresh copies (PLAN-0020 W2).

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, so its declared
prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 42_veldo_0102_fixval

WHAT IS UNDER TEST. .veldo/fix_validation.py over .veldo/capsule.py against a REAL two-commit git
repository built under a temporary directory with the repository's own suite layout (scripts/suites/
shared.py and a fragment): for a fixed finding all four results hold and the finding is closed, for
an unfixed finding the capsule still reproduces and the finding stays open, and a result that could
not be produced is missing, never passed (AC1); every run is one child process in a copy under the
run directory with a deadline that kills the process group, a run directory inside the worktree is
refused, and the worktree is unchanged by digest (AC2); a declared mutant whose anchor matches zero
or two times is INVALID_MUTATION with the file and anchor named, the finding is not closed, and no
other anchor is searched for (AC3). The three declared falsifiers are applied to COPIES of the organ
and required to turn their named row red while the unmutated organ passes it.
"""
import importlib.util as _v102_ilu
import json as _v102_json
import os as _v102_os
import shutil as _v102_shutil
import subprocess as _v102_sp
import sys as _v102_sys
import tempfile as _v102_tf
from pathlib import Path as _v102_Path

_v102_tmp = _v102_Path(_v102_tf.mkdtemp(prefix="v102"))
_v102_have_git = _v102_shutil.which("git") is not None and _v102_shutil.which("tar") is not None


def _v102_load(name, path):
    spec = _v102_ilu.spec_from_file_location(name, path)
    m = _v102_ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _v102_organs(tag, edits=()):
    """fix_validation.py loads capsule.py from its own directory, so a mutant copy sits beside a copy
    of capsule.py."""
    d = _v102_tmp / ("organs_" + tag)
    d.mkdir()
    _v102_shutil.copy2(ROOT / ".veldo" / "capsule.py", d / "capsule.py")
    src = (ROOT / ".veldo" / "fix_validation.py").read_text()
    for old, new in edits:
        assert src.count(old) == 1, (old[:60], src.count(old))
        src = src.replace(old, new)
    (d / "fix_validation.py").write_text(src)
    return _v102_load("v102_fixval_" + tag, d / "fix_validation.py"), _v102_load("v102_capsule_" + tag, d / "capsule.py")


FV102, CAP102 = _v102_organs("main")

if not _v102_have_git:
    expect("VELDO-0102 STOOD DOWN by name - git or tar is not installed here, so the real-checkout rows cannot run", True)
else:
    # A small repository with the suite layout: shared.py binds ROOT and expect; the fragment has rows.
    _v102_repo = _v102_tmp / "repo"
    (_v102_repo / "scripts" / "suites").mkdir(parents=True)
    _v102_env = dict(_v102_os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")

    def _v102_git(*a):
        return _v102_sp.run(["git", "-C", str(_v102_repo), *a], check=True, capture_output=True, text=True, env=_v102_env).stdout.strip()

    (_v102_repo / "scripts" / "suites" / "shared.py").write_text(
        "from pathlib import Path\nROOT = Path(__file__).resolve().parents[2]\n"
        "def expect(name, condition):\n    assert condition, name\n")
    (_v102_repo / "scripts" / "suites" / "50_rows.py").write_text(
        "import importlib.util as ilu\n"
        "spec = ilu.spec_from_file_location('organ', ROOT / 'organ.py'); organ = ilu.module_from_spec(spec); spec.loader.exec_module(organ)\n"
        "expect('ROW guard/rejects-ledger-id: the guard refuses the reserved id', organ.guard('authority:ledger') == 'refused')\n"
        "expect('ROW guard/accepts-plain-id: a plain id passes', organ.guard('output-7') == 'accepted')\n"
        "expect('ROW guard/never-mutated: a row nothing mutates', True)\n")
    _v102_git("init", "-q")
    (_v102_repo / "organ.py").write_text("def guard(entity_id):\n    return 'accepted'\n")
    _v102_git("add", "-A"); _v102_git("commit", "-q", "-m", "reviewed")
    _v102_reviewed = _v102_git("rev-parse", "HEAD")
    (_v102_repo / "organ.py").write_text("RESERVED = ('authority:',)\n\ndef guard(entity_id):\n    if entity_id.startswith(RESERVED):\n        return 'refused'\n    return 'accepted'\n")
    _v102_git("add", "-A"); _v102_git("commit", "-q", "-m", "fixed")
    _v102_fixed = _v102_git("rev-parse", "HEAD")

    def _v102_capsule(where, body, expected):
        where.mkdir(parents=True)
        (where / "repro.py").write_text(body)
        CAP102.write_manifest(where, where.name, _v102_reviewed, ["python3", CAP102.MOUNT + "/repro.py"], expected, "reviewer's observation")
        return str(where)

    _v102_cap_f1 = _v102_capsule(_v102_tmp / "cap_F-1", "import organ\nprint('ledger id ->', organ.guard('authority:ledger'))\n",
                                 {"kind": "stdout_contains", "value": "ledger id -> accepted"})
    _v102_cap_f2 = _v102_capsule(_v102_tmp / "cap_F-2", "import organ\nprint('plain ->', organ.guard('output-7'))\n",
                                 {"kind": "stdout_contains", "value": "plain -> accepted"})   # F-2 is NOT fixed: still reproduces on the fix
    _v102_mutant_ok = {"file": "organ.py", "edits": [["    if entity_id.startswith(RESERVED):\n        return 'refused'\n", ""]]}
    _v102_plan = {"repo": str(_v102_repo), "worktree": str(_v102_repo), "reviewed_commit": _v102_reviewed, "fixed_commit": _v102_fixed, "deadline_seconds": 60,
                  "findings": [
                      {"id": "F-1", "capsule": _v102_cap_f1, "row": {"suite": "50_rows", "label": "guard/rejects-ledger-id", "mutant": _v102_mutant_ok}},
                      {"id": "F-2", "capsule": _v102_cap_f2, "row": {"suite": "50_rows", "label": "guard/accepts-plain-id", "mutant": _v102_mutant_ok}},
                      {"id": "F-3", "row": {"suite": "50_rows", "label": "guard/never-mutated"}},
                  ]}
    _v102_before = FV102._tree_digest(_v102_repo)
    _v102_rec = FV102.validate(_v102_plan, workdir=_v102_tmp / "run_main")
    _v102_r1 = _v102_rec["findings"][0]["results"]; _v102_r2 = _v102_rec["findings"][1]["results"]; _v102_r3 = _v102_rec["findings"][2]["results"]

    # --- AC1 -------------------------------------------------------------------------------------
    expect("VELDO-0102 AC1 fixval/four-results-required: for the fixed finding all four results are passed and it is closed "
           "(capsule reproduces on the reviewed copy, not on the fixed copy, the pinned row reds with the mutant and is green "
           "fresh); for the unfixed finding the capsule still reproduces on the fixed copy and it stays open; for the finding "
           "without a capsule the two capsule results are missing, never passed, and it stays open",
           _v102_rec["findings"][0]["closed"] is True and all(_v102_r1[k]["status"] == "passed" for k in FV102.RESULT_KEYS)
           and _v102_rec["findings"][1]["closed"] is False and _v102_r2["capsule_fixed"]["status"] == "failed" and _v102_r2["capsule_reviewed"]["status"] == "passed"
           and _v102_rec["findings"][2]["closed"] is False and _v102_r3["capsule_reviewed"]["status"] == "missing"
           and _v102_r3["capsule_fixed"]["status"] == "missing" and _v102_r3["row_fresh_green"]["status"] == "passed"
           and _v102_r3["row_mutant_red"]["status"] == "missing"
           and _v102_rec["closed"] == ["F-1"] and _v102_rec["open"] == ["F-2", "F-3"])

    _v102_M1, _ = _v102_organs("skiprev", [('        for key, commit, want in (("capsule_reviewed", reviewed, True), ("capsule_fixed", fixed, False)):',
                                            '        out["results"]["capsule_reviewed"] = {"status": "passed", "skipped": True}\n        for key, commit, want in (("capsule_fixed", fixed, False),):')])
    # The falsifier is applied where it decides: a finding whose capsule never reproduces the defect, so only the
    # skipped run on the reviewed commit stands between it and closure.
    _v102_cap_f3 = _v102_capsule(_v102_tmp / "cap_F-3", "print('nothing to see')\n", {"kind": "stdout_contains", "value": "DEFECT"})
    _v102_plan3 = dict(_v102_plan, findings=[{"id": "F-3", "capsule": _v102_cap_f3, "row": {"suite": "50_rows", "label": "guard/rejects-ledger-id", "mutant": _v102_mutant_ok}}])
    _v102_o3 = FV102.validate(_v102_plan3, workdir=_v102_tmp / "run_o3")
    _v102_m3 = _v102_M1.validate(_v102_plan3, workdir=_v102_tmp / "run_m3")
    expect("VELDO-0102 AC1 fixval/four-results-required DRIVEN (the declared falsifier): a finding whose capsule "
           "never reproduced the defect is open on the original (capsule_reviewed failed) and closed on the copy that skips "
           "that run and reports it passed",
           _v102_o3["findings"][0]["closed"] is False and _v102_o3["findings"][0]["results"]["capsule_reviewed"]["status"] == "failed"
           and _v102_m3["findings"][0]["closed"] is True)

    # --- AC2 -------------------------------------------------------------------------------------
    _v102_after = FV102._tree_digest(_v102_repo)
    _v102_refused = False
    try:
        FV102.validate(_v102_plan, workdir=_v102_repo / "runs-inside")
    except FV102.ValidationError:
        _v102_refused = True
    _v102_cap_sleep = _v102_capsule(_v102_tmp / "cap_sleep", "import time, subprocess, sys\nsubprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\ntime.sleep(30)\nprint('DEFECT')\n",
                                    {"kind": "stdout_contains", "value": "DEFECT"})
    _v102_plan_sleep = dict(_v102_plan, deadline_seconds=1, findings=[{"id": "S", "capsule": _v102_cap_sleep}])
    import time as _v102_time
    _v102_t0 = _v102_time.monotonic()
    _v102_srec = FV102.validate(_v102_plan_sleep, workdir=_v102_tmp / "run_sleep")
    _v102_elapsed = _v102_time.monotonic() - _v102_t0
    expect("VELDO-0102 AC2 fixval/never-in-the-worktree: a run directory inside the worktree is refused before anything runs, "
           "the worktree's digest is identical before and after a full validation, no .capsule mount exists in it, and a "
           "capsule that outlives the deadline (with a grandchild process) is recorded as deadline, not passed, and the whole "
           "validation returns well before the sleep would have ended",
           _v102_refused and _v102_before == _v102_after and _v102_rec["worktree_unchanged"] is True
           and not (_v102_repo / CAP102.MOUNT).exists() and _v102_git("status", "--porcelain") == ""
           and _v102_srec["findings"][0]["results"]["capsule_reviewed"]["status"] == "deadline" and _v102_elapsed < 25)

    _v102_M2, _ = _v102_organs("inside", [('    if _inside(wd, worktree):\n        raise ValidationError', '    if False:\n        raise ValidationError')])
    _v102_m2_ok = False
    try:
        _v102_M2.validate(dict(_v102_plan, findings=[]), workdir=_v102_repo / "runs-inside-m")
        _v102_m2_ok = True   # the copy returned a record for a run directory inside the worktree
    except _v102_M2.ValidationError:
        _v102_m2_ok = False
    _v102_shutil.rmtree(_v102_repo / "runs-inside-m", ignore_errors=True)
    expect("VELDO-0102 AC2 fixval/never-in-the-worktree DRIVEN (the declared falsifier): with the inside-the-worktree refusal "
           "removed in a copy, a run directory inside the worktree is accepted on the copy and refused by the original",
           _v102_m2_ok and _v102_refused)

    # --- AC3 -------------------------------------------------------------------------------------
    _v102_mut_zero = {"file": "organ.py", "edits": [["def guard_renamed(entity_id):", "def x(entity_id):"]]}
    _v102_mut_two = {"file": "organ.py", "edits": [["return", "raise SystemExit"]]}
    _v102_plan_inv = dict(_v102_plan, findings=[
        {"id": "Z", "capsule": _v102_cap_f1, "row": {"suite": "50_rows", "label": "guard/rejects-ledger-id", "mutant": _v102_mut_zero}},
        {"id": "T", "capsule": _v102_cap_f1, "row": {"suite": "50_rows", "label": "guard/rejects-ledger-id", "mutant": _v102_mut_two}}])
    _v102_inv = FV102.validate(_v102_plan_inv, workdir=_v102_tmp / "run_inv")
    _v102_z = _v102_inv["findings"][0]["results"]["row_mutant_red"]; _v102_t = _v102_inv["findings"][1]["results"]["row_mutant_red"]
    expect("VELDO-0102 AC3 fixval/invalid-mutation-not-covered: a declared mutant whose anchor matches zero times and one whose "
           "anchor matches twice are each INVALID_MUTATION naming the file and the anchor with its match count, neither "
           "finding is closed although every other result passed, and the runner did not fall back to another anchor",
           _v102_z["status"] == FV102.INVALID_MUTATION and _v102_z.get("matches") == 0 and _v102_z.get("file") == "organ.py"
           and _v102_t["status"] == FV102.INVALID_MUTATION and _v102_t.get("matches") == 2 and _v102_t.get("anchor") == "return" and _v102_t.get("file") == "organ.py"
           and _v102_inv["closed"] == [] and _v102_inv["findings"][0]["results"]["capsule_reviewed"]["status"] == "passed")


    # --- fixes after the author's review (2026-09-19) ------------------------------------------------
    # Nothing a plan names may reach outside the copy it is meant for: not a mutant's file, not a
    # finding's id (which names the run directories).
    _v102_canary = _v102_tmp / "canary.txt"
    _v102_canary.write_text("UNTOUCHED-CANARY\n")
    _v102_mut_abs = {"file": str(_v102_canary), "edits": [["UNTOUCHED-CANARY", "TOUCHED-CANARY"]]}
    _v102_mut_dotdot = {"file": "../../organ.py", "edits": [["def guard", "def x"]]}
    _v102_plan_esc = dict(_v102_plan, findings=[
        {"id": "A", "row": {"suite": "50_rows", "label": "guard/rejects-ledger-id", "mutant": _v102_mut_abs}},
        {"id": "B", "row": {"suite": "50_rows", "label": "guard/rejects-ledger-id", "mutant": _v102_mut_dotdot}},
        {"id": "../../../escaped", "row": {"suite": "50_rows", "label": "guard/rejects-ledger-id", "mutant": _v102_mutant_ok}}])
    _v102_esc = FV102.validate(_v102_plan_esc, workdir=_v102_tmp / "run_esc")
    _v102_canary_after = _v102_canary.read_text()
    _v102_M_conf, _ = _v102_organs("unconfined", [("    target = _confined(tree, rel)\n    if target is None:", "    target = tree / rel\n    if False:")])
    _v102_M_conf.validate(dict(_v102_plan_esc, findings=_v102_plan_esc["findings"][:1]), workdir=_v102_tmp / "run_esc_m")
    _v102_canary_after_m = _v102_canary.read_text()
    _v102_canary.write_text("UNTOUCHED-CANARY\n")
    expect("VELDO-0102 AC2 fixval/paths-confined-to-the-copy: a mutant naming an absolute path outside the copy and one naming a "
           "path through .. are each INVALID_MUTATION saying the path is not inside the copy, a finding whose id would climb out "
           "of the run directory gets four missing results and is not closed, and the file outside is byte-identical afterwards; "
           "DRIVEN: a copy without the confinement rewrites that outside file",
           _v102_esc["findings"][0]["results"]["row_mutant_red"]["status"] == FV102.INVALID_MUTATION
           and "inside the copy" in _v102_esc["findings"][0]["results"]["row_mutant_red"]["reason"]
           and _v102_esc["findings"][1]["results"]["row_mutant_red"]["status"] == FV102.INVALID_MUTATION
           and all(_v102_esc["findings"][2]["results"][k]["status"] == "missing" for k in FV102.RESULT_KEYS)
           and _v102_esc["closed"] == [] and _v102_canary_after == "UNTOUCHED-CANARY\n"
           and _v102_canary_after_m == "TOUCHED-CANARY\n")

    # A reproduction that crashed on the fixed commit has not shown that the defect is gone.
    _v102_cap_crash = _v102_capsule(_v102_tmp / "cap_C", "import organ\n"
                                    "if organ.guard('authority:ledger') == 'refused':\n"
                                    "    import module_that_does_not_exist_after_the_fix\n"
                                    "print('ledger id -> accepted')\n",
                                    {"kind": "stdout_contains", "value": "ledger id -> accepted"})
    _v102_plan_crash = dict(_v102_plan, findings=[{"id": "C", "capsule": _v102_cap_crash,
                                                   "row": {"suite": "50_rows", "label": "guard/rejects-ledger-id", "mutant": _v102_mutant_ok}}])
    _v102_crash = FV102.validate(_v102_plan_crash, workdir=_v102_tmp / "run_crash")
    _v102_M_crash, _ = _v102_organs("crashpasses", [('        if not want_reproduced and r.get("exit_code") not in (0, None) and r.get("expected_kind") != "exit_code":', '        if False:')])
    _v102_crash_m = _v102_M_crash.validate(_v102_plan_crash, workdir=_v102_tmp / "run_crash_m")
    _v102_cr = _v102_crash["findings"][0]["results"]
    expect("VELDO-0102 AC1 fixval/a-crash-is-not-a-pass: a reproduction that reproduces on the reviewed commit but CRASHES on the "
           "fixed one (the branch it takes there imports a module that is not present) is recorded missing with the exit code and "
           "the reason, not passed, so the finding stays open although its two row results passed; DRIVEN: a copy that judges the "
           "fixed run by the marker alone closes the finding",
           _v102_cr["capsule_reviewed"]["status"] == "passed" and _v102_cr["capsule_fixed"]["status"] == "missing"
           and _v102_cr["capsule_fixed"]["exit_code"] not in (0, None) and "did not run to completion" in _v102_cr["capsule_fixed"]["reason"]
           and _v102_cr["row_fresh_green"]["status"] == "passed" and _v102_cr["row_mutant_red"]["status"] == "passed"
           and _v102_crash["closed"] == [] and _v102_crash_m["closed"] == ["C"])

    # An error while producing one result is that result, recorded as missing; the other findings still run.
    _v102_cap_nobin = _v102_tmp / "cap_N"
    _v102_cap_nobin.mkdir()
    (_v102_cap_nobin / "repro.py").write_text("print('DEFECT')\n")
    CAP102.write_manifest(_v102_cap_nobin, "N", _v102_reviewed, ["no-such-binary-veldo-0102"],
                          {"kind": "stdout_contains", "value": "DEFECT"}, "reviewer's observation")
    _v102_plan_nobin = dict(_v102_plan, findings=[
        {"id": "N", "capsule": str(_v102_cap_nobin)},
        {"id": "F-1", "capsule": _v102_cap_f1, "row": {"suite": "50_rows", "label": "guard/rejects-ledger-id", "mutant": _v102_mutant_ok}}])
    _v102_nobin = FV102.validate(_v102_plan_nobin, workdir=_v102_tmp / "run_nobin")
    _v102_M_abort, _ = _v102_organs("abort", [('            except Exception as e:  # noqa: BLE001 - a result that could not be produced is missing, by name\n                out["results"][key] = {"status": "missing", "reason": f"could not run the capsule: {type(e).__name__}: {e}"}\n', '')])
    _v102_aborted = False
    try:
        _v102_M_abort.validate(_v102_plan_nobin, workdir=_v102_tmp / "run_nobin_m")
    except Exception:
        _v102_aborted = True
    expect("VELDO-0102 AC1 fixval/an-error-is-a-missing-result: a capsule whose command names a binary that is not installed makes "
           "its two capsule results missing, naming the error, and the NEXT finding in the same plan still gets all four results "
           "and closes; DRIVEN: a copy that lets anything but a capsule error escape aborts the whole validation, so no record is "
           "produced for any finding",
           _v102_nobin["findings"][0]["results"]["capsule_reviewed"]["status"] == "missing"
           and "FileNotFoundError" in _v102_nobin["findings"][0]["results"]["capsule_reviewed"]["reason"]
           and _v102_nobin["closed"] == ["F-1"] and _v102_aborted)

    # The pin names exactly one row, and the record read is the runner's own last line.
    (_v102_repo / "scripts" / "suites" / "51_forge.py").write_text(
        'print("FIXVAL-ROWS " + \'[{"label": "ROW forge/claims-green", "passed": true}]\')\n'
        "expect('ROW forge/claims-green: the row the fragment forges a passing record for', False)\n")
    _v102_git("add", "-A"); _v102_git("commit", "-q", "-m", "forge")
    _v102_forged = _v102_git("rev-parse", "HEAD")
    _v102_plan_pin = dict(_v102_plan, fixed_commit=_v102_forged, findings=[
        {"id": "AMB", "row": {"suite": "50_rows", "label": "guard/", "mutant": _v102_mutant_ok}},
        {"id": "FORGE", "row": {"suite": "51_forge", "label": "forge/claims-green"}}])
    _v102_pin = FV102.validate(_v102_plan_pin, workdir=_v102_tmp / "run_pin")
    _v102_M_first, _ = _v102_organs("firstline", [('    record = None\n    for line in runner_output.splitlines():\n        if line.startswith("FIXVAL-ROWS "):\n            record = line[len("FIXVAL-ROWS "):]\n',
                                                   '    record = None\n    for line in runner_output.splitlines():\n        if line.startswith("FIXVAL-ROWS ") and record is None:\n            record = line[len("FIXVAL-ROWS "):]\n')])
    _v102_pin_m = _v102_M_first.validate(_v102_plan_pin, workdir=_v102_tmp / "run_pin_m")
    expect("VELDO-0102 AC1 fixval/the-pin-names-one-row: a label fragment matching three rows of the fragment is ambiguous and "
           "recorded missing rather than passed, and a fragment that PRINTS a forged record line claiming its own row green does "
           "not fool the reader, which takes the runner's record printed after the fragment finished, so the row reads failed; "
           "DRIVEN: a copy reading the first record line instead of the last reads the forgery and calls the row green",
           _v102_pin["findings"][0]["results"]["row_fresh_green"]["status"] == "missing"
           and _v102_pin["findings"][0]["results"]["row_fresh_green"]["row_status"] == "ambiguous"
           and _v102_pin["findings"][1]["results"]["row_fresh_green"]["status"] == "failed"
           and _v102_pin_m["findings"][1]["results"]["row_fresh_green"]["status"] == "passed")

    # The RUNS never happen inside a worktree; the RECORD may be written into the proof bundle.
    _v102_out = _v102_repo / "proof" / "VELDO-9102" / "validation"
    _v102_plan_file = _v102_tmp / "plan.json"
    _v102_plan_file.write_text(_v102_json.dumps(dict(_v102_plan, findings=[_v102_plan["findings"][0]])))
    _v102_rc = FV102.main(["fix_validation.py", "run", str(_v102_plan_file), str(_v102_out)])
    _v102_written = (_v102_out / "fix-validation.json").is_file()
    _v102_run_dir = _v102_json.loads((_v102_out / "fix-validation.json").read_text())["run_directory"] if _v102_written else ""
    _v102_M_runs, _ = _v102_organs("runsinside", [('        runs = Path(tempfile.mkdtemp(prefix="fixval-runs-"))', '        runs = out / "runs"')])
    _v102_rc_m = _v102_M_runs.main(["fix_validation.py", "run", str(_v102_plan_file), str(_v102_out / "m")])
    expect("VELDO-0102 AC2 fixval/record-inside-runs-outside: the command writes its record into a directory inside the repository "
           "(a proof bundle's validation directory, as the spec's rollback describes) while the runs themselves happen outside "
           "every worktree, and the record names that outside run directory; DRIVEN: a copy that runs where it writes is REFUSED "
           "and writes no record at all",
           _v102_rc == 0 and _v102_written and not _v102_run_dir.startswith(str(_v102_repo))
           and _v102_rc_m == 2 and not (_v102_out / "m" / "fix-validation.json").exists())

    _v102_M3, _ = _v102_organs("covered", [('                out["results"]["row_mutant_red"] = {"status": INVALID_MUTATION, **{k: v for k, v in applied.items() if k != "applied"}}',
                                             '                out["results"]["row_mutant_red"] = {**{k: v for k, v in applied.items() if k != "applied"}, "status": "passed"}')])
    _v102_m3_inv = _v102_M3.validate(_v102_plan_inv, workdir=_v102_tmp / "run_inv_m")
    expect("VELDO-0102 AC3 fixval/invalid-mutation-not-covered DRIVEN (the declared falsifier): with a mutant that does not "
           "apply treated as covered in a copy, both findings are closed on the copy and neither on the original",
           _v102_m3_inv["closed"] == ["Z", "T"] and _v102_inv["closed"] == [])
