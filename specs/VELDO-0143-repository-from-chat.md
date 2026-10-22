---
schema: veldo.spec/v1
id: VELDO-0143
title: A repository the owner asks for in chat is created or adopted and bound to a new project on his one answer
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W103
plan_revision: 4
depends_on: [VELDO-0028, VELDO-0029, VELDO-0047, VELDO-0068, VELDO-0076, VELDO-0088, VELDO-0089, VELDO-0126, VELDO-0132, VELDO-0139, VELDO-0142, VELDO-0149, VELDO-0150, VELDO-0152, VELDO-0153, VELDO-0154, VELDO-0161, VELDO-0162]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_repository*.py"
  - ".veldo/control_repository*.py"
  - "packs/*/.veldo/control_repository*.py"
  - "engine/.veldo/control_effect_executor*.py"
  - ".veldo/control_effect_executor*.py"
  - "packs/*/.veldo/control_effect_executor*.py"
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "packs/*/.veldo/control_factory_setup*.py"
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_service*.py"
  - "packs/*/.veldo/control_service*.py"
  - "engine/.veldo/control_project*.py"
  - ".veldo/control_project*.py"
  - "packs/*/.veldo/control_project*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/control_workflow_cycle_pm.py"
  - ".veldo/control_workflow_cycle_pm.py"
  - "packs/*/.veldo/control_workflow_cycle_pm.py"
  - "engine/.veldo/control_intake_routes.py"
  - ".veldo/control_intake_routes.py"
  - "packs/*/.veldo/control_intake_routes.py"
  - "engine/.veldo/control_objective.py"
  - ".veldo/control_objective.py"
  - "packs/*/.veldo/control_objective.py"
  - "engine/.veldo/control_grooming_request.py"
  - ".veldo/control_grooming_request.py"
  - "packs/*/.veldo/control_grooming_request.py"
  - "engine/.veldo/control_backlog.py"
  - ".veldo/control_backlog.py"
  - "packs/*/.veldo/control_backlog.py"
  - "scripts/suites/*_veldo_0143_*.py"
  - "scripts/suites/106_veldo_0185_dispatch_setup.py"
  - "engine/.veldo/control_telegram_report.py"
  - ".veldo/control_telegram_report.py"
  - "packs/*/.veldo/control_telegram_report.py"
  - "scripts/suites/72_veldo_0128_reports.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0143-repository-from-chat.md"
  - "specs/index.md"
  - "proof/VELDO-0143/*"
behavior_bearing: true
observability:
  logs: >
    Record each provisioning step with the repository, identity, settled decision, step name and
    outcome or named refusal; each adoption signature with the decision it answered; never a token.
  metrics: >
    Count repositories created, adopted and failed by reason, and adoption signatures issued.
  traces: >
    Join the owner's message, the factory PM run, the proposal, his settlement, every provisioning step,
    the adoption signature, the repository record and the activated project.
  error_taxonomy: >
    Distinguish directory not empty, remote exists, remote owner mismatch, token unavailable, creation
    refused by the host, push refused, no settled decision and signature refused; a repository left
    `failed` names its reason and is never reported ready.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A new-project request becomes one project proposal from the factory project's PM, settled
      by the owner's one answer, and nothing is asked when his message already names the project and the
      identity. Set and completeness: Setup creates the one `factory` project, bound to a small
      repository of its own under the factory state root that holds only its team configuration, with a
      PM role for requests that are not yet any project's. Send "start a new personal project called
      tidepool" and a message that names no identity; intake sends each to the factory project,
      the factory PM routes it as a new project (VELDO-0152 AC3), and the factory PM run prepares one
      proposal naming the
      project, the identity (asked in the same request when he did not say), the directory, the remote
      name and visibility, the first objective, the default team's current revision (VELDO-0162 AC4) and
      the default pipeline, and the coordination budget. His one answer, a yes or a correction, settles
      the project and the first objective, and no further question is sent; the first message, which
      named both, is itself that answer and nothing is presented. Falsifier: Present a proposal when his
      message already named the project and the identity; the nothing-asked row must fail.
    falsified_by: >
      Present a proposal when his message already named the project and the identity; the
      nothing-asked row must fail.
  - id: AC2
    text: >
      Claim: A repository is created only on a settled owner answer, by the repository provisioner as a
      registered protected effect whose steps run in order, each recorded, stopping by name at the first
      failure. Set and completeness: On the settlement the provisioner (VELDO-0028) refuses a directory
      that exists and is not empty, and takes the adoption path (VELDO-0161) when it is already a Git
      repository;
      otherwise it creates the directory under the identity's projects root, initializes the repository,
      lays down Veldo with the scaffold, writes the identity's author configuration and makes the initial
      commit; creates the remote under the identity's owner through GitHub's REST interface with the
      identity's token, using the standard library, at the chosen visibility (private unless he said
      otherwise); and pushes the initial commit with the identity's credential through the `identity`
      profile (VELDO-0153). Fail each step in turn against a disposable remote and require the repository
      record `failed` with that step named and no later step run. Falsifier: Run the provisioner without
      a settled answer; the settlement-required check must fail.
    falsified_by: >
      Run the provisioner without a settled answer; the settlement-required check must fail.
  - id: AC3
    text: >
      Claim: The same settlement activates the new project on the adopted repository with the default
      team and pipeline and admits its first objective, which is built as the project's first ordinary
      unit. Set and completeness: After creation and its adoption (VELDO-0161), or an adoption alone,
      reaches `active`, the settlement is applied as the project's activation (VELDO-0076, applied from
      his answer by VELDO-0149) with the default team revision the proposal named as its first team
      revision (VELDO-0162 AC4) and the default pipeline (VELDO-0132), and its first objective is
      accepted by his answer, or by his first message when it named both (VELDO-0150), and admitted at
      the default priority with no further question; a repository that ended `failed` activates nothing.
      Observe the owner told "tidepool is ready; the first objective is next", and the first unit
      dispatched in the new repository with the identity as author. Falsifier: Activate the project
      while its repository is still `provisioning`; the activation-order check must fail.
    falsified_by: >
      Activate the project while its repository is still `provisioning`; the activation-order check
      must fail.
