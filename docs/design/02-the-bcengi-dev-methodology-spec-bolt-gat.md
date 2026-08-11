# The Bcengi Dev Methodology: Spec, Bolt, Gate

A lightweight, AI-native way of building, designed for exactly five people (Frontend, Igor, Infra, Docs-eng, Dmitry) shipping across the companion, mobile, places, core, and CMS repos with Claude Code. The whole thing fits on one page and changes almost nothing about how you already work. It just names the parts, kills the ceremony you already skip, and makes the two things that now matter (the spec and the gate) unwaivable.

---

## Philosophy (why this shape)

Generation is free for you already. Four devs plus a heavily-technical CEO each running fleets of agents produce more diffs than five humans could ever hand-review. So the job is not "write more code," it is "decide what should exist, then trust it without babysitting every line." Every practice below exists to protect the two scarce things: **taste** (deciding what to build, non-delegable, mostly Dmitry) and **verification** (proving it works, machine-runnable, so no human is the loop). Everything that existed only to coordinate slow human hands gets deleted, not recalibrated.

You are the profile that wins at this, because you already solved the hard part: persistent file memory + KB + per-repo CLAUDE.md means context already travels as files. You do not need to bolt on what the rest of the industry is scrambling for. You need to stop running a heavy tracker on top of it.

---

## Principles (the seven that decide arguments)

1. **The spec is the unit of work, not the ticket.** A short markdown file in the repo, next to the code, that the agent can read, edit, and diff. Jira stops being where work lives.
2. **The diff is the contract.** Backlog grooming, ticket updates, and status are edits to files in a PR, never a separate ceremony or a system the agent cannot see.
3. **Verify by construction, not by approval.** Code reaches a human only after it has passed machine gates the agent ran itself. Humans review the 2-3 judgment calls, never every line.
4. **The writer is blind to its own bugs.** The agent that reviews is a fresh context (and where it matters, a different model) than the one that wrote the code.
5. **Handover is a file, not a meeting.** A fresh agent rehydrates from memory + KB + the repo. Nobody explains state to anybody.
6. **Estimate nothing. Measure cycle time and rework.** Story points, velocity, burndown are deleted. Done/not-done plus how long it took plus did-it-come-back.
7. **Spec-before-code only where it bites: money, auth, schema, the telecom core, and PRICES.** Everywhere else, spec-anchored is enough. Do not go waterfall-purist.

---

## Roles (five people, no new hires, no army)

- **Dmitry = Chief Decomposer + Taste.** Owns the one act that does not automate: cutting the work into specs and deciding what should exist and in what order. Runs the Monday INDEX pass. Final human gate on money, auth, and core changes. Also just another agent-operator on his own repos.
- **Frontend = owner, web/CMS + mobile frontend.** CODEOWNER on those surfaces.
- **Igor = owner, Django companion + data/schema.** CODEOWNER on migrations and money paths (Stripe, loyalty points). Schema migrations are human-led by him, per the DB-default-for-live-migrations rule.
- **Infra = owner, infra + CI gates + the Rust telecom core surface.** Owns the gate definitions themselves. Core changes are human-led.
- **Docs-eng = owner, docs + specs hygiene + KB/Confluence sync.** Not "the doc guy who writes prose after the fact." He owns that specs stay honest, the INDEX is current, and shipped changes land in the KB. This is now a first-class engineering role because handover IS the docs.

"Owner" means CODEOWNERS on that surface and the human who runs the reviewer pass on PRs touching it. Everyone operates agent fleets across any repo; ownership is about who holds the gate, not who is allowed to touch the code.

---

## The working loop (per change, hours to days, never two weeks)

This replaces the sprint. One change flows through five steps. Call the whole cycle a **Bolt** (an hours-to-days unit of work, not a two-week fiction).

