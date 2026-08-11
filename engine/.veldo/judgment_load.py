#!/usr/bin/env python3
"""Human-judgment load: the second axis of effort (WARP-1407, W7 of PLAN-0014).

WHAT THIS IS. Effort is a PAIR, not a scalar. One axis is what the machine spent (tokens, the
Tokens of Effort corpus in `toe_corpus.py`); the other is what a human had to spend deciding,
derived from the human minutes the loop already carries on its own events. This module derives the
second axis and renders the pair, per spec and per plan, through ONE renderer, so no two surfaces
can spell the pair two ways.

WHY A SECOND AXIS AT ALL, because this is the whole point of the item. A single-axis unit cannot
distinguish a change that took the machine 400k tokens and nobody's attention from a four-line
change that took three review rounds and an owner approval. The second one is the expensive one, and
every legacy unit scored it as trivial. The pair makes that class - cheap to build, expensive to
approve - visible, and nothing else in this method ever showed it.

***

BOTH AXES ARE EMPTY IN THIS REPOSITORY TODAY, AND THAT IS A MEASURED FACT REPORTED AS A NUMBER.

Measured 2026-08-10 over this repository's own log: 1078 events (a count that rises by one on every
gate run), and NOT ONE of them carries `human_minutes` or `tokens`; 174 shipped specs, 0 percent
coverage on both axes. WARP-1401 measured the same gap for spend and named the architectural reason:
a token count is not knowable from inside a repository. WARP-0733 then built the recorder
(`spend.py`), so the call now EXISTS; what has not happened is anybody calling it. The judgment axis
therefore has the recording machinery and none of the data.

That shapes every line below. `minutes_recorded` is False on every record here, and this module
NEVER lets that read as "zero minutes of judgment". `classify()` refuses to shape a record whose
minutes were never recorded, `coverage()` reports the gap as a number, and the report prints "not
recorded" in the place where a figure would go. A confident zero on this axis would be worse than no
axis at all: it would score every approval-heavy change as free, which is precisely the error the
pair exists to end.

WHAT IS RECORDED, AND IT IS NOT MINUTES. The OCCASIONS a human had to judge - review requests,
recorded verdicts, recorded approvals - are in the log at high coverage today. They are counted here
as `episodes` and reported beside the pair, and they are NEVER scaled into a minute figure. A
minutes-per-review coefficient would be an invention, and an invented second axis is the thing this
plan's no-false-precision posture (NG6) refuses. Episodes say how often; only minutes say how long.

THE ONLY RECORDER PRODUCES A MIXED SIGNAL, AND THIS MODULE NAMES IT. `spend.py` records minutes on a
`spec.shipped` event: one bulk number for a whole change. A bulk number cannot say whether the time
went into reviewing or into approving, so those minutes land in the `ship_bulk` kind and
`split_known` stays False. A reader is never handed an approval figure that was inferred from a
total.

WRITES NOTHING, EVER. There is no emitter, no store and no append here: this module reads the corpus,
the event log and the plan registry, and returns rows. A repository that records no minutes and no
tokens is byte-identically unaffected by its existence - it produces the same rows with both axes
marked unrecorded, and nothing fails.

ONE PARSER, ONE REPORTER. Nothing here parses front matter: plan membership comes from the plan
registry in `validate.py` (which reads through `validate.parse_yamlish`, the one parser) and spec
features come from `toe_corpus.spec_features` (the one feature reader). Problems are reported
through `validate.fail`, the one failure reporter, when a caller wants them listed, and raised as
`JudgmentLoadError` when a caller wants the derivation stopped. Both spellings of a problem come
from ONE judge (`_figure_problem`), so a value the reporter names and a value the derivation refuses
are the same set.
"""
import argparse
import importlib.util
import json
import statistics
import sys
from pathlib import Path

SCHEMA = "veldo.judgment_pair/v1"
ROOT = Path(__file__).resolve().parent.parent

# The two envelope figures the pair is built from. Named once so the reader below, the coverage
# report and the refusal messages cannot disagree about which fields are the axes.
TOKENS_FIELD = "tokens"
MINUTES_FIELD = "human_minutes"

