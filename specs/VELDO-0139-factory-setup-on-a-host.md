---
schema: veldo.spec/v1
id: VELDO-0139
title: Set up a real factory on this host with the owner's own signed commands
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0025, VELDO-0029, VELDO-0047, VELDO-0064, VELDO-0065, VELDO-0067, VELDO-0073, VELDO-0138]
placement: [engine, tracker, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "packs/*/.veldo/control_factory_setup*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "bin/veldo"
  - "engine/bin/veldo"
  - "scripts/suites/*_veldo_0139_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0139-factory-setup-on-a-host.md"
  - "specs/index.md"
  - "proof/VELDO-0139/*"
behavior_bearing: true
acceptance_criteria:
  - id: AC1
    text: >
      Claim: One owner command, veldo factory setup, lays down a new factory on this host from the
      existing pieces: the store under the given state root, the membership bootstrap signed by the
      owner's own key, this host's trust naming its identity and enrollment signers, the enrollment of
      the named workspace clone, and the authority service installed through VELDO-0047's installer.
      Set and completeness: Run it over an empty 0700 state root owned by the account and read back the
      store, the owner's membership, the host trust, the workspace binding and the installed unit;
      refuse by name, writing nothing, when the state root is absent, not 0700, not the account's, or
      already holds a store, trust or binding. Falsifier: Overwrite an existing store; the no-overwrite
      check must fail.
    falsified_by: >
      Overwrite an existing store; the no-overwrite check must fail.
  - id: AC2
    text: >
      Claim: The same setup enrolls the Telegram edge and the owner's chat and writes the ingress
      configuration without ever copying the token. Set and completeness: The edge key is generated in
      the protected key directory and enrolled with its possession proof by the owner's signed command
      (VELDO-0067); the owner's chat is enrolled from the chat id he gives (VELDO-0064/0065); the 0600
      VELDO-0073 ingress configuration names the account's own 0600 token file; the service starts
      inert (not_activated). Read each back; search the state root, the install root and the
      configuration for the token bytes. Falsifier: Write a copy of the token into the configuration
      or the state root; the no-token-copy check must fail.
    falsified_by: >
      Write a copy of the token into the configuration or the state root; the no-token-copy check must
      fail.
  - id: AC3
    text: >
      Claim: After setup, VELDO-0138's live qualification runs on the real factory with no other
      preparation. Set and completeness: Against a loopback stand-in, run setup, start the service,
      veldo channel qualify with the owner's key, open one decision request, reply as the owner,
      activate; the edge is active and the qualification recorded by the service's own gate. The real
      Telegram leg is run once by the lead with the owner and recorded; fixtures never count as it.
      Falsifier: Accept a genesis command not signed by the owner's key; the owner-genesis check must
      fail.
    falsified_by: >
      Accept a genesis command not signed by the owner's key; the owner-genesis check must fail.
required_evidence: [unit, integration]
rollback: >
  Stop and uninstall the service with VELDO-0047's lifecycle; the state root and host trust are left
  for the owner to remove by hand, never deleted by the setup.
---

## Intent

Every part a running factory needs exists and is proved, but nothing assembles them on a real host:
the suites build a factory with test harnesses. This is the one owner-run setup that lays a real
factory down, so the live qualification (VELDO-0138) and the rest of the journey run on it.

## Context

Found on 2026-09-25 when the lead prepared the real-factory live qualification: the owner created
the state root /var/lib/veldo (Telegram 29101-29106) and no production path existed to set up the
store, trust, enrollments and ingress configuration. No specification owned it.

## Out of scope

Other hosts and packs, adoption of an existing repository's history, migration and rollback of a
running factory (Release 4); restart recovery (Release 2); a second owner (Release 3).

## What the reviewer judges

- Normal use: the owner runs veldo factory setup once on this host, naming the state root, his own
  signing key, the workspace clone, his Telegram chat id and the account's own 0600 token file. It
  creates the store and signs the membership bootstrap with his key, writes this host's trust,
  enrolls the workspace, enrolls the Telegram edge key with its possession proof and his chat, writes
  the 0600 ingress configuration naming the token file, and installs the authority service, which
  starts inert. The live qualification then runs through it.
- Threat model: an existing store, trust or binding overwritten; a state root that is absent, shared
  or loosely permissioned accepted; a genesis or enrollment not signed by the owner's key; the token
  copied anywhere; the edge key written outside the protected key directory; the service starting
  active or sending before activation. The owner's account, the host, the store and the installed
  engine are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); the items in
  Out of scope above; forged rows in our own store and files planted in the installed directory.

## Notes

Reuse the existing commands and modules (membership bootstrap, VELDO-0029 enrollment, VELDO-0047
install, VELDO-0067 edge enrollment, VELDO-0064/0065 chat enrollment, VELDO-0073 ingress
configuration); setup orders and checks them, it does not reimplement them. bin/veldo stays a thin
dispatcher.

## History

2026-09-25: written by the lead when the real-factory live qualification found no setup path. Draft;
the owner decides readiness.
