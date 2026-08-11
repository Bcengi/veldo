#!/usr/bin/env python3
"""VELDO security review dimension (WARP-1309, W9 of PLAN-0013).

The independent reviewer grades security ABOVE THE MECHANIZABLE FLOOR, the way the shape-fit lane
grades architecture: the verdict contract carries the finding, and correct-but-insecure is a
legitimate rework verdict.

**WHY A LANE AND NOT MORE CHECKS.** W1 through W8 mechanized what can be settled by a rule: a
literal secret, a wildcard permission, a dependency nobody decided, an unsigned commit. Those are
now floors and they hold without anyone's attention. What they cannot settle is whether a change is
SAFE - whether this endpoint should be reachable by that caller, whether the new code path trusts
something it should not, whether the design gives an attacker a step they did not have yesterday.
That is judgment, so it stays in the review lane and is honestly marked as judgment rather than
dressed up as a check (NG5).

**THE FLOOR IS A FLOOR, NOT A CEILING, AND THE DANGEROUS READER IS THE ONE WHO FORGETS THAT.** A
reviewer shown "secret scan: clean, privilege: clean, dependencies: clean" is being handed a very
comfortable green wall, and the temptation is to grade the rest by vibes. So the context this module
builds says in as many words: these are settled, do NOT re-grade them, grade what is above them, and
here are the four dimensions that live up there.

**THE MACHINE NEVER LOWERS.** Any mechanical finding forces `insecure` no matter what the reviewer
concluded. A reviewer may overrule the machine upward - calling something insecure the floors found
clean is exactly what the lane is for - and never downward.

**FAIL CLOSED AND ADOPTION SAFE, both load bearing.** A malformed security block, an
out-of-vocabulary verdict, or an `insecure` that names no finding each refuse by name. A verdict
carrying no security dimension does not block, so a repository that has not adopted the lane is
byte-identically unaffected.

**THE REFERENCE REVIEWER RAISES.** `LiveSecurityReviewer` is wired to nothing and refuses to
fabricate a judgment, mirroring `LiveShapeReviewer` and the dispatcher's `LiveReviewer`. No security
judgment is ever synthesized in code - a fabricated "looks fine" is worse than an absent one,
because it is indistinguishable from a real one in the record.

Dependency free by construction: the floor modules are passed IN by the caller, so this module
imports nothing, adds no second parser and no import cycle.
"""

SCHEMA = "veldo.security_review/v1"

# The vocabulary. Two values, because a security verdict that can be "mostly" is one nobody acts on.
SECURITY_VERDICTS = {"secure", "insecure"}

# What the reviewer grades, named so the lane is a specific request rather than "have a think about
# security". These are exactly the four the plan names, and they are the four the FLOORS CANNOT
# REACH: each needs to know what the change is FOR.
SECURITY_DIMENSIONS = {
    "secrets_handling": "does anything reach a log, an error, a context or an artifact that should "
                        "not - above the literal-secret floor, which is already enforced",
    "input_trust": "what does this change newly TRUST, and where does that input actually come "
                   "from",
    "privilege_footprint": "what can this component reach that it could not yesterday, and does it "
                           "need to",
    "dependency_delta": "what did this change bring in, transitively, and what does it now run at "
                        "install or build time",
}


class SecurityReviewError(ValueError):
    """Raised when a judgment is malformed or fabricated. Fails loud rather than let it through."""


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def mechanical_security_findings(diff_text=None, infra=None, deps=None, commits=None,
                                 scan=None, privilege=None, supply=None, attribution=None,
                                 registry=None):
    """The floors, re-run at review time, as (dimension, rule, detail).

    Every module here is PASSED IN, so this adds no imports and no second spelling of what a secret
    or a wildcard is. Each floor STANDS DOWN when its module or its input is absent: a repository
    that has not adopted the secret scan gets no secret findings, rather than an error.

    These are re-run at review rather than trusted from the build because a build's own report of
    itself is the one artifact an insecure change has every reason to be wrong about."""
    out = []
    if scan is not None and diff_text:
        for hit in scan.scan_text(diff_text) or []:
            out.append(("secrets_handling", "literal_secret_in_diff", str(hit)))
    if privilege is not None and infra:
        for rule, where, detail in privilege.check(infra):
            out.append(("privilege_footprint", rule, "%s: %s" % (where, detail)))
    if supply is not None and deps:
        for reason, subject, detail in supply.check(**deps):
            out.append(("dependency_delta", reason, "%s: %s" % (subject, detail)))
    if attribution is not None and commits and registry is not None:
        for sha, reason, detail in attribution.check_range(commits, registry):
            out.append(("privilege_footprint", reason, "%s: %s" % (sha[:8], detail)))
    return out


class SecurityReviewer:
    """The fresh-context review seam. `review(spec, context)` returns a mapping carrying a verdict
    from SECURITY_VERDICTS and, when insecure, a finding naming what is unsafe."""

    def review(self, spec, context=None):                # pragma: no cover - interface
        raise NotImplementedError


class LiveSecurityReviewer(SecurityReviewer):
    """The reference reviewer, WIRED TO NOTHING, which RAISES.

    A fabricated judgment is worse than an absent one: in the record it is indistinguishable from a
    real one, and it is the artifact somebody will later point at to show the change was reviewed."""

    def review(self, spec, context=None):
        raise SecurityReviewError(
            "no security reviewer is wired: a real one dispatches a genuinely fresh context over "
            "the built change and returns its judgment. Nothing here fabricates one, because a "
            "fabricated judgment is indistinguishable in the record from a real one")


