# VELDO-0143: a repository the owner asks for in chat, created or adopted and bound to a new project on his one answer

Branch agent/claude/veldo-0143, built on VELDO-0161 (da39f3fb) and VELDO-0153 (b44736c0), neither landed yet.
Code commits cf1e81b9, 87b0c00a, f96e1407 and bf6c3911. Nothing here is a gate result, a review verdict or an approval.
The full gate, the factory PM run row and the setup suites are the host's to run (Host runs, below).

## What was built

| Piece | Where |
| --- | --- |
| The factory PM's new-project document; the one proposal derived from it (repository uuid, directory under the identity's projects root, remote under the identity's owner and its visibility, the adoption proposal with its scaffold commit for a directory that is already a Git repository, the default team's current revision, the default pipeline, charter, authority policy, budget); its brief; the nothing-asked rule; the one presentation; his answer (an offered identity named in it resolves the proposal); his correction read by the factory PM; the one judge of a settled decision; the activation chain | `engine/.veldo/control_project_proposal.py` |
| The provisioner's creation steps: directory, init, scaffold, author, commit, the GitHub REST remote (standard library, VELDO-0153's owner check first, the token from the keystore, an existing remote refused, GitHub's answer checked against owner, name and visibility), the identity-profile push | `engine/.veldo/control_repository_creation.py` |
| The registered protected effect `repository_provisioning`: settlement first, each step recorded, stopping by name; the adoption path for an existing repository; the VELDO-0161 adoption tail (refactored into `enroll`, its anchors unchanged) | `engine/.veldo/control_effect_executor_creation.py`, `control_effect_executor_adoption.py` |
| Repository records of origin `created`, the creation error taxonomy, new-project decisions judged by the one judge | `engine/.veldo/control_repository.py` |
| Activation from the decision, refused until the repository is active (also inside the transaction) | `engine/.veldo/control_project.py` (`activate_decided`) |
| The first objective accepted by the decision; its work admitted at the default priority with no question | `control_objective.py` (`accept_decided`), `control_grooming_request.py`, `control_backlog.py` |
| The message moved into the new project as its first objective proposal | `control_intake_routes.py` (`resolve_new_project`) |
| The factory PM run for a NEW_PROJECT message or a correction; the factory project's cycles on the factory line | `control_workflow_cycle_pm.py` |
| The running service: applies answers, starts the provisioner, fails a decision whose repository failed, activates once the repository is active (accepted base revision, the team's capability configurations at the named revisions, activation, first team, objective), gains the repository's line | `control_service_projects.py`, `control_service.py` |
| The owner told "<name> is ready; the first objective is next" (or why it could not be set up) by a VELDO-0128 report of the decision | `control_telegram_report.py` (`project_ready`) |
| Setup: the factory project's own repository at <state root>/factory holding only team.json, enrolled, bound, the factory project activated on it; host/provisioner.json | `control_factory_setup.py`, `control_factory_setup_dispatch.py` |
| The new modules in the scaffold's file list; one load site named so the installer's closure resolves it | `init_scaffold.py` |
| Suite `110_veldo_0143_new_project`; finding 143 (nine mutations) | `scripts/suites/`, `scripts/check_teeth_mutations.py` |

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
`newproject143-ambient-push`.

**AC3** (the same settlement activates the project once the repository is active; first objective accepted and
admitted; the owner told; the first unit dispatched in the new repository). Rows: `activation/order`,
`activation/applied`, `activation/failed-activates-nothing`, `activation/admitted-without-question`,
`activation/new-line`, all green here. Declared falsifier `newproject143-activated-while-provisioning` turns
`activation/order` red. The dispatch of the first unit itself goes through the new line's Runner after the new
project's PM cycle elaborates the objective: that cycle needs the graph runtime, so here the row proves the line
(its own receiver configuration, workspace and Gate, the team's configurations readable in it, its accepted base
revision, the identity as the author of its units), and the host runs the cycle (see Host runs).

Falsifiers: `falsifiers.json`, run through the driver's own worker mode with `run_falsifiers.py` (the mutation
coordinator does not start in this sandbox): baseline before and after, each with only `pm/new-project-run` red;
all nine cases killed.

## How the suite behaves where it runs

- Settlement is real: VELDO-0068 terms, the VELDO-0064 inbox, the VELDO-0065 presenter over a loopback Bot API,
  the owner's answer through the API edge (proof/VELDO-0152/fixture.py's signed fixture).
- The owner's messages come through the real intake by Telegram and API request; the PM's route and new-project
  documents are supplied by the suite except in `pm/new-project-run`.
- GitHub is a loopback REST stand-in creating bare repositories that the identity wire maps the GitHub URLs to;
  every push goes through VELDO-0153's identity profile inside the hermetic fence. Where AF_UNIX is refused the
  fence runs without its recording SSH agent (printed), as VELDO-0161's suite does.
- The authority service's take-on and new-project pass run in this process over the same store.

## Dependency and consumer suites here (consumer-suites.json)

Run on this branch and on an archive of the starting commit in the same sandbox: every count is identical. Green:
46, 66, 68 (both), 69 (both), 72 (both), 73_0078, 73_0089, 75, 76, 77, 82, 84, 86_0168, 91_0151, 108, 26. Red
here identically on both trees: 71_0076 (worker launches), 83, 92, 93 (graph runtime), 73_0139, 85, 86_0189,
91_0167, 94, 96, 106 (user manager qualification), 109's four AC2 rows (AF_UNIX), 71_0130 (install refused).

Static checks run here: lint, template sync, generated (requires.json regenerated), validate.py all; the
installer's closure derivation resolves with the new modules.

## Host runs (required before review)

1. `bash scripts/verify.sh` (full gate, both legs, mutation stage).
2. `python3 scripts/selftest.py --suite 110_veldo_0143_new_project`: all rows green, `pm/new-project-run` included.
3. `python3 scripts/check_teeth_mutations.py --finding 143`: all nine cases killed.
4. The setup suites this change touches: 73_veldo_0139_factory_setup, 106_veldo_0185_dispatch_setup (its
   fresh/team row now expects the factory project's own repository), 85_veldo_0171_setup_api,
   91_veldo_0167_setup_records, 86_veldo_0189_engine_upgrade (the installed closure gains eight modules).
5. The service and loop suites: 66_veldo_0047_authority, 83_veldo_0154_factory_loop, 92_veldo_0088_pm_cycles,
   93_veldo_0152_intake_routes, 94_veldo_0162_configuration_routes, 96_veldo_0204_reservation_policies,
   71_veldo_0076_projects, 71_veldo_0130_api, and 109_veldo_0161_adoption with `--finding 161` (the adoption
   effect was refactored).
6. A live qualification on the owner's host, not run anywhere: a real GitHub token per identity creating a real
   repository, and a new project's first unit built end to end through the factory loop.

## Assumptions and limits

- VELDO-0161 and VELDO-0153 are this branch's base and are not landed; this lands after them.
- A correction is read by the factory PM: the corrected proposal settles the decision without being shown to him
  again, as the criterion says ("a yes or a correction ... no further question").
- "Registered protected effect" is read as the named effect `repository_provisioning` the running service alone
  starts, with the trusted supervisor-side configuration; it is not a VELDO-0028 worker-requested handle.
- The factory project's own repository is no line; its cycles run on the work configuration's first line.
- A factory set up before this change keeps its factory project on the workspace, and has no provisioner
  configuration until set up anew; new-project decisions there wait, refused unavailable_service:provisioner.
- Independent critical-risk review and the owner's approval are outstanding.
