# Changing to Veldo: The Human Transition

*The change-management companion: how a company moves every person to Veldo without firing anyone, without pretending the change is small, and without breaking the people it depends on.*

*Version 1.0, 2026-07-16*

## 0. Read this first

This document was researched independently by two frontier models and reconciled; the studies it cites are real and named in the sources section. It exists because of three sentences from the founder that are the design constraints for everything below:

1. **"People do not want to change - this will never change."** Correct, and the program below never assumes otherwise. It is designed for real humans, not for the compliant employees of management literature.
2. **"Without firing people in the process."** Taken as a hard design input, with its economic consequences stated honestly rather than wished away.
3. **"For many it's just hard to do a brand new job - like a muscle that was never used."** The deepest of the three. Most resistance analysis obsesses over motivation; at least half the problem is capability: judging a spec, reading a proof, and rejecting weak evidence are real skills that nobody on the team has exercised yet, including the best engineer in the building. A person can be fully willing and still flail for months, and a program that cannot tell flailing from refusing will damage both. The competence machinery below (the sandbox, private practice, the judgment ladder, the six-week focused plans) exists for exactly this.

One advantage this transition has over every transformation in the literature: Veldo produces receipts. A person's first proven change is visible, concrete, and theirs within days, not quarters. The muscle that was never used gets feedback on every rep.

## 1. The truth first

Veldo is not a tool rollout. It is an occupational redesign.

It removes the activity around which many engineers built competence, status, pleasure, and identity. It substantially dissolves traditional QA and project management. Resistance is not irrational. Some people are protecting status, some are protecting safety, some are grieving a craft, and some correctly see flaws in the new system.

Three conditions cannot coexist indefinitely:

1. Every role must move to Veldo.
2. A person may permanently refuse Veldo and every useful adjacent role.
3. The company will neither terminate the person nor carry idle payroll.

With no firing as the design input, the company must fund redeployment, preserve some legitimate non-Veldo work, or carry the person until voluntary departure. There is no change-management technique that eliminates that economic fact.

The viable endpoint is:

- Agents write ordinary production code.
- Humans still read and understand code, systems, risks, and evidence.
- Humans do not routinely hand-write production changes.
- High-risk surfaces retain human judgment and approval.
- Emergency recovery retains a break-glass path.
- Veldo is promoted based on measured system performance, not faith in AI.

A blanket rule that no human may ever type code, even during a tool outage or catastrophic recovery, is unsafe. The operational rule should be no hand-written production code in the ordinary lane.

## 2. The resistance map

### 2.1 First rule: do not call every objection resistance

A person who exposes a weak test, unsafe agent permission, ambiguous specification, or false proof is doing the new job correctly.

Judge behavior:

- Valid dissent names a risk, supplies evidence, and proposes a test or control.
- Resistance protects the old method regardless of evidence.
- Sabotage hides work, bypasses controls, manufactures failure, or falsifies evidence.

Do not diagnose motives publicly. Address observable behavior privately.

### 2.2 Senior engineer

**What they actually fear**

- Loss of the identity that made them valuable.
- Loss of the flow-state pleasure of coding.
- Status inversion, especially if a junior appears faster with an agent.
- Exposure that their expertise is partly tacit and difficult to express as constraints or evidence.
- Becoming a reviewer of mediocre machine output instead of a builder.
- Deskilling and future unemployability.
- Accountability for code they did not personally construct.
- Replacement after they train the system to embody their knowledge.

**How it presents**

- Quietly hand-writing changes before asking the agent to reproduce them.
- Labeling ordinary work an emergency.
- Choosing pathological tasks for public demonstrations.
- Comparing agent elapsed time with their own typing time while excluding review, testing, and rework.
- Keeping architectural knowledge in their head so the agent predictably fails.
- Overclassifying changes as high or critical risk.
- Producing impossibly detailed specifications that secretly prescribe their own implementation.
- Reviewing agent output so aggressively that nothing can pass.
- Creating a hero incident in which only their manual intervention can save production.
- Saying they support Veldo while continuing to assign manual implementation to others.

**Counter-moves**

- Do not make them compete with the agent at typing.
- Protect pay and level during the conversion year.
- Give them a real successor identity: proof architect, protected-surface owner, failure-model owner, or system risk owner.
- Ask them to convert tacit expertise into executable constraints, threat models, architectural decisions, rollback mechanisms, and tests.
- Compare representative work using specification-to-production time, escaped defects, rework, and human attention. Never run a typing race.
- Give them authority over genuine technical risks, but not an unrestricted veto.
- Require every claimed exception to name the exact Veldo limitation and its expiration condition.
- Publicly celebrate the senior who prevents an unsafe merge or makes a class of failures impossible.
- Have them teach failure patterns, not tool buttons.

### 2.3 Junior engineer

**What they actually fear**

- The learning ladder has disappeared before they climbed it.
- They cannot judge code they would not have known how to write.
- The agent makes output look senior while their understanding remains junior.
- Asking basic questions will reveal that they do not understand the generated system.
- They will become cheap agent operators with no durable expertise.
- Senior reviewers will blame them for accepting bad evidence.

**How it presents**

- Quietly accepting agent output without understanding it.
- Copying generated explanations into proof reports.
- Hiding uncertainty because everyone else appears fluent.
- Asking the agent to make tests pass without investigating why they failed.
- Overproducing specifications and evidence to look diligent.
- Avoiding high-risk work indefinitely.
- Continuing to code privately as a way to learn.
- Becoming dependent on one tool or prompt pattern.
- Freezing when specifications contain ambiguity that a senior would resolve intuitively.

**Counter-moves**

- Explicitly say that being a Veldo novice is expected and not a performance defect.
- Use private practice before public demonstrations.
- Teach code reading, system tracing, failure analysis, test quality, and risk classification.
- Require juniors to predict what the agent will change and what could fail before running it.
- Have them explain generated behavior from the repository, not from the agent's summary.
- Pair them with seniors around evidence and counterexamples, not around keyboard control.
- Give them small but real judgment rights as competence grows.
- Build a visible progression from intent interpretation to evidence judgment to risk ownership.
- Assess with planted flaws and scenario exercises, not prompt speed.

No typing does not mean no code literacy. A junior who never learns to read code, trace state, understand data models, or reason about failure cannot become a trustworthy judge.

### 2.4 QA

**What they actually fear**

- Their current role genuinely disappears.
- "Quality is everyone's job" means nobody owns quality.
- Agents will generate both the defect and the test that overlooks it.
- Their accumulated product intuition will be dismissed as obsolete manual labor.
- They will be offered a cosmetic title with no durable work.
- Once the proof system is built, their transition role will disappear too.

**How it presents**

