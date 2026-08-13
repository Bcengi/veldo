"""VELDO-0009: init stamps what it laid down, and the drift detector that gives the stamp a purpose.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, which always
runs, so its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 26_veldo_0009_install_stamp

WHAT IS UNDER TEST. .veldo/init_scaffold.py's stamp writer and .veldo/version.py's stamp reader and
drift detector. THE SCAFFOLDER IS RUN FOR REAL into temporary trees, because the property is what an
install produces and a fixture would test the fixture.

NO ROW PINS THIS TREE'S DRIFT ANSWER. AC4's live row used to assert that this repository reports
UNSTAMPED, so ONE run of the documented create-only scaffolder over the repository root - idempotent,
advertised as safe to re-run, writing a stamp that is not gitignored - reddened a named row for a
correct operation. What is asserted instead is that whatever state the tree is in, the answer this
organ gives about it is CONSISTENT WITH IT, and every one of the five answers is driven so the
property is not a detector nobody has run.

EVERY CRITERION'S BLOCK IS WRAPPED, so a raise reds a NAMED row instead of shortening the run.
"""
import shutil as _is_shutil
import sys as _is_sys
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
        got, stood = ISC9._write_stamp(base / "no-templates-here", base, created, skipped)
        expect("VELDO-0009 AC3: templates declaring NO version produce NO stamp at all - not one "
               "saying unknown, and not a placeholder. An unstamped install is an honest state a "
               "reader can act on; a stamp that guesses makes a drift detector confidently wrong",
               got is None and created == [] and not (base / ISC9.STAMP).exists())
        expect("VELDO-0009 AC3: AND THE STAND-DOWN IS RETURNED TO THE CALLER WITH ITS REASON, naming "
               "the shapes that were searched. Ledger finding 64: a stand-down recorded where nothing "
               "prints it is silence, and independent review measured what that cost - five of the "
               "seven supported packs declare no version at any shape searched, so their adopters got "
               "no record and no word of it. Reason: %r" % stood,
               isinstance(stood, str) and "no install record was laid" in stood
               and all(c in stood for c in ISC9._VERSION_CANDIDATES))

    for shape, rel in (("a composed Claude pack", ".claude-plugin/plugin.json"),
                       ("a composed pack with its manifest at the root", "plugin.json"),
                       ("a marketplace tree", ".claude-plugin/marketplace.json")):
        with tempfile.TemporaryDirectory() as d:
            t = Path(d) / "templates"
            p = t / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            entry = {"name": VV9.PLUGIN_NAME, "version": "5.5.5"}
            body = ({"plugins": [entry]} if rel.endswith("marketplace.json") else entry)
            p.write_text(json.dumps(body))
            expect("VELDO-0009 AC3: the version is found in %s. THREE REAL SHAPES are searched rather "
                   "than one assumed - assuming a single shape is precisely what made 1.0 "
                   "uninstallable" % shape,
                   ISC9._template_version(t) == "5.5.5")

    with tempfile.TemporaryDirectory() as d:
        parent = Path(d)
        (parent / ".claude-plugin").mkdir(parents=True)
        (parent / ".claude-plugin" / "marketplace.json").write_text(
            json.dumps({"plugins": [{"name": VV9.PLUGIN_NAME, "version": "6.6.6"}]}))
        (parent / "engine").mkdir()
        expect("VELDO-0009 AC3: the version is also found in the templates' PARENT, which is how THIS "
               "repository is laid out - templates in engine/ with the manifest above it. Without "
               "this leg the veldo home repository itself would produce no stamp",
               ISC9._template_version(parent / "engine") == "6.6.6")

    # WHAT THE STAMP RECORDS MUST BE VELDO'S VERSION, AND MUST BE A VERSION. Both holes were driven by
    # independent review and both made a drift detector confidently wrong, which is exactly what AC3's
    # "no stamp is better than a stamp that guesses" forbids.
    with tempfile.TemporaryDirectory() as d:
        parent = Path(d)
        (parent / ".claude-plugin").mkdir(parents=True)
        (parent / ".claude-plugin" / "marketplace.json").write_text(json.dumps({"plugins": [
            {"name": "other-plugin", "version": "9.9.9"},
            {"name": VV9.PLUGIN_NAME, "version": "3.10.1"}]}))
        (parent / "engine").mkdir()
        expect("VELDO-0009 AC3: with a CO-HOSTED plugin listed FIRST in the parent marketplace, the "
               "version stamped is the one the entry NAMED %r declares. The positional read answered "
               "9.9.9 - a version this install is not, a fact nobody declared about veldo - and the "
               "same defect was fixed in version.py while surviving here, because a stamp is written "
               "once and read months later by somebody with no way to check it" % VV9.PLUGIN_NAME,
               ISC9._template_version(parent / "engine") == "3.10.1")

    with tempfile.TemporaryDirectory() as d:
        parent = Path(d)
        (parent / ".claude-plugin").mkdir(parents=True)
        (parent / ".claude-plugin" / "marketplace.json").write_text(json.dumps(
            {"plugins": [{"name": "other-plugin", "version": "9.9.9"}]}))
        (parent / "engine").mkdir()
        expect("VELDO-0009 AC3 NEGATIVE CONTROL for the name match: a parent marketplace hosting ONLY "
               "somebody else's plugin yields NO version, so the match above discriminates rather than "
               "taking whatever it finds - and no stamp is the answer, not that plugin's number",
               ISC9._template_version(parent / "engine") is None)

    # AND THE STAND-DOWN IS PRINTED, DRIVEN THROUGH THE CLI AN ADOPTER RUNS. Returning the reason to a
    # caller that never prints it is ledger finding 64's first defect exactly, so the property is
    # measured where the adopter reads it: stdout. This reproduces the thin-pack case rather than
    # imitating it - the templates tree is a real copy of engine/ with no manifest above it, which is
    # byte-for-byte the shape aider, codex, copilot, cursor and opencode install from.
    with tempfile.TemporaryDirectory() as d:
        pack = Path(d) / "pack"
        _is_shutil.copytree(ROOT / "engine", pack)
        target = Path(d) / "target"
        target.mkdir()
        _is_sp.run(["git", "init", "-q", "."], cwd=str(target), capture_output=True)
        out = _is_sp.run([_is_sys.executable, str(pack / ".veldo" / "init_scaffold.py"), str(target)],
                         capture_output=True, text=True, timeout=300)
        expect("VELDO-0009 AC3: an install from a pack that declares NO version PRINTS the stand-down "
               "and still exits 0, so an adopter is TOLD the record was not laid instead of reading "
               "'substrate complete' and nothing. Five of the seven supported packs are in exactly this "
               "state, and the silence is what made their trees answer UNSTAMPED with a reason about an "
               "install nobody made. Exit %d, stdout tail: %r"
               % (out.returncode, out.stdout.strip().splitlines()[-2:]),
               out.returncode == 0
               and "no install record was laid" in out.stdout
               and "substrate complete" in out.stdout
               and not (target / ISC9.STAMP).exists())

    for label, declared in (("whitespace", "   "), ("a placeholder", "TBD"),
                            ("the EMPTY string", ""), ("a single integer", "1")):
        with tempfile.TemporaryDirectory() as d:
            t = Path(d) / "templates"
            t.mkdir(parents=True)
            (t / "plugin.json").write_text(json.dumps({"name": VV9.PLUGIN_NAME,
                                                       "version": declared}))
            tgt = Path(d) / "target"
            tgt.mkdir()
            created, skipped = [], []
            got2, stood2 = ISC9._write_stamp(t, tgt, created, skipped)
            expect("VELDO-0009 AC3: templates declaring %s (%r) produce NO stamp, because a string is "
                   "not a version. Driven by independent review: any non-empty string passed, so '   ' "
                   "became a stamp whose version was '   ', installed_version returned it as a VERSION "
                   "with no cause, and drift() reported VERSION_SUBSTRATE_DRIFT naming it against the "
                   "real number. The shape rule is the READER'S OWN, loaded rather than copied, because "
                   "two enumerations of one rule diverge" % (label, declared),
                   got2 is None and created == [] and not (tgt / ISC9.STAMP).exists()
                   and isinstance(stood2, str) and not VV9._version_shaped(declared))


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

        # THE PRESENT-BUT-BROKEN CANONICAL DECLARATION, which the folded cause used to describe with a
        # sentence that was false about it. Driven by independent review.
        (base / ".claude-plugin").mkdir(parents=True, exist_ok=True)
        (base / ".claude-plugin" / "marketplace.json").write_text("{not json")
        broken = VV9.drift(base)
        expect("VELDO-0009 AC4: with the canonical declaration PRESENT and UNREADABLE the cause is "
               "still VERSION_NOTHING_TO_COMPARE - the caller's next move is the same - but the REASON "
               "says the file is there and could not be read, and does NOT claim that an adopting "
               "repository is always in this state. That sentence was false about exactly the tree it "
               "described, which HAS a marketplace manifest and has a broken one, and it pointed at the "
               "wrong repair: supply a version, rather than fix the file you have",
               broken["cause"] == VV9.CAUSE_NO_CURRENT
               and "PRESENT and could not be read" in broken["detail"]
               and "always in this state" not in broken["detail"]
               and VV9.drift_contradictions(broken, base) == [])
        (base / ".claude-plugin" / "marketplace.json").unlink()

    # OVER THIS REPOSITORY: THE PROPERTY, NOT THE ANSWER. This row asserted that the live tree reports
    # UNSTAMPED, so ONE run of the documented create-only scaffolder - advertised as idempotent and safe
    # to re-run, writing a stamp that is not gitignored - reddened a named row for a correct,
    # non-destructive operation, and the red read as "the drift detector is broken" when the detector had
    # answered correctly. Independent review measured it: 42 passed, 1 failed after
    # `python3 .veldo/init_scaffold.py .`. Ledger finding 51's fix shape: assert the PROPERTY the pin
    # stood in for. Every one of the five answers is allowed here; only an answer that contradicts the
    # tree it describes is a finding, and that set is a defect set by construction.
    live = VV9.drift(ROOT)
    _is_wrong = VV9.drift_contradictions(live, ROOT)
    expect("VELDO-0009 AC4 OVER THIS REPOSITORY: whatever state this tree is in, the answer this organ "
           "gives about it is CONSISTENT WITH IT - the cause is one of the four declared causes or "
           "None, it carries a reason, and the values reported beside it match what is on disk. NOTHING "
           "IS PINNED: stamping this repository, unstamping it, corrupting the stamp or bumping the "
           "version each move it to a different allowed answer and none of them reds this row, while a "
           "detector that reported UNSTAMPED with a stamp present, or a drift that failed to name both "
           "versions, does. MEASURED at this run: cause %r, installed %r, current %r, contradictions %r"
           % (live["cause"], live["installed"], live["current"], _is_wrong),
           _is_wrong == []
           and (live["cause"] is None or live["cause"] in VV9.DRIFT_CAUSES))

    # AND THE CONSISTENCY CHECK HAS TEETH, over every one of the five answers plus a forced lie. Without
    # this the row above is a property nobody has driven, which is a detector whose reach is unknown.
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        (base / ".veldo").mkdir(parents=True)
        # EACH ANSWER IS JUDGED AT THE MOMENT IT WAS PRODUCED, because the judgement reads the tree and
        # the tree moves between states here. Measured while writing this: judging all five at the end
        # reported the UNSTAMPED answer as contradictory, which it was - of the LATER tree.
        _is_states = []

        def _is_state(name, out):
            _is_states.append((name, out, VV9.drift_contradictions(out, base)))

        _is_state("UNSTAMPED", VV9.drift(base))
        (base / VV9.STAMP).write_text("{not json")
        _is_state("VERSION_STAMP_UNREADABLE", VV9.drift(base))
        (base / VV9.STAMP).write_text(json.dumps({"schema": VV9.STAMP_SCHEMA, "version": "1.2.3"}))
        _is_state("VERSION_NOTHING_TO_COMPARE", VV9.drift(base))
        _is_state("VERSION_SUBSTRATE_DRIFT", VV9.drift(base, current="9.9.9"))
        _is_state("no drift", VV9.drift(base, current="1.2.3"))
        expect("VELDO-0009 AC4: ALL FIVE answers are internally consistent when produced over the tree "
               "they describe - %s - so the row above is a property that has been driven across every "
               "state rather than over the one state this repository happens to be in"
               % ", ".join("%s:%r" % (n, w) for n, _o, w in _is_states),
               all(w == [] for _n, _o, w in _is_states)
               and sorted(n for n, _o, _w in _is_states if n != "no drift")
               == sorted(VV9.DRIFT_CAUSES))

        _is_lie = dict(_is_states[0][1])          # the UNSTAMPED answer, now over a STAMPED tree
        _is_lie["cause"], _is_lie["installed"] = VV9.UNSTAMPED, "1.2.3"
        _is_forged = dict(_is_states[3][1])          # the DRIFT answer, with its reason replaced
        _is_forged["detail"] = "the substrate drifted"
        expect("VELDO-0009 AC4 NEGATIVE CONTROL, ADDITIVE: two ANSWERS ARE ADDED that contradict the "
               "tree - one reporting UNSTAMPED while naming an installed version and over a tree where "
               "the stamp exists, one reporting a drift whose reason names NEITHER version - and both "
               "are NAMED as contradictions. So the empty list above is a measurement rather than this "
               "function's only output. Named: %r / %r"
               % (VV9.drift_contradictions(_is_lie, base),
                  VV9.drift_contradictions(_is_forged, base)),
               len(VV9.drift_contradictions(_is_lie, base)) == 2
               and len(VV9.drift_contradictions(_is_forged, base)) == 2)


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
