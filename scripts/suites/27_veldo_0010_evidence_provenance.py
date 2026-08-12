"""VELDO-0010: evidence names the version that produced it.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, which always
runs, so its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 27_veldo_0010_evidence_provenance

WHAT IS UNDER TEST. The provenance half of .veldo/version.py, plus TWO CLAIMS ABOUT THE REST OF THE
TREE that this item rests on: that the proof contract does not require the field, and that the gate
carries no version stamp yet.

THE LIVE ROWS ASSERT A PARTITION, NEVER A COUNT. Nothing here pins 143: a row that did would redden
the next time anybody records a proof, which is the live-state defect this repository has been bitten
by five times. What is asserted is that the buckets sum to the total, whatever the total is.

EVERY CRITERION'S BLOCK IS WRAPPED, so a raise reds a NAMED row instead of shortening the run.
"""
VP = V._VC._organ("version", ROOT / ".veldo" / "version.py")


def _vp_block(label, fn):
    try:
        fn()
    except Exception as _vp_e:                   # noqa: BLE001 - a raise must RED a row, never skip
        expect("VELDO-0010 %s: the block ran to completion rather than raising (%r)"
               % (label, _vp_e), False)


def _vp_bundle(d, spec, manifest):
    p = Path(d) / "proof" / spec
    p.mkdir(parents=True, exist_ok=True)
    (p / "manifest.json").write_text(manifest if isinstance(manifest, str)
                                     else json.dumps(manifest))


def _vp_report(bundles):
    with tempfile.TemporaryDirectory() as d:
        for spec, m in bundles:
            _vp_bundle(d, spec, m)
        rep = VP.provenance_report(Path(d))
        return rep, VP.provenance_lines(rep)


_VP_LIVE = VP.provenance_report(ROOT)


# ---------------------------------------------------------------------------------------
# AC1. THE FIELD IS OPTIONAL BY CONSTRUCTION, AND THE MIGRATION IS THE ITEM.
#
# FALSIFIED BY: add the field to PROOF_REQ, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _vp_ac1():
    expect("VELDO-0010 AC1: the producing version is ABSENT from the proof contract's required keys, "
           "so every one of this repository's %d existing bundles validates unchanged. MEASURED: none "
           "of them carries the field, and requiring it would have reddened a working repository on "
           "the day it landed - the lesson VELDO-0001 wrote down and this item obeys"
           % _VP_LIVE["bundles"],
           VP.PROOF_VERSION_FIELD not in V.PROOF_REQ and _VP_LIVE["bundles"] > 100)
    expect("VELDO-0010 AC1: the real corpus validates - run_all over this repository returns zero "
           "errors with the field nowhere in it, which is the migration property stated as a "
           "measurement rather than a promise",
           V.run_all() == 0)


_vp_block("AC1", _vp_ac1)


# ---------------------------------------------------------------------------------------
# AC2. NOTHING IS INFERRED FOR A BUNDLE THAT DOES NOT SAY.
#
# FALSIFIED BY: fall back to the tree's current version, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _vp_ac2():
    rep, lines = _vp_report([("SPEC-0001", {"schema": "veldo.proof/v1", "spec_id": "SPEC-0001"})])
    expect("VELDO-0010 AC2: a bundle with NO field is UNVERSIONED, appears under NO version, and the "
           "report says in words that nothing was inferred. Reporting today's version for evidence "
           "written by an older one would state exactly the fact this field exists to establish - "
           "evidence produced when the checks were weaker would become indistinguishable from "
           "evidence produced now",
           rep["unversioned"] == ["proof/SPEC-0001/manifest.json"]
           and rep["versioned"] == [] and rep["by_version"] == {}
           and any("NOTHING infers a version" in ln for ln in lines))

    rep2, _ = _vp_report([("SPEC-0002", {"schema": "veldo.proof/v1", "spec_id": "SPEC-0002",
                                         VP.PROOF_VERSION_FIELD: "3.10.1"})])
    expect("VELDO-0010 AC2 NEGATIVE CONTROL: a bundle that DOES name its version appears under that "
           "version and not among the unversioned, so UNVERSIONED is a measurement of the field's "
           "absence rather than the reader's only answer",
           [b["version"] for b in rep2["versioned"]] == ["3.10.1"]
           and rep2["unversioned"] == []
           and list(rep2["by_version"]) == ["3.10.1"])

    expect("VELDO-0010 AC2 OVER THE REAL CORPUS: every bundle in this repository is UNVERSIONED and "
           "by_version is EMPTY - so the reader is not quietly attributing 143 bundles to today's "
           "version. Reported rather than pinned: as bundles start carrying the field this row keeps "
           "holding, because it asserts that the unattributed ones stay unattributed",
           _VP_LIVE["by_version"] == {} or all(
               b not in _VP_LIVE["unversioned"] for v in _VP_LIVE["by_version"]
               for b in _VP_LIVE["by_version"][v]))


