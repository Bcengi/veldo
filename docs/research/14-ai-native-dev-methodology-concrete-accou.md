# AI-Native Dev Methodology: Concrete Accounts (2025-2026)

## Bottom line
The teams shipping fastest with coding agents converged on the same shape: the unit of work is a **spec with executable acceptance criteria living in the repo**, not a ticket in a tracker. Humans do decomposition and review. Agents do implementation in parallel, each in its own git worktree. Process discipline (standups, grooming, per-ticket status updates) gets replaced by **deterministic enforcement (hooks) and in-repo markdown**. Every credible account says the same two things: the bottleneck moved from writing code to (a) specifying clearly and (b) reviewing volume. This maps almost exactly onto what Bcengi already has (file-based memory + KB) and what it wants to drop (heavy Jira).

---

## Key findings

**1. Role shift: implementer to orchestrator, confirmed by data, not hype.** Anthropic's own research: developers use AI in ~60% of their work but can "fully delegate" only 0-20% of tasks. The win is **output volume**, not per-task speed: engineers report "a net decrease in time spent per task category, but a much larger net increase in output volume." ~27% of AI-assisted work is stuff that "wouldn't have been done otherwise" (papercuts, nice-to-have tools, exploration). (Anthropic, "2026 Agentic Coding Trends Report".)

**2. The spec index replaces the project-management tool.** In the most on-point small-team account (4 engineers, 14 Q4 features), the entire project plan is a markdown table at `specs/INDEX.md`, updated by whoever moves a spec between states, checked "every Monday morning." Standups and the formal PM tool were dropped. Code review, PRs, and tests were kept. Result claimed: throughput went from ~1 feature per engineer per quarter to 2-3x that at the same headcount. (Joshua McDonald, "Running a Small Team on a Big Project.")

**3. Verifiable acceptance criteria are the whole game.** Geocodio engineer Mathias Hansen built two complete apps in a weekend with autonomous loops. His rule: "Each task needs clear, verifiable criteria so Claude knows exactly when it's done" and good criteria are executable commands or assertions ("php artisan test passes"), not subjective judgments. Reframe: "The bottleneck isn't 'can we build this?' anymore. It's 'can we specify this clearly enough?'" (Geocodio, "Ship Features in Your Sleep with Ralph Loops.")

**4. Parallelism is the productivity unlock, and it is bounded by review, not by the model.** Anthropic's internal engineers run 3-5 (some 5-10) Claude sessions concurrently, each in its own git worktree so they never collide. Industry reporting puts teams at 4-8 concurrent worktrees per developer, "bottlenecked on review rather than Claude." (Anthropic best-practices; Claude Code worktrees guides.)

**5. Decomposition is the human job that does not automate.** McDonald: "the decomposition is the part you cannot automate... either output needs a human (usually the manager or tech lead) to map it onto the team you actually have." His split is ~60% human / 40% agent; risky work (schema migrations, new dependencies) goes to experienced humans, low-risk sub-half-day mini-specs go to implementer subagents in worktrees.

**6. Onboarding/handover collapses from weeks to hours** when context is written down. Anthropic cites Augment Code delivering a project a CTO scoped at 4-8 months in two weeks; Rakuten had Claude Code implement a method in vLLM (12.5M LOC) in 7 hours autonomous, single run, 99.9% numerical accuracy. This is the trend Bcengi's persistent memory already operationalizes.

**7. Jira is being demoted, not always deleted.** The argument (Michael Wolpers) is to keep Jira as an "execution interface" but move the knowledge authority to markdown-in-git organized by sprint, because git gives agents temporal context "a Jira board makes expensive to extract." Linear reportedly took ~30% share from Jira in 2025. (Note: the Wolpers piece is argument, not a documented migration; treat as framing.)

---

## Concrete practices worth stealing (opinionated)

**Make the mini-spec the unit of work, with a fixed template.** McDonald's required sections: Data contracts, User-visible behavior, Failure modes, Rollout, Out of scope, Open questions. A four-page spec decomposes into 5-10 mini-specs that run in parallel (his search-with-autocomplete example produced 7 across data/API/frontend/analytics). Steal the template verbatim.

**Enforce with hooks, not with meetings.** McDonald runs four hooks so a no-process team still has guardrails: (1) spec-gate PreToolUse blocks writes outside a spec, (2) test-runner PostToolUse runs tests on every save, (3) completion-check on Stop verifies the task finished, (4) spec-loader on SessionStart injects the active spec. For a team that wants zero ceremony, this is the key move: the discipline is code.

**Ship one feature as multiple thin PRs in parallel worktrees.** This is the pattern "senior engineers using Claude Code ship the fastest with," and it also improves review quality. One agent per mini-spec, isolated worktree, does not touch shared schemas.

**Reviewer subagent fans out a verifier per finding.** Anthropic's canonical pattern: a reviewer reads a diff, produces findings, then dispatches a separate verifier subagent per finding instead of grading its own work. Pair with one human final pass. This is how a tiny team keeps quality when agents produce 3x the volume.

