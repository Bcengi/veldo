# BRIEFING: Lightweight work-tracking for tiny AI-first teams

## Bottom line (opinionated)

For a 5-person team that lives inside Claude Code across many repos, the single source of truth should be **plain markdown task files committed next to the code, one small tool to view them as a board, and "done" defined as a machine-checkable gate the agent runs on itself.** Jira loses not because it lacks features but because its state lives in a system the agent cannot see, edit, or diff. The whole industry moved in 2025-2026 toward "the task lives where the code lives," and the sharpest version of that for AI agents is git-native markdown (Backlog.md), not a hosted tracker.

Concretely, two viable stacks, and I would run a hybrid:
- **Per-repo, agent-facing:** Backlog.md (markdown tasks in-repo) as the working queue the agent reads/writes/closes.
- **Cross-repo, human-facing:** GitHub Issues/Projects (or Linear) as the thin roll-up layer where a human sees "what is in flight across the 5 repos" without opening each one.

Do not put Linear/Jira in the agent's inner loop. Put it (if anything) at the portfolio level for Dmitry's own visibility.

---

## The three archetypes, and what tiny AI teams actually pick

**1. Git-native markdown tasks ("issues as code") - the AI-native winner.**
The standout is **Backlog.md**: every task is a plain `.md` file in a `backlog/` folder in the repo, version-controlled, no server, no account, no telemetry. Each task carries a description, per-task **acceptance criteria**, a reusable project-wide **Definition of Done** checklist (configured in `backlog.config.yml`), status across a To Do / In Progress / Review / Done pipeline, plus milestones, dependencies, and threaded comments from humans and agents. It ships a terminal Kanban board (`backlog board`) and a local drag-and-drop web UI (`backlog browser`), and it ships explicit Claude Code / MCP agent instructions. The design thesis is exactly your situation: agents decompose a feature into atomic, PR-sized tasks, and the task file becomes "a permanent ledger of what was attempted and why, legible to you, your team, and the next agent." (github.com/MrLesk/Backlog.md; news.ycombinator.com/item?id=44483530). There is also a newer entrant, **Backlog** (backlog.so / backloghq/backlog), a persistent-task plugin for Claude Code that links every change back to the task, the claim that authorized it, and the agent that produced it via `git log`.

**2. GitHub Issues + Projects - the pragmatic default.**
2025-2026 GitHub Issues got sub-issues (parent/child hierarchy), checklist-items-to-sub-issues conversion, and a GA Projects revamp, and crucially you can now **assign an issue directly to a coding agent** (Copilot, Claude, Codex) that plans, executes, and opens a PR. GitHub Agentic Workflows lets you author intent-driven automations in plain markdown that run in Actions (e.g. any `bug`-labeled issue auto-triggers an agent to reproduce and investigate). If a tiny team already lives in GitHub, this is often "sufficient" (a recurring HN verdict: `gh` CLI + Issues covers most of what Backlog.md does). Weakness: state is in GitHub's DB, not in the repo, so it is not diffable and not offline. (github.blog agentic-workflows; github.com/orgs/community/discussions/154148; github.blog Octoverse 2025).

**3. Linear - the fast hosted tracker for AI-native startups.**
Every 2025-2026 comparison lands the same way: for a 5-50 engineer startup that wants speed and to stay out of the way, Linear beats Jira. Sub-50ms loads, opinionated cycles, keyboard-driven, unlimited users on free, issues creatable from Slack, AI triage/backlog-prioritization built in. The specific pitch to you: "Linear's lightweight issues and fast cycle model fit teams where engineers prompt-spec features in Cursor or Claude Code and ship within a day." It is still a hosted DB the agent does not natively own, but its MCP/API is clean. (tech-insider.org/linear-vs-jira-2026; monday.com/blog/rnd/linear-or-jira; medium.com/@chrisshoff2026 Linear vs Jira 2025).

---

## Practices worth stealing (concrete)

