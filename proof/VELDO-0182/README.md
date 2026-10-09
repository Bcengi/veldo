# VELDO-0182 implementation and review handoff

The interface-access blocker is resolved. The implementation keeps one signed,
versioned memory record, refuses profiles contained by memory locations, hands
its current locations to every launch, and provides before/after loss checks.
The specification remains ready. Independent review, approval and the canonical
gate are pending; no gate stamp or passing aggregate unit evidence is claimed.

## Interfaces and provenance

`interface-contract.json` records each adapter's captured version and source
hashes. No capture file was copied into this repository.

- ava_memory: myday mem0_memory at b641e2ad6c01deb54888ffc7be27b72f029941f7.
- knowledge_graph: myday knowledge_graph at 81541d04ea30c30808145f7498516033ee6cd14a.
- memory_kb: myday memory_kb at 879a46b2b8eb127f525cffd22c9e508b36db5546.
- claude_mem: installed plugin 10.6.2, run as installed (Round 2).
- file_memory: the specification's auto-memory layout, MEMORY.md plus fact files.

The portable fixtures use synthetic content and the fixed directory layouts,
SQLite graph tables, Chroma document/metadata subset, and plugin observations,
session summaries and user prompts. They replace embeddings and semantic ranking
with deterministic matching. When the excluded captures are present, the suite
also imports the actual captured Python wrappers in place, with synthetic backend
APIs. claude-mem has no capture step: its check runs the installed plugin itself,
proven read only against the owner's real store (Round 2).
These are interface tests, not a claim about live memory or embedding quality.
Without captures, that optional conformance step reports itself unavailable.

mem0 enumeration grows its limit until exhausted instead of trusting the
captured stats function's 10000-item ceiling. The knowledge graph samples entities,
as the specified get_entity/search_entities pair requires, while backing up all
tables. The KB enumerates full documents across all seven collections, decrypts
through the captured store helper, and refuses unavailable plaintext.

claude-mem is checked through its own search (Round 2). Counts and the random
sample come from a consistent private copy of the named claude-mem.db. Each
sampled memory is fetched by id through claude-mem's routes and searched for
through its search server, started from the manifest's command against a worker
dedicated to the check. That worker runs over the private copy, never over the
named store and never through the owner's running worker.

## Operational interface

Add the memory option to factory setup, naming a JSON manifest with these fields:

```json
{
  "host": "owner-host",
  "assistant_mcp": "/absolute/myday/.mcp.json",
  "parts": {
    "file_memory": {"data": "/absolute/profile/project/memory"},
    "ava_memory": {"code": "/absolute/myday/mem0_memory", "interpreter": "/absolute/owned/python"},
    "knowledge_graph": {"code": "/absolute/myday/knowledge_graph", "interpreter": "/absolute/owned/python"},
    "memory_kb": {"code": "/absolute/myday/memory_kb", "interpreter": "/absolute/owned/python"},
    "claude_mem": {
      "code": "/absolute/plugin/10.6.2",
      "command": ["/absolute/plugin/10.6.2/scripts/mcp-server.cjs"],
      "data": "/absolute/claude-mem-data"
    }
  }
}
```

Use absolute, existing, owned code and data paths; a location is not a link, nor
is any directory above it. A link inside a location is the store's own: it is
copied as a link and never followed. The same rule applies in setup, revise, the
signed transition and handoff, all through one normalization. Interpreter
paths may use venv or system symlinks; their resolved executable must belong to
the owner or root and must not be group or world writable. The invocation path
is preserved so Python still discovers its venv. A launch is handed memory only
on the host the manifest names (invalid_input:memory:host:differs). Profile
comparisons compare every registered profile path against both the handed code
and data directories by real path, without walking either. Memory inside a profile is permitted.
The first three server data paths are derived from their code locations, so the
manifest cannot redirect them. Setup names existing bytes and never migrates them.