**1. Spec.** Owner or Dmitry writes or updates a spec file: `specs/NNN-short-name.md`. Minimum viable spec is four short sections:
   - **Intent** (2-4 sentences: what and why).
   - **Acceptance criteria** in EARS, one testable line each: `WHEN <condition> THE SYSTEM SHALL <behavior>`. Each line maps one-to-one onto a test.
   - **Out of scope** (kills agent scope-creep).
   - **Risk flags**: does this touch money / auth / schema / core / PRICES? If yes, it needs a human plan gate before code.

   For a small change the spec is 15 lines. Do not gold-plate it.

**2. Plan (gate 1, human, only for risk-flagged work).** For anything touching the five risky surfaces, the agent produces a short plan and the owner approves it before a line is written. For everything else, skip straight to Bolt. This is the only planning ceremony that survives, and it is a 5-minute read of a plan file, not a meeting.

**3. Bolt.** The operator points one or more agents at the spec in a git worktree. Agents implement against the acceptance criteria. Ceiling is 4-8 concurrent agents per person, set by your own review capacity, not the tooling. Agents write the tests the acceptance criteria imply, including property tests for invariants (see gate).

**4. Gate (the quality backbone, mostly machine).** The agent must go green on the three-layer verify loop below before any human looks. A red gate never reaches a human.

**5. Merge + close.** Owner runs the thin human slice (reviewer pass), merges to main, and the spec's INDEX line flips to done. Release is continuous (below). Memory/KB updated if new durable context was learned.

There is no standup. Status is the INDEX file and the PR queue, both of which the agents and humans can already see. Moving context between humans across time is what your persistent memory is for.

---

## What replaces sprint planning: the Monday INDEX pass

Once a week, Monday morning, Dmitry (with Docs-eng) opens **one file per repo: `specs/INDEX.md`.** That file IS the project plan. It is a flat list:

```
## Companion specs
- [ ] 041-detail-latency-duffel   Igor    risk:none    (round-2 open)
- [x] 038-mark-booked             Igor    risk:money   shipped 07-10
- [>] 044-multi-trip-reorder      Frontend risk:none    in bolt
```

The pass is 20 minutes across all repos: what shipped, what is stuck, what are this week's 3-6 most-important Bolts, what got reprioritized. Reprioritization is editing this file in a PR, not a grooming meeting. That is the entire "planning" apparatus. No pointing, no capacity math, no commitment to a two-week batch.

Jira DEV survives only as the **human-facing what/why/priority ledger** for cross-repo initiatives and anything a non-dev needs to see (a fundraise-linked feature, a compliance item). It is a thin roll-up, never the agent's inner loop, and you stop writing granular implementation tickets in it entirely. The heavy feel goes away the day you stop pretending Jira is where work happens.

---

## Minimal tracking + Definition of Done

**Tracking = three artifacts, all in-repo, all diffable:**
- `specs/INDEX.md` per repo (the live plan).
- The PR queue (`gh pr list`) is the WIP board. WIP limit is your agent-review ceiling; if PRs are piling unreviewed, stop starting Bolts.
- Two metrics only, measured on the system and never on a person: **cycle time** (spec opened -> merged) and **rework rate** (did a shipped change come back for a fix within N days). Any metric that rises when you generate more code (LOC, PR count, commits) is banned from the wall because it now lies.

**Definition of Done is a single standing gate, identical for every Bolt:**
> A Bolt is done when (1) its EARS acceptance criteria all have passing tests, (2) the standing CI gate is green, (3) a fresh-context reviewer pass ran, (4) someone actually ran the thing once (the smoke), and (5) any new durable context was written to memory/KB.

Acceptance criteria are per-Bolt and live in the spec. Definition of Done is standing and lives once, in `DEFINITION_OF_DONE.md` at each repo root (or in CLAUDE.md). Never negotiated per-Bolt.

---

## How specs and intent are captured

