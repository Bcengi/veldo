# VELDO-0035 proof

Implementation: accepted snapshots, complete transactional read-set registrations, and ordinary
materialization at an explicit local watermark. Specification remains **ready**. This bundle is
implementation evidence, not independent engineering review, owner approval, or service activation.

Canonical verification: pending the clean-tree `bash scripts/verify.sh` run. Its summary and
log digest will be recorded here; no full gate log is committed.

## Criteria and observed rows

The registered suite is `scripts/suites/58_veldo_0035_snapshots.py`. Its 27 assertions execute in the
full unit gate. `observations.json` retains its actual 45 stale-command outcomes, ten document
comparisons, eleven projection comparisons, and all assertion results. `drive.py` reproduces those
detailed diagnostic observations; a diagnostic or partial suite run does not verify this change.

| Criterion | Rows | What actually ran |
|---|---|---|
| AC1 | `snapshots/stale-input`; `snapshots/registration-inventory`; `snapshots/control/{upsert_entity,retire_entity,record_receipt,reserve,record_effect}`; `snapshots/refusal/{unregistered,missing-snapshot}`; `snapshots/refusal-observations` | Each of the five base store commands is enabled with explicit entity, collection and reference inputs. Nine different changes per command are committed through another real SQLite connection after snapshot acceptance: dependency target, authority version, new dependency edge, new blocker, previously absent entity, membership, delegation, verification key, and status. Every attempted consume refuses `stale_input`, with unchanged domain state and journal sequence. Each command also has a successful unchanged-input control. Missing snapshots and undeclared operations refuse before writing. Counters and pending snapshot identities are checked. |
| AC2 | `snapshots/accepted-bytes`; `snapshots/missing-artifact/{specification,plan,release,decision,floor,policy,graph,roster,admission,receipt}.md`; `snapshots/coordinates`; `snapshots/signed-watermark`; `snapshots/installed-assets` | Real Git commits and blobs, real SQLite snapshots, and real Ed25519 journal signatures. All ten document paths are edited and committed to a newer HEAD; reads still compare equal to the original accepted bytes. Removing each referenced Git blob refuses `missing_artifact` even though the checkout contains a replacement. Snapshot coordinates, all selected entity versions/digests, its signed journal watermark, and runtime asset registration are checked. |
| AC3 | `snapshots/materialized-revision`; `snapshots/tampered-projection`; `snapshots/incomplete-projection` | Ten documents plus one status projection are materialized after both HEAD and current store status have changed. A separate Python process opens the real store read-only, loads the accepted snapshot, and reads the published directory. Every member digest and watermark is compared with accepted store data. Edited output bytes and an absent completion manifest refuse explicitly. |

## Driven negative controls

Every case is registered in `scripts/check_teeth_mutations.py`, finding 35, and therefore in the
required `check_gate_mutations.py` stage. Each edits a temporary production copy. Baseline and
byte-identical no-op copies remain green. All named failures below are completed assertions,
not exceptions, missing rows, timeouts, or hung processes. Exact edits are the adjacent `.diff`
files; `mutations.json` records target observations, actual red rows, and before/after digests.

| Criterion | Mutation | Named assertion turned red |
|---|---|---|
| AC1 declared falsifier | `snapshot-project-only`: validate only project input after other inputs change | `snapshots/stale-input` |
| AC1 second mutation | `snapshot-ignore-collections`: omit collection comparisons, admitting a newly inserted blocker | `snapshots/stale-input` |
| AC2 declared falsifier | `snapshot-checkout-bytes`: return edited checkout bytes | `snapshots/accepted-bytes` |
| AC2 second mutation | `snapshot-head-bytes`: return the newer, unaccepted HEAD's bytes | `snapshots/accepted-bytes` |
| AC3 declared falsifier | `snapshot-working-status`: publish unaccepted checkout status bytes | `snapshots/materialized-revision` |
| AC3 second mutation | `snapshot-wrong-watermark`: publish a watermark one ahead of the accepted store sequence | `snapshots/materialized-revision` |

The two AC2 mutations also turn `snapshots/materialized-revision` red; every criterion still has
two distinct mutations targeting its own named row.

## Runtime seam and scope

The existing VELDO-0023 store and VELDO-0025 authority entities are consumed without modification.
Downstream eligibility (0052), project-manager/proposal (0088/0092), allocation (0037), and candidate
publication (0049) services are not implemented here. The narrow missing data seam is an
`accepted_revision` entity with `domain_uuid`, `repository_uuid`, exact `commit`,
`documents: {relative_path: sha256_digest}`, and `statuses: {relative_path: entity_id}`. An authorized
accepting service supplies that entity through the existing store; the test provisions minimal
accepted records as Release 1 permits. This is not a new admission or authorization protocol.

Authority startup loads the shipped store and calls
`control_readset.attach(store, connection, enrolled_repo, domain_uuid, repository_uuid)`.
For each operation it enables, it calls `reader.enable(operation, declaration)`. A declaration
names an accepted revision, entity inputs and collection queries with referenced entity fields.
`$argument` references resolve against the command arguments. Empty collections remain explicit
inputs, so inserting a blocker changes the read set. Registration changes also invalidate a
snapshot. The wrapped transition runs inside the store's `BEGIN IMMEDIATE`, even for direct
`store.execute` calls; the original business transition sees the declared accepted inputs.

`accept_snapshot` persists a snapshot entity through the store's signed journal. Consumers name
that snapshot in parameters and declare its expected version 1. All registered inputs, including
collection members and referenced dependency targets, are reread transactionally before writes.
The store alone commits. Observations link command, domain, repository, snapshot, accepted input
versions/digests and resulting sequence; `counts` exposes accepted/refused calls and `pending()`
returns accepted snapshots without a consuming command.

`control_snapshot.load` obtains accepted snapshot data from the store.
`materialize(snapshot, enrolled_repo, new_directory)` writes the complete explicit revision and
writes its manifest last. `read_materialized` compares the directory with the supplied accepted
store snapshot, not just with the directory's own manifest. Git access uses `git_process.py`.
Source documents are pinned Git bytes; operational statuses are captured store bytes.

Both runtime assets are installed by `_FILES` in `init_scaffold.py`. They are not validator imports
and therefore do not belong in `REQUIRED_SUBSTRATE`. Canonical engine files and repository-installed
copies are byte-identical. This checkout does not contain committed composed-pack `.veldo` copies;
pack composition derives them from the engine. No policy or specification status changed.
The mutation registry footprint exception is recorded in the specification's prose History.

No crash recovery, fencing, clock qualification, current-pointer recovery, model execution,
channel activation, or extra host qualification was added. Callers retain current authorization,
engineering-review, budget and exact-tree publication obligations at their existing boundaries.

## Gate cost and evidence size

`timing.json` measures 6.90 seconds per registered suite run. The green gate runs it
twice (unit and first-use integration). Its six added mutation cases take 22.48 seconds
through the unchanged gate scheduler, including frozen-copy setup, fresh baselines and no-op
controls (ten worker invocations). Added workload from these measured components: **36.28 seconds**,
below the 60-second limit. This accounts for both suite runs; it is not a whole-gate before/after
differential and does not replace full verification.

Proof is readable JSON, Markdown, Python and six small unified diffs. It contains no private keys,
credential-shaped fixture output, binary/encoded blobs, bytecode, or full gate logs.
