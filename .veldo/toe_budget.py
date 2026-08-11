#!/usr/bin/env python3
"""Budgets: the roll-up, the dollar range, and pacing (WARP-1408, W8 of PLAN-0014).

WHAT THIS IS. Three readings over records that already exist, and not one new store:

  1. THE ROLL-UP. A plan's Tokens of Effort range is the sum of its items' committed
     estimate ranges (veldo.estimate/v1, WARP-1402), and a program's is the sum of its
     plans'. Summing RANGES is not summing points, so the rule is declared and the
     validator recomputes through it: see THE ARITHMETIC below.
  2. THE DOLLAR RANGE. A token range converts to money at a DECLARED rate whose
     provenance is recorded (veldo.toe_token_price/v1). No rate means UNPRICED, which is
     a different fact from free, and this module never lets it read as zero.
  3. PACING. The range is held against what the plan has actually spent so far, and
     against whatever cap the plan declares, so a reader can see position rather than
     only totals.

ADVISORY, AND THAT IS A HARD BOUNDARY (PLAN-0014 NG1, D4). Nothing here gates, blocks,
deprioritizes, refuses or delays a unit of work. Every advisory verdict this module can
reach - over the declared cap, partial coverage, unpriced, no estimates at all - exits 0
and prints ADVISORY. The only non-zero exit is a record PRESENT ON DISK that cannot be
read, which is a refusal to REPORT and never a refusal of work; nothing in
scripts/verify.sh names this module, so no exit code of mine reaches the gate. If a cap
ever enforces anything, that is D4 and a separate spec with its own review.

WHAT DOES REACH THE GATE IS THIS MODULE'S SUITE FRAGMENT, under the REQUIRED CHECK_unit
slot, and that is the back door NG1 arrives through if nobody watches it: an assertion
pinning this repository's EMPTY estimate ledger, its absent price record or its
spend-free event stream would turn a required gate slot red the first time somebody
committed an estimate, declared a rate or recorded a token - a number from this item
stopping work. So the fragment asserts every empty-ledger SHAPE over FIXTURE trees, and
over this repository it asserts only that the readings TRACK the records on disk.

***

WHAT THIS IS NOT, AND THE DIVISION OF LABOUR WITH .veldo/budget.py, WHICH ALREADY EXISTS.

`.veldo/budget.py` holds a plan's HAND-DECLARED cap against RECORDED SPEND and ENFORCES
it: over the cap, it exits non-zero naming the overage. That is a different question from
this one and it is not re-asked here. This module holds a DERIVED RANGE (the sum of
committed estimates) against that same declared cap and that same recorded spend, and it
advises.

So the two never disagree about their shared inputs, because this module does not
recompute them. It REUSES budget.py for all three:

  budget.parse_budgets(fm)     what cap this plan declares (and its refusal when malformed)
  budget.plan_work_specs(fm)   which spec ids are this plan's work items
  budget.plan_spend(fm, evs)   what this plan has spent, through metrics.compute, the ONE
                               spend aggregation in this system

MEASURED, AND IT SHAPES THE ADOPTION PATH: `engine/.veldo` ships 83 modules and
`budget.py` is NOT one of them (measured 2026-08-10). This module's engine twin therefore
cannot make it a hard import, and it does not: `_budget()` returns None when the owner is
absent and every reading that needs it STANDS DOWN BY NAME rather than being recomputed
here under a second attribution rule. Substituting a different rule for the declared one
is how a planning number stops meaning what its owner thinks it means, so the standdown
says which file is missing. The gap is recorded with this item's delivery notes for W10.

***

THE ARITHMETIC, STATED BECAUSE A ROLL-UP RULE NOBODY CAN SEE IS A RULE NOBODY CAN CHECK.

v1 declares ONE rule, `sum_bounds`: the total's low is the sum of the item lows and the
total's high is the sum of the item highs. That is interval addition, and it is the only
rule that needs no assumption at all about how the item errors relate to each other.

WHAT IS DELIBERATELY REFUSED, by name, from a declared table (REFUSED_RULES):

  mean / midpoint      collapse a range to a point, and veldo.estimate/v1 has no field
                       for a point. NG6 is structural here, not advice.
  root_sum_square      quadrature narrows a total by assuming the item errors are
                       INDEPENDENT. Every range in this repository comes out of the same
                       estimator under the same declared prior, so their errors are
                       correlated by construction, and narrowing on an independence
                       nobody has measured is manufacturing confidence.
  pert                 (low + 4*mode + high)/6 is a point, and there is no `mode`.

THE PROPERTY THAT MAKES THE SUM SAFE TO READ, and the reason a wide range and a narrow
one cannot average into false confidence. Define a range's SPREAD as high/low. Under
sum_bounds the total's spread is sum(high)/sum(low), which is a weighted mediant of the
item spreads, so

    min(item spreads)  <=  total spread  <=  max(item spreads)

The total can therefore NEVER be tighter than the tightest item it contains. Adding a
wide item to a set of narrow ones moves the total TOWARD the wide one; it cannot pull the
total inside the narrow band. Both bounds of that sandwich are asserted in the suite over
a wide-plus-narrow pair, because a rule stated in a docstring is a rule nobody has run.

A PARTIAL SUM IS NOT A PLAN'S RANGE, and this is the honesty that matters most here. A
plan with ten items and three estimates has a range for THREE ITEMS, and printing that as
the plan's number understates it by however much the other seven cost. So coverage is
counted, `complete` is a field, the unestimated items are NAMED, and a plan with NO
estimates gets NO range at all: None, never 0. MEASURED 2026-08-10 over this repository:
PLAN-0014 has 10 work items and `.veldo/estimates/` did not exist, so every roll-up here
stood down and said so. That is a measurement carrying its date, not an invariant: the
suite asserts that coverage TRACKS the records on disk, never that there are none.

CALIBRATION TRAVELS WITH THE SUM. A total is `calibrated` only when EVERY contributing
estimate is (the weakest link governs a sum, because one uncalibrated item is enough to
make the total's error unmeasured). WARP-1401 measured 0 percent spend coverage in this
repository and WARP-1402 therefore produces `uncalibrated` records, so any total here is
uncalibrated money over an uncalibrated range, and the view says which.

***

THE RATE, AND WHY IT CARRIES ITS PROVENANCE.

`veldo.toe_token_price/v1` at `.veldo/toe_token_price.yaml`, optional, absent by default:

  schema: veldo.toe_token_price/v1
  usd_micros_per_1k_tokens: 3000     # integer micro-USD per 1000 tokens
  model: <the model identity this rate is for>
  source: <where the rate came from>
  observed_at: 2026-08-10
  note: <optional, one line>

MONEY IS INTEGER MICRO-USD, not a float. Two reasons, both mechanical. The front-matter
subset has no float, so a fractional rate written there would come back as a STRING and
be coerced by whoever read it next; and a dollar figure derived from an uncalibrated
token range has no business carrying binary rounding on top of the uncertainty it already
has. Integer micros are exact, identical on every machine, and convert to a displayed
dollar figure by integer division.

THE ROUNDING IS DIRECTIONAL, so it can only widen: the low bound FLOORS and the high
bound CEILS, in the conversion and again in the display. The displayed dollar interval
therefore CONTAINS the exact one. A rounding that narrowed a money range would be the
same false precision the token schema already refuses.

`source` and `observed_at` are REQUIRED. A rate is the one number in this whole chain
that comes from outside the repository entirely, so a rate with no stated provenance is a
number a later analysis will over-trust - the same reason `spend.py` requires a basis and
every estimate layer requires one. And `model` is required because a price is per model
(D5): the view reports which model the rate is for, and states plainly that the token
range it converts carries no model stamp of its own.

UNPRICED IS NOT ZERO. With no rate record the money block reads `priced: false` with the
reason, and every money field is None. A malformed rate record is REFUSED BY NAME and
does NOT fall back to a default rate, because silently substituting a guess for the
number a human wrote down is worse than having none.

***

PACING, AND THE ZERO THAT WOULD BE A LIE.

Pacing compares the range to `budget.plan_spend`. With nothing recorded, "0 percent of
the estimate consumed" reads as a measurement of being on track, when the truth is that
nobody has recorded anything. So `spend_recorded` is a field, and when it is false the
position is None with the reason. MEASURED 2026-08-10 over this repository: over a thousand
events, 0 tokens, 0 cost_usd, 0 human_minutes, and 0 correlations carrying spend at all, so
pacing here stood down on real data rather than on a fixture. The suite asserts that the
recorded flag EQUALS toe_corpus.spend_for recomputed over the same stream, so the first
recorded token moves the reading instead of reddening a required gate slot.

THE PACING SEAM, AND THE FAILURE MODE IT REFUSES. `.veldo/governor.py` paces workers
against rolling `Window(name, seconds, tokens)` budgets, and it returns ZERO WORKERS when
a window's budget is spent. So handing it a number derived from estimates is the one place
in this item where a number could stop work, and three rules keep that impossible:

  - `pacing_windows` emits the HIGH bound and never the low. The low bound of a range is
    its optimistic end, not a limit, and pacing against it would stall real work on the
    happy case.
  - With no range at all it emits NOTHING, with the reason. A zero-token window is the
    dangerous shape: `governor.Window` refuses a non-positive budget, so an empty
    estimate ledger would either crash the pacer or, if it did not, stall every worker.
  - It emits DATA (plain dicts), never a `Window`. This module does not import the
    governor, does not call it, and nothing in this repository wires the two together.
    Whether an advisory number is ever handed to an enforcing consumer is a decision for
    whoever wires it, made in the open, and it is D4.

***

ADOPTION SAFE AND WRITES NOTHING. There is no store, no emitter and no append here: every
function reads the arguments it is handed or the records that exist and returns a dict. No
records means every surface stands down silently and creates nothing. No clock is read
(dates come from the records), no subprocess is spawned, no socket is opened. One parser
(`validate.parse_yamlish`) and one failure reporter (`validate.fail`), both loaded lazily
by path the way every other organ here loads a sibling.
"""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

