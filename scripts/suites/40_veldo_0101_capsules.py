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
WRITE_IN_101 = '    if not isinstance(reviewed_commit, str) or not COMMIT_ISH.fullmatch(reviewed_commit):'
WRITE_OUT_101 = '    if not isinstance(m["reviewed_commit"], str) or not COMMIT_ISH.fullmatch(m["reviewed_commit"]):'
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

# The commit a capsule names goes into a git argument list in every consumer of that capsule, and git
# reads a name beginning with a dash as an option. It is a commit id at both ends of the file.
_v101_bad_commits = ("--output=/tmp/nothing-here", "HEAD", "main", "", "not hex at all")
_v101_write_refused = []
for _v101_bad in _v101_bad_commits:
    _v101_d = _v101_tmp / ("commit_" + str(abs(hash(_v101_bad)))[:8])
    _v101_d.mkdir()
    (_v101_d / "repro.py").write_text("print('DEFECT')\n")
    try:
        CAP101.write_manifest(_v101_d, "F-01", _v101_bad, ["python3", CAP101.MOUNT + "/repro.py"],
                              {"kind": "stdout_contains", "value": "DEFECT"}, "obs")
        _v101_write_refused.append((_v101_bad, "ACCEPTED"))
    except CAP101.CapsuleError:
        pass
_v101_good = _v101_make_capsule(_v101_tmp / "commit_good", "print('DEFECT')\n", commit="0123abcdef0123abcdef")
_v101_hand = _v101_tmp / "commit_hand"
_v101_hand.mkdir()
(_v101_hand / "repro.py").write_text("print('DEFECT')\n")
CAP101.write_manifest(_v101_hand, "F-01", "0123abc", ["python3", CAP101.MOUNT + "/repro.py"],
                      {"kind": "stdout_contains", "value": "DEFECT"}, "obs")
_v101_m = _v101_json.loads((_v101_hand / CAP101.MANIFEST).read_text())
_v101_m["reviewed_commit"] = "--output=/tmp/nothing-here"
(_v101_hand / CAP101.MANIFEST).write_text(_v101_json.dumps(_v101_m, indent=1, sort_keys=True) + "\n")
_v101_load_refused = False
try:
    CAP101.load_capsule(_v101_hand)
except CAP101.CapsuleError as _v101_e:
    _v101_load_refused = "commit id" in str(_v101_e)
