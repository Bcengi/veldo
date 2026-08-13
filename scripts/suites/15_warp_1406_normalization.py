"""WARP-1406 (W6 of PLAN-0014): normalization, the stable planning unit over raw-token ground truth.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Run it alone with
`python3 scripts/selftest.py --suite 15_warp_1406_normalization`, which runs this fragment plus its
declared prerequisite closure, which is itself alone.

WHAT IS OBSERVED HERE, AND WHY EACH POSITIVE HAS A NEGATIVE BESIDE IT. Every assertion in this
block is paired with a control that would pass if the code under test did nothing at all, so a
green line here is a measurement and not an absence:

  - a point is produced for a record whose TOKEN spend was recorded, and withheld with a NAMED
    reason for one whose was not, so the point generator is neither always-a-number nor
    always-a-null. Driven over the FOUR distinct shapes that reach that branch rather than one:
    nothing recorded at all, a change costed only in DOLLARS, a change costed only in HUMAN MINUTES,
    and a spend record of `tokens=0` that the SANCTIONED WRITER accepts. The last three arrive with
    the corpus's `spend_recorded` flag TRUE and no usable token count, which is how a confident 0.000
    reached the surface, the four reasons are asserted to be four DISTINCT strings, and the control
    beside them adds a token count and requires the point to come ON;
  - the RENDERED LINE is asserted as the COMPLETE ORDERED LIST OF FIGURES IT PRINTS, at two prices,
    rather than by the absence of a literal. The decision that the line does not print the RECORDED
    cost cannot be guarded by an absent spelling: a render that appends the recorded cost rounded, or
    that puts the recorded cost in the money column of the row whose tokens were never recorded,
    prints it while every spelling checked for is still absent;
  - the recorded columns are asserted against the corpus's own spend block over values that are
    deliberately NOT round, because every value in the first fixture is a multiple of 100 and a
    display that rounded the recorded actual to the nearest 100 passed the whole fragment;
  - the summary roll-up, which is the bottom line of every rendered report and the number a planner
    sizes work with, is asserted as ONE whole-dict equality per fixture rather than key by key, so a
    silently added key reds too, and the PRINTED total line is asserted beside it;
  - the derived peg is shown to MOVE when the corpus moves, so the median is computed rather than
    the first or the last element being picked;
  - the byte-identity of the actuals across a re-peg is asserted with a COMPARATOR THAT IS ITSELF
    SHOWN TO DETECT A CHANGE (a deliberate tamper), because "nothing changed" proves nothing if
    the comparison could not see a change;
  - the two views across a re-peg are required to DIFFER, so the identity of the data underneath is
    not the identity of a run in which nothing happened;
  - the era refusal is paired with a one-era control in which those SAME rows all get points, so
    the null is the era rule firing and not a function that refuses everything;
  - every malformed-record refusal is paired with the well-formed record validating CLEAN.

THE NON-NEGOTIABLE PROPERTY IS DRIVEN ON DISK, NOT ARGUED. The re-peg leg seeds a real tree with a
real event log file, hashes the corpus and the log bytes and mtime, re-pegs and re-prices twice, and
requires the bytes and the mtime to be unchanged while the displayed numbers move.
"""
import re as _w1406_re  # noqa: E402 - the figure reader below; the fragment IS the module body

_w1406_nspec = importlib.util.spec_from_file_location(
    "veldo_toe_normalize_suite", ROOT / ".veldo/toe_normalize.py")
NORM = importlib.util.module_from_spec(_w1406_nspec)
_w1406_nspec.loader.exec_module(NORM)

_w1406_cspec = importlib.util.spec_from_file_location(
    "veldo_toe_corpus_1406", ROOT / ".veldo/toe_corpus.py")
CORP = importlib.util.module_from_spec(_w1406_cspec)
_w1406_cspec.loader.exec_module(CORP)

_w1406_mspec = importlib.util.spec_from_file_location(
    "veldo_metrics_1406", ROOT / ".veldo/metrics.py")
_W1406_M = importlib.util.module_from_spec(_w1406_mspec)
_w1406_mspec.loader.exec_module(_W1406_M)
_W1406_ISO = _W1406_M.parse_iso

_W1406_SPEC = """---
schema: veldo.spec/v1
id: %(id)s
title: a seeded change for the normalization fixture
status: shipped
risk: %(risk)s
plan: PLAN-0014
lane: planned
human_approval: not_required
acceptance_criteria:
  - id: AC1
    text: one
---
body
"""


def _w1406_seed_specs(d, entries):
    """One spec file per (id, risk) entry, in a directory the corpus can be built over."""
    for sid, risk in entries:
        tmpfile(d, "%s-seeded.md" % sid, _W1406_SPEC % {"id": sid, "risk": risk})
    return d


def _w1406_ev(sid, tokens=None, at=None, cost_usd=None, human_minutes=None):
    """One shipped event carrying whatever spend fields this fixture names, and ONLY those.

    A field left None is ABSENT from the envelope rather than present as a zero, because "never
    recorded" and "recorded as zero" are the two facts this whole item exists to keep apart, and a
    fixture that cannot express the first one cannot test the refusal. The shipped emitter declares
    the token, dollar and human-minute flags independently and optionally (.veldo/events.py), so an
    event carrying a cost and no token count is the ordinary case and not a hostile one."""
    e = {"schema": "veldo.event/v1", "type": "spec.shipped", "spec_id": sid}
    for _k, _v in (("tokens", tokens), ("cost_usd", cost_usd),
                   ("human_minutes", human_minutes), ("at", at)):
        if _v is not None:
            e[_k] = _v
    return e


def _w1406_capture():
    """(messages, report) - a reporter with validate.fail's shape that records instead of printing,
    so a refusal can be asserted BY ITS TEXT rather than by a bare non-zero count."""
    msgs = []

    def report(name, msg):
        msgs.append("%s: %s" % (name, msg))
        return 1

    return msgs, report


def _w1406_points(view):
    return {r["spec"]: r["points"] for r in view["rows"]}


def _w1406_reason(view, sid):
    for r in view["rows"]:
        if r["spec"] == sid:
            return r["reason"] or ""
    return ""


def _w1406_line(lines, sid):
    """The rendered ROW line for one spec, or the empty string. Matched on the line's OWN OPENING
    field rather than by `in`, because the peg header also names a spec, and matched by resolution
    rather than by index, because a positional pin measures whatever moved into that slot."""
    for line in lines:
        if line.startswith(sid):
            return line
    return ""


def _w1406_pt_cells(lines):
    """The point cell of every rendered line that carries one, so two renders can be compared on
    their POINTS alone while their money columns differ."""
    return [line.split(" pt")[0].split()[-1] for line in lines if " pt" in line and " tok" in line]


def _w1406_row_cells(lines, ids):
    """The point cell of each named ROW, in the order the ids are given, resolved the way
    `_w1406_line` resolves a row rather than by position. Separate from `_w1406_pt_cells` because
    that helper reads every line carrying both markers, which includes the ROLL-UP (its own text
    carries `pt` and `raw tokens`), and a list pinned to literals has to be exactly the rows."""
    return [_w1406_line(lines, sid).split(" pt")[0].split()[-1] for sid in ids]


_W1406_FIGURE = _w1406_re.compile(r"\d+(?:\.\d+)?")


def _w1406_figures(line, with_reason=False):
    """Every FIGURE one rendered row line PRINTS, in order, as the exact strings it printed.

    THIS IS THE INSTRUMENT THE "DOES NOT PRINT THE RECORDED COST" DECISION NEEDS, and the reason it
    reads a whole list rather than searching for a value is that a search can only be run for
    spellings somebody thought of: `12.37` rounded to `12.4`, or moved into another row's column, is
    the same recorded cost reaching the same reader past the same check. A complete list has no
    spellings in it - anything printed is either in the list or reds it.

    The leading spec field is dropped because a spec id carries digits of its own, and the trailing
    parenthesised reason is dropped unless it is asked for, because a reason is prose the module put
    on the ROW while the claim under test is about what the COLUMNS say."""
    body = line if with_reason else line.partition("  (")[0]
    parts = body.split(None, 1)
    return _W1406_FIGURE.findall(parts[1]) if len(parts) > 1 else []


def _w1406_raised(fn, *a, **kw):
    """(raised, message) for one attempt. The MESSAGE is returned because an assertion that
    something raised, without checking WHAT, passes on an unrelated TypeError."""
    try:
        fn(*a, **kw)
    except BaseException as e:
        return True, "%s: %s" % (type(e).__name__, e)
    return False, ""


# ---------------------------------------------------------------------------------------
# FIXTURE A: five standard-risk changes with recorded token spend, one standard-risk change
# with NO spend at all, and one high-risk change with spend. No era ledger, so everything
# sits in the implicit pre-ledger era.
# ---------------------------------------------------------------------------------------
_W1406_A_SPEND = [("WARP-9411", 1000), ("WARP-9412", 2000), ("WARP-9413", 3000),
                  ("WARP-9414", 4000), ("WARP-9415", 5000)]
_w1406_a_events = [_w1406_ev(sid, tok, "2026-01-%02dT00:00:00Z" % (i + 1))
                   for i, (sid, tok) in enumerate(_W1406_A_SPEND)]
_w1406_a_events.append(_w1406_ev("WARP-9417", 9000, "2026-01-06T00:00:00Z"))

with tempfile.TemporaryDirectory() as _w1406_da:
    _w1406_seed_specs(_w1406_da, [(sid, "standard") for sid, _t in _W1406_A_SPEND]
                      + [("WARP-9416", "standard"), ("WARP-9417", "high")])
    _W1406_A = CORP.build(specs_dir=_w1406_da, events=_w1406_a_events)

_w1406_no_eras = NORM.eras([])
_w1406_peg_a = NORM.resolve_peg(_W1406_A, _w1406_a_events, _w1406_no_eras, CORP, _W1406_ISO)
_w1406_view_a = NORM.normalize(_W1406_A, _w1406_peg_a, _w1406_a_events, _w1406_no_eras,
                               CORP, _W1406_ISO)

# ---------------------------------------------------------------------------------------
# FIXTURE H: HOSTILE NUMBERS, AND SPEND THAT IS NOT TOKEN SPEND.
#
# Two changes whose recorded token counts and recorded dollar costs are deliberately NOT round
# (3137 tokens at 12.37 usd, 41 tokens at 0.0137 usd). Every value in fixture A is a multiple of
# 100, which is enough for a display layer that rounded the recorded actual to the nearest 100 to
# pass every assertion in this fragment, so the rounding leg of AC1 is driven here instead.
#
# Plus the two shapes the point gate has to refuse WITHOUT printing a zero: a change whose only
# recorded spend is a DOLLAR COST, and one whose only recorded spend is HUMAN MINUTES. Both come out
# of the corpus with spend_recorded TRUE and a token count of zero, because `spend_recorded` answers
# "did anybody record anything" and not "was this measured in tokens".
# ---------------------------------------------------------------------------------------
_W1406_H_IDS = ("WARP-9421", "WARP-9422", "WARP-9423", "WARP-9424")
_W1406_H_EVENTS = [
    _w1406_ev("WARP-9421", 3137, "2026-02-01T00:00:00Z", cost_usd=12.37),
    _w1406_ev("WARP-9422", 41, "2026-02-02T00:00:00Z", cost_usd=0.0137),
    _w1406_ev("WARP-9423", None, "2026-02-03T00:00:00Z", cost_usd=7.5),
    _w1406_ev("WARP-9424", None, "2026-02-04T00:00:00Z", human_minutes=90),
]
with tempfile.TemporaryDirectory() as _w1406_dh:
    _w1406_seed_specs(_w1406_dh, [(sid, "standard") for sid in _W1406_H_IDS])
    _W1406_H = CORP.build(specs_dir=_w1406_dh, events=_W1406_H_EVENTS)

# A DECLARED peg of 1000 tokens, so every expected point below is readable by eye from the recorded
# count and a rounding at any granularity moves it.
_W1406_H_DECL = {"schema": NORM.SCHEMA_PEG, "basis": NORM.PEG_DECLARED, "tokens": 1000,
                 "era": NORM.ERA_UNSTAMPED, "spec": "WARP-9421"}
_w1406_peg_h = NORM.resolve_peg(_W1406_H, _W1406_H_EVENTS, _w1406_no_eras, CORP, _W1406_ISO,
                                declared=_W1406_H_DECL)
_w1406_view_h = NORM.normalize(_W1406_H, _w1406_peg_h, _W1406_H_EVENTS, _w1406_no_eras,
                               CORP, _W1406_ISO)
# The DERIVED peg over the same corpus, to show ONE predicate governs the peg path and the display
# path: neither token-less change can become the reference change either.
_w1406_peg_h_derived = NORM.resolve_peg(_W1406_H, _W1406_H_EVENTS, _w1406_no_eras, CORP, _W1406_ISO)
# The same corpus with a token count added to the cost-only change, and it is added AS AN EVENT and
# rebuilt through the corpus rather than written into the spend block by hand: the era of a row is
# read from the events that carried its TOKEN count, so a corpus record claiming tokens no event
# carries is a state the real path cannot produce, and a control built that way would be a control
# over an impossible tree. The original corpus and event list are asserted untouched below.
_W1406_H_TOKENED_EVENTS = _W1406_H_EVENTS + [
    _w1406_ev("WARP-9423", 2000, "2026-02-03T00:00:00Z")]
