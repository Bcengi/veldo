"""WARP-1407: human-judgment load, the second axis of effort, and the pair it is half of.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Run it alone with
`python3 scripts/selftest.py --suite 15_warp_1407_judgment_load`, which runs this fragment plus
its declared prerequisite closure - itself alone. Every name it uses from the shared namespace
(expect, ROOT, importlib, json, tempfile, Path) is bound by shared.py, which always runs; its own
two imports are prefixed and local.

WHAT IS OBSERVED HERE, AND WHY IT IS SHAPED THIS WAY. The product under test is an HONESTY
mechanism: a pair whose second axis has no data in this repository at all. So the assertion that
matters most is a NEGATIVE one - that an unrecorded axis is reported as unrecorded and never as a
cheap one - and a negative assertion is worthless unless the positive case is also driven. Every
property below is therefore asserted TWICE: once over seeded data where the figure exists and the
shape must be named, and once over seeded data where it does not and the shape must be unknown. A
check that passed because nothing was there would fail the first half; a check that always found
something would fail the second.

TEETH, MEASURED RATHER THAN CLAIMED. Six deliberate breaks were driven and watched go red on
`--suite 15_warp_1407_judgment_load`, which is 54 passing assertions unmodified:
  1. Disabling the missing-axis branch in `classify`, so a missing axis falls through to the median
     comparison and an unrecorded zero reads as a low figure: 49 passed, 1 FAILED - the AC3 row.
     WARP-9406, three review episodes and not one recorded minute, came back labelled
     cheap_on_both with the reason "medians over the 4 record(s) carrying both axes", which is a
     confident lie in the exact shape this item exists to prevent.
  2. Making `_figure_problem` tolerant of a string figure: 47 passed, 3 FAILED (the string-refusal
     row, the check_log row, and the one-judge row that binds the raise to the report).
  3. Dropping human_minutes from the seeded verdict event, a FIXTURE break rather than a code one:
     44 passed, 6 FAILED (AC1 pair, split, rendered line and plan roll-up; AC2 reference medians;
     AC3 corpus-equality) - which is what proves those rows read the seeded figure rather than
     asserting a shape that would hold over any data.
  4. Making the figure renderer `"%d" % value` unconditionally, so a fractional figure truncates:
     1 FAILED, the fractional-rendering row.
  5. Re-deriving `classifiable` in coverage from the module's own floor instead of reading the
     reference it was handed: 1 FAILED. This is the one that needed a designed input - the two
     spellings AGREE on every ordinary corpus, so the assertion hands coverage a reference built on
     a different floor, which is the only shape that tells them apart.
  6. Relaxing the median comparison from `>` to `>=`: 1 FAILED, the row for a record sitting exactly
     at both medians, which then reads as expensive on both.
Each was reverted; what is here is the file that goes green over the unmodified module.
"""
import hashlib as _jl_hashlib

_jl_spec_mod = importlib.util.spec_from_file_location(
    "veldo_judgment_load_suite", ROOT / ".veldo/judgment_load.py")
JL = importlib.util.module_from_spec(_jl_spec_mod)
_jl_spec_mod.loader.exec_module(JL)

_jl_tc_spec = importlib.util.spec_from_file_location(
    "veldo_toe_corpus_suite_1407", ROOT / ".veldo/toe_corpus.py")
JLTC = importlib.util.module_from_spec(_jl_tc_spec)
_jl_tc_spec.loader.exec_module(JLTC)

_jl_sp_spec = importlib.util.spec_from_file_location(
    "veldo_spend_suite_1407", ROOT / ".veldo/spend.py")
JLSP = importlib.util.module_from_spec(_jl_sp_spec)
_jl_sp_spec.loader.exec_module(JLSP)

_jl_ev_spec = importlib.util.spec_from_file_location(
    "veldo_events_suite_1407", ROOT / ".veldo/events.py")
JLEV = importlib.util.module_from_spec(_jl_ev_spec)
_jl_ev_spec.loader.exec_module(JLEV)


