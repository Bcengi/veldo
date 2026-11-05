---
schema: veldo.spec/v1
id: VELDO-0257
title: Every credential path that existing features open into a run moves behind the outside gate and the old path is removed, while programs outside Veldo keep their own credentials until each is retired
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0158, VELDO-0177, VELDO-0181, VELDO-0183, VELDO-0249, VELDO-0251, VELDO-0252, VELDO-0254, VELDO-0256]
placement: [engine, enforcement, distribution]
protected_paths: [".veldo/control_credential_delivery.py", "engine/.veldo/control_credential_delivery.py"]
footprint:
  - ".veldo/control_credential_delivery.py"
  - "engine/.veldo/control_credential_delivery.py"
  - ".veldo/control_launch*.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_mcp_catalog.py"
  - "engine/.veldo/control_mcp_catalog.py"
  - ".veldo/control_memory*.py"
  - "engine/.veldo/control_memory*.py"
  - ".veldo/control_factory_setup*.py"
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_conversation*.py"
  - "engine/.veldo/control_conversation*.py"
  - ".veldo/control_engine_*.py"
  - "engine/.veldo/control_engine_*.py"
  - "docs/outside-services.md"
  - "scripts/suites/*_veldo_0257_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0257-existing-credential-deliveries-into-runs-move-behind-the-outside-gate.md"
  - "specs/index.md"
  - "proof/VELDO-0257/**"
