# The Bcengi Spec Method

A spec-driven development methodology for a 5-person team that lives inside Claude Code. The premise: at Bcengi, code generation is already free. The scarce things are deciding what should exist, writing it down precisely enough that an agent cannot misunderstand it, and proving the result is correct before it ships. This method makes the spec the only durable unit of work and makes an unwaivable machine gate the only thing standing between a spec and production.

The whole method fits on one page (below). Everything after that page is the how.

---

## The one page

1. Work does not exist until it has a spec file in the repo. The spec is a short markdown file with intent, EARS acceptance criteria, and a done checklist. No spec, no agent.
2. Every repo has one `specs/INDEX.md`. That file is the plan. There is no other plan. Jira DEV becomes a thin read-only mirror, not the inner loop.
3. Humans write and accept specs. Agents implement them. The human gate is between spec and implementation, and again at the verify gate before merge.
4. Nothing merges until the machine gate is green: types, lint, tests including property tests, build, spec-drift check, secret scan, dependency check, and an independent fresh-context reviewer agent. The human reviews the 2-3 judgment calls the gate cannot make, not every line.
5. No sprints, no points, no standups, no velocity. Continuous flow with a WIP limit of one active spec per person plus their agent fleet.
6. Handover is a file, never a meeting. Persistent memory plus the KB plus the spec history mean a fresh agent rehydrates state on its own.
7. Five surfaces are guarded by CODEOWNERS and require a spec plus Dmitry sign-off before code: money (Stripe, pricing, PRICES CMS), auth, schema migrations, the Rust telecom core, and anything irreversible in production.

---

## 1. Principles

**The spec is the source of truth, the code is a build artifact of it.** We are spec-anchored, not spec-purist. We do not regenerate the whole codebase from specs every time (that is waterfall reborn and it collapses). Specs and code evolve together in the same PR, and the spec-drift check in CI enforces that they stay in sync. When they disagree, the spec is what we meant and the code is a bug.

**Humans author intent and acceptance. Agents author implementation.** The 70/20 split is our operating model: the human makes essentially all the planning and decomposition decisions and almost none of the keystroke decisions. If you find yourself hand-writing implementation, stop and ask why the spec was not good enough for an agent to do it.

**Verify by construction, do not trust and review.** A clean-looking agent diff is more dangerous than an ugly one because it invites rubber-stamping. We do not defend against that with more human eyeballs. We defend against it with gates the human cannot skip and a smoke test that actually runs the thing.

**Context is the scarce resource, keep it lean.** CLAUDE.md holds always-true facts only. Skills hold sometimes-relevant procedures. Specs hold this-task-only intent. We do not let instruction files bloat, because a fat always-loaded context measurably degrades the agent.

**Taste and decomposition stay human and stay small.** The one planning act that never gets delegated is cutting a fuzzy want into crisp, independently-verifiable specs. That is the job now. Everything downstream of a good spec is cheap.

---

## 2. The working loop

The loop has four phases and two human gates. It runs per spec, continuously, with no batching into sprints.

```
INTENT  ->  [Gate A: human accepts spec]  ->  IMPLEMENT (agent fleet)
                                                    |
                                                    v
                                            VERIFY (machine gate)
                                                    |
                                                    v
                              [Gate B: human accepts the 2-3 judgment calls]  ->  SHIP
```

**Phase 1 - INTENT (human, minutes).** A human writes a spec file. For most work this is 15-40 lines. The spec states what should exist and why, lists acceptance criteria in EARS syntax, and names the surface it touches. This is the expensive thinking and it is deliberately done by a person. Dmitry or the surface owner writes it; an agent may draft it from a Telegram thread or a transcript, but a human accepts the words.

**Gate A - spec acceptance (human).** The surface owner reads the spec and answers one question: if an agent implements exactly this, and it passes, are we done and correct? If yes, the spec is marked `accepted` in INDEX.md and an agent is pointed at it. If no, the spec is not ready and no code gets written. This gate is where bugs are cheapest to kill.