- **One file, in the repo, next to the code**: `specs/NNN-name.md`. Version-controlled, so intent evolves with the code (spec-anchored, not spec-as-source). Never regenerate the whole codebase from the spec; let tests enforce alignment.
- **EARS for every acceptance line.** `WHEN the trip has no next action THE SYSTEM SHALL render the discovery hero.` One line, one test. This is the human's real authored artifact now, so this is where care goes, not into the code.
- **For risk-flagged work, the plan file is captured too** and lives beside the spec until merge, then is deleted or folded into the spec.
- **CLAUDE.md / AGENTS.md stay lean.** CLAUDE.md holds always-true facts (the six gates, deploy gotchas, service ports). Procedural sometimes-relevant workflows go in Skills/playbooks, not always-loaded. Instruction bloat measurably degrades agent attention, so Docs-eng prunes CLAUDE.md as ruthlessly as he prunes dead code. Rule: if a fact is not true 90% of the time an agent reads the file, it does not belong in CLAUDE.md.

---

## The quality gate: how AI work is verified (three layers)

This is the load-bearing half of the method. Generation speed only becomes shipped-and-trusted speed if the gate converts it. Without this, pointing more agents at more repos ships less, not more.

**Layer 1 - deterministic, agent-runs-it-in-loop (the agent must pass these before claiming done):**
- Types + lint + build + unit tests, per repo:
  - Companion (Django): `ruff`, `mypy`, `pytest`.
  - Mobile (Kotlin): `./gradlew :app:assembleDebug -x lint`, `ktlint`, unit tests. Install only on build success.
  - Places (PostGIS): test suite + the **500ms query-budget assertion** as a hard test, not a guideline.
  - Core (Rust): `cargo test`, `cargo clippy -D warnings` across the crates.
  - Web/CMS: build + lint.
- **Property tests on invariants** (highest-leverage test type for AI code, and agents write them well). Assert the things that are expensive to violate: no-negative-price, cost cap (`<$0.10/plan`, `$3/mo` ceiling), loyalty `100 pts = $1` pinned, round-trip serialization, monotonic pagination. Example-based + property-based together catch far more than either alone.

**Layer 2 - conformance, in CI (GitHub Actions, since you already live on `gh`):**
- **Independent reviewer pass by a fresh-context agent, ideally a different model** than the writer. Its job is to find bugs and spec-drift, not to approve. Output is a findings list, not a thumbs-up.
- **Spec-drift check**: does the diff still satisfy the EARS lines? Flag divergence.
- **Security, the two categories that actually bite:**
  - **Secret scanning** (gitleaks) on every commit. Claude-assisted commits leak secrets at ~2x baseline, so this is a gate, not a habit.
  - **Slopsquatting guard**: any newly-added dependency must be verified to exist and be the real package before install (hallucinated package names are stable enough to be weaponized). New dependency = automatic human flag.

**Layer 3 - human, the thin top slice (narrow and high-stakes, to defeat rubber-stamping):**
- The owner reviews only the judgment calls and only the risky surfaces: money, auth, schema migrations, the Rust core, PRICES. `CODEOWNERS` enforces that these paths cannot merge without the owner.
- **A mandatory run-it smoke** on anything touching those surfaces. Clean-looking agent diffs draw *higher* false confidence, so "I read it and it looks right" is banned as sign-off on risky paths. You ran it, or it did not ship. (This is the Replit-deleted-the-prod-DB lesson: the fix is a run-it check on the few irreversible surfaces, not broad human review everywhere.)
- Everywhere else, the human trusts the gate and merges. Broad line-by-line human review is deleted; it degrades into rubber-stamping and is worse than no review.

Gates are **unwaivable in CI.** No green, no merge, no exceptions, including for "small" changes. Infra owns the gate definitions; changing a gate is itself a spec.

---

## Knowledge and handover (you already have the hard part)

Handover is not a document you write and not a meeting you hold. It is the state that already persists:
- **In-repo**: the spec, the INDEX, CLAUDE.md, the tests. A fresh agent on a cold repo rehydrates from these in minutes.
- **Cross-session / cross-repo**: the four memory backends and the KB. When a Bolt teaches something durable (a deploy gotcha, a decision, a rejected approach), the operator writes it to memory in real time, before moving on, and Docs-eng ensures the KB/Confluence sync ran.