behavior_bearing: true
observability:
  logs: >
    Setup writes one line per catalog record it moves behind the gate (record, the gate service it became,
    the keystore reference it kept by name) and one line per role revision it changes. The launcher's
    record of a run names the gate services the run selected, never a credential reference or value. A
    write a conversation turn raised is logged with its decision id and, once settled, the dispatch that
    sent it.
  metrics: >
    Records moved behind the gate; launches refused as credential_in_run; conversation writes raised,
    approved, refused and sent; memory tool calls through the gate by classification.
  traces: >
    A conversation write joins the turn that raised it, the decision that settled it, the token id of
    VELDO-0252 and the gate access line of the dispatch that sent it.
  error_taxonomy: >
    unsupported_configuration:credential_in_run:<record> (VELDO-0251 AC2; a run selecting a record that
    carries a keychain reference), approval_required (a write a turn sent with no settled decision),
    memory_socket_refused (a run's attempt to reach a host store server directly). No other new names.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: a conversation turn reaches its role's credentialed servers and the web only through the gate,
      with no credential and no direct network in the run. Set: the delivery of VELDO-0158 that VELDO-0177
      AC1 uses for conversation runs no longer resolves keystore references into the run; each catalog
      record with a keychain reference is served behind the gate and the turn reaches it through
      VELDO_SERVICE_<NAME>_URL or the gate MCP endpoint; the assistant roles' web fetch uses the read route
      of VELDO-0256, and an engine's own sandbox network grant for a role is off. Completeness: every
      conversation and project launch path reads the same selection. Rows, on each engine: the fixture
      engine finds no credential file and no canary value anywhere it can read; a turn's tool call to a
      credentialed fixture server answers through the gate; a turn fetches a fixture page through the
      read route; a direct fetch fails.
    falsified_by: >
      Keep VELDO-0158's resolution for conversation runs; the canary scan row finds the fixture credential
      in the run and fails.
  - id: AC2
    text: >
      Claim: memory servers an installation declares are services behind the gate, their store secrets stay
      gate side, and no run reaches a store server or a host loopback service directly. Set: each memory
      server of VELDO-0183 that carries a credential reference or reaches a host store server (over a Unix
      socket or host loopback) runs behind the gate as an MCP service; its passphrase-style credential is
      resolved gate side; the run reaches only the gate endpoint. Each tool is classified by VELDO-0251 AC3:
      a tool the installation wants to pass without per-call approval is a reviewed exact read override,
      and a tool with no such override is a write. Rows: a run's memory search and add through the gate
      answer from the one fixture store; the run's connect to the store server's socket path and to the
      session-history worker's loopback port fail; the passphrase canary appears nowhere in the run; an
      unannotated tool with no override asks for approval.
    falsified_by: >
      Keep the stdio bridge in the run reaching the store server's socket; the socket row connects and
      fails.
  - id: AC3
    text: >
      Claim: an outward write a conversation turn wants is a factory decision, and the owner's answer
      approves that exact request for a later dispatch; a plain reply never releases a write. Set: VELDO-0181's
      path in which the owner's plain reply is the next turn and the tool writes with credentials it holds
      is replaced: the turn submits the exact request to the approval service (VELDO-0249 as amended,
      VELDO-0252) and raises a decision naming it; the owner's settled answer yields the approval for that
      request; the write is sent once, through the gate, by the next dispatch of the conversation. Rows: a
      turn asks to write and the owner replies yes in plain words without settling the decision, and the
      write is refused approval_required; after the decision settles, the next dispatch's write passes once
      and a repeat is refused; the run never holds the token.
    falsified_by: >
      Treat the owner's plain reply as the approval; the plain-reply row sends the write and fails.
  - id: AC4
    text: >
      Claim: the old delivery paths are removed, not switched off, and moving a credential behind the gate
      leaves the copies held by programs outside Veldo untouched until the owner retires each. Set: the code
      in control_credential_delivery that resolves a keystore reference into a run's configuration or
      environment is deleted, and a run selecting a credential-bearing record is refused as
      unsupported_configuration:credential_in_run:<record>; setup's move of a credential into the keystore
      for the gate reads the owner's input and writes only the keystore, never a file of another program;
      docs/outside-services.md states the end state (each host program off its own copy) and how to retire
      one service at a time, not as a setup step. Rows: a static row finds no resolution of a keystore
      reference on any run launch path; a selection of a credential-bearing record is refused at launch;
      a fixture host program's credential file is byte for byte unchanged after setup moves its credential.
    falsified_by: >
      Leave the resolution code behind a switch; the static row finds it and fails.
required_evidence: [unit, integration]
rollback: >
  Revert the change. VELDO-0158 delivery into runs, the in-run memory bridge and VELDO-0181's plain-reply
  path return as built; gate service declarations made by setup stay in the installation repository,
  inert. Keystore items are untouched. No automatic rollback, retry or recovery is authorized.
---

## Intent

Three features already built on branches in flight open credential paths into runs: conversation runs get
their servers' credentials, memory servers get their store passphrase and reach host store servers from
inside the run, and a plain reply lets a tool write with the credentials it holds. They land as built
because they serve today's setup. Once the gate and its check service exist, this ticket moves each onto
the gate and removes the old path, so no credential but the engine's own login is ever in a run.

## Context

- VELDO-0177 AC1 delivers each conversation role's server credentials through VELDO-0158, and AC2 grants
  the assistant roles web fetch and an engine sandbox with network access.
- VELDO-0183 gives a memory server a passphrase credential reference and bridges from the run to host
  store servers over a Unix socket; its session-history server needs a worker on host loopback.
- VELDO-0181's out-of-scope text lets the owner's plain reply be the next turn, with the tool acting
  through its own configured credentials.
- VELDO-0251 AC2 refuses a credential-bearing record in a run; VELDO-0254 closes every direct path out;
  VELDO-0256 gives runs their web reads back through the gate.
- An installation moving to the gate usually has other programs on the host that use the same vendor
  credentials from their own files; Veldo does not launch them and must not break them.

## Design

Per feature: declare the credentialed server as a gate service, point the role at it, delete the old
resolution, and prove with canaries that nothing is left in the run. Conversation writes go through the
same exact-request approval as every other write, sent by the next dispatch.

## Out of scope

- The gate, the check, the approval service and the read routes themselves.
- Retiring host programs' own credential copies, which is installation practice the guide describes.
- Changing what memory servers store or how they serialize writes.

## What the reviewer judges

- Normal use: after landing, a conversation on each engine searches memory, reads a credentialed service,
  fetches a page and asks for one write that the owner approves, all with no credential in the run, while
  the owner's other host programs keep working.
- Threat model: a credential left in a run by a path not migrated, a run reaching a store server's socket,
  a plain reply taken as approval, a migration that edits another program's credential file.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962).

## History

2026-11-04: new draft, Telegram 39145, from research/veldo-plan-consistency-review-2026-11-04.md (A1, A2,
A6, A10, A13, A14, C4 for VELDO-0181, C8, C13, C21, D9, E2) and the lead's rulings
research/veldo-plan-rulings-2026-11-04.md (R2: VELDO-0177, VELDO-0183 and VELDO-0181 land as built and one
ticket migrates them after VELDO-0251 and VELDO-0252; R5 memory services behind the gate; R7). Standalone;
no plan work item.
