---
schema: veldo.spec/v1
id: VELDO-0039
title: Durable dispatch acceptance and launch records
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W24
plan_revision: 3
depends_on: [VELDO-0028, VELDO-0031, VELDO-0036]
placement: [fleet, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_dispatch*.py"
  - ".veldo/control_dispatch*.py"
  - "packs/*/.veldo/control_dispatch*.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "packs/*/.veldo/control_launch*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0039_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0039-durable-dispatch-acceptance.md"
  - "specs/index.md"
  - "proof/VELDO-0039/*"
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
      Claim: Preparation records the complete dispatch contract before invocation and permits one
      active dispatch per unit/station. Set and completeness: Submit a real admitted unit twice
      through the runner; inspect stored source, input, capability, reservation and deadline
      bindings and count launched workers. Falsifier: Spawn before recording the contract; the
      launch-order check must fail.
    falsified_by: >
      Spawn before recording the contract; the launch-order check must fail.
  - id: AC2
    text: >
      Claim: The trusted receiver records launch acceptance under the original dispatch identity.
      Set and completeness: Drive accepted, refused and unknown launch results through the real
      receiver boundary; compare OS process/start identity and stored acceptance, and refuse another
      launch of an unknown attempt. Falsifier: Create a new dispatch for an unknown result; the
      second-launch check must fail.
    falsified_by: >
      Create a new dispatch for an unknown result; the second-launch check must fail.
  - id: AC3
    text: >
      Claim: Prepared, accepted, running and terminal observations update only their bound dispatch.
      Set and completeness: Derive allowed ordinary transitions from the dispatch schema and
      exercise each plus a wrong-dispatch result using real records; terminal output alone cannot
      create landed completion. Falsifier: Apply one worker result to another dispatch; the state-
      binding check must fail.
    falsified_by: >
      Apply one worker result to another dispatch; the state-binding check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Durable dispatch acceptance and launch records. Deliver the normal function needed by the running factory journey.

## Context

W24 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Persist explicit dispatch identity and the accepted contract in the authority before receiver
launch. Use local committed acceptance in Release 1. Ambiguous launch is a stopped original
dispatch, never permission to spawn again.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 1: owner Telegram 28848 moves
recovery/robustness to Release 2. Drop AC2 ambiguous-spawn/restart recovery and AC1/AC3
replication-failure and crash matrices; keep explicit dispatch identity, launch acceptance,
and ordinary state transitions. Removed recovery, durability and failure-matrix obligations
belong to Release 2; additional host/channel/version and full distribution breadth belongs to
Release 4. Normal function and the checks stated above remain Release 1.
