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
every git-path attribution and then every declared-placement attribution. It is now driven three
ways - over an INJECTED LOADER with known inputs, over a THROWAWAY GIT REPOSITORY this file builds
(its own contract, its own specs, its own event log, its own commits), and over the REAL repository,
where the whole-corpus partition is a set equality against an independently built corpus.

NOTHING IN THIS FILE STANDS DOWN ANY MORE, and the two legs that did are the reason the fixture
repository exists. Both were routed through shared.no_history with a PROSE SENTENCE where the
mechanism wants a module path, and history_begins_with answers True for a non-path in EVERY
repository, so the guard that separates an honestly absent input from a BROKEN READER could not
fail: gutting toe_corpus.git_touched, the one reader both depended on, left this file green. The
readers now take a `root` - a seam _run already had - and are driven over a tree with real commits,
so both legs run everywhere and neither is traded for an unknown gap.

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

AND SIX MORE, DRIVEN AGAINST THIS REVISION FOR THE FINDINGS AN INDEPENDENT REVIEW RAISED AFTERWARDS.
Each was applied to BOTH twins, diffed to prove it landed, and reverted; each reddened the row named
here and no other, and the additive controls stayed green. Every one of the six was GREEN before this
revision, which is the whole reason they are recorded rather than described.

 14. `usable_as_cost_ground_truth` computed over the whole corpus again instead of over the records
     that reached an area: 1 red, the recorded-spend-on-a-spec-no-area-holds row. It reds ONE row and
     that is worth stating plainly: the live rows cannot see this mutation, because nothing in this
     repository has recorded spend yet, which is exactly why the state is driven from a FIXTURE.
 15. the unattributed bucket's `cost` and `cycles` blocks dropped: 10 red, and no coverage lost (67
     passed 10 failed against a 77-row baseline). The 750000 recorded tokens are then in no figure
     anywhere in the report. THE FIRST VERSION OF THIS MEASUREMENT WAS WORTH LESS THAN IT LOOKED: the
     rows indexed the blocks directly, so the mutation raised KeyError at module scope, reddened one
     row and DELETED every row below it - ledger 67's weaker assertion exactly. The reads go through
     _w1409_dig and _w1409_render now, and the same mutation reds ten NAMED rows with the run intact.
 16. `git_touched` gutted to empty lists: 3 red (the fixture count-equals-the-read row, the
     fixture-tree wiring row and the housekeeping row that requires the fixture read to be
     non-empty). It was green in EVERY repository before the fixture existed.
 17. `files_touched` replaced by hardcoded zeros: 1 red, the fixture count-equals-the-read row. A
     wrong number in every one of the 174 corpus records this plan trains on, and green before.
 18. one line in `report()` writing a file under ROOT: 2 red (the tree-inventory row and its own
     additive control, whose planted-write diff is no longer exactly the planted path). The exact
     mutation a review applied while this file stayed at 40 passed.
 19. repo_report's default loader bound to ROOT instead of to the root it was given: 2 red (the
     loader-binding row and the fixture-tree row, the second because the event stream, the git
     history and the protected patterns then come from this repository instead of from the tree
     under report).

AND THE TWO ADDITIVE CONTROLS, which must red ONE row each and leave every other row green, because a
control that ADDS something and reds the whole file proves nothing about what it added:
 A1. a second problem spelling behind check_corpus: 1 red, the two-surfaces-one-enumeration row.
 A2. an importlib load of this module inserted into scripts/secret_inventory.py, a REQUIRED gate
     stage: 1 red, the no-gate-stage-consumes-it row.

ALL EIGHT FALSIFICATIONS THE SPEC DECLARES WERE ALSO RE-DRIVEN AGAINST THIS REVISION, each reddening
the rows its own field names: AC1 10 red, AC2 7, AC3 11, AC4 (cost) 4, AC4 (gate cycles) 4, AC5 3,
AC6 2, AC7 4, AC8 3.

AND ONE OF THOSE LIVE ASSERTIONS WAS A LANDMINE RATHER THAN A CHECK, fixed here. AC4 over the real
repository asserted that NO record carries spend - today's emptiness written as a required invariant -
so it stayed green exactly as long as nobody used .veldo/spend.py and reddened the moment somebody
did. Measured in a scratch copy: from 38 passed 0 failed, one sanctioned
`python3 .veldo/spend.py record --spec WARP-0100 --basis harness_reported --tokens 750000` left it at
37 passed 1 FAILED. It is now asserted against an expectation DERIVED from the independently built
corpus, per area and per signal, with only the arm that speaks about an absence branched on what the
run just measured. The teeth were re-measured with the spend recorded: `_sum_cost` returning 0
instead of None for a set that recorded nothing reds the derived assertion, which is the confident
zero this criterion exists to refuse. The live block is 4 assertions rather than 1. A clean run of
this fragment is 51 passed 0 failed at this revision; mutations 1 to 13 were counted at the 40-row
revision and 14 to 19 at this one, which is why the two sets of counts are labelled separately rather
than restated as one number nobody re-measured.
"""
import hashlib as _w1409_hashlib
import os as _w1409_os
import re as _w1409_re
import shutil as _w1409_shutil
import subprocess as _w1409_subprocess
import sys as _w1409_sys

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


# -----------------------------------------------------------------------------------
# THE FIXTURE REPOSITORY. A THROWAWAY GIT TREE WITH ONE COMMIT NAMING A SPEC, WHICH IS THE SEAM TWO
# PROPERTIES OF THIS ITEM CANNOT BE ASKED ABOUT WITHOUT.
#
# This repository's history is flattened: its one root commit names no spec id, so
# toe_corpus.git_touched honestly reads nothing for every spec and BOTH of its views read 0. A review
# measured what that costs: `files_touched` replaced by hardcoded zeros, and `git_touched` gutted to
# empty lists, EACH left this suite at 40 passed 0 failed - and that dict is the `git` block of every
# one of the 174 corpus records the whole plan trains on. The two legs were routed through
# shared.no_history with a PROSE SENTENCE where the mechanism wants a module path, and
# history_begins_with answers True for a non-path in every repository forever, so the guard that
# separates an absent input from a BROKEN READER could not fail either.
#
# A property only a differently shaped tree can exhibit needs a SEAM to be asked about that tree
# (ledger 60), and the seam existed: `toe_corpus._run(args, cwd=None)` already took the working
# directory and only these two callers did not pass it. So both readers now take a `root`, this tree
# is built with real commits, and BOTH STAND-DOWNS ARE GONE: every leg below runs everywhere, with no
# dependence on what this repository's own history happens to name.
#
# The tree is also a whole REPOSITORY rather than a bare git directory, because the same fixture
# answers the other question a review left open: whether repo_report(root=X) honours X for EVERY
# input or only for the two it reads directly.
# -----------------------------------------------------------------------------------
_W1409_FIXTURE_SPEC = """---
schema: veldo.spec/v1
id: %s
title: %s
status: shipped
risk: standard
owner: selftest
%sacceptance_criteria:
  - id: AC1
    text: observable.
