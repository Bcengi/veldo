#!/usr/bin/env python3
"""VELDO support numbers: the REPORT layer - the named set and the text (WARP-1210).

The third module of the support pass, and the one every SURFACE reads. The pure
derivation (.veldo/metrics_support.py) decides every number, every exclusion and
every stand-down; the wired readers (.veldo/metrics_readers.py) gather its inputs;
this module turns that model into what a human reads:

  support_named_inputs(model)  THE ONE NAMED SET: every source that did not
                               prove a COMPLETE read and every input the
                               derivation could not use, with its reason, its
                               subject and its detail. The metrics CLI's text
                               report, its --json and .veldo/dashboard.py's HTML
                               cards are three PRESENTATIONS of this ONE list,
                               which is what keeps them from disagreeing.
                               Claiming "one renderer" was false while the text
                               named four excluded inputs and the HTML named none
                               of them; a selftest now asserts all three surfaces
                               carry every entry of this set.
  support_renderable(model)    THE GOVERNING RULE, obeyed: no measure reaches
                               ANY of the three surfaces unless every declared
                               source proved it read completely.
  support_lines(model)         the TEXT presentation, used by the metrics CLI
                               and by the dashboard's text report.
  support_json(model)          the MACHINE-READABLE presentation, under the same
                               rule: the model when it is renderable, and the
                               completeness verdict with the named set and NO
                               measure when it is not.

WHY IT IS ITS OWN MODULE: the round-3 sweep of the two defect classes took the
derivation past the 1000-line module budget, and a module that both derives and
presents has two jobs. The seam is MODEL versus REPORT, the same rule the round-2
split applied to metrics.py, and it makes the two-presentations fix structural
rather than a promise: one naming source, read by all three surfaces.

Pure, like the derivation it renders: no file, no clock, no network, nothing
written. It loads the DECLARED CONTRACT by path for the closed set of reason
names, so the taxonomy still has exactly one owner - and it no longer loads the
derivation at all, because a layer that renders a MODEL needs the vocabulary, not
the arithmetic.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# THE DECLARED CONTRACT, bound at import for the closed set of reason names and the non-empty-string
# predicate. No name is restated here: a stand-down this layer renders is a stand-down the derivation
# decided, under the name the contract declared.
_ctspec = importlib.util.spec_from_file_location("veldo_metrics_support_contract_for_report",
                                                 ROOT / ".veldo" / "metrics_support_contract.py")
_contract = importlib.util.module_from_spec(_ctspec)
_ctspec.loader.exec_module(_contract)
_is_str = _contract._is_str
printable = _contract.printable
SUPPORT_UNRESOLVED_RECEIPT = _contract.SUPPORT_UNRESOLVED_RECEIPT
SUPPORT_CONFLICTING_RECEIPTS = _contract.SUPPORT_CONFLICTING_RECEIPTS
SUPPORT_UNRESOLVED_RECURRENCE = _contract.SUPPORT_UNRESOLVED_RECURRENCE
SUPPORT_NO_ARCHITECTURE_CONTRACT = _contract.SUPPORT_NO_ARCHITECTURE_CONTRACT
SUPPORT_UNREADABLE_ARCHITECTURE_CONTRACT = _contract.SUPPORT_UNREADABLE_ARCHITECTURE_CONTRACT
SUPPORT_UNREADABLE_SPEC_CORPUS = _contract.SUPPORT_UNREADABLE_SPEC_CORPUS
SUPPORT_INCOMPLETE_READ = _contract.SUPPORT_INCOMPLETE_READ


def support_renderable(model):
    """WHETHER ANY SUPPORT NUMBER MAY BE RENDERED AT ALL - the governing rule (AC3) as the surfaces see
    it. The DERIVATION decides it (support_numbers marks the model), because a decision belongs where the
    other decisions are; this reads that mark and, like read_proves_complete, grants it only on a POSITIVE
    match: a model that is not a mapping, one from a version that does not carry the mark, or one carrying
    anything other than True renders NOTHING. A missing key is therefore a stand-down and never a
    number."""
    return isinstance(model, dict) and model.get("renderable") is True


# WHAT SURVIVES A STAND-DOWN ON THE MACHINE-READABLE SURFACE: the model's own account of WHY there is no
# number, and nothing that could be read as a MEASURE. Every key here is a verdict, a name, or a count of
# what this pass COULD NOT USE - and round 10 states that precisely, because the sentence here said "not one
# is a count of authenticated incidents" while contract_dependence carried not_counted_count and the ids of
# the authenticated incidents it counts (round-9 note 1: the property held, the sentence did not). EXACTLY
# TWO NUMERIC LEAVES REACH THIS SURFACE WHEN IT STANDS DOWN, both counts of a shortfall and neither a
# measure: incomplete_source_count (how many DECLARED SOURCES did not prove a complete read) and
# contract_dependence.not_counted_count (how many AUTHENTICATED INCIDENTS have a contribution that turns on
# the contract half of the diagnosability definition, named individually beside it). NO trend, share,
# percent, median, population, authenticated count or area row appears, which a selftest asserts by walking
# every numeric leaf of a stood-down answer rather than by reading this list.
SUPPORT_JSON_VERDICT = ("renderable", "incomplete_sources", "incomplete_source_count",
                        "sources_affirmed", "sources_declared", "source_problems", "read_skipped",
                        "closed_event_type", "contract_dependence", "review_lane")


def support_json(model):
    """THE MACHINE-READABLE PRESENTATION, under the SAME governing rule as the two human ones (AC3): the
    model as it stands when every declared source proved a COMPLETE read, and WITHOUT A SINGLE MEASURE when
    one did not.

    Round 5 printed the whole model unconditionally here, so a broken data path emitted
    diagnosability_score 0.0 percent and recurrence_rate 0.0 percent beside renderable false while this
    pass's own docstring, in eight shipped copies, said no surface renders a measure while renderable is
    False (R5-B1). Nothing consumes this surface yet, which is exactly why it was worth fixing before
    something does: a machine reading a number this pass refuses to show a human is the same lie with a
    longer fuse. THREE SURFACES, ONE RULE.

    A stood-down answer carries the completeness verdict, the declared and affirmed sources, the ONE NAMED
    SET both human surfaces show, every entry the DECLARED SKIP RULE accounted for and did not read, the
    diagnosability definition's declared dependence (which carries NO MEASURE: it names the STATE of each
    half and the authenticated incidents whose contribution turns on one of them), and the WITHHELD key list
    - so a consumer sees a REFUSAL it can act on rather than a silence, and never an empty repository."""
    if support_renderable(model):
        return model
    kept = {key: model[key] for key in SUPPORT_JSON_VERDICT if key in model}
    kept["named_inputs"] = support_named_inputs(model)
    kept["withheld"] = sorted(key for key in model if key not in kept)
    kept["withheld_because"] = (
        "EVERY MEASURE IS WITHHELD: a declared source did not prove it read COMPLETELY, so this surface "
        "renders no number at all, exactly as the text report and the dashboard cards do not. The model "
        "still DERIVED them (a stand-down nobody can diagnose is its own defect); incomplete_sources and "
        "named_inputs say which source fell short and why, and `withheld` names every key held back.")
    return kept


def support_empty(model):
    """Whether this is a repository that never opened an incident: no closed lifecycle event, no
    receipt, nothing excluded, AND no source that could not be read or that did not prove a complete
    read. Rendered as ONE honest empty-state line rather than an error or a row of zeros. An unreadable
    or unproven source can never hide behind the empty state: "nothing happened here" and "nothing could
    be read here" are different facts."""
    return not (model.get("closed_events") or model.get("receipts_read") or model.get("excluded")
                or model.get("source_problems") or model.get("incomplete_sources"))