def _jl_spec_text(spec_id, plan=None, approval="not_required", footprint=(".veldo/x.py",), acs=2):
    """One shipped-spec fixture. Written into a temp specs directory, never into specs/, so the real
    corpus and the real contract validation never see these ids."""
    fm = ["---", "schema: veldo.spec/v1", "id: %s" % spec_id,
          "title: judgment load fixture", "status: shipped",
          "risk: standard - fixture", "owner: selftest",
          "human_approval: %s" % approval]
    fm += (["lane: planned", "plan: %s" % plan, "work: W1"] if plan else ["lane: standalone"])
    fm += ["footprint:"] + ['  - "%s"' % f for f in footprint] + ["acceptance_criteria:"]
    for i in range(1, acs + 1):
        fm += ["  - id: AC%d" % i, "    text: fixture criterion."]
    fm += ["---", "", "## Outcome", "", "fixture.", ""]
    return "\n".join(fm)


def _jl_ev(etype, spec, **kw):
    ev = {"schema": "veldo.event/v1", "type": etype, "at": "2026-08-10T00:00:00Z", "spec_id": spec}
    ev.update(kw)
    return ev


# ---------------------------------------------------------------------------------------
# THE SEEDED WORLD. Six shipped specs, chosen so that all four shape labels AND both flavours of
# unknown appear at once:
#   9401 minutes recorded ONLY on spec.shipped, the way the one real recorder writes them
#   9402 minutes on a verdict and an approval: cheap in tokens, expensive in judgment
#   9403 expensive in tokens, cheap in judgment, with three judgment episodes
#   9404 expensive on both
#   9405 no events at all: both axes unrecorded
#   9406 three review episodes and NOT ONE recorded minute: the row this whole item is about
# ---------------------------------------------------------------------------------------
_JL_EVENTS = [
    _jl_ev("spec.shipped", "WARP-9401", tokens=100, human_minutes=10),
    _jl_ev("verdict.recorded", "WARP-9402", human_minutes=20),
    _jl_ev("approval.recorded", "WARP-9402", human_minutes=40),
    _jl_ev("spec.shipped", "WARP-9402", tokens=50),
    _jl_ev("spec.shipped", "WARP-9403", tokens=1000, human_minutes=5),
    _jl_ev("verdict.recorded", "WARP-9403"),
    _jl_ev("verdict.recorded", "WARP-9403"),
    _jl_ev("review.requested", "WARP-9403"),
    _jl_ev("spec.shipped", "WARP-9404", tokens=2000, human_minutes=100),
    _jl_ev("approval.recorded", "WARP-9404"),
    _jl_ev("verdict.recorded", "WARP-9406"),
    _jl_ev("verdict.recorded", "WARP-9406"),
    _jl_ev("verdict.recorded", "WARP-9406"),
]
_JL_SPECS = {
    "WARP-9401": {"plan": "PLAN-9400"},
    "WARP-9402": {"plan": "PLAN-9400", "approval": "required"},
    "WARP-9403": {"plan": "PLAN-9400"},
    "WARP-9404": {"plan": "PLAN-9401"},
    "WARP-9405": {"plan": "PLAN-9401"},
    "WARP-9406": {},
}
_JL_IDS = sorted(_JL_SPECS)

with tempfile.TemporaryDirectory() as _jl_dir:
    _jl_specs_dir = Path(_jl_dir) / "specs"
    _jl_specs_dir.mkdir()
    for _sid, _opts in sorted(_JL_SPECS.items()):
        (_jl_specs_dir / ("%s.md" % _sid)).write_text(_jl_spec_text(_sid, **_opts))
    _JL_CORPUS = JLTC.build(specs_dir=_jl_specs_dir, events=_JL_EVENTS, protected=())
    _JL_PLAN_ITEMS = {"PLAN-9400": ["WARP-9401", "WARP-9402", "WARP-9403", "WARP-9499"],
                      "PLAN-9401": ["WARP-9404", "WARP-9405"]}
    _JL_REPORT = JL.build(_JL_CORPUS, _JL_EVENTS, _JL_PLAN_ITEMS)
    # The same corpus and the same specs with a log that carries NO figure at all: the adoption
    # case, and the negative control standing beside every positive assertion below.
    _JL_BARE_EVENTS = [{k: v for k, v in e.items()
                        if k not in ("tokens", "human_minutes")} for e in _JL_EVENTS]
    _JL_BARE_CORPUS = JLTC.build(specs_dir=_jl_specs_dir, events=_JL_BARE_EVENTS, protected=())
    _JL_BARE_REPORT = JL.build(_JL_BARE_CORPUS, _JL_BARE_EVENTS, _JL_PLAN_ITEMS)

_JL_ROWS = {r["spec"]: r for r in _JL_REPORT["rows"]}
_JL_BARE_ROWS = {r["spec"]: r for r in _JL_BARE_REPORT["rows"]}

