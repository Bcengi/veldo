---
schema: veldo.spec/v1
id: VELDO-0084
title: Readmission, scope enforcement, and admission-debt reporting
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W69
plan_revision: 1
depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0079]
placement: [contracts, tracker, fleet, metrics, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/frontier.py"
  - ".veldo/frontier.py"
  - "packs/*/.veldo/frontier.py"
  - "engine/.veldo/tasks.py"
  - ".veldo/tasks.py"
  - "packs/*/.veldo/tasks.py"
  - "engine/.veldo/request_projection.py"
  - ".veldo/request_projection.py"
  - "packs/*/.veldo/request_projection.py"
  - "engine/.veldo/control_readmission*.py"
  - ".veldo/control_readmission*.py"
  - "packs/*/.veldo/control_readmission*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0084_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0084-readmission-scope-admission-debt.md"
  - "specs/index.md"
  - "proof/VELDO-0084/*"
behavior_bearing: true
observability:
  logs: >
    Scope invalidations identify old/new envelope digests, changed dimensions, stopped units and
    required grooming request.
  metrics: >
    Report RAW, PREPARED and AWAITING_GROOMING counts/oldest ages, prepared debt over seven days,
    proposed Tokens of Effort and unknown estimates.
  traces: >
    Trace discovered scope change through withdrawn authority to current enrolled readmission and
    any resumed contract.
  error_taxonomy: >
    Distinguish signed-ceiling excess, material class change, stale resumption, missing estimate
    and fourteen-day andon.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Scope changes invalidate affected admission before further build or publication. Set:
      control_readmission, frontier.claimable and C shared eligibility over R69 paths, interfaces,
      specs/criteria, data classes, dependencies, targets, risk and artifact types. Completeness:
      Compare schema dimensions and invalidation predicates bidirectionally. Change each
      independently, including new protected path, migration, class change and budget above 20
      percent; race direct execution and publication. Require affected units AWAITING_AUTHORITY
      and backlog AWAITING_GROOMING with only previously authorized
      containment/observation/reconciliation continuing. Falsifier: Ignore a newly discovered
      protected path because the project version is unchanged; readmission/protected-scope must
      detect continued build permission.
    falsified_by: >
      Ignore a newly discovered protected path because the project version is unchanged;
      readmission/protected-scope must detect continued build permission.
  - id: AC2
    text: >
      Claim: A smaller budget increase still cannot exceed the signed ceiling, and renewed
      authority binds current scope. Set: Readmission settlement through request.request_digest
      and E, with B account/project/unit reservation predicates. Completeness: Test below/at/above
      both 20 percent and the signed ceiling independently, including a 10-percent excess over
      that ceiling. Accept only a current authorized presentation-bound revision with new
      decomposition/priority where applicable; preserve old requests. Explicit R68 escalation
      conveys only emergency bounds, never ordinary scope expansion. Falsifier: Permit a
      10-percent increase above the signed ceiling; readmission/small-over-ceiling must detect a
      newly permitted provider request.
    falsified_by: >
      Permit a 10-percent increase above the signed ceiling; readmission/small-over-ceiling must
      detect a newly permitted provider request.
  - id: AC3
    text: >
      Claim: Admission debt reports age and unknown effort without admitting or reprioritizing
      work. Set: control_readmission reports, tasks.task_report/report_lines and
      request_projection views for RAW, PREPARED and AWAITING_GROOMING. Completeness: Populate all
      lifecycle states and timestamps just below/at/above seven and fourteen days. Independently
      compute counts, oldest ages and prepared debt totals; retain missing estimates as unknown.
      Debt older than fourteen days creates one durable andon obligation. Rejected work retains
      preparation/reason and consumes no floor capacity. Verify state/priority equality before and
      after reporting. Falsifier: Convert a missing effort estimate to zero in debt totals;
      debt/unknown-effort must detect hidden unestimated work.
    falsified_by: >
      Convert a missing effort estimate to zero in debt totals; debt/unknown-effort must detect
      hidden unestimated work.
required_evidence: [unit, integration]
rollback: >
  Retain authority stops and old envelopes; restore reports from verified history and resume only
  after a current readmission decision.
---

## Intent

Stop work whose accepted scope has changed and expose aging admission work without granting it authority.

## Context

Package F, W69 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R61/R69 connect material changes to execution permission. Metrics are derived, while invalidation and readmission control critical authority. Risk is critical; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

Automatic reprioritization, free budget growth and redefinition of the seven-day threshold are excluded.

## Notes

D1/D2 block atomic invalidation and published readmission; D3/D4 remain required for stopped execution qualification. Dmitry must designate the authority allowed to enlarge scope, budget or priority; a project owner label is insufficient. Map control_readmission and report consumers into the declared areas before ready and register installed assets. Keep age tests tied to the repository clock stand-down contract: an unanswerable clock reports uncertainty, not a young debt age. Preserve signed-ceiling boundary cases separately from percentage cases.
