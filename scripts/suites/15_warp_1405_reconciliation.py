"""WARP-1405: reconciliation and the estimator's own accuracy, and why each check can fail.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, which always
runs, so its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 15_warp_1405_reconciliation

WHAT IS OBSERVED HERE, AND HOW. The subject is a ledger schema plus three derivations over it,
so the shape is negative-first like every suite in this repository: each planted-bad record must
be REFUSED and each refusal is paired with the positive control that the same record validates
once corrected, because a validator that refuses everything satisfies every negative assertion
and is worthless. The derivations get the same treatment in the other direction: every claim
that recalibration HELPS is paired with a control where it must NOT claim to help.

THE ASSERTIONS WERE WATCHED FAILING, not assumed to bite. THIRTEEN properties of the module were
broken on purpose and the reds recorded, one mutation at a time, both copies of the module
mutated together so every red is attributable to BEHAVIOUR rather than to engine drift, each
restored before the next (53 of 53 green restored). Mutations 1 to 6 were driven when this
fragment was built; 7 to 13 were driven at the review that found four of the assertions below
green under mutation, and the counts for 1, 2 and 3 were RE-MEASURED then rather than carried
over:

  1. `error_pct_of` returning 0 always: 8 RED. The derived-variance refusal, the three-case
     variance property, the planted-bias accuracy, the bias-versus-counts ledger, the
     bias-reduction claim, the population pairing and its negative control, and the EXAMPLE
     RECORD on disk. That last one is the instructive red: a mutation which makes the builder
     and the validator agree with each other is invisible to any in-memory fixture, and what
     catches it is a real file whose numbers were computed and committed by the unmutated code.
  2. `outcome_of` calling everything `in_range`: 10 RED, the widest blast radius in the fragment,
     including the anti-vacuity control that three DISTINCT outcomes appear, the trailing
     window, both curve assertions, the bias direction and the example record. The bounds
     refusals stayed GREEN, which is what makes those attributable to the bounds rule rather
     than to this derivation.
  3. dropping the MIN_FITTED_SPREAD_PCT floor from `recalibrated_range`: 2 RED, the floor
     assertion and the layer-inputs assertion, the latter through the `spread_floor_applied`
     flag it pins rather than through the bounds (the recomputation below follows the RECORDED
     flag, so it reproduces the unfloored bounds correctly and the flag is what disagrees).
     Nothing else moved, so the floor is measured rather than incidental: it is the check that
     stops five records which happen to agree from licensing a range one rounding step wide.
  4. `fit` ignoring its `exclude` argument: 1 RED, the leave-one-out assertion, and NOTHING
     ELSE in the fragment noticed. That is exactly why that assertion exists: in-sample scoring
     is a refit grading its own homework, and it looks identical to a working measurement from
     every other angle.
  5. `accuracy([])` reporting a hit rate of 0 instead of `measured: False`: 3 RED, the
     empty-ledger honesty pair, the real-repository measurement, and the inspectable surface
     driven as a real process. The load-bearing honesty of this item is that an unmeasured
     estimator says so, and a zero there reads as "it missed every time".
  6. `write_record` silently overwriting a differing record: 1 RED, the regrade refusal, while
     the idempotence assertion (identical bytes report `unchanged`) stayed GREEN. The pair
     separates two things one flag would confuse: writing the same measurement twice is free,
     and rewriting a recorded measurement is refused.
  7. `compare` scoring the prior over the WHOLE ledger instead of over the records the refit
     actually scored (`paired_before = accuracy(records)`): 1 RED, the population assertion.
     That mutation is the code AS SHIPPED before this remediation, and it is why that assertion
     exists: over a ledger mixing records that carry a structural proxy with records that do
     not, it published "mean absolute error 300 to 0 percent" and `improved: True` between two
     different populations, on a ledger where the refit provably changed nothing.
  8. `holdout` dropping a never-fittable record instead of skipping it with a reason: 1 RED, the
     same population assertion, through the unpaired list and the scored-plus-skipped count. A
     record in NEITHER list is a population nobody can see the size of.
  9. the refitted layer recording an envelope 3x and 7x wrong
     (`fitted_scale_low * 3, fitted_scale_high * 7`): 1 RED, the layer-inputs assertion. This
     mutation was GREEN before this remediation, because that assertion recomputed the bounds by
     CALLING the function that produced them, handed the same fit object.
 10. the layer recording a widening ratio 25 points too high (`half_spread_pct + 25`): 1 RED,
     the same assertion. That number was recorded NOWHERE before this remediation, and without
     it a floored layer's own inputs reproduced a POINT against real bounds hundreds of
     thousands of tokens apart.
 11. `bias` derived from the sign of the mean error instead of from the counts: 1 RED, the
     bias-versus-counts assertion. GREEN before this remediation, because the only ledger bias
     was asserted over had every actual on one side, where the counts and the mean cannot
     disagree.
 12. `check_dir`'s validation loop replaced by `pass`: 1 RED, the present-but-broken check
     assertion. GREEN before this remediation, when the only directory check_dir was ever
     pointed at was an ABSENT one.
 13. `fit`'s own reason appended with "VERDICT: the structure is WRONG and no scale will fix
     it": 1 RED, the never-labels assertion. GREEN before this remediation, when that assertion
     read the fit dict's KEY NAMES and never a string a reader sees.

WHAT IS MEASURED RATHER THAN ARGUED. Two things. First, that this repository has NO measured
estimator accuracy: the live event log is read and required to carry no spend field at all,
which is WARP-1401's finding re-measured against today's bytes, and the paired control requires
the same predicate to FIND spend in a seeded event so the zero is the log's doing. Second, that
a reconciliation can never invalidate a spec: the REAL validate.check_spec runs over a hermetic
repository root three times, with no record, with a valid one and with a MALFORMED one, and must
return the identical zero, with the negative control that it DOES refuse a genuinely broken spec
under the same root.
"""
import re as _w1405_re
import shutil as _w1405_shutil

_w1405_spec = importlib.util.spec_from_file_location(
    "w1405_toe_reconcile", ROOT / ".veldo" / "toe_reconcile.py")
R1405 = importlib.util.module_from_spec(_w1405_spec)
_w1405_spec.loader.exec_module(R1405)

_w1405_espec = importlib.util.spec_from_file_location(
    "w1405_estimate", ROOT / ".veldo" / "estimate.py")
E1405 = importlib.util.module_from_spec(_w1405_espec)
_w1405_espec.loader.exec_module(E1405)

_w1405_cspec = importlib.util.spec_from_file_location(
    "w1405_toe_corpus", ROOT / ".veldo" / "toe_corpus.py")
C1405 = importlib.util.module_from_spec(_w1405_cspec)
_w1405_cspec.loader.exec_module(C1405)

_w1405_mspec = importlib.util.spec_from_file_location(
    "w1405_metrics", ROOT / ".veldo" / "metrics.py")
M1405 = importlib.util.module_from_spec(_w1405_mspec)
_w1405_mspec.loader.exec_module(M1405)


def _w1405_probs(rec, spec_id=None):
    """Every problem with one record, joined, so an assertion can require the refusal to NAME
    what is wrong. A bare boolean would pass on any refusal at all, including an unrelated one."""
    return " | ".join(R1405.validate_record(rec, spec_id=spec_id))


def _w1405_raises(fn, *a, **kw):
    """(raised, message). The message is returned because that is what carries the refusal: an
    assertion that something raised, without checking WHAT, passes on a stray TypeError."""
    try:
        fn(*a, **kw)
    except BaseException as e:
        return True, "%s: %s" % (type(e).__name__, e)
    return False, ""


