---
schema: veldo.spec/v1
id: VELDO-0115
title: Observe real store mutation through the bound authority
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0023, VELDO-0029, VELDO-0107]
placement: [contracts, fleet]
protected_paths: []
footprint:
  - ".veldo/control_client.py"
  - "engine/.veldo/control_client.py"
  - ".veldo/control_store.py"
  - "engine/.veldo/control_store.py"
  - "scripts/fixtures/authority_store.py"
  - "scripts/suites/47_veldo_0107_ipc.py"
  - "scripts/suites/*_veldo_0115_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0115-real-authority-store-fixture.md"
  - "specs/index.md"
  - "proof/VELDO-0115/*"
behavior_bearing: true
observability:
  logs: >
    Record enrolled coordinates, authority identity, database identity, command id and independently read committed journal positions.
  metrics: >
    Count committed commands in the target and unexpected changes in the other store.
  traces: >
    Bind every result to the input identity, implementation digest and fixture version.
  error_taxonomy: >
    Distinguish routing_mismatch, store_not_changed, unexpected_store_change and non_durable_acceptance.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A signed mutating request through real authenticated IPC changes the configured SQLite store itself and returns the store's committed watermark.
      Set: Two independently enrolled clones in different domains, two real authority processes and stores, and each public routing call that accepts mutation; run each direction with a fresh command id and nonce.
      Completeness: A shared fixture invokes production Authority judgment and control_store execution, never a logging-only apply callback. Enumerate public routing entry points and compare completed cases; after acceptance, open the target database through a separate connection and assert the exact entity transition and matching journal command id.
      Refutation: ipc/configured-store-really-changes is false if an accepted command exists only in a callback log or response.
    falsified_by: >
      Replace the authority's store execution with a callback that logs and returns acceptance without committing; ipc/configured-store-really-changes must turn red.
  - id: AC2
    text: >
      Claim: Only the request coordinate's bound store changes when ambient location and environment point elsewhere.
      Set: The same two-direction routing set crossed with serving-process cwd, importing location and VELDO_CONTROL_DB pointed at the other real enrolled domain.
      Completeness: Capture full logical table and journal snapshots of both stores, assert exactly the expected target delta and no delta in the other, and require both stores to be writable positive controls. Names and callback logs are not store observations.
      Refutation: ipc/only-the-bound-store-changes is false if the other store changes or the bound store lacks the expected transaction.
    falsified_by: >
      Pass the serving process's other store connection to control_store.execute; ipc/only-the-bound-store-changes must turn red.
  - id: AC3
    text: >
      Claim: Accepted target state survives closing and reopening the store, and the reusable fixture exposes committed baselines for further qualification.
      Set: Every accepted command from AC1 and AC2, reopening after authority shutdown; untouched peer store reopened too.
      Completeness: Independently reopen each database and compare entity values, journal identity and watermark with the expected transaction. Fixture consumers receive real handles, lifecycle controls and snapshot readers from this single implementation.
      Refutation: ipc/accepted-state-survives-reopen is false if acceptance precedes a transaction that never commits.
    falsified_by: >
      Replace the final SQLite commit in the accepted command path with rollback while returning the computed response; ipc/accepted-state-survives-reopen must turn red.
required_evidence: [unit, integration]
rollback: >
  Revert this capability and its consumer wiring together; retain the evidence gap as open rather than reporting coverage from the earlier weaker rows.
---

## Intent

Replace callback-only routing evidence with direct, durable observations of the configured stores, and supply one real-authority/store fixture to other integration drafts.

## Context

VELDO-0107 AC1 and proof/VELDO-0107/README.md:61-64 explicitly leave real-store mutation and the unchanged other store unproven. VELDO-0023 defines the store transaction machinery consumed here.

## Out of scope

Domain registration conflict policy, unavailable-client semantics, store crash recovery and process/listener tracing.

## Notes

The fixture owns authority startup, real enrollment, signed-command construction, journal/table inspection and explicit stop/kill controls. Later uniqueness and unavailable-client consumers depend on this fixture rather than making their own callback authorities. It may wire the existing apply seam to production store execution; it may not replace production validation or execution with an oracle callback.

This is planned work, not implementation evidence. All named rows below this contract are obligations for a future ready implementation. For each declared falsifier, retain the applied diff, require the named row to become false in an otherwise completed run, and revert the mutation. A crash, missing row or timeout is an invalid drive, not a detected falsifier.