- Preserving a separate manual QA phase after every gate passes.
- Creating flaky or excessively broad gates that make Veldo look unreliable.
- Waiting until after merge to reveal defects that could have been raised earlier.
- Insisting all behavior needs human testing.
- Rubber-stamping agent evidence because challenging it feels futile.
- Hoarding regression knowledge in private test plans.
- Defining quality as test volume rather than confidence.
- Treating every escaped defect as proof that automation cannot work.

**Counter-moves**

- Say plainly that the traditional QA role is ending.
- Offer a paid trial as quality evidence owner, failure-model owner, exploratory risk owner, or proof-system steward.
- Make them responsible for whether evidence actually proves claims, not for manually repeating checks.
- Use their product intuition to design adversarial scenarios, invariants, production observability, and escaped-defect taxonomy.
- Require each gate to identify the failure it detects, its reliability, and its cost.
- Give them authority to escalate weak proof, but not to recreate a universal manual phase.
- Define the durable portion of the new role by month 6. Do not promise permanent work that exists only during migration.
- Cross-train toward security, compliance, customer risk, operations, or domain ownership if one full-time quality role will not remain.

### 2.5 Product manager

**What they actually fear**

- Specifications will expose that product decisions were previously resolved through implementation conversation.
- Ambiguity that once looked like flexibility will now look like incompetence.
- Engineering will blame product for every failed agent run.
- Repository-native truth will reduce their control over roadmap narratives.
- Continuous flow will remove familiar planning and prioritization rituals.
- Agents may appear capable of drafting product requirements, threatening their role.

**How it presents**

- Producing vague intent and expecting the agent to infer the product decision.
- Moving scope after implementation starts.
- Keeping material decisions in Slack, meetings, or a ticketing system.
- Writing excessive detail to avoid accountability.
- Treating acceptance criteria as a contract weapon against engineering.
- Rejecting technically proven outcomes based on unstated expectations.
- Reintroducing batch planning because continuous decisions feel uncomfortable.
- Blaming Veldo when the specification was never executable.

**Counter-moves**

- Make specification creation a dialogue with an agent and an engineer, not a blank form.
- Teach examples, counterexamples, constraints, unacceptable outcomes, and reversibility.
- Measure specification failure as a system signal, not a PM shame metric.
- Require scope changes to revise the specification and invalidate stale evidence.
- Preserve product authority over intent and tradeoffs.
- Remove responsibility for implementation detail unless it is a genuine constraint.
- Celebrate killing a bad idea early and exposing ambiguity before construction.
- Train PMs to judge whether a proven result serves the stated intent, not just whether boxes were checked.

### 2.6 Project manager

**What they actually fear**

- Veldo explicitly removes much of their current job.
- Repository status and continuous flow eliminate manual reporting and coordination.
- Their relationships and process knowledge will be replaced by automation.
- "Change lead" may be a temporary holding role, not a career.
- They may lose authority because work no longer waits for a coordination meeting.

**How it presents**

- Recreating Jira in Markdown.
- Keeping both old and new status systems "for safety."
- Reintroducing sprints, release trains, standups, and dependency meetings.
- Batching work to make it easier to report.
- Turning the weekly index pass into a long planning ceremony.
- Demanding manual updates that can be derived from repository state.
- Defining success as process compliance rather than flow and outcomes.
- Becoming the unofficial gatekeeper for all Veldo work.

**Counter-moves**

- State honestly that status collection and sprint administration are ending.
- Give them a time-limited transition role, not a fake permanent one.
- Evaluate durable alternatives early: customer implementation, portfolio decisions, vendor management, compliance programs, operations, change enablement, or cross-company dependencies.
- Retain project management only where external coordination is real and cannot be represented by repository state.
- Automatically generate views from the repository.
- Put an expiration date on every parallel tracking system.
- Do not let the project manager own Veldo approval. That creates the bottleneck Veldo is intended to remove.

### 2.7 Designer

**What they actually fear**

- Design quality cannot be fully reduced to executable criteria.
- Agents will produce technically correct but aesthetically poor interfaces.
- Design will be bypassed because implementation is cheap.
- Figma and design critique will lose authority as repository truth expands.
- Their subjective judgment will be treated as anti-automation.
- Faster iteration will increase review load rather than reduce it.

**How it presents**

- Keeping critical decisions only in design files or meetings.
- Issuing late subjective vetoes against already proven changes.
- Refusing to define design constraints because "you know it when you see it."
- Requiring human review for every minor visual change.
- Using pixel perfection as an all-purpose blocking criterion.
- Avoiding generated interfaces entirely after one poor result.
- Allowing agents to infer interaction behavior from static images.

**Counter-moves**

- Preserve a human design-review lane for changes affecting look, feel, accessibility, or user flow.
- Encode design tokens, component rules, accessibility requirements, content standards, screenshots, and interaction examples where machines can use them.
- Separate objective evidence from inherently human judgment.
- Require design review only for named surfaces and change classes.
- Make the designer the owner of user-facing intent and design-system constraints, not a late-stage approver of everything.
- Use agents to generate alternatives, then make human tradeoffs explicit and durable.

### 2.8 Infrastructure engineer

**What they actually fear**

- Agents can cause damage at machine speed.
- Repository access may imply dangerous production access.
- Proof in a test environment may not represent production reality.
- Their operational expertise may be ignored by people impressed with agent speed.
- They will remain accountable for incidents while losing control of implementation.
- Veldo will eliminate the hero role that currently establishes their status.

**How it presents**

- Classifying nearly all infrastructure work as critical.
- Refusing agents the context needed to operate safely.
- Keeping runbooks and environment knowledge outside the repository.
- Preserving manual production changes because automation is "too risky."
- Creating emergency exceptions for routine work.
- Demonstrating one catastrophic hypothetical as a reason to block the entire method.
- Allowing weak test environments so production remains the only meaningful test.
- Taking over incidents manually and failing to backfill proof.

**Counter-moves**

- Start infrastructure last, after ordinary application changes work reliably.
- Use least-privilege agent identities, short-lived credentials, policy as code, dry runs, canaries, and tested rollback.
- Keep production execution separate from code generation.
- Define protected paths precisely. Do not use "infrastructure" as one blanket category.
- Convert operational knowledge into machine-readable runbooks, invariants, and recovery checks.
- Measure emergency-lane use and require backfill within 24 hours.
- Preserve human approval for destructive, access-control, encryption, core-network, and non-reversible changes.
- Give infrastructure experts real authority over resilience and recovery design.

## 3. The research base, applied to Veldo

### 3.1 Established change and learning research

### Kotter

**What it says:** Large changes require a credible case, a guiding coalition, removal of obstacles, visible wins, and reinforcement in the operating system.

