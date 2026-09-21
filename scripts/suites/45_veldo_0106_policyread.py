"""VELDO-0106: the owner's two settings are read exactly as written (PLAN-0020 W6).

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, so its declared
prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 45_veldo_0106_policyread

WHAT IS UNDER TEST. The read of .veldo/policy.yaml inside check_proof_bundle, and the shape gate on
the recorded start line in start_line_scope, both in .veldo/fix_validation_record.py. The policy is
a REAL FILE in each of the six shapes it can take, read through the real call site rather than a
hand-built dictionary, over a real git repository. The general parser the validator hands in is run
beside the reader on the same text, so a row fails if the call site is ever pointed back at it. The
three declared falsifiers are applied to COPIES of the organ, or to a copy of the shared parser, and
required to turn their named row red while the unmutated code passes it.
"""
import contextlib as _v106_ctx
import importlib.util as _v106_ilu
import io as _v106_io
import os as _v106_os
import shutil as _v106_shutil
import subprocess as _v106_sp
import tempfile as _v106_tf
from pathlib import Path as _v106_Path

_v106_tmp = _v106_Path(_v106_tf.mkdtemp(prefix="v106"))
_v106_have_git = _v106_shutil.which("git") is not None


def _v106_load(name, path):
    spec = _v106_ilu.spec_from_file_location(name, path)
    m = _v106_ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _v106_organ(tag, edits=()):
    """A copy of the record organ with its siblings beside it, so a mutant is that organ alone."""
    d = _v106_tmp / ("organ_" + tag)
    d.mkdir()
    _v106_shutil.copy2(ROOT / ".veldo" / "capsule.py", d / "capsule.py")
    _v106_shutil.copy2(ROOT / ".veldo" / "fix_validation.py", d / "fix_validation.py")
    src = (ROOT / ".veldo" / "fix_validation_record.py").read_text()
    for old, new in edits:
        assert src.count(old) == 1, (old[:70], src.count(old))
        src = src.replace(old, new)
    (d / "fix_validation_record.py").write_text(src)
    return _v106_load("v106_record_" + tag, d / "fix_validation_record.py")


def _v106_validator(tag, edits=()):
    """A copy of the VALIDATOR with the whole of .veldo beside it, because validate.py resolves its
    siblings from its own location and will not import without them."""
    d = _v106_tmp / ("val_" + tag)
    _v106_shutil.copytree(ROOT / ".veldo", d / ".veldo")
    src = (ROOT / ".veldo" / "validate.py").read_text()
    for old, new in edits:
        assert src.count(old) == 1, (old[:70], src.count(old))
        src = src.replace(old, new)
    (d / ".veldo" / "validate.py").write_text(src)
    return _v106_load("v106_validate_" + tag, d / ".veldo" / "validate.py")


READ_106 = '    parsed = read_policy(policy) if policy.is_file() else {}'
SHAPE_106 = '''    if not _FULL_COMMIT_ID.fullmatch(start):
        return {"recorded": start, "resolved": False, "excluded": False,
                "reason": (f"the recorded start line {start!r} is not a commit id; it must be forty "
                           "hexadecimal characters, not a branch, a tag or an abbreviation")}'''
FV106 = _v106_organ("main")
CAP106 = _v106_load("v106_capsule", ROOT / ".veldo" / "capsule.py")
VAL106 = _v106_load("v106_validate_main", ROOT / ".veldo" / "validate.py")

if not _v106_have_git:
    expect("VELDO-0106 STOOD DOWN by name - git is not installed here, so the policy and start-line rows "
           "cannot run over a real repository", True)
