---
schema: veldo.spec/v1
id: WARP-1309
title: The mechanizable floor is a floor, not a ceiling - a reviewer handed a green wall of
  automated checks grades the rest by vibes, so the lane says what is settled and what is not
status: shipped
risk: high - this decides what a security verdict means and whether it stops a merge. It also
  touches the verdict validator and the merge gate, which every change in the repository passes
  through.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0013
work: W9
depends_on: [WARP-1302, WARP-1305]
placement: [contracts, enforcement, loop]
footprint:
  - ".veldo/security_review.py"
  - "engine/.veldo/security_review.py"
  - ".veldo/shape_review.py"
  - "engine/.veldo/shape_review.py"
  - ".veldo/validate.py"
  - "engine/.veldo/validate.py"
  - ".veldo/validate_checks.py"
  - "engine/.veldo/validate_checks.py"
  - ".veldo/dispatch.py"
  - "engine/.veldo/dispatch.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-1309-security-review-dimension.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      CORRECT-BUT-INSECURE IS REFUSED AT THE REAL MERGE GATE. The conformance fixture drives a
      verdict that is `pass` with zero blocking findings and an `insecure` security dimension
      through the real `Dispatcher._verdict_passes`, and it does not ship. The same verdict with
      the concern resolved does ship, so the refusal is attributable to the dimension.
  - id: AC2
    text: >
      THE MACHINE NEVER LOWERS. Any mechanical finding forces `insecure` regardless of what the
      reviewer concluded; a reviewer verdict of `insecure` is honoured over a clean floor, because
      grading above the floor is the entire point of the lane. Only a clean floor AND a reviewer
      verdict of `secure` yields `secure`.
  - id: AC3
    text: >
      THE CONTEXT SAYS THE FLOOR IS SETTLED AND NAMES WHAT IS ABOVE IT. A reviewer shown a green
      wall of automated checks grades the rest by vibes, so `security_review_context` states that
      the mechanical results are already enforced, says not to re-grade them, and names the four
      dimensions the floors cannot reach: secrets handling, input trust, privilege footprint,
      dependency delta.
  - id: AC4
    text: >
      FAIL CLOSED AND ADOPTION SAFE, both proven. A malformed block, an out-of-vocabulary verdict,
      an out-of-vocabulary dimension, and an `insecure` naming no finding each refuse by name; a
      verdict carrying no security dimension does not block and passes the gate unchanged.
  - id: AC5
    text: >
      NO JUDGMENT IS EVER SYNTHESIZED IN CODE. `LiveSecurityReviewer.review` raises rather than
      fabricate, and `build_security` refuses a judgment carrying no in-vocabulary verdict. A
      fabricated judgment is worse than an absent one: in the record it is indistinguishable from a
      real one, and it is what somebody later points at to show the change was reviewed.
  - id: AC6
    text: >
      ONE DIMENSION INTERFACE, ENUMERATED ONCE. Both lanes expose `validate_dimension` and
      `dimension_blocks`; the verdict validator and the merge gate iterate
      `validate_checks.REVIEW_DIMENSIONS`, so a third review dimension is one entry and edits
      neither `validate.py` nor the gate. `validate.py` stays at or under its file_lines budget.
  - id: AC7
    text: >
      THE FLOORS ARE RE-RUN AT REVIEW AND PASSED IN, NEVER IMPORTED. A build's own report of itself
      is the artifact an insecure change has every reason to be wrong about. Each floor stands down
      when its module or its input is absent, so a repository that adopted only some of them gets
      the ones it has rather than an error.
required_evidence: [unit]
rollback: >
  Revert the two wiring lines (the dimension loop in validate.py, the gate read in dispatch.py) and
  delete the module. A verdict carrying no security dimension is byte-identically unaffected, so
  reverting restores previous behaviour exactly.
---

## Outcome

The independent reviewer grades security above the mechanizable floor, and correct-but-insecure is a
verdict that sends a change back.

## Why a lane and not more checks

W1 through W8 mechanized what a rule can settle: a literal secret, a wildcard permission, a
dependency nobody decided, an unsigned commit. Those are floors now and they hold without anybody's
attention.

What no rule settles is whether a change is safe. Whether this endpoint should be reachable by that
caller. Whether the new path trusts something it should not. Whether the design hands an attacker a
step they did not have yesterday. That is judgment, and the honest thing is to mark it as judgment
rather than dress it up as a check that always passes.

## The failure mode this is actually designed against

A reviewer handed "secret scan: clean, privilege: clean, dependencies: clean, signatures: valid" has
been handed a very comfortable green wall. The natural next move is to conclude the change is fine
and write two sentences saying so. At that point the lane costs real money and buys nothing, and
worse, it produces a record that says the change was security-reviewed.

So the context is explicit: these are settled, do not re-grade them, grade what is above them, and
here are the four things that live up there.

## The machine never lowers

A mechanical finding forces insecure whatever the reviewer said. The reviewer can overrule the
machine upward - calling something unsafe that every floor found clean is exactly what this lane
exists for - and never downward.

## Nothing fabricates a judgment

The reference reviewer is wired to nothing and raises. A fabricated "looks fine" is worse than a
missing one, because in the record the two are indistinguishable, and the fabricated one is what
somebody will point at later to show the change was reviewed.
