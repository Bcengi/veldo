"""VELDO-0001: every behaviour-bearing criterion declares its own falsification.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, which always
runs, so its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 17_veldo_0001_falsification_declared

WHAT IS UNDER TEST AND WHERE IT LIVES. The check is
validate_checks.check_falsification_declared, with its pure predicate falsification_problems
and its migration measurement falsification_migration. It is driven through V._VC, which is the
module instance .veldo/validate.py itself loaded and handed the ONE front-matter parser and the
ONE failure reporter, so these assertions exercise the same object the validator uses rather
than a second copy with test wiring.

WHAT THIS FRAGMENT REFUSES TO DO, because it is the whole point of the item it tests. Every
property below is asserted in BOTH directions. The rule's product is a REFUSAL, and a refusal
asserted alone is indistinguishable from a validator that refuses everything: so each refusing
row is paired with an ACCEPTING row over a fixture that differs in exactly the one field, and
each stand-down row is paired with a row proving the same run still refuses a gated fixture. The
four criteria of VELDO-0001 each declare a FALSIFIED BY and a NEGATIVE CONTROL, and the rows
below are named for them.

TEETH, RE-MEASURED AT THIS COMMIT RATHER THAN CLAIMED, AND EVERY COUNT CARRIES ITS METHOD. Each of
the four declared falsifications and each of the four negative controls was applied to a scratch
copy of the repository, DIFFED against a pre-mutation snapshot to prove the edit landed, run, and
restored. A mutation to validate_checks.py is mirrored into engine/.veldo/validate_checks.py, so
the byte-identity row is never counted as one of its casualties. THE METHOD, because a count
without its method is not a measurement: the first number is FAILED ROWS IN THE WHOLE RUN of
`python3 scripts/selftest.py --suite 17_veldo_0001_falsification_declared`, the second is how many
of those are THIS FRAGMENT's rows, and the two differ only where a mutation also breaks a row in
shared.py. RE-DRIVEN 2026-08-13 over the F2 and F6 remediation, because rows were added and a count
nobody re-drives goes stale in silence (that is this fragment's own F4). Unmodified: 60 rows here, 86
passed, 0 failed.
  AC1  delete the per-criterion loop in falsification_problems, so only the presence and shape of
       acceptance_criteria is checked: 23 failed, 23 here, including the fixture positive control,
       the three-criteria refusal count, the per-criterion cause rows, the rendered refusal lines,
       the whole of AC2, which reaches its causes through the same loop, and both
       template-to-validator rows. The AC1 accepting row stayed GREEN, which is what makes the
       count a measurement of the loop rather than of the module failing to load.
  AC2  accept any non-empty string (drop both floors in _falsification_statement): 7 failed, 7
       here: the `n/a` row, the padded row, both floor rows, the whitespace-collapsed row, the
       both-floors-have-teeth row and the no-exemption-keyword row. The empty, whitespace and
       bare-key rows stay GREEN, correctly, because this mutation leaves the empty guard standing,
       and the genuine one-sentence declaration stays accepted.
       THIS COUNT WAS RECORDED AS 8 AND IT IS 7, found by the independent review (VELDO-0001 F4)
       and reproduced here. Neither reading of the criterion's own words reaches 8: keeping the
       empty guard gives 7, dropping it as well gives 9. The other seven counts were each low by
       exactly one for a knowable reason, which is the more useful half of that finding: the F3
       remediation added five rows to this fragment and nobody re-drove the mutations, so a record
       that had been true went stale silently. This one was wrong when it was written.
  AC3  ignore behavior_bearing (falsification_gated returns True always, and the presence gate is
       removed): 10 failed, 9 here - the two stand-down rows, the REPORTED row, the additive
       second-corpus row, the registry row, the one-definition row, the seeded migration row, its
       negative control and the live non-vacuity row - plus "good spec accepted" in shared.py,
       whose fixture declares no behaviour and is refused once the gate is gone. The
       behaviour-bearing refusal stayed RED, so the stand-down is not what makes cases pass.
  AC4  remove the falsified_by key from engine/specs/TEMPLATE.md: 4 failed, 4 here: the
       declaration row, the parsed-key row, the template-drives-the-validator row and the
       every-template glob row.
AND THE FOUR NEGATIVE CONTROLS were driven the same way, by breaking what each one exists to
catch: a BLANKET refusal (28 failed, 28 here, the AC1 accepting row and both
written-from-the-template rows among them), a character floor raised to 500 so a real sentence is
refused (11 failed, 11 here, the AC2 accepting row among them), a BLANKET stand-down (34 failed, 34
here, the AC3 still-refused row among them), and a template carrying `falsifiable_by`, a spelling
nothing enforces (5 failed, 5 here, including the misspelling row, so that row is not "some string
is present in a long file").
AND THE ROWS ADDED BY THE TWO REMEDIATIONS were driven the same way. Loosening the spine-document
predicate off FALSIFICATION_FIELD to a substring reds its constructed control ALONE (1 failed, 1
here), and appending a sentence to docs/method.md naming both misspellings in order to warn against
them leaves the run GREEN where the absence pin it replaced went red. Deleting the stand-down REPORT
from _falsification_stand_down, leaving the record standing, reds exactly the two rows that are about
reporting and nothing else (2 failed, 2 here: the REPORTED row and the additive second-corpus row).
The flip record was driven on both of its legs, each reddening the flip row alone (1 failed, 1 here):
a date that is not a date, and a posture clause that stops naming the flip in the line an operator
reads. AND THE ADDITIVE CONTROL FOR THE REPORT, over the LIVE corpus rather than a fixture: adding a
spec that declares no behaviour to specs/ leaves this fragment GREEN and moves the reported count from
168 stood down to 169, so the addition is asserted to have applied rather than assumed.

ONE ROW HERE WAS WRITTEN WRONG FIRST AND THE F4 RUN CAUGHT IT, which is worth recording because
it is this item's own defect class. The template row read `FALSIFICATION_FIELD in TEMPLATE.md`,
and deleting the field from the template left it GREEN: the field name also appears in the
comment that explains the field. A row claiming to check that the template carries the field,
satisfied by prose about the field. It now requires a front-matter key line carrying a value.

THE WIRING IS REAL AND FOUR ROWS ASSERT IT, which is the opposite of what this paragraph used to
say (VELDO-0001 F1). It read "check_spec does not CALL this check", "the registration line belongs
in .veldo/validate.py, which is outside the footprint VELDO-0001 declares" and "NO row here
pretends the wiring exists", and all three were false where they stood. The registration is
`.veldo/validate.py:129`. The spec's footprint lists ".veldo/validate.py" as its FIRST entry, and
its rollback clause reads "Delete the check's registration in check_spec", which presupposes the
line exists. And FOUR rows below reach this check THROUGH V.check_spec - the fixture positive
control, the scalar row and the two empty-acceptance_criteria rows - so deleting the registration
reddens all four: reducing that call to check_observability alone was measured by the reviewer at
four failures, exactly those. `validate.py all` genuinely refuses. Behaviour was never affected;
the RECORD was the defect, and a reader auditing this item from its evidence would have concluded
the enforcement was inert. Those four rows are written as an EQUIVALENCE against
FD.FALSIFICATION_ENFORCED rather than against today's value of it, so the posture can flip without
a suite that reds on its own rule being enforced.

THE STAND-DOWN IS NOW REPORTED AND NOT ONLY RECORDED, which is the opposite of what this paragraph
used to say (VELDO-0001 F2). It read "nothing on an operator's path calls falsification_migration_line
and at `validate.py all` this repository's 168 stand-downs read exactly like a pass", and that was
true where it stood: the rows below proved RECORDING and an operator met nothing. The recorder now
prints ONE line per CORPUS per run, in the sibling release check's words, with its counts measured by
falsification_migration() where the line is printed. MEASURED at the surface the finding named:
`python3 .veldo/validate.py all 2>&1 | grep -ic 'falsif|stood down|stand-down'` was 0 and is 2, one
line for specs/ (168 stood down) and one for .veldo/examples (2), and the run stays exit 0.

WHAT THIS FRAGMENT STILL CANNOT ASSERT, stated rather than hidden. TWO CLAUSES, both recorded rather
than closed. The flip commit 01bcdf3 states the count three ways and no DATE, which AC3 asks its
message for (VELDO-0001 F6): amending it would rewrite history this tree shares, so the date is
recorded in FALSIFICATION_FLIP beside the posture, it reaches an operator inside the line above, and
the row named for F6 requires that record to stay complete - but no row here reads git, so the
MESSAGE itself is still unasserted by construction. And the posture is a module constant with no
per-repo override (VELDO-0001 F7), so an adopter who already declares behavior_bearing: true is
refused on arrival rather than given the reporting window AC3 describes for this repository; the
comment on FALSIFICATION_ENFORCED says so in those words, and the remedy is a contract change with
its own item rather than a line added here.
"""
import contextlib as _fd_ctx
import io as _fd_io
import re as _fd_re

