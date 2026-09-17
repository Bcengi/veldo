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
plan_revision: 1
depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0078, VELDO-0079]
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
    Decomposition records identify source system/identity/revision/role, spec alias/UUID, expected
    digest, approved unit set and pending publication.
  metrics: >
    Count allocation conflicts, deduplicated proposals, reserved unpublished aliases and refused
    decomposition growth.
  traces: >
    Join elaboration source to allocation transaction, immutable artifact, published snapshot and
    priority-approved engineering unit.
  error_taxonomy: >
    Distinguish invalid unit ID, source-content conflict, stale spec edit, recycled alias and
    unpublished allocation.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Decomposition binds one primary spec revision and one admitted backlog item per
      engineering unit. Set: control_decomposition proposals and claim.unit_id_problem with
      tasks.task_id_problems as an existing caller of the same rule. Completeness: Derive required
      unit/decomposition fields from A. Exercise additional constraint specs without combining
      authority, duplicate active spec revisions, and revised unit sets after priority. Invoke
      installed claim.unit_id_problem before any unit artifact reservation; rejected identifiers
      create no artifact. New units require fresh prioritization while remaining approved units
      may continue. Falsifier: Reserve a unit artifact before calling claim.unit_id_problem;
      decomposition/invalid-id-no-artifact must detect the reserved invalid key.
    falsified_by: >
      Reserve a unit artifact before calling claim.unit_id_problem;
      decomposition/invalid-id-no-artifact must detect the reserved invalid key.
  - id: AC2
    text: >
      Claim: Concurrent authors use B atomic alias allocation and source mapping, never checkout
      maxima. Set: control_decomposition publication consuming W22 allocation over source system,
      identity, revision and intended artifact role. Completeness: Race real processes in separate
      clones on identical and distinct sources. Require same-source/same-bytes reuse,
      distinct-source unique aliases, immutable digest/version/mapping/publication obligation in
      one transaction, and named conflict or new revision for changed bytes. Include existing
      WARP/VELDO IDs; reserved aliases are never recycled. Falsifier: Allocate aliases from the
      current checkout maximum; decomposition/concurrent-aliases must detect two authors receiving
      the same new alias.
    falsified_by: >
      Allocate aliases from the current checkout maximum; decomposition/concurrent-aliases must
      detect two authors receiving the same new alias.
  - id: AC3
    text: >
      Claim: Allocation and eventual publication form one recoverable operation without exposing
      partial snapshots. Set: control_document materialization and control_decomposition edits
      over immutable spec artifacts and snapshot pointers. Completeness: SIGKILL after
      reservation, artifact write and before/after snapshot switch, then replay original command.
      Require one artifact per source revision/role, recoverable pending publication, exclusive
      creation and atomic declared-version replacement. Stale expected version or digest refuses
      edits; readers see complete old/new snapshots and no admitted unpublished unit. Falsifier:
      Expose the new allocation before switching a complete published snapshot;
      decomposition/partial-publication must detect a reader resolving a missing artifact.
    falsified_by: >
      Expose the new allocation before switching a complete published snapshot;
      decomposition/partial-publication must detect a reader resolving a missing artifact.
required_evidence: [unit, integration]
rollback: >
  Stop decomposition publication, retain reservations and pending obligations, and replay through
  the same source identities after repair.
---

## Intent

Publish concurrent elaboration safely and keep every executable decomposition inside deliberately prioritized scope.

## Context

Package F, W70 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R10/R19, R61 and R73 require atomic source allocation. Misbinding an artifact or unit can execute scope under another request, warranting critical risk. Risk is critical; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

New alias syntax, checkout-based counters and automatic admission of drafted specifications are excluded.

## Notes

D1 blocks allocation transactions and D2 acknowledgment/publication; D4 blocks multi-clone production qualification and D3 inherited launches. Dmitry must name the decomposition approval/priority authority before additional principals approve units. W22 already owns allocation: extend its caller rather than create another counter. control_decomposition needs contracts/fleet mapping and W30 inventory before ready. Record kill barriers and source-to-artifact set equality, preserving reserved holes as evidence rather than tidying the sequence.
