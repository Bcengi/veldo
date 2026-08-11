#!/usr/bin/env python3
"""VELDO adversarial decision review (veldo.decision_review/v1): a foundational choice
is ATTACKED by a fresh context before a human commits to it, and its structural
validator, its binding to the decision it reviews, the delegated fail-loud reviewer
seam, and the gate that lets a decision move to `decided` only once a recorded
adversarial review exists for it.

This is the W6 organ of PLAN-0011 and the third move of the method's "wrong
foundations" invention. WARP-1105 made a foundational choice a first-class decision
RECORD (the option space, each option's dead-end condition, the reversal-cost class
and the assumptions that become living tripwires) but shipped only a DRAFT example,
because a record cannot legitimately move to `decided` until its framing has been
attacked. This module is that attack: a readable review under .veldo/decision_reviews/
that binds to a decision and records the adversarial findings against its framing:

  PROBLEM-CLASS CHALLENGE. Is the problem_class stated honestly, judged against the
  problem class rather than anchored to today's scale (constraint C6)?
  PER-OPTION CHALLENGE. Does each option's dead_end actually hold, where and when?
  MISSING OPTIONS. Is a better option missing that the framing did not consider?
  PER-ASSUMPTION CHALLENGE. Are the recorded assumptions the real load-bearing ones?

The review produces a recommendation and a disposition for the HUMAN to read. W6
INFORMS the decision; it never makes it (O4, NG2). A review may not carry a chosen
option or a decider: it is not a decision, and the structural check refuses one that
smuggles a decision field.

Three properties are load bearing and enforced fail closed:

  A REVIEW BINDS TO A DECISION. bind_review resolves the referenced decision (by id,
  schema veldo.decision/v1) and refuses a review whose decision is malformed or absent,
  whose decision_version does not match the record's current version (a stale review
  does not vouch for the current framing), or whose challenges do not COVER every option
  and every assumption the decision declares (a partial attack is not an attack on the
  framing).

  THE REVIEWER IS DELEGATED AND FAILS LOUD. The adversarial attack is performed by a
  genuinely fresh context, mirroring the executor's LiveLoop.review and the dispatcher's
  LiveReviewer. LiveAdversarialReviewer is wired to nothing and RAISES rather than
  fabricate an attack. No review's findings, disposition, or recommendation are ever
  synthesized in code.

  SCRUTINY SCALES WITH REVERSAL COST (D5). decided_requires_review refuses a decision
  whose status is `decided` unless it carries at least the number of bound, valid
  adversarial reviews its risk tier requires, read from .veldo/policy.yaml risk_tiers (the
  single source of truth). W5 mapped irreversible to the critical tier; critical requires
  two independent reviews, a standard tier one. A decided record with fewer bound reviews
  than its tier requires is refused: this is the gate W6 adds to W5.

The in-session TRIPWIRE pass that monitors each assumption's signal for an approaching
breach after the decision is WARP-1107 (W7), honestly a later item; nothing here
pretends to do its work.

Two postures, both shared with the record organ:
  ADOPTION SAFE. A repository with no .veldo/decisions/ directory is untouched:
  check_reviews stands down and returns clean, so adding this module changes no existing
  gate. The moment a review or a decided record exists it is validated and fails closed.
  FAIL CLOSED. A malformed review, an out-of-vocabulary disposition or verdict, a
  challenge missing its finding, a review that smuggles a decision, a review that does not
  resolve or cover its decision, or a decided record with too few bound reviews each refuse
  by name.

Dependency free by construction: the caller (.veldo/validate.py) passes in the front-matter
parser, the failure reporter, and the decision loader (.veldo/decision.py's load_record, the
one place a decision record is read), so this module adds no second YAML parser and no
import cycle.
"""
import re
from pathlib import Path

SCHEMA = "veldo.decision_review/v1"
DISPOSITIONS = {"defensible", "reframe", "refuted"}
PROBLEM_CLASS_VERDICTS = {"honest", "anchored_to_scale"}
DEAD_END_VERDICTS = {"holds", "does_not_hold"}
ASSUMPTION_VERDICTS = {"load_bearing", "not_load_bearing"}
# Fields a decision RECORD carries when a human has decided (see decision.py). A review
# is not a decision, so a review carrying any of these smuggles a decision and is refused.
DECISION_FIELDS = ("chosen", "decided_by", "decided_at")
DECISION_SCHEMA = "veldo.decision/v1"


