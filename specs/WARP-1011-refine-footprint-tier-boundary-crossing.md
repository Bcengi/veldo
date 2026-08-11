---
schema: veldo.spec/v1
id: WARP-1011
title: Refine the footprint tier rule to a boundary crossing, not mere breadth
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: standalone
protected_paths: []
placement: [contracts]
footprint:
  - .veldo/arch.py
  - .veldo/capabilities.yaml
  - scripts/selftest.py
  - engine/.veldo/arch.py
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/arch.py
  - packs/*/.veldo/capabilities.yaml
  - specs/WARP-1011-refine-footprint-tier-boundary-crossing.md
acceptance_criteria:
  - id: AC1
    text: >
      footprint_tier_floor (in .veldo/arch.py) raises a spec's required risk tier to at
      least high ONLY when the declared areas its footprint (with its placement) touches
      contain a PAIR with NO allow-listed dependency edge between them in either direction:
      a genuine boundary crossing, an architecturally-unmodeled coupling per the contract's
      dependencies.allow edges. When every pair of touched areas is joined by an allow-listed
      edge in some direction (cohesive breadth), or the footprint touches at most one declared
      area, the tier is NOT raised. Proven over this repository's REAL contract (verified
      against .veldo/architecture.yaml dependencies.allow): a connected pair {contracts, loop}
      (loop-to-contracts) and {contracts, fleet} (fleet-to-contracts) each stay standard; the
      unmodeled pair {enforcement, fleet} (no edge either direction) elevates to high; a single
      area stays standard; a three-area all-connected footprint stays standard while a
      three-area footprint containing one unmodeled pair elevates. A small pure helper reads the
      contract's dependencies.allow (the one place the tier rule consults the dependency graph).
  - id: AC2
    text: >
      The existing WARP-1103 selftest assertions are UPDATED to the refined semantics, not left
      encoding the old coarse rule (two-area-via-allowed-edge -> standard; two-area-no-edge ->
      high; single area -> standard). Coverage is re-pointed, not deleted: the fixture that once
      asserted "any two-area span elevates" now exercises both a connected pair (stays standard)
      and an unmodeled pair (elevates), using a fixture extended with an unconnected area so the
      distinction the old rule could not make is under test. A source guard confirms the retired
      coarse assertion label is gone from scripts/selftest.py and the refined boundary-aware
      labels are present, and that no other shipped test encodes the old coarse rule.
  - id: AC3
    text: >
      The refinement has TEETH proven by mutation (the anti-vacuity rule C1). The connectivity
      read from dependencies.allow is load-bearing: over the fixture, REMOVING the only declared
      edge flips the previously-connected two-area pair from standard to high (observed RED), and
      restoring the edge reverts it to standard byte-identical, with the real .veldo/arch.py on
      disk never mutated. The core fix is proven directly: a connected-pair footprint at risk
      standard PASSES the mandatory placement gate (RED if it wrongly elevated, the rubber stamp
      the founder decision removes), while an unmodeled-pair footprint at risk standard is
      REFUSED (a genuine crossing still elevates), and the unmodeled pair passes once its risk is
      raised to high.
  - id: AC4
    text: >
      Forward-only: the refinement retroactively changes nothing. footprint_tier_floor is computed
      only at the ready transition, the claim, and run-check (via placement_gate), never in
      validate.py run_all's corpus pass, so the already-shipped corpus is never re-tiered. A source
      guard confirms run_all invokes no tier gate. The shipped WARP-1103 (recorded risk high) and
      its frozen proof (bound to impl commit 84fc55d) are unchanged, check_spec over the shipped
      WARP-1103 spec still validates, and its recorded risk stays high. Dogfooded on the very spec
      that motivated the fix: WARP-1103's {contracts, fleet} footprint is now cohesive breadth
      (connected by the allow-listed fleet-to-contracts edge), so under the refined rule it no
      longer trips a tier floor, and it still passes the gate at its recorded risk high (nothing
      lowers a declared tier).
  - id: AC5
    text: >
      NEW-MODULE detection stays DEFERRED to WARP-1102 (W2), stated honestly. This refinement only
      sharpens the boundary-crossing signal; it reads the declared areas and the contract's
      dependency edges alone and inspects no diff, so it makes no new-module claim. A footprint
      glob cannot by itself tell a genuinely new path from one the contract simply does not
      enumerate; that needs the gate-time footprint-versus-diff machinery of WARP-1102. The
      docstring of footprint_tier_floor and the spec_placement_footprint capability note both name
      the deferral to WARP-1102 (W2) and disclaim adding new-module detection here.
  - id: AC6
    text: >
      Byte-identical pack sync, no protected path, and a clean dogfood. The refined .veldo/arch.py
      and the honestly-updated .veldo/capabilities.yaml note ship byte-identical across root,
      engine, and all 6 packs (pack drift empty, pack conformance pass, template sync
      pass). This spec (WARP-1011) declares placement [contracts] and a footprint that resolves to
      the contracts area only, so its own required tier is standard with no approval, a clean
      dogfood of the very rule it refines; it passes the mandatory placement gate at risk standard
      and declares no protected path. No protected path (scripts/verify.sh, scripts/veldo-guard.sh,
      .veldo/policy.yaml, .veldo/policy_check.py and their twins) is touched, the full gate is GREEN
      (selftest, contracts, generated, docs, secret scan, template sync, pack drift), and RULE #1
      is clean (ASCII hyphen only, no em or en dash, no prose double-hyphen).
required_evidence: [unit]
rollback: >
  Revert the commit. The change refines footprint_tier_floor in .veldo/arch.py (adding two small
  pure helpers that read the contract's dependencies.allow and test pairwise connectivity),
  updates the WARP-1103 selftest assertions to the refined boundary-aware semantics, adds a
  WARP-1011 selftest block, and honestly updates the spec_placement_footprint capability note,
  all re-synced byte-identical across engine and the 6 packs. The rule is computed only
  at the ready transition, the claim, and run-check, never as a corpus sweep, so reverting returns
  the tier computation to its prior coarse form with no migration and nothing to unwind; the
  already-shipped corpus was never re-tiered either way. A repository with no architecture
  contract is unaffected (the adoption-safe posture).
---

## Intent

WARP-1103 (shipped) added the footprint-to-tier rule: a spec whose placement and footprint
together span two or more declared contract areas had its required risk tier floored at high,
forcing human approval. That rule was too coarse. It elevated ANY two-area change, even when the
two areas are connected by an allow-listed dependency edge, which is mere breadth and
architecturally fine. That was a rubber stamp (the founder's word, 2026-07-22): needless human
approval that has already pushed two builders to scope AWAY from legitimate cross-area work to
dodge the gate.

This refinement sharpens the signal. The tier floor rises to high ONLY when the touched areas
contain a PAIR with NO allow-listed dependency edge between them in either direction: a genuine
boundary crossing, a coupling the architecture contract does not model. Cohesive breadth over
allow-listed edges no longer elevates. The signal now marks a real crossing, not size.

## Context

- Depends on WARP-1103 (shipped): footprint_tier_floor, footprint_areas, area_for_path, and the
  mandatory placement_gate in .veldo/arch.py, and its selftest block in scripts/selftest.py. This
  item refines footprint_tier_floor and updates those WARP-1103 assertions to match.
- The contract's dependencies.allow (in .veldo/architecture.yaml) is the model of intended
  couplings. An allow-listed edge in either direction between a pair of touched areas means the
  coupling is sanctioned (cohesive breadth); the absence of any edge is the unmodeled coupling a
  genuine boundary crossing is. The refined rule reads exactly those edges.
- Forward-only by construction: footprint_tier_floor is computed at elaboration, the ready
  transition, the claim, and run-check, never as a sweep of the shipped corpus (run_all does not
  invoke it), so shipped specs including WARP-1103 keep their recorded risk and frozen proofs.

## Out of scope

- No new-module detection. Deciding that a change CREATES a genuinely new module (a brand-new path
  belonging to no area yet) needs the actual diff, which is WARP-1102's (W2) gate-time
  footprint-versus-diff machinery: a footprint glob cannot by itself tell a new path from one the
  contract does not enumerate. This item only sharpens the boundary-crossing signal.
- No transitive connectivity. The rule tests the DIRECT allow-listed edge between a pair (either
  direction), matching "a pair with no edge between them". Whether transitive reachability should
  count as cohesion is a separate contract-semantics question, not decided here.
- No retroactive re-tiering. The shipped corpus is past ready and claim and is never re-evaluated;
  WARP-1103's recorded risk high and its frozen proof are unchanged.
- No change to the shipped enforcement core: scripts/verify.sh, veldo-guard.sh, .veldo/policy_check.py,
  .veldo/policy.yaml and their twins are untouched (protected paths). The rule lives in the
  non-protected engine (.veldo/arch.py).

## Notes

- Keep the rule PURE and read the contract's edges through one small helper (_allowed_edges), so
  the tier rule and the contract validator agree on what an allow-listed edge is. arch.py adds no
  second parser and imports only pathlib and re.
- Put teeth on the connectivity read (mutate the fixture's edge and observe the previously-connected
  pair elevate, then revert) and prove the core fix directly (a connected-pair footprint at risk
  standard passes the gate). A mechanical check that cannot refuse, or one that cannot PASS a
  legitimate breadth change, is exactly the vacuity C1 forbids.
- Follow the byte-identical engine sync discipline: the edited .veldo/arch.py and .veldo/capabilities.yaml
  land in engine and every pack byte-identical, and the drift checks end empty. The
  architecture contract ARTIFACT stays per-repo (not synced into the engine).
- RULE #1 clean (ASCII hyphen only, no em or en dash, no prose double-hyphen).
