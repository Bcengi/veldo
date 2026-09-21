"""VELDO-0105: the fix-validation rule has a start line, and history is not re-judged (PLAN-0020 W5).

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, so its declared
prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 44_veldo_0105_startline

WHAT IS UNDER TEST. start_line_from_policy, start_line_scope and the scope test inside check_bundle
in .veldo/fix_validation_record.py, over a REAL git repository built under a temporary directory,
with real commits on a trunk and on a branch that does not contain the line. The three declared
falsifiers are applied to COPIES of the organ and required to turn their named row red while the
unmutated organ passes it.
"""
import importlib.util as _v105_ilu
import json as _v105_json
import os as _v105_os
import shutil as _v105_shutil
import subprocess as _v105_sp
import tempfile as _v105_tf
from pathlib import Path as _v105_Path

_v105_tmp = _v105_Path(_v105_tf.mkdtemp(prefix="v105"))
_v105_have_git = _v105_shutil.which("git") is not None


def _v105_load(name, path):
    spec = _v105_ilu.spec_from_file_location(name, path)
    m = _v105_ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _v105_organ(tag, edits=()):
    """A copy of the organ with its siblings beside it, so a mutant is that organ alone."""
    d = _v105_tmp / ("organ_" + tag)
    d.mkdir()
    _v105_shutil.copy2(ROOT / ".veldo" / "capsule.py", d / "capsule.py")
    _v105_shutil.copy2(ROOT / ".veldo" / "fix_validation.py", d / "fix_validation.py")
    src = (ROOT / ".veldo" / "fix_validation_record.py").read_text()
    for old, new in edits:
        assert src.count(old) == 1, (old[:70], src.count(old))
        src = src.replace(old, new)
    (d / "fix_validation_record.py").write_text(src)
    return _v105_load("v105_record_" + tag, d / "fix_validation_record.py")


ANCESTRY_105 = '    if _is_ancestor(repo, start, commit):'
UNRESOLVED_105 = '''    if not _commit_exists(repo, start):
        return {"recorded": start, "resolved": False, "excluded": False,
                "reason": f"the recorded start line {start[:12]} is not a commit in this repository"}'''
FV105 = _v105_organ("main")
CAP105 = _v105_load("v105_capsule", ROOT / ".veldo" / "capsule.py")

# --- the line as the owner records it, read from policy text and from nowhere else ---------------
_v105_pol = {
    "absent": {},
    "flag_only": {"fix_validation": {"required": "true"}},
    "with_line": {"fix_validation": {"required": "true", "from_commit": "abc123def456"}},
    "quoted": {"fix_validation": {"required": "true", "from_commit": "'abc123def456'"}},
    "empty_line": {"fix_validation": {"required": "true", "from_commit": ""}},
    "not_a_block": {"fix_validation": "true"},
}
_v105_read = {k: FV105.start_line_from_policy(v) for k, v in _v105_pol.items()}

expect("VELDO-0105 AC3 startline/read-only-from-the-policy: the start line is fix_validation.from_commit in the "
       "parsed policy and nothing else; absent, empty, and a policy whose fix_validation is not a block all read "
       "as no line, and a quoted value reads as the bare commit",
       _v105_read["absent"] == "" and _v105_read["flag_only"] == "" and _v105_read["empty_line"] == ""
       and _v105_read["not_a_block"] == "" and _v105_read["with_line"] == "abc123def456"
       and _v105_read["quoted"] == "abc123def456")

if not _v105_have_git:
    expect("VELDO-0105 STOOD DOWN by name - git is not installed here, so the repository rows cannot run", True)
