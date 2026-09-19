"""VELDO-0101: the Codex review saves a reproduction capsule per confirmed defect (PLAN-0020 W1).

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, so its declared
prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 40_veldo_0101_capsules

WHAT IS UNDER TEST. .veldo/capsule.py: the review brief names the capsule directory, the required
files and the rule that a finding without a capsule is unconfirmed (AC1); a capsule is a directory
whose manifest digests every file, and the loader refuses changed bytes, a missing file and an
undigested extra file (AC2); the runner executes the saved command in a fresh copy of the named
commit of a REAL git repository, compares the observation in a separate function, reproduces the
defect on the reviewed commit and not on the fixed commit, and leaves the reviewer's files byte for
byte identical (AC3). The three declared falsifiers are applied to COPIES of the organ and required
to turn their named row red while the unmutated organ passes it.
"""
import importlib.util as _v101_ilu
import json as _v101_json
import os as _v101_os
import shutil as _v101_shutil
import subprocess as _v101_sp
import sys as _v101_sys
import tempfile as _v101_tf
from pathlib import Path as _v101_Path

_v101_tmp = _v101_Path(_v101_tf.mkdtemp(prefix="v101"))
_v101_have_git = _v101_shutil.which("git") is not None and _v101_shutil.which("tar") is not None


def _v101_load(name, path):
    spec = _v101_ilu.spec_from_file_location(name, path)
    m = _v101_ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _v101_mutant(edits, tag):
    """A copy of the organ with each (old, new) edit applied exactly once."""
    src = (ROOT / ".veldo" / "capsule.py").read_text()
    for old, new in edits:
        assert src.count(old) == 1, (old[:60], src.count(old))
        src = src.replace(old, new)
    d = _v101_tmp / ("mut_" + tag)
    d.mkdir()
    (d / "capsule.py").write_text(src)
    return _v101_load("v101_capsule_" + tag, d / "capsule.py")


CAP101 = _v101_load("v101_capsule_main", ROOT / ".veldo" / "capsule.py")

# --- AC1: the brief -------------------------------------------------------------------------------

_v101_brief = CAP101.brief_text()
expect("VELDO-0101 AC1 capsule/brief-requires-capsule: the review brief names the capsule directory, manifest.json with "
       "finding_id, reviewed_commit, command, expected and observation, the reviewer's script and fixtures, and states "
       "that a finding without a capsule is reported as UNCONFIRMED",
       CAP101.CAPSULE_ROOT in _v101_brief and "manifest.json" in _v101_brief
       and all(k in _v101_brief for k in ("finding_id", "reviewed_commit", "command", "expected", "observation"))
       and "script" in _v101_brief and "fixtures" in _v101_brief
       and "without a capsule is reported as UNCONFIRMED" in _v101_brief)

_v101_m1 = _v101_mutant([("A finding without a capsule is reported \"\n        \"as UNCONFIRMED, not as a finding. ", "")], "brief")
expect("VELDO-0101 AC1 capsule/brief-requires-capsule DRIVEN (the declared falsifier): with the unconfirmed rule removed "
       "from the brief in a copy of the organ, the row's own check fails on that copy and passes on the original",
       ("without a capsule is reported as UNCONFIRMED" not in _v101_m1.brief_text())
       and ("without a capsule is reported as UNCONFIRMED" in _v101_brief))

# --- AC2: the capsule and its loader -------------------------------------------------------------


def _v101_make_capsule(where, script_body, expected=None, finding="F-01", commit="0000000"):
    where.mkdir(parents=True)
    (where / "repro.py").write_text(script_body)
    (where / "fixtures").mkdir()
    (where / "fixtures" / "input.txt").write_text("fixture bytes\n")
    CAP101.write_manifest(where, finding, commit, ["python3", CAP101.MOUNT + "/repro.py"],
                          expected or {"kind": "stdout_contains", "value": "DEFECT"}, "the script prints DEFECT on the reviewed commit")
    return where


_v101_c1 = _v101_make_capsule(_v101_tmp / "c1", "import sys\nprint('DEFECT')\n")
_v101_ok = CAP101.load_capsule(_v101_c1)
_v101_tampered = _v101_tmp / "c1_tampered"
_v101_shutil.copytree(_v101_c1, _v101_tampered)
_v101_p = _v101_tampered / "repro.py"
_v101_p.write_bytes(_v101_p.read_bytes().replace(b"DEFECT", b"DEFECX", 1))
_v101_extra = _v101_tmp / "c1_extra"
_v101_shutil.copytree(_v101_c1, _v101_extra)
(_v101_extra / "notes.txt").write_text("an undigested file\n")
_v101_missing = _v101_tmp / "c1_missing"
_v101_shutil.copytree(_v101_c1, _v101_missing)
(_v101_missing / "fixtures" / "input.txt").unlink()


def _v101_refuses(d):
    try:
        CAP101.load_capsule(d)
        return False
    except CAP101.CapsuleError:
        return True


expect("VELDO-0101 AC2 capsule/tampered-bytes-refused: an untouched capsule loads with every file digested; the same "
       "capsule with one byte of the script changed is refused, one with an undigested extra file is refused, and one "
       "with a digested file missing is refused",
       set(_v101_ok["files"]) == {"repro.py", "fixtures/input.txt"} and _v101_refuses(_v101_tampered)
       and _v101_refuses(_v101_extra) and _v101_refuses(_v101_missing))

_v101_m2 = _v101_mutant([("    if missing or extra or changed:\n        raise CapsuleError", "    if missing or extra:\n        raise CapsuleError")], "digest")


