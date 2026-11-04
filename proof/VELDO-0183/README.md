# VELDO-0183 proof: the owner's memory servers in the catalog

Base 671bd13e (VELDO-0230, VELDO-0231 and VELDO-0177 on main a0f33f80). Commits: 35b17f88 (store servers, bridge,
memory_kb tools, servers step, the catalog's paid-API refusal, fixture stores), a6356609 (suite 130, the writers the
store binds, one tools thread), 681d41da (mutation cases, falsifiers), and the proof commit after it.

The test is one new suite, `130_veldo_0183_memory_servers` (fifteen rows), on VELDO-0171's installed-host fixture as
suite 129 uses it: a host laid down by the real setup with three registered accounts (two Claude Code, one Codex),
the memory record admitted by the owner's signed command over proof/VELDO-0183/fixtures.py's synthetic stores (a
FastMCP stand-in, a Chroma-like store that loses writes when two processes open it, the knowledge graph's WAL SQLite,
a claude-mem search server), memory_kb's passphrase and a paid key saved as credentials into a fake keystore, then
`veldo memory servers` (control_memory_servers.setup_servers) run with the fixture's user manager stand-in. Turns are a
generated fake engine that starts the MCP servers its configuration names and prints Claude Code's stream JSON; its
output is kept by the real execution record. No real engine, login, paid API, keyring, memory store or server.

Red before: red-at-671bd13e.txt (all fifteen rows red at the base). Green after: suites.txt (130 and the named
suites alone). Falsifiers: falsifiers.txt (each case applied to .veldo, suite run, module restored byte for byte) and
mutation-<case>.txt (each case run alone by the gate's mutation driver: baseline and no-op green, mutant red on its
row). Open items: OPEN.md.

## AC1: four catalog records over the one store, selected by both assistant roles

Built: control_memory_servers.definitions and save_catalog. From the memory record, four records are saved through
the installed engine's catalog writer, each by the owner's command authenticated as VELDO-0203 authenticates his
revisions: `ava-memory` and `memory-kb` launch the factory's stdio bridge (`veldo memory bridge <part>`, in
control_factory_setup_memory) to the part's store server, `knowledge-graph` is its interpreter running its
mcp_server.py, `claude-mem` is its search server's command from the manifest, and `memory-kb` names
JARVIS_PASSPHRASE's credential reference when the owner saved it. memory_kb's tools (control_memory_kb) are its cli.py
subcommands search, index-file, index-dir, index-telegram, stats, list, delete and clear, without setup-passphrase,
each answered inside the store server. save_roles saves a new revision of `assistant` and `assistant_codex` adding all
four as `always` selections of all tools, and one default team revision naming them.

Test rows: AC1/catalog-records, AC1/role-selections, AC1/init. The init row runs a turn on each engine's role
revision (as control_conversation.role_at binds it) with its servers from the catalog, and requires the init event
to list the four connected, with the role's expected launch set (control_agent_config_handoff inventory, expected,
difference) equal to it and every tool each server registers offered.

Falsifier (spec): save the roles without claude-mem. Case roles183-no-claude-mem drops claude-mem from the
selections: AC1/init red, the init event listing ava-memory, knowledge-graph and memory-kb only
(falsifiers.txt, mutation-roles183-no-claude-mem.txt).

## AC2: no paid model API, and smart add on the subscription

Built: control_mcp_catalog.paid_api_names and paid_api. Every catalog save, for every record, is refused
`invalid_input:mcp_server:paid_api:<name>` when an environment or header name, or the saved credential a reference
points at, is one the receiver strips from an engine as a paid-API switch or login (each engine module's CREDENTIALS
and SETTINGS, ANTHROPIC_API_KEY and OPENAI_API_KEY among them). The store server keeps only the names a process needs
to run in its environment, so the part's code never sees a paid key, and answers ava-memory's memory_add_smart itself:
the text goes to `veldo memory extract` (control_memory_servers.extract), which chooses a Claude Code account with the
account pool's own choose, runs Claude Code in that account's profile with no paid-API name in its environment,
records the run under the state root's memory/extractions, and the store server adds each fact with the part's own
memory_add.

