"""VELDO-0002: what is done, what nobody concluded, and what is queued.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, which always
runs, so its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 19_veldo_0002_work_state

WHAT IS UNDER TEST. .veldo/work_state.py, driven DIRECTLY: it is a reader that writes nothing and
gates nothing, so there is no wrapper to go through and no registration to wait for. It is loaded
once, by path, the way every organ in that directory is loaded.

EVERY FIXTURE IS A REAL TREE ON DISK. The reader's whole job is to answer over a tree that may be
broken, so a fixture built from in-memory dicts would test the wrong thing. Each row builds specs,
proof bundles and run folders as FILES and points the reader at them.

BOTH DIRECTIONS, EVERYWHERE. The product of this item is a PARTITION, and a partition asserted from
one side is indistinguishable from a reader that puts everything in one bucket. So every row that
asserts an item lands in one state also asserts a sibling fixture, differing in exactly one file,
lands in a DIFFERENT one.
"""
import os as _ws_os
import re as _ws_re
import time as _ws_time

WS = V._VC._organ("work_state", ROOT / ".veldo" / "work_state.py")


def _ws_block(label, fn):
    """Run one criterion's block, and red a NAMED row if it raises instead of losing every row
    below it. The house pattern (18_veldo_0011's _rc_block): a raise at fragment scope takes the
    rest of the fragment with it, which is how a mutation that DELETES coverage passes as a
    shorter run rather than a red one. MEASURED, not assumed: three of this item's five declared
    falsifications raise rather than return a wrong answer, and before this wrapper they produced
    a run with no summary line at all."""
    try:
        fn()
    except Exception as _ws_e:                   # noqa: BLE001 - a raise must RED a row, never skip
        expect("VELDO-0002 %s: the block ran to completion rather than raising (%r)"
               % (label, _ws_e), False)


def _ws_tree(d, specs=(), bundles=(), runs=(), raw=()):
    """Build a tree: specs as front-matter files, bundles as proof artifacts, runs as run folders.

    bundles entries are (spec_id, files). files is a tuple of names, in which case every artifact
    RECORDS A PASSING VERDICT, or a mapping of name -> the verdict value that artifact records,
    where None writes no verdict field at all. Both shapes exist because DONE reads the verdict's
    BYTES: a row needs to build a bundle that is half written (a manifest with no verdict), one
    whose verdict records a REJECTION, and one where a later round records a pass.
    raw entries are (spec_id, name, text) written verbatim, for bytes that are not JSON at all.
    runs entries are (run_id, spec_id, status, heartbeat_age_seconds_or_None).
    """
    base = Path(d)
    sdir = base / "specs"
    sdir.mkdir(parents=True, exist_ok=True)
    for sid, status in specs:
        (sdir / ("%s-fixture.md" % sid)).write_text(
            "---\nschema: veldo.spec/v1\nid: %s\ntitle: fixture\nstatus: %s\n---\n" % (sid, status))
    for sid, files in bundles:
        bdir = base / "proof" / sid
        bdir.mkdir(parents=True, exist_ok=True)
        named = files if isinstance(files, dict) else dict.fromkeys(files, _WS_PASS)
        for name, verdict in named.items():
            body = {"schema": "fixture", "spec_id": sid}
            if verdict is not None:
                body["verdict"] = verdict
            (bdir / name).write_text(json.dumps(body))
    for sid, name, text in raw:
        bdir = base / "proof" / sid
        bdir.mkdir(parents=True, exist_ok=True)
        (bdir / name).write_text(text)
    rroot = base / "runsroot"
    if runs:
        rroot.mkdir(parents=True, exist_ok=True)
    for run_id, sid, status, age in runs:
        rd = rroot / run_id
        rd.mkdir(parents=True, exist_ok=True)
        (rd / "meta.json").write_text(json.dumps(
            {"run_id": run_id, "spec_id": sid, "started_at": "2026-08-12T02:00:00Z",
             "pid": 4242, "head": "cafef00d"}))
        state = {"run_id": run_id, "spec_id": sid, "status": status, "phase": "build",
                 "question": None, "updated_at": "2026-08-12T02:00:00Z"}
        if age is not None:
            stamp = _ws_time.gmtime(_ws_time.time() - age)
            state["heartbeat_at"] = _ws_time.strftime("%Y-%m-%dT%H:%M:%SZ", stamp)
        (rd / "state.json").write_text(json.dumps(state))
    return str(rroot)