**Phase 2 - IMPLEMENT (agent, minutes to hours).** The owner spins up one or more Claude Code agents in git worktrees, one worktree per spec, and points each at its spec file. The agent implements, runs the deterministic gates itself in-loop (types, lint, unit and property tests, build), and iterates until they are green before a human looks. The reliable ceiling is 4-8 concurrent agents per person, set by that person's verify capacity, not by tooling. One active spec at a time is "yours"; the fleet is agents working sub-specs of it or adjacent accepted specs.

**Phase 3 - VERIFY (machine, automatic).** The PR opens and CI runs the full gate (section 5). Critically this includes an independent reviewer agent running fresh context on a different model from the one that wrote the code, because the author is blind to its own bugs. The gate produces a green/red signal and a short list of judgment calls it surfaced but cannot decide.

**Gate B - judgment acceptance (human).** The human does not re-read every line. The gate already proved the lines. The human reviews only: the intent match (does this actually do what the spec meant), the 2-3 flagged judgment calls, and, for guarded surfaces, a mandatory run-it smoke test. Then merge.

**Phase 4 - SHIP.** Merge to the trunk triggers deploy per repo (section 8). The spec's status flips to `shipped` in INDEX.md, which is the single source of "what is live."

### Cadence

There is no sprint. There is a rhythm.

- **Continuous:** the loop above, all day, per spec.
- **Monday spec review (async, 20 minutes, no meeting by default):** each owner opens their repo's `specs/INDEX.md`, prunes done specs to the shipped log, and confirms the top 3 accepted specs for the week. This is the only recurring ceremony and it is editing a file, not attending a call. Dmitry reads the five INDEX files as his weekly plan.
- **Anytime:** anyone can add a `draft` spec. Only the surface owner can move it to `accepted`.

That is the entire cadence. Standups, sprint planning, grooming, and retro-as-meeting are gone. Their function survives as artifacts: status lives in INDEX.md, retro lessons get written to the KB and to CLAUDE.md as rules, so the lesson travels to the next agent instead of evaporating in a meeting.

---

## 3. What replaces sprint planning

Sprint planning assumed human execution time was estimable and worth committing to in two-week batches. Neither holds. Agent execution time bears no relation to human effort, so we delete estimation rather than fix it.

The replacement is **the accepted-spec queue with a WIP limit.**

- Each repo's `specs/INDEX.md` has three sections: `Accepted` (ready to implement, ordered by priority), `In Flight` (an agent is on it now), and `Shipped` (rolling log, trimmed monthly).
- WIP limit: one In Flight spec per human at a time. You do not start a second until your first ships or is explicitly parked. This is the single most important throughput rule. Pointing more agents at more repos without shipping the current work is exactly how a team ships less, not more.
- Priority is set by Dmitry (or the surface owner for pure-tech work) by ordering the Accepted list. Reordering a markdown list is the entire planning act. No poker, no points, no capacity math.
- "How long will it take" is answered with cycle time from the shipped log (spec-accepted to shipped, measured), not with an estimate. If someone needs a date, we quote the median cycle time for that surface.

---

## 4. Minimal tracking and Definition of Done

### Tracking

The tracker is `specs/INDEX.md` per repo. That is it. It is in the repo, so the agent can read it, diff it, and edit it, which is the whole reason it beats Jira for the inner loop.

Jira DEV survives in exactly one role: the human-facing what/why/priority ledger for cross-repo and business-visible work, and the link between a CEO-* business ticket and the spec that implements it. It is a thin roll-up, updated by a hook or a weekly agent that syncs INDEX statuses into Jira, never the place work actually happens. If a spec exists, its Jira ticket (if any) just points at the spec file. We never maintain state in two places by hand.

A spec's lifecycle states, all tracked in INDEX.md:
`draft -> accepted -> in-flight -> shipped` (plus `parked` for anything paused).

