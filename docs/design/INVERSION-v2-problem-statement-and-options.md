# THE VERIFICATION INVERSION - problem statement and options, VERSION 2

**Status: PROBLEM STATEMENT, not yet a proposal.** Version 1 was written 2026-07-26 05:22, sent for
independent adversarial design review at 06:44, and came back **needs_rewrite with 3 FATAL and 7 BLOCKING**
at 07:01. This is the rewrite. One slot is still open, marked PENDING, and it is the slot that decides the
recommendation: nobody has measured whether a design review actually CATCHES the failure that motivated it.
That experiment is running, pre-registered, two-armed.

**Why version 1 had to be rewritten rather than patched.** Its three fatal findings each broke a different
layer: the economics of the recommendation, the problem statement itself, and the stopgap that would have
shipped first. The population figures survived intact and are carried forward.

**What version 1 got wrong, stated plainly, because it is the most useful thing in this document:**

1. Its premise was false. The mechanism it proposed to invent ALREADY SHIPS.
2. Its threshold was a base-rate fallacy. The policy cost 37h to prevent 33h.
3. Its cheap stopgap is refuted by the artifact it claimed it would have caught.
4. Four of its figures did not reproduce, and one INVERTED.

---

## 1. The problem, corrected

Version 1 said: "the design is checked by a schema validator, so a design is reviewed by exactly one person,
its author." **That is false, and the truth is more uncomfortable.**

**Three checks that attack design already ship, all of them predating the failure:**

| artifact | landed | what it does |
|---|---|---|
| `packs/claude/skills/review/SKILL.md:13-16` | 2026-07-16 | "After two failed cycles on the same specification, stop and bring in the human: at that point the defect is almost always in the specification." |
| `packs/claude/agents/veldo-reviewer.md` | 2026-07-16 | "Judge the change against the Intent section of the specification, not only the acceptance criteria." |
| `.veldo/decision_review.py` (WARP-1106) | 2026-07-22 | A foundational choice is ATTACKED by a fresh context before a human commits to it. Four dimensions including MISSING OPTIONS. Gates a decision record from reaching `decided`. |

WARP-1210 began 2026-07-23. **It ran ELEVEN failed cycles under a shipped rule that says to stop at two and
that names the correct conclusion in advance.** Version 1's option C, "instruct the reviewer to also rule on
the spec," was already in force on 2026-07-16, ten days before I proposed it as new.

**So the defect is not a missing idea. It is A RULE WITHOUT TEETH.** The whole thesis of this method is that
a claim without teeth is not enforced, and its own routing rule was advisory prose in a skill document, with
no counter, no gate and no event to fire on. We wrote down the right upfront thinking and then let it leak
away for want of a mechanism.

**The gap that does survive, narrowed and still real: NO ADVERSARY ATTACKS A SPEC'S DESIGN AT SPEC
GRANULARITY BEFORE THE BUILD.** `decision_review.py` covers foundational CHOICES, not specs. `shape_review.py`
covers architectural fit AFTER the build. The reviewer brief covers intent but only once code exists. The
nearest neighbour to what is needed is a shipped organ to extend, not a phase to invent.

**The cost structure that makes this worth fixing at all.** A design error's cost is its own fix multiplied by
the rounds it survives, because each round faithfully verifies an implementation against the wrong
specification and the reviewer can only find the next symptom. That claim is narrowed in section 3; one
genuine multiplied thread is measured, and the "one omission caused 30 hours" version is withdrawn.

---

## 2. Evidence, measured, with populations named

Every figure below reproduced under independent re-derivation. Where version 1 published a figure that did
not reproduce, the correction is shown.

**Population A - all 145 delivered primary ids (133 VELDO, 12 PLAN), from git:**

