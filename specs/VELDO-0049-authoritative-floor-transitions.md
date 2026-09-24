---
schema: veldo.spec/v1
id: VELDO-0049
title: Dispatch and tracker bridge consume authoritative state transitions
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W34
plan_revision: 3
depends_on: [VELDO-0031, VELDO-0035, VELDO-0039]
placement: [fleet, tracker, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/dispatch.py"
  - ".veldo/dispatch.py"
  - "packs/*/.veldo/dispatch.py"
  - "engine/.veldo/tracker_bridge.py"
  - ".veldo/tracker_bridge.py"
  - "packs/*/.veldo/tracker_bridge.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0049_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0049-authoritative-floor-transitions.md"
  - "specs/index.md"
  - "proof/VELDO-0049/*"
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
      Claim: Build acceptance is authoritative and only the materializer writes enrolled status
      projections. Set and completeness: Enumerate dispatch status-write sites and run build
      success, red gate and invalid proof through real files/store/gate; only accepted proof
      produces the review handoff and projection. Falsifier: Write a review status directly without
      accepted proof; the authority-to-projection check must fail.
    falsified_by: >
      Write a review status directly without accepted proof; the authority-to-projection check must
      fail.
  - id: AC2
    text: >
      Claim: Review uses a separate eligible principal and fresh context bound to exact source and
      proof. Set and completeness: Run separate builder/reviewer processes; exercise self-review,
      wrong source/proof, missing receipt and valid independent review. Check applicable policy
      count and identity against signed assignment and review records. Falsifier: Accept the builder
      as its own reviewer; the independence check must fail.
    falsified_by: >
      Accept the builder as its own reviewer; the independence check must fail.
  - id: AC3
    text: >
      Claim: A pass cannot erase an unresolved blocking finding or establish source completion. Set
      and completeness: Present a blocking finding followed by a pass, rejected approval and a valid
      explicit finding disposition; inspect allowed handoff and unchanged trunk on rejection. Only
      the lander may establish completion. Falsifier: Let a later pass discard an unresolved
      finding; the publication-refusal check must fail.
    falsified_by: >
      Let a later pass discard an unresolved finding; the publication-refusal check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Dispatch and tracker bridge consume authoritative state transitions. Deliver the normal function needed by the running factory journey.

## Context

W34 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## What the reviewer judges

- Normal use: the dispatcher moves an enrolled unit from build to review to handoff only through the
  authority's transitions; a build is accepted only with accepted proof and a green gate; review runs as a
  separate eligible principal in a fresh context bound to the exact source and proof; a pass cannot clear
  an unresolved blocking finding; only the lander establishes completion.
- Threat model: a builder that reviews its own work or claims review, a stale or wrong proof or source, a
  later pass that tries to erase an earlier blocking finding, and a direct status write that skips the
  authority. The owner's account, the store and the gate are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); Jira tracker
  intake (dropped by the owner, 28857 and 28859); crash recovery between transitions (Release 2); forged
  rows in our own store.

## Notes

Dispatcher._dispatch_build/_set_status and _dispatch_review/_verdict_passes use authority
transitions and retained engineering-review policy. Tracker drafting/promotion paths are
disabled for enrolled factory work; Telegram/API intake is a separate concern.
LiveLoop/LiveReviewer adapter wiring is separately specified.

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
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC1 projection
crash/replay races moved to Release 2; AC3 tracker drafting/promotion integration is dropped
by 28857/28859. Authoritative transitions and independent review remain. The criteria,
declared evidence universe, Context and Notes above now carry only the retained function. No
specification status or historical proof was changed.
