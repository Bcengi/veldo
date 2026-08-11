# Minimal security/governance for agent-written code: briefing

## Bottom line up front

The threat data from 2025-2026 says two categories account for almost all the real risk from agent-written code: **leaked secrets** and **poisoned dependencies**. Both are now measurably worse with AI coding tools, and both are fixable with automated gates that need zero human babysitting. Everything else (review discipline, compliance) can stay deliberately thin. The right shape for a tiny team is not "process," it is **~5 automated gates checked into git + CI plus 2 Claude Code config files per repo**. Controls run on commit/push/PR, never in a meeting or a ticket queue.

The opinionated principle: make the safe path the default path in tooling, so nobody has to remember to be careful. Humans review architecture and product judgment; machines catch secrets, bad packages, and obvious vulns.

---

## Key findings (the numbers that justify the controls)

**Secrets are the #1 measured harm, and AI roughly doubles it.**
- 28.65M new hardcoded secrets hit public GitHub in 2025, +34% YoY (GitGuardian State of Secrets Sprawl 2026).
- Claude-Code-assisted commits leaked secrets at 3.2% vs a 1.5% baseline, roughly 2x. AI tools generate "production-ready-looking" code with hardcoded keys, and completion can re-emit memorized credentials.
- AI-service credentials are the fastest-growing leak category, +81% YoY.
- 24,008 unique secrets found in MCP config files on public GitHub (2,117 still valid). "Convenience-first" official docs actively normalize hardcoding keys into MCP config. This one is directly relevant to you: you run many MCP servers.
- Remediation is the real failure: 64% of valid secrets from 2022 are still live. Detection without rotation is theater.

**Slopsquatting is the dependency threat unique to agents.**
- Study across 16 models / 576,000 code samples: hallucinated package names are stable enough to weaponize. 43% of fake names recur across similar prompts; 58% reappear within 10 iterations. Attackers just register the names the models keep inventing.
- Classic typosquatting detection does not help: hallucinated names are brand-new strings with no near-collision to a real package.
- Real incidents exist: the "Clinejection" chain (Feb 2026) showed AI agents wired into CI/CD multiply blast radius. CISA/NSA/Five Eyes issued a joint advisory on AI agent supply-chain risk in early 2026. Malicious packages riding this vector have pulled tens of thousands of downloads.

**Agent-written PRs degrade review quality in a specific way.**
- A Jan 2026 study found agent-generated changes carry more redundancy and more technical debt per change than human code, and, worse, reviewers report *higher* confidence approving them (clean-looking diffs cause approval bias).
- Empirical finding: most AI-generated PRs get no human review, and when reviewed, the review is often done by another agent. "It looks clean" is now a known failure mode, not a safety signal.

**Claude Code itself ships real controls (and has had real CVEs).**
- Read-only by default; permission model with allow/deny; working-directory write boundary; `permissions.deny` to hard-block things like `curl`/secret paths; `/sandbox` (Linux bubblewrap, macOS seatbelt) cut permission prompts 84% internally; isolated context window for web fetch; MCP servers require trust verification; managed settings + `ConfigChange` hooks let you enforce/audit config org-wide.
- But: CVE-2025-54794 (path-restriction bypass) and CVE-2025-54795 (command-injection RCE) are a reminder the agent is attack surface. Trust verification is *disabled* in non-interactive `-p` mode, which matters if you script agents in CI.

---

## Concrete practices worth stealing

### Secrets (highest ROI, do first)
1. **Client-side secret-scan pre-commit hook** on every repo: `gitleaks` or GitGuardian `ggshield`. Fastest feedback, catches the majority of accidents. GitGuardian ships an AI/agent-aware hook specifically because AI commits leak 2x.
2. **Server-side backstop** because pre-commit is bypassable with `--no-verify`: a pre-receive hook or GitHub push protection / a `gitleaks` CI job that fails the build. Client hook = convenience, server hook = the actual control.
3. **Treat a leaked secret as compromised, always rotate.** The 64%-still-live stat is the lesson: scanning that doesn't trigger rotation is worthless. Have a one-command rotation path.
4. **Never let keys touch MCP config in a repo.** Keys live in `.env` (gitignored) or a real secret store; MCP config references env vars. Scan config files too, given the 24k-secrets-in-MCP finding.

