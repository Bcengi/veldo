# VELDO-0143 round 3: rebased onto VELDO-0161 round 9, and the first independent review's findings

Branch agent/claude/veldo-0143, rebased onto 928918a5 with no conflicts (`REBASE.md`). The review is
`../REVIEW-claude-2026-10-23.md`, added as written. Round 3's commits: 223936c3 (rebase evidence, review),
2be2d2f8 (F1, F2, F3, F4, F6 and their rows), 74ce781d (F5's rows, the thirteen new mutations), then this
evidence, DECISIONS 17 to 22 and the specification's history. Nothing here is a gate result, a review verdict or
an approval.

This sandbox refuses AF_UNIX, has no systemd user manager and may not write the account's graph stage; suite 110
runs here through `../round2/sandbox_run.py --stage --agent` (the graph stage and the recording SSH agent stood
in). The full gate (`scripts/verify.sh`) cannot run here: its nested agent sandbox refuses to start.

## Results here

- Suite 110 at 74ce781d (`110-head.json`): 64 passed; red: service/hand-off (AF_UNIX, the host's) and
  activation/first-unit (F5, an open defect, below). At the rebased head before round 3, bf6c44ac: 50 passed,
  red only service/hand-off (`110-rebased.json`).
- Finding 143 (`falsifiers-143.json`, `../run_falsifiers.py`, worker mode, no stand-ins): 31 registered, 30 killed,
  each target row red on its mutant and green at baseline. `newproject143-scaffold-not-laid` is not judged here
  (its row, suite 66 authority/installed-assets, needs the user manager). Baseline before and after: red only
  service/hand-off, pm/new-project-run (the graph stage, which worker mode does not stand in) and
  activation/first-unit.
- Consumer suites, the 0161 base 928918a5 against this branch at 74ce781d, one after the other here
  (`consumer-suites.json`, archives; `consumer-suites-git.json`, clones for 16 and 24): 38 suites, 37 with the
  same result on both trees. Suite 24 has the same nine rows red on both (its nested gate cannot run here); one of
  those rows embeds each composed pack's file count, five more on the branch (control_project_proposal,
  control_service_projects, control_repository_creation, control_effect_executor_creation, init_scaffold).

## Each finding: fix, row, falsifier

| Finding | Fix | Row (red without the fix) | Registered mutation, here |
| --- | --- | --- | --- |
| F1 high | `NewProjects` calls `notify` after every decision it writes; the service's pass makes itself due for a write outside the pass (control_service_projects `written`) | service/pm-settled-due: his own message and his correction, each settled through `ProjectCycles.apply` as a loop pass applies the PM's run, make the pass due with no other event; the serve loop's check starts the provisioner for each; both projects activate | newproject143-pm-settled-not-due: killed |
| F2 high | `correction_problems` (name, identity, visibility, mode, an adoption only as shown) in `correct()` before anything is built and in the judge; an approval naming no offered identity fails `invalid_input:answer:identity` | proposal/correction-bound: a bare "yes", and a PM document changing the identity, the visibility, the mode (an adoption he was not shown: nothing laid in that repository) or the name, each fail the decision by name; a correction that says each change settles; a settled correction forged around `correct()` is refused `no_settled_decision:correction:identity` and the provisioner touches nothing | newproject143-correction-identity-unbound, -visibility-unbound, -mode-unbound, -name-unbound, newproject143-bare-yes-corrected, newproject143-judge-correction-unbound: each killed |
| F3 medium | `name_taken` (projects and live decisions, without case) in `build()` and before it in `propose()`/`correct()`: `stale_subject:project_exists`, the decision failed; `activate()` fails the decision `already_exists` | proposal/name-taken (another live decision's name, "Driftwood"); activation/name-taken (an existing project's name; a project of the same name activated meanwhile fails the decision once, reported) | newproject143-name-not-one-project, newproject143-taken-left-settled: killed |
| F4 medium | the decision is written `presenting` (proposal, alias, deadline) before `_present`; `resume()` at the pass finishes it from the record | proposal/presentation-interrupted: a store refusal on the `presented` write and a crash inside the presentation both leave `presenting`; the next pass presents each with the same proposal, each question reaches him once, his answer settles it | newproject143-presentation-not-resumed: killed |
| F5 medium | the pass's activation event names the line it added | activation/line-from-pass: with the factory loop attached, the pass that activates the project gives the loop the repository's line, with its workspace, Gate and the first line's roles | newproject143-line-not-added: killed |
| F5 (AC3) | none: an open defect, below | activation/first-unit: red | none |
| F6 low | `propose()` fails the decision `unavailable_service:provisioner` when no provisioner configuration is installed (nothing presented or settled); a settled decision whose service has none is failed the same way, not left waiting | proposal/no-provisioner: his message that named both and one that asked, neither settled nor presented, both reported "could not be set up" naming the reason; a settled decision on a service with none failed by name | newproject143-proposed-without-provisioner, newproject143-settled-left-waiting: killed |

Every pre-existing row still holds; pm/new-project-run's service names the provisioner configuration (F6), and
newproject143-second-question follows `_present`'s new arguments.

## F5: the first unit is not dispatched in the new repository (open, needs the owner)

activation/first-unit drives AC3's observation through the real loop: a project activated by the pass with the
factory loop attached, its line added, a unit of that project claimed by the builder, the loop's pass, a fake
engine that commits in its workspace with an author planted in its environment. It is red here, and on a host it
will be red the same way: the loop's pass faults the new line (`unknown_outcome:Refused`) and offers nothing.

**Cause.** `Line.run` builds the line's project cycles (`control_workflow_cycle_pm.from_line`) on the service's
one connection. Their owners register once per connection: `control_alias.attach` refuses a second allocation
authority (`invalid_registration: connection already has an allocation authority`, the row's detail),
`control_readset.attach` a second snapshot authority, and `control_grooming` requires the channel's connection.
Backlog, team and intake owners re-register silently, so the last line's would also take the first's commands.
A factory's first line always runs the factory project's cycles, so the line of every new project is the second
and never runs. This is VELDO-0154/0088's single-line assumption, not 0143's code, but AC3's "the first unit
dispatched in the new repository" depends on it.

**What holds once that is solved.** With the new line's cycles stood in (a scratch replacement in the run script,
not in the suite: `110-first-unit-cycles-stood-in.json`), the row's other parts are green: the unit is offered
on the new line to the builder, dispatched through its Runner, its packet names the new repository, its build
follows that repository's commit, and the commit is authored and committed by the identity alone, the planted
author stripped.

**Not fixed here.** Two attempts in `from_line` were reverted: one shared, extended allocation authority (the
read sets then refuse), and a store connection per later line (grooming then refuses: the channel's presenter,
inbox and settlement live on the service's connection). A real fix routes the per-line owners on one connection,
or gives each line its own channel services. That is a design change in modules outside this specification's
footprint (control_alias, control_readset, control_grooming, control_backlog, control_team), and so the owner's
decision: widen 0143, or a VELDO item of its own that 0143's AC3 depends on.

## Host runs

1. `python3 scripts/selftest.py --suite 110_veldo_0143_new_project`: every row green except
   activation/first-unit (F5, expected red, named). service/hand-off, provision/signing-no-agent with its recording
   socket, pm/new-project-run, service/pm-settled-due on a host with AF_UNIX (its provisioners then reach for the
   closed socket of service/provisions and wait for an instance's take-on).
2. `python3 scripts/selftest.py --suite 66_veldo_0047_authority`: every row green, authority/installed-assets included.
3. `python3 scripts/check_gate_mutations.py --finding 143`: 31 of 31 killed.
4. `python3 scripts/check_gate_mutations.py --finding 161`: 57 of 57 (VELDO-0161 round 9), not re-run here.
5. Each consumer suite this sandbox could not judge (red on both trees here, or stopping before its rows), at this
   branch's head and at 928918a5: 106_veldo_0185_dispatch_setup, 66_veldo_0047_authority, 71_veldo_0076_projects,
   71_veldo_0130_api, 73_veldo_0139_factory_setup, 83_veldo_0154_factory_loop, 85_veldo_0171_setup_api,
   86_veldo_0189_engine_upgrade, 91_veldo_0167_setup_records, 92_veldo_0088_pm_cycles, 93_veldo_0152_intake_routes,
   94_veldo_0162_configuration_routes, 96_veldo_0204_reservation_policies, 66_veldo_0051_events,
   64_veldo_0050_proof, 107_veldo_0153_identity_push (no table here), 109_veldo_0161_adoption (four AF_UNIX rows),
   24_veldo_0007_install_and_run (nested gate).
6. `bash scripts/verify.sh`: red until F5 is decided.
