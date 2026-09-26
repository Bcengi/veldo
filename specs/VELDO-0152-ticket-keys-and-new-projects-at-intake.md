---
schema: veldo.spec/v1
id: VELDO-0152
title: Intake decides a project from a ticket key or a name the message states, and the factory project's PM routes every other message to a new project, an existing project or one question
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W112
plan_revision: 4
depends_on: [VELDO-0076, VELDO-0088, VELDO-0126, VELDO-0128, VELDO-0130, VELDO-0154]
placement: [contracts, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_intake*.py"
  - ".veldo/control_intake*.py"
  - "packs/*/.veldo/control_intake*.py"
  - "engine/.veldo/control_project*.py"
  - ".veldo/control_project*.py"
  - "packs/*/.veldo/control_project*.py"
  - "engine/.veldo/control_workflow_cycle*.py"
  - ".veldo/control_workflow_cycle*.py"
  - "packs/*/.veldo/control_workflow_cycle*.py"
  - "engine/.veldo/control_telegram_report*.py"
  - ".veldo/control_telegram_report*.py"
  - "packs/*/.veldo/control_telegram_report*.py"
  - "engine/.veldo/control_api_models*.py"
  - ".veldo/control_api_models*.py"
  - "packs/*/.veldo/control_api_models*.py"
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
    Record each intake decision with the rule that decided the project (the API request's project, a
    name or a ticket key prefix) or that none did, the candidates it weighed and the project record
    versions it read; each route with the PM run that recorded it, the route, the project and the
    reason; each question asked; and each refused route by name, without secrets.
  metrics: >
    Count messages decided by request, by name and by ticket key, messages sent to the factory
    project's inbox, routes applied by each of the three routes, questions asked and routes refused by
    reason.
  traces: >
    Join each intake command to the project records it read, the factory inbox proposal, the PM run's
    dispatch, the route, and the proposal it moved to or the question it asked.
  error_taxonomy: >
    Distinguish a request that names the factory project, a route to a project outside the principal's
    scope, a malformed route, a route for a proposal already routed and a route that names the factory
    project; none invents ownership or makes the factory project a default.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A ticket key whose prefix exactly one candidate project lists, or a project the message
      explicitly names, decides that project at intake, even when the rest of the text reads like a new
      project, because a new project has no tickets. Set and completeness: Give project records an
      optional list of ticket key prefixes (for example `BCG`) and drive, through the common intake with
      one Telegram message and one API request each (the request signed by the API edge and submitted
      through `Intake.receive('api_request', ...)`, the intake interface the authenticated API calls, as
      VELDO-0126 drives it), "please do BCG-123" with one project listing `BCG`, with two listing it and
      with none; "BCG-123: add the new project settings page" and "in bcengi please add a new page to the
      project site" with `bcengi` listing `BCG`; and an API request whose project field names `bcengi`.
      The single lister, the named project and the requested project each get the proposal VELDO-0126
      makes for a decided project, with the deciding rule recorded, and no question is sent; a prefix
      two projects list, a prefix none lists, and a name or prefix on the factory project decide nothing
      and the message takes AC2's path. Falsifier: Ignore the projects' ticket key prefixes when
      resolving the project; the ticket-key routing row must fail.
    falsified_by: >
      Ignore the projects' ticket key prefixes when resolving the project; the ticket-key routing row must
      fail.
  - id: AC2
    text: >
      Claim: Every message that no ticket key, name or requested project decides goes to the factory
      project as an inbox proposal, with no intake question and no rule on its words, and the factory
      project is never a default, an only candidate or a destination for ordinary work. Set and
      completeness: With no configured project besides the factory project, with one and with two, for
      the owner and for a member whose scope covers one of two projects, send "start a new personal
      project called tidepool", "make a new repo for the site", "renew the project's certificate" and
      "fix the login bug" by Telegram and by API request. Each is kept as an inbox proposal of the
      factory project whose context lists only the principal's own projects, no question is sent, the
      decision records that nothing decided it, and none goes to an only candidate. An API request whose
      project field names the factory project is refused `invalid_input:factory_project`, and a
      principal whose scope covers no project is refused as VELDO-0126 refuses one. The factory
      project's record, with its PM role, is created in this concern's own store for its checks
      (VELDO-0143's setup creates it in a real factory). Falsifier: Route an undecided message to the
      only configured project, as VELDO-0126 did; the factory-inbox row must fail.
    falsified_by: >
      Route an undecided message to the only configured project, as VELDO-0126 did; the factory-inbox
      row must fail.
  - id: AC3
    text: >
      Claim: The factory project's PM run records exactly one of three routes with its reason, intake's
      routing command carries out exactly that route, and only an unclear route asks the owner. Set and
      completeness: For an inbox proposal from AC2, the factory loop's pass (VELDO-0154 AC1) starts the
      factory project's cycle, which dispatches the PM run through the Runner (VELDO-0088 AC1) on a fake
      `claude` or `codex` executable that prints the installed CLI's output shape, following the fakes of
      VELDO-0060 and VELDO-0061; its final message is the route document the suite supplies, and the
      cycle hands it to intake's routing command. Drive each route. A new project (a): the proposal stays
      in the factory project as a new-project request, the input of VELDO-0143's proposal, and nothing
      is asked. An existing project (b), named by project id: the proposal moves to that project in the
      form AC1 gives a decided project, and the factory inbox proposal is retired, pointing at it.
      Unclear (c): one "which project?" question goes to the principal on the channel he wrote on,
      offering his own projects and "a new project"; an answer naming one offered project by name or
      ticket key resolves as AC1 decides, and any other answer is kept on the proposal as new input for
      the factory PM's next run. Each applied route, with its reason and the dispatch that recorded it,
      is on the proposal record, in intake's observation and counts, in the proposal VELDO-0130's
      authenticated read serves the owner, and in a VELDO-0128 progress report. Falsifier: Send the
      "which project?" question on a new-project route; the asked-only-when-unclear row must fail.
    falsified_by: >
      Send the "which project?" question on a new-project route; the asked-only-when-unclear row must
      fail.
  - id: AC4
    text: >
      Claim: A route to a project outside the principal's scope, a malformed route and a route that
      names the factory project for ordinary work are each refused by name and change nothing. Set and
      completeness: Supply from the fake engine, for the owner's inbox proposal and for a member's: an
      existing-project route naming a project outside the member's scope (`unauthorized:project`);
      malformed routes, which are no route, two routes, an unknown route, a missing or empty reason, a
      project id that names no project, a project id on a new-project or unclear route, an unknown field
      and a document for another proposal (`invalid_input:route`); a document for a proposal already
      routed (`stale_version`); and an existing-project route naming the factory project
      (`invalid_input:factory_project`). Each refusal stops the rest of that cycle's proposals and is
      reported as VELDO-0088 reports one, the proposal stays in the factory inbox unchanged, and no
      project is decided, no question is sent and no route is recorded. Falsifier: Apply an
      existing-project route naming a project outside the member's scope; the scope-refusal row must
      fail.
    falsified_by: >
      Apply an existing-project route naming a project outside the member's scope; the scope-refusal row
      must fail.
required_evidence: [unit, integration]
rollback: >
  Resolve projects at intake by the requested project, a name and a ticket key only, and keep every other
  message as an inbox proposal of the factory project with no route applied; intake commands, proposals,
  routes and questions are kept. No automatic rollback is authorized.
---

## Intent

"Please do BCG-123" should land in the project whose tickets start with `BCG` without a question. Every
message that no ticket key or project name decides should be read by the factory project's PM, a
Claude Code or Codex run on the owner's logged-in subscriptions, which understands from his text
whether he wants a new project or an existing one, and asks him only when it cannot tell.

## Context

W112 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. Sections 2 and 5
of the approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner
Telegram 29162) amend VELDO-0126 AC1 with ticket key prefixes and the new-project route. VELDO-0126 has
landed with its proof, so this repository's convention puts that amendment in its own specification
that depends on it, and VELDO-0126 keeps its landed text. The owner then decided that a new project is
recognized by a model run that reads his text, never by a keyword rule (Telegram 29186, 29187 and
29191, History below). Today, with one configured project, intake routes a new-project request into it
as an objective; with two, it asks "which project?" offering only existing ones, and a ticket key names
no project.

## Out of scope

The factory project's project proposal, the repository and its provisioning (VELDO-0143); fetching the
ticket (the builder's or the PM's configured tools); the UI's rendering of the route (VELDO-0131, which
depends on this specification and reads it through VELDO-0130); the quality of the PM's judgment of a
text, which a fake engine does not exercise and the full journey (VELDO-0059) runs on real engines; any
change to VELDO-0126's criteria.

