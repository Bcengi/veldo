"""WARP-1408: the budget roll-up, the dollar range, pacing, and the advisory proof.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, which always
runs, so its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 15_warp_1408_budget_rollup

WHAT IS OBSERVED HERE, AND HOW. The subject is arithmetic over records plus one hard posture
(nothing blocks), so the shape is: every positive number is RECOMPUTED from its inputs rather
than compared to a pinned literal, every standdown is PAIRED with the control that the same code
does produce a number when the data is there, and the advisory claim is DRIVEN through the two
real surfaces that could delay work - validate.check_spec and frontier.claimable - instead of
being grepped for.

WHAT IS ASSERTED OVER *THIS* REPOSITORY, AND WHAT IS ASSERTED OVER A FIXTURE. THIS FRAGMENT IS A
REQUIRED GATE CHECK: scripts/verify.sh:19 declares CHECK_unit="required:python3
scripts/selftest.py", so every assertion here can turn the gate red. An assertion that pinned this
repository's EMPTY estimate ledger, its ABSENT price record or its spend-free event stream would
therefore go red the first time somebody committed an estimate, declared a rate or recorded a
token - a number from this item stopping work, which is the exact NG1 failure AC5 exists to close,
arriving through the suite rather than through the module. It was that: `coverage["estimated"] ==
0`, `not (ROOT/".veldo"/"estimates").exists()`, `len(_read_events(ROOT)) > 1000` with "empty
ledger" pinned beside it, PLAN-0004's `token_position is None`, and the real view's pacing window
pinned empty. MEASURED: with one estimate written for WARP-1401 through the real writer, one rate
declared and one spend event appended, the PRE-FIX fragment went `40 passed, 2 failed` while the
tree was doing nothing wrong, and this one reports 45 passed over that same tree.

So the rule here is: over ROOT, assert only that a reading TRACKS the records on disk (an equality
against a recount, or a biconditional against the state that decides it), bound to a non-empty work
list and a non-empty stream so a failed parse still reds; over FIXTURE trees, assert the SHAPES -
the empty ledger, the unpriced money block, the standdown reasons - where they keep their teeth
whatever this repository later contains.

THE ASSERTIONS WERE WATCHED FAILING. Nine mutations were driven into BOTH copies of
.veldo/toe_budget.py, one at a time, each reverted before the next, and the reds below are what
was actually observed (baseline for this fragment: 45 passed, 0 failed):

  1. combine_ranges summing the lows changed to taking the MIN low: 7 RED (the sum identity, the
     mediant sandwich, monotonicity, the program sum, the pacing position, all four pacing
     boundaries and the cap positions). AND THE INSTRUCTIVE PART, which is why the exact-sum
     assertion is written the way it is: the MONEY CONTAINMENT assertion stayed GREEN, because
     it converts the same (mutated) low it compares against, so it is self-consistent and blind.
     A ratio-only check would have been blind too, since a min-low WIDENS the spread. Only the
     assertion that recomputes the sum from the items catches this class.
  2. an unpriced range reporting 0 and "0.00" instead of None and "unpriced": 1 RED, the
     unpriced-is-not-zero assertion, with its priced control green. That pair is what makes it a
     measurement of the branch and not of the module in general.
  3. `up=True` dropped from the money high bound so both bounds floor: 1 RED, the containment
     assertion and only that one, which is what makes it attributable to the rounding DIRECTION
     rather than to the conversion.
  4. the recorded flag forced True: 2 RED, both empty-ledger standdowns (the seeded one and the
     one measured over this repository), while every pacing BOUNDARY assertion stayed green
     because those seed recorded spend. Absence and zero are different facts and only the
     standdown pair tells them apart.
  5. pacing_windows offering the LOW bound: 1 RED, and it is the one that matters most, because
     the governor returns ZERO WORKERS when a window's budget is spent.
  6. the PARTIAL guard deleted from pacing_windows: 1 RED.
  7. a malformed record left OUT of problems while still excluded from the sum (the silent-drop
     defect, not the silent-include one): 1 RED, the fail-closed assertion.
  8. the CLI exiting non-zero when the range is over the declared cap: 1 RED, the advisory
     exit-code assertion. This is the mutation that matters for NG1, and it is caught by a real
     process rather than by reading the source.
  9. the ADVISORY marker flipped to blocks True: 3 RED, the six-shape sweep plus both engine-tree
     assertions, which is what proves the marker is carried by the shapes and not only declared
     once at the top of the module. Coverage's `complete` forced True reddened 3 (partial,
     program, pacing-window standdown), and program partiality not propagating reddened 1.

AND THE REMEDIATION ROUND, driven the same way (both twins edited together, each mutation diffed
before the run so a replace that matched nothing could not pass for a check that cannot fail):

 10. `spread_pct` inverted to `low * 100 // high`: 1 RED, the false-confidence guard. The mediant
     sandwich alone was blind to it - reciprocals preserve the sandwich - and so was the strictness
     clause. `high * 1000 // low`, percent silently rescaled to per-mille, is the other member of
     that class and it reds the same assertion. Controls from the earlier round still hold:
     `return 200` and `return high - low` each red 1.
 11. the money HIGH bound wired to round DOWN (`up=True` -> `up=False`): 1 RED, the directional
     assertion, which now pins the REPORTED strings on the inexact view ("<0.01" and "0.01") where
     the two directions differ. The LOW bound wired UP reds the same one, and neither was
     observable while only render_usd's own literals and the micro-USD integers were checked.
 12. `program_rollup`'s weakest-link calibration forced to "calibrated": 1 RED, the program
     calibration pair. `all` -> `any` reds it too, which the previous fixture set could not do
     because every contributor in it was uncalibrated.
 13. the PARTIAL standdown in `pacing_windows` reverted to the plan-shaped format string: 1 RED,
     the program-seam assertion, naming `RAISED KeyError: 'estimated'` through _w1408_pace rather
     than taking the whole fragment down with a traceback. Dropping the no-range guard reds 2 (the
     plan seam and the program seam).
 14. and the adaptive real-tree readings, each reddened by one edit TODAY, on the empty ledger, so
     that dropping the pinned zeros did not buy a set of checks that cannot fail: `missing` forced
     to [] reds 3, no-range returning 0 instead of None reds 9 (including the fixture-tree shape),
     the recorded flag forced True reds 2, the declared cap rescaled reds the PLAN-0004 reading,
     and the neither-shape refusal turned into a silent string reds the program seam.
"""
import re as _w1408_re
import shutil as _w1408_shutil


def _w1408_load(name, rel):
    """One engine module, loaded by path the way shared.py loads validate.py."""
    _s = importlib.util.spec_from_file_location(name, ROOT / rel)
    _m = importlib.util.module_from_spec(_s)
    _s.loader.exec_module(_m)
    return _m


T1408 = _w1408_load("w1408_toe_budget", ".veldo/toe_budget.py")
E1408 = _w1408_load("w1408_estimate", ".veldo/estimate.py")
B1408 = _w1408_load("w1408_budget", ".veldo/budget.py")
G1408 = _w1408_load("w1408_governor", ".veldo/governor.py")
FR1408 = _w1408_load("w1408_frontier", ".veldo/frontier.py")
C1408 = _w1408_load("w1408_toe_corpus", ".veldo/toe_corpus.py")


def _w1408_raises(fn, *a, **kw):
    """(raised, message). The message is returned because that is what carries the refusal: an
    assertion that something raised, without checking WHAT, passes on a stray TypeError."""
    try:
        fn(*a, **kw)
    except BaseException as e:
        return True, "%s: %s" % (type(e).__name__, e)
    return False, ""


def _w1408_est(sid, low, high, basis="uncalibrated_prior", layer="structural_proxy"):
    """One estimate record built through the REAL veldo.estimate/v1 builder, so every number
    this fragment sums has already been through that schema's own refusals. A hand-built dict
    here would let this suite roll up a shape the estimator can never produce."""
    return E1408.build_record(sid, "2026-08-10", [{
        "layer": layer, "basis": basis, "low": low, "high": high,
        "inputs": {"acceptance_criteria": 3}}])


def _w1408_plan(pid, specs, budgets_text=""):
    """A plan's front matter as a dict, through the ONE parser rather than as a literal, so the
    roll-up is driven over exactly the shape validate.plan_registry hands it."""
    lines = ["schema: veldo.plan/v1", "id: %s" % pid, "title: fixture", "work:"]
    for i, s in enumerate(specs, 1):
        lines += ["  - item: W%d" % i, "    spec: %s" % s, "    depends_on: []"]
    return V.parse_yamlish("\n".join(lines) + "\n" + budgets_text)


class _W1408PermissiveEstimate(object):
    """A stand-in for the estimate module that ACCEPTS every record, and nothing else.

    It exists for exactly one assertion. The roll-up refuses to add a record whose unit is not
    tokens, and that branch is UNREACHABLE today by construction, because estimate.UNITS
    declares `tokens` alone and the real validator refuses any other unit first. Reaching a
    guard that only fires after a future item widens that vocabulary needs a validator that
    lets the record through, and pretending the guard is tested without one would be the
    vacuous half of a pass."""

    @staticmethod
    def validate_record(rec, spec_id=None):
        return []


_W1408_PRICE = {"schema": T1408.SCHEMA_PRICE, "usd_micros_per_1k_tokens": 3000,
                "model": "fixture-model-a", "source": "a fixture rate, not a real price",
                "observed_at": "2026-08-10"}
