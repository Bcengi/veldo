---
schema: veldo.spec/v1
id: VELDO-0054
title: Decision-record dependency evaluation for the floor slice
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W39
plan_revision: 3
depends_on: [VELDO-0020, VELDO-0035, VELDO-0052]
placement: [distribution, contracts, fleet]
protected_paths: []
footprint:
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/plan.py"
  - ".veldo/plan.py"
  - "packs/*/.veldo/plan.py"
  - "engine/.veldo/frontier.py"
  - ".veldo/frontier.py"
  - "packs/*/.veldo/frontier.py"
  - "engine/.veldo/control_eligibility*.py"
  - ".veldo/control_eligibility*.py"
  - "packs/*/.veldo/control_eligibility*.py"
  - "engine/.veldo/control_decision_dependency*.py"
  - ".veldo/control_decision_dependency*.py"
  - "packs/*/.veldo/control_decision_dependency*.py"
  - "scripts/suites/*_veldo_0054_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0054-floor-decision-dependencies.md"
  - "specs/index.md"
  - "proof/VELDO-0054/*"
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
      Claim: Plan and specification eligibility resolves exact accepted decision bindings. Set and
      completeness: Enumerate enabled plan._decision_blocks, item_state, cmd_run_check, frontier and
      direct floor consumers; pass current signed fixture settlements bound to framing/subject
      digests, and change either digest. Only the current exact binding unblocks. Falsifier: Accept
      a receipt without its framing digest; the wrong-framing eligibility check must fail.
    falsified_by: >
      Accept a receipt without its framing digest; the wrong-framing eligibility check must fail.
  - id: AC2
    text: >
      Claim: Missing, ambiguous or unsupported governing decisions remain named blockers. Set and
      completeness: Drive each of these three cases plus a valid bound decision through every
      enabled consumer against real accepted artifacts and SQLite. No inline resolved text
      substitutes for settlement. Falsifier: Treat an inline status edit as a ruling; the unsigned-
      resolution check must fail.
    falsified_by: >
      Treat an inline status edit as a ruling; the unsigned-resolution check must fail.
  - id: AC3
    text: >
      Claim: A ruling authorizes only its recorded subject and scope. Set and completeness: Use a
      valid signed decision for one spec/plan and try it on another or with changed
      operation/target/parameters; inspect refused eligibility and preserved accepted artifacts.
      Falsifier: Reuse one subject ruling for another subject; the scope-binding check must fail.
    falsified_by: >
      Reuse one subject ruling for another subject; the scope-binding check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Decision-record dependency evaluation for the floor slice. Deliver the normal function needed by the running factory journey.

## Context

W39 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

The normal spec/plan governing decision consumer is required now; 0069 supplies actual
settlement binding later in Release 1. Signed fixtures only test consumption, never
authenticate a live owner. Tripwire and adversarial-decision-review obligations unsupported by
this slice block eligibility.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 1: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC2
expiry/reverse invalidation and AC3 tripwire/adversarial decision-review depth moved to
Release 3; crash/restart matrix moved to Release 2. AC1 normal exact binding consumption
remains. The criteria, declared evidence universe, Context and Notes above now carry only the
retained function. No specification status or historical proof was changed.
