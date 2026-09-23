---
schema: veldo.spec/v1
id: VELDO-0052
title: Shared eligibility in work, frontier, plan, direct executor, and review
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W37
plan_revision: 3
depends_on: [VELDO-0021, VELDO-0025, VELDO-0031, VELDO-0035, VELDO-0036]
placement: [distribution, fleet, loop, contracts]
protected_paths: []
footprint:
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/work.py"
  - ".veldo/work.py"
  - "packs/*/.veldo/work.py"
  - "engine/.veldo/work_state.py"
  - ".veldo/work_state.py"
  - "packs/*/.veldo/work_state.py"
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
  - "scripts/suites/*_veldo_0052_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0052-shared-floor-eligibility.md"
  - "specs/index.md"
  - "proof/VELDO-0052/*"
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
      Claim: Every enabled floor entry invokes shared station-specific eligibility, including direct
      build and review. Set and completeness: Enumerate frontier, work, plan, executor, dispatch and
      publication registrations from actual call sites; invoke each with absent admission, draft
      governing plan, unresolved dependency/decision, stale scope and valid inputs against the real
      store. Count launches. Falsifier: Bypass eligibility in direct _dispatch_review; a blocked
      item must launch a reviewer and fail the check.
    falsified_by: >
      Bypass eligibility in direct _dispatch_review; a blocked item must launch a reviewer and fail
      the check.
  - id: AC2
    text: >
      Claim: Claim and subsequent transitions validate the current versions/digests of their
      consumed inputs. Set and completeness: Change an accepted dependency or authority input after
      selection while project version stays fixed; exercise dispatch, review and publication checks
      against the new snapshot and observe named refusal. Falsifier: Check only current_status after
      a prerequisite is withdrawn; the stale-input check must fail.
    falsified_by: >
      Check only current_status after a prerequisite is withdrawn; the stale-input check must fail.
  - id: AC3
    text: >
      Claim: All work/plan/frontier readers distinguish attempt, proof acceptance, landed revision
      and objective satisfaction. Set and completeness: Enumerate completion consumers and read each
      fact in a fresh process using real receipts; passing verdicts and shipped file text without
      the exact landing receipt cannot satisfy engineering dependencies. Falsifier: Conclude from a
      manifest plus passing verdict on build-only; the completion-reader comparison must fail.
    falsified_by: >
      Conclude from a manifest plus passing verdict on build-only; the completion-reader comparison
      must fail.
  - id: AC4
    text: >
      Claim: Every build and review subscription CLI invocation checks usage caps before launch
      and retains unknown usage conservatively. Set
      and completeness: Enumerate initial, retry and follow-on adapter paths for both stations; use
      real reservation transactions and an observed receiver to refuse a request exceeding remaining
      account/project/unit usage allowance under 0036/0062 before any invocation. Falsifier: Bypass the reservation predicate for
      review follow-on calls; the forbidden-call observation must fail.
    falsified_by: >
      Bypass the reservation predicate for review follow-on calls; the forbidden-call observation
      must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Shared eligibility in work, frontier, plan, direct executor, and review. Deliver the normal function needed by the running factory journey.

## Context

W37 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Keep canonical clock uncertainty as a named refusal. 0053 supplies required architecture entry
checks and 0054 exact decision consumption. Existing applicable gate/regression obligations
remain; richer unsupported governance blocks admission rather than being presumed satisfied.
Recheck current inputs after selection and before effects.

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
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC2 exhaustive
concurrent-input/restart and AC4 resource-limit/exposure-recovery matrices moved to Release 2.
Every shared entry, current authority, completion and pre-call caps remain. The criteria,
declared evidence universe, Context and Notes above now carry only the retained function. No
specification status or historical proof was changed.