def _ws_report(specs=(), bundles=(), runs=(), raw=(), with_registry=True):
    """One report over a fresh tree. Returns (report, lines)."""
    with tempfile.TemporaryDirectory() as d:
        rroot = _ws_tree(d, specs, bundles, runs, raw)
        if not with_registry:
            rroot = _ws_os.path.join(d, "no-registry-here")
        rep = WS.work_report(root=Path(d), runs_root=rroot)
        return rep, WS.report_lines(rep)


# THE VERDICT VALUES THE FIXTURES RECORD, taken from the two modules that own the vocabulary
# rather than spelled here as lore: the passing set from the module work_state itself delegates
# to, and the rejecting value from validate's declared vocabulary MINUS that passing set. The row
# in _ws_ac1_recorded_verdict asserts both are legal and that the rejecting one is genuinely not passing, so a
# fixture cannot pass by recording a word that means nothing to this repository.
_WS_PASS = sorted(WS.passing_verdicts())[0]
_WS_FAIL = sorted(set(V.VERDICTS) - set(WS.passing_verdicts()))[0]

_WS_FULL = ("manifest.json", "verdict.json")

# The rename the AC5 substitution fixture applies to every corpus pattern verdict_corpus declares.
_WS_RENAME_PREFIX = "substituted-"


def _ws_substituted_corpus(d):
    """A tree whose .veldo/verdict_corpus.py declares RENAMED corpus patterns, plus byte-identical
    copies of the organs work_state loads. Returns (the substituted module, how many declarations
    were rewritten).

    WHY A SUBSTITUTION AND NOT AN EQUALITY. "The reader takes its patterns from that module" is a
    claim about DELEGATION, and value equality between two reads of the same constants cannot
    detect a hand-kept copy on the day it is written, which is the day it is written correctly.
    Substituting the module gives delegation an observable consequence.

    THE RENAME IS DERIVED, never spelled: every `NAME_PATTERN = "value"` declaration line in the
    real module is rewritten to carry the prefix, so this fixture does not contain the values this
    repository happens to use today either. Whatever FOLLOWS the value on that line is preserved,
    because a declaration carrying a trailing comment is still a declaration - measured, not
    imagined: an additive control that added a fifth pattern WITH a comment reddened the
    applied-check below while this pattern was anchored at the end of the line."""
    vdir = Path(d) / ".veldo"
    vdir.mkdir(parents=True, exist_ok=True)
    src = (ROOT / ".veldo" / "verdict_corpus.py").read_text()
    renamed, n = _ws_re.subn(r'(?m)^([A-Z_]*%s) = "([^"]+)"(.*)$' % WS.CORPUS_PATTERN_SUFFIX,
                             r'\1 = "%s\2"\3' % _WS_RENAME_PREFIX, src)
    (vdir / "verdict_corpus.py").write_text(renamed)
    for name in ("work_state.py", "runlog.py", "executor.py"):
        (vdir / name).write_bytes((ROOT / ".veldo" / name).read_bytes())
    return V._VC._organ("verdict_corpus_substituted", vdir / "verdict_corpus.py"), n

