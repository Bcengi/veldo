---
schema: veldo.spec/v1
id: VELDO-0183
title: Ava's ava-memory, knowledge graph and claude-mem servers are catalog MCP servers over the one memory store, never handed a paid model API, and every memory call is in the run's record
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
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
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
    Record each memory server's catalog revision with the memory record revision it reads, each catalog
    save refused for a paid-API name, and each run's memory servers as names; never memory content or a
    credential.
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
    server).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Setup defines ava-memory, the knowledge graph and claude-mem as catalog MCP server records
      launched as the owner's assistant launches them today and pointing at the one memory store, and the
      seeded assistant roles select all three with all their tools. Set and completeness: From the memory
      record (VELDO-0182), setup saves three VELDO-0144 catalog records by the owner's signed command:
      `ava-memory` (the mem0_memory interpreter running mcp_server.py in its code directory, as myday's
      `.mcp.json` launches it), `knowledge-graph` (the knowledge_graph interpreter running its mcp_server.py)
      and `claude-mem` (its search server's command from the manifest), each reading the record's location
      of its data. Setup adds each to the `assistant` and `assistant_codex` roles of VELDO-0177 AC2 as an
      `always` selection of all tools, as a new role revision. The init event of a turn on each engine lists
      the three servers connected with every tool each registers. Falsifier: Seed the roles without
      `claude-mem`, and the init row must fail on the missing server.
    falsified_by: >
      Seed the roles without `claude-mem`, and the init row must fail on the missing server.
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
      missing-key message, while `memory_search`, `memory_add` and every knowledge graph and claude-mem tool
      work. Falsifier: Accept `ANTHROPIC_API_KEY` as the ava-memory record's credential, and the paid-API row
      must fail on the saved revision.
    falsified_by: >
      Accept `ANTHROPIC_API_KEY` as the ava-memory record's credential, and the paid-API row must fail on the
      saved revision.
  - id: AC3
    text: >
      Claim: Every memory read and write is a tool call in the run's execution record, and a write in one
      conversation is found by another conversation and by the owner's assistant, because it is the one
      store. Set and completeness: Each call to a memory server's tool is kept in the turn's execution record
      (VELDO-0141 AC1) with its input and result, redacted as every line is. The suite runs fixture copies of
      the three servers over one fixture store: conversation A adds a memory and a knowledge graph fact;
      conversation B, on another account, finds both by search; and the fixture's own server, started as
      myday's `.mcp.json` starts it, finds them too. Falsifier: Hand each conversation its own copy of the
      data directory, and the cross-conversation row must fail on B's empty search.
    falsified_by: >
      Hand each conversation its own copy of the data directory, and the cross-conversation row must fail
      on B's empty search.
required_evidence: [unit, integration]
rollback: >
  Remove the memory selections from the assistant roles by a new revision while keeping the catalog
  records and the memory itself. No automatic rollback is authorized.
---

## Intent

A conversation searches and saves the owner's memory through the same servers his assistant uses, and
he can see every memory call it makes.

## Context

W143 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. The owner's
requirement (Telegram 29294, lead agreed): conversations use Ava's memory, each part offered as a catalog
MCP server (VELDO-0144). myday's `.mcp.json` starts ava-memory and the knowledge graph as stdio servers
from their own virtual environments; claude-mem is a Claude Code plugin with its own search server. Their
calls are ordinary MCP tool calls, so the record already keeps them once they run in a turn. The owner's
standing rule is no paid model API; mem0's smart extraction is the one memory path that needs one. A
draft: only the owner marks it ready.

## Out of scope

claude-mem's session capture, which runs from its Claude Code hooks, and the everything-off baseline
keeps hooks off (VELDO-0155); the factory keeps a conversation's history itself (VELDO-0176), and capturing
factory turns into claude-mem is filed for Release 2. Concurrent-write qualification of the stores
(Release 2).

## What the reviewer judges

- Normal use: a conversation searches ava-memory for a rule the owner saved, adds a knowledge graph fact,
  and searches claude-mem for how a problem was solved last month; the owner's assistant later finds the
  new fact.
- Threat model: a paid model API key handed to a server; a server pointed at another store than the
  record; a memory call missing from the record; a memory tool taken away from a role.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); faults inside
  the memory servers' own code, which is the owner's assistant's.

## Notes

The paid-API rule is checked where a catalog record is saved, so it holds for every server a role can
select, and the receiver's environment strip still holds for the engines.

## History

2026-09-27: new draft for the owner's memory requirement (Telegram 29294). Only the owner marks a
specification ready.
