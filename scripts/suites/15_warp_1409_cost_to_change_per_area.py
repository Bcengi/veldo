"""WARP-1409: cost-to-change per area, and the join that produced every number.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. It builds its own fixtures in a temporary tree and rebinds nothing
that a later fragment reads. Every name it uses is bound by shared.py (expect, ROOT, V, tmpfile,
json, tempfile, importlib, Path) or by itself, which is why its declared prerequisite closure in
scripts/suites/manifest.json is itself alone. The one name it needs and shared.py does not bind,
the re module, it imports under its own alias rather than rebinding `re` in a namespace every
later fragment shares.

Run it: `python3 scripts/selftest.py --suite 15_warp_1409_cost_to_change_per_area`.

WHAT IS OBSERVED HERE AND WHY IT IS PAIRED. The item's whole risk is a number attributed to an
area nobody put it in, so every positive assertion has a NEGATIVE CONTROL beside it that removes
exactly one input and requires the answer to CHANGE:

  the placement join is driven, and then the placement is removed and the same record must stop
  being placement-attributed - so basis is the declaration's doing and not a constant;
  the git-path fallback is driven, and then the paths are emptied and the same record must
  become UNATTRIBUTED rather than land anywhere - so the fallback cannot fabricate;
  the git_path LABEL is asserted inside the serialized report, and the placement-only report is
  asserted to carry NO such label - so the label is not always-on decoration;
  the unknown-cost None is asserted, and a record carrying real spend is asserted to produce
  real numbers - so None is the absence of data and not a hardcoded value;
  the stand-downs are asserted, and a populated corpus is asserted NOT to stand down - so the
  stand-down is not unconditional;
  the refusals are asserted BY MESSAGE for eight planted-bad shapes, and the well-formed corpus
  is asserted to raise nothing - so the validator is not simply always refusing.

AND THE WIRING IS DRIVEN, NOT ONLY THE PURE CORE. repo_report() produces every number the spec
publishes and every number a reader will quote, and for a while nothing called it: a review severed
each of its two joins in turn and this file stayed at 30 passed while the live map lost, in turn,
every git-path attribution and then every declared-placement attribution. It is now driven twice -
over an INJECTED LOADER with known inputs, which runs everywhere, and over the REAL repository,
where the whole-corpus partition is a set equality against an independently built corpus. Its
git-path half over live history is SPLIT OUT and stands down here for the WARP-1711 reason.

TEETH, MEASURED RATHER THAN CLAIMED. THIRTEEN mutations were driven one at a time in a scratch copy
of this repository, each one DIFFED to prove it applied - a replacement that matched nothing looks
exactly like a check that cannot fail - from a clean 38 passed 0 failed. Every one of them turned
assertions here RED. (The four mutations the original item drove against the earlier revision of
this file are recorded in the spec's Notes; these thirteen are the remediation's own, and they target
the properties that were previously asserted by nothing. Every mutation of .veldo/cost_to_change.py
also reds the engine-twin comparison, because it touched one copy of a pair that must stay
byte-identical.)

  1. repo_report's front-matter lookup severed (fm_of -> None): 5 red. This is the mutation that
     replaced every declared-placement attribution in the live map with the weaker join and left
     the suite green before.
  2. repo_report's touched-paths lookup severed (paths_of -> []): 2 red. Ditto for the git-path
     join, the stand-down that is this item's whole stated point.
  3. repo_report handing the corpus builder no events (events=[]): 3 red.
  4. an importlib load of the module inserted into scripts/secret_inventory.py, a REQUIRED gate
     stage: 1 red. It was green against the hand-typed gate-file list this replaced.
  5. CHECK_security downgraded from required to na in scripts/verify.sh: 1 red, which is what makes
     the gate domain derived rather than described.
  6. engine/.veldo/cost_to_change.py report() gutted to `return {}`: 1 red. Also green before.
  7. engine/.veldo/toe_corpus.py git_touched gutted to empty lists: 1 red. Also green before, and
     that copy is the one publish.py ships to adopters.
  8. _sum_cycles summing an unrecorded gate signal to 0 instead of None: 4 red.
  9. gate_basis hardcoded to 'recorded': 4 red.
 10. the cycle_notice suppressed: 3 red.
 11. "gate_event_records" dropped from the stand-down's coverage block: 2 red.
 12. a second suite fragment naming the module: 1 red.
 13. repo_report loading .veldo/entropy.py instead of .veldo/metrics.py, the C6 edge: 6 red.

AND ONE OF THOSE LIVE ASSERTIONS WAS A LANDMINE RATHER THAN A CHECK, fixed here. AC4 over the real
repository asserted that NO record carries spend - today's emptiness written as a required invariant -
so it stayed green exactly as long as nobody used .veldo/spend.py and reddened the moment somebody
did. Measured in a scratch copy: from 38 passed 0 failed, one sanctioned
`python3 .veldo/spend.py record --spec WARP-0100 --basis harness_reported --tokens 750000` left it at
37 passed 1 FAILED. It is now asserted against an expectation DERIVED from the independently built
corpus, per area and per signal, with only the arm that speaks about an absence branched on what the
run just measured. The teeth were re-measured with the spend recorded: `_sum_cost` returning 0
instead of None for a set that recorded nothing reds the derived assertion, which is the confident
zero this criterion exists to refuse. The live block is 4 assertions rather than 1, so a clean run is
40 passed 0 failed and the mutation counts above are the ones measured at the earlier revision.
"""
import re as _w1409_re

_w1409_cspec = importlib.util.spec_from_file_location(
    "w1409_cost_to_change", ROOT / ".veldo/cost_to_change.py")
_W1409 = importlib.util.module_from_spec(_w1409_cspec)
_w1409_cspec.loader.exec_module(_W1409)

_w1409_tspec = importlib.util.spec_from_file_location(
    "w1409_toe_corpus", ROOT / ".veldo/toe_corpus.py")
_W1409TC = importlib.util.module_from_spec(_w1409_tspec)
_w1409_tspec.loader.exec_module(_W1409TC)

_W1409ARCH = V._arch_module()

_W1409_CONTRACT_TEXT = """schema: veldo.arch/v1
id: fixture
title: The WARP-1409 fixture shape
version: 1
status: approved
approved_by: selftest
approved_at: 2026-01-01
areas:
  - id: alpha
    title: The alpha area
    includes: [".veldo/alpha.py", "alpha/**"]
  - id: beta
    title: The beta area
    includes: [".veldo/beta.py"]
dependencies:
  enforcement: review
  allow:
    - {from: beta, to: alpha}
"""

_W1409_SPEC_WITH_PLACEMENT = """---
schema: veldo.spec/v1
id: WARP-9401
title: fixture spec that declares where it lands
status: shipped
risk: standard
owner: selftest
placement: [alpha]
footprint:
  - ".veldo/alpha.py"
acceptance_criteria:
  - id: AC1
    text: observable.
rollback: git revert
---
body
"""


def _w1409_rec(spec_id, **over):
    """One well-formed veldo.toe_actuals/v1 record, shaped exactly as toe_corpus.build emits
    them. The overrides are how each planted-bad shape below is built, so a bad record differs
    from a good one in ONE field and the refusal is attributable to that field. The parameter is
    spec_id rather than spec so that `spec` itself is overridable, which is how the
    record-names-no-spec shape is planted."""
    rec = {
        "schema": _W1409.CORPUS_SCHEMA,
        "spec": spec_id,
        "features": {"spec_id": spec_id, "status": "shipped", "risk": "standard",
                     "acceptance_criteria": 2, "footprint_declared": 1, "depends_on": 0,
                     "spec_bytes": 900, "protected_touch": False},
        "cycles": {"gate_passes": 1, "gate_failures": 2, "review_verdicts": 1,
                   "events_seen": 4},
        "spend": {"tokens": 0, "cost_usd": 0, "human_minutes": 0, "spend_recorded": False},
        "git": {"commits": 1, "files_touched": 3},
    }
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(rec.get(k), dict):
            rec[k] = dict(rec[k], **v)
        else:
            rec[k] = v
    return rec


def _w1409_raises(fn, *a, **kw):
    """(raised, message) for one attempt. The MESSAGE is returned because an assertion that
    something raised, without checking WHAT, passes on an unrelated TypeError."""
    try:
        fn(*a, **kw)
    except BaseException as e:
        return True, "%s: %s" % (type(e).__name__, e)
    return False, ""


