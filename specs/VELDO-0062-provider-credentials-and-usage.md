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
plan_revision: 4
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
  - "engine/.veldo/control_account*.py"
  - ".veldo/control_account*.py"
  - "packs/*/.veldo/control_account*.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "packs/*/.veldo/control_launch*.py"
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
      Claim: Each invocation authenticates only with the subscription login of the account its
      dispatch recorded, and internal handles derive from accepted contracts. Set and completeness:
      For Claude Code and Codex on Linux (the Mac read-back is VELDO-0147), read back that each
      invocation's engine environment carries exactly the profile (Claude Code's `CLAUDE_CONFIG_DIR`,
      Codex's `CODEX_HOME`) of the account the Runner selected and the dispatch recorded, never a
      profile taken from the caller's environment or another account's, and no paid-API credential
      variable; substitute contract, unit, station and expiry and require refusal. MCP server credentials are
      passed exactly as configured under VELDO-0127 and VELDO-0144; they are not provider model
      credentials and are not refused by this check. Separating the provider login from the worker's
      tool and build children is Release 2 hardening for both engines (owner, Telegram 29163): in
      Release 1 a tool may read its own engine login, the same as an interactive session today.
      Falsifier: Take the profile directory from the caller's environment instead of the dispatch
      record; the login-source check must fail.
    falsified_by: >
      Take the profile directory from the caller's environment instead of the dispatch record; the
      login-source check must fail.
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
      completeness: For each registered account of each provider and the journey project, alter ambient account
      labels and report attribution, and remove measurement while retaining allocation; compare
      displayed watermark and totals to actual stored receipts. Falsifier: Use a caller-supplied
      account label for usage; the ledger-attribution comparison must fail.
    falsified_by: >
      Use a caller-supplied account label for usage; the ledger-attribution comparison must fail.
  - id: AC5
    text: >
      Claim: The owner registers any number of logged-in subscription accounts for each provider,
      each once with its own login, and the factory runs work on all of them at the same time, each
      with its own credentials, usage and rate-limit windows, moving new work off an account that
      has reached its limit. Set and completeness: Register three Claude Code accounts and one Codex
      account (each its own profile: Claude Code's config directory, Codex's home), run concurrent
      work across them, and read back that each invocation used exactly its own account's profile and
      was charged to that account; exhaust one account's allowance and require new work to go to
      another account of the same provider while nothing is sent to the exhausted one until its
      reported reset; add an account later with no restart of running work. An account with no
      usage observation yet admits one run at a time until its first observation, because unknown is
      never zero. Falsifier: Launch two accounts' work with one shared profile; the per-account
      isolation check must fail.
    falsified_by: >
      Launch two accounts' work with one shared profile; the per-account isolation check must fail.
  - id: AC6
    text: >
      Claim: A run stopped by its account's limit is classified `account_limit` with its window and
      reset time, and a re-run-or-ask decision is made over its record: re-run on another account only
      when the record shows no call to an MCP tool not marked read-only, and otherwise ask the owner,
      naming the calls. Set and completeness: Feed the receiver's classification a stream that reports
      its window exhausted, an engine that ends with its rate-limit result, and an ordinary nonzero
      exit, and read back `account_limit` with the window and reset time recorded for the first two
      only. Feed the decision fixture records in the execution record's shape (VELDO-0141) with the
      read-only marks of catalog revisions (VELDO-0144): one with no MCP call, one with only calls to
      tools marked read-only, one with a call to a tool not marked read-only, and one with a call to a
      tool of a server whose revision marks nothing; the first two decide re-run and the others decide
      ask with exactly those calls named. Carrying out the decision (the new dispatch, or the question
      to the owner) is VELDO-0129 AC6. Falsifier: Decide re-run for a record that shows a call to an
      MCP tool not marked read-only; the ask-decision row must fail.
    falsified_by: >
      Decide re-run for a record that shows a call to an MCP tool not marked read-only; the
      ask-decision row must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Provider credential separation and live usage accounting. Deliver the normal function needed by the running factory journey.

## Context

W47 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
Section 8 of the approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md)
designs the account pool; section 6 the login boundary.
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
- Threat model: an invocation authenticated with another account's profile or one taken from the
  caller's environment; a paid API credential reaching the engine; a worker's own report claiming less
  usage than the CLI recorded; work sent to an account at its limit before its reported reset; a run
  that wrote through an MCP server decided for a re-run on another account instead of asking. MCP servers keep the
  credentials their configuration gives them (VELDO-0127, VELDO-0144). The owner's account and the
  installed engine are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); a child
  deliberately hunting credentials through kernel interfaces; CLI report formats the installed CLIs do
  not produce; lost reports after a crash (Release 2); a worker's tools reading their own engine
  login, accepted for Release 1 by the owner (Telegram 29163) with the separation in Release 2;
  carrying a session over to another account mid-run.

## Notes

Qualify every logged-in subscription account the owner registers, any number per provider (today three
Claude Code and one Codex), for each of Claude Code and Codex on Linux, and on the Mac through VELDO-0147. Models run only through those subscriptions; paid model APIs are prohibited.
There is no per-call price. Record actual invocation counts, wall time, tokens or messages as
reported by the CLI, and the subscription's exposed rate-limit windows, resets and usage
watermarks. Do not fabricate unreported counters or require pricing to qualify an adapter.

The account registry is a store record family at factory scope, not a file under one repository's
Git common directory: each `account` record has an id, a provider (`claude_code` or `codex`), a label,
a status (`active`, `paused` by the owner, or `disabled`), a profile directory per host
(`CLAUDE_CONFIG_DIR` or `CODEX_HOME`), its rate-limit windows (utilization, reset time, observed at,
source dispatch) and its concurrency, one run by default. `.veldo/accounts.py` becomes the local helper
that prepares a profile directory and prints its login step for either provider. The owner registers
an account for a provider and host, logs in once into the prepared profile, and a short qualification
run confirms the login is a subscription; the Runner reads the pool at every dispatch, so the new
account takes work at the next dispatch.

Choosing an account is part of preparing a dispatch, inside the VELDO-0036 reservation. The candidates
are the active accounts of an engine the role allows, with a profile on the chosen host, outside every
reported rate-limit window and under their concurrency. The Runner picks the lowest last reported
utilization on the tightest window, then the fewest active runs, then the least recently used. With
no candidate the unit waits, the UI shows "no account until" the earliest reset, and the factory loop
sets a timer for that time (VELDO-0129 AC4). The re-run rule (AC6) is a decision over a record: it
reads a run's execution record in VELDO-0141's shape and the read-only marks of VELDO-0144's catalog
revisions, so its checks use fixture records and this concern depends on neither; VELDO-0129 AC6 feeds it
each real run's record and carries out what it decides.

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

2026-09-25: the owner widened this item (Telegram 29127 asked, 29128 "yes, widen"): any number of
registered accounts per provider, run concurrently with separate credentials, usage and rate limits, and
new work moved off an account at its limit (AC5; AC4 and the Notes now say each registered account).

2026-09-25, PLAN-0019 revision 4: amended on the approved operating-model design
(docs/design/PLAN-0019-operating-model-design.md, owner Telegram 29162), sections 6 and 8(e), and
the owner's answer to its section 15 (Telegram 29163). The login-separation clause of AC1 moves to
Release 2 as hardening for both engines; AC1 keeps that each invocation authenticates only with the
profile of the account its dispatch recorded, and its falsifier is now the login source. AC5 adds
the re-run rule at a limit (again on another account from the accepted commit only when no call was
made to an MCP tool not marked read-only, otherwise the owner is asked) and one run at a time for an
account with no observation. The footprint adds the account records and the Runner's selection
(`control_account`, `control_runner`). The Notes make the registry a store record family with
per-host profiles for both providers and state the selection order. Status unchanged.

2026-09-25, PLAN-0019 revision 4 review: a specification ships whole and the run-check refuses one whose
dependencies are not shipped, so the Mac leg of this Linux-first qualification moves to VELDO-0147,
which is built after VELDO-0124 and VELDO-0125. Status unchanged.

2026-09-25, PLAN-0019 revision 4 review: AC5 keeps the pool, concurrency, moving new work and the
one-run rule for an unobserved account; the `account_limit` classification and the re-run-or-ask
decision over a record are new AC6, tested with fixture records and with a falsifier of its own, and the
re-dispatch and the question to the owner are VELDO-0129 AC6. The footprint names the Runner where it
lives, `control_launch` (there is no `control_runner` module), which also holds the receiver that
classifies the limit. Status unchanged.
