# FLOW: The Bcengi Development Methodology

A radical-minimalist, AI-native way to build. One sentence: the repo is the tracker, the spec file is the ticket, the CI gate is the reviewer, and persistent memory is the handover, so there is nothing left to run a meeting about. Nobody manages the process because there is almost no process to manage.

---

## 0. The single premise

Generation is free at Bcengi. Every one of you drives a fleet of Claude Code agents across companion, mobile, places, core, and CMS. So the constraint is never "can we write it" - it is "did we decide the right thing, and can we prove it works before it ships." FLOW spends zero effort coordinating execution and all of its (small) effort on deciding and verifying. If a practice exists to move code faster, delete it. If a practice exists to catch silently-wrong code, make it unwaivable.

---

## 1. Principles (the whole constitution)

1. **The repo is the system of record.** State that an agent cannot read, diff, or edit does not exist. Anything a fresh agent needs must live in the repo (spec, plan, CLAUDE.md, tests) or in memory/KB. Jira DEV is demoted to a wall, not a workflow.
2. **Pull, never push.** No sprints, no assignments, no capacity planning. Work sits in one ranked list; whoever is free pulls the top item they own. The only scheduling primitive is a WIP limit.
3. **The spec is the unit of work, not the ticket.** For anything non-trivial you author a short in-repo spec with executable acceptance criteria before an agent writes code. The diff is the contract.
4. **Verify by construction, not by inspection.** The agent must pass a machine-checkable gate before a human looks. Humans review judgment calls (2-3 per change), never every line.
5. **Estimation is banned.** No points, no velocity, no "how long." The only time signal is cycle time (pull to merge), watched at the system level, never per person.
6. **Context is the scarce resource.** Keep CLAUDE.md lean and always-true. Push procedural knowledge into skills and playbooks that load on demand. A bloated instruction file is a bug.
7. **Taste and decomposition stay human.** Deciding what should exist and cutting it into safe pieces is the one planning act that survives. Everything downstream is delegated.
8. **Risk gates, not blanket gates.** Money, auth, prod DB, schema migrations, the Rust core, and PRICES/MVNE CMS are the only surfaces that get mandatory human sign-off. Everything else flows on green CI.

---

## 2. The working loop (the entire cadence)

There is one loop, run continuously by each person, at their own pace. No standup, no sprint boundary, no planning meeting.

**PULL -> SPEC -> DELEGATE -> VERIFY -> LAND -> REMEMBER**

- **PULL.** Open `NOW.md` at the repo root (the ranked list, section 4). Take the top unclaimed item on your surface. Put your initials next to it. That is the entire act of "assignment." WIP limit: max 2 items in-flight per person, because your ceiling is your own review capacity, not the agents'.
- **SPEC.** If the item is trivial (copy tweak, config, obvious bugfix), skip to DELEGATE. Otherwise write or update a spec file (section 5). This is the real work and the only writing that must be human-authored.
- **DELEGATE.** Point one or more Claude Code agents at the spec in isolated git worktrees. Run 2-6 in parallel across items; the number is bounded by how many diffs you can actually verify today, not by the tooling.
- **VERIFY.** The agent runs the in-loop gate itself (types, lint, unit + property tests, build, smoke run) and does not return until green. Then a fresh-context reviewer agent (different session, ideally different model) reviews the diff against the spec. Then you spend five minutes on the judgment calls it surfaces. See section 6.
- **LAND.** Merge to the trunk on green. Small changes ship straight through. Risk-surface changes wait on the one human sign-off. See section 8.
- **REMEMBER.** If the work produced a decision, a gotcha, a corrected assumption, or a "we tried X and it broke," write it to memory/KB immediately (section 7). This replaces the retro and the handover doc. If it produced nothing durable, write nothing.

The loop has no fixed tempo. Docs-eng can land four doc PRs before lunch; Infra can spend three days on a single PLMN-registration item. Neither event needs a ceremony, a re-plan, or a status update, because `NOW.md`, the open PRs, and the memory writes already say everything a standup would.

