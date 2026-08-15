"""VELDO-0015: liveness stands down on clock disagreement.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, so its declared
prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 28_veldo_0015_clock_standdown

WHAT IS UNDER TEST. The future direction of both freshness readers. Before this spec, both
subtracted one way (now - hb > window), so a heartbeat AHEAD of the reader's clock never exceeded
the window and read as alive FOREVER (PLAN-0018 finding 76). The fix is a THIRD VERDICT, never a
symmetric window: symmetric turns the lockout into a silent double-build, because a fast clock then
reads stale and a LIVE claim is handed to a second worker. Settled as veldo-factory kernel OD-9.

EVERY VERDICT HERE IS COMPUTED WITH AN EXPLICIT now_epoch, never the wall clock, so these rows are
deterministic and cannot rot as the suite ages. The claim-side rows drive the REAL claim() path,
lock, publish and all, in a temporary claims root, never a re-implementation of it.
"""
import importlib.util as _v15_ilu

_v15_spec = _v15_ilu.spec_from_file_location("v15_claim", ROOT / ".veldo" / "claim.py")
CL15 = _v15_ilu.module_from_spec(_v15_spec)
_v15_spec.loader.exec_module(CL15)
_v15_rspec = _v15_ilu.spec_from_file_location("v15_runlog", ROOT / ".veldo" / "runlog.py")
RL15 = _v15_ilu.module_from_spec(_v15_rspec)
_v15_rspec.loader.exec_module(RL15)

# A fixed reference instant, so every arithmetic below is checkable by eye:
# 2026-07-24T12:00:00Z.
_V15_NOW = 1784980800.0
_V15_TOL = CL15.CLOCK_SKEW_TOLERANCE_SECONDS
_V15_RTOL = RL15.CLOCK_SKEW_TOLERANCE_SECONDS


