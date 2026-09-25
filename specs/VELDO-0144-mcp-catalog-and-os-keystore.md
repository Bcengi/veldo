---
schema: veldo.spec/v1
id: VELDO-0144
title: MCP servers defined once as versioned catalog records, with credentials only in the host OS keystore
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W104
plan_revision: 4
depends_on: [VELDO-0039, VELDO-0047, VELDO-0060, VELDO-0061, VELDO-0130]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_mcp_catalog*.py"
  - ".veldo/control_mcp_catalog*.py"
  - "packs/*/.veldo/control_mcp_catalog*.py"
  - "engine/.veldo/control_credential*.py"
  - ".veldo/control_credential*.py"
  - "packs/*/.veldo/control_credential*.py"
  - "engine/.veldo/secretref.py"
  - ".veldo/secretref.py"
  - "packs/*/.veldo/secretref.py"
  - "engine/.veldo/control_api*.py"
  - ".veldo/control_api*.py"
  - "packs/*/.veldo/control_api*.py"
  - "engine/.veldo/control_runner*.py"
  - ".veldo/control_runner*.py"
  - "packs/*/.veldo/control_runner*.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "packs/*/.veldo/control_launch*.py"
  - "engine/.veldo/control_engine*.py"
  - ".veldo/control_engine*.py"
  - "packs/*/.veldo/control_engine*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0144_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0144-mcp-catalog-and-os-keystore.md"
  - "specs/index.md"
  - "proof/VELDO-0144/*"
behavior_bearing: true
observability:
  logs: >
    Record each catalog save (server id, revision, actor), each credential write, replacement or
    deletion (credential id, set by) and each launch's resolved credential ids or named refusal;
    never a credential value.
  metrics: >
    Count catalog revisions, credential writes and launches refused as credential_unavailable, by id.
  traces: >
    Join each dispatch to the catalog revisions and credential ids its configuration resolved.
  error_taxonomy: >
    Distinguish stale or unauthorized save, invalid server definition, keystore locked, keystore
    unreachable, reference not found and delivery failed; a launch without its server is never run.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: MCP servers are defined once, through a typed API route and the authority's command, as
      versioned catalog records whose every save is a new immutable revision, and Atlassian is one of
      them. Set and completeness: Save a stdio server and an http server through the API's catalog
      route (a passkey session, VELDO-0130) and the authority's catalog command, then a second revision
      of each; compare every field of `mcp_server` (id, revision, label, transport, command and
      arguments, url, environment as literals or credential references, headers as credential
      references, the hosts it can run on, and the tools the owner marks read-only) with the stored
      revisions, and reject a stale or unauthorized save by name. Configure the Atlassian server as an
      ordinary catalog server with its credential in the keystore; no claude.ai connector is used.
      Falsifier: Overwrite a saved server revision in place; the revision-history check must fail.
    falsified_by: >
      Overwrite a saved server revision in place; the revision-history check must fail.
  - id: AC2
    text: >
      Claim: A credential's value is written to and read from the host OS keystore only, and the store
      keeps only its reference. Set and completeness: Set a credential through the server form's
      write-only field; the value travels once over TLS inside the passkey session to the API's
      credential route and on to the authority's credential command, which writes it to the Secret
      Service through `secret-tool`'s standard input and commits a `credential` record with id, label,
      reference, set at and set by, and nothing else; resolving it realizes secretref's `keychain`
      scheme. During and after the write, search the store, the journal, the event feed, proof, logs and
      every process command line for the value, and require it in none; replace and delete a value
      through the route, and require every read-back attempt refused. Falsifier: Pass the value to
      `secret-tool` as a command-line argument; the no-value-on-command-line check must fail.
    falsified_by: >
      Pass the value to `secret-tool` as a command-line argument; the no-value-on-command-line check
      must fail.
  - id: AC3
    text: >
      Claim: Each run receives exactly the credential values its configuration's servers reference,
      through a private file or the engine environment on Linux and through a secrets frame on the Mac,
      never through a command line, the packet, the contract or the journal. Set and completeness:
      Immediately before a spawn the Runner resolves the references the dispatch's configuration uses.
      For Claude Code on Linux the receiver writes the generated MCP configuration, values included,
      into the run's private directory (mode 0700, under the factory state root, outside the clone) and
      removes it when the run is reaped; for Codex, whose `CODEX_HOME` is the account profile, each
      secret reaches the engine environment under the name the server definition gives it through
      Codex's `env_vars` or `bearer_token_env_var` fields. For a Mac run, after the release and before
      the wrapper execs, the receiver writes one secrets frame over the same SSH channel; the wrapper
      reads exactly that frame, writes the run's private file (mode 0600 in a 0700 directory) and only
      then execs, the receiver removes that directory over SSH when the run ends, the journal records
      only the credential ids delivered, and nothing is written to the Mac's keychain. Inspect every
      launched process's command line and environment, the packet, the contract and the journal.
      Falsifier: Put a Codex server's secret on the engine command line; the command-line check must
      fail.
    falsified_by: >
      Put a Codex server's secret on the engine command line; the command-line check must fail.
  - id: AC4
    text: >
      Claim: A launch whose credential cannot be resolved is refused by name, and the run never starts
      without its server. Set and completeness: With the keystore locked, with it unreachable, and with a
      reference that resolves to nothing, dispatch a run whose configuration uses that credential and
      require the refusal `credential_unavailable:<id>` before spawn, with no engine process started;
      a run whose configuration needs no credential launches normally in the same state. Falsifier:
      Launch the run without the server when its credential does not resolve; the named-refusal check
      must fail.
    falsified_by: >
      Launch the run without the server when its credential does not resolve; the named-refusal check
      must fail.