Concretely, onboarding a new agent or a new person collapses to: point them at the repo's CLAUDE.md + `specs/INDEX.md`, and let the memory search answer "have we done this before." No handover meeting exists because the function of handover (context traveling across time and people) is served by files that both humans and agents read. The retro does not survive as a meeting either; its function survives as the real-time memory write. If a Bolt went sideways, the lesson is a memory file, not a calendar event.

---

## How releases happen

- **Continuous, per-repo, trunk-based.** Merge to main behind the green gate is the release for services (companion, places, core, CMS). No release train, no cutting a sprint.
- **Push by default**, mobile is merge-first, matching your existing default. The gate makes this safe.
- **Deploy is boring and codified** in CLAUDE.md per repo (the tripdesk bind-mount + `flush_provider_cache`, the places `--force-recreate`, the zombie-backend recovery). Deploy gotchas are always-true facts, so they live in CLAUDE.md, and the agent follows them. Never deploy mid-device-test.
- **Irreversible actions** (schema migration, PRICES publish via webflow-ops only, money-path changes) are the only releases that get a human hand on the lever plus the smoke run.

---

## Artifact catalog (the complete list, nothing else)

| Artifact | Where | Owner | Purpose |
|---|---|---|---|
| `specs/NNN-name.md` | in repo | whoever opens the Bolt | intent + EARS acceptance + scope + risk flags |
| `specs/INDEX.md` | in repo | Docs-eng keeps current | the live plan, read every Monday |
| plan file (risk-flagged only) | beside spec | owner | human gate 1 before code |
| `DEFINITION_OF_DONE.md` | repo root | Infra | the one standing gate |
| `CLAUDE.md` / `AGENTS.md` | repo root | Docs-eng prunes | always-true facts, kept lean |
| CI gate config | `.github/workflows` | Infra | the three-layer verify, unwaivable |
| `CODEOWNERS` | repo root | Infra | forces owner review on risky paths |
| PR queue (`gh pr list`) | GitHub | everyone | the WIP board |
| memory + KB | file memory / Confluence | operator writes, Docs-eng syncs | handover, decisions, gotchas |
| Jira DEV | Jira | Dmitry | thin cross-repo what/why ledger only |

Ten artifacts, eight of which live in the repo. No dashboard, no burndown, no sprint board.

---

## What you stop doing (delete, do not recalibrate)

- Story points, velocity, burndown. Deleted.
- Two-week sprints and sprint planning. Replaced by the Monday INDEX pass.
- Standups and status sync. Replaced by INDEX + PR queue + memory.
- Granular Jira implementation tickets. Replaced by spec files.
- Backlog grooming meetings. Replaced by editing INDEX in a PR.
- Line-by-line human review on everything. Replaced by machine gates + thin owner slice on risky paths only.
- Retro as a meeting. Replaced by real-time memory writes.
- Any enterprise agentic-SDLC org chart (GitHub's 5 roles, Atlassian Rovo stages, AO-DLC). Ignored entirely; you are five people, not a program office.

---

## The one-week adoption plan (least change, start Monday)

- **Mon:** Dmitry + Docs-eng create `specs/` + `specs/INDEX.md` in the two hottest repos (companion, mobile). Backfill the current open work as INDEX lines. Run the first 20-minute INDEX pass.
- **Tue:** Infra writes the Layer-1 CI gate for those two repos (the commands already exist; wire them into GitHub Actions as required checks). Add gitleaks. Add `CODEOWNERS` for money/auth/schema/core/PRICES paths.
- **Wed:** Add the fresh-context reviewer pass (Layer 2) as a CI job using a different model than the typical writer. Add the new-dependency flag.
- **Thu:** Write `DEFINITION_OF_DONE.md`, prune each `CLAUDE.md` to always-true facts, move procedural stuff to Skills/playbooks.
- **Fri:** Run one full Bolt end-to-end under the method (spec -> gate -> merge) on a real change. Fix what felt heavy. Roll the same setup to places, core, CMS the following week.

Nothing here asks you to adopt a tool you do not have, hire anyone, or add a meeting. It names what you already do, deletes the tracker ceremony you already resent, and makes the spec and the gate the two things nobody is allowed to skip.