with tempfile.TemporaryDirectory() as _w1406_dht:
    _w1406_seed_specs(_w1406_dht, [(sid, "standard") for sid in _W1406_H_IDS])
    _W1406_H_TOKENED = CORP.build(specs_dir=_w1406_dht, events=_W1406_H_TOKENED_EVENTS)
_w1406_view_h_tokened = NORM.normalize(_W1406_H_TOKENED, _w1406_peg_h, _W1406_H_TOKENED_EVENTS,
                                       _w1406_no_eras, CORP, _W1406_ISO)

# ---------------------------------------------------------------------------------------
# FIXTURE R: A RATIO BELOW THE DISPLAY RESOLUTION, WHICH IS THE SPREAD AN AGENT-RUN REPOSITORY
# ACTUALLY HAS.
#
# Three changes at 300000 tokens and two at 100, so the peg is 300000 and the two small changes are
# at 1/3000 of it. `round(x, 3)` is 0.0 for any ratio under 0.0005, so BOTH of these were MEASURED
# changes that rendered as `0.000 pt` - the exact string AC1 forbids - and, because points_total
# summed the ROUNDED points, each contributed exactly zero to the bottom line a plan is sized with.
# Fixture H could not see it: its smallest ratio is 0.041, so the guard `'0.000 pt' not in ...` was
# scoped to a fixture whose numbers cannot produce the string it forbids.
# ---------------------------------------------------------------------------------------
_W1406_R_SPEND = [("WARP-9431", 300000), ("WARP-9432", 300000), ("WARP-9433", 300000),
                  ("WARP-9434", 100), ("WARP-9435", 100)]
_W1406_R_EVENTS = [_w1406_ev(sid, tok, "2026-03-%02dT00:00:00Z" % (i + 1))
                   for i, (sid, tok) in enumerate(_W1406_R_SPEND)]
with tempfile.TemporaryDirectory() as _w1406_dr:
    _w1406_seed_specs(_w1406_dr, [(sid, "standard") for sid, _t in _W1406_R_SPEND])
    _W1406_R = CORP.build(specs_dir=_w1406_dr, events=_W1406_R_EVENTS)
_w1406_peg_r = NORM.resolve_peg(_W1406_R, _W1406_R_EVENTS, _w1406_no_eras, CORP, _W1406_ISO)
_w1406_view_r = NORM.normalize(_W1406_R, _w1406_peg_r, _W1406_R_EVENTS, _w1406_no_eras,
                               CORP, _W1406_ISO)
_W1406_R_TRUE = 3 * 1.0 + 2 * (100 / 300000)

# ---------------------------------------------------------------------------------------
# AC1. THE NORMALIZED POINT, WITH RAW TOKENS ON THE SAME ROW.
# ---------------------------------------------------------------------------------------
expect("WARP-1406 AC1, THE CONFIDENT ZERO ONE ROUNDING AWAY: A MEASURED CHANGE BELOW THE DISPLAY "
       "RESOLUTION IS RENDERED AS `<0.001 pt` AND STILL COUNTS IN THE TOTAL, driven over a fixture "
       "whose spread can PRODUCE the forbidden string. Two changes of 100 tokens against a peg of "
       "300000 are at 1/3000 of the reference change: %.3f of that ratio is `0.000`, so the display "
       "printed a zero point beside a real token count - indistinguishable, on the surface a planner "
       "reads, from a change nobody measured - and points_total, summing the ROUNDED points, valued "
       "both of them at exactly nothing. The peg's own three changes are unaffected at 1.000, so "
       "this is the ruler's resolution being named and not a rescale. THE ROLL-UP IS THE OTHER HALF "
       "AND IT IS PINNED TO THE UNROUNDED SUM: 3.001, not the 3.0 that summing rounded points gives, "
       "and the two literals are asserted DIFFERENT so the row cannot pass on a total that lost them",
       "0.000 pt" not in "".join(NORM.render_lines(_w1406_view_r))
       and _w1406_row_cells(NORM.render_lines(_w1406_view_r), [s for s, _t in _W1406_R_SPEND])
       == ["1.000", "1.000", "1.000", "<0.001", "<0.001"]
       and _w1406_points(_w1406_view_r)["WARP-9434"] == 100 / 300000
       and _w1406_view_r["summary"]["points_total"] == round(_W1406_R_TRUE, 3) == 3.001
       and round(_W1406_R_TRUE, 3) != 3.0
       and _w1406_view_r["summary"]["pointed"] == 5
       and _w1406_view_r["summary"]["unpointed"] == 0)

expect("WARP-1406 AC1 NEGATIVE CONTROL FOR THE BELOW-RESOLUTION CELL: the cell is a fact about the "
       "RULER and not about the change, so the same two changes measured against a peg they are NOT "
       "tiny against carry ordinary points, and a change whose token count was never recorded still "
       "gets `- pt` rather than `<0.001 pt`. Without this leg a render that printed `<0.001` for "
       "every small-looking row, or for every row at all, would pass the assertion above",
       _w1406_row_cells(NORM.render_lines(NORM.normalize(
           _W1406_R, dict(_w1406_peg_r, tokens=100), _W1406_R_EVENTS, _w1406_no_eras, CORP,
           _W1406_ISO)), [s for s, _t in _W1406_R_SPEND])
       == ["3000.000", "3000.000", "3000.000", "1.000", "1.000"]
       and NORM.point_cell(None) == "        - pt"
       and NORM.point_cell(0.041) == "    0.041 pt"
       and NORM.point_cell(0.0004) == "   <0.001 pt")
expect("WARP-1406 AC1: every corpus record with recorded spend renders as a NORMALIZED POINT "
       "against the peg, and the peg's own change is exactly 1.000 pt. The five seeded changes at "
       "1000, 2000, 3000, 4000 and 5000 tokens against a 3000-token peg come out at 0.333, 0.667, "
       "1.000, 1.333 and 1.667 ON THE SCREEN, and the ROW carries the ratio UNROUNDED, which is "
       "asserted here as the exact quotients: the point is a ratio of tokens to the reference "
       "change and not a rescaled copy of the raw number, and the rounding belongs to the DISPLAY "
       "and to the roll-up rather than to the stored row. Both halves are asserted because they "
       "are two different claims: rounding into the row is invisible on this fixture and is what "
       "made a small measured change contribute exactly zero to a plan's bottom line",
       _w1406_points(_w1406_view_a).get("WARP-9413") == 1.0
       and [_w1406_points(_w1406_view_a).get(s) for s, _t in _W1406_A_SPEND]
       == [1000 / 3000, 2000 / 3000, 1.0, 4000 / 3000, 5000 / 3000]
       and _w1406_row_cells(NORM.render_lines(_w1406_view_a),
                            [s for s, _t in _W1406_A_SPEND] + ["WARP-9416", "WARP-9417"])
       == ["0.333", "0.667", "1.000", "1.333", "1.667", "-", "3.000"])

expect("WARP-1406 AC1: THE RAW TOKENS AND THE RECORDED COST RIDE ON THE SAME ROW AS THE POINT, byte "
       "for byte the numbers the corpus recorded (D2: both units, the point primary on a planning "
       "surface and the raw ground truth one field away). Asserted as EQUALITY against the corpus's "
       "own spend block for EVERY row of TWO corpora rather than for a sample, and the second one "
       "carries deliberately NON-ROUND values - 3137 and 41 tokens, 12.37 and 0.0137 recorded usd - "
       "with the expected pairs PINNED to literals beside the equality. Both legs are needed: with "
       "fixture A alone every token value was a multiple of 100, so rounding the recorded actual to "
       "the nearest 100 passed, and every recorded cost was 0.0, so hard-coding the cost column to "
       "zero or scaling it by 100 passed as well. A rounded actual and a 100x money column are the "
       "two ways this display could look exactly like a working one while every plan built on it "
       "was wrong",
       [(r["spec"], r["tokens"], r["cost_usd"]) for r in _w1406_view_a["rows"]]
       == [(r["spec"], r["spend"]["tokens"], r["spend"]["cost_usd"]) for r in _W1406_A]
       and [(r["spec"], r["tokens"], r["cost_usd"]) for r in _w1406_view_h["rows"]]
       == [(r["spec"], r["spend"]["tokens"], r["spend"]["cost_usd"]) for r in _W1406_H]
       and [(r["spec"], r["tokens"], r["cost_usd"]) for r in _w1406_view_h["rows"]]
       == [("WARP-9421", 3137, 12.37), ("WARP-9422", 41, 0.0137),
           ("WARP-9423", 0, 7.5), ("WARP-9424", 0, 0.0)])

expect("WARP-1406 AC1, THE CONFIDENT ZERO THIS ITEM EXISTS TO REFUSE, ON THE PATH THAT ACTUALLY "
       "REACHES IT: a change whose spend WAS recorded but NOT IN TOKENS gets NO POINT, and its "
       "reason NAMES the field that was recorded and says the token count was not. The corpus sets "
       "spend_recorded for ANY of tokens, cost_usd or human_minutes and the shipped emitter's three "
       "spend flags are independent and optional, so a change costed in dollars or in human minutes "
       "arrives here with spend recorded and a token count of zero. Gating the point on that flag "
       "printed 0.000 pt as a measurement, counted the change in the POINTED denominator and added "
       "its zero to the total - the exact shape AC1 forbids in its own words. Driven over both "
       "shapes, and both reasons are DIFFERENT TEXT from the nothing-recorded reason, because "
       "'recorded, but not in tokens' is a third fact and not the same silence",
       _w1406_points(_w1406_view_h) == {"WARP-9421": 3.137, "WARP-9422": 0.041,
                                       "WARP-9423": None, "WARP-9424": None}
       and "cost_usd" in _w1406_reason(_w1406_view_h, "WARP-9423")
       and "NOT in tokens" in _w1406_reason(_w1406_view_h, "WARP-9423")
       and "human_minutes" in _w1406_reason(_w1406_view_h, "WARP-9424")
       and "NOT in tokens" in _w1406_reason(_w1406_view_h, "WARP-9424")
       and _w1406_reason(_w1406_view_h, "WARP-9423")
       != _w1406_reason(_w1406_view_h, "WARP-9424")
       and _w1406_reason(_w1406_view_h, "WARP-9423")
       != _w1406_reason(_w1406_view_a, "WARP-9416")
       and "0.000 pt" not in "".join(NORM.render_lines(_w1406_view_h))
       and "- pt" in _w1406_line(NORM.render_lines(_w1406_view_h), "WARP-9423"))

expect("WARP-1406 AC1 NEGATIVE CONTROL FOR THE TOKEN PREDICATE: those two rows DO carry recorded "
       "spend and their recorded dollars are on the view, so the withheld points above are the "
       "TOKEN test firing and not the corpus having nothing to show; ADDING a token count to the "
       "cost-only change turns its point ON at 2.000 against the 1000-token peg, so the refusal is "
       "a rule rather than a blanket; and the SAME predicate governs the PEG, which derives to "
       "WARP-9422 over a sample of 2 rather than pulling a token-less change into the median. One "
       "predicate on both paths is the fix: the peg path already required a positive token count "
       "while the display path required only the flag, which is how two readers of one corpus "
       "disagreed about which changes were measured",
       all(r["spend_recorded"] is True for r in _w1406_view_h["rows"])
       and [r["cost_usd"] for r in _w1406_view_h["rows"] if r["spec"] == "WARP-9423"] == [7.5]
       and _w1406_points(_w1406_view_h_tokened)["WARP-9423"] == 2.0
       and _w1406_points(_w1406_view_h)["WARP-9423"] is None
       and [(r["spec"], r["spend"]["tokens"]) for r in _W1406_H]
       == [("WARP-9421", 3137), ("WARP-9422", 41), ("WARP-9423", 0), ("WARP-9424", 0)]
       and _w1406_peg_h_derived["pegged"] is True
       and _w1406_peg_h_derived["spec"] == "WARP-9422"
       and _w1406_peg_h_derived["tokens"] == 41
       and _w1406_peg_h_derived["sample"] == 2)

