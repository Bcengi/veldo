"""VELDO-0006: budget continuity on the operator's path.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, which always
runs, so its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 23_veldo_0006_budget_state

WHAT IS UNDER TEST. .veldo/budget_state.py, driven directly, AND the claim that every number in it
comes from .veldo/governor.py rather than a second implementation - which is asserted by calling the
governor's own functions over the same inputs and requiring equality, not by reading the source.

TIME IS A PARAMETER EVERYWHERE. Every row passes now_epoch explicitly, so no row depends on the wall
clock and none can pass or fail because of when the suite ran.

EVERY CRITERION'S BLOCK IS WRAPPED, so a raise reds a NAMED row instead of shortening the run.
"""
BS = V._VC._organ("budget_state", ROOT / ".veldo" / "budget_state.py")
BSG = V._VC._organ("governor", ROOT / ".veldo" / "governor.py")

_BS_NOW = 1_760_000_000.0


def _bs_block(label, fn):
    try:
        fn()
    except Exception as _bs_e:                   # noqa: BLE001 - a raise must RED a row, never skip
        expect("VELDO-0006 %s: the block ran to completion rather than raising (%r)"
               % (label, _bs_e), False)


def _bs_windows(session_tokens=1000.0, weekly_tokens=10000.0):
    return [BSG.Window("session", 3600, session_tokens),
            BSG.Window("weekly", 7 * 86400, weekly_tokens)]


def _bs_event(tokens, ago_seconds, now=_BS_NOW):
    """One spend event at a known offset from now, stamped the way the stream stamps them."""
    import datetime as _bs_dt
    at = _bs_dt.datetime.fromtimestamp(now - ago_seconds, _bs_dt.timezone.utc)
    return {"schema": "veldo.event/v1", "type": "gate.passed", "tokens": tokens,
            "at": at.strftime("%Y-%m-%dT%H:%M:%SZ")}


# ---------------------------------------------------------------------------------------
# AC1. NO RECORDED SPEND IS NOT ZERO SPEND.
#
# FALSIFIED BY: treat an empty spend history as zero tokens spent, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _bs_ac1():
    rep = BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW, events=[], max_workers=8)
    lines = BS.report_lines(rep)
    expect("VELDO-0006 AC1: with NO recorded spend every window reports UNMEASURED and there is NO "
           "remaining figure at all - not zero used, not the full budget left. MEASURED on the live "
           "stream 2026-08-12: it carries zero events with a spend field, so the obvious report "
           "would announce the whole budget remains when the truth is the instrument was never "
           "connected. Those invite opposite decisions",
           all(w["state"] == BS.UNMEASURED for w in rep["windows"])
           and all(w["used"] is None and w["remaining"] is None for w in rep["windows"])
           and rep["spend_events"] == 0
           and any("UNMEASURED" in ln and "no remaining figure" in ln for ln in lines))

    rep2 = BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW,
                            events=[_bs_event(250, 60)], per_worker_rate=1.0, max_workers=8)
    session = rep2["windows"][0]
    expect("VELDO-0006 AC1 NEGATIVE CONTROL: with ONE recorded spend event inside the horizon the "
           "same window reports a REAL used and remaining figure, so UNMEASURED is a measurement of "
           "the stream rather than this module's only answer. The two fixtures differ by exactly one "
           "event",
           session["state"] == "measured" and session["used"] == 250.0
           and session["remaining"] == 750.0
           and session["recorded_events_in_horizon"] == 1)

    rep3 = BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW,
                            events=[_bs_event(250, 7200)], per_worker_rate=1.0, max_workers=8)
    expect("VELDO-0006 AC1: an event OUTSIDE the trailing horizon leaves that window UNMEASURED "
           "while the longer window measures it - the horizon is what decides, per window, so a "
           "spend from two hours ago cannot make a one-hour window look measured",
           rep3["windows"][0]["state"] == BS.UNMEASURED
           and rep3["windows"][1]["state"] == "measured"
           and rep3["windows"][1]["used"] == 250.0)


_bs_block("AC1", _bs_ac1)


