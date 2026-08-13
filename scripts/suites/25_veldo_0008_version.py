"""VELDO-0008: veldo version, from one declaration.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, which always
runs, so its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 25_veldo_0008_version

WHAT IS UNDER TEST. .veldo/version.py, driven directly, plus its CLI driven as a subprocess because
a caller capturing its output is the reason the refusal path has to exit non-zero.

THE LIVE ROWS ASSERT SET MEMBERSHIP AND AGREEMENT, NOT A NUMBER. Nothing here pins 3.10.1: a row
that did would redden on the next release, which is the live-state defect this repository has been
bitten by five times. What is asserted is that the derived set CONTAINS all three tracked
declarations, and that every manifest CLAIMING TO DECLARE THIS PROJECT'S VERSION agrees with the
canonical declaration whatever it says.

AND THE SETS REQUIRED EMPTY ARE DEFECT SETS BY CONSTRUCTION, which is what makes them safe to
require. Independent review drove the version this replaces: it required agreement over every tracked
file NAMED plugin.json, so committing one third-party sample under a runner's testdata/ reddened the
gate with a message claiming this repository's manifests disagree. A file that does not say it
declares veldo's version is now reported and never accused, so growth cannot join the accused set.

EVERY CRITERION'S BLOCK IS WRAPPED, so a raise reds a NAMED row instead of shortening the run.
"""
import re as _vv_re
import subprocess as _vv_sp
import sys as _vv_sys

VV = V._VC._organ("version", ROOT / ".veldo" / "version.py")


def _vv_block(label, fn):
    try:
        fn()
    except Exception as _vv_e:                   # noqa: BLE001 - a raise must RED a row, never skip
        expect("VELDO-0008 %s: the block ran to completion rather than raising (%r)"
               % (label, _vv_e), False)


def _vv_first(seq):
    """The first finding of a list, or an empty one. LEDGER FINDING 67: a mutation that EMPTIES a
    findings list must red the row that NAMES the property, not the block's wrapper with an IndexError.
    Driven while remediating this item: replacing the derived sweep with a hand-listed pair emptied the
    disagreement list in a fixture tree, `rep["disagreements"][0]` raised, and AC3's named rows vanished
    from the run instead of one of them reddening."""
    return seq[0] if seq else {}


def _vv_tree(d, canonical=None, others=()):
    """A tree with a canonical manifest and any number of other manifests, as real files.

    A DICT BODY IS GIVEN THIS PROJECT'S NAME unless it already declares one, because a manifest that
    does not say WHOSE version it declares is not this project's (see version.attribution), so a
    fixture built without the name would be exercising the attribution path while its row claims to be
    about agreement. A raw string body is written verbatim, which is how the unreadable cases are
    built."""
    base = Path(d)
    if canonical is not None:
        p = base / VV.CANONICAL
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"plugins": [{"name": "veldo", "version": canonical}]}))
    for rel, body in others:
        q = base / rel
        q.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(body, dict) and "plugins" not in body:
            body = dict(body)
            body.setdefault("name", VV.PLUGIN_NAME)
        q.write_text(body if isinstance(body, str) else json.dumps(body))
    return base


def _vv_marketplace(d, entries, top=None, others=()):
    """A tree whose canonical manifest hosts the given plugin ENTRIES verbatim, so a row can put a
    co-hosted plugin ahead of ours, name two entries the same, or add a schema version beside the
    list - the shapes a marketplace really takes, none of which a positional read survives."""
    base = Path(d)
    p = base / VV.CANONICAL
    p.parent.mkdir(parents=True, exist_ok=True)
    body = dict(top or {})
    body["plugins"] = list(entries)
    p.write_text(json.dumps(body))
    for rel, other in others:
        q = base / rel
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_text(other if isinstance(other, str) else json.dumps(other))
    return base


# ---------------------------------------------------------------------------------------
# AC1. EVERY MANIFEST THAT DECLARES A VERSION IS DERIVED, NOT LISTED.
#
# FALSIFIED BY: replace the derived sweep with a hand-written pair, and the row naming the third
# manifest must go red.
# ---------------------------------------------------------------------------------------


