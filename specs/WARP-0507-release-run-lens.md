---
schema: veldo.spec/v1
id: WARP-0507
title: Release VELDO Run Lens v1 (PLAN-0005 at 6/6)
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: standalone
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: All six PLAN-0005 work items (R1 through R6, WARP-0501 through WARP-0506)
      are status shipped with a proof and a passing verdict, the plan release check
      reports PLAN-0005 releasable, and the plan status is set to released.
  - id: AC2
    text: The plugin version is bumped to 3.1.0 for the Run Lens v1 milestone; the
      method document is unchanged (the Run Lens is tooling that observes the same
      loop, not a change to the generic method), and the release version field
      reflects plugin 3.1.0.
  - id: AC3
    text: The full gate is GREEN (selftest passes, contracts pass) and the genericity
      and dash sweeps pass on the changed plan and this spec; no protected path is
      touched.
required_evidence: [operational]
rollback: git revert the release commit and this evidence; set PLAN-0005 back to
  in_progress if the release must be withdrawn (the work items stay shipped).
---

## Intent

Close out the VELDO Run Lens: mark PLAN-0005 released now that all six work items are
shipped and independently reviewed, and cut the plugin 3.1.0 milestone.

## Context

R1 (run registry) through R6 (chat-surface CLI) each shipped through the full VELDO
loop with an independent review. The Run Lens is git-native and proportionate: a
per-run folder outside git history, the run.* event vocabulary, an optional
default-off executor observer, a read-only status reader and local server, a
cooperative answer/steer/abort inbox, and a chat-surface CLI. This is a plan release
plus a version bump, reviewed independently like any change per PLAN-0005 constraint
C1.

## Notes

The evidence is operational: the plan release check reports releasable, the plan
status is released, the plugin is at 3.1.0, and the full gate is green. The method
document is intentionally unchanged - the Run Lens adds tooling that observes and
steers the existing loop, it does not change the generic methodology.