### Acceptance criteria vs Definition of Done

These are different and both required.

**Acceptance criteria are per-spec** and written in EARS, one testable line each, each mapping one-to-one onto a test:

```
WHEN a TravelPass user has auto-refill enabled AND balance drops below the trigger
THE SYSTEM SHALL initiate exactly one refill charge within 60 seconds
AND SHALL NOT initiate a second charge while the first is pending.
```

That single line becomes one property test (no double-charge invariant) and one example test (the happy path). If you cannot phrase a criterion as `WHEN ... THE SYSTEM SHALL ...`, the intent is still fuzzy and the spec is not ready for Gate A.

**Definition of Done is a standing, repo-wide gate**, identical for every spec, encoded in CI so it cannot be skipped:

A spec is Done only when:
1. Every acceptance criterion has a passing test named after it.
2. All deterministic gates are green (types, lint, unit, property, build).
3. Spec-drift check passes (the spec file and the code changed in the same PR; a spec touching a guarded surface has a linked spec-hash in the PR).
4. Secret scan and dependency check pass (no leaked secrets, no unresolvable or newly-hallucinated package names).
5. The independent fresh-context reviewer agent returned no blocking finding.
6. For guarded surfaces only: a human ran the smoke test and signed off.
7. The spec's status is set to `shipped` in INDEX.md.

The rule, stated once: a task is done only when its acceptance criteria are met and the standing Definition of Done is satisfied. Neither alone counts.

---

## 5. The quality gate (how AI work is verified and reviewed)

Three layers. The human is deliberately the thinnest layer, at the top, on the fewest decisions.

**Layer 1 - agent-runnable, in-loop (the agent does this to itself before any human or CI sees it).** Types, lint, unit tests, property tests, build. The agent is given the command to run all of these and is instructed to not surface work until they are green. This is the highest-leverage practice we have: give the agent a machine-checkable pass/fail so the human is not the loop.

**Layer 2 - CI conformance gate (automatic, on every PR).** This is the unwaivable backbone.
- Spec-drift detection: code changed without its spec, or a guarded-surface change without a linked accepted spec, fails the build.
- Independent reviewer agent: a fresh Claude Code run, different model from the author, reviews the diff against the spec with no memory of writing it. It cannot approve; it can only block or pass with flagged judgment calls.
- Property-based tests run as a first-class gate, not an afterthought. Property tests plus example tests together catch materially more than either alone, and they are exactly the tests agents write well. Our standing invariants by surface: no-negative-price and no-double-charge (companion, Stripe), round-trip encode/decode and monotonic sequence numbers (Rust core), geo round-trips and non-empty result contracts (PostGIS places), cost-cap-per-plan under 0.10 dollars (tripdesk).
- Security gates on the two things that actually bite us: secret scan (Claude-assisted commits leak secrets at roughly double baseline, so this is not optional) and dependency verification against slopsquatting (agents hallucinate stable, weaponizable package names; every new dependency must resolve to a real, pre-existing, pinned package or the build fails).

**Layer 3 - human judgment (thin, top slice only).** The human does not review lines. The human reviews:
- Intent: does this do what the spec meant, beyond passing the literal criteria.
- The 2-3 judgment calls the reviewer agent surfaced.
- For guarded surfaces: a mandatory run-it smoke test. You execute the actual flow (charge a test card in test mode, register a PLMN in staging, hit the endpoint) and watch it work. No smoke test, no merge on those surfaces.

**The proof-it-works discipline.** For anything on a guarded surface, the PR description must contain a proof: a short note of the manual check you ran and its result, plus the bundled automated test. A computer cannot be held accountable, so the human who merges is. The Replit-deleted-the-prod-database story is the standing reminder of why irreversible surfaces get a human hand on them.

