#!/usr/bin/env python3
"""VELDO metrics dashboard: render the derived metrics for a human to read.

This is a RENDERING layer, nothing more. Every number it shows comes from
.veldo/metrics.py compute(), the single source of truth for metrics; the
dashboard never recomputes a figure of its own. If a datum is missing, it is
added to compute() (the shared reader) and both the reader and this dashboard
read it there, so the summary and the dashboard can never disagree.

It reads .veldo/events.jsonl (via metrics.load_accounted, which returns the
events AND, when the stream itself could not be read, the NAME of the artifact
that was not read - rendered above every figure it cost) and presents cycle time
(spec.ready to spec.shipped), proof latency, human minutes, gate pass rate,
verdict counts, emergency debt, and regression health.

The SUPPORT section (WARP-1210, W10 of PLAN-0012) follows the same discipline one
level further: every figure comes from metrics_support.support_numbers over the
inputs metrics_readers.load_support_inputs gathers, and nothing is derived here.
THREE SURFACES, ONE NAMED SET: the text report is
metrics_support_report.support_lines verbatim, the HTML below is a SECOND
presentation that renders the SAME metrics_support_report.support_named_inputs
list, one card per named input, and the metrics CLI's --json is the THIRD through
metrics_support_report.support_json. The HTML used to render only a COUNT, so with
four live exclusions the text named each one and the HTML named none - which is
why the claim of a single renderer was false and why a selftest now asserts all
three surfaces name the same set. Those numbers are AUTHENTICATED against the
reconciliation receipts in the derivation, never here - and they are rendered ONLY
when every declared source proved it read COMPLETELY (AC3), which this surface
obeys through sreport.support_renderable because it is the surface a human
actually looks at and therefore the one where a plausible wrong number does the
damage. All THREE surfaces obey that one mark: round 5 shipped the --json
printing every measure while renderable was false, and the docstring of the
derivation claimed in eight copies that none of them does.

  python3 .veldo/dashboard.py                 # readable text report (default)
  python3 .veldo/dashboard.py --html           # self-contained HTML to stdout
  python3 .veldo/dashboard.py --html --out F    # write the HTML to file F
"""
import argparse
import html
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Load the reader as the single source of truth. Importing it (rather than
# reimplementing load/compute) is what guarantees no second calculation.
_mspec = importlib.util.spec_from_file_location("veldo_metrics", ROOT / ".veldo" / "metrics.py")
metrics = importlib.util.module_from_spec(_mspec)
_mspec.loader.exec_module(metrics)

# The support derivation (WARP-1210 W10) and its wired readers, loaded the same way: the pure derivation
# is the single source for the four support measures - it decides every number, every exclusion and
# whether anything may be rendered at all - and the readers are the ONE impure edge that gathers the
# stream, the receipts, the records, the corpus, the contract and the cost data. There is NO shared
# renderer between this surface and the CLI's text: what keeps them from disagreeing is that both present
# the report layer's ONE named set. The dashboard renders that model and never derives a number of its own.
_sspec = importlib.util.spec_from_file_location("veldo_metrics_support",
                                               ROOT / ".veldo" / "metrics_support.py")
support = importlib.util.module_from_spec(_sspec)
_sspec.loader.exec_module(support)

_rspec = importlib.util.spec_from_file_location("veldo_metrics_readers",
                                               ROOT / ".veldo" / "metrics_readers.py")
readers = importlib.util.module_from_spec(_rspec)
_rspec.loader.exec_module(readers)

# The support REPORT layer, loaded the same way: the ONE named set of every input the derivation could
# not use, the text presentation, and the machine presentation the CLI's --json renders. This module's HTML
# is the third presentation of that same list, so the three surfaces cannot name different sets - and the
# ONE string primitive that makes a rendered value printable on any stream comes from here too, so this
# surface and the text surface cannot disagree about that either.
_ptspec = importlib.util.spec_from_file_location("veldo_metrics_support_report",
                                                ROOT / ".veldo" / "metrics_support_report.py")
sreport = importlib.util.module_from_spec(_ptspec)
_ptspec.loader.exec_module(sreport)

# THE ENTROPY OWNER (PLAN-0011 W8) IS RESOLVED THROUGH THE DECLARED OWNER TABLE RATHER THAN LOADED HERE, and
# this is round 11's correction of a defect this file shipped for ten rounds. .veldo/entropy.py is one of the
# THIRTEEN SOURCES the support pass DECLARES; round 10 guarded the CALL to it and left the LOAD sitting at
# module level in no handler at all, so a mode-000, sparse or wrong-kind .veldo/entropy.py - or .veldo/validate
# .py, which entropy.py loads itself at ITS module level - exited BOTH of these surfaces 1 with ZERO BYTES of
# stdout, and a FIFO at either path hung them forever, while the two metrics surfaces stood the very same
# source down BY NAME through this very table. A GUARD ON THE CALL CANNOT SEE A FAILURE IN THE IMPORT, and a
# rule quantified over READ PRIMITIVES could not see it either, because a module load is a read that none of
# them names. The resolution is now the one the metrics surfaces already use, in the same words:
# metrics_owner_reads._owner asks the DECLARED KIND TEST first (a load OPENS the file, and a blocking open
# raises nothing for any handler to catch), then loads inside a handler naming the whole Exception family, and
# NAMES the declared source that failed rather than charging it to whatever was being rendered.
# AND THE DOMAIN OF THAT HAND-OFF IS THE DECLARED CLOSURE, not the store this surface passes in (round 12):
# the boundary lives in .veldo/metrics_read_closure.py, which is the facade over .veldo/metrics_read_kind.py,
# and it derives the unit, the unit's kind and every root the owner opens ON THIS PASS'S BEHALF from the
# declaration, so this surface cannot ask the question about the wrong thing.
_kspec = importlib.util.spec_from_file_location("veldo_metrics_read_closure_for_dashboard",
                                               ROOT / ".veldo" / "metrics_read_closure.py")
kind = importlib.util.module_from_spec(_kspec)
_kspec.loader.exec_module(kind)

_ENTROPY_READS = []
entropy = readers.load_owners(_ENTROPY_READS).get("entropy_series_owner")


def _entropy_owner_standdown():
    """The NAMED reason this surface has no entropy section, built from the DECLARED SOURCE'S OWN READ RECORD
    so the words here and the words on the metrics surfaces are the same words. An owner that is ABSENT is
    COMPLETE AND EMPTY (an engine that ships no such organ, which must stay adoption safe) and names no
    problem at all, so that case is stated here rather than left as an empty sentence."""
    named = "; ".join("%s (%s): %s" % (_p["source"], _p["subject"], _p["detail"])
                      for _r in _ENTROPY_READS if not readers.read_proves_complete(_r)
                      for _p in _r["problems"])
    return named or ("this engine ships no .veldo/entropy.py, so there is no cost-to-change series to render: "
                     "an absent owner is complete and empty (adoption safe)")


def report_figures(events):
    """The exact figures the dashboard renders, each drawn straight from
    metrics.compute(). The renderers below consume ONLY this, so there is one
    numeric path from events to pixels and no room for a forked calculation.
    """
    m = metrics.compute(events)
    return {
        "cycle_time_hours": m["spec_to_ship_hours_avg"],
        "cycle_time_samples": m["spec_to_ship_samples"],
        "proof_latency_hours": m["proof_latency_hours_avg"],
        "human_minutes": m["human_minutes_total"],
        "human_minutes_by_type": m["human_minutes_by_type"],
        "gate_pass_rate": m["gate_pass_rate"],
        "gate_pass": m["gate_pass"],
        "gate_fail": m["gate_fail"],
        "verdict_counts": m["verdict_counts"],
        "emergency_debt": m["open_emergency_debt"],
        "regression_health": m["regression_health"],
        "events_total": m["events_total"],
        "changes_tracked": m["changes_tracked"],
    }


def support_figures(events, root=None):
    """The SUPPORT numbers (WARP-1210, W10 of PLAN-0012) the dashboard renders, drawn straight from
    metrics_support.support_numbers - the single derivation - over the inputs
    metrics_readers.load_support_inputs gathers (the reconciliation receipts, the incident records, the
    corpus spec index, the contract's declared areas, the named problem for EVERY source that could not
    be read, and PLAN-0011's per-area cost data). The renderers consume ONLY this model and the report
    layer's named set, so the support section has one numeric path from the recorded events and receipts
    to pixels and no forked recomputation, exactly as report_figures does for the core metrics and
    entropy_figures does for entropy. Nothing here decides a number or a stand-down."""
    return support.support_numbers(events, **readers.load_support_inputs(root=root, events=events))


def entropy_figures(events):
    """The per-area entropy figures the dashboard renders, each drawn straight from
    entropy.entropy_report via entropy.area_figures. The renderers consume ONLY this, so the
    entropy section has one numeric path from the recorded events + placements to pixels and no
    forked recomputation, exactly as report_figures does for the core metrics. Returns
    (the stand-down REASON or "", figures, crossings).

    THE OWNER IS EXECUTED INSIDE A HANDLER THAT NAMES THE WHOLE Exception FAMILY, which is round 10's
    defect class one surface over: entropy.entropy_report reads the spec corpus itself, through its own
    locale and its own predicates, and this pass cannot know what that read can raise - measured, ONE
    sparse spec file took BOTH dashboard surfaces down with MemoryError and zero bytes of stdout while the
    two metrics surfaces stood the same source down by name. A section whose owner will not read STANDS
    DOWN with the reason NAMED, exactly as every delegation in the support pass does. The reason is now a
    STRING rather than a flag, because "no architecture contract (adoption safe)" was the only sentence
    this surface could say and it would have been a false reason for an owner that raised.

    AND THE OWNER THAT WILL NOT LOAD AT ALL stands the section down here too (round 11): an owner resolved to
    None is a DECLARED SOURCE that did not prove a complete read, and its own read record says which one and
    why. Round 10's guard covered only what the owner RAISED when CALLED."""
    if entropy is None:
        return _entropy_owner_standdown(), [], []
    # AND THE CALL GOES THROUGH THE ONE DELEGATION BOUNDARY: the owner reads specs/ ITSELF, so a spec file no
    # read may open BLOCKED both of these surfaces forever inside the owner's own open while the two metrics
    # surfaces stood the same store down by name. The KIND TEST asks first; the handler is the same one.
    report, delegation = kind.delegated("entropy_series_owner", ROOT,
                                        lambda: entropy.entropy_report(events=events), {})
    if delegation:
        return ("the entropy owner .veldo/entropy.py could not complete its own read (%s), so this section "
                "stands down: an owner that raised, or one this pass refused to hand a store it may not "
                "open, is not an absent contract" % delegation), [], []
    if report.get("standdown"):
        return "no architecture contract, standing down (adoption safe)", [], []
    return "", entropy.area_figures(report), report.get("crossings", [])


def _fmt(v, suffix=""):
    return "n/a" if v is None else f"{v}{suffix}"


def _rate_pct(rate):
    return "n/a" if rate is None else f"{round(rate * 100, 1)}%"


def _counts_str(counts):
    if not counts:
        return "none recorded"
    return ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))


