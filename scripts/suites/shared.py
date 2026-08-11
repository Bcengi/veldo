"""Shared fixtures and the assertion primitive: the one module every suite imports.

THIS FILE IS THE SUITE'S PREAMBLE PLUS EVERY MODULE-LEVEL BINDING THAT CROSSED A REGION
BOUNDARY in the monolith WARP-0712 cut up. Its membership was not chosen: it is the fixed
point of "run it, and if it dies on an undefined name, add the statement that binds that
name". It is enumerated as the FIRST suite in suites/manifest.json, because it carries
assertions of its own and a label produced by a file no manifest names is exactly what
SUITE_NOT_ENUMERATED exists to refuse.

THERE IS ONE NAMESPACE AND IT IS THIS MODULE'S. scripts/selftest.py execs every fragment into
this module's __dict__, in manifest order; no fragment imports this module and none has a
namespace of its own. So a fragment that REBINDS a name here changes what every later fragment
sees, which is exactly what the monolith did and is why the decomposition cannot change what any
assertion proves. The dispatcher's docstring states the measurement that decision came from.
"""
#!/usr/bin/env python3
"""Contract-system self-test: the unit suite of this repository.

The product here is the validation machinery itself, so the tests are
negative-first: every planted-bad artifact must be REJECTED. A validator
that accepts garbage is worse than no validator, because it stamps the
garbage green.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

spec = importlib.util.spec_from_file_location("validate", ROOT / ".veldo" / "validate.py")
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)

pspec = importlib.util.spec_from_file_location("policy_check", ROOT / ".veldo" / "policy_check.py")
P = importlib.util.module_from_spec(pspec)
pspec.loader.exec_module(P)

# THE FILE THIS SUITE'S OWN ASSERTIONS ARE IN, whichever file that is. WARP-0712 cut the
# monolith into fragments executed in one namespace, and the dispatcher binds __suite_file__
# before each fragment runs. A handful of assertions have their OWN file as their subject, and
# a literal path would make every one of them measure the dispatcher after the cut and pass
# vacuously. Before the cut the fallback is the monolith itself, so this works both ways.
def suite_file():
    return Path(globals().get("__suite_file__", str(ROOT / "scripts/selftest.py")))


PASS = 0
FAIL = 0


def expect(name, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
    else:
        FAIL += 1
        print(f"  SELFTEST FAIL: {name}")


def tmpfile(dirpath, name, content):
    p = Path(dirpath) / name
    p.write_text(content)
    return p


# --- WARP-1711: THE ONE STAND-DOWN MECHANISM FOR A FROM-GIT LEG IN A FLATTENED REPOSITORY -------
# Several suites prove a claim as a BEFORE-AND-AFTER against a revision resolved from this
# repository's own history, deliberately, because a digest pinned inside the branch it defends is
# not evidence. A successor repository produced by scripts/migrate_to_veldo.py holds ONE commit, so
# that input does not exist there and those legs cannot run. The honest report is a NAMED stand-down
# rather than a red check or, far worse, a silent pass - and it lives HERE, once, because a second
# copy of this decision in another suite is a second thing to get wrong.
#
# ONE CONDITION, TESTED ONE WAY: the revision did not resolve AND THIS HISTORY CANNOT CONTAIN AN
# EARLIER STATE OF THE MODULE, because the module's oldest revision here IS a root commit. A
# repository WITH history whose lookup fails is a broken search and stays LOUD.
#
# THE FIRST VERSION OF THIS GATED ON `COMMIT_DEPTH == 1` AND THAT WAS THE WRONG FACT, which an
# independent review proved by building the successor and committing to it once: at depth 1 it was
# green with 29 stand-downs, and at depth 2 it was 32 failures with none. The input these legs need
# is missing at EVERY depth in a successor, not only at the first, because the resolver wants the
# newest revision NOT carrying today's markers and the migration commit already carries them. So a
# depth test made the successor green exactly once and red on its own first change, which is the
# thing AC4 exists to prevent. The right question is not how many commits exist, it is whether any
# revision older than the module's own arrival could ever exist here.
def _commit_depth():
    """This repository's commit depth, or 0 when git cannot answer at all. Exactly 1 is the
    flattened successor the migration produces; 0 is a broken read and never a licence."""
    try:
        return int(subprocess.run(["git", "-C", str(ROOT), "rev-list", "--count", "HEAD"],
                                  capture_output=True, text=True, check=True).stdout.strip())
    except Exception:                       # noqa: BLE001 - a broken read is 0, never a stand-down
        return 0


COMMIT_DEPTH = _commit_depth()


def _root_commits():
    """Every parentless commit reachable from HEAD. In a flattened successor there is exactly one
    and it introduced the entire tree."""
    try:
        return set(subprocess.run(["git", "-C", str(ROOT), "rev-list", "--max-parents=0", "HEAD"],
                                  capture_output=True, text=True, check=True).stdout.split())
    except Exception:                       # noqa: BLE001 - unreadable git is never a stand-down
        return set()


ROOT_COMMITS = _root_commits()


def history_begins_with(rel):
    """True when THIS history cannot hold a state of `rel` earlier than the one it starts with:
    either the module has no revisions here at all, or its OLDEST revision is a root commit.

    That is the fact a from-git leg actually depends on. A flattened successor satisfies it for
    every file at every depth, because one commit introduced the whole tree, so no future commit
    can produce an earlier state. This repository does NOT satisfy it: metrics.py's oldest revision
    is fabbbf2 while the root is 8894e6d, so the real assertion keeps running here, which is the
    negative control the stand-down needs in order to mean anything."""
    if not ROOT_COMMITS:
        return False
    try:
        revs = subprocess.run(["git", "-C", str(ROOT), "log", "--format=%H", "--reverse", "--", rel],
                              capture_output=True, text=True, check=True).stdout.split()
    except Exception:                       # noqa: BLE001
        return False
    return (not revs) or revs[0] in ROOT_COMMITS
# EVERY from-git leg registers here whether it stands down or not, so the mechanism itself is
# checkable rather than trusted: a suite compares the set that STOOD DOWN against the set that
# EXISTS in whichever repository it is running in. A stand-down that cannot be shown NOT to fire
# where history exists is a hole wearing a label.
HISTORY_LEGS = []          # (suite file name, leg, ((module, rev or None), ...))
STOOD_DOWN = []            # (suite file name, leg)


def stand_down(leg, why, weaker, item, inputs=()):
    """PRINT and RECORD one stand-down, and return True so a caller reads as `if stand_down(...)`.

    The ONE printer, because the wording is the contract: a reader of the gate output must be able
    to tell a criterion that was CHECKED from one that STOOD DOWN without reading the suite source.
    Every line names WHAT stood down, WHY, WHICH weaker leg still proves the criterion here, and
    WHERE the strong leg was proven. The CONDITION is never decided here - each caller states its
    own, because the two shapes are different facts: a revision that cannot be resolved, and a
    recorded event whose commit is absent."""
    HISTORY_LEGS.append((suite_file().name, leg, tuple(inputs)))
    STOOD_DOWN.append((suite_file().name, leg))
    # NO FALSE PROMISE. The first wording ended "it re-arms by itself as this repository accumulates
    # commits", which is the opposite of the truth: the resolver wants a revision without today's
    # markers, the migration commit already carries them, and no future commit creates an earlier
    # state. A stand-down that tells a reader it will heal itself is worse than one that admits it
    # will not, because the reader stops looking.
    print("   %s: %s STANDS DOWN, and this is recorded rather than passed: %s. %s The from-history "
          "leg was proven in the predecessor repository, which is frozen and retains that history; "
          "it cannot be re-derived here and does not re-arm as commits accumulate." % (item, leg, why, weaker))
    return True


def no_history(inputs, leg, weaker, item):
    """True when the from-git leg named by `leg` cannot run BECAUSE THERE IS NO HISTORY, having
    PRINTED that fact. False in every other case, including a repository with history whose
    revision lookup failed - that is a defect and the caller must assert exactly as it always did.

    `inputs` is the leg's ACTUAL INPUT as (module path, resolved revision or None) pairs - every
    revision the leg needs, never a summary boolean - so a registry reader can go back to each one
    and check it names a real earlier state rather than today's file.

    Silence is not an acceptable stand-down: the line names WHAT stood down, WHY (a single-commit
    repository), WHICH weaker leg still proves the criterion here, and WHERE the strong leg was
    proven. Only a leg REQUIRING a pre-change revision may be routed through here - every leg about
    TODAY'S code must be split out by the caller and keep running everywhere, because trading a
    known gap for an unknown one is the thing this must not do."""
    _ins = tuple(inputs)
    _unresolved = [_m for _m, _r in _ins if not _r]
    if not _unresolved or not all(history_begins_with(_m) for _m in _unresolved):
        HISTORY_LEGS.append((suite_file().name, leg, _ins))
        return False
    return stand_down(
        leg,
        "this history begins with %s already in place (its oldest revision is a root commit), so "
        "no revision of it earlier than that exists here to resolve, and none can appear later"
        % " and ".join(sorted(_unresolved)),
        weaker, item, _ins)


def history_legs(name=None):
    """The from-git legs registered by ONE suite file (this one by default). Per suite, because a
    partial run stops at the suite it was asked for and a registry read across all of them would
    say a later suite's legs are missing when they simply never ran."""
    _n = name or suite_file().name
    return [(_leg, _ins) for _s, _leg, _ins in HISTORY_LEGS if _s == _n]


