# VELDO-0076 proof

Release 1 stage 4: the enrolled owner activates a project with a real signed command that binds its owner,
charter, one execution repository, authority policy and a finite coordination budget; a pause or cancel
stops the frontier's offers and every dispatch of the project while running work gets the host's
ordinary stop; completion waits until every objective is terminal and every ordinary obligation is
resolved. Specification status, risk and `.veldo/policy.yaml` are unchanged. This proof is for
independent review; it is not a self-approval, and the canonical gate is run by the lead, not recorded
here.

## What was built

- **`.veldo/control_project.py` (new).** The project service: the only writer of `project:<name>`
  records (it declares the `project` kind and the `project:` id prefix through
  `control_store.declare_owners`). Every operation is a
  signed command `{'command', 'signature'}` verified against the principal's active key; the principal
  must be an active person holding `project_owner` in a scope covering the project, and after
  activation the owner the record names. Every transition is asked of `entity_contract.transition` on
  the R05 vocabulary with the evidence the service established. `activate` binds `ACTIVATION_FIELDS`
  (owner, charter, execution repository, authority policy, coordination budget) and refuses an omitted
  field as `missing_field:<field>`, an unbounded budget as `unbounded_budget:<unit>`, a policy role no
  current person holds in the project's scope as `inapplicable_policy:<touchpoint>/<role>`. `pause` and
  `cancel` record the project's accepted or running dispatches in `stopping` and then ask the host's
  ordinary stop of each (`runner_stop(runner)`: the VELDO-0039 Launch's cooperative stop and the
  containment group's escalation). `resume` judges the activation predicates again. `complete` reads,
  inside its own transaction, every objective, assignment, governing decision (the Gate's
  `decision_blockers` over the same connection and the configured settlement trust), dispatch,
  release execution and reservation of the project and refuses `open_obligation:<kind>` naming each
  open one. Each transition appends one `history` entry and changes no earlier one.
- **`.veldo/control_eligibility.py`.** `Gate._unit_problems` refuses a unit whose project record
  carries a lifecycle state other than ACTIVE (`project_not_active:<state>`, classified
  missing_authority). Every station asks it, so the frontier offers nothing from a paused or canceled
  project and a claim, the runner's preparation and the receiver's recheck refuse; a ticket issued
  before the pause is also stale. A project record with no lifecycle state (written before the service
  existed; the service is now the kind's only writer) is not judged by this rule. This path was added to
  the footprint, with a History line: the frontier's own footprint file could not stop a dispatch.
  Review fixes: the project is judged only from a record of kind `project` (any other kind at the
  project's id refuses `project_not_active:not_a_project`), and an ACTIVE project whose recorded owner
  is not a current person member holding `project_owner` in its scope refuses
  `project_not_active:owner_not_current`, since only that owner may stop it (VELDO-0138's fail-safe;
  handover is Release 3). The owner's membership record is a consumed input (`project_owner`).
- **`.veldo/init_scaffold.py`.** Installs `control_project.py`. Engine copies are byte-identical.

The frontier, `request.py` and `authorization.py` are unchanged: the frontier already asks the Gate at
its selection station for every offer.

## Rows, falsifiers and red records

Suite `scripts/suites/71_veldo_0076_projects.py` (about 3 s): the real SQLite store with OpenSSH
command, journal and decision settlement signatures, the VELDO-0064 inbox, VELDO-0036 reservations, the
VELDO-0031 claim transition, the VELDO-0052 Gate and the real frontier over spec files, the VELDO-0039
runner with real receiver and fixture worker processes in their own systemd containment groups, and a
reader in another process. It also passes in the stage environment (`env -i`, empty HOME,
`GIT_CONFIG_GLOBAL=/dev/null`).

`red-at-8d6715b.json`: the suite against the pre-change tree (`git archive 8d6715b`): every criterion
row red by assertion (the tree has no project service, so nothing activates, pauses or completes, and
its Gate refuses every unit for want of a project record).

`red-at-93a56d6.json`: the current suite against the tree before the review fixes: exactly
`project/foreign-kind`, `project/owner-demoted` and `project/owner-revoked` red by assertion (a
generic upsert of another kind at `project:proj-x` was accepted, admitted the unit and dispatched it,
and blocked the owner's activation; a demoted or revoked owner's unit was admitted and dispatched).

`python3 -B proof/VELDO-0076/drive.py` regenerates `mutations.json` and the diffs: 21 mutants, each reds
its named row by assertion, the baseline and a no-op copy of each mutated module green. Registry:
`scripts/check_teeth_mutations.py --finding 76`.

| Row | Criterion | Mutations (declared falsifier first) |
| --- | --- | --- |
| `project/unbounded-budget` | AC1 | `budget-predicate-skipped` |
| `project/activation-fields` | AC1 | `omitted-policy-activates` |
| `project/activation-authority` | AC1 | `non-owner-activates`, `signature-unverified` |
| `project/one-active` | AC1 | `second-activation-replaces` |
| `project/paused-frontier` | AC2 | `frontier-offers-paused-project` |
| `project/paused-dispatch` | AC2 | `paused-project-dispatches` |
| `project/stop-policy` | AC2 | `pause-stops-nothing` |
| `project/history-preserved` | AC2 | `pause-rewrites-history` |
| `project/cancel` | AC2 | `canceled-project-resumes` |
| `project/resume` | AC2 | none |
| `project/open-objective` | AC3 | `objective-ignored-at-completion` |
| `project/open-assignment` | AC3 | `assignment-ignored-at-completion` |
| `project/open-decision` | AC3 | `decision-ignored-at-completion` |
| `project/open-dispatch` | AC3 | `dispatch-ignored-at-completion` |
| `project/open-reservation` | AC3 | `reservation-ignored-at-completion` |
| `project/complete-resolved` | AC3 | none (the positive case each open-* row is judged beside) |
| `project/foreign-kind` | review | `project-kind-unchecked`, `project-prefix-unowned` |
| `project/owner-demoted` | review | `owner-currency-unchecked`, `demoted-owner-current` |
| `project/owner-revoked` | review | `owner-currency-unchecked`, `revoked-owner-current` |
| `install/assets` | all | `project-not-scaffolded` |
| `project/observability` | all | none |

## What each criterion's rows drive

**AC1.** Each field the specification names is omitted in turn from a real signed activation and
refused by its name with nothing written; the complete one creates one ACTIVE record with every field as
signed, read back in another process. Eleven authority shapes are refused by name (no role, another
scope, revoked, a signature by another key, an owner other than the signer, a service principal, a
policy role nobody holds, an empty or unknown-role policy, an empty charter, another repository), and
twelve unbounded budgets (none, empty, a missing required unit, infinity, NaN, unset, negative, zero, a
boolean, text, an unknown unit). A second activation refuses `already_exists` and a generic store
upsert of a project record refuses `entity_owned`.

**AC2.** Project A has a ready unit the frontier offers, a unit running in a real contained worker, a
prepared but unlaunched contract and a landed completion receipt; project B has a ready unit. The pause
records the running dispatch, asks its receiver to stop (the supervision's cause is `requested`, the
record ends exited, the worker process is gone, its slot is retired as cancelled), the frontier offers
only B's unit and names `project_not_active:PAUSED` for A's, a new submit of A's work refuses by that
name with no dispatch record, and the contract prepared before the pause is refused by its receiver
without launching. Every journal record before the pause is unchanged, the pause's record touched only
the project, the receipt is unchanged and the history keeps its activation. Resume offers and
dispatches A's work again; cancel stops the new running dispatch the same way, refuses resume as
`invalid_transition:CANCELED->ACTIVE`, keeps every history entry, and another process reads it.

**AC3.** Project C is refused completion, separately, with an ACTIVE objective, an OFFERED inbox
assignment (a real signed open), an unsettled governing decision on one of its units, a dispatch the
runner prepared (named with the worker slot it holds) and a lone worker slot; each refusal names exactly
its open obligation and writes nothing. Each is then resolved through its ordinary path (the objective
satisfied, the requester's signed cancel, an OpenSSH-signed approving settlement the trusted verifier
accepts, the receiver launching and the runner retiring the slot, the reservation service retiring the
lone slot); completion is then accepted at the activation version plus one, keeps its history and bound
fields, is terminal, and another process reads it.

**Review fixes.** A generic signed upsert of kind `note` at `project:proj-x` refuses `entity_owned`,
the unit of proj-x is not admitted (`missing_authority:project`) and its dispatch refuses by that name,
then the owner activates proj-x and its unit is admitted. In a second store no project service declared
into, a `note` record at a unit's project id refuses exactly `project_not_active:not_a_project` while a
`project` record beside it raises no project refusal. Project proj-z is active under zed; with zed's
`project_owner` role removed he can no longer pause it and the Gate refuses its unit exactly
`project_not_active:owner_not_current` with its dispatch refused by that name; restoring the role
admits it again. The same with zed revoked, and after restoring the membership the unit dispatches and
its worker exits.

## Checks run

Findings whose modules changed still reject: 52, 53, 54, 134 (`control_eligibility.py`), 52, 54, 135
(`frontier.py`, unchanged but loading the Gate) and 39, 40, 41, 42, 45, 47, 50, 51, 67, 68, 73
(`init_scaffold.py`). Every suite that loads `control_eligibility.py` passes.