def render_text(events, root=None, stream_shortfall=None):
    f = report_figures(events)
    rh = f["regression_health"]
    lines = [
        "VELDO metrics dashboard (rendered from events.jsonl via metrics.compute)",
        "=" * 64,
        f"  events observed:      {f['events_total']}  "
        f"({f['changes_tracked']} changes tracked)",
        f"  cycle time (avg):     {_fmt(f['cycle_time_hours'], ' h')}  "
        f"(spec.ready to spec.shipped, {f['cycle_time_samples']} shipped)",
        f"  proof latency (avg):  {_fmt(f['proof_latency_hours'], ' h')}  "
        f"(spec.ready to proof.recorded)",
        f"  human minutes:        {f['human_minutes']}  "
        f"by step {f['human_minutes_by_type'] or 'none'}",
        f"  gate pass rate:       {_rate_pct(f['gate_pass_rate'])}  "
        f"({f['gate_pass']} pass / {f['gate_fail']} fail)",
        f"  verdicts:             {_counts_str(f['verdict_counts'])}",
        f"  emergency debt:       {f['emergency_debt']}  (open emergency pushes)",
        f"  regression health:    current gate {rh['current_gate'] or 'n/a'}, "
        f"{rh['regressions']} regressions / {rh['recoveries']} recoveries "
        f"over {rh['gate_runs']} gate runs",
    ]
    if stream_shortfall:
        # THE UNREAD ARTIFACT ABOVE THE NUMBERS IT COST, never below them: every figure in the block above
        # is derived from NO recorded line, and a reader who sees the zeros first has already believed them.
        lines.insert(2, "  " + sreport.printable(stream_shortfall))
    standdown, figs, crossings = entropy_figures(events)
    lines.append("")
    lines.append("  entropy - cost-to-change per area (PLAN-0011 W8; advisory, never gates):")
    # THE AREA ID AND THE DIMENSION ARE READ OFF DISK (the architecture contract), and this is the ONE
    # remaining place a value from a file reached a print unsanitized: one non-ASCII area id exited the
    # WHOLE text dashboard 1 under an ASCII locale, taking every number above it with it. printable() is
    # identity on ASCII, so nothing a real contract renders moves. The HTML side already escapes through
    # _card. This is inside WARP-1210's footprint, whatever the number it interpolates belongs to.
    text = sreport.printable
    if standdown:
        lines.append("    " + text(standdown))
    else:
        for fig in figs:
            lt = fig["latest"]
            ss = fig["static_shape"]
            cal = " [calibrating]" if fig["calibrating"] else ""
            lines.append(f"    {text(fig['area'])}: {fig['samples']} sample(s){cal}  "
                         f"latest hm={lt['human_minutes']} tok={lt['tokens']} "
                         f"cyc={lt['review_cycles']}  static dup={ss['duplication']} "
                         f"cx={ss['complexity']} bpressure={ss['boundary_pressure']}")
        if crossings:
            lines.append("    crossings (feed WARP-1109 restoration):")
            for c in crossings:
                tag = "advisory" if c["advisory"] else "trusted"
                lines.append(f"      [{tag}] {text(c['area'])}.{text(c['dimension'])}: "
                             f"{c['latest']} vs baseline {c['baseline']}")
        else:
            lines.append("    crossings: none")
    # The support numbers (WARP-1210 W10), appended so every line above stays byte-identical: a
    # repository with no incident events reads exactly as it did before, plus one honest empty-state
    # line. This is metrics_support_report.support_lines verbatim, so the text report here and the
    # metrics CLI are the same bytes rather than two renderings that agree by inspection.
    lines.append("")
    lines.extend(sreport.support_lines(support_figures(events, root=root)))
    return "\n".join(lines)


