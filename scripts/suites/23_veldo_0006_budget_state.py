"""VELDO-0006: budget continuity on the operator's path.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, which always
runs, so its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 23_veldo_0006_budget_state

WHAT IS UNDER TEST. .veldo/budget_state.py, driven directly, AND the claim that its pacing numbers
come from .veldo/governor.py rather than a second implementation - which is asserted TWO ways,
because one of them cannot fail for the defect the criterion names. Equality against the governor's
own functions catches a copy that DIVERGED. INTERCEPTION - swapping the organ loader for one that
records every call made through the governor, then requiring the report's worker count and resume
time to BE values those calls returned - catches a FAITHFUL copy, which is the one that looks right
until it drifts. An independent review drove AC3's declared mutation (a verbatim copy-paste of
governor.desired_workers / resume_at inside the module) and the whole suite stayed green.

THE EVENT SHAPES ARE THE LIVE ONES. Measured 2026-08-12: the live stream carries 1173 events and
NOT ONE of them has a tokens field. Every fixture here that means "no recorded spend" is therefore
driven BOTH ways: with an empty list, and with events that carry no tokens field at all, because the
second is the shape this repository actually has and the first was the only one asserted.

TIME IS A PARAMETER EVERYWHERE. Every row passes now_epoch explicitly, so no row depends on the wall
clock and none can pass or fail because of when the suite ran. The one exception is the live-claim
fixture in AC4, whose heartbeat must be fresh by claim.py's own contract; it stamps the heartbeat
from the clock deliberately and asserts a COUNT, never a time.

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


def _bs_at(ago_seconds, now=_BS_NOW):
    """A timestamp at a known offset from now, stamped the way the stream stamps them."""
    import datetime as _bs_dt
    return _bs_dt.datetime.fromtimestamp(
        now - ago_seconds, _bs_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bs_event(tokens, ago_seconds, now=_BS_NOW):
    """One spend event at a known offset from now, stamped the way the stream stamps them."""
    return {"schema": "veldo.event/v1", "type": "gate.passed", "tokens": tokens,
            "at": _bs_at(ago_seconds, now)}


def _bs_non_spend_event(ago_seconds, now=_BS_NOW, kind="gate.passed"):
    """AN EVENT WITH NO TOKENS FIELD AT ALL - the only shape the live stream has (measured
    2026-08-12: 1173 events, 0 carrying a tokens field). Not a spend event, and the whole refusal
    this item exists for depends on the module knowing that."""
    return {"schema": "veldo.event/v1", "type": kind, "commit": "deadbeef",
            "at": _bs_at(ago_seconds, now)}


# ---------------------------------------------------------------------------------------
# AC1. NO RECORDED SPEND IS NOT ZERO SPEND.
#
# FALSIFIED BY: treat an empty spend history as zero tokens spent, OR drop the rule that decides
# which events carry a recorded spend, and the rows below must go red.
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

    # THE SHAPE THE LIVE STREAM ACTUALLY HAS, which no row exercised before. An empty list is not
    # the case this repository is in: it has 1173 events and none of them is a spend.
    nonspend = [_bs_non_spend_event(60), _bs_non_spend_event(1200)]
    repn = BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW, events=nonspend,
                            per_worker_rate=1.0, max_workers=8)
    linesn = BS.report_lines(repn)
    expect("VELDO-0006 AC1: EVENTS THAT ARE NOT SPEND EVENTS DO NOT MAKE A WINDOW MEASURED. Two "
           "gate.passed events inside the session horizon carrying NO tokens field - the ONLY shape "
           "the live stream has, measured 2026-08-12 at 1173 events and zero with a tokens field - "
           "leave every window UNMEASURED with no used and no remaining figure and the spend count "
           "at zero. The rule that separates a spend reading from any other event is the whole of "
           "what stands between this stream and 'the entire budget remains', and it is the "
           "governor's own rule rather than a second spelling of it",
           len(nonspend) == 2 and all("tokens" not in e for e in nonspend)
           and repn["spend_events"] == 0
           and all(w["state"] == BS.UNMEASURED for w in repn["windows"])
           and all(w["used"] is None and w["remaining"] is None for w in repn["windows"])
           and all(w["recorded_events_in_horizon"] == 0 for w in repn["windows"])
           and not any("remaining, from" in ln for ln in linesn))

    mixed = [_bs_non_spend_event(30), _bs_event(250, 60), _bs_non_spend_event(90)]
    repm = BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW, events=mixed,
                            per_worker_rate=1.0, max_workers=8)
    expect("VELDO-0006 AC1 NEGATIVE CONTROL: ADD one spend event to those two non-spend events and "
           "the same window measures it - one recorded event in the horizon out of three events, "
           "the spend total from the spend alone. So UNMEASURED is a measurement of the stream and "
           "the count is a count of READINGS rather than of events",
           len(mixed) == 3 and repm["spend_events"] == 1
           and repm["windows"][0]["recorded_events_in_horizon"] == 1
           and repm["windows"][0]["state"] == BS.MEASURED
           and repm["windows"][0]["used"] == 250.0
           and repm["windows"][0]["remaining"] == 750.0)

    rep2 = BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW,
                            events=[_bs_event(250, 60)], per_worker_rate=1.0, max_workers=8)
    session = rep2["windows"][0]
    expect("VELDO-0006 AC1 NEGATIVE CONTROL: with ONE recorded spend event inside the horizon the "
           "same window reports a REAL used and remaining figure, so UNMEASURED is a measurement of "
           "the stream rather than this module's only answer. The two fixtures differ by exactly one "
           "event",
           session["state"] == BS.MEASURED and session["used"] == 250.0
           and session["remaining"] == 750.0
           and session["recorded_events_in_horizon"] == 1)

    rep3 = BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW,
                            events=[_bs_event(250, 7200)], per_worker_rate=1.0, max_workers=8)
    expect("VELDO-0006 AC1: an event OUTSIDE the trailing horizon leaves that window UNMEASURED "
           "while the longer window measures it - the horizon is what decides, per window, so a "
           "spend from two hours ago cannot make a one-hour window look measured",
           rep3["windows"][0]["state"] == BS.UNMEASURED
           and rep3["windows"][1]["state"] == BS.MEASURED
           and rep3["windows"][1]["used"] == 250.0)

    # THE TAXONOMY'S OTHER HALF: a window with spend totalling zero is distinct from UNMEASURED and
    # is not "budget available" either. Reachable through the sanctioned writer: events.py takes
    # --tokens 0.
    repz = BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW, events=[_bs_event(0, 60)],
                            per_worker_rate=1.0, max_workers=8)
    zwin = repz["windows"][0]
    linesz = BS.report_lines(repz)
    expect("VELDO-0006 AC1: A RECORDED SPEND TOTALLING ZERO IS NOT AVAILABLE BUDGET EITHER, and it "
           "is not UNMEASURED. The declared taxonomy keeps them distinct because they mean "
           "different things: one stream was never instrumented, the other is connected and "
           "measured no consumption, which is an idle window OR a miscounting instrument. So the "
           "state is ZERO_RECORDED, the reading is counted, and no remaining figure is quoted",
           zwin["state"] == BS.ZERO_RECORDED and BS.ZERO_RECORDED != BS.UNMEASURED
           and zwin["recorded_events_in_horizon"] == 1 and zwin["used"] == 0
           and zwin["remaining"] is None
           and any("ZERO_RECORDED" in ln and "not a remaining figure" in ln for ln in linesz)
           and not any("1000 remaining" in ln for ln in linesz))


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
           and rep2["rate_corroborated"] is True and rep2["rate_used"] == 0.05
           and rep2["desired_workers"] == BSG.desired_workers(
               _bs_windows(), [_bs_event(100, 60)], _BS_NOW, 0.05, 8))

    # THE POSTURE MAY NOT CONTRADICT THE WINDOWS IN THE SAME REPORT. The rate is the CALLER's
    # argument; the stream is the evidence for it.
    supplied = BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW,
                                events=[_bs_non_spend_event(60)], per_worker_rate=1.0,
                                max_workers=8)
    slines = BS.report_lines(supplied)
    expect("VELDO-0006 AC2: A RATE THE STREAM DOES NOT CORROBORATE IS NOT A MEASUREMENT. The rate "
           "arrives as an argument this module never measured, so a caller passing 1.0 over a "
           "stream with no reading inside any horizon used to get 'burn is measured at 1.0 tokens "
           "per worker per second' printed directly above 'UNMEASURED - no recorded spend inside "
           "the horizon'. The posture stays BOOTSTRAP, the rate handed to the governor is the "
           "honest 0.0, the supplied number is named as uncorroborated, and NO line claims burn is "
           "measured",
           supplied["posture"] == BS.POSTURE_BOOTSTRAP
           and supplied["per_worker_rate"] == 1.0
           and supplied["rate_corroborated"] is False and supplied["rate_used"] == 0.0
           and BS.RATE_UNCORROBORATED in supplied["posture_note"]
           and "supplied: 1.0" in supplied["posture_note"]
           and not any("burn is measured" in ln for ln in slines)
           and supplied["desired_workers"] == BSG.desired_workers(
               _bs_windows(), [_bs_non_spend_event(60)], _BS_NOW, 0.0, 8))

    # THE SAME CONTRADICTION THROUGH THE TAXONOMY'S OTHER DOOR. Requiring only that a reading EXIST
    # inside a horizon left the zero-total window corroborating a positive rate.
    zero_reading = [_bs_event(0, 60)]
    zr = BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW, events=zero_reading,
                          per_worker_rate=1.0, max_workers=8)
    zlines = BS.report_lines(zr)
    neg = BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW,
                           events=[_bs_event(-100, 60)], per_worker_rate=1.0, max_workers=8)
    expect("VELDO-0006 AC2: A RECORDED TOTAL OF NO MORE THAN ZERO CORROBORATES NO BURN RATE. The "
           "evidence for a positive rate is a TOTAL, not a count of readings: with the count as the "
           "test, ONE reading of zero tokens inside the horizon printed 'burn is measured at 1.0 "
           "tokens per worker per second' directly above 'ZERO_RECORDED - 1 recorded event(s) "
           "inside the horizon total ZERO tokens', and paced the worker count off it - 1 worker "
           "where the governor's own bootstrap answer for that stream is 8. The condition is the "
           "governor's own: measure_per_worker_rate is the windowed spend over the horizon and the "
           "worker count, so it CANNOT have produced a positive rate from this stream, and the rate "
           "handed to the governor is that same 0.0. A negative recorded total is the same case",
           zr["windows"][0]["state"] == BS.ZERO_RECORDED
           and zr["rate_corroborated"] is False and zr["rate_used"] == 0.0
           and zr["posture"] == BS.POSTURE_BOOTSTRAP
           and not any("burn is measured" in ln for ln in zlines)
           and BS.RATE_UNCORROBORATED in zr["posture_note"]
           and BSG.measure_per_worker_rate(zero_reading, _BS_NOW, 3600, 8) == 0.0
           and zr["desired_workers"] == BSG.desired_workers(
               _bs_windows(), zero_reading, _BS_NOW, 0.0, 8)
           and zr["desired_workers"] != BSG.desired_workers(
               _bs_windows(), zero_reading, _BS_NOW, 1.0, 8)
           and neg["windows"][0]["state"] == BS.ZERO_RECORDED
           and neg["rate_corroborated"] is False
           and neg["posture"] == BS.POSTURE_BOOTSTRAP)

    both = zero_reading + [_bs_event(250, 60)]
    corr = BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW, events=both,
                            per_worker_rate=1.0, max_workers=8)
    clines = BS.report_lines(corr)
    expect("VELDO-0006 AC2 NEGATIVE CONTROL: ADD one reading carrying real burn to that same zero "
           "reading and the same call corroborates the supplied rate - posture PACING, the rate "
           "used is the number handed in, and the report does say burn is measured. The two "
           "fixtures differ by exactly one ADDED event, so the refusal above is a measurement of "
           "the recorded total rather than this module's answer to any stream that carries a rate",
           len(both) == len(zero_reading) + 1
           and corr["windows"][0]["state"] == BS.MEASURED
           and corr["windows"][0]["used"] == 250.0
           and corr["rate_corroborated"] is True and corr["rate_used"] == 1.0
           and corr["posture"] == BS.POSTURE_PACING
           and any("burn is measured" in ln for ln in clines))

    # WHY IT IS BOOTSTRAPPING IS DERIVED FROM THE WINDOWS. The branch that read `if not spends`
    # told an operator with a reading INSIDE a horizon that no window held one.
    unpaced = BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW,
                              events=[_bs_event(250, 60)], per_worker_rate=0.0, max_workers=8)
    notes = {BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW,
                              events=[])["posture_note"],
             BS.budget_report(windows=_bs_windows()[:1], now_epoch=_BS_NOW,
                              events=[_bs_event(250, 7200)])["posture_note"],
             zr["posture_note"], unpaced["posture_note"]}
    expect("VELDO-0006 AC2: THE BOOTSTRAP REASON IS DERIVED FROM THE WINDOWS RATHER THAN FROM ONE "
           "COUNT STANDING IN FOR FOUR STATES. A stream carrying real burn inside the horizon with "
           "no rate supplied to pace with bootstraps for a different reason than an uninstrumented "
           "one, and the note told that operator the windows held 'none of them inside its horizon' "
           "while the row underneath reported 250 of 1000 used. Each state names what it measured, "
           "and the four bootstrap reasons are four distinct sentences",
           unpaced["posture"] == BS.POSTURE_BOOTSTRAP
           and unpaced["windows"][0]["state"] == BS.MEASURED
           and unpaced["windows"][0]["used"] == 250.0
           and "no positive per-worker rate" in unpaced["posture_note"]
           and "none of them" not in unpaced["posture_note"]
           and "NOT ONE event" not in unpaced["posture_note"]
           and "ZERO_RECORDED" not in unpaced["posture_note"]
           and len(notes) == 4)

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
# AC3. NO SECOND IMPLEMENTATION OF THE PACING RULES.
#
# FALSIFIED BY: compute the worker count or the resume time here - EVEN AS A FAITHFUL COPY of the
# governor's arithmetic - and the interception rows below must go red.
# ---------------------------------------------------------------------------------------


def _bs_gov_spy():
    """(install, restore, calls): budget_state's organ loader, wrapped so every call made THROUGH
    the governor is recorded as {function: [returned values]}.

    THIS IS WHAT EQUALITY CANNOT DO. Equality against BSG.desired_workers is satisfied by a
    faithful copy-paste inside budget_state, which is precisely the duplication AC3 calls the
    defect ('both copies look right'). Recording the calls asks the other question: was the number
    in the report PRODUCED BY the governor, or merely equal to what the governor would have said."""
    calls = {}
    real = BS._organ
    paced = ("desired_workers", "resume_at", "windowed_spend", "measure_per_worker_rate")

    class _BSSpy:
        def __init__(self, mod):
            self._mod = mod

        def __getattr__(self, name):
            attr = getattr(self._mod, name)
            if name not in paced:
                return attr

            def _recorded(*a, **k):
                out = attr(*a, **k)
                calls.setdefault(name, []).append(out)
                return out
            return _recorded

    def _install():
        BS._organ = lambda name: (_BSSpy(real(name)) if name == "governor" else real(name))

    def _restore():
        BS._organ = real
    return _install, _restore, calls


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
           "is present ONLY in the SPENT posture - the one posture where an operator needs it - "
           "while staying a declared key with a None value everywhere else, so a consumer reading "
           "it never meets a KeyError",
           rep2["resume_at"] == BSG.resume_at(Wo, over, _BS_NOW)
           and BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW,
                                events=[], max_workers=6)["resume_at"] is None)

    # INTERCEPTION. The declared falsification is a SECOND IMPLEMENTATION, faithful or not, and
    # equality cannot see a faithful one. These two rows can.
    install, restore, calls = _bs_gov_spy()
    install()
    try:
        spent = BS.budget_report(windows=Wo, now_epoch=_BS_NOW, events=over, per_worker_rate=0.02,
                                 max_workers=6)
    finally:
        restore()
    expect("VELDO-0006 AC3: the WORKER COUNT is not merely EQUAL to governor.desired_workers, it IS "
           "a value that function returned when this report was built - proved by recording every "
           "call made through the governor. This is the row AC3's own declared mutation must red: a "
           "faithful copy-paste of the governor's arithmetic inside this module satisfies equality "
           "and records no call at all",
           bool(calls.get("desired_workers"))
           and spent["desired_workers"] in calls["desired_workers"])
    expect("VELDO-0006 AC3: the RESUME TIME is likewise a value governor.resume_at returned on this "
           "call, not a number computed here that happens to agree. Two implementations of one rule "
           "look right until they drift, and the drift is what nobody sees",
           bool(calls.get("resume_at")) and spent["resume_at"] in calls["resume_at"])
    expect("VELDO-0006 AC3: THE HORIZON CUT IS THE GOVERNOR'S TOO. Counting the readings inside a "
           "window is windowed_spend asked a different question rather than a local `t >= now - "
           "seconds`, so the governor's own function is called at least twice per window and the "
           "recorded-event counts are what those calls returned",
           len(calls.get("windowed_spend", [])) >= 2 * len(Wo)
           and [w["recorded_events_in_horizon"] for w in spent["windows"]] == [1, 1])
    install2, restore2, calls2 = _bs_gov_spy()
    install2()
    try:
        boot = BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW, events=[], max_workers=6)
    finally:
        restore2()
    expect("VELDO-0006 AC3 NEGATIVE CONTROL: the interception measures THIS module's calls and is "
           "not an always-true observation about the recorder - over a report that never reaches "
           "the SPENT posture the same recorder sees no resume_at call at all, while still seeing "
           "the windowed spend and the worker count. So a recorded call is evidence about the code "
           "path that ran",
           boot["resume_at"] is None and not calls2.get("resume_at")
           and bool(calls2.get("windowed_spend")) and bool(calls2.get("desired_workers")))

    # WHAT IS DERIVED HERE IS NAMED, so the criterion's own text is true of the code. `remaining`
    # is the window's budget minus the governor's used, and the state and posture labels are this
    # module's presentation. None of them is pacing arithmetic.
    expect("VELDO-0006 AC3: the figures this module DERIVES are named and are exactly the "
           "presentation ones - what remains against a window's budget is its tokens minus the "
           "governor's used, and nothing else here does arithmetic the governor also does",
           [w["remaining"] for w in rep["windows"]]
           == [max(0.0, w.tokens - BSG.windowed_spend(evs, _BS_NOW, w.seconds)) for w in W])


_bs_block("AC3", _bs_ac3)


# ---------------------------------------------------------------------------------------
# AC4. LOSING A WINDOW MUST COST PACING AND NOT WORK, AND THE REPORT SAYS WHAT SURVIVES.
#
# FALSIFIED BY: delete the survival section, and the first row below must go red. Report an
# unreadable half as zero, and the UNKNOWN rows below must go red.
# ---------------------------------------------------------------------------------------


def _bs_organ_raiser(organ_name, read_name, exc):
    """(install, restore): budget_state's organ loader, wrapped so ONE named read on ONE organ
    raises and everything else passes through.

    WHY THIS SEAM EXISTS. The declared taxonomy names an UNREADABLE half as UNKNOWN, and the two
    unreadable shapes are not reachable by choosing a path: `claim.claimed_units` answers an EMPTY
    SET for an absent claims directory by its own contract, which is a real zero and not a failure,
    and a corpus root that is absent takes the module's other branch. So both except paths stayed
    unasserted, and turning them into `= 0` with the reason dropped left this suite at 58 passed, 0
    failed. The read is captured PER SHAPE, per ledger finding 67: the failure is injected at the
    ONE call that fails, so a report that answers a confident zero reds the row that names that
    shape rather than shortening the run."""
    real = BS._organ

    class _BSBoom:
        def __init__(self, mod):
            self._mod = mod

        def __getattr__(self, name):
            attr = getattr(self._mod, name)
            if name != read_name:
                return attr

            def _raise(*a, **k):
                raise exc
            return _raise

    def _install():
        BS._organ = lambda name: (_BSBoom(real(name)) if name == organ_name else real(name))

    def _restore():
        BS._organ = real
    return _install, _restore


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
           "what is at risk instead of guessing. Asserted as SHAPE and never as today's counts: a "
           "row pinning the corpus size reddens on the first day the corpus changes",
           isinstance(s["concluded_artifacts"], int) and s["concluded_artifacts"] >= 0
           and isinstance(s["claimed_units"], int) and s["claimed_units"] >= 0
           and s["stale_after_seconds"] == V._VC._organ(
               "claim", ROOT / ".veldo" / "claim.py").STALE_AFTER_SECONDS
           and any("survives stopping" in ln for ln in lines)
           and rep["at_risk"] == [])

    with tempfile.TemporaryDirectory() as d:
        absent = Path(d) / "tree-that-was-never-created"
        unreadable = BS.survival(root=absent)
        rep2 = BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW, events=[], max_workers=4,
                                root=absent)
        lines2 = BS.report_lines(rep2)
        expect("VELDO-0006 AC4: over a tree with no corpus the survival read reports UNKNOWN rather "
               "than zero, FOR BOTH HALVES, and the report LINE says UNKNOWN and lists the risk it "
               "could not measure. 'Nothing is at risk' and 'I could not tell what is at risk' are "
               "opposite reassurances, and a confident zero here is the exact sentence this item "
               "exists to refuse. The row this replaces accepted `== 0 or is None`, so it accepted "
               "the defect it was written to catch",
               unreadable["concluded_artifacts"] is None
               and unreadable["claimed_units"] is None
               and BS.ARTIFACTS_UNKNOWN in (unreadable["artifacts"] or "")
               and any("UNKNOWN concluded artifact set(s)" in ln for ln in lines2)
               and any("UNKNOWN claimed unit(s)" in ln for ln in lines2)
               and len(rep2["at_risk"]) == 2)

        # NEGATIVE CONTROL, ADDITIVE: build the corpus and the ledger this read looks for, and the
        # same call answers with real counts. So UNKNOWN is a measurement of what was readable.
        tree = Path(d) / "tree"
        (tree / "proof" / "VELDO-9999").mkdir(parents=True)
        # THE VERDICT CARRIES A PASSING VALUE, and it has to. This fixture wrote a verdict with a
        # schema and NO verdict field, which counted as concluded while `concluded()` only checked
        # that a verdict FILE existed. VELDO-0002's remediation made it read what the verdict SAYS,
        # so a bundle whose verdict states nothing is correctly no longer concluded and this fixture
        # measured 0 where it asserts 1. The row's SUBJECT is a real concluded bundle producing a real
        # count, so the fixture is what was wrong, not the assertion: it now writes what a concluded
        # bundle actually looks like. Measured both ways at integration: no verdict value gives 0, a
        # `pass` gives 1.
        (tree / "proof" / "VELDO-9999" / "verdict.json").write_text(
            '{"schema": "veldo.verdict/v1", "verdict": "pass"}')
        (tree / "proof" / "VELDO-9999" / "manifest.json").write_text('{"schema": "veldo.proof/v1"}')
        (tree / "claims").mkdir()
        built = BS.survival(root=tree, claims_root=str(tree))
        expect("VELDO-0006 AC4 NEGATIVE CONTROL: with ONE concluded bundle on disk and an empty "
               "claims directory the same read answers 1 and 0 - a real zero for the ledger, "
               "reported as zero. So the UNKNOWN above is a measurement of an unreadable half "
               "rather than this module's only answer, and the two controls differ by what EXISTS "
               "rather than by which path was passed",
               built["concluded_artifacts"] == 1 and built["artifacts"] is None
               and built["claimed_units"] == 0 and built["ledger"] is None
               and built["claims_root"] == str(tree / "claims"))

        import datetime as _bs_dt
        import json as _bs_json
        (tree / "claims" / "VELDO-9999.json").write_text(_bs_json.dumps(
            {"unit_id": "VELDO-9999", "holder": "veldo-0006-suite",
             "heartbeat_at": _bs_dt.datetime.now(_bs_dt.timezone.utc).strftime(
                 "%Y-%m-%dT%H:%M:%SZ")}))
        claimed = BS.survival(root=tree, claims_root=str(tree))
        expect("VELDO-0006 AC4 NEGATIVE CONTROL: ADD one live claim to that ledger and the count "
               "follows it, so the claimed-unit figure is read from the ledger rather than "
               "defaulted. This is the half an operator needs before stopping: those units return "
               "to the queue when the claim ages out",
               claimed["claimed_units"] == 1
               and claimed["stale_after_seconds"] == built["stale_after_seconds"])

        # AN UNREADABLE HALF, WHICH IS THE TAXONOMY'S OTHER UNKNOWN AND WAS THE UNASSERTED ONE.
        # "An absent corpus root" and "a ledger belonging to another tree" are driven above by
        # choosing a path; "an unreadable ledger" and an unreadable corpus cannot be, so the read is
        # made to fail at the one call that fails and each shape gets its own row.
        install, restore = _bs_organ_raiser("work_state", "work_report",
                                           OSError("corpus read refused"))
        install()
        try:
            unread_a = BS.survival(root=ROOT)
            rep_a = BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW, events=[],
                                     max_workers=4, root=ROOT)
        finally:
            restore()
        lines_a = BS.report_lines(rep_a)
        expect("VELDO-0006 AC4: AN UNREADABLE CORPUS IS UNKNOWN WITH THE REASON CARRIED, not zero "
               "concluded artifacts. The read is made to fail at the one call that reads the corpus, "
               "so this row is about the module's own refusal path rather than about a chosen path: "
               "the count is None, the reason names the cause, the report LINE says UNKNOWN, the risk "
               "is listed, and the ledger half - which read fine - still answers a number. Setting "
               "this branch to `= 0` with the reason dropped left the whole suite green",
               unread_a["concluded_artifacts"] is None
               and BS.ARTIFACTS_UNKNOWN in (unread_a["artifacts"] or "")
               and "corpus read refused" in (unread_a["artifacts"] or "")
               and any("UNKNOWN concluded artifact set(s)" in ln for ln in lines_a)
               and any(BS.ARTIFACTS_UNKNOWN in r for r in rep_a["at_risk"])
               and isinstance(unread_a["claimed_units"], int))

        install, restore = _bs_organ_raiser("claim", "claimed_units",
                                           OSError("ledger read refused"))
        install()
        try:
            unread_l = BS.survival(root=ROOT)
            rep_l = BS.budget_report(windows=_bs_windows(), now_epoch=_BS_NOW, events=[],
                                     max_workers=4, root=ROOT)
        finally:
            restore()
        lines_l = BS.report_lines(rep_l)
        expect("VELDO-0006 AC4: AN UNREADABLE LEDGER IS UNKNOWN WITH THE REASON CARRIED, not nothing "
               "at risk - the second half of the declared taxonomy and the one no row reached, "
               "because the ledger answers an EMPTY SET for an absent claims directory by its own "
               "contract and that is a real zero. What it did read before the failure is kept, so "
               "the stale-after window is still reported while the count is UNKNOWN, and the "
               "artifact half still answers a number",
               unread_l["claimed_units"] is None
               and BS.LEDGER_UNKNOWN in (unread_l["ledger"] or "")
               and "ledger read refused" in (unread_l["ledger"] or "")
               and unread_l["stale_after_seconds"] is not None
               and any("UNKNOWN claimed unit(s)" in ln for ln in lines_l)
               and any(BS.LEDGER_UNKNOWN in r for r in rep_l["at_risk"])
               and isinstance(unread_l["concluded_artifacts"], int))

        after = BS.survival(root=ROOT)
        expect("VELDO-0006 AC4 NEGATIVE CONTROL: the injected failure is what those two rows "
               "measured, and it was really applied. The SAME call with no injection answers an "
               "integer for both halves and names no risk, so UNKNOWN above is a measurement of a "
               "read that failed rather than an artefact of the seam, and the loader the suite "
               "restored is the module's own",
               isinstance(after["concluded_artifacts"], int)
               and isinstance(after["claimed_units"], int)
               and after["artifacts"] is None and after["ledger"] is None
               and BS._organ("claim").STALE_AFTER_SECONDS == after["stale_after_seconds"])

        foreign = BS.survival(root=tree)
        expect("VELDO-0006 AC4: A SURVIVAL REPORT ABOUT ANOTHER TREE DOES NOT QUOTE THIS PROCESS'S "
               "LEDGER. claim.claims_root resolves from the running process, so with no claims root "
               "given for that tree the honest answer is UNKNOWN with the reason named - not this "
               "tree's live claims presented as that one's risk. The artifact half, which does "
               "honour the root, still answers",
               foreign["claimed_units"] is None
               and foreign["ledger"] == BS.LEDGER_FOREIGN_TREE
               and foreign["concluded_artifacts"] == 1
               and foreign["stale_after_seconds"] == built["stale_after_seconds"])


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
    expect("VELDO-0006 AC5: the report carries ONE KEY SHAPE whether it stood down or not, with NO "
           "exception for any posture-dependent key, so a consumer never guesses whether a key is "
           "missing or genuinely empty. The version of this row that excluded resume_at from both "
           "sides was asserting the claim with the counter-example carved out",
           sorted(rep) == sorted(BS.REPORT_KEYS) and sorted(rep2) == sorted(BS.REPORT_KEYS)
           and "resume_at" in BS.REPORT_KEYS)

    import ast as _bs_a
    src = (ROOT / ".veldo" / "budget_state.py").read_text()
    tree = _bs_a.parse(src)
    local = {n.name for n in _bs_a.walk(tree)
             if isinstance(n, (_bs_a.FunctionDef, _bs_a.AsyncFunctionDef, _bs_a.ClassDef))}
    called = set()
    for node in _bs_a.walk(tree):
        if isinstance(node, _bs_a.Call):
            f = node.func
            called.add(f.attr if isinstance(f, _bs_a.Attribute) else getattr(f, "id", "?"))
    imported = set()
    for node in _bs_a.walk(tree):
        if isinstance(node, _bs_a.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, _bs_a.ImportFrom):
            imported.add((node.module or "").split(".")[0])

    # AN ALLOWLIST, NOT A DENYLIST. The row this replaces proved an absence with a fixed deny-list
    # of {sleep, spawn, retire, wait_until, Popen, Thread, Process}, and a review added
    # subprocess.run(['/bin/sleep', ...]) plus os.system(...) while the suite stayed green: the two
    # most ordinary spellings of spawning and waiting were not on the list. A denylist of names is a
    # promise that whoever adds the next one is on it. This fails CLOSED instead: every call in the
    # module resolves to a function defined IN the module or to a name declared here, and every
    # import is declared here, so a new external call or import reds this row until someone states
    # why it belongs in a read model that must be safe to run at any moment.
    allowed_calls = {
        # builtins a read model may use
        "all", "any", "dict", "int", "isinstance", "len", "list", "max", "min", "sorted", "str",
        "sum", "float", "bool",
        # the organ loader, spelled once in _organ
        "spec_from_file_location", "module_from_spec", "exec_module",
        # reading a path and a JSON line
        "Path", "read_text", "is_file", "is_dir", "resolve", "splitlines", "strip", "loads",
        "append", "get",
        # THE GOVERNOR'S OWN FUNCTIONS - the only pacing arithmetic this module may use
        "windowed_spend", "desired_workers", "resume_at", "target_rate", "_tokens_at",
        # the two organs the survival read consults
        "work_report", "claimed_units", "claims_root",
    }
    allowed_imports = {"importlib", "json", "pathlib"}
    stray_calls = sorted(called - allowed_calls - local)
    stray_imports = sorted(imported - allowed_imports)
    expect("VELDO-0006 AC5: IT PACES NOTHING AND WAITS FOR NOTHING, proved by an ALLOWLIST that "
           "fails closed rather than a denylist of the spellings someone thought of. Every call in "
           "the module is either a function defined in it or one of the declared names - the "
           "loader, a path read, a JSON parse, or one of the governor's own pacing functions - and "
           "every import is declared. subprocess.run and os.system are not on the list, and neither "
           "is anything else that could change what runs. Stray calls %r, stray imports %r"
           % (stray_calls, stray_imports),
           stray_calls == [] and stray_imports == []
           and not (called & {"sleep", "spawn", "retire", "wait_until", "Popen", "Thread",
                              "Process", "run", "system", "fork", "call", "check_output"})
           and len(allowed_calls & called) >= 8)

    def _bs_loads_budget_state(path):
        """Whether one stage LOADS the read model, which is NOT the same as naming it: /veldo:init
        legitimately lists .veldo/budget_state.py among the files it ships, and a check that read
        the name as a load would refuse the module being installed at all. So a python stage is read
        through the AST - a literal naming the module passed to a loader call - and a shell stage is
        read as text, because a shell stage's only way to reach it is to run it."""
        import re as _bs_re
        try:
            text = path.read_text(errors="replace")
        except OSError:
            return False
        if path.suffix != ".py":
            return bool(_bs_re.search(r"budget_state", text))
        try:
            tree_ = _bs_a.parse(text)
        except SyntaxError:
            return False
        for node in _bs_a.walk(tree_):
            if not isinstance(node, _bs_a.Call):
                continue
            fname = (node.func.attr if isinstance(node.func, _bs_a.Attribute)
                     else getattr(node.func, "id", ""))
            if fname not in ("spec_from_file_location", "_organ", "_load", "_sibling",
                             "import_module", "module_from_spec"):
                continue
            for arg in list(node.args) + [kw.value for kw in node.keywords]:
                if isinstance(arg, _bs_a.Constant) and isinstance(arg.value, str) \
                        and arg.value.rstrip(".py").endswith("budget_state"):
                    return True
        return False

    def _bs_stage_path(tok):
        """ONE resolver for a path token a stage names, used by BOTH the gate-stage derivation and
        the transitive walk, because two spellings of one rule diverge.

        A single leading './' is stripped as a relative-path PREFIX and nothing else is, which is
        the whole point of the function existing. The version this replaces wrote
        `tok.lstrip('./')`, which strips CHARACTERS rather than a prefix, so every `.veldo/...`
        token lost its leading dot, resolved to a `veldo/...` path that is not a file, and was
        dropped: all four .veldo stages the gate runs were silently absent from the set the row
        below claims to walk, and a load added to `.veldo/validate.py` reddened nothing. Returns
        None for a token that is not a file in this repository, so a token naming something outside
        the tree is not adopted as a stage."""
        rel = tok[2:] if tok.startswith("./") else tok
        p = (ROOT / rel).resolve()
        return p if p.is_file() and str(p).startswith(str(ROOT.resolve())) else None

    def _bs_names(path):
        """The sibling scripts and organs one script NAMES: a literal path token that resolves to a
        file in this repository, or an organ loaded by bare name. Both spellings, because .veldo
        modules are loaded by name and scripts are named by path."""
        import re as _bs_re
        try:
            text = path.read_text(errors="replace")
        except OSError:
            return set()
        out = set()
        for tok in _bs_re.findall(r"[A-Za-z0-9_./-]+\.(?:py|sh)", text):
            p = _bs_stage_path(tok)
            if p is not None:
                out.add(p)
        for name in _bs_re.findall(r"(?:_organ|_sibling|_load)\(\s*[\"']([A-Za-z0-9_]+)[\"']", text):
            p = (ROOT / ".veldo" / (name + ".py")).resolve()
            if p.is_file():
                out.add(p)
        return out

    # THE PROPERTY IS ABOUT GATE STAGES, so the set walked is derived from the gate itself. The row
    # this replaces scanned EVERY .veldo/*.py and scripts/*.py and required the result to be empty,
    # which pins this repository's current emptiness as an invariant: a reviewer added a 24-line
    # operator console that only prints report_lines and the row went red, so the check reddened for
    # the first person to put the read model on the operator's path the spec title names. That is the
    # defect class scripts/check_first_use.py exists to forbid.
    import re as _bs_re
    gate = (ROOT / "scripts" / "verify.sh").read_text()
    stages = set()
    for tok in _bs_re.findall(r"[A-Za-z0-9_./-]+\.(?:py|sh)", gate):
        p = _bs_stage_path(tok)
        if p is not None:
            stages.add(p)
    closure, frontier = set(stages), set(stages)
    while frontier:
        nxt = set()
        for p in frontier:
            # A SUITE IS THE TEST OF A MODULE, NOT A CONSUMER OF IT: the unit stage's fragments load
            # what they assert over, and one that could not load its subject could not test it. So
            # the walk does not follow into scripts/suites, and says so rather than pretending the
            # gate never reaches them.
            if "suites" in p.parts:
                continue
            nxt |= _bs_names(p)
        frontier = nxt - closure
        closure |= frontier
    loaders = sorted(p.name for p in closure
                     if p.name != "budget_state.py" and _bs_loads_budget_state(p))
    expect("VELDO-0006 AC5: NO GATE STAGE LOADS THIS. It is a read model an operator runs, so a "
           "gate that consulted it would turn a budget observation into a landing condition. "
           "Derived from scripts/verify.sh itself and walked transitively through the stages it "
           "runs, rather than by sweeping the repository and requiring today's emptiness: putting "
           "the read model on an operator's path is the point of the item and must not redden the "
           "gate. AND THE SET REACHES THE GATE'S .veldo STAGES, because a derivation that resolves "
           "only the scripts/ half is not walking the gate however precisely the row is worded: "
           "four .veldo stages were silently missing while this row was green. Loaders found among "
           "the gate's own stages: %r" % (loaders,),
           loaders == [] and len(stages) >= 5 and len(closure) >= 10
           and any(p.parent.name == ".veldo" for p in stages)
           and any(p.parent.name == "scripts" for p in stages))

    with tempfile.TemporaryDirectory() as d:
        outside = Path(d) / "outside_stage.py"
        outside.write_text("import importlib.util\n"
                           "m = importlib.util.spec_from_file_location('x', "
                           "'.veldo/budget_state.py')\n")
        expect("VELDO-0006 AC5 NEGATIVE CONTROL: the resolver behind that set does not drop a "
               "spelling the gate actually uses. Driven on the three token shapes scripts/verify.sh "
               "contains - a '.veldo/...' path whose leading dot a character-stripping lstrip ate, a "
               "'./scripts/...' path, and the same path bare - and on a real file OUTSIDE the tree, "
               "which is refused rather than adopted as a stage even though it exists and does load "
               "the module. This is the row that would have caught the derivation walking eight "
               "stages while claiming to walk the gate",
               _bs_stage_path(".veldo/validate.py")
               == (ROOT / ".veldo" / "validate.py").resolve()
               and _bs_stage_path("./scripts/selftest.py")
               == (ROOT / "scripts" / "selftest.py").resolve()
               and _bs_stage_path("scripts/selftest.py")
               == (ROOT / "scripts" / "selftest.py").resolve()
               and outside.is_file() and _bs_loads_budget_state(outside)
               and _bs_stage_path(str(outside)) is None)

    with tempfile.TemporaryDirectory() as d:
        probe = Path(d) / "probe_stage.py"
        probe.write_text("import importlib.util\n"
                         "m = importlib.util.spec_from_file_location('x', '.veldo/budget_state.py')\n")
        organ_probe = Path(d) / "probe_organ.py"
        organ_probe.write_text('def go():\n    return _organ("budget_state")\n')
        shell_probe = Path(d) / "probe_stage.sh"
        shell_probe.write_text("#!/usr/bin/env bash\npython3 .veldo/budget_state.py\n")
        names_probe = Path(d) / "probe_names_only.py"
        names_probe.write_text('SHIPPED = [".veldo/budget_state.py", ".veldo/governor.py"]\n')
        expect("VELDO-0006 AC5 NEGATIVE CONTROL: the detector REPORTS a load when there is one, in "
               "all three spellings a stage could use - a literal module path, an organ load by "
               "name, and a shell stage running the file - proved on synthetic stages rather than on "
               "the repository, so the green row above is not green because the walker cannot see "
               "anything. And it does NOT report a stage that merely NAMES the module in a list of "
               "files, because /veldo:init does exactly that in order to ship it",
               _bs_loads_budget_state(probe) and _bs_loads_budget_state(organ_probe)
               and _bs_loads_budget_state(shell_probe)
               and not _bs_loads_budget_state(names_probe)
               and (ROOT / ".veldo" / "budget_state.py").resolve() in _bs_names(organ_probe))


_bs_block("AC5", _bs_ac5)
