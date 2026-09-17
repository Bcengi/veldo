---
schema: veldo.spec/v1
id: VELDO-0016
title: Decision records and effective policy amendments
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W1
plan_revision: 1
depends_on: []
placement: [contracts, enforcement]
protected_paths: [.veldo/policy.yaml]
footprint:
  - ".veldo/architecture.yaml"
  - ".veldo/arch.py"
  - "engine/.veldo/arch.py"
  - ".veldo/validate_checks.py"
  - "engine/.veldo/validate_checks.py"
  - ".veldo/capabilities.yaml"
  - ".veldo/policy.yaml"
  - "scripts/suites/06_capabilities_manifest_honesty_veldo.py"
  - "engine/.veldo/*contract*.py"
  - "scripts/suites/*"
  - "packs/**/.veldo/*contract*.py"
  - "specs/VELDO-0016-policy-boundaries.md"
  - "specs/index.md"
  - "proof/VELDO-0016/*"
behavior_bearing: true
observability:
  logs: Policy-loading and activation diagnostics identify the boundary, decision ID/version, architecture revision, and missing qualification obligation.
  metrics: Qualification reports count covered decision-to-policy boundaries and registered versus missing R43/R44 obligations for each host profile.
  traces: Activation evidence joins accepted decision digests, installed policy revision, loader result, capability profile, and lifecycle qualification references.
  error_taxonomy: Distinguish draft or stale decision, absent required policy, unreadable or invalid policy, unqualified containment or resource limits, and review mistaken for authority.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Only accepted version-bound decisions can authorize effective project policy changes.
      Set: Repository placement, orchestrator process ownership, operational persistence, replaceable
      LangGraph execution, and review/completion policy decisions named by R03, including all four
      open PLAN-0019 choices. Completeness: Derive a decision-to-policy matrix from those named
      boundaries and compare both directions with the activation registry; exercise missing, draft,
      superseded, stale, and accepted records for each boundary. Falsifier: Accept a draft process
      decision as activation authority; the policy-activation/draft row must fail.
    falsified_by: >
      Accept a draft process decision as activation authority; the policy-activation/draft row must
      fail.
  - id: AC2
    text: >
      Claim: The governed runner replaces no_detached_processes and agent-mediated launch with
      explicit R43/R44 obligations, while activation requires the accepted architecture revision and
      qualification. Set: Architecture contract, capability declarations, arch.py loading, and the
      lexical fleet assertions in scripts/suites/06_capabilities_manifest_honesty_veldo.py;
      containment, hard per-group memory, cumulative descendant CPU-time and writable-storage limits,
      exhaustion stop and slot quarantine, authority and unrelated-project survival, exit identity,
      control-channel fencing, heartbeat, stop escalation, and retirement obligations.
      Completeness: Compare the replacement obligation registry against every R43/R44
      clause and every affected lexical assertion; require a test registration for each obligation
      before the new profile can be eligible; missing or unenforceable resource limits and absent
      exhaustion qualification must refuse activation. Real lifecycle qualification is supplied by B and D, not
      claimed by these contract tests. Falsifier: Remove empty-containment proof from the replacement
      retirement predicate; the policy-activation/retirement-obligation row must fail.
    falsified_by: >
      Remove empty-containment proof from the replacement retirement predicate; the policy-
      activation/retirement-obligation row must fail.
  - id: AC3
    text: >
      Claim: Architecture loading distinguishes absent optional, valid, and invalid present contracts
      and refuses absent required contracts. Set: All public architecture loading and eligibility
      adapters used by this policy contract, crossed with absent, unreadable, malformed, invalid, and
      valid contract inputs. Completeness: Enumerate adapters from the policy loading registry and
      require fixture coverage of the full product of adapters and states, with a separate required-
      contract flag; assert canonical and synced entry points use the same result type. Falsifier: Map
      an unreadable present contract to optional absence; the policy-loading/unreadable row must fail.
    falsified_by: >
      Map an unreadable present contract to optional absence; the policy-loading/unreadable row must
      fail.
  - id: AC4
    text: >
      Claim: The policy contract preserves stdlib enforcement, replaceable execution, separate review
      meaning, and receipted activation with rollback. Set: R21 checkpoint authority limits, R35
      execution dependency isolation, R46 review versus authorization, R50 installed verifier
      independence, and R53 exclusive store/runner/lander/evidence responsibilities. Completeness: A
      clause-to-predicate table must cover each boundary and reject a seeded violation per predicate;
      import checks run with the execution environment unavailable and review acceptance requires
      independent actor and blocking-finding disposition. Falsifier: Treat a passing reviewer
      assertion as landing authorization; the policy-boundaries/review-is-not-authority row must fail.
    falsified_by: >
      Treat a passing reviewer assertion as landing authorization; the policy-boundaries/review-is-
      not-authority row must fail.
required_evidence: [unit, integration]
rollback: >
  Retain the prior accepted contract and compatible reader. Refuse new project-layer activation
  until corrected contracts are accepted; preserve accepted history and refuse implicit schema
  downgrade. Revert only unactivated contract changes through the ordinary reviewed path.
---

## Intent

**Outcome.** Ratify and express the project-layer policy boundary so future implementations cannot mistake a draft decision or source landing for activated authority.

## Context

**Authority.** Package A of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R03, R21, R34-R35, R43-R44, R46, R50, R53, R56, and R75. The later decision-surface ruling in its provenance header takes precedence over retained tracker-only wording.

**Risk.** Wrong policy activation can grant autonomous process and publication authority; this is a critical boundary even though the present artifact is a draft. No approval is asserted by human_approval: required; this draft must obtain its applicable approval and independent review before implementation or activation.

## Out of scope

**Boundary.** Provider runtime implementation, live service installation, approval of the four open decisions, and any channel activation belong to later authorized work.

## Notes

The decision-to-policy matrix must include every open architectural choice; recording these drafts supplies no activation authority. Contract fixtures establish loader and replacement-obligation refusals, while B and D supply the real lifecycle and resource-exhaustion observations. Before ready, resolve the proposed architecture revision and exact loader, capability, and synchronized file changes.
