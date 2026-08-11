# SECOND INDEPENDENT ADVERSARIAL DESIGN REVIEW of INVERSION-v2-problem-statement-and-options.md

**VERDICT: needs_rewrite**

Reviewer: fresh context. I did not write the document and I did not write review 1. Read-only on
`/path/to/repo` throughout: no gate run, no worktree, no branch, no commit, no write of
any kind in that repository. My only writes are this file and a throwaway analysis directory in a
scratchpad. Every figure below was re-derived from `git log`, `git show`, `git ls-tree`, the spec
corpus, the verdict artifacts, `.veldo/` and the owner's recorded memory, and the method is named so
it can be re-run.

I also ran the experiment nobody had run: a NEGATIVE CONTROL on a healthy spec. Result in its own
section below. It is the single most decision-relevant thing in this review after the arithmetic.

**Version 2 is a large improvement on version 1 and most of review 1's fixes landed.** The
population figures reproduce exactly, the trigger-rate arithmetic is now run, the false premise is
corrected, house style passes, and the pre-registration is genuine and was followed. That is not
enough. Five findings are FATAL and each breaks a different layer, and the pattern across them is
the same one that killed version 1: **the rewrite replaced one overconfident conclusion with
another, and did not test the replacement.**

Specifically: version 1's fatal error was that option C, the thing it would ship first, was refuted
by the artifact it claimed it would have caught. Version 2's F3, the thing it would ship first, is
refuted by the same artifact in the same way, and F3 arrived as a SUGGESTION IN REVIEW 1 that
version 2 promoted to a commitment without measuring it. A reviewer's proposed fix is not evidence.

---

## FATAL 1 - F3 is refuted by the artifact it claims it would have fixed, exactly as option C was, and the escalation it forces was actually exercised on that item and did not converge the loop

