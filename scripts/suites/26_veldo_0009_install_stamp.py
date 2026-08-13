"""VELDO-0009: init stamps what it laid down, and the drift detector that gives the stamp a purpose.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, which always
runs, so its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 26_veldo_0009_install_stamp

WHAT IS UNDER TEST. .veldo/init_scaffold.py's stamp writer and .veldo/version.py's stamp reader and
drift detector. THE SCAFFOLDER IS RUN FOR REAL into temporary trees, because the property is what an
install produces and a fixture would test the fixture.

EVERY CRITERION'S BLOCK IS WRAPPED, so a raise reds a NAMED row instead of shortening the run.
"""
import subprocess as _is_sp

ISC9 = V._VC._organ("init_scaffold", ROOT / ".veldo" / "init_scaffold.py")
VV9 = V._VC._organ("version", ROOT / ".veldo" / "version.py")


def _is_block(label, fn):
    try:
        fn()
    except Exception as _is_e:                   # noqa: BLE001 - a raise must RED a row, never skip
        expect("VELDO-0009 %s: the block ran to completion rather than raising (%r)"
               % (label, _is_e), False)


def _is_install(d):
    """A real install into d, with git initialised the way an adopter's tree is."""
    _is_sp.run(["git", "init", "-q", "."], cwd=str(d), capture_output=True)
    return ISC9.scaffold(d)


# ---------------------------------------------------------------------------------------
# AC1. THE STAMP IS GENERATED, NEVER COPIED.
#
# FALSIFIED BY: add it to the copied-template list, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _is_ac1():
    with tempfile.TemporaryDirectory() as d:
        rep = _is_install(d)
        stamp_path = Path(d) / ISC9.STAMP
        expect("VELDO-0009 AC1: a fresh install CARRIES a stamp, and it is reported as created",
               stamp_path.is_file() and ISC9.STAMP in rep["created"]
               and rep["stamp"] and rep["stamp"]["schema"] == ISC9.STAMP_SCHEMA)
        expect("VELDO-0009 AC1: NO TEMPLATE for the stamp exists in the templates tree, so it is "
               "GENERATED rather than copied. Not a style choice: a copied template would have to be "
               "tracked and published, and this session already found what happens when the "
               "scaffolder DEMANDS a template the published pack does not carry - every install fails "
               "with 'template missing', which is the 1.0 defect exactly",
               not (ISC9.DEFAULT_TEMPLATES / ISC9.STAMP).exists()
               and ISC9.STAMP not in ISC9._FILES)
        stamp = json.loads(stamp_path.read_text())
        expect("VELDO-0009 AC1: the stamp records the version, the moment, AND the templates path it "
               "was laid from, so a reader knows not just which version but which tree produced it",
               stamp["version"] and stamp["installed_at"].endswith("Z")
               and stamp["laid_from"] and Path(stamp["laid_from"]).exists())


_is_block("AC1", _is_ac1)


# ---------------------------------------------------------------------------------------
# AC2. CREATE-ONLY, LIKE EVERYTHING ELSE THE SCAFFOLDER LAYS.
#
# FALSIFIED BY: overwrite an existing stamp, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _is_ac2():
    with tempfile.TemporaryDirectory() as d:
        _is_install(d)
        first = (Path(d) / ISC9.STAMP).read_bytes()
        again = ISC9.scaffold(d)
        expect("VELDO-0009 AC2: a SECOND scaffold reports the stamp as SKIPPED and leaves it "
               "byte-identical. A stamp rewritten by a later re-run that laid nothing would erase the "
               "only evidence of drift at the exact moment somebody was looking for it",
               ISC9.STAMP in again["skipped"]
               and ISC9.STAMP not in again["created"]
               and (Path(d) / ISC9.STAMP).read_bytes() == first
               and again["stamp"] is None)


_is_block("AC2", _is_ac2)