# A WIDE range and a NARROW one on purpose: the whole false-confidence question is what a sum
# does when its contributors disagree about how much is unknown.
_W1408_WIDE = _w1408_est("WARP-9401", 100000, 625000)      # spread 625 percent
_W1408_NARROW = _w1408_est("WARP-9402", 200000, 220000)    # spread 110 percent
_W1408_FM2 = _w1408_plan("PLAN-9414", ["WARP-9401", "WARP-9402"])
_W1408_ESTS2 = {"WARP-9401": _W1408_WIDE, "WARP-9402": _W1408_NARROW}
_W1408_SPEND = {"tokens": 150000, "recorded": True, "source": "fixture"}


def _w1408_roll(fm=None, ests=None, price=None, spend=None, rule=T1408.SUM_BOUNDS, E=None):
    """The roll-up under test, through the REAL estimate schema and the REAL budget owner
    unless a case explicitly needs otherwise: a stubbed owner everywhere would let this
    fragment prove agreement with a fiction."""
    return T1408.rollup(fm if fm is not None else _W1408_FM2,
                        _W1408_ESTS2 if ests is None else ests,
                        price=price, spend=spend, rule=rule, E=E or E1408, B=B1408)


_W1408_FULL = _w1408_roll(price=_W1408_PRICE, spend=_W1408_SPEND)

# -----------------------------------------------------------------------------------
# AC1. THE ROLL-UP IS INTERVAL ADDITION, DECLARED, RECOMPUTED, AND IT NEVER NARROWS.
# -----------------------------------------------------------------------------------
expect("WARP-1408 AC1 POSITIVE CONTROL: a two-item roll-up over records built by the REAL "
       "veldo.estimate/v1 builder sums the bounds exactly - the total low is the sum of the item "
       "lows and the total high the sum of the item highs, recomputed here from the items "
       "themselves rather than compared to a pinned literal - and it is none of the "
       "point-producing combinations. Every refusal below is therefore a refusal of the MUTATION "
       "and not of the shape in general",
       _W1408_FULL["tokens"]["low"] == sum(r["low"] for r in _W1408_FULL["items"])
       and _W1408_FULL["tokens"]["high"] == sum(r["high"] for r in _W1408_FULL["items"])
       and (_W1408_FULL["tokens"]["low"], _W1408_FULL["tokens"]["high"]) == (300000, 845000)
       and _W1408_FULL["rule"] == T1408.SUM_BOUNDS
       and _W1408_FULL["coverage"]["complete"] is True)

_w1408_spreads = [r["spread_pct"] for r in _W1408_FULL["items"]]
_w1408_three = _w1408_roll(
    fm=_w1408_plan("PLAN-9415", ["WARP-9401", "WARP-9402", "WARP-9403"]),
    ests=dict(_W1408_ESTS2, **{"WARP-9403": _w1408_est("WARP-9403", 10000, 11000)}))
expect("WARP-1408 AC1, THE FALSE-CONFIDENCE GUARD: a WIDE range (625 percent) and a NARROW one "
       "(110 percent) do not average into confidence. Under sum_bounds the total's spread is a "
       "weighted mediant of the item spreads, so it is SANDWICHED between the tightest and the "
       "widest item - it can never be tighter than the narrowest thing inside it - and both "
       "sides of that sandwich are asserted, on two different item sets, with the exact sums "
       "asserted separately above so the sandwich cannot be reached by fudging the bounds. "
       "AND THE DEFINITION IS PINNED BY VALUE, not only by relation: spread is HIGH OVER LOW as "
       "a percent, asserted on two literals and recomputed for the total from the bound sums. "
       "The sandwich alone cannot tell high/low from low/high, because taking the reciprocal of "
       "every term preserves it and rescaling percent into per-mille preserves it too - both "
       "mutations were green before these three clauses, and an inverted definition would print "
       "a 6.25x range to a human as spread 16%",
       T1408.spread_pct(100000, 625000) == 625
       and T1408.spread_pct(200000, 220000) == 110
       and _W1408_FULL["tokens"]["spread_pct"] == 845000 * 100 // 300000
       and min(_w1408_spreads) <= _W1408_FULL["tokens"]["spread_pct"] <= max(_w1408_spreads)
       and _W1408_FULL["tokens"]["spread_pct"] > min(_w1408_spreads)
       and min(r["spread_pct"] for r in _w1408_three["items"])
       <= _w1408_three["tokens"]["spread_pct"]
       <= max(r["spread_pct"] for r in _w1408_three["items"]))

_w1408_one = _w1408_roll(fm=_w1408_plan("PLAN-9416", ["WARP-9401"]))
expect("WARP-1408 AC1 MONOTONE AND NOT A CONSTANT (the anti-vacuity control): adding an item "
       "strictly raises BOTH bounds, across one, two and three items, and the three roll-ups "
       "produce three DISTINCT ranges. A roll-up that returned one constant would satisfy every "
       "refusal assertion in this fragment and be worthless",
       _w1408_one["tokens"]["low"] < _W1408_FULL["tokens"]["low"] < _w1408_three["tokens"]["low"]
       and _w1408_one["tokens"]["high"] < _W1408_FULL["tokens"]["high"]
       < _w1408_three["tokens"]["high"]
       and len({(v["tokens"]["low"], v["tokens"]["high"])
                for v in (_w1408_one, _W1408_FULL, _w1408_three)}) == 3)

_w1408_rss = _w1408_raises(T1408.check_rule, "root_sum_square")
_w1408_mean = _w1408_raises(T1408.check_rule, "mean")
expect("WARP-1408 AC1: THE COMBINATIONS THAT WOULD MANUFACTURE CONFIDENCE ARE REFUSED BY NAME "
       "WITH THE REASON, from a declared table. root_sum_square is refused for the reason it is "
       "wrong HERE (quadrature narrows a total by assuming the item errors are INDEPENDENT, and "
       "every range in this repository comes from one estimator under one declared prior), mean, "
       "midpoint and pert are refused for producing a POINT, and a rule named nowhere is refused "
       "with the declared set. A refusal that only says no sends the next person to read code",
       _w1408_rss[0] and "INDEPENDENT" in _w1408_rss[1] and "REFUSED" in _w1408_rss[1]
       and _w1408_mean[0] and "POINT" in _w1408_mean[1]
       and all(_w1408_raises(T1408.check_rule, r)[0] for r in T1408.REFUSED_RULES)
       and "v1 declares" in _w1408_raises(T1408.check_rule, "vibes")[1]
       and _w1408_raises(T1408.check_rule, T1408.SUM_BOUNDS) == (False, ""))

expect("WARP-1408 AC1: A REFUSED RULE IS REFUSED AT EVERY DOOR, not only the front one: "
       "combine_ranges, rollup and program_rollup each raise on it, so no caller reaches the "
       "arithmetic around the check. And the EMPTY set is refused too, naming the ABSENCE OF "
       "EVIDENCE rather than returning a vacuous (0, 0), because a sum over nothing is exactly "
       "the confident zero this item exists to refuse",
       _w1408_raises(T1408.combine_ranges, [(1, 2)], "mean")[0]
       and _w1408_raises(_w1408_roll, None, None, None, None, "mean")[0]
       and _w1408_raises(T1408.program_rollup, [_W1408_FULL], "mean")[0]
       and _w1408_raises(T1408.combine_ranges, [])[0]
       and "absence of evidence" in _w1408_raises(T1408.combine_ranges, [])[1])

_w1408_broken = _w1408_roll(ests={"WARP-9401": _W1408_WIDE,
                                  "WARP-9402": dict(_W1408_NARROW, high=_W1408_NARROW["low"])})
expect("WARP-1408 AC1 FAIL CLOSED ON A RECORD THIS ROLL-UP CANNOT ADD: a MALFORMED estimate (a "
       "POINT range, which veldo.estimate/v1 refuses) is EXCLUDED from the sum, NAMED in "
       "problems, and counted as unestimated - never silently added and never silently dropped. "
       "The total becomes the sum of the remaining valid item, recomputed here, so the exclusion "
       "is visible in the arithmetic and not only in the prose. Every record is re-validated "
       "through the estimate module's OWN validator, so the roll-up and the estimator can never "
       "disagree about what a valid record is",
       _w1408_broken["tokens"]["low"] == _W1408_WIDE["low"]
       and _w1408_broken["tokens"]["high"] == _W1408_WIDE["high"]
       and _w1408_broken["coverage"]["estimated"] == 1
       and len(_w1408_broken["problems"]) == 1
       and "POINT" in _w1408_broken["problems"][0]
       and "WARP-9402" in _w1408_broken["problems"][0])

_w1408_foreign = dict(_W1408_NARROW, unit="story_points")
_w1408_unit_guard = _w1408_roll(ests={"WARP-9401": _W1408_WIDE, "WARP-9402": _w1408_foreign},
                                E=_W1408PermissiveEstimate)