def _support_subject(entry):
    """The NAMED subject of one exclusion: the incident id, and the receipt id too when a receipt is
    what could not be resolved, what conflicts with another, or what named a recurrence nothing
    carries, so a surprising number is diagnosable from the output alone."""
    if entry.get("reason") in (SUPPORT_UNRESOLVED_RECEIPT, SUPPORT_CONFLICTING_RECEIPTS,
                               SUPPORT_UNRESOLVED_RECURRENCE):
        return "receipt %s (incident %s)" % (entry.get("receipt") or "unnamed",
                                             entry.get("incident") or "unnamed")
    return "incident %s" % (entry.get("incident") or "unnamed")


def support_named_inputs(model):
    """THE ONE NAMED SET ALL THREE SURFACES RENDER: every input this derivation could not use, as
    {kind, reason, subject, detail}. The text report lists them, the HTML dashboard gives each its own card
    and the machine surface carries the list itself, so the three surfaces are three PRESENTATIONS of this
    one list rather than three renderers that can drift - which they had, with four exclusions live, the
    text naming each one and the HTML naming a total and nothing else. A selftest asserts all three surfaces
    carry every entry of this set.

    Ordered deliberately: the INCOMPLETE SOURCES first, because a source that did not prove it read
    completely takes the whole section down and nothing else on the surface matters until it is fixed;
    then the UNREADABLE SOURCES, because a number computed over a source nobody could read is the next
    thing a reader has to know; then the EXCLUDED inputs; then the UNRESOLVED recurrence references; then
    the UNUSABLE intervals, which the text also repeats beside the trend they belong to (the one place a
    reader looking at a sample count needs them).

    This set is the MODEL's own list and is not sanitized here: every string in it arrived through an
    INGEST boundary that already made it printable (the read constructors and the reader problem record),
    and the two EGRESS boundaries that write to a stream - support_lines for the text and the dashboard's
    card for the HTML - each apply printable() once. WHAT EACH OF THE FOUR IS LOAD-BEARING FOR is not the
    same thing, and round 6 said it was: the two EGRESS points each keep THEIR OWN SURFACE alive (remove
    one and that surface exits 1 at the print), while the two INGEST points keep the MODEL itself printable
    for whoever reads it without a surface - removing one alone moves no rendered byte, which is exactly
    what the teeth matrix's empty off-diagonal shows."""
    named = [{"kind": "INCOMPLETE SOURCE", "reason": e["reason"],
              "subject": "source %s (%s)" % (e["source"], e["subject"]), "detail": e["detail"]}
             for e in model.get("incomplete_sources") or ()]
    named += [{"kind": "UNREADABLE SOURCE", "reason": e["reason"],
               "subject": "source %s (%s)" % (e["source"], e["subject"]), "detail": e["detail"]}
              for e in model.get("source_problems") or ()]
    named += [{"kind": "EXCLUDED", "reason": e["reason"], "subject": _support_subject(e),
               "detail": e["detail"]} for e in model.get("excluded") or ()]
    named += [{"kind": "UNRESOLVED", "reason": e["reason"], "subject": _support_subject(e),
               "detail": e["detail"]} for e in model.get("recurrence_unresolved") or ()]
    for key in ("time_to_diagnosis", "time_to_restore"):
        named += [{"kind": "UNUSABLE", "reason": u["reason"],
                   "subject": "incident %s" % u["incident"], "detail": u["detail"]}
                  for u in (model.get(key) or {}).get("unusable") or ()]
    return named