def _vv_ac1():
    live = VV.tracked_manifests(ROOT)
    expect("VELDO-0008 AC1: the derived set INCLUDES all three tracked declarations, packs/antigravity "
           "/plugin.json among them. THE PREMISE THIS ROW USED TO CARRY WAS FALSE and independent "
           "review measured it: it said nothing checked that third manifest before this item, when "
           "WARP-1311 AC5 already swept all three BY DERIVATION (the marketplace's plugin entries plus "
           "packs/*/plugin.json and packs/*/.claude-plugin/plugin.json) and reds when any one of them "
           "moves. What this set adds is reach - derived from git ls-files by FILENAME, so a "
           "declaration at a shape none of those globs matches is covered by arriving - and a NAMED "
           "canonical side, so a disagreement can say which file to edit",
           "packs/antigravity/plugin.json" in live
           and ".claude-plugin/marketplace.json" in live
           and "packs/claude/.claude-plugin/plugin.json" in live)
    expect("VELDO-0008 AC1 ANTI-VACUITY: the derived set is NON-EMPTY and has MORE THAN TWO members "
           "(%d), so a sweep that matched nothing - which would satisfy every agreement assertion "
           "below - reds here instead" % len(live),
           len(live) > 2)

    # THE DECLARED EXCLUSION, PROVEN BY BUILDING ONE. Independent review measured the row that used to
    # stand here holding with the exclusion DELETED from both copies of the module: its two clauses
    # were `no live path contains 'fixtures'`, true because the tracked fixtures are named
    # pass.plugin.json and fail.plugin.json so the NAME filter already drops them, and
    # `EXCLUDE_PARTS == ('fixtures',)`, a literal compared with itself. Nothing ever constructed a
    # fixture manifest to be excluded, so a claimed exclusion had no behaviour behind it.
    with tempfile.TemporaryDirectory() as d:
        base = _vv_tree(d, "9.9.9", [("scripts/runners/plugin/fixtures/plugin.json",
                                      {"name": VV.PLUGIN_NAME, "version": "1.0.0"})])
        got_fx = VV.tracked_manifests(base)
        rep_fx = VV.version_report(base)
        expect("VELDO-0008 AC1: a fixture manifest named exactly plugin.json under a fixtures/ path, "
               "DECLARING THIS PROJECT'S NAME and a DIFFERENT version, is EXCLUDED from the derived "
               "set and therefore accused of nothing. Built rather than asserted: the name filter "
               "cannot save this one and attribution cannot either, so the exclusion is the only thing "
               "keeping it out and deleting EXCLUDE_PARTS reds this row",
               "scripts/runners/plugin/fixtures/plugin.json" not in got_fx
               and rep_fx["disagreements"] == [] and rep_fx["cause"] is None
               and rep_fx["checked"] == 1)

    with tempfile.TemporaryDirectory() as d:
        base = _vv_tree(d, "9.9.9", [("scripts/runners/plugin/testdata/plugin.json",
                                      {"name": VV.PLUGIN_NAME, "version": "1.0.0"})])
        got_td = VV.tracked_manifests(base)
        rep_td = VV.version_report(base)
        expect("VELDO-0008 AC1 NEGATIVE CONTROL for the exclusion: the SAME manifest one directory "
               "over, not under fixtures/, IS swept and IS reported as a disagreement - so the "
               "exclusion measures the declared path component rather than the sweep being blind to "
               "this shape of file",
               "scripts/runners/plugin/testdata/plugin.json" in got_td
               and [x["manifest"] for x in rep_td["disagreements"]]
               == ["scripts/runners/plugin/testdata/plugin.json"])

    expect("VELDO-0008 AC1: and no fixture path survives into the LIVE derived set, whatever the "
           "tracked fixtures are called",
           not any("fixtures" in Path(rel).parts for rel in live))

    with tempfile.TemporaryDirectory() as d:
        base = _vv_tree(d, "9.9.9", [("packs/new/plugin.json", {"version": "9.9.9"})])
        got = VV.tracked_manifests(base)
        expect("VELDO-0008 AC1: a pack added LATER is covered by ARRIVING rather than by being "
               "remembered - a manifest this fragment never named is in the derived set, over a tree "
               "with no git history at all, which is the shape a scaffolded repository has",
               "packs/new/plugin.json" in got and VV.CANONICAL in got)


_vv_block("AC1", _vv_ac1)