rollback: git revert
---
body
"""
# The events the fixture tree's OWN log carries. Not one of these ids appears in this repository's
# log, which is what makes reading them back proof that the event stream came from the fixture.
_W1409_FIXTURE_EVENTS = [
    dict({"schema": "veldo.event/v1", "id": "w1409fixture%d" % _i,
          "at": "2026-01-01T00:00:0%dZ" % _i, "producer": "selftest",
          "spec_id": "WARP-9451", "type": _t}, **_x)
    for _i, (_t, _x) in enumerate([
        ("spec.shipped", {"tokens": 4321, "cost_usd": 2.5, "human_minutes": 9}),
        ("gate.passed", {}), ("gate.failed", {}), ("verdict.recorded", {})])]
_W1409_FIXTURE_REPO = Path(tempfile.mkdtemp(prefix="w1409-fixture-repo-"))


def _w1409_git(*args):
    """One git command in the fixture repository, with an identity supplied on the command line so
    the fixture never depends on this machine's git configuration."""
    return _w1409_subprocess.run(
        ["git", "-C", str(_W1409_FIXTURE_REPO), "-c", "user.name=selftest",
         "-c", "user.email=selftest@veldo.invalid"] + list(args),
        capture_output=True, text=True, check=True)


(_W1409_FIXTURE_REPO / "specs").mkdir()
# The whole estimation layer, because repo_report(root=X) derives X's map with X's OWN organs: that
# is how the event stream, the git history and the protected patterns come from X rather than from
# wherever this file lives.
_w1409_shutil.copytree(ROOT / ".veldo", _W1409_FIXTURE_REPO / ".veldo",
                       ignore=_w1409_shutil.ignore_patterns("__pycache__"))
(_W1409_FIXTURE_REPO / "specs" / "WARP-9451-placed.md").write_text(
    _W1409_FIXTURE_SPEC % ("WARP-9451", "fixture spec declaring where it lands",
                           'placement: [metrics]\nfootprint:\n  - ".veldo/metrics.py"\n'))
(_W1409_FIXTURE_REPO / "specs" / "WARP-9452-unplaced.md").write_text(
    _W1409_FIXTURE_SPEC % ("WARP-9452", "fixture spec declaring no placement at all", ""))
(_W1409_FIXTURE_REPO / ".veldo" / "events.jsonl").write_text(
    "\n".join(json.dumps(_e, sort_keys=True) for _e in _W1409_FIXTURE_EVENTS) + "\n")
_w1409_git("init", "-q")
_w1409_git("add", "-A")
# The seed commit names NO spec id on purpose: the reader must find the ONE commit that does.
_w1409_git("commit", "-q", "-m", "seed the fixture tree")
(_W1409_FIXTURE_REPO / ".veldo" / "dashboard.py").write_text(
    (_W1409_FIXTURE_REPO / ".veldo" / "dashboard.py").read_text() + "\n# fixture edit\n")
_w1409_git("add", "-A")
_w1409_git("commit", "-q", "-m",
           "WARP-9452: the change this fixture attributes by git path")


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


def _w1409_dig(obj, *keys):
    """A nested read that returns None for an ABSENT key instead of raising, used for every read of
    a block this remediation added.

    A row that indexes a key straight out of a report turns a mutation which DELETES that key into a
    KeyError at module scope, and that takes every assertion below it with it: the evidence then reads
    "something went red and the run got shorter", which is exactly what a mutation deleting coverage
    produces and exactly what ledger 67 records as the weaker assertion. Read through here, the same
    mutation reds the row that NAMES the missing figure and nothing else."""
    for _k in keys:
        if not isinstance(obj, dict) or _k not in obj:
            return None
        obj = obj[_k]
    return obj


