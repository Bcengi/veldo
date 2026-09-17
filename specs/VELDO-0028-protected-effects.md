---
schema: veldo.spec/v1
id: VELDO-0028
title: Protected effect execution and atomic nonce consumption
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W13
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0026, VELDO-0027]
placement: [engine, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/credential_issue.py"
  - ".veldo/credential_issue.py"
  - "packs/*/.veldo/credential_issue.py"
  - "engine/.veldo/control_effect*.py"
  - ".veldo/control_effect*.py"
  - "packs/*/.veldo/control_effect*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0028_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0028-protected-effects.md"
  - "specs/index.md"
  - "proof/VELDO-0028/*"
behavior_bearing: true
observability:
  logs: >
    Effect denials identify operation, unit, contract digest, capability identity, and consumed or
    refused nonce identity.
  metrics: >
    Count accepted effects, duplicate requests, expired handles, unresolved outcomes, and denied
    credential exchanges.
  traces: >
    Join accepted contract, invocation identity, nonce transaction, receiver evidence, and
    reconciliation obligation.
  error_taxonomy: >
    Distinguish forged task declaration, scope mismatch, stale generation, expired capability,
    nonce replay, and outcome unknown.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The real Credential Service derives short-lived invocation handles from accepted
      contracts and only the trusted Effect Executor can exchange them for privileged operations.
      Set: Each registered privileged operation and invocation scope in real SQLite, with
      credentials held outside the worker OS identity. Completeness: Use actual IPC clients and a
      credential-protected local target; substitute caller task declarations, contract, unit,
      station, sandbox, and expiry. Verify fresh invocation identity and expiry no later than
      contract deadline plus fifteen minutes, and denied direct worker credential reads.
      Falsifier: Trust a worker-supplied task declaration instead of the stored contract and
      invoke an out-of-scope target; effects/forged-scope must observe zero target calls.
    falsified_by: >
      Trust a worker-supplied task declaration instead of the stored contract and invoke an
      out-of-scope target; effects/forged-scope must observe zero target calls.
  - id: AC2
    text: >
      Claim: Authorization, current authority and claim generations, and nonce consumption
      serialize with durable effect acceptance so one capability cannot authorize two logical
      effects. Set: Concurrent protected requests with identical and changed content, using real
      executor processes and a durable target receipt. Completeness: Race both orders against
      revocation and stale generations; count SQLite nonce and acceptance rows and target
      operations. SIGKILL before and after acceptance commit and require one logical identity on
      retry, never fresh permission from a consumed nonce. Falsifier: Move nonce consumption after
      effect acceptance and race two consumers; effects/nonce-race must detect more than one
      accepted effect.
    falsified_by: >
      Move nonce consumption after effect acceptance and race two consumers; effects/nonce-race
      must detect more than one accepted effect.
  - id: AC3
    text: >
      Claim: A crash between acceptance and conclusive target evidence leaves explicit uncertainty
      and forbids blind execution retry. Set: Before-send, target-commit-before-reply, and
      receipt-commit windows for a real local effect receiver with persistent outcome records.
      Completeness: Kill the executor at each barrier, restart it, and compare target bytes,
      consumed nonce, and stored recovery obligation. Receiver evidence may resolve the outcome;
      process absence or a new nonce alone may not. The API preserves the original dispatch for
      W23 recovery. Falsifier: Treat consumed nonce plus absent executor PID as nonexecution after
      the target committed; effects/unknown-retry must catch the duplicate target operation.
    falsified_by: >
      Treat consumed nonce plus absent executor PID as nonexecution after the target committed;
      effects/unknown-retry must catch the duplicate target operation.
required_evidence: [unit, integration]
rollback: >
  Revoke affected handles, stop new effects, and preserve consumed nonces and uncertain dispatches
  for reconciliation; never reset replay protection.
---

## Intent

Execute privileged effects only through trusted capabilities with atomic authorization and nonce consumption.

## Context

Package B, W13 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R22, R33, R36, R39, R45, R57, R74. Package A contracts must be accepted before implementation; this draft grants no implementation or activation authority.

Capability or nonce errors could expose credentials or repeat privileged effects. The declared risk floor is critical. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

Effect-specific resolution commands are W23 and production provider qualification is D.

## Notes

D1 blocks the inherited authority store; D2 controls release of effects that depend on pending publication. Replace the existing FakeIssuer seam with the actual protected internal issuer, while retaining fixture keys only in tests. B tests a real local target and credential boundary; D separately establishes live provider credential separation. No unknown target effect is autonomously enabled.

