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

TEETH, MEASURED RATHER THAN CLAIMED. Sixteen deliberate breaks were driven and watched go red on
`--suite 15_warp_1407_judgment_load`, which was 61 passing assertions and is 84 after the repairs an
independent L2 review asked for (recorded at the end of this list as breaks 17 to 22, each driven the
same way, plus breaks 23 and 24 for the two minor defects the same review left open). Every count below is the count at the time that break was driven:
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
Ten more were driven after a review measured that four properties the ACs name were asserted
NOWHERE, so the module could be inverted with this suite green. Each is one edit to
.veldo/judgment_load.py, applied in a scratch clone, DIFFED to prove the edit landed, and run:
  7. Appending one JSON line to `ROOT/".veldo/judgment_load_state.jsonl"` inside `build()` - a real
     state writer, which the previous write-nothing check could not see because it digested the
     tmp INPUT tree that build() holds no path to: 1 FAILED, the AC5 ROOT-tree row. That row now
     points JL.ROOT at a seeded hermetic repository, which is the tree every path in the module is
     built from.
  8. `"minutes_coverage": 1.0` hardcoded, which makes the report print "judgment minutes known on 0
     (100.0%)" over an axis with nothing on it: 3 FAILED (both coverage tuples and the rendered
     coverage line).
  9. `"episodes_known": 0` hardcoded, the figure AC3's headline coverage rests on: the same 3 FAILED.
 10. The plan line's `"(not declared)"` denominator fallback replaced with the plan's own spec count,
     so a partial roll-up reads as complete: 1 FAILED, the rendered plan line.
 11. The plan line's token column fed the minutes figure and its known-count fed the spec count:
     1 FAILED, the same rendered plan line, which is why that line is pinned whole rather than by
     the denominator alone.
 12. Deleting the "NOT CLASSIFIABLE YET" banner: 1 FAILED, the bare-report banner row.
 13. `approval_required` inverted to `== "not_required"`: 1 FAILED, the AC1 approval-surface row.
 14. `protected_touch` replaced with the constant False: 1 FAILED, the AC1 protected-touch row.
 15. The `reference:` line of the report blanked: 2 FAILED (the bare-report banner row and its
     positive control), where before it was measured green.
 16. `"split_known": 0` hardcoded in the coverage block: 2 FAILED (the seeded coverage tuple and the
     rendered coverage line).