## What the reviewer judges

- Normal use: "please do BCG-123" lands in the project whose ticket keys include `BCG` with no
  question; "start a new personal project called tidepool" goes to the factory project's inbox and its
  PM records a new project; "fix the login bug" with one project goes to the factory PM, which routes it
  to that project; only an unclear route asks, offering his projects and "a new project"; each route
  and its reason show in the API read the UI uses and in the progress report.
- Threat model: a message a ticket key or name decides sent to the factory PM, or new-project wording
  overriding a deciding key or name; an undecided message routed to an only candidate or decided by
  its words; the factory project taking ordinary work, or chosen as a default or as an only candidate;
  a prefix two projects list treated as deciding either; a route applied to a project outside the
  principal's scope, a malformed or stale route applied, or a question sent on a route other than
  unclear; a model called from intake, the cycle runner or the authority instead of a dispatched run, or
  any paid model API. The owner's account, the store, the installed engines and the authenticated
  channel edges are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), including
  these from the review of the earlier build: the ticket key prefix pattern is matched with `match` and
  `$`, which accepts a trailing newline (`fullmatch` closes it); a project's prefix list has no cap on
  its length; "a new project" is offered to a member who cannot take it; and, from this amendment, a
  message that names an existing project while asking for a new one (the name decides), and a PM that
  returns unclear again after the owner's answer. Also VELDO-0143's proposal and provisioning; recovery
  (Release 2); forged rows in our own store and files planted in the installed directory.

