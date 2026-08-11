# P(catch) EXPERIMENT - PRE-REGISTERED SCORING

Written 2026-07-26 07:10 EDT, BEFORE the experiment ran and before any result was seen. The point of writing
it first is that a design review's value is exactly what it CATCHES, and an author scoring his own experiment
after the fact will find a way to call a near-miss a hit. Pre-registration is the only defence.

## The question

Design review is being proposed as a phase. Every affordability number in
`INVERSION-problem-statement-and-options.md` is multiplied by P(catch): the probability that an independent
adversarial design review, given a spec as authored, names the design defect that actually went on to cost
the project ~34 hours. Nothing measures it. The only observation available today is a MISS (the round-1 code
reviewer had the spec, ruled per-criterion on all six criteria, and did not name the domain gap).

## The setup

- Subject: `specs/WARP-1210-the-support-numbers.md` exactly as authored at `c37e833` (2026-07-24 18:28 EDT,
  6 acceptance criteria, status ready, BEFORE the first build).
- The reviewer sees the repository as it stood at `c37e833`, extracted with `git archive` so there is no
  `.git` and no future history. `proof/WARP-1210/` DOES NOT EXIST at that revision (verified: 0 files), so
  no verdict, no manifest and no round can leak. The 138 verdicts present belong to OTHER items and are
  legitimate convention context.
- The reviewer is NOT told: that this spec failed, how many rounds it took, what the defect was, that an
  inversion workstream exists, or that its output will be scored. It receives a generic design-review brief.
- Blindness is the whole experiment. A contaminated run measures nothing.

## What actually went wrong, recorded here so scoring cannot drift

1. **The domain was never declared.** The spec said what to build but never said "this item is complete when
   X holds over the following complete set, enumerated in this way." The defect-class key was consequently
   re-keyed FIVE times across rounds 8 to 12 (recursion, then exception classes, then read primitives, then
   the item's declared sources, then declared sources plus their transitive closure), each one name short.
2. **The evidence observed a PROXY.** The item promises what FOUR RENDERED SURFACES show; the test grid built
   its model from a reader and never ran a surface.
3. **Human decisions arrived one at a time** across a night when they were four faces of one question.

## Scoring, fixed now

- **FULL CATCH** = the review names defect 1: that the spec does not declare the complete set it is over, or
  equivalently asks how the enumeration of sources is known to be complete, in a way that would have forced
  the domain to be declared before building. Wording may differ; the demand must be for a declared and
  provable domain.
- **PARTIAL CATCH** = names defect 2 (evidence observes an intermediate rather than the promised rendered
  surfaces) or defect 3 (decisions not raised together), without defect 1.
- **MISS** = names neither. Generic findings ("acceptance criteria could be tighter", "risk tier seems low",
  style, scope) are a MISS however numerous.
- Recorded alongside: the reviewer's wall clock, and whether it would have BLOCKED the spec from being built.

## What each outcome means for the proposal, decided now

- **FULL CATCH:** P(catch) is plausibly high, the cheap triggers in the rewrite become clearly worth their
  cost, and the requirement that a design review be able to REFUSE gains an observed basis.
- **PARTIAL:** the mechanism finds real design defects but not reliably the expensive one. Favours the
  triggers whose cost is near zero (the second-failed-review route) over any broad threshold.
- **MISS:** decisive against adding a design-review PHASE at any threshold, because a phase that does not
  catch the failure that motivated it fails R5 by measurement. The honest response would then be to shrink
  items and enforce the routing rule that already ships, and to say so plainly.

One run is n=1 and will be reported as n=1. It cannot establish a rate; it can establish existence or refute
an assumption, which is enough to change which option is defensible.

## TWO ARMS, and the difference between them is the actual finding

Added 07:14 EDT, before either arm ran, because the first design of this experiment was circular and I want
the circularity recorded rather than quietly fixed.

The proposed mechanism is a reviewer PLUS a brief. If the brief tells the reviewer to check "is the domain
declared and provably complete, and does the evidence observe the promise or a proxy," then catching this
particular spec is guaranteed, because that brief was written by me yesterday FROM this exact failure.
Measuring it would measure hindsight, not judgement, and would be the one-convenient-fixture defect that
refuted WARP-0721.

So:

- **ARM A, GENERIC.** An adversarial design reviewer told only to attack the design and find what will prove
  expensive, with no dimensions named and no hint of the failure mode. This measures whether design review
  as an ACT catches this class absent hindsight. It is the honest P(catch).
- **ARM B, CODIFIED.** The same spec and tree, with the four-component brief (promise, domain, enumeration,
  observation) plus refutation and unasked decisions. This measures the CODIFIED gate, and its result is
  expected to be a catch, so a catch here proves little on its own.

**The informative quantity is A minus B.** If A catches it, design review works generically and the brief is
a convenience. If A misses and B catches, then the BRIEF is doing the work, which means (i) the mechanism
cannot be better than the failures already harvested into its brief, and (ii) option D's sequencing argument
is vindicated: build the judgement layer, harvest what it finds, derive the checks. If both miss, adding a
design-review phase fails R5 by measurement and the honest answer is smaller items plus enforcing the routing
rule that already ships.

Arm A is the number that goes to Dmitry as P(catch). Arm B is reported beside it and labelled as
hindsight-informed, never merged into one figure.
