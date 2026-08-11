# The Green Gate: A Verification-First Dev Method for Bcengi

The premise: at Bcengi, agents write most of the code and generation is effectively free. So the method is not about producing code faster. It is about making it safe to accept code fast. Every practice below exists to answer one question before a human spends attention: **has this been proven to work by something other than the agent that wrote it?** If yes, it moves. If no, it does not exist yet. Speed is a byproduct of trust, and trust comes from a gate, not from a person reading every line.

The name is literal. Work is either behind the gate (unproven, invisible) or through it (proven, mergeable). The gate is machine-runnable. Humans do not stand at the gate reading diffs. Humans decide what should exist and own the three or four surfaces where being wrong is unrecoverable.

---

## 1. Principles (the non-negotiables)

1. **Verify by construction, not trust-but-verify.** The agent does not "try to write correct code." It writes code plus the executable proof that the code meets its spec, and it runs that proof itself before anyone looks. No proof, no PR.

2. **The writer never certifies its own work.** The agent that wrote the code cannot be the agent that approves it. A fresh-context reviewer agent, ideally a different model, runs against the spec with no memory of the implementation choices. Authors are blind to their own bugs; this is structural, not a matter of diligence.

3. **The spec is the contract; the test is the spec made executable.** Intent is captured once, in-repo, in testable lines. Acceptance criteria map one-to-one onto tests. If a criterion cannot be written as a check, it is not an acceptance criterion yet, it is a wish.

4. **Machine gates are unwaivable; human gates are narrow and high-stakes.** CI does not have a "merge anyway" button that a tired founder clicks at 1am. Humans review only the handful of surfaces where a machine cannot judge intent or where being wrong is irreversible: money, auth, schema migrations, the Rust telecom core, anything that touches production data or a customer's connectivity.

5. **Delete estimation. Measure the gate.** No story points, no velocity, no sprint commitments. The only tracked numbers are cycle time (spec accepted to merged) and rework rate (merged then patched within N days). Every speed number is bolted to a quality number so nobody games throughput by shipping slop.

6. **Context is the scarce resource; keep instruction files lean.** CLAUDE.md holds always-true facts. Skills hold sometimes-relevant procedures. Nothing that is occasionally-true lives in the always-loaded file. A bloated instruction file degrades the agent's attention measurably, so we treat context budget like a real budget.

7. **Handover is a file, not a meeting.** A fresh agent re-hydrates from the repo plus persistent memory. We do not hold status meetings to move context between humans, because the context does not live in humans.

---

## 2. The working loop (the whole cadence)

There are no sprints. There is one loop, run continuously, per unit of work. A "unit of work" is one shippable change: a feature, a fix, a migration. It takes hours to a few days, never two weeks.

```
INTENT  ->  SPEC  ->  [human gate: is this the right thing?]
        ->  PLAN + DECOMPOSE  ->  [human gate: is the cut right? risky surfaces flagged?]
        ->  IMPLEMENT (agent, in a worktree)
        ->  SELF-VERIFY (agent runs Layer 1 in-loop until green)
        ->  GATE (CI runs Layer 2; reviewer-agent runs against spec)
        ->  [human gate: only if the change touches a risky surface]
        ->  MERGE  ->  RELEASE (continuous)  ->  MEMORY WRITE
```

The two human gates that always happen are cheap and early: **is this the right thing to build** (before spec is finalized) and **is the decomposition right** (before agents run). Both are taste calls, both are fast, both are non-delegable. The human gate at the end is conditional: it fires only for risky surfaces. Everything else merges on green.

**Cadence in practice.** No daily standup. Instead:

- **Monday, 20 minutes, async or a quick call:** open `specs/INDEX.md`. That file IS the plan. Reorder priorities, kill dead units, spawn new spec stubs. That is the entire "planning ceremony."
- **Any day, any time:** anyone (usually Dmitry, but any engineer) writes or edits a spec and opens the human gate on it. The moment it passes, an agent starts.
- **Continuous:** each engineer runs 2 to 4 agents in parallel worktrees. The ceiling is set by that person's review capacity, not by tooling. When you cannot verify a fourth agent's output, you do not start a fourth agent.
- **Friday, 15 minutes:** read the week's rework-rate and cycle-time numbers off the dashboard. If rework rose, we tightened the wrong gate or skipped verification somewhere. That is the retro, and its output is a KB write, not a discussion.