# ---------------------------------------------------------------------------------------
# AC1. DONE IS DERIVED FROM THE ARTIFACTS, NEVER FROM WHAT A RUN SAID ABOUT ITSELF.
#
# FALSIFIED BY: delete the artifact half of the partition so DONE is read from the run registry's
# status field, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _ws_ac1():
    _WS_LIED, _ = _ws_report(
        specs=[("WARP-9001", "ready")],
        runs=[("run-lied", "WARP-9001", "done", 5)])
    expect("VELDO-0002 AC1: a run recording status DONE for a spec with NO proof bundle is reported "
           "UNCONCLUDED, not done - a process that announced its own success and left nothing behind is "
           "the exact shape of the 2026-08-10 loss, so its own word about itself is what must not be "
           "trusted. The run's claim is still carried, with the folder to look in",
           _WS_LIED["items"]["WARP-9001"]["state"] == WS.UNCONCLUDED
           and _WS_LIED["counts"][WS.DONE] == 0
           and len(_WS_LIED["items"]["WARP-9001"]["claims"]) == 1
           and _WS_LIED["items"]["WARP-9001"]["claims"][0]["run_said"] == "done")

    _WS_REAL, _ = _ws_report(
        specs=[("WARP-9002", "ready")],
        bundles=[("WARP-9002", _WS_FULL)])
    expect("VELDO-0002 AC1 NEGATIVE CONTROL: a spec whose artifacts ARE on disk is DONE even though no "
           "run folder mentions it at all, so the artifact half is what decides and the run half cannot "
           "veto it. Without this row the one above is satisfied by a reader that calls everything "
           "unconcluded",
           _WS_REAL["items"]["WARP-9002"]["state"] == WS.DONE
           and _WS_REAL["counts"][WS.DONE] == 1
           and _WS_REAL["items"]["WARP-9002"]["claims"] == [])

    _WS_HALF, _ = _ws_report(
        specs=[("WARP-9003", "ready")],
        bundles=[("WARP-9003", ("manifest.json",))],
        runs=[("run-half", "WARP-9003", "running", 2)])
    expect("VELDO-0002 AC1: a HALF-WRITTEN bundle is not done. A manifest with no verdict is a bundle "
           "mid-write, which is a different state from finished, and reading it as done is how a "
           "reader tells an operator to stop looking at work that is not there",
           _WS_HALF["items"]["WARP-9003"]["state"] == WS.UNCONCLUDED
           and _WS_HALF["counts"][WS.DONE] == 0)

_ws_block("AC1", _ws_ac1)


# ---------------------------------------------------------------------------------------
# AC2. A RUN WHOSE LIVENESS CANNOT BE CONFIRMED IS SAID TO BE UNCONFIRMED, WITH THE AGE.
#
# FALSIFIED BY: replace the liveness branch with a return of "running" whenever a run folder
# exists, and the stale row below must go red.
# ---------------------------------------------------------------------------------------


def _ws_ac2():
    _WS_STALE, _WS_STALE_LINES = _ws_report(
        specs=[("WARP-9010", "ready")],
        runs=[("run-stale", "WARP-9010", "running", 54000)])
    _ws_stale_row = _WS_STALE["runs"][0]
    expect("VELDO-0002 AC2: a run whose heartbeat is 15 hours old is LIVENESS_UNCONFIRMED and carries "
           "THE AGE, never 'running' and never 'dead' - this module reads a heartbeat written by a "
           "process it cannot see, so both of those would be a guess an operator would act on. THE AGE "
           "IS THE PRODUCT: runlog.classify calls 31 seconds and 15 hours the same word, which is right "
           "for liveness and useless to a person who just lost a session",
           _ws_stale_row["liveness"] == WS.LIVENESS_UNCONFIRMED
           and 53000 < _ws_stale_row["heartbeat_age_seconds"] < 55000
           and any("last heartbeat" in ln and "LIVENESS_UNCONFIRMED" in ln for ln in _WS_STALE_LINES))

    _WS_LIVE, _ = _ws_report(
        specs=[("WARP-9011", "ready")],
        runs=[("run-live", "WARP-9011", "running", 1)])
    expect("VELDO-0002 AC2 NEGATIVE CONTROL: a run heartbeating one second ago IS reported active, so "
           "the unconfirmed answer is a measurement of the heartbeat rather than this module's only "
           "answer. The two fixtures differ in exactly one field, the heartbeat age",
           _WS_LIVE["runs"][0]["liveness"] == WS.LIVENESS_ACTIVE
           and _WS_LIVE["runs"][0]["heartbeat_age_seconds"] < 30)

    _WS_NOHB, _WS_NOHB_LINES = _ws_report(
        specs=[("WARP-9012", "ready")],
        runs=[("run-nohb", "WARP-9012", "running", None)])
    expect("VELDO-0002 AC2: a run that never wrote a heartbeat at all reports an age of None and says "
           "so in words, NOT an age of zero - never confirmed once and confirmed a moment ago are "
           "opposite facts and a zero would state the reassuring one",
           _WS_NOHB["runs"][0]["heartbeat_age_seconds"] is None
           and _WS_NOHB["runs"][0]["liveness"] == WS.LIVENESS_UNCONFIRMED
           and any("no heartbeat ever recorded" in ln for ln in _WS_NOHB_LINES))