# ---------------------------------------------------------------------------------------
# AC3. NO STAMP IS BETTER THAN A STAMP THAT GUESSES.
#
# FALSIFIED BY: write a placeholder version, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _is_ac3():
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        created, skipped = [], []
        got = ISC9._write_stamp(base / "no-templates-here", base, created, skipped)
        expect("VELDO-0009 AC3: templates declaring NO version produce NO stamp at all - not one "
               "saying unknown, and not a placeholder. An unstamped install is an honest state a "
               "reader can act on; a stamp that guesses makes a drift detector confidently wrong",
               got is None and created == [] and not (base / ISC9.STAMP).exists())

    for shape, rel in (("a composed Claude pack", ".claude-plugin/plugin.json"),
                       ("a composed pack with its manifest at the root", "plugin.json"),
                       ("a marketplace tree", ".claude-plugin/marketplace.json")):
        with tempfile.TemporaryDirectory() as d:
            t = Path(d) / "templates"
            p = t / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            body = ({"plugins": [{"version": "5.5.5"}]} if rel.endswith("marketplace.json")
                    else {"version": "5.5.5"})
            p.write_text(json.dumps(body))
            expect("VELDO-0009 AC3: the version is found in %s. THREE REAL SHAPES are searched rather "
                   "than one assumed - assuming a single shape is precisely what made 1.0 "
                   "uninstallable" % shape,
                   ISC9._template_version(t) == "5.5.5")

    with tempfile.TemporaryDirectory() as d:
        parent = Path(d)
        (parent / ".claude-plugin").mkdir(parents=True)
        (parent / ".claude-plugin" / "marketplace.json").write_text(
            json.dumps({"plugins": [{"version": "6.6.6"}]}))
        (parent / "engine").mkdir()
        expect("VELDO-0009 AC3: the version is also found in the templates' PARENT, which is how THIS "
               "repository is laid out - templates in engine/ with the manifest above it. Without "
               "this leg the veldo home repository itself would produce no stamp",
               ISC9._template_version(parent / "engine") == "6.6.6")


_is_block("AC3", _is_ac3)


# ---------------------------------------------------------------------------------------
# AC4. THE COMPARISON AN ADOPTER CANNOT MAKE IS REPORTED AS SUCH.
#
# FALSIFIED BY: report no drift when this tree declares no current version, and the row below must
# go red.
# ---------------------------------------------------------------------------------------


def _is_ac4():
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        _is_install(base)
        installed = json.loads((base / ISC9.STAMP).read_text())["version"]

        no_current = VV9.drift(base)
        expect("VELDO-0009 AC4: a scaffolded repository - stamped, and with NO marketplace manifest "
               "because it is not a marketplace - reports VERSION_NOTHING_TO_COMPARE. Reporting 'no "
               "drift' would clear an install nobody measured; reporting 'drifted' would accuse every "
               "adopter in existence. The comparison cannot be made from inside that tree",
               no_current["cause"] == VV9.CAUSE_NO_CURRENT
               and no_current["installed"] == installed
               and no_current["current"] is None
               and "not a marketplace" in no_current["detail"])

        same = VV9.drift(base, current=installed)
        expect("VELDO-0009 AC4 NEGATIVE CONTROL: with the current version SUPPLIED and matching, the "
               "SAME tree reports no drift at all - so the refusal above is a measurement of what was "
               "available rather than the detector's only answer",
               same["cause"] is None and same["installed"] == same["current"] == installed)

        moved = VV9.drift(base, current="99.0.0")
        expect("VELDO-0009 AC4: with a NEWER version available the same tree reports "
               "VERSION_SUBSTRATE_DRIFT naming BOTH versions, because a drift is actionable only if "
               "you know which way it went",
               moved["cause"] == VV9.CAUSE_DRIFT
               and moved["installed"] == installed and moved["current"] == "99.0.0"
               and installed in moved["detail"] and "99.0.0" in moved["detail"])

    live = VV9.drift(ROOT)
    expect("VELDO-0009 AC4 OVER THIS REPOSITORY: it reports UNSTAMPED, which is correct and worth "
           "asserting - the veldo home repository was never scaffolded, so it has nothing to be "
           "stamped from. Reported rather than pinned: if it ever IS stamped this row reds and the "
           "answer changes honestly",
           live["cause"] == VV9.UNSTAMPED and live["installed"] is None
           and "unknown rather than current" in live["detail"])


_is_block("AC4", _is_ac4)


