# AI-Native Dev Cadence and Flow: Briefing for a Tiny Claude-Code Team

## The one finding that reframes everything
Generation is now free. Review, integration, and verification are the constraint. Every credible 2025-2026 source converges on this: the bottleneck moved from writing code to deciding what is safe to merge. Faros AI's telemetry study of 10,000+ developers across 1,255 teams is the hard evidence: high-AI-adoption teams merge 98% more PRs and complete 21% more tasks, but PR review time rose 91%, average PR size rose 154%, and bugs per developer rose 9%. Critically, none of the team-level gains aggregated to company-level gains, because downstream bottlenecks (review, CI, release) absorbed the value (Amdahl's Law). Design your cadence to protect reviewer attention, not to maximize agent output. Everything below follows from that.

## Cadence: continuous flow, not sprints
Sprints break under AI because task completion time became wildly variable. An agent can finish three days of planned work in an afternoon, which makes a two-week commitment fiction and forces constant re-planning. The consensus model is Kanban-style continuous flow (pull-based, WIP-limited), or Scrumban (a planned lane plus a pull lane for bugs/ops/debt). Roughly 59% of teams still run two-week sprints, but that share has dropped every year since 2022.

The sharpest reframe is specs.md's "Bolts" replacing sprints: intent-triggered units lasting hours to days, done when done, measured by business value rather than story points or velocity, with the human as validator and the agent doing end-to-end execution. Opinion for Bcengi: run pure continuous flow. No estimation, no velocity, no sprint ceremonies. You are five technical people with heavy Claude Code usage; ceremony is pure drag.

## The core loop (concrete)
This is the loop nearly every source describes, and Anthropic's own usage data validates the shape of it:

1. Human writes intent and plans (Anthropic: humans make ~70% of planning decisions but only ~20% of execution decisions). Invest human time upstream. Expertise multiplies output: expert users trigger action chains 2x+ longer than novices (12 vs 5 actions) and get ~5x the output per instruction.
2. Task is scoped crisply into a spec ("Add empty-state copy to the billing settings page," not "improve billing"). Vague scope is the root cause of the 154% PR-size bloat.
3. Agent executes in an isolated worktree on its own branch. Sessions run ~4 turns, ~10 agent actions per turn.
4. Agent self-verifies: runs targeted tests, lint, screenshots, before reporting done.
5. Agent emits a PR receipt (see below).
6. Human reviews the diff, focusing only on the 2-3 judgment calls, not every line. `git diff main..agent/branch` before merge, and look at what changed, not just whether CI is green (agents routinely edit adjacent files).
7. Merge one branch at a time, rebase the next.

## Agent-per-branch / PR-per-task / worktrees
The stable pattern: one task = one crisp spec = one git worktree = one branch = one small PR. Concretely:

```
git worktree add ../daybook-agent-a -b agent/places-hero-fix
cd ../daybook-agent-a && claude
# ... agent works ...
git diff main..agent/places-hero-fix   # review before merge
```

- Name branches after tasks, not agents (`agent/places-hero-fix`, not `claude-session-2`).
- Put a per-worktree CLAUDE.md that restricts which directories the agent may edit. This prevents scope creep and cross-agent collisions. It maps exactly onto your team's natural boundaries: Frontend=frontend dirs, Igor=backend, Infra=infra, Docs-eng=docs. Directory ownership is your parallelization and review-routing key.
- Parallel ceiling is real: 2-3 agents is standard, 4-5 is the laptop ceiling (RAM/CPU), 6-10+ needs remote machines. The honest caveat from practitioners: multi-agent "doesn't make sense for 95% of agent-assisted tasks." Reserve the parallel fleet for a groomed backlog of genuinely independent cards; default to 1-2.
- Async background execution is now first-class in Claude Code: Ctrl+B backgrounds a running agent, `/tasks` shows status/token usage/progress, and the sub-agent wakes the main agent with results. Good for research, cross-repo analysis, docs, audits; keep file-modifying and sequentially-dependent work in the foreground.

## WIP limits: this is the whole game
Put the WIP limit on the Review column, not the Doing column. Reviewer attention is the binding constraint, so throttle how much work you start to what a human can actually review. Rule of thumb: if agents produce 5-6 PRs/dev/day and one reviewer meaningfully handles N, cap started work so the review queue never exceeds N. The silent killer is "started but not picked up": AI-generated PRs reportedly wait ~4.6x longer before a reviewer even opens them, and that pickup latency dominates total cycle time even though AI PRs get read ~2x faster once opened.

Triage lanes are how you make the WIP limit survivable. Classify every card by risk and give each lane proportional scrutiny:
- Chore (dep bumps, test fixes, doc updates): auto-merge on green, or lightweight review. Stripe's agents auto-merge low-risk changes and route everything else to humans, which alone removes a huge chunk of the queue.
- Product change: full diff review focused on the judgment calls.
- High-risk: design/plan review before the agent writes code, not after.

## Review-loop practices worth stealing
- PR receipt (steal this immediately). Every agent PR carries: task summary + scope boundaries; verification performed (which tests, lint, screenshots); known gaps + risk label; cost signals (runtime, retries, CI minutes); and "reviewer focus: the 2-3 decisions that need human judgment." For a tiny team this converts review from re-reading everything into checking the judgment calls. Claude can generate the receipt as part of finishing the task.
- Keep PRs small on purpose to fight the 154% bloat. Narrow specs produce narrow diffs.
- Treat rejection rate, bounced PRs, and CI failures as training signals for your prompts and CLAUDE.md files, not as shame metrics. Keep a baseline when you change models/prompts/permissions.
- CI as product infrastructure once agents run at volume: selective test routing, flaky-test quarantine, per-agent budget/cost caps. Minimum viable version for you: a fast test subset gate plus quarantining flaky tests so a red flake never blocks the review queue.