# WHAT EVERY RENDERED ROW OF FIXTURE H MUST PRINT, AT TWO PRICES, AS THE COMPLETE ORDERED LIST OF ITS
# FIGURES. Pinned to literals because the fixture is fully known: the point cell where there is one,
# the RECORDED token count, and the money column, which is the price applied to those tokens and
# nothing else. The recorded costs on these rows are 12.37, 0.0137 and 7.50, and NONE of the three is
# in either list at either price - not because a spelling of them was searched for and not found, but
# because every figure the line prints is enumerated here and there is no room left for a fourth.
#
# THE 4.00 PRICE IS CHOSEN SO THE DERIVED FIGURE LANDS NEXT DOOR TO THE RECORDED ONE: 3137 tokens at
# 4.00 per 1k is 12.55 against a recorded 12.37. A reader eyeballing that column cannot tell the two
# apart, which is exactly why the column has to be the derived one by assertion.
#
# AND THE MONEY CELL IS ABSENT ENTIRELY ON THE TWO ROWS WHOSE TOKENS WERE NEVER RECORDED, which is
# why their figure lists are one figure long. The column used to print a DERIVED `0.00 usd` there,
# so a change whose recorded cost is 7.50 reported nothing in the money column of the row whose
# whole message is that nothing was measured: the confident zero this item refuses, one column over
# from the `- pt` that gets it right.
_W1406_H_FIGS_050 = [("WARP-9421", ["3.137", "3137", "1.57"]),
                     ("WARP-9422", ["0.041", "41", "0.02"]),
                     ("WARP-9423", ["0"]),
                     ("WARP-9424", ["0"])]
_W1406_H_FIGS_400 = [("WARP-9421", ["3.137", "3137", "12.55"]),
                     ("WARP-9422", ["0.041", "41", "0.16"]),
                     ("WARP-9423", ["0"]),
                     ("WARP-9424", ["0"])]


def _w1406_h_figs(price, with_reason=False):
    """(spec, every figure its rendered line prints) for every row of fixture H, in corpus order."""
    _lines = NORM.render_lines(_w1406_view_h, price)
    return [(sid, _w1406_figures(_w1406_line(_lines, sid), with_reason)) for sid in _W1406_H_IDS]


expect("WARP-1406 AC1: THE RENDERED LINE PRINTS THE POINT, THE RECORDED TOKENS AND THE PRICE APPLIED "
       "TO THOSE TOKENS, AND NOTHING ELSE - SO IT DOES NOT PRINT THE RECORDED COST, which rides on "
       "the view ROW where a consumer reads it. Asserted as the COMPLETE ORDERED LIST OF FIGURES each "
       "line prints, for every row, at TWO prices, pinned to literals and bound to the fixture's own "
       "length. The recorded costs here are 12.37, 0.0137 and 7.50 and none of them can appear, "
       "because the figures are enumerated rather than searched: a check spelled as 'the string 12.37 "
       "is absent' passes on a line that appends the recorded cost ROUNDED (12.4), and on a money "
       "column that shows the recorded 7.50 on the very row whose tokens were never recorded, and "
       "both of those print the recorded cost to the reader. The 4.00 price puts the derived figure "
       "at 12.55 next to a recorded 12.37 on purpose: eyeballing that column cannot tell them apart. "
       "The whole line is then read INCLUDING the reason, where no figure belongs either, so a cost "
       "appended anywhere on a row reds this; and because a per-row check can only see rows, the "
       "render is closed off at both ends: the PEG HEADER and the ROLL-UP are byte-identical priced "
       "and unpriced, and the line count is the rows plus exactly those two, so the price adds one "
       "COLUMN and there is nowhere else in the render for a dollar figure to sit. THE MONEY CELL IS "
       "WITHHELD, as `- usd`, ON THE TWO ROWS WHOSE TOKENS WERE NEVER RECORDED, which is why their "
       "figure lists carry ONE figure: the column is derived from a token count that does not exist, "
       "and printing its derived 0.00 told a reader that a change whose recorded cost is 7.50 cost "
       "nothing - the same confident zero the point column refuses with `- pt`, one column over",
       _w1406_h_figs(0.5) == _W1406_H_FIGS_050
       and _w1406_h_figs(4.0) == _W1406_H_FIGS_400
       and len(_W1406_H_FIGS_050) == len(_W1406_H_FIGS_400) == len(_W1406_H_IDS) == 4
       and "- usd" in _w1406_line(NORM.render_lines(_w1406_view_h, 4.0), "WARP-9423")
       and "- usd" in _w1406_line(NORM.render_lines(_w1406_view_h, 4.0), "WARP-9424")
       and " 1.57 usd" in _w1406_line(NORM.render_lines(_w1406_view_h, 0.5), "WARP-9421")
       and " 12.55 usd" in _w1406_line(NORM.render_lines(_w1406_view_h, 4.0), "WARP-9421")
       and [r["cost_usd"] for r in _w1406_view_h["rows"] if r["spec"] == "WARP-9421"] == [12.37]
       and [r["cost_usd"] for r in _w1406_view_h["rows"] if r["spec"] == "WARP-9423"] == [7.5]
       and _w1406_h_figs(0.5, True) == _W1406_H_FIGS_050
       and "NOT in tokens" in _w1406_line(NORM.render_lines(_w1406_view_h, 0.5), "WARP-9423")
       and NORM.render_lines(_w1406_view_h, 4.0)[0] == NORM.render_lines(_w1406_view_h)[0]
       and NORM.render_lines(_w1406_view_h, 4.0)[-1] == NORM.render_lines(_w1406_view_h)[-1]
       and len(NORM.render_lines(_w1406_view_h, 4.0)) == len(NORM.render_lines(_w1406_view_h))
       == len(_W1406_H_IDS) + 2)

# ---------------------------------------------------------------------------------------
# FIXTURE Z: THE FOURTH SHAPE THAT REACHES THE NO-POINT BRANCH, AND THE SANCTIONED WRITER MAKES IT.
#
# `spend.validate(spec, "harness_reported", tokens=0)` returns NO problems: zero is a number, it is
# not negative, and at least one figure was supplied. So `veldo spend record --tokens 0` is a legal
# call, and what it puts in the log comes back out of the corpus as `spend_recorded` TRUE with every
# figure ZERO. That row can name no field - a zero in the corpus spend block is the DEFAULT for a
# field nobody recorded, so which field carried the recorded zero is unknowable - and "no recorded
# spend" is FALSE about it, which is the message it used to get.
#
# THE EVENTS ARE BUILT THROUGH THE SHIPPED WRITER, at its own `emit` injection point, rather than
# hand-assembled here. A hand-written envelope is this suite's guess at the shape, and the whole claim
# of this fixture is that the shape is REACHABLE through the sanctioned path. The live event log's
# mtime_ns is asserted unchanged across it, because a fixture that recorded spend into this
# repository's own log would have changed the data every other assertion here reads.
# ---------------------------------------------------------------------------------------
_w1406_sspec = importlib.util.spec_from_file_location(
    "veldo_spend_1406", ROOT / ".veldo/spend.py")
_W1406_SPEND = importlib.util.module_from_spec(_w1406_sspec)
_w1406_sspec.loader.exec_module(_W1406_SPEND)

_w1406_espec = importlib.util.spec_from_file_location(
    "veldo_events_1406", ROOT / ".veldo/events.py")
_W1406_EV = importlib.util.module_from_spec(_w1406_espec)
_w1406_espec.loader.exec_module(_W1406_EV)

_W1406_Z_EVENTS = []


def _w1406_z_emit(etype, **kw):
    """The writer's own injection point, filled with the SHIPPED envelope builder and no file. So the
    fixture carries the bytes `veldo spend record` would have written, without writing them."""
    ev = _W1406_EV.make_event(etype, **kw)
    _W1406_Z_EVENTS.append(ev)
    return ev


_w1406_z_log_before = (ROOT / ".veldo/events.jsonl").stat().st_mtime_ns
_W1406_Z_PROBLEMS = _W1406_SPEND.validate("WARP-9425", "harness_reported", tokens=0)
_W1406_Z_REFUSED = ""
try:
    for _w1406_zs, _w1406_zt in (("WARP-9425", 0), ("WARP-9426", 7000)):
        _W1406_SPEND.record(_w1406_zs, "harness_reported", tokens=_w1406_zt, emit=_w1406_z_emit)
except ValueError as _w1406_ze:
    # CAUGHT SO THE DAY THE WRITER STOPS ACCEPTING THIS SHAPE IS A NAMED RED AND NOT A TRACEBACK
    # THAT TAKES THE WHOLE SELFTEST DOWN. The refusal is then asserted below as the string it is: if
    # `veldo spend record --tokens 0` ever becomes illegal, the fixture is unreachable and this
    # fragment must say so by name rather than aborting every suite after it.
    _W1406_Z_REFUSED = str(_w1406_ze)
_w1406_z_log_after = (ROOT / ".veldo/events.jsonl").stat().st_mtime_ns

with tempfile.TemporaryDirectory() as _w1406_dz:
    _w1406_seed_specs(_w1406_dz, [("WARP-9425", "standard"), ("WARP-9426", "standard")])
    _W1406_Z = CORP.build(specs_dir=_w1406_dz, events=_W1406_Z_EVENTS)
_w1406_peg_z = NORM.resolve_peg(_W1406_Z, _W1406_Z_EVENTS, _w1406_no_eras, CORP, _W1406_ISO)
_w1406_view_z = NORM.normalize(_W1406_Z, _w1406_peg_z, _W1406_Z_EVENTS, _w1406_no_eras,
                               CORP, _W1406_ISO)

expect("WARP-1406 AC1, THE FOURTH SHAPE, AND IT COMES OUT OF THE SANCTIONED WRITER: a spend record "
       "of tokens=0. `spend.validate(spec, 'harness_reported', tokens=0)` returns NO problems, so "
       "`veldo spend record --tokens 0` is legal, and the corpus reports that change with "
       "spend_recorded TRUE and every figure zero. It gets its OWN reason for two reasons that are "
       "both about the reader: naming a field is impossible, because a zero in the corpus spend block "
       "is the DEFAULT for a field nobody recorded and which field carried the recorded zero is "
       "unknowable; and 'no recorded spend' is FALSE about a change whose record is in the log, which "
       "sends that reader hunting for a missing record that is sitting right there. The row's reason "
       "is the ONLY thing the surface says about it, since the point is withheld either way, so a "
       "false reason is the whole output being wrong. Asserted through the shipped writer rather than "
       "over a hand-written envelope, because the claim is that the shape is REACHABLE",
       _W1406_Z_PROBLEMS == []
       and _W1406_Z_REFUSED == ""
       and [(r["spec"], r["spend"]["spend_recorded"], r["spend"]["tokens"]) for r in _W1406_Z]
       == [("WARP-9425", True, 0), ("WARP-9426", True, 7000)]
       and _w1406_points(_w1406_view_z) == {"WARP-9425": None, "WARP-9426": 1.0}
       and "every recorded figure is zero" in _w1406_reason(_w1406_view_z, "WARP-9425")
       and "no recorded spend" not in _w1406_reason(_w1406_view_z, "WARP-9425")
       and NORM.spend_fields_recorded(
           [r for r in _W1406_Z if r["spec"] == "WARP-9425"][0]["spend"]) == [])

expect("WARP-1406 AC1 NEGATIVE CONTROL FOR THE FOURTH REASON: the four shapes that reach the no-point "
       "branch produce FOUR DISTINCT reasons, asserted as a set of four across three fixtures, so the "
       "new branch did not swallow the nothing-recorded fact it sits beside - THAT row still says 'no "
       "recorded spend' and it is the only one that does. The recorded zero keeps its raw column and "
       "its recorded flag on the view, so the fact is REFUSED and not hidden. The SAME predicate "
       "governs the peg, which derives to the 7000-token change over a sample of ONE rather than "
       "pulling the recorded zero into the median. And the live event log's mtime_ns is unchanged "
       "across building a fixture through the real spend writer, so this suite measured the writer "
       "without recording anything into this repository",
       len({_w1406_reason(_w1406_view_a, "WARP-9416"),
            _w1406_reason(_w1406_view_h, "WARP-9423"),
            _w1406_reason(_w1406_view_h, "WARP-9424"),
            _w1406_reason(_w1406_view_z, "WARP-9425")}) == 4
       and "no recorded spend" in _w1406_reason(_w1406_view_a, "WARP-9416")
       and [(r["spec"], r["tokens"], r["spend_recorded"]) for r in _w1406_view_z["rows"]]
       == [("WARP-9425", 0, True), ("WARP-9426", 7000, True)]
       and _w1406_peg_z["spec"] == "WARP-9426" and _w1406_peg_z["tokens"] == 7000
       and _w1406_peg_z["sample"] == 1
       and _w1406_z_log_after == _w1406_z_log_before)

expect("WARP-1406 AC1 NEGATIVE CONTROL: a record whose spend was NEVER RECORDED gets NO POINT AT "
       "ALL and a reason that says why, so the row generator is not simply a function that always "
       "emits a number. This is WARP-1401's finding carried into the display layer: a confident "
       "zero and an unmeasured change look identical once a zero is printed, and this repository's "
       "spend coverage is 0 percent, so that row is the COMMON case and not the exotic one",
       _w1406_points(_w1406_view_a).get("WARP-9416") is None
       and "confident zero" in _w1406_reason(_w1406_view_a, "WARP-9416")
       and _w1406_view_a["summary"]["unpointed"] == 1
       and _w1406_view_a["summary"]["pointed"] == 6)

