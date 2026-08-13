"""VELDO-0011: the release contract and its registry.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, which always
runs, so its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 18_veldo_0011_release_contract

WHAT IS UNDER TEST AND WHERE IT LIVES. .veldo/release_contract.py: the veldo.release/v1 record checks
(record_problems), the corpus enumeration (release_problems), the reading (release_report), the
two refusing entry points (check_release, check_plan_ids), the ONE duplicate rule
(duplicate_ids over id_paths) and the content binding (member_digest). It is driven DIRECTLY,
with validate.py's ONE front-matter parser and ONE failure reporter handed in exactly as
validate.py hands them to .veldo/request.py, so these assertions exercise the object the gate
will run rather than a second copy with test wiring. IT IS NOT DRIVEN THROUGH validate.py,
because the registration line lives in validate.py and that file is outside this lane; the call
shapes the registration needs are pinned below so the line cannot be wrong when it lands, and NO
row here pretends the wiring exists.

NAMES. The module handle is `_RCM`, not `RL`: fragment 04 already binds `RL` to the run log, and
these fragments share ONE namespace, so rebinding it would change what a later fragment sees.

EVERY BLOCK CAPTURES ITS OWN EXCEPTIONS. A raise at fragment scope takes every assertion below
it with it, which is how a mutation that deletes coverage passes as a shorter run. Each criterion
runs inside _rc_block, which reds a NAMED assertion if the block raises, so a mutation can only
ever turn rows red.

BOTH DIRECTIONS, EVERYWHERE. The product of this item is a REFUSAL, and a refusal asserted alone
is indistinguishable from a validator that refuses every release. So every refusing row is paired
with an ACCEPTING row over a fixture that differs in exactly one field or one member, the
required-field table is bound to its own LENGTH so emptying it reds, and every live read BRANCHES
on what it measured rather than asserting that this repository stays as it is today.
"""
import ast as _rc_ast
import contextlib as _rc_ctx
import hashlib as _rc_hashlib
import io as _rc_io
import re as _rc_re

_rc_spec = importlib.util.spec_from_file_location("veldo_releases",
                                                 ROOT / ".veldo" / "release_contract.py")
_RCM = importlib.util.module_from_spec(_rc_spec)
_rc_spec.loader.exec_module(_RCM)

# The plan module, for AC4's negative control: the whole of that criterion is the DIFFERENCE
# between this item's digest and the shipped plan_hash, so both hashers must be reachable here.
_rc_pspec = importlib.util.spec_from_file_location("veldo_plan_rc", ROOT / ".veldo" / "plan.py")
_RCP = importlib.util.module_from_spec(_rc_pspec)
_rc_pspec.loader.exec_module(_RCP)

_RC_SRC = (ROOT / ".veldo" / "release_contract.py").read_text()

# The standard-library names this module is allowed to reach for. A SUBSET rule rather than an
# equality, so adding a stdlib import is not a gate event, while ANY module of this repository or
# any third-party package (a YAML library above all) is - that is what dependency free means here,
# and it is what makes the parse callable the caller hands in the only path from text to values.
_RC_STDLIB_ONLY = {"hashlib", "re", "pathlib", "json", "os", "sys", "io", "collections",
                   "itertools", "functools", "datetime", "typing", "dataclasses", "textwrap"}


def _rc_block(label, fn):
    """Run one criterion's block, and red a NAMED row if it raises instead of losing the rest
    of the fragment. The label names the criterion, so a reader of the gate output knows which
    criterion lost its coverage rather than reading a shorter pass count."""
    try:
        fn()
    except Exception as _e:                      # noqa: BLE001 - a raise must RED a row, never skip rows
        expect("VELDO-0011 %s: the block ran to completion rather than raising (%r)" % (label, _e),
               False)


def _rc_release(rid, members=(("plan", "PLAN-9101"),), drop=(), **extra):
    """One release fixture whose ONLY defect can be the thing the row is about.

    Every field a release needs is present and valid unless the row drops or overrides it,
    because a fixture missing two things cannot tell which one a refusal came from. `drop`
    removes fields by name, `extra` overrides or adds them verbatim, and `members` is a list of
    (kind, target) pairs written as an author would type them."""
    lines = ["---", "schema: %s" % _RCM.SCHEMA, "id: %s" % rid, "title: a release fixture",
             "status: draft", "revision: 1", "owner: selftest", "milestone: v1"]
    # A DROPPED OR OVERRIDDEN FIELD LEAVES NO BASE LINE BEHIND: the one parser refuses a duplicate
    # key outright, so a fixture that kept both would test the parser rather than the row.
    lines = [ln for ln in lines
             if ln.split(":", 1)[0] not in drop and ln.split(":", 1)[0] not in extra]
    for k in sorted(extra):
        lines.append("%s: %s" % (k, extra[k]))
    if "members" not in drop and "members" not in extra:
        lines.append("members:")
        for kind, target in members:
            lines.append("  - kind: %s" % kind)
            lines.append("    target: %s" % target)
    return "\n".join(lines + ["---", "", "body", ""])


def _rc_plan(pid, kind="iteration"):
    """One valid veldo.plan/v1 fixture, so a member resolves against a real plan rather than a
    stub the plan validator would reject anyway. Written out rather than derived from
    plans/TEMPLATE.md, because that template carries trailing comments the one parser folds into
    the value, so `kind` read from it is not the word `mvp`."""
    return ("---\nschema: veldo.plan/v1\nid: %s\ntitle: a member plan\nkind: %s\nstatus: ready\n"
            "revision: 1\nowner: selftest\napproved_by: selftest\napproved_at: 2026-01-01\n"
            "outcomes:\n  - id: O1\n    becomes_true: a user gets the thing.\n"
            "    measure: journey green\n"
            "feature_tree:\n  - id: F1\n    title: the feature\n    outcome_refs: [O1]\n"
            "work:\n  - item: W1\n    spec: VELDO-9101\n    title: first\n"
            "    feature_refs: [F1]\n    depends_on: []\n    order: 10\n"
            "regression:\n  journeys:\n    - id: RJ1\n      title: the journey\n"
            "      activation: {when: start}\n      suite: e2e\n"
            "release:\n  milestone: v1\n  mode: continuous\n"
            "open_decisions:\n  - id: D1\n    text: an open question nothing waits on.\n"
            "    blocks: []\n---\nbody\n" % (pid, kind))


def _rc_tree(root, releases=(), plans=(("PLAN-9101", "iteration"),), template=False):
    """(releases dir, plans dir) laid out flat, the way both corpora really are. `releases` is a
    list of (filename, text); `plans` a list of (id, kind)."""
    rd, pd = Path(root) / "releases", Path(root) / "plans"
    pd.mkdir(parents=True, exist_ok=True)
    for pid, kind in plans:
        (pd / ("%s-fixture.md" % pid)).write_text(_rc_plan(pid, kind))
    if releases or template:
        rd.mkdir(parents=True, exist_ok=True)
    for name, text in releases:
        (rd / name).write_text(text)
    if template:
        (rd / "TEMPLATE.md").write_text((ROOT / "releases" / "TEMPLATE.md").read_text())
    return rd, pd


def _rc_reldir(root, name, text):
    """A releases directory holding exactly one release file, returned as the directory. Used
    where the PLANS half is the live corpus and only the release side is a fixture."""
    d = Path(root)
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text)
    return d


def _rc_check(rd, pd):
    """(errors, printed) for the release corpus check. The printed half matters as much as the
    count: the promise is that a refusal NAMES the file and the member, which is a promise about
    the line on the page, and a message right in the enumeration and lost on the way to the
    reporter would satisfy a count-only row."""
    buf = _rc_io.StringIO()
    with _rc_ctx.redirect_stdout(buf):
        errs = _RCM.check_release(rd, pd, V.parse_yamlish, V.fail)
    return errs, buf.getvalue()