# THE ONE MAP from an event type to the kind of judgment its minutes paid for. It is used twice -
# to split the minutes and to count the episodes - so there is one spelling of what counts as a
# review and what counts as an approval. An event type absent from this map that nonetheless
# carries minutes lands in "other": counted in the total, never silently dropped, and never
# promoted into a kind it did not declare.
KIND_BY_EVENT = {
    "review.requested": "review",
    "verdict.recorded": "review",
    "approval.recorded": "approval",
    "plan.approved": "approval",
    # The ONE type the recorder writes today (spend.py records at ship). A bulk figure for a whole
    # change, which is why it is its own kind rather than being folded into review or approval.
    "spec.shipped": "ship_bulk",
}
KINDS = ("review", "approval", "ship_bulk", "other")
# The kinds that actually say WHICH judgment the minutes bought. Minutes outside this set are real
# judgment time with an unknown split, so `split_known` is False and no approval figure is shown.
SPLIT_KINDS = ("review", "approval")

# The smallest both-axes population a median may be taken over. Below this a "median" is one or two
# data points wearing a statistic's clothes, and a shape label drawn from it would be noise
# presented as a finding. The reference block reports the population either way, so a reader can see
# what a label rests on rather than trusting the label.
MIN_POPULATION = 4

# The shape labels. The first is the class the single-axis unit never showed, which is the reason
# this item exists; the last is the honest answer whenever an axis is missing or the population is
# too small.
SHAPE_CHEAP_BUILD_EXPENSIVE_APPROVE = "cheap_to_build_expensive_to_approve"
SHAPE_EXPENSIVE_BUILD_CHEAP_APPROVE = "expensive_to_build_cheap_to_approve"
SHAPE_EXPENSIVE_BOTH = "expensive_on_both"
SHAPE_CHEAP_BOTH = "cheap_on_both"
SHAPE_UNKNOWN = "unknown"

NO_PLAN = "(no plan)"


class JudgmentLoadError(ValueError):
    """A figure this module reads is malformed. Raised BY NAME so a bad value never silently no-ops
    (parallels RequestRecordError, ArchContractError and DecisionRecordError)."""


def _load(rel, name):
    """Load a sibling module BY PATH, the way spend.py loads events.py and the way validate.py loads
    its sibling validators. Keeps this module free of a package import and free of any second
    implementation of what it borrows."""
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mine(event, spec_id):
    """Whether one event belongs to one spec. ONE selector in this module, deliberately: the corpus
    (`toe_corpus.cycles_for` / `spend_for`) has its own and does not export it, so rather than reach
    into it or copy it silently, the selftest asserts THIS reader's totals equal the corpus reader's
    over the same seeded events. Two enumerations of one set are proven equal, not assumed."""
    return (event.get("spec_id") == spec_id
            or event.get("correlation_id") == spec_id)


def _who(event):
    """The spec an event names, for a message. Never used to attribute a figure - `_mine` does
    that - only to make a refusal say which change it was talking about."""
    return event.get("spec_id") or event.get("correlation_id") or "(no spec)"


def _figure_problem(field, event, value):
    """THE ONE JUDGE of an envelope figure: the problem with it as a sentence, or None.

    Both spellings of a problem come from here - `_figure` raises it and `check_log` reports it
    through validate.fail - so the set of values the reporter names and the set the derivation
    refuses cannot drift apart.

    DELIBERATELY STRICTER THAN THE CORPUS, and the difference is the point. `spend_for` in
    toe_corpus.py wants a TOTAL and skips anything non-numeric, which is right for a sum. This
    module owns the HONESTY FLAG on the axis, and a skipped value is minutes that vanish from the
    axis while `minutes_recorded` still flips true: the reader would then see a figure smaller than
    the truth, presented as measured."""
    if not isinstance(event, dict):
        return ("event %r is not a mapping: the caller owns reading the log and hands this module "
                "parsed events" % (event,))
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return ("%s on a %r event for %s must be a number, got %r: a figure this module cannot read "
                "is refused rather than skipped, because a skipped figure leaves the axis marked "
                "recorded and smaller than it is"
                % (field, event.get("type"), _who(event), value))
    if value < 0:
        return ("%s on a %r event for %s cannot be negative, got %r"
                % (field, event.get("type"), _who(event), value))
    return None