# ---------------------------------------------------------------------------------------
# AC2. NO GUESSED VERSION, EVER.
#
# FALSIFIED BY: fall back to a default string, and the row below must go red. ALSO FALSIFIED BY
# dropping the shape test from read_manifest, and by reading plugins[0] instead of the entry named
# PLUGIN_NAME - each has its own row below, because both of those WERE the code and both answered
# with a version this installation is not while this suite stayed green.
# ---------------------------------------------------------------------------------------


def _vv_ac2():
    with tempfile.TemporaryDirectory() as d:
        base = _vv_tree(d, None, [("packs/a/plugin.json", {"version": "1.2.3"})])
        v, cause, detail = VV.version(base)
        expect("VELDO-0008 AC2: with the canonical declaration ABSENT the reader returns NO version "
               "and refuses by name, even though another manifest right there declares 1.2.3. A "
               "default or a fallback would be the confident-zero disease applied to identity: an "
               "installation reporting a version it invented sends a bug report to the wrong tree",
               v is None and cause == VV.CAUSE_CANONICAL_ABSENT and "guessed" in detail)

    with tempfile.TemporaryDirectory() as d:
        base = _vv_tree(d, None)
        (base / VV.CANONICAL).parent.mkdir(parents=True, exist_ok=True)
        (base / VV.CANONICAL).write_text("{not json")
        v2, cause2, _ = VV.version(base)
        expect("VELDO-0008 AC2: an UNREADABLE canonical declaration refuses the same way, so a "
               "corrupted manifest cannot produce a version either",
               v2 is None and cause2 == VV.CAUSE_CANONICAL_ABSENT)

    with tempfile.TemporaryDirectory() as d:
        base = _vv_tree(d, "4.5.6")
        v3, cause3, _ = VV.version(base)
        expect("VELDO-0008 AC2 NEGATIVE CONTROL: with the canonical declaration present the same "
               "reader returns the real version and no cause, so the refusal is a measurement rather "
               "than the reader's only answer",
               v3 == "4.5.6" and cause3 is None)

    # A STRING IS NOT A VERSION. Every one of these was answered with exit zero before this row
    # existed: the reader refused only on a missing key, so "" and "TBD" travelled all the way to a
    # caller as this installation's identity.
    for label, declared in (("the EMPTY string", ""), ("whitespace", "   "),
                            ("a placeholder", "TBD"), ("a single integer", "1"),
                            ("a word with a dot", "next.build")):
        with tempfile.TemporaryDirectory() as d:
            base = _vv_tree(d, declared)
            vs, causes, details = VV.version(base)
            expect("VELDO-0008 AC2: a canonical declaration of %s (%r) is NOT a version, so the "
                   "reader REFUSES instead of reporting it. An installation answering with an empty "
                   "identity and a zero exit is the confident-zero disease wearing a pass, and it "
                   "cannot be caught downstream by proving the answer is PRESENT: the empty string "
                   "is a substring of every string" % (label, declared),
                   vs is None and causes == VV.CAUSE_CANONICAL_ABSENT
                   and "not version-shaped" in (details or ""))

    with tempfile.TemporaryDirectory() as d:
        base = _vv_marketplace(d, [{"name": "veldo-companion", "version": "9.9.9"},
                                   {"name": VV.PLUGIN_NAME, "version": "3.11.0"}])
        vp, causep, _ = VV.version(base)
        expect("VELDO-0008 AC2: the canonical read matches the entry NAMED %r rather than taking "
               "plugins[0]. With a co-hosted plugin listed FIRST the positional read answered 9.9.9 "
               "- a version this installation is not - and nothing downstream could notice, because "
               "every copy of the real number then 'disagrees' with the intruder rather than the "
               "other way round" % VV.PLUGIN_NAME,
               (vp, causep) == ("3.11.0", None))

    with tempfile.TemporaryDirectory() as d:
        base = _vv_marketplace(d, [{"name": VV.PLUGIN_NAME, "version": "3.11.0"}],
                               top={"version": "1"})
        vt, causet, _ = VV.version(base)
        expect("VELDO-0008 AC2: a top-level \"version\" beside the plugin list is a SCHEMA version "
               "and does not shadow the entry. Reading the top level first answered '1' as this "
               "product's identity, with exit zero",
               (vt, causet) == ("3.11.0", None))

    with tempfile.TemporaryDirectory() as d:
        base = _vv_marketplace(d, [{"name": "veldo-companion", "version": "2.0.0"}])
        vn, causen, detailn = VV.version(base)
        expect("VELDO-0008 AC2: a marketplace with NO entry named %r declares no version for this "
               "installation, so the reader refuses and NAMES the entries it did find. Answering "
               "with somebody else's plugin version would be a guess about this one" % VV.PLUGIN_NAME,
               vn is None and causen == VV.CAUSE_CANONICAL_ABSENT
               and VV.PLUGIN_NAME in (detailn or "") and "veldo-companion" in (detailn or ""))

    with tempfile.TemporaryDirectory() as d:
        base = _vv_marketplace(d, [{"name": VV.PLUGIN_NAME, "version": "3.10.1"},
                                   {"name": VV.PLUGIN_NAME, "version": "3.11.0"}])
        va, causea, detaila = VV.version(base)
        expect("VELDO-0008 AC2: two entries claiming the name and declaring different versions is an "
               "AMBIGUITY, not a tie-break to guess at - the reader refuses and says how many "
               "entries claimed it, because picking one is exactly the positional read again",
               va is None and causea == VV.CAUSE_CANONICAL_ABSENT
               and "do not declare one version" in (detaila or ""))

    with tempfile.TemporaryDirectory() as d:
        entries = [{"name": VV.PLUGIN_NAME, "version": "3.10.1"},
                   {"name": "veldo-companion", "version": "0.4.0"}]
        base = _vv_marketplace(d, entries,
                               others=[("packs/claude/plugin.json",
                                        {"name": "veldo", "version": "3.10.1"})])
        hosted = json.loads((base / VV.CANONICAL).read_text())["plugins"]
        repn = VV.version_report(base)
        expect("VELDO-0008 AC2 NEGATIVE CONTROL, ADDITIVE: a legitimately co-hosted plugin ADDED to "
               "the marketplace at its own version (%d entries present, the second declaring 0.4.0) "
               "changes nothing - this installation is still 3.10.1, the pack still agrees, no cause. "
               "So the rows above discriminate between a co-hosted entry and a wrong answer rather "
               "than refusing every marketplace that hosts more than one plugin" % len(hosted),
               len(hosted) == 2 and hosted[1]["version"] == "0.4.0"
               and repn["version"] == "3.10.1" and repn["cause"] is None
               and repn["disagreements"] == [] and repn["unparseable"] == []
               and repn["checked"] == 2)


