---
schema: veldo.spec/v1
id: VELDO-0116
title: Refuse every registered mutating client after authority or relay death
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0109, VELDO-0112, VELDO-0113, VELDO-0115]
placement: [contracts, fleet]
protected_paths: []
footprint:
  - ".veldo/control_client.py"
  - "engine/.veldo/control_client.py"
  - ".veldo/claim.py"
  - "engine/.veldo/claim.py"
  - ".veldo/dispatch.py"
  - "engine/.veldo/dispatch.py"
  - "scripts/suites/49_veldo_0109_unavailable.py"
  - "scripts/suites/*_veldo_0116_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0116-unavailable-registered-client-matrix.md"
  - "specs/index.md"
  - "proof/VELDO-0116/*"
behavior_bearing: true
observability:
  logs: >
    Name registry client, transport, kill barrier, actual killed PID/exit status, service identity and last observed watermark.
  metrics: >
    Report the registry-derived expected and completed matrix, refusals and unexpected admissions.
  traces: >
    Bind every result to the input identity, implementation digest and fixture version.
  error_taxonomy: >
    Distinguish authority_unavailable after authority death from relay loss with a live authority; preserve uncertainty for a request whose delivery cannot be established.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The unavailable matrix covers every registered mutating client and every transport it declares.
      Set: VELDO-0112's runtime inventory crossed with authority-SIGKILL for all transports and relay-SIGKILL/live-authority for relay-capable clients; claim, command and dispatch admission must be present.
      Completeness: Derive case ids directly from registry capabilities, require exact expected/completed set equality, and add a temporary registered client to prove automatic matrix expansion. A missing required client kind, adapter or empty inventory is failure.
      Refutation: unavailable/registered-matrix-is-complete is false on an omitted registration or transport cell.
    falsified_by: >
      Filter dispatch admission out of the generated unavailable matrix; unavailable/registered-matrix-is-complete must turn red.
  - id: AC2
    text: >
      Claim: After a live accepted operation establishes a watermark, killing the authority makes every subsequent mutation/admission refuse with authority_unavailable, its service identity and that last watermark.
      Set: Every authority-death matrix cell; wait for verified SIGKILL exit before invoking the client, retain the dead socket inode, and use a fresh command identity.
      Completeness: Use VELDO-0115 for the live positive control and independent store inspection; confirm -SIGKILL termination and unchanged post-kill baselines after refusal. Assert no accepted receipt, claim acquisition, worker launch or dispatch admission. Consume the no-auto-start evidence from VELDO-0113 for the same client cases.
      Refutation: unavailable/sigkill-refuses-every-client is false if a registered call succeeds, admits work or loses the refusal's service/watermark.
    falsified_by: >
      Return an accepted cached response from the command client's dead-socket path; unavailable/sigkill-refuses-every-client must turn red.
  - id: AC3
    text: >
      Claim: Losing the relay while the authority lives refuses through the real client and cannot be mistaken for either acceptance or proof that the authority died.
      Set: Every relay-death matrix cell, with relay SIGKILL before forwarding begins and separately after forwarding/commit but before a response can reach the client.
      Completeness: Use barriers with recorded delivery/commit state, verify the relay's -SIGKILL exit and verify authority liveness through an independent signed local request. Before-forward cells leave the store unchanged; after-commit cells may contain exactly the already committed command, but return authority_unavailable with delivery uncertainty and the last client-observed watermark, never a fabricated acceptance or automatic retry.
      Refutation: unavailable/killed-relay-live-authority is false if a client accepts a truncated/missing answer, admits dependent work or reissues the command.
    falsified_by: >
      Translate the killed relay's EOF into an accepted empty response; unavailable/killed-relay-live-authority must turn red.
required_evidence: [unit, integration]
rollback: >
  Revert this capability and its consumer wiring together; retain the evidence gap as open rather than reporting coverage from the earlier weaker rows.
---

## Intent

Close the fleet-wide unavailable evidence gap using the registry and real authority/store fixtures.

## Context

VELDO-0109 AC1 and proof/VELDO-0109/README.md:81-90 cover only generic send, including one SIGKILL case. The registered client and killed-relay/live-authority matrix remains open.

## Out of scope

Reimplementing fixture inventories, recovery/reconciliation after uncertain delivery, and proving transient filesystem-write absence.

## Notes

The uppercase requirement name AUTHORITY_UNAVAILABLE corresponds to the existing wire reason authority_unavailable. Live controls must genuinely succeed before faults are applied; invalid signatures or unenrolled clients cannot provide refusal evidence. Claim/admission adapters expose their actual admission outputs, not only a transport response. Mid-flight transport loss cannot establish that an authority did not commit.

This is planned work, not implementation evidence. All named rows below this contract are obligations for a future ready implementation. For each declared falsifier, retain the applied diff, require the named row to become false in an otherwise completed run, and revert the mutation. A crash, missing row or timeout is an invalid drive, not a detected falsifier.