def _support_named_line(entry, pad):
    """One named input as one text line, in the ONE format every surface and every block uses."""
    return pad + "  %s %s %s: %s" % (entry["kind"], entry["reason"], entry["subject"], entry["detail"])


def support_skipped_lines(model, pad):
    """WHAT WAS ACCOUNTED FOR AND NOT READ, as text lines: one line per entry the DECLARED SKIP RULE
    dismissed, with the source it was found in and the reason it is not a record. Its own block, before the
    render decision, so it appears whether the section renders or stands down - an entry nobody read is a
    fact about the read rather than about the numbers. Empty for a store that holds only records, which is
    why a healthy repository's section is byte-identical to what it was."""
    return [pad + "accounted and NOT read (%s): %s" % (entry["source"], entry["entry"])
            for entry in model.get("read_skipped") or ()]


def _support_trend_lines(trend, label, pad):
    """One trend's lines: the named stand-down, or the median and the latest WITH the sample count
    against the authenticated population, plus the per-incident values in RECORDED order. Every
    UNUSABLE interval is named on its own line either way, through the ONE named-input formatter, so an
    incident whose timeline yielded no interval is visible rather than a silently missing sample."""
    unusable = [_support_named_line({"kind": "UNUSABLE", "reason": u["reason"],
                                     "subject": "incident %s" % u["incident"], "detail": u["detail"]},
                                    pad)
                for u in trend.get("unusable") or ()]
    if trend["standdown"]:
        return [pad + "%s: STANDING DOWN (%s): none of the %d authenticated incident(s) records a "
                      "usable %s" % (label, trend["standdown"], trend["population"],
                                     trend["field"])] + unusable
    return [pad + "%s: median %s h, latest %s h over %d observation(s) of %d authenticated "
                  "incident(s) [%s]" % (label, trend["median"], trend["latest"], trend["samples"],
                                        trend["population"], trend["reading"]),
            pad + "  values in recorded order: "
            + ", ".join("%s %s h" % (o["incident"], o["hours"]) for o in trend["observations"])
            ] + unusable


