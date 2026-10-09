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
- claude_mem: installed plugin 10.6.2.
- file_memory: the specification's auto-memory layout, MEMORY.md plus fact files.

The portable fixtures use synthetic content and the fixed directory layouts,
SQLite graph tables, Chroma document/metadata subset, and plugin observations,
session summaries and user prompts. They replace embeddings and semantic ranking
with deterministic matching. When the excluded captures are present, the suite
also imports the actual captured Python wrappers in place, with synthetic backend
APIs, and drives the actual captured MCP script against a loopback worker API.
These are interface tests, not a claim about live memory or embedding quality.
Without captures, that optional conformance step reports itself unavailable.

mem0 enumeration grows its limit until exhausted instead of trusting the
captured stats function's 10000-item ceiling. The knowledge graph samples entities,
as the specified get_entity/search_entities pair requires, while backing up all
tables. The KB enumerates full documents across all seven collections, decrypts
through the captured store helper, and refuses unavailable plaintext. The plugin
checks all three searchable memory types and explicitly disables its default
90-day search cutoff. Version 10.6.2 has no summary/prompt get tool; its filter-only
search supplies full records for lookup by typed id. Observations use the dedicated
get_observations tool. A failed or unavailable search is a refusal, never success.

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
      "command": ["/absolute/owned/node", "/absolute/plugin/10.6.2/scripts/mcp-server.cjs"],
      "data": "/absolute/claude-mem-data"
    }
  }
}
```

Use absolute, existing, owned paths without symlinks, including the executable
paths. The host field is descriptive; it cannot bypass profile exclusion. Profile
comparisons inspect every registered profile path against both the handed code
and data directories using real paths. Memory inside a profile is permitted.
The first three server data paths are derived from their code locations, so the
manifest cannot redirect them. Setup names existing bytes and never migrates them.

The memory command has check and revise subcommands. Check takes the part name
above and before or after, plus the state-root option. Revise takes a new manifest,
state-root and owner-key options. Initial setup and revision surround the record
switch with checks. A differing setup manifest refuses and writes nothing.
The revise command uses the original owner's signature and an expected revision.
A live authority receives the signed command through setup's existing transport;
an offline writer must hold authority.lock. An identical setup does not declare
ownership again, refresh a sample, copy data or advance the journal.

Each engine receives VELDO_MEMORY containing the revision and normalized locations.
The receiver emits the same metadata and saves a private per-dispatch receipt under
memory/launches. It ignores any inherited VELDO_MEMORY. This implements location
handoff; configuring the memory servers and the engines' native file-memory behavior
belongs to VELDO-0183 and VELDO-0184, respectively.

The first before check copies data to memory/copies/part. SQLite files use online
backup, including committed WAL rows. Subsequent before checks refresh the private
count/sample file without replacing that copy. After reads the current store,
requires at least the saved count and every sampled id and own-text search, and
names the part, live location and safety copy on refusal. A copy is never handed
to a launch. A failed after stops the switch operation; it does not automatically
roll back the owner's record or memory.

## Acceptance criteria and counterexamples

| Criterion | Proving rows in suite 105 | Executed falsifier |
| --- | --- | --- |
| AC1 | setup/five-parts, record/owner-signature, record/revise, integration/fresh-setup, setup/missing-database, launch/same-on-every-account, launch/current-revision, launch/durable-receipt | falsifier/account-derived changes the scratch receiver to derive file memory from each account profile. Two real Codex turns receive different locations, violating the same-location assertion. |
| AC2 | profile/setup-refused, profile/later-registration, profile/real-paths, profile/memory-inside-accepted | falsifier/setup-only removes the registration-time check. The forbidden profile registers, violating the no-registration assertion. |
| AC3 | setup/idempotent, integration/setup-repeat, integration/identical-files, integration/service-lock, integration/differs-no-writes | falsifier/rewrite-rerun always writes the otherwise identical record. The journal advances, violating the unchanged-head assertion. |
| AC4 | check/loss for each part, check/search-required for each server, check/count-drop, check/twenty, check/copy-once for each part, copy/sqlite-online, integration/check-cli, integration/revise-cli | falsifier/copy for each part checks the unchanged safety copy after deleting a sampled live id and adding another. It wrongly passes, violating the loss-refusal assertion. |

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