def _rc_plan_ids(pd):
    """(errors, printed) for the plan-id duplicate check."""
    buf = _rc_io.StringIO()
    with _rc_ctx.redirect_stdout(buf):
        errs = _RCM.check_plan_ids(pd, V.parse_yamlish, V.fail)
    return errs, buf.getvalue()


def _rc_causes(rd, pd):
    """The multiset of named causes the ONE enumeration reports, as {cause: count}. Asserted as
    the module's own constants, never as message substrings, so a reworded refusal does not redden
    a row about the taxonomy."""
    out = {}
    for _subject, cause, _msg in _RCM.release_problems(rd, pd, V.parse_yamlish):
        out[cause] = out.get(cause, 0) + 1
    return out


# =======================================================================================
# AC1. ONE ARTIFACT, NO SECOND PARSER, AND EVERY REQUIRED FIELD REFUSED BY NAME.
#
# FALSIFIED BY (from the criterion itself): delete the required-field loop so only the schema
# string is verified, and the row that a release declaring NO MEMBERS is refused with members
# named must go red. POSITIVE CONTROL: the well-formed fixture is accepted with zero errors, so
# the refusal is discriminating rather than a blanket rejection of every release.
# =======================================================================================
# ONE BAD SHAPE AT A TIME, and the assertion below is bound to the LENGTH of this table, so a
# table somebody empties reds instead of passing over nothing. Each row is (label, drop, extra,
# expected cause, the word the refusal must NAME).
_RC_BAD = [
    ("no schema", ("schema",), {}, _RCM.CAUSE_MISSING_FIELD, "schema"),
    ("no id", ("id",), {}, _RCM.CAUSE_MISSING_FIELD, "id"),
    ("no title", ("title",), {}, _RCM.CAUSE_MISSING_FIELD, "title"),
    ("no status", ("status",), {}, _RCM.CAUSE_MISSING_FIELD, "status"),
    ("no revision", ("revision",), {}, _RCM.CAUSE_MISSING_FIELD, "revision"),
    ("no owner", ("owner",), {}, _RCM.CAUSE_MISSING_FIELD, "owner"),
    ("no milestone", ("milestone",), {}, _RCM.CAUSE_MISSING_FIELD, "milestone"),
    ("no members field at all", ("members",), {}, _RCM.CAUSE_MISSING_FIELD, "members"),
    ("an empty members list", ("members",), {"members": "[]"}, _RCM.CAUSE_MISSING_FIELD,
     "members"),
    ("a foreign schema", (), {"schema": "veldo.plan/v1"}, _RCM.CAUSE_BAD_SCHEMA, "schema"),
    ("an id that is not REL-nnnn", (), {"id": "RELEASE-1"}, _RCM.CAUSE_BAD_ID, "id"),
    ("a status outside the closed set", (), {"status": "donezo"}, _RCM.CAUSE_BAD_STATUS,
     "status"),
    ("a kind outside the closed set", (), {"kind": "yolo"}, _RCM.CAUSE_BAD_KIND, "kind"),
    ("revision zero", (), {"revision": "0"}, _RCM.CAUSE_BAD_REVISION, "revision"),
    ("revision that is not an integer", (), {"revision": "one"}, _RCM.CAUSE_BAD_REVISION,
     "revision"),
]


def _rc_ac1():
    with tempfile.TemporaryDirectory() as d:
        rd, pd = _rc_tree(d, releases=[("REL-9001-good.md", _rc_release("REL-9001"))])
        # POSITIVE CONTROL FIRST, on the fixture builder itself, so every refusal below is
        # attributable to the row's one defect and not to a fixture the validator would reject
        # anyway.
        _errs, _out = _rc_check(rd, pd)
        expect("VELDO-0011 AC1 POSITIVE CONTROL: the well-formed release fixture is accepted with "
               "zero errors and prints nothing, so the refusals below are discriminating rather "
               "than a blanket rejection of every release",
               _errs == 0 and _out == ""
               and _RCM.release_problems(rd, pd, V.parse_yamlish) == [])

        driven = 0
        for label, drop, extra, cause, named in _RC_BAD:
            rd2, pd2 = _rc_tree(Path(d) / label.replace(" ", "_"),
                                releases=[("REL-9002-bad.md",
                                           _rc_release("REL-9002", drop=drop, **extra))])
            errs, out = _rc_check(rd2, pd2)
            got = _rc_causes(rd2, pd2)
            expect("VELDO-0011 AC1: %s is refused with the named cause %s, the refusal names %r "
                   "and the file, and the refusal count equals the enumeration's problem count"
                   % (label, cause, named),
                   errs >= 1 and cause in got and named in out and "REL-9002-bad.md" in out
                   and errs == len(_RCM.release_problems(rd2, pd2, V.parse_yamlish)))
            driven += 1
        expect("VELDO-0011 AC1 ANTI-VACUITY: every row of the required-field table was driven, and "
               "the count is bound to the table's own LENGTH, so a table somebody empties reds "
               "instead of passing over nothing",
               driven == len(_RC_BAD) and len(_RC_BAD) >= 15)

        # THE MEMBERS ROW THE FALSIFICATION NAMES, on its own, because it is the one the declared
        # mutation must redden: no members field at all.
        rd3, pd3 = _rc_tree(Path(d) / "nomembers",
                            releases=[("REL-9003-empty.md",
                                       _rc_release("REL-9003", drop=("members",)))])
        errs3, out3 = _rc_check(rd3, pd3)
        expect("VELDO-0011 AC1: a release declaring NO MEMBERS is refused, with the field named "
               "on the page a reader sees",
               errs3 == 1 and "missing front-matter field: members" in out3)

        # THE PARSER THE CALLER HANDS IN. The fields arrive as the same values the plan and spec
        # validators see, and front
        # matter outside the subset is refused BY NAME rather than skipped.
        rd4, pd4 = _rc_tree(Path(d) / "tabs",
                            releases=[("REL-9004-tabs.md",
                                       _rc_release("REL-9004").replace("  - kind: plan",
                                                                       "\t- kind: plan"))])
        errs4, out4 = _rc_check(rd4, pd4)
        expect("VELDO-0011 AC1: front matter outside the ONE parser's subset is refused by name "
               "rather than skipped, through validate.parse_yamlish and no second reader",
               errs4 == 1 and _RCM.CAUSE_UNREADABLE in _rc_causes(rd4, pd4)
               and "outside the contract subset" in out4)
        # DERIVED FROM THE MODULE'S OWN SYNTAX TREE, not from substrings. The substring form
        # ("def parse_yamlish" absent, "import yaml" absent) is kept because it is what the
        # criterion names, but a parser under another name or another import spelling would walk
        # straight past it, so the import closure and the defined-function set are read structurally.
        # This module is dependency free BY CONSTRUCTION - it imports nothing of this repository and
        # no YAML library - which is what makes the parse callable its caller hands in the only path
        # from front-matter text to values. NOTE: validate.parse_yamlish is NOT the repository's only
        # front-matter reader (validate.front_matter is a cruder one with ten live call sites); the
        # claim asserted here is about THIS module shipping no second one.
        _rc_defs, _rc_imports, _rc_tokenising = set(), set(), set()
        for _node in _rc_ast.walk(_rc_ast.parse(_RC_SRC)):
            if isinstance(_node, _rc_ast.FunctionDef):
                _rc_defs.add(_node.name)
            elif isinstance(_node, _rc_ast.Import):
                _rc_imports.update(a.name.split(".")[0] for a in _node.names)
            elif isinstance(_node, _rc_ast.ImportFrom):
                _rc_imports.add((_node.module or "").split(".")[0])
            elif (isinstance(_node, _rc_ast.Call)
                  and isinstance(_node.func, _rc_ast.Attribute)
                  and _node.func.attr in ("splitlines", "partition", "rpartition", "split")):
                _rc_tokenising.add(_node.func.attr)
        expect("VELDO-0011 AC1: this module ships NO second front-matter parser, read from its "
               "SYNTAX TREE rather than from a substring - it defines no parse function, imports no "
               "YAML library and no module of this repository, and NOTHING in it tokenises text by "
               "line or by colon, which is the shape every hand-rolled front-matter reader has, so "
               "the parse callable its caller hands in is the only path from text to values",
               "def parse_yamlish" not in _RC_SRC and "import yaml" not in _RC_SRC
               and "parse(m.group(1))" in _RC_SRC
               and not [n for n in _rc_defs if "parse" in n or "yaml" in n]
               and _rc_tokenising == set()
               and _rc_imports <= _RC_STDLIB_ONLY
               and not (_rc_imports & {"yaml", "ruamel", "validate", "plan"})
               and _rc_imports and _rc_defs and "front_matter" in _rc_defs)

        # THE APPROVAL REFUSAL IN THE PLAN CONTRACT'S OWN WORDS, and that is measured against the
        # plan validator's real output rather than against a sentence copied by hand.
        rd5, pd5 = _rc_tree(Path(d) / "unapproved",
                            releases=[("REL-9005-ready.md",
                                       _rc_release("REL-9005", status="ready"))])
        errs5, out5 = _rc_check(rd5, pd5)
        buf = _rc_io.StringIO()
        with _rc_ctx.redirect_stdout(buf):
            V.check_plan(tmpfile(d, "PLAN-9199-unapproved.md",
                                 _rc_plan("PLAN-9199").replace("approved_by: selftest\n", "")
                                 .replace("approved_at: 2026-01-01\n", "")))
        plan_lines = [ln.split(": ", 1)[1] for ln in buf.getvalue().splitlines() if ": " in ln]
        want = [ln.replace("a plan leaves draft", "a release leaves draft")
                for ln in plan_lines if "leaves draft" in ln]
        expect("VELDO-0011 AC1: a status past draft with no approved_by and no approved_at is "
               "refused TWICE, in the same words the plan contract refuses it in, measured against "
               "the plan validator's own output rather than a hand-copied sentence",
               errs5 == 2 and len(want) == 2 and all(w in out5 for w in want)
               and _rc_causes(rd5, pd5) == {_RCM.CAUSE_UNAPPROVED: 2})
        expect("VELDO-0011 AC1 POSITIVE CONTROL: the same fixture with an approval recorded is "
               "accepted, so the row above is the approval rule and not the status word",
               _rc_check(*_rc_tree(Path(d) / "approved",
                                   releases=[("REL-9006-ready.md",
                                              _rc_release("REL-9006", status="ready",
                                                          approved_by="dmitry",
                                                          approved_at="2026-08-11"))]))
               == (0, ""))


