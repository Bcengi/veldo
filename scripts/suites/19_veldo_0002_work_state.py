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


def _ws_tree(d, specs=(), bundles=(), runs=()):
    """Build a tree: specs as front-matter files, bundles as proof artifacts, runs as run folders.

    bundles entries are (spec_id, files) where files is a tuple naming which artifacts exist, so a
    row can build a bundle that is HALF written - a manifest with no verdict - which is a different
    state from finished and must not read as done.
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
        for name in files:
            (bdir / name).write_text(json.dumps({"schema": "fixture", "spec_id": sid}))
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


def _ws_report(specs=(), bundles=(), runs=(), with_registry=True):
    """One report over a fresh tree. Returns (report, lines)."""
    with tempfile.TemporaryDirectory() as d:
        rroot = _ws_tree(d, specs, bundles, runs)
        if not with_registry:
            rroot = _ws_os.path.join(d, "no-registry-here")
        rep = WS.work_report(root=Path(d), runs_root=rroot)
        return rep, WS.report_lines(rep)


_WS_FULL = ("manifest.json", "verdict.json")

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
# FALSIFIED BY: hand-list the artifact patterns instead of taking them from verdict_corpus, and
# the set-equality row below must go red.
# ---------------------------------------------------------------------------------------


def _ws_ac5():
    _WS_VC = V._VC._organ("verdict_corpus", ROOT / ".veldo" / "verdict_corpus.py")
    expect("VELDO-0002 AC5: the patterns this reader walks are EQUAL AS A SET to the ones "
           "verdict_corpus declares, taken from that module rather than copied. A hand-kept copy here "
           "is how this repository has already shipped two mechanisms enumerating one set in two "
           "spellings, with the gap invisible to both",
           set(WS.corpus_patterns()) == {_WS_VC.VERDICT_PATTERN, _WS_VC.MANIFEST_PATTERN}
           and set(_WS_BOTH["corpus_patterns"]) == set(WS.corpus_patterns()))
    # MEASURED OVER THIS REPOSITORY, as SET EQUALITY against the module that owns the enumeration, so
    # the two cannot diverge in a spelling. Nothing here requires the set to be non-empty: the row states
    # equality, which holds at any size, and it REPORTS the size it measured. An assertion that required
    # artifacts to exist would redden a fresh adopter's gate on day one.
    _WS_LIVE_REP = WS.work_report(root=ROOT, runs_root=str(ROOT / "no-such-runs-root-for-this-row"))
    _WS_VC_BOTH = (set(_ws_v.split("/")[1] for _ws_v in _WS_VC.disk_corpus(ROOT, _WS_VC.VERDICT_PATTERN)
                       if len(_ws_v.split("/")) > 2)
                   & set(_ws_m.split("/")[1] for _ws_m in _WS_VC.disk_corpus(ROOT,
                                                                             _WS_VC.MANIFEST_PATTERN)
                         if len(_ws_m.split("/")) > 2))
    expect("VELDO-0002 AC5: over THIS repository the reader's DONE set is EQUAL to the set of spec ids "
           "verdict_corpus names for BOTH patterns (%d of them), asserted as set equality against that "
           "module rather than recomputed here. The row states equality, which holds at any size, and "
           "requires no artifact to exist: a row demanding a non-empty corpus would redden a fresh "
           "adopter's gate on their first day"
           % len(_WS_VC_BOTH),
           {_ws_s for _ws_s in _WS_LIVE_REP["items"]
            if _WS_LIVE_REP["items"][_ws_s]["state"] == WS.DONE} == _WS_VC_BOTH)


_ws_block("AC5", _ws_ac5)


