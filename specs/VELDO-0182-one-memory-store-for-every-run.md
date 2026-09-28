---
schema: veldo.spec/v1
id: VELDO-0182
title: The factory keeps one memory store record naming where each part of Ava's memory lives, none containing an account profile, hands the same locations to every run on every account, and checks no memory is lost when a store is switched
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W142
plan_revision: 4
depends_on: [VELDO-0139, VELDO-0144, VELDO-0160, VELDO-0171]
placement: [contracts, engine, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_memory*.py"
  - ".veldo/control_memory*.py"
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "engine/.veldo/control_accounts.py"
  - ".veldo/control_accounts.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_service*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "bin/veldo"
  - "engine/bin/veldo"
  - "scripts/suites/*_veldo_0182_*.py"
  - "scripts/suites/73_veldo_0139_factory_setup.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0182-one-memory-store-for-every-run.md"
  - "specs/index.md"
  - "proof/VELDO-0182/*"
behavior_bearing: true
observability:
  logs: >
    Record the memory step of each setup run (done, already done or refused) with each part's code
    directory, its fixed data path and the digest of its manifest entry, each part's copy with its path and
    each check with its count and sample size, each memory record revision with
    the owner's signed command, and each launch's handed memory locations; never memory content.
  metrics: >
    Count memory record revisions, setup memory steps by outcome, memory checks by outcome, and account registrations refused for a
    profile inside a memory location.
  traces: >
    Join each run's handed memory locations to the memory record revision it read.
  error_taxonomy: >
    Distinguish a part whose code directory, interpreter or fixed data path is missing, a link, or not the
    owner's own (invalid_input:memory:<part>:<reason>), a memory location that contains a registered
    account profile (invalid_input:memory:contains_account_profile:<part>), an account whose profile lies
    inside a memory location (invalid_input:account_profile:inside_memory:<part>) and a re-run whose
    manifest differs (invalid_input:state_root:differs:memory) and a switch after which a store holds fewer memories
    or misses a sampled one (missing_evidence:memory:<part>:lost).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The factory keeps one memory store record naming the one location of each part of the owner's
      assistant memory, laid down by setup from his memory manifest, and every run on every account is
      handed exactly those locations. Set and completeness: Factory setup's `memory` option names a manifest
      with five parts: the file memory directory (one fact per file with its MEMORY.md index, the Claude
      Code auto-memory layout); ava-memory (the myday mem0_memory code directory and its interpreter);
      the knowledge graph (the myday knowledge_graph code directory and its interpreter); memory_kb (the
      myday memory_kb code directory, the session-summary knowledge base, and its interpreter); and
      claude-mem (its installed plugin directory, whose version VELDO-0187 reads, its search server's
      command and its data directory, all named since its code is not in our repositories), and beside them
      the path of the owner's assistant's MCP configuration (myday's `.mcp.json`), whose memory entries
      VELDO-0183 AC4 points at the store servers. The first three servers' data paths are fixed in their
      code, not configurable, so the manifest names code directories and setup checks the fixed data path
      under each: mem0_memory's `data` directory (config.py DATA_DIR, holding `chromadb` and `history.db`),
      knowledge_graph's `knowledge_graph.db` (db.py DB_PATH) and memory_kb's `data/chromadb` (kb/config.py
      DB_PATH). Setup checks each location exists, is the owner's own and is not a link, and writes the memory
      record by the owner's signed command; only another signed command revises it. Nothing is copied for use,
      because a copy would be a second memory (AC4's one copy is a safety copy no run is handed): the record points at the bytes the owner's assistant reads and writes
      today. Each launch that hands memory reads the record's current revision and records it. The suite
      launches turns on two accounts of each engine and compares their handed locations, and sets up a
      manifest whose knowledge_graph directory lacks `knowledge_graph.db`. Falsifier: Derive the file memory
      location from the run's own account profile, and the same-on-every-account row must fail on two
      different directories.
    falsified_by: >
      Derive the file memory location from the run's own account profile, and the same-on-every-account row
      must fail on two different directories.
  - id: AC2
    text: >
      Claim: No memory location contains a registered account profile, so a run handed memory is never
      handed an account's login with it, while memory that lies inside a profile, as Ava's file memory does
      today, is accepted. Set and completeness: Setup refuses a manifest whose location of any part
      contains the profile directory of any registered account on this host
      (invalid_input:memory:contains_account_profile:<part>), writing nothing, and VELDO-0160 AC1's register
      command refuses an account whose profile directory lies inside a memory location
      (invalid_input:account_profile:inside_memory:<part>), registering nothing. A memory location inside
      a profile is not refused, because the record names it and no run finds it through the profile. Both
      compare real paths. The suite registers accounts, then sets up memory whose file memory directory
      contains one profile; sets up memory first and then registers an account whose profile lies inside
      the knowledge_graph directory; and sets up a file memory directory inside a registered profile, which
      is accepted. Falsifier: Check only at setup, and the later-registration row must fail on the
      registered account.
    falsified_by: >
      Check only at setup, and the later-registration row must fail on the registered account.
  - id: AC3
    text: >
      Claim: Running setup again with the same memory manifest changes nothing, and on a host laid down
      before this change it adds only the memory record. Set and completeness: The memory step follows
      VELDO-0171 AC4's re-run rule: the record equal to the one it would write is left alone, an absent one
      is written by the owner's signed command under VELDO-0171 AC1's lock rule, and a manifest that differs
      from the record is refused by name (invalid_input:state_root:differs:memory), writing nothing; a new
      manifest goes through the owner's revise command. After a second run over a complete host the store's
      journal head is unchanged. Falsifier: Write a new record revision on every run, and the second-run row
      must fail on the changed journal head.
    falsified_by: >
      Write a new record revision on every run, and the second-run row must fail on the changed journal
      head.
  - id: AC4
    text: >
      Claim: Before a memory store is first switched, it is copied aside once, and after each switch a
      light check finds the store still holds its memories, so a switch that loses memory stops and names
      the store and its copy. Set and completeness: `veldo memory check <part> before` copies the part's
      data location to `<state root>/memory/copies/<part>` (0700, the owner's own, never named in the
      memory record and never handed to a run) the first time it runs for that part and never again, a
      SQLite database through SQLite's online backup so the copy is whole while the owner's assistant runs;
      it then counts the part's memories and picks 20 at random (all of them when fewer) and saves the count
      and the sample beside the copy. `veldo memory check <part> after` requires at least the count `before` saved and each
      sampled memory found by its id and by a search for its own text, through the part's own functions:
      mem0_memory's memory_store get and search, knowledge_graph's db get_entity and search_entities,
      memory_kb's kb store collection get by document id and kb search, claude-mem's search server, and for the file memory
      the file by name and a search of the directory for its text. Otherwise it refuses by name
      (missing_evidence:memory:<part>:lost), naming the store and the copy's path, and the step that switched
      it stops. The switches that run it around themselves are this memory step for each part it first
      names, VELDO-0183 AC4's first start of each store server and its rewrite of the assistant's MCP
      entries, and the owner's assistant's own switch in the myday change VELDO-0183's Notes file. One row
      sets up memory over fixture stores of all five parts, finds each part's copy holding its memories,
      then for each of the five parts removes one sampled memory and adds another between `before` and
      `after`, the count unchanged, and requires the refusal naming that part and its copy. Falsifier: Have `after` count the memories in the copy in
      place of the switched store, and the removed-memories row must fail on a check that passes.
    falsified_by: >
      Have `after` count the memories in the copy in place of the switched store, and the removed-memories
      row must fail on a check that passes.
required_evidence: [unit, integration]
rollback: >
  Stop handing memory to runs while keeping the memory record; the memory itself is the owner's and is
  never changed by a rollback. No automatic rollback is authorized.
---

## Intent

Conversations use the same memory the owner's assistant Ava uses today, and remember the same things
whichever of his accounts runs them.

## Context

W142 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. The owner asked
(Telegram 29294): "What about memory? How will it work? Can we borrow Ava's setup?", and the lead agreed.
Ava's memory is our own code in myday: the file memory, ava-memory (myday/mem0_memory, a semantic store
whose data directory config.py fixes beside its code), the knowledge graph (myday/knowledge_graph, a
database file db.py fixes beside its code), memory_kb (myday/memory_kb, the session-summary knowledge base,
a command-line tool whose ChromaDB store kb/config.py fixes under its own `data` directory) and the
claude-mem Claude Code plugin's session history. Claude Code keeps auto-memory per profile, and each
account is its own profile (VELDO-0160), so without one record a conversation would forget when it moves
accounts at a limit. Ava's file memory itself lives inside a Claude Code profile today, so AC2 refuses
only the other direction: a memory location wide enough to hold an account's login. The servers are
VELDO-0183, the file memory's handoff VELDO-0184, and the capture of conversation turns into claude-mem
VELDO-0187. VELDO-0139 is a standalone built item, so its edge is kept here and not in the plan graph. A
draft: only the owner marks it ready.

## Out of scope

Moving Ava's memory under the factory's state root (the owner may do it later by revising the record);
several owners' memories (Release 3); how the stores serialize concurrent writers (VELDO-0183 AC4).

## What the reviewer judges

- Normal use: the owner runs setup with a manifest naming Ava's memory, and a conversation on any of his
  four accounts finds a fact Ava saved yesterday.
- Threat model: a run handed a different memory than the record names; a memory location that holds an
  account profile, so a run with memory access reaches that account's login; memory copied, so two
  memories drift; the record revised without the owner's signed command; a re-run that rewrites the
  record; a manifest whose data path is not where the server's code reads it; a switch that loses
  memories and nobody notices, or a store switched with no copy to go back to.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), such as the
  owner moving a memory directory by hand after setup (the launch refuses the missing location by name);
  forged rows in our own store.

## Notes

The factory owns the record and the handing in; the bytes stay shared with the owner's assistant, which
is what "the same memory" means.

AC4 is deliberately light (owner, Telegram 29310): one copy per part and a count with a sample of 20, not a
census of every memory. The count is taken just before and just after a switch; running the step again
takes a fresh `before` while the first copy stays.

## History

2026-09-27: new draft for the owner's memory requirement (Telegram 29294). Only the owner marks a
specification ready.

2026-09-27, review of the drafts: memory_kb is the fifth part; mem0 and the knowledge graph fix their data
paths in code, so the manifest names code directories and setup checks those fixed paths; AC2 keeps only
the "contains" refusal and drops "lies inside a profile", which would refuse Ava's real file memory. Still
a draft.

2026-09-27, third round: AC1's manifest also names the owner's assistant's MCP configuration, which
VELDO-0183 AC4 points at the store servers that serialize concurrent writers; Out of scope names AC4.
Criterion meaning otherwise unchanged. Still a draft.

2026-09-27: marked ready by the owner (Telegram 29301, "All ready otherwise"), with his two points applied: plain-words commands (29299) and smart add on the subscription instead of a paid API (29300).

2026-09-28: the owner asked that no memory be lost when memory moves (Telegram 29306), and then that the
check stay light (29310, "Don't need overkill for memory, just a light check is fine that it's still
there"). New AC4: before a store's first switch it is copied aside once, and after each switch `veldo
memory check` finds at least the number of memories it saved and a random sample of 20 by id and by search, or stops
and names the store and the copy; VELDO-0183 AC4's switch and the owner's assistant's myday switch run the
same check. The title names it. Asked by the owner; back to draft: the owner must re-mark it ready.

2026-09-28: marked ready by the owner (Telegram 29313, "Ok approved"), after the fresh check's text fixes.