### Dependency / supply-chain (agent-specific, second priority)
5. **Agents install from the lockfile, never regenerate it.** When a new dep is genuinely needed, the agent produces a **lockfile diff for human review** rather than installing-and-continuing. This is the single most important agent rule and it is cheap.
6. **Kill install scripts by default:** `npm ci --ignore-scripts`, `pip install --only-binary :all:`. Postinstall scripts are the most common malware vector.
7. **Dependency cooldown:** do not let agents pull a package version published in the last 24-72h. Community detection usually flags malicious releases inside that window. (OX Security, Andrew Nesbitt both push this.)
8. **A slopsquatting-aware scanner in CI:** Socket.dev / Snyk / Aikido now detect the exact signature (newly registered name, thin download history, wide AI-suggested spread). Pair with `lockfile-lint` to gate agent-modified lockfiles.
9. **Registry allowlist** so agents resolve only from approved registries/scopes (blocks dependency-confusion too).

### Review gates (keep light, make them targeted)
10. **One human approval on anything that reaches `main`/production**, but spend that human attention on architecture, test judgment, and product context, not typo-hunting. Given approval bias, the reviewer's job is explicitly "is this the right design and is it tested," not "does the diff look clean."
11. **Let AI do the first-pass review** (Claude Code security-guidance plugin, or a CI SAST step) for obvious defects and policy violations, then a human signs off. Hybrid is the documented best pattern.
12. **Require the diff to run.** Because agent code carries more hidden debt, a mandatory "did you actually exercise this path" gate (a smoke test, not just green unit tests) catches the confident-but-broken changes.

### Claude Code config (your specific tool)
13. **Check `.claude/settings.json` into each repo** with `permissions.deny` for secret paths and network fetch, an allowlist of safe commands, and approved MCP servers. This is governance-as-code: it travels with the repo, enforces itself, needs no ticket.
14. **Turn on `/sandbox`** (bubblewrap on your Linux boxes) for the 84% fewer prompts *and* the filesystem/network isolation that contains a prompt-injected agent. Use `anthropic-experimental/sandbox-runtime` to sandbox MCP servers too.
15. **Use `ConfigChange` hooks** to audit/block mid-session config changes, and **managed settings** to set a floor across the team's machines.
16. **Prompt-injection hygiene:** the agent reads untrusted content (web pages, place data, partner docs, issue text). Keep WebFetch's isolated context, never auto-approve `curl`/`wget`, and assume any external text can carry instructions.

### Least-viable compliance (do the minimum, on purpose)
17. **Do not pursue SOC 2 until a specific enterprise deal ($100K+ ACV) demands it.** Below ~$500K ARR with <10 people, formal compliance is a distraction from PMF. The consensus 2025-2026 startup guidance is explicit about this.
18. **When a deal forces it:** scope to **Security criterion only**, production + customer-data systems only. Get **Type 1 fast to unblock the deal, and start the Type 2 observation window the same day.**
19. **The controls that actually matter are the boring ones you should have anyway:** MFA everywhere (Workspace, GitHub, AWS, DB, SSH), RBAC + least privilege, encryption in transit/at rest, dependency + vuln scanning, quarterly access review. You are already building most of these as engineering hygiene.
20. **Evidence is the whole game.** No documented evidence = no compliance. Use an automation platform (Vanta / Comp AI / similar) to collect evidence so you don't hire for it. This is the "no army" move: the tool is the compliance team.

---

## What specifically applies to Bcengi

You are a 5-person shop running Claude Code hard across Django/Kotlin/PostGIS/Rust/web with many MCP servers. Concretely:

- **Your biggest real exposure is secrets, not exotic agent attacks.** The MCP-config-leak finding is aimed straight at you (many MCP servers, keys in `.env` files that agents touch). Priorities #1-#4 above are the highest-leverage work and are a half-day of setup: `gitleaks` pre-commit + a CI `gitleaks` gate + push protection on every repo, and a rotate-on-detect reflex.
- **Slopsquatting matters because Dmitry and the team let Claude Code add dependencies freely.** The cheapest strong control is a per-repo rule: **agent installs from lockfile, proposes lockfile diffs, never auto-adds packages**, plus `--ignore-scripts`/`--only-binary` and a Socket.dev CI check. This costs you almost nothing and closes the one attack class that is unique to how you work.
- **Governance-as-code fits your "no heavy process" constraint perfectly.** A committed `.claude/settings.json` per repo (deny secret paths + network, allowlist safe commands, pin approved MCP servers) is enforcement without Jira, without meetings, without a security hire. It is the correct architecture: the control lives with the artifact, self-enforces, and is code-reviewed like anything else. This beats a DEV-Jira "security checklist ticket" that nobody fills in.
- **`/sandbox` on the Linux dev boxes is close to free** and gets you both fewer prompts and real containment. Turn it on.
- **Your file-based memory + KB change what "handover" and audit mean, and you should lean into it.** Instead of a compliance binder, your controls, rotation runbook, approved-MCP list, and "why we deny X" rationale can live as memory files / KB entries that both humans and the agent read. That is your audit trail and your onboarding doc in one, and it is the natural place to record the one-command secret-rotation path and the dependency-cooldown rule so the agent enforces them itself.
- **Review: one human approval to `main` is enough at your size, but make the reviewer's job "design + did-you-run-it," not "does it look clean."** The approval-bias finding is the thing to internalize on a team that ships fast on clean-looking agent diffs. A mandatory smoke-test-the-path step catches more than another pair of eyes on the diff.
- **Skip SOC 2 until the fundraise or a named enterprise customer forces it**, then Security-only scope, Type 1 to unblock, Vanta-style automation so it costs zero headcount.

