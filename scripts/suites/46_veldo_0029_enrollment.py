"""VELDO-0029: one signed binding decides which authority a clone writes to (PLAN-0019 W14).

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, so its declared
prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 46_veldo_0029_enrollment

WHAT IS UNDER TEST. .veldo/control_enrollment.py, over REAL git repositories built under a temporary
directory: two clones of different repositories, a linked worktree, a clone replaced at the same path
by a different repository and by a fresh clone of the same one. The signer is an HMAC the suite
supplies, because the module holds no key material and takes signing and verification as callables;
what the rows turn on is that the signature is CHECKED, not how strong it is. Every declared
falsifier is applied to a COPY of the organ and required to turn its named row red while the
unmutated organ passes it.

WHAT IT DELIBERATELY DOES NOT TEST. Reaching the authority. The local socket is VELDO-0107, the SSH
relay is VELDO-0108 and the unreachable case is VELDO-0109. This item answers WHICH store, and its
rows stop there.
"""
import hashlib as _v29_hashlib
import hmac as _v29_hmac
import importlib.util as _v29_ilu
import os as _v29_os
import shutil as _v29_shutil
import subprocess as _v29_sp
import tempfile as _v29_tf
from pathlib import Path as _v29_Path

_v29_tmp = _v29_Path(_v29_tf.mkdtemp(prefix="v29"))
_v29_have_git = _v29_shutil.which("git") is not None
_v29_KEY = b"the owner's key, which this module never sees"


def _v29_load(name, path):
    spec = _v29_ilu.spec_from_file_location(name, path)
    m = _v29_ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _v29_organ(tag, edits=()):
    """A copy of the organ, so a mutant is that organ alone."""
    d = _v29_tmp / ("organ_" + tag)
    d.mkdir()
    src = (ROOT / ".veldo" / "control_enrollment.py").read_text()
    for old, new in edits:
        assert src.count(old) == 1, (old[:70], src.count(old))
        src = src.replace(old, new)
    (d / "control_enrollment.py").write_text(src)
    return _v29_load("v29_enroll_" + tag, d / "control_enrollment.py")


def _v29_sign(payload):
    return "hmac-sha256:" + _v29_hmac.new(_v29_KEY, payload, _v29_hashlib.sha256).hexdigest()


def _v29_verify(payload, signature):
    return _v29_hmac.compare_digest(_v29_sign(payload), signature)


EN29 = _v29_organ("main")
HOST = "workstation-1"
DOMAIN = "11111111-1111-1111-1111-111111111111"
STORE = "22222222-2222-2222-2222-222222222222"
DOMAIN_B = "33333333-3333-3333-3333-333333333333"
STORE_B = "44444444-4444-4444-4444-444444444444"

# The mutation anchors, each rebuilding a specific wrong design rather than breaking something near it.
VERIFY_29 = '    if not verify(binding_signed_bytes(binding), binding["signature"]):'
IDENT_29 = '    if sorted(binding["repository_root_commit"]) != sorted(ident["root_commits"]):'
RESOLVE_29 = '    binding = read_binding(workspace)'
REFUSE_29 = '''        raise EnrollmentRefused(reason, text + ('''

if not _v29_have_git:
    expect("VELDO-0029 STOOD DOWN by name - git is not installed here, so every row needs a real "
           "repository and none of them can run", True)
