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
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023]
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
    Allocation results identify repository, source tuple, alias, artifact digest, expected
    version, and pending publication.
  metrics: >
    Count fresh allocations, identical retries, content conflicts, unrecycled reservations, and
    unfinished document publications.
  traces: >
    Join source-system identity and revision to counter transaction, immutable artifact,
    publication obligation, and materialized version.
  error_taxonomy: >
    Distinguish invalid unit alias, source-content conflict, stale edit, exclusive-create
    collision, and publication pending.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A per-repository transactional counter and uniqueness constraint allocate new VELDO
      aliases without changing historical WARP or VELDO identities. Set: Separate drafting
      processes requesting aliases through control.sqlite3, including identical
      source-system/source-ID/source-revision/artifact-role tuples. Completeness: Race identical
      and distinct sources, corrupt a proposed unit ID, and SIGKILL after counter commit before
      response. Require one alias for an identical proposal, distinct aliases for distinct
      accepted sources, no recycled reservation, and claim.unit_id_problem before any unit
      artifact reservation. Falsifier: Allocate from each checkout maximum instead of the store
      counter and race two authors; aliases/concurrent-allocation must detect duplicate aliases.
    falsified_by: >
      Allocate from each checkout maximum instead of the store counter and race two authors;
      aliases/concurrent-allocation must detect duplicate aliases.
  - id: AC2
    text: >
      Claim: Changed source content and edits compare expected version and artifact digest,
      returning a new revision or named conflict instead of overwriting an accepted document. Set:
      Real command and filesystem clients editing the same accepted specification or repeating a
      source tuple with altered bytes. Completeness: Execute both writer orders against one
      version, record winning bytes and journal results, and retry after process restart. Require
      identical retries to return their original allocation and changed content to preserve the
      prior artifact and rejected proposal evidence. Falsifier: Ignore the expected digest and
      race an edited document against a newer accepted revision; aliases/stale-edit must reject
      the overwrite.
    falsified_by: >
      Ignore the expected digest and race an edited document against a newer accepted revision;
      aliases/stale-edit must reject the overwrite.
  - id: AC3
    text: >
      Claim: Allocation, artifact identity, source mapping, and publication obligation commit
      together; subsequent materialization exposes only complete published versions. Set: Real
      SQLite allocation and exclusive file creation or atomic version replacement in specs
      projections, with concurrent snapshot readers. Completeness: SIGKILL after allocation,
      during temporary-file write, and after rename before publication acknowledgement. Restart
      the materializer and verify same alias, exact accepted bytes, no overwrite of another
      author, and published-only reader visibility at each boundary. Falsifier: Mark publication
      complete before atomic replacement and kill the writer with a partial temporary file;
      aliases/publication-window must detect incomplete reader content.
    falsified_by: >
      Mark publication complete before atomic replacement and kill the writer with a partial
      temporary file; aliases/publication-window must detect incomplete reader content.
required_evidence: [unit, integration]
rollback: >
  Pause allocation and materialization, retain counter reservations and source mappings, and
  resume pending publication without recycling any identifier.
---

## Intent

Allocate one durable specification alias per source revision and publish its accepted document without races or overwrites.

## Context

Package B, W22 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R10, R19, R22, R57, R73. Package A supplies the accepted contracts; this draft grants no implementation or activation authority.

The high risk floor reflects the consequences of failure in this boundary. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

Automatic admission of drafted specifications and project elaboration workflows are excluded.

## Notes

D1 blocks allocation persistence through W8, and D2 governs when the snapshot may be exposed as published. The source tuple includes intended artifact role; two outputs from one source are not accidentally collapsed. Static IDs in this plan were expressly allocated during drafting, but runtime authors must never scan a checkout maximum. The materializer consumes W20 snapshot semantics without changing the plan dependency list.

