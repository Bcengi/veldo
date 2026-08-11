---
schema: veldo.spec/v1
id: WARP-0616
title: the authorization module for the human-decision surface - required_roles / quorum / is_authorized /
  separation-of-duties + anti-rubber-stamp attestations, reading an approver block from policy.yaml
  (absent = fail-closed) and reusing the frozen two_key for irreversible / money / external; the engine
  ships INERT and authorizes nothing until the protected policy.yaml block is added under a separate
  approval (W6 of the human-decision surface)
status: shipped
risk: standard - an additive, INERT authorization engine. It is a set of PURE functions that decide whether
  a veldo.request/v1 human decision is authorized, reading an approver block from policy.yaml; but that
  block does NOT exist in any shipped policy.yaml, so in the committed state is_authorized returns False for
  every request (fail-closed, authorizes nothing). It touches NO protected path (it does NOT edit
  policy.yaml - adding the approver block is a SEPARATE protected-path approval, VEL-3), reuses the frozen
  two_key.py unchanged for irreversible/money/external, reads policy.yaml read-only, and writes nothing.
  The switch-on (the policy.yaml edit) is the high-risk gated action and is out of scope here. The logic
  correctness is safety-critical and gets a full independent adversarial review.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0016
work: W6
plan_revision: 1
placement: [engine]
footprint:
  - .veldo/authorization.py
  - engine/.veldo/authorization.py
  - packs/aider/.veldo/authorization.py
  - packs/antigravity/.veldo/authorization.py
  - packs/codex/.veldo/authorization.py
  - packs/copilot/.veldo/authorization.py
  - packs/cursor/.veldo/authorization.py
  - packs/opencode/.veldo/authorization.py
  - .veldo/capabilities.yaml
  - engine/.veldo/capabilities.yaml
  - packs/aider/.veldo/capabilities.yaml
  - packs/antigravity/.veldo/capabilities.yaml
  - packs/codex/.veldo/capabilities.yaml
  - packs/copilot/.veldo/capabilities.yaml
  - packs/cursor/.veldo/capabilities.yaml
  - packs/opencode/.veldo/capabilities.yaml
  - .veldo/architecture.yaml
  - scripts/selftest.py
  - specs/WARP-0616-authorization-module.md
  - specs/index.md
  - proof/WARP-0616/**
protected_paths: []
behavior_bearing: true
observability:
  logs: is_authorized reports its decision as a structured record - the request id, touchpoint, tier, which
    roles/attestations it required, which it found, whether quorum + independence + separation held, whether
    two_key was required and satisfied, and the single reason it denied - so a stranger sees exactly why a
    decision was authorized or refused from the report alone.
  error_taxonomy: an absent or malformed approver block fails CLOSED (authorizes nothing, never open); a
    missing/duplicate/self approver denies on separation or quorum, not an exception; an irreversible/money/
    external request without a satisfied two_key contract is denied, not errored; a request whose bound
    digest changed after an attestation invalidates that attestation (denied, must re-attest).
acceptance_criteria:
  - id: AC1
    text: A new engine module .veldo/authorization.py provides PURE functions - required_roles(touchpoint,
      tier), quorum(tier) -> {count, min_independence}, and is_authorized(request, attestations,
      approver_registry) -> a structured decision (authorized bool + reason) - that decide whether a
      veldo.request/v1 human decision is authorized. It reads the approver policy read-only and writes
      nothing. It is distributed across all 8 engine copies (root + engine + 6 packs)
      byte-identical, like request.py / two_key.py.
  - id: AC2
    text: The approver policy is read from a human_decisions block in policy.yaml. That block is ABSENT from
      every shipped policy.yaml, so the module ships INERT - with no block configured, is_authorized returns
      authorized=False for EVERY request (fail-closed, adoption-safe). An absent OR malformed block fails
      closed, never open. This spec does NOT add the block or edit policy.yaml (protected path); switching it
      on is a separate approval (VEL-3).
  - id: AC3
    text: Anti-rubber-stamp attestations - an approval is only authorized when it carries STRUCTURED
      attestations (a non-empty rationale, an explicit risk_acceptance, and for a review-disposition
      touchpoint a finding_disposition), never a bare yes. Attestation is per-request (no bulk/blanket
      approve). A MATERIAL CHANGE to the bound artifact (its digest differs from the digest the attestation
      was made against) INVALIDATES that attestation - the decision is denied until re-attested.
  - id: AC4
    text: Separation of duties + quorum - an authorizing approver identity MUST differ from the request's
      producer/proposer and can NEVER be the agent/service-account; quorum(tier).count distinct approvers
      are required and min_independence is enforced (independent identities, not one identity counted twice).
      For a request whose impact is irreversible / money / external, the frozen two_key.authorize contract
      (KEY1 + KEY2, reused UNCHANGED) MUST additionally be satisfied or the request is denied.
  - id: AC5
    text: A selftest drives authorization.py offline and is NON-TAUTOLOGICAL - authorized when roles +
      quorum + independence + separation + attestations are all satisfied against a FIXTURE policy;
      fail-closed when the block is absent; denied when approver == producer (separation); denied when quorum
      is short or independence is faked; denied when an irreversible request lacks a satisfied two_key;
      denied when the bound digest changed after attestation - each with an in-memory source-mutation TOOTH
      that turns its assertion red while the on-disk module stays byte-unchanged (neutralizing the
      fail-closed default authorizes an unconfigured request; neutralizing the separation check authorizes a
      self-approval; neutralizing the digest-invalidation authorizes a stale attestation). None vacuous. All
      8 authorization.py copies are asserted byte-identical.
required_evidence: [unit]
rollback: git revert; additive - a new engine module in all 8 copies (byte-identical), one capability entry
  per copy, the module declared in the engine area of architecture.yaml, a selftest block, and this spec; it
  reuses the frozen two_key.py UNCHANGED; it touches NO protected path (policy.yaml is not edited); pure
  stdlib; and it ships INERT (authorizes nothing until the policy.yaml block is separately approved), so the
  change cannot alter any authorization outcome on its own.
---

## Intent

Build the engine that answers one question correctly: is THIS human decision authorized? Who is allowed to
approve this touchpoint at this tier, are there enough independent approvers, is the approver someone other
than the person (or agent) who proposed the work, did they attest with real reasoning rather than a bare
yes, and - for irreversible or money or external actions - is the two-key contract satisfied. It is the
matrix behind every gate in the human-decision surface.

Two safety properties are load-bearing here. First, it ships INERT: the approver block it reads does not
exist in any shipped policy.yaml, so until that block is added (a separate, protected, human-approved edit -
VEL-3) the engine authorizes nothing. Shipping the engine switches nothing on. Second, it FAILS CLOSED: a
missing or malformed policy, a short quorum, a self-approval, a stale attestation, or a missing two-key all
resolve to denied, never to authorized.

## Context

W6 of the approved human-decision surface (VEL-1). It composes on W2 (veldo.request/v1, WARP-0615) as the
thing being authorized and REUSES the shipped safety core unchanged - two_key.py (WARP-1207) for the
irreversible/money/external second key, and the same policy.yaml risk_tiers that policy_check.py reads. It
is a sibling of decision.py / two_key.py / policy_check.py and distributed the same way (all 8 engine
copies, byte-identical). It does NOT touch the frozen records and does NOT edit policy.yaml.