def _support_share_lines(share, label, pad):
    """One share's line: the named stand-down over an empty population, or the percent WITH its
    numerator and denominator beside it, so one incident never hides behind 100 percent."""
    if share["standdown"]:
        return [pad + "%s: STANDING DOWN (%s): the population is 0 authenticated closed incident(s), "
                      "so there is no rate to report (a rate with no population is not a rate)"
                % (label, share["standdown"])]
    return [pad + "%s: %s%% (%d of %d %s)" % (label, share["percent"], share["numerator"],
                                              share["denominator"], share["of"])]


def _support_dependence_lines(dependence, pad):
    """The diagnosability score's DECLARED CONTRACT DEPENDENCE, rendered directly beneath the score it
    qualifies rather than in a footnote or a docstring nobody reads. Always one line (a reader must see
    the dependence whether or not it bit here), plus one named line per authenticated incident whose
    contribution turns on the contract, so the number is never read as contract-independent."""
    lines = [pad + "  contract dependence (DECLARED, not a claim of invariance): %s"
             % dependence["detail"]]
    for entry in dependence["not_counted"]:
        lines.append(pad + "    NOT COUNTED incident %s: it resolves to no governing spec in the "
                           "corpus and to no declared contract area (it declares area %r, spec %r, so "
                           "its contribution turns on the %s)"
                     % (entry["incident"], entry["affected_area"], entry["affected_spec"],
                        entry["turns_on"]))
    return lines


