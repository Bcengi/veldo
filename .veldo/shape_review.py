#!/usr/bin/env python3
"""VELDO shape-fit review dimension (the shape_fit block of veldo.verdict/v1): the
independent review grades a SECOND dimension beyond spec-conformance, does this
change FIT the declared architecture shape, and correct-but-does-not-fit is a
legitimate rework verdict.

This is the W4 organ of PLAN-0011 and the fourth move of the decay half of the
method's "The Shape of the System" invention. W1 made the shape a contract
(.veldo/architecture.yaml), W3 made every spec declare its placement and footprint
before anything is built, and this item grades the built change against that
declaration at review time: the reviewer receives the contract and the spec's
placement alongside the spec, the final diff, and the proof, and returns a
shape-fit judgment the verdict carries. A misfit blocks the merge like any
blocking finding (D4, from day one, because rework is cheap while construction
is cheap).

The dimension has a MECHANICAL half and a DELEGATED half, honestly split:

  MECHANICAL, and fail closed. mechanical_shape_findings decides, from the
  contract plus the spec's placement/footprint plus the diff's paths alone, the
  shape-fit rules that need no judgment: a placement area that does not resolve
  to a declared area; a diff path outside the declared footprint (a change may
  not silently touch a path it never declared); a diff path resolving to a
  declared area outside the declared placement (the footprint does not stay
  within the declared areas); and a diff that couples two declared areas with no
  allow-listed dependency edge between them (an unmodeled boundary crossing the
  contract does not sanction). Every one of these is settled by the declaration
  and the contract's edges, so it is enforced by code and fails closed. The rules
  reuse .veldo/arch.py's area_for_path, area_ids, and the dependency-graph helpers
  (the one place a path is mapped to an area and a modeled boundary is defined),
  so there is no second placement or boundary implementation.

  DELEGATED, and fail loud. Whether the change follows the declared PATTERNS of
  the areas it touches is a judgment no mechanical rule can settle, so it stays in
  the review lane exactly as the contract marks those patterns review, never a
  vacuous mechanized check (NG5). ShapeReviewer.review is the fresh-context seam;
  the reference LiveShapeReviewer is wired to nothing and RAISES rather than
  fabricate a judgment, mirroring the executor's LiveLoop.review and the
  dispatcher's LiveReviewer. No shape-fit judgment is synthesized in code.

build_shape_fit assembles the shape_fit block the verdict carries from the two
halves, and the MACHINE NEVER LOWERS: any mechanical misfit forces does_not_fit
regardless of the delegated judgment; a judgment of does_not_fit is honored; only
a clean mechanical result AND a reviewer verdict of fits yields fits. shape_fit_blocks
is the merge gate's read of the dimension: a does_not_fit blocks, a malformed block
blocks (fail closed), and a verdict with no shape_fit dimension does not block
(adoption safe, an unreviewed-for-shape verdict is byte-identically unaffected).

Two postures, both load bearing and shared with the sibling organs:
  ADOPTION SAFE. A verdict with no shape_fit dimension does not block, and every
  mechanical rule stands down when no contract is passed, so nothing here changes
  a repository that has not adopted a contract.
  FAIL CLOSED. A malformed shape_fit block, an out-of-vocabulary shape verdict, a
  does_not_fit that names no finding, and a fabricated or malformed judgment each
  refuse by name.

Dependency free by construction: the arch helpers (the one place placement and the
boundary graph are read) and the failure reporter are passed IN by the caller
(.veldo/validate.py, .veldo/dispatch.py), so this module imports nothing and adds no
second parser and no import cycle. Enforcing the declared footprint against the diff
as a red GATE check in scripts/verify.sh is the separate gate-time organ WARP-1102
(W2), a protected-path change this item does not make; this item grades shape-fit at
review time and carries the judgment in the verdict.
"""

SCHEMA = "veldo.shape_review/v1"
# The shape-fit verdict vocabulary, carried in the shape_fit block of a veldo.verdict/v1
# verdict. does_not_fit is a legitimate rework outcome even when the change is correct.
SHAPE_FIT_VERDICTS = {"fits", "does_not_fit"}


class ShapeReviewError(ValueError):
    """A shape-fit judgment is malformed, or the reviewer is not wired. Raised by name
    so a bad judgment never silently no-ops and the delegated reviewer never fabricates
    a judgment (parallels DecisionReviewError and the executor's ExecutorError)."""


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _as_list(v):
    return v if isinstance(v, list) else []


def declared_placement(fm):
    """The placement area ids a spec declares (the areas the change lands in), as a
    list of non-empty strings. The one place a spec's placement is read here."""
    return [a for a in _as_list((fm or {}).get("placement")) if _is_str(a)]


def declared_footprint(fm):
    """The footprint path globs a spec declares (the paths the change may touch), as a
    list of non-empty strings. The one place a spec's footprint is read here."""
    return [g for g in _as_list((fm or {}).get("footprint")) if _is_str(g)]


