# INDEPENDENT ADVERSARIAL DESIGN REVIEW of INVERSION-problem-statement-and-options.md

**VERDICT: needs_rewrite**

Reviewer: fresh context, did not write the document, instructed to refute it. Read-only on
`/path/to/repo` throughout: no gate run, no worktree, no branch, no write of any kind in that
repository. Every figure below was reproduced independently from `git log`, `git show`, the spec corpus, the
verdict artifacts and `.veldo/`, and the command or method is named so it can be re-run.

Three findings are FATAL, and each one changes a different layer: the economics of the recommendation, the
problem statement itself, and the stopgap that would ship today. That combination is not repairable by
editing sentences, so the verdict is a rewrite rather than a fix list. The measured population figures in
section 2 survive and should be carried forward intact; they are the strongest part of the document.

---

## FATAL 1 - the recommended threshold is net-negative on the document's own history, at the document's own asserted review cost

**Attacked:** claim 4, section 5's "R3's threshold", decision 1, the 90-to-1 asymmetry.

**What I checked.** I counted acceptance criteria across the WHOLE spec corpus using the repository's own
counting logic (`spec_criterion_ids` in `.veldo/validate.py`: ids matched inside the YAML front matter),
not a hand-picked sample. 137 specs in `specs/` excluding `index.md` and `TEMPLATE.md`.

**What I found.** The AC distribution is `{2:2, 3:7, 4:16, 5:78, 6:21, 7:10, 8:2, 10:1}`.

| trigger | fires on | share of corpus | catches (of the 5 troubled items) |
|---|---|---|---|
| universal (option A) | 137 of 137 | 100% | 5 of 5 |
| **AC >= 5 (recommended)** | **112 of 137** | **81.8%** | 5 of 5 |
| AC >= 6 | 34 of 137 | 24.8% | 3 of 5 |
| AC >= 7 | 13 of 137 | 9.5% | 1 of 5 |

**AC >= 5 is not a threshold. It is "review everything" with 25 items exempted.** It costs 82% of what
option A costs, and the document already ruled that option A fails R3. So the document's own rejection of A
applies to its own recommendation, and the sentence "option B is viable after all" does not survive its own
measurement.

Now the arithmetic the document never runs. The 90-to-1 ratio prices ONE false positive against ONE false
negative. That is a base-rate fallacy: the policy buys about 107 false positives for the 1 catastrophic true
positive in this history, so the decision-relevant quantity is total policy cost against expected saving,
not the per-instance ratio.

- The thing being prevented: WARP-1210's overrun above the project mean is 34.37h - 1.19h = **33.2h**
  (whole item 34.4h).
- Policy cost at the document's OWN asserted 20 minutes: 112 x 20 min = **37.3h**.
- Policy cost at measured review cost (see below, mean 42.6 min over 11 verdicts): 112 x 42.6 min = **79.6h**.

**The recommendation is a net loss even if the 20-minute assertion is granted in full, and even if the
review catches the failure with probability 1.** I do not need the 20 minutes to be wrong to refute the
recommendation; I only need the trigger rate, which is 81.8% and measured. This is the whole finding: the
document attacked the wrong operand. It defended the per-review cost and never checked how many reviews the
threshold buys.

**On the 20 minutes specifically, since the document rests a decision on it.** It is asserted and nowhere
measured. The only measurement of adversarial review cost that exists in this repository is the WARP-1210
review series itself, which I measured as the interval from each round's evidence commit to the mtime of the
verdict file that reviewed it:

| verdict | evidence commit | verdict written | minutes |
|---|---|---|---|
| 1 | 07-24 19:20 | 07-24 19:47 | 26.6 |
| 2 | 07-24 20:46 | 07-24 21:26 | 40.2 |
| 4 | 07-25 08:08 | 07-25 08:37 | 29.2 |
| 5 | 07-25 11:06 | 07-25 11:41 | 34.3 |
| 6 | 07-25 13:30 | 07-25 14:17 | 47.2 |
| 7 | 07-25 15:49 | 07-25 16:08 | 18.4 |
| 8 | 07-25 17:24 | 07-25 17:48 | 23.7 |
| 9 | 07-25 21:04 | 07-25 21:42 | 38.4 |
| 10 | 07-25 23:11 | 07-25 23:41 | 30.5 |
| 11 | 07-26 01:52 | 07-26 02:52 | 59.3 |
| 12 | 07-26 04:50 | 07-26 06:51 | 121.3 |

