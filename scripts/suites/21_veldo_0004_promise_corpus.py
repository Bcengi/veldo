"""VELDO-0004: the promise corpus - a claim a document makes, settled against the tree.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, which always
runs, so its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 21_veldo_0004_promise_corpus

WHAT IS UNDER TEST. .veldo/promises.py, driven directly and handed validate.py's ONE front-matter
parser and ONE failure reporter, exactly as validate.py hands them to every other organ.

EVERY FIXTURE IS A REAL TREE. The module's whole job is to read a tree and say what it found, so a
fixture built from in-memory dicts would test the wrong thing: every row writes documents and
corpora as FILES and settles against them.

EVERY CRITERION'S BLOCK IS WRAPPED. A raise at fragment scope takes every row below it with it,
which is how a mutation that DELETES coverage passes as a shorter run instead of a red one.

BOTH DIRECTIONS, EVERYWHERE. This item's product is an ACCUSATION against shipped prose, and the
audit that motivated it had five of fifteen accusations overturned. So every refusal is paired with
an accepting fixture differing in exactly one field, and every settlement is asserted in both
directions - a predicate that only ever accuses is as useless as one that never does.
"""
PM = V._VC._organ("promises", ROOT / ".veldo" / "promises.py")


def _pm_block(label, fn):
    """Red a NAMED row when a criterion's block raises, instead of losing every row below it."""
    try:
        fn()
    except Exception as _pm_e:                   # noqa: BLE001 - a raise must RED a row, never skip
        expect("VELDO-0004 %s: the block ran to completion rather than raising (%r)"
               % (label, _pm_e), False)


def _pm_claim(cid="CLAIM-0001", locator="line 12", text="the document claims a thing",
              predicate="text_present", target="docs/doc.md", drop=(), **extra):
    """One claim whose ONLY defect can be the thing a row is about."""
    c = {"id": cid, "locator": locator, "text": text, "predicate": predicate, "target": target}
    if predicate in ("text_present", "text_absent"):
        c["needle"] = "a thing that is here"
    if predicate == "symbol_defined":
        c["symbol"] = "a_symbol"
    for k in drop:
        c.pop(k, None)
    c.update(extra)
    return c


def _pm_emit(claims, cid="PROMISES-doc", schema=PM.SCHEMA, document="docs/doc.md", drop=(),
             **extra):
    head = {"schema": schema, "id": cid, "version": 1, "document": document}
    for k in drop:
        head.pop(k, None)
    head.update(extra)
    lines = ["%s: %s" % (k, head[k]) for k in head]
    lines.append("claims:")
    for c in claims:
        first = True
        for k in c:
            lead = "  - " if first else "    "
            first = False
            lines.append("%s%s: %s" % (lead, k, c[k]))
    return "\n".join(lines) + "\n"


def _pm_tree(d, corpora=(), docs=(("docs/doc.md", "a thing that is here"),)):
    base = Path(d)
    pdir = base / ".veldo" / "promises"
    pdir.mkdir(parents=True, exist_ok=True)
    for rel, text in docs:
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    for name, text in corpora:
        (pdir / name).write_text(text)
    return base, pdir


def _pm_check(corpora, docs=(("docs/doc.md", "a thing that is here"),)):
    import contextlib as _pm_ctx
    import io as _pm_io
    with tempfile.TemporaryDirectory() as d:
        base, pdir = _pm_tree(d, corpora, docs)
        buf = _pm_io.StringIO()
        with _pm_ctx.redirect_stdout(buf):
            n = PM.check_promises_dir(pdir, base, V.parse_yamlish, V.fail)
        return n, buf.getvalue()


def _pm_report(corpora, docs=(("docs/doc.md", "a thing that is here"),)):
    with tempfile.TemporaryDirectory() as d:
        base, pdir = _pm_tree(d, corpora, docs)
        rep = PM.promise_report(pdir=pdir, root=base, parse=V.parse_yamlish)
        return rep, PM.report_lines(rep)