def _card(label, value, sub=""):
    """ONE card, escaped for HTML and PRINTABLE on any output stream. printable() sits inside the escape
    for the same reason the text report's does: a card's sub-line quotes what was read off disk (a
    directory entry name, an incident id), this page is printed to stdout or written with the platform
    encoding, and one byte an ASCII stream cannot encode used to exit this surface 1 with NOTHING written
    at all. html.escape decides what is safe to put in a page; printable decides what can leave it."""
    text = sreport.printable
    sub_html = f'<div class="sub">{html.escape(text(sub))}</div>' if sub else ""
    return (
        '<div class="card">'
        f'<div class="label">{html.escape(text(label))}</div>'
        f'<div class="value">{html.escape(text(value))}</div>'
        f"{sub_html}</div>"
    )


def _dependence_cards(dependence):
    """The diagnosability score's DECLARED dependence, as its own card: BOTH halves named, never only the
    contract. Its own function because both the rendered section and the STAND-DOWN show it - a reader has
    to be told which half of the definition was available whether or not a number came out. The card carries
    NO MEASURE: its value names each half's state and its sub-line COUNTS the authenticated incidents whose
    contribution turns on one, which is a count of named incidents rather than a share, a rate or a trend."""
    if not isinstance(dependence, dict):
        return []
    halves = []
    if not dependence["area_half_available"]:
        halves.append("area half %s" % dependence["state"])
    if not dependence["spec_half_available"]:
        halves.append("spec half %s" % dependence["corpus_state"])
    return [_card("Diagnosability definition dependence",
                  ", ".join(halves) if halves else "both halves available",
                  "%s (%d authenticated incident(s) turn on it)"
                  % (dependence["detail"], dependence["not_counted_count"]))]