**Veldo decision:** The founder does not announce universal adoption and delegate it. The founder forms a three-person conversion cell, removes delivery pressure from the pilot, produces representative wins, and then deletes the old lane. The "win" is not generated code. It is a faster proven change with no quality loss.

### ADKAR

**What it says:** Awareness, desire, knowledge, ability, and reinforcement are different conditions. Information does not create ability, and ability does not create desire.

**Veldo decision:** Diagnose the failure before intervening. Someone who does not understand why Veldo is needed gets business context. Someone who fears replacement gets the employment commitment. Someone who lacks evidence judgment gets coached practice. Someone who can do it but bypasses it gets an accountability conversation.

### Bridges' transition model

**What it says:** People must let go of an old identity, pass through an uncertain neutral zone, and establish a new beginning. The psychological transition lags the formal change.

**Veldo decision:** Publicly acknowledge that hand-coding, traditional QA, and status reporting are ending. Create a protected 6-12 month neutral zone in which awkwardness is not punished. Establish successor identities through real decision rights, not inspirational language.

### Rogers' diffusion of innovations

**What it says:** Adoption spreads through credible peers when an innovation is observable, trialable, compatible enough to test, and demonstrably useful.

**Veldo decision:** Start with volunteers who are trusted by peers, not only AI enthusiasts. Let others observe real proof packages and delivery results. Bring the late majority in after representative evidence exists, but before a permanent two-tier system forms.

### Edmondson's psychological safety

**What it says:** Learning requires the ability to admit uncertainty, errors, and lack of knowledge without interpersonal punishment. Safety is not low standards.

**Veldo decision:** Initial practice is private. Failed agent runs are learning material, not performance evidence. People must be able to say "I cannot tell whether this proof is valid." Falsifying proof, bypassing gates, and attacking colleagues remain accountable behavior.

### Dreyfus skill acquisition

**What it says:** Experts use contextual pattern recognition and intuition, while novices need explicit rules and examples. Expertise in one practice does not automatically transfer to a redesigned practice.

**Veldo decision:** Treat the best senior coder as a Veldo novice without pretending their old expertise is worthless. Start with checklists and worked examples, then move to ambiguous scenarios, risk tradeoffs, and adversarial evidence review. Do not hand everyone a training document and call them trained.

### Self-determination theory

**What it says:** Motivation is stronger when people experience autonomy, competence, and relatedness. Pure control produces minimum compliance and concealed resistance.

**Veldo decision:** The destination is mandatory, but people receive bounded choice over pilot timing, learning format, role trials, and areas of specialization. Competence is built privately. Cohorts and pairing preserve social belonging.

### Loss aversion

**What it says:** People weigh losses more heavily than comparable gains, especially losses of status, mastery, security, and control.

**Veldo decision:** Do not sell hypothetical future productivity while immediately removing current status. Protect base pay and level during conversion. Name what is being lost. Create the successor source of status before removing the old one.

### Identity theory and identity work

**What it says:** Work changes are resisted when they invalidate the story people tell about who they are. People adopt new identities through credible experiments and social recognition.

**Veldo decision:** Give people provisional new identities they can test: proof architect, intent owner, quality evidence owner, protected-surface owner. Public recognition follows real demonstrations of judgment, not title inflation.

### Deliberate practice and cognitive apprenticeship

**What it says:** Expertise grows through repeated work at the edge of ability, rapid feedback, observation of expert reasoning, and progressively reduced scaffolding.

**Veldo decision:** Use short scenarios with planted specification defects, weak evidence, misleading tests, and incorrect risk classifications. Seniors explain their reasoning. Juniors first observe, then perform part of the judgment, then own a complete low-risk decision.

### 3.2 What 2024-2026 AI adoption evidence changes

The evidence is mixed because "AI coding" covers very different activities.

### Controlled coding tasks show potential, not organizational proof

The GitHub Copilot controlled study by Peng and colleagues found participants completed a bounded coding task about 56 percent faster. Later field experiments, including work reported by Cui and colleagues in 2024 across several companies, found increased completed tasks after Copilot access, with larger gains for less experienced developers in some settings.

**Veldo decision:** AI can reduce construction time. That does not establish that autonomous implementation plus autonomous proof improves a mature delivery system. Do not use a toy-task speed result to justify whole-company conversion.

### Local speed can fail to improve delivery

DORA's 2024 research reported positive associations between AI use and several individual-level outcomes, but it also warned that increased AI adoption did not automatically improve delivery throughput or stability. The findings were associative, not a causal verdict on every tool.

**Veldo decision:** Measure specification-to-production time, escaped defects, reversions, proof latency, and recovery. Never declare success because developers report feeling faster or generate more changes.

### Experienced developers can become slower

METR's 2025 randomized study of experienced open-source developers working in repositories they already knew found that the tested AI tools made them about 19 percent slower. Participants expected a speedup and continued to perceive one even when measurement showed a slowdown. The sample and task setting were limited, but the mismatch between perception and measured performance is important.

**Veldo decision:** Do not accept "this feels faster" or "the old way was faster" as evidence. Predefine representative tasks and measure end-to-end performance. Expect some senior experts to experience a real initial slowdown.

### Trust remains substantially lower than usage

Stack Overflow's 2024 and 2025 surveys showed broad use or planned use of AI tools alongside persistent distrust of output accuracy. Adoption and confidence are not the same thing.

**Veldo decision:** Treat skepticism as normal. Veldo must earn confidence through reproducible evidence, independent review, and escaped-defect results. Forced enthusiasm is irrelevant.

### More generated code can create more review and maintenance work

Observational analyses such as GitClear's 2024 reports found patterns consistent with increased code churn and copy-paste behavior during the generative AI period. These studies do not prove AI caused the changes, but they reinforce the possibility that cheap construction increases downstream burden.

**Veldo decision:** Cap change size, require meaningful evidence, and optimize verification. Do not reward code volume, change count, or agent activity.

### Agent benchmarks are not company performance

Benchmark progress on repository tasks demonstrates rapidly improving capability, but benchmarks generally provide cleaner objectives, bounded environments, and objective tests. Real organizations contain contradictory intent, undocumented constraints, production-only behavior, security restrictions, and political tradeoffs.

**Veldo decision:** The company repository and proof system are part of the product. Veldo cannot succeed by purchasing a stronger model while leaving the repository ambiguous.

### There is no strong longitudinal proof of the complete Veldo model

As of the 2024-2026 adoption wave, evidence supports useful AI assistance and rapidly improving agents. It does not yet establish that removing routine human coding across an entire organization is universally superior or safe over multiple years.

