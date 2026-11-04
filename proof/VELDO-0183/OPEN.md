# VELDO-0183: open items for the lead

Fix round 1 closed the build's items 1 to 3 (see README, "Fix round 1"); fix round 2 closed item 1 below. What stays open:

## 1. memory_kb argument shapes: resolved (fix round 2)

The lead read the real signatures and cli.py's calls from the owner's code. Each memory-kb tool's input is now its
subcommand's arguments and each call passes them as cli.py does: search(collection, query, n_results=n,
classifications=list or None) or search_all(query, ...), n default 5, classifications split on commas;
index_file(path, classification=..., default "BP"); index_directory(path, pattern=..., default "*.md"), neither
taking a collection; index_conversation(message, metadata={"chat_id": chat_id or ""}, classification=..., default
"BP"), chat_id optional; get_stats(); list_documents(collection, limit=..., default 20); delete(collection, doc_id);
clear as delete_collection on the store server's one client. The fixture kb package has exactly those signatures.
Row AC1/real-layout now binds each tool's call to the fixture function's signature by name (inspect.signature
bind), so a wrong parameter name, a missing argument or an omitted default fails it, as does a tool input other
than cli.py's arguments; red before the fix and green after (round2-real-layout.txt).

## 2. `clear` and the store server's client

`clear` opens chromadb.PersistentClient(path=kb.config.DB_PATH) once in the store server, kept for its life
(control_memory_kb.client), and calls delete_collection(name=...) on it. chromadb shares one system among the clients
of one path in a process, so this is the same store the kb package's own client has open, never a second process.
Not established here: whether kb.store caches a collection object across calls in a way a
delete_collection on the shared system leaves stale (the fixture's kb.store reads its collection from the client on
every call).

## 3. The rerun with the authority service running

`veldo factory setup` runs the servers step at its end, and its rerun runs it again when a memory plan and a dispatch
plan both exist (suite 130 row AC1/setup-step: four records and both role revisions with no separate command, the
rerun saving nothing). The step takes the store's lock itself, so a rerun while the authority service runs reports
`memory_servers` deferred (reason service_running) instead of writing; `veldo memory servers` with the service
stopped completes it. Not exercised by a row.

## 4. Smaller points for review (unchanged from the build)

- The paid-API names the catalog refuses are every engine module's CREDENTIALS and SETTINGS (control_launch's
  STRIPPED). The VELDO-0165 execution strip's other names (GH_TOKEN, GITHUB_TOKEN, SSH_AUTH_SOCK and the rest) are
  not refused: a GitHub MCP server legitimately takes a GitHub token. Widen paid_api_names if the owner reads
  "login" more broadly.
- The bridge logs each call with its catalog revision and memory record revision (from its record's arguments)
  and `VELDO_DISPATCH_ID` when its environment carries one; whether the receiver hands MCP servers that name is
  not established here, so the join of a store server's call line to its run rests on the run's execution record.
- `veldo memory kb` offers no `setup-passphrase` (the Notes say the owner sets the passphrase with `veldo memory
  kb` on the host); not an AC, left for the myday change the Notes file.
- The extraction behind smart add chooses its account with the pool's own `choose` over the store's account
  records, read without the reservation ledger (no worker slot is reserved for it), and records the run under
  `<state root>/memory/extractions/`.
- The fixture's FastMCP stand-in has list_tools and call_tool as the mcp package's FastMCP does; the store server
  also accepts call_tool's (content, structured) pair and dict answers of newer mcp releases.
