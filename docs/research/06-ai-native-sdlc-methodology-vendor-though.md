# AI-Native SDLC Methodology: Vendor + Thought-Leader Frameworks (2025-2026)

## The one big finding

Every serious framework in 2025-2026 has converged on the same shape: **intent/spec up front, agent executes, human reviews the diff, not the keystrokes.** The interesting split is not "should agents write code" (settled) but **how much process you wrap around it.** Big vendors (GitHub, Atlassian) are re-institutionalizing the SDLC around agents (five-phase pipelines, throughput dashboards, PR-approval gates). The thought leaders (Karpathy, Anthropic) push the opposite: thin process, tight context, an "autonomy slider" the human controls. For a 5-person team that already lives in Claude Code, the thought-leader camp is the one to steal from. The vendor camp is mostly re-selling Jira-shaped ceremony you already found too heavy.

---

## By angle, with sources

### 1. GitHub: agentic SDLC + Spec Kit + Copilot coding agent
GitHub's official position is **"agentic DevOps"**: the coding agent is a background SWE teammate you assign issues to, it spins up its own GitHub Actions env, opens a PR, and **PRs require human approval before any CI/CD runs**. The reference architecture is an explicit 5-role pipeline: Assessor (finds ambiguity) -> Resolver -> Specifier -> Generator (code from spec only) -> Validator (checks code against spec + guardrails).
- [GitHub Copilot coding agent 101 (GitHub Blog)](https://github.blog/ai-and-ml/github-copilot/github-copilot-coding-agent-101-getting-started-with-agentic-workflows-on-github/)
- [microsoft/agentic-sdlc-starter (reference architecture)](https://github.com/microsoft/agentic-sdlc-starter)
- [Agentic DevOps (Microsoft Azure Blog)](https://azure.microsoft.com/en-us/blog/agentic-devops-evolving-software-development-with-github-copilot-and-microsoft-azure/)

The genuinely portable piece is **Spec Kit** (open source, Sept 2025), which works with Claude Code directly, not just Copilot. It formalizes **Spec-Driven Development**: `/specify` (user journeys and success, not stack) -> `/plan` (stack, architecture, constraints) -> `/tasks` (small reviewable units) -> `/implement`. The thesis: **"intent is the source of truth,"** LLMs are pattern-completers that fail on ambiguity, so you invest in an unambiguous spec instead of re-prompting. Ships with quality checklists and cross-artifact analysis.
- [Spec-driven development with AI: new open source toolkit (GitHub Blog)](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/)
- [github/spec-kit (repo)](https://github.com/github/spec-kit)

### 2. Karpathy: Software 3.0, vibe coding, autonomy slider
From the June 17, 2025 AI Startup School keynote. The framing: **1.0 = code, 2.0 = learned weights, 3.0 = prompts (English is the new programming language)**; a huge amount of software gets rewritten across all three at once. LLMs are the new OS/utility. Two failure modes to design around: **"jagged intelligence"** (superhuman then dumb on trivial things) and **"anterograde amnesia"** (no memory past the context window, the Memento problem). His practical mandate for teams:
- **Autonomy slider, not full autonomy.** Ship the human-in-the-loop dial (Cursor Tab -> agent mode; Perplexity search -> deep research). Keep agents "on a tight leash" and widen as you trust them.
- **"Demo is `works.any()`, product is `works.all()`."** The gap between an impressive one-shot and a reliable product is verification. Make the human verification loop fast (GUI over reading logs).
- **Build FOR agents.** Ship machine-readable context (`llms.txt`, clean-context extractors) instead of forcing the agent to parse human docs.
- Sources: [Karpathy on Software 3.0 (Latent Space, full talk + notes)](https://www.latent.space/p/s3); follow-on [From Vibe Coding to Agentic Engineering](https://sozai.app/transcript/andrej-karpathy-vibe-coding-agentic-engineering/). Note his own later caution: even he **"never felt more behind as a programmer"** and warns vibe coding breaks at production scale, which is why the next step is disciplined agentic engineering.

### 3. Agent-orchestration platforms / patterns
The field standardized on a handful of named patterns in 2025-2026: **Solo, Parallel Workers, Pipeline, Hub-and-Spoke (orchestrator-worker), Swarm.** The orchestrator-worker pattern = a planner agent holds a project-state object (done / blocked / progress), fans work to specialized workers, synthesizes results. For real parallelism (5+ agents), three mechanisms: **native subagents, tmux orchestrators, git worktrees for isolation.** Late-2025 unlock: CLI agents got reliable enough to run unsupervised + worktrees solved branch isolation.
- [AI Agent Orchestration in 2026 (amux)](https://amux.io/guides/ai-agent-orchestration-2026/)
- [Multi-Agent Orchestration: 5 Patterns That Work (Digital Applied)](https://www.digitalapplied.com/blog/multi-agent-orchestration-5-patterns-that-work)
- [Running Multiple Agent Instances: Parallel Orchestration Patterns](https://codex.danielvaughan.com/2026/04/18/running-multiple-codex-agents-parallel-orchestration/)

### 4. Atlassian's AI posture (the "heavy" reference point)
Atlassian is building **Rovo Dev** agents across five SDLC stages (Plan, Orchestrate, Code, Review, Operate) and, notably, published hard internal numbers to justify the reorg: **19% more PRs/month** on adopting repos (37-51% on low/medium repos, 59-87% at 3-5 active users), **2-4 hours saved per dev per week (~10% of the 24h devs spend coding/reviewing)**, and **51% of security vulns auto-resolved.** Their opinionated claim: **"developer productivity becomes a function of how well a team collaborates across a team of humans and agents,"** and the metric to watch is **PR throughput / hours saved, not seat-usage.**
- [The AI-native SDLC is paying off: 19% more PRs (Inside Atlassian)](https://www.atlassian.com/blog/ai-at-work/ai-native-sdlc-paying-off-per-developer-per-week)
- [Agentic AI for the Whole SDLC with Rovo Dev (The New Stack)](https://thenewstack.io/agentic-ai-for-the-whole-sldc-with-atlassian-rovo-dev-agents/)
- [Rovo Dev in the CLI (Inside Atlassian)](https://www.atlassian.com/blog/development/rovo-dev-command-line-interface)

### 5. Anthropic (most directly applicable to you)
The 400k-session study is the empirical backbone. Findings that matter for methodology:
- **Humans make ~70% of planning decisions but only ~20% of execution decisions.** You own *what*, the agent owns *how*. Design your process around that split.
- **Domain expertise, not coding skill, predicts success.** Experts trigger 12-action chains vs 5 for novices; verified success 28-33% (expert/intermediate) vs 15% (novice). Every top-10 occupation lands within 7 points of software engineers. Translation: your senior context is the moat, not typing.
- **Debugging sessions fell nearly in half** over 7 months as work shifted to deploy/analysis/docs. Task value rose ~27% (building +43%). Agents move you up the value stack.
- [How Claude Code is used in practice (Anthropic)](https://www.anthropic.com/research/claude-code-expertise)

On context/memory (the part that redefines "handover" for you):
- **Subagents return distilled 1-2k-token summaries** from tens of thousands of tokens of exploration. The main agent keeps a high-level plan; workers do deep work in clean windows. This is orchestrator-worker done natively.
- **File-based memory** lets agents "maintain project state across sessions and reference previous work without keeping everything in context." Anthropic's whole framing is **context engineering (curating the right tokens) over prompt engineering.**
- [Effective context engineering for AI agents (Anthropic)](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Best practices for Claude Code (docs)](https://code.claude.com/docs/en/best-practices): Plan Mode to separate research from execution; `.claude/agents/` subagents with scoped tools; context window as the primary constraint.

### 6. AGENTS.md (the interop standard you should adopt)
OpenAI-proposed Aug 2025, donated to the Linux Foundation's Agentic AI Foundation Dec 2025, read by 30+ agents (Claude Code via import, Copilot, Cursor, Codex, Gemini CLI). It is a **"README for machines"**: build/test commands with exact flags, conventions that differ from defaults, architectural boundaries, guardrails. **Nearest-file-wins in monorepos**, so each package ships tailored rules.
- [agentsmd/agents.md (repo)](https://github.com/agentsmd/agents.md)
- [AGENTS.md spec + vs CLAUDE.md/.cursorrules (Morph)](https://www.morphllm.com/agents-md-guide)

---

## Practices worth stealing (concrete, opinionated)

1. **Adopt Spec-Driven Development as your ONE ritual, nothing else.** For anything bigger than a bug fix, write a short spec (intent + success + constraints) before the agent codes. This is the single highest-leverage practice and it is process-light: it lives in a markdown file per feature, not in Jira. Steal Spec Kit's `/specify -> /plan -> /tasks` shape; you do not need the tool, the discipline is the point. It directly attacks Karpathy's ambiguity failure mode.

2. **Make the review the process, kill the tracking process.** The consensus gate everywhere (GitHub, Atlassian, Anthropic's 70/20 split) is human-reviews-the-PR. That is a gate you already have for free in git. Lean on it hard and let it replace status meetings. "Handover" for you is no longer a person explaining WIP; it is a spec file + the agent's memory + the open PR.

3. **Use the autonomy slider deliberately per repo.** Karpathy's leash idea maps cleanly to your stack: Rust telecom core and PostGIS = tight leash (agent proposes, human verifies e2e, per your own self-test rules); CMS copy, docs, mobile scaffolding = long leash. Write the leash length INTO each repo's AGENTS.md/CLAUDE.md.

4. **Standardize on AGENTS.md at repo root, `@import` your CLAUDE.md.** You run many repos across many tools; a per-repo AGENTS.md (exact build/test commands, the "no em-dash" class of guardrails, architectural boundaries) is the cheapest durable investment and it is portable if anyone uses Cursor/Codex/Copilot. Nearest-file-wins is perfect for your polyrepo reality.

5. **Orchestrator-worker + git worktrees is your "no army" multiplier.** This is exactly your parallel-agent-fleet memory rule, and the field now confirms it: file-disjoint tasks, worktree isolation, subagents that return 1-2k-token distilled summaries. That is how 5 people execute like 20 without hiring. Reserve tmux/external orchestration only if you push past ~5 concurrent agents.

6. **Measure PR throughput and hours-reinvested, not agent usage.** Atlassian's one genuinely useful contribution. If you want any metric at all, count merged PRs/week and where the reclaimed hours went (they moved theirs into code quality, docs, engineering culture). Do NOT build a dashboard for this; a monthly glance is enough for 5 people.

7. **Context engineering > prompt engineering as the team skill.** Anthropic's data says domain expertise is the differentiator and context is the constraint. Invest in curated, current context files and pruning stale ones (you already do memory decay checks) rather than clever prompts. Your file-based memory + KB is precisely the asset the rest of the industry is now scrambling to build with "memory tools."

---

## What applies specifically to Bcengi (tiny team, Claude Code, file memory + KB, ship fast, no heavy process)

- **You are already running the thought-leader methodology; you do NOT need the vendor SDLC.** GitHub's 5-role pipeline and Atlassian's 5-stage Rovo reorg are enterprise change-management products. For 5 people who live in Claude Code, they add ceremony you explicitly rejected. Take their PR-gate and their throughput metric; skip the rest.
- **Jira feels heavy because it is the wrong artifact for agent work.** The industry answer is: the spec file is the plan, the PR is the status, the agent memory is the handover. Keep Jira only for human-only, cross-session commitments (deadlines, "Dmitry must sign X"), and let feature-level detail live in per-feature spec markdown next to the code. That is less process, not more.
- **Your file-based memory + KB is a real competitive edge, not overhead.** Anthropic just shipped "memory tools" in beta to give agents what you already have. It changes handover: onboarding Misha or spinning a background agent is "point it at the repo's AGENTS.md + memory," not a person's tribal knowledge. Double down: one crisp AGENTS.md per repo is the missing piece that makes your memory portable to any agent and to any new hire.
- **The moat is Dmitry's + the seniors' domain context, per Anthropic's data, so structure work as: humans write specs and review diffs, agents execute in worktrees.** That is the whole methodology. It scales your existing habits instead of importing someone else's org chart.
- **Explicit anti-pattern to avoid:** do not let "AI-native SDLC" become a reason to adopt Rovo/Copilot-agent tooling on top of Claude Code. Karpathy's "build for agents" and Anthropic's context-engineering guidance say the leverage is in your repo context files and your review loop, not in another vendor agent platform layered over the one you already use well.