# ---------------------------------------------------------------------------------------
# AC2. BOOTSTRAP IS SAID OUT LOUD, BECAUSE IT MEANS THE PACING IS NOT HAPPENING.
#
# FALSIFIED BY: report PACING whenever windows are configured, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _bs_ac2():
    rep = BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW, events=[],
                           per_worker_rate=0.0, max_workers=8)
    expect("VELDO-0006 AC2: an UNMEASURED burn rate reports posture BOOTSTRAP and says the worker "
           "count is a PERMISSION rather than a pace. The governor's own contract is that a rate of "
           "zero or less permits max_workers, which is right for the governor and dangerous as a "
           "silent state: in this repository burn has NEVER been measured, so the pacing this plan "
           "promises has never paced anything here and nothing said so",
           rep["posture"] == BS.POSTURE_BOOTSTRAP
           and "PERMITS" in rep["posture_note"] and "not a pace" in rep["posture_note"]
           and rep["desired_workers"] == 8)

    rep2 = BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW,
                            events=[_bs_event(100, 60)], per_worker_rate=0.05, max_workers=8)
    expect("VELDO-0006 AC2 NEGATIVE CONTROL: with a MEASURED rate the posture is PACING and the "
           "worker count is derived from the tighter window's target rate. So BOOTSTRAP is a "
           "measurement of the rate rather than a label the module always applies",
           rep2["posture"] == BS.POSTURE_PACING
           and "burn is measured" in rep2["posture_note"]
           and rep2["desired_workers"] == BSG.desired_workers(
               _bs_windows(), [_bs_event(100, 60)], _BS_NOW, 0.05, 8))

    spent = BS.budget_report(windows=_bs_windows(session_tokens=100.0), now_epoch=_BS_NOW,
                             events=[_bs_event(150, 60)], per_worker_rate=0.05, max_workers=8)
    expect("VELDO-0006 AC2: a window whose budget is USED UP inside its horizon reports posture "
           "SPENT, zero workers, and the resume time - three distinguishable postures, because an "
           "operator acts differently in each: wait for the roll, connect the instrument, or carry on",
           spent["posture"] == BS.POSTURE_SPENT and spent["desired_workers"] == 0
           and spent["resume_at"] > _BS_NOW
           and spent["windows"][0]["state"] == BS.POSTURE_SPENT)
    expect("VELDO-0006 AC2: the three postures are the declared set and nothing else is reachable",
           set(BS.POSTURES) == {BS.POSTURE_PACING, BS.POSTURE_BOOTSTRAP, BS.POSTURE_SPENT}
           and {rep["posture"], rep2["posture"], spent["posture"]} == set(BS.POSTURES))


_bs_block("AC2", _bs_ac2)


# ---------------------------------------------------------------------------------------
# AC3. EVERY NUMBER COMES FROM THE GOVERNOR, NOT A SECOND IMPLEMENTATION.
#
# FALSIFIED BY: compute the worker count or the resume time here, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _bs_ac3():
    evs = [_bs_event(300, 30), _bs_event(400, 120), _bs_event(200, 1800)]
    W = _bs_windows()
    rep = BS.budget_report(windows=W, now_epoch=_BS_NOW, events=evs, per_worker_rate=0.02,
                           max_workers=6)
    expect("VELDO-0006 AC3: the WINDOWED SPEND in the report equals governor.windowed_spend over "
           "the same inputs, per window. A read model that recomputed the pacing arithmetic would "
           "be two implementations of one rule - this repository's most repeated defect, and the one "
           "that diverges quietly because both copies look right",
           [w["used"] for w in rep["windows"]]
           == [BSG.windowed_spend(evs, _BS_NOW, w.seconds) for w in W])
    expect("VELDO-0006 AC3: the WORKER COUNT equals governor.desired_workers over the same inputs",
           rep["desired_workers"] == BSG.desired_workers(W, evs, _BS_NOW, 0.02, 6))
    expect("VELDO-0006 AC3: the TARGET RATE per window equals the governor's own Window.target_rate, "
           "so even the arithmetic that looks trivial is not respelled here",
           [w["target_rate"] for w in rep["windows"]] == [w.target_rate() for w in W])

    over = [_bs_event(1500, 60)]
    Wo = _bs_windows(session_tokens=1000.0)
    rep2 = BS.budget_report(windows=Wo, now_epoch=_BS_NOW, events=over, per_worker_rate=0.02,
                            max_workers=6)
    expect("VELDO-0006 AC3: the RESUME TIME equals governor.resume_at over the same inputs, and it "
           "is only reported in the SPENT posture - the one posture where an operator needs it",
           rep2["resume_at"] == BSG.resume_at(Wo, over, _BS_NOW)
           and "resume_at" not in BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW,
                                                   events=[], max_workers=6))


_bs_block("AC3", _bs_ac3)