with tempfile.TemporaryDirectory() as _d:
    _w1409_cpath = tmpfile(_d, "architecture.yaml", _W1409_CONTRACT_TEXT)
    _W1409_CONTRACT = _W1409ARCH.load_contract(_w1409_cpath, V.parse_yamlish)

    # The fixture contract is a REAL one, not a hand-built dict that only resembles one: it is
    # parsed by the shipped reader and accepted by the shipped structural validator. Without
    # this every area-resolution assertion below could be passing over a shape the contract
    # system would reject.
    expect("WARP-1409 FIXTURE IS REAL: the fixture architecture contract is read by the shipped "
           "arch.load_contract through validate.parse_yamlish (the ONE parser) and accepted by "
           "arch.validate_contract with zero errors, so every area resolution asserted below is "
           "resolution against a contract this repository would actually honor",
           _W1409ARCH.validate_contract(_W1409_CONTRACT, _d, _w1409_cpath,
                                        lambda n, m: 1) == 0
           and sorted(_W1409ARCH.area_ids(_W1409_CONTRACT)) == ["alpha", "beta"])

    # The specs directory the front-matter index reads, through the ONE parser.
    _w1409_specs = Path(_d) / "specs"
    _w1409_specs.mkdir()
    (_w1409_specs / "WARP-9401-declared.md").write_text(_W1409_SPEC_WITH_PLACEMENT)
    _W1409_FM = _W1409.front_matter_index(_w1409_specs, V.parse_yamlish)

    expect("WARP-1409 AC1: THE FRONT-MATTER INDEX GOES THROUGH validate.parse_yamlish AND "
           "NOTHING ELSE, so placement and footprint arrive as real lists and this module ships "
           "no second parser. Driven over a fixture specs directory: the declared spec's "
           "placement comes back as the LIST ['alpha'], not as a string, and a directory with "
           "no specs yields an empty index rather than an exception",
           _W1409_FM.get("WARP-9401", {}).get("placement") == ["alpha"]
           and _W1409_FM.get("WARP-9401", {}).get("footprint") == [".veldo/alpha.py"]
           and _W1409.front_matter_index(Path(_d) / "no-such-dir", V.parse_yamlish) == {})

    # -----------------------------------------------------------------------------------
    # AC1. THE PLACEMENT JOIN, and the negative control that removes the declaration.
    # -----------------------------------------------------------------------------------
    _w1409_declared = _w1409_rec("WARP-9401")
    _w1409_att_placed = _W1409.attribute(_w1409_declared, _W1409_CONTRACT, _W1409ARCH,
                                         _W1409_FM.get("WARP-9401"), [".veldo/beta.py"])
    expect("WARP-1409 AC1: A SPEC THAT DECLARES A RESOLVING PLACEMENT IS JOINED ON THE "
           "DECLARATION, and the declaration WINS over the paths. The record is attributed to "
           "alpha with basis 'placement' even though the paths handed in point at beta, because "
           "a placement is what a human said and the paths are only what happened. It goes "
           "through arch.footprint_areas, the same join key PLAN-0011's entropy map uses, so "
           "the two maps cannot disagree about where a change landed",
           _w1409_att_placed["areas"] == ["alpha"]
           and _w1409_att_placed["basis"] == _W1409.BY_PLACEMENT)

    _w1409_att_nodecl = _W1409.attribute(_w1409_declared, _W1409_CONTRACT, _W1409ARCH,
                                         None, [".veldo/beta.py"])
    expect("WARP-1409 AC1 NEGATIVE CONTROL: THE SAME RECORD WITH THE DECLARATION REMOVED STOPS "
           "BEING PLACEMENT-ATTRIBUTED. One input differs (the front matter is absent) and the "
           "answer changes: basis becomes 'git_path' and the area becomes beta, the one the "
           "paths actually point at. Without this pair, the assertion above would pass on an "
           "implementation that stamped 'placement' on everything",
           _w1409_att_nodecl["areas"] == ["beta"]
           and _w1409_att_nodecl["basis"] == _W1409.BY_GIT_PATH)

    _w1409_att_unresolving = _W1409.attribute(
        _w1409_declared, _W1409_CONTRACT, _W1409ARCH,
        {"placement": ["nowhere_at_all"], "footprint": ["nothing/matches.py"]}, [])
    expect("WARP-1409 AC3: A PLACEMENT NAMING AN AREA THE CONTRACT DOES NOT DECLARE RESOLVES TO "
           "NOTHING AND INVENTS NO HOME. The record falls through to the stand-down and, with no "
           "paths to consider, comes back UNATTRIBUTED with an empty area list. A declaration "
           "the contract cannot resolve is not a join, and treating it as one would put cost in "
           "an area that does not exist",
           _w1409_att_unresolving["areas"] == []
           and _w1409_att_unresolving["basis"] == _W1409.UNATTRIBUTED)

    # -----------------------------------------------------------------------------------
    # AC2. THE GIT-PATH FALLBACK, LABELLED IN THE DATA. The report is serialized and the
    # label is looked for in the BYTES a consumer reads, because a docstring sentence and a
    # code comment are invisible to the entropy organ that consumes this.
    # -----------------------------------------------------------------------------------
    _w1409_gitrec = _w1409_rec("WARP-9402")
    _w1409_rep_git = _W1409.report([_w1409_gitrec], _W1409_CONTRACT, _W1409ARCH,
                                  fm_of=lambda _s: None,
                                  paths_of=lambda _s: [".veldo/alpha.py", "alpha/deep/thing.py"])
    _w1409_git_json = json.dumps(_w1409_rep_git, sort_keys=True)
    _w1409_git_area = _w1409_rep_git["areas"].get("alpha", {})
    expect("WARP-1409 AC2: A RECORD WITH NO PLACEMENT IS ATTRIBUTED BY GIT PATH AND THE REPORT "
           "SAYS SO IN THE DATA, not only in a comment or in the rendered text. The area carries "
           "attribution {'git_path': 1} and attribution_basis 'git_path', the member entry "
           "carries basis 'git_path' plus a label naming the weakness, the report carries "
           "git_path_attributed true, a bases entry, and a notice counting the records - and all "
           "of it survives json.dumps, which is the only form the consuming organ ever sees",
           _w1409_git_area.get("attribution") == {_W1409.BY_GIT_PATH: 1}
           and _w1409_git_area.get("attribution_basis") == _W1409.BY_GIT_PATH
           and [m["basis"] for m in _w1409_git_area.get("members", [])] == [_W1409.BY_GIT_PATH]
           and "GIT PATH" in _w1409_git_area["members"][0]["basis_label"]
           and _w1409_rep_git["git_path_attributed"] is True
           and _W1409.BY_GIT_PATH in _w1409_rep_git["bases"]
           and "BY GIT PATH" in _w1409_rep_git.get("notice", "")
           and "git_path" in _w1409_git_json and "GIT PATH" in _w1409_git_json)

    _w1409_rep_placed = _W1409.report([_w1409_declared], _W1409_CONTRACT, _W1409ARCH,
                                      fm_of=_W1409_FM.get, paths_of=lambda _s: [])
    expect("WARP-1409 AC2 NEGATIVE CONTROL: THE PLACEMENT-ONLY REPORT CARRIES NO GIT-PATH WARNING "
           "ANYWHERE. git_path_attributed is false, the git_path count is 0, there is no notice "
           "key at all, the bases map holds only 'placement', and the label's own text (the "
           "ATTRIBUTED BY GIT PATH sentence) appears nowhere in the serialized report. The basis "
           "KEY stays present at zero on purpose, so a consumer reads a stable shape; what must "
           "be absent is the WARNING. Without this pair the label assertions above would pass on "
           "an implementation that stamped the git-path warning on every report, which would "
           "train a reader to ignore it exactly when it matters",
           _w1409_rep_placed["git_path_attributed"] is False
           and _w1409_rep_placed["attribution"][_W1409.BY_GIT_PATH] == 0
           and "notice" not in _w1409_rep_placed
           and sorted(_w1409_rep_placed["bases"]) == [_W1409.BY_PLACEMENT]
           and "GIT PATH" not in json.dumps(_w1409_rep_placed, sort_keys=True))

    expect("WARP-1409 AC2 NEGATIVE CONTROL, THE FALLBACK CANNOT FABRICATE: THE SAME "
           "PLACEMENT-FREE RECORD WITH NO PATHS AVAILABLE IS UNATTRIBUTED, NOT PLACED. It lands "
           "in no area, it is counted in unattributed.records, and its spec id appears in the "
           "unattributed list. One input differs from the assertion two above (the paths are "
           "empty) and the record moves out of every area, which is what proves the git-path "
           "areas came from the paths rather than from a default",
           (lambda r: r["areas"] == {} and r["unattributed"]["records"] == 1
            and r["unattributed"]["specs"] == ["WARP-9402"]
            and r["attribution"][_W1409.UNATTRIBUTED] == 1
            and r["git_path_attributed"] is False)(
               _W1409.report([_w1409_gitrec], _W1409_CONTRACT, _W1409ARCH,
                             fm_of=lambda _s: None, paths_of=lambda _s: [])))

    # -----------------------------------------------------------------------------------
    # AC3. NOTHING IS FABRICATED, PROVEN AS SET EQUALITY OVER ONE ENUMERATION rather than as
    # two counts that could each be wrong in the same direction.
    # -----------------------------------------------------------------------------------
    _W1409_MIXED = [
        _w1409_rec("WARP-9401"),                       # declares placement alpha
        _w1409_rec("WARP-9402"),                       # git path into alpha
        _w1409_rec("WARP-9403"),                       # git path into beta and alpha
        _w1409_rec("WARP-9404"),                       # paths the contract does not enumerate
    ]
    _W1409_PATHS = {
        "WARP-9402": [".veldo/alpha.py"],
        "WARP-9403": [".veldo/beta.py", "alpha/x.py"],
        "WARP-9404": ["somewhere/else.py", "README.md"],
    }
    _w1409_rep = _W1409.report(_W1409_MIXED, _W1409_CONTRACT, _W1409ARCH,
                              fm_of=_W1409_FM.get,
                              paths_of=lambda s: _W1409_PATHS.get(s, []))
    _w1409_in_areas = set()
    for _a in _w1409_rep["areas"].values():
        _w1409_in_areas |= {m["spec"] for m in _a["members"]}
    expect("WARP-1409 AC3: THE SPECS INSIDE THE AREAS AND THE SPECS OUTSIDE THEM PARTITION THE "
           "CORPUS EXACTLY, asserted as SET EQUALITY and DISJOINTNESS over one enumeration and "
           "not as a pair of counts that could both be wrong the same way. Every corpus spec is "
           "either in at least one area or in the unattributed list, never both and never "
           "neither, so no record can be silently dropped and none can be silently invented",
           _w1409_in_areas | set(_w1409_rep["unattributed"]["specs"])
           == {r["spec"] for r in _W1409_MIXED}
           and _w1409_in_areas & set(_w1409_rep["unattributed"]["specs"]) == set()
           and _w1409_rep["unattributed"]["specs"] == ["WARP-9404"])

    expect("WARP-1409 AC3: THE COVERAGE FIGURES ARE DERIVED FROM THE SAME PARTITION THEY "
           "DESCRIBE. records equals the corpus length, attributed plus unattributed equals "
           "records, and area_memberships equals the total number of (record, area) pairs, which "
           "is GREATER than attributed here because WARP-9403 crossed two areas. A cross-area "
           "change contributes its recorded cost to EACH area it touched and is never divided "
           "between them, because a split would be an invented weighting",
           _w1409_rep["coverage"]["records"] == len(_W1409_MIXED) == 4
           and _w1409_rep["coverage"]["attributed"] + _w1409_rep["unattributed"]["records"]
           == _w1409_rep["coverage"]["records"]
           and _w1409_rep["coverage"]["area_memberships"]
           == sum(a["records"] for a in _w1409_rep["areas"].values()) == 4
           and _w1409_rep["areas"]["alpha"]["records"] == 3
           and _w1409_rep["areas"]["beta"]["records"] == 1
           and _w1409_rep["areas"]["alpha"]["attribution_basis"] == "mixed")

    expect("WARP-1409 AC3: THE CYCLE SUMS ARE THE RECORDED ONES AND GATE FAILURES STAY SEPARATE "
           "FROM PASSES, because failures are the rework signal and a map that merged them could "
           "not show rework at all. Three records in alpha at 1 pass and 2 failures each sum to "
           "3 and 6, and cycles_known counts the records that had ANY cycle data rather than "
           "assuming every record did. THIS IS ALSO THE POSITIVE CONTROL FOR THE GATE BASIS: these "
           "records DO carry gate events, so gate_basis reads 'recorded', gate_coverage is 1.0, "
           "usable_as_rework_ground_truth is true and there is no cycle notice - which is what "
           "makes the None asserted below the absence of the signal and not a hardcoded value",
           _w1409_rep["areas"]["alpha"]["cycles"]["gate_passes"] == 3
           and _w1409_rep["areas"]["alpha"]["cycles"]["gate_failures"] == 6
           and _w1409_rep["areas"]["alpha"]["cycles"]["cycles_known"] == 3
           and _w1409_rep["areas"]["alpha"]["cycles"]["cycles_coverage"] == 1.0
           and _w1409_rep["areas"]["alpha"]["cycles"]["gate_basis"] == "recorded"
           and _w1409_rep["areas"]["alpha"]["cycles"]["gate_events_known"] == 3
           and _w1409_rep["areas"]["alpha"]["cycles"]["gate_coverage"] == 1.0
           and _w1409_rep["coverage"]["gate_event_records"] == 4
           and _w1409_rep["coverage"]["usable_as_rework_ground_truth"] is True
           and "cycle_notice" not in _w1409_rep)

    expect("WARP-1409 AC3 NEGATIVE CONTROL FOR cycles_known: a record whose event stream held "
           "NOTHING (events_seen 0) is counted as having NO cycle data, so cycles_coverage drops "
           "below 1.0 and a reader can tell a genuine zero from an absent one. Without this "
           "control, cycles_known could be a synonym for the record count",
           (lambda r: r["areas"]["alpha"]["cycles"]["cycles_known"] == 0
            and r["areas"]["alpha"]["cycles"]["cycles_coverage"] == 0.0)(
               _W1409.report([_w1409_rec("WARP-9405",
                                         cycles={"gate_passes": 0, "gate_failures": 0,
                                                 "review_verdicts": 0, "events_seen": 0})],
                             _W1409_CONTRACT, _W1409ARCH, fm_of=lambda _s: None,
                             paths_of=lambda _s: [".veldo/alpha.py"])))

    # -----------------------------------------------------------------------------------
    # AC4. THE UNRECORDED GATE CYCLE IS None AND NOT ZERO EITHER, which is the same discipline
    # applied to the signal that was printing a confident zero with FULL COVERAGE. Measured over
    # this repository's log: every gate.passed and gate.failed event carries a commit and no spec
    # id or correlation id, and toe_corpus.cycles_for joins on those ids, so gate_passes and
    # gate_failures were structurally 0 for every record and could never be anything else - while
    # cycles_coverage read 1.0, because a review verdict alone satisfies events_seen. A reader
    # quoting "this area had zero gate failures" was quoting the emitter gap.
    # -----------------------------------------------------------------------------------
    _W1409_NO_GATE = [
        _w1409_rec("WARP-9408", cycles={"gate_passes": 0, "gate_failures": 0,
                                        "review_verdicts": 3, "events_seen": 3}),
        _w1409_rec("WARP-9409", cycles={"gate_passes": 0, "gate_failures": 0,
                                        "review_verdicts": 1, "events_seen": 1}),
    ]
    _w1409_rep_nogate = _W1409.report(_W1409_NO_GATE, _W1409_CONTRACT, _W1409ARCH,
                                      fm_of=lambda _s: None,
                                      paths_of=lambda _s: [".veldo/alpha.py"])
    _w1409_nogate_cycles = _w1409_rep_nogate["areas"]["alpha"]["cycles"]
    expect("WARP-1409 AC4: AN AREA WHOSE RECORDS CARRY NO GATE EVENT REPORTS gate_passes AND "
           "gate_failures AS None WITH gate_basis 'unrecorded', NEVER AS A CONFIDENT ZERO - and it "
           "does so in the DATA, which is AC2's own stated principle, not in the spec prose where "
           "this gap used to live. THE FIXTURE IS THE PRODUCTION SHAPE: records that carry review "
           "verdicts and no gate events, so cycles_coverage is 1.0 while gate_coverage is 0.0, "
           "which is exactly the trap - full cycle coverage beside a gate figure that measures "
           "nothing. The two signals are separate: review_verdicts is the REAL sum 4 with "
           "review_basis 'recorded' and verdicts_known 2, because that emitter does name the spec. "
           "usable_as_rework_ground_truth is false and the report carries a cycle_notice naming the "
           "emitter gap by name, and all of it survives json.dumps",
           _w1409_nogate_cycles["gate_passes"] is None
           and _w1409_nogate_cycles["gate_failures"] is None
           and _w1409_nogate_cycles["gate_basis"] == "unrecorded"
           and _w1409_nogate_cycles["gate_events_known"] == 0
           and _w1409_nogate_cycles["gate_coverage"] == 0.0
           and _w1409_nogate_cycles["review_verdicts"] == 4
           and _w1409_nogate_cycles["review_basis"] == "recorded"
           and _w1409_nogate_cycles["verdicts_known"] == 2
           and _w1409_nogate_cycles["cycles_coverage"] == 1.0
           and _w1409_rep_nogate["coverage"]["gate_event_records"] == 0
           and _w1409_rep_nogate["coverage"]["usable_as_rework_ground_truth"] is False
           and "verify.sh" in _w1409_rep_nogate.get("cycle_notice", "")
           and "no spec id" in _w1409_rep_nogate.get("cycle_notice", "")
           and "unrecorded" in json.dumps(_w1409_rep_nogate, sort_keys=True))

    expect("WARP-1409 AC4: THE RENDERED TEXT PRINTS gate_passes=None RATHER THAN 0 for the same "
           "records, so the human surface cannot show a confident zero the JSON does not carry, and "
           "it names the basis and the gate-event coverage beside the figure. NEGATIVE CONTROL IN "
           "THE SAME ASSERTION: the mixed fixture, whose records DO carry gate events, renders the "
           "real numbers and never the None, so this is the absence of the signal rather than a "
           "renderer that always prints None",
           "gate_passes=None" in _W1409.render_text(_w1409_rep_nogate)
           and "gate_failures=None" in _W1409.render_text(_w1409_rep_nogate)
           and "unrecorded, gate events on 0 of 2" in _W1409.render_text(_w1409_rep_nogate)
           and "gate_passes=3" in _W1409.render_text(_w1409_rep)
           and "gate_passes=None" not in _W1409.render_text(_w1409_rep))

    # -----------------------------------------------------------------------------------
    # AC4. THE UNKNOWN COST IS None AND NOT ZERO. This is the assertion the mutation teeth
    # were taken on: WARP-1401 measured that nothing in this loop emits tokens, so a summed
    # zero here would be a confident measurement of nothing.
    # -----------------------------------------------------------------------------------
    expect("WARP-1409 AC4: AN AREA WHOSE RECORDS CARRY NO RECORDED SPEND REPORTS ITS COST FIELDS "
           "AS None WITH cost_known FALSE, NEVER AS A CONFIDENT ZERO. WARP-1401 measured the "
           "reason: not one event in this repository carries tokens, cost_usd or human_minutes, "
           "because a token count is not knowable from inside a repository. A summed zero here "
           "would teach every later TOE layer from nothing while looking like data, and the "
           "report says so at the top level too via cost_notice",
           all(_w1409_rep["areas"]["alpha"]["cost"][f] is None
               for f in _W1409.COST_FIELDS)
           and _w1409_rep["areas"]["alpha"]["cost"]["cost_known"] is False
           and _w1409_rep["areas"]["alpha"]["cost"]["cost_basis"] == "unrecorded"
           and _w1409_rep["areas"]["alpha"]["cost"]["spend_coverage"] == 0.0
           and _w1409_rep["coverage"]["usable_as_cost_ground_truth"] is False
           and "None rather than zero" in _w1409_rep.get("cost_notice", ""))

    _w1409_spent = _w1409_rec("WARP-9406", spend={"tokens": 1200, "cost_usd": 3.5,
                                                  "human_minutes": 12,
                                                  "spend_recorded": True})
    _w1409_rep_spent = _W1409.report([_w1409_spent], _W1409_CONTRACT, _W1409ARCH,
                                     fm_of=lambda _s: None,
                                     paths_of=lambda _s: [".veldo/alpha.py"])
    expect("WARP-1409 AC4 POSITIVE CONTROL: A RECORD THAT ACTUALLY CARRIES SPEND PRODUCES REAL "
           "NUMBERS, so the None above is the absence of data and not a hardcoded value. tokens "
           "1200, cost_usd 3.5 and human_minutes 12 come through, cost_known is true, "
           "spend_coverage is 1.0, usable_as_cost_ground_truth flips to true, and the top-level "
           "cost_notice is GONE. This is the pair that makes the unknown-cost assertion a "
           "measurement rather than a restatement of the implementation",
           _w1409_rep_spent["areas"]["alpha"]["cost"]["tokens"] == 1200
           and _w1409_rep_spent["areas"]["alpha"]["cost"]["cost_usd"] == 3.5
           and _w1409_rep_spent["areas"]["alpha"]["cost"]["human_minutes"] == 12
           and _w1409_rep_spent["areas"]["alpha"]["cost"]["cost_known"] is True
           and _w1409_rep_spent["areas"]["alpha"]["cost"]["cost_basis"] == "recorded"
           and _w1409_rep_spent["areas"]["alpha"]["cost"]["spend_coverage"] == 1.0
           and _w1409_rep_spent["coverage"]["usable_as_cost_ground_truth"] is True
           and "cost_notice" not in _w1409_rep_spent)

    _w1409_rep_mixed_cost = _W1409.report(
        [_w1409_spent, _w1409_rec("WARP-9407")], _W1409_CONTRACT, _W1409ARCH,
        fm_of=lambda _s: None, paths_of=lambda _s: [".veldo/alpha.py"])
    expect("WARP-1409 AC4: PARTIAL SPEND COVERAGE IS REPORTED AS PARTIAL. With one of two "
           "records carrying spend, the area's tokens are the ONE recorded figure (1200) and "
           "spend_known is 1 of 2 with spend_coverage 0.5, so a reader can see the sum covers "
           "half the changes rather than reading it as the area's whole cost. The unrecorded "
           "record contributes nothing rather than a zero, which is the same distinction the "
           "None above draws, at the record level",
           _w1409_rep_mixed_cost["areas"]["alpha"]["cost"]["tokens"] == 1200
           and _w1409_rep_mixed_cost["areas"]["alpha"]["cost"]["spend_known"] == 1
           and _w1409_rep_mixed_cost["areas"]["alpha"]["cost"]["spend_coverage"] == 0.5
           and _w1409_rep_mixed_cost["areas"]["alpha"]["records"] == 2)

    # -----------------------------------------------------------------------------------
    # AC5. FAIL CLOSED AND BY NAME, eight planted-bad shapes, each refused with a message
    # naming the record, the field and what is wrong. Bound to the length of its own literal
    # table, so emptying the table reds this instead of passing over nothing.
    # -----------------------------------------------------------------------------------
    _W1409_BAD = [
        ("a record that is not a mapping at all", ["not", "a", "mapping"],
         "must be a mapping"),
        ("a record from some other schema", _w1409_rec("WARP-9411", schema="veldo.other/v1"),
         "schema must be"),
        ("a record naming no spec", _w1409_rec("WARP-9412", spec=""),
         "must name the spec it accounts for"),
        ("a NEGATIVE gate-failure count", _w1409_rec("WARP-9413",
                                                     cycles={"gate_failures": -1}),
         "cycles.gate_failures cannot be negative"),
        ("a gate-failure count that is a string", _w1409_rec("WARP-9414",
                                                             cycles={"gate_failures": "two"}),
         "cycles.gate_failures must be a number"),
        ("a spend block that is not a mapping", _w1409_rec("WARP-9415", spend=None),
         "spend must be a mapping"),
        ("spend_recorded that is not a boolean", _w1409_rec("WARP-9416",
                                                            spend={"spend_recorded": "yes"}),
         "spend.spend_recorded must be a boolean"),
        ("cycles with no events_seen at all, which is what separates absent from zero",
         dict(_w1409_rec("WARP-9417"), cycles={"gate_passes": 1, "gate_failures": 0,
                                               "review_verdicts": 0}),
         "cycles.events_seen must be a number"),
    ]
    _w1409_refusals = []
    for _label, _bad, _want in _W1409_BAD:
        _raised, _msg = _w1409_raises(_W1409.report, [_bad], _W1409_CONTRACT, _W1409ARCH)
        _w1409_refusals.append((_label, _want, _raised, _msg))

    expect("WARP-1409 AC5: EVERY MALFORMED ACTUALS RECORD IS REFUSED BY NAME, driven for EIGHT "
           "planted shapes: not a mapping, a foreign schema, no spec id, a negative gate-failure "
           "count, a non-numeric one, a spend block that is not a mapping, a non-boolean "
           "spend_recorded, and cycles with no events_seen. Each raises and each message names "
           "the FIELD, because 'invalid record' tells the reader nothing they can act on. "
           "Skipping a bad record instead would produce a smaller per-area map that still looks "
           "complete, and a per-area cost is exactly the number somebody quotes without asking "
           "how many records it came from. BOUND TO THE LENGTH OF ITS OWN TABLE",
           len(_w1409_refusals) == len(_W1409_BAD) == 8
           and all(raised and want in msg for _l, want, raised, msg in _w1409_refusals))

    expect("WARP-1409 AC5: THE REFUSAL NAMES THE SPEC THE BAD RECORD BELONGS TO, not only the "
           "index, so a corpus of 174 records points at the one that is wrong. Checked on the "
           "negative-count shape, whose spec id is known",
           "WARP-9413" in _w1409_raises(
               _W1409.report, [_w1409_rec("WARP-9413", cycles={"gate_failures": -1})],
               _W1409_CONTRACT, _W1409ARCH)[1])

    expect("WARP-1409 AC5: A DUPLICATE SPEC IS REFUSED, because the same record counted twice "
           "inflates every area it touches and a per-area cost that double-counts one change is "
           "wrong in the direction nobody checks. The message names the spec and the indices",
           (lambda r: r[0] and "appears in 2 records" in r[1] and "WARP-9401" in r[1])(
               _w1409_raises(_W1409.report, [_w1409_rec("WARP-9401"), _w1409_rec("WARP-9401")],
                             _W1409_CONTRACT, _W1409ARCH)))

    expect("WARP-1409 AC5 POSITIVE CONTROL: THE WELL-FORMED CORPUS RAISES NOTHING and reports "
           "zero problems, so the validator is not simply refusing everything. Without this "
           "pair, an implementation that raised on every input would satisfy all eight refusals "
           "above and be worthless",
           _W1409.corpus_problems(_W1409_MIXED) == []
           and not _w1409_raises(_W1409.report, _W1409_MIXED, _W1409_CONTRACT, _W1409ARCH)[0])

    # The recording reporter has the SAME (name, msg) -> 1 shape validate.fail has, so what it
    # collects is exactly what the gate surface emits. It exists so the two surfaces can be
    # compared as SETS of messages rather than as two counts that could agree by accident.
    _w1409_reported = []
    _w1409_bad_one = [_w1409_rec("WARP-9418", spend=None)]
    _w1409_errs = _W1409.check_corpus(
        _w1409_bad_one, lambda n, m: (_w1409_reported.append(m), 1)[1])
    expect("WARP-1409 AC5: THE GATE-SHAPED REPORTER IS AN INJECTED fail AND THE TWO SURFACES READ "
           "ONE ENUMERATION. check_corpus is driven with the real validate.fail and returns a "
           "positive count for a malformed corpus and exactly 0 for the well-formed one; driven "
           "again with a recording reporter of the same shape, the messages it emits are the SAME "
           "LIST corpus_problems returns, which is what makes the reporting surface and the hard "
           "refusal incapable of disagreeing about what is wrong",
           _W1409.check_corpus(_w1409_bad_one, V.fail) > 0
           and _W1409.check_corpus(_W1409_MIXED, V.fail) == 0
           and _w1409_errs == len(_w1409_reported) == len(
               _W1409.corpus_problems(_w1409_bad_one)) > 0
           and _w1409_reported == _W1409.corpus_problems(_w1409_bad_one))

    # -----------------------------------------------------------------------------------
    # AC6. ADOPTION SAFE, AND THE STAND-DOWN IS NOT UNCONDITIONAL.
    # -----------------------------------------------------------------------------------
    _w1409_sd_records = _W1409.report([], _W1409_CONTRACT, _W1409ARCH)
    _w1409_sd_contract = _W1409.report(_W1409_MIXED, None, _W1409ARCH)
    expect("WARP-1409 AC6: WITH NO ACTUALS RECORDS THE WHOLE DERIVATION STANDS DOWN SILENTLY, "
           "and with no architecture contract it stands down too. Each returns a report with "
           "standdown true, a reason naming which condition it was, empty areas and zeroed "
           "counts. The two stand-downs are KEY-IDENTICAL to each other, and their keys are a "
           "SUPERSET of every key a live report carries apart from the two conditional notices, "
           "so a consumer reading a stand-down never has to guess whether a key is missing or "
           "the value is genuinely empty. Neither raises: a repository that records none of this "
           "is byte-identically unaffected",
           _w1409_sd_records["standdown"] is True
           and "no toe actuals records" in _w1409_sd_records["reason"]
           and _w1409_sd_contract["standdown"] is True
           and "no architecture contract" in _w1409_sd_contract["reason"]
           and _w1409_sd_records["areas"] == _w1409_sd_contract["areas"] == {}
           and sorted(_w1409_sd_records) == sorted(_w1409_sd_contract)
           and set(_w1409_rep) - {"notice", "cost_notice"} <= set(_w1409_sd_records)
           # The same shape claim ONE LEVEL DOWN, where the coverage figures live: a consumer
           # reading coverage.gate_event_records off a stand-down must not get a KeyError, and a
           # key added to the live coverage block and forgotten in the stand-down is exactly the
           # drift the top-level comparison cannot see.
           and sorted(_w1409_sd_records["coverage"]) == sorted(_w1409_rep["coverage"])
           and _w1409_sd_records["coverage"]["records"] == 0)

    expect("WARP-1409 AC6 NEGATIVE CONTROL: A POPULATED CORPUS WITH A CONTRACT DOES NOT STAND "
           "DOWN. standdown is false, there is no reason key, and the areas are populated, so "
           "the two stand-downs above are the missing inputs' doing and not an unconditional "
           "empty report. Without this pair, a module that always stood down would pass every "
           "adoption-safety assertion in this file",
           _w1409_rep["standdown"] is False and "reason" not in _w1409_rep
           and sorted(_w1409_rep["areas"]) == ["alpha", "beta"])

    # -----------------------------------------------------------------------------------
    # AC6. DETERMINISTIC AND IDEMPOTENT, including under a reordered corpus: the report is a
    # function of the SET of records, so re-harvesting history in a different order cannot
    # move a number.
    # -----------------------------------------------------------------------------------
    expect("WARP-1409 AC6: THE REPORT IS BYTE-IDENTICAL ACROSS TWO RUNS OVER IDENTICAL INPUTS "
           "AND ACROSS A REVERSED CORPUS, so it is deterministic and independent of harvest "
           "order. Nothing here reads a clock, mints an id or writes a file, which is what lets "
           "the map be re-derived over history as often as anyone likes",
           json.dumps(_W1409.report(_W1409_MIXED, _W1409_CONTRACT, _W1409ARCH,
                                    fm_of=_W1409_FM.get,
                                    paths_of=lambda s: _W1409_PATHS.get(s, [])),
                      sort_keys=True)
           == json.dumps(_w1409_rep, sort_keys=True)
           == json.dumps(_W1409.report(list(reversed(_W1409_MIXED)), _W1409_CONTRACT, _W1409ARCH,
                                       fm_of=_W1409_FM.get,
                                       paths_of=lambda s: _W1409_PATHS.get(s, [])),
                         sort_keys=True))

    # -----------------------------------------------------------------------------------
    # AC1 + AC2, THE WIRING ITSELF. repo_report() is the function that produces every number
    # the spec publishes and every number a reader will quote, and it composes FIVE things: the
    # contract, the corpus, the front-matter lookup, the touched-paths lookup and the parser.
    # A review severed each of the two JOINS in it separately and this suite stayed green while
    # the live map lost, in turn, every git-path attribution and then every declared-placement
    # attribution - because everything above drives report() over hand-built lookups and nothing
    # drove the composition. It is driven here through the injected loader, over KNOWN inputs, so
    # both joins and every wired argument are observable. This runs everywhere: it needs no
    # history, unlike the live git-path leg further down.
    # -----------------------------------------------------------------------------------
    class _W1409Mod:
        """A stand-in for one loaded sibling. Answers only the attributes repo_report actually
        uses, so a rewiring that reaches for something else raises AttributeError here rather than
        passing."""

        def __init__(self, **kw):
            self.__dict__.update(kw)

    _W1409_STUB_EVENTS = [{"schema": "veldo.event/v1", "type": "sentinel"}]
    _W1409_STUB_PROTECTED = ["fixture/protected/**"]
    _W1409_STUB_CORPUS = [_w1409_rec("WARP-9401"),      # declares placement alpha in the specs dir
                          _w1409_rec("WARP-9421"),      # no spec file, so paths decide
                          _w1409_rec("WARP-9422")]      # no spec file and paths outside the contract
    _W1409_STUB_TOUCHED = {"WARP-9421": [".veldo/beta.py"],
                           "WARP-9422": ["outside/everything.py"]}
    _w1409_asked = []
    _w1409_build_kw = {}
    _w1409_contract_root = []

    def _w1409_build(specs_dir=None, events=None, protected=None):
        _w1409_build_kw.update({"specs_dir": specs_dir, "events": events, "protected": protected})
        return list(_W1409_STUB_CORPUS)

    def _w1409_stub_load(name, rel):
        """The loader repo_report is handed. It records WHICH PATHS the wiring asks for, and it
        KeyErrors on anything else, so a module that started reaching for a fifth sibling cannot be
        silently accepted here. The caller below turns that into a RED rather than letting it abort
        the fragment: a raise at module scope would take every assertion after it with it, and a
        mutation that silently deletes coverage is the failure this whole remediation is about."""
        _w1409_asked.append(rel)
        return {
            ".veldo/validate.py": _W1409Mod(
                load_repo_contract=lambda repo_root=None: (
                    _w1409_contract_root.append(repo_root) or (_W1409ARCH, _W1409_CONTRACT)),
                parse_yamlish=V.parse_yamlish),
            ".veldo/toe_corpus.py": _W1409Mod(
                build=_w1409_build,
                git_touched=lambda s: {"commits": ["deadbeef"] if s in _W1409_STUB_TOUCHED else [],
                                       "files": _W1409_STUB_TOUCHED.get(s, [])}),
            ".veldo/metrics.py": _W1409Mod(load=lambda: _W1409_STUB_EVENTS),
            ".veldo/policy_check.py": _W1409Mod(
                protected_patterns=lambda: _W1409_STUB_PROTECTED),
        }[rel]

    def _w1409_wire(load):
        """(report, error) for ONE wiring run over an injected loader. The error is returned rather
        than raised so a rewiring reds the assertion that names it instead of aborting the
        fragment."""
        try:
            return _W1409.repo_report(root=_d, load=load), ""
        except BaseException as _e:                                            # noqa: BLE001
            return {"areas": {}, "attribution": {}, "coverage": {},
                    "unattributed": {"specs": []}}, "%s: %s" % (type(_e).__name__, _e)

    _w1409_wired, _w1409_wired_err = _w1409_wire(_w1409_stub_load)
    _w1409_wired_members = {m["spec"]: m["basis"] for _a in _w1409_wired["areas"].values()
                            for m in _a["members"]}
    expect("WARP-1409 AC1 AND AC2, THE WIRING: repo_report COMPOSES BOTH JOINS AND EVERY ARGUMENT IS "
           "OBSERVABLE. Driven with a loader that answers the four sibling paths from known data. It "
           "asks for exactly .veldo/validate.py, .veldo/toe_corpus.py, .veldo/metrics.py and "
           ".veldo/policy_check.py; it hands the corpus builder the specs directory under the root "
           "it was given, the events metrics.load returned and the patterns policy_check returned, "
           "all three by identity rather than by resemblance; and it obtains the contract through "
           "validate.load_repo_contract for that same root. The RESULT proves both joins fired at "
           "once: WARP-9401, which declares a resolving placement in the specs directory, comes back "
           "basis 'placement'; WARP-9421, which has no spec file and whose only evidence is the "
           "paths git_touched returned, comes back basis 'git_path' in the area those paths fall "
           "into; WARP-9422, with neither, is unattributed. Severing either lookup in the wiring "
           "moves a record and reds this, which is what nothing asserted before, and a wiring that "
           "reaches for a fifth sibling or misuses one reds here too, by name, rather than raising",
           _w1409_wired_err == ""
           and _w1409_asked == [".veldo/validate.py", ".veldo/toe_corpus.py", ".veldo/metrics.py",
                            ".veldo/policy_check.py"]
           and _w1409_contract_root == [str(_d)]
           and _w1409_build_kw["specs_dir"] == Path(_d) / "specs"
           and _w1409_build_kw["events"] is _W1409_STUB_EVENTS
           and _w1409_build_kw["protected"] is _W1409_STUB_PROTECTED
           and _w1409_wired_members == {"WARP-9401": _W1409.BY_PLACEMENT,
                                        "WARP-9421": _W1409.BY_GIT_PATH}
           and sorted(_w1409_wired["areas"]) == ["alpha", "beta"]
           and _w1409_wired["unattributed"]["specs"] == ["WARP-9422"]
           and _w1409_wired["attribution"] == {_W1409.BY_PLACEMENT: 1, _W1409.BY_GIT_PATH: 1,
                                               _W1409.UNATTRIBUTED: 1}
           and _w1409_wired["coverage"]["records"] == len(_W1409_STUB_CORPUS) == 3)

    expect("WARP-1409 AC2 NEGATIVE CONTROL ON THE WIRING: WITH THE GIT READER ANSWERING NOTHING, THE "
           "SAME COMPOSITION LOSES ITS GIT-PATH ATTRIBUTION AND FABRICATES NOTHING IN ITS PLACE. One "
           "input differs - git_touched returns no files for any spec - and WARP-9421 moves out of "
           "beta into the unattributed list while WARP-9401, whose join is a declaration rather than "
           "a path, does not move at all. That is the pair which proves the git-path areas in the "
           "wired report came from the reader, and it is the mutation (paths_of severed) that used "
           "to leave this suite at 30 passed",
           (lambda r, err: err == ""
            and r["attribution"] == {_W1409.BY_PLACEMENT: 1, _W1409.BY_GIT_PATH: 0,
                                     _W1409.UNATTRIBUTED: 2}
            and sorted(r["areas"]) == ["alpha"]
            and r["unattributed"]["specs"] == ["WARP-9421", "WARP-9422"]
            and r["git_path_attributed"] is False)(
               *_w1409_wire(lambda n, rel: (
                   _W1409Mod(build=_w1409_build,
                             git_touched=lambda _s: {"commits": [], "files": []})
                   if rel == ".veldo/toe_corpus.py" else _w1409_stub_load(n, rel)))))