def _figure(field, event, value):
    """One envelope figure, refused BY NAME if `_figure_problem` names a problem with it."""
    problem = _figure_problem(field, event, value)
    if problem:
        raise JudgmentLoadError(problem)
    return value


def _events_are_mappings(events):
    """Refuse a non-mapping member up front, so every reader below can assume dicts and no reader
    has to carry its own shape guard."""
    for e in events:
        if not isinstance(e, dict):
            raise JudgmentLoadError(_figure_problem(MINUTES_FIELD, e, None))


def _kind_of(event):
    """The judgment kind of one event, from the ONE map. An unmapped type carrying minutes is
    "other": real time with an unknown purpose."""
    return KIND_BY_EVENT.get(event.get("type"), "other")


def minutes_for(events, spec_id):
    """The judgment load of one spec: the human minutes the log carries for it, split by the kind of
    judgment they paid for.

    `minutes_recorded` is the load-bearing field. A total of zero because no human spent a minute and
    a total of zero because nobody ever recorded one are different facts, and a reader that cannot
    tell them apart will price approval-heavy work at nothing.

    `split_known` is the second honesty flag: true only when at least one minute landed on an event
    that says WHICH judgment it was. The only recorder in this method writes a bulk figure at ship,
    so on real data the total can be known while the split is not."""
    _events_are_mappings(events)
    by_kind = {k: 0 for k in KINDS}
    carrying = 0
    for e in events:
        if not _mine(e, spec_id):
            continue
        v = e.get(MINUTES_FIELD)
        if v is None:
            continue
        by_kind[_kind_of(e)] += _figure(MINUTES_FIELD, e, v)
        carrying += 1
    # ONE enumeration: the total IS the sum of the kinds, never a second pass over the events.
    total = sum(by_kind.values())
    return {
        "minutes": total,
        "by_kind": by_kind,
        "events_with_minutes": carrying,
        "minutes_recorded": carrying > 0,
        "split_known": any(by_kind[k] for k in SPLIT_KINDS),
    }


def tokens_for(events, spec_id):
    """The machine axis of one spec: the tokens the log carries for it, with the same honest flag.

    The tokens are on the corpus record too, but the corpus's `spend_recorded` is true when ANY of
    tokens, cost or minutes is present, so it cannot answer "were TOKENS recorded" - which is exactly
    what a pair needs to say whether its first axis is measured. Hence a per-field reader here,
    proven equal to the corpus's total by the selftest."""
    _events_are_mappings(events)
    total, carrying = 0, 0
    for e in events:
        if not _mine(e, spec_id):
            continue
        v = e.get(TOKENS_FIELD)
        if v is None:
            continue
        total += _figure(TOKENS_FIELD, e, v)
        carrying += 1
    return {"tokens": total, "events_with_tokens": carrying, "tokens_recorded": carrying > 0}


def episodes_for(events, spec_id):
    """How many times a human had to JUDGE this change: review requests, recorded verdicts, recorded
    approvals. Counted through the same ONE kind map, whether or not any minutes were recorded
    against them.

    THIS IS NOT MINUTES AND IS NEVER CONVERTED INTO MINUTES. It is the one part of the judgment axis
    already recorded at high coverage in this repository, so it is reported beside the pair to say
    how OFTEN a human was in the loop. Multiplying it by an assumed minutes-per-review would
    manufacture the very number this module refuses to guess."""
    _events_are_mappings(events)
    by_kind = {k: 0 for k in SPLIT_KINDS}
    for e in events:
        if not _mine(e, spec_id):
            continue
        kind = _kind_of(e)
        if kind in by_kind:
            by_kind[kind] += 1
    return {"total": sum(by_kind.values()), "by_kind": by_kind}