_ws_block("AC2", _ws_ac2)


# ---------------------------------------------------------------------------------------
# AC3. DISAGREEMENT IS REPORTED IN BOTH DIRECTIONS, BECAUSE THEY ARE DIFFERENT FAILURES.
#
# FALSIFIED BY: drop the uncovered-artifacts direction, keeping only run folders with no
# artifacts, and the UNRECORDED row below must go red.
# ---------------------------------------------------------------------------------------


def _ws_ac3():
    # GLOBAL because AC4's key-shape row and AC5's pattern row read this same report, and a
    # fixture rebuilt per block would let the three rows disagree about what they measured.
    global _WS_BOTH, _WS_BOTH_LINES
    _WS_BOTH, _WS_BOTH_LINES = _ws_report(
        specs=[("WARP-9020", "ready"), ("WARP-9021", "ready"), ("WARP-9022", "ready")],
        bundles=[("WARP-9021", _WS_FULL), ("WARP-9022", _WS_FULL)],
        runs=[("run-a", "WARP-9020", "running", 60000), ("run-c", "WARP-9022", "done", 10)])
    expect("VELDO-0002 AC3: a proof bundle NO run folder ever claimed is reported UNRECORDED with its "
           "paths. That is work which COMPLETED off the record - the 2026-08-10 shape - and it is "
           "invisible to any reader that walks only the run registry, which is why this direction "
           "exists at all",
           [u["spec"] for u in _WS_BOTH["unrecorded"]] == ["WARP-9021"]
           and _WS_BOTH["counts"][WS.UNRECORDED] == 1
           and any("UNRECORDED WARP-9021" in ln for ln in _WS_BOTH_LINES))
    expect("VELDO-0002 AC3: the OTHER direction is a separate list - a run folder whose spec has no "
           "artifacts is UNCONCLUDED, which is possibly-half-finished work rather than work done off "
           "the record. Two different failures, two different next actions, never one bucket",
           [u["spec"] for u in _WS_BOTH["unconcluded"]] == ["WARP-9020"])
    expect("VELDO-0002 AC3 NEGATIVE CONTROL: the spec that is BOTH claimed and concluded appears in "
           "NEITHER uncovered list, so the two lists measure disagreement and are not a restatement of "
           "the corpus. WARP-9022 has a run and a full bundle and is simply done",
           _WS_BOTH["items"]["WARP-9022"]["state"] == WS.DONE
           and "WARP-9022" not in [u["spec"] for u in _WS_BOTH["unrecorded"]]
           and "WARP-9022" not in [u["spec"] for u in _WS_BOTH["unconcluded"]])
    expect("VELDO-0002 AC3: the three states PARTITION the items exactly - every spec id either half "
           "knows about lands in exactly one of done, unconcluded or queued, and the counts sum to the "
           "item total. UNRECORDED is a property OF a done item, not a fourth bucket competing with it",
           sum(_WS_BOTH["counts"][s] for s in (WS.DONE, WS.UNCONCLUDED, WS.QUEUED))
           == len(_WS_BOTH["items"])
           and sorted(_WS_BOTH["items"]) == ["WARP-9020", "WARP-9021", "WARP-9022"])


