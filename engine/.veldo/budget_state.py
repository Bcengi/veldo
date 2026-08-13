#!/usr/bin/env python3
"""VELDO budget state: where the budget stands on the path an operator actually takes.

WHAT THIS EXISTS TO REFUSE TO SAY. Measured on 2026-08-12: this repository's event stream carries
ZERO events with a spend field. So the governor's windowed_spend returns 0.0 for every window,
and the obvious report would announce that the entire budget remains. The truth is that nothing
was ever recorded, and those are different facts with opposite consequences - the first invites an
operator to spend, the second says the instrument is not connected.

THE WHOLE REFUSAL RESTS ON ONE PREDICATE, so it is single-sourced and asserted. What separates
"no recorded spend" from "a recorded spend of zero" is the rule for what counts as a spend
READING, and that rule is the governor's `_tokens_at` (a tokens field plus a parseable timestamp)
called from here rather than respelled here. An independent review removed the local respelling of
it and the whole suite stayed green while the module announced the full budget as remaining over
1173 live events, none of which carried a spend field. The suite now feeds events that carry NO
tokens field - the only shape the live stream has - and requires UNMEASURED.

AND A THIRD STATE, because the taxonomy names it: a window whose readings TOTAL ZERO is
ZERO_RECORDED, distinct from UNMEASURED and equally not "budget available". A stream that recorded
consumption of zero is either idle or miscounting, and neither is a licence to spend the window.

AND A SECOND THING NOBODY WAS TOLD. The governor's own contract is that a per-worker rate of zero
or less means burn is not measured yet, and it then permits max_workers. That is correct for the
governor - it cannot pace what it cannot measure - but it is dangerous as a SILENT state, because
in this repository burn has never been measured, which means the pacing PLAN-0018 promises has
never paced anything here. So this report names the POSTURE:

  PACING     burn is measured and the worker count is derived from it
  BOOTSTRAP  no burn is measured, so the governor PERMITS the maximum and is NOT pacing
  SPENT      a window's budget is used up inside its trailing horizon; zero until it rolls

THE RATE IS AN ARGUMENT, SO IT IS CORROBORATED AGAINST THE STREAM. The per-worker rate is measured
by the caller (governor.measure_per_worker_rate) and handed in, which means a caller can hand in a
number this module never measured. It used to print "burn is measured at 1.0 tokens per worker per
second" directly above "UNMEASURED - no recorded spend inside the horizon". Now a rate no reading
inside any window's horizon corroborates is NOT repeated as a measurement: the posture stays
BOOTSTRAP and the rate handed to the governor is 0.0, its own honest bootstrap value.

AND THE CORROBORATING EVIDENCE IS RECORDED CONSUMPTION, NOT A RECORDED READING. Requiring only
that SOME reading sits inside a horizon let the same contradiction back in through the taxonomy's
other door: one reading of zero tokens made the report print "burn is measured at 1.0 tokens per
worker per second" directly above "ZERO_RECORDED - 1 recorded event(s) inside the horizon total
ZERO tokens", and it changed the worker count an operator reads from 8 to 1. The condition is the
governor's own: measure_per_worker_rate is the windowed spend divided by the horizon and the worker
count, so it CANNOT return a positive rate over readings totalling zero or less. A positive rate is
therefore corroborated only by a window whose readings TOTAL more than zero, which is the same
evidence the caller's own measurement rests on rather than a second opinion about it.

WHAT COMES FROM THE GOVERNOR AND WHAT IS DERIVED HERE, NAMED SEPARATELY, because the blanket claim
that every number came from the governor was not true of the shipped code and a review said so.
FROM THE GOVERNOR, BY CALLING IT: the windowed spend (windowed_spend), the worker count
(desired_workers), the resume time (resume_at), each window's target rate (Window.target_rate),
the rule for what counts as a recorded spend (_tokens_at), and the trailing-horizon cut - which is
windowed_spend asked a DIFFERENT QUESTION, over the same events with each reading's value replaced
by 1, so the governor COUNTS the readings inside the horizon instead of totalling them. DERIVED
HERE and nowhere else: what remains against a window's budget (its tokens minus the governor's
used), the window's state label, the posture label, and the prose. No pacing arithmetic is
respelled here, and the suite proves the single sourcing BY INTERCEPTION - the worker count and the
resume time in the report are the values a call into the governor returned on that call - because
equality against a second implementation only ever catches a copy that DIVERGED, never a faithful
one, and the faithful copy is the one that diverges quietly later.

WHAT MAKES STOPPING SAFE IS NOT THIS MODULE. Concluded work is artifacts on disk, and a claimed
unit's claim AGES OUT of the ledger so the unit returns to the queue - the properties VELDO-0002
and VELDO-0003 landed. This report names them with the counts it measured, so an operator deciding
whether to stop reads what is at risk instead of guessing. NEITHER HALF MAY ANSWER ZERO WHEN IT
COULD NOT READ: an absent corpus root is UNKNOWN rather than a corpus of zero, and a survival
report about ANOTHER tree does not quote this process's claim ledger.

IT PACES NOTHING. No decision here changes what runs; it spawns nothing and never sleeps.
"""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

