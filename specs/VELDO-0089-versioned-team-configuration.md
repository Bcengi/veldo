---
schema: veldo.spec/v1
id: VELDO-0089
title: Versioned team configuration
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W74
plan_revision: 3
depends_on: [VELDO-0025, VELDO-0036, VELDO-0049, VELDO-0076]
placement: [contracts, engine, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/decision_review.py"
  - ".veldo/decision_review.py"
  - "packs/*/.veldo/decision_review.py"
  - "engine/.veldo/control_team*.py"
  - ".veldo/control_team*.py"
  - "packs/*/.veldo/control_team*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0089_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0089-versioned-team-configuration.md"
  - "specs/index.md"
  - "proof/VELDO-0089/*"
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
      Claim: Versioned team data defines one PM and required elaboration, implementation and
      independent review roles. Set and completeness: Compare required responsibilities, expertise,
      proposal permissions, engine eligibility, context/tool restrictions, budget and independence
      fields to the team schema and project requirements; missing or conflicting staffing produces
      an owner request, not invented workers. Falsifier: Accept a team missing required independent
      review; the incomplete-roster check must fail.
    falsified_by: >
      Accept a team missing required independent review; the incomplete-roster check must fail.
  - id: AC2
    text: >
      Claim: Team changes require current scoped owner authority and do not confer admission rights.
      Set and completeness: Accept a version-bound owner amendment and reject stale versions,
      altered signed parameters and manager self-promotion through the retained settlement path;
      compare stored team revisions and unchanged authority grants. Falsifier: Grant admission
      rights to a configured PM role; the roster-not-authority check must fail.
    falsified_by: >
      Grant admission rights to a configured PM role; the roster-not-authority check must fail.
  - id: AC3
    text: >
      Claim: Assignments bind current team configuration and applicable engineering-review policy.
      Set and completeness: Create builder/reviewer assignments under real policy and team
      revisions; attempt missing policy, insufficient review count, same builder/reviewer and wrong
      reviewed subject. Each must block, and a valid independent assignment succeeds. Falsifier:
      Default a missing review policy to no reviews; the policy-required check must fail.
    falsified_by: >
      Default a missing review policy to no reviews; the policy-required check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Versioned team configuration. Deliver the normal function needed by the running factory journey.

## Context

W74 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Assignment consumes VELDO-0049 engineering-review policy and its count, independence and
exact-subject bindings. It does not invoke deferred VELDO-0070/decision_review adversarial
decision workflows. Missing applicable policy refuses; no permissive fallback or roster-
derived authority is allowed.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 4: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC2 amendment
races and AC3 mid-cycle matrix moved to Release 2; extra channels moved to Release 4; every-
review-tier/adversarial decision-review depth moved to Release 3. Versioned roles, expertise,
budgets and applicable 0049 engineering review remain. The criteria, declared evidence
universe, Context and Notes above now carry only the retained function. No specification
status or historical proof was changed.
