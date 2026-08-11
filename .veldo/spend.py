#!/usr/bin/env python3
"""Spend recording: the missing emitter Tokens of Effort was waiting for (PLAN-0014 W1b).

WHY THIS EXISTS. WARP-1401 built the actuals corpus and measured that its spend inputs are empty:
904 events in this repository and not one carrying `tokens`, `cost_usd` or `human_minutes`. The
envelope always allowed them, the CLI always accepted them, three readers always aggregated them.
Nothing ever wrote one, so every estimator layer above the corpus would have been learning from
nothing while looking like it worked.

THE REASON NOBODY WROTE ONE IS ARCHITECTURAL, and it shapes this module. A token count is not
knowable from inside a repository: the gate cannot see what an agent spent, because that number
lives in the harness running the agent. So the emitter cannot be a derivation - there is nothing to
derive it from. It has to be a RECORD the agent makes about itself, at the moment it ships.

WHICH MAKES THIS SELF-REPORTED DATA, AND THE MODULE SAYS SO RATHER THAN LETTING A READER ASSUME
OTHERWISE. It is not adversarial - an agent has no incentive to misreport its own token count - but
it is approximate for a mundane reason: work that spans several sessions, a compaction, or more
than one agent does not sum cleanly, and the agent recording the number may only know its own part.
So `basis` is a required field, and it says which. A number whose provenance is unstated is a
number a later analysis will over-trust.

WHAT IS ENFORCED AND WHAT IS NOT, deliberately. Recording is not a gate condition: a spec does not
fail to ship because its spend is unknown, because that would make an estimation convenience into a
blocker on real work, which is the ceremony this project exists to avoid. What IS mechanical is the
REPORT - `coverage()` in `toe_corpus.py` shows the gap as a number, so adoption is visible rather
than assumed. If the number stays at zero, that is an answer too: it means nobody is recording, and
the honest response is to drop the layers that need actuals rather than to pretend.
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_EVENT_TYPE = "spec.shipped"

# HOW THE NUMBER WAS ARRIVED AT. Required, because a token count with no stated provenance is one a
# later analysis will over-trust. Ordered loosely from most to least trustworthy.
BASES = {
    "harness_reported": "the agent harness reported this session's usage directly",
    "agent_estimate": "the agent's own estimate of its usage, not read from a meter",
    "partial_session": "one session of work that spanned several; this is not the whole cost",
    "reconstructed": "assembled after the fact from logs or transcripts",
}

FIELDS = ("tokens", "cost_usd", "human_minutes")


def _events():
    spec = importlib.util.spec_from_file_location("veldo_events_spend", ROOT / ".veldo/events.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def validate(spec_id, basis, tokens=None, cost_usd=None, human_minutes=None):
    """Every problem with a spend record, as a list. Empty means recordable.

    AT LEAST ONE FIGURE IS REQUIRED, because a record carrying none is indistinguishable from the
    silence it was meant to replace - it would make `spend_recorded` true while adding nothing, and
    that is worse than no record at all since it inflates the coverage number this whole item
    exists to make honest."""
    out = []
    if not (isinstance(spec_id, str) and spec_id.strip()):
        out.append("a spend record must name the spec it accounts for, got %r" % (spec_id,))
    if basis not in BASES:
        out.append("basis must be one of %s (a number with no stated provenance is one a later "
                   "analysis will over-trust), got %r" % (sorted(BASES), basis))
    vals = {"tokens": tokens, "cost_usd": cost_usd, "human_minutes": human_minutes}
    for k, v in sorted(vals.items()):
        if v is None:
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            out.append("%s must be a number, got %r" % (k, v))
        elif v < 0:
            out.append("%s cannot be negative, got %r" % (k, v))
    if all(vals[k] is None for k in vals):
        out.append("a spend record carrying no figure at all is indistinguishable from silence, and "
                   "recording it would inflate the coverage number this exists to keep honest: "
                   "supply at least one of tokens, cost_usd or human_minutes")
    return out


def record(spec_id, basis, tokens=None, cost_usd=None, human_minutes=None, note=None, emit=None):
    """Append ONE spend record for a spec, through the event module's single writer.

    Goes through `events.emit` rather than opening the log here, because that function is the one
    place in this system that puts bytes in the log and adding a second writer would be exactly the
    defect the event module spent nine rounds closing. `emit` is injectable so the selftest can
    drive this without touching the real log."""
    problems = validate(spec_id, basis, tokens, cost_usd, human_minutes)
    if problems:
        raise ValueError("refusing to record spend: " + "; ".join(problems))
    extra = {"spend_basis": basis}
    if note:
        extra["spend_note"] = note
    fn = emit if emit is not None else _events().emit
    return fn(SCHEMA_EVENT_TYPE, spec=spec_id, tokens=tokens, cost_usd=cost_usd,
              human_minutes=human_minutes, extra=extra)


def _cli(argv):
    ap = argparse.ArgumentParser(
        prog="spend.py",
        description="Record what a change actually cost, against its spec. Self-reported by the "
                    "agent that did the work, because a token count is not knowable from inside "
                    "the repository.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record", help="append one spend record for a spec")
    r.add_argument("--spec", required=True)
    r.add_argument("--basis", required=True, choices=sorted(BASES),
                   help="; ".join("%s: %s" % (k, v) for k, v in sorted(BASES.items())))
    r.add_argument("--tokens", type=int)
    r.add_argument("--cost-usd", type=float)
    r.add_argument("--human-minutes", type=int)
    r.add_argument("--note")
    sub.add_parser("bases", help="the declared provenance values and what each means")
    a = ap.parse_args(argv)
    if a.cmd == "bases":
        for k, v in sorted(BASES.items()):
            print("%-18s %s" % (k, v))
        return 0
    try:
        ev = record(a.spec, a.basis, a.tokens, a.cost_usd, a.human_minutes, a.note)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(json.dumps(ev, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
