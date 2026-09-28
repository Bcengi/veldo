---
schema: veldo.spec/v1
id: VELDO-0180
title: One typed owner command turns a conversation into a new or existing project's work, and that work starts with the conversation's context and results
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W140
plan_revision: 4
depends_on: [VELDO-0143, VELDO-0150, VELDO-0152, VELDO-0175, VELDO-0176, VELDO-0177, VELDO-0178]
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
  - "engine/.veldo/control_api*.py"
  - ".veldo/control_api*.py"
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
    Record each conversion with its conversation, the owner command that asked for it and its route (API
    or Telegram), the project route, the project and objective it made, and the digests of the rendering and the workspace snapshot it bound;
    never their content.
  metrics: >
    Count conversions by route (new project, existing project) and by command route, conversions that
    asked the owner one question, and conversion commands refused.
  traces: >
    Join each conversion to the owner command that asked for it, the route document the factory built from
    it and the project's first PM and build runs that read its inputs.
  error_taxonomy: >
    Distinguish a conversion command from anyone but the owner (missing_authority:conversation_owner), one
    with no project name (invalid_input:conversation_command:project_name), an out-of-scope route
    (VELDO-0152 AC4's refusals) and a snapshot whose digest differs from the one bound
    (binding_mismatch:conversation_snapshot).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A conversation becomes a project's work only on the owner's typed command,
      `conversations.make_project` in the API, or on Telegram in reply to one of its messages `/project <name>`
      or his own words meaning it ("make this a project called billing"), and the project is named from that command, never from anything a turn produced. Set and
      completeness: `conversations.make_project` is a POST route this specification adds to the published
      ROUTES table (VELDO-0130, VELDO-0178), and `/project` or its plain-words form is read as VELDO-0175 AC4 reads its commands, from the owner's own
      message only.
      The command names the conversation, its current version (VELDO-0174 AC1) and a name,
      with any text after the name as the objective in his words, else the conversation's first message. A
      name that is one of his projects' names or ids is the existing-project route; any other is a new
      project with that name, with the Git identity when the command names one. The factory builds VELDO-0152
      AC3's route document from the command alone, marked with its conversation as its source, and intake's
      routing command carries it out; a new project goes through VELDO-0143's proposal, which asks his one
      answer only when the identity is missing, and the objective is accepted by his command (VELDO-0150) in
      either route. A command from anyone but the owner is refused by name
      (missing_authority:conversation_owner) and one with no name is refused by name
      (invalid_input:conversation_command:project_name), each making nothing. A route document, a project
      name or a "created" claim in a turn's reply, tool results or protocol messages makes nothing, and
      VELDO-0181 AC2 keeps it as text. The suite sends each command form, and ends a turn with a well-formed
      route document naming a project and a reply that says "created". Falsifier: Carry out a route document
      found in a turn's final message, and the injected-route row must fail on a project made with no owner
      command.
    falsified_by: >
      Carry out a route document found in a turn's final message, and the injected-route row must fail on a
      project made with no owner command.
  - id: AC2
    text: >
      Claim: The project's work starts with the conversation's context and results: its objective binds
      the conversation's history and a snapshot of its workspace, and the project's PM and first build runs
      receive both. Set and completeness: At conversion the factory binds to the objective the conversation
      id, VELDO-0176 AC3's rendering of every turn so far (from the redacted records), never shortened because
      runs receive it as an input artifact file and not as their prompt, by digest, and a
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
typed command, and the project does not start from nothing: it has what the conversation learned and made.

## Context

W140 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. VELDO-0152's
routing command carries out a PM's route document, VELDO-0143 makes a new project on the owner's one
answer, and VELDO-0150 accepts an objective proposed by his own message. The factory builds the same route
document from the owner's typed command, so no new authority is added: the route takes effect through the
same routing command. A turn's output never proposes it, because a tool result or a fetched page could
carry a well-formed route document, and the name comes from his command for the same reason. A draft: only the owner marks it ready.

## Out of scope

Turning part of a conversation into several projects at once (one command, one route); moving an
existing project's work back into a conversation; landing anything from the conversation itself (only the
pipeline lands).

## What the reviewer judges

- Normal use: after a morning of back and forth that produced a working script, the owner replies
  `/project ads-audit audit last month's Google Ads spend` to the last reply; the project is made, asking him
  only for the Git identity when none is named, and its first PM run and build start from the
  conversation's history and the script.
- Threat model: a project made from a route the owner did not type (a turn's own route document, a tool
  result or fetched page carrying one, a re-run continuation); a project named from a turn's output; a reply that claims a project was made; a snapshot changed between conversion and
  the build; the conversation's commits reaching trunk without the gate and review.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); forged rows in
  our own store; the Line that serves the new project in the running service is VELDO-0188's.

## Notes

The rendering, not the held session, crosses into the project, so a credential value the session held
never reaches the project's runs.

## History

2026-09-27: new draft for the owner's conversation requirement (Telegram, 2026-09-27). Only the owner
marks a specification ready.

2026-09-27, review of the drafts: AC1 takes the conversion only from the owner's typed command
(`conversations.make_project` or Telegram's `/project <name>`), with the name from that command, since an
injected tool result could otherwise make a project with no question; depends_on adds VELDO-0178, whose
routes table the command joins. Filed: a new project gets no Line without a reinstall. Still a draft.

2026-09-27, third round: the filed note on a new project's Line now names VELDO-0188, which starts a
Line at run time for every project the store records. Criteria unchanged. Still a draft.

2026-09-27: marked ready by the owner (Telegram 29301, "All ready otherwise"), with his two points applied: plain-words commands (29299) and smart add on the subscription instead of a paid API (29300).
