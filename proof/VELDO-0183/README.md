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
alone), each run VELDO-0182's `before` and `after` check around them; a check that runs while a store server is up
reads the store through that server (fix round 3). `veldo memory kb <subcommand>` reaches the same socket.

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

## Fix round 1 (the build's open items)

Commits: e5efd9f9 (memory_kb's real layout, the fixture, setup running the servers step, rows AC1/real-layout and
AC1/setup-step), eb925fc9 (mutation cases kb183-guessed-name and setup183-no-servers-step), 46f88f3d (suite 130 on
the gate's unconfined list, protected), and the proof commit after them. Suite 130 now has seventeen rows.

- memory_kb (OPEN item 3): control_memory_kb's tools call what memory_kb's cli.py calls, as the lead read it:
  kb.store.search (kb.store.search_all when no collection is named), get_stats, list_documents(collection, limit),
  delete(collection, doc_id); kb.indexers.file.index_file and index_directory;
  kb.indexers.telegram.index_conversation(message, metadata={"chat_id": ...}, classification=...); and `clear` as
  delete_collection on chromadb.PersistentClient(path=kb.config.DB_PATH), opened once in the store server. The
  fixture kb package has exactly that layout (and a chromadb stand-in sharing one system per path, as chromadb
  does); the guessed kb.indexer module and kb.store stats, delete_document and clear_collection are gone. Row
  AC1/real-layout fails when a tool maps to a function outside that layout (targets() against the lead's list), when
  one does not resolve in the fixture, or when the fixture carries a guessed name. Case kb183-guessed-name (stats to
  kb.store.stats) turns it red. AC2/tools-work now calls every memory_kb tool, both search branches, delete and
  clear (and finds nothing after clear).
- ava-memory (OPEN item 3): the fixture's mcp_server.py is FastMCP `ava-memory` with memory_search(query, limit=10,
  category=""), memory_add(text, category="general", source=""), memory_add_smart(text), memory_stats(),
  memory_delete(memory_id), memory_get_all(limit=50); AC1/real-layout checks those signatures, and AC2/tools-work
  calls all six. Smart add maps the text to memory_add's text unchanged.
- Setup (OPEN item 2): `veldo factory setup` runs the servers step (control_factory_setup.memory_servers, the same
  setup_servers `veldo memory servers` runs) after its api_unit and tailscale_serve steps, and its rerun at its end,
  when a memory plan and a dispatch plan both exist; the rerun reports it deferred while the authority service holds
  the store's lock. Row AC1/setup-step runs factory setup with the memory manifest (this fixture's stores, the
  claude-mem part from VELDO-0182's fixture, with its bun, uvx and uv cache stand-ins on PATH as suite 105 runs
  them) and finds the four records, both role revisions selecting all four and both store servers started, with no
  separate command; the rerun reports the step already_done and the journal head unchanged. Case
  setup183-no-servers-step turns it red. The main journey still runs `veldo memory servers` on a host laid down
  without the memory option.
- Unconfined list (OPEN item 1): scripts/gate_unconfined.json names 130_veldo_0183_memory_servers beside 129.
  mutation-driver-confined.txt (the confined-leg baseline failure that motivated it) is removed.

Evidence: suites.txt (130, 128, 129, 123, 127 and VELDO-0182's 105, each alone, green), falsifiers.txt (six cases
applied to .veldo, each restored byte for byte), mutation-<case>.txt (each of the six cases run alone by
scripts/check_gate_mutations.py honouring the committed list: baseline and no-op green, mutant red on its row). The
full gate was not run.

## Fix round 2 (memory_kb argument shapes)

