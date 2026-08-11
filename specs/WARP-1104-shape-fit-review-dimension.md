---
schema: veldo.spec/v1
id: WARP-1104
title: The shape-fit review dimension - review grades whether a change fits the declared shape, and correct-but-does-not-fit is a rework verdict (W4 of PLAN-0011)
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0011
work: W4
plan_revision: 2
depends_on: [WARP-1101, WARP-1103]
protected_paths: []
placement: [contracts, fleet]
footprint:
  - .veldo/shape_review.py
  - .veldo/validate.py
  - .veldo/dispatch.py
  - .veldo/capabilities.yaml
  - .veldo/init_scaffold.py
  - engine/.veldo/shape_review.py
  - engine/.veldo/validate.py
  - engine/.veldo/dispatch.py
  - engine/.veldo/capabilities.yaml
  - packs/*/.veldo/shape_review.py
  - packs/*/.veldo/validate.py
  - packs/*/.veldo/dispatch.py
  - packs/*/.veldo/capabilities.yaml
  - scripts/selftest.py
  - specs/WARP-1104-shape-fit-review-dimension.md
acceptance_criteria:
  - id: AC1
    text: >
      The mechanizable half of the shape-fit dimension lives in .veldo/shape_review.py:
      mechanical_shape_findings decides, from the architecture contract plus the spec's
      placement/footprint plus the diff's paths alone, the shape-fit rules that need no
      judgment and FAILS CLOSED by name on each of: a placement area that does not
      resolve to a declared contract area (referenced but absent); a diff path outside
      the declared footprint (a change may not silently touch a path it did not declare);
      a diff path that resolves to a declared area outside the declared placement (the
      footprint does not stay within the declared areas); and a diff that couples two
      declared areas with no allow-listed dependency edge between them in either
      direction (an unmodeled boundary crossing the contract does not sanction). It
      reuses .veldo/arch.py's area_for_path, area_ids, and the dependency-graph helpers
      (_allowed_edges, _areas_connected, _glob_re), the one place a path is mapped to an
      area and a modeled boundary is defined, so there is no second placement or boundary
      implementation. A within-placement, within-footprint change yields no findings
      (positive control); each misfit class is proven RED by a negative selftest and the
      mutation reverts. python3 .veldo/validate.py shape-review <spec> <paths...> runs the
      mechanical dimension against this repository's contract and fails closed on a misfit;
      adoption safe (no contract stands the check down).
  - id: AC2
    text: >
      The pattern-fit judgment (whether a change follows the declared PATTERNS of the areas
      it touches, the part no mechanical rule can settle) is a DELEGATED fresh-context
      reviewer seam that FAILS LOUD, mirroring the executor's LiveLoop.review and the
      dispatcher's LiveReviewer. ShapeReviewer.review(spec, context) is the seam;
      shape_review_context assembles what the reviewer receives alongside the spec, the final
      diff, and the proof (the contract's declared areas, the spec's placement and footprint,
      the areas the final diff touched, and the mechanical findings); the reference
      LiveShapeReviewer is wired to nothing and RAISES ShapeReviewError, refusing to fabricate
      a judgment. No shape-fit judgment is synthesized in code, and a fake injected reviewer is
      the only path a judgment enters. A selftest asserts the reference reviewer raises, that
      ShapeReviewError is a ValueError, and that an injected reviewer is the sole entry point.
  - id: AC3
    text: >
      build_shape_fit assembles the shape_fit block a veldo.verdict/v1 verdict carries, from
      the mechanical findings and the delegated judgment, and the MACHINE NEVER LOWERS: any
      mechanical misfit forces verdict does_not_fit regardless of the judgment, a judgment of
      does_not_fit is honored, and only a clean mechanical result AND a reviewer verdict of fits
      yields fits. A malformed or fabricated judgment (a missing or out-of-vocabulary verdict) is
      refused by name (ShapeReviewError, the delegated seam fails loud, never fabricates). The
      machine-never-lowers tooth (a reviewer that says fits over a mechanical misfit still yields
      does_not_fit), the does_not_fit honoring, the clean-yields-fits case, and the malformed-judgment
      refusal are each asserted in the selftest.
  - id: AC4
    text: >
      The verdict contract (veldo.verdict/v1) carries the shape_fit finding and validate.py
      validates it FAIL CLOSED. validate_shape_fit (in .veldo/shape_review.py, invoked from
      validate.py check_json for a verdict) checks the shape_fit block structurally and refuses
      by name: a non-mapping block, an out-of-vocabulary shape_fit.verdict, a non-list mechanical
      findings list, a malformed review sub-block or an out-of-vocabulary review verdict, and a
      does_not_fit dimension that records no finding at all (a misfit must name what does not fit).
      A well-formed shape_fit block validates clean through python3 .veldo/validate.py verdict, and
      a verdict with no shape_fit dimension is byte-identically unaffected (adoption safe). Each
      failure class is proven by a negative selftest and the positive control validates.
  - id: AC5
    text: >
      The shape-fit dimension BLOCKS the merge (D4, RJ3): shape_fit_blocks(verdict) returns True
      for a does_not_fit dimension and (fail closed) for a malformed one, and False for a fits
      dimension or a verdict with no shape_fit (adoption safe). The dispatcher's verdict gate
      (dispatch._verdict_passes) consults it alongside the passing-verdict word and the policy
      check's blocking findings, so a CORRECT-BUT-MISFIT verdict (verdict pass, shape_fit does_not_fit)
      is REFUSED at the merge choke point and the spec returns to fail_status for rework, while a
      fitting verdict ships (reworked to fit). This is the fleet-area review-machinery touch W4
      needs, over the allow-listed fleet -> contracts edge (cohesive breadth, not a boundary
      crossing). A selftest drives the REAL dispatcher gate over both a misfit and a fitting verdict
      (the RJ3 conformance journey over a fixture change), and a verdict without a shape_fit block
      still passes the gate unchanged.
  - id: AC6
    text: >
      The extended engine ships byte-identical across all 8 copies (root, engine, and the
      6 packs): .veldo/shape_review.py is new engine, and the edits to .veldo/validate.py and
      .veldo/dispatch.py re-sync byte-identical (template sync and pack drift pass). The init scaffold
      lays .veldo/shape_review.py beside .veldo/decision_review.py; capabilities.yaml gains one honest
      entry (shape_fit_review, mechanical) that names the delegated pattern-fit reviewer as a fail-loud
      seam (NG5). This spec (WARP-1104) declares its own placement (contracts and fleet, the two areas
      it lands in) and footprint and computes to tier standard, because contracts and fleet are joined
      by the allow-listed fleet -> contracts edge (cohesive breadth under the WARP-1011 refined rule,
      not a boundary crossing). No protected path is touched (the merge-gate wiring lives in the
      non-protected fleet dispatcher, not in verify.sh, veldo-guard.sh, policy.yaml, or policy_check.py).
      The full gate is GREEN (selftest, contracts, generated, docs, template sync, pack drift) and RULE
      #1 is clean.
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds one module (.veldo/shape_review.py: the mechanical shape-fit
  findings, the delegated fail-loud ShapeReviewer seam, build_shape_fit, validate_shape_fit, and
  shape_fit_blocks), a call to it from .veldo/validate.py (the verdict shape_fit validation in
  check_json, check_shape_review, and the shape-review CLI mode), a shape-fit read in
  .veldo/dispatch.py's _verdict_passes, an init-scaffold substrate entry, and one capabilities entry,
  all re-synced byte-identical across engine and the 6 packs. A verdict with no shape_fit
  dimension is unaffected either way (adoption safe): shape_fit_blocks returns False, so the merge
  gate behaves exactly as before, and nothing else consumes the dimension. Reverting returns the
  review gate to its prior behavior with no migration and nothing to unwind.
