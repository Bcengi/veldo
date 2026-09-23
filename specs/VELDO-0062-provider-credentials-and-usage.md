---
schema: veldo.spec/v1
id: VELDO-0062
title: Provider credential separation and live usage accounting
status: ready
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
      Claim: Each logged-in subscription CLI invocation checks and reserves applicable usage
      allowance before launch; the worker stops when a cap is reached. Set and completeness:
      Inventory initial, retry and follow-on invocations for both providers; record supported
      invocation/time controls, CLI-reported tokens/messages and subscription rate-limit windows.
      Exercise available, exhausted and unknown allowance, two invocations competing for one
      remainder, live cap-triggered stop and a reported rate-limit reset. Record launch counts,
      elapsed time and reported usage; refused checks launch nothing. Qualification requires no
      price or per-request monetary maximum. Falsifier: Check a follow-on cap after launch;
      the pre-call ordering check must fail.
    falsified_by: >
      Check a follow-on cap after launch; the pre-call ordering check must fail.
  - id: AC3
    text: >
      Claim: Usage settles once per invocation/sequence and incomplete reports retain conservative
      usage reservations. Set and completeness: Capture live CLI usage receipts from each configured subscription, ingest
      normal/duplicate/missing reports, and compare balances independently in their declared
      invocation/time/token/message units; cancellation or timeout alone cannot release an accepted request allocation.
      Falsifier: Release reserved usage on accepted-invocation timeout; the next-invocation refusal check must
      fail.
    falsified_by: >
      Release reserved usage on accepted-invocation timeout; the next-invocation refusal check must fail.
  - id: AC4
    text: >
      Claim: Subscription usage and remaining allowance are attributed to the stored account/project/unit. Set and
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

## What the reviewer judges

- Normal use: Claude Code and Codex run through the logged-in subscriptions; each invocation checks its
  usage cap before launch, usage is settled once from the CLI's own report, and totals are shown per
  account, project and unit.
- Threat model: a worker or tool child reading the provider model credential, and a worker's own report
  claiming less usage than the CLI recorded. MCP servers keep the credentials their configuration gives
  them (VELDO-0127). The owner's account and the installed engine are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); a child
  deliberately hunting credentials through kernel interfaces; CLI report formats the installed CLIs do
  not produce; lost reports after a crash (Release 2).

## Notes

Qualify one logged-in subscription account for each of Claude Code and Codex on the two MVP
host profiles. Models run only through those subscriptions; paid model APIs are prohibited.
There is no per-call price. Record actual invocation counts, wall time, tokens or messages as
reported by the CLI, and the subscription's exposed rate-limit windows, resets and usage
watermarks. Do not fabricate unreported counters or require pricing to qualify an adapter.

VELDO-0036 supplies atomic account/project/unit usage reservations. Before every initial,
retry or follow-on CLI invocation, check all applicable caps and outstanding reservations;
refuse exhausted allowance or an active rate-limit window. Stop the worker when its cap is
reached. Use supported invocation/time controls when finer usage controls are unavailable;
reported tokens/messages are accounted at their actual observation granularity, without a
claim of a hard per-request maximum.

Unknown usage is never zero. Retain its reservation and conservatively bound the remaining
allowance; if that cannot be done, stop and refuse further invocation until reconciled.
Timeout, cancellation and missing reports never replenish allowance. A rate-limit window
reopens only on its reported reset or refreshed allowance, not an invented reset. Protect raw
receipts and publish redacted digests sufficient for independent checking.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, pre-invocation subscription usage caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 1: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC3
restart/reordered reports moved to Release 2; AC1 all-authentication/host and AC4 two-
account/two-project matrices moved to Release 4, except the two MVP hosts. One account per
provider, live subscription usage, custody and all pre-invocation caps remain. The criteria, declared evidence
universe, Context and Notes above now carry only the retained function. No specification
status or historical proof was changed.