n=11, mean **42.6 min**, median 34.3, range 18.4 to 121.3. These are CODE reviews, which have a gate result
and a manifest to lean on. My own cost for this design review is at the bottom of this document. A
defensible planning range is 20 to 45 minutes, and the conclusion above holds across all of it.

**FIX.** Replace the per-instance ratio with an expected-value test stated explicitly:
`trigger_rate x population x review_cost < P(catch) x expected_saving`. Then publish the candidates that
pass it. From this history: AC >= 6 costs 24.2h at measured cost, fires on 24.8%, catches 1210 plus two
others, and needs P(catch) > 0.73 to pay. The second-failed-review trigger (FATAL 2, BLOCKING 6) costs
0.71h. Both pay. The recommended AC >= 5 does not, under any review cost above 18 minutes. And state
P(catch) as an unknown that must be measured, because nothing in this document establishes it.

---

## FATAL 2 - claim 1's refutation condition FIRES: three existing checks attack the design, and one of them is the mechanism this document proposes to invent

**Attacked:** claim 1 ("finding an existing independent check on the design phase" refutes it), section 1's
"the design is checked by a schema validator", section 6's third bullet.

**What I checked.** `ls .veldo/`, then read the module headers of every file whose name suggested a review or
gate function, then the shipped agent briefs and skills in `packs/claude/`, then `git log` for when each landed.

**What I found. Three of them, all shipped, all predating WARP-1210.**

1. **`.veldo/decision_review.py`** (WARP-1106, landed 2026-07-22, commit 9f15c8f). Its own docstring: "VELDO
   adversarial decision review (veldo.decision_review/v1): a foundational choice is ATTACKED by a fresh
   context before a human commits to it". Its four named dimensions are PROBLEM-CLASS CHALLENGE, PER-OPTION
   CHALLENGE, **MISSING OPTIONS**, PER-ASSUMPTION CHALLENGE, and it gates a decision record from reaching
   `decided` until a recorded adversarial review exists. That is an independent adversarial design review
   with teeth, already built, on a sibling artifact. The document does not mention it once.

2. **`packs/claude/agents/veldo-reviewer.md`** (landed 2026-07-16, commit c5c0c8d, present in the file's first
   version, verified with `git show c5c0c8d:`): "Judge the change against the Intent section of the
   specification, not only the acceptance criteria: a change that satisfies the letter while missing the
   intent fails." **That is option C, already shipped, ten days before this document proposes it.**

3. **`packs/claude/skills/review/SKILL.md`** (same commit): "A fail returns the change to implementation. **After
   two failed cycles on the same specification, stop and bring in the human: at that point the defect is
   almost always in the specification.**" WARP-1210 ran ELEVEN cycles.

There is also a pre-build mechanical design check with real semantic content, not just schema: W3's
placement and footprint validation refuses a spec reaching `ready` without a placement that resolves to a
declared architecture area, and raises the risk tier on a boundary crossing (`.veldo/validate.py check_ready`
/ `check_placement`, spec template lines 14 to 21). And `.veldo/shape_review.py` carries a DELEGATED
fresh-context judgment on whether a change follows the declared patterns of the areas it touches, which is
design judgment, albeit post-build.

**Why this is fatal rather than a citation gap.** The document's problem statement is "the design has no
adversary, therefore build one." The artifacts say something different and more uncomfortable: the design
had a routing rule with a human escalation at two failed cycles, and the item that motivated this whole
document ran eleven. A new phase built to replace a rule that was not obeyed will be a fifth mechanism in
the same position as the fourth. That is the same error the owner already caught once this week in
WARP-0721: rigour aimed at the wrong shape.

**FIX.** Rewrite section 1. State the real, narrower gap, which survives: **no adversary attacks a SPEC's
design at spec granularity before the build.** `decision_review.py` covers foundational CHOICES (veldo.decision/v1
records); `shape_review.py` covers architectural fit AFTER the build; the reviewer brief covers intent
but only once code exists. Then re-derive the options from that gap, with "extend the organ that already
exists" and "give the two-cycle rule mechanical teeth" as first-class options rather than absences.

---

## FATAL 3 - option C is refuted by the artifact it claims it would have caught, and option C is the half that ships today

**Attacked:** section 5, "That alone would have surfaced 1210's root cause in round 1 instead of round 12";
decision 2 ("Recommend yes").

