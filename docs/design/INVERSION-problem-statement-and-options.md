# THE VERIFICATION INVERSION - problem statement and options

**Status: PROBLEM STATEMENT, not a proposal.** Written 2026-07-26 after Dmitry named the issue. It must get an
INDEPENDENT ADVERSARIAL DESIGN REVIEW in a fresh context before it reaches him, because a proposal to
institutionalise design review that has not itself been design reviewed is indefensible. He explicitly allowed
hours rather than minutes.

## This document's own claims, stated in the structure it will argue for

| # | promise | domain | enumeration | observation | what would refute it |
|---|---|---|---|---|---|
| 1 | Verification is concentrated where errors are cheapest to find | the six phases of the Veldo loop | the loop is a declared, finite sequence | which phases have an independent adversary vs a schema check | finding an existing independent check on the design phase |
| 2 | A design error's cost is multiplied by the rounds it survives | WARP-1210's 12 rounds | git history, all rounds counted | rounds attributable to one design omission | showing the rounds had independent causes |
| 3 | The method's own laws were discovered, not designed | the laws added to project_veldo.md on 2026-07-25/26 | that file's own 2026-07-25/26 sections | each law's origin: designed upfront or extracted from a failure | finding a law that was specified before its first failure |
| 4 | A design review is affordable at the project's real item size | the 145 delivered items | git history by primary id | review cost vs the 1.19h mean and the failure tail | measuring review cost above the saving it produces |

Claim 4 is the weakest and the one the review should attack hardest. It is the difference between a fix and a
tax.

## 1. The problem, precisely

The loop is: intent, specification, implementation, proof, independent adversarial review, merge.

**The implementation is attacked by a fresh adversary who did not write it and is instructed to refute it. The
design is checked by a schema validator.** A validator confirms a spec HAS a footprint, acceptance criteria, a
risk tier and a rollback. It cannot tell you the domain is the wrong domain, that the evidence observes a proxy,
that four decisions are missing, or that the abstraction is wrong. So a design is reviewed by exactly one person:
its author.

**Why that is an inversion rather than a gap.** The cost of a design error is not its own fix. It is its fix
multiplied by every implementation round it survives, because each round faithfully verifies an implementation
against the wrong specification and the reviewer can only find the next symptom. On WARP-1210:

- one undeclared domain
- twelve builds, eleven failed reviews
- roughly 30 hours against a project mean of 1.19h per item, i.e. about 25x
- the defect-class key escalated five times before anyone asked what the complete set was
- the test grid observed a reader while the item promised four rendered surfaces

Every individual round was rigorous. The rigour was aimed one layer below the thing that was wrong.

## 2. Evidence, measured rather than asserted

| fact | value | source |
|---|---|---|
| items delivered | 145 | git, primary id per commit subject |
| mean span per item | 1.19h | git, first-to-last commit per id |
| items at 1-3 commits | 139 of 145 (96%) | primary-id commit counts |
| max commits, any other item | 6 | same |
| WARP-1210 commits | 20+ | same |
| WARP-1210 elapsed | ~30h | same |
| real defects found in rounds 8-12 | 5 distinct, all pre-existing | verdicts 8-12 |
| rounds whose finding was PROSE only | 7 of 11 | verdicts 1-11 |
| laws added to the method on 2026-07-25/26 | 6 | project_veldo.md |
| of those, designed upfront | 0 | same |

The last row is the one that should be uncomfortable. **The method is being built by the anti-pattern it exists
to prevent.**

## 3. What a solution must do, derived from the evidence

- **R1** Attack the DESIGN before implementation begins, by someone other than its author, with the same
  refute-it instruction the implementation reviewer gets.
- **R2** Route review findings back into the DESIGN phase, not only into code. Eleven reviews produced eleven code
  patches and zero design-gate changes.
- **R3** Be affordable at the real item size. A 1.19h item cannot carry an hour of design review; a 30h item
  obviously can. Any uniform cost is wrong in one direction or the other.
- **R4** Not become ceremony. Five sections nobody reads costs every item and prevents nothing, which is worse
  than nothing. Whatever is added must be able to REFUSE a plausible-looking answer.
- **R5** Be proven against the failure that motivated it. If the mechanism would not have caught WARP-1210's
  original spec, it is measuring the wrong thing.

## 4. Options

### A. Adversarial design review as a mandatory phase

A fresh context reviews every spec before build, instructed to refute the design: find the missing domain, the
proxy observation, the unasked decisions, the wrong abstraction.

Satisfies R1, R2 (findings land in the spec, before code exists), R5. **Fails R3 as stated**: a uniform review on
every item taxes the 139 items that take 1-3 commits to protect against the one that does not. If a design review
costs 20 minutes against a 1.19h mean, that is roughly 28% overhead on every item.

### B. Adversarial design review above a threshold

Same, but only for items above some risk or size line.

Satisfies R3. **The threshold is the whole problem**: guessed wrong, it misses the next 1210. WARP-1210 was rated
high, not critical, and would have needed the line drawn at high to be caught - which would catch a large fraction
of all items anyway. A guessed threshold also violates R4's spirit: it is a number with no derivation.

### C. Retrospective spec review by the implementation reviewer

The existing reviewer also rules on the SPEC, not just the code.

Cheapest, adds no phase. **Fails R1 in the way that matters**: it happens after the build, so the multiplier has
already been paid. It would have caught 1210's domain gap in round 1's review rather than round 12 - which is
actually most of the value - but it cannot prevent the first wasted build.