expect("WARP-1407 fixture: the seeded corpus holds exactly the six shipped fixture specs",
       sorted(_JL_ROWS) == _JL_IDS and sorted(_JL_BARE_ROWS) == _JL_IDS)

# ---------------------------------------------------------------------------------------
# AC1. THE PAIR IS ONE VALUE, DERIVED PER SPEC, AND ONE RENDERER SHOWS IT.
# ---------------------------------------------------------------------------------------
expect("WARP-1407 AC1: the pair carries both axes for a spec whose figures were recorded",
       (_JL_ROWS["WARP-9402"]["tokens"], _JL_ROWS["WARP-9402"]["tokens_known"],
        _JL_ROWS["WARP-9402"]["judgment_minutes"], _JL_ROWS["WARP-9402"]["judgment_known"])
       == (50, True, 60, True))
expect("WARP-1407 AC1: the judgment axis is split by the kind of judgment the minutes paid for",
       _JL_ROWS["WARP-9402"]["judgment_by_kind"]["review"] == 20
       and _JL_ROWS["WARP-9402"]["judgment_by_kind"]["approval"] == 40
       and _JL_ROWS["WARP-9402"]["split_known"] is True)
# NEGATIVE CONTROL for both rows above: a spec with no events at all yields the same fields with
# every figure zero and every flag false, so the assertions above measure the seeded figures rather
# than the mere presence of the keys.
expect("WARP-1407 AC1 NEGATIVE CONTROL: a spec with no events carries both axes as unrecorded",
       (_JL_ROWS["WARP-9405"]["tokens"], _JL_ROWS["WARP-9405"]["tokens_known"],
        _JL_ROWS["WARP-9405"]["judgment_minutes"], _JL_ROWS["WARP-9405"]["judgment_known"],
        _JL_ROWS["WARP-9405"]["split_known"], _JL_ROWS["WARP-9405"]["episodes"])
       == (0, False, 0, False, False, 0))

expect("WARP-1407 AC1: the pair line carries both axes, the split and the shape",
       all(s in JL.pair_line(_JL_ROWS["WARP-9402"])
           for s in ("WARP-9402", "toe 50 tok", "judgment 60 min", "[review 20, approval 40]",
                     JL.SHAPE_CHEAP_BUILD_EXPENSIVE_APPROVE)))
expect("WARP-1407 AC1 NEGATIVE CONTROL: the pair line of an unrecorded pair says so twice and "
       "shows no split block",
       JL.pair_line(_JL_ROWS["WARP-9405"]).count("not recorded") == 2
       and "[" not in JL.pair_line(_JL_ROWS["WARP-9405"]))
# The envelope permits a fractional figure, so the renderer must not truncate one into a smaller
# number that reads as measured. Positive: a fractional minute count keeps its decimals. Negative
# control: an integral one prints with no decimal point at all, so this is not just "always .2f".
expect("WARP-1407 AC1: a fractional figure renders without being truncated, and an integral one "
       "renders as an integer",
       "judgment 1.50 min" in JL.pair_line(dict(_JL_ROWS["WARP-9401"], judgment_minutes=1.5))
       and "judgment 10 min" in JL.pair_line(_JL_ROWS["WARP-9401"]))

_JL_TEXT = JL.render(_JL_REPORT)
expect("WARP-1407 AC1: the report surface renders every row THROUGH pair_line (one renderer)",
       all(JL.pair_line(r) in _JL_TEXT for r in _JL_REPORT["rows"]))
expect("WARP-1407 AC1 NEGATIVE CONTROL: a line for a spec the report does not hold is absent",
       JL.pair_line(dict(_JL_ROWS["WARP-9402"], spec="WARP-9499")) not in _JL_TEXT)

# The per-plan roll-up, the other place effort is shown, carries its DENOMINATOR so a plan line
# cannot read as complete when it is partial.
expect("WARP-1407 AC1: the per-plan roll-up sums the pair and names the declared item count",
       (_JL_REPORT["plans"]["PLAN-9400"]["specs"],
        _JL_REPORT["plans"]["PLAN-9400"]["work_items"],
        _JL_REPORT["plans"]["PLAN-9400"]["tokens"],
        _JL_REPORT["plans"]["PLAN-9400"]["judgment_minutes"],
        _JL_REPORT["plans"]["PLAN-9400"]["minutes_known"]) == (3, 4, 1150, 75, 3))