_vv_block("AC2", _vv_ac2)


# ---------------------------------------------------------------------------------------
# AC3. A DISAGREEMENT NAMES BOTH SIDES.
#
# FALSIFIED BY: report only that the versions differ, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _vv_ac3():
    with tempfile.TemporaryDirectory() as d:
        base = _vv_tree(d, "3.10.1", [("packs/drifted/plugin.json", {"version": "3.9.0"})])
        rep = VV.version_report(base)
        lines = VV.report_lines(rep)
        d0 = _vv_first(rep["disagreements"])
        expect("VELDO-0008 AC3: a disagreement names BOTH manifests AND BOTH versions. 'The versions "
               "differ' is not actionable; 'this file says 3.9.0 and the canonical one says 3.10.1' "
               "is - and which side is wrong is not always the copy, which is exactly why both values "
               "have to be in the record",
               len(rep["disagreements"]) == 1
               and d0.get("manifest") == "packs/drifted/plugin.json"
               and d0.get("declares") == "3.9.0" and d0.get("canonical_declares") == "3.10.1"
               and d0.get("canonical") == VV.CANONICAL
               and rep["cause"] == VV.CAUSE_DISAGREEMENT
               and any("3.9.0" in ln and "3.10.1" in ln for ln in lines))

    with tempfile.TemporaryDirectory() as d:
        base = _vv_tree(d, "3.10.1", [("packs/ok/plugin.json", {"version": "3.10.1"})])
        rep2 = VV.version_report(base)
        expect("VELDO-0008 AC3 NEGATIVE CONTROL: two manifests that AGREE produce no disagreement "
               "and no cause, so the finding above discriminates rather than firing on any pair",
               rep2["disagreements"] == [] and rep2["cause"] is None and rep2["checked"] == 2)

    with tempfile.TemporaryDirectory() as d:
        base = _vv_tree(d, "3.10.1", [("packs/broken/plugin.json", {"name": VV.PLUGIN_NAME})])
        rep3 = VV.version_report(base)
        expect("VELDO-0008 AC3: a manifest that SAYS IT IS THIS PROJECT'S and declares no readable "
               "version is UNPARSEABLE - its own finding, separate from a disagreement, because the fix "
               "differs: one file needs repairing and the other needs a number changed",
               [u["manifest"] for u in rep3["unparseable"]] == ["packs/broken/plugin.json"]
               and rep3["disagreements"] == [] and rep3["checked"] == 2)

    # ATTRIBUTION: WHOSE VERSION IS THIS. Independent review drove the defect these rows close - a
    # tracked third-party sample at engine/scripts/runners/plugin/testdata/plugin.json reddened the
    # gate with a message claiming THIS repository's version manifests disagree, and the plugin-load
    # runner's own default manifest name is literally plugin.json.
    with tempfile.TemporaryDirectory() as d:
        base = _vv_tree(d, "3.10.1", [("engine/scripts/runners/plugin/testdata/plugin.json",
                                       {"name": "third-party-sample", "version": "1.0.0"})])
        repf = VV.version_report(base)
        lines_f = VV.report_lines(repf)
        expect("VELDO-0008 AC3: a manifest naming SOMEBODY ELSE is NOT THIS PROJECT'S - reported by "
               "path with the reason, accused of nothing, and counted in `swept` but not in `checked`. "
               "The sweep finds candidates by FILENAME, which is the right way to find them and the "
               "wrong way to decide whose they are; conflating the two made this reader tell a "
               "maintainer that a vendored sample was this repository's version manifest drifting",
               repf["disagreements"] == [] and repf["cause"] is None
               and [n["manifest"] for n in repf["not_this_project"]]
               == ["engine/scripts/runners/plugin/testdata/plugin.json"]
               and "third-party-sample" in _vv_first(repf["not_this_project"]).get("detail", "")
               and (repf["swept"], repf["checked"]) == (2, 1)
               and any("NOT THIS PROJECT'S" in ln for ln in lines_f))

    with tempfile.TemporaryDirectory() as d:
        base = _vv_tree(d, "3.10.1", [("vendor/tool/plugin.json", "{not json")])
        repu = VV.version_report(base)
        expect("VELDO-0008 AC3: a file named plugin.json that cannot be read as JSON AT ALL cannot be "
               "attributed either, so it is NAMED as not this project's rather than accused of "
               "declaring the wrong version. A reader may not tell a maintainer to fix a number in a "
               "file it could not even parse, and it may not require a set that any vendored corrupt "
               "manifest can join to stay empty",
               repu["disagreements"] == [] and repu["unparseable"] == []
               and [n["manifest"] for n in repu["not_this_project"]] == ["vendor/tool/plugin.json"]
               and "cannot be attributed" in _vv_first(repu["not_this_project"]).get("detail", ""))

    with tempfile.TemporaryDirectory() as d:
        base = _vv_marketplace(d, [{"name": "veldo-companion", "version": "1.0.0"},
                                   {"name": VV.PLUGIN_NAME, "version": "3.10.1"}],
                               others=[("packs/claude/plugin.json",
                                        {"name": "veldo", "version": "3.10.1"}),
                                       ("packs/antigravity/plugin.json",
                                        {"name": "veldo", "version": "3.10.1"})])
        repi = VV.version_report(base)
        expect("VELDO-0008 AC3: a co-hosted marketplace entry does not INVERT THE BLAME. Every pack "
               "declares what the veldo entry declares, so there is no disagreement to report; "
               "reading plugins[0] named BOTH packs as the ones that had drifted, away from a number "
               "that is not this project's at all - the exact inverse of the diagnosis this criterion "
               "promises, and the wrong two files to go and edit",
               repi["disagreements"] == [] and repi["cause"] is None
               and repi["version"] == "3.10.1" and repi["checked"] == 3
               and repi["manifests"][VV.CANONICAL] == "3.10.1")

    _vv_lrep = VV.version_report(ROOT)
    expect("VELDO-0008 AC3 OVER THE LIVE TREE: every manifest that CLAIMS TO DECLARE THIS PROJECT'S "
           "VERSION agrees with the canonical declaration, whatever it says. Nothing here pins the "
           "number, and the two sets required empty are DEFECT SETS BY CONSTRUCTION - a file saying it "
           "declares veldo's version and declaring the wrong one, or none that can be read, is wrong "
           "however the tree grows. Independent review drove the version this replaces: it equated 'a "
           "tracked file named plugin.json' with 'a declaration of THIS project's version', so "
           "committing one third-party sample reddened the gate with a message claiming this "
           "repository's manifests disagree. MEASURED at this run, pinned nowhere: %d swept by name, "
           "%d of them this project's, %d belonging to somebody else or unreadable"
           % (_vv_lrep["swept"], _vv_lrep["checked"], len(_vv_lrep["not_this_project"])),
           _vv_lrep["disagreements"] == []
           and _vv_lrep["unparseable"] == []
           and _vv_lrep["version"] is not None)
    expect("VELDO-0008 AC3 ANTI-VACUITY over the live tree: MORE THAN TWO manifests were attributed to "
           "this project (%d), so the agreement above cannot hold because attribution swept the whole "
           "set away - which is the one way narrowing a domain can turn a real check into a green one"
           % _vv_lrep["checked"],
           _vv_lrep["checked"] > 2
           and _vv_lrep["checked"] + len(_vv_lrep["not_this_project"]) == _vv_lrep["swept"])


