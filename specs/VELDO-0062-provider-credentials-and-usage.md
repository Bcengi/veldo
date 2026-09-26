---
schema: veldo.spec/v1
id: VELDO-0062
title: Provider subscription logins and live usage accounting
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
  - "scripts/check_teeth_mutations.py"
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
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Provider subscription logins and live usage accounting. Deliver the normal function needed by the running factory journey.

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
  usage than the CLI recorded; a usage reservation released before its settlement (the pool, the limit
  and the re-run decision are VELDO-0160's). MCP servers keep the
  credentials their configuration gives them (VELDO-0127, VELDO-0144). The owner's account and the
  installed engine are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); a child
  deliberately hunting credentials through kernel interfaces; CLI report formats the installed CLIs do
  not produce; lost reports after a crash (Release 2); a worker's tools reading their own engine
  login, accepted for Release 1 by the owner (Telegram 29163) with the separation in Release 2.

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
account takes work at the next dispatch. Running on many accounts at once, choosing among them, the
limit and the re-run rule are VELDO-0160.

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

2026-09-25, PLAN-0019 revision 4 review: the factory loop, with its reset timers and the
re-dispatch or question that carries out AC6's decision, is VELDO-0154, split from VELDO-0129 (its
former AC4 and AC6 are VELDO-0154 AC1 and AC3), and the references follow. Criterion meaning and status
unchanged.

2026-09-25, PLAN-0019 revision 4, third review: the title drops "credential separation", which is
Release 2 hardening since the owner's answer (Telegram 29163), and names what Release 1 keeps: each
invocation on its own account's subscription login, and live usage accounting. Status unchanged.

2026-09-25, PLAN-0019 revision 4, third review: this specification held six criteria, so the pool (AC5)
and the `account_limit` classification with the re-run-or-ask decision (AC6) move to the new draft
VELDO-0160, where AC5 is its AC1 unchanged and AC6 is two criteria with a falsifier each; the selection
order moves with them. AC1 to AC4 (the login per dispatch, the pre-launch caps, settlement and
attribution) are unchanged. Status unchanged.

2026-09-25, built (Release 1, Linux): the account records are a store record family
(`control_accounts`) over profiles `.veldo/accounts.py` prepares for either provider; the launch
receiver reads the account the accepted contract records, gives the engine only that account's
profile on this host and no paid-API credential variable, and checks and reserves each initial, retry
or follow-on invocation through VELDO-0036 before anything is spawned; Claude Code's stream JSON and
Codex's exec JSON are read for usage and rate-limit windows, kept as private raw receipts with their
digests in the ledger, and settled once, unknown usage retained. Proof in `proof/VELDO-0062/`: suite
`75_veldo_0062_accounts` (15 rows), the red record at 0af8dc0 (all 15 red by assertion) and 17
finding 62 mutations, each red on its named row. The footprint adds `scripts/check_teeth_mutations.py`,
where the criteria's falsifiers are registered as finding 62 (and finding 36's mutants of
`control_reservations.py` now copy its siblings, since it loads the account records). The engines in
the suite are fake executables printing the installed CLIs' report formats; the live run of the real
CLIs on the owner's registered subscriptions is not part of this build. Status unchanged.

2026-09-25, second review fixed (Release 1, Linux): the first build's fake engines were written to match
our own reader, so nothing checked them against the real CLIs, and three defects passed. Claude Code's
conclusive usage is now the result's `modelUsage` summed over every model (input, output, cache read and
cache creation tokens), never the result's `usage`, which the binary's own schema says is the main agent
loop only; a result without it leaves tokens unknown. Codex's limit signal is now the usage-limit message
`codex exec --json` actually prints (in its `error` event and failed turn), with the reset it states, at
the end of that local minute, or none when it states none (the account then stays refused until observed
otherwise); the `rate_limits` field it read is never printed by exec. The engine environment strips every
login variable by family (`ANTHROPIC_`, `OPENAI_`, `CODEX_`, `CLAUDE_CODE_USE_`, credential-word `CLAUDE_`
names) and every name the installed binaries' own credential tables list, not a fixed list. The
provider-to-variable map is named once (`accounts.PROFILE_ENV`), and `fleet.py` no longer hands a Codex
account to a Claude session. Every line the suite's fakes print is built in a shape the installed
binaries declare, and two rows check them against `proof/VELDO-0062/cli-formats.json`, which
`extract_formats.py` reads out of claude 2.1.281 and codex 0.154.0 without running either. The scaffold lays
down `accounts.py`, which `control_accounts` now loads. The footprint already covers every file changed
(`fleet.py`, `init_scaffold.py` and `proof/VELDO-0062/*` included). Status unchanged.

2026-09-26, third review fixed (Release 1, Linux): the strip tables are now the installed binaries' own
lists, read by `extract_formats.py` into `cli-formats.json`: Claude Code's sensitive-variable set (its
logins, the OAuth store, host credentials file, managed and remote settings redirects, the OAuth,
staging, bridge and federation overrides), its session, bridge, trusted-device, background-session and
file-descriptor tokens and the variables a host credentials file may set, and Codex's auth redirects
(login endpoint, client, issuer, refresh and revoke overrides, ChatGPT backend, model endpoints,
organization, `CODEX_SQLITE_HOME`). The credential-word rule is gone: a count or threshold is not a login.
The strip applies to the inherited environment only; what an adapter configures reaches the engine as
configured (its model table included), and a configured login, redirect or provider switch is refused by
name when the configuration is loaded. A resumed Claude Code session is charged its running total less
the session's running total the ledger settled last (each final report now records it), unknown when
that is unknown or larger; a resumed Codex thread is never subtracted. Codex's whole error table is read:
the workspace credits, spend cap, quota and plan messages are each an exhausted window with no reset. The
reset boundary is tested at the seams that take a clock (the account record, the reservation check, the
Codex reader), so the suite no longer waits for a minute to end. Proof: suite `75_veldo_0062_accounts`
(21 rows), the red record at 0af8dc0 (all 19 behavior rows red by assertion, the two format rows green)
and 48 finding 62 mutations, each red on its named row; findings 36 (its report-order mutant follows the
settled session), 39, 40 and 41 still reject. Main merged at a166d14. Status unchanged.

2026-09-26, fourth review fixed (Release 1, Linux): a resumed Claude Code session's settled total was
subtracted by the session id in the contract's `resume` and never checked against the session id the
CLI reports in its stream, so a CLI that started a fresh session was charged less than it recorded. The
settled total is now subtracted only when the CLI reports the session the contract resumes; another
session is charged its whole running total (a fork that carried the earlier turns is over-counted,
never under-counted), and each final report records which case charged it (`whole`, `difference` or
`whole_other_session`). Proof: suite `75_veldo_0062_accounts` (22 rows, the new one
`settle/resumed-other-session`), the red record at 0af8dc0 (all 20 behavior rows red by assertion, the
two format rows green) and 50 finding 62 mutations, each red on its named row; findings 36, 39, 40 and
41 still reject. Main merged at aa5c721d. Status unchanged.