# -----------------------------------------------------------------------------------
# AC7. THE SEAM TO THE ARCHITECTURE ORGAN IS PROSE, NOT A DEPENDENCY EDGE. Asserted over
# the text of BOTH files, with a positive control so the absence is not passing for a
# trivial reason.
# -----------------------------------------------------------------------------------
_W1409_SRC = (ROOT / ".veldo/cost_to_change.py").read_text()
_W1409_ENTROPY_SRC = (ROOT / ".veldo/entropy.py").read_text()
# THE MODULE'S WHOLE DEPENDENCY SURFACE, enumerated from the source rather than described: every
# sibling it can reach is NAMED BY A LITERAL PATH at a loader call, whether that call is the
# module's own `_load` or the injected `load` repo_report takes, so this regex is the complete list
# of files it can pull in. Asserting the SET makes the absence of entropy.py a measurement over a
# known-non-empty list instead of a grep that would also pass on a module that loaded nothing at
# all. The loader being injectable does not widen the surface: what a caller may substitute is HOW
# these four paths are turned into modules, and the paths themselves are literals right here.
_W1409_LOADS = sorted(set(_w1409_re.findall(r'_?load\("[^"]+",\s*"([^"]+)"\)', _W1409_SRC)))
expect("WARP-1409 AC7: THE CROSS-PLAN SEAM IS SOFT (PLAN-0014 C6), ASSERTED AS THE MODULE'S WHOLE "
       "DEPENDENCY SURFACE. Every sibling .veldo/cost_to_change.py can reach arrives through a "
       "loader call with a literal path, and that set is exactly validate, toe_corpus, metrics and "
       "policy_check: .veldo/entropy.py is NOT in it, and entropy.py names cost_to_change nowhere "
       "either. So PLAN-0011's organ and this aggregation are joined by prose and by a shared "
       "RESOLVER, never by an import either one could break. The set is non-empty and pinned to "
       "its members, so this cannot pass for a module that loads nothing",
       _W1409_LOADS == [".veldo/metrics.py", ".veldo/policy_check.py", ".veldo/toe_corpus.py",
                        ".veldo/validate.py"]
       and "cost_to_change" not in _W1409_ENTROPY_SRC
       and "footprint_areas" in _W1409_SRC and "area_for_path" in _W1409_SRC)

