"""VELDO-0005: where the capability manifest and the tree disagree.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, which always
runs, so its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 22_veldo_0005_declared_vs_shipped

WHAT IS UNDER TEST. .veldo/declared.py, driven directly. It reads no front matter and takes no
parser, because the manifest's note fields carry commas, braces and colons in prose and the ONE
parser is deliberately not asked to survive that - so the fixtures below are real manifest files
written in the manifest's own line shape.

THE ROWS THAT MATTER MOST ARE THE ONES OVER THE REAL MANIFEST, and TWO OF THEM WERE A DEFECT.
This item exists because the naive resolver reported 42 unresolved homes of 167 on THIS repository
and every one was false, so a fixture-only suite would miss the entire point. But the first version
of those live rows required this repository's unresolved set to be EMPTY and required a design/
directory to be ABSENT, and this fragment runs inside verify.sh's required unit stage, so an
ordinary repository change reddened the whole gate on this organ's heuristic verdict - which is
exactly what PLAN-0018 NG3 and AC5 forbid. Independent review drove it: `mkdir design` reddened
the gate, and so did adding ONE CORRECT capability declaration whose home lives under a pack root
other than packs/claude.

SO THE LIVE ROWS ASSERT SOUNDNESS AND AGREEMENT, NEVER CONTENT. No live row requires a bucket to
be empty, a count to hold, or a path to be absent. What they assert is that no accusation the
organ makes is FALSE (verified by statting the tree here, not by trusting the resolver), that the
organ's undeclared set equals a derivation done in this file, and that the record shape holds. AC5
then drives those same claims over a report that HAS findings in every bucket, so a row that
started pinning emptiness again would redden there rather than in front of whoever next adds a
capability.

EVERY CRITERION'S BLOCK IS WRAPPED, so a raise reds a NAMED row instead of shortening the run.
"""
# ONE enumeration of the module under test: the path this fragment LOADS is the path its live rows
# name as their subject, so a rename cannot leave a row measuring a file that no longer exists.
_DC_MODULE = ".veldo/declared.py"
DC = V._VC._organ("declared", ROOT / _DC_MODULE)


def _dc_block(label, fn):
    try:
        fn()
    except Exception as _dc_e:                   # noqa: BLE001 - a raise must RED a row, never skip
        expect("VELDO-0005 %s: the block ran to completion rather than raising (%r)"
               % (label, _dc_e), False)


def _dc_manifest(rows):
    """A manifest in the real line shape: two spaces, a name, a colon, a brace block."""
    lines = ["# fixture manifest", "capabilities:"]
    for name, body in rows:
        lines.append("  %s: {%s}" % (name, body))
    return "\n".join(lines) + "\n"


def _dc_tree(d, rows, files=(), exemptions=None, packs=None):
    """A tree with a manifest, some real files, and optionally an exemption list and a REAL pack
    manifest - because the roots the resolver may search are derived from that file plus the tree,
    so a fixture that wants a pack root declares it the way this repository does."""
    base = Path(d)
    (base / ".veldo").mkdir(parents=True, exist_ok=True)
    (base / ".veldo" / "capabilities.yaml").write_text(_dc_manifest(rows))
    for rel in files:
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith("/"):
            p.mkdir(parents=True, exist_ok=True)
        else:
            p.write_text("# fixture\n")
    if exemptions is not None:
        (base / ".veldo" / "undeclared_exemptions.yaml").write_text(exemptions)
    if packs is not None:
        (base / ".veldo" / "packs.json").write_text(json.dumps(packs))
    return base


def _dc_report(rows, files=(), exemptions=None, packs=None):
    with tempfile.TemporaryDirectory() as d:
        base = _dc_tree(d, rows, files, exemptions, packs)
        rep = DC.declared_report(root=base)
        return rep, DC.report_lines(rep)


