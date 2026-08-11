# The Planning Layer in Veldo

*Training series. The product manager's other half: driving a whole iteration through the planning layer, above the spec loop.*

*Version 1.0, 2026-07-16*

## 1. What this module is

The Product Manager training document teaches the spec loop: one intent, one specification, one proven change. This module teaches the layer above it: how you take a whole product increment (several features, many specs, shared regression) and drive it through Veldo as one coherent thing, without a status board, a standup, or a Gantt chart.

The skill is planning holistically and then letting the machine decompose in order. You state the outcomes, the feature breakdown, the ordering, the regression, and what "done" means, once, in a **Product Plan**. From then on the plan is the context every spec inherits, the order specs are pulled in, and the board that reports its own state. You never assemble status; you read it.

One honesty note up front, so you inherit no illusion: the layer carries the mechanical half of project management (ordering, refusing broken order, surfacing drift, computing revision impact). Whether it fully carries the JUDGMENT half is an open Veldo acceptance test, settled only by delivering a real iteration through it. Until that proof lands, a human still watches the whole; this module trains you to be that human well.

## 2. When you plan, and when you do not

Two lanes, and choosing right is the first skill:

- **Do not plan** a bug, a copy fix, a config change, one isolated improvement. It is a standalone spec; `/veldo:spec` and go. Forcing a plan onto a one-liner is the ceremony Veldo deletes.
- **Do plan** a product increment: several features, many specs, a regression surface they share. That is where a plan earns its tens of minutes by keeping the whole coherent.

If a standalone change turns out to belong to an increment, you PROMOTE it into the plan rather than letting it float as a hidden dependency. The binding is enforced both ways, so there is no such thing as a half-promoted change that the gate tolerates.

## 3. Anatomy of a plan (what you are actually deciding)

A plan is not a schedule. Each part is a product decision only you can make:

- **Outcomes.** Observable changes for users, each with a measure. "Returning customers reorder in two taps" - not "build the reorder feature." State the product, not the work.
- **Non-goals.** The exclusions you name on purpose. This is where scope drift dies before it starts.
- **Constraints.** The budgets and invariants every spec below inherits, written once.
- **The feature tree.** The decomposition into capabilities a user can name, each tracing to an outcome.
- **The work DAG.** The ordered items, each becoming one spec, each with an honest `depends_on`. This is the part people get wrong: an empty dependency list is a decision you made; a missing one is an error. Small items, provable one at a time.
- **Regression.** The journeys that must stay green across the whole iteration, chosen up front, not accreted after each bug.
- **Release.** The milestone, whether pieces merge continuously as they go green or cut together, and what watching it in production means.
- **Open decisions.** Each names exactly what it blocks. A decision that gates nothing does not stop the frontier; a decision that gates work keeps that work off the frontier, loudly, until you answer it.

## 4. Driving the layer end to end (exact)

**Create.** You describe the increment; the agent interviews you at the PRODUCT level:

```
/veldo:plan create the orders redesign: reorder, saved carts, and the empty state
```

Answer in outcomes and features, not tasks. The agent drafts from the template and validates it. It is `draft` until you approve.

**Approve.** Reading the draft is the signature that makes the ordering real:

```
Approve the plan.
```

The agent records you as approver with a date and flips it to `ready`. Approve nothing you have not read; the plan is the context every downstream spec inherits, so a sloppy plan is a sloppy iteration.

**Pull the frontier.** You never pick work by gut; the plan computes what is buildable:

```
/veldo:plan status PLAN-0007
```

The burn-down shows each item as shipped, waiting on named dependencies, blocked by a decision, or on the frontier. Pull a frontier item into a spec and run it; repeat. Building out of order is refused by the machine (`run-check`), not left to your memory. Your judgment goes into WHICH frontier item matters most next, not into whether it is allowed.

**Revise under change.** Plans change; do it honestly:

```
Split W4 into an API item and a UI item; the UI now depends on the API.
```

The agent bumps the revision, records the note, and runs impact analysis so you see the blast radius on anything already shipped. A revision invalidates context built against the old version, mechanically, so nothing ships against a plan that quietly moved.

**Read status and metrics.** This replaces every status meeting you used to run:

```
/veldo:status
```

The plan burn-down plus the derived numbers (spec-to-ship time, proof latency, human minutes, open blockers) come from the event stream, never a spreadsheet. The one question to ask monthly: is human-minutes-per-shipped-change trending toward stating intent and judging results and nothing else?

**Release.** Only the check lets a plan close:

```
/veldo:plan release PLAN-0007
```

It verifies all work shipped, regression present, no open decision still blocking, a milestone named. For continuous mode the work already merged as it went green; release is the marker plus the observation window.

## 5. The curriculum

**Module 1 - Outcomes, not tasks.** Take a real upcoming increment and write its outcomes as measurable product states. Exercise: for each outcome, write the one measure that proves it; if you cannot, it is a task in disguise.

**Module 2 - The DAG.** Decompose that increment into work items with honest dependencies. Exercise: draw the graph, then have the validator catch a cycle you plant deliberately, and watch the frontier change as you mark items shipped in the sandbox.

**Module 3 - The frontier as your queue.** Run five pull-and-build cycles in the sandbox. Exercise: try to pull an item whose dependency is unshipped and watch `run-check` refuse it; that refusal is the ordering enforcing itself.

**Module 4 - Revision impact.** Change an approved sandbox plan three ways (add work, change a dependency, drop scope). Exercise: for each, read the impact output and name what it invalidated before you look at the answer.

**Module 5 - Regression you designed.** Declare the journeys that must stay green across the whole iteration up front. Exercise: set one journey to activate only after a specific item ships, and confirm it appears in the per-spec active set only from that point.

## 6. How you break the planning layer without meaning to

- **Planning the unplannable.** A plan around a single bug is ceremony; the direct lane exists for a reason.
- **A DAG that is really a list.** Every item depending on the previous one is a schedule wearing a graph's clothes; find the real independence and parallelize it.
- **Deciding by silence on an open decision.** A blocked frontier is the plan asking you a question loudly, once. Answer it or kill the item; leaving it teaches the team that blocked means dead.
- **Editing an approved plan instead of revising it.** Silent scope change under shipped work is exactly what the revision mechanism exists to prevent; use it.
- **Rebuilding a tracker on top of the plan.** Owners, dates, and status colors added by hand recreate the board Veldo deleted. The plan reports itself; your job is noticing what it reports.

## 7. You have arrived when

- You can look at an incoming request and place it in the right lane without thinking.
- Your last plan's DAG had real parallelism, and the frontier was never a queue of one.
- You revised an approved plan and could name what the revision invalidated before the tool told you.
- You have not run a status meeting in a month, and you can state the current bottleneck from the numbers.
- Someone asked you to "just track it in the plan" and you said no, because that is not what the plan is for.

## 8. Where this sits

The method's Stage 0 is the concept; the setup guide's sections 3.9 and 4.10 are the contract and the operating verbs; the runbook's planning chapter is the keystroke-exact walkthrough; and the Product Manager document is the spec-loop craft this module sits on top of. Read that one first if you have not.

## Document History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-07-16 | Initial planning-layer training module |
