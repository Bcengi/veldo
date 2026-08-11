---
schema: veldo.spec/v1
id: WARP-0708
title: Release VELDO Fleet v1 (PLAN-0007 at 7/7) - plugin 3.2.0
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: standalone
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: All seven PLAN-0007 work items (Y1 through Y7, WARP-0701 through WARP-0707) are status
      shipped with a proof and a passing verdict, the plan release check reports PLAN-0007
      releasable, and the plan status is set to released.
  - id: AC2
    text: The plugin version is bumped to 3.2.0 for the VELDO Fleet v1 milestone, and the plan's
      release version field reflects plugin 3.2.0. The method document is unchanged - the fleet
      is tooling that runs the same VELDO loop in parallel (claim, build, review, land), not a
      change to the generic method.
  - id: AC3
    text: The full gate is GREEN (selftest passes, contracts pass) and the genericity and dash
      sweeps pass on the changed plan and this spec; no protected path is touched.
required_evidence: [operational]
rollback: git revert the release commit and this evidence; set PLAN-0007 back to in_progress if
  the release must be withdrawn (the work items stay shipped).
---

## Intent

Close out the VELDO Fleet: mark PLAN-0007 released now that all seven work items are shipped and
independently reviewed, and cut the plugin 3.2.0 milestone.

## Context

Y1 (claim ledger) through Y7 (fleet launcher) each shipped through the full VELDO loop with an
independent review, and the dogfood earned its keep - the reviews caught and closed a
foundational mutual-exclusion race in the claim primitive (fixed as WARP-0710) before the
lander could ship on top of it. The fleet is elastic pull-based workers that self-divide the
whole repo's ready work through an atomic capability-matched claim, a global claimable frontier,
a worker loop, a serialized merge-based lander, shared-read-once environment provisioning, a
measure-not-query token governor, and an in-session launcher - no central coordinator, no
detached process. This is a plan release plus a version bump, reviewed independently like any
change per PLAN-0007 constraint C1.

## Notes

The version bump touches plugin.json and the plan flip touches plans/, so this release commit
is not evidence-only and carries its own independent review and verdict. WARP-0710 (the
claim-ledger hardening found while building Y4) shipped as a standalone spec, not a PLAN-0007
work item, so it does not gate the plan release; it is recorded in its own proof.