The retro function survives; the retro meeting does not. What travels is an artifact (a memory file, an INDEX note), never a recurring meeting.

---

## 3. What replaces sprint planning

Sprint planning was a mechanism for committing slow human execution to a two-week batch. Agent execution time is unpredictable per task and near-zero in aggregate, so batching is fiction. It is replaced by two things:

**(a) The spec index as a living Kanban.** `specs/INDEX.md` is the single source of "what and why and in what order." It is a flat markdown list with status per unit: `idea -> specced -> in-flight -> verifying -> merged`. WIP is limited per person by their review bandwidth, not by a sprint boundary. There is no burndown because there is nothing to burn down; there is a queue and a flow.

**(b) Decomposition as the one surviving planning act.** This is the human's real planning work and it does not get delegated. Before agents run, a human cuts the unit into tasks and marks each task's **risk class**:

- **green task:** pure logic, UI, docs, isolated backend. Agent runs, merges on machine-green, no human at the end.
- **red task:** touches money, auth, schema migration, the Rust core, production data, or a new external dependency. Agent runs, but a human is on the final gate and a run-it smoke test is mandatory.

The 60/40 split holds: roughly 60% of the thinking (decomposition, spec, taste) is human, 40% (implementation) is agent. Red tasks stay human-led even when an agent types the code.

---

## 4. Minimal tracking and Definition of Done

**Tracking.** The repo is the tracker. `specs/` folder plus `specs/INDEX.md` is the plan. Jira DEV survives only as a thin, human-facing roll-up: what we are working on, why, and priority, for the rare moment someone wants a bird's-eye view or Dmitry wants to see it on mobile. Jira is never the agent's inner loop, because the agent cannot see, diff, or edit Jira state. The diff is the contract. If it is not in the repo, the agent does not know about it, so it does not count.

Rule: **no ticket is created for work that has a spec.** The spec is the ticket. Jira gets a one-line roll-up entry per unit, auto-generated from the INDEX, and nothing more.

**Two tiers of "done."**

- **Acceptance criteria** are per-task, written in EARS form, and each maps to a test:
  `WHEN a TravelPass refill is requested AND balance is below threshold THE SYSTEM SHALL charge exactly the top-up amount and never a negative value.`
  One line, one test, testable or it does not go in.

- **Definition of Done** is a standing gate, identical for every task, never re-negotiated:

  1. All acceptance-criteria tests pass.
  2. Types, lint, build green.
  3. Unit tests plus at least one property-based test for any invariant the change touches.
  4. Reviewer-agent (fresh context, different model) ran against the spec and found no spec-drift.
  5. Security gate clean: no leaked secrets, no hallucinated/unpinned dependency.
  6. For red tasks only: human sign-off plus a recorded run-it smoke test.
  7. Memory written (see section 7).

A task is done only when its acceptance criteria are met **and** the standing Definition of Done is satisfied. Both, always.

---

## 5. How specs and intent are captured

Spec-anchored, never spec-as-source. Specs and code evolve together; tests enforce alignment. We do not regenerate the whole codebase from a spec (that is waterfall reborn, and the Rust core especially would collapse under it).

Every unit of work gets one file: `specs/<unit-name>.md`. It has exactly four sections, kept short:

```
# <unit name>
## Why            one paragraph of intent. the thing taste decided.
## Acceptance     EARS lines. each maps to a named test.
## Risk           green | red. if red, name the surface (money/auth/migration/core).
## Notes          links to prior art, KB entries, the reference agents should read first.
```

The `## Acceptance` block is the human's real authored artifact. Dmitry or the owning engineer writes it. The agent may draft it, but a human owns the final EARS lines because that is where intent lives and where verification hooks in. Everything downstream (plan, tasks, tests, code) is regenerable from this file; this file is not regenerable from the code.

When intent changes mid-flight, you edit the spec in the same PR as the code. The spec update and the code update land together. That is what "the diff is the contract" means in practice.

---

## 6. The quality gate (three layers, verification-first core)

This is the backbone. The gate is where "fast" becomes "fast and trusted."

**Layer 1: agent self-verification, in-loop, before any human or CI sees it.** The agent is given a machine-checkable pass/fail signal and told to loop until green. Deterministic checks it runs itself: types, lint, unit tests, property tests, build. The agent does not surface work until Layer 1 is green. A progress file with `passing:` flags tracks its own state so a long-running agent does not lose the thread. The human is not the loop here; the compiler and the test runner are.

