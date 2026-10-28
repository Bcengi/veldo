# VELDO-0112 registered client fixture

Owner go: Telegram 37209 and 37212. Base: main
`59b119a1c565c805b1c883fa56c2ce6685548d67`. Work stays on
`agent/codex/veldo-0112`; no push or landing is performed.

## Implementation

The registry guards public mutation functions and methods at their definitions.
File-location imports share one state per installed source directory. A removed
registration disables existing handles and identity dispatch. Conflicting
identities refuse with `duplicate_client`. The boundary check discovers public
callers of mutation sinks in the client surfaces independently of their
decorators, requires claim, command and dispatch admission, and checks canonical
engine synchronization and installation inclusion.

The reusable fixture joins adapters to the complete registration and transport
product. Its 19 cases invoke their registered public functions. Claim, renewal,
release and protected use run through the enrolled claim client, real AF_UNIX
receiver and signed SQLite journal. Commands run through `send`; both relay
entry points carry signed requests to that authority. Durable dispatch methods
consume real reservation and lifecycle preconditions and commit signed journal
entries. Each operation must advance the journal. The two dispatch orchestration
front doors use their documented external service seams, as explained in OPEN.md.

The command client is the common transport used by API, setup and channel
callers. This fixture tests its registered public entry, not every possible
command payload or those applications' authorization rules. Authority-side
writers and read-only inspection are excluded from the client boundary census.

Two independent consumers enumerate and execute a temporary extra production
registration. Receipts reject omitted, duplicate, stale and empty inventories.
A registration without an adapter fails discovery. Receipts bind case and input
identities, registration and implementation digests, fixture version and digest,
adapter identity, transport, accepted result digests, and registered versus
exercised sets.

## Checks and falsifiers

| Criterion | Automated row | Source falsifier |
| --- | --- | --- |
| AC1 | `clients/registry-is-the-boundary` | Remove the claim decorator, leaving its public mutation function callable. |
| AC2 | `clients/every-registration-is-drivable` | Remove the dispatch preparation adapter. |
| AC3 | `clients/registry-growth-expands-cases` | Filter the extra registration from exported cases. |

`drive.py` makes a private copy for each falsifier, retains its diff, requires the
named row to be false in a completed run with the expected diagnosis, restores
the source, and requires all three rows to pass. A crash, missing row, abnormal
exit or unexpected diagnosis is an invalid drive. Each red and subsequent green
has its own JSON artifact; `mutations.json` records the result summary.

`run_checks.py` runs the ticket baseline, those falsifiers and restored controls,
then only suites 47, 48, 49 and 113. The first three were edited solely to copy the
new runtime dependency into their miniature installations. The selected suite
runner deliberately returns 2 for a successful partial run. It is not a full
gate result. The owner explicitly deferred the full gate to a batch; it was not
run here.

Reproduce with the owner's blocking host lock:

```sh
flock /home/dmitry/.local/state/core-gates/.gate.lock python3 -B proof/VELDO-0112/run_checks.py
```

The tests never acquire or release that host lock themselves. Their stores,
keys, sockets, claims and locks live in temporary directories. Server threads
are joined and temporary sources restored or removed. The implementation and
proof use no other project code or added package dependency.

No protected paths were changed. OPEN.md records the footprint and current-code
reconciliation, and separates this fixture qualification from worker, full
floor, SSH authentication, unavailable-service and census qualification.
