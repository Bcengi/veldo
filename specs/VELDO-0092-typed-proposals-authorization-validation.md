---
schema: veldo.spec/v1
id: VELDO-0092
title: Typed proposals and complete authorization validation
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W77
plan_revision: 4
depends_on: [VELDO-0035, VELDO-0052, VELDO-0054, VELDO-0069, VELDO-0078, VELDO-0085, VELDO-0089, VELDO-0091]
placement: [contracts, engine, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/frontier.py"
  - ".veldo/frontier.py"
  - "packs/*/.veldo/frontier.py"
  - "engine/.veldo/control_proposal*.py"
  - ".veldo/control_proposal*.py"
  - "packs/*/.veldo/control_proposal*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0092_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0092-typed-proposals-authorization-validation.md"
  - "specs/index.md"
  - "proof/VELDO-0092/*"
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
      Claim: Only registered typed proposals with complete identity, expected versions and authority
      enter validation. Set and completeness: Compare action schema/handler registrations in both
      directions and omit target, version, evidence, transition, authority or idempotency key;
      shell, SQL and invented types must refuse before effects. Falsifier: Accept shell text as a
      generic executable proposal; the typed-only check must fail.
    falsified_by: >
      Accept shell text as a generic executable proposal; the typed-only check must fail.
  - id: AC2
    text: >
      Claim: Commit validates current schema, identity, authority, scope, dependencies, decisions,
      roster, independence, budget and lifecycle. Set and completeness: Derive applicable inputs
      from enabled handlers, mutate each predicate in ordinary real-store requests and insert a
      blocking dependency with unchanged project version; inspect named refusal before assignment,
      dispatch or publication. Falsifier: Validate only project version after inserting a
      dependency; the stale-proposal check must fail.
    falsified_by: >
      Validate only project version after inserting a dependency; the stale-proposal check must
      fail.
  - id: AC3
    text: >
      Claim: A declared atomic group commits all accepted actions together or none, under stable
      action identities. Set and completeness: Submit a valid group, a group with one invalid
      action, an unchanged duplicate and changed content under the same identity to real store
      transactions; inspect complete result, zero partial effects and explicit conflict. Falsifier:
      Commit the first action before validating the remaining group; the partial-group check must
      fail.
    falsified_by: >
      Commit the first action before validating the remaining group; the partial-group check must
      fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Typed proposals and complete authorization validation. Deliver the normal function needed by the running factory journey.

## Context

W77 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Use complete current authorization inputs from accepted snapshots, including dependency
collections and exact decision settlements. Unsupported governing obligations block. Domain
commands commit declared atomic groups; graph output, confidence and objective acceptance
cannot supply missing authority.

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
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC2 exhaustive
concurrent read-set insertion and AC3 kill/lost-ack/replica qualification moved to Release 2.
Typed current-authorized actions, dependency checks and all-or-nothing groups remain. The
criteria, declared evidence universe, Context and Notes above now carry only the retained
function. No specification status or historical proof was changed.