**Layer 2: CI conformance gates, unwaivable.** Runs on every PR, cannot be clicked past:

- **Spec-drift check:** does the code still satisfy the acceptance-criteria tests named in the spec? Divergence fails the build.
- **Independent reviewer agent:** fresh context, different model from the writer, reviews the diff against the spec. It reports the two or three judgment calls a human should look at, and flags anything that looks plausible-but-wrong (AI's signature failure). It does not rubber-stamp; it produces a short findings list.
- **Property-based tests** for invariants. This is the highest-leverage test type for agent code and agents write them well. Bcengi-specific invariants that belong here: no-negative-price, refill idempotency, companion cost stays under the $0.10/plan and $3/mo caps, round-trip serialization for the module_system bundle, PostGIS geo results are within bounds, Rust core packet-path invariants. These are cheap to assert and expensive to violate silently.
- **Security gate on the two things that actually bite us:** leaked secrets (agent commits leak them at roughly double the human rate, so this is scanned every commit, not reviewed by eye) and poisoned/hallucinated dependencies (slopsquatting: an agent invents a package name, it gets installed, you are owned). Every new dependency must be pinned and must resolve to a package that existed before this PR. New dependency equals red task automatically.

**Layer 3: human judgment, narrow and high-stakes only.** A human looks only when the change is red-classed. And when they look, they do not read every line and nod. They do two things: judge the two or three intent/risk calls the reviewer-agent surfaced, and **run it** (a recorded smoke test on the real path, not a unit stub). The approval-bias danger is real: clean-looking agent diffs invite confident rubber-stamps that carry hidden debt. The defense is that human review is rare, so when it happens it is a genuine run-it-and-judge act, not a scroll-and-approve reflex.

**CODEOWNERS enforces who must look.** The Rust core, payment code, auth, and any `migrations/` directory have named owners whose sign-off CI requires. Igor owns backend money/auth surfaces, Infra owns infra and migrations, the Rust core owner (Dmitry or the assigned lead) owns the telecom path. Everything not under CODEOWNERS merges on green with no human at the end. This is the single lever that keeps the team from either rubber-stamping everything or reviewing everything. Guard the few surfaces that can end you; let the rest flow.

---

## 7. Knowledge and handover with persistent memory

Bcengi already has the thing the rest of the industry is bolting on: file-based AI memory plus a KB. This changes what handover means completely. There is no handover document and no handover meeting. A fresh agent re-hydrates from three places, in this order:

1. **Repo context:** CLAUDE.md (always-true facts), the relevant Skill (the procedure for this kind of task), the spec file, and the code.
2. **Persistent memory / KB:** the memory files and the four memory backends. Before non-trivial work, the agent queries memory for prior art. "Did we solve this before" is a query, not a person you ask.
3. **The spec's `## Notes`:** which specifically points the next agent at the right prior work so it does not have to search blind.

**The discipline that makes this work: memory is written as the last step of Done.** When a unit merges, the agent (or the engineer) writes what was learned: the decision, the gotcha, the non-obvious constraint. Not a transcript, a distilled rule. This is exactly how the existing memory files already work (the deploy gotchas, the zombie-backend runbook, the weather-units rule). We extend that same practice to all dev work. The KB write is unwaivable in the Definition of Done because a merged change with no memory write means the next agent re-learns the same gotcha the hard way.

Context hygiene is a first-class rule: CLAUDE.md stays lean (always-true only), procedures live in Skills, noisy exploration runs in subagents so it never pollutes the main context window. Instruction bloat is treated as a bug.

Onboarding a new engineer (or a new repo, or Misha starting) collapses from weeks to hours, because the agent they drive already knows the codebase from memory plus repo context. The human learns taste and the risky surfaces; the agent supplies the state.

---

## 8. How releases happen

Continuous. Merge to main equals released, or as close as each repo allows. There is no release train, no release meeting, no cut-and-freeze.

- **Green merges deploy automatically** for green-classed changes in the web/CMS, companion, and places repos, because the gate already proved them.
- **Red merges deploy behind the human who signed off**, who is also the person who ran the smoke test. They own watching it land.
- **The Rust telecom core and anything touching PLMN/IPX registration is manual-promote**, always, no matter how green. Some surfaces are irreversible enough that "the gate passed" is necessary but not sufficient. This is deliberate and permanent.
- **Rollback is the release plan.** Every deploy must be revertible in one step. If it cannot be cleanly reverted (a schema migration, a data backfill), it is red by definition and gets a written rollback procedure before it ships.

The failure mode we are defending against is not a bad build. It is silent degradation shipped fast: the Replit-agent-deletes-prod-and-fabricates-users tail. The defense is that the surfaces where that happens (prod data, money, migrations, core) are the exact surfaces that are red-classed, human-gated, smoke-tested, and one-step-revertible. Everywhere else, we let it rip on green.

---

## 9. Artifacts (the complete list, nothing more)

- **`specs/<unit>.md`** - one per unit of work. Why / Acceptance (EARS) / Risk / Notes. The contract.
- **`specs/INDEX.md`** - the living plan and Kanban. Opened Monday, edited anytime. Replaces the tracker.
- **CLAUDE.md** - always-true facts per repo. Lean by rule.
- **Skills** - procedures for recurring task types (add a companion card, ship a CMS locale, run a places ingest). Sometimes-relevant, loaded on demand.
- **Tests** - unit plus property-based, named to match acceptance criteria. The executable spec.
- **CODEOWNERS** - names the humans who must gate the red surfaces. Short list.
- **CI config** - the three-layer gate, unwaivable, no merge-anyway button.
- **Progress file** - per long-running agent, `passing:` flags, so state survives a context reset.
- **Memory files / KB entries** - written at Done. The handover.
- **Jira DEV** - thin auto-generated roll-up, human-facing only, one line per unit. Not in the loop.

That is the entire artifact set. If a proposed artifact is not on this list, the default answer is no.

---

## 10. Roles for a 4-5 person team

Nobody is "the implementer" anymore; everyone is an orchestrator plus an owner of a risky surface. Coding skill is assumed; the differentiator is domain taste and verification rigor.

- **Dmitry (CEO, taste and intent):** writes and approves specs, especially the `## Why` and the acceptance criteria. Owns the "is this the right thing" gate. Runs his own agent fleet. Named CODEOWNER on the Rust core and on strategic/money surfaces. His scarce contribution is deciding what should exist, which is the one thing that does not parallelize.

- **Igor (backend, owns money and auth):** CODEOWNER on payment, auth, and API surfaces. Orchestrates backend agents. Final gate and smoke test on backend red tasks. Guardian of the no-negative-price / idempotency invariants in the property-test suite.

- **Frontend (frontend/mobile):** orchestrates Kotlin mobile and web UI agents. Most of his work is green-classed and merges on the gate. Owns the run-it discipline for user-facing flows (self-test on device before showing, which is already a standing rule).

- **Infra (infra, owns migrations and deploys):** CODEOWNER on `migrations/`, deploy config, and the continuous-release pipeline. Owns the unwaivable-CI setup itself and the rollback-in-one-step rule. When a task is red because it touches infra or data, Infra is the human on the gate.

- **Docs-eng (docs, becomes verification and context steward):** docs are now largely agent-generated, so Docs-eng's higher-leverage job is owning the context layer: keeping CLAUDE.md lean and true, curating Skills, and making sure the memory-write-at-Done discipline actually happens across repos. He is the person who notices when instruction files bloat or when the reviewer-agent is being ignored. In a verification-first shop, the doc owner is the natural owner of "is our context and our gate healthy."

The reviewer is not a person on this list. The reviewer is an agent, fresh context, different model, run in CI. Humans review only what CODEOWNERS forces them to, and when they do, they run it rather than read it.

---

## The one-paragraph version

Generation is free at Bcengi, so we deleted every ceremony that existed to coordinate slow human typing: no points, no velocity, no sprints, no standups, no heavy tickets. In their place is one artifact and one gate. The artifact is a short in-repo spec whose acceptance criteria are written as EARS lines that map one-to-one onto tests. The gate is three layers of machine verification (agent self-check in-loop, unwaivable CI with a different-model reviewer agent and property tests and a secrets/dependency scan, and a narrow human sign-off plus mandatory run-it smoke test on only the red surfaces: money, auth, migrations, the Rust core). Handover is a memory file the next agent reads, written as the last step of Done. Releases are continuous and revertible-in-one-step, with the irreversible surfaces manually promoted no matter how green. We measure only cycle time bolted to rework rate, never individuals, never output volume. Speed is safe because nothing a human sees is unproven, and the few things that can end us are the only things a human is required to look at.
