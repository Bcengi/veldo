"""WARP-1403: the sizing pass, and the reasons each check can fail.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, which always
runs, so its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 16_warp_1403_sizing_pass

WHAT IS OBSERVED HERE, AND HOW. The subject is a SEAM plus a schema, so there are two shapes of
assertion and each is paired with its opposite. Every refusal is paired with the positive control
that the same input is ACCEPTED once corrected, because a validator that refuses everything
passes every negative assertion and is worthless. And every standdown is paired with the seeded
case where the same code speaks up, because an absence that is never contrasted with a presence
is a pass earned by looking nowhere.

THE ASSERTIONS WERE WATCHED FAILING, one deliberate mutation at a time, each restored before the
next. The reds are recorded in the spec's delivery notes; the four that shaped the design:

  1. giving LiveSizingAgent.size a return value instead of a raise (the fabrication this whole
     item exists to make impossible): 2 RED - the fail-loud assertion and the propagation
     assertion - while the injected-agent control stayed GREEN, which is what makes those two
     attributable to the seam and not to the composition.
  2. dropping the brief_digest comparison from _binding_problems: 2 RED - the stale-digest
     refusal and the example-judgement-against-a-real-brief refusal. The clean-judgement control
     stayed green, so the pair measures the binding rather than the presence of a rule.
  3. reporting `tokens_recorded: 0` on an empty ledger instead of omitting the key: 1 RED, the
     honest-omission half of the ledger pair, while the seeded-ledger half stayed green. That is
     exactly the defect the assertion exists for: a zero that reads like a measurement.
  4. re-spelling the point refusal locally instead of fetching W2's bounds rule: 1 RED, the
     one-spelling assertion, while the point refusal itself stayed green - which is the point:
     the behaviour survives a duplicated rule, and only the source-level assertion sees it.

AND THREE ASSERTIONS ADDED 2026-08-11, after an independent review found four of its own mutations
left all 37 assertions green. Three of the four are closed here: two declared refusals nothing
drove, and a reach claim that was four forbidden greps rather than a set. The fourth, an identity
check on the ONE glob compiler, is not among the findings that review's challenger confirmed and is
untouched. Beside them, one honest-omission property that was asserted only over the half of its
domain where 'carrying spend' and 'carrying tokens' coincide is now asserted over the half where
they do not:

  5. gating the ledger's token keys on ANY spend field again (a record with cost_usd and no tokens
     reporting tokens_recorded: 0 beside anchor_available: yes): 1 RED, the per-field control.
  6. neutering layer_vocabulary's layer-id check, its basis check, or _brief_unit's unit-count
     check, one at a time: 1 RED each. All three were declared refusals nothing drove.
  7. importing subprocess under an alias, or __import__("socket"): 1 RED each, on the parsed
     import set. Both were invisible to the four forbidden spellings the old grep listed.

The naming sweep's own reds come from probes rather than module mutations, since no module names
this one: a throwaway file in .veldo, in engine/.veldo and in scripts/ each red it now, and the
first two of those three were green before. The full log is in the spec's remediation note.

AND TWO MORE ADDED LATER THE SAME DAY, because a fresh review of those three found the same defect
class inside the fix. Both were fixture and assertion work; the module is untouched by this round.

  8. `token_spend_events`, whose declared job is to be the BASIS of the token total, was
     indistinguishable from the any-field count: every seeded record carried tokens, so
     len(with_tokens) and len(carrying) were the same number. MEASURED: rewriting the key as
     len(carrying) left the suite at 40 passed. A MIXED ledger (one tokens record beside two
     recorded as cost and as human minutes) is the only shape where the two diverge, and over it
     that same rewrite is 1 RED.
  9. the reach claim named its own residual as EXACTLY TWO dynamic spellings, which is a universal
     claim over a hand-picked pair. MEASURED against the previous revision, each green at 40:
     `os.popen("true")`, `eval("1 + 1")`, `getattr(os, "sys" + "tem")("true")` and this module's OWN
     loader idiom aimed at ../../etc. The claim is now four equalities over the parsed call surface
     plus a pinned execution-target set, and those four are 1 RED each, as are a
     spec_from_file_location outside `_mod` and a `_mod` target reached through a variable.

AND ONE DEFUSED 2026-08-11: THE REAL-LOG LEG WAS A LANDMINE, not a measurement. It ran over the
live event log and asserted `spend_events == 0`, which is not a property of this module - it is the
observation that nobody had called `spend.py` yet. MEASURED in a scratch copy: one sanctioned write,
`.veldo/spend.py record --spec WARP-0100 --basis harness_reported --tokens 750000`, took the
fragment from 42 passed, 0 failed to 41 passed, 1 FAILED, and the assertion that fired was that leg.
The emptiness is now a BRANCH selected by an independent recount of the live log, never an
assertion; the partition and the key-licensing equalities are unconditional. The teeth are intact
and sharper with data present, since the numeric keys must then EQUAL the recount rather than merely
be absent:

 10. with that same spend record in place, `"anchor_available": E.NO` hardcoded (the module claiming
     the stand-down while data exists) is 1 RED, and `out["tokens_recorded"] = 0` beside a present
     key is 1 RED - the two directions this leg has always existed to catch, now catchable over a
     log that HAS spend in it.
"""
import ast as _w1403_ast
import hashlib as _w1403_hashlib
import re as _w1403_re
import shutil as _w1403_shutil

_w1403_sspec = importlib.util.spec_from_file_location(
    "w1403_sizing_pass", ROOT / ".veldo" / "sizing_pass.py")
SP1403 = importlib.util.module_from_spec(_w1403_sspec)
_w1403_sspec.loader.exec_module(SP1403)
E1403 = SP1403._estimate()
SPEND1403 = SP1403._spend()


def _w1403_probs(rec, brief_rec=None):
    """Every problem with one judgement, joined, so an assertion can require the refusal to NAME
    what is wrong. A bare boolean would pass on any refusal at all, including an unrelated one."""
    return " | ".join(SP1403.validate_judgement(rec, brief_rec))


def _w1403_raises(fn, *a, **kw):
    """(raised, message). The message is returned because that is what carries the refusal: an
    assertion that something raised, without checking WHAT, passes on a stray TypeError."""
    try:
        fn(*a, **kw)
    except BaseException as e:
        return True, "%s: %s" % (type(e).__name__, e)
    return False, ""


def _w1403_spec_text(spec_id="WARP-9403", risk="standard", acs=3,
                     footprint=(".veldo/sizing_nothing_a.py", ".veldo/sizing_nothing_b.py")):
    """A fixture spec with exactly the mechanical features under test. Built rather than pinned,
    because the digest-sensitivity assertions each need two specs differing in ONE feature."""
    lines = ["---", "schema: veldo.spec/v1", "id: %s" % spec_id,
             "title: sizing fixture", "status: ready", "risk: %s" % risk, "owner: selftest"]
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


def _w1403_judgement(brief_rec, **over):
    """A judgement bound to a brief: the shape an in-session agent writes, with the digest of the
    brief it actually read. Overridable field by field, so every refusal below changes ONE thing."""
    j = {"schema": SP1403.SCHEMA, "spec": brief_rec["spec"],
         "brief_digest": SP1403.brief_digest(brief_rec),
         "model": "fixture-model-id[1m]", "low": 400000, "high": 1700000,
         "reasoning": "a new schema module, a byte-identical twin and one suite fragment over a "
                      "small existing surface",
         "self_cost_tokens": 9000, "self_cost_basis": "agent_estimate"}
    j.update(over)
    return j


class _W1403Agent(SP1403.SizingAgent):
    """A FAKE in-session agent: it returns the judgement it was constructed with. It stands in
    for the real thing exactly the way the fleet's fake dispatcher hooks do, and the reference
    agent beside it still refuses, so nothing in the shipped path can produce a judgement."""

    def __init__(self, judgement):
        self.judgement = judgement
        self.briefs = []

    def size(self, brief):
        self.briefs.append(brief)
        return dict(self.judgement)


class _W1403Angry(SP1403.SizingAgent):
    """An agent that fails the way a real one fails: it raises something this module does not
    define. Used to measure that NOTHING here catches it and substitutes a number."""

    def size(self, brief):
        raise RuntimeError("the sizing agent fell over")


def _w1403_size(*a, **kw):
    """The composition path with its exception turned into DATA, and this shape is deliberate.

    MEASURED WHILE PROVING THE TEETH: three separate deliberate breaks of this module (a brief
    that stopped being deterministic, a validator that refused everything, and the layer basis
    changed to a calibrated one) all surfaced at the FIRST composition call and took the whole
    fragment down with a traceback, producing zero verdict lines - so the assertions those
    breaks were supposed to red were never seen failing at all. A crash is strictly worse than
    a red: it makes a run that found nothing look like a run that could not look. So a failure
    here is recorded and handed to the assertions, and the composition's own success is an
    assertion like any other."""
    try:
        return SP1403.size(*a, **kw), ""
    except BaseException as e:
        return ({"record": {}, "layer": {}, "judgement": {}, "brief": {}, "brief_digest": ""},
                "%s: %s" % (type(e).__name__, e))


def _w1403_layer(judgement, brief_rec=None):
    """layer_from with its exception turned into DATA, for the same measured reason as
    _w1403_size above: a refusal raised out of a bare call here killed the fragment mid-run and
    silenced every assertion after it."""
    try:
        return SP1403.layer_from(judgement, brief_rec), ""
    except BaseException as e:
        return {}, "%s: %s" % (type(e).__name__, e)


def _w1403_value(fn, *a, **kw):
    """(value, error) - the same crash-into-data discipline for a call whose RESULT an assertion
    needs and not only whether it raised. Every function in this module refuses by RAISING, so a
    bare call inside an assertion is one mutation away from ending the run."""
    try:
        return fn(*a, **kw), ""
    except BaseException as e:
        return None, "%s: %s" % (type(e).__name__, e)