---

## 3. What replaces sprint planning

Nothing recurring. There is no planning meeting. Planning is two continuous activities:

**A. Ranking (async, whenever).** Dmitry (and anyone with context) keeps `NOW.md` ordered. Reordering a list is a 30-second edit in a PR, not an event. The top of the list is "pull this next"; the bottom is "someday." That is the whole backlog. Priority lives in list order, not in a priority field.

**B. Decomposition-on-demand (the one real planning act).** When a big thing lands on the list (fundraise-blocking model work, CoreConnect IPX integration, a mobile module-system change), the owner of that surface cuts it into pull-sized pieces by writing specs, right before it gets worked, not months ahead. Decomposition is the part you cannot delegate, so it is done just-in-time by the human who owns the surface, in the spec files themselves. No grooming session, no estimation, no epic hierarchy. If a piece is too big to verify in one sitting, it is too big; split it.

The quarterly-ish "what are we even doing" conversation still happens, but it is a conversation Dmitry starts when strategy shifts, not a calendar ritual. Its output is a reordered `NOW.md`, nothing else.

---

## 4. Minimal-but-sufficient tracking

**One file per repo: `NOW.md` at the root.** It is the project plan, the backlog, and the board, and it is the thing you open first every working session. Format:

```
# NOW - companion

## In flight (WIP<=2 per person)
- [AR] disc-card-detail-latency  spec: specs/disc-detail-latency.md  PR #412
- [IG] mark-booked-idempotency   spec: specs/mark-booked.md          PR #414

## Next (pull from the top)
- weather-units-device-locale    spec: specs/weather-units.md
- viator-add-to-trip-retry
- eat-photo-rank-fallback

## Someday
- shopping-list-affiliate (PARKED by Dmitry 2026-07-12, do not build)
```

That is the entire tracking system. No Jira board for dev flow. Jira DEV survives only as the human-facing "what and why" ledger for cross-functional items (a deal needs a feature, a patent needs a diagram) and for anything Dmitry wants to see rolled up outside the repos. It is never in an agent's inner loop and it is never the source of truth for dev state. Rule: if updating Jira and updating `NOW.md` ever disagree, `NOW.md` wins and Jira is wrong.

**Cross-repo view.** Because Bcengi spans five-plus repos, there is one top-level `NOW.md` in a small `bcengi-flow` repo that links each repo's `NOW.md` and lists only the handful of items that cross repo boundaries (mobile change that needs a companion API, CMS change that needs a places field). This is the closest thing to a company board, and it is a single readable file.

**Cycle time is the only metric.** A trivial CI job stamps pull-time (initials added) and merge-time, and reports median cycle time per repo weekly. Watch it move; never attribute it to a person. Pair it with **rework rate** (share of merges reverted or patched within 7 days) so speed cannot hide silent breakage. Any metric that rises when you generate more code (LOC, PR count, commits) is banned from every dashboard because it is now actively misleading.

**Definition of Done (one standing gate, identical everywhere):**
A change is done when, and only when:
1. Its acceptance criteria (in its spec) are met.
2. The in-loop gate is green: types, lint, unit + property tests, build.
3. A fresh-context reviewer agent has reviewed the diff against the spec and its findings are resolved.
4. It has been run once for real (smoke), not just tested. Proven to work, not assumed.
5. Any durable lesson is written to memory/KB.
6. For a risk surface only: the named human has signed off.

Steps 1-5 are unwaivable and mostly enforced by hooks/CI, not by discipline. Step 6 applies to the short list in section 8.

---

## 5. How specs and intent are captured

**Specs live in `specs/` in the same repo as the code, versioned with it.** One markdown file per unit of work. They evolve with the code (spec-anchored, not spec-as-only-source; we never regenerate whole services from a spec, and we never let the spec rot behind the code). A spec is short. Template:

```
# Spec: mark-booked idempotency

## Intent (1-3 sentences, human-authored)
Marking a discovery item as booked must be safe to retry. A double-tap
or a client retry must not create two bookings or double-count points.

## Acceptance criteria (EARS, one testable line each)
- WHEN a mark-booked request arrives for an item already booked by the
  same user THE SYSTEM SHALL return the existing booking and SHALL NOT
  create a second record.
- WHEN two mark-booked requests for the same item arrive concurrently
  THE SYSTEM SHALL persist exactly one booking.
- WHEN points are awarded for a booking THE SYSTEM SHALL award them at
  most once per booking.

## Out of scope
Refund/unbook flow. Cross-trip dedupe.

## Notes / risk
Touches points ledger -> money-adjacent. Needs Igor sign-off.
```

**EARS syntax is mandatory** ("WHEN [condition] THE SYSTEM SHALL [behavior]") because each line maps one-to-one onto a test. If a criterion cannot become a test, it is not a criterion, it is a wish; rewrite it.

**Intent capture is cheap and continuous.** When Dmitry describes a feature over Telegram or in a session, the agent drafts the spec from that transcript and opens it as a PR. The human edits the intent and the criteria. We do not transcribe requirements into a ticket and then re-explain them to an agent; the spec IS the requirement, authored once, read by every agent thereafter. This is the "we never created a ticket again" discipline: the conversation becomes a spec file, full stop.

**Trivial work needs no spec.** A spec that says less than the diff would is waste. Copy tweaks, dependency bumps, config, obvious one-line fixes go straight to DELEGATE with a one-line PR description. The judgment "does this need a spec" is itself a taste call and stays human; the default is "no spec unless it touches behavior, money, auth, data shape, or a core system."

---

## 6. The quality gate (how AI work is verified and reviewed)

Three layers, and the human is deliberately the thinnest one. This is the backbone; everything else in FLOW is allowed to be loose because this is not.

**Layer 1 - in-loop, the agent checks itself.** Before the writing agent returns anything, it must run and pass, on its own: type check, lint, unit tests, property tests, build, and a smoke run of the actual path it changed. The agent does not present work to a human until this is green. Enforced by the agent's harness and by a pre-PR hook, not by hope.

- **Property-based tests are first-class here, not optional.** They are the highest-leverage test type for agent-written code and agents write them well. Assert invariants the domain cannot violate: no negative price, companion plan cost stays under the hard $0.10 cap, points award at most once, a country-code round-trips, monotonic usage counters, refill math conserves balance. These catch the plausible-but-wrong output that example tests miss.

**Layer 2 - conformance, in CI, agent-driven.** On every PR:
- **Fresh-context reviewer agent.** A separate Claude Code session with no memory of writing the code reviews the diff against its spec. Different model where practical, because the author is blind to its own bugs. It reports: spec drift, missing criteria, risky calls. This is the canonical writer/reviewer split and it is mandatory.
- **Spec-drift check.** If code in a spec's area changed but the spec did not (or vice versa), CI flags it. Specs and code move together or the build complains.
- **Security gates on the two things that actually bite us:** a secret scanner (agent commits leak secrets at roughly double the human rate, so this is non-negotiable across companion, core, and every `.env`-adjacent repo) and a dependency check that fails on any package name not already in the lockfile, to kill slopsquatting (hallucinated package names are stable enough to be weaponized; the Rust core and Django services are the exposed surfaces).
- **Evals for probabilistic behavior.** Companion/tripdesk changes that alter model behavior run against a small saved eval set (real prompts, expected shape) so we catch regressions in the parts unit tests cannot pin.

**Layer 3 - human, the thin top slice.** You read the reviewer agent's 2-3 judgment calls and the diff's intent, not every line. Your job is intent, risk, and irreversibility, and one thing a machine cannot do: confirm it was actually run. Simon Willison's rule is house law: you ship code you have proven to work, with a manual proof and a bundled automated test, because a computer can never be held accountable for a bug and you can.