_vv_block("AC3", _vv_ac3)


# ---------------------------------------------------------------------------------------
# AC4. THE CLI ANSWERS WHAT THIS INSTALLATION IS, AND FAILS LOUD WHEN IT CANNOT.
#
# FALSIFIED BY: print a version when the canonical declaration is absent, and the row below must
# go red.
# ---------------------------------------------------------------------------------------


def _vv_ac4():
    ok = _vv_sp.run([_vv_sys.executable, str(ROOT / ".veldo" / "version.py")],
                    cwd=str(ROOT), capture_output=True, text=True)
    live = VV.version(ROOT)[0]
    first = (ok.stdout.split() or [""])[0]
    expect("VELDO-0008 AC4: the CLI prints the version AND the canonical path, exiting zero. The "
           "path is printed because an adopter debugging a version needs to know which file to look "
           "at, and a bare number does not say. THE FIRST TOKEN IS COMPARED FOR EQUALITY and tested "
           "for version SHAPE, not scanned for as a substring: `version(ROOT)[0] in stdout` cannot "
           "fail when the declaration is the empty string, which is the one state where the clause "
           "had to hold - it printed ' (from %s)' with exit zero and this row passed"
           % VV.CANONICAL,
           ok.returncode == 0 and VV.CANONICAL in ok.stdout
           and first == live and VV._version_shaped(live))

    with tempfile.TemporaryDirectory() as d:
        base = _vv_tree(d, None)
        vdir = base / ".veldo"
        vdir.mkdir(parents=True, exist_ok=True)
        (vdir / "version.py").write_text((ROOT / ".veldo" / "version.py").read_text())
        bad = _vv_sp.run([_vv_sys.executable, str(vdir / "version.py")],
                         cwd=str(base), capture_output=True, text=True)
        expect("VELDO-0008 AC4: with NO canonical declaration the CLI exits NON-ZERO and prints the "
               "refusal rather than a number, so a script capturing its output can never silently "
               "receive a guess. Driven as a real subprocess, because the exit status is the whole "
               "property and calling the function would not test it. Asserted THREE ways: non-zero "
               "exit, the refusal named in the output, and NO version-shaped string anywhere in it",
               bad.returncode != 0
               and VV.CAUSE_CANONICAL_ABSENT in bad.stdout
               and not _vv_re.search(r"\b\d+\.\d+\.\d+\b", bad.stdout))

    # THE STATE THAT DEFEATED THIS CRITERION'S CLOSING GUARANTEE, driven as a subprocess exactly as
    # a caller runs it. A canonical declaration of "" is PRESENT and READABLE, so nothing refused:
    # the CLI printed " (from .claude-plugin/marketplace.json)" and exited 0, and --report claimed
    # agreement over three manifests and exited 0.
    for label, declared in (("the EMPTY string", ""), ("a placeholder", "TBD")):
        with tempfile.TemporaryDirectory() as d:
            base = _vv_tree(d, declared)
            vdir = base / ".veldo"
            vdir.mkdir(parents=True, exist_ok=True)
            (vdir / "version.py").write_text((ROOT / ".veldo" / "version.py").read_text())
            bare = _vv_sp.run([_vv_sys.executable, str(vdir / "version.py")],
                              cwd=str(base), capture_output=True, text=True)
            rep = _vv_sp.run([_vv_sys.executable, str(vdir / "version.py"), "--report"],
                             cwd=str(base), capture_output=True, text=True)
            expect("VELDO-0008 AC4: a canonical declaration of %s makes BOTH the bare CLI and "
                   "--report exit NON-ZERO and print the refusal. This is the state where 'a script "
                   "capturing its output can never silently receive a guess' was false: the script "
                   "received %r and a ZERO exit, which reads as a pass, and no presence check could "
                   "see it because the empty string is a substring of everything"
                   % (label, "%s (from %s)" % (declared, VV.CANONICAL)),
                   bare.returncode != 0 and VV.CAUSE_CANONICAL_ABSENT in bare.stdout
                   and "not version-shaped" in bare.stdout
                   and rep.returncode != 0 and VV.CAUSE_CANONICAL_ABSENT in rep.stdout)


