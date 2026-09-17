---
schema: veldo.spec/v1
id: VELDO-0062
title: Provider credential separation and live usage accounting
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W47
plan_revision: 1
depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059]
placement: [fleet, engine, metrics, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/accounts.py"
  - ".veldo/accounts.py"
  - "packs/*/.veldo/accounts.py"
  - "engine/.veldo/credential_issue.py"
  - ".veldo/credential_issue.py"
  - "packs/*/.veldo/credential_issue.py"
  - "engine/.veldo/fleet.py"
  - ".veldo/fleet.py"
  - "packs/*/.veldo/fleet.py"
  - "engine/.veldo/budget_state.py"
  - ".veldo/budget_state.py"
  - "packs/*/.veldo/budget_state.py"
  - "engine/.veldo/control_engine_claude*.py"
  - ".veldo/control_engine_claude*.py"
  - "packs/*/.veldo/control_engine_claude*.py"
  - "engine/.veldo/control_engine_codex*.py"
  - ".veldo/control_engine_codex*.py"
  - "packs/*/.veldo/control_engine_codex*.py"
  - "engine/.veldo/control_reservation*.py"
  - ".veldo/control_reservation*.py"
  - "packs/*/.veldo/control_reservation*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0062_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0062-provider-credentials-and-usage.md"
  - "specs/index.md"
  - "proof/VELDO-0062/*"
behavior_bearing: true
observability:
  logs: >
    Credential and accounting receipts name provider account, invocation, contract, request
    sequence, pricing revision, maximum allocated charge, and observed charge without secrets.
  metrics: >
    Expose reserved, settled, outstanding, and unknown amounts at account/project/unit ceilings,
    plus rejected credential exchanges and duplicate usage sequences.
  traces: >
    Join accepted contract to internal handle issuance and use, protected provider call, actual
    usage evidence, and exactly one durable charge settlement.
  error_taxonomy: >
    Distinguish reusable-profile exposure, forged task scope, expired handle, unbounded maximum,
    exhausted remainder, usage conflict, and unresolved possible charge.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Provider authentication is held by protected services and is inaccessible to real
      model tools/builds; internal capabilities derive only from accepted contracts. Set:
      accounts.account_add/resolve/get, fleet.InSessionSpawner._assemble_env,
      credential_issue.issue/authorize_use/Credential.reveal, and both production adapters on
      every supported authentication and host profile. Completeness: Enumerate credential sources
      from launch environment, mounts, descriptors, sockets, and provider configuration. Run
      actual tool/build children attempting each access, another account, forged task_declares,
      changed contract/unit/station/sandbox, expired handles, and revocation at use. Require
      unique short-lived invocation identity expiring no later than deadline plus fifteen minutes
      and zero reusable profile mounts. Unsafe profiles stay disabled. Falsifier: Mount the
      resolved account profile into a worker tool sandbox; provider/custody must detect a reusable
      credential read from that child.
    falsified_by: >
      Mount the resolved account profile into a worker tool sandbox; provider/custody must detect
      a reusable credential read from that child.
  - id: AC2
    text: >
      Claim: Every live billable request allocates an enforceable maximum possible charge
      atomically from all applicable remaining reservations before reaching the provider. Set:
      Initial, retry, and follow-on calls for Claude Code and Codex, through B control_reservation
      and production credential_issue.authorize_use boundaries, at account/project/unit ceilings.
      Completeness: Inventory all billable paths and applicable pricing components, including
      input/output and any enabled extras; bind pricing revision, hard request limits, exact
      monetary units and rounding to the maximum. Race real callers below, at, and above each
      remainder after charges and exposure, observing actual outbound calls and billed results.
      Unknown or unenforceable maxima refuse before any call; a provider mode without enforcement
      cannot qualify. Falsifier: Allocate a follow-on maximum after sending and race two calls for
      the same remainder; provider/pre-call-race must detect the extra outbound billable call.
    falsified_by: >
      Allocate a follow-on maximum after sending and race two calls for the same remainder;
      provider/pre-call-race must detect the extra outbound billable call.
  - id: AC3
    text: >
      Claim: Observed usage settles once per invocation and sequence while incomplete reports
      retain conservative exposure through cancellation and restart. Set: Both adapters feeding B
      reservation accounting and budget_state.budget_report/report_lines, with actual provider
      receipts and normal, delayed, duplicate, reordered, malformed, and conflicting usage.
      Completeness: Capture live costs and reconcile token/charge semantics against provider
      evidence for each qualified mode. Kill the adapter after provider acceptance before usage
      persistence, replay reports through separate processes, and compare durable balances with an
      independent exact-unit oracle. Only reconciled usage or authoritative no-charge evidence
      releases exposure; estimates and unknowns remain labeled and unbounded uncertainty blocks
      affected admission. Falsifier: Release outstanding exposure when an accepted request times
      out; provider/timeout-exposure must catch a new call spending the unresolved allocation.
    falsified_by: >
      Release outstanding exposure when an accepted request times out; provider/timeout-exposure
      must catch a new call spending the unresolved allocation.
  - id: AC4
    text: >
      Claim: Account selection and cost reports cannot misattribute consumption or turn missing
      instrumentation into free capacity. Set: accounts.resolve/get/list_accounts and
      budget_state.read_events/spend_events/budget_report/report_lines over accepted account
      bindings and real concurrent invocations in two provider accounts and two projects.
      Completeness: Drive every supported provider accounting mode with explicit repository
      coordinates. Supply an unrelated ambient account environment, corrupt usage attribution, and
      remove measurement data while retaining committed allocations. Compare each
      account/project/unit total and displayed watermark to signed stored receipts; missing
      instrumentation must show unknown exposure, never another account balance or available
      budget. Falsifier: Attribute one invocation usage to a caller-supplied account label instead
      of its accepted contract; provider/account-substitution must detect the wrong ledger and
      report totals.
    falsified_by: >
      Attribute one invocation usage to a caller-supplied account label instead of its accepted
      contract; provider/account-substitution must detect the wrong ledger and report totals.
required_evidence: [unit, integration]
rollback: >
  Disable affected provider modes, revoke handles, preserve private custody and all usage/exposure
  records, and reconcile charges before releasing any reservation.
---

## Intent

Qualify live provider credential custody and charge accounting before either engine can consume a production budget.

## Context

Package D, W47 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A/B/C contracts govern implementation. This draft grants no implementation or activation authority.

R36, R39, R45, and R59 extend the inspected account-profile and FakeIssuer seams. Leakage of a reusable login or allocation after a billable call can exceed both authority and signed spending limits. The declared risk floor is critical; required approval must bind the eventual change and proof. This declaration records no approval.

## Out of scope

Customer billing, new admission policy, secret inventory exemptions, and governor pacing strategy are excluded.

## Notes

D1/D2 block the store and acknowledged effects; D3/D4 block real credential-isolated host and clone qualification until Dmitry rules. B W13 owns the actual issuer and W21 the reservation predicate; this item proves both against live provider behavior and repairs provider integration, rather than accepting FakeIssuer.mint as issuance evidence. Qualification must name supported billing/authentication modes and all pricing components before ready, with actual costs under a declared finite budget. No provider price or safe proxy is assumed. Preserve raw protected receipts outside public proof and publish redacted digests/provenance sufficient for independent checks. Register any adapter assets in W30 inventory, map budget_state and credential_issue into effective architecture, and retain each mutation diff with its named failing row.