expect("WARP-1407 AC1 NEGATIVE CONTROL: a plan the item map does not declare reports its "
       "denominator as unknown rather than inventing one",
       _JL_REPORT["plans"][JL.NO_PLAN]["work_items"] is None
       and _JL_REPORT["plans"][JL.NO_PLAN]["specs"] == 1)

# plan_items_from_registry reads the declared items THROUGH the one plan registry (which parses with
# validate.parse_yamlish); it is the only front-matter reading this module does, and it stands down
# to an empty map rather than a fabricated denominator.
expect("WARP-1407 AC1: plan items come from the plan registry, and an empty registry yields "
       "no denominators at all",
       JL.plan_items_from_registry({"PLAN-9400": {"fm": {"work": [{"item": "W1",
                                                                  "spec": "WARP-9401"}]}}})
       == {"PLAN-9400": ["WARP-9401"]}
       and JL.plan_items_from_registry({}) == {} and JL.plan_items_from_registry(None) == {})
expect("WARP-1407 AC1 NEGATIVE CONTROL: a work item declaring no spec id contributes no "
       "denominator entry (a malformed item is not counted as one)",
       JL.plan_items_from_registry({"P": {"fm": {"work": [{"item": "W1"}, "junk"]}}}) == {"P": []})

# ---------------------------------------------------------------------------------------
# AC2. AN UNRECORDED AXIS IS "NOT RECORDED", NEVER A ZERO, AND THE GAP IS A NUMBER.
# ---------------------------------------------------------------------------------------
_JL_COV, _JL_BARE_COV = _JL_REPORT["coverage"], _JL_BARE_REPORT["coverage"]
expect("WARP-1407 AC2: coverage counts what is measured on the seeded log",
       (_JL_COV["records"], _JL_COV["minutes_known"], _JL_COV["tokens_known"],
        _JL_COV["pair_known"], _JL_COV["usable_as_second_axis"], _JL_COV["classifiable"])
       == (6, 4, 4, 4, True, True))
expect("WARP-1407 AC2 NEGATIVE CONTROL: with no figure anywhere the same six rows are produced "
       "and coverage reports zero known, not zero cost",
       (_JL_BARE_COV["records"], _JL_BARE_COV["minutes_known"], _JL_BARE_COV["tokens_known"],
        _JL_BARE_COV["pair_known"], _JL_BARE_COV["usable_as_second_axis"],
        _JL_BARE_COV["classifiable"]) == (6, 0, 0, 0, False, False))
expect("WARP-1407 AC2: the report SAYS the axis is unusable when nothing is recorded, in words, "
       "rather than printing zeros",
       "NOT USABLE AS A SECOND AXIS YET" in JL.render(_JL_BARE_REPORT)
       and "not recorded" in JL.render(_JL_BARE_REPORT))
expect("WARP-1407 AC2 NEGATIVE CONTROL: that banner is absent when minutes ARE recorded",
       "NOT USABLE AS A SECOND AXIS YET" not in _JL_TEXT)

# The four shapes, which is what a second axis buys: the first label is the class no single-axis
# unit could ever show.
expect("WARP-1407 AC2: cheap to build and expensive to approve is named as its own shape",
       _JL_ROWS["WARP-9402"]["shape"] == JL.SHAPE_CHEAP_BUILD_EXPENSIVE_APPROVE)
expect("WARP-1407 AC2: the other three shapes are named from the same reference",
       (_JL_ROWS["WARP-9401"]["shape"], _JL_ROWS["WARP-9403"]["shape"],
        _JL_ROWS["WARP-9404"]["shape"])
       == (JL.SHAPE_CHEAP_BOTH, JL.SHAPE_EXPENSIVE_BUILD_CHEAP_APPROVE, JL.SHAPE_EXPENSIVE_BOTH))
expect("WARP-1407 AC2: the reference is the repository's own medians over the both-axes rows, "
       "reported with its population",
       (_JL_REPORT["reference"]["population"], _JL_REPORT["reference"]["median_tokens"],
        _JL_REPORT["reference"]["median_judgment_minutes"], _JL_REPORT["reference"]["usable"])
       == (4, 550.0, 35.0, True))