def _dc_roots_here(tree):
    """The roots a declared home may be relative to, derived HERE and independently of the module:
    the repository root, the canonical engine and pack directories the pack manifest declares, and
    every directory that exists under packs/. This exists so the live rows compare the module
    against a derivation rather than against the module's own constant - the previous rows asserted
    `f['roots_tried'] == list(DC.SEARCH_ROOTS)`, which a resolver that reported a root it never
    searched satisfied."""
    base = Path(tree)
    roots = ["."]

    def add(candidate):
        if isinstance(candidate, str):
            cleaned = candidate.strip().strip("/")
            if cleaned and cleaned != "." and cleaned not in roots:
                roots.append(cleaned)

    manifest = base / ".veldo" / "packs.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(errors="replace"))
        except ValueError:
            data = None
        if isinstance(data, dict):
            add(data.get("canonical_engine"))
            for pack in data.get("packs") or []:
                if isinstance(pack, dict):
                    add(pack.get("pack_dir"))
                    add(pack.get("wrapper_dir"))
    if (base / "engine").is_dir():
        add("engine")
    if (base / "packs").is_dir():
        for child in sorted((base / "packs").iterdir()):
            if child.is_dir():
                add("packs/" + child.name)
    return roots


def _dc_undeclared_here(tree):
    """The undeclared-module set, derived HERE. The compound split and the root search are done in
    this file, which is the axis AC3's falsification moves; the manifest PARSE and the exemption
    read are the module's, deliberately, because a second parser for a file whose note fields carry
    braces and colons in prose is not what this row is about."""
    base = Path(tree)
    roots = _dc_roots_here(base)
    declared = set()
    for _name, _status, home in DC.manifest_rows((base / DC.MANIFEST).read_text(errors="replace")):
        if not isinstance(home, str):
            continue
        for seg in [s.strip() for s in home.split("+") if s.strip()]:
            for r in roots:
                candidate = base / seg if r == "." else base / r / seg
                if candidate.exists():
                    declared.add(candidate.relative_to(base).as_posix())
                    break
    exempt = DC.read_exemptions(root=base)
    mods = sorted(DC.MODULE_DIR + "/" + p.name for p in (base / DC.MODULE_DIR).glob(DC.MODULE_GLOB))
    return [m for m in mods if m not in declared and m not in exempt]


def _dc_defects(tree, rep):
    """WHAT A REPORT OVER A REAL TREE MUST NEVER CONTAIN, measured by statting the tree HERE rather
    than by trusting the resolver. Every bucket is a DEFECT bucket, so none of them is a fact about
    how much this repository declares: a genuinely stale declaration adds a TRUE accusation and
    lands in none of these, which is why AC5 can drive this same function over a report that has
    findings in every bucket and require the same emptiness of the defects.

      false_accusations    an accused segment that EXISTS under some root the tree declares. This
                           is the defect the whole item exists to eliminate, and the naive resolver
                           produced 42 of them.
      compound_accusations an accusation against a compound STRING rather than against one path,
                           which is what dropping the split produces.
      incomplete_records   a finding missing part of the record AC2 requires.
      phantom_resolutions  a resolved segment that does not exist at the path recorded.
      two_buckets          a module reported in two buckets at once.
    """
    base, roots = Path(tree), _dc_roots_here(tree)
    out = {"false_accusations": [], "compound_accusations": [], "incomplete_records": [],
           "phantom_resolutions": [], "two_buckets": []}
    for f in rep["unresolved"]:
        tried, segs = f.get("roots_tried") or [], f.get("unresolved_segments") or []
        if (sorted(f) != sorted(DC.FINDING_KEYS_UNRESOLVED)
                or f.get("finding") != DC.FINDING_HOME_UNRESOLVED
                or not isinstance(f.get("home_as_declared"), str)
                or not segs or "." not in tried):
            out["incomplete_records"].append(f.get("capability"))
        for seg in segs:
            if DC.COMPOUND_SEP in seg:
                out["compound_accusations"].append((f.get("capability"), seg))
                continue
            where = [r for r in roots
                     if (base / seg if r == "." else base / r / seg).exists()]
            if where:
                out["false_accusations"].append((f.get("capability"), seg, where))
        for seg in f.get("resolved_segments") or []:
            if not (base / seg).exists():
                out["phantom_resolutions"].append((f.get("capability"), seg))
    out["two_buckets"] = sorted({f["module"] for f in rep["undeclared"]}
                                & {f["module"] for f in rep["exempted"]})
    return out


def _dc_clean(defects):
    return all(not v for v in defects.values())


# ---------------------------------------------------------------------------------------
# AC1. THE RESOLVER IS THE ITEM, AND THE NAIVE ONE IS WRONG A THIRD OF THE TIME.
#
# FALSIFIED BY: reduce the resolver to a single root and a single segment, and the row below
# must go red.
# ---------------------------------------------------------------------------------------


