# VELDO-0077 proof

Release 1 stage 4: an owner message becomes an objective of one project through the common intake, the
project's current owner accepts it through the settlement, and that acceptance binds its exact outcome,
scope, authority and evidence requirements. Features proposed under an accepted objective are neither
admitted nor prioritized by it. Only the bound assessor's signed assessment of the accepted revision,
over kept evidence records, satisfies it. Cancellation needs the owner's explicit disposition of every
unfinished feature and keeps history. Specification status, risk and `.veldo/policy.yaml` are unchanged.
This proof is for independent review; it is not a self-approval, and the canonical gate is run by the
lead, not recorded here.

## What was built

- **`.veldo/control_objective.py` (new).** The objective service: the only writer of objective records
  and of the features under them (it declares the `objective` kind and the `objective:` and
  `objective-feature:` id prefixes through `control_store.declare_owners`). Every operation is a signed
  command verified against the principal's active key, and every transition is asked of
  `entity_contract.transition` on the R06 vocabulary.
  - `propose` takes a VELDO-0126 intake proposal of kind objective (state PROPOSED, one project) whose
    project is ACTIVE, and the bound fields: outcome, scope, authority (acceptor, the project's owner;
    assessor, an active person in the project's scope) and evidence requirements (an id and the kind
    of kept record that proves it). The record is PROPOSED at revision 1 with the digest of exactly those
    fields. `amend` gives a new revision and digest.
  - `accept` applies a VELDO-0068 settlement on the `decision_disposition` touchpoint. The settled
    effect's target must be `acceptance_target` of the objective's CURRENT revision, the request's brief
    must be `acceptance_brief` of that revision, and the request's owner and the settlement's only
    principal must be the bound acceptor, who is the project's owner and current. Otherwise it refuses
    `stale_subject:revision`, `stale_subject:brief` or `not_owner` and writes nothing.
  - `propose_feature` writes a RAW `backlog_item` under an ACCEPTED or ACTIVE objective, inside its
    accepted scope (`out_of_scope:<item>` otherwise), with no admission and no priority; the first one
    links the contribution (ACCEPTED -> ACTIVE).
  - `assess` is the bound assessor's signed assessment of the accepted revision: every evidence
    requirement names a kept record of its kind by id and entity digest, read inside the transaction,
    and a gate observation proves only with exit 0 (`missing_evidence:<id>`, `unproven_outcome:<id>`,
    `not_authorized:assessor`, `stale_subject:revision`). The receipt is completion_contract's
    `objective_satisfied` fact. `specifications()` reports the shipped status of the features'
    specifications and decides nothing.
  - `cancel` by the project's current owner needs a reason and a disposition of every unfinished
    feature (`release_floor_contract.objective_cancellation_problems`), each recorded by that owner:
    `stop` cancels the feature, `transfer` moves it to another accepted objective of the project.
    `reopen` asks the lifecycle for an edge back to PROPOSED, which R06 does not declare; continuation
    is a new objective whose `continues` names the terminal one.
  - An objective of a project that is not ACTIVE is not accepted, elaborated or satisfied.
- **`.veldo/init_scaffold.py`.** Installs `control_objective.py`. Engine copies are byte-identical.

`request.py` and `authorization.py` are unchanged: the path the running factory uses is the control
store's intake and settlement, and neither module is on it. `control_request_settlement.py` is
unchanged: its `decision_disposition` touchpoint already asks the project owner, one principal,
independent of the requester, and a non-governing target is carried to the effect as signed.

## Rows, falsifiers and red record

Suite `scripts/suites/72_veldo_0077_objectives.py` (about 2 s): the real SQLite store with OpenSSH
command, journal and API signatures, the VELDO-0076 project activated by its owner's signed command,
owner messages through the VELDO-0126 intake as requests the API edge signed, VELDO-0064 requests
presented by the VELDO-0065 presenter over a loopback Bot API and answered through the API edge into the
VELDO-0068 settlement, gate observations of real check processes kept by the VELDO-0050 proof service,
specification files in a workspace, and a reader in another process. It also passes in the stage
environment (`env -i`, empty HOME, `GIT_CONFIG_GLOBAL=/dev/null`).

`red-at-a0e76af.json`: the suite against the pre-change tree (`git archive a0e76af`): every row red by
assertion, no region raised (the tree has no objective service, so every command is answered
`no_objective_service`).

`red-at-86a58f0.json`: the current suite against the first build (`git archive 86a58f0`), by assertion,
no region raised: `satisfaction/stale-evidence` (a passing observation kept before the acceptance
satisfied the objective, so `satisfaction/unproven-outcome` and `satisfaction/other-process` follow it),
`cancel/transfer-bounded` (the out-of-scope transfer was accepted) and `project/inactive-refusals`
(amend worked in a paused project). The brief check alone and the paused refusals of accept,
propose_feature and assess were already correct there; their rows and mutants close the coverage gap.

`python3 -B proof/VELDO-0077/drive.py` regenerates `mutations.json` and the diffs: 23 mutants, each reds
its named row by assertion, the baseline and a no-op copy of each mutated module green. Registry:
`scripts/check_teeth_mutations.py --finding 77`.

