# AI-Native SDLC: Which Ceremonies Are Getting Dropped (practitioner briefing, 2025-2026)

## Verdict up front
The consensus across 2025-2026 practitioner writing is not "agile is dead." It is that AI collapses the *execution* half of the loop to near zero, so every ceremony that existed to **coordinate slow human execution** is being gutted, while the ceremonies that exist to **decide, align, and verify** are surviving (and in some cases getting heavier). Concretely: story-point estimation and velocity are the clearest casualties, sprint planning and standups are being compressed or replaced, detailed Jira tickets are being replaced by spec files in the repo, and the backlog is being replaced by a spec index. The single recurring replacement artifact is a **markdown spec (and a spec index) living in the repo, reviewed as a PR diff.**

For a tiny team that already lives in Claude Code with file-based memory, this is almost tailor-made: the "handover" problem that ceremonies solved is mostly solved by your files already.

---

## What is being dropped or gutted, ceremony by ceremony

**Story-point estimation and velocity - effectively dead.** This is the least controversial casualty. The specs.md AI-native SDLC writeup states it flatly: "Story Points: AI execution time bears no relation to human effort estimates" and "Velocity fluctuates wildly based on AI tool usage, not team capability." Practitioners on Scrum.org's own forum report that once devs are on tools like Cursor/Claude Code, per-person throughput jumps so unevenly that point estimates stop correlating with anything. Nobody has a credible replacement metric for effort; teams instead measure business value shipped or just track spec status. Steal this: kill points entirely, do not try to "recalibrate" them.

**Sprint planning - compressed from days to hours, or replaced.** AWS's AI-DLC (announced at re:Invent 2025, now the most-cited formal AI-native methodology) replaces the multi-day planning ceremony with "Mob Elaboration": the whole team validates AI-generated requirements and stories in real time, and "what traditionally takes weeks of back-and-forth between a PM and stakeholders gets done in 2-3 hours." The two-week sprint itself is replaced by "Bolts" (work cycles measured in hours or days) and epics by "Units of Work."

**Daily standups - the weakest survivor.** Multiple sources call standups "status theater" that AI makes redundant because "automated systems could surface [the status] instantly" (specs.md). The counterpoint camp does not defend the *status* function of standups; they defend a coordination function (see "what not to drop"). For a 4-person distributed team, the async-status version of a standup is fully replaceable by a shared spec-index file.

**Detailed Jira tickets - replaced by spec files.** This is the strongest and most repeated theme, backed by the two best practitioner accounts (below). The argument (Thoughtworks, Technology Radar Vol. 32): tickets "conflict, go stale, contradict each other; a developer on a new story can unknowingly violate decisions in an older ticket nobody remembers. The current spec can't go stale this way." Evgeni Rusev reports a team where "after every meeting, [the PM] updated the specs from the transcript, and we never created a Jira ticket again."

**Backlog grooming - replaced by editing the spec / spec index.** Grooming existed to keep a queue of tickets legible. When work lives as version-controlled markdown specs plus an INDEX file, "grooming" becomes editing files in a PR. There is no separate ceremony.

**Retrospectives - the one ceremony people are fighting to keep**, but even here the ritual form (sticky notes, "what went well") is being called "ritual theater." The 2026 reframing: a retro must "produce artifacts that travel," pre-loaded by an AI agent with real signals (merged PRs by size, test failures, cycle time, action items from prior retros).

---

## The replacement that keeps recurring: specs-in-repo + a spec index as the plan

Across every serious source, the same shape emerges, and it is what you should actually steal:

- **A `/specs` folder at repo root, markdown, organized by user workflow, not by ticket** (Rusev). Each spec has stable acceptance-criteria IDs (`AC-1`, `AC-2`).
- **"The diff is the contract."** Requirements change = edit the spec = review the spec diff as a PR. That review *replaces* the detailed ticket description and the planning conversation (Rusev).
- **A `specs/INDEX.md` that is literally the project plan.** Joshua McDonald (running a 4-engineer team on a big project with Claude Code) opens it "every Monday morning" and treats it as the plan: each row is a spec's status, owner, decomposition into mini-specs, what is in flight, what is blocked. That file *is* the standup and the backlog.
- **A `/tasks` folder of markdown files, version-controlled next to `/specs` and code, for teams that dropped Jira entirely** (Rusev, "Model 2").
- **Specs stay short and decompose for parallelism.** McDonald's rule: "Keep the spec under four pages. If it runs longer, the feature should be two specs," and the real test of a good spec is "can two engineers work on different parts in parallel without their pull requests colliding?" Data contracts (schemas, field names, nullability) are written *before* user-visible behavior.

---

## What specifically applies to Bcengi (tiny team, heavy Claude Code, file-based memory)

You are the exact team these methodologies target, and you already have half of it. Opinionated recommendations:

1. **Kill story points and velocity outright.** You do not have an estimation problem to solve; you have an estimation ritual to delete. Your dev signal is "what merged," visible in git.

2. **Replace the "too heavy" DEV Jira project with a `specs/` folder + `specs/INDEX.md` per repo.** This directly fixes your stated pain (Jira feels too heavy) and matches McDonald's exact setup for a same-sized team. The INDEX becomes the async standup. Keep Jira/CEO only for cross-cutting business tracking, not for dev execution. Note: this touches how the team works, so it is a proposal for Dmitry to approve, not something to unilaterally impose.

3. **Adopt the spec-gate hook.** McDonald's single highest-leverage trick: a Claude Code `PreToolUse` hook that blocks writes to source files unless an active spec exists. It "prevents the one where Claude pattern-matches its way into writing code that solves a slightly different problem than the one I asked for." For a team letting agents run long across Django, Kotlin, PostGIS, and Rust repos, this is the cheapest drift-insurance you can install.