else:
    # ---- the repository the two settings are read against ---------------------------------------
    _v106_repo = _v106_tmp / "repo"
    (_v106_repo / ".veldo").mkdir(parents=True)
    (_v106_repo / "specs").mkdir()
    _v106_env = dict(_v106_os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                     GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")

    def _v106_git(*a):
        return _v106_sp.run(["git", "-C", str(_v106_repo), *a], check=True, capture_output=True,
                            text=True, env=_v106_env).stdout.strip()

    def _v106_commit(msg, **files):
        for rel, body in files.items():
            p = _v106_repo / rel.replace("__", "/")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body)
        _v106_git("add", "-A")
        _v106_git("commit", "-q", "-m", msg)
        return _v106_git("rev-parse", "HEAD")

    _v106_git("init", "-q")
    _v106_git("checkout", "-q", "-b", "trunk")
    _v106_OLD_R = _v106_commit("old review", **{"organ.py": "def guard(x):\n    return 'accepted'\n"})
    _v106_OLD_F = _v106_commit("old fix", **{"organ.py": "def guard(x):\n    return 'refused'\n"})
    _v106_LINE = _v106_commit("the start line lands here", **{"line.txt": "here\n"})
    _v106_REV = _v106_commit("new review", **{"organ.py": "def guard(x):\n    return 'accepted2'\n"})
    _v106_git("tag", "release-1")

    # A bundle carrying the REVIEWER's own evidence and NO validation record, committed after the
    # line: in scope, and refused whenever the flag is read as on. It is the thing whose treatment
    # makes the two settings observable at the call site.
    _v106_bdir = _v106_repo / "proof" / "VELDO-9106"
    _v106_cd = _v106_bdir / "capsules" / "F-1"
    _v106_cd.mkdir(parents=True)
    (_v106_cd / "repro.py").write_text("print('reproduction for F-1')\n")
    CAP106.write_manifest(_v106_cd, "F-1", _v106_REV, ["python3", CAP106.MOUNT + "/repro.py"],
                          {"kind": "stdout_contains", "value": "reproduction"}, "the reviewer's observation")
    _v106_FIX = _v106_commit("new fix, and the bundle lands", **{"organ.py": "def guard(x):\n    return 'refused2'\n"})
    _v106_manifest = {"schema": "veldo.proof/v1", "spec_id": "VELDO-9106", "commit": _v106_FIX}
    (_v106_bdir / "manifest.json").write_text(
        '{"schema": "veldo.proof/v1", "spec_id": "VELDO-9106", "commit": "' + _v106_FIX + '"}\n')
    _v106_mpath = _v106_bdir / "manifest.json"

    # ---- AC1: every shape the owner's file can take, read at the call site -----------------------
    _v106_ZERO = "0" + "1" * 39          # forty hex characters, and a general parser makes it 39
    _v106_SHAPES = {
        "block_plain": (
            "fix_validation:\n"
            "  required: true\n"
            "  from_commit: " + _v106_LINE + "\n", _v106_LINE),
        "block_trailing_comments": (
            "fix_validation:\n"
            "  required: true  # armed by the owner\n"
            "  from_commit: " + _v106_LINE + "  # where the rule begins\n", _v106_LINE),
        "inline_plain": (
            "fix_validation: {required: true, from_commit: " + _v106_LINE + "}\n", _v106_LINE),
        "inline_trailing_comment": (
            "fix_validation: {required: true, from_commit: " + _v106_LINE + "}  # armed\n", _v106_LINE),
        "quoted_and_a_hash_in_a_string": (
            "fix_validation:\n"
            "  required: \"true\"  # armed\n"
            "  from_commit: '" + _v106_LINE + "'  # the line\n"
            "  note: \"a # here is text, not a comment\"\n", _v106_LINE),
        "leading_zero_value": (
            "fix_validation:\n"
            "  required: true\n"
            "  from_commit: " + _v106_ZERO + "\n", _v106_ZERO),
    }

    def _v106_at_call_site(organ, text):
        """What the REAL call site prints and returns for this policy text, with the general parser
        handed in exactly as validate.py hands it in."""
        (_v106_repo / ".veldo" / "policy.yaml").write_text(text)
        buf = _v106_io.StringIO()
        with _v106_ctx.redirect_stdout(buf):
            errs = organ.check_proof_bundle(_v106_mpath, _v106_manifest, _v106_repo,
                                            VAL106.parse_yamlish, VAL106.front_matter, VAL106.fail)
        return buf.getvalue(), errs

    def _v106_by_general_parser(text):
        """The same two settings, as the handed-in general parser would have answered them."""
        try:
            parsed = VAL106.parse_yamlish(text)
        except Exception:  # noqa: BLE001 - a shape it cannot parse at all is still a disagreement
            return (None, None)
        return (FV106.flag_from_policy(parsed), FV106.start_line_from_policy(parsed))

    _v106_M_general = _v106_organ("generalparser", [
        (READ_106, '    parsed = parse_yamlish(policy.read_text()) if policy.is_file() else {}')])

    _v106_read_ok, _v106_general_disagrees, _v106_mutant_differs = [], [], []
    for _v106_name, (_v106_text, _v106_want) in _v106_SHAPES.items():
        _v106_out, _v106_errs = _v106_at_call_site(FV106, _v106_text)
        _v106_read_ok.append((
            _v106_name,
            "fix validation required," in _v106_out
            and ("from " + _v106_want[:12]) in _v106_out
            and _v106_errs >= 1))
        _v106_general_disagrees.append((_v106_name, _v106_by_general_parser(_v106_text) != (True, _v106_want)))
        _v106_mut_out, _v106_mut_errs = _v106_at_call_site(_v106_M_general, _v106_text)
        _v106_mutant_differs.append((_v106_name, (_v106_mut_out, _v106_mut_errs) != (_v106_out, _v106_errs)))

    # The hash inside quotes is text: read from the same real file, not from a hand-built mapping.
    (_v106_repo / ".veldo" / "policy.yaml").write_text(_v106_SHAPES["quoted_and_a_hash_in_a_string"][0])
    _v106_note = FV106.read_policy(_v106_repo / ".veldo" / "policy.yaml").get("fix_validation", {}).get("note", "")

    expect("VELDO-0106 AC1 policyread/a-comment-does-not-disarm-the-rule: in all six shapes the owner's file "
           "can take - block and inline, with and without a trailing comment, with quoted values and a hash "
           "inside a string, and with a leading-zero value a general parser would coerce - the call site reads "
           "the flag as REQUIRED and the start line exactly as written, and refuses the bundle. The general "
           "parser's answer is computed beside it on the same text and disagrees on four of the six, which is "
           "the silent return to advisory this item exists to stop; DRIVEN: a copy whose call site reads the "
           "policy with that general parser answers differently on those same shapes",
           all(ok for _, ok in _v106_read_ok)
           and sum(1 for _, d in _v106_general_disagrees if d) >= 4
           and sum(1 for _, d in _v106_mutant_differs if d) >= 4
           and "#" in _v106_note)

    # ---- AC2: a start line is a commit id, by shape, before anything is resolved ------------------
    _v106_M_noshape = _v106_organ("noshape", [(SHAPE_106, "    pass")])
    _v106_VALUES = {
        "full_id": _v106_LINE,
        "abbreviated": _v106_LINE[:12],
        "branch": "trunk",
        "tag": "release-1",
        "leading_zero_numeric": "0123456789",
        "empty": "",
    }
    _v106_scope = {k: FV106.start_line_scope(_v106_repo, v, _v106_FIX) for k, v in _v106_VALUES.items()}
    _v106_scope_mut = {k: _v106_M_noshape.start_line_scope(_v106_repo, v, _v106_FIX)
                       for k, v in _v106_VALUES.items()}
    # Completeness: the branch and the tag GENUINELY resolve in this repository, so the row fails if
    # resolvability is what is being tested rather than shape.
    _v106_really_resolve = (FV106._commit_exists(_v106_repo, "trunk")
                            and FV106._commit_exists(_v106_repo, "release-1"))
    _v106_refused = ["abbreviated", "branch", "tag", "leading_zero_numeric"]

    expect("VELDO-0106 AC2 policyread/a-branch-is-not-a-start-line: an abbreviated id, a branch name and a tag "
           "that both really resolve here, and a leading-zero numeric value are each REFUSED for their shape "
           "before anything is resolved, the reason names the value it was given, and every bundle stays in "
           "scope, because a mistyped line must not exempt anything; a full forty-character id resolves and an "
           "empty one is no line at all; DRIVEN: a copy without the shape gate accepts the branch and the tag, "
           "so the owner's line would follow a ref that moves without the owner",
           _v106_really_resolve
           and all(_v106_scope[k]["excluded"] is False and _v106_scope[k]["resolved"] is False
                   and "is not a commit id" in _v106_scope[k]["reason"]
                   and _v106_VALUES[k] in _v106_scope[k]["reason"] for k in _v106_refused)
           and _v106_scope["full_id"]["resolved"] is True
           and _v106_scope["empty"]["reason"] == "no start line recorded"
           and all("is not a commit id" not in _v106_scope_mut[k]["reason"] for k in ("branch", "tag")))

    # ---- the negative control: the copying is not what changes the behaviour ---------------------
    _v106_M_noop = _v106_organ("noop", [('import subprocess', '# additive no-op control\nimport subprocess')])
    _v106_control = [
        (_v106_at_call_site(_v106_M_noop, _v106_SHAPES["block_trailing_comments"][0]),
         _v106_at_call_site(FV106, _v106_SHAPES["block_trailing_comments"][0])),
        (_v106_M_noop.start_line_scope(_v106_repo, "trunk", _v106_FIX),
         _v106_scope["branch"]),
        (_v106_M_noop.start_line_scope(_v106_repo, _v106_LINE, _v106_FIX),
         _v106_scope["full_id"]),
    ]
    expect("VELDO-0106 control policyread/copying-is-not-what-changes-it: a copy of the organ carrying only an "
           "added comment answers exactly as the original does on the three cases the rows above turn on, so "
           "the difference each DRIVEN mutant shows is the mutation and not the copying",
           all(a == b for a, b in _v106_control))