**What I checked.** Read `proof/WARP-1210/verdict-1-fail-round1.json` in full structure: reviewer identity,
per-criterion rulings, findings, the schema-gap ruling, the gate observations, and the disposition.

**What I found.** The round-1 review was not a code-only review that happened not to look at the spec. It
had the spec, it ruled per-criterion on AC1 through AC6, it ruled AC1 **refuted**, it issued a separate
`schema_gap_ruling` on a declared limitation in the spec's own terms, and it was operating under a standing
instruction to fail a change that satisfies the letter while missing the intent. It named three blocking
code defects. **It did not name the domain gap.**

So the counterfactual is not merely unsupported; the nearest available observation is a MISS by a reviewer
already doing what option C asks for. "Instruct the existing reviewer to also rule on the spec" is a change
to a brief that already says that.

**Why this matters most of all.** C is described as "nearly free" and "captures most of the value today,"
which makes it the thing most likely to ship unexamined tomorrow morning. It would ship a rewording of an
instruction that has been in force since 2026-07-16, and it would be recorded as having addressed the
inversion.

**FIX.** Delete the counterfactual, or replace it with the only claim the artifacts support, which is
stronger and cheaper: obeying the EXISTING two-cycle rule would have forced the spec question at round 2 by
construction, requiring no new judgement from anyone and no new phase. Measured base rate for that trigger:
across 133 items with proof directories, exactly ONE ever reached two failed reviews (WARP-1210 at eleven;
WARP-1208 and WARP-0616 have one each). Cost 0.71h. That is the derived, over-triggering-proof, zero-tax
trigger the document says it wants and did not find.

---

## BLOCKING 4 - claim 2 has no attribution rule, so it is not falsifiable as stated, and the verdicts point away from it

**Attacked:** claim 2 ("A design error's cost is multiplied by the rounds it survives"), its observation
column ("rounds attributable to one design omission"), section 1's "one undeclared domain / twelve builds".

**What I checked.** I extracted and classified every finding in all 11 verdict files (34 findings), using
the reviewers' own severity labels rather than my paraphrase.

**What I found.**

- **No attribution rule is stated anywhere.** "Rounds attributable to one design omission" has no defined
  test, so no observation can settle it. This is the identical defect class that refuted WARP-0721 hours
  earlier: a count with no rule for what counts.
- **At least three defects were injected BY the repair rounds.** The reviewers' own labels: R5-B2 "blocking,
  and a REGRESSION this round introduced"; R8-B1 "blocking - a REAL DEFECT, a ROUND-8 REGRESSION"; R11-B3 a
  2.05x gate-cost regression "Ruled a DEFECT, not a tradeoff". R3-B4 is a defect in code round 3 newly
  wrote. No design review of the original spec can prevent a defect that round 8 creates.
- **The author's own record says exactly this and the document omits it.** `project_veldo.md`, 2026-07-25:
  "each round writes NEW code and new code has new defects - round 8's crash did not exist until round 8
  created it, so no care in round 7 could have caught it. That argues for SMALLER CHANGES, not more
  diligence." And: "**THE ACTUAL DISEASE IS ITEM SIZE**, and here is the measurement that proves it:
  running the gate on round 9's half-finished tree, changing ONE rule broke TEN separate assertions."
  Neither sentence appears in the document, and the document proposes more diligence.
- **About 13 of the 34 findings are manifest and prose honesty findings**, a recurring authorial pattern
  that a design review does not touch at all.
- **One genuine multiplied thread does exist**, and I want to be precise because it is the part that
  survives: the sweep-key class widened five times, recursion -> exception classes -> read primitives ->
  declared sources -> transitive closure of what is opened on the item's behalf, rounds 8 through 12, and
  round 12's verdict (written 06:51 today, while this review was running) reports R12-B1 as a fifth member
  still open. That is a real multiplier. But it was widened BY REVIEWERS across rounds; it is not the same
  object as "one undeclared domain in the original spec," and the original spec's domain gap is a third
  thing again.

**FIX.** State the attribution rule before the claim. Publish the per-round classification as evidence, not
the conclusion. Then split claim 2 into the part the evidence supports (one defect class widened across five
rounds and is still open) and the part it does not (30 hours caused by one design omission). The 25x figure
should be deleted or re-derived against the rounds actually attributable under the stated rule.

---

## BLOCKING 5 - "rounds whose finding was PROSE only: 7 of 11" does not reproduce, and it inverts

**Attacked:** section 2, evidence table, row 9, sourced to "verdicts 1-11".