**Attacked:** section 5 row F3 ("the one that mattered"), section 7 bullet 1 ("It would have forced
the specification question at round 2 of WARP-1210 by construction"), section 6's closing sentence
("F3 catches the same catastrophe class by construction at 1/137th of the cost. No arithmetic makes
universal review a better FIRST move than F3"), decision 1.

**What I checked.** The full WARP-1210 commit timeline with author dates, which commits touched the
specification, and the gap-capped active time in each segment of the item.

**What I found. A human WAS brought in to rule on the specification, at round 4, and 78 percent of
the item's cost came after that.**

`d283ae1`, 2026-07-25 08:43 EDT: "WARP-1210 spec: the owner chose option A, so completeness becomes
the governing rule and the class collapses." Review 1 independently confirms this commit rewrote AC3
and preserved the old text as AC3b. After it: nine more fix rounds and eight more failed reviews.

Segmenting the item's gap-capped active time (inter-commit gaps capped at 2h, the document's own
derivation), total 25.69h at HEAD:

| segment | rounds | raw span | gap-capped | share of active |
|---|---|---|---|---|
| before F3 would fire | 1 to 2 | 2.98h | 2.98h | 11.6% |
| **what F3 saves** | 3 to 4 | 11.28h | **2.68h** | **10.4%** |
| after the human ruled on the spec | 5 to 13 | 22.60h | **20.03h** | **78.0%** |

The middle row is F3's entire reachable benefit, and 2.0h of that 2.68h is a capped overnight gap:
the observed inter-commit labour between the round-2 verdict and the owner's decision is 41 minutes
(`1baa755` 08:02, `dabec0d` 08:08, `1ac8735` 08:37, `d283ae1` 08:43).

**So on the only item in 133 that F3 would ever have fired on, its measured benefit is 41 minutes of
observed labour, at most 2.68h on the generous basis, against a 25.69h item.** The mechanism F3
relies on (escalate, the human rules on the specification, the loop converges) was exercised on this
exact item, two rounds later than F3 would have forced it, and the loop then ran nine more rounds.
"Catches the catastrophe class by construction" is not a measured claim; it is refuted by the
artifact.

**Why this is fatal rather than a correction.** F3 is what ships first. It is the only thing the
document says is "Committed now, because it does not depend on P(catch)". Its priority rests entirely
on the by-construction claim, and the sentence "No arithmetic makes universal review a better FIRST
move than F3" has, after this, no arithmetic behind it. This is structurally identical to version 1's
FATAL 3 relocated one option to the left, and the document did not catch it because review 1 handed
it the claim ("obeying the EXISTING two-cycle rule would have forced the spec question at round 2 by
construction") and version 2 adopted a reviewer's suggestion without attacking it.

**FIX.** Delete "by construction". State F3's benefit as what it is: it removes two rounds of
escalation latency, measured at 41 minutes of labour and at most 2.68h on this history's one
instance. F3 may still be worth shipping at 0.22h, and I think it probably is, but it must be argued
as a cheap latency fix and not as the answer to the catastrophe. Then re-derive the sequencing,
because the ordering argument was carried entirely by the deleted sentence.

---

## FATAL 2 - the 33.2h numerator mixes two derivations; on the document's own stated derivation the like-for-like overrun is 21.0h, and the universal reversal becomes a 9h net loss

**Attacked:** section 6 ("Expected saving is the overrun above normal: 34.37h - 1.19h = 33.2h"), the
whole second trigger table, "It is no longer refuted", `PCATCH-results.md`'s reversal section.

**What I checked.** Both derivations, at the revision version 2 was written against and at HEAD.

**What I found.** Section 2 already says the 1.19h mean is "valid ONLY on the gap-capped active-time
derivation (inter-commit gaps capped at 2h, 173.1h over 145)". I reproduced that exactly: sorting all
commits by author date and summing inter-commit gaps capped at 2h gives **173.15h over 145 =
1.1941h** at `HEAD~1`, which is the state version 2 measured. Good figure, and now pinned.

Section 6 then subtracts that from **34.37h, which is WARP-1210's RAW first-to-last commit span**, a
wall-clock number containing two overnight sleeps. The two terms are not on the same instrument.

On the same gap-capped derivation, decomposed by item (the capped gaps whose later commit belongs to
the item, which sums to the global total by construction):

| basis | WARP-1210 | project mean | like-for-like overrun |
|---|---|---|---|
| **gap-capped, at HEAD~1 (the document's own derivation)** | **22.21h** | 1.1941h | **21.0h** |
| gap-capped, at HEAD (round 13 landed) | 24.21h | 1.2079h | 23.0h |
| raw first-to-last span, both terms | 36.86h | 1.2268h | 35.6h |
| **the document's mix** | 34.37h raw | 1.19h gap-capped | 33.2h |

**Recomputing the reversal at 21.0h: universal design review costs 13.2 min x 137 = 30.1h against a
21.0h saving. That is a net LOSS of 9.1h.** The sentence "roughly break-even on that term alone" and
"It is no longer refuted" do not survive on the document's own preferred derivation. Note also that
the mix is not uniformly self-serving: on a consistent raw-span basis the overrun is 35.6h and the
universal option looks slightly better than the document claims. **The sign of the universal
conclusion flips with the derivation, and the document presents it as settled.**

**FIX.** Pick one derivation, use it for both terms, and say which. State the overrun as 21.0h
gap-capped, or 35.6h raw-span, and recompute every row of both tables. Then state explicitly that the
universal conclusion is basis-dependent, because that is the honest form of the finding and it is the
form he can act on.

---

## FATAL 3 - the attribution rule does not discriminate; applied literally it reinstates the claim the same section withdraws, which is why the document never applies it

**Attacked:** section 3's stated rule and its withdrawal, section 6's numerator, section 8's second
refutation condition.

**What I checked.** Every commit that touched `specs/WARP-1210-the-support-numbers.md` and what each
one changed.

**What I found.** The rule reads: "a round is attributable to a design omission only if the defect it
found was present in the artifact BEFORE the first build AND its fix required changing the
specification." **Nine of the eleven fix commits modify the specification**, and the edits are
substantive rather than cosmetic:

- round 10 (`2bc62cc`) adds to a criterion: "AND THE CLASS THOSE ROUNDS WERE EACH ONE MEMBER OF IS
  NAMED FROM THE HARM RATHER THAN FROM THE MECHANISM"
- round 11 (`9863a7d`) rewrites the same passage again
- round 12 (`a9e808e`) adds: "AND THE DOMAIN OF THAT RULE IS THE TRANSITIVE CLOSURE OF WHAT IS OPENED
  ON THIS PASS'S BEHALF"
- rounds 2, 5, 6, 7, 8, 9 each add footprint entries and amend criterion prose

So the second conjunct is satisfied by nearly every round. **Applied literally, the rule attributes
roughly all eleven rounds to a design omission, which is precisely the "30 hours from one design
omission" claim that the same section explicitly WITHDRAWS three paragraphs earlier.** The document
contradicts itself, and section 6 never applies the rule to the arithmetic because applying it
produces the answer section 3 disowned.

The rule is missing a granularity clause: which PART of the specification, and whether the edit
corrected an omission present at `c37e833` or added a requirement discovered during review. Without
it the rule cannot separate the three threads section 3 says it separates. **This is the third
instance in this workstream of a count with no rule for what counts** - it is what refuted WARP-0721,
it is what review 1's BLOCKING 4 asked to be fixed, and the rewrite restated the rule without making
it discriminate.

**Consequence for the arithmetic, which is the reason this is FATAL and not a wording fix.** Take the
document's own prose seriously (at least three defects injected by the repair rounds, and about 13 of
34 findings being manifest and prose honesty findings that no design review touches) and the
design-attributable share is on the order of half. Applied to FATAL 2's 21.0h that is a saving near
11h, against 30.1h for the universal option and 7.5h for AC >= 6. **Universal review is then refuted
by a factor of nearly three, AC >= 6 becomes marginal, and only footprint >= 15 (2.0h) and F3 (0.22h)
still pay.** The document reverses a rejection while leaving out the one adjustment it promised.

**FIX.** Add the granularity clause. Apply it. Publish the per-round classification as evidence.
Carry the resulting share into section 6's numerator, and restate the universal conclusion from the
number that comes out.

---

## FATAL 4 - the question the document does not ask has a measured answer, and the answer refutes F3's precondition: the events F3 fires on are emitted by an instruction with a 0-for-148 record

**Attacked:** section 1 ("the defect is A RULE WITHOUT TEETH"), R7, section 7's fourth bullet ("Emit
review lifecycle events as a precondition").

**What I checked.** When the two-cycle rule landed and whether it predates the item; every mention of
`review.passed` and `review.failed` in code and in instructions; who emits the events that DO exist;
the event stream itself; the verdict count.

**What survived.** The two-cycle rule is real and predates the item. It is in the FIRST version of
`packs/claude/skills/review/SKILL.md` at `e0fb198`, 2026-07-16, seven days before WARP-1210 began, and it
reads as quoted. `packs/claude/agents/veldo-reviewer.md` at `c5c0c8d`, 2026-07-16, and
`.veldo/decision_review.py` at `9f15c8f`, 2026-07-22, are also as described. Section 1 is correct.

**What I found, which the document does not.** The document asks why a shipped rule was ignored and
answers "no teeth". The sharper answer is measurable and it is in the same file. The SAME PARAGRAPH
of `packs/claude/skills/review/SKILL.md`, since its first version, also says:

> "Append review.passed or review.failed to .veldo/events.jsonl."

There are **148 verdict files** in `proof/` and **zero** `review.*` events in `.veldo/events.jsonl`.
Meanwhile the stream holds 551 `gate.passed` and 45 `gate.failed`, and those are emitted by
`scripts/verify.sh:118` - a script.

**The events that exist are the ones a SCRIPT emits. The events that do not exist are the ones an
INSTRUCTION asks an agent to emit. 596 to 0.** No code path anywhere emits `review.passed` or
`review.failed`; the only mentions outside the event vocabulary are in prose instructions
(`packs/claude/skills/review/SKILL.md`, the seven `packs/*/skills/review/SKILL.md` copies, `docs/method.md`,
`docs/setup.md`).

**Why this is fatal for F3 specifically.** F3's enforcement chain is: reviewer writes a verdict, the
operator emits `review.failed`, a counter increments, the gate blocks. Step two is the step with the
0-for-148 compliance record, by the same actor that ignored the advisory rule eleven times. The
document names the events as "a precondition" and never says WHO OR WHAT emits them. If the answer is
"the review skill tells the agent to", then F3 is a rule without teeth whose teeth are a rule without
teeth, and the mechanism's enforcement depends on the same actor whose non-compliance created the
problem.

**FIX.** State that the emitter is CODE, on the same footing as `verify.sh`: verdict validation
(`python3 .veldo/validate.py verdict <file>`) emits the lifecycle event as a side effect of validating,
so the event cannot be omitted by an agent that forgets, and F3's counter reads a stream that exists
by construction. Then say so as the FINDING, not just as a precondition, because "the events a script
emits exist and the events an instruction requests do not, 596 to 0" is the strongest single
measurement of this document's own thesis and it generalises past this proposal.

---

## FATAL 5 - the policy formula has no term for the cost of a REFUSAL, and the measured refusal rate is 1.0

**Attacked:** section 6's formula `trigger_rate x population x cost_per_review < P(catch) x
expected_saving`, both trigger tables, R4.

The formula is the document's central contribution and the fix review 1 demanded. It prices the
REVIEW. It has no term for what happens when the review says no. That term is not a rounding error:

- Measured refusal rate across every design review anyone has run, including mine: **3 of 3
  `do_not_build_yet`**, on two specs, one catastrophic and one healthy, under three different briefs,
  one of which explicitly invited approval.
- Every refusal that means anything costs an amendment plus a re-review. At the document's own 13.2
  minutes and a refusal rate of 1.0, the universal option is 137 x 2 rounds = **60.2h**, not 30.1h,
  and 90.3h at three rounds. Against FATAL 2's corrected saving of 21.0h, or roughly 11h after FATAL
  3's attribution, universal review is refuted by a factor of three to eight.
- The same correction applies to the cheap triggers, which is the honest half: `footprint >= 15` goes
  from 2.0h to about 4.0h and still pays comfortably. **The cheap triggers survive this finding. The
  reversal does not.**
- R4 requires a refusal to have "a defined operational meaning: what it blocks, what artifact records
  it, what unblocks it, who arbitrates". At a refusal rate of 1.0 that requirement stops being a
  design detail and becomes the mechanism's dominant cost, and decision 5 is where the whole policy
  lives.

**FIX.** Add the refusal term to the formula:
`trigger_rate x population x (cost_per_review + refusal_rate x (amendment + re_review)) < ...`.
Measure the refusal rate, which is 1.0 on the three runs that exist. Then answer decision 6 BEFORE
recommending anything, because an uncapped design review at a refusal rate of 1.0 is the WARP-1210
loop moved one phase earlier onto prose, which is the document's own stated worry and now has a
measurement behind it. Full detail in the negative-control section below.

---

## BLOCKING 6 - "the brief is a convenience, not the mechanism" is refuted by the document's own round-1 evidence, and that sentence is what defers the mechanical gate indefinitely

**Attacked:** section 6's A-minus-B bullet, section 7's "the four-component checklist is optional
polish. Build the reviewer, not the gate."

A-minus-B compares two DESIGN briefs and concludes that briefs do not matter. The third data point is
already in the document as version 1's FATAL 3. I read it:
`proof/WARP-1210/verdict-1-fail-round1.json`, reviewer field
`claude-opus-5[1m] (independent adversarial fresh-context reviewer ... instructed to default to
REFUTED, to attack the NUMBERS rather than look for crashes ...)`, ruling per criterion
AC1 refuted, AC2 refuted, AC3 refuted, AC4 confirmed, AC5 confirmed, AC6 refuted, plus a separate
`schema_gap_ruling`. Same model family, same spec, same repository, same fresh-context independence.
It did not name the domain gap.

**Change the brief from a code brief to a design brief and the outcome flips from MISS to FULL
CATCH.** So the brief IS the mechanism. What A-minus-B actually shows is narrower and still useful:
codifying the DIMENSIONS INSIDE a design brief is a convenience. As written the sentence
overgeneralises, and the document then rests two architectural commitments on it: demoting a
mechanical design gate to "optional polish" and deferring it "indefinitely rather than sequenced".

**FIX.** Restate as: "Codifying the dimensions inside a design brief is a convenience. The design
brief itself is the mechanism, and the round-1 code brief on the same spec by the same model is the
control that shows it." Then re-derive whether the mechanical half is really optional.

---

## BLOCKING 7 - deferring WARP-0721 "indefinitely" reverses a recorded owner decision, is decided inside the recommendation, and is not among the nine

**Attacked:** section 6's "demotes a mechanical design gate to optional polish", section 7's "with the
mechanical half deferred indefinitely rather than sequenced".

The owner's recorded rule `feedback_design_upfront_not_discovered`, dated 2026-07-26, states: "How to
apply, and it is a GATE not an intention - 'think harder upfront' is unfalsifiable, so it was codified
as WARP-0721 (VEL-12)." It records his two corrections that produced the four components and the
count budget, and criterion (b) for whether such a gate is real: "each component is checked for a
MECHANICAL property rather than presence, because fields satisfiable by adjectives add ceremony and
prevent nothing, which is worse than no gate." `WARP-0721-design-gate-domain-and-observation.md`
carries `risk: high` and `human_approval: required`, and it changes what READY MEANS.

Version 2 relabels that "optional polish", says "Build the reviewer, not the gate", and defers it
indefinitely on the strength of two arms on one spec. **That is a reversal of a recorded owner
decision on a high-risk, human-approval-required artifact, made in a sub-clause of a recommendation,
and it is not one of the nine decisions.**

It is also incoherent with F1. The owner's recorded correction 2 makes the claim COUNT the scope
signal: "the COUNT becomes the scope signal: twenty claims is a five-ticket problem wearing one
ticket's clothes ... the budget signals SPLIT THE ITEM." That is F1's trigger. Version 2 commits F1
while deferring indefinitely the only mechanism that measures F1's trigger.

**FIX.** Make it decision 10, quote the recorded rule, and either name F1's signal independently of
WARP-0721 or move F1 out of "committed now".

---

## BLOCKING 8 - F1 is committed with no trigger, no owner and no definition, and on the only signal the document endorses it forces splits on six items that shipped clean in two commits

**Attacked:** section 5 row F1 ("On the same signal, the action is SPLIT, not REVIEW"), section 7
bullet 2, decision 2.

The same signal as WHAT? In section 5 the ambient signal is AC >= 5, which section 6 then refutes.
Section 7 endorses footprint >= 15 for the REVIEW and names no signal for F1. Decision 2 asks "the
same signal" without defining it. Nothing states who decides the split lines, what a split does to
the plan's work-item numbering, whether it re-opens plan approval, or what artifact records it.

**Measured, on the only signal the document endorses.** footprint >= 15 fires on 9 of the 30 specs
that declare a footprint. Three are troubled: WARP-1210 (45 paths), WARP-0616 (21), WARP-1208 (15).
**Six shipped clean in two commits each:** WARP-1103 (20), WARP-1107 (20), WARP-0615 (18), WARP-1209
(16), WARP-1104 (15), WARP-1201 (15). Under F1 those six become forced splits into roughly three
items apiece, which is about twelve extra items each carrying a spec, a manifest, a proof, a verdict
and a gate run.

The document prices F1's marginal cost at "near zero because the split was already required by the
standing 3-to-4-criteria rule." **The standing rule is an AC rule and the endorsed signal is a
footprint rule.** They are different signals over different populations, and the substitution is
asserted rather than argued. F1's cost is unmeasured.

**FIX.** Name F1's signal explicitly. Publish its trigger set. Price the splits it forces on the six
clean items. Give the SPLIT action an owner, a definition of a split line, and an artifact.

---

## BLOCKING 9 - F3's mechanism and F3's price are two different triggers

**Attacked:** section 5 row F3 against section 6's table row and decision 1.

The document describes F3 three ways and prices it on the one it did not describe:

- section 5: "**A review finding that indicts the SPEC** blocks further building until the spec is
  amended or a human rules" - a JUDGEMENT by a reviewer, base rate never measured
- section 6 table: "**F3 second failed review** | 1 of 133 | 0.71h" - an EVENT, base rate measured
- section 7 and decision 1: "teeth on the two-cycle rule" - the event again

The 0.71h and 0.22h figures are measured for the event. R7 ("Fire WITHOUT the owner noticing ... an
event in the loop rather than a person's attention") is satisfied by the event and NOT by the
judgement, because "does this finding indict the spec" is a judgement the reviewer makes and, once
the spec is the author's, is author-adjacent. The document's central claim for F3, that its trigger is
one the author cannot author, holds only for the reading it did not use in the options table.

**FIX.** Pick one. If it is the second failed review, delete the indictment wording from section 5. If
it is the indictment finding, measure its base rate and stop claiming R7.

---

## BLOCKING 10 - the 13.2-minute figure is fine; the COMPARISON to 42.6 is a measurement artifact, and the cost the document says "belongs beside the review cost" is not in it

**Attacked:** `PCATCH-results.md`'s cost table and its reversal, section 6's "Measured cost: 13.2 min
mean over three real design reviews", section 2's comparison table.

The 42.6-minute code-review mean is (evidence commit -> verdict file mtime). I reproduced it to
within one percent (I get 43.1 min, n=11, median 35.2, from the same method) so the FIGURE is fine.
The INSTRUMENT is not comparable: it includes dispatch latency and the operator's read time, and the
round-12 datum of 121.3 min is plainly latency rather than review effort. The 13.2-minute design mean
is the subagent's harness-measured execution duration, which excludes dispatch, the operator's read,
the ruling of the output and the spec amendment.

`PCATCH-results.md` names the missing term itself: "So a design review's output must itself be ruled,
not adopted. That cost is real and belongs beside the review cost." Four lines later it publishes the
13.2 mean without it, and the assertion that "it is not a new burden" is unmeasured. **The margin the
reversal rests on is 3.1h on 30.1h, about ten percent.** At a fully loaded 20 minutes the universal
option costs 45.7h and is refuted on every numerator in this review.

Two further defects in the same figure. The population is mixed: the 17.4-minute datum is a review of
a prose problem statement, not of a spec, and the other two are the same spec reviewed twice, so n=3
covers two artifacts. And the 12.4-minute figure for arm A appears only in prose, absent from the
file's own table headed "use ACTUAL durations, not self-reports", which is the discipline that table
exists to enforce.

**To be explicit about what I am NOT claiming:** my own review came in at 24 wall-clock minutes on the
code-review instrument, so I have no evidence that 13.2 is too low as a LEVEL. Use 13.2 for the review
itself. The defects are the cross-instrument comparison, the missing refusal and amendment term (FATAL
5), and the mixed population.

**FIX.** Publish n, the instrument and the population beside the figure. Drop the "against 42.6 minutes
for code review" comparison or re-measure both on one instrument. Put the ruling cost in the table.

---

## BLOCKING 11 - the experiment is not reproducible: neither arm's verbatim brief is recorded, and A minus B is the whole point

The prompt IS the intervention. The pre-registration describes arm A as "told only to attack the
design and find what will prove expensive, with no dimensions named and no hint of the failure mode",
but the actual text is nowhere in `veldo-staged-specs/` or in the repository. So the claim that arm A
named no dimensions cannot be audited by anyone, including the owner, and A-minus-B cannot be
re-derived. The ruling vocabulary each arm was offered is also unrecorded, which matters directly for
the base-rate question below: a brief that offers only `do_not_build_yet` and `needs_rewrite` cannot
produce an approval.

**FIX.** Commit both briefs verbatim beside the results, with the ruling vocabulary each was offered.

---

## BLOCKING 12 - selection on the outcome is unaddressed, and the pre-registration's own cited lesson names this exact defect

The subject spec was chosen BECAUSE it failed catastrophically, and no negative control was run or
proposed. The owner's recorded adversarial pass on WARP-0721 already named this as finding 5: "The
historical test was ONE convenient fixture (refuse WARP-1210's original spec) - the same 'property
exhibited over one fixture rather than enforced' failure my own reviewers had thrown back at builders
four times that night." Version 2 cites the WARP-0721 refutation approvingly, twice, and then rests a
reversal on the same single convenient fixture. The project's own promoted law is NO UNBACKED
UNIVERSAL.

I ran the control. It returned `do_not_build_yet` with 9 findings on a spec that shipped in two
commits and 19 minutes with all five criteria confirmed on the first pass, and its most expensive
finding is a verified hit against the shipped code. See the negative-control section below; it is
FATAL 5's evidence and it is the reason FATAL 2 and FATAL 3 are not the only things blocking the
reversal.

**FIX.** Publish the negative control, or run your own. Report P(catch) beside the refusal rate on
healthy specs, which is 1 of 1, and beside the base rate of the ruling vocabulary, which is 3 of 3.

---

## BLOCKING 13 - the "5 troubled items" denominator has no membership rule, and the catch column in both tables is therefore unauditable

Both trigger tables have a column "catches (of 5 troubled)" and the document never says what makes an
item troubled. Measured: only FOUR VELDO items exceed three commits (WARP-1210 at 31, WARP-0614 at 6,
WARP-1208 at 6, WARP-0616 at 5). WARP-0623, which is in review 1's troubled set and carried forward
into version 2's, has THREE commits and zero failed verdicts, the same as ten other items that are
not in the set (WARP-0100, WARP-0107, WARP-0612, WARP-0613, WARP-1107 among them).

The denominator changes the answer. On "more than three commits" the set is four, and footprint >= 15
catches 3 of 4 (75 percent, WARP-0614 at 13 paths is the miss) rather than 3 of 5 (60 percent). This
is the FOURTH count with no rule in this workstream and it sits in the table that decides the
threshold.

**FIX.** State the membership rule, publish the set, and recompute both catch columns.

---

## BLOCKING 14 - who runs the design review, and at what independence level, is never asked; review 1 asked for it and the rewrite dropped the note instead of answering it

`.veldo/policy.yaml` keys `min_independence` to risk tier for code reviews (L1 at low, L2 at standard
and high, two L2 verdicts at critical) and records the founder's instruction verbatim: reviews the
operator initiates run on a fresh-context DIFFERENT Claude model of the Opus family, level L2, at
every tier; cross-vendor L3 and L4 only on his explicit per-case instruction. A design review is a new
review kind with no row in that file. Review 1's NOTE 14 asked exactly this. Version 2 says nothing
about whether the design reviewer is a fresh L2 context, whether the author's own session may run it,
or whether `policy.yaml` gains a row.

**FIX.** State the ladder and add the question to the decision list.

---

## BLOCKING 15 - the nine decisions are version 1's four plus review 1's five, not version 2's own; at least five more are decided in prose

The document says so itself: "Version 1 asked four and made five more inside its own recommendation.
That is the failure he named, so all nine are here." Four plus five is nine, which is the arithmetic
of a carried-forward list, not of a fresh derivation over a recommendation that changed materially.
Version 2's recommendation reversed the universal option, chose a cut point, chose judgement over
mechanism, and deferred a high-risk approved-required spec indefinitely. Its own new decisions are in
prose:

1. **The cut point 15.** Decision 4 asks WHICH SIGNAL and never asks where to cut it. At >= 15 the
   trigger fires on 9 of 30 (three troubled, six clean); at >= 20 on 4; at >= 13 on 14. The
   consequence is measured and the question is not asked.
2. **Deferring WARP-0721 indefinitely** (BLOCKING 7).
3. **F1's signal** (BLOCKING 8).
4. **The independence level of the new review kind** (BLOCKING 14).
5. **Who or what emits the review lifecycle events** (FATAL 4).
6. **The disposition of F2.** Section 5 rates it favourably: "Inherits a schema, a binding, a
   fail-closed gate and a MISSING OPTIONS dimension. Smaller than a new phase." Section 7 never
   mentions it. Section 9 never asks about it. Extending a shipped organ instead of adding a phase is
   the conservative architecture and the document drops it without a reason.
7. **What "revisit toward universal" requires.** No trigger, no owner, no evidence bar.

**FIX.** Derive the list from version 2's recommendation and publish whatever count comes out. The
number nine is not a target.

---

## BLOCKING 16 - decision 3 contradicts section 7, and section 7 contradicts itself on F3's cost

Decision 3: "Is a pre-build design review added at all? Recommend deferring until P(catch) reports."
P(catch) reported in sections 6 and 7 of the same document, and section 7 recommends adding one.
Section 7 bullet 1 prices F3 at 0.71h; bullet 3 prices the same F3 at 0.22h; neither names its cost
basis. Version 1 partly died of a load-bearing self-contradiction on WARP-1210's risk tier (review 1,
BLOCKING 10). The rewrite carries two more, and both are in the sections he will read first.

**FIX.** Update decision 3 to the post-result question. State F3's cost once, with its basis.

---

## BLOCKING 17 - this proposal is the shape it warns against

"Committed now" is F3, plus F1, plus review lifecycle events. The recommendation then adds a pre-build
design review, a signal, a cut point, refusal semantics, a verdict binding and a grandfathering
policy. That is at least four independently shippable concerns with well over a dozen acceptance
criteria between them, against a standing house rule of ONE concern per item and three to four
criteria maximum - the rule this document identifies as the disease's cure and then does not apply to
itself. WARP-0721 already made this mistake once and the owner's recorded meta-lesson is explicit:
apply the rule to itself as the first test.

**FIX. Split on these lines, in dependency order:**

1. **Review lifecycle events emitted by CODE.** Independently valuable, unblocks everything, no
   decisions needed beyond where the emit call goes. Ship first.
2. **F3, the second-failed-review block.** Needs 1. Needs the trigger disambiguated (BLOCKING 9) and
   its benefit restated (FATAL 1).
3. **F1, the split trigger.** Needs a signal named and its cost measured (BLOCKING 8).
4. **The pre-build adversarial design review.** Needs the signal, the cut point, the refusal
   semantics, the independence level, the verdict binding and the grandfathering policy. This is the
   only one that should carry the decision weight, and it is the one that should wait for the
   negative control and the corrected arithmetic.

---

## NEGATIVE CONTROL - the experiment nobody ran, and it did not come back the way I expected

**RESULT: `do_not_build_yet`, 9 findings, on a spec that shipped in two commits and 19 minutes and
passed its independent adversarial code review with all five criteria CONFIRMED on the first
attempt.**

### The subject and the construction

**WARP-1209, "diagnosability gated - observability as acceptance criteria" (W9 of PLAN-0012).** It is
the immediate predecessor of WARP-1210 in the same plan, authored in the same era under the same
conventions. Its record: 2 commits, raw span 19 minutes, 0.86h of gap-capped active time, one
`proof/WARP-1209/verdict.json` ruling `pass_with_notes` with AC1 through AC5 all `confirmed` by
`claude-opus-4-8[1m]`, an independent adversarial fresh-context reviewer. Zero fail verdicts. By every
measure available in this repository it is a healthy item.

**It also declares 16 footprint paths, so `footprint >= 15`, the trigger section 7 endorses, FIRES ON
IT.** This is not a hypothetical control. It is an item the recommended policy would have gated.

Construction, stated so the differences from arm A are visible rather than hidden:

- Tree extracted with `git archive 379063b8^ | tar -x` into a scratch directory, so no `.git` and no
  future history, the same method as arm A. Verified afterwards: no `.git`, `.veldo/observability.py`
  absent, `proof/WARP-1209/` absent, 117 proof directories from other items present as legitimate
  convention context, 124 specs.
- The WARP-1209 spec added from `379063b8` with `status: review` changed to `status: ready`, and
  `specs/index.md` from the same commit.
- **Honest difference 1.** WARP-1210 is the ONLY item in all 348 commits with a spec-only commit, so
  no other item HAS a committed pre-build revision. I had to synthesise one. The spec text is
  therefore as-authored only up to any edits made in-session during the build, which are invisible to
  git. Since WARP-1209 needed no fix rounds, the risk is small, but it is real.
- **Honest difference 2.** Arm A's verbatim brief is not recorded anywhere (BLOCKING 11), so I could
  not match it. I wrote one to the pre-registration's description of arm A: attack the design, find
  what will prove expensive, no dimensions named, no hint that anything failed, no mention of the
  inversion workstream or that the output would be scored. **My brief biased TOWARD approval more than
  arm A's plausibly did:** it offered `build` as an explicit first option and said "If the design is
  sound, say `build`; a reviewer who can never approve is worthless." It still returned
  `do_not_build_yet`.
- Reviewer: fresh Opus context, read-only, 52 tool uses. **Self-reported cost "approximately 35
  minutes"; harness-measured duration 13.3 minutes, a 2.6x self-inflation.** That independently
  reproduces `PCATCH-results.md`'s methodological finding that "agent self-reports run 2 to 3 times
  high and were discarded", which I had no way to check before and now can: the discipline is correct
  and the document was right to apply it.

### Result 1 - `do_not_build_yet` is what an adversarial design reviewer says

Three specs, three arms, three refusals. WARP-1210 arm A: `do_not_build_yet`, 13 findings. WARP-1210
arm B: `do_not_build_yet`, 7 dimensions FAIL. WARP-1209, healthy, generic brief, approval explicitly
invited: `do_not_build_yet`, 9 findings. **The RULING carries no information.** `P(catch) = 1 of 1`
cannot be published without `P(refuse | healthy spec) = 1 of 1` beside it, and the document publishes
the first as the basis for a reversal and does not have the second.

### Result 2 - and this is the part I did not expect: the findings are not false positives

I spot-checked three premises against the shipped code, and the most expensive one is a VERIFIED HIT
of exactly the kind `PCATCH-results.md` celebrates for arm B.

**The control's F1 predicted, from the pre-build spec alone,** that AC2 ("wired at the SAME transition
the placement gate uses, `validate.check_ready`") and AC4 ("where no such rules exist the gate STANDS
DOWN honestly to the spec-level floor") are incompatible, that `check_ready` returns 0 before
evaluating anything when no architecture contract exists, that `/veldo:init` lays down no contract, and
therefore that under the cheap reading "this item ships an engine capability that is inert in every
repository `/veldo:init` creates" while its own specified selftests cannot tell the two readings apart.

**What shipped.** `.veldo/validate_checks.py:190-205`, `check_ready`: `arch, contract =
load_repo_contract(repo_root)` then `if contract is None: return 0`. The diagnosability gate is
enforced inside that function at line 217 and after, downstream of the early return. And
`.veldo/validate_checks.py:134-135`, `check_observability`: `if not contract_path.is_file(): return 0
# adoption safe: no contract in this repo, the check stands down`.

**The builder took the cheap horn.** The mandatory diagnosability rule is inert in any repository with
no architecture contract. The item passed with all five criteria confirmed, and the capability is on
the record.

Two more premises checked and holding: `scripts/verify.sh` runs `check_template_sync.sh` and never
`scripts/check_pack_drift.py`, so AC5's gate list is inaccurate (the control's F9); and
`specs/TEMPLATE.md` is absent from WARP-1209's footprint, so the trigger field is undiscoverable where
authors start (the control's F2). I did not adjudicate the other six and I will not assert what I did
not measure.

### What the control actually establishes, which is not what I went looking for

**It does NOT show a false-positive problem. It shows something worse for the arithmetic and better
for the mechanism.**

1. **The reversal as ARGUED is dead, and this is independent of FATAL 2 and FATAL 3.** The document
   prices the policy as `trigger_rate x population x cost_per_review` and calibrates the saving on the
   ONE catastrophe. The measured refusal rate is 1.0 and the refusals are substantive, so the real
   policy is not 137 reviews at 13.2 minutes; it is **137 review-amend-re-review loops**. At two
   rounds that is 60.2h, at three it is 90.3h, against a corrected saving of 21.0h before attribution
   and about 11h after it. **There is no term in the document's formula for the cost of a refusal**, and
   R4 explicitly requires the refusal to have a defined operational meaning. At a refusal rate of 1.0,
   "blocks `ready`" means nothing ships until round two.
2. **Decision 6 is the load-bearing decision, not a footnote.** The document asks "Does the three-round
   cap apply to design reviews? An uncapped adversarial review of PROSE reproduces the WARP-1210 loop
   one phase earlier, where there is no gate to settle an argument" and then recommends the review
   anyway, with arithmetic that assumes one round. My control is the measurement that says the worry is
   real: the refusal rate is 1.0 and there is no gate on prose.
3. **The document's weakest-stated claim is the one that got STRONGER, and it should be promoted.**
   Section 6 concedes "the ordinary-defect saving is bounded below rather than measured, from n=2".
   The control is the third data point and it is the first on a HEALTHY spec: real, verifiable design
   debt, found pre-build, on an item nobody thought had a problem, at 13.3 minutes. **That is the honest
   case for a design review, and it is not the case the document makes.** The document argues from the
   catastrophe term, where the numerator is broken and the base rate is 1 in 145. It should argue from
   the ordinary-defect term, where the hit rate looks like 1.0, and then it has to price the refusal
   loop, which is the work it has not done.

### The one-line answer to attack vector 2

Selection on the outcome mattered, but not in the direction anyone expected. The generic design
reviewer is not a coin that always says no to specs that failed; it says no to everything, and it is
usually right. That makes P(catch) uninformative, makes the refusal cost the decisive unmeasured
quantity, and moves the whole argument off the catastrophe and onto the ordinary defect, where the
document has n=3 and no price.

---

## What survived my attack, and what I did to try to break it

- **Every population figure. All of them, exactly.** Acceptance-criteria distribution
  `{2:2, 3:7, 4:16, 5:78, 6:21, 7:10, 8:2, 10:1}` using `validate.py`'s own `spec_criterion_ids`
  logic over the 137 files in `specs/` excluding `index.md` and `TEMPLATE.md`. Risk tiers 126
  standard, 10 high, 1 critical. 30 of 137 declare a footprint. footprint >= 15 fires on 9 of 30. The
  four specs with no commits are WARP-0201 to WARP-0204. AC >= 5 fires on 112, AC >= 6 on 34. Nothing
  moved.
- **The 1.19h mean, and its derivation is now pinned.** I tried three id-extraction rules and both
  author and committer dates. Committer dates give 1.081h mean and a 0.221h median; author dates give
  **1.227h mean, 0.310h median, 53.8 percent of items under 20 minutes**, which reproduces the
  document's median and its "53 percent" exactly. The gap-capped figure reproduces only on
  TIME-SORTED order: 173.15h over 145 = 1.1941h at `HEAD~1`. Log order gives 168.48h and 1.162h, a
  2.7 percent swing, so state the ordering with the number.
- **F3's base rate, 1 in 133.** I counted fail verdicts per proof directory across all 133. WARP-1210
  has 11; WARP-0616 and WARP-1208 have one each; everything else has zero. Exact.
- **Section 1's mechanism inventory.** The two-cycle rule is in the FIRST version of
  `packs/claude/skills/review/SKILL.md` at `e0fb198`, 2026-07-16, and reads as quoted.
  `packs/claude/agents/veldo-reviewer.md` at `c5c0c8d`, same day. `.veldo/decision_review.py` at `9f15c8f`,
  2026-07-22. All three predate WARP-1210, which began 2026-07-23. I tried to break the "rule
  predates the item" claim by checking the first version of the file rather than HEAD, and it held.
- **The surviving gap.** No adversary attacks a spec's design at spec granularity before the build. I
  tried to break it and could not. I also found something stronger in its favour and worth recording:
  **WARP-1210 is the ONLY item in the entire corpus with a spec-only commit.** I searched all 348
  commits for any commit touching only `specs/`; there are exactly three and all three are WARP-1210's
  (`c37e833`, `ffc3bd6`, `d283ae1`). Every other item's specification and implementation land in one
  commit. So the workflow as practised does not produce a committed pre-build spec state, which is a
  real feasibility point for a pre-build review phase and is not in the document.
- **Arm B's VERIFIED HIT.** I tried hard to break this one because it is the most impressive claim in
  the package. `.veldo/reconciliation_store.py` has exactly one commit in its entire history
  (WARP-1208's `3ff4336`) and zero from WARP-1210. It appears nowhere in WARP-1210's spec, so it was
  never in the footprint. `.veldo/metrics_readers.py:185-195` reads exactly as quoted, including the
  word "honestly". Arm B could not have seen it: at `c37e833` there are zero files under
  `proof/WARP-1210/`, `metrics_readers.py` does not exist, and the 138 verdicts present belong to
  other items. **The prediction is genuine and the blindness holds.** This is the strongest single
  piece of evidence in the package and it should be foregrounded rather than sitting in a subsection.
- **The pre-registration was written first and was FOLLOWED.** I compared the scoring criteria in
  `PCATCH-experiment-preregistration.md` against how `PCATCH-results.md` scored both arms, line by
  line. FULL CATCH required naming defect 1, "that the spec does not declare the complete set it is
  over, or equivalently asks how the enumeration of sources is known to be complete". Arm A's F1
  names a fifth undeclared store; arm B names five input sets where the spec names two. Both meet the
  criterion as written. Nothing was loosened, the two-arm split was added BEFORE either arm ran and
  for the right reason, and the pre-registration's honesty about its own first design being circular
  is the best writing in the package. **Arm A's false positive was also volunteered rather than
  buried, and I verified the correction: `_load` genuinely never registers in `sys.modules`, and there
  genuinely is no cycle.** Credit where it is due; this is the part of the work that should be
  repeated on everything.
- **House style PASSES.** Zero codepoints above 127 in the version 2 document and in all four PCATCH
  files. Zero prose double hyphens in version 2, the pre-registration, the results and arm A. Arm B
  has three and all three are `--json` and `--field` CLI flags, which are code, not prose. This review
  is held to the same standard.

---

## NOTES

- **NOTE 18 - the 594-event figure does not reproduce as a count, only as a property.** I measure 593
  events at HEAD and 596 in the working tree, all of them `gate.passed` (551) or `gate.failed` (45).
  The KIND claim is exactly right and is the load-bearing half. The count drifts on every gate run
  because the file is uncommitted-modified. The repository's own rule applies: publish the figure with
  the revision that produces it, or state the property and delete the number.
- **NOTE 19 - WARP-1210's own figures are already stale and will be stale again by the time he reads
  this.** Round 13 landed at 2026-07-26 07:19, so the item stands at 31 commits and a 36.86h raw span,
  and its spec still reads `status: ready`. The document prices a saving against an item that has not
  finished. Say so, and key the figures to a named revision.
- **NOTE 20 - the expected-saving term assumes P(fix given catch) = 1.** It treats a caught WARP-1210
  as becoming a mean-cost item. Both arms ruled it a three-way or four-way split, so the honest
  counterfactual is three or four mean-cost items plus the review plus the split overhead. That moves
  the same direction as FATAL 2 and FATAL 3; I have not stacked a number on it to avoid double
  counting, but it should be stated.
- **NOTE 21 - presentation risk in section 1.** The second sentence tells the owner that a framing
  taken from his own recorded words is "false". The measured correction is that the gap is NARROWER
  than stated, not that the principle is wrong: three adjacent checks exist and none of them attacks a
  spec pre-build, which is what he said. Word it as a narrowing. He is more likely to act on
  "you were right and here is the precise version" than on "that is false".
- **NOTE 22 - R6 is stated and then not served by anything that ships.** R6 requires addressing
  iteration-injected defects. F1 is the only candidate that touches it, F1 has no trigger (BLOCKING 8),
  and the three-round cap, which is the actual live mechanism against iteration-injected defects and is
  already in force per the owner's recorded correction, is mentioned only as decision 6 about design
  reviews and never as the answer to R6.

---

## My own cost

- **Wall clock: 24 minutes** (first read of the subject document at about 07:19 EDT, this file
  written at 07:43 EDT on 2026-07-26), measured start of material to artifact written, the same way
  the code reviews were measured. Of that, 13.3 minutes overlapped the negative-control reviewer,
  which I ran in parallel while re-deriving figures. **Second reviewer's cost: 13.3 minutes harness
  duration, 52 tool uses.** Total agent-minutes for this review including the control: about 37.
- **I am correcting my own first estimate rather than publishing it.** I wrote 118 minutes into an
  earlier draft of this section from a bad recollection of when I started, and the file timestamps
  refute it. In a review whose credibility rests on measurement, publishing that would have been the
  exact sin I am charging.
- **What that means for BLOCKING 10, honestly: my own datum does NOT refute the 13.2-minute figure, it
  lands near it.** A design review of a 20KB process document that re-derived figures across 348
  commits and 137 specs and ran a delegated control experiment cost 24 wall-clock minutes. BLOCKING 10
  is therefore narrower than the level of the number: it is about the INSTRUMENT (13.2 harness-minutes
  against 42.6 commit-to-mtime-minutes is not a comparison, so "design review is three times cheaper
  than code review" is a measurement artifact) and about the ruling and amendment cost that
  `PCATCH-results.md` says belongs in the figure and then omits. The absolute level of 13.2 survives.
- **What it needed:** the 20KB subject document, the 38KB first review, four PCATCH files (67KB of arm
  output); 348 commit subjects with author and committer timestamps under two id-extraction rules; all
  137 spec front matters programmatically for acceptance criteria, risk tiers and footprint counts;
  the AC-count history of five specs at their first commits; all 133 proof directories for fail-verdict
  counts; `proof/WARP-1210/verdict-1-fail-round1.json`; the WARP-1210 spec diff at nine fix commits;
  `.veldo/events.jsonl` in the working tree and at two revisions; `scripts/verify.sh`;
  `packs/claude/skills/review/SKILL.md` at HEAD and at `e0fb198`; `.veldo/policy.yaml`; `.veldo/validate.py`'s
  criterion counter and event vocabulary; `.veldo/metrics_readers.py`;
  `git ls-tree` at `c37e833` to verify blindness; a spec-only-commit search across all 348 commits;
  the owner's memory files `feedback_design_upfront_not_discovered` and the MEMORY.md index; and
  `WARP-0721-design-gate-domain-and-observation.md`. One constructed pre-build tree, one delegated
  reviewer, six throwaway analysis scripts.

---

## Ruling

**needs_rewrite.** Not fit to go to the owner as-is, and not fit with a fix list, for the same reason
review 1 gave: the five fatal findings break five different layers (the recommended first move's
benefit, the central numerator, the attribution rule, the precondition's enforcement, and the policy
formula itself), and four of them change the recommendation rather than its wording.

**Does the universal-review reversal survive? No, three times over, independently.** The numerator is
21.0h and not 33.2h once both terms sit on the derivation section 2 itself insists on (FATAL 2). The
attribution rule the document states and never applies cuts that to roughly 11h (FATAL 3). And the
formula has no term for a refusal, whose measured rate is 1.0, which doubles or triples the cost side
(FATAL 5). Universal design review is refuted by a factor of three to eight, not "roughly
break-even". **The cheap triggers survive all three corrections comfortably**, and that is the version
of the recommendation that can go forward.

**What I would keep intact.** The population figures, all of them, which reproduce exactly. Section
1's corrected mechanism inventory. The pre-registration and its two-arm design, which is genuine work
and was followed. Arm B's verified hit, which I tried hard to break and could not. The volunteered
false positive. Section 8. That is a lot, and version 3 should be much shorter to write than version 2
was.

**The one claim that got STRONGER and should lead version 3.** Not the catastrophe. Design review
finds real, verifiable design defects on ORDINARY specs at 10 to 18 measured minutes, and the negative control
is the first evidence of that on a spec nobody thought had a problem. The document's own weakest
sentence ("the ordinary-defect saving is bounded below rather than measured, from n=2") is where the
case actually lives. Argue it there, price the refusal loop, and the answer may well come out in
favour of a broad design review for reasons that have nothing to do with WARP-1210.

**The one thing I would do first.** Not another rewrite of the argument. Ship the smallest true thing:
make verdict validation emit `review.passed` and `review.failed` from CODE. One concern, three or four
acceptance criteria, independently valuable, nearly free, the precondition for every other option in
the document, and the only proposal in it whose enforcement does not depend on the actor whose
non-compliance created the problem. Then measure for a week and write version 3 against data rather
than against one fixture.