expect("WARP-1406 AC1: the rendered display carries the point FIRST and the raw tokens beside it, "
       "and a dollar column appears ONLY when a price is supplied. Driven through render_lines "
       "rather than described, because the display unit decision (D2) is only real in what a "
       "reader actually sees",
       "1.000 pt" in _w1406_line(NORM.render_lines(_w1406_view_a), "WARP-9413")
       and "3000 tok" in _w1406_line(NORM.render_lines(_w1406_view_a), "WARP-9413")
       and _w1406_line(NORM.render_lines(_w1406_view_a), "WARP-9413").index(" pt")
       < _w1406_line(NORM.render_lines(_w1406_view_a), "WARP-9413").index(" tok")
       and "usd" not in "".join(NORM.render_lines(_w1406_view_a))
       and "usd" in "".join(NORM.render_lines(_w1406_view_a, 0.5)))

# ---------------------------------------------------------------------------------------
# AC2. THE PEG IS A CORPUS STATISTIC THAT NAMES THE CHANGE IT IS PEGGED TO (D1).
# ---------------------------------------------------------------------------------------
expect("WARP-1406 AC2: the derived peg is the MEDIAN standard-risk shipped change carrying "
       "recorded token spend, and it NAMES that change (D1: a corpus statistic, never a "
       "hand-picked favourite). Over the five seeded standard-risk changes the peg is WARP-9413 at "
       "3000 tokens with a sample of 5, and the HIGH-risk change at 9000 tokens is excluded, which "
       "is what keeps a peg from drifting every time an unusually risky change ships",
       _w1406_peg_a["pegged"] is True
       and _w1406_peg_a["basis"] == NORM.PEG_DERIVED
       and _w1406_peg_a["spec"] == "WARP-9413"
       and _w1406_peg_a["tokens"] == 3000
       and _w1406_peg_a["sample"] == 5
       and _w1406_peg_a["risk"] == "standard")

# The median is shown to MOVE. Without this the assertion above would pass on an implementation
# that returned the middle ELEMENT OF THE INPUT ORDER, or the first candidate, or the last.
_W1406_BUMPED = json.loads(json.dumps(_W1406_A))
for _r in _W1406_BUMPED:
    if _r["spec"] == "WARP-9411":
        _r["spend"]["tokens"] = 9999
_w1406_bumped_events = [dict(e, tokens=9999) if e["spec_id"] == "WARP-9411" else e
                        for e in _w1406_a_events]
_w1406_peg_bumped = NORM.resolve_peg(_W1406_BUMPED, _w1406_bumped_events, _w1406_no_eras,
                                     CORP, _W1406_ISO)
expect("WARP-1406 AC2 TEETH: moving ONE change's recorded tokens MOVES THE PEG, from WARP-9413 at "
       "3000 to WARP-9414 at 4000. Without this leg the assertion above would pass unchanged on an "
       "implementation that returned the middle element of the INPUT ORDER, or the first candidate, "
       "or the last, none of which is a median. The corpus is deep-copied for this, so the "
       "unmutated fixture every later assertion uses is provably untouched",
       _w1406_peg_bumped["spec"] == "WARP-9414" and _w1406_peg_bumped["tokens"] == 4000
       and _w1406_peg_a["spec"] == "WARP-9413" and _w1406_peg_a["tokens"] == 3000)

# The EVEN sample, where the arithmetic middle is a change nobody made.
_W1406_EVEN = [_r for _r in _W1406_A if _r["spec"] != "WARP-9415"]
_w1406_peg_even = NORM.resolve_peg(_W1406_EVEN, _w1406_a_events, _w1406_no_eras, CORP, _W1406_ISO)
expect("WARP-1406 AC2: on an EVEN sample the peg is the LOWER MEDIAN, an OBSERVED change, and not "
       "the arithmetic middle of two of them. Over 1000, 2000, 3000 and 4000 tokens the peg is "
       "WARP-9412 at 2000 and explicitly NOT 2500, because a planner told the reference change is "
       "2500 tokens has been handed a change that nobody ever made and cannot go and read",
       _w1406_peg_even["spec"] == "WARP-9412" and _w1406_peg_even["tokens"] == 2000
       and _w1406_peg_even["tokens"] != 2500 and _w1406_peg_even["sample"] == 4)

# The unpeggable corpus: this repository's own situation, and it must stand down rather than invent.
# The one record left in it is the HIGH-risk change, which HAS recorded spend and is therefore not
# excluded for want of data - it is excluded from the PEG, which is the case worth testing.
_W1406_UNPEGGABLE = [_r for _r in _W1406_A if _r["spec"] == "WARP-9417"]
_w1406_peg_none = NORM.resolve_peg(_W1406_UNPEGGABLE, _w1406_a_events, _w1406_no_eras,
                                   CORP, _W1406_ISO)
_w1406_view_none = NORM.normalize(_W1406_UNPEGGABLE, _w1406_peg_none, _w1406_a_events,
                                  _w1406_no_eras, CORP, _W1406_ISO)
expect("WARP-1406 AC2 NEGATIVE CONTROL: a corpus with NO usable candidate yields pegged FALSE with "
       "the reason stated, never a fabricated peg and never a peg of zero, and every row of the "
       "resulting view says it has no peg in force. This is the case this repository is actually "
       "in - 174 shipped specs, 0 with recorded spend - so the standing-down path is the one that "
       "runs here today, and a peg of zero would have divided every displayed number by it",
       _w1406_peg_none["pegged"] is False
       and _w1406_peg_none["tokens"] is None
       and "nothing to peg to" in _w1406_peg_none["reason"]
       and all(r["points"] is None and "no peg in force" in r["reason"]
               for r in _w1406_view_none["rows"])
       and _w1406_view_none["rows"] != []
       and "standing down" in NORM.render_lines(_w1406_view_none)[0])

# The DECLARED override (D1: the founder may replace the provisional statistic).
_W1406_DECLARED = {"schema": NORM.SCHEMA_PEG, "basis": NORM.PEG_DECLARED, "tokens": 2000,
                   "era": NORM.ERA_UNSTAMPED, "spec": "WARP-9412"}
_w1406_peg_decl = NORM.resolve_peg(_W1406_A, _w1406_a_events, _w1406_no_eras, CORP, _W1406_ISO,
                                   declared=_W1406_DECLARED)
_w1406_bad_msgs, _w1406_bad_report = _w1406_capture()
_w1406_peg_bad = NORM.resolve_peg(_W1406_A, _w1406_a_events, _w1406_no_eras, CORP, _W1406_ISO,
                                  declared=dict(_W1406_DECLARED, tokens=0),
                                  report=_w1406_bad_report)
expect("WARP-1406 AC2: a DECLARED peg replaces the derived statistic and the view SAYS which basis "
       "it used, and a MALFORMED declared peg is refused by name and does NOT silently fall back "
       "to the derivation. Falling back would substitute a different reference change for the one a "
       "human wrote down, so every number on the surface would stop meaning what its owner thinks "
       "it means while looking completely normal",
       _w1406_peg_decl["pegged"] is True and _w1406_peg_decl["basis"] == NORM.PEG_DECLARED
       and _w1406_peg_decl["tokens"] == 2000
       and _w1406_peg_bad["pegged"] is False
       and _w1406_peg_bad["basis"] == NORM.PEG_DECLARED
       and _w1406_peg_bad["tokens"] is None
       and any("tokens must be greater than zero" in m for m in _w1406_bad_msgs))

_w1406_era_msgs, _w1406_era_report = _w1406_capture()
_w1406_peg_unknown_era = NORM.resolve_peg(
    _W1406_A, _w1406_a_events, _w1406_no_eras, CORP, _W1406_ISO,
    declared=dict(_W1406_DECLARED, era="era-nobody-recorded"), report=_w1406_era_report)
expect("WARP-1406 AC2: a DECLARED PEG NAMING AN ERA THE LEDGER DOES NOT DECLARE is refused by name, "
       "and the message LISTS the eras that are declared. It is checked where the ledger is known "
       "rather than in the record validator, because a typo'd era name is otherwise accepted and "
       "then turns every row into a null for the wrong reason: named, but tracing a whole surface "
       "of missing numbers back to a spelling mistake is a bad afternoon. NEGATIVE CONTROL BESIDE "
       "IT: the same peg naming the era the ledger DOES declare is accepted",
       _w1406_peg_unknown_era["pegged"] is False
       and any("era-nobody-recorded" in m and "pre-ledger" in m for m in _w1406_era_msgs)
       and NORM.resolve_peg(_W1406_A, _w1406_a_events, _w1406_no_eras, CORP, _W1406_ISO,
                            declared=_W1406_DECLARED)["pegged"] is True)

expect("WARP-1406 AC2 NEGATIVE CONTROL: the WELL-FORMED declared peg validates CLEAN, so every "
       "refusal above is a rule firing rather than a validator that refuses whatever it is shown",
       NORM.validate_peg(_W1406_DECLARED) == []
       and NORM.validate_peg(dict(_W1406_DECLARED, era="")) != []
       and NORM.validate_peg(dict(_W1406_DECLARED, schema="veldo.something/v1")) != []
       and NORM.validate_peg(dict(_W1406_DECLARED, basis=NORM.PEG_DERIVED)) != [])

# ---------------------------------------------------------------------------------------
# AC3. THE NON-NEGOTIABLE PROPERTY: RE-PEGGING AND RE-PRICING TOUCH NO STORED ACTUAL.
# Driven over a real tree with a real event log FILE, so "touches nothing" is a fact about
# bytes and mtimes on disk and not a claim about a function's intentions.
# ---------------------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as _w1406_d3:
    _w1406_sd3 = Path(_w1406_d3) / "specs"
    _w1406_sd3.mkdir()
    _w1406_seed_specs(_w1406_sd3, [(sid, "standard") for sid, _t in _W1406_A_SPEND])
    _w1406_log = Path(_w1406_d3) / "events.jsonl"
    _w1406_log.write_text("".join(json.dumps(e, sort_keys=True) + "\n"
                                  for e in _w1406_a_events[:len(_W1406_A_SPEND)]))
    _w1406_read = NORM.read_events(_w1406_log)
    _w1406_c3 = CORP.build(specs_dir=_w1406_sd3, events=_w1406_read)

    # THE SNAPSHOT: the actuals, the log's bytes, the log's mtime, and every spec file's bytes.
    _w1406_before_corpus = json.dumps(_w1406_c3, sort_keys=True)
    _w1406_before_log = (_w1406_log.read_bytes(), _w1406_log.stat().st_mtime_ns)
    _w1406_before_specs = {p.name: p.read_bytes() for p in sorted(_w1406_sd3.glob("*.md"))}

    _w1406_peg_1 = NORM.resolve_peg(_w1406_c3, _w1406_read, _w1406_no_eras, CORP, _W1406_ISO)
    _w1406_v1 = NORM.normalize(_w1406_c3, _w1406_peg_1, _w1406_read, _w1406_no_eras,
                               CORP, _W1406_ISO)
    _w1406_lines_1 = NORM.render_lines(_w1406_v1)

    # RE-PEG: a different reference change, so every displayed point must move.
    _w1406_peg_2 = NORM.resolve_peg(_w1406_c3, _w1406_read, _w1406_no_eras, CORP, _W1406_ISO,
                                    declared=dict(_W1406_DECLARED, tokens=5000,
                                                  spec="WARP-9415"))
    _w1406_v2 = NORM.normalize(_w1406_c3, _w1406_peg_2, _w1406_read, _w1406_no_eras,
                               CORP, _W1406_ISO)
    _w1406_lines_2 = NORM.render_lines(_w1406_v2)

    # RE-PRICE: the same peg, a price added. The money moves; no point may.
    _w1406_lines_priced = NORM.render_lines(_w1406_v1, 0.75)
    _w1406_lines_priced_2 = NORM.render_lines(_w1406_v1, 1.50)

    # THE COMPARATOR'S OWN TOOTH: a deep copy of the actuals with ONE recorded token count moved by
    # one, so the comparison used below is shown to DETECT a change rather than being too coarse to
    # see one. It is a copy, so the fixture every later assertion reads is provably untouched.
    _w1406_tampered = json.loads(json.dumps(_w1406_c3))
    _w1406_tampered[0]["spend"]["tokens"] += 1

    _w1406_after_corpus = json.dumps(_w1406_c3, sort_keys=True)
    _w1406_after_log = (_w1406_log.read_bytes(), _w1406_log.stat().st_mtime_ns)
    _w1406_after_specs = {p.name: p.read_bytes() for p in sorted(_w1406_sd3.glob("*.md"))}

    expect("WARP-1406 AC3, THE PROPERTY THIS ITEM EXISTS FOR: RE-PEGGING RE-RENDERS AND CHANGES "
           "NOTHING UNDERNEATH. Two pegs and two prices are rendered over one seeded tree, and "
           "afterwards the actuals are BYTE-IDENTICAL (json.dumps sorted), the event log's BYTES "
           "AND mtime_ns are unchanged, and every seeded spec file's bytes are unchanged. The "
           "recorded number is the evidence, and evidence is not rewritten when the ruler changes",
           _w1406_after_corpus == _w1406_before_corpus
           and _w1406_after_log == _w1406_before_log
           and _w1406_after_specs == _w1406_before_specs)

    expect("WARP-1406 AC3 NEGATIVE CONTROL, THE COMPARATOR HAS TEETH: the same comparison is run "
           "against a DELIBERATELY TAMPERED copy of the actuals and it REPORTS THE CHANGE. Without "
           "this leg the byte-identity assertion above would pass just as well on a comparison too "
           "coarse to see anything, which is the shape of a check that cannot fail",
           json.dumps(NORM.normalize(_w1406_c3, _w1406_peg_1, _w1406_read, _w1406_no_eras,
                                     CORP, _W1406_ISO)["rows"], sort_keys=True)
           == json.dumps(_w1406_v1["rows"], sort_keys=True)
           and json.dumps(_w1406_tampered, sort_keys=True) != _w1406_before_corpus
           and _w1406_tampered[0]["spend"]["tokens"] != _w1406_c3[0]["spend"]["tokens"])

    expect("WARP-1406 AC3: THE VIEWS ACTUALLY DIFFER, so the identity of the data underneath is a "
           "measurement rather than the identity of a run in which nothing happened. Re-pegging "
           "from 3000 to 5000 tokens moves EVERY point, and the two rendered displays differ line "
           "for line while carrying the same raw token column",
           _w1406_points(_w1406_v1) != _w1406_points(_w1406_v2)
           and all(_w1406_points(_w1406_v1)[s] != _w1406_points(_w1406_v2)[s]
                   for s, _t in _W1406_A_SPEND)
           and _w1406_lines_1 != _w1406_lines_2
           and [r["tokens"] for r in _w1406_v1["rows"]] == [r["tokens"] for r in _w1406_v2["rows"]])

    expect("WARP-1406 AC3: A PRICE CHANGE MOVES THE MONEY AND CANNOT MOVE A POINT, which is why a "
           "normalized planning number survives a price shift at all: a point is a ratio of tokens "
           "to tokens, so no price appears in it by construction. Two different prices are "
           "rendered over ONE view; the dollar column differs, the point column is identical, and "
           "the actuals are still byte-identical",
           _w1406_lines_priced != _w1406_lines_priced_2
           and "usd" in "".join(_w1406_lines_priced)
           and _w1406_pt_cells(_w1406_lines_priced) != []
           and _w1406_pt_cells(_w1406_lines_priced) == _w1406_pt_cells(_w1406_lines_priced_2)
           and _w1406_pt_cells(_w1406_lines_priced) == _w1406_pt_cells(_w1406_lines_1)
           and json.dumps(_w1406_c3, sort_keys=True) == _w1406_before_corpus)