## Spec-driven development is your queue format
SDD went mainstream in 2026 (Kiro, GitHub Spec Kit, BMAD) on a simple premise: agents write code well and guess intent badly, so an executable spec becomes the source of truth. AWS reports Kiro customers shipping 40-hour features in under 8 hours of human time when authored spec-first. For you this is not a tool purchase, it is a discipline: the plan/spec doc IS the queue card. A lightweight `plan.md` per task (or a Claude-Code plan) is enough. A groomed backlog of crisp, independent specs is the precondition for running parallel agents at all, so grooming specs into independence is now the single highest-leverage human hour in the week.

## How work gets queued and pulled (tiny-team version)
- Kill the heavy Jira DEV project for dev flow. Replace it with a thin pull queue: three states only, Spec'd -> In Progress -> In Review. The card is a crisp spec + a risk label. GitHub Issues, a markdown backlog, or a stripped Jira with just title/spec/risk all work.
- Pull, do not pre-assign. Whoever is free pulls the top independent card in their domain. Directory ownership decides who reviews.
- WIP limits: cap In Review to daily reviewable throughput (that is the throttle), and cap In Progress to ~2-3 per person.

## What your file-based memory + KB actually change about handover
This is your structural advantage and it is under-discussed in the literature. Traditional handover ceremonies (standups, sprint reviews, ticket-comment archaeology, onboarding docs, "what was I doing") exist to move context between humans across time. When persistent file-based memory plus a KB carry that context, an agent re-hydrates on demand and those ceremonies become largely redundant. CLAUDE.md per repo/worktree + your KB IS the durable context layer that standups were patching.

Two implications:
1. The async, no-standup, continuous-flow model is more viable for Bcengi than for almost any team, because you have already solved the context-loss problem that ceremonies exist to patch.
2. Make the memory/KB write part of the definition of done. You already do real-time memory saves; extend it so every merged task updates CLAUDE.md/KB, so the next agent pull starts warm. Handover stops being a meeting and becomes a file diff.

## Opinionated recommendation (tight)
1. No sprints. Continuous Kanban, three columns: Spec'd, In Progress, In Review. No estimation, no velocity, no ceremonies.
2. The WIP limit lives on In Review, sized to what you plus the owning dev can review per day. That is the only throttle that matters. Cap In Progress at 2-3 per person.
3. One task = one crisp spec = one worktree = one branch = one small PR. Per-worktree CLAUDE.md scopes editable dirs to the owner's domain.
4. Risk-label every card: chore / product / high-risk. Chores auto-merge on green. Product gets a diff review. High-risk gets a plan review before any code.
5. Mandate Claude-generated PR receipts. Review the judgment calls, not the lines.
6. Parallel fleet only against a groomed backlog of independent cards. Default to 1-2 agents. Do not cargo-cult 10-agent fleets.
7. Definition of done includes a memory/KB write. Grooming crisp, independent specs is Dmitry's highest-leverage hour of the week.

## Sources (title + URL)
- [The AI Productivity Paradox Research Report - Faros AI](https://www.faros.ai/blog/ai-software-engineering) and [AI Engineering Report 2026: The Acceleration Whiplash (PDF) - Faros AI](https://pages.faros.ai/hubfs/AI_Engineering_Report_2026_The_Acceleration_Whiplash_Faros.pdf)
- [How Claude Code is used in practice - Anthropic](https://www.anthropic.com/research/claude-code-expertise)
- [AI Coding Agents Move the Bottleneck to Review Queues - Developers Digest](https://www.developersdigest.tech/blog/ai-coding-agents-review-queues)
- [Git Worktrees + Claude Code: The 2026 Playbook for Running Parallel Agents - Developers Digest](https://www.developersdigest.tech/blog/git-worktrees-claude-code-parallel-agents-guide)
- [The AI-Native SDLC: Reimagined - specs.md](https://specs.md/methodology/sdlc-reimagined)
- [Claude Code Async: Background Agents & Parallel Tasks - claudefa.st](https://claudefa.st/blog/guide/agents/async-workflows)
- [AI Is Breaking Code Review: How Engineering Teams Survive the PR Bottleneck - Codacy](https://blog.codacy.com/ai-breaking-code-review-how-engineering-teams-survive-pr-bottleneck)
- [Code Review Is the Real Bottleneck of 2026 - DEV Community](https://dev.to/code-board/code-review-is-the-real-bottleneck-of-2026-and-most-teams-dont-see-it-5eed)
- [How to plan a software development sprint in 2026 (59% two-week-sprint stat) - Cadence](https://cadence.withremote.ai/blog/plan-software-development-sprint)
- [Spec-Driven Development (SDD): The Definitive 2026 Guide - BCMS](https://thebcms.com/blog/spec-driven-development)
- [Understanding Spec-Driven Development: Kiro, spec-kit, and Tessl - Martin Fowler](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)
- [Claude Code Adds Dynamic Workflows for Parallel Agent Coordination - InfoQ](https://www.infoq.com/news/2026/06/dynamic-workflows-claude-code/)

Note: the "4.6x longer to pick up / 2x faster once reviewed" figures appear in the Codacy and DEV bottleneck writeups summarizing 2026 telemetry; treat as directional. The Faros figures (98% / 91% / 154% / 9% / 21%) are from the primary 10,000-developer study and are the most citable.
