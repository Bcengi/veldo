AI-NATIVE ENGINEERING METRICS: BRIEFING FOR A TINY CLAUDE-CODE TEAM

TL;DR VERDICT
Velocity and story points are dead for a team like yours, and not because they are old-fashioned. They are dead because they measure effort/volume, and AI has severed the link between volume and value. Claude Code makes "how many points is this" unanswerable (a task is 4 minutes or 4 hours of agent time, and the human effort is review, not typing). Replace estimation-of-effort with measurement-of-flow-and-outcome. For a 4-dev-plus-CEO shop the entire useful metric set is three numbers plus one habit, all derivable from git, deploy logs, and Jira. Do NOT buy an engineering-intelligence SaaS (Jellyfish/DX/Faros/Swarmia are built for 50-to-5000-dev orgs and would be pure overhead here).

THE PARADOX THE 2025-2026 DATA ACTUALLY SHOWS (this is the whole story)
AI reliably inflates activity and quietly degrades stability. The numbers are remarkably consistent across independent sources:
- DORA 2025: individual output up (+21% tasks completed, +98% PRs merged) but org-level delivery stays FLAT, with +9% bugs per developer and +91% PR review time. The gains get absorbed by review and rework. DORA added a FIFTH metric this year, "rework rate" (how often you push unplanned fixes to prod), precisely to catch this blind spot.
- A widely-cited 2025 stat: PRs merged per person rose ~98% while incidents per PR rose ~243%. AI generates code faster than review and deploy can absorb it.
- DX benchmarks: real median productivity gain is 5-15%, not the 3x-10x vendors claim. Daily AI users merge ~60% more PRs than non-users, but that is throughput, not outcome.
- The METR randomized trial is the single most important counter-signal for a team like yours: experienced devs working in their OWN repos were 19% SLOWER with AI, while believing they were 20% faster. Perception is inverted from reality. This means self-reported "AI saves me time" surveys are worthless as a metric. You must measure the system, not ask people how it feels.
- Code-quality studies (early 2026): >15% of commits from every AI assistant introduce at least one issue, and ~24% of AI-introduced issues survive to the latest revision (accumulating debt).

Implication: any metric that goes UP when you generate more code (LOC, commits, PRs/week, story-point burndown) is now actively misleading. The signal has moved downstream to review load, rework, and defects.

WHAT TO STOP MEASURING
Story points and velocity (effort estimation is meaningless with agents). Lines of code and commit counts (AI inflates freely). PRs-per-developer as a productivity KPI (up 98% while value flat). Any per-person output metric (SPACE and DORA both warn these are gameable and destructive; with AI they are noise). Deployment frequency and lead time read in isolation (they "lie" once AI writes 30-70% of code, per the TianPan/DORA critique). Self-reported time-saved surveys (METR proves the perception gap).

WHAT REPLACES VELOCITY/STORY POINTS (the AI-era metric set)
The consensus framing across DORA 2025 and DX's "Core 4" (speed, effectiveness, quality, impact) is: stop counting what developers produce, measure how value flows through the whole delivery system, and always pair a speed metric with a quality guardrail so improving one cannot silently wreck the other.

1. CYCLE TIME (idea/first-commit to production). This is the best single throughput metric BECAUSE it captures the review+rework overhead that AI shifts downstream. The diagnostic is clean: if AI genuinely helps your system, cycle time drops; if AI is just adding volume, cycle time stays flat or rises even as PR counts explode. This is your replacement for velocity.

2. CHANGE FAILURE RATE + REWORK RATE (the guardrail). Rework rate = share of merges that need an unplanned follow-up fix. This is THE metric for AI-generated code because AI's failure mode is plausible-but-wrong code that ships then needs patching. DORA elite is 0-2% change failure; ~40% of teams are above 16%. For your team, simplest operational definition: "did this merge require an unplanned fix within N days." Track the trend, not the absolute.

3. OUTCOME / IMPACT METRIC (what story points were always a bad proxy for). Core 4's "effectiveness" = how often shipped code actually solves the intended problem; "impact" = correlation between eng output and a business/product KPI. You already have these written into your own rules and should elevate them to the primary success signal: companion cost <$0.10/plan, no query/endpoint >500ms, companion conversion, ship-to-adoption. A feature that ships fast and clean but nobody uses scores zero. This is the metric that matters most and the one AI cannot inflate.

BATCH SIZE (track as a habit, not a KPI). DORA 2025's "small batch discipline" is one of the seven capabilities that separate teams that WIN from AI from teams that drown in it. Big AI-generated diffs are the primary risk vector (they blow up review time and rework). Keep PRs small; watch median diff size drifting up as an early-warning.

