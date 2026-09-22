"""VELDO-0104: validation.json in the proof bundle, the two-round cap, and the proof check refusing
unvalidated fixes (PLAN-0020 W4).

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, so its declared
prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 43_veldo_0104_proofcheck

WHAT IS UNDER TEST. The record and the rule in .veldo/fix_validation_record.py (write_record, fix_rounds,
round_count, review_evidence, check_bundle, flag_from_policy, read_flag) over a REAL git repository
built under a temporary directory with a spec, a review commit with saved capsules, fix commits, a
gate stamp, a proof commit and a ship commit; and the ONE call site in .veldo/validate.py, exercised
by running `python3 .veldo/validate.py proof` as a child process on a bundle built from THIS
repository's own commits, so the check is shown to be reached from the proof mode. The three declared
falsifiers are applied to COPIES of the organ and required to turn their named row red while the
unmutated organ passes it.
"""
import importlib.util as _v104_ilu
import json as _v104_json
import os as _v104_os
import re as _v104_re
import shutil as _v104_shutil
import subprocess as _v104_sp
import sys as _v104_sys
import tempfile as _v104_tf
from pathlib import Path as _v104_Path

_v104_tmp = _v104_Path(_v104_tf.mkdtemp(prefix="v104"))
_v104_have_git = _v104_shutil.which("git") is not None


def _v104_load(name, path):
    spec = _v104_ilu.spec_from_file_location(name, git_fixture_dependency(path))
    m = _v104_ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _v104_organ(tag, edits=()):
    """A copy of the record-and-check organ with its siblings beside it, so a mutant is that organ alone
    and nothing else. The runner and the capsule module travel with it because it loads both by path."""
    d = _v104_tmp / ("organ_" + tag)
    d.mkdir()
    _v104_shutil.copy2(ROOT / ".veldo" / "capsule.py", d / "capsule.py")
    _v104_shutil.copy2(ROOT / ".veldo" / "fix_validation.py", d / "fix_validation.py")
    src = (ROOT / ".veldo" / "fix_validation_record.py").read_text()
    for old, new in edits:
        assert src.count(old) == 1, (old[:70], src.count(old))
        src = src.replace(old, new)
    (d / "fix_validation_record.py").write_text(src)
    return _v104_load("v104_record_" + tag, d / "fix_validation_record.py")


MISSING_LINE_104 = '    missing = [c for c in (reviewed, commit) if not _commit_exists(repo, c)]'
FV104 = _v104_organ("main")
CAP104 = _v104_load("v104_capsule", ROOT / ".veldo" / "capsule.py")

# --- the owner flag, read from fixtures and from the real policy ----------------------------------
_v104_pol = _v104_tmp / "policies"
_v104_pol.mkdir()
_v104_fixtures = {
    "absent": "schema: veldo.policy/v1\nversion: 1\n",
    "inline_on": "schema: veldo.policy/v1\nfix_validation: {required: true}\nversion: 1\n",
    "inline_on_comment": "fix_validation: {required: true}   # the owner flipped it on 2026-09-20\nversion: 1\n",
    "block_on_comment": "fix_validation:\n  # the owner's switch\n  required: true  # flipped on 2026-09-20\n  note: on\nversion: 1\n",
    "block_quoted": 'fix_validation:\n  required: "true"\nversion: 1\n',
    "block_off": "fix_validation:\n  required: false\nversion: 1\n",
    "hash_in_a_string": 'fix_validation:\n  note: "required: true # not the flag"\n  required: false\nversion: 1\n',
}
for _n, _b in _v104_fixtures.items():
    (_v104_pol / (_n + ".yaml")).write_text(_b)
_v104_flags = {n: FV104.read_flag(_v104_pol / (n + ".yaml")) for n in _v104_fixtures}
_v104_flags["missing_file"] = FV104.read_flag(_v104_pol / "nope.yaml")
_v104_policy_text = (ROOT / ".veldo" / "policy.yaml").read_text()


def _v104_flag_independently(text):
    """What the flag IS, decided by this row and not by the organ under test: the repository's policy
    says required: true inside a fix_validation block. Written here so the row's expectation cannot
    adapt to a misreading organ."""
    m = _v104_re.search(r"(?m)^fix_validation:(.*)$", text)
    if not m:
        return False
    if m.group(1).strip().startswith("{"):
        return bool(_v104_re.search(r"required\s*:\s*['\"]?true['\"]?", m.group(1)))
    tail = text[m.end():].splitlines()
    for line in tail:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith((" ", "\t")):
            break
        if _v104_re.match(r"\s*required\s*:\s*['\"]?true['\"]?\s*(#.*)?$", line):
            return True
    return False