def _w1409_render(rep):
    """The rendered text for one report, or "" when rendering RAISES. Same reason as _w1409_dig: the
    text surface reads figures the report is required to carry, so a mutation that removes one of
    them makes render_text raise, and an unhandled raise at module scope would delete every assertion
    below it instead of reddening the rows that name the missing figure. An empty string reds exactly
    those rows."""
    try:
        return _W1409.render_text(rep)
    except BaseException as _e:                                                # noqa: BLE001
        return ""


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
           and "cycle_notice" not in _w1409_rep
           # THE SAME SPLIT ON THE OTHER SIGNAL, in the one fixture that exhibits it: all four
           # records carry gate events and WARP-9404 is attributed to nothing, so 3 of the 4
           # reached an area, the boolean speaks about those 3, and the 4th record's cycles are
           # reported in unattributed.cycles with its own notice rather than in no figure at all.
           and _w1409_rep["coverage"]["gate_attributed_records"] == 3
           and _w1409_rep["coverage"]["gate_unattributed_records"] == 1
           and "unattributed_cycle_notice" in _w1409_rep
           and _w1409_dig(_w1409_rep, "unattributed", "cycles", "gate_passes") == 1
           and _w1409_dig(_w1409_rep, "unattributed", "cycles", "gate_failures") == 2
           and _w1409_dig(_w1409_rep, "unattributed", "cycles", "gate_basis") == "recorded")

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
           "gate_passes=None" in _w1409_render(_w1409_rep_nogate)
           and "gate_failures=None" in _w1409_render(_w1409_rep_nogate)
           and "unrecorded, gate events on 0 of 2" in _w1409_render(_w1409_rep_nogate)
           and "gate_passes=3" in _w1409_render(_w1409_rep)
           and "gate_passes=None" not in _w1409_render(_w1409_rep))

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
           and "cost_notice" not in _w1409_rep_spent
           # AND THE UNATTRIBUTED-SPEND DISCLOSURE IS NOT ALWAYS-ON DECORATION: this record IS
           # attributed, so cost_unattributed_records is 0 and that notice is absent. A warning a
           # reader sees on every report is a warning a reader learns to ignore.
           and _w1409_rep_spent["coverage"]["cost_attributed_records"] == 1
           and _w1409_rep_spent["coverage"]["cost_unattributed_records"] == 0
           and "unattributed_spend_notice" not in _w1409_rep_spent)

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
    # AC4. SPEND RECORDED AGAINST A SPEC NO AREA HOLDS, which is the state ONE
    # `.veldo/spend.py record` produces against any unattributed spec - 108 of this repository's
    # 174 records are unattributed, and WARP-0100, the spec the remediation itself recorded
    # against, is one of them. IT USED TO MAKE THE MAP CONTRADICT ITSELF IN THE DATA: the
    # corpus-level `usable_as_cost_ground_truth` went true while every area still reported
    # tokens None with cost_basis unrecorded, the cost notice that explains those Nones was
    # SUPPRESSED BY THE SAME RECORD, and the recorded tokens appeared in no figure anywhere,
    # because the unattributed bucket carried only records, specs and a reason.
    # THE FIXTURE CARRIES THE STATE, so this is driven in every repository rather than only in
    # one that happens to have recorded spend today - which is the whole reason the live arm
    # below could not see it.
    # -----------------------------------------------------------------------------------
    _w1409_spent_nowhere = _w1409_rec("WARP-9431",
                                      spend={"tokens": 750000, "cost_usd": 0,
                                             "human_minutes": 0, "spend_recorded": True})
    _w1409_rep_nowhere = _W1409.report([_w1409_spent_nowhere], _W1409_CONTRACT, _W1409ARCH,
                                       fm_of=lambda _s: None, paths_of=lambda _s: [])
    _w1409_nowhere_json = json.dumps(_w1409_rep_nowhere, sort_keys=True)
    expect("WARP-1409 AC4: RECORDED SPEND ON A SPEC NO AREA HOLDS IS REPORTED IN A FIGURE, AND THE "
           "HEADLINE BOOLEAN DOES NOT CLAIM COST GROUND TRUTH OVER A MAP WITH NO COST IN IT. The "
           "one record carries 750000 tokens and resolves to no area, so: "
           "usable_as_cost_ground_truth is FALSE because it is a statement about the PER-AREA "
           "figures and no area has one; cost_known_records is 1 while cost_attributed_records is "
           "0 and cost_unattributed_records is 1, so all three facts are readable rather than one "
           "blunt one; the cost notice is STILL PRESENT, because the record that creates the "
           "contradiction must not be the record that removes the disclosure; a second notice "
           "names the recorded-but-unattributed count; and the 750000 tokens are IN THE REPORT, in "
           "unattributed.cost with cost_basis 'recorded', because a figure a reader cannot audit "
           "should not exist. Nothing is spread, split or defaulted into an area to achieve that",
           _w1409_rep_nowhere["unattributed"]["records"] == 1
           and _w1409_rep_nowhere["unattributed"]["specs"] == ["WARP-9431"]
           and _w1409_rep_nowhere["areas"] == {}
           and _w1409_rep_nowhere["coverage"]["cost_known_records"] == 1
           and _w1409_rep_nowhere["coverage"]["cost_attributed_records"] == 0
           and _w1409_rep_nowhere["coverage"]["cost_unattributed_records"] == 1
           and _w1409_rep_nowhere["coverage"]["usable_as_cost_ground_truth"] is False
           and "cost_notice" in _w1409_rep_nowhere
           and "reaches NO per-area figure" in _w1409_rep_nowhere["unattributed_spend_notice"]
           and _w1409_dig(_w1409_rep_nowhere, "unattributed", "cost", "tokens") == 750000
           and _w1409_dig(_w1409_rep_nowhere, "unattributed", "cost", "cost_basis") == "recorded"
           and _w1409_dig(_w1409_rep_nowhere, "unattributed", "cost", "spend_known") == 1
           and "750000" in _w1409_nowhere_json
           and "unattributed cost: recorded, tokens=750000"
           in _w1409_render(_w1409_rep_nowhere))

    _w1409_rep_spend_split = _W1409.report(
        [_w1409_spent, _w1409_spent_nowhere], _W1409_CONTRACT, _W1409ARCH,
        fm_of=lambda _s: None,
        paths_of=lambda _s: [".veldo/alpha.py"] if _s == "WARP-9406" else [])
    expect("WARP-1409 AC4: WITH ONE ATTRIBUTED AND ONE UNATTRIBUTED SPEND RECORD, BOTH FIGURES ARE "
           "REPORTED AND THE UNATTRIBUTED DISCLOSURE SURVIVES THE ARM IT DOES NOT BELONG TO. This "
           "is the case a single notice would have hidden: usable_as_cost_ground_truth is true and "
           "the cost notice is correctly GONE, because alpha does report a real cost - and the "
           "unattributed spend notice is STILL THERE, naming 1 of 2, with the 750000 tokens in "
           "unattributed.cost beside alpha's 1200. Gating the second disclosure on the first would "
           "lose it in exactly the state where a reader is most likely to add the two numbers up",
           _w1409_rep_spend_split["coverage"]["usable_as_cost_ground_truth"] is True
           and "cost_notice" not in _w1409_rep_spend_split
           and _w1409_rep_spend_split["coverage"]["cost_attributed_records"] == 1
           and _w1409_rep_spend_split["coverage"]["cost_unattributed_records"] == 1
           and "1 of the 2 record(s) carrying spend are UNATTRIBUTED"
           in _w1409_rep_spend_split["unattributed_spend_notice"]
           and _w1409_rep_spend_split["areas"]["alpha"]["cost"]["tokens"] == 1200
           and _w1409_dig(_w1409_rep_spend_split, "unattributed", "cost", "tokens") == 750000)

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
           # THE EXCLUSION IS THE MODULE'S OWN ENUMERATION, NOT A LITERAL SET SPELLED OUT HERE.
           # Two spellings of "which keys are conditional" is how a notice gets added to the live
           # report and forgotten in the stand-down, which is the drift this comparison exists to
           # catch, and a literal set here would have to be edited to keep it green - the one edit
           # that turns the check into a record of what happened.
           and set(_w1409_rep) - set(_W1409.CONDITIONAL_KEYS) <= set(_w1409_sd_records)
           and set(_w1409_rep_nowhere) - set(_W1409.CONDITIONAL_KEYS) <= set(_w1409_sd_records)
           # AND THE EXCLUSION SET IS AUDITED RATHER THAN TRUSTED: every key it declares
           # conditional is one a report built in this file ACTUALLY CARRIES, so it cannot become a
           # licence to drop a key from the stand-down by naming it here.
           and set(_W1409.CONDITIONAL_KEYS) <= (
               set(_w1409_rep) | set(_w1409_rep_git) | set(_w1409_rep_nogate)
               | set(_w1409_rep_nowhere))
           and not set(_W1409.CONDITIONAL_KEYS) & set(_w1409_sd_records)
           # The same shape claim ONE LEVEL DOWN, where the coverage figures live: a consumer
           # reading coverage.gate_event_records off a stand-down must not get a KeyError, and a
           # key added to the live coverage block and forgotten in the stand-down is exactly the
           # drift the top-level comparison cannot see. The unattributed bucket now carries its own
           # cost and cycle blocks, so it gets the same treatment.
           and sorted(_w1409_sd_records["coverage"]) == sorted(_w1409_rep["coverage"])
           and sorted(_w1409_sd_records["unattributed"]) == sorted(_w1409_rep["unattributed"])
           and sorted(_w1409_dig(_w1409_sd_records, "unattributed", "cost") or {}) == sorted(
               _w1409_rep["areas"]["alpha"]["cost"])
           and sorted(_w1409_dig(_w1409_sd_records, "unattributed", "cycles") or {}) == sorted(
               _w1409_rep["areas"]["alpha"]["cycles"])
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
    # THE ROOT IS HONOURED FOR EVERY INPUT, AND THAT IS THE LOADER'S DOING. repo_report(root=X)
    # read the contract and the specs from X while the EVENT STREAM came from metrics.LOG, the GIT
    # HISTORY from toe_corpus.ROOT and the PROTECTED PATTERNS from policy_check, all three resolved
    # from wherever this file lives - so a per-area cost map produced for X carried Y's cycles,
    # spend and git attribution, with nothing in the report saying which tree each figure came
    # from. A half honoured root is the shape a caller cannot detect, which is worse than no
    # parameter at all.
    #
    # THE FIX IS ONE LINE AND NO SECOND SPELLING OF "WHICH TREE": the four siblings are loaded FROM
    # the tree under report, so each one's own module-level root IS that tree. Threading a root
    # argument through metrics.load, policy_check.protected_patterns and toe_corpus would have put
    # that decision in three more modules. Driven here in two halves - the loader honours the root,
    # and repo_report binds its default loader to the root it was given - and end to end over a
    # real fixture repository further down.
    # -----------------------------------------------------------------------------------
    _w1409_other = Path(_d) / "othertree"
    (_w1409_other / ".veldo").mkdir(parents=True)
    (_w1409_other / ".veldo" / "metrics.py").write_text("MARKER = 'the other tree'\n")
    _w1409_probe = _W1409._load("w1409_probe_metrics", ".veldo/metrics.py", _w1409_other)
    _w1409_real_metrics = _W1409._load("w1409_real_metrics", ".veldo/metrics.py")
    _w1409_absent_load = _w1409_raises(_W1409._load, "w1409_absent", ".veldo/toe_corpus.py",
                                       _w1409_other)
    expect("WARP-1409 AC1: THE MODULE LOADER LOADS FROM THE ROOT IT IS GIVEN, and an absent sibling "
           "is NAMED rather than thrown. Handed a tree holding one stand-in metrics.py, it returns "
           "THAT module (its MARKER is readable and the real module's LOG is not); handed no root it "
           "returns this repository's real one (LOG present, no MARKER). Asked for a sibling that "
           "tree does not carry, it raises ValueError naming BOTH the missing module path and the "
           "root, which is what turns an adopter's FileNotFoundError traceback into one line and "
           "exit 1: a tree without the estimation layer has no map to produce, and saying so is a "
           "state a caller can act on",
           getattr(_w1409_probe, "MARKER", None) == "the other tree"
           and not hasattr(_w1409_probe, "LOG")
           and hasattr(_w1409_real_metrics, "LOG")
           and not hasattr(_w1409_real_metrics, "MARKER")
           and _w1409_absent_load[0]
           and _w1409_absent_load[1].startswith("ValueError")
           and ".veldo/toe_corpus.py" in _w1409_absent_load[1]
           and str(_w1409_other) in _w1409_absent_load[1])

    _w1409_load_asked = []

    def _w1409_recording_load(name, rel, root=None):
        """The module loader, replaced for ONE call, recording the (path, root) pair it is asked
        for and answering with the same stubs the wiring block uses. This is how the BINDING is
        observed: the loader repo_report builds for itself is otherwise invisible."""
        _w1409_load_asked.append((rel, str(root) if root is not None else None))
        return _w1409_stub_load(name, rel)

    _w1409_load_saved = _W1409._load
    try:
        _W1409._load = _w1409_recording_load
        _w1409_rooted, _w1409_rooted_err = _w1409_wire(None)
    finally:
        _W1409._load = _w1409_load_saved
    expect("WARP-1409 AC1 AND AC4: repo_report ASKS FOR ALL FOUR SIBLINGS UNDER THE ROOT IT WAS "
           "GIVEN, so every one of its five inputs comes from the tree under report and none of "
           "them from wherever this module happens to live. Driven with no loader injected at all, "
           "which is the production path: the real loader is replaced for one call and records what "
           "it was asked for, and all four requests carry the root - not None, and not this "
           "repository. The composition still produced the report (three records, both joins), so "
           "this is a rewiring observed rather than a call that failed early, and the real loader "
           "is restored afterwards",
           _w1409_rooted_err == ""
           and [_p for _p, _r in _w1409_load_asked] == [
               ".veldo/validate.py", ".veldo/toe_corpus.py", ".veldo/metrics.py",
               ".veldo/policy_check.py"]
           and {_r for _p, _r in _w1409_load_asked} == {str(_d)}
           and _w1409_rooted["coverage"]["records"] == 3
           and _W1409._load is _w1409_load_saved)

    # -----------------------------------------------------------------------------------
    # AC6. THE DERIVATION WRITES NOTHING, OBSERVED RATHER THAN PROMISED.
    #
    # AC6's own sentence says "nothing reads a clock, mints an id or writes a file", and until now
    # nothing defended the last clause: determinism across two in-process runs and a reversed corpus
    # cannot see a filesystem write, and the spawn scanner looks for subprocess primitives. A review
    # added ONE line to report() writing .veldo/ctc_side_effect.json, watched the file appear on
    # disk, and the suite stayed at 40 passed 0 failed. This is ledger 53's repair, in the shape a
    # sibling suite already uses (15_warp_1407): a recursive inventory of PATH, SIZE, MTIME and
    # SHA256 around the call, over the tree the module resolves its own paths from - pointed at a
    # hermetic fixture for the duration, the way that suite points its module's ROOT - AND over this
    # repository's real .veldo, which is where any state file in this package would land.
    #
    # NO EXCLUSION LIST, because a list is something a real writer could hide behind: the ONE thing
    # suppressed is the interpreter's own bytecode cache, and that is suppressed rather than
    # excluded.
    # -----------------------------------------------------------------------------------
    def _w1409_inventory(root):
        """path -> (size, mtime_ns, sha256) for every entry under one tree, directories included as
        paths so a new file is visible even when nothing else moves. ONE instrument, used for the
        claim and for the controls below, so an instrument that could see nothing could not pass for
        a tree that did not change."""
        out = {}
        for _p in sorted(Path(root).rglob("*")):
            _rel = str(_p.relative_to(root))
            if _p.is_dir():
                out[_rel] = ("dir", 0, "")
                continue
            _st = _p.stat()
            out[_rel] = (_st.st_size, _st.st_mtime_ns,
                         _w1409_hashlib.sha256(_p.read_bytes()).hexdigest())
        return out

    _w1409_wtree = Path(_d) / "writetree"
    (_w1409_wtree / ".veldo").mkdir(parents=True)
    (_w1409_wtree / ".veldo" / "seed.json").write_text("{}\n")
    _w1409_inv_roots = [_w1409_wtree, ROOT / ".veldo"]
    _w1409_root_saved, _w1409_pyc_saved = _W1409.ROOT, _w1409_sys.dont_write_bytecode
    try:
        _W1409.ROOT, _w1409_sys.dont_write_bytecode = _w1409_wtree, True
        _w1409_inv_before = [_w1409_inventory(_r) for _r in _w1409_inv_roots]
        _w1409_inv_rep = _W1409.report(_W1409_MIXED, _W1409_CONTRACT, _W1409ARCH,
                                       fm_of=_W1409_FM.get,
                                       paths_of=lambda s: _W1409_PATHS.get(s, []))
        _w1409_inv_text = _w1409_render(_w1409_inv_rep)
        _w1409_inv_after = [_w1409_inventory(_r) for _r in _w1409_inv_roots]
    finally:
        _W1409.ROOT, _w1409_sys.dont_write_bytecode = _w1409_root_saved, _w1409_pyc_saved
    expect("WARP-1409 AC6: BUILDING AND RENDERING THE WHOLE REPORT LEAVES EVERY TREE IT COULD REACH "
           "BYTE-IDENTICAL, asserted as a recursive inventory of path, size, mtime and sha256 "
           "before and after rather than as a promise or a source grep. Two trees: the one the "
           "module resolves its own paths from, pointed at a hermetic fixture for the duration, and "
           "this repository's real .veldo, where a cache or a stamp would land. THE DOMAIN IS REAL "
           "BEFORE THE ABSENCE IS CLAIMED OVER IT: the inventories are non-empty, the real one names "
           "cost_to_change.py itself and covers over a hundred entries, and the derivation "
           "demonstrably RAN over the fixture (four records, two areas, a rendered table) rather "
           "than standing down. ROOT is restored afterwards, so every assertion below reads the real "
           "repository",
           _w1409_inv_before == _w1409_inv_after
           and len(_w1409_inv_after[0]) >= 2
           and ".veldo/seed.json" in _w1409_inv_after[0]
           and "cost_to_change.py" in _w1409_inv_after[1]
           and len(_w1409_inv_after[1]) > 100
           and _w1409_inv_rep["coverage"]["records"] == 4
           and sorted(_w1409_inv_rep["areas"]) == ["alpha", "beta"]
           and "area alpha" in _w1409_inv_text
           and _W1409.ROOT == ROOT
           and _w1409_sys.dont_write_bytecode == _w1409_pyc_saved)

    (_w1409_wtree / ".veldo" / "ctc_side_effect.json").write_text('{"wrote": true}')
    expect("WARP-1409 AC6 CONTROL, ADDITIVE: THE INVENTORY SEES A PLANTED WRITE AND NAMES IT. The "
           "file planted here is the exact one a review added to report() while the suite stayed "
           "green, so the identity above is a measurement of that mutation's absence and not an "
           "instrument that notices nothing. The diff is asserted to be EXACTLY the planted path, "
           "so the instrument is shown to be specific as well as sensitive",
           set(_w1409_inventory(_w1409_wtree)) - set(_w1409_inv_after[0])
           == {".veldo/ctc_side_effect.json"})

    _w1409_os.utime(_w1409_wtree / ".veldo" / "seed.json",
                    ns=(_w1409_inv_after[0][".veldo/seed.json"][1] + 10 ** 9,
                        _w1409_inv_after[0][".veldo/seed.json"][1] + 10 ** 9))
    expect("WARP-1409 AC6 CONTROL: THE INVENTORY SEES A REWRITE THAT CHANGES NO BYTES, which is why "
           "the mtime is in it. A writer that stamps the same content on every run is invisible to a "
           "content-only digest, and ledger 53 records that exact mutation surviving one. Driven by "
           "moving one file's mtime a second forward with its bytes untouched: the entry for that "
           "path changes while its sha256 does not",
           _w1409_inventory(_w1409_wtree)[".veldo/seed.json"]
           != _w1409_inv_after[0][".veldo/seed.json"]
           and _w1409_inventory(_w1409_wtree)[".veldo/seed.json"][2]
           == _w1409_inv_after[0][".veldo/seed.json"][2])

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

