"""WARP-1404: historical analogy, and the reasons each check can fail.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, which always
runs, so its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 15_warp_1404_historical_analogy

WHAT IS OBSERVED HERE, AND WHY IT IS SHAPED AS PAIRS. The subject is a layer whose correct output
in this repository today is NOTHING, and the danger with a module like that is a test suite that
proves only the refusal. A function that always declines passes every stand-down assertion in this
file. So every refusal is paired with the positive control that a SEEDED corpus through the SAME
function produces a range, and every acceptance is paired with the negative control that a
mutation of the same input is refused.

THE ASSERTIONS WERE WATCHED FAILING, one mutation at a time, in BOTH copies of the module so the
byte-identity assertion is never the thing that reds, each restored before the next. Measured
2026-08-10 against this fragment's 37 passed, 0 failed:

  1. `_standdown` given `"low": 0, "high": 0` alongside its reason: 5 RED, which is the whole
     spread of the property - the three zero-evidence shapes, the below-minimum stand-down, the
     unreadable target, the era exclusion and the real-repository measurement all require the
     bound keys to be ABSENT. A confident zero where there is no evidence is the one defect this
     item exists to prevent, so it had to be seen biting on every path rather than on one.
  2. the evidence loop made to add `cycles.gate_failures` to each record's distance: 1 RED, the
     leakage assertion, and nothing else.
     AND THE INSTRUCTIVE PART, recorded because it changed the assertion: the FIRST probe
     perturbed `distance` itself and was INVISIBLE. It had to be, and the reason is worth
     stating - `distance` is handed a feature VECTOR, so it cannot reach an outcome no matter
     what it does, which made the original assertion (two records with identical features are
     the same distance apart) structurally guaranteed and therefore worth nothing. The only
     place leakage can enter is what the evidence loop FEEDS the distance, so the assertion was
     rewritten to read the REPORT's own distances, and then the faithful mutation bit.
  3. `widening_pct` pinned to `SMALL_SAMPLE_SLACK` regardless of n: 3 RED, the tightening
     assertion, the monotonicity sweep, and the two-cluster anti-vacuity assertion, whose
     cheap and expensive ranges stopped being disjoint once every range was widened by 150
     percent. The layer's PROVENANCE assertion stayed GREEN, because the recorded inputs still
     reproduced the recorded bounds, and that is the instructive part here: a self-consistent
     record is not a correct one, so the tightening property needs its own teeth rather than
     riding on arithmetic that recomputes itself.
  4. the era window dropped, by ignoring `era` in `evidence`: 2 RED, the injected-reader
     exclusion and the hermetic end-to-end ledger assertion. The control (no ledger, so one era,
     so nothing excluded) stayed GREEN, which is what proves the exclusion is the LEDGER's doing
     and not a module that drops records.
  5. `augment` made to hand a layer to `build_record` unconditionally, so a stand-down still
     produced a two-layer record: 2 RED, the byte-identity of the stand-down record against
     estimate.propose alone, and the calibration pair. That equality is PLAN-0014's
     adoption-safety property for this item, and it is asserted on rendered BYTES because bytes
     are what gets committed beside a spec.
  6. `refuse_malformed` made to skip a record of the wrong schema instead of refusing: 1 RED, the
     fail-closed assertion, while its partner (a well-formed but unusable record is COUNTED, not
     refused) stayed GREEN. Absence stands down; breakage speaks up; those are different facts.

WHAT IS DELIBERATELY MEASURED RATHER THAN ARGUED. Two things. The stand-down over THIS repository
is driven through the real `repo_basis` over the real corpus and the real event log, and it is
required to be the no-spend stand-down over a NON-EMPTY corpus - and then the same real corpus,
with spend planted on four of its own records, is required to produce a range, so the measured
stand-down is attributable to the missing emitter and not to anything else about this repository.
And the era window is driven end to end over a hermetic repository root carrying a real
capability-shift ledger, real spend events and real fixture specs, not only through an injected
reader, because an injected reader tests the fake.
"""
import shutil as _w1404_shutil

_w1404_aspec = importlib.util.spec_from_file_location(
    "w1404_analogy", ROOT / ".veldo" / "toe_analogy.py")
A1404 = importlib.util.module_from_spec(_w1404_aspec)
_w1404_aspec.loader.exec_module(A1404)

_w1404_espec = importlib.util.spec_from_file_location(
    "w1404_estimate", ROOT / ".veldo" / "estimate.py")
E1404 = importlib.util.module_from_spec(_w1404_espec)
_w1404_espec.loader.exec_module(E1404)

_w1404_nspec = importlib.util.spec_from_file_location(
    "w1404_normalize", ROOT / ".veldo" / "toe_normalize.py")
N1404 = importlib.util.module_from_spec(_w1404_nspec)
_w1404_nspec.loader.exec_module(N1404)

_w1404_cspec = importlib.util.spec_from_file_location(
    "w1404_corpus", ROOT / ".veldo" / "toe_corpus.py")
TC1404 = importlib.util.module_from_spec(_w1404_cspec)
_w1404_cspec.loader.exec_module(TC1404)

_w1404_mspec = importlib.util.spec_from_file_location(
    "w1404_metrics", ROOT / ".veldo" / "metrics.py")
M1404 = importlib.util.module_from_spec(_w1404_mspec)
_w1404_mspec.loader.exec_module(M1404)


def _w1404_raises(fn, *a, **kw):
    """(raised, message). The message is returned because that is what carries the refusal: an
    assertion that something raised, without checking WHAT, passes on a stray TypeError."""
    try:
        fn(*a, **kw)
    except BaseException as e:
        return True, "%s: %s" % (type(e).__name__, e)
    return False, ""


def _w1404_rec(spec, risk="standard", acs=2, globs=2, protected=False, tokens=None,
               cycles=None, git=None):
    """One veldo.toe_actuals/v1 record in the shape WARP-1401's build produces. Built rather
    than pinned, because every matching assertion below needs two records differing in exactly
    ONE feature, and `tokens=None` is the record shape of a change whose spend was never
    recorded, which is every record in this repository today."""
    return {
        "schema": "veldo.toe_actuals/v1",
        "spec": spec,
        "features": {"spec_id": spec, "status": "shipped", "risk": risk,
                     "acceptance_criteria": acs, "footprint_declared": globs,
                     "protected_touch": protected, "plan": None, "lane": None,
                     "human_approval": None, "depends_on": 0, "spec_bytes": 4096},
        "cycles": cycles or {"gate_passes": 1, "gate_failures": 0, "review_verdicts": 1,
                             "events_seen": 2},
        "spend": {"tokens": tokens or 0, "cost_usd": 0.0, "human_minutes": 0,
                  "spend_recorded": tokens is not None},
        "git": git or {"commits": 1, "files_touched": 3},
    }