The whole safe-but-light stack: `gitleaks` (2 hooks), lockfile-only + cooldown + Socket.dev, a committed `.claude/settings.json`, `/sandbox` on, one human approval with a run-it gate, and compliance parked until a deal demands it. No new tool sprawl, no process, no army.

---

## Sources (title + URL)

Secrets:
- [The State of Secrets Sprawl 2026 - GitGuardian](https://blog.gitguardian.com/the-state-of-secrets-sprawl-2026/)
- [29 million leaked secrets in 2025: Why AI agents credentials are out of control - Help Net Security](https://www.helpnetsecurity.com/2026/04/14/gitguardian-ai-agents-credentials-leak/)
- [AI coding assistants twice as likely to leak secrets - SC Media](https://www.scworld.com/news/ai-coding-assistants-twice-as-likely-to-leak-secrets-as-overall-leaks-rise-34)
- [Why 28 million credentials leaked on GitHub in 2025 - Snyk](https://snyk.io/articles/state-of-secrets/)
- [gitleaks/gitleaks (GitHub)](https://github.com/gitleaks/gitleaks)
- [Product showcase: Stop secrets leaking through AI coding tools with GitGuardian ggshield - Help Net Security](https://www.helpnetsecurity.com/2026/04/15/product-showcase-gitguardian-ggshield-ai-hook/)

Slopsquatting / supply chain:
- [Slopsquatting: When AI Agents Hallucinate Malicious Packages - Trend Micro](https://www.trendmicro.com/vinfo/us/security/news/cybercrime-and-digital-threats/slopsquatting-when-ai-agents-hallucinate-malicious-packages)
- [Slopsquatting: AI Code Hallucinations Fuel Supply Chain Attacks - Cloud Security Alliance](https://labs.cloudsecurityalliance.org/research/csa-research-note-slopsquatting-ai-supply-chain-20260419-csa/)
- [Package Security Defenses for AI Agents - Andrew Nesbitt](https://nesbitt.io/2026/04/09/package-security-defenses-for-ai-agents.html)
- [The OX Guide to Version Pinning, Installation Cooldown, and Defense in Depth - OX Security](https://www.ox.security/blog/preventing-future-supply-chain-attacks-the-ox-guide-to-version-pinning-installation-cooldown-and-defense-in-depth/)
- [AI Coding Agents Skip Package Verification, and Attackers Are Exploiting It - TechTimes](https://www.techtimes.com/articles/319457/20260701/ai-coding-agents-skip-package-verification-attackers-are-exploiting-it.htm)

Claude Code security:
- [Security - Claude Code Docs](https://code.claude.com/docs/en/security)
- [Making Claude Code more secure and autonomous with sandboxing - Anthropic](https://www.anthropic.com/engineering/claude-code-sandboxing)
- [Claude Code Security: Top 6 Risks, Controls, and Best Practices - Checkmarx](https://checkmarx.com/learn/ai-security/claude-code-security-top-6-risks-controls-and-best-practices/)
- [Prompt Injection and AI Agent Security Risks: A Claude Code Guide - TrueFoundry](https://www.truefoundry.com/blog/claude-code-prompt-injection)

Review gates for agent code:
- [These Aren't the Reviews You're Looking For: How Humans Review AI-Generated Pull Requests - arXiv](https://arxiv.org/html/2605.02273v1)
- [From Industry Claims to Empirical Reality: An Empirical Study of Code Review Agents - arXiv](https://arxiv.org/pdf/2604.03196)
- [AI Code Review: Can Agents Replace Human Reviewers? - DualMedia](https://www.dualmedia.com/ai-code-review/)

Least-viable compliance:
- [SOC 2 for Startups: The Complete Guide 2026 - Workstreet](https://www.workstreet.com/blog/soc-2-for-startups)
- [An actionable guide to SOC 2 compliance for startups - Vanta](https://www.vanta.com/collection/soc-2/soc-2-for-startups)
- [SOC 2 Checklist for SaaS Startups 2025 - Comp AI](https://www.trycomp.ai/hub/soc-2-checklist-for-saas-startups)

Governance framing:
- [AI Agent Security Cheat Sheet - OWASP](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html)
- [Secure development practices for agentic AI systems - AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-security/best-practices-dev-practices.html)
