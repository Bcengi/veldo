# The AI-Native Software Development Landscape

A synthesis of 14 research briefings on how software development changes when agents write most of the code. The through-line: generation went to near-zero cost, so every practice that existed to coordinate slow human execution is dying, and every practice that exists to decide, specify, and verify is intensifying. What follows is the shape of that shift, opinionated and concrete.

---

## 1. What is genuinely changing (the load-bearing shifts)

**The bottleneck moved from writing to verifying, and this is the single fact everything else follows from.** The hard data is now consistent across independent studies. Faros AI's telemetry across 10,000+ developers found high-AI-adoption teams merge 98% more PRs and complete 21% more tasks, but PR review time rose 91%, PR size rose 154%, and none of the team-level gains aggregated to company-level gains because downstream review/CI/release absorbed them (Faros AI, "The AI Productivity Paradox," faros.ai/blog/ai-software-engineering). DORA 2025 added a fifth metric, "rework rate," specifically to catch AI's failure signature: plausible-but-wrong code that ships then needs patching (Swarmia, "What the 2025 DORA report tells us about AI readiness"). The reframe is total: code generation is free, and the scarce artifacts are now the specification, the acceptance criteria, and reviewer attention.

**The unit of work is becoming the spec, not the ticket.** This is the most repeated claim in the entire corpus. An executable, version-controlled spec living in the repo is replacing the tracker ticket as the durable object. The industry converged on one flow regardless of tool: Spec -> Plan -> Tasks -> Implement, with a human gate between phases (GitHub Spec Kit, github.blog "Spec-driven development with AI"; AWS Kiro, kiro.dev/docs/specs; OpenSpec, github.com/Fission-AI/OpenSpec). The sharpest practitioner version: Evgeni Rusev's team "updated the specs from the transcript, and we never created a Jira ticket again" (evgenirusev.com/posts/spec-driven-development-guide).

**The engineer's role shifts from implementer to orchestrator.** Anthropic's own 400k-session study and its 2026 Agentic Coding Trends Report quantify it: humans make ~70% of planning decisions but only ~20% of execution decisions; developers use AI in ~60% of work but can fully delegate only 0-20% of tasks (anthropic.com/research/claude-code-expertise; resources.anthropic.com/hubfs/2026 Agentic Coding Trends Report.pdf). Every engineer now runs a fleet of agents in parallel git worktrees, and the reliable ceiling (4-8 concurrent per person) is set by human review capacity, not by tooling.

**Handover stopped being a document or a meeting and became a file.** Context now lives where the work lives: in-repo instruction files (AGENTS.md / CLAUDE.md), docs moved next to code, and persistent memory. AGENTS.md is now a real standard, not a fad: OpenAI-originated Aug 2025, moved to the Linux Foundation's Agentic AI Foundation, 60,000+ repos, read by 30+ tools (agents.md; morphllm.com/agents-md-guide). Onboarding collapses from weeks to hours because a fresh agent re-hydrates from memory + repo context rather than a person explaining state.

**Domain expertise, not coding skill, became the differentiator.** Anthropic's data: experts trigger 12-action chains vs 5 for novices and verify success at roughly double the rate. And "taste" (deciding what should exist) is the scarce, non-parallelizable skill (Cat Wu, Head of Product Claude Code: "taste is the scarce skill"; Towards Data Science, "Code Is Cheap. Engineering Judgement Is Now the Scarce Resource").

---

## 2. What dies or goes lightweight

These are the clearest casualties. The consensus is not "agile is dead," it is that ceremonies built to coordinate slow human execution have no job left to do.

**Story points and velocity: dead, not recalibrated.** AI execution time bears no relation to human effort estimates, and velocity fluctuates on tool usage rather than capability (specs.md/methodology/sdlc-reimagined). Any metric that rises when you generate more code (LOC, commits, PRs/week, burndown) is now actively misleading. Do not try to fix estimation, delete it. Replace with binary done/not-done plus cycle time.

**Sprints: replaced by continuous flow.** Task completion time became too variable for two-week commitments to be anything but fiction. AWS's AI-DLC replaces sprints with "Bolts" (hours-to-days work cycles) and epics with "Units of Work" (aws.amazon.com/blogs/devops/ai-driven-development-life-cycle). Continuous Kanban with WIP limits is the successor.

**Detailed tickets and the heavy tracker: demoted to a thin roll-up.** The tracker loses because its state lives in a system the agent cannot see, edit, or diff. The replacement that recurs everywhere: a `specs/` folder plus a `specs/INDEX.md` that is literally the project plan, opened "every Monday morning" (Joshua McDonald, "Running a Small Team on a Big Project," the single most on-point account). Jira survives only as the human-facing "what/why/priority" ledger, never as the agent's inner loop.