4. **Your file-based AI memory changes what "handover" means, which is the whole point.** The ceremonies you are dropping (standup status-sync, ticket detail, planning readouts) mostly existed to transfer context between humans. Your CLAUDE.md + KB + spec files already carry that context to both humans and agents. This is precisely why a tiny Claude-Code-native team can drop more ceremony than a normal team: the persistent-context layer is the replacement. Treat the spec file as the canonical handover unit, and let the KB index it.

5. **Keep decomposition human, and keep it as your one real "planning" act.** McDonald is blunt: "decomposition is the part you cannot automate." His split is roughly 60% of mini-specs to humans, 40% delegated to Claude in isolated git worktrees, and "the forty percent that runs through Claude is what gives the team back its evenings." For your team, the weekly act is not planning poker; it is Dmitry or a tech lead slicing specs into parallel mini-specs and deciding which go to a human vs an agent worktree. Given your `feedback_parallel_agent_fleet` posture (file-disjoint, worktree-isolated), you are already structured for this.

6. **Layer review instead of gate-keeping tickets.** McDonald runs four review layers: hooks on save (lint/imports/tests), `/review` before push, a multi-agent `/ultrareview` before merge, and a `/spec-aware-review` that checks the implementation against the spec, not just for correctness. That last one is the ceremony that actually replaces "acceptance criteria sign-off." Merge often, in small batches, keeping the index current, so two in-flight specs see each other before they collide.

7. **Adopt gradually.** McDonald: "do not try to install all of it at once... The skills folder grows the way a team's runbook grows: slowly, in response to specific frustrations rather than imagined ones." Start with specs + INDEX + the spec-gate hook. That is 80% of the value.

---

## What NOT to drop (the honest counterweight)

The "keep it" camp does not defend status theater; they defend three functions, and they are right for you:

- **Integration coordination.** Even with clean parallel mini-specs, "integration gets messy" (McDonald). Merging often with a live index is the only thing that stops two agent-written branches from colliding. Do not drop this; the INDEX file *is* this.
- **A learning loop.** The retro-defenders' data point: teams that cut the retro "consistently report declining velocity and increasing technical debt over 3 to 4 sprints." You do not need a 60-minute meeting; you need a recurring artifact that captures decisions that travel. Your KB / memory files can be that loop if you actually write to them (which your CLAUDE.md already mandates).
- **Alignment and release decisions.** AI compresses execution, not judgment. As one 2026 piece puts it, ceremonies shift "from coordinating effort to validating delivery signals." The human "verify and approve" checkpoint is explicitly retained even in AWS's aggressive AI-DLC.

Caveat on sources: the strongest, most concrete accounts are the two individual practitioners (McDonald, Rusev) and AWS's formal methodology. Several other hits (specs.md, groovyweb) are thin/marketing-flavored and assert more than they evidence, so I have leaned on them only for the crisp framing quotes and cross-checked the substance against the practitioner accounts.

---

## Notable sources (cited)

- Joshua McDonald, "Running a Small Team on a Big Project: Spec-Driven Development with Claude Code" (Medium, 2026) - the best direct match to your situation. https://joshmcdonald.medium.com/running-a-small-team-on-a-big-project-spec-driven-development-with-claude-code-9a1b97f58551
- Evgeni Rusev, "Spec-Driven Development: A Practical Guide for AI-Accelerated Teams" (2026) - Model 1 (specs + Jira) vs Model 2 (drop Jira, use `/tasks` markdown). https://evgenirusev.com/posts/spec-driven-development-guide/
- AWS, "AI-Driven Development Life Cycle: Reimagining Software Engineering" (AWS DevOps Blog, 2025-2026) - bolts vs sprints, units of work vs epics, mob elaboration/construction. https://aws.amazon.com/blogs/devops/ai-driven-development-life-cycle/
- AWS, "Open-Sourcing Adaptive Workflows for AI-DLC" (AWS DevOps Blog, 2026). https://aws.amazon.com/blogs/devops/open-sourcing-adaptive-workflows-for-ai-driven-development-life-cycle-ai-dlc/
- Thoughtworks, "Spec-driven development: Unpacking one of 2025's key new AI-assisted engineering practices" (Technology Radar Vol. 32 context). https://www.thoughtworks.com/en-us/insights/blog/agile-engineering-practices/spec-driven-development-unpacking-2025-new-engineering-practices
- Deepak Babu Piskala, "Spec-Driven Development: From Code to Contract in the Age of AI Coding Assistants" (arXiv, Jan 2026). https://arxiv.org/html/2602.00180v1
- "Spec-Driven Development in 2026: What It Is, the Tooling, and How Teams Actually Use It" (DEV Community). https://dev.to/krlz/spec-driven-development-in-2026-what-it-is-the-tooling-and-how-teams-actually-use-it-2fk2
- specs.md, "The AI-Native SDLC: Reimagined" - explicit dropped-ceremony list (standups, sprint planning, story points, velocity, two-week sprints). https://specs.md/methodology/sdlc-reimagined
- TechTarget, "How AI is changing Scrum workflows." https://www.techtarget.com/searchapparchitecture/tip/How-AI-is-changing-Scrum-workflows
- echometer, "AI in Agile Software Development: State of the Evidence 2026." https://echometerapp.com/en/ai-in-agile-software-development/
- Counterweight - "Agile Isn't Dead and AI Isn't Killing It Either" (Medium, Jan 2026). https://medium.com/@rethinkyourunderstanding/agile-is-not-dead-fa8531ec3e91
- Counterweight - "Sprint Retrospective 2026: What Most Teams Get Wrong" (retro as an artifact that travels). https://coommit.com/blog/sprint-retrospective-2026-distributed-teams
