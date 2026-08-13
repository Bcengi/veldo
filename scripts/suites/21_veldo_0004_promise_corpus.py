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

EVERY PREDICATE, NOT ONE OF THEM. AC4's claim is universal: EVERY contradiction carries the
predicate, the target it read and what it found. That was asserted on path_exists alone, and
measured by independent review, the evidence could be stripped from path_absent, text_present,
text_absent and symbol_defined with this fragment fully green - path_absent was not settled here
even once. The AC4 block now drives all five mechanical predicates in both directions from ONE
table whose key set is asserted EQUAL to the module's own PREDICATES, so a predicate added to the
module without a fixture reds a row rather than inheriting an untested universal claim.
"""
PM = V._VC._organ("promises", ROOT / ".veldo" / "promises.py")


def _pm_block(label, fn):
    """Red a NAMED row when a criterion's block raises, instead of losing every row below it."""
    try:
        fn()
    except Exception as _pm_e:                   # noqa: BLE001 - a raise must RED a row, never skip
        expect("VELDO-0004 %s: the block ran to completion rather than raising (%r)"
               % (label, _pm_e), False)


def _pm_captured(fn, *a, **kw):
    """(value, raised) for ONE read, so a RAISE reds the row that NAMED the read.

    The block wrapper above is the last line of defence and it is a blunt one: when a read raises,
    the wrapper reds ONE row about "the block" and every row below the raise never runs, which is
    indistinguishable from a mutation that deleted coverage. Measured on this fragment: AC1's own
    declared falsification raised KeyError out of the validator and the run went from 56 rows to 34
    with a single red naming the wrapper. A read a row cares about is captured HERE so the row
    itself can require that nothing was raised."""
    try:
        return fn(*a, **kw), None
    except Exception as _pm_e:                   # noqa: BLE001 - the raise is the measurement
        return None, _pm_e


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

    # CAPTURED, so a RAISE reds THIS row rather than the block wrapper. This is the row AC1's own
    # declared falsification names, and driving that falsification showed the validator raising
    # KeyError out of `PRED_NEEDS[pred]` before it ever reached the refusal: the wrapper reddened,
    # 22 rows below never ran, and the recorded evidence read as teeth when it was a shorter run.
    # The read is required to ANSWER as well as to refuse, so the unrunnable-predicate path is
    # asserted here rather than left to a mutation to discover.
    _pm_res_lf, _pm_raised_lf = _pm_captured(
        _pm_check, [("a.yaml", _pm_emit([_pm_claim(predicate="looks_fine")]))])
    n, out = _pm_res_lf if _pm_raised_lf is None else (0, "the read RAISED %r" % (_pm_raised_lf,))
    expect("VELDO-0004 AC1: a claim declaring predicate `looks_fine` is refused with "
           "PROMISE_PREDICATE_UNKNOWN and the allowed predicates named, AND THE READ RETURNS "
           "RATHER THAN RAISING: a validator that dies on an unknown predicate takes every other "
           "claim in every other corpus with it. The vocabulary is tiny on purpose: a predicate "
           "that needed judgement would be a machine making a review-lane call, which is the "
           "confident wrongness this whole item exists to avoid. Measured: %s"
           % ("no raise" if _pm_raised_lf is None else repr(_pm_raised_lf)),
           _pm_raised_lf is None and n > 0 and PM.CAUSE_PREDICATE_UNKNOWN in out
           and "text_present" in out and "unsettleable" in out)

    _pm_res_lft, _pm_raised_lft = _pm_captured(
        _pm_check, [("a.yaml", _pm_emit([_pm_claim(predicate="looks_fine",
                                                   target="/etc/passwd")]))])
    n_lft, out_lft = _pm_res_lft if _pm_raised_lft is None else (0, "RAISED %r" % (_pm_raised_lft,))
    expect("VELDO-0004 AC1: a claim declaring an unknown predicate AND an unbound target names "
           "BOTH refusals, because this reader's contract is every structural problem with one "
           "claim and an author fixing them one at a time is what a named taxonomy prevents. "
           "Measured: %s" % ("no raise" if _pm_raised_lft is None else repr(_pm_raised_lft)),
           _pm_raised_lft is None and n_lft > 0
           and PM.CAUSE_PREDICATE_UNKNOWN in out_lft and PM.CAUSE_TARGET_UNBOUND in out_lft)

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

    # THE CORPUS'S OWN KEY SET IS CLOSED TOO, and this half was entirely unasserted: measured by
    # independent review, CORPUS_REQUIRED, the unrecognised-corpus-key refusal and the
    # schema-mismatch refusal could all be DELETED with this fragment green, because every row
    # above drops fields from a CLAIM and none from the head. It matters to AC4 as much as to AC1:
    # `document` is a corpus field, and a corpus that omits it prints None as the document on every
    # contradiction line, which is the locator a human needs in order to overturn the accusation.
    for field in PM.CORPUS_REQUIRED:
        if field == "claims":
            body = "\n".join("%s: %s" % kv for kv in (("schema", PM.SCHEMA),
                                                      ("id", "PROMISES-doc"),
                                                      ("version", 1),
                                                      ("document", "docs/doc.md"))) + "\n"
            n_c, out_c = _pm_check([("a.yaml", body)])
        else:
            n_c, out_c = _pm_check([("a.yaml", _pm_emit([_pm_claim()], drop=(field,)))])
        expect("VELDO-0004 AC1: a CORPUS declaring no %s is refused with PROMISE_MISSING_FIELD "
               "naming the field, so the head of the record is closed by the same rule as the "
               "claims inside it" % field,
               n_c > 0 and PM.CAUSE_MISSING_FIELD in out_c and field in out_c)

    n_ck, out_ck = _pm_check([("a.yaml", _pm_emit([_pm_claim()], waived="trust me"))])
    expect("VELDO-0004 AC1: an UNRECOGNISED key on the CORPUS is refused too, for the same reason "
           "it is on a claim: a closed set whose extra keys are ignored is not closed, and a corpus "
           "level `waived` would take every claim in the file out of the count at once",
           n_ck > 0 and PM.CAUSE_KEY_UNRECOGNIZED in out_ck and "waived" in out_ck)

    n_s, out_s = _pm_check([("a.yaml", _pm_emit([_pm_claim()], schema="veldo.promises/v2"))])
    expect("VELDO-0004 AC1: a corpus declaring a DIFFERENT schema is refused with the expected one "
           "named, because a record read under the wrong contract is read by guessing",
           n_s > 0 and PM.CAUSE_UNREADABLE in out_s and PM.SCHEMA in out_s)

    n_u, out_u = _pm_check([("a.yaml", "this file is not a corpus at all\n")])
    expect("VELDO-0004 AC1: a corpus file the ONE parser cannot read is refused with "
           "PROMISE_UNREADABLE naming the file. The module's law is that an unreadable corpus is "
           "CARRIED as an error and never dropped, because a dropped file is a coverage figure "
           "quoted without the weakness that produced it - and until this row the cause fired in "
           "no assertion at all",
           n_u > 0 and PM.CAUSE_UNREADABLE in out_u and "a.yaml" in out_u)

    n_ml, out_ml = _pm_check([("a.yaml", "- one\n- two\n")])
    expect("VELDO-0004 AC1: a corpus that parses to a LIST rather than a mapping is refused with "
           "PROMISE_UNREADABLE naming what it got, rather than being walked as if it were a record",
           n_ml > 0 and PM.CAUSE_UNREADABLE in out_ml and "list" in out_ml)

    n_i, out_i = _pm_check([("a.yaml", _pm_emit([_pm_claim(needle=200)]))])
    expect("VELDO-0004 AC1: `needle: 200` - the obvious way to write 'the document says 200 "
           "countries' - is refused AT READ TIME with the type named. The one front-matter parser "
           "coerces a bare number to an INT, and `200 in text` is a TypeError that loses the whole "
           "report and every other corpus in it, so this belongs in the refusal taxonomy rather "
           "than in a traceback",
           n_i > 0 and PM.CAUSE_MISSING_FIELD in out_i and "int" in out_i and "200" in out_i)

    with tempfile.TemporaryDirectory() as d:
        base, _pdir_i = _pm_tree(d)
        s_int = PM.settle(_pm_claim(cid="CLAIM-INT", needle=200), root=base)
        s_sym = PM.settle(_pm_claim(cid="CLAIM-SYM", predicate="symbol_defined", target="mod.py",
                                    symbol=200), root=base)
        expect("VELDO-0004 AC1: and a claim that reached the settler anyway does not CRASH it - an "
               "int needle and an int symbol each settle UNSETTLEABLE naming the type. A settler "
               "that throws takes every claim in every other corpus down with it, and an int "
               "symbol would otherwise be a FALSE ACCUSATION: nothing is named 200, so the claim "
               "would be contradicted",
               s_int["outcome"] == PM.UNSETTLEABLE and "int" in s_int["measured"]
               and s_sym["outcome"] == PM.UNSETTLEABLE and "int" in s_sym["measured"])

    with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as elsewhere:
        base, _pdir_s = _pm_tree(d)
        outside = Path(elsewhere) / "secret.md"
        outside.write_text("a thing that is here")
        (base / "docs" / "link.md").symlink_to(outside)
        s_link = PM.settle(_pm_claim(cid="CLAIM-LINK", target="docs/link.md"), root=base)
        expect("VELDO-0004 AC1: a target that is a SYMLINK out of the tree settles UNSETTLEABLE "
               "naming where it resolved, never SUPPORTED. target_problems refuses an absolute "
               "path and a '..' segment in the TEXT of a target and a committed symlink is "
               "neither, so the row above claims more than the text check delivers unless the "
               "resolved path is compared to the resolved root as well",
               s_link["outcome"] == PM.UNSETTLEABLE and "outside this repository" in s_link["measured"])

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

    # DECLARING `unsettleable` MUST NOT BUY SILENCE ABOUT WHAT THE AUTHOR EXPECTED. Measured by
    # independent review: a claim declaring predicate unsettleable settles without reading anything,
    # needs no target, and `author_disagrees` excludes the outcome - so the author's own `believed`
    # was recorded in the settlement and printed NOWHERE, which is the `waived: trust me` move the
    # AC1 row above refuses, under a name the vocabulary allows. Excluding it from author_disagrees
    # is right, because no predicate read anything for the author to disagree WITH; leaving the
    # declared expectation unprinted is the recorded-but-unreported stand-down instead.
    rep_b, lines_b = _pm_report([("a.yaml", _pm_emit([
        _pm_claim(cid="CLAIM-V2", predicate="text_present"),
        _pm_claim(cid="CLAIM-B", predicate="unsettleable", drop=("target",),
                  believed="SUPPORTED", note="taste, not a fact about the tree")]))])
    expect("VELDO-0004 AC3: a claim that declares `unsettleable` AND what its author BELIEVED has "
           "that belief PRINTED on its own line. It is correctly absent from author_disagrees - no "
           "predicate read anything, so there is no reading to disagree with - and that is exactly "
           "why the page must carry it: otherwise declaring unsettleable buys total silence about "
           "an expectation nothing checked, which is `waived: trust me` under an allowed name",
           [s["claim"] for s in rep_b["unsettleable"]] == ["CLAIM-B"]
           and rep_b["author_disagrees"] == []
           and any("UNSETTLEABLE CLAIM-B" in ln and "BELIEVED this SUPPORTED" in ln
                   and "no predicate here checked that" in ln for ln in lines_b))

    rep_nb, lines_nb = _pm_report([("a.yaml", _pm_emit([
        _pm_claim(cid="CLAIM-V3", predicate="text_present"),
        _pm_claim(cid="CLAIM-N", predicate="unsettleable", drop=("target",),
                  note="taste, not a fact about the tree")]))])
    expect("VELDO-0004 AC3 CONTROL for the row above, differing in exactly one field: the same "
           "claim WITHOUT `believed` is still named on the page and carries no belief sentence, so "
           "the row above discriminates rather than matching a line printed on every unsettleable "
           "settlement",
           [s["claim"] for s in rep_nb["unsettleable"]] == ["CLAIM-N"]
           and any("UNSETTLEABLE CLAIM-N" in ln for ln in lines_nb)
           and not any("BELIEVED" in ln for ln in lines_nb))

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

    # A MALFORMED CLAIM USED TO VANISH, AND THE PAGE THEN PRINTED A CONFIDENT ZERO. all_claims
    # dropped it and deferred to check_promises_dir, which nothing in an adopting tree calls -
    # AC5 forbids anything loading this module - so the report was the only surface and it counted
    # one claim where the author wrote two. That is this criterion's own confident zero, one level
    # down from the file-level version the module already carried loudly.
    rep_m, lines_m = _pm_report([("a.yaml", _pm_emit([_pm_claim(cid="CLAIM-GOOD"),
                                                     _pm_claim(cid="CLAIM-BAD",
                                                               drop=("locator",))]))])
    expect("VELDO-0004 AC3: a MALFORMED claim beside a well-formed one is CARRIED into the report "
           "with its cause and named on the page, never dropped. The author declared TWO claims: a "
           "report that counted one, said 0 CONTRADICTED and mentioned the difference nowhere is "
           "the confident zero this criterion exists to prevent",
           rep_m["declared"] == 2 and rep_m["claims"] == 1
           and [m["claim"] for m in rep_m["malformed"]] == ["CLAIM-BAD"]
           and PM.CAUSE_MISSING_FIELD in rep_m["malformed"][0]["causes"]
           and any("COULD NOT BE READ AS CLAIMS" in ln and "CLAIM-BAD" in ln for ln in lines_m))

    expect("VELDO-0004 AC3: DECLARED accounts for every claim an author wrote - the settled buckets "
           "plus the malformed ones - so no claim can leave the corpus without appearing in a count",
           rep_m["declared"] == rep_m["claims"] + len(rep_m["malformed"])
           and len(rep_m["supported"]) + len(rep_m["contradicted"]) + len(rep_m["unsettleable"])
           == rep_m["claims"])

    rep_o, lines_o = _pm_report([("a.yaml", _pm_emit([_pm_claim(cid="CLAIM-BAD",
                                                                drop=("locator",))]))])
    expect("VELDO-0004 AC3: a corpus whose ONLY claim is malformed stands the report down with a "
           "reason that says what actually happened - the corpus DOES declare a claim, and it is "
           "the claim that is broken. 'No corpus declares a claim at all' is a false sentence in a "
           "module whose whole thesis is that a settlement names what it measured",
           rep_o["stood_down"] is True and rep_o["reason"] == PM.STAND_DOWN_NOTHING_READABLE
           and rep_o["declared"] == 1 and rep_o["claims"] == 0
           and any("COULD NOT BE READ AS CLAIMS" in ln for ln in lines_o))

    rep_u, lines_u = _pm_report([("bad.yaml", "this file is not a corpus at all\n"),
                                 ("good.yaml", _pm_emit([_pm_claim(cid="CLAIM-W")]))])
    expect("VELDO-0004 AC3: an UNREADABLE corpus beside a readable one is carried into the report "
           "and named on the page as absent from every count above, so a file that was silently "
           "discarded cannot become a clean run over a corpus nobody read",
           len(rep_u["unreadable"]) == 1 and rep_u["unreadable"][0].endswith("bad.yaml")
           and rep_u["corpora"] == 2 and rep_u["claims"] == 1
           and any("COULD NOT BE READ" in ln and "bad.yaml" in ln for ln in lines_u))

    import re as _pm_re
    _pm_score = _pm_re.compile(r"\d+\.\d+|%|percent|ratio|proportion|score|per cent")
    _pm_all_lines = lines + lines2 + lines_b + lines_nb + lines_m + lines_o + lines_u
    expect("VELDO-0004 AC3: NO SCORE IS PRINTED ON THE PAGE EITHER, and the page is the surface a "
           "number would be quoted FROM: no line of any report above carries a float, a percent "
           "sign, or the words percent, ratio, proportion or score. Asserted over report_lines and "
           "not only over the report dict, because the dict is not what a stranger reads and a "
           "printed '50 percent of this corpus is supported (0.50)' passed every dict row here",
           _pm_all_lines and not any(_pm_score.search(ln.lower()) for ln in _pm_all_lines))