_rc_block("AC1", _rc_ac1)

# =======================================================================================
# AC2. NO TWO ARTIFACTS SHARE AN ID, IN EITHER REGISTRY, THROUGH ONE SPELLING OF THE RULE.
#
# FALSIFIED BY (from the criterion itself): restore the bare assignment as the only write into
# the registry, dropping the duplicate accumulation, and the row that a tree holding two plan
# files declaring PLAN-9999 is refused with BOTH filenames named must go red. The declared
# mutation names .veldo/validate.py:669, which is outside this lane's footprint; the accumulation
# lives in _RCM.id_paths instead, and the equivalent single edit there (keep one path per id) is
# what this row is falsified by. NEGATIVE CONTROL: a corpus with no duplicate must report none.
# =======================================================================================


def _rc_ac2():
    with tempfile.TemporaryDirectory() as d:
        pd = Path(d) / "plans"
        pd.mkdir()
        (pd / "PLAN-9999-first.md").write_text(_rc_plan("PLAN-9999"))
        (pd / "PLAN-9999-second.md").write_text(_rc_plan("PLAN-9999"))
        (pd / "TEMPLATE.md").write_text(_rc_plan("PLAN-0000"))
        errs, out = _rc_plan_ids(pd)
        expect("VELDO-0011 AC2: two plan files declaring PLAN-9999 are refused, and the refusal "
               "names BOTH files, so 'one of them vanished' is actionable",
               errs == 1 and "PLAN-9999-first.md" in out and "PLAN-9999-second.md" in out
               and "duplicate plan id PLAN-9999" in out)
        expect("VELDO-0011 AC2: the accessor names the id with every file that declared it",
               _RCM.plan_duplicate_ids(pd, V.parse_yamlish)
               == [("PLAN-9999", ["PLAN-9999-first.md", "PLAN-9999-second.md"])])
        # THE SHIPPED DEFECT, DEMONSTRATED rather than described: the registry keeps ONE of the two.
        reg = V.plan_registry(pd)
        expect("VELDO-0011 AC2: the shipped registry silently keeps ONE of the two colliding files, "
               "which is the defect this refusal exists for, and it still does not raise",
               len(reg) == 1 and "PLAN-9999" in reg)
        expect("VELDO-0011 AC2: THE REGISTRY'S RETURN SHAPE AND CONTRACT DO NOT MOVE - its entries "
               "are still {path, fm} for the eight callers that read it",
               set(reg["PLAN-9999"]) == {"path", "fm"}
               and isinstance(reg["PLAN-9999"]["fm"], dict))
        # ONE RULE, not two agreeing copies. The rule is duplicate_ids over an id-to-paths mapping,
        # and the module contains exactly ONE implementation of the more-than-one test.
        expect("VELDO-0011 AC2: BOTH registries detect duplicates through ONE function taking the "
               "id-to-paths mapping, structurally - one definition of the rule, and both accessors "
               "reach it the same way, so a release-side copy cannot exist even while it agrees",
               _RC_SRC.count("def duplicate_ids(") == 1
               and _RC_SRC.count("return duplicate_ids(id_paths(artifact_files(") == 2
               and "duplicate_ids(id_paths(files, parse))" in _RC_SRC
               and _RCM.duplicate_ids({"X-1": [Path("a.md"), Path("b.md")], "X-2": [Path("c.md")]})
               == [("X-1", ["a.md", "b.md"])]
               and _RCM.duplicate_ids({}) == [])
        # NEGATIVE CONTROL: one file renamed to a distinct id, nothing else changed.
        (pd / "PLAN-9999-second.md").write_text(_rc_plan("PLAN-9998"))
        expect("VELDO-0011 AC2 NEGATIVE CONTROL: give the second file its own id and the SAME check "
               "reports nothing, so the refusal is the collision and not the pair of files",
               _rc_plan_ids(pd) == (0, "")
               and _RCM.plan_duplicate_ids(pd, V.parse_yamlish) == []
               and len(V.plan_registry(pd)) == 2)

        # THE RELEASE REGISTRY, same rule, same shape.
        rd, pd2 = _rc_tree(Path(d) / "rel",
                           releases=[("REL-9101-a.md", _rc_release("REL-9101")),
                                     ("REL-9101-b.md", _rc_release("REL-9101"))])
        errs2, out2 = _rc_check(rd, pd2)
        expect("VELDO-0011 AC2: two release files declaring REL-9101 are refused with both files "
               "named, under the same cause name",
               _RCM.CAUSE_DUPLICATE_RELEASE_ID in _rc_causes(rd, pd2)
               and "REL-9101-a.md" in out2 and "REL-9101-b.md" in out2 and errs2 >= 1)
        expect("VELDO-0011 AC2 NEGATIVE CONTROL: two releases with distinct ids and distinct "
               "members are accepted",
               _rc_check(*_rc_tree(Path(d) / "rel2",
                                   releases=[("REL-9102-a.md",
                                              _rc_release("REL-9102",
                                                          members=(("plan", "PLAN-9101"),))),
                                             ("REL-9103-b.md",
                                              _rc_release("REL-9103",
                                                          members=(("plan", "PLAN-9102"),)))],
                                   plans=(("PLAN-9101", "iteration"),
                                          ("PLAN-9102", "iteration")))) == (0, ""))

        # A MEMBER BINDING TO AN AMBIGUOUS PLAN ID is the release-side face of the same defect: the
        # member would bind to whichever file sorted last.
        rd3 = Path(d) / "amb" / "releases"
        pd3 = Path(d) / "amb" / "plans"
        pd3.mkdir(parents=True)
        rd3.mkdir(parents=True)
        (pd3 / "PLAN-9201-one.md").write_text(_rc_plan("PLAN-9201"))
        (pd3 / "PLAN-9201-two.md").write_text(_rc_plan("PLAN-9201"))
        (rd3 / "REL-9201-x.md").write_text(_rc_release("REL-9201",
                                                       members=(("plan", "PLAN-9201"),)))
        errs3, out3 = _rc_check(rd3, pd3)
        expect("VELDO-0011 AC2: a member targeting an ambiguous plan id is refused by the release "
               "check too, naming both plan files, because a release that groups a colliding id "
               "cannot say which file it grouped",
               _RCM.CAUSE_DUPLICATE_PLAN_ID in _rc_causes(rd3, pd3)
               and "PLAN-9201-one.md" in out3 and "PLAN-9201-two.md" in out3 and errs3 >= 1)


