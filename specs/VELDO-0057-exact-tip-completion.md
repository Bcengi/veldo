---
schema: veldo.spec/v1
id: VELDO-0057
title: Exact-tip publication, lost acknowledgement recovery, and completion receipt
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W42
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0054, VELDO-0055, VELDO-0056]
placement: [distribution, fleet, contracts, metrics]
protected_paths: []
footprint:
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/lander.py"
  - ".veldo/lander.py"
  - "packs/*/.veldo/lander.py"
  - "engine/.veldo/control_landing*.py"
  - ".veldo/control_landing*.py"
  - "packs/*/.veldo/control_landing*.py"
  - "scripts/suites/*_veldo_0057_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0057-exact-tip-completion.md"
  - "specs/index.md"
  - "proof/VELDO-0057/*"
behavior_bearing: true
observability:
  logs: >
    Publication records expose dispatch, expected remote tip, tested candidate, permit generations,
    outcome query, and receipt publication state.
  metrics: >
    Count exact-tip conflicts, authorization regressions, uncertain publications, reconciled
    acknowledgments, and completed replicated landings.
  traces: >
    Join implementation, proof, independent review, candidate tree, gate invocation, remote ref
    evidence, signed landing receipt, and spec.shipped.
  error_taxonomy: >
    Distinguish stale tip, revoked permission, stale claim, candidate mismatch, rejected approval,
    acknowledgment lost, outcome unknown, and receipt export pending.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: GitLandOps.finalize publishes only a fast-forward candidate under an exact
      expected-old-tip condition enforced by the remote integration. Set: Real serialized
      Lander.land calls and protected Effect Executor requests to a bare Git remote, with two real
      publishing clients and Git ancestry/ref observations. Completeness: Race remote updates after
      verification in both orders, including a moved tip that is still an ancestor of the candidate
      and would pass an ordinary fast-forward push. Require exact-tip rejection without overwriting
      the new tip; rebuild a candidate and obtain fresh applicable checks before retry. Derive
      publication routes from finalize and the effect registry. Falsifier: Use an unconstrained
      fast-forward push after the competing client moves the remote to another candidate ancestor;
      publication/exact-old-tip must detect acceptance despite the changed expected tip.
    falsified_by: >
      Use an unconstrained fast-forward push after the competing client moves the remote to another
      candidate ancestor; publication/exact-old-tip must detect acceptance despite the changed
      expected tip.
  - id: AC2
    text: >
      Claim: Immediately before effect acceptance, finalize rechecks current authority and claim
      generations, admission, scope, decisions, dependencies, approvals, and exact tested candidate.
      Set: GitLandOps.finalize, Lander.land, and B serialized authorization/effect acceptance using
      real control.sqlite3, signed fixture commands, Git objects, and a bare remote. Completeness:
      Enumerate R49/R76 prerequisites and race a second client invalidating each after candidate
      verification. Hold project version fixed for indirect changes. Resume a SIGSTOPped old lander
      after authority/claim generation replacement; require denied publication with durable reason.
      Mutate signed command target/parameters under its old envelope and require digest refusal
      before any ref update. Falsifier: Reuse a pre-verification dependency decision after its
      receipt is withdrawn; publication/dependency-race must detect the forbidden remote update.
    falsified_by: >
      Reuse a pre-verification dependency decision after its receipt is withdrawn;
      publication/dependency-race must detect the forbidden remote update.
  - id: AC3
    text: >
      Claim: Lost publication acknowledgment is reconciled against exact remote candidate and
      ancestry under the original dispatch; uncertainty cannot trigger another publication. Set:
      Real GitLandOps.finalize publication, B recovery commands, control.sqlite3 effect records, and
      a bare remote with durable receive observations. Completeness: SIGKILL the publishing process
      before send, after remote ref acceptance before reply, and after target observation before
      receipt commit. Restart and query actual remote refs and ancestry, including candidate-at-tip,
      candidate-as-ancestor, divergent ref, and unreachable remote. Count receive attempts and
      require original identity, conclusive evidence for success, or AWAITING_AUTHORITY without
      blind retry. Falsifier: Allocate a new publication dispatch after a kill following remote
      acceptance; publication/lost-ack must detect a second receiver publication attempt.
    falsified_by: >
      Allocate a new publication dispatch after a kill following remote acceptance;
      publication/lost-ack must detect a second receiver publication attempt.
  - id: AC4
    text: >
      Claim: Completion becomes authoritative only after remote confirmation and committed,
      replicated landing receipt with spec.shipped; local-only finalize success cannot complete
      work. Set: GitLandOps.finalize results including push disabled, signed control_landing
      receipts, ordered event projection, and W37 work_state/plan/frontier completion readers.
      Completeness: Derive all required landing receipt bindings from R76 and corrupt each
      separately. Reject receipt export at the bare replica ref after source publication and kill
      before export acknowledgment; readers must show publication pending, not completed. Reconcile
      and publish the same receipt as the positive control. Build-only, review pass, and shipped
      file strings must fail the same consumer checks. Falsifier: Report completion immediately
      after local receipt commit while its replica export is rejected; publication/receipt-pending
      must detect unsupported completion in work_state.work_report.
    falsified_by: >
      Report completion immediately after local receipt commit while its replica export is rejected;
      publication/receipt-pending must detect unsupported completion in work_state.work_report.
required_evidence: [unit, integration]
rollback: >
  Close publication permits, retain remote observations and unresolved dispatches, and recover by
  original identity. Never undo a confirmed remote effect by deleting its local receipt.
---

## Intent

Publish the exact verified candidate once and establish completion only from remotely confirmed, replicated evidence.

## Context

Package C, W42 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A and B contracts govern this repair. This is a draft, not implementation or activation authority.

R23, R32-R33, R39, R49, R58, R74, and R76 govern this source-publication boundary. Incorrect retries or premature receipts could repeat effects or claim an unlanded revision complete. The declared risk floor is critical; required approval must bind the eventual change and proof and is not recorded by this declaration.

## Out of scope

Live remote activation and off-host operational durability qualification remain B/H obligations; source landing never activates new verifier or service code.

## Notes

D1/D2 block authoritative publication and acknowledgment semantics; D3/D4 remain prerequisites for the runner and clone inputs. control_landing is a proposed fleet/contracts receipt adapter over B effects and recovery, not a second publisher; resolve inventory and architecture mapping before ready. W41 supplies candidates, W39/W40 consume governing decisions and regression, and W43 supplies the trusted verification observation connected in W44. Preserve distinct implementation, evidence, reviewed, and candidate identities. The exact-title spelling follows the plan. A local bare remote proves the protocol, not host-loss durability. Each falsifier must change real execution, retain its diff and failing row, and be reverted; a second no-op receive attempt still violates lost-ack recovery.