**Veldo decision:** Treat Veldo as a falsifiable operating-model hypothesis. Promote it in stages. Keep quality and recovery tripwires. Delay expansion when the proof system is not ready.

### 3.3 The 2026 adoption-wave additions (second research pass)

Independent current-source research adds five findings that change program decisions:

**The adoption trap is now the documented default.** 2026 industry analyses of agentic-coding rollouts converge on one pattern: teams that adopt agents bottom-up feel faster at the keyboard while the delivery system slows, because the bottleneck moves to reviewing, validating, and safely releasing the larger volume of change. The dominant failure is grassroots tool adoption outpacing operating design. **Veldo decision:** this is the strongest argument for Veldo itself, and the program should say so plainly: Veldo is not the risky new thing bolted onto AI adoption; it is the operating design whose absence is what makes AI adoption fail. The company is not adopting agents. It is adopting the system that makes agents safe.

**Willingness and trust are different axes, and only one should be trained.** The large developer surveys through 2025 show usage climbing while trust in output accuracy stays low and even falls. **Veldo decision:** never argue people into trusting agent output; that is the wrong target. Train them to trust the EVIDENCE instead: the gate, the proof, the independent review. Veldo's own premise is that nobody should trust output, which turns the skeptic's instinct from an obstacle into the asset, formalized.

**Adoption becomes sticky once crossed.** By early 2026, studies report most developers refusing to work WITHOUT AI on ordinary tasks. The same population that resisted the on-ramp defends the plateau. **Veldo decision:** the Phase 2 plateau is survivable and temporary; design everything around getting each person THROUGH their first twenty changes, because retention after genuine adoption takes care of itself.

**Re-skilling fatigue is a documented clinical pattern.** 2025-2026 organizational research describes exhaustion from perpetual tool churn: people are not tired of one change, they are tired of changing. **Veldo decision:** consolidate the learning into one program with one endpoint, promise no further methodology change for a defined period after stabilization, and never stack a second transformation on top of this one mid-flight.

**Psychological safety has numbers now.** Half of surveyed workers report worry about AI's workplace impact; a third feel overwhelmed; programs that skip the explicit safety commitment see their training fail to take. The practice of "ethical offboarding" (visible generosity even toward people who eventually leave) measurably deepens trust among those who stay. **Veldo decision:** the public commitment in 4.1 is not decoration; it is the single intervention with the strongest evidence behind it. And how the company treats its hardest transition case will be read by everyone else as the true policy.

### 3.4 The resulting research-backed decisions

1. Volunteers go first because early coercion creates concealment, not competence.
2. The old way remains available only during a defined transition. Permanent parallel systems prevent conversion.
3. Repository clarity and verification come before autonomous implementation.
4. Training documents are reference material, not skill acquisition.
5. Experienced coders need status protection and practice, not lectures about AI.
6. Juniors need a redesigned apprenticeship or the company will destroy its future judgment capacity.
7. Adoption is measured at the delivery-system level, not by tool usage.
8. The founder must remain visibly involved for at least 6 months.
9. The transition takes 9-12 months in a prepared small company. It takes longer if the repository and gates are poor.
10. The first major incident is the real adoption test.

## 4. The program

### 4.1 Make the no-firing commitment precise

### Should it be public?

Yes. Make it public before the first required training, assessment, or pilot.

First:

- Confirm the company can fund 9-12 months of reduced capacity and role transition.
- Align every manager on the exact promise.
- Identify the limits around misconduct, sabotage, and dishonesty.
- Decide whether the promise is time-bounded or absolute.

Then announce it at one company meeting, publish it in writing the same day, and hold individual role-impact conversations during the following week.

### Recommended words

> We are not installing a coding tool. We are changing how work is done, and some current tasks and roles will disappear. I will not insult you by pretending otherwise.
>
> No current employee will lose employment, base pay, or level during the next 12 months because Veldo removes their old tasks or because they are initially slow or unsuccessful at learning the new work. We will provide private practice, coaching, and at least two serious role trials where needed.
>
> You do not have to be excited. You do have to participate in good faith, use Veldo on work declared eligible, expose failures honestly, and never bypass or falsify gates. Evidence-backed criticism is part of the new job. Sabotage and dishonesty are not.
>
> We will judge the method by delivery speed, defects, reversions, recovery, and human attention. If Veldo does not perform safely, we will change the method. We will not change the data to protect the story.

Do not say "AI will not replace anyone." Some tasks and roles are being replaced. Say exactly who is protected, from what, and for how long.

### If the founder means literally no firing, without a time limit

Add this commitment and budget for it:

> Anyone who cannot or does not choose to perform Veldo work will be offered legitimate adjacent or legacy work. They will not retain authority to make a Veldo team use the old method. If suitable work eventually runs out, the company will carry that employment cost until a voluntary transition or natural attrition.

If the company cannot afford that sentence, it cannot honestly promise absolute no firing.

### 4.2 Assign ownership and capacity

For a company with 5-20 engineers, create a temporary conversion cell:

- Founder: sponsor, final policy owner, two hours per week minimum.
- Veldo lead: owns method implementation and removes obstacles.
- Proof lead: owns gates, evidence quality, and escaped-defect learning.
- People lead: owns role conversations, learning plans, and redeployment.

These may be three people with overlapping duties. Do not create a large transformation office.

Capacity rules:

- Reserve 20 percent of engineering capacity for the first 12 weeks.
- Reduce roadmap commitments accordingly.
- Reserve 10 percent through month 6 for gate and repository improvements.
- Give pilot coaches explicit workload relief.
- Do not make people learn Veldo after hours.

If delivery promises remain unchanged, training will be the first thing sacrificed and hidden manual coding will become the actual operating model.

### 4.3 Sequencing and timeline

#### Phase 0: Contract and foundation, weeks 0-4

**Actions**

- Make the public employment and learning commitment.
- Hold a private role-impact conversation with every affected person.
- Record a four-week baseline where possible.
- Map all protected paths and risk classes.
- Make build, test, deployment, rollback, and environment setup reproducible.
- Create the canonical verification command.
- Measure and fix gate flakiness.
- Create the specification template and repository index.
- Build the private sandbox.
- Select 2-4 volunteer pioneers.
- Declare which work is initially eligible.
- Require every manager to accept the transition contract before their team enters the pilot.

**Initial eligible work**

- Reversible low-risk product changes.
- Small standard-risk changes with strong existing tests.
- Documentation and tooling.
- Isolated bug fixes with reproducible failures.
- Test and observability improvements.

**Initially ineligible work**

- Money movement.
- Authentication and authorization.
- Destructive migrations.
- Core infrastructure.
- Irreversible data changes.
- Weakly observed production-only behavior.

**Exit conditions**