expect("WARP-1409 AC7: THE ONE DEPENDENCY THIS MODULE DOES TAKE IS ALREADY MODELLED IN THE "
       "CONTRACT. It is placed in the metrics area and it loads arch, which lives in contracts, "
       "and the contract's dependencies.allow declares metrics to contracts. So nothing in this "
       "item adds an edge to the architecture contract, which is the exact thing C6 forbids: the "
       "edge it uses was declared before this item existed",
       ("metrics", "contracts") in _W1409ARCH._allowed_edges(
           _W1409ARCH.load_contract(ROOT / ".veldo/architecture.yaml", V.parse_yamlish)))


def _w1409_spawn_hits(text):
    """The spawn primitives present in a text. ONE scanner, used for the module and for the
    planted control below, so a scanner that found nothing could not pass for a clean file."""
    return [t for t in ("subprocess", "Popen", "os.system", "os.fork", "threading",
                        "multiprocessing", "nohup", "setsid", "daemon") if t in text]


expect("WARP-1409 AC7: THE MODULE STARTS NOTHING. Its source contains no spawn primitive at all "
       "(no subprocess, Popen, os.system, os.fork, threading, multiprocessing, nohup, setsid or "
       "daemon), so the derivation is a pure function over injected data that runs in-session and "
       "outlives nothing, which is this repository's standing no-detached-processes invariant. "
       "POSITIVE CONTROL: the SAME scanner over a planted text finds the primitive, so the empty "
       "result above is a measurement and not a scanner that looks for nothing",
       _w1409_spawn_hits(_W1409_SRC) == []
       and _w1409_spawn_hits("x = subprocess.Popen(['sh'])") == ["subprocess", "Popen"])

