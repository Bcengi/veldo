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

TEETH, MEASURED RATHER THAN CLAIMED. Four mutations were driven through .veldo/cost_to_change.py
and every one of them turned assertions here RED, from a clean 30 passed 0 failed:

  1. _sum_cost returning 0 instead of None for an area with no recorded spend: 2 red (the
     unknown-cost assertion and the rendered-text assertion that reads tokens=None).
  2. attribute() stamping BY_PLACEMENT on the git-path case: 4 red. THE INSTRUCTIVE ONE, because
     every per-area TOTAL stayed identical and only the basis assertions caught it, which is
     exactly the failure this item exists to prevent.
  3. attribute() defaulting an unattributable record into the first declared area: 5 red (the
     never-fabricate pair, the partition set equality, the coverage figures and the cycle sums).
  4. front_matter_index returning {} so no placement is ever seen: 6 red.
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
           "assuming every record did",
           _w1409_rep["areas"]["alpha"]["cycles"]["gate_passes"] == 3
           and _w1409_rep["areas"]["alpha"]["cycles"]["gate_failures"] == 6
           and _w1409_rep["areas"]["alpha"]["cycles"]["cycles_known"] == 3
           and _w1409_rep["areas"]["alpha"]["cycles"]["cycles_coverage"] == 1.0)

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
# AC7. THE SEAM TO THE ARCHITECTURE ORGAN IS PROSE, NOT A DEPENDENCY EDGE. Asserted over
# the text of BOTH files, with a positive control so the absence is not passing for a
# trivial reason.
# -----------------------------------------------------------------------------------
_W1409_SRC = (ROOT / ".veldo/cost_to_change.py").read_text()
_W1409_ENTROPY_SRC = (ROOT / ".veldo/entropy.py").read_text()
# THE MODULE'S WHOLE DEPENDENCY SURFACE, enumerated from the source rather than described: every
# sibling it can reach comes through one `_load(name, rel)` call with a literal path, so this
# regex is the complete list of files it can pull in. Asserting the SET makes the absence of
# entropy.py a measurement over a known-non-empty list instead of a grep that would also pass on
# a module that loaded nothing at all.
_W1409_LOADS = sorted(set(_w1409_re.findall(r'_load\("[^"]+",\s*"([^"]+)"\)', _W1409_SRC)))
expect("WARP-1409 AC7: THE CROSS-PLAN SEAM IS SOFT (PLAN-0014 C6), ASSERTED AS THE MODULE'S WHOLE "
       "DEPENDENCY SURFACE. Every sibling .veldo/cost_to_change.py can reach arrives through a "
       "_load call with a literal path, and that set is exactly validate, toe_corpus, metrics and "
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
# AC6. NOTHING IN THE GATE CALLS THIS MODULE, which is what makes "a repository that never
# uses it is byte-identically unaffected" a property rather than a promise.
# -----------------------------------------------------------------------------------
_W1409_GATE_FILES = ["scripts/verify.sh", "scripts/check_lint.sh", "scripts/check_docs.sh",
                     "scripts/check_generated.sh", "scripts/check_template_sync.sh",
                     ".veldo/validate.py", ".veldo/validate_checks.py", ".veldo/shape_gate.py",
                     ".veldo/policy_check.py"]
_w1409_gate_texts = {f: (ROOT / f).read_text() for f in _W1409_GATE_FILES}
expect("WARP-1409 AC6: NO GATE STAGE INVOKES THIS MODULE. The string cost_to_change appears in "
       "none of the nine files the gate actually runs, so nothing can fail because a per-area "
       "cost map was unavailable, malformed or slow, and a repository that never calls it is "
       "byte-identically unaffected. POSITIVE CONTROL: the same scan over the same files DOES "
       "find shape_gate.py inside scripts/verify.sh, so it is capable of finding a wiring that "
       "exists. BOUND to the length of its own file list, so emptying that list reds this",
       len(_w1409_gate_texts) == len(_W1409_GATE_FILES) == 9
       and all("cost_to_change" not in t for t in _w1409_gate_texts.values())
       and "shape_gate.py" in _w1409_gate_texts["scripts/verify.sh"])

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

del _w1409_cspec, _w1409_tspec, _w1409_re
