"""VELDO-0010: evidence names the version that produced it.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, which always
runs, so its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 27_veldo_0010_evidence_provenance

WHAT IS UNDER TEST. The provenance half of .veldo/version.py, plus TWO CLAIMS ABOUT THE REST OF THE
TREE that this item rests on: that the proof contract does not require the field, and that BOTH
GATES STAMP the producing version into the record they write.

THE GATE HALF IS MEASURED BY RUNNING THE GATE, never by scanning its source. The first version of
AC5 was refuted by independent review for exactly that: both of its rows were substring scans over
scripts/verify.sh's text, so deleting the field from the printf in both gates and from
run_scope.verify_stamp_payload, and leaving one comment reading `# TODO(VELDO-0010): the record still
owes a "veldo_version": field`, held this suite at 44 passed 0 failed and the whole repository at
4530 passed 0 failed while the record the gate writes lost the field. A substring scan used to prove
a PRESENCE is the same defect as one used to prove an ABSENCE. So each gate is now RUN in a throwaway
tree and the .veldo/last_verify it produced is PARSED.

THE LIVE ROWS ASSERT A PARTITION, NEVER A COUNT. Nothing here pins 143 or 155: a row that did would
redden the next time anybody records a proof, which is the live-state defect this repository has been
bitten by five times. What is asserted is that the buckets sum to the total, whatever the total is.

EVERY CRITERION'S BLOCK IS WRAPPED, AND SO IS THE LIVE READ ITSELF, so a raise reds a NAMED row
instead of shortening the run. The live read was at module level until review measured what that
costs: one proof manifest that parses as JSON but is not an object aborted the entire selftest with a
traceback rather than reddening one row.
"""
import shutil as _vp_shutil
import subprocess as _vp_subprocess

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


def _vp_report(bundles, dirs_without_manifest=()):
    with tempfile.TemporaryDirectory() as d:
        for spec, m in bundles:
            _vp_bundle(d, spec, m)
        for spec in dirs_without_manifest:
            (Path(d) / "proof" / spec).mkdir(parents=True, exist_ok=True)
        rep = VP.provenance_report(Path(d))
        return rep, VP.provenance_lines(rep)


_VP_LIVE = None


def _vp_read_live():
    global _VP_LIVE
    _VP_LIVE = VP.provenance_report(ROOT)


# A WRAPPED ROW RATHER THAN A MODULE-LEVEL CALL. Measured by independent review: with this read at
# module level, a single proof manifest that parses as JSON but is not an object raised out of the
# reader and aborted the whole selftest with a traceback, producing no verdict line at all. The read
# is now a row of its own, and the reader itself no longer raises on any unreadable manifest.
_vp_block("LIVE CORPUS READ", _vp_read_live)


# ---------------------------------------------------------------------------------------
# AC1. THE FIELD IS OPTIONAL BY CONSTRUCTION, AND THE MIGRATION IS THE ITEM.
#
# FALSIFIED BY: add the field to PROOF_REQ, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _vp_ac1():
    expect("VELDO-0010 AC1: the producing version is ABSENT from the proof contract's required keys, "
           "so every one of this repository's existing bundles validates unchanged. MEASURED at this "
           "run: %d proof directories, %d carrying a manifest, %d of those naming a producing version "
           "and %d predating the field - and requiring the field would have reddened every one of the "
           "latter on the day it landed, the lesson VELDO-0001 wrote down and this item obeys"
           % (_VP_LIVE["directories"], _VP_LIVE["bundles"], len(_VP_LIVE["versioned"]),
              len(_VP_LIVE["unversioned"])),
           VP.PROOF_VERSION_FIELD not in V.PROOF_REQ and _VP_LIVE["bundles"] > 100)
    expect("VELDO-0010 AC1: the real corpus validates - run_all over this repository returns zero "
           "errors with the field required nowhere, which is the migration property stated as a "
           "measurement rather than a promise",
           V.run_all() == 0)


_vp_block("AC1", _vp_ac1)


# ---------------------------------------------------------------------------------------
# AC2. NOTHING IS INFERRED FOR A BUNDLE THAT DOES NOT SAY.
#
# FALSIFIED BY: fall back to the tree's current version, and the rows below must go red.
# ---------------------------------------------------------------------------------------


