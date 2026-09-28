---
schema: veldo.spec/v1
id: VELDO-0183
title: Ava's ava-memory, knowledge graph, claude-mem and memory_kb servers are catalog MCP servers over the one memory store, every store write serialized across processes, never handed a paid model API, and every memory call is in the run's record
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W143
plan_revision: 4
depends_on: [VELDO-0141, VELDO-0144, VELDO-0158, VELDO-0177, VELDO-0182]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_memory*.py"
  - ".veldo/control_memory*.py"
  - "engine/.veldo/control_mcp_catalog*.py"
  - ".veldo/control_mcp_catalog*.py"
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "engine/.veldo/control_team*.py"
  - ".veldo/control_team*.py"
  - "engine/.veldo/control_agent_config*.py"
  - ".veldo/control_agent_config*.py"
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_service*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "bin/veldo"
  - "engine/bin/veldo"
  - "scripts/suites/*_veldo_0183_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0183-memory-servers-in-the-catalog.md"
  - "specs/index.md"
  - "proof/VELDO-0183/*"
behavior_bearing: true
observability:
  logs: >
    Record each store server's start and lock with its part and socket, each memory server's catalog
    revision with the memory record revision it reads, each catalog save refused for a paid-API name, and
    each run's memory servers as names; never memory content or a credential.
  metrics: >
    Count memory tool calls per server and tool, catalog saves refused for a paid-API name, and runs whose
    memory servers failed to connect.
  traces: >
    Join each memory tool call line to its run, its server's catalog revision and the memory record
    revision.
  error_taxonomy: >
    Distinguish a catalog record that hands a server a paid-API or login name
    (invalid_input:mcp_server:paid_api:<name>) from a memory server that fails to connect at launch (the
    init event's server status, stopped by name before the first turn as VELDO-0127 AC4 stops a missing
    server) and from a ChromaDB store another process holds open when its store server starts
    (conflict:memory_store_open:<part>:<pid>).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Setup defines ava-memory, the knowledge graph, claude-mem and memory_kb as catalog MCP server
      records serving their own code's tools over the one memory store (the two ChromaDB parts through
      AC4's store servers), and the assistant roles
      select all four with all their tools. Set and completeness: From the memory record (VELDO-0182), setup
      saves four VELDO-0144 catalog records by the owner's signed command: `ava-memory` (AC4's bridge to the
      mem0_memory store server, which serves the tools of mcp_server.py, the server myday's `.mcp.json`
      launches today);
      `knowledge-graph` (the knowledge_graph interpreter running mcp_server.py in its code directory, whose
      main creates the database with init_db and serves FastMCP `knowledge-graph` over stdio; myday's
      `.mcp.json` lists only ava-memory among the memory servers, so this entry point is named from the
      code); `claude-mem` (its search server's command from the manifest); and `memory-kb` (AC4's bridge to
      the memory_kb store server, which serves the tools of control_memory_kb, shipped by the factory since
      memory_kb is a command-line tool with no server of its own), whose tools are its cli.py subcommands
      (search, index-file, index-dir, index-telegram, stats, list, delete, clear and setup-passphrase), each
      answered by the store server calling the kb package functions that subcommand calls, never by a
      second process opening the store, with
      memory_kb's `JARVIS_PASSPHRASE` (kb/crypto.py) as the record's credential reference when the owner has
      saved it (VELDO-0158 delivers and redacts it). Setup adds each to the `assistant` and `assistant_codex`
      roles of VELDO-0177 AC2 as an `always` selection of all tools, as a new role revision. The init event of
      a turn on each engine lists the four servers connected with every tool each registers. Falsifier: Save
      the roles without `claude-mem`, and the init row must fail on the missing server.
    falsified_by: >
      Save the roles without `claude-mem`, and the init row must fail on the missing server.
  - id: AC2
    text: >
      Claim: No catalog server is ever handed a paid model API credential or switch, so ava-memory's one tool
      that calls the Anthropic API answers with its own refusal while every other tool works. Set and
      completeness: A catalog save whose server environment or credential reference names any name the
      receiver strips from an engine's environment as a paid-API switch or login (VELDO-0155, VELDO-0156,
      VELDO-0165; `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` among them) is refused by name
      (invalid_input:mcp_server:paid_api:<name>), for every catalog record, not only memory. ava-memory's
      `memory_add_smart` needs `ANTHROPIC_API_KEY` for its extraction model (myday mem0_memory
      memory_store.add_smart); it stays offered, since tools are never taken away, and answers its own
      missing-key message, while `memory_search`, `memory_add` and every knowledge graph, claude-mem and
      memory_kb tool work. Falsifier: Accept `ANTHROPIC_API_KEY` as the ava-memory record's credential, and
      the paid-API row must fail on the saved revision.
    falsified_by: >
      Accept `ANTHROPIC_API_KEY` as the ava-memory record's credential, and the paid-API row must fail on the
      saved revision.
  - id: AC3
    text: >
      Claim: Every memory read and write is a tool call in the run's execution record, and a write in one
      conversation is found by another conversation and by the owner's assistant, because it is the one
      store. Set and completeness: Each call to a memory server's tool is kept in the turn's execution record
      (VELDO-0141 AC1) with its input and result, redacted as every line is. The suite runs fixture copies of
      the four servers over one fixture store: conversation A adds a memory, a knowledge graph fact and a
      memory_kb document; conversation B, on another account, finds all three by search; and the fixture's
      own servers and memory_kb's command line, started as the owner's assistant's configuration starts
      them, find them too. Falsifier: Hand each conversation its own copy of the data directory, and the
      cross-conversation row must fail on B's empty search.
    falsified_by: >
      Hand each conversation its own copy of the data directory, and the cross-conversation row must fail
      on B's empty search.
  - id: AC4
    text: >
      Claim: Every write to mem0_memory's and memory_kb's ChromaDB stores made by a conversation, by the
      owner's assistant's MCP entries or by `veldo memory kb` is serialized across processes,
      because one store server per store is the only process that opens it and every conversation and the
      owner's assistant reach that server over a local socket, while the knowledge graph's SQLite store
      already serializes its writers. Set and completeness: Setup installs, by the owner's signed command, one
      store server per ChromaDB part as a user unit beside the authority service (control_service's
      Systemctl): the part's own interpreter running the factory's control_memory_store in the part's code
      directory, which imports the part's own tools (mem0_memory's mcp_server `mcp`, whose tools call
      memory_store; control_memory_kb over memory_kb's kb package), holds an exclusive lock on a lock file in
      the part's data directory for its whole life, and serves those tools one call at a time over a Unix
      socket under the state root that only the owner's account can open. Before it opens the store it refuses
      by name a store another process holds open (conflict:memory_store_open:<part>:<pid>). AC1's `ava-memory`
      and `memory-kb` records launch the factory's stdio bridge (`veldo memory bridge <part>`), which lists
      the server's tools and forwards each call; setup writes the same bridge as the `ava-memory` and
      `memory-kb` entries of the owner's assistant MCP configuration the memory manifest names (VELDO-0182
      AC1), keeping the previous bytes for the rollback and leaving entries that already name the bridge
      alone, and `veldo memory kb <subcommand>` runs memory_kb's command line through the same server. The
      knowledge graph needs no server: db.py opens every connection in WAL mode, so SQLite's own file locks
      admit one writer at a time and a writer that waits past Python's five second default gets "database is
      locked" as its tool's error, never a lost or torn write; claude-mem's store is written only by its own
      worker (VELDO-0187). The suite runs two writer processes at once, one through a conversation's catalog
      bridge and one through the assistant's configuration entry, each adding 200 memories to each ChromaDB
      store, and after both end requires all 400 found by id and by search from a fresh process, the store's
      files held open by exactly one process throughout. Falsifier: Launch AC1's `ava-memory` record as
      mcp_server.py opening the store itself, as myday's `.mcp.json` does today, and the one-opener row must
      fail on the second process holding the store's files open.
    falsified_by: >
      Launch AC1's `ava-memory` record as mcp_server.py opening the store itself, as myday's `.mcp.json`
      does today, and the one-opener row must fail on the second process holding the store's files open.