### D. Two layers, sequenced judgement-first

The full symmetry of what code already has: a mechanical design gate (the lint equivalent) PLUS an adversarial
design review (the reviewer equivalent). Sequenced so the REVIEW is built first and the mechanical checks are
derived from what reviews actually find, rather than guessed.

Satisfies R1, R2, R4, R5. R3 remains open and must be solved by a DERIVED threshold rather than a guessed one.

### E. Author pre-mortem instead of review

The author writes how this item will fail before building it.

Cheapest that touches R1. **Fails independence**, which is the entire mechanism: the author's blind spots are
exactly what a pre-mortem cannot see. Recorded for completeness; not recommended.

## 5. Recommendation, and the honest gap in it

**D, sequenced judgement-first, with C as the immediate stopgap.**

C is nearly free and captures most of the value today: the existing reviewer already reads the spec to review the
code, and instructing it to rule on the SPEC's domain, observation point and decisions costs almost nothing. That
alone would have surfaced 1210's root cause in round 1 instead of round 12.

D is the real answer, and the sequencing matters because I already made the opposite mistake once (WARP-0721 built
the mechanical layer first and was refuted five ways within the hour). Build the judgement layer, watch what it
finds, and let the mechanical checks be derived from real findings rather than from one night's grievances.

### R3's threshold - MEASURED, and it partly refuted my own recommendation

I said guessing is how B fails, so I measured instead. Every item that exceeded three commits, against its
declared acceptance-criteria count and risk tier:

| item | commits | ACs | risk |
|---|---|---|---|
| WARP-1210 | 30 | 7 | standard |
| WARP-1208 | 6 | 6 | standard |
| WARP-0614 | 6 | 6 | standard |
| WARP-0616 | 5 | 5 | standard |
| WARP-0623 | 4 | 5 | standard |

And a sample of well-behaved items: WARP-0100 (5 ACs, 3 commits), 0101 (5, 2), 0102-0106 (4 ACs, 2 commits each),
0107 (4, 3).

**FINDING 1, which kills the obvious threshold: RISK TIER DOES NOT DISCRIMINATE AT ALL.** All five high-round
items are `standard`. A risk-based threshold - the first thing anyone would reach for, and what option B implies -
would have caught none of them. That is worth knowing before building it.

**FINDING 2: AC count is a WEAK signal with OVERLAPPING distributions.** High-round items run 5-7; well-behaved
items run 4-5. Five acceptance criteria appears in BOTH groups (WARP-0616 took 5 commits, WARP-0101 took 2). So a
clean separating threshold does not exist in this data, and my stated refutation condition ("if the items that
needed many rounds are indistinguishable, the recommendation must change") has partly fired.

**HOW THE RECOMMENDATION CHANGES, and this is the useful part.** A threshold protecting against an expensive
failure has ASYMMETRIC ERROR COSTS: a false positive costs one unnecessary design review, about 20 minutes; a
false negative costs a 1210, about 30 hours. That is a ratio near 90 to 1. **So the threshold should be set
DELIBERATELY LOW, accepting over-triggering, rather than tuned for accuracy.** At AC >= 5 it catches all five
known high-round items and also fires on some items that would have been fine - which is the correct direction to
be wrong in.

So option B is viable after all, but ONLY with a low, over-triggering, cost-asymmetry-justified threshold, and
NOT on risk tier. That is a different B from the one I described, and I would not have got there by reasoning.

## 6. What would refute this whole analysis

- If the 11 failed reviews had **independent** causes rather than one design omission, the multiplier argument
  collapses and 1210 is just a hard item.
- If a design review's cost, measured, exceeds the cost of the rounds it prevents at the project's real item size,
  then the inversion is real but not worth correcting.
- If some existing check already attacks the design and I have simply not recognised it, the premise is wrong.
- If the items that needed many rounds are indistinguishable from those that did not, R3 has no solution and the
  recommendation must change.

## 7. Decisions needed from Dmitry, ALL AT ONCE (per his rule)

These are the choices in this design. They are listed together, before anything is built, deliberately.

1. **Universal, or thresholded at AC >= 5?** Now MEASURED rather than guessed. Risk tier discriminates nothing
   (all five high-round items were `standard`). AC count is a weak signal with overlapping distributions, so no
   clean threshold exists - but the error costs are asymmetric by roughly 90 to 1 (a needless review costs about 20
   minutes, a missed design error cost 30 hours), so the threshold should be set LOW and over-trigger on purpose.
   My recommendation: threshold at AC >= 5, which catches all five known cases and knowingly fires on some items
   that would have been fine.
2. **Does the stopgap ship immediately?** Instructing the existing reviewer to also rule on the spec costs
   almost nothing and can be in the next brief. Recommend yes.
3. **Who reviews the design?** A fresh agent context (cheap, available, no independence from the model) or a human
   (independent, scarce, and it is you). Recommend agent, with the honest note that it is not independent of the
   model that wrote the spec.
4. **Does the method's own development get held to this?** Every Veldo item would then need a design review,
   including the one that introduces design review. Recommend yes, and it makes the first one recursive in a way
   that is a useful test rather than a paradox.

## 8. Next step

Independent adversarial design review of THIS DOCUMENT in a fresh context, instructed to attack claim 4 hardest
and to answer whether R3's threshold is derivable from the 145-item history. Then, and only then, a proposal to
Dmitry.
