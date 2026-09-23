---
schema: veldo.spec/v1
id: VELDO-0050
title: Executor persists proof and performs complete contextual validation
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W35
plan_revision: 3
depends_on: [VELDO-0035, VELDO-0049]
placement: [distribution, loop, contracts, metrics]
protected_paths: []
footprint:
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/executor.py"
  - ".veldo/executor.py"
  - "packs/*/.veldo/executor.py"
  - "engine/.veldo/validate.py"
  - ".veldo/validate.py"
  - "packs/*/.veldo/validate.py"
  - "engine/.veldo/control_proof*.py"
  - ".veldo/control_proof*.py"
  - "packs/*/.veldo/control_proof*.py"
  - "scripts/suites/*_veldo_0050_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0050-durable-contextual-proof.md"
  - "specs/index.md"
  - "proof/VELDO-0050/*"
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
      Claim: Proof is stored as accepted immutable evidence before built or review is offered. Set
      and completeness: Run the actual builder, end its process, and resolve its complete proof
      bundle from a fresh reviewer without builder memory or temporary files; compare artifact
      digests and implementation/spec identity. Falsifier: Keep the manifest only in temporary
      validation storage; the fresh reviewer must fail to resolve it.
    falsified_by: >
      Keep the manifest only in temporary validation storage; the fresh reviewer must fail to
      resolve it.
  - id: AC2
    text: >
      Claim: Proof validation covers the complete accepted specification and required evidence. Set
      and completeness: Derive criterion/evidence/check sets from the accepted spec and installed
      catalog; invoke contextual validation with empty, omitted, duplicate and invented mappings,
      nonexistent commit, wrong spec revision, missing producer/observation, wrong digest and
      missing evidence. Each must refuse. Falsifier: Use check_json alone for an empty-criteria
      proof naming a nonexistent commit; the contextual-validation check must fail.
    falsified_by: >
      Use check_json alone for an empty-criteria proof naming a nonexistent commit; the contextual-
      validation check must fail.
  - id: AC3
    text: >
      Claim: Proof records actual trusted checks and never defaults missing build checks to passed.
      Set and completeness: Run the real canonical gate with green, red and missing-terminal-output
      cases; compare every required catalog check to captured output, exit and Evidence Service
      observations. Missing or altered observations refuse review. Falsifier: Insert a default
      passed unit check when observations are absent; the no-default-success check must fail.
    falsified_by: >
      Insert a default passed unit check when observations are absent; the no-default-success check
      must fail.
  - id: AC4
    text: >
      Claim: Executor proof and review observations go to their owning services, while build-only
      leaves landing receipts absent. Set and completeness: Drive build-only and full review paths
      through real events.emit restrictions and the journal; compare producer ownership and read
      completion from a new process. Falsifier: Emit verdict.recorded directly from the executor;
      the owning-service check must fail.
    falsified_by: >
      Emit verdict.recorded directly from the executor; the owning-service check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Executor persists proof and performs complete contextual validation. Deliver the normal function needed by the running factory journey.

## Context

W35 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Preserve implementation commit, proof artifact/evidence commit and final candidate as distinct
subjects. VELDO-0051 owns journal projection; neither the executor nor a signed reviewer
assertion can manufacture completion. Required checks and contextual proof coverage remain
intact.

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
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC1 every-
write-barrier crash recovery and AC4 projection replay moved to Release 2. Fresh-reviewer
proof access, contextual coverage, actual checks and build-only distinction remain. The
criteria, declared evidence universe, Context and Notes above now carry only the retained
function. No specification status or historical proof was changed.