def unattributed(events):
    """Minutes and tokens on events that name NEITHER a spec nor a correlation, so no pair can ever
    carry them.

    Reported as a number rather than refused, and the asymmetry with `_figure` is deliberate. A
    malformed VALUE is a defect in whatever wrote it, and a writer can be fixed, so it is refused. An
    event that is well formed but unattributable is already in an APPEND-ONLY log and cannot be
    withdrawn, so refusing it would make the derivation permanently unrunnable over history - a
    condition unsatisfiable by construction, which is the trap WARP-0733 named. Counted and shown
    instead, so the effort it represents is visibly missing rather than invisibly missing."""
    _events_are_mappings(events)
    n, mins, toks = 0, 0, 0
    for e in events:
        if e.get("spec_id") or e.get("correlation_id"):
            continue
        m, t = e.get(MINUTES_FIELD), e.get(TOKENS_FIELD)
        if m is None and t is None:
            continue
        n += 1
        if m is not None:
            mins += _figure(MINUTES_FIELD, e, m)
        if t is not None:
            toks += _figure(TOKENS_FIELD, e, t)
    return {"events": n, "minutes": mins, "tokens": toks}


def check_log(events, name, fail):
    """EVERY problem with the figures in a log, reported through the caller's failure reporter
    (validate.fail) rather than raised, returning the count. The gate-shaped spelling, mirroring
    `request.validate_record(data, root, record_path, fail)`.

    Two callers, two needs: a derivation must STOP on a figure it cannot read (a pair built from a
    partially-read axis is a wrong number wearing a measured one's clothes), while somebody fixing a
    log wants the whole list at once. Both consult `_figure_problem`, so they cannot disagree about
    what is malformed."""
    errs = 0
    for i, e in enumerate(events):
        if not isinstance(e, dict):
            errs += fail(name, "event %d: %s" % (i, _figure_problem(MINUTES_FIELD, e, None)))
            continue
        for field in (MINUTES_FIELD, TOKENS_FIELD):
            v = e.get(field)
            if v is None:
                continue
            problem = _figure_problem(field, e, v)
            if problem:
                errs += fail(name, "event %d: %s" % (i, problem))
    return errs


def pair(record, events):
    """The PAIR for one corpus record: both axes, each with its own honesty flag, plus the episode
    count and the approval surface the spec declared. Deterministic and read-only."""
    spec = record.get("spec")
    features = record.get("features") or {}
    tk = tokens_for(events, spec)
    mn = minutes_for(events, spec)
    ep = episodes_for(events, spec)
    return {
        "schema": SCHEMA,
        "spec": spec,
        "plan": features.get("plan") or NO_PLAN,
        "risk": features.get("risk"),
        # The approval SURFACE, read off the spec's own front matter by the corpus (the one feature
        # reader). It is the mechanical reason a change costs a human anything at all, so it travels
        # with the pair rather than being looked up separately by each surface.
        "approval_required": features.get("human_approval") == "required",
        "protected_touch": bool(features.get("protected_touch")),
        "tokens": tk["tokens"],
        "tokens_known": tk["tokens_recorded"],
        "judgment_minutes": mn["minutes"],
        "judgment_known": mn["minutes_recorded"],
        "judgment_by_kind": mn["by_kind"],
        "split_known": mn["split_known"],
        "episodes": ep["total"],
        "episodes_by_kind": ep["by_kind"],
        # Set by classify(). Present from the start so a surface reading it never raises, and UNKNOWN
        # from the start so an unclassified row can never read as a cheap one.
        "shape": SHAPE_UNKNOWN,
        "shape_reason": "unclassified: classify() has not run over a reference population",
    }


def reference(rows, min_population=MIN_POPULATION):
    """The comparison the shape labels are drawn from: medians over the rows where BOTH axes are
    recorded. Reported alongside every label, because "expensive" here means "above this
    repository's own median", never an absolute figure."""
    both = [r for r in rows if r["tokens_known"] and r["judgment_known"]]
    out = {
        "population": len(both),
        "min_population": min_population,
        "median_tokens": None,
        "median_judgment_minutes": None,
        "usable": False,
        "reason": "",
    }
    if len(both) < min_population:
        out["reason"] = ("%d record(s) carry both axes; a median needs at least %d, or the label is "
                         "one data point wearing a statistic's clothes"
                         % (len(both), min_population))
        return out
    out["median_tokens"] = statistics.median(r["tokens"] for r in both)
    out["median_judgment_minutes"] = statistics.median(r["judgment_minutes"] for r in both)
    out["usable"] = True
    out["reason"] = "medians over the %d record(s) carrying both axes" % len(both)
    return out