- **One task = one PR-sized unit.** The single most-repeated rule from practitioners: "smaller atomic tasks are the only way to achieve a high success rate," tasks "as big as would fit in a PR." This is the real reason to leave Jira epics behind, they encourage tasks too big for an agent to land cleanly.
- **The three-checkpoint loop (spec -> plan -> code).** Backlog.md and every spec-driven-development guide converge on the same shape: (1) agent decomposes the idea into small tasks with acceptance criteria *before* coding, human reviews; (2) agent researches the codebase and writes the implementation plan *into the task file*, human reviews; (3) agent implements, one focused PR, human reviews. "A human review between every pair." (github.com/MrLesk/Backlog.md; datacamp.com spec-driven-development-with-claude-code).
- **Spec-driven development files as the artifact.** The lean 4-step is `specify -> plan -> tasks -> implement`, materialized as `requirements.md`, `design.md`, `tasks.md` in-repo. The stated root cause it solves: "your AI agents have no shared source of truth, and they fill every gap with their own assumptions." (gist alfredoperez SDD; github.com/FredAntB/Spec-Driven-Development).
- **AGENTS.md at repo root as the shared context contract.** The 2026 convention (OpenAI-introduced, GitHub-documented) so every agent - Claude Code, Copilot, Codex - reads the same instructions. Pairs with, does not replace, the task files. (medium.com/codandotv AGENTS.md).
- **Separate the writer agent from the validator agent.** "Do not ask the same agent to write code and verify it. The validator is a separate agent with a separate prompt, separate context, and explicit permission to fail the work." (braingrid.ai definition-of-done-for-ai-builders; dev.to/teppana88).
- **Keep dependencies explicit in the task file** so the agent picks the right next task, and expect a real problem at scale: agents "blowing out the context budget" navigating a large markdown backlog. Mitigation is aggressive archiving of Done tasks and tight per-task scope (HN thread).

---

## How AI-first teams define "done"

The clean distinction that has emerged: **acceptance criteria are per-task and specific; Definition of Done is a standing gate applied to every change.** "A task is done only when its acceptance criteria are met and the standing Definition of Done is satisfied." Write acceptance criteria as testable conditions, because when an agent reads them "it becomes the specification the agent builds against and the only standard it checks itself by." (asa.team DoD-vs-acceptance-criteria; braingrid.ai how-to-write-acceptance-criteria; agentcenter.cloud).

The concrete, steal-this DoD checklist for AI agents (from addyosmani/agent-skills, definition-of-done.md):
- **Correctness:** all acceptance criteria met; behavior verified **at runtime, not just compiled/typechecked**; new behavior covered by a test that fails without the change and passes with it; existing tests still pass; edge and error paths handled, not just the happy path.
- **Quality:** intent-revealing naming, no duplicated logic, no dead code/debug output/commented blocks, **changes scoped to the task with no sneaked-in refactors**, lint/format pass.
- **Integration:** works with the rest of the system; migrations/config/feature-flags accounted for; backward compatibility considered for any public interface.
- **Ship-readiness:** security review for untrusted input/auth/data; observability on critical paths; rollback plan for risky changes; **human review and approval before merge.**

Two AI-specific additions the sources stress: verified in a real environment not just locally, and for anything touching model/prompt/agent behavior, require **evaluation evidence** (LLM output is probabilistic, a binary pass/fail on one run "is gambling, not testing"). (github.com/addyosmani/agent-skills; braingrid.ai; scrum.org definition-done-ai-agents).

---

## What specifically applies to Bcengi