_vp_block("AC2", _vp_ac2)


# ---------------------------------------------------------------------------------------
# AC3. A PRESENT FIELD IS CHECKED FOR SHAPE AND NEVER FOR EQUALITY.
#
# FALSIFIED BY: accept any string as a version, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _vp_ac3():
    for bad in ("latest", "", "v", "three.ten"):
        rep, lines = _vp_report([("SPEC-0003", {"schema": "veldo.proof/v1", "spec_id": "SPEC-0003",
                                                VP.PROOF_VERSION_FIELD: bad})])
        expect("VELDO-0010 AC3: a bundle declaring the field as %r is MALFORMED with the bundle "
               "named, because a present-but-broken field is somebody's mistake and naming it is how "
               "they fix it - distinct from an absent field, which is a legitimate state" % bad,
               [m["bundle"] for m in rep["malformed"]] == ["proof/SPEC-0003/manifest.json"]
               and rep["unversioned"] == [] and rep["versioned"] == []
               and any("MALFORMED" in ln for ln in lines))

    old = VP.provenance_report
    rep2, _ = _vp_report([("SPEC-0004", {"schema": "veldo.proof/v1", "spec_id": "SPEC-0004",
                                         VP.PROOF_VERSION_FIELD: "1.0.0"})])
    expect("VELDO-0010 AC3: a version OLDER than the tree's current one is ACCEPTED and reported "
           "under itself, NEVER checked for equality. A bundle produced by an older version "
           "legitimately carries an older version - that is the entire purpose of recording it, and a "
           "check demanding agreement would make the field useless the first time it was true",
           [b["version"] for b in rep2["versioned"]] == ["1.0.0"]
           and rep2["malformed"] == []
           and VP.version(ROOT)[0] != "1.0.0" and old is VP.provenance_report)
    expect("VELDO-0010 AC3: an UNPARSEABLE manifest is malformed too, so a corrupt bundle never reads "
           "as one that simply predates the field",
           _vp_report([("SPEC-0005", "{not json")])[0]["malformed"])


_vp_block("AC3", _vp_ac3)


# ---------------------------------------------------------------------------------------
# AC4. THE COUNTS PARTITION THE BUNDLES EXACTLY.
#
# FALSIFIED BY: drop the unversioned count, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _vp_ac4():
    expect("VELDO-0010 AC4: over this repository's REAL corpus the buckets PARTITION the bundles - "
           "versioned plus unversioned plus malformed equals the total (%d) - so a reader can tell how "
           "much of the evidence corpus the answer covers. A report quoting only the versioned count "
           "would be a coverage figure without the weakness that produced it"
           % _VP_LIVE["bundles"],
           len(_VP_LIVE["versioned"]) + len(_VP_LIVE["unversioned"]) + len(_VP_LIVE["malformed"])
           == _VP_LIVE["bundles"])

    rep, _ = _vp_report([
        ("SPEC-A", {"schema": "veldo.proof/v1", "spec_id": "SPEC-A"}),
        ("SPEC-B", {"schema": "veldo.proof/v1", "spec_id": "SPEC-B",
                    VP.PROOF_VERSION_FIELD: "4.0.0"}),
        ("SPEC-C", {"schema": "veldo.proof/v1", "spec_id": "SPEC-C",
                    VP.PROOF_VERSION_FIELD: "latest"})])
    expect("VELDO-0010 AC4: a mixed corpus partitions the same way - one of each - so the partition "
           "holds over a set that actually populates every bucket rather than only over one where two "
           "are empty",
           (len(rep["versioned"]), len(rep["unversioned"]), len(rep["malformed"])) == (1, 1, 1)
           and rep["bundles"] == 3)
    expect("VELDO-0010 AC4: the report carries ONE KEY SHAPE, and an absent proof root yields the "
           "same keys with zero bundles rather than a missing key",
           sorted(rep) == sorted(VP.PROVENANCE_KEYS)
           and sorted(VP.provenance_report(Path(tempfile.gettempdir()) / "no-such-veldo-proof-tree"))
           == sorted(VP.PROVENANCE_KEYS))


