#!/usr/bin/env python3
"""VELDO support numbers: the PURE derivation (WARP-1210).

The second derivation of the metrics area, extracted from .veldo/metrics.py so
each module has one job: .veldo/metrics_support_contract.py declares the names,
the source table and the COMPLETENESS RULE, this module decides every number,
.veldo/metrics_readers.py is the ONE impure edge that gathers its inputs, and
.veldo/metrics_support_report.py turns the model into the ONE NAMED SET that all
THREE surfaces (the CLI's text, the CLI's --json and the dashboard's HTML)
present. Nothing here reads a
file, a clock, a network or an environment: EVERY input arrives from the caller,
which is what makes the same inputs give the same numbers across processes and
every stand-down testable with no filesystem at all.

THE GOVERNING RULE ARRIVES AS AN INPUT LIKE EVERYTHING ELSE: the readers hand in
one READ RECORD per declared source, each carrying a POSITIVE ASSERTION that the
read was COMPLETE, and this derivation renders NO number at all unless every
declared source proved it (contract.support_completeness). It still computes the
model - the numbers, the exclusions and the named sources are all decided here,
so the stand-down is diagnosable rather than blank - and it marks the model
NOT RENDERABLE, which all three surfaces obey. A source that cannot prove a
complete read is never treated as an absent one.

A DUPLICATE KEY IS NEVER RESOLVED BY COLLECTION ORDER either: SUPPORT_ID_KEYED
declares every dict this pass keys by an id it read, with the conflict it refuses
or the reason it cannot conflict.

  from the caller's side: support_numbers(events, **load_support_inputs())
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# THE ONE TIMESTAMP READER, BOUND from the core derivation at import rather than reimplemented, so this
# module ships no second date parser and no second answer to "what is an unreadable timestamp" (it is
# None, never a zero).
_cspec = importlib.util.spec_from_file_location("veldo_metrics_core_for_support",
                                                ROOT / ".veldo" / "metrics.py")
_core = importlib.util.module_from_spec(_cspec)
_cspec.loader.exec_module(_core)
parse_iso = _core.parse_iso

# THE DECLARED CONTRACT, bound the same way: the closed set of names, the source table, the id-keyed
# register, the rounding, the review lane and the ONE completeness decision. Every name this derivation
# uses is RE-EXPORTED from that owner rather than restated, so there is exactly one place a reason name
# is spelled and the report layer, the readers and this module cannot drift on one.
_ctspec = importlib.util.spec_from_file_location("veldo_metrics_support_contract_for_support",
                                                 ROOT / ".veldo" / "metrics_support_contract.py")
_contract = importlib.util.module_from_spec(_ctspec)
_ctspec.loader.exec_module(_contract)
_is_str = _contract._is_str
SUPPORT_SOURCES = _contract.SUPPORT_SOURCES
SUPPORT_ID_KEYED = _contract.SUPPORT_ID_KEYED
SUPPORT_REASONS = _contract.SUPPORT_REASONS
SUPPORT_RECEIPT_SCHEMA = _contract.SUPPORT_RECEIPT_SCHEMA
SUPPORT_ROUNDING = _contract.SUPPORT_ROUNDING
SUPPORT_REVIEW_LANE = _contract.SUPPORT_REVIEW_LANE
SUPPORT_READ_COMPLETE = _contract.SUPPORT_READ_COMPLETE
SUPPORT_UNBACKED_EVENT = _contract.SUPPORT_UNBACKED_EVENT
SUPPORT_UNRESOLVED_RECEIPT = _contract.SUPPORT_UNRESOLVED_RECEIPT
SUPPORT_CONFLICTING_RECEIPTS = _contract.SUPPORT_CONFLICTING_RECEIPTS
SUPPORT_CONFLICTING_RECORDS = _contract.SUPPORT_CONFLICTING_RECORDS
SUPPORT_UNRESOLVED_RECURRENCE = _contract.SUPPORT_UNRESOLVED_RECURRENCE
SUPPORT_UNUSABLE_INTERVAL = _contract.SUPPORT_UNUSABLE_INTERVAL
SUPPORT_UNREADABLE_TIMESTAMP = _contract.SUPPORT_UNREADABLE_TIMESTAMP
SUPPORT_EMPTY_DENOMINATOR = _contract.SUPPORT_EMPTY_DENOMINATOR
SUPPORT_NO_AREA_COST_DATA = _contract.SUPPORT_NO_AREA_COST_DATA
SUPPORT_UNREADABLE_AREA_COST_DATA = _contract.SUPPORT_UNREADABLE_AREA_COST_DATA
SUPPORT_NO_ARCHITECTURE_CONTRACT = _contract.SUPPORT_NO_ARCHITECTURE_CONTRACT
SUPPORT_UNREADABLE_ARCHITECTURE_CONTRACT = _contract.SUPPORT_UNREADABLE_ARCHITECTURE_CONTRACT
SUPPORT_NO_SPEC_CORPUS = _contract.SUPPORT_NO_SPEC_CORPUS
SUPPORT_UNREADABLE_SPEC_CORPUS = _contract.SUPPORT_UNREADABLE_SPEC_CORPUS
SUPPORT_INCOMPLETE_READ = _contract.SUPPORT_INCOMPLETE_READ
source_problem_detail = _contract.source_problem_detail
support_source_problems = _contract.support_source_problems
support_completeness = _contract.support_completeness
read_proves_complete = _contract.read_proves_complete

# --- the support numbers (WARP-1210, W10 of PLAN-0012, the second half of outcome O6) -------------
# Support gets NUMBERS: time-to-diagnosis and time-to-restore trending, the recurrence rate, the
# diagnosability score, and incidents-per-area joined with PLAN-0011's cost-to-change data. Every one
# is derived from artifacts the loop ALREADY wrote (the incident lifecycle events, the incident
# records' RECORDED timelines, and the reconciliation receipts): no new store, no new event type, no
# new instrumentation, and nothing read from a live system.
#
# THE AUTHENTICATION IS THE SPINE, and it is the direct consequence of a review finding rather than an
# invention: WARP-1208 added the incident lifecycle to the gate's recognition set, which was correct
# and necessary, and the side effect is that RECOGNITION IS NOT AUTHENTICATION. Any writer can append
# an incident.closed, so every measure below counts ONLY an incident whose closure is BACKED by a
# reconciliation receipt that resolves to that incident id. The receipts are the AUTHORITY; the events
# are the INDEX; an unbacked event and an unresolvable receipt are each EXCLUDED and NAMED.
#
# HONESTY OF NUMBERS is the property this derivation is judged on rather than safety of action, so: no
# rate is rendered over an empty population, every share carries its numerator and denominator, a trend
# is a trend (the per-incident values in recorded order plus the median and the latest) and never a
# single average that hides a regression, an area is never invented, and every excluded or unresolvable
# input appears BY NAME in the model and in the rendered output. A derived number is acted on by a
# human who cannot see how it was computed, so every quiet lie here would be a defect.


def closed_incident_ids(events, closed_event_type=None):
    """The incident ids the RECORDED stream reports CLOSED, in recorded order and DE-DUPLICATED, so a
    duplicated close event names one incident ONCE and cannot double-count it (the corruption
    WARP-1208's store refuses to create). The event's own incident field is preferred and its
    correlation_id is the fallback; the reconciliation stamps both. Pure over the parsed events: the
    close event TYPE is INJECTED (metrics_readers.support_vocabulary resolves it from the contract that
    owns the vocabulary), and None means no close event type was supplied, so nothing is recognized and
    the derivation stands down honestly rather than reaching for a file behind the caller's back."""
    out = []
    if not _is_str(closed_event_type):
        return out
    for e in events or []:
        if not isinstance(e, dict) or e.get("type") != closed_event_type:
            continue
        iid = e.get("incident") if _is_str(e.get("incident")) else e.get("correlation_id")
        if _is_str(iid) and iid not in out:
            out.append(iid)
    return out


def _receipt_schema_problem(receipt):
    """Why a record is NOT a reconciliation receipt AT ALL, or None when it declares the owner's
    schema (SUPPORT_RECEIPT_SCHEMA). Receipt IDENTITY, asked before and independently of receipt
    RESOLUTION, because "is this a receipt" and "does it back a closed incident" are two different
    questions and each deserves its own answer: a mapping that does not declare the schema
    authenticates nothing, however well it is shaped. Until this check existed a three-key hand-written
    JSON file in the store forged all four measures with zero exclusions reported (the round-1 review's
    ranked note 1), because resolution alone is STRUCTURAL and the store's directory was the only
    authority on what a receipt is."""
    if not isinstance(receipt, dict):
        return "the receipt is not a record (mapping)"
    if receipt.get("schema") != SUPPORT_RECEIPT_SCHEMA:
        return ("the record does not declare schema %r (it declares %r), so it is not a reconciliation "
                "receipt and cannot authenticate a closure"
                % (SUPPORT_RECEIPT_SCHEMA, receipt.get("schema")))
    return None


def _receipt_problem(receipt, closed):
    """Why a receipt does NOT resolve to a closed incident, or None when it does. A receipt that names
    no incident, or that names an incident the recorded stream never reports closed, does not resolve: a
    settlement with no close event is not evidence of a closure (the exact partial-failure gap
    WARP-1208's review named), so it is EXCLUDED and NAMED rather than counted. Receipt IDENTITY is
    _receipt_schema_problem's question and is decided before this one."""
    if not isinstance(receipt, dict):
        return "the receipt is not a record (mapping)"
    iid = receipt.get("incident")
    if not _is_str(iid):
        return "the receipt names no incident, so there is nothing for it to back"
    if iid not in closed:
        return ("the receipt names incident %r, which the recorded stream never reports closed: a "
                "settlement with no close event is not evidence of a closure" % iid)
    return None


def authenticate_incidents(events, receipts=None, closed_event_type=None):
    """THE AUTHENTICATION JOIN, the load-bearing property of this derivation. An incident is counted
    ONLY when its closure is BACKED by a reconciliation receipt that resolves to that incident id.

    Returns {closed_events, closed (the ids, so the recurrence cross-reference and the caller read ONE
    computation), receipts_read, receipts_backing, receipts_excluded, authenticated (ids in recorded
    order), backing (incident id -> the ONE receipt that backs it), excluded (named entries)}.
    A close event with NO backing receipt is excluded from every numerator and every denominator and
    reported BY NAME (UNBACKED_EVENT) with its incident id; a record that is not a receipt at all is
    excluded and named (UNRESOLVED_RECEIPT) with the schema it declares; a receipt whose incident cannot
    be resolved is excluded and named the same way; and TWO OR MORE receipts resolving to ONE incident
    are ALL excluded and ALL named (CONFLICTING_RECEIPTS) rather than one of them silently winning.
    That last rule is the round-1 review's F3: the receipt is content-addressed and CLOCK-FREE, so
    nothing in two receipts orders them, and a first-one-wins pick made the recurrence rate depend on a
    hash in filename order. There is no honest tie-break, so the closure's evidence is AMBIGUOUS and the
    incident is excluded until a human resolves which settlement is the truth. The receipt arithmetic
    therefore CLOSES - receipts_read == receipts_backing + receipts_excluded - and both sides are
    COUNTED independently so a reader can CHECK it rather than take it on the docstring's word. With NO
    receipts nothing authenticates: the derivation stands down to zero rather than falling back to the
    raw events. PURE over the injected events and receipts (the receipt store is a reader, so the
    stand-downs are testable with no filesystem)."""
    receipts = list(receipts or [])
    closed = closed_incident_ids(events, closed_event_type)
    backing, excluded, resolving, conflicted = {}, [], {}, set()
    for position, receipt in enumerate(receipts):
        # RECEIPT IDENTITY first, then receipt RESOLUTION: two separate questions, two separate
        # decisions, so neither can be lost by fixing the other and each is provable on its own.
        problem = _receipt_schema_problem(receipt)
        if problem is None:
            problem = _receipt_problem(receipt, closed)
        if problem is not None:
            excluded.append({"reason": SUPPORT_UNRESOLVED_RECEIPT, "position": position,
                             "receipt": receipt.get("id") if isinstance(receipt, dict) else None,
                             "incident": receipt.get("incident") if isinstance(receipt, dict) else None,
                             "detail": problem})
            continue
        resolving.setdefault(receipt["incident"], []).append((position, receipt))
    for iid, found in resolving.items():
        if len(found) > 1:
            conflicted.add(iid)
            for position, receipt in found:
                excluded.append({"reason": SUPPORT_CONFLICTING_RECEIPTS, "position": position,
                                 "receipt": receipt.get("id"), "incident": iid,
                                 "detail": "%d receipts resolve to incident %r (%s) and NOTHING orders "
                                           "them: the receipt is content-addressed and clock-free, so "
                                           "there is no honest way to choose which settlement is the "
                                           "truth. The closure's evidence is AMBIGUOUS, so this "
                                           "incident is excluded from every numerator and every "
                                           "denominator and every one of its receipts is named, rather "
                                           "than one of them winning on filename order"
                                           % (len(found), iid,
                                              # SORTED, so the named set does not depend on the order
                                              # the caller happened to read the receipts in.
                                              ", ".join(sorted(str(r.get("id"))
                                                               for _p, r in found)))})
            continue
        backing[iid] = found[0][1]
    authenticated = [iid for iid in closed if iid in backing]
    for iid in closed:
        if iid not in backing and iid not in conflicted:
            excluded.append({"reason": SUPPORT_UNBACKED_EVENT, "position": None, "receipt": None,
                             "incident": iid,
                             "detail": "the stream reports this incident closed but NO reconciliation "
                                       "receipt resolves to it, so it is excluded from every numerator "
                                       "and every denominator (recognition is not authentication)"})
    return {"closed_events": len(closed), "closed": closed, "receipts_read": len(receipts),
            "receipts_backing": len(backing),
            # COUNTED, never derived by subtraction: a subtracted figure could not fail to close, and
            # an arithmetic that cannot fail proves nothing. Each excluded RECEIPT carries its position
            # in the injected order; an excluded close EVENT carries none.
            "receipts_excluded": sum(1 for e in excluded if e["position"] is not None),
            "authenticated": authenticated, "backing": backing, "excluded": excluded}


def _timeline_problem(reason, detail):
    """One named timeline problem: the REASON from the closed set, the SOURCE it belongs to in SUPPORT_SOURCES,
    and the detail. A record rather than a bare string precisely so an unsubtractable pair and an UNREADABLE
    timestamp cannot arrive under one name (the round-2 residual)."""
    return {"reason": reason, "source": "incident_timeline", "detail": detail}


def _interval_hours(opened, reached):
    """(the elapsed HOURS between two PARSED timestamps, None) or (None, the named problem) when the
    pair cannot be turned into an honest interval. FAILS CLOSED on a pair no arithmetic can reach: a
    NAIVE and an AWARE timestamp in one timeline raise TypeError on subtraction, and the shipped
    validator does NOT refuse that record - its ordering check is a LEXICOGRAPHIC string compare over
    the raw values, so a mixed-awareness pair validates with ZERO errors - which made a contract-valid
    record take down every number on the metrics CLI and the whole dashboard (the round-1 review's F1).
    An unsubtractable pair is therefore an honest ABSENT interval that is REPORTED BY NAME, never a
    number and never a crash that costs the reader the measures that were fine. A NEGATIVE interval is
    dropped for the same reason it always was, and is now named too: a negative time-to-diagnosis is a
    corrupt measure, not a number to put in a median."""
    try:
        hours = (reached - opened).total_seconds() / 3600
    except (TypeError, OverflowError) as exc:
        return None, _timeline_problem(
            SUPPORT_UNUSABLE_INTERVAL,
            "the timeline's two timestamps CANNOT BE SUBTRACTED (%s), so no interval exists "
            "to measure: one carries an offset and the other does not, which the record "
            "contract accepts because its ordering check compares the raw strings" % exc)
    if hours < 0:
        return None, _timeline_problem(
            SUPPORT_UNUSABLE_INTERVAL,
            "the interval is NEGATIVE (%s h), which is a corrupt measure rather than a "
            "number to put in a median" % round(hours, SUPPORT_ROUNDING["hours"]))
    return round(hours, SUPPORT_ROUNDING["hours"]), None


def _incident_interval(incident, field):
    """(hours, None) or (None, the named problem) for one incident timeline interval, opened_at to `field`
    (diagnosed_at or restored_at). (None, None) ONLY when a timestamp is ABSENT: nothing was recorded,
    which is a gap and not a corruption, so it is not named. A timestamp that IS RECORDED and that no parser can read is a DIFFERENT FACT and is NAMED
    (UNREADABLE_TIMESTAMP). Round 2 found the two conflated here - `yesterday`, `not-a-date` and a
    leap-shaped 12:00:60Z each validate with zero errors and were then dropped with no name, exactly
    indistinguishable from a timestamp nobody recorded - which is the ABSENT-versus-UNREADABLE class the
    contract half already fixed, sitting on the timeline. Neither is inferable from a missing sample."""
    timeline = incident.get("timeline") if isinstance(incident, dict) else None
    if not isinstance(timeline, dict):
        return None, None
    parsed = {}
    for key in ("opened_at", field):
        raw = timeline.get(key)
        parsed[key] = parse_iso(raw)
        if parsed[key] is None and raw is not None:
            return None, _timeline_problem(
                SUPPORT_UNREADABLE_TIMESTAMP,
                "the timeline RECORDS %s as %r and no parser can read it as a timestamp, so this "
                "interval is UNREADABLE rather than absent: something was recorded, and dropping it "
                "under the same silence as a timestamp nobody wrote hides a corrupt record behind a "
                "gap" % (key, raw))
    if parsed["opened_at"] is None or parsed[field] is None:
        return None, None
    return _interval_hours(parsed["opened_at"], parsed[field])


def _incident_hours(incident, field):
    """Elapsed HOURS from the incident timeline's opened_at to `field`, or None when the pair is absent,
    unreadable, unsubtractable or negative. The one-value view of _incident_interval, for a caller that
    does not report the reason; support_trend uses the pair so no unusable interval vanishes."""
    return _incident_interval(incident, field)[0]


def _median(values):
    """The MEDIAN of the recorded values at the declared precision: the middle value, or the MEAN of the
    two middle values for an even count (declared here rather than implied). None when there is none."""
    ordered = sorted(values)
    if not ordered:
        return None
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return round((ordered[middle - 1] + ordered[middle]) / 2, SUPPORT_ROUNDING["hours"])


def _population(count):
    """The population a measure rests on, and THE ONE PLACE the zero-denominator decision is made:
    (the count, the named stand-down or None). A measure with NO population stands down BY NAME
    (EMPTY_DENOMINATOR) and is never rendered as 0 percent, 100 percent, or a dash that reads as a
    value, because a rate with no population is not a rate and a trend with no observation is not a
    trend. Neutralizing this ONE decision is the anti-vacuity tooth: it fabricates a number over
    nothing."""
    return count, (SUPPORT_EMPTY_DENOMINATOR if not count else None)


def support_trend(ids, records, field):
    """One TREND over an incident timeline interval: the per-incident values IN RECORDED ORDER plus the
    MEDIAN and the LATEST, never a single average that hides a regression. Reported with its sample
    count against the authenticated population, so a reader sees the evidence base each number rests
    on; a trend with ONE data point is reported as a SINGLE OBSERVATION and NOT as a trend direction,
    and one with none stands down by name. An incident whose timeline yielded no usable interval is
    reported BY NAME in `unusable` rather than dropped, under the reason the timeline itself decided
    (UNUSABLE_INTERVAL for a pair no arithmetic can reach, UNREADABLE_TIMESTAMP for a value recorded and
    unreadable), so a sample count short of the population is explained. Pure over the injected ids."""
    observations, unusable = [], []
    for iid in ids:
        hours, problem = _incident_interval(records.get(iid), field)
        if hours is not None:
            observations.append({"incident": iid, "hours": hours})
        elif problem is not None:
            unusable.append({"reason": problem["reason"], "incident": iid,
                             "detail": problem["detail"]})
    values = [o["hours"] for o in observations]
    samples, standdown = _population(len(observations))
    reading = None
    if standdown is None:
        reading = "single observation" if samples == 1 else "trend over %d observations" % samples
    return {"field": field, "unit": "hours", "rounding": SUPPORT_ROUNDING["hours"],
            "observations": observations, "samples": samples, "population": len(ids),
            "median": _median(values), "latest": values[-1] if values else None,
            "reading": reading, "standdown": standdown,
            "unusable": unusable, "unusable_count": len(unusable)}


def support_share(numerator_ids, population_ids, of):
    """One SHARE, reported WITH its numerator and its denominator beside it, so a reader can see that
    "100 percent diagnosability" over one incident is ONE INCIDENT. Over an empty population it stands
    down BY NAME (EMPTY_DENOMINATOR) instead of rendering 0 percent, 100 percent, or a dash that reads
    as a value. Rounding is the declared SUPPORT_ROUNDING, applied here and nowhere else."""
    denominator, standdown = _population(len(population_ids))
    numerator = len(numerator_ids)
    return {"of": of, "numerator": numerator, "denominator": denominator,
            "incidents": list(numerator_ids),
            "rate": None if standdown else round(numerator / denominator, SUPPORT_ROUNDING["rate"]),
            "percent": None if standdown else round(100.0 * numerator / denominator,
                                                    SUPPORT_ROUNDING["percent"]),
            "standdown": standdown}


def recurring_incidents(ids, backing, known_ids=None, recorded_ids=None):
    """(the authenticated incidents whose BACKING RECEIPT names a recurrence of an AUTHENTICATED incident,
    the named entries for every recurrence_of id no authenticated incident carries). Read from the RECEIPT,
    never from the event and never from prose - and CROSS-REFERENCED, which round 2 found it was not: one
    arbitrary string bought a 100 percent recurrence rate, and the same hole fires on a GENUINE receipt
    carrying a stale or typo'd id. The recurrence rate is the MISSING-SPECIFICATION signal that drives spec
    work, so a reference resolving to nothing is NAMED (UNRESOLVED_RECURRENCE) rather than counted. An
    incident counts as recurring when at least ONE of its ids resolves.

    known_ids IS THE AUTHENTICATED POPULATION AND NOTHING ELSE, which took three rounds to get right and is
    worth stating exactly. Round 3 resolved against the CLOSE EVENTS union the records union the conflicted
    ids, so it included ids THIS PASS ITSELF EXCLUDED and one forged unbacked incident.closed moved the rate
    from 0 to 100 percent (R3-B4). Round 5 narrowed that to the BACKING keys union the RECORDS READ and
    claimed the population was authenticated - and it was not: a HAND-WRITTEN incident record, which needs
    no receipt and no event and which any writer inside .veldo/ can drop in, still moved the rate from 0 to
    100 percent, so the docstring's claim was false against exactly the writer AC2 exists to defeat.

    The population is therefore the BACKING KEYS ALONE: every closure a reconciliation receipt
    authenticates. recorded_ids is the RECORD-ONLY half, used for the NAMING and never for the numerator,
    so a reference to an incident that IS recorded but that nothing authenticates is named as its own fact
    rather than as a reference to nothing - and the availability that costs is reported instead of taken:
    both halves of the population appear on the surface (recurrence_population and
    recurrence_population_records_only), so a genuine reference to an older incident is visible to a human
    even though it cannot move the number."""
    known = {k for k in (known_ids or ()) if _is_str(k)}
    recorded = {k for k in (recorded_ids or ()) if _is_str(k)} - known
    out, unresolved = [], []
    for iid in ids:
        receipt = backing.get(iid) or {}
        claimed = receipt.get("recurrence_of")
        named = [x for x in claimed if _is_str(x)] if isinstance(claimed, (list, tuple)) else []
        resolved = [x for x in named if x in known]
        phantom = [x for x in named if x not in known]
        if phantom:
            unresolved.append({"reason": SUPPORT_UNRESOLVED_RECURRENCE, "position": None,
                               "receipt": receipt.get("id"), "incident": iid,
                               "detail": "the receipt names recurrence_of %s, which NO AUTHENTICATED "
                                         "incident carries (%s), so the reference does not resolve and is "
                                         "not counted as a recurrence: %s"
                                         % (", ".join(sorted(repr(p) for p in phantom)),
                                            "an incident RECORD does carry %s and NO receipt authenticates "
                                            "it, which is not enough: a hand-written record would "
                                            "otherwise move this signal"
                                            % ", ".join(sorted(repr(p) for p in phantom if p in recorded))
                                            if any(p in recorded for p in phantom) else
                                            "no receipt-backed closure carries it and no record read does "
                                            "either",
                                            "the incident still counts through %s"
                                            % ", ".join(sorted(repr(r) for r in resolved)) if resolved else
                                            "this incident is a FIRST OCCURRENCE for the rate, because a "
                                            "phantom id would buy a missing-specification signal with no "
                                            "incident behind it")})
        if resolved:
            out.append(iid)
    return out, unresolved


def _record_substance(record):
    """One incident record's RECORDED SUBSTANCE as a short intrinsic string: the title and the recorded timeline,
    which is what decides the numbers. Used to NAME the participants of a duplicate-id conflict, where the id
    itself cannot tell them apart. Intrinsic and order-free, so the named set never depends on read order."""
    timeline = record.get("timeline") if isinstance(record, dict) else None
    parts = (["%s=%r" % (k, timeline[k]) for k in sorted(timeline)]
             if isinstance(timeline, dict) else [])
    return "title %r timeline(%s)" % (record.get("title"), ", ".join(parts))


def index_incident_records(incidents=None):
    """THE INCIDENT RECORDS INDEXED BY THEIR OWN ID, with a duplicate id REFUSED rather than resolved by
    the order the records arrived in. Returns {records (id -> the ONE record), conflicted (id -> how
    many claimed it), records_read, records_indexed, records_conflicted, records_unidentified,
    excluded (named entries)}.

    TWO OR MORE records carrying ONE id are ALL excluded and ALL NAMED (CONFLICTING_RECORDS) with every
    participant's recorded substance in a SORTED detail, and the incident is excluded from every
    numerator and every denominator: the receipts rule, applied to the collection one over, which is
    where the round-2 review found it missing. records.setdefault made the winner the first record in
    FILENAME ORDER, so a time-to-diagnosis median and latest of 1.0 or 9.0 hours came out of identical
    substance while records_read reported 1 when 2 were read. The id IS the record's identity, so there
    is no honest tie-break; a human resolves which record is the truth. The record arithmetic CLOSES -
    records_read == records_indexed + records_conflicted + records_unidentified - every figure COUNTED
    independently rather than derived by subtraction. Pure over the injected records."""
    records = list(incidents or [])
    found, unidentified = {}, 0
    for position, record in enumerate(records):
        rid = record.get("id") if isinstance(record, dict) else None
        if _is_str(rid):
            found.setdefault(rid, []).append((position, record))
        else:
            unidentified += 1
    index, conflicted, excluded = {}, {}, []
    for rid in sorted(found):
        group = found[rid]
        if len(group) < 2:
            index[rid] = group[0][1]
            continue
        conflicted[rid] = len(group)
        excluded.append({"reason": SUPPORT_CONFLICTING_RECORDS, "position": None, "receipt": None,
                         "incident": rid,
                         "detail": "%d incident records carry the id %r and NOTHING orders them: the "
                                   "id IS the identity, so the recorded timeline is AMBIGUOUS and this "
                                   "incident is excluded from every numerator and every denominator "
                                   "rather than a median coming out of whichever file sorted first. "
                                   "Every participant, named by its recorded substance: %s"
                                   % (len(group), rid,
                                      # SORTED and INTRINSIC, so the named set does not depend on the
                                      # order the caller happened to read the records in.
                                      "; ".join(sorted(_record_substance(r) for _p, r in group)))})
    return {"records": index, "conflicted": conflicted, "records_read": len(records),
            "records_indexed": len(index), "records_conflicted": sum(conflicted.values()),
            "records_unidentified": unidentified, "excluded": excluded}


def _records_diagnosis_validation(receipt):
    """Whether the receipt RECORDS a human diagnosis validation: a diagnosis_validation block naming
    the validator. The close gate already refuses to settle without one, so this READS what the receipt
    recorded rather than re-deciding it; a receipt that records none does not count."""
    block = receipt.get("diagnosis_validation") if isinstance(receipt, dict) else None
    return isinstance(block, dict) and _is_str(block.get("validated_by"))


def incident_corpus_resolution(incident, spec_areas=None, contract_areas=None):
    """WHERE an incident lands in the RECORDED corpus, mechanically and never inferred from prose:
    {"spec": the governing spec id when the corpus carries it, "areas": the DECLARED contract areas it
    resolves to}. The area comes from the record's affected_area when it declares one, ELSE from its
    affected_spec resolved to that spec's PLACEMENT (the PLAN-0011 join key). AN AREA IS NEVER
    INVENTED: a name the contract does not declare resolves to no area, and a record that declares an
    area is never silently reassigned to a different one."""
    if not isinstance(incident, dict):
        return {"spec": None, "areas": []}
    index = spec_areas if isinstance(spec_areas, dict) else {}
    declared = {a for a in (contract_areas or ()) if _is_str(a)}
    spec_id = incident.get("affected_spec")
    spec = spec_id if _is_str(spec_id) and spec_id in index else None
    areas, area = set(), incident.get("affected_area")
    if _is_str(area):
        if area in declared:
            areas.add(area)
    elif spec is not None:
        areas |= {a for a in (index.get(spec) or ()) if a in declared}
    return {"spec": spec, "areas": sorted(areas)}


def diagnosable_incidents(ids, backing, records, spec_areas=None, contract_areas=None):
    """The authenticated incidents RESOLVED FROM ARTIFACTS ALONE under the DECLARED MECHANICAL
    definition: the receipt RECORDS a diagnosis validation AND the incident RESOLVES to a governing
    spec the corpus carries or to a declared contract area. A declared PROXY, not a measurement of
    understanding (SUPPORT_REVIEW_LANE), and never inferred from prose."""
    out = []
    for iid in ids:
        if not _records_diagnosis_validation(backing.get(iid)):
            continue
        resolution = incident_corpus_resolution(records.get(iid), spec_areas, contract_areas)
        if resolution["spec"] or resolution["areas"]:
            out.append(iid)
    return out


def contract_dependence(ids, backing, records, spec_areas=None, contract_areas=None,
                        contract_problem=None, corpus_problem=None):
    """WHERE THE DIAGNOSABILITY SCORE DEPENDS ON THE ARTIFACTS IT RESOLVES AGAINST, REPORTED rather than
    claimed away. The declared mechanical definition has TWO halves - the receipt records a diagnosis
    validation, AND the incident resolves to a governing spec THE CORPUS CARRIES or to a DECLARED
    contract area - so the score depends on BOTH the architecture contract (the area half) and the spec
    corpus (the spec half), and the round-1 review was right to refute the claim that it is
    contract-independent: an incident resolvable ONLY through its declared area counts with a contract
    and does not count without one.

    BOTH HALVES ARE REPORTED, which round 2 required: with an unreadable corpus this block used to tell
    the reader the area half was available and say nothing about the corpus, while the score had already
    collapsed to 0.0 percent because one malformed spec file emptied the index. The definition is kept
    (it is the criterion's own words, and an area the contract does not declare is never invented) and
    the CLAIM is made true instead: this names the STATE of each half, names every authenticated incident
    whose contribution turns on one of them and which one, and says which way it moves."""
    state = (SUPPORT_UNREADABLE_ARCHITECTURE_CONTRACT if contract_problem is not None
             else SUPPORT_NO_ARCHITECTURE_CONTRACT if contract_areas is None else None)
    corpus_state = SUPPORT_UNREADABLE_SPEC_CORPUS if corpus_problem is not None else None
    if corpus_state is None and not spec_areas:
        corpus_state = SUPPORT_NO_SPEC_CORPUS
    turning_on_it = []
    for iid in ids:
        if not _records_diagnosis_validation((backing or {}).get(iid)):
            continue
        record = records.get(iid) if isinstance(records, dict) else None
        resolution = incident_corpus_resolution(record, spec_areas, contract_areas)
        if resolution["spec"] or resolution["areas"]:
            continue
        area = record.get("affected_area") if isinstance(record, dict) else None
        spec = record.get("affected_spec") if isinstance(record, dict) else None
        if _is_str(area):
            turning_on_it.append({"incident": iid, "affected_area": area, "affected_spec": None,
                                  "turns_on": "architecture_contract"})
        elif _is_str(spec):
            turning_on_it.append({"incident": iid, "affected_area": None, "affected_spec": spec,
                                  "turns_on": "spec_corpus"})
    unavailable = ["the AREA half is UNAVAILABLE (%s)" % state] if state is not None else []
    if corpus_state is not None:
        unavailable.append("the SPEC half is UNAVAILABLE (%s)" % corpus_state)
    if unavailable:
        detail = ("%s, so an incident resolvable only through that half cannot count: this score is "
                  "NOT the number the same artifacts would produce against a readable contract and a "
                  "readable corpus" % " and ".join(unavailable))
    else:
        detail = ("both halves of the definition are available (a readable contract declares the areas "
                  "and the corpus carries the specs), so an incident resolving to either counts; an "
                  "area the contract does NOT declare still resolves to nothing, because an area is "
                  "never invented")
    return {"measure": "diagnosability_score", "state": state, "corpus_state": corpus_state,
            "area_half_available": state is None, "spec_half_available": corpus_state is None,
            "detail": detail,
            "not_counted": turning_on_it, "not_counted_count": len(turning_on_it)}


def _area_cost_cell(area, area_cost, area_cost_problem=None):
    """One area's cost-to-change cell: (the RECORDED figures, None) when PLAN-0011 data exists for that
    area, else (None, the named stand-down). A cost figure is never carried for an area that has none
    and never invented; neutralizing this ONE decision is the anti-vacuity tooth, and it fabricates a
    cost the data does not contain. THE STAND-DOWN NAMES WHICH FACT IT IS: a series nobody could read is
    UNREADABLE_AREA_COST_DATA, an absent one is NO_AREA_COST_DATA, and this is the ONE place that
    decision is made, so the map-level stand-down and every cell agree by construction."""
    cell = (area_cost or {}).get(area) if isinstance(area_cost, dict) else None
    if isinstance(cell, dict):
        return dict(cell), None
    if area_cost_problem is not None:
        return None, SUPPORT_UNREADABLE_AREA_COST_DATA
    return None, SUPPORT_NO_AREA_COST_DATA


def incidents_per_area(ids, records, spec_areas=None, contract_areas=None, area_cost=None,
                       contract_problem=None, corpus_problem=None, area_cost_problem=None):
    """THE SOFT JOIN (C7) that never fakes itself: incidents attributed to DECLARED contract areas on
    ONE map with PLAN-0011's cost-to-change-per-area data. With a contract FILE that yields no declared
    area (truncated, malformed, or declaring none) the join stands down BY NAME as its OWN condition
    (UNREADABLE_ARCHITECTURE_CONTRACT), never as an empty denominator, because "nobody could read the
    shape" and "no incident attributed to a declared area" are different facts and the round-1 review
    caught the second being reported for the first. THE SAME RULE NOW HOLDS FOR THE CORPUS, which is
    where round 2 caught it still standing: attribution also runs through the spec index, so when the
    corpus could not be READ this map stands down as UNREADABLE_SPEC_CORPUS rather than reporting an
    empty denominator, and when rows survive anyway the incomplete attribution is named beside them. A
    stand-down must never report a population when the truth is that a source could not be read. With NO
    architecture contract at all the whole join stands down BY NAME (NO_ARCHITECTURE_CONTRACT) and the
    incident measures still render on their own; with a contract but no cost data the incident column
    renders and each cost cell stands down by name (NO_AREA_COST_DATA, or UNREADABLE_AREA_COST_DATA when
    the series could not be read); with no attributable incident the map stands down (EMPTY_DENOMINATOR)
    rather than inventing a row. An unattributable incident is listed BY ID, never given a default."""
    if contract_problem is not None:
        return {"standdown": SUPPORT_UNREADABLE_ARCHITECTURE_CONTRACT, "areas": [], "attributed": 0,
                "unattributed": list(ids), "population": len(ids), "cost_standdown": None,
                "detail": contract_problem}
    if contract_areas is None:
        return {"standdown": SUPPORT_NO_ARCHITECTURE_CONTRACT, "areas": [], "attributed": 0,
                "unattributed": list(ids), "population": len(ids), "cost_standdown": None,
                "detail": "no architecture contract declares the shape, so there is no declared area "
                          "to attribute an incident to and no cost map to join it with (adoption "
                          "safe: the incident measures still render on their own)"}
    per_area, unattributed = {}, []
    for iid in ids:
        areas = incident_corpus_resolution(records.get(iid), spec_areas, contract_areas)["areas"]
        if not areas:
            unattributed.append(iid)
        for area in areas:
            per_area.setdefault(area, []).append(iid)
    rows = []
    for area in sorted(per_area):
        cost, cost_standdown = _area_cost_cell(area, area_cost, area_cost_problem)
        rows.append({"area": area, "incidents": len(per_area[area]),
                     "incident_ids": list(per_area[area]), "cost": cost,
                     "cost_standdown": cost_standdown})
    standdown = _population(len(rows))[1]
    if standdown is not None and corpus_problem is not None:
        # A HALF THAT COULD NOT BE READ IS NEVER AN EMPTY POPULATION. Attribution runs through the spec
        # index, so an unreadable corpus produces no row for a reason that has nothing to do with the
        # incidents; reporting EMPTY_DENOMINATOR here says they were unattributable, which is false.
        standdown = SUPPORT_UNREADABLE_SPEC_CORPUS
    return {"standdown": standdown, "areas": rows,
            "attributed": len(ids) - len(unattributed), "unattributed": unattributed,
            "population": len(ids), "detail": corpus_problem,
            "cost_standdown": None if (isinstance(area_cost, dict) and area_cost)
                              else _area_cost_cell(None, None, area_cost_problem)[1]}


def support_numbers(events, receipts=None, incidents=None, spec_areas=None, contract_areas=None,
                    area_cost=None, closed_event_type=None, contract_problem=None,
                    corpus_problem=None, input_problems=None, source_reads=None):
    """THE FOUR SUPPORT MEASURES outcome O6 names (WARP-1210, W10 of PLAN-0012), derived from RECORDED
    artifacts only and AUTHENTICATED against the reconciliation receipts: time-to-diagnosis and
    time-to-restore as TRENDS, the recurrence rate, the diagnosability score, and the
    incidents-per-area soft join with PLAN-0011's cost-to-change data.

    EVERY READER IS INJECTED - the events, the receipts (the authority), the incident records (their
    recorded timelines), the corpus spec index, the contract's declared areas, the per-area cost data,
    and the NAMED PROBLEM for every source that could not be READ - plus the close event TYPE itself -
    so this is a PURE function: no clock, no network, no filesystem, not even a lazy one, and the same
    inputs give the same numbers across processes. metrics_readers.load_support_inputs() gathers every
    one of them at the ONE impure edge. It writes nothing, starts no process, thread or timer, reads no
    live system, and does not call compute(), so no number the core derivation reports changes.

    source_reads IS THE GOVERNING RULE'S INPUT (AC3): one READ RECORD per declared source, each carrying
    a POSITIVE ASSERTION that the read was COMPLETE. The model is marked NOT RENDERABLE unless EVERY
    declared source proves it, and the incomplete sources are NAMED - so a permission-denied directory,
    a symlink loop, a suffix or placement no reader enumerates, or a source nobody wired at all takes
    the WHOLE SECTION down instead of turning 100 percent into 0 percent in silence. The numbers are
    still DERIVED here (a stand-down a reader cannot diagnose is its own defect), and NONE OF THE THREE
    SURFACES renders one while `renderable` is False: the CLI's TEXT and the dashboard's CARDS obey the
    mark through metrics_support_report.support_renderable, and the CLI's --json obeys it through
    metrics_support_report.support_json, which withholds every measure and keeps the completeness verdict.
    Round 5 shipped this sentence with only two of the three obeying it, which is what R5-B1 blocked: the
    machine-readable surface printed diagnosability_score 0.0 percent beside renderable false.

    contract_problem and corpus_problem are named arguments rather than entries in input_problems
    because they DECIDE as well as report (each stands the area map down as its own condition); every
    other source's problem arrives in input_problems, is named through SUPPORT_SOURCES, and is read by a
    behavioral consumer through the ONE selector source_problem_detail, so a third deciding source needs
    no new argument. Returns the MODEL every surface presents through .veldo/metrics_support_report.py."""
    auth = authenticate_incidents(events, receipts, closed_event_type)
    index = index_incident_records(incidents)
    records, backing = index["records"], auth["backing"]
    # A RECORD CONFLICT EXCLUDES THE INCIDENT, exactly as a receipt conflict does: its recorded timeline
    # is ambiguous, so it leaves every numerator and every denominator and is named ONCE (it is backed,
    # so it is never also reported UNBACKED_EVENT - one condition, one name).
    ids = [iid for iid in auth["authenticated"] if iid not in index["conflicted"]]
    excluded = list(auth["excluded"]) + index["excluded"]
    # THE RECURRENCE POPULATION IS AUTHENTICATED (R3-B4, and round 5's note 1 one level in): the
    # receipt-BACKED closures ALONE. Never the close events (an unbacked forgery would resolve) and never
    # the records read (a HAND-WRITTEN record would resolve, which moved the rate from 0 to 100 percent
    # while this pass claimed the population was authenticated). The RECORD-ONLY half is passed for the
    # NAMING and reported beside the rate, so what the narrowing costs is visible rather than silent.
    known = set(backing)
    records_only = sorted(set(records) - known)
    recurring, recurrence_unresolved = recurring_incidents(ids, backing, known, records_only)
    cost_problem = source_problem_detail(input_problems, "area_cost_series")
    problems = support_source_problems(input_problems, contract_problem, corpus_problem)
    completeness = support_completeness(source_reads)
    # WHAT WAS ACCOUNTED FOR AND NOT READ, carried out of the read records so a SURFACE can show it: the
    # declared skip rule counts and names every non-record it dismissed, and until round 7 that fact lived
    # only in a read's basis text, which no surface renders - so "a human can see what was not read" was
    # false on all three. It is a directory-entry accounting fact, never a measure, so it survives a
    # stand-down (SUPPORT_JSON_VERDICT keeps it) exactly as the named sources do.
    skipped = [{"source": r.get("source"), "subject": r.get("subject"), "entry": e}
               for r in source_reads or () if isinstance(r, dict) for e in r.get("skipped") or ()]
    return {
        # THE ONE RENDER DECISION: every declared source proved a COMPLETE read AND no source reported a
        # problem. The second half is not redundant - a reader that names a problem cannot affirm, so the
        # real path can never separate them, and asserting both means a forged affirmation beside a named
        # problem still renders nothing.
        "renderable": bool(completeness["complete"]) and not problems,
        "incomplete_sources": completeness["incomplete"],
        "incomplete_source_count": len(completeness["incomplete"]),
        "sources_affirmed": completeness["affirmed"], "sources_declared": completeness["declared"],
        "read_skipped": skipped,
        "closed_events": auth["closed_events"], "receipts_read": auth["receipts_read"],
        "receipts_backing": auth["receipts_backing"], "receipts_excluded": auth["receipts_excluded"],
        "records_read": index["records_read"], "records_indexed": index["records_indexed"],
        "records_conflicted": index["records_conflicted"],
        "records_unidentified": index["records_unidentified"],
        "authenticated": ids, "authenticated_count": len(ids),
        "excluded": excluded, "excluded_count": len(excluded),
        "source_problems": problems,
        "recurrence_unresolved": recurrence_unresolved,
        "recurrence_unresolved_count": len(recurrence_unresolved),
        "closed_event_type": closed_event_type,
        "time_to_diagnosis": support_trend(ids, records, "diagnosed_at"),
        "time_to_restore": support_trend(ids, records, "restored_at"),
        # THE POPULATION THE CROSS-REFERENCE RESOLVES AGAINST, reported beside the rate rather than left
        # implicit: it is the fact R3-B4 got wrong, so a reader has to be able to see it. BOTH HALVES are
        # reported, because the second one is deliberately NOT part of it: an incident this pass READ a
        # record for but that no receipt authenticates cannot resolve a reference, and a reader who sees a
        # named UNRESOLVED_RECURRENCE has to be able to tell that case from a reference to nothing at all.
        "recurrence_population": sorted(known), "recurrence_population_count": len(known),
        "recurrence_population_records_only": records_only,
        "recurrence_population_records_only_count": len(records_only),
        "recurrence_rate": support_share(
            recurring, ids,
            "authenticated closed incident(s) whose receipt carries a recurrence_of that resolves to one "
            "of the %d incident(s) a RECEIPT AUTHENTICATES (a MISSING SPECIFICATION; resolved against that "
            "population alone, never against the close events and never against the %d incident(s) this "
            "pass read a RECORD for but nothing authenticates, either of which any writer can append)"
            % (len(known), len(records_only))),
        "diagnosability_score": support_share(
            diagnosable_incidents(ids, backing, records, spec_areas, contract_areas), ids,
            "authenticated closed incident(s) resolved from artifacts alone (the receipt records a "
            "diagnosis validation and the incident resolves to a governing spec or a declared area)"),
        "contract_dependence": contract_dependence(ids, backing, records, spec_areas, contract_areas,
                                                   contract_problem, corpus_problem),
        "incidents_per_area": incidents_per_area(ids, records, spec_areas, contract_areas, area_cost,
                                                 contract_problem, corpus_problem, cost_problem),
        "review_lane": SUPPORT_REVIEW_LANE,
    }