**What I checked.** Every verdict's findings and their reviewer-assigned severity strings.

**What I found. Zero of the eleven rounds are prose-only.** Every single verdict contains at least one
finding its own reviewer labels a real defect: R1 F1 to F3 all "blocking" with F1 "the worst of the three";
R2 both; R4 B1 to B4; R5-B2 the regression; R6-B2 "the half that is a real defect"; R7-B4 "this half is a
DEFECT rather than prose"; R8-B1 "a REAL DEFECT"; R9-B1 "a REAL DEFECT with TWO members"; R10-B1 and
R10-B2 both "a REAL DEFECT"; R11-B1 "a REAL DEFECT with FOUR members" and R11-B3 "a DEFECT rather than a
tradeoff"; R12-B1.

What DOES reproduce: 9 of 11 rounds contain at least one prose or honesty finding (R1 and R2 contain none),
and 0 of 11 are prose-only. The author's earlier record says something different again and narrower: "four
[of nine] were arguments about wording."

**Why it matters beyond accuracy.** As written the cell supports the reading that the rounds were ceremony.
The artifacts support the opposite reading: the item was genuinely defective in eleven distinct sittings,
which is claim 2's own stated refutation condition. A figure in a table headed "measured rather than
asserted" that reverses the argument's direction is not a typo.

**FIX.** Recount, restate as "9 of 11 rounds carried at least one prose finding; 11 of 11 carried at least
one real defect," and follow the repository's own rule after three consecutive non-reproducing label diffs:
publish the figure with the command that produces it, or state the property and delete the number.

---

## BLOCKING 6 - the threshold table reports a POST-HOC acceptance-criteria count for the single item that decides the threshold

**Attacked:** section 5's table row "WARP-1210 | 30 | 7 | standard"; decision 1.

**What I checked.** AC count at every commit that touched `specs/WARP-1210-the-support-numbers.md`, using
the repository's own counting method, plus the same drift check across all 137 specs.

**What I found.** WARP-1210 was authored with **6** acceptance criteria and carried 6 at `c37e833`,
`2ba8350`, `ffc3bd6` and `1baa755`. It reached 7 at `d283ae1`, which is round 4, when the owner's option-A
decision rewrote AC3 and preserved the old text as a new AC3b. `project_veldo.md`, 2026-07-25, states the
mechanism outright: "The old AC3 soft-join text is preserved as AC3b."

Two consequences:

1. A design-time trigger must be evaluated on the spec AS AUTHORED. Only 2 of 137 specs drifted at all
   (WARP-0612 and WARP-1210, both 6 to 7), so the population figures are safe, but the one number the
   recommendation hangs on is the wrong number.
2. **A threshold at AC >= 7, which the table's "7" makes look adequate, would have MISSED WARP-1210
   entirely.** At design time the troubled set is 1210=6, 0614=6, 1208=6, 0616=5, 0623=5. So AC >= 7 catches
   0 of 5 and AC >= 6 is the only AC threshold that both pays (FATAL 1) and catches the catastrophic item.

**FIX.** Publish design-time counts for the whole comparison table, state that the count is taken at
`ready`, and re-derive.

---

## BLOCKING 7 - the trigger is author-controlled and prose-editable, and the repository's own sizing rule turns compliance into exemption

**Attacked:** decision 1, R4, the AC >= 5 mechanism.

**What I checked.** How WARP-1210's count actually moved; the standing house rule on item size; the trigger
rate against it.

**What I found.**

- The count moved by **splitting one criterion's prose in two** (AC3 to AC3 plus AC3b). No design changed.
  A signal that moves when you reformat a sentence is not a measurement of design size, and the author
  controls the sentence.
- The standing HARD rule already in force is `feedback_smaller_tickets`: "ONE concern per item, ~3-4
  acceptance criteria MAX, split BEFORE building." So an author who COMPLIES with the house rule lands at 4
  ACs and is **automatically exempt** from the design review, and an author who wants to dodge the gate
  writes four fatter criteria. The gate rewards the exact behaviour it should catch.
- This is the same hole that refuted WARP-0721 hours earlier: a count signal with no granularity rule.

