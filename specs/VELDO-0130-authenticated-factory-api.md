---
schema: veldo.spec/v1
id: VELDO-0130
title: Authenticated factory state, message and decision API
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W93
plan_revision: 3
depends_on: [VELDO-0025, VELDO-0035, VELDO-0047, VELDO-0064, VELDO-0065, VELDO-0068, VELDO-0069, VELDO-0126]
placement: [contracts, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_api*.py"
  - ".veldo/control_api*.py"
  - "packs/*/.veldo/control_api*.py"
  - "scripts/suites/*_veldo_0130_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0130-authenticated-factory-api.md"
  - "specs/index.md"
  - "proof/VELDO-0130/*"
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
      Claim: Every API operation authenticates the caller and checks current domain/repository and
      operation permissions. Set and completeness: Derive routes from the published API contract,
      including event reads and configuration/workflow operations used by the UI. Exercise
      missing/invalid/expired credentials, wrong-domain access, insufficient role and valid current
      enrollment for every route family; browser mutation sessions also reject cross-origin/forged
      requests under the chosen auth mechanism. Falsifier: Authorize a decision using the body
      actor_id; the impersonation refusal check must fail.
    falsified_by: >
      Authorize a decision using the body actor_id; the impersonation refusal check must fail.
  - id: AC2
    text: >
      Claim: Read and event APIs expose authoritative state with identities, versions and freshness.
      Set and completeness: Compare responses and live event delivery to the actual store for
      projects/objectives, nested backlog/specs/units, machines/workers, run steps/tool calls,
      decisions, gate/review/proof, spend and configuration/workflows. Enumerate supported read
      models and redact credentials; unavailable authority yields an explicit error or labeled stale
      read, never invented live state. Falsifier: Return an unstated stale snapshot as current; the
      freshness check must fail.
    falsified_by: >
      Return an unstated stale snapshot as current; the freshness check must fail.
  - id: AC3
    text: >
      Claim: Message and decision writes reuse common intake and exact settlement. Set and
      completeness: Send plain-text messages through the API and UI message box into 0126; answer a
      decision using current request/presentation versions and actual session principal. Test a
      stale answer, unauthorized owner and conflicting Telegram/UI answers to one request. Inspect
      one terminal ruling with unchanged provenance and no intake self-admission. Falsifier: Create
      a second settlement for the UI answer after Telegram settles; the one-request-one-ruling check
      must fail.
    falsified_by: >
      Create a second settlement for the UI answer after Telegram settles; the one-request-one-
      ruling check must fail.
  - id: AC4
    text: >
      Claim: UI configuration edits and operational actions use typed current-version authority
      commands. Set and completeness: Enumerate the UI action contract for owner admission/priority,
      project pause/cancel, worker stop, team/agent configuration and workflow edits; compare route-
      to-command registrations. Submit valid and stale/unauthorized changes and inspect accepted
      revisions or named refusals with no browser-side authority or direct store writes. Falsifier:
      Bypass authority checking on a workflow save endpoint; the unauthorized-write check must fail.
    falsified_by: >
      Bypass authority checking on a workflow save endpoint; the unauthorized-write check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern while preserving accepted records, configuration
  revisions and unresolved work. No automatic rollback, retry or recovery is authorized.
---

## Intent

Give the Veldo UI and other authenticated callers one API for current state, new messages and
exact decision answers, backed by the Linux authority.

## Context

W93 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its 2026-09-22
scope amendments. This new specification is draft; authoring it supplies neither implementation
proof nor operational activation. Implementation still requires readiness and applicable approval.

## Out of scope

Automatic recovery, durability/scale qualification and additional host/channel types beyond
this declared concern. These belong to later releases as assigned by the plan. No existing
specification status, implementation, test, runtime policy or deployed service changes in this draft.

## Notes

Owner Telegram 28857 requires authenticated API intake and the UI. The API is an ingress/read
service over existing domain commands, never a second store or scheduler. Document the chosen
authenticated session/token mechanism, enrollment mapping and secure transport deployment
before ready. The API may not trust actor IDs in request bodies. No additional authentication
provider or framework is selected by this draft.

Use canonical engine assets and synchronize installed copies. Resolve the proposed footprint's
architecture mapping before ready, including the new UI assets where applicable; this draft does
not amend the architecture contract. Inventory every asset the selected journey installs. Compare
executable registrations to each criterion's declared universe, observe the real named interfaces,
and retain the driven negative-control diff and named failed row. Fixtures cannot certify real
platform, engine or host behavior. Required evidence labels describe future implementation proof,
not tests run by this writing revision.

## History

2026-09-22: new draft for PLAN-0019 revision 3, Release 1 stage 5, under the owner's
complete-factory MVP decisions. Simple function and its meaningful refusal checks are in this
release; recovery and robustness are Release 2, governance depth Release 3, broader hosts/channels,
installation, adoption, migration and rollback Release 4.