# ---------------------------------------------------------------------------------------
# AC4. ERAS ARE RECORDED AND NEVER SILENTLY MIXED.
# ---------------------------------------------------------------------------------------
_W1406_SHIFT = {"schema": NORM.SCHEMA_SHIFT, "id": "era-second-model",
                "at": "2026-01-04T00:00:00Z", "model": "model-two",
                "previous_model": "model-one", "work_per_token": "increased",
                "note": "the new model does more work per token, so later token counts read smaller"}

with tempfile.TemporaryDirectory() as _w1406_d4:
    _w1406_eras_dir = Path(_w1406_d4) / "toe_eras"
    _w1406_written = NORM.record_shift(_W1406_SHIFT, _w1406_eras_dir, _W1406_ISO)
    _w1406_ledger_msgs, _w1406_ledger_report = _w1406_capture()
    _w1406_shifts, _w1406_ledger_errs = NORM.load_ledger(
        _w1406_eras_dir, V.parse_yamlish, _w1406_ledger_report, _W1406_ISO)
    # The SAME load with the parser taken from the module's own default resolution, so the one
    # parser is the one that actually reads a record on the shipped path too.
    _w1406_shifts_default, _ = NORM.load_ledger(
        _w1406_eras_dir, V.parse_yamlish, _w1406_ledger_report)

    expect("WARP-1406 AC4: A CAPABILITY SHIFT IS A RECORDED LEDGER ENTRY THAT ROUND TRIPS THROUGH "
           "THE ONE PARSER. record_shift writes it, validate.parse_yamlish (handed in, never a "
           "second parser) reads it back, and every field survives: when it took effect, which "
           "model, which model it replaced, and which direction the work per token moved. The "
           "ledger is what lets a number say which era it came from instead of being blended into "
           "one that no model ever produced",
           _w1406_written.name == "era-second-model.yaml"
           and _w1406_ledger_errs == 0 and _w1406_ledger_msgs == []
           and len(_w1406_shifts) == 1
           and _w1406_shifts[0]["model"] == "model-two"
           and _w1406_shifts[0]["previous_model"] == "model-one"
           and _w1406_shifts[0]["work_per_token"] == "increased"
           and _w1406_shifts[0]["at"] == "2026-01-04T00:00:00Z"
           and _w1406_shifts_default == _w1406_shifts)

    expect("WARP-1406 AC4: THE LEDGER IS APPEND ONLY. Recording the same era id twice is REFUSED "
           "by name rather than overwriting the entry a past view was rendered against; a shift "
           "recorded wrongly is corrected by recording a NEW entry. Asserted by attempting it",
           _w1406_raised(NORM.record_shift, _W1406_SHIFT, _w1406_eras_dir, _W1406_ISO)[0]
           and "append only" in _w1406_raised(
               NORM.record_shift, _W1406_SHIFT, _w1406_eras_dir, _W1406_ISO)[1])

    _w1406_two = NORM.eras(_w1406_shifts)
    _w1406_peg_e = NORM.resolve_peg(_W1406_A, _w1406_a_events, _w1406_two, CORP, _W1406_ISO)
    _w1406_view_e = NORM.normalize(_W1406_A, _w1406_peg_e, _w1406_a_events, _w1406_two,
                                   CORP, _W1406_ISO)

    expect("WARP-1406 AC4: WITH TWO ERAS DECLARED, THE PEG LANDS IN THE LATEST ERA THAT HAS "
           "CANDIDATES and rows measured in the OTHER era get NO POINT AT ALL, with the reason "
           "naming BOTH eras. A model that does more work per token makes the two token counts "
           "different units, so blending them would produce a total no model ever produced. The "
           "raw tokens are still on every one of those rows, and the era ledger is reported beside "
           "the view, so nothing is hidden - it is refused",
           _w1406_peg_e["era"] == "era-second-model"
           and _w1406_peg_e["spec"] == "WARP-9414" and _w1406_peg_e["sample"] == 2
           and _w1406_points(_w1406_view_e)["WARP-9414"] == 1.0
           and _w1406_points(_w1406_view_e)["WARP-9415"] == 1.25
           and all(_w1406_points(_w1406_view_e)[s] is None
                   for s in ("WARP-9411", "WARP-9412", "WARP-9413"))
           and all("era 'pre-ledger'" in _w1406_reason(_w1406_view_e, s)
                   and "era 'era-second-model'" in _w1406_reason(_w1406_view_e, s)
                   for s in ("WARP-9411", "WARP-9412", "WARP-9413"))
           and [r["tokens"] for r in _w1406_view_e["rows"]]
           == [r["spend"]["tokens"] for r in _W1406_A]
           and _w1406_view_e["summary"]["eras_declared"] == ["pre-ledger", "era-second-model"])

    expect("WARP-1406 AC4 NEGATIVE CONTROL: with ONE era - the same corpus, the same events, an "
           "EMPTY ledger - those same three rows all get points. So the withheld point above is the "
           "era rule firing, and not a function that refuses whatever it is shown. Both views are "
           "built from identical actuals, which is the same property AC3 asserts, observed from the "
           "other side",
           all(_w1406_points(_w1406_view_a)[s] is not None
               for s in ("WARP-9411", "WARP-9412", "WARP-9413"))
           and _w1406_view_a["summary"]["pointed"] == 6
           and _w1406_view_e["summary"]["pointed"] == 3)

expect("WARP-1406: THE SUMMARY ROLL-UP IS ASSERTED AS ONE WHOLE-DICT EQUALITY, over three fixtures, "
       "and the PRINTED bottom line is asserted with it. This is the line a planner sizes and budgets "
       "work with, and it was the one part of the module no assertion touched: probing single keys "
       "left points_total, tokens_total and eras_present free, so all three could be replaced with "
       "garbage while this suite stayed green. A whole-dict equality also reds when a key is silently "
       "ADDED, which per-key probing cannot see. Both units are present in every one: a normalized "
       "total with no raw total underneath is a number nobody can audit, and the token-less rows are "
       "counted as UNPOINTED rather than diluting the pointed denominator",
       _w1406_view_a["summary"] == {"rows": 7, "pointed": 6, "unpointed": 1, "points_total": 8.0,
                                    "tokens_by_era": {"pre-ledger": 24000}, "tokens_unplaced": 0,
                                    "tokens_total": 24000, "eras_present": ["pre-ledger"],
                                    "eras_declared": ["pre-ledger"]}
       and _w1406_view_h["summary"] == {"rows": 4, "pointed": 2, "unpointed": 2,
                                        "points_total": 3.178,
                                        "tokens_by_era": {"pre-ledger": 3178},
                                        "tokens_unplaced": 0, "tokens_total": 3178,
                                        "eras_present": ["pre-ledger"],
                                        "eras_declared": ["pre-ledger"]}
       and _w1406_view_e["summary"] == {"rows": 7, "pointed": 3, "unpointed": 4,
                                        "points_total": 4.5,
                                        "tokens_by_era": {"era-second-model": 18000,
                                                          "pre-ledger": 6000},
                                        "tokens_unplaced": 0, "tokens_total": None,
                                        "eras_present": ["era-second-model", "pre-ledger"],
                                        "eras_declared": ["pre-ledger", "era-second-model"]}
       and NORM.render_lines(_w1406_view_a)[-1]
       == ("total: 8.0 pt over 6 change(s), 24000 raw tokens, 1 row(s) with no point, "
           "eras ['pre-ledger']")
       and NORM.render_lines(_w1406_view_h)[-1]
       == ("total: 3.178 pt over 2 change(s), 3178 raw tokens, 2 row(s) with no point, "
           "eras ['pre-ledger']"))

expect("WARP-1406 AC4: THE RAW-TOKEN ROLL-UP REFUSES THE BLEND THE POINTS REFUSE, AND THE PRINTED "
       "BOTTOM LINE SAYS SO. `tokens_total` used to sum the raw tokens of every row whatever era it "
       "was measured in, so the two-era view above reported 24000 raw tokens beside the list of eras "
       "present with no qualification: two models' tokens added into one number, which is this "
       "module's own definition of a number no model ever produced, sitting one column from a points "
       "total that had refused to do exactly that. The whole-dict equality PINNED that blend, so it "
       "was the value the suite required. Now the raw tokens are reported PER ERA, `tokens_total` is "
       "None whenever they span more than one, and the bottom line names the refusal the way every "
       "refused row names its own. THE PER-ERA FIGURES ARE ASSERTED AGAINST THE CORPUS ITSELF rather "
       "than to literals alone: 6000 in pre-ledger and 18000 in era-second-model, summing to the "
       "24000 that is no longer presented as one number",
       _w1406_view_e["summary"]["tokens_total"] is None
       and _w1406_view_e["summary"]["tokens_by_era"] == {"era-second-model": 18000,
                                                         "pre-ledger": 6000}
       and sum(_w1406_view_e["summary"]["tokens_by_era"].values())
       + _w1406_view_e["summary"]["tokens_unplaced"]
       == sum(r["spend"]["tokens"] for r in _W1406_A)
       and NORM.render_lines(_w1406_view_e)[-1]
       == ("total: 4.5 pt over 3 change(s), raw tokens NOT totalled (18000 in era-second-model, "
           "6000 in pre-ledger, 0 in no readable era): tokens measured either side of a capability "
           "shift are different units and this module does not blend them, 4 row(s) with no point, "
           "eras ['era-second-model', 'pre-ledger']")
       and "24000" not in NORM.render_lines(_w1406_view_e)[-1])

expect("WARP-1406 AC4 NEGATIVE CONTROL FOR THE PER-ERA ROLL-UP: a ONE-ERA view still reports ONE raw "
       "total, in the same words it always did, so the refusal above is the era rule firing and not a "
       "roll-up that has stopped totalling anything. The same rows, the same actuals, an empty "
       "ledger: 24000 raw tokens, printed as one figure, with `tokens_by_era` carrying that one era "
       "and nothing outside it",
       _w1406_view_a["summary"]["tokens_total"] == 24000
       and list(_w1406_view_a["summary"]["tokens_by_era"]) == ["pre-ledger"]
       and "24000 raw tokens" in NORM.render_lines(_w1406_view_a)[-1]
       and "NOT totalled" not in NORM.render_lines(_w1406_view_a)[-1])

# A change whose OWN spend straddles a shift, and a change whose spend carries no readable
# timestamp: two different facts, each reported by name rather than folded into one silence.
_w1406_straddle_events = _w1406_a_events + [
    _w1406_ev("WARP-9418", 700, "2026-01-02T00:00:00Z"),
    _w1406_ev("WARP-9418", 800, "2026-01-05T00:00:00Z"),
    {"schema": "veldo.event/v1", "type": "spec.shipped", "spec_id": "WARP-9419", "tokens": 600},
]
with tempfile.TemporaryDirectory() as _w1406_d5:
    _w1406_seed_specs(_w1406_d5, [(sid, "standard") for sid, _t in _W1406_A_SPEND]
                      + [("WARP-9418", "standard"), ("WARP-9419", "standard")])
    _W1406_C5 = CORP.build(specs_dir=_w1406_d5, events=_w1406_straddle_events)