expect("WARP-1409 AC8: a spec id NO commit names yields empty lists and zero counts rather than an "
       "exception, on both views of the one git read",
       _W1409TC.git_touched("WARP-0000-nothing-names-this")
       == {"commits": [], "files": []}
       and _W1409TC.files_touched("WARP-0000-nothing-names-this")
       == {"commits": 0, "files_touched": 0})

# THE NON-EMPTY HALF, OVER THE FIXTURE REPOSITORY, WITH NO STAND-DOWN LEFT ANYWHERE.
#
# This used to route through shared.no_history with the PROSE SENTENCE "the commits naming WARP-1401"
# where the mechanism wants a module path. history_begins_with runs `git log -- <rel>` and returns
# True whenever the result is empty, which a non-path always is, so the guard that separates an
# HONESTLY ABSENT input from a BROKEN READER answered True in this repository and in every other one,
# forever - and neither leg was about a pre-change revision, which is the only kind of leg that may
# be routed through there at all. The consequence was measured, not theorised: gutting git_touched,
# the ONE reader both halves of the git-path stand-down depend on, left this suite at 40 passed 0
# failed, and so did replacing files_touched with hardcoded zeros - a wrong number in every one of
# the 174 corpus records this plan trains on.
#
# The fixture repository closes both, everywhere: ONE commit in it names WARP-9452 and touches
# exactly one file, so each count can be required to EQUAL the length of the list it counts over a
# NON-EMPTY read, and the absent control runs in the same tree rather than in a different one.
_w1409_fx_touched = _W1409TC.git_touched("WARP-9452", root=_W1409_FIXTURE_REPO)
_w1409_fx_counted = _W1409TC.files_touched("WARP-9452", root=_W1409_FIXTURE_REPO)
_w1409_fx_absent = _W1409TC.git_touched("WARP-9499-nothing-names-this",
                                        root=_W1409_FIXTURE_REPO)