# ---- AC3: the shared parser is left alone, and the measurement that says why is kept -------------
# Two documents the shared parser reads, parsed by the shipped parser and by a copy that strips
# trailing comments, over THIS repository's own corpus rather than a fixture built to fit the rule.
_v106_STRIP_HELPER = '''def _v106_strip(line):
    out, quote = [], None
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\\"'":
            quote = ch
            out.append(ch)
            continue
        if ch == "#":
            break
        out.append(ch)
    return "".join(out).rstrip()


def parse_yamlish(src):'''
_v106_APPEND = '        ls.append((len(raw) - len(raw.lstrip(" ")), raw.strip()))'
_v106_M_strip = _v106_validator("strip", [
    (_v106_APPEND, '        ls.append((len(raw) - len(raw.lstrip(" ")), _v106_strip(raw).strip()))'),
    ("def parse_yamlish(src):", _v106_STRIP_HELPER)])


def _v106_front_matter_text(text):
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    return text[4:end] if end > 0 else None


_v106_CORPUS = sorted(list(ROOT.glob("specs/*.md")) + list(ROOT.glob("plans/*.md")))


def _v106_measure(shipped, variant):
    """How many documents of the corpus parse differently under the two parsers, and which fields."""
    differ, fields = [], {}
    for p in _v106_CORPUS:
        text = _v106_front_matter_text(p.read_text())
        if text is None:
            continue
        try:
            a = shipped.parse_yamlish(text)
        except Exception:  # noqa: BLE001 - a document neither can parse is not a difference
            a = "unparsed"
        try:
            b = variant.parse_yamlish(text)
        except Exception:  # noqa: BLE001
            b = "unparsed"
        if a != b:
            differ.append(p.name)
            if isinstance(a, dict) and isinstance(b, dict):
                for k in set(a) | set(b):
                    if a.get(k) != b.get(k):
                        fields[k] = fields.get(k, 0) + 1
    return differ, fields