class DecisionReviewError(ValueError):
    """A decision review is malformed, or the reviewer is not wired. Raised by name so a
    bad review never silently no-ops, and the delegated reviewer never fabricates an
    attack (parallels DecisionRecordError and the executor's ExecutorError)."""


def default_reviews_dir(root=None):
    return Path(root or ".") / ".veldo" / "decision_reviews"


def default_decisions_dir(root=None):
    return Path(root or ".") / ".veldo" / "decisions"


def load_review(path, parse):
    """Parse the review at path into a dict using the caller's front-matter parser (the
    VELDO yamlish subset), raising DecisionReviewError on unreadable or unparseable input.
    The single place a review is read, so a later consumer reuses it rather than parsing
    the file a second way."""
    p = Path(path)
    try:
        text = p.read_text()
    except OSError as e:
        raise DecisionReviewError("decision review unreadable: %s" % e)
    try:
        data = parse(text)
    except ValueError as e:
        raise DecisionReviewError("decision review outside the review subset: %s" % e)
    if not isinstance(data, dict):
        raise DecisionReviewError("decision review must be a mapping at the top level")
    return data


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _as_list(v):
    return v if isinstance(v, list) else []


def _is_pos_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 1


def _challenge_refs(challenges, key):
    """The list of referenced ids for a challenge block (option or assumption), skipping
    malformed entries (reported separately)."""
    out = []
    for c in _as_list(challenges):
        if isinstance(c, dict) and _is_str(c.get(key)):
            out.append(c[key])
    return out