expect("WARP-1408 AC1: TWO UNITS ARE NEVER ADDED. A record whose unit is not tokens is excluded "
       "and NAMED as not summable rather than converted by a factor nobody declared. That guard "
       "is UNREACHABLE today by construction - estimate.UNITS declares tokens alone, asserted "
       "here as a SET EQUALITY so a later item widening that vocabulary reds this and is sent "
       "straight to this guard - so it is driven through a permissive validator, which is the "
       "only honest way to observe a branch that fires only after that widening",
       set(E1408.UNITS) == {T1408.UNIT_TOKENS}
       and "unit" in " ".join(E1408.validate_record(_w1408_foreign))
       and _w1408_unit_guard["coverage"]["estimated"] == 1
       and "not summable" in " ".join(_w1408_unit_guard["problems"])
       and _w1408_unit_guard["tokens"]["high"] == _W1408_WIDE["high"])

# -----------------------------------------------------------------------------------
# AC2. A PARTIAL SUM IS NEVER PRESENTED AS A PLAN'S RANGE.
# -----------------------------------------------------------------------------------
_w1408_none = _w1408_roll(fm=_w1408_plan("PLAN-9424", ["WARP-9401", "WARP-9402"]),
                          ests={}, price=_W1408_PRICE, spend=_W1408_SPEND)
_w1408_partial = _w1408_roll(fm=_w1408_plan("PLAN-9425", ["WARP-9401", "WARP-9402"]),
                             ests={"WARP-9401": _W1408_WIDE}, price=_W1408_PRICE)
expect("WARP-1408 AC2, THE ONE THAT MATTERS MOST HERE: A PLAN WITH NO ESTIMATES GETS NO RANGE, "
       "not a zero. low and high are None, the reason NAMES the confident zero it refuses and "
       "counts the items still waiting, and the money and pacing blocks stand down with their "
       "own reasons instead of printing figures over an empty set. Paired with its control: the "
       "same code with two records present DOES produce a range, so the standdown is the "
       "coverage's doing and not a branch that never returns a number",
       _w1408_none["tokens"]["low"] is None and _w1408_none["tokens"]["high"] is None
       and "confident zero" in _w1408_none["reason"]
       and _w1408_none["money"]["priced"] is False
       and _w1408_none["pacing"]["available"] is False
       and _W1408_FULL["tokens"]["low"] is not None)

expect("WARP-1408 AC2: A PARTIAL ROLL-UP SAYS PARTIAL, NAMES THE MISSING ITEMS AND SAYS WHICH "
       "DIRECTION IT IS WRONG IN. complete is False, missing carries the unestimated spec ids, "
       "and the reason says the number UNDERSTATES the plan - because a partial sum read as a "
       "plan's range is not merely incomplete, it is biased LOW, and a reader who is not told "
       "that will plan against it",
       _w1408_partial["coverage"]["complete"] is False
       and _w1408_partial["coverage"]["missing"] == ["WARP-9402"]
       and "PARTIAL" in _w1408_partial["reason"]
       and "understates" in _w1408_partial["reason"]
       and _W1408_FULL["coverage"]["missing"] == []
       and _W1408_FULL["reason"] is None)

# MEASURED OVER THIS REPOSITORY'S OWN BYTES, not over a fixture - AND ADAPTIVE BY CONSTRUCTION.
# THIS FRAGMENT RUNS UNDER THE GATE'S REQUIRED CHECK_unit SLOT (scripts/verify.sh:19), so an
# assertion here that pinned today's empty estimate ledger, absent price record or spend-free
# stream would turn a REQUIRED gate slot red the first time somebody committed an estimate,
# declared a rate or recorded a token - a number from this item stopping work, which is exactly
# the NG1 failure AC5 exists to close. Every reading over ROOT is therefore asserted as TRACKING
# the records on disk; every empty-ledger SHAPE is asserted over a FIXTURE tree instead.
_W1408_REAL = T1408.build_view("PLAN-0014")
_W1408_REAL_FM = V.plan_registry(ROOT / "plans")["PLAN-0014"]["fm"]
_W1408_REAL_WORK = B1408.plan_work_specs(_W1408_REAL_FM)
_W1408_REAL_ESTS = E1408.load_dir(ROOT / E1408.ESTIMATES_DIR)[0]
# The roll-up's own admission test, recomputed here from the bytes on disk: a record must be
# PRESENT for that item, VALID under the estimate module's own validator, and in TOKENS to be
# summable. Anything else is unestimated, which is what `missing` must then list.
_W1408_REAL_SUMMABLE = [_s for _s in _W1408_REAL_WORK
                        if _s in _W1408_REAL_ESTS
                        and E1408.validate_record(_W1408_REAL_ESTS[_s], spec_id=_s) == []
                        and _W1408_REAL_ESTS[_s].get("unit") == T1408.UNIT_TOKENS]
_W1408_REAL_PRICE = T1408.read_price(root=ROOT, parse=V.parse_yamlish)
expect("WARP-1408 AC2 MEASURED OVER THE REAL PLAN-0014, AS TRACKING AND NEVER AS A PINNED ZERO: "
       "the view's item list IS the plan's own work list read through budget.plan_work_specs, "
       "the estimated count EQUALS the summable records found on disk for those items, `missing` "
       "is exactly the rest in the plan's own order, a range exists IF AND ONLY IF something is "
       "estimated, and money is priced IF AND ONLY IF a rate is declared and there is a range. "
       "Bound to a NON-EMPTY work list, so a parse that found nothing reds instead of passing "
       "over an empty set. MEASURED 2026-08-10 that reads 10 items, 0 estimated, no range, "
       "unpriced - and not one clause here asserts that zero, because this fragment is a "
       "REQUIRED gate check and the first committed estimate must move it, not break it",
       [_r["spec"] for _r in _W1408_REAL["items"]] == _W1408_REAL_WORK
       and _W1408_REAL_WORK != []
       and _W1408_REAL["coverage"]["items"] == len(_W1408_REAL_WORK)
       and _W1408_REAL["coverage"]["estimated"] == len(_W1408_REAL_SUMMABLE)
       and _W1408_REAL["coverage"]["missing"] == [_s for _s in _W1408_REAL_WORK
                                                  if _s not in _W1408_REAL_SUMMABLE]
       and (_W1408_REAL["tokens"]["low"] is None) == (_W1408_REAL_SUMMABLE == [])
       and (_W1408_REAL["money"]["priced"] is True)
       == (_W1408_REAL_PRICE is not None and _W1408_REAL["tokens"]["low"] is not None))

_W1408_EMPTY_PLANFILE = """---
schema: veldo.plan/v1
id: PLAN-9430
title: empty-ledger fixture plan
status: in_progress
revision: 1
owner: selftest
work:
  - item: W1
    spec: WARP-9401
    depends_on: []
  - item: W2
    spec: WARP-9402
    depends_on: []
---
body
"""

with tempfile.TemporaryDirectory() as _w1408_emptyd:
    _w1408_emptyroot = Path(_w1408_emptyd) / "repo"
    (_w1408_emptyroot / "plans").mkdir(parents=True)
    (_w1408_emptyroot / ".veldo").mkdir()
    (_w1408_emptyroot / "plans" / "PLAN-9430.md").write_text(_W1408_EMPTY_PLANFILE)
    _w1408_emptyview = T1408.build_view("PLAN-9430", root=_w1408_emptyroot)
    expect("WARP-1408 AC2 THE EMPTY-LEDGER SHAPE, ASSERTED OVER A FIXTURE TREE RATHER THAN OVER "
           "THIS REPOSITORY'S EMPTINESS: over a root carrying a plan and a .veldo with NO "
           "estimates directory in it, build_view reads 0 of 2 estimated, NAMES both items still "
           "waiting, has NO range (None on both bounds, never 0), refuses the confident zero BY "
           "NAME and reads UNPRICED with the word where a figure would go. The tree is the "
           "fixture's, so this keeps its teeth on the day this repository commits its first "
           "estimate - which is precisely what the same claim asserted against ROOT turned into: "
           "a REQUIRED gate slot that goes red the first time the feature is used",
           not (_w1408_emptyroot / ".veldo" / "estimates").exists()
           and _w1408_emptyview["coverage"]["items"] == 2
           and _w1408_emptyview["coverage"]["estimated"] == 0
           and _w1408_emptyview["coverage"]["missing"] == ["WARP-9401", "WARP-9402"]
           and _w1408_emptyview["tokens"]["low"] is None
           and _w1408_emptyview["tokens"]["high"] is None
           and "confident zero" in _w1408_emptyview["reason"]
           and _w1408_emptyview["money"]["priced"] is False
           and _w1408_emptyview["money"]["usd_low"] == "unpriced"
           and _w1408_emptyview["money"]["usd_micros_high"] is None)

_w1408_prog = T1408.program_rollup([_W1408_FULL, _w1408_partial, _w1408_none])
expect("WARP-1408 AC2 PROGRAM ROLL-UP: a program's range is the sum of its plans' ranges under "
       "the same rule, recomputed here from the contributing plans; a plan with NO range "
       "contributes nothing and is NAMED rather than counted as zero; and partiality PROPAGATES "
       "UPWARD, because a program containing one partial plan is partial and a total that forgot "
       "that would be the same lie one layer up",
       _w1408_prog["tokens"]["low"]
       == _W1408_FULL["tokens"]["low"] + _w1408_partial["tokens"]["low"]
       and _w1408_prog["tokens"]["high"]
       == _W1408_FULL["tokens"]["high"] + _w1408_partial["tokens"]["high"]
       and _w1408_prog["coverage"]["with_range"] == 2
       and _w1408_prog["coverage"]["without_range"] == 1
       and _w1408_prog["coverage"]["complete"] is False
       and sorted(_w1408_prog["coverage"]["partial_plans"]) == ["PLAN-9424", "PLAN-9425"]
       and T1408.program_rollup([_W1408_FULL])["coverage"]["complete"] is True)