def stood_down(name=None):
    """The legs of ONE suite file (this one by default) that stood down, by name."""
    _n = name or suite_file().name
    return [_leg for _s, _leg in STOOD_DOWN if _s == _n]


GOOD_SPEC = """---
schema: veldo.spec/v1
id: WARP-9001
title: Self-test fixture
status: ready
risk: standard
owner: selftest
acceptance_criteria:
  - id: AC1
    text: something observable happens.
required_evidence: [unit]
rollback: git revert
---
body
"""

with tempfile.TemporaryDirectory() as d:
    # positive control: the good spec is accepted
    good = tmpfile(d, "good.md", GOOD_SPEC)
    expect("good spec accepted", V.check_spec(good) == 0)

    # spec without acceptance criteria is rejected
    bad = GOOD_SPEC.replace("acceptance_criteria:\n  - id: AC1\n    text: something observable happens.\n", "")
    expect("spec without criteria rejected", V.check_spec(tmpfile(d, "nocrit.md", bad)) > 0)

    # spec with unknown evidence kind is rejected at spec time
    bad = GOOD_SPEC.replace("[unit]", "[vibes]")
    expect("unknown evidence kind rejected", V.check_spec(tmpfile(d, "vibes.md", bad)) > 0)

    # spec with bad status is rejected
    bad = GOOD_SPEC.replace("status: ready", "status: donezo")
    expect("bad status rejected", V.check_spec(tmpfile(d, "status.md", bad)) > 0)

    # proof with an invented criterion is rejected by coverage
    proof = {
        "schema": "veldo.proof/v1", "spec_id": "WARP-9001", "commit": "deadbeef",
        "producer": "selftest", "rollback": "git revert",
        "criteria": [
            {"id": "AC1", "status": "passed", "evidence": [{"type": "unit", "ref": "x"}]},
            {"id": "AC9", "status": "passed", "evidence": [{"type": "unit", "ref": "x"}]},
        ],
        "checks": [{"name": "unit", "status": "passed"}],
    }
    pf = tmpfile(d, "proof.json", json.dumps(proof))
    expect("invented proof criterion rejected", V.check_criteria_coverage(good, pf) > 0)

    # proof missing a spec criterion is rejected by coverage
    proof["criteria"] = []
    pf2 = tmpfile(d, "proof2.json", json.dumps(proof))
    expect("missing proof criterion rejected", V.check_criteria_coverage(good, pf2) > 0)

    # required evidence kind absent from proof is rejected
    proof["criteria"] = [{"id": "AC1", "status": "passed",
                          "evidence": [{"type": "operational", "ref": "x"}]}]
    proof["checks"] = [{"name": "operational", "status": "passed"}]
    pf3 = tmpfile(d, "proof3.json", json.dumps(proof))
    expect("absent required evidence rejected", V.check_required_evidence(good, pf3) > 0)

    # criterion passed without evidence is rejected
    proof["criteria"] = [{"id": "AC1", "status": "passed", "evidence": []}]
    pf4 = tmpfile(d, "proof4.json", json.dumps(proof))
    expect("passed-without-evidence rejected", V.check_json(pf4, V.PROOF_REQ, "proof") > 0)

    # verdict with a bad verdict value is rejected
    verdict = {"schema": "veldo.verdict/v1", "spec_id": "WARP-9001", "commit": "deadbeef",
               "reviewer": "selftest", "verdict": "looks_fine", "criteria": []}
    vf = tmpfile(d, "verdict.json", json.dumps(verdict))
    expect("bad verdict value rejected", V.check_json(vf, V.VERDICT_REQ, "verdict") > 0)

