---
schema: veldo.spec/v1
id: VELDO-0017
title: Entity identity and lifecycle schemas
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W2
plan_revision: 1
depends_on: []
placement: [contracts]
protected_paths: []
footprint:
  - ".veldo/validate.py"
  - "engine/.veldo/validate.py"
  - ".veldo/claim.py"
  - "engine/.veldo/claim.py"
  - "engine/.veldo/*contract*.py"
  - "scripts/suites/*"
  - "packs/**/.veldo/*contract*.py"
  - "specs/VELDO-0017-entity-lifecycle-contracts.md"
  - "specs/index.md"
  - "proof/VELDO-0017/*"
behavior_bearing: true
observability:
  logs: No runtime log is introduced by these pure schemas; validation results identify entity type, identity field, ownership relation, or refused state pair.
  metrics: No runtime metric is defined; proof reports coverage of entity schemas, Cartesian lifecycle pairs, ownership cardinalities, and the enumerated historical alias corpus.
  traces: Schema evidence binds the schema version, entity fixture digest, source/destination states, ownership endpoints, and canonical unit-ID validator result.
  error_taxonomy: Distinguish missing identity, conflated scope/concurrency versions, undeclared transition, terminal-history rewrite, duplicate ownership, and invalid unit alias.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every new durable entity has the common identity envelope and immutable provenance, with
      scope revision distinct from concurrency version. Set: Projects, objectives, backlog items,
      admission requests, execution units and attempts, contracts, artifacts, receipts, assignments,
      stations, team configurations, dispatches, decisions, reservations, and release executions.
      Completeness: Register the entire schema universe from the cited design clauses; compare the
      registry to fixtures in both directions, remove each required field in turn, and test
      concurrency updates without changing plan revision and scope changes without alias reuse.
      Falsifier: Use plan revision as the entity concurrency version; the entity-schema/version-
      separation row must fail.
    falsified_by: >
      Use plan revision as the entity concurrency version; the entity-schema/version-separation row
      must fail.
  - id: AC2
    text: >
      Claim: Only declared lifecycle transitions with their entry predicates are legal; terminal
      history cannot be reopened or rewritten. Set: Every source and destination pair in project,
      objective, backlog, execution-unit, assignment, and release-execution state vocabularies,
      including declined, expired, and canceled assignment outcomes. Completeness: Generate the
      Cartesian transition universe from the schema state registry, check every allowed edge with each
      required predicate absent, and require every undeclared edge to refuse; assert registry closure
      against R05, R06, R11, R13, R18, and R65. Falsifier: Permit RAW to transition directly to
      ACTIVE; the lifecycle/backlog-direct-execution row must fail.
    falsified_by: >
      Permit RAW to transition directly to ACTIVE; the lifecycle/backlog-direct-execution row must
      fail.
  - id: AC3
    text: >
      Claim: Ownership cardinality and authorization are preserved through assignment, transfer, and
      retry. Set: Project-to-objective, objective-to-backlog, backlog-to-unit, unit-to-primary-
      specification, actor-to-assignment, and attempt-to-unit relationships. Completeness: Derive
      relationship fixtures from the schema cardinality registry and exercise zero, one, and duplicate
      owners, duplicate active units for one admitted revision, unchanged-scope retry, and
      unauthorized transfer for each applicable relation. Falsifier: Allow a second project to own the
      same execution unit; the ownership/duplicate-project row must fail.
    falsified_by: >
      Allow a second project to own the same execution unit; the ownership/duplicate-project row must
      fail.
  - id: AC4
    text: >
      Claim: Aliases preserve existing identifiers and never become paths or authenticated subjects;
      proposed unit IDs use the installed canonical validator before artifact admission. Set: All
      historical WARP and VELDO specification and plan aliases plus valid and invalid unit IDs
      classified by claim.unit_id_problem. Completeness: Read the historical corpus as a population
      and assert byte-preserved identity for each member without pinning its size; feed the canonical
      validator results into admission fixtures and spy on validation before any artifact write.
      Falsifier: Skip claim.unit_id_problem before unit artifact creation; the identity/canonical-
      unit-validation row must fail.
    falsified_by: >
      Skip claim.unit_id_problem before unit artifact creation; the identity/canonical-unit-validation
      row must fail.
required_evidence: [unit, integration]
rollback: >
  Retain the prior accepted contract and compatible reader. Refuse new project-layer activation
  until corrected contracts are accepted; preserve accepted history and refuse implicit schema
  downgrade. Revert only unactivated contract changes through the ordinary reviewed path.
---

## Intent

**Outcome.** Give every coordination record an unambiguous identity and legal lifecycle before any store or scheduler can persist transitions.

## Context

**Authority.** Package A of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R04-R13, R15-R18, R22, R56, R65, and R73. The later decision-surface ruling in its provenance header takes precedence over retained tracker-only wording.

**Risk.** Identity or transition mistakes can duplicate ownership or make unauthorized execution eligible, so the declared floor is high. No approval is asserted by human_approval: required; this draft must obtain its applicable approval and independent review before implementation or activation.

## Out of scope

**Boundary.** SQLite persistence, transactional alias allocation, runtime project operations, and migration are B, F, and H work. This spec defines executable pure schemas and refusing transitions only.

## Notes

Derive lifecycle pairs from the declared states and historical alias coverage from the repository corpus, without fixed population counts. The canonical unit-ID check must precede artifact admission even in the contract integration fixture. Persistence and concurrent alias allocation remain separate B work; this draft does not reserve runtime identities.