SCHEMA = "veldo.toe_budget/v1"
SCHEMA_PRICE = "veldo.toe_token_price/v1"
ROOT = Path(__file__).resolve().parent.parent

# Where a repository keeps its declared token price when it chooses to declare one. OPTIONAL:
# its absence is the adoption-safe path and reads as UNPRICED, never as zero.
PRICE_FILE = ".veldo/toe_token_price.yaml"

# THE UNIT THIS ROLL-UP CAN ADD. Raw tokens are the recorded ground truth (PLAN-0014 C2) and
# the only unit veldo.estimate/v1 commits a range in. Declared here as well so a record in
# some other unit is a NAMED refusal rather than a silent addition of unlike things.
UNIT_TOKENS = "tokens"

# HOW A SET OF RANGES BECOMES ONE RANGE. One rule in v1, recomputed by the reader rather than
# trusted, exactly as veldo.estimate/v1 recomputes a committed range from its layers.
SUM_BOUNDS = "sum_bounds"
ROLLUP_RULES = {
    SUM_BOUNDS: "interval addition: the total's low is the sum of the item lows and its high "
                "is the sum of the item highs. The only combination that assumes nothing at "
                "all about how the item errors relate to each other",
}

# WHAT IS REFUSED AND WHY, from a table, so the refusal teaches instead of only stopping. A
# rule named here is refused with its reason; a rule named nowhere is refused with the
# declared set. Both are refusals: this module never guesses which rule was meant.
REFUSED_RULES = {
    "mean": "an average of two ranges is a POINT, and veldo.estimate/v1 has no field for a "
            "point. False precision is refused structurally, not discouraged",
    "midpoint": "the middle of a range is a POINT; see mean",
    "root_sum_square": "quadrature narrows a total by assuming the item errors are "
                       "INDEPENDENT. Every range here comes from one estimator under one "
                       "declared prior, so the errors are correlated by construction and "
                       "narrowing on an unmeasured independence manufactures confidence",
    "pert": "(low + 4*mode + high)/6 is a POINT and there is no mode in this schema",
}

# The rate record's declared key set. Unknown keys are refused BY NAME rather than ignored,
# for the reason veldo.estimate/v1 gives: a schema that ignores what it does not recognise is
# a schema a later reader can be lied to through.
PRICE_REQUIRED = ("schema", "usd_micros_per_1k_tokens", "model", "source", "observed_at")
PRICE_OPTIONAL = ("note",)
PRICE_ORDER = PRICE_REQUIRED + PRICE_OPTIONAL