def validate_review(data, root, review_path, fail):
    """Structural validation of one parsed veldo.decision_review/v1 review. Reports each
    problem through fail(name, msg) and returns the error count. Pure over the dict (no
    filesystem access), so it is trivially reused by the directory scan and the single-file
    entry point. This checks the review is well formed; binding it to its decision is
    bind_review, and the decided-requires-review gate is decided_requires_review."""
    errs = 0
    name = str(review_path)

    if data.get("schema") != SCHEMA:
        errs += fail(name, "schema must be %r (got %r)" % (SCHEMA, data.get("schema")))
    for field in ("id", "decision", "reviewer", "recommendation"):
        if not _is_str(data.get(field)):
            errs += fail(name, "missing or empty required field: %s" % field)
    if not _is_pos_int(data.get("version")):
        errs += fail(name, "version must be an integer >= 1: a decision review is versioned")
    if not _is_pos_int(data.get("decision_version")):
        errs += fail(name, "decision_version must be an integer >= 1: a review binds to the exact decision version it reviewed")

    disposition = data.get("disposition")
    if disposition not in DISPOSITIONS:
        errs += fail(name, "disposition must be one of %s (got %r): the adversarial outcome, advisory to the human, never a decision" % (sorted(DISPOSITIONS), disposition))

    # A review is NOT a decision: it informs the human and never decides (O4, NG2). A
    # review that smuggles a chosen option or a decider is refused, so no decision can be
    # made under cover of a review.
    for f in DECISION_FIELDS:
        if data.get(f) is not None:
            errs += fail(name, "a review must not carry %s: a decision review informs the human and never decides (O4, NG2)" % f)

    # The problem-class challenge: is the problem class stated honestly, judged against the
    # problem class and not anchored to today's scale (C6). A mapping with a verdict from a
    # closed vocabulary and a finding.
    pcc = data.get("problem_class_challenge")
    if not isinstance(pcc, dict):
        errs += fail(name, "problem_class_challenge is required: a mapping with a verdict (%s) and a finding" % sorted(PROBLEM_CLASS_VERDICTS))
    else:
        if pcc.get("verdict") not in PROBLEM_CLASS_VERDICTS:
            errs += fail(name, "problem_class_challenge.verdict must be one of %s (got %r)" % (sorted(PROBLEM_CLASS_VERDICTS), pcc.get("verdict")))
        if not _is_str(pcc.get("finding")):
            errs += fail(name, "problem_class_challenge.finding is required (what the attack found about the framing)")

    # The per-option challenge: a non-empty list, each naming an option and judging whether
    # that option's dead_end holds, with a finding. A review that challenges no option is
    # not an adversarial review (the anti-vacuity move for the attack).
    ocs = _as_list(data.get("option_challenges"))
    if not ocs:
        errs += fail(name, "no option_challenges: an adversarial review attacks each option's dead_end; a review that challenges nothing is not a review")
    for oc in ocs:
        if not isinstance(oc, dict) or not _is_str(oc.get("option")):
            errs += fail(name, "each option_challenge needs an option id")
            continue
        if oc.get("dead_end_verdict") not in DEAD_END_VERDICTS:
            errs += fail(name, "option_challenge %s: dead_end_verdict must be one of %s (got %r)" % (oc.get("option"), sorted(DEAD_END_VERDICTS), oc.get("dead_end_verdict")))
        if not _is_str(oc.get("finding")):
            errs += fail(name, "option_challenge %s: a finding is required (does this option's dead_end hold, where and when)" % oc.get("option"))
    oc_refs = _challenge_refs(ocs, "option")
    for oid in sorted(set(oc_refs)):
        if oc_refs.count(oid) > 1:
            errs += fail(name, "duplicate option_challenge for %r" % oid)

    # Missing options: candidate options the framing did not consider. The field is required
    # (a review states, even if empty, that it looked for a missing option), but the list may
    # be empty (no better option found). Each present entry needs a summary and a finding.
    mos = data.get("missing_options")
    if mos is None or not isinstance(mos, list):
        errs += fail(name, "missing_options is required as a list (use [] to record that no better option was found)")
    else:
        for mo in mos:
            if not isinstance(mo, dict) or not _is_str(mo.get("summary")) or not _is_str(mo.get("finding")):
                errs += fail(name, "each missing_options entry needs a summary and a finding (a candidate the framing omitted and why it may be better)")

    # The per-assumption challenge: a non-empty list, each naming an assumption and judging
    # whether it is a real load-bearing one, with a finding.
    acs = _as_list(data.get("assumption_challenges"))
    if not acs:
        errs += fail(name, "no assumption_challenges: an adversarial review attacks whether the recorded assumptions are the real load-bearing ones")
    for ac in acs:
        if not isinstance(ac, dict) or not _is_str(ac.get("assumption")):
            errs += fail(name, "each assumption_challenge needs an assumption id")
            continue
        if ac.get("verdict") not in ASSUMPTION_VERDICTS:
            errs += fail(name, "assumption_challenge %s: verdict must be one of %s (got %r)" % (ac.get("assumption"), sorted(ASSUMPTION_VERDICTS), ac.get("verdict")))
        if not _is_str(ac.get("finding")):
            errs += fail(name, "assumption_challenge %s: a finding is required (is this the real load-bearing assumption)" % ac.get("assumption"))
    ac_refs = _challenge_refs(acs, "assumption")
    for aid in sorted(set(ac_refs)):
        if ac_refs.count(aid) > 1:
            errs += fail(name, "duplicate assumption_challenge for %r" % aid)

    return errs


def bind_review(review, decision, where, fail):
    """Cross-artifact binding: pair a review to the decision it reviews and FAIL CLOSED if
    the record is malformed or absent. Pure over the two dicts.

    decision is the parsed veldo.decision/v1 record the review's `decision` id resolves to,
    or None when it could not be resolved. A review whose decision is None is refused
    (referenced but absent). Otherwise the review must bind to the exact version reviewed
    (decision_version == the record's version) and its challenges must COVER every option
    and every assumption the decision declares and reference none it does not: a partial
    attack, or an attack on an option the framing never offered, does not bind."""
    errs = 0
    if not isinstance(decision, dict):
        return fail(where, "review references decision %r which is malformed or absent (referenced but absent, fail closed)" % review.get("decision"))

    dv = review.get("decision_version")
    rv = decision.get("version")
    if _is_pos_int(dv) and _is_pos_int(rv) and dv != rv:
        errs += fail(where, "decision_version %r does not match decision %r version %r: a stale review does not vouch for the current framing" % (dv, review.get("decision"), rv))

    declared_options = {o.get("id") for o in _as_list(decision.get("options"))
                        if isinstance(o, dict) and _is_str(o.get("id"))}
    reviewed_options = set(_challenge_refs(_as_list(review.get("option_challenges")), "option"))
    for extra in sorted(reviewed_options - declared_options):
        errs += fail(where, "option_challenge references option %r the decision does not declare (referenced but absent)" % extra)
    for missing in sorted(declared_options - reviewed_options):
        errs += fail(where, "option %r is not challenged: an adversarial review must attack every option in the framing" % missing)

    declared_asm = {a.get("id") for a in _as_list(decision.get("assumptions"))
                    if isinstance(a, dict) and _is_str(a.get("id"))}
    reviewed_asm = set(_challenge_refs(_as_list(review.get("assumption_challenges")), "assumption"))
    for extra in sorted(reviewed_asm - declared_asm):
        errs += fail(where, "assumption_challenge references assumption %r the decision does not declare (referenced but absent)" % extra)
    for missing in sorted(declared_asm - reviewed_asm):
        errs += fail(where, "assumption %r is not challenged: an adversarial review must attack every recorded assumption" % missing)

    return errs