- The canonical gate is reliable enough that bypass is not routine.
- Rollback works.
- At least one complete Veldo change has run in the sandbox.
- The volunteers understand the no-firing and no-falsification contract.
- Managers have stopped assigning new manual implementation for pilot-eligible work.

#### Phase 1: Volunteer lighthouse, months 2-3

Use 2-4 volunteers. Include:

- One respected senior or strong mid-level engineer.
- One product or design partner.
- The QA person if one exists.
- One junior when the environment is safe enough.

Do not use only AI hobbyists. Do not begin with the loudest opponent. The first cohort must be credible and capable of learning in public after private practice.

**Actions**

- Run 15-25 representative changes through Veldo.
- Keep them small and reversible.
- Use the complete proof and fresh-context review loop.
- Record every exception.
- Hold private coaching twice weekly.
- Run one sandbox comparison against the old method using end-to-end measures. Do not duplicate every production task.
- Demonstrate proof packages and reviewer catches, not generated code.
- Fix proof-system defects immediately.

**Promotion conditions**

- At least 20 representative changes or four stable weeks.
- Escaped defects and reversions are no worse than baseline.
- No unresolved severe incident attributable to a known gate bypass.
- At least two people other than the Veldo lead can independently run and judge the lifecycle.
- Gate flakiness is below the point where bypass feels rational.
- The team has completed one rollback or recovery drill.
- Participants report that they can admit uncertainty without punishment.

A productivity gain is not required yet. Safety and repeatability are.

#### Phase 2: Cohort expansion, months 4-5

Bring people in cohorts of 2-3. The next cohort should include:

- A pragmatic peer from the early majority.
- A respectful skeptic.
- A manager whose behavior will influence others.
- People from a second product area.

This is when laggards begin, not at the final deadline. By then they have peer evidence, a working sandbox, and local coaches.

**Actions**

- Move 30-50 percent of eligible ordinary work to Veldo.
- Run high-risk scenarios in the sandbox without production execution.
- Assign one skeptic a formal red-team role.
- Begin individual role trials for QA and project management.
- Remove duplicate status reporting.
- Introduce team-level metrics.
- Rotate pairing so champions do not become permanent operators.
- Require manual exceptions to record reason, owner, and expiration date.

Expect the honeymoon to end here. Easy tasks have been exhausted, proof gates accumulate, and agents meet ambiguous legacy behavior. This plateau is normal.

#### Phase 3: Veldo becomes the default, months 6-8

**Actions**

- All ordinary reversible production work enters the Veldo lane by default.
- Agents write all ordinary production changes.
- Humans own intent, evidence judgment, exceptions, and protected approvals.
- High-risk changes use stronger evidence and human lanes.
- Manual coding is limited to the declared emergency lane.
- Every emergency receives specification, proof, and independent review within 24 hours.
- Old sprint and status processes become read-only or are removed.
- Every remaining non-Veldo area has a named reason and sunset condition.
- Managers are held accountable for preventing quiet reversion.

The target date for ending hand-written ordinary production code should be near the end of this phase. If promotion conditions are not met, move the date. Do not fake readiness to protect a date.

#### Phase 4: Stabilization and role settlement, months 9-12

**Actions**

- Settle permanent roles and redeployments.
- Remove transition-only duties.
- Enable automatic merge for proven reversible work.
- Audit protected paths and agent permissions.
- Test recovery from agent, model, CI, and vendor outages.
- Review whether junior development is producing real judgment.
- Compare rolling system results with the original baseline.
- Retire individual exceptions that have become permanent without justification.
- Reduce temporary adoption rituals.

A well-prepared company may reach the ordinary-code endpoint in 6-9 months. A company with weak tests, undocumented architecture, or fragile deployment should expect 12-18 months.

### 4.4 Design the sandbox for safe incompetence

The sandbox should have:

- A fork or synthetic service with no production credentials.
- No customer data.
- The same specification, proof, and review structure as production.
- Seed tasks based on actual past defects and changes.
- Planted ambiguous specifications.
- Tests that pass while behavior remains wrong.
- Misleading proof packages.
- Incorrect risk classifications.
- Rollback and incident scenarios.
- A reset button.
- No raw practice telemetry in performance reviews.

Give each person two 60-90 minute practice blocks per week for 8 weeks.

### Why initial practice should be private

Public novice performance creates evaluation anxiety, particularly for high-status experts. People then optimize for appearing competent:

- They conceal failed runs.
- They copy others' prompts.
- They avoid hard tasks.
- They overprepare a polished demo.
- They decline to ask basic questions.

Private practice allows genuine error. Public learning begins later with selected artifacts and the learner's consent.

Raw practice activity stays private. Competence is assessed separately through a short, private scenario exercise and real-work observation.

### 4.5 Use a judgment competency ladder

Do not certify people based on tool usage.

### Level 1: Intent recognition

The person can distinguish desired outcome, implementation suggestion, constraint, and unstated assumption.

### Level 2: Specification judgment

The person can identify ambiguity, missing edge cases, non-testable criteria, excessive scope, and required human decisions.

### Level 3: Evidence judgment

The person can map each criterion to evidence, detect superficial tests, reproduce results, and identify what remains unproven.

### Level 4: Risk and reversibility judgment

The person can classify risk, explain blast radius, require an appropriate rollback, and recognize when human approval is needed.

### Level 5: Proof-system improvement

The person can turn recurring failures into durable repository constraints, improve gate reliability, and coach others.

A practical assessment should ask the person to:

- Find defects in three specifications.
- Reject a plausible but inadequate proof package.
- Identify a planted regression.
- Classify a change's risk.
- Decide whether to merge, fail, or escalate.
- Explain the decision without relying on the agent's summary.

### 4.6 Redesign pairing and apprenticeship

Traditional driver-navigator pairing assumes a human is constructing code. Replace it with two forms.

### Intent pairing

One person owns the desired outcome. The other acts as constraint and ambiguity challenger.

Typical pairings:

- PM and engineer.
- Designer and engineer.
- Customer expert and domain engineer.
- Infra owner and application engineer.

### Evidence pairing

One person maps criteria to evidence. The other acts as skeptic and tries to falsify the claim.

Typical pairings:

- Junior prepares the criterion-to-evidence map.
- Senior searches for missing failure modes.
- QA challenges test meaning.
- Infra or security joins for protected surfaces.

Rotate these roles. A junior must learn to challenge, not only prepare material for senior approval.

### How juniors grow when nobody types

Use this progression:

1. Predict the affected components before the agent acts.
2. Read the implementation plan and identify missing context.
3. Trace one changed behavior through the code and data model.
4. Explain why each test is meaningful.
5. Create counterexamples and fault injections.
6. Compare two agent-generated approaches and judge the tradeoff.
7. Investigate one failed gate without asking the agent to fix it immediately.
8. Follow production behavior after merge.
9. Participate in an incident and convert the lesson into a durable constraint.
10. Own low-risk merge judgment under supervision.

Juniors should read substantial code even if they do not write production code.

### How seniors convert mastery

A senior's new apprenticeship is not "learn prompting." It is:

- Articulate tacit architectural constraints.
- Define failure models and invariants.
- Judge whether tests establish behavior.
- Design reversibility.
- Separate low-risk automation from protected judgment.
- Improve observability.
- Coach reasoning.
- Diagnose whether a failure came from intent, context, construction, proof, or review.

This gives the best coder a harder and more consequential mastery path, rather than pretending agent operation is equivalent to their old craft.

### 4.7 Change incentives and status

### Protect during conversion

- Base pay protected for 12 months.
- Level protected for 12 months.
- No performance penalty for sandbox failures.
- No promotion advantage based on agent volume or tool usage.
- No title downgrade disguised as role modernization.

### Celebrate the new scarce work

Celebrate:

- An ambiguity caught before construction.
- A weak proof rejected.
- A dangerous risk escalation.
- A rollback made reliable.
- A flaky gate repaired.
- A production-only assumption made observable.
- Tacit knowledge converted into a repository constraint.
- A junior who correctly challenges a senior or an agent.
- A reviewer catch that prevents an escaped defect.
- A small change that avoids unnecessary complexity.

Do not celebrate:

- Lines generated.
- Agent sessions.
- Number of specifications.
- Prompt cleverness.
- Raw merge count.
- Heroic emergency bypasses.
- Speed without quality.

### Prevent status collapse for the best typist

- Acknowledge the loss privately and publicly.
- Give them ownership of a real protected surface.
- Make their judgment visible in high-consequence decisions.
- Ask them to create the team's failure taxonomy.
- Give them teaching status based on reasoning, not nostalgia.
- Do not force them into a live prompting contest with a junior.
- Do not call reluctance a lack of growth mindset.

### 4.8 Measure without surveillance

### Team-level scorecard

Use rolling four-week measures:

- Specification-to-production time.
- Proof latency, including the slowest 10 percent.
- First-pass proof rate.
- Escaped defect rate, severity weighted.
- Reversion or urgent correction rate.
- Mean recovery time.
- Specification failure rate.
- Agent review catch rate.
- Emergency-lane use.
- Human minutes per shipped change.
- Percentage of eligible ordinary changes completed through Veldo.
- Verification investment.
- Three-item anonymous pulse: role clarity, safety admitting uncertainty, and workload sustainability.

Interpret metrics together. A reduction in human minutes is not success if escaped defects increase.

### Rules against surveillance

- No individual token, prompt, session, or agent-use dashboard.
- No ranking by Veldo adoption.
- No productivity score inferred from commits or changes.
- No use of sandbox telemetry in performance reviews.
- No publication of subgroup results with fewer than five people.
- Audit logs may exist for security and incident reconstruction, but not as adoption scores.
- Individual capability is assessed privately through work samples and coaching.

Individual accountability still exists. A manager may discuss a person's actual specifications, reviews, bypasses, or decisions. What is prohibited is converting machine activity traces into a proxy for value.

Individual dashboards backfire because people optimize visible activity, conceal uncertainty, and route around the system. Veldo needs honest failure signals more than it needs compliance screenshots.

### 4.9 Temporary transition rituals

Veldo's steady state should remain light. During the transition, use fixed-term rituals with explicit sunset dates.

### Weekly index pass

Keep the normal 15-20 minute repository index review.

### Proof clinic

For the first 12 weeks, hold a 30-minute weekly clinic:

- One ambiguous specification.
- One strong or weak proof package.
- One independent-review catch.
- One gate improvement.

Show reasoning, not agent theatrics. End the recurring clinic after 12 weeks unless the team explicitly renews it for a defined problem.

### Conversion office hours

Offer two optional private blocks per week during the first 8-12 weeks.

### Incident-to-constraint review

After an escaped defect or emergency, ask:

- What claim was false?
- Why did the specification, proof, or review miss it?
- What durable constraint will prevent the class of failure?
- Was the emergency lane used correctly?

### What replaces the emotional value of shipping by hand

Create a lightweight "claim made safe" recognition:

- The intent that became real.
- The strongest evidence.
- The uncertainty that was removed.
- The reviewer catch.
- The repository improvement left behind.

The identity shifts from "I typed this system into existence" to "I made this change safe enough to become reality."

### 4.10 The path for someone who cannot or will not convert

Treat inability and refusal differently.

### For someone trying but unable

1. Identify the missing subskill: domain knowledge, decomposition, specification judgment, evidence literacy, risk judgment, or tool operation.
2. Give a focused six-week supported plan.
3. Assess privately with scenarios and real low-risk work.
4. If progress remains inadequate, offer at least two adjacent role trials of 6-8 weeks each.
5. Settle into a useful role without presenting it as failure.

Potential roles include:

- Customer discovery and domain research.
- Customer implementation.
- Support escalation and incident coordination.
- Security or compliance evidence.
- Repository stewardship.
- Observability and operational risk.
- Design review.
- Protected-surface approval.
- Quality risk and failure modeling.
- Vendor and integration management.
- Legacy-system stewardship with an explicit sunset.
- Change coaching, if the person has genuine teaching ability.

### For someone who will not convert

Give choices, not a veto:

- Participate in a supported Veldo trial.
- Move to a legitimate non-Veldo human-judgment role.
- Own a defined legacy or external coordination area.
- Accept a voluntary paid transition if they want to leave.

They may not:

- Keep managing a Veldo team while privately reversing the method.
- Maintain a shadow manual coding lane for ordinary work.
- Label all their preferred work an exception.
- Instruct others to bypass gates.
- Falsify proof or adoption results.

Under an absolute no-firing policy, a persistent refuser is redeployed or carried. Their decision rights move away from Veldo work even if employment continues.

### When not converting is legitimate

- Human design judgment.
- User research.
- Product strategy.
- Customer and domain decisions.
- Legal or regulatory approval.
- Security risk acceptance.
- Incident command.
- Protected infrastructure approval.
- Hardware or physical validation.
- Vendor and customer coordination.
- Legacy maintenance that cannot yet enter Veldo.
- Work during a declared emergency.

Not converting is not legitimate when it means a permanent manual coding exception for ordinary reversible production work.

## 5. The hard cases

### 5.1 The best senior engineer quietly refuses

### Wrong move