# Micro-USD per USD, and per 1000 tokens, named once so no line below spells a magic number.
MICROS_PER_USD = 1000000
MICROS_PER_CENT = 10000
TOKENS_PER_RATE_UNIT = 1000

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# THE ADVISORY MARKER every view carries. It is a field and not a docstring promise, so a
# consumer can assert it, and the suite asserts that no shape this module produces omits it.
ADVISORY = {
    "blocks": False,
    "note": "advisory only (PLAN-0014 NG1, D4): this view informs pacing and never gates, "
            "blocks, deprioritizes, refuses or delays a unit of work. Enforcement, if it "
            "ever happens, is a separate founder decision and a separate spec",
}

_MODS = {}


def _mod(rel, name, required=True):
    """One sibling organ of THIS engine, loaded by path and cached, the shape every module
    here uses. `required=False` returns None when the file is absent instead of raising,
    which is how an OPTIONAL owner (see `_budget`) stands down rather than crashing an
    engine tree that does not ship it."""
    key = (str(ROOT), rel)
    if key not in _MODS:
        path = ROOT / rel
        if not path.is_file():
            if required:
                raise ValueError("this engine has no %s, which this module needs" % rel)
            _MODS[key] = None
            return None
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MODS[key] = mod
    return _MODS[key]


def _validate():
    """The ONE front-matter parser and the ONE failure reporter."""
    return _mod(".veldo/validate.py", "veldo_validate_toe_budget")


def _estimate():
    """The estimate record's owner (WARP-1402): its schema, its validator and its reader.
    Every record this module sums is re-validated through THAT module, so the roll-up and the
    estimator can never disagree about what a valid record is."""
    return _mod(".veldo/estimate.py", "veldo_estimate_toe_budget")


def _corpus():
    """The actuals corpus (WARP-1401), for its ONE answer to "did this event carry spend".
    Reused rather than re-spelled, the same reason toe_normalize reuses it: the field set and
    the numeric test belong to the module that owns them."""
    return _mod(".veldo/toe_corpus.py", "veldo_toe_corpus_toe_budget")


def _budget():
    """The budget owner (.veldo/budget.py), or None when this engine does not ship it.

    OPTIONAL BY MEASUREMENT, not by preference: engine/.veldo ships 83 modules and this is
    not one of them, so a hard import here would make this module unimportable in the tree
    /veldo:init lays down. Every reading that needs it stands down BY NAME, and none of them
    is recomputed here: which correlations a plan's spend is attributed to, and what cap a
    plan declares, are that module's decisions."""
    return _mod(".veldo/budget.py", "veldo_budget_toe_budget", required=False)


# ---------------------------------------------------------------------------------------
# The rate: validation, reading, and the conversion.
# ---------------------------------------------------------------------------------------

def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _named(rec, key):
    v = rec.get(key)
    return isinstance(v, str) and v.strip() != ""


def validate_price(rec):
    """Every problem with a token-price record, as messages that NAME the field. Empty means
    usable.

    Fail closed, because the alternative is money that looks measured. A rate is the only
    number in this chain that comes from outside the repository, so its provenance
    (`source`, `observed_at`) and the model it applies to are REQUIRED, and an unknown key is
    refused rather than carried along."""
    if not isinstance(rec, dict):
        return ["a token-price record must be a mapping of fields, got %s" % type(rec).__name__]
    out = []
    unknown = sorted(set(rec) - set(PRICE_REQUIRED) - set(PRICE_OPTIONAL))
    if unknown:
        out.append("unknown key(s) %s: %s declares %s (required) and %s (optional), and an "
                   "unknown key is refused rather than ignored"
                   % (unknown, SCHEMA_PRICE, list(PRICE_REQUIRED), list(PRICE_OPTIONAL)))
    for k in PRICE_REQUIRED:
        if k not in rec:
            out.append("missing required field %r (a rate is the one number here that comes "
                       "from outside the repository, so it does not get to arrive without "
                       "its provenance)" % k)
    if "schema" in rec and rec.get("schema") != SCHEMA_PRICE:
        out.append("schema must be %r, got %r" % (SCHEMA_PRICE, rec.get("schema")))
    if "usd_micros_per_1k_tokens" in rec:
        v = rec["usd_micros_per_1k_tokens"]
        if not _is_int(v):
            out.append("usd_micros_per_1k_tokens must be an INTEGER number of micro-USD per "
                       "1000 tokens (the front-matter subset has no float, and money derived "
                       "from an uncalibrated range has no business carrying binary rounding "
                       "too), got %r" % (v,))
        elif v <= 0:
            out.append("usd_micros_per_1k_tokens must be greater than zero: a rate of zero "
                       "would price every range at nothing, which is exactly the confident "
                       "zero an unpriced range must never become, got %r" % (v,))
    if "model" in rec and not _named(rec, "model"):
        out.append("model must name the model identity this rate is for, because a price is "
                   "per model (PLAN-0014 D5), got %r" % (rec.get("model"),))
    if "source" in rec and not _named(rec, "source"):
        out.append("source must say where this rate came from: a number with no stated "
                   "provenance is one a later analysis will over-trust, got %r"
                   % (rec.get("source"),))
    if "observed_at" in rec and not (isinstance(rec["observed_at"], str)
                                     and DATE_RE.match(rec["observed_at"])):
        out.append("observed_at must be a YYYY-MM-DD date, so a reader can see how stale the "
                   "rate is, got %r" % (rec.get("observed_at"),))
    if "note" in rec and not _named(rec, "note"):
        out.append("note, when present, must be a non-empty single-line string, got %r"
                   % (rec.get("note"),))
    for k, v in sorted(rec.items()):
        if isinstance(v, str) and ("\n" in v or "\r" in v):
            out.append("field %r carries a newline, which the record format cannot round trip" % k)
    return out


def render_price(rec, parse=None):
    """One rate record as the front-matter subset, in a declared key order, so a written
    record and a hand-written one look the same in a diff.

    THE WRITER IS BOUND TO THE READER BY AN ACTUAL ROUND TRIP, not by a second copy of the
    parser's rules. Rendering a value the ONE parser would read back as something else (a
    string of digits, a bracketed value, anything with a newline) is refused HERE, by parsing
    the bytes and comparing, rather than by re-spelling a list of refusals that would then
    have to be kept in step with the parser forever."""
    problems = validate_price(rec)
    if problems:
        raise ValueError("refusing to render an invalid token-price record: "
                         + "; ".join(problems))
    text = "".join("%s: %s\n" % (k, rec[k]) for k in PRICE_ORDER if rec.get(k) is not None)
    parse = parse or _validate().parse_yamlish
    try:
        back = parse(text)
    except ValueError as e:
        raise ValueError("refusing to render this token-price record: the bytes are outside "
                         "the front-matter parser subset (%s)" % e)
    wanted = {k: rec[k] for k in PRICE_ORDER if rec.get(k) is not None}
    if back != wanted:
        raise ValueError("refusing to render this token-price record: it would not read back "
                         "as itself. wrote %r, the ONE parser returns %r" % (wanted, back))
    return text