_w1408_other_rate = dict(_W1408_PRICE, usd_micros_per_1k_tokens=9000, model="fixture-model-b")
_w1408_two_rates = T1408.program_rollup(
    [_W1408_FULL, _w1408_roll(price=_w1408_other_rate, spend=_W1408_SPEND)])
_w1408_one_unpriced = T1408.program_rollup([_W1408_FULL, _w1408_roll()])
expect("WARP-1408 AC2 PROGRAM MONEY IS NOT BLENDED ACROSS RATES OR ACROSS SILENCE. Two plans "
       "priced at two DIFFERENT rates are two different units, so the program total stands down "
       "naming them rather than producing a mixture wearing one number's clothes; and a program "
       "where one contributing plan is UNPRICED stands down too, because omitting it would "
       "understate the program while looking complete. Control: two plans at ONE rate DO price",
       _w1408_two_rates["money"]["priced"] is False
       and "DIFFERENT rates" in _w1408_two_rates["money"]["reason"]
       and _w1408_one_unpriced["money"]["priced"] is False
       and "unpriced is not zero" in _w1408_one_unpriced["money"]["reason"]
       and T1408.program_rollup([_W1408_FULL, _w1408_roll(price=_W1408_PRICE)])
       ["money"]["priced"] is True)

# -----------------------------------------------------------------------------------
# AC3. THE DOLLAR RANGE: A DECLARED RATE WITH RECORDED PROVENANCE, AND UNPRICED IS NOT ZERO.
# -----------------------------------------------------------------------------------
expect("WARP-1408 AC3 POSITIVE CONTROL: the fixture rate record validates CLEAN and round trips "
       "through the ONE parser - render_price writes it and validate.parse_yamlish reads back the "
       "identical mapping. The writer is bound to the reader by that round trip rather than by a "
       "second copy of the parser's rules, so a value the parser would change is refused at write "
       "time instead of discovered by whoever reads the record next",
       T1408.validate_price(_W1408_PRICE) == []
       and V.parse_yamlish(T1408.render_price(_W1408_PRICE, parse=V.parse_yamlish))
       == _W1408_PRICE
       and _w1408_raises(T1408.render_price, dict(_W1408_PRICE, note="two\nlines"))[0])

expect("WARP-1408 AC3: A RATE WITHOUT ITS PROVENANCE IS REFUSED BY NAME, field by field. A "
       "missing source, model, observed_at or rate is each refused with the field named; a "
       "non-integer rate is refused (the front-matter subset has no float, so it would arrive as "
       "a string); a rate of ZERO is refused specifically, because it would price every range at "
       "nothing; an unknown key and a wrong schema are refused rather than ignored. A rate is the "
       "one number in this chain that comes from outside the repository entirely, so it does not "
       "get to arrive anonymously",
       all(T1408.validate_price({k: v for k, v in _W1408_PRICE.items() if k != drop}) != []
           and drop in " ".join(T1408.validate_price(
               {k: v for k, v in _W1408_PRICE.items() if k != drop}))
           for drop in ("source", "model", "observed_at", "usd_micros_per_1k_tokens"))
       and "INTEGER" in " ".join(T1408.validate_price(
           dict(_W1408_PRICE, usd_micros_per_1k_tokens="3000")))
       and "greater than zero" in " ".join(T1408.validate_price(
           dict(_W1408_PRICE, usd_micros_per_1k_tokens=0)))
       and "unknown key" in " ".join(T1408.validate_price(dict(_W1408_PRICE, currency="usd")))
       and "schema must be" in " ".join(T1408.validate_price(
           dict(_W1408_PRICE, schema="veldo.price/v9"))))

expect("WARP-1408 AC3 CONTROL ON THAT TIGHTNESS: the OPTIONAL note set to another legal value is "
       "ACCEPTED, so the refusals above are not a validator that reds on any edit at all. A "
       "validator that refuses everything passes every negative assertion and proves nothing",
       T1408.validate_price(dict(_W1408_PRICE, note="a different one-line note")) == [])

_w1408_unpriced = _w1408_roll(spend=_W1408_SPEND)
expect("WARP-1408 AC3, UNPRICED IS NOT ZERO: with no rate the money block reads priced False, "
       "every money FIELD is None, the displayed figures read the word unpriced, and the reason "
       "says unpriced is not free. The absence of a zero is checked as the absence of a zero "
       "VALUE and not as a string search, because a cost printed as zero is the single output "
       "this module exists to prevent. Control: the same range WITH a rate carries integer "
       "micro-USD bounds",
       _w1408_unpriced["money"]["priced"] is False
       and _w1408_unpriced["money"]["usd_micros_low"] is None
       and _w1408_unpriced["money"]["usd_micros_high"] is None
       and _w1408_unpriced["money"]["usd_low"] == "unpriced"
       and "not free" in _w1408_unpriced["money"]["reason"]
       and 0 not in [_w1408_unpriced["money"][k]
                     for k in ("usd_micros_low", "usd_micros_high")]
       and isinstance(_W1408_FULL["money"]["usd_micros_low"], int)
       and isinstance(_W1408_FULL["money"]["usd_micros_high"], int))

_w1408_odd = T1408.rollup(_w1408_plan("PLAN-9426", ["WARP-9401"]),
                          {"WARP-9401": _w1408_est("WARP-9401", 333, 1667)},
                          price=dict(_W1408_PRICE, usd_micros_per_1k_tokens=3001),
                          E=E1408, B=B1408)
def _w1408_cents(shown):
    """A DISPLAYED dollar figure back to whole cents, or None when the figure names no cent
    count at all ("<0.01", "unpriced"). Containment is a claim about the printed interval and a
    string is not a number, so something has to convert one: without this the display side of
    the directional rule could only be checked against the helper's own literals."""
    if not _w1408_re.match(r"^-?\d+\.\d\d$", shown or ""):
        return None
    _whole, _frac = shown.lstrip("-").split(".")
    _c = int(_whole) * 100 + int(_frac)
    return -_c if shown.startswith("-") else _c


expect("WARP-1408 AC3: THE MONEY ROUNDING IS DIRECTIONAL, SO IT CAN ONLY WIDEN. The low bound "
       "FLOORS and the high bound CEILS in integer arithmetic, so the money interval CONTAINS "
       "the exact one - driven on a range and a rate where the division is deliberately inexact "
       "(333 and 1667 tokens at 3001 micro-USD per 1k) as well as on the round fixture - and the "
       "bounds stay strictly apart, so rounding never collapses money into a point either. AND "
       "THE ASSERTION IS ABOUT THE FIGURES THE VIEW REPORTS, not only about the micro-USD "
       "integers and not only about render_usd in isolation: the two REPORTED strings are pinned "
       "on the inexact view, where the two directions differ ('<0.01' and '0.01'), and the "
       "printed cents are held to the same containment as the micros on both views. Wiring the "
       "high bound to round DOWN - or the low bound UP - was green while only the helper and the "
       "micros were checked, and it ships a money range NARROWER than the exact one",
       _w1408_odd["money"]["usd_low"] == "<0.01"
       and _w1408_odd["money"]["usd_high"] == "0.01"
       and _W1408_FULL["money"]["usd_low"] == "0.90"
       and _W1408_FULL["money"]["usd_high"] == "2.54"
       and all(_w1408_cents(_v["money"]["usd_high"]) is not None
               and _w1408_cents(_v["money"]["usd_high"]) * T1408.MICROS_PER_CENT
               >= _v["money"]["usd_micros_high"]
               and ((_w1408_cents(_v["money"]["usd_low"]) * T1408.MICROS_PER_CENT
                     <= _v["money"]["usd_micros_low"])
                    if _w1408_cents(_v["money"]["usd_low"]) is not None
                    else _v["money"]["usd_micros_low"] < T1408.MICROS_PER_CENT)
               for _v in (_W1408_FULL, _w1408_odd))
       and _W1408_FULL["money"]["usd_micros_low"]
       <= _W1408_FULL["tokens"]["low"] * 3000 / 1000.0
       and _W1408_FULL["money"]["usd_micros_high"]
       >= _W1408_FULL["tokens"]["high"] * 3000 / 1000.0
       and _w1408_odd["money"]["usd_micros_low"] <= 333 * 3001 / 1000.0
       and _w1408_odd["money"]["usd_micros_high"] >= 1667 * 3001 / 1000.0
       and _w1408_odd["money"]["usd_micros_low"] < _w1408_odd["money"]["usd_micros_high"]
       and T1408.usd_micros(1667, 3001, up=False) < T1408.usd_micros(1667, 3001, up=True))

expect("WARP-1408 AC3: THE DISPLAY ROUNDS THE SAME DIRECTION AS THE BOUND IT SHOWS, so the "
       "PRINTED interval contains the exact one too - 1999999 micro-USD shows as 1.99 for a low "
       "bound and 2.00 for a high one - and a non-zero amount below one cent renders <0.01 "
       "rather than 0.00. A truncating display would quietly narrow every money range it "
       "printed, and a sub-cent cost printed as 0.00 is the confident zero in a different costume",
       T1408.render_usd(1999999) == "1.99" and T1408.render_usd(1999999, up=True) == "2.00"
       and T1408.render_usd(5000) == "<0.01" and T1408.render_usd(5000, up=True) == "0.01"
       and T1408.render_usd(0) == "0.00" and T1408.render_usd(None) == "unpriced")