_rc_block("AC2", _rc_ac2)

# THE LIVE CORPUS, as a READING of it rather than a requirement on it. AC2's own words: over the
# live corpus assert only that the number of distinct ids read equals the number of plan files
# read, so a repository that grows a duplicate reds on the DUPLICATE. Measured as READ on
# 2026-08-11: 18 plan files, 18 distinct ids. The figures are NOT pinned here.


def _rc_ac2_live():
    files = _RCM.artifact_files(ROOT / "plans")
    mapping = _RCM.id_paths(files, V.parse_yamlish)
    reg = V.plan_registry(ROOT / "plans")
    expect("VELDO-0011 AC2 LIVE: the number of distinct plan ids read equals the number of plan "
           "files read, so this corpus carries no duplicate today and a future duplicate reds on "
           "the duplicate rather than on a pinned count",
           len(mapping) == len(files) and _RCM.plan_duplicate_ids(ROOT / "plans",
                                                                 V.parse_yamlish) == [])
    # NON-VACUITY IS "THE CORPUS IS NOT EMPTY", never a floor on its size: `len(files) > 10` was a
    # lower bound on a live population, so a repository that legitimately shrinks its plan corpus
    # would red a row that is about the ACCESSOR agreeing with the registry.
    expect("VELDO-0011 AC2 LIVE: and that is not vacuous - the corpus really has plan files, and "
           "the accessor's id set is EQUAL to the shipped registry's id set in both directions, so "
           "this is a second ACCESSOR over one corpus and not a second spelling of the corpus",
           len(files) >= 1 and len(mapping) >= 1 and set(mapping) == set(reg)
           and {p.name for paths in mapping.values() for p in paths}
           == {p.name for p in files})


_rc_block("AC2 LIVE", _rc_ac2_live)

# =======================================================================================
# AC3. THE FLOOR IS A TYPE, THE DEPTH IS NOT CAPPED, AND THE MEMBER GRAPH IS A FOREST.
#
# FALSIFIED BY (from the criterion itself): drop the member-kind whitelist so kind is accepted as
# any string, and the row that a member declaring kind spec with target VELDO-0011 is refused must
# go red. POSITIVE CONTROLS: every graph refusal is paired with a fixture differing in ONE member
# that must validate.
# =======================================================================================


