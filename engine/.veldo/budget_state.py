#!/usr/bin/env python3
"""VELDO budget state: where the budget stands on the path an operator actually takes.

WHAT THIS EXISTS TO REFUSE TO SAY. Measured on 2026-08-12: this repository's event stream carries
ZERO events with a spend field. So the governor's windowed_spend returns 0.0 for every window,
and the obvious report would announce that the entire budget remains. The truth is that nothing
was ever recorded, and those are different facts with opposite consequences - the first invites an
operator to spend, the second says the instrument is not connected.

AND A SECOND THING NOBODY WAS TOLD. The governor's own contract is that a per-worker rate of zero
or less means burn is not measured yet, and it then permits max_workers. That is correct for the
governor - it cannot pace what it cannot measure - but it is dangerous as a SILENT state, because
in this repository burn has never been measured, which means the pacing PLAN-0018 promises has
never paced anything here. So this report names the POSTURE:

  PACING     burn is measured and the worker count is derived from it
  BOOTSTRAP  no burn is measured, so the governor PERMITS the maximum and is NOT pacing
  SPENT      a window's budget is used up inside its trailing horizon; zero until it rolls

EVERY NUMBER COMES FROM THE GOVERNOR. The worker count, the windowed spend and the resume time are
governor.desired_workers, governor.windowed_spend and governor.resume_at called over the same
inputs. A read model that recomputed the pacing arithmetic would be two implementations of one
rule, which is this repository's most repeated defect and the one that diverges quietly because
both copies look right.

WHAT MAKES STOPPING SAFE IS NOT THIS MODULE. Concluded work is artifacts on disk, and a claimed
unit's claim AGES OUT of the ledger so the unit returns to the queue - the properties VELDO-0002
and VELDO-0003 landed. This report names them with the counts it measured, so an operator deciding
whether to stop reads what is at risk instead of guessing, and an absent ledger is reported as
unknown rather than as nothing at risk.

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

STAND_DOWN_NO_WINDOWS = ("no budget window is configured here: nobody declared a budget, which is "
                         "NOT the same fact as the budget being fine")
LEDGER_UNKNOWN = ("the claim ledger could not be read, so what is at risk from stopping is "
                  "UNKNOWN rather than nothing")

REPORT_KEYS = ("stood_down", "reason", "posture", "posture_note", "windows", "desired_workers",
               "per_worker_rate", "spend_events", "survives", "at_risk")


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


def spend_events(events):
    """The events carrying a token spend. THE COUNT IS THE POINT: zero of them means the stream was
    never instrumented, which is what makes a zero total meaningless."""
    return [e for e in events if e.get("tokens") is not None]


def survival(root=None, claims_root=None):
    """What survives stopping right now, measured rather than asserted.

    Concluded work is ARTIFACTS: they are on disk and stopping cannot touch them. A CLAIMED unit
    survives differently - its claim ages out of the ledger and the unit returns to the queue - so
    the two are counted separately. An unreadable ledger is UNKNOWN, never nothing at risk."""
    base = Path(root) if root is not None else ROOT
    out = {"concluded_artifacts": None, "claimed_units": None, "ledger": None,
           "stale_after_seconds": None}
    try:
        ws = _organ("work_state")
        rep = ws.work_report(root=base, runs_root=str(base / "no-runs-root-for-this-read"))
        out["concluded_artifacts"] = rep["counts"][ws.DONE]
    except Exception as e:                        # noqa: BLE001 - an unreadable corpus is UNKNOWN
        out["concluded_artifacts"] = None
        out["ledger"] = "work state unreadable: %s" % e
    try:
        cl = _organ("claim")
        out["claimed_units"] = len(cl.claimed_units(root=claims_root))
        out["stale_after_seconds"] = cl.STALE_AFTER_SECONDS
    except Exception:                             # noqa: BLE001 - absent or unreadable ledger
        out["claimed_units"] = None
        out["ledger"] = LEDGER_UNKNOWN
    return out


def budget_report(windows=(), root=None, now_epoch=None, per_worker_rate=0.0, max_workers=1,
                  events=None, limit_cooldown_until=None, claims_root=None):
    """ONE key shape whether it stood down or not.

    windows is a list of governor.Window. per_worker_rate is the MEASURED burn per worker; the
    caller measures it with governor.measure_per_worker_rate, and zero or less is the honest
    bootstrap value rather than a default that looks like a measurement."""
    base = Path(root) if root is not None else ROOT
    rep = {"stood_down": True, "reason": None, "posture": None, "posture_note": None,
           "windows": [], "desired_workers": None, "per_worker_rate": per_worker_rate,
           "spend_events": 0, "survives": {}, "at_risk": []}
    if not windows:
        rep["reason"] = STAND_DOWN_NO_WINDOWS
        return rep

    gov = _organ("governor")
    evs = read_events(root=base) if events is None else list(events)
    spends = spend_events(evs)
    rep["spend_events"] = len(spends)
    now = now_epoch if now_epoch is not None else 0.0

    spent_window = None
    for w in windows:
        inside = [e for e in spends
                  if gov.M.parse_at(e) is not None
                  and gov.M.parse_at(e).timestamp() >= now - w.seconds]
        used = gov.windowed_spend(evs, now, w.seconds)
        row = {"name": w.name, "horizon_seconds": w.seconds, "tokens": w.tokens,
               "recorded_events_in_horizon": len(inside),
               "used": None if not inside else used,
               "remaining": None if not inside else max(0.0, w.tokens - used),
               "target_rate": w.target_rate(),
               "state": UNMEASURED if not inside else (
                   POSTURE_SPENT if used >= w.tokens else "measured")}
        rep["windows"].append(row)
        if row["state"] == POSTURE_SPENT:
            spent_window = w

    rep["desired_workers"] = gov.desired_workers(
        list(windows), evs, now, per_worker_rate, max_workers,
        limit_cooldown_until=limit_cooldown_until)

    if spent_window is not None:
        rep["posture"] = POSTURE_SPENT
        rep["posture_note"] = (
            "window %r is spent inside its trailing horizon, so the governor permits ZERO workers "
            "until it rolls; the resume time is when enough of the oldest spend ages out"
            % spent_window.name)
        rep["resume_at"] = gov.resume_at(list(windows), evs, now)
    elif per_worker_rate <= 0:
        rep["posture"] = POSTURE_BOOTSTRAP
        rep["posture_note"] = (
            "NO BURN IS MEASURED, so the governor PERMITS %s worker(s) rather than pacing them. "
            "The worker count below is a PERMISSION, not a pace. %d event(s) in the stream carry a "
            "token spend: with none, a windowed total of zero means the instrument was never "
            "connected, not that the budget is untouched"
            % (rep["desired_workers"], len(spends)))
    else:
        rep["posture"] = POSTURE_PACING
        rep["posture_note"] = (
            "burn is measured at %s tokens per worker per second, so the worker count is derived "
            "from the tighter window's target rate" % per_worker_rate)

    rep["survives"] = survival(base, claims_root)
    if rep["survives"]["claimed_units"] is None:
        rep["at_risk"].append(LEDGER_UNKNOWN)
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