def _v15_stamp(offset_seconds):
    """An ISO stamp offset from the fixed reference instant, in the ONE spelling the readers read."""
    import datetime as _dt
    t = _dt.datetime.fromtimestamp(_V15_NOW + offset_seconds, _dt.timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def _v15_rec(offset_seconds):
    return {"unit_id": "VELDO-0015-FIX", "worker_id": "worker-fast-clock",
            "requirements": [], "claimed_at": _v15_stamp(offset_seconds),
            "heartbeat_at": _v15_stamp(offset_seconds)}


# ---------------------------------------------------------------------------------------------
# AC1 + AC2: the claim ledger, driven through the REAL claim() path in a temporary claims root.
# ---------------------------------------------------------------------------------------------
with tempfile.TemporaryDirectory(prefix="v15claims") as _v15_d:
    _v15_root = Path(_v15_d)
    # Publish a record whose heartbeat is FAR ahead of the reference clock, through the real
    # claim() so the on-disk shape is the ledger's own, then re-stamp its heartbeat to the future.
    _v15_ok, _v15_why = CL15.claim("VELDO-0015-FIX", "worker-fast-clock", root=_v15_root)
    expect("VELDO-0015 fixture: the fast worker's original claim is granted through the real path",
           _v15_ok is True and _v15_why == "granted")
    _v15_path = CL15._path("VELDO-0015-FIX", _v15_root)
    _v15_cur = CL15._read(_v15_path)
    # THE WALL-CLOCK ROWS STAMP RELATIVE TO THE WALL CLOCK. claim() judges liveness with the real
    # now, so a "future" stamp built from the fixed reference instant is only future until the
    # calendar catches up - and it already had: the first run of this suite stamped July 24 plus an
    # hour, three WEEKS in the past at execution time, the takeover legitimately granted, and both
    # naming rows went red. The row below the fixed-instant rows use _V15_NOW; the rows that drive
    # the real claim() use real time, each clock judged against itself.
    import time as _v15_time
    _v15_cur["heartbeat_at"] = _v15_stamp((_v15_time.time() - _V15_NOW) + _V15_TOL + 3600)
    CL15._publish(str(Path(_v15_path).parent), str(_v15_path), _v15_cur)

    # The verdict function itself, at the fixed instant, on a fixed-instant record.
    expect("VELDO-0015 AC1: liveness() answers 'unanswerable' for a heartbeat beyond tolerance "
           "ahead - the named third verdict, not 'live' (the pre-fix answer, which held the unit "
           "forever) and not 'stale' (the symmetric-window answer, which hands a live claim to a "
           "second worker)",
           CL15.liveness(_v15_rec(_V15_TOL + 3600), now_epoch=_V15_NOW) == "unanswerable")

    # AC2 through the REAL takeover path: a second worker's claim() must not be granted, and the
    # record on disk must still name the original holder afterwards.
    _v15_ok2, _v15_why2 = CL15.claim("VELDO-0015-FIX", "worker-two", root=_v15_root)
    expect("VELDO-0015 AC2: the takeover path does NOT grant - a second worker's claim() against "
           "the unanswerable record is refused, and the on-disk record still names the original "
           "holder, so the silent double-build (two workers, one unit) is impossible by "
           "construction rather than by luck",
           _v15_ok2 is False
           and CL15._read(_v15_path).get("worker_id") == "worker-fast-clock")

    # AC1's naming half: the refusal reason is the summons, not the wait-word. The record's
    # heartbeat is an hour beyond tolerance ahead of the REAL clock (stamped above), so claim()'s
    # wall-clock verdict is deterministic for the lifetime of any single run.
    expect("VELDO-0015 AC1: the refusal is BY NAME - (False, 'unanswerable'), never (False, "
           "'claimed'), because 'claimed' tells an operator to wait and waiting cannot fix a "
           "broken clock",
           _v15_why2 == "unanswerable")

    # AC2's held half, on the surface the frontier actually reads (review B2: under the
    # unanswerable-counts-stale mutation, holder/is_claimed/claimed_units all flipped to
    # "unclaimed" while claim() refused forever - a hot loop between the offer surface and the
    # claim surface that no row saw, because none of these three names appeared in this suite).
    expect("VELDO-0015 AC2: the unit VISIBLY stays held on the reader surface - holder() still "
           "names the original worker, is_claimed() answers True, and the unit appears in "
           "claimed_units() - so the frontier cannot start offering a unit the claim surface "
           "refuses",
           CL15.holder("VELDO-0015-FIX", root=_v15_root) == "worker-fast-clock"
           and CL15.is_claimed("VELDO-0015-FIX", root=_v15_root) is True
           and "VELDO-0015-FIX" in CL15.claimed_units(root=_v15_root))

    # AC2's boolean-contract half: the reclaim test answers False (not reclaimable), and the
    # near-boundary arithmetic holds on both sides.
    expect("VELDO-0015 AC2: _is_stale answers False for the unanswerable record - 'cannot judge' "
           "never authorizes a takeover - while a genuinely stale record (heartbeat one second "
           "past the window) still answers True, so the reclaim rule kept its teeth",
           CL15._is_stale(_v15_cur, now_epoch=_V15_NOW) is False
           and CL15._is_stale(_v15_rec(-(CL15.STALE_AFTER_SECONDS + 1)), now_epoch=_V15_NOW) is True)

# ---------------------------------------------------------------------------------------------
# AC4's BAND ROW (review B1): the tolerance's magnitude is a checked fact, not a comment. The
# review drove the constant to 0 (every one-second skew alarms: the false-alarm flood AC4 forbids)
# and to one year (finding 76 restored: a day-fast clock reads live forever) with every row green,
# because every fixture was expressed relative to the constant itself - branch-on-the-verdict one
# level up. The band: at least a minute, at most ten times the module's own staleness window.
# ---------------------------------------------------------------------------------------------
expect("VELDO-0015 AC4: the tolerance constants are pinned inside the defensible band in BOTH "
       "modules - at least 60 seconds (no NTP-grade false alarms) and at most ten times the "
       "module's own staleness window (no silent restoration of finding 76 by a huge tolerance)",
       60 <= CL15.CLOCK_SKEW_TOLERANCE_SECONDS <= 10 * CL15.STALE_AFTER_SECONDS
       and 60 <= RL15.CLOCK_SKEW_TOLERANCE_SECONDS <= 10 * RL15.STALE_AFTER_SECONDS)

# ---------------------------------------------------------------------------------------------
# AC3 + AC4: the run reader, at the same fixed instant.
# ---------------------------------------------------------------------------------------------
def _v15_state(offset_seconds, status="running"):
    return {"status": status, "heartbeat_at": _v15_stamp(offset_seconds)}


expect("VELDO-0015 AC3: runlog.classify answers 'unanswerable' for a heartbeat beyond tolerance "
       "ahead of now, where the pre-fix reader answered 'active' forever",
       RL15.classify(_v15_state(_V15_RTOL + 3600), now_epoch=_V15_NOW) == "unanswerable")

expect("VELDO-0015 AC3: terminal facts still outrank the clock - a run with status 'done' or "
       "'blocked' classifies by its recorded status even with a far-future heartbeat, because a "
       "recorded terminal fact does not need a clock",
       RL15.classify(_v15_state(_V15_RTOL + 3600, status="done"), now_epoch=_V15_NOW) == "done"
       and RL15.classify(_v15_state(_V15_RTOL + 3600, status="blocked"),
                         now_epoch=_V15_NOW) == "blocked")

with tempfile.TemporaryDirectory(prefix="v15tol") as _v15_td:
    import time as _v15_t2
    _v15_troot = Path(_v15_td)
    CL15.claim("VELDO-0015-TOL", "holder-a", root=_v15_troot)
    _v15_tp = CL15._path("VELDO-0015-TOL", _v15_troot)
    _v15_tc = CL15._read(_v15_tp)
    # ahead of the REAL clock by half the tolerance: ordinary skew, judged by claim() itself
    _v15_tc["heartbeat_at"] = _v15_stamp((_v15_t2.time() - _V15_NOW) + _V15_TOL // 2)
    CL15._publish(str(Path(_v15_tp).parent), str(_v15_tp), _v15_tc)
    expect("VELDO-0015 AC4: an IN-tolerance future heartbeat is refused by the real claim() with "
           "'claimed' - the wait-word, correct for ordinary skew - never 'unanswerable' (review "
           "N2: this mapping was previously asserted only through liveness(), not the real path)",
           CL15.claim("VELDO-0015-TOL", "intruder", root=_v15_troot) == (False, "claimed"))

expect("VELDO-0015 AC4: ordinary skew is not an alarm - a heartbeat ahead by exactly the tolerance "
       "still classifies 'active' and still reads live for the claim ledger, and one second beyond "
       "flips both, so the boundary sits exactly where the constant declares it",
       RL15.classify(_v15_state(_V15_RTOL), now_epoch=_V15_NOW) == "active"
       and RL15.classify(_v15_state(_V15_RTOL + 1), now_epoch=_V15_NOW) == "unanswerable"
       and CL15.liveness(_v15_rec(_V15_TOL), now_epoch=_V15_NOW) == "live"
       and CL15.liveness(_v15_rec(_V15_TOL + 1), now_epoch=_V15_NOW) == "unanswerable")

# ---------------------------------------------------------------------------------------------
# AC5: no surface answers "alive" for a future stamp - the REAL status reader, driven.
# work_state.liveness deliberately never forwards a future stamp to classify (it answers before
# consulting the window - a protection that PREDATES this spec, from the finding-61 work), so the
# routing claim the first draft of this criterion made was false, and the meta attr-check caught
# its dead fixture. The truthful assertion: the real reader answers UNCONFIRMED with the
# future-stamp note, never ACTIVE, and that pre-existing protection is pinned as a regression row
# so this spec cannot be "completed" by quietly removing it.
# ---------------------------------------------------------------------------------------------
WS15 = _v15_ilu.module_from_spec(
    _v15_ilu.spec_from_file_location("v15_workstate", ROOT / ".veldo" / "work_state.py"))
WS15.__spec__.loader.exec_module(WS15)
_v15_run = {"state": {"status": "running", "heartbeat_at": _v15_stamp(_V15_RTOL + 3600)}}
_v15_ans, _v15_age, _v15_note = WS15.liveness(_v15_run, now_epoch=_V15_NOW)
expect("VELDO-0015 AC5: the real status reader (work_state.liveness) answers LIVENESS_UNCONFIRMED "
       "with the future-stamp note for a future-heartbeat run - never LIVENESS_ACTIVE - so no "
       "operator surface calls a broken clock alive; pinned here so the pre-existing protection "
       "cannot be quietly removed as redundant after this spec",
       _v15_ans == WS15.LIVENESS_UNCONFIRMED
       and _v15_ans != WS15.LIVENESS_ACTIVE
       and _v15_note is not None and "future" in str(_v15_note).lower())

# ---------------------------------------------------------------------------------------------
# AC6: THE REGRESSION TABLE. Every shipped verdict for agreeing clocks is byte-identical, over all
# five fixture families, asserted as a table rather than as prose.
# ---------------------------------------------------------------------------------------------
# ONE table, iterated, with its row count asserted (review N1: the first draft defined a table
# nothing read and asserted a hand-written conjunction beside it, so deleting a family would have
# shrunk the evidence silently). Each row: (label, claim-side record or None, liveness expected,
# reclaimable expected, runlog state or None, classify expected).
_V15_TABLE = [
    ("fresh",             _v15_rec(0),                                "live",  False,
     _v15_state(0),                                "active"),
    ("slightly past",     _v15_rec(-5),                               "live",  False,
     _v15_state(-5),                               "active"),
    ("exactly at window", _v15_rec(-CL15.STALE_AFTER_SECONDS),        "live",  False,
     _v15_state(-RL15.STALE_AFTER_SECONDS),        "active"),
    ("past window",       _v15_rec(-(CL15.STALE_AFTER_SECONDS + 60)), "stale", True,
     _v15_state(-(RL15.STALE_AFTER_SECONDS + 60)), "stale"),
    ("absent heartbeat",  {"worker_id": "w"},                         "stale", True,
     {"status": "running"},                        "stale"),
    ("malformed stamp",   {"heartbeat_at": "not-a-time"},             "stale", True,
     {"status": "running", "heartbeat_at": "not-a-time"}, "stale"),
]
_v15_table_ok = all(
    CL15.liveness(_rec, now_epoch=_V15_NOW) == _lv
    and CL15._is_stale(_rec, now_epoch=_V15_NOW) is _st
    and RL15.classify(_state, now_epoch=_V15_NOW) == _cl
    for (_label, _rec, _lv, _st, _state, _cl) in _V15_TABLE
)
expect("VELDO-0015 AC6: EVERY SHIPPED VERDICT FOR AGREEING CLOCKS IS UNCHANGED - one table of six "
       "fixture families (fresh, slightly past, exactly-at-window with the strict comparison "
       "preserved, past-window, absent, malformed), iterated over BOTH readers, with the row count "
       "itself asserted so deleting a family reds this row instead of shrinking the evidence",
       _v15_table_ok and len(_V15_TABLE) == 6)

with tempfile.TemporaryDirectory(prefix="v15reg") as _v15_rd:
    _v15_rroot = Path(_v15_rd)
    CL15.claim("VELDO-0015-REG", "holder", root=_v15_rroot)
    _v15_intruder = CL15.claim("VELDO-0015-REG", "intruder", root=_v15_rroot)
    _v15_again = CL15.claim("VELDO-0015-REG", "holder", root=_v15_rroot)
expect("VELDO-0015 AC6: the two reasons that existed before still exist and still mean what they "
       "meant - a live claim by another worker still refuses with 'claimed', and this worker's own "
       "claim is still re-granted",
       _v15_intruder == (False, "claimed") and _v15_again == (True, "granted"))