POSTURE_PACING = "PACING"
POSTURE_BOOTSTRAP = "BOOTSTRAP"
POSTURE_SPENT = "SPENT"
POSTURES = (POSTURE_PACING, POSTURE_BOOTSTRAP, POSTURE_SPENT)

# A window with NO recorded spend inside its horizon. Distinct from a window whose recorded spend
# totals zero, and neither is "budget available".
UNMEASURED = "UNMEASURED"
# A window with readings inside its horizon that TOTAL ZERO. The stream is connected and measured
# no consumption, which the taxonomy keeps distinct from UNMEASURED and equally does not report as
# budget available: an idle window and a miscounting instrument look identical from here.
ZERO_RECORDED = "ZERO_RECORDED"
# A window with readings totalling more than zero and less than its budget.
MEASURED = "measured"
WINDOW_STATES = (UNMEASURED, ZERO_RECORDED, MEASURED, POSTURE_SPENT)

STAND_DOWN_NO_WINDOWS = ("no budget window is configured here: nobody declared a budget, which is "
                         "NOT the same fact as the budget being fine")
LEDGER_UNKNOWN = ("the claim ledger could not be read, so what is at risk from stopping is "
                  "UNKNOWN rather than nothing")
LEDGER_FOREIGN_TREE = ("this survival report is about another tree and no claims root was given "
                       "for it: the ledger resolves from the running process, so quoting it here "
                       "would report one tree's risk about another. UNKNOWN rather than a count")
ARTIFACTS_UNKNOWN = ("the artifact corpus could not be read, so what survives stopping as "
                     "concluded work is UNKNOWN rather than nothing")
RATE_UNCORROBORATED = ("a per-worker rate was PASSED IN and this report will not repeat it as a "
                       "measurement: no window's readings inside its horizon TOTAL more than zero, "
                       "so nothing on the stream corroborates a positive burn rate and the rate "
                       "handed to the governor is 0.0, the governor's own honest bootstrap value. "
                       "governor.measure_per_worker_rate is the windowed spend over the horizon and "
                       "the worker count, so it cannot have produced this number from this stream")

REPORT_KEYS = ("stood_down", "reason", "posture", "posture_note", "windows", "desired_workers",
               "per_worker_rate", "rate_corroborated", "rate_used", "resume_at", "spend_events",
               "survives", "at_risk")