The memory command has check and revise subcommands. Check takes the part name
above and before or after, plus the state-root option. Revise takes a new manifest,
state-root and owner-key options. Initial setup and revision check the old and candidate locations before the signed
record switch. A failed switch leaves the old record and launch handoff intact;
a retry checks again. Fresh setup, and a re-run whose memory step will write,
probe every adapter before host writes. A differing setup manifest refuses and writes nothing.
The revise command uses the original owner's signature and an expected revision.
A live authority receives the signed command through setup's existing transport;
an offline writer must hold authority.lock. An identical setup does not declare
ownership again, refresh a sample, copy data or advance the journal.

Each engine receives VELDO_MEMORY containing the revision and normalized locations.
The receiver emits the same metadata and saves a private per-dispatch receipt under
memory/launches. It ignores any inherited VELDO_MEMORY, refuses configured VELDO_ names before
adapter acceptance and applies handed memory last in the exec wrapper. The wrapper
drops only reserved VELDO_ names from the engine overrides; the VELDO_MCP_ names
that carry Codex's header credentials (VELDO-0158) pass. This implements location
handoff; configuring the memory servers and the engines' native file-memory behavior
belongs to VELDO-0183 and VELDO-0184, respectively.

The first before check copies data to memory/copies/part. SQLite files use online
backup, including committed WAL rows. Subsequent before checks refresh the private
count/sample file without replacing that copy. After reads the current store,
requires at least the saved count and every sampled id and own-text search, and
names the part, live location and safety copy on refusal. A copy is never handed
to a launch. A failed after stops before the record changes. Adapter/import failures report
unavailable_service, distinct from missing_evidence for measured loss. Memory
steps report done, already_done or refused with outcome counters; a refusal
counts as a check refusal only when a check refused. KB checks select only existing
collections and replace the captured create-on-read helper in their subprocess.

A safety copy works while the owner's assistant runs (Round 2). A SQLite database
is copied by SQLite's online backup in one step: a live store's shared memory is
opened read-only, and a WAL database no one holds open is read immutably so that
nothing is created beside it. A Chroma directory is copied segment files first
and database second; the copy is kept only when no segment file changed from
before its first byte to after the backup, and none within a second before it,
and is retried otherwise. WAL, shared memory and log files are never stamped.

## Acceptance criteria and counterexamples

