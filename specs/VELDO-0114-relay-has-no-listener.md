---
schema: veldo.spec/v1
id: VELDO-0114
title: Prove the relay opens no service during its whole invocation
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0108, VELDO-0111]
placement: [contracts, fleet]
protected_paths: []
footprint:
  - ".veldo/control_relay.py"
  - "engine/.veldo/control_relay.py"
  - "scripts/suites/48_veldo_0108_relay.py"
  - "scripts/suites/*_veldo_0114_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0114-relay-has-no-listener.md"
  - "specs/index.md"
  - "proof/VELDO-0114/*"
behavior_bearing: true
observability:
  logs: >
    Attach process/listener traces and declared pre-existing endpoint identities to each relay invocation.
  metrics: >
    Count measured relay invocations, unexpected process births and service bindings by family.
  traces: >
    Bind every result to the input identity, implementation digest and fixture version.
  error_taxonomy: >
    Distinguish relay_listener, relay_child_process and census_incomplete from the relay's transport refusals.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A relay invocation creates no listening socket or service receive binding, even temporarily.
      Set: Local command-channel invocations with successful, refused, empty, limit-sized and transport-error exchanges, under the full family/type capability inventory of VELDO-0111.
      Completeness: Cross each exchange outcome with the census capability receipt, require a complete interval and zero new service events attributable to the relay scope. Qualify with transient pathname/abstract Unix, out-of-directory, IPv4 and IPv6 listener probes so addresses cannot narrow the claim. An unavailable VELDO-0111 mechanism or INCOMPLETE receipt emits relay/no-listener-during-call as STANDS DOWN with census_incomplete, never green.
      Refutation: relay/no-listener-during-call is false if any new service event occurs before relay exit.
    falsified_by: >
      Open and immediately close an IPv4 listener on an ephemeral port before forwarding; relay/no-listener-during-call must turn red.
  - id: AC2
    text: >
      Claim: The one-request relay does not create a second serving process.
      Set: The same invocation set, measured from before relay startup through exit and descendant drain, with the intended relay root launch recorded separately.
      Completeness: Use VELDO-0111 birth/ancestry events; require zero descendants created by the relay. The fixture authority and any SSH daemon are pre-existing processes outside the measured relay scope, not name-based exemptions. An unavailable mechanism or INCOMPLETE receipt emits relay/no-second-process as STANDS DOWN with census_incomplete, never green.
      Refutation: relay/no-second-process is false for any relay-created child, including one that exits or reparents before return.
    falsified_by: >
      Fork a short-lived endpoint helper from the relay before connecting; relay/no-second-process must turn red.
  - id: AC3
    text: >
      Claim: The no-listener part of relay/one-endpoint-one-judgement is satisfied only by complete census evidence.
      Set: All relay exchange outcomes plus unavailable, lost-event and terminated-collector runs.
      Completeness: The row must retain its endpoint/judgment comparison and consume one complete census receipt per invocation. Missing or INCOMPLETE receipts leave the obligation unproven and prevent qualification, even when the old pathname snapshots match. Drive unavailable-mechanism faults and require relay/one-endpoint-one-judgement, relay/no-listener-during-call, relay/no-second-process and relay/listener-proof-needs-census each to be emitted as STANDS DOWN with census_incomplete, with zero green consumer rows and qualification incomplete.
      Refutation: relay/listener-proof-needs-census is false if snapshot equality substitutes for a failed observer.
    falsified_by: >
      Fall back to pathname snapshot equality when census collection fails; relay/listener-proof-needs-census must turn red.
required_evidence: [unit, integration]
rollback: >
  Revert this capability and its consumer wiring together; retain the evidence gap as open rather than reporting coverage from the earlier weaker rows.
---

## Intent

Close the general no-service and process-census gap in VELDO-0108 without duplicating the observation fixture.

## Context

VELDO-0108 AC3 and proof/VELDO-0108/README.md:35-40 describe only fixture-local Unix socket snapshots. This draft consumes VELDO-0111 for the stronger live observation.

## Out of scope

A new transport protocol, SSH-server authentication qualification, transport fault scheduling and another lifecycle collector.

## Notes

The observable interval starts before the relay executable runs. The authority's already-open listener belongs to setup, while every socket the relay opens belongs to the measurement regardless of path or family. Connecting sockets are permitted; listening or accepting a service binding is not.

Use VELDO-0111's unprivileged Linux ptrace fixture and capability receipt. On a host where that mechanism is unavailable, the census is INCOMPLETE and every consumer listed in AC3 stands down BY NAME, never green or omitted, including the original relay/one-endpoint-one-judgement composite row. Its endpoint/judgment comparison may still run, but cannot make the composite obligation pass. Fault-injection checks can validate stand-down propagation without certifying listener absence on that host.

This is planned work, not implementation evidence. All named rows below this contract are obligations for a future ready implementation. For each declared falsifier, retain the applied diff, require the named row to become false in an otherwise completed run, and revert the mutation. A crash, missing row or timeout is an invalid drive, not a detected falsifier.