- Shame them in front of the team.
- Threaten their title.
- Run a public typing-versus-agent race.
- Let them retain a secret manual exception because they are valuable.
- Accuse them of being afraid of technology.
- Promote a junior over them based on visible agent speed.

### Right move

Use observable facts. Acknowledge identity loss. Offer status continuity through harder judgment work. Require a bounded trial and remove the secret exception.

### Founder script

> I want to talk about a pattern, not guess at your motives. The last six eligible changes assigned to you were either done manually first or classified as exceptions. That means the operating model is not actually changing in your area.
>
> You are our strongest coder. I also understand that I am asking you to stop doing the activity that built your reputation and that you probably enjoy most. I am not going to call that trivial.
>
> I am not asking you to become a prompt operator. I need your expertise applied to architecture, failure modes, proof quality, and protected decisions. That is at least as important as construction, and I will preserve your pay and level while we test the new role.
>
> I am asking for a six-week good-faith trial on agreed work. We will measure complete delivery, not agent speed. You may challenge Veldo with evidence. You may not maintain an invisible manual lane. If this role is not a fit after a real trial, we will test adjacent roles without firing you for struggling. Can you agree to the trial and to stop the hidden exception?

### 5.2 The QA person whose role dissolved

### Wrong move

- Say "quality is everyone's job" and offer no role.
- Rename them "quality architect" while leaving them with the same manual regression queue.
- Pretend their role did not disappear.
- Ask them to train the system and then eliminate them.
- Make them the human approver for every change.

### Right move

Name the ending. Protect employment and pay. Offer a real trial with concrete accountabilities and define the durable destination early.

### Founder script

> Your current job as the separate person who manually checks work after engineering is ending. I will not pretend this is only a tool change or tell you that nothing is being lost.
>
> The company still needs the judgment you built: where systems fail, what users do unexpectedly, which evidence is weak, and which defects matter. I want to offer you a 90-day paid trial as quality evidence owner. Your work would be to challenge proof, design failure models, improve observability, classify escaped defects, and turn recurring failures into durable gates.
>
> This is not a promise that transition work will remain a full-time job forever. By month 6 we will decide which part is durable and whether it should be combined with security, compliance, operations, or customer risk. Your pay and employment are protected during that process. You do not have to pretend the loss is good news.

### 5.3 The person who tries but cannot judge specifications or evidence

### Wrong move

- Give them more documentation.
- Tell them to prompt better.
- Fail them in a public demonstration.
- Assume lack of intelligence.
- Leave them approving work they cannot evaluate.
- Manufacture a meaningless role to avoid a hard conversation.

### Right move

Recognize effort. Diagnose the missing capability. Reduce decision scope. Try adjacent work that uses their actual strengths.

### Founder script

> I can see that you have made a real effort. This is not a conversation about attitude or character.
>
> The current gap is specific: you can operate the workflow, but you are not yet reliably identifying ambiguous criteria or weak evidence. That means I cannot put you in an independent merge-judgment role today.
>
> We are going to separate the skills. For six weeks, you will work on criterion-to-evidence mapping with a senior checking the final decision. Then we will reassess privately using real examples.
>
> If the judgment still does not become reliable, we will not keep forcing the same job until you look incompetent. We will test two adjacent roles that use your strengths. Your employment and pay remain protected during those trials. The objective is useful work and dignity, not making everyone fit the same mold.

### 5.4 The vocal cynic infecting others

### Wrong move

- Silence them.
- Call all criticism negativity.
- Debate them endlessly in company meetings.
- Let them make unsupported claims without challenge.
- Give them informal permission to ridicule learners.
- Exclude them completely and turn them into a martyr.

### Right move

Convert criticism into a bounded red-team charter. Set conduct boundaries. Require evidence and proposed tests.

### Founder script

> Some of your concerns may be correct. Veldo can create false confidence, weak tests, and more code than we can safely review. I want those risks exposed.
>
> From now on, criticism needs to take one of three forms: a reproducible failure, a named risk with a proposed control, or a representative comparison. I am giving you a formal red-team role for the next six weeks to produce that evidence.
>
> You may attack the method as hard as the evidence supports. You may not ridicule people learning it, spread claims you will not test, or tell others to bypass the agreed process. If you find a real failure, I will stop or change the rollout. If you refuse the red-team structure and continue undermining colleagues, that becomes a conduct problem rather than dissent.

### 5.5 The manager who converts the team back when the founder looks away

### Wrong move

- Add more activity dashboards.
- Quietly bypass the manager.
- Let the team operate two systems indefinitely.
- Accept "my team is different" without evidence.
- Make the manager a Veldo sponsor in title while rewarding old delivery behavior.

### Right move

Treat operating-model sponsorship as a condition of managing the team. Offer redeployment without preserving people-management authority.

### Founder script

> We agreed that eligible work in your team would use Veldo. In the last month, you reassigned four changes to manual implementation and restarted the old status process. This is not a training gap. It is a reversal of the company operating model.
>
> You may challenge the model with evidence and request specific exceptions. You may not quietly convert the team back.
>
> I need a clear choice. You can manage the team through Veldo with coaching and the agreed safeguards, or you can move into a domain, customer, or risk role with your pay protected during the transition. What you cannot do is keep management authority while running a different development system when I am not present.
>
> I need your decision by Friday. Until then, no new manual exceptions may be created without written risk justification.

## 6. Failure modes of the program itself

### 6.1 Going too fast

**How it dies:** The founder declares a company-wide deadline before the repository, gates, and people are ready. Defects rise, then everyone concludes Veldo is reckless.

**Tripwire:** Escaped defects or reversions exceed baseline for two rolling four-week periods, or emergency-lane use exceeds 5 percent of eligible changes for two weeks.

**Response:** Stop expansion. Keep the current cohort. Repair specifications, gates, or observability before resuming.

### 6.2 Going too slowly

**How it dies:** The pilot remains optional for months. The old system continues to receive the important work. Veldo becomes a side project.

**Tripwire:** After month 3, fewer than 20 representative changes have shipped, or more than half of eligible work still enters the old lane without recorded exceptions.

**Response:** Name eligible work as Veldo-default and put expiration dates on exceptions.

### 6.3 Champions burn out

**How it dies:** Two enthusiasts become the agent operators, help desk, reviewers, and change therapists for everyone else.

**Tripwire:** A champion spends more than 25 percent of their time supporting others for three consecutive weeks, or the same two people review more than 70 percent of Veldo changes.

**Response:** Reduce delivery load, rotate duties, train the next cohort, and cap office hours.

### 6.4 The founder's attention moves on

**How it dies:** Managers learn that the new method is optional once the announcement energy fades.

**Tripwire:** The founder misses two consecutive transition reviews, leaves blockers unresolved for more than seven days, or tolerates a senior exception not available to others.