| fact | value | note |
|---|---|---|
| items delivered | 145 | primary id at commit-subject start |
| items at 1 to 3 commits | 139 of 145 (96%) | |
| max commits, any other item | 6 | WARP-0614, WARP-1208, PLAN-0011 |
| WARP-1210 | 30 commits, 34.37h | nothing between 6 and 30 |
| mean span per item | 1.19h | valid ONLY on the gap-capped active-time derivation (inter-commit gaps capped at 2h, 173.1h over 145) |
| MEDIAN span per item | **0.31h (19 min)** | 53% of items under 20 min; 21 items are single-commit |

The median matters: version 1 argued affordability against a mean that one 34h item inflates by about 40%.
Publish both or the argument is anchored on the wrong statistic.

**Population B - the 137 specs a design gate would act on** (excludes 12 PLAN ids and 4 specs with no
commits). Version 1 silently mixed A and B, which is exactly the class of error it claimed a schema
validator cannot catch.

| distribution | measured |
|---|---|
| acceptance criteria | `{2:2, 3:7, 4:16, 5:78, 6:21, 7:10, 8:2, 10:1}` |
| risk tier | 126 standard, 10 high, 1 critical |
| declares a footprint | 30 of 137 (21.9%; mandatory only since PLAN-0011 W3, so 100% going forward) |

**Corrections to version 1's table:**

| version 1 said | measured truth |
|---|---|
| "7 of 11 rounds were PROSE only" | **0 of 11.** Every verdict carries at least one finding its own reviewer labels a real defect. 9 of 11 carry at least one prose finding. The cell as published INVERTED the argument. |
| "real defects in rounds 8-12: 5 distinct, all pre-existing" | R8-B1's own severity string reads "a REAL DEFECT, a ROUND-8 REGRESSION". At least three defects were INJECTED BY THE REPAIR ROUNDS. |
| "twelve builds, eleven failed reviews" | 11 build attempts and, at version 1's mtime, 10 verdicts. Round numbering skips 3, which is the off-by-one. |
| "WARP-1210 was rated high" (line 88) | `standard`. Version 1 contradicted itself; its own FINDING 1 was right. |
| "WARP-1210 had 7 acceptance criteria" | Authored with **6**; reached 7 at round 4 when a criterion was split in two. A design-time trigger must be scored on the artifact AS AUTHORED. |
| laws added 2026-07-25/26: 6, of those 0 designed upfront | No counting rule was stated and at least 8 candidates exist. The generalisation to "the method's own laws" is withdrawn (see section 8). |

**Measured cost of adversarial review, the first real data on this:**

| kind | n | mean | range |
|---|---|---|---|
| code review, this item | 11 | 42.6 min | 18.4 to 121.3 |
| design review, this document | 1 | 18 min | - |

So 20 to 45 minutes is the defensible planning range. Version 1's asserted 20 minutes was optimistic but not
wrong. **It was never the per-review cost that killed version 1's recommendation. It was the trigger rate.**

---

## 3. The multiplier claim, split into the part the evidence supports and the part it does not

Version 1 claimed "one undeclared domain cost eleven rounds." It stated no attribution rule, which made the
claim unfalsifiable, and the artifacts point away from the strong form.

**SUPPORTED, and it is a real multiplier:** the defect-class key widened FIVE times across rounds 8 to 12 -
recursion, then exception classes, then read primitives, then the item's declared sources, then declared
sources plus the transitive closure of what is opened on its behalf - and round 12 found a fifth member still
open. Each key was one name short, and each round could only find the next symptom. **One question asked
upfront (what is the complete set this touches, and how do we PROVE the enumeration is complete?) reaches the
final answer immediately.**

**WITHDRAWN:** "30 hours from one design omission." At least three defects were created by the repair rounds
themselves, and about 13 of the 34 findings are manifest and prose honesty findings that no design review
touches. **My own record from 2026-07-25 already said the disease is item size:** "each round writes NEW code
and new code has new defects; round 8's crash did not exist until round 8 created it, so no care in round 7
could have caught it. That argues for SMALLER CHANGES, not more diligence." Version 1 omitted that and
proposed more diligence.