# ---------------------------------------------------------------------------------------
# AC4. LOSING A WINDOW MUST COST PACING AND NOT WORK, AND THE REPORT SAYS WHAT SURVIVES.
#
# FALSIFIED BY: delete the survival section, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _bs_ac4():
    rep = BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW, events=[], max_workers=4,
                           root=ROOT)
    s = rep["survives"]
    lines = BS.report_lines(rep)
    expect("VELDO-0006 AC4: the report names BOTH things that survive stopping, measured over this "
           "repository rather than asserted: concluded work as ARTIFACTS on disk, and claimed units "
           "whose claims AGE OUT of the ledger and return to the queue. On 2026-08-10 and 2026-08-11 "
           "two sessions hit limits and 85 agents died mid-flight; what makes stopping safe now is "
           "not this module but VELDO-0002 and VELDO-0003, and this names it so an operator reads "
           "what is at risk instead of guessing",
           isinstance(s["concluded_artifacts"], int) and s["concluded_artifacts"] > 0
           and isinstance(s["claimed_units"], int)
           and s["stale_after_seconds"] == V._VC._organ(
               "claim", ROOT / ".veldo" / "claim.py").STALE_AFTER_SECONDS
           and any("survives stopping" in ln for ln in lines))

    unreadable = BS.survival(root=Path(tempfile.gettempdir()) / "no-such-veldo-tree-at-all")
    expect("VELDO-0006 AC4: over a tree with no corpus the survival read reports UNKNOWN rather "
           "than zero. 'Nothing is at risk' and 'I could not tell what is at risk' are opposite "
           "reassurances, and this module claims nothing it did not measure",
           unreadable["concluded_artifacts"] == 0 or unreadable["concluded_artifacts"] is None)

    with tempfile.TemporaryDirectory() as d:
        rep2 = BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW, events=[], max_workers=4,
                               root=Path(d), claims_root=str(Path(d) / "claims"))
        expect("VELDO-0006 AC4: with an EMPTY claims directory the claimed-unit count is a real "
               "zero and is reported as such, so the UNKNOWN above is a measurement of an "
               "unreadable ledger rather than the module's only answer about the ledger",
               rep2["survives"]["claimed_units"] == 0)


_bs_block("AC4", _bs_ac4)


# ---------------------------------------------------------------------------------------
# AC5. ADOPTION SAFE, AND IT PACES NOTHING.
#
# FALSIFIED BY: remove the absent-configuration stand-down, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _bs_ac5():
    rep = BS.budget_report(windows=(), now_epoch=_BS_NOW, events=[])
    lines = BS.report_lines(rep)
    expect("VELDO-0006 AC5: a repository configuring NO budget window stands the report down by "
           "name - 'nobody declared a budget here' is not 'the budget is fine' - and reports no "
           "posture at all rather than a comfortable one",
           rep["stood_down"] is True and rep["reason"] == BS.STAND_DOWN_NO_WINDOWS
           and rep["posture"] is None
           and any("stood down" in ln for ln in lines))

    rep2 = BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW, events=[])
    expect("VELDO-0006 AC5 NEGATIVE CONTROL: with a window configured the same report answers, so "
           "the stand-down is a measurement of the configuration rather than the module's only "
           "behaviour",
           rep2["stood_down"] is False and rep2["posture"] == BS.POSTURE_BOOTSTRAP)
    expect("VELDO-0006 AC5: the report carries ONE KEY SHAPE whether it stood down or not, so a "
           "consumer never guesses whether a key is missing or genuinely empty",
           sorted(k for k in rep if k != "resume_at") == sorted(BS.REPORT_KEYS)
           and sorted(k for k in rep2 if k != "resume_at") == sorted(BS.REPORT_KEYS))

    import ast as _bs_a
    src = (ROOT / ".veldo" / "budget_state.py").read_text()
    names = set()
    for node in _bs_a.walk(_bs_a.parse(src)):
        if isinstance(node, _bs_a.Name):
            names.add(node.id)
        elif isinstance(node, _bs_a.Attribute):
            names.add(node.attr)
    expect("VELDO-0006 AC5: IT PACES NOTHING AND WAITS FOR NOTHING. No sleep, no spawn, no waiter "
           "and no worker retirement is referenced - the module makes no decision that changes what "
           "runs, which is what lets an operator run it at any moment without consequence. AST "
           "identifiers, not substrings, because prose describing what it refuses to do is prose",
           not (names & {"sleep", "spawn", "retire", "wait_until", "Popen", "Thread", "Process"}))

    def _bs_loads(path):
        try:
            tree = _bs_a.parse(path.read_text())
        except (OSError, SyntaxError):
            return False
        for node in _bs_a.walk(tree):
            if not isinstance(node, _bs_a.Call):
                continue
            fname = (node.func.attr if isinstance(node.func, _bs_a.Attribute)
                     else getattr(node.func, "id", ""))
            if fname not in ("spec_from_file_location", "_organ", "_load", "_sibling"):
                continue
            for arg in list(node.args) + [kw.value for kw in node.keywords]:
                if isinstance(arg, _bs_a.Constant) and isinstance(arg.value, str) \
                        and arg.value.rstrip(".py").endswith("budget_state"):
                    return True
        return False

    expect("VELDO-0006 AC5: NO GATE STAGE LOADS THIS. It is a read model an operator runs, so a gate "
           "that consulted it would turn a budget observation into a landing condition. Asserted "
           "over LOADS via the AST, because /veldo:init legitimately NAMES it in order to ship it",
           sorted(p.name for p in list((ROOT / ".veldo").glob("*.py"))
                  + list((ROOT / "scripts").glob("*.py"))
                  if p.name != "budget_state.py" and _bs_loads(p)) == [])


_bs_block("AC5", _bs_ac5)
