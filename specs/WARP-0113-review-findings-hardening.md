---
schema: veldo.spec/v1
id: WARP-0113
title: Harden enforcement per the WARP-0100 independent review findings
status: shipped
risk: high    # floored: changes scripts/verify.sh, a protected path
owner: dmitry
human_approval: required
lane: standalone
protected_paths: [scripts/verify.sh, .veldo/policy.yaml]
acceptance_criteria:
  - id: AC1
    text: policy_check.py evaluates verdicts of BOTH canonical findings shapes
      (dict blocking/non_blocking; list of severity+text) without raising, and
      anything outside both shapes counts as blocking - fail closed, unit-tested.
  - id: AC2
    text: validate.py pins the verdict findings contract mechanically - both
      canonical shapes accepted, string findings, unknown severities, unknown
      dict keys, and non-list blocking all red (selftest).
  - id: AC3
    text: No compiled bytecode is tracked; .gitignore prevents re-tracking; a
      gate run no longer dirties the tree with .pyc files.
  - id: AC4
    text: The hygiene sweeps cover every tracked text file (pdf/ and images
      excluded) so the check matches its stated rule, and the docs check is
      hermetically self-tested via a path override - a planted em-dash and
      company reference turn it red inside the unit suite, not just in a
      one-off demonstration.
  - id: AC5
    text: The generated check is snapshot-based - red if and only if
      regeneration changes specs/index.md, independent of other uncommitted
      work (negative demonstration - a hand-edited index is red pre-commit,
      regeneration is green pre-commit).
  - id: AC6
    text: The build and dependency_audit na reasons truthfully name the pdf
      pipeline and its imports.
  - id: AC7
    text: The repository policy encodes the operator's review-independence
      rule - every tier reviews on a different Claude model (L2, Opus family,
      two independent verdicts at critical), cross-vendor only on explicit
      founder instruction - replacing the generic ladder's L3/L4 tiers for
      this repository.
  - id: AC8
    text: The generic documents (setup guide independence ladder + policy
      example + control-plane principle, runbook protected-path walkthrough)
      present cross-vendor review as an optional, recorded budget decision
      that improves quality where the cost is justified - never a requirement
      for the method to work; L2 (different model, same vendor) is the stated
      working default at every tier above low.
  - id: AC9
    text: The five WARP-0101 reviewer notes are closed - duplicate keys and tab
      indentation are hard parse errors (the demonstrated green-cycle exploit
      via duplicated depends_on now fails), every work item must reference a
      feature and every feature an outcome, work spec ids are format-checked
      without crashing the DAG walk, and the plan index names each open
      decision with what it blocks regardless of dependency state.
  - id: AC10
    text: The WARP-0100 L2 review's two blocking findings are closed - the
      approval decision vocabulary is pinned (a near-miss value like
      'approve' is loud at validation, never silently inert) - and its
      high-risk note is acted on - policy_check.py (instance and template)
      joins the protected paths, so the enforcer of protection is itself
      protected.
required_evidence: [unit, operational]
rollback: git revert; enforcement-behavior changes are strictly widening
  (accept both verdict shapes) or strictly tightening (findings contract,
  wider sweeps), and the 26 pre-existing selftest cases pass unmodified.
---

## Intent

The WARP-0100 independent review returned seven non-blocking findings and
the WARP-0101 review five more; this change closes the eleven that are code (the seventh, CLAUDE.md describing plan
machinery, was closed by WARP-0101 landing). Chief among them: the shipped
policy_check crashed with a traceback on a verdict whose findings were the
list shape that reviewers naturally produce - it failed closed, but by
accident, with no reason attached. Enforcement that crashes is enforcement
nobody trusts.

## Context

Standalone lane: review-found defects, not plan work. The findings shapes
observed in the wild are both legitimate (the pilot repository uses the dict
shape, this repository's reviews use the list shape), so the contract admits
both and the enforcement normalizes; everything else fails closed loudly.

## Out of scope

The remaining absent capabilities (verdict-proof digest binding, approval
self-separation) stay in PLAN-0001 W9; this change fixes defects, it does
not pull plan work out of order.
