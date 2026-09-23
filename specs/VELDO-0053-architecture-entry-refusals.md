---
schema: veldo.spec/v1
id: VELDO-0053
title: Architecture failure handling at every eligibility entry
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W38
plan_revision: 3
depends_on: [VELDO-0016, VELDO-0052]
placement: [distribution, contracts, fleet, loop]
protected_paths: []
footprint:
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/validate_checks.py"
  - ".veldo/validate_checks.py"
  - "packs/*/.veldo/validate_checks.py"
  - "engine/.veldo/arch.py"
  - ".veldo/arch.py"
  - "packs/*/.veldo/arch.py"
  - "engine/.veldo/frontier.py"
  - ".veldo/frontier.py"
  - "packs/*/.veldo/frontier.py"
  - "engine/.veldo/plan.py"
  - ".veldo/plan.py"
  - "packs/*/.veldo/plan.py"
  - "engine/.veldo/executor.py"
  - ".veldo/executor.py"
  - "packs/*/.veldo/executor.py"
  - "engine/.veldo/dispatch.py"
  - ".veldo/dispatch.py"
  - "packs/*/.veldo/dispatch.py"
  - "engine/.veldo/control_eligibility*.py"
  - ".veldo/control_eligibility*.py"
  - "packs/*/.veldo/control_eligibility*.py"
  - "scripts/suites/*_veldo_0053_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "scripts/suites/60_veldo_0052_eligibility.py"
  - "specs/VELDO-0053-architecture-entry-refusals.md"
  - "specs/index.md"
  - "proof/VELDO-0053/*"
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
      Claim: Required architecture distinguishes valid, absent and invalid accepted contracts. Set
      and completeness: Drive each loader/ready entry with valid, optional absent, required absent,
      unreadable, malformed and wrong-type real files; compare outcomes to the installed structural
      validator and policy. Falsifier: Treat a present malformed contract as optional absence; the
      ready-refusal check must fail.
    falsified_by: >
      Treat a present malformed contract as optional absence; the ready-refusal check must fail.
  - id: AC2
    text: >
      Claim: Invalid or required-missing architecture blocks each enabled eligibility entry. Set and
      completeness: Enumerate shared entry registrations and invoke frontier, plan, executor and
      direct review with invalid accepted architecture; inspect zero new claims/launches and
      unchanged trunk. Falsifier: Skip architecture checking for direct review; the forbidden-review
      launch check must fail.
    falsified_by: >
      Skip architecture checking for direct review; the forbidden-review launch check must fail.
  - id: AC3
    text: >
      Claim: Architecture enforcement uses the trusted installed validator and accepted artifact.
      Set and completeness: Delete or weaken clone architecture and replace its validator with a
      success stub; run the installed entry against the accepted digest and record actual
      executable/artifact identity. Falsifier: Load the clone validator instead of the installed
      one; the substitution check must fail.
    falsified_by: >
      Load the clone validator instead of the installed one; the substitution check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Architecture failure handling at every eligibility entry. Deliver the normal function needed by the running factory journey.

## Context

W38 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

No architecture.yaml amendment is authorized here. This normal entry check is consumed by
0052/0057; it is not deferred merely because the larger governance package is later. Use
actual permission denial under the worker identity, not mocked read errors.

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
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC2 concurrent
architecture-input matrix and AC3 racing revision qualification moved to Release 2. Required
architecture checks at all normal floor entries remain. The criteria, declared evidence
universe, Context and Notes above now carry only the retained function. No specification
status or historical proof was changed.

2026-09-23, build: scripts/check_teeth_mutations.py joined the footprint so the declared
falsifiers and their second mutations are registered with the repository's mutation driver
(finding 53). No criterion, status or evidence universe changed.

2026-09-23, review fixes: scripts/suites/60_veldo_0052_eligibility.py joined the footprint. A Gate
built with no workspace passed the architecture predicate whenever the authority held no record, so
the constructor's default argument was a pass. It now always refuses by name, and the two Gates that
suite constructs are given the workspace they read. No criterion, status or evidence universe changed.
