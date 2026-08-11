# The Designer in Veldo

*Training series. Your mock becomes a contract, your judgment becomes a lane, and your verdict becomes a file with your name on it.*

*Version 1.0, 2026-07-16*

## 1. Your job, redefined

Design used to end in a handoff: the mock went over the wall, a developer interpreted it, and fidelity depended on their patience and your vigilance. In Veldo the wall is gone in both directions. Your design system enters the repository as data (tokens, a mirrored component library, locked baselines), agents build against it exactly, and the machine defends fidelity forever after one human approval. And where judgment cannot be mechanized - whether the interaction FEELS right - you are not a consulted opinion; you are a review lane with teeth: `design_review` in a spec's required evidence means nothing user-facing merges without your recorded verdict.

| What stops | What starts |
|---|---|
| Redlines and exhaustive handoff annotations | The design contract: tokens and components as repository data agents must use |
| Pixel-policing implementations after the fact | One side-by-side approval per screen; the baseline defends it from then on |
| Chasing developers about spacing | The token lint chases them (and the agents) mechanically |
| Design approval as a vibe in a meeting | A structured verdict file, bound to the exact commit, with your name |
| Producing every artifact by hand | Reviewing generated variants; your taste applied at the judging layer rather than the production layer |

## 2. Your moments in the loop (exact)

**Feeding the contract (once per design-system change):**

```
The new spacing scale is final in Figma. Export tokens and mirror the two
new components into the library; everything downstream inherits.
```

**The baseline approval (once per new or changed screen):**

```
Agent: Compare: mock 214-1187 vs tests/baselines/orders-empty-desktop.png
       and -mobile.png. Approve as locked baselines?
You:   Desktop yes. Mobile: button is 8px from the bottom, mock shows 24.
       Fix and recapture.
...
You:   Approved.
```

**The verdict (your lane, on look/feel/flow changes):**

```
Record my design review for VELDO-0214: approved. Matches the mock on both
breakpoints; the motion on state-entry reads right.
```

Which becomes `proof/VELDO-0214/design-verdict.json` with your name, bound to that commit; if the commit changes, your verdict is stale by design and the merge waits for you again.

**Rejecting with usable precision:**

```
Record my design review for VELDO-0219: rejected. The error state reads as
success: green check iconography on a failed payment. Blocking. The empty
state copy is fine.
```

## 3. The curriculum

**Module D1 - Criteria your taste can survive.** "Make it feel premium" proves nothing; "the card uses elevation-2, entry animation 200ms ease-out, no layout shift on load" proves itself. Exercise: take one mock and split your intent into what the machine can hold (tokens, spacing, states become criteria) and what only you can judge (the residue is your lane, and it is smaller than you think).

**Module D2 - The states nobody mocks.** Empty, loading, error, offline, permission-denied. Exercise: for one real screen, specify all five states through the spec dialogue; watch how many decisions you were leaving to chance.

**Module D3 - Verdict discipline.** Exercise: review three generated variants of one flow; record a structured verdict on each, with blocking versus non-blocking findings separated. Then the planted one: a polished variant that confuses users under an error state; reject it for the right reason.

**Module D4 - Baseline stewardship.** Tolerances, viewports, when a baseline SHOULD change. Exercise: a legitimate rebrand touches forty baselines; run the re-approval efficiently instead of one screen at a time.

## 4. How you break Veldo without meaning to

- **Subjective criteria.** "Intuitive" and "clean" build nothing and prove nothing; they are your judgment's job, not the spec's.
- **The universal design gate.** Requiring your verdict on every change (copy fixes, backend work) rebuilds the queue; your lane is look, feel, and flow, as policy states.
- **Verdicts in chat.** "Looks good, thumbs up" in a thread is not a verdict; if it is not the file, the merge policy cannot see it, and your authority silently evaporates.
- **Letting the contract drift.** Figma updated, tokens not re-exported: now the machine defends yesterday's design against today's, precisely.

## 5. You have arrived when

- A screen shipped pixel-exact to your mock and you never spoke to the person, because there wasn't one: your contract and your two approvals did it.
- Your rejection verdict blocked a merge, and everyone agreed the system worked.
- The five ugly states of every new screen are specified because your criteria became the template.
- You spend your week on design, not on defending design.

## Document History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-07-16 | Initial training document |
