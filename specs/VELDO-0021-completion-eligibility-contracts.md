---
schema: veldo.spec/v1
id: VELDO-0021
title: Completion and executable eligibility predicates
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W6
plan_revision: 1
depends_on: [VELDO-0018, VELDO-0019, VELDO-0020]
placement: [contracts, fleet, loop, metrics]
protected_paths: []
footprint:
  - ".veldo/validate.py"
  - "engine/.veldo/validate.py"
  - ".veldo/validate_checks.py"
  - "engine/.veldo/validate_checks.py"
  - ".veldo/work.py"
  - "engine/.veldo/work.py"
  - ".veldo/work_state.py"
  - "engine/.veldo/work_state.py"
  - ".veldo/frontier.py"
  - "engine/.veldo/frontier.py"
  - ".veldo/plan.py"
  - "engine/.veldo/plan.py"
  - ".veldo/executor.py"
  - "engine/.veldo/executor.py"
  - ".veldo/lander.py"
  - "engine/.veldo/lander.py"
  - ".veldo/events.py"
  - "engine/.veldo/events.py"
  - "engine/.veldo/*contract*.py"
  - "scripts/suites/*"
  - "packs/**/.veldo/*contract*.py"
  - "specs/VELDO-0021-completion-eligibility-contracts.md"
  - "specs/index.md"
  - "proof/VELDO-0021/*"
behavior_bearing: true
observability:
  logs: Contract refusals name the predicate, subject revision, and offending reference without including private keys or credentials.
  metrics: Proof reports required and exercised schema, transition, or boundary sets and coverage gaps; an unknown result never counts as zero failures.
  traces: Evidence joins the criterion, fixture or observation, input digests, and exact contract revision; runtime receipt production belongs to later packages.
  error_taxonomy: Distinguish missing input, malformed input, stale revision, unauthorized actor, forbidden transition, and unavailable evidence with named refusals.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Attempt finished, artifact accepted, revision landed, and objective satisfied are
      distinct revision-bound facts with their own evidence. Set: Runner exit and accounting, station
      artifact acceptance, remote-confirmed and replicated landing with spec.shipped, and signed
      objective assessment. Completeness: Derive fact kinds and required receipt fields from R70/R76,
      require set equality with the predicate registry, and test every pair for non-implication plus
      missing, wrong-subject, and superseded receipts. Falsifier: Infer revision landed from attempt
      finished; the completion/build-only row must fail.
    falsified_by: >
      Infer revision landed from attempt finished; the completion/build-only row must fail.
  - id: AC2
    text: >
      Claim: Every execution entry uses a complete authoritative snapshot and refuses stale or missing
      prerequisites, including negative predicates. Set: Selection, direct execution, build, review,
      claim, redispatch, result acceptance, and publication over specifications, plans, releases,
      decisions, floors, policy, membership, admission, graph, roster, reservations, and receipts.
      Completeness: Require exact registry coverage of R70 entries and read-set kinds; mutate each
      referenced version and insert a conflicting blocker after the read, while holding project
      version fixed, and require a named refusal. Falsifier: Allow review against a draft governing
      plan; the eligibility/review-draft-plan row must fail.
    falsified_by: >
      Allow review against a draft governing plan; the eligibility/review-draft-plan row must fail.
  - id: AC3
    text: >
      Claim: Engineering completion requires complete contextual proof, independent review with
      finding disposition, and verification of the exact integrated candidate outside worker control.
      Set: Implementation Git object, accepted spec and complete criterion set, evidence digests,
      producer and reviewer identities, checks, candidate tree, installed verifier, protected-path
      approval, and post-run tree equality. Completeness: Generate removal and substitution fixtures
      for each proof/review/gate obligation from the contract registry; include empty criteria,
      nonexistent commit, duplicate mappings, fabricated checks, builder as reviewer, unresolved
      objections, and candidate mutation. Falsifier: Accept an empty criterion universe as valid
      proof; the completion/empty-proof row must fail.
    falsified_by: >
      Accept an empty criterion universe as valid proof; the completion/empty-proof row must fail.
  - id: AC4
    text: >
      Claim: Publication eligibility and completion require current authority and claim generations,
      exact-old-tip publication, remote confirmation, and replicated receipt; uncertainty stays
      explicit. Set: Landing success, red gate, rejected approval, moved remote tip, withdrawn
      dependency, revoked authority, lost acknowledgement, and unknown effect outcomes at every
      landing boundary. Completeness: Enumerate the publication transition table and all R32 recovery
      findings; require evidence for each finding, external gate-output location, and a receipt
      joining implementation, proof, review, tested candidate, unit, and dispatch without self-
      certification. Falsifier: Treat a lost publication acknowledgement as successful completion
      without remote evidence; the completion/unknown-publication row must fail.
    falsified_by: >
      Treat a lost publication acknowledgement as successful completion without remote evidence; the
      completion/unknown-publication row must fail.
required_evidence: [unit, integration]
rollback: >
  Retain the prior accepted contract and compatible reader. Refuse new project-layer activation
  until corrected contracts are accepted; preserve accepted history and refuse implicit schema
  downgrade. Revert only unactivated contract changes through the ordinary reviewed path.
---

## Intent

**Outcome.** Give every reader and execution entry the same evidence-based meaning of eligibility and completion, with no status or review shortcut.

## Context

**Authority.** Package A of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R10, R13-R16, R25, R32, R46-R52, R56, R70, and R76. The later decision-surface ruling in its provenance header takes precedence over retained tracker-only wording.

**Risk.** Incorrect completion or eligibility can authorize unsafe execution and publication, so this concern is critical. No approval is asserted by human_approval: required; this draft must obtain its applicable approval and independent review before implementation or activation.

## Out of scope

**Boundary.** This spec defines pure completion and eligibility contracts. Reader rewiring, gate-output isolation, disposable candidate landing, and real lost-acknowledgement tests belong to C. VELDO-0015 is existing behavior; its three reporting follow-ups belong to B.

## Notes

**Proof discipline.** This is one contract concern, with four criteria. The named check rows above are implementation obligations, not claims that those checks exist today. Proof must show its tested set equals the declared schema or policy universe and must drive each stated mutation, demonstrate the changed bytes, require the named row to fail, and restore the implementation. Removing a failure fixture cannot reduce the declared universe.

**Implementation boundary.** Define pure versioned data and named transition refusals in canonical engine/, synchronize shipped counterparts, and record every new asset in the distribution inventory. The draft footprint lists existing integration points and contract/test additions; refine it to exact new modules and synchronized counterparts before ready. Do not build the B-H runtime under this spec. Future runtime observations and receipts are required by their own specifications.
