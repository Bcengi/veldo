---
schema: veldo.spec/v1
id: VELDO-0158
title: Each Linux run receives exactly its servers' credentials, resolved from the keystore just before spawn and added to the run's redaction set
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W118
plan_revision: 4
depends_on: [VELDO-0039, VELDO-0060, VELDO-0061, VELDO-0141, VELDO-0144, VELDO-0155, VELDO-0156]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_credential*.py"
  - ".veldo/control_credential*.py"
  - "packs/*/.veldo/control_credential*.py"
  - "engine/.veldo/secretref.py"
  - ".veldo/secretref.py"
  - "packs/*/.veldo/secretref.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "packs/*/.veldo/control_launch*.py"
  - "engine/.veldo/control_engine*.py"
  - ".veldo/control_engine*.py"
  - "packs/*/.veldo/control_engine*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0158_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0158-credentials-delivered-to-a-linux-run.md"
  - "specs/index.md"
  - "proof/VELDO-0158/*"
behavior_bearing: true
observability:
  logs: >
    Record each launch's resolved credential ids, the route each took (private file or engine
    environment) and each named refusal; never a credential value.
  metrics: >
    Count launches with credentials, credential ids resolved, and launches refused as
    credential_unavailable, by id.
  traces: >
    Join each dispatch to the catalog revisions and credential ids its configuration resolved.
  error_taxonomy: >
    Distinguish keystore locked, keystore unreachable, reference not found and delivery failed; a launch
    without its server is never run.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Each run receives exactly the credential values its configuration's servers reference,
      through a private file or the engine environment on Linux, never through a command line, the
      packet, the contract or the journal. Set and completeness: Immediately before a spawn the Runner
      resolves the references the dispatch's configuration uses. For Claude Code on Linux the receiver
      writes the generated MCP configuration, values included, into the run's private directory (mode
      0700, under the factory state root, outside the clone) and removes it when the run is reaped; for
      Codex, whose `CODEX_HOME` is the account profile, each secret reaches the engine environment under
      the name the server definition gives it through Codex's `env_vars` or `bearer_token_env_var`
      fields. Inspect every launched process's command line and environment, the packet, the contract and
      the journal. Falsifier: Put a Codex server's secret on the engine command line; the command-line
      check must fail.
    falsified_by: >
      Put a Codex server's secret on the engine command line; the command-line check must fail.
  - id: AC2
    text: >
      Claim: A launch whose credential cannot be resolved is refused by name, and the run never starts
      without its server. Set and completeness: With the keystore locked, with it unreachable, and with a
      reference that resolves to nothing, dispatch a run whose configuration uses that credential and
      require the refusal `credential_unavailable:<id>` before spawn, with no engine process started; a
      run whose configuration needs no credential launches normally in the same state. Falsifier: Launch
      the run without the server when its credential does not resolve; the named-refusal check must fail.
    falsified_by: >
      Launch the run without the server when its credential does not resolve; the named-refusal check
      must fail.
  - id: AC3
    text: >
      Claim: Every value the Runner resolves from the keystore for a run enters that run's set of resolved
      values, so the receiver replaces it in the execution record before the scanner runs (VELDO-0141
      AC4). Set and completeness: Set through the credential route (VELDO-0144 AC2) a credential whose
      value has no known pattern and low entropy, configure a catalog server that references it, and
      dispatch real Claude Code and Codex runs whose configuration uses that server and that print the
      value alone, inside a command's output and in their error stream. Read back each record: every
      occurrence is replaced by the marker naming its kind and no line holds any part of the value; a
      value resolved for one run is not in another run's set. Falsifier: Resolve the keystore value
      without adding it to the run's set; the row requiring the planted keystore value to appear redacted
      must fail.
    falsified_by: >
      Resolve the keystore value without adding it to the run's set; the row requiring the planted
      keystore value to appear redacted must fail.
required_evidence: [unit, integration]
rollback: >
  Refuse by name every launch whose configuration needs a credential; runs that need none continue, and
  catalog revisions, credential records and keystore items are unchanged. No automatic rollback is
  authorized.
---