def _support_standdown_cards(model):
    """THE WHOLE SECTION, STOOD DOWN on the card surface because a declared source did not prove a COMPLETE
    read (AC3): the one stand-down card with its counts, one card per NAMED input (every incomplete source
    and every unreadable source), and the diagnosability definition's DECLARED dependence. NO measure card
    at all. Its own function because this is the presentation a human sees when the numbers are withheld,
    and because a branch this load-bearing should be readable on its own."""
    return [_card("Support numbers", "standing down",
                  "%d of %d declared source(s) did not prove a COMPLETE read and %d source(s) reported a "
                  "problem, so no number is rendered at all; %d input(s) excluded in all"
                  % (len(model.get("incomplete_sources") or ()),
                     len(model.get("sources_declared") or ()),
                     len(model.get("source_problems") or ()),
                     model.get("excluded_count") or 0))
            ] + [_card("%s %s" % (_e["kind"], _e["reason"]), _e["subject"], _e["detail"])
                 for _e in sreport.support_named_inputs(model)] \
        + _dependence_cards(model.get("contract_dependence"))


def _support_area_cards(area_map):
    """The incidents-per-area cards: the named stand-down or one card per area row, plus - on the surface
    the row count appears on - the UNATTRIBUTED incidents by id and the INCOMPLETE attribution. Round 4's
    note 5: the text report named both and the cards named neither, so a human reading the cards saw an
    area row count that looked complete."""
    cards = []
    if area_map["standdown"]:
        cards.append(_card("Incidents per area", "standing down",
                           "%s (soft join, never faked)" % area_map["standdown"]))
    for row in area_map["areas"]:
        cards.append(_card("area %s" % row["area"], "%d incident(s)" % row["incidents"],
                           row["cost_standdown"] or "cost-to-change %s sample(s)"
                           % (row["cost"] or {}).get("samples")))
    if area_map["unattributed"] and area_map["areas"]:
        cards.append(_card("Unattributed incidents", "%d of %d authenticated"
                           % (len(area_map["unattributed"]), area_map["population"]),
                           "never assigned to a default area: %s"
                           % ", ".join(area_map["unattributed"])))
    if area_map["detail"] and area_map["areas"]:
        cards.append(_card("ATTRIBUTION INCOMPLETE", support.SUPPORT_UNREADABLE_SPEC_CORPUS,
                           "rows survived an unreadable corpus, so the attribution above is INCOMPLETE "
                           "rather than wrong: %s" % area_map["detail"]))
    return cards