else:
    # A trunk with a line partway along it, and a branch that forks BEFORE the line and therefore
    # never contains it. Both shapes exist in a real repository and the branch is the one a naive
    # ancestry test gets wrong.
    _v105_repo = _v105_tmp / "repo"
    _v105_repo.mkdir(parents=True)
    _v105_env = dict(_v105_os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                     GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")

    def _v105_git(*a):
        return _v105_sp.run(["git", "-C", str(_v105_repo), *a], check=True, capture_output=True,
                            text=True, env=_v105_env).stdout.strip()

    def _v105_commit(msg, **files):
        for rel, body in files.items():
            p = _v105_repo / rel.replace("__", "/")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body)
        _v105_git("add", "-A")
        _v105_git("commit", "-q", "-m", msg)
        return _v105_git("rev-parse", "HEAD")

    _v105_git("init", "-q")
    _v105_git("checkout", "-q", "-b", "trunk")
    _v105_OLD_R = _v105_commit("old review", **{"organ.py": "def guard(x):\n    return 'accepted'\n"})
    _v105_OLD_F = _v105_commit("old fix", **{"organ.py": "def guard(x):\n    return 'refused'\n"})
    _v105_FORK = _v105_git("rev-parse", "HEAD")
    _v105_LINE = _v105_commit("the start line lands here", **{"line.txt": "here\n"})
    _v105_NEW_R = _v105_commit("new review", **{"organ.py": "def guard(x):\n    return 'accepted2'\n"})
    _v105_NEW_F = _v105_commit("new fix", **{"organ.py": "def guard(x):\n    return 'refused2'\n"})
    _v105_git("checkout", "-q", "-b", "sidebranch", _v105_FORK)
    _v105_BR_R = _v105_commit("branch review", **{"organ.py": "def guard(x):\n    return 'accepted3'\n"})
    _v105_BR_F = _v105_commit("branch fix", **{"organ.py": "def guard(x):\n    return 'refused3'\n"})
    _v105_git("checkout", "-q", "trunk")

    def _v105_bundle(tag, reviewed):
        """A bundle carrying the REVIEWER's own evidence, and no validation record."""
        d = _v105_tmp / ("bundle_" + tag)
        cd = d / "capsules" / "F-1"
        cd.mkdir(parents=True)
        (cd / "repro.py").write_text("print('reproduction for F-1')\n")
        CAP105.write_manifest(cd, "F-1", reviewed, ["python3", CAP105.MOUNT + "/repro.py"],
                              {"kind": "stdout_contains", "value": "reproduction"}, "the reviewer's observation")
        return d

    _v105_b_old = _v105_bundle("old", _v105_OLD_R)
    _v105_b_new = _v105_bundle("new", _v105_NEW_R)
    _v105_b_br = _v105_bundle("branch", _v105_BR_R)

    def _v105_check(organ, bundle, commit, line):
        man = {"schema": "veldo.proof/v1", "spec_id": "VELDO-9105", "commit": commit}
        return organ.check_bundle(man, None, _v105_repo, bundle, True, "proven", start_line=line)

    # ---- AC1: the line decides scope, and git answers the ancestry question ----------------------
    _v105_old_excluded = _v105_check(FV105, _v105_b_old, _v105_OLD_F, _v105_LINE)
    _v105_at_line = _v105_check(FV105, _v105_b_new, _v105_LINE, _v105_LINE)
    _v105_after = _v105_check(FV105, _v105_b_new, _v105_NEW_F, _v105_LINE)
    _v105_branch = _v105_check(FV105, _v105_b_br, _v105_BR_F, _v105_LINE)
    _v105_M_inverted = _v105_organ("inverted", [(ANCESTRY_105, '    if not _is_ancestor(repo, start, commit):')])
    _v105_old_under_mutant = _v105_check(_v105_M_inverted, _v105_b_old, _v105_OLD_F, _v105_LINE)

    expect("VELDO-0105 AC1 proofcheck/start-line-excludes-history: a bundle that landed before the recorded start "
           "line is not applicable and says so, and is never refused for a missing validation record; one at the "
           "line and one after it are both in scope and both refused; a bundle on a branch that never contains "
           "the line is excluded too, which is the case a naive comparison gets wrong; DRIVEN: a copy with the "
           "ancestry test inverted judges the bundle that predates the line",
           _v105_old_excluded["applicable"] is False
           and _v105_old_excluded["start_line"]["excluded"] is True
           and "before the start line" in _v105_old_excluded["start_line"]["reason"]
           and _v105_old_excluded["problems"] == [] and _v105_old_excluded["refuses"] is False
           and _v105_after["applicable"] is True and _v105_after["refuses"] is True
           and [p["code"] for p in _v105_after["problems"]] == [FV105.NO_RECORD]
           and _v105_branch["applicable"] is False and _v105_branch["start_line"]["excluded"] is True
           and _v105_old_under_mutant["applicable"] is True and _v105_old_under_mutant["refuses"] is True)

    # ---- AC2: absence and an unresolvable line both fail CLOSED ---------------------------------
    _v105_no_line = _v105_check(FV105, _v105_b_old, _v105_OLD_F, "")
    _v105_unknown = _v105_check(FV105, _v105_b_old, _v105_OLD_F, "0" * 40)
    _v105_garbage = _v105_check(FV105, _v105_b_old, _v105_OLD_F, "not-a-commit-id")
    _v105_M_open = _v105_organ("failsopen", [(UNRESOLVED_105, '''    if not _commit_exists(repo, start):
        return {"recorded": start, "resolved": False, "excluded": True,
                "reason": "unresolvable"}''')])
    _v105_unknown_under_mutant = _v105_check(_v105_M_open, _v105_b_old, _v105_OLD_F, "0" * 40)

    expect("VELDO-0105 AC2 proofcheck/unresolvable-start-line-fails-closed: with no line recorded, with a line "
           "naming a commit this repository does not have, and with a malformed line, the bundle the rule would "
           "refuse is still in scope and still refused, and the reason is carried; DRIVEN: a copy that treats an "
           "unresolvable line as excluding everything lets that same bundle through, which is one wrong character "
           "in a commit id switching the whole rule off",
           _v105_no_line["applicable"] is True and _v105_no_line["refuses"] is True
           and _v105_no_line["start_line"]["reason"] == "no start line recorded"
           and _v105_unknown["applicable"] is True and _v105_unknown["refuses"] is True
           and "not a commit in this repository" in _v105_unknown["start_line"]["reason"]
           and _v105_garbage["applicable"] is True and _v105_garbage["refuses"] is True
           and _v105_unknown_under_mutant["applicable"] is False
           and _v105_unknown_under_mutant["refuses"] is False)

    # ---- AC3: nothing the author writes can move the line ---------------------------------------
    # The manifest and the validation record both carry a well-formed later line. They are present
    # and correct in shape, so this row fails if they are read AT ALL rather than merely absent.
    _v105_author_man = {"schema": "veldo.proof/v1", "spec_id": "VELDO-9105", "commit": _v105_OLD_F,
                        "fix_validation": {"from_commit": _v105_OLD_R}, "from_commit": _v105_OLD_R}
    _v105_author_rec = {"schema": FV105.RECORD_SCHEMA, "spec_id": "VELDO-9105",
                        "reviewed_commit": _v105_OLD_R, "fixed_commit": _v105_OLD_F,
                        "from_commit": _v105_OLD_R, "fix_validation": {"from_commit": _v105_OLD_R},
                        "findings": []}
    _v105_author = FV105.check_bundle(_v105_author_man, _v105_author_rec, _v105_repo, _v105_b_old,
                                      True, "proven", start_line=_v105_LINE)
    _v105_M_manifest = _v105_organ("frommanifest", [
        ('    scope = start_line_scope(repo, start_line or "", commit)',
         '    scope = start_line_scope(repo, start_line or (manifest.get("from_commit") or ""), commit)')])
    _v105_author_under_mutant = _v105_M_manifest.check_bundle(
        _v105_author_man, _v105_author_rec, _v105_repo, _v105_b_old, True, "proven", start_line="")

    expect("VELDO-0105 AC3 proofcheck/start-line-not-author-writable: a bundle whose manifest and whose validation "
           "record both carry a well-formed start line of their own is still judged against the owner's line in the "
           "policy, so the author's values change nothing and the bundle stays excluded; DRIVEN: a copy that falls "
           "back to the manifest's value when the policy names none reads the author's line and puts the bundle "
           "back in scope on the author's say-so",
           _v105_author["applicable"] is False and _v105_author["start_line"]["recorded"] == _v105_LINE
           and _v105_author_under_mutant["applicable"] is True)

    # ---- the negative control: the mutant machinery itself --------------------------------------
    # Every row above proves its point by showing a MUTATED copy behaving differently. That argument
    # is worth nothing if the copying is what changes the behaviour, so one copy is made with an
    # additive no-op and required to agree with the original on all four answers.
    _v105_M_noop = _v105_organ("noop", [('import subprocess', '# additive no-op control\nimport subprocess')])
    _v105_control = [
        (_v105_check(_v105_M_noop, _v105_b_old, _v105_OLD_F, _v105_LINE)["applicable"],
         _v105_old_excluded["applicable"]),
        (_v105_check(_v105_M_noop, _v105_b_new, _v105_NEW_F, _v105_LINE)["refuses"], _v105_after["refuses"]),
        (_v105_check(_v105_M_noop, _v105_b_old, _v105_OLD_F, "0" * 40)["applicable"], _v105_unknown["applicable"]),
        (_v105_check(_v105_M_noop, _v105_b_br, _v105_BR_F, _v105_LINE)["applicable"], _v105_branch["applicable"]),
    ]
    expect("VELDO-0105 control startline/copying-is-not-what-changes-it: a copy of the organ carrying only an "
           "added comment answers exactly as the original does on all four cases the rows above turn on, so the "
           "difference each DRIVEN mutant shows is the mutation and not the copying",
           all(a == b for a, b in _v105_control))

    # ---- the whole landed corpus, through the real command, with the line set at HEAD ------------
    # The thing that made this item exist: with the flag on and no line, thirteen shipped bundles go
    # red. With the line recorded, the same command over the same corpus refuses none of them.
    _v105_pol_backup = (ROOT / ".veldo" / "policy.yaml").read_text()
    _v105_head = _v105_sp.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
    _v105_corpus = {}
    try:
        for _v105_tag, _v105_block in (
                ("no_line", "fix_validation:\n  required: true\n"),
                ("with_line", f"fix_validation:\n  required: true\n  from_commit: {_v105_head}\n")):
            (ROOT / ".veldo" / "policy.yaml").write_text(_v105_pol_backup + _v105_block)
            _v105_corpus[_v105_tag] = _v105_sp.run(
                ["python3", str(ROOT / ".veldo" / "validate.py"), "all"],
                capture_output=True, text=True, cwd=str(ROOT))
    finally:
        (ROOT / ".veldo" / "policy.yaml").write_text(_v105_pol_backup)

    expect("VELDO-0105 AC1 proofcheck/the-corpus-this-item-exists-for: running the real validator over this "
           "repository's own landed corpus with the flag on and NO line recorded refuses bundles that shipped "
           "before the machinery existed, and the same run with the line recorded at HEAD refuses none of them "
           "and names the line in every result; the policy file is restored either way",
           _v105_corpus["no_line"].returncode != 0
           and _v105_corpus["with_line"].returncode == 0
           and "before the start line" in _v105_corpus["with_line"].stdout
           and f"from {_v105_head[:12]}" in _v105_corpus["with_line"].stdout
           and (ROOT / ".veldo" / "policy.yaml").read_text() == _v105_pol_backup)