Commits: 971bb78c (the fixture kb package's functions take the real signatures; row AC1/real-layout binds each
memory-kb tool's call to them and checks the tools' inputs; AC2/tools-work's calls use the real inputs), 59af0aa5
(control_memory_kb), and the proof commit after them.

- control_memory_kb's tool inputs are cli.py's arguments: search query, collection, n, classifications; index-file
  path, classification; index-dir path, pattern; index-telegram message, chat_id (optional), classification; stats
  none; list collection, limit; delete collection, doc_id; clear collection. Each call passes cli.py's defaults
  (n 5, classification "BP", pattern "*.md", chat_id "", limit 20) as cli.py does. No tool takes the passphrase.
- Row AC1/real-layout checks the fixture's functions' full signatures against the lead's reading, then runs
  fourteen tool calls (both search branches, each optional argument given and omitted) with each kb function
  replaced by a recorder that binds the call to that function's own signature: the bound arguments must equal
  cli.py's, by name. A wrong parameter name, a missing argument or an omitted default fails it. A third check
  compares each tool's input schema with cli.py's arguments.
- AC2/tools-work now indexes the directory into memory_kb's own collection, searches one collection with n and
  classifications, searches every collection, and clears `conversations` (the telegram thread is gone after).

Evidence: round2-real-layout.txt (the row red at 971bb78c, green at 59af0aa5), suites.txt (suite 130 alone, green),
mutation-<case>.txt (the six cases rerun alone through scripts/check_gate_mutations.py honouring the committed list:
baseline and no-op green, mutant red on its row). falsifiers.txt is fix round 1's. The full gate was not run.

## Fix round 3 (review 2026-11-04, finding 1: the check opened a served store)

Commits: 3aac9321 and 7b67f6af (the extended row and the fixture's open record), b0af7b3c (the fix), 77661c64
(mutation case servers183-check-opens-store), and the proof commit after them.

- The finding: setup's own memory check ran VELDO-0182's adapter in a new process over the live store after the
  store server had started (start_stores' `after`, rewrite_assistant's `before` and `after`), a second opener of a
  store its store server holds.
- The fix: the store server answers two more requests on its socket, `check` and `copy`
  (control_memory_store.Inspector): `check` runs VELDO-0182's own reader, control_memory_adapter.inspect, on the
  server's tools thread over the store the server already holds open (kb.store's _get_collection, which the
  adapter's memory_kb reader repoints, is restored after), and `copy` runs VELDO-0182's copy_data in the server,
  into a staging directory under the state root's memory/copies only. Sampled rows go back over the socket only;
  the journal line names the part, request and outcome. control_memory_check.check takes an optional `served`
  reader; the servers step passes control_memory_servers.Served (the socket's `check` and `copy`) for every check
  that runs while a store server is up (start_stores' `after`, both of rewrite_assistant's) and none for the
  `before` at a first start, which runs before the server starts. Without `served` the check is unchanged, so
  VELDO-0182's check where no store server exists is the same code path. The `memory_check` events carry `served`.
- The row: AC4/one-opener now also samples /proc for each store throughout the main journey's servers step and its
  rerun and throughout `veldo factory setup` with the memory manifest and its rerun (row AC1/setup-step's runs), and
  requires no sample with two processes holding a store's files. The fixture's Chroma stand-in records each open of
  a store with the other pids then holding its files (fixtures.OPENS, opens.jsonl beside the fixture stores), and
  the row requires no open in those windows beside another holder, so a second opener is caught at the moment it
  opens, not only when a sample lands on it. The writers' sampling is unchanged.
- Red then green: round3-one-opener.txt. At 7b67f6af (production as at 83588ab4) only AC4/one-opener is red: in
  both windows each store shows three opens beside its store server (the `after` check and the rewrite's two) and
  samples with two holders; at b0af7b3c the suite is green, seventeen rows.
- Mutation case servers183-check-opens-store passes no `served` reader, bringing the second opener back: mutant
  red on AC4/one-opener only, baseline and no-op green.

Evidence: round3-one-opener.txt, suites.txt (130, 128, 129, 123, 127 and 105, each alone at 77661c64, green),
mutation-<case>.txt (the seven cases, each run alone by scripts/check_gate_mutations.py honouring the committed list
at 77661c64: baseline and no-op green, mutant red on its row). falsifiers.txt is fix round 1's. OPEN.md item 5. The
full gate was not run.