---

## Intent

This is W4 of PLAN-0011, the review-time move of the decay half of the
architecture organ. W1 made the intended shape a versioned, human-approved
contract (.veldo/architecture.yaml); W3 made every spec declare, before anything is
built, its placement (which contract areas the change lands in) and its footprint
(the paths it may touch). This item closes the loop at review: the independent
reviewer receives the contract and the spec's placement alongside the spec, the
final diff, and the proof, and grades a SECOND dimension beyond spec-conformance,
does this change FIT the declared shape. Correct-but-does-not-fit is a legitimate
rework verdict: a change can pass every acceptance criterion and still erode the
architecture, and catching that at review, while construction is still cheap, is
the whole point (D4: a misfit blocks the merge like any blocking finding, from day
one).

The dimension is honestly split. Everything decidable from the contract plus the
declaration plus the diff's paths is MECHANICAL and fails closed: a placement that
does not resolve, a diff that touches outside its declared footprint, a diff whose
areas escape the declared placement, and a diff that couples two areas the contract
does not model with a dependency edge. Whether the change follows the declared
PATTERNS of the areas it touches is a JUDGMENT no mechanical rule can settle, so it
stays in the review lane, graded by a delegated fresh-context reviewer that fails
loud rather than fabricate a verdict (NG5, the same honesty the contract keeps by
marking those patterns review). The machine never lowers: a mechanical misfit forces
does_not_fit even if the reviewer would pass it.