# NEGATIVE CONTROL: the same rows minus one both-axes record leave the population below the floor,
# and then NOTHING is labelled - a median over three points is refused rather than published.
_JL_THIN, _JL_THIN_REF = JL.classify([r for r in _JL_REPORT["rows"] if r["spec"] != "WARP-9404"])
expect("WARP-1407 AC2 NEGATIVE CONTROL: below the population floor no row is labelled and the "
       "reason names the shortfall",
       _JL_THIN_REF["usable"] is False and _JL_THIN_REF["population"] == 3
       and all(r["shape"] == JL.SHAPE_UNKNOWN for r in _JL_THIN)
       and "at least %d" % JL.MIN_POPULATION in _JL_THIN_REF["reason"])
# The floor has ONE spelling: `classifiable` in the coverage block is read off the same reference the
# labels came from, so the two can never disagree about whether this corpus can be labelled at all.
expect("WARP-1407 AC2: coverage's classifiable flag agrees with the reference the labels came from, "
       "in both directions",
       _JL_COV["classifiable"] == _JL_REPORT["reference"]["usable"] is True
       and JL.coverage(_JL_THIN, None, _JL_THIN_REF)["classifiable"] is False
       and JL.coverage(_JL_THIN)["classifiable"] is False)
# TEETH ON THAT AGREEMENT, because agreement between two spellings that happen to match today is not
# evidence of one spelling. Handed a reference built on a DIFFERENT floor, coverage follows the
# reference; a second comparison against the module constant would answer False here.
expect("WARP-1407 AC2: classifiable is READ from the reference, not re-derived from the module's "
       "own floor",
       JL.coverage(_JL_THIN, None, JL.reference(_JL_THIN, min_population=2))["classifiable"] is True
       and len([r for r in _JL_THIN if r["tokens_known"] and r["judgment_known"]])
       < JL.MIN_POPULATION)
# A record sitting EXACTLY at the median is low, not expensive: the comparison is strictly above.
expect("WARP-1407 AC2: a record exactly at both medians is cheap on both, never expensive - the "
       "comparison is strictly above the median",
       JL.classify([dict(_JL_ROWS["WARP-9402"], spec="WARP-9498", tokens=550,
                         judgment_minutes=35)] + _JL_REPORT["rows"])[0][0]["shape"]
       == JL.SHAPE_CHEAP_BOTH)

# ---------------------------------------------------------------------------------------
# AC3. EPISODES ARE COUNTED AND ARE NEVER CONVERTED INTO MINUTES. This is the row the whole item
# turns on: WARP-9406 had a human in the loop three times and not one recorded minute, and the
# temptation is to score it. It is reported as unknown, and the reason names the missing axis.
# ---------------------------------------------------------------------------------------
expect("WARP-1407 AC3: a spec with judgment episodes and no recorded minutes keeps a zero "
       "judgment total with judgment_known FALSE",
       (_JL_ROWS["WARP-9406"]["episodes"], _JL_ROWS["WARP-9406"]["judgment_minutes"],
        _JL_ROWS["WARP-9406"]["judgment_known"]) == (3, 0, False))
expect("WARP-1407 AC3: and it is NOT classified cheap - the shape is unknown and the reason names "
       "the axis that is missing",
       _JL_ROWS["WARP-9406"]["shape"] == JL.SHAPE_UNKNOWN
       and "judgment minutes" in _JL_ROWS["WARP-9406"]["shape_reason"]
       and "not recorded" in _JL_ROWS["WARP-9406"]["shape_reason"])
expect("WARP-1407 AC3 NEGATIVE CONTROL: a spec with the SAME episode count and recorded minutes "
       "IS classified, so the unknown above is the missing axis and not the code refusing "
       "everything",
       _JL_ROWS["WARP-9403"]["episodes"] == 3
       and _JL_ROWS["WARP-9403"]["judgment_known"] is True
       and _JL_ROWS["WARP-9403"]["shape"] != JL.SHAPE_UNKNOWN)
expect("WARP-1407 AC3: episodes count review requests, verdicts and approvals, and NOT the "
       "bookkeeping ship record",
       (_JL_ROWS["WARP-9403"]["episodes_by_kind"]["review"],
        _JL_ROWS["WARP-9404"]["episodes_by_kind"]["approval"],
        _JL_ROWS["WARP-9401"]["episodes"]) == (3, 1, 0))