GOOD_PLAN = """---
schema: veldo.plan/v1
id: PLAN-9001
title: Self-test plan fixture
kind: iteration
status: ready
revision: 1
owner: selftest
approved_by: selftest
approved_at: 2026-01-01
outcomes:
  - id: O1
    becomes_true: a user does a thing that spans
      two continuation lines.
    measure: journey green
feature_tree:
  - id: F1
    title: the feature
    outcome_refs: [O1]
work:
  - item: W1
    spec: WARP-9101
    title: first
    feature_refs: [F1]
    depends_on: []
    order: 10
  - item: W2
    spec: WARP-9102
    title: second
    feature_refs: [F1]
    depends_on: [WARP-9101]
    order: 20
regression:
  journeys:
    - id: RJ1
      title: the journey
      activation: {when: start}
      suite: e2e
release:
  milestone: v1
  mode: continuous
open_decisions:
  - id: D1
    text: an open question nothing waits on.
    blocks: []
---
body
"""

with tempfile.TemporaryDirectory() as d:
    # positive control: the good plan is accepted
    goodp = tmpfile(d, "PLAN-9001-good.md", GOOD_PLAN)
    expect("good plan accepted", V.check_plan(goodp) == 0)

    # dependency cycle is rejected
    bad = GOOD_PLAN.replace("depends_on: []\n    order: 10",
                            "depends_on: [WARP-9102]\n    order: 10")
    expect("plan dependency cycle rejected", V.check_plan(tmpfile(d, "cycle.md", bad)) > 0)

    # dangling depends_on is rejected
    bad = GOOD_PLAN.replace("depends_on: [WARP-9101]", "depends_on: [WARP-9999]")
    expect("dangling dependency rejected", V.check_plan(tmpfile(d, "dangle.md", bad)) > 0)

    # unknown outcome ref is rejected
    bad = GOOD_PLAN.replace("outcome_refs: [O1]", "outcome_refs: [O7]")
    expect("unknown outcome ref rejected", V.check_plan(tmpfile(d, "oref.md", bad)) > 0)

    # unknown feature ref is rejected
    bad = GOOD_PLAN.replace("feature_refs: [F1]\n    depends_on: []",
                            "feature_refs: [F9]\n    depends_on: []")
    expect("unknown feature ref rejected", V.check_plan(tmpfile(d, "fref.md", bad)) > 0)

    # undeclared depends_on is rejected (absence is not [])
    bad = GOOD_PLAN.replace("    depends_on: []\n    order: 10\n", "    order: 10\n")
    expect("undeclared depends_on rejected", V.check_plan(tmpfile(d, "nodep.md", bad)) > 0)

    # approval required beyond draft
    bad = GOOD_PLAN.replace("approved_by: selftest\n", "").replace("approved_at: 2026-01-01\n", "")
    expect("ready without approval rejected", V.check_plan(tmpfile(d, "noappr.md", bad)) > 0)

    # open decision without an explicit blocks list is rejected
    bad = GOOD_PLAN.replace("    text: an open question nothing waits on.\n    blocks: []",
                            "    text: an open question nothing waits on.")
    expect("decision without blocks rejected", V.check_plan(tmpfile(d, "noblocks.md", bad)) > 0)

    # decision blocking an unknown spec is rejected
    bad = GOOD_PLAN.replace("blocks: []", "blocks: [WARP-9999]")
    expect("decision blocking unknown spec rejected", V.check_plan(tmpfile(d, "badblock.md", bad)) > 0)

    # duplicate work specs are rejected
    bad = GOOD_PLAN.replace("spec: WARP-9102", "spec: WARP-9101").replace(
        "depends_on: [WARP-9101]", "depends_on: []")
    expect("duplicate work spec rejected", V.check_plan(tmpfile(d, "dupspec.md", bad)) > 0)

    # bad release mode is rejected
    bad = GOOD_PLAN.replace("mode: continuous", "mode: yolo")
    expect("bad release mode rejected", V.check_plan(tmpfile(d, "mode.md", bad)) > 0)

    # forward mirroring: an existing spec that does not bind back is rejected
    sdir = Path(d) / "specs"
    sdir.mkdir()
    (sdir / "WARP-9101-first.md").write_text("""---
schema: veldo.spec/v1
id: WARP-9101
title: first
status: ready
risk: standard
owner: selftest
plan: PLAN-9001
work: W2
acceptance_criteria:
  - id: AC1
    text: observable.
rollback: git revert
---
""")
    expect("mirror mismatch rejected", V.check_plan(goodp, specs_dir=sdir) > 0)
    (sdir / "WARP-9101-first.md").write_text((sdir / "WARP-9101-first.md").read_text().replace("work: W2", "work: W1"))
    expect("correct mirror accepted", V.check_plan(goodp, specs_dir=sdir) == 0)

    # reverse binding: spec declaring plan without work is rejected
    sfm = V.front_matter((sdir / "WARP-9101-first.md").read_text())
    reg = {"PLAN-9001": {"path": goodp, "fm": V.parse_yamlish(__import__("re").match(r"^---\n(.*?)\n---", GOOD_PLAN, __import__("re").S).group(1))}}
    expect("spec binding to wrong plan rejected",
           V.check_spec_plan_binding("x.md", {"id": "WARP-9101", "plan": "PLAN-9002", "work": "W1"}, reg) > 0)
    expect("spec claiming missing work item rejected",
           V.check_spec_plan_binding("x.md", {"id": "WARP-9101", "plan": "PLAN-9001", "work": "W9"}, reg) > 0)
    expect("spec plan without work rejected",
           V.check_spec_plan_binding("x.md", {"id": "WARP-9101", "plan": "PLAN-9001"}, reg) > 0)
    expect("correct spec binding accepted",
           V.check_spec_plan_binding("x.md", {"id": "WARP-9101", "plan": "PLAN-9001", "work": "W1"}, reg) == 0)