else:
    _v29_env = dict(_v29_os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                    GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")

    def _v29_git(repo, *a):
        return _v29_sp.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True,
                           env=_v29_env).stdout.strip()

    def _v29_repo(name, seed):
        d = _v29_tmp / name
        d.mkdir(parents=True)
        _v29_git(d, "init", "-q")
        _v29_git(d, "checkout", "-q", "-b", "trunk")
        (d / "seed.txt").write_text(seed + "\n")
        _v29_git(d, "add", "-A")
        _v29_git(d, "commit", "-q", "-m", "seed " + seed)
        return d

    # TWO DIFFERENT REPOSITORIES, each with its own root commit, and a linked worktree of the first.
    _v29_A = _v29_repo("repoA", "alpha")
    _v29_B = _v29_repo("repoB", "beta")
    _v29_WT = _v29_tmp / "worktreeA"
    _v29_git(_v29_A, "worktree", "add", "-q", "--detach", str(_v29_WT), "HEAD")
    _v29_STORE_A = str(_v29_tmp / "authorityA" / "control.sqlite3")
    _v29_STORE_Bp = str(_v29_tmp / "authorityB" / "control.sqlite3")

    _v29_bind_A = EN29.enroll(_v29_A, DOMAIN, STORE, _v29_STORE_A, HOST, 3, _v29_sign,
                              "dmitry", "2026-09-21T00:00:00Z")
    _v29_bind_B = EN29.enroll(_v29_B, DOMAIN_B, STORE_B, _v29_STORE_Bp, HOST, 1, _v29_sign,
                              "dmitry", "2026-09-21T00:00:00Z")

    def _v29_resolve(organ, workspace, **kw):
        try:
            return ("store", organ.resolve_store(workspace, _v29_verify, kw.pop("host", HOST), **kw))
        except organ.EnrollmentRefused as e:
            return ("refused", e.reason)

    # ---- AC1: the binding is the answer, and it is the answer because it is SIGNED ---------------
    _v29_a = _v29_resolve(EN29, _v29_A)
    _v29_b = _v29_resolve(EN29, _v29_B)
    # The linked worktree shares repoA's common directory, so it reads repoA's binding and resolves
    # to the same store: separate working copies of one clone are one enrolled clone.
    _v29_wt = _v29_resolve(EN29, _v29_WT)
    # A binding whose bytes were edited after signing.
    _v29_tampered_dir = _v29_tmp / "tampered"
    _v29_shutil.copytree(_v29_A, _v29_tampered_dir, symlinks=True)
    _v29_tp = EN29.binding_path(_v29_tampered_dir)
    import json as _v29_json
    _v29_doc = _v29_json.loads(_v29_Path(_v29_tp).read_text())
    _v29_doc["store_path"] = _v29_STORE_Bp
    _v29_Path(_v29_tp).write_text(_v29_json.dumps(_v29_doc))
    _v29_tampered = _v29_resolve(EN29, _v29_tampered_dir)
    _v29_M_nosig = _v29_organ("nosig", [(VERIFY_29, "    if False:")])
    _v29_tampered_mut = _v29_resolve(_v29_M_nosig, _v29_tampered_dir)

    expect("VELDO-0029 AC1 enrollment/an-unsigned-binding-is-not-a-binding: two clones of DIFFERENT "
           "repositories, each enrolled by the real call, resolve to their own store and not to each other's; "
           "a linked worktree resolves to the same store as the clone it belongs to, because separate working "
           "copies of one clone are one enrolled clone; and a binding edited after signing is REFUSED as "
           "signature_invalid rather than obeyed. DRIVEN: a copy that skips the signature check hands back the "
           "edited binding's store, which is the whole record reduced to a file anyone can write",
           _v29_a == ("store", _v29_STORE_A) and _v29_b == ("store", _v29_STORE_Bp)
           and _v29_wt == ("store", _v29_STORE_A)
           and _v29_tampered == ("refused", "signature_invalid")
           and _v29_tampered_mut == ("store", _v29_STORE_Bp))

    # ---- AC2: the workspace is given, never inferred ---------------------------------------------
    # Every ambient source pointed at the OTHER enrolled repository, which is real and really
    # enrolled, so the row fails if the answer is right only because the alternative did not exist.
    _v29_before_cwd = _v29_os.getcwd()
    _v29_os.chdir(str(_v29_B))
    _v29_os.environ["VELDO_CONTROL_DB"] = _v29_STORE_Bp
    _v29_os.environ["VELDO_REPO"] = str(_v29_B)
    # GIT_DIR, GIT_WORK_TREE, GIT_COMMON_DIR and GIT_OBJECT_DIRECTORY each OVERRIDE `git -C`,
    # which is how the FIRST version of this module failed this row: with GIT_DIR set, its own
    # `git -C repoA rev-list` answered repoB's root commit while believing it had named repoA.
    _v29_os.environ["GIT_DIR"] = str(_v29_B / ".git")
    _v29_os.environ["GIT_WORK_TREE"] = str(_v29_B)
    _v29_os.environ["GIT_COMMON_DIR"] = str(_v29_B / ".git")
    _v29_os.environ["GIT_OBJECT_DIRECTORY"] = str(_v29_B / ".git" / "objects")
    try:
        _v29_under_ambient = _v29_resolve(EN29, _v29_A)
        _v29_ambient_ident = EN29.workspace_identity(_v29_A)["root_commits"]
        # The mutant resolves from the process's own directory when an explicit workspace was given,
        # which is exactly what control_db_path does today.
        _v29_M_cwd = _v29_organ("fromcwd", [
            (RESOLVE_29, "    workspace = os.getcwd()\n    binding = read_binding(workspace)")])
        _v29_under_ambient_mut = _v29_resolve(_v29_M_cwd, _v29_A)
    finally:
        _v29_os.chdir(_v29_before_cwd)
        for _v29_k in ("VELDO_CONTROL_DB", "VELDO_REPO", "GIT_DIR", "GIT_WORK_TREE",
                       "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY"):
            _v29_os.environ.pop(_v29_k, None)
    _v29_src29 = (ROOT / ".veldo" / "control_enrollment.py").read_text()

    expect("VELDO-0029 AC2 enrollment/ambient-sources-decide-nothing: with the process standing inside the "
           "OTHER enrolled repository, with VELDO_CONTROL_DB naming the other store and with GIT_DIR, "
           "GIT_WORK_TREE, GIT_COMMON_DIR and GIT_OBJECT_DIRECTORY all naming the other repository, "
           "resolving the first workspace still answers the first store and reading its identity still "
           "reads its own root commits. Those four are the point: each OVERRIDES `git -C`, so passing the "
           "workspace explicitly was NOT enough and the first version of this module failed here. It now "
           "reads the environment in exactly one place and only to strip every GIT_ variable from it by "
           "prefix, never to take a value, and contains no os.getcwd and no __file__ at all. DRIVEN: a copy that resolves "
           "from the process's current directory when an explicit workspace was given answers the other "
           "store, which is what the shipped control_db_path does today",
           _v29_under_ambient == ("store", _v29_STORE_A)
           and _v29_ambient_ident == EN29.root_commits(_v29_A)
           and "os.getcwd" not in _v29_src29 and "__file__" not in _v29_src29
           and _v29_src29.count("os.environ") == 1
           and 'if not k.startswith("GIT_")' in _v29_src29
           and _v29_under_ambient_mut == ("store", _v29_STORE_Bp))

    # ---- AC2, second row: the ambient resolver in control_store is CLOSED -----------------------
    # The defect this whole item exists to remove lived in control_store.control_db_path, which
    # derived a database from VELDO_CONTROL_DB or from `git rev-parse --git-common-dir` in the
    # process's current directory. It had NO CALLERS, so nothing was reaching the wrong database;
    # what existed was the means to, sitting where the next person to need a default would find it.
    # This row is the guard on that: it refuses without an explicit path, and the module derives
    # nothing.
    _v29_CS = _v29_load("v29_control_store", ROOT / ".veldo" / "control_store.py")
    _v29_cs_src = (ROOT / ".veldo" / "control_store.py").read_text()
    try:
        _v29_CS.control_db_path(None)
        _v29_no_arg = "answered"
    except Exception as e:  # noqa: BLE001 - the refusal's TYPE is asserted below, not caught by it
        _v29_no_arg = type(e).__name__
    _v29_explicit = _v29_CS.control_db_path(str(_v29_tmp / "explicit" / "control.sqlite3"))
    _v29_before_cwd2 = _v29_os.getcwd()
    _v29_os.chdir(str(_v29_B))
    _v29_os.environ["VELDO_CONTROL_DB"] = _v29_STORE_Bp
    try:
        _v29_under_ambient2 = _v29_CS.control_db_path(
            str(_v29_tmp / "explicit" / "control.sqlite3"))
    finally:
        _v29_os.chdir(_v29_before_cwd2)
        _v29_os.environ.pop("VELDO_CONTROL_DB", None)
    _v29_derives = ("os.environ.get(\"VELDO_CONTROL_DB\")" in _v29_cs_src
                    or "rev-parse\", \"--git-common-dir" in _v29_cs_src)

    expect("VELDO-0029 AC2 enrollment/the-ambient-store-resolver-is-closed: control_store.control_db_path "
           "REFUSES without an explicit path instead of deriving one, answers the path it is given, and "
           "answers that same path with the process standing in the other repository and VELDO_CONTROL_DB "
           "naming the other store. The module no longer contains either derivation. It had no callers, so "
           "nothing was reaching the wrong database; what existed was the means to, where the next person to "
           "want a default would find it, and this row is the guard that stops it coming back",
           _v29_no_arg == "StoreRefused"
           and _v29_explicit == _v29_under_ambient2
           and _v29_explicit.endswith("explicit/control.sqlite3")
           and not _v29_derives)

    # ---- AC3: a directory replaced under the same path is not the clone that enrolled ------------
    # Case one: the path now holds a DIFFERENT repository, with the old binding restored into it,
    # which is the shape of someone putting their configuration back after re-cloning.
    _v29_swap = _v29_tmp / "swapped"
    _v29_sp.run(["git", "clone", "-q", str(_v29_B), str(_v29_swap)], check=True, capture_output=True,
                env=_v29_env)
    _v29_binding_bytes = _v29_Path(EN29.binding_path(_v29_A)).read_bytes()
    _v29_uuid_bytes = _v29_Path(EN29.clone_uuid_path(_v29_A)).read_bytes()
    _v29_dst = _v29_Path(EN29.binding_path(_v29_swap))
    _v29_dst.parent.mkdir(parents=True, exist_ok=True)
    _v29_dst.write_bytes(_v29_binding_bytes)
    _v29_Path(EN29.clone_uuid_path(_v29_swap)).write_bytes(_v29_uuid_bytes)
    _v29_other_repo = _v29_resolve(EN29, _v29_swap)
    # Case two: a FRESH CLONE OF THE SAME REPOSITORY, with the binding restored but not the clone
    # uuid, which git never tracked. Same repository, same root commits, and still not the clone
    # that enrolled.
    _v29_fresh = _v29_tmp / "freshA"
    _v29_sp.run(["git", "clone", "-q", str(_v29_A), str(_v29_fresh)], check=True, capture_output=True,
                env=_v29_env)
    _v29_fd = _v29_Path(EN29.binding_path(_v29_fresh))
    _v29_fd.parent.mkdir(parents=True, exist_ok=True)
    _v29_fd.write_bytes(_v29_binding_bytes)
    _v29_same_repo = _v29_resolve(EN29, _v29_fresh)
    # Nothing local may appear because of a refusal.
    _v29_after = sorted(p.name for p in (_v29_fresh / ".git" / "veldo" / "control").iterdir())
    _v29_M_trustpath = _v29_organ("trustpath", [(IDENT_29, "    if False:")])
    _v29_other_repo_mut = _v29_resolve(_v29_M_trustpath, _v29_swap)

    expect("VELDO-0029 AC3 enrollment/a-replaced-clone-must-enroll-again: a directory replaced under the same "
           "path is refused in BOTH shapes, with the old binding restored into it either way. A different "
           "repository fails on root commits; a FRESH CLONE OF THE SAME REPOSITORY has the same root commits "
           "and is still refused, because the clone uuid git never tracked did not come with it. That second "
           "case is why identity is two things rather than one. The refusal creates no store and no ledger. "
           "DRIVEN: a copy that skips the repository identity check accepts the swapped directory and hands "
           "back the authority of a repository that is no longer there",
           _v29_other_repo == ("refused", "repository_identity_mismatch")
           and _v29_same_repo == ("refused", "clone_replaced")
           and _v29_after == ["enrollment.json"]
           and _v29_other_repo_mut[0] == "store")

    # ---- AC4: every refusal is named, and a refusal hands back no path ---------------------------
    _v29_notrepo = _v29_tmp / "notarepo"
    _v29_notrepo.mkdir()
    _v29_unenrolled = _v29_repo("unenrolled", "gamma")
    _v29_malformed = _v29_tmp / "malformed"
    _v29_shutil.copytree(_v29_A, _v29_malformed, symlinks=True)
    _v29_Path(EN29.binding_path(_v29_malformed)).write_text("{not json")
    _v29_seen = {
        "not_a_repository": _v29_resolve(EN29, _v29_notrepo),
        "not_enrolled": _v29_resolve(EN29, _v29_unenrolled),
        "malformed_binding": _v29_resolve(EN29, _v29_malformed),
        "signature_invalid": _v29_tampered,
        "repository_identity_mismatch": _v29_other_repo,
        "clone_replaced": _v29_same_repo,
        "host_binding_stale": _v29_resolve(EN29, _v29_A, host="another-machine"),
        "cross_domain": _v29_resolve(EN29, _v29_A, domain_uuid=DOMAIN_B),
        "store_uuid_mismatch": _v29_resolve(EN29, _v29_A, store_uuid=STORE_B),
        "generation_behind": _v29_resolve(EN29, _v29_A, minimum_generation=9),
    }
    _v29_named = {k: v == ("refused", k) for k, v in _v29_seen.items()}
    _v29_exhausted = sorted(_v29_seen) == sorted(EN29.REFUSALS)
    # The refusal carries the coordinates it judged, so a person reading it knows which directory
    # and which file were involved rather than only that routing failed.
    try:
        EN29.resolve_store(_v29_A, _v29_verify, "another-machine")
        _v29_carried = False
    except EN29.EnrollmentRefused as e:
        _v29_carried = ("workspace" in e.coordinates and "binding_path" in e.coordinates
                        and "another-machine" in e.message)
    _v29_M_handsback = _v29_organ("handsback", [
        (REFUSE_29, '        return binding["store_path"]\n        raise EnrollmentRefused(reason, text + (')])
    _v29_handsback = _v29_resolve(_v29_M_handsback, _v29_A, host="another-machine")

    expect("VELDO-0029 AC4 enrollment/a-refusal-hands-back-no-path: every one of the ten reasons in the "
           "module's own closed list is produced by a REAL binding and a real workspace rather than a "
           "hand-built record, each refusal names its own reason, and the list is EXHAUSTED, so a reason added "
           "later without a case fails this row. The refusal carries the workspace and the binding path it "
           "judged and the value it objected to. DRIVEN: a copy that returns the store alongside the problems "
           "hands a caller a path it may not use, which is worse than no answer because it looks like one",
           all(_v29_named.values()) and _v29_exhausted and _v29_carried
           and _v29_handsback == ("store", _v29_STORE_A))

    # ---- the negative control --------------------------------------------------------------------
    _v29_M_noop = _v29_organ("noop", [("import hashlib", "# additive no-op control\nimport hashlib")])
    _v29_control = [
        (_v29_resolve(_v29_M_noop, _v29_A), _v29_a),
        (_v29_resolve(_v29_M_noop, _v29_WT), _v29_wt),
        (_v29_resolve(_v29_M_noop, _v29_swap), _v29_other_repo),
        (_v29_resolve(_v29_M_noop, _v29_A, host="another-machine"), _v29_seen["host_binding_stale"]),
    ]
    expect("VELDO-0029 control enrollment/copying-is-not-what-changes-it: a copy of the organ carrying only an "
           "added comment answers exactly as the original does on all four cases the rows above turn on, so "
           "the difference each DRIVEN mutant shows is the mutation and not the copying",
           all(a == b for a, b in _v29_control))