# -----------------------------------------------------------------------------------
# AC6. NO GATE STAGE CONSUMES THIS MODULE'S OUTPUT, which is what makes "a repository that
# never uses it is byte-identically unaffected" a property rather than a promise.
#
# THE DOMAIN IS DERIVED FROM scripts/verify.sh, NOT TYPED. What stood here was nine hand-typed
# literals, and a universal claim over a hand-typed list is a claim about the list. That one
# OMITTED three executables verify.sh runs as REQUIRED stages (scripts/selftest.py,
# scripts/secret_inventory.py, .veldo/events.py) and INCLUDED two it never invokes directly
# (.veldo/validate_checks.py, .veldo/policy_check.py), so wiring the module into
# scripts/secret_inventory.py - a required stage - left the assertion green. The stage set is now
# parsed out of the catalog and the always-run body, and then closed transitively over what each
# member EXECUTES or LOADS, so a new stage or a new load edge enters the domain by itself.
# -----------------------------------------------------------------------------------
_W1409_VERIFY_SRC = (ROOT / "scripts/verify.sh").read_text()
_W1409_PATH_RE = r"(?:\.veldo|scripts)/[\w./-]+\.(?:py|sh)"
_W1409_RUN_RE = r"(?:python3|bash|sh)\s+(%s)" % _W1409_PATH_RE
# Every catalog item DECLARED required, with the command it declares, plus every direct
# invocation in the always-run body below the catalog (contracts, shape gate, review events).
_W1409_REQUIRED = _w1409_re.findall(r'^CHECK_(\w+)="required:(.+)"$', _W1409_VERIFY_SRC,
                                    _w1409_re.M)