- **Adopt Backlog.md per repo** (Django companion, Kotlin mobile, PostGIS places, Rust core, web/CMS). It is the closest fit to how Dmitry already works: markdown, git, no server, Claude Code-native, tasks diffable in the same PR as the code. It also dovetails with your existing file-based memory + KB: the task file becomes the handover artifact, so "handover" stops meaning "explain state to the next agent" and becomes "point the next agent at `backlog/TASK-N.md`." Codify your DoD once in each repo's `backlog.config.yml` and in AGENTS.md/CLAUDE.md so every agent self-checks against it.
- **Solve the multi-repo gap deliberately - it is the known weak spot.** Backlog.md is per-repo, and unified cross-repo visibility is the top open question in the community. For 5 repos you need a thin roll-up. Cheapest correct option: a nightly Claude Code job that reads each repo's `backlog/` and renders one cross-repo board (into your KB or a single markdown/HTML dashboard). If you want it hosted and human-facing, mirror only milestone-level items into GitHub Projects or Linear, and treat that mirror as read-mostly. Do not make the agents write to two systems.
- **Do not put Jira/Linear in the agent's inner loop.** The value of a hosted tracker for you is portfolio visibility for Dmitry, not agent task state. Agent state belongs in-repo where it can be read, edited, and reverted by the same tools that touch the code.
- **Encode the "one task = one PR" rule as policy.** With Claude Code shipping many PRs per day, oversized tasks are your main failure mode. Enforce PR-sized decomposition at the spec-review checkpoint.
- **Institute writer-agent vs validator-agent** as a standing practice, given your parallel-agent-fleet style. The validator gets fresh context and permission to reject. This is the cheapest quality lever and needs no new tooling.
- **Keep AGENTS.md/CLAUDE.md as the context contract** across all repos so every agent inherits the same DoD and conventions - you already do a version of this, formalize the DoD block into it.

---

## Sources (title + URL)

- [Backlog.md - task manager for humans and AI agents in a git ecosystem (GitHub)](https://github.com/MrLesk/Backlog.md)
- [Backlog - persistent task management plugin for Claude Code and agent teams (GitHub)](https://github.com/backloghq/backlog) and [backlog.so](https://backlog.so/)
- [Backlog.md discussion (Hacker News)](https://news.ycombinator.com/item?id=44483530)
- [Definition of Done reference for AI coding agents (addyosmani/agent-skills)](https://github.com/addyosmani/agent-skills/blob/main/references/definition-of-done.md)
- [How to Write Acceptance Criteria an AI Agent Can Actually Verify (Braingrid)](https://www.braingrid.ai/blog/how-to-write-acceptance-criteria-ai-agent-can-verify)
- [Definition of Done for AI Builders (Braingrid)](https://www.braingrid.ai/blog/definition-of-done-for-ai-builders)
- [Definition of Done vs Acceptance Criteria (asa.team)](https://blog.asa.team/definition-of-done-vs-acceptance-criteria/)
- [How I Validate Quality When AI Agents Write My Code (dev.to/teppana88)](https://dev.to/teppana88/how-i-validate-quality-when-ai-agents-write-my-code-481c)
- [Spec-Driven Development with Claude Code (DataCamp)](https://www.datacamp.com/tutorial/spec-driven-development-with-claude-code)
- [SDD: specify -> plan -> tasks -> implement (gist, alfredoperez)](https://gist.github.com/alfredoperez/9b952315f4dd6bc2718fa1e259275109)
- [Spec-Driven Development skill: requirements.md/design.md/tasks.md (FredAntB)](https://github.com/FredAntB/Spec-Driven-Development)
- [AGENTS.md: a Single Source of Truth for Any AI in Your Repo (Medium/CodandoTV)](https://medium.com/codandotv/agents-md-a-single-source-of-truth-for-any-ai-in-your-repo-ce1d0d7ea918)
- [Automate repository tasks with GitHub Agentic Workflows (GitHub Blog)](https://github.blog/ai-and-ml/automate-repository-tasks-with-github-agentic-workflows/)
- [Evolving GitHub Issues and Projects, GA (GitHub community)](https://github.com/orgs/community/discussions/154148)
- [What 986 million code pushes say about the developer workflow in 2025 (GitHub Octoverse)](https://github.blog/news-insights/octoverse/what-986-million-code-pushes-say-about-the-developer-workflow-in-2025/)
- [Linear vs Jira: Why 30% of Teams Switched, 2026 (tech-insider)](https://tech-insider.org/linear-vs-jira-2026/)
- [Linear vs Jira, which is best for your team in 2026 (monday.com)](https://monday.com/blog/rnd/linear-or-jira/)
- [Linear vs Jira 2025: Why Startups Are Switching (Medium)](https://medium.com/@chrisshoff2026/linear-vs-jira-2025-why-startups-are-switching-15d60e1abfc1)
