---
schema: veldo.spec/v1
id: WARP-1106
title: Adversarial decision review - the artifact, the delegated fresh-context reviewer seam, and the decided-requires-review gate (W6 of PLAN-0011)
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0011
work: W6
plan_revision: 2
depends_on: [WARP-1105]
protected_paths: []
placement: [contracts]
footprint:
  - .veldo/decision_review.py
  - .veldo/validate.py
  - .veldo/capabilities.yaml
  - .veldo/init_scaffold.py
  - .veldo/examples/decision-review-example.yaml
  - engine/.veldo/decision_review.py
  - engine/.veldo/validate.py
  - engine/.veldo/capabilities.yaml
  - engine/.veldo/examples/decision-review-example.yaml
  - packs/*/.veldo/decision_review.py
  - packs/*/.veldo/validate.py
  - packs/*/.veldo/capabilities.yaml
  - scripts/selftest.py
  - specs/WARP-1106-adversarial-decision-review.md
acceptance_criteria:
  - id: AC1
    text: >
      A versioned decision-review artifact format (schema veldo.decision_review/v1)
      exists, homed as per-repo instance data under .veldo/decision_reviews/*.yaml, a
      directory the engine glob does not sweep, so reviews stay per-repo like the
      decision records they attack and are never shipped in the engine. Each review
      binds to a decision record (a decision id and the decision_version it reviewed)
      and captures the adversarial attack on the framing: a problem_class challenge
      (is the problem class stated honestly, not anchored to today's scale), a
      per-option challenge (a non-empty option_challenges list, each naming an option
      and judging whether that option's dead_end holds), missing-option findings (a
      missing_options list, possibly empty, for a better option the framing omitted),
      a per-assumption challenge (a non-empty assumption_challenges list, each naming
      an assumption and judging whether it is a real load-bearing one), a recommendation
      to the human, and a disposition. A clearly-marked illustrative example ships at
      .veldo/examples/decision-review-example.yaml reviewing the shipped decision-example
      (DEC-0000) in its un-decided draft state, and validates clean via python3
      .veldo/validate.py decision-review .veldo/examples/decision-review-example.yaml; a
      selftest asserts the example is present, names the example decision, and carries
      no decision block (a review informs, it never decides).
  - id: AC2
    text: >
      A validator (.veldo/decision_review.py, invoked by .veldo/validate.py) structurally
      checks a decision review the way .veldo/decision.py checks a decision record and
      FAILS CLOSED by name on each of: a wrong schema id, a missing or empty required
      field (id, decision, reviewer, recommendation), a non-integer version or
      decision_version, an out-of-vocabulary disposition, problem-class verdict,
      dead-end verdict, or assumption verdict, an option_challenge or assumption_challenge
      lacking its finding, an empty option_challenges or assumption_challenges list (a
      review that challenges nothing is not an adversarial review), a duplicate option or
      assumption reference within the review, a review that smuggles a decision (a
      chosen, decided_by, or decided_at field - a review informs and never decides), and
      a file outside the parser subset (malformed). It reuses validate.parse_yamlish (no
      second parser) and the validate.fail reporter (no import cycle). Each failure class
      is proven by a negative selftest that refuses, and a well-formed review validates
      clean.
  - id: AC3
    text: >
      Mechanical control logic pairs a review to its decision record and FAILS CLOSED if
      the record is malformed or absent. bind_review resolves the referenced decision (by
      id, restricted to schema veldo.decision/v1) from the decision records directory and
      refuses a review whose decision cannot be resolved (referenced but absent); refuses
      a review whose decision_version does not match the record's current version (a stale
      review does not vouch for the current framing); requires the option_challenges to
      cover EVERY option the decision declares and to reference no option the decision does
      not declare; and requires the assumption_challenges to cover EVERY assumption and to
      reference none absent (a partial attack is not an attack on the framing). Both the
      negatives (an unresolvable decision, a version mismatch, an uncovered option, an
      unknown option reference) and the positive (the shipped example review binds clean to
      the shipped example decision) are asserted in the selftest.
  - id: AC4
    text: >
      The fresh-context adversarial reviewer is a DELEGATED seam that FAILS LOUD without a
      real reviewer, mirroring the executor's LiveLoop.review and the dispatcher's
      LiveReviewer. AdversarialReviewer.review(decision, context) is the seam; the reference
      LiveAdversarialReviewer is wired to nothing and RAISES by name (DecisionReviewError),
      refusing to fabricate a review, so an adopting runtime must inject a reviewer that
      dispatches a genuinely fresh context over the proposed decision and returns its attack.
      No decision-review verdict is synthesized in code: the module validates and binds a
      review artifact but never manufactures its findings, its disposition, or its
      recommendation. A selftest asserts the reference reviewer raises (it refuses to
      fabricate), and that a fake injected reviewer is the only path an attack enters.
  - id: AC5
    text: >
      Scrutiny scales with reversal cost, and a decision may only move to decided once a
      recorded adversarial review exists for it (the gate W6 adds to W5). decided_requires_review
      over the decision records refuses a record whose status is decided unless it carries at
      least the number of bound, valid adversarial reviews its risk tier requires, read from
      .veldo/policy.yaml risk_tiers (the single source of truth), so the irreversible choices
      that W5 maps to the critical tier need two independent reviews (D5) while a standard tier
      needs one; a decided record with fewer bound reviews than its tier requires is refused (a
      decided record without a bound review is refused). Adoption safe and fail closed: an absent
      .veldo/decisions/ directory stands down (a repository with no decision records is
      byte-identically unaffected, verified over a temporary tree), and the moment a decided
      record exists the gate fails closed. The negatives (a decided standard record with zero
      bound reviews refused; a decided critical record with one review refused; a review bound to
      a stale version not counted) and the positives (a decided standard record with one bound
      review passes; a decided critical record with two passes) are asserted over a temporary
      tree in the selftest.
  - id: AC6
    text: >
      The check has TEETH proven by mutation over this repository's shipped
      decision-review-example.yaml (the anti-vacuity rule C1): stripping an option_challenge's
      finding, and removing the recommendation, each turn the structural check RED; and over a
      temporary tree, deleting the sole bound review of a decided record turns
      decided_requires_review RED. Each mutation reverts byte-identical. .veldo/decision_review.py
      ships in the engine and is re-synced byte-identical across engine and all 6
      packs, .veldo/validate.py's edit is re-synced likewise, the init scaffold lays
      .veldo/decision_review.py beside .veldo/decision.py, and capabilities.yaml gains one honest
      mechanical entry (adversarial_decision_review) in every copy (template sync and pack drift
      pass). The delegated fresh-context reviewer is honestly labeled a delegated seam that fails
      loud (nothing mechanizable that nothing enforces, NG5). The decision REVIEWS themselves are
      per-repo (.veldo/decision_reviews/, not shipped in the engine), so a fresh init stays
      review-free and adoption safe; the in-session tripwire MONITORING of the decision's
      assumptions is WARP-1107 (W7), honestly out of scope here. The full gate is GREEN (selftest,
      contracts, generated, docs, secret scan, template sync, pack drift), RULE #1 is clean, and
      no protected path is touched.
required_evidence: [unit]
rollback: >
  Revert the commit. The change adds one validator module (.veldo/decision_review.py),
  a call to it from .veldo/validate.py (a directory scan in run_all, a single-file
  decision-review check for the example, the decided-requires-review gate over the
  decision records, and a decision-review CLI mode), an init-scaffold substrate entry,
  one capabilities entry, one illustrative example artifact, and a selftest block.
  Nothing consumes decision reviews beyond the decided-requires-review gate yet, and
  that gate stands down entirely when no .veldo/decisions/ directory exists, so removing
  it returns the gate to its prior behavior with no migration and nothing to unwind. A
  repository with no decision records (this repository included) is unaffected either
  way (the adoption-safe posture).
---

## Intent

This is W6 of PLAN-0011 and the third move of the method's "wrong foundations"
invention (Invention #2, adversarial fresh-context decision review): a foundational
choice must be ATTACKED before a human commits to it. WARP-1105 shipped the decision
RECORD (the option space, each option's dead-end condition, the reversal-cost class
and the assumptions that become living tripwires) but deliberately shipped only a
DRAFT example, because a genuinely decided record needs an adversarial review that
did not exist yet. This item builds that review: the decision-review ARTIFACT that
captures the attack on the framing, the mechanical control logic that binds a review
to the decision it reviews and fails closed on a malformed or absent record, the
DELEGATED fresh-context reviewer seam that fails loud rather than fabricate an
attack, and the gate that lets a record legitimately move to `decided` only once a
recorded adversarial review exists for it, with scrutiny scaling to the reversal
cost through the existing risk tiers.

The review attacks four things, exactly the brief the method states: is the
problem_class stated honestly rather than anchored to today's scale; does each
option's dead_end actually hold; is a better option missing; and are the recorded
assumptions the real load-bearing ones. It produces a recommendation and a
disposition for the HUMAN to read; W6 informs the decision, it never makes it (O4,
NG2). Scrutiny scales with reversal cost: a decision W5 maps to the critical tier
(the irreversible ones, D5) needs two independent reviews, a standard tier needs
one, read from the same policy risk_tiers the rest of the loop already reads.

## Context

- Depends on WARP-1105 (shipped): the decision record at .veldo/decisions/*.yaml
  (veldo.decision/v1) and its validator .veldo/decision.py, with the reversal_cost
  to risk-tier mapping already enforced there (irreversible must sit at critical).
  This item reads a decision through decision.py's load_record (the one place a
  record is parsed) and reads the record's already-validated risk tier; it never
  re-derives the mapping.
- Resolved decision D5: reversal cost is expressed through the existing risk tiers,
  with irreversible mapping to critical (two independent verdicts plus recorded
  human approval). W5 mechanized the record-side mapping; this item mechanizes the
  review-side scrutiny, reading the required number of independent adversarial
  reviews from .veldo/policy.yaml risk_tiers (the reviews count), so the tier to
  independent-review-count mapping lives in one place, not two.
- The validator is modeled on the two shipped siblings (.veldo/arch.py, .veldo/decision.py):
  structural, fail-closed, closed-vocabulary checks over the same front-matter subset
  (validate.parse_yamlish), no second parser, no import cycle. decision_review.py
  receives the parser and the failure reporter from validate.py, which owns them.
- The delegated reviewer seam mirrors the shipped fail-loud pattern exactly: the
  executor's LiveLoop.review and the dispatcher's LiveReviewer both raise rather than
  fabricate a verdict. LiveAdversarialReviewer is the analogue for a decision: it
  refuses to fabricate an attack, so a review artifact is only ever produced by a
  genuinely fresh context an adopting runtime injects.
- The two postures the plan binds everywhere: adoption safe (a repository without a
  .veldo/decisions/ directory is untouched, the gate stands down) and fail closed (the
  moment a review or a decided record exists it is validated and refuses anything that
  does not hold).

## Out of scope

- No in-session tripwire monitoring. Comparing each assumption's declared signal
  against its current recorded value and surfacing an approaching or reached breach as
  a named finding in the gate output and veldo status is WARP-1107 (W7). This item only
  reviews the framing before the decision; it does not watch the assumptions after it.
- No machine decision and no self-promotion (NG2). The review produces a recommendation
  and a disposition for a human; it never sets a decision's chosen option, never records
  a decider, and never flips a decision to decided. The structural check refuses a review
  that smuggles any decision field.
- No fabricated review. The adversarial attack is performed by a delegated fresh context,
  never synthesized in code. The reference reviewer fails loud; the module validates and
  binds an artifact a real reviewer produced.
- No elaboration blocking. Making an elaboration that hits an undecided foundational
  choice block and surface the decision is a separate downstream concern and is not built
  here.
- No change to the shipped enforcement core: scripts/verify.sh, veldo-guard.sh,
  .veldo/policy_check.py, .veldo/policy.yaml and their engine twins are untouched
  (protected paths). The decided-requires-review gate lives in the non-protected engine
  (.veldo/decision_review.py, .veldo/validate.py) and READS policy.yaml risk_tiers without
  editing it.

## Notes

- Keep the validator dependency free and the artifact readable (the C3 proportionality
  constraint). Follow the byte-identical engine sync discipline: .veldo/decision_review.py
  and the edited .veldo/validate.py and .veldo/capabilities.yaml land in engine and
  every pack byte-identical, and the drift checks end empty. The decision REVIEWS are
  per-repo (like the decision records and the contract), and homing them in a
  .veldo/decision_reviews/ subdirectory keeps them out of the .veldo/*.yaml engine glob
  structurally, so a fresh /veldo:init repository starts review-free and adoption safe. The
  illustrative example ships in .veldo/examples so an adopter sees the format; it reviews the
  DRAFT decision-example and attributes no decision to any human.
- Read policy.yaml risk_tiers with a small, focused reader (the same proportionate posture
  policy_check.py uses): the reviews count per tier, defaulting to one (never zero) when the
  tier or the file is absent, so a decided record can never pass with no adversarial review.
- Put teeth on the check by mutating the shipped example (strip an option_challenge finding,
  remove the recommendation) and observing the check go red before reverting, and prove the
  decided-requires-review gate with a temporary-tree fixture (a decided record with no bound
  review refuses; the bound review clears it; a critical record needs two); a mechanical check
  that cannot refuse is exactly the vacuity C1 forbids.
- Honesty (NG5 and the WARP-1101 review lesson): do not mark a rule mechanizable that nothing
  enforces, and state the delegated-reviewer boundary honestly. This repository ships the
  artifact format, its validator, the binding gate, and the fail-loud reviewer seam with a
  draft-decision review example; it does not manufacture a real adversarial verdict, and it
  does not flip the shipped decision example to decided.
- RULE #1 clean (ASCII hyphen only, no em or en dash, no prose double-hyphen).