required_evidence: [unit, integration]
rollback: >
  Stop accepting catalog saves and credential writes; recorded revisions, credential records and
  keystore items stay as they are, and runs that need a credential refuse by name. No automatic
  rollback is authorized.
---

## Intent

MCP servers are defined in the UI and saved once, and every role selects them by reference instead of
carrying its own copy of each definition. Their credentials live in the local OS keystore, so a secret
never sits in the store, the journal, proof, logs or a command line; a cloud keystore replaces the
local one later through the same references if the factory runs in the cloud.

## Context

W104 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. Section 3 of the
approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner Telegram
29162) designs the catalog, the credential's two halves and each delivery route. VELDO-0127 (amended)
refers to catalog revisions instead of embedding definitions. `.veldo/secretref.py` (PLAN-0013) names
a secret by a reference such as `keychain:<name>` and resolves it only at use into a handle that never
prints its value, with only a test store behind it; `.veldo/secret_scan.py` detects credential shapes.
VELDO-0141 replaces each run's exact resolved values in its execution record before the scanner runs.

## Out of scope

A cloud keystore, per-run OS users, credential rotation reminders, the claude.ai connectors, storing
MCP credentials in the Mac keychain, and a connection test button.

## What the reviewer judges

- Normal use: the owner adds a server in the UI's catalog form and types its credential into a
  write-only field; roles select the server by id and revision; each run gets the resolved values it
  needs, on Linux or the Mac, and nothing else.
- Threat model: a credential value in the store, journal, event feed, proof, logs, a command line, the
  packet, the contract or the Mac keychain; a value read back through the UI or API; a saved revision
  overwritten; a run launched without its server when its credential does not resolve; a run's private
  files left behind; a run given another server's credential. The owner's account, the keystore, the
  host and the Mac over SSH are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); a worker's
  tools deliberately reading the credentials its own servers use, or reaching the keystore through the
  owner's unconfined keyring daemon (the stated MVP boundary; separate OS users are Release 2); a
  keystore locked after an unattended reboot, which the owner unlocks at the desktop; forged rows in our
  own store and files planted in the installed directory.

## Notes

On Linux the keystore is the Secret Service of the GNOME keyring daemon already running in the owner's
session, reached through the `secret-tool` executable of the distribution's libsecret-tools package
(0.21.4 in this release's archive, not yet installed; GNOME's libsecret, LGPL-2.1+ with GPL-2+ parts),
run as a separate process and never linked. Installing it is the owner's one-time setup step. The
command's observation and journal entry exclude the value field by name.

The Linux legs are built first; the Mac secrets frame of AC3 is qualified when VELDO-0124 and
VELDO-0125 land, the way VELDO-0060 and VELDO-0061 qualify their Mac configuration in the host stage.

## History

2026-09-25: written as a draft for PLAN-0019 revision 4 from the approved operating-model design
(Telegram 29162), section 3(e). Draft; the owner decides readiness.
