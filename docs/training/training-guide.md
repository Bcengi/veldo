# The Veldo Training Guide

*The map of the training series: who transforms, who dissolves, what everyone learns first, and how people grow when nobody types.*

*Version 1.2, 2026-07-16*

## 1. What this series is for

Veldo changes what humans do: agents own construction and proof; humans own intent and judgment. Every role in the building either transforms or dissolves, and pretending otherwise would waste everyone's time. This guide is the map; each role has its own training document with the concrete day, the exact loop moments, a curriculum with sandbox exercises, the ways that role accidentally breaks Veldo, and the milestones that say you have arrived.

The goal, stated the way the founder stated it: get to the point where human engineers who really want to type code stop typing code, because their judgment is worth more than their typing.

One boundary rule shared by every role: humans do not type implementation code, tests, configuration, or specs during ordinary work; agents do, including the Markdown and YAML (hand-writing a spec file is still mechanical construction). Humans read everything, judge everything, and direct everything. The emergency lane is the one exception, and it backfills.

## 2. The role map

| Today's role | Verdict | Becomes | Training document |
|---|---|---|---|
| Product Manager | Transformed, biggest gain | Product Intent Owner: the most leveraged human in the building | product-manager.md |
| Architect | Transformed | Architecture and Reversibility Owner: the gate is the architecture | architect.md |
| Backend Developer | Absorbed | Product Systems Engineer (systems judgment domain) | backend-developer.md |
| Web Developer | Absorbed | Product Systems Engineer (browser + design contract domain) | web-developer.md |
| Mobile Developer | Absorbed | Product Systems Engineer (lifecycle + irreversibility domain) | mobile-developer.md |
| Infrastructure Engineer | Transformed | Platform Reliability Engineer: substrate, gate runtime, recovery | infrastructure-engineer.md |
| QA Engineer | Dissolved as a separate phase; reborn | Verification Engineer: the proof system as a product | qa-verification-engineer.md |
| Project Manager | Coordination machinery dissolved; the judgment half is conditional | Product Operations (load-bearing until the planning layer proves it can carry project management - an explicit Veldo 1.0 acceptance test), or Product Intent, or outward-facing roles | project-manager.md |
| Designer | Transformed | Design Intent and Review Owner: the mock is a contract, the verdict is a file | designer.md |

**Roles that dissolve, stated plainly - with one honest condition:** dedicated manual QA does not exist under Veldo, and the project manager's coordination MACHINERY (sprints, status collection, handoffs) does not either. But the project-management JUDGMENT - keeping a five-screen, hundred-permutation feature coherent, noticing drift, sequencing under change - dissolves only when the planning layer PROVES it can carry that judgment with receipts. Until that proof exists, the Product Operations hat is load-bearing, not vestigial, and the claim stays conditional. The founder's phrasing is the standard: unless AI can prove it can project manage, declaring the role dead is a stretch. The sprint machinery, status collection, handoffs, and manual test phases those roles coordinated are deleted by the method itself, not reassigned. The PEOPLE do not dissolve: their documents name real destinations, and the change-management document owns how the company gets everyone there without casualties.

