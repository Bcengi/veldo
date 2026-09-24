# VELDO-0050 proof

Executor persists proof and performs complete contextual validation, PLAN-0019 revision 3 W35
(Release 1 stage 1). Branch `build-veldo-0050`, built on 91fb549. Specification status and every
other specification are unchanged.

## What landed

**The proof service** (`.veldo/control_proof.py`, engine copy identical, laid by the scaffolder).
Two store commands, each the only writer of its entity kind (`control_store.declare_owners` names
this file): `record_gate_observation` stores what the gate was observed doing (command, commit, gate
script digest, exit, the complete output and its digest) when it is captured, and `accept_proof`
stores one immutable bundle per unit and built commit. `resolve()` is the fresh reader: from the
store alone it re-derives the bundle from Git and the stored observation and requires it to equal
what was accepted.

**Contextual validation** takes the criterion set and the required evidence from the accepted spec
(the spec document at the run's base commit, by sha256), the check set from the installed catalog
(the required items of the canonical gate at that base) and the evidence kinds from the installed
validator. It reports every problem by name: empty, omitted, duplicate or invented mappings, a
criterion without evidence, an artifact absent or with another digest, a required kind not
evidenced, an implementation commit that is malformed, absent or not in the built commit's history,
the wrong spec revision or a spec the build changed, a missing or foreign producer, a missing,
altered or foreign observation, a gate with no exit 0 or no terminal GREEN line, a required check
not observed passing, and a claimed check the observation does not show.

**The executor.** With the floor enabled the proof step is assemble, validate and accept, and
acceptance comes before the run finishes built or enters review. `LiveLoop.gate` is green only on
exit 0, a terminal GREEN line for the commit it ran at, and every required catalog check observed
passing, and it records the observation. `LiveLoop.assemble_proof` uses the committed manifest when
the built commit carries one and never adds a default check. With the floor enabled the executor
emits only proof.recorded, review.requested and approval.recorded.

## Rows (suite `64_veldo_0050_proof`, 14 rows: 9 assertions and 5 `ran/` rows)

Real SQLite store with OpenSSH journal and review signatures, a work repository laid by the
scaffolder and running its own canonical gate, the eligibility Gate, VELDO-0036 reservations, the
VELDO-0031 claim transition, the VELDO-0049 floor authority, and real receiver, builder and reviewer
processes launched through VELDO-0039's runner under separate principals.

**AC1.** `proof/accepted-before-offer`: a dispatched build is accepted with journal order
observation, then acceptance, then the floor's build acceptance; proof.recorded names the bundle; a
second acceptance is refused `proof_immutable`, a generic write `entity_owned`; with no proof service
the same executor halts at proof. `proof/fresh-reviewer-resolves`: after the builder exited, a
reviewer process given only the floor's assignment resolves the bundle, and its manifest digest,
implementation commit, spec revision, artifact digests and checks match what the suite computes
from Git on its own.

**AC2.** `proof/contextual-refusals`: fourteen cases (empty, omitted, duplicate, invented,
nonexistent commit, empty with a nonexistent commit, the owner's earlier spec revision, missing and
foreign producer, wrong digest, missing evidence, absent artifact, unevidenced required kind, missing
observation) each refused with its own code and nothing stored; the valid proof is accepted, and its
derived sets equal the suite's own reading of the spec and the catalog.

**AC3.** `proof/actual-checks`: the bundle's checks are exactly the installed catalog's required
items as the gate printed them (unit and security, while the manifest claims only unit), with
command, gate exit and observation, and the stored output's digest matches its bytes.
`proof/no-default-success`: a red gate and a gate killed before its terminal line halt at gate with
no bundle and no proof.recorded; accepting the killed observation directly is refused for exit,
terminal, both checks and the unobserved claim; an altered and a foreign observation are refused;
the executor's assembly with no observation claims no check.

**AC4.** `proof/owning-services`: the full review path (direct execution, floor enabled) reaches
ready through the real events.emit; its events are exactly proof.recorded, review.requested and
approval.recorded by executor.py, every line in both logs has its type's producer, no
verdict.recorded is written, and the journal holds only the proof service's two commands for the
unit. `proof/build-only-no-landing`: a new process reads no completion fact, no completion receipt,
no landing event, the floor state review and the resolvable bundle.

**Also.** `proof/installed-assets` (the scaffold lays control_proof.py and its closure, and the laid
executor loads it) and `proof/observations` (counts, pending observed commits, refusals with their
taxonomy).

## Red at the pre-change code

`red.py 91fb549` writes `red-91fb549.json`. `prefix/executor.py` is 91fb549's executor.py byte for
byte plus a marked stand-in giving the new names their pre-change behaviour (`accept_proof` is
check_json over a temporary file, storing nothing); `prefix/control_proof.py` is a marked stand-in
that stores and resolves nothing; init_scaffold.py is the commit's own. Every other installed module
is identical to the commit. All 9 assertion rows fail and all 5 `ran/` rows pass. Observed: the
build halts at proof because the old assembly ignores the committed manifest and its checks are the
default passed unit check, check_json alone accepts 12 of the 14 contextual cases, nothing resolves
for the reviewer, and the scaffold lays no proof module.

## Mutations

24 registered as finding 50 in `scripts/check_teeth_mutations.py`. `mutations.py` drives them and
writes `mutations.json`, with each diff in `mutations/`. Each reds its named row by assertion and
that row's region completes; every row has at least two. Declared falsifiers:
`proof-kept-in-temporary-storage` (AC1), `proof-check-json-alone` (AC2), `proof-default-passed-check`
(AC3), `proof-executor-emits-verdict` (AC4).

## Costs

Suite 64: 4.7 to 5.5 s inside selftest at load average below 1; `drive.py` 5.4 s
(`observations.json` holds one run). Finding 50 with 4 jobs: 24 mutations in 39.6 s. Regression runs
with zero failures: 63_veldo_0049_floor, 62_veldo_0039_dispatch, 60_veldo_0052_eligibility,
60_veldo_0053_architecture, 58_veldo_0035_snapshots, 50_git_environment, 21_veldo_0004_promise_corpus,
01 through 06 and 13. The full gate is the lead's.

## Not done here, stated

Suite 03 pins the pre-factory executor emitting verdict.recorded through a fake emitter (the event
set and the human-minutes sum rows), so without a Gate the executor still hands it to `emit`, where
the real emitter refuses it; removing that needs suite 03's footprint. The floor authority
(dispatch.py, VELDO-0049) still accepts a build from the committed manifest and does not yet require
the stored bundle; with LiveLoop as the dispatcher's hooks the bundle always comes first, but hooks
that keep no proof service reach review. LiveLoop.review and LiveReviewer (VELDO-0129) must call
`resolve()`; the suite's reviewer is a fixture. Builders must now write `spec_revision` and evidence
entries `{type, path, digest}`; the proof skill does not yet. The gate runs in the workspace and must
be the base's verifier; isolation outside the candidate and signed Evidence Service receipts are
VELDO-0058. The observation keeps the complete gate output in the store, unbounded (resource use by
our own account is out of review scope). A direct run with review needs the unit's producer in its
accepted record (VELDO-0052), which the suite provisions as suites 60 do. Not run here: the Mac and
the full gate.