def read_price(path=None, root=None, parse=None):
    """The declared rate, or None when the repository declares none (the adoption-safe path).

    A file that exists but cannot be read or is malformed raises ValueError NAMING the
    problems. It deliberately does not fall back to a default rate: substituting a guess for
    the number a human wrote down is how money stops meaning what its owner thinks it means,
    and it would turn a typo into a silently different bill."""
    p = Path(path) if path else (Path(root) if root else ROOT) / PRICE_FILE
    if not p.is_file():
        return None
    parse = parse or _validate().parse_yamlish
    try:
        rec = parse(p.read_text())
    except (ValueError, OSError) as e:
        raise ValueError("the token-price record at %s is outside the front-matter parser "
                         "subset: %s" % (p, e))
    problems = validate_price(rec)
    if problems:
        raise ValueError("refusing the token-price record at %s: %s" % (p, "; ".join(problems)))
    return rec


def price_from_args(micros, model, source, observed_at):
    """A rate supplied on the command line for a one-off display, validated exactly as hard
    as a committed one.

    THE PROVENANCE IS NOT OPTIONAL HERE EITHER. It would be easy to let a caller pass a bare
    number for a quick look, and that number would then appear beside a dollar figure with
    nothing saying where it came from. So the same four fields are required and the same
    validator refuses, which is what makes "you cannot get money out of this without saying
    where the rate came from" a property rather than a convention."""
    rec = {"schema": SCHEMA_PRICE, "usd_micros_per_1k_tokens": micros, "model": model,
           "source": source, "observed_at": observed_at}
    problems = validate_price(rec)
    if problems:
        raise ValueError("refusing an ad-hoc token price: " + "; ".join(problems))
    return rec


