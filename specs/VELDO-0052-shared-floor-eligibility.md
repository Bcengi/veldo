---
schema: veldo.spec/v1
id: VELDO-0052
title: Shared eligibility in work, frontier, plan, direct executor, and review
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W37
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049]
placement: [fleet, loop, contracts]
protected_paths: []
footprint:
  - "engine/.veldo/work.py"
  - ".veldo/work.py"
  - "packs/*/.veldo/work.py"
  - "engine/.veldo/work_state.py"
  - ".veldo/work_state.py"
  - "packs/*/.veldo/work_state.py"
  - "engine/.veldo/frontier.py"
  - ".veldo/frontier.py"
  - "packs/*/.veldo/frontier.py"
  - "engine/.veldo/plan.py"
  - ".veldo/plan.py"
  - "packs/*/.veldo/plan.py"
  - "engine/.veldo/executor.py"
  - ".veldo/executor.py"
  - "packs/*/.veldo/executor.py"
  - "engine/.veldo/dispatch.py"
  - ".veldo/dispatch.py"
  - "packs/*/.veldo/dispatch.py"
  - "engine/.veldo/control_eligibility*.py"
  - ".veldo/control_eligibility*.py"
  - "packs/*/.veldo/control_eligibility*.py"
  - "scripts/suites/*_veldo_0052_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0052-shared-floor-eligibility.md"
  - "specs/index.md"
  - "proof/VELDO-0052/*"
behavior_bearing: true
observability:
  logs: >
    Eligibility results expose station, accepted snapshot and published watermark, failed input, and
    current versus expected versions.
  metrics: >
    Count refused entries by prerequisite, suppressed stale offers, incomplete completion chains,
    and denied provider requests.
  traces: >
    Join selection and claim to dispatch, review, result acceptance, and publication decisions using
    the same input digest set.
  error_taxonomy: >
    Distinguish draft plan, missing admission, unresolved dependency, stale negative read, expired
    authority, unknown spend, and historical-only completion.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: All floor entries invoke the shared station-specific eligibility decision, including
      direct build and review calls. Set: frontier.claimable, dependency_gate,
      _plan_build_candidates, work.WorkLoop._claim_next and _still_claimable, plan.cmd_run_check,
      executor.LiveLoop.run_check and Executor.run, dispatch.Dispatcher.dispatch and
      _dispatch_review; claim, redispatch, result acceptance, and publication services from B remain
      guarded. Completeness: Enumerate executable entry registrations and call sites against R70,
      then invoke each in a real client process using control.sqlite3 snapshots, real claims, signed
      commands, and a contained fake-model child. Cross planned/standalone and build/review with
      draft plan, absent admission, unresolved decision/dependency, stale scope, and valid inputs.
      Count actual launches and require named refusals. Falsifier: Retain dependency_gate review
      exemption and call _dispatch_review directly against a draft governing plan;
      eligibility/direct-review must detect entry into the reviewer process.
    falsified_by: >
      Retain dependency_gate review exemption and call _dispatch_review directly against a draft
      governing plan; eligibility/direct-review must detect entry into the reviewer process.
  - id: AC2
    text: >
      Claim: Rechecking after claim validates the complete current read set rather than assuming
      prerequisites are monotonic. Set: WorkLoop._still_claimable, Executor.run station transitions,
      and Dispatcher._dispatch_review over specs, plans, releases, decisions, floors, policy,
      membership, admission, graph, roster, reservations, and receipts in the real store.
      Completeness: Derive applicable entry/input pairs from A contracts; another process changes
      each version or inserts a blocker after selection while project version stays fixed. Race
      before claim, accepting dispatch, review, and result acceptance; assert no stale transition or
      publication permission and retained refusal reasons after SIGKILL/restart. Falsifier: Make
      _still_claimable check only current_status after a prerequisite receipt is withdrawn;
      eligibility/claim-race must detect a launched stale unit.
    falsified_by: >
      Make _still_claimable check only current_status after a prerequisite receipt is withdrawn;
      eligibility/claim-race must detect a launched stale unit.
  - id: AC3
    text: >
      Claim: work_state.concluded and work_report, frontier.unmet_dependencies and current_status,
      and plan._shipped_set and item_state consume the same revision-bound completion facts. Set:
      Real run registry, proof and verdict files, event projections, and signed receipt snapshots
      for build-only, artifact-accepted, revision-landed, and objective-satisfied subjects.
      Completeness: Drive each fact through its actual producer and read each consumer in a new
      process. Add a passing verdict and shipped status without a landing receipt, supersede a
      prerequisite, and corrupt a receipt signature; none may satisfy engineering dependencies.
      Compare all four facts and historical labels without inventing authority for unenrolled
      records. Falsifier: Let work_state.concluded return true for manifest plus passing verdict
      after a build-only attempt; eligibility/completion-readers must detect false landed
      completion.
    falsified_by: >
      Let work_state.concluded return true for manifest plus passing verdict after a build-only
      attempt; eligibility/completion-readers must detect false landed completion.
  - id: AC4
    text: >
      Claim: Floor dispatch retains B request reservations and qualified resource limits through
      retries and follow-on model calls. Set: Executor.run build/review invocations and
      Dispatcher._dispatch_build/_dispatch_review using the real reservation store, trusted request
      adapter, local fake-provider process, and systemd/cgroup runner. Completeness: Enumerate
      initial/retry/follow-on request paths; race two requests for the last account/project/unit
      remainder, retain exposure after killing an accepted request before usage, and remove each
      required memory/CPU-time/storage-byte/inode limit before launch. Inspect actual receiver calls
      and installed group limits; refused work produces no provider call or unbounded child.
      Falsifier: Bypass the reservation predicate on a review follow-on call while another process
      consumes the remainder; eligibility/review-request-bound must detect the forbidden receiver
      request.
    falsified_by: >
      Bypass the reservation predicate on a review follow-on call while another process consumes the
      remainder; eligibility/review-request-bound must detect the forbidden receiver request.
required_evidence: [unit, integration]
rollback: >
  Stop affected enrolled entries, preserve signed history and pending obligations, and restore the
  prior compatible consumer only after current authorization is revalidated.
---

## Intent

Use one evidence-based eligibility decision at every floor entry and one completion meaning in every floor reader.

## Context

Package C, W37 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A and B contracts govern this repair. This is a draft, not implementation or activation authority.

R14, R39, R43-R45, R51-R52, and R70 drive real consumer rewiring. A missed entry or stale read permits unauthorized execution even if selection looked safe. The declared risk floor is critical; required approval must bind the eventual change and proof and is not recorded by this declaration.

## Out of scope

New project graph operations and historical migration are F and H. Live provider price qualification remains D.

## Notes

D1/D2 block authoritative snapshot consumption; D3/D4 block the contained isolated-clone execution used by the race matrix. The inspected WorkLoop assumes dependency monotonicity, frontier exempts review, plan run-check reads status, and work_state concludes from a passing verdict. Replace those shortcuts for enrolled work with A predicates and B snapshots. control_eligibility names a proposed adapter, not a second policy implementation; resolve its contracts/fleet placement before ready. Keep B clock unanswerable refusals intact. W39 and W40 supply decision and regression consumers; W42 owns the final publication boundary. Save each negative-control diff and its named failing observation, using actual processes rather than mocked hook success.
