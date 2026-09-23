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
plan_revision: 3
depends_on: [VELDO-0028, VELDO-0036]
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
    Record the operation, domain, repository, unit or request identity, accepted input versions,
    outcome and named refusal without secrets.
  metrics: >
    Count accepted and refused operations and expose current pending work for this specification.
  traces: >
    Join accepted inputs, actual service observations and resulting authority records by identity.
  error_taxonomy: >
    Distinguish invalid input, missing authority, stale subject, unavailable service,
    missing evidence and unknown outcome where applicable; never label unknown as success.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Provider model authentication stays in its protected adapter service and internal
      handles derive from accepted contracts. Set and completeness: For Claude Code and Codex,
      enumerate provider model credentials reachable through environment, mounts, descriptors,
      sockets and provider configuration by real tool/build children on Linux and Mac. Attempt
      reads of those model credentials and substitute contract/unit/station/sandbox/expiry;
      require refusal and no reusable provider model profile mounts in tool/build children.
      The authenticated model CLI may use its own protected subscription profile. MCP server
      credentials and profiles are passed exactly as configured under VELDO-0127; they are not
      provider model credentials and are not refused by this check. Falsifier: Mount a reusable
      provider model account profile into a worker tool environment; the credential-read check
      must fail.
    falsified_by: >
      Mount a reusable provider model account profile into a worker tool environment; the
      credential-read check must fail.
  - id: AC2
    text: >
      Claim: Each billable request allocates its enforceable maximum from all applicable remaining
      budgets before sending. Set and completeness: Inventory initial, retry and follow-on paths for
      both providers, enabled price components and hard request limits; bind pricing revision, exact
      units and rounding. Exercise fitting, excessive and unknown maxima and two requests for one
      remainder, recording outbound calls and live charges. Falsifier: Allocate a follow-on maximum
      after sending; the pre-call ordering check must fail.
    falsified_by: >
      Allocate a follow-on maximum after sending; the pre-call ordering check must fail.
  - id: AC3
    text: >
      Claim: Usage settles once per invocation/sequence and incomplete reports retain conservative
      exposure. Set and completeness: Capture live receipts from each configured provider, ingest
      normal/duplicate/missing reports, and compare balances with an independent exact-unit
      calculation; cancellation or timeout alone cannot release an accepted request allocation.
      Falsifier: Release exposure on accepted-request timeout; the next-spend refusal check must
      fail.
    falsified_by: >
      Release exposure on accepted-request timeout; the next-spend refusal check must fail.
  - id: AC4
    text: >
      Claim: Costs and remaining budget are attributed to the stored account/project/unit. Set and
      completeness: For the one account per provider and journey project, alter ambient account
      labels and report attribution, and remove measurement while retaining allocation; compare
      displayed watermark and totals to actual stored receipts. Falsifier: Use a caller-supplied
      account label for usage; the ledger-attribution comparison must fail.
    falsified_by: >
      Use a caller-supplied account label for usage; the ledger-attribution comparison must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Provider credential separation and live usage accounting. Deliver the normal function needed by the running factory journey.

## Context

W47 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Qualify one account and authentication mode for each of Claude Code and Codex on the two MVP
host profiles. Record pricing and hard-limit evidence; no price or safe proxy is assumed.
Protect raw receipts and publish redacted digests sufficient for independent checking. Unknown
cost is never zero.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 1: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC3
restart/reordered reports moved to Release 2; AC1 all-authentication/host and AC4 two-
account/two-project matrices moved to Release 4, except the two MVP hosts. One account per
provider, live costs, custody and all pre-call caps remain. The criteria, declared evidence
universe, Context and Notes above now carry only the retained function. No specification
status or historical proof was changed.
