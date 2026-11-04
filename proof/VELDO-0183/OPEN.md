# VELDO-0183: open items for the lead

## 1. scripts/gate_unconfined.json must name suite 130 (protected file, the lead adds it)

`130_veldo_0183_memory_servers` reuses VELDO-0171's installed-host fixture through proof/VELDO-0185/fixture.py, as
`129_veldo_0177_assistant_setup` does, and like 129 it cannot run in the mutation stage's confined leg: run alone
under `scripts/check_teeth_mutations.py` (confined), its baseline fails at the fixture's first step, exactly as 129's
own case `setup177-no-assistants` does when run the same way (both shown in mutation-driver-confined.txt). Suggested
entry, beside 129's:

    {"suite": "130_veldo_0183_memory_servers", "reason": "systemd user manager: factory setup installs and starts user services on this host (VELDO-0171's fixture), and the memory store servers as user units"}

The manifest entry declares `resources: {"systemd_user_manager": 1}`, as 129's does. The suite itself drives the
fixture's user manager stand-in and starts no real unit.

## 2. The servers step is its own owner command, not yet called from `veldo factory setup`

AC1 and AC4's setup work (catalog records, role revisions, store server units, the assistant's entries, the checks
around them) is `veldo memory servers` (options: the state root, the owner's key, and optionally the unit directory and the install root)
(control_memory_servers.setup_servers), run after `veldo factory setup` with its memory option has laid the memory
record and the default team down. It is idempotent (a second run saves nothing; suite 130 row
AC4/assistant-entries). Calling it from the end of control_factory_setup.setup and rerun (inside the footprint:
engine/.veldo/control_factory_setup.py) was left out on purpose: setup with a memory manifest runs VELDO-0182's
five-part preflight, whose claude-mem probe needs VELDO-0182's worker fixture, so that wiring would ship untested
here. One call after the `api_unit` step when both a memory plan and a dispatch plan exist would do it.

## 3. Owner interfaces assumed, not read (the build was told never to read the owner's memory code)

- control_memory_kb maps each memory_kb subcommand to the kb function its cli.py calls: `search` to
  kb.search.search, `index-file`, `index-dir`, `index-telegram` to kb.indexer.index_file, index_directory,
  index_telegram, and `stats`, `list`, `delete`, `clear` to kb.store.stats, list_documents, delete_document,
  clear_collection. These names are this build's assumption; check them against the captured memory_kb cli.py
  (VELDO-0182's interface capture) before the first conversation. A wrong name answers that one tool with an error
  naming the missing attribute; nothing else is affected.
- ava-memory's `memory_add_smart` is answered by the store server: it takes the tool's first string input as the
  text, extracts on the subscription, and adds each fact through mcp_server's own `memory_add` tool, into its first
  required string input, passing any other input `memory_add` also accepts. Check against the captured
  mcp_server.py.
- The fixture's FastMCP stand-in has list_tools and call_tool as the mcp package's FastMCP does; the store server
  also accepts call_tool's (content, structured) pair and dict answers of newer mcp releases.

## 4. Smaller points for review

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
