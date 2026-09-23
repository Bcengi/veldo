---
schema: veldo.spec/v1
id: VELDO-0037
title: Atomic specification alias allocation and document publication
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W22
plan_revision: 3
depends_on: [VELDO-0023, VELDO-0035]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_alias*.py"
  - ".veldo/control_alias*.py"
  - "packs/*/.veldo/control_alias*.py"
  - "engine/.veldo/control_document*.py"
  - ".veldo/control_document*.py"
  - "packs/*/.veldo/control_document*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0037_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0037-specification-alias-publication.md"
  - "specs/index.md"
  - "proof/VELDO-0037/*"
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
      Claim: Authority allocation gives unique VELDO aliases and preserves historical IDs. Set and
      completeness: Use real counter/uniqueness constraints with identical and distinct source-
      system/ID/revision/role tuples; inspect same-source reuse, distinct-source allocation and no
      reserved alias recycling. Reject invalid unit IDs through claim.unit_id_problem before
      artifacts. Falsifier: Allocate from checkout maximum instead of the store counter; independent
      requests with stale checkouts must collide and fail the check.
    falsified_by: >
      Allocate from checkout maximum instead of the store counter; independent requests with stale
      checkouts must collide and fail the check.
  - id: AC2
    text: >
      Claim: Edits compare expected version and artifact digest before replacing accepted content.
      Set and completeness: Submit current, stale and changed-content requests against real accepted
      documents; require a new version or named conflict with prior bytes preserved, and identical
      request reuse of its allocation. Falsifier: Ignore expected digest on an edit; the stale-
      overwrite check must fail.
    falsified_by: >
      Ignore expected digest on an edit; the stale-overwrite check must fail.
  - id: AC3
    text: >
      Claim: Source mapping, allocation and accepted document identity commit together and
      materialize exact bytes. Set and completeness: Publish each enabled artifact role through real
      store/filesystem operations; compare source tuple, alias, version, digest and reader-visible
      complete document against the accepted record. Falsifier: Publish altered bytes under the
      accepted digest; the document comparison must fail.
    falsified_by: >
      Publish altered bytes under the accepted digest; the document comparison must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Atomic specification alias allocation and document publication. Deliver the normal function needed by the running factory journey.

## Context

W22 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Use the authority counter, never a runtime checkout maximum. Source identity includes intended
artifact role, so one source can produce distinct specifications and other artifacts. 0035
supplies accepted snapshots and ordinary materialization; local commit is sufficient under
amended C3.

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
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC1/AC2
concurrency/restart matrices and AC3 interrupted materialization moved to Release 2. Unique
counter/source mapping, version checks and exact published bytes remain. The criteria,
declared evidence universe, Context and Notes above now carry only the retained function. No
specification status or historical proof was changed.
