# VELDO-0113 implementation and evidence

The CLI construction gap is fixed under lead decision 2 (2026-11-21). Acceptance
remains incomplete pending VELDO-0111's COMPLETE qualification. No canonical gate,
independent review or owner approval is claimed here.

`bin/veldo` and `engine/bin/veldo` now send signed work requests through the same
`control_client.send` boundary used by the claim client. The production command
accepts `--principal`, `--key`, `--host-trust` and optional `--account`. It opens
no store and constructs no Dispatcher. The authority's adjacent `work_command`
operation verifies the command signature, active owner membership, repository
scope and coordinates. It queues a wake of its existing configured factory loop;
its response is explicitly `queued`, not a completed build. An account argument
must match the configured builder. Missing configuration refuses by name. The
library's explicit dispatcher injection remains a test seam, inaccessible from
the CLI; non-default local execution options cannot enter the remote path.

Suite 115 exercises both shipped CLIs against absent endpoints and real socket
inodes left by SIGKILL. It forbids client database connections and local dispatcher
use. A separate process owns a real SQLite store and serves the real authenticated
IPC boundary and Service.apply with OpenSSH signatures; a recording loop measures
only the accepted wake, not build execution. Refused signatures, another
principal, another repository scope, missing owner role and malformed parameters
must cause no wake. Readiness uses a pipe, never a sleep or a short deadline.

The original direct-store counterexample remains in `contract-gap.txt` and
`reproduce_contract_gap.py`. It explains the first lead amendment and is not an
absence claim. The amended spec History records both lead decisions.

The construction census recursively scans both shipped module trees, both CLI
directories and operational scripts, excluding test harnesses. It follows direct,
imported and assigned constructor aliases and reports file, line and source
SHA-256. New source files are discovered on every run. There are no CLI exemptions.
The current allowed sites in each shipped module tree are:

- Dispatches: `control_service.py:3207,3939`, `control_service_api.py:214`,
  `control_launch.py:2295`, `control_launch_work.py:148`.
- Dispatcher: `dispatch.py:574`.

There is still no process-specific writable-store grant. `control_store.open_store`
checks filesystem support and durability, not caller process identity. The fixture
runs a separate non-authority process that opens a fresh real store and commits a
probe table. That row is GAP, never isolation success. The lead explicitly leaves
this for a separate security ticket; the CLI fix does not close that broader gap.

The unchanged VELDO-0112 inventory has 21 identities: 11 external clients and ten
in-process authority entries. Both endpoint states produce 42 assessment cases,
with 22 observed external invocations. In-process identities retain their
construction disposition and inventory digest. The dead endpoint's binding child
acknowledges readiness through a pipe, is killed with SIGKILL and is reaped before
clients run. External adapters receive valid enrollment and signing inputs and no
store handle. Actual refusal must reach the endpoint and carry ENOENT or
ECONNREFUSED, not merely fail an unrelated schema check.

Launch envelopes declare the root and required Git identity lookups before the
call. Each lookup has exact argv and a causal root-parent birth slot. A wrapper
acknowledges its PID and parent, then execs Git in the same process. Those records
join one-to-one to census birth/exit intervals; executable names waive nothing.
Every service event attributable to the observed client scope is forbidden.

The three consumer rows retain distinct PASS, FAIL and STANDS DOWN statuses.
INCOMPLETE capture or qualification always makes absence stand down with
`census_incomplete`, even if partial capture sees a forbidden effect. All eight
observer faults are attempted for every external registry/state case (176 drives).
The fixture separately checks fault phase/category/capability and propagation of
all three required names with zero PASS absence rows. Protocol assertions and
synthetic evaluator controls never establish live absence.

Five falsifiers are registered under finding 113: immediately reaped fallback
Authority, transient abstract Unix listener, incomplete census accepted as success,
extra Dispatches construction in claim.py, and restored direct Dispatcher
construction in bin/veldo. Each has an exact retained diff and named target row.
`run_checks.py` drives temporary source copies and retains full receipts, then
checks the targets and restoration. The standard mutation coordinator's findings
are retained separately. VELDO-0111's incomplete AC2 qualification prevents the
required live AC1/AC2 false-row evidence; captured effects are only diagnostics.

`proof/VELDO-0111/OPEN.md` describes the dependency gaps, including protocol
inventory bounds. This is not merely a host permission issue. Earlier receipts
and logs are historical diagnostics, retained with their original digests in Git;
current reruns replace their corresponding current evidence files. Earlier
construction failures and writer tuple/list round-trip failures are not green
acceptance evidence. `--reassess` explicitly reads a saved receipt without a new
observer invocation.

Receipt archives use lossless shared tables and LZMA inside a gzip JSON envelope.
`run_checks.read_receipts(path)` reconstructs each full receipt and verifies its
original SHA-256. Compact text summaries omit repeated per-case receipt hashes;
the full archives retain them. The writer rejects personal paths in raw receipts.
Human-readable diagnostic logs normalize home prefixes before retention.

Checks run through the external host-heavy wrapper. New synchronization uses
pipes, process completion and observation barriers; new deadlines are 1200-second
hang detectors. The census coordinates at most four independent observer
processes, each with private arguments and launch acknowledgements. Selected
selftests remain partial runs, not canonical gate evidence.
