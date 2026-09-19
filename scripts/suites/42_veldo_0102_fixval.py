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
    # The source blocks the mutants below replace, kept here so every row can reach them.
    COMMIT_GUARD_42 = '        if not isinstance(value, str) or not COMMIT_ISH.fullmatch(value):'
    PIPE_BLOCK_42 = '    channel_fd, channel_path = tempfile.mkstemp(prefix="fixval-rows-")\n    os.unlink(channel_path)\n    try:\n        r = _run([sys.executable, str(runner), str(suites), str(fragment), str(channel_fd)], tree, deadline, pass_fds=(channel_fd,))\n        os.lseek(channel_fd, 0, os.SEEK_SET)\n        blob = b""\n        while True:\n            chunk = os.read(channel_fd, 65536)\n            if not chunk:\n                break\n            blob += chunk\n    finally:\n        os.close(channel_fd)\n'
    PIPE_MUTANT_42 = '    read_fd, write_fd = os.pipe()\n    try:\n        r = _run([sys.executable, str(runner), str(suites), str(fragment), str(write_fd)], tree, deadline, pass_fds=(write_fd,))\n        os.close(write_fd)\n        write_fd = None\n        blob = b""\n        while True:\n            chunk = os.read(read_fd, 65536)\n            if not chunk:\n                break\n            blob += chunk\n    finally:\n        if write_fd is not None:\n            os.close(write_fd)\n        os.close(read_fd)\n'
    NAMED_CHANNEL_42 = '    channel_path = tree.parent / (tree.name + ".row_record")\n    channel_fd = os.open(channel_path, os.O_RDWR | os.O_CREAT | os.O_TRUNC, 0o600)\n    try:\n        r = _run([sys.executable, str(runner), str(suites), str(fragment), str(channel_fd)], tree, deadline, pass_fds=(channel_fd,))\n        blob = channel_path.read_bytes()\n    finally:\n        os.close(channel_fd)\n'

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
           _v102_rec["findings"][0]["all_results_passed"] is True and all(_v102_r1[k]["status"] == "passed" for k in FV102.RESULT_KEYS)
           and _v102_rec["findings"][1]["all_results_passed"] is False and _v102_r2["capsule_fixed"]["status"] == "failed" and _v102_r2["capsule_reviewed"]["status"] == "passed"
           and _v102_rec["findings"][2]["all_results_passed"] is False and _v102_r3["capsule_reviewed"]["status"] == "missing"
           and _v102_r3["capsule_fixed"]["status"] == "missing" and _v102_r3["row_fresh_green"]["status"] == "passed"
           and _v102_r3["row_mutant_red"]["status"] == "missing"
           and _v102_rec["all_results_passed"] == ["F-1"] and _v102_rec["open"] == ["F-2", "F-3"] and _v102_rec["closes_findings"] is False)

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
           _v102_o3["findings"][0]["all_results_passed"] is False and _v102_o3["findings"][0]["results"]["capsule_reviewed"]["status"] == "failed"
           and _v102_m3["findings"][0]["all_results_passed"] is True)

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
           and _v102_inv["all_results_passed"] == [] and _v102_inv["findings"][0]["results"]["capsule_reviewed"]["status"] == "passed")


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
           and _v102_esc["all_results_passed"] == [] and _v102_canary_after == "UNTOUCHED-CANARY\n"
           and _v102_canary_after_m == "TOUCHED-CANARY\n")

    # Whether a reproduction exercised the fix or died before it could is NOT decidable from an exit
    # code, and the runner no longer guesses: it reports both exit codes and marks the fixed run whose
    # exit status differs. The judgment belongs to the assessor, and a landing needs its verdict too.
    _v102_cap_crash = _v102_capsule(_v102_tmp / "cap_C", "import organ\n"
                                    "if organ.guard('authority:ledger') == 'refused':\n"
                                    "    import module_that_does_not_exist_after_the_fix\n"
                                    "print('ledger id -> accepted')\n",
                                    {"kind": "stdout_contains", "value": "ledger id -> accepted"})
    _v102_plan_crash = dict(_v102_plan, findings=[{"id": "C", "capsule": _v102_cap_crash,
                                                   "row": {"suite": "50_rows", "label": "guard/rejects-ledger-id", "mutant": _v102_mutant_ok}}])
    _v102_crash = FV102.validate(_v102_plan_crash, workdir=_v102_tmp / "run_crash")
    _v102_cr = _v102_crash["findings"][0]["results"]

    # The capsule that reports through its exit status: it raises TypeError while the defect is there
    # and a clean ValueError after the fix. Both runs exit 1 and the fix is CORRECT.
    _v102_cap_err = _v102_capsule(_v102_tmp / "cap_E", "import organ\n"
                                  "if organ.guard('authority:ledger') == 'accepted':\n"
                                  "    raise TypeError('the ledger id was accepted')\n"
                                  "raise ValueError('refused cleanly')\n",
                                  {"kind": "stderr_contains", "value": "TypeError"})
    _v102_plan_err = dict(_v102_plan, findings=[{"id": "E", "capsule": _v102_cap_err,
                                                 "row": {"suite": "50_rows", "label": "guard/rejects-ledger-id", "mutant": _v102_mutant_ok}}])
    _v102_err = FV102.validate(_v102_plan_err, workdir=_v102_tmp / "run_err")
    _v102_er = _v102_err["findings"][0]["results"]
    _v102_M_silent, _ = _v102_organs("silentexit", [
        ('        base["exit_code_changed"] = reviewed_exit_code is not None and r.get("exit_code") != reviewed_exit_code',
         '        base["exit_code_changed"] = False')])
    _v102_crash_silent = _v102_M_silent.validate(_v102_plan_crash, workdir=_v102_tmp / "run_crash_s")
    expect("VELDO-0102 AC1 fixval/exit-codes-are-reported-not-judged: a reproduction that ran cleanly while the defect was "
           "present and then crashed on the fix, and one that exits non-zero on both because that is how it reports, are both "
           "recorded by their observation alone, so neither is refused and neither is silently excused; each fixed result "
           "carries the reviewed run's exit code beside its own and marks exit_code_changed, which is true for the crash and "
           "false for the one that reports the same way twice, so the assessor that decides can see it; DRIVEN: a copy that "
           "never marks the change leaves the crash indistinguishable from the working fix",
           _v102_cr["capsule_reviewed"]["status"] == "passed" and _v102_cr["capsule_reviewed"]["exit_code"] == 0
           and _v102_cr["capsule_fixed"]["status"] == "passed" and _v102_cr["capsule_fixed"]["exit_code"] not in (0, None)
           and _v102_cr["capsule_fixed"]["reviewed_exit_code"] == 0 and _v102_cr["capsule_fixed"]["exit_code_changed"] is True
           and _v102_er["capsule_reviewed"]["exit_code"] == 1 and _v102_er["capsule_fixed"]["exit_code"] == 1
           and _v102_er["capsule_fixed"]["exit_code_changed"] is False and _v102_err["all_results_passed"] == ["E"]
           and _v102_crash_silent["findings"][0]["results"]["capsule_fixed"]["exit_code_changed"] is False)

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
    _v102_M_abort, _ = _v102_organs("abort", [
        ('            except Exception as e:  # noqa: BLE001 - a result that could not be produced is missing, by name\n                out["results"][key] = {"status": "missing", "reason": f"could not run the capsule: {type(e).__name__}: {e}"}\n', ''),
        ('        except Exception as e:  # noqa: BLE001 - one finding that cannot be validated is not the others\' problem\n', '        except ValidationError as e:\n')])
    _v102_aborted = False
    try:
        _v102_M_abort.validate(_v102_plan_nobin, workdir=_v102_tmp / "run_nobin_m")
    except Exception:
        _v102_aborted = True
    _v102_plan_shapes = dict(_v102_plan, findings=[
        {"id": "S1", "row": "50_rows"},
        {"id": "S2", "capsule": {"dir": "x"}},
        "not an object at all",
        {"capsule": _v102_cap_f1},
        {"id": "F-1", "capsule": _v102_cap_f1, "row": {"suite": "50_rows", "label": "guard/rejects-ledger-id", "mutant": _v102_mutant_ok}}])
    _v102_shapes = FV102.validate(_v102_plan_shapes, workdir=_v102_tmp / "run_shapes")
    expect("VELDO-0102 AC1 fixval/an-error-is-a-missing-result: a capsule whose command names a binary that is not installed "
           "makes its two capsule results missing, naming the error, and the NEXT finding in the same plan still gets all four "
           "results and closes; a plan whose entries are the wrong SHAPE (a row given as a string, a capsule given as an "
           "object, an entry that is not an object, a finding with no id) produces four missing results each, naming what is "
           "wrong, and the well-formed finding beside them still closes; DRIVEN: a copy that lets anything but a validation "
           "error escape either guard aborts the whole run, so no record is produced for any finding",
           _v102_nobin["findings"][0]["results"]["capsule_reviewed"]["status"] == "missing"
           and "FileNotFoundError" in _v102_nobin["findings"][0]["results"]["capsule_reviewed"]["reason"]
           and _v102_nobin["all_results_passed"] == ["F-1"] and _v102_aborted
           and len(_v102_shapes["findings"]) == 5 and _v102_shapes["all_results_passed"] == ["F-1"]
           and all(_v102_shapes["findings"][i]["results"][k]["status"] == "missing"
                   for i in range(4) for k in FV102.RESULT_KEYS))

    # The pin names exactly one row, and the record does not travel on the fragment's stdout, where the
    # fragment could write it. The forging fragment below uses the three ways a fragment can speak:
    # it prints a marked record on stdout, it rebinds the recorder's own globals, and it registers a
    # handler to speak at exit. Its row is honestly false and must read failed through all of them.
    (_v102_repo / "scripts" / "suites" / "51_forge.py").write_text(
        "import atexit, json, os\n"
        "FORGED = [{'label': 'ROW forge/claims-green', 'passed': True}]\n"
        "RECORD = {'marker': 'veldo.fixval-rows/v1', 'status': 'ok', 'rows': FORGED}\n"
        "print(json.dumps(RECORD))\n"
        "expect('ROW forge/claims-green: the row the fragment forges a passing record for', False)\n"
        "try:\n"
        "    expect.__globals__['rows'] = FORGED\n"
        "except Exception:\n"
        "    pass\n"
        "_real_dumps = json.dumps\n"
        "def _fake_dumps(obj, *a, **k):\n"
        "    if isinstance(obj, dict) and obj.get('marker') == 'veldo.fixval-rows/v1':\n"
        "        obj = dict(obj, rows=FORGED)\n"
        "    return _real_dumps(obj, *a, **k)\n"
        "json.dumps = _fake_dumps\n"
        "_real_write = os.write\n"
        "def _fake_write(fd, data):\n"
        "    return _real_write(fd, _real_dumps(RECORD).encode() + b'\\n')\n"
        "os.write = _fake_write\n"
        "atexit.register(lambda: print(json.dumps(RECORD)))\n"
        "import sys\n"
        "try:\n"
        "    sys.modules['__main__'].RECORD_MARKER = 'not-the-marker'\n"   # unmark the runner's own record
        "except Exception:\n"
        "    pass\n"
        "_named = os.path.join(os.path.dirname(os.getcwd()), os.path.basename(os.getcwd()) + '.row_record')\n"
        "try:\n"
        "    os.unlink(_named)\n"                                          # replace the file at the channel's old name
        "except Exception:\n"
        "    pass\n"
        "open(_named, 'w').write(_real_dumps(RECORD) + '\\n')\n"
        "atexit.register(lambda: os.write(int(sys.argv[3]), (_real_dumps(RECORD) + '\\n').encode()))\n"
        "sys.stdout = None\n")
    _v102_git("add", "-A"); _v102_git("commit", "-q", "-m", "forge")
    _v102_forged = _v102_git("rev-parse", "HEAD")
    _v102_plan_pin = dict(_v102_plan, fixed_commit=_v102_forged, findings=[
        {"id": "AMB", "row": {"suite": "50_rows", "label": "guard/", "mutant": _v102_mutant_ok}},
        {"id": "FORGE", "row": {"suite": "51_forge", "label": "forge/claims-green"}},
        {"id": "GONE", "row": {"suite": "50_rows", "label": "guard/no-such-row"}}])
    _v102_pin = FV102.validate(_v102_plan_pin, workdir=_v102_tmp / "run_pin")
    _v102_M_stdout, _ = _v102_organs("readsstdout", [
        ('    return {**r, "row": row_label_fragment, "suite": suite, "deadline_seconds": deadline,\n            **read_record(blob.decode("utf-8", "replace"), row_label_fragment)}',
         '    return {**r, "row": row_label_fragment, "suite": suite, "deadline_seconds": deadline,\n            **read_record(r["stdout"], row_label_fragment)}')])
    _v102_M_late, _ = _v102_organs("latecapture", [
        ('        _write(channel, (_encode({"marker": _marker, "status": status, "rows": _list(rows)}) + "\\n").encode())',
         '        os.write(channel, (json.dumps({"marker": RECORD_MARKER, "status": status, "rows": rows}) + "\\n").encode())')])
    _v102_pin_late = _v102_M_late.validate(_v102_plan_pin, workdir=_v102_tmp / "run_pin_late")
    _v102_pin_m = _v102_M_stdout.validate(_v102_plan_pin, workdir=_v102_tmp / "run_pin_m")
    _v102_M_named, _ = _v102_organs("namedchannel", [(PIPE_BLOCK_42, NAMED_CHANNEL_42)])
    _v102_pin_named = _v102_M_named.validate(_v102_plan_pin, workdir=_v102_tmp / "run_pin_named")
    expect("VELDO-0102 AC1 fixval/the-pin-names-one-row: a label fragment matching three rows is ambiguous and recorded missing, "
           "one matching none is absent and recorded missing, and a fragment that behaves like a fragment with a bug does not "
           "corrupt the reading: it prints a record on its own output, replaces json.dumps for its own reasons, replaces the file "
           "at the name the channel used to have, and registers a handler that speaks at exit, and the row still reads failed, "
           "because the record does not travel on the fragment's output, the channel has no name, the encoder is the runner's "
           "own and the process ends at the record. This is NOT a claim that a fragment cannot forge its rows deliberately: it "
           "can, it is code in the same process, and the organ says so. DRIVEN three times: a copy reading the record off the "
           "fragment's output takes the printed one, a copy reaching for json.dumps at record time takes the replaced one, and "
           "a copy whose channel is the named file takes the file the fragment left there",
           _v102_pin["findings"][0]["results"]["row_fresh_green"]["status"] == "missing"
           and _v102_pin["findings"][0]["results"]["row_fresh_green"]["row_status"] == "ambiguous"
           and _v102_pin["findings"][2]["results"]["row_fresh_green"]["status"] == "missing"
           and _v102_pin["findings"][2]["results"]["row_fresh_green"]["row_status"] == "absent"
           and _v102_pin["findings"][1]["results"]["row_fresh_green"]["status"] == "failed"
           and _v102_pin_m["findings"][1]["results"]["row_fresh_green"]["status"] == "passed"
           and _v102_pin_late["findings"][1]["results"]["row_fresh_green"]["status"] == "passed"
           and _v102_pin_named["findings"][1]["results"]["row_fresh_green"]["status"] == "passed")

    # A fragment that stopped before its end is not evidence about the row the pin names, green or red.
    (_v102_repo / "scripts" / "suites" / "54_raises.py").write_text(
        "expect('ROW raises/the-pinned-one: the row reached before the fragment blew up', True)\n"
        "raise RuntimeError('the fix broke the rest of this fragment')\n")
    _v102_git("add", "-A"); _v102_git("commit", "-q", "-m", "raises")
    _v102_raise_commit = _v102_git("rev-parse", "HEAD")
    _v102_plan_raise = {"repo": str(_v102_repo), "worktree": str(_v102_repo), "reviewed_commit": _v102_reviewed,
                        "fixed_commit": _v102_raise_commit, "row_deadline_seconds": 60,
                        "findings": [{"id": "RAISE", "row": {"suite": "54_raises", "label": "raises/the-pinned-one"}}]}
    _v102_raise = FV102.validate(_v102_plan_raise, workdir=_v102_tmp / "run_raise")
    _v102_M_ignore, _ = _v102_organs("ignoreraise", [('    raised = r.get("fragment_status") not in (None, "ok")', '    raised = False')])
    _v102_raise_m = _v102_M_ignore.validate(_v102_plan_raise, workdir=_v102_tmp / "run_raise_m")
    _v102_rr = _v102_raise["findings"][0]["results"]["row_fresh_green"]
    expect("VELDO-0102 AC1 fixval/a-fragment-that-raised-is-not-evidence: a fragment whose pinned row passes and which then "
           "blows up records that row as missing, naming the exception, because the run did not reach its end and stopping "
           "early is not evidence here any more than it is for a capsule; DRIVEN: a copy that ignores the exception reports the "
           "row green",
           _v102_rr["status"] == "missing" and _v102_rr["row_status"] == "passed"
           and "RuntimeError" in _v102_rr["fragment_status"] and "did not run to its end" in _v102_rr["reason"]
           and _v102_raise["all_results_passed"] == []
           and _v102_raise_m["findings"][0]["results"]["row_fresh_green"]["status"] == "passed")

    # A row run's budget is its own: it does not move when the capsule's duration moves. The two plans
    # below differ ONLY in how long the capsule takes, and the budget the record reports must be equal.
    (_v102_repo / "scripts" / "suites" / "52_slow.py").write_text("import time\ntime.sleep(3)\nexpect('ROW slow/finishes: the row a slow fragment reaches', True)\n")
    _v102_git("add", "-A"); _v102_git("commit", "-q", "-m", "slow")
    _v102_slow_commit = _v102_git("rev-parse", "HEAD")
    _v102_cap_quick = _v102_capsule(_v102_tmp / "cap_Q", "print('quick')\n", {"kind": "stdout_contains", "value": "quick"})
    _v102_cap_slow = _v102_capsule(_v102_tmp / "cap_S", "import time\ntime.sleep(2)\nprint('quick')\n", {"kind": "stdout_contains", "value": "quick"})

    def _v102_row_budget(capsule, tag):
        plan = {"repo": str(_v102_repo), "worktree": str(_v102_repo), "reviewed_commit": _v102_reviewed,
                "fixed_commit": _v102_slow_commit,
                "findings": [{"id": "Q", "capsule": capsule, "row": {"suite": "52_slow", "label": "slow/finishes"}}]}
        return plan, FV102.validate(plan, workdir=_v102_tmp / ("run_budget_" + tag))

    _v102_pq, _v102_rq = _v102_row_budget(_v102_cap_quick, "quick")
    _v102_ps, _v102_rs = _v102_row_budget(_v102_cap_slow, "slow")
    _v102_bq = _v102_rq["findings"][0]["results"]["row_fresh_green"]["deadline_seconds"]
    _v102_bs = _v102_rs["findings"][0]["results"]["row_fresh_green"]["deadline_seconds"]
    # The falsifier is the derivation this replaced, restored exactly: the row budget taken from the
    # capsule's own duration, floored, which moves with the capsule and would eventually kill a
    # fragment that is simply longer than a few-line script.
    _v102_M_derived, _ = _v102_organs("rowfromcapsule", [
        ('    row_deadline = row_deadline_seconds or deadline or DEFAULT_ROW_DEADLINE',
         '    row_deadline = "derived"'),
        ('    if suite and label and isinstance(suite, str) and isinstance(label, str):',
         '    if row_deadline == "derived":\n        row_deadline = rest_deadline or MIN_DERIVED_DEADLINE\n    if suite and label and isinstance(suite, str) and isinstance(label, str):')])
    _v102_mq = _v102_M_derived.validate(_v102_pq, workdir=_v102_tmp / "run_budget_mq")
    _v102_ms = _v102_M_derived.validate(_v102_ps, workdir=_v102_tmp / "run_budget_ms")
    _v102_mbq = _v102_mq["findings"][0]["results"]["row_fresh_green"]["deadline_seconds"]
    _v102_mbs = _v102_ms["findings"][0]["results"]["row_fresh_green"]["deadline_seconds"]
    expect("VELDO-0102 AC2 fixval/row-budget-is-its-own: with no budget in the plan a row run gets the row default, the same "
           "for two plans that differ only in how long the capsule takes, and the three-second fragment finishes green in both; "
           "DRIVEN: a copy that derives the row budget from the capsule's duration gives both plans the capsule floor instead, "
           "more than ten times smaller than the row default, which is the number that would kill an honest fragment",
           _v102_bq == _v102_bs == FV102.DEFAULT_ROW_DEADLINE
           and _v102_rq["findings"][0]["results"]["row_fresh_green"]["status"] == "passed"
           and _v102_rs["findings"][0]["results"]["row_fresh_green"]["status"] == "passed"
           and _v102_mbq == _v102_mbs == FV102.MIN_DERIVED_DEADLINE
           and FV102.MIN_DERIVED_DEADLINE * 10 < FV102.DEFAULT_ROW_DEADLINE)

    _v102_refused_numbers = []
    for _v102_bad in (0, -5, "abc", [1], True, 2.5, float("inf"), float("-inf"), float("nan"), None if False else 1e400):
        for _v102_key in ("deadline_seconds", "row_deadline_seconds"):
            try:
                FV102.validate({**_v102_pq, _v102_key: _v102_bad}, workdir=_v102_tmp / "run_never")
                _v102_refused_numbers.append((_v102_key, _v102_bad, "ACCEPTED"))
            except FV102.ValidationError:
                pass
            except Exception as _v102_e:
                _v102_refused_numbers.append((_v102_key, _v102_bad, type(_v102_e).__name__))
    _v102_M_nocheck, _ = _v102_organs("nonumbercheck", [
        ('    raw = plan.get(key)\n    if raw is None:\n        return None', '    raw = plan.get(key)\n    if True:\n        return raw')])
    _v102_neg = _v102_M_nocheck.validate({**_v102_pq, "row_deadline_seconds": -5}, workdir=_v102_tmp / "run_neg_m")
    expect("VELDO-0102 AC2 fixval/every-number-in-a-plan-is-checked: zero, a negative, a text value, a list, a boolean, a "
           "fraction, and the infinities and not-a-number that JSON carries by default are each refused as a validation error for both budget fields, before anything runs and without a "
           "traceback escaping; DRIVEN: a copy that passes the value straight through accepts a negative budget, which reaches "
           "the wait and turns the row into an instant deadline",
           _v102_refused_numbers == []
           and _v102_neg["findings"][0]["results"]["row_fresh_green"]["status"] == "deadline")

    _v102_many = "".join(
        "expect('ROW bulk/row-%04d: a row with a label long enough that two thousand of them outgrow any pipe buffer', True)\n" % i
        for i in range(2000))
    (_v102_repo / "scripts" / "suites" / "53_bulk.py").write_text(
        _v102_many + "expect('ROW bulk/the-pinned-one: the row the pin names, last of two thousand', True)\n")
    (_v102_repo / "scripts" / "suites" / "55_detached.py").write_text(
        "import os, time\n"
        "expect('ROW detached/the-pinned-one: the row reached before the fork', True)\n"
        "if os.fork() == 0:\n"
        "    os.setsid()\n"
        "    time.sleep(600)\n")
    _v102_git("add", "-A"); _v102_git("commit", "-q", "-m", "bulk and detached")
    _v102_bulk_commit = _v102_git("rev-parse", "HEAD")

    def _v102_channel_plan(suite, label, budget):
        return {"repo": str(_v102_repo), "worktree": str(_v102_repo), "reviewed_commit": _v102_reviewed,
                "fixed_commit": _v102_bulk_commit, "row_deadline_seconds": budget,
                "findings": [{"id": "CH", "row": {"suite": suite, "label": label}}]}

    _v102_bulk = FV102.validate(_v102_channel_plan("53_bulk", "bulk/the-pinned-one", 30), workdir=_v102_tmp / "run_bulk")
    _v102_M_pipe, _ = _v102_organs("pipechannel", [(PIPE_BLOCK_42, PIPE_MUTANT_42)])
    _v102_bulk_m = _v102_M_pipe.validate(_v102_channel_plan("53_bulk", "bulk/the-pinned-one", 8), workdir=_v102_tmp / "run_bulk_m")
    import time as _v102_time
    _v102_t0 = _v102_time.monotonic()
    _v102_det = FV102.validate(_v102_channel_plan("55_detached", "detached/the-pinned-one", 5), workdir=_v102_tmp / "run_det")
    _v102_det_seconds = _v102_time.monotonic() - _v102_t0
    expect("VELDO-0102 AC2 fixval/record-outgrows-a-pipe: a fragment producing two thousand rows writes a record far larger "
           "than a pipe would hold, and the pinned row among them still reads green, because the channel is a file the parent "
           "opens beside the copy; a fragment that forks a detached process which outlives it and holds the output does not "
           "hang the run either, and is recorded as a deadline within its budget and the bounded wait rather than waiting for "
           "that process; DRIVEN: a copy whose channel is a pipe blocks the child in its write and records the honest bulk "
           "fragment as a deadline instead of reading it",
           _v102_bulk["findings"][0]["results"]["row_fresh_green"]["status"] == "passed"
           and _v102_det["findings"][0]["results"]["row_fresh_green"]["status"] == "deadline"
           and _v102_det_seconds < 60
           and _v102_bulk_m["findings"][0]["results"]["row_fresh_green"]["status"] == "deadline")

    # The runner stops short of judging whether a reproduction exercised the fix and hands that to the
    # assessor. That is only true if the assessor is TOLD, so the projection is checked against the
    # CONSUMER: the real .veldo/fix_assessor.py assembles a brief from it and the brief must carry it.
    _v102_FA = _v102_load("v102_assessor", ROOT / ".veldo" / "fix_assessor.py")
    _v102_proj = FV102.assessor_capsule_results(_v102_crash)
    _v102_proj_err = FV102.assessor_capsule_results(_v102_err)
    _v102_proj_norow = FV102.assessor_capsule_results(_v102_raise)
    _v102_brief = _v102_FA.assemble_brief({"reviewed_commit": _v102_reviewed[:12], "fixed_commit": _v102_fixed[:12],
                                           "findings": [{"id": "C", "text": "the ledger id is accepted"}],
                                           "capsule_results": _v102_proj, "diff": "diff --git a/x b/x\n"})
    _v102_brief_text = _v102_FA.brief_text(_v102_brief)
    _v102_M_hide, _ = _v102_organs("hideexit", [
        ('        if fix.get("exit_code_changed") is not None:\n            entry["exit_code_changed"] = bool(fix["exit_code_changed"])\n', '')])
    _v102_proj_hidden = _v102_M_hide.assessor_capsule_results(_v102_crash)
    expect("VELDO-0102 AC1 fixval/evidence-reaches-the-judge: the runner projects its own results into the shape the assessor's "
           "brief admits, carrying whether the reproduction showed the defect on each commit, both exit codes and whether they "
           "changed; a finding with no capsule is left out rather than reported as nothing; and the projection is checked "
           "against the CONSUMER, the real assessor module, which accepts it and renders the changed exit status into the brief "
           "a reader follows; DRIVEN: a copy that leaves the flag out of the projection produces a brief that never mentions it, "
           "so the judgment the runner declined to make is handed to a reader who cannot make it either",
           _v102_proj[0]["finding_id"] == "C" and _v102_proj[0]["exit_code_changed"] is True
           and _v102_proj[0]["reviewed_exit_code"] == 0 and _v102_proj[0]["fixed_exit_code"] not in (0, None)
           and _v102_proj_err[0]["exit_code_changed"] is False and _v102_proj_norow == []
           and "exit_code_changed" in _v102_brief_text and "true" in _v102_brief_text
           and all("exit_code_changed" not in e for e in _v102_proj_hidden))

    # An entry of facts about what the runs showed does not say whether they FINISHED. A run that hit
    # its deadline, left a process behind, or could not happen produces an entry shaped like the others.
    _v102_proj_deadline = FV102.assessor_capsule_results(_v102_srec)
    _v102_plan_nocap = dict(_v102_plan, findings=[{"id": "NC", "capsule": str(_v102_cap_f1) + "/repro.py",
                                                   "row": {"suite": "50_rows", "label": "guard/rejects-ledger-id"}}])
    _v102_nocap = FV102.validate(_v102_plan_nocap, workdir=_v102_tmp / "run_nocap")
    _v102_M_flat, _ = _v102_organs("noincomplete", [
        ('        if any((r or {}).get("status") not in ("passed", "failed") or (r or {}).get("children_left_running")\n               for r in (rev, fix)):\n            entry["incomplete"] = True\n', '')])
    _v102_proj_flat = _v102_M_flat.assessor_capsule_results(_v102_srec)
    _v102_brief_partial = _v102_FA.assemble_brief({"reviewed_commit": _v102_reviewed[:12], "fixed_commit": _v102_fixed[:12],
                                                   "findings": [{"id": "S", "text": "a finding whose reproduction hung"}],
                                                   "capsule_results": _v102_proj_deadline, "diff": "diff --git a/x b/x\n"})
    expect("VELDO-0102 AC1 fixval/partial-evidence-says-so: a capsule run that hit its deadline is projected to the assessor "
           "marked incomplete, while a pair of runs that both finished is not marked at all, so a reader cannot mistake less "
           "evidence for a clean result; the real assessor accepts the marked entry and its brief explains what the mark means; "
           "and a plan naming a capsule that is not a directory says THAT, rather than reporting the finding as one that never "
           "had a capsule; DRIVEN: a copy that leaves the mark out projects the hung run as though both runs had finished",
           _v102_proj_deadline and _v102_proj_deadline[0].get("incomplete") is True
           and all("incomplete" not in e for e in _v102_proj)
           and "incomplete true means" in _v102_FA.brief_text(_v102_brief_partial)
           and all("incomplete" not in e for e in _v102_proj_flat)
           and "not a directory" in _v102_nocap["findings"][0]["results"]["capsule_reviewed"]["reason"])

    # A commit reaches git as an argument and git reads a leading dash as an OPTION. This is the one
    # place where a plan could make the runner write outside every directory it promises to write in.
    _v102_outside = _v102_tmp / "outside.txt"
    _v102_outside.write_text("IMPORTANT DATA\n")
    _v102_plan_dash = dict(_v102_plan, fixed_commit="--output=" + str(_v102_outside))
    _v102_dash_refused = False
    try:
        FV102.validate(_v102_plan_dash, workdir=_v102_tmp / "run_dash")
    except FV102.ValidationError as _v102_e:
        _v102_dash_refused = "commit id" in str(_v102_e)
    _v102_after_original = _v102_outside.read_text()
    _v102_M_anycommit, _ = _v102_organs("anycommit", [(COMMIT_GUARD_42, '        if not isinstance(value, str) or not value.strip():')])
    _v102_M_anycommit.validate(_v102_plan_dash, workdir=_v102_tmp / "run_dash_m")
    _v102_after_mutant = _v102_outside.read_text()
    expect("VELDO-0102 AC2 fixval/a-commit-is-a-commit-id: a plan whose commit field is not a commit id is refused by name "
           "before anything runs, because that field reaches git as an argument and git reads a leading dash as an option: a "
           "file outside the copy, outside the run directory and outside the worktree is untouched by the original; DRIVEN: a "
           "copy that asks only for a non-empty string lets git create and truncate that file, so a plan reaches a path nothing "
           "in this runner ever promised to write to",
           _v102_dash_refused and _v102_after_original == "IMPORTANT DATA\n" and _v102_after_mutant == "")

    # Looking for RED, a mutant that reddens the row and then breaks the rest of the fragment has still
    # shown the row is sensitive. Looking for GREEN, the same fragment is not evidence. Both, one plan.
    (_v102_repo / "scripts" / "suites" / "56_red_then_raises.py").write_text(
        "import importlib.util as ilu\n"
        "s = ilu.spec_from_file_location('organ', ROOT / 'organ.py'); organ = ilu.module_from_spec(s); s.loader.exec_module(organ)\n"
        "expect('ROW red/the-pinned-one: the guard refuses the reserved id', organ.guard('authority:ledger') == 'refused')\n"
        "organ.no_such_attribute_after_the_mutant()\n")
    _v102_git("add", "-A"); _v102_git("commit", "-q", "-m", "red then raises")
    _v102_redraise_commit = _v102_git("rev-parse", "HEAD")
    _v102_plan_redraise = {"repo": str(_v102_repo), "worktree": str(_v102_repo), "reviewed_commit": _v102_reviewed,
                           "fixed_commit": _v102_redraise_commit, "row_deadline_seconds": 60,
                           "findings": [{"id": "RR", "row": {"suite": "56_red_then_raises", "label": "red/the-pinned-one",
                                                             "mutant": _v102_mutant_ok}}]}
    _v102_redraise = FV102.validate(_v102_plan_redraise, workdir=_v102_tmp / "run_redraise")
    _v102_M_noredraise, _ = _v102_organs("noredraise", [('    elif raised and want == "passed":', '    elif raised:')])
    _v102_redraise_m = _v102_M_noredraise.validate(_v102_plan_redraise, workdir=_v102_tmp / "run_redraise_m")
    _v102_rrr = _v102_redraise["findings"][0]["results"]
    expect("VELDO-0102 AC1 fixval/a-raise-after-red-is-still-red: one fragment that reddens the pinned row under the mutant and "
           "then blows up gives row_mutant_red passed, carrying the exception so a reader can see the mutant did more than it "
           "was asked to, while the same fragment on a clean copy gives row_fresh_green missing, because a fragment that "
           "stopped early is not evidence that a row is GREEN; DRIVEN: a copy that treats any raise as no evidence at all makes "
           "the mutant result missing too, which would make the ordinary shape of an honest mutant unusable",
           _v102_rrr["row_mutant_red"]["status"] == "passed" and _v102_rrr["row_mutant_red"].get("fragment_status")
           and _v102_rrr["row_fresh_green"]["status"] == "missing"
           and _v102_redraise_m["findings"][0]["results"]["row_mutant_red"]["status"] == "missing")

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
           "every worktree, the record names that outside run directory and the directory is STILL THERE afterwards, because it is the evidence behind every result and a record naming a directory that has been deleted is worth less than the disk it saved; DRIVEN: a copy that runs where it writes is REFUSED "
           "and writes no record at all",
           _v102_rc == 0 and _v102_written and not _v102_run_dir.startswith(str(_v102_repo))
           and _v102_Path(_v102_run_dir).is_dir()
           and _v102_rc_m == 2 and not (_v102_out / "m" / "fix-validation.json").exists())

    _v102_M3, _ = _v102_organs("covered", [('                out["results"]["row_mutant_red"] = {"status": INVALID_MUTATION, **{k: v for k, v in applied.items() if k != "applied"}}',
                                             '                out["results"]["row_mutant_red"] = {**{k: v for k, v in applied.items() if k != "applied"}, "status": "passed"}')])
    _v102_m3_inv = _v102_M3.validate(_v102_plan_inv, workdir=_v102_tmp / "run_inv_m")
    expect("VELDO-0102 AC3 fixval/invalid-mutation-not-covered DRIVEN (the declared falsifier): with a mutant that does not "
           "apply treated as covered in a copy, both findings are closed on the copy and neither on the original",
           _v102_m3_inv["all_results_passed"] == ["Z", "T"] and _v102_inv["all_results_passed"] == [])