# TWO ENUMERATIONS OF ONE SET, PROVEN EQUAL rather than assumed: this module's own per-spec figure
# readers against the corpus's independent ones, over the same events. Anti-vacuity is explicit -
# at least one of the totals compared is non-zero.
_JL_TOTALS_MATCH = all(
    JL.tokens_for(_JL_EVENTS, s)["tokens"] == JLTC.spend_for(_JL_EVENTS, s)["tokens"]
    and JL.minutes_for(_JL_EVENTS, s)["minutes"] == JLTC.spend_for(_JL_EVENTS, s)["human_minutes"]
    for s in _JL_IDS)
expect("WARP-1407 AC3: this module's axis totals equal the corpus's own totals for every seeded "
       "spec, and the compared figures are not all zero",
       _JL_TOTALS_MATCH and JLTC.spend_for(_JL_EVENTS, "WARP-9404")["tokens"] == 2000
       and JL.minutes_for(_JL_EVENTS, "WARP-9402")["minutes"] == 60)
expect("WARP-1407 AC3 NEGATIVE CONTROL: the equality is a measurement, not a tautology - the two "
       "readers DISAGREE by construction on a figure the corpus skips and this module refuses",
       JLTC.spend_for([_jl_ev("spec.shipped", "WARP-9407", human_minutes="12")],
                      "WARP-9407")["human_minutes"] == 0)
# The independent count of what was seeded, so the episode figure is compared against the fixture
# rather than against itself.
_JL_SEEDED_EPISODES = sum(
    1 for e in _JL_EVENTS
    if e["type"] in ("verdict.recorded", "review.requested", "approval.recorded"))
expect("WARP-1407 AC3: the episode total over the corpus equals the number of judgment events "
       "seeded, counted independently here",
       sum(r["episodes"] for r in _JL_REPORT["rows"]) == _JL_SEEDED_EPISODES == 9)

# ---------------------------------------------------------------------------------------
# AC4. A MALFORMED FIGURE IS REFUSED BY NAME; AN UNATTRIBUTABLE ONE IS COUNTED, NOT DROPPED.
# ---------------------------------------------------------------------------------------
def _jl_refusal(fn, *args):
    """(raised, message). The message is returned because an assertion that something raised,
    without checking WHAT, passes on an unrelated TypeError."""
    try:
        fn(*args)
    except JL.JudgmentLoadError as e:
        return True, str(e)
    except BaseException as e:  # noqa: BLE001 - a wrong exception type is a finding, not a pass
        return False, "%s: %s" % (type(e).__name__, e)
    return False, ""


_JL_BAD = {
    "a string": [_jl_ev("spec.shipped", "WARP-9410", human_minutes="12")],
    "a boolean": [_jl_ev("spec.shipped", "WARP-9410", human_minutes=True)],
    "a negative": [_jl_ev("spec.shipped", "WARP-9410", human_minutes=-5)],
}
for _label, _evs in sorted(_JL_BAD.items()):
    _raised, _msg = _jl_refusal(JL.minutes_for, _evs, "WARP-9410")
    expect("WARP-1407 AC4: %s human_minutes is refused BY NAME (the field and the value in the "
           "message)" % _label,
           _raised and "human_minutes" in _msg and "spec.shipped" in _msg)
_JL_TOK_RAISED, _JL_TOK_MSG = _jl_refusal(
    JL.tokens_for, [_jl_ev("spec.shipped", "WARP-9410", tokens=[1])], "WARP-9410")
expect("WARP-1407 AC4: a malformed tokens figure is refused BY NAME too",
       _JL_TOK_RAISED and "tokens" in _JL_TOK_MSG)
_JL_MAP_RAISED, _JL_MAP_MSG = _jl_refusal(JL.minutes_for, ["not an event"], "WARP-9410")
expect("WARP-1407 AC4: an event that is not a mapping is refused, naming that",
       _JL_MAP_RAISED and "not a mapping" in _JL_MAP_MSG)
# NEGATIVE CONTROL: the well-formed seeded log raises nothing, so the refusals above are the
# malformed values and not a reader that refuses whatever it is handed.
expect("WARP-1407 AC4 NEGATIVE CONTROL: the well-formed seeded log is read without a refusal",
       _jl_refusal(JL.minutes_for, _JL_EVENTS, "WARP-9402") == (False, "")
       and _jl_refusal(JL.tokens_for, _JL_EVENTS, "WARP-9402") == (False, ""))

# The gate-shaped spelling of the same judge: every problem listed through a failure reporter,
# rather than the first one raised. Driven with a recorder here so the messages can be asserted,
# and once with validate.fail (the one reporter) so the real signature is exercised.
_JL_MSGS = []
_JL_ERRS = JL.check_log([e for evs in _JL_BAD.values() for e in evs] + _JL_EVENTS,
                        "seeded.jsonl", lambda where, msg: (_JL_MSGS.append(msg), 1)[1])
