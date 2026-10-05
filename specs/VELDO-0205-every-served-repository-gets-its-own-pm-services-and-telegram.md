---
schema: veldo.spec/v1
id: VELDO-0205
title: Every repository the factory serves gets its own working PM services on the one shared store connection, each command judged, written and shown only by the services of the repository it names, and the owner's Telegram requests and replies reach the right repository through the one bot, each message naming its repository when the factory serves more than one
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
  - "engine/.veldo/control_claim.py"
  - ".veldo/control_claim.py"
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
  - "engine/.veldo/control_team_routes.py"
  - ".veldo/control_team_routes.py"
  - "engine/.veldo/control_decomposition.py"
  - ".veldo/control_decomposition.py"
  - "engine/.veldo/control_intake_routes.py"
  - ".veldo/control_intake_routes.py"
  - "engine/.veldo/control_signer_answers.py"
  - ".veldo/control_signer_answers.py"
  - "scripts/suites/92_veldo_0088_pm_cycles.py"
  - "scripts/suites/68_veldo_0126_intake.py"
  - "scripts/suites/86_veldo_0189_engine_upgrade.py"
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
    repository's entity (no_such_item for backlog and grooming items, as the VELDO-0088 fix names it;
    wrong_repository for allocation, for a team command naming another repository's project or unit and
    for a backlog take of another repository's project's feature; snapshot_identity_mismatch for a
    snapshot; missing_authority for an inbox answer or disposition naming an alias only another repository
    holds), a Telegram message addressed to a project whose execution repository this instance does
    not serve (missing_authority:repository_not_served, control_service's name), a reply to a presentation
    of no served repository (unknown_presentation, VELDO-0066's name), and a registration made on a
    connection the lock holder did not open (missing_authority:not_the_authority, control_api_authority's
    name). Each service's own refusals pass through unchanged.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every line the running service builds gets working PM services for its own repository on the
      service's connection and the ingress's connection, however many repositories the instance serves, and no
      connection beyond those two is opened. Set and completeness: Exactly these per-repository authorities
      become keyed by repository on their connection: Teams (control_team), Inbox (control_assignment), the
      claim Receiver (control_claim, built by control_service receiver(repository)), ReadSets
      (control_readset), and on the ingress connection Presenter (control_channel_presentation frame) and
      Settlement (control_request_settlement); control_backlog and control_grooming already are (the
      VELDO-0088 fix). Domain-wide authorities (control_project, control_intake, control_alias,
      accept_revision, channel activation and enrollment, and the module-level transitions of
      control_dispatch and the project cycle record) stay one per connection. Each keyed connection keeps
      ONE transition per command, which hands the command to the service of the repository it names and
      refuses invalid_input:repository when no service of that repository is registered. Teams, Inbox and
      the claim Receiver are keyed by the repository_uuid of the signed command their service has already
      checked against its coordinates, which Teams adds to its store parameters (Inbox's assignment_id and
      the claim id already carry it); the snapshot authority
      (control_readset attach) keeps one ReadSets per repository; ReadSets.execute adds its own
      repository_uuid to the parameters of accept_snapshot and of every enabled operation, and the keyed
      transition picks the ReadSets of that parameter, never of the stored revision or snapshot, so the
      picked ReadSets still checks the accepted revision (accept) and the stored snapshot (SN.load) are its
      own; control_service's inbox(repository) and receiver(repository) build that repository's service on
      first use, with or without a line, and return the same one afterwards. The allocation authority
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
      repository's ids, reads back every record each wrote (team, assignment, backlog item, grooming request,
      snapshot, allocation) and requires its repository_uuid to be that repository's, and asserts the
      process opened exactly the two connections; pm/same-repository-twice
      builds A's line twice and requires invalid_registration:pm_services with the journal head and registry
      unchanged; pm/unserved-repository executes, directly on the service's connection (control_store
      execute), a store command of each keyed operation whose parameters name a third repository C that has
      no services, and requires invalid_input:repository with nothing written, and sends the same signed
      command through the service and requires missing_authority:repository_not_served; lock/not-the-authority
      calls from_line and open_ingress, which take the service's authority lock descriptor and ask
      control_api_authority.authority_problem(lock, conn) before registering anything, with a descriptor this
      process does not hold the lock on, and requires missing_authority:not_the_authority with the registry
      unchanged. Falsifier: Restore the single registration in Teams
      (conn.command_registry[OPERATION] = self._in_transaction), and pm/two-lines must fail on A's team record
      stored with B's repository_uuid.
    falsified_by: >
      Restore the single registration in Teams (conn.command_registry[OPERATION] = self._in_transaction), and
      pm/two-lines must fail on A's team record stored with B's repository_uuid.
  - id: AC2
    text: >
      Claim: Work for one repository is never judged by, written to or shown as another repository's. Set and
      completeness: The repository a command names is a field its signer chooses, so it only picks the
      service; the picked service then checks, inside the store transaction, that every entity the command
      names belongs to its own repository, taking the repository of a project from the project record's
      execution_repository (VELDO-0149) and never from the command. It refuses: an allocation naming B's
      kind under A's ids (wrong_repository); a snapshot whose accepted revision is B's requested under A
      (snapshot_identity_mismatch); a team command (propose, amend, owner_save or assign) naming a project
      whose execution_repository is not the service's, or assigning a unit whose repository_uuid is not
      the service's (wrong_repository, a new check in control_team); a backlog take of a feature whose
      project's execution_repository is not the service's (wrong_repository, a new check in
      control_backlog); an inbox answer or disposition under A's ids naming an alias only B holds
      (missing_authority, as control_assignment already refuses an alias with no assignment in the
      service's own namespace); and a backlog operation or grooming proposal naming B's item
      (no_such_item, the VELDO-0088 fix). Every read a service
      offers lists only its repository's records: the inbox index, the backlog listing, the project cycle
      records, the pending publication obligations, and the pm_snapshot_inputs read set, whose decisions
      collection is narrowed to where repository_uuid is the line's repository and whose dispatches
      collection to where contract.repository is the line's repository (the read-set where gains dotted
      field paths for this); the narrowed declaration has a new registration digest, so a snapshot accepted
      before the upgrade refuses stale_input once and the next cycle takes a new one. Rows: pm/cross-repository signs
      each of those commands with A's ids naming B's entity, and also signs a team propose and a backlog take
      with B's ids naming A's project, and requires each named refusal, every named entity
      unchanged and the journal head unchanged; pm/views fills both repositories and requires every read of A's
      services to list A's records only and B's to list B's only, including A's accepted pm_snapshot_inputs snapshot holding none of B's assignments or dispatches. Falsifier: Let the keyed accept_snapshot
      transition skip the picked ReadSets' check of the accepted revision's repository, and pm/cross-repository
      must fail on A's snapshot accepted over B's revision.
    falsified_by: >
      Let the keyed accept_snapshot transition skip the picked ReadSets' check of the accepted revision's
      repository, and pm/cross-repository must fail on A's snapshot accepted over B's revision.
  - id: AC3
    text: >
      Claim: The one Telegram bot presents every served repository's pending requests, each message naming
      its repository when the instance serves more than one, and the owner's reply settles the request of the repository whose message he replied to,
      never another's. Set and completeness: open_ingress takes the instance's served repositories (the
      service's configured repositories, of which the ingress configuration's authority_ids repository must be
      one, as control_service_channel installable already checks) and builds ONE gate and ONE acquirer (one
      bot, one acquisition cursor) and, per served repository, its Inbox, Presenter and Settlement on the
      ingress connection, each keyed by repository as AC1 states. Channel.tick presents every repository's
      pending requests. When the instance serves more than one repository, every message the ingress sends
      for a repository (presentation, notice, tell and hint) begins with the line `Repository: <label>`,
      where the label is the final component of the path the store binds for that repository (control_store
      bound_repository) followed by the first eight characters of its uuid in parentheses, and the project
      name on a second line where the request has one; in a presentation these lines come first in the body,
      before `Veldo needs your`, so a multi-part presentation shows them in part 1 after its part line. The
      label and project lines are recorded in the receipt (a repository_label field) and are part of the
      rendered bytes the receipt's digest covers. When the instance serves one repository, nothing is added:
      the receipt has no repository_label, the renderer version is unchanged, and every message is byte for
      byte what it is today, so every existing receipt still verifies. A hint for a message that names a
      project carries the label of that project's execution repository, whichever presenter sends it. A
      reply is routed by the presentation receipt it replies to
      (receipt_for_message, which reads every repository's receipts): the receipt's request id
      (assignment:<repository_uuid>:<alias>, written by the presenter, never by the sender) names the
      repository, the Acquirer hands the reply to that repository's Presenter (canonical_answer and answer),
      and that repository's Settlement settles it. from_line builds each line's Grooming with its own
      repository's ingress Inbox, Presenter and Settlement. A reply to a message of no served repository is
      unknown_presentation. Rows: telegram/one-repository serves only A and requires A's presentation, hint
      and notice bytes to equal those rendered without this specification, with no repository_label in the
      receipt; telegram/two-presentations has one pending request in each repository and
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
      only the factory PM until it routes it to a project. Set and completeness: Intake decides a project only from the command's
      project field or a ticket key unique to one project (VELDO-0152, unchanged), and the project's execution
      repository (VELDO-0149) is the repository the message is addressed to. A project's execution
      repository is fixed at activation (no operation changes it), so it is the authority: the intake
      proposal records it, the line of that repository picks the proposal up only when the recorded
      repository equals its own, and the taken-as-work hint names the project and, when the instance serves
      more than one repository, begins with that repository's label. A message naming a project whose
      execution repository this instance does not serve is refused missing_authority:repository_not_served,
      the owner is told so in the hint, and no proposal is written. A message naming no project is the
      factory inbox proposal VELDO-0152 defines: only the factory project's PM cycle lists it (its
      pm_snapshot_inputs inbox, in the line of the factory project's execution repository); no other
      project's cycle, no Inbox and no backlog of any repository lists it until the factory PM routes it to
      a project, and the project question an unclear route asks offers each project with its repository's
      label when the instance serves more than one. There is no repository syntax and no second bot: a repository with no project is
      not addressable from Telegram until a project is activated on it. Rows: telegram/addressed-by-project
      sends one message naming A's project and one carrying B's ticket key and requires each proposal to record
      its own project's repository, each hint to begin with that label, and only that repository's snapshot
      inputs to list it; telegram/unaddressed sends a message naming no project and requires a factory inbox
      proposal that only the factory project's cycle inputs list, then routes it to B's project and requires it in B's inputs
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
bot, always seeing which repository a message is about when the factory serves more than one, and always reaching the repository he meant.

## Context

W152 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. The VELDO-0088 fix
(branch fix-veldo-ingress-grooming, its History of 2026-10-04) found that on one store connection several
authorities are one per connection: control_alias attach and control_readset attach refuse a second
registration, and Teams and Inbox register their command as the connection's single transition, so the last
built judges every repository's commands. That fix keyed control_backlog and control_grooming by repository
and made from_line refuse a second repository's line up front (invalid_registration:pm_services), leaving
per-repository allocation, snapshot, teams, inbox and claim authorities open; and the Telegram ingress is built for
the one repository its configuration names. MVP means every product function, so the factory must serve
several repositories. This specification starts from main after that fix lands: its dependency on the fix
is its dependency on VELDO-0088, whose branch carries commits 63f6a737 (keyed backlog and grooming, the
second-line refusal), 0a0d0c63 (no_such_item for another repository's item) and e0d531a8 (the grooming
mutation). If it is built before they are on main, its branch is cut from fix-veldo-ingress-grooming and
rebased onto main once VELDO-0088 merges.
VELDO-0138 is in this specification's depends_on but not in W152's: it is a standalone item built
on 2026-09-25 that Release 1 reuses, bound to no work item, and a plan item may depend only on the
specification of another work item.

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

Keying by the signed command's repository (or, for ReadSets, by the repository its own execute adds)
keeps the judgment where the service's own coordinate check already is: the transition picks the
service, and the service refuses anything not its own, taking a project's repository from the project
record rather than from the command, so a wrong pick refuses rather than writes. The label is derived from what the store
already binds, so no new configuration names a repository for display.

## History

2026-10-04: new specification for the second-repository blocker the VELDO-0088 fix recorded
(invalid_registration:pm_services and the one-repository Telegram ingress), written and marked ready at
the owner's request.

2026-10-04: built on branch build-veldo-0205 (the VELDO-0088 fix branch merged with this specification).
Teams, Inbox, the claim Receiver, ReadSets, the framing Presenter and Settlement now each keep one
transition per command on their connection that hands it to the service of the repository it names
(invalid_input:repository otherwise); ReadSets.execute adds its own repository_uuid and the read-set where
gains dotted paths. from_line builds every line's services: it asks control_api_authority.authority_problem
with the service's authority lock first, refuses only a second build of the same repository, attaches the
one allocation authority over every line's repository, shares one Intake, and gives each line's Grooming
its repository's ingress Inbox, Presenter and Settlement. open_ingress takes the served repositories and
the lock, builds one gate and acquirer, and the Acquirer hands each reply to the presenter of the
repository its receipt's request names. With more than one served repository, presentations, tells and
hints begin with `Repository: <label>` (and `Project: <name>`), bound in the receipt's repository_label;
with one, every byte is unchanged. Footprint additions, each needed by a criterion: control_team_routes
(its owner_save command now carries the repository Teams is keyed by), control_decomposition (an allocation
for another repository's item is refused wrong_repository, the AC2 allocation refusal, and its pending
obligations are its own), control_intake_routes (a routed proposal records its project's repository and
the unclear-route question labels each project), control_signer_answers (the protected signer signs an
answer naming the repository whose request it answers, else no reply to a second repository could
settle), and suite 92, whose followup/two-repositories row asserted the second-line refusal this
specification removes; finding 88's v88-second-line-registers is retired with it, and findings 136 and
138 keep their mutations with the anchors of the calls that now pass the served repositories. Proof:
suite 95_veldo_0205_multirepo (13 rows), proof/VELDO-0205 (drive.py, red-at-01734c59.json: every
behaviour row red by assertion; pm/same-repository-twice and telegram/one-repository hold there too, by
design), and 18 finding 205 mutations, each red on its named row. Two more suites follow the specified
change: suite 68_veldo_0126_intake's exact proposal fields now include `repository`, and suite
86_veldo_0189_engine_upgrade's restore-reported row names as blocked the rows of the file it damages
(a recorded row of control_request_settlement, an owning module this specification changes since that
row's older engine, restores, so the refusal rightly does not name it). The claim Receiver keeps its own
registration literal and Settlement's dispatch has no getattr, so the VELDO-0169 writer census still
traces every claim write to the Gate's project check.