# THE MODULE THE VALIDATOR ITSELF LOADED, not a second instance: validate.py binds its ONE
# parser and ONE reporter into this object at import time, so every refusal below is printed by
# the reporter the gate prints through and every front matter is read by the parser the contract
# is defined in terms of.
FD = V._VC


def _fd_spec(criteria, bb="true"):
    """One spec fixture whose ONLY defect can be the falsification rule.

    Every other front-matter field a spec needs is present and valid, because a fixture missing
    two things cannot tell which one a refusal came from. `criteria` is a list of (id, extra
    lines) pairs, where the extra lines are written verbatim under the criterion so a fixture can
    declare a malformed shape as an author would type it. `bb` is the behavior_bearing value, or
    None to omit the field entirely."""
    fm = ["---", "schema: veldo.spec/v1", "id: WARP-9601",
          "title: falsification fixture", "status: ready", "risk: standard - fixture",
          "owner: selftest", "lane: standalone"]
    if bb is not None:
        fm.append("behavior_bearing: %s" % bb)
    fm.append("acceptance_criteria:")
    for cid, lines in criteria:
        fm.append("  - id: %s" % cid)
        fm.append("    text: the fixture criterion states something observable.")
        fm.extend("    %s" % line for line in lines)
    fm += ["required_evidence: [unit]", "rollback: git revert", "---", "", "body", ""]
    return "\n".join(fm)


# A GENUINE declaration and the shapes that are not one. The genuine one is a real sentence
# naming a real mutation, because the accepting leg has to be satisfied by what an author would
# actually write, not by a string tuned to clear a floor.
_FD_GOOD = "falsified_by: delete the per-criterion loop and this fixture stops being refused"
_FD_GOOD2 = "falsified_by: remove the field from the template and this row must go red"


def _fd_check(path, **kw):
    """(errors, printed): the check's error count and EXACTLY what a reader sees.

    The printed half matters as much as the count. AC1's promise is that the refusal NAMES the
    criterion, which is a promise about the line on the page, and a message that is right in the
    predicate and lost on the way to the reporter would satisfy a count-only assertion."""
    buf = _fd_io.StringIO()
    with _fd_ctx.redirect_stdout(buf):
        errs = FD.check_falsification_declared(path, **kw)
    return errs, buf.getvalue()


def _fd_fm(text):
    """The fixture's front matter through the ONE parser, for the rows that drive the pure
    predicate rather than the file-reading check."""
    return V.parse_yamlish(_fd_re.match(r"^---\n(.*?)\n---", text, _fd_re.S).group(1))


def _fd_causes(text):
    """{criterion subject: cause} for one fixture, through the pure predicate. The cause is
    asserted as the module's own named constant, never as a message substring, so a reworded
    refusal does not redden a row about the taxonomy."""
    return {subject: cause for subject, cause, _msg in FD.falsification_problems(_fd_fm(text))}


# ---------------------------------------------------------------------------------------
# AC1. A BEHAVIOUR-BEARING CRITERION WITHOUT A DECLARED FALSIFICATION IS REFUSED, AND THE
# REFUSAL NAMES THE CRITERION.
#
# FALSIFIED BY (from the criterion itself): delete the per-criterion loop so the check only
# verifies that acceptance_criteria exists, and the three-criterion fixture below must stop
# being refused. NEGATIVE CONTROL: the same validator must still ACCEPT a fixture whose criteria
# all declare one.
# ---------------------------------------------------------------------------------------
_FD_BARE3 = _fd_spec([("AC1", []), ("AC2", []), ("AC3", [])])
_FD_ALL3 = _fd_spec([("AC1", [_FD_GOOD]), ("AC2", [_FD_GOOD2]),
                     ("AC3", ["falsified_by: make the stand-down unconditional and this row reds"])])
_FD_MIXED = _fd_spec([("AC1", [_FD_GOOD]), ("AC2", []), ("AC3", [])])