def run_scope():
    """THE SCOPE OF THE RUN IN PROGRESS: what this run is allowed to claim (WARP-0717).

    scripts/selftest.py binds SCOPE before any fragment executes. The fallback is a FULL
    scope, because a caller that set nothing selected nothing; a partial run always has a
    selector and therefore always has a scope, so the fallback can never launder one.
    """
    scope = globals().get("SCOPE")
    if scope is not None:
        return scope
    spec = importlib.util.spec_from_file_location(
        "veldo_run_scope", ROOT / "scripts" / "run_scope.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.full_scope()


def report():
    """The aggregate summary line, in the monolith's exact format, and the exit code.

    IT EMITS THROUGH THE RUN SCOPE. That is the whole of WARP-0717's AC2 on this line: a
    partial run that reaches here does not print a slightly different line, it RAISES
    PARTIAL_RUN_CANNOT_VERIFY, so the line the gate parses cannot be produced by a run that
    tested a subset. The format is unchanged, and the scope owns it.
    """
    scope = run_scope()
    print(scope.aggregate_line(PASS, FAIL))
    return scope.exit_code(FAIL)


def suite_source():
    """The whole unit suite's source: every file the manifest enumerates, concatenated.

    It exists because a handful of assertions have the SUITE ITSELF as their subject - they
    check that a retired assertion label is gone and that its replacement is present. Before
    the decomposition they read one file. Reading scripts/selftest.py after it would read a
    dispatcher and pass vacuously, so they read this instead, and their labels are untouched.
    """
    import json as _json
    _here = Path(__file__).resolve().parent
    _m = _json.loads((_here / "manifest.json").read_text())
    _parts = [(_here / s["file"]).read_text() for s in _m["suites"]]
    return "".join(_parts)