_vv_block("AC4", _vv_ac4)


# ---------------------------------------------------------------------------------------
# AC5. A TREE WITH ONE MANIFEST AGREES WITH ITSELF, AND SAYS SO.
#
# FALSIFIED BY: remove the absent-manifest stand-down, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _vv_ac5():
    with tempfile.TemporaryDirectory() as d:
        base = _vv_tree(d, "7.0.0")
        rep = VV.version_report(base)
        lines = VV.report_lines(rep)
        expect("VELDO-0008 AC5: a tree with a canonical declaration and NO other manifest reports "
               "AGREEMENT over a set of ONE with the count named. Not silence, and not a claim that "
               "many copies were checked: the count that was checked is part of the answer. THIS IS NOT "
               "WHAT AN ADOPTING REPOSITORY LOOKS LIKE, and the row used to say it was - independent "
               "review installed one and measured it: the scaffolder lays .veldo/version.py and NO "
               "marketplace manifest, so a real adopter's tree is VERSION_CANONICAL_ABSENT, which AC2 "
               "and AC4 cover, and what its veldo version IS lives in the install stamp that "
               "VELDO-0009's drift() reads. What this row covers is a MARKETPLACE with one entry and no "
               "packs, and the honest report over a set of one",
               rep["checked"] == 1 and rep["swept"] == 1 and rep["version"] == "7.0.0"
               and rep["cause"] is None and rep["disagreements"] == []
               and any("1 manifest(s) checked" in ln for ln in lines))

    # AND THE STATE A REAL ADOPTER IS IN, ASSERTED HERE SO THE CLAIM ABOVE CANNOT DRIFT BACK. Driven
    # rather than described: the reader refuses in a tree laid down by the shipped scaffolder.
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        (base / ".veldo").mkdir(parents=True)
        (base / ".veldo" / "installed.json").write_text(json.dumps(
            {"schema": "veldo.installed/v1", "version": "7.0.0"}))
        repa = VV.version_report(base)
        expect("VELDO-0008 AC5: in an ADOPTER-SHAPED tree - an install stamp and no marketplace "
               "manifest, because an adopting repository is not a marketplace - this reader REFUSES "
               "with %s over a set of ZERO rather than reporting agreement with itself. The set of one "
               "above is a marketplace, not an adopter, and conflating them let the criterion be "
               "justified by a tree nothing in the field produces" % VV.CAUSE_CANONICAL_ABSENT,
               repa["cause"] == VV.CAUSE_CANONICAL_ABSENT and repa["version"] is None
               and repa["checked"] == 0 and repa["swept"] == 0)
    expect("VELDO-0008 AC5: the report carries ONE KEY SHAPE whether it refused or not, so a "
           "consumer never guesses whether a key is missing or genuinely empty",
           sorted(VV.version_report(ROOT)) == sorted(VV.REPORT_KEYS)
           and sorted(VV.version_report(Path(tempfile.gettempdir()) / "no-such-veldo-tree"))
           == sorted(VV.REPORT_KEYS))
    expect("VELDO-0008 AC5: every declared cause is registered under a unique name",
           len(set(VV.CAUSES)) == len(VV.CAUSES)
           and {VV.CAUSE_CANONICAL_ABSENT, VV.CAUSE_DISAGREEMENT, VV.CAUSE_UNPARSEABLE}
           == set(VV.CAUSES))


_vv_block("AC5", _vv_ac5)
