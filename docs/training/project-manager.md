# The Project Manager and Veldo

*Training series. The candid document: the coordination machinery dissolves, the judgment half stays human until the planning layer proves otherwise, and the person holding the role has real places to go.*

*Version 1.1, 2026-07-16*

## 1. The honest verdict

Veldo eliminates the machinery a project manager coordinates: there are no sprints to plan, no standups to run, no status to collect (the index and the receipts ARE the status, generated, always current), no dev-to-QA handoffs to shepherd, no release trains to schedule for ordinary changes, and no estimation rituals because implementation capacity stopped being the bottleneck. Inside the loop, there is nothing left to project-manage. Saying this plainly is kinder than pretending: **the coordination machinery of project management does not exist in Veldo.** One honest condition on the stronger claim: the JUDGMENT half of the job - keeping a large feature (five screens, a hundred permutations) coherent, noticing drift before it becomes rework, sequencing under change - is only out of a human's hands when the planning layer has PROVED it can carry that judgment: dependency refusal working, drift surfaced by the plan status, revision impact computed, blockers raised loudly, all with receipts. That proof is an explicit Veldo 1.0 acceptance test. Until it passes, the Product Operations hat below is load-bearing.

What does NOT dissolve is the judgment good project managers actually carry: knowing which of thirty things matters, spotting the dependency nobody mentioned, noticing that a decision has been quietly unmade for a week, keeping externally-made promises honest. That judgment has three real destinations.

## 2. The three destinations

**Product Operations (the closest fit).** The index across repositories is groomed weekly; intake needs stewarding so external requests become specs instead of hidden work; emergency backfill debts need tracking; blocked human decisions need surfacing loudly. This is a real function - a fraction of one person at our scale, part of a role, not a role - and it is the coordination skill pointed at the system instead of at people. The failure mode to renounce explicitly: rebuilding Jira inside the index, adding meetings to "align", inserting yourself as a status intermediary. The system reports itself; your job is noticing what it reports.

**Product Intent (the bigger jump).** Many PjMs are half a PM already: they know the customers, the stakes, the promises. The Product Manager training document is the path; the spec dialogue replaces the coordination toolkit, and the leverage is far higher.

**Delivery-facing roles outside the loop.** Customer success, partner management, external program coordination: everywhere the company touches parties that do NOT run Veldo, the coordination skill remains fully valuable, because the outside world still runs on meetings and promises.

## 3. If you hold the Product Operations hat: your moments (exact)

**The weekly pass (yours to run, 20 minutes, the one ritual):**

```
/veldo:index
```

Then the four decisions per row: close, kill, unblock (name the human and the question), or confirm ready order.

**The intake watch:**

```
Three requests came in through support this week that never became specs.
Routing them through intake now; nothing enters work as a hallway promise.
```

**The debt watch:**

```
The emergency backfill from Tuesday is 20 hours old. Flagging: it blocks the
next ordinary merge in 4 hours.
```

**The decision surfacing (your highest-value act):**

```
VELDO-0244 has been blocked for 3 days on one question: do we refund partial
months? That is a founder decision. Asking it here, loudly, once.
```

## 4. The curriculum (for the Product Operations path)

**Module 1 - The index as the board.** Run five weekly passes in the sandbox. Exercise: the seeded index has 30 specs, 8 stale, 4 duplicates, 3 oversized, 1 overdue backfill; restore it in 20 minutes using agents, without creating a meeting or a second tracker.

**Module 2 - Metrics that matter.** Spec-to-ship time, proof latency, blocked-decision age, human minutes. Exercise: from the events log, find the real bottleneck this month and state it in one sentence (it will not be implementation).

**Module 3 - Intake discipline.** Exercise: take five raw requests (tickets, chat messages, a founder aside) and shepherd each into intake; watch which become specs, duplicates, or refusals.

**Module 4 - Un-learning.** The hardest module. List every recurring meeting and status artifact you ran before; write next to each what Veldo artifact replaced it; delete them all publicly.

## 5. How this transition breaks Veldo without meaning to

- **Status theater.** Adding owners, dates, and RAG colors to the index rebuilds the tracker Veldo deleted.
- **The alignment meeting.** Any recurring meeting about work state is a confession that someone is not reading the receipts.
- **Human middleware.** Relaying between people what the system already reports teaches people not to look.
- **Approval insertion.** Adding yourself as a checkpoint before merge, anywhere, for anything ordinary.

## 6. You have arrived when

- The weekly pass takes eighteen minutes and ends with two decisions surfaced to the right humans.
- A month with zero recurring meetings you own, and nobody has asked for status once.
- You caught a promise made to a customer that no spec covered, three weeks before it would have detonated.
- You can name the current bottleneck from the events log, and you are right.

## Document History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-07-16 | Initial training document |
| 1.1 | 2026-07-16 | The dissolution claim made honestly conditional on the planning layer proving it can project manage |