WHAT A TINY CLAUDE-CODE TEAM SHOULD ACTUALLY TRACK (opinionated)
For Frontend/Igor/Infra/Docs-eng plus Dmitry, the answer is deliberately minimal:
- THREE system numbers, weekly, no dashboard: (a) median cycle time commit-to-prod, (b) rework/change-failure trend, (c) one product-outcome number per active workstream (latency, cost/plan, conversion). Derive all three from git + deploy history + Jira; a 30-line script beats any SaaS.
- MEASURE THE TEAM, NEVER THE INDIVIDUAL. At n=4 with heavy AI, per-person output is both meaningless and corrosive. The unit of measurement is the repo/system, not the dev.
- KILL ESTIMATION ENTIRELY. Replace planning-poker/points with binary done/not-done plus cycle time. Your Jira DEV project "feels too heavy" precisely because it carries estimation ceremony that AI made obsolete. Strip it to: what is in flight, what shipped, did it need rework, did it move the product number.
- ONE COST SANITY-CHECK, quarterly: net time gain = time saved minus AI/Claude spend (DX's "net time gain per developer"). You are paying real Claude Code money across many repos; a rough "is this obviously worth it" glance is enough, do not over-instrument it.
- Optional lightweight signal if you ever suspect over-reliance: AI-vs-human churn ratio. Heuristic from the field is that if AI code churns >1.5x human code (or >12% at 30 days), your AI share is too high. Probably too heavy to formalize at your size, but useful as a mental model when a repo starts feeling brittle.

THE CLAUDE-CODE + PERSISTENT-MEMORY ANGLE (this genuinely changes what to measure)
DORA 2025 names "AI-accessible internal data" and "healthy data ecosystems" as top capabilities that predict AI success. Your file-based memory + KB IS that capability, already built. This redefines two classic metrics:
- HANDOVER / ONBOARDING metrics (time-to-first-PR, knowledge-transfer time) become close to irrelevant, because context lives in memory/KB and an agent resumes it. The metric worth watching instead is CONTEXT-LOSS INCIDENTS: how often does work stall or a rebuild happen because context was not written to memory/KB. Your own history (the wireless-ADB and CMS-reload memory-miss incidents) shows this is your real failure mode, not slow typing. A tiny team's leverage metric is "did the decision/rule get captured so it does not get re-litigated," not "how fast did the human ramp."
- REVIEW is now the bottleneck and the human's real job. Since AI writes the code and METR shows humans misjudge their own speed, the honest productivity question is "how loaded is review and how much rework leaks past it," which your cycle-time + rework pair already captures.

PRACTICES WORTH STEALING (concrete)
- Adopt DORA's five metrics including rework rate, but read them as a SET, never individually. Deployment frequency alone lies; rework rate is the truth-teller.
- Use DX's Core 4 as the frame and commit to measuring at minimum Speed (cycle time) + Quality (rework/CFR) + one Impact number. That is a complete AI-era scorecard.
- Enforce the "no metric improves at another's expense" rule (velocity = throughput + direction): always ship a speed number bolted to a quality guardrail so a green speed chart cannot hide a rework explosion.
- Lean into DORA's winning capabilities you can control at your scale: small batch discipline, user-centric focus, and AI-accessible internal data (your memory/KB). These three predict AI payoff more than any tool choice.
- Trust instrumented system data over developer sentiment (METR). If you run one survey, make it the DX Developer Experience Index for flow/friction, and treat it as a health signal, not a productivity number.

SOURCES (2025-2026)
- DORA / Google, State of AI-Assisted Software Development 2025, key takeaways: Faros AI, "Key Takeaways from the DORA Report 2025" https://www.faros.ai/blog/key-takeaways-from-the-dora-report-2025
- Rework as the new fifth metric + AI-readiness: Swarmia, "What the 2025 DORA report tells us about AI readiness" https://www.swarmia.com/blog/dora-2025-report-ai-readiness/
- DORA metrics reinterpreted for the AI era (Core 4 context, cycle time as truth-teller): getDX, "DORA metrics: the complete guide to measuring DevOps performance in the AI era" https://getdx.com/blog/dora-metrics/
- Three-layer AI-impact framework (utilization/impact/cost, PR throughput, net time gain, 5-15% real gain): getDX, "How to measure AI performance in software engineering" https://getdx.com/blog/measure-ai-impact/
- Deployment frequency and lead time become misleading when AI writes 30-70% of code: TianPan, "DORA in the Age of AI: When Deployment Frequency Lies" https://tianpan.co/blog/2026-05-07-dora-metrics-ai-era-deployment-frequency-lies
- Why traditional KPIs fail, 18 AI-era metrics beyond velocity: EPAM, "Traditional Engineering KPIs Fail in the AI Era" https://www.epam.com/insights/ai/blogs/ai-engineering-metrics-kpis-to-measure-success
- Activity-vs-outcome, throughput-quality paradox, complexity-adjusted velocity: Oobeya, "Engineering Metrics in the AI Era: A Complete Guide for 2026" https://oobeya.io/blog/engineering-metrics-in-the-ai-era
- AI-native benchmarks (adoption, AI code share, churn ratio 1.5x/12%): Larridin, "Developer Productivity Benchmarks 2026" https://larridin.com/developer-productivity-hub/developer-productivity-benchmarks-2026
- Metric-pairing philosophy (velocity = throughput + direction; no metric degrades another): Kubiya, "Engineering Velocity: Metrics, Bottlenecks & Solutions [2026]" https://www.kubiya.ai/blog/engineering-velocity and Milestone, "Engineering Metrics Benchmarks for 2026" https://mstone.ai/blog/engineering-metrics-benchmarks-high-performing-teams-success/
- Code-quality degradation and AI-tool comparison data (Claude Code agentic completion, defect survival): SitePoint, "GitHub Copilot vs Claude Code: 2026 Accuracy & Speed Analysis" https://www.sitepoint.com/github-copilot-vs-claude-code-accuracy-speed-2026/

Note on the METR "19% slower / felt 20% faster" finding: it is cited secondhand in the DevEx search results above; if you want the primary source before quoting it externally, it is METR's 2025 randomized controlled trial on AI and experienced open-source developer productivity (metr.org). Worth verifying the exact figure directly given how load-bearing it is to the argument.