_v101_m_commit = _v101_mutant([(WRITE_IN_101, "    if False:"), (WRITE_OUT_101, "    if False:")], "anycommitcapsule")
_v101_m_loaded = _v101_m_commit.load_capsule(_v101_hand)["reviewed_commit"]
expect("VELDO-0101 AC2 capsule/a-capsules-commit-is-a-commit-id: the commit a capsule names must be seven to forty hexadecimal "
       "characters, checked when the manifest is written and again when it is read back, because a capsule read off disk was "
       "written by something else and every consumer puts that string into a git argument list, where a leading dash is an "
       "option; an option-shaped value, a branch name, a symbolic name, an empty string and plain text are each refused at both "
       "ends while a real commit id is accepted, and the review brief says so; DRIVEN: a copy without either check hands the "
       "option-shaped value back to its caller",
       _v101_write_refused == [] and _v101_good.is_dir() and _v101_load_refused
       and _v101_m_loaded == "--output=/tmp/nothing-here"
       and "COMMIT ID you read" in CAP101.brief_text())

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


    # A command that spawns a helper and outlives the deadline: the deadline must kill the whole process
    # group, or the helper survives as a stray process after the runner has returned.
    _v101_pidfile = _v101_tmp / "helper.pid"
    _v101_c_grp = _v101_make_capsule(_v101_tmp / "c_grp",
                                     "import subprocess, sys, time\n"
                                     "subprocess.Popen([sys.executable, '-c', 'import os, sys, time; open(sys.argv[1], \"w\").write(str(os.getpid())); time.sleep(90)', "
                                     + repr(str(_v101_pidfile)) + "], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
                                     "time.sleep(90)\nprint('DEFECT')\n", commit=_v101_reviewed)

    def _v101_helper_alive(pidfile, wait=3.0):
        """True while the helper named in the pidfile is running, polled for up to wait seconds for it to
        go away; None when the helper never wrote its pid."""
        import time as _t
        end = _t.monotonic() + wait
        while True:
            try:
                pid = int(pidfile.read_text())
            except (OSError, ValueError):
                pid = None
            if pid is not None:
                try:
                    _v101_os.kill(pid, 0)
                    alive = True
                except ProcessLookupError:
                    return False
                except PermissionError:
                    alive = True
                if not alive or _t.monotonic() > end:
                    return alive
            elif _t.monotonic() > end:
                return None
            _t.sleep(0.1)

    _v101_r_grp = CAP101.run_capsule(_v101_c_grp, _v101_repo, _v101_reviewed, timeout=2, workdir=_v101_tmp / "run_grp")
    _v101_grp_alive = _v101_helper_alive(_v101_pidfile)
    expect("VELDO-0101 AC3 capsule/deadline-kills-the-group: a command that spawns a helper and outlives the deadline is "
           "recorded timed out and not reproduced, the runner returns at the deadline rather than when the helper ends, and "
           "the helper is dead afterwards because the deadline killed the whole process group",
           _v101_r_grp["timed_out"] is True and _v101_r_grp["reproduced"] is False and _v101_r_grp["duration_seconds"] < 30
           and _v101_grp_alive is False)

    _v101_m_grp = _v101_mutant([("            os.killpg(p.pid, signal.SIGKILL)\n", "            p.kill()\n")], "childonly")
    _v101_pidfile.unlink(missing_ok=True)
    _v101_r_grp_m = _v101_m_grp.run_capsule(_v101_c_grp, _v101_repo, _v101_reviewed, timeout=2, workdir=_v101_tmp / "run_grp_m")
    _v101_grp_m_alive = _v101_helper_alive(_v101_pidfile, wait=1.0)
    try:
        _v101_os.kill(int(_v101_pidfile.read_text()), 9)   # clean up the stray the mutant left behind
    except (OSError, ValueError):
        pass
    expect("VELDO-0101 AC3 capsule/deadline-kills-the-group DRIVEN: with a copy of the runner that kills only the command on "
           "the deadline, the helper is still alive after the copy returns and dead after the original returns",
           _v101_r_grp_m["timed_out"] is True and _v101_grp_m_alive is True and _v101_grp_alive is False)


    # --- fixes after the author's review (2026-09-19) ------------------------------------------------
    # The observation is judged over the WHOLE output, not the 4000-character tail the record keeps.
    _v101_c_long = _v101_make_capsule(_v101_tmp / "c_long", "import organ\nprint('answer is', organ.answer())\nprint('x' * 6000)\n",
                                      expected={"kind": "stdout_contains", "value": "answer is DEFECT"}, commit=_v101_reviewed)
    _v101_r_long = CAP101.run_capsule(_v101_c_long, _v101_repo, _v101_reviewed, timeout=60, workdir=_v101_tmp / "run_long")
    _v101_m_tail = _v101_mutant([('    result["reproduced"] = (not timed_out) and observation_matches(m["expected"], result)\n'
                                  '    result["stdout"], result["stderr"] = out[-4000:], err[-4000:]\n',
                                  '    result["stdout"], result["stderr"] = out[-4000:], err[-4000:]\n'
                                  '    result["reproduced"] = (not timed_out) and observation_matches(m["expected"], result)\n')], "tail")
    _v101_r_long_m = _v101_m_tail.run_capsule(_v101_c_long, _v101_repo, _v101_reviewed, timeout=60, workdir=_v101_tmp / "run_long_m")
    expect("VELDO-0101 AC3 capsule/whole-output-judged: a reproduction that prints the defect marker and then 6000 characters "
           "of log is judged reproduced (the whole output is compared, the record keeps a tail and says it is truncated); "
           "DRIVEN: a copy that trims the output before judging it reports not reproduced",
           _v101_r_long["reproduced"] is True and _v101_r_long["output_truncated"] is True and len(_v101_r_long["stdout"]) <= 4000
           and _v101_r_long_m["reproduced"] is False)

    # A capsule may not carry symbolic links: the digests cannot cover what a link points at.
    _v101_c_link = _v101_make_capsule(_v101_tmp / "c_link", "print('DEFECT')\n", commit=_v101_reviewed)
    (_v101_tmp / "c_link" / "helpers").symlink_to(_v101_tmp)
    _v101_link_refused = False
    try:
        CAP101.load_capsule(_v101_c_link)
    except CAP101.CapsuleError as e:
        _v101_link_refused = "symbolic link" in str(e)
    _v101_m_link = _v101_mutant([("    if links:\n        raise CapsuleError", "    if False:\n        raise CapsuleError")], "links")
    _v101_link_loaded_m = False
    try:
        _v101_m_link.load_capsule(_v101_c_link); _v101_link_loaded_m = True
    except _v101_m_link.CapsuleError:
        pass
    expect("VELDO-0101 AC2 capsule/symlinks-refused: a capsule with a symbolic link beside its digested files is refused by name; "
           "DRIVEN: a copy without the link check loads it as if every file were digested",
           _v101_link_refused and _v101_link_loaded_m)

    # The mounted copy is digested too: a runner that rewrites the mount, not the source, is caught.
    _v101_attack = ("    shutil.copytree(capsule_dir, mount, symlinks=True)\n",
                    "    shutil.copytree(capsule_dir, mount, symlinks=True)\n    (mount / 'repro.py').write_text(\"print('REWRITTEN')\\n\")\n")
    _v101_m_mount = _v101_mutant([_v101_attack], "mountattack")
    _v101_m_mount_nocheck = _v101_mutant([_v101_attack, ("    if mounted != before:\n        raise CapsuleError", "    if False:\n        raise CapsuleError")], "mountnocheck")
    _v101_mount_caught = False
    try:
        _v101_m_mount.run_capsule(_v101_c3, _v101_repo, _v101_reviewed, timeout=60, workdir=_v101_tmp / "run_mount")
    except _v101_m_mount.CapsuleError as e:
        _v101_mount_caught = "mounted copy" in str(e)
    _v101_r_nocheck = _v101_m_mount_nocheck.run_capsule(_v101_c3, _v101_repo, _v101_reviewed, timeout=60, workdir=_v101_tmp / "run_mount_nc")
    expect("VELDO-0101 AC3 capsule/mount-digested: a runner copy that rewrites the mounted script before running it is refused by the "
           "mount digest check; DRIVEN: the same rewrite with the mount check removed runs the rewritten script unnoticed",
           _v101_mount_caught and "REWRITTEN" in _v101_r_nocheck["stdout"] and _v101_r_nocheck["reproduced"] is False
           and CAP101.digest_files(_v101_c3) == _v101_before)

    # The capsule digest covers the command and the expected observation, the two manifest fields no file digest covers.
    _v101_m_a = CAP101.load_capsule(_v101_c3)
    _v101_m_b = dict(_v101_m_a, expected={"kind": "stdout_contains", "value": "answer is"})
    _v101_m_digestfiles = _v101_mutant([('    blob = json.dumps({"files": manifest.get("files"), "command": manifest.get("command"), "expected": manifest.get("expected")}, sort_keys=True)',
                                        '    blob = json.dumps({"files": manifest.get("files")}, sort_keys=True)')], "digestfiles")
    expect("VELDO-0101 AC3 capsule/digest-covers-manifest: two capsules with the same files but a different expected observation have "
           "different capsule digests, and the run record carries that digest; DRIVEN: a copy digesting the files alone gives them the same digest",
           CAP101.capsule_digest(_v101_m_a) != CAP101.capsule_digest(_v101_m_b) and _v101_r_rev["capsule_digest"] == CAP101.capsule_digest(_v101_m_a)
           and _v101_m_digestfiles.capsule_digest(_v101_m_a) == _v101_m_digestfiles.capsule_digest(_v101_m_b))

    # After the deadline kill, the wait for the group's pipes is bounded: a helper that left the group and holds stdout
    # is recorded as children_left_running instead of holding the runner until it exits.
    _v101_pid2 = _v101_tmp / "escaped.pid"
    _v101_c_esc = _v101_make_capsule(_v101_tmp / "c_esc",
                                     "import subprocess, sys, time\n"
                                     "subprocess.Popen([sys.executable, '-c', 'import os, sys, time; open(sys.argv[1], \"w\").write(str(os.getpid())); time.sleep(14)', "
                                     + repr(str(_v101_pid2)) + "], start_new_session=True)\n"
                                     "time.sleep(90)\nprint('DEFECT')\n", commit=_v101_reviewed)
    _v101_r_esc = CAP101.run_capsule(_v101_c_esc, _v101_repo, _v101_reviewed, timeout=2, workdir=_v101_tmp / "run_esc")
    _v101_esc_alive_after_original = _v101_helper_alive(_v101_pid2, wait=0.2)
    _v101_m_wait = _v101_mutant([("            out_b, err_b = p.communicate(timeout=KILL_WAIT)\n", "            out_b, err_b = p.communicate()\n")], "unboundedwait")
    _v101_pid2.unlink(missing_ok=True)
    try:
        _v101_os.kill(int(open(str(_v101_pid2)).read()), 9)
    except (OSError, ValueError):
        pass
    _v101_r_esc_m = _v101_m_wait.run_capsule(_v101_c_esc, _v101_repo, _v101_reviewed, timeout=2, workdir=_v101_tmp / "run_esc_m")
    try:
        _v101_os.kill(int(_v101_pid2.read_text()), 9)
    except (OSError, ValueError, ProcessLookupError):
        pass
    expect("VELDO-0101 AC3 capsule/post-kill-wait-bounded: with a helper that left the process group and holds the output pipe, "
           "the runner returns within the deadline plus the bounded wait, records timed out, not reproduced and children_left_running, "
           "and the escaped helper is indeed still alive at that moment; DRIVEN: a copy whose post-kill wait is unbounded returns only "
           "when the helper exits and records no survivor",
           _v101_r_esc["timed_out"] is True and _v101_r_esc["reproduced"] is False and _v101_r_esc["children_left_running"] is True
           and _v101_r_esc["duration_seconds"] < 2 + CAP101.KILL_WAIT + 4 and _v101_esc_alive_after_original is True
           and _v101_r_esc_m["timed_out"] is True and _v101_r_esc_m["children_left_running"] is False and _v101_r_esc_m["duration_seconds"] > 10)


    # The path a capsule names for a file_exists expectation is confined to the checkout the same way a
    # plan's paths are: a file outside the copy answers a question about this machine, not this commit.
    _v101_c_out = _v101_make_capsule(_v101_tmp / "c_out", "print('nothing')\n",
                                     expected={"kind": "file_exists", "value": "/etc/hostname"}, commit=_v101_reviewed)
    _v101_c_up = _v101_make_capsule(_v101_tmp / "c_up", "print('nothing')\n",
                                    expected={"kind": "file_exists", "value": "../../etc/hostname"}, commit=_v101_reviewed)
    _v101_c_in = _v101_make_capsule(_v101_tmp / "c_in", "print('nothing')\n",
                                    expected={"kind": "file_exists", "value": "organ.py"}, commit=_v101_reviewed)
    _v101_r_out = CAP101.run_capsule(_v101_c_out, _v101_repo, _v101_reviewed, timeout=60, workdir=_v101_tmp / "run_out")
    _v101_r_up = CAP101.run_capsule(_v101_c_up, _v101_repo, _v101_reviewed, timeout=60, workdir=_v101_tmp / "run_up")
    _v101_r_in = CAP101.run_capsule(_v101_c_in, _v101_repo, _v101_reviewed, timeout=60, workdir=_v101_tmp / "run_in")
    # Both guards have to go: the first refuses the shape of the path, the second refuses a path that
    # resolves outside the copy, and either alone still answers about the copy.
    _v101_m_out = _v101_mutant([('        inside = not rel.startswith(("/", "\\\\")) and ".." not in Path(rel).parts', "        inside = True"),
                                ('            inside = inside and target.resolve().relative_to(tree.resolve()) is not None', "            pass")], "unconfinedfile")
    _v101_r_out_m = _v101_m_out.run_capsule(_v101_c_out, _v101_repo, _v101_reviewed, timeout=60, workdir=_v101_tmp / "run_out_m")
    expect("VELDO-0101 AC3 capsule/named-file-stays-inside: a file_exists expectation naming an absolute path outside the copy, "
           "and one naming a path through .., each answer that the file is not present and do not reproduce, while one naming a "
           "file of the commit answers that it is; DRIVEN: a copy without the confinement answers about the machine's own file "
           "and reproduces",
           _v101_r_out["files_present"]["/etc/hostname"] is False and _v101_r_out["reproduced"] is False
           and _v101_r_up["reproduced"] is False and _v101_r_in["reproduced"] is True
           and _v101_r_out_m["files_present"]["/etc/hostname"] is True and _v101_r_out_m["reproduced"] is True)

    # The declared falsifier: a runner that rewrites the reviewer's script into an assertion before running it.
    _v101_m3 = _v101_mutant([("    shutil.copytree(capsule_dir, mount, symlinks=True)\n",
                              "    shutil.copytree(capsule_dir, mount, symlinks=True)\n"
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