def _organ(name):
    spec = importlib.util.spec_from_file_location(
        "veldo_bs_" + name, ROOT / ".veldo" / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_events(path=None, root=None):
    """The recorded event stream as dicts. A line that does not parse is skipped, because the log
    is append-only with several producers and one bad line must not blind the reader."""
    base = Path(root) if root is not None else ROOT
    p = Path(path) if path is not None else base / ".veldo" / "events.jsonl"
    out = []
    if not p.is_file():
        return out
    for line in p.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if isinstance(ev, dict):
            out.append(ev)
    return out


def spend_events(events, gov=None):
    """The events carrying a token spend, BY THE GOVERNOR'S OWN RULE FOR WHAT A READING IS.

    THE COUNT IS THE POINT: zero of them means the stream was never instrumented, which is what
    makes a zero total meaningless. So the predicate that decides it is not spelled here. It is
    governor._tokens_at, asked one event at a time, and the reach for a name with an underscore is
    deliberate: the alternative is a second spelling of the one rule that separates "no recorded
    spend" from "a recorded spend of zero", and two spellings of that rule is the defect this item
    was written about. `gov` is injectable so a caller that already loaded the governor does not
    load it twice."""
    g = gov if gov is not None else _organ("governor")
    return [e for e in events if g._tokens_at([e])]


def recorded_in_horizon(gov, spends, now_epoch, seconds):
    """HOW MANY readings sit inside the trailing horizon, using the governor's own horizon rule.

    windowed_spend already parses the timestamps and applies the cut; asked over the same events
    with each reading's value replaced by 1 it COUNTS the readings instead of totalling them. Same
    parse, same cut, same definition of a reading, one implementation - a local `t >= now - seconds`
    here would be a second spelling of the governor's own line."""
    return int(gov.windowed_spend([dict(e, tokens=1) for e in spends], now_epoch, seconds))


def survival(root=None, claims_root=None):
    """What survives stopping right now, measured rather than asserted, and UNKNOWN when it could
    not be measured.

    Concluded work is ARTIFACTS: they are on disk and stopping cannot touch them. A CLAIMED unit
    survives differently - its claim ages out of the ledger and the unit returns to the queue - so
    the two are counted separately.

    NEITHER HALF MAY ANSWER ZERO WHEN IT COULD NOT READ. "Nothing is at risk" and "I could not tell
    what is at risk" are opposite reassurances, and the first is the confident zero this whole item
    exists to refuse. An absent corpus root is UNKNOWN rather than a corpus of zero. And the claim
    ledger is a property of a TREE while claim.claims_root resolves it from the RUNNING PROCESS, so
    a survival report about another tree with no claims root given for it reports UNKNOWN instead of
    quoting this tree's live claims as that one's risk."""
    base = Path(root) if root is not None else ROOT
    out = {"concluded_artifacts": None, "claimed_units": None, "artifacts": None, "ledger": None,
           "claims_root": None, "stale_after_seconds": None}
    try:
        ws = _organ("work_state")
        vc = _organ("verdict_corpus")
        corpus = base / vc.PROOF_ROOT
        if corpus.is_dir():
            rep = ws.work_report(root=base, runs_root=str(base / "no-runs-root-for-this-read"))
            out["concluded_artifacts"] = rep["counts"][ws.DONE]
        else:
            out["artifacts"] = "%s (no corpus root at %s)" % (ARTIFACTS_UNKNOWN, corpus)
    except Exception as e:                        # noqa: BLE001 - an unreadable corpus is UNKNOWN
        out["concluded_artifacts"] = None
        out["artifacts"] = "%s (%s)" % (ARTIFACTS_UNKNOWN, e)
    try:
        cl = _organ("claim")
        out["stale_after_seconds"] = cl.STALE_AFTER_SECONDS
        if claims_root is None and base.resolve() != ROOT.resolve():
            out["ledger"] = LEDGER_FOREIGN_TREE
        else:
            out["claims_root"] = cl.claims_root(claims_root)
            out["claimed_units"] = len(cl.claimed_units(root=claims_root))
    except Exception as e:                        # noqa: BLE001 - absent or unreadable ledger
        out["claimed_units"] = None
        out["ledger"] = "%s (%s)" % (LEDGER_UNKNOWN, e)
    return out


def budget_report(windows=(), root=None, now_epoch=None, per_worker_rate=0.0, max_workers=1,
                  events=None, limit_cooldown_until=None, claims_root=None):
    """ONE key shape whether it stood down or not, with no posture-dependent key.

    windows is a list of governor.Window. per_worker_rate is the burn per worker the CALLER
    measured with governor.measure_per_worker_rate; zero or less is the honest bootstrap value
    rather than a default that looks like a measurement, and a positive value no reading inside any
    horizon corroborates is not repeated as a measurement either (rate_used falls back to 0.0)."""
    base = Path(root) if root is not None else ROOT
    rep = {"stood_down": True, "reason": None, "posture": None, "posture_note": None,
           "windows": [], "desired_workers": None, "per_worker_rate": per_worker_rate,
           "rate_corroborated": None, "rate_used": None, "resume_at": None,
           "spend_events": 0, "survives": {}, "at_risk": []}
    if not windows:
        rep["reason"] = STAND_DOWN_NO_WINDOWS
        return rep

    gov = _organ("governor")
    evs = read_events(root=base) if events is None else list(events)
    spends = spend_events(evs, gov)
    rep["spend_events"] = len(spends)
    now = now_epoch if now_epoch is not None else 0.0

    spent_window = None
    for w in windows:
        recorded = recorded_in_horizon(gov, spends, now, w.seconds)
        used = gov.windowed_spend(evs, now, w.seconds)
        if not recorded:
            state, shown, remaining = UNMEASURED, None, None
        elif used >= w.tokens:
            state, shown, remaining = POSTURE_SPENT, used, max(0.0, w.tokens - used)
        elif used <= 0:
            state, shown, remaining = ZERO_RECORDED, used, None
        else:
            state, shown, remaining = MEASURED, used, max(0.0, w.tokens - used)
        rep["windows"].append({"name": w.name, "horizon_seconds": w.seconds, "tokens": w.tokens,
                               "recorded_events_in_horizon": recorded, "used": shown,
                               "remaining": remaining, "target_rate": w.target_rate(),
                               "state": state})
        if state == POSTURE_SPENT:
            spent_window = w

    # THE RATE IS CORROBORATED OR IT IS NOT USED. The caller supplies it; the stream is the
    # evidence for it. With no reading inside any window's horizon there is no evidence, so the
    # rate handed to the governor is the governor's own bootstrap value rather than a number
    # nothing here measured.
    #
    # AND THE EVIDENCE IS A TOTAL, NOT A COUNT. Requiring only that a reading EXIST inside a
    # horizon accepted a rate the governor's own measurement of that same stream returns 0.0 for:
    # measure_per_worker_rate is the windowed spend divided by the horizon and the worker count, so
    # readings totalling zero or less cannot produce a positive rate. Counting readings instead of
    # totalling them printed "burn is measured at 1.0" over a ZERO_RECORDED window and paced the
    # worker count off it.
    corroborated = any(row["used"] is not None and row["used"] > 0 for row in rep["windows"])
    rate_used = per_worker_rate if corroborated else 0.0
    rep["rate_corroborated"] = corroborated
    rep["rate_used"] = rate_used

    rep["desired_workers"] = gov.desired_workers(
        list(windows), evs, now, rate_used, max_workers,
        limit_cooldown_until=limit_cooldown_until)

    if spent_window is not None:
        rep["posture"] = POSTURE_SPENT
        rep["posture_note"] = (
            "window %r is spent inside its trailing horizon, so the governor permits ZERO workers "
            "until it rolls; the resume time is when enough of the oldest spend ages out"
            % spent_window.name)
        rep["resume_at"] = gov.resume_at(list(windows), evs, now)
    elif rate_used <= 0:
        rep["posture"] = POSTURE_BOOTSTRAP
        # WHY IT IS BOOTSTRAPPING IS DERIVED FROM THE WINDOWS, not from one count that stood in for
        # four different states. The branch that read `if not spends` told an operator with a
        # reading INSIDE a horizon that the window had none of them inside it, which was false of
        # the report printed underneath it. Each state now says what it measured.
        readings = sum(row["recorded_events_in_horizon"] for row in rep["windows"])
        totals = [row["used"] for row in rep["windows"] if row["used"] is not None]
        if not spends:
            why = ("NO BURN IS MEASURED: NOT ONE event in the stream carries a token spend, so a "
                   "windowed total of zero means the instrument was never connected, not that the "
                   "budget is untouched")
        elif not readings:
            why = ("NO BURN IS MEASURED inside a horizon: %d event(s) in the stream carry a token "
                   "spend and no window holds any of them, which is UNMEASURED rather than "
                   "untouched" % len(spends))
        elif not any(t > 0 for t in totals):
            why = ("NO BURN IS MEASURED: %d reading(s) sit inside a horizon and they TOTAL no more "
                   "than zero, which is ZERO_RECORDED rather than measured burn - an idle window "
                   "and a miscounting instrument look identical from here, and neither paces "
                   "anything" % readings)
        else:
            why = ("%d reading(s) inside a horizon carry recorded burn, but the caller supplied no "
                   "positive per-worker rate to pace with, so the governor permits the maximum "
                   "instead of pacing it" % readings)
        rep["posture_note"] = (
            "the governor PERMITS %s worker(s) rather than pacing them. The worker count below is "
            "a PERMISSION, not a pace. %s" % (rep["desired_workers"], why))
        if per_worker_rate > 0:
            rep["posture_note"] += ". %s (supplied: %s)" % (RATE_UNCORROBORATED, per_worker_rate)
    else:
        rep["posture"] = POSTURE_PACING
        rep["posture_note"] = (
            "burn is measured at %s tokens per worker per second, so the worker count is derived "
            "from the tighter window's target rate" % rate_used)

    rep["survives"] = survival(base, claims_root)
    if rep["survives"]["claimed_units"] is None:
        rep["at_risk"].append(rep["survives"]["ledger"] or LEDGER_UNKNOWN)
    if rep["survives"]["concluded_artifacts"] is None:
        rep["at_risk"].append(rep["survives"]["artifacts"] or ARTIFACTS_UNKNOWN)
    rep["stood_down"] = False
    return rep


def report_lines(rep):
    """The report as lines a stranger reads before deciding whether to stop."""
    if rep["stood_down"]:
        return ["budget state: stood down - %s" % rep["reason"]]
    lines = ["budget state: posture %s. %s" % (rep["posture"], rep["posture_note"])]
    for w in rep["windows"]:
        if w["state"] == UNMEASURED:
            lines.append("  %s (%.0fs horizon, %.0f tokens): UNMEASURED - no recorded spend inside "
                         "the horizon, so there is no remaining figure to quote"
                         % (w["name"], w["horizon_seconds"], w["tokens"]))
        elif w["state"] == ZERO_RECORDED:
            lines.append("  %s (%.0fs horizon, %.0f tokens): ZERO_RECORDED - %d recorded event(s) "
                         "inside the horizon total ZERO tokens, so the stream is connected and "
                         "measured no consumption; that is not a remaining figure to spend against"
                         % (w["name"], w["horizon_seconds"], w["tokens"],
                            w["recorded_events_in_horizon"]))
        else:
            lines.append("  %s (%.0fs horizon): %.0f of %.0f used, %.0f remaining, from %d "
                         "recorded event(s)"
                         % (w["name"], w["horizon_seconds"], w["used"], w["tokens"],
                            w["remaining"], w["recorded_events_in_horizon"]))
    s = rep["survives"]
    lines.append("  survives stopping: %s concluded artifact set(s) on disk; %s claimed unit(s) "
                 "whose claims age out after %ss and return to the queue"
                 % ("UNKNOWN" if s["concluded_artifacts"] is None else s["concluded_artifacts"],
                    "UNKNOWN" if s["claimed_units"] is None else s["claimed_units"],
                    s["stale_after_seconds"]))
    for risk in rep["at_risk"]:
        lines.append("  AT RISK, unmeasured: %s" % risk)
    return lines
