#!/usr/bin/env python3
"""VELDO metrics: derive the numbers that matter from the event stream.

The method's scarce resource is human attention, and its health is spec-to-
ship latency and verification throughput - not lines of code. This reads
.veldo/events.jsonl (event envelope v1) and computes those, by correlation_id
so a change's events are tied together. No state of its own; the events are
the truth.

TWO DERIVATIONS live in the metrics area, in TWELVE modules with one direction
of dependency and one job each (the count is a MEASUREMENT of the file list, not
a leftover: round 4 failed a manifest for saying three when there were four,
this sentence said FIVE while seven shipped, and it said TEN while twelve did):

  .veldo/metrics.py           this file: the LOOP measures (compute) over the
                             event stream alone, plus the CLI that renders
                             both derivations.
  .veldo/metrics_event_stream.py
                             THE LOOP DERIVATION'S READ of that one recorded
                             artifact: its declared codec, its four per-line
                             skips, and the NAMED SHORTFALL when the stream
                             EXISTS and cannot be read at all - which sat inside
                             no handler in this file until round 10 and exited
                             all four surfaces printing nothing.
  .veldo/metrics_support_contract.py
                             the DECLARED CONTRACT of the support pass: the
                             closed set of exclusion and stand-down names, the
                             table of every source it reads, the register of
                             every id-keyed collection, and the ONE decision
                             that says whether a source proved it read
                             COMPLETELY. Every other module obeys it.
  .veldo/metrics_support.py   the SUPPORT measures (WARP-1210, W10 of
                             PLAN-0012, the second half of outcome O6):
                             time-to-diagnosis and time-to-restore as TRENDS,
                             the recurrence rate, the diagnosability score,
                             and the incidents-per-area soft join. A PURE
                             derivation over injected inputs: it reads no
                             file, no clock and no network at all.
  .veldo/metrics_read_accounting.py
                             THE ACCOUNTED READ: what makes a read of a
                             filesystem source COMPLETE (presence by lstat,
                             enumeration by listdir, every entry accounted
                             against the DECLARED SKIP RULE), implemented once
                             for every source.
  .veldo/metrics_skip_rule.py THE DECLARED SKIP RULE and what a store ENTRY IS:
                             the table of names a store may hold that are not
                             records, the KIND test a name may only be applied
                             through, and the describer an entry nobody could
                             account for is NAMED by. The DECLARATION an adopter
                             reads and may extend, which is why it loads
                             nothing at all.
  .veldo/metrics_read_kind.py THE DECLARED READ UNIT AND ITS KIND: what each of
                             the thirteen declared sources reads, and whether an
                             entry may be OPENED at all - a read that BLOCKS
                             raises nothing for any handler to name.
  .veldo/metrics_read_closure.py
                             THE TRANSITIVE CLOSURE of what an ENGINE OWNER
                             opens ON THIS PASS'S BEHALF, plus the ONE hand-off.
  .veldo/metrics_owner_reads.py
                             THE ENGINE OWNERS this pass EXECUTES - the record
                             loader, the one front-matter parser, the corpus
                             index and the cost series - each a declared source
                             that NAMES ITSELF when it will not load, resolved
                             against the ENGINE rather than the repository.
  .veldo/metrics_shape_readers.py
                             the DECLARED SHAPE the incidents are joined to:
                             the architecture contract, the spec corpus, the
                             placement-to-area index and the cost series.
  .veldo/metrics_readers.py   the WIRED READERS: the one impure edge that
                             gathers the event stream, the receipts, the
                             incident records and the vocabulary off disk, each
                             with a POSITIVE assertion that the read was
                             COMPLETE, plus the ONE gatherer every surface
                             calls.
  .veldo/metrics_support_report.py
                             the REPORT layer over that model: the ONE NAMED
                             SET of every source that did not prove a complete
                             read and every input the derivation could not
                             use, the TEXT presentation, and the MACHINE
                             presentation (--json). The dashboard's HTML is the
                             third presentation of the same named set, which is
                             what keeps the three surfaces agreeing.

The support measures AUTHENTICATE every input against the reconciliation
receipts, because RECOGNITION IS NOT AUTHENTICATION: the gate recognizes an
incident.closed, so any writer can append one, and a measure that trusts the
event stream alone is unauthenticated. The receipts are the AUTHORITY, the
events are the INDEX, and every input that cannot be counted is reported BY
NAME rather than dropped. And EVERY SOURCE PROVES IT READ COMPLETELY OR NO
SUPPORT NUMBER IS RENDERED AT ALL: an absent source is complete and empty, and
anything else has to be affirmed, so a filesystem shape nobody enumerated fails
closed instead of turning a real measure into a plausible wrong one. The two
derivations are independent: the support pass does not call compute and changes
no number compute reports.

  python3 .veldo/metrics.py            # human-readable summary
  python3 .veldo/metrics.py --json     # machine-readable
"""
import argparse
import datetime
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / ".veldo" / "events.jsonl"