def _skipped_cards(model):
    """One card per entry the DECLARED SKIP RULE accounted for and did NOT read: the value is the entry with
    the reason it is not a record, the sub-line is the source it was found in. printable() rides inside
    _card, so an entry name no ASCII stream can encode is escaped here rather than fatal."""
    return [_card("Accounted and not read", entry["entry"], "in source %s" % entry["source"])
            for entry in model.get("read_skipped") or ()]


def _support_cards(model):
    """The support section's cards: what was ACCOUNTED AND NOT READ first, because that is a fact about the
    READ and belongs on every path, then the section itself. Two functions rather than one branch repeated
    inside four returns, so the skipped block cannot be lost on a path somebody adds later."""
    return _skipped_cards(model) + _support_state_cards(model)


def _support_state_cards(model):
    """The support section's cards, each value and each sub-line taken from the model
    metrics_support.support_numbers derived and metrics_support_report.support_lines renders as text: a
    measure with no population shows its NAMED stand-down instead of a number, every share carries its
    numerator and denominator, the authenticated-versus-excluded evidence base sits on its own card, and
    EVERY NAMED INPUT GETS ITS OWN CARD from the report layer's one named set. That last part is the
    round-2 finding: this surface used to publish a COUNT of exclusions and name none of them, so the
    number a human actually looks at was not diagnosable from the surface it appeared on. No number is
    computed here and no name is invented here.

    THE GOVERNING RULE IS OBEYED FIRST (AC3): unless every declared source proved a COMPLETE read, this
    surface shows the stand-down and its named sources and NO measure card at all. It is the surface a
    human actually looks at, so it is the surface where a plausible wrong number does the damage."""
    if not sreport.support_renderable(model):
        return _support_standdown_cards(model)
    if not model.get("closed_event_type"):
        # The named sources ride along with the stand-down here too: an owner that is PRESENT and
        # unreadable is a different fact from an absent one, and this surface has to say which.
        return [_card("Support numbers", "standing down",
                      "the incident lifecycle vocabulary owner is absent or supplied no close event type")
                ] + [_card("%s %s" % (_e["kind"], _e["reason"]), _e["subject"], _e["detail"])
                     for _e in sreport.support_named_inputs(model)]
    if sreport.support_empty(model):
        return [_card("Support numbers", "no incidents recorded",
                      "no incident lifecycle event and no reconciliation receipt (adoption safe)")]
    cards = [_card("Authenticated incidents",
                   "%d of %d" % (model["authenticated_count"], model["closed_events"]),
                   "closed events backed by a reconciliation receipt; %d receipt(s) read = %d backing "
                   "+ %d excluded and named; %d record(s) read = %d indexed + %d conflicted + %d "
                   "unidentified; %d input(s) excluded in all"
                   % (model["receipts_read"], model["receipts_backing"], model["receipts_excluded"],
                      model["records_read"], model["records_indexed"], model["records_conflicted"],
                      model["records_unidentified"], model["excluded_count"]))]
    # EVERY NAMED INPUT, ON ITS OWN CARD, from the SAME list the text report names: an unreadable source,
    # an excluded input, an unresolved recurrence reference, an unusable interval. A selftest asserts this
    # surface and the text surface carry the identical named set.
    for entry in sreport.support_named_inputs(model):
        cards.append(_card("%s %s" % (entry["kind"], entry["reason"]), entry["subject"],
                           entry["detail"]))
    for key, label in (("time_to_diagnosis", "Time to diagnosis"), ("time_to_restore", "Time to restore")):
        t = model[key]
        # An UNUSABLE interval is named on the card too, never only in the text report: a sample count
        # short of the population must be explained on whichever surface the reader is looking at.
        unusable = ("; %d %s named" % (t["unusable_count"], support.SUPPORT_UNUSABLE_INTERVAL)
                    if t.get("unusable_count") else "")
        cards.append(_card(label, "standing down" if t["standdown"] else "median %s h" % t["median"],
                           (t["standdown"] or "latest %s h over %d of %d authenticated (%s)"
                            % (t["latest"], t["samples"], t["population"], t["reading"])) + unusable))
    for key, label in (("recurrence_rate", "Recurrence rate"), ("diagnosability_score", "Diagnosability score")):
        s = model[key]
        cards.append(_card(label, "standing down" if s["standdown"] else "%s%%" % s["percent"],
                           s["standdown"] or "%d of %d %s" % (s["numerator"], s["denominator"], s["of"])))
    # The diagnosability score's DECLARED dependence, on its own card beside the score rather than in a
    # footnote: the score is not contract-independent and a reader must be told so here too. BOTH HALVES
    # are named, never only the contract: with an unreadable corpus this card used to affirm that the area
    # half was available and say nothing about the corpus while the score had already gone to zero.
    cards += _dependence_cards(model["contract_dependence"])
    return cards + _support_area_cards(model["incidents_per_area"])