**Build the codebase for agents (Armin Ronacher, most concrete individual workflow):**
- Run `claude --dangerously-skip-permissions` inside Docker (his alias `claude-yolo`). Bcengi already runs `--dangerously-skip-permissions`; the containment lesson still applies.
- "Anything can be a tool," but tools must be **fast** and **clear about errors**, and "protected against an LLM chaos monkey using them completely wrong."
- **Always log to files** so agents self-diagnose; put critical commands in a `Makefile`.
- Prefer plain SQL over ORMs ("you get excellent SQL out of agents"), "the dumbest possible thing that will work," longer descriptive function names, keep permission checks local (agents forget checks hidden in config).
- Be conservative about library upgrades (they invalidate the agent's learned reasoning).
- Note his language take: agents struggle with Python "magic" (pytest fixture injection, async loops); Go's explicitness suits them. Relevant when Bcengi picks patterns in each repo.

**Unified logging + a "read last N log lines" tool** (Simon Willison). Treat the LLM as "a digital intern, hired to type code for me based on my detailed instructions." Use a cheaper/second model (he uses Gemini CLI subagents) for grunt subtasks to preserve the main agent's context budget.

**Bound autonomous loops and watch cost.** The Ralph loop (Geoffrey Huntley, May 2025): a bash `while` loop re-reads a `PROMPT.md` each iteration, using the filesystem (`progress.txt`, `prd.json`) as memory instead of conversation history ("naive persistence"). Powerful for greenfield/prototypes and overnight backlog burndown. Caveat: one Geocodio engineer burned two Claude Max subscriptions ($400/mo) in days. Start with 10 iterations, not 100. Do not point a Ralph loop at the Rust telecom core.

---

## What specifically applies to Bcengi

1. **Demote the DEV Jira board to a roadmap, move execution into each repo.** Keep Jira/CEO project for the "what" and priorities (Dmitry's level). Add a `specs/INDEX.md` per repo as the live execution tracker. This kills the "Jira feels too heavy" problem without losing traceability, and it is exactly the McDonald/Wolpers pattern. Your file-based memory already makes in-repo the natural home.

2. **Handover is already solved; lean into it.** Your persistent memory + KB is precisely the "onboarding weeks to hours" mechanism Anthropic describes. Drop status-sync standups entirely: a fresh agent session reads `CLAUDE.md` + active spec + memory KB and is caught up. That is your comparative advantage; most teams are just now bolting on `CLAUDE.md`/`AGENTS.md`.

3. **The one rule to enforce: no work without an executable acceptance criterion.** For a 4-person team across Django/Kotlin/PostGIS/Rust/web, this is the single highest-leverage change. "Done" = a command that passes, per repo. This is what lets Frontend/Igor/Infra/Docs-eng each run 3-5 agents without you reviewing prose.

4. **Assign by risk, not by ticket.** Rust core, PostGIS schema changes, telecom infra, new dependencies stay human-led (your ~60/40 human/agent split). Frontend features, docs, CMS content, papercuts, and glue go to agents in worktrees. Docs-eng (docs) and much of the companion/web surface are near-fully delegable; the Rust core is not.

5. **Your real bottleneck will be review, so build the review pipeline now.** Adopt the reviewer-subagent-fans-out-verifiers pattern plus a human gate. Without it, agent volume outruns your ability to trust it, and a tiny team cannot afford a regression in the telecom core.

6. **Add hooks so "no process" does not mean "no guardrails."** Test-on-save, spec-gate, and session-start-spec-loader hooks give you the safety of process with none of the meetings. This is the concrete answer to "no heavy process and no army."

7. **Use loops for the backlog, bounded.** Point a bounded Ralph-style loop at accumulated papercuts and prototype work overnight (the "27% that wouldn't have been done otherwise"). Cap iterations and watch spend.

---

## Notable sources (title + URL)

- Anthropic, "2026 Agentic Coding Trends Report" (primary; 60%-used/0-20%-delegated data, Rakuten/CRED/Augment Code cases): https://resources.anthropic.com/hubfs/2026%20Agentic%20Coding%20Trends%20Report.pdf
- Joshua McDonald, "Running a Small Team on a Big Project: Spec-Driven Development with Claude Code" (most on-point: 4 engineers, spec index, hooks, 60/40 split): https://joshmcdonald.medium.com/running-a-small-team-on-a-big-project-spec-driven-development-with-claude-code-9a1b97f58551
- Geocodio, "Ship Features in Your Sleep with Ralph Loops" (real company, verifiable-criteria rule, cost warning): https://www.geocod.io/code-and-coordinates/2026-01-27-ralph-loops
- Armin Ronacher, "Agentic Coding Recommendations" (most concrete individual workflow): https://lucumr.pocoo.org/2025/6/12/agentic-coding/
- Simon Willison, "Agentic Coding: The Future of Software Development with Agents": https://simonwillison.net/2025/Jun/29/agentic-coding/
- Anthropic, "Claude Code: Best Practices for Agentic Coding" (worktrees, parallel sessions, subagents): https://www.anthropic.com/engineering/claude-code-best-practices
- Anthropic, "Claude Code Advanced Patterns: Subagents, MCP, and Scaling to Real Codebases": https://resources.anthropic.com/hubfs/Claude%20Code%20Advanced%20Patterns_%20Subagents,%20MCP,%20and%20Scaling%20to%20Real%20Codebases.pdf
- Michael Wolpers, "From Jira to AI Agents" (framing for demoting Jira; argument, not a documented migration): https://age-of-product.com/jira-ai-agents/
- Addy Osmani, "How to write a good spec for AI agents": https://addyosmani.com/blog/good-spec/
- Grokipedia, "Ralph (AI coding agent)" (origin/definition of the Ralph loop, Geoffrey Huntley, May 2025): https://grokipedia.com/page/Ralph_AI_coding_agent

Weaker/secondary (use only as directional): buildmvpfast solo-dev revenue breakdowns (e.g. a solo dev reported ~$602K in 2025 / ~$28K MRR from mobile apps) and "Linear vs Jira 2026" (the ~30% switch figure). Revenue-proof, not process-proof; not primary.

One honest caveat: the Anthropic trends report is partly predictive ("we predict"), and several enterprise case numbers (CRED "doubled," TELUS "30% faster") are vendor-reported. The small-team practices (McDonald, Geocodio, Ronacher, Willison) are the load-bearing, directly-transferable material.