**Roles that appear:** Verification Engineer (from QA's strongest practitioners; the highest-leverage engineering function in a method whose bottleneck is verification) and a fractional Security and Trust Owner (a review lane for auth, secrets, sensitive data, and regulatory surfaces: at our scale a hat worn by a senior engineer, becoming a role only when volume demands).

**The absorption, explained once:** backend, web, and mobile stop being separate job families because implementation throughput stopped being the scarce thing. What remains scarce is domain judgment, so the three converge into Product Systems Engineer with different judgment domains: systems and data, the browser and the design contract, the device and its irreversibility. Specialist knowledge stays; specialist typing ends.

**Companion modules (topic, not role).** Beside the role documents, the series carries topic modules that more than one role draws on. The first is *The Planning Layer in Veldo* (planning-layer.md): how a whole product increment is driven through Product Plans, the work DAG, and the ready frontier. It is the product-intent owner's second half and it is what the Product Operations hat leans on, so it is read by whoever holds either.

## 3. The shared core (everyone, before any specialization)

Every person, regardless of role, completes the same short core, because Veldo runs on a shared literacy:

1. **The loop and the boundary.** Intent to spec to implementation to proof to review to merge; what humans own; what agents own; why fluent agent output is not evidence.
2. **Repository truth.** Where specs, proofs, verdicts, policy, and the index live; why chat and memory are not records.
3. **Spec literacy.** Reading a specification critically: are these criteria observable, gameable, complete on the ugly paths?
4. **Evidence judgment.** Reading a proof manifest and a verdict; the difference between a test that proves and a test that executes; letter versus intent.
5. **Risk and lanes.** The tiers, the protected paths, raise-never-lower, when a human must judge, and why ordinary green merges without anyone.
6. **The rituals that remain.** The weekly index pass, the emergency lane and its backfill, the receipts.

**The core capstone (one sandbox afternoon, as a team):** an ambiguous bug report, a misleading passing test, a protected path, and a simulated incident. The team takes the bug from intake through reproduction, spec, implementation, catching the planted test, review, merge, and the incident through the emergency lane with backfill, without any human editing a file by hand. Passing the capstone is the adoption gate for a team.

## 4. Growing seniors when nobody types (the apprenticeship problem)

Typing was never the teacher; consequences were. Traditional coding bundled prediction, failure, and feedback into the act of construction, and removing construction without replacing the learning loop would stop the company from ever producing another senior. The replacement is explicit:

**Stage 1 - Repository literacy.** The apprentice learns to read everything: specs, diffs, schemas, proofs, verdicts, incidents. No ownership yet. Reading code remains mandatory forever; a company whose humans stop reading code loses its judgment in one generation.

**Stage 2 - Prediction before execution.** Before an agent runs a spec, the apprentice writes down: which components will change, what shape the implementation takes, what the tests will be, what could fail. Then compares against reality and records the miss. This prediction-error loop is the core of the new apprenticeship: consequences without construction.

**Stage 3 - Seeded-defect training.** A battery of planted flaws: implementation defects, superficial proofs, ambiguous specs, incident replays. The apprentice finds them without the implementing agent's summary. (Every role document's curriculum contains its versions of these.)

**Stage 4 - Low-risk ownership.** Twenty small specs owned end to end: intent through production observation. Promotion runs on measurable judgment: spec failure rate, escaped defects, prediction calibration.

**Stage 5 - Standard-risk ownership, then lanes.** Bigger surfaces, then shadowing a protected lane ten times before holding approval authority anywhere that matters.

The inversion to internalize: juniors used to produce cheap work and learn; now the machine produces the work, and juniors produce cheap PREDICTIONS and learn faster, because they see ten changes a day instead of one a week.

## 5. The minimum viable team (one product line)

| Role | Count |
|---|---|
| Product Intent Owner | 1 |
| Design Intent and Review Owner | 1 |
| Product Systems Engineer | 2 (overlapping domains) |
| Platform Reliability + Verification Engineer (combined at this scale) | 1 |
| Architecture and Reversibility Owner | fractional (0.25) |
| Security and Trust Owner | fractional (0.25) |
| Project Manager | 0 |
| Manual QA | 0 |

Five humans run a product line, with two fractional hats shared across lines. The role done badly that breaks Veldo fastest is Product Intent: a bad gate ships a wrong implementation occasionally, but bad intent makes the whole machine prove and ship the wrong product at full speed. That is why the PM document is the deepest in the series and why intent quality is the first thing to train, not the last.

## 6. How to run the training

1. Everyone takes the shared core, together, in one afternoon, on the sandbox repository. The capstone is the gate.
2. Each person takes their role document and runs its curriculum in the sandbox over the following two weeks, alongside normal work.
3. Every exercise is a Veldo change: the training itself runs through the loop, so learning the method and using it are the same act.
4. Arrival is measured by each document's milestones, not by course completion: the milestones are observable in the receipts, like everything else in Veldo.
5. The order of people follows the change-management document: volunteers first, never a forced march.

## Document History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-07-16 | Initial training guide: role map with verdicts, shared core, apprenticeship path, minimum viable team |
| 1.1 | 2026-07-16 | Project-manager verdict made honestly conditional: coordination machinery dissolves; the judgment half awaits the planning layer's proof |
| 1.2 | 2026-07-16 | Companion (topic) modules introduced, starting with the planning-layer module for product-intent owners and the Product Operations hat |
