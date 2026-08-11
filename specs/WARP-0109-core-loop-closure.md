---
schema: veldo.spec/v1
id: WARP-0109
title: Core-loop closure - boundary, revisions, digest binding, self-separation (W9)
status: shipped
risk: high
owner: dmitry
lane: planned
plan: PLAN-0001
work: W9
plan_revision: 3
human_approval: required
protected_paths: [.veldo/policy_check.py]
acceptance_criteria:
  - id: AC1
    text: Ready-spec boundary - a spec that carries a proof manifest while
      still in draft status blocks the push; a shipped/ready spec does not.
      Unit-tested.
  - id: AC2
    text: Spec-revision invalidation - a proof produced against an older spec
      revision than the spec now declares is stale and blocks the push, and a
      non-integer spec revision fails closed. Unit-tested.
  - id: AC3
    text: Verdict-proof digest binding - a verdict may carry proof_digest; when
      present it must equal the current proof manifest's digest, so a verdict
      cannot be reused for a proof it did not review. The digest function is
      identical in policy_check and validate (drift-guarded). Unit-tested.
  - id: AC4
    text: Approval self-separation and path-scoped authorization - an approval
      whose approver equals the proof producer is rejected, and each touched
      protected path requires an approval whose scope.paths covers it (empty
      scope.paths authorizes nothing). Unit-tested.
required_evidence: [unit, operational]
rollback: git revert; every check is strictly tightening and fails closed;
  optional fields (spec_revision, proof_digest) are only enforced when
  present, so prior proofs and verdicts remain valid; the 104 prior selftest
  cases pass within the 120.
---

## Intent

The core loop's remaining honesty gaps close. Until now a draft could carry a
proof, a proof could outlive the spec revision it was built against, a
passing verdict was not bound to the exact proof it reviewed, an approver
could in principle approve their own work, and a single in-range approval
authorized every protected path. Each is now mechanical and fails closed, so
the capability manifest's absent list for the core loop shrinks to the items
that genuinely remain platform work.

## Context

W9 of PLAN-0001, depends on W8 (events, shipped). High risk: it changes the
protected enforcer .veldo/policy_check.py, so it carries a recorded human
approval scoped to that path. The digest binding is the proportionate subset
of the setup's fuller signed-contract vision; full content-addressed contract
forms remain honestly absent.

## Out of scope

An auth gateway that injects a verified human identity (fresh attestation
beyond agent-recorded provenance) - a later platform capability. Full
signed/content-addressed contract schemas. Server-side enforcement (W10).