_W1409_STAGES = sorted(
    {p for _n, _cmd in _W1409_REQUIRED for p in _w1409_re.findall(_W1409_PATH_RE, _cmd)}
    | set(_w1409_re.findall(_W1409_RUN_RE, _W1409_VERIFY_SRC)))


def _w1409_invokes(rel):
    """What ONE gate file EXECUTES or LOADS: the shell commands it runs and the sibling modules it
    hands to importlib. An EXECUTES/LOADS edge, deliberately not a MENTIONS edge - a comment naming
    scripts/publish.py, or publish.py's own hold-back list of engine paths, is not a gate
    dependency, and a closure built on mentions would drag half the repository in and make the
    absence below unfalsifiable in the other direction."""
    p = ROOT / rel
    if not p.is_file():
        return set()
    t = p.read_text()
    out = set(_w1409_re.findall(_W1409_RUN_RE, t))
    for _grp in _w1409_re.findall(r'(?:ROOT|root|base|BASE)\s*/\s*((?:"[^"]+"\s*/\s*)*"[^"]+")', t):
        _cand = "/".join(_w1409_re.findall(r'"([^"]+)"', _grp))
        if _cand.endswith((".py", ".sh")):
            out.add(_cand)
    return {o for o in out if o != rel}


_W1409_GATE_CLOSURE = set(_W1409_STAGES)
_w1409_frontier = list(_W1409_STAGES)
while _w1409_frontier:
    for _w1409_edge in _w1409_invokes(_w1409_frontier.pop()):
        if _w1409_edge not in _W1409_GATE_CLOSURE:
            _W1409_GATE_CLOSURE.add(_w1409_edge)
            _w1409_frontier.append(_w1409_edge)
_W1409_GATE_TEXTS = {f: (ROOT / f).read_text() for f in sorted(_W1409_GATE_CLOSURE)
                     if (ROOT / f).is_file()}

expect("WARP-1409 AC6: THE GATE DOMAIN IS DERIVED AND IT IS REAL, which is the precondition for "
       "any claim of the form 'no gate stage does X'. Parsed out of scripts/verify.sh: every "
       "catalog item declared required contributes at least one repository path, the required set "
       "covers lint, unit, security, generated, docs and extra, and the stage set contains all six "
       "of those scripts plus the three the always-run body invokes directly (.veldo/validate.py, "
       ".veldo/shape_gate.py, .veldo/events.py) - the last three being exactly what the hand-typed "
       "list this replaces got wrong. The transitive closure is STRICTLY LARGER than the stage set "
       "and every member of it is a file that exists, and it reaches .veldo/validate_checks.py "
       "through validate.py and .veldo/secret_inventory.py through scripts/secret_inventory.py, so "
       "both edge forms (a shell invocation and an importlib load) are proven to work",
       len(_W1409_REQUIRED) >= 6
       and {n for n, _c in _W1409_REQUIRED} >= {"lint", "unit", "security", "generated", "docs",
                                                "extra"}
       and all(_w1409_re.findall(_W1409_PATH_RE, _cmd) for _n, _cmd in _W1409_REQUIRED)
       and set(_W1409_STAGES) >= {"scripts/check_lint.sh", "scripts/selftest.py",
                                  "scripts/secret_inventory.py", "scripts/check_generated.sh",
                                  "scripts/check_docs.sh", "scripts/check_template_sync.sh",
                                  ".veldo/validate.py", ".veldo/shape_gate.py",
                                  ".veldo/events.py"}
       and _W1409_GATE_CLOSURE > set(_W1409_STAGES)
       and sorted(_W1409_GATE_TEXTS) == sorted(_W1409_GATE_CLOSURE)
       and ".veldo/validate_checks.py" in _W1409_GATE_CLOSURE
       and ".veldo/secret_inventory.py" in _W1409_GATE_CLOSURE)

expect("WARP-1409 AC6: NO GATE STAGE CONSUMES THIS MODULE'S OUTPUT. The string cost_to_change "
       "appears in NONE of the files in the derived gate closure asserted above, so nothing the "
       "gate runs can fail because a per-area cost map was unavailable, malformed or slow, and a "
       "repository that never calls it is byte-identically unaffected. THE ONE STAGE THAT DOES "
       "LOAD THE MODULE IS NAMED RATHER THAN GLOSSED: scripts/selftest.py is a required stage "
       "(CHECK_unit) and it executes this fragment, which loads the module under test. That is a "
       "test dependency and not a consumer - a suite fragment asserting a module's behaviour is "
       "the opposite of a gate stage trusting its numbers - and it is bounded here rather than "
       "assumed, by requiring that THIS FILE is the only suite fragment in the repository that "
       "names the module at all. So a second fragment starting to read the report, or any stage "
       "implementation acquiring it, reds this",
       "cost_to_change" not in "".join(_W1409_GATE_TEXTS.values())
       and "scripts/selftest.py" in _W1409_STAGES
       and sorted(p.name for p in (ROOT / "scripts/suites").glob("*.py")
                  if "cost_to_change" in p.read_text())
       == ["15_warp_1409_cost_to_change_per_area.py"])

# -----------------------------------------------------------------------------------
# AC8. ONE GIT READER. The stand-down needs the PATHS git says a change touched, and the
# corpus record needs their COUNT; both now come from toe_corpus.git_touched, so the second
# `git log --grep` this item would otherwise have spelled out does not exist.
# -----------------------------------------------------------------------------------
_W1409_REAL_SPEC = "WARP-1401"
_w1409_touched = _W1409TC.git_touched(_W1409_REAL_SPEC)
_w1409_counted = _W1409TC.files_touched(_W1409_REAL_SPEC)
expect("WARP-1409 AC8: toe_corpus.files_touched COUNTS EXACTLY WHAT git_touched READS, driven "
       "over a real spec id in this repository's own history. Its returned keys are unchanged "
       "(commits and files_touched) so the WARP-1401 corpus record is byte-identical to before, "
       "and each count equals the length of the corresponding list, which is what makes the two "
       "views of one git read impossible to drift apart",
       sorted(_w1409_counted) == ["commits", "files_touched"]
       and _w1409_counted["commits"] == len(_w1409_touched["commits"])
       and _w1409_counted["files_touched"] == len(_w1409_touched["files"])
       and _w1409_touched["files"] == sorted(_w1409_touched["files"]))

# SPLIT (WARP-1711): the ABSENT half - a spec id no commit names answers with empty lists and zero
# counts rather than an exception - is a fact about the reader and runs everywhere. The NON-EMPTY
# half needs a commit that names a real spec id, which a flattened successor does not have: its one
# commit names no spec at all, so the reader honestly reads nothing and the pair cannot be taken.
expect("WARP-1409 AC8: a spec id NO commit names yields empty lists and zero counts rather than an "
       "exception, on both views of the one git read",
       _W1409TC.git_touched("WARP-0000-nothing-names-this")
       == {"commits": [], "files": []}
       and _W1409TC.files_touched("WARP-0000-nothing-names-this")
       == {"commits": 0, "files_touched": 0})
if not no_history([("the commits naming %s" % _W1409_REAL_SPEC,
                    _w1409_touched["commits"] and _W1409_REAL_SPEC)],
                  "the NON-EMPTY half of the git-reader control",
                  "The ABSENT half - a spec id no commit names answering with empty lists and zero "
                  "counts rather than raising - is SPLIT OUT and still runs here, immediately above, "
                  "and the COUNT-EQUALS-THE-READ assertion above it holds over whatever this "
                  "repository's history does name.", "WARP-1409 AC8"):
    expect("WARP-1409 AC8 NEGATIVE CONTROL: a spec id NO commit names yields empty lists and zero "
       "counts rather than an exception, and the real spec id above yields a NON-EMPTY read. The "
       "pair is what proves the reader is reading git at all: without the non-empty half, an "
       "implementation that always returned nothing would satisfy the absent case and quietly "
       "make every git-path attribution in the repository unattributed",
       _W1409TC.git_touched("WARP-0000-nothing-names-this")
       == {"commits": [], "files": []}
       and _W1409TC.files_touched("WARP-0000-nothing-names-this")
       == {"commits": 0, "files_touched": 0}
       and _w1409_touched["files"] != [] and _w1409_touched["commits"] != [])

# -----------------------------------------------------------------------------------
# The rendered text is drawn from the report, so a reader and a JSON consumer cannot see two
# different numbers. Checked on the mixed fixture and on a stand-down.
# -----------------------------------------------------------------------------------
_w1409_text = _W1409.render_text(_w1409_rep)
expect("WARP-1409 AC2: THE RENDERED TEXT CARRIES THE GIT-PATH WARNING AND THE SAME FIGURES THE "
       "JSON DOES, drawn from the report rather than recomputed, so the human surface and the "
       "machine surface cannot disagree. A stand-down renders one honest line naming the reason "
       "instead of an empty table that reads like a repository with no cost",
       "BY GIT PATH" in _w1409_text
       and ("records %d" % _w1409_rep["coverage"]["records"]) in _w1409_text
       and "area alpha" in _w1409_text and "tokens=None" in _w1409_text
       and "standing down" in _W1409.render_text(_w1409_sd_records))

# -----------------------------------------------------------------------------------
# THE REAL REPOSITORY, THROUGH repo_report(), ONCE. Everything above drives the pure core over
# fixtures or the wiring over a stub; this is the function the CLI runs and the source of every
# figure the spec publishes. The invariants asserted here are ones that hold however the corpus
# grows, so they cannot rot into a red: a set equality against an independently built corpus, the
# partition identity, and the two honesty gaps as they actually read today.
# -----------------------------------------------------------------------------------
_w1409_mspec = importlib.util.spec_from_file_location("w1409_metrics", ROOT / ".veldo/metrics.py")
_W1409M = importlib.util.module_from_spec(_w1409_mspec)
_w1409_mspec.loader.exec_module(_W1409M)
_w1409_pspec = importlib.util.spec_from_file_location("w1409_policy_check",
                                                     ROOT / ".veldo/policy_check.py")
_W1409PC = importlib.util.module_from_spec(_w1409_pspec)
_w1409_pspec.loader.exec_module(_W1409PC)

# The error is CAPTURED rather than allowed to abort, for the same reason as in the wired block: a
# raise here would take every assertion below it with it, and a mutation that silently deletes
# coverage is the failure mode this suite exists to rule out. Every live assertion reads the error
# FIRST, so an exception reds by name and the assertions after it still run.
try:
    _W1409_LIVE = _W1409.repo_report()
    _W1409_LIVE_ERR = ""