expect("WARP-1408 AC3: MONEY CANNOT BE OBTAINED WITHOUT SAYING WHERE THE RATE CAME FROM. "
       "price_from_args refuses a bare number three ways - no model, no source, no observed_at - "
       "through the SAME validator a committed record goes through, and accepts the complete "
       "one. That is what makes provenance a property rather than a convention: the quick-look "
       "path is exactly as strict as the committed path",
       _w1408_raises(T1408.price_from_args, 3000, None, "s", "2026-08-10")[0]
       and _w1408_raises(T1408.price_from_args, 3000, "m", None, "2026-08-10")[0]
       and _w1408_raises(T1408.price_from_args, 3000, "m", "s", None)[0]
       and T1408.price_from_args(3000, "m", "s", "2026-08-10")["source"] == "s")

_w1408_calibrated = _w1408_roll(
    ests={"WARP-9401": _w1408_est("WARP-9401", 100000, 625000, basis="corpus_analogy",
                                  layer="historical_analogy"),
          "WARP-9402": _w1408_est("WARP-9402", 200000, 220000, basis="corpus_analogy",
                                  layer="historical_analogy")},
    price=_W1408_PRICE)
_w1408_mixed_cal = _w1408_roll(
    ests={"WARP-9401": _w1408_est("WARP-9401", 100000, 625000, basis="corpus_analogy",
                                  layer="historical_analogy"),
          "WARP-9402": _W1408_NARROW},
    price=_W1408_PRICE)
expect("WARP-1408 AC3: CALIBRATION TRAVELS WITH THE SUM AND THE WEAKEST LINK GOVERNS IT. A total "
       "reads calibrated only when EVERY contributing estimate is; one uncalibrated item makes "
       "the total uncalibrated, because one unmeasured contributor is enough to leave the total's "
       "error unmeasured. And the money CAVEAT carries that word plus the rate's model, so a "
       "dollar figure can never be read as measured when the range beneath it is not",
       _w1408_calibrated["calibration"] == "calibrated"
       and _w1408_mixed_cal["calibration"] == "uncalibrated"
       and _W1408_FULL["calibration"] == "uncalibrated"
       and "uncalibrated" in _W1408_FULL["money"]["caveat"]
       and "fixture-model-a" in _W1408_FULL["money"]["caveat"]
       and "no model stamp" in _W1408_FULL["money"]["caveat"])

_w1408_cal_a = _w1408_roll(
    fm=_w1408_plan("PLAN-9431", ["WARP-9401"]),
    ests={"WARP-9401": _w1408_est("WARP-9401", 100000, 625000, basis="corpus_analogy",
                                  layer="historical_analogy")},
    price=_W1408_PRICE)
_w1408_prog_cal = T1408.program_rollup([_w1408_calibrated, _w1408_cal_a])
_w1408_prog_mixed = T1408.program_rollup([_w1408_calibrated, _W1408_FULL])
expect("WARP-1408 AC2 AND AC3: THE WEAKEST LINK GOVERNS A PROGRAM TOTAL TOO, AND THAT WORD RIDES "
       "INTO THE PROGRAM MONEY CAVEAT. A program over two FULLY CALIBRATED plan views reads "
       "calibrated and its caveat says the range is calibrated; swap ONE contributor for an "
       "uncalibrated plan and both flip. It takes a MIXED program to observe this at all - in a "
       "program where every contributor is uncalibrated, inverting all() to any() is invisible - "
       "which is why a PAIR is built here rather than a pin added: before it, forcing every "
       "program total to read `calibrated` was green while that word travelled into a dollar "
       "caveat over uncalibrated inputs, and a dollar figure that reads as measured when its "
       "range is not is the honesty failure this whole item is shaped around",
       [_v["calibration"] for _v in (_w1408_calibrated, _w1408_cal_a)]
       == ["calibrated", "calibrated"]
       and _w1408_prog_cal["calibration"] == "calibrated"
       and "the range is calibrated" in _w1408_prog_cal["money"]["caveat"]
       and _w1408_prog_mixed["calibration"] == "uncalibrated"
       and "the range is uncalibrated" in _w1408_prog_mixed["money"]["caveat"]
       and _w1408_prog["calibration"] == "uncalibrated")

# -----------------------------------------------------------------------------------
# AC4. PACING READS RECORDED SPEND THROUGH ITS OWNER, AND STANDS DOWN ON AN EMPTY LEDGER.
# -----------------------------------------------------------------------------------
_W1408_EVENTS = [
    {"schema": "veldo.event/v1", "type": "spec.shipped", "at": "2026-08-09T10:00:00Z",
     "correlation_id": "WARP-9401", "tokens": 90000, "cost_usd": 0.27},
    {"schema": "veldo.event/v1", "type": "spec.shipped", "at": "2026-08-09T11:00:00Z",
     "correlation_id": "WARP-9402", "tokens": 60000, "cost_usd": 0.18},
]
_w1408_sv = T1408.plan_spend_view(_W1408_FM2, _W1408_EVENTS, B=B1408, C=C1408)
_w1408_corpus_sum = sum(C1408.spend_for(_W1408_EVENTS, c)["tokens"]
                        for c in [_W1408_FM2.get("id")] + B1408.plan_work_specs(_W1408_FM2))
expect("WARP-1408 AC4: THE SPEND NUMBER COMES FROM ITS OWNER AND THERE IS NO SECOND "
       "CALCULATION. The total is budget.plan_spend (which reads metrics.compute, the ONE spend "
       "aggregation in this system, and owns which correlations belong to a plan) and the "
       "RECORDED FLAG is toe_corpus.spend_for (which owns what carrying spend means). The two "
       "are asserted EQUAL on the same seeded events, so a divergence between the enforcer's "
       "number and the advisor's reds this instead of quietly producing two numbers for one plan",
       _w1408_sv["tokens"] == B1408.plan_spend(_W1408_FM2, _W1408_EVENTS)["tokens"]
       and _w1408_sv["tokens"] == _w1408_corpus_sum
       and _w1408_sv["tokens"] == 150000
       and _w1408_sv["recorded"] is True)

_w1408_empty_sv = T1408.plan_spend_view(_W1408_FM2, [], B=B1408, C=C1408)
_w1408_empty_pace = _w1408_roll(spend=_w1408_empty_sv, price=_W1408_PRICE)["pacing"]
expect("WARP-1408 AC4, THE ZERO THAT WOULD BE A LIE: an empty ledger reads NOT RECORDED, never 0 "
       "percent consumed. spend_recorded is False, the position and both percentages are None, "
       "and the reason says a 0 percent figure would read as a measurement of being on track "
       "rather than as an empty ledger. Paired with the control that seeded spend DOES produce a "
       "position and percentages, so the standdown is the ledger's doing and not a dead branch",
       _w1408_empty_sv["recorded"] is False and _w1408_empty_sv["tokens"] == 0
       and _w1408_empty_pace["available"] is False
       and _w1408_empty_pace["position"] is None
       and _w1408_empty_pace["of_low_pct"] is None
       and "empty ledger" in _w1408_empty_pace["reason"]
       and _W1408_FULL["pacing"]["available"] is True
       and _W1408_FULL["pacing"]["position"] == "under_low")

_W1408_REAL_EVS = T1408._read_events(ROOT)
_W1408_REAL_RECORDED = any(
    C1408.spend_for(_W1408_REAL_EVS, _c)["spend_recorded"]
    for _c in [_W1408_REAL_FM.get("id")] + _W1408_REAL_WORK if _c)
expect("WARP-1408 AC4 MEASURED OVER THIS REPOSITORY'S REAL STREAM, AS TRACKING AND NEVER AS A "
       "PINNED ABSENCE: the pacing block's recorded flag EQUALS toe_corpus.spend_for recomputed "
       "by this fragment over the SAME events and the SAME correlations, a position is available "
       "IF AND ONLY IF spend is recorded and a range exists, and the empty-ledger REASON appears "
       "exactly when nothing is recorded and not otherwise. Bound to a NON-EMPTY stream, so a log "
       "nobody could read reds this instead of passing as an honest absence - the difference "
       "between measuring a gap and failing to look. MEASURED 2026-08-10: over a thousand events "
       "and not one carrying tokens, cost_usd or human_minutes; the first recorded token moves "
       "every clause with the data instead of reddening a REQUIRED gate slot",
       len(_W1408_REAL_EVS) > 0
       and _W1408_REAL["pacing"]["spend_recorded"] == _W1408_REAL_RECORDED
       and _W1408_REAL["pacing"]["available"] == (_W1408_REAL_RECORDED
                                                 and _W1408_REAL["tokens"]["low"] is not None)
       and ("empty ledger" in (_W1408_REAL["pacing"]["reason"] or ""))
       == (not _W1408_REAL_RECORDED))

_w1408_pos = [T1408._pacing(300000, 845000,
                            {"tokens": n, "recorded": True, "source": "fixture"})["position"]
              for n in (299999, 300000, 845000, 845001)]
