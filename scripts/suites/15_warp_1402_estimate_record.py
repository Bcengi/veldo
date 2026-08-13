"""WARP-1402: the estimate record and the structural proxy, and the reasons each check can fail.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, which always
runs, so its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 15_warp_1402_estimate_record

WHAT IS OBSERVED HERE, AND HOW. The subject is a SCHEMA and a derivation, so the shape is
negative-first, the way this repository's suite has been since the beginning: every planted-bad
record must be REFUSED, and every refusal is paired with the positive control that the same
record validates once corrected. That pairing is the whole method here, because a validator that
refuses everything passes every negative assertion and is useless.

THE ASSERTIONS WERE WATCHED FAILING, not assumed to bite. Properties of the module were broken on
purpose and the reds were recorded, one mutation at a time, each restored before the next. The
mutation is applied to BOTH engine twins every time, because mutating one of them reds the
byte-identity assertion and that red would mask whatever the mutation was actually meant to test:

  1. `min(lows)` to `max(lows)` in `combine`: 3 RED. The envelope assertion, and BOTH assertions
     about the committed example record on disk. AND THE INSTRUCTIVE PART: the AC2 positive
     control stayed GREEN, because it compares the record's stored range against the same broken
     combine() that produced it, so it is self-consistent and blind. What caught the mutation was
     the example record's COMMITTED BYTES, whose stored range was written before the break. That
     is the reason a real file on disk is asserted here and not only fixtures built in memory.
  2. dropping the protected-path rework allowance from `expected_review_cycles`: 1 RED, the
     protected-touch monotonicity assertion and nothing else, which is what makes that assertion
     attributable to the allowance rather than to the model in general.
  3. making `validate_record` accept any `calibration`: 1 RED, the calibration-lie assertion,
     while its control (a corpus-grounded layer legitimately reading `calibrated`) stayed green.
     The pair therefore measures the derivation and not the mere presence of a rule.
  4. recording a token scale in the layer's inputs that is not the one used: 1 RED, the assertion
     that the recorded inputs reproduce the layer's own bounds. This is the assertion that keeps
     the record's provenance honest, so it needed to be shown biting on exactly that.

TWO CHECKS IN THIS FILE WERE VACUOUS UNTIL AN INDEPENDENT REVIEW DROVE THEM. The fragment claimed
TWICE that it proved the proxy reads no clock, and it proved nothing of the kind: `committed_at`
was referenced by ZERO assertions, and the determinism assertion compared two calls that PASS THE
SAME DATE ARGUMENT, which agree whether the date came from the argument or from a clock. Both of
the review's mutations left this fragment at 41 passed, 0 failed. The reds below were recorded
against the assertions that replaced it:

  5. `propose` stamping `date.today()` instead of the date passed in: 3 RED - the committed_at
     provenance assertion, the survives-the-write assertion, and the text property that now names
     clock tokens. Its VARIANT reaching the same clock indirectly (`__import__("dateti" + "me")`,
     `utcnow`) reds only the first two and leaves the text property GREEN, which is the honest
     attribution: the text property is the weaker half and cannot see an indirect reach.
  6. `build_record` hardcoding a date: 2 RED, the same two behavioural assertions. Driven twice,
     the second time hardcoded to `_W1402_AT` ITSELF - the value a clock would have returned on the
     day the review ran - because an assertion that compared ONE record against ONE date would stay
     green there. It reds, because the binding is TWO DISTINCT dates over one spec: a date that
     does not come from the argument is the same date twice, whatever that date is.
  7. the ORIGINAL inputs defect restored (the renderer testing `l.get("inputs")` again AND the
     validator no longer refusing an empty map): 2 RED, the write-and-read-back assertion and the
     empty-map pair. Each half of the validator's rule was then removed on its own - the key rule,
     the value rule, the empty-map rule - and each reds the write-and-read-back assertion by
     itself, so that assertion is attributable to all three and not to one of them.
     WHAT STAYED GREEN, ON RECORD: reverting ONLY the renderer to `l.get("inputs")`, with the
     validator left intact. Nothing reds, because a validator that refuses the empty map means the
     renderer can never meet one. The renderer now tests PRESENCE rather than truthiness because
     that is what optional means in this schema, but the GUARANTEE is carried by the validator, and
     this fragment does not claim otherwise.
  8. THE DEFECT ITEM 7 INTRODUCED, and the shape its own table did not have a row for: a layer whose
     `inputs` key is PRESENT WITH A NULL VALUE. Item 7 moved the renderer from truthiness to
     PRESENCE and left the validator reading `l.get("inputs")`, which cannot tell an absent key from
     a null one - so the null stayed VALID and the presence-testing writer went from silently
     dropping it to dying on `sorted(None)`. It is reachable from a FILE, not only from a fixture:
     the ONE parser reads a bare `inputs:` line as null. Restoring the exact pre-fix lines in both
     twins (`l.get("inputs")` plus `if ins is None: return []`) reds 2: the survives-its-own-write
     assertion and the per-key null sweep. Measured separately at that mutation, the record the
     validator blesses takes write_record into `TypeError: 'NoneType' object is not iterable`, which
     is why the write-and-read-back assertion now requires the refusal to be a ValueError and not
     merely an exception. Each half was then driven on its own:
       8a. only the null branch removed from `_inputs_problems`, the sentinel kept: 1 RED, the sweep
           ALONE. The shapes assertion stays green, because the null then falls through to "must be
           a mapping, got NoneType" - a ValueError refusal naming inputs. So the sweep is the
           assertion that pins the REASON and the shapes assertion pins the OUTCOME, and neither
           claims the other's job.
       8b. only the null branch removed from `_note_problems`: 1 RED, the sweep. Driven because the
           FIRST version of the sweep asked only "was there a refusal" and stayed GREEN here, a null
           note being caught anyway by the note's own is-a-string check. The sweep now requires the
           OPTIONAL keys to be refused AS NULL by the shared rule, and that version reds.
       8c. `.get` restored with the null branch DELETED rather than emptied: the fragment DIES at
           build_record rather than showing reds, because `.get` turns an ABSENT inputs key into
           None too and the mapping check then refuses a legitimate layer. Recorded because it is
           the same conflation seen from the other side.
       8d. the NULL row deleted from the shape table: 1 RED, the shapes assertion, on its own
           cardinality binding, so the table cannot be quietly emptied of the row that matters.
       8e. `render_record` no longer asking the validator first: 1 RED, the shapes assertion, on the
           NEVER-A-CRASH clause alone. That clause is otherwise unreachable, and it is what pins the
           order: the writer trusts the one gate instead of defending itself, so one record cannot
           get two verdicts depending on which door it came through.
     RE-DRIVEN WITH THE NULL ROW PRESENT: reverting only the renderer to `l.get("inputs")` still
     reds nothing, for the reason item 7 gives.

WHAT IS DELIBERATELY MEASURED RATHER THAN ARGUED. The load-bearing claim of this item is that an
estimate can never invalidate a spec. That is not asserted by grepping for the absence of a call:
the REAL validate.check_spec is driven over a hermetic repository root three times - with no
estimate, with a valid one, and with a MALFORMED one - and required to return the identical zero,
with the negative control that the same validator DOES refuse a genuinely broken spec under the
same root. An absence that is not paired with a refusal is a check that passed for having looked
nowhere.
"""
import re as _w1402_re
import shutil as _w1402_shutil

_w1402_espec = importlib.util.spec_from_file_location(
    "w1402_estimate", ROOT / ".veldo" / "estimate.py")
E1402 = importlib.util.module_from_spec(_w1402_espec)
_w1402_espec.loader.exec_module(E1402)


def _w1402_probs(rec, spec_id=None):
    """Every problem with one record, joined, so an assertion can require the refusal to NAME
    what is wrong. A bare boolean would pass on any refusal at all, including an unrelated one."""
    return " | ".join(E1402.validate_record(rec, spec_id=spec_id))


def _w1402_raises(fn, *a, **kw):
    """(raised, message). The message is returned because that is what carries the refusal: an
    assertion that something raised, without checking WHAT, passes on a stray TypeError."""
    try:
        fn(*a, **kw)
    except BaseException as e:
        return True, "%s: %s" % (type(e).__name__, e)
    return False, ""


def _w1402_spec_text(spec_id="WARP-9402", risk="standard", acs=2,
                     footprint=(".veldo/nothing_a.py", ".veldo/nothing_b.py")):
    """A fixture spec with exactly the mechanical features under test. Built rather than pinned,
    because every monotonicity assertion below needs two specs differing in ONE feature."""
    lines = ["---", "schema: veldo.spec/v1", "id: %s" % spec_id,
             "title: estimate fixture", "status: ready", "risk: %s" % risk, "owner: selftest"]
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


def _w1402_with_comment(text, after):
    """The same fixture spec with a `#` comment line inserted INSIDE its footprint block, `after`
    items in. A comment is ordinary in this repository's front matter, and until 2026-08-13 the ONE
    footprint reader stopped at it: `after=0` emptied the block and any other position truncated it,
    so the estimate stated a surface and a protected touch it had not measured (finding F3)."""
    lines = text.splitlines()
    i = lines.index("footprint:") + 1 + after
    return "\n".join(lines[:i] + ["  # a comment inside the block, which is not the end of it"]
                     + lines[i:]) + "\n"


_W1402_AT = "2026-08-10"
_W1402_ANALOGY = {"layer": "historical_analogy", "basis": "corpus_analogy",
                  "low": 240000, "high": 1400000,
                  "inputs": {"matched_specs": 12, "corpus_records": 148}}