def _vp_attribution_read_back(rep, base):
    """(attributed_wrong, unversioned_that_do_declare) re-read FROM DISK.

    The reader's own buckets are not evidence that the reader did not infer, which is what made the
    old real-corpus row vacuous: it asked whether a bundle was in two buckets at once, and the
    reader's control flow guarantees it is not. So this reopens every manifest the report filed under
    a version and compares the version IN THE FILE with the version it was filed under, and reopens
    every manifest the report called UNVERSIONED and requires the field to be genuinely absent. Two
    directions, because an inference shows up either as an attribution the file does not support or
    as an unversioned bundle that would have supported one."""
    wrong, declaring = [], []
    for v in rep["by_version"]:
        for rel in rep["by_version"][v]:
            try:
                data = json.loads((Path(base) / rel).read_text())
            except (OSError, ValueError):
                wrong.append(rel)
                continue
            if not isinstance(data, dict) or data.get(VP.PROOF_VERSION_FIELD) != v:
                wrong.append(rel)
    for rel in rep["unversioned"]:
        try:
            data = json.loads((Path(base) / rel).read_text())
        except (OSError, ValueError):
            declaring.append(rel)
            continue
        if isinstance(data, dict) and VP.PROOF_VERSION_FIELD in data:
            declaring.append(rel)
    return wrong, declaring


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

    _vp_wrong, _vp_declaring = _vp_attribution_read_back(_VP_LIVE, ROOT)
    expect("VELDO-0010 AC2 OVER THE REAL CORPUS: every version this reader attributes to a bundle is "
           "READ BACK OUT OF THAT BUNDLE'S OWN FILE, and every bundle it calls UNVERSIONED is "
           "confirmed from the file to declare nothing - so no piece of this repository's evidence is "
           "attributed to a version the evidence itself does not claim. Reported rather than pinned: "
           "no count and no emptiness of the live corpus is asserted, only that the attribution and "
           "the files agree, so bundles that start carrying the field keep this row green. Wrong "
           "attributions: %d; unversioned bundles that do declare a version: %d"
           % (len(_vp_wrong), len(_vp_declaring)),
           _vp_wrong == [] and _vp_declaring == [] and _VP_LIVE["bundles"] > 100)


_vp_block("AC2", _vp_ac2)


# ---------------------------------------------------------------------------------------
# AC3. A PRESENT FIELD IS CHECKED FOR SHAPE AND NEVER FOR EQUALITY.
#
# FALSIFIED BY: accept any string as a version, and the rows below must go red.
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

    rep2, _ = _vp_report([("SPEC-0004", {"schema": "veldo.proof/v1", "spec_id": "SPEC-0004",
                                         VP.PROOF_VERSION_FIELD: "1.0.0"})])
    expect("VELDO-0010 AC3: a version OLDER than the tree's current one is ACCEPTED and reported "
           "under itself, NEVER checked for equality. A bundle produced by an older version "
           "legitimately carries an older version - that is the entire purpose of recording it, and a "
           "check demanding agreement would make the field useless the first time it was true",
           [b["version"] for b in rep2["versioned"]] == ["1.0.0"]
           and rep2["malformed"] == []
           and VP.version(ROOT)[0] != "1.0.0")
    expect("VELDO-0010 AC3: an UNPARSEABLE manifest is malformed too, so a corrupt bundle never reads "
           "as one that simply predates the field",
           _vp_report([("SPEC-0005", "{not json")])[0]["malformed"])

    for shape in ("[]", '"3.10.1"', "17", "null"):
        rep3, lines3 = _vp_report([("SPEC-0006", shape)])
        expect("VELDO-0010 AC3: a manifest whose body is %s - it PARSES as JSON but is not an object "
               "- is reported MALFORMED with the bundle named, and the reader RETURNS rather than "
               "raising. Found by independent review: the shape check answered 'no problem' for a "
               "non-object and the caller then called .get on it, so one such file raised "
               "AttributeError out of the reader, and because the live read ran at module level that "
               "aborted the whole selftest with a traceback instead of reddening one row" % shape,
               [m["bundle"] for m in rep3["malformed"]] == ["proof/SPEC-0006/manifest.json"]
               and rep3["unversioned"] == [] and rep3["versioned"] == []
               and any("MALFORMED" in ln for ln in lines3))


_vp_block("AC3", _vp_ac3)