## Intent

Each run gets the credentials its MCP servers need at the moment it starts, from the keystore, in a
place only that run reads, and a value that reaches the run's output is replaced before it is kept.

## Context

W118 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. Section 3 of the
approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner Telegram
29162) designs delivery to a Linux run and redaction by exact value; its section 12 builds this with
VELDO-0144 in its second stage (item 10). AC1 and AC2 were VELDO-0144 AC3 and AC4, split out on the
third review of revision 4 so VELDO-0144 keeps defining servers and storing credentials and this
specification owns delivering them, with AC3 requiring the keystore's values to enter the per-run set
VELDO-0141 AC4 replaces. This new specification is draft; authoring it supplies neither implementation
proof nor operational activation.

## Out of scope

The catalog and the keystore write (VELDO-0144); the Mac secrets frame (VELDO-0147 AC4); a cloud
keystore; per-run OS users; a connection test button.

## What the reviewer judges

- Normal use: a dispatch's configuration names catalog servers; just before the spawn the Runner
  resolves their credentials from the keystore, the receiver hands each value over through the run's
  private file or the Codex engine environment, and any value the run prints is replaced in its record.
- Threat model: a credential value on a command line, in the packet, the contract or the journal; a run
  launched without its server when its credential does not resolve; a run's private files left behind;
  a run given another server's credential; a keystore value that reaches the record because it was not
  in the run's set. The owner's account, the keystore and the host are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); a worker's
  tools deliberately reading the credentials its own servers use, or reaching the keystore through the
  owner's unconfined keyring daemon (the stated MVP boundary; separate OS users are Release 2); a
  keystore locked after an unattended reboot, which the owner unlocks at the desktop; forged rows in our
  own store and files planted in the installed directory.

## Notes

Resolution goes through secretref's `keychain` scheme, which VELDO-0144 realizes over the Secret
Service. The set of resolved values is the one VELDO-0141 AC4 names; this specification is what puts
the keystore's values in it, and nothing else supplies credential values to a run in Release 1. The
generated MCP configuration and the Codex engine environment it writes into are the ones the
everything-off baselines of VELDO-0155 and VELDO-0156 generate, and the run's private directory is never
the `XDG_RUNTIME_DIR` VELDO-0155 AC4 gives the engine.

**The form of the dispatch configuration it resolves.** VELDO-0127, which records a role's configuration
on each dispatch, is built after this specification, so the resolver reads a dispatch configuration of
this form, which VELDO-0127 later fills from the role's accepted revision: a list of MCP selections, each
naming a catalog server id and revision (VELDO-0144 AC1). For each listed revision the resolver reads that
revision's `mcp_server` record, and the references it resolves are exactly the credential references in
its environment and headers, each a secretref `keychain:<name>` naming a `credential` record; a literal
environment value is passed as it is and resolves nothing. A server not listed contributes nothing, so
no run receives another server's credential. Until VELDO-0127 is built the checks give the dispatch
configuration in this form directly.

Use canonical engine assets and synchronize installed copies. Inventory every asset the selected
journey installs. Compare executable registrations to each criterion's declared universe, observe the
real named interfaces, and retain the driven negative-control diff and named failed row. Fixtures
cannot certify real engine or host behavior. Required evidence labels describe future implementation
proof, not tests run by this writing revision.

## History

2026-09-25: split from VELDO-0144 on the third review of PLAN-0019 revision 4. AC1 and AC2 are VELDO-0144
AC3 and AC4 with their text and falsifiers unchanged; AC3 is new, because VELDO-0141 AC4's redaction of
exact values had nothing that supplied the keystore's values to it, and adding it to VELDO-0144 would
have made five criteria. A draft: only the owner marks a specification ready.

2026-09-25, PLAN-0019 revision 4, fourth review: depends_on adds VELDO-0155 and VELDO-0156, whose
baselines generate the MCP configuration and engine environment AC1 delivers into and whose AC4 gives
the engine its own runtime directory, and the Notes state the form of the dispatch configuration the
resolver reads, since VELDO-0127 is built after this specification. Criteria unchanged. A draft.
