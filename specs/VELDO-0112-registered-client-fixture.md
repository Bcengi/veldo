---
schema: veldo.spec/v1
id: VELDO-0112
title: Derive mutating-client fixtures from the production client registry
status: draft
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0109]
placement: [contracts, fleet]
protected_paths: []
footprint:
  - ".veldo/control_client_registry.py"
  - "engine/.veldo/control_client_registry.py"
  - ".veldo/claim.py"
  - "engine/.veldo/claim.py"
  - ".veldo/control_client.py"
  - "engine/.veldo/control_client.py"
  - ".veldo/dispatch.py"
  - "engine/.veldo/dispatch.py"
  - "scripts/fixtures/registered_clients.py"
  - "scripts/suites/*_veldo_0112_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0112-registered-client-fixture.md"
  - "specs/index.md"
  - "proof/VELDO-0112/*"
behavior_bearing: true
observability:
  logs: >
    Emit stable client and entry-point identities, transport modes, fixture adapter identity and omitted-registration errors.
  metrics: >
    Compare registered, exercised and missing client/transport pairs.
  traces: >
    Bind every result to the input identity, implementation digest and fixture version.
  error_taxonomy: >
    Distinguish unregistered_entrypoint, missing_fixture_adapter, duplicate_client and vacuous_client_set.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Production mutation entry points and qualification use one client registry, including claim, command and dispatch admission.
      Set: Every production client entry point that can mutate or admit work, including plugins registered through the production registration mechanism.
      Completeness: Enumerate actual registrations after normal module loading and reconcile public mutation entry points with those registrations; require the three existing client kinds and unique stable identities. A client cannot become callable through production dispatch without registration; direct bypasses fail the boundary check.
      Refutation: clients/registry-is-the-boundary is false for any callable mutation entry point absent from the registry.
    falsified_by: >
      Expose the claim mutation entry point without registering it; clients/registry-is-the-boundary must turn red.
  - id: AC2
    text: >
      Claim: Each registered mutating client has a reusable adapter that invokes its real public entry point with valid enrollment, signatures and preconditions.
      Set: The registry's full client-by-supported-transport product, including local IPC and relay where the client supports them.
      Completeness: Join fixture adapters to runtime registrations by identity and require exact set equality and at least one live accepted operation per pair. The fixture fails for a new registration without an adapter; it never substitutes generic send for the registered entry point.
      Refutation: clients/every-registration-is-drivable is false for a missing adapter or a registered path whose positive control cannot act.
    falsified_by: >
      Remove the dispatch-admission adapter from fixture discovery; clients/every-registration-is-drivable must turn red.
  - id: AC3
    text: >
      Claim: Consumers obtain the same freshly enumerated case inventory and cannot silently shrink it using a handwritten list.
      Set: All consumers of the fixture, with a temporary additional valid client registration and with an empty registration result.
      Completeness: A registry-extension control must appear in every returned inventory; the empty result is an error. Inventory receipts record the registration digest and compare executed case identities to the fixture's exported set.
      Refutation: clients/registry-growth-expands-cases is false if the added client is absent or an empty registry passes.
    falsified_by: >
      Filter the temporary extra registration out of the exported fixture cases; clients/registry-growth-expands-cases must turn red.
required_evidence: [unit, integration]
rollback: >
  Revert this capability and its consumer wiring together; retain the evidence gap as open rather than reporting coverage from the earlier weaker rows.
---

## Intent

Make every-client claims enumerable once, so lifecycle and refusal consumers cannot maintain divergent client lists.

## Context

VELDO-0109 AC1 and proof/VELDO-0109/README.md:88-90 leave the registered-client matrix open. Inspection at 2d19756 found a store COMMAND_REGISTRY but no corresponding mutating-client registry; store operations are not client entry points. Creating that shared production boundary is part of this draft.

## Out of scope

Implementing refusal behavior, census collection, authority/store fixtures, or separate registries for each suite.

## Notes

The adapters accept an externally supplied authority/relay fixture; this item owns only client enumeration and invocation. VELDO-0109 is a behavioral prerequisite, not evidence that this inventory already exists. The no-auto-start, unavailable-matrix and write-observation follow-ups will consume this capability.

This is planned work, not implementation evidence. All named rows below this contract are obligations for a future ready implementation. For each declared falsifier, retain the applied diff, require the named row to become false in an otherwise completed run, and revert the mutation. A crash, missing row or timeout is an invalid drive, not a detected falsifier.
