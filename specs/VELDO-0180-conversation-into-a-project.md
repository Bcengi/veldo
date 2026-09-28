---
schema: veldo.spec/v1
id: VELDO-0180
title: One owner message turns a conversation into a new or existing project's work, and that work starts with the conversation's context and results
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W140
plan_revision: 4
depends_on: [VELDO-0143, VELDO-0150, VELDO-0152, VELDO-0175, VELDO-0176, VELDO-0177]
placement: [contracts, loop, fleet]
protected_paths: []
footprint:
  - "engine/.veldo/control_conversation*.py"
  - ".veldo/control_conversation*.py"
  - "engine/.veldo/control_intake*.py"
  - ".veldo/control_intake*.py"
  - "engine/.veldo/control_objective*.py"
  - ".veldo/control_objective*.py"
  - "engine/.veldo/control_project*.py"
  - ".veldo/control_project*.py"
  - "engine/.veldo/control_workflow_cycle*.py"
  - ".veldo/control_workflow_cycle*.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0180_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0180-conversation-into-a-project.md"
  - "specs/index.md"
  - "proof/VELDO-0180/*"
behavior_bearing: true
observability:
  logs: >
    Record each conversion with its conversation, the owner message that asked for it, the route, the
    project and objective it made, and the digests of the rendering and the workspace snapshot it bound;
    never their content.
  metrics: >
    Count conversions by route (new project, existing project), conversions that asked the owner one
    question, and route documents refused.
  traces: >
    Join each conversion to the turn whose message asked for it, the route document it produced and the
    project's first PM and build runs that read its inputs.
  error_taxonomy: >
    Distinguish a route document from a turn whose input was not the owner's own message
    (missing_authority:conversation_route), a malformed or out-of-scope route (VELDO-0152 AC4's refusals)
    and a snapshot whose digest differs from the one bound (binding_mismatch:conversation_snapshot).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The owner's one message in a conversation asking to make it a project becomes that project's
      work through VELDO-0152's routing command, with no further question when his message names what the
      route needs. Set and completeness: The turn that his message starts ends with the route document of
      VELDO-0152 AC3, a new project (with the project name and Git identity when his message names them) or
      an existing project named by id, marked with its conversation as its source. Intake's routing command
      carries out exactly that route, and only for a turn whose input was the conversation owner's own
      authenticated message; a route document from any other turn is refused by name
      (missing_authority:conversation_route). A new project goes through VELDO-0143's proposal, which asks
      his one answer only when the name or identity is missing; the objective his message proposes is
      accepted by that message (VELDO-0150) in either route. A reply text that says a project was made, with
      no route document, makes nothing. Falsifier: Take the route from the reply's text in place of the
      route document, and the route-document row must fail on a project made from a reply that only says
      "created".
    falsified_by: >
      Take the route from the reply's text in place of the route document, and the route-document row must
      fail on a project made from a reply that only says "created".
  - id: AC2
    text: >
      Claim: The project's work starts with the conversation's context and results: its objective binds
      the conversation's history and a snapshot of its workspace, and the project's PM and first build runs
      receive both. Set and completeness: At conversion the factory binds to the objective the conversation
      id, VELDO-0176 AC3's rendering of every turn so far (from the redacted records) by digest, and a
      snapshot of the workspace: its files, and for each attached project clone its local commits as a Git
      bundle against the trunk commit it was taken at, stored by digest under the project's state. The
      project's PM run and the first build run of the unit it stages receive the rendering and the snapshot
      as input artifacts, checked against the bound digests before launch (else
      binding_mismatch:conversation_snapshot); the builder starts from trunk and may apply the bundle, and
      the result reaches trunk only through the ordinary pipeline, gate, review and landing. The
      conversation stays open and points at the project. Falsifier: Bind only the owner's last message as
      the objective's input, and the context row must fail on the first turn's message missing from the PM
      run's input.
    falsified_by: >
      Bind only the owner's last message as the objective's input, and the context row must fail on the
      first turn's message missing from the PM run's input.
required_evidence: [unit, integration]
rollback: >
  Refuse conversation route documents while keeping every conversation, objective and project already
  made. No automatic rollback is authorized.
---

## Intent

A conversation that turns out to be real work becomes a project, or part of an existing one, with one
message, and the project does not start from nothing: it has what the conversation learned and made.

## Context

W140 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. VELDO-0152's
routing command carries out a PM's route document, VELDO-0143 makes a new project on the owner's one
answer, and VELDO-0150 accepts an objective proposed by his own message. A conversation turn proposes the
same route document, so no new authority is added: the route takes effect through the same command, on
the owner's own message. A draft: only the owner marks it ready.

## Out of scope

Turning part of a conversation into several projects at once (one message, one route); moving an
existing project's work back into a conversation; landing anything from the conversation itself (only the
pipeline lands).

## What the reviewer judges

- Normal use: after a morning of back and forth that produced a working script, the owner writes "make
  this a new personal project called ads-audit"; the project is made with no question, and its first PM
  run and build start from the conversation's history and the script.
- Threat model: a project made from a route the owner did not ask for (a turn's own idea, a tool result, a
  re-run continuation); a reply that claims a project was made; a snapshot changed between conversion and
  the build; the conversation's commits reaching trunk without the gate and review.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); forged rows in
  our own store.

## Notes

The rendering, not the held session, crosses into the project, so a credential value the session held
never reaches the project's runs.

## History

2026-09-27: new draft for the owner's conversation requirement (Telegram, 2026-09-27). Only the owner
marks a specification ready.