SIX MORE AFTER AN INDEPENDENT L2 REVIEW FOUND ONE BLOCKER AND FOUR MAJORS HERE, all six driven in a
scratch copy, diffed to prove the edit landed, run, and reverted. Every count below was re-measured
against the final file, whose baseline is 84 passed, 0 failed:
 17. Rendering the plan roll-up's two axis columns with `_num` again, which is what the module did and
     what the AC1 row USED TO PIN: 3 FAILED (the AC1 rendered plan line, the AC2 row requiring the
     words on the plan line of a log carrying no figure, and the AC2 row requiring a plan whose
     figures were recorded AS ZERO to print the zero). This is the blocker, and its shape is that the
     check certified the defect - the honest rendering was what turned the gate red.
 18. `_figure_problem` dropped back to the sign test alone (`not math.isfinite` disabled), so NaN and
     infinity pass the ONE judge again: 5 FAILED - the NaN row, the infinity row, the check_log count,
     the end-to-end CLI row (where `check` reported a clean log and `report` printed "judgment nan
     min" at 100.0 percent coverage), and the LIVE row where the judge stops agreeing with an
     independent reading of what a well-formed figure is. The negative-infinity row stays GREEN and
     that is correct rather than a gap: -inf is still caught by the sign test below, so this mutation
     reaches exactly the two values the sign test cannot see.
 19. `split_known` back to the truthiness of the SUM, so a split recorded AS ZERO reads as a split
     nobody recorded: 3 FAILED (the recorded-zero flags row, its rendered line, and the row that
     classifies a recorded zero instead of leaving it unknown).
 20. `minutes_recorded` (a) and `tokens_recorded` (b) derived from the TOTAL instead of the count of
     events carrying the field: 4 FAILED each, where before the recorded-zero fixture existed both
     edits left the suite fully green - which is what made the honesty flag both criteria hang on
     silently swappable for a semantically different definition.
 21. The correlation half of `_mine` deleted: 1 FAILED, the correlation-attributed equality row, where
     before the correlation fixture existed this left the suite green while the corpus reader it
     promises to equal joins on that field. Its negative control stays green by design: an event whose
     correlation id names a different spec belongs to neither reader under either spelling.
 22. The organ guard removed from `_repo_report` (a bare `_load` again): 2 FAILED, the corpus-organ
     and log-organ legs, each naming the organ whose absence it stands down for - in a tree without
     toe_corpus.py the report exits 1 with a raw FileNotFoundError instead of naming it. The plan
     registry leg stays green because its own load is guarded separately.
 23. The spec-id refusal deleted from `pair`, so a record naming no spec becomes a phantom row that
     collects the figures of every unattributable event: 1 FAILED, the refusal row. Its negative
     control stays green by design - that record carries a spec id, so the deleted refusal never
     reaches it - which is the same shape as break 21.
 24. `unread_figures` made to return 0 unconditionally, so the page stops saying how many figures the
     derivation could not read: 2 FAILED (the seeded count row and the end-to-end row where `check`
     exits 1 naming a figure `report` never read).
Each was reverted; what is here is the file that goes green over the unmodified module. AND ONE
ADDITIVE CONTROL: the reviewer's own added assertion over a figure recorded as zero, which FAILED
against the module as shipped, was added on top of this file and run - 80 passed, 0 failed.
"""
import hashlib as _jl_hashlib
import math as _jl_math
import shutil as _jl_shutil
import subprocess as _jl_subprocess
import sys as _jl_sys

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

# THE APPROVAL SURFACE, which AC1 requires the pair to carry and which is the mechanical reason a
# change costs a human anything at all. Asserted in BOTH directions and over the WHOLE seeded set,
# so neither an inverted comparison in pair() nor a constant in its place can pass: WARP-9402 is the
# one fixture declaring `human_approval: required` and every other fixture declares not_required.
expect("WARP-1407 AC1: the pair carries the approval surface the spec declared, true for the one "
       "fixture that declared it and false for every fixture that did not",
       _JL_ROWS["WARP-9402"]["approval_required"] is True
       and _JL_ROWS["WARP-9401"]["approval_required"] is False
       and [s for s in _JL_IDS if _JL_ROWS[s]["approval_required"]] == ["WARP-9402"])
# The other surface field the pair carries. The seeded corpus is built with NO protected patterns,
# so the true half needs its own fixture pair through the SAME corpus reader: one footprint inside
# the protected pattern and one outside it.
with tempfile.TemporaryDirectory() as _jl_dir_prot:
    _jl_prot_dir = Path(_jl_dir_prot) / "specs"
    _jl_prot_dir.mkdir()
    (_jl_prot_dir / "WARP-9420.md").write_text(
        _jl_spec_text("WARP-9420", footprint=(".veldo/policy.yaml",)))
    (_jl_prot_dir / "WARP-9421.md").write_text(
        _jl_spec_text("WARP-9421", footprint=("docs/notes.md",)))
    _JL_PROT_ROWS = {r["spec"]: r for r in JL.build(
        JLTC.build(specs_dir=_jl_prot_dir, events=[], protected=(".veldo/*",)), [])["rows"]}
expect("WARP-1407 AC1: the pair carries protected_touch from the corpus - true for a footprint "
       "inside the protected pattern, false for one outside it, and false everywhere when the "
       "corpus was built with no protected patterns at all",
       _JL_PROT_ROWS["WARP-9420"]["protected_touch"] is True
       and _JL_PROT_ROWS["WARP-9421"]["protected_touch"] is False
       and all(_JL_ROWS[s]["protected_touch"] is False for s in _JL_IDS))

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
# THE RENDERED plan line, not only the dict behind it. AC1's denominator promise is a promise about
# what a READER sees, and a fallback printing the plan's own spec count where the declared count
# goes would make a partial roll-up read as complete with every dict assertion above still green.
# Pinned as the WHOLE line, so a swapped column (minutes rendered in the tokens place, the spec
# count rendered as the known-count) reds here too rather than only the denominator.
#
# AND THE PLAN LINE OBEYS `_axis`, WHICH IS THE PROPERTY THIS ROW USED TO CERTIFY THE OPPOSITE OF.
# The line pinned here before the review read "toe 0 tok (0 known)  judgment 0 min (0 known)" - a
# figure standing where AC2 promises the words go, on the surface built for comparing plans, pinned
# as the expected output so the honest rendering was what turned the gate red. Both flavours are
# pinned now: a plan with figures prints them, and a plan with nothing recorded on an axis prints
# "not recorded" there while still carrying its declared denominator and its episode count. Rendering
# either plan column with `_num` again reds this row.
expect("WARP-1407 AC1: the rendered plan line carries the declared denominator and every column in "
       "its own place, and a plan the item map does not declare renders '(not declared)' rather "
       "than a number of its own",
       "  PLAN-9400        3 of 4 work item spec(s) in the corpus  toe 1150 tok         (3 known)  "
       "judgment 75 min           (3 known)  episodes 5" in _JL_TEXT
       and "  (no plan)        1 of (not declared) work item spec(s) in the corpus  "
       "toe not recorded     (0 known)  judgment not recorded     (0 known)  episodes 3" in _JL_TEXT)

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
# EVERY FIGURE THE COVERAGE BLOCK PUBLISHES, counts AND percentages, pinned as ONE tuple against
# the same fixture. The percentages are the half a reader acts on and they were the half nothing
# asserted: a hardcoded 1.0 would print "judgment minutes known on 0 (100.0%)", a confident
# full-coverage claim over an empty axis. Pinned in both directions, and the fixture is designed so
# they are not all the same number: with the figures stripped, minutes/tokens/pair coverage go to
# 0.0 while episodes coverage stays 0.6667, so one percentage substituted for another also reds.
expect("WARP-1407 AC2: coverage counts AND percentages over the seeded log, every published figure",
       (_JL_COV["records"], _JL_COV["minutes_known"], _JL_COV["minutes_coverage"],
        _JL_COV["tokens_known"], _JL_COV["tokens_coverage"],
        _JL_COV["pair_known"], _JL_COV["pair_coverage"],
        _JL_COV["split_known"], _JL_COV["episodes_known"], _JL_COV["episodes_coverage"],
        _JL_COV["usable_as_second_axis"], _JL_COV["classifiable"])
       == (6, 4, 0.6667, 4, 0.6667, 4, 0.6667, 1, 4, 0.6667, True, True))
expect("WARP-1407 AC2 NEGATIVE CONTROL: with no figure anywhere the same six rows are produced "
       "and coverage reports zero known and zero percent, not zero cost - while the episode "
       "coverage, which IS recorded, stays where it was",
       (_JL_BARE_COV["records"], _JL_BARE_COV["minutes_known"], _JL_BARE_COV["minutes_coverage"],
        _JL_BARE_COV["tokens_known"], _JL_BARE_COV["tokens_coverage"],
        _JL_BARE_COV["pair_known"], _JL_BARE_COV["pair_coverage"],
        _JL_BARE_COV["split_known"], _JL_BARE_COV["episodes_known"],
        _JL_BARE_COV["episodes_coverage"], _JL_BARE_COV["usable_as_second_axis"],
        _JL_BARE_COV["classifiable"]) == (6, 0, 0.0, 0, 0.0, 0, 0.0, 0, 4, 0.6667, False, False))
# And the percentages AS RENDERED, because the coverage line is where a reader meets them. The whole
# line is pinned in both reports, so a percentage that is right in the dict and wrong on the way to
# the page reds here.
_JL_BARE_TEXT = JL.render(_JL_BARE_REPORT)
expect("WARP-1407 AC2: the rendered coverage line carries every count with its own percentage, and "
       "on the log carrying no figure it reads 0.0 percent rather than a confident full coverage",
       "coverage: 6 record(s); judgment minutes known on 4 (66.7%), tokens on 4 (66.7%), both on 4 "
       "(66.7%); judgment split known on 1; episodes on 4" in _JL_TEXT
       and "coverage: 6 record(s); judgment minutes known on 0 (0.0%), tokens on 0 (0.0%), both on "
       "0 (0.0%); judgment split known on 0; episodes on 4" in _JL_BARE_TEXT)
expect("WARP-1407 AC2: the report SAYS the axis is unusable when nothing is recorded, in words, "
       "rather than printing zeros, and says the same about the labels it therefore withholds",
       "NOT USABLE AS A SECOND AXIS YET" in _JL_BARE_TEXT
       and "not recorded" in _JL_BARE_TEXT
       and "NOT CLASSIFIABLE YET" in _JL_BARE_TEXT
       and "reference: 0 record(s) carry both axes" in _JL_BARE_TEXT
       and _JL_BARE_REPORT["reference"]["reason"] in _JL_BARE_TEXT)
expect("WARP-1407 AC2 NEGATIVE CONTROL: both banners are absent when minutes ARE recorded and the "
       "population carries the labels, so neither is a banner that always prints",
       "NOT USABLE AS A SECOND AXIS YET" not in _JL_TEXT
       and "NOT CLASSIFIABLE YET" not in _JL_TEXT
       and "reference: medians over the 4 record(s) carrying both axes" in _JL_TEXT)

# THE PLAN LINE OBEYS THE SAME RULE AS THE ROW, which is the clause AC2 was refuted on. The plan
# roll-up is a SECOND rendering of the same pair, and it used to format its two axes with `_num`, so
# a plan whose specs recorded nothing printed "toe 0 tok (0 known)  judgment 0 min (0 known)": a
# figure standing exactly where the words go, on the surface built for comparing plans. Asserted as
# the whole rendered line AND as a property over the whole page - a report in which NO figure was
# recorded may not contain a zero wearing a unit anywhere, which is a defect by construction here
# rather than a count of anything, so no legitimate growth can red it.
expect("WARP-1407 AC2: on a log carrying no figure the PLAN line prints the words in both axis "
       "columns while keeping its declared denominator and its episode count, and no zero wearing a "
       "unit appears anywhere on that page",
       "  PLAN-9400        3 of 4 work item spec(s) in the corpus  toe not recorded     (0 known)  "
       "judgment not recorded     (0 known)  episodes 5" in _JL_BARE_TEXT
       and "0 tok " not in _JL_BARE_TEXT and "0 min " not in _JL_BARE_TEXT
       and _JL_BARE_TEXT.count("not recorded") == 2 * len(_JL_BARE_ROWS) + 2 * len(
           _JL_BARE_REPORT["plans"]))
# THE BANNER SAYS WHAT IT COUNTED, and what it counted is the records in this report. It used to say
# "no human minutes are recorded anywhere in this log ... nobody has called it", which is a claim
# about the LOG derived from a count over shipped-corpus ROWS: false the first time anybody records a
# minute against a spec that has not shipped, and self-contradicting on the same page whenever the
# unattributable line above it reports minutes of its own. Driven both ways below.
expect("WARP-1407 AC2: the unusable banner is scoped to the records it was counted over, and points "
       "at the two places its count cannot see rather than claiming they are empty",
       "no human minutes are recorded on any of the 6 record(s) in this report" in _JL_BARE_TEXT
       and "NOT about the whole log" in _JL_BARE_TEXT
       and "--all" in _JL_BARE_TEXT
       and "anywhere in this log" not in _JL_BARE_TEXT
       and "nobody has called it" not in _JL_BARE_TEXT)
# CASE A of the two states that made the old sentence false, built rather than reasoned about: 45
# minutes on an event naming no spec. The unattributable line reports them, so a page claiming none
# exist in the log would contradict its own line two rows up.
_JL_ORPHAN_MIN = {"schema": "veldo.event/v1", "type": "spec.shipped", "at": "2026-08-10T00:00:00Z",
                  "human_minutes": 45, "tokens": 900}
_JL_ORPHAN_TEXT = JL.render(JL.build(_JL_BARE_CORPUS, _JL_BARE_EVENTS + [_JL_ORPHAN_MIN],
                                     _JL_PLAN_ITEMS))
expect("WARP-1407 AC2: with minutes recorded on an event that names no spec, the report reports "
       "them as unattributable AND its unusable banner still says only what it counted, so one page "
       "does not contradict itself",
       "unattributable: 1 event(s) carrying 45 minute(s) and 900 token(s)" in _JL_ORPHAN_TEXT
       and "no human minutes are recorded on any of the 6 record(s) in this report"
       in _JL_ORPHAN_TEXT
       and "anywhere in this log" not in _JL_ORPHAN_TEXT
       and "nobody has called it" not in _JL_ORPHAN_TEXT)

# A FIGURE RECORDED AS ZERO, the other half of the distinction AC2 is built on and the half no
# fixture carried. Every seeded figure above is non-zero, which made `carrying > 0` (the count of
# events that carried the field) and `total > 0` (the truthiness of the sum) one predicate over this
# suite's data: both honesty flags could be silently redefined as the sum with the gate fully green,
# and the shipped `split_known` answered the recorded-zero case wrongly - the module's own thesis
# inverted inside its own second flag. Kept as its own small population rather than added to the
# seeded six, so every figure pinned above stays the figure this suite drives.
_JL_ZERO_EVENTS = [_jl_ev("verdict.recorded", "WARP-9407", human_minutes=0, tokens=0)]
_JL_SILENT_EVENTS = [_jl_ev("verdict.recorded", "WARP-9407")]
_JL_ZERO_MIN, _JL_ZERO_TOK = (JL.minutes_for(_JL_ZERO_EVENTS, "WARP-9407"),
                              JL.tokens_for(_JL_ZERO_EVENTS, "WARP-9407"))
_JL_SILENT_MIN, _JL_SILENT_TOK = (JL.minutes_for(_JL_SILENT_EVENTS, "WARP-9407"),
                                  JL.tokens_for(_JL_SILENT_EVENTS, "WARP-9407"))
expect("WARP-1407 AC2: a figure RECORDED AS ZERO is RECORDED - both axes carry the zero with their "
       "flags true and the split KNOWN, because the flags count the events that carried the field "
       "and never read the truthiness of the sum",
       (_JL_ZERO_MIN["minutes"], _JL_ZERO_MIN["minutes_recorded"], _JL_ZERO_MIN["split_known"],
        _JL_ZERO_MIN["events_with_minutes"], _JL_ZERO_TOK["tokens"],
        _JL_ZERO_TOK["tokens_recorded"]) == (0, True, True, 1, 0, True))
expect("WARP-1407 AC2 NEGATIVE CONTROL: the SAME event carrying no figure at all reports the same "
       "zero with every flag FALSE, so the row above measures the recorded zero rather than a flag "
       "that is always true",
       (_JL_SILENT_MIN["minutes"], _JL_SILENT_MIN["minutes_recorded"],
        _JL_SILENT_MIN["split_known"], _JL_SILENT_MIN["events_with_minutes"],
        _JL_SILENT_TOK["tokens"], _JL_SILENT_TOK["tokens_recorded"])
       == (0, False, False, 0, 0, False))
_JL_ZERO_ROW = JL.pair({"spec": "WARP-9407", "features": {}}, _JL_ZERO_EVENTS)
expect("WARP-1407 AC2: the rendered line for a recorded zero shows the FIGURE and the split it was "
       "recorded on, never the words, which belong to an axis nobody recorded",
       "toe 0 tok" in JL.pair_line(_JL_ZERO_ROW)
       and "judgment 0 min" in JL.pair_line(_JL_ZERO_ROW)
       and "[review 0, approval 0]" in JL.pair_line(_JL_ZERO_ROW)
       and "not recorded" not in JL.pair_line(_JL_ZERO_ROW))
# THE TWO ZEROS ON ONE PAGE, which is the whole distinction: the recorded zero is LABELLED against
# the reference (it is genuinely cheap on both), while the spec whose minutes nobody recorded stays
# unknown with the missing axis named.
_JL_ZERO_CLS = {r["spec"]: r for r in JL.classify([_JL_ZERO_ROW] + _JL_REPORT["rows"])[0]}
expect("WARP-1407 AC2: a recorded zero IS classified against the reference while an unrecorded axis "
       "is not, so the two zeros are told apart in one classification pass",
       _JL_ZERO_CLS["WARP-9407"]["shape"] == JL.SHAPE_CHEAP_BOTH
       and _JL_ZERO_CLS["WARP-9406"]["shape"] == JL.SHAPE_UNKNOWN
       and "not recorded" in _JL_ZERO_CLS["WARP-9406"]["shape_reason"])
# AND THE PLAN LINE TELLS THE SAME TWO ZEROS APART, which is the half the two repairs meet in: sending
# the plan columns through `_axis` must not turn a plan whose figures were recorded AS ZERO into a plan
# that recorded nothing. The words are for a plan with no known figure on the axis; a plan whose one
# spec recorded a zero prints the zero.
_JL_ZERO_TEXT = JL.render(JL.build([{"spec": "WARP-9407", "features": {"plan": "PLAN-9402"}}],
                                   _JL_ZERO_EVENTS, {"PLAN-9402": ["WARP-9407"]}))
expect("WARP-1407 AC2: a plan whose figures were RECORDED AS ZERO prints the zero on its plan line, "
       "not the words - the words are reserved for an axis with no known figure on it",
       "  PLAN-9402        1 of 1 work item spec(s) in the corpus  toe 0 tok            (1 known)  "
       "judgment 0 min            (1 known)  episodes 1" in _JL_ZERO_TEXT
       and "not recorded" not in _JL_ZERO_TEXT)

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
       JLTC.spend_for([_jl_ev("spec.shipped", "WARP-9408", human_minutes="12")],
                      "WARP-9408")["human_minutes"] == 0)
# BOTH HALVES OF THE ONE SELECTOR PARTICIPATE IN THAT EQUALITY. `_mine` attributes an event by
# spec_id OR correlation_id and not one seeded event above carries a correlation id, so the equality
# was proven over a population that could not exhibit a divergence in that half: deleting the
# correlation clause left this suite fully green while toe_corpus.cycles_for and spend_for both join
# on it. The two enumerations this module promises to keep equal would have parted company on the
# first correlation-attributed figure, silently and in the direction that UNDERSTATES an axis.
_JL_CORR_EVENTS = [{"schema": "veldo.event/v1", "type": "verdict.recorded",
                    "at": "2026-08-10T00:00:00Z", "correlation_id": "WARP-9430",
                    "human_minutes": 25, "tokens": 700}]
expect("WARP-1407 AC3: a figure attributed by correlation_id ALONE lands on the same spec in both "
       "enumerations - this module's per-field readers and the corpus's own total reader - so the "
       "correlation half of the one selector is inside the equality that row exists to prove",
       (JL.minutes_for(_JL_CORR_EVENTS, "WARP-9430")["minutes"],
        JL.tokens_for(_JL_CORR_EVENTS, "WARP-9430")["tokens"])
       == (JLTC.spend_for(_JL_CORR_EVENTS, "WARP-9430")["human_minutes"],
           JLTC.spend_for(_JL_CORR_EVENTS, "WARP-9430")["tokens"])
       == (25, 700)
       and JL.minutes_for(_JL_CORR_EVENTS, "WARP-9430")["minutes_recorded"] is True)
expect("WARP-1407 AC3 NEGATIVE CONTROL: a correlation id naming a DIFFERENT spec contributes to "
       "neither reader, so the equality above is attribution rather than two readers accepting "
       "whatever they are handed",
       (JL.minutes_for(_JL_CORR_EVENTS, "WARP-9431")["minutes"],
        JL.minutes_for(_JL_CORR_EVENTS, "WARP-9431")["minutes_recorded"],
        JL.tokens_for(_JL_CORR_EVENTS, "WARP-9431")["tokens_recorded"],
        JLTC.spend_for(_JL_CORR_EVENTS, "WARP-9431")["human_minutes"]) == (0, False, False, 0))
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
    # NaN AND INFINITY ARE NOT NON-NEGATIVE NUMBERS EITHER, and this is the shape AC4's total
    # property was refuted on: `nan < 0` and `inf < 0` are both False, so the sign test alone let
    # them through as well formed. `json.loads` accepts the bare NaN and Infinity literals and
    # events.read_log parses with it, so the input arrives from a log file rather than only from an
    # API call. Measured before the fix: the row rendered "judgment nan min" while coverage
    # reported 100.0 percent pair known, `check` reported 0 malformed figures over the same log, and
    # one NaN inside the both-axes population moved the median (15.0 with it first in the log, 25.0
    # with it last) and relabelled records that had nothing wrong with them.
    "a NaN": [_jl_ev("spec.shipped", "WARP-9410", human_minutes=float("nan"))],
    "an infinity": [_jl_ev("spec.shipped", "WARP-9410", human_minutes=float("inf"))],
    "a negative infinity": [_jl_ev("spec.shipped", "WARP-9410", human_minutes=float("-inf"))],
}
for _label, _evs in sorted(_JL_BAD.items()):
    _raised, _msg = _jl_refusal(JL.minutes_for, _evs, "WARP-9410")
    # THE VALUE IS ASSERTED IN THE MESSAGE, not only the field: AC4 requires the refusal to name the
    # field, the event type AND the value, and a message naming two of the three is what an author
    # cannot locate.
    expect("WARP-1407 AC4: %s human_minutes is refused BY NAME (the field, the event type and the "
           "value in the message)" % _label,
           _raised and "human_minutes" in _msg and "spec.shipped" in _msg
           and repr(_evs[0]["human_minutes"]) in _msg)
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
       _JL_ERRS == len(_JL_BAD) == 6 and len(_JL_MSGS) == 6
       and all("human_minutes" in m for m in _JL_MSGS))
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

# A RECORD WITH NO SPEC ID IS REFUSED BY NAME. With `spec` None the one selector compares None against
# every event's spec_id, so a phantom row collects the figures of every event that names no spec - the
# same figures the unattributable block reports as belonging to nobody, counted a second time on one
# page as if they belonged to somebody. Unreachable through toe_corpus.build, which skips a spec file
# with no id, and reachable through this public function, which is where the next caller finds it.
_JL_NOSPEC_RAISED, _JL_NOSPEC_MSG = _jl_refusal(JL.pair, {"features": {}}, [_JL_ORPHAN])
expect("WARP-1407 AC4: a corpus record naming no spec id is refused BY NAME rather than becoming a "
       "phantom row that collects every unattributable figure",
       _JL_NOSPEC_RAISED and "names no spec id" in _JL_NOSPEC_MSG
       and "unattributable" in _JL_NOSPEC_MSG)
expect("WARP-1407 AC4 NEGATIVE CONTROL: the same record WITH a spec id is accepted and does NOT "
       "collect the unattributable figures, so the refusal above is the missing id and not a reader "
       "that refuses whatever it is handed",
       _jl_refusal(JL.pair, {"spec": "WARP-9414", "features": {}}, [_JL_ORPHAN]) == (False, "")
       and (JL.pair({"spec": "WARP-9414", "features": {}}, [_JL_ORPHAN])["judgment_minutes"],
            JL.pair({"spec": "WARP-9414", "features": {}}, [_JL_ORPHAN])["judgment_known"])
       == (0, False))

# report AND check MUST NOT DISAGREE SILENTLY ABOUT ONE LOG. The judge is one; the two COMMANDS are
# not, because the derivation only reads figures for specs the corpus HOLDS. Measured before this
# counter existed: an adopter tree whose only event carried human_minutes '12' gave `report` exit 0 and
# a clean page while `check` exited 1 naming the figure, so a reader who ran report and saw green had
# not learned what check would tell them. The gap is not closed by widening the derivation - a pair is
# FOR a spec in the corpus - it is closed by the page saying how much it does not cover.
_JL_UNREAD_EVENTS = _JL_EVENTS + [_jl_ev("spec.shipped", "WARP-9499", tokens=7, human_minutes=3)]
expect("WARP-1407 AC4: figures recorded against a spec the corpus does not hold are COUNTED as "
       "figures the derivation did not read, both axes of them, and the count is on the page",
       JL.unread_figures(_JL_REPORT["rows"], _JL_UNREAD_EVENTS) == 2
       and JL.unread_figures(_JL_REPORT["rows"], _JL_EVENTS) == 0
       and "figures the derivation did not read: 0" in _JL_TEXT)
expect("WARP-1407 AC4 NEGATIVE CONTROL: an UNATTRIBUTABLE figure is not counted as unread - it has "
       "its own line with its own figures, and counting it in both places is the double count this "
       "distinction exists to avoid",
       JL.unread_figures(_JL_REPORT["rows"], [_JL_ORPHAN]) == 0
       and JL.unattributed([_JL_ORPHAN]) == {"events": 1, "minutes": 7, "tokens": 11})

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
#
# TWO TREES, AND ONLY THE SECOND ONE COULD EVER MOVE. The first block below digests the tree the
# FIXTURES were seeded into, which is a READ-ONLY-INPUT check and is labelled as one: build() is
# handed parsed records and holds no path at all, so no edit to the module could turn that digest
# red. The tree the write-nothing property is actually about is the one every path in this module is
# built from - JL.ROOT, resolved at call time - and that is the second block.
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
    expect("WARP-1407 AC5 READ-ONLY INPUTS: building and rendering the pair leaves the INPUT tree "
           "the fixtures were seeded into byte-identical", _jl_before == _jl_after)
    # POSITIVE CONTROL on the instrument itself: the digest DOES move when a byte changes, so the
    # equality above is a measurement rather than a digest that cannot notice anything.
    (Path(_jl_dir2) / "events.jsonl").write_text("changed\n")
    expect("WARP-1407 AC5 CONTROL: the tree digest notices a single changed file, so the "
           "unchanged result above is evidence", _jl_digest(_jl_dir2) != _jl_after)

# THE TREE THE MODULE RESOLVES AGAINST. A hermetic repository is seeded at a temp path - the
# package's own modules, a specs directory, an event log - JL.ROOT is pointed at it for the duration,
# and the WHOLE tree is digested around the full repo-shaped call: _repo_report(), which reaches for
# the log, the corpus, the protected set and the plan registry through ROOT, and render(). A writer
# anywhere under ROOT, which is the only shape a state file in this package could take, moves the
# digest. The call is asserted to have really run over that tree in the same breath as the digest,
# so an exception or an empty corpus cannot be what kept the tree unchanged.
with tempfile.TemporaryDirectory() as _jl_dir3:
    _jl_root3 = Path(_jl_dir3)
    (_jl_root3 / ".veldo").mkdir()
    (_jl_root3 / "specs").mkdir()
    (_jl_root3 / "plans").mkdir()
    for _jl_mod in sorted((ROOT / ".veldo").glob("*.py")):
        (_jl_root3 / ".veldo" / _jl_mod.name).write_bytes(_jl_mod.read_bytes())
    for _sid, _opts in sorted(_JL_SPECS.items()):
        (_jl_root3 / "specs" / ("%s.md" % _sid)).write_text(_jl_spec_text(_sid, **_opts))
    (_jl_root3 / ".veldo" / "events.jsonl").write_text(
        "\n".join(json.dumps(e, sort_keys=True) for e in _JL_EVENTS) + "\n")
    _jl_root_saved, _jl_pyc_saved = JL.ROOT, _jl_sys.dont_write_bytecode
    try:
        # The ONE thing suppressed for the duration, and it is the interpreter writing rather than
        # the derivation: loading the sibling modules by path caches their bytecode, which would put
        # a .veldo/__pycache__ into the seeded tree (measured: seven .pyc files, and nothing else).
        # Suppressing it is what lets the digest cover the WHOLE tree with no exclusion list, which
        # is a list a real writer could hide behind.
        JL.ROOT, _jl_sys.dont_write_bytecode = _jl_root3, True
        _jl_root_before = _jl_digest(_jl_root3)
        _jl_repo = JL._repo_report()
        _jl_repo_text = JL.render(_jl_repo)
        _jl_root_after = _jl_digest(_jl_root3)
    finally:
        JL.ROOT, _jl_sys.dont_write_bytecode = _jl_root_saved, _jl_pyc_saved
    expect("WARP-1407 AC5: reporting over the tree the module RESOLVES against leaves that tree "
           "byte-identical, and the derivation demonstrably ran over it (six rows, six records, a "
           "rendered report) rather than standing down",
           _jl_root_before == _jl_root_after
           and len(_jl_repo["rows"]) == 6 and _jl_repo["coverage"]["records"] == 6
           and "EFFORT IS A PAIR" in _jl_repo_text
           and sorted(_jl_repo["plans"]) == [JL.NO_PLAN, "PLAN-9400", "PLAN-9401"])
    expect("WARP-1407 AC5 CONTROL: ROOT is restored afterwards, so the assertions below read the "
           "real repository and not the fixture tree",
           JL.ROOT == ROOT and _jl_sys.dont_write_bytecode == _jl_pyc_saved)
    # POSITIVE CONTROL on this digest call site: ONE new file under .veldo/, which is the shape a
    # state writer in this package would take, moves it.
    (_jl_root3 / ".veldo" / "judgment_load_state.jsonl").write_text("{}\n")
    expect("WARP-1407 AC5 CONTROL: the digest over the ROOT tree notices one new file under "
           ".veldo/, so the byte-identical result above is a measurement",
           _jl_digest(_jl_root3) != _jl_root_after)

# ---------------------------------------------------------------------------------------
# ADOPTION SAFE IN A TREE THAT DOES NOT CARRY THE SIBLINGS, which is the tree `/veldo:init` lays down
# today: it lays down neither this module nor toe_corpus.py nor spend.py. MEASURED 2026-08-13 on
# exactly that shape, before the repair: `python3 .veldo/judgment_load.py report` exited 1 with a raw
# `FileNotFoundError: .veldo/toe_corpus.py`. That is ledger finding 61, and Dmitry's direction of
# 2026-08-13 is that a reader NAMES an absent organ instead of dying - work_state.py was repaired that
# way and this module had not inherited it. A traceback out of a read model is a run that could not
# look, indistinguishable from a run that found nothing; so is a page of zeros at 0.0 percent, which
# is why the derivation stand-down prints no figures at all.
#
# RUN IN A REAL TREE, NEVER SCANNED FOR A GUARD. Every leg below builds a tree, DELETES one organ from
# it and runs the CLI as a subprocess, so what is asserted is the exit code and the page an adopter
# reads. A grep for a try/except in the source would be a claim about today's text, and a text scan
# standing in for a real dependency is the defect this ledger records more than any other. The tree is
# built by copying every .veldo module and then removing ONE by name, so the fixture is a DEFECT BY
# CONSTRUCTION: nothing that changes what init lays down can empty it or quietly make it vacuous.
# ---------------------------------------------------------------------------------------
_JL_TREES = []


def _jl_tree(without=(), events=None):
    """A repository-shaped tree carrying every .veldo module EXCEPT the ones named, the seeded fixture
    specs and a log. Registered for removal at the end of the fragment."""
    d = Path(tempfile.mkdtemp(prefix="jl-organ-"))
    _JL_TREES.append(d)
    (d / ".veldo").mkdir()
    (d / "specs").mkdir()
    (d / "plans").mkdir()
    for _m in sorted((ROOT / ".veldo").glob("*.py")):
        if _m.name in without:
            continue
        (d / ".veldo" / _m.name).write_bytes(_m.read_bytes())
    for _sid, _o in sorted(_JL_SPECS.items()):
        (d / "specs" / ("%s.md" % _sid)).write_text(_jl_spec_text(_sid, **_o))
    (d / ".veldo" / "events.jsonl").write_text(
        "\n".join(json.dumps(e, sort_keys=True)
                  for e in (_JL_EVENTS if events is None else events)) + "\n")
    return d


def _jl_cli(tree, *args):
    """(exit code, output) of this module's own CLI run inside that tree. stdout and stderr are joined
    because a stand-down that went to the wrong stream is still a stand-down a reader must see, and
    the exit code is asserted separately."""
    _p = _jl_subprocess.run([_jl_sys.executable, ".veldo/judgment_load.py"] + list(args),
                            cwd=str(tree), capture_output=True, text=True)
    return _p.returncode, _p.stdout + _p.stderr


_JL_FULL = _jl_tree()
_JL_FULL_RC, _JL_FULL_OUT = _jl_cli(_JL_FULL, "report")
_JL_FULL_CHECK = _jl_cli(_JL_FULL, "check")
# THE CONTROL FIRST, because a stand-down is only evidence if the same tree WITH the organ reports.
expect("WARP-1407 AC5 CONTROL: with every organ present the CLI reports the seeded corpus and checks "
       "the seeded log, so the stand-downs below are the absent organ and not a tree that cannot "
       "work at all",
       (_JL_FULL_RC, _JL_FULL_CHECK[0]) == (0, 0)
       and "coverage: 6 record(s)" in _JL_FULL_OUT
       and "UNANSWERABLE" not in _JL_FULL_OUT
       and "malformed figure(s) in %d event(s)" % len(_JL_EVENTS) in _JL_FULL_CHECK[1])

_JL_NO_CORPUS = _jl_tree(without=("toe_corpus.py",))
_JL_NC_RC, _JL_NC_OUT = _jl_cli(_JL_NO_CORPUS, "report")
expect("WARP-1407 AC5: with the corpus organ absent the report NAMES it and exits 0 instead of "
       "dying, and it prints NO figure at all - not a page of zeros at 0.0 percent, which would "
       "state that this repository's axes are empty while measuring neither",
       _JL_NC_RC == 0
       and "JUDGMENT LOAD UNANSWERABLE IN THIS TREE" in _JL_NC_OUT
       and ".veldo/toe_corpus.py" in _JL_NC_OUT
       and "Traceback" not in _JL_NC_OUT and "FileNotFoundError" not in _JL_NC_OUT
       and "coverage:" not in _JL_NC_OUT and "0.0%" not in _JL_NC_OUT
       and "per plan:" not in _JL_NC_OUT)

_JL_NO_LOG = _jl_tree(without=("events.py",))
_JL_NL_RC, _JL_NL_OUT = _jl_cli(_JL_NO_LOG, "report")
_JL_NL_CHECK_RC, _JL_NL_CHECK_OUT = _jl_cli(_JL_NO_LOG, "check")
expect("WARP-1407 AC5: with the log organ absent the report names THAT organ, and `check` refuses "
       "rather than reporting a clean log it never opened - a check that could not look is not a pass",
       _JL_NL_RC == 0 and ".veldo/events.py" in _JL_NL_OUT
       and "JUDGMENT LOAD UNANSWERABLE IN THIS TREE" in _JL_NL_OUT
       and _JL_NL_CHECK_RC == 1
       and "NOT CHECKED" in _JL_NL_CHECK_OUT and ".veldo/events.py" in _JL_NL_CHECK_OUT
       and "0 malformed" not in _JL_NL_CHECK_OUT
       and "Traceback" not in _JL_NL_OUT + _JL_NL_CHECK_OUT)

# A PARTIAL STAND-DOWN IS SCOPED TO THE COLUMN IT IS ABOUT. The plan registry organ carries only the
# DENOMINATORS, so its absence does not invalidate a single row: the rows print, and the reason the
# denominators read "(not declared)" is the absent organ rather than a plan declaring no items.
_JL_NO_REG = _jl_tree(without=("validate.py",))
_JL_NR_RC, _JL_NR_OUT = _jl_cli(_JL_NO_REG, "report")
expect("WARP-1407 AC5: with the plan registry organ absent the rows are still reported and the "
       "DENOMINATORS stand down by name, so '(not declared)' is never left to mean two things",
       _JL_NR_RC == 0
       and "DENOMINATORS STOOD DOWN" in _JL_NR_OUT and ".veldo/validate.py" in _JL_NR_OUT
       and "coverage: 6 record(s)" in _JL_NR_OUT
       and "of (not declared) work item spec(s)" in _JL_NR_OUT
       and "JUDGMENT LOAD UNANSWERABLE" not in _JL_NR_OUT
       and "Traceback" not in _JL_NR_OUT)

# THE NaN, END TO END THROUGH THE CLI, in the tree an adopter would run it in - because the refutation
# was measured there and not in a unit call. Before the repair: `check` printed "0 malformed figure(s)
# in 1 event(s)" and exited 0, and `report` exited 0 printing "judgment nan min" beside "judgment
# minutes known on 1 (100.0%)". The log is written with the bare NaN literal json.dumps emits, which
# is exactly how it would reach an adopter's tree.
_JL_NAN_TREE = _jl_tree(events=[_jl_ev("spec.shipped", "WARP-9401", tokens=5,
                                       human_minutes=float("nan"))])
_JL_NAN_CHECK_RC, _JL_NAN_CHECK_OUT = _jl_cli(_JL_NAN_TREE, "check")
_JL_NAN_REPORT_RC, _JL_NAN_REPORT_OUT = _jl_cli(_JL_NAN_TREE, "report")
expect("WARP-1407 AC4: a NaN figure in a real log on disk is named by `check` and refuses the "
       "derivation in `report`, and neither surface ever prints it as a measured figure",
       "NaN" in (_JL_NAN_TREE / ".veldo" / "events.jsonl").read_text()
       and _JL_NAN_CHECK_RC == 1
       and "1 malformed figure(s) in 1 event(s)" in _JL_NAN_CHECK_OUT
       and "human_minutes" in _JL_NAN_CHECK_OUT and "nan" in _JL_NAN_CHECK_OUT
       and _JL_NAN_REPORT_RC == 1
       and "refusing to report judgment load" in _JL_NAN_REPORT_OUT
       and "judgment nan min" not in _JL_NAN_REPORT_OUT
       and "100.0%" not in _JL_NAN_REPORT_OUT)

# report AND check OVER ONE LOG, END TO END, in the tree an adopter would run them in. The single
# figure here is BOTH malformed AND on a spec the corpus does not hold, which is exactly the state the
# review measured the two commands disagreeing about: check names it and report cannot read it. Report
# still exits 0, because nothing it derived is wrong, and it now says how many figures it did not read.
_JL_UNREAD_TREE = _jl_tree(events=[_jl_ev("spec.shipped", "WARP-9499", human_minutes="12")])
_JL_UR_CHECK_RC, _JL_UR_CHECK_OUT = _jl_cli(_JL_UNREAD_TREE, "check")
_JL_UR_REPORT_RC, _JL_UR_REPORT_OUT = _jl_cli(_JL_UNREAD_TREE, "report")
expect("WARP-1407 AC4: over one log the two commands do not disagree silently - `check` names the "
       "malformed figure and exits 1, and `report` exits 0 while stating on the page that there was a "
       "figure it did not read",
       _JL_UR_CHECK_RC == 1 and "human_minutes" in _JL_UR_CHECK_OUT
       and "WARP-9499" in _JL_UR_CHECK_OUT
       and _JL_UR_REPORT_RC == 0
       and "figures the derivation did not read: 1" in _JL_UR_REPORT_OUT
       and "coverage: 6 record(s)" in _JL_UR_REPORT_OUT)

for _t in _JL_TREES:
    _jl_shutil.rmtree(_t, ignore_errors=True)

# ---------------------------------------------------------------------------------------
# LIVE, over this repository's real corpus and real log. Two properties that must hold whatever the
# data says: every accusation the judge makes about the real log is true, and every row whose axis was
# never recorded is unknown rather than labelled. The MEASURED numbers behind the spec's prose (0
# percent minutes coverage over 174 shipped specs, 81 percent episode coverage) are recorded in the
# spec, not pinned here, because pinning a live count reddens the gate the first time someone records
# a minute - which is the outcome this item wants.
# ---------------------------------------------------------------------------------------
_JL_REAL_EVENTS = JLEV.read_log()


def _jl_unreadable(event):
    """WHICH FIGURES OF ONE EVENT ARE NOT NON-NEGATIVE FINITE NUMBERS, written from AC4's own words
    rather than by calling the judge. Deliberately a second reading: it exists to check the judge over
    the real log, and a row that asked the judge whether it agrees with itself would pass by
    construction."""
    bad = []
    for _f in (JL.MINUTES_FIELD, JL.TOKENS_FIELD):
        _v = event.get(_f)
        if _v is None:
            continue
        if (isinstance(_v, bool) or not isinstance(_v, (int, float))
                or not _jl_math.isfinite(_v) or _v < 0):
            bad.append(_f)
    return bad


def _jl_judged(events):
    """(count the judge reports, count the independent reading reports) over one log."""
    return (JL.check_log(events, "seeded.jsonl", lambda where, msg: 1),
            sum(len(_jl_unreadable(e)) if isinstance(e, dict) else 1 for e in events))


# NOT A PIN ON LIVE STATE, and the difference is the whole finding. The row here used to require
# `check_log(...) == 0` over the real log inside a REQUIRED gate stage: the log is append-only, so one
# malformed figure ever written would make it permanently red with no remediation short of rewriting
# history - and this module's own docstring uses exactly that reasoning to explain why an
# unattributable event is COUNTED rather than refused. What is required instead is the PROPERTY the
# pin stood in for: the judge and an independent reading of AC4's words agree about the real log, in
# both directions, whatever the count is. A genuinely malformed figure appended tomorrow keeps this
# green; a judge that misses one, or names one that is fine, reds it. The seeded leg is the
# anti-vacuity control, because agreement over a clean log is agreement about nothing.
_JL_REAL_JUDGED, _JL_REAL_INDEP = _jl_judged(_JL_REAL_EVENTS)
_JL_SEEDED_BAD = [e for _evs in _JL_BAD.values() for e in _evs] + _JL_EVENTS
_JL_SEED_JUDGED, _JL_SEED_INDEP = _jl_judged(_JL_SEEDED_BAD)
expect("WARP-1407 LIVE: the judge and an independent reading of what a well-formed figure is agree "
       "about every event in the real log, and this row requires that count to be no particular "
       "number - a malformed figure in an append-only log is a state to report, never a gate to "
       "wedge",
       _JL_REAL_JUDGED == _JL_REAL_INDEP
       and (_JL_SEED_JUDGED, _JL_SEED_INDEP) == (len(_JL_BAD), len(_JL_BAD))
       and len(_JL_REAL_EVENTS) > 0)
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
