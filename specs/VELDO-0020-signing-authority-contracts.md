---
schema: veldo.spec/v1
id: VELDO-0020
title: Signing and authority contracts for enrolled channels
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W5
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017]
placement: [contracts, engine, tracker]
protected_paths: []
footprint:
  - ".veldo/authorization.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/request.py"
  - "engine/.veldo/request.py"
  - ".veldo/request_reconcile.py"
  - "engine/.veldo/request_reconcile.py"
  - ".veldo/request_projection.py"
  - "engine/.veldo/request_projection.py"
  - "engine/.veldo/*contract*.py"
  - "scripts/suites/*"
  - "packs/**/.veldo/*contract*.py"
  - "specs/VELDO-0020-signing-authority-contracts.md"
  - "specs/index.md"
  - "proof/VELDO-0020/*"
behavior_bearing: true
observability:
  logs: Contract refusals name the predicate, subject revision, and offending reference without including private keys or credentials.
  metrics: Proof reports required and exercised schema, transition, or boundary sets and coverage gaps; an unknown result never counts as zero failures.
  traces: Evidence joins the criterion, fixture or observation, input digests, and exact contract revision; runtime receipt production belongs to later packages.
  error_taxonomy: Distinguish missing input, malformed input, stale revision, unauthorized actor, forbidden transition, and unavailable evidence with named refusals.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Distinct principal types and scoped membership govern authorization; role, quorum, named-
      principal, and independence requirements are conjunctive. Set: People, services, policies, and
      agent runs at command, proposal, assignment, claim, dispatch, privileged-tool, result, decision,
      and landing boundaries. Completeness: Derive the boundary/type matrix from the authority
      contract and compare it to R39; exercise each applicable role, actor kind, quorum, expiry,
      revocation, and independence failure with a matching permitted control. Falsifier: Allow an
      agent to satisfy a named-person predicate; the authority-substitution/named-principal row must
      fail.
    falsified_by: >
      Allow an agent to satisfy a named-person predicate; the authority-substitution/named-principal
      row must fail.
  - id: AC2
    text: >
      Claim: Command signatures bind the complete request and active delegation, and verification does
      not trust ambient transport or branch keys. Set: Domain, repository, store, command ID, request
      revision, challenge nonce, expiry, membership and delegation versions, and accepted key
      transitions in OpenSSH-envelope Ed25519 commands. Completeness: Enumerate signed fields from the
      versioned envelope schema; mutate each one independently and test replay, retired verification
      keys, revoked active authority, rotation, and wrong repository with complete field coverage.
      Falsifier: Omit repository identity from signature verification; the signing/wrong-repository
      row must fail.
    falsified_by: >
      Omit repository identity from signature verification; the signing/wrong-repository row must
      fail.
  - id: AC3
    text: >
      Claim: Every enrolled channel uses its own restricted edge key and presentation-bound canonical
      attribution; text, display names, and channel count cannot substitute for evidence or people.
      Set: Telegram chat, Jira, signed CLI, and email when enrolled; each edge delegation binds
      principal, channel, assertion kind, authority scope, request and presentation version, and
      expiry. Completeness: Generate edge conformance from the enrolled-channel registry, require
      positive and refusing fixtures per field, and include chat platform message ID, sender ID, and
      timestamp fetched from the platform plus the CLI personal envelope and email refusal while
      unenrolled. Falsifier: Accept a chat assertion with message text but no platform message ID; the
      channel-attribution/text-only row must fail.
    falsified_by: >
      Accept a chat assertion with message text but no platform message ID; the channel-
      attribution/text-only row must fail.
  - id: AC4
    text: >
      Claim: One request version settles once in Veldo with originating-channel attribution, exact
      presentation, and dependent effects; repeated channel assertions do not create new principals or
      authority. Set: Concurrent same-channel and cross-channel answers, framing revisions, rendered
      brief changes, subject changes, expired requests, revoked keys, quorum accumulation, and
      decision binding effects. Completeness: Declare the settlement transition input universe from
      R40/R72, enumerate every refusal family and pairwise cross-channel winner order, and assert a
      single terminal transition with nonce and projection obligations in the atomic result.
      Falsifier: Count one principal answering on two channels as two quorum members; the
      settlement/cross-channel-principal row must fail.
    falsified_by: >
      Count one principal answering on two channels as two quorum members; the settlement/cross-
      channel-principal row must fail.
required_evidence: [unit, integration]
rollback: >
  Retain the prior accepted contract and compatible reader. Refuse new project-layer activation
  until corrected contracts are accepted; preserve accepted history and refuse implicit schema
  downgrade. Revert only unactivated contract changes through the ordinary reviewed path.
---

## Intent

**Outcome.** Define who may authorize each action and how every enrolled channel proves the actor and presentation without becoming another authority.

## Context

**Authority.** Package A of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R09, R15, R18, R20, R36-R41, R56, R60, R70, R72, and R74. The later decision-surface ruling in its provenance header takes precedence over retained tracker-only wording.

**Risk.** Signature and principal substitution can grant admission or settlement authority, so this concern is critical. No approval is asserted by human_approval: required; this draft must obtain its applicable approval and independent review before implementation or activation.

## Out of scope

**Boundary.** Cryptographic key enrollment and store implementation are B. Real platform evidence, channel signing infrastructure, interrupted settlement, and live ingress activation are E. No key, person, or channel is enrolled by this draft.

## Notes

**Proof discipline.** This is one contract concern, with four criteria. The named check rows above are implementation obligations, not claims that those checks exist today. Proof must show its tested set equals the declared schema or policy universe and must drive each stated mutation, demonstrate the changed bytes, require the named row to fail, and restore the implementation. Removing a failure fixture cannot reduce the declared universe.

**Implementation boundary.** Define pure versioned data and named transition refusals in canonical engine/, synchronize shipped counterparts, and record every new asset in the distribution inventory. The draft footprint lists existing integration points and contract/test additions; refine it to exact new modules and synchronized counterparts before ready. Do not build the B-H runtime under this spec. Future runtime observations and receipts are required by their own specifications.
