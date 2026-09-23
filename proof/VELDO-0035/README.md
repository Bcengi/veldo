# VELDO-0035 proof

Implementation: accepted snapshots, complete transactional read-set registrations, and ordinary
materialization at an explicit local watermark. Specification remains **ready**. This bundle is
implementation evidence, not independent engineering review, owner approval, or service activation.

Canonical verification: `bash scripts/verify.sh` passed from clean commit `06b58e898daaafd17c51b2d1865945c51258bf49`.
`gate-summary.json` retains the full-gate summary and log digest; no full gate log is committed.

```text
selftest: 5705 passed, 0 failed
FIRST USE: pass. Every family's sanctioned first use leaves the suite exactly as green as it was, so no assertion in scripts/suites/ requires this repository's current emptiness. What that does and does not cover is in this file's docstring.
template sync: pass (157 pair(s) compared, 6 declared per-repo, 131 engine-only)
mutations: passed registered=90 executed=90 rejected=90 workers=122 elapsed=73.108s
GATE: GREEN (06b58e898daaafd17c51b2d1865945c51258bf49)
```

Two earlier runs were stopped after diagnosed integration issues (the mutation registry footprint
declaration and the required Git-helper alias); `initial-attempt.json` records them. Both were
corrected before the successful clean-tree run. The final evidence commit changes proof only.

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

## Review corrections at 296be42 (R1-R4)

R1 and R4: `review-r1-red.json` records completed failing suite assertions against production
files extracted from `296be42` (no other branch or worktree used). The capsule scenario holds an
old read transaction, commits a blocker on another connection, and tries a reservation through
that writer using the same store module. `review-r1-green.json` records the corrected behavior.
The store now dispatches connection-local registrations and passes the executing connection
inside its own BEGIN IMMEDIATE transaction. Snapshot commands on unregistered connections
refuse `unregistered_inputs`; guards refuse wrong connections and transactions not opened by
store execution. Validation and all writes therefore use the same transaction and connection.

The module-level command catalog remains unchanged by ReadSets. Two authorities in different
domains can enable the same operation independently; duplicate enable and duplicate attachment
refuse. Closing a store connection clears its registrations. The added control-store footprint
is the minimal dispatch seam required for this correction, mirrored from the canonical engine.
The registered mutations remove the unguarded-connection refusal and separately allow a deferred
read transaction; the named rows must fail assertions, rather than terminate with exceptions.

R2: `review-r2-red.json` records the path-prefix inventory assertion failing against `296be42`;
`review-r2-green.json` records acceptance refusing `invalid_input` with every domain table
unchanged. Validation covers document/status and status/status ancestry, deep descendants, and
the reserved `manifest.json` completion path before acceptance writes anything. The materializer
uses the same inventory validation before creating a destination. The two mutations respectively
remove ancestor checking and check only the immediate parent; both fail the inventory row.

R3: `review-r3-red.json` records the status-only commit assertion failing against `296be42`,
including the capsule's HEAD movement and publication after acceptance. Commit validation now
runs outside the document loop: every accepted revision must supply a full object id, and Git
must resolve that id to that exact existing commit. Symbolic refs are refused rather than
silently selecting whichever HEAD is current. The snapshot pins the validated id. Empty document
inventories receive the same check. Missing object ids and blob ids also refuse, while a valid
status-only snapshot publishes its original commit and captured status after HEAD has moved.
`review-r3-green.json` records all rows green; two distinct mutations skip empty-inventory
validation or accept nonexistent/noncommit ids, and both fail the status-only row.

`review-capsules.json` retains final runs of the three original, unmodified capsules, copied
one at a time to `.capsule/` and invoked from this repository root. All exit zero, explicitly
refuse the unsafe operation, and emit no `BUG:` observation. R1's attached-connection stale-input
control also passes. Capsule copies are removed and no other worktree is modified.

### Final review verification and cost

The clean-tree gate at `072eb215b8395eedad79524ea5ab27b8ff74183f` passed:

```text
selftest: 5711 passed, 0 failed
FIRST USE: pass. Every family's sanctioned first use leaves the suite exactly as green as it was, so no assertion in scripts/suites/ requires this repository's current emptiness. What that does and does not cover is in this file's docstring.
template sync: pass (157 pair(s) compared, 6 declared per-repo, 131 engine-only)
mutations: passed registered=96 executed=96 rejected=96 workers=130 elapsed=90.404s
GATE: GREEN (072eb215b8395eedad79524ea5ab27b8ff74183f)
```

`review-gate-summary.json` retains the elapsed time and full-log digest. This run
supersedes the initial build gate above; `manifest.json` binds the corrected implementation
and updated criterion evidence to this verified commit. The final commit changes proof only.

`review-timing.json` measures the original suite at 6.81 s and the corrected suite at
7.81 s (1.00 s added per run; the gate executes it twice). All twelve VELDO-0035 mutation
cases, including the six new review controls and fresh baseline/no-op copies, take 39.49 s
through the unchanged scheduler. The conservative whole-feature added workload is **55.12 s**
(two corrected suite runs plus all twelve mutations), against the 60 s budget. This is a
component measurement, not a whole-gate before/after differential.

The first timing sample overlapped the gate's nested integration suite and measured 60.24 s;
`review-timing-concurrent.json` retains it. The reported 55.12 s sample was taken after the full
gate finished. These are observed timings, not a guarantee under arbitrary host contention.
The gate itself took 762.22 s and rejected all 96 registered repository mutations, including
all twelve snapshot cases. Proof remains readable text below 1 MB, with no full gate log.
