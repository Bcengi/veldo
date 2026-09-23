---
schema: veldo.spec/v1
id: VELDO-0031
title: Authority-backed claims and claim-generation fencing
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W16
plan_revision: 3
depends_on: [VELDO-0023, VELDO-0025, VELDO-0029, VELDO-0107]
placement: [fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/claim.py"
  - ".veldo/claim.py"
  - "packs/*/.veldo/claim.py"
  - "engine/.veldo/control_claim*.py"
  - ".veldo/control_claim*.py"
  - "packs/*/.veldo/control_claim*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0031_*.py"
  - "scripts/check_teeth_mutations.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0031-authority-backed-claims.md"
  - "specs/index.md"
  - "proof/VELDO-0031/*"
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
      Claim: Claim ownership, unit activation and first-unit backlog activation commit together. Set
      and completeness: Race two real clone clients for one admitted unit; enumerate claim and
      activation entries and inspect one owner and coherent unit/backlog state in SQLite, with no
      clone-local ledger writes. Reject invalid aliases before artifacts. Falsifier: Write ownership
      without the corresponding unit transition; the stored-state consistency check must fail.
    falsified_by: >
      Write ownership without the corresponding unit transition; the stored-state consistency check
      must fail.
  - id: AC2
    text: >
      Claim: Renew, release and protected use require the currently stored owner and claim
      generation. Set and completeness: Exercise each operation with current and mismatched
      holder/generation in the real store and receiver; a non-owner cannot release or use the claim.
      Falsifier: Ignore the claim generation on protected use; the stale-generation request must
      reach the receiver and fail the check.
    falsified_by: >
      Ignore the claim generation on protected use; the stale-generation request must reach the
      receiver and fail the check.
  - id: AC3
    text: >
      Claim: Uncertain ownership refuses admission and exposes a named stop without takeover. Set
      and completeness: Present known owned, unowned and uncertain claim states to claim and landing
      callers, including the existing unanswerable detector result; inspect holder and local/remote
      refs. Falsifier: Map an unanswerable claim result to ordinary contention and retry; the stop
      and unchanged-ref observation must fail.
    falsified_by: >
      Map an unanswerable claim result to ordinary contention and retry; the stop and unchanged-ref
      observation must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Authority-backed claims and claim-generation fencing. Deliver the normal function needed by the running factory journey.

## Context

W16 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Use the installed claim.unit_id_problem before artifacts and VELDO-0015 for existing clock
stand-down. No automatic reclaim is in Release 1. Local claim commands must use the real
authority store, not a clone ledger.

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
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC1 lost-reply
crash proof, AC2 takeover fencing and AC3 reclaim/clock/receiver matrix moved to Release 2.
Current-holder checks and uncertainty stop remain. The criteria, declared evidence universe,
Context and Notes above now carry only the retained function. No specification status or
historical proof was changed.

2026-09-22 implementation: registered the Release 1 claim suite and its prerequisite closure
in scripts/suites/manifest.json and requires.json, with six driven negative controls in the
existing scripts/check_teeth_mutations.py registry. Runtime changes remain within the declared
claim and scaffold footprint. The proof README records the accepted-admission and receiver seams
consumed ahead of the service-runner and exact-publication items on parallel branches.