def _w1403_call_surface(tree):
    """EVERY CALL IN A PARSED MODULE, PARTITIONED BY THE SHAPE OF ITS CALLEE, so a claim about what
    a module reaches for can be a set equality over an exhaustive domain instead of a list of the
    spellings somebody thought of. Python's call grammar has exactly three callee shapes and this
    returns all three, so nothing falls outside the partition:

      bare      a Name - `eval(...)`, `__import__(...)`, `len(...)`
      dotted    an Attribute chain rooted at a Name - `os.popen(...)`, `importlib.import_module()`
      computed  a callee that is itself an expression - `getattr(os, "sys" + "tem")(...)`, which is
                where a respelling hides. Reported as the INNER callee's name plus "()" when that
                inner callee is a plain name, so this shape can be enumerated by what produced the
                thing being called rather than dismissed; any other expression shape (a subscript,
                a lambda) is reported as its node type.

    An Attribute chain rooted at something other than a Name (`_estimate().propose(...)`) keeps only
    its attribute part, so it never masquerades as a call into an imported module.

    Returns LISTS and not sets, so a caller can assert a COUNT (how many times the one
    code-executing call is made) as well as a membership."""
    bare, dotted, computed = [], [], []
    for node in _w1403_ast.walk(tree):
        if not isinstance(node, _w1403_ast.Call):
            continue
        fn, parts = node.func, []
        while isinstance(fn, _w1403_ast.Attribute):
            parts.append(fn.attr)
            fn = fn.value
        if parts:
            root = fn.id + "." if isinstance(fn, _w1403_ast.Name) else ""
            dotted.append(root + ".".join(reversed(parts)))
        elif isinstance(fn, _w1403_ast.Name):
            bare.append(fn.id)
        elif isinstance(fn, _w1403_ast.Call) and isinstance(fn.func, _w1403_ast.Name):
            computed.append(fn.func.id + "()")
        else:
            computed.append(type(fn).__name__)
    return bare, dotted, computed


def _w1403_literal_args(tree, fname, argno=0):
    """The set of constant strings passed in one argument position of every call to `fname`, plus
    the count of calls to it that pass something else there. A pinned literal set is only a claim
    about the call's target if no call reaches that position through a variable."""
    lits, computed = set(), 0
    for node in _w1403_ast.walk(tree):
        if not (isinstance(node, _w1403_ast.Call) and isinstance(node.func, _w1403_ast.Name)
                and node.func.id == fname):
            continue
        arg = node.args[argno] if len(node.args) > argno else None
        if isinstance(arg, _w1403_ast.Constant) and isinstance(arg.value, str):
            lits.add(arg.value)
        else:
            computed += 1
    return lits, computed


_W1403_AT = "2026-08-10"