def _rc_ac3():
    with tempfile.TemporaryDirectory() as d:
        # THE LOAD-BEARING LEG: an unknown kind is refused, which is what gives the walk a floor.
        rd, pd = _rc_tree(Path(d) / "kind",
                          releases=[("REL-9301-a.md",
                                     _rc_release("REL-9301", members=(("spec", "VELDO-0011"),)))])
        errs, out = _rc_check(rd, pd)
        expect("VELDO-0011 AC3: a member declaring kind spec with target VELDO-0011 is refused, "
               "with the member located and the allowed kinds named",
               errs == 1 and _rc_causes(rd, pd) == {_RCM.CAUSE_MEMBER_KIND: 1}
               and "member 1" in out and "'spec'" in out and "REL-9301-a.md" in out)
        # AND THE TYPE RULE UNDER A KNOWN KIND: a spec id is refused BY NAME as a spec id.
        rd2, pd2 = _rc_tree(Path(d) / "spectarget",
                            releases=[("REL-9302-a.md",
                                       _rc_release("REL-9302",
                                                   members=(("plan", "VELDO-0011"),)))])
        errs2, out2 = _rc_check(rd2, pd2)
        expect("VELDO-0011 AC3: a member of kind plan whose target is a SPEC id is refused by "
               "name, saying a spec binds to a plan and never to a release",
               errs2 == 1 and _rc_causes(rd2, pd2) == {_RCM.CAUSE_MEMBER_TARGET_TYPE: 1}
               and "is a spec id" in out2)
        # The type rule is symmetric: each kind takes its own id shape and no other, AND THE
        # REFUSAL NAMES THE TYPE THE TARGET ACTUALLY IS. Swapping kind and target between the two
        # levels is the likeliest mistake in this contract, and SPEC_ID_RE is a superset of both
        # member vocabularies, so a refusal that asks it first tells the author PLAN-9101 "is a
        # spec id" and then explains a rule about specs that does not apply to their file.
        for label, kind, target, names in (
                ("a plan member pointing at a release", "plan", "REL-9309", "release"),
                ("a release member pointing at a plan", "release", "PLAN-9101", "plan")):
            rd3, pd3 = _rc_tree(Path(d) / label.replace(" ", "_"),
                                releases=[("REL-9303-a.md",
                                           _rc_release("REL-9303", members=((kind, target),)))])
            errs3b, out3b = _rc_check(rd3, pd3)
            expect("VELDO-0011 AC3: %s is refused, so the id shape is typed by the member's kind "
                   "in both directions, and the refusal names %s the target ACTUALLY is rather "
                   "than calling it a spec id and explaining a rule about specs"
                   % (label, "the " + names + " id"),
                   _rc_causes(rd3, pd3) == {_RCM.CAUSE_MEMBER_TARGET_TYPE: 1}
                   and errs3b == 1
                   and ("which is a %s id" % names) in out3b
                   and "is a spec id" not in out3b and target in out3b)
        expect("VELDO-0011 AC3: the kind vocabulary and the id shape it implies are ONE table, so "
               "a kind cannot exist without a typed id shape and the two cannot disagree",
               _RCM.MEMBER_KINDS == set(_RCM.MEMBER_ID_RE) == {"plan", "release"}
               and "MEMBER_KINDS = set(MEMBER_ID_RE)" in _RC_SRC)
        expect("VELDO-0011 AC3 POSITIVE CONTROL: the same fixture with kind plan and a PLAN id is "
               "accepted, so the rows above are the type rule and not the member block",
               _rc_check(*_rc_tree(Path(d) / "typeok",
                                   releases=[("REL-9304-a.md",
                                              _rc_release("REL-9304",
                                                          members=(("plan", "PLAN-9101"),)))]))
               == (0, ""))

        # NO CAP ON THE DEPTH. A three-level chain validates, and so does a five-level one, so the
        # row proves the ABSENCE of a cap rather than asserting a maximum.
        for depth in (3, 5):
            chain = []
            for i in range(1, depth + 1):
                target = ("release", "REL-94%02d" % (i + 1)) if i < depth else ("plan",
                                                                               "PLAN-9101")
                chain.append(("REL-94%02d-lvl.md" % i,
                              _rc_release("REL-94%02d" % i, members=(target,))))
            rd4, pd4 = _rc_tree(Path(d) / ("chain%d" % depth), releases=chain)
            rep = _RCM.release_report(rd4, pd4, V.parse_yamlish)
            expect("VELDO-0011 AC3: a chain %d levels deep, ending at a plan, validates with zero "
                   "errors, and every member resolves, so nothing caps the depth" % depth,
                   _rc_check(rd4, pd4) == (0, "") and rep["releases"] == depth
                   and rep["members"] == depth and rep["members_resolved"] == depth)
        expect("VELDO-0011 AC3: and no constant caps it - the module declares no depth maximum, "
               "which is what makes the rows above a reading of the absence of a cap",
               not _rc_re.search(r"(?i)max_?depth|depth_?limit|MAX_MEMBERS", _RC_SRC))

        # A MEMBER RING IS REFUSED WITH THE RING NAMED IN ORDER.
        rd5, pd5 = _rc_tree(Path(d) / "cycle",
                            releases=[("REL-9501-a.md",
                                       _rc_release("REL-9501",
                                                   members=(("release", "REL-9502"),))),
                                      ("REL-9502-b.md",
                                       _rc_release("REL-9502",
                                                   members=(("release", "REL-9501"),)))])
        errs5, out5 = _rc_check(rd5, pd5)
        expect("VELDO-0011 AC3: a member cycle is refused with the ring named IN ORDER",
               _RCM.CAUSE_MEMBER_CYCLE in _rc_causes(rd5, pd5)
               and "REL-9501 -> REL-9502 -> REL-9501" in out5)
        expect("VELDO-0011 AC3: a release that lists ITSELF is the same refusal, named as a ring "
               "of one",
               "REL-9503 -> REL-9503"
               in _rc_check(*_rc_tree(Path(d) / "selfcycle",
                                      releases=[("REL-9503-a.md",
                                                 _rc_release("REL-9503",
                                                             members=(("release", "REL-9503"),)))]
                                      ))[1])
        expect("VELDO-0011 AC3 POSITIVE CONTROL: the SAME two releases with one member changed - "
               "the second points at the plan instead of back - validate with zero errors, so the "
               "cycle rule is not refusing every nested release",
               _rc_check(*_rc_tree(Path(d) / "nocycle",
                                   releases=[("REL-9504-a.md",
                                              _rc_release("REL-9504",
                                                          members=(("release", "REL-9505"),))),
                                             ("REL-9505-b.md",
                                              _rc_release("REL-9505",
                                                          members=(("plan", "PLAN-9101"),)))]))
               == (0, ""))

        # SINGLE PARENTAGE IS A REFUSAL, NOT A CONVENTION.
        rd6, pd6 = _rc_tree(Path(d) / "twoparents",
                            releases=[("REL-9601-a.md",
                                       _rc_release("REL-9601", members=(("plan", "PLAN-9101"),))),
                                      ("REL-9602-b.md",
                                       _rc_release("REL-9602", members=(("plan", "PLAN-9101"),)))])
        errs6, out6 = _rc_check(rd6, pd6)
        expect("VELDO-0011 AC3: a plan claimed as a member by two releases is refused with BOTH "
               "releases named - two DISTINCT releases, and the count it prints is the number of "
               "them - so the member set is a forest by refusal",
               _RCM.CAUSE_MEMBER_CLAIMED_TWICE in _rc_causes(rd6, pd6)
               and "REL-9601" in out6 and "REL-9602" in out6 and "PLAN-9101" in out6
               and "by 2 releases: REL-9601, REL-9602" in out6
               and _RCM.member_claims(_RCM.release_registry(rd6, V.parse_yamlish))
               == {"PLAN-9101": ["REL-9601", "REL-9602"]})
        expect("VELDO-0011 AC3 POSITIVE CONTROL: the SAME two releases with the second claiming a "
               "different plan validate with zero errors",
               _rc_check(*_rc_tree(Path(d) / "oneparent",
                                   releases=[("REL-9603-a.md",
                                              _rc_release("REL-9603",
                                                          members=(("plan", "PLAN-9101"),))),
                                             ("REL-9604-b.md",
                                              _rc_release("REL-9604",
                                                          members=(("plan", "PLAN-9102"),)))],
                                   plans=(("PLAN-9101", "iteration"),
                                          ("PLAN-9102", "iteration")))) == (0, ""))
        # And a member declared twice inside ONE release is refused too, which is the same
        # ambiguity one level down. ONE AUTHORING MISTAKE IS ONE REFUSAL: the causes are asserted
        # as an EXACT multiset, because the repeat used to draw a SECOND refusal saying the member
        # "is claimed as a member by 2 releases: REL-9701, REL-9701" - one release named twice, a
        # count that is wrong, and a claim about parentage that is false. A row that asserted its
        # cause with `in` could not see that extra false problem.
        rd7, pd7 = _rc_tree(Path(d) / "twice",
                            releases=[("REL-9701-a.md",
                                       _rc_release("REL-9701",
                                                   members=(("plan", "PLAN-9101"),
                                                            ("plan", "PLAN-9101"))))])
        errs7, out7 = _rc_check(rd7, pd7)
        expect("VELDO-0011 AC3: one release declaring the same member twice is refused EXACTLY "
               "ONCE, naming the position it repeats, and it is NOT also told the member has two "
               "parents: the claim is made by each release's DISTINCT targets, so one release "
               "cannot be its own second parent",
               _rc_causes(rd7, pd7) == {_RCM.CAUSE_MEMBER_DECLARED_TWICE: 1}
               and errs7 == 1 and "already declared as member 1" in out7
               and "claimed as a member" not in out7
               and _RCM.member_claims(_RCM.release_registry(rd7, V.parse_yamlish))
               == {"PLAN-9101": ["REL-9701"]})


_rc_block("AC3", _rc_ac3)

# =======================================================================================
# AC4. A MEMBER IS BOUND BY THE BYTES OF ITS FILE, AT FULL WIDTH, AND IT IS NOT plan_hash.
#
# FALSIFIED BY (from the criterion itself): return plan.plan_hash of the parsed front matter from
# member_digest instead of hashing the file bytes, and the row that a one-byte edit to a fixture
# plan's BODY changes the member digest while plan_hash over the same two files stays EQUAL must
# go red. That row IS the negative control: it asserts the DIFFERENCE between the two hashers
# rather than the mere presence of a hash.
# =======================================================================================