expect("WARP-1409 AC8: files_touched COUNTS EXACTLY WHAT git_touched READS, DRIVEN OVER A NON-EMPTY "
       "READ IN EVERY REPOSITORY. In the fixture tree one commit names WARP-9452 and changed one "
       "file: git_touched returns that one sha and that one path, files_touched returns 1 and 1, and "
       "each count EQUALS the length of the matching list rather than agreeing with it at zero. THE "
       "PAIR: the same reader in the same tree answers a spec id no commit names with empty lists "
       "and zero counts. Without the non-empty half, hardcoded zeros satisfy the absent case and "
       "quietly make every git-path attribution in the repository unattributed - which is what was "
       "measured before this row existed. This needs no history of its own and stands down nowhere",
       sorted(_w1409_fx_counted) == ["commits", "files_touched"]
       and sorted(_w1409_fx_touched) == ["commits", "files"]
       and _w1409_dig(_w1409_fx_counted, "commits")
       == len(_w1409_dig(_w1409_fx_touched, "commits") or []) == 1
       and _w1409_dig(_w1409_fx_counted, "files_touched")
       == len(_w1409_dig(_w1409_fx_touched, "files") or []) == 1
       and _w1409_dig(_w1409_fx_touched, "files") == [".veldo/dashboard.py"]
       and _w1409_fx_absent == {"commits": [], "files": []}
       and _W1409TC.files_touched("WARP-9499-nothing-names-this", root=_W1409_FIXTURE_REPO)
       == {"commits": 0, "files_touched": 0})