with tempfile.TemporaryDirectory() as _fd_d:
    _fd_bare3 = tmpfile(_fd_d, "bare3.md", _FD_BARE3)
    _fd_all3 = tmpfile(_fd_d, "all3.md", _FD_ALL3)
    _fd_mixed = tmpfile(_fd_d, "mixed.md", _FD_MIXED)

    # POSITIVE CONTROL FIRST, on the fixture builder itself: the fixtures are valid specs apart
    # from this rule, so every refusal below is attributable to the falsification field and not
    # to a fixture the validator would reject anyway.
    expect("VELDO-0001 fixture: both fixtures are otherwise-valid specs, so a refusal below is "
           "the falsification rule and nothing else",
           # BOUND TO THE POSTURE, not to today's value of it. These read `== 0` while the rule
           # only REPORTED; the flip to refusing made check_spec correctly return non-zero on the
           # non-compliant fixture, and a suite that reds on its own rule being enforced is a suite
           # asserting the migration never finishes. The compliant fixture must be clean either way.
           V.check_spec(_fd_all3) == 0
           and (V.check_spec(_fd_bare3) > 0 if FD.FALSIFICATION_ENFORCED
                else V.check_spec(_fd_bare3) == 0))

    _fd_errs, _fd_out = _fd_check(_fd_bare3, enforce=True)
    expect("VELDO-0001 AC1: a behaviour-bearing spec with three criteria and no falsified_by "
           "anywhere is refused ONCE PER CRITERION",
           _fd_errs == 3)
    expect("VELDO-0001 AC1: each refusal NAMES the criterion id and the field to add, on the page "
           "a reader sees",
           all(("criterion %s declares no %s" % (c, FD.FALSIFICATION_FIELD)) in _fd_out
               for c in ("AC1", "AC2", "AC3")))
    expect("VELDO-0001 AC1: the cause is the named MISSING cause for every one of them, and the "
           "count of refusals equals the count of problems the predicate found",
           _fd_causes(_FD_BARE3) == {"AC1": FD.FALSIFICATION_MISSING,
                                     "AC2": FD.FALSIFICATION_MISSING,
                                     "AC3": FD.FALSIFICATION_MISSING}
           and len(FD.falsification_problems(_fd_fm(_FD_BARE3))) == _fd_errs)
    # THE LEG THAT MATTERS. Same validator, same posture, same fixture shape: the refusal has to
    # be discriminating rather than a blanket rejection of every spec.
    _fd_errs_ok, _fd_out_ok = _fd_check(_fd_all3, enforce=True)
    expect("VELDO-0001 AC1 NEGATIVE CONTROL: the SAME validator in the SAME refusing posture "
           "accepts a fixture whose three criteria all declare a falsification, and prints "
           "nothing at all",
           _fd_errs_ok == 0 and _fd_out_ok == ""
           and FD.falsification_problems(_fd_fm(_FD_ALL3)) == [])
    # PER CRITERION, not per spec: one compliant criterion beside two bare ones refuses twice and
    # names only the two. A per-spec check would refuse once, or three times, and both would pass
    # a bare count assertion over the all-bare fixture above.
    _fd_errs_mix, _fd_out_mix = _fd_check(_fd_mixed, enforce=True)
    expect("VELDO-0001 AC1: the rule binds each criterion separately - a spec with one compliant "
           "criterion and two bare ones is refused exactly twice, and the compliant one is not "
           "named",
           _fd_errs_mix == 2 and "criterion AC2 " in _fd_out_mix and "criterion AC3 " in _fd_out_mix
           and "criterion AC1 " not in _fd_out_mix)
    # A criterion with no id of its own is still located, by position, because a refusal an author
    # cannot find is a refusal they route around.
    _FD_NOID = _fd_spec([("AC1", [])]).replace("  - id: AC1\n", "  - restated: x\n")
    _fd_noid_errs, _fd_noid_out = _fd_check(tmpfile(_fd_d, "noid.md", _FD_NOID), enforce=True)
    expect("VELDO-0001 AC1: a criterion carrying no id is refused and named by its POSITION "
           "rather than silently skipped",
           _fd_noid_errs == 1 and "criterion acceptance_criteria[1] declares no" in _fd_noid_out)
    # A behaviour-bearing spec whose acceptance_criteria is a SCALAR would otherwise be the one
    # free exemption: check_spec accepts it (the field is present) and no criterion exists to ask.
    _FD_SCALAR = _fd_spec([("AC1", [_FD_GOOD])])
    _FD_SCALAR = _fd_re.sub(r"acceptance_criteria:\n(  .*\n)+", "acceptance_criteria: yes\n",
                            _FD_SCALAR)
    expect("VELDO-0001 AC1: a behaviour-bearing spec whose acceptance_criteria is a scalar rather "
           "than a list is refused instead of being an exemption, and check_spec alone does NOT "
           "catch it",
           _fd_check(tmpfile(_fd_d, "scalar.md", _FD_SCALAR), enforce=True)[0] > 0
           and _fd_causes(_FD_SCALAR) == {"acceptance_criteria": FD.FALSIFICATION_UNREADABLE}
           and (V.check_spec(tmpfile(_fd_d, "scalar2.md", _FD_SCALAR)) > 0
                if FD.FALSIFICATION_ENFORCED
                else V.check_spec(tmpfile(_fd_d, "scalar2.md", _FD_SCALAR)) == 0))
    # THE OTHER FREE EXEMPTION, and it is reachable by an author in one keystroke: check_spec
    # accepts `acceptance_criteria: []` and a bare key, because the FIELD is present. Emptying the
    # field would then be the one way for a behaviour-bearing spec to be asked nothing. Measured
    # over this repository's 200 specs: zero carry that shape, so refusing it reddens nothing.
    for _fd_lbl, _fd_block in (("an empty list", "acceptance_criteria: []"),
                               ("a bare key", "acceptance_criteria:")):
        _FD_EMPTY = _fd_re.sub(r"acceptance_criteria:\n(  .*\n)+", _fd_block + "\n",
                               _fd_spec([("AC1", [_FD_GOOD])]))
        expect("VELDO-0001 AC1: %s in acceptance_criteria is refused rather than being asked "
               "nothing, and check_spec alone accepts it" % _fd_lbl,
               _fd_check(tmpfile(_fd_d, "empty.md", _FD_EMPTY), enforce=True)[0] == 1
               and _fd_causes(_FD_EMPTY) == {"acceptance_criteria": FD.FALSIFICATION_MISSING}
               and (V.check_spec(tmpfile(_fd_d, "empty2.md", _FD_EMPTY)) > 0
                    if FD.FALSIFICATION_ENFORCED
                    else V.check_spec(tmpfile(_fd_d, "empty2.md", _FD_EMPTY)) == 0))
    # The fourth refusal path: a spec that declares behaviour in front matter the ONE parser
    # cannot read. It is refused BY NAME rather than skipped, because a spec whose criteria cannot
    # be read is a spec whose falsifications cannot be checked.
    _FD_TABS = _fd_spec([("AC1", [_FD_GOOD])]).replace("  - id: AC1", "\t- id: AC1")
    _fd_tab_errs, _fd_tab_out = _fd_check(tmpfile(_fd_d, "tabs.md", _FD_TABS), enforce=True)
    expect("VELDO-0001 AC1: front matter outside the parser subset is refused by name, saying "
           "which field it could not read the criteria for",
           _fd_tab_errs == 1 and FD.FALSIFICATION_FIELD in _fd_tab_out
           and "outside the parser subset" in _fd_tab_out)
    expect("VELDO-0001 AC1 NEGATIVE CONTROL: the same fixture with the tab replaced by spaces is "
           "read and accepted, so the row above is the parser and not the fixture",
           _fd_check(tmpfile(_fd_d, "tabs-ok.md", _FD_TABS.replace("\t- id: AC1",
                                                                   "  - id: AC1")),
                     enforce=True) == (0, ""))

