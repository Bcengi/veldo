# Veldo rethink, August 2026

Written 2026-08-01 at Dmitry's instruction: "Veldo is really problematic. We need to step back
and rethink how it works. Too many guards and failures."

**STATUS 2026-08-01: accepted and partly implemented.** Dmitry chose option 3 with human
sign-off narrowed to high risk, plus making the size budget advisory. Both have landed:
`4cfd318` (module_lines advisory) and `1d2cc2c` (WARP-0730, verdict authority leaves the agent).
What remains is the code deletion in section 6 step 3, rescoped below, and the measurement in
step 5. Sections written before those landed are left as they were, with corrections marked.

**It disagrees with the premise in one important place**, and that disagreement is the most
useful thing in the document, so it is up front rather than buried.

***

## 1. What the numbers actually say

Measured this morning against `b0fa073`, not recalled:

| | |
|---|---|
| Specs shipped | **145** |
| Specs open | 7 ready, 6 draft |
| Commits, last 3 weeks | 489 (194, then 170, then 125) |
| Engine | 73 modules, 31,356 lines |
| Test suites | 14 files, 28,883 lines, largest 7,768 |
| Architecture rules | 20 |
| Commits per item, worst | WARP-1210: **37**. 0712: 18. 0722: 16. 0716: 15. |

**The system is not stalled. It has shipped 145 items.** Any rethink that starts from "nothing
ships" is arguing with something that is not happening, and would throw away a method that is
demonstrably producing.

**Two corrections to things I have told you, both in the method's favour.**

- I said the suite split was one of two load-bearing things still outstanding. **WARP-0712 is
  shipped.** The 16,000-line file that serialised everything is now 14 files. That was the
  structural fix and it landed.
- I said the suite was a single 23,023-line file. It is not, and has not been for some time.

So of the two things I called load-bearing, one is done. **The forgery guard is the only genuinely
stuck item**, and everything else in your complaint traces back to it.

## 2. Where you are right, precisely

The complaint is not throughput. It is **cost per item and one item that will not close**.

Thirty-seven commits for WARP-1210 is not a healthy number. Sixteen for WARP-0722, which the spec
records as nine build rounds that each closed a route and never stated the property. And the
forgery guard has now been defeated **seven times in seven spellings**.

And last night produced the cleanest instance of the pathology: **a correct, measured, four-line
security fix could not land because `events.py` was one line under a 1000-line budget.** A guard
about file length blocked a guard about forgery. I stopped rather than delete four comments to
turn the gate green, which was the right call and also means the fix is still not in.

That is the real shape of the problem. Not "too many guards" in the aggregate, but:

1. **One guard is unachievable where it is being attempted** and is consuming the programme.
2. **Guards now interact**, so the cost of the next fix is set by rules unrelated to it.
3. **The method is validated on itself**, so every defect found becomes a rule that makes the
   next fix harder. That loop only tightens.

## 3. The thing I think is actually wrong

**The forgery guard is defending a property that cannot hold from inside the process it is
defending against.**

It tries to stop an agent marking its own homework, while that agent has write access to the
filesystem, the repository and the Python process. Every round buys exactly one spelling, because
there is always another way to name a file, redirect an enumeration, or write bytes without
importing the module that checks them.

The current code is honest about this. `log_entitlement` declares three limits it cannot close: a
writer that never imports the module, arbitrary in-process Python, and `GIT_DIR` redirection. My
own fix last night closed a fourth route and declared a fifth. **Those declarations are the proof
that the property is unachievable here** - not evidence of sloppiness, evidence of position.

Nine rounds have now demonstrated empirically what the threat model implies analytically.

### The alternative: remove the capability instead of guarding it

An agent should not be able to write a verdict at all.

Move the verdict log where the agent cannot reach it. In descending order of cost:

- **You record verdicts.** A one-line human action. Costs your attention, which is the method's
  own scarce resource, and is the only version with no attack surface at all.
- **A separate process the agent cannot write to**, accepting verdicts over a socket, running as
  a different user. The agent asks; something else decides and writes.
- **An append-only external service** with a credential the agent does not hold.

Any of these deletes the entire class, because the thing they defend cannot be attempted.