except BaseException as _w1409_live_exc:                                       # noqa: BLE001
    _W1409_LIVE = {"areas": {}, "attribution": {_b: 0 for _b in _W1409.BASES},
                   "coverage": {"records": -1}, "unattributed": {"specs": []}}
    _W1409_LIVE_ERR = "%s: %s" % (type(_w1409_live_exc).__name__, _w1409_live_exc)
# The corpus built INDEPENDENTLY of repo_report, from the same three readers it names, so the
# comparison below is a set equality between two derivations and not a count against itself.
_W1409_LIVE_CORPUS = _W1409TC.build(specs_dir=ROOT / "specs", events=_W1409M.load(),
                                    protected=_W1409PC.protected_patterns())
_w1409_live_members = {m["spec"]: m["basis"] for _a in _W1409_LIVE["areas"].values()
                       for m in _a["members"]}
_w1409_live_areas_of = {}
for _an, _a in _W1409_LIVE["areas"].items():
    for _m in _a["members"]:
        _w1409_live_areas_of.setdefault(_m["spec"], set()).add(_an)

expect("WARP-1409 AC1 AND AC3 OVER THE REAL REPOSITORY: repo_report() AGGREGATES THE WHOLE ACTUALS "
       "CORPUS AND PARTITIONS IT, asserted as a SET EQUALITY against a corpus built independently "
       "from the same three readers (toe_corpus.build over metrics.load and "
       "policy_check.protected_patterns) rather than as one count compared with itself. Every spec "
       "in the live corpus is in an area or in the unattributed list, never both and never neither; "
       "the three attribution counts sum to coverage.records; and the DECLARED-PLACEMENT JOIN IS "
       "NON-EMPTY, with the named pair that makes the basis a measurement in the live map rather "
       "than a constant: WARP-1401, which declares placement metrics, comes back basis 'placement' "
       "in the metrics area, and WARP-0100, the first spec in this repository and one that declares "
       "no placement at all, comes back unattributed. Blinding the front-matter lookup in the "
       "wiring - the mutation that used to leave this suite at 30 passed - moves all 66 of those "
       "declarations out of 'placement' and reds this",
       _W1409_LIVE_ERR == ""
       and set(_w1409_live_members) | set(_W1409_LIVE["unattributed"]["specs"])
       == {r["spec"] for r in _W1409_LIVE_CORPUS}
       and set(_w1409_live_members) & set(_W1409_LIVE["unattributed"]["specs"]) == set()
       and sum(_W1409_LIVE["attribution"][b] for b in _W1409.BASES)
       == _W1409_LIVE["coverage"]["records"] == len(_W1409_LIVE_CORPUS)
       and _W1409_LIVE["attribution"][_W1409.BY_PLACEMENT] > 0
       and _w1409_live_members.get(_W1409_REAL_SPEC) == _W1409.BY_PLACEMENT
       and "metrics" in _w1409_live_areas_of.get(_W1409_REAL_SPEC, set())
       and "WARP-0100" in _W1409_LIVE["unattributed"]["specs"])

# -----------------------------------------------------------------------------------
# THE TWO HONESTY GAPS OVER THE LIVE MAP, ASSERTED AGAINST WHAT THE CORPUS RECORDS RATHER THAN
# AGAINST THE FACT THAT NOBODY HAS RECORDED ANYTHING YET.
#
# WHAT WAS WRONG HERE, AND IT WAS A LANDMINE RATHER THAN A CHECK. This assertion used to read "Not
# one record in this repository's corpus carries spend, so every cost field of every area is None"
# and it asserted exactly that: usable_as_cost_ground_truth false, the cost notice present, every
# area's cost None. None of those is a property of the module. All three are properties of nobody
# having used .veldo/spend.py yet, and the module exists to be used. Proven in a scratch copy of
# this repository, from a clean 38 passed 0 failed:
#     python3 .veldo/spend.py record --spec WARP-0100 --basis harness_reported --tokens 750000
# which is the sanctioned writer doing the one thing it is for, left the suite at 37 passed 1
# FAILED - this assertion. A gate that reds on the first legitimate use of the feature it guards is
# worse than a missing check, because it teaches whoever hits it that the gate is noise, and the
# person who hits it is whoever first records spend.
#
# THE SHAPE THAT KEEPS THE TEETH WITHOUT PINNING TODAY'S EMPTINESS: every per-area figure is
# asserted EQUAL TO AN EXPECTATION DERIVED FROM THE INDEPENDENTLY BUILT CORPUS above - the same
# corpus the partition set equality uses - and the derivation is written HERE rather than borrowed
# from the module under test, so both sides cannot move together. A signal that reached none of an
# area's records must read None; a signal that reached some of them must read the real sum over
# exactly those records. That covers today's all-None map as an OUTPUT of the measurement and a
# recorded map the same way, and it reds in BOTH directions: a confident zero where nothing was
# recorded, and a None (or a wrong sum) where something was.
#
# ONLY THE ARM THAT SPEAKS ABOUT AN ABSENCE IS BRANCHED - the notices, and the None the human
# surface prints - and the branch is chosen by what this run just measured, so recording spend MOVES
# the assertion to its other arm instead of reding it. The structural invariants (the basis agreeing
# with the count, the coverage arithmetic, the text carrying the JSON's own figures, the review half
# being a real number) stay unconditional.
# -----------------------------------------------------------------------------------
_w1409_live_text = _W1409.render_text(_W1409_LIVE) if _W1409_LIVE_ERR == "" else ""


def _w1409_gate_signal(cycles):
    """Whether ONE corpus record carried a gate-cycle signal, spelled out here rather than taken
    from the module under test: sharing its _has_cycle_signal would move both sides of every
    comparison below together, and an equality that moves with the mutation cannot catch it."""
    return any(isinstance(cycles.get(_f), (int, float)) and not isinstance(cycles.get(_f), bool)
               and cycles[_f] > 0 for _f in _W1409.GATE_CYCLE_FIELDS)


# The two signals as the INDEPENDENT corpus reports them: which specs recorded spend, and which
# carried a gate event that reached them. Empty today; both are read rather than assumed.
_w1409_live_spend_of = {_r["spec"]: _r["spend"] for _r in _W1409_LIVE_CORPUS
                        if isinstance(_r.get("spend"), dict)
                        and _r["spend"].get("spend_recorded") is True}
_w1409_live_cycles_of = {_r["spec"]: _r["cycles"] for _r in _W1409_LIVE_CORPUS
                         if isinstance(_r.get("cycles"), dict)}
_w1409_live_gate_specs = {_s for _s, _c in _w1409_live_cycles_of.items()
                          if _w1409_gate_signal(_c)}


def _w1409_live_expect_area(area):
    """The cost and gate figures ONE live area MUST report, derived from the independent corpus:
    the sum over that area's own members for a signal at least one of them carried, and None for a
    signal none of them carried. That is the module's STATED rule, restated here over independently
    read data, which is what makes the comparison evidence rather than a tautology."""
    _members = [_m["spec"] for _m in _W1409_LIVE["areas"][area]["members"]]
    _spent = [_s for _s in _members if _s in _w1409_live_spend_of]
    _gated = [_s for _s in _members if _s in _w1409_live_gate_specs]
    _cost = {}
    for _f in _W1409.COST_FIELDS:
        if not _spent:
            _cost[_f] = None
            continue
        _total = sum(_w1409_live_spend_of[_s].get(_f, 0) for _s in _spent)
        _cost[_f] = round(float(_total), 6) if _f == "cost_usd" else _total
    _gate = {_f: (sum(_w1409_live_cycles_of.get(_s, {}).get(_f, 0) for _s in _members)
                  if _gated else None)
             for _f in _W1409.GATE_CYCLE_FIELDS}
    return {"spend_known": len(_spent), "cost": _cost,
            "gate_events_known": len(_gated), "gate": _gate}


def _w1409_live_area_ok(area):
    """One live area's cost and gate blocks against that expectation. None-ness is compared
    EXPLICITLY as well as by value, because the two lies this must catch are opposite: a confident
    zero where the corpus recorded nothing, and a None where it recorded something."""
    _a = _W1409_LIVE["areas"][area]
    _e = _w1409_live_expect_area(area)
    _c, _cost = _a["cycles"], _a["cost"]
    if (_cost["spend_known"] != _e["spend_known"]
            or _cost["cost_known"] is not bool(_e["spend_known"])
            or _cost["cost_basis"] != ("recorded" if _e["spend_known"] else "unrecorded")
            or _cost["spend_coverage"] != round(_e["spend_known"] / _a["records"], 4)):
        return False
    if (_c["gate_events_known"] != _e["gate_events_known"]
            or _c["gate_basis"] != ("recorded" if _e["gate_events_known"] else "unrecorded")
            or _c["gate_coverage"] != round(_e["gate_events_known"] / _a["records"], 4)):
        return False
    for _fields, _key, _got in ((_W1409.COST_FIELDS, "cost", _cost),
                                (_W1409.GATE_CYCLE_FIELDS, "gate", _c)):
        for _f in _fields:
            if (_got[_f] is None) is not (_e[_key][_f] is None) or _got[_f] != _e[_key][_f]:
                return False
    # AND THE HUMAN SURFACE CANNOT PRINT A FIGURE THE JSON DOES NOT CARRY: both blocks are asserted
    # as the exact substrings render_text builds from THIS report, so a None rendered as 0 reds here
    # whichever arm the repository is on.
    return (("tokens=%s cost_usd=%s human_minutes=%s (%s,"
             % (_cost["tokens"], _cost["cost_usd"], _cost["human_minutes"],
                _cost["cost_basis"])) in _w1409_live_text
            and ("gate_passes=%s gate_failures=%s (%s,"
                 % (_c["gate_passes"], _c["gate_failures"], _c["gate_basis"]))
            in _w1409_live_text)