# -----------------------------------------------------------------------------------
# THE WHOLE WIRING OVER A REAL TREE THAT IS NOT THIS ONE. Every figure in this report can only have
# come from the fixture repository: its contract, its specs, its own event log, its own git history.
# This is the row that makes `root` a parameter a caller can trust, and it is also where the git-path
# join is driven over REAL git output rather than over an injected reader - which is what the LIVE
# git-path leg used to stand down for.
# -----------------------------------------------------------------------------------
try:
    _W1409_FX_REP = _W1409.repo_report(root=_W1409_FIXTURE_REPO)
    _W1409_FX_ERR = ""
except BaseException as _w1409_fx_exc:                                          # noqa: BLE001
    _W1409_FX_REP = {"areas": {}, "coverage": {}, "unattributed": {"specs": []},
                     "attribution": {_b: 0 for _b in _W1409.BASES}}
    _W1409_FX_ERR = "%s: %s" % (type(_w1409_fx_exc).__name__, _w1409_fx_exc)
_w1409_fx_area = _W1409_FX_REP["areas"].get("metrics", {})
expect("WARP-1409 AC1, AC2 AND AC4 OVER A DIFFERENT TREE: repo_report(root=X) DERIVES X'S MAP FROM "
       "X'S OWN FIVE INPUTS. The fixture repository holds two shipped specs, one declaring placement "
       "metrics and one declaring nothing, an event log carrying 4321 tokens and one gate pass and "
       "one gate failure for the declaring one, and a commit naming the other and touching "
       ".veldo/dashboard.py. Read back: two records, ONE area, attribution {placement: 1, git_path: "
       "1} with attribution_basis 'mixed', cost tokens 4321 with cost_basis 'recorded' on spend 1 of "
       "2, gate_passes 1 and gate_failures 1 with gate_basis 'recorded', the git-path notice "
       "present, and both blunt booleans true. EVERY ONE OF THOSE FIGURES IS UNREACHABLE FROM THIS "
       "REPOSITORY: this log carries no WARP-9451 event and this history names no spec at all, so "
       "before the fix the same call read the contract and the specs from the fixture while taking "
       "the event stream, the git history and the protected patterns from here - a map for X "
       "carrying Y's numbers, with nothing in the report saying so",
       _W1409_FX_ERR == ""
       and _W1409_FX_REP["coverage"]["records"] == 2
       and sorted(_W1409_FX_REP["areas"]) == ["metrics"]
       and _w1409_fx_area.get("attribution") == {_W1409.BY_PLACEMENT: 1, _W1409.BY_GIT_PATH: 1}
       and _w1409_fx_area.get("attribution_basis") == "mixed"
       and {_m["spec"]: _m["basis"] for _m in _w1409_fx_area.get("members", [])}
       == {"WARP-9451": _W1409.BY_PLACEMENT, "WARP-9452": _W1409.BY_GIT_PATH}
       and _w1409_dig(_w1409_fx_area, "cost", "tokens") == 4321
       and _w1409_dig(_w1409_fx_area, "cost", "cost_usd") == 2.5
       and _w1409_dig(_w1409_fx_area, "cost", "human_minutes") == 9
       and _w1409_dig(_w1409_fx_area, "cost", "cost_basis") == "recorded"
       and _w1409_dig(_w1409_fx_area, "cost", "spend_known") == 1
       and _w1409_dig(_w1409_fx_area, "cycles", "gate_passes") == 1
       and _w1409_dig(_w1409_fx_area, "cycles", "gate_failures") == 1
       and _w1409_dig(_w1409_fx_area, "cycles", "gate_basis") == "recorded"
       and _W1409_FX_REP["git_path_attributed"] is True
       and "BY GIT PATH" in _W1409_FX_REP.get("notice", "")
       and _W1409_FX_REP["coverage"]["usable_as_cost_ground_truth"] is True
       and _W1409_FX_REP["coverage"]["usable_as_rework_ground_truth"] is True
       and _W1409_FX_REP["unattributed"]["specs"] == []
       # THE PAIR THAT PROVES THE FIGURES COULD NOT HAVE COME FROM HERE. Both are facts about DATA
       # rather than about dependencies: a synthetic spec id absent from this repository's own log,
       # and this repository's own git reader answering nothing for it.
       and "WARP-9451" not in (ROOT / ".veldo/events.jsonl").read_text()
       and _W1409TC.git_touched("WARP-9452") == {"commits": [], "files": []})

# -----------------------------------------------------------------------------------
# The rendered text is drawn from the report, so a reader and a JSON consumer cannot see two
# different numbers. Checked on the mixed fixture and on a stand-down.
# -----------------------------------------------------------------------------------
_w1409_text = _w1409_render(_w1409_rep)
expect("WARP-1409 AC2: THE RENDERED TEXT CARRIES THE GIT-PATH WARNING AND THE SAME FIGURES THE "
       "JSON DOES, drawn from the report rather than recomputed, so the human surface and the "
       "machine surface cannot disagree. A stand-down renders one honest line naming the reason "
       "instead of an empty table that reads like a repository with no cost",
       "BY GIT PATH" in _w1409_text
       and ("records %d" % _w1409_rep["coverage"]["records"]) in _w1409_text
       and "area alpha" in _w1409_text and "tokens=None" in _w1409_text
       and "standing down" in _w1409_render(_w1409_sd_records))

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
_w1409_live_text = _w1409_render(_W1409_LIVE) if _W1409_LIVE_ERR == "" else ""


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
# SPLIT BY WHETHER THE RECORD REACHED AN AREA AT ALL, which is the distinction the blunt booleans
# and the notices are statements about and the one this block could not see. 108 of this repository's
# 174 records are unattributed, so a signal recorded against one of them is in NO per-area figure,
# and every per-area leg of the recorded arm below iterated the areas of the recording spec - empty
# for an unattributed one, which made the whole arm vacuously true in exactly the state ONE
# `.veldo/spend.py record` produces. Derived HERE from the independently built corpus and the live
# map's own membership index, so both sides of every comparison cannot move together.
_w1409_live_spend_placed = {_s for _s in _w1409_live_spend_of if _s in _w1409_live_areas_of}
_w1409_live_spend_nowhere = {_s for _s in _w1409_live_spend_of
                             if _s not in _w1409_live_areas_of}
