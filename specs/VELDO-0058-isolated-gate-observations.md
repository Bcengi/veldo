---
schema: veldo.spec/v1
id: VELDO-0058
title: Gate-output isolation and exact tested-tree evidence
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W43
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0056]
placement: [distribution, enforcement, fleet, loop, metrics]
protected_paths: [scripts/verify.sh, engine/scripts/verify.sh]
footprint:
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/lander.py"
  - ".veldo/lander.py"
  - "packs/*/.veldo/lander.py"
  - "engine/.veldo/executor.py"
  - ".veldo/executor.py"
  - "packs/*/.veldo/executor.py"
  - "engine/.veldo/events.py"
  - ".veldo/events.py"
  - "packs/*/.veldo/events.py"
  - "engine/.veldo/control_verification*.py"
  - ".veldo/control_verification*.py"
  - "packs/*/.veldo/control_verification*.py"
  - "scripts/verify.sh"
  - "engine/scripts/verify.sh"
  - "packs/*/scripts/verify.sh"
  - "scripts/suites/*_veldo_0058_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0058-isolated-gate-observations.md"
  - "specs/index.md"
  - "proof/VELDO-0058/*"
behavior_bearing: true
observability:
  logs: >
    Verification records name trusted executable digests, candidate commit/tree, invocation ID,
    observation destination, catalog results, and post-run equality.
  metrics: >
    Count candidate mutations, observation-write failures, missing terminal records, redirected
    event writes, and verifier substitutions.
  traces: >
    Trace the installed gate launch through captured process results and external signed observation
    to the exact candidate consumed by publication.
  error_taxonomy: >
    Distinguish unsafe destination, unavailable sink, interrupted gate, missing required check,
    candidate mutation, and untrusted executable.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: scripts/verify.sh redirects its stamp, gate events, and review-event reconciliation
      output to a trusted external destination in candidate mode, leaving the candidate unchanged.
      Set: The last_verify writer, gate event append, and events.reconcile_verdicts invoked by the
      real gate through GitLandOps.gate and LiveLoop.gate; canonical engine and installed gate
      copies. Completeness: Enumerate every gate-induced write, including child commands and
      reconciliation. Run green and red gates over committed candidates with actual proof artifacts.
      Test missing/unwritable destinations and symlink redirection back into the candidate; compare
      tracked and untracked bytes plus index before and after. Sink failure refuses trusted success
      without fallback to candidate files. Preserve documented ordinary-checkout behavior.
      Falsifier: Leave the review-event reconciliation path writing candidate .veldo/events.jsonl
      while redirecting only the final stamp; gate-output/review-write must detect the dirty tested
      tree.
    falsified_by: >
      Leave the review-event reconciliation path writing candidate .veldo/events.jsonl while
      redirecting only the final stamp; gate-output/review-write must detect the dirty tested tree.
  - id: AC2
    text: >
      Claim: GitLandOps.gate and LiveLoop.gate produce an external trusted observation binding exact
      candidate commit/tree, command, verifier digests, required checks, actual results, and
      post-run equality. Set: Real installed verifier process, Git candidate
      objects/index/workspace, external observation files, and signed Evidence Service receipts in
      control.sqlite3. Completeness: Compare catalog required checks with captured terminal results,
      then SIGKILL the gate before terminal output and corrupt a captured check result or candidate
      identity. Use a separate process to modify tracked bytes, index entries, or add untracked
      output during verification. Every incomplete or changed subject refuses; evidence that changes
      candidate bytes requires a new commit and verification. Falsifier: Omit post-run tree equality
      and write a tracked candidate file after the final check but before receipt acceptance;
      gate-output/post-run-mutation must detect invalid acceptance.
    falsified_by: >
      Omit post-run tree equality and write a tracked candidate file after the final check but
      before receipt acceptance; gate-output/post-run-mutation must detect invalid acceptance.
  - id: AC3
    text: >
      Claim: Candidate code cannot replace the installed enforcement or policy process that
      authorizes publication, and its final gate receipt is never required inside its own tested
      commit. Set: GitLandOps.gate/finalize and Executor LiveLoop.gate using trusted versioned
      verifier/policy installation, controlled candidate tests, real Git, real signatures, and an
      external receipt store. Completeness: Replace candidate scripts/verify.sh and
      .veldo/policy_check.py with success stubs while the trusted installation remains fixed; run a
      real red check and rejected fixture approval and require unchanged trunk. Move the external
      observation under the candidate or alter its digest before acceptance and refuse. Then prove a
      valid candidate can be verified without adding the receipt to its own tree. Falsifier: Launch
      candidate policy_check.py from finalize after replacing it with a success stub;
      gate-output/installed-policy must detect publication past the real rejected approval.
    falsified_by: >
      Launch candidate policy_check.py from finalize after replacing it with a success stub;
      gate-output/installed-policy must detect publication past the real rejected approval.
required_evidence: [unit, integration]
rollback: >
  Disable candidate publication if external observations cannot be trusted, retain all tested-tree
  evidence, and restore the prior installed verifier through separately authorized activation.
---

## Intent

Keep final gate observations outside the candidate and bind publication to the exact tree actually tested by trusted enforcement.

## Context

Package C, W43 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A and B contracts govern this repair. This is a draft, not implementation or activation authority.

R47, R50-R51, and R76 require trusted observations without self-certification. This footprint edits protected gate scripts and determines whether candidate bytes are authorized to publish. The declared risk floor is critical; required approval must bind the eventual change and proof and is not recorded by this declaration.

## Out of scope

Ordinary gate catalog obligations are not weakened; service upgrade activation and live channel decisions remain separate.

## Notes

D1/D2 block accepted verification receipts and their publication; D3 blocks controlled execution activation and D4 the isolated-clone path. Both scripts/verify.sh and engine/scripts/verify.sh are protected, with corresponding pack copies in the footprint. The current home gate writes .veldo/last_verify and .veldo/events.jsonl after running checks; its review stage also appends. Inventory all three paths and any newly introduced writer. control_verification is a proposed enforcement/loop adapter requiring architecture and distribution registration before ready. Trusted policy is consumed from its installed location; this spec does not amend policy_check.py. Retain actual argv/executable digests, mutation diffs, and failing rows. An environment variable alone is not a trusted sink selection, and no new receipt may require embedding itself in the commit it certifies.
