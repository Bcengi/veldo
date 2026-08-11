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
"""
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

    expect("WARP-1403 AC3: THE MODULE REACHES FOR NOTHING OUTSIDE THE REPOSITORY. Its source "
           "names no subprocess, socket or urllib import and no Popen, so nothing written here "
           "spawns a process or opens a connection (NG5) - the event log is reached through the "
           "event module's ONE reader, which reads that file and nothing else - and it takes the "
           "estimate's unit from W2's "
           "declared vocabulary rather than spelling one - refusing outright if that vocabulary "
           "ever stops naming exactly one, because a brief cannot choose a unit for an agent",
           all(tok not in (ROOT / ".veldo/sizing_pass.py").read_text()
               for tok in ("import subprocess", "import socket", "import urllib", "Popen("))
           and _W1403_BRIEF["unit"] in E1403.UNITS and len(E1403.UNITS) == 1)

    # -----------------------------------------------------------------------------------
    # AC4. THE EMPTY LEDGER IS REPORTED EMPTY, AND A JUDGEMENT NEVER READS CALIBRATED.
    # -----------------------------------------------------------------------------------
    _w1403_real_events = SP1403._read_events()
    _w1403_real_ledger = SP1403.ledger_state(_w1403_real_events)
    expect("WARP-1403 AC4 MEASURED OVER THE REAL LOG: this repository's ledger carries events in "
           "the thousand and NOT ONE with a spend field, so anchor_available reads no and the "
           "numeric anchor keys are ABSENT rather than zero. That omission is the assertion: a "
           "zero because nothing was spent and a zero because nothing was ever recorded are "
           "different facts, and an agent handed the second as a measurement calibrates against "
           "nothing while feeling informed. Bound to the log's own length, not a literal count; "
           "when real spend is first recorded this reds and the finding gets updated, which is "
           "what a measured claim is supposed to do",
           _w1403_real_ledger["events"] == len(_w1403_real_events)
           and _w1403_real_ledger["events"] > 900
           and _w1403_real_ledger["spend_events"] == 0
           and _w1403_real_ledger["anchor_available"] == E1403.NO
           and "tokens_recorded" not in _w1403_real_ledger
           and "specs_with_spend" not in _w1403_real_ledger)

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
           and _w1403_seeded_ledger["spend_events"] == 2
           and _w1403_seeded_ledger["tokens_recorded"] == 3500
           and _w1403_seeded_ledger["specs_with_spend"] == 2
           and _w1403_seeded_ledger["events"] == 3)

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
    expect("WARP-1403 AC5: NOTHING IN THE GATE NAMES THIS MODULE. scripts/verify.sh declares no "
           "slot mentioning sizing_pass.py, neither does the contract validator it runs, and no "
           "engine module reads it either - so no path through the gate and no organ of the loop "
           "can refuse, block or delay work over a sizing pass. Bound to a non-empty slot list, "
           "so a parse that found no slots reds this rather than passing over nothing",
           _w1403_slots != [] and all("sizing" not in s for s in _w1403_slots)
           and "sizing_pass" not in _w1403_gate_text
           and "sizing_pass" not in (ROOT / ".veldo/validate.py").read_text()
           and [_p.name for _p in sorted((ROOT / ".veldo").glob("*.py"))
                if "sizing_pass.py" in _p.read_text() and _p.name != "sizing_pass.py"] == [])

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

del _w1403_hashlib, _w1403_re, _w1403_shutil