required_evidence: [unit, integration]
rollback: >
  Restore the owner's assistant MCP configuration bytes setup kept and stop the store servers; remove the
  memory selections from the assistant roles by a new revision while keeping the catalog records and the
  memory itself. No automatic rollback is authorized.
---

## Intent

A conversation searches and saves the owner's memory through the same servers his assistant uses, and
he can see every memory call it makes.

## Context

W143 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. The owner's
requirement (Telegram 29294, lead agreed): conversations use Ava's memory, each part offered as a catalog
MCP server (VELDO-0144). myday's `.mcp.json` starts ava-memory as a stdio server from its own virtual
environment; the knowledge graph is a stdio server of the same shape (knowledge_graph/mcp_server.py) that
`.mcp.json` does not list; memory_kb is a command-line tool the owner's assistant runs from its shell;
claude-mem is a Claude Code plugin with its own search server. memory_kb gets a factory-shipped server
rather than a shell command so each of its calls is a named tool call in the record and its passphrase a
keystore credential, as for every other server. Their
calls are ordinary MCP tool calls, so the record already keeps them once they run in a turn. The owner's
standing rule is no paid model API; mem0's smart extraction is the one memory path that needs one. A
draft: only the owner marks it ready.

## Out of scope

claude-mem's capture of conversation turns, which is VELDO-0187, since its own capture runs from Claude
Code hooks that the everything-off baseline keeps off (VELDO-0155).