def _w1404_vec(risk="standard", acs=2, globs=2, protected=False):
    return A1404.vector({"risk": risk, "acceptance_criteria": acs,
                         "footprint_declared": globs, "protected_touch": protected})


def _w1404_spec_text(spec_id="WARP-9404", risk="standard", acs=2, status="ready",
                     footprint=(".veldo/nothing_a.py", ".veldo/nothing_b.py")):
    """A fixture spec carrying exactly the mechanical features under test."""
    lines = ["---", "schema: veldo.spec/v1", "id: %s" % spec_id,
             "title: analogy fixture", "status: %s" % status, "risk: %s" % risk,
             "owner: selftest"]
    if footprint:
        lines.append("placement: [metrics]")
        lines.append("footprint:")
        for f in footprint:
            lines.append('  - "%s"' % f)
    lines.append("acceptance_criteria:")
    for i in range(1, acs + 1):
        lines.append("  - id: AC%d" % i)
        lines.append("    text: observable thing %d happens." % i)
    lines += ["required_evidence: [unit]", "rollback: git revert", "---", "body", ""]
    return "\n".join(lines)


_W1404_AT = "2026-08-10"
_W1404_TARGET = "WARP-9404"

# Two clusters of shipped history: cheap standard-risk changes and expensive critical ones. The
# clusters exist so the anti-vacuity assertion has something to say - a layer that returned one
# constant range would satisfy every refusal in this file and be worthless.
_W1404_CHEAP = [_w1404_rec("WARP-0001", acs=2, globs=2, tokens=300000),
                _w1404_rec("WARP-0002", acs=3, globs=2, tokens=420000),
                _w1404_rec("WARP-0003", acs=2, globs=3, tokens=360000),
                _w1404_rec("WARP-0004", acs=1, globs=1, tokens=250000)]
_W1404_DEAR = [_w1404_rec("WARP-0101", risk="critical", acs=8, globs=12, protected=True,
                          tokens=2400000),
               _w1404_rec("WARP-0102", risk="critical", acs=9, globs=11, protected=True,
                          tokens=3100000),
               _w1404_rec("WARP-0103", risk="critical", acs=8, globs=13, protected=True,
                          tokens=2800000)]
_W1404_NOSPEND = [_w1404_rec("WARP-0201"), _w1404_rec("WARP-0202"), _w1404_rec("WARP-0203")]
_W1404_SEEDED = _W1404_CHEAP + _W1404_DEAR + _W1404_NOSPEND

_W1404_SMALL = _w1404_vec()
_W1404_BIG = _w1404_vec(risk="critical", acs=8, globs=12, protected=True)