_w1406_two_eras = NORM.eras([_W1406_SHIFT])
_w1406_peg_5 = NORM.resolve_peg(_W1406_C5, _w1406_straddle_events, _w1406_two_eras,
                                CORP, _W1406_ISO)
_w1406_view_5 = NORM.normalize(_W1406_C5, _w1406_peg_5, _w1406_straddle_events,
                               _w1406_two_eras, CORP, _W1406_ISO)
expect("WARP-1406 AC4: A CHANGE WHOSE OWN SPEND STRADDLES A CAPABILITY SHIFT GETS NO ERA AND NO "
       "POINT, and the reason says it SPANS eras. Its total is already a mixture of two units "
       "before any display touches it, so normalizing it would launder the mixture into a "
       "confident number. Separately, spend carrying NO READABLE UTC TIMESTAMP is reported as an "
       "UNKNOWN era rather than being assumed into the current one - three distinct facts (nothing "
       "recorded, unreadable, spans a shift), three distinct messages",
       _w1406_points(_w1406_view_5)["WARP-9418"] is None
       and "spans 2 eras" in _w1406_reason(_w1406_view_5, "WARP-9418")
       and _w1406_points(_w1406_view_5)["WARP-9419"] is None
       and "no readable UTC timestamp" in _w1406_reason(_w1406_view_5, "WARP-9419")
       and _w1406_reason(_w1406_view_5, "WARP-9418") != _w1406_reason(_w1406_view_5, "WARP-9419")
       and _w1406_points(_w1406_view_5)["WARP-9415"] is not None)

expect("WARP-1406 AC4 NEGATIVE CONTROL: the straddling change and the timestamp-less change both "
       "DO have recorded spend and their raw tokens are present and correct on the view, so the "
       "withheld points above are the era rules firing rather than the corpus having nothing to "
       "show. 700 plus 800 tokens for the straddler, 600 for the other",
       [(r["spec"], r["tokens"], r["spend_recorded"]) for r in _w1406_view_5["rows"]
        if r["spec"] in ("WARP-9418", "WARP-9419")]
       == [("WARP-9418", 1500, True), ("WARP-9419", 600, True)])

# ---------------------------------------------------------------------------------------
# FIXTURE N: THE ERA OF A TOKEN TOTAL IS DECIDED BY TOKEN EVENTS, AND ONLY BY THOSE.
#
# WARP-9441's token spend sits wholly inside era-second-model, and thirty HUMAN MINUTES for the same
# change sit on the pre-ledger side of the shift. WARP-9442 is the same change with no minutes at
# all. The era path used to select events with the corpus's `spend_recorded` flag - true for a dollar
# cost or human minutes alone, which is the permissive flag `recorded_tokens` exists to refuse on the
# point path - so WARP-9441 lost its point and its row said its TOKEN total was "itself a mixture of
# units" because of minutes that are not denominated in tokens at all. Reachable through the
# sanctioned writer, whose --tokens, --cost-usd and --human-minutes flags are independent.
# ---------------------------------------------------------------------------------------
_W1406_N_EVENTS = [
    _w1406_ev("WARP-9441", 4000, "2026-01-05T00:00:00Z"),
    _w1406_ev("WARP-9441", None, "2026-01-02T00:00:00Z", human_minutes=30),
    _w1406_ev("WARP-9442", 4000, "2026-01-06T00:00:00Z"),
]
with tempfile.TemporaryDirectory() as _w1406_dn:
    _w1406_seed_specs(_w1406_dn, [("WARP-9441", "standard"), ("WARP-9442", "standard")])
    _W1406_N = CORP.build(specs_dir=_w1406_dn, events=_W1406_N_EVENTS)
_w1406_peg_n = NORM.resolve_peg(_W1406_N, _W1406_N_EVENTS, _w1406_two_eras, CORP, _W1406_ISO)
_w1406_view_n = NORM.normalize(_W1406_N, _w1406_peg_n, _W1406_N_EVENTS, _w1406_two_eras,
                               CORP, _W1406_ISO)
_w1406_note_n = ([r["note"] for r in _w1406_view_n["rows"] if r["spec"] == "WARP-9441"]
                 or [None])[0]

expect("WARP-1406 AC4: A NON-TOKEN SPEND EVENT DOES NOT DECIDE THE ERA OF A TOKEN MEASUREMENT, AND "
       "THE FACT IS NOT DELETED EITHER - IT IS A NOTE. WARP-9441's 4000 tokens were all measured "
       "inside era-second-model and its thirty human minutes sit on the other side of the shift: it "
       "keeps its point at 1.000, its era is era-second-model, and its row carries a note saying "
       "where the non-token figures sit and that they were not allowed to decide the era. Before "
       "this, the era path selected events by the corpus's `spend_recorded` flag - the permissive "
       "flag `recorded_tokens` exists to refuse on the point path, two spellings of one predicate on "
       "a second path - so the row lost its point and said its token total was 'a mixture of units' "
       "about minutes that are not tokens at all. The reason it printed was FALSE, which is worse "
       "than the missing point: it is the only thing the surface says about the row",
       _w1406_points(_w1406_view_n)["WARP-9441"] == 1.0
       and [r["era"] for r in _w1406_view_n["rows"] if r["spec"] == "WARP-9441"]
       == ["era-second-model"]
       and "mixture of units" not in _w1406_reason(_w1406_view_n, "WARP-9441")
       and "human_minutes" not in _w1406_reason(_w1406_view_n, "WARP-9441")
       and _w1406_note_n is not None
       and "pre-ledger" in _w1406_note_n and "era-second-model" in _w1406_note_n
       and "note:" in _w1406_line(NORM.render_lines(_w1406_view_n), "WARP-9441")
       and _w1406_view_n["summary"]["points_total"] == 2.0)

expect("WARP-1406 AC4 NEGATIVE CONTROL FOR THE TOKEN-ERA RULE, AND IT IS THE ROW ABOVE'S TEETH: the "
       "note is NOT decoration every row gets - the same change with no non-token spend (WARP-9442) "
       "carries no note at all - and the straddle refusal is STILL LIVE when it is the TOKEN events "
       "that straddle, which is fixture C5's WARP-9418 with 700 tokens either side of the same "
       "shift. So the era rule was narrowed to the events that can answer the question and not "
       "switched off: one change keeps its point with a note, another loses it by name",
       [r["note"] for r in _w1406_view_n["rows"] if r["spec"] == "WARP-9442"] == [None]
       and "note:" not in _w1406_line(NORM.render_lines(_w1406_view_n), "WARP-9442")
       # AND THE NOTE IS ITS OWN READER RATHER THAN A THIRD ELEMENT OF era_of's RETURN, because
       # .veldo/toe_analogy.py takes era_of as a callable and unpacks (era, reason): measured, a
       # third element raised ValueError out of the gate's unit stage from WARP-1404's evidence
       # window. The arity is pinned here, in the item that owns the function, so the coupling is
       # asserted by the module that would break it and not only discovered by the whole gate.
       and len(NORM.era_of("WARP-9441", _W1406_N_EVENTS, _w1406_two_eras, CORP, _W1406_ISO)) == 2
       and NORM.era_note("WARP-9441", "era-second-model", _W1406_N_EVENTS, _w1406_two_eras,
                         CORP, _W1406_ISO) == _w1406_note_n
       and NORM.era_note("WARP-9441", None, _W1406_N_EVENTS, _w1406_two_eras,
                         CORP, _W1406_ISO) is None
       and _w1406_points(_w1406_view_5)["WARP-9418"] is None
       and "spans 2 eras" in _w1406_reason(_w1406_view_5, "WARP-9418")
       and [r["note"] for r in _w1406_view_5["rows"] if r["spec"] == "WARP-9418"] == [None])

# ---------------------------------------------------------------------------------------
# AC5. FAIL CLOSED BY NAME, AND ADOPTION SAFE.
# ---------------------------------------------------------------------------------------
_W1406_BAD_SHIFTS = [
    ("a record missing the model",
     {k: v for k, v in _W1406_SHIFT.items() if k != "model"}, "missing required field 'model'"),
    ("a record with the wrong schema", dict(_W1406_SHIFT, schema="veldo.event/v1"),
     "schema must be 'veldo.toe_capability_shift/v1'"),
    ("a timestamp with no UTC zone, which would turn a comparison into a crash",
     dict(_W1406_SHIFT, at="2026-01-04 00:00:00"), "at must be a UTC timestamp"),
    ("a timestamp that is not a timestamp", dict(_W1406_SHIFT, at="last tuesday"),
     "at must be a UTC timestamp"),
    ("a work_per_token outside the declared vocabulary",
     dict(_W1406_SHIFT, work_per_token="better"), "work_per_token must be one of"),
    ("an id that would escape the ledger directory", dict(_W1406_SHIFT, id="../../etc/passwd"),
     "not usable as a ledger file name"),
    ("a note carrying a newline the record format cannot round trip",
     dict(_W1406_SHIFT, note="one\ntwo"), "carries a newline"),
    ("a record that is not a map at all", ["not", "a", "map"], "must be a map of fields"),
]
_w1406_bad_results = [(_l, NORM.validate_shift(_r, _W1406_ISO), _w)
                      for _l, _r, _w in _W1406_BAD_SHIFTS]

expect("WARP-1406 AC5: EVERY MALFORMED CAPABILITY-SHIFT RECORD IS REFUSED WITH A MESSAGE THAT "
       "NAMES WHAT IS WRONG, over EIGHT hostile shapes: no model, the wrong schema, a timestamp "
       "with no UTC zone, a timestamp that is not one, a work_per_token outside the vocabulary, an "
       "id that would escape the ledger directory, a note carrying a newline the format cannot "
       "round trip, and a record that is not a map at all. A half-applied era is worse than none: "
       "it would swallow every actual on one side of an unreadable boundary while the view looked "
       "exactly like a working one. THE all() IS BOUND TO THE LENGTH OF ITS OWN LITERAL SOURCE, so "
       "an emptied shape list REDS this instead of passing over nothing",
       len(_w1406_bad_results) == len(_W1406_BAD_SHIFTS) == 8
       and all(problems and any(want in p for p in problems)
               for _l, problems, want in _w1406_bad_results))

expect("WARP-1406 AC5 NEGATIVE CONTROL: the WELL-FORMED shift record validates CLEAN, with zero "
       "problems, and each of the three OPTIONAL fields may be absent without a complaint. So the "
       "eight refusals above are eight rules firing and not a validator that refuses everything, "
       "which would pass every refusal assertion in this block and be worth nothing",
       NORM.validate_shift(_W1406_SHIFT, _W1406_ISO) == []
       and NORM.validate_shift({k: v for k, v in _W1406_SHIFT.items()
                                if k not in ("note", "previous_model")}, _W1406_ISO) == []
       and all(NORM.validate_shift(dict(_W1406_SHIFT, work_per_token=w), _W1406_ISO) == []
               for w in NORM.WORK_PER_TOKEN))