# ---------------------------------------------------------------------------------------
# AC2. A DECLARATION THAT SAYS NOTHING IS NOT A DECLARATION.
#
# FALSIFIED BY: accept any non-empty string, and a fixture declaring `falsified_by: n/a` must
# stop being refused. NEGATIVE CONTROL: a genuine one-sentence declaration must still be
# accepted, so the length rule cannot be satisfied only by padding.
# ---------------------------------------------------------------------------------------
# ONE TABLE, INPUT TO NAMED CAUSE, so the three causes are proven DISTINGUISHABLE rather than
# merely present. Each row is the value an author would type; the expected cause is the module's
# own constant.
_FD_VALUES = [
    ("n/a", FD.FALSIFICATION_EMPTY, "falsified_by: n/a"),
    ("padded n/a", FD.FALSIFICATION_EMPTY, 'falsified_by: "n/a                              "'),
    ("empty string", FD.FALSIFICATION_EMPTY, 'falsified_by: ""'),
    ("whitespace", FD.FALSIFICATION_EMPTY, 'falsified_by: "   "'),
    ("bare key", FD.FALSIFICATION_EMPTY, "falsified_by:"),
    ("under the character floor", FD.FALSIFICATION_EMPTY, "falsified_by: a b c d e"),
    ("under the word floor", FD.FALSIFICATION_EMPTY, "falsified_by: aaaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
    ("a list", FD.FALSIFICATION_UNREADABLE, "falsified_by: [delete the loop, and see]"),
    ("a mapping", FD.FALSIFICATION_UNREADABLE, "falsified_by: {change: the loop and watch it}"),
    ("a number", FD.FALSIFICATION_UNREADABLE, "falsified_by: 42"),
]
for _fd_label, _fd_cause, _fd_line in _FD_VALUES:
    _fd_txt = _fd_spec([("AC1", [_fd_line])])
    expect("VELDO-0001 AC2: %s is refused with the cause %s, distinct from the missing-field cause"
           % (_fd_label, _fd_cause),
           _fd_causes(_fd_txt) == {"AC1": _fd_cause} and _fd_cause != FD.FALSIFICATION_MISSING)
expect("VELDO-0001 AC2: the three causes are three DIFFERENT names, so a refusal tells an author "
       "which of them they hit",
       len({FD.FALSIFICATION_MISSING, FD.FALSIFICATION_EMPTY, FD.FALSIFICATION_UNREADABLE}) == 3)
# NEGATIVE CONTROL for the whole table: a genuine one-sentence declaration is accepted, and so is
# a folded one, which is the shape the one parser hands back with its marker still attached.
_FD_FOLDED = _fd_spec([("AC1", ["falsified_by: >",
                                "  drop the word floor and the padded fixture stops being",
                                "  refused"])])
expect("VELDO-0001 AC2 NEGATIVE CONTROL: a genuine one-sentence declaration is accepted, in both "
       "the inline and the folded form, so the floors cannot be what refuses everything",
       FD.falsification_problems(_fd_fm(_fd_spec([("AC1", [_FD_GOOD])]))) == []
       and FD.falsification_problems(_fd_fm(_FD_FOLDED)) == [])
expect("VELDO-0001 AC2: padding cannot satisfy the floors - the statement is measured with its "
       "whitespace collapsed, so a placeholder padded past the character floor still fails while "
       "the same floor is cleared by a real sentence",
       FD._falsification_statement("n/a" + " " * 80)[0] == FD.FALSIFICATION_EMPTY
       and len("n/a" + " " * 80) > FD.FALSIFICATION_MIN_CHARS
       and FD._falsification_statement(_FD_GOOD.split(": ", 1)[1])[0] is None)
expect("VELDO-0001 AC2: BOTH floors have teeth, proven by a value that clears one and fails the "
       "other in each direction",
       FD._falsification_statement("a b c d e f")[0] == FD.FALSIFICATION_EMPTY
       and FD._falsification_statement("x" * 60)[0] == FD.FALSIFICATION_EMPTY)
expect("VELDO-0001 AC2: a real boolean, which no author types but a caller can pass, is the "
       "unreadable cause rather than being coerced into a statement",
       FD._falsification_statement(True)[0] == FD.FALSIFICATION_UNREADABLE
       and FD._falsification_statement(None)[0] == FD.FALSIFICATION_EMPTY)
expect("VELDO-0001 AC2: there is no exemption keyword - the words a rule with an escape hatch "
       "would honour are refused like any other placeholder",
       all(FD._falsification_statement(w)[0] == FD.FALSIFICATION_EMPTY
           for w in ("n/a", "N/A", "none", "TODO", "exempt", "-", "see above")))

# ---------------------------------------------------------------------------------------
# AC3. SPECS THAT DECLARE NO BEHAVIOUR ARE UNAFFECTED, AND SO IS A REPOSITORY THAT HAS NOT
# ADOPTED THIS YET.
#
# FALSIFIED BY: make the check ignore behavior_bearing entirely, and a fixture that declares no
# behaviour while carrying bare criteria must start being refused. NEGATIVE CONTROL: with the
# stand-down in place, a behaviour-bearing fixture missing a falsification must still be refused.
# ---------------------------------------------------------------------------------------
_FD_NO_BB = _fd_spec([("AC1", []), ("AC2", [])], bb=None)
_FD_BB_FALSE = _fd_spec([("AC1", []), ("AC2", [])], bb="false")

with tempfile.TemporaryDirectory() as _fd_d2:
    del FD.FALSIFICATION_STANDDOWNS[:]      # the registry is the record; measure a clean one
    FD.FALSIFICATION_REPORTED_CORPORA.clear()   # and a run that has reported no corpus yet
    _fd_nobb = tmpfile(_fd_d2, "nobb.md", _FD_NO_BB)
    _fd_false = tmpfile(_fd_d2, "false.md", _FD_BB_FALSE)
    _fd_gated = tmpfile(_fd_d2, "gated.md", _FD_BARE3)
    _fd_n1, _fd_o1 = _fd_check(_fd_nobb, enforce=True)
    _fd_n2, _fd_o2 = _fd_check(_fd_false, enforce=True)
    _fd_n3, _fd_o3 = _fd_check(_fd_gated, enforce=True)
    expect("VELDO-0001 AC3: a spec that declares no behavior_bearing field carries bare criteria "
           "without being REFUSED, in the REFUSING posture, and nothing on the page names a "
           "criterion of it or reports a problem in it",
           _fd_n1 == 0 and "criterion AC1 " not in _fd_o1
           and "MIGRATION REPORT" not in _fd_o1)
    expect("VELDO-0001 AC3: and so does a spec that declares behavior_bearing: false, which prints "
           "NOTHING AT ALL because its corpus has already been reported in this run - the report is "
           "one line per corpus, never one per spec, or 168 lines would bury the signal",
           _fd_n2 == 0 and _fd_o2 == "")
    # THE STAND-DOWN IS REPORTED AND NOT ONLY RECORDED (VELDO-0001 F2). The rows below prove the
    # RECORD; this one proves an operator MEETS it, in the sibling release check's words, through
    # the same reporter every refusal prints through. The count is asserted as the READER's over
    # this same corpus AND as a known number for a corpus this fragment built, so a reader that
    # returned zero for everything could not satisfy it.
    _FD_SD_HERE = FD.falsification_migration(specs_dir=_fd_d2)["stood_down"]
    expect("VELDO-0001 AC3: the stand-down is REPORTED where an operator stands, naming the field, "
           "the corpus and the count MEASURED by the reader at the moment it printed, in the words "
           "the sibling release check uses (VELDO-0001 F2)",
           _fd_o1.count("\n") == 1
           and "falsified_by STANDS DOWN" in _fd_o1
           and "recorded rather than passed" in _fd_o1
           and str(_fd_d2) in _fd_o1
           and _FD_SD_HERE == 2
           and ("%d stood down" % _FD_SD_HERE) in _fd_o1
           and "Posture: %s" % ("REFUSING" if FD.FALSIFICATION_ENFORCED else "REPORTING")
           in _fd_o1)
    # NEGATIVE CONTROL: the stand-down is not what makes every case pass. The same call, the same
    # posture, one field different.
    expect("VELDO-0001 AC3 NEGATIVE CONTROL: in the SAME run a behaviour-bearing fixture missing "
           "its falsifications is still refused, so the stand-down is the declaration and not the "
           "check refusing nothing",
           _fd_n3 == 3 and "criterion AC1 " in _fd_o3)
    # The stand-down is RECORDED rather than passed: a reader can tell a spec that was CHECKED
    # from one the rule never asked anything of, and each record names its own reason.
    _fd_sd = dict((Path(p).name, why) for p, why in FD.falsification_standdowns())
    expect("VELDO-0001 AC3: each stand-down is RECORDED with the reason it stood down, and the "
           "two reasons are DIFFERENT - an absent field and an explicit false are not the same "
           "fact",
           sorted(_fd_sd) == ["false.md", "nobb.md"]
           and "declares no behavior_bearing field" in _fd_sd["nobb.md"]
           and "behavior_bearing: false" in _fd_sd["false.md"]
           and _fd_sd["nobb.md"] != _fd_sd["false.md"])
    expect("VELDO-0001 AC3: the gated spec is NOT in the stand-down registry, so the registry "
           "records the specs the rule stood down for rather than every spec it saw",
           "gated.md" not in _fd_sd)
    # ADDITIVE CONTROL for the report, and it is what makes the number a MEASUREMENT: a SECOND
    # corpus appearing in the same run reports its OWN line with its OWN count, three where the
    # first said two, while the first corpus is not reported a second time. An assertion that the
    # line merely contains a number would survive a hardcoded one; this cannot.
    with tempfile.TemporaryDirectory() as _fd_d2b:
        _fd_b1 = tmpfile(_fd_d2b, "nobb1.md", _FD_NO_BB)
        _fd_b2 = tmpfile(_fd_d2b, "nobb2.md", _FD_NO_BB)
        tmpfile(_fd_d2b, "nobb3.md", _FD_NO_BB)
        _fd_n4, _fd_o4 = _fd_check(_fd_b1, enforce=True)
        _fd_n5, _fd_o5 = _fd_check(_fd_b2, enforce=True)
        _fd_n6, _fd_o6 = _fd_check(_fd_nobb, enforce=True)
        expect("VELDO-0001 AC3 NEGATIVE CONTROL, ADDITIVE: a second corpus in the same run reports "
               "its own count (3, where the first corpus reported 2), the second stand-down inside "
               "it prints nothing, and the already-reported first corpus stays silent",
               (_fd_n4, _fd_n5, _fd_n6) == (0, 0, 0)
               and _fd_o4.count("\n") == 1 and str(_fd_d2b) in _fd_o4
               and "3 stood down" in _fd_o4 and "2 stood down" not in _fd_o4
               and _fd_o5 == "" and _fd_o6 == ""
               and FD.falsification_migration(specs_dir=_fd_d2b)["stood_down"] == 3)
    expect("VELDO-0001 AC3: behaviour-bearing has ONE definition in this repository - the check "
           "reads it through observability.behavior_bearing, the same reader the diagnosability "
           "gate uses, in all three states",
           FD.falsification_gated(_fd_fm(_FD_BARE3))[0] is True
           and FD.falsification_gated(_fd_fm(_FD_NO_BB))[0] is False
           and FD.falsification_gated(_fd_fm(_FD_BB_FALSE))[0] is False
           and FD._observability_module().behavior_bearing(_fd_fm(_FD_BARE3)) is True)

    # THE MIGRATION POSTURE. The same fixture, the same problems: refused when enforcing, and
    # REPORTED with the posture named in the line when not, which is what makes landing this
    # change green in a repository whose specs have not adopted it.
    _fd_r_errs, _fd_r_out = _fd_check(_fd_gated, enforce=False)
    expect("VELDO-0001 AC3: in the reporting posture the SAME three problems are printed and the "
           "count is 0, the line says it is not a refusal, and it still names every criterion",
           _fd_r_errs == 0 and "MIGRATION REPORT, not a refusal yet" in _fd_r_out
           and all(c in _fd_r_out for c in ("AC1", "AC2", "AC3"))
           and _fd_r_out.count("\n") == 1)
    expect("VELDO-0001 AC3 NEGATIVE CONTROL: a compliant spec prints no report line either, so "
           "the report is the problems and not a line that always prints",
           _fd_check(tmpfile(_fd_d2, "ok.md", _FD_ALL3), enforce=False) == (0, ""))
    # The DECLARED posture is what an unqualified call uses. Asserted as an equivalence rather
    # than by pinning today's value, so flipping the constant is a decision that does not have to
    # redden this row - and a call that ignored the constant would fail on one side of it.
    expect("VELDO-0001 AC3: an unqualified call follows the DECLARED posture "
           "(FALSIFICATION_ENFORCED), and the two postures do not agree on this fixture, so the "
           "row cannot pass by them being the same",
           _fd_check(_fd_gated)[0] == _fd_check(_fd_gated, enforce=FD.FALSIFICATION_ENFORCED)[0]
           and _fd_check(_fd_gated, enforce=True)[0] != _fd_check(_fd_gated, enforce=False)[0])
    # THE REGISTRATION SHAPE. check_spec calls its sibling spec checks as (path, repo_root); this
    # pins that the same call works here, so the one line that registers this check cannot be
    # wrong when it lands. It does NOT assert the registration exists, because it does not.
    expect("VELDO-0001 AC3: the check accepts the (path, repo_root) call shape check_spec uses "
           "for its sibling spec checks, and repo_root changes nothing, because this rule is a "
           "property of the spec alone",
           _fd_check(_fd_gated, repo_root=str(ROOT), enforce=True)[0]
           == _fd_check(_fd_gated, repo_root=str(Path(_fd_d2)), enforce=True)[0] == 3)

# THE MIGRATION MEASUREMENT, over a SEEDED corpus first, because a count asserted only over this
# repository cannot tell a right measurement from one that missed half the files. Five specs, one
# of each shape that exists, plus the two filenames every corpus reader must skip.
with tempfile.TemporaryDirectory() as _fd_d3:
    _fd_sdir = Path(_fd_d3) / "specs"
    _fd_sdir.mkdir()
    (_fd_sdir / "gated-bad.md").write_text(_FD_BARE3)
    (_fd_sdir / "gated-good.md").write_text(_FD_ALL3)
    (_fd_sdir / "not-bearing.md").write_text(_FD_BB_FALSE)
    (_fd_sdir / "no-field.md").write_text(_FD_NO_BB)
    (_fd_sdir / "broken.md").write_text("no front matter at all\n")
    (_fd_sdir / "TEMPLATE.md").write_text(_FD_BARE3)
    (_fd_sdir / "index.md").write_text(_FD_BARE3)
    _FD_SEED = FD.falsification_migration(specs_dir=_fd_sdir)
    expect("VELDO-0001 AC3: the migration measurement over a seeded corpus counts every shape "
           "separately and skips the template and the derived index",
           (_FD_SEED["specs"], _FD_SEED["behaviour_bearing"], _FD_SEED["compliant"],
            _FD_SEED["would_refuse"], _FD_SEED["criteria_would_refuse"], _FD_SEED["stood_down"])
           == (5, 2, 1, 1, 3, 3)
           and _FD_SEED["specs_would_refuse"] == ["gated-bad.md"]
           and _FD_SEED["by_cause"] == {FD.FALSIFICATION_MISSING: 3})
    (_fd_sdir / "gated-bad.md").write_text(_FD_ALL3)      # migrate the one offender, in place
    _FD_SEED2 = FD.falsification_migration(specs_dir=_fd_sdir)
    expect("VELDO-0001 AC3 NEGATIVE CONTROL: bring the one non-compliant spec into compliance and "
           "the measurement says so, so the count above is a measurement rather than a constant",
           (_FD_SEED2["specs"], _FD_SEED2["behaviour_bearing"], _FD_SEED2["compliant"],
            _FD_SEED2["would_refuse"], _FD_SEED2["criteria_would_refuse"])
           == (5, 2, 2, 0, 0)
           and _FD_SEED2["by_cause"] == {} and _FD_SEED2["specs_would_refuse"] == []
           and _FD_SEED2["stood_down"] == _FD_SEED["stood_down"] == 3)
    expect("VELDO-0001 AC3: an absent specs directory measures nothing rather than raising, so a "
           "repository that has no corpus is unaffected",
           FD.falsification_migration(specs_dir=Path(_fd_d3) / "absent")["specs"] == 0)

# LIVE, over this repository's real corpus. CONSERVATION and non-vacuity rather than a pinned
# count: pinning today's 32 would redden the gate the first time somebody migrates one spec,
# which is the outcome this item wants. The pinned number belongs in the flip commit's message.
_FD_LIVE = FD.falsification_migration()
expect("VELDO-0001 AC3 LIVE: every spec in this repository is either asked for a falsification "
       "or stood down, and every asked spec either complies or would be refused - the two "
       "partitions are exact, so no spec falls between them",
       _FD_LIVE["behaviour_bearing"] + _FD_LIVE["stood_down"] == _FD_LIVE["specs"]
       and _FD_LIVE["compliant"] + _FD_LIVE["would_refuse"] == _FD_LIVE["behaviour_bearing"])
expect("VELDO-0001 AC3 LIVE: and that is not vacuous - this repository really does carry "
       "behaviour-bearing specs and really does carry specs the rule stands down for",
       _FD_LIVE["specs"] > 100 and _FD_LIVE["behaviour_bearing"] > 0
       and _FD_LIVE["stood_down"] > 0
       and len(_FD_LIVE["specs_would_refuse"]) == _FD_LIVE["would_refuse"])
expect("VELDO-0001 AC3 LIVE: the migration line states the count and the posture it was measured "
       "under, because the same numbers mean different things on either side of the flip",
       ("%d would be refused" % _FD_LIVE["would_refuse"])
       in FD.falsification_migration_line(_FD_LIVE)
       and ("REFUSING" if FD.FALSIFICATION_ENFORCED else "REPORTING")
       in FD.falsification_migration_line(_FD_LIVE))
# THE FLIP RECORD, ASSERTED RATHER THAN TRUSTED. AC3 requires the flip to be a separate commit whose
# message states the DATE and the count. 01bcdf3 is that commit and it states the count three ways and
# no date (VELDO-0001 F6); amending a commit this tree shares is not available, so the date is recorded
# in the module beside the posture and REACHES an operator through the stand-down line. Nothing asserted
# that record before this row, which is what made the one clause living in git history unevidenced: it
# requires a commit id, an ISO date, and a posture that AGREES with FALSIFICATION_ENFORCED, so flipping
# the constant without recording when cannot stay green.
_FD_FLIP = FD.FALSIFICATION_FLIP
_FD_FLIP_LINE = FD.falsification_migration_line(_FD_LIVE)
expect("VELDO-0001 AC3: the FLIP RECORD names a commit, an ISO date and a posture that AGREES with "
       "FALSIFICATION_ENFORCED, and both the date and the commit reach the line an operator reads, "
       "which is where the clause the flip commit's message omits is met (VELDO-0001 F6)",
       bool(_fd_re.match(r"^[0-9a-f]{7,40}$", str(_FD_FLIP.get("commit"))))
       and bool(_fd_re.match(r"^\d{4}-\d{2}-\d{2}$", str(_FD_FLIP.get("date"))))
       and _FD_FLIP.get("posture") in ("REFUSING", "REPORTING")
       and (_FD_FLIP["posture"] == "REFUSING") == (FD.FALSIFICATION_ENFORCED is True)
       and _FD_FLIP["date"] in _FD_FLIP_LINE and _FD_FLIP["commit"] in _FD_FLIP_LINE)

# ---------------------------------------------------------------------------------------
# AC4. THE TEMPLATE AND THE SPINE DOCUMENT ASK FOR IT.
#
# FALSIFIED BY: remove the field from the template, and the assertion that reads the template for
# it must go red. NEGATIVE CONTROL: the assertion must fail if it is looking for a string the
# template never contained, so it is pinned to the field name the validator actually enforces
# rather than to a spelling nobody uses.
# ---------------------------------------------------------------------------------------
_FD_TPL = (ROOT / "engine/specs/TEMPLATE.md").read_text()
_FD_METHOD = (ROOT / "docs/method.md").read_text()
# PINNED TO A DECLARATION, NOT TO THE WORD (see the docstring's note on this row): a substring
# test was satisfied by the comment that EXPLAINS the field, so it survived the field's deletion.
# This requires a front-matter KEY LINE CARRYING A VALUE.
_FD_TPL_DECL = _fd_re.search(r"(?m)^ *%s: *\S" % FD.FALSIFICATION_FIELD, _FD_TPL)
expect("VELDO-0001 AC4: the spec template DECLARES the field as a front-matter key carrying a "
       "value, and explains in one line what belongs in it, pinned to FALSIFICATION_FIELD - the "
       "name the validator ENFORCES - rather than to a spelling of it",
       _FD_TPL_DECL is not None and FD.FALSIFICATION_FIELD == "falsified_by"
       and "negative control" in _FD_TPL.lower())
expect("VELDO-0001 AC4 NEGATIVE CONTROL: plausible spellings the template never contained are "
       "absent, so the row above is not 'some string is present in a long file'",
       not any(s in _FD_TPL for s in ("falsifiable_by", "falsification_by", "falsified-by",
                                      "negative_control:")))
# STRUCTURAL, not a substring: the field is a real KEY on a real criterion when the template is
# read by the ONE parser, so a mention in a comment could not satisfy this.
_FD_TPL_FM = _fd_fm(_FD_TPL)
expect("VELDO-0001 AC4: the field is a real key on every criterion of the template when the "
       "template is parsed by the one front-matter parser, not a word in a comment",
       isinstance(_FD_TPL_FM.get("acceptance_criteria"), list)
       and _FD_TPL_FM["acceptance_criteria"]
       and all(FD.FALSIFICATION_FIELD in c for c in _FD_TPL_FM["acceptance_criteria"]))
# THE TEMPLATE IS BOUND TO THE VALIDATOR, in both directions: a spec written from the template
# passes the check, and the same spec with the template's field removed is refused. A template
# prompting for a field the validator does not enforce would pass every row above.
with tempfile.TemporaryDirectory() as _fd_d4:
    _fd_from_tpl = _FD_TPL.replace("# behavior_bearing: true", "behavior_bearing: true")
    _fd_tpl_spec = tmpfile(_fd_d4, "from-template.md", _fd_from_tpl)
    _fd_stripped = tmpfile(_fd_d4, "stripped.md", _fd_re.sub(
        r"(?m)^ *%s:.*\n" % FD.FALSIFICATION_FIELD, "", _fd_from_tpl))
    expect("VELDO-0001 AC4: a behaviour-bearing spec written FROM the template satisfies the "
           "check, so the field the template asks for is the field the validator enforces",
           _fd_check(_fd_tpl_spec, enforce=True) == (0, ""))
    expect("VELDO-0001 AC4 NEGATIVE CONTROL: the same spec with the template's field deleted is "
           "refused, so the row above is the field and not the template being accepted for other "
           "reasons",
           _fd_check(_fd_stripped, enforce=True)[0] == 1)
def _fd_method_states_the_rule(text):
    """The property the spine document must have, as ONE predicate, so the control below drives
    the SAME predicate the row above passes rather than a paraphrase of it. Pinned to
    FALSIFICATION_FIELD, the name the validator ENFORCES, rather than to a spelling of it."""
    return (FD.FALSIFICATION_FIELD in text
            and "negative control" in text.lower()
            and "declaring its own falsification" in text)


expect("VELDO-0001 AC4: the spine document states the rule where it defines a specification, "
       "naming both the field and the negative control - MEASURED at zero occurrences of "
       "'negative control' in this file before this item",
       _fd_method_states_the_rule(_FD_METHOD))
# WHY THIS CONTROL IS CONSTRUCTED RATHER THAN AN ABSENCE PIN OVER LIVE PROSE. Found by the
# independent review of VELDO-0001 (F8). This row used to assert that docs/method.md - 1503 lines
# of prose, edited by every item that touches the method - contains NEITHER "falsifiable_by" NOR
# "falsification_by". The intent was right and the mechanism was the one this ledger refuses
# (findings 46 and 51): an assertion over live text whose required answer is an ABSENCE reddens a
# required gate on a benign edit, and the first author who documents the misspelling in order to
# warn against it turns it red. The property the pin stood in for is that the row above
# DISCRIMINATES - it is satisfied by the enforced name and by nothing else - so that is what is
# asserted, over a document CONSTRUCTED to carry the defect. Growth in the real document cannot
# reach this row, and the mutation is asserted to have APPLIED so the control cannot pass by the
# rename having done nothing.
_FD_METHOD_MISSPELLED = _FD_METHOD.replace(FD.FALSIFICATION_FIELD, "falsifiable_by")
expect("VELDO-0001 AC4 NEGATIVE CONTROL, CONSTRUCTED: the row above is pinned to the ENFORCED "
       "field name and satisfied by no other spelling - rename the field to `falsifiable_by` "
       "throughout a copy of the spine document and the SAME predicate goes false, while the real "
       "document is never required to be free of a string a future author may legitimately write",
       _FD_METHOD_MISSPELLED != _FD_METHOD
       and "falsifiable_by" in _FD_METHOD_MISSPELLED
       and not _fd_method_states_the_rule(_FD_METHOD_MISSPELLED))
# WHAT AN ADOPTER INSTALLS IS WHAT THIS REPOSITORY RUNS: the check ships in engine/ and the two
# copies are byte-identical. Nine estimation modules once shipped into engine/ with nobody
# comparing them, and a review inverted one of them with the gate green.
expect("VELDO-0001 AC4: the checked module and the copy /veldo:init lays down are byte-identical, "
       "so the rule an adopter installs is the rule this repository runs",
       (ROOT / ".veldo/validate_checks.py").read_bytes()
       == (ROOT / "engine/.veldo/validate_checks.py").read_bytes())

# EVERY TEMPLATE AN AUTHOR IS POINTED AT MUST CARRY THE PROMPT, AND THIS REPOSITORY'S OWN DID NOT.
# Found by the independent review of VELDO-0001 (F3). The rule shipped into the adopter copy at
# engine/specs/TEMPLATE.md and NOT into specs/TEMPLATE.md, which is the file README.md tells an
# author here to copy, and which additionally told them in writing that "Nothing checks this" after
# validate.py had begun refusing it. So the rule survived locally only where somebody remembered
# it, which is the exact failure AC4's own rationale names.
#
# WHY THIS IS A PROPERTY CHECK AND NOT A SYNC CHECK, stated because the obvious answer is wrong:
# scripts/check_template_sync.sh excepts specs/TEMPLATE.md PERMANENTLY as per-repo, and rightly so,
# because the two files legitimately differ - the local one carries the four-things block that the
# shipped one does not. Byte-identity is therefore the wrong assertion and would have to be waived
# forever, which is how this diverged unseen. What is asserted instead is the PROPERTY both copies
# must have, over every template the repository offers an author, DERIVED by glob rather than
# hand-listed so a third template cannot arrive unchecked.
_fd_templates = sorted(list((ROOT / "specs").glob("TEMPLATE*.md"))
                       + list((ROOT / "engine/specs").glob("TEMPLATE*.md")))
_fd_tpl_text = {str(p.relative_to(ROOT)): p.read_text() for p in _fd_templates}


def _fd_prompts_field(text, field):
    """A KEY on its own line, never the word ANYWHERE in the text. This distinction is the whole
    reason this helper exists rather than an `in` test: the first version of the row below used
    `field in text` and stayed GREEN when the field was deleted from specs/TEMPLATE.md, because the
    explanatory comment above it still contains the word. That is the same defect VELDO-0010 F1
    names - a substring scan used to prove a presence - reproduced here while fixing it, and caught
    only by driving the mutation. A commented-out key does not count either: an author copying the
    template must find a line they fill in, not a line they first have to uncomment."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped.startswith(field + ":"):
            return True
    return False


expect("VELDO-0001 AC4: EVERY spec template this repository offers an author prompts for the "
       "falsification field AS A KEY ON ITS OWN LINE, uncommented, derived by glob over specs/ and "
       "engine/specs/ rather than hand-listed, and the set is non-empty so an empty glob cannot "
       "satisfy it. A MENTION IN A COMMENT DOES NOT COUNT, which is not a detail: the first "
       "version of this row tested `field in text` and stayed green with the field deleted, "
       "because the comment explaining the field still contains its name. MEASURED BEFORE THE "
       "FIX: specs/TEMPLATE.md carried neither this field nor behavior_bearing, "
       "engine/specs/TEMPLATE-standing.md carried neither, engine/specs/TEMPLATE.md carried both, "
       "and no assertion in this repository read either local copy at all",
       bool(_fd_tpl_text)
       and all(_fd_prompts_field(_t, FD.FALSIFICATION_FIELD)
               for _t in _fd_tpl_text.values()))
expect("VELDO-0001 AC4: every one of those templates also names behavior_bearing, because "
       "falsified_by is required only on a behaviour-bearing spec and a template that prompts for "
       "the field without naming the flag that makes it mandatory prompts for it in the one case "
       "it is not needed. Named in a comment IS enough here and deliberately so, because the flag "
       "is optional by design and a template that declared it live would force every spec written "
       "from it to be behaviour-bearing",
       bool(_fd_tpl_text)
       and all("behavior_bearing" in _t for _t in _fd_tpl_text.values()))
expect("VELDO-0001 AC4 NEGATIVE CONTROL, ADDITIVE: a template ADDED to the set that carries the "
       "field ONLY inside a comment is refused, so the rows above hold over the set as it grows "
       "and the comment-versus-key distinction is asserted rather than described",
       (lambda _added: not all(
           _fd_prompts_field(_t, FD.FALSIFICATION_FIELD) for _t in dict(
               _fd_tpl_text, **{"specs/TEMPLATE-probe.md": _added}).values()))
       ("---\nid: WARP-9999\nbehavior_bearing: true\nacceptance_criteria:\n  - id: AC1\n"
        "    text: no prompt here\n    # falsified_by: mentioned but not offered\n---\n"))
# A SPEC WRITTEN FROM THE LOCAL TEMPLATE SATISFIES THE ENFORCED CHECK, which is the behavioural
# half: the row above proves the prompt is present, this proves the prompt is CORRECT. Same drive
# as the engine-copy row earlier in this fragment, run against the copy an author here starts from.
with tempfile.TemporaryDirectory() as _fd_d5:
    _fd_local = (ROOT / "specs/TEMPLATE.md").read_text().replace(
        "# behavior_bearing: true", "behavior_bearing: true")
    _fd_local_spec = tmpfile(_fd_d5, "from-local-template.md", _fd_local)
    _fd_local_stripped = tmpfile(_fd_d5, "from-local-stripped.md", _fd_re.sub(
        r"(?m)^ *%s:.*\n" % FD.FALSIFICATION_FIELD, "", _fd_local))
    expect("VELDO-0001 AC4: a behaviour-bearing spec written from THIS REPOSITORY'S OWN template "
           "satisfies the check, so the field the local template asks for is the field the "
           "validator enforces and not a near-miss spelling",
           _fd_check(_fd_local_spec, enforce=True) == (0, ""))
    expect("VELDO-0001 AC4 NEGATIVE CONTROL: the same spec with that field deleted is REFUSED, so "
           "the row above is the field doing the work rather than the template being accepted for "
           "some other reason",
           _fd_check(_fd_local_stripped, enforce=True)[0] == 1)

del _fd_ctx, _fd_io, _fd_re