with tempfile.TemporaryDirectory() as _d:

    # ---------------------------------------------------------------------------------------
    # AC1. NO EVIDENCE MEANS NO NUMBER, AND THE REFUSAL CARRIES NO BOUND AT ALL.
    # ---------------------------------------------------------------------------------------
    _w1404_layer, _w1404_rep = A1404.analogy(_W1404_TARGET, _W1404_SMALL, _W1404_SEEDED)
    expect("WARP-1404 AC1 POSITIVE CONTROL: over a SEEDED corpus the layer DOES produce a range, "
           "on the declared layer id and the declared corpus-grounded basis, with a low strictly "
           "below its high. Without this every stand-down assertion below would pass on a "
           "function that declines unconditionally, which is the one way a module like this can "
           "be completely broken and completely green",
           _w1404_rep["predicted"] is True
           and _w1404_layer is not None
           and _w1404_layer["layer"] == A1404.LAYER == "historical_analogy"
           and _w1404_layer["basis"] == A1404.BASIS == "corpus_analogy"
           and _w1404_layer["low"] < _w1404_layer["high"])

    expect("WARP-1404 AC1: THE LAYER ID AND BASIS COME FROM WARP-1402'S DECLARED VOCABULARY, "
           "checked against that module rather than spelled twice. The vocabulary was declared "
           "for the whole plan up front precisely so this item adds a record to it instead of "
           "widening it, and a typo here would be a layer no reader recognises",
           A1404.LAYER in E1404.LAYERS and A1404.BASIS in E1404.BASES
           and A1404.BASIS in E1404.CALIBRATED_BASES)

    _W1404_STANDDOWNS = (
        ("no_corpus", []),
        ("no_recorded_actuals", list(_W1404_NOSPEND)),
        ("no_comparable_records", [_w1404_rec(_W1404_TARGET, tokens=400000)]),
    )
    _w1404_sd = [A1404.analogy(_W1404_TARGET, _W1404_SMALL, c) for _code, c in _W1404_STANDDOWNS]
    expect("WARP-1404 AC1, THE LOAD-BEARING ONE: EVERY ZERO-EVIDENCE SHAPE PRODUCES NO LAYER AND "
           "A REPORT WITH NO `low` AND NO `high` KEY AT ALL. Not zero, not null: ABSENT, so a "
           "consumer that skipped `predicted` gets a KeyError rather than a figure it can sum "
           "into a budget. Driven over an empty corpus, a corpus whose records carry no spend, "
           "and a corpus whose only record is the target's own, each required to give its OWN "
           "declared reason code rather than a generic one - because those are three different "
           "facts and only one of them is fixed by recording spend",
           len(_W1404_STANDDOWNS) == 3
           and all(l is None for l, _r in _w1404_sd)
           and all("low" not in r and "high" not in r for _l, r in _w1404_sd)
           and [r["reason_code"] for _l, r in _w1404_sd]
           == [code for code, _c in _W1404_STANDDOWNS]
           and all(r["reason"] == A1404.REASONS[r["reason_code"]] for _l, r in _w1404_sd)
           and all(r["matched_specs"] == [] and r["matched"] == 0 for _l, r in _w1404_sd))

    expect("WARP-1404 AC1: THE TARGET'S OWN RECORD IS EXCLUDED AND COUNTED. A corpus whose only "
           "record is the spec being estimated stands down naming that, with self=1 in the "
           "exclusions, because a re-estimate of a shipped change that predicted its own cost "
           "perfectly would be a measurement of nothing at all",
           _w1404_sd[2][1]["excluded"]["self"] == 1
           and _w1404_sd[2][1]["candidates"] == 0
           and "not an analogy for itself" in A1404.REASONS[A1404.NO_COMPARABLE_RECORDS])

    _w1404_few = A1404.analogy(_W1404_TARGET, _W1404_SMALL, _W1404_CHEAP[:2])
    _w1404_exact = A1404.analogy(_W1404_TARGET, _W1404_SMALL, _W1404_CHEAP[:3])
    expect("WARP-1404 AC1: BELOW THE DECLARED MINIMUM OF COMPARABLES THERE IS NO RANGE, with the "
           "count and the requirement named in the detail, AND ITS CONTROL: exactly the minimum "
           "DOES produce one. One matched change is an anecdote and two are an anecdote and its "
           "gap; neither carries information about the spread of the population. The paired "
           "control is what makes the refusal the THRESHOLD's doing rather than a module that "
           "needs more than it will ever get",
           _w1404_few[0] is None and _w1404_few[1]["reason_code"] == "too_few_matches"
           and "low" not in _w1404_few[1] and _w1404_few[1]["matched"] == 2
           and str(A1404.MIN_MATCHES) in _w1404_few[1]["detail"]
           and _w1404_exact[0] is not None
           and _w1404_exact[1]["matched"] == A1404.MIN_MATCHES == 3)

    expect("WARP-1404 AC1: THE REASON VOCABULARY IS CLOSED, as a set equality against the six "
           "declared codes and not a count, so a reason added without a sentence - or a sentence "
           "with no code - reds here instead of reaching a consumer that switches on it and finds "
           "a case it does not handle. Bound to a literal tuple, so emptying the table reds this "
           "rather than passing over nothing",
           set(A1404.REASONS) == {A1404.NO_CORPUS, A1404.NO_RECORDED_ACTUALS,
                                  A1404.NO_COMPARABLE_RECORDS, A1404.NO_SAME_ERA_ACTUALS,
                                  A1404.TOO_FEW_MATCHES, A1404.UNREADABLE_TARGET}
           and len(A1404.REASONS) == 6
           and all(isinstance(v, str) and len(v) > 40 for v in A1404.REASONS.values()))

    _w1404_badtarget = A1404.analogy(_W1404_TARGET, None, _W1404_SEEDED)
    expect("WARP-1404 AC1: A TARGET WHOSE OWN FEATURES CANNOT BE READ IS A STAND-DOWN AND NEVER A "
           "GUESS, even over a corpus rich enough to answer. Declining blocks nothing, because a "
           "spec stands without an estimate; silently treating an unreadable tier as standard is "
           "how a wrong number gets a confident range around it",
           _w1404_badtarget[0] is None
           and _w1404_badtarget[1]["reason_code"] == "unreadable_target_features"
           and "low" not in _w1404_badtarget[1])

    expect("WARP-1404 AC1: vector() REFUSES AN UNREADABLE FEATURE MAPPING BY RETURNING None, for "
           "an undeclared tier, a negative count and a missing count, AND ITS CONTROL: the same "
           "mapping corrected returns a tuple. A default there would make every unreadable spec "
           "silently comparable to every other unreadable spec, which is the shape of a match "
           "that looks like evidence and is not",
           A1404.vector({"risk": "apocalyptic", "acceptance_criteria": 2,
                         "footprint_declared": 2}) is None
           and A1404.vector({"risk": "standard", "acceptance_criteria": -1,
                             "footprint_declared": 2}) is None
           and A1404.vector({"risk": "standard", "footprint_declared": 2}) is None
           and A1404.vector("not a mapping") is None
           and A1404.vector({"risk": "standard", "acceptance_criteria": 2,
                             "footprint_declared": 2}) == (1, 2, 2, False))

    # ---------------------------------------------------------------------------------------
    # AC2. PRE-BUILD FEATURES ONLY, AND THE LEAKAGE RULE IS MEASURED.
    # ---------------------------------------------------------------------------------------
    _w1404_plain = _w1404_rec("WARP-0301", tokens=300000)
    _w1404_loud = _w1404_rec("WARP-0302", tokens=1900000,
                             cycles={"gate_passes": 44, "gate_failures": 33,
                                     "review_verdicts": 22, "events_seen": 900},
                             git={"commits": 400, "files_touched": 900})
    _w1404_leak = A1404.analogy(_W1404_TARGET, _W1404_SMALL,
                                [_w1404_plain, _w1404_loud, _w1404_rec("WARP-0303",
                                                                       tokens=310000)])
    expect("WARP-1404 AC2, THE LEAKAGE RULE AS A MEASUREMENT OF THE PLUMBING AND NOT OF THE "
           "DISTANCE FUNCTION ALONE: three records with IDENTICAL pre-build features and wildly "
           "different cycles, git reality and recorded cost come back at the SAME distance IN THE "
           "REPORT and all three match. It is asserted on the report's own distances on purpose - "
           "distance() cannot see an outcome because it is handed a feature vector, so an "
           "assertion over distance() alone is structurally guaranteed and has no teeth at all; "
           "the only place leakage can enter is what the evidence loop FEEDS it, and that is what "
           "this reads. An estimate is committed before the work, so a matcher that chose "
           "comparables by how much trouble they turned out to be would score beautifully against "
           "history and be unusable on the only spec anybody ever needs an estimate for",
           _w1404_leak[1].get("distances") == [0, 0, 0]
           and sorted(_w1404_leak[1]["matched_specs"])
           == ["WARP-0301", "WARP-0302", "WARP-0303"]
           and A1404.distance(_W1404_SMALL, A1404.vector(_w1404_plain["features"]))
           == A1404.distance(_W1404_SMALL, A1404.vector(_w1404_loud["features"])))

    expect("WARP-1404 AC2: THE DECLARED MATCH SET IS EXACTLY THE PRE-BUILD FEATURES AND IS "
           "DISJOINT FROM THE OUTCOME BLOCKS, as set relations rather than as a comment. The "
           "weights name risk, criteria, surface and protected touch and nothing else; the "
           "outcome blocks are the three WARP-1401 records a change's cost in; the intersection "
           "is empty and every matched feature is one WARP-1401's own feature reader produces",
           set(A1404.FEATURE_WEIGHTS) == {"risk", "acceptance_criteria", "footprint_declared",
                                          "protected_touch"}
           and set(A1404.OUTCOME_BLOCKS) == {"cycles", "spend", "git"}
           and not (set(A1404.FEATURE_WEIGHTS) & set(A1404.OUTCOME_BLOCKS))
           and set(A1404.FEATURE_WEIGHTS) <= (
               set(_w1404_plain["features"]) | {"protected_touch"}))

    expect("WARP-1404 AC2: THE RISK ORDER COVERS EXACTLY THE RISK VOCABULARY validate.py DECLARES, "
           "as a set equality and not a count, so a tier added to the contract reds this rather "
           "than silently becoming unmatchable at the moment somebody writes the first spec at "
           "that tier",
           set(A1404.RISK_ORDER) == V.RISKS and len(A1404.RISK_ORDER) == len(V.RISKS))

    _w1404_dists = [
        A1404.distance(_W1404_SMALL, _w1404_vec()),
        A1404.distance(_W1404_SMALL, _w1404_vec(acs=3)),
        A1404.distance(_W1404_SMALL, _w1404_vec(risk="high")),
        A1404.distance(_W1404_SMALL, _w1404_vec(globs=4)),
        A1404.distance(_W1404_SMALL, _w1404_vec(protected=True)),
    ]
    expect("WARP-1404 AC2 ANTI-VACUITY ON THE DISTANCE: it is ZERO for a mechanically identical "
           "spec and STRICTLY POSITIVE for a change in each of the four declared features one at "
           "a time, and the four are not all the same number. A constant distance would make "
           "every spec comparable to every other and would satisfy every matching assertion in "
           "this file while meaning nothing",
           _w1404_dists[0] == 0
           and all(d > 0 for d in _w1404_dists[1:])
           and len(set(_w1404_dists[1:])) > 1
           and A1404.distance(_W1404_SMALL, None) is None
           and A1404.distance(None, _W1404_SMALL) is None)

    _w1404_near = _w1404_rec("WARP-0401", acs=4, tokens=500000)
    _w1404_far = _w1404_rec("WARP-0402", acs=2 + A1404.MATCH_RADIUS + 1, tokens=9000000)
    _w1404_radius = A1404.analogy(_W1404_TARGET, _W1404_SMALL,
                                  _W1404_CHEAP + [_w1404_near, _w1404_far])
    expect("WARP-1404 AC2: A RECORD BEYOND THE MATCH RADIUS DOES NOT ENTER THE EVIDENCE SET, AND "
           "ITS CONTROL: a record INSIDE it does. Both differ from the target in the same single "
           "pre-build feature and differ from each other only in how far, so the exclusion is "
           "the RADIUS and not a matcher that rejects whatever it has not seen before. The far "
           "record was given a nine-times cost on purpose: if it had leaked in, the range would "
           "have moved and this assertion would say so",
           "WARP-0401" in _w1404_radius[1]["matched_specs"]
           and "WARP-0402" not in _w1404_radius[1]["matched_specs"]
           and _w1404_radius[1]["candidates"] == 6
           and _w1404_radius[1]["matched"] == 5
           and max(_w1404_radius[1]["distances"]) <= A1404.MATCH_RADIUS
           and _w1404_radius[1]["observed_high"] == 500000)

    _w1404_selfset = A1404.analogy("WARP-0001", _W1404_SMALL, _W1404_CHEAP)
    expect("WARP-1404 AC2: THE TARGET IS EXCLUDED FROM ITS OWN EVIDENCE SET even when the rest of "
           "the corpus can answer: estimating WARP-0001 matches the other three cheap changes and "
           "never itself, and the exclusion is counted rather than silent",
           _w1404_selfset[0] is not None
           and "WARP-0001" not in _w1404_selfset[1]["matched_specs"]
           and _w1404_selfset[1]["excluded"]["self"] == 1
           and len(_w1404_selfset[1]["matched_specs"]) == 3)

    # ---------------------------------------------------------------------------------------
    # AC3. AN OBSERVED ENVELOPE THAT CITES ITS EVIDENCE, AND AN ALLOWANCE THAT TIGHTENS.
    # ---------------------------------------------------------------------------------------
    _w1404_in = _w1404_layer["inputs"]
    expect("WARP-1404 AC3: THE LAYER'S RECORDED INPUTS REPRODUCE ITS OWN BOUNDS, recomputed here "
           "from the record alone: the observed envelope, the widening, the rounding. THIS is "
           "what buys the plan its reconciliation - because the observed envelope and the "
           "allowance applied to it are both on record, W5 can tell a range that was wrong "
           "because the comparables were wrong from one that was wrong because the allowance was, "
           "and refit one without touching the other",
           _w1404_in["sample_widening_pct"] == A1404.widening_pct(_w1404_in["matched_specs"])
           and _w1404_layer["low"] == E1404._round_tokens(
               _w1404_in["observed_low"] * 100 // (100 + _w1404_in["sample_widening_pct"]))
           and _w1404_layer["high"] == E1404._round_tokens(
               _w1404_in["observed_high"] * (100 + _w1404_in["sample_widening_pct"]) // 100))

    expect("WARP-1404 AC3: THE LAYER CITES THE SHIPPED SPECS IT MATCHED, BY ID, and the count "
           "agrees with the list, and the observed envelope is exactly the lowest and highest "
           "recorded cost among them. A range whose evidence cannot be opened and read is a "
           "number somebody has to take on trust, which is the thing legacy points were and this "
           "unit is not",
           _w1404_in["matched_spec_ids"].split() == _w1404_rep["matched_specs"]
           and _w1404_in["matched_specs"] == len(_w1404_rep["matched_specs"])
           and sorted(_w1404_in["matched_spec_ids"].split())
           == ["WARP-0001", "WARP-0002", "WARP-0003", "WARP-0004"]
           and _w1404_in["observed_low"] == 250000
           and _w1404_in["observed_high"] == 420000)

    expect("WARP-1404 AC3: THE LAYER RECORDS THE TARGET FEATURES IT MATCHED ON, so a "
           "reconciliation can see WHICH spec this range was drawn for and not only what the "
           "range was, and the protected-touch fact uses WARP-1402's declared word rather than a "
           "boolean the front-matter subset cannot hold",
           _w1404_in["target_risk"] == "standard"
           and _w1404_in["target_acceptance_criteria"] == 2
           and _w1404_in["target_regression_surface"] == 2
           and _w1404_in["target_protected_touch"] == E1404.NO
           and _w1404_in["match_radius"] == A1404.MATCH_RADIUS)

    def _w1404_clones(n, tokens=400000):
        """n comparable changes that all cost the SAME, so the only thing that can move the range
        is the small-sample allowance. Holding the observed envelope fixed is the whole point:
        otherwise a narrowing could be an accident of which costs happened to be drawn."""
        return [_w1404_rec("WARP-1%03d" % i, tokens=tokens) for i in range(n)]

    _w1404_by_n = [A1404.analogy(_W1404_TARGET, _W1404_SMALL, _w1404_clones(n))[1]
                   for n in (3, 5, 15)]
    expect("WARP-1404 AC3, THE PROPERTY THE PLAN ASKS FOR: HOLDING THE OBSERVED ACTUALS FIXED, "
           "MORE MATCHED CHANGES GIVE A STRICTLY NARROWER RANGE ON BOTH BOUNDS at every step. "
           "Measured over 3, 5 and 15 identically-costed comparables, so the observed envelope "
           "cannot be what moved and the tightening is attributable to the allowance alone. The "
           "OBSERVED envelope is data and is allowed to widen with history; narrowing THAT as the "
           "sample grows would be manufacturing confidence out of ignorance, which is NG6",
           len(_w1404_by_n) == 3
           and all(r["predicted"] for r in _w1404_by_n)
           and all(_w1404_by_n[i]["low"] < _w1404_by_n[i + 1]["low"]
                   and _w1404_by_n[i]["high"] > _w1404_by_n[i + 1]["high"]
                   for i in range(2))
           and [r["observed_low"] for r in _w1404_by_n] == [400000] * 3
           and [r["observed_high"] for r in _w1404_by_n] == [400000] * 3)

    _w1404_sweep = [A1404.widening_pct(n) for n in range(1, 61)]
    expect("WARP-1404 AC3: THE ALLOWANCE IS NON-INCREASING ACROSS A SWEPT SAMPLE SIZE AND NEVER "
           "REACHES ZERO, floored at the declared minimum, and it is not a constant. A converged "
           "estimator is still an estimator: an allowance that reached zero would be a claim to "
           "have finished converging, which is exactly the false precision this plan forbids. "
           "widening_pct of a non-positive sample RAISES rather than returning a default",
           all(_w1404_sweep[i] >= _w1404_sweep[i + 1] for i in range(len(_w1404_sweep) - 1))
           and min(_w1404_sweep) == A1404.MIN_WIDEN_PCT > 0
           and len(set(_w1404_sweep)) > 3
           and _w1404_raises(A1404.widening_pct, 0)[0]
           and _w1404_raises(A1404.widening_pct, -1)[0])

    _w1404_tiny = A1404.analogy(_W1404_TARGET, _W1404_SMALL, _w1404_clones(40, tokens=900))[1]
    expect("WARP-1404 AC3: BOUNDS LAND ON WARP-1402'S ROUNDING GRID, and rounding is allowed to "
           "coarsen a range and never to collapse it into a point - measured on comparables that "
           "cost 900 tokens each, where the whole range is smaller than one grid step. ONE grid "
           "for both layers on purpose: bounds on two different grids would make the committed "
           "envelope's provenance ambiguous, and a reader could not tell which layer a bound came "
           "from",
           _w1404_tiny["predicted"] is True
           and _w1404_tiny["low"] % E1404.ROUND_STEP == 0
           and _w1404_tiny["high"] % E1404.ROUND_STEP == 0
           and _w1404_tiny["low"] < _w1404_tiny["high"]
           and _w1404_layer["low"] % E1404.ROUND_STEP == 0
           and _w1404_layer["high"] % E1404.ROUND_STEP == 0)

    _w1404_dear = A1404.analogy(_W1404_TARGET, _W1404_BIG, _W1404_SEEDED)
    expect("WARP-1404 AC3 ANTI-VACUITY ON THE WHOLE LAYER: two different targets over the SAME "
           "corpus get DIFFERENT ranges from DIFFERENT cited comparables - the small spec from "
           "the cheap cluster, the big one from the expensive cluster, with no spec appearing in "
           "both. A layer that returned one range whatever it was asked would pass every "
           "stand-down and every provenance assertion above and be worth nothing at all",
           _w1404_dear[0] is not None
           and (_w1404_dear[1]["low"], _w1404_dear[1]["high"])
           != (_w1404_rep["low"], _w1404_rep["high"])
           and _w1404_dear[1]["low"] > _w1404_rep["high"]
           and not (set(_w1404_dear[1]["matched_specs"]) & set(_w1404_rep["matched_specs"]))
           and sorted(_w1404_dear[1]["matched_specs"])
           == ["WARP-0101", "WARP-0102", "WARP-0103"])

    expect("WARP-1404 AC3: THE LAYER AND THE REPORT ARE DETERMINISTIC AND THE EVIDENCE SET IS "
           "ORDERED. Two calls over the same corpus give identical structures, and the matched "
           "list is sorted by distance then spec id, so a record re-derived years later can be "
           "compared to the committed one. Nothing here reads a clock: the date is passed in",
           A1404.analogy(_W1404_TARGET, _W1404_SMALL, _W1404_SEEDED) == (_w1404_layer, _w1404_rep)
           and _w1404_rep["distances"] == sorted(_w1404_rep["distances"])
           and _w1404_raises(A1404.predict, [])[0]
           and "no number at all" in _w1404_raises(A1404.predict, [])[1])

    # ---------------------------------------------------------------------------------------
    # AC4. MODEL IDENTITY WINDOWS THE EVIDENCE, THROUGH THE ONE ERA READER (D5).
    # ---------------------------------------------------------------------------------------
    _W1404_OLD_ERA = {"WARP-0001": ("pre-ledger", None), "WARP-0002": ("pre-ledger", None),
                      "WARP-0003": ("pre-ledger", None), "WARP-0004": ("pre-ledger", None)}
    _w1404_windowed = A1404.analogy(
        _W1404_TARGET, _W1404_SMALL, _W1404_CHEAP,
        era_of=lambda s: _W1404_OLD_ERA.get(s, ("m5", None)), era="m5")
    _w1404_unwindowed = A1404.analogy(_W1404_TARGET, _W1404_SMALL, _W1404_CHEAP)
    expect("WARP-1404 AC4: ACTUALS FROM AN EARLIER MODEL ERA ARE EXCLUDED AND COUNTED, NEVER "
           "BLENDED, and the stand-down names that as the reason. A token stops meaning what it "
           "meant when the model changes, so two numbers either side of a capability shift are "
           "not in the same unit and no conversion factor is invented here. ITS CONTROL: the "
           "identical corpus with NO era window produces a range, so the exclusion is the WINDOW "
           "and not a module that drops records",
           _w1404_windowed[0] is None
           and _w1404_windowed[1]["reason_code"] == "no_same_era_actuals"
           and _w1404_windowed[1]["excluded"]["other_era"] == 4
           and _w1404_windowed[1]["candidates"] == 0
           and "low" not in _w1404_windowed[1]
           and _w1404_unwindowed[0] is not None
           and _w1404_unwindowed[1]["matched"] == 4)

    _w1404_unreadable_era = A1404.analogy(
        _W1404_TARGET, _W1404_SMALL, _W1404_CHEAP, era_of=lambda _s: (None, "unreadable"),
        era="m5")
    expect("WARP-1404 AC4: AN ACTUAL WHOSE ERA CANNOT BE READ IS EXCLUDED AS UNREADABLE AND "
           "COUNTED SEPARATELY from one measured in another era. They are different facts - one "
           "is a timestamp nobody can parse, the other is a model change somebody recorded - and "
           "a reader who cannot tell them apart cannot tell which one to go and fix",
           _w1404_unreadable_era[0] is None
           and _w1404_unreadable_era[1]["excluded"]["unreadable_era"] == 4
           and _w1404_unreadable_era[1]["excluded"]["other_era"] == 0
           and _w1404_unreadable_era[1]["reason_code"] == "no_same_era_actuals")

    expect("WARP-1404 AC4: THE PLANNING ERA IS THE LATEST THE LEDGER DECLARES, and an empty "
           "ledger has none. The same argument WARP-1406's peg makes for the same reason: "
           "planning happens in the era you are in, and an older era keeps its own numbers rather "
           "than being converted into this one",
           A1404.planning_era(N1404.eras([])) == N1404.ERA_UNSTAMPED
           and A1404.planning_era([]) is None
           and A1404.planning_era(N1404.eras([
               {"id": "m5", "at": "2026-08-01T00:00:00Z", "model": "m5",
                "work_per_token": "increased"}])) == "m5")

    # THE END-TO-END LEDGER MEASUREMENT: a hermetic repository root with a real capability-shift
    # record, real spend events either side of it, and real fixture specs. An injected era reader
    # tests the fake; this tests the shipped one.
    # ONE enumeration of the fixture history, used for both the specs and the spend events. Two
    # lists of the same four changes would disagree the first time one was edited, and this
    # repository has a named rule about that.
    _W1404_HISTORY = (("WARP-9501", "2026-07-01T00:00:00Z"),
                      ("WARP-9502", "2026-09-01T00:00:00Z"),
                      ("WARP-9503", "2026-09-02T00:00:00Z"),
                      ("WARP-9504", "2026-09-03T00:00:00Z"))
    _w1404_root = Path(_d) / "erarepo"
    (_w1404_root / ".veldo" / "toe_eras").mkdir(parents=True)
    (_w1404_root / "specs").mkdir()
    for _rel in (".veldo/architecture.yaml", ".veldo/policy.yaml"):
        _w1404_shutil.copy(ROOT / _rel, _w1404_root / _rel)
    for _sid, _when in _W1404_HISTORY:
        (_w1404_root / "specs" / ("%s-fixture.md" % _sid)).write_text(
            _w1404_spec_text(spec_id=_sid, status="shipped"))
    (_w1404_root / "specs" / "WARP-9404-target.md").write_text(_w1404_spec_text())
    (_w1404_root / ".veldo" / "events.jsonl").write_text("".join(
        json.dumps({"schema": "veldo.event/v1", "type": "spec.shipped", "spec_id": _sid,
                    "at": _when, "tokens": 400000 + 10000 * _i, "producer": "selftest"}) + "\n"
        for _i, (_sid, _when) in enumerate(_W1404_HISTORY)))
    _w1404_noledger = A1404.repo_basis(root=_w1404_root)
    _w1404_no_l, _w1404_no_r = A1404.analogy(
        "WARP-9404", _W1404_SMALL, _w1404_noledger[0], era_of=_w1404_noledger[1],
        era=_w1404_noledger[2])
    (_w1404_root / ".veldo" / "toe_eras" / "m5.yaml").write_text(
        "schema: veldo.toe_capability_shift/v1\nid: m5\nat: 2026-08-15T00:00:00Z\n"
        "model: m5\nwork_per_token: increased\n")
    _w1404_ledger = A1404.repo_basis(root=_w1404_root)
    _w1404_l, _w1404_r = A1404.analogy(
        "WARP-9404", _W1404_SMALL, _w1404_ledger[0], era_of=_w1404_ledger[1],
        era=_w1404_ledger[2])
    expect("WARP-1404 AC4 END TO END OVER A REAL LEDGER, not an injected reader: a hermetic "
           "repository root with four shipped fixture specs carrying real spend events, one of "
           "them BEFORE a recorded capability shift. With no ledger the planning era is "
           "pre-ledger and all four are comparables; the moment the shift record exists the "
           "planning era is m5, the pre-shift change is excluded as other_era, and the range is "
           "drawn from the three that remain. This is WARP-1406's shipped era reader doing the "
           "windowing, which is why no second era reader exists here",
           _w1404_noledger[2] == N1404.ERA_UNSTAMPED and _w1404_ledger[2] == "m5"
           and _w1404_no_r["candidates"] == 4 and _w1404_no_r["matched"] == 4
           and _w1404_r["candidates"] == 3 and _w1404_r["matched"] == 3
           and _w1404_r["excluded"]["other_era"] == 1
           and "WARP-9501" in _w1404_no_r["matched_specs"]
           and "WARP-9501" not in _w1404_r["matched_specs"]
           and _w1404_l is not None and _w1404_no_l is not None
           and _w1404_l["inputs"]["era"] == "m5")

    # ---------------------------------------------------------------------------------------
    # AC5. ADOPTION SAFE, ADVISORY, AND IT CAN ONLY EVER WIDEN WHAT W2 COMMITTED.
    # ---------------------------------------------------------------------------------------
    _w1404_fix = tmpfile(_d, "WARP-9404-fixture.md", _w1404_spec_text())
    _w1404_w2only = E1404.propose(_w1404_fix, _W1404_AT)
    _w1404_standrec, _w1404_standrep = A1404.augment(_w1404_fix, _W1404_AT, _W1404_NOSPEND)
    expect("WARP-1404 AC5, THE ADOPTION-SAFETY EQUALITY: ON A STAND-DOWN THE RECORD THIS MODULE "
           "PRODUCES IS BYTE-IDENTICAL TO THE ONE estimate.propose PRODUCES ALONE. Asserted on "
           "the rendered BYTES and not only on the dict, because bytes are what gets committed "
           "beside a spec. Adding this layer to a repository with no recorded actuals changes "
           "nothing at all about what is written, which is the only posture under which a "
           "calibrating layer can be added to a working loop",
           _w1404_standrec == _w1404_w2only
           and E1404.render_record(_w1404_standrec) == E1404.render_record(_w1404_w2only)
           and _w1404_standrep["predicted"] is False
           and [l["layer"] for l in _w1404_standrec["layers"]] == ["structural_proxy"]
           and _w1404_standrec["calibration"] == "uncalibrated")

    _w1404_bothrec, _w1404_bothrep = A1404.augment(_w1404_fix, _W1404_AT, _W1404_SEEDED)
    _w1404_proxy = _w1404_w2only["layers"][0]
    expect("WARP-1404 AC5: WITH THE LAYER PRESENT THE COMMITTED RANGE IS THE ENVELOPE OF BOTH "
           "LAYERS AND IS NEVER NARROWER THAN THE PROXY'S OWN ON EITHER BOUND, recomputed through "
           "the real combine() and validated by the real validate_record. This module can only "
           "ever WIDEN what W2 committed: superseding the prior would narrow the range, and the "
           "only thing that could justify a narrowing is W5's measurement that the analogy is "
           "actually more accurate, which does not exist yet. A narrowing taken on an argument "
           "rather than a measurement is the false precision this plan forbids",
           E1404.validate_record(_w1404_bothrec) == []
           and [l["layer"] for l in _w1404_bothrec["layers"]]
           == ["structural_proxy", "historical_analogy"]
           and (_w1404_bothrec["low"], _w1404_bothrec["high"])
           == E1404.combine(_w1404_bothrec["layers"], _w1404_bothrec["combination"])
           and _w1404_bothrec["low"] <= _w1404_proxy["low"]
           and _w1404_bothrec["high"] >= _w1404_proxy["high"])

    expect("WARP-1404 AC5: THE CALIBRATION FLIPS TO calibrated ONLY BECAUSE A CORPUS-GROUNDED "
           "BASIS IS PRESENT, derived by WARP-1402 and never asserted here, with the stand-down "
           "record reading uncalibrated over the identical spec. That is the one honest claim "
           "this layer adds to the plan: a record says it is calibrated when, and only when, some "
           "part of it came from something that actually happened",
           _w1404_bothrec["calibration"] == "calibrated"
           and _w1404_standrec["calibration"] == "uncalibrated"
           and E1404.calibration_of(_w1404_bothrec["layers"]) == "calibrated"
           and E1404.parse_record(E1404.render_record(_w1404_bothrec)) == _w1404_bothrec)

    _w1404_before = sorted(p.name for p in Path(_d).iterdir())
    A1404.augment(_w1404_fix, _W1404_AT, _W1404_SEEDED)
    A1404.analogy(_W1404_TARGET, _W1404_SMALL, _W1404_SEEDED)
    _w1404_after = sorted(p.name for p in Path(_d).iterdir())
    _w1404_src = (ROOT / ".veldo/toe_analogy.py").read_text()
    expect("WARP-1404 AC5: THIS MODULE HAS NO WRITER AT ALL, measured as a behaviour and stated "
           "as a text property. Driving the whole surface leaves the working directory "
           "unchanged, and the source names no write_text, no open-for-write, no mkdir, no "
           "subprocess, no socket and no urllib, so it cannot write, spawn a process or open a "
           "connection, and it declares no daemon or timer (NG5)",
           _w1404_before == _w1404_after
           and all(tok not in _w1404_src for tok in (
               "write_text", "mkdir(", "import subprocess", "import socket", "import urllib",
               "Popen(", '"w"', "'w'")))

    _W1404_MALFORMED = (
        ("not a list", "not a list"),
        ("must be a mapping", ["nope"]),
        ("reasons from", [dict(_w1404_plain, schema="veldo.something_else/v1")]),
        ("names no spec", [{k: v for k, v in _w1404_plain.items() if k != "spec"}]),
        ("no `features` mapping", [{k: v for k, v in _w1404_plain.items() if k != "features"}]),
        ("appears in 2 records", [_w1404_plain, dict(_w1404_plain)]),
    )
    _w1404_refusals = [_w1404_raises(A1404.refuse_malformed, c) for _needle, c
                       in _W1404_MALFORMED]
    expect("WARP-1404 AC5: A MALFORMED CORPUS IS REFUSED BY NAME, six shapes and each message "
           "naming what is wrong: not a list, a record that is not a mapping, the wrong schema, "
           "no spec id, no features block, and a duplicated spec. A record quietly skipped makes "
           "a smaller evidence set look complete, and an evidence set is exactly the thing "
           "somebody quotes without asking how big it was. Bound to the length of its own literal "
           "table, so emptying it reds this instead of passing over nothing",
           len(_W1404_MALFORMED) == 6
           and all(r[0] for r in _w1404_refusals)
           and all(_W1404_MALFORMED[i][0] in _w1404_refusals[i][1]
                   for i in range(len(_W1404_MALFORMED))))

    _w1404_mixed = list(_W1404_CHEAP) + list(_W1404_NOSPEND) + [
        _w1404_rec("WARP-0601", risk="apocalyptic", tokens=700000),
        _w1404_rec("WARP-0602", tokens=0)]
    _w1404_mixedrep = A1404.analogy(_W1404_TARGET, _W1404_SMALL, _w1404_mixed)[1]
    expect("WARP-1404 AC5 THE PARTNER OF THAT REFUSAL: a WELL-FORMED but UNUSABLE record is "
           "COUNTED AND NAMED, never refused. Three with no spend, one whose tier cannot be read "
           "and one whose recorded spend is zero are each counted under their own exclusion while "
           "the four usable ones still produce a range. Absence stands down; breakage speaks up. "
           "A module that refused the unusable would make one unrecorded change take the whole "
           "layer down, and a module that skipped the malformed would hide it",
           A1404.refuse_malformed(_w1404_mixed) is _w1404_mixed
           and _w1404_mixedrep["predicted"] is True
           and _w1404_mixedrep["matched"] == 4
           and _w1404_mixedrep["excluded"]["no_spend"] == 3
           and _w1404_mixedrep["excluded"]["unreadable_features"] == 1
           and _w1404_mixedrep["excluded"]["zero_tokens"] == 1
           and _w1404_mixedrep["candidates"] == 4
           and set(A1404.EXCLUSIONS) == set(_w1404_mixedrep["excluded"])
           and len(A1404.EXCLUSIONS) == 6)

    # THE MEASUREMENT OVER THIS REPOSITORY, and the control that makes it attributable. The
    # target is THIS spec's own features, read through the shipped reader, because the honest
    # question is what an analogy layer would say about the work in hand.
    #
    # THE CONTROL PLANTS SPEND EVENTS, NOT CORPUS RECORDS, and the difference is not cosmetic:
    # the first draft of this control set `spend_recorded` on six corpus records directly and
    # the layer still stood down, because the ERA of an actual is read from the timestamps of
    # the events that carried its spend, and those events did not exist. That was the control
    # being unfaithful rather than the module being wrong - a corpus record's spend is DERIVED
    # from the event stream, so a repository cannot reach the state the first draft planted. It
    # now appends the events .veldo/spend.py would emit and REBUILDS the corpus and the era
    # reader from them, which exercises the whole shipped path.
    _w1404_real = A1404.repo_basis()
    _w1404_selfvec = A1404.vector(A1404.target_features(
        ROOT / "specs/WARP-1404-historical-analogy.md",
        protected=E1404.protected_paths(ROOT)))
    _w1404_realrep = A1404.analogy(
        "WARP-1404", _w1404_selfvec, _w1404_real[0],
        era_of=_w1404_real[1], era=_w1404_real[2])[1]
    _w1404_ranked = sorted(
        (r for r in _w1404_real[0] if A1404.vector(r["features"]) is not None),
        key=lambda r: (A1404.distance(_w1404_selfvec, A1404.vector(r["features"])), r["spec"]))
    _w1404_plant_ids = [r["spec"] for r in _w1404_ranked[:6]]
    _w1404_plant_events = N1404.read_events(ROOT / ".veldo" / "events.jsonl") + [
        {"schema": "veldo.event/v1", "type": "spec.shipped", "spec_id": _sid,
         "at": "2026-08-0%dT00:00:00Z" % (_i + 1), "tokens": 500000 + 10000 * _i,
         "cost_usd": 1.0, "producer": "selftest", "spend_basis": "harness_reported"}
        for _i, _sid in enumerate(_w1404_plant_ids)]
    _w1404_planted = TC1404.build(specs_dir=ROOT / "specs", events=_w1404_plant_events,
                                 protected=E1404.protected_paths(ROOT))
    _w1404_plantedrep = A1404.analogy(
        "WARP-1404", _w1404_selfvec, _w1404_planted,
        era_of=lambda s: N1404.era_of(s, _w1404_plant_events, N1404.eras([]), TC1404,
                                      M1404.parse_iso),
        era=_w1404_real[2])[1]
    expect("WARP-1404 AC5 MEASURED OVER THIS REPOSITORY: the corpus is NOT empty (%d shipped "
           "records) and yet this layer stands down as no_recorded_actuals with NO bound of any "
           "kind, because not one record carries recorded token spend - WARP-1401 measured 0 "
           "percent spend coverage and .veldo/spend.py has never been used. AND THE CONTROL THAT "
           "MAKES THAT ATTRIBUTABLE: planting spend on records of this repository's OWN corpus "
           "makes the SAME call produce a range, so the stand-down is the missing emitter and not "
           "something else about this repository's specs"
           % len(_w1404_real[0]),
           len(_w1404_real[0]) > 100
           and _w1404_realrep["predicted"] is False
           and _w1404_realrep["reason_code"] == "no_recorded_actuals"
           and "low" not in _w1404_realrep and "high" not in _w1404_realrep
           and _w1404_realrep["excluded"]["no_spend"] == len(_w1404_real[0])
           and _w1404_realrep["candidates"] == 0
           and len(_w1404_plant_ids) == 6
           and _w1404_plantedrep["predicted"] is True
           and _w1404_plantedrep["matched"] >= A1404.MIN_MATCHES
           and _w1404_plantedrep["low"] < _w1404_plantedrep["high"]
           and set(_w1404_plantedrep["matched_specs"]) <= set(_w1404_plant_ids))

    _w1404_cli = subprocess.run(
        [sys.executable, str(ROOT / ".veldo/toe_analogy.py"), "report",
         "--spec", str(ROOT / "specs/WARP-1404-historical-analogy.md")],
        capture_output=True, text=True, cwd=str(ROOT))
    expect("WARP-1404 AC5: THE CLI STANDS DOWN AND EXITS 0, driven as a real process over this "
           "repository, saying STANDING DOWN, printing no range, and saying in words that this is "
           "not a finding. A tool that exited non-zero on the absence of evidence would turn an "
           "advisory estimator into a gate the first time somebody wired it into a script, which "
           "is precisely NG1",
           _w1404_cli.returncode == 0
           and "STANDING DOWN" in _w1404_cli.stdout
           and "not a finding" in _w1404_cli.stdout
           and "no number produced" in _w1404_cli.stdout)

    _w1404_gate = (ROOT / "scripts/verify.sh").read_text()
    _w1404_slots = [s for s in _w1404_gate.splitlines() if s.startswith("CHECK_")]
    expect("WARP-1404 AC5: NOTHING IN THE GATE NAMES THIS MODULE. scripts/verify.sh declares no "
           "slot mentioning toe_analogy.py, and neither does the contract validator it runs, so "
           "no path through the gate can refuse, block or delay work on an estimate. Bound to a "
           "non-empty slot list, so a parse that found no slots reds this rather than passing "
           "over nothing",
           _w1404_slots != [] and all("analogy" not in s for s in _w1404_slots)
           and "toe_analogy" not in _w1404_gate
           and "toe_analogy" not in (ROOT / ".veldo/validate.py").read_text())

    # The real contract validator over a hermetic root, three ways, exactly as WARP-1402 proves
    # it: an estimate beside a spec can never invalidate the spec.
    _w1404_vroot = Path(_d) / "vrepo"
    (_w1404_vroot / ".veldo" / "estimates").mkdir(parents=True)
    (_w1404_vroot / "specs").mkdir()
    for _rel in (".veldo/architecture.yaml", ".veldo/policy.yaml"):
        _w1404_shutil.copy(ROOT / _rel, _w1404_vroot / _rel)
    _w1404_vspec = _w1404_vroot / "specs" / "WARP-9404-fixture.md"
    _w1404_vspec.write_text(_w1404_spec_text())
    _w1404_before_est = V.check_spec(_w1404_vspec, repo_root=_w1404_vroot)
    E1404.write_record(_w1404_bothrec, dirpath=_w1404_vroot / ".veldo" / "estimates")
    _w1404_after_est = V.check_spec(_w1404_vspec, repo_root=_w1404_vroot)
    _w1404_badspec = _w1404_vroot / "specs" / "WARP-9405-broken.md"
    _w1404_badspec.write_text(_w1404_spec_text(spec_id="WARP-9405").replace(
        "status: ready", "status: donezo"))
    expect("WARP-1404 AC5: AN ESTIMATE CARRYING THIS LAYER CANNOT INVALIDATE A SPEC, measured by "
           "driving the real validate.check_spec over a hermetic repository root before and after "
           "the calibrated record is written beside the spec by the real writer, and getting the "
           "identical 0. WITH THE NEGATIVE CONTROL that the same validator over the same root "
           "DOES refuse a genuinely broken spec, without which the two zeros would be a pass "
           "earned by looking nowhere",
           (_w1404_before_est, _w1404_after_est) == (0, 0)
           and V.check_spec(_w1404_badspec, repo_root=_w1404_vroot) > 0)

    expect("WARP-1404 AC5: THE MODULE IS BYTE-IDENTICAL IN BOTH ENGINE HOMES, so what "
           "/veldo:init lays down for an adopter is the module this repository runs and proves. "
           "The layer three later surfaces will read is exactly the thing that must not exist in "
           "two slightly different spellings",
           (ROOT / ".veldo/toe_analogy.py").read_bytes()
           == (ROOT / "engine/.veldo/toe_analogy.py").read_bytes())

del _w1404_shutil