def _dc_ac1():
    rep, _ = _dc_report(
        [("compound", "status: mechanical, home: .veldo/a.py + .veldo/b.py"),
         ("under_pack", "status: procedure, home: skills/plan"),
         ("a_directory", "status: procedure, home: docs")],
        files=[".veldo/a.py", ".veldo/b.py", "packs/claude/skills/plan/SKILL.md", "docs/x.md"])
    expect("VELDO-0005 AC1: ALL THREE SHAPES THE NAIVE RESOLVER GOT WRONG now resolve - a COMPOUND "
           "home naming two paths, a home living under a PACK ROOT rather than the repository root, "
           "and a home that is a DIRECTORY rather than a file. Measured on this repository's real "
           "manifest, assuming one root and one file reported 42 unresolved of 167 and every one "
           "was false, which is a third of the corpus wrongly accused by the obvious implementation",
           rep["unresolved"] == [])

    rep_pack, _ = _dc_report(
        [("tool_native_driver", "status: mechanical, home: .cursor/hooks/veldo-guard-hook.sh")],
        files=["vendor/zed-pack/.cursor/hooks/veldo-guard-hook.sh"],
        packs={"canonical_engine": "engine",
               "packs": [{"id": "zed", "pack_dir": "vendor/zed-pack"}]})
    expect("VELDO-0005 AC1: A HOME UNDER ANY ROOT THE PACK MANIFEST DECLARES resolves, and the "
           "roots are READ FROM THAT MANIFEST rather than written here. This row is the one "
           "independent review earned: the resolver carried the literal tuple ('.', 'engine', "
           "'packs/claude') while .veldo/packs.json declares SEVEN pack roots, so one CORRECT "
           "declaration about a real .cursor hook under packs/cursor was reported HOME_UNRESOLVED - "
           "the same false accusation the item exists to eliminate, for six of the seven drivers. "
           "The fixture's root is vendor/zed-pack, which no tree discovery would find, so the row "
           "reds if the manifest stops being read",
           rep_pack["unresolved"] == []
           and "vendor/zed-pack" in rep_pack["roots_available"])

    rep2, lines2 = _dc_report(
        [("genuinely_gone", "status: mechanical, home: .veldo/nowhere.py")],
        files=[".veldo/a.py"])
    expect("VELDO-0005 AC1 NEGATIVE CONTROL: a home naming a path that exists nowhere IS reported "
           "unresolved. Without this row the one above is satisfied by a resolver that resolves "
           "everything, which is the failure mode in the opposite direction and the more dangerous "
           "one, because it reports a clean manifest forever",
           [f["capability"] for f in rep2["unresolved"]] == ["genuinely_gone"]
           and any("HOME_UNRESOLVED genuinely_gone" in ln for ln in lines2))

    rep3, _ = _dc_report(
        [("half_gone", "status: mechanical, home: .veldo/a.py + .veldo/nowhere.py")],
        files=[".veldo/a.py"])
    expect("VELDO-0005 AC1: a COMPOUND home with ONE resolving segment and one missing is reported, "
           "and the finding separates which segment resolved from which did not - a compound whose "
           "first half exists must not read as satisfied",
           len(rep3["unresolved"]) == 1
           and rep3["unresolved"][0]["unresolved_segments"] == [".veldo/nowhere.py"]
           and rep3["unresolved"][0]["resolved_segments"] == [".veldo/a.py"])

    _dc_live = DC.declared_report(root=ROOT)
    _dc_live_defects = _dc_defects(ROOT, _dc_live)
    expect("VELDO-0005 AC1 OVER THE REAL MANIFEST, which is the row this item was written for: NO "
           "ACCUSATION THIS ORGAN MAKES ABOUT THIS REPOSITORY IS FALSE. Every accused segment is "
           "stat'ed HERE under every root the tree declares, and an accused path found anywhere is "
           "the defect - the naive resolver produced 42 of those out of 167. REPORTED, NEVER "
           "PINNED, and this is the correction independent review forced: %d capability(ies), %d "
           "shipped module(s), %d unresolved home(s) today, and this row requires NONE of those "
           "numbers to be anything. The row it replaced required the unresolved set to be EMPTY, so "
           "one correct declaration about a non-Claude pack root reddened the whole gate"
           % (_dc_live["capabilities"], _dc_live["modules"], len(_dc_live["unresolved"])),
           _dc_clean(_dc_live_defects)
           and _dc_live["capabilities"] > 0 and _dc_live["modules"] > 0)