# THE READ OF THE ONE RECORDED ARTIFACT the loop measures are derived from, loaded BY PATH exactly as every
# organ of this area loads its owner. It is its OWN module because the read is its own job - the seam the
# support pass has had since round 5 - and because a module at its declared bound cannot grow a guard: this
# file stood at 399 of its declared 400 lines, and compressing the declarations around the read to make room
# for one is the wrong answer to a bound. The reason, the four exception classes a read of a recorded
# artifact must name, and what is said when the artifact will not be read are all declared there.
_esspec = importlib.util.spec_from_file_location("veldo_metrics_event_stream",
                                                 ROOT / ".veldo" / "metrics_event_stream.py")
_stream = importlib.util.module_from_spec(_esspec)
_esspec.loader.exec_module(_stream)


def load():
    """Every RECORDED event of the stream, for every caller that wants the events and nothing else (the
    dashboard, the entropy map, the reconciliation pass): byte for byte what it returned before the read
    became its own module, so no caller changes and no number moves. THE READ ITSELF - its declared codec,
    its FOUR per-line skips, and what it NAMES when the artifact cannot be read at all - is
    .veldo/metrics_event_stream.py, and load_accounted() below is that same read WITH the name."""
    return load_accounted()[0]


def load_accounted():
    """(the events, the SHORTFALL naming the recorded artifact when the stream itself could not be read, or
    None) - THE ACCOUNTED FORM of the loop read, added at round 10 because the whole-file read sat inside NO
    HANDLER AT ALL: a mode-000 .veldo/events.jsonl exited ALL FOUR SURFACES 1 with PermissionError and zero
    bytes of stdout, a DIRECTORY at that path with IsADirectoryError, and a stream larger than the address
    space with MemoryError, in every case losing every PRE-EXISTING loop number to an artifact nobody could
    read. An ABSENT stream is complete and empty and carries NO shortfall (adoption safe); anything else is
    NAMED, and both surfaces print that name ABOVE the measures, so a zero here is never read as a history."""
    return _stream.load_stream(LOG)


def parse_iso(value):
    """One ISO-8601 timestamp string as a datetime, or None when it is absent or unreadable. THE ONE
    timestamp reader in this module: parse_at reads an event's `at` through it and the support measures
    read an incident timeline through it, so there is no second date parser and no second answer to
    "what is an unreadable timestamp" (it is None, never a zero)."""
    try:
        return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def parse_at(ev):
    return parse_iso(ev.get("at")) if isinstance(ev, dict) else None


def _is_str(v):
    """A non-empty string, the idiom every sibling organ carries (never a parser)."""
    return isinstance(v, str) and v.strip() != ""


def cost_by_correlation(events):
    """Per-correlation COST-TO-CHANGE components for the entropy derivation (PLAN-0011 W8).
    Every field is one the loop ALREADY records on the envelope; this is a second VIEW of the
    same events (keyed by correlation_id), never a second store or new instrumentation. The
    entropy map (.veldo/entropy.py) reads this through compute() and joins it to contract areas
    through placement, so the map, the dashboard, and the budget enforcer never fork a number.
    gate.failed attribution is best-effort: a gate event contributes only when it carries a
    correlation_id (verify.sh stamps uncorrelated gate events, which stay global)."""
    out = {}
    for e in events:
        c = e.get("correlation_id") or e.get("spec_id")
        if not c:
            continue
        b = out.setdefault(c, {"tokens": 0, "cost_usd": 0.0, "human_minutes": 0,
                               "review_cycles": 0, "gate_failures": 0,
                               "shipped_at": None, "first_at": None, "last_at": None})
        tk, cu, hm = e.get("tokens"), e.get("cost_usd"), e.get("human_minutes")
        if tk is not None:
            b["tokens"] += int(tk)
        if cu is not None:
            b["cost_usd"] += float(cu)
        if hm is not None:
            b["human_minutes"] += int(hm or 0)
        t = e.get("type")
        if t == "verdict.recorded":
            b["review_cycles"] += 1
        elif t == "gate.failed":
            b["gate_failures"] += 1
        at = e.get("at")
        if at:
            if b["first_at"] is None or at < b["first_at"]:
                b["first_at"] = at
            if b["last_at"] is None or at > b["last_at"]:
                b["last_at"] = at
            if t == "spec.shipped":
                b["shipped_at"] = at
    for c in out:
        out[c]["cost_usd"] = round(out[c]["cost_usd"], 6)
    return out


