# The Architect in Veldo

*Training series. The gate is the architecture now: you own the system that decides what is true.*

*Version 1.0, 2026-07-16*

## 1. Your job, redefined

Architecture used to be advisory: diagrams, review meetings, guidelines that engineers followed when they remembered to. In Veldo, architecture is enforced or it is fiction. Your decisions live in three places that machines obey: the policy file (risk tiers, protected paths), the gate (what proof means here), and the contracts (what a spec, a proof, a verdict must contain). You stop being the person who draws boxes and start being the person who designs the proof system.

| What stops | What starts |
|---|---|
| Architecture review meetings | Architecture constraints as policy and gate checks that block violations mechanically |
| Slideware and wiki diagrams that drift | Architecture decisions in the repo, agent-readable, enforced where enforceable |
| Being consulted after the design is done | Decomposition judgment before implementation: the DB-evolution refusal is your standard |
| Guarding quality by reviewing everything | Designing the reviews: independence levels, human lanes, what evidence each risk tier demands |
| Approving technology choices in the hallway | Owning the protected-path taxonomy and the risk floors, as reviewed changes to policy |

## 2. Your day

You read verdicts and escaped-defect reports the way you used to read code: they tell you where the proof system is thin. You spend your time on the highest-leverage artifacts in the company: the policy file, the gate's check suite, the contract shapes, the standing ADRs. When a spec smells too big, you decompose it or teach the agent's refusal to stick. When the same defect class escapes twice, you add the check that makes a third time impossible.

## 3. Your moments in the loop (exact)

**Flooring a new risk area:**

```
Protect payments/reconciliation/** at critical in the billing repo. Reason:
mis-reconciliation is unrecoverable money movement.
```

The agent drafts the policy change; it goes through the loop like any change (policy is itself protected), and from merge onward every touch of that path is floored, mechanically, forever.

**Judging a decomposition.** A spec arrives with ten criteria across three subsystems:

```
Split VELDO-0310: the schema change ships first (additive, dual-write), the
read-path switch second behind a fallback, the cleanup third after a week
of observation. Each independently reversible.
```

**Raising the reviewer bar:**

```
Changes under core/routing/** review at L3 minimum. Update policy.
```

**The escaped defect ritual.** Something shipped proven and broke anyway:

```
Add to the gate: a contract test that fails when the API returns amounts
without currency. That class of escape is now impossible. Spec it.
```

## 4. The curriculum

**Module 1 - Policy as your medium.** Learn `.veldo/policy.yaml` cold: tiers, floors, independence ladder, merge rule. Exercise: take three real past incidents and write the policy lines that would have forced a human gate in front of each.

**Module 2 - Gate design.** The gate is a portfolio: fast checks for every change, expensive checks for risky ones, zero flaky checks ever. Exercise: audit the pilot repo's verify.sh; find the check that is missing (what shipped bug would it have caught?) and the check that is theater (what does it actually prove?).

**Module 3 - Decomposition judgment.** The skill of splitting work so every merge leaves the system correct. Exercise: take the gnarliest pending migration and write the three-spec expand-and-contract plan with rollback per stage.

**Module 4 - Contracts and ADRs for machine readers.** Your decisions are read by agents thousands of times. Exercise: rewrite one existing ADR so an agent implementing against it cannot misread it; then have an agent implement a small spec in that area and see what it does.

**Module 5 - Reading the system's health.** Proof latency, first-pass rate, escaped defects, reversion rate: these are architecture metrics now. Exercise: from the events log, find the slowest gate stage and cut it 30% without losing evidence.

## 5. How you break Veldo without meaning to

- **Guidelines in prose instead of checks.** If it matters and is checkable, it goes in the gate. A guideline the agent can talk itself around is a suggestion (stance 3).
- **Protecting everything.** Floor half the repo at critical and you have rebuilt the approval queue Veldo deleted. Protect the unrecoverable; let the reversible flow.
- **Reviewing everything yourself.** You are the bar-setter, not the bar. Design the review; do not become its bottleneck.
- **Big-bang designs.** Your own designs must arrive as decomposed spec sequences, or nobody else's will.

## 6. You have arrived when

- A violation of your architecture cannot merge, and you did not have to be present.
- The policy file reads like your architectural philosophy, executable.
- An escaped defect leads to a new check within a day, every time.
- Your decomposition of a scary migration shipped in three boring merges.

## Document History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-07-16 | Initial training document |