required_evidence: [unit, integration]
rollback: >
  Stop provisioning and adoption and disable the adoption signer; repositories already created or
  adopted stay as they are, with their records, for the owner to remove by hand. No automatic rollback
  is authorized.
---

## Intent

The owner often starts a new project in a new directory that becomes a new Git repository, under the
Bcengi organization or his personal account. He asks in chat, and the factory creates the folder and
the repository and adopts it with no separate command, as Claude Code does for him today.

## Context

W103 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. Section 5 of the
approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner Telegram
29162) designs the factory project, the one-answer proposal, the provisioner and adoption. Today nothing
creates a repository as an effect, a running service cannot take on a new repository without
reinstallation, VELDO-0076 accepted only the store's one repository and only the owner's signed key
(VELDO-0149 widens both), and a new project cannot come from chat: with one configured project intake
routed the request into it, and with two it asked "which project?" offering only existing ones.
VELDO-0152, VELDO-0126's revision 4 amendment, routes the request here; VELDO-0142 supplies the identity
and VELDO-0153 its push profile and owner check; VELDO-0139's setup creates the factory project.

## Out of scope

The optional UI form for creating a repository, Git hosts other than GitHub, deleting or archiving a
repository, moving a repository between identities (refused), several projects in one repository, and
an identity spanning two remote owners.

## What the reviewer judges

- Normal use: the owner writes "start a new personal project called tidepool" in Telegram or the UI;
  the factory PM run proposes the project, he answers once (or not at all when his message said the
  identity), and the repository is created or adopted under that identity, taken on by the running
  service, bound to the activated project, and its first objective runs as the first ordinary unit.
- Threat model: a repository created without a settled owner answer; a non-empty directory
  overwritten; a remote created under the wrong owner or pushed with an ambient credential; a step
  failure that runs later steps or reports the repository ready; a second question after his answer; a
  project activated before its repository is active. Adoption, the adoption signer and taking the
  repository on without a restart are VELDO-0161's. The owner's account, the keystore, GitHub and the
  store are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); a name taken
  on GitHub between the proposal and the creation (it refuses by name); forged rows in our own store and
  files planted in the installed directory.

## Notes

Adoption, the adoption signer (which widens enrollment, section 13 of the design) and taking the
repository on without a restart are VELDO-0161, which creation ends in. The token needs workflow
permission because the scaffold writes `.github/workflows/veldo-gate.yml`. VELDO-0139 is a standalone
built item, so this edge is kept here and not in the plan graph.

## History

2026-09-25: written as a draft for PLAN-0019 revision 4 from the approved operating-model design
(Telegram 29162), section 5(e). Draft; the owner decides readiness.

2026-09-25, PLAN-0019 revision 4 review: depends_on adds VELDO-0154, the factory loop that starts
the factory project's PM cycle in AC1, split from VELDO-0129. Draft; the owner decides readiness.