def _support_area_lines(area_map, pad):
    """The incidents-per-area map's lines: the named stand-down, or one row per area with its incident
    count and either the joined cost-to-change figures or the named cost stand-down, plus every
    unattributable incident listed by id (never assigned to a default area)."""
    lines = [pad + "incidents per area (soft join with PLAN-0011 cost-to-change per area; stands down "
                   "by name, never faked):"]
    if area_map["standdown"] in (SUPPORT_NO_ARCHITECTURE_CONTRACT,
                                SUPPORT_UNREADABLE_ARCHITECTURE_CONTRACT,
                                SUPPORT_UNREADABLE_SPEC_CORPUS):
        return lines + [pad + "  STANDING DOWN (%s): %s" % (area_map["standdown"], area_map["detail"])]
    if area_map["standdown"]:
        lines.append(pad + "  STANDING DOWN (%s): no authenticated incident attributes to a declared "
                           "area (%d of %d unattributed)"
                     % (area_map["standdown"], len(area_map["unattributed"]), area_map["population"]))
    for row in area_map["areas"]:
        latest = (row["cost"] or {}).get("latest") or {}
        cost = ("cost-to-change STANDING DOWN (%s)" % row["cost_standdown"] if row["cost_standdown"]
                else "cost-to-change %s sample(s), latest human_minutes=%s tokens=%s review_cycles=%s"
                % (row["cost"].get("samples"), latest.get("human_minutes"), latest.get("tokens"),
                   latest.get("review_cycles")))
        lines.append(pad + "  %s: %d incident(s) of %d authenticated; %s"
                     % (row["area"], row["incidents"], area_map["population"], cost))
    if area_map["unattributed"] and area_map["areas"]:
        lines.append(pad + "  unattributed (never assigned to a default area): "
                     + ", ".join(area_map["unattributed"]))
    if area_map["detail"] and area_map["areas"]:
        # Rows survived an unreadable corpus, so the attribution is INCOMPLETE rather than wrong: named
        # here beside the rows, because a reader of a row count must know what it could not see.
        lines.append(pad + "  ATTRIBUTION INCOMPLETE (%s): %s"
                     % (SUPPORT_UNREADABLE_SPEC_CORPUS, area_map["detail"]))
    return lines


def support_standdown_lines(model, pad):
    """THE WHOLE SECTION, STOOD DOWN because a declared source did not prove a COMPLETE read (AC3): the
    one stand-down line, then every NAMED input, then the diagnosability definition's DECLARED dependence.
    NO measure, NO share, NO trend, NO area row and NO count of authenticated incidents appears here - a
    number derived over a source nobody could read is the thing this item exists to prevent, and the four
    reviews before this one each found one being rendered.

    What DOES appear is everything a human needs to fix it: which sources fell short, under which declared
    name, and why. A blank stand-down would be its own defect. The dependence lines carry NO MEASURE either,
    which is a narrower claim than round 6 made: they state which half of the diagnosability definition was
    available (a property of the definition) and they NAME each authenticated incident whose contribution
    turns on a half, one line each - so the reader can count them, and no share, rate or trend is shown."""
    incomplete = model.get("incomplete_sources") or ()
    problems = model.get("source_problems") or ()
    lines = [pad + "SECTION STANDING DOWN: %d of %d declared source(s) did not prove a COMPLETE read and "
                   "%d source(s) reported a problem, so NO support number is rendered at all (every "
                   "source proves it read completely, or no number: an unproven read is never treated as "
                   "an absence)" % (len(incomplete), len(model.get("sources_declared") or ()),
                                    len(problems))]
    lines += [_support_named_line(entry, pad) for entry in support_named_inputs(model)]
    if isinstance(model.get("contract_dependence"), dict):
        lines += _support_dependence_lines(model["contract_dependence"], pad)
    return lines


def support_lines(model, indent="  "):
    """The support section as TEXT lines, EVERY ONE OF THEM PRINTABLE on any output stream. This is the ONE
    place a rendered line becomes stream-safe, and it is load-bearing rather than defensive: the section's
    details quote what was read off disk (a directory entry name, a receipt id, an incident title), the
    stream that prints them may be ASCII (LANG=C is the common cron and CI case), and the print comes AFTER
    the loop measures have already been written - so one unencodable byte cost a reader every PRE-EXISTING
    number too, on the stand-down path this item exists to keep standing. _support_section_lines decides
    what is said; this decides that it can be said out loud."""
    return [printable(line) for line in _support_section_lines(model, indent)]


