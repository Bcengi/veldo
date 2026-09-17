---
schema: veldo.spec/v1
id: VELDO-0019
title: Combined dependency graph and decision observation rules
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W4
plan_revision: 1
depends_on: [VELDO-0017, VELDO-0018]
placement: [contracts, fleet]
protected_paths: []
footprint:
  - ".veldo/plan.py"
  - "engine/.veldo/plan.py"
  - ".veldo/frontier.py"
  - "engine/.veldo/frontier.py"
  - ".veldo/decision.py"
  - "engine/.veldo/decision.py"
  - ".veldo/decision_review.py"
  - "engine/.veldo/decision_review.py"
  - ".veldo/tripwire.py"
  - "engine/.veldo/tripwire.py"
  - "engine/.veldo/*contract*.py"
  - "scripts/suites/*"
  - "packs/**/.veldo/*contract*.py"
  - "specs/VELDO-0019-combined-graph-contracts.md"
  - "specs/index.md"
  - "proof/VELDO-0019/*"
behavior_bearing: true
observability:
  logs: Contract refusals name the predicate, subject revision, and offending reference without including private keys or credentials.
  metrics: Proof reports required and exercised schema, transition, or boundary sets and coverage gaps; an unknown result never counts as zero failures.
  traces: Evidence joins the criterion, fixture or observation, input digests, and exact contract revision; runtime receipt production belongs to later packages.
  error_taxonomy: Distinguish missing input, malformed input, stale revision, unauthorized actor, forbidden transition, and unavailable evidence with named refusals.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Authorization requires an acyclic union of all execution prerequisite edge families,
      independent of the release membership forest. Set: Plan work, specification depends_on, project
      dependencies, decision prerequisites, and applicable release-execution ordering edges.
      Completeness: Declare the edge-family registry from R14 and require set equality with graph
      adapters; generate paths and cycles spanning each pair of families and a full-family cycle, plus
      separate valid release membership that introduces no implicit order. Falsifier: Validate each
      edge family separately and omit union-cycle detection; the combined-graph/cross-family-cycle row
      must fail.
    falsified_by: >
      Validate each edge family separately and omit union-cycle detection; the combined-graph/cross-
      family-cycle row must fail.
  - id: AC2
    text: >
      Claim: Dependencies resolve exact accepted artifact revisions or completion receipts and refuse
      unresolved targets by name. Set: Every dependency target state: resolved, missing, ambiguous,
      inaccessible, wrong revision, and unsupported receipt. Completeness: Generate target-state
      fixtures for each edge family from the resolver registry, require full matrix coverage, and
      preserve the reference and named refusal in the result. Falsifier: Treat a shipped status string
      as a completion receipt; the graph-resolution/status-only row must fail.
    falsified_by: >
      Treat a shipped status string as a completion receipt; the graph-resolution/status-only row must
      fail.
  - id: AC3
    text: >
      Claim: Rejected amendments that reveal prerequisites, and later withdrawals, remove affected
      readiness and publication permission without rewriting completed history. Set: Queued, running,
      and completed dependents reached by the reverse transitive closure of an amended, withdrawn, or
      invalidated prerequisite. Completeness: Compute expected closure with an independent small-graph
      oracle over each edge family and mixed chains; compare all impacted units, preserving completed
      receipts with appended impact requirements. Falsifier: Leave a running dependent publication-
      eligible after withdrawal; the graph-invalidation/running-publication row must fail.
    falsified_by: >
      Leave a running dependent publication-eligible after withdrawal; the graph-invalidation/running-
      publication row must fail.
  - id: AC4
    text: >
      Claim: Governing decision settlement and invalidation bind full subjects and observation
      freshness; unavailable evidence cannot silently authorize. Set: Decision bindings for projects,
      release executions, plans, backlog items, specs, and contracts, crossed with missing, stale,
      contradictory, invalid, and current observations and explicit advisory assumptions.
      Completeness: Derive binding and observation kinds from R71 contracts; require matrix coverage,
      exact framing digests, distinct-principal review predicates, and atomic eligibility effects in
      the pure transition result. Falsifier: Treat a stale measured governing assumption as current;
      the decision-observation/stale-measurement row must fail.
    falsified_by: >
      Treat a stale measured governing assumption as current; the decision-observation/stale-
      measurement row must fail.
required_evidence: [unit, integration]
rollback: >
  Retain the prior accepted contract and compatible reader. Refuse new project-layer activation
  until corrected contracts are accepted; preserve accepted history and refuse implicit schema
  downgrade. Revert only unactivated contract changes through the ordinary reviewed path.
---

## Intent

**Outcome.** Define one dependency decision over the combined graph, including current governing decisions and observations, before graph storage exists.

## Context

**Authority.** Package A of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R14, R39-R40, R56, R65, R70, and R71. The later decision-surface ruling in its provenance header takes precedence over retained tracker-only wording.

**Risk.** Incomplete dependency closure can publish work after its authority or prerequisite was withdrawn; the declared floor is high. No approval is asserted by human_approval: required; this draft must obtain its applicable approval and independent review before implementation or activation.

## Out of scope

**Boundary.** Graph persistence and transactional application are B; floor decision consumption is C; live decision reviews and tripwire production flows are E. This spec defines their shared pure contract.

## Notes

**Proof discipline.** This is one contract concern, with four criteria. The named check rows above are implementation obligations, not claims that those checks exist today. Proof must show its tested set equals the declared schema or policy universe and must drive each stated mutation, demonstrate the changed bytes, require the named row to fail, and restore the implementation. Removing a failure fixture cannot reduce the declared universe.

**Implementation boundary.** Define pure versioned data and named transition refusals in canonical engine/, synchronize shipped counterparts, and record every new asset in the distribution inventory. The draft footprint lists existing integration points and contract/test additions; refine it to exact new modules and synchronized counterparts before ready. Do not build the B-H runtime under this spec. Future runtime observations and receipts are required by their own specifications.