**A measurably better signal exists, with a caveat I will state rather than hide.** Footprint path count is
declared in the spec and validated against the architecture contract, so it is not free prose. Among the 30
specs that declare a footprint (all 5 troubled items are in that population): AC >= 5 fires on 28 of 30
(93%) and catches 5 of 5; AC >= 6 fires on 13 of 30 (43%) and catches 3 of 5; **footprint >= 15 fires on 9
of 30 (30%) and catches 3 of 5**, which dominates AC >= 6 at equal catch. WARP-1210 declares 45 footprint
paths against a corpus median of 0 and a p90 of 13. **Caveat:** footprint is declared on only 30 of 137
specs (21.9%) because it became mandatory with PLAN-0011 W3, and all five troubled items are recent, so part
of that selectivity is a coverage artifact. It is mandatory going forward, so coverage is 100% for future
items, but the comparison is over 30 items and should be reported as such.

**FIX.** Either move to a signal the author does not freely control (footprint count, validated against the
contract), or make the trigger an event the author cannot author at all (the second failed review). If AC
count stays, state a granularity rule for what one criterion is, because without it the number means
nothing.

---

## BLOCKING 8 - the five options are not exhaustive, and the missing option is the author's own recorded root cause

**Attacked:** section 4 (options A to E), section 3 (R1 to R5).

**What I found. Three options the document never records.**

- **F1. Shrink the item so no design is big enough to be expensive to get wrong.** This is the author's own
  recorded root cause from the previous day ("THE ACTUAL DISEASE IS ITEM SIZE... Fix = smaller tickets"), it
  is an existing HARD rule (~3-4 ACs max), and it has a structural half already specified (WARP-0712).
  Crucially it reuses the SAME measurement: on AC >= 5 the mechanical action becomes SPLIT, not REVIEW.
  Splitting is work that was going to happen anyway under the standing rule, so its marginal cost is far
  below 42.6 minutes, and it attacks the mechanism the author identified as not fixable by diligence
  ("each round writes NEW code and new code has new defects").
- **F2. Extend the organ that already exists.** `.veldo/decision_review.py` already attacks a design
  artifact adversarially in a fresh context with four dimensions including MISSING OPTIONS, and already
  gates a state transition. Extending its domain from veldo.decision/v1 records to specs is a smaller change
  than a new phase and inherits a schema, a binding, and a fail-closed gate.
- **F3. R2 standing alone as its own option.** A mandatory spec-defect finding class: an implementation
  reviewer's finding that indicts the SPEC blocks further building until the spec is amended or a human
  rules. This is the shipped two-cycle rule given mechanical teeth. Measured cost: 1 item in 133, 0.71h.
  It is the only candidate here whose trigger the author cannot influence and whose cost is negligible.