class AdversarialReviewer:
    """The fresh-context adversarial review seam. review(decision, context) returns a
    review mapping (a veldo.decision_review/v1 artifact) that attacks the proposed decision's
    framing. A concrete reviewer dispatches a genuinely fresh context over the decision; this
    module talks only to this interface, so a review is never fabricated in code and the
    reference cannot pretend to have attacked anything."""

    def review(self, decision, context=None):
        raise NotImplementedError


class LiveAdversarialReviewer(AdversarialReviewer):
    """Reference adversarial reviewer wired to nothing. Fails LOUD: an adopting runtime must
    inject a reviewer that dispatches a genuinely fresh context over the proposed decision and
    returns its attack. Refusing to fabricate a review is the honest default, exactly as the
    executor's LiveLoop.review and the dispatcher's LiveReviewer refuse to fabricate a verdict."""

    def review(self, decision, context=None):
        raise DecisionReviewError(
            "adversarial decision review is a delegated fresh-context step; no reviewer is "
            "wired. Inject a reviewer that dispatches a genuinely fresh context over the "
            "proposed decision and returns its attack (problem-class, per-option, missing-option, "
            "and per-assumption challenges plus a recommendation and a disposition). Refusing to "
            "fabricate a review.")


def required_reviews_for(risk, policy_path):
    """The number of independent adversarial reviews a decision at this risk tier requires,
    read from .veldo/policy.yaml risk_tiers (the single source of truth for the tier ladder,
    D5). Defaults to 1 (the floor: any decided decision needs at least one adversarial review)
    when the tier or the policy file is absent, never 0, so a decided record can never pass with
    no review. Proportionate line reader, the same posture policy_check.py uses: each tier is a
    line "  <tier>: {..., reviews: N, ...}" inside the risk_tiers block."""
    default = 1
    try:
        text = Path(policy_path).read_text()
    except OSError:
        return default
    in_block = False
    for line in text.splitlines():
        if re.match(r"^risk_tiers:\s*$", line):
            in_block = True
            continue
        if in_block:
            if line and not line[0].isspace() and not line.startswith("#"):
                break  # a non-indented line ends the risk_tiers block
            m = re.match(r"^\s{2}(\w+):\s*\{.*\breviews:\s*(\d+)", line)
            if m and m.group(1) == risk:
                return int(m.group(2))
    return default


def resolve_decision(decision_id, decisions_dir, parse, load_decision):
    """The parsed veldo.decision/v1 record whose id is decision_id under decisions_dir, or
    None when none resolves. Reads each record through the injected load_decision (decision.py's
    load_record, the one place a record is read), and matches on the decision schema and id so a
    review-shaped file in the tree is never mistaken for a decision."""
    d = Path(decisions_dir)
    if not d.is_dir():
        return None
    for p in sorted(d.glob("*.yaml")):
        try:
            data = load_decision(p, parse)
        except Exception:
            continue
        if isinstance(data, dict) and data.get("schema") == DECISION_SCHEMA and data.get("id") == decision_id:
            return data
    return None