def _support_section_lines(model, indent="  "):
    """The support section as TEXT lines: the metrics CLI's surface, and the dashboard's text report.
    The HTML dashboard is ANOTHER presentation of the same model; what keeps them from disagreeing is
    support_named_inputs (the one named set all three render), not a shared renderer. The
    authenticated-versus-excluded counts sit BESIDE the numbers rather than in a footnote, every
    unreadable source and every excluded input is listed BY NAME with its id, every share carries its
    numerator and denominator, and every stand-down is NAMED from the closed set.

    THE FIRST DECISION IS THE GOVERNING RULE: unless every declared source proved a COMPLETE read, this
    renders the stand-down and no number. It comes FIRST, before the vocabulary stand-down and before the
    empty state, because a source that could not be read is not an absent vocabulary and not an empty
    repository, and reading it as either is exactly the conflation this item failed four reviews on."""
    pad = indent + "  "
    lines = [indent + "support numbers (WARP-1210 W10: time-to-diagnosis, time-to-restore, recurrence "
                      "rate, diagnosability score; authenticated against the reconciliation receipts):"]
    # WHAT WAS NOT READ COMES FIRST AND ON EVERY PATH: a skipped entry is a fact about the read, so it is
    # not the stand-down's business and not the render's - it belongs to both.
    lines += support_skipped_lines(model, pad)
    if not support_renderable(model):
        return lines + support_standdown_lines(model, pad)
    if not _is_str(model.get("closed_event_type")):
        # The stand-down comes FIRST and the named sources come with it: "the owner is absent" is the
        # adoption-safe case, and an owner that is PRESENT and unreadable must not borrow that sentence.
        return lines + [pad + "the incident lifecycle vocabulary owner is absent or supplied no close "
                              "event type, so nothing is recognized: standing down (adoption safe)"] \
            + [_support_named_line(_e, pad) for _e in support_named_inputs(model)]
    if support_empty(model):
        return lines + [pad + "no incident lifecycle event and no reconciliation receipt recorded: "
                              "standing down as an honest empty state, not a row of zeros (adoption "
                              "safe)"]
    lines.append(pad + "authenticated: %d of %d closed incident(s) backed by a receipt that resolves "
                       "to them (%d receipt(s) read, %d incident record(s) read, %d input(s) excluded)"
                 % (model["authenticated_count"], model["closed_events"], model["receipts_read"],
                    model["records_read"], model["excluded_count"]))
    # THE RECEIPT ARITHMETIC, spelled out so it can be checked rather than trusted: every receipt read
    # either backs exactly one authenticated closure or is excluded and named, and the two figures are
    # COUNTED independently. A header that reported "2 read, 1 authenticated, 0 excluded" was the
    # round-1 review's F3 in one line.
    lines.append(pad + "  receipt arithmetic: %d read = %d backing a closed incident + %d "
                       "excluded and named" % (model["receipts_read"], model["receipts_backing"],
                                               model["receipts_excluded"]))
    # THE RECORD ARITHMETIC, the same discipline one collection over, because round 2 found the records
    # index silently dropping a duplicate id: every record read is either indexed by its id, or excluded
    # and named as a conflict, or carries no usable id at all.
    lines.append(pad + "  record arithmetic: %d read = %d indexed by id + %d excluded and named + %d "
                       "carrying no usable id" % (model["records_read"], model["records_indexed"],
                                                  model["records_conflicted"],
                                                  model["records_unidentified"]))
    for entry in support_named_inputs(model):
        if entry["kind"] != "UNUSABLE":
            lines.append(_support_named_line(entry, pad))
    lines += _support_trend_lines(model["time_to_diagnosis"], "time-to-diagnosis", pad)
    lines += _support_trend_lines(model["time_to_restore"], "time-to-restore", pad)
    lines += _support_share_lines(model["recurrence_rate"], "recurrence rate", pad)
    lines += _support_share_lines(model["diagnosability_score"], "diagnosability score", pad)
    lines += _support_dependence_lines(model["contract_dependence"], pad)
    lines += _support_area_lines(model["incidents_per_area"], pad)
    return lines + [pad + model["review_lane"]]