def classify(rows, min_population=MIN_POPULATION):
    """Label each row against the reference, returning (new rows, reference). Pure: the input rows
    are not mutated.

    A ROW WITH A MISSING AXIS IS NEVER LABELLED. It comes back unknown with the reason naming which
    axis is missing, because the alternative - treating an unrecorded axis as a low one - would score
    every approval-heavy change as cheap, which is the single most expensive mistake this module
    could make.

    STRICTLY ABOVE the median is high; at or below it is low. So a record sitting exactly at the
    median is never called expensive, and with a two-record population neither of them is."""
    ref = reference(rows, min_population)
    out = []
    for r in rows:
        row = dict(r)
        missing = [n for n, known in (("tokens", r["tokens_known"]),
                                      ("judgment minutes", r["judgment_known"])) if not known]
        if missing:
            row["shape"] = SHAPE_UNKNOWN
            row["shape_reason"] = ("not recorded: %s (an unrecorded axis is never read as a low one)"
                                   % " and ".join(missing))
        elif not ref["usable"]:
            row["shape"] = SHAPE_UNKNOWN
            row["shape_reason"] = "no reference population: %s" % ref["reason"]
        else:
            hi_tokens = r["tokens"] > ref["median_tokens"]
            hi_minutes = r["judgment_minutes"] > ref["median_judgment_minutes"]
            row["shape"] = (SHAPE_EXPENSIVE_BOTH if hi_tokens and hi_minutes
                            else SHAPE_CHEAP_BUILD_EXPENSIVE_APPROVE if hi_minutes
                            else SHAPE_EXPENSIVE_BUILD_CHEAP_APPROVE if hi_tokens
                            else SHAPE_CHEAP_BOTH)
            row["shape_reason"] = ref["reason"]
        out.append(row)
    return out, ref


def coverage(rows, gap=None, ref=None):
    """HOW MUCH OF THE PAIR IS ACTUALLY MEASURED, as numbers rather than as an impression.

    `usable_as_second_axis` is the blunt one: false means no human minutes exist anywhere, so the
    judgment axis is a shape with no data in it and every consumer of it must say so. `gap` is the
    optional `unattributed()` block, carried through so one report shows both kinds of missing:
    never recorded, and recorded but unattributable.

    `classifiable` is read off the SAME reference the labels come from, computed here when the caller
    does not pass the one it already has. A second comparison against the population floor in this
    function would be a second spelling of the threshold, free to drift from classify's."""
    n = len(rows)
    mk = sum(1 for r in rows if r["judgment_known"])
    tk = sum(1 for r in rows if r["tokens_known"])
    both = sum(1 for r in rows if r["judgment_known"] and r["tokens_known"])
    split = sum(1 for r in rows if r["split_known"])
    eps = sum(1 for r in rows if r["episodes"] > 0)
    ref = ref if ref is not None else reference(rows)
    return {
        "records": n,
        "minutes_known": mk,
        "minutes_coverage": round(mk / n, 4) if n else 0.0,
        "tokens_known": tk,
        "tokens_coverage": round(tk / n, 4) if n else 0.0,
        "pair_known": both,
        "pair_coverage": round(both / n, 4) if n else 0.0,
        "split_known": split,
        "episodes_known": eps,
        "episodes_coverage": round(eps / n, 4) if n else 0.0,
        "usable_as_second_axis": mk > 0,
        "classifiable": bool(ref["usable"]),
        "unattributed": dict(gap) if gap else {"events": 0, "minutes": 0, "tokens": 0},
    }


