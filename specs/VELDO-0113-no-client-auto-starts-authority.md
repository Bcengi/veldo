---
schema: veldo.spec/v1
id: VELDO-0113
title: Measure no auto-start across every registered client
status: draft
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0109, VELDO-0111, VELDO-0112]
placement: [contracts, fleet]
protected_paths: []
footprint:
  - ".veldo/control_client.py"
  - "engine/.veldo/control_client.py"
  - ".veldo/claim.py"
  - "engine/.veldo/claim.py"
  - ".veldo/dispatch.py"
  - "engine/.veldo/dispatch.py"
  - "scripts/suites/*_veldo_0113_*.py"
  - "scripts/suites/49_veldo_0109_unavailable.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0113-no-client-auto-starts-authority.md"
  - "specs/index.md"
  - "proof/VELDO-0113/*"
behavior_bearing: true
observability:
  logs: >
    Name the client, endpoint state and any forbidden birth/listener with its lifecycle trace.
  metrics: >
    Report expected/completed registry cases, forbidden launches and observation failures.
  traces: >
    Bind every result to the input identity, implementation digest and fixture version.
  error_taxonomy: >
    Distinguish authority_unavailable from forbidden_autostart and census_incomplete.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every registered mutating client refuses rather than spawning an authority when its endpoint is missing or present but dead.
      Set: The VELDO-0112 client/transport inventory crossed with absent endpoint and a dead socket inode left by SIGKILL; observe each entire invocation with VELDO-0111.
      Completeness: Require exact equality between generated and completed case identities and a complete census for each. An unavailable VELDO-0111 mechanism or INCOMPLETE receipt emits unavailable/no-client-starts-the-authority as STANDS DOWN with census_incomplete, never green. Launch envelopes declare only the client's root and necessary transport launches by birth identity and causal parent before the call; authority launches have no exemption.
      Refutation: unavailable/no-client-starts-the-authority is false on any extra process birth, even if it exits before the call returns or uses another name.
    falsified_by: >
      Spawn and immediately reap a fallback authority on connection failure; unavailable/no-client-starts-the-authority must turn red.
  - id: AC2
    text: >
      Claim: A refusing client cannot host a fallback authority inside its own process or any descendant.
      Set: The same registry/state product, with listener observations across all families qualified by VELDO-0111, unrestricted addresses and transient lifetimes.
      Completeness: Require zero new listening or service-receive bindings attributable to the client scope after excluding only the pre-existing fixture endpoints. The census receipt must certify full interval coverage; an unavailable mechanism or INCOMPLETE receipt emits unavailable/no-client-hosts-a-listener as STANDS DOWN with census_incomplete, never green.
      Refutation: unavailable/no-client-hosts-a-listener is false on a new service event even when no child is created.
    falsified_by: >
      Bind and close a transient abstract Unix listener inside the connection-refusal handler; unavailable/no-client-hosts-a-listener must turn red.
  - id: AC3
    text: >
      Claim: The former socket snapshot row cannot satisfy the census-backed no-auto-start obligation.
      Set: Every registry case with a healthy observer and with a deliberately unavailable or interrupted observer.
      Completeness: The row result carries its client inventory digest and complete observation receipt; qualification requires one receipt per case and prohibits the old address-only check from supplying it. Drive unavailable-mechanism faults and require all three consumer row names to remain present as STANDS DOWN with census_incomplete, including unavailable/no-auto-start-needs-census, with zero green consumer rows and qualification incomplete.
      Refutation: unavailable/no-auto-start-needs-census is false when any incomplete census is accepted as evidence.
    falsified_by: >
      Treat an unavailable census as a successful no-auto-start result; unavailable/no-auto-start-needs-census must turn red.
required_evidence: [unit, integration]
rollback: >
  Revert this capability and its consumer wiring together; retain the evidence gap as open rather than reporting coverage from the earlier weaker rows.
---

## Intent

Move VELDO-0109's no-auto-start evidence onto the shared live census for all clients.

## Context

The gap is explicit in VELDO-0109 AC3 and proof/VELDO-0109/README.md:40-42,71-77. The existing address check cannot see a short-lived fallback process or another address.

## Out of scope

Building another observer or client registry; filesystem writes and detailed kill/refusal semantics have separate consumers.

## Notes

Use the VELDO-0112 adapters unchanged. Git identity lookups or transport helpers genuinely needed by a client must be declared in the launch envelope and matched to fixture-controlled identities, never waived by executable name. Ordinary schema/refusal checks remain necessary; the three rows here establish only the process/listener side of no-auto-start.

Use VELDO-0111's unprivileged Linux ptrace fixture and capability receipt. On a host where that mechanism is unavailable, the census is INCOMPLETE: unavailable/no-client-starts-the-authority, unavailable/no-client-hosts-a-listener and unavailable/no-auto-start-needs-census each stand down BY NAME, never green or omitted. A successful refusal or equal socket snapshots cannot discharge these obligations. Fault-injection checks may prove that propagation is correct; they do not prove process/listener absence on the unavailable host.

This is planned work, not implementation evidence. All named rows below this contract are obligations for a future ready implementation. For each declared falsifier, retain the applied diff, require the named row to become false in an otherwise completed run, and revert the mutation. A crash, missing row or timeout is an invalid drive, not a detected falsifier.