expect("WARP-1408 AC4: THE POSITION IS EXACT AT ALL FOUR BOUNDARIES - one token below the low is "
       "under_low, the low itself is in_range, the high itself is in_range, one token above the "
       "high is over_high - and both percentages are computed against the bounds they name. An "
       "off-by-one at a boundary is how a plan reads as on track on the day it goes over",
       _w1408_pos == ["under_low", "in_range", "in_range", "over_high"]
       and _W1408_FULL["pacing"]["of_low_pct"] == 150000 * 100 // 300000
       and _W1408_FULL["pacing"]["of_high_pct"] == 150000 * 100 // 845000)

_w1408_win, _w1408_win_why = T1408.pacing_windows(_W1408_FULL, [("session", 14400)])
_w1408_nowin, _w1408_nowin_why = T1408.pacing_windows(_w1408_none, [("session", 14400)])
_w1408_partwin, _w1408_partwin_why = T1408.pacing_windows(_w1408_partial, [("session", 14400)])
_W1408_REALWIN = T1408.pacing_windows(_W1408_REAL, [("session", 14400)])
expect("WARP-1408 AC4: THE PACING SEAM OFFERS THE HIGH BOUND AND NEVER THE LOW, and it offers "
       "NOTHING at all when there is no range or when the roll-up is PARTIAL, each with its "
       "reason named. This is the one place in this item where a number could stop work: the "
       "governor returns ZERO WORKERS when a window's budget is spent, so the optimistic end of "
       "a range as a cap would stall real work, and a partial range would throttle a whole pool "
       "against a number known to be too small. Measured over the REAL PLAN-0014: no window at "
       "all, so this repository's empty estimate ledger cannot reach a pacer even by accident",
       len(_w1408_win) == 1
       and _w1408_win[0]["tokens"] == _W1408_FULL["tokens"]["high"]
       and _w1408_win[0]["tokens"] != _W1408_FULL["tokens"]["low"]
       and _w1408_win[0]["bound"] == "high" and _w1408_win[0]["advisory"] is True
       and _w1408_win_why is None
       and _w1408_nowin == [] and "no range" in _w1408_nowin_why
       and _w1408_partwin == [] and "PARTIAL" in _w1408_partwin_why
       and (_W1408_REALWIN[0] != []) == (_W1408_REAL["tokens"]["high"] is not None
                                         and _W1408_REAL["coverage"]["complete"])
       and (_W1408_REALWIN[1] is None) == (_W1408_REALWIN[0] != [])
       and all(_w["tokens"] == _W1408_REAL["tokens"]["high"] and _w["bound"] == "high"
               for _w in _W1408_REALWIN[0]))

def _w1408_pace(view):
    """(windows, reason), or (None, the RAISED message) when the seam raises.

    A CRASH ON THIS SEAM MUST BE A NAMED RED, not a traceback that takes the whole fragment
    down before any assertion is reached: that is the difference between a report naming the
    branch that broke and a stack dump somebody has to attribute by hand. The shape this
    guards against is not hypothetical - the seam raised KeyError('estimated') on a PARTIAL
    program view, which is the branch that exists to stand down safely."""
    try:
        return T1408.pacing_windows(view, [("session", 14400)])
    except BaseException as e:
        return None, "RAISED %s: %s" % (type(e).__name__, e)


_w1408_progwin, _w1408_progwin_why = _w1408_pace(
    T1408.program_rollup([_W1408_FULL, _w1408_one]))
_w1408_progpart, _w1408_progpart_why = _w1408_pace(_w1408_prog)
_w1408_progempty, _w1408_progempty_why = _w1408_pace(T1408.program_rollup([_w1408_none]))
_w1408_badshape = _w1408_raises(T1408.pacing_windows,
                                {"tokens": {"high": 5}, "coverage": {"complete": False}},
                                [("session", 14400)])
expect("WARP-1408 AC4: THE PACING SEAM STANDS DOWN ON A PROGRAM ROLL-UP EXACTLY AS IT DOES ON A "
       "PLAN'S, AND IT NO LONGER DIES ON ONE. program_rollup is a public surface producing the "
       "same tokens block, so a caller reaching this seam with one is ordinary - and a PARTIAL "
       "program view used to reach a plan-shaped message and raise KeyError('estimated'), which is "
       "a CRASH on the safety-critical branch while the complete case sailed through and emitted a "
       "window. Now: a partial program returns no window with PARTIAL and the partial plans NAMED, "
       "a program with no contributing range returns no window naming that, a COMPLETE program "
       "returns the program's HIGH bound recomputed here as the sum of its plans' highs, and a "
       "view whose coverage block is NEITHER shape is refused BY NAME rather than by traceback",
       _w1408_progpart == [] and "PARTIAL" in _w1408_progpart_why
       and "PLAN-9425" in _w1408_progpart_why and "PLAN-9424" in _w1408_progpart_why
       and _w1408_progempty == [] and "no range" in _w1408_progempty_why
       and _w1408_progwin is not None and len(_w1408_progwin) == 1
       and _w1408_progwin[0]["tokens"] == (_W1408_FULL["tokens"]["high"]
                                           + _w1408_one["tokens"]["high"])
       and _w1408_progwin[0]["bound"] == "high" and _w1408_progwin_why is None
       and _w1408_badshape[0] and "NEITHER" in _w1408_badshape[1])

_w1408_gov_windows = [G1408.Window(w["name"], w["seconds"], w["tokens"]) for w in _w1408_win]
_w1408_burnt = [{"schema": "veldo.event/v1", "type": "spec.shipped",
                 "at": "2026-08-09T12:00:00Z", "correlation_id": "WARP-9401",
                 "tokens": _W1408_FULL["tokens"]["high"] + 1}]
_w1408_burn_at = G1408._tokens_at(_w1408_burnt)[0][0]
expect("WARP-1408 AC4: THE REAL GOVERNOR CONSUMES THESE NUMBERS UNMODIFIED. Its own "
       "Window(name, seconds, tokens) is built from the shapes this module emits and driven "
       "through the real desired_workers: with no burn it runs workers, and with burn past the "
       "window it runs none - which is the GOVERNOR'S pre-existing law over a declared budget, "
       "unchanged, and not something this module decides. And it is genuinely a DATA seam: after "
       "a full view and a pacing_windows call, this module's own loader cache contains no "
       "governor at all, and what it emitted is a plain dict",
       G1408.desired_workers(_w1408_gov_windows, [], _w1408_burn_at, 0.0, 4) == 4
       and G1408.desired_workers(_w1408_gov_windows, _w1408_burnt,
                                 _w1408_burn_at + 60, 1.0, 4) == 0
       and all("governor" not in rel for (_r, rel) in T1408._MODS)
       and isinstance(_w1408_win[0], dict)
       and _w1408_raises(G1408.Window, "w", 1, 0)[0])

_w1408_capped = T1408.rollup(
    _w1408_plan("PLAN-9427", ["WARP-9401", "WARP-9402"],
                budgets_text="budgets:\n  tokens: 1000\n  cost_usd: 0.5\n"),
    _W1408_ESTS2, price=_W1408_PRICE, spend=_W1408_SPEND, E=E1408, B=B1408)
_w1408_roomy = T1408.rollup(
    _w1408_plan("PLAN-9428", ["WARP-9401", "WARP-9402"],
                budgets_text="budgets:\n  tokens: 99000000\n  cost_usd: 900.0\n"),
    _W1408_ESTS2, price=_W1408_PRICE, spend=_W1408_SPEND, E=E1408, B=B1408)
_w1408_badcap = T1408.rollup(
    _w1408_plan("PLAN-9429", ["WARP-9401"], budgets_text="budgets:\n  tokens: lots\n"),
    _W1408_ESTS2, price=_W1408_PRICE, E=E1408, B=B1408)
expect("WARP-1408 AC4: THE DECLARED CAP IS READ THROUGH budget.parse_budgets AND NEVER PARSED A "
       "SECOND WAY. A range wholly above the cap reads over_cap on tokens and on dollars, a "
       "roomy cap reads under_cap on both, and a MALFORMED budgets block is reported with that "
       "module's OWN refusal rather than crashing or being interpreted differently here. "
       "over_cap is a word in a report: the exit-code assertion in AC5 is what makes that load "
       "bearing",
       _w1408_capped["cap"]["token_position"] == "over_cap"
       and _w1408_capped["cap"]["cost_position"] == "over_cap"
       and _w1408_roomy["cap"]["token_position"] == "under_cap"
       and _w1408_roomy["cap"]["cost_position"] == "under_cap"
       and _w1408_badcap["cap"]["declared"] is False
       and "malformed" in _w1408_badcap["cap"]["reason"]
       and _w1408_raises(B1408.parse_budgets, {"budgets": {"tokens": "lots"}})[0])

_W1408_REAL_0004 = T1408.build_view("PLAN-0004")
_W1408_CAPS_0004 = B1408.parse_budgets(V.plan_registry(ROOT / "plans")["PLAN-0004"]["fm"])
expect("WARP-1408 AC4 MEASURED OVER THE ONE PLAN IN THIS REPOSITORY THAT DECLARES A BUDGET: "
       "PLAN-0004's cap is read through budget.parse_budgets from real bytes and travels into the "
       "view UNMODIFIED - asserted against that module's OWN answer rather than against a literal, "
       "so a rescale or a dropped field reds while a founder legitimately changing the cap does "
       "not - and the cap's POSITION is None if and only if there is nothing to place against it. "
       "MEASURED 2026-08-10: 20,000,000 tokens declared and NO range, because none of its work "
       "items carries an estimate. A cap that is read and a range that is absent is the state this "
       "repository is in, and the report says both rather than filling the gap with a zero; the "
       "biconditional is what keeps that honest once an estimate exists, instead of pinning the "
       "absence into a REQUIRED gate check",
       _W1408_REAL_0004["cap"]["declared"] is True
       and _W1408_REAL_0004["cap"]["tokens"] == _W1408_CAPS_0004.get("tokens")
       and _W1408_REAL_0004["cap"]["tokens"] > 0
       and _W1408_REAL_0004["cap"]["cost_usd"] == _W1408_CAPS_0004.get("cost_usd")
       and (_W1408_REAL_0004["cap"]["token_position"] is None)
       == (_W1408_REAL_0004["tokens"]["low"] is None
           or _W1408_REAL_0004["cap"]["tokens"] is None))

# -----------------------------------------------------------------------------------
# AC5. ADVISORY BY DESIGN, AND ADOPTION SAFE. The load-bearing pair of this item.
# -----------------------------------------------------------------------------------
_W1408_SPEC = """---
schema: veldo.spec/v1
id: %s
title: budget roll-up fixture
status: ready
risk: standard
owner: selftest
lane: planned
plan: PLAN-9420
work: %s
placement: [metrics]
footprint:
  - ".veldo/nothing_%s.py"
acceptance_criteria:
  - id: AC1
    text: something observable happens.
required_evidence: [unit]
rollback: git revert
---
body
"""
_W1408_PLANFILE = """---
schema: veldo.plan/v1
id: PLAN-9420
title: advisory fixture plan
status: in_progress
revision: 1
owner: selftest
budgets:
  tokens: 1000
work:
  - item: W1
    spec: WARP-9420
    depends_on: []
  - item: W2
    spec: WARP-9421
    depends_on: []
---
body
"""

with tempfile.TemporaryDirectory() as _w1408_d:
    _w1408_root = Path(_w1408_d) / "repo"
    (_w1408_root / ".veldo").mkdir(parents=True)
    (_w1408_root / "specs").mkdir()
    (_w1408_root / "plans").mkdir()
    _w1408_claims = Path(_w1408_d) / "claims"
    _w1408_claims.mkdir()
    for _w1408_rel in (".veldo/architecture.yaml", ".veldo/policy.yaml"):
        _w1408_shutil.copy(ROOT / _w1408_rel, _w1408_root / _w1408_rel)
    (_w1408_root / "plans" / "PLAN-9420.md").write_text(_W1408_PLANFILE)
    (_w1408_root / "specs" / "WARP-9420.md").write_text(_W1408_SPEC % ("WARP-9420", "W1", "a"))
    (_w1408_root / "specs" / "WARP-9421.md").write_text(_W1408_SPEC % ("WARP-9421", "W2", "b"))
    _w1408_estdir = _w1408_root / ".veldo" / "estimates"

    def _w1408_claimset():
        return sorted(u["spec"] for u in FR1408.claimable(
            worker_caps=[], repo_root=_w1408_root, claims_root=_w1408_claims))

    def _w1408_specerrs():
        return (V.check_spec(_w1408_root / "specs" / "WARP-9420.md", repo_root=_w1408_root),
                V.check_spec(_w1408_root / "specs" / "WARP-9421.md", repo_root=_w1408_root))

    _w1408_before = _w1408_claimset()
    _w1408_spec_before = _w1408_specerrs()

    # STATE TWO: two committed estimates whose roll-up is 845,000 tokens against this plan's
    # declared cap of 1,000. Over by nearly three orders of magnitude, on purpose.
    E1408.write_record(_w1408_est("WARP-9420", 100000, 625000), dirpath=_w1408_estdir)
    E1408.write_record(_w1408_est("WARP-9421", 200000, 220000), dirpath=_w1408_estdir)
    _w1408_over = T1408.build_view("PLAN-9420", root=_w1408_root)
    _w1408_after = _w1408_claimset()
    _w1408_spec_after = _w1408_specerrs()

    # STATE THREE: a MALFORMED price record present on disk beside them.
    (_w1408_root / T1408.PRICE_FILE).write_text(
        "schema: veldo.toe_token_price/v1\nusd_micros_per_1k_tokens: 0\n")
    _w1408_broken_price = _w1408_claimset()
    _w1408_spec_broken = _w1408_specerrs()
    _w1408_price_refusal = _w1408_raises(T1408.read_price, None, _w1408_root, V.parse_yamlish)

    expect("WARP-1408 AC5, THE LOAD-BEARING ONE: NO NUMBER THIS ITEM PRODUCES CAN DELAY A UNIT "
           "OF WORK, measured by driving the REAL frontier.claimable over a hermetic repository "
           "root three times - with no estimates, with estimates whose roll-up is hundreds of "
           "times this plan's declared token cap, and with a MALFORMED price record present - "
           "and getting the IDENTICAL claimable set every time. The frontier is the surface that "
           "decides what work may be pulled, so this is the actual delay path and not a proxy "
           "for it, and the roll-up genuinely does read over_cap in the middle of it",
           _w1408_before == _w1408_after == _w1408_broken_price
           and _w1408_before == ["WARP-9420", "WARP-9421"]
           and _w1408_over["cap"]["token_position"] == "over_cap")

    # THE NEGATIVE CONTROL for that identity: the same frontier over the same root DOES withhold
    # a unit when a real prerequisite is unshipped, so the three identical sets are the estimate
    # being irrelevant rather than this fixture being inert.
    (_w1408_root / "specs" / "WARP-9421.md").write_text(
        (_W1408_SPEC % ("WARP-9421", "W2", "b")).replace(
            "lane: planned", "depends_on: [WARP-9499]\nlane: planned"))
    _w1408_withheld = _w1408_claimset()
    expect("WARP-1408 AC5 NEGATIVE CONTROL FOR THAT PASS: the SAME frontier over the SAME root "
           "DOES shrink when a spec declares an unshipped prerequisite, so the three identical "
           "sets above are the estimate being invisible and not the frontier being blind under "
           "this fixture. Without this control the whole assertion would be a pass earned by "
           "looking nowhere",
           _w1408_withheld == ["WARP-9420"] and len(_w1408_withheld) < len(_w1408_before))

    expect("WARP-1408 AC5: AN ESTIMATE, A ROLL-UP OVER ITS CAP AND A BROKEN PRICE RECORD ARE ALL "
           "INVISIBLE TO SPEC VALIDATION TOO. The real validate.check_spec returns the identical "
           "zero in all three states, which is PLAN-0014 C3 as a measurement: these records live "
           "BESIDE the spec, so neither their absence nor their breakage can invalidate one. And "
           "the broken price record IS broken - read_price refuses it by name and does not fall "
           "back to a default rate, so this is not three zeros over an unnoticed file",
           _w1408_spec_before == _w1408_spec_after == _w1408_spec_broken == (0, 0)
           and _w1408_price_refusal[0]
           and "greater than zero" in _w1408_price_refusal[1])

    _w1408_bad_spec = _w1408_root / "specs" / "WARP-9422.md"
    _w1408_bad_spec.write_text((_W1408_SPEC % ("WARP-9422", "W1", "c")).replace(
        "status: ready", "status: donezo"))
    expect("WARP-1408 AC5 NEGATIVE CONTROL FOR THOSE ZEROS: the same validator over the same "
           "root DOES refuse a genuinely broken spec, so the identical zeros above are the "
           "records being irrelevant and not check_spec being inert here",
           V.check_spec(_w1408_bad_spec, repo_root=_w1408_root) > 0)

    # The CLI as a real process over the same fixture root, with the price record repaired so
    # the money line is real. The plan is hundreds of times over its declared cap; exit is 0.
    (_w1408_root / T1408.PRICE_FILE).write_text(
        T1408.render_price(_W1408_PRICE, parse=V.parse_yamlish))
    _w1408_cli = subprocess.run(
        [sys.executable, str(ROOT / ".veldo/toe_budget.py"), "rollup", "PLAN-9420",
         "--root", str(_w1408_root)], capture_output=True, text=True, cwd=str(ROOT))
    _w1408_planfm = V.plan_registry(_w1408_root / "plans")["PLAN-9420"]["fm"]
    _w1408_enforcer = B1408.check(_w1408_planfm, [
        {"schema": "veldo.event/v1", "type": "spec.shipped", "at": "2026-08-09T10:00:00Z",
         "correlation_id": "WARP-9420", "tokens": 5000}])
    expect("WARP-1408 AC5: OVER THE DECLARED CAP, THE REPORT EXITS 0 AND SAYS ADVISORY, driven "
           "as a real process. Paired with the control that the PRE-EXISTING enforcer "
           "(budget.check) over the SAME plan front matter with recorded spend past the SAME cap "
           "DOES return a violation - so the zero is this module's posture and not a dead "
           "fixture, and the division of labour is measured rather than asserted: budget.py "
           "enforces recorded spend against a declared cap, this advises a derived range "
           "against it",
           _w1408_cli.returncode == 0
           and "over_cap" in _w1408_cli.stdout
           and "ADVISORY" in _w1408_cli.stdout
           and "blocks nothing" in _w1408_cli.stdout
           and len(_w1408_enforcer) == 1
           and _w1408_enforcer[0]["resource"] == "tokens")

    _w1408_cli_missing = subprocess.run(
        [sys.executable, str(ROOT / ".veldo/toe_budget.py"), "rollup", "PLAN-9420",
         "--root", str(_w1408_d)], capture_output=True, text=True, cwd=str(ROOT))
    expect("WARP-1408 AC5: A PLAN NOBODY CAN FIND IS A REFUSAL TO REPORT - non-zero, naming "
           "where it looked - which is a different thing from refusing WORK. Nothing in the gate "
           "calls this module, so no exit code of its own reaches anything that decides whether "
           "a change lands; every ADVISORY verdict, including over the cap, exits 0",
           _w1408_cli_missing.returncode == 1
           and "no plan found" in _w1408_cli_missing.stderr)

    # ADOPTION SAFETY, measured as the absence of writes rather than argued.
    _w1408_bare = Path(_w1408_d) / "bare"
    (_w1408_bare / "plans").mkdir(parents=True)
    (_w1408_bare / "plans" / "PLAN-9420.md").write_text(_W1408_PLANFILE)
    _w1408_bare_view = T1408.build_view("PLAN-9420", root=_w1408_bare)
    expect("WARP-1408 AC5 ADOPTION SAFE AND WRITES NOTHING: over a root holding a plan and "
           "NOTHING else - no estimates directory, no price record, no event log - every reader "
           "stands down with its reason and the tree is UNCHANGED afterwards: no .veldo, no "
           "estimates directory, no price file, no events.jsonl created. A reporting surface "
           "that created its own inputs would make adoption a mutation",
           _w1408_bare_view["tokens"]["low"] is None
           and _w1408_bare_view["money"]["priced"] is False
           and not (_w1408_bare / ".veldo").exists()
           and sorted(p.name for p in _w1408_bare.iterdir()) == ["plans"])

    expect("WARP-1408 AC5: THE VIEW IS DETERMINISTIC AND READS NO CLOCK. Two build_views over "
           "one root are equal, and the module's source names no subprocess, socket or urllib "
           "import, no Popen and no wall-clock call, so it cannot spawn a process, open a "
           "connection or vary by the hour (NG5). The determinism half is behavioural and is "
           "what actually carries the clock claim; the text half is the weaker one and is "
           "stated as such",
           T1408.build_view("PLAN-9420", root=_w1408_bare) == _w1408_bare_view
           and all(tok not in (ROOT / ".veldo/toe_budget.py").read_text()
                   for tok in ("import subprocess", "import socket", "import urllib",
                               "Popen(", "datetime.now", "time.time")))

    # THE ADOPTER'S TREE, exactly as /veldo:init lays it down: the ENGINE canon. Measured
    # 2026-08-10, it ships no budget.py, so the twin must IMPORT there and STAND DOWN BY NAME.
    _w1408_engine = Path(_w1408_d) / "adopter"
    _w1408_shutil.copytree(ROOT / "engine" / ".veldo", _w1408_engine / ".veldo")
    _w1408_engine_has_budget = (_w1408_engine / ".veldo" / "budget.py").exists()
    _w1408_espec = importlib.util.spec_from_file_location(
        "w1408_engine_toe_budget", _w1408_engine / ".veldo" / "toe_budget.py")
    T1408E = importlib.util.module_from_spec(_w1408_espec)
    _w1408_espec.loader.exec_module(T1408E)
    _w1408_engine_view = T1408E.rollup(_W1408_FM2, _W1408_ESTS2, price=_W1408_PRICE)
    expect("WARP-1408 AC5: THE TWIN IMPORTS AND BEHAVES IN THE TREE /veldo:init LAYS DOWN, and "
           "it is true in BOTH worlds so it stays honest as the engine grows: the twin is loaded "
           "from a COPY of engine/.veldo and, when that tree ships budget.py, it produces a real "
           "range, while when it does not it stands down naming .veldo/budget.py as the owner it "
           "is missing. Either way it imports cleanly and carries the advisory marker - never an "
           "ImportError, and never a plan's work items and spend attribution recomputed under a "
           "second rule of its own",
           (T1408E._budget() is not None) == _w1408_engine_has_budget
           and ((_w1408_engine_view["tokens"]["low"] is not None) if _w1408_engine_has_budget
                else (_w1408_engine_view["tokens"]["low"] is None
                      and "budget.py" in _w1408_engine_view["reason"]))
           and _w1408_engine_view["advisory"]["blocks"] is False)

    # And the standdown itself, over a tree DETERMINISTICALLY missing the owner, so this
    # assertion keeps its teeth on the day the engine gains budget.py.
    _w1408_nobudget = Path(_w1408_d) / "nobudget"
    _w1408_shutil.copytree(ROOT / "engine" / ".veldo", _w1408_nobudget / ".veldo")
    if (_w1408_nobudget / ".veldo" / "budget.py").exists():
        (_w1408_nobudget / ".veldo" / "budget.py").unlink()
    _w1408_nbspec = importlib.util.spec_from_file_location(
        "w1408_nobudget_toe_budget", _w1408_nobudget / ".veldo" / "toe_budget.py")
    T1408N = importlib.util.module_from_spec(_w1408_nbspec)
    _w1408_nbspec.loader.exec_module(T1408N)
    _w1408_nb_view = T1408N.rollup(_W1408_FM2, _W1408_ESTS2, price=_W1408_PRICE)
    expect("WARP-1408 AC5: AN ENGINE TREE WITHOUT .veldo/budget.py IMPORTS THIS MODULE AND "
           "STANDS DOWN BY NAME, driven over a tree with that file deliberately removed so the "
           "assertion keeps its teeth whatever the engine ships later. The roll-up has no range, "
           "the pacing and the cap each name the missing owner, and nothing raises: fail closed "
           "and by name, because recomputing which correlations a plan's spend belongs to under "
           "a local rule is how two readers of one log start disagreeing",
           T1408N._budget() is None
           and _w1408_nb_view["tokens"]["low"] is None
           and "budget.py" in _w1408_nb_view["reason"]
           and "budget.py" in _w1408_nb_view["pacing"]["reason"]
           and "budget.py" in _w1408_nb_view["cap"]["reason"]
           and _w1408_nb_view["advisory"]["blocks"] is False)

_w1408_gate_text = (ROOT / "scripts/verify.sh").read_text()
_w1408_slots = _w1408_re.findall(r"CHECK_\w+=\"[^\"]*\"", _w1408_gate_text)
expect("WARP-1408 AC5: NOTHING IN THE GATE NAMES THIS MODULE. scripts/verify.sh declares no slot "
       "mentioning toe_budget.py, and neither does the contract validator it runs, so no path "
       "through the gate can refuse, block or delay work on a roll-up, a dollar figure or a cap. "
       "Bound to a non-empty slot list, so a parse that found no slots reds this rather than "
       "passing over nothing. This is the WEAKER half: the frontier and check_spec measurements "
       "above are what carry NG1",
       _w1408_slots != [] and all("toe_budget" not in s for s in _w1408_slots)
       and "toe_budget" not in _w1408_gate_text
       and "toe_budget" not in (ROOT / ".veldo/validate.py").read_text())

expect("WARP-1408 AC5: EVERY SHAPE THIS MODULE PRODUCES CARRIES THE ADVISORY MARKER AS A FIELD, "
       "asserted across all six of them - complete, partial, no-estimates, over-cap, program, "
       "and the real PLAN-0014 view. It is a field rather than a docstring promise so a consumer "
       "can assert it, and this sweep is what stops a later shape shipping without it",
       all(v["advisory"]["blocks"] is False and "never gates" in v["advisory"]["note"]
           for v in (_W1408_FULL, _w1408_partial, _w1408_none, _w1408_capped, _w1408_prog,
                     _W1408_REAL))
       and T1408.ADVISORY["blocks"] is False)

expect("WARP-1408 AC5: THE MODULE AND THE EXAMPLE RATE RECORD ARE BYTE-IDENTICAL IN BOTH ENGINE "
       "HOMES, so what /veldo:init lays down for an adopter is the module this repository runs "
       "and proves, and the example an adopter copies is the one validated here",
       (ROOT / ".veldo/toe_budget.py").read_bytes()
       == (ROOT / "engine/.veldo/toe_budget.py").read_bytes()
       and (ROOT / ".veldo/examples/toe-token-price-example.yaml").read_bytes()
       == (ROOT / "engine/.veldo/examples/toe-token-price-example.yaml").read_bytes())

_w1408_ex = V.parse_yamlish(
    (ROOT / ".veldo/examples/toe-token-price-example.yaml").read_text())
expect("WARP-1408 AC5: THE COMMITTED EXAMPLE RATE RECORD IS VALID, checked as real bytes on disk "
       "through the ONE parser rather than as a fixture built in this file, so the documented "
       "shape cannot drift from the shape the validator accepts. Its rate is a positive integer "
       "in micro-USD and it carries all three provenance fields, because an example that taught "
       "the anonymous form would teach the one thing this schema refuses",
       T1408.validate_price(_w1408_ex) == []
       and isinstance(_w1408_ex["usd_micros_per_1k_tokens"], int)
       and _w1408_ex["usd_micros_per_1k_tokens"] > 0
       and all(_w1408_ex.get(k) for k in ("model", "source", "observed_at")))

del _w1408_re, _w1408_shutil