def _rc_ac4():
    with tempfile.TemporaryDirectory() as d:
        rd, pd = _rc_tree(Path(d) / "digest",
                          releases=[("REL-9801-a.md", _rc_release("REL-9801"))])
        member = pd / "PLAN-9101-fixture.md"
        before_bytes = member.read_bytes()
        before = _RCM.member_digest(member)
        rep_before = _RCM.release_report(rd, pd, V.parse_yamlish)
        expect("VELDO-0011 AC4: the digest is the sha256 of the FILE BYTES, at the full 64-hex "
               "width a digest that BINDS is written at in this repository",
               before == _rc_hashlib.sha256(before_bytes).hexdigest()
               and len(before) == 64 and _RCM.DIGEST_RE.fullmatch(before))
        # THE DIGEST IS REACHED, not an unused primitive: the registry records it on each resolved
        # member beside that member's id and path, so the derived view reads ONE value.
        rec = rep_before["member_records"][0]
        expect("VELDO-0011 AC4: the release registry records the digest on the resolved member "
               "beside its id and its path, so a later receipt reads one value rather than "
               "computing its own",
               rec["digest"] == before and rec["target"] == "PLAN-9101"
               and Path(rec["path"]) == member and rec["kind"] == "plan"
               and rep_before["digest_coverage"] == 1.0)

        # THE LEG THAT MATTERS. One byte BELOW the front matter, which plan_hash cannot see.
        fm_of = lambda text: V.parse_yamlish(_rc_re.match(r"^---\n(.*?)\n---", text,
                                                          _rc_re.S).group(1))
        text_before = member.read_text()
        # ONE BYTE, SUBSTITUTED BELOW THE FRONT MATTER: the last character of the body, so the
        # file is the same length and the front matter is byte-identical.
        text_after = text_before[:-2] + "X\n"
        member.write_text(text_after)
        after = _RCM.member_digest(member)
        expect("VELDO-0011 AC4 NEGATIVE CONTROL: a ONE-BYTE edit BELOW the front matter changes "
               "the member digest while plan_hash over the same two files stays EQUAL, which is "
               "the whole difference between a binding and a label",
               after != before and len(after) == 64
               and _RCP.plan_hash(fm_of(text_before)) == _RCP.plan_hash(fm_of(text_after))
               and text_before != text_after
               and len(text_after) == len(text_before)
               and text_before.split("---\n")[1] == text_after.split("---\n")[1])
        expect("VELDO-0011 AC4: and the report follows the bytes - the recorded digest changes "
               "with the body, so the value a receipt would bind on is the one that moved",
               _RCM.release_report(rd, pd, V.parse_yamlish)["member_records"][0]["digest"] == after)
        # WIDTH, in both directions: the binding keeps all 64, and plan_hash's 16 is a DIFFERENT
        # value, so a truncation to 16 could not satisfy the rows above.
        short = _RCP.plan_hash(fm_of(text_after))
        expect("VELDO-0011 AC4: plan_hash is a 16-hex prefixed label and the member digest is the "
               "full 64, so a truncation to plan_hash's width reds instead of passing",
               short.startswith("sha256:") and len(short.split(":", 1)[1]) == 16
               and after != short.split(":", 1)[1] and not after.startswith("sha256:")
               and before[:16] != short.split(":", 1)[1])
        expect("VELDO-0011 AC4: plan_hash itself is UNCHANGED - it still drops the volatile keys, "
               "which is the working binding a shipped assertion pins and this item must not widen",
               _RCP.plan_hash({"id": "PLAN-1", "approved_at": "2026-01-01"})
               == _RCP.plan_hash({"id": "PLAN-1", "approved_at": "2026-12-31"})
               and _RCP.plan_hash({"id": "PLAN-1"}) == _RCP.plan_hash({"id": "PLAN-1",
                                                                      "recorded_at": "x"}))
        # A FIGURE WITH NO BASIS IS NOT PRINTED. An unelaborated member carries None, never "".
        rd2, pd2 = _rc_tree(Path(d) / "unelaborated",
                            releases=[("REL-9802-a.md",
                                       _rc_release("REL-9802",
                                                   members=(("plan", "PLAN-9101"),
                                                            ("plan", "PLAN-9999"))))])
        rep2 = _RCM.release_report(rd2, pd2, V.parse_yamlish)
        digs = {m["target"]: m["digest"] for m in rep2["member_records"]}
        expect("VELDO-0011 AC4: a declared member whose target file is absent is counted as "
               "unelaborated and carries digest None rather than an empty string, and coverage is "
               "resolved over declared",
               digs["PLAN-9999"] is None and digs["PLAN-9101"] is not None
               and (rep2["members"], rep2["members_resolved"], rep2["members_unelaborated"])
               == (2, 1, 1) and rep2["digest_coverage"] == 0.5
               and _rc_check(rd2, pd2) == (0, ""))
        expect("VELDO-0011 AC4: an unreadable file digests to None rather than to the hash of "
               "nothing",
               _RCM.member_digest(Path(d) / "absent-entirely.md") is None)

    # WHAT AN ADOPTER INSTALLS IS WHAT THIS REPOSITORY RUNS.
    expect("VELDO-0011 AC4: the module and the copy /veldo:init lays down are byte-identical, so "
           "the contract an adopter installs is the contract this repository runs",
           (ROOT / ".veldo/release_contract.py").read_bytes()
           == (ROOT / "engine/.veldo/release_contract.py").read_bytes())
    expect("VELDO-0011 AC4: and so are the two copies of the release template",
           (ROOT / "releases/TEMPLATE.md").read_bytes()
           == (ROOT / "engine/releases/TEMPLATE.md").read_bytes())


_rc_block("AC4", _rc_ac4)

# =======================================================================================
# AC5. ADOPTION SAFE, AND THE WORD MVP DOES NOT REDDEN SEVENTEEN PLANS.
#
# FALSIFIED BY (from the criterion itself): make the member scan refuse a member plan declaring
# kind mvp instead of appending a notice, and the row that such a release validates with zero
# errors and exactly one notice must go red. ANTI-VACUITY ON BOTH HALVES: the notice row is paired
# with a sibling fixture whose member plan does NOT declare mvp, and the stand-down rows are
# paired with a POPULATED corpus that must NOT stand down.
# =======================================================================================


