# The Product Manager in Veldo

*Training series. The most leveraged human in the building: in Veldo, the product manager ships features by specifying them.*

*Version 1.1, 2026-07-16*

## 1. Your job, redefined

Before Veldo, your intent passed through many hands: a ticket, a grooming meeting, an engineer's interpretation, a QA person's reading of that interpretation. Every hand changed it a little, and you found out what you actually shipped at the demo.

In Veldo, your intent goes into a specification, and the specification is the contract the machine builds and proves against. Nothing reinterprets you. That is enormous leverage and enormous responsibility: **the quality of what ships is now bounded by the quality of what you specify.** Garbage intent no longer gets quietly fixed by a thoughtful engineer downstream; it gets built, proven, and shipped exactly as stated.

| What stops | What starts |
|---|---|
| Writing tickets and user stories for humans to interpret | The spec dialogue: answering an agent's interview until intent is testable |
| Sprint planning, grooming, estimation meetings | The weekly index pass (15-20 minutes, the only ritual left) |
| Chasing status across standups and boards | Reading receipts; `/veldo:status` when curious |
| Waiting for the demo to see what was built | Judging shipped changes against intent, with evidence attached |
| Negotiating with engineering about capacity | Deciding priority order in the index; capacity is not the bottleneck anymore |
| Acceptance testing by clicking around | Writing acceptance criteria so the machine clicks around forever |

## 2. Your day

Morning: your assistant (chat or terminal) has receipts from what shipped overnight and, at most, one or two things waiting on your judgment: a blocked spec with a product question, a baseline to eyeball, a priority call. You answer them in plain sentences.

The rest of the day is the actual job: talking to customers, watching usage, deciding what matters next. When something crosses the line into "we should build this," you state it, take the interview, approve the spec, and let it run. You do not attend a single meeting about how the work is going. The work reports itself.

## 3. Your moments in the loop (exact)

**Starting work:**

```
/veldo:spec When a customer's payment fails three times, pause their subscription instead of retrying forever
```

The agent interviews you. This is where your craft lives now; answer precisely:

```
Agent: What should the customer see when paused?
You:   The billing page shows "Paused - payment needed" with a fix-payment button.
Agent: Should pausing stop service immediately or at period end?
You:   At period end.
Agent: What un-pauses it?
You:   A successful payment. Automatically.
```

**Approving:** read the spec file the agent drafted. The only question that matters: *if every acceptance criterion passes, is this actually what I want?* If yes:

```
Ready.
```

**Judging a receipt:**

```
VELDO-0231 shipped. 4/4 criteria proven. Gate green. Review: pass.
```

Your job is not to re-verify (the machine did); it is to ask whether the intent was right: watch the metric, read a support ticket, use the feature once. Letter-not-intent gaps are yours to catch, and yours to fix by writing better criteria next time.

**The weekly pass:**

```
/veldo:index
```

Close what shipped. Kill what went stale (killing is a product decision; do it proudly). Re-answer what is blocked. Confirm the next ready specs in priority order. Twenty minutes; if it takes longer, your specs are too big.

## 4. The curriculum

**Module 1 - Testable intent.** The core skill. An acceptance criterion is something a machine can decide. "The page should feel faster" is not a criterion; "the orders list renders in under 300ms at p95 with 1,000 orders" is. Exercise: take five vague requests from your real backlog and rewrite each as criteria; run each through `/veldo:spec` and see what the validator and the interview push back on.

**Module 2 - The interview.** Learn to be interviewed well: the agent asks about edge cases, failure states, and exemptions because those are where shipped bugs live. Answering "I don't know, what do you think?" is allowed; deciding by silence is not. Exercise: hand the agent a deliberately underspecified request and answer only what is asked; compare the resulting spec to what you assumed you meant.

**Module 3 - Judging evidence, not vibes.** Read five proof manifests and five verdicts from real shipped changes until they stop looking like noise. You are not checking the machine's work; you are learning what proven looks like so you notice when a criterion was satisfied in letter but not intent. Exercise: find one shipped change where all criteria passed and the outcome still missed; write the criterion that was missing.

**Module 4 - Risk honesty.** You declare a spec's risk floor. Learn the tiers and the protected paths of your repositories. When your feature touches money, auth, or data deletion, say so in the spec; the system will catch it anyway, but your credibility is the difference between a partner and a person the policy has to defend against.

**Module 5 - Standing specs and the index.** Recurring requests (copy tweaks, config changes, report tweaks) get standing specifications so they stop consuming your attention. The index is your only board; learn to run the weekly pass in twenty minutes flat.

**Module 6 - The planning layer.** Everything above is the spec loop: one intent, one change. A product increment (several features, many specs, shared regression) is planned holistically first and decomposed second, through a Product Plan. That is the other half of this role, and it has its own module: [The Planning Layer in Veldo](planning-layer.md). Take it once you are fluent in testable intent, because a plan is a graph of specs and a shaky spec makes a shaky plan.

## 5. How you break Veldo without meaning to

- **Untestable criteria.** The machine will build something; it will be proven against nothing. Every downstream failure traces back to this.
- **Deciding by silence.** A blocked spec you ignore for three days taught the team that blocked means dead. Answer or kill, same day.
- **Re-litigating shipped work in chat instead of specs.** "Actually can we also..." in a message thread is intent leakage; it belongs in a new spec or a revision.
- **Approving specs you have not read.** "Ready" is a signature. The one thing the method cannot survive is a rubber stamp at the intent gate.
- **Scope-stuffing.** Ten criteria on one spec is three specs wearing a coat. Big specs are where proof gets shallow and reviews go blind.

## 6. You have arrived when

- Your last five specs went through implementation with zero clarifying escalations.
- You killed something in the weekly pass without guilt.
- You caught a letter-not-intent gap from the receipt, and the criterion you added would have caught it mechanically.
- You have not attended a status meeting in a month, and you know the state of everything.
- An engineer asked YOU how to phrase a criterion.

## Document History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-07-16 | Initial training document |
| 1.1 | 2026-07-16 | Module 6 added, pointing to the new planning-layer module - the holistic half of the role, above the spec loop |
