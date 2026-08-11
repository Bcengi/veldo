---
schema: veldo.spec/v1
id: WARP-0110
title: Server-side gate wiring - CI check template + branch-protection recipe (W10)
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0001
work: W10
plan_revision: 3
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A runnable CI workflow template ships at
      engine/.github/workflows/veldo-gate.yml. It is valid YAML, it
      runs the SAME gate a developer runs locally by invoking the real
      commands (./scripts/verify.sh, then python3 .veldo/policy_check.py) rather
      than reimplementing any check, and it checks out full history so the
      guard's commit-range logic works server-side. Verified operationally by
      parsing the YAML and by running that exact command sequence.
  - id: AC2
    text: The template is generic and portable - it carries no company or
      product reference (only Bcengi/veldo is permitted as the distribution
      coordinate, and it appears nowhere in the workflow), and it passes the
      repository's docs-hygiene, secret, and lint gates unchanged.
  - id: AC3
    text: A proportionate docs section (docs/plugin.md) explains how to enforce
      the gate server-side - the CI check, the required-status-check /
      branch-protection recipe that makes a policy_check failure unmergeable,
      and how this mirrors the local pre-push guard. The plugin contents
      reference lists the new template. Docs-hygiene stays green.
  - id: AC4
    text: .veldo/capabilities.yaml (template and instance, kept identical)
      states the honest status - the CI template as a shipped reference
      artifact and branch protection as a human-performed procedure - with no
      claim that the repository self-enforces server-side. The prior
      server_side_enforcement=absent entry no longer claims absence.
required_evidence: [unit, operational]
rollback: git revert; W10 adds a new template file, a docs section, a plugin
  version bump, and honesty edits to capabilities.yaml - no protected gate
  script or enforcer is touched, so reverting removes the artifact and the
  guidance with no effect on any running gate; the 121 prior selftest cases
  are unchanged.
---

## Intent

The gate a developer runs locally (verify.sh green, selftest inside it,
policy_check exit 0, enforced by the pre-push guard) must be runnable
server-side, where a local hook cannot be edited away. W10 ships the artifact
that makes that possible - a CI workflow template that runs the identical
commands - and documents the branch-protection recipe that turns it into a
required check, so a change that fails the gate cannot merge. It does not add
a server-side enforcer of its own; it makes the existing gate reachable by CI
and tells the repository owner how to require it.

## Context

W10 of PLAN-0001 (feature F6), depends on W9 (core-loop closure, shipped).
The plan scopes this to guidance plus a shipped template (non-goal NG2 keeps
the server-side merge queue deferred). The right architecture is one
canonical gate command, identical locally and in CI: the workflow invokes
./scripts/verify.sh (whose unit slot IS scripts/selftest.py) and then
.veldo/policy_check.py, never a reimplementation, so there is no divergence
between what the agent ran and what CI runs. Full server-side enforcement in
the home repository itself is a host procedure the owner applies, not
something the plugin can self-configure, and the capability manifest says so.

## Out of scope

A server-side merge queue that re-proves the merged result (control-plane,
deferred per NG2). Actually wiring the home repository's own GitHub branch
protection (a host setting only the owner applies). Any change to the
protected gate scripts or enforcers (verify.sh, veldo-guard.sh, policy.yaml,
policy_check.py, and their template copies) - W10 is new artifacts and docs.

## Notes

The template lives under engine/.github/workflows/ so /veldo:init
drops it into an adopting repository at .github/workflows/veldo-gate.yml; it is
not a workflow of the home repository (GitHub only reads workflows from the
repository-root .github/workflows). The honest status is reference (the
artifact ships) plus procedure (branch protection is applied by a human),
never mechanical, because the repository cannot self-enforce a host setting.