2026-09-25, PLAN-0019 revision 4, third review: AC3's taking a repository on without a restart had no
falsifier, and giving it one would have made five criteria, so adoption (the former AC3, with the signer
scope and its falsifier) and the no-restart criterion with a new falsifier are the new draft VELDO-0161,
which depends_on now names. The former AC4 is AC3, and AC2 and AC3 name VELDO-0161 where creation ends in
adoption. Draft; the owner decides readiness.

2026-09-25, PLAN-0019 revision 4, fourth review: AC3 cited a "default team template (VELDO-0089)" that
VELDO-0089 does not define. The default team is now VELDO-0162 AC4, a versioned team the owner saves
through the team route, built in the design's second stage and so before this specification; AC1's
proposal names its current revision, AC3 gives the project that revision as its first team revision, and
depends_on adds VELDO-0162. Criterion meaning unchanged. Draft; the owner decides readiness.

2026-09-26, lead: AC1 names the factory PM's new-project route (VELDO-0152 AC3), since the owner replaced
the keyword rule with routing by the factory PM (Telegram 29186, 29187 and 29191).

2026-10-22 implementation on agent/claude/veldo-0143, built on VELDO-0161 (da39f3fb) and VELDO-0153 (b44736c0),
neither landed yet. control_project_proposal holds the factory PM's new-project document, the one proposal it
derives (repository uuid, directory under the identity's projects root, remote under the identity's owner and its
visibility, the adoption proposal with its scaffold commit when the directory is already a Git repository, the
default team's current revision, the default pipeline, charter, authority policy and budget), its brief, the
nothing-asked rule, the one presentation, his answer, and the one judge of a settled decision that the
provisioner, the adoption signer, the service's take-on and the activation all call. When the PM named no
identity, every configured identity is offered in the same request and his approving answer names one; an answer
that returns the proposal, or approves it naming none, is his correction: the factory PM's next run reads it and
its corrected document settles the decision with no second presentation. control_repository_creation and
control_effect_executor_creation are the provisioner: the registered protected effect `repository_provisioning`,
which the running service starts as its own process for a settled decision (never a worker), checks the
settlement before anything else, records each step and stops by name at the first failure, and ends in
VELDO-0161's adoption tail, refactored into control_effect_executor_adoption.enroll with its text and its
registered anchors unchanged. control_project.activate_decided refuses until the repository record is active,
also inside the activating transaction. The running service (control_service_projects) applies the answers,
starts the provisioner, fails a decision whose repository failed and tells the owner, and once the repository
is active applies the same settlement: the repository's first accepted revision (its initial or scaffold commit)
and the default team's capability configurations copied at the revisions the team names, so its Runner binds
them; the activation; the first team revision, the named default revision, after VELDO-0089's staffing checks;
the message moved into the project (control_intake_routes, on intake's own route command); the first objective
proposed by the project's PM and accepted by the decision (control_objective accept_decided, acceptance path
new_project); the decision activated; and the factory loop gains the repository's line. The owner is told
"<name> is ready; the first objective is next", or that it could not be set up and why, by VELDO-0128's report
of the decision record (event project_ready), through the reporter's one rendered send (VELDO-0168). Setup creates the factory
project's own repository at <state root>/factory, holding only team.json, enrolled by the owner, bound to the
workspace's identity and by the store, and activates the factory project on it; it writes host/provisioner.json.
The factory project's cycles run on the loop's factory line, the first line the work configuration names, since
its own repository is no line.

Footprint added in this change, each because the criteria cannot be met without it: control_workflow_cycle_pm
(the factory PM run that prepares the proposal from a NEW_PROJECT message, AC1, and the factory line);
control_intake_routes (the message moved into the new project as its first objective proposal, AC3);
control_objective (the first objective accepted by his answer, which VELDO-0077's acceptance by answer cannot
bind: the objective does not exist when he answers); control_grooming_request and control_backlog (work under
that objective admitted at the default priority with no further question, AC3, as VELDO-0079 admits work under an
objective his own message accepted); suite 106's fresh/team row, which asserted the factory project on the
workspace's repository and now asserts it on its own; control_telegram_report (the owner told, AC3, as a
report event rather than a new send site) and suite 72's registry row, which enumerates every event.
init_scaffold's version-reader load names its file through one binding so the installer's closure, which now reaches it through the provisioner, can name it; behavior is
unchanged. Suite 110_veldo_0143_new_project carries the rows; finding 143 registers nine mutations, the three
declared falsifiers first. A factory set up before this change keeps its factory project on the workspace; a
re-run neither moves it nor requires the factory repository. Acceptance criteria, risk, readiness and approval
requirements are unchanged.
