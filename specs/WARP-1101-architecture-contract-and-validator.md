---
schema: veldo.spec/v1
id: WARP-1101
title: The architecture contract artifact and its validator (W1 of PLAN-0011)
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0011
work: W1
plan_revision: 2
depends_on: []
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      A versioned architecture contract artifact lives at .veldo/architecture.yaml
      (schema veldo.arch/v1, per resolved decision D1), declaring the system's
      intended shape: areas with their module boundaries (path globs), the allowed
      dependencies between areas, the patterns and invariants in force, and size
      and complexity budgets, each rule marked mechanizable or review. This
      repository carries its OWN contract as the first instance, whose areas map to
      the real .veldo engine layout. python3 .veldo/validate.py arch validates it
      clean, and a selftest asserts the seed contract is present and approved.
  - id: AC2
    text: >
      A validator (.veldo/arch.py, invoked by .veldo/validate.py) structurally
      checks a contract the way a plan is checked and FAILS CLOSED by name on each
      of: a wrong schema id, a missing or empty required field, a non-integer
      version, an out-of-vocabulary enforcement label, an unknown budget rule kind
      (unknown rule kinds rejected at contract time), a dependency edge or budget
      that references an area the contract does not declare (referenced but
      absent), a duplicate area, pattern, invariant, or budget id, and a file
      outside the parser subset (malformed). Each failure class is proven by a
      negative selftest that refuses, and a well-formed contract validates clean.
  - id: AC3
    text: >
      The contract leaves draft only by a recorded human approval, mirroring the
      plan governance: a contract whose status is approved but which carries no
      approved_by or approved_at is refused, while a draft contract needs no
      approver. Changing the shape means changing the contract first, on the
      record. Both the negative (approved without approver refuses) and the
      positive (draft is valid un-approved state) are asserted in the selftest.
  - id: AC4
    text: >
      Adoption safe and fail closed. An absent contract stands down: a repository
      without a contract is byte-identically unaffected by the check (verified over
      a temporary tree). A contract that is referenced as required but is absent
      fails closed by name, and a malformed present contract fails closed. The
      contract carries a pluggable per-language analyzer slot (per resolved
      decision D6); a reference analyzer whose referenced config file is absent
      fails closed (referenced but absent). Each is proven by a selftest.
  - id: AC5
    text: >
      The check has TEETH proven by mutation over this repository's REAL contract
      (the anti-vacuity rule C1): repointing a real dependency edge to an undeclared
      area, and stripping the recorded approval while approved, each turn the check
      RED. .veldo/arch.py ships in the engine and is re-synced byte-identical across
      engine and all packs, .veldo/validate.py's edit is re-synced
      likewise, and capabilities.yaml gains one honest mechanical entry in every
      copy (template sync and pack drift pass). The contract ARTIFACT
      .veldo/architecture.yaml is per-repo and is NOT shipped in the engine, so a
      fresh init stays contract-free and adoption safe. The full gate is GREEN
      (selftest, contracts, generated, docs, secret scan, drift), RULE #1 is clean,
      and no protected path is touched.
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds one artifact (.veldo/architecture.yaml,
  per-repo), one validator module (.veldo/arch.py), a call to it from
  .veldo/validate.py, a capabilities entry, and a selftest block; nothing consumes
  the contract for enforcement yet (the first consumers are WARP-1102 and
  WARP-1103), so removing it returns the gate to its prior behavior with no
  migration and nothing to unwind. Removing or leaving unapproved the contract
  file alone also stands the check down (the adoption-safe posture).
---

## Intent

This is the first root of PLAN-0011: the intended shape of the system becomes an
artifact, not a memory. Today VELDO proves each change locally (spec, gate, proof,
independent review) but has no place that states the shape those changes must
fit. This item creates that place - a versioned, human-approved architecture
contract at .veldo/architecture.yaml (schema veldo.arch/v1) - and the structural
validator that keeps the contract itself honest, exactly the move that once
turned intent into the spec. Changing the shape now means changing the contract
first, on the record.

## Context

- Resolved decision D1: the artifact is the architecture contract at
  .veldo/architecture.yaml, schema veldo.arch/v1. WARP-1101 is a frontier root
  (depends_on: []), unblocked the moment PLAN-0011 left draft (revision 2,
  approved 2026-07-22).
- The validator is modeled on .veldo/plan.py: structural, required-field and
  closed-vocabulary checks over the same front-matter subset (validate.parse_yamlish),
  no second parser, no import cycle. arch.py receives the parser and the failure
  reporter from validate.py, which owns them.
- Resolved decision D6: duplication and complexity measurement are
  stdlib-proportionate reference implementations with a pluggable per-language
  slot; this item ships the slot in the contract schema (analyzers), and the
  reference analyzers themselves ship with WARP-1102 (W2).
- The two postures the plan binds everywhere: adoption safe (a repository without
  a contract is untouched, every new check stands down) and fail closed (the
  moment a contract exists it is validated and refuses anything malformed).

## Out of scope

- No gate enforcement of the shape rules against the source. Reading the contract
  and failing scripts/verify.sh on a boundary, budget, duplication, or pattern
  violation is WARP-1102 (W2). This item is the contract and its structural
  validator only.
- No placement or footprint on specs (WARP-1103, W3), no shape-fit review
  dimension (WARP-1104, W4), no decision records, tripwires, or entropy metrics.
- No change to the shipped enforcement core: scripts/verify.sh, veldo-guard.sh,
  .veldo/policy_check.py, .veldo/policy.yaml and their engine twins are
  untouched (protected paths).

## Notes

- Keep the validator dependency free and the artifact readable (the C3
  proportionality constraint: readable file formats, stdlib implementations, no
  signing or ledger formalism). Follow the byte-identical engine sync discipline:
  .veldo/arch.py and the edited .veldo/validate.py and .veldo/capabilities.yaml land
  in engine and every pack byte-identical, and the drift checks end
  empty. The contract artifact itself is per-repo (like capabilities.yaml and
  policy.yaml) and is NOT synced into the engine, so a fresh /veldo:init repository
  starts contract-free and adoption safe.
- Put teeth on the check by mutating this repository's real contract and observing
  the gate go red before reverting; a mechanical check that cannot refuse is
  exactly the vacuity C1 forbids.
- RULE #1 clean (ASCII hyphen only, no em or en dash, no prose double-hyphen).
