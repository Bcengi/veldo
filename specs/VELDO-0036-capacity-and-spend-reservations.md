---
schema: veldo.spec/v1
id: VELDO-0036
title: Durable capacity and spend reservations
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W21
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023]
placement: [fleet, metrics, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/accounts.py"
  - ".veldo/accounts.py"
  - "packs/*/.veldo/accounts.py"
  - "engine/.veldo/budget.py"
  - ".veldo/budget.py"
  - "packs/*/.veldo/budget.py"
  - "engine/.veldo/control_reservation*.py"
  - ".veldo/control_reservation*.py"
  - "packs/*/.veldo/control_reservation*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0036_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0036-capacity-and-spend-reservations.md"
  - "specs/index.md"
  - "proof/VELDO-0036/*"
behavior_bearing: true
observability:
  logs: >
    Reservation decisions identify account, project, unit, request identity, maximum charge,
    remaining allowance, and retained exposure.
  metrics: >
    Report reserved capacity, settled charges, outstanding exposure, unknown spend, and pre-call
    refusals at all three ceilings.
  traces: >
    Join invocation and request identities to pricing and hard-limit evidence, allocation commit,
    usage sequence, and settlement receipt.
  error_taxonomy: >
    Distinguish capacity exhausted, ceiling exceeded, unenforceable charge bound, duplicate usage,
    unknown spend, and retirement incomplete.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Concurrent admission reserves capacity and cost atomically at account, project, and
      unit ceilings before dispatch. Set: Real authority transactions from competing client
      processes sharing control.sqlite3, across every configured account/project/unit limit.
      Completeness: Drive below, equal, and above-bound allocations for each ceiling and
      intersecting project/account pairs. SIGKILL after reservation commit before reply and retry
      the same identity; compare all balances and allocation rows, requiring at most the
      admissible capacity. Falsifier: Check capacity outside the reservation transaction and race
      two last-slot clients; reservations/capacity-race must detect over-allocation.
    falsified_by: >
      Check capacity outside the reservation transaction and race two last-slot clients;
      reservations/capacity-race must detect over-allocation.
  - id: AC2
    text: >
      Claim: Every billable request, including retries and follow-on calls, allocates its
      enforceable maximum possible charge from all remaining reservations before the provider
      boundary is entered. Set: Trusted adapter request admission against real SQLite, using
      pricing plus hard request limits and a real local request receiver with deterministic
      response bytes. Completeness: Enumerate initial, retry, and follow-on request paths; race
      separate callers for the same remainder after settled charges and outstanding exposure. Test
      below, exact, above, absent, and unenforceable maxima at every ceiling; record receiver
      calls and require zero calls for refusal. Falsifier: Allocate a follow-on request maximum
      after invoking the receiver and race two requests exceeding the shared remainder;
      reservations/pre-call-bound must fail.
    falsified_by: >
      Allocate a follow-on request maximum after invoking the receiver and race two requests
      exceeding the shared remainder; reservations/pre-call-bound must fail.
  - id: AC3
    text: >
      Claim: Usage is deduplicated by invocation and sequence, and timeout, cancellation, or
      delayed reporting never releases outstanding charge exposure. Set: Real usage ingestion,
      request cancellation, and restart processes over committed request allocations, with known
      and unknown charge outcomes. Completeness: Duplicate and reorder usage messages, kill the
      adapter after receiver acceptance before usage acknowledgement, and restart ingestion.
      Compare settled charges and retained exposure; only reconciled usage or authoritative
      no-charge evidence frees an allocation, and unbounded exposure blocks affected admission.
      Falsifier: Release charge exposure on timeout after the receiver accepted the request;
      reservations/timeout-exposure must catch a subsequent request spending that remainder.
    falsified_by: >
      Release charge exposure on timeout after the receiver accepted the request;
      reservations/timeout-exposure must catch a subsequent request spending that remainder.
  - id: AC4
    text: >
      Claim: A capacity slot stays reserved or quarantined until containment emptiness, outcome,
      accounting, and required resource cleanup are durably reconciled. Set: Reservation
      retirement API receiving real process-exit and filesystem-cleanup observations, including an
      unknown outstanding effect. Completeness: Hold a child process alive, withhold accounting,
      and interrupt cleanup in turn; race retirement and new admission through SQLite. Kill the
      retiring process before its final commit and require the restarted reader to retain the slot
      until every registered retirement obligation is present. Falsifier: Release the slot on
      parent exit while a real descendant remains alive; reservations/premature-retirement must
      refuse new use of the slot.
    falsified_by: >
      Release the slot on parent exit while a real descendant remains alive;
      reservations/premature-retirement must refuse new use of the slot.
required_evidence: [unit, integration]
rollback: >
  Stop new allocations and preserve all balances and uncertain exposure; reconcile usage and
  retired containment before releasing capacity or money.
---

## Intent

Reserve capacity and maximum request charges durably so concurrent work cannot spend the same remaining allowance.

## Context

Package B, W21 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R22, R31, R43-R45, R57, R70. Package A supplies the accepted contracts; this draft grants no implementation or activation authority.

The critical risk floor reflects the consequences of failure in this boundary. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

Provider prices, live charges, production adapter certification, and governor policy tuning are D work.

## Notes

D1 is inherited from W8; D3 blocks activation of the containment-backed capacity profile. The reviewed R45 amendment requires a separate allocation before every billable request, not just an invocation estimate. B proves the transaction and pre-call enforcement using a local receiver; D must qualify each live provider pricing model and enforceable maximum. Monetary arithmetic must use exact units with declared rounding, never binary floating-point budget comparisons.