**Attribution rule, stated before any count is published:** a round is attributable to a design omission only
if the defect it found was present in the artifact BEFORE the first build AND its fix required changing the
specification. By that rule the domain-declaration omission is one thread; the sweep-key widening is a second,
partly overlapping; iteration-injected defects are a third and are NOT preventable by design review.

---

## 4. What a solution must do

R1 to R5 are carried forward. R2 is demoted to an option, because it read as a requirement only because it
was a mechanism in disguise. Two requirements are added, both derived from findings above.

- **R1** Attack the DESIGN before implementation begins, by someone other than its author, with the same
  refute-it instruction the implementation reviewer gets.
- **R3** Be affordable at the real item size, judged by TOTAL POLICY COST, not a per-instance ratio.
- **R4** Not become ceremony. It must be able to REFUSE, and the refusal must have a defined operational
  meaning: what it blocks, what artifact records it, what unblocks it, who arbitrates.
- **R5** Be proven against the failure that motivated it. If it would not have caught WARP-1210's spec as
  authored, it measures the wrong thing.
- **R6 (NEW)** Address defects INJECTED BY ITERATION, which are a distinct and larger class than design
  omissions and are not reachable by reviewing the original spec.
- **R7 (NEW)** Fire WITHOUT the owner noticing. The capability to self-refute demonstrably exists; what was
  missing every single time was the TRIGGER. A mechanism whose trigger is a person's attention has already
  failed once this week.

---

## 5. Options, re-derived over the corrected problem

| option | what it is | verdict |
|---|---|---|
| A. Universal design review | Every spec, fresh adversary, pre-build | Fails R3 on arithmetic: 137 x 42.6 min = 97h |
| B. Thresholded design review | Same, above a signal | Viable ONLY at a trigger rate the arithmetic supports; AC >= 5 is refuted (see section 6) |
| C. Reviewer also rules on the spec | Extend the code reviewer's brief | **REFUTED.** Already in force since 2026-07-16, and the round-1 reviewer had the spec, ruled per-criterion on all six, and missed the domain gap anyway |
| D. Mechanical gate plus adversarial review, judgement first | Full symmetry with code | Still the right shape for the surviving gap, but its threshold must come from section 6 |
| E. Author pre-mortem | Author writes how it will fail | Fails independence, which is the entire mechanism |
| **F1. Shrink the item** | On the same signal, the action is SPLIT, not REVIEW | My own recorded root cause. Marginal cost near zero: the split was already required by the standing 3-to-4-criteria rule. Attacks R6, which nothing else does |
| **F2. Extend `decision_review.py`** | Widen the shipped organ from decision records to specs | Inherits a schema, a binding, a fail-closed gate and a MISSING OPTIONS dimension. Smaller than a new phase |
| **F3. Teeth on the two-cycle rule** | A review finding that indicts the SPEC blocks further building until the spec is amended or a human rules | **1 item in 133 ever reached two failed reviews. Total cost 0.71h.** The only candidate whose trigger the author cannot influence and the only one that satisfies R7 |

---

## 6. The arithmetic version 1 never ran

The test, stated as a formula so it cannot be skipped again:

```
trigger_rate x population x cost_per_review   <   P(catch) x expected_saving
```

Expected saving is the overrun above normal: 34.37h - 1.19h = **33.2h**.

