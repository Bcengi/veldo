---
schema: veldo.spec/v1
id: VELDO-0164
title: The API's read models, workflow read and event feed serve a member only the projects her scope covers
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W124
plan_revision: 4
depends_on: [VELDO-0076, VELDO-0130, VELDO-0162]
placement: [contracts, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_api_authority*.py"
  - ".veldo/control_api_authority*.py"
  - "engine/.veldo/control_api_models*.py"
  - ".veldo/control_api_models*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0164_*.py"
  - "scripts/suites/71_veldo_0130_api.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0164-api-reads-scoped-to-the-readers-projects.md"
  - "specs/index.md"
  - "proof/VELDO-0164/*"
behavior_bearing: true
observability:
  logs: >
    Record each read and feed answer with the principal, the model or cursor, and the count of entities
    and records withheld as out of scope; never a withheld entity's id or data.
  metrics: >
    Count reads and feed pages served, and entities and records withheld by reason (out of scope, no
    project).
  traces: >
    Join each answer to the member's scope as read and the journal watermark it was read at.
  error_taxonomy: >
    Distinguish a member with no project in this domain (unauthorized:no_project, unchanged) from an
    answer that withheld entities; a withheld entity is never reported as missing or as an error.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A read model and a workflow read serve a member only entities of projects her scope covers.
      Set and completeness: Every entity kind registered in the published read models (control_api_models
      READ_MODELS) declares, beside its owning module, how its project is read: a field of its own data,
      or the project of the unit, dispatch, request or repository it names, and every such project-bound
      kind is filtered to the reader's scope. The suite enumerates the registration and requires a rule
      for every kind, so a kind added later without one fails. Two kinds belong to no project and are
      served to every current member: the role and tool configuration records (VELDO-0127) and the
      default team (VELDO-0162, whose kind declares this rule when it is registered), because they hold no
      secret (a server's credentials live only in the VELDO-0144 catalog and the host keystore) and a
      member proposing a team must see the roles and tools she proposes from. Every entity whose rule
      reads no project (an intake proposal not yet routed, an account-scoped subscription reservation) is served only to a member whose scope is universal.
      The workflow read serves a revision only to a member whose scope covers its repository, the scope
      its editor is judged by. Seed two projects, A and B, with an entity of every registered
      project-bound kind in each, plus configuration records, the default team seeded through
      VELDO-0162's team kind, an unrouted intake_proposal row and an account-scoped
      subscription_reservation row; a member scoped to A reads every model and the workflow read and
      gets every A entity, no B entity, every configuration record and the default team, and neither
      entity whose rule reads no project. Falsifier: Serve read_model's whole result without
      the scope filter, and the member-scoped-to-A row must fail on a B entity.
    falsified_by: >
      Serve read_model's whole result without the scope filter, and the member-scoped-to-A row must fail
      on a B entity.
  - id: AC2
    text: >
      Claim: The live event feed lists a member only the changes of projects her scope covers and of the
      kinds served to every member. Set and
      completeness: For each committed journal record after the cursor, `events` lists only the changed
      entities AC1's rule for their kind serves the member, and only the
      published events and revocations of those entities, plus the revocations of her own credentials and
      membership; a record with none of them is left out of the page. The watermark and the publication's
      freshness are served unchanged, so her cursor still advances past records she cannot see. The edge's
      own journal follow (`feed`) is unchanged, since it ends sessions for every member. Commit, in order,
      a change to A, a change to B, a record changing both, and a revocation of another member; the member
      scoped to A gets the first record, the A half of the third, neither the second nor the fourth, and
      the head watermark. Falsifier: List every record's entities unfiltered, and the feed row must fail on
      the change to B.
    falsified_by: >
      List every record's entities unfiltered, and the feed row must fail on the change to B.
  - id: AC3
    text: >
      Claim: A member whose scope is universal, which the owner's is, reads exactly what she reads today.
      Set and completeness: With the same seeded store, the owner's answers from every read model, the
      workflow read and the event feed are compared with the answers VELDO-0130's reader gives before this
      change, entity for entity and record for record, including the project-less kinds. Falsifier: Treat
      the universal scope as covering no project-less kind but those served to every member, and the
      owner-unchanged row must fail on an unrouted intake proposal.
    falsified_by: >
      Treat the universal scope as covering no project-less kind but those served to every member, and
      the owner-unchanged row must fail on an unrouted intake proposal.
required_evidence: [unit, integration]
rollback: >
  Revert to VELDO-0130's reader, which serves only members whose scope covers a project of this domain;
  the owner's reads are unchanged either way. No automatic rollback is authorized.
---

## Intent

A member of the factory whose scope names one project reads that project's state and changes through the
API, and never another project's.

## Context

W124 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. The Codex
whole-project review of 2026-09-26 found, and a code read confirmed, that
`control_api_authority._reader_problem` checks only that the member's scope covers some project this
domain serves, after which `read()` and `events()` return the whole store and the whole journal: a
member scoped to project A reads project B. `control_api_models` says so in its own comment ("no model is
filtered to a member's projects yet"). VELDO-0130's threat model was the owner, whose scope is universal,
so this was not a defect of its review. VELDO-0141's record route already scopes each run to the project
its dispatch reserved, and this change brings the other reads to the same rule. This new specification
is draft; authoring it supplies neither implementation proof nor operational activation.

## Out of scope

The execution record route (VELDO-0141, already scoped); the commands (message, answer, revocation,
workflow save), which already judge the member; a member's read of her own intake proposals not yet routed to
a project; hiding the journal's length or the watermark.

## What the reviewer judges

- Normal use: the owner, and later a member scoped to some projects, opens the UI; the API reads models,
  the workflow canvas and the live feed for her session.
- Threat model: an authenticated current member reading an entity, a change or a revocation of a project
  outside her scope through any of these reads, or an unrouted intake proposal without a universal scope; a
  member denied the configuration records or the default team she needs to propose a team. The owner's
  account, the authority service and the store are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), such as a member
  inferring activity from the watermark's growth; forged rows in our own store; a kind whose project
  changes after it was written.

## Notes

The project rule belongs in the registration, beside the owning module and constant, so one table
decides both what a model reads and whom it serves, and the suite that already checks the registration
against the owning modules checks the rule too. The scope comparison is `control_membership.scope_covers`
with the project name, as the Gate and the record route use it.

## History

2026-09-27: new draft from the Codex whole-project review of 2026-09-26, confirmed in code. A draft: only
the owner marks a specification ready.

2026-09-27: amended on the independent check of this batch and the lead's decision. The role and tool
configuration records (VELDO-0127) and the default team are served to every current member, since they
hold no secrets and a member proposing a team must see them; every project-bound kind is filtered to the
reader's scope, and every other project-less kind stays universal-scope only. AC3's falsifier now fails on
an unrouted intake proposal, the project-less kind the universal scope still decides. Still a draft.

2026-09-27: lead follow-up: depends_on adds VELDO-0162 and AC1 seeds its default team; project-less
entities are decided per entity, with intake_proposal and subscription_reservation named from main.
Still a draft.

2026-09-27: marked ready by the owner (Telegram 29229, "all ready").