_pm_block("AC3", _pm_ac3)


# ---------------------------------------------------------------------------------------
# AC4. A CONTRADICTION CARRIES WHAT IT MEASURED, SO A HUMAN CAN OVERTURN IT.
#
# FALSIFIED BY: drop the measured evidence from ANY ONE of the five mechanical predicates'
# contradiction paths, and that predicate's row below must go red.
# ---------------------------------------------------------------------------------------

# THE WHOLE VOCABULARY, BOTH DIRECTIONS, ONE TABLE. AC4's claim is universal and it was pinned on
# path_exists alone: measured by independent review, one mutation setting measured, predicate AND
# target to None on every contradiction from path_absent, the text branch and the symbol branch
# left this fragment at 53 passed, 0 failed - and each branch was vacuous on its own too. The text
# predicates are what this item is actually about, because a claim a document makes IS text.
#
# Each entry is (contradicting claim fields, a token its reading MUST name, supporting claim
# fields, a token that reading must name). The tokens are what makes the row a check on the
# READING rather than on the presence of a string: a constant "contradicted" in the measured
# column would satisfy `is a non-empty str` and satisfies nothing here.
_PM_EV_DOCS = (("docs/doc.md", "a thing that is here"),
               ("mod.py", "def a_symbol():\n    return 1\n"))