_ws_block("AC3", _ws_ac3)


# ---------------------------------------------------------------------------------------
# AC4. NO CONFIDENT ZERO.
#
# FALSIFIED BY: make the report return zeros and empty lists when the runs root does not exist,
# instead of standing down with a reason, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _ws_ac4():
    _WS_NOREG, _WS_NOREG_LINES = _ws_report(
        specs=[("WARP-9030", "ready")],
        bundles=[("WARP-9030", _WS_FULL)],
        with_registry=False)
    expect("VELDO-0002 AC4: when the run registry does not exist the run half STANDS DOWN and names "
           "the reason, because 'no run has ever recorded itself here' and 'no run is in flight' are "
           "different facts that a zero cannot tell apart. This is the confident zero this migration "
           "kept finding, written into the one organ whose whole job is to be trusted after a loss",
           _WS_NOREG["runs_stood_down"] is True
           and "NOT the same fact" in _WS_NOREG["runs_standdown_reason"]
           and any("STOOD DOWN" in ln for ln in _WS_NOREG_LINES))
    expect("VELDO-0002 AC4: the CORPUS half still answers while the run half is stood down, because it "
           "reads artifacts that do not depend on the registry - a reader that refused to answer at all "
           "would be useless in exactly the situation it exists for",
           _WS_NOREG["items"]["WARP-9030"]["state"] == WS.DONE
           and _WS_NOREG["counts"][WS.DONE] == 1)
    expect("VELDO-0002 AC4: with the run half stood down NOTHING is called UNRECORDED, because being "
           "unclaimed cannot be measured against a registry that does not exist. Asserting it here "
           "would be the same confident zero pointing the other way",
           _WS_NOREG["unrecorded"] == [] and _WS_NOREG["counts"][WS.UNRECORDED] == 0)
    expect("VELDO-0002 AC4 NEGATIVE CONTROL: the SAME fixture WITH a registry present does not stand "
           "down and does name the artifact unrecorded, so the stand-down is a measurement of the "
           "registry and not the module's default",
           _ws_report(specs=[("WARP-9030", "ready")], bundles=[("WARP-9030", _WS_FULL)],
                      runs=[("run-x", "WARP-9099", "running", 5)])[0]["unrecorded"][0]["spec"]
           == "WARP-9030")
    expect("VELDO-0002 AC4: the report has ONE key shape whether the run half stood down or not, so a "
           "consumer never guesses whether a key is missing or genuinely empty",
           sorted(_WS_NOREG) == sorted(WS.REPORT_KEYS)
           and sorted(_WS_BOTH) == sorted(WS.REPORT_KEYS))


_ws_block("AC4", _ws_ac4)


# ---------------------------------------------------------------------------------------
# AC5. THE CORPUS IS THE ONE ALREADY DECLARED, NOT A SECOND SPELLING OF IT.
#
# FALSIFIED BY: hand-list the artifact patterns instead of taking them from verdict_corpus, and the
# SUBSTITUTION row below must go red. That is the row this criterion is measured by, and it exists
# because an independent review drove the declared falsification and the suite stayed GREEN: with
# the values unchanged, value equality between two reads of the same two constants cannot tell a
# delegation from a copy, which is the entire defect the criterion names. Only a WRONG value was
# caught, and a wrong value is a different defect that AC1 and AC3 already red.
# ---------------------------------------------------------------------------------------