_w1409_live_gate_placed = {_s for _s in _w1409_live_gate_specs if _s in _w1409_live_areas_of}
_w1409_live_gate_nowhere = {_s for _s in _w1409_live_gate_specs
                            if _s not in _w1409_live_areas_of}


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
       and _W1409_LIVE["coverage"]["cost_attributed_records"] == len(_w1409_live_spend_placed)
       and _W1409_LIVE["coverage"]["cost_unattributed_records"] == len(_w1409_live_spend_nowhere)
       and (_W1409_LIVE["coverage"]["usable_as_cost_ground_truth"]
            is bool(_w1409_live_spend_placed))
       and ("cost_notice" in _W1409_LIVE) is (not _w1409_live_spend_placed)
       and ("unattributed_spend_notice" in _W1409_LIVE) is bool(_w1409_live_spend_nowhere)
       and _W1409_LIVE["coverage"]["gate_event_records"] == len(_w1409_live_gate_specs)
       and _W1409_LIVE["coverage"]["gate_attributed_records"] == len(_w1409_live_gate_placed)
       and _W1409_LIVE["coverage"]["gate_unattributed_records"] == len(_w1409_live_gate_nowhere)
       and (_W1409_LIVE["coverage"]["usable_as_rework_ground_truth"]
            is bool(_w1409_live_gate_placed))
       and ("cycle_notice" in _W1409_LIVE) is (not _w1409_live_gate_placed)
       and ("unattributed_cycle_notice" in _W1409_LIVE) is bool(_w1409_live_gate_nowhere)
       # NOTHING RECORDED IS ABSENT FROM EVERY FIGURE, over whatever this repository has recorded:
       # the unattributed bucket's own cost and cycle blocks report exactly the records that landed
       # in no area, with the same basis rule the areas follow. This is unconditional and it is the
       # leg that reds if a recorded figure goes back to being in no figure at all.
       and _w1409_dig(_W1409_LIVE, "unattributed", "cost", "spend_known") == len(
           _w1409_live_spend_nowhere)
       and (_w1409_dig(_W1409_LIVE, "unattributed", "cost", "cost_basis")
            == ("recorded" if _w1409_live_spend_nowhere else "unrecorded"))
       and all((_w1409_dig(_W1409_LIVE, "unattributed", "cost", _f) is None)
               is (not _w1409_live_spend_nowhere) for _f in _W1409.COST_FIELDS)
       and _w1409_dig(_W1409_LIVE, "unattributed", "cycles", "gate_events_known") == len(
           _w1409_live_gate_nowhere)
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
    expect("WARP-1409 AC4 OVER THE REAL REPOSITORY, THE RECORDED COST ARM: %d record(s) carry "
           "spend, %d of them attributed to an area and %d attributed to nothing, and EVERY ONE OF "
           "THEM IS IN A FIGURE. An attributed one is in an area reporting cost_basis 'recorded' "
           "with a real tokens number; an unattributed one is COUNTED IN unattributed.cost, which "
           "reports 'recorded' with a real tokens number of its own and a notice naming how many. "
           "THE ARM IS WRITTEN SO IT CANNOT BE SATISFIED BY AN EMPTY ITERATION: it used to read "
           "`for area in areas_of(spec)`, which is empty for an unattributed spec, so the whole arm "
           "was vacuously true in exactly the state one `.veldo/spend.py record` against any of the "
           "108 unattributed specs produces - the state in which the map announced itself usable as "
           "cost ground truth with every area reporting None. Each spec is now required to be in "
           "one of the two figures BY NAME, and the two sets are required to partition the "
           "recording set with neither side allowed to be the whole of it by default"
           % (len(_w1409_live_spend_of), len(_w1409_live_spend_placed),
              len(_w1409_live_spend_nowhere)),
           _W1409_LIVE_ERR == ""
           # The blunt boolean is about the PER-AREA figures, so it is true exactly when some
           # recording spec reached an area - never merely because something somewhere recorded.
           and (_W1409_LIVE["coverage"]["usable_as_cost_ground_truth"]
                is bool(_w1409_live_spend_placed))
           and ("cost_notice" in _W1409_LIVE) is (not _w1409_live_spend_placed)
           and _w1409_live_spend_placed | _w1409_live_spend_nowhere == set(_w1409_live_spend_of)
           and not (_w1409_live_spend_placed & _w1409_live_spend_nowhere)
           and all(_s in _w1409_live_areas_of
                   or _s in set(_W1409_LIVE["unattributed"]["specs"])
                   for _s in _w1409_live_spend_of)
           and all(_W1409_LIVE["areas"][_a]["cost"]["cost_basis"] == "recorded"
                   and _W1409_LIVE["areas"][_a]["cost"]["tokens"] is not None
                   for _s in _w1409_live_spend_placed
                   for _a in _w1409_live_areas_of[_s])
           # The other half of the same sentence, and the half that was missing: what happens to
           # spend recorded against a spec no area holds.
           and (not _w1409_live_spend_nowhere
                or (_w1409_dig(_W1409_LIVE, "unattributed", "cost", "cost_basis") == "recorded"
                    and _w1409_dig(_W1409_LIVE, "unattributed", "cost", "tokens") is not None
                    and _w1409_dig(_W1409_LIVE, "unattributed", "cost", "spend_known")
                    == len(_w1409_live_spend_nowhere)
                    and set(_w1409_live_spend_nowhere)
                    <= set(_W1409_LIVE["unattributed"]["specs"])
                    and "reaches NO per-area figure"
                    in _W1409_LIVE.get("unattributed_spend_notice", "")))
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
           # INCLUDING THE BUCKET THAT HOLDS NO AREA: nothing recorded anywhere means the
           # unattributed cost is None too, and "no record carries spend" is not a licence for one
           # figure in this report to read zero.
           and all(_w1409_dig(_W1409_LIVE, "unattributed", "cost", f) is None
                   for f in _W1409.COST_FIELDS)
           and "cost" in _W1409_LIVE["unattributed"]
           and _w1409_dig(_W1409_LIVE, "unattributed", "cost", "cost_basis") == "unrecorded"
           and "unattributed_spend_notice" not in _W1409_LIVE
           and "tokens=None" in _w1409_live_text)