**SCOPED 2026-08-01, and the 1,600-line estimate in the first draft of this document was wrong.**
Measured after WARP-0730 landed:

- `verdict_corpus.py` (662 lines) **must STAY.** It is not the forgery guard, it is the corpus
  enumerator, and `validate.py`, `policy_check.py` and `intent_corpus.py` all depend on it for
  ordinary proof-artifact enumeration. Deleting it was never the right move and the estimate
  assumed otherwise.
- What is genuinely removable is narrower: `log_entitlement` and the `entitled` parameter
  threaded through `_append_events`, `refuse_reserved_envelope` and `_reconcile_pass` in
  `events.py`, times its eight shipped copies. Order 150 lines, not 1,600.
- **One open question the deferral did not anticipate.** `metrics.py` tallies `verdict.recorded`
  events into a review count. Remove the entitlement check and that tally becomes forgeable. It
  is an internal metric rather than a published claim, so the stakes are low, but it should be a
  decision rather than a side effect: either the tally is dropped, or it is labelled as
  descriptive and unverified.

The remaining caution is that this edits the writer to an append-only log, where a mistake is
permanent. It deserves its own focused pass rather than being tacked onto the end of another.

The honest cost: verdicts stop being free. Today they cost nothing and are worth nothing, because
the writer can forge them. Under this change they cost a human action and are worth something.
That trade is the whole point.

## 4. What earns its cost and must survive any rewrite

Three things. They are cheap, they are why the method catches real defects, and I would fight for
them:

1. **The spec states the property before anything is built.** WARP-0722's own post-mortem is that
   nine rounds each closed a route and none wrote the question down. The discipline is correct;
   it was skipped.
2. **The gate is the only thing that says done.** No self-certification. This is the load-bearing
   cultural rule and it worked last night: it stopped me shipping something I wanted to ship.
3. **Every guard has a failing witness.** A guard with no test that fails without it is a claim,
   not a guard.

## 5. What I would cut

- **Rules about the rules.** The 1000-line module budget is a review-grade heuristic being
  enforced mechanically. It blocked a security fix and taught nothing. Make it advisory, or
  scope it to new modules.
- **Critical-tier two-review ceremony. CORRECTED 2026-08-01.** This was written believing the
  two-review requirement blocked code merges. It does not: the `reviews` count in `risk_tiers` is
  read only by `decision_review.py`, for adversarial review of DESIGN DECISIONS, and it floors at
  one by design. What actually blocked a merge was `policy_check` requiring a verdict, and that is
  what WARP-0730 removed. I tried to drop the reviews count as part of that item and the gate
  caught it; critical decision records still require two. **Do not conflate code verdicts with
  decision reviews.**
- **Every guard whose threat model is an agent we are ourselves running.** If the answer to
  "who is the attacker" is "the thing we launched, on our own machine, with our own credentials",
  the answer is a permission boundary, not a predicate.
- **Guards that interact.** Any rule able to block an unrelated fix should be advisory. The gate
  should be red for correctness, not for housekeeping.

## 6. What this looks like as work

Sequenced so each step is independently abandonable. **Steps 1, 2 and 4 are done; the ordering
below is left as originally written so the plan and what happened can be compared:**

1. **Decide where verdicts get written.** One decision from you, and everything else follows.
   Nothing should be built until it is made.
2. **Move the verdict log out of agent reach**, in whichever form step 1 chose.
3. **Delete the entitlement machinery**, in one commit, with the measurement of what it cost.
   Close WARP-0725 as superseded rather than fixed, and say plainly that the hole was closed by
   removing the capability rather than by winning the eighth round.
4. **Demote the mechanizable rules that are really heuristics.** Line budgets, duplication ratios.
5. **Then, and only then, do the wall-clock measurement I still owe you** on an ordinary item,
   because it should be measured on the method you are keeping, not the one being replaced.

## 7. The uncomfortable part

I have contributed to this. Last night I added a guard, then moved it, then extracted a helper,
then trimmed a docstring, all to fit a line budget, and the net effect on your business was zero.
That is four hours inside the method's own machinery.

The measure of whether this rethink worked is not fewer rules. It is whether the next ordinary
item ships in an afternoon.

***

**One decision needed from you: where does a verdict get written, and by whom.** Everything in
section 6 follows from it and nothing should start before it.