with tempfile.TemporaryDirectory() as _w1406_d6:
    # FOUR BAD NEIGHBOURS, ONE PER PATH INTO THE REFUSAL, and the fourth is the one that was missing.
    # A record outside the PARSER subset, a record that PARSES AND FAILS validate_shift, a DUPLICATE
    # era id, and two shifts claiming ONE INSTANT: each refused through the reporter, naming the file
    # or the id, and left OUT of the ledger while the good record still loads.
    #
    # WHY THE THIRD FILE EXISTS AND WHAT ITS ABSENCE COST. Until it did, the only bad neighbours here
    # were a parse error and a same-instant duplicate, so the `validate_shift` refusal INSIDE
    # load_ledger - the branch AC5's fail-closed claim is actually about - was never reached by any
    # fixture in this suite. MEASURED on the tree before this fixture landed: making load_ledger
    # ACCEPT every malformed record into the ledger and report nothing left the suite at 60 passed 0
    # failed; so did returning an EMPTY ledger on the first bad record, which is the half-applied
    # catastrophe this module's own docstring calls worse than none; so did removing the duplicate-id
    # refusal, because both existing bad records have distinct ids. Three mutations of one branch,
    # none of them visible. The shipped code was correct and nothing would have noticed it stopping.
    _w1406_led6 = Path(_w1406_d6) / "toe_eras"
    _w1406_led6.mkdir()
    (_w1406_led6 / "aa-broken.yaml").write_text("\tschema: tabbed\n")
    (_w1406_led6 / "bb-good.yaml").write_text(NORM.render_shift(_W1406_SHIFT))
    (_w1406_led6 / "cc-same-instant.yaml").write_text(
        NORM.render_shift(dict(_W1406_SHIFT, id="era-third-model")))
    # PARSES CLEANLY, FAILS validate_shift: `work_per_token: better` is outside the declared
    # vocabulary, and everything else about the record is well formed, so only the validator can
    # refuse it.
    (_w1406_led6 / "dd-parses-invalid.yaml").write_text(
        NORM.render_shift(dict(_W1406_SHIFT, id="era-bad-direction",
                               at="2026-01-08T00:00:00Z", work_per_token="better")))
    # A DUPLICATE ERA ID at a different instant, so it reaches the duplicate-id branch rather than
    # the same-instant one: two entries claiming one era boundary cannot both be it.
    (_w1406_led6 / "ee-duplicate-id.yaml").write_text(
        NORM.render_shift(dict(_W1406_SHIFT, at="2026-01-06T00:00:00Z")))
    # ONE INSTANT SPELLED THE OTHER WAY. `2026-01-04T00:00:00+00:00` is the same moment as the good
    # record's `2026-01-04T00:00:00Z`, and the same-instant check used to compare the timestamp
    # STRING, so both were accepted: `eras()` then emitted an interval half open on the right AT ITS
    # OWN LEFT EDGE, and the earlier era was declared, listed in eras_declared, reported in the view
    # and unreachable by any actual. The id sorts AFTER the good record's so the survivor is still the
    # good record and this row measures the refusal rather than a reshuffle.
    _W1406_OTHER_SPELLING_AT = "2026-01-04T00:00:00+00:00"
    (_w1406_led6 / "ff-same-instant-other-spelling.yaml").write_text(
        NORM.render_shift(dict(_W1406_SHIFT, id="era-zzz-restamped",
                               at=_W1406_OTHER_SPELLING_AT)))
    # A SECOND GOOD RECORD, so the ledger produces a CLOSED interval and the era-interval property
    # below has something to be true of: with one shift every interval is open at one end, and a
    # property asserted over an empty set of closed intervals is the shape this whole review is about.
    (_w1406_led6 / "gg-later-good.yaml").write_text(
        NORM.render_shift(dict(_W1406_SHIFT, id="era-later-model",
                               at="2026-01-10T00:00:00Z", previous_model="model-two")))
    _w1406_m6, _w1406_r6 = _w1406_capture()
    _w1406_shifts6, _w1406_errs6 = NORM.load_ledger(_w1406_led6, V.parse_yamlish, _w1406_r6,
                                                    _W1406_ISO)
    # WHAT THIS DIRECTORY PARSED AT ALL, read back from the fixture rather than from the loader, so
    # the row below cannot be satisfied by a loader that refuses everything it is shown.
    _w1406_parsed6 = [V.parse_yamlish(p.read_text())
                      for p in sorted(_w1406_led6.glob("*.yaml")) if p.name != "aa-broken.yaml"]

    expect("WARP-1406 AC5: A LEDGER DIRECTORY WITH BAD RECORDS FAILS CLOSED AND BY NAME, OVER ALL "
           "FOUR PATHS INTO THE REFUSAL. A record outside the parser subset is refused naming its "
           "FILE; a record that PARSES and fails validate_shift is refused naming the FIELD, which is "
           "the branch this criterion's whole fail-closed claim is about and the one no fixture "
           "reached until now; a DUPLICATE era id is refused because two entries cannot both be one "
           "boundary; and a second shift claiming the SAME INSTANT is refused naming both ids, "
           "because no actual at that instant would have one era. FOUR refusals, one per bad file, "
           "and the ledger comes back carrying exactly the ONE good record - so nothing is half "
           "applied, nothing is silently swallowed, and a bad neighbour does not take the ledger "
           "down. The count is bound to the fixture's own bad-file list, so a shape added here "
           "without its refusal reds this row",
           _w1406_errs6 == len(_w1406_m6) == 5
           and [s["id"] for s in _w1406_shifts6] == ["era-second-model", "era-later-model"]
           and any("aa-broken.yaml" in m and "outside the parser subset" in m for m in _w1406_m6)
           and any("dd-parses-invalid.yaml" in m and "work_per_token must be one of" in m
                   for m in _w1406_m6)
           and any("duplicate shift id" in m and "era-second-model" in m for m in _w1406_m6)
           and any("era-third-model" in m and "one era" in m for m in _w1406_m6)
           and any("era-zzz-restamped" in m and _W1406_OTHER_SPELLING_AT in m
                   and "one moment" in m for m in _w1406_m6))

    expect("WARP-1406 AC5 NEGATIVE CONTROL FOR THE FAIL-CLOSED BRANCH: the two records the loader "
           "refused through validate_shift and through the duplicate-id rule DID parse cleanly, read "
           "back through the same one parser straight from the fixture, so their refusal is the "
           "loader's own judgement and not the parser's. And the good record beside them is not just "
           "present in the ledger, it is BYTE-EQUAL to what record_shift wrote, so a loader that "
           "returned a truncated or defaulted record for the survivor would red here",
           len(_w1406_parsed6) == 6
           and all(isinstance(r, dict) and r.get("id") for r in _w1406_parsed6)
           and [NORM.validate_shift(r, _W1406_ISO) != [] for r in _w1406_parsed6
                if r.get("work_per_token") == "better"] == [True]
           and _w1406_shifts6[:1] == [V.parse_yamlish(
               (_w1406_led6 / "bb-good.yaml").read_text())])

    _w1406_eras6 = NORM.eras(_w1406_shifts6)
    _w1406_spans6 = [(e["era"], _W1406_ISO(e["from"]), _W1406_ISO(e["to"]))
                     for e in _w1406_eras6 if e["from"] and e["to"]]
    expect("WARP-1406 AC5: THE SAME-INSTANT REFUSAL IS DECIDED ON THE PARSED INSTANT, NOT ON THE "
           "TIMESTAMP STRING, SO ONE MOMENT SPELLED TWO WAYS IS STILL ONE BOUNDARY. "
           "`2026-01-04T00:00:00Z` and `2026-01-04T00:00:00+00:00` are the same instant, asserted "
           "here through the one timestamp reader rather than assumed, and keying the check on the "
           "text accepted BOTH with zero problems reported: `eras()` then emitted an interval half "
           "open on the right at its OWN LEFT EDGE, so an era was declared, listed in eras_declared "
           "and reported in the view while no actual could ever be in it - a whole era of numbers "
           "silently attributed to its successor. Asserted as the PROPERTY rather than as the one "
           "spelling: every era interval this ledger produces has its start strictly before its end, "
           "which no pair of records claiming one moment can satisfy",
           _W1406_ISO("2026-01-04T00:00:00Z") == _W1406_ISO(_W1406_OTHER_SPELLING_AT)
           and _w1406_spans6 != []
           and all(lo < hi for _era, lo, hi in _w1406_spans6)
           and NORM.era_at(_w1406_eras6, "2026-01-04T00:00:00Z", _W1406_ISO) == "era-second-model"
           and NORM.era_at(_w1406_eras6, "2026-01-03T23:59:59Z", _W1406_ISO) == NORM.ERA_UNSTAMPED
           and [e["era"] for e in _w1406_eras6]
           == [NORM.ERA_UNSTAMPED, "era-second-model", "era-later-model"])

with tempfile.TemporaryDirectory() as _w1406_d7:
    _w1406_m7, _w1406_r7 = _w1406_capture()
    _w1406_absent = NORM.load_ledger(Path(_w1406_d7) / "no_such_dir", V.parse_yamlish,
                                     _w1406_r7, _W1406_ISO)
    expect("WARP-1406 AC5 ADOPTION SAFE: with NO ledger directory the ledger is empty, the problem "
           "count is zero, and the reporter is NEVER CALLED - not one line printed, so a repository "
           "that records no capability shift is byte-identically unaffected and is not nagged about "
           "a file it never asked for. Asserted as an EMPTY message list rather than as a count, "
           "because a check that only counts problems cannot tell silence from a warning",
           _w1406_absent == ([], 0) and _w1406_m7 == []
           and NORM.eras([]) == [{"era": NORM.ERA_UNSTAMPED, "model": None, "from": None,
                                  "to": None, "work_per_token": None}])

# ---------------------------------------------------------------------------------------
# AC5, ADVISORY: NO GATE STAGE CONSULTS THIS MODULE.
#
# THE SUBJECT IS THE GATE'S OWN STAGES, DERIVED, AND THE PREVIOUS VERSION OF THIS ROW COULD NOT FAIL
# FOR THE DEFECT IT NAMES. It was `"toe_normalize" not in scripts/verify.sh`: a substring scan over
# ONE file's text, while the property is about the gate's STAGES. verify.sh does not name the modules
# `validate.py` loads, so a stage added inside `validate.run_all` is invisible to it. MEASURED on the
# tree before this row changed: a stage that loads this module by path, builds the view over the
# repository and calls fail() when no peg is in force took `.veldo/validate.py all` to exit 1 printing
# ".veldo/toe_normalize.py: the normalized planning view has no peg in force" - a gate reddened on a
# planning number, which is exactly what PLAN-0014 NG1 forbids and what this criterion exists to
# prevent - and this suite stayed at 60 passed, 0 failed.
#
# The fix shape is PLAN-0018 finding 63's, already driven for VELDO-0003's organ: the DOMAIN becomes
# the gate's own stages (validate.py, validate_checks.py, the organs validate.py loads, and the stage
# scripts verify.sh names), and the assertion is that none of THEM loads this module. That set is a
# DEFECT set by construction rather than a population - NG1 forbids every member of it and no
# legitimate change adds one - so requiring it empty cannot rot the day somebody uses the feature,
# which the ADDITIVE control at the end of this fragment measures from the other side.
#
# LOADS, BY AST, NOT MENTIONS: /veldo:init and scripts/publish.py legitimately NAME this module in
# order to ship it, and naming is not consulting. A stage this suite cannot READ or PARSE is NAMED in
# the same list rather than answered False, because a stage nobody could read is not a stage in which
# an absence was measured.
import ast as _w1406_ast  # noqa: E402 - the detector below; the fragment IS the module body

_W1406_LOADERS = ("spec_from_file_location", "_organ", "_load", "_sibling", "import_module")


def _w1406_names_norm(value):
    """True when this string constant names THIS module: a path to it, its filename, or an import
    alias ending in its stem. Basename STEM, so a directory of that name elsewhere in the argument
    does not decide it."""
    stem = value.replace("\\", "/").rsplit("/", 1)[-1]
    if stem.endswith(".py"):
        stem = stem[:-3]
    return stem == "toe_normalize" or stem.endswith("toe_normalize")


def _w1406_loads_norm_text(src):
    """Whether this SOURCE loads .veldo/toe_normalize.py, by AST: a call to one of the loader
    functions this repository uses, with a string ANYWHERE in its arguments naming the module -
    anywhere, because `ROOT / ".veldo" / "toe_normalize.py"` is a BinOp and the constant sits inside
    it, and a detector that only reads DIRECT arguments is blind to the spelling validate.py itself
    uses for every organ it loads (PLAN-0018 finding 63 measured exactly that)."""
    try:
        tree = _w1406_ast.parse(src)
    except SyntaxError as _e:
        return "UNPARSEABLE: %s" % _e
    for node in _w1406_ast.walk(tree):
        if not isinstance(node, _w1406_ast.Call):
            continue
        fname = (node.func.attr if isinstance(node.func, _w1406_ast.Attribute)
                 else getattr(node.func, "id", ""))
        if fname not in _W1406_LOADERS:
            continue
        for arg in list(node.args) + [kw.value for kw in node.keywords]:
            for sub in _w1406_ast.walk(arg):
                if isinstance(sub, _w1406_ast.Constant) and isinstance(sub.value, str) \
                        and _w1406_names_norm(sub.value):
                    return True
    return False


def _w1406_gate_stage_files():
    """The files a GATE RUN executes, derived from the gate's own two declarations rather than listed
    here: validate.py is the built-in stage set, the organs it loads by path are part of a gate run
    too, and verify.sh names the script stages. A stage added to either declaration is in this domain
    automatically, which is what makes the emptiness below a defect set rather than a snapshot."""
    out = {ROOT / ".veldo" / "validate.py", ROOT / ".veldo" / "validate_checks.py"}
    vsh = ROOT / "scripts" / "verify.sh"
    if vsh.is_file():
        text = vsh.read_text()
        for cand in sorted((ROOT / "scripts").glob("*.py")):
            if cand.name in text:
                out.add(cand)
    try:
        vtree = _w1406_ast.parse((ROOT / ".veldo" / "validate.py").read_text())
    except (OSError, SyntaxError):
        vtree = None
    if vtree is not None:
        for node in _w1406_ast.walk(vtree):
            if isinstance(node, _w1406_ast.Constant) and isinstance(node.value, str) \
                    and node.value.endswith(".py"):
                cand = ROOT / ".veldo" / Path(node.value).name
                if cand.is_file():
                    out.add(cand)
    return sorted(p for p in out if p.is_file())