def compute(events):
    by_corr = {}
    for e in events:
        c = e.get("correlation_id") or e.get("spec_id")
        if c:
            by_corr.setdefault(c, []).append(e)

    spec_to_ship = []   # hours from spec.ready to spec.shipped
    proof_latency = []  # hours from spec.ready to proof.recorded
    for corr, evs in by_corr.items():
        evs = sorted(evs, key=lambda e: e.get("at", ""))
        first = next((e for e in evs if e.get("type") == "spec.ready"), None)
        shipped = next((e for e in evs if e.get("type") == "spec.shipped"), None)
        proof = next((e for e in evs if e.get("type") == "proof.recorded"), None)
        if first and shipped:
            a, b = parse_at(first), parse_at(shipped)
            if a and b:
                spec_to_ship.append((corr, (b - a).total_seconds() / 3600))
        if first and proof:
            a, b = parse_at(first), parse_at(proof)
            if a and b:
                proof_latency.append((corr, (b - a).total_seconds() / 3600))

    human_minutes = sum(int(e.get("human_minutes", 0) or 0) for e in events)
    hm_by_type = {}
    for e in events:
        hm = int(e.get("human_minutes", 0) or 0)
        if hm:
            hm_by_type[e["type"]] = hm_by_type.get(e["type"], 0) + hm

    # spend on the stream: tokens and cost_usd ride the envelope the same
    # optional way human_minutes does. Aggregate totals and by correlation_id
    # here so the budget enforcer and any dashboard read the SAME numbers - one
    # calculation, never a fork. Events with no spend fields contribute nothing.
    spend_by_corr = {}
    spend_tokens_total = 0
    spend_cost_total = 0.0
    for e in events:
        tk = e.get("tokens")
        cu = e.get("cost_usd")
        if tk is None and cu is None:
            continue
        c = e.get("correlation_id") or e.get("spec_id")
        bucket = spend_by_corr.setdefault(c, {"tokens": 0, "cost_usd": 0.0}) if c else None
        if tk is not None:
            tki = int(tk)
            spend_tokens_total += tki
            if bucket is not None:
                bucket["tokens"] += tki
        if cu is not None:
            cuf = float(cu)
            spend_cost_total += cuf
            if bucket is not None:
                bucket["cost_usd"] += cuf
    spend_cost_total = round(spend_cost_total, 6)
    for c in spend_by_corr:
        spend_by_corr[c]["cost_usd"] = round(spend_by_corr[c]["cost_usd"], 6)

    # Per-correlation cost-to-change components for the entropy derivation (PLAN-0011 W8),
    # computed by the dedicated reader above so compute() stays cohesive and the entropy map,
    # the dashboard, and the budget enforcer all read the one aggregation.
    cost_by_corr = cost_by_correlation(events)

    gate_pass = sum(1 for e in events if e.get("type") == "gate.passed")
    gate_fail = sum(1 for e in events if e.get("type") == "gate.failed")
    open_emerg = 0
    for e in events:
        if e.get("type") == "emergency.push":
            open_emerg += 1
        elif e.get("type") in ("emergency.closed", "spec.shipped") and open_emerg:
            open_emerg -= 1

    # verdict tally: how the reviews landed, by the verdict.recorded value.
    verdict_counts = {}
    for e in events:
        if e.get("type") == "verdict.recorded":
            v = e.get("verdict")
            if v:
                verdict_counts[v] = verdict_counts.get(v, 0) + 1

    # regression health: read the gate's green/red history in time order. A
    # green-to-red transition is a regression, red-to-green a recovery, and the
    # last gate event is the current standing. This is the durable signal the
    # dashboard renders; it lives here so there is one calculation, not two.
    gate_history = sorted(
        (e for e in events if e.get("type") in ("gate.passed", "gate.failed")),
        key=lambda e: e.get("at", ""),
    )
    regressions = 0
    recoveries = 0
    prev = None
    for e in gate_history:
        cur = "green" if e.get("type") == "gate.passed" else "red"
        if prev == "green" and cur == "red":
            regressions += 1
        elif prev == "red" and cur == "green":
            recoveries += 1
        prev = cur
    regression_health = {
        "current_gate": prev,
        "gate_runs": len(gate_history),
        "regressions": regressions,
        "recoveries": recoveries,
    }

    def avg(pairs):
        return round(sum(v for _, v in pairs) / len(pairs), 2) if pairs else None

    return {
        "events_total": len(events),
        "changes_tracked": len(by_corr),
        "spec_to_ship_hours_avg": avg(spec_to_ship),
        "spec_to_ship_samples": len(spec_to_ship),
        "proof_latency_hours_avg": avg(proof_latency),
        "human_minutes_total": human_minutes,
        "human_minutes_by_type": hm_by_type,
        "spend_tokens_total": spend_tokens_total,
        "spend_cost_usd_total": spend_cost_total,
        "spend_by_correlation": spend_by_corr,
        "cost_by_correlation": cost_by_corr,
        "gate_pass": gate_pass,
        "gate_fail": gate_fail,
        "gate_pass_rate": round(gate_pass / (gate_pass + gate_fail), 3) if (gate_pass + gate_fail) else None,
        "open_emergency_debt": open_emerg,
        "verdict_counts": verdict_counts,
        "regression_health": regression_health,
    }


