---
schema: veldo.spec/v1
id: VELDO-0151
title: A team may name specialist roles beyond the four required ones, and every role names its capability configuration and its kind
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W111
plan_revision: 4
depends_on: [VELDO-0089, VELDO-0127]
placement: [contracts, engine, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_team*.py"
  - ".veldo/control_team*.py"
  - "packs/*/.veldo/control_team*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0151_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0151-specialist-roles-with-capability-configurations.md"
  - "specs/index.md"
  - "proof/VELDO-0151/*"
behavior_bearing: true
observability:
  logs: >
    Record each team revision with its roles, each role's kind and capability configuration reference,
    and each staffing request opened for a missing or unresolvable role, without secrets.
  metrics: >
    Count team revisions accepted and refused, specialist roles per team and staffing requests by reason.
  traces: >
    Join each role to the capability configuration revision it names and each assignment to the team
    revision and role it staffed.
  error_taxonomy: >
    Distinguish a missing required role, a role with no capability configuration reference, a reference
    that resolves to no accepted configuration, an unknown kind and a staffing choice naming a role the
    team does not have; none invents a worker.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Versioned team data may name specialist roles beyond the four required ones, and every role
      carries a capability configuration reference and a kind, required or specialist. Set and
      completeness: Compare the team schema's role fields with VELDO-0089's plus `capability_configuration`
      and `kind`, for a team with the four required roles alone and one that adds specialist roles such as
      `designer`, `ios_builder` or `builder_jira`. The four required roles are of kind `required` and every
      other role of kind `specialist`. A role with no capability configuration reference, one whose
      reference resolves to no accepted VELDO-0127 configuration, and a role with another kind each
      produce an owner request, never an invented worker, and the team revision is not accepted.
      Falsifier: Accept a role that names no capability configuration; the missing-reference row must
      fail.
    falsified_by: >
      Accept a role that names no capability configuration; the missing-reference row must fail.
  - id: AC2
    text: >
      Claim: A staffing choice names roles, and a specialist the team does not have becomes a staffing
      request to the owner, never an invented worker. Set and completeness: Assign a unit from a staffing
      choice that names a specialist role the team has, and one that names a specialist role it does not
      have; the first binds the current team revision, the role and its capability configuration
      reference under the applicable VELDO-0049 review policy, and the second opens one staffing request
      to the project's current owner and assigns nothing. Falsifier: Assign a worker for a specialist role
      the team does not have; the staffing-request row must fail.
    falsified_by: >
      Assign a worker for a specialist role the team does not have; the staffing-request row must fail.
required_evidence: [unit, integration]
rollback: >
  Accept only the four required roles, as VELDO-0089 did; team revisions, assignments and staffing
  requests are kept. No automatic rollback is authorized.
---

## Intent

A project manager decides which specialists a piece of work needs, so a team must be able to name roles
beyond the four every team has, and each role must say which capability configuration its workers run
with.

## Context

W111 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. Section 4 of the
approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner Telegram
29162) amends VELDO-0089 AC1 to allow specialist roles, each with a capability configuration reference
and a kind. VELDO-0089 has landed with its proof, so this repository's convention puts that amendment in
its own specification that depends on it, and VELDO-0089 keeps its landed text. Today the team schema is
closed to the four required role names (`REQUIRED_ROLES` in `.veldo/control_team.py`).

## Out of scope

Choosing a specialist by expertise, engine, host capability and independence (VELDO-0090); the
capability configurations themselves (VELDO-0127); any change to VELDO-0089's criteria.

## What the reviewer judges

- Normal use: the owner sets a project's team as versioned data, the four required roles plus any
  specialist roles, each naming its capability configuration; the PM's staffing choice names roles, and
  assignments bind the current team revision, the role and its configuration reference.
- Threat model: a role accepted with no capability configuration reference, or one that resolves to
  nothing; a specialist role treated as required or the reverse; a worker invented for a role the team
  does not have; a roster entry that grants admission rights. The owner's account, the store and the
  signing edge are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); amendment
  races and mid-cycle changes (Release 2); adversarial decision review depth (Release 3); forged rows in
  our own store and files planted in the installed directory.

## Notes

A role's tools and MCP servers still come only from VELDO-0127's versioned capability configuration,
which each role names by its `capability_configuration` reference; the team schema has no tool
restrictions or second capability filter. VELDO-0089's owner amendments, staffing requests and
review-policy bindings are consumed as they are. The thin VELDO-0088 of stage 2 of the design's critical
path stages one unit with the four required roles through these references.

## History

2026-09-25: written for PLAN-0019 revision 4 from the approved operating-model design (Telegram 29162),
section 4(e), whose VELDO-0089 AC1 amendment is carried here whole because VELDO-0089 has landed. AC1 is
that amendment with its own falsifier; AC2 is the design's rule that a missing specialist becomes a
staffing request. A draft: only the owner
marks a specification ready.