def diff_areas(changed_paths, contract, arch):
    """The set of declared contract areas the diff's paths actually touch, mapped through
    arch.area_for_path (the one place a path is resolved to its area). A path that matches
    no area's includes lies outside the declared shape and contributes no area."""
    hit = set()
    for p in _as_list(changed_paths):
        if _is_str(p):
            hit |= arch.area_for_path(p, contract)
    return hit


def _path_in_footprint(path, globs, arch):
    """Whether a diff path is covered by any declared footprint glob, using arch._glob_re
    (the one glob compiler the contract's includes use), so footprint coverage and area
    resolution agree on what a glob matches rather than re-deriving it."""
    return any(arch._glob_re(g).match(path) for g in globs if _is_str(g))


def mechanical_shape_findings(fm, contract, changed_paths, arch):
    """The mechanizable shape-fit findings for a change, from the contract plus the spec's
    placement/footprint plus the diff's paths alone. Returns a list of finding strings,
    empty iff the change fits the mechanizable shape rules. Pure over the inputs (no I/O),
    so it is trivially gate-tested. Each rule is settled by the declaration and the contract
    edges, never by taste, so it is enforced here and fails closed; the pattern-fit judgment
    that needs taste is the delegated reviewer's, not this function's.

    The rules, in order:
      1. every placement area resolves to a declared contract area;
      2. every diff path is covered by the declared footprint (a change may not silently
         touch a path it never declared);
      3. every diff path that resolves to a declared area lands in the declared placement
         (the footprint stays within the declared areas);
      4. the declared areas the diff touches contain no pair without an allow-listed
         dependency edge between them (no unmodeled boundary crossing)."""
    findings = []
    placement = declared_placement(fm)
    footprint = declared_footprint(fm)
    known = arch.area_ids(contract)
    placed = set(placement)

    for aid in placement:
        if aid not in known:
            findings.append(
                "placement area %r does not resolve to a declared contract area "
                "(referenced but absent)" % aid)

    for path in _as_list(changed_paths):
        if not _is_str(path):
            continue
        if footprint and not _path_in_footprint(path, footprint, arch):
            findings.append(
                "the diff touches %r, outside the declared footprint: a change may not "
                "silently touch a path it did not declare" % path)
        for a in sorted(arch.area_for_path(path, contract)):
            if a not in placed:
                findings.append(
                    "the diff touches area %r (path %r) outside the declared placement %s: "
                    "the footprint does not stay within the declared areas"
                    % (a, path, sorted(placed)))

    touched = sorted(diff_areas(changed_paths, contract, arch))
    edges = arch._allowed_edges(contract)
    for i in range(len(touched)):
        for j in range(i + 1, len(touched)):
            if not arch._areas_connected(touched[i], touched[j], edges):
                findings.append(
                    "the diff couples areas %r and %r with no allow-listed dependency edge "
                    "between them in either direction: an unmodeled boundary crossing the "
                    "contract does not sanction" % (touched[i], touched[j]))
    return findings


class ShapeReviewer:
    """The fresh-context shape-fit review seam. review(spec, context) returns the pattern-fit
    JUDGMENT the mechanical rules cannot settle: whether the change follows the declared
    patterns of the areas it touches, as a mapping {verdict: fits|does_not_fit, finding: str}.
    A concrete reviewer dispatches a genuinely fresh context over the contract, the spec's
    placement, the final diff, and the proof; this module talks only to this interface, so a
    judgment is never fabricated in code and the reference cannot pretend to have graded fit."""

    def review(self, spec, context=None):
        raise NotImplementedError


class LiveShapeReviewer(ShapeReviewer):
    """Reference shape-fit reviewer wired to nothing. Fails LOUD: an adopting runtime must
    inject a reviewer that dispatches a genuinely fresh context over the contract, the spec's
    placement, the final diff, and the proof, and returns its pattern-fit judgment. Refusing
    to fabricate a judgment is the honest default, exactly as the executor's LiveLoop.review
    and the dispatcher's LiveReviewer refuse to fabricate a verdict."""

    def review(self, spec, context=None):
        raise ShapeReviewError(
            "shape-fit review is a delegated fresh-context step; no reviewer is wired. Inject "
            "a reviewer that dispatches a genuinely fresh context over the contract, the spec's "
            "placement, the final diff, and the proof, and returns its pattern-fit judgment "
            "(does this change follow the declared patterns of the areas it touches). The "
            "mechanizable shape rules are graded by mechanical_shape_findings; this is the "
            "judgment half. Refusing to fabricate a shape-fit judgment.")