expect("WARP-1407 AC4: check_log reports EVERY malformed figure through the caller's reporter",
       _JL_ERRS == 3 and len(_JL_MSGS) == 3 and all("human_minutes" in m for m in _JL_MSGS))
expect("WARP-1407 AC4 NEGATIVE CONTROL: check_log over the well-formed log reports nothing",
       JL.check_log(_JL_EVENTS, "seeded.jsonl", V.fail) == 0)
expect("WARP-1407 AC4: the raise and the report come from ONE judge, so they name the same value",
       JL._figure_problem("human_minutes",
                          _jl_ev("spec.shipped", "WARP-9410", human_minutes="12"), "12")
       == _jl_refusal(JL.minutes_for, _JL_BAD["a string"], "WARP-9410")[1]
       and JL._figure_problem("human_minutes", _jl_ev("spec.shipped", "WARP-9410", human_minutes=1),
                              1) is None)

_JL_ORPHAN = {"schema": "veldo.event/v1", "type": "spec.shipped", "at": "2026-08-10T00:00:00Z",
              "human_minutes": 7, "tokens": 11}
expect("WARP-1407 AC4: minutes on an event naming no spec are COUNTED as unattributable, with "
       "their figures, rather than dropped",
       JL.unattributed([_JL_ORPHAN]) == {"events": 1, "minutes": 7, "tokens": 11})
expect("WARP-1407 AC4 NEGATIVE CONTROL: the same event WITH a spec is not unattributable and its "
       "minutes land on that spec's pair instead",
       JL.unattributed([dict(_JL_ORPHAN, spec_id="WARP-9411")]) == {"events": 0, "minutes": 0,
                                                                   "tokens": 0}
       and JL.minutes_for([dict(_JL_ORPHAN, spec_id="WARP-9411")], "WARP-9411")["minutes"] == 7)
expect("WARP-1407 AC4: the seeded log has no unattributable figure, and the report says so as a "
       "number",
       _JL_COV["unattributed"] == {"events": 0, "minutes": 0, "tokens": 0}
       and "unattributable: 0 event(s)" in _JL_TEXT)

# ---------------------------------------------------------------------------------------
# AC5. THE ONLY RECORDER WRITES A BULK FIGURE AT SHIP, AND THE SPLIT IS REPORTED UNKNOWN RATHER
# THAN INFERRED. Bound to spend.py's own declaration, so the kind map cannot drift from the
# recorder it describes.
# ---------------------------------------------------------------------------------------
expect("WARP-1407 AC5: minutes recorded the way spend.py records them count toward the judgment "
       "total and leave the split UNKNOWN",
       (_JL_ROWS["WARP-9401"]["judgment_minutes"], _JL_ROWS["WARP-9401"]["judgment_known"],
        _JL_ROWS["WARP-9401"]["split_known"],
        _JL_ROWS["WARP-9401"]["judgment_by_kind"]["ship_bulk"],
        _JL_ROWS["WARP-9401"]["judgment_by_kind"]["review"]) == (10, True, False, 10, 0))
expect("WARP-1407 AC5: and its rendered line says the split is not recorded rather than showing "
       "a review or approval figure",
       "[split not recorded]" in JL.pair_line(_JL_ROWS["WARP-9401"])
       and "review" not in JL.pair_line(_JL_ROWS["WARP-9401"]).split("judgment")[1])
expect("WARP-1407 AC5 NEGATIVE CONTROL: minutes on a verdict or an approval DO set the split, so "
       "the unknown above is the bulk record and not a flag that is never set",
       _JL_ROWS["WARP-9402"]["split_known"] is True)
expect("WARP-1407 AC5: the kind map is bound to the recorder's own event type (a drift guard: if "
       "spend.py changes what it writes, this fails rather than silently mis-splitting)",
       JLSP.SCHEMA_EVENT_TYPE == "spec.shipped"
       and JL.KIND_BY_EVENT[JLSP.SCHEMA_EVENT_TYPE] == "ship_bulk"
       and JL.KIND_BY_EVENT["verdict.recorded"] == "review"
       and JL.KIND_BY_EVENT["approval.recorded"] == "approval")