def plan_items_from_registry(registry):
    """{plan id: [spec ids the plan declares]} from a plan registry (validate.plan_registry, which
    reads through the ONE front-matter parser).

    It exists so the per-plan roll-up carries its DENOMINATOR. A plan line reading "3 specs" is
    quietly partial: the reader cannot tell whether the plan has three items or thirteen. Adoption
    safe: an empty registry yields an empty map and the roll-up then reports the denominator as
    not declared rather than inventing one."""
    out = {}
    for pid, entry in (registry or {}).items():
        items = []
        for w in (entry.get("fm") or {}).get("work") or []:
            if isinstance(w, dict) and isinstance(w.get("spec"), str):
                items.append(w["spec"])
        out[pid] = items
    return out


def by_plan(rows, plan_items=None):
    """The pair rolled up per plan, which is the other place effort is shown. Sums carry their own
    known-counts: a plan total of 0 minutes over 9 specs none of which recorded any is reported as
    0 of 9 known, never as a plan that cost no judgment. `work_items` is the plan's declared item
    count when a registry was supplied and None when it was not."""
    items = plan_items or {}
    out = {}
    for r in rows:
        b = out.setdefault(r["plan"], {
            "specs": 0, "tokens": 0, "tokens_known": 0,
            "judgment_minutes": 0, "minutes_known": 0, "episodes": 0,
            "work_items": len(items[r["plan"]]) if r["plan"] in items else None,
        })
        b["specs"] += 1
        b["tokens"] += r["tokens"]
        b["tokens_known"] += 1 if r["tokens_known"] else 0
        b["judgment_minutes"] += r["judgment_minutes"]
        b["minutes_known"] += 1 if r["judgment_known"] else 0
        b["episodes"] += r["episodes"]
    return out


def _num(value):
    """A figure as text without rounding a lie into it: an integral value prints as an integer, a
    fractional one keeps two decimals. `%d` would silently truncate, and a module whose subject is
    not printing figures that are not there should not print a figure smaller than the one it read."""
    return "%d" % value if float(value).is_integer() else "%.2f" % value


def _axis(value, known, unit):
    """One axis rendered: a figure when it was measured, the words "not recorded" when it was not.
    There is no third rendering, and in particular no zero standing in for silence."""
    return ("%s %s" % (_num(value), unit)) if known else "not recorded"


def pair_line(row):
    """THE ONE RENDERING OF THE PAIR. Every surface that shows effort renders it through this
    function, so this module's report, a status line and the dashboard cannot show the same change
    three ways or drift apart when the honesty rules change.

    Raw tokens are what is recorded and what is shown; the normalized display point is WARP-1406's
    concern and layers over this without touching it."""
    kinds = row["judgment_by_kind"]
    split = (" [review %s, approval %s]" % (_num(kinds["review"]), _num(kinds["approval"]))
             if row["split_known"] else " [split not recorded]" if row["judgment_known"] else "")
    return ("%-12s toe %-16s judgment %-16s%s  episodes %d  shape %s"
            % (row["spec"], _axis(row["tokens"], row["tokens_known"], "tok"),
               _axis(row["judgment_minutes"], row["judgment_known"], "min"),
               split, row["episodes"], row["shape"]))


def build(corpus, events, plan_items=None):
    """The pair for a whole corpus, classified: the one call a surface makes.

    `events` is the parsed event list, `corpus` the records from `toe_corpus.build`, and `plan_items`
    the optional declared-item map - all passed in by the caller for the same reason the corpus does
    it, so this is drivable from seeded data and can never reach for the real log behind a test's
    back."""
    rows = [pair(r, events) for r in corpus]
    rows, ref = classify(rows)
    return {
        "schema": SCHEMA,
        "rows": rows,
        "reference": ref,
        # The reference computed once and handed on, so the labels and `classifiable` cannot come
        # from two different comparisons against the population floor.
        "coverage": coverage(rows, unattributed(events), ref),
        "plans": by_plan(rows, plan_items),
    }