def _ws_ac5():
    _WS_VC = V._VC._organ("verdict_corpus", ROOT / ".veldo" / "verdict_corpus.py")
    # THE DECLARED SET, DERIVED FROM THE DECLARING MODULE by the same naming rule work_state uses,
    # not a two-element literal written here. The earlier spelling of this row compared against
    # {VERDICT_PATTERN, MANIFEST_PATTERN} while that module declares FOUR corpus patterns, so the
    # second spelling of "which patterns matter" had moved from the module into its test.
    _WS_DECLARED = {_ws_v for _ws_k, _ws_v in vars(_WS_VC).items()
                    if _ws_k.endswith(WS.CORPUS_PATTERN_SUFFIX) and isinstance(_ws_v, str) and _ws_v}
    expect("VELDO-0002 AC5: the patterns this reader walks are EQUAL AS A SET to EVERY corpus pattern "
           "verdict_corpus declares (%d of them, derived from that module's own declarations by the "
           "naming rule rather than named one by one here), and the two the done rule needs are among "
           "them. No cardinality is pinned: the row states equality and a relationship, both of which "
           "hold at any size" % len(_WS_DECLARED),
           set(WS.corpus_patterns()) == _WS_DECLARED
           and {_WS_VC.VERDICT_PATTERN, _WS_VC.MANIFEST_PATTERN} <= set(WS.corpus_patterns())
           and set(_WS_BOTH["corpus_patterns"]) == set(WS.corpus_patterns()))

    # THE TEETH. verdict_corpus is SUBSTITUTED for one declaring renamed patterns, and this reader
    # must follow it: the bundle named for the SUBSTITUTED patterns is done and the bundle named for
    # the values this repository uses today is not. A hand-kept copy of those values passes every
    # equality row above and fails here, which is the difference between detecting a wrong pattern
    # and detecting a second spelling.
    with tempfile.TemporaryDirectory() as _ws_d:
        _WS_SUB, _ws_n = _ws_substituted_corpus(_ws_d)
        _WS_SUB_DECLARED = {_ws_v for _ws_k, _ws_v in vars(_WS_SUB).items()
                            if _ws_k.endswith(WS.CORPUS_PATTERN_SUFFIX)
                            and isinstance(_ws_v, str) and _ws_v}
        expect("VELDO-0002 AC5 FIXTURE APPLIED, asserted before anything is read from it: the "
               "substituted verdict_corpus rewrote %d declaration(s), one per pattern the real module "
               "declares, and the set it now declares is DISJOINT from the real one. A fixture that "
               "silently failed to apply would leave the row below passing for the wrong reason"
               % _ws_n,
               _ws_n == len(_WS_DECLARED) and _ws_n >= 2
               and not (_WS_SUB_DECLARED & _WS_DECLARED)
               and all(_ws_v.startswith(_WS_RENAME_PREFIX) for _ws_v in _WS_SUB_DECLARED))
        _WS_SUB_WS = V._VC._organ("work_state_substituted",
                                  Path(_ws_d) / ".veldo" / "work_state.py")
        _ws_new_v = _WS_SUB.VERDICT_PATTERN.replace("*", "")
        _ws_new_m = _WS_SUB.MANIFEST_PATTERN.replace("*", "")
        _ws_old_v = _WS_VC.VERDICT_PATTERN.replace("*", "")
        _ws_old_m = _WS_VC.MANIFEST_PATTERN.replace("*", "")
        _ws_tree(_ws_d,
                 specs=[("WARP-9050", "ready"), ("WARP-9051", "ready")],
                 bundles=[("WARP-9050", {_ws_new_v: _WS_PASS, _ws_new_m: None}),
                          ("WARP-9051", {_ws_old_v: _WS_PASS, _ws_old_m: None})])
        _WS_SUB_REP = _WS_SUB_WS.work_report(
            root=Path(_ws_d), runs_root=_ws_os.path.join(_ws_d, "no-registry-here"))
        expect("VELDO-0002 AC5 TEETH: with verdict_corpus SUBSTITUTED for one declaring renamed "
               "patterns, this reader walks THE SUBSTITUTED MODULE'S patterns - the bundle named for "
               "them is DONE and the bundle named for the values this repository happens to use today "
               "is not. This is the row the criterion's declared falsification must red: hand-listing "
               "the patterns leaves every value-equality assertion green, because a copy that copies "
               "correctly is invisible to a comparison of the copies",
               set(_WS_SUB_WS.corpus_patterns()) == _WS_SUB_DECLARED
               and _WS_SUB_REP["items"]["WARP-9050"]["state"] == _WS_SUB_WS.DONE
               and _WS_SUB_REP["items"]["WARP-9051"]["state"] != _WS_SUB_WS.DONE)

    # MEASURED OVER THIS REPOSITORY, as RELATIONSHIPS against the module that owns the enumeration,
    # with the spec id read through that module's own spec_id_for_verdict rather than re-split here:
    # one shape read in two places is the thing this criterion exists to forbid, and the previous
    # spelling of this row recomputed it inline as _ws_v.split("/")[1] while its own message said it
    # did not. Nothing here requires the corpus to be non-empty or to have a fixed size: both
    # clauses hold at any size, including on a fresh adopter's first day.
    _WS_LIVE_REP = WS.work_report(root=ROOT, runs_root=str(ROOT / "no-such-runs-root-for-this-row"))
    _WS_LIVE_DONE = {_ws_s for _ws_s, _ws_i in _WS_LIVE_REP["items"].items()
                     if _ws_i["state"] == WS.DONE}
    _WS_VC_BOTH = ({_WS_VC.spec_id_for_verdict(_ws_v)
                    for _ws_v in _WS_VC.disk_corpus(ROOT, _WS_VC.VERDICT_PATTERN)}
                   & {_WS_VC.spec_id_for_verdict(_ws_m)
                      for _ws_m in _WS_VC.disk_corpus(ROOT, _WS_VC.MANIFEST_PATTERN)}) - {""}
    _WS_NOT_DONE_BOTH = _WS_VC_BOTH - _WS_LIVE_DONE
    expect("VELDO-0002 AC5 over THIS repository: every item this reader calls DONE is one "
           "verdict_corpus names for BOTH patterns, and each of the %d of %d it names for both that "
           "is NOT done carries a verdict artifact recording something other than a passing review - "
           "so the enumeration is that module's and the exclusions are the recorded verdicts, never a "
           "second walk written here. Relationships, not counts: no clause requires a non-empty "
           "corpus or a fixed size" % (len(_WS_NOT_DONE_BOTH), len(_WS_VC_BOTH)),
           _WS_LIVE_DONE <= _WS_VC_BOTH
           and all(any(not _ws_r["concludes"] for _ws_r in _WS_LIVE_REP["items"][_ws_s]["verdicts"])
                   for _ws_s in _WS_NOT_DONE_BOTH))


