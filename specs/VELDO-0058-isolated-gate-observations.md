---
schema: veldo.spec/v1
id: VELDO-0058
title: Gate-output isolation and exact tested-tree evidence
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W43
plan_revision: 3
depends_on: [VELDO-0050, VELDO-0056]
placement: [distribution, enforcement, fleet, loop, metrics]
protected_paths: [scripts/verify.sh, engine/scripts/verify.sh, .veldo/policy_check.py,
  engine/.veldo/policy_check.py]
footprint:
  - ".veldo/policy_check.py"
  - "engine/.veldo/policy_check.py"
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
  - "scripts/check_teeth_mutations.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0058-isolated-gate-observations.md"
  - "specs/index.md"
  - "proof/VELDO-0058/*"
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
      candidate commit/tree, command, verifier digests, required checks, actual results, and post-
      run equality. Set: Real installed verifier process, Git candidate objects/index/workspace,
      external observation files, and signed Evidence Service receipts in control.sqlite3.
      Completeness: Compare catalog required checks with captured terminal results, then omit
      terminal output and corrupt a captured check result or candidate identity. Use a separate
      process to modify tracked bytes, index entries, or add untracked output during verification.
      Every incomplete or changed subject refuses; evidence that changes candidate bytes requires a
      new commit and verification. Falsifier: Omit post-run tree equality and write a tracked
      candidate file after the final check but before receipt acceptance; gate-output/post-run-
      mutation must detect invalid acceptance.
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
      candidate policy_check.py from finalize after replacing it with a success stub; gate-
      output/installed-policy must detect publication past the real rejected approval.
    falsified_by: >
      Launch candidate policy_check.py from finalize after replacing it with a success stub; gate-
      output/installed-policy must detect publication past the real rejected approval.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Gate-output isolation and exact tested-tree evidence. Deliver the normal function needed by the running factory journey.

## Context

W43 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## What the reviewer judges

- Normal use: the canonical gate runs against a landing candidate and writes its stamp, its gate
  events and its review-event reconciliation to a trusted sink outside the candidate, never into the
  candidate's tracked tree. GitLandOps.gate and LiveLoop.gate each produce an external trusted
  observation that binds the exact candidate commit and the verification that ran, with the tree
  unchanged after the run. The enforcement and policy process that judges the candidate is the
  installed one, not code from the candidate, and a valid candidate verifies without its own receipt
  being added to its tree. The owner approved changing scripts/verify.sh for this (Telegram 29068
  asked, 29069 "Yes verify", 2026-09-24).
- Threat model: candidate code that writes its own stamp or events into its tree, replaces the
  installed enforcement or policy process, changes the tree during the run, or passes without an
  observation bound to its exact commit; a missing or partial gate result read as success. The
  owner's account, the installed engine and Git are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); gate process
  kill qualification (Release 2, see History); a hostile gate process reaching the caller through the
  same account (the same-account class filed by VELDO-0040 and VELDO-0067); files planted in the
  installed directory.

## Notes

All existing trusted gate-output, installed policy and post-run equality obligations remain.
Only process-kill qualification moves to Release 2. Gate stamps, gate events and review-event
reconciliation must all write to the trusted external sink; the final receipt cannot be
required inside its own candidate.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 1: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. No whole criterion
removed. Old AC2 gate process-kill qualification moved to Release 2. Missing results still
refuse; external observations, installed enforcement and post-run tree equality remain. The
criteria, declared evidence universe, Context and Notes above now carry only the retained
function. No specification status or historical proof was changed.

2026-09-24, build: scripts/check_teeth_mutations.py joins the footprint, before any mutation is
registered, because each criterion's falsifier is a registered mutation of finding 58 there, and the
AC1 falsifier mutates scripts/verify.sh, which the driver could not reach: it mutated only .veldo/
modules. The driver gains one optional case field naming the directory a module lives in, and the
cases of every other finding are unchanged.

2026-09-24, build (branch build-veldo-0058): scripts/verify.sh gains candidate mode (owner approval
proof/VELDO-0058/approval-dmitry.json, Telegram 29068/29069), .veldo/control_verification.py runs the
trusted installation's verifier and policy against a candidate and accepts its external observation,
and GitLandOps.gate/finalize and LiveLoop.gate use it. The ordinary checkout gate and the landing step's
inputs are unchanged. Suite 69 carries the four rows; proof/VELDO-0058/README.md has the evidence. No
status was changed.

2026-09-24, review fix (AC3, blocking): the installed policy_check.py read the protected list from the
candidate's own .veldo/policy.yaml, so a candidate that emptied protected_paths landed a protected
change with no approval. The policy source is now an explicit input separate from the subject root:
policy_check.py reads policy.yaml through its POLICY path (unset, it is the subject root's, as before),
and control_verification sets it to the installation's policy.yaml, refusing as missing_authority when
that file is absent or inside the candidate. .veldo/policy_check.py and engine/.veldo/policy_check.py
join the footprint and protected_paths; their change is its own commit, for the owner's approval.
Suite 69 gains gate-output/installed-policy-list. No status was changed.

2026-09-24, second review fix (AC3, blocking): the installed policy_check.py computed the push range
from the candidate workspace's own refs/remotes/origin/HEAD and origin/main, so candidate code running
in the gate could move origin/main to HEAD, empty the range and land a protected change with no
approval. The range base is now an explicit input like the policy source: policy_check.py reads every
range as BASE..HEAD when its BASE is set (unset, the refs decide, as before), and control_verification
run_policy takes the base and sets it; GitLandOps.finalize passes its own recorded watermark, refused as
missing_authority unless a full 40-hex commit that exists and is an ancestor of the candidate. The
policy_check.py change is its own commit, for the owner's approval. As defense in depth the candidate
state that the gate and acceptance compare now binds every ref and HEAD's symbolic target. Suite 69
gains gate-output/range-base-from-lander and gate-output/refs-bound. No status was changed.