_dc_block("AC1", _dc_ac1)


# ---------------------------------------------------------------------------------------
# AC2. AN UNRESOLVED HOME CARRIES WHAT THE RESOLVER TRIED.
#
# FALSIFIED BY: drop the attempted-paths record, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _dc_ac2():
    with tempfile.TemporaryDirectory() as d:
        base = _dc_tree(d, [("stale", "status: mechanical, home: .veldo/moved_away.py")],
                        files=[".veldo/a.py", "vendor/zed-pack/keep"],
                        packs={"canonical_engine": "engine",
                               "packs": [{"id": "zed", "pack_dir": "vendor/zed-pack"}]})
        rep = DC.declared_report(root=base)
        lines = DC.report_lines(rep)
        f = rep["unresolved"][0]
        expect("VELDO-0005 AC2: an unresolved finding carries the home AS DECLARED, WHICH segment "
               "failed, and EVERY ROOT that was searched. The obvious implementation of this check "
               "was wrong 42 times out of 167, so a finding reporting only its conclusion would "
               "have laundered every one of those into a fact about the file documentation defers "
               "to. The roots are checked against a derivation done in this file, NOT against the "
               "module's own constant: the previous row asserted equality with DC.SEARCH_ROOTS, "
               "which a resolver that reported a root it never stat'ed satisfied",
               f["home_as_declared"] == ".veldo/moved_away.py"
               and f["unresolved_segments"] == [".veldo/moved_away.py"]
               and f["roots_tried"] == _dc_roots_here(base)
               and "vendor/zed-pack" in f["roots_tried"]
               and f["capability"] == "stale" and f["finding"] == DC.FINDING_HOME_UNRESOLVED)
        expect("VELDO-0005 AC2: the PRINTED line carries the roots too, so the person deciding "
               "whether to edit the manifest sees where the resolver looked without opening a JSON "
               "file, and the roots it names are the ones this tree declares rather than three "
               "written into the module",
               any("could not find" in ln and "vendor/zed-pack" in ln and "engine" in ln
                   for ln in lines))
        expect("VELDO-0005 AC2: the report names the roots AVAILABLE to the resolver even when "
               "nothing is unresolved, so a reader can tell a clean run from a run that searched "
               "the wrong places, and the human report prints them with where they came from",
               rep["roots_available"] == _dc_roots_here(base)
               and len(rep["roots_available"]) >= 2
               and any("roots available to the resolver" in ln for ln in lines))

        resolved, unresolved, tried = DC.resolve_home(".veldo/a.py", root=base)
        gone_resolved, gone_unresolved, gone_tried = DC.resolve_home(".veldo/gone.py", root=base)
        expect("VELDO-0005 AC2: WHAT IS RECORDED IS WHAT WAS SEARCHED. A segment found under the "
               "FIRST root records that root ALONE, and only a segment found nowhere records them "
               "all. The record used to be the root LIST copied unconditionally, so a resolver that "
               "skipped a root still printed 'could not find X under any of ...' naming it, which "
               "is a false statement about work never done",
               tried == ["."] and unresolved == [] and resolved == [".veldo/a.py"]
               and gone_tried == _dc_roots_here(base) and len(gone_tried) > 1
               and gone_unresolved == [".veldo/gone.py"] and gone_resolved == [])


_dc_block("AC2", _dc_ac2)


# ---------------------------------------------------------------------------------------
# AC3. A MODULE DECLARED INSIDE A COMPOUND HOME IS DECLARED.
#
# FALSIFIED BY: compare against the raw home STRINGS instead of the resolved segments, and the
# row below must go red.
# ---------------------------------------------------------------------------------------


