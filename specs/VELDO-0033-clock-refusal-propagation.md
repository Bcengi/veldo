---
schema: veldo.spec/v1
id: VELDO-0033
title: Clock claim-refusal propagation through execution and landing
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W18
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0031]
placement: [fleet, loop]
protected_paths: []
footprint:
  - "engine/.veldo/work.py"
  - ".veldo/work.py"
  - "packs/*/.veldo/work.py"
  - "engine/.veldo/tasks.py"
  - ".veldo/tasks.py"
  - "packs/*/.veldo/tasks.py"
  - "engine/.veldo/dispatch.py"
  - ".veldo/dispatch.py"
  - "packs/*/.veldo/dispatch.py"
  - "engine/.veldo/executor.py"
  - ".veldo/executor.py"
  - "packs/*/.veldo/executor.py"
  - "engine/.veldo/lander.py"
  - ".veldo/lander.py"
  - "packs/*/.veldo/lander.py"
  - "scripts/suites/*_veldo_0033_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0033-clock-refusal-propagation.md"
  - "specs/index.md"
  - "proof/VELDO-0033/*"
behavior_bearing: true
observability:
  logs: >
    Execution and landing results retain unanswerable with unit, holder, both clocks, tolerance,
    interrupted station, and operations action.
  metrics: >
    Count clock-refused execution and landing attempts independently of contention timeouts;
    uncertain units cause no launch or publication.
  traces: >
    Join claim refusal through work selection, dispatch result, executor report, and land-lock
    result without reason loss.
  error_taxonomy: >
    Distinguish unanswerable from claimed, ordinary lock timeout, capability refusal, and
    authority unavailable.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: All shipped claim callers preserve the refusal reason and stop affected execution
      instead of treating uncertainty as ordinary contention. Set: claim_task, work.Worker claim
      selection, dispatch and executor result paths, and serialized lander lock acquisition.
      Completeness: Discover claim() call sites and compare them with the propagation matrix; use
      real future-heartbeat records and separate CLI processes for each entry. Observe no launched
      builder and no claimed-success result, with the original refusal in persisted run reporting.
      Falsifier: Discard _reason in work claim selection after a real future-heartbeat refusal;
      clock-propagation/work-result must fail.
    falsified_by: >
      Discard _reason in work claim selection after a real future-heartbeat refusal;
      clock-propagation/work-result must fail.
  - id: AC2
    text: >
      Claim: An uncertain land lock returns a named stand-down promptly and leaves both local and
      remote Git refs unchanged. Set: Real lander invocations against a disposable repository and
      bare remote with a held future-heartbeat LAND_LOCK_UNIT. Completeness: Record refs and claim
      bytes, start the lander, and measure completion without waiting out its contention timeout.
      Race a lock heartbeat change at acquisition and assert no sync, merge, gate, finalize, or
      lock-owner rewrite after an unanswerable result. Falsifier: Retry unanswerable until the
      ordinary lock timeout and return only stage lock; clock-propagation/lander-reason must
      detect the delay and missing reason.
    falsified_by: >
      Retry unanswerable until the ordinary lock timeout and return only stage lock;
      clock-propagation/lander-reason must detect the delay and missing reason.
  - id: AC3
    text: >
      Claim: Operations reconciliation is required before resuming uncertain work, while ordinary
      contention and valid success remain distinct. Set: Persisted interrupted execution and
      landing results across restart, with current, held, uncertain, and reconciled claims.
      Completeness: SIGKILL the caller after recording refusal, restart it, and inspect stored
      reason and authority state; neither restart nor _is_stale false grants permission. Exercise
      a current claim and authorized reconciliation as positive controls through the same real
      entry points. Falsifier: Convert persisted unanswerable to retryable claimed on caller
      restart; clock-propagation/restart must observe continued stand-down.
    falsified_by: >
      Convert persisted unanswerable to retryable claimed on caller restart;
      clock-propagation/restart must observe continued stand-down.
required_evidence: [unit, integration]
rollback: >
  Stop affected callers and preserve the refusal record; rollback must retain claim stand-down and
  cannot restore blind retry on uncertainty.
---

## Intent

Carry an unanswerable claim refusal to execution and landing callers so they stop with a usable reason.

## Context

Package B, W18 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R25, R44, R51, R57. Package A contracts must be accepted before implementation; this draft grants no implementation or activation authority.

Dropping claim uncertainty at execution or landing boundaries could allow unsafe retries or hide a required stop. The declared risk floor is high. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

No new clock detector, candidate construction, or completion predicate is implemented here.

## Notes

work.py and lander.py currently discard _reason, and the lander reports a generic lock stage. Preserve their ordinary return contracts additively while making uncertainty explicit. D1 is inherited for authority-backed claims. Future tests may run Git operations only inside disposable fixtures; this specification authoring task does not land or push source. C retains the larger lander redesign.