def _v101_m2_refuses(d):
    try:
        _v101_m2.load_capsule(d)
        return False
    except _v101_m2.CapsuleError:
        return True


expect("VELDO-0101 AC2 capsule/tampered-bytes-refused DRIVEN (the declared falsifier): with the digest comparison skipped "
       "in a copy of the loader, the tampered capsule loads on the copy and is refused by the original",
       (not _v101_m2_refuses(_v101_tampered)) and _v101_refuses(_v101_tampered))

# --- AC3: the runner against a real repository ---------------------------------------------------

if not _v101_have_git:
    expect("VELDO-0101 AC3 STOOD DOWN by name - git or tar is not installed here, so the real-checkout rows cannot run", True)
else:
    _v101_repo = _v101_tmp / "repo"
    _v101_repo.mkdir()

    def _v101_git(*a):
        return _v101_sp.run(["git", "-C", str(_v101_repo), *a], check=True, capture_output=True, text=True,
                            env=dict(_v101_os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")).stdout.strip()

    _v101_git("init", "-q")
    (_v101_repo / "organ.py").write_text("def answer():\n    return 'DEFECT'\n")
    _v101_git("add", "-A"); _v101_git("commit", "-q", "-m", "reviewed")
    _v101_reviewed = _v101_git("rev-parse", "HEAD")
    (_v101_repo / "organ.py").write_text("def answer():\n    return 'correct'\n")
    _v101_git("add", "-A"); _v101_git("commit", "-q", "-m", "fixed")
    _v101_fixed = _v101_git("rev-parse", "HEAD")

    # The reviewer's script prints evidence rather than asserting; it is preserved as written.
    _v101_c3 = _v101_make_capsule(_v101_tmp / "c3", "import organ\nprint('answer is', organ.answer())\n",
                                  expected={"kind": "stdout_contains", "value": "answer is DEFECT"}, commit=_v101_reviewed)
    _v101_before = CAP101.digest_files(_v101_c3)
    _v101_r_rev = CAP101.run_capsule(_v101_c3, _v101_repo, _v101_reviewed, timeout=60, workdir=_v101_tmp / "run_rev")
    _v101_r_fix = CAP101.run_capsule(_v101_c3, _v101_repo, _v101_fixed, timeout=60, workdir=_v101_tmp / "run_fix")
    _v101_after = CAP101.digest_files(_v101_c3)
    _v101_repo_clean = _v101_git("status", "--porcelain") == ""

    expect("VELDO-0101 AC3 capsule/reviewer-bytes-preserved: the saved command runs in a fresh copy of the reviewed commit and "
           "reproduces the defect, runs in a fresh copy of the fixed commit and does not, the observation is judged by a "
           "separate function, the repository under review is untouched, and the reviewer's files carry the same digests "
           "before and after both runs",
           _v101_r_rev["reproduced"] is True and _v101_r_fix["reproduced"] is False
           and CAP101.observation_matches({"kind": "stdout_contains", "value": "answer is DEFECT"}, _v101_r_rev)
           and _v101_before == _v101_after and _v101_repo_clean
           and not (_v101_repo / CAP101.MOUNT).exists())

    expect("VELDO-0101 AC3 capsule/run-record: the run record names the finding, the commit, the command, the exit code, "
           "the duration and a digest of the capsule, and a timed-out run is recorded as not reproduced rather than as passed",
           _v101_r_rev["finding_id"] == "F-01" and _v101_r_rev["commit"] == _v101_reviewed and _v101_r_rev["exit_code"] == 0
           and _v101_r_rev["command"] == ["python3", CAP101.MOUNT + "/repro.py"] and len(_v101_r_rev["capsule_digest"]) == 64
           and CAP101.run_capsule(_v101_make_capsule(_v101_tmp / "c_sleep", "import time\ntime.sleep(5)\nprint('DEFECT')\n", commit=_v101_reviewed),
                                  _v101_repo, _v101_reviewed, timeout=1, workdir=_v101_tmp / "run_sleep")["reproduced"] is False)

    # The declared falsifier: a runner that rewrites the reviewer's script into an assertion before running it.
    _v101_m3 = _v101_mutant([("    mount = tree / MOUNT\n    shutil.copytree(capsule_dir, mount)\n",
                              "    mount = tree / MOUNT\n    shutil.copytree(capsule_dir, mount)\n"
                              "    _s = Path(capsule_dir) / 'repro.py'\n"
                              "    if _s.exists():\n        _s.write_text(_s.read_text() + '\\nassert True\\n')\n"
                              "    shutil.copy2(_s, mount / 'repro.py')\n")], "rewrite")
    _v101_c3m = _v101_make_capsule(_v101_tmp / "c3m", "import organ\nprint('answer is', organ.answer())\n",
                                   expected={"kind": "stdout_contains", "value": "answer is DEFECT"}, commit=_v101_reviewed)
    _v101_m3_before = _v101_m3.digest_files(_v101_c3m)
    try:
        _v101_m3.run_capsule(_v101_c3m, _v101_repo, _v101_reviewed, timeout=60, workdir=_v101_tmp / "run_mut")
        _v101_m3_raised = False
    except _v101_m3.CapsuleError:
        _v101_m3_raised = True
    _v101_m3_after = _v101_m3.digest_files(_v101_c3m)
    expect("VELDO-0101 AC3 capsule/reviewer-bytes-preserved DRIVEN (the declared falsifier): with a copy of the runner that "
           "rewrites the script to an assertion before running it, the reviewer's digests change and the copy's own "
           "after-run check raises, so the preservation the row asserts is broken on the copy and holds on the original",
           _v101_m3_before != _v101_m3_after and _v101_m3_raised and _v101_before == _v101_after)
