"""VELDO-0008: veldo version, from one declaration.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, which always
runs, so its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 25_veldo_0008_version

WHAT IS UNDER TEST. .veldo/version.py, driven directly, plus its CLI driven as a subprocess because
a caller capturing its output is the reason the refusal path has to exit non-zero.

THE LIVE ROWS ASSERT SET MEMBERSHIP AND AGREEMENT, NOT A NUMBER. Nothing here pins 3.10.1: a row
that did would redden on the next release, which is the live-state defect this repository has been
bitten by five times. What is asserted is that the derived set CONTAINS the manifest nothing checked
before, and that every member agrees with the canonical declaration whatever it says.

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


def _vv_tree(d, canonical=None, others=()):
    """A tree with a canonical manifest and any number of other manifests, as real files."""
    base = Path(d)
    if canonical is not None:
        p = base / VV.CANONICAL
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"plugins": [{"name": "veldo", "version": canonical}]}))
    for rel, body in others:
        q = base / rel
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_text(body if isinstance(body, str) else json.dumps(body))
    return base


# ---------------------------------------------------------------------------------------
# AC1. EVERY MANIFEST THAT DECLARES A VERSION IS DERIVED, NOT LISTED.
#
# FALSIFIED BY: replace the derived sweep with a hand-written pair, and the row naming the third
# manifest must go red.
# ---------------------------------------------------------------------------------------


def _vv_ac1():
    live = VV.tracked_manifests(ROOT)
    expect("VELDO-0008 AC1: the derived set INCLUDES packs/antigravity/plugin.json - a third "
           "declaration of this project's version that NOTHING checked before this item. The one "
           "shipped assertion named two files, and its own comment says the manifests drifted apart "
           "once. Same hand-listed-pair defect as seven template pairs guarding nine modules",
           "packs/antigravity/plugin.json" in live
           and ".claude-plugin/marketplace.json" in live
           and "packs/claude/.claude-plugin/plugin.json" in live)
    expect("VELDO-0008 AC1 ANTI-VACUITY: the derived set is NON-EMPTY and has MORE THAN TWO members "
           "(%d), so a sweep that matched nothing - which would satisfy every agreement assertion "
           "below - reds here instead" % len(live),
           len(live) > 2)
    expect("VELDO-0008 AC1: fixture manifests are EXCLUDED with their reason declared - they exist to "
           "be read by a runner's own tests and are deliberately not this project's version, so "
           "sweeping them in would manufacture disagreements out of test data",
           not any("fixtures" in Path(rel).parts for rel in live)
           and VV.EXCLUDE_PARTS == ("fixtures",))

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
# FALSIFIED BY: fall back to a default string, and the row below must go red.
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
        d0 = rep["disagreements"][0]
        expect("VELDO-0008 AC3: a disagreement names BOTH manifests AND BOTH versions. 'The versions "
               "differ' is not actionable; 'this file says 3.9.0 and the canonical one says 3.10.1' "
               "is - and which side is wrong is not always the copy, which is exactly why both values "
               "have to be in the record",
               len(rep["disagreements"]) == 1
               and d0["manifest"] == "packs/drifted/plugin.json"
               and d0["declares"] == "3.9.0" and d0["canonical_declares"] == "3.10.1"
               and d0["canonical"] == VV.CANONICAL
               and rep["cause"] == VV.CAUSE_DISAGREEMENT
               and any("3.9.0" in ln and "3.10.1" in ln for ln in lines))

    with tempfile.TemporaryDirectory() as d:
        base = _vv_tree(d, "3.10.1", [("packs/ok/plugin.json", {"version": "3.10.1"})])
        rep2 = VV.version_report(base)
        expect("VELDO-0008 AC3 NEGATIVE CONTROL: two manifests that AGREE produce no disagreement "
               "and no cause, so the finding above discriminates rather than firing on any pair",
               rep2["disagreements"] == [] and rep2["cause"] is None and rep2["checked"] == 2)

    with tempfile.TemporaryDirectory() as d:
        base = _vv_tree(d, "3.10.1", [("packs/broken/plugin.json", "{not json")])
        rep3 = VV.version_report(base)
        expect("VELDO-0008 AC3: an UNPARSEABLE manifest is its own finding, separate from a "
               "disagreement, because the fix differs - one file needs repairing and the other needs "
               "a number changed",
               [u["manifest"] for u in rep3["unparseable"]] == ["packs/broken/plugin.json"]
               and rep3["disagreements"] == [])

    expect("VELDO-0008 AC3 OVER THE LIVE TREE: every derived manifest AGREES with the canonical "
           "declaration, whatever it says. Nothing here pins the number - a row asserting 3.10.1 "
           "would redden on the next release, which is the live-state defect this repository has "
           "been bitten by five times",
           VV.version_report(ROOT)["disagreements"] == []
           and VV.version_report(ROOT)["unparseable"] == []
           and VV.version_report(ROOT)["version"] is not None)


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
    expect("VELDO-0008 AC4: the CLI prints the version AND the canonical path, exiting zero. The "
           "path is printed because an adopter debugging a version needs to know which file to look "
           "at, and a bare number does not say",
           ok.returncode == 0 and VV.CANONICAL in ok.stdout
           and VV.version(ROOT)[0] in ok.stdout)

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
        expect("VELDO-0008 AC5: a tree with a canonical declaration and NO other manifest - which is "
               "what an adopting repository looks like - reports AGREEMENT over a set of ONE with the "
               "count named. Not silence, and not a claim that many copies were checked: the count "
               "that was checked is part of the answer",
               rep["checked"] == 1 and rep["version"] == "7.0.0"
               and rep["cause"] is None and rep["disagreements"] == []
               and any("1 manifest(s) checked" in ln for ln in lines))
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