# ---------------------------------------------------------------------------------------
# AC4. THE COUNTS PARTITION THE BUNDLES EXACTLY.
#
# FALSIFIED BY: drop the unversioned count, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _vp_ac4():
    expect("VELDO-0010 AC4: over this repository's REAL corpus the buckets PARTITION the manifests - "
           "versioned plus unversioned plus malformed equals the number of bundles carrying one (%d) "
           "- so a reader can tell how much of the evidence corpus the answer covers. A report "
           "quoting only the versioned count would be a coverage figure without the weakness that "
           "produced it" % _VP_LIVE["bundles"],
           len(_VP_LIVE["versioned"]) + len(_VP_LIVE["unversioned"]) + len(_VP_LIVE["malformed"])
           == _VP_LIVE["bundles"])

    expect("VELDO-0010 AC4: AND THE DENOMINATOR ACCOUNTS FOR EVERY DIRECTORY UNDER proof/, which is "
           "the hole independent review measured: the reader globbed manifests and called the total "
           "'bundle(s)', so proof directories holding no manifest.json at all sat outside every "
           "bucket and a reader could not tell they had been skipped. Manifests found plus "
           "directories NAMED as carrying none equals directories present (%d + %d = %d), so a "
           "skipped bundle is named rather than invisible"
           % (_VP_LIVE["bundles"], len(_VP_LIVE["no_manifest"]), _VP_LIVE["directories"]),
           _VP_LIVE["bundles"] + len(_VP_LIVE["no_manifest"]) == _VP_LIVE["directories"]
           and _VP_LIVE["directories"] > 100)

    rep, lines = _vp_report([
        ("SPEC-A", {"schema": "veldo.proof/v1", "spec_id": "SPEC-A"}),
        ("SPEC-B", {"schema": "veldo.proof/v1", "spec_id": "SPEC-B",
                    VP.PROOF_VERSION_FIELD: "4.0.0"}),
        ("SPEC-C", {"schema": "veldo.proof/v1", "spec_id": "SPEC-C",
                    VP.PROOF_VERSION_FIELD: "latest"})], dirs_without_manifest=("SPEC-D",))
    expect("VELDO-0010 AC4: a mixed corpus partitions the same way - one of each, plus one directory "
           "with no manifest NAMED as such - so the partition holds over a set that actually "
           "populates every bucket rather than only over one where three are empty",
           (len(rep["versioned"]), len(rep["unversioned"]), len(rep["malformed"])) == (1, 1, 1)
           and rep["bundles"] == 3 and rep["directories"] == 4
           and rep["no_manifest"] == ["proof/SPEC-D"]
           and any("NO MANIFEST" in ln for ln in lines))
    expect("VELDO-0010 AC4: the report carries ONE KEY SHAPE, and an absent proof root yields the "
           "same keys with zero bundles rather than a missing key",
           sorted(rep) == sorted(VP.PROVENANCE_KEYS)
           and sorted(VP.provenance_report(Path(tempfile.gettempdir()) / "no-such-veldo-proof-tree"))
           == sorted(VP.PROVENANCE_KEYS))


_vp_block("AC4", _vp_ac4)


# ---------------------------------------------------------------------------------------
# AC5. THE GATE STAMPS THE PRODUCING VERSION, IN BOTH GATES, AND NULL RATHER THAN A GUESS.
#
# FALSIFIED BY: remove the version field from the record the gate stamps in scripts/verify.sh, or
# leave a bare mention of a producing version without writing the key, and the rows below must go
# red.
#
# ASSERTED OVER THE RECORD THE GATE WROTE, NOT OVER THE GATE'S SOURCE TEXT. Both gates are protected
# paths, so this criterion cannot be met by editing them: it is met by RUNNING them. Each gate is
# copied into a throwaway tree beside .veldo/version.py and executed, and the .veldo/last_verify it
# produced is parsed. The run is RED in that tree because no check script is there to pass, which is
# deliberate - the stamp is written on both the green and the red path, and what is under test is its
# CONTENT rather than the verdict.
# ---------------------------------------------------------------------------------------

_VP_GATES = ("scripts/verify.sh", "engine/scripts/verify.sh")
# A version no tree here declares, so a gate that stamped its own repository's version instead of the
# one it read would fail the negative control rather than pass it by coincidence.
_VP_STUB_VERSION = "9.9.9"

_vp_rs_spec = importlib.util.spec_from_file_location(
    "vp_run_scope", ROOT / "scripts" / "run_scope.py")
_VP_RS = importlib.util.module_from_spec(_vp_rs_spec)
_vp_rs_spec.loader.exec_module(_VP_RS)


def _vp_run_gate(gate_rel, declare_version):
    """RUN one gate in a throwaway tree; return (parsed record, raw text) for what it stamped.

    The tree holds the gate and .veldo/version.py and, when declare_version is given, the canonical
    declaration the version reader reads. That is what drives the SAME script down both branches of
    the one property AC5 states: a version that CAN be read is stamped, and one that cannot is null.
    Nothing is stubbed on the path under test - the version derivation and the printf are the shipped
    ones, executed."""
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        (base / "scripts").mkdir(parents=True)
        (base / ".veldo").mkdir(parents=True)
        _vp_shutil.copy2(ROOT / gate_rel, base / "scripts" / "verify.sh")
        _vp_shutil.copy2(ROOT / ".veldo" / "version.py", base / ".veldo" / "version.py")
        if declare_version is not None:
            (base / ".claude-plugin").mkdir(parents=True)
            (base / ".claude-plugin" / "marketplace.json").write_text(json.dumps(
                {"plugins": [{"name": "veldo", "version": declare_version}]}))
        _vp_subprocess.run(["bash", "scripts/verify.sh"], cwd=str(base),
                           capture_output=True, text=True, timeout=300)
        stamp = base / ".veldo" / "last_verify"
        if not stamp.is_file():
            return None, None
        raw = stamp.read_text()
        try:
            return json.loads(raw), raw
        except ValueError:
            return None, raw