def _w1406_gate_consumers_of(stage_files):
    """The gate stages that LOAD this module, each named, with any this suite could not read carried
    into the SAME list rather than dropped."""
    out = []
    for p in stage_files:
        if p.name == "toe_normalize.py":
            continue
        try:
            verdict = _w1406_loads_norm_text(p.read_text())
        except OSError as _e:
            verdict = "UNREADABLE: %s" % _e
        if verdict is True:
            out.append(p.relative_to(ROOT).as_posix())
        elif verdict is not False:
            out.append("%s: %s" % (p.relative_to(ROOT).as_posix(), verdict))
    return sorted(out)


_w1406_stage_files = _w1406_gate_stage_files()
_w1406_gate_consumers = _w1406_gate_consumers_of(_w1406_stage_files)
_W1406_GATE_SPELLING = ('def run_all():\n'
                        '    _s = importlib.util.spec_from_file_location(\n'
                        '        "veldo_toe_norm_gate", ROOT / ".veldo" / "toe_normalize.py")\n')
_W1406_LITERAL_SPELLING = 'def _p():\n    return _load("norm", ".veldo/toe_normalize.py")\n'
_W1406_OTHER_SPELLING = 'def _p():\n    return _load("corp", ".veldo/toe_corpus.py")\n'

expect("WARP-1406 AC5: NO GATE STAGE CONSULTS THIS MODULE, and the SUBJECT is the gate's own stages "
       "rather than one file's text. Normalization is advisory by construction (PLAN-0014 NG1: "
       "nothing in that plan gates, blocks or refuses work on an estimate), and a display layer that "
       "could redden a build would make a planning convenience into a blocker on real work. This row "
       "used to be `'toe_normalize' not in scripts/verify.sh`, which cannot fail for the defect it "
       "names: verify.sh never names the modules validate.py loads, and a real stage added to "
       "validate.run_all took `.veldo/validate.py all` to exit 1 on a planning number while this "
       "suite stayed green. The domain is now DERIVED from validate.py, validate_checks.py, the "
       "organs validate.py loads by path, and the stage scripts verify.sh names, so a stage added to "
       "either declaration is covered without editing this row, and the set is a DEFECT set NG1 "
       "forbids every member of rather than a population a legitimate use joins (%d stage(s) read, "
       "consumers: %s)" % (len(_w1406_stage_files), _w1406_gate_consumers),
       bool(_w1406_stage_files) and _w1406_gate_consumers == []
       and (ROOT / ".veldo" / "validate.py") in set(_w1406_stage_files)
       and (ROOT / "scripts" / "selftest.py") in set(_w1406_stage_files))

expect("WARP-1406 AC5 NEGATIVE CONTROL, AND IT IS THE ROW ABOVE'S REACH: the detector FIRES on both "
       "spellings a gate stage could use - a literal \".veldo/toe_normalize.py\" and the "
       "`ROOT / \".veldo\" / \"toe_normalize.py\"` form validate.py already uses for every organ it "
       "loads - and stays SILENT on a load of a different organ and on a mere MENTION of this one, "
       "since /veldo:init and scripts/publish.py both name the module in order to ship it and naming "
       "is not consulting. A stage it cannot parse is NAMED rather than answered False, and that "
       "state is driven here too. Without this leg the emptiness above would be an absence measured "
       "with an instrument nobody had shown could detect anything",
       _w1406_loads_norm_text(_W1406_LITERAL_SPELLING) is True
       and _w1406_loads_norm_text(_W1406_GATE_SPELLING) is True
       and _w1406_loads_norm_text(_W1406_OTHER_SPELLING) is False
       and _w1406_loads_norm_text('X = "engine/.veldo/toe_normalize.py"\n') is False
       and str(_w1406_loads_norm_text("def (:\n")).startswith("UNPARSEABLE"))

expect("WARP-1406: the module lands in BOTH engine homes byte-identically, so what /veldo:init "
       "lays down for an adopter is what this repository runs (PLAN-0014 C5). Asserted as a byte "
       "comparison, because a copy that has drifted is worse than a copy that is missing: the "
       "missing one is obvious and the drifted one ships a different answer",
       (ROOT / "engine/.veldo/toe_normalize.py").is_file()
       and (ROOT / ".veldo/toe_normalize.py").read_bytes()
       == (ROOT / "engine/.veldo/toe_normalize.py").read_bytes())


# ---------------------------------------------------------------------------------------
# THE REAL REPOSITORY, ONCE. The invariant asserted here is one that holds whether or not
# anybody ever records spend, so it cannot rot into a red the day somebody does.
# ---------------------------------------------------------------------------------------
_w1406_live_log = ROOT / ".veldo/events.jsonl"
_w1406_live_before = _w1406_live_log.stat().st_mtime_ns
_w1406_live = NORM.build_view(root=ROOT, report=_w1406_capture()[1])

# THE SAME LIVE CORPUS WITH A PEG FORCED IN. Today's live peg stands down for want of any recorded
# token spend, and a view with no peg gives every row a null for THAT reason, which would leave the
# invariant below unable to fail whatever this module did. Forcing a valid declared peg over the real
# corpus removes that excuse, and it is pegged against an EMPTY ledger so an era mismatch cannot be
# the reason either: the only thing left that can withhold a point is the token predicate.
_w1406_live_events = NORM.read_events(_w1406_live_log)
_w1406_live_corpus = CORP.build(specs_dir=ROOT / "specs", events=_w1406_live_events)
_w1406_live_forced = NORM.normalize(
    _w1406_live_corpus,
    NORM.resolve_peg(_w1406_live_corpus, _w1406_live_events, _w1406_no_eras, CORP, _W1406_ISO,
                     declared=dict(_W1406_DECLARED, tokens=1000, spec=None)),
    _w1406_live_events, _w1406_no_eras, CORP, _W1406_ISO)


def _w1406_measured_in_tokens(r):
    """The invariant's own predicate, spelled once: a point is only ever printed for a row whose
    RECORDED TOKEN count is a positive number. `spend_recorded` is not that test - it is true for a
    change costed only in dollars or only in human minutes - and the display divides tokens, so the
    flag is the wrong invariant to assert here."""
    return (r["spend_recorded"] and isinstance(r["tokens"], (int, float))
            and not isinstance(r["tokens"], bool) and r["tokens"] > 0)


expect("WARP-1406: OVER THIS REPOSITORY'S OWN CORPUS AND LOG, NO ROW EVER CARRIES A POINT WITHOUT A "
       "POSITIVE RECORDED TOKEN COUNT, and reading the view does not touch the log (mtime_ns "
       "unchanged). The invariant is the TOKEN count and not the spend_recorded flag, because the "
       "flag is true for a change costed only in dollars or only in minutes while the display "
       "divides tokens: asserting the flag here would have passed on the confident zero this item "
       "forbids. ASSERTED TWICE OVER THE REAL DATA, once through the shipped build_view and once "
       "with a valid peg FORCED IN, because today's live peg stands down for want of recorded token "
       "spend and a standing-down peg nulls every row for its own reason, which would make this leg "
       "unfalsifiable. Stated as an INVARIANT rather than as today's figure on purpose: WARP-1401 "
       "measured 0 percent spend coverage here, so today every row stands down with a reason, and "
       "the day an agent records its first spend this assertion must still hold rather than turning "
       "red for having been written as a snapshot",
       _w1406_live["rows"] != []
       and all(r["points"] is None or _w1406_measured_in_tokens(r) for r in _w1406_live["rows"])
       and all(r["points"] is not None or r["reason"] for r in _w1406_live["rows"])
       and _w1406_live_forced["peg"]["pegged"] is True
       and [r["spec"] for r in _w1406_live_forced["rows"]] == [r["spec"] for r in _w1406_live["rows"]]
       and all(r["points"] is None or _w1406_measured_in_tokens(r)
               for r in _w1406_live_forced["rows"])
       and all(r["points"] is not None or r["reason"] for r in _w1406_live_forced["rows"])
       and _w1406_live_log.stat().st_mtime_ns == _w1406_live_before
       and (not (ROOT / NORM.ERAS_DIR).is_dir()
            or NORM.load_ledger(ROOT / NORM.ERAS_DIR, V.parse_yamlish,
                                _w1406_capture()[1], _W1406_ISO)[1] == 0))

# ---------------------------------------------------------------------------------------
# A TREE THAT CARRIES THIS MODULE AND NOT ITS SIBLINGS, WHICH IS WHAT AN ADOPTER GETS TODAY.
#
# This module reads three siblings by path (toe_corpus.py, metrics.py, validate.py). A pack that
# ships this file into a tree laid down without them produced a raw traceback:
# `FileNotFoundError: .../.veldo/toe_corpus.py`, exit 1, with no sentence a reader could act on -
# PLAN-0018 finding 61's shape in a new module. Driven in a REAL TREE and through the real CLI
# rather than reasoned about, and built by copying the ENGINE copy of this module, which is the byte
# an adopter receives.
#
# THE TREE IS CONSTRUCTED HERE RATHER THAN SCAFFOLDED, AND THE EXCLUSION IS EXACTLY TWO FILES.
# Asserting which modules the installer lays down would pin live state the installer is about to
# change; a tree that carries every other organ and NOT the two this module reads its data through is
# a defect BY CONSTRUCTION and stays one however the installer's set grows. Every other .veldo module
# is copied rather than a discovered subset, because validate.py loads organs of its own at import
# time and a hand-listed closure would rot the day it gains one.
# ---------------------------------------------------------------------------------------
_W1406_ORPH_WITHHELD = ("toe_corpus.py", "metrics.py")
with tempfile.TemporaryDirectory() as _w1406_dorph:
    _w1406_orph = Path(_w1406_dorph) / ".veldo"
    _w1406_orph.mkdir()
    for _w1406_src in sorted((ROOT / ".veldo").glob("*.py")):
        if _w1406_src.name not in _W1406_ORPH_WITHHELD:
            (_w1406_orph / _w1406_src.name).write_bytes(_w1406_src.read_bytes())
    (_w1406_orph / "toe_normalize.py").write_bytes(
        (ROOT / "engine/.veldo/toe_normalize.py").read_bytes())
    (Path(_w1406_dorph) / "specs").mkdir()
    _w1406_orph_report = subprocess.run(
        [sys.executable, ".veldo/toe_normalize.py", "report"], cwd=_w1406_dorph,
        capture_output=True, text=True)
    _w1406_orph_write = subprocess.run(
        [sys.executable, ".veldo/toe_normalize.py", "record-shift", "--id", "era-x",
         "--at", "2026-01-04T00:00:00Z", "--model", "m", "--work-per-token", "increased"],
        cwd=_w1406_dorph, capture_output=True, text=True)

    expect("WARP-1406 AC5, ADOPTION SAFE THE OTHER WAY: IN A TREE THAT CARRIES THIS MODULE WITHOUT "
           "ITS SIBLING ORGANS, THE READ VERB NAMES THE ABSENT ORGAN AND STANDS DOWN INSTEAD OF "
           "RAISING. Measured through the real CLI in a real directory: `report` exits 0 and prints "
           "one line naming `.veldo/toe_corpus.py` and saying this is an incomplete install rather "
           "than a repository with nothing recorded, and no traceback and no FileNotFoundError reach "
           "the reader. Before this the same command exited 1 on a raw FileNotFoundError, which is "
           "what an adopter receives the moment the pack ships this file, and a reader cannot act on "
           "a traceback. A READER that cannot answer names the state; a WRITER refuses, and "
           "`record-shift` in that same tree exits 1 naming the organ it could not load, because "
           "nothing was appended and a zero exit there would claim a record that does not exist",
           len(_W1406_ORPH_WITHHELD) == 2
           and not (_w1406_orph / "toe_corpus.py").exists()
           and _w1406_orph_report.returncode == 0
           and "toe_corpus.py" in _w1406_orph_report.stdout
           and "standing down" in _w1406_orph_report.stdout
           and "incomplete install" in _w1406_orph_report.stdout
           and "Traceback" not in _w1406_orph_report.stderr
           and "FileNotFoundError" not in _w1406_orph_report.stderr
           and _w1406_orph_write.returncode == 1
           and "metrics.py" in _w1406_orph_write.stderr
           and "Traceback" not in _w1406_orph_write.stderr)

    expect("WARP-1406 AC5 NEGATIVE CONTROL FOR THE ABSENT-ORGAN STAND-DOWN: the same module in THIS "
           "repository, where every sibling is present, does NOT stand down - it builds the real view "
           "and prints a peg line - so the stand-down is an absent organ being named and not a module "
           "that has stopped answering. And the stand-down is reached only through absence: with the "
           "organs present, `OrganAbsent` is never raised, and `_sibling` returns a loaded module for "
           "each of the three",
           "standing down: this module reads the sibling organ" not in "".join(_w1406_live["lines"])
           and _w1406_live["lines"][0].startswith("peg:")
           and all(hasattr(NORM._sibling(_n, _r), "__name__") for _n, _r in
                   (("veldo_toe_corpus_probe", ".veldo/toe_corpus.py"),
                    ("veldo_metrics_probe", ".veldo/metrics.py"),
                    ("veldo_validate_probe", ".veldo/validate.py")))
           and _w1406_raised(NORM._sibling, "veldo_absent_probe", ".veldo/no_such_organ.py")[1]
           .startswith("OrganAbsent"))