# ---------------------------------------------------------------------------------------
# AC1. A CLAIM IS A CLOSED CONTRACT WITH A DECLARED PREDICATE.
#
# FALSIFIED BY: widen PREDICATES to accept any string, and the predicate row must go red.
# ---------------------------------------------------------------------------------------


def _pm_ac1():
    n_ok, _ = _pm_check([("a.yaml", _pm_emit([_pm_claim()]))])
    expect("VELDO-0004 AC1 NEGATIVE CONTROL FIRST: a well-formed corpus is ACCEPTED with zero "
           "errors, so every refusal below discriminates rather than being a validator that "
           "refuses every corpus it is shown",
           n_ok == 0)

    n, out = _pm_check([("a.yaml", _pm_emit([_pm_claim(predicate="looks_fine")]))])
    expect("VELDO-0004 AC1: a claim declaring predicate `looks_fine` is refused with "
           "PROMISE_PREDICATE_UNKNOWN and the allowed predicates named. The vocabulary is tiny on "
           "purpose: a predicate that needed judgement would be a machine making a review-lane "
           "call, which is the confident wrongness this whole item exists to avoid",
           n > 0 and PM.CAUSE_PREDICATE_UNKNOWN in out and "text_present" in out
           and "unsettleable" in out)

    for field in PM.CLAIM_REQUIRED:
        n_f, out_f = _pm_check([("a.yaml", _pm_emit([_pm_claim(drop=(field,))]))])
        expect("VELDO-0004 AC1: a claim declaring no %s is refused with PROMISE_MISSING_FIELD "
               "naming the field" % field,
               n_f > 0 and PM.CAUSE_MISSING_FIELD in out_f and field in out_f)

    n_n, out_n = _pm_check([("a.yaml", _pm_emit([_pm_claim(predicate="text_present",
                                                           drop=("needle",))]))])
    expect("VELDO-0004 AC1: a claim whose predicate needs a needle and has none is refused AT READ "
           "TIME rather than settling as unsettleable. That distinction matters: an unrunnable "
           "claim reported as unsettleable would look like an honest limit of the vocabulary "
           "instead of an author mistake",
           n_n > 0 and PM.CAUSE_MISSING_FIELD in out_n and "needle" in out_n)

    n_k, out_k = _pm_check([("a.yaml", _pm_emit([_pm_claim(waived="trust me")]))])
    expect("VELDO-0004 AC1: an UNRECOGNISED key on a claim is refused, not ignored - a closed set "
           "whose extra keys are ignored is not closed, and `waived` is exactly the key somebody "
           "would add to make an inconvenient claim stop counting",
           n_k > 0 and PM.CAUSE_KEY_UNRECOGNIZED in out_k and "waived" in out_k)

    n_d, out_d = _pm_check([("a.yaml", _pm_emit([_pm_claim()])),
                            ("b.yaml", _pm_emit([_pm_claim()], cid="PROMISES-two"))])
    expect("VELDO-0004 AC1: one claim id declared by TWO files is refused with BOTH files named",
           n_d > 0 and PM.CAUSE_DECLARED_TWICE in out_d and "a.yaml" in out_d
           and "b.yaml" in out_d)

    for bad, why in (("/etc/passwd", "absolute"), ("../outside.md", "escaping with ..")):
        n_t, out_t = _pm_check([("a.yaml", _pm_emit([_pm_claim(target=bad)]))])
        expect("VELDO-0004 AC1: a target that is %s is refused with PROMISE_TARGET_UNBOUND, so no "
               "claim can be settled against a file outside this repository" % why,
               n_t > 0 and PM.CAUSE_TARGET_UNBOUND in out_t)
    expect("VELDO-0004 AC1: every declared cause is registered under a unique name, so no two "
           "refusals share a spelling, and the predicate vocabulary has no duplicate either",
           len(set(PM.CAUSES)) == len(PM.CAUSES)
           and len(set(PM.PREDICATES)) == len(PM.PREDICATES)
           and set(PM.PRED_NEEDS) == set(PM.PREDICATES))


