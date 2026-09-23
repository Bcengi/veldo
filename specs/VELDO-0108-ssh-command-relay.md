---
schema: veldo.spec/v1
id: VELDO-0108
title: Remote clients reach the same endpoint through an authenticated SSH command relay, not a second server
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W85
plan_revision: 2
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0025, VELDO-0029, VELDO-0107]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_relay.py"
  - ".veldo/control_relay.py"
  - "scripts/suites/*_veldo_0108_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0108-ssh-command-relay.md"
  - "specs/index.md"
  - "proof/VELDO-0108/*"
behavior_bearing: true
observability:
  logs: >
    Every relayed request names the remote principal SSH authenticated, the workspace coordinate
    the command carried, and the local endpoint it was handed to.
  metrics: >
    Count relay authentication failures and relayed commands whose signature failed at the
    authority, separately, because they are different attacks.
  error_taxonomy: >
    Distinguish an SSH principal that is not enrolled, a relayed command whose signature does not
    verify, a coordinate the relay's host does not serve, and a relay that cannot reach the
    endpoint.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A remote client's command reaches the authority unchanged and is judged there, not at
      the relay. Set: A disposable SSH relay to a real endpoint, with commands valid, tampered in
      transit, and signed by a principal the authority does not know; bare socket cases with an
      exactly 1 MiB request and short response, a short request and exactly 1 MiB response,
      and each direction over 1 MiB. Exactly-at-limit bytes are carried unchanged with exit 0;
      oversized input or output is refused with exit 4 and zero stdout bytes. Completeness: The command the
      authority received is compared byte for byte with the one sent, so the row fails if the relay
      is rewriting rather than relaying. Falsifier: Have the relay accept a command the authority
      would refuse; relay/the-authority-judges-not-the-relay must fail.
    falsified_by: >
      Have the relay accept a command the authority would refuse;
      relay/the-authority-judges-not-the-relay must fail.
  - id: AC2
    text: >
      Claim: SSH authentication is the transport and the command signature is the authority, and
      neither substitutes for the other. Set: An SSH principal that authenticates carrying an
      unsigned command, and a correctly signed command from a principal SSH refuses.
      Completeness: Both refusals are distinguishable by name. Falsifier: Accept a command because
      SSH authenticated its carrier; relay/ssh-is-transport-not-authority must fail.
    falsified_by: >
      Accept a command because SSH authenticated its carrier;
      relay/ssh-is-transport-not-authority must fail.
  - id: AC3
    text: >
      Claim: The relay introduces no listening network service of its own and no second code path:
      a relayed command and a local one reach the same endpoint and are judged by the same code.
      Set: The same command sent locally and through the relay, with the authority's journal
      compared. Completeness: Suite 48 compares pathname Unix sockets under the fixture directory
      in /proc/net/unix before invocation and after relay exit: no additional fixture-local socket
      remains afterward. Source inspection separately checks for bind/listen calls. This is neither
      a process census nor a general listener proof; transient listeners, abstract Unix sockets,
      sockets outside the fixture and other protocols are not observed. The wider no-listener
      requirement and host process census are INTENDED and NOT YET DEMONSTRATED; they need a
      kernel-level lifecycle census fixture. Falsifier: Serve relayed commands
      from a second path; relay/one-endpoint-one-judgement must fail.
    falsified_by: >
      Serve relayed commands from a second path; relay/one-endpoint-one-judgement must fail.
required_evidence: [unit, integration]
rollback: >
  Remove the relay's authorized keys entry. Remote clients lose access and local clients are
  unaffected; no state is lost.
---

## Intent

A client on another machine reaches the same authority endpoint over SSH, and SSH carries it rather than deciding it.

## Context

PLAN-0019 W85, revision 2. Design clause R20, which says remote clients use an authenticated SSH command relay to the IPC endpoint and that no separate network application server is introduced. Split out of VELDO-0029 by Dmitry on 2026-09-21.

The temptation this item exists to refuse is the convenient one: let the relay decide, because it has already authenticated somebody. SSH says who is carrying the command. The command's own signature says who authored it and what it may do. Collapsing the two makes every host with relay access an authority.

## Out of scope

The local endpoint is VELDO-0107 and the unavailable case is VELDO-0109. Host and credential lifecycle is R26 work.

## Notes

The relay is a command channel, so its qualification is about what it refuses to change, not about throughput.

2026-09-22 follow-ups: VELDO-0111 (reusable during-call process and all-family listener census); VELDO-0114 (census-backed relay no-listener consumer); VELDO-0121 (endpoint close/failure interleavings and bounded relay completion); VELDO-0123 (required every-gate mutation drivers with a 600-second stage budget).

## Revision 3 release disposition

2026-09-22, owner Telegram 28852: the built relay is reused in Release 1 stage 2 by
Mac workers reaching the Linux authority. Its existing criteria and evidence remain the
recorded relay contract; they do not certify a macOS worker profile or host-capability routing.
Those two integration concerns receive new draft specifications in this revision. There is
no new relay server to build. The wider during-call listener/process census, transport failure
interleavings and recovery qualification named above belong to Release 2, not to Mac activation
as a package barrier. This allocation changes neither this specification's status nor its
honest limits on existing evidence.