_vp_block("AC4", _vp_ac4)


# ---------------------------------------------------------------------------------------
# AC5. THE GATE-OUTPUT HALF IS SPECIFIED AND NOT WRITTEN, AND THIS SAYS SO.
#
# FALSIFIED BY: declare a version slot in scripts/verify.sh, and the row below must go red.
# ---------------------------------------------------------------------------------------

_VP_SPEC = ROOT / "specs" / "VELDO-0010-evidence-names-the-version-that-produced-it.md"
# THE DECLARATION, not the prose. An earlier version of the row below searched the whole spec file for
# the gate's path and failed, because the spec legitimately NAMES the gate while declaring it is not
# touching it - a mention is not a footprint, the same distinction VELDO-0003 and VELDO-0005 landed.
# So the assertion reads the one line that states the claim: this item declares NO protected path.
_VP_DECLARES_NO_PROTECTED = "protected_paths: []" in _VP_SPEC.read_text()
_VP_GATE = (ROOT / "scripts" / "verify.sh").read_text()
# TWO FACTS, NOT ONE, and separating them is what gives this criterion teeth. FOUND BY DRIVING: with a
# single "does the gate mention a version" flag, BOTH branches of the posture were satisfiable, so
# adding a bare marker to the gate reddened nothing - the posture pattern's own vacuous shape.
_VP_MENTIONS = "veldo_version" in _VP_GATE          # the gate refers to a producing version at all
_VP_STAMPS = '\\"veldo_version\\":' in _VP_GATE or '"veldo_version":' in _VP_GATE  # it WRITES the key
_VP_STAMPED = _VP_STAMPS


def _vp_ac5():
    # UNCONDITIONAL, for the reason VELDO-0007's twin records: the reporting branch existed only while
    # the protected-path edit waited for approval, Dmitry approved it on 2026-08-12, and a posture
    # derived from the live gate cannot catch its own removal - with the stamp gone, both branches
    # passed. Ledger finding 45.
    expect("VELDO-0010 AC5: the gate STAMPS the producing version into the record it writes, so every "
           "gate run says which version produced it. Both this repository's gate and the SHIPPED "
           "template carry it, because an adopter's gate output should name its version too",
           _VP_STAMPS
           and '"veldo_version":' in (ROOT / "engine/scripts/verify.sh").read_text())
    expect("VELDO-0010 AC5: MENTIONING a producing version without WRITING the key is red - a marker "
           "or a comment in the gate with no field in the record it stamps is a half-done "
           "registration, and this is the row that catches it",
           _VP_MENTIONS == _VP_STAMPS)
    expect("VELDO-0010 AC5: the stamp is NULL rather than a guessed string when the version cannot be "
           "read. A gate record is exactly where an invented version would be believed, and "
           "VELDO-0008's rule is that an installation reporting a number it invented sends a bug "
           "report to the wrong tree",
           "VERSION_JSON=null" in _VP_GATE
           and "VERSION_JSON=null" in (ROOT / "engine/scripts/verify.sh").read_text())
    expect("VELDO-0010 AC5: the record the gate stamps carries the commit and the status beside the "
           "version, so the three facts a reader needs about a gate run are in one place",
           "last_verify" in _VP_GATE and '"commit"' in _VP_GATE)


_vp_block("AC5", _vp_ac5)