with tempfile.TemporaryDirectory() as _d:
    _w1403_dir = Path(_d)
    _w1403_fix = tmpfile(_d, "WARP-9403-fixture.md", _w1403_spec_text())
    _W1403_BRIEF = SP1403.brief(_w1403_fix)
    _W1403_J = _w1403_judgement(_W1403_BRIEF)
    _W1403_OUT, _W1403_ERR = _w1403_size(_w1403_fix, _W1403_AT, agent=_W1403Agent(_W1403_J))
    _W1403_REC = _W1403_OUT["record"]

    expect("WARP-1403 AC1: THE COMPOSITION PATH COMPLETES, and it is asserted rather than assumed "
           "so that a break in it reds a LABEL instead of killing the run. With a real judgement "
           "behind the seam, size() returns a record carrying exactly two layers - the structural "
           "prior and this pass - with no error. Every assertion below reads that record, so this "
           "is the one that says whether they had anything to read",
           _W1403_ERR == ""
           and [l.get("layer") for l in _W1403_REC.get("layers") or ()]
           == ["structural_proxy", SP1403.LAYER_ID])

    # -----------------------------------------------------------------------------------
    # AC1. THE SEAM FAILS LOUD, AND NOTHING HERE MANUFACTURES A RANGE.
    # -----------------------------------------------------------------------------------
    _w1403_live = _w1403_raises(SP1403.LiveSizingAgent().size, _W1403_BRIEF)
    _w1403_unwired = _w1403_raises(SP1403.size, _w1403_fix, _W1403_AT)
    expect("WARP-1403 AC1: THE REFERENCE AGENT RAISES AND SAYS WHY. LiveSizingAgent refuses with "
           "'Refusing to fabricate a judgement', and size() with no agent wired refuses the same "
           "way rather than falling back to anything. This is the LiveLoop and LiveReviewer "
           "posture: a sizing pass that invented a plausible range would be worse than none, "
           "because the number would be indistinguishable from a prediction and W5 would later "
           "reconcile a real actual against a fabrication",
           _w1403_live[0] and "Refusing to fabricate a judgement" in _w1403_live[1]
           and _w1403_unwired[0] and "no agent is wired" in _w1403_unwired[1])

    _w1403_angry = _w1403_raises(SP1403.size, _w1403_fix, _W1403_AT, agent=_W1403Angry())
    expect("WARP-1403 AC1: A FAILING AGENT'S EXCEPTION PROPAGATES UNCHANGED. An agent that raises "
           "a RuntimeError out of size() takes the whole pass down with its own message; nothing "
           "catches it and substitutes a range. A handler around the agent call IS a fallback, "
           "and a fallback here is a fabricated estimate",
           _w1403_angry[0] and _w1403_angry[1].startswith("RuntimeError")
           and "fell over" in _w1403_angry[1])

    _w1403_nofile = _w1403_raises(
        SP1403.JudgementFileAgent(_w1403_dir / "no_such_judgement.yaml").size, _W1403_BRIEF)
    expect("WARP-1403 AC1: THE FILE AGENT IS TRANSPORT AND SAYS SO. Pointed at a path with no "
           "judgement it refuses by name instead of producing one, because it carries an agent's "
           "judgement and cannot make one",
           _w1403_nofile[0] and "Refusing to fabricate a judgement" in _w1403_nofile[1]
           and "does not make one" in _w1403_nofile[1])

    _w1403_jf = tmpfile(_d, "judgement.yaml", "schema: %s\nspec: %s\nbrief_digest: %s\n"
                                              "model: fixture-model-id\nlow: 400000\n"
                                              "high: 1700000\nreasoning: %s\n"
                                              "self_cost_tokens: 9000\n"
                                              "self_cost_basis: agent_estimate\n"
                        % (SP1403.SCHEMA, _W1403_BRIEF["spec"],
                           SP1403.brief_digest(_W1403_BRIEF), _W1403_J["reasoning"]))
    _w1403_from_file, _w1403_file_err = _w1403_size(
        _w1403_fix, _W1403_AT, agent=SP1403.JudgementFileAgent(_w1403_jf))
    expect("WARP-1403 AC1 POSITIVE CONTROL FOR EVERY REFUSAL ABOVE: with a real judgement behind "
           "the seam the pass DOES produce a record carrying the sizing_pass layer, both through "
           "an injected agent and through a judgement file written in the front-matter subset. "
           "Without this control the four refusals would pass on a module that refuses everything",
           SP1403.layer_of(_W1403_REC) is not None
           and _w1403_file_err == ""
           and (SP1403.layer_of(_w1403_from_file["record"]) or {}).get("low") == 400000
           and E1403.validate_record(_W1403_REC) == []
           and E1403.validate_record(_w1403_from_file["record"]) == [])

    _w1403_other, _w1403_other_err = _w1403_size(_w1403_fix, _W1403_AT, agent=_W1403Agent(
        _w1403_judgement(_W1403_BRIEF, low=333000, high=444000)))
    expect("WARP-1403 AC1 ANTI-VACUITY: THE RANGE IS THE AGENT'S AND NOT THE BRIEF'S. Two "
           "judgements over the SAME brief yield two DIFFERENT layers, each carrying exactly the "
           "bounds the agent gave, and neither pair equals the structural prior in that brief. A "
           "module that quietly derived a range from the features would produce one answer here "
           "and this is the assertion that would catch it",
           ((SP1403.layer_of(_W1403_REC) or {}).get("low"),
            (SP1403.layer_of(_W1403_REC) or {}).get("high"))
           == (_W1403_J["low"], _W1403_J["high"])
           and ((SP1403.layer_of(_w1403_other["record"]) or {}).get("low"),
                (SP1403.layer_of(_w1403_other["record"]) or {}).get("high")) == (333000, 444000)
           and (333000, 444000) != (_W1403_BRIEF["prior"]["low"], _W1403_BRIEF["prior"]["high"]))

    # -----------------------------------------------------------------------------------
    # AC2. THE JUDGEMENT IS VALIDATED FAIL CLOSED, ON W2'S RULES AND W1b'S VOCABULARY.
    # -----------------------------------------------------------------------------------
    expect("WARP-1403 AC2 POSITIVE CONTROL: the judgement a fixture agent writes validates CLEAN "
           "against its own brief, and an OPTIONAL note is accepted, so every refusal below is a "
           "refusal of the MUTATION and not of the shape in general",
           SP1403.validate_judgement(_W1403_J, _W1403_BRIEF) == []
           and SP1403.validate_judgement(
               _w1403_judgement(_W1403_BRIEF, note="one more line"), _W1403_BRIEF) == [])

    _w1403_point = _w1403_probs(_w1403_judgement(_W1403_BRIEF, high=_W1403_J["low"]))
    expect("WARP-1403 AC2: A POINT PREDICTION IS REFUSED BY THE SAME RULE THE RECORD USES, and "
           "the message is W2's own ('is a POINT'), because this module FETCHES that rule instead "
           "of respelling it. An inverted range is refused separately. The sizing pass sharpens a "
           "range by disagreeing visibly; it never becomes a single number",
           "is a POINT" in _w1403_point
           and "inverted" in _w1403_probs(_w1403_judgement(_W1403_BRIEF, low=1700000,
                                                           high=400000))
           and "must be an integer" in _w1403_probs(_w1403_judgement(_W1403_BRIEF, low="lots"))
           and "must be positive" in _w1403_probs(_w1403_judgement(_W1403_BRIEF, low=0)))

    _w1403_saved_bounds = E1403._bounds_problems
    try:
        del E1403._bounds_problems
        _w1403_norule = _w1403_raises(SP1403._bounds_rule)
    finally:
        E1403._bounds_problems = _w1403_saved_bounds
    expect("WARP-1403 AC2: THE POINT REFUSAL HAS EXACTLY ONE SPELLING IN THE ENGINE, and the "
           "fetch is proven by removing it. The bounds rule this module applies IS "
           "estimate._bounds_problems by identity, this module's own source carries no 'is a "
           "POINT' message, and with that rule deleted from the estimate module the fetch REFUSES "
           "rather than falling back to a local copy. Two spellings of one refusal is how one of "
           "the two later starts accepting a point, and this repository has a named rule about it",
           SP1403._bounds_rule() is E1403._bounds_problems
           and "is a POINT" not in (ROOT / ".veldo/sizing_pass.py").read_text()
           and _w1403_norule[0] and "refusing to re-spell" in _w1403_norule[1])

    expect("WARP-1403 AC2: AN UNKNOWN KEY IS REFUSED RATHER THAN IGNORED, and a missing required "
           "key is NAMED. A schema that ignores what it does not recognise is a schema a later "
           "item smuggles a field past, and every reader that does not know the field keeps "
           "working while meaning something else",
           "unknown key(s)" in _w1403_probs(dict(_W1403_J, confidence=90))
           and "confidence" in _w1403_probs(dict(_W1403_J, confidence=90))
           and "missing required key 'model'" in _w1403_probs(
               {k: v for k, v in _W1403_J.items() if k != "model"})
           and "missing required key 'self_cost_tokens'" in _w1403_probs(
               {k: v for k, v in _W1403_J.items() if k != "self_cost_tokens"}))

    expect("WARP-1403 AC2: THE MODEL IDENTITY IS REQUIRED AND THE REASONING HAS A FLOOR. An empty "
           "model is refused, a three-character reasoning is refused with the floor named, and a "
           "MULTI-LINE reasoning is refused because it becomes the estimate layer's note and that "
           "record's renderer would not read a multi-line value back as itself. The floor is on "
           "SAYING something; whether the reasoning is good is a reviewer's judgement",
           "model must be a non-empty" in _w1403_probs(_w1403_judgement(_W1403_BRIEF, model=""))
           and "at least %d are required" % SP1403.MIN_REASONING_CHARS
           in _w1403_probs(_w1403_judgement(_W1403_BRIEF, reasoning="big"))
           and "must be ONE line" in _w1403_probs(
               _w1403_judgement(_W1403_BRIEF, reasoning="a reason that is long enough to pass the "
                                                        "floor\nand then keeps going")))

    expect("WARP-1403 AC2: THE PASS'S OWN COST IS REQUIRED, AND ITS PROVENANCE COMES FROM THE "
           "SPEND RECORDER'S TABLE. A zero or absent token count is refused, an unknown basis is "
           "refused with the declared set in the message, and the accepted set is asserted EQUAL "
           "to spend.BASES rather than listed here - so a provenance added there is accepted here "
           "with no edit, and one removed there stops being accepted here",
           "self_cost_tokens must be a positive integer" in _w1403_probs(
               _w1403_judgement(_W1403_BRIEF, self_cost_tokens=0))
           and "self_cost_basis must be one of" in _w1403_probs(
               _w1403_judgement(_W1403_BRIEF, self_cost_basis="vibes"))
           and set(SPEND1403.BASES) == {b for b in SPEND1403.BASES
                                        if SP1403.validate_judgement(
                                            _w1403_judgement(_W1403_BRIEF,
                                                             self_cost_basis=b)) == []}
           and len(SPEND1403.BASES) >= 4)

    expect("WARP-1403 AC2: A JUDGEMENT OUTSIDE THE PARSER SUBSET IS A REFUSAL THAT CARRIES THE "
           "PARSER'S OWN HINT, and a judgement that parses to something other than a mapping is "
           "refused too. There is no second parser here: it is validate.parse_yamlish or nothing",
           _w1403_raises(SP1403.parse_judgement, "- not\n- a mapping\n")[0]
           and SP1403.parse_judgement("schema: %s\n" % SP1403.SCHEMA) == {
               "schema": SP1403.SCHEMA})

    # -----------------------------------------------------------------------------------
    # AC3. THE BRIEF IS MECHANICAL AND DETERMINISTIC, AND THE DIGEST BINDS THE JUDGEMENT.
    # -----------------------------------------------------------------------------------
    expect("WARP-1403 AC3: THE BRIEF IS DETERMINISTIC IN THE DICT AND IN THE BYTES. Two calls "
           "over the same spec and the same tree give an identical brief, an identical canonical "
           "serialization and an identical digest. Nothing reads a clock and nothing is random, "
           "which is what makes a digest a binding rather than a nuisance",
           SP1403.brief(_w1403_fix) == _W1403_BRIEF
           and SP1403.canonical_brief(SP1403.brief(_w1403_fix))
           == SP1403.canonical_brief(_W1403_BRIEF)
           and SP1403.brief_digest(SP1403.brief(_w1403_fix))
           == SP1403.brief_digest(_W1403_BRIEF)
           and SP1403.DIGEST_RE.match(SP1403.brief_digest(_W1403_BRIEF)))

    _w1403_more_acs = SP1403.brief(tmpfile(_d, "acs.md", _w1403_spec_text(acs=6)))
    _w1403_prot = SP1403.brief(_w1403_fix, protected=(".veldo/sizing_nothing_a.py",))
    # A hermetic root carrying the SAME policy, so the structural prior is unchanged and the ONLY
    # difference is that one footprint path now exists. Without the copied policy the prior would
    # move too and the digest change could not be attributed to the code.
    _w1403_code_root = _w1403_dir / "coderoot"
    (_w1403_code_root / ".veldo").mkdir(parents=True)
    _w1403_shutil.copy(ROOT / ".veldo/policy.yaml", _w1403_code_root / ".veldo/policy.yaml")
    (_w1403_code_root / ".veldo" / "sizing_nothing_a.py").write_text("x = 1\ny = 2\n")
    _w1403_with_code = SP1403.brief(_w1403_fix, root=_w1403_code_root)
    _w1403_seeded = SP1403.brief(_w1403_fix, events=[{"type": "spec.shipped", "tokens": 12345}])
    _w1403_digests = {SP1403.brief_digest(b) for b in
                      (_W1403_BRIEF, _w1403_more_acs, _w1403_prot, _w1403_with_code,
                       _w1403_seeded)}
    expect("WARP-1403 AC3 THE DIGEST IS SENSITIVE TO ALL FOUR THINGS IT CLAIMS TO BIND, measured "
           "as five distinct digests: the original, more acceptance criteria, a protected-path "
           "touch (which moves the structural prior), a footprint file that now EXISTS with bytes "
           "and lines, and a ledger that now carries a spend event. Two of the four are attributed "
           "EXACTLY - the code case differs from the original in the code block ALONE with the "
           "prior identical, and the ledger case in the ledger block alone - so this is not four "
           "changes that happened to move something. It is the anti-vacuity control for the "
           "binding: a constant digest would satisfy the equality assertion above and bind nothing",
           len(_w1403_digests) == 5
           and _w1403_with_code["prior"] == _W1403_BRIEF["prior"]
           and _w1403_with_code["code"] != _W1403_BRIEF["code"]
           and {k: v for k, v in _w1403_with_code.items() if k != "code"}
           == {k: v for k, v in _W1403_BRIEF.items() if k != "code"}
           and {k: v for k, v in _w1403_seeded.items() if k != "ledger"}
           == {k: v for k, v in _W1403_BRIEF.items() if k != "ledger"})

    expect("WARP-1403 AC3: A STALE OR TRANSPLANTED JUDGEMENT IS REFUSED BY NAME. A judgement "
           "carrying the digest of a DIFFERENT brief is refused with both digests in the message, "
           "and a judgement naming a different spec is refused as a judgement about another "
           "question. A judgement is only ever about the brief it was made from",
           "does not match the brief actually read" in _w1403_probs(
               _w1403_judgement(_w1403_more_acs, spec=_W1403_BRIEF["spec"]), _W1403_BRIEF)
           and "cannot be moved to another" in _w1403_probs(
               _w1403_judgement(_W1403_BRIEF, spec="WARP-9999"), _W1403_BRIEF))

    _w1403_facts = SP1403.code_facts(
        [".veldo/sizing_nothing_a.py", ".veldo/sizing_nothing_b.py"], root=_w1403_code_root)
    _w1403_absent_entry = [e for e in _w1403_facts["entries"] if e["kind"] == "absent"][0]
    _w1403_file_entry = [e for e in _w1403_facts["entries"] if e["kind"] == "file"][0]
    expect("WARP-1403 AC3: THE CODE FACTS SEPARATE WHAT EXISTS FROM WHAT WILL BE CREATED, and the "
           "absent one carries NO SIZE AT ALL rather than a zero. Editing a large module and "
           "creating a new file are different sizing problems, and 26 of this repository's 785 "
           "footprint entries are paths that do not exist yet, so this is not a corner case",
           _w1403_facts["existing_files"] == 1 and _w1403_facts["to_create"] == 1
           and _w1403_file_entry["bytes"] == 12 and _w1403_file_entry["lines"] == 2
           and "bytes" not in _w1403_absent_entry and "lines" not in _w1403_absent_entry
           and _w1403_facts["existing_bytes"] == 12 and _w1403_facts["existing_lines"] == 2)

    (_w1403_code_root / "sub").mkdir()
    (_w1403_code_root / "sub" / "a.py").write_text("a\n")
    (_w1403_code_root / "sub" / "b.py").write_text("b\nb\n")
    (_w1403_code_root / "sub" / "skip.pyc").write_bytes(b"\x00\x01")
    (_w1403_code_root / "sub" / "__pycache__").mkdir()
    (_w1403_code_root / "sub" / "__pycache__" / "c.py").write_text("c\n")
    _w1403_glob = SP1403.code_facts(["sub/*.py", "sub/nothing_*.py", "sub"],
                                    root=_w1403_code_root)
    _w1403_pat = [e for e in _w1403_glob["entries"] if e["entry"] == "sub/*.py"][0]
    _w1403_pat0 = [e for e in _w1403_glob["entries"] if e["entry"] == "sub/nothing_*.py"][0]
    _w1403_dir_entry = [e for e in _w1403_glob["entries"] if e["kind"] == "directory"][0]
    expect("WARP-1403 AC3: A GLOB IS RESOLVED THROUGH THE ONE GLOB COMPILER, and a glob matching "
           "nothing is its own fact. 121 of 785 footprint entries in this repository carry a "
           "metacharacter, so a brief that refused to resolve them would be blind on one entry in "
           "six; and an unmatched pattern is counted apart from an absent literal because the "
           "literal is a file to create while the pattern is ambiguous. Bytecode and __pycache__ "
           "are never walked, so a brief's digest cannot depend on what was imported recently",
           Path(SP1403._arch().__file__).resolve() == (ROOT / ".veldo/arch.py").resolve()
           and "[^/]*" not in (ROOT / ".veldo/sizing_pass.py").read_text()
           and "fnmatch" not in (ROOT / ".veldo/sizing_pass.py").read_text()
           and sorted(_w1403_pat["paths"]) == ["sub/a.py", "sub/b.py"]
           and _w1403_pat["lines"] == 3
           and _w1403_pat0["matched"] == 0 and "bytes" not in _w1403_pat0
           and _w1403_glob["patterns"] == 2 and _w1403_glob["patterns_unmatched"] == 1
           and _w1403_glob["to_create"] == 0
           and _w1403_dir_entry["paths"] == ["sub/a.py", "sub/b.py"])

    _w1403_esc = _w1403_raises(SP1403.code_facts, ["../outside.py"])
    _w1403_abs = _w1403_raises(SP1403.code_facts, ["/etc/hostname"])
    expect("WARP-1403 AC3: A FOOTPRINT ENTRY THAT LEAVES THE REPOSITORY IS REFUSED BEFORE "
           "ANYTHING IS READ, both the absolute form and the parent-escape form, each named. A "
           "brief that could read outside the tree is a brief that could be aimed at a secret, "
           "and the refusal happens before the read rather than after it",
           _w1403_esc[0] and "escapes the repository root" in _w1403_esc[1]
           and _w1403_abs[0] and "refusing the absolute footprint entry" in _w1403_abs[1])

    # THE REACH SURFACE, PARSED AND ENUMERATED RATHER THAN GREPPED. A list of forbidden spellings is
    # a list of the spellings somebody thought of: `from subprocess import run`, `__import__("x")`
    # and `import http.client` all evade "import subprocess". The import set closed that, but naming
    # its own residual as EXACTLY TWO dynamic spellings was the same defect in other clothes, and a
    # review of that revision evaded it four ways with every assertion green: `os.popen("true")`
    # (which is neither "os.system(" nor "Popen("), `eval("1 + 1")`, `getattr(os, "sys" + "tem")()`
    # and this module's OWN loader idiom aimed at `../../etc`. So the domain is CLOSED instead of
    # sampled: four equalities over the parsed module, one per shape a reach can take.
    #
    # WHY THOSE SHAPES EXHAUST IT. Foreign code can only enter this module by an import statement
    # (set one), by a builtin call such as `__import__`, `eval`, `exec` or `compile` (set two, every
    # bare-name callee the module does not itself define), by an attribute call into a module it
    # already imported such as `importlib.import_module` or `os.popen` (set three, every dotted
    # callee rooted at an imported name), or by CALLING WHAT A CALL RETURNED, which is the shape
    # `getattr(os, "sys" + "tem")("id")` hides in. That fourth shape is NOT empty here and is not
    # claimed to be: sizing_pass.py:532 calls W2's bounds rule as `_bounds_rule()(rec, ...)`. So it
    # is enumerated by what produced the callee, and the one producer is a function THIS module
    # defines. The one remaining door, the spec_from_file_location idiom this module loads its
    # siblings through, is the assertion below.
    _w1403_src = (ROOT / ".veldo/sizing_pass.py").read_text()
    _w1403_tree = _w1403_ast.parse(_w1403_src)
    _W1403_IMPORTS_ALLOWED = {"argparse", "hashlib", "importlib", "json", "os", "re", "sys",
                              "pathlib"}
    _w1403_imports = set()
    for _w1403_node in _w1403_ast.walk(_w1403_tree):
        if isinstance(_w1403_node, _w1403_ast.Import):
            _w1403_imports.update(_a.name.split(".")[0] for _a in _w1403_node.names)
        elif isinstance(_w1403_node, _w1403_ast.ImportFrom):
            _w1403_imports.add((_w1403_node.module or "").split(".")[0])
    _w1403_defs = {_n.name for _n in _w1403_ast.walk(_w1403_tree)
                   if isinstance(_n, (_w1403_ast.FunctionDef, _w1403_ast.AsyncFunctionDef,
                                      _w1403_ast.ClassDef))}
    _w1403_bare, _w1403_dotted, _w1403_computed = _w1403_call_surface(_w1403_tree)
    # Every bare-name callee this module does not define with a def or a class: builtins, plus
    # `Path` from its one `from` import and `rx`, the ONE glob compiler it fetches from arch.py at
    # sizing_pass.py:340. eval, exec, __import__, compile and open are refused by the EQUALITY.
    _W1403_BARE_ALLOWED = {"Path", "SystemExit", "any", "callable", "enumerate", "getattr", "int",
                           "isinstance", "len", "list", "min", "print", "rx", "set", "sorted",
                           "str", "sum", "tuple", "type"}
    # Every call this module makes into a module it imports. os.popen, os.system, os.execv,
    # os.spawnl and importlib.import_module are refused by the EQUALITY, not by being listed.
    _W1403_MODULE_CALLS = {"argparse.ArgumentParser", "hashlib.sha256",
                           "importlib.util.module_from_spec",
                           "importlib.util.spec_from_file_location", "json.dumps", "os.walk",
                           "re.compile"}
    _w1403_into_imports = {_c for _c in _w1403_dotted
                           if _c.split(".")[0] in _W1403_IMPORTS_ALLOWED}
    expect("WARP-1403 AC3: THE MODULE REACHES FOR NOTHING OUTSIDE THE REPOSITORY, asserted as FOUR "
           "SET EQUALITIES over its parsed call surface rather than as a grep for the spellings "
           "somebody thought of. Its imports are exactly argparse, hashlib, importlib, json, os, "
           "re, sys and pathlib; the bare-name calls it does not define itself are exactly a "
           "declared list of builtins plus Path and the one glob compiler, so eval, exec, "
           "__import__ and compile are refused by the equality; the calls it makes into those "
           "imported modules are exactly seven named ones, so os.popen, os.system, os.execv and "
           "importlib.import_module are refused the same way; and the fourth shape, CALLING WHAT A "
           "CALL RETURNED, is enumerated instead of waved away, because it is not empty - W2's "
           "bounds rule is fetched and called at sizing_pass.py:532 - so it is pinned to that ONE "
           "producer, a function this module defines, which is what makes getattr(os, 'sys' + "
           "'tem')('id') a red rather than a blind spot. Nothing here spawns a process or opens a "
           "connection (NG5). What this does NOT claim: the paths it READS. Those are the "
           "footprint, whose escape refusal is the assertion above, and its sibling engine "
           "modules, whose target set is the assertion below",
           _w1403_imports == _W1403_IMPORTS_ALLOWED
           and set(_w1403_bare) - _w1403_defs == _W1403_BARE_ALLOWED
           and _w1403_defs & _W1403_BARE_ALLOWED == set()
           and _w1403_into_imports == _W1403_MODULE_CALLS
           and sorted(set(_w1403_computed)) == ["_bounds_rule()"]
           and "_bounds_rule" in _w1403_defs)

    # THE ONE DOOR THE EQUALITIES ABOVE LEAVE OPEN, and it is this module's own idiom: an allowed
    # `spec_from_file_location` can execute ANY file, so pinning the call is worth nothing without
    # pinning what it is aimed at. All three module-executing calls live inside `_mod`, which builds
    # its path as ROOT / rel and nothing else, and every `rel` a caller passes is a string literal,
    # so the module's entire code-execution target set is enumerable and enumerated here.
    _W1403_EXECUTING = ["importlib.util.module_from_spec",
                        "importlib.util.spec_from_file_location", "spec.loader.exec_module"]
    _W1403_MOD_TARGETS = {".veldo/arch.py", ".veldo/estimate.py", ".veldo/events.py",
                          ".veldo/spend.py", ".veldo/toe_corpus.py", ".veldo/validate.py"}
    _w1403_mod_def = [_n for _n in _w1403_ast.walk(_w1403_tree)
                      if isinstance(_n, _w1403_ast.FunctionDef) and _n.name == "_mod"]
    _w1403_exec_all = sorted(_c for _c in _w1403_dotted if _c in _W1403_EXECUTING)
    _w1403_exec_in_mod = sorted(_c for _c in _w1403_call_surface(_w1403_mod_def[0])[1]
                                if _c in _W1403_EXECUTING) if _w1403_mod_def else []
    _w1403_loader_path = [_w1403_ast.dump(_n.args[1]) for _n in _w1403_ast.walk(_w1403_tree)
                          if isinstance(_n, _w1403_ast.Call)
                          and isinstance(_n.func, _w1403_ast.Attribute)
                          and _n.func.attr == "spec_from_file_location" and len(_n.args) > 1]
    _w1403_mod_targets, _w1403_mod_computed = _w1403_literal_args(_w1403_tree, "_mod")
    expect("WARP-1403 AC3 AND THE ONE DOOR THOSE EQUALITIES LEAVE: EVERY FILE THIS MODULE CAN "
           "EXECUTE IS NAMED, and all six are inside this engine. The three importlib calls that "
           "load and run a file occur exactly once each and all three are inside `_mod`; `_mod` "
           "builds the path it executes as ROOT / rel, asserted against that parsed shape and not "
           "against a substring; every caller passes a string literal and never a variable; and "
           "the set of those literals is exactly validate.py, estimate.py, toe_corpus.py, arch.py, "
           "spend.py and events.py, each of which resolves to a real file under the repository "
           "root. Without this an allowlisted spec_from_file_location would satisfy every equality "
           "above while executing any file on the machine: a module's own loader is the reach a "
           "list of forbidden spellings never sees",
           _w1403_exec_all == sorted(_W1403_EXECUTING)
           and _w1403_exec_in_mod == sorted(_W1403_EXECUTING)
           and _w1403_loader_path == [_w1403_ast.dump(
               _w1403_ast.parse("ROOT / rel", mode="eval").body)]
           and _w1403_mod_targets == _W1403_MOD_TARGETS
           and _w1403_mod_computed == 0
           and all((ROOT / _t).is_file()
                   and str((ROOT / _t).resolve()).startswith(str(ROOT.resolve()) + "/")
                   for _t in _w1403_mod_targets))

    # THE UNIT REFUSAL, DRIVEN. The claim is that the brief REFUSES when W2's vocabulary stops
    # naming exactly one unit; observing that it names one today is a fact about estimate.py that
    # is true whether this module checks it or not, which is a label and not a measurement.
    _w1403_saved_units = E1403.UNITS
    try:
        E1403.UNITS = dict(_w1403_saved_units,
                           points="a second unit veldo.estimate/v1 does not declare")
        _w1403_two_units = _w1403_raises(SP1403.brief, _w1403_fix)
    finally:
        E1403.UNITS = _w1403_saved_units
    expect("WARP-1403 AC3: A BRIEF REFUSES RATHER THAN CHOOSING A UNIT FOR AN AGENT, AND THAT IS "
           "DRIVEN. With W2's unit vocabulary made to declare TWO units, brief() refuses and names "
           "the count instead of picking the first; with the vocabulary restored it names the one "
           "declared unit again. A brief that chose on the agent's behalf would get back a range "
           "in a unit nobody agreed on, and the estimate record would combine it with the "
           "structural prior as though the two were the same quantity",
           _w1403_two_units[0] and "declares 2 units" in _w1403_two_units[1]
           and "cannot tell an agent which one to predict in" in _w1403_two_units[1]
           and _w1403_value(SP1403._brief_unit, E1403) == (sorted(E1403.UNITS)[0], "")
           and _W1403_BRIEF["unit"] in E1403.UNITS and len(E1403.UNITS) == 1)

    # -----------------------------------------------------------------------------------
    # AC4. THE LEDGER REPORT AGREES WITH THE LOG IT MEASURED, AND A JUDGEMENT NEVER READS
    # CALIBRATED.
    # -----------------------------------------------------------------------------------
    # WHAT THIS LEG MAY AND MAY NOT ASSERT, because the first version of it got that wrong. It ran
    # over the LIVE log and pinned `spend_events == 0`, which is not a property of this module: it
    # is the observation that nobody had used the emitter yet. MEASURED 2026-08-11: one sanctioned
    # write, `python3 .veldo/spend.py record --spec WARP-0100 --basis harness_reported
    # --tokens 750000`, took the fragment from 42 passed to 41 passed, 1 failed. A gate that reds on
    # the first legitimate use of the feature it guards teaches whoever hits it that the gate is
    # noise, and the person who hits it first is the one who asked for the feature.
    # So the emptiness is a BRANCH, never an assertion. The partition and the key-licensing
    # equalities below hold over ANY log; the arm is chosen by what the recount just found; and the
    # recount is spelled HERE, in its own second spelling of "numeric", so that the two sides of
    # every equality cannot move together when the module is mutated. The teeth are unchanged in
    # the empty state and stronger in the recorded one, where the numeric keys must equal an
    # independent recount instead of merely being absent.
    _w1403_real_events = SP1403._read_events()
    _w1403_real_ledger = SP1403.ledger_state(_w1403_real_events)
    _w1403_spend_fields = SP1403._corpus().SPEND_FIELDS

    def _w1403_isnum(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    _w1403_real_carry = [_e for _e in _w1403_real_events if isinstance(_e, dict)
                         and any(_w1403_isnum(_e.get(_f)) for _f in _w1403_spend_fields)]
    _w1403_real_tok = [_e for _e in _w1403_real_carry if _w1403_isnum(_e.get("tokens"))]
    _w1403_real_specs = len({_e.get("spec_id") or _e.get("correlation_id")
                             for _e in _w1403_real_carry
                             if _e.get("spec_id") or _e.get("correlation_id")})
    if not _w1403_real_carry:
        # THE HONEST STAND-DOWN, and it is required in exactly this state and nowhere else.
        _w1403_real_arm = (_w1403_real_ledger["spend_events"] == 0
                           and _w1403_real_ledger["anchor_available"] == E1403.NO
                           and _w1403_real_ledger["token_anchor_available"] == E1403.NO
                           and "tokens_recorded" not in _w1403_real_ledger
                           and "token_spend_events" not in _w1403_real_ledger
                           and "specs_with_spend" not in _w1403_real_ledger)
    elif _w1403_real_tok:
        # SPEND IS RECORDED AND SOME OF IT IS TOKENS: every numeric key must equal the recount.
        _w1403_real_arm = (_w1403_real_ledger["anchor_available"] == E1403.YES
                           and _w1403_real_ledger["token_anchor_available"] == E1403.YES
                           and _w1403_real_ledger["specs_with_spend"] == _w1403_real_specs
                           and _w1403_real_ledger["token_spend_events"] == len(_w1403_real_tok)
                           and _w1403_real_ledger["tokens_recorded"]
                           == sum(int(_e["tokens"]) for _e in _w1403_real_tok)
                           and 1 <= _w1403_real_ledger["specs_with_spend"]
                           <= _w1403_real_ledger["spend_events"])
    else:
        # SPEND IS RECORDED AND NONE OF IT IS TOKENS: the per-field omission, over the real log.
        _w1403_real_arm = (_w1403_real_ledger["anchor_available"] == E1403.YES
                           and _w1403_real_ledger["token_anchor_available"] == E1403.NO
                           and _w1403_real_ledger["specs_with_spend"] == _w1403_real_specs
                           and "tokens_recorded" not in _w1403_real_ledger
                           and "token_spend_events" not in _w1403_real_ledger)
    expect("WARP-1403 AC4 MEASURED OVER THE REAL LOG, AND THE MEASUREMENT CHOOSES THE ARM: the "
           "ledger report is recomputed here from the live log by a second spelling of the same "
           "definitions, and it must AGREE. Unconditionally: events is one enumeration of the log, "
           "spend_events equals the recount, the spend events are a subset of the events, and each "
           "numeric key is present EXACTLY when the flag licensing it says yes. Then the arm the "
           "recount selects - with nothing recorded, anchor_available no and the numeric keys "
           "ABSENT rather than zero, because a zero because nothing was spent and a zero because "
           "nothing was ever recorded are different facts and an agent handed the second "
           "calibrates against nothing while feeling informed; with spend recorded, the totals "
           "must equal the recount and the token keys are still gated on tokens alone. What this "
           "leg must NEVER assert is that the log carries no spend: that is today's emptiness, not "
           "an invariant, and pinning it made the first sanctioned use of spend.py red the gate",
           _w1403_real_ledger["events"] == len(_w1403_real_events)
           and _w1403_real_ledger["events"] > 900
           and _w1403_real_ledger["spend_events"] == len(_w1403_real_carry)
           and 0 <= _w1403_real_ledger["spend_events"] <= _w1403_real_ledger["events"]
           and len(_w1403_real_tok) <= _w1403_real_ledger["spend_events"]
           and _w1403_real_ledger["anchor_available"]
           == (E1403.YES if _w1403_real_carry else E1403.NO)
           and _w1403_real_ledger["token_anchor_available"]
           == (E1403.YES if _w1403_real_tok else E1403.NO)
           and ("specs_with_spend" in _w1403_real_ledger) == bool(_w1403_real_carry)
           and ("tokens_recorded" in _w1403_real_ledger) == bool(_w1403_real_tok)
           and ("token_spend_events" in _w1403_real_ledger) == bool(_w1403_real_tok)
           and _w1403_real_arm
           and SP1403.brief(_w1403_fix, events=_w1403_real_events)["ledger"]
           == _w1403_real_ledger)

    _w1403_seed = [{"type": "spec.shipped", "spec_id": "WARP-9001", "tokens": 1000},
                   {"type": "spec.shipped", "spec_id": "WARP-9002", "tokens": 2500,
                    "human_minutes": 4},
                   {"type": "gate.passed", "spec_id": "WARP-9003"}]
    _w1403_seeded_ledger = SP1403.ledger_state(_w1403_seed)
    expect("WARP-1403 AC4 THE CONTROL THAT MAKES THAT A MEASUREMENT: over a SEEDED ledger the same "
           "function reports anchor_available yes, the recorded token total and the number of "
           "specs it came from, all present and correct. So the standdown above is the ledger "
           "being empty and not a hardcoded no - without this control that assertion would pass "
           "on a function that could never say anything else",
           _w1403_seeded_ledger["anchor_available"] == E1403.YES
           and _w1403_seeded_ledger["token_anchor_available"] == E1403.YES
           and _w1403_seeded_ledger["spend_events"] == 2
           and _w1403_seeded_ledger["tokens_recorded"] == 3500
           and _w1403_seeded_ledger["token_spend_events"] == 2
           and _w1403_seeded_ledger["specs_with_spend"] == 2
           and _w1403_seeded_ledger["events"] == 3)

    # THE THIRD CONTROL, over the part of the domain the pair above never reached: spend recorded
    # in a field that is NOT tokens. spend.validate requires only ONE of the three declared spend
    # fields and its writer defaults tokens to None, so this record shape is ordinary rather than
    # hypothetical, and it is the one where "carrying spend" and "carrying tokens" stop coinciding.
    _w1403_no_tok = [{"type": "spec.shipped", "spec_id": "WARP-9101", "cost_usd": 12.5,
                      "human_minutes": 30},
                     {"type": "spec.shipped", "spec_id": "WARP-9102", "human_minutes": 45},
                     {"type": "gate.passed", "spec_id": "WARP-9103"}]
    _w1403_no_tok_ledger = SP1403.ledger_state(_w1403_no_tok)
    expect("WARP-1403 AC4 THE OMISSION IS PER FIELD AND NOT PER LEDGER: over a ledger whose spend "
           "events carry cost_usd and human_minutes but NO tokens, the token keys are ABSENT and "
           "token_anchor_available reads no, while anchor_available still reads yes and "
           "spend_events counts both records. Gating the token total on 'some spend field is "
           "present' would hand an agent tokens_recorded: 0 next to anchor_available: yes - a zero "
           "because tokens were never recorded, dressed as a measurement, which is the exact "
           "defect AC4 exists to prevent and which the empty-log half of this pair cannot see "
           "because there the two definitions coincide",
           _w1403_no_tok_ledger["anchor_available"] == E1403.YES
           and _w1403_no_tok_ledger["token_anchor_available"] == E1403.NO
           and "tokens_recorded" not in _w1403_no_tok_ledger
           and "token_spend_events" not in _w1403_no_tok_ledger
           and _w1403_no_tok_ledger["spend_events"] == 2
           and _w1403_no_tok_ledger["specs_with_spend"] == 2
           and _w1403_no_tok_ledger["events"] == 3
           and SP1403.brief(_w1403_fix, events=_w1403_no_tok)["ledger"]
           == _w1403_no_tok_ledger)

    # THE FOURTH CONTROL, and the only fixture in which `token_spend_events` MEANS anything. Its
    # declared job is to be the BASIS of the token total, but in the three ledgers above the token
    # events and the spend events are the SAME events - both seeded records carry tokens, and in the
    # no-tokens ledger the key is absent - so `len(with_tokens)` and `len(carrying)` are the same
    # number and the key could be summed over the wrong set with every assertion green. Measured:
    # `out["token_spend_events"] = len(carrying)` left the suite at 40 passed. A MIXED ledger, one
    # record with tokens beside two whose spend was recorded as cost and as human minutes, is the
    # only shape where the basis and the any-field count DIVERGE, and it is the shape the sanctioned
    # writer produces, since spend.record defaults tokens to None per record and not per ledger.
    _w1403_mixed = [{"type": "spec.shipped", "spec_id": "WARP-9201", "tokens": 1200},
                    {"type": "spec.shipped", "spec_id": "WARP-9202", "cost_usd": 3.75},
                    {"type": "spec.shipped", "spec_id": "WARP-9203", "human_minutes": 20},
                    {"type": "gate.passed", "spec_id": "WARP-9204"}]
    _w1403_mixed_ledger = SP1403.ledger_state(_w1403_mixed)
    expect("WARP-1403 AC4 THE TOKEN TOTAL IS SUMMED OVER THE EVENTS ITS BASIS NAMES: over a ledger "
           "carrying one tokens record and two whose spend is cost_usd and human_minutes, "
           "token_spend_events reads 1 while spend_events reads 3, and tokens_recorded is the 1200 "
           "of that one record. The two counts DIVERGE here and nowhere else in this file, which "
           "is what makes token_spend_events a measured basis and not a second name for "
           "spend_events: a total reported over 3 events when 1 was measured is a number with a "
           "denominator nobody can check, and the three ledgers above cannot see it because there "
           "the token events and the spend events are the same events",
           _w1403_mixed_ledger["token_spend_events"] == 1
           and _w1403_mixed_ledger["spend_events"] == 3
           and _w1403_mixed_ledger["token_spend_events"]
           != _w1403_mixed_ledger["spend_events"]
           and _w1403_mixed_ledger["tokens_recorded"] == 1200
           and _w1403_mixed_ledger["token_anchor_available"] == E1403.YES
           and _w1403_mixed_ledger["anchor_available"] == E1403.YES
           and _w1403_mixed_ledger["specs_with_spend"] == 3
           and _w1403_mixed_ledger["events"] == 4
           and SP1403.brief(_w1403_fix, events=_w1403_mixed)["ledger"]
           == _w1403_mixed_ledger)

    expect("WARP-1403 AC4: AN AGENT'S JUDGEMENT NEVER MAKES AN ESTIMATE CALIBRATED. The record "
           "carrying this layer reads calibration uncalibrated and validates clean, because "
           "agent_judgement is deliberately NOT one of W2's bases grounded in recorded actuals. A "
           "reasoned guess arriving dressed as a measurement is the one thing this layer must "
           "never do on the way to a budget or a dollar figure",
           _W1403_REC.get("calibration") == "uncalibrated"
           and SP1403.LAYER_BASIS not in E1403.CALIBRATED_BASES
           and E1403.calibration_of(_W1403_REC.get("layers") or []) == "uncalibrated")

    _w1403_saved_cal = E1403.CALIBRATED_BASES
    try:
        E1403.CALIBRATED_BASES = tuple(_w1403_saved_cal) + (SP1403.LAYER_BASIS,)
        _w1403_cal_refusal = _w1403_raises(SP1403.layer_from, _W1403_J, _W1403_BRIEF)
    finally:
        E1403.CALIBRATED_BASES = _w1403_saved_cal
    expect("WARP-1403 AC4 AND ITS TEETH, DRIVEN: with agent_judgement moved INTO the calibrated "
           "set, layer_from refuses to write the layer at all and names the reason, and the "
           "vocabulary check goes back to passing the moment it is restored. The check is not a "
           "comment about a promise, it is a live refusal that fires when the promise breaks",
           _w1403_cal_refusal[0]
           and "grounded in recorded actuals" in _w1403_cal_refusal[1]
           and _w1403_value(SP1403.layer_vocabulary)
           == ((SP1403.LAYER_ID, SP1403.LAYER_BASIS), ""))

    # THE OTHER TWO OF THE THREE DECLARED REFUSALS, driven the same way the calibrated one above
    # already is. layer_vocabulary says it "fails closed by name on three things"; before this the
    # third was driven and the first two were only described, so deleting either check left every
    # assertion in this fragment green.
    _w1403_saved_layers = E1403.LAYERS
    try:
        E1403.LAYERS = {k: v for k, v in _w1403_saved_layers.items() if k != SP1403.LAYER_ID}
        _w1403_no_layer = _w1403_raises(SP1403.layer_vocabulary)
    finally:
        E1403.LAYERS = _w1403_saved_layers
    _w1403_saved_bases = E1403.BASES
    try:
        E1403.BASES = {k: v for k, v in _w1403_saved_bases.items() if k != SP1403.LAYER_BASIS}
        _w1403_no_basis = _w1403_raises(SP1403.layer_vocabulary)
    finally:
        E1403.BASES = _w1403_saved_bases
    expect("WARP-1403 AC4: ALL THREE OF THE VOCABULARY REFUSALS ARE DRIVEN, not one of three. With "
           "this layer id removed from W2's LAYERS the module refuses and NAMES the id; with this "
           "basis removed from W2's BASES it refuses and names the basis; each goes back to "
           "returning the pair the moment the vocabulary is restored. The sizing pass EXTENDS that "
           "vocabulary and never widens it, so a typo in a layer id, or a basis W2 stopped "
           "declaring, must be a refusal rather than a contribution nothing downstream recognises",
           _w1403_no_layer[0] and "is not one of the layers" in _w1403_no_layer[1]
           and SP1403.LAYER_ID in _w1403_no_layer[1]
           and _w1403_no_basis[0] and "is not one of the bases" in _w1403_no_basis[1]
           and SP1403.LAYER_BASIS in _w1403_no_basis[1]
           and _w1403_value(SP1403.layer_vocabulary)
           == ((SP1403.LAYER_ID, SP1403.LAYER_BASIS), ""))

    _w1403_emitted = []
    _w1403_ev, _w1403_ev_err = _w1403_value(
        SP1403.record_self_cost, _W1403_J,
        emit=lambda t, **kw: (_w1403_emitted.append((t, kw)) or {"type": t}))
    expect("WARP-1403 AC4: THE PASS'S OWN COST IS RECORDED LIKE ANY OTHER WORK, through the spend "
           "recorder's ONE writer, against the spec it sized, carrying the tokens, the stated "
           "provenance and the brief it was made from. That is what puts the estimating "
           "apparatus's cost INSIDE the measured cost of the change it sized, where C4's "
           "proportionality claim can be checked instead of asserted - and today it would be the "
           "first spend record this repository has ever written",
           _w1403_ev_err == "" and len(_w1403_emitted) == 1
           and _w1403_emitted[0][0] == SPEND1403.SCHEMA_EVENT_TYPE
           and _w1403_emitted[0][1]["tokens"] == _W1403_J["self_cost_tokens"]
           and _w1403_emitted[0][1]["spec"] == _W1403_J["spec"]
           and _w1403_emitted[0][1]["extra"]["spend_basis"] == _W1403_J["self_cost_basis"]
           and _W1403_J["brief_digest"][:12] in _w1403_emitted[0][1]["extra"]["spend_note"])

    _w1403_pricey, _w1403_pricey_err = _w1403_layer(
        _w1403_judgement(_W1403_BRIEF, self_cost_tokens=200000), _W1403_BRIEF)
    _w1403_pricey_rec = _w1403_raises(E1403.build_record, "WARP-9403", _W1403_AT,
                                      [_w1403_pricey])
    _w1403_cheap_in = (SP1403.layer_of(_W1403_REC) or {}).get("inputs") or {}
    expect("WARP-1403 AC4: THE COST SHARE IS ON RECORD AND CROSSING THE CEILING IS REPORTED, "
           "NEVER REFUSED. A pass costing half its own lower bound still produces a valid layer, "
           "flagged outside the ceiling, while the ordinary one is flagged inside it. Refusing to "
           "record an expensive pass would delete the only evidence that the estimating apparatus "
           "costs more than the work it sizes, which is the fact C4 exists to catch",
           _w1403_cheap_in.get("self_cost_within_ceiling") == E1403.YES
           and _w1403_cheap_in.get("self_cost_bps_of_low") == 9000 * 10000 // _W1403_J["low"]
           and _w1403_pricey_err == ""
           and (_w1403_pricey.get("inputs") or {}).get("self_cost_within_ceiling") == E1403.NO
           and (_w1403_pricey.get("inputs") or {}).get("self_cost_bps_of_low", 0)
           > SP1403.SELF_COST_CEILING_BPS
           and _w1403_pricey_rec[0] is False)

    _w1403_inside, _w1403_inside_err = _w1403_size(
        _w1403_fix, _W1403_AT, agent=_W1403Agent(_w1403_judgement(
            _W1403_BRIEF, low=_W1403_BRIEF["prior"]["low"] + 1000,
            high=_W1403_BRIEF["prior"]["high"] - 1000)))
    expect("WARP-1403 AC4: THE LAYER WIDENS THE COMMITTED RANGE OR LEAVES IT ALONE, NEVER "
           "NARROWS IT. A judgement reaching higher than the prior raises the committed high while "
           "the low stays the prior's, and a judgement wholly INSIDE the prior changes the "
           "committed range not at all. That is the envelope doing its job: two layers that "
           "disagree are evidence of uncertainty, and tightening the band on disagreement would "
           "manufacture confidence (NG6)",
           _W1403_REC.get("high") == _W1403_J["high"]
           and _W1403_REC.get("low") == _W1403_BRIEF["prior"]["low"]
           and _w1403_inside_err == ""
           and (_w1403_inside["record"].get("low"), _w1403_inside["record"].get("high"))
           == (_W1403_BRIEF["prior"]["low"], _W1403_BRIEF["prior"]["high"])
           and SP1403.layer_of(_w1403_inside["record"]) is not None)

    _w1403_moved = json.loads(json.dumps(_W1403_BRIEF))
    _w1403_moved["prior"]["low"] += 1
    _w1403_prior_refusal = _w1403_raises(SP1403.assert_prior_agrees, _W1403_REC, _w1403_moved)
    expect("WARP-1403 AC4: ONE ENUMERATION OF THE PRIOR, ASSERTED AND NOT ASSUMED. The brief "
           "shows the agent a structural prior and the committed record derives that layer again; "
           "with the two disagreeing by ONE token the pass refuses and names both pairs, and it "
           "agrees on the real record. Two derivations of one number diverge the moment anything "
           "between them differs, so committing a record whose prior is not the prior the "
           "judgement was made against is exactly the failure this closes",
           _w1403_prior_refusal[0]
           and "is a judgement about a different question" in _w1403_prior_refusal[1]
           and _w1403_raises(SP1403.assert_prior_agrees, _W1403_REC, _W1403_BRIEF)[0] is False)

    # -----------------------------------------------------------------------------------
    # AC5. OPTIONAL, ADOPTION SAFE, NEVER A BLOCKER. The load-bearing pair of this item.
    # -----------------------------------------------------------------------------------
    _w1403_absent_dir = _w1403_dir / "no_such_sizings_dir"
    expect("WARP-1403 AC5: WITH NO JUDGEMENTS PRESENT EVERY READER STANDS DOWN SILENTLY AND "
           "CREATES NOTHING. load_dir gives an empty set with no problems, judgement_for gives "
           "None, check_dir reports nothing checked, layer_of a structural-only record gives "
           "None, and the directory is STILL absent afterwards. A repository that never uses this "
           "is byte-identically unaffected, which is the only posture under which an optional "
           "second estimating layer is safe to add to a working gate",
           SP1403.load_dir(_w1403_absent_dir) == ({}, [])
           and SP1403.judgement_for("WARP-9403", dirpath=_w1403_absent_dir) is None
           and SP1403.check_dir(_w1403_absent_dir) == (0, 0)
           and SP1403.layer_of(E1403.propose(_w1403_fix, _W1403_AT)) is None
           and not _w1403_absent_dir.exists())

    _w1403_cli = subprocess.run(
        [sys.executable, str(ROOT / ".veldo/sizing_pass.py"), "check",
         "--dir", str(_w1403_absent_dir)], capture_output=True, text=True, cwd=str(ROOT))
    _w1403_cli_vocab = subprocess.run(
        [sys.executable, str(ROOT / ".veldo/sizing_pass.py"), "vocab"],
        capture_output=True, text=True, cwd=str(ROOT))
    expect("WARP-1403 AC5: THE CLI'S check EXITS 0 AND SAYS IT IS STANDING DOWN when nothing is "
           "committed, driven as a real process, and vocab prints the layer, the basis and the "
           "cost vocabulary. A tool that exited non-zero on the absence of an optional record "
           "would turn an advisory layer into a gate the first time somebody wired it into a "
           "script, which is precisely NG1",
           _w1403_cli.returncode == 0 and "standing down" in _w1403_cli.stdout
           and "not a finding" in _w1403_cli.stdout
           and _w1403_cli_vocab.returncode == 0
           and SP1403.LAYER_BASIS in _w1403_cli_vocab.stdout
           and "never enforced" in _w1403_cli_vocab.stdout)

    _w1403_mix = _w1403_dir / "sizings"
    _w1403_mix.mkdir()
    (_w1403_mix / "WARP-9403.yaml").write_text(_w1403_jf.read_text())
    (_w1403_mix / "WARP-9499.yaml").write_text(
        "schema: %s\nspec: WARP-9499\nlow: 5\nhigh: 5\n" % SP1403.SCHEMA)
    _w1403_loaded, _w1403_loadprobs = SP1403.load_dir(_w1403_mix)
    _w1403_mixcli = subprocess.run(
        [sys.executable, str(ROOT / ".veldo/sizing_pass.py"), "check", "--dir", str(_w1403_mix)],
        capture_output=True, text=True, cwd=str(ROOT))
    expect("WARP-1403 AC5 FAIL CLOSED ON A PRESENT-BUT-BROKEN JUDGEMENT: load_dir returns the one "
           "valid record and reports the broken one by path, rather than quietly returning a "
           "smaller set, and the CLI report - driven as a real process over the same directory - "
           "counts BOTH files, exits non-zero and names the broken one through the ONE failure "
           "reporter. Absence stands down; breakage speaks up. Those are different facts and a "
           "reader that cannot tell them apart is the defect W1's coverage report exists to avoid",
           sorted(_w1403_loaded) == ["WARP-9403"]
           and len(_w1403_loadprobs) == 1 and "WARP-9499" in _w1403_loadprobs[0]
           and _w1403_mixcli.returncode == 1
           and "2 record(s) checked" in _w1403_mixcli.stdout
           and "WARP-9499" in (_w1403_mixcli.stdout + _w1403_mixcli.stderr)
           and (_w1403_value(SP1403.judgement_for, "WARP-9403",
                             dirpath=_w1403_mix)[0] or {}).get("spec") == "WARP-9403")

    (_w1403_mix / "WARP-9403.yaml").write_text(
        _w1403_jf.read_text().replace("spec: WARP-9403", "spec: WARP-9404"))
    _w1403_misfiled = _w1403_raises(SP1403.read_judgement, _w1403_mix / "WARP-9403.yaml")
    (_w1403_mix / "WARP-9403.yaml").write_text(_w1403_jf.read_text())
    expect("WARP-1403 AC5: A JUDGEMENT FILED UNDER THE WRONG NAME IS REFUSED, naming both the "
           "filename it is filed as and the spec it claims. The filename is the key, which is "
           "what makes two judgements for one spec impossible, so the two are checked against "
           "each other rather than one being trusted",
           _w1403_misfiled[0] and "the filename is the key" in _w1403_misfiled[1]
           and (_w1403_value(SP1403.read_judgement,
                             _w1403_mix / "WARP-9403.yaml")[0] or {}).get("spec")
           == "WARP-9403")

    # A hermetic repository root: the real contract and policy, a fixture spec, and the two
    # optional record directories under our control. check_spec accepts repo_root, so the REAL
    # validator runs over it.
    _w1403_root = _w1403_dir / "repo"
    (_w1403_root / ".veldo").mkdir(parents=True)
    (_w1403_root / "specs").mkdir()
    for _rel in (".veldo/architecture.yaml", ".veldo/policy.yaml"):
        _w1403_shutil.copy(ROOT / _rel, _w1403_root / _rel)
    _w1403_rspec = _w1403_root / "specs" / "WARP-9403-fixture.md"
    _w1403_rspec.write_text(_w1403_spec_text())
    _w1403_estdir = _w1403_root / ".veldo" / "estimates"
    _w1403_sizdir = _w1403_root / ".veldo" / "sizings"

    _w1403_none = V.check_spec(_w1403_rspec, repo_root=_w1403_root)
    E1403.write_record(E1403.propose(_w1403_rspec, _W1403_AT), dirpath=_w1403_estdir)
    _w1403_proxy_only = V.check_spec(_w1403_rspec, repo_root=_w1403_root)
    _w1403_hbrief = SP1403.brief(_w1403_rspec, root=_w1403_root)
    _w1403_hj = _w1403_judgement(_w1403_hbrief)
    _w1403_hout, _w1403_herr = _w1403_size(_w1403_rspec, _W1403_AT,
                                           agent=_W1403Agent(_w1403_hj), root=_w1403_root)
    if not _w1403_herr:
        E1403.write_record(_w1403_hout["record"], dirpath=_w1403_estdir, replace=True)
    _w1403_sized = V.check_spec(_w1403_rspec, repo_root=_w1403_root)
    _w1403_sizdir.mkdir(parents=True)
    (_w1403_sizdir / "WARP-9403.yaml").write_text(
        "schema: %s\nspec: WARP-9403\nlow: 7\nhigh: 7\n" % SP1403.SCHEMA)
    _w1403_broken = V.check_spec(_w1403_rspec, repo_root=_w1403_root)
    _w1403_broken_probs = _w1403_probs(SP1403.parse_judgement(
        (_w1403_sizdir / "WARP-9403.yaml").read_text()))
    _w1403_bad_spec = _w1403_root / "specs" / "WARP-9404-broken.md"
    _w1403_bad_spec.write_text(
        _w1403_spec_text(spec_id="WARP-9404").replace("status: ready", "status: donezo"))
    _w1403_bad_errs = V.check_spec(_w1403_bad_spec, repo_root=_w1403_root)

    expect("WARP-1403 AC5, THE LOAD-BEARING ONE: A SIZING PASS CAN NEVER INVALIDATE A SPEC, "
           "measured by DRIVING the real validate.check_spec over a hermetic repository root FOUR "
           "times - with no estimate at all, with a structural-only estimate, with an estimate "
           "carrying a real sizing_pass layer, and with a MALFORMED judgement file committed "
           "beside it - and getting the identical 0 every time, while validate_judgement names "
           "that malformed record's defects. This is PLAN-0014 C3 and NG1 as a measurement: the "
           "layer lives BESIDE the spec, so its absence AND its breakage are invisible to the "
           "thing that decides whether a spec is valid",
           (_w1403_none, _w1403_proxy_only, _w1403_sized, _w1403_broken) == (0, 0, 0, 0)
           and "is a POINT" in _w1403_broken_probs
           and "missing required key 'brief_digest'" in _w1403_broken_probs
           and _w1403_herr == "" and SP1403.layer_of(_w1403_hout["record"]) is not None)

    expect("WARP-1403 AC5 NEGATIVE CONTROL FOR THAT PASS: the SAME validator over the SAME "
           "hermetic root DOES refuse a genuinely broken spec, so the four zeros above are the "
           "sizing pass being irrelevant and not check_spec being blind under this fixture. "
           "Without this control the whole assertion would be a pass earned by looking nowhere",
           _w1403_bad_errs > 0)

    _w1403_gate_text = (ROOT / "scripts/verify.sh").read_text()
    _w1403_slots = _w1403_re.findall(r"CHECK_\w+=\"[^\"]*\"", _w1403_gate_text)
    # THE SWEEP'S DOMAIN IS EVERY TREE THIS CLAIM IS ABOUT, not the one directory this repository
    # happens to run from: the private engine, the CANONICAL engine an adopter is handed, and
    # scripts/, which is where a gate stage would actually live. A probe naming this module from
    # engine/.veldo or from scripts/ used to leave the sweep green.
    #
    # THE SPELLINGS ARE PATH-SHAPED AND IMPORT-SHAPED, deliberately, because the bare stem
    # `sizing_pass` is ALSO the LAYER ID that W2's vocabulary declares (estimate.py names it, in
    # both engine homes, and must): a bare-stem sweep would red on W2 declaring its own layer and
    # would then be relaxed until it measured nothing.
    _W1403_NAME_SPELLINGS = ("sizing_pass.py", "import sizing_pass", "from sizing_pass",
                             'sizing_pass")')
    _W1403_LOAD_SPELLINGS = ("import sizing_pass", "from sizing_pass", 'sizing_pass")')
    # A release DISPOSITION list may NAME this file's path - shipping it or holding it back is a
    # decision about the module, not a use of it. Nothing anywhere may IMPORT or EXECUTE it.
    _W1403_MAY_NAME = ("scripts/publish.py",)
    _W1403_SWEEP = {
        ".veldo/*.py": sorted((ROOT / ".veldo").glob("*.py")),
        "engine/.veldo/*.py": sorted((ROOT / "engine/.veldo").glob("*.py")),
        "scripts/*.py": sorted((ROOT / "scripts").glob("*.py")),
        "scripts/*.sh": sorted((ROOT / "scripts").glob("*.sh")),
    }
    _W1403_SELVES = (".veldo/sizing_pass.py", "engine/.veldo/sizing_pass.py")
    _w1403_domain, _w1403_namers, _w1403_loaders = set(), [], []
    for _w1403_paths in _W1403_SWEEP.values():
        for _w1403_p in _w1403_paths:
            _w1403_rel = str(_w1403_p.relative_to(ROOT))
            _w1403_domain.add(_w1403_rel)
            if _w1403_rel in _W1403_SELVES:
                continue
            _w1403_txt = _w1403_p.read_text()
            if any(_s in _w1403_txt for _s in _W1403_NAME_SPELLINGS):
                _w1403_namers.append(_w1403_rel)
            if any(_s in _w1403_txt for _s in _W1403_LOAD_SPELLINGS):
                _w1403_loaders.append(_w1403_rel)
    expect("WARP-1403 AC5: NOTHING IN THE GATE NAMES THIS MODULE AND NOTHING ANYWHERE LOADS IT, "
           "swept over FOUR domains rather than one: scripts/verify.sh declares no slot mentioning "
           "it, the contract validator it runs does not name it, and across .veldo/*.py, "
           "engine/.veldo/*.py, scripts/*.py and scripts/*.sh no file names its path and none "
           "imports or executes it, except that a release disposition list is allowed to name the "
           "path it holds back or ships. So no path through the gate and no organ of the loop can "
           "refuse, block or delay work over a sizing pass. Bound to a non-empty slot list and to "
           "four non-empty domains that provably contain both engine homes and the gate script, so "
           "a glob that matched nothing reds this rather than passing over nothing",
           _w1403_slots != [] and all("sizing" not in s for s in _w1403_slots)
           and "sizing_pass" not in _w1403_gate_text
           and "sizing_pass" not in (ROOT / ".veldo/validate.py").read_text()
           and all(len(_v) > 0 for _v in _W1403_SWEEP.values())
           and {".veldo/estimate.py", "engine/.veldo/estimate.py", "engine/.veldo/sizing_pass.py",
                "scripts/verify.sh", "scripts/publish.py"} <= _w1403_domain
           and sorted(set(_w1403_namers) - set(_W1403_MAY_NAME)) == []
           and _w1403_loaders == [])

    _w1403_example = ROOT / ".veldo/examples/sizing-judgement-example.yaml"
    _w1403_example_rec = SP1403.parse_judgement(_w1403_example.read_text())
    expect("WARP-1403 AC5: THE MODULE AND ITS EXAMPLE ARE BYTE-IDENTICAL IN BOTH ENGINE HOMES, so "
           "what an adopter is handed is the code this repository runs and proves, and the "
           "committed example judgement is checked as REAL BYTES on disk rather than as a fixture "
           "built in this file - a documented shape that can drift from the shape the validator "
           "accepts teaches the wrong thing to every adopter",
           (ROOT / ".veldo/sizing_pass.py").read_bytes()
           == (ROOT / "engine/.veldo/sizing_pass.py").read_bytes()
           and _w1403_example.read_bytes()
           == (ROOT / "engine/.veldo/examples/sizing-judgement-example.yaml").read_bytes()
           and SP1403.validate_judgement(_w1403_example_rec) == []
           and (_w1403_layer(_w1403_example_rec)[0] or {}).get("basis") == SP1403.LAYER_BASIS)

    expect("WARP-1403 AC5 AND THE EXAMPLE'S OWN HONESTY: the example's digest is the sha256 of a "
           "stated ASCII string and of NO brief in this repository, so checked against a real "
           "brief the example is REFUSED - which is the binding working rather than a flaw in the "
           "example. Asserted here so the example can never quietly become a judgement that "
           "passes a binding it was never made against",
           "does not match the brief actually read" in _w1403_probs(
               dict(_w1403_example_rec, spec=_W1403_BRIEF["spec"]), _W1403_BRIEF)
           and _w1403_example_rec["brief_digest"] == _w1403_hashlib.sha256(
               b"example").hexdigest())

del _w1403_ast, _w1403_hashlib, _w1403_re, _w1403_shutil