def security_review_context(mechanical, spec_id=None):
    """What the reviewer is handed. The floors' results, and an explicit instruction NOT to
    re-grade them.

    THIS IS THE PART THAT DECIDES WHETHER THE LANE IS WORTH ANYTHING. A reviewer shown a green wall
    of automated checks grades the rest by vibes, so the context says what is settled, says not to
    re-grade it, and names the four dimensions that live above it."""
    return {
        "schema": SCHEMA,
        "spec_id": spec_id,
        "mechanical": list(mechanical or []),
        "floor_is_settled": [
            "Literal secrets, generated-privilege defaults, dependency decisions and commit "
            "attribution are ALREADY ENFORCED mechanically and are listed above if they failed.",
            "Do NOT re-grade them and do not report a clean floor as a security review.",
            "Grade what is above the floor. A clean floor is the starting point, not the finding.",
        ],
        "grade_these": dict(SECURITY_DIMENSIONS),
        "reminder": "Correct-but-insecure is a legitimate rework verdict. A change can do exactly "
                    "what its spec says and still be one you should not merge.",
    }


def build_security(judgment, mechanical=None):
    """Assemble the `security` block a veldo.verdict/v1 verdict carries.

    THE MACHINE NEVER LOWERS: any mechanical finding forces insecure regardless of the judgment; a
    judgment of insecure is honoured; only a clean floor AND a reviewer verdict of secure yields
    secure. A malformed or fabricated judgment refuses by name, so the delegated seam fails loud."""
    jv = (judgment or {}).get("verdict")
    if jv not in SECURITY_VERDICTS:
        raise SecurityReviewError(
            "security judgment must carry a verdict from %s (got %r): a real fresh-context reviewer "
            "returns its judgment, and a missing or out-of-vocabulary one is refused, never "
            "fabricated" % (sorted(SECURITY_VERDICTS), jv))
    mech = list(mechanical or [])
    return {
        "verdict": "insecure" if (mech or jv == "insecure") else "secure",
        "mechanical": mech,
        "review": {"verdict": jv, "finding": (judgment or {}).get("finding"),
                   "dimensions": sorted((judgment or {}).get("dimensions") or [])},
    }


def validate_security(block, where, fail):
    """Structural validation of a `security` block. Reports through fail(where, msg) and returns the
    error count. Pure over the block, so validate.py reuses it without a second parser.

    Fails closed by name on: a non-mapping block, an out-of-vocabulary verdict, a non-list
    mechanical list, a malformed review sub-block, a dimension outside the vocabulary, and an
    INSECURE THAT NAMES NO FINDING - a rework verdict that does not say what is unsafe sends the
    builder back with nothing to fix, which is how a lane becomes a formality."""
    if not isinstance(block, dict):
        return fail(where, "security must be a mapping {verdict, mechanical, review}")
    errs = 0
    v = block.get("verdict")
    if v not in SECURITY_VERDICTS:
        errs += fail(where, "security.verdict must be one of %s (got %r)"
                     % (sorted(SECURITY_VERDICTS), v))
    mech = block.get("mechanical")
    if mech is not None and not isinstance(mech, list):
        errs += fail(where, "security.mechanical must be a list of findings")
    review = block.get("review")
    if review is not None:
        if not isinstance(review, dict):
            errs += fail(where, "security.review must be a mapping {verdict, finding, dimensions}")
        else:
            rv = review.get("verdict")
            if rv is not None and rv not in SECURITY_VERDICTS:
                errs += fail(where, "security.review.verdict must be one of %s (got %r)"
                             % (sorted(SECURITY_VERDICTS), rv))
            dims = review.get("dimensions")
            if dims is not None:
                if not isinstance(dims, list):
                    errs += fail(where, "security.review.dimensions must be a list")
                else:
                    for d in dims:
                        if d not in SECURITY_DIMENSIONS:
                            errs += fail(where, "security.review.dimensions member %r is outside "
                                                "the vocabulary %s"
                                         % (d, sorted(SECURITY_DIMENSIONS)))
    if v == "insecure":
        has_mech = isinstance(mech, list) and len(mech) > 0
        has_review = isinstance(review, dict) and _is_str(review.get("finding"))
        if not (has_mech or has_review):
            errs += fail(where, "security.verdict is insecure but no finding is recorded: a rework "
                                "verdict that does not say what is unsafe sends the builder back "
                                "with nothing to fix")
    return errs


def security_blocks(verdict):
    """Whether the security dimension of a verdict BLOCKS the merge. Pure over the verdict mapping,
    read by the merge gate:
      - no security dimension does not block (adoption safe: an unreviewed-for-security verdict is
        byte-identically unaffected);
      - an insecure dimension blocks, so the spec returns for rework;
      - a MALFORMED block or an out-of-vocabulary verdict blocks (fail closed: an unreadable
        security dimension is never shipped)."""
    block = (verdict or {}).get("security")
    if block is None:
        return False
    if not isinstance(block, dict):
        return True
    v = block.get("verdict")
    if v not in SECURITY_VERDICTS:
        return True
    return v == "insecure"


# The dimension interface both review lanes implement, so the verdict validator and the merge gate
# wire a new dimension without either of them learning its name.
validate_dimension = validate_security
dimension_blocks = security_blocks