with tempfile.TemporaryDirectory() as _d:
    _w1402_fix = tmpfile(_d, "WARP-9402-fixture.md", _w1402_spec_text())
    _W1402_GOOD = E1402.propose(_w1402_fix, _W1402_AT)

    # -----------------------------------------------------------------------------------
    # AC1. A RANGE, NEVER A POINT, AND THE UNIT IS PART OF IT.
    # -----------------------------------------------------------------------------------
    expect("WARP-1402 AC1 POSITIVE CONTROL: the record the structural proxy produces for a "
           "fixture spec validates CLEAN through validate_record, so every refusal below is a "
           "refusal of the MUTATION and not of the shape in general. Without this the negative "
           "assertions would all pass on a validator that refuses everything",
           E1402.validate_record(_W1402_GOOD) == []
           and _W1402_GOOD["unit"] == "tokens"
           and _W1402_GOOD["low"] < _W1402_GOOD["high"])

    _w1402_point = dict(_W1402_GOOD, high=_W1402_GOOD["low"])
    _w1402_point["layers"] = [dict(_W1402_GOOD["layers"][0], high=_W1402_GOOD["low"])]
    expect("WARP-1402 AC1: A POINT IS REFUSED BY NAME. low equal to high is rejected and the "
           "message says POINT, on the record AND on the layer, so no shape of this schema can "
           "carry a single number. This is NG6 made structural: false precision is not a thing "
           "an estimator can be talked out of if the schema admits it",
           "POINT" in _w1402_probs(_w1402_point)
           and "POINT" in _w1402_probs(dict(
               _W1402_GOOD, layers=[dict(_W1402_GOOD["layers"][0],
                                         low=_W1402_GOOD["layers"][0]["high"])])))

    expect("WARP-1402 AC1: AN INVERTED RANGE IS REFUSED BY NAME, separately from the point, so "
           "a transposed pair reads as the mistake it is rather than as a very wide range",
           "inverted" in _w1402_probs(dict(_W1402_GOOD, low=_W1402_GOOD["high"],
                                           high=_W1402_GOOD["low"])))

    expect("WARP-1402 AC1: A NON-INTEGER AND A NON-POSITIVE BOUND ARE EACH REFUSED BY NAME. A "
           "string bound is what a hand-typed record produces, and the front-matter subset has "
           "no float, so a bound that is not an integer is not a number this schema can hold",
           "must be an integer" in _w1402_probs(dict(_W1402_GOOD, low="lots"))
           and "must be positive" in _w1402_probs(dict(_W1402_GOOD, low=0)))

    expect("WARP-1402 AC1: THE UNIT IS REQUIRED AND ITS VOCABULARY IS CLOSED. A missing unit is "
           "named as a missing required key, and an unknown one is refused with the declared set "
           "in the message. A range whose unit is unstated is two numbers, and this repository "
           "has already been bitten by a figure whose units were assumed",
           "missing required key 'unit'" in _w1402_probs(
               {k: v for k, v in _W1402_GOOD.items() if k != "unit"})
           and "tokens" in _w1402_probs(dict(_W1402_GOOD, unit="story_points")))

    expect("WARP-1402 AC1: A LAYER MAY NOT SPELL A UNIT OF ITS OWN. The unit is declared once at "
           "the top level, and a layer carrying one is refused with the reason named, because two "
           "spellings of one unit is the second-spelling defect this repository has a rule about "
           "and WARP-1401's own footprint reader exists because of it",
           "second-spelling" in _w1402_probs(dict(
               _W1402_GOOD, layers=[dict(_W1402_GOOD["layers"][0], unit="tokens")])))

    expect("WARP-1402 AC1 NEGATIVE CONTROL ON THE VALIDATOR'S TIGHTNESS: an OPTIONAL key set to "
           "another legal value is ACCEPTED, so the refusals above are not this validator "
           "rejecting every edit. A validator that reds on any mutation proves nothing about "
           "which mutation is wrong",
           E1402.validate_record(dict(_W1402_GOOD, note="a different one-line note")) == [])

    # -----------------------------------------------------------------------------------
    # AC2. THE COMMITTED RANGE IS DERIVED FROM THE LAYERS AND THE RECORD CANNOT LIE ABOUT IT.
    # -----------------------------------------------------------------------------------
    expect("WARP-1402 AC2 POSITIVE CONTROL: the good record's committed range IS what the "
           "declared combination computes over its layers, driven through the same combine() the "
           "validator recomputes with, so the refusals below are attributable to the mutation",
           (_W1402_GOOD["low"], _W1402_GOOD["high"])
           == E1402.combine(_W1402_GOOD["layers"], _W1402_GOOD["combination"]))

    _w1402_wide_msg = _w1402_probs(dict(_W1402_GOOD, high=_W1402_GOOD["high"] + 1))
    expect("WARP-1402 AC2: A COMMITTED RANGE WIDENED BY ONE TOKEN IS REFUSED BY NAME, and so is "
           "one narrowed by a thousand. The validator RECOMPUTES the range from the layers "
           "instead of trusting it, and the message carries both the claimed pair and the "
           "computed one. This is the check that stops a record being edited to look better "
           "before a reconciliation scores it",
           "is not what combination" in _w1402_wide_msg
           and str(_W1402_GOOD["high"]) in _w1402_wide_msg
           and "is not what combination" in _w1402_probs(
               dict(_W1402_GOOD, low=_W1402_GOOD["low"] - 1000)))

    _w1402_enclosed = {"layer": "sizing_pass", "basis": "agent_judgement",
                       "low": _W1402_GOOD["low"] + 1000, "high": _W1402_GOOD["high"] - 1000}
    _w1402_two = E1402.build_record("WARP-9402", _W1402_AT,
                                    [_W1402_GOOD["layers"][0], _W1402_ANALOGY])
    _w1402_encl_rec = E1402.build_record("WARP-9402", _W1402_AT,
                                         [_W1402_GOOD["layers"][0], _w1402_enclosed])
    expect("WARP-1402 AC2: THE ENVELOPE ONLY EVER WIDENS. A second layer reaching higher raises "
           "the committed high and a second layer wholly INSIDE the first does not narrow "
           "anything, both measured over a record built through the real build_record. Averaging "
           "two disagreeing layers into a tighter band than either supports is exactly the false "
           "precision NG6 forbids, so the arithmetic is a union and sharpening is left to a "
           "stronger layer superseding a weaker one",
           _w1402_two["high"] == _W1402_ANALOGY["high"]
           and _w1402_two["low"] == _W1402_GOOD["low"]
           and (_w1402_encl_rec["low"], _w1402_encl_rec["high"])
           == (_W1402_GOOD["low"], _W1402_GOOD["high"]))

    expect("WARP-1402 AC2: AN UNKNOWN COMBINATION RULE IS A REFUSAL THAT NAMES THE DECLARED SET, "
           "in the validator AND in combine() itself, so a later item adds a rule to the table "
           "rather than inventing one a reader will not recognise",
           "combination must be one of" in _w1402_probs(dict(_W1402_GOOD, combination="average"))
           and _w1402_raises(E1402.combine, _W1402_GOOD["layers"], "average")[0]
           and "envelope" in _w1402_raises(E1402.combine, _W1402_GOOD["layers"], "average")[1])

    expect("WARP-1402 AC2: A RECORD WITH NO LAYERS IS REFUSED, because a range with nothing "
           "behind it is a pair of naked numbers and a reconciliation could never attribute it. "
           "combine() refuses the empty set too rather than returning a vacuous pair",
           "non-empty" in _w1402_probs(dict(_W1402_GOOD, layers=[]))
           and _w1402_raises(E1402.combine, [], "envelope")[0])

    # -----------------------------------------------------------------------------------
    # AC3. EVERY LAYER SAYS WHAT IT CONTRIBUTED, AND CALIBRATION IS DERIVED.
    # -----------------------------------------------------------------------------------
    expect("WARP-1402 AC3: the proxy's record carries EXACTLY ONE layer, named structural_proxy, "
           "on basis uncalibrated_prior, and reads calibration: uncalibrated - which is the "
           "inherited measurement doing its job. WARP-1401 measured 0 percent spend coverage over "
           "this repository, so nothing here can be calibrated today and the record says so "
           "rather than presenting a declared scale as a measured one",
           [l["layer"] for l in _W1402_GOOD["layers"]] == ["structural_proxy"]
           and _W1402_GOOD["layers"][0]["basis"] == "uncalibrated_prior"
           and _W1402_GOOD["calibration"] == "uncalibrated")

    expect("WARP-1402 AC3: A CLAIMED CALIBRATION IS REFUSED BY NAME. Flipping calibration to "
           "calibrated over an uncalibrated_prior layer is rejected with the derived value in the "
           "message, so a stated prior can never be dressed as a measurement on the way to a "
           "budget or a dollar figure",
           "calibration is DERIVED" in _w1402_probs(
               dict(_W1402_GOOD, calibration="calibrated")))

    expect("WARP-1402 AC3 CONTROL FOR THAT REFUSAL: a record carrying a corpus-grounded layer IS "
           "accepted as calibrated, so the check is the layer BASES' doing and not a rule that "
           "always refuses the word. Without this control the assertion above would pass on a "
           "validator that hardcoded calibration to uncalibrated forever",
           _w1402_two["calibration"] == "calibrated"
           and E1402.validate_record(_w1402_two) == []
           and E1402.calibration_of([_W1402_ANALOGY]) == "calibrated"
           and E1402.calibration_of(_W1402_GOOD["layers"]) == "uncalibrated")

    expect("WARP-1402 AC3: AN UNKNOWN LAYER ID, AN UNKNOWN BASIS AND A REPEATED LAYER ARE EACH "
           "REFUSED BY NAME, each message carrying the declared vocabulary. The vocabulary is "
           "declared once for the whole plan so W3, W4 and W5 add a record to it rather than "
           "widening it, and a repeated layer is refused because a reconciliation has to be able "
           "to say WHICH layer was right",
           "not one of the declared layers" in _w1402_probs(dict(
               _W1402_GOOD, layers=[dict(_W1402_GOOD["layers"][0], layer="gut_feel")]))
           and "provenance" in _w1402_probs(dict(
               _W1402_GOOD, layers=[dict(_W1402_GOOD["layers"][0], basis="vibes")]))
           and "repeats layer" in _w1402_probs(dict(
               _W1402_GOOD,
               layers=[_W1402_GOOD["layers"][0], dict(_W1402_GOOD["layers"][0])])))

    expect("WARP-1402 AC3: AN UNKNOWN TOP-LEVEL KEY IS REFUSED RATHER THAN IGNORED, with the "
           "declared key set in the message. A schema that ignores what it does not recognise is "
           "a schema three later items can smuggle a field past, and every reader that does not "
           "know the field would keep working while meaning something different",
           "unknown key(s)" in _w1402_probs(dict(_W1402_GOOD, confidence=90))
           and "confidence" in _w1402_probs(dict(_W1402_GOOD, confidence=90)))

    expect("WARP-1402 AC3: A RECORD FILED UNDER THE WRONG NAME IS REFUSED, naming both the "
           "filename it is filed as and the spec it claims. The filename is the key, which is "
           "what makes two estimates for one spec impossible, so the two are checked against each "
           "other rather than one being trusted",
           "the filename is the key" in _w1402_probs(_W1402_GOOD, spec_id="WARP-9999")
           and _w1402_probs(_W1402_GOOD, spec_id="WARP-9402") == "")

    # The renderer and the ONE parser, bound to each other by a round trip rather than by hope.
    expect("WARP-1402 AC3: EVERY RECORD ROUND TRIPS THROUGH THE ONE PARSER. render_record then "
           "validate.parse_yamlish returns the identical dict, for the single-layer record and "
           "for the two-layer one with nested inputs. This is what makes the writer not a second "
           "spelling of the reader: it is bound to it by measurement, and a value the parser "
           "would read back as something else is refused at render time",
           E1402.parse_record(E1402.render_record(_W1402_GOOD)) == _W1402_GOOD
           and E1402.parse_record(E1402.render_record(_w1402_two)) == _w1402_two)

    # THE PART THE ROUND TRIP ABOVE WAS TOO NARROW TO SEE, and the TWO defects it hid. Both records
    # it drives carry a NON-EMPTY inputs map. The inputs map is the ONE place in this schema where
    # the keys and the values are the caller's rather than the vocabulary's, so it is the one place
    # validate_record can bless something the writer cannot write - and it did, twice. An EMPTY map
    # was VALID and the renderer wrote it away WITHOUT A WORD, so the record read back from disk was
    # a different record than the one validated, with no error anywhere to say so. And a NULL one -
    # which is what the ONE parser reads a bare `inputs:` line as, so it arrives from a file and not
    # only from a fixture - was VALID too, because `l.get("inputs")` cannot tell an absent key from
    # a null one; the writer, testing PRESENCE as optional means, then died on `sorted(None)` with
    # an uncaught TypeError. The property is asserted over the KEY'S STATES rather than over those
    # two cases: VALID must mean SURVIVES ITS OWN WRITE, and every state the writer cannot carry
    # must be a REFUSAL that names `inputs` - never a silent drop and never a crash.
    _W1402_DROP = object()          # "not there at all", which dict(layer, inputs=x) cannot say
    _W1402_GOODMAP = "a normal map of numbers"
    _W1402_ABSENT = "the key ABSENT, which is how a layer that read no numbers says so"
    _W1402_NULL = "the key PRESENT and NULL, which is what a bare `inputs:` line parses to"
    _W1402_EMPTY = "the key present and an EMPTY map"
    _W1402_INPUT_SHAPES = (
        (_W1402_GOODMAP, {"acceptance_criteria": 3, "regression_surface": 2}, True),
        ("a map carrying a declared word as well as numbers",
         {"reviews_source": "policy", "reviews_declared": 1}, True),
        (_W1402_ABSENT, _W1402_DROP, True),
        (_W1402_NULL, None, False),
        (_W1402_EMPTY, {}, False),
        ("a key the parser cannot read back as a key", {"a-b": 3}, False),
        ("a key with a space in it", {"a b": 3}, False),
        ("a key opening with a digit", {"1x": 3}, False),
        ("a key that is the empty string", {"": 3}, False),
        ("a value outside the subset's scalars", {"x": 1.5}, False),
        ("a boolean, which the subset has no spelling for", {"x": True}, False),
        ("a nested map, which the block writer cannot carry", {"x": {"y": 1}}, False),
        ("a string where a mapping belongs", "acceptance_criteria=3", False),
        ("a list where a mapping belongs", [3, 2], False),
    )

    def _w1402_shape_rec(_i):
        """_W1402_GOOD with its one layer's inputs put into one state, INCLUDING not being there.
        The absent case needs its own construction on purpose: dict(layer, inputs=x) can say null
        but it cannot say ABSENT, and telling those two apart is the entire subject here."""
        _l = dict(_W1402_GOOD["layers"][0])
        if _i is _W1402_DROP:
            del _l["inputs"]
        else:
            _l["inputs"] = _i
        return dict(_W1402_GOOD, layers=[_l])

    _w1402_shapes = [(_n, _w1402_shape_rec(_i), _ok) for _n, _i, _ok in _W1402_INPUT_SHAPES]
    _w1402_shape = {_n: _r for _n, _r, _ok in _w1402_shapes}

    def _w1402_survives_write(rec, slot):
        """One record all the way to a real file and back through the real reader. Not
        render-then-parse in memory: the claim is that a VALID record survives its own WRITE, so
        the bytes on disk are what is read back."""
        return E1402.read_record(E1402.write_record(
            rec, dirpath=Path(_d) / "shapes" / slot)) == rec

    expect("WARP-1402 AC3: A RECORD validate_record CALLS VALID SURVIVES ITS OWN WRITE AND READ "
           "BACK IN EVERY STATE A LAYER'S `inputs` KEY CAN BE IN, and every state the writer "
           "cannot carry is REFUSED BY NAME with `inputs` in the message - as a ValueError "
           "REFUSAL, never a silent drop and never a crash out of the writer. THE SCOPE IS THAT "
           "KEY AND WHAT THE TABLE ENUMERATES, which is deliberate: this says nothing about the "
           "string VALUES elsewhere in the record, where a padded or all-digit single-line string "
           "is still refused at RENDER time by the assertion below rather than by the validator. "
           "The table enumerates the STATES THIS KEY HAS, which are the branches "
           "_inputs_problems decides between: ABSENT, PRESENT "
           "AND NULL, present and not a mapping, present and an EMPTY mapping, present with a key "
           "the ONE parser cannot read back, present with a value the ONE renderer cannot write, "
           "and present and good. Two of those have failed for real: the EMPTY map validated clean "
           "and then VANISHED on the way to disk (the worst of the three available failures - "
           "raise, refuse, SILENTLY DIFFERENT RECORD), and the NULL one validated clean and then "
           "took the writer into an UNCAUGHT TypeError from sorted(None), because `.get` reads a "
           "present null as an absence. That is why the refusal is required to be a ValueError "
           "here: a TypeError out of the writer is this defect's exact signature. Driven through "
           "the real file and the real reader, bound to the length of its own literal table with "
           "both verdicts present, so emptying it or making it one-sided reds this instead of "
           "passing over nothing",
           len(_W1402_INPUT_SHAPES) == 14 and len(_w1402_shapes) == 14
           and len(_w1402_shape) == 14
           and len({_ok for _n, _i, _ok in _W1402_INPUT_SHAPES}) == 2
           and all(
               (E1402.validate_record(_r) == []
                and E1402.parse_record(E1402.render_record(_r)) == _r
                and _w1402_survives_write(_r, "ok%d" % _j))
               if _ok else
               ("inputs" in _w1402_probs(_r)
                and _w1402_raises(E1402.render_record, _r)[1].startswith("ValueError:")
                and _w1402_raises(E1402.write_record, _r,
                                  Path(_d) / "shapes" / ("no%d" % _j))[1].startswith("ValueError:"))
               for _j, (_n, _r, _ok) in enumerate(_w1402_shapes)))

    expect("WARP-1402 AC3: THE EMPTY INPUTS MAP IS REFUSED FOR THE REASON THAT MAKES IT WRONG, "
           "naming that the key would be dropped on the way to disk, and the SAME layer validates "
           "clean both with the key absent and with a non-empty map. That pair is what makes this "
           "a finding about the EMPTY map rather than a validator that has turned against inputs "
           "in general",
           "present but EMPTY" in _w1402_probs(_w1402_shape[_W1402_EMPTY])
           and "would not be the record that was validated" in _w1402_probs(
               _w1402_shape[_W1402_EMPTY])
           and E1402.validate_record(_w1402_shape[_W1402_ABSENT]) == []
           and E1402.validate_record(_w1402_shape[_W1402_GOODMAP]) == [])

    # THE NULL KEY, AND WHY IT IS ASSERTED OVER EVERY DECLARED KEY RATHER THAN OVER `inputs` ALONE.
    # The defect was never about inputs: it was `d.get(key)`, which returns None for a key that is
    # absent AND for a key that is present with a null value, so every optional key in the schema
    # had it. The sweep below is enumerated FROM THE MODULE'S OWN VOCABULARIES and cross-bound to
    # the writer's own key-order tables, so a key added to this schema tomorrow is swept on the day
    # it is added, and a key the writer writes but this sweep does not reach reds this.
    _W1402_DECL_RECORD = E1402.RECORD_REQUIRED + E1402.RECORD_OPTIONAL
    _W1402_DECL_LAYER = E1402.LAYER_REQUIRED + E1402.LAYER_OPTIONAL
    _w1402_nulled = (
        [("record key %r" % _k, dict(_W1402_GOOD, **{_k: None}), _k in E1402.RECORD_OPTIONAL)
         for _k in _W1402_DECL_RECORD]
        + [("layer key %r" % _k,
            dict(_W1402_GOOD, layers=[dict(_W1402_GOOD["layers"][0], **{_k: None})]),
            _k in E1402.LAYER_OPTIONAL)
           for _k in _W1402_DECL_LAYER])
    # FOUR VERDICTS PER KEY, not one: refused at all, refused as a ValueError REFUSAL through the
    # real writer rather than a crash, and - for the OPTIONAL keys, the ones where absent and null
    # are two different legal-looking states - refused AS NULL by the shared rule. That last column
    # is what makes the assertion attributable: a null note is ALSO caught by the note's own
    # is-a-string check, so requiring only "some refusal" would stay green with the null rule ripped
    # out of it, which was MEASURED (mutation 8b below) rather than reasoned about.
    _w1402_null_verdicts = [
        (_w, _w1402_probs(_r) != "",
         _w1402_raises(E1402.write_record, _r,
                       Path(_d) / "nulls" / ("k%d" % _j))[1].startswith("ValueError:"),
         "PRESENT with a null value" in _w1402_probs(_r) if _opt else True)
        for _j, (_w, _r, _opt) in enumerate(_w1402_nulled)]
    expect("WARP-1402 AC3: EVERY KEY THIS SCHEMA DECLARES IS REFUSED WHEN IT IS PRESENT WITH A "
           "NULL VALUE, in the record scope and in the layer scope, AND THE FAILURE IS A REFUSAL "
           "AND NEVER A CRASH - each one driven through the real write_record and required to come "
           "back a ValueError. This is the assertion that would have caught the defect: a null "
           "`inputs` was VALID, because `d.get(key)` cannot tell an absent key from a null one, and "
           "the writer then died on sorted(None) with an uncaught TypeError - a record the "
           "validator had just called valid, unable to survive its own write. Optional means "
           "PRESENT OR ABSENT and null is neither, which is why the rule is one rule over every "
           "declared key rather than a patch on the one key that was reported. EVERY OPTIONAL KEY "
           "IS ALSO REQUIRED TO BE REFUSED AS NULL, by the shared rule and named as such, because "
           "those are the keys where absent and null are two different legal-looking states - and "
           "because a weaker `some refusal happened` column stays GREEN with the null rule ripped "
           "out of the note, which was measured. The key list is ENUMERATED FROM THE MODULE'S OWN "
           "VOCABULARIES and cross-bound to the writer's key-order tables in both scopes, so it "
           "cannot silently stop covering what the writer writes, and the optional slots are "
           "counted from those vocabularies rather than typed here. PAIRED WITH ITS CONTROLS: both "
           "optional keys validate CLEAN when genuinely absent, so this is a rule about null and "
           "not a validator that has turned against optional keys",
           len(_w1402_null_verdicts) == len(_W1402_DECL_RECORD) + len(_W1402_DECL_LAYER)
           and set(_W1402_DECL_RECORD) == set(E1402.RECORD_ORDER)
           and set(_W1402_DECL_LAYER) == set(E1402.LAYER_ORDER)
           and len([1 for _w, _r, _opt in _w1402_nulled if _opt]) \
           == len(E1402.RECORD_OPTIONAL) + len(E1402.LAYER_OPTIONAL) >= 2
           and all(_refused and _writefailed and _named_as_null
                   for _w, _refused, _writefailed, _named_as_null in _w1402_null_verdicts)
           and "PRESENT with a null value" in _w1402_probs(_w1402_shape[_W1402_NULL])
           and "inputs" in _w1402_probs(_w1402_shape[_W1402_NULL])
           and "note" not in _W1402_GOOD
           and E1402.validate_record(_W1402_GOOD) == []
           and E1402.validate_record(_w1402_shape[_W1402_ABSENT]) == []
           and E1402.validate_record(dict(_W1402_GOOD, layers=[
               {_k: _v for _k, _v in _W1402_GOOD["layers"][0].items() if _k != "note"}])) == [])

    expect("WARP-1402 AC3: THE RENDERER REFUSES A VALUE THAT WOULD NOT READ BACK AS ITSELF, by "
           "name, for the three shapes the front-matter subset really does change: a multi-line "
           "string, a string of digits (which reads back as an integer), and a string opening "
           "with a bracket (which reads back as a list). Refused at write time, because the "
           "alternative is a record that parses into something nobody wrote",
           all(_w1402_raises(E1402.render_record, dict(_W1402_GOOD, note=n))[0]
               and "refusing to render" in _w1402_raises(
                   E1402.render_record, dict(_W1402_GOOD, note=n))[1]
               for n in ("two\nlines", "12345", "[not, a, list]")))

    # The committed example record: real bytes, not an in-memory fixture.
    _w1402_ex = ROOT / ".veldo/examples/estimate-example.yaml"
    _w1402_ex_engine = ROOT / "engine/.veldo/examples/estimate-example.yaml"
    _w1402_ex_rec = E1402.parse_record(_w1402_ex.read_text())
    expect("WARP-1402 AC3: THE COMMITTED EXAMPLE RECORD IS VALID, and it is checked as real bytes "
           "on disk rather than as a fixture built in this file, so the documented shape cannot "
           "drift from the shape the validator accepts. It carries two layers on purpose, so the "
           "derived fields are visible at work, and its engine copy is byte-identical because "
           "that is what /veldo:init lays down for an adopter",
           E1402.validate_record(_w1402_ex_rec) == []
           and len(_w1402_ex_rec["layers"]) == 2
           and _w1402_ex_rec["calibration"] == "calibrated"
           and _w1402_ex.read_bytes() == _w1402_ex_engine.read_bytes())

    expect("WARP-1402 AC3: THE MODULE IS BYTE-IDENTICAL IN BOTH ENGINE HOMES, so what "
           "/veldo:init lays down for an adopter is the module this repository runs and proves. A "
           "schema three later items write into is exactly the thing that must not exist in two "
           "slightly different spellings",
           (ROOT / ".veldo/estimate.py").read_bytes()
           == (ROOT / "engine/.veldo/estimate.py").read_bytes())

    expect("WARP-1402 AC3 CONTROL ON THE EXAMPLE: its committed range is the ENVELOPE of its own "
           "two layers, recomputed here rather than read, so an example edited by hand into "
           "something the schema forbids reds this instead of teaching the wrong shape",
           (_w1402_ex_rec["low"], _w1402_ex_rec["high"])
           == E1402.combine(_w1402_ex_rec["layers"], _w1402_ex_rec["combination"]))

    # -----------------------------------------------------------------------------------
    # AC4. THE STRUCTURAL PROXY: DETERMINISTIC, MECHANICAL, MONOTONE, SCALE-HONEST.
    # -----------------------------------------------------------------------------------
    expect("WARP-1402 AC4: THE PROXY IS DETERMINISTIC IN BOTH THE DICT AND THE BYTES. Two calls "
           "over the same spec and the same date give an identical record and an identical "
           "rendering, so a record can be re-derived years later and compared to the committed "
           "one. This assertion says NOTHING about where the date came from: both calls pass the "
           "same argument, so a propose() that stamped a clock would satisfy it. The date's "
           "PROVENANCE is the assertion below, and it is a separate assertion on purpose",
           E1402.propose(_w1402_fix, _W1402_AT) == _W1402_GOOD
           and E1402.render_record(E1402.propose(_w1402_fix, _W1402_AT))
           == E1402.render_record(_W1402_GOOD))

    # THE RECORDED DATE IS THE DATE THE CALLER PASSED IN. Two DIFFERENT dates over ONE spec is the
    # construction that binds it: a clock-reading propose() and a hardcoded committed_at both give
    # the SAME date twice, so both make these two records equal and red this. Nothing here compares
    # against today, which is what keeps it biting on every day of the year rather than only on the
    # days the fixture date and the clock happen to disagree.
    _W1402_AT2 = "2019-03-04"
    _w1402_rec_at2 = E1402.propose(_w1402_fix, _W1402_AT2)
    _w1402_at_lines = [[ln for ln in E1402.render_record(r).splitlines()
                        if ln.startswith("committed_at:")]
                       for r in (_W1402_GOOD, _w1402_rec_at2)]
    expect("WARP-1402 AC4: committed_at IS THE DATE THE CALLER PASSED IN, AND NOTHING ELSE IN THE "
           "RECORD DEPENDS ON IT. The same fixture spec proposed at two DISTINCT declared dates "
           "gives two records that carry those two dates, that are otherwise IDENTICAL key for "
           "key, and whose rendered bytes differ in exactly the one committed_at line. This is "
           "the field that makes a record a commitment made BEFORE the work, so a date supplied "
           "by a clock at write time would silently turn every estimate into a postdated guess "
           "that reconciliation could never contradict. Bound to two distinct literals, so "
           "collapsing them to one date reds this instead of passing over one date twice",
           _W1402_AT != _W1402_AT2
           and _W1402_GOOD["committed_at"] == _W1402_AT
           and _w1402_rec_at2["committed_at"] == _W1402_AT2
           and {k: v for k, v in _w1402_rec_at2.items() if k != "committed_at"}
           == {k: v for k, v in _W1402_GOOD.items() if k != "committed_at"}
           and _w1402_at_lines == [["committed_at: %s" % _W1402_AT],
                                   ["committed_at: %s" % _W1402_AT2]]
           and [ln for ln in E1402.render_record(_w1402_rec_at2).splitlines()
                if not ln.startswith("committed_at:")]
           == [ln for ln in E1402.render_record(_W1402_GOOD).splitlines()
               if not ln.startswith("committed_at:")])

    expect("WARP-1402 AC4: THE SAME DATE SURVIVES THE WRITE. build_record's seam and the file on "
           "disk carry the caller's date too, read back through the real reader, so the binding "
           "above is a property of the RECORD and not of one constructor. A record whose date is "
           "re-derived at write time would be a commitment nobody made",
           E1402.build_record("WARP-9402", _W1402_AT2,
                              [_W1402_GOOD["layers"][0]])["committed_at"] == _W1402_AT2
           and E1402.parse_record(E1402.render_record(_w1402_rec_at2))["committed_at"]
           == _W1402_AT2
           and E1402.read_record(E1402.write_record(
               _w1402_rec_at2, dirpath=Path(_d) / "atdir"))["committed_at"] == _W1402_AT2)

    _w1402_ac5 = E1402.structural_proxy(tmpfile(_d, "acs5.md", _w1402_spec_text(acs=5)))
    _w1402_ac2 = _W1402_GOOD["layers"][0]
    _W1402_FP6 = tuple(".veldo/nothing_%d.py" % i for i in range(6))
    _w1402_surface6 = E1402.structural_proxy(tmpfile(
        _d, "surface6.md", _w1402_spec_text(footprint=_W1402_FP6)))
    expect("WARP-1402 AC4: MORE ACCEPTANCE CRITERIA AND A LARGER REGRESSION SURFACE EACH WIDEN "
           "THE RANGE STRICTLY, on both bounds, with one feature changed at a time. Monotonicity "
           "is the only property a structural proxy can be held to before there are actuals to "
           "fit it against: the SCALE may be wrong, but the ordering must not be",
           _w1402_ac5["low"] > _w1402_ac2["low"] and _w1402_ac5["high"] > _w1402_ac2["high"]
           and _w1402_surface6["low"] > _w1402_ac2["low"]
           and _w1402_surface6["high"] > _w1402_ac2["high"]
           and _w1402_ac5["inputs"]["acceptance_criteria"] == 5
           and _w1402_surface6["inputs"]["regression_surface"] == 6)

    _W1402_RISKS = ("low", "standard", "high", "critical")
    _w1402_by_risk = [E1402.structural_proxy(tmpfile(
        _d, "risk_%s.md" % r, _w1402_spec_text(risk=r))) for r in _W1402_RISKS]
    expect("WARP-1402 AC4: THE RANGE IS STRICTLY MONOTONE IN THE RISK TIER across all four "
           "declared tiers, and the four ranges are four DISTINCT ranges. That second half is the "
           "anti-vacuity control: a proxy that returned one constant would satisfy every "
           "refusal assertion in this fragment and be worthless. Bound to the length of its own "
           "literal tier tuple, so emptying it reds this instead of passing over nothing",
           len(_W1402_RISKS) == 4 and len(_w1402_by_risk) == 4
           and len({(l["low"], l["high"]) for l in _w1402_by_risk}) == 4
           and all(_w1402_by_risk[i]["low"] < _w1402_by_risk[i + 1]["low"]
                   and _w1402_by_risk[i]["high"] < _w1402_by_risk[i + 1]["high"]
                   for i in range(3)))

    _w1402_prot = E1402.structural_proxy(_w1402_fix, protected=(".veldo/nothing_a.py",))
    expect("WARP-1402 AC4: A PROTECTED-PATH TOUCH STRICTLY WIDENS THE RANGE, measured on the SAME "
           "spec with only the protected set changed, and the layer records the touch and the "
           "rework it charged for it. A protected path forces a recorded human approval bound to "
           "the exact commit, so any later fix invalidates it and costs a whole cycle again - the "
           "one mechanical feature of a spec that reliably predicts a wait on a person",
           _w1402_prot["low"] > _w1402_ac2["low"] and _w1402_prot["high"] > _w1402_ac2["high"]
           and _w1402_prot["inputs"]["protected_touch"] == "yes"
           and _w1402_ac2["inputs"]["protected_touch"] == "no"
           and _w1402_prot["inputs"]["protected_rework"] == E1402.PROTECTED_REWORK
           and _w1402_prot["inputs"]["expected_review_cycles"]
           == _w1402_ac2["inputs"]["expected_review_cycles"] + E1402.PROTECTED_REWORK)

    _w1402_min = E1402.structural_proxy(tmpfile(
        _d, "minimal.md", _w1402_spec_text(risk="low", acs=1, footprint=())))
    expect("WARP-1402 AC4: THE SMALLEST POSSIBLE SPEC STILL GETS A RANGE AND NOT A POINT, and a "
           "spec with NO footprint block yields a regression surface of 0 rather than raising - "
           "which is exactly the way WARP-1401's duplicated footprint reader failed, and the "
           "reason this layer reads its features through that module's ONE reader instead of "
           "spelling the regex again. Rounding is allowed to coarsen a range, never to collapse it",
           _w1402_min["low"] < _w1402_min["high"]
           and _w1402_min["inputs"]["regression_surface"] == 0
           and _w1402_min["low"] >= E1402.ROUND_STEP)

    # FINDING F3, THE CONFIDENT ZERO IN THIS RECORD'S OWN FEATURE READ. The ONE footprint reader
    # required the line after `footprint:` to be a list item and stopped at the first line that was
    # not one, so a COMMENT truncated the block and a comment on its first line emptied it. This
    # layer then published `regression_surface` and `protected_touch` as MEASUREMENTS. Measured over
    # this repository by the independent review: 8 of 215 specs got a materially wrong committed
    # record and 3 said protected_touch: no about a spec that DOES touch a declared protected path;
    # VELDO-0010 read 0 of 13 entries and committed 120000-750000 where the correct read gives
    # 375000-2344000. The three rows below are over FIXTURES on purpose - every one of them is a
    # defect by construction, so none of them pins how many specs in this tree happen to carry a
    # comment today, and specs gaining or losing comments cannot make any of them red.
    def _w1402_layer(path, **kw):
        """The layer for one fixture spec, or None when the proxy REFUSED it. CAPTURED rather than
        called inline: with the pre-fix reader these fixtures make the proxy raise, and an
        uncaught raise at this level reds NO row - it kills the fragment and takes every later row
        with it, which is ledger finding 67's shape and reads exactly like a mutation that deleted
        coverage. Driven: with the comment skip removed this returns None and the two rows below
        red, with the run's total unchanged."""
        try:
            return E1402.structural_proxy(path, **kw)
        except Exception:
            return None

    _w1402_cmt_first = _w1402_layer(tmpfile(
        _d, "cmt_first.md", _w1402_with_comment(_w1402_spec_text(footprint=_W1402_FP6), 0)))
    _w1402_cmt_mid = _w1402_layer(tmpfile(
        _d, "cmt_mid.md", _w1402_with_comment(_w1402_spec_text(footprint=_W1402_FP6), 3)))
    expect("WARP-1402 AC4 (finding F3): A COMMENT INSIDE THE FOOTPRINT BLOCK CHANGES NOTHING ABOUT "
           "THE MEASURED SURFACE. The surface equals the block's OWN item count with the comment "
           "first (the shape that emptied the read) and with the comment part way down (the shape "
           "that truncated it), and both records are the SAME RANGE as the comment-free spec with "
           "the same six entries - which is the binding that makes this about the reader rather "
           "than about one arithmetic path. Bound to the length of the fixture's own footprint "
           "tuple, so shortening the fixture reds this instead of agreeing with a smaller answer",
           len(_W1402_FP6) == 6
           and _w1402_cmt_first is not None and _w1402_cmt_mid is not None
           and _w1402_cmt_first["inputs"]["regression_surface"] == len(_W1402_FP6)
           and _w1402_cmt_mid["inputs"]["regression_surface"] == len(_W1402_FP6)
           and (_w1402_cmt_first["low"], _w1402_cmt_first["high"])
           == (_w1402_surface6["low"], _w1402_surface6["high"])
           and (_w1402_cmt_mid["low"], _w1402_cmt_mid["high"])
           == (_w1402_surface6["low"], _w1402_surface6["high"]))

    _W1402_PROT_ONE = ".veldo/protected_only_entry.py"
    _w1402_cmt_prot = _w1402_layer(
        tmpfile(_d, "cmt_prot.md", _w1402_with_comment(
            _w1402_spec_text(footprint=(_W1402_PROT_ONE,)), 0)),
        protected=(_W1402_PROT_ONE,))
    expect("WARP-1402 AC4 (finding F3): A PROTECTED PATH HIDDEN BEHIND A COMMENT IS STILL FOUND. A "
           "spec whose footprint block opens with a comment and declares exactly one entry, that "
           "entry being protected, records protected_touch: yes and charges the protected rework. "
           "This is the half that mattered most in the live corpus: three committed records said "
           "protected_touch: no about specs that touch a protected path, and this model's own "
           "comment calls that the one mechanical feature that reliably predicts a wait on a person",
           _w1402_cmt_prot is not None
           and _w1402_cmt_prot["inputs"]["protected_touch"] == "yes"
           and _w1402_cmt_prot["inputs"]["protected_rework"] == E1402.PROTECTED_REWORK
           and _w1402_cmt_prot["inputs"]["regression_surface"] == 1)

    _w1402_unread = tmpfile(_d, "unreadable.md", _w1402_spec_text(footprint=_W1402_FP6).replace(
        '  - "%s"' % _W1402_FP6[0], '  "%s"' % _W1402_FP6[0], 1))
    _w1402_unread_out = _w1402_raises(E1402.structural_proxy, _w1402_unread)
    expect("WARP-1402 AC4 (finding F3): A FOOTPRINT BLOCK THAT IS PRESENT AND READS EMPTY IS A "
           "REFUSAL, NEVER A SURFACE OF 0. The fixture declares a block whose first line the ONE "
           "reader cannot read as an item, so the block yields nothing while plainly existing, and "
           "the proxy refuses BY NAME rather than recording a zero it never measured - the fix for "
           "the comment shape repairs the shapes we know about, and this is what keeps the next "
           "unreadable one from arriving as a confident measurement. THE CONTROL IS THE ROW ABOVE, "
           "bound here as well: the same fixture with NO block at all estimates fine at surface 0, "
           "so this refuses an unreadable block and not an absent one",
           _w1402_unread_out[0] and _w1402_unread_out[1].startswith("ValueError:")
           and "reads as EMPTY" in _w1402_unread_out[1]
           and _w1402_min["inputs"]["regression_surface"] == 0)

    _w1402_in = _w1402_ac2["inputs"]
    _w1402_point_from_inputs = (_w1402_in["structural_weight_tenths"]
                                * _w1402_in["tokens_per_structural_unit"] // 10)
    # EVERY KEY THE TWO ROWS BELOW ADD IS READ THROUGH A CAPTURE, not indexed inline. A layer that
    # stopped recording one of them would otherwise raise KeyError out of the assertion expression,
    # which reds the row by KILLING THE RUN and takes every later row with it - the shape ledger
    # finding 67 records, where the evidence for a mutation became "some row went red and the run got
    # shorter". A missing key now makes the weight unrecomputable, which reds the NAMED row and
    # nothing else.
    _W1402_COEFF_KEYS = ("base_tenths", "ac_tenths", "surface_tenths")
    _w1402_coeffs = {k: _w1402_in.get(k) for k in _W1402_COEFF_KEYS}
    _w1402_weight_from_record = (
        (_w1402_coeffs["base_tenths"]
         + _w1402_coeffs["ac_tenths"] * _w1402_in["acceptance_criteria"]
         + _w1402_coeffs["surface_tenths"] * _w1402_in["regression_surface"])
        * _w1402_in["expected_review_cycles"]
        if all(isinstance(v, int) and not isinstance(v, bool)
               for v in _w1402_coeffs.values()) else None)
    expect("WARP-1402 AC4: THE LAYER'S RECORDED INPUTS ARE SUFFICIENT TO REPRODUCE ITS OWN "
           "BOUNDS, recomputed here FROM THE RECORD ALONE and from no module constant: weight from "
           "the coefficients the record names, then weight times scale, spread applied, rounded. "
           "THIS is what buys the plan its reconciliation: because the structural WEIGHT, the "
           "coefficients behind it and the token SCALE are all on record, W5 can tell a good "
           "estimate (weight right, scale right) from a lucky one (both wrong in opposite "
           "directions) and refit the scale without touching the structure. IT READS THE RECORD "
           "RATHER THAN THE MODULE ON PURPOSE, and that is finding F6: while the coefficients were "
           "absent from the record this row recomputed the weight from today's BASE_TENTHS, "
           "AC_TENTHS and SURFACE_TENTHS, so changing a coefficient moved both sides together and "
           "the row could not fail for it - and no reader of an OLD record could have decomposed "
           "its weight at all",
           _w1402_ac2["low"] == E1402._round_tokens(
               _w1402_point_from_inputs * 100 // _w1402_in["spread_pct"])
           and _w1402_ac2["high"] == E1402._round_tokens(
               _w1402_point_from_inputs * _w1402_in["spread_pct"] // 100)
           and _w1402_weight_from_record == _w1402_in["structural_weight_tenths"])

    expect("WARP-1402 AC4 (finding F6): THE RECORD NAMES THE MODEL THAT PRODUCED IT, and the "
           "numbers it names are the ones the module actually used. The layer carries weight_model "
           "plus every coefficient the weight is built from and the scale it multiplied by, and each "
           "equals the module's own constant - so a layer that recorded a coefficient set it did not "
           "use reds THIS row, while the reproduction row above stays honest by reading only the "
           "record. Both halves are needed and they are separate assertions: one says the record is "
           "self-contained, this one says it is TRUE. Bound to a non-empty model name, because a "
           "blank one would identify nothing while looking like provenance",
           _w1402_in.get("weight_model") == E1402.WEIGHT_MODEL
           and isinstance(E1402.WEIGHT_MODEL, str) and E1402.WEIGHT_MODEL.strip()
           and _w1402_coeffs == {"base_tenths": E1402.BASE_TENTHS,
                                 "ac_tenths": E1402.AC_TENTHS,
                                 "surface_tenths": E1402.SURFACE_TENTHS}
           and _w1402_in["tokens_per_structural_unit"] == E1402.TOKENS_PER_STRUCTURAL_UNIT
           and _w1402_in["spread_pct"] == E1402.SPREAD_PCT)

    expect("WARP-1402 AC4: AN UNDECLARED RISK TIER IS A REFUSAL AND NEVER A GUESS. The proxy "
           "refuses to estimate a spec whose tier it cannot read, naming the tiers it knows, and "
           "refusing to estimate blocks nothing because the spec stands without an estimate. "
           "Silently treating an unknown tier as standard is how a wrong number gets a confident "
           "range around it",
           _w1402_raises(E1402.structural_proxy, tmpfile(
               _d, "weird.md", _w1402_spec_text(risk="apocalyptic")))[0]
           and "not a declared tier" in _w1402_raises(E1402.structural_proxy, tmpfile(
               _d, "weird2.md", _w1402_spec_text(risk="apocalyptic")))[1])

    expect("WARP-1402 AC4: THE PROXY'S DEFAULT TIER TABLE COVERS EXACTLY THE RISK VOCABULARY "
           "validate.py DECLARES, as a set equality and not a count, so a tier added to the "
           "contract reds this instead of silently falling through to a refusal at the moment "
           "someone writes the first spec at that tier",
           set(E1402.DEFAULT_REVIEWS) == V.RISKS and set(E1402.DEFAULT_GATE) == V.RISKS)

    # THE MEASURED FINDING OF THIS ITEM, ASSERTED AS THE PROPERTY IT IS AND NOT AS TODAY'S ANSWER.
    # What stood here required policy_tier('critical')[2] == 'default', which is true only because
    # this repository's policy.yaml writes that tier across two lines and the ONE parser folds the
    # continuation into the preceding scalar. So REPAIRING that file - the same inline map on one
    # line, changing no meaning - turned this row RED, inside CHECK_unit, a required stage: the row
    # required the file this item's own docstring calls out to STAY broken (finding F5, ledger
    # finding 51's shape). The property it was standing in for is the one below, and it holds under
    # either state of that file: every tier states which of the two sources it got, and the source it
    # states is the source it USED. Nothing here requires any tier to have any particular source, and
    # the repair reds nothing.
    _W1402_POLDOC = V.parse_yamlish((ROOT / ".veldo/policy.yaml").read_text())
    _W1402_POLTIERS = _W1402_POLDOC.get("risk_tiers") if isinstance(_W1402_POLDOC, dict) else None

    def _w1402_readable_tier(name):
        """What the declared policy offers for one tier THROUGH THE ONE PARSER: a (reviews, gate)
        pair when the file really carries a readable map for it, else None. This is the same
        question policy_tier asks, so 'the source it states is the source it used' is checkable
        without a second opinion about what the file says."""
        t = _W1402_POLTIERS.get(name) if isinstance(_W1402_POLTIERS, dict) else None
        if not isinstance(t, dict):
            return None
        r, g = t.get("reviews"), t.get("gate")
        if isinstance(r, int) and not isinstance(r, bool) and r > 0 and g in E1402.GATE_REWORK:
            return r, g
        return None

    _w1402_sources = {t: E1402.policy_tier(t) for t in sorted(V.RISKS)}
    expect("WARP-1402 AC4 MEASURED OVER THE REAL POLICY: for EVERY declared risk tier, the record's "
           "stated source is the source the number came from. A tier the declared .veldo/policy.yaml "
           "really offers through the ONE parser is read from it and says `policy` with the file's "
           "own numbers; a tier it does not offer falls back and says `default` with the declared "
           "default table's numbers. That is the property the record needs, because a default hidden "
           "inside a record that looks like a policy reading is the kind of number a later analysis "
           "over-trusts. IT REQUIRES NO TIER TO HAVE ANY PARTICULAR SOURCE: this repository's "
           "`critical` tier is written across two lines and folds, so it reads `default` today, and "
           "repairing that file is a change this row must not punish. The teeth are in the two "
           "hermetic fixtures below, which drive BOTH routes whatever this file happens to say",
           set(_w1402_sources) == set(V.RISKS)
           and all(s in ("policy", "default") for _r, _g, s in _w1402_sources.values())
           and all((_w1402_readable_tier(t) == (r, g)) if s == "policy"
                   else (_w1402_readable_tier(t) is None
                         and (r, g) == (E1402.DEFAULT_REVIEWS[t], E1402.DEFAULT_GATE[t]))
                   for t, (r, g, s) in _w1402_sources.items()))

    _w1402_polroot = Path(_d) / "polroot"
    (_w1402_polroot / ".veldo").mkdir(parents=True)
    (_w1402_polroot / ".veldo" / "policy.yaml").write_text(
        "schema: veldo.policy/v1\nrisk_tiers:\n"
        "  critical: {gate: expanded, reviews: 3, min_independence: L2}\n")
    _w1402_polroot_none = Path(_d) / "noplace"
    _w1402_polroot_none.mkdir()
    # THE FOLDED SHAPE AS A FIXTURE, so the finding this item measured is driven hermetically and
    # not by requiring the live file to keep it. Same tier, same meaning, written across two lines.
    _w1402_polroot_fold = Path(_d) / "polfold"
    (_w1402_polroot_fold / ".veldo").mkdir(parents=True)
    (_w1402_polroot_fold / ".veldo" / "policy.yaml").write_text(
        "schema: veldo.policy/v1\nrisk_tiers:\n"
        "  critical: {gate: expanded, reviews: 3, min_independence: L2,\n"
        "             human_approval: true}\n")
    expect("WARP-1402 AC4 CONTROL FOR THAT FINDING, AND IT NOW CARRIES THE WHOLE WEIGHT: three "
           "hermetic policy roots, three answers. The SAME tier on ONE line reads `policy` with the "
           "fixture's own 3 reviews; the SAME tier written across TWO lines reads `default`, which "
           "is the folding this item measured, reproduced without requiring any live file to stay "
           "unreadable; and a root with no policy at all falls back for every tier, which is the "
           "adopting repository's case. So the fallback is the line FOLDING and not a hardcoded "
           "refusal of the critical tier, and a policy_tier that always claimed `policy` reds the "
           "second and third of these",
           E1402.policy_tier("critical", root=_w1402_polroot) == (3, "expanded", "policy")
           and E1402.policy_tier("critical", root=_w1402_polroot_fold)
           == (E1402.DEFAULT_REVIEWS["critical"], E1402.DEFAULT_GATE["critical"], "default")
           and E1402.policy_tier("standard", root=_w1402_polroot_none)[2] == "default")

    expect("WARP-1402 AC4: THE PROXY REACHES FOR NOTHING OUTSIDE THE REPOSITORY AND NAMES NO "
           "CLOCK. Its source names no subprocess, socket or urllib import, so it cannot spawn a "
           "process or open a connection, and it declares no daemon or timer (NG5); it also names "
           "no clock source at all, so there is nowhere for a date to enter except the argument. "
           "This is a TEXT property and it is the WEAKER half: a clock reached indirectly would "
           "pass it. The behavioural half is the committed_at provenance assertion above, which "
           "is what actually proves the recorded date is the one the caller passed in",
           all(tok not in (ROOT / ".veldo/estimate.py").read_text()
               for tok in ("import subprocess", "import socket", "import urllib", "Popen(",
                           "import datetime", "import time", "date.today", "datetime.now",
                           "time.time")))

    # -----------------------------------------------------------------------------------
    # AC5. ADOPTION SAFE, AND NEVER A BLOCKER. The load-bearing pair of this item.
    # -----------------------------------------------------------------------------------
    _w1402_absent = Path(_d) / "no_such_estimates_dir"
    expect("WARP-1402 AC5: WITH NO RECORDS PRESENT EVERY READER STANDS DOWN SILENTLY AND CREATES "
           "NOTHING. load_dir gives an empty set with no problems, estimate_for gives None, "
           "check_dir reports nothing checked, and the directory is STILL absent afterwards. A "
           "repository that never uses this is byte-identically unaffected, which is the only "
           "posture under which adding an estimator to a working gate is safe",
           E1402.load_dir(_w1402_absent) == ({}, [])
           and E1402.estimate_for("WARP-9402", dirpath=_w1402_absent) is None
           and E1402.check_dir(_w1402_absent) == (0, 0)
           and not _w1402_absent.exists())

    _w1402_cli = subprocess.run(
        [sys.executable, str(ROOT / ".veldo/estimate.py"), "check", "--dir", str(_w1402_absent)],
        capture_output=True, text=True, cwd=str(ROOT))
    expect("WARP-1402 AC5: THE CLI'S check EXITS 0 AND SAYS IT IS STANDING DOWN when nothing is "
           "committed, driven as a real process. A tool that exits non-zero on the absence of an "
           "optional record would turn an advisory estimator into a gate the first time somebody "
           "wired it into a script, which is precisely NG1",
           _w1402_cli.returncode == 0 and "standing down" in _w1402_cli.stdout
           and "not a finding" in _w1402_cli.stdout)

    # A hermetic repository root: the real contract and policy, a fixture spec, and an estimates
    # directory we control. check_spec accepts repo_root, so the REAL validator runs over it.
    _w1402_root = Path(_d) / "repo"
    (_w1402_root / ".veldo").mkdir(parents=True)
    (_w1402_root / "specs").mkdir()
    for _rel in (".veldo/architecture.yaml", ".veldo/policy.yaml"):
        _w1402_shutil.copy(ROOT / _rel, _w1402_root / _rel)
    _w1402_rspec = _w1402_root / "specs" / "WARP-9402-fixture.md"
    _w1402_rspec.write_text(_w1402_spec_text())
    _w1402_estdir = _w1402_root / ".veldo" / "estimates"

    _w1402_no_est = V.check_spec(_w1402_rspec, repo_root=_w1402_root)
    E1402.write_record(_W1402_GOOD, dirpath=_w1402_estdir)
    _w1402_with_est = V.check_spec(_w1402_rspec, repo_root=_w1402_root)
    (_w1402_estdir / "WARP-9402.yaml").write_text(
        "schema: veldo.estimate/v1\nspec: WARP-9402\nlow: 5\nhigh: 5\nlayers: []\n")
    _w1402_broken_est = V.check_spec(_w1402_rspec, repo_root=_w1402_root)
    _w1402_broken_probs = _w1402_probs(
        E1402.parse_record((_w1402_estdir / "WARP-9402.yaml").read_text()), spec_id="WARP-9402")
    _w1402_bad_spec = _w1402_root / "specs" / "WARP-9403-broken.md"
    _w1402_bad_spec.write_text(_w1402_spec_text(spec_id="WARP-9403").replace(
        "status: ready", "status: donezo"))
    _w1402_bad_spec_errs = V.check_spec(_w1402_bad_spec, repo_root=_w1402_root)

    expect("WARP-1402 AC5, THE LOAD-BEARING ONE: AN ESTIMATE CAN NEVER INVALIDATE A SPEC, "
           "measured by DRIVING the real validate.check_spec over a hermetic repository root "
           "three times - with no estimate, with a valid one written by the real writer, and with "
           "a MALFORMED one (a point range and no layers) - and getting the identical 0 every "
           "time, while validate_record names that malformed record's defects. This is PLAN-0014 "
           "C3 and NG1 as a measurement: the estimate lives BESIDE the spec, so its absence and "
           "even its breakage are invisible to the thing that decides whether a spec is valid",
           (_w1402_no_est, _w1402_with_est, _w1402_broken_est) == (0, 0, 0)
           and "POINT" in _w1402_broken_probs and "non-empty" in _w1402_broken_probs)

    expect("WARP-1402 AC5 NEGATIVE CONTROL FOR THAT PASS: the SAME validator over the SAME "
           "hermetic root DOES refuse a genuinely broken spec, so the three zeros above are the "
           "estimate being irrelevant and not check_spec being blind under this fixture. Without "
           "this control the whole assertion would be a pass earned by looking nowhere",
           _w1402_bad_spec_errs > 0)

    _w1402_mixdir = Path(_d) / "mixed"
    _w1402_mixdir.mkdir()
    E1402.write_record(_W1402_GOOD, dirpath=_w1402_mixdir)
    (_w1402_mixdir / "WARP-9499.yaml").write_text("schema: veldo.estimate/v1\nspec: WARP-9499\n")
    _w1402_loaded, _w1402_loadprobs = E1402.load_dir(_w1402_mixdir)
    expect("WARP-1402 AC5 FAIL CLOSED ON A PRESENT-BUT-BROKEN RECORD: load_dir returns the one "
           "valid record and reports the broken one by path in its problems, rather than quietly "
           "returning a smaller set. Absence stands down; breakage speaks up. Those are different "
           "facts and a reader that cannot tell them apart is the defect WARP-1401's coverage "
           "report exists to avoid",
           sorted(_w1402_loaded) == ["WARP-9402"]
           and len(_w1402_loadprobs) == 1
           and "WARP-9499" in _w1402_loadprobs[0])

    _w1402_overwrite = _w1402_raises(E1402.write_record, _W1402_GOOD, dirpath=_w1402_mixdir)
    expect("WARP-1402 AC5: WRITING OVER A COMMITTED ESTIMATE IS REFUSED BY NAME unless replace is "
           "asked for explicitly, and the replace path DOES write. An estimate is a commitment "
           "made before the work; one silently rewritten afterwards is what makes a "
           "reconciliation score a number that was edited to fit, which is the exact failure "
           "legacy points never noticed they had",
           _w1402_overwrite[0] and "refusing to overwrite" in _w1402_overwrite[1]
           and E1402.write_record(_W1402_GOOD, dirpath=_w1402_mixdir, replace=True).is_file()
           and E1402.read_record(_w1402_mixdir / "WARP-9402.yaml") == _W1402_GOOD)

    # THE DOMAIN OF "NO GATE STAGE NAMES THIS MODULE" IS DERIVED, NOT TWO FILES TYPED HERE.
    # What stood here scanned scripts/verify.sh's slot values plus verify.sh and validate.py for the
    # literal `estimate.py`. The independent review walked straight past it (finding F4): it added a
    # REQUIRED stage that refuses to let work proceed on a WARP-140x spec without a committed
    # estimate - the exact NG1 violation this criterion exists to forbid - by repointing CHECK_extra
    # at a new script, and this fragment stayed 46 passed 0 failed. Over the whole repository the only
    # red was a SIBLING item's derived gate domain (WARP-1409 AC6), which is where the shape below
    # comes from: the stage set is PARSED out of the required catalog and the always-run body and then
    # closed over what each member EXECUTES or LOADS, so a new stage, a repointed slot or a new load
    # edge enters the domain by itself instead of waiting for somebody to add it to a list.
    # AND THE CLAIM IS NARROWED TO WHAT THE ARTIFACT SUPPORTS, which is the other half of F4. A scan
    # over any domain, however derived, cannot see a path a stage COMPUTES - `".veldo/" + "estim" +
    # "ate" + ".py"` is invisible to every one of them, and saying otherwise would be the same
    # overreach in a bigger costume. So this row asserts the two things it can: the domain is real,
    # and no file in it names this module or its records directory. The measurement that carries NG1
    # is the three-way check_spec pair above, which is behavioural and does not care how a path was
    # spelled.
    _W1402_PATH_RE = r"(?:\.veldo|scripts)/[\w./-]+\.(?:py|sh)"
    _W1402_RUN_RE = r"(?:python3|bash|sh)\s+(%s)" % _W1402_PATH_RE
    _w1402_gate_text = (ROOT / "scripts/verify.sh").read_text()
    _w1402_required = _w1402_re.findall(r'^CHECK_(\w+)="required:(.+)"$', _w1402_gate_text,
                                        _w1402_re.M)
    _w1402_stages = sorted(
        {p for _n, _cmd in _w1402_required for p in _w1402_re.findall(_W1402_PATH_RE, _cmd)}
        | set(_w1402_re.findall(_W1402_RUN_RE, _w1402_gate_text)))

    def _w1402_gate_edges(rel):
        """What ONE gate file EXECUTES or LOADS: the commands it shells and the sibling modules it
        hands to importlib. An EXECUTES/LOADS edge and deliberately not a MENTIONS edge - a comment
        naming a path is not a dependency, and a closure built on mentions would drag in half the
        repository and make the absence below unfalsifiable in the other direction."""
        p = ROOT / rel
        if not p.is_file():
            return set()
        t = p.read_text()
        out = set(_w1402_re.findall(_W1402_RUN_RE, t))
        for _grp in _w1402_re.findall(
                r'(?:ROOT|root|base|BASE)\s*/\s*((?:"[^"]+"\s*/\s*)*"[^"]+")', t):
            _cand = "/".join(_w1402_re.findall(r'"([^"]+)"', _grp))
            if _cand.endswith((".py", ".sh")):
                out.add(_cand)
        return {o for o in out if o != rel}

    _w1402_domain = set(_w1402_stages)
    _w1402_frontier = list(_w1402_stages)
    while _w1402_frontier:
        for _w1402_edge in _w1402_gate_edges(_w1402_frontier.pop()):
            if _w1402_edge not in _w1402_domain:
                _w1402_domain.add(_w1402_edge)
                _w1402_frontier.append(_w1402_edge)
    _w1402_domain_texts = {f: (ROOT / f).read_text() for f in sorted(_w1402_domain)
                           if (ROOT / f).is_file()}
    expect("WARP-1402 AC5: THE GATE DOMAIN IS DERIVED AND IT IS REAL, which is the precondition for "
           "the claim below and the thing the two-file scan it replaces never had. Every slot "
           "scripts/verify.sh declares REQUIRED contributes at least one repository path, the "
           "required set covers lint, unit, security, generated, docs and extra, the stage set holds "
           "the scripts those slots name plus the modules the always-run body invokes directly, the "
           "transitive closure over EXECUTES-or-LOADS is STRICTLY LARGER than the stage set, and "
           "every member of it is a file that exists. So a required slot repointed at a new script "
           "reds this rather than leaving a sibling item to catch it",
           len(_w1402_required) >= 6
           and {n for n, _c in _w1402_required} >= {"lint", "unit", "security", "generated", "docs",
                                                    "extra"}
           and all(_w1402_re.findall(_W1402_PATH_RE, _cmd) for _n, _cmd in _w1402_required)
           and set(_w1402_stages) >= {"scripts/check_lint.sh", "scripts/selftest.py",
                                      "scripts/secret_inventory.py", "scripts/check_generated.sh",
                                      "scripts/check_docs.sh", "scripts/check_template_sync.sh",
                                      ".veldo/validate.py", ".veldo/events.py"}
           and _w1402_domain > set(_w1402_stages)
           and sorted(_w1402_domain_texts) == sorted(_w1402_domain))

    expect("WARP-1402 AC5: NO FILE IN THAT DERIVED DOMAIN NAMES THIS MODULE OR ITS RECORDS "
           "DIRECTORY, so no stage the gate runs can refuse, block or delay work because an estimate "
           "was absent, malformed or slow (NG1, PLAN-0014 D4). Asserted over every file the gate "
           "reaches rather than the two this row used to read, and the ONE stage that does load the "
           "module is named rather than glossed: scripts/selftest.py is a required stage and it "
           "executes this fragment, which is a test dependency and the opposite of a consumer. "
           "BOUNDED HONESTLY: this is a text property over a derived domain, and a stage that "
           "COMPUTED the path would pass it - that is stated rather than papered over, and it is why "
           "the load-bearing evidence for NG1 is the three-way check_spec measurement above",
           _w1402_domain_texts != {}
           and all(tok not in t for t in _w1402_domain_texts.values()
                   for tok in ("estimate.py", E1402.ESTIMATES_DIR))
           and "scripts/selftest.py" in _w1402_stages)

# THE SPEC ID BECOMES A PATH, AND UNTIL 2026-08-13 IT WAS REFUSED NOWHERE. Ledger finding 71, found by
# the independent review this item had never had, and REPRODUCED before being fixed: a spec whose `id:`
# is `../policy` is accepted by validate.check_spec with ZERO errors, and write_record then wrote an
# estimate record OVER .veldo/policy.yaml, 3977 bytes down to 848, with no `replace` and no refusal.
# That file declares which paths are PROTECTED and what the risk tiers are, so a shipped writer could
# delete the policy that governs it.
# THE OVERWRITE GUARD DID NOT FAIL, IT WAS ASKED TOO EARLY: `p.exists()` ran before `d.mkdir()`, so for
# `.veldo/estimates/../policy.yaml` it answered about a path that could not resolve yet and said False;
# the write then ran after mkdir when the same path resolved. Both halves are asserted here.
with tempfile.TemporaryDirectory() as _w1402_td:
    _w1402_tr = Path(_w1402_td)
    (_w1402_tr / ".veldo").mkdir(parents=True)
    _w1402_victim = _w1402_tr / ".veldo" / "policy.yaml"
    _w1402_victim.write_text("schema: veldo.policy/v1\nprotected_paths: []\n")
    _w1402_before = _w1402_victim.read_bytes()
    _w1402_trav = dict(_W1402_GOOD, spec="../policy")
    _w1402_out = _w1402_raises(E1402.write_record, _w1402_trav,
                               _w1402_tr / ".veldo" / "estimates")
    expect("WARP-1402 finding 71: A SPEC ID THAT IS A PATH TRAVERSAL IS REFUSED BEFORE IT BECOMES A "
           "PATH, and the file it would have destroyed is BYTE-IDENTICAL afterwards. The refusal is a "
           "ValueError from the writer rather than a crash, and it comes from the claim ledger's ONE "
           "definition of an id that cannot be stored faithfully rather than a second copy of that "
           "rule here. Reproduced before the fix: policy.yaml went 3977 bytes to 848",
           _w1402_out[1].startswith("ValueError:")
           and _w1402_victim.read_bytes() == _w1402_before)
    expect("WARP-1402 finding 71: the refusal NAMES the id and the basename it would have collapsed "
           "onto, because an operator who is told only that a write was refused has to guess which of "
           "their inputs was wrong",
           "../policy" in _w1402_out[1] and ".._policy" in _w1402_out[1])
    # THE ORDERING HALF, asserted separately because the guard was correct and consulted too early.
    _w1402_ed = _w1402_tr / ".veldo" / "estimates2"
    _w1402_ok1 = E1402.write_record(dict(_W1402_GOOD), _w1402_ed)
    _w1402_second = _w1402_raises(E1402.write_record, dict(_W1402_GOOD), _w1402_ed)
    expect("WARP-1402 finding 71: the overwrite guard is consulted where it can ANSWER. A second write "
           "of the same id into a directory that now exists is refused, which is the property the "
           "traversal exposed as order-dependent: the directory is created BEFORE the existence "
           "question rather than after it",
           Path(_w1402_ok1).is_file() and _w1402_second[1].startswith("ValueError:")
           and "refusing to" in _w1402_second[1])
    expect("WARP-1402 finding 71 NEGATIVE CONTROL: a LEGITIMATE spec id still writes, so the rows "
           "above measure the traversal rather than a writer that now refuses everything",
           Path(_w1402_ok1).name.endswith(".yaml") and "policy" not in Path(_w1402_ok1).name)

    # THE TWO HALVES THE FIRST REPAIR LEFT OPEN, both still reproducible at the reviewed commit's
    # successor and both measured before being fixed (finding F1's evidence line, verbatim):
    # `validate_record(build_record('../victim/OWNED', ...)) == []`, and `estimate_for` reading a
    # record back from OUTSIDE the records directory through the same traversal. The writer refused,
    # so nothing was destroyed - but a record whose key is a path was still VALID, and the READ side
    # answered from a file it was never asked to open, which is a wrong answer rather than a crash.
    expect("WARP-1402 finding F1: THE ID RULE LIVES IN validate_record, THE ONE GATE EVERY READER "
           "AND EVERY WRITER HERE ASKS, so build_record, write_record, read_record and estimate_for "
           "all inherit it from one statement instead of four delegations. A record keyed by a "
           "traversal is INVALID and the problem names the id and the basename it would collapse "
           "onto; build_record refuses to assemble one at all. Reproduced before this existed: "
           "validate_record returned [] for exactly this record",
           "cannot be this record's key" in _w1402_probs(_w1402_trav)
           and "../policy" in _w1402_probs(_w1402_trav)
           and ".._policy" in _w1402_probs(_w1402_trav)
           and _w1402_raises(E1402.build_record, "../victim/OWNED", _W1402_AT,
                             [dict(_W1402_GOOD["layers"][0])])[0])

    expect("WARP-1402 finding F1: THE CONTAINMENT HALF, which holds whatever the character rule "
           "turns out to have missed. _record_path is the ONE place an id becomes a path for reading "
           "and for writing both, and it refuses any id whose file resolves outside the records "
           "directory, naming both paths. This is deliberately a SECOND line: the row above is the "
           "rule, this is the property, and deleting either one reds its own row rather than both",
           _w1402_raises(E1402._record_path, _w1402_tr / ".veldo" / "estimates",
                         "../policy")[1].startswith("ValueError:")
           and "OUTSIDE the records directory" in _w1402_raises(
               E1402._record_path, _w1402_tr / ".veldo" / "estimates", "../policy")[1]
           and E1402._record_path(_w1402_ed, "WARP-9402").parent.resolve()
           == _w1402_ed.resolve())

    (_w1402_tr / "outside.yaml").write_text(E1402.render_record(
        dict(_W1402_GOOD, spec="WARP-9402")))
    _w1402_read_out = _w1402_raises(E1402.estimate_for, "../outside", dirpath=_w1402_ed)
    expect("WARP-1402 finding F1: THE READ SIDE REFUSES THE SAME ID INSTEAD OF ANSWERING FROM "
           "OUTSIDE ITS OWN STORE. A real record file is planted one directory ABOVE the records "
           "directory and estimate_for is asked for it by traversal: it refuses by name rather than "
           "reading it back as a committed estimate, which is what it did when measured. THE "
           "ADDITIVE CONTROL IS IN THE SAME ROW: the record legitimately committed in that directory "
           "is still read back in full, so this refuses the traversal and not the reader",
           _w1402_read_out[0] and _w1402_read_out[1].startswith("ValueError:")
           and (_w1402_tr / "outside.yaml").is_file()
           and E1402.estimate_for("WARP-9402", dirpath=_w1402_ed) == _W1402_GOOD)

del _w1402_re, _w1402_shutil