**Response:** Recommit visibly or pause expansion. A delegated founder mandate without founder attention is not a mandate.

### 6.5 A converted and unconverted caste forms

**How it dies:** Early adopters receive prestige, access, and promotions. Others are treated as obsolete. People conceal difficulty to avoid joining the lower caste.

**Tripwire:** Jokes about "legacy people," promotion language tied to AI enthusiasm, or desirable assignments restricted to the pioneer group.

**Response:** Enforce pay protection, rotate visible work, recognize multiple human-judgment roles, and bring the next cohort in promptly.

### 6.6 Metrics theater

**How it dies:** Specification counts, merge counts, first-pass rates, or human minutes improve while quality deteriorates.

**Tripwire:** First-pass proof approaches 100 percent, reviewer catch rate approaches zero, or human minutes fall while reversions and defects rise.

**Response:** Audit a random sample of proof packages. Add adversarial checks. Remove the gamed metric from incentives.

### 6.7 Proof theater

**How it dies:** Agents produce polished reports that restate claims without establishing them. Humans stop checking because everything looks complete.

**Tripwire:** Reviewers cannot reproduce evidence, tests never fail before fixes, or reviewers cannot explain why the evidence proves the criterion.

**Response:** Require criterion-to-evidence mapping, reproducibility, planted-defect exercises, and periodic independent audits.

### 6.8 The old lane survives underground

**How it dies:** Humans write code first, ask the agent to restate it, or label routine work as emergency work.

**Tripwire:** Emergency use rises, unexplained local changes appear before agent runs, or the same person repeatedly requests exceptions.

**Response:** Discuss the behavior privately, simplify legitimate friction, and enforce expiration dates. Do not create individual activity surveillance.

### 6.9 The pilot is built from toy work

**How it dies:** Documentation and copy changes look spectacular, then the method collapses on real product behavior.

**Tripwire:** More than half the pilot consists of low-complexity mechanical work, or no production-relevant standard-risk change has completed by the end of month 3.

**Response:** Add representative legacy, integration, UI, and production-observability work before expansion.

### 6.10 Managers are exempted

**How it dies:** Individual contributors change while managers continue rewarding old behavior and planning through the old system.

**Tripwire:** Manual status requests, sprint commitments, or typing-based praise continue after the relevant team enters Veldo.

**Response:** Require manager conversion before team conversion. Redeploy managers who will not sponsor the operating model.

### 6.11 Junior development becomes passive observation

**How it dies:** Juniors watch agents and seniors make every consequential decision. Output rises while human judgment capacity decays.

**Tripwire:** After three months, juniors cannot independently reject a weak proof package, explain a changed data path, or own a low-risk decision.

**Response:** Reduce agent throughput if necessary and restore deliberate apprenticeship, prediction, explanation, and progressively delegated judgment.

### 6.12 The no-firing promise loses credibility

**How it dies:** The first struggling person receives a surprise poor-performance label or quiet pay reduction.

**Tripwire:** Performance documentation begins citing adoption speed, prompt activity, or sandbox failure during the protected period.

**Response:** Stop the action. Separate misconduct from learning difficulty. Honor the written commitment or publicly admit it has been broken.

### 6.13 Veldo becomes a religion

**How it dies:** Evidence against the method is treated as disloyalty. Metrics are reinterpreted to preserve the founder's decision.

**Tripwire:** No pilot result is considered capable of delaying expansion, or valid critics are labeled resistant without a test.

**Response:** Predeclare stop conditions and give a skeptic authority to trigger review when they are met.

## 7. What never to do

- Never call this merely a tool rollout.
- Never promise that no role will disappear.
- Never promise no firing unless the company can fund the promise.
- Never remove manual implementation before repository context and proof gates work.
- Never use public prompting contests.
- Never compare typing speed with agent generation speed.
- Never rank people by AI activity.
- Never use individual adoption dashboards.
- Never use sandbox failure in performance reviews.
- Never make the best coder feel deliberately humiliated.
- Never tell QA that nothing important is changing.
- Never rename a dissolved role without defining durable work.
- Never let a resistant manager keep people-management authority over a Veldo team.
- Never leave juniors to learn by watching an agent.
- Never reward code volume or merge count.
- Never treat agent-generated tests as independent proof by default.
- Never let implementation and review share the same unchallenged context.
- Never let temporary manual exceptions become permanent through silence.
- Never use production deadlines as the primary training environment.
- Never punish someone for saying, "I cannot tell whether this is proven."
- Never confuse psychological safety with freedom to sabotage.
- Never confuse skepticism with sabotage.
- Never let the founder disappear after the announcement.
- Never force the adoption date when the safety tripwires say stop.
- Never claim that Veldo has been proven simply because current agents are impressive.

The founder's core job is not persuading everyone to love Veldo. It is creating a system in which people can lose an old professional identity without losing dignity, income, or belonging, while making honest participation and the new operating boundary non-negotiable.

## 8. Sources

Established research applied in section 3.1: Kotter (Leading Change); Prosci ADKAR; Bridges (Managing Transitions); Rogers (Diffusion of Innovations); Edmondson (psychological safety, The Fearless Organization); the Dreyfus skill-acquisition model; Deci and Ryan (self-determination theory); Kahneman and Tversky (loss aversion); the identity-work literature.

Empirical studies applied in section 3.2: Peng et al. (2023), GitHub Copilot controlled experiment (about 56 percent faster on a bounded task); Cui et al. (2024), field experiments across multiple firms; the DORA 2024 report (AI adoption versus delivery throughput and stability); METR (2025), randomized study of experienced developers (a measured slowdown of about 19 percent against a perceived speedup); Stack Overflow Developer Surveys 2024-2025 (the usage-trust gap); GitClear (2024), code-churn analyses.

Current-source layer in section 3.3 (2026 web research): industry analyses of agentic-coding operating models and the adoption trap (Augment Code, d4b.dev, CodePick, 2026); the Anthropic 2026 Agentic Coding Trends report; the study of Microsoft's early-2026 CLI coding-agent rollout (arXiv); Stack Overflow's 2025 survey retrospective ("willing but reluctant"); the 2026 METR finding on developers refusing to work without AI (TechCrunch, May 2026); re-skilling-fatigue research (PMC, 2026); KPMG and BCG upskilling-program analyses; Forbes and CIO coverage of AI-upskilling failure modes.

## Document History

Minor versions add, clarify, or extend; major versions restructure or break compatibility with existing practice.

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-07-16 | Initial document: two-model research reconciled (the resistance map, the applied research base with the 2026 layer, the funded no-firing program, hard-case scripts, thirteen program failure modes with tripwires) |
