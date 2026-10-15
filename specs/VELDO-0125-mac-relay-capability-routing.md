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
plan_revision: 4
depends_on: [VELDO-0039, VELDO-0047, VELDO-0108, VELDO-0124]
placement: [fleet, project_runner, contracts]
protected_paths: []
footprint:
  - "scripts/suites/86_veldo_0168_text.py"
  - "scripts/suites/68_veldo_0134_acceptance.py"
  - "engine/.veldo/control_channel_enrollment.py"
  - ".veldo/control_channel_enrollment.py"
  - "scripts/suites/33_veldo_0020_authority.py"
  - "scripts/suites/36_veldo_0023_journal.py"
  - "engine/.veldo/authority_contract.py"
  - ".veldo/authority_contract.py"
  - "engine/.veldo/control_launch.py"
  - ".veldo/control_launch.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_store.py"
  - ".veldo/control_store.py"
  - "engine/.veldo/control_membership.py"
  - ".veldo/control_membership.py"
  - "engine/.veldo/control_claim.py"
  - ".veldo/control_claim.py"
  - "engine/.veldo/control_assignment.py"
  - ".veldo/control_assignment.py"
  - "engine/.veldo/control_dispatch.py"
  - ".veldo/control_dispatch.py"
  - "engine/.veldo/control_reservations.py"
  - ".veldo/control_reservations.py"
  - "engine/.veldo/project_runner_macos.py"
  - ".veldo/project_runner_macos.py"
  - "engine/.veldo/project_runner_macos_profile.py"
  - ".veldo/project_runner_macos_profile.py"
  - "scripts/suites/*_veldo_0124_*.py"
  - "proof/VELDO-0124/*.py"
  - "proof/VELDO-0124/manifest.json"
  - "engine/.veldo/control_worker*.py"
  - ".veldo/control_worker*.py"
  - "packs/*/.veldo/control_worker*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
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

2026-10-10: candidate build on agent/codex/veldo-0125. Four canonical routing and
worker assets, with identical installed copies and seven-pack composition checks,
implement the three signed worker command families on the existing Linux
service/relay path, all-required-capability selection with durable blocked state,
and bound result/spend records. The Mac bridge consumes the 0124 supervisor.
Suites 105_veldo_0125_relay and 106_veldo_0125_routing supply named Linux logic
rows; proof/VELDO-0125/README.md records their scope and three single-change
falsifiers. The sandbox refuses Unix socket creation, so real IPC is explicitly
not run here; its runnable check is retained. Real Mac and SSH rows are declared
through the synthetic-engine native roundtrip driver and remain pending. No
provider login, live capture, deployed service, qualification or activation was
changed. Existing fleet, project_runner and contracts placements describe these
assets; no architecture contract amendment is made. Criteria, risk, approval and
status are unchanged. The reviewer owns the canonical gate and merged-tree stamp.

2026-10-10: the owner's assistant decided to amend the footprint to include
engine/.veldo/control_launch.py and .veldo/control_launch.py because AC2 cannot
hold in production otherwise. Production Runner preparation now selects the
qualified host before submission. The same review authorizes the listed service,
store, membership, dispatch, reservation and containment fixes and their 0124
regressions. Criteria and approval requirements are unchanged.

2026-10-15: B2 independent-review corrections bind remote acceptance to the current
eligibility decision inside its authority transaction, and wire factory submission
to a configured Mac receiver with a tracked asynchronous launch. Regression rows
cover withdrawn/replaced admission, factory delivery, missing-receiver retirement
and transport output that attempts to impersonate completion. Targeted falsifiers
remove the eligibility recheck, restore the unowned/no-contact submission, and drop
pending factory tracking. Configuration and evidence limits are recorded in
proof/VELDO-0125/README.md; acceptance criteria and approval requirements are unchanged.