_PM_EVIDENCE = {
    "path_exists": (dict(target="docs/missing.md"), "path does not exist",
                    dict(target="docs/doc.md"), "path exists"),
    "path_absent": (dict(target="docs/doc.md"), "path exists",
                    dict(target="docs/missing.md"), "path does not exist"),
    "text_present": (dict(target="docs/doc.md", needle="a sentence nobody wrote"),
                     "a sentence nobody wrote",
                     dict(target="docs/doc.md", needle="a thing that is here"),
                     "a thing that is here"),
    "text_absent": (dict(target="docs/doc.md", needle="a thing that is here"),
                    "a thing that is here",
                    dict(target="docs/doc.md", needle="a sentence nobody wrote"),
                    "a sentence nobody wrote"),
    "symbol_defined": (dict(target="mod.py", symbol="never_written"), "never_written",
                       dict(target="mod.py", symbol="a_symbol"), "a_symbol"),
}


def _pm_ac4_every_predicate():
    """Every mechanical predicate settled in both directions, with the evidence asserted on each."""
    claims = []
    for pred in sorted(_PM_EVIDENCE):
        con_kw, _ct, sup_kw, _st = _PM_EVIDENCE[pred]
        claims.append(_pm_claim(cid="CON-%s" % pred, predicate=pred, **con_kw))
        claims.append(_pm_claim(cid="SUP-%s" % pred, predicate=pred, **sup_kw))
    rep, lines = _pm_report([("all.yaml", _pm_emit(claims))], docs=_PM_EV_DOCS)
    settled = rep["supported"] + rep["contradicted"] + rep["unsettleable"]
    by = {s["claim"]: s for s in settled}

    for pred in sorted(_PM_EVIDENCE):
        con_kw, con_tok, sup_kw, sup_tok = _PM_EVIDENCE[pred]
        c = by.get("CON-%s" % pred, {})
        expect("VELDO-0004 AC4 [%s]: the CONTRADICTED settlement carries the predicate, the target "
               "it read AND what it found there, in the record and on the printed line. The 2026-08-10 "
               "audit raised fifteen accusations and FIVE WERE OVERTURNED: an accusation whose "
               "evidence is not in the record is indistinguishable from a correct one, and the cost "
               "of acting on a wrong one is deleting a true sentence from a shipped document" % pred,
               c.get("outcome") == PM.CONTRADICTED and c.get("predicate") == pred
               and c.get("target") == con_kw["target"]
               and isinstance(c.get("measured"), str) and con_tok in c["measured"]
               and c.get("document") == "docs/doc.md" and c.get("locator") == "line 12"
               and any(("CONTRADICTED CON-%s" % pred) in ln and pred in ln
                       and con_kw["target"] in ln and con_tok in ln for ln in lines))
        s = by.get("SUP-%s" % pred, {})
        expect("VELDO-0004 AC4 [%s]: the SUPPORTED settlement of the same predicate carries the "
               "same three things, because a settlement that only explains itself when it accuses "
               "is one nobody can audit" % pred,
               s.get("outcome") == PM.SUPPORTED and s.get("predicate") == pred
               and s.get("target") == sup_kw["target"]
               and isinstance(s.get("measured"), str) and sup_tok in s["measured"])

    expect("VELDO-0004 AC4: the table above covers EVERY mechanical predicate the module ships, "
           "asserted as SET EQUALITY against PREDICATES rather than by counting fixtures, so a "
           "predicate added to the module cannot inherit this criterion's universal claim without "
           "a fixture that drives it in both directions",
           set(_PM_EVIDENCE) == set(PM.PREDICATES) - {PM.PRED_UNSETTLEABLE})

    expect("VELDO-0004 AC4: and the universal is asserted as a universal - EVERY settlement in the "
           "report, all ten, five contradictions and five supports, carries a predicate, a target "
           "and a reading of more than a word. A row that checked one predicate would report safety "
           "for the other four, which is exactly what was measured here before this block existed",
           len(rep["contradicted"]) == 5 and len(rep["supported"]) == 5
           and rep["unsettleable"] == [] and rep["declared"] == 10
           and all(s["predicate"] in PM.PREDICATES and isinstance(s["target"], str) and s["target"]
                   and isinstance(s["measured"], str) and len(s["measured"]) > 8
                   and len(s["measured"].split()) > 1
                   for s in rep["supported"] + rep["contradicted"]))


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
_pm_block("AC4 every predicate", _pm_ac4_every_predicate)


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
    import os as _pm_os

    # THE IDIOM THIS REPOSITORY ACTUALLY USES, AND THE WHOLE TREE IT LIVES IN. The scan this
    # replaces keyed on the name of the CALLED function and globbed exactly two directories, so it
    # was blind to `functools.partial(_organ, name, path)` - the wiring .veldo/validate_checks.py
    # uses for ALL NINE of its organs - and never opened bin/veldo (documented as the single front
    # door, no .py suffix), scripts/suites/, or any subdirectory. Measured by independent review:
    # the partial wiring loaded this organ inside a required gate stage, proved by the module's own
    # SCHEMA constant appearing in a marker file during the run, with this row GREEN. The one
    # wiring anybody would write was invisible to the assertion that forbids it.
    # The import machinery itself, plus the three cross-file organ helpers this codebase passes
    # between modules. Every OTHER loader name is DERIVED per file below rather than enumerated
    # here, because a hand-written list of helper names is the same losing enumeration that made
    # the previous scan blind: validate_checks.py calls its loader `_organ` and bin/veldo calls
    # its `_mod`, and the next one will be called something else again.
    _PM_MACHINERY = ("spec_from_file_location", "exec_module", "import_module", "load_module",
                     "__import__", "SourceFileLoader", "_organ", "_load", "_sibling")

    def _pm_loader_names(tree):
        """Every name in THIS file that loads a module: the machinery, and the transitive closure
        of functions whose bodies reach it, so a wrapper cannot launder the load."""
        names = set(_PM_MACHINERY)
        bodies = []
        for node in _pm_a.walk(tree):
            if isinstance(node, (_pm_a.FunctionDef, _pm_a.AsyncFunctionDef)):
                inner = {n.attr for n in _pm_a.walk(node) if isinstance(n, _pm_a.Attribute)}
                inner |= {n.id for n in _pm_a.walk(node) if isinstance(n, _pm_a.Name)}
                bodies.append((node.name, inner))
        changed = True
        while changed:
            changed = False
            for fname, inner in bodies:
                if fname not in names and (inner & names):
                    names.add(fname)
                    changed = True
        return names

    def _pm_names_promises(s):
        base = str(s).replace("\\", "/").rsplit("/", 1)[-1]
        if base.endswith(".py"):
            base = base[:-3]
        return base == "promises" or base.endswith("_promises")

    def _pm_strings_under(node):
        return [n.value for n in _pm_a.walk(node)
                if isinstance(n, _pm_a.Constant) and isinstance(n.value, str)]

    def _pm_call_names(call):
        """Every name that could BE the loader in one call: the callee AND the names handed to it
        as arguments, because partial() puts the loader in an argument and the callee is 'partial'."""
        out = []
        for n in [call.func] + list(call.args) + [kw.value for kw in call.keywords]:
            if isinstance(n, _pm_a.Attribute):
                out.append(n.attr)
            elif isinstance(n, _pm_a.Name):
                out.append(n.id)
        return set(out)

    def _pm_loads(path):
        """Whether this file LOADS the promises organ, over the whole call expression rather than
        its callee name. A non-Constant path argument no longer hides it either: the module can be
        named by any string constant anywhere in the call, or by a name bound to one."""
        try:
            tree = _pm_a.parse(path.read_text(errors="replace"))
        except (OSError, SyntaxError, ValueError):
            return False
        loaders = _pm_loader_names(tree)
        alias = set()
        for node in _pm_a.walk(tree):
            if isinstance(node, _pm_a.Assign) \
                    and any(_pm_names_promises(s) for s in _pm_strings_under(node.value)):
                alias |= {t.id for t in node.targets if isinstance(t, _pm_a.Name)}
        for node in _pm_a.walk(tree):
            if not isinstance(node, _pm_a.Call):
                continue
            names = _pm_call_names(node)
            if not (names & loaders):
                continue
            if (names & alias) or any(_pm_names_promises(s) for s in _pm_strings_under(node)):
                return True
        return False

    def _pm_python_sources():
        """Every Python source in BOTH trees: subdirectories included, and the extensionless
        executables too, because bin/veldo is the documented single front door and carries no .py
        suffix. An assertion is only ever as wide as the file set it reads."""
        out = []
        for dirpath, dirnames, filenames in _pm_os.walk(ROOT):
            dirnames[:] = sorted(x for x in dirnames
                                 if x not in (".git", "__pycache__", "node_modules", ".venv",
                                              "venv"))
            for fn in sorted(filenames):
                p = Path(dirpath) / fn
                if fn.endswith(".py"):
                    out.append(p)
                elif "." not in fn:
                    try:
                        head = p.open("rb").readline()
                    except OSError:
                        continue
                    if head.startswith(b"#!") and b"python" in head:
                        out.append(p)
        return out

    _pm_sources = _pm_python_sources()
    _pm_rel = {str(p.relative_to(ROOT)) for p in _pm_sources}
    expect("VELDO-0004 AC5: the surface that assertion is measured over CONTAINS the files a wiring "
           "would really go in - the organ inventory in .veldo/validate_checks.py and its engine "
           "twin, the documented single front door bin/veldo which has no .py suffix, the gate's "
           "own unit stage, and this fragment in scripts/suites/. The scan this replaces globbed "
           "two directories and opened none of the last three",
           {".veldo/validate_checks.py", "engine/.veldo/validate_checks.py", "bin/veldo",
            "scripts/selftest.py", "scripts/suites/21_veldo_0004_promise_corpus.py"} <= _pm_rel)

    _pm_loaders = sorted({p.name for p in _pm_sources if _pm_loads(p)})
    expect("VELDO-0004 AC5: NO GATE STAGE LOADS THIS. PLAN-0018 NG3 says a completeness organ that "
           "BLOCKED on a heuristic verdict would cut true sentences and stop real work, and this is "
           "that organ: advisory, loud, human-resolved. Asserted over LOADS via the AST, not over "
           "mentions, because /veldo:init legitimately NAMES the module in order to ship it - and "
           "asserted as an EQUALITY against the one file that must load it, this fragment, so a "
           "scan that went blind reports a set that is missing its own known load and reds instead "
           "of reading as safety",
           _pm_loaders == ["21_veldo_0004_promise_corpus.py"])


_pm_block("AC5", _pm_ac5)
