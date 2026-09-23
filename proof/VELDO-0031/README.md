# VELDO-0031 proof

Release 1 authority-backed claims. Specification status and policy are unchanged.
No automatic reclaim, crash recovery, replacement fencing or clock qualification was added.

## Criteria and executable rows

The gate runs `scripts/suites/58_veldo_0031_claims.py`. Each criterion has one named
assertion collecting its individually printed observations; a failed observation
makes that assertion red. All operations cross authenticated AF_UNIX IPC from real
enrolled Git clones to the configured real SQLite store. Ed25519 command signatures
are verified against active stored membership keys; journal records are signed too.
Fixture keys and signatures are temporary and are never retained in this proof.

| Criterion | Row | Observed set |
| --- | --- | --- |
| AC1 | `claims/atomic-activation` | Two child clone processes race for one admitted unit; one owner; a single journal transition includes ownership, unit READY -> CLAIMED and backlog PRIORITIZED -> ACTIVE; SQLite states agree; capability denial; four invalid alias forms produce no writes; enrolled default caller stops; neither clone creates a ledger or database. |
| AC2 | `claims/current-generation` | Renew, release and use each receive the current holder/generation and three mismatched combinations at the real receiver; release retains the generation and the next explicit claim increments it; old generation remains refused through DISPATCHING, RUNNING, VERIFYING, REVIEWING, READY_TO_LAND and LANDING; revoked membership and another holder's signature refuse. |
| AC3 | `claims/uncertainty-stop` | Unowned, owned, explicit uncertain, stale and existing detector-unanswerable states; the actual existing Lander takes an explicit authority client; known contention is bounded; uncertainty raises a named terminal stop; holder/state and local/remote refs stay unchanged; service unavailability is named. Receiver diagnostics, accepted/refused counts and pending claims are observed. |

## Driven falsification

`scripts/check_teeth_mutations.py --finding 31` drives temporary production copies.
The required mutation gate independently runs baseline, byte-identical no-op copy,
and mutant workers. Exceptions, missing rows and timeouts are errors, not detections.
Each mutation below completes assertions and turns its named row red. Exact applied
zero-context diffs are committed alongside this file. The activation mutations scope
the omitted transition to the raced unit, leaving the separate landing-lock fixture
usable so later assertions complete instead of throwing.

| Mutation | Red row |
| --- | --- |
| `claims-ownership-without-unit` (declared AC1 falsifier) | `claims/atomic-activation` |
| `claims-ownership-without-backlog` (second AC1 defect) | `claims/atomic-activation` |
| `claims-ignore-use-generation` (declared AC2 falsifier) | `claims/current-generation` |
| `claims-ignore-use-holder` (second AC2 defect) | `claims/current-generation` |
| `claims-uncertainty-as-contention` (declared AC3 falsifier) | `claims/uncertainty-stop` |
| `claims-detector-as-owned` (second AC3 defect) | `claims/uncertainty-stop` |

The activation defects also invalidate dependent AC2 observations. These are
additional detected failures; the declared AC1 row itself fails its stored-state
assertion. `mutations.jsonl` records the actual red rows and green controls.

## Integration seams and limits

The dependencies for SQLite commands, enrolled routing, IPC and membership exist.
The service runner and final factory admission/publication integration are parallel
items. This change provides only their narrow claim seam:

- `control_claim.Receiver.apply` is the real `control_client.Authority.apply` callback.
  It reads current accepted membership/key records, verifies the holder signature,
  binds authorization and activation entity versions, and calls `control_store.execute`.
  The store alone writes the entire signed transaction. Receiver construction fixes
  domain, repository, store and authority generation; requests cannot select a store.
- Minimal accepted `execution_unit` records name repository, `backlog_item_uuid`, requirements
  and eligible holders, starting READY; the `backlog_item` starts PRIORITIZED. These
  reuse the existing lifecycle names; claiming produces CLAIMED and ACTIVE together. The suite provisions these
  through signed store commands. This does not implement owner admission or scheduling.
- `control_claim_client.Client` is passed as `claim.py`'s `root` or the existing
  Lander's `claims_root`. Enrolled default calls stop with `authority_required` rather
  than falling back to a clone ledger. Unenrolled legacy filesystem callers remain
  compatible. A client retains the generation returned by claim; use can also carry
  the dispatch's explicit generation. It never refreshes generation to pass a check.
- `Client.use` is the receiver-side ownership check for the future exact-publication
  caller. It grants no publication permit. The landing test drives actual existing
  lock/caller control flow with Git operations on disposable local/bare repositories;
  its gate and reconcile callbacks are deterministic fixtures. It does not claim to
  prove the separate final publication, review or admission specifications.
- The scaffold installs both claim modules and their existing IPC/enrollment dependencies.
  New claim modules are not imported by validators and therefore are not added to
  REQUIRED_SUBSTRATE. All changed installed .veldo files match engine/.veldo byte for byte.

## Timing and gate

`measure.py` measures the added suite twice (unit plus first-use integration), then
its registered mutation workload with the real frozen-input mutation runner and
baseline/no-op controls. Its in-memory inventory selection applies only to this
measurement; the final canonical gate uses the complete registry. `timing.json`
records measured time including snapshot overhead. The new workload is below the
60-second limit. This is a conservative isolated workload measurement, not a claim
that concurrent gate wall time is additive.

The final gate summary, input commit and full-log SHA-256 will be recorded in
`gate-summary.json`; no full gate log is committed. Independent review and landing
approval are not asserted by this implementation proof. No push is performed.
