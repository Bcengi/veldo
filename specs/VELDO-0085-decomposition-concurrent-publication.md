---
schema: veldo.spec/v1
id: VELDO-0085
title: Decomposition and concurrent elaboration publication
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W70
plan_revision: 3
depends_on: [VELDO-0037, VELDO-0078, VELDO-0079]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/claim.py"
  - ".veldo/claim.py"
  - "packs/*/.veldo/claim.py"
  - "engine/.veldo/tasks.py"
  - ".veldo/tasks.py"
  - "packs/*/.veldo/tasks.py"
  - "engine/.veldo/control_decomposition*.py"
  - ".veldo/control_decomposition*.py"
  - "packs/*/.veldo/control_decomposition*.py"
  - "engine/.veldo/control_alias*.py"
  - ".veldo/control_alias*.py"
  - "packs/*/.veldo/control_alias*.py"
  - "engine/.veldo/control_document*.py"
  - ".veldo/control_document*.py"
  - "packs/*/.veldo/control_document*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0085_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0085-decomposition-concurrent-publication.md"
  - "specs/index.md"
  - "proof/VELDO-0085/*"
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
      Claim: Decomposition binds one primary specification revision and one admitted backlog item
      per unit. Set and completeness: Enumerate required unit fields, invoke claim.unit_id_problem
      before artifacts and reject invalid IDs, duplicate active spec revisions or authority combined
      across backlog items. New units need fresh priority. Falsifier: Reserve an artifact before
      unit-ID validation; the invalid-ID-no-artifact check must fail.
    falsified_by: >
      Reserve an artifact before unit-ID validation; the invalid-ID-no-artifact check must fail.
  - id: AC2
    text: >
      Claim: Each accepted decomposition artifact uses authority allocation and its source
      revision/role. Set and completeness: Publish identical and distinct source tuples through 0037
      in real SQLite; compare alias reuse, unique distinct aliases and exact source-to-spec mapping,
      preserving existing WARP and VELDO identities. Falsifier: Allocate the alias from checkout
      maximum; the authority-counter comparison must fail.
    falsified_by: >
      Allocate the alias from checkout maximum; the authority-counter comparison must fail.
  - id: AC3
    text: >
      Claim: Published specifications have the accepted complete bytes and declared dependencies.
      Set and completeness: Read the materialized files in another process and compare versions,
      digests, unit ownership and dependency edges; a stale edit or unpublished document cannot
      become admitted execution input. Falsifier: Omit a generated dependency when publishing its
      spec; the decomposition-to-eligibility comparison must fail.
    falsified_by: >
      Omit a generated dependency when publishing its spec; the decomposition-to-eligibility
      comparison must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Decomposition and concurrent elaboration publication. Deliver the normal function needed by the running factory journey.

## Context

W70 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

0037 owns the only alias counter and source mapping. This consumer publishes the PM
decomposition as actual specifications, with dependencies delivered to 0052/0092. Preserve
contract-named scope and one owning backlog item per unit.

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
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC2 multi-
clone/concurrent-author and AC3 crash/snapshot recovery matrices moved to Release 2. Approved
decomposition and actual specification/dependency publication remain. The criteria, declared
evidence universe, Context and Notes above now carry only the retained function. No
specification status or historical proof was changed.
