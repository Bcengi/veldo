---
schema: veldo.spec/v1
id: VELDO-0125
title: Mac worker dispatch through the relay with host-capability routing
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W88
plan_revision: 3
depends_on: [VELDO-0039, VELDO-0047, VELDO-0108, VELDO-0124]
placement: [fleet, project_runner, contracts]
protected_paths: []
footprint:
  - "engine/.veldo/control_worker*.py"
  - ".veldo/control_worker*.py"
  - "packs/*/.veldo/control_worker*.py"
  - "engine/.veldo/control_routing*.py"
  - ".veldo/control_routing*.py"
  - "packs/*/.veldo/control_routing*.py"
  - "scripts/suites/*_veldo_0125_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0125-mac-relay-capability-routing.md"
  - "specs/index.md"
  - "proof/VELDO-0125/*"
behavior_bearing: true
observability:
  logs: >
    Record operation, domain/repository, actor or role, input/configuration versions,
    resulting record identity and named refusal; exclude secrets.
  metrics: >
    Count accepted/refused operations and pending work, with bounded run duration and
    charge attribution where this concern uses a worker.
  traces: >
    Correlate input request, configuration/host, dispatched work and resulting authority evidence.
  error_taxonomy: >
    Distinguish unauthenticated, unauthorized, stale version, unsupported configuration,
    unavailable service, missing evidence and unknown outcome; none is successful completion.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Mac worker claim, launch acceptance and result commands reach the same Linux authority
      through VELDO-0108. Set and completeness: For those three enabled remote command families,
      compare signed commands sent on the real Mac with records committed by the configured Linux
      SQLite authority; carry explicit domain/repository/store/workspace identities and observe no
      Mac authority store or local mutation fallback. Falsifier: Create a Mac-local authority store
      when remote submission fails; the one-authority check must fail.
    falsified_by: >
      Create a Mac-local authority store when remote submission fails; the one-authority check must
      fail.
  - id: AC2
    text: >
      Claim: Dispatch selects only a qualified worker satisfying every required host capability. Set
      and completeness: Register the selected Linux and Mac profiles and submit host-neutral, macOS-
      required and iOS-build units. Compare accepted requirements, selected host and actual worker
      launch; both macOS-required and iOS work go only to the Mac. With the Mac unavailable, those
      units remain visibly blocked. Falsifier: Fall back to Linux for an iOS build when the Mac is
      unavailable; the host-routing refusal check must fail.
    falsified_by: >
      Fall back to Linux for an iOS build when the Mac is unavailable; the host-routing refusal
      check must fail.
  - id: AC3
    text: >
      Claim: Remote result and spend records retain the original unit, host and dispatch identity.
      Set and completeness: Complete real Mac work through the relay and compare output/proof
      references, usage and terminal observations to the Linux authority record and owner-visible
      machine/run state. Submit a result for another dispatch and require refusal; SSH
      authentication alone cannot authorize it. Falsifier: Apply a relayed result to a caller-
      supplied different dispatch; the remote-result binding check must fail.
    falsified_by: >
      Apply a relayed result to a caller-supplied different dispatch; the remote-result binding
      check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern while preserving accepted records, configuration
  revisions and unresolved work. No automatic rollback, retry or recovery is authorized.
---

## Intent

Dispatch work to the qualified host capable of running it, with Mac workers using the existing
SSH relay to the Linux authority.

## Context

W88 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 2.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its 2026-09-22
scope amendments. This new specification is draft; authoring it supplies neither implementation
proof nor operational activation. Implementation still requires readiness and applicable approval.

## Out of scope

Automatic recovery, durability/scale qualification and additional host/channel types beyond
this declared concern. These belong to later releases as assigned by the plan. No existing
specification status, implementation, test, runtime policy or deployed service changes in this draft.

## Notes

Owner Telegram 28852 brings the Mac and built VELDO-0108 relay into the MVP. Reuse that relay
and its production authenticated IPC endpoint. Transport identity is not command authority.
Worker host capabilities are accepted configuration, not a claim made by a model. Cloud/other
hosts are Release 4; transport-failure and reconnect/recovery matrices are Release 2.

Use canonical engine assets and synchronize installed copies. Resolve the proposed footprint's
architecture mapping before ready, including the new UI assets where applicable; this draft does
not amend the architecture contract. Inventory every asset the selected journey installs. Compare
executable registrations to each criterion's declared universe, observe the real named interfaces,
and retain the driven negative-control diff and named failed row. Fixtures cannot certify real
platform, engine or host behavior. Required evidence labels describe future implementation proof,
not tests run by this writing revision.

## History

2026-09-22: new draft for PLAN-0019 revision 3, Release 1 stage 2, under the owner's
complete-factory MVP decisions. Simple function and its meaningful refusal checks are in this
release; recovery and robustness are Release 2, governance depth Release 3, broader hosts/channels,
installation, adoption, migration and rollback Release 4.
