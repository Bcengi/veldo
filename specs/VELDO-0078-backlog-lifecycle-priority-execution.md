---
schema: veldo.spec/v1
id: VELDO-0078
title: Backlog lifecycle and priority-controlled execution
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W63
plan_revision: 3
depends_on: [VELDO-0052, VELDO-0076, VELDO-0077]
placement: [contracts, fleet, distribution]
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
  - "engine/.veldo/claim.py"
  - ".veldo/claim.py"
  - "packs/*/.veldo/claim.py"
  - "engine/.veldo/control_backlog*.py"
  - ".veldo/control_backlog*.py"
  - "packs/*/.veldo/control_backlog*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0078_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0078-backlog-lifecycle-priority-execution.md"
  - "specs/index.md"
  - "proof/VELDO-0078/*"
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
      Claim: Only prioritized admitted work can create eligible engineering units. Set and
      completeness: Drive the ordinary path and direct claim entries with intake-only, prepared,
      admitted-without-priority and prioritized work; inspect real store/claim results and reject
      any executable unit without accepted admission and priority. Falsifier: Allow tasks.claim_task
      for admitted but unprioritized work; the missing-priority check must fail.
    falsified_by: >
      Allow tasks.claim_task for admitted but unprioritized work; the missing-priority check must
      fail.
  - id: AC2
    text: >
      Claim: First claim activates the item and follows only its approved decomposition. Set and
      completeness: Claim a real approved unit and inspect coherent owner/item activation; append
      another proposed unit and require fresh prioritization for it while existing approved units
      may continue. Falsifier: Make an appended unit executable without renewed prioritization; the
      decomposition-growth check must fail.
    falsified_by: >
      Make an appended unit executable without renewed prioritization; the decomposition-growth
      check must fail.
  - id: AC3
    text: >
      Claim: A clean blocked phase resumes only after its binding is resolved and DONE requires
      accepted unit outcomes. Set and completeness: Record interrupted phase/reason, settle its
      actual owner decision and resume that phase. Attempt DONE with path-only output, canceled
      attempt and missing required unit receipt; only complete receipts or an authorized alternative
      outcome suffice. Falsifier: Use output-file existence as DONE; the missing-outcome check must
      fail.
    falsified_by: >
      Use output-file existence as DONE; the missing-outcome check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Backlog lifecycle and priority-controlled execution. Deliver the normal function needed by the running factory journey.

## Context

W63 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

The regular path is proposed/prepared, awaiting grooming, admitted, prioritized, active,
optionally blocked, and done or canceled. Unsupported advanced work classes remain non-
executable. Use the existing unit-ID validator and current owner/admission policy.

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
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC1 exhaustive
state-pair qualification moved to Release 3 with advanced backlog states; AC2 crash/replay
races moved to Release 2. Priority, approved decomposition, clean blocked resumption and
evidence-based DONE remain. The criteria, declared evidence universe, Context and Notes above
now carry only the retained function. No specification status or historical proof was changed.