**CODEOWNERS.** Five surfaces require both an accepted spec and owner sign-off, and are the only places broad human review applies: money (Stripe, pricing, the PRICES/MVNE_PRICES CMS which per house rule only webflow-ops writes), auth, schema and live data migrations, the Rust telecom core, and any irreversible production action. Everything else rides the machine gate.

---

## 6. Specs and how intent is captured

**The spec file.** Lives at `specs/<short-slug>.md` in the relevant repo. Template, deliberately short:

```
# <slug>: <one-line intent>
Surface: companion | mobile | places | core | web-cms   Guarded: yes/no
Owner: <human>    Status: draft|accepted|in-flight|shipped

## Why
2-4 sentences. The problem and the decision. Link the CEO-* ticket or Telegram thread if any.

## Acceptance criteria (EARS)
- WHEN ... THE SYSTEM SHALL ...
- WHEN ... THE SYSTEM SHALL ...

## Out of scope
Bullet the things this deliberately does not do.

## Notes for the implementing agent
Files, patterns to follow, gotchas. Keep lean.
```

**Capturing intent without ceremony.** Intent arrives as a Telegram message to Dmitry, a KB note, or a live thought. An agent can draft the spec from that raw input (transcript to spec is a solved pattern), but a human owns the accept. The rule that replaces ticket-writing: we update the spec from the conversation, and we do not open a Jira ticket for it. Jira only gets involved when the work is business-visible and needs to show up on a CEO dashboard.

**Big or risky work gets decomposed into multiple specs by a human.** Decomposition is the non-automatable act. A schema migration plus its backfill plus its API change is three specs with an ordering, not one. Risky work (migrations, new dependencies, telecom core) stays human-led at roughly 60/40 human-to-agent, meaning the human writes tighter specs and reviews harder, not that the human types more.

**Plans, when needed.** For a multi-spec effort the owner drops a `specs/<slug>-plan.md` that lists the child specs and their order. This is the only "plan" artifact and it is optional for single-spec work.

---

## 7. Knowledge and handover

Handover stopped being a document or a meeting and became a file. Bcengi already has the two things the rest of the industry is bolting on: persistent file-based AI memory and a knowledge base. We lean on them hard.

- **CLAUDE.md per repo:** always-true facts about that codebase. The build command, the run command, the conventions, the guarded surfaces, the gotchas that never change. Kept lean on purpose.
- **Skills:** procedural, sometimes-relevant workflows (how to regen the deck, how to run the places crawler, how to smoke-test a Stripe flow). Loaded on trigger, not always.
- **Specs history:** the `Shipped` log in INDEX.md plus the spec files themselves are the durable record of what was built and why. A fresh agent reads the spec to understand a feature, not a wiki.
- **The KB and persistent memory:** carry cross-session context and lessons. A retro lesson is not discussed in a meeting, it is written as a rule (into CLAUDE.md if always-true, into a memory file if behavioral) so it reaches the next agent automatically.

The payoff: onboarding a new agent, or a new human like Misha, collapses from weeks to hours, because a fresh agent rehydrates from memory plus repo context plus the spec index rather than from a person explaining state. There is no "sync meeting" because there is no context stranded in someone's head. If context is not in a file an agent can read, it does not exist.

The discipline this demands: when you learn something, write it to the right place immediately (real-time, not batched). A lesson kept in your head is a handover you failed to do.

---

## 8. Releases

Continuous, per repo, gated by the same machine gate. There is no release train and no release ceremony.

- Merge to trunk is the release trigger. If the gate is green, it merges; merged code deploys. The gate is the release process.
- **Guarded surfaces get a staged rollout, not a bigger meeting.** Money, auth, migrations, and the Rust core deploy to staging first with the human smoke test, then to production. Migrations use the expand-contract pattern (add, backfill, switch, drop) as separate shipped specs so no single deploy is irreversible.
- **Rollback is a revert of the merge, and the spec goes back to `accepted` with a note.** Because the spec is the source of truth, a rollback is never lossy: the intent is still captured, only the (buggy) implementation is pulled.
- **Every speed metric is bolted to a quality guardrail.** We track cycle time (spec-accepted to shipped) paired with rework rate (shipped specs that needed a follow-up fix within a week). We never report one without the other, because deploy-frequency and PR-count lie once agents write most of the code. We measure the system, never the individual. LOC, commits, and PRs-per-week are banned as signals because they rise when you generate more code regardless of value.

