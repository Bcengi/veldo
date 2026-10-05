---
schema: veldo.spec/v1
id: VELDO-0205
title: Every repository the factory serves gets its own working PM services on the one shared store connection, each command judged, written and shown only by the services of the repository it names, and the owner's Telegram requests and replies reach the right repository through the one bot, each message naming its repository
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W152
plan_revision: 4
depends_on: [VELDO-0035, VELDO-0037, VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0068, VELDO-0073, VELDO-0078, VELDO-0079, VELDO-0088, VELDO-0089, VELDO-0126, VELDO-0138, VELDO-0149, VELDO-0152, VELDO-0154, VELDO-0171]
placement: [contracts, engine, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_alias.py"
  - ".veldo/control_alias.py"
  - "engine/.veldo/control_readset.py"
  - ".veldo/control_readset.py"
  - "engine/.veldo/control_team.py"
  - ".veldo/control_team.py"
  - "engine/.veldo/control_assignment.py"
  - ".veldo/control_assignment.py"
  - "engine/.veldo/control_backlog.py"
  - ".veldo/control_backlog.py"
  - "engine/.veldo/control_grooming.py"
  - ".veldo/control_grooming.py"
  - "engine/.veldo/control_intake.py"
  - ".veldo/control_intake.py"
  - "engine/.veldo/control_workflow_cycle_pm.py"
  - ".veldo/control_workflow_cycle_pm.py"
  - "engine/.veldo/control_channel_ingress.py"
  - ".veldo/control_channel_ingress.py"
  - "engine/.veldo/control_channel_presentation.py"
  - ".veldo/control_channel_presentation.py"
  - "engine/.veldo/control_channel_attribution.py"
  - ".veldo/control_channel_attribution.py"
  - "engine/.veldo/control_request_settlement.py"
  - ".veldo/control_request_settlement.py"
  - "engine/.veldo/control_service_channel.py"
  - ".veldo/control_service_channel.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "scripts/suites/*_veldo_0205_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0205-every-served-repository-gets-its-own-pm-services-and-telegram.md"
  - "specs/index.md"
  - "proof/VELDO-0205/*"
behavior_bearing: true
observability:
  logs: >
    Record each PM service a line registers on a connection with its repository, connection (service or
    ingress) and service kind; each command a keyed transition hands on, with its operation, command id,
    the repository that picked the service and the outcome; each Telegram message the ingress sends or
    acquires with the repository it was routed to, the request or proposal id and the outcome; never a
    message's text, a brief, a token or a signature.
  metrics: >
    Count registered PM services by repository and kind, keyed transitions by operation, repository and
    outcome, refusals by name, and Telegram presentations, settlements and intake proposals by repository.
  traces: >
    Join each acquired Telegram reply to the presentation receipt it answered, that receipt's request and
    repository, and the settlement record it produced; join each intake proposal to its project and that
    project's execution repository.
  error_taxonomy: >
    Distinguish a command naming a repository that has no service of that kind on the connection
    (invalid_input:repository), a second registration of one repository's service of one kind on one
    connection (invalid_registration:pm_services), a command signed with one repository's ids naming another
    repository's entity (no_such_item for backlog and grooming, as the VELDO-0088 fix names it;
    wrong_repository for allocation; snapshot_identity_mismatch for a snapshot; stale_subject for a team or
    inbox command), a Telegram message addressed to a project whose execution repository this instance does
    not serve (missing_authority:repository_not_served, control_service's name), a reply to a presentation
    of no served repository (unknown_presentation, VELDO-0066's name), and a registration made on a
    connection the lock holder did not open (missing_authority:not_the_authority, control_api_authority's
    name). Each service's own refusals pass through unchanged.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every line the running service builds gets working PM services for its own repository on the
      service's connection and the ingress's connection, however many repositories the instance serves, and no
      connection beyond those two is opened. Set and completeness: Every authority that today registers its
      command as the connection's single transition becomes keyed by repository on that connection: the
      connection keeps ONE transition per command, which hands the command to the service of the repository
      it names and refuses invalid_input:repository when no service of that repository is registered, the
      pattern the VELDO-0088 fix gave control_backlog and control_grooming. Teams (control_team) and Inbox
      (control_assignment) are keyed by the repository_uuid of the signed command their service has already
      checked against its coordinates, carried in the store parameters; the snapshot authority
      (control_readset attach) keeps one ReadSets per repository and its accept_snapshot and each enabled
      operation's transition pick the ReadSets of the repository the snapshot request names, which still checks
      the accepted revision is its own; control_service's inbox(repository) returns the one Inbox registered
      for that repository on its connection instead of building one per use. The allocation authority
      (control_alias) is already one domain's authority over a map of repositories, so it stays one per
      connection: the service attaches it once, over every served repository with that repository's line
      workspace, before any line builds, and from_line uses that authority and binds its own publisher
      (Allocations.bind_publisher, one per repository). Intake, which is domain wide, is built once per
      connection and shared by every line. from_line no longer refuses a second repository's line; it refuses
      a second build of the SAME repository's services on one connection (invalid_registration:pm_services)
      before registering anything. VELDO-0171's lock rule holds: every registration is on the service's
      connection or the ingress's connection, both opened by the process holding authority.lock, and a keyed
      registration on a connection whose process does not hold the lock is refused
      missing_authority:not_the_authority. Rows (suite scripts/suites/*_veldo_0205_*.py), each on a store laid
      down with two adopted repositories A and B, two projects each activated on one of them (VELDO-0149) and
      the real ingress: pm/two-lines builds both lines through from_line and, for each repository, allocates a
      document of its own kind, accepts a snapshot over its own accepted revision, opens a team request, opens
      and answers an inbox request, admits a backlog item and grooms it, each accepted and committed with that
      repository's ids, and asserts the process opened exactly the two connections; pm/same-repository-twice
      builds A's line twice and requires invalid_registration:pm_services with the journal head and registry
      unchanged; pm/unserved-repository sends a correctly signed command for a third repository C that has no
      services and requires invalid_input:repository with nothing written; lock/not-the-authority attaches a
      keyed registration on a connection opened by a process that does not hold the lock and requires
      missing_authority:not_the_authority. Falsifier: Restore the single registration in Teams
      (conn.command_registry[OPERATION] = self._in_transaction), and pm/two-lines must fail on A's team request
      judged by B's Teams.
    falsified_by: >
      Restore the single registration in Teams (conn.command_registry[OPERATION] = self._in_transaction), and
      pm/two-lines must fail on A's team request judged by B's Teams.
  - id: AC2
    text: >
      Claim: Work for one repository is never judged by, written to or shown as another repository's. Set and
      completeness: The service a keyed transition picks still checks that every entity the command names
      belongs to its own repository, inside the store transaction, and refuses by the name the service
      already uses: an allocation naming B's kind under A's ids (wrong_repository), a snapshot whose accepted
      revision is B's requested under A (snapshot_identity_mismatch), a team command naming B's assignment
      (stale_subject), an inbox answer or disposition naming B's assignment id (stale_subject), and a backlog
      operation or grooming proposal naming B's item (no_such_item, the VELDO-0088 fix). Every read a service
      offers lists only its repository's records: the inbox index, the backlog listing, the project cycle
      records, the pending snapshots and the pending publication obligations. Rows: pm/cross-repository signs
      each of those five commands with A's ids naming B's entity and requires each named refusal, B's entities
      unchanged and the journal head unchanged; pm/views fills both repositories and requires every read of A's
      services to list A's records only and B's to list B's only. Falsifier: Let the keyed accept_snapshot
      transition skip the picked ReadSets' check of the accepted revision's repository, and pm/cross-repository
      must fail on A's snapshot accepted over B's revision.
    falsified_by: >
      Let the keyed accept_snapshot transition skip the picked ReadSets' check of the accepted revision's
      repository, and pm/cross-repository must fail on A's snapshot accepted over B's revision.
  - id: AC3
    text: >
      Claim: The one Telegram bot presents every served repository's pending requests, each message naming
      its repository, and the owner's reply settles the request of the repository whose message he replied to,
      never another's. Set and completeness: open_ingress takes the instance's served repositories (the
      service's configured repositories, of which the ingress configuration's authority_ids repository must be
      one, as control_service_channel installable already checks) and builds ONE gate and ONE acquirer (one
      bot, one acquisition cursor) and, per served repository, its Inbox, Presenter and Settlement on the
      ingress connection, each keyed by repository as AC1 states. Channel.tick presents every repository's
      pending requests. Every message the ingress sends for a repository begins with the line
      `Repository: <label>`, where the label is the final component of the path the store binds for that
      repository (control_store bound_repository) followed by the first eight characters of its uuid in
      parentheses, and the project name on a second line where the request has one; the label is part of the
      rendered bytes the receipt's digest covers. A reply is routed by the presentation receipt it replies to
      (receipt_for_message, which reads every repository's receipts): the receipt's request names the
      repository, and that repository's Settlement settles it. A reply to a message of no served repository is
      unknown_presentation. Rows: telegram/two-presentations has one pending request in each repository and
      requires two messages through the one bot, each beginning with its own label; telegram/reply-routes
      answers B's message and requires B's request settled by B's Settlement and A's request still pending,
      then answers A's and requires A's settled; telegram/label-bound requires a receipt whose rendered bytes
      omit or change the label to be presentation_mismatch. Falsifier: Settle every acquired reply through the
      Settlement of the ingress configuration's authority_ids repository, and telegram/reply-routes must fail on
      B's answer not settling B's request.
    falsified_by: >
      Settle every acquired reply through the Settlement of the ingress configuration's authority_ids
      repository, and telegram/reply-routes must fail on B's answer not settling B's request.
  - id: AC4
    text: >
      Claim: The owner addresses a repository through a project, and a message that addresses none reaches
      no repository until it is routed. Set and completeness: Intake decides a project only from the command's
      project field or a ticket key unique to one project (VELDO-0152, unchanged), and the project's execution
      repository (VELDO-0149) is the repository the message is addressed to; the intake proposal records that
      repository, the line of that repository picks it up, and the taken-as-work hint names the project and
      begins with that repository's label. A message naming a project whose execution repository this
      instance does not serve is refused missing_authority:repository_not_served with that hint and no
      proposal. A message naming no project is the factory inbox proposal VELDO-0152 defines and belongs to
      no repository: no repository's PM services, snapshot inputs or inbox list it until the factory PM
      routes it to a project, and the project question an unclear route asks offers each project with its
      repository's label. There is no repository syntax and no second bot: a repository with no project is
      not addressable from Telegram until a project is activated on it. Rows: telegram/addressed-by-project
      sends one message naming A's project and one carrying B's ticket key and requires each proposal to record
      its own project's repository, each hint to begin with that label, and only that repository's snapshot
      inputs to list it; telegram/unaddressed sends a message naming no project and requires a factory inbox
      proposal that no repository's services list, then routes it to B's project and requires it in B's inputs
      only; telegram/unserved-project requires missing_authority:repository_not_served for a project activated
      on a repository this instance does not serve. Falsifier: Record the ingress configuration's authority_ids
      repository as every proposal's repository instead of its project's execution repository, and
      telegram/addressed-by-project must fail on B's proposal recorded under A.
    falsified_by: >
      Record the ingress configuration's authority_ids repository as every proposal's repository instead of
      its project's execution repository, and telegram/addressed-by-project must fail on B's proposal recorded
      under A.
required_evidence: [unit, integration]
rollback: >
  Restore the single registrations and from_line's refusal of a second repository's line, and configure one
  repository per instance. Records already written stay as accepted records of the repository they name; no
  record is rewritten. No automatic rollback is authorized.
---

## Intent

The owner runs one factory for several repositories: each repository's work is planned, allocated,
staffed, asked about and groomed as its own, and the owner talks to all of them through the one Telegram
bot, always seeing which repository a message is about and always reaching the repository he meant.

## Context

W152 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. The VELDO-0088 fix
(branch fix-veldo-ingress-grooming, its History of 2026-10-04) found that on one store connection several
authorities are one per connection: control_alias attach and control_readset attach refuse a second
registration, and Teams and Inbox register their command as the connection's single transition, so the last
built judges every repository's commands. That fix keyed control_backlog and control_grooming by repository
and made from_line refuse a second repository's line up front (invalid_registration:pm_services), leaving
per-repository allocation, snapshot, teams and inbox authorities open; and the Telegram ingress is built for
the one repository its configuration names. MVP means every product function, so the factory must serve
several repositories. This specification starts from main after that fix lands.

Architecture: per-repository keyed authorities on the one service connection (and on the one ingress
connection), not one connection per repository. VELDO-0171's lock rule makes the lock holder the only
writer, so further connections would all live in that one process and add no isolation: isolation has to
be in the judgment, by repository, whatever the connection. Store-wide state (owner declarations,
repository bindings, project records, claims, assignments and dispatches the cycles read) is shared, and
separate connections in one process would read it at different watermarks and contend for BEGIN
IMMEDIATE. Telegram has one bot and one acquisition cursor, so one ingress connection must serve every
repository in any design, and keyed routing is needed there regardless. The keyed pattern is already
reviewed for backlog and grooming, control_alias's Allocations is already one domain's authority over a
repositories map, and control_service already routes every packet by its command's repository.

## Out of scope

Serving a repository the installation does not configure (adding a served repository stays a re-run of
setup); a second bot, a second chat or per-repository Telegram channels; repository addressing by any
syntax other than a project; per-repository budgets or reservation policies (VELDO-0204); the API edge and
owner UI views by repository; moving a project to another execution repository.

## What the reviewer judges

- Normal use: the owner has two repositories adopted and a project on each; both lines build their PM
  services at the service's start; he writes "add retry to the importer" naming the importer's project and
  the hint comes back headed with that repository's label; decision requests from both repositories arrive
  in the one chat, each headed with its repository, and each reply settles the request it answers; a message
  naming no project waits in the factory inbox until the factory PM routes it.
- Threat model: a command signed with one repository's ids written to, or judged against, another
  repository's entities; the last service built judging every repository's commands; a snapshot of one
  repository accepted over another's revision; a reply settling another repository's request, or a
  presentation whose repository label differs from the request it carries; an unaddressed message
  silently assigned to the configured repository; a read of one repository listing another's records; a
  second writer, by a registration on a connection the lock holder did not open.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), such as two
  bound repository paths ending in the same directory name and sharing a uuid prefix; forged rows in our
  own store.

## Notes

Keying by the signed command's repository rather than by a parameter alone keeps the judgment where the
service's own coordinate check already is: the transition picks the service, and the service refuses
anything not its own, so a wrong pick refuses rather than writes. The label is derived from what the store
already binds, so no new configuration names a repository for display.

## History

2026-10-04: new specification for the second-repository blocker the VELDO-0088 fix recorded
(invalid_registration:pm_services and the one-repository Telegram ingress), written and marked ready at
the owner's request.
