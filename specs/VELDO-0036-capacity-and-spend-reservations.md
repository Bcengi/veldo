---
schema: veldo.spec/v1
id: VELDO-0036
title: Capacity and subscription usage reservations
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W21
plan_revision: 3
depends_on: [VELDO-0023, VELDO-0025]
placement: [fleet, metrics, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/accounts.py"
  - ".veldo/accounts.py"
  - "packs/*/.veldo/accounts.py"
  - "engine/.veldo/budget.py"
  - ".veldo/budget.py"
  - "packs/*/.veldo/budget.py"
  - "engine/.veldo/control_reservation*.py"
  - ".veldo/control_reservation*.py"
  - "packs/*/.veldo/control_reservation*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0036_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0036-capacity-and-spend-reservations.md"
  - "specs/index.md"
  - "proof/VELDO-0036/*"
behavior_bearing: true
observability:
  logs: >
    Record the operation, domain, repository, unit or request identity, accepted input versions,
    outcome and named refusal without secrets.
  metrics: >
    Count accepted and refused operations and expose current pending work for this specification.
  traces: >
    Join accepted inputs, actual service observations and resulting authority records by identity.
  error_taxonomy: >
    Distinguish invalid input, missing authority, stale subject, unavailable service,
    missing evidence and unknown outcome where applicable; never label unknown as success.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Capacity and subscription usage reservations are atomic at applicable account,
      project and unit ceilings before dispatch. Set and completeness: On the configured journey accounts/project,
      exercise below, equal and above each ceiling and two clients competing for the last slot in
      real SQLite; compare allocation rows and balances. Falsifier: Check the last slot outside its
      reservation transaction; competing admissions must over-allocate and fail the check.
    falsified_by: >
      Check the last slot outside its reservation transaction; competing admissions must over-
      allocate and fail the check.
  - id: AC2
    text: >
      Claim: Every subscription CLI invocation checks and reserves its applicable usage caps before
      launch, including initial, retry and follow-on invocations. Set and completeness: Enumerate
      invocation boundaries from adapter registrations; exercise invocation counts, wall time,
      CLI-reported tokens/messages where available, and subscription rate-limit windows with
      remaining, exhausted and unknown allowance. Refusals launch nothing; a worker stops when
      its cap is reached. No price or per-request monetary maximum is required. Falsifier:
      Check a follow-on cap after launch; the pre-call ordering check must fail.
    falsified_by: >
      Check a follow-on cap after launch; the pre-call ordering check must fail.
  - id: AC3
    text: >
      Claim: Usage settles once per invocation/sequence and unknown usage retains conservative
      reservations.
      Set and completeness: Ingest normal, duplicate and missing reports for accepted requests;
      compare balances in the declared usage units. Timeout or cancellation without conclusive
      usage or non-execution evidence cannot free the allocation. Falsifier: Release exposure on a timeout after
      acceptance; a subsequent invocation must exceed its usage cap and fail the check.
    falsified_by: >
      Release exposure on a timeout after acceptance; a subsequent invocation must exceed its usage cap
      and fail the check.
  - id: AC4
    text: >
      Claim: A capacity slot is released only after actual worker termination, cleanup and accounted
      or retained unknown-usage reservations. Set and completeness: Hold a real descendant alive, withhold
      outcome/accounting and leave clone cleanup incomplete separately; attempt retirement and
      observe refusal until required ordinary observations exist. Falsifier: Release capacity on
      parent exit while its descendant is alive; the slot-reuse check must fail.
    falsified_by: >
      Release capacity on parent exit while its descendant is alive; the slot-reuse check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Capacity and subscription usage reservations. Deliver the normal function needed by the running factory journey.

## Context

W21 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Models run only through logged-in Claude Code and Codex subscriptions; paid model APIs are
prohibited. A budget is a usage allowance, not a per-call price. Reserve against the configured
account, project and unit using invocation counts and wall time, tokens/messages as the CLI
reports them, and the subscription's exposed rate-limit windows. Record units, observation
watermarks and reset times. Never invent token telemetry, remaining quota or a monetary maximum.

Before every initial, retry or follow-on CLI invocation, atomically check the applicable caps,
retain outstanding reservations and reserve the next invocation/time allowance. Observe reported
token/message usage and rate-limit signals during execution; stop the worker when its cap is
reached, and refuse further invocations until allowance is available. A reported window limit
blocks dispatch until its reported reset or refreshed allowance. Delayed token/message reports
are accounted when available, not represented as an enforceable per-request maximum.

Qualification may use supported invocation/time controls without requiring an unavailable token
limit or any price. Missing usage is never zero: keep its reservation; if an applicable remaining
allowance cannot be bounded conservatively, stop and refuse further invocation until reconciled.
A process exit or timeout alone does not establish unused allowance.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, pre-invocation subscription usage caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 1: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC1 crash/broad
intersecting allocation matrix, AC3 restart/reordering and AC4 durable quarantine recovery
moved to Release 2. Subscription usage caps, deduplicated accounting and unknown usage reservations remain. The criteria,
declared evidence universe, Context and Notes above now carry only the retained function. No
specification status or historical proof was changed.

2026-09-22 implementation: registers the Release 1 reservation suite in scripts/suites/manifest.json
and requires.json, and its temporary-copy negative controls in scripts/check_teeth_mutations.py.
The latter is the shared mutation driver required by this work; no criterion or status changes.
