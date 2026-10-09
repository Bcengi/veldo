# VELDO-0182 blocked preflight

This is a blocker record, not implementation proof. The attempt started at
294e1933 on agent/codex/veldo-0182. No acceptance criterion is proven.

Read before implementation: README.md, VELDO.md, CLAUDE.md, engine/AGENTS.md,
engine/VELDO.md, engine/CLAUDE.md, VELDO-0182 and its four direct dependencies
(VELDO-0139, VELDO-0144, VELDO-0160 and VELDO-0171). The account registry,
setup, service and launch integration points were inspected. VELDO-0183's
memory references were also checked for an existing store interface contract.

## Blocker

AC4 requires counts and sampled retrieval through the stores' own functions:
mem0_memory's memory_store get and search, knowledge_graph's db get_entity and
search_entities, memory_kb's collection get and kb search, and claude-mem's
search server. The specification supplies names and fixed data locations, but
not the callable signatures, initialization, result shapes, enumeration and
count interfaces, or claude-mem search protocol needed to implement those
adapters and representative fixtures.

The tracked checkout has no implementation of those four stores and no located
capture of their interfaces. Direct read probes of candidate source locations
and the Claude plugin cache all returned EACCES. The exact candidate paths,
errors and tracked-source inventory are retained in preflight.json. These are
candidate paths, not verified installation locations: permission denial proves
neither existence nor absence. No memory content or credentials were read or
retained. A readable source location was requested during the attempt and none
was supplied before this blocker was recorded.

Inventing get, search and count protocols and generating fixtures that implement
those same inventions would not demonstrate AC4's required behavior against
the owner's stores. In particular, it could report a successful switch without
testing the memory the assistant actually uses. The user's explicit instruction
is to stop and record a blocker when the specification cannot be met safely.
Implementation therefore stopped before production edits or partial delivery.

To resume, provide readable, version-identified source snapshots for myday's
mem0_memory, knowledge_graph and memory_kb packages, and the installed
claude-mem search server, or equivalent authoritative interface captures covering
initialization, enumeration/count, lookup by id and search by text. Include
the stores' data-layout contracts needed for the safety copy. Source or captures
must exclude live memory content, account profiles and credentials. No change
to the acceptance criteria is requested.

## Operational criteria and planned proof

These are planned behavior rows, not tests that exist or have run. Suite number
105 remains the number requested for the resumed implementation; no suite or
manifest registration was added for this blocker-only change.

AC1: Owner-signed setup creates the five-part record with fixed data paths and assistant MCP configuration; two accounts of each engine receive identical locations and the current revision; missing knowledge_graph.db refuses before writes; revisions require the owner's signed command.

Falsifier: Derive file memory from each run's account profile; the same-locations row must fail.

Result: Not implemented or run.

AC2: Setup rejects each location containing a registered profile without writes; later registration inside a memory location rejects without registration; file memory inside a profile succeeds; comparisons use real paths.

Falsifier: Remove the registration-time check; the later-registration row must fail.

Result: Not implemented or run.

AC3: Identical setup leaves files and journal head unchanged; an older host gains only the missing memory step under the setup lock rule; a differing manifest refuses without writes and requires the owner's revise command.

Falsifier: Write a revision on every setup; the second-run journal-head assertion must fail.

Result: Not implemented or run.

AC4: Setup over all five fixture stores leaves a single private safety copy per part, using SQLite online backup for databases; repeated before checks refresh count and random sample without replacing the copy; after checks the live store's count and every sampled id and text through its own functions; remove a sample and add a replacement for each part, retaining the count, and require the named refusal with store and copy paths.

Falsifier: Check the copy instead of the switched store; the removed-memory row must fail because the broken check passes.

Result: Blocked by unavailable store interface evidence; not implemented or run.

The safety copies must never appear in the memory record or launch handoff.
Launches must read the current revision and refuse missing locations by name.
Setup's initial memory step must run the before and after checks around the
first naming of each part. Future switches in VELDO-0183 and myday consume the
same check interface, as the unchanged specification requires.

## Validation and scope

Only source discovery, permission probes and static repository reads were run.
No suite, mutation runner, canonical gate, external service or memory switch
was run. No gate stamp, independent review, unit evidence or integration evidence
is claimed. No success proof manifest was created: the required behavioral
evidence does not exist. The retained JSON is explicitly a blocked preflight
record, not a veldo.proof/v1 bundle.

Changes are limited to this record, preflight.json and the specification's
History. Acceptance criteria, ready status, production code, suite registrations
and other branches and worktrees remain unchanged.