def _dc_ac3():
    rep, lines = _dc_report(
        [("compound", "status: mechanical, home: .veldo/a.py + .veldo/b.py")],
        files=[".veldo/a.py", ".veldo/b.py", ".veldo/c.py"])
    expect("VELDO-0005 AC3: BOTH halves of a compound home count as DECLARED, and only the module "
           "named in no home at all is reported. Comparing against the home STRING would report "
           "both halves undeclared - the same false accusation as AC1's, seen in the mirror",
           [f["module"] for f in rep["undeclared"]] == [".veldo/c.py"]
           and any("UNDECLARED_MODULE .veldo/c.py" in ln for ln in lines))

    rep2, _ = _dc_report(
        [("all_of_them", "status: mechanical, home: .veldo/a.py + .veldo/b.py + .veldo/c.py")],
        files=[".veldo/a.py", ".veldo/b.py", ".veldo/c.py"])
    expect("VELDO-0005 AC3 NEGATIVE CONTROL: with every shipped module named somewhere, NOTHING is "
           "reported undeclared - so the finding above is a measurement rather than a scan that "
           "always finds something",
           rep2["undeclared"] == [] and rep2["modules"] == 3)

    _dc_live = DC.declared_report(root=ROOT)
    _dc_derived = _dc_undeclared_here(ROOT)
    _dc_reported = [f["module"] for f in _dc_live["undeclared"]]
    expect("VELDO-0005 AC3 OVER THE REAL TREE: the organ's undeclared set is EXACTLY the set an "
           "independent derivation reaches here - shipped modules minus the RESOLVED segments of "
           "every declared home minus recorded exemptions, with the compound split and the root "
           "search done in this file. %d shipped module(s) and %d undeclared, and this row requires "
           "neither number to be anything, because judging whether an internal helper deserves a "
           "capability is a human call. The row this replaced named six module paths and asserted "
           "they were absent from the undeclared list, which SURVIVED AC3's own falsification (six "
           "simple homes whose strings equal their module paths, so raw-string comparison still "
           "found them) and pinned today's filenames besides. The organ this fragment drives must "
           "still be declared: that was the fix this measurement forced"
           % (_dc_live["modules"], len(_dc_reported)),
           _dc_reported == _dc_derived and _dc_live["modules"] > 0
           and _DC_MODULE not in set(_dc_reported))


_dc_block("AC3", _dc_ac3)


# ---------------------------------------------------------------------------------------
# AC4. AN EXEMPTION CARRIES A REASON AND IS COUNTED SEPARATELY.
#
# FALSIFIED BY: fold exempted modules into the declared count, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _dc_ac4():
    rep, lines = _dc_report(
        [("one", "status: mechanical, home: .veldo/a.py")],
        files=[".veldo/a.py", ".veldo/helper.py"],
        exemptions='.veldo/helper.py: an internal helper with no user-facing capability\n')
    expect("VELDO-0005 AC4: an exempted module is counted in its OWN bucket WITH its reason and is "
           "never added to the declared count, so the report cannot be made clean by exempting "
           "everything - the number of exemptions is exactly as visible as the number of findings",
           [f["module"] for f in rep["exempted"]] == [".veldo/helper.py"]
           and rep["exempted"][0]["reason"].startswith("an internal helper")
           and rep["undeclared"] == []
           and any("exempted .veldo/helper.py" in ln for ln in lines))

    rep2, _ = _dc_report(
        [("one", "status: mechanical, home: .veldo/a.py")],
        files=[".veldo/a.py", ".veldo/helper.py"],
        exemptions='.veldo/helper.py:\n')
    expect("VELDO-0005 AC4: an exemption with NO REASON is not an exemption - the module is reported "
           "undeclared. An exemption list with no reasons is where undeclared modules go to be "
           "forgotten, which is the thing an exemption mechanism is most likely to become",
           [f["module"] for f in rep2["undeclared"]] == [".veldo/helper.py"]
           and rep2["exempted"] == [])

    rep3, _ = _dc_report(
        [("one", "status: mechanical, home: .veldo/a.py")],
        files=[".veldo/a.py", ".veldo/helper.py"])
    expect("VELDO-0005 AC4 NEGATIVE CONTROL: with NO exemption list at all the same module is "
           "reported undeclared, so the exemption is what changes the answer rather than the "
           "module being invisible for some other reason",
           [f["module"] for f in rep3["undeclared"]] == [".veldo/helper.py"])


_dc_block("AC4", _dc_ac4)


