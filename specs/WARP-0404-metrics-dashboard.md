---
schema: veldo.spec/v1
id: WARP-0404
title: Metrics dashboard - render the event-envelope metrics from events.jsonl (X4 of PLAN-0004)
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0004
work: X4
plan_revision: 3
human_approval: not_required
protected_paths: []
required_evidence: [unit, operational]
acceptance_criteria:
  - id: AC1
    text: A stdlib dashboard tool ships at .veldo/dashboard.py. It reads the event
      stream (.veldo/events.jsonl) and renders the derived metrics for a human to
      read - cycle time (spec.ready to spec.shipped), proof latency (spec.ready to
      proof.recorded), human minutes, gate pass rate, verdict counts, emergency
      debt, and regression health. It renders a readable text report by default
      and a self-contained HTML page under --html (inline CSS only, no external
      asset, script, font, link, or network request), optionally written to a
      file under --out. It imports nothing outside the standard library.
  - id: AC2
    text: The dashboard is a rendering layer with no calculation of its own. Every
      number it shows comes from .veldo/metrics.py compute(), the single source of
      truth for metrics; the dashboard calls compute() and formats the result, it
      never recomputes a figure independently. A single function returns the exact
      figures the renderers display, and both the text and HTML renderers consume
      only that function, so there is one numeric path from events to output and
      no room for a forked calculation.
  - id: AC3
    text: Where the reader lacked a datum it is extended once, not forked. metrics.py
      compute() gains verdict_counts (tallied from verdict.recorded events by
      verdict value) and regression_health (the gate's green/red history in time
      order - a green-to-red transition is a regression, red-to-green a recovery,
      and the last gate event is the current standing), and both the reader's own
      summary and the dashboard read those from compute(). The metrics.py template
      copy is updated to match the repository instance so the shipped reader and
      the home reader stay identical.
  - id: AC4
    text: The control logic is gate-tested in scripts/selftest.py (CHECK_unit) with
      a synthetic events stream and no external surface. The selftest calls
      metrics.compute() and the dashboard's figure function on the same events and
      asserts the dashboard's reported numbers EQUAL compute()'s for cycle time,
      human minutes, gate pass rate, verdict counts, and regression health. It
      proves the equality is non-tautological: a plausible forked recompute of the
      same metric (gate pass rate over the wrong denominator) yields a DIFFERENT
      number on the same stream, so a dashboard that recomputed instead of reading
      compute() would fail the assertion. It also asserts the rendered text and
      HTML actually carry those figures (the render binds to the figure function),
      that the HTML is self-contained, and that an empty stream renders honest
      blanks rather than crashing.
  - id: AC5
    text: .veldo/capabilities.yaml (repository instance and engine copy,
      kept byte-identical) declares the dashboard status mechanical - its control
      logic and its real surface (reading events.jsonl through metrics.compute and
      rendering) both run in the gate here via stdlib, with no product surface this
      repository lacks - and metrics_derivation's note is updated to record the new
      verdict-count and regression-health data. The status is honest: the dashboard
      overclaims nothing it does not run end to end in the gate.
  - id: AC6
    text: The deliverable is generic (zero company, product, or person names beyond
      the standard owner field, and zero absolute host paths in the tool, the spec,
      and the capabilities entry) and hygienic (ASCII only, no em or en dash, no
      double hyphen). The specs index regenerates to include this spec, and the
      full gate (lint, unit, generated, docs, template sync, secret scan, contract
      validation) stays green with every prior selftest case still passing.
rollback: git revert; X4 is additive - a new stdlib tool .veldo/dashboard.py (and
  its template copy), an extension to .veldo/metrics.py compute() (and its template
  copy), a selftest block, two capabilities entries, and this spec. It touches no
  protected path and no synced core enforcer (validate.py, policy_check.py,
  update_index.py, veldo-guard.sh) and adds no new required CHECK_ slot, so
  reverting removes the dashboard, the added metrics fields, and the unit block
  with no effect on any running gate; prior selftest cases are unchanged.
---

## Intent

PLAN-0004 turns VELDO from a method plus runners into an executable system, and
feature F3 (observability and ops) is how the humans running it see whether the
loop is healthy. The event envelope already records the loop's real steps and
metrics.py already derives the numbers that matter; what is missing is a way for
a person to read them at a glance. X4 delivers that: a dashboard that renders
cycle time, proof latency, human minutes, gate pass rate, verdict counts,
emergency debt, and regression health as a text report or a self-contained HTML
page. The one hard rule is no drift - the dashboard is a rendering of the single
source of truth, never a second opinion. It reads the numbers from
metrics.compute(); it does not recompute them, so the summary a person reads and
the dashboard they open can never disagree.

## Context

X4 of PLAN-0004, feature F3, pulled against plan revision 3 with no dependency;
X5 (cost and token budget governance) depends on it. It follows the shipped
pattern for a core capability: an additive stdlib module under .veldo/ next to the
reader it renders, a template copy shipped to adopting repos (as events.py and
metrics.py already are), control logic gate-tested in the unit slot with no live
surface, and an honest capabilities entry. Where the reader lacked a datum the
dashboard needs (verdict counts, regression health), metrics.py compute() is
extended once so there remains a single calculation the reader and the dashboard
both read - never a fork.

## Out of scope

Any new metric definition beyond surfacing what compute() derives (cost and token
governance is X5, which extends the event stream and reader on its own terms).
Serving the HTML over a network, a live-updating page, or any hosting stack - the
dashboard writes a self-contained file a person opens, consistent with the plan's
non-goal of a bespoke hosting stack before measured need. Changing the event
vocabulary or the envelope. Charts or external visualization libraries - the HTML
is plain inline-styled cards, stdlib-rendered, no third party.

## Notes

Why mechanical and not reference: the dashboard's surface is reading events.jsonl
through metrics.compute() and formatting the result, and both the control logic
and that real surface run in this gate on this box with stdlib only - there is no
product surface the home repository lacks, so the status is mechanical, not
reference.

Why the no-drift test is non-tautological: the risk the spec guards against is a
future edit that "optimizes" the dashboard to recompute a metric itself and
drifts from compute(). The selftest asserts the rendered figures equal compute()
on a synthetic stream AND shows that a plausible forked recompute of the same
metric (gate pass rate over the per-event denominator instead of pass over
pass-plus-fail) gives a different number on that stream, so the equality
assertion has teeth: had the dashboard forked the calculation, the gate would be
red. A mutation run during development confirmed this - forking one figure turned
the selftest red naming the mismatch.

The reviewer should confirm by rerunning the selftest and driving the tool: (1)
the rendered numbers equal metrics.compute() for cycle time, human minutes, gate
pass rate, verdict counts, and regression health; (2) the forked-recompute
demonstration proves the equality is discriminating; (3) the HTML is
self-contained (no external asset, script, link, or network request); (4) the
capabilities status equals mechanical in both the instance and the template copy;
(5) the docs, secret, lint, generated, and template-sync gates stay green with
every prior selftest case still passing.
