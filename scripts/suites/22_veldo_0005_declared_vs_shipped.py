"""VELDO-0005: where the capability manifest and the tree disagree.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, which always
runs, so its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 22_veldo_0005_declared_vs_shipped

WHAT IS UNDER TEST. .veldo/declared.py, driven directly. It reads no front matter and takes no
parser, because the manifest's note fields carry commas, braces and colons in prose and the ONE
parser is deliberately not asked to survive that - so the fixtures below are real manifest files
written in the manifest's own line shape.

THE ROWS THAT MATTER MOST ARE THE ONES OVER THE REAL MANIFEST. This item exists because the naive
resolver reported 42 unresolved homes of 167 on THIS repository and every one was false, so a
fixture-only suite would miss the entire point. The live rows below assert set equality and report
what they measured; none of them requires a count to be zero, because a row that pinned today's
manifest would redden the moment somebody adds a capability.

EVERY CRITERION'S BLOCK IS WRAPPED, so a raise reds a NAMED row instead of shortening the run.
"""
DC = V._VC._organ("declared", ROOT / ".veldo" / "declared.py")


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


def _dc_tree(d, rows, files=(), exemptions=None):
    """A tree with a manifest, some real files, and optionally an exemption list."""
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
    return base


def _dc_report(rows, files=(), exemptions=None):
    with tempfile.TemporaryDirectory() as d:
        base = _dc_tree(d, rows, files, exemptions)
        rep = DC.declared_report(root=base)
        return rep, DC.report_lines(rep)


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
    expect("VELDO-0005 AC1 OVER THE REAL MANIFEST, which is the row this item was written for: "
           "every one of this repository's %d declared capabilities resolves. Reported, not pinned - "
           "the row states that the unresolved SET is empty over the live manifest, and if a real "
           "stale declaration ever appears this reds and names it, which is the point"
           % _dc_live["capabilities"],
           _dc_live["unresolved"] == [] and _dc_live["capabilities"] > 100)


_dc_block("AC1", _dc_ac1)


# ---------------------------------------------------------------------------------------
# AC2. AN UNRESOLVED HOME CARRIES WHAT THE RESOLVER TRIED.
#
# FALSIFIED BY: drop the attempted-paths record, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _dc_ac2():
    rep, lines = _dc_report(
        [("stale", "status: mechanical, home: .veldo/moved_away.py")],
        files=[".veldo/a.py"])
    f = rep["unresolved"][0]
    expect("VELDO-0005 AC2: an unresolved finding carries the home AS DECLARED, WHICH segment "
           "failed, and EVERY ROOT that was searched. The obvious implementation of this check was "
           "wrong 42 times out of 167, so a finding reporting only its conclusion would have "
           "laundered every one of those into a fact about the file documentation defers to",
           f["home_as_declared"] == ".veldo/moved_away.py"
           and f["unresolved_segments"] == [".veldo/moved_away.py"]
           and f["roots_tried"] == list(DC.SEARCH_ROOTS)
           and f["capability"] == "stale" and f["finding"] == DC.FINDING_HOME_UNRESOLVED)
    expect("VELDO-0005 AC2: the PRINTED line carries the roots too, so the person deciding whether "
           "to edit the manifest sees where the resolver looked without opening a JSON file",
           any("could not find" in ln and "engine" in ln and "packs/claude" in ln
               for ln in lines))
    expect("VELDO-0005 AC2: the report names the roots it searched even when nothing is unresolved, "
           "so a reader can tell a clean run from a run that searched the wrong places",
           rep["roots_tried"] == list(DC.SEARCH_ROOTS) and len(rep["roots_tried"]) >= 2)


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
    _dc_mine = {".veldo/work_state.py", ".veldo/tasks.py", ".veldo/promises.py",
                ".veldo/behavior_floor.py", ".veldo/release_contract.py",
                ".veldo/declared.py"}
    expect("VELDO-0005 AC3 OVER THE REAL TREE: the six organs of the last three days are all "
           "DECLARED, which is the fix this measurement forced - 26 of 108 shipped modules were "
           "claimed by nothing when this was first run and five of them were the newest ones. "
           "Reported, not pinned: %d module(s) remain undeclared and this row does not require that "
           "number to be zero, because judging whether an internal helper deserves a capability is "
           "a human call and a row demanding zero would gate it"
           % len(_dc_live["undeclared"]),
           not (_dc_mine & {f["module"] for f in _dc_live["undeclared"]}))


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
# AC5. EACH LEG STANDS DOWN SEPARATELY AND IT GATES NOTHING.
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

    expect("VELDO-0005 AC5: A DESIGN-WITH-NO-DESCENDANTS LEG IS NOT BUILT, and this row says so "
           "rather than letting its absence read as coverage. This repository has no design/ "
           "directory, so the leg would ship with nothing to run against and its first real "
           "execution would be its first test. Asserted BOTH ways: the module declares no design "
           "finding, and the directory it would need really is absent here",
           set(DC.FINDINGS) == {DC.FINDING_HOME_UNRESOLVED, DC.FINDING_UNDECLARED_MODULE}
           and not (ROOT / "design").is_dir())

    import ast as _dc_a

    def _dc_loads(path):
        try:
            tree = _dc_a.parse(path.read_text())
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

    _dc_loaders = sorted(p.name for p in list((ROOT / ".veldo").glob("*.py"))
                         + list((ROOT / "scripts").glob("*.py"))
                         if p.name != "declared.py" and _dc_loads(p))
    expect("VELDO-0005 AC5: NO GATE STAGE LOADS THIS. PLAN-0018 NG3: a completeness organ that "
           "BLOCKED on a heuristic verdict would cut true sentences and stop real work, and this "
           "one's findings are judgement calls by construction. Asserted over LOADS via the AST, "
           "not over mentions, because /veldo:init legitimately NAMES the module to ship it",
           _dc_loaders == [])


_dc_block("AC5", _dc_ac5)