# ---------------------------------------------------------------------------------------
# AC5. EACH LEG STANDS DOWN SEPARATELY AND ITS FINDINGS GATE NOTHING.
#
# FALSIFIED BY: remove the per-leg stand-downs, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _dc_ac5():
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        rep = DC.declared_report(root=base)
        lines = DC.report_lines(rep)
        expect("VELDO-0005 AC5: an ABSENT MANIFEST stands the WHOLE report down by name, because "
               "both findings are defined against it - 'there is nothing to disagree with' is not "
               "the same fact as 'the manifest and the tree agree'",
               rep["stood_down"] is True and "NOT the same fact" in rep["reason"]
               and any("stood down" in ln for ln in lines))

    # THE MODULES LEG STANDS DOWN ONLY WHEN THE MANIFEST IS ELSEWHERE, and that is worth saying:
    # the default manifest lives INSIDE the directory the modules leg scans, so with the default
    # path this branch is unreachable and asserting it there would be asserting nothing. It becomes
    # reachable through the manifest parameter, which is how an adopter with a manifest outside
    # .veldo/ reaches it, so the row drives it that way instead of pretending the default does.
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        (base / "elsewhere").mkdir(parents=True)
        mpath = base / "elsewhere" / "capabilities.yaml"
        mpath.write_text(_dc_manifest([("gone", "status: mechanical, home: nowhere.py")]))
        rep2 = DC.declared_report(root=base, manifest=mpath)
        expect("VELDO-0005 AC5: with the manifest present but NO module directory, the report "
               "ANSWERS and the unresolved leg reports its finding while ONLY the modules leg "
               "stands down, with its own reason. Two different absences, reported separately, "
               "because they send a reader to different places",
               rep2["stood_down"] is False
               and [f["capability"] for f in rep2["unresolved"]] == ["gone"]
               and rep2["modules_leg_stood_down"] is True
               and rep2["modules_leg_reason"] == DC.STAND_DOWN_NO_MODULES
               and rep2["undeclared"] == [] and rep2["modules"] == 0)

    rep3, _ = _dc_report([("one", "status: mechanical, home: .veldo/a.py")],
                         files=[".veldo/a.py"])
    expect("VELDO-0005 AC5: the report carries ONE KEY SHAPE whether a leg stood down or not, so a "
           "consumer never guesses whether a key is missing or genuinely empty",
           sorted(rep3) == sorted(DC.REPORT_KEYS)
           and sorted(DC.declared_report(root=Path(tempfile.gettempdir()) / "no-such-tree-here"))
           == sorted(DC.REPORT_KEYS))

    # A DESIGN-WITH-NO-DESCENDANTS LEG IS NOT BUILT. The row that said so used to assert
    # `not (ROOT / "design").is_dir()`, which is a pin on live repository state: `mkdir design`
    # reddened the required unit stage, and the sentence it certified was false anyway, because
    # docs/design/ holds 19 design documents. What is asserted instead is a property of the CODE
    # that cannot be true of a half-built leg: the finding kinds the module DECLARES are exactly
    # the kinds a driven report EMITS, so naming a third kind without building its leg reds here.
    _dc_both, _ = _dc_report([("gone", "status: mechanical, home: .veldo/nowhere.py")],
                             files=[".veldo/an_undeclared_module.py"])
    _dc_emitted = {f["finding"] for f in _dc_both["unresolved"] + _dc_both["undeclared"]}
    expect("VELDO-0005 AC5: A DESIGN-WITH-NO-DESCENDANTS LEG IS NOT BUILT, and this row says so as "
           "a property of the code rather than as a claim about the tree: the finding kinds the "
           "module DECLARES are exactly the kinds a driven report EMITS, so a third kind named "
           "without a leg to emit it reds this row and a leg emitting an undeclared kind reds it "
           "too. The reason recorded before was FALSE - docs/design/ holds 19 design documents and "
           "PLAN-0018 observation 18, the observation that produced this work item, names "
           "docs/design/05-product-planning-layer-sol.md as a design that died with nothing "
           "noticing - and the assertion certifying it pinned the ABSENCE of a directory. The true "
           "reason is a scope decision: that leg needs a DESCENDANTS relation between a design and "
           "the specs or plan items it produced, which is a different corpus and a different "
           "judgement from comparing the manifest against the shipped modules",
           set(DC.FINDINGS) == _dc_emitted and len(_dc_emitted) == 2)

    import ast as _dc_a

    def _dc_loads(path):
        try:
            tree = _dc_a.parse(path.read_text(errors="replace"))
        except (OSError, SyntaxError):
            return False
        for node in _dc_a.walk(tree):
            if not isinstance(node, _dc_a.Call):
                continue
            fname = (node.func.attr if isinstance(node.func, _dc_a.Attribute)
                     else getattr(node.func, "id", ""))
            if fname not in ("spec_from_file_location", "_organ", "_load", "_sibling"):
                continue
            for arg in list(node.args) + [kw.value for kw in node.keywords]:
                if isinstance(arg, _dc_a.Constant) and isinstance(arg.value, str) \
                        and arg.value.rstrip(".py").endswith("declared"):
                    return True
        return False

    _dc_skip = {".git", "__pycache__", "node_modules", "venv", ".venv"}
    _dc_scanned = [p for p in sorted(ROOT.rglob("*.py"))
                   if not (_dc_skip & set(p.relative_to(ROOT).parts))
                   and p.relative_to(ROOT).as_posix() != _DC_MODULE]
    _dc_loaders = sorted(p.relative_to(ROOT).as_posix() for p in _dc_scanned if _dc_loads(p))
    _dc_self = suite_file().resolve().relative_to(ROOT).as_posix()
    expect("VELDO-0005 AC5: THE ONLY THING THAT LOADS THIS ORGAN IS A SUITE FRAGMENT, and the scan "
           "PROVES ITS OWN DOMAIN by finding THIS FRAGMENT in it. The row this replaced claimed NO "
           "GATE STAGE LOADS THIS and globbed .veldo/*.py plus scripts/*.py non-recursively, so the "
           "one loader in the whole tree - this file, under scripts/suites/ - was outside its domain "
           "BY CONSTRUCTION and it reported an empty list. That claim is retracted: this fragment "
           "runs inside verify.sh's required unit stage like every other fragment, so what is true "
           "is that no gate SCRIPT consumes the organ's findings, which is what this row asserts "
           "over %d python file(s) recursively. A scan that cannot see its own loader is the defect, "
           "so it reds if the domain narrows again"
           % len(_dc_scanned),
           _dc_self in _dc_loaders
           and all(ldr.startswith("scripts/suites/") for ldr in _dc_loaders))

    # ITS FINDINGS GATE NOTHING, DRIVEN RATHER THAN PROMISED. Two of this fragment's live rows once
    # required this repository's unresolved set to be EMPTY and a design/ directory to be ABSENT,
    # and because the fragment runs in the required unit stage that made an ordinary repository
    # change red the gate on a heuristic verdict. So the live claims are one function, and it is
    # driven over a report carrying REAL findings in every bucket: unresolved, undeclared and
    # exempted. A row that starts pinning emptiness again reds HERE, in front of whoever wrote it,
    # instead of in front of whoever next adds a capability.
    _dc_live = DC.declared_report(root=ROOT)
    _dc_synth, _ = _dc_report(
        [("injected_stale", "status: mechanical, home: .veldo/never_was_here.py")],
        files=[".veldo/an_undeclared_module.py", ".veldo/an_exempted_helper.py"],
        exemptions='.veldo/an_exempted_helper.py: a fixture reason, so the bucket is not empty\n')
    _dc_worse = dict(_dc_live)
    for _dc_bucket in ("unresolved", "undeclared", "exempted"):
        _dc_worse[_dc_bucket] = list(_dc_live[_dc_bucket]) + list(_dc_synth[_dc_bucket])
    _dc_worse["capabilities"] = _dc_live["capabilities"] + _dc_synth["capabilities"]
    _dc_worse["modules"] = _dc_live["modules"] + _dc_synth["modules"]
    _dc_grew = all(len(_dc_worse[b]) > len(_dc_live[b])
                   for b in ("unresolved", "undeclared", "exempted"))
    expect("VELDO-0005 AC5: ITS FINDINGS GATE NOTHING, and that is DRIVEN here rather than "
           "promised. The organ-produced findings of a fixture tree are spliced into the live "
           "report so every bucket carries one - unresolved, undeclared and exempted - and every "
           "claim this fragment makes about a real tree is re-driven over THAT report and must "
           "still hold. The splice is asserted to have grown all three buckets first, so a green "
           "here cannot come from a control that never applied. This is the row that would have "
           "caught the defect independent review found: the old live rows required the unresolved "
           "set to be empty, so a correct declaration about a non-Claude pack root turned the "
           "required unit stage red",
           _dc_grew and _dc_clean(_dc_defects(ROOT, _dc_worse))
           and sorted(_dc_worse) == sorted(DC.REPORT_KEYS))


_dc_block("AC5", _dc_ac5)
