# The Backend Developer in Veldo

*Training series. The hard truth first: the destination is that people who really want to type code stop typing code, because their judgment is worth more than their typing.*

*Version 1.0, 2026-07-16*

## 1. Your job, redefined

You did not spend years learning to type. You spent years learning what breaks, what scales, what a race condition smells like, where the edge cases hide, and what a good system feels like. Typing was how that knowledge got into the codebase. It was the transport, not the value. Veldo replaces the transport. The knowledge is now delivered three ways: into specifications (technical intent the agent builds against), into the gate (checks that encode what you know about how things break), and into judgment (reading diffs, proofs, and verdicts with the eye that took years to build).

This is a real loss and it is fine to say so: the flow state of building by hand was genuinely joyful. It is also finished as a profession's core activity, the way hand-assembly was. What remains is the senior half of the job, for everyone.

| What stops | What starts |
|---|---|
| Typing implementation code | Collaborating on specs where the technical intent is subtle (idempotency, ordering, failure modes) |
| Writing most tests by hand | Gate engineering: designing the checks, killing flakes, deepening coverage where risk lives |
| Code review as line-by-line reading of teammates' PRs | Judging agent output: does this diff match the intent; is this proof real; is this test meaningful |
| Standup, estimation, ticket grooming | The escalation seat: two failed reviews, gnarly production debugging, the problems agents cannot crack |
| Being measured by output volume | Being measured by what you catch, what you specify, and what stops breaking |

## 2. Your day

You run `/veldo:status`, see three specs in flight, and read the verdict on the one that shipped overnight. A spec needs technical shaping: the PM's intent is right but the idempotency criterion is missing, so you add it in a two-line conversation. An implementation failed review twice, so it lands in your lap, and this is the fun part: the actual puzzle, the thing agents still hand to a human. In the afternoon you notice the gate let a slow query through last week, and you spend an hour adding the performance check that makes that permanent knowledge instead of tribal memory.

## 3. Your moments in the loop (exact)

**Shaping a spec technically:**

```
Add to VELDO-0231: retries must be idempotent by payment intent id; a replayed
webhook must not double-credit. That's the criterion that matters here.
```

**Judging a proof.** Read `proof/<id>/manifest.json` with one question per criterion: would this evidence convince me if a stranger submitted it? A test named `test_no_duplicate_order` that mocks away the database convinces no one; say so:

```
AC1's test mocks the store, so it proves nothing about the race. Require the
integration variant against real Postgres.
```

**The escalation seat (after two failed reviews):**

```
The spec is ambiguous, not the code: "handle concurrent updates" has no
observable criterion. Rewriting: last-writer-wins per field, with the
version check returning 409 on conflict. Rerun.
```

**Gate engineering:**

```
/veldo:spec Add a gate check: any endpoint responding over 500ms p95 in the
integration suite fails the build. Standing knowledge, not memory.
```

## 4. The curriculum

**Module 1 - From typing to specifying.** Take a feature you would normally build by hand. Write only the spec: every failure mode, ordering rule, and boundary you would have handled silently while typing must become a criterion. Run it. Compare the agent's implementation to what you would have written; every difference that matters is a criterion you missed.

**Module 2 - Reading diffs you did not write.** Speed and skepticism. Exercise: review five agent diffs; for each, find one thing to reject or one sharpened criterion, in under ten minutes each. (There is always one.)

**Module 3 - Proof literacy.** Exercise: we plant a proof manifest where one criterion is satisfied in letter but not intent. Find it. Then write the criterion phrasing that would have made the gap impossible.

**Module 4 - Gate engineering.** The new "writing code that matters." Exercise: take the last three production incidents; for each, build the check that would have caught it pre-merge, and prove it by reverting the fix in a branch and watching the gate go red.

**Module 5 - The escalation craft.** Debugging without having written any of it. Exercise: an agent is stuck after two review failures on a sandbox spec; resolve it, and notice that the fix was to the spec more often than to the code.

## 5. How you break Veldo without meaning to

- **"Faster to just do it myself."** The single most corrosive sentence. It is sometimes even true for the one change, and it steals the criterion, the proof, and the gate check from every future change. The typing urge is a signal you have knowledge that belongs in the spec or the gate; put it there.
- **Rubber-stamp judgment.** Skimming proofs turns the whole method into theater. Three sharp reviews beat ten shallow ones.
- **Hoarding the escalations.** Solving the hard one and not leaving behind the check or the criterion means you fixed a change instead of the system.
- **Nostalgia sabotage.** "The old way was faster" demos on cherry-picked examples. The receipts answer this; let them.

## 6. You have arrived when

- Your specs run through implementation with zero clarifying escalations.
- You caught a real defect from a proof manifest alone.
- Something you know about how systems break is now a gate check with your name on the commit.
- You took the escalation seat on a nasty one and enjoyed it more than you would have enjoyed typing the feature.
- A month passed without you writing implementation code, and your fingerprints are on everything that shipped.

## Document History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-07-16 | Initial training document |