def _rc_ac5():
    with tempfile.TemporaryDirectory() as d:
        _rd, pd = _rc_tree(Path(d) / "base")
        no_dir = _RCM.release_report(Path(d) / "base" / "absent", pd, V.parse_yamlish)
        tpl_only_rd, tpl_pd = _rc_tree(Path(d) / "tplonly", template=True)
        tpl_only = _RCM.release_report(tpl_only_rd, tpl_pd, V.parse_yamlish)
        live_rd, live_pd = _rc_tree(Path(d) / "populated",
                                    releases=[("REL-9901-a.md", _rc_release("REL-9901"))])
        live = _RCM.release_report(live_rd, live_pd, V.parse_yamlish)
        expect("VELDO-0011 AC5: BOTH stand-down conditions produce the SAME report in the SAME key "
               "shape a live read carries, differing in exactly the one field that names WHICH "
               "condition it was",
               no_dir["stood_down"] is tpl_only["stood_down"] is True
               and {k: v for k, v in no_dir.items() if k != "stand_down"}
               == {k: v for k, v in tpl_only.items() if k != "stand_down"}
               and no_dir["stand_down"] != tpl_only["stand_down"]
               and no_dir["stand_down"] == _RCM.STAND_DOWN_NO_DIRECTORY
               and tpl_only["stand_down"] == _RCM.STAND_DOWN_EMPTY_REGISTRY
               and set(no_dir) == set(tpl_only) == set(live) == set(_RCM.REPORT_KEYS))
        expect("VELDO-0011 AC5: the stand-down is NOT keyed on the directory - the template CREATES "
               "the directory and the check still stands down, which is what a directory-keyed "
               "stand-down would have silently stopped doing",
               tpl_only_rd.is_dir() and (tpl_only_rd / "TEMPLATE.md").is_file()
               and _RCM.release_registry(tpl_only_rd, V.parse_yamlish) == {}
               and _RCM.artifact_files(tpl_only_rd) == []
               and "TEMPLATE" in _RC_SRC)
        # THE CORRECTION THIS SUITE FOUND BY DRIVING IT, and the row that keeps it fixed: a release
        # file declaring NO id leaves the REGISTRY empty while the corpus plainly holds a release.
        # Keyed on the registry, that file stood the whole check down and its own refusal was never
        # reached - a broken artifact passing as an unadopted repository.
        broken_rd, broken_pd = _rc_tree(Path(d) / "broken",
                                        releases=[("REL-9908-noid.md",
                                                   _rc_release("REL-9908", drop=("id",)))])
        broken_errs, broken_out = _rc_check(broken_rd, broken_pd)
        expect("VELDO-0011 AC5: a releases directory whose only file declares NO id does NOT stand "
               "down - it is refused, because an empty registry over a non-empty corpus is a broken "
               "artifact rather than an unadopted repository",
               _RCM.release_report(broken_rd, broken_pd,
                                   V.parse_yamlish)["stood_down"] is False
               and _RCM.release_registry(broken_rd, V.parse_yamlish) == {}
               and broken_errs == 1 and "missing front-matter field: id" in broken_out
               and "STANDS DOWN" not in broken_out)
        expect("VELDO-0011 AC5: the stand-down PRINTS one line naming which condition stood the "
               "check down, so it cannot be mistaken for a pass, and it refuses nothing",
               _rc_check(tpl_only_rd, tpl_pd)[0] == 0
               and _RCM.STAND_DOWN_EMPTY_REGISTRY in _rc_check(tpl_only_rd, tpl_pd)[1]
               and "STANDS DOWN" in _rc_check(tpl_only_rd, tpl_pd)[1])
        # NEGATIVE CONTROL FOR THE WHOLE STAND-DOWN: a populated corpus must NOT stand down, so
        # the stand-down cannot be what makes every case pass.
        expect("VELDO-0011 AC5 NEGATIVE CONTROL: a POPULATED release corpus does not stand down, "
               "and its figures are a real reading",
               live["stood_down"] is False and live["stand_down"] is None
               and live["releases"] == 1 and live["members"] == 1
               and live["members_by_kind"] == {"plan": 1}
               and _rc_check(live_rd, live_pd) == (0, ""))
        # AND THE STAND-DOWN DOES NOT SWALLOW THE PLAN-SIDE REFUSAL, which is why the two checks
        # are registered separately.
        dup = Path(d) / "dupplans" / "plans"
        dup.mkdir(parents=True)
        (dup / "PLAN-9997-a.md").write_text(_rc_plan("PLAN-9997"))
        (dup / "PLAN-9997-b.md").write_text(_rc_plan("PLAN-9997"))
        dup_rep = _RCM.release_report(Path(d) / "dupplans" / "releases", dup, V.parse_yamlish)
        expect("VELDO-0011 AC5: with NO releases directory at all the release check stands down "
               "while check_plan_ids still refuses a duplicate plan id, so the adoption-safe "
               "posture never hides the corpus defect",
               dup_rep["stood_down"] is True and _rc_plan_ids(dup)[0] == 1)
        # AND THE STOOD-DOWN REPORT DOES NOT PRINT A CONFIDENT ZERO ABOUT THE OTHER CORPUS. Every
        # other figure in that report is zero BY CONSTRUCTION (the release candidate file set is
        # empty). The plan half of duplicate_ids is a reading of a corpus this branch never looked
        # at, so it was the one figure that could be FALSE: it said the plan corpus carries no
        # duplicate id while two files declared PLAN-9997. It is now COMPUTED, and asserted EQUAL
        # to the accessor in both directions rather than pinned to a value.
        for _label, _rd in (("no releases directory at all", Path(d) / "dupplans" / "releases"),
                            ("a releases directory holding only the template",
                             _rc_tree(Path(d) / "duptpl", template=True, plans=())[0])):
            _rep = _RCM.release_report(_rd, dup, V.parse_yamlish)
            expect("VELDO-0011 AC5: standing down on %s still READS the plan corpus - the plan half "
                   "of duplicate_ids names the duplicate the other check refuses, and it equals the "
                   "accessor's own reading rather than a constant" % _label,
                   _rep["stood_down"] is True
                   and _rep["duplicate_ids"]["plan"] == _RCM.plan_duplicate_ids(dup,
                                                                               V.parse_yamlish)
                   and _rep["duplicate_ids"]["plan"]
                   == [("PLAN-9997", ["PLAN-9997-a.md", "PLAN-9997-b.md"])])
        # ADDITIVE CONTROL: the SAME stood-down branch over a plan corpus with no duplicate reports
        # an empty plan half, so the figure follows the corpus rather than always naming something.
        expect("VELDO-0011 AC5: and over a plan corpus that carries NO duplicate the same "
               "stood-down branch reports an empty plan half, so that figure is a reading in both "
               "directions and not a line that always fires",
               _RCM.release_report(Path(d) / "base" / "absent", pd,
                                   V.parse_yamlish)["duplicate_ids"]
               == {"release": [], "plan": _RCM.plan_duplicate_ids(pd, V.parse_yamlish)}
               and _RCM.plan_duplicate_ids(pd, V.parse_yamlish) == []
               and _RCM.artifact_files(pd) != [])

        # THE MVP DISPOSITION: reported once per release, naming the count and the files.
        mvp_rd, mvp_pd = _rc_tree(Path(d) / "mvpmember",
                                  releases=[("REL-9902-a.md", _rc_release("REL-9902"))],
                                  plans=(("PLAN-9101", "mvp"),))
        errs, out = _rc_check(mvp_rd, mvp_pd)
        notices = _RCM.release_notices(mvp_rd, mvp_pd, V.parse_yamlish)
        expect("VELDO-0011 AC5: a release whose member plan declares kind mvp validates with ZERO "
               "errors and exactly ONE notice, naming the count and the file it counted",
               errs == 0 and len(notices) == 1 and notices[0][1] == _RCM.MVP
               and "1 member plan(s)" in out and "PLAN-9101-fixture.md" in out
               and "not a refusal" in out)
        # ANTI-VACUITY: the sibling fixture, differing only in the member plan's kind, produces NO
        # notice, so an always-on line a reader would learn to ignore fails here.
        plain_rd, plain_pd = _rc_tree(Path(d) / "plainmember",
                                      releases=[("REL-9903-a.md", _rc_release("REL-9903"))],
                                      plans=(("PLAN-9101", "iteration"),))
        expect("VELDO-0011 AC5 ANTI-VACUITY: the SAME fixture whose member plan declares kind "
               "iteration produces NO notice and prints nothing, so the notice is the legacy kind "
               "and not a line that always prints",
               _RCM.release_notices(plain_rd, plain_pd, V.parse_yamlish) == []
               and _rc_check(plain_rd, plain_pd) == (0, ""))
        # WHAT IS REFUSED IS THE COLLISION THAT NEEDS NO RETROFIT.
        two_mvp = _rc_tree(Path(d) / "twomvp",
                           releases=[("REL-9904-a.md",
                                      _rc_release("REL-9904", kind="mvp",
                                                  members=(("plan", "PLAN-9101"),))),
                                     ("REL-9905-b.md",
                                      _rc_release("REL-9905", kind="mvp",
                                                  members=(("plan", "PLAN-9102"),)))],
                           plans=(("PLAN-9101", "iteration"), ("PLAN-9102", "iteration")))
        errs2, out2 = _rc_check(*two_mvp)
        expect("VELDO-0011 AC5: two releases both declaring kind mvp ARE refused, with both named, "
               "because at most one artifact may claim to be the MVP",
               _rc_causes(*two_mvp) == {_RCM.CAUSE_MVP_COLLISION: 1}
               and "REL-9904" in out2 and "REL-9905" in out2 and errs2 == 1)
        expect("VELDO-0011 AC5 POSITIVE CONTROL: one mvp release beside one ordinary release is "
               "accepted, so the refusal is the collision and not the word",
               _rc_check(*_rc_tree(Path(d) / "onemvp",
                                   releases=[("REL-9906-a.md",
                                              _rc_release("REL-9906", kind="mvp",
                                                          members=(("plan", "PLAN-9101"),))),
                                             ("REL-9907-b.md",
                                              _rc_release("REL-9907",
                                                          members=(("plan", "PLAN-9102"),)))],
                                   plans=(("PLAN-9101", "iteration"),
                                          ("PLAN-9102", "iteration")))) == (0, ""))


_rc_block("AC5", _rc_ac5)

# THE LIVE READ FOR AC5, BRANCHED ON WHAT IT MEASURED rather than pinning today's emptiness. The
# moment somebody declares this repository's first release, the branch below follows the corpus
# instead of reddening, which is PLAN-0018 finding 26 obeyed rather than quoted.