def render_html(events, root=None, stream_shortfall=None):
    """A self-contained HTML page: inline CSS only, no external asset, script,
    font, or network request, so it renders offline and travels as one file.
    """
    f = report_figures(events)
    rh = f["regression_health"]
    gate = rh["current_gate"] or "n/a"
    cards = [
        _card("Cycle time (avg)", _fmt(f["cycle_time_hours"], " h"),
              f"spec.ready to spec.shipped, {f['cycle_time_samples']} shipped"),
        _card("Proof latency (avg)", _fmt(f["proof_latency_hours"], " h"),
              "spec.ready to proof.recorded"),
        _card("Human minutes", f["human_minutes"], "the scarce resource"),
        _card("Gate pass rate", _rate_pct(f["gate_pass_rate"]),
              f"{f['gate_pass']} pass / {f['gate_fail']} fail"),
        _card("Verdicts", _counts_str(f["verdict_counts"]), "review outcomes"),
        _card("Emergency debt", f["emergency_debt"], "open emergency pushes"),
        _card("Regression health", f"gate {gate}",
              f"{rh['regressions']} regressions / {rh['recoveries']} "
              f"recoveries over {rh['gate_runs']} runs"),
        _card("Events observed", f["events_total"],
              f"{f['changes_tracked']} changes tracked"),
    ]
    if stream_shortfall:
        # THE UNREAD ARTIFACT AS ITS OWN CARD on the surface a human actually looks at, inserted FIRST
        # rather than appended: the cards above it are all derived from no recorded line at all.
        cards.insert(0, _card("Recorded event stream", "UNREAD", stream_shortfall))
    style = (
        "body{font-family:system-ui,sans-serif;margin:0;padding:2rem;"
        "background:#0f1115;color:#e6e6e6}"
        "h1{font-size:1.25rem;font-weight:600;margin:0 0 1.25rem}"
        ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));"
        "gap:1rem}"
        ".card{background:#1a1d24;border:1px solid #2a2f3a;border-radius:10px;"
        "padding:1rem 1.1rem}"
        ".label{font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;"
        "color:#8b93a1}"
        ".value{font-size:1.6rem;font-weight:600;margin:.35rem 0 .2rem;"
        "word-break:break-word}"
        ".sub{font-size:.78rem;color:#8b93a1}"
        "footer{margin-top:1.5rem;font-size:.72rem;color:#5f6672}"
        "@media (prefers-color-scheme:light){body{background:#f6f7f9;color:#1a1d24}"
        ".card{background:#fff;border-color:#e2e5ea}.label,.sub{color:#5f6672}}"
    )
    standdown, figs, crossings = entropy_figures(events)
    ecards = []
    if standdown:
        # THE REASON, NOT A FIXED SENTENCE: this card said "no architecture contract (adoption safe)"
        # whatever stood the section down, which would have been a FALSE reason for an owner that raised -
        # the shape round 10 measured taking both of these surfaces down on one sparse spec file.
        ecards.append(_card("Entropy", "standing down", standdown))
    else:
        for fig in figs:
            lt = fig["latest"]
            ss = fig["static_shape"]
            sub = (f"latest hm {lt['human_minutes']}, tok {lt['tokens']}; "
                   f"static dup {ss['duplication']}, cx {ss['complexity']}, "
                   f"bpressure {ss['boundary_pressure']}"
                   + (" (calibrating)" if fig["calibrating"] else ""))
            ecards.append(_card(f"area {fig['area']}", f"{fig['samples']} sample(s)", sub))
        ecards.append(_card("Crossings", len(crossings),
                            "relative-baseline degradations feeding WARP-1109" if crossings
                            else "none (advisory, never gates)"))
    entropy_section = (
        "<h1>Entropy - cost-to-change per area</h1>"
        f'<div class="grid">{"".join(ecards)}</div>'
    )
    # The support numbers (WARP-1210 W10), inserted between the entropy section and the footer so every
    # byte above and below stays exactly as it was: a repository with no incident events renders as
    # before plus one honest empty-state card.
    support_section = (
        "<h1>Support numbers - authenticated against the reconciliation receipts</h1>"
        f'<div class="grid">{"".join(_support_cards(support_figures(events, root=root)))}</div>'
    )
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>VELDO metrics dashboard</title>"
        f"<style>{style}</style></head><body>"
        "<h1>VELDO metrics dashboard</h1>"
        f'<div class="grid">{"".join(cards)}</div>'
        f"{entropy_section}"
        f"{support_section}"
        "<footer>Rendered from events.jsonl via metrics.compute and entropy.entropy_report - the "
        "single sources of truth. This dashboard renders those numbers; it never recomputes "
        "them.</footer>"
        "</body></html>"
    )


def main():
    ap = argparse.ArgumentParser(description="Render the VELDO metrics dashboard.")
    ap.add_argument("--html", action="store_true", help="render self-contained HTML")
    ap.add_argument("--out", help="write output to this file instead of stdout")
    args = ap.parse_args()
    # THE ACCOUNTED READ of the one recorded artifact both sections rest on: the events AND, when the stream
    # exists and could not be read, the SHORTFALL that names it. Before round 10 this line was
    # metrics.load(), whose whole-file read sat inside no handler, so a mode-000 events.jsonl exited BOTH
    # surfaces here 1 with nothing written at all.
    events, stream_shortfall = metrics.load_accounted()
    out = (render_html(events, stream_shortfall=stream_shortfall) if args.html
           else render_text(events, stream_shortfall=stream_shortfall))
    if args.out:
        Path(args.out).write_text(out)
        print(f"wrote {'HTML' if args.html else 'text'} dashboard to {args.out}")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