_pm_block("AC1", _pm_ac1)


# ---------------------------------------------------------------------------------------
# AC2. THE SETTLEMENT IS DERIVED BY RUNNING THE PREDICATE, NEVER READ FROM `believed`.
#
# FALSIFIED BY: read the outcome from `believed`, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _pm_ac2():
    rep, _ = _pm_report([("a.yaml", _pm_emit([
        _pm_claim(cid="CLAIM-A", predicate="text_absent", believed="SUPPORTED")]))])
    expect("VELDO-0004 AC2: a claim whose author BELIEVED it supported settles CONTRADICTED when "
           "the predicate fails - the needle IS in the document, so text_absent is false. The "
           "believed field is not consulted; it exists only so the report can name a claim whose "
           "author and whose tree disagree, which it does",
           [s["claim"] for s in rep["contradicted"]] == ["CLAIM-A"]
           and [s["claim"] for s in rep["author_disagrees"]] == ["CLAIM-A"]
           and rep["supported"] == [])

    rep2, _ = _pm_report([("a.yaml", _pm_emit([
        _pm_claim(cid="CLAIM-B", predicate="text_present", believed="CONTRADICTED")]))])
    expect("VELDO-0004 AC2 NEGATIVE CONTROL, and it is the leg that matters: a claim whose author "
           "believed it CONTRADICTED settles SUPPORTED when the predicate holds. So `believed` is "
           "ignored in BOTH directions rather than merely overridden in the failing one - a module "
           "that trusted the field when it said contradicted would pass the row above",
           [s["claim"] for s in rep2["supported"]] == ["CLAIM-B"]
           and [s["claim"] for s in rep2["author_disagrees"]] == ["CLAIM-B"]
           and rep2["contradicted"] == [])

    with tempfile.TemporaryDirectory() as d:
        base, pdir = _pm_tree(
            d, [("a.yaml", _pm_emit([
                _pm_claim(cid="CLAIM-S", predicate="symbol_defined", target="mod.py",
                          symbol="real_function"),
                _pm_claim(cid="CLAIM-T", predicate="symbol_defined", target="mod.py",
                          symbol="mentioned_only")]))],
            docs=[("mod.py", "def real_function():\n    \"\"\"mentioned_only is named here.\"\"\"\n"
                             "    return 1\n")])
        rep3 = PM.promise_report(pdir=pdir, root=base, parse=V.parse_yamlish)
        expect("VELDO-0004 AC2: symbol_defined reads the AST, so a function that EXISTS is "
               "supported and a name that appears only in a DOCSTRING is contradicted. A substring "
               "check would call both supported, which is the exact false positive that defeated an "
               "absence scan earlier in this project",
               [s["claim"] for s in rep3["supported"]] == ["CLAIM-S"]
               and [s["claim"] for s in rep3["contradicted"]] == ["CLAIM-T"])


_pm_block("AC2", _pm_ac2)


# ---------------------------------------------------------------------------------------
# AC3. UNSETTLEABLE IS FIRST-CLASS AND NEVER FOLDED INTO SUPPORTED.
#
# FALSIFIED BY: fold UNSETTLEABLE into SUPPORTED, and the stand-down row must go red.
# ---------------------------------------------------------------------------------------