def _w1405_spec_text(spec_id, risk="standard", acs=2, status="shipped",
                     footprint=(".veldo/nothing_a.py",)):
    """A fixture spec with exactly the mechanical features under test, built rather than pinned
    because the refit assertions need specs that differ in ONE feature and therefore in weight."""
    lines = ["---", "schema: veldo.spec/v1", "id: %s" % spec_id,
             "title: reconciliation fixture", "status: %s" % status, "risk: %s" % risk,
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


def _w1405_corpus_row(spec_id, tokens, recorded=True):
    """One corpus record of the shape WARP-1401 builds, carrying only what this item reads."""
    return {"schema": "veldo.toe_actuals/v1", "spec": spec_id,
            "features": {}, "cycles": {}, "git": {},
            "spend": {"tokens": tokens, "cost_usd": 0.0, "human_minutes": 0,
                      "spend_recorded": recorded}}


_W1405_COMMITTED = "2026-08-01"
_W1405_AT = "2026-08-10"
# The planted systematic bias: every actual comes in at this multiple of the estimate's own
# structural point, which is the shape a wrong SCALE takes (the structure ranks the work
# correctly, every number is uniformly too small).
_W1405_BIAS = 3

with tempfile.TemporaryDirectory() as _d:
    _w1405_ests, _w1405_actuals, _w1405_weights = {}, {}, {}
    for _i, _acs in enumerate((1, 2, 3, 5, 8), start=1):
        _sid = "WARP-9411" if _i == 1 else "WARP-941%d" % _i
        _p = tmpfile(_d, "%s.md" % _sid, _w1405_spec_text(_sid, acs=_acs))
        _est = E1405.propose(_p, _W1405_COMMITTED)
        _w = _est["layers"][0]["inputs"]["structural_weight_tenths"]
        _w1405_ests[_sid] = _est
        _w1405_weights[_sid] = _w
        _w1405_actuals[_sid] = (_w * E1405.TOKENS_PER_STRUCTURAL_UNIT // 10) * _W1405_BIAS
    _W1405_SPECS = sorted(_w1405_ests)
    _w1405_corpus = [_w1405_corpus_row(s, _w1405_actuals[s]) for s in _W1405_SPECS]
    _W1405_LEDGER, _w1405_stand = R1405.pair(_w1405_ests, _w1405_corpus, _W1405_AT)
    _W1405_ONE = _W1405_LEDGER[0]

    # -----------------------------------------------------------------------------------
    # AC1. THE RECORD, AND WHY ITS DERIVED FIELDS CANNOT LIE.
    # -----------------------------------------------------------------------------------
    expect("WARP-1405 AC1 POSITIVE CONTROL: the record the reconciler derives from a real "
           "committed estimate and a recorded actual validates CLEAN, carries the estimate, the "
           "actual and the variance, and round trips through the ONE parser byte for byte. Every "
           "refusal below is therefore a refusal of the MUTATION and not of the shape in general, "
           "which is the only way a negative-first fragment proves anything",
           R1405.validate_record(_W1405_ONE, spec_id=_W1405_ONE["spec"]) == []
           and _W1405_ONE["unit"] == "tokens"
           and (_W1405_ONE["estimate_low"], _W1405_ONE["estimate_high"])
           == (_w1405_ests[_W1405_ONE["spec"]]["low"], _w1405_ests[_W1405_ONE["spec"]]["high"])
           and _W1405_ONE["actual"] == _w1405_actuals[_W1405_ONE["spec"]]
           and R1405.parse_record(R1405.render_record(_W1405_ONE)) == _W1405_ONE)

    expect("WARP-1405 AC1: THE OUTCOME IS DERIVED AND A KINDER ONE IS REFUSED BY NAME. Filing an "
           "above-range actual as in_range is rejected with the computed outcome in the message. "
           "The outcome is what a hit rate counts, so a record able to relabel its own outcome "
           "would let an estimator improve its grade after the fact by editing one word",
           "kinder one" in _w1405_probs(dict(_W1405_ONE, outcome="in_range"))
           and "kinder one" in _w1405_probs(dict(_W1405_ONE, outcome="below")))

    expect("WARP-1405 AC1: THE VARIANCE IS DERIVED AND AN EDITED ONE IS REFUSED BY NAME, with "
           "both the claimed percentage and the computed one in the message. This is the check "
           "that makes the ledger a measurement rather than a scoreboard: the whole learning "
           "loop rests on a variance nobody could adjust once the actual was known",
           "it is DERIVED, measured against the bound" in _w1405_probs(
               dict(_W1405_ONE, error_pct=0))
           and str(_W1405_ONE["error_pct"]) in _w1405_probs(dict(_W1405_ONE, error_pct=1)))

    expect("WARP-1405 AC1: THE VARIANCE IS MEASURED AGAINST THE BOUND THE ACTUAL MISSED, and it "
           "is ZERO inside the range. Driven over the three cases directly: an actual above the "
           "high is positive, below the low is negative, and inside is exactly 0. A midpoint "
           "would be the point estimate this schema refuses to have (NG6), so grading against "
           "one would smuggle it back in through the scorer",
           R1405.error_pct_of(100000, 200000, 300000) == 50
           and R1405.error_pct_of(100000, 200000, 50000) == -50
           and R1405.error_pct_of(100000, 200000, 150000) == 0
           and R1405.outcome_of(100000, 200000, 150000) == R1405.HIT)

    expect("WARP-1405 AC1: THE IMPLIED SCALE AND THE SCALE ERROR ARE DERIVED, and an edited one "
           "is refused by name. These two are the fields a refit is fitted from, so a record "
           "that could carry an implied scale its own weight and actual do not support would "
           "poison every future estimate rather than just misreport one past one",
           "it is DERIVED, and it is the number a refit is fitted from" in _w1405_probs(
               dict(_W1405_ONE, implied_scale=_W1405_ONE["implied_scale"] + 1))
           and "how a wrong SCALE is told apart from a wrong STRUCTURE" in _w1405_probs(
               dict(_W1405_ONE, scale_error_pct=_W1405_ONE["scale_error_pct"] + 1)))

    expect("WARP-1405 AC1: A POINT ESTIMATE CANNOT BE RECONCILED, and the refusal comes from "
           "estimate.py's ONE bounds rule rather than from a second spelling of it here: low "
           "equal to high is named a POINT and an inverted pair is named inverted. A reconciler "
           "that accepted a point range would be scoring an estimate the estimate schema itself "
           "refuses to hold",
           "POINT" in _w1405_probs(dict(_W1405_ONE,
                                        estimate_high=_W1405_ONE["estimate_low"]))
           and "inverted" in _w1405_probs(dict(_W1405_ONE,
                                               estimate_low=_W1405_ONE["estimate_high"] + 1)))

    expect("WARP-1405 AC1: AN ACTUAL THAT IS NOT A POSITIVE INTEGER IS REFUSED, never rounded "
           "and never defaulted. A string, a float and a zero are each refused with the reason "
           "named. A zero actual is the ABSENCE of a measurement rather than a very cheap "
           "change, and the two must not arrive at the same number",
           all("never rounds, rescales or defaults" in _w1405_probs(dict(_W1405_ONE, actual=v))
               for v in ("lots", 0, -5))
           and "must be a positive integer" in _w1405_probs(dict(_W1405_ONE, actual=0)))

    expect("WARP-1405 AC1: A RECONCILIATION DATED BEFORE THE ESTIMATE IT SCORES IS REFUSED BY "
           "NAME. An estimate written after the work was already reconciled is not a commitment, "
           "and scoring one would flatter the estimator with hindsight, which is precisely the "
           "failure legacy points never noticed they had",
           "flatter the estimator with hindsight" in _w1405_probs(
               dict(_W1405_ONE, reconciled_at="2026-07-01")))

    expect("WARP-1405 AC1: THE CLOSED VOCABULARIES ARE CLOSED. An unknown top-level key, an "
           "unknown outcome, a unit outside estimate.py's declared set, an unknown actual_source "
           "and a calibration outside estimate.py's set are each refused with the declared set "
           "in the message. The unit and calibration vocabularies are READ FROM estimate.py, so "
           "this ledger cannot drift into a second spelling of either",
           "unknown key(s)" in _w1405_probs(dict(_W1405_ONE, confidence=90))
           and "outcome must be one of" in _w1405_probs(dict(_W1405_ONE, outcome="fine"))
           and "unit must be one of" in _w1405_probs(dict(_W1405_ONE, unit="story_points"))
           and "provenance" in _w1405_probs(dict(_W1405_ONE, actual_source="somewhere"))
           and "estimate_calibration must be one of" in _w1405_probs(
               dict(_W1405_ONE, estimate_calibration="probably")))

    expect("WARP-1405 AC1: A HALF-PRESENT BLOCK IS REFUSED BY NAME, for the features and for the "
           "structure-and-scale pair, each message listing what is given and what is missing. "
           "All or none, because a refit reads exactly those four keys: a record missing one of "
           "them would contribute nothing to a fit while looking complete on the page",
           "half present" in _w1405_probs(
               {k: v for k, v in _W1405_ONE.items() if k != "risk"})
           and "half present" in _w1405_probs(
               {k: v for k, v in _W1405_ONE.items() if k != "declared_scale"}))

    expect("WARP-1405 AC1: A RECORD FILED UNDER THE WRONG NAME IS REFUSED, naming both the "
           "filename it is filed as and the spec it claims, because the filename is the key and "
           "that is what makes two reconciliations of one spec impossible",
           "the filename is the key" in _w1405_probs(_W1405_ONE, spec_id="WARP-9999")
           and _w1405_probs(_W1405_ONE, spec_id=_W1405_ONE["spec"]) == "")

    expect("WARP-1405 AC1: THE RENDERER REFUSES A VALUE THAT WOULD NOT READ BACK AS ITSELF, by "
           "name, using estimate.py's ONE scalar renderer: a multi-line note, a note that is a "
           "string of digits (which reads back as an integer) and one opening with a bracket "
           "(which reads back as a list). Refused at write time, because the alternative is a "
           "ledger that parses into numbers nobody wrote",
           all(_w1405_raises(R1405.render_record, dict(_W1405_ONE, note=n))[0]
               and "refusing to render" in _w1405_raises(
                   R1405.render_record, dict(_W1405_ONE, note=n))[1]
               for n in ("two\nlines", "12345", "[not, a, list]")))

    expect("WARP-1405 AC1 NEGATIVE CONTROL ON THE VALIDATOR'S TIGHTNESS: an OPTIONAL key set to "
           "another legal value is ACCEPTED, and so is a record with no era and no note at all. "
           "A validator that reds on any edit proves nothing about which edit was wrong",
           R1405.validate_record(dict(_W1405_ONE, note="a different one-line note")) == []
           and R1405.validate_record(dict(_W1405_ONE, era="model-era-1")) == []
           and R1405.validate_record({k: v for k, v in _W1405_ONE.items()
                                      if k not in ("era", "note")}) == [])

    # The committed example record: real bytes on disk, not a fixture built in this file.
    _w1405_ex = ROOT / ".veldo/examples/toe-reconciliation-example.yaml"
    _w1405_ex_engine = ROOT / "engine/.veldo/examples/toe-reconciliation-example.yaml"
    _w1405_ex_rec = R1405.parse_record(_w1405_ex.read_text())
    expect("WARP-1405 AC1: THE COMMITTED EXAMPLE RECORD IS VALID AND ITS DERIVED FIELDS ARE "
           "RECOMPUTED HERE RATHER THAN READ, over real bytes on disk. This is the assertion that "
           "catches a mutation which makes the builder and the validator agree with each other: "
           "the file's numbers were computed by the unmutated code and committed, so they are "
           "evidence no in-memory fixture can be. Its engine twin is byte-identical, because that "
           "is what /veldo:init lays down for an adopter",
           R1405.validate_record(_w1405_ex_rec, spec_id="WARP-9402") == []
           and _w1405_ex_rec["outcome"] == R1405.outcome_of(
               _w1405_ex_rec["estimate_low"], _w1405_ex_rec["estimate_high"],
               _w1405_ex_rec["actual"])
           and _w1405_ex_rec["error_pct"] == R1405.error_pct_of(
               _w1405_ex_rec["estimate_low"], _w1405_ex_rec["estimate_high"],
               _w1405_ex_rec["actual"])
           and _w1405_ex_rec["implied_scale"] == R1405.implied_scale_of(
               _w1405_ex_rec["actual"], _w1405_ex_rec["structural_weight_tenths"])
           and _w1405_ex.read_bytes() == _w1405_ex_engine.read_bytes())

    expect("WARP-1405 AC1: THE MODULE IS BYTE-IDENTICAL IN BOTH ENGINE HOMES, so what "
           "/veldo:init lays down for an adopter is the module this repository runs and proves. A "
           "ledger three surfaces read is exactly the thing that must not exist in two slightly "
           "different spellings",
           (ROOT / ".veldo/toe_reconcile.py").read_bytes()
           == (ROOT / "engine/.veldo/toe_reconcile.py").read_bytes())

    # -----------------------------------------------------------------------------------
    # AC2. EXACTLY ONCE, IDEMPOTENTLY, AND EVERY UNRECONCILED ESTIMATE EXPLAINED.
    # -----------------------------------------------------------------------------------
    expect("WARP-1405 AC2 POSITIVE CONTROL: pairing five committed estimates against five "
           "recorded actuals gives five records, no standdowns, in spec order, and doing it "
           "twice gives an IDENTICAL list. Nothing reads a clock (the date is passed in), which "
           "is what makes writing them idempotent rather than merely usually idempotent",
           len(_W1405_LEDGER) == 5 and _w1405_stand == []
           and [r["spec"] for r in _W1405_LEDGER] == _W1405_SPECS
           and R1405.pair(_w1405_ests, _w1405_corpus, _W1405_AT)[0] == _W1405_LEDGER)

    _w1405_wdir = Path(_d) / "written"
    _w1405_first = R1405.write_all(_W1405_LEDGER, dirpath=_w1405_wdir)
    _w1405_again = R1405.write_all(_W1405_LEDGER, dirpath=_w1405_wdir)
    expect("WARP-1405 AC2, THE IDEMPOTENCE THAT MAKES 'EXACTLY ONCE' TRUE: the first pass creates "
           "five records, the second creates NOTHING and reports all five unchanged, and the "
           "directory holds exactly five files afterwards. So the reconciliation pass needs no "
           "bookkeeping about whether it already ran, which is the only way a step at ship time "
           "survives contact with re-runs, retries and two agents landing the same day",
           (len(_w1405_first[0]), len(_w1405_first[1]), len(_w1405_first[2])) == (5, 0, 0)
           and (len(_w1405_again[0]), len(_w1405_again[1]), len(_w1405_again[2])) == (0, 5, 0)
           and len(list(_w1405_wdir.glob("*.yaml"))) == 5
           and R1405.write_record(_W1405_ONE, dirpath=_w1405_wdir)[1] == "unchanged")

    _w1405_moved = dict(_W1405_ONE, actual=_W1405_ONE["actual"] + 1000)
    _w1405_moved["outcome"] = R1405.outcome_of(_w1405_moved["estimate_low"],
                                               _w1405_moved["estimate_high"],
                                               _w1405_moved["actual"])
    _w1405_moved["error_pct"] = R1405.error_pct_of(_w1405_moved["estimate_low"],
                                                  _w1405_moved["estimate_high"],
                                                  _w1405_moved["actual"])
    _w1405_moved["implied_scale"] = R1405.implied_scale_of(
        _w1405_moved["actual"], _w1405_moved["structural_weight_tenths"])
    _w1405_moved["scale_error_pct"] = R1405._pct(
        _w1405_moved["declared_scale"] - _w1405_moved["implied_scale"],
        _w1405_moved["implied_scale"])
    _w1405_regrade = _w1405_raises(R1405.write_record, _w1405_moved, dirpath=_w1405_wdir)
    expect("WARP-1405 AC2: A RECORDED VARIANCE IS NOT SILENTLY REGRADED. A record whose bytes "
           "DIFFER from the one on disk is refused by name, and the explicit replace path does "
           "write. Paired with the idempotence above, that separates two things a single flag "
           "would confuse: writing the same measurement twice is free, and rewriting a "
           "measurement is a decision somebody has to make in a diff",
           _w1405_regrade[0] and "refusing to rewrite a recorded variance" in _w1405_regrade[1]
           and R1405.write_record(_w1405_moved, dirpath=_w1405_wdir,
                                  replace=True)[1] == "created"
           and R1405.read_record(_w1405_wdir / ("%s.yaml" % _W1405_ONE["spec"]))
           == _w1405_moved)

    # Four ways a reconciliation legitimately does not happen, all four in one pass.
    _w1405_hard_ests = dict(_w1405_ests)
    _w1405_hard_ests["WARP-9421"] = dict(_W1405_LEDGER and _w1405_ests[_W1405_SPECS[0]])
    _w1405_hard_ests["WARP-9421"] = dict(_w1405_hard_ests["WARP-9421"], spec="WARP-9421")
    _w1405_hard_ests["WARP-9422"] = dict(_w1405_hard_ests["WARP-9421"], spec="WARP-9422")
    _w1405_hard_ests["WARP-9423"] = dict(_w1405_hard_ests["WARP-9421"], spec="WARP-9423")
    _w1405_hard_ests["WARP-9424"] = dict(_w1405_hard_ests["WARP-9421"], spec="WARP-9424",
                                         low=_w1405_hard_ests["WARP-9421"]["high"] + 1)
    _w1405_hard_corpus = list(_w1405_corpus) + [
        _w1405_corpus_row("WARP-9422", 0, recorded=False),
        _w1405_corpus_row("WARP-9423", 12.5),
        _w1405_corpus_row("WARP-9424", 400000),
    ]
    _w1405_hard_recs, _w1405_hard_stand = R1405.pair(_w1405_hard_ests, _w1405_hard_corpus,
                                                     _W1405_AT)
    _w1405_by_spec = {s["spec"]: s["reason"] for s in _w1405_hard_stand}
    expect("WARP-1405 AC2: EVERY UNRECONCILED ESTIMATE IS EXPLAINED AND NONE IS DROPPED. Four "
           "reasons, one pass: not shipped (no corpus row), spend never recorded, an actual that "
           "is not an integer token count, and an estimate the estimate module itself refuses. "
           "Each is a named standdown row and none of the four enters the ledger. An accuracy "
           "number computed over the changes that happened to work is a hit rate over a "
           "self-selected sample, which is the most flattering number an estimator can publish",
           sorted(_w1405_by_spec) == ["WARP-9421", "WARP-9422", "WARP-9423", "WARP-9424"]
           and "not yet shipped" in _w1405_by_spec["WARP-9421"]
           and "no spend was ever recorded" in _w1405_by_spec["WARP-9422"]
           and "not a positive integer" in _w1405_by_spec["WARP-9423"]
           and "invalid estimate" in _w1405_by_spec["WARP-9424"]
           and [r["spec"] for r in _w1405_hard_recs] == _W1405_SPECS)

    expect("WARP-1405 AC2 NEGATIVE CONTROL FOR THOSE STANDDOWNS: the same two specs DO reconcile "
           "once the data is there. Given a corpus row with a recorded integer actual, the "
           "not-shipped and the no-spend cases both produce records. So the standdowns above are "
           "the DATA's doing and not a reconciler that refuses whatever it does not recognise",
           len(R1405.pair(
               {k: _w1405_hard_ests[k] for k in ("WARP-9421", "WARP-9422")},
               [_w1405_corpus_row("WARP-9421", 400000),
                _w1405_corpus_row("WARP-9422", 500000)], _W1405_AT)[0]) == 2)

    # -----------------------------------------------------------------------------------
    # AC3. THE ESTIMATOR'S OWN ACCURACY, THE CURVE, AND THE EMPTY LEDGER.
    # -----------------------------------------------------------------------------------
    _w1405_empty = R1405.accuracy([])
    expect("WARP-1405 AC3, THE LOAD-BEARING HONESTY OF THIS ITEM: AN EMPTY LEDGER REPORTS NO "
           "MEASURED ACCURACY, NOT A SCORE OF ZERO. Every figure is None, `measured` is False and "
           "the reason says the estimator has no measured accuracy yet. A hit rate of 0 means it "
           "missed every time; an unmeasured estimator has never been scored, and printing the "
           "first when the second is true is the exact dishonesty this item exists to refuse. The "
           "curve is EMPTY rather than a flat line along the bottom, and the refit and the "
           "comparison both stand down with reasons",
           _w1405_empty["measured"] is False
           and "NO MEASURED ACCURACY" in _w1405_empty["reason"]
           and all(_w1405_empty[k] is None for k in ("hit_rate_pct", "mean_error_pct",
                                                     "mean_abs_error_pct", "bias",
                                                     "worst_error_pct", "mean_width_pct"))
           and R1405.curve([]) == []
           and R1405.fit([])["fitted"] is False
           and "at least" in R1405.fit([])["reason"]
           and R1405.compare([])["measured"] is False
           and R1405.compare([])["improved"] is None)

    # MEASURED OVER THIS REPOSITORY'S OWN BYTES, not asserted from WARP-1401's report.
    _w1405_live = M1405.load()
    _w1405_live_spend = [e for e in _w1405_live
                         if any(isinstance(e.get(f), (int, float))
                                and not isinstance(e.get(f), bool)
                                for f in C1405.SPEND_FIELDS)]
    _w1405_live_ledger, _w1405_live_probs = R1405.load_dir(root=ROOT)
    expect("WARP-1405 AC3 MEASURED OVER THE REAL EVENT LOG: this repository's log is non-empty "
           "and NOT ONE of its recorded events carries tokens, cost_usd or human_minutes, so no "
           "shipped change has an actual, the ledger is empty and it reports itself unmeasured. "
           "That is WARP-1401's 0 percent spend coverage re-measured against today's bytes rather "
           "than quoted, and it is why the calibration curve this item ships renders nothing "
           "here: the honest output of an estimator with no history is that it has none. The "
           "count is deliberately NOT in this label, because the log grows on every gate run and "
           "a label that moved with it would not be reproducible",
           _w1405_live != [] and _w1405_live_spend == []
           and _w1405_live_ledger == {} and _w1405_live_probs == []
           and R1405.accuracy(list(_w1405_live_ledger.values()))["measured"] is False)

    expect("WARP-1405 AC3 NEGATIVE CONTROL FOR THAT MEASUREMENT: the SAME predicate finds spend "
           "in a seeded event, and toe_corpus's own reader agrees with it. So the zero above is "
           "the log's doing and not a broken test looking at the wrong field, which is the way "
           "an absence assertion normally passes for having looked nowhere",
           [e for e in [{"type": "spec.shipped", "spec_id": "WARP-9411", "tokens": 12345}]
            if any(isinstance(e.get(f), (int, float)) and not isinstance(e.get(f), bool)
                   for f in C1405.SPEND_FIELDS)] != []
           and C1405.spend_for([{"spec_id": "WARP-9411", "tokens": 12345}],
                               "WARP-9411")["spend_recorded"] is True)

    _W1405_ACC = R1405.accuracy(_W1405_LEDGER)
    expect("WARP-1405 AC3: OVER THE PLANTED-BIAS LEDGER THE ACCURACY IS MEASURED AND IT IS BAD, "
           "which is the point: five actuals at %dx the structural point land ABOVE every "
           "committed high, so the hit rate is 0 percent, the mean error is positive and the bias "
           "reads under_estimating. Bound to the counts rather than only the rate, so a counter "
           "that filed everything under one outcome could not satisfy this and the assertion "
           "below at the same time" % _W1405_BIAS,
           _W1405_ACC["measured"] is True and _W1405_ACC["n"] == 5
           and _W1405_ACC["hit_rate_pct"] == 0
           and _W1405_ACC["counts"]["above"] == 5
           and _W1405_ACC["counts"]["in_range"] == 0
           and _W1405_ACC["mean_error_pct"] > 0
           and _W1405_ACC["bias"] == "under_estimating")

    def _w1405_rescored(rec, low, high, actual):
        """One record moved onto a new committed range and a new actual with ALL FOUR derived
        fields recomputed, so a fixture built here is a record the validator calls VALID rather
        than a dict shaped like one. Every assertion using it asserts that too."""
        out = dict(rec, estimate_low=low, estimate_high=high, actual=actual)
        out["outcome"] = R1405.outcome_of(low, high, actual)
        out["error_pct"] = R1405.error_pct_of(low, high, actual)
        out["implied_scale"] = R1405.implied_scale_of(actual, out["structural_weight_tenths"])
        out["scale_error_pct"] = R1405._pct(out["declared_scale"] - out["implied_scale"],
                                           out["implied_scale"])
        return out

    # THE LEDGER WHERE THE COUNTS AND THE MEAN ERROR POINT OPPOSITE WAYS. Two actuals land far
    # BELOW one committed range and one lands far above it, and because the variance is measured
    # against the bound the actual missed, an undershoot can never pass -99 percent while an
    # overshoot is unbounded: errors -66, -66 and +200, a mean of +23 over a majority that came
    # in LOW.
    _W1405_SKEW = [_w1405_rescored(_W1405_LEDGER[_i], 300000, 600000, _a)
                   for _i, _a in enumerate((100000, 100000, 1800000))]
    _w1405_sacc = R1405.accuracy(_W1405_SKEW)
    # ONE MISS EACH WAY: the directions cancel while the mean does not, which is the third branch.
    _w1405_bacc = R1405.accuracy(_W1405_SKEW[1:])
    _w1405_vocab_cli = subprocess.run(
        [sys.executable, str(ROOT / ".veldo/toe_reconcile.py"), "vocabulary"],
        capture_output=True, text=True, cwd=str(ROOT))
    expect("WARP-1405 AC3: THE REPORTED BIAS IS THE DIRECTION ITS OWN SHIPPED VOCABULARY SAYS IT "
           "IS, MEASURED WHERE THE COUNTS AND THE MEAN DISAGREE. Over a ledger of three valid "
           "records with two actuals BELOW the range and one above, the mean bound-relative error "
           "is POSITIVE (+23, because an undershoot is floored at -99 percent while an overshoot "
           "is unbounded, so the two directions are not on one scale) and the reported bias is "
           "over_estimating, which is what the counts say. Bound to the sentence a READER is "
           "handed: the CLI's vocabulary subcommand prints the BIAS table, and the entry for the "
           "reported key must be the one that names the direction the counts show. The identity is "
           "asserted over three different ledgers, so it is a property of the derivation and not "
           "of this fixture. Read off the mean instead, this ledger would be published as "
           "under_estimating: the exact opposite of what its own table says the word means",
           all(R1405.validate_record(_r, spec_id=_r["spec"]) == [] for _r in _W1405_SKEW)
           and _w1405_sacc["counts"] == {"above": 1, "below": 2, "in_range": 0}
           and [_r["error_pct"] for _r in _W1405_SKEW] == [-66, -66, 200]
           and _w1405_sacc["mean_error_pct"] > 0
           and _w1405_sacc["bias"] == "over_estimating"
           and _w1405_bacc["counts"] == {"above": 1, "below": 1, "in_range": 0}
           and _w1405_bacc["bias"] == "balanced" and _w1405_bacc["mean_error_pct"] != 0
           and all(_acc["bias"] == ("balanced" if _acc["counts"]["above"]
                                    == _acc["counts"]["below"] else
                                    "under_estimating" if _acc["counts"]["above"]
                                    > _acc["counts"]["below"] else "over_estimating")
                   for _acc in (_w1405_sacc, _w1405_bacc, _W1405_ACC))
           and R1405.BIAS[_w1405_sacc["bias"]].startswith("MORE actuals landed below")
           and R1405.BIAS["under_estimating"].startswith("MORE actuals landed above")
           and _w1405_vocab_cli.returncode == 0
           and R1405.BIAS[_w1405_sacc["bias"]].split(",")[0] in _w1405_vocab_cli.stdout)

    # A mixed ledger: two in range, one below, two above, built by moving the actuals only.
    _w1405_mixed_actuals = {}
    for _i, _s in enumerate(_W1405_SPECS):
        _e = _w1405_ests[_s]
        _w1405_mixed_actuals[_s] = ([(_e["low"] + _e["high"]) // 2,
                                     (_e["low"] + _e["high"]) // 2,
                                     _e["low"] // 2,
                                     _e["high"] * 2,
                                     _e["high"] * 3])[_i]
    _W1405_MIXED, _ = R1405.pair(_w1405_ests,
                                 [_w1405_corpus_row(s, _w1405_mixed_actuals[s])
                                  for s in _W1405_SPECS], _W1405_AT)
    _w1405_macc = R1405.accuracy(_W1405_MIXED)
    expect("WARP-1405 AC3 ANTI-VACUITY ON THE SCORER: over a ledger deliberately built with two "
           "in range, one below and two above, the counts are exactly that, the hit rate is 40 "
           "percent and all THREE declared outcomes appear. A scorer that returned one constant "
           "outcome, or one constant rate, would satisfy every refusal assertion in this fragment "
           "and be worthless; this is the assertion that refuses it. The worst error is the "
           "largest by MAGNITUDE, so one big undershoot cannot hide behind several small overshoots",
           _w1405_macc["counts"] == {"above": 2, "below": 1, "in_range": 2}
           and _w1405_macc["hit_rate_pct"] == 40
           and len({r["outcome"] for r in _W1405_MIXED}) == 3
           and _w1405_macc["worst_error_pct"] == max(
               (r["error_pct"] for r in _W1405_MIXED), key=abs))

    _w1405_win = R1405.accuracy(_W1405_MIXED, window=2)
    expect("WARP-1405 AC3: THE TRAILING WINDOW IS THE LINE THE METHOD'S WRITING PROMISES, and it "
           "really slices. Over the last 2 of 5 records the figures are computed from those two "
           "alone, the window and the whole-ledger size are BOTH reported so a window wider than "
           "the history cannot read as a fuller one, and a non-positive window is refused rather "
           "than silently treated as everything",
           _w1405_win["n"] == 2 and _w1405_win["ledger"] == 5 and _w1405_win["window"] == 2
           and _w1405_win["counts"] == {"above": 2, "below": 0, "in_range": 0}
           and R1405.accuracy(_W1405_MIXED, window=99)["n"] == 5
           and _w1405_raises(R1405.accuracy, _W1405_MIXED, 0)[0])

    _W1405_CURVE = R1405.curve(_W1405_MIXED, window=3)
    expect("WARP-1405 AC3: THE CALIBRATION CURVE IS ONE POINT PER RECONCILIATION, IN ORDER, and "
           "each point's figures are the SAME function the headline number uses over the same "
           "prefix, asserted by recomputing every point rather than by trusting the loop. That is "
           "what anyone can inspect: the cumulative accuracy beside the trailing-window accuracy, "
           "so a converging estimator and a drifting one look different on the page instead of "
           "averaging into one comfortable number",
           len(_W1405_CURVE) == 5
           and [p["n"] for p in _W1405_CURVE] == [1, 2, 3, 4, 5]
           and all(p["cumulative_hit_rate_pct"]
                   == R1405.accuracy(_W1405_MIXED[:p["n"]])["hit_rate_pct"]
                   and p["window_hit_rate_pct"]
                   == R1405.accuracy(_W1405_MIXED[:p["n"]], window=3)["hit_rate_pct"]
                   and p["window_n"] == min(p["n"], 3)
                   for p in _W1405_CURVE)
           and _W1405_CURVE[-1]["cumulative_hit_rate_pct"] == 40)

    # THE INSPECTABLE SURFACE, end to end, both ways: the real CLI over the real repository
    # (which must stand down honestly) and the real build_view over a hermetic root carrying a
    # seeded ledger (which must render the numbers and the curve).
    _w1405_report_cli = subprocess.run(
        [sys.executable, str(ROOT / ".veldo/toe_reconcile.py"), "report"],
        capture_output=True, text=True, cwd=str(ROOT))
    _w1405_viewroot = Path(_d) / "viewroot"
    (_w1405_viewroot / ".veldo").mkdir(parents=True)
    (_w1405_viewroot / "specs").mkdir()
    for _rel in (".veldo/architecture.yaml", ".veldo/policy.yaml"):
        _w1405_shutil.copy(ROOT / _rel, _w1405_viewroot / _rel)
    R1405.write_all(_W1405_MIXED, dirpath=_w1405_viewroot / ".veldo" / "reconciliations")
    _w1405_view = R1405.build_view(root=_w1405_viewroot, window=3)
    _w1405_lines = R1405.render(_w1405_view)
    expect("WARP-1405 AC3: THE SURFACE ANYONE CAN INSPECT ACTUALLY RENDERS, BOTH WAYS. Driven as a "
           "real process over THIS repository the report exits 0 and says its accuracy is NOT "
           "MEASURED and that an empty curve is not a flat line at zero; driven through the real "
           "build_view over a hermetic root carrying the seeded ledger it prints the hit-rate line, "
           "one line per curve point and the refit line. The pair is what makes the stand-down "
           "attributable to the DATA: the same code renders numbers the moment a ledger exists",
           _w1405_report_cli.returncode == 0
           and "NOT MEASURED" in _w1405_report_cli.stdout
           and "not a flat line at zero" in _w1405_report_cli.stdout
           and _w1405_view["records"] == 5
           and any("percent of the last 3 unit(s) in range" in ln for ln in _w1405_lines)
           and sum(1 for ln in _w1405_lines if "cumulative" in ln) == 5
           and any(ln.startswith("refit: scale") for ln in _w1405_lines)
           and not any("NOT MEASURED" in ln for ln in _w1405_lines))

    expect("WARP-1405 AC3: THE CURVE MOVES, which is the property a curve has to have to be one. "
           "Over the mixed ledger the cumulative hit rate is not constant across its points, and "
           "the trailing window disagrees with the cumulative figure at the end. Without this the "
           "curve assertion above would pass on a flat line, which is exactly what an estimator "
           "that never learns anything would produce",
           len({p["cumulative_hit_rate_pct"] for p in _W1405_CURVE}) > 1
           and _W1405_CURVE[-1]["window_hit_rate_pct"]
           != _W1405_CURVE[-1]["cumulative_hit_rate_pct"])

    # -----------------------------------------------------------------------------------
    # AC4. STRUCTURE VERSUS SCALE: THE REFIT, ITS FLOOR, AND OUT-OF-SAMPLE HONESTY.
    # -----------------------------------------------------------------------------------
    _W1405_FIT = R1405.fit(_W1405_LEDGER)
    expect("WARP-1405 AC4: THE REFIT RECOVERS THE PLANTED SCALE AND LEAVES THE STRUCTURE ALONE. "
           "Every actual was planted at %dx its structural point, so every implied scale is %dx "
           "the declared one and the fitted scale is exactly that, named to the change it came "
           "from. This is the whole payoff of WARP-1402 recording the weight and the scale "
           "separately: the estimator can be corrected where it is wrong without touching the "
           "part that was right" % (_W1405_BIAS, _W1405_BIAS),
           _W1405_FIT["fitted"] is True and _W1405_FIT["sample"] == 5
           and _W1405_FIT["scale"] == E1405.TOKENS_PER_STRUCTURAL_UNIT * _W1405_BIAS
           and _W1405_FIT["spec"] in _W1405_SPECS
           and _W1405_FIT["declared_scales"] == [E1405.TOKENS_PER_STRUCTURAL_UNIT]
           and _W1405_FIT["dispersion_pct"] == 0)

    _W1405_CMP = R1405.compare(_W1405_LEDGER)
    expect("WARP-1405 AC4, THE CLAIM THIS ITEM EXISTS TO SUPPORT: RECALIBRATION MEASURABLY "
           "REDUCES THE PLANTED BIAS, AND IT IS SCORED OUT OF SAMPLE. Held out one record at a "
           "time, the refitted estimator puts every actual back inside its range: the hit rate "
           "goes 0 to 100 percent and the mean absolute error falls to 0, so the delta is "
           "negative and `improved` is True. Fitting and scoring on the same records would prove "
           "nothing at all, because the fit would already have seen the answers",
           _W1405_CMP["measured"] is True and _W1405_CMP["improved"] is True
           and _W1405_CMP["before"]["hit_rate_pct"] == 0
           and _W1405_CMP["after"]["hit_rate_pct"] == 100
           and _W1405_CMP["after"]["scored"] == 5
           and _W1405_CMP["mean_abs_error_delta_pct"] < 0
           and _W1405_CMP["hit_rate_delta_pct"] > 0)

    # A ledger whose implied scales DISAGREE: the structure does not explain the variance.
    _w1405_wild = {}
    for _i, _s in enumerate(_W1405_SPECS):
        _w1405_wild[_s] = (_w1405_weights[_s] * E1405.TOKENS_PER_STRUCTURAL_UNIT // 10) \
            * (1, 2, 4, 8, 16)[_i]
    _W1405_WILD, _ = R1405.pair(_w1405_ests,
                                [_w1405_corpus_row(s, _w1405_wild[s]) for s in _W1405_SPECS],
                                _W1405_AT)
    _w1405_wfit = R1405.fit(_W1405_WILD)

    # A ledger the estimator ALREADY got right: every actual lands exactly on its structural
    # point, so the declared scale was correct all along and there is nothing to correct.
    _W1405_CALIB, _ = R1405.pair(
        _w1405_ests,
        [_w1405_corpus_row(s, _w1405_weights[s] * E1405.TOKENS_PER_STRUCTURAL_UNIT // 10)
         for s in _W1405_SPECS], _W1405_AT)
    _w1405_ccmp = R1405.compare(_W1405_CALIB)
    expect("WARP-1405 AC4 NEGATIVE CONTROL ON THAT CLAIM: over a ledger the estimator ALREADY got "
           "right, the refit does NOT claim to improve anything and does not break it either. "
           "Every actual sits exactly on its structural point, so the hit rate is already 100 "
           "percent, the refit recovers the DECLARED scale unchanged, the deltas are zero and "
           "`improved` is False. Without this control the assertion above would pass on a "
           "comparison hardcoded to say yes, which is the likeliest way a self-grading estimator "
           "lies",
           _w1405_ccmp["measured"] is True and _w1405_ccmp["improved"] is False
           and _w1405_ccmp["before"]["hit_rate_pct"] == 100
           and _w1405_ccmp["after"]["hit_rate_pct"] == 100
           and _w1405_ccmp["mean_abs_error_delta_pct"] == 0
           and R1405.fit(_W1405_CALIB)["scale"] == E1405.TOKENS_PER_STRUCTURAL_UNIT)

    _w1405_wcmp = R1405.compare(_W1405_WILD)
    expect("WARP-1405 AC4: AN IMPROVEMENT BOUGHT BY WIDENING SAYS SO ON THE SAME LINE. Over the "
           "ledger whose implied scales span 16x the refit DOES raise the hit rate, and it does it "
           "by producing ranges wide enough to contain almost anything: the width delta is "
           "strongly positive and the reason prints both widths. A hit rate on its own is gameable "
           "by an estimator answering 'between one token and a billion', so this surface never "
           "reports one without the width it was bought with",
           _w1405_wcmp["measured"] is True and _w1405_wcmp["width_delta_pct"] > 100
           and _w1405_wcmp["after"]["mean_width_pct"] > _w1405_wcmp["before"]["mean_width_pct"]
           and "mean range width" in _w1405_wcmp["reason"]
           and _w1405_ccmp["width_delta_pct"] < _w1405_wcmp["width_delta_pct"])

    # A MIXED-FITTABILITY LEDGER, which is the ordinary steady state and not a contrived one:
    # build_record omits the structure-and-scale block for every estimate with no structural proxy
    # layer, which is exactly what a sizing-pass or historical-analogy estimate produces. Four
    # records the refit provably changes nothing on (every actual already exactly on its point),
    # plus two the prior missed by 10x that carry NO block, so the refit can never score them.
    _W1405_CALIB_BY = {_r["spec"]: _r for _r in _W1405_CALIB}
    _W1405_MIXFIT = [dict(_W1405_CALIB_BY[_s]) for _s in _W1405_SPECS[:4]]
    for _i, _s in enumerate(_W1405_SPECS[:2]):
        _r = dict(_W1405_CALIB_BY[_s], spec="WARP-944%d" % (_i + 1))
        for _k in R1405.DECOMP_KEYS:
            del _r[_k]
        _r["actual"] = _r["estimate_high"] * 10
        _r["outcome"] = R1405.outcome_of(_r["estimate_low"], _r["estimate_high"], _r["actual"])
        _r["error_pct"] = R1405.error_pct_of(_r["estimate_low"], _r["estimate_high"], _r["actual"])
        _W1405_MIXFIT.append(_r)
    _w1405_mixcmp = R1405.compare(_W1405_MIXFIT)
    _w1405_mixview = R1405.render({
        "records": len(_W1405_MIXFIT), "dir": "(fixture)", "problems": [],
        "accuracy": R1405.accuracy(_W1405_MIXFIT),
        "window_accuracy": R1405.accuracy(_W1405_MIXFIT), "curve": [],
        "fit": R1405.fit(_W1405_MIXFIT), "compare": _w1405_mixcmp, "pending": []})
    expect("WARP-1405 AC4, THE POPULATION THE CLAIM IS MADE OVER: A DELTA IS ONLY EVER TAKEN "
           "BETWEEN TWO FIGURES OVER THE SAME RECORDS. Over a ledger of six valid records where "
           "the four the refit can touch were ALREADY EXACTLY RIGHT and the other two carry no "
           "structure-and-scale block and were missed by 10x, the refit changes nothing and must "
           "say so: every delta is 0 and `improved` is False, and the rendered line reads that the "
           "refit does NOT improve on the prior. Scored against the WHOLE ledger instead, the same "
           "run would publish mean absolute error 300 to 0 percent, hit rate 67 to 100 and "
           "`improved: True`, and that entire 300 is the two records present in one figure and "
           "absent from the other - which is asserted here as the arithmetic this refuses. Every "
           "record is accounted for: scored plus skipped equals the ledger, and each unpaired "
           "record is named with the reason the refit could not score it, so the count is honest "
           "rather than quietly smaller",
           all(R1405.validate_record(_r, spec_id=_r["spec"]) == [] for _r in _W1405_MIXFIT)
           and _w1405_mixcmp["measured"] is True and _w1405_mixcmp["improved"] is False
           and _w1405_mixcmp["before"]["n"] == 6 and _w1405_mixcmp["after"]["scored"] == 4
           and _w1405_mixcmp["paired_before"]["n"] == 4
           and (_w1405_mixcmp["hit_rate_delta_pct"], _w1405_mixcmp["mean_abs_error_delta_pct"])
           == (0, 0)
           # The unpaired arithmetic, spelled out: this is what the module must NOT publish.
           and _w1405_mixcmp["after"]["mean_abs_error_pct"] \
           - _w1405_mixcmp["before"]["mean_abs_error_pct"] == -300
           and _w1405_mixcmp["after"]["hit_rate_pct"] \
           - _w1405_mixcmp["before"]["hit_rate_pct"] == 33
           and _w1405_mixcmp["after"]["scored"] + len(_w1405_mixcmp["after"]["skipped"]) == 6
           and [_u["spec"] for _u in _w1405_mixcmp["unpaired"]] == ["WARP-9441", "WARP-9442"]
           and all("structural_weight_tenths" in _u["reason"]
                   for _u in _w1405_mixcmp["unpaired"])
           and "in NEITHER figure" in _w1405_mixcmp["reason"]
           and any("the refit does NOT improve on the prior" in _ln for _ln in _w1405_mixview)
           and sorted(_ln.split()[1] for _ln in _w1405_mixview
                      if _ln.startswith("  unpaired:")) == ["WARP-9441", "WARP-9442"])

    expect("WARP-1405 AC4 NEGATIVE CONTROL ON THAT PAIRING: the SAME six-record ledger with the "
           "two unfittable records REMOVED is a ledger of four the refit still cannot improve, and "
           "the WHOLE-ledger figures then agree with the paired ones because there is only one "
           "population left. So the zero deltas above are the pairing being right and not a "
           "comparison that reports zero whatever it is handed: over the planted-bias ledger, "
           "where every record is fittable, the same code still reports a real improvement",
           R1405.compare(_W1405_MIXFIT[:4])["improved"] is False
           and R1405.compare(_W1405_MIXFIT[:4])["before"]["mean_abs_error_pct"]
           == R1405.compare(_W1405_MIXFIT[:4])["paired_before"]["mean_abs_error_pct"]
           and R1405.compare(_W1405_MIXFIT[:4])["unpaired"] == []
           and _W1405_CMP["improved"] is True
           and _W1405_CMP["paired_before"]["n"] == _W1405_CMP["before"]["n"] == 5
           and _W1405_CMP["mean_abs_error_delta_pct"] < 0)

    _w1405_agree_range = R1405.recalibrated_range(100, _W1405_FIT)
    _w1405_wild_range = R1405.recalibrated_range(100, _w1405_wfit)
    # THE TEXT A READER ACTUALLY SEES about the fit, every branch of it: the fitted reason, the
    # dispersed reason, and all three stand-downs, plus the layer note this module writes into an
    # estimate and the refit and recalibration lines the report prints.
    _W1405_VERDICT_RE = _w1405_re.compile(
        r"\b(wrong|right|correct|correctly|incorrect|explains?|explained|fault|faulty|verdict|"
        r"broken|invalid|useless)\b", _w1405_re.I)
    _w1405_fit_prose = [
        _W1405_FIT["reason"], _w1405_wfit["reason"], R1405.fit([])["reason"],
        R1405.fit(_W1405_LEDGER[:2])["reason"],
        R1405.fit([dict(_r, era="era-a" if _i % 2 else "era-b")
                   for _i, _r in enumerate(_W1405_LEDGER)])["reason"],
        R1405.recalibrated_layer(100, _W1405_FIT)["note"],
        R1405.recalibrated_layer(100, _w1405_wfit)["note"],
    ] + [_ln for _ln in _w1405_lines
         if _ln.startswith("refit:") or _ln.startswith("recalibration:")]
    expect("WARP-1405 AC4: DISAGREEMENT WIDENS THE RANGE INSTEAD OF HIDING IN IT, AND THE MODULE "
           "NEVER LABELS THE STRUCTURE RIGHT OR WRONG, asserted over the STRINGS A READER SEES "
           "and not over the fit dict's key names. Over a ledger whose implied scales span 16x the "
           "dispersion is reported as a large percentage and the refitted range is far wider than "
           "over the ledger that agrees; and not one verdict word (wrong, right, correct, "
           "explains, fault, verdict, broken, invalid) appears in any fit reason, in either "
           "stand-down, in the layer note this module writes into an estimate or in the refit and "
           "recalibration lines the report prints. Bound to a POSITIVE CONTROL that the same "
           "pattern DOES fire on the sentence this claim forbids, because an absence assertion "
           "whose matcher matches nothing is a pass earned by looking nowhere. The word "
           "`structure` itself is legal (a stand-down names the block it needs), so the match is "
           "on the VERDICT and never on the noun; the key-name clause is kept as the second half",
           _w1405_wfit["fitted"] is True and _w1405_wfit["dispersion_pct"] > 1000
           and _w1405_wild_range[1] - _w1405_wild_range[0]
           > (_w1405_agree_range[1] - _w1405_agree_range[0]) * 5
           and _w1405_fit_prose != [] and len(_w1405_fit_prose) >= 9
           and not any(_W1405_VERDICT_RE.search(_t) for _t in _w1405_fit_prose)
           and _W1405_VERDICT_RE.search(
               "VERDICT: the structure is WRONG and no scale will fix it") is not None
           and any("structure" in _t for _t in _w1405_fit_prose)
           and "structure" not in " ".join(sorted(_w1405_wfit)))

    expect("WARP-1405 AC4: THE FLOOR UNDER A FITTED RANGE, which is false precision arriving "
           "through the back door. Five records agreeing EXACTLY would otherwise license a range "
           "one rounding step wide, an estimator claiming a change to a tenth of a percent "
           "because five earlier ones agreed. So the agreeing fit reports the floor APPLIED and "
           "its range still spans at least the declared minimum, while the disagreeing fit does "
           "NOT apply it and keeps its measured envelope. The pair is what makes the floor "
           "attributable to the sample rather than a constant widening",
           R1405.recalibrated_range(100, _W1405_FIT)[2] is True
           and R1405.recalibrated_range(100, _w1405_wfit)[2] is False
           and (_w1405_agree_range[1] - _w1405_agree_range[0]) * 100
           >= _w1405_agree_range[0] * R1405.MIN_FITTED_SPREAD_PCT
           and _w1405_agree_range[1] > _w1405_agree_range[0] + E1405.ROUND_STEP)

    _w1405_out_spec = _W1405_SPECS[-1]
    _w1405_outlier = [dict(r) for r in _W1405_WILD]
    _w1405_ex_fit = R1405.fit(_w1405_outlier, exclude=_w1405_out_spec)
    _w1405_hold = R1405.holdout(_w1405_outlier)
    _w1405_hold_row = next(r for r in _w1405_hold["rows"] if r["spec"] == _w1405_out_spec)
    expect("WARP-1405 AC4: LEAVE-ONE-OUT REALLY LEAVES ONE OUT. Excluding the largest-implied "
           "record moves the fitted scale and shrinks the sample by exactly one, and the held-out "
           "row for that record is scored against the scale fitted WITHOUT it, asserted as an "
           "identity against a separate fit call. An in-sample number here would be a refit "
           "grading its own homework, and it would look exactly like a working measurement",
           _w1405_ex_fit["sample"] == _w1405_wfit["sample"] - 1
           and _w1405_ex_fit["excluded"] == _w1405_out_spec
           and _w1405_ex_fit["scale"] != _w1405_wfit["scale"]
           and _w1405_hold_row["fitted_scale"] == _w1405_ex_fit["scale"]
           and _w1405_hold_row["fitted_from_records"] == _w1405_ex_fit["sample"])

    expect("WARP-1405 AC4: THE REFIT STANDS DOWN BELOW ITS DECLARED MINIMUM SAMPLE AND SAYS SO, "
           "and it fits at exactly the minimum. Two records give `fitted: False` with the sample "
           "size and the minimum in the reason; three records fit. So the threshold is the sample "
           "and not a rule that always refuses, and a median over one or two numbers never "
           "becomes a confident multiplier",
           R1405.fit(_W1405_LEDGER[:2])["fitted"] is False
           and str(R1405.MIN_REFIT_SAMPLE) in R1405.fit(_W1405_LEDGER[:2])["reason"]
           and R1405.fit(_W1405_LEDGER[:R1405.MIN_REFIT_SAMPLE])["fitted"] is True
           and R1405.MIN_REFIT_SAMPLE == 3)

    _w1405_two_eras = [dict(r, era="era-a" if i % 2 else "era-b")
                       for i, r in enumerate(_W1405_LEDGER)]
    _w1405_one_era = [dict(r, era="era-a") for r in _W1405_LEDGER]
    expect("WARP-1405 AC4: TWO ERAS ARE NEVER BLENDED INTO ONE FITTED SCALE (D5), and the "
           "refusal names them. A ledger whose records carry two era stamps stands the refit "
           "down; the SAME records under one era fit normally. A model that does different work "
           "per token makes its actuals a different unit, and one multiplier claiming to convert "
           "between them would be a guess wearing a measurement's clothes",
           R1405.fit(_w1405_two_eras)["fitted"] is False
           and "era-a" in R1405.fit(_w1405_two_eras)["reason"]
           and "era-b" in R1405.fit(_w1405_two_eras)["reason"]
           and R1405.fit(_w1405_one_era)["fitted"] is True
           and R1405.fit(_w1405_one_era)["era"] == "era-a")

    _w1405_layer = R1405.recalibrated_layer(_w1405_weights[_W1405_SPECS[0]], _W1405_FIT)
    _w1405_new_spec = tmpfile(_d, "WARP-9431.md", _w1405_spec_text("WARP-9431", acs=3))
    _w1405_both = R1405.propose_recalibrated(_w1405_new_spec, "2026-08-11", _W1405_FIT)
    _w1405_super = R1405.propose_recalibrated(_w1405_new_spec, "2026-08-11", _W1405_FIT,
                                              supersede=True)
    _w1405_prior = E1405.propose(_w1405_new_spec, "2026-08-11")
    expect("WARP-1405 AC4: THE REFIT IS DELIVERED AS A LAYER IN WARP-1402'S OWN VOCABULARY, "
           "through its own record assembler, so this item extends a vocabulary rather than "
           "widening one. The layer id and basis are the declared `recalibrated` pair, the record "
           "validates clean through the ESTIMATE validator, and it reads calibration: calibrated "
           "because that basis is grounded in recorded actuals: the first record in this "
           "repository's schema that could honestly say so",
           _w1405_layer["layer"] == "recalibrated" and _w1405_layer["basis"] == "recalibrated"
           and _w1405_layer["layer"] in E1405.LAYERS and _w1405_layer["basis"] in E1405.BASES
           and E1405.validate_record(_w1405_super) == []
           and _w1405_super["calibration"] == "calibrated"
           and [l["layer"] for l in _w1405_super["layers"]] == ["recalibrated"])

    expect("WARP-1405 AC4: THE ENVELOPE STILL ONLY WIDENS, AND SHARPENING IS THE CALLER'S "
           "EXPLICIT JUDGEMENT. Keeping both layers gives a committed range that is the union of "
           "the prior and the refit and is therefore no narrower than the prior; replacing the "
           "prior gives a range that no longer contains its low. Nothing in this module narrows "
           "a range behind a caller's back, which is WARP-1402's AC2 held from the outside",
           _w1405_both["low"] <= _w1405_prior["low"]
           and _w1405_both["high"] >= _w1405_prior["high"]
           and (_w1405_both["low"], _w1405_both["high"])
           == E1405.combine(_w1405_both["layers"], "envelope")
           and _w1405_super["low"] > _w1405_prior["low"]
           and [l["layer"] for l in _w1405_both["layers"]]
           == ["structural_proxy", "recalibrated"])

    _w1405_lin = _w1405_layer["inputs"]
    _w1405_wlayer = R1405.recalibrated_layer(_w1405_weights[_W1405_SPECS[0]], _w1405_wfit)
    _w1405_wlin = _w1405_wlayer["inputs"]

    def _w1405_bounds_from_inputs(ins):
        """One layer's bounds recomputed FROM ITS RECORDED INPUTS ALONE, with the arithmetic
        written out here rather than borrowed from the module.

        THIS IS THE WHOLE POINT OF THE ASSERTION BELOW AND IT IS WHY IT IS SPELLED TWICE. Calling
        `recalibrated_range` with the same fit object would recompute the bounds with the very
        call that produced them: both sides would move together for any change to that arithmetic
        or to any number the record claims it was fitted from, so the record could lie about its
        own envelope and nothing would notice. Every value read here comes out of the layer, so a
        recorded input that does not support the recorded bounds reds this."""
        lo_scale, hi_scale = ins["fitted_scale_low"], ins["fitted_scale_high"]
        if ins["spread_floor_applied"] == E1405.YES:
            mid = ins["fitted_scale"]
            lo_scale = min(lo_scale, mid * 100 // ins["half_spread_pct"])
            hi_scale = max(hi_scale, mid * ins["half_spread_pct"] // 100)
        weight = ins["structural_weight_tenths"]
        low = E1405._round_tokens(weight * lo_scale // 10)
        high = E1405._round_tokens(weight * hi_scale // 10)
        return low, (high if high > low else low + E1405.ROUND_STEP)

    def _w1405_input_is_load_bearing(layer, key):
        """Whether one recorded input actually decides the recorded bounds: tripling it must move
        the recomputation. An assertion over inputs the arithmetic ignores is an assertion that
        cannot fail, which is what this pair of layers is here to rule out."""
        return _w1405_bounds_from_inputs(dict(layer["inputs"], **{key: layer["inputs"][key] * 3})) \
            != (layer["low"], layer["high"])

    expect("WARP-1405 AC4: THE REFITTED LAYER'S RECORDED INPUTS REPRODUCE ITS OWN BOUNDS, "
           "recomputed here FROM THE LAYER ALONE with the arithmetic written out, in BOTH "
           "branches: the floored layer (five records agreeing, so the declared widening ratio "
           "runs) and the unfloored one (implied scales spanning 16x, so the measured envelope "
           "runs). The ratio the floor widens by is one of the recorded inputs, because without it "
           "a floored layer's inputs reproduce the fitted point twice over, a POINT, which is the "
           "one shape NG6 refuses. Bound to a sensitivity control on every input the arithmetic "
           "reads, so this cannot be satisfied by numbers nothing depends on: tripling any of them "
           "moves the recomputed pair. So the next reconciliation can attribute THIS layer's error "
           "the same way this one attributed the prior's, and a record that lied about the "
           "envelope it was fitted from would red here",
           (_w1405_layer["low"], _w1405_layer["high"])
           == _w1405_bounds_from_inputs(_w1405_lin)
           and (_w1405_wlayer["low"], _w1405_wlayer["high"])
           == _w1405_bounds_from_inputs(_w1405_wlin)
           and _w1405_layer["high"] > _w1405_layer["low"] + E1405.ROUND_STEP
           and all(_w1405_input_is_load_bearing(_w1405_layer, k)
                   for k in ("fitted_scale", "fitted_scale_high", "half_spread_pct",
                             "structural_weight_tenths"))
           and all(_w1405_input_is_load_bearing(_w1405_wlayer, k)
                   for k in ("fitted_scale_low", "fitted_scale_high",
                             "structural_weight_tenths"))
           and _w1405_lin["half_spread_pct"] == R1405.HALF_SPREAD_PCT
           and _w1405_lin["min_fitted_spread_pct"] == R1405.MIN_FITTED_SPREAD_PCT
           and _w1405_lin["fitted_scale"] == _W1405_FIT["scale"]
           and _w1405_lin["declared_scale_replaced"] == E1405.TOKENS_PER_STRUCTURAL_UNIT
           and _w1405_lin["spread_floor_applied"] == E1405.YES
           and _w1405_wlin["spread_floor_applied"] == E1405.NO
           and _w1405_lin["dispersion_pct"] == 0
           and _w1405_lin["fitted_from_records"] == 5)

    expect("WARP-1405 AC4: NO FITTED SCALE MEANS NO RECALIBRATED LAYER, refused by name and "
           "carrying the stand-down reason. An estimator with nothing to learn from keeps its "
           "declared prior and says so; inventing a layer out of an unfitted refit would put a "
           "number with the word `recalibrated` on it in front of a planner",
           _w1405_raises(R1405.recalibrated_layer, 100, R1405.fit([]))[0]
           and "no fitted scale" in _w1405_raises(
               R1405.recalibrated_layer, 100, R1405.fit([]))[1]
           and _w1405_raises(R1405.recalibrated_range, 0, _W1405_FIT)[0])

    # -----------------------------------------------------------------------------------
    # AC5. ADOPTION SAFE, AND NEVER A BLOCKER.
    # -----------------------------------------------------------------------------------
    _w1405_absent = Path(_d) / "no_such_reconciliations_dir"
    expect("WARP-1405 AC5: WITH NO RECORDS PRESENT EVERY READER STANDS DOWN SILENTLY AND CREATES "
           "NOTHING. load_dir gives an empty ledger with no problems, record_for gives None, "
           "check_dir reports nothing checked, and the directory is STILL absent afterwards. A "
           "repository that never reconciles anything is byte-identically unaffected, which is "
           "the only posture under which adding this to a working gate is safe",
           R1405.load_dir(_w1405_absent) == ({}, [])
           and R1405.record_for("WARP-9411", dirpath=_w1405_absent) is None
           and R1405.check_dir(_w1405_absent) == (0, 0)
           and not _w1405_absent.exists())

    _w1405_cli = subprocess.run(
        [sys.executable, str(ROOT / ".veldo/toe_reconcile.py"), "check",
         "--dir", str(_w1405_absent)], capture_output=True, text=True, cwd=str(ROOT))
    expect("WARP-1405 AC5: THE CLI'S check EXITS 0 AND SAYS IT IS STANDING DOWN when nothing is "
           "recorded, driven as a real process. A tool that exited non-zero on the absence of an "
           "optional record would turn an advisory ledger into a gate the first time somebody "
           "wired it into a script, which is precisely NG1",
           _w1405_cli.returncode == 0 and "standing down" in _w1405_cli.stdout
           and "not a finding" in _w1405_cli.stdout)

    _w1405_mixdir = Path(_d) / "mixed"
    _w1405_mixdir.mkdir()
    R1405.write_record(_W1405_ONE, dirpath=_w1405_mixdir)
    (_w1405_mixdir / "WARP-9499.yaml").write_text(
        "schema: veldo.toe_reconciliation/v1\nspec: WARP-9499\nactual: 5\n")
    _w1405_loaded, _w1405_loadprobs = R1405.load_dir(_w1405_mixdir)
    expect("WARP-1405 AC5 FAIL CLOSED ON A PRESENT-BUT-BROKEN RECORD: load_dir returns the valid "
           "record and reports the broken one by path, rather than quietly returning a smaller "
           "ledger. Absence stands down; breakage speaks up. Those are different facts, and an "
           "accuracy number computed over a silently smaller ledger is the defect WARP-1401's "
           "coverage report exists to prevent",
           sorted(_w1405_loaded) == [_W1405_ONE["spec"]]
           and len(_w1405_loadprobs) == 1 and "WARP-9499" in _w1405_loadprobs[0])

    _w1405_mixcheck = R1405.check_dir(_w1405_mixdir)
    _w1405_broken_cli = subprocess.run(
        [sys.executable, str(ROOT / ".veldo/toe_reconcile.py"), "check",
         "--dir", str(_w1405_mixdir)], capture_output=True, text=True, cwd=str(ROOT))
    expect("WARP-1405 AC5: THE OPERATOR-FACING check IS THE SURFACE THAT EXISTS TO NAME A BROKEN "
           "RECORD, SO IT IS MEASURED OVER ONE. Over the same directory holding one VALID record "
           "and one MALFORMED one, check_dir reports BOTH records checked and a non-zero problem "
           "count, and the CLI driven as a real process EXITS 1 and prints the malformed file's "
           "path while never naming the valid one. Paired with the absence assertion above, that "
           "keeps two facts distinguishable which one exit code would blur: nothing recorded is a "
           "stand-down at 0, and something recorded and broken is a finding at 1. Without this the "
           "whole subcommand could be replaced by `pass` and every check_dir assertion would still "
           "pass, because the only directory it was ever pointed at was empty",
           _w1405_mixcheck[0] == 2 and _w1405_mixcheck[1] > 0
           and _w1405_broken_cli.returncode == 1
           and "2 record(s) checked" in _w1405_broken_cli.stdout
           and "0 problem(s)" not in _w1405_broken_cli.stdout
           and "WARP-9499.yaml" in _w1405_broken_cli.stdout
           and "%s.yaml" % _W1405_ONE["spec"] not in _w1405_broken_cli.stdout)

    # A hermetic repository root: the real contract and policy, a fixture spec, and a
    # reconciliations directory we control. check_spec accepts repo_root, so the REAL validator
    # runs over it.
    _w1405_root = Path(_d) / "repo"
    (_w1405_root / ".veldo").mkdir(parents=True)
    (_w1405_root / "specs").mkdir()
    for _rel in (".veldo/architecture.yaml", ".veldo/policy.yaml"):
        _w1405_shutil.copy(ROOT / _rel, _w1405_root / _rel)
    _w1405_rspec = _w1405_root / "specs" / ("%s-fixture.md" % _W1405_ONE["spec"])
    _w1405_rspec.write_text(_w1405_spec_text(_W1405_ONE["spec"], status="ready"))
    _w1405_recdir = _w1405_root / ".veldo" / "reconciliations"

    _w1405_no_rec = V.check_spec(_w1405_rspec, repo_root=_w1405_root)
    R1405.write_record(_W1405_ONE, dirpath=_w1405_recdir)
    _w1405_with_rec = V.check_spec(_w1405_rspec, repo_root=_w1405_root)
    (_w1405_recdir / ("%s.yaml" % _W1405_ONE["spec"])).write_text(
        "schema: veldo.toe_reconciliation/v1\nspec: %s\nestimate_low: 5\nestimate_high: 5\n"
        "actual: 0\noutcome: brilliant\n" % _W1405_ONE["spec"])
    _w1405_broken_rec = V.check_spec(_w1405_rspec, repo_root=_w1405_root)
    _w1405_broken_probs = _w1405_probs(
        R1405.parse_record((_w1405_recdir / ("%s.yaml" % _W1405_ONE["spec"])).read_text()),
        spec_id=_W1405_ONE["spec"])
    _w1405_bad_spec = _w1405_root / "specs" / "WARP-9498-broken.md"
    _w1405_bad_spec.write_text(_w1405_spec_text("WARP-9498", status="ready").replace(
        "status: ready", "status: donezo"))
    _w1405_bad_spec_errs = V.check_spec(_w1405_bad_spec, repo_root=_w1405_root)

    expect("WARP-1405 AC5, THE LOAD-BEARING ONE: A RECONCILIATION CAN NEVER INVALIDATE A SPEC, "
           "measured by DRIVING the real validate.check_spec over a hermetic repository root "
           "three times - with no record, with a valid one written by the real writer, and with a "
           "MALFORMED one (a point range, a zero actual and an invented outcome) - and getting "
           "the identical 0 every time, while validate_record names that record's defects. This "
           "is PLAN-0014 C3 and NG1 as a measurement rather than as a promise: the ledger lives "
           "BESIDE the spec, so its absence and even its breakage are invisible to the thing "
           "that decides whether a spec is valid",
           (_w1405_no_rec, _w1405_with_rec, _w1405_broken_rec) == (0, 0, 0)
           and "POINT" in _w1405_broken_probs
           and "outcome must be one of" in _w1405_broken_probs
           and "must be a positive integer" in _w1405_broken_probs)

    expect("WARP-1405 AC5 NEGATIVE CONTROL FOR THAT PASS: the SAME validator over the SAME "
           "hermetic root DOES refuse a genuinely broken spec, so the three zeros above are the "
           "reconciliation being irrelevant and not check_spec being blind under this fixture. "
           "Without this control the whole assertion would be a pass earned by looking nowhere",
           _w1405_bad_spec_errs > 0)

    _w1405_gate_text = (ROOT / "scripts/verify.sh").read_text()
    _w1405_slots = _w1405_re.findall(r"CHECK_\w+=\"[^\"]*\"", _w1405_gate_text)
    expect("WARP-1405 AC5: NOTHING IN THE GATE NAMES THIS MODULE. scripts/verify.sh declares no "
           "slot mentioning toe_reconcile.py, and neither does the contract validator it runs, so "
           "no path through the gate can refuse, block or delay work on a variance or on an "
           "estimator's accuracy. Bound to a non-empty slot list, so a parse that found no slots "
           "reds this rather than passing over nothing. It is the WEAKER half: the measurement "
           "that carries NG1 is the three-way check_spec pair above",
           _w1405_slots != [] and all("reconcile" not in s for s in _w1405_slots)
           and "toe_reconcile" not in _w1405_gate_text
           and "toe_reconcile" not in (ROOT / ".veldo/validate.py").read_text())

    expect("WARP-1405 AC5: THE MODULE REACHES FOR NOTHING OUTSIDE THE REPOSITORY AND READS NO "
           "CLOCK. Its source names no subprocess, socket or urllib import and no Popen, so it "
           "cannot spawn a process or open a connection (NG5), and it names no clock: every date "
           "is passed in, which is what the determinism assertion above actually measures",
           all(tok not in (ROOT / ".veldo/toe_reconcile.py").read_text()
               for tok in ("import subprocess", "import socket", "import urllib", "Popen(",
                           "datetime.now", "time.time"))
           and R1405.pair(_w1405_ests, _w1405_corpus, _W1405_AT)[0] == _W1405_LEDGER)

del _w1405_re, _w1405_shutil
