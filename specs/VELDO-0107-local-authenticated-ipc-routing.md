---
schema: veldo.spec/v1
id: VELDO-0107
title: Local clients reach the authority over authenticated IPC carrying explicit workspace coordinates
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W84
plan_revision: 2
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0025, VELDO-0029]
placement: [contracts, fleet]
protected_paths: []
footprint:
  - "engine/.veldo/control_client.py"
  - ".veldo/control_client.py"
  - "scripts/suites/*_veldo_0107_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0107-local-authenticated-ipc-routing.md"
  - "specs/index.md"
  - "proof/VELDO-0107/*"
behavior_bearing: true
observability:
  logs: >
    Every request names the workspace coordinate it carried, the peer it authenticated, and the
    store the authority resolved for it.
  metrics: >
    Count peer authentication failures and coordinate mismatches, separately.
  error_taxonomy: >
    Distinguish an unauthenticated peer, a valid peer whose command signature does not verify, a
    command whose workspace coordinate is not the one the socket serves, and a malformed request.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A local client reaches the authority over a real authenticated socket, and the request
      carries the workspace coordinate explicitly; the authority serves the store that coordinate's
      binding names and no other. Set: Two enrolled clones, two authorities, real sockets, every
      public routing call. Completeness: Both stores are inspected after every call, so a write to
      the wrong one is visible rather than merely unasserted. Falsifier: Resolve the target from
      the serving process's own location instead of the request's coordinate;
      ipc/the-coordinate-comes-from-the-request must fail.
    falsified_by: >
      Resolve the target from the serving process's own location instead of the request's
      coordinate; ipc/the-coordinate-comes-from-the-request must fail.
  - id: AC2
    text: >
      Claim: Peer authentication and command signature are independent, and both are required. Set:
      An authenticated peer with an invalid command signature, an unauthenticated peer with a valid
      command signature, and both valid. Completeness: The two failures are distinguishable in the
      refusal, so the row fails if one check is standing in for the other. Falsifier: Accept a
      valid command signature from an unauthenticated peer;
      ipc/transport-and-command-are-checked-separately must fail.
    falsified_by: >
      Accept a valid command signature from an unauthenticated peer;
      ipc/transport-and-command-are-checked-separately must fail.
  - id: AC3
    text: >
      Claim: The socket's own placement follows the binding, so a client cannot be pointed at
      another domain's socket by an environment variable or a current directory. Set: Two running
      authorities and a client with each ambient source pointed at the other. Completeness: The
      other authority is real and running, so the row fails if the answer is right only because the
      alternative was absent. Falsifier: Take the socket path from the environment;
      ipc/the-socket-follows-the-binding must fail.
    falsified_by: >
      Take the socket path from the environment; ipc/the-socket-follows-the-binding must fail.
required_evidence: [unit, integration]
rollback: >
  Stop the authority process. Clients refuse, which is VELDO-0109's behaviour, and no state is lost.
---

## Intent

A local client reaches its own authority over an authenticated socket, and the repository it means travels in the request.

## Context

PLAN-0019 W84, revision 2. Design clause R20. Split out of VELDO-0029 by Dmitry on 2026-09-21.

VELDO-0029 decides WHICH store a workspace belongs to. This item is how a process in that workspace reaches it: a real authenticated socket, with the workspace coordinate in the request rather than inferred by the process that serves it. The inference is the same defect at the other end of the wire, and it is worth its own set because a serving process has its own current directory and its own module location, neither of which is the caller's.

## Out of scope

The remote transport is VELDO-0108 and the unavailable case is VELDO-0109. No network application server is introduced.

## Notes

SSH is a relay to this endpoint, not a second protocol, so this item's request shape is the one VELDO-0108 carries.