_ws_block("AC5", _ws_ac5)


# ---------------------------------------------------------------------------------------
# AC1, SECOND PROPERTY. A VERDICT FILE IS NOT A CONCLUSION - WHAT IT RECORDS IS.
#
# Its own block rather than more rows inside _ws_ac1, because a block that raises loses every row
# below it and these rows are the ones an operator's "what is done" depends on. AC1 declares TWO
# mutations for exactly this reason; this is the second.
#
# FALSIFIED BY: make DONE read the EXISTENCE of a verdict artifact instead of the verdict it
# records, and the rejection row below must go red.
# ---------------------------------------------------------------------------------------


def _ws_ac1_recorded_verdict():
    # THE VERDICT'S BYTES, NOT ITS FILENAME. Measured on this repository before the fix: TWELVE
    # items whose only verdict on disk recorded a rejection were reported DONE, the L2 review that
    # FAILED this very item among them, and the headline read "154 done, 0 unconcluded".
    expect("VELDO-0002 AC1: the two verdict values these fixtures record are the vocabulary's own - "
           "%r comes from the passing set work_state delegates to and %r from validate's declared "
           "VERDICTS minus that set, so the rejection below is a legal verdict this repository can "
           "write rather than a word invented to fail a check" % (_WS_PASS, _WS_FAIL),
           _WS_PASS in V.VERDICTS and _WS_FAIL in V.VERDICTS
           and _WS_PASS in WS.passing_verdicts() and _WS_FAIL not in WS.passing_verdicts())

    _WS_REJ, _WS_REJ_LINES = _ws_report(
        specs=[("WARP-9004", "ready")],
        bundles=[("WARP-9004", {"manifest.json": None, "verdict.json": _WS_FAIL})])
    expect("VELDO-0002 AC1: a complete bundle whose VERDICT RECORDS A REJECTION is NOT done, because "
           "what concludes an item is what the verdict SAYS and never that a file with that name "
           "exists. Reading existence as done reported twelve rejected items on this repository as "
           "done, including the review that failed this item, and an operator told 'done' about "
           "rejected work stops looking at exactly the work that needs them. The verdict PATH and the "
           "recorded value are printed, because the product of this reader is somewhere to look",
           _WS_REJ["items"]["WARP-9004"]["state"] != WS.DONE
           and _WS_REJ["counts"][WS.DONE] == 0
           and [(r["path"], r["verdict"], r["concludes"])
                for r in _WS_REJ["items"]["WARP-9004"]["verdicts"]]
           == [("proof/WARP-9004/verdict.json", _WS_FAIL, False)]
           and any("REVIEWED AND NOT CONCLUDED WARP-9004" in ln
                   and "proof/WARP-9004/verdict.json" in ln and _WS_FAIL in ln
                   for ln in _WS_REJ_LINES))

    _WS_ROUND2, _WS_ROUND2_LINES = _ws_report(
        specs=[("WARP-9005", "ready")],
        bundles=[("WARP-9005", {"manifest.json": None, "verdict-1.json": _WS_FAIL,
                                "verdict-2.json": _WS_PASS})])
    expect("VELDO-0002 AC6 NEGATIVE CONTROL, ADDITIVE: the same rejected bundle with ONE MORE artifact "
           "ADDED, a second-round verdict recording %r, IS done and prints no rejection line - so the "
           "row above measures what the verdicts say rather than refusing every bundle that carries a "
           "failing round. This is the shape of every multi-round review in this repository: the "
           "failing round stays on disk as the record" % _WS_PASS,
           _WS_ROUND2["items"]["WARP-9005"]["state"] == WS.DONE
           and _WS_ROUND2["counts"][WS.DONE] == 1
           and [r["concludes"] for r in _WS_ROUND2["items"]["WARP-9005"]["verdicts"]] == [False, True]
           and not any("REVIEWED AND NOT CONCLUDED" in ln for ln in _WS_ROUND2_LINES))

    _WS_UNREADABLE, _ = _ws_report(
        specs=[("WARP-9006", "ready")],
        bundles=[("WARP-9006", ("manifest.json",))],
        raw=[("WARP-9006", "verdict.json", "{ this is not json")])
    expect("VELDO-0002 AC1: a verdict artifact this reader CANNOT READ concludes nothing - it is "
           "reported with a recorded verdict of None and the item is not done. Fails closed on "
           "purpose: the reassuring answer has to be earned by bytes that parse",
           _WS_UNREADABLE["items"]["WARP-9006"]["state"] != WS.DONE
           and [(r["verdict"], r["concludes"])
                for r in _WS_UNREADABLE["items"]["WARP-9006"]["verdicts"]] == [(None, False)])


_ws_block("AC1 recorded-verdict", _ws_ac1_recorded_verdict)