| Criterion | Proving rows in suite 105 | Executed falsifier |
| --- | --- | --- |
| AC1 | setup/five-parts, record/owner-signature, record/revise, integration/fresh-setup, setup/missing-database, launch/same-on-every-account, launch/current-revision, launch/durable-receipt | falsifier/account-derived changes the scratch receiver to derive file memory from each account profile. Two real Codex turns receive different locations, violating the same-location assertion. |
| AC2 | profile/setup-refused, profile/later-registration, profile/real-paths, profile/memory-inside-accepted, profile/no-walk, link/location-same-everywhere, link/nested-same-everywhere | falsifier/setup-only removes the registration-time check. The forbidden profile registers, violating the no-registration assertion. |
| AC3 | setup/idempotent, integration/setup-repeat, integration/identical-files, integration/service-lock, integration/differs-no-writes | falsifier/rewrite-rerun always writes the otherwise identical record. The journal advances, violating the unchanged-head assertion. |
| AC4 | check/loss for each part, check/search-required for each server, check/count-drop, check/twenty, check/copy-once for each part, worker/* (Round 2), copy/* (Round 2), integration/check-cli, integration/revise-cli | falsifier/copy for each part checks the unchanged safety copy after deleting a sampled live id and adding another. It wrongly passes, violating the loss-refusal assertion. |

`local-results.json` retains row-level diagnostics. The suite number is 105 and
its manifest declares no prerequisite suite. Only the shared harness and this
specification's rows run. Scoped selftest deliberately returns exit 2 when all
rows pass and cannot produce passing unit evidence. The proof manifest maps every
criterion to its test source and leaves verification pending. It is not a landing
approval and does not turn partial results into a full gate result.

The setup fixtures use an isolated user-manager stand-in. This environment refuses
Unix datagram sockets, so the running-service row uses the real Service admission
and authority.lock with an explicit in-process transport stand-in. It asserts that
setup opens no writable store handle. The full socket/service-manager lifecycle
remains the reviewer's gate coverage. Launch rows use the real Runner, receiver,
account registry and wrapper, with qualified fake engine binaries and no real login.

No full selftest, gate, mutation runner, push, merge or live memory switch was run.
Round 2's read-only runs against the owner's real stores are described below.

## Review repair rows

Configuration precedence: launch/reserved-config for both engines refuses memory
and future reserved names. launch/config-precedence starts both engines with a
legacy configuration bypass and compares actual environment with the signed
record. falsifier/config-precedence removes the exec protection too and observes
revision 99 while the receipt event still names revision 1.

Switch atomicity: switch/refused-unchanged compares the record, journal and
handoff; switch/retry-rechecks observes the repeated checks; switch/original-setup
accepts the original manifest. falsifier/commit-before-check moves the signed
write ahead of the check and reproduces all three failures.

Other review rows: integration/adapter-preflight-no-writes, integration/refused-outcome,
setup/venv-interpreter, setup/system-interpreter and check/unavailable-not-lost.
Round 2 replaced worker/real-routing, worker/named-store-chroma-off,
worker/missing-not-lost, profile/handoff-nested-link, profile/handoff-code-link,
copy/moving-index-refused, copy/open-index-writer-refused and copy/quiescent-index,
which tested designs it removed. The KB fixture raises if a check creates a
collection. System interpreter ownership is represented as root in its focused
row because this sandbox maps the system filesystem owner to uid 65534; that uid
is never accepted by production validation.

The repair diagnostics report 101 passing specification rows in suite 105.
Suites 75 and 78 have no failures. Suites 73 and 85 retain the reviewer-reported
user-manager refusals (16 and 15 rows), and suite 82 retains its single Codex
evidence/completeness failure. These scoped runs are diagnostics, not aggregate
verification. The gate and mutation runner remain reserved to the reviewer.

## Round 2: second review repairs

The second review (00b27f77..78ca3687) blocked on three defects and named six
more. Each repair, its rows in suite 105 and the mutation that turns them red
are below. Every mutation was applied to the shipped module, the suite run, and
the module restored; each failed exactly the rows named, by assertion
(local-results.json, round_two_falsifiers).

| Item | Repair | Rows | Mutation that fails them |
| --- | --- | --- | --- |
| 1 | The exec wrapper drops only reserved VELDO_ names, so VELDO_MCP_ credentials reach Codex; the handed VELDO_MEMORY is applied last | launch/engine-overrides; suite 85_veldo_0158 delivery/codex-environment | drop every VELDO_ name |
| 2 | claude-mem's own search through a dedicated worker over a private copy | worker/dedicated, worker/owner-worker-untouched, worker/kills-nothing, worker/stopped, worker/cut-short-stopped, worker/read-only, worker/facts-and-untexted, worker/search-is-claude-mems, worker/unaudited-version-refused, check/search-required-claude_mem | answer every search as found; no ps shim; no HOME sweep in the adapter; no sweep in the parent |
| 3 | Safety copies while the assistant runs | copy/sqlite-writer-50ms, copy/check-while-assistant-writes, copy/idle-wal-no-sidecars, copy/chroma-open-writer, copy/chroma-persist-retried, copy/chroma-busy-refused | copy SQLite raw; open an idle database normally; keep a Chroma copy without comparing stamps |
| 4 | Containment by real path, no walk | profile/no-walk | walk each location |
| 5 | One link rule, the specification's | link/location-same-everywhere, link/nested-same-everywhere | refuse nested links at handoff |
| 6 | Re-run preflight | integration/rerun-preflight | no preflight on re-run |
| 8 | Check metric only for check refusals | metrics/check-refusal, metrics/step-refusal-only | count every refusal as a check refusal |
| 9 | Handoff on the manifest's host only | launch/host-differs | no host comparison |

Item 7 (refusal at registration rather than launch) is unchanged: the
specification does not require registration time.

### claude-mem's own search

Text search in claude-mem 10.6.2 runs only through Chroma, with a 90 day window
unless a date range is given. A text search therefore needs a working chroma-mcp
over a consistent copy of claude-mem's Chroma. The worker writes its data
directory, and keeps its process registry and its Chroma directory under HOME,
not under CLAUDE_MEM_DATA_DIR. At start, and every 30 seconds after, it kills
processes it finds with `ps`: any other worker-service.cjs or chroma-mcp, any
mcp-server.cjs older than 30 minutes, idle claude children, and claude processes
reparented to init. Started plainly, it would kill the owner's worker and Chroma.

So the check gives it a private HOME holding a consistent copy (claude-mem.db by
online backup, Chroma as above), CLAUDE_MEM_DATA_DIR inside it, its own port
(never 37777 nor the port the store's settings name), a `ps` on PATH that lists
nothing, no pending messages or active sessions in the copy, a Claude path that
does not exist, claude-mem's own request bound raised to 300 s, and the owner's
uv cache, interpreters, uv.toml and UV_ settings for chroma-mcp. The search
server runs from the manifest's command against that worker. Afterwards every
process carrying the private HOME is stopped, by the adapter and again by the
parent. These safeguards were audited for 10.6.2, the only version started.

A sampled memory is searched for by the first 2000 characters of the longest
text claude-mem indexes for it (observation narrative, text and facts; summary
request, investigated, learned, completed, next_steps and notes; prompt text),
with its type and project and a date range from 1970. The owner's store holds
988 observations whose only indexed text is in facts, which are searched by a
fact, and 1085 observations with a title only and 110 empty summaries, for which
claude-mem indexes no text and its search can never return them: those are
fetched by id only. When a search misses, the check waits for the dedicated
worker's own Chroma backfill, then searches again.

### The owner's real stores, read only

real-store-results.json records the runs, all traced with strace (no payload
bytes) and analyzed for any open for writing, write, rename, unlink, mode, time
or link change under the five store locations, and for any signal outside the
traced process tree. The owner's worker, its search servers and its three
chroma-mcp processes were listed before and after each run and did not change.

- Safety copies of all five parts while the owner's Chroma held its files open:
  every SQLite copy passes integrity_check with the source's counts, and every
  Chroma copy loads in chromadb with the source's counts (claude-mem 448896).
- claude-mem before: passed in 139 s, 79469 memories, copy made, 20 sampled.
- claude-mem after, final implementation: passed in 449 s, all 20 found by id
  and by claude-mem's own search.
- after on a private copy of the real store with one sampled memory renumbered:
  refused missing_evidence:memory:claude_mem:lost, naming the store and the copy.
- No writing syscall under any store and no signal outside the traced tree. The
  only open for writing is SQLite's read-only connection opening claude-mem's
  existing WAL, which every reader of a live WAL database does; nothing is
  written through it.

Incident: before the idle-database rule existed, one read-only count opened the
owner's knowledge_graph.db (WAL mode, held open by no one) and SQLite created an
empty knowledge_graph.db-wal beside it. Nothing else was written, and the empty
file was left for the owner. copy/idle-wal-no-sidecars now guards this.

Environment: on 2026-10-09 a fresh uvx resolution of chroma-mcp picks pydantic
2.14.0, with which chroma-mcp's mcp 1.6.0 cannot import. The owner's running
chroma-mcp still has pydantic 2.13.5. The real runs set UV_CONSTRAINT to a file
holding pydantic<2.14. Without such a constraint the check refuses
unavailable_service:memory:claude_mem:adapter, as claude-mem's own search is
unavailable; the owner's claude-mem meets the same failure at its next restart.

### Suites

Suites 105 (111 rows), 85_veldo_0158_credential_delivery, 85_veldo_0171_setup_api,
82_veldo_0141_execution_record, 82_veldo_0129_worker_wiring and every other suite
that loads a changed module pass, one at a time in the foreground. Suite
91_veldo_0167_setup_records failed 8 rows on 78ca3687 because the receiver had no
memory field when its spawn seam is driven directly; it passes now.
82_veldo_0173_tool_registry (3 rows), 82_veldo_0165_launch_hygiene (2 rows) and
86_veldo_0127_agent_configuration (live/claude, live/codex) fail identically on
the unmodified 78ca3687: they read the host's Claude binary or live captures.