Test rows: AC2/paid-api (ava-memory with ANTHROPIC_API_KEY as its credential refused and no revision saved; a
reference to the saved ANTHROPIC_API_KEY credential under another name refused; OPENAI_API_KEY in an unrelated
server refused; each refusal observed and counted), AC2/smart-add (no paid key in the suite's environment; both
extracted memories found by another turn; the extraction is one recorded run on a registered Claude Code account the
pool chose; the fake Claude Code ran in that profile and saw no key ending _API_KEY), AC2/tools-work (every
ava-memory, knowledge graph, memory_kb and claude-mem tool answered without error).

Falsifier (spec): accept ANTHROPIC_API_KEY as the ava-memory record's credential. Case catalog183-paid-api-accepted
makes paid_api answer None: the revision is saved and AC2/paid-api is red (falsifiers.txt,
mutation-catalog183-paid-api-accepted.txt).

## AC3: every memory call in the run's record; one store across conversations

Built: nothing new beyond AC1 and AC4: memory calls are ordinary MCP tool calls, so the execution record keeps them.
control_memory_servers.metrics counts memory tool calls per server and tool, paid-API refusals and runs whose memory
servers failed to connect, from a run's record lines.

Test rows: AC3/record (the turn's record keeps every line the engine printed, each equal to the execution record's
own redaction of it; each memory call is a tool use with its input followed by its result; memory_kb's passphrase,
present in a search result, is replaced by its marker; the counts), AC3/cross-conversation (conversation A on
claude-a adds a memory, a graph fact and a memory_kb document; conversation B on claude-b finds all three; the
assistant's servers started from its rewritten configuration find them; `veldo memory kb search` finds the document).

Falsifier (spec): hand each conversation its own copy of the data directory. Row AC3/own-copy-falsifier runs B over a
copy taken before A wrote, through the copy's own servers, and requires B's searches empty and the
cross-conversation condition false; it passes in every run (suites.txt), so the cross-conversation row fails on B's
empty search under that defect. No production line chooses a per-conversation copy, so there is no mutation case for
it.

## AC4: one opener per ChromaDB store, every write serialized

Built: control_memory_store.py, run by the part's interpreter in its code directory as the user unit
`veldo-memory-<part>.service` (Type=notify) that start_stores writes, enables and starts beside the authority
service. It takes an exclusive lock on veldo-store.lock in the part's data directory for its life, refuses
`conflict:memory_store_open:<part>:<pid>` when the lock or any store file is held by another process (read from
/proc), imports the part's tools (mem0_memory's mcp_server `mcp`; memory_kb's control_memory_kb), and serves them over
a 0600 Unix socket in a 0700 directory under the state root, checking the peer's uid, every call on the one thread that
imported them. The first start of each store server, and the rewrite of the assistant's ava-memory and memory-kb
entries to the bridge (previous bytes kept under memory/assistant-mcp, entries that already name the bridge left
alone), each run VELDO-0182's `before` and `after` check around them. `veldo memory kb <subcommand>` reaches the same
socket.

Test rows: AC4/store-units, AC4/open-refused (a second store server on the same store refused naming the running
server's pid; a store another process holds open refused naming it, no socket made), AC4/assistant-entries (bridge
entries, other entries untouched, previous bytes kept 0600, the rewrite inside the check, a second run saving
nothing), AC4/one-opener and AC4/all-written: five writers at once (a conversation's catalog bridge and the
assistant's entry on each store, and `veldo memory kb index-file` on memory_kb's), 200 each, /proc sampled every
50 ms showing each store's files held by its store server alone in every sample; after all end a fresh process finds
all 400 in mem0_memory's store and all 600 in memory_kb's, by id and by search.

Falsifier (spec): launch ava-memory as mcp_server.py opening the store itself. Case servers183-ava-opens-store: the
one-opener row is red on a second process holding mem0_memory's files (and writes are lost). Guard case
store183-open-unchecked removes the open check: AC4/open-refused red (falsifiers.txt, mutation files).

## Observability

Row observability: the store servers' journal lines carry each start and lock with its part and socket, and each call
with its server, tool, catalog revision and memory record revision; no memory content or credential appears in them;
the servers step observes each catalog revision with the memory record revision it read. Catalog refusals carry the
paid-API name.
