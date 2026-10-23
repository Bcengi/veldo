# VELDO-0143: a repository the owner asks for in chat, created or adopted and bound to a new project on his one answer

Branch agent/claude/veldo-0143, rebased onto VELDO-0161 round 5 (8f749423, reviewed sound) and so on VELDO-0153,
neither landed yet. Code commits f993e8d7, 4689067d, bc81c1b8 and dfeb0eca (round 1's, replayed), and d859b3db (the
adaptation to VELDO-0161's final design). The rebase, each conflict and its resolution: REBASE.md. The
specification's words this branch had to interpret, for the reviewer to judge: DECISIONS.md. Evidence of the
rebased branch: rebase/. The round-1 evidence (falsifiers.json, observations.json, consumer-suites.json) is kept as
it was, for the round-1 tree. Nothing here is a gate result, a review verdict or an approval.
The full gate, the factory PM run row and the setup suites are the host's to run (Host runs, below).
Round 2, the host's failures at a07ad991, each cause, fix, row and falsifier, and the host runs it needs: round2/README.md.

## What was built

| Piece | Where |
| --- | --- |
| The factory PM's new-project document; the one proposal derived from it (repository uuid, directory under the identity's projects root, remote under the identity's owner and its visibility, the adoption proposal with its scaffold commit for a directory that is already a Git repository, the default team's current revision, the default pipeline, charter, authority policy, budget); its brief; the nothing-asked rule; the one presentation; his answer (an offered identity named in it resolves the proposal); his correction read by the factory PM; the one judge of a settled decision; the activation chain | `engine/.veldo/control_project_proposal.py` |
| The provisioner's creation steps: directory, init, scaffold, author, commit, the GitHub REST remote (standard library, VELDO-0153's owner check first, the token from the keystore, an existing remote refused, GitHub's answer checked against owner, name and visibility), the identity-profile push | `engine/.veldo/control_repository_creation.py` |
| The registered protected effect `repository_provisioning`: settlement first, the adoption effect's lock and INTERRUPTED rule, every store and host refusal before anything is made, each step recorded, stopping by name, the repository's own configuration judged before GitHub is asked; the adoption path for an existing repository (VELDO-0161's `adopt`, unchanged); the adoption's end (`preflight`, `enroll`) and the synchronous hand-off to the running service (`take_on`) | `engine/.veldo/control_effect_executor_creation.py` (the adoption effect is VELDO-0161's, byte for byte) |
| Repository records of origin `created`, the creation error taxonomy, new-project decisions judged by the one judge | `engine/.veldo/control_repository.py` |
| Activation from the decision, refused until the repository is active (also inside the transaction) | `engine/.veldo/control_project.py` (`activate_decided`) |
| The first objective accepted by the decision; its work admitted at the default priority with no question | `control_objective.py` (`accept_decided`), `control_grooming_request.py`, `control_backlog.py` |
| The message moved into the new project as its first objective proposal | `control_intake_routes.py` (`resolve_new_project`) |
| The factory PM run for a NEW_PROJECT message or a correction; the factory project's cycles on the factory line | `control_workflow_cycle_pm.py` |
| The running service: applies answers, starts the provisioner (its end seen on its output pipe in the serve loop's poll set), answers its take-on, fails a decision whose repository failed, activates once the repository is active (accepted base revision, the team's capability configurations at the named revisions, activation, first team, objective), gains the repository's line; the pass runs only when an event made it due | `control_service_projects.py`, `control_service.py` |
| The owner told "<name> is ready; the first objective is next" (or why it could not be set up) by a VELDO-0128 report of the decision | `control_telegram_report.py` (`project_ready`) |
| Setup: the factory project's own repository at <state root>/factory holding only team.json, enrolled, bound, the factory project activated on it; host/provisioner.json | `control_factory_setup.py`, `control_factory_setup_dispatch.py` |
| The new modules in the scaffold's file list; one load site named so the installer's closure resolves it | `init_scaffold.py` |
| Suite `110_veldo_0143_new_project`; finding 143 (sixteen mutations) | `scripts/suites/`, `scripts/check_teeth_mutations.py` |

Each `.veldo/` copy is byte-identical to its engine file (template sync). Files outside the original footprint
are added to it in the specification with the reason for each (its history, 2026-10-22).

## Per criterion

**AC1** (one proposal from the factory PM, settled by his one answer; nothing asked when his message named the
project and the identity). Rows: `factory/own-repository`, `intake/new-project-routed`, `proposal/nothing-asked`,
`proposal/fields`, `proposal/one-answer`, `proposal/correction`, `proposal/refusals`, all green here, and
`pm/new-project-run` (the factory loop's real PM cycle through the Runner and the launch receiver on a fake
engine), red here by name: the cycle's graph needs the installed runtime (`runtime_unavailable`, as VELDO-0152's
route rows are red here). Declared falsifier `newproject143-presented-when-named` turns `proposal/nothing-asked`
red. Also killed: `newproject143-second-question` (`proposal/correction`), `newproject143-factory-repository-unbound`
(`factory/own-repository`).

**AC2** (created only on a settled answer, step by step, each recorded, stopping by name). Rows:
`provision/settlement-required`, `provision/created`, `provision/answered-and-corrected`,
`provision/directory-not-empty`, `provision/adoption-path`, `provision/step-failures` (each of init, scaffold,
author, commit, the token, an existing remote, GitHub answering another owner, a refused creation and a refused
push fails the record at that step with no later step run; the author and commit failures are injected by
replacing that step's function in the effect's step table, the others are real conditions), `provision/observed`,
`service/provisions` (the running service starts the registered effect as its own process). All green here.
Declared falsifier `newproject143-provisioner-unsettled` turns `provision/settlement-required` red. Also killed:
`newproject143-directory-overwritten`, `newproject143-step-failure-continues`, `newproject143-remote-owner-unchecked`,
`newproject143-ambient-push`. On the rebased branch also: `provision/checks-before-creation` (an adoption signer
this host does not enroll refused before any directory exists; a repository configuration naming a command
refused before GitHub is asked), `provision/interrupted` (a record left provisioning with no binding failed
`unknown_outcome:interrupted`; a live run's lock refuses, touching nothing), `provision/handed-over` (the
created repository handed to the running service and answered synchronously, active before the provisioner
returns) and `service/hand-off` (the same from the service-started provisioner over a real socket; red by name
here, AF_UNIX refused). Killed: `newproject143-checks-after-creation`,
`newproject143-configuration-unchecked-before-remote`, `newproject143-interrupted-left-provisioning`,
`newproject143-live-run-unheld`, `newproject143-take-on-not-sent`, `newproject143-take-on-not-due`,
`newproject143-provisioner-end-unseen`.

**AC3** (the same settlement activates the project once the repository is active; first objective accepted and
admitted; the owner told; the first unit dispatched in the new repository). Rows: `activation/order`,
`activation/applied`, `activation/failed-activates-nothing`, `activation/admitted-without-question`,
`activation/new-line`, all green here. Declared falsifier `newproject143-activated-while-provisioning` turns
`activation/order` red. The dispatch of the first unit itself goes through the new line's Runner after the new
project's PM cycle elaborates the objective: that cycle needs the graph runtime, so here the row proves the line
(its own receiver configuration, workspace and Gate, the team's configurations readable in it, its accepted base
revision, the identity as the author of its units), and the host runs the cycle (see Host runs).

Falsifiers: round 1 `falsifiers.json` (nine of nine); rebased branch `rebase/falsifiers.json`, sixteen of sixteen
killed, run through the driver's own worker mode with `run_falsifiers.py` (the mutation coordinator does not start
in this sandbox), baseline before and after red only on `service/hand-off` and `pm/new-project-run`.