def _valid_bound_reviews_by_decision(reviews_dir, decisions_dir, root, parse, fail, load_decision):
    """The set of decision ids that carry at least one STRUCTURALLY VALID and BOUND review,
    mapped to the count of such reviews. A review counts for a decision only when it validates
    structurally AND binds (resolves, version matches, full coverage) with zero errors, so the
    decided-requires-review gate cannot be satisfied by a malformed or partial review. Errors are
    reported through fail as a side effect (the reviews are validated here, once)."""
    counts = {}
    errs = 0
    d = Path(reviews_dir)
    if not d.is_dir():
        return counts, errs
    ids = {}
    for p in sorted(d.glob("*.yaml")):
        try:
            data = load_review(p, parse)
        except DecisionReviewError as e:
            errs += fail(str(p), str(e))
            continue
        rid = data.get("id")
        if _is_str(rid):
            ids.setdefault(rid, []).append(p.name)
        v = validate_review(data, root, p, fail)
        decision = resolve_decision(data.get("decision"), decisions_dir, parse, load_decision)
        b = bind_review(data, decision, str(p), fail)
        errs += v + b
        if v == 0 and b == 0:
            counts[data.get("decision")] = counts.get(data.get("decision"), 0) + 1
    for rid, files in sorted(ids.items()):
        if len(files) > 1:
            errs += fail(str(d), "duplicate decision review id %r across reviews: %s" % (rid, ", ".join(sorted(files))))
    return counts, errs


def decided_requires_review(decisions_dir, bound_counts, root, parse, fail, required_for, load_decision):
    """The gate W6 adds to W5: a decision may move to `decided` only once a recorded adversarial
    review exists for it, and scrutiny scales with reversal cost (D5). For each decision record
    whose status is `decided`, require at least required_for(risk) bound, valid reviews (the tier's
    reviews count from policy risk_tiers), and REFUSE a decided record with fewer. bound_counts is
    the per-decision count of valid bound reviews computed once by the reviews scan. Pure over the
    filesystem read of the decisions dir; the counting and policy read are injected."""
    errs = 0
    d = Path(decisions_dir)
    if not d.is_dir():
        return 0
    for p in sorted(d.glob("*.yaml")):
        try:
            data = load_decision(p, parse)
        except Exception:
            continue  # a malformed record is reported by decision.check_decisions_dir, not here
        if not isinstance(data, dict) or data.get("status") != "decided":
            continue
        did = data.get("id")
        risk = data.get("risk")
        need = required_for(risk)
        have = bound_counts.get(did, 0)
        if have < need:
            errs += fail(str(p), "decision %r is decided but carries %d bound adversarial review(s); its risk tier %r requires %d (a foundational choice is decided only after it is adversarially reviewed, and scrutiny scales with reversal cost, D5)" % (did, have, risk, need))
    return errs


def check_review(path, root, required, parse, fail, decisions_dir=None, load_decision=None):
    """Single-file entry point. Absent file: stand down (adoption safe) unless it is required,
    in which case fail closed (referenced but absent). Present file: parse and validate
    structurally, and when a decisions_dir and a load_decision are supplied also bind it to its
    decision, failing closed on anything malformed or unbound."""
    p = Path(path)
    if not p.is_file():
        if required:
            return fail(str(p), "decision review is referenced as required but absent (fail closed)")
        return 0
    try:
        data = load_review(p, parse)
    except DecisionReviewError as e:
        return fail(str(p), str(e))
    errs = validate_review(data, root, p, fail)
    if decisions_dir is not None and load_decision is not None:
        decision = resolve_decision(data.get("decision"), decisions_dir, parse, load_decision)
        errs += bind_review(data, decision, str(p), fail)
    return errs


def check_reviews(reviews_dir, decisions_dir, root, parse, fail, required_for, load_decision):
    """The gate entry point over the per-repo decision reviews and the decided-requires-review
    property over the decision records. Adoption safe: with no .veldo/decisions/ directory AND no
    .veldo/decision_reviews/ directory, both stand down and this returns clean, so a repository with
    no decision records is byte-identically unaffected. Present reviews each fail closed on anything
    malformed or unbound (and a duplicate review id is refused), and a decided decision record fails
    closed unless it carries the bound reviews its tier requires."""
    rdir = Path(reviews_dir)
    ddir = Path(decisions_dir)
    if not rdir.is_dir() and not ddir.is_dir():
        return 0
    bound_counts, errs = _valid_bound_reviews_by_decision(rdir, ddir, root, parse, fail, load_decision)
    errs += decided_requires_review(ddir, bound_counts, root, parse, fail, required_for, load_decision)
    return errs