## What the reviewer judges

- Normal use: a conversation searches ava-memory for a rule the owner saved, adds a knowledge graph fact,
  searches claude-mem for how a problem was solved last month and memory_kb for last week's session
  summary; the owner's assistant later finds the new fact.
- Threat model: two writers in separate processes, a conversation and the owner's assistant, one losing
  the other's memories; a store opened by a second process beside its store server; the store socket
  reachable by another account; a paid model API key handed to a server; a server pointed at another store
  than the record; a memory call missing from the record; a memory tool taken away from a role.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); faults inside
  the memory servers' own code, which is the owner's assistant's; claude-mem's search
  server answers only while claude-mem's own worker runs, which setup neither starts nor checks (filed).

## Notes

myday's own programs that open a ChromaDB store directly are moved to `veldo memory kb` and the bridge in a
myday change filed with the owner, needed before his first conversation: mem0_memory/cli.py and
memory_kb/cli.py; save-session.sh (cron at 04:00) and sync_confluence.sh (cron at 04:30), which call
`memory_kb/cli.py index-file`; index_telegram.py, index_report.py and memory_kb/confluence_sync.py;
hooks/pre_action_check.py, which calls the mem0 command line on each action; the session-end step myday's
CLAUDE.md runs; and backup.sh, which copies the chromadb directory with tar and must copy through the
store server instead. Until then the store server's start refuses a store one of them holds open, by name.
The memory_kb server the factory ships does not offer the `setup-passphrase` tool: a passphrase given as
tool input would be kept in the run's record; the owner sets it with `veldo memory kb` on the host.

The paid-API rule is checked where a catalog record is saved, so it holds for every server a role can
select, and the receiver's environment strip still holds for the engines.

## History

2026-09-27: new draft for the owner's memory requirement (Telegram 29294). Only the owner marks a
specification ready.

2026-09-27, review of the drafts: AC1 adds memory_kb as a fourth server and names the knowledge graph's
entry point from its code, since myday's `.mcp.json` lists only ava-memory; claude-mem's capture of turns
is no longer deferred and is VELDO-0187. Filed: concurrent ChromaDB writers and claude-mem's worker. Still
a draft.

2026-09-27, third round: concurrent writers are MVP function (the lead's decision), so new AC4 serializes
every write to the two ChromaDB stores through one store server per store that conversations and the
owner's assistant both reach, with a two-writer falsifier, and states that the knowledge graph's SQLite
store already locks; AC1's `ava-memory` and `memory-kb` records launch AC4's bridge, and memory_kb's tools
are answered inside its store server rather than by a cli.py process per call; the filed note on
concurrent writers is withdrawn. Still a draft.

2026-09-27, recheck: AC4 now claims serialization for the writers the factory controls (conversations, the assistant's MCP entries and `veldo memory kb`); the Notes list every myday program that opens a ChromaDB store directly, moved to the bridge in a myday change before the first conversation; the shipped memory_kb server does not offer setup-passphrase.
