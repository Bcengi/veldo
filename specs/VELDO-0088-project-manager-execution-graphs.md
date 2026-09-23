---
schema: veldo.spec/v1
id: VELDO-0088
title: Project-manager execution graphs
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W73
plan_revision: 3
depends_on: [VELDO-0035, VELDO-0043, VELDO-0045, VELDO-0060, VELDO-0061, VELDO-0076, VELDO-0078, VELDO-0079, VELDO-0132]
placement: [contracts, loop, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/tasks.py"
  - ".veldo/tasks.py"
  - "packs/*/.veldo/tasks.py"
  - "engine/.veldo/frontier.py"
  - ".veldo/frontier.py"
  - "packs/*/.veldo/frontier.py"
  - "engine/.veldo/control_graph*.py"
  - ".veldo/control_graph*.py"
  - "packs/*/.veldo/control_graph*.py"
  - "engine/.veldo/control_project_cycle*.py"
  - ".veldo/control_project_cycle*.py"
  - "packs/*/.veldo/control_project_cycle*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0088_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0088-project-manager-execution-graphs.md"
  - "specs/index.md"
  - "proof/VELDO-0088/*"
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
      Claim: The PM reads an immutable accepted snapshot and returns proposals under its bounded
      coordination contract. Set and completeness: Run actual LangGraph proposal, no-action and
      failure cycles; enumerate required project/source/watermark/input-version/reservation fields
      and compare every cycle receipt including empty cycles to real store records. Falsifier: Omit
      the no-action cycle receipt; the cycle-accounting check must fail.
    falsified_by: >
      Omit the no-action cycle receipt; the cycle-accounting check must fail.
  - id: AC2
    text: >
      Claim: Nodes can propose but cannot admit, prioritize, assign, dispatch or complete directly.
      Set and completeness: Compare node/output registrations with typed proposal handlers and
      attempt shell/SQL actions, invented roles and store access from a graph process; observe only
      separately validated commands changing domain state. Waiting on a person releases the worker.
      Falsifier: Let a node set priority directly; the unauthorized-transition check must fail.
    falsified_by: >
      Let a node set priority directly; the unauthorized-transition check must fail.
  - id: AC3
    text: >
      Claim: One cycle per project runs, with one bounded follow-up when relevant input arrives
      during it. Set and completeness: Hold an actual PM cycle while an owner answer and worker
      completion arrive; observe one active cycle, one pending follow-up using the new accepted
      snapshot, and no self-triggered loop after inputs are consumed. Apply the finite cycle budget.
      Falsifier: Discard pending input when the active cycle ends; the expected-follow-up
      observation must fail.
    falsified_by: >
      Discard pending input when the active cycle ends; the expected-follow-up observation must
      fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Project-manager execution graphs. Deliver the normal function needed by the running factory journey.

## Context

W73 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Use the actual installed nonpersistent LangGraph step runtime and Veldo-owned workflow
definition. This item brings 0093 ordinary cycle scheduling forward: at most one cycle per
project and one bounded follow-up for pending relevant input. Checkpoint recovery and broad
replacement equivalence remain Release 2.

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
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC3
retry/cancellation/replacement-adapter matrix moved to Release 2. Actual PM execution remains;
ordinary serialized scheduling and one pending-input follow-up move forward from 0093. The
criteria, declared evidence universe, Context and Notes above now carry only the retained
function. No specification status or historical proof was changed.
