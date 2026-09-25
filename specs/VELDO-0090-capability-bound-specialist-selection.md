---
schema: veldo.spec/v1
id: VELDO-0090
title: Capability-bound specialist selection
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W75
plan_revision: 4
depends_on: [VELDO-0036, VELDO-0060, VELDO-0061, VELDO-0089, VELDO-0108, VELDO-0125, VELDO-0127]
placement: [contracts, fleet, engine, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/tasks.py"
  - ".veldo/tasks.py"
  - "packs/*/.veldo/tasks.py"
  - "engine/.veldo/claim.py"
  - ".veldo/claim.py"
  - "packs/*/.veldo/claim.py"
  - "engine/.veldo/frontier.py"
  - ".veldo/frontier.py"
  - "packs/*/.veldo/frontier.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/control_specialist*.py"
  - ".veldo/control_specialist*.py"
  - "packs/*/.veldo/control_specialist*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0090_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0090-capability-bound-specialist-selection.md"
  - "specs/index.md"
  - "proof/VELDO-0090/*"
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
      Claim: Selection conjunctively matches expertise, current authority, engine, host, context and
      independence. Set and completeness: For the configured team and Linux/Mac workers, vary each
      required predicate independently in real assignments, including iOS-on-Linux and person-
      required work proposed to an agent; inspect eligible candidates or named refusal. Falsifier:
      Select a Linux worker for a macOS requirement; the host-capability check must fail.
    falsified_by: >
      Select a Linux worker for a macOS requirement; the host-capability check must fail.
  - id: AC2
    text: >
      Claim: Missing expertise yields a staffing request or blocker without an invented fallback.
      Set and completeness: Remove the only eligible specialist or independent reviewer, run a PM
      selection and inspect one owner request, no dispatch and no held waiting worker; a
      reassignment retains scope, deadline and budget. Falsifier: Fall back to the builder when no
      independent reviewer exists; the no-review-fallback check must fail.
    falsified_by: >
      Fall back to the builder when no independent reviewer exists; the no-review-fallback check
      must fail.
  - id: AC3
    text: >
      Claim: Selection is only a proposal; assignment and dispatch recheck current versions and
      reservations. Set and completeness: Select a worker, change its team/assignment version or
      consume the remaining budget before acceptance, then call the real assignment/dispatch
      boundary; require a named refusal without launch or expanded scope. Falsifier: Skip team-
      version checking on acceptance; the stale-selection check must fail.
    falsified_by: >
      Skip team-version checking on acceptance; the stale-selection check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Capability-bound specialist selection. Deliver the normal function needed by the running factory journey.

## Context

W75 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Required capabilities include operating-system requirements: macOS/iOS work goes only to a
qualified Mac through the new remote-worker routing spec. Exact per-role MCP/tool handoff is
separately specified. Matching capabilities never substitutes for named person authority or
review independence.

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
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC3 concurrent
revocation/reassignment/exhaustion moved to Release 2; AC1 all-model/host matrix moved to
Release 4 except Linux/Mac. Specialist matching, missing-expertise stops and assignment checks
remain. The criteria, declared evidence universe, Context and Notes above now carry only the
retained function. No specification status or historical proof was changed.
