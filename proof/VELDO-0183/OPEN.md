# VELDO-0183: open items for the lead

Fix round 1 closed the build's items 1 to 3 (see README, "Fix round 1"). What stays open:

## 1. memory_kb argument shapes the lead's reading did not give (assumed, named here)

The module paths and function names are now the ones memory_kb's cli.py imports, and suite 130 row
AC1/real-layout fails on any other. The lead gave the call shapes of list_documents(collection, limit),
delete(collection, doc_id) and index_conversation(message, metadata={"chat_id": ...}, classification=...). These
argument shapes are still this build's assumption; check them against cli.py before the first conversation:

- `search` with a collection calls kb.store.search(collection, query), the order VELDO-0182's capture of kb/search.py
  shows it wrapping; without one, kb.store.search_all(query). `n_results=` is passed by keyword only when the tool
  input names it.
- `index-file` and `index-dir` call index_file(path) and index_directory(path), with `collection=` by keyword only
  when the tool input names one.
- `index-telegram` passes `classification=` only when the tool input names it, so the function's own default holds.
- `stats` calls get_stats() with no argument; `list` passes limit only when given.

A wrong shape answers that one tool with the function's own TypeError; nothing else is affected.

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