def _vp_ac5():
    # FOUR RUNS: both gates, each with the version readable and unreadable. Computed once here so
    # every row below reads the same measured records.
    read = dict((g, _vp_run_gate(g, _VP_STUB_VERSION)[0]) for g in _VP_GATES)
    unread = dict((g, _vp_run_gate(g, None)[0]) for g in _VP_GATES)
    payload = _VP_RS.full_scope(_VP_RS.load_manifest()).verify_stamp_payload(
        "deadbeef", "green", "2026-01-01T00:00:00Z", 4, 18, _VP_STUB_VERSION)

    expect("VELDO-0010 AC5: the gate WRITES the producing version into the record it stamps, and this "
           "is MEASURED BY RUNNING IT - each gate executed in a throwaway tree and the "
           ".veldo/last_verify it produced parsed, with the key required present on BOTH paths, a "
           "readable version and an unreadable one. Both this repository's gate and the SHIPPED "
           "template, because an adopter's gate output should name its version too. The row this "
           "replaces was a substring scan of the gate's source, and review satisfied it with a "
           "comment while the record carried no field at all",
           all(rec is not None and VP.PROOF_VERSION_FIELD in rec
               for rec in list(read.values()) + list(unread.values())))

    for _vp_g in _VP_GATES:
        _vp_text = (ROOT / _vp_g).read_text()
        _vp_mentions = VP.PROOF_VERSION_FIELD in _vp_text.lower()
        _vp_stamps = read[_vp_g] is not None and VP.PROOF_VERSION_FIELD in read[_vp_g]
        expect("VELDO-0010 AC5: in %s, MENTIONING a producing version without WRITING the key into "
               "the record is RED. THE TWO FACTS ARE INDEPENDENT BY CONSTRUCTION now: one reads the "
               "gate's TEXT case-insensitively, so a comment, a marker and the shell variable all "
               "count as a mention, and the other reads THE FILE THE GATE WROTE. So a gate that "
               "derives a producing version and stamps no field - verbatim the half-done registration "
               "PLAN-0018 ledger finding 45 names - reddens here, which the old pair could not do "
               "because both of its facts were scans of the same text" % _vp_g,
               _vp_mentions == _vp_stamps)

    for _vp_g in _VP_GATES:
        _vp_rec = unread[_vp_g]
        expect("VELDO-0010 AC5: %s stamps NULL rather than a guessed string when the version cannot "
               "be read, MEASURED by running it in a tree that carries no canonical declaration and "
               "reading the value out of the record it wrote. This is the defect that measurement "
               "caught: version.py prints its refusal on STDOUT for every cause it models, so a gate "
               "taking the first word of that stdout stamped the word veldo as a version - a "
               "fabricated identity in the one record where it would be believed, and VELDO-0008's "
               "rule is that an installation reporting a number it invented sends the bug report to "
               "the wrong tree. Value stamped: %r"
               % (_vp_g, (_vp_rec or {}).get(VP.PROOF_VERSION_FIELD)),
               _vp_rec is not None and VP.PROOF_VERSION_FIELD in _vp_rec
               and _vp_rec[VP.PROOF_VERSION_FIELD] is None)

    expect("VELDO-0010 AC5 NEGATIVE CONTROL: the SAME gates, run in a tree that DOES declare a "
           "version, stamp THAT version - %r, version-shaped by this module's own rule - so the null "
           "above is a measurement of a version that could not be read rather than the only value "
           "these gates know how to write. A gate hardcoding null would satisfy every row above and "
           "fail this one" % _VP_STUB_VERSION,
           all(rec is not None and rec.get(VP.PROOF_VERSION_FIELD) == _VP_STUB_VERSION
               and VP._version_shaped(rec.get(VP.PROOF_VERSION_FIELD)) for rec in read.values()))

    expect("VELDO-0010 AC5: the record the gate ACTUALLY WROTE carries the commit and the status "
           "beside the version, so the three facts a reader needs about a gate run are in one place - "
           "and its key set EQUALS the payload scripts/run_scope.py declares for a Python-side stamp "
           "writer. An equality between the record produced and the payload declared, rather than two "
           "hand-typed key lists, because two enumerations of one set diverge",
           all(rec is not None and sorted(rec) == sorted(payload)
               and isinstance(rec.get("commit"), str) and rec.get("status") in ("green", "red")
               for rec in list(read.values()) + list(unread.values())))


_vp_block("AC5", _vp_ac5)