_SIBLINGS = {}


def _sibling(name, rel):
    """Load a sibling engine module BY PATH and cache it, the convention every organ here uses
    (dashboard.py, entropy.py and incident_reconcile.py all load their owners this way): one owner per
    vocabulary, nothing reimplemented, no second parser. `rel` may be an ABSOLUTE path, which resolves to
    itself (pathlib) and is how metrics_readers loads the OWNER MODULES against ITS declared engine root
    rather than against this file's - the cache key is the path, so two engines never share an instance."""
    if rel not in _SIBLINGS:
        spec = importlib.util.spec_from_file_location(name, ROOT / rel)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _SIBLINGS[rel] = mod
    return _SIBLINGS[rel]



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    events, stream_shortfall = load_accounted()
    m = compute(events)
    if stream_shortfall:
        # THE UNREAD ARTIFACT CARRIED ONTO EVERY SURFACE, on the model rather than at one print: the text
        # report prints it above the measures and --json carries it as its own key, so a consumer of the
        # machine surface cannot read a zero here as a history either. Absent from the model when the stream
        # read fine, which is what keeps every existing --json byte identical.
        m = dict(m, event_stream_shortfall=stream_shortfall)
    # The support numbers (WARP-1210): the derivation, its wired readers and its report layer are
    # siblings loaded here at the CLI edge, so a repository that only reads the loop measures pays
    # nothing for them.
    SUP = _sibling("veldo_metrics_support", ".veldo/metrics_support.py")
    RDR = _sibling("veldo_metrics_readers", ".veldo/metrics_readers.py")
    RPT = _sibling("veldo_metrics_support_report", ".veldo/metrics_support_report.py")
    support = SUP.support_numbers(events, **RDR.load_support_inputs(events=events))
    if args.json:
        # THE THIRD SURFACE, UNDER THE SAME RULE (AC3): support_json withholds every measure when a
        # declared source did not prove a COMPLETE read, and keeps the completeness verdict and the named
        # sources. This printed the whole model unconditionally until round 6, so a broken data path
        # emitted a 0.0 percent score beside renderable false while the derivation's own docstring said no
        # surface does that. The LOOP measures are untouched: `m` is exactly what compute() returned.
        print(json.dumps(dict(m, support=RPT.support_json(support)), indent=2))
        return 0
    print("VELDO metrics (derived from events.jsonl):")
    if stream_shortfall:
        print("  " + RPT.printable(stream_shortfall))
    print(f"  events: {m['events_total']}, changes tracked: {m['changes_tracked']}")
    print(f"  spec-to-ship avg: {m['spec_to_ship_hours_avg']} h "
          f"({m['spec_to_ship_samples']} shipped)")
    print(f"  proof latency avg: {m['proof_latency_hours_avg']} h")
    print(f"  human minutes total: {m['human_minutes_total']} {m['human_minutes_by_type']}")
    print(f"  spend: {m['spend_tokens_total']} tokens, ${m['spend_cost_usd_total']} "
          f"(by correlation: {m['spend_by_correlation'] or 'none'})")
    print(f"  gate pass rate: {m['gate_pass_rate']} ({m['gate_pass']} pass / {m['gate_fail']} fail)")
    print(f"  verdicts: {m['verdict_counts']}")
    rh = m["regression_health"]
    print(f"  regression health: current gate {rh['current_gate']}, "
          f"{rh['regressions']} regressions / {rh['recoveries']} recoveries "
          f"over {rh['gate_runs']} runs")
    print(f"  open emergency debt: {m['open_emergency_debt']}")
    for line in RPT.support_lines(support):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