| trigger | fires on | policy cost at 42.6 min | catches (of 5 troubled) | pays if |
|---|---|---|---|---|
| universal (A) | 137 of 137 | 97.3h | 5 | never on this history |
| **AC >= 5 (version 1's pick)** | **112 of 137 (81.8%)** | **79.6h** | 5 | never; 37.3h even at 20 min |
| AC >= 6 | 34 of 137 (24.8%) | 24.2h | 3 | P(catch) > 0.73 |
| risk >= high | 10 of 137 (7.3%) | 7.1h | **0** | never; catches nothing |
| footprint >= 15 | 9 of 30 (30%) | 6.4h | 3 | P(catch) > 0.19 |
| **F3 second failed review** | **1 of 133** | **0.71h** | 1 (the one that mattered) | P(catch) > 0.02 |

**Three conclusions.**

1. **AC >= 5 is refuted.** It is "review everything" with 25 exemptions, at 82% of the universal cost that
   this document already rejected. It is a net loss at every review cost above 18 minutes.
2. **Acceptance-criteria count is the wrong SIGNAL, not merely the wrong cut point.** It moved from 6 to 7 by
   splitting one sentence, with no design change. Worse, the standing house rule is 3 to 4 criteria maximum,
   so an author who COMPLIES is automatically EXEMPT: the trigger rewards the behaviour it exists to catch.
   Footprint count is declared and validated against the architecture contract, and dominates AC >= 6 at
   equal catch (30% versus 43%).
3. **The cheapest trigger is also the most precise.** Over-triggering was never the only way to be safe.

**P(catch) - MEASURED, and it reverses the cost side of this section.** Full detail in `PCATCH-results.md`;
the experiment was pre-registered before either arm ran.

- **ARM A, the honest arm** (generic brief, no dimensions named, no hint that the spec had failed): ruled
  `do_not_build_yet` with 13 findings and caught **all three** pre-registered defects, plus independently
  ruled the item to be 60 to 65 assertions needing a three-way split. **P(catch) = 1 of 1.**
- **ARM B** (codified four-component brief): also `do_not_build_yet`, all seven dimensions FAIL, all three
  defects caught, plus a VERIFIED HIT - it predicted from the spec alone that the receipt store cannot be
  enumerated and that the build would have to choose "a gate refusal or forking store layout into a second
  owner," and the shipped code took the second horn and says so in its own docstring.
- **A minus B: both caught it, so THE BRIEF IS A CONVENIENCE, NOT THE MECHANISM.** Design review as an act
  works without hindsight, so the mechanism is not capped by the failures already harvested into its checklist.
  This strengthens the judgement layer and demotes a mechanical design gate to optional polish, which is
  exactly why WARP-0721 (polish first) was refuted.
- **Measured cost: 13.2 min mean over three real design reviews** (17.4, 9.8, 12.4), against 42.6 min for code
  review of the same item. Agent self-reports run 2 to 3 times high and were discarded.
- **Honesty: one of arm A's 13 findings is a false positive** (a mutual recursion that does not exist; the load
  direction is one way). A design review's output must be RULED, not adopted.

**Recomputed at the measured cost, this REVERSES version 2's draft rejection of the universal option:**

| trigger | fires on | cost at 13.2 min | catches (of 5) |
|---|---|---|---|
| universal (A) | 137 of 137 | **30.1h** | 5 |
| AC >= 6 | 34 of 137 | 7.5h | 3 |
| footprint >= 15 | 9 of 30 | 2.0h | 3 |
| **F3 second failed review** | **1 of 133** | **0.22h** | 1 (the one that mattered) |

Universal review costs 30.1h against the 33.2h overrun of the one catastrophe in this history - roughly
break-even on that term alone, and positive once the ordinary defects both arms found are counted. **It is no
longer refuted.** Three caveats keep it second: break-even requires another such item in the next 137; the
ordinary-defect saving is bounded below rather than measured, from n=2 with a nonzero false-positive rate; and
**F3 catches the same catastrophe class by construction at 1/137th of the cost.** No arithmetic makes universal
review a better FIRST move than F3.

---

## 7. Recommendation

**Committed now, because it does not depend on P(catch):**

- **F3, teeth on the two-cycle rule.** It costs 0.71h across the entire history, its trigger is an event the
  author cannot author, it satisfies R7, and it is enforcement of a rule we already wrote and already believe.
  It would have forced the specification question at round 2 of WARP-1210 by construction.
- **F1, shrink the item.** It is the recorded root cause, it is the only candidate that touches R6, and its
  marginal cost is near zero because the split was already required.
