# VELDO-0115: real authority and store qualification

Implementation base: main 59b119a1c565c805b1c883fa56c2ce6685548d67.
Owner authorization: Telegram 37209 and 37212, supplied in this task.

The reusable implementation is `scripts/fixtures/authority_store.py`. Its consumer
is suite `113_veldo_0115_authority_store`, registered with a prerequisite closure
containing only itself. It exercises production `control_client.Authority` judgment,
kernel peer credentials, real Ed25519 signatures, production enrollment, and
`control_store.execute` through the existing apply seam. The fixture uses two actual
Git clones with separate signed enrollment records, domains and SQLite stores.

PLAN-0019 revision 4 places this broader qualification in Release 2. The normal
single-domain service wiring was already incorporated in VELDO-0047. This ticket
qualifies the reusable lower-level fixture, and does not reinstall that service.

## Acceptance checks

| AC | Check | Observation | Declared falsifier |
| :--- | :--- | :--- | :--- |
| AC1 | `ipc/configured-store-really-changes` | Exact upsert, signed journal identity, command, nonce, publication row and committed response watermark | Replace store execution with a logging callback returning acceptance |
| AC2 | `ipc/only-the-bound-store-changes` | Full logical snapshots before and after; exactly one target transaction and no peer delta | Execute through the other writable store connection |
| AC3 | `ipc/accepted-state-survives-reopen` | Stop both authorities after every command; independently reopen target and untouched peer and repeat the transaction comparison | Roll back instead of the final SQLite commit while returning the computed result |

The matrix is the public mutating local routing API crossed with both directions
and all eight combinations of serving/client cwd, importing module location, and
`VELDO_CONTROL_DB` pointing at the other enrolled domain. Each case carries a fresh
command ID and nonce. The public API census classifies every top-level public
function and public class method in `control_client.py`; `send` is the mutating
routing entry. `build_request` constructs data, `inspect` is read-only, and
`Authority.judge`, `serve_one` and `serve_forever` are server-side dispatch. A new
public function fails the census until classified and, if mutating, exercised.
SSH relay qualification remains VELDO-0108's separate transport scope.

Every store first commits a positive-control entity using the original executor.
Snapshots use new read-only sqlite3 connections and enumerate every logical table,
including tables a later consumer might add. The expected transaction is computed
independently of the executor and its snapshot helpers. All old rows must remain
identical; exactly the five expected tables grow by one row. Journal signatures
are independently verified, and the full response must match the committed record.
The `ipc/fixture-unit-controls` row verifies signature rejection after payload
alteration and that acceptance cannot make the observer accept unchanged tables.

The fixture exposes `handles`, `binding`, `path`, `workspace`, `baseline`,
`open_store`, `snapshot`, `start`, `stop`, `kill`, signed `command` construction and
`send`. Consumers must close returned write connections. Children remain attached
to the caller, stop on pipe EOF, and are reaped explicitly. Temporary fixtures do
not acquire or manipulate any host lock.

## Scope of the routing census

The census in suite 113 covers the routing calls in `.veldo/control_client.py`, the client path this
ticket changes. `ServiceAuthority.apply` in `.veldo/control_client_api.py` also writes to the store, but it
is the service-side path that already writes through `control_store.execute` and is not in this
specification's footprint, so it is left out of this census on purpose (review 2026-10-28, finding 2).

## Reproduction and evidence

Run the ticket's falsifiers with the host lock held:

```sh
flock /home/dmitry/.local/state/core-gates/.gate.lock python3 proof/VELDO-0115/check.py
```

The driver retains each applied `AC*.diff`, completed red report and log, restores
the disposable source, and then retains a green report and log for the same suite.
Every run must finish all 16 accepted cases and emit all three AC checks plus the unit row.
Exceptions, absent rows, and incomplete matrices invalidate the drive. Mutations
never alter tracked runtime files. `results.json` binds every run to its input
digests and records each report's digest. Reports retain input commands, enrollment,
authority PID and module digests, database identities, full snapshots, independently
read journal positions, deltas, and named failure categories.

The registered suite can also run alone:

```sh
python3 scripts/selftest.py --suite 113_veldo_0115_authority_store
```

Recorded suite result in `suite.log`: four ticket rows passed across 16 completed
cases, with zero failures. The harness also reports its 26 shared setup checks,
for 30 total, and exits 2 to mark a deliberately partial run. This is ticket
evidence under owner rule 37191, not a full-gate or landing claim.

Recorded falsifier result in `results.json`: all three declared mutants completed
their 16 accepted cases and turned their required check red, exit 1. Each restored
run completed 16 cases with all four rows green, exit 0. The unit controls stayed
green throughout. Each mutant also reds the other two integration checks because
they independently require the expected committed target transaction. All six
runs completed, for 96 accepted requests in total. The driver itself exited 0.
These original reports and applied diffs describe the historical implementation
at `999448eb`, with the full ID in the result and SHA-256 input digests.

The batch compatibility fix at `806cc66b` copies the five required runtime modules
plus `control_client_registry.py` when present. The authority fixture and falsifier
driver share this selection, and both include the registry in their input digests.
This works on the ticket without VELDO-0112 and with its registry prelude in the batch.
`batch-fix-2026-10-28.json` records the fresh confined suite and falsifier results,
tested revisions, receipt digests and retained artifact locations. These are scoped
checks for inventory rows 2 and 5, not a full gate or a landing decision.

Only this ticket's checks and falsifiers are authorized here. The full gate and
batch independent review remain the later landing process. No protected paths are
named by this specification, and none are changed by this implementation.