def _rc_ac5_live():
    rep = _RCM.release_report(ROOT / "releases", ROOT / "plans", V.parse_yamlish)
    expect("VELDO-0011 AC5 LIVE: the live report carries the full key shape whichever branch it "
           "is in, so a reader never has to ask which shape they were handed",
           set(rep) == set(_RCM.REPORT_KEYS))
    if rep["stood_down"]:
        expect("VELDO-0011 AC5 LIVE: this repository declares no release yet, so the check stands "
               "down NAMING which condition, refuses nothing, and every figure is absent rather "
               "than zero-with-no-basis",
               rep["stand_down"] in (_RCM.STAND_DOWN_NO_DIRECTORY, _RCM.STAND_DOWN_EMPTY_REGISTRY)
               and rep["digest_coverage"] is None
               and _rc_check(ROOT / "releases", ROOT / "plans")[0] == 0)
    else:
        expect("VELDO-0011 AC5 LIVE: this repository declares releases, so the reading is "
               "internally consistent - resolved plus unelaborated is every declared member, and "
               "coverage is one over the other",
               rep["members_resolved"] + rep["members_unelaborated"] == rep["members"]
               and sum(rep["members_by_kind"].values()) == rep["members"]
               and (rep["digest_coverage"] is None
                    or rep["digest_coverage"] == round(rep["members_resolved"]
                                                       / rep["members"], 3))
               and all(m["digest"] is None or len(m["digest"]) == 64
                       for m in rep["member_records"]))
    # THE MEASUREMENT THAT CHOSE REPORT-OVER-REFUSE, BRANCHED ON WHAT IS THERE RATHER THAN ON A
    # LOWER BOUND. The previous shape asserted that more than one live plan file declares the
    # legacy kind mvp, which is a floor on a live population THIS ITEM'S OWN NOTICE EXISTS TO DRIVE
    # TO ZERO: the notice tells authors the plan-level kind is legacy, and the row reddened the
    # moment fewer than two files still carried it. Migrating 16 of the 17 took the suite to
    # 103 passed 1 failed on this row alone. So the row now asserts the PROPERTY the pin stood in
    # for - the notice DISCRIMINATES over whatever this corpus holds - and it requires no count to
    # be any particular value, in either direction: legacy plans present, the notice names exactly
    # those files and no others; migration complete, the notice fires on nothing.
    live_kind = {}
    for _p in _RCM.artifact_files(ROOT / "plans"):
        _fm = _RCM.front_matter(_p, V.parse_yamlish)[0] or {}
        if isinstance(_fm.get("id"), str):
            live_kind[_fm["id"]] = (_fm.get("kind"), _p.name)
    legacy = sorted(pid for pid, (k, _n) in live_kind.items() if k == _RCM.MVP)
    current = sorted(pid for pid, (k, _n) in live_kind.items() if k != _RCM.MVP)
    with tempfile.TemporaryDirectory() as _d:
        # ONE release grouping EVERY plan this repository declares: legal (each target is claimed
        # once), and it drives the disposition over the real corpus instead of a fixture.
        _rd = Path(_d) / "livemembers"
        _rd.mkdir(parents=True)
        (_rd / "REL-9990-live.md").write_text(
            _rc_release("REL-9990", members=tuple(("plan", pid) for pid in sorted(live_kind))))
        _n = _RCM.release_notices(_rd, ROOT / "plans", V.parse_yamlish)
        _errs, _out = _rc_check(_rd, ROOT / "plans")
        if legacy:
            expect("VELDO-0011 AC5 LIVE: this corpus still carries the legacy kind mvp, so the "
                   "disposition REPORTS rather than refuses - a release grouping every live plan "
                   "validates with zero errors and draws exactly one notice, which names every "
                   "legacy plan file and no other plan file",
                   _errs == 0 and len(_n) == 1 and _n[0][1] == _RCM.MVP
                   and ("%d member plan(s)" % len(legacy)) in _n[0][2]
                   and all(live_kind[pid][1] in _n[0][2] for pid in legacy)
                   and all(live_kind[pid][1] not in _n[0][2] for pid in current)
                   and "not a refusal" in _out)
        else:
            expect("VELDO-0011 AC5 LIVE: the migration this notice exists to cause is COMPLETE - no "
                   "live plan declares the legacy kind mvp - so a release grouping every live plan "
                   "draws no notice at all, and the disposition still refuses nothing",
                   _errs == 0 and _n == [] and _out == "")
        if legacy and current:
            expect("VELDO-0011 AC5 LIVE: and the notice is the KIND and not the membership - a "
                   "release grouping only plans that do NOT declare the legacy kind draws no "
                   "notice, so this discriminates between live plans rather than firing on all",
                   _RCM.release_notices(
                       _rc_reldir(Path(_d) / "livecurrent", "REL-9991-live.md",
                                  _rc_release("REL-9991",
                                              members=tuple(("plan", pid) for pid in current))),
                       ROOT / "plans", V.parse_yamlish) == [])


_rc_block("AC5 LIVE", _rc_ac5_live)

# =======================================================================================
# THE TEMPLATE DRIVES THE VALIDATOR, and the registration this fragment cannot make.
# =======================================================================================


def _rc_template_and_wiring():
    tpl = (ROOT / "releases" / "TEMPLATE.md").read_text()
    with tempfile.TemporaryDirectory() as d:
        rd, pd = _rc_tree(Path(d) / "fromtpl")
        rd.mkdir(parents=True, exist_ok=True)
        (rd / "REL-0000-from-template.md").write_text(tpl)
        expect("VELDO-0011: a release written FROM the template validates with zero errors, so the "
               "fields the template asks for are the fields the validator enforces",
               _rc_check(rd, pd) == (0, ""))
        # STRUCTURAL, not a substring: the template's fields are real keys under the ONE parser,
        # and its members are real typed entries, so a mention in a comment could not satisfy this.
        fm = V.parse_yamlish(_rc_re.match(r"^---\n(.*?)\n---", tpl, _rc_re.S).group(1))
        expect("VELDO-0011: every required field is a real key in the template when it is read by "
               "the one parser, and each member declares a kind from the closed set",
               all(f in fm for f in _RCM.REQUIRED_FIELDS)
               and fm["schema"] == _RCM.SCHEMA and fm["status"] in _RCM.STATUSES
               and isinstance(fm["members"], list) and len(fm["members"]) >= 2
               and all(m.get("kind") in _RCM.MEMBER_KINDS for m in fm["members"]))
        expect("VELDO-0011: the template is EXCLUDED from the registry exactly as plan_registry "
               "excludes it, so shipping it declares no release",
               _RCM.release_registry(*_rc_tree(Path(d) / "tplreg", template=True)[:1],
                                     parse=V.parse_yamlish) == {})
    # THE REGISTRATION SHAPE. The two lines that wire this into the corpus sweep live in
    # .veldo/validate.py, which is outside this lane, so they are REPORTED rather than written -
    # and the exact call shape they use is pinned here, so the lines cannot be wrong when they
    # land. No row claims the wiring exists.
    expect("VELDO-0011: both entry points accept the (dir, dir, parse, fail) call shape the "
           "registration will use, with validate.py's own parser and reporter, and neither raises "
           "on an absent directory",
           _RCM.check_release(ROOT / "releases", ROOT / "plans", V.parse_yamlish, V.fail) == 0
           and _RCM.check_plan_ids(ROOT / "plans", V.parse_yamlish, V.fail) == 0
           and _RCM.check_release(ROOT / "no-such-dir", ROOT / "plans",
                                  V.parse_yamlish, V.fail) == 0
           and _RCM.check_plan_ids(ROOT / "no-such-dir", V.parse_yamlish, V.fail) == 0)
    expect("VELDO-0011: the reporting form and the refusing form read ONE problem enumeration, so "
           "the two surfaces cannot disagree about what is wrong",
           "report[\"problems\"]" in _RC_SRC
           and _RC_SRC.count("def release_problems(") == 1
           and _RC_SRC.count("release_problems(releases_dir, plans_dir, parse)") == 2)
    # DERIVED, never a pinned count: every CAUSE_ constant the module declares is registered in
    # CAUSES, and no two of them share a value, so a cause added later without being registered
    # reds here instead of being invisible.
    declared = {k: v for k, v in vars(_RCM).items() if k.startswith("CAUSE_")}
    expect("VELDO-0011: every cause the module declares is registered in CAUSES and no two causes "
           "share a name, derived from the module rather than from a count typed here",
           set(declared.values()) == _RCM.CAUSES
           and len(set(declared.values())) == len(declared) and len(declared) > 10
           and all(_RC_SRC.count(n) >= 3 for n in declared))


_rc_block("template and wiring", _rc_template_and_wiring)

del _rc_ast, _rc_ctx, _rc_hashlib, _rc_io, _rc_re, _rc_spec, _rc_pspec
