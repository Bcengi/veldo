---
schema: veldo.spec/v1
id: VELDO-0182
title: The factory keeps one memory store record naming where each part of Ava's memory lives, outside every account profile, and hands the same locations to every run on every account
status: draft
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
    Record the memory step of each setup run (done, already done or refused) with each part's location
    and digest of its manifest entry, each memory record revision with the owner's signed command, and each
    launch's handed memory locations; never memory content.
  metrics: >
    Count memory record revisions, setup memory steps by outcome, and account registrations refused for a
    memory location inside their profile.
  traces: >
    Join each run's handed memory locations to the memory record revision it read.
  error_taxonomy: >
    Distinguish a part whose location is missing, a link, or not the owner's own
    (invalid_input:memory:<part>:<reason>), a location inside a registered account profile
    (invalid_input:memory:inside_account_profile:<part>), an account whose profile holds a memory location
    (invalid_input:account_profile:holds_memory:<part>) and a re-run whose manifest differs
    (invalid_input:state_root:differs:memory).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The factory keeps one memory store record naming the one location of each part of the owner's
      assistant memory, laid down by setup from his memory manifest, and every run on every account is
      handed exactly those locations. Set and completeness: Factory setup's `memory` option names a manifest
      with four parts: the file memory directory (one fact per file with its MEMORY.md index, the Claude Code
      auto-memory layout); ava-memory (the myday mem0_memory server's code directory, its interpreter and its
      data directory); the knowledge graph (the myday knowledge_graph server's code directory, interpreter
      and database file); and claude-mem (its MCP search server's command and its data directory). Setup
      checks each location exists, is the owner's own and is not a link, and writes the memory record by the
      owner's signed command; only another signed command revises it. Nothing is copied, because a copy would
      be a second memory: the record points at the bytes the owner's assistant reads and writes today. Each
      launch that hands memory reads the record's current revision and records it. The suite launches turns
      on two accounts of each engine and compares their handed locations. Falsifier: Derive the file memory
      location from the run's own account profile, and the same-on-every-account row must fail on two
      different directories.
    falsified_by: >
      Derive the file memory location from the run's own account profile, and the same-on-every-account row
      must fail on two different directories.
  - id: AC2
    text: >
      Claim: No memory location lies inside a registered account profile, so moving a conversation between
      accounts never changes what it remembers. Set and completeness: Setup refuses a manifest whose
      location of any part lies inside, or contains, the profile directory of any registered account on this
      host (invalid_input:memory:inside_account_profile:<part>), writing nothing, and VELDO-0160 AC1's
      register command refuses an account whose profile directory contains or lies inside a memory location
      (invalid_input:account_profile:holds_memory:<part>), registering nothing. Both compare real paths.
      The suite registers accounts, then sets up memory inside one profile, and sets up memory first and then
      registers an account whose profile holds its directory. Falsifier: Check only at setup, and the
      later-registration row must fail on the registered account.
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
whose data directory sits beside its code), the knowledge graph (myday/knowledge_graph, a database file
beside its code) and the claude-mem Claude Code plugin's session history. Claude Code keeps auto-memory
per profile, and each account is its own profile (VELDO-0160), so without one record a conversation would
forget when it moves accounts at a limit. The servers are VELDO-0183 and the file memory's handoff
VELDO-0184. VELDO-0139 is a standalone built item, so its edge is kept here and not in the plan graph. A
draft: only the owner marks it ready.

## Out of scope

Moving Ava's memory under the factory's state root (the owner may do it later by revising the record);
several owners' memories (Release 3); concurrent-write qualification of the stores (Release 2).

## What the reviewer judges

- Normal use: the owner runs setup with a manifest naming Ava's memory, and a conversation on any of his
  four accounts finds a fact Ava saved yesterday.
- Threat model: a run handed a different memory than the record names; a memory location inside an
  account profile, so a move between accounts changes it; memory copied, so two memories drift; the
  record revised without the owner's signed command; a re-run that rewrites the record.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), such as the
  owner moving a memory directory by hand after setup (the launch refuses the missing location by name);
  forged rows in our own store.

## Notes

The factory owns the record and the handing in; the bytes stay shared with the owner's assistant, which
is what "the same memory" means.

## History

2026-09-27: new draft for the owner's memory requirement (Telegram 29294). Only the owner marks a
specification ready.
