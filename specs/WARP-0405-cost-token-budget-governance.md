---
schema: veldo.spec/v1
id: WARP-0405
title: Cost and token budget governance - track and enforce spend per plan and per spec over the event stream (X5 of PLAN-0004)
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0004
work: X5
plan_revision: 3
depends_on: [WARP-0404]
human_approval: not_required
protected_paths: []
required_evidence: [unit, operational]
acceptance_criteria:
  - id: AC1
    text: Spend rides the single existing event stream. .veldo/events.py emit and
      make_event gain optional numeric tokens and cost_usd fields that ride the
      veldo.event/v1 envelope exactly the way human_minutes already does,
      attributed by the existing correlation_id (which defaults to the spec or
      plan id). The extension is backward compatible - an event with no spend
      fields still parses and validates, and events.jsonl validation is
      unchanged - and no second data store is introduced. .veldo/events.py and
      engine/.veldo/events.py stay byte-identical.
  - id: AC2
    text: Budgets are declared in the plan, validated for shape only. A plan may
      carry a light budgets block in veldo.plan/v1 (an optional plan-level tokens
      cap, an optional cost_usd cap, and an optional per_spec list of per-work-item
      caps). A missing budgets block means no budget governance for that plan
      (backward compatible). The block's shape is validated the lightweight
      yamlish way plan fields are validated today - not a JSON Schema - and a
      malformed block (a non-mapping, an unknown key, a negative or non-numeric
      cap, a per_spec entry without a valid spec id or without any cap, or a
      duplicate spec) is a named BudgetError, never a silent no-governance pass.
      Float caps that the yamlish subset leaves as strings are coerced to numbers.
  - id: AC3
    text: The spend aggregation reuses metrics.compute() once, so there is no
      drift. .veldo/metrics.py compute() is extended a single time to aggregate
      spend from the stream - a token total, a cost_usd total, and spend by
      correlation_id - and both the reader's own summary and the budget enforcer
      read those from compute(), never a forked calculation. .veldo/metrics.py and
      engine/.veldo/metrics.py stay byte-identical. A selftest asserts
      the budget module's spend numbers EQUAL metrics.compute()'s on the same
      stream (no drift).
  - id: AC4
    text: A mechanical enforcer ships at .veldo/budget.py. Given a plan (and its
      per-spec caps) and the event stream, it computes spend per plan (attributed
      to the plan id and its work-item spec correlations, not the global stream
      total) and per spec (that spec's own correlation), reports OVER or UNDER,
      and EXITS NON-ZERO naming the plan or spec and the overage when any declared
      budget is exceeded; it exits 0 when every declared budget is within limit or
      no budgets are declared. It reads events.jsonl only through metrics.compute
      and imports nothing outside the standard library.
  - id: AC5
    text: The control logic and its real surface are gate-tested with no external
      dependency. The selftest (CHECK_unit) drives budget.py over synthetic event
      streams and crafted plans: a stream under budget passes, a stream over a
      plan budget fails loud naming the plan and the overage, a stream over a
      per-spec budget fails loud naming the spec and the overage, a plan with no
      budgets declared passes, and the no-drift assertion holds (budget spend
      equals metrics.compute). It proves the enforcer is non-tautological: a
      one-line mutation that ignores the cap (always-under) and a one-line
      mutation that misattributes spend across correlations each turn the gate
      red, and every malformed budgets shape is rejected as a named BudgetError.
  - id: AC6
    text: Capabilities coverage is honest. Both .veldo/capabilities.yaml and
      engine/.veldo/capabilities.yaml carry, byte-identically, a
      budget_governance entry with status drawn from the manifest vocabulary
      (mechanical). mechanical is honest because the control logic AND its real
      surface - reading events.jsonl through metrics.compute and enforcing against
      declared budgets - both run end to end in the gate here over synthetic
      streams with stdlib only; there is no product surface this repository lacks,
      so the status overclaims nothing.
  - id: AC7
    text: The deliverable is generic (zero company, product, or person names beyond
      the standard owner field, and zero absolute host paths in the module, the
      plan budgets block, the capabilities entry, and this spec) and hygienic
      (ASCII only, no em or en dash, no double hyphen). The specs index
      regenerates to include this spec, and the full gate (lint, unit, generated,
      docs, template sync, secret scan, contract validation) stays green with
      every prior selftest case still passing.
rollback: git revert; X5 is additive - optional tokens and cost_usd envelope
  fields on .veldo/events.py (and its template copy), a single spend aggregation
  added to .veldo/metrics.py compute() (and its template copy), a new stdlib module
  .veldo/budget.py, a budgets block on PLAN-0004, a selftest block, two
  capabilities entries, and this spec. It touches no protected path and no synced
  core enforcer (validate.py, policy_check.py, update_index.py, veldo-guard.sh) and
  adds no new required CHECK_ slot, so reverting removes the spend fields, the
  aggregation, the enforcer, and the unit block with no effect on any running
  gate; prior selftest cases and prior events with no spend fields are unchanged.
---

## Intent

PLAN-0004 turns VELDO from a method plus runners into an executable system, and
feature F3 (observability and ops) is how the humans running it keep the loop
healthy. X4 gave them a dashboard over the events VELDO already emits; X5 gives
them governance over what those events cost. The event stream already ties every
step of a change together by correlation_id, and the metrics reader already
derives the numbers that matter from it. What is missing is a way to say how much
a plan or a spec is allowed to spend and to have that limit enforced. X5 delivers
it as a reader and enforcer over the one existing stream: spend rides the
envelope the same optional way human_minutes does, budgets are declared in the
plan, the aggregation reuses metrics.compute() so the enforcer and the dashboard
can never disagree, and the enforcer exits non-zero naming the plan or spec and
the overage when a declared budget is exceeded. The one hard rule is no second
store and no drift - budget burn is the metrics reader's numbers, read once.

## Context

X5 of PLAN-0004, feature F3, pulled against plan revision 3, depends on X4
(WARP-0404) because the no-drift discipline it inherits - read budget burn only
through metrics.compute(), never recompute - is the same discipline the dashboard
established. It follows the shipped pattern for a core capability: an additive
stdlib module under .veldo/ next to the reader it consumes, an optional extension
to the events envelope and the metrics reader kept byte-identical with their
template copies and backward compatible, control logic gate-tested in the unit
slot with no live surface, and an honest capabilities entry. Where the envelope
lacked a datum the governance needs (per-event spend), events.py is extended once
so tokens and cost_usd ride it the way human_minutes already does, and
metrics.compute() aggregates that spend once so there remains a single
calculation the reader and the enforcer both read - never a fork.

## Out of scope

A second spend data store, a spend ledger, a metering daemon, or a service - the
whole design is a reader over the single event stream, proportionate to the need
and no heavier. Emitting spend automatically from the executor or an agent (that
is a later, additive caller; the envelope field and its CLI are the seam).
Blocking a merge or a push on a budget overage server-side (that is control-plane
work gated on the plan's decisions); the enforcer exits non-zero so an adopting
repo can wire it where it chooses. Charging models, price tables, or currency
conversion beyond the plain cost_usd the caller records. Changing the event
vocabulary or the correlation semantics.

## Notes

Why mechanical and not reference: the enforcer's surface is reading events.jsonl
through metrics.compute() and comparing the aggregated spend against the budgets a
plan declares, and both the control logic and that real surface run in this gate
on this box with stdlib only over synthetic streams - there is no product surface
the home repository lacks, so the status is mechanical, not reference.

Why the no-drift and non-tautology tests have teeth: the risk is a future edit
that "optimizes" the enforcer to sum spend itself and drifts from compute(), or
that quietly stops enforcing the cap. The selftest asserts the enforcer's spend
equals metrics.compute() on a synthetic stream (no drift), and drives two
one-line mutations that must turn the gate red - a cap-ignoring enforcer that
always reports under budget misses a real overage, and an enforcer that sums the
global stream total instead of the plan's own correlations misattributes an
unrelated correlation's spend into the plan. Both were run during development and
turned the selftest red naming the mismatch, so the assertions are discriminating.
Every malformed budgets shape is rejected as a named BudgetError, so a validator
that silently accepted a bad budget would turn the gate red.

The reviewer should confirm by rerunning the selftest and driving the tool: (1)
tokens and cost_usd ride the events envelope and old events without them still
parse; (2) the enforcer's spend equals metrics.compute() for the plan and each
spec; (3) an under-budget stream passes and an over-budget plan and per-spec
stream each fail loud naming the plan or spec and the overage; (4) a plan with no
budgets passes; (5) the cap-ignoring and misattribution mutations each turn the
gate red; (6) the capabilities status equals mechanical byte-identically in both
the instance and the template copy; (7) the docs, secret, lint, generated, and
template-sync gates stay green with every prior selftest case still passing.