**The named danger: approval bias.** Clean-looking agent diffs draw higher-confidence approvals while carrying more hidden debt, and "human in the loop" quietly rots into rubber-stamping. FLOW fights this structurally, not with willpower: broad human review is removed entirely (so there is no rubber stamp to give), and human attention is concentrated only on the narrow risk surfaces in section 8, each of which requires the mandatory run-it smoke plus a written one-line "I ran X and saw Y." No "LGTM" on a money or auth or core change without that line.

---

## 7. Knowledge and handover (given persistent memory)

Handover is not a document and never a meeting. It is a file the next agent reads. Bcengi already has the two things the rest of the industry is bolting on: file-based AI memory and a knowledge base. FLOW leans on them as the primary continuity mechanism.

- **CLAUDE.md per repo = always-true facts.** Architecture, invariants, the hard rules (no em-dashes, spend gate, PRICES hands-off, right-architecture), how to run the gate. Kept lean; anything sometimes-relevant is moved out. Bloat here degrades every agent's attention, so pruning CLAUDE.md is real maintenance work, done whenever it grows a section that is not always true.
- **Skills / playbooks = procedural, load-on-demand.** The recurring workflows (deploy the companion with the bind-mount-goes-stale dance, recover the zombie backend, regen the deck, publish CMS locales) live as skills that load only when triggered, keeping the always-loaded context small.
- **Memory + KB = the durable lessons and decisions.** The REMEMBER step writes here. This is where "we tried real-MSISDN-via-Mvne and Dmitry rejected it as bs" or "recreate wipes container pytest" lives, so the next agent (or the next person) re-hydrates state instead of asking a human. Onboarding Misha, or spinning a fresh agent on a cold repo, is hours not weeks because the context is queryable, not tribal.

**This is what replaces the retro.** The counterweight research is clear that killing the retro's function tanks quality over a few cycles even though killing its ritual form is fine. So FLOW keeps the function and drops the meeting: every durable lesson becomes a memory/KB write or a CLAUDE.md/spec edit that travels to the next agent automatically. The retrospective happens continuously, one lesson at a time, as an artifact, not quarterly as a conversation people forget.

**One rule to keep memory trustworthy:** memory is queried fresh every time before a non-trivial change, never assumed from recall. A lesson that is not written is a lesson that did not happen.

---

## 8. Releases

Trunk-based and continuous. There is no release train and no release meeting.

- **Merge to trunk on green** (DoD steps 1-5). Small and medium changes deploy on merge via CI to the relevant service.
- **Feature flags over long branches.** In-progress behavior ships dark behind a flag rather than living on a branch for days. This keeps the trunk always-releasable and keeps agents working against real integrated code, not a stale fork.
- **The risk surfaces that require one named human sign-off before deploy** (CODEOWNERS on exactly these paths, nothing else):
  - Money: Stripe paths, pricing, points ledger, refill math -> Igor + spend-gate rules where a cost decision is involved.
  - Auth and the companion gateway / IDOR surface -> Igor/Infra.
  - Schema migrations and anything touching prod DB -> owner of that DB.
  - The Rust telecom core (PLMN, IPX, data plane) -> Infra, always human-led, never fully delegated.
  - PRICES / MVNE_PRICES CMS -> untouched by dev flow entirely; webflow-ops is the sole writer, hard rule.
- **The Replit lesson is wired in, not trusted to people.** An agent must never hold the only key to an irreversible prod action. Prod DB writes and destructive infra run through a path that requires the human smoke-and-signoff line, and agents run against copies/staging for anything destructive. Fast shipping everywhere else earns us the room to be slow and paranoid on exactly these five surfaces.
- **Rollback is the norm, not an incident.** Because changes are small and flagged, reverting is a flag flip or a one-commit revert. Rework rate tracks how often this happens; a rising number is the signal to tighten a gate, never to add a meeting.

---