def render(report):
    """The text surface: the pair per spec, the pair per plan, and the gap as numbers. One line per
    spec through `pair_line`, so what a reader sees here is what any other surface shows."""
    cov, ref = report["coverage"], report["reference"]
    out = ["EFFORT IS A PAIR: tokens of effort, and human-judgment load.", ""]
    for row in report["rows"]:
        out.append("  " + pair_line(row))
    out.append("")
    out.append("per plan:")
    for plan in sorted(report["plans"]):
        b = report["plans"][plan]
        out.append("  %-14s %3d of %s work item spec(s) in the corpus  toe %s tok (%d known)  "
                   "judgment %s min (%d known)  episodes %d"
                   % (plan, b["specs"],
                      b["work_items"] if b["work_items"] is not None else "(not declared)",
                      _num(b["tokens"]), b["tokens_known"],
                      _num(b["judgment_minutes"]), b["minutes_known"], b["episodes"]))
    out.append("")
    out.append("coverage: %d record(s); judgment minutes known on %d (%.1f%%), tokens on %d "
               "(%.1f%%), both on %d (%.1f%%); judgment split known on %d; episodes on %d"
               % (cov["records"], cov["minutes_known"], 100 * cov["minutes_coverage"],
                  cov["tokens_known"], 100 * cov["tokens_coverage"],
                  cov["pair_known"], 100 * cov["pair_coverage"],
                  cov["split_known"], cov["episodes_known"]))
    out.append("reference: %s" % (ref["reason"] or "none"))
    gap = cov["unattributed"]
    out.append("unattributable: %d event(s) carrying %s minute(s) and %s token(s) name no spec, so "
               "no pair can hold them"
               % (gap["events"], _num(gap["minutes"]), _num(gap["tokens"])))
    if not cov["usable_as_second_axis"]:
        out.append("NOT USABLE AS A SECOND AXIS YET: no human minutes are recorded anywhere in this "
                   "log. The recorder exists (.veldo/spend.py record --human-minutes); nobody has "
                   "called it. Every shape above is unknown for that reason, and a zero here would "
                   "be a lie rather than a measurement.")
    if not cov["classifiable"]:
        out.append("NOT CLASSIFIABLE YET: %s" % ref["reason"])
    return "\n".join(out)


def _repo_report(shipped_only=True):
    """The report over THIS repository, assembled from the one reader of each input: the event log
    through events.read_log, the corpus through toe_corpus.build, the protected set through
    policy_check.protected_patterns, and the plan registry through validate.plan_registry."""
    events = _load(".veldo/events.py", "veldo_events_judgment").read_log()
    try:
        protected = _load(".veldo/policy_check.py", "veldo_policy_judgment").protected_patterns()
    except (OSError, ValueError):
        protected = ()  # adoption safe: no policy in this repository, no protected-path feature
    corpus = _load(".veldo/toe_corpus.py", "veldo_toe_corpus_judgment").build(
        events=events, protected=protected, shipped_only=shipped_only)
    V = _load(".veldo/validate.py", "veldo_validate_judgment")
    return build(corpus, events, plan_items_from_registry(V.plan_registry(ROOT / "plans")))


def _cli(argv):
    ap = argparse.ArgumentParser(
        prog="judgment_load.py",
        description="The second axis of effort: human-judgment load derived from the human minutes "
                    "the loop records, shown as a pair with tokens of effort. Reads only; writes "
                    "nothing.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report", help="the pair per spec and per plan, with the gap as numbers")
    r.add_argument("--json", action="store_true")
    r.add_argument("--all", action="store_true",
                   help="include specs that have not shipped (default: shipped only)")
    sub.add_parser("check", help="list every malformed figure in the log, through validate.fail")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        V = _load(".veldo/validate.py", "veldo_validate_judgment")
        events = _load(".veldo/events.py", "veldo_events_judgment").read_log()
        errs = check_log(events, ".veldo/events.jsonl", V.fail)
        print("judgment load: %d malformed figure(s) in %d event(s)" % (errs, len(events)))
        return 1 if errs else 0
    try:
        report = _repo_report(shipped_only=not a.all)
    except JudgmentLoadError as e:
        print("refusing to report judgment load: %s" % e, file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, indent=1) if a.json else render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
