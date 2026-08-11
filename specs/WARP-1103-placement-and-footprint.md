---
schema: veldo.spec/v1
id: WARP-1103
title: Placement and footprint at elaboration (W3 of PLAN-0011)
status: shipped
risk: high - the footprint crosses from the contracts area into the fleet area (it edits frontier.py), and by this spec's own footprint tier rule a boundary-crossing change is at least high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0011
work: W3
plan_revision: 2
depends_on: [WARP-1101]
protected_paths: []
placement: [contracts]
footprint:
  - .veldo/arch.py
  - .veldo/validate.py
  - .veldo/plan.py
  - .veldo/frontier.py
  - .veldo/capabilities.yaml
  - engine/.veldo/arch.py
  - engine/.veldo/validate.py
  - engine/.veldo/plan.py
  - engine/.veldo/frontier.py
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/arch.py
  - packs/*/.veldo/validate.py
  - packs/*/.veldo/plan.py
  - packs/*/.veldo/frontier.py
  - packs/*/.veldo/capabilities.yaml
  - packs/claude/skills/spec/SKILL.md
  - packs/*/skills/spec/SKILL.md
  - specs/TEMPLATE.md
  - specs/WARP-1103-placement-and-footprint.md
  - scripts/selftest.py
acceptance_criteria:
  - id: AC1
    text: >
      A spec declares, in its front matter, a placement (one or more architecture
      area ids from the .veldo/architecture.yaml contract that the change lands in)
      and a footprint (the path globs it is allowed to touch). The FIELDS are optional
      at the schema level (a draft that has not yet been elaborated, and every spec in
      a contract-free repository, is byte-identically unaffected), but once a contract
      exists the placement becomes MANDATORY at the ready transition and the claim (AC6).
      The shipped spec TEMPLATE documents both fields and states the mandatory-at-ready
      rule, and this spec (WARP-1103) itself declares its placement (area contracts,
      since it extends the contract validators) and a footprint as the first dogfood
      instance. python3 .veldo/validate.py placement
      specs/WARP-1103-placement-and-footprint.md validates it clean, and a selftest
      asserts the real spec declares placement contracts and validates through both
      check_placement and check_spec.
  - id: AC2
    text: >
      A validator (validate_placement in .veldo/arch.py, invoked from
      .veldo/validate.py check_placement at spec-validation time) checks a declared
      placement AGAINST the contract's areas and FAILS CLOSED by name on each of: a
      placement area id that does not resolve to a declared contract area (referenced
      but absent), a placement that is not a non-empty list, a footprint that is
      missing or empty when a placement is declared, a footprint entry that is not a
      non-empty path-glob string, a footprint declared without a placement (a
      footprint is placeless without an area), and a duplicate placement area id.
      Each failure class is proven by a negative selftest that refuses, and a
      well-formed declaration validates clean. It reuses validate.parse_yamlish (no
      second parser) and the validate.fail reporter (no import cycle), and reads the
      contract's areas through arch.area_ids (the one place placement resolution
      reads the contract).
  - id: AC3
    text: >
      Optional and adoption safe on two axes, fail closed once declared. When no
      architecture contract exists in the repository the placement check stands down
      entirely, so a contract-free repository is byte-identically unaffected (the C2
      posture, verified over a temporary tree); and when a contract exists, a spec
      that declares neither placement nor footprint stands down too (placement is
      never forced onto a spec). The moment a placement is declared against a present
      contract it is validated fail closed. Both the stand-downs (no contract, no
      declaration) and the fail-closed refusals (unknown area, empty footprint) are
      asserted in the selftest.
  - id: AC4
    text: >
      The checks have TEETH proven by mutation over this repository's REAL WARP-1103
      spec (the anti-vacuity rule C1): repointing its placement to an area the
      contract does not declare, and removing its placement while keeping its
      footprint, each turn the structural check RED; and against the MANDATORY gate,
      removing the real spec's placement, and lowering its risk below the tier its
      boundary-crossing footprint implies, each turn placement_gate RED. Each mutation
      is applied to a copy of the real front matter and reverts byte-identical. Honesty
      (NG5): the elaboration-time gate makes no assertion about the source or the diff.
      Enforcing the declared footprint against the actual diff at gate time, and
      detecting a genuinely new module, is WARP-1102 (W2); grading whether a change fits
      the declared shape is the shape-fit review dimension WARP-1104 (W4); neither is
      claimed here.
  - id: AC6
    text: >
      MANDATORY at the ready transition and the claim, without a corpus sweep. When a
      contract exists, a spec may not REACH ready and is never CLAIMED for build unless
      it declares a placement that resolves to a contract area. placement_gate (a pure
      predicate in .veldo/arch.py) is the one implementation; it is enforced at the
      transition and claim code paths, never as a static check_spec rule over every
      spec: validate.py check_ready (the ready CLI mode, run by the /veldo:spec skill)
      refuses the ready transition, frontier.claimable filters a placeless build unit
      out of the claimable set, and plan.py run-check refuses the build. The already
      shipped corpus is past ready and claim, so it is never re-evaluated and needs no
      migration: a selftest guard proves a SHIPPED placeless spec still validates
      through check_spec while check_ready on the same spec (with a contract present)
      refuses, and scripts/verify.sh stays green over the 107 shipped specs unchanged.
      Adoption safe: with no contract the gate stands down everywhere (verified over a
      temporary tree).
  - id: AC7
    text: >
      A footprint that crosses a declared area boundary raises the risk tier and
      nothing lowers it. footprint_tier_floor (in .veldo/arch.py) maps a footprint's
      globs to the contract's areas (area_for_path), and when a spec's placement and
      footprint together span two or more declared areas the required tier floor is at
      least high; placement_gate refuses a spec whose declared risk is below that floor.
      A selftest fixture whose footprint spans two areas with risk standard is refused
      (RED) and passes once its risk is high. HONEST BOUNDARY: the multi-area span is
      the signal well defined from the declaration alone; detecting that a change
      creates a genuinely new module needs the actual diff and is deferred to WARP-1102
      (W2). This spec dogfoods the rule: its footprint edits frontier.py (the fleet
      area) as well as the contracts-area validators, so it spans contracts and fleet,
      is therefore a high-risk change by its own rule, and is declared risk high.
  - id: AC5
    text: >
      The extended engine ships byte-identical across all 8 copies (root,
      engine, and the 6 packs): validate_placement, placement_gate,
      footprint_tier_floor, area_for_path in .veldo/arch.py; check_ready,
      placement_gate_problems, placement_gate_ok, load_repo_contract and the ready CLI
      mode in .veldo/validate.py; the run-check gate in .veldo/plan.py; and the claimable
      filter in .veldo/frontier.py. The spec TEMPLATE gains the mandatory-at-ready
      documentation and the /veldo:spec elaboration skill asks for placement and
      footprint (synced across the skill copies); capabilities.yaml carries one honest
      mechanical entry (spec_placement_footprint) updated to the mandatory gate in every
      copy (template sync and pack drift pass). The architecture contract ARTIFACT stays
      per-repo and is not shipped in the engine, so a fresh init stays contract-free and
      the gate stands down (adoption safe). The full gate is GREEN (selftest, contracts,
      generated, docs, secret scan, template sync, pack drift), RULE #1 is clean, and no
      protected path is touched (the transition and claim gate lives in the non-protected
      engine, not in verify.sh, veldo-guard.sh, policy.yaml, or policy_check.py).
required_evidence: [unit]
rollback: >
  Revert the commit. The change extends .veldo/arch.py (area_ids, validate_placement,
  and the mandatory gate placement_gate with footprint_tier_floor and area_for_path),
  wires it from .veldo/validate.py (check_placement plus check_ready and the silent gate
  predicates, with a placement and a ready CLI mode), gates the claim in .veldo/frontier.py
  and the build in .veldo/plan.py run-check, asks for placement in the /veldo:spec skill,
  updates the spec TEMPLATE and one capabilities entry, and adds selftest teeth. The gate
  is scoped to the ready transition and the claim, so it evaluates no already-shipped
  spec; reverting returns spec validation and claiming to their prior behavior with no
  migration and nothing to unwind. A spec that declares no placement, and a repository
  with no architecture contract, are unaffected either way (the adoption-safe posture).
---

## Intent

This is W3 of PLAN-0011, the elaboration-time half of the architecture organ: no
change is built placeless. When a spec is elaborated it declares WHERE in the
declared shape its change lands (its placement into one or more architecture areas
from the .veldo/architecture.yaml contract) and its FOOTPRINT (the path globs it is
allowed to touch), and that declaration is validated against the contract's areas
at the cheapest moment, before anything is built. A placement that names an area
the contract does not declare is refused; a footprint is a real, non-empty glob
list. Placement stops being a memory an agent carries and becomes a checked field,
the same move that turned intent into the spec and the shape into a contract.

The declaration is not merely allowed, it is REQUIRED at the moment it matters. When
a contract exists, a spec may not reach ready and is never claimed for build unless
its placement resolves to a contract area (outcome O3 and regression RJ2). This is
enforced exactly at the ready transition (validate.py check_ready) and the claim
(frontier.claimable and plan.py run-check), never as a static sweep of every spec,
so the mandatory rule binds new work at the transition while the 107 already-shipped
specs, long past ready and claim, are untouched and need no migration. And because a
footprint reveals what a change actually spans, a footprint that crosses a declared
area boundary raises the spec's risk tier and nothing lowers it: the cheapest moment
to notice that a change is bigger than it claims to be is before it is built.

## Context

- Depends on WARP-1101 (shipped): the architecture contract at
  .veldo/architecture.yaml (veldo.arch/v1) and its validator .veldo/arch.py. This item
  extends arch.py with area_ids, validate_placement (the optional structural check),
  and the mandatory gate (placement_gate, footprint_tier_floor, area_for_path), and
  reads the contract through arch.load_contract, the one place the artifact is parsed.
- The validator is modeled on the two shipped siblings (.veldo/arch.py for the
  contract, .veldo/decision.py for the decision record): structural, fail-closed,
  reusing validate.parse_yamlish (no second parser) and validate.fail (no import
  cycle). validate.check_placement loads arch.py and passes in this module's parser
  and reporter.
- The two postures the plan binds everywhere: adoption safe (a repository without a
  contract is untouched, and a spec that declares no placement stands down) and fail
  closed (the moment a placement is declared against a present contract it is
  validated and refuses anything that does not resolve).
- Resolved decision D1: the contract lives at .veldo/architecture.yaml with areas the
  placement resolves against. This repository's contract declares the area
  contracts, which is where this change (extending the contract validators) lands,
  so WARP-1103 is its own first dogfood placement.

## Out of scope

- No enforcement of the declared footprint against the actual diff. Reading the
  footprint and failing scripts/verify.sh when a change touches a path outside it is
  WARP-1102 (W2, the gate-time shape enforcement), a protected-path change this item
  does not make. This item validates the DECLARATION at elaboration time and enforces
  the mandatory placement at the ready transition and the claim; it does not compare
  the footprint to the built diff.
- No new-module detection from the footprint alone. Deciding that a change CREATES a
  genuinely new module (a brand-new path belonging to no area yet) needs the actual
  diff, which is W2's gate-time footprint-versus-diff machinery: a footprint glob
  cannot by itself tell a new path from one the contract does not enumerate. The
  well-defined elaboration-time signal, a footprint that spans two or more declared
  areas (a boundary crossing), is what the tier rule enforces here.
- No shape-fit review dimension. Grading whether a correct change fits the declared
  shape, with correct-but-does-not-fit as a rework verdict, is WARP-1104 (W4).
- No corpus migration. The mandatory placement rule is scoped to the ready transition
  and the claim, not a static re-check of every spec, so the already-shipped corpus is
  never re-evaluated and nothing is migrated.
- No change to the shipped enforcement core: scripts/verify.sh, veldo-guard.sh,
  .veldo/policy_check.py, .veldo/policy.yaml and their engine twins are
  untouched (protected paths). The mandatory gate lives in the non-protected engine
  (arch.py, validate.py, plan.py, frontier.py).

## Notes

- Keep the gate predicate PURE and in one place: arch.placement_gate returns the list
  of problems (arch.py imports only pathlib and re), and every consumer renders it, so
  the ready transition, the claimable frontier, and run-check never diverge on what a
  resolving placement is. arch.py adds no second parser; validate.load_repo_contract
  loads and parses the contract once per pass.
- Put the claim-side gate in frontier.claimable (the claimability decision), not in the
  claim ledger .veldo/claim.py, which stays a pure coordination primitive that does not
  read specs. fleet depends on contracts is an allowed edge in the contract, and
  frontier already imports validate, so no new boundary is introduced.
- Follow the byte-identical engine sync discipline: the edited .veldo/arch.py,
  .veldo/validate.py, .veldo/plan.py, .veldo/frontier.py, .veldo/capabilities.yaml, the
  documented specs/TEMPLATE.md, and the /veldo:spec skill land in engine and
  every pack byte-identical, and the drift checks end empty. The contract ARTIFACT stays
  per-repo (not synced into the engine), so a fresh /veldo:init repository starts
  contract-free and the gate stands down.
- Put teeth on each behavior by mutating this repository's real WARP-1103 spec and
  observing the check go red before reverting, and prove the no-corpus-sweep guard (a
  shipped placeless spec still validates while check_ready on it refuses); a mechanical
  check that cannot refuse is exactly the vacuity C1 forbids.
- RULE #1 clean (ASCII hyphen only, no em or en dash, no prose double-hyphen).