## 9. Artifacts (the complete list)

That is all of them. If an artifact is not on this list, FLOW does not have it.

- `NOW.md` per repo (ranked pull list = board + backlog + plan).
- Top-level `bcengi-flow/NOW.md` (cross-repo items only).
- `specs/*.md` per repo (intent + EARS acceptance criteria; the unit of work).
- `CLAUDE.md` per repo (always-true facts + the hard rules + how to run the gate).
- Skills / playbooks (procedural, load-on-demand).
- Memory + KB (durable decisions and lessons; the handover medium).
- The test suite, especially property tests (executable acceptance criteria).
- CI config (the gate: in-loop checks, reviewer agent, spec-drift, secret + dependency scans, evals).
- CODEOWNERS (only the five risk surfaces).
- PRs (the diff is the contract; the reviewer agent's report rides along).

Deleted on purpose: story points, velocity charts, burndown, sprint boards, the Jira dev workflow, standups, sprint planning, grooming sessions, retros-as-meetings, estimation, handover docs, status reports.

---

## 10. Roles for the 4-5 person team

Roles are surface ownership, not process positions. Each person owns a surface, keeps its `NOW.md` ranked (with Dmitry), authors specs for non-trivial work on it, drives the agent fleet, and is the named sign-off for that surface's risk paths.

- **Dmitry (CEO, taste and priority).** Owns ranking across all `NOW.md` files and the cross-repo list. Authors intent for strategic work. Makes the taste calls: what should exist, what is parked (shopping-list affiliate stays parked until he says otherwise), what is out of scope. Because he codes heavily in Claude Code himself, he also pulls and ships like anyone else. He is not a process manager; there is no process to manage.
- **Igor (backend).** Owns companion Django + APIs + data. Named sign-off for money and auth surfaces. Authors specs for anything touching the points ledger, Stripe, gateway/IDOR.
- **Frontend (frontend / mobile Kotlin).** Owns mobile and web UI. Authors specs for behavior changes; drives agents on the module-system and companion home surfaces. Runs the on-device smoke that no CI can replace.
- **Infra (infra + Rust core).** Owns deploy, CI, and the telecom core. Guardian of the gate itself (keeps the three verification layers honest). Named sign-off for migrations, prod DB, and the Rust core, which stays human-led by rule.
- **Docs-eng (docs).** Owns that specs, CLAUDE.md files, and KB stay lean and true. This is a first-class role here, not overhead: in a memory-native team the quality of the context files IS the onboarding speed and the agent output quality. Docs-eng prunes CLAUDE.md bloat, curates the KB, and makes sure every REMEMBER write is findable.

No CoS-for-process, no scrum master, no release manager, no reviewer role (the reviewer is an agent). The 4-5 people decide, decompose, and verify. The agents do the rest.

---

## 11. Failure modes this design is built to prevent

- **Silent degradation shipped fast** -> unwaivable CI gate + property tests + rework-rate watch. You cannot merge red, and churn shows up in a week.
- **Diffused accountability** -> CODEOWNERS on the five risk surfaces + the mandatory "I ran X, saw Y" line. Someone named is accountable for every dangerous change.
- **Rubber-stamping** -> broad human review deleted so there is no stamp; attention concentrated only where it is irreversible.
- **Context rot** -> Docs-eng's role + lean CLAUDE.md + load-on-demand skills. The scarce resource is protected.
- **Waterfall-by-spec** -> spec-anchored, never spec-as-only-source; specs and code move together, enforced by the spec-drift check; we never regenerate whole services from a document.
- **Faster-feels-but-ships-less** -> the whole point of the verify backbone is to convert free generation into shipped-and-trusted, measured by cycle time bolted to rework rate, never by output volume.

The bet: a small team already living inside agents with persistent memory is the exact profile that wins under these conditions, because the context and handover problem the rest of the industry is scrambling to solve is one Bcengi has already solved. FLOW just removes everything that was in the way of that advantage.