## How the suite behaves where it runs

- Settlement is real: VELDO-0068 terms, the VELDO-0064 inbox, the VELDO-0065 presenter over a loopback Bot API,
  the owner's answer through the API edge (proof/VELDO-0152/fixture.py's signed fixture).
- The owner's messages come through the real intake by Telegram and API request; the PM's route and new-project
  documents are supplied by the suite except in `pm/new-project-run`.
- GitHub is a loopback REST stand-in creating bare repositories that the identity wire maps the GitHub URLs to;
  every push goes through VELDO-0153's identity profile inside the hermetic fence. Where AF_UNIX is refused the
  fence runs without its recording SSH agent (printed), as VELDO-0161's suite does.
- The authority service's take-on and new-project pass run in this process over the same store. The
  provisioner's hand-off reaches it through control_client's Authority judging the request in process
  (`provision/handed-over`); `service/hand-off` serves a real socket in the suite's loop where AF_UNIX is allowed.
  Rows provisioned with no service running see the hand-off named `not_taken_on:authority_unavailable` and the
  record taken on at an instance's start, VELDO-0161's path for that case.

## Dependency and consumer suites, static checks and host runs

Round 1: `consumer-suites.json` (against da39f3fb). Rebased branch: `rebase/consumer-suites.json` (against
8f749423) and `rebase/suite-109.json`; the results and the host run list are in REBASE.md (Results, Host runs).

## Assumptions and limits

- VELDO-0161 (round 5) and VELDO-0153 are this branch's base and are not landed; this lands after them.
- Each interpretation of the specification's words is listed in DECISIONS.md for the reviewer to judge.
- A provisioner started by an earlier instance of the service that fails after a restart is seen at the new
  instance's next pass, not at once (REBASE.md, Known limit).
- A correction is read by the factory PM: the corrected proposal settles the decision without being shown to him
  again, as the criterion says ("a yes or a correction ... no further question").
- "Registered protected effect" is read as the named effect `repository_provisioning` the running service alone
  starts, with the trusted supervisor-side configuration; it is not a VELDO-0028 worker-requested handle.
- The factory project's own repository is no line; its cycles run on the work configuration's first line.
- A factory set up before this change keeps its factory project on the workspace, and has no provisioner
  configuration until set up anew; new-project decisions there wait, refused unavailable_service:provisioner.
- Independent critical-risk review and the owner's approval are outstanding.
