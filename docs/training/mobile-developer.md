# The Mobile Developer in Veldo

*Training series. Your destination role: Product Systems Engineer whose domain of judgment is the one runtime you cannot roll back.*

*Version 1.0, 2026-07-16*

## 1. Your job, redefined

Read the backend developer's document first; the transformation is the same. What is uniquely yours is the fact that defines all mobile judgment: **a shipped client cannot be recalled.** Web rolls back in minutes; your mistake lives on customers' devices until they choose to update. That asymmetry is why your knowledge - lifecycle, offline, fragmentation, store mechanics - becomes some of the most valuable spec-and-evidence material in the company.

| What stops | What starts |
|---|---|
| Typing screens, sync code, device tests | Specifying lifecycle truth: process death, offline, backgrounding, permissions, upgrade paths as criteria |
| Simulator green as "works" | Requiring device-matrix and lifecycle evidence; a clean simulator proves almost nothing |
| Manual release-candidate passes | The gate carries the matrix; you judge the evidence |
| Bundling work because releases are expensive | Small reversible changes behind flags, decoupled from the release train |
| Assuming revert = rollback | Designing server-side containment: every risky client behavior has a kill switch that does not need a store release |

## 2. Your unique craft: reversibility where none exists

The store release train is Veldo's one legitimate release train, and your craft is making it boring: features land dark behind flags across multiple releases, fully decoupled from exposure, which happens server-side, gradually, observed, and reversible. "How do we turn this off without a release?" is the question you ask of every spec, and the rollback field of every mobile spec must answer it.

## 3. Your moments in the loop (exact)

**Shaping a spec with lifecycle truth:**

```
Add to VELDO-0318: AC4, a sync interrupted by process death resumes without
data loss on next launch; AC5, the feature behaves correctly when the app
returns from background after 6+ hours; AC6, v(N-1) clients against the new
server see the legacy behavior, unbroken.
```

**The containment question (every risky mobile spec):**

```
Rollback says "revert the commit" - not good enough for mobile. Add the
server-side flag; exposure at 5% of devices first; crash rate gates the
ramp. Then it's ready.
```

**Judging device evidence:**

```
The matrix run skipped the OS version with 22% of our fleet. Rerun with it;
AC2's animation criterion is exactly where that version bites.
```

## 4. The curriculum

Backend modules 1-3 and 5 apply verbatim. Your additions:

**Module M1 - Lifecycle evidence.** Exercise: an agent change passes a clean simulator but loses edits after process death during sync (planted). Catch it from the evidence, then write the standing criterion so every future sync spec inherits it.

**Module M2 - The containment design.** Exercise: take a real upcoming feature and design its dark-launch: the flag, the exposure ramp, the crash/metric gates, and the kill switch, all as spec criteria.

**Module M3 - The upgrade matrix.** Old client + new server, new client + old server, interrupted upgrade. Exercise: write the compatibility criteria for a schema-touching change and have the agent prove all three cells.

## 5. How you break Veldo without meaning to

- Everything in the backend document, plus:
- **Simulator faith.** The clean simulator is where mobile bugs go to hide.
- **Release-train batching.** Bundling unrelated work "because a release is expensive" recreates the big-bang deploys Veldo exists to kill; the flag decouples landing from exposure.
- **Rollback theater.** A rollback plan that requires a store release is a hope, not a plan.

## 6. You have arrived when

- A feature shipped dark across two releases and nobody noticed until you turned it on for 5%.
- Your kill switch got used in anger, worked in seconds, and the postmortem praised the spec.
- The upgrade-matrix criteria you wrote are the repo standard.
- A month without typing implementation code, and the crash rate is the best it has ever been.

## Document History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-07-16 | Initial training document |