expect("WARP-1407 AC5 NEGATIVE CONTROL: an event type the map does not know carries its minutes "
       "into 'other' - counted in the total, never promoted into a kind it did not declare",
       JL.minutes_for([_jl_ev("merge.completed", "WARP-9412", human_minutes=9)],
                      "WARP-9412") == {"minutes": 9,
                                       "by_kind": {"review": 0, "approval": 0, "ship_bulk": 0,
                                                   "other": 9},
                                       "events_with_minutes": 1, "minutes_recorded": True,
                                       "split_known": False})
expect("WARP-1407 AC5: every field this module reads off an event is a field the envelope already "
       "carries (no new telemetry)",
       all(f in JLEV.make_event("spec.shipped", spec="WARP-9413", tokens=1, human_minutes=1)
           for f in (JL.TOKENS_FIELD, JL.MINUTES_FIELD, "spec_id", "type")))

# ---------------------------------------------------------------------------------------
# AC5 (second half). ADOPTION SAFE: the derivation WRITES NOTHING. Asserted behaviourally over a
# tree digest rather than by grepping the source for the absence of a write, because an absent call
# is a fact about today's text while an unchanged tree is a fact about the run.
# ---------------------------------------------------------------------------------------
def _jl_digest(root):
    h = _jl_hashlib.sha256()
    for p in sorted(Path(root).rglob("*")):
        h.update(str(p.relative_to(root)).encode())
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()


with tempfile.TemporaryDirectory() as _jl_dir2:
    _jl_sd = Path(_jl_dir2) / "specs"
    _jl_sd.mkdir()
    for _sid, _opts in sorted(_JL_SPECS.items()):
        (_jl_sd / ("%s.md" % _sid)).write_text(_jl_spec_text(_sid, **_opts))
    (Path(_jl_dir2) / "events.jsonl").write_text(
        "\n".join(json.dumps(e, sort_keys=True) for e in _JL_EVENTS) + "\n")
    _jl_before = _jl_digest(_jl_dir2)
    _jl_c = JLTC.build(specs_dir=_jl_sd, events=_JL_EVENTS, protected=())
    _jl_r = JL.build(_jl_c, _JL_EVENTS, _JL_PLAN_ITEMS)
    JL.render(_jl_r)
    _jl_after = _jl_digest(_jl_dir2)
    expect("WARP-1407 AC5: building and rendering the pair leaves the tree it read "
           "byte-identical (it writes nothing)", _jl_before == _jl_after)
    # POSITIVE CONTROL on the instrument itself: the digest DOES move when a byte changes, so the
    # equality above is a measurement rather than a digest that cannot notice anything.
    (Path(_jl_dir2) / "events.jsonl").write_text("changed\n")
    expect("WARP-1407 AC5 CONTROL: the tree digest notices a single changed file, so the "
           "unchanged result above is evidence", _jl_digest(_jl_dir2) != _jl_after)

# ---------------------------------------------------------------------------------------
# LIVE, over this repository's real corpus and real log. Two properties that must hold whatever the
# data says: the real log carries no malformed figure, and every row whose axis was never recorded
# is unknown rather than labelled. The MEASURED numbers behind the spec's prose (0 percent minutes
# coverage over 174 shipped specs, 81 percent episode coverage) are recorded in the spec, not
# pinned here, because pinning a live count reddens the gate the first time someone records a
# minute - which is the outcome this item wants.
# ---------------------------------------------------------------------------------------
_JL_REAL_EVENTS = JLEV.read_log()
expect("WARP-1407 LIVE: the real event log carries no malformed figure",
       JL.check_log(_JL_REAL_EVENTS, ".veldo/events.jsonl", V.fail) == 0)
_JL_REAL_ROWS = JL.build(
    JLTC.build(events=_JL_REAL_EVENTS, protected=()), _JL_REAL_EVENTS)["rows"]
expect("WARP-1407 LIVE: the real corpus produces a pair row per shipped spec, and every row with "
       "an unrecorded axis is unknown rather than labelled",
       len(_JL_REAL_ROWS) > 0
       and all(r["shape"] == JL.SHAPE_UNKNOWN for r in _JL_REAL_ROWS
               if not (r["tokens_known"] and r["judgment_known"])))
expect("WARP-1407 LIVE: and that is not vacuous - the real corpus does carry rows whose judgment "
       "axis was never recorded (the gap this item reports as a number)",
       sum(1 for r in _JL_REAL_ROWS if not r["judgment_known"]) > 0)