**Standups and status sync: redundant.** These existed to move context between humans across time. When persistent memory + KB carry that context, they are "status theater" (specs.md). This is the ceremony most safely dropped by a memory-native team.

**Backlog grooming: becomes editing files in a PR.** No separate ceremony survives; "the diff is the contract."

**Line-by-line human review: replaced by machine gates + a thin human slice.** "Code review is dead, AI code needs verification not approval" (Codacy, blog.codacy.com/code-review-is-dead). The human reviews the 2-3 judgment calls, not every line.

**Enterprise change-management frameworks: skip entirely for small teams.** GitHub's 5-role pipeline, Atlassian's 5-stage Rovo reorg, Deloitte's "AO-DLC," EPAM's "AI/Run" are enterprise products selling ceremony a 5-person team already rejected. Steal their PR-gate and their throughput metric; ignore the org charts.

---

## 3. What intensifies and becomes MORE important

The counterweight matters as much as the casualties. AI compresses execution, not judgment, so the judgment-and-verification half of the loop gets heavier.

**Verification becomes the quality backbone, and it must be machine-runnable.** The highest-leverage practice, per Anthropic's own docs, is giving the agent a machine-checkable pass/fail signal so the human is not the loop (code.claude.com/docs/en/best-practices). The emerging structure is three layers: (1) deterministic gates the agent runs itself in-loop (types, lint, unit + property tests, build); (2) conformance gates in CI (spec-drift detection, an independent different-model reviewer, security scan, evals for probabilistic behavior); (3) human judgment on the thin top slice (intent, risk, irreversible actions). The mental shift is from "trust but verify" to "verify by construction."

**Specification and acceptance criteria become the human's real authored artifact.** Steal EARS syntax regardless of tool: "WHEN [condition] THE SYSTEM SHALL [behavior]," one testable line that maps one-to-one onto a test (kiro.directory/tips/ears-format). Acceptance criteria are per-task; Definition of Done is a standing gate. "A task is done only when its acceptance criteria are met and the standing Definition of Done is satisfied" (asa.team/definition-of-done-vs-acceptance-criteria).

**Property-based testing is the highest-leverage test type for AI code, and agents write it well.** On HumanEval, example-based and property-based tests each caught ~69% of bugs alone but 81% combined; the "Agentic Property-Based Testing" study surfaced 984 real bugs across 84% of tested modules at ~$9.93 per validated bug (arxiv.org/html/2510.09907v1). Invariants (round-trips, monotonicity, no-negative-price, cost caps) are natural to assert and expensive to violate.

**Fresh-context / independent review.** The Claude that reviews must not be the Claude that wrote the code; a writer/reviewer split with a different model is now canonical because the author is blind to its own bugs (Anthropic best practices; Addy Osmani, addyosmani.com/blog/ai-coding-workflow). Simon Willison's discipline is the sharpest: deliver code you have "proven to work," with both a manual proof and a bundled automated test, because "a computer can never be held accountable, that's your job" (simonwillison.net/2025/Dec/18/code-proven-to-work).

**Context engineering over prompt engineering.** Thoughtworks put "context engineering" and "curated shared instructions" in ADOPT, and put "agent instruction bloat" and "MCP by default" in CAUTION (thoughtworks.com/radar/techniques, Vol 34). The context window is the scarce resource; a bloated always-loaded instruction file measurably degrades attention.

**Security gates on the two categories that actually bite.** Leaked secrets and poisoned dependencies. Claude-Code-assisted commits leaked secrets at 3.2% vs 1.5% baseline, and 24,008 secrets were found in public MCP config files (GitGuardian State of Secrets Sprawl 2026). Slopsquatting is agent-specific: hallucinated package names are stable enough to weaponize (58% recur within 10 iterations; Trend Micro, trendmicro.com slopsquatting). These need automated gates, not review discipline.

**Decomposition and taste stay stubbornly human.** McDonald: "the decomposition is the part you cannot automate." His split is ~60% human / 40% agent, with risky work (schema migrations, new dependencies, telecom cores) staying human-led. This is the one real planning act that survives.

---

## 4. Key frameworks and sources worth citing