# ---------------------------------------------------------------------------------------
# AC5. AN UNSTAMPED TREE AND A CORRUPT STAMP ARE DIFFERENT FACTS.
#
# FALSIFIED BY: return the version without checking the schema, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _is_ac5():
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        (base / ".veldo").mkdir(parents=True)
        (base / VV9.STAMP).write_text(json.dumps({"version": "1.2.3"}))
        v, cause, detail = VV9.installed_version(base)
        expect("VELDO-0009 AC5: a JSON file at the stamp path that is NOT a veldo.installed/v1 record "
               "is VERSION_STAMP_UNREADABLE - not UNSTAMPED and not a version. Something wrote there "
               "and the fix is to look at it, where an unstamped tree needs nothing looked at",
               v is None and cause == VV9.CAUSE_STAMP_UNREADABLE
               and VV9.STAMP_SCHEMA in detail)

    # AC5 CLAIMS A TOTAL PROPERTY AND THE ROWS ABOVE COVERED ONE SHAPE OF IT. Ledger finding 67, from
    # VELDO-0009 F2: the criterion says "a file at the stamp path that PARSES but is not a
    # veldo.installed/v1 record" is VERSION_STAMP_UNREADABLE, and for every JSON that is not an OBJECT
    # the reader raised AttributeError instead - out of installed_version, out of drift(), and out of
    # the --drift CLI. The row above uses a dict, which is the one non-record shape that never crashed.
    # All FOUR non-object shapes are exercised here because "parses but is not a record" is the whole
    # claim, and a total property tested on one member is a claim about one member.
    for _v9_body in ("[]", "null", "5", '"veldo.installed/v1"'):
        with tempfile.TemporaryDirectory() as _v9_d:
            _v9_base = Path(_v9_d)
            (_v9_base / ".veldo").mkdir(parents=True)
            (_v9_base / VV9.STAMP).write_text(_v9_body)
            # THE READ IS CAPTURED so a RAISE reds THIS row rather than the block's. Measured while
            # writing it: with the guard removed the raise escaped, the block wrapper reddened its own
            # row, and six rows below simply vanished from the run - so the evidence was "some row went
            # red" plus a shorter run, which is the shape a mutation that DELETES coverage produces.
            try:
                _v9_v, _v9_cause, _v9_detail = VV9.installed_version(_v9_base)
            except Exception as _v9_e:               # noqa: BLE001 - the raise IS the measurement
                _v9_v, _v9_cause, _v9_detail = "raised", type(_v9_e).__name__, ""
            expect("VELDO-0009 AC5: a stamp that PARSES as JSON without being an object (%s) is "
                   "VERSION_STAMP_UNREADABLE with the type named, rather than an AttributeError out of "
                   "the reader. A traceback from a read model makes a run that COULD NOT LOOK "
                   "indistinguishable from one that found nothing" % _v9_body,
                   _v9_v is None and _v9_cause == VV9.CAUSE_STAMP_UNREADABLE
                   and type(json.loads(_v9_body)).__name__ in (_v9_detail or ""))

    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        (base / ".veldo").mkdir(parents=True)
        (base / VV9.STAMP).write_text("{not json")
        _v2, cause2, _ = VV9.installed_version(base)
        expect("VELDO-0009 AC5: an unparseable stamp is the same named cause, so a corrupted record "
               "never reads as a missing one",
               cause2 == VV9.CAUSE_STAMP_UNREADABLE)

    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        _v3, cause3, detail3 = VV9.installed_version(base)
        expect("VELDO-0009 AC5 NEGATIVE CONTROL: a tree with NO stamp at all is UNSTAMPED with its own "
               "reason, distinct from the corrupt cases above, so the three states never collapse",
               cause3 == VV9.UNSTAMPED and "set up by hand" in detail3)

    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        _is_install(base)
        v4, cause4, _ = VV9.installed_version(base)
        expect("VELDO-0009 AC5: a REAL install reads back its own stamp, so the refusals above "
               "discriminate rather than being the reader's only behaviour",
               cause4 is None and v4 == json.loads((base / ISC9.STAMP).read_text())["version"])


_is_block("AC5", _is_ac5)