**On R1 to R5 themselves.** R1, R3, R4 and R5 derive from the evidence. **R2 does not read as a
requirement; it reads as an option that was demoted into one** ("Route review findings back into the DESIGN
phase... Eleven reviews produced eleven code patches and zero design-gate changes"). And the requirement the
evidence most strongly supports is absent: nothing in R1 to R5 says the mechanism must be able to prevent
defects INJECTED BY ITERATION, which the author measured as a distinct and larger class.

**Does the recommendation satisfy R4?** Not demonstrably. R4 says the mechanism "must be able to REFUSE a
plausible-looking answer," and the document never states what a design review REFUSES, what artifact records
the refusal, what unblocks it, or who arbitrates a disputed refusal. Compare `decision_review.py`, which
answers all four for decisions. As written, option D satisfies R4 by assertion.

**FIX.** Record F1, F2, F3. Re-run the requirement derivation against the full option set. State R2 as an
option and add the iteration-injection requirement.

---

## BLOCKING 9 - the four decisions are not all of them, and he objected specifically to decisions arriving one at a time

**Attacked:** section 7.

At least five decisions are made inside the recommendation and not put to him.

1. **Which signal.** Decision 1 asks universal-or-AC>=5 and never asks whether AC count is the right signal.
   Footprint separates better on the population where both exist (BLOCKING 7). Choosing the signal is a
   bigger decision than choosing the cut point on it.
2. **Is a design refusal blocking, and what unblocks it.** R4 demands refusal power; nothing states what
   refusal means operationally, whether it prevents `ready`, or who arbitrates.
3. **Does the three-round cap apply to design reviews?** The repository adopted a three-round cap for code
   reviews on 2026-07-25 precisely because of this item. An uncapped adversarial design review reproduces
   the WARP-1210 loop one phase earlier, on prose, where there is no gate to settle an argument. The
   document does not mention the cap.
4. **Is the design verdict a bound artifact or a conversation?** Code reviews bind to a proof digest so a
   verdict cannot be reused. `decision_review.py` binds a review to a decision and refuses an unbound one.
   Nothing says whether a design verdict has a schema, a binding, or a home.
5. **What happens to the 112 already-shipped specs above the threshold?** Grandfathered, swept, or
   reviewed on next touch.

**FIX.** Add all five to section 7. A missing decision is the failure mode he named.

---

## BLOCKING 10 - the document contradicts itself on WARP-1210's risk tier, and the contradiction is load-bearing

**Attacked:** line 88 against lines 134 and 143.

Line 88 (option B's rejection): "WARP-1210 was rated **high**, not critical, and would have needed the line
drawn at high to be caught - which would catch a large fraction of all items anyway." Line 134 (the measured
table) and line 143 (FINDING 1) say `standard`.

I verified the spec: `risk: standard - this item DERIVES and RENDERS...`. The true corpus distribution,
first token of the risk field across all 137 specs, is 126 standard, 10 high, 1 critical. So the document's
own FINDING 1 is correct and line 88 is wrong.

This is load-bearing, not cosmetic: line 88's rejection of a risk-based threshold is argued from "high would
catch a large fraction of all items anyway," and the real data says a `high` threshold fires on 10 of 137
(7.3%) and catches NONE of the five troubled items. The right rejection is FINDING 1's, which is stronger.
Leaving both in the same document is a contradiction he will find.

**FIX.** Delete line 88's clause and point option B's rejection at FINDING 1.

---

## NOTE 11 - the mean is the wrong statistic for R3, and claim 4's domain is not the population the threshold acts on

Reproduced independently from `git log` with a primary-id parse. **All of these hold:** 145 distinct primary
ids (133 VELDO, 12 PLAN); 139 of 145 at 1 to 3 commits (96%); max 6 commits for any other item (WARP-0614,
WARP-1208, PLAN-0011); WARP-1210 at 30 commits and 34.37h; nothing between 6 and 30. "Rework is a lone
outlier, not systemic" survives cleanly.

Mean first-to-last span is **1.21h** with the id-at-subject-start parse and 1.29h if the id may appear
anywhere, against 1.19h published, so the headline figure reproduces within about 2%. But:

- **Median is 0.31h (19 minutes)**, 53% of items have a span under 20 minutes, and 21 items have a span of
  exactly 0 because they are single-commit. R3's sentence "a 1.19h item cannot carry an hour of design
  review" is anchored on a mean that one 34h item inflates by roughly 40%.
- **The 1.19h figure IS independently defensible on a different derivation**, and the document should use
  that one: summing inter-commit gaps capped at 2h gives 173.1h of active time over 145 items = 1.19h per
  item. That is a throughput measure and it is the right denominator. Say so, because as published the
  figure is sourced to "first-to-last commit per id," which yields a median of 19 minutes and invites
  exactly the objection that the mean measures queueing.
- **Domain mismatch.** Claim 4's domain is "the 145 delivered items," which includes 12 PLAN ids and
  excludes 4 specs with no commits (WARP-0201 to 0204). The threshold acts on the 137 specs. Two
  populations, silently. That is precisely the class of error the document says a schema validator cannot
  catch, in the document's own claim register.

**FIX.** Publish median and distribution beside the mean, state the derivation actually used, and name the
population each figure is over.

---

## NOTE 12 - claim 3's count does not reproduce, and its refutation condition fires outside the chosen window

Counting bolded rules in the 2026-07-25 and 2026-07-26 sections of `project_veldo.md` I reach at least eight
candidates, not 6: the three-round cap; builder self-audit against the whole spec before declaring done; NO
UNBACKED UNIVERSAL; MEASURE FIRST then write the sentence from the output; declared depth bound plus a
RecursionError backstop; the sweep law; the sweep law refined to transitive closure; a cost regression is a
checkable claim by omission; publish-with-command-or-delete-the-number; smaller tickets. **No counting rule
is stated**, which is the same defect as WARP-0721's count signal with no granularity rule.

The refutation condition is "finding a law that was specified before its first failure," and it fires
outside the two-day window:

- Method v1.1's raise-risk-never-lower law and its letter-not-intent failure mode both came from a
  fresh-eyes REVIEW of the method, not from a failure (`project_veldo.md`, 2026-07-16).
- All 17 plans declare `constraints` and `non_goals` upfront. PLAN-0011 C6 reads "Decisions are judged
  against the problem class... 'it is only one process today' is not a rationale the record may carry,"
  designed before any recorded failure of that shape, and now enforced by `decision_review.py`'s
  problem-class challenge. PLAN-0011 NG5 ("the gate never carries a vacuous check") is enforced by
  `shape_gate.py`.

So the domain of claim 3 is a two-day window selected because it is the window in which failures produced
laws, and the promise generalises from it to "the method's own laws," plus "the method is being built by the
anti-pattern it exists to prevent." **That is an unbacked universal drawn from a convenient sample, which
violates the method's own promoted law 1 and repeats WARP-0721's one-convenient-fixture defect.**

**FIX.** Narrow the promise to what was measured ("the laws added on 2026-07-25 and 2026-07-26 were
extracted from failures"), state the counting rule, and drop the generalization to the method.

---

## NOTE 13 - claim 1's promise as worded states the opposite of the thesis, and its observation is a proxy

"Verification is concentrated where errors are cheapest to find" describes a healthy system. The document's
argument is that verification is concentrated where errors are cheapest to FIND and most expensive to FIX.
And the observation column counts which phases have an adversary, which is a proxy for a claim about cost,
not an observation of it. This is the same component mismatch that refuted WARP-0721: the promise, the
observation and the refutation condition are not about the same thing.

**FIX.** Word the promise as the defect ("verification is concentrated after the cost of an error has
already been multiplied") and observe the cost, not the adversary count.

---

## NOTE 14 - decision 3 presents a false binary and omits the policy already in force

Decision 3 offers "a fresh agent context (cheap, available, no independence from the model) or a human." The
repository's `.veldo/policy.yaml` already answers most of this: L2 independence is required at EVERY tier,
defined as "reviews the operator initiates run on a fresh-context DIFFERENT Claude model (Opus family)",
with cross-vendor L3/L4 reachable on the owner's explicit per-case instruction. Measured across the corpus:
133 verdicts by `claude-opus-4-8[1m]`, 14 by `claude-opus-5[1m]`, 1 by `claude-fable-5`, so model diversity
is practice and not aspiration.

On the substantive question the prompt raises, my honest ruling: a different-model fresh context is a real
second sample, not a full independence guarantee. The author's five self-refutations of WARP-0721 show the
capability exists; that they arrived only after the owner asked shows the TRIGGER is what is missing, not
the capability. **The proposal has no mechanism that fires without the owner noticing.** F3 (a mandatory
spec-defect route on the second failed review) is the only candidate in or near this document that does,
because its trigger is an event in the loop rather than a person's attention.

**FIX.** State the existing ladder, ask the narrower real question (does a design review need L3 rather
than L2), and name what fires the mechanism when nobody is watching.

---

## NOTE 15 - R5 has no instrument: the method cannot observe its own review loop

`.veldo/events.jsonl` holds 594 events, and every one is `gate.passed` (550) or `gate.failed` (44). There are
no `spec.ready`, `review.passed` or `review.failed` events at all, although `validate.py` declares those
kinds. That is why the round counts in this document had to be assembled from filenames and git rather than
from the method's own instrumentation.

Two consequences: R5 ("be proven against the failure that motivated it") has nothing to measure against for
any future item, and the second-failed-review trigger has nothing to fire on until review events are
actually emitted.

**FIX.** Name emitting review lifecycle events as a precondition of whatever ships.

---

## NOTE 16 - two figures in the "measured rather than asserted" table did not reproduce at the time of writing

- "twelve builds, eleven failed reviews." I count **11 build attempts** (each an implementation or fix
  commit followed by an evidence commit) and, at the document's 05:22 mtime, **10 verdict files**;
  `verdict-12-fail.json` was written at 06:51 today, after the document. Round numbering skips 3 (there is
  no verdict-3; the third build's verdict is labelled round 4), which is the source of the off-by-one.
- "real defects found in rounds 8-12: 5 distinct, all pre-existing" is contradicted by the round-8
  verdict's own severity string: R8-B1 is "blocking - a REAL DEFECT, a **ROUND-8 REGRESSION**".

The repository's own rule after three consecutive non-reproducing label diffs applies here: publish a figure
that reproduces from a stated command at stated revisions, or state the property and delete the number. The
document commits the exact sin it catalogues.

---

## NOTE 17 - house style: PASSES

Zero non-ASCII characters in the document (checked every codepoint above 127: none). The only doubled-hyphen
occurrences are markdown table separators on lines 11, 45 and 133, which are markup, not prose. No em dash,
no en dash, no prose double hyphen. This review is held to the same standard.

---

## What survived my attack, and what I did to try to break it

- **The population figures. All of them.** 145 primary ids, 139 of 145 at 1 to 3 commits, max 6 elsewhere,
  WARP-1210 at 30 commits and 34.4h, nothing between 6 and 30. I re-derived every one from `git log` with
  three different id-extraction rules and they held. The 1.19h mean reproduces to within 2% on the
  subject-start parse and exactly on a gap-capped active-time derivation. Carry this section forward intact;
  it is the best work in the document.
- **FINDING 1, that risk tier discriminates nothing.** I tried to break it by computing the true tier
  distribution across all 137 specs rather than the five sampled: 126 standard, 10 high, 1 critical, and all
  five troubled items are standard. A `high` threshold fires on 7.3% of the corpus and catches none of them.
  The finding is correct and understated, and it also refutes the document's own line 88.
- **FINDING 2, that AC distributions overlap.** Confirmed and worse than reported. I tried to break it by
  measuring the complete corpus instead of a hand-picked well-behaved sample, expecting the sample to have
  been flattering. It was: 78 of 137 specs sit at exactly 5 ACs, so the overlap is not a tail effect, it is
  the mode.
- **The core observation, in narrowed form.** No adversary attacks a spec's design at spec granularity
  before the build. I tried hard to break this by reading every `.veldo/` module header, both gate scripts,
  all five agent briefs and all ten skills, and I found three adjacent mechanisms (FATAL 2) but none that
  attacks a SPEC pre-build. The gap is real. It is narrower than claimed and its nearest neighbour is a
  shipped organ to extend.
- **Claim 2, as one thread only.** The sweep-key class genuinely widened five times across rounds 8 to 12
  and is still open at round 12. That is a real multiplier, and I could not break it. It does not support
  "30 hours from one design omission."
- **Option E's rejection.** Correct, and for the right reason.

## The one thing I would attack next, given more time

**Run the experiment that establishes P(catch), because every affordability number in the document is
multiplied by it and nothing measures it.** Take WARP-1210's spec at `c37e833`, which is the authored
version with 6 ACs before any build, into a fresh context under the design-review instruction, and see
whether it names the domain gap. The only observation currently available is a MISS (FATAL 3), so P(catch)
could plausibly be low, and at a low P(catch) even the thresholds that pass FATAL 1's arithmetic stop
paying. It is one review, roughly 40 minutes, it converts R5 from an assertion into a measurement, and it
should be run BEFORE the owner is asked to decide anything, because decisions 1, 2 and 4 all change sign
depending on the answer.

## My own cost datum, which is the only honest measurement of design-review cost available

- **Wall clock: 18 minutes** (first read of the document at roughly 06:43 EDT, review file written at 07:01
  EDT on 2026-07-26). Measured the same way I measured the code reviews above, start of material to artifact
  written, so the numbers are comparable.
- **Reading and analysis it needed:** the 12KB document; 347 commit subjects with timestamps; all 137 spec
  front matters (programmatically, for AC counts, risk tiers and footprints); the AC-count history of
  WARP-1210 across all 13 commits touching its spec plus a drift check across all 137; all 11 WARP-1210
  verdict files (about 350KB, findings and severity fields); `.veldo/policy.yaml`; the module headers of
  `decision_review.py`, `shape_review.py` and `shape_gate.py`; `packs/claude/agents/veldo-reviewer.md` at HEAD and
  at its first commit; `packs/claude/skills/review/SKILL.md`; PLAN-0011's constraints; `validate.py`'s AC counting
  function; the 2026-07-25 and 2026-07-26 sections of `project_veldo.md`; and 594 event records. Six
  throwaway analysis scripts.
- **What that says about the document's 20 minutes.** It is closer to right than the code-review data alone
  suggests, and I will say so plainly rather than bank the convenient number: a design review of a 12KB
  argument came in at 18 minutes, against measured code reviews at a mean of 42.6 minutes. So roughly 20 to
  45 minutes is the defensible planning range, and the document's 20 sits at the optimistic edge of it rather
  than being wrong. It remains an ASSERTED number in the document and must be published as a measurement
  with its method, not as a parenthetical.
- **And it does not rescue the recommendation.** FATAL 1 holds at 18 minutes, at 20, and at 42.6, because
  what kills AC >= 5 is the 81.8% trigger rate, not the per-review cost. At 18 minutes the AC >= 5 policy
  still costs 33.6h against a 33.2h saving. That trigger rate is the one number the document never measured.