def _pm_ac3():
    rep, lines = _pm_report([("a.yaml", _pm_emit([
        _pm_claim(cid="CLAIM-U", predicate="unsettleable", drop=("target",),
                  note="taste, not a fact about the tree")]))])
    expect("VELDO-0004 AC3: a corpus whose claims are ALL unsettleable STANDS THE REPORT DOWN "
           "rather than announcing zero contradictions. 'The tree supports this' and 'nothing here "
           "can decide this' are opposite facts about how far to trust the report, and reporting a "
           "clean run over a corpus where no predicate decided anything is the confident zero this "
           "migration kept finding",
           rep["stood_down"] is True
           and rep["reason"] == PM.STAND_DOWN_NOTHING_SETTLEABLE
           and any("stood down" in ln for ln in lines))

    rep2, lines2 = _pm_report([("a.yaml", _pm_emit([
        _pm_claim(cid="CLAIM-V", predicate="text_present"),
        _pm_claim(cid="CLAIM-U", predicate="unsettleable", drop=("target",),
                  note="a matter of taste")]))])
    expect("VELDO-0004 AC3 NEGATIVE CONTROL: with ONE settleable claim beside it the report "
           "answers, the unsettleable claim is counted in its OWN bucket and named on the page, and "
           "it never appears among the supported. The two fixtures differ by exactly one claim",
           rep2["stood_down"] is False
           and [s["claim"] for s in rep2["supported"]] == ["CLAIM-V"]
           and [s["claim"] for s in rep2["unsettleable"]] == ["CLAIM-U"]
           and any("UNSETTLEABLE CLAIM-U" in ln for ln in lines2))

    expect("VELDO-0004 AC3: NO SCORE IS PRINTED. No key is a ratio or a percentage and no value in "
           "the report is a float, because a proportion of a corpus nobody enumerated is exactly "
           "the number that would get quoted out of it",
           not any(w in k.lower() for k in rep2
                   for w in ("percent", "pct", "ratio", "score", "coverage"))
           and not any(isinstance(v, float) for v in rep2.values())
           and not any(isinstance(v, float) for s in rep2["supported"] for v in s.values()))

    expect("VELDO-0004 AC3: the three outcomes PARTITION the settleable claims exactly - every "
           "claim lands in one bucket and the buckets sum to the claim count",
           len(rep2["supported"]) + len(rep2["contradicted"]) + len(rep2["unsettleable"])
           == rep2["claims"])


_pm_block("AC3", _pm_ac3)


# ---------------------------------------------------------------------------------------
# AC4. A CONTRADICTION CARRIES WHAT IT MEASURED, SO A HUMAN CAN OVERTURN IT.
#
# FALSIFIED BY: drop the measured evidence from a settlement, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _pm_ac4():
    rep, lines = _pm_report([("a.yaml", _pm_emit([
        _pm_claim(cid="CLAIM-C", predicate="path_exists", target="docs/missing.md"),
        _pm_claim(cid="CLAIM-D", predicate="text_present")]))])
    con = rep["contradicted"][0]
    sup = rep["supported"][0]
    expect("VELDO-0004 AC4: every CONTRADICTED settlement carries the predicate, the target it "
           "read AND what it found there. This is the finding that produced the item: the "
           "2026-08-10 audit raised fifteen accusations and FIVE WERE OVERTURNED, and an accusation "
           "whose evidence is not in the record is indistinguishable from a correct one - while the "
           "cost of acting on a wrong one is deleting a true sentence from a shipped document",
           con["predicate"] == "path_exists" and con["target"] == "docs/missing.md"
           and con["measured"] == "path does not exist"
           and con["document"] == "docs/doc.md" and con["locator"] == "line 12")
    expect("VELDO-0004 AC4: the SAME evidence is recorded for a SUPPORTED settlement, because a "
           "settlement that only explains itself when it accuses is one nobody can audit. The "
           "supported reading names the offset it found the needle at",
           sup["measured"] and "found" in sup["measured"] and "offset" in sup["measured"]
           and sup["predicate"] == "text_present")
    expect("VELDO-0004 AC4: the printed contradiction line carries the reading too, so the person "
           "deciding whether to change a document sees the measurement without opening a JSON file",
           any("CONTRADICTED CLAIM-C" in ln and "path does not exist" in ln
               and "docs/missing.md" in ln for ln in lines))

    with tempfile.TemporaryDirectory() as d:
        base, pdir = _pm_tree(d, [("a.yaml", _pm_emit([
            _pm_claim(cid="CLAIM-E", predicate="text_present", target="docs/unreadable.md")]))])
        (base / "docs" / "unreadable.md").mkdir(parents=True, exist_ok=True)
        rep2 = PM.promise_report(pdir=pdir, root=base, parse=V.parse_yamlish)
        expect("VELDO-0004 AC4: a target that cannot be READ settles UNSETTLEABLE with the reason, "
               "never CONTRADICTED. Accusing a document because the checker could not open a file "
               "is the wrong-accusation failure mode itself, so an unreadable target is a limit of "
               "the measurement and is reported as one",
               [s["claim"] for s in rep2["unsettleable"]] == ["CLAIM-E"]
               and "could not be read" in rep2["unsettleable"][0]["measured"]
               and rep2["contradicted"] == [])