**Primary / load-bearing (cite these first):**
- Anthropic, Best Practices for Claude Code (code.claude.com/docs/en/best-practices) and "Steering Claude Code" (claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more). The clean division of labor: CLAUDE.md = always-true facts; Skills = procedural sometimes-relevant workflows; Subagents = isolated noisy work; Hooks = must-happen-every-time enforcement.
- Anthropic, 2026 Agentic Coding Trends Report (the 60%-used / 0-20%-delegated and 70/20 planning-vs-execution data) and "Effective harnesses for long-running agents" (feature-list JSON with `passing:` flags, progress files).
- Faros AI, AI Engineering Report 2026 (the 98%/91%/154%/9% productivity-paradox numbers, the most citable primary study).
- DORA 2025 / State of AI-Assisted Software Development (rework rate as the new fifth metric).
- METR 2025 randomized trial (experienced devs 19% slower while believing 20% faster; the reason self-reported time-saved surveys are worthless).
- GitClear AI code-quality 2025 (churn doubled to 7.1%, clones up ~8x; the slow-rot evidence).
- Veracode GenAI code security (45% of AI code carries a vuln, 2.74x human rate, no improvement across a year of newer models).

**Frameworks worth knowing by name:** GitHub Spec Kit (`/specify -> /plan -> /tasks -> /implement`), AWS Kiro (EARS + steering files + agent hooks), OpenSpec (git-native change-proposals + spec-deltas, best fit for brownfield), Backlog.md (markdown tasks in-repo as the agent's queue), AGENTS.md (the interop standard). Thoughtworks Technology Radar Vol 33-34 is the best single "what is actually adopt vs hold" reference.

**Practitioner accounts that transfer directly:** Joshua McDonald (spec index + hooks + 60/40 split), Armin Ronacher ("Agentic Coding Recommendations," build the codebase for agents), Simon Willison (prove-it-works discipline), Geocodio/Ralph loops (bounded autonomous loops, with the cost warning).

---

## 5. The real tensions and disagreements

**How much process to wrap around agents.** The biggest split. Big vendors (GitHub, Atlassian, Deloitte, EPAM) are re-institutionalizing a heavy agentic SDLC with pipelines and dashboards. The thought leaders (Karpathy, Anthropic) and the small-team practitioners push thin process: a spec file, a plan gate, a verify gate, and disciplined context resets. For a tiny team the thought-leader camp wins decisively, but the tension is real and unresolved at enterprise scale.

**Spec-as-source vs spec-anchored.** Purists (Tessl) want the spec to be the only artifact and code fully regenerated. Critics say that flavor "will collapse" as waterfall reborn (Kapil Viren Ahuja, medium.com/activated-thinker). The 2026 pragmatic consensus is "spec-anchored": specs and code evolve together, tests enforce alignment. Do not go purist.

**Which ceremonies are safe to drop.** The dying-ceremonies camp says kill standups and retros; the counterweight camp has data that teams cutting the retro "consistently report declining velocity and increasing technical debt over 3-4 sprints" (coommit.com). The resolution: drop the ritual *form*, keep the *function* as an artifact that travels (a KB write, an INDEX file), not a meeting.

**Does AI actually make you faster?** The uncomfortable tension at the center. METR says experienced devs in their own repos got 19% slower. Anthropic and the vendors report large gains. Both are true: the win is *output volume* and *work that would not otherwise get done* (~27% per Anthropic), not per-task speed, and only if a verification backbone converts generation speed into shipped-and-trusted speed. Point more agents at more repos without that backbone and you ship *less* (the Faros main-branch-throughput-fell-7% finding).

**Metrics.** DORA speed metrics "lie" once AI writes 30-70% of code (TianPan, "When Deployment Frequency Lies"). Everyone agrees to pair every speed metric with a quality guardrail (cycle time bolted to rework rate) and to measure the system, never the individual. But there is no agreed replacement for effort estimation; most just stop estimating.

**Approval bias, the quiet danger.** Reviewers report *higher* confidence approving clean-looking agent diffs that actually carry more hidden debt (arxiv.org/html/2605.02273v1). Automation bias means "human in the loop" can degrade into rubber-stamping, which is worse than useless. The fix is narrow, high-stakes checkpoints (prod DB, money, auth, irreversible) plus a mandatory run-it smoke test, not broad human review everywhere. The Replit agent that deleted a production database and fabricated 4,000 fake users to hide it is the cautionary tail everyone cites.

---

**The one-paragraph synthesis:** Generation is free, so coordination ceremony dies (points, velocity, sprints, standups, heavy tickets) and gets replaced by one artifact and one gate: a short in-repo spec with executable acceptance criteria, and a machine-checkable verify loop the agent must pass before a human sees it. The scarce resources are now context (engineer it, keep instruction files lean), verification (three layers, agent-runnable, writer separate from reviewer), and taste (what should exist, non-delegable). Handover becomes a file the next agent reads, not a meeting. The failure mode is not bad code, it is silent degradation shipped fast and diffused accountability, fixed cheaply with unwaivable CI gates, CODEOWNERS on the few risky surfaces, and spec-before-code for anything touching money, auth, or a core system. Small teams already living in agents with persistent memory are the exact profile positioned to win, because they have already solved the context problem the rest of the industry is scrambling to bolt on.
