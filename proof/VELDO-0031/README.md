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

The final clean-tree gate is recorded in `gate-summary.json`, including its input
commit and full-log SHA-256. No full gate log is committed. Independent review and landing
approval are not asserted by this implementation proof. No push is performed.

Measured added workload: 10.48 seconds. Final gate results:

```text
GATE: GREEN (74b8b6c4d3c45287abadaa3bf5a3bec20659c927)
selftest: 5681 passed, 0 failed
mutations: passed registered=90 executed=90 rejected=90 workers=122 elapsed=62.083s
```

The earlier diagnostic gate was stopped after the missing mutation-registry footprint
entry was identified; `diagnostic-gate.json` retains that failure and its log digest.
The authorized registry path was then declared. A later diagnostic run passed units but
stopped for a canonical lifecycle correction. This complete clean-tree run passed.

## Independent review corrections at 5cf94c3

The six supplied reproduction scenarios are registered as separate assertion rows in
`scripts/suites/59_veldo_0031_review.py`. Before any production edit, all six rows
failed assertions against `5cf94c3a64d3aa1e6c47bae2cb9a90e9ea0d4357`; the original
run is retained in `review-baseline-red.txt`. `review-baseline-red.json` reruns the
final suite against files extracted from that same commit and records six RED
assertions with the suite digest. No branch or worktree was changed for that run.

| Finding / row | Correction | Registered negative controls |
| --- | --- | --- |
| R1 / `claims/review-r1` | Validate packet, command and signature types before reading fields or invoking the verifier; refuse `malformed_request`, record the refusal, and continue serving. ASCII signature validation also prevents invalid Unicode from reaching the verifier's file writer. | `review-r1-command-crash`, `review-r1-signature-crash` |
| R2 / `claims/review-r2` | One ownership consistency function checks activation for claim, inspect, renew, release and use. Both omitted activation legs and activation without ownership stop consistently. | `review-r2-inspect-skips-consistency`, `review-r2-activation-without-owner` |
| R3 / `claims/review-r3` | Retain heartbeat ClaimStopped, join the heartbeat, and perform protected use immediately before finalize. Test both a loss without a heartbeat tick and a heartbeat stop followed by recovery; neither can move local or remote refs. | `review-r3-publish-without-use`, `review-r3-swallow-heartbeat-stop` |
| R4 / `claims/review-r4` | Read enrollment beside the explicitly selected ledger, including the environment override, independently of cwd. | `review-r4-cwd-selects-enrollment`, `review-r4-refuse-unrelated-root` |
| R5 / `claims/review-r5` | Expiration alone cannot revoke the stored holder's right to renew or release with its current generation. Wrong holders/generations, use and takeover remain refused. | `review-r5-expiry-revokes-owner`, `review-r5-release-ignores-holder` |
| R6 / `claims/review-r6` | Share ClaimStopped identity across file-location imports so callers catch both authority and routing stops. | `review-r6-private-stop-class`, `review-r6-routing-wrong-exception` |

Each finding has a separate implementation commit; R1 has an additional signature
encoding correction. `review-rN-green.json` records each target row's transition
while later findings were still RED, so those intermediate files do not assert a
green suite. `review-r1-unicode-red.json` and `review-r1-unicode-green.json` retain
the additional encoding scenario's before/after observations. The legacy AC2 row
now requires a refusal for terminal inconsistent state on release as well as use;
it no longer asserts that contradictory operation-specific answer. The spec History
and footprint explicitly include the landing caller required by AC3.

`review-repros.json` records another run of all six supplied scripts, each unchanged
and digest identified. Their shared fixture's SRC was pointed at this checkout's
installed modules instead of its frozen original snapshot. All six exit zero and
none prints a BUG line. `review-mutations.jsonl` and the `review-r*.diff` files retain
the driven negative controls. These targeted results are diagnostic evidence; the
complete clean-tree gate is the acceptance check.

The original proof and gate records above are historical. The correction gate and
workload measurements are recorded separately below. Independent
review approval and landing are not asserted; no push was performed.

Measured corrected claim workload: 24.18 seconds including both suite passes and
all 18 claim mutations with baseline/no-op controls (30 workers), below 60 seconds.
`review-timing.json` records the measurement; the canonical gate uses the entire
mutation inventory without filtering.

Final correction gate, started from a clean tree:

```text
GATE: GREEN (e1dfd6ee0118cd92d7da272245de6b7a9ed215f4)
selftest: 5687 passed, 0 failed
mutations: passed registered=102 executed=102 rejected=102 workers=142 elapsed=72.098s
```

`review-gate-summary.json` records the tested commit and full-log SHA-256. The
manifest binds the corrected evidence to that verified tree. The final commit only
records this proof; `.veldo/last_verify` and `.veldo/events.jsonl` are restored to
their original checkout contents and are not included.
