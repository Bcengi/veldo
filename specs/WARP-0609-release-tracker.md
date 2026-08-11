---
schema: veldo.spec/v1
id: WARP-0609
title: Release VELDO tracker integration v1 (PLAN-0006 at 8/8) - plugin 3.3.0
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: standalone
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: All eight PLAN-0006 work items (W1 through W8, WARP-0601 through WARP-0608) are status
      shipped with a proof and a passing verdict, the plan release check reports PLAN-0006
      releasable, and the plan status is set to released.
  - id: AC2
    text: The plugin version is bumped to 3.3.0 for the VELDO tracker integration v1 milestone, and
      the plan's release version field reflects plugin 3.3.0. The method document is unchanged - the
      tracker integration is tooling behind a vendor-neutral seam (routing, intake, a one-way mirror)
      that runs alongside the same VELDO loop, not a change to the generic method.
  - id: AC3
    text: The full gate is GREEN (selftest passes, contracts pass) and the genericity and dash
      sweeps pass on the changed plan and this spec; no protected path is touched.
required_evidence: [operational]
rollback: git revert the release commit and this evidence; set PLAN-0006 back to in_progress if the
  release must be withdrawn (the work items stay shipped).
---

## Intent

PLAN-0006 (tracker integration) is complete: routing (W1) and its enforcement (W2), the
provider-agnostic seam and fake tracker (W3), Jira and Confluence intake (W4, W7), the one-way spec
and epic mirrors (W5, W6), and the end-to-end conformance (W8) are all shipped with independent
verdicts. This releases it as VELDO tracker integration v1 and bumps the plugin to 3.3.0.

## Context

A standalone release act, the same shape as WARP-0708 (the fleet release). It marks PLAN-0006
released, sets its release version to plugin 3.3.0, and bumps packs/claude/.claude-plugin/plugin.json. The
plan's release contract requires all work shipped and the full regression defined (RJ1 and RJ2, owned
by W8); both hold. No product or method change ships here - the integration is generic, per-org
config-wired, and proven offline over the fake tracker, with the live Jira and Confluence adapters
reference-wired.

## Notes

The version bump is a minor (3.2.0 to 3.3.0): the tracker integration extends the plugin with new
capabilities behind a seam and adds no breaking change. The method document is untouched. The live
adapters remain reference-wired (a scoped token from a secrets store per org); the fake-tracker path
is what the gate runs. Rollback is a git revert plus setting the plan back to in_progress; the shipped
work items and their proofs are unaffected.