## Context

- Depends on WARP-1101 (shipped): the contract at .veldo/architecture.yaml
  (veldo.arch/v1) and .veldo/arch.py, whose area_for_path, area_ids, and dependency
  graph helpers this item reuses (the one place a path resolves to an area and a
  modeled boundary is defined).
- Depends on WARP-1103 (shipped): the spec's placement and footprint declaration
  and the elaboration-time placement gate. This item grades the BUILT change against
  that same declaration at review time.
- Resolved decision D4: a misfit finding blocks the merge like any blocking finding
  from day one (rework is cheap when construction is cheap). The merge gate
  (dispatch._verdict_passes) consults the shape-fit dimension exactly as it consults
  the policy check's blocking findings.
- The verdict contract (veldo.verdict/v1, validated by validate.py check_json) gains
  a shape_fit block; the delegated reviewer seam mirrors the shipped fail-loud
  pattern of executor.LiveLoop.review and dispatch.LiveReviewer exactly.
- The two postures the plan binds everywhere: adoption safe (a verdict with no
  shape_fit dimension is unaffected, and the mechanical rules stand down with no
  contract) and fail closed (the moment a shape_fit block or a mechanical misfit
  exists it is validated and refuses anything that does not hold).

## Out of scope

- No gate-time footprint-versus-diff enforcement in scripts/verify.sh. Reading the
  footprint and failing the GATE (a red verify.sh) when the built source touches a
  path outside it, and detecting a genuinely new module from the diff, is the
  gate-time shape enforcement WARP-1102 (W2), a protected-path change this item does
  not make. This item grades shape-fit at REVIEW time and carries the judgment in the
  verdict; the merge gate it wires is the non-protected fleet dispatcher.
- No new-module detection from the footprint alone (same boundary W3 states): a glob
  cannot by itself tell a genuinely new path from one the contract does not enumerate.
- No entropy metrics or restoration. Deriving per-area cost-to-change and generating
  restoration specs is WARP-1108/WARP-1109 (W8/W9).
- No fabricated judgment. The pattern-fit judgment is performed by a delegated fresh
  context, never synthesized in code; the reference reviewer fails loud.
- No change to the shipped enforcement core: scripts/verify.sh, veldo-guard.sh,
  .veldo/policy_check.py, .veldo/policy.yaml and their engine twins are
  untouched (protected paths). The shape-fit dimension lives in the non-protected
  engine (.veldo/shape_review.py, .veldo/validate.py, .veldo/dispatch.py) and READS the
  contract and the verdict without editing policy.

## Notes

- Keep .veldo/shape_review.py dependency free (it imports nothing): the arch helpers
  and the failure reporter are passed IN by the caller, so there is no second parser
  and no import cycle, and the mechanical rules reuse arch's one placement and boundary
  implementation.
- Put the merge-gate read in dispatch._verdict_passes (the choke point where a verdict
  lets a change ship), beside the existing blocking-findings read, so the shape-fit
  dimension is a first-class gate and not a coincidence of the reviewer duplicating a
  finding. shape_fit_blocks is pure over the verdict and fails closed on a malformed
  block.
- Follow the byte-identical engine sync discipline: .veldo/shape_review.py, the edited
  .veldo/validate.py and .veldo/dispatch.py, and .veldo/capabilities.yaml land in
  engine and every pack byte-identical, and the drift checks end empty. The
  verdicts themselves are per-repo instance data; this repository carries no real
  verdict for its own head, so its own shape-fit surface is exercised over selftest
  fixtures (the adoption-safe posture).
- Put teeth on each behavior (the anti-vacuity rule C1): a diff outside the placement,
  the footprint, or an unmodeled boundary each turn the mechanical check RED and revert;
  the machine-never-lowers rule turns a reviewer's fits into does_not_fit; the delegated
  reviewer raises; a malformed shape_fit block refuses; and the dispatcher's real verdict
  gate refuses a correct-but-misfit verdict while a fitting one ships (RJ3).
- RULE #1 clean (ASCII hyphen only, no em or en dash, no prose double-hyphen).
