# The Web Developer in Veldo

*Training series. Your destination role: Product Systems Engineer with the browser as your domain of judgment.*

*Version 1.0, 2026-07-16*

## 1. Your job, redefined

Everything in the backend developer's document applies to you: typing was the transport for your knowledge, not the value, and the destination is that people who really want to type code stop typing code. Read that document first; this one covers what is uniquely yours: the browser is the most hostile runtime in computing, and your judgment about it is now delivered through specs, the design contract, and evidence, not through hand-written components.

| What stops | What starts |
|---|---|
| Typing components, CSS, and browser tests | Specifying interaction behavior: loading, error, focus, responsive, and offline states as criteria |
| Translating Figma into code by hand | Stewarding the design contract: tokens, the component library, the baselines |
| Manual browser passes before release | Requiring browser-level evidence: Playwright journeys, accessibility output, visual diffs |
| A screenshot as proof it works | Judging evidence: does the trace show focus surviving the retry, or just pixels looking right |
| Frontend tickets on their own schedule | The same loop as everyone: spec, run, judge |

## 2. Your unique craft: the design contract

The three-layer design contract (tokens, components, baselines) is your product now. The component library in code that mirrors the design system one to one is the highest-leverage artifact a web person owns: every screen composed from it is on-design by construction, and every fidelity bug you prevent there is prevented everywhere, forever. When the gate's token lint fails on a raw hex value, that is your past work catching what used to be your future rework.

## 3. Your moments in the loop (exact)

**Shaping a UI spec's ugly states (the value you add that mocks never show):**

```
Add to VELDO-0214: AC6, the empty state renders correctly while offline;
AC7, focus lands on "Browse products" when the state appears, and survives
a failed navigation; AC8, screen-reader announces the heading before the button.
```

**Judging browser evidence:**

```
The Playwright trace for AC2 clicks the button but never asserts the route
changed under a slow network. Require the navigation assertion with
throttling on.
```

**Design-system stewardship:**

```
/veldo:spec Promote the new date-picker into the component library, mirrored
to the Figma component, tokens only, with baselines at three viewports.
Product screens stop hand-rolling date inputs from merge onward.
```

## 4. The curriculum

Modules 1-3 and 5 of the backend developer's curriculum apply verbatim (specifying, reading diffs, proof literacy, escalation). Your additions:

**Module W1 - The design contract.** Exercise: take one screen that drifts from its mock today; fix it the Veldo way: token lint rule, component promotion, locked baseline. Then try to reintroduce the drift and watch the gate refuse.

**Module W2 - Evidence for experience.** Exercise: a change passes all component tests but loses keyboard focus after a retry (planted). Find it from the evidence alone, then write the criterion that makes the class impossible.

**Module W3 - Baseline judgment.** Tolerances are yours to own: too tight and the gate is flaky, too loose and drift walks through. Exercise: set tolerances for a text-heavy screen and an image-heavy screen and defend the difference.

## 5. How you break Veldo without meaning to

- Everything in the backend document, plus:
- **Hand-tweaking the last five percent.** Adjusting CSS after the agent finishes invalidates the evidence and teaches you to distrust the loop instead of sharpening the spec.
- **Screenshot faith.** A screenshot proves pixels once; a criterion with a trace proves behavior forever.
- **Letting the component library rot.** Every screen built around a missing component is fidelity debt the gate cannot see.

## 6. You have arrived when

- A designer's mock went to production without you typing a line, and it is exact.
- The token lint caught a violation from an agent, because you built the rule.
- Your ugly-state criteria (offline, focus, screen reader) are copied by other specs as the standard.
- You judged a visual diff in one minute and were right.

## Document History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-07-16 | Initial training document |
