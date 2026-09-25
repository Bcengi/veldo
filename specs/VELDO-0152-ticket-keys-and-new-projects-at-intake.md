---
schema: veldo.spec/v1
id: VELDO-0152
title: Intake routes a message by the ticket key prefixes a project lists, and a new-project request to the factory project
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W112
plan_revision: 4
depends_on: [VELDO-0076, VELDO-0126]
placement: [contracts, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_intake*.py"
  - ".veldo/control_intake*.py"
  - "packs/*/.veldo/control_intake*.py"
  - "engine/.veldo/control_project*.py"
  - ".veldo/control_project*.py"
  - "packs/*/.veldo/control_project*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0152_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0152-ticket-keys-and-new-projects-at-intake.md"
  - "specs/index.md"
  - "proof/VELDO-0152/*"
behavior_bearing: true
observability:
  logs: >
    Record each intake decision with the rule that decided the project (name, ticket key prefix or
    new-project request), the candidates it weighed and the question asked, without secrets.
  metrics: >
    Count messages routed by name, by ticket key, as new-project requests and by question.
  traces: >
    Join each intake command to the project record and the prefix list revision that decided it.
  error_taxonomy: >
    Distinguish an unresolved project, a ticket key prefix two candidates list and a new-project request;
    none invents ownership or selects the factory project as a default.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A ticket key in the text whose prefix exactly one candidate project lists decides that
      project, as the candidate's name does. Set and completeness: Give project records an optional list
      of ticket key prefixes (for example `BCG`) and drive, through the common intake with one Telegram
      message and one API request each (the request signed by the API edge and submitted through
      `Intake.receive('api_request', ...)`, the intake interface the authenticated API calls, as
      VELDO-0126 drives it), "please do BCG-123" with one project listing `BCG`,
      with two projects listing it, and with none. The first routes to that project; the second and third
      keep an inbox proposal and ask "which project?" rather than invent ownership. Falsifier: Ignore the
      projects' ticket key prefixes when resolving the project; the ticket-key routing row must fail.
    falsified_by: >
      Ignore the projects' ticket key prefixes when resolving the project; the ticket-key routing row must
      fail.
  - id: AC2
    text: >
      Claim: A new-project request is never routed to an only candidate and goes to the factory project as
      an inbox proposal with no intake question. Set and completeness: A new-project request is the whole
      words "new" and "project" or "repository", matched the way named projects are matched. With one
      configured project and with two, send "start a new personal project called tidepool" and "make a
      new repository for the site"; each goes to the factory project as an inbox proposal and no question
      is sent, while "renew the project's certificate" is not a new-project request. The factory project's
      record is created in this concern's own store for its checks (VELDO-0143's setup creates it in a
      real factory). Falsifier: Route "start a new personal project called tidepool" to the only
      configured project; the new-project routing check must fail.
    falsified_by: >
      Route "start a new personal project called tidepool" to the only configured project; the
      new-project routing check must fail.
  - id: AC3
    text: >
      Claim: Every "which project?" question offers "a new project" as an answer, and the factory project
      is never selected as a default or as an only candidate. Set and completeness: Drive an unresolved
      message with no configured project besides the factory project, with one and with two; every
      question lists "a new project" beside the existing projects, and none routes the message to the
      factory project unless it is a new-project request. Falsifier: Offer only existing projects in a
      "which project?" question; the new-project-choice row must fail.
    falsified_by: >
      Offer only existing projects in a "which project?" question; the new-project-choice row must fail.
required_evidence: [unit, integration]
rollback: >
  Resolve projects by name only and route no message to the factory project, as VELDO-0126 did; intake
  commands, proposals and questions are kept. No automatic rollback is authorized.
---

## Intent

"Please do BCG-123" should land in the project whose tickets start with `BCG` without a question, and
"start a new personal project called tidepool" should start a new project instead of being filed into
the only one there is.

## Context

W112 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4. Sections 2 and 5
of the approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner
Telegram 29162) amend VELDO-0126 AC1 with ticket key prefixes and the new-project route. VELDO-0126 has
landed with its proof, so this repository's convention puts that amendment in its own specification
that depends on it, and VELDO-0126 keeps its landed text. Today, with one configured project, intake
routes a new-project request into it as an objective; with two, it asks "which project?" offering only
existing ones, and a ticket key names no project.

## Out of scope

The factory project's PM cycle over a new-project request, the proposal and the repository (VELDO-0143);
fetching the ticket (the builder's or the PM's configured tools); any change to VELDO-0126's criteria.

## What the reviewer judges

- Normal use: "please do BCG-123" lands in the project whose ticket keys include `BCG`; "start a new
  personal project called tidepool" goes to the factory project with no question; any "which project?"
  question offers "a new project".
- Threat model: a new-project request routed into an existing project; the factory project chosen as a
  default or as an only candidate; a ticket key whose prefix two projects list treated as deciding either;
  a word that merely contains "new" read as a new-project request. The owner's account, the store and
  the authenticated channel edges are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); VELDO-0143's
  proposal and provisioning; recovery (Release 2); forged rows in our own store and files planted in the
  installed directory.

## Notes

A project record gains an optional list of ticket key prefixes, kept by the project service
(`control_project`). Every factory has one project named `factory` (VELDO-0143), whose PM prepares a
project proposal from a new-project request; intake never selects it as a default or as an only
candidate. It is built with VELDO-0143 in the order of section 12 of the design.

## History

2026-09-25: written for PLAN-0019 revision 4 from the approved operating-model design (Telegram 29162),
sections 2(e) and 5(e), whose VELDO-0126 AC1 amendments are carried here whole because VELDO-0126 has
landed: the ticket key rule, the new-project route with the design's falsifier, and the "a new project"
answer, one criterion each. A draft: only the owner
marks a specification ready.

2026-09-25, PLAN-0019 revision 4, third review: AC1 drives the API leg through the intake interface
`Intake.receive('api_request', ...)` with a request the API edge signs, as VELDO-0126 does, rather than
an authenticated API call, because the API server (VELDO-0130) is a later stage and drives its own leg.
Criterion meaning and status unchanged.