_pm_block("AC4", _pm_ac4)


# ---------------------------------------------------------------------------------------
# AC5. ADOPTION SAFE, AND IT GATES NOTHING.
#
# FALSIFIED BY: remove the absent-corpus stand-down, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _pm_ac5():
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        rep = PM.promise_report(pdir=base / ".veldo" / "promises", root=base,
                                parse=V.parse_yamlish)
        expect("VELDO-0004 AC5: a repository with no .veldo/promises/ directory STANDS DOWN by name "
               "rather than reporting a clean corpus it never looked at. 'Nobody has extracted a "
               "document's claims here' and 'no document makes a false claim' are different facts",
               rep["stood_down"] is True and "NOT the same fact" in rep["reason"]
               and PM.check_promises_dir(base / ".veldo" / "promises", base, V.parse_yamlish,
                                         V.fail) == 0)

    rep_live, _ = _pm_report([("a.yaml", _pm_emit([_pm_claim()]))])
    expect("VELDO-0004 AC5 NEGATIVE CONTROL: with a corpus present the SAME report answers, so the "
           "stand-down is a measurement of the tree and not this module's only behaviour",
           rep_live["stood_down"] is False and len(rep_live["supported"]) == 1)
    expect("VELDO-0004 AC5: the report carries ONE KEY SHAPE whether it stood down or not, so a "
           "consumer never guesses whether a key is missing or genuinely empty",
           sorted(rep_live) == sorted(PM.REPORT_KEYS)
           and sorted(_pm_report([])[0]) == sorted(PM.REPORT_KEYS))

    import ast as _pm_a

    def _pm_loads(path):
        try:
            tree = _pm_a.parse(path.read_text())
        except (OSError, SyntaxError):
            return False
        for node in _pm_a.walk(tree):
            if not isinstance(node, _pm_a.Call):
                continue
            fname = (node.func.attr if isinstance(node.func, _pm_a.Attribute)
                     else getattr(node.func, "id", ""))
            if fname not in ("spec_from_file_location", "_organ", "_load", "_sibling"):
                continue
            for arg in list(node.args) + [kw.value for kw in node.keywords]:
                if isinstance(arg, _pm_a.Constant) and isinstance(arg.value, str) \
                        and arg.value.rstrip(".py").endswith("promises"):
                    return True
        return False

    _pm_loaders = sorted(p.name for p in list((ROOT / ".veldo").glob("*.py"))
                         + list((ROOT / "scripts").glob("*.py"))
                         if p.name != "promises.py" and _pm_loads(p))
    expect("VELDO-0004 AC5: NO GATE STAGE LOADS THIS. PLAN-0018 NG3 says a completeness organ that "
           "BLOCKED on a heuristic verdict would cut true sentences and stop real work, and this is "
           "that organ: advisory, loud, human-resolved. Asserted over LOADS via the AST, not over "
           "mentions, because /veldo:init legitimately NAMES the module in order to ship it",
           _pm_loaders == [])


_pm_block("AC5", _pm_ac5)