---

## 9. Artifacts (the complete list)

That is the whole set. If an artifact is not on this list, we do not maintain it.

- `specs/<slug>.md` - the unit of work. Intent plus EARS acceptance plus done checklist.
- `specs/INDEX.md` - the plan and the tracker, per repo. Accepted / In Flight / Shipped.
- `specs/<slug>-plan.md` - optional, for multi-spec efforts.
- `CLAUDE.md` - always-true facts per repo.
- Skills - sometimes-relevant procedures.
- `CODEOWNERS` - the five guarded surfaces.
- CI gate config - the unwaivable Definition of Done, encoded.
- KB and persistent memory - durable lessons and cross-session context.
- Jira DEV - thin read-only mirror for business-visible work only.

Dead artifacts, explicitly retired: sprint boards, story points, velocity charts, burndown, detailed hand-written tickets as the inner loop, standup notes, separate grooming backlogs, per-line review threads.

---

## 10. Roles for the 5-person team

Roles are about spec ownership and gate authority, not about who types.

**Dmitry (CEO, spec author and priority owner).** Writes and accepts the specs that touch product direction, money, and strategy. Orders the Accepted lists across the five repos, which is the entire planning act. Holds final sign-off on all guarded surfaces. Runs his own agent fleet like everyone else. His Monday read of the five INDEX files is his dashboard.

**Igor (backend, owner of companion and core-adjacent backend specs).** Owns and accepts backend specs. Guarded-surface owner for schema migrations and money-touching backend (Stripe, pricing logic). Writes the property invariants for backend surfaces. Highest smoke-test burden because his surfaces are the guarded ones.

**Frontend (frontend and mobile, owner of Kotlin mobile and web/CMS UI specs).** Owns and accepts UI specs. Guarded-surface owner for any client that touches auth flows or payment UI. Never changes UX without a spec and sign-off (standing house rule).

**Infra (infra, owner of the deploy gate itself).** Owns the CI conformance gate, the security scans, the staged rollout for guarded surfaces, and the Rust core deployment path (PLMN, IPX). His most important artifact is the gate, because the gate is the release process and the quality backbone. Guarded-surface owner for irreversible production actions.

**Docs-eng (docs, owner of CLAUDE.md, skills, and the KB).** Owns the context layer: keeps CLAUDE.md lean and true, curates skills, keeps the KB and memory current, and runs the spec-to-Jira mirror. In an AI-native shop the docs role is context engineering, and it is load-bearing, not clerical. He is the person who makes handover-as-a-file actually work.

**Shared by all five:** everyone writes specs, everyone runs an agent fleet (4-8 concurrent, capped by their own verify capacity), everyone is the human on Gate B for their own surface, and everyone writes lessons to memory in real time. The independent reviewer is always an agent on a different model, never a teammate reading lines, so no one is a bottleneck on another person's throughput.

---

## Why this fits Bcengi specifically

You already ship fast, already live in Claude Code across many repos, and already have persistent memory plus a KB. That is the exact profile that wins here, because the hard problem the rest of the industry is scrambling to solve (where does context live) you have already solved. What you are missing is not more process, it is one disciplined artifact and one unwaivable gate. This method adds precisely those two things and deletes everything else. The failure mode it is built to prevent is the only one that actually threatens a fast small team: silent degradation shipped quickly and diffused accountability. The spec-before-code rule on money, auth, and the core, plus a CI gate no one can wave through, plus a named human on the merge of anything irreversible, is what converts your generation speed into shipped-and-trusted speed instead of into rework.