| Row | Criterion | Mutations (declared falsifier first) |
| --- | --- | --- |
| `acceptance/later-feature` | AC1 | `feature-admitted-on-acceptance` |
| `acceptance/stale-answer` | AC1 | `stale-answer-accepted`, `brief-unchecked` |
| `acceptance/owner-only` | AC1 | `any-member-accepts` |
| `acceptance/bounded-elaboration` | AC1 | `feature-scope-unbounded` |
| `acceptance/intake-source` | AC1 | `feature-prefix-unowned` |
| `acceptance/binds-fields` | AC1 | none (the positive case the refusals are judged beside) |
| `satisfaction/unproven-outcome` | AC2 | `shipped-specs-satisfy` |
| `satisfaction/wrong-signer` | AC2 | `assessor-unchecked` |
| `satisfaction/stale-revision` | AC2 | `assessment-revision-unchecked` |
| `satisfaction/missing-evidence` | AC2 | `unsubmitted-evidence-skipped`, `assessment-evidence-digest-unchecked` |
| `satisfaction/stale-evidence` | AC2 | `pre-acceptance-evidence-counts` |
| `satisfaction/proven` | AC2 | none (the positive case) |
| `satisfaction/other-process` | AC2 | none (the read-only reader) |
| `cancel/work-disposition` | AC3 | `cancel-without-disposition`, `disposition-recorder-unchecked` |
| `cancel/history-kept` | AC3 | `cancel-rewrites-history` |
| `cancel/reopen-linked` | AC3 | `terminal-objective-reopens`, `continuation-of-live-objective` |
| `cancel/transfer-bounded` | AC3 | `transfer-scope-unbounded`, `transfer-keeps-source-revision`, `duplicate-disposition-accepted` |
| `project/inactive-refusals` | all | `inactive-project-elaborates`, `amend-in-inactive-project` |
| `install/assets` | all | `objective-not-scaffolded` |
| `observability` | all | none (pending work measured as the change the row's own objectives and feature make) |

## What each criterion's rows drive

**AC1.** Four owner messages reach the intake: one naming proj-a becomes a proposed objective, one
naming no project stays an inbox proposal, one names proj-b, which is not active, and one is proposed
with another member as acceptor; only the first is accepted by `propose`, a second `propose` of it
refuses `already_exists`, an intake source record refuses `no_such_proposal`, and a generic upsert at an
objective or feature id refuses `entity_owned`. The objective is presented at revision 1, the proposer
amends the outcome, the owner then answers the revision 1 request and it settles, and applying it
refuses `stale_subject:revision` with the record unchanged. A request addressed to zed (a project owner
in scope who is not proj-a's owner) settles on his answer and is refused `not_owner`. The request for
revision 2, answered by olga, accepts it: the record's bound fields equal the ones proposed and amended,
the settled effect's target is the accepted revision and digest, and the brief olga was shown carries
every bound field. A feature under the PROPOSED objective is refused; one under the accepted objective is
RAW with no admission and no priority, no admission record or settled effect names it, and a separate
admission request settles `work_admitted` on it while the feature itself stays RAW. A feature scoped
outside the accepted scope refuses `out_of_scope:loyalty`.

**AC2.** The declared set, each case on a real store: a person who is not the assessor and a service
are refused; an assessment missing one requirement, naming a record that does not exist, or naming a
kept record with another digest refuses `missing_evidence:regression`; an assessment of revision 1 when
revision 2 was accepted refuses `stale_subject:revision`. An assessment of the second objective over
passing observations the proof service kept before that objective was accepted refuses
`stale_subject:evidence`: the record's first journal sequence must follow the accepting command's. A second objective whose features' two
specifications are all shipped, with an outcome check that ran and exited 1, refuses
`unproven_outcome:outcome` and stays ACTIVE. The complete, current assessment by asha satisfies the first
objective with the `objective_satisfied` receipt of revision 2, and another process reads both states
read-only and verifies asha's signature with ssh-keygen.

**AC3.** A third objective with two RAW features is refused cancellation with no disposition, with one
of two dispositions, with dispositions recorded by someone else, and when signed by zed; nothing changes.
Olga's cancel stopping one feature and transferring the other to a fourth accepted objective is
accepted: the stopped feature is CANCELED with its disposition, the transferred one belongs to the
fourth objective, the objective keeps its acceptance, owner, accepted revision, features and every
earlier history entry, and the request, settlement, effect and receipt records are unchanged. Reopening
refuses `invalid_transition:CANCELED->PROPOSED`, amending it is refused, a continuation naming a live
objective refuses `invalid_input:continues`, and a new objective that continues the canceled one is
accepted while the canceled record stays byte-for-byte the same. A source objective accepted at
revision 1 and a receiver scoped to checkout, amended and accepted at revision 2: transferring the
payments feature refuses `out_of_scope:payments`, a disposition set naming one feature twice refuses
`invalid_input:duplicate_disposition`, neither writes anything, and transferring the checkout feature
moves it under the receiver with `objective_revision` 2 and leaves no canceled feature listed there.

**Inactive projects.** proj-a paused with a settled acceptance answer and fresh evidence waiting:
amend, accept, propose_feature, assess and a new objective refuse `project_not_active:PAUSED` and write
nothing, and the owner still cancels an objective. proj-a canceled: amend, propose_feature and assess
refuse `project_not_active:CANCELED`. proj-b activated and completed over a canceled objective: amend,
accept and a new objective refuse `project_not_active:COMPLETED`.

## Checks run

Every finding's `init_scaffold.py` mutation still rejects (39, 40, 41, 42, 45, 47, 50, 51, 67, 68, 73,
76, 138: 23 mutations), and findings 76 and 68 reject in full. Every suite that loads
`init_scaffold.py` passes (31 suites). `control_intake.py`, `control_request_settlement.py` and
`control_project.py` are unchanged, so findings 126, 68, 69, 133 and 76 are unaffected there.

## Stated limits

One project and one acceptor per objective; objectives spanning projects and additional owners are
Release 3. Units under a stopped feature are not reached by this service: it never admits a feature,
so none exists unless a later admission put one there (VELDO-0078). Recovery and restart are Release 2.