_v104_real_flag = _v104_flag_independently(_v104_policy_text)

if not _v104_have_git:
    expect("VELDO-0104 STOOD DOWN by name - git is not installed here, so the repository rows cannot run", True)
else:
    # A repository with the shape a landing actually has: the review commit, a fix, a gate stamp, a
    # proof commit, a ship commit (specs only), a second fix, a third fix in the suites.
    _v104_repo = _v104_tmp / "repo"
    (_v104_repo / "specs").mkdir(parents=True)
    _v104_bundle = _v104_repo / "proof" / "VELDO-9104"
    _v104_bundle.mkdir(parents=True)
    _v104_env = dict(_v104_os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")

    def _v104_git(*a):
        return _v104_sp.run(["git", "-C", str(_v104_repo), *a], check=True, capture_output=True, text=True, env=_v104_env).stdout.strip()

    def _v104_commit(msg, **files):
        for rel, body in files.items():
            p = _v104_repo / rel.replace("__", "/")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body)
        _v104_git("add", "-A")
        _v104_git("commit", "-q", "-m", msg)
        return _v104_git("rev-parse", "HEAD")

    _v104_git("init", "-q")
    _v104_R = _v104_commit("reviewed", **{"specs__VELDO-9104-fixture.md": "---\nid: VELDO-9104\nstatus: proven\n---\n",
                                          "organ.py": "def guard(x):\n    return 'accepted'\n", ".veldo__last_verify": "0\n"})
    _v104_F1 = _v104_commit("fix 1", **{"organ.py": "def guard(x):\n    return 'refused' if x.startswith('a:') else 'accepted'\n"})
    _v104_STAMP = _v104_commit("gate stamp", **{".veldo__last_verify": "1\n", ".veldo__events.jsonl": "{}\n"})
    _v104_PROOF = _v104_commit("proof bundle", **{"proof__VELDO-9104__README.md": "# proof\n"})
    _v104_SHIP = _v104_commit("shipped", **{"specs__VELDO-9104-fixture.md": "---\nid: VELDO-9104\nstatus: shipped\n---\n", "specs__index.md": "| VELDO-9104 | shipped |\n"})
    _v104_F2 = _v104_commit("fix 2", **{"organ.py": "RESERVED = ('a:',)\n\ndef guard(x):\n    return 'refused' if x.startswith(RESERVED) else 'accepted'\n"})
    _v104_F3 = _v104_commit("fix 3", **{"scripts__suites__50_veldo_9104_rows.py": "expect('row', True)\n"})

    # The REVIEWER's evidence in the bundle: a verified capsule per finding, naming the reviewed commit.
    def _v104_capsule(bundle, fid, commit):
        d = _v104_Path(bundle) / "capsules" / fid
        d.mkdir(parents=True)
        (d / "repro.py").write_text(f"print('reproduction for {fid}')\n")
        CAP104.write_manifest(d, fid, commit, ["python3", CAP104.MOUNT + "/repro.py"],
                              {"kind": "stdout_contains", "value": "reproduction"}, "the reviewer's observation")
        return d

    _v104_capsule(_v104_bundle, "F-1", _v104_R)
    _v104_capsule(_v104_bundle, "F-2", _v104_R)

    _v104_ok = {k: {"status": "passed"} for k in FV104.RESULT_KEYS}
    _v104_runner = {"schema": FV104.SCHEMA, "reviewed_commit": _v104_R, "fixed_commit": _v104_F2,
                    "findings": [{"finding_id": "F-1", "results": _v104_ok, "closed": True},
                                 {"finding_id": "F-2", "results": {**_v104_ok, "row_mutant_red": {"status": "failed"}}, "closed": False}],
                    "closed": ["F-1"], "open": ["F-2"]}
    _v104_assess = {"schema": "veldo.assessment/v1", "reviewed_commit": _v104_R, "fixed_commit": _v104_F2,
                    "per_finding": {"F-1": {"status": "closed", "reason": "the guard rejects the id"},
                                    "F-2": {"status": "closed", "reason": "looks closed to me"}},
                    "provenance": {"harness": "claude-code-headless", "model": "claude-fable-5-1", "tokens": 41900, "wall_seconds": 12.3}}
    _v104_rec = FV104.write_record(_v104_runner, _v104_assess, "VELDO-9104", _v104_repo, _v104_bundle)
    _v104_rec_disk = _v104_json.loads((_v104_bundle / FV104.RECORD_FILE).read_text())
    _v104_kept = _v104_json.loads((_v104_bundle / FV104.RECORD_DIR / f"{_v104_F2[:12]}.json").read_text())
    _v104_stale_refused = False
    try:
        FV104.write_record(dict(_v104_runner, fixed_commit=_v104_F3), _v104_assess, "VELDO-9104", _v104_repo, _v104_bundle)
    except FV104.ValidationError as e:
        _v104_stale_refused = "disagree on fixed_commit" in str(e)

    _v104_man = {"schema": "veldo.proof/v1", "spec_id": "VELDO-9104", "commit": _v104_F2}
    _v104_complete = {**_v104_rec, "findings": [dict(f, results=_v104_ok, assessor={"status": "closed", "reason": "r"}, closed=True) for f in _v104_rec["findings"]], "open": [], "closed": ["F-1", "F-2"]}
    _v104_c_ok = FV104.check_bundle(_v104_man, _v104_complete, _v104_repo, _v104_bundle, True, "proven")
    _v104_c_none = FV104.check_bundle(_v104_man, None, _v104_repo, _v104_bundle, True, "proven")
    _v104_c_open = FV104.check_bundle(_v104_man, _v104_rec, _v104_repo, _v104_bundle, True, "proven")
    _v104_c_wrong = FV104.check_bundle(_v104_man, {**_v104_complete, "fixed_commit": _v104_F1}, _v104_repo, _v104_bundle, True, "proven")
    _v104_c_partial = FV104.check_bundle(_v104_man, {**_v104_complete, "findings": _v104_complete["findings"][:1]}, _v104_repo, _v104_bundle, True, "proven")
    _v104_c_atreview = FV104.check_bundle({**_v104_man, "commit": _v104_R}, None, _v104_repo, _v104_bundle, True, "proven")
    _v104_noev = _v104_tmp / "bundle_without_evidence"
    _v104_noev.mkdir()
    _v104_c_noev = FV104.check_bundle(_v104_man, None, _v104_repo, _v104_noev, True, "proven")
    _v104_codes = lambda c: [p["code"] for p in c["problems"]]

    # The ONE call site, run as a child process on a bundle built from THIS repository's own commits.
    _v104_head = _v104_sp.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    _v104_prev = _v104_sp.run(["git", "-C", str(ROOT), "rev-parse", "HEAD~1"], capture_output=True, text=True).stdout.strip()
    _v104_glue_dir = _v104_tmp / "glue"
    _v104_glue_dir.mkdir()
    _v104_capsule(_v104_glue_dir, "G-1", _v104_prev)
    (_v104_glue_dir / "manifest.json").write_text(_v104_json.dumps({
        "schema": "veldo.proof/v1", "spec_id": "VELDO-0104", "commit": _v104_head, "producer": "suite 43",
        "criteria": [], "checks": [], "rollback": "none"}))
    _v104_g = _v104_sp.run([_v104_sys.executable, str(ROOT / ".veldo" / "validate.py"), "proof", str(_v104_glue_dir / "manifest.json")],
                           capture_output=True, text=True, cwd=str(ROOT))
    _v104_gout = _v104_g.stdout + _v104_g.stderr
    _v104_shipped_dir = _v104_tmp / "glue_not_applicable"
    _v104_shipped_dir.mkdir()
    (_v104_shipped_dir / "manifest.json").write_text(_v104_json.dumps({
        "schema": "veldo.proof/v1", "spec_id": "VELDO-0104", "commit": _v104_head, "producer": "suite 43",
        "criteria": [], "checks": [], "rollback": "none"}))
    _v104_g2 = _v104_sp.run([_v104_sys.executable, str(ROOT / ".veldo" / "validate.py"), "proof", str(_v104_shipped_dir / "manifest.json")],
                            capture_output=True, text=True, cwd=str(ROOT))
    _v104_gout2 = _v104_g2.stdout + _v104_g2.stderr

    # --- AC1 -------------------------------------------------------------------------------------
    expect("VELDO-0104 AC1 proofcheck/record-binds-commit: validation.json is composed from the runner's and the assessor's "
           "records (a finding closes only when all four results passed AND the assessor said closed), is kept under "
           "validation/<fix-commit>.json as well, and an assessment of a DIFFERENT fix commit is refused rather than composed; "
           "over the bundle at F2 the rule accepts the complete record, names no-validation-record for a missing one, "
           "finding-not-closed with the finding and the result for an open one, validation-record-does-not-name-this-commit "
           "for a record naming F1, and finding-not-covered for a record that omits a finding whose capsule the reviewer "
           "saved; and `validate.py proof`, run as a child process on a bundle carrying a capsule from this repository's own "
           "previous commit, reaches the check and names the missing record, refusing exactly when the flag is on",
           _v104_rec["closed"] == ["F-1"] and _v104_rec["open"] == ["F-2"] and _v104_rec_disk == _v104_rec and _v104_kept == _v104_rec
           and _v104_rec["schema"] == FV104.RECORD_SCHEMA and _v104_stale_refused
           and _v104_c_ok["applicable"] and _v104_c_ok["problems"] == [] and _v104_c_ok["refuses"] is False
           and _v104_codes(_v104_c_none) == [FV104.NO_RECORD] and _v104_c_none["refuses"] is True
           and FV104.FINDING_NOT_CLOSED in _v104_codes(_v104_c_open)
           and any("F-2" in p["text"] and "row_mutant_red" in p["text"] for p in _v104_c_open["problems"])
           and _v104_codes(_v104_c_wrong) == [FV104.RECORD_WRONG_COMMIT] and _v104_F1[:12] in _v104_c_wrong["problems"][0]["text"]
           and FV104.FINDING_NOT_COVERED in _v104_codes(_v104_c_partial)
           and FV104.NO_RECORD in _v104_gout and (_v104_g.returncode != 0) is bool(_v104_real_flag))

    _v104_M1 = _v104_organ("anycommit", [('        if record.get("fixed_commit") != commit:', '        if False:')])
    _v104_m1 = _v104_M1.check_bundle(_v104_man, {**_v104_complete, "fixed_commit": _v104_F1}, _v104_repo, _v104_bundle, True, "proven")
    expect("VELDO-0104 AC1 proofcheck/record-binds-commit DRIVEN (the declared falsifier): with the commit comparison removed "
           "in a copy, a record naming F1 is accepted for the bundle at F2 on the copy and refused by the original",
           _v104_m1["problems"] == [] and _v104_codes(_v104_c_wrong) == [FV104.RECORD_WRONG_COMMIT])

    # Applicability is derived from the reviewer's evidence, not declared by the author.
    _v104_M1b = _v104_organ("declared", [('    ev = review_evidence(proof_dir, capsule_mod)\n    reviewed = ev.get("commit")',
                                          '    ev = {"commit": manifest.get("reviewed_commit"), "findings": [], "source": "the manifest"}\n    reviewed = ev.get("commit")')])
    _v104_m1b = _v104_M1b.check_bundle(_v104_man, None, _v104_repo, _v104_bundle, True, "proven")
    _v104_m1b_declared = _v104_M1b.check_bundle({**_v104_man, "reviewed_commit": _v104_R}, None, _v104_repo, _v104_bundle, True, "proven")
    expect("VELDO-0104 AC1 proofcheck/applicability-is-derived: the bundle is subject to the rule because it carries the "
           "reviewer's verified capsules taken at an earlier commit, with no reviewed_commit field in the manifest at all; a "
           "bundle carrying no review evidence is not applicable and silent; a bundle whose own commit IS the reviewed one is "
           "not applicable; DRIVEN: a copy that takes applicability from the manifest instead lets the same bundle through "
           "when the author omits the field, and applies only when the author volunteers it",
           _v104_c_none["applicable"] is True and "reviewed_commit" not in _v104_man
           and _v104_c_none["reviewed_commit"] == _v104_R and "capsule" in str(_v104_c_none["evidence"])
           and _v104_c_noev["applicable"] is False and _v104_c_noev["problems"] == []
           and _v104_c_atreview["applicable"] is False
           and _v104_m1b["applicable"] is False and _v104_m1b_declared["applicable"] is True)

    # --- AC2 -------------------------------------------------------------------------------------
    _v104_man3 = {**_v104_man, "commit": _v104_F3}
    _v104_rec3 = {**_v104_rec, "fixed_commit": _v104_F3}
    _v104_renamed = {**_v104_rec3, "findings": [dict(f, id=f["id"].replace("F-", "G-")) for f in _v104_rec3["findings"]], "open": ["G-2"], "closed": ["G-1"]}
    _v104_c3 = FV104.check_bundle(_v104_man3, _v104_rec3, _v104_repo, _v104_bundle, True, "proven")
    _v104_c3_renamed = FV104.check_bundle(_v104_man3, _v104_renamed, _v104_repo, _v104_bundle, True, "proven")
    _v104_c3_shipped = FV104.check_bundle(_v104_man3, _v104_renamed, _v104_repo, _v104_bundle, True, "shipped")
    _v104_c2_shipped = FV104.check_bundle(_v104_man, _v104_complete, _v104_repo, _v104_bundle, True, "shipped")
    _v104_git_rounds = [r["commit"] for r in FV104.fix_rounds(_v104_repo, _v104_R, _v104_F3)]
    # A squash: ONE commit on top of the review carrying everything the three fix commits carried,
    # built with plumbing so the working tree and the bundle beside it are untouched.
    _v104_SQ = _v104_git("commit-tree", _v104_F3 + "^{tree}", "-p", _v104_R, "-m", "everything at once")
    _v104_sq_git = FV104.fix_rounds(_v104_repo, _v104_R, _v104_SQ)
    _v104_sq_counted = FV104.round_count(_v104_repo, _v104_R, _v104_SQ, _v104_bundle)
    expect("VELDO-0104 AC2 proofcheck/round-cap-survives-rename: a round is a commit that changes code or suites, so F1, F2 and "
           "F3 count while the gate stamp, the proof commit and the ship commit (specs only) do not, and the count is NOT "
           "filtered by the spec's footprint, which a fix commit could rewrite; the bundle at F2 has two rounds and is not "
           "parked, at F3 it has three, exceeds the cap and is parked with its open findings listed; renaming every finding in "
           "the record changes neither; a parked item whose spec says shipped is refused by name and a two-round shipped item "
           "is not; and a squashed history that shows ONE commit still counts the rounds the bundle's own kept records name",
           _v104_git_rounds == [_v104_F1, _v104_F2, _v104_F3]
           and _v104_c3["rounds"] == 3 and _v104_c3["parked"] is True and FV104.ROUND_CAP_EXCEEDED in _v104_codes(_v104_c3)
           and _v104_c3_renamed["rounds"] == 3 and _v104_c3_renamed["parked"] is True
           and FV104.PARKED_SHIPPED not in _v104_codes(_v104_c3_renamed) and FV104.PARKED_SHIPPED in _v104_codes(_v104_c3_shipped)
           and _v104_c_ok["rounds"] == 2 and _v104_c_ok["parked"] is False and _v104_c2_shipped["parked"] is False
           and len(_v104_sq_git) == 1 and _v104_sq_counted["count"] == 2 and _v104_sq_counted["from_records"] == [_v104_F2])

    _v104_M2 = _v104_organ("renamereset", [('    counted = round_count(repo, reviewed, commit, proof_dir)\n    out["rounds"] = counted["count"]',
                                            '    counted = round_count(repo, reviewed, commit, proof_dir)\n'
                                            '    if isinstance(record, dict) and record.get("findings") and all(str(f.get("id", "")).startswith("G-") for f in record["findings"]):\n'
                                            '        counted = {"count": 1, "from_git": [], "from_records": []}\n'
                                            '    out["rounds"] = counted["count"]')])
    _v104_m2 = _v104_M2.check_bundle(_v104_man3, _v104_renamed, _v104_repo, _v104_bundle, True, "proven")
    expect("VELDO-0104 AC2 proofcheck/round-cap-survives-rename DRIVEN (the declared falsifier): with a copy that restarts the "
           "round count when the findings carry new names, the renamed record at F3 is not parked on the copy and parked on "
           "the original",
           _v104_m2["parked"] is False and _v104_m2["rounds"] == 1 and _v104_c3_renamed["parked"] is True)

    # --- AC3 -------------------------------------------------------------------------------------
    _v104_c_none_off = FV104.check_bundle(_v104_man, None, _v104_repo, _v104_bundle, False, "proven")
    _v104_c3_off = FV104.check_bundle(_v104_man3, _v104_renamed, _v104_repo, _v104_bundle, False, "shipped")
    expect("VELDO-0104 AC3 proofcheck/flag-off-is-a-warning: the flag reads true from an inline map and from a block, with a "
           "trailing comment or quotes in either, and false when absent, false, or the policy file is missing, and a # inside a "
           "quoted string is text rather than a comment; the row decides what the real policy says with its own reader, not the "
           "organ's; with the flag off the same bundles report the same problems and refuse nothing, with it on they refuse; "
           "the proof mode prints the flag state for an applicable bundle AND for one that is not applicable; and "
           ".veldo/policy.yaml is a protected path, so flipping the flag is a reviewed change",
           _v104_flags == {"absent": False, "inline_on": True, "inline_on_comment": True, "block_on_comment": True,
                           "block_quoted": True, "block_off": False, "hash_in_a_string": False, "missing_file": False}
           and FV104.read_flag(ROOT / ".veldo" / "policy.yaml") == _v104_real_flag
           and _v104_codes(_v104_c_none_off) == [FV104.NO_RECORD] and _v104_c_none_off["refuses"] is False
           and _v104_codes(_v104_c3_off) == _v104_codes(_v104_c3_shipped) and _v104_c3_off["refuses"] is False
           and _v104_c3_shipped["refuses"] is True
           and ("fix validation required" if _v104_real_flag else "fix validation advisory") in _v104_gout
           and ("fix validation required" if _v104_real_flag else "fix validation advisory") in _v104_gout2
           and "not applicable" in _v104_gout2 and _v104_g2.returncode == 0
           and '{path: ".veldo/policy.yaml"' in _v104_policy_text)

    _v104_M3 = _v104_organ("alwaysrefuse", [('    out["refuses"] = bool(required and problems)', '    out["refuses"] = bool(problems)')])
    _v104_m3 = _v104_M3.check_bundle(_v104_man, None, _v104_repo, _v104_bundle, False, "proven")
    expect("VELDO-0104 AC3 proofcheck/flag-off-is-a-warning DRIVEN (the declared falsifier): with a copy that refuses whatever "
           "the flag says, the missing record refuses on the copy with the flag off and warns on the original",
           _v104_m3["refuses"] is True and _v104_c_none_off["refuses"] is False)

    # --- the whole chain, once, against the real organs ------------------------------------------
    # Every row above exercises one organ. This one runs the chain PLAN-0020 actually describes:
    # a reviewer's capsule in the bundle, the runner's four results, the projection to the reader, a
    # reader's verdict (a fake harness, so nothing is spent), the validation record composed from both,
    # and the proof check over the bundle. Nothing here is a stub except the model call.
    _v104_FV = _v104_load("v104_runner", ROOT / ".veldo" / "fix_validation.py")
    _v104_FA = _v104_load("v104_assessor", ROOT / ".veldo" / "fix_assessor.py")
    _v104_e2e = _v104_tmp / "e2e"
    _v104_erepo = _v104_e2e / "repo"
    (_v104_erepo / "scripts" / "suites").mkdir(parents=True)

    def _v104_egit(*a):
        return _v104_sp.run(["git", "-C", str(_v104_erepo), *a], check=True, capture_output=True, text=True, env=_v104_env).stdout.strip()

    (_v104_erepo / "scripts" / "suites" / "shared.py").write_text(
        "from pathlib import Path\nROOT = Path(__file__).resolve().parents[2]\ndef expect(n, c):\n    assert c, n\n")
    (_v104_erepo / "scripts" / "suites" / "60_rows.py").write_text(
        "import importlib.util as ilu\n"
        "s = ilu.spec_from_file_location('organ', ROOT / 'organ.py'); organ = ilu.module_from_spec(s); s.loader.exec_module(organ)\n"
        "expect('ROW guard/rejects-reserved: the guard refuses a reserved id', organ.guard('authority:x') == 'refused')\n")
    (_v104_erepo / "organ.py").write_text("def guard(i):\n    return 'accepted'\n")
    _v104_egit("init", "-q"); _v104_egit("add", "-A"); _v104_egit("commit", "-q", "-m", "reviewed")
    _v104_eR = _v104_egit("rev-parse", "HEAD")
    (_v104_erepo / "organ.py").write_text("RESERVED = ('authority:',)\n\ndef guard(i):\n    if i.startswith(RESERVED):\n        return 'refused'\n    return 'accepted'\n")
    _v104_egit("add", "-A"); _v104_egit("commit", "-q", "-m", "fix")
    _v104_eF = _v104_egit("rev-parse", "HEAD")

    _v104_ebundle = _v104_erepo / "proof" / "VELDO-9999"
    _v104_ecaps = _v104_ebundle / "capsules" / "F-1"
    _v104_ecaps.mkdir(parents=True)
    (_v104_ecaps / "repro.py").write_text("import organ\nprint('reserved ->', organ.guard('authority:x'))\n")
    CAP104.write_manifest(_v104_ecaps, "F-1", _v104_eR, ["python3", CAP104.MOUNT + "/repro.py"],
                          {"kind": "stdout_contains", "value": "reserved -> accepted"}, "the guard accepts a reserved id")
    _v104_eplan = {"repo": str(_v104_erepo), "worktree": str(_v104_erepo), "reviewed_commit": _v104_eR,
                   "fixed_commit": _v104_eF, "row_deadline_seconds": 60,
                   "findings": [{"id": "F-1", "capsule": str(_v104_ecaps),
                                 "row": {"suite": "60_rows", "label": "guard/rejects-reserved",
                                         "mutant": {"file": "organ.py", "edits": [["    if i.startswith(RESERVED):\n        return 'refused'\n", ""]]}}}]}
    _v104_runner = _v104_FV.validate(_v104_eplan, workdir=_v104_e2e / "runs")
    _v104_proj = _v104_FV.assessor_capsule_results(_v104_runner)

    _v104_efake = _v104_e2e / "fake.py"
    _v104_efake.write_text(
        "import json, os, sys\n"
        "open(os.environ['V104_BRIEF'], 'w').write(sys.stdin.read())\n"
        "v = {'findings': [{'id': 'F-1', 'status': os.environ['V104_VERDICT'], 'reason': 'read the diff'}], 'new_defects': []}\n"
        "print(json.dumps({'type': 'result', 'model': 'claude-fable-5-1', 'usage': {'input_tokens': 1000, 'output_tokens': 50},\n"
        "                  'duration_ms': 10, 'structured_output': v, 'result': json.dumps(v)}))\n")
    _v104_ediff = _v104_sp.run(["git", "-C", str(_v104_erepo), "diff", _v104_eR, _v104_eF], capture_output=True, text=True).stdout

    def _v104_assess(verdict, tag):
        wd = _v104_e2e / ("assess_" + tag)
        wd.mkdir()
        _v104_os.environ["V104_BRIEF"] = str(wd / "brief.txt")
        _v104_os.environ["V104_VERDICT"] = verdict
        rec = _v104_FA.assess({"reviewed_commit": _v104_eR[:12], "fixed_commit": _v104_eF[:12],
                               "findings": [{"id": "F-1", "text": "the guard accepts a reserved id"}],
                               "capsule_results": _v104_proj, "diff": _v104_ediff},
                              wd, harness=[_v104_sys.executable, str(_v104_efake)], timeout=60)
        rec["reviewed_commit"], rec["fixed_commit"] = _v104_eR, _v104_eF
        return rec, (wd / "brief.txt").read_text()

    _v104_a_closed, _v104_brief_seen = _v104_assess("closed", "closed")
    _v104_a_open, _ = _v104_assess("not_closed", "open")
    _v104_erec = FV104.write_record(_v104_runner, _v104_a_closed, "VELDO-9999", _v104_erepo, _v104_ebundle)
    _v104_erec_open = FV104.write_record(_v104_runner, _v104_a_open, "VELDO-9999", _v104_erepo, _v104_ebundle)
    _v104_eman = {"schema": "veldo.proof/v1", "spec_id": "VELDO-9999", "commit": _v104_eF}
    _v104_echeck = FV104.check_bundle(_v104_eman, _v104_erec, _v104_erepo, _v104_ebundle, True, "proven")
    _v104_echeck_open = FV104.check_bundle(_v104_eman, _v104_erec_open, _v104_erepo, _v104_ebundle, True, "proven")
    _v104_echeck_none = FV104.check_bundle(_v104_eman, None, _v104_erepo, _v104_ebundle, True, "proven")
    _v104_M_ignore = _v104_organ("ignoreverdict", [('            vst = (f.get("assessor") or {}).get("status")\n            if vst != "closed":', '            vst = "closed"\n            if False:')])
    _v104_eopen_m = _v104_M_ignore.check_bundle(_v104_eman, _v104_erec_open, _v104_erepo, _v104_ebundle, True, "proven")
    expect("VELDO-0104 AC1 proofcheck/the-whole-chain: the chain PLAN-0020 describes runs end to end against the real organs "
           "with only the model call faked: the reviewer's capsule in the bundle reproduces on the reviewed commit and not on "
           "the fix, the author's row reds with its mutant and is green without it, the runner says it closes nothing and hands "
           "its evidence to the reader, the reader's verdict and those results compose one validation record, and the proof "
           "check accepts the bundle; the SAME run with the reader saying not_closed is refused by name although all four "
           "mechanical results passed, and with no record at all it is refused as having none; DRIVEN: a copy of the check that "
           "does not consult the reader's verdict accepts the bundle the reader rejected",
           all(_v104_runner["findings"][0]["results"][k]["status"] == "passed" for k in FV104.RESULT_KEYS)
           and _v104_runner["closes_findings"] is False and _v104_runner["all_results_passed"] == ["F-1"]
           and "exit_code_changed" in _v104_brief_seen and _v104_a_closed["closed"] == ["F-1"]
           and _v104_a_closed["provenance_missing"] is False
           and _v104_erec["closed"] == ["F-1"] and _v104_erec["rounds"]["count"] == 1 and _v104_erec["parked"] is False
           and _v104_echeck["applicable"] is True and _v104_echeck["problems"] == [] and _v104_echeck["refuses"] is False
           and _v104_erec_open["closed"] == [] and FV104.ASSESSOR_NOT_CLOSED in [p["code"] for p in _v104_echeck_open["problems"]]
           and _v104_echeck_open["refuses"] is True
           and [p["code"] for p in _v104_echeck_none["problems"]] == [FV104.NO_RECORD]
           and _v104_eopen_m["problems"] == [])

    # A bundle can carry a review taken in a repository whose history was frozen and not carried over.
    # THIS repository carries many: their verdicts name commits that do not exist here. Counting rounds
    # over a history nobody has is not a question with an answer, and calling it a failure would refuse
    # the whole landed corpus the moment the owner turned the flag on, which is the same as having no
    # flag at all.
    _v104_elsewhere = _v104_tmp / "bundle_from_elsewhere"
    _v104_elsewhere.mkdir()
    (_v104_elsewhere / "verdict.json").write_text(_v104_json.dumps({"schema": "veldo.verdict/v1", "commit": "0" * 40, "verdict": "pass"}))
    _v104_man_elsewhere = {"schema": "veldo.proof/v1", "spec_id": "VELDO-9104", "commit": _v104_eF if _v104_have_git else "1" * 40}
    _v104_c_elsewhere = FV104.check_bundle(_v104_man_elsewhere, None, _v104_erepo, _v104_elsewhere, True, "proven")
    _v104_M_nocheck = _v104_organ("commitsanywhere", [(MISSING_LINE_104, "    missing = []")])
    _v104_nocheck_raised = None
    try:
        _v104_M_nocheck.check_bundle(_v104_man_elsewhere, None, _v104_erepo, _v104_elsewhere, True, "proven")
        _v104_nocheck_raised = "no"
    except Exception as _v104_e:
        _v104_nocheck_raised = type(_v104_e).__name__
    # And the whole landed corpus of this repository, through the real command, with nothing refused.
    _v104_all = _v104_sp.run([_v104_sys.executable, str(ROOT / ".veldo" / "validate.py"), "all"],
                             capture_output=True, text=True, cwd=str(ROOT))
    expect("VELDO-0104 AC3 proofcheck/a-review-from-a-history-nobody-has: a bundle whose review evidence names a commit this "
           "repository does not have is NOT applicable, and says which commit it could not find, rather than failing to count "
           "rounds over a history nobody has; run over this repository's own landed corpus the check reports on every bundle "
           "and refuses none of them, and no git error reaches the output; DRIVEN: a copy that does not ask whether the "
           "commits are here raises trying to count between them, which with the flag on would refuse every bundle carrying a "
           "review from the predecessor repository",
           _v104_c_elsewhere["applicable"] is False and _v104_c_elsewhere.get("unknown_commits") == ["0" * 40]
           and _v104_c_elsewhere["problems"] == []
           and _v104_nocheck_raised == "ValidationError"
           and _v104_all.returncode == 0 and "separate paths from revisions" not in (_v104_all.stdout + _v104_all.stderr)
           and "does not have" in _v104_all.stdout)