def shape_review_context(fm, contract, changed_paths, arch):
    """What the delegated reviewer receives alongside the spec, the final diff, and the proof:
    the contract's declared areas, the spec's declared placement and footprint, the areas the
    final diff actually touched, and the mechanically-decided shape-fit findings. The reviewer
    grades the pattern-fit dimension on top of these mechanical facts; the mechanical facts it
    cannot override (build_shape_fit enforces that the machine never lowers)."""
    return {
        "schema": SCHEMA,
        "areas": sorted(arch.area_ids(contract)),
        "placement": declared_placement(fm),
        "footprint": declared_footprint(fm),
        "diff_areas": sorted(diff_areas(changed_paths, contract, arch)),
        "mechanical_findings": mechanical_shape_findings(fm, contract, changed_paths, arch),
    }


def build_shape_fit(fm, contract, changed_paths, judgment, arch):
    """Assemble the shape_fit block a veldo.verdict/v1 verdict carries, from the mechanical
    shape-fit findings and the delegated reviewer's pattern-fit judgment. The MACHINE NEVER
    LOWERS: any mechanical misfit forces does_not_fit regardless of the judgment, a judgment
    of does_not_fit is honored, and only a clean mechanical result AND a reviewer verdict of
    fits yields fits.

    The judgment is the mapping a real ShapeReviewer returned; it must carry a verdict from
    SHAPE_FIT_VERDICTS, and a malformed or fabricated judgment (missing or out-of-vocabulary
    verdict) is refused by name (ShapeReviewError), so the delegated seam fails loud rather
    than let a garbage judgment through."""
    jverdict = (judgment or {}).get("verdict")
    if jverdict not in SHAPE_FIT_VERDICTS:
        raise ShapeReviewError(
            "shape-fit judgment must carry a verdict from %s (got %r): a real fresh-context "
            "reviewer returns its pattern-fit verdict; a missing or out-of-vocabulary one is "
            "refused, never fabricated" % (sorted(SHAPE_FIT_VERDICTS), jverdict))
    mech = mechanical_shape_findings(fm, contract, changed_paths, arch)
    verdict = "does_not_fit" if (mech or jverdict == "does_not_fit") else "fits"
    return {
        "verdict": verdict,
        "mechanical": mech,
        "review": {"verdict": jverdict, "finding": (judgment or {}).get("finding")},
    }


def validate_shape_fit(block, where, fail):
    """Structural validation of a shape_fit block carried in a veldo.verdict/v1 verdict. Reports
    each problem through fail(where, msg) and returns the error count. Fails closed by name on a
    non-mapping block, an out-of-vocabulary shape_fit.verdict, a non-list mechanical findings
    list, a malformed review sub-block or an out-of-vocabulary review verdict, and a does_not_fit
    dimension that records no finding at all (a misfit must name what does not fit). Pure over
    the block, so validate.py reuses it from the verdict check without a second parser."""
    if not isinstance(block, dict):
        return fail(where, "shape_fit must be a mapping {verdict, mechanical, review}")
    errs = 0
    v = block.get("verdict")
    if v not in SHAPE_FIT_VERDICTS:
        errs += fail(where, "shape_fit.verdict must be one of %s (got %r)" % (sorted(SHAPE_FIT_VERDICTS), v))
    mech = block.get("mechanical")
    if mech is not None and not isinstance(mech, list):
        errs += fail(where, "shape_fit.mechanical must be a list of findings")
    review = block.get("review")
    if review is not None:
        if not isinstance(review, dict):
            errs += fail(where, "shape_fit.review must be a mapping {verdict, finding}")
        elif review.get("verdict") is not None and review.get("verdict") not in SHAPE_FIT_VERDICTS:
            errs += fail(where, "shape_fit.review.verdict must be one of %s (got %r)" % (sorted(SHAPE_FIT_VERDICTS), review.get("verdict")))
    if v == "does_not_fit":
        has_mech = isinstance(mech, list) and len(mech) > 0
        has_review = isinstance(review, dict) and _is_str(review.get("finding"))
        if not (has_mech or has_review):
            errs += fail(where, "shape_fit.verdict is does_not_fit but no finding is recorded: a misfit must name what does not fit (mechanical or review)")
    return errs


def shape_fit_blocks(verdict):
    """Whether the shape-fit dimension of a verdict BLOCKS the merge (D4: a misfit blocks like
    any blocking finding). A PURE predicate over the verdict mapping, read by the merge gate:
      - a verdict with no shape_fit dimension does not block (adoption safe: a verdict that was
        never shape-reviewed is byte-identically unaffected);
      - a does_not_fit dimension blocks;
      - a MALFORMED shape_fit block, or an out-of-vocabulary shape verdict, blocks (fail closed:
        an unreadable shape dimension is never shipped, mirroring policy_check.blocking_findings)."""
    block = (verdict or {}).get("shape_fit")
    if block is None:
        return False
    if not isinstance(block, dict):
        return True
    v = block.get("verdict")
    if v not in SHAPE_FIT_VERDICTS:
        return True
    return v == "does_not_fit"


# The dimension interface both review lanes implement (PLAN-0013 W9), so the verdict validator and
# the merge gate wire a new review dimension without either of them learning its name.
validate_dimension = validate_shape_fit
dimension_blocks = shape_fit_blocks