# THE GATE ARM, the same shape over the other signal. Its writer is not spend.py but verify.sh
# learning to name the spec its run belongs to (out of scope for this item and named as such in the
# notice), so this arm flips the day that emitter changes rather than reding.
if _w1409_live_gate_specs:
    expect("WARP-1409 AC4 OVER THE REAL REPOSITORY, THE RECORDED GATE ARM: %d record(s) carry a "
           "gate pass or a gate failure, %d of them attributed to an area and %d attributed to "
           "nothing, and EVERY ONE OF THEM IS IN A FIGURE - the same shape as the cost arm and for "
           "the same reason. An attributed one is in an area reporting gate_basis 'recorded' with "
           "real gate_passes and gate_failures; an unattributed one is counted in "
           "unattributed.cycles with its own notice, rather than turning the blunt "
           "usable_as_rework_ground_truth boolean true while every area reports None. The per-area "
           "leg iterates the ATTRIBUTED set, so it cannot be satisfied by an empty iteration"
           % (len(_w1409_live_gate_specs), len(_w1409_live_gate_placed),
              len(_w1409_live_gate_nowhere)),
           _W1409_LIVE_ERR == ""
           and (_W1409_LIVE["coverage"]["usable_as_rework_ground_truth"]
                is bool(_w1409_live_gate_placed))
           and ("cycle_notice" in _W1409_LIVE) is (not _w1409_live_gate_placed)
           and _w1409_live_gate_placed | _w1409_live_gate_nowhere == _w1409_live_gate_specs
           and not (_w1409_live_gate_placed & _w1409_live_gate_nowhere)
           and all(_s in _w1409_live_areas_of
                   or _s in set(_W1409_LIVE["unattributed"]["specs"])
                   for _s in _w1409_live_gate_specs)
           and all(_W1409_LIVE["areas"][_a]["cycles"]["gate_basis"] == "recorded"
                   and _W1409_LIVE["areas"][_a]["cycles"]["gate_passes"] is not None
                   and _W1409_LIVE["areas"][_a]["cycles"]["gate_failures"] is not None
                   for _s in _w1409_live_gate_placed
                   for _a in _w1409_live_areas_of[_s])
           and (not _w1409_live_gate_nowhere
                or (_w1409_dig(_W1409_LIVE, "unattributed", "cycles", "gate_basis") == "recorded"
                    and _w1409_dig(_W1409_LIVE, "unattributed", "cycles", "gate_passes") is not None
                    and _w1409_dig(_W1409_LIVE, "unattributed", "cycles", "gate_events_known")
                    == len(_w1409_live_gate_nowhere)
                    and "reported ONLY in unattributed.cycles"
                    in _W1409_LIVE.get("unattributed_cycle_notice", ""))))
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
           and all(_w1409_dig(_W1409_LIVE, "unattributed", "cycles", f) is None
                   for f in _W1409.GATE_CYCLE_FIELDS)
           and "cycles" in _W1409_LIVE["unattributed"]
           and "unattributed_cycle_notice" not in _W1409_LIVE
           and "gate_passes=None" in _w1409_live_text)

# THE GIT-PATH DISCLOSURE OVER THE LIVE MAP, AS A PROPERTY RATHER THAN A COUNT, WITH NO STAND-DOWN.
#
# This used to require the live git-path count to be POSITIVE and stood down through
# shared.no_history when it was not - with a prose sentence where the mechanism wants a module path,
# so the guard could not fail and a broken git reader would have stood down instead of reddening.
# BOTH HALVES OF THAT ARE NOW WRONG TO KEEP. The join itself is driven over REAL git output in the
# fixture repository above, where one commit names WARP-9452 and the report comes back basis
# 'git_path' in the area that path falls into. And the live half is asserted as the property that
# holds whichever way this repository's history reads: EVERY DISCLOSURE AGREES WITH THE COUNT. It is
# 0 here (a flattened history whose one commit names no spec) and it would be 41 in the predecessor;
# neither number is pinned, and a report that carried the warning without the records, or the records
# without the warning, reds either way.
expect("WARP-1409 AC2 OVER THE REAL REPOSITORY: EVERY GIT-PATH DISCLOSURE AGREES WITH THE GIT-PATH "
       "COUNT, whatever that count is. git_path_attributed, the presence of the notice, the presence "
       "of the bases entry that spells the weakness out, and the presence of a member carrying basis "
       "'git_path' are each true EXACTLY when the count is positive, and the notice counts the same "
       "records the attribution block does. NO COUNT IS PINNED: this history's one commit names no "
       "spec so the count is 0 today, the predecessor's was 41, and a repository that accumulates "
       "spec-naming commits moves the arm rather than reding it. The JOIN is proven over real git "
       "output in the fixture repository above rather than stood down here",
       _W1409_LIVE_ERR == ""
       and (_W1409_LIVE["git_path_attributed"]
            is (_W1409_LIVE["attribution"][_W1409.BY_GIT_PATH] > 0))
       and ("notice" in _W1409_LIVE) is (_W1409_LIVE["attribution"][_W1409.BY_GIT_PATH] > 0)
       and ((_W1409.BY_GIT_PATH in _W1409_LIVE["bases"])
            is (_W1409_LIVE["attribution"][_W1409.BY_GIT_PATH] > 0))
       and ((_W1409.BY_GIT_PATH in set(_w1409_live_members.values()))
            is (_W1409_LIVE["attribution"][_W1409.BY_GIT_PATH] > 0))
       and (_W1409_LIVE["attribution"][_W1409.BY_GIT_PATH] == 0
            or ("%d of %d records" % (_W1409_LIVE["attribution"][_W1409.BY_GIT_PATH],
                                      _W1409_LIVE["coverage"]["records"]))
            in _W1409_LIVE["notice"]))

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

_w1409_shutil.rmtree(_W1409_FIXTURE_REPO, ignore_errors=True)
expect("WARP-1409 housekeeping: the fixture repository this suite built - a real git tree with two "
       "commits, the estimation layer and its own event log - is REMOVED afterwards, so the suite "
       "leaves nothing behind, and it was a real tree while it existed rather than a mocked one",
       not _W1409_FIXTURE_REPO.exists()
       and (_w1409_dig(_w1409_fx_touched, "commits") or []) != [] and _W1409_FX_ERR == "")

del _w1409_cspec, _w1409_tspec, _w1409_mspec, _w1409_pspec, _w1409_re
del _w1409_hashlib, _w1409_os, _w1409_shutil, _w1409_subprocess, _w1409_sys
