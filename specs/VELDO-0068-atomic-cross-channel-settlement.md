---
schema: veldo.spec/v1
id: VELDO-0068
title: Atomic cross-channel settlement and principal-based quorum enforcement
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W53
plan_revision: 3
depends_on: [VELDO-0035, VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067]
placement: [contracts, tracker, engine, distribution]
protected_paths: [.veldo/settlements/*]
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/request_reconcile.py"
  - ".veldo/request_reconcile.py"
  - "packs/*/.veldo/request_reconcile.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/control_request_settlement*.py"
  - ".veldo/control_request_settlement*.py"
  - "packs/*/.veldo/control_request_settlement*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/control_assignment.py"
  - ".veldo/control_assignment.py"
  - ".veldo/settlements/*.json"
  - "scripts/suites/*_veldo_0068_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0068-atomic-cross-channel-settlement.md"
  - "specs/index.md"
  - "proof/VELDO-0068/*"
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
      Claim: Settlement preserves the offered ruling and the actual actor-authored reasoning. Set
      and completeness: Enumerate enabled request touchpoints for grooming, admission, priority and
      finding/decision disposition; submit choices and rejection through real signed Telegram
      assertions and compare source, stored ruling/rationale and typed effects. Falsifier: Convert
      all chosen options to a generic decided value; the carried-ruling comparison must fail.
    falsified_by: >
      Convert all chosen options to a generic decided value; the carried-ruling comparison must
      fail.
  - id: AC2
    text: >
      Claim: One request version has at most one terminal settlement with all components committed
      together. Set and completeness: Send two conflicting authenticated answers for one
      request/version to real SQLite; inspect ruling, nonce, typed effects, terminal state and
      receipt as one consistent result with one winner. This same key applies to later UI/API
      answers. Falsifier: Insert the receipt separately from the terminal transaction; the
      transaction-boundary observation must fail.
    falsified_by: >
      Insert the receipt separately from the terminal transaction; the transaction-boundary
      observation must fail.
  - id: AC3
    text: >
      Claim: Terminal request state materializes with its exact settlement reference. Set and
      completeness: Settle accepted and rejected requests, read the published snapshot in another
      process and submit another ordinary answer ID; require terminal status, exact receipt/version
      and no reapplication from stale YAML. Falsifier: Leave request status open after settlement;
      the terminal-inbox check must fail.
    falsified_by: >
      Leave request status open after settlement; the terminal-inbox check must fail.
  - id: AC4
    text: >
      Claim: Applicable policy and request authority requirements are conjunctive. Set and
      completeness: Derive the actual journey role/count/independence predicates; exercise stronger
      request role, wrong owner, duplicate principal, stale presentation and valid authority for
      acceptance and rejection. Unsupported quorum policies block rather than weaken requirements.
      Falsifier: Ignore request.required_roles when policy roles pass; the stronger-role refusal
      check must fail.
    falsified_by: >
      Ignore request.required_roles when policy roles pass; the stronger-role refusal check must
      fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Atomic cross-channel settlement and principal-based quorum enforcement. Deliver the normal function needed by the running factory journey.

## Context

W53 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 3.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## What the reviewer judges

- Normal use: an owner answers a presented request (grooming, admission, priority, finding or decision
  disposition) through a signed Telegram assertion, or later through the authenticated API, which uses
  the same settlement service. The one SQLite authority records one terminal settlement per request
  version, carrying the exact offered ruling and the owner's own reasoning, and commits the ruling,
  the nonce, the typed effects, the terminal request state and the receipt in one transaction. The
  published request state then reads as terminal with that settlement's receipt and version, and an
  ordinary later answer changes nothing. Policy requirements and the request's own required roles
  both apply.
- Threat model: a chosen option flattened to a generic value; two conflicting answers for one request
  version both taking effect or leaving a half-written settlement; a receipt written outside the
  terminal transaction; a request left open after settlement or reapplied from stale YAML; a stronger
  request role ignored because policy roles pass; the wrong owner, a duplicate principal or a stale
  presentation accepted; an unsupported quorum policy weakening a requirement. The owner's account,
  the store and the signing edge are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); the crash,
  replica and full cross-channel matrix and restart recovery (Release 2, see History); an answer
  accepted on another connection after a settlement reads the answers and before it commits, which
  takes no effect but is not listed on the settlement as not counted (Release 2, see History); forged
  rows in our own store and files planted in the installed directory.

## Notes

One SQLite authority owns settlement, terminal request state and typed effects. No
FilesystemSettlementStore may become an enrolled second authority. Telegram is qualified
first; authenticated UI/API uses the same settlement service and must test one conflicting-
answer pair, not the deferred exhaustive channel/recovery matrix.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 3: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC2
crash/replica/cross-channel matrix and AC3 restart/materialization recovery moved to Release
2; unused AC4 quorum combinations moved to Release 3. Jira work is dropped. Actual ruling,
atomic terminal state/effects and applicable authority remain, including one Telegram/UI
conflict check. The criteria, declared evidence universe, Context and Notes above now carry
only the retained function. No specification status or historical proof was changed.

2026-09-24, implementation: `scripts/check_teeth_mutations.py` was added to the footprint so the
declared falsifiers can be registered as finding 68 of the existing teeth mutation driver, as
VELDO-0065, VELDO-0066 and VELDO-0067 registered theirs. The criteria, status and risk are unchanged.

2026-09-24, implementation: `.veldo/control_request_settlement.py` is the one settlement service on the
control store. The journey's five enabled touchpoints and their role, count and independence predicates
are its `JOURNEY` configuration; a request names its touchpoint and its own required roles and quorum
through requester-signed terms bound as the assignment's subject. Telegram answers are the VELDO-0065
presenter's accepted answers; the authenticated API edge's answers are accepted under the same
presentation rules. One registered transaction, keyed and nonced by request and version, writes the
settlement (offered choice, ruling, the owner's reasoning, the signed assertion), the typed effect, the
receipt and the terminal request state; the earliest binding answer wins and every other is named. The
requirement is the conjunction of the journey policy and the request's terms, and a count or an
independence above one blocks as unsupported. Terminal state is published through a VELDO-0035
accepted revision and snapshot. Rows, the red record at 335d996 and the finding 68 mutations are in
`proof/VELDO-0068/`. Every Telegram answer runs against a loopback Bot API server, not the Telegram
service. The criteria, status and risk are unchanged.

2026-09-24, review fix: `.veldo/control_assignment.py` (engine copy byte-identical) was added to the
footprint. The VELDO-0064 `answer` command moved a presented request that carries settlement terms to
SUBMITTED with no settlement, typed effect or receipt, and a later answer was then refused as closed, so
that request version ended with no settlement. The command now refuses such a request as
`settlement_required`, so the settlement service is the only way it is answered; a request without
terms is answered exactly as before. The row case is in `settlement/one-transaction`, red at 0617f3d,
with the finding 68 mutation `inbox-answer-bypasses-settlement`. The criteria, status and risk are
unchanged.

2026-09-24, review, filed for Release 2: a settlement lists as not counted only the answers it read.
An answer accepted on another connection after that read and before the settlement commits takes no
effect, is never counted and is refused as already_settled on a later settlement, but it is not listed
on the settlement. Listing it (pinning the version's answer set in the terminal transaction) is Release
2 work. The module's docstring and the proof README now promise only what holds. The criteria, status
and risk are unchanged.