- **Withdraw C.** It is already in force and demonstrably insufficient.
- **Emit review lifecycle events** as a precondition. `.veldo/events.jsonl` holds 594 events, every one
  `gate.passed` or `gate.failed`; there are no `spec.ready`, `review.passed` or `review.failed` events at all,
  although validate.py declares those kinds. F3 has nothing to fire on until they exist, and R5 has nothing
  to measure against for any future item.

**Now measured, and it changes the ambition:** a pre-build design review is defensible, not refuted. P(catch)
came back 1 of 1 on the honest generic arm, the measured cost is 13.2 minutes rather than the 42.6 I had
budgeted, and both arms found real design defects on an ordinary spec beyond the one catastrophe. So:

- **Add a pre-build adversarial design review, as JUDGEMENT not checklist.** The generic brief caught
  everything the codified brief caught, so the four-component checklist is optional polish. Build the reviewer,
  not the gate. This is option D with the mechanical half deferred indefinitely rather than sequenced.
- **On which signal: start at `footprint >= 15`** (2.0h total, 30% trigger, author-resistant because footprint
  is validated against the architecture contract) and revisit toward universal once there is data beyond n=2.
  Not acceptance-criteria count, which is author-editable prose and grants automatic exemption to anyone
  complying with the standing 3-to-4 rule.
- **Sequence is F3, then F1, then the review.** F3 costs 0.22h and catches the catastrophe class by
  construction; nothing beats that as a first move.

---

## 8. What would refute this analysis

- If P(catch) is low, every option that adds a review phase fails R5 and only F1 and F3 stand.
- If the eleven rounds are mostly iteration-injected rather than design-attributable under section 3's stated
  rule, F1 dominates everything and design review is a minor correction.
- If footprint proves as author-editable as criterion count, the signal question reopens.
- **Withdrawn from version 1:** "the method's own laws were discovered, not designed" was an unbacked
  universal drawn from the two-day window selected BECAUSE failures produced laws there. Counterexamples sit
  outside it: all 17 plans declare constraints and non-goals upfront, and PLAN-0011 C6 ("decisions are judged
  against the problem class; it is only one process today is not a rationale the record may carry") was
  designed before any recorded failure of that shape and is now enforced by `decision_review.py`. The narrow
  claim survives: the laws added on 2026-07-25 and 2026-07-26 were extracted from failures.

---

## 9. Decisions needed from Dmitry - ALL NINE, TOGETHER

Version 1 asked four and made five more inside its own recommendation. That is the failure he named, so all
nine are here.

1. **Do we ship F3 (teeth on the two-cycle rule) now?** 0.71h across 133 items. Recommend yes.
2. **Do we ship F1 (the same signal triggers SPLIT rather than REVIEW)?** Recommend yes.
3. **Is a pre-build design review added at all?** Recommend deferring until P(catch) reports.
4. **WHICH SIGNAL**, if one is used: footprint count (validated, author-resistant, 30% trigger) or
   acceptance-criteria count (author-editable, 82% trigger)? Recommend footprint. This is a bigger decision
   than the cut point, and version 1 never asked it.
5. **What does a design refusal DO?** Block `ready`, or advise? What records it, what unblocks it, who
   arbitrates a disputed refusal? R4 is unmet until this is answered.
6. **Does the three-round cap apply to design reviews?** An uncapped adversarial review of PROSE reproduces
   the WARP-1210 loop one phase earlier, where there is no gate to settle an argument.
7. **Is a design verdict a bound artifact or a conversation?** Code verdicts bind to a proof digest;
   `decision_review.py` refuses an unbound review. Recommend bound.
8. **What happens to the specs already above whatever threshold is chosen?** Grandfathered, swept, or
   reviewed on next touch. Recommend grandfathered.
9. **Does the method's own development get held to this, including the item that introduces it?**
   Recommend yes.

---

## 10. Next step

Land P(catch) from both arms, fill the one PENDING slot, then a second independent adversarial design review
of THIS document, then the proposal goes to Dmitry with all nine decisions together. Version 1 went to review
before it went to him, which is the only reason its three fatal errors are in this document instead of in his
inbox.