def usd_micros(tokens, rate_micros_per_1k, up=False):
    """Convert a token count to micro-USD in integer arithmetic.

    DIRECTIONAL ON PURPOSE: `up=False` floors and `up=True` ceils, so a range converted with
    floor on the low and ceil on the high yields a money interval that CONTAINS the exact
    one. Rounding is allowed to widen a range and never to narrow it, which is the same rule
    veldo.estimate/v1 applies to its own bounds."""
    n = tokens * rate_micros_per_1k
    if up:
        return -((-n) // TOKENS_PER_RATE_UNIT)
    return n // TOKENS_PER_RATE_UNIT


def render_usd(micros, up=False):
    """Micro-USD as a displayed dollar figure, truncated (or raised) to cents in integer
    arithmetic.

    THE DISPLAY ROUNDS THE SAME DIRECTION AS THE BOUND IT SHOWS, so the printed interval also
    contains the exact one. And a non-zero amount below a cent renders `<0.01` rather than
    `0.00`, because a cost printed as zero is the one output this module exists to prevent."""
    if micros is None:
        return "unpriced"
    neg = micros < 0
    m = -micros if neg else micros
    if up:
        cents_total = -((-m) // MICROS_PER_CENT)
    else:
        cents_total = m // MICROS_PER_CENT
    if m > 0 and cents_total == 0:
        return "<0.01"
    return "%s%d.%02d" % ("-" if neg else "", cents_total // 100, cents_total % 100)


# ---------------------------------------------------------------------------------------
# The roll-up.
# ---------------------------------------------------------------------------------------

def check_rule(rule):
    """The declared rule, or a ValueError that NAMES why this one is not available. A rule in
    REFUSED_RULES is refused with its own reason, because a caller reaching for quadrature is
    making a claim about error independence and deserves to be told that, not handed a list."""
    if rule in ROLLUP_RULES:
        return rule
    if rule in REFUSED_RULES:
        raise ValueError("combination rule %r is REFUSED, not merely absent: %s. v1 declares "
                         "%s" % (rule, REFUSED_RULES[rule], sorted(ROLLUP_RULES)))
    raise ValueError("unknown combination rule %r: v1 declares %s (and refuses %s, each for a "
                     "stated reason)" % (rule, sorted(ROLLUP_RULES), sorted(REFUSED_RULES)))


def combine_ranges(ranges, rule=SUM_BOUNDS):
    """(low, high) for a set of (low, high) pairs under one declared rule.

    Raises on an unknown or refused rule and on an empty set: a total over no range is not
    zero, it is a total nobody has any evidence for, and returning (0, 0) here is precisely
    how an empty ledger becomes a confident number."""
    check_rule(rule)
    pairs = list(ranges)
    if not pairs:
        raise ValueError("cannot roll up an empty set of ranges: a sum over nothing is not "
                         "zero, it is the absence of evidence, and this module reports that "
                         "absence instead of a number")
    for lo, hi in pairs:
        if not (_is_int(lo) and _is_int(hi)):
            raise ValueError("every range needs an integer low and high, got %r" % ((lo, hi),))
    return sum(lo for lo, _ in pairs), sum(hi for _, hi in pairs)


def spread_pct(low, high):
    """A range's width as a percent of its low bound (high * 100 / low), floored.

    THE ONE NUMBER THAT MAKES FALSE CONFIDENCE VISIBLE. Under sum_bounds the total's spread
    is a weighted mediant of the item spreads, so it always lies between the tightest and the
    widest item: a wide range and a narrow one cannot average into a total tighter than the
    narrow one. Reported per item and for the total so a reader can check that themselves."""
    if not (_is_int(low) and _is_int(high)) or low <= 0:
        return None
    return high * 100 // low


def _item_row(sid, rec, E):
    """One work item's contribution, or its named reason for contributing nothing.

    A record handed to this module is NEVER trusted: it goes through the estimate module's own
    validator, and an invalid one is EXCLUDED from the sum and NAMED. Silently including a
    broken record would put a number nobody can defend into a dollar figure; silently dropping
    it would understate the plan while looking complete."""
    row = {"spec": sid, "estimated": False, "malformed": False, "low": None, "high": None,
           "unit": None, "calibration": None, "spread_pct": None, "reason": None}
    if rec is None:
        row["reason"] = ("no committed estimate (an estimate is opt-in per plan, PLAN-0014 D3, "
                         "so its absence is an ordinary state and not a finding)")
        return row
    problems = E.validate_record(rec, spec_id=sid)
    if problems:
        row["malformed"] = True
        row["reason"] = "the committed estimate is malformed and is excluded from the sum: %s" \
                        % "; ".join(problems)
        return row
    if rec.get("unit") != UNIT_TOKENS:
        row["malformed"] = True
        row["reason"] = ("the committed estimate is in unit %r and this roll-up adds %r: two "
                         "units are not summable, and converting one into the other here would "
                         "invent a factor nobody declared" % (rec.get("unit"), UNIT_TOKENS))
        return row
    row.update({"estimated": True, "low": rec["low"], "high": rec["high"],
                "unit": rec["unit"], "calibration": rec.get("calibration"),
                "spread_pct": spread_pct(rec["low"], rec["high"])})
    return row


def _money(low, high, price, calibration):
    """The dollar range for a token range, or the named reason there is none.

    UNPRICED IS NOT ZERO: with no rate every field is None and `priced` is False. The caveat
    is part of the answer rather than a footnote somewhere else, because the two things a
    reader of this number must know are that the rate is for ONE model while the token range
    carries no model stamp, and whether the range underneath was calibrated at all."""
    out = {"priced": False, "usd_micros_low": None, "usd_micros_high": None,
           "usd_low": "unpriced", "usd_high": "unpriced", "rate": None, "reason": None,
           "caveat": None}
    if low is None or high is None:
        out["reason"] = ("there is no token range to price, so there is no dollar range: an "
                         "unpriced total reads as unpriced and never as zero")
        return out
    if price is None:
        out["reason"] = ("this repository declares no token price (%s is absent) and none was "
                         "supplied, so the range is UNPRICED. Unpriced is not free" % PRICE_FILE)
        return out
    rate = price["usd_micros_per_1k_tokens"]
    out.update({
        "priced": True,
        "usd_micros_low": usd_micros(low, rate, up=False),
        "usd_micros_high": usd_micros(high, rate, up=True),
        "rate": {k: price[k] for k in PRICE_ORDER if k in price},
        "caveat": ("the rate is declared for model %r and observed %s; the token range it "
                   "converts carries no model stamp of its own, and the range is %s"
                   % (price["model"], price["observed_at"], calibration or "of unknown "
                      "calibration")),
    })
    out["usd_low"] = render_usd(out["usd_micros_low"], up=False)
    out["usd_high"] = render_usd(out["usd_micros_high"], up=True)
    return out


def _pacing(low, high, spend):
    """Where the plan is against its own range, or the named reason it cannot be said.

    THE ZERO THIS REFUSES TO PRINT: with nothing recorded, "0 percent consumed" reads as a
    measurement of being on track. Nothing recorded and nothing spent are different facts, so
    `spend_recorded` is a field and the position is None when it is false."""
    out = {"available": False, "spend_recorded": False, "spent_tokens": None,
           "position": None, "of_low_pct": None, "of_high_pct": None, "reason": None,
           "source": (spend or {}).get("source")}
    if spend is None:
        out["reason"] = ("the plan's recorded spend could not be read: %s"
                         % "this engine ships no .veldo/budget.py, which owns how a plan's "
                           "spend is attributed, and this module does not recompute that "
                           "attribution under a rule of its own")
        return out
    out["spend_recorded"] = bool(spend.get("recorded"))
    if not out["spend_recorded"]:
        out["reason"] = ("no spend has ever been recorded against this plan, so there is "
                         "nothing to pace against. A 0 percent figure here would read as a "
                         "measurement of being on track rather than as an empty ledger")
        return out
    spent = int(spend.get("tokens") or 0)
    out["spent_tokens"] = spent
    if low is None or high is None:
        out["reason"] = ("spend is recorded but there is no estimate range to pace against, "
                         "so only the total is reported")
        return out
    out["available"] = True
    out["of_low_pct"] = spent * 100 // low if low > 0 else None
    out["of_high_pct"] = spent * 100 // high if high > 0 else None
    out["position"] = "under_low" if spent < low else ("over_high" if spent > high else "in_range")
    return out


def _cap(plan_fm, B, low, high, money):
    """The plan's own DECLARED cap, read through budget.py, and where the rolled-up range
    falls against it. Advisory: `over` is a word in a report and never an exit code.

    Read rather than re-parsed: budget.parse_budgets owns the shape of a budgets block,
    including its refusal, so a malformed one is named here with that module's own message
    instead of being interpreted a second way."""
    out = {"declared": False, "tokens": None, "cost_usd": None, "token_position": None,
           "cost_position": None, "reason": None}
    if B is None:
        out["reason"] = ("no .veldo/budget.py in this engine, which owns what a plan's "
                         "declared budget IS, so the cap is not read here")
        return out
    try:
        caps = B.parse_budgets(plan_fm)
    except Exception as e:                                  # BudgetError, named by that module
        out["reason"] = "the plan's budgets block is malformed: %s" % e
        return out
    if not caps:
        out["reason"] = "this plan declares no budget, so there is no cap to compare against"
        return out
    out["declared"] = True
    out["tokens"] = caps.get("tokens")
    out["cost_usd"] = caps.get("cost_usd")
    if out["tokens"] is not None and low is not None:
        out["token_position"] = ("under_cap" if high <= out["tokens"]
                                 else ("over_cap" if low > out["tokens"] else "straddles_cap"))
    if out["cost_usd"] is not None and money.get("priced"):
        cap_micros = int(round(float(out["cost_usd"]) * MICROS_PER_USD))
        out["cost_position"] = (
            "under_cap" if money["usd_micros_high"] <= cap_micros
            else ("over_cap" if money["usd_micros_low"] > cap_micros else "straddles_cap"))
    return out


def rollup(plan_fm, estimates, price=None, spend=None, rule=SUM_BOUNDS, E=None, B=None):
    """ONE plan's rolled-up range, dollar range and pacing. PURE over what it is handed.

    `estimates` is {spec_id: record} exactly as estimate.load_dir returns; `price` is a
    validated rate record or None; `spend` is {tokens, recorded, source} or None when the
    owner of that reading is unavailable. `E` and `B` are the estimate and budget modules,
    injectable so a test drives this without either one reaching for the real repository.

    Nothing is written. Nothing is refused. A plan with no estimates gets no range, and that
    is an answer with a reason attached, not a zero."""
    check_rule(rule)
    E = E or _estimate()
    if B is None:
        B = _budget()
    work = B.plan_work_specs(plan_fm) if B is not None else []
    rows = [_item_row(sid, (estimates or {}).get(sid), E) for sid in work]
    priced_rows = [r for r in rows if r["estimated"]]
    low = high = None
    if priced_rows:
        low, high = combine_ranges([(r["low"], r["high"]) for r in priced_rows], rule)
    calibration = None
    if priced_rows:
        # THE WEAKEST LINK GOVERNS A SUM. One uncalibrated item is enough to make the total's
        # error unmeasured, so `calibrated` requires every contributor to be.
        calibration = ("calibrated" if all(r["calibration"] == "calibrated" for r in priced_rows)
                       else "uncalibrated")
    money = _money(low, high, price, calibration)
    view = {
        "schema": SCHEMA,
        "plan": plan_fm.get("id"),
        "rule": rule,
        "unit": UNIT_TOKENS,
        "items": rows,
        "coverage": {
            "items": len(rows),
            "estimated": len(priced_rows),
            "unestimated": len(rows) - len(priced_rows),
            "complete": bool(rows) and len(priced_rows) == len(rows),
            "missing": [r["spec"] for r in rows if not r["estimated"]],
        },
        "tokens": {"low": low, "high": high,
                   "spread_pct": spread_pct(low, high) if low is not None else None},
        "calibration": calibration,
        "money": money,
        "pacing": _pacing(low, high, spend),
        "cap": _cap(plan_fm, B, low, high, money),
        "advisory": dict(ADVISORY),
        "reason": None,
        # NAMED, NOT COUNTED, and flagged by the row that judged it rather than by a substring
        # of its own message: a record present and broken speaks up here while an absent one
        # stands down silently. Those are different facts.
        "problems": ["%s: %s" % (r["spec"], r["reason"]) for r in rows if r["malformed"]],
    }
    if not rows:
        view["reason"] = ("this plan declares no work items, so there is nothing to roll up"
                          if B is not None else
                          "no .veldo/budget.py in this engine, which owns which spec ids are a "
                          "plan's work items, so the roll-up stands down rather than reading "
                          "the plan a second way")
    elif not priced_rows:
        view["reason"] = ("no work item of this plan carries a committed estimate, so there is "
                          "NO range: a sum over nothing would be a confident zero. %d item(s) "
                          "are waiting for one" % len(rows))
    elif not view["coverage"]["complete"]:
        view["reason"] = ("PARTIAL: %d of %d work items carry an estimate, so this range is the "
                          "range of THOSE items and is not the plan's range. It understates the "
                          "plan by whatever the other %d cost"
                          % (view["coverage"]["estimated"], view["coverage"]["items"],
                             view["coverage"]["unestimated"]))
    return view


def program_rollup(views, rule=SUM_BOUNDS):
    """A program's range: the sum of its plans' ranges, under the same declared rule.

    PARTIALITY PROPAGATES UPWARD, because it has to: a program containing one partial plan is
    partial, and a plan that contributed no range at all is a bigger hole than a partial one,
    so both are named separately.

    MONEY IS NOT BLENDED ACROSS RATES. Two plans priced at two different rates are two
    different units, and a program total across them would be a mixture wearing a single
    number's clothes - the same refusal toe_normalize makes across capability eras. It stands
    down with both rates named."""
    check_rule(rule)
    with_range = [v for v in views if v["tokens"]["low"] is not None]
    low = high = None
    if with_range:
        low, high = combine_ranges([(v["tokens"]["low"], v["tokens"]["high"])
                                    for v in with_range], rule)
    calibration = None
    if with_range:
        calibration = ("calibrated" if all(v["calibration"] == "calibrated" for v in with_range)
                       else "uncalibrated")
    rates = [json.dumps(v["money"]["rate"], sort_keys=True) for v in with_range
             if v["money"]["priced"]]
    money = {"priced": False, "usd_micros_low": None, "usd_micros_high": None,
             "usd_low": "unpriced", "usd_high": "unpriced", "rate": None, "reason": None,
             "caveat": None}
    if not with_range:
        money["reason"] = "no plan in this program carries a range, so there is nothing to price"
    elif len(rates) != len(with_range):
        money["reason"] = ("%d of %d contributing plans are unpriced, and a program total that "
                           "silently omitted them would understate the program: unpriced is not "
                           "zero" % (len(with_range) - len(rates), len(with_range)))
    elif len(set(rates)) > 1:
        money["reason"] = ("the contributing plans are priced at %d DIFFERENT rates (%s), which "
                           "are different units; blending them would produce a mixture wearing "
                           "one number's clothes" % (len(set(rates)), sorted(set(rates))))
    else:
        money = _money(low, high, with_range[0]["money"]["rate"], calibration)
    return {
        "schema": SCHEMA,
        "program": [v["plan"] for v in views],
        "rule": rule,
        "unit": UNIT_TOKENS,
        "plans": [{"plan": v["plan"], "low": v["tokens"]["low"], "high": v["tokens"]["high"],
                   "complete": v["coverage"]["complete"], "reason": v["reason"]} for v in views],
        "coverage": {
            "plans": len(views),
            "with_range": len(with_range),
            "without_range": len(views) - len(with_range),
            "complete": bool(views) and all(v["coverage"]["complete"] for v in views),
            "partial_plans": [v["plan"] for v in views if not v["coverage"]["complete"]],
        },
        "tokens": {"low": low, "high": high,
                   "spread_pct": spread_pct(low, high) if low is not None else None},
        "calibration": calibration,
        "money": money,
        "advisory": dict(ADVISORY),
    }


# ---------------------------------------------------------------------------------------
# The pacing seam. Data, never a Window, and never the low bound.
# ---------------------------------------------------------------------------------------

def _coverage_detail(cov):
    """How partial a roll-up is, IN THE WORDS OF WHICHEVER SHAPE IT IS.

    Both public surfaces here produce a `coverage` block and the two blocks count different
    things: a PLAN view counts work items (`items` / `estimated`) and a PROGRAM view counts
    plans (`plans` / `with_range` / `partial_plans`). Discriminated on the declared key rather
    than duck-typed, and a THIRD shape is refused BY NAME, because the alternative shipped
    once: a plan-shaped format string reached with a program view raised KeyError from inside
    a message, on the one branch that exists to stand down safely."""
    if "items" in cov:
        return "%s of %s work items estimated" % (cov.get("estimated"), cov.get("items"))
    if "plans" in cov:
        return ("%s of %s plan(s) carry a range and these are themselves partial: %s"
                % (cov.get("with_range"), cov.get("plans"),
                   ", ".join(cov.get("partial_plans") or []) or "none"))
    raise ValueError("pacing_windows was handed a view whose coverage block is NEITHER a plan's "
                     "(items) nor a program's (plans), so how partial it is cannot be stated: "
                     "keys %r" % (sorted(cov),))


def pacing_windows(view, horizons=()):
    """([window shapes], reason). PLAIN DICTS a caller may hand to .veldo/governor.py's
    Window(name, seconds, tokens), which is unmodified and not imported here.

    THREE RULES, and each one closes a way a number could stop work:

      - the HIGH bound and never the low. A range's low bound is its optimistic end, not a
        limit; pacing against it would stall real work on the happy case.
      - NOTHING when there is no range. A zero-token window is the dangerous shape: the
        governor refuses a non-positive budget and returns zero workers when a window is
        spent, so an empty estimate ledger must produce no window at all rather than one
        that stalls a pool.
      - DATA, not a Window. Constructing the governor's object here would make this module
        the thing that paces; handing over numbers leaves that decision where it belongs,
        in the open, with whoever wires it (D4).

    A PLAN VIEW AND A PROGRAM VIEW ARE BOTH ACCEPTED, and that is not a convenience: a
    program roll-up is a public surface producing the same `tokens` block, so a caller
    reaching the seam with one is ordinary. Both stand down identically, which is the whole
    point - the shape that used to raise here was the PARTIAL one, the unsafe branch, while
    the complete one passed through and emitted a window."""
    high = view.get("tokens", {}).get("high")
    if high is None:
        why = view.get("reason")
        if not why:
            why = ("no contributing plan carries a range"
                   if "plans" in (view.get("coverage") or {}) else "no estimates")
        return [], ("no range to pace against: %s" % why)
    if not (view.get("coverage") or {}).get("complete"):
        return [], ("the roll-up is PARTIAL (%s), and pacing a whole pool against part of a "
                    "roll-up's range would throttle on a number known to be too small"
                    % _coverage_detail(view.get("coverage") or {}))
    out = []
    for name, seconds in horizons:
        if seconds <= 0:
            raise ValueError("horizon %r needs positive seconds, got %r" % (name, seconds))
        out.append({"name": name, "seconds": seconds, "tokens": high,
                    "bound": "high", "advisory": True})
    if not out:
        return [], "no horizon was asked for, so no window is offered"
    return out, None


# ---------------------------------------------------------------------------------------
# Assembly over a real repository, and the report.
# ---------------------------------------------------------------------------------------

def plan_spend_view(plan_fm, events, B=None, C=None):
    """What this plan has spent, and whether ANY of it was ever recorded.

    TWO OWNERS, EACH FOR THE THING IT OWNS, and no third calculation. The TOTAL comes from
    budget.plan_spend (which reads metrics.compute, the one spend aggregation in this system,
    and owns which correlations belong to a plan). The RECORDED FLAG comes from
    toe_corpus.spend_for, which owns the answer to "did this event carry spend at all" - the
    distinction budget.py has no reason to make, because a zero and an absence enforce the
    same. The suite asserts the two agree on the total, so a divergence reds a test instead
    of quietly producing two numbers."""
    if B is None:
        B = _budget()
    if B is None:
        return None
    C = C or _corpus()
    totals = B.plan_spend(plan_fm, events)
    corrs = [plan_fm.get("id")] + B.plan_work_specs(plan_fm)
    recorded = any(C.spend_for(events, c)["spend_recorded"] for c in corrs if c)
    return {"tokens": int(totals.get("tokens") or 0),
            "cost_usd": totals.get("cost_usd"),
            "recorded": recorded,
            "source": "budget.plan_spend over the event stream"}


def build_view(plan_arg, root=None, price=None, rule=SUM_BOUNDS, events=None):
    """The whole view over a real repository. READS ONLY: no file is written, no event is
    appended, and nothing is created when nothing is there."""
    base = Path(root) if root else ROOT
    V = _validate()
    E = _estimate()
    B = _budget()
    fm = load_plan_fm(plan_arg, base, V)
    if price is None:
        price = read_price(root=base, parse=V.parse_yamlish)
    if events is None:
        events = _read_events(base)
    ests, problems = E.load_dir(base / E.ESTIMATES_DIR)
    spend = plan_spend_view(fm, events, B=B) if B is not None else None
    view = rollup(fm, ests, price=price, spend=spend, rule=rule, E=E, B=B)
    view["problems"] = list(view["problems"]) + list(problems)
    return view


def load_plan_fm(arg, base=None, V=None):
    """A plan file path or a PLAN-id, as front matter, through the ONE parser. The same two
    ways budget.py accepts a plan, so a plan this module can report on is a plan that module
    can enforce on."""
    base = Path(base) if base else ROOT
    V = V or _validate()
    p = Path(arg)
    if p.is_file():
        m = re.match(r"^---\n(.*?)\n---", p.read_text(), re.S)
        if not m:
            raise ValueError("no front matter in %s" % arg)
        return V.parse_yamlish(m.group(1))
    reg = V.plan_registry(base / "plans")
    if arg in reg:
        return reg[arg]["fm"]
    raise ValueError("no plan found: %s (looked for a file and for a plan id under %s)"
                     % (arg, base / "plans"))


def _read_events(base):
    """The event log as parsed lines. A line that is not JSON is skipped rather than refused,
    because validate.check_events owns that judgement and two organs refusing one line
    differently is how one of them becomes unrunnable. An absent log is empty, not an error."""
    p = Path(base) / ".veldo" / "events.jsonl"
    if not p.is_file():
        return []
    out = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def render_lines(view):
    """The human report. Every standdown prints its REASON, because a surface that prints
    nothing where a number would go teaches a reader to assume a zero."""
    t, cov, money, pace, cap = (view["tokens"], view["coverage"], view["money"],
                               view["pacing"], view["cap"])
    out = ["roll-up for %s (rule %s, unit %s)" % (view["plan"], view["rule"], view["unit"])]
    for r in view["items"]:
        if r["estimated"]:
            out.append("  %-14s %10d .. %-10d %s (spread %s%%, %s)"
                       % (r["spec"], r["low"], r["high"], view["unit"], r["spread_pct"],
                          r["calibration"]))
        else:
            out.append("  %-14s %s" % (r["spec"], "no range: %s" % r["reason"]))
    out.append("  coverage: %d of %d item(s) estimated%s"
               % (cov["estimated"], cov["items"],
                  "" if cov["complete"] else (" (NONE)" if not cov["estimated"]
                                              else " (PARTIAL)")))
    if t["low"] is None:
        out.append("  tokens: NONE - %s" % view["reason"])
    else:
        out.append("  tokens: %d .. %d (spread %s%%, %s)"
                   % (t["low"], t["high"], t["spread_pct"], view["calibration"]))
        if view["reason"]:
            out.append("  NOTE: %s" % view["reason"])
    if money["priced"]:
        out.append("  dollars: %s .. %s usd (rate %d micro-usd per 1k tokens, model %s, "
                   "source %s, observed %s)"
                   % (money["usd_low"], money["usd_high"],
                      money["rate"]["usd_micros_per_1k_tokens"], money["rate"]["model"],
                      money["rate"]["source"], money["rate"]["observed_at"]))
        out.append("  caveat: %s" % money["caveat"])
    else:
        out.append("  dollars: UNPRICED - %s" % money["reason"])
    if pace["available"]:
        out.append("  pacing: %d tokens spent, %s (%s%% of the low bound, %s%% of the high)"
                   % (pace["spent_tokens"], pace["position"], pace["of_low_pct"],
                      pace["of_high_pct"]))
    else:
        out.append("  pacing: not available - %s" % pace["reason"])
    if cap["declared"]:
        out.append("  declared cap: %s tokens, %s usd; range is %s / %s"
                   % (cap["tokens"], cap["cost_usd"], cap["token_position"],
                      cap["cost_position"]))
    else:
        out.append("  declared cap: none - %s" % cap["reason"])
    for p in view["problems"]:
        out.append("  PROBLEM: %s" % p)
    out.append("  ADVISORY: this informs pacing and blocks nothing (PLAN-0014 NG1, D4)")
    return out


def render_program_lines(view):
    """The program report, in the same shape and with the same standdown discipline."""
    t, cov, money = view["tokens"], view["coverage"], view["money"]
    out = ["program roll-up over %d plan(s) (rule %s, unit %s)"
           % (cov["plans"], view["rule"], view["unit"])]
    for p in view["plans"]:
        if p["low"] is None:
            out.append("  %-12s no range: %s" % (p["plan"], p["reason"]))
        else:
            out.append("  %-12s %10d .. %-10d %s%s"
                       % (p["plan"], p["low"], p["high"], view["unit"],
                          "" if p["complete"] else "  (PARTIAL)"))
    if t["low"] is None:
        out.append("  tokens: NONE - no contributing plan carries a range")
    else:
        out.append("  tokens: %d .. %d (spread %s%%, %s) over %d of %d plan(s)"
                   % (t["low"], t["high"], t["spread_pct"], view["calibration"],
                      cov["with_range"], cov["plans"]))
    out.append("  dollars: %s" % ("%s .. %s usd" % (money["usd_low"], money["usd_high"])
                                  if money["priced"] else "UNPRICED - %s" % money["reason"]))
    out.append("  ADVISORY: this informs pacing and blocks nothing (PLAN-0014 NG1, D4)")
    return out


def _cli(argv):
    ap = argparse.ArgumentParser(
        prog="toe_budget.py",
        description="Roll a plan's committed estimate ranges up to a plan or program range, "
                    "convert it to a dollar range at a declared rate, and pace it against "
                    "recorded spend. ADVISORY: informs, never blocks.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, helptext in (("rollup", "one plan's rolled-up range, dollars and pacing"),
                           ("program", "the sum of several plans' ranges")):
        c = sub.add_parser(name, help=helptext)
        c.add_argument("plan", nargs="+" if name == "program" else 1,
                       help="a plan file path or a PLAN-id")
        c.add_argument("--json", action="store_true", help="machine-readable output")
        c.add_argument("--root", default=None,
                       help="read the plan, the committed estimates, the declared price and the "
                            "event log under THIS root instead of the repository this module "
                            "lives in. Reads only, creates nothing, and exists so the report "
                            "can be driven over a fixture tree: a surface nobody can run over "
                            "a planted-bad input is a surface nobody has tested")
        c.add_argument("--price-usd-micros-per-1k", type=int,
                       help="display only: integer micro-USD per 1000 tokens. Requires "
                            "--price-model, --price-source and --price-observed-at: money "
                            "without a stated provenance is refused")
        c.add_argument("--price-model")
        c.add_argument("--price-source")
        c.add_argument("--price-observed-at")
    sub.add_parser("rules", help="the declared roll-up rule and the refused ones, with reasons")
    sub.add_parser("price", help="the declared token price in force and where it came from")
    a = ap.parse_args(argv)

    if a.cmd == "rules":
        print("declared:")
        for k in sorted(ROLLUP_RULES):
            print("  %-16s %s" % (k, ROLLUP_RULES[k]))
        print("refused (each by name, with the reason, never silently unavailable):")
        for k in sorted(REFUSED_RULES):
            print("  %-16s %s" % (k, REFUSED_RULES[k]))
        return 0

    V = _validate()
    if a.cmd == "price":
        try:
            price = read_price(parse=V.parse_yamlish)
        except ValueError as e:
            V.fail(PRICE_FILE, str(e))
            return 1
        if price is None:
            print("token price: none declared at %s - every dollar range reads UNPRICED, "
                  "which is not zero (this is not a finding)" % PRICE_FILE)
            return 0
        print(json.dumps(price, sort_keys=True, indent=1))
        return 0

    price = None
    if a.price_usd_micros_per_1k is not None:
        try:
            price = price_from_args(a.price_usd_micros_per_1k, a.price_model, a.price_source,
                                    a.price_observed_at)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 1
    try:
        views = [build_view(p, root=a.root, price=price) for p in a.plan]
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    if a.cmd == "program":
        pv = program_rollup(views)
        print(json.dumps(pv, sort_keys=True, indent=1) if a.json
              else "\n".join(render_program_lines(pv)))
        return 0
    view = views[0]
    print(json.dumps(view, sort_keys=True, indent=1) if a.json
          else "\n".join(render_lines(view)))
    # EXIT 0 ON EVERY ADVISORY VERDICT, including over the declared cap and PARTIAL. A tool
    # that exited non-zero on a number would become a gate the first time somebody wired it
    # into a script, which is exactly NG1. A record present on disk that cannot be read is a
    # refusal to REPORT and is the only non-zero path here.
    return 1 if view["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
