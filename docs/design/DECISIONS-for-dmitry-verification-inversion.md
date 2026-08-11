# The design problem you raised: what we found, and the four decisions

Written 2026-07-26 after two independent adversarial design reviews of my own proposals. Both came back
`needs_rewrite`. This document is what SURVIVED them, plus the decisions that are actually yours.

I am not sending you my options document. Both versions of it were substantially wrong and its value was in
generating the finding below, not in its recommendation.

---

## 1. The answer to your question, and it is not what I expected

You asked whether we were missing something important in the whole process. We were, and it is not a missing
idea. **The method already contained the right rule, written down, shipped, and it never once executed.**

In one paragraph of `packs/claude/skills/review/SKILL.md`, shipped 2026-07-16, there are two instructions:

1. "After two failed cycles on the same specification, stop and bring in the human: at that point the defect
   is almost always in the specification."
2. "Append review.passed or review.failed to .veldo/events.jsonl."

WARP-1210 started 2026-07-23 and ran eleven failed cycles. Measured today:

| | count |
|---|---|
| verdict files that exist | 148 |
| `review.passed` / `review.failed` events ever emitted | **0** |
| `gate.passed` / `gate.failed` events ever emitted | **596** |

The gate events exist because `scripts/verify.sh:118` emits them. It is a script. **596 to 0. The events a
script emits all exist. The events an instruction requests have never happened once.**

**So the diagnosis is: our thinking was fine and was never converted into code.** No explanation involving
diligence, attention or care is needed. A rule addressed to whoever is doing the work is a wish, not a
mechanism, and it has a measured execution rate of zero here.

That is the finding. It is bigger than design review, and it is the chapter for the book.

---

## 2. What I proposed and what killed it, because you should not trust my next proposal either

| I proposed | why it died |
|---|---|
| Review every spec with 5+ acceptance criteria | Base-rate error. It fires on 112 of 137 specs and costs 37h to prevent 33h. I priced one false alarm against one disaster while the policy buys about 107 false alarms per disaster. |
| Tell the code reviewer to also judge the spec | Already in force since 2026-07-16. The round-1 reviewer had the spec, ruled on all six criteria, and missed the design flaw anyway. |
| Put mechanical teeth on the two-cycle rule | You WERE brought in on the specification at round 4 and nine more rounds followed. Its whole reachable saving is about 41 minutes. And its teeth depend on emitting review events, the instruction with the 0-for-148 record. I proposed enforcing one dead rule using another. |
| "Review everything, it is affordable now" | The saving is 21h not 33h on our own derivation, about 11h after attribution, and the cost doubles once you count that a review always demands a second round. Wrong by a factor of three to eight. |

The pattern in all four: I did the arithmetic on the half I found interesting and not on the half that decided
the answer. Both reviews caught it. That is the process working, at a cost of about 20 minutes per review.

---

## 3. What DID survive, measured

- **A design review costs 13 minutes** and finds real defects. Verified, not asserted: on WARP-1210 a reviewer
  given only the pre-build spec predicted the receipt store could not be enumerated and that the build would
  have to duplicate the store's path into a second file. That is exactly what shipped, and the code says so in
  its own comment.
- **It works on healthy specs too.** A control review of WARP-1209, which shipped clean in 2 commits and 19
  minutes, predicted the gate would ship inert in every new repository. Confirmed in shipped code at
  `.veldo/validate_checks.py:204`.
- **But its VERDICT is worthless.** Three reviews across two specs and three different briefings all returned
  "do not build." A judgement that is always the same carries no information. **So design review is worth
  running as a FINDING GENERATOR and worthless as a pass/fail gate.** That distinction is the most useful thing
  we learned and it is the opposite of what I was about to build.
- **Item size has real support.** Two independent reviewers, from the spec alone, ruled WARP-1210 was three to
  four items wearing one item's clothes. That matches the post-mortem exactly.

---

## 4. THE FOUR DECISIONS

**1. Adopt "if it matters, it is code, not prose"?** Every rule we intend to hold gets an emitter or a refusal
path in a script, or it does not count as shipped. Plus a one-time sweep of the existing method for rules with
no enforcement, since we now know of at least two. **My recommendation: yes.** This is the finding, and it is
the only one of the four with measured proof behind it.

**2. Run design review on new specs as a finding generator, no ruling and no gate?** 13 minutes, produces real
verified findings, and the reviewer reports findings only, never a verdict, so nobody can rubber-stamp or be
blocked by it. **Recommendation: yes, on specs that declare 15 or more footprint paths** (9 of the 30 specs
that declare one). Not on acceptance-criteria count: that number is editable prose and complying with our own
3-to-4 rule would grant automatic exemption.

**3. Enforce item size mechanically, and on what signal?** This is the one I am least sure of and I will say so
rather than dress it up. The honest problem: the same signal that catches WARP-1210 would also force splits on
six items that shipped clean in two commits. **Options: (a) enforce it and accept needless splits, (b) make it
advisory, which per finding 1 means it will not happen, (c) leave it and revisit with more data.** No
recommendation. I do not have the evidence to pick.

**4. WARP-0721 / VEL-12 - keep it parked, kill it, or rebuild it?** I had drafted "defer indefinitely," which
quietly reverses your recorded instruction that it is a gate and not an intention. That reversal is yours to
make, not mine to slip into prose. The experiment does now confirm its diagnosis: it built a mechanical
checklist when the valuable half is judgement. **Recommendation: kill the checklist, keep the one salvageable
piece** (acceptance criteria state what is claimed, over what set, how completeness is known, and what would
refute it) folded into the spec template rather than as a separate register.

---

## 5. What I am NOT asking you to decide

The rewrite of my options document, whether design review is eventually universal, who runs it and at what
independence level, and what happens to the 112 existing specs. All of those depend on decision 1 and 2 and
should not be decided in the same breath. If you say yes to 1 and 2, they become concrete and I will bring them
back as one set, not one at a time.
