---
schema: veldo.spec/v1
id: VELDO-0092
title: Typed proposals and complete authorization validation
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W77
plan_revision: 1
depends_on: [VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0088, VELDO-0089, VELDO-0091]
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
    Proposal results name cycle/logical action, target versions, complete read set, atomic group,
    authority predicate and committed result or refusal.
  metrics: >
    Count per-predicate refusals, stale negative reads, replayed actions and rejected atomic
    groups.
  traces: >
    Trace typed graph output through deterministic validation, store commit, replication and
    stable results returned to the adapter.
  error_taxonomy: >
    Distinguish malformed action, scope escalation, missing decision, stale graph/roster,
    insufficient budget and idempotency conflict.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Only typed proposals with complete identities, versions and authority requirements
      enter validation. Set: control_proposal schemas consumed by authorization.is_authorized and
      request.validate_record for every registered R30 action. Completeness: Require action
      registry/schema/handler equality. Omit target, expected version, evidence, intended
      transition, authority or idempotency key one at a time; submit shell commands, SQL and
      invented action types. Reject before effects. Model confidence, roster labels and objective
      acceptance cannot supply missing admission or priority authority. Falsifier: Allow a
      shell-command proposal as a generic action; proposals/typed-only must detect an executable
      untyped proposal.
    falsified_by: >
      Allow a shell-command proposal as a generic action; proposals/typed-only must detect an
      executable untyped proposal.
  - id: AC2
    text: >
      Claim: Veldo validates the entire authorization and read set at commit, including absence
      predicates. Set: control_proposal commit and C shared eligibility/frontier consumers across
      schema, identity, authorization, scope, dependency closure, unresolved decisions, roster,
      separation of duties, budget and lifecycle. Completeness: Compare every predicate and R70
      input class to independent failure rows. Hold project version fixed while changing spec,
      plan, release, decision, floor, policy, membership, admission, graph, roster, reservation or
      receipt; insert a new blocker into a previously empty collection. Race real owner/service
      commands during the model cycle and require named refusal before commit. Falsifier: Validate
      only project version while ignoring a newly inserted blocking decision;
      proposals/negative-read-staleness must detect a committed stale action.
    falsified_by: >
      Validate only project version while ignoring a newly inserted blocking decision;
      proposals/negative-read-staleness must detect a committed stale action.
  - id: AC3
    text: >
      Claim: Declared atomic groups commit completely or not at all, and graph retries reuse
      stable action identities. Set: B store transactions for control_proposal groups and
      independent group results under one cycle. Completeness: Use real concurrent processes and
      kill barriers at each action write, commit and reply. Inject an invalid action into a
      multi-action group and require zero group effects; separate valid groups receive their own
      result. Replay identical cycle/logical operations after lost acknowledgment and require
      prior results; changed payload under the same identity conflicts. D2 pending export cannot
      be reported as success. Falsifier: Commit the first action before validating the rest of its
      atomic group; proposals/group-atomicity must detect a partial accepted group.
    falsified_by: >
      Commit the first action before validating the rest of its atomic group;
      proposals/group-atomicity must detect a partial accepted group.
required_evidence: [unit, integration]
rollback: >
  Stop proposal commits, preserve original cycle/action identities and results, and replay only
  after current validation is restored.
---

## Intent

Turn project-manager output into auditable Veldo transitions only after complete deterministic authorization.

## Context

Package G, W77 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R29/R30, R62 and R70 define the trust boundary between reasoning and authority. This validator can grant execution and therefore has critical risk. Risk is critical; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

A second policy engine, direct database access for models and changing admission decisions inside a proposal are excluded.

## Notes

D1 blocks atomic groups/read sets and D2 their acknowledged results; D3/D4 remain inherited dispatch prerequisites. Dmitry must supply any named authority binding a proposal requires; absent product rulings are explicit unresolved decisions. Administrative actions must reuse B full canonical command-digest verification, including operation, target and every parameter. Map control_proposal to contracts/engine/fleet and inventory its installed entry points before ready. Keep each rejected predicate row and partial-group crash observation for fresh-context review.
