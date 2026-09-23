---
schema: veldo.spec/v1
id: VELDO-0035
title: Complete read-set validation and authoritative snapshots
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W20
plan_revision: 3
depends_on: [VELDO-0023, VELDO-0025]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_snapshot*.py"
  - ".veldo/control_snapshot*.py"
  - "packs/*/.veldo/control_snapshot*.py"
  - "engine/.veldo/control_readset*.py"
  - ".veldo/control_readset*.py"
  - "packs/*/.veldo/control_readset*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0035_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0035-authoritative-snapshots.md"
  - "specs/index.md"
  - "proof/VELDO-0035/*"
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
      Claim: A command validates the versions and digests of all inputs it consumed before
      committing. Set and completeness: Enumerate inputs in each enabled command registration,
      including dependency collections and absence of blockers; use a real stored snapshot, change a
      dependency or authority input, and require a named stale-input refusal. Falsifier: Check only
      project version after a dependency changes; the stale-input command must incorrectly commit
      and fail the check.
    falsified_by: >
      Check only project version after a dependency changes; the stale-input command must
      incorrectly commit and fail the check.
  - id: AC2
    text: >
      Claim: Snapshots identify domain, repository, accepted commit, journal watermark and input
      versions/digests. Set and completeness: Read each registered journey input from accepted real
      artifacts; edit checkout bytes and remove a referenced artifact. Require the accepted bytes or
      explicit refusal, never mutable-path substitution. Falsifier: Read edited checkout bytes
      instead of the accepted artifact; the digest comparison must fail.
    falsified_by: >
      Read edited checkout bytes instead of the accepted artifact; the digest comparison must fail.
  - id: AC3
    text: >
      Claim: The materializer publishes accepted document and status bytes at an explicit watermark.
      Set and completeness: Enumerate the enabled document/status projections, materialize one
      complete accepted revision, and read it from another process; compare every member digest and
      watermark with the store. Falsifier: Publish a status projection from unaccepted working
      bytes; the reader-to-store comparison must fail.
    falsified_by: >
      Publish a status projection from unaccepted working bytes; the reader-to-store comparison must
      fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Complete read-set validation and authoritative snapshots. Deliver the normal function needed by the running factory journey.

## Context

W20 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Accepted snapshots supply 0052 eligibility and 0088/0092 proposals; 0037 and 0049 use ordinary
materialization. Local committed watermarks are sufficient under amended C3. The MVP checks
current inputs transactionally without claiming every concurrent negative-read interleaving.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 1: owner Telegram 28848 moves
recovery/robustness to Release 2. AC1 exhaustive concurrent complete-read-set qualification
and AC3 crash-safe pointer switching, interrupted publication and recovery move to Release 2;
accepted snapshots and ordinary materialization remain.