## Notes

**What intake decides.** A project record gains an optional list of ticket key prefixes, kept by the
project service (`control_project`, `ticket_key_prefixes`, bound at activation), and every factory has
one project named `factory` (`FACTORY_PROJECT`, VELDO-0143). Intake reads the candidates' project
records inside its store transaction, and their versions are the command's expected versions, so the
prefix list revision that decided a message is the one it committed over. The requested project of an
API request, one candidate's name as a whole word, or a ticket key whose prefix exactly one candidate
lists decides the project, in that order, as VELDO-0126's name rule does. The factory project is never
a name the text says, a ticket key's project, a default or an only candidate. Everything else, including
what VELDO-0126 sent to an only candidate or asked about, goes to the factory project's inbox. Intake
itself holds no rule about new projects, and no rule anywhere tests the words "new", "project" or
"repository".

**The PM run and its route.** The factory project's team has a PM role. The loop starts the factory
project's cycle on the inbox proposal like any project's new input (VELDO-0154 AC1, VELDO-0088 AC3), and
its coordinate node dispatches the PM run through the Runner, a Claude Code or Codex run on the owner's
logged-in subscription accounts (VELDO-0060, VELDO-0061), never a model API. Its input is the proposal's
text and clarifications and the principal's own projects, each with its id, name and ticket key
prefixes; its output is one route document naming the proposal, exactly one route (`new_project`,
`existing_project` with a project id, or `unclear`) and a reason in plain words. The cycle hands the
document to intake's routing command as VELDO-0088 hands a proposal to its owning command, and that
command checks it against the principal's scope at the versions it reads. A member's message follows the
same path within that member's scope: the PM sees only his projects, and a route outside them refuses.
The route is recorded on the proposal, observed and counted by intake, served with the proposal by
VELDO-0130's read, and reported by a VELDO-0128 report event registered for it. The unclear route's
question is intake's own "which project?" question, delivered as VELDO-0126 delivers one.

**Built with VELDO-0143.** It is built with VELDO-0143 in the order of section 12 of the design, after
the factory loop (VELDO-0154) and the PM run (VELDO-0088) it needs.

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

2026-09-26, the owner's decision: a new project is recognized by a Claude Code or Codex run that reads
his text, never by a keyword rule (Telegram 29186, 29187: "This should be handled by llm that
understands that this should be a new project from text I send"; 29191: "By llm I always mean claude
code or codex"). The review of the earlier build found its keyword rule beating a deciding ticket key
("BCG-123: add the new project settings page" went to the factory project). AC1 keeps the ticket key
rule and adds that a deciding key or name wins over new-project wording; AC2 sends every other message
to the factory project's inbox with no question and no rule on its words, replacing the keyword rule
and, for undecided messages, VELDO-0126's only-candidate route and its intake question; new AC3 is the
factory PM's three routes, applied by intake's routing command, recorded and shown in the API read and
the progress report, and asking the owner only when the route is unclear; new AC4 is the refused
routes. The criteria are proved with a fake engine that supplies the PM run's route document, never a
model. depends_on adds VELDO-0088 (the PM run), VELDO-0154 (the loop that starts its cycle), VELDO-0128
(the progress report) and VELDO-0130 (the read the UI uses), so W112 moves from stage 4 to stage 5. The
footprint adds the cycle runner, the Telegram report and the API read models. The review's filed items
(`fullmatch` for the prefix pattern, a cap on the prefix list, and "a new project" offered to a member
who cannot take it) are named in What the reviewer judges. The earlier build on `build-veldo-0152`
(516afd1 to 1036497) is superseded, except its ticket-key parts, which carry over: the project record's
prefix list and `FACTORY_PROJECT` in `control_project`, and intake's ticket key matching, its reads of
the project records at their versions and its decision record. The status stays ready, because the owner
approved this direction; risk unchanged.