expect("WARP-1409 AC4 OVER THE REAL REPOSITORY: THE TWO GAPS ARE NUMBERS IN THE LIVE MAP AND NOT "
       "PROSE IN THE SPEC, AND EACH NUMBER IS ASSERTED AGAINST AN EXPECTATION DERIVED FROM THE "
       "INDEPENDENTLY BUILT CORPUS RATHER THAN AGAINST TODAY'S EMPTINESS. Per area: spend_known, "
       "gate_events_known and both coverage ratios equal the count of that area's own members that "
       "carried the signal; cost_basis and gate_basis are 'recorded' exactly when that count is "
       "positive; every cost field and every gate-cycle field equals the sum over exactly those "
       "members, and is None when none of them carried it - so a confident zero reds and so does a "
       "None over recorded data; and the rendered text carries the report's own figures for both "
       "blocks, so the human surface cannot show a number the JSON does not. The corpus-level "
       "booleans and notices AGREE WITH THE COUNTS: cost_known_records and gate_event_records equal "
       "the independently derived sets, usable_as_cost_ground_truth and "
       "usable_as_rework_ground_truth are true exactly when those sets are non-empty, and each "
       "notice is present exactly when its set is empty. Review verdicts are real: at least one "
       "area reports a positive verdict count with review_basis 'recorded', which keeps an "
       "unrecorded signal an absence of ONE signal rather than a module that reports nothing",
       _W1409_LIVE_ERR == ""
       and _W1409_LIVE["coverage"]["cost_known_records"] == len(_w1409_live_spend_of)
       and (_W1409_LIVE["coverage"]["usable_as_cost_ground_truth"]
            is bool(_w1409_live_spend_of))
       and ("cost_notice" in _W1409_LIVE) is (not _w1409_live_spend_of)
       and _W1409_LIVE["coverage"]["gate_event_records"] == len(_w1409_live_gate_specs)
       and (_W1409_LIVE["coverage"]["usable_as_rework_ground_truth"]
            is bool(_w1409_live_gate_specs))
       and ("cycle_notice" in _W1409_LIVE) is (not _w1409_live_gate_specs)
       and all(_w1409_live_area_ok(_a) for _a in _W1409_LIVE["areas"])
       # The basis is read FIRST and the count second, in that order: when the basis is
       # 'unrecorded' the count is None, and a comparison against None would raise TypeError -
       # which is a crash rather than a red, and a suite that crashes reports nothing.
       and any(a["cycles"]["review_basis"] == "recorded" and a["cycles"]["review_verdicts"] > 0
               for a in _W1409_LIVE["areas"].values()))

# THE COST ARM, chosen by what the run just measured. An assertion over the live repository may
# require the honest stand-down when nothing is recorded and the recorded reading when something is.
# What it must never do - what it did until this remediation - is require the recorded set to be
# EMPTY.
if _w1409_live_spend_of:
    expect("WARP-1409 AC4 OVER THE REAL REPOSITORY, THE RECORDED COST ARM: %d record(s) in this "
           "repository's corpus carry spend, so the live map reports them AS NUMBERS and drops the "
           "stand-down - usable_as_cost_ground_truth true and no cost_notice - and NOTHING "
           "RECORDED IS SILENTLY DROPPED: every spec that recorded spend is in an area or in the "
           "unattributed list, every area holding one reports cost_basis 'recorded' with a real "
           "tokens figure, and no area's spend_known exceeds the corpus count"
           % len(_w1409_live_spend_of),
           _W1409_LIVE_ERR == ""
           and _W1409_LIVE["coverage"]["usable_as_cost_ground_truth"] is True
           and "cost_notice" not in _W1409_LIVE
           and all(_s in _w1409_live_areas_of
                   or _s in set(_W1409_LIVE["unattributed"]["specs"])
                   for _s in _w1409_live_spend_of)
           and all(_W1409_LIVE["areas"][_a]["cost"]["cost_basis"] == "recorded"
                   and _W1409_LIVE["areas"][_a]["cost"]["tokens"] is not None
                   for _s in _w1409_live_spend_of
                   for _a in _w1409_live_areas_of.get(_s, ()))
           and all(_a["cost"]["spend_known"] <= len(_w1409_live_spend_of)
                   for _a in _W1409_LIVE["areas"].values()))
else:
    expect("WARP-1409 AC4 OVER THE REAL REPOSITORY, THE COST STAND-DOWN ARM: not one record in "
           "this repository's corpus carries spend AS READ ON THIS RUN, so every cost field of "
           "every area is None with cost_basis 'unrecorded' rather than a confident zero, the "
           "report carries the cost notice naming .veldo/spend.py, and the rendered text prints "
           "tokens=None. THIS IS AN ARM AND NOT AN INVARIANT: the first `.veldo/spend.py record` "
           "moves this to the recorded arm instead of reding it, which is what the emptiness "
           "assertion this replaced could not do",
           _W1409_LIVE_ERR == ""
           and _W1409_LIVE["coverage"]["usable_as_cost_ground_truth"] is False
           and ".veldo/spend.py" in _W1409_LIVE.get("cost_notice", "")
           and all(a["cost"][f] is None for a in _W1409_LIVE["areas"].values()
                   for f in _W1409.COST_FIELDS)
           and all(a["cost"]["cost_basis"] == "unrecorded"
                   for a in _W1409_LIVE["areas"].values())
           and "tokens=None" in _w1409_live_text)

# THE GATE ARM, the same shape over the other signal. Its writer is not spend.py but verify.sh
# learning to name the spec its run belongs to (out of scope for this item and named as such in the
# notice), so this arm flips the day that emitter changes rather than reding.
if _w1409_live_gate_specs:
    expect("WARP-1409 AC4 OVER THE REAL REPOSITORY, THE RECORDED GATE ARM: %d record(s) in this "
           "repository's corpus carry a gate pass or a gate failure, so the live map reports the "
           "rework half AS NUMBERS - usable_as_rework_ground_truth true and no cycle_notice - and "
           "every spec whose gate events reached it is in an area reporting gate_basis 'recorded' "
           "with real gate_passes and gate_failures figures, or in the unattributed list"
           % len(_w1409_live_gate_specs),
           _W1409_LIVE_ERR == ""
           and _W1409_LIVE["coverage"]["usable_as_rework_ground_truth"] is True
           and "cycle_notice" not in _W1409_LIVE
           and all(_s in _w1409_live_areas_of
                   or _s in set(_W1409_LIVE["unattributed"]["specs"])
                   for _s in _w1409_live_gate_specs)
           and all(_W1409_LIVE["areas"][_a]["cycles"]["gate_basis"] == "recorded"
                   and _W1409_LIVE["areas"][_a]["cycles"]["gate_passes"] is not None
                   and _W1409_LIVE["areas"][_a]["cycles"]["gate_failures"] is not None
                   for _s in _w1409_live_gate_specs
                   for _a in _w1409_live_areas_of.get(_s, ())))
else:
    expect("WARP-1409 AC4 OVER THE REAL REPOSITORY, THE GATE STAND-DOWN ARM: not one gate.passed "
           "or gate.failed event reaches a record AS READ ON THIS RUN - the emitter writes a "
           "commit and no spec id or correlation id - so gate_passes and gate_failures are None "
           "for EVERY area with gate_basis 'unrecorded', usable_as_rework_ground_truth is false, "
           "the report carries the cycle notice NAMING THE EMITTER, and the rendered text prints "
           "gate_passes=None. THIS IS AN ARM AND NOT AN INVARIANT: the day verify.sh names the "
           "spec its run belongs to, this moves to the recorded arm instead of reding",
           _W1409_LIVE_ERR == ""
           and _W1409_LIVE["coverage"]["usable_as_rework_ground_truth"] is False
           and "verify.sh" in _W1409_LIVE.get("cycle_notice", "")
           and all(a["cycles"][f] is None for a in _W1409_LIVE["areas"].values()
                   for f in _W1409.GATE_CYCLE_FIELDS)
           and all(a["cycles"]["gate_basis"] == "unrecorded"
                   for a in _W1409_LIVE["areas"].values())
           and "gate_passes=None" in _w1409_live_text)

# SPLIT, for the same reason WARP-1711 split the git-reader control below: the GIT-PATH half of the
# live wiring needs commits that name a spec id, and this history's one commit names none, so
# git_touched honestly reads nothing for every spec and the live map's git_path count is 0. The half
# that runs everywhere is above (the placement join non-empty, and the partition), and the wiring's
# git-path join is driven behaviourally over the injected loader inside the fixture block, where the
# reader's answer is an input rather than this repository's history.
if not no_history([("the commits naming any spec of the live actuals corpus",
                    _W1409_LIVE["attribution"][_W1409.BY_GIT_PATH] and "live git-path join")],
                  "the LIVE half of the git-path join in repo_report",
                  "The git-path join is proven BEHAVIOURALLY in the wiring assertion above, where "
                  "the touched-paths reader is injected and severing it moves a record out of its "
                  "area, and the placement join plus the whole-corpus partition are asserted over "
                  "this repository's own live map immediately above.", "WARP-1409 AC2"):
    expect("WARP-1409 AC2 OVER THE REAL REPOSITORY: BOTH JOINS ARE NON-EMPTY IN THE LIVE MAP, so "
           "neither lookup in the wiring can be severed without a red. The git-path count is "
           "positive, the report carries the notice counting those records and the bases entry that "
           "spells the weakness out, and at least one live spec comes back basis 'git_path'",
           _W1409_LIVE["attribution"][_W1409.BY_GIT_PATH] > 0
           and _W1409_LIVE["git_path_attributed"] is True
           and "BY GIT PATH" in _W1409_LIVE.get("notice", "")
           and _W1409.BY_GIT_PATH in _W1409_LIVE["bases"]
           and _W1409.BY_GIT_PATH in set(_w1409_live_members.values()))

# -----------------------------------------------------------------------------------
# THE ENGINE TWINS THE FOOTPRINT DECLARES. Both were asserted by nothing and guarded by
# nothing: scripts/check_template_sync.sh's PAIRS map lists neither, so gutting either engine
# copy left the 1409 suite, the full selftest and the template-sync check all green. It matters
# most for engine/.veldo/toe_corpus.py, which scripts/publish.py does NOT hold back, so the
# engine copy of the git reader this item modified is what an adopter gets.
# -----------------------------------------------------------------------------------
expect("WARP-1409: BOTH MODULES THIS ITEM TOUCHED LAND IN THE ENGINE HOME BYTE-IDENTICALLY "
       "(PLAN-0014 C5), asserted as a byte comparison plus is_file on the engine side so a MISSING "
       "twin reds as loudly as a drifted one. A copy that has drifted is worse than a copy that is "
       "missing: the missing one is obvious and the drifted one ships a different answer, and "
       "engine/.veldo/toe_corpus.py is not on publish.py's hold-back list, so it is the copy an "
       "adopter actually runs. Nothing else in this repository compares either pair",
       (ROOT / "engine/.veldo/cost_to_change.py").is_file()
       and (ROOT / ".veldo/cost_to_change.py").read_bytes()
       == (ROOT / "engine/.veldo/cost_to_change.py").read_bytes()
       and (ROOT / "engine/.veldo/toe_corpus.py").is_file()
       and (ROOT / ".veldo/toe_corpus.py").read_bytes()
       == (ROOT / "engine/.veldo/toe_corpus.py").read_bytes())

del _w1409_cspec, _w1409_tspec, _w1409_mspec, _w1409_pspec, _w1409_re
