---
schema: veldo.spec/v1
id: WARP-0410
title: Release VELDO 2.0 and descope the server-side control-plane track
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: standalone
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: PLAN-0004 work items X8 (WARP-0408) and X9 (WARP-0409), feature F2, and
      outcome O2 are removed from the plan with no orphaned references; the plan
      validator passes and the remaining traceability chain is intact (outcomes
      O1/O3/O4 map to features F1/F3/F4 map to work items X1 through X7).
  - id: AC2
    text: PLAN-0004 is at revision 4 with a Revisions entry that records the
      founder's decision to descope the control-plane and identity track (F2) as
      over-architecture for this problem class, and the Intent no longer claims a
      server-side control plane as delivered scope.
  - id: AC3
    text: The plan release check reports PLAN-0004 releasable with all remaining
      work shipped (7 of the original 9 items), and the plan status is released.
  - id: AC4
    text: The plugin version is bumped to 3.0.0 for the milestone, and the method
      document is left unchanged with the stated rationale that the generic
      methodology did not change (VELDO 2.0 is tooling that makes the same loop
      executable).
  - id: AC5
    text: The full gate is GREEN (selftest passes, contracts pass) and the
      genericity and dash sweeps pass on the changed plan and spec.
required_evidence: [operational]
rollback: git revert the release commit and this evidence; reopen PLAN-0004 (status
  in_progress, restore X8/X9/F2/O2) if the control-plane track is ever wanted.
---

## Intent

Close out VELDO 2.0. The founder descoped the server-side control-plane and
identity track (X8, X9) as over-architecture for a fast small-team SDLC, so the
plannable buildout is complete at the executor, observability/ops, and adoption
tracks (X1 through X7). This change makes PLAN-0004 reflect that reality and marks
the milestone released.

## Context

X8 (SSH-signed identity gateway) and X9 (GitHub-native control plane) were never
built; their specs do not exist, so removing the work items, feature F2, and
outcome O2 leaves no orphaned specs to reconcile. The agent-recorded-with-
provenance approval model stands and is honestly labeled in capabilities. This is
a plan revision plus release plus version bump, reviewed independently like any
change per PLAN-0004 constraint C1.

## Notes

The change under review is the release commit (plan revision 4, status released,
plugin 3.0.0). The evidence is operational: the plan validator, the plan release
check, and the full gate all pass, and the descope leaves the plan's reference
graph consistent.