def _v106_ac3(shipped, variant):
    """The claim, as a function of WHICH parser is the shipped one, so it can be driven."""
    keeps = shipped.parse_yamlish("key: a value  # a trailing note\n").get("key") == "a value  # a trailing note"
    differ, fields = _v106_measure(shipped, variant)
    top = max(fields, key=fields.get) if fields else None
    return keeps and len(differ) > 0 and top == "acceptance_criteria", differ, fields


_v106_ok, _v106_differ, _v106_fields = _v106_ac3(VAL106, _v106_M_strip)
_v106_ok_mut, _, _ = _v106_ac3(_v106_M_strip, _v106_M_strip)
print(f"  VELDO-0106 AC3: {len(_v106_differ)} of {len(_v106_CORPUS)} documents parse differently if the "
      f"shared parser strips trailing comments; fields: "
      f"{', '.join(f'{k} x{v}' for k, v in sorted(_v106_fields.items(), key=lambda kv: -kv[1])[:6])}")

expect("VELDO-0106 AC3 policyread/the-shared-parser-is-left-alone: the shipped shared parser still keeps a "
       "trailing comment in a scalar, and over this repository's own corpus of specifications and plans a copy "
       "that strips them parses a non-empty set of documents differently, concentrated in acceptance-criteria "
       "text; that is the measured reason the obvious repair was not made, and the count and the fields are "
       "printed above rather than pinned, because the corpus grows; DRIVEN: with the stripping copy AS the "
       "shipped parser the claim is false, so the row is not true by construction",
       _v106_ok and not _v106_ok_mut)
