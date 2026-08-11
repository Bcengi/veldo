# Veldo Development Method

*Software development at full speed, enabled by AI and governed by proof.*

*Version 2.2, 2026-08-03*

Veldo is Verification-Enforced Lifecycle Delivery Orchestration: a software development methodology designed for teams that build primarily with AI coding agents. It replaces the traditional software development lifecycle with a repository-native, specification-driven, proof-gated system optimized for extreme delivery speed.

The central premise is simple:

> When implementation becomes nearly free, verification becomes the primary engineering bottleneck.

AI coding agents can compress planning and implementation work that once took weeks into hours. A development process designed around human implementation speed becomes unnecessary overhead. Sprints, story points, standups, handoffs, manual status reporting, and separate QA phases no longer improve delivery enough to justify their cost.

Veldo reorganizes development around the new constraint. Humans define intent and exercise judgment. AI agents build, test, inspect, and review. The repository contains the complete operational truth. Changes move continuously into one trunk as soon as the system can prove that they satisfy their specification.

Veldo does not optimize the traditional software development lifecycle. It replaces it.

## 1. Core Model

Every change follows the same fundamental path:

```
Intent -> Specification -> Implementation -> Proof -> Independent Review -> Merge
```

A human states what should change and how success will be recognized. An AI coding agent implements the change. Automated checks prove that the implementation meets the specification and does not violate repository constraints. A fresh-context agent independently reviews the specification, implementation, and evidence. The change merges automatically when all required gates pass, except when the change affects an area where an incorrect decision would be difficult or impossible to reverse.

The unit of delivery is therefore not code alone. The unit of delivery is:

**Specification + Implementation + Evidence**

Code without evidence is incomplete.

That path is the spine of every change. Above it sits one more layer, for product work only. A product increment (several features, many specifications, shared regression) is defined holistically before it is decomposed, so specifications are pulled from a deliberate order rather than arriving as a random stream. A bug or an isolated change skips that layer and enters the path directly. Principle 2.11 states the two lanes; Stage 0 in the lifecycle defines the planning layer and how work flows out of it.

## 2. Foundational Principles

### 2.1 The repository is the operating system

The repository is the single source of truth for the product and the development process. Anything required to understand, build, validate, operate, or modify the system must be available to an authorized agent through the repository or through a machine-readable interface referenced by the repository.

This includes:

- Source code
- Specifications
- Acceptance criteria
- Tests
- Architecture decisions
- Coding conventions
- Operational procedures
- Development commands
- Environment requirements
- Database schemas
- API contracts
- Deployment configuration
- Current work status
- Known limitations
- Product terminology
- Security requirements
- Agent instructions

If an agent cannot read it, diff it, or invoke it, it should not be considered reliable operational knowledge.

External systems may still exist, but they must not become hidden sources of truth. Chat messages, meetings, private notes, and undocumented decisions are temporary communication channels. Any durable decision must be moved into the repository.

The repository being the source of truth does not mean humans type into it. The repository is the database, not the user interface: humans state intent in their own tools and their own words, agents are the scribes that write truth into the repository, and human-readable views are generated outward from it. What the principle forbids is truth living anywhere else, not humans working where they are comfortable.

### 2.2 The specification is the unit of work

Veldo does not begin with a Jira ticket, user story, sprint commitment, or engineering estimate. It begins with a short in-repository specification. For a product increment, the specification is still the unit of work; it is simply pulled from a Product Plan in deliberate order rather than authored in isolation (principle 2.11, Stage 0). The plan sets the order and carries the holistic context; the specification remains the contract the machine builds and proves against.

The specification defines:

- The problem or desired outcome
- The intended behavior
- The relevant constraints
- Acceptance criteria
- Required tests or evidence
- Areas that must not change
- Any required human approval

The specification describes intent, not implementation details, unless a technical constraint is itself part of the requirement.

A specification should be small enough that one agent can implement it coherently and one reviewer can evaluate it without reconstructing an entire project history.

A specification is complete only when success can be evaluated.

Bad specification:

> Improve account creation.

Better specification:

> Reduce account creation failures caused by duplicate email formatting.

Acceptance criteria:

- Email addresses are normalized before duplicate-account checks.
- Gmail dot variations are treated according to the existing identity policy.
- Existing accounts are not modified.
- The API returns the current duplicate-account error format.
- Unit tests cover normalization, duplicate detection, and unaffected domains.

The specification is the contract between human intent and machine execution.

Recurring, mechanical change classes do not need a fresh specification per instance. Dependency updates, copy corrections, and configuration rotations are high-volume, mostly mechanical, and occasionally catastrophic. Define a **standing specification** once per change class: its acceptance criteria, risk classification, and required evidence. Each instance then runs the normal loop against the standing specification: an ordinary change whose proof manifest references the standing specification's id, gated and reviewed as usual, with the index tracking the class rather than each instance. This keeps proof without per-change ceremony.

Specifications are also how outside signals become work. Bug reports, support tickets, crash alerts, and feature requests arrive in whatever tool their reporters live in; they are input, not work. An intake agent converts them: it deduplicates, attempts to reproduce, and drafts the specification with the reproduction attached as a failing test, because a bug's first acceptance criterion is its reproduction. When reproduction is genuinely impossible, intermittent, production-only, or environment-bound, the specification says so and names the closest observable proxy (a log signature, a metric) as the criterion instead. No one needs to write specification files by hand, engineers included: humans state intent in their own words and their own tools, and agents formalize it into the contract.

### 2.3 Humans own intent and judgment

Humans remain accountable for two functions:

**Intent.** Humans decide:

- What outcome matters
- What problem should be solved
- What tradeoffs are acceptable
- What constraints apply
- What should not be changed
- How success should be recognized

**Judgment.** Humans decide:

- Whether the specification reflects the real need
- Whether risks are acceptable
- Whether irreversible changes should proceed
- Whether a result is strategically or operationally appropriate
- Whether an exception to an automated rule is justified

Humans should not manually perform machine work merely because that work was historically performed by engineers.

The objective is not to remove humans from development. The objective is to reserve human attention for decisions that require human responsibility.

### 2.4 Machines own construction and proof

AI agents are responsible for the mechanical execution of development:

- Reading the repository
- Understanding relevant context
- Planning the implementation
- Modifying code
- Creating and updating tests
- Running checks
- Inspecting failures
- Correcting defects
- Updating documentation
- Producing evidence
- Reviewing changes
- Identifying risk
- Verifying acceptance criteria

The implementing agent must not treat code generation as completion. Its responsibility ends only when it has produced both the change and the evidence required to evaluate the change.

### 2.5 Verification is the bottleneck

Traditional development optimized the production of code because code was expensive to produce. In AI-native development, code generation is cheap and fast. The scarce resource is confidence.

The critical engineering question changes from:

> How quickly can we write this?

to:

> How quickly can we prove this is correct?

Veldo therefore invests heavily in:

- Executable acceptance criteria
- Automated tests
- Static analysis
- Type checking
- Contract tests
- Integration tests
- Security checks
- Migration validation
- Deployment checks
- Independent review
- Observability
- Fast rollback

A team practicing Veldo should spend more effort improving its proof system than optimizing raw code generation. Faster agents without stronger verification only create defects faster.

### 2.6 Every change must carry evidence

A change is not complete because the implementation looks plausible. It is complete when evidence demonstrates that the implementation satisfies the specification.

Evidence may include:

- Passing automated tests
- New tests that fail before the change and pass after it
- Type-checking results
- Linting results
- Build results
- API contract validation
- Database migration checks
- Security scan results
- Performance measurements
- Screenshots
- Recorded UI behavior
- Structured manual verification
- Logs from a test environment
- Reviewer findings
- A design owner's review verdict for user-facing changes
- Explicit mapping from acceptance criteria to proof

The required evidence should be proportional to the risk of the change. A text correction may require a build and visual check. An authentication change may require unit, integration, security, regression, and human review.

### 2.7 Independent review requires fresh context

The agent that created a change should not be the only agent deciding whether the change is correct. Implementation and review are separate roles.

The review should be performed by a fresh-context agent that receives:

- The specification
- The relevant repository instructions
- The final diff
- The produced evidence
- Access to run necessary checks

The reviewer should ideally use a different model or independent execution context.

The reviewer must evaluate the change from first principles rather than trusting the implementing agent's summary. Its job is to determine:

- Whether the implementation satisfies every acceptance criterion
- Whether the evidence actually proves the claims being made
- Whether tests are meaningful rather than superficial
- Whether the change introduces regressions
- Whether the implementation violates repository conventions
- Whether security, data integrity, or operational risks were missed
- Whether unnecessary complexity was introduced
- Whether the specification itself contains unresolved ambiguity

Fresh-context review reduces shared assumptions, confirmation bias, and false confidence.

### 2.7.1 Long-running loops keep the orchestrator thin (clean-context dispatch)

Fresh-context review (2.7) is one instance of a broader rule that governs any session which drives more than one specification. When a single long-lived session runs many specs in a loop, an autonomous or multi-spec run, it must act as a THIN DISPATCHER, not an inline worker.

Each spec's heavy work, its build and its independent review, must be performed in a DISPATCHED FRESH SUB-CONTEXT (a sub-agent) that returns only a compact receipt: the small summary of what happened (the criteria proven, the gate result, the verdict, the commit, and the one thing awaiting a human), never the sub-context's full transcript. The long-lived orchestrator keeps ONLY that receipt per spec. It does not perform per-spec build or review work inline, and it does not read a sub-context's transcript into its own context.

The reason is mechanical, not stylistic. An orchestrator that drives spec after spec inline accumulates every spec's build context plus every review sub-context's transcript in one process. Its memory then grows without bound, as the sum of all specs rather than the size of one, until the operating system's out-of-memory killer terminates it. On 2026-07-19 a single orchestrator session that drove item after item inline reached roughly 17.8 GB and was killed by the kernel, taking its terminal down with it. A thin dispatcher keeps a flat footprint across any number of specs, because it retains a bounded receipt per spec and nothing more.

This rule has teeth beyond prose. The dispatch boundary projects each outcome to a bounded receipt through a pure function whose allowlist of summary fields fails closed, and a self-test rejects any receipt that smuggles a transcript or a full nested result through it, so the boundary cannot silently regress.

### 2.8 Green means merge

For ordinary reversible changes, passing all defined gates should result in automatic merge. Ordinary means no required human lane: a change whose specification requires a human review lane (section 7) is not ordinary, however reversible it is. Human approval should not be required merely because human approval was historically part of the process. A human review queue recreates the exact bottleneck that AI-native development is intended to remove.

The default rule is:

> Specification satisfied + gates green + independent review passed = merge

Human sign-off is reserved for changes where being wrong could create severe or irreversible consequences. Examples include:

- Movement of money
- Billing calculations
- Authentication and authorization
- Destructive database migrations
- Encryption or key management
- Core infrastructure
- Production access controls
- Legal or regulatory behavior
- Permanent deletion
- High-impact security changes
- Changes that cannot be rolled back safely

Human approval is a risk control, not a ritual.

### 2.9 Changes flow continuously into one trunk

Veldo uses continuous integration into a shared primary branch. There are no sprint boundaries. There are no release trains for ordinary changes. There is no requirement to batch unrelated work into a scheduled deployment.

A proven change should merge as soon as it is ready. Branches should be short-lived and limited to the implementation of a single coherent specification. The expected lifetime of a normal change is hours to a few days, not weeks.

Long-lived branches indicate one of the following problems:

- The specification is too large
- The proof system is too slow
- The architecture makes changes difficult to isolate
- The acceptance criteria are unclear
- Too much work has been bundled together
- A decision is blocked on unavailable human judgment

The solution is usually to reduce scope or improve the system, not add more project management.

### 2.10 Work should remain small and reversible

Veldo favors small, independently provable changes.

A good change:

- Has one clear objective
- Produces a focused diff
- Can be reviewed in isolation
- Has explicit acceptance criteria
- Can be tested reliably
- Can be rolled back
- Does not depend on a large sequence of unmerged work

Large changes should be decomposed into independently valid increments. Decomposition must not produce meaningless partial states. Each increment should leave the system correct and operational.

Feature flags, compatibility layers, expand-and-contract migrations, and parallel interfaces may be used to preserve reversibility.

### 2.11 Product work is planned before it is decomposed

A stream of individual specifications is exactly right for a bug or an isolated change, and exactly wrong for a product increment. Product development is holistic first: outcomes, the feature breakdown, the order, the regression, and what "done" means are decided together, and only then does the work split into pieces. Pulling specifications off a random queue loses that whole; a piece built without the picture it belongs to is built blind.

Veldo therefore keeps two lanes:

- **The direct lane.** A bug, a copy fix, a config change, one isolated improvement: a standalone specification enters the lifecycle at Stage 1. Nothing changes for this lane; it is the common case and it stays light.
- **The planned lane.** A product increment (several features, many specifications, shared regression) is defined once as a **Product Plan** before any specification is written, and specifications are pulled from it in dependency order. Stage 0 defines this.

The plan is not a return to sprints and estimates. It is a single lightweight artifact that holds the holistic view so every part inherits it, and it obeys the same proportionality rule as everything else: defining one takes tens of human minutes, and if the planning apparatus grows past that, it has become the ceremony Veldo exists to remove. The two lanes stay honest through promotion: a change that started standalone and turns out to belong to an increment is promoted into the plan rather than living as a shadow dependency, and the binding is mechanically enforced in both directions.

## 3. The Veldo Change Lifecycle

### Stage 0: Plan the iteration

This stage applies only to a product increment: several features, many specifications, shared regression. A bug or an isolated change skips it and starts at Stage 1 (principle 2.11). Skipping it for genuinely isolated work is correct, not a shortcut; forcing a plan onto a one-line fix is the ceremony the proportionality rule forbids.

A product increment is defined holistically before it is decomposed. The holistic definition is a **Product Plan**: a short, human-approved document that becomes the context every specification pulled from it inherits, so the agent building one part sees the whole it belongs to.

A Product Plan contains:

- **Outcomes.** The observable changes for users the increment must make true, each with a measure. Outcomes are states of the product, not tasks.
- **Non-goals.** Named exclusions that kill scope drift before it starts.
- **Constraints.** Cross-cutting rules every work item inherits: budgets, invariants, platform rules.
- **A feature tree.** The decomposition into capabilities a user can name, each tracing to an outcome.
- **The work DAG.** An ordered list of work items, each of which becomes exactly one specification, each declaring its dependencies explicitly. An empty dependency list is a declaration; a missing one is an error.
- **Planned regression.** The journeys that must stay green across the whole increment, declared up front with their activation (from the start, or once a named item ships, or manual) and where they run, never accumulated by accident.
- **A release definition.** The milestone, the mode (merge continuously as pieces go green, or cut a coordinated release together), and what observing the increment in production means.
- **Open decisions.** Each names exactly what it blocks. Work proceeds around anything a decision does not block; nothing waits on a question that does not gate it.

The plan is a contract, as the specification is a contract. It is approved by a human, on the record, before it leaves draft, and a validator checks it mechanically: every reference resolves, the dependency graph is acyclic, each work item mirrors the specification it becomes and vice versa, and no unresolved decision blocks a work item that is otherwise ready.

The DAG has a **frontier**: the work items whose dependencies are all shipped and that no open decision blocks. Specifications are pulled from the frontier in deliberate order, one at a time, and each then runs the ordinary lifecycle, Stages 1 through 10. Building out of order is refused by the machine, not by discipline: a planned specification whose dependencies are unshipped, or whose plan has been revised since it was pulled, does not run until it is re-pulled against the current plan. Each change also binds to the exact plan state it was built against, so proof records which version of the whole a part was proven under. The plan's status (what has shipped, what waits on what, what the frontier is) is derived from the specification files, never hand-maintained, so it cannot drift from the truth the way a status board does.

**Promotion** keeps the two lanes honest. A change that began as a standalone specification and turns out to belong to an increment is promoted into the plan: it is added to the work DAG with its dependencies, and the specification gains the plan binding. Because mirroring is enforced in both directions, a half-promoted change fails the gate: a specification that claims a plan with no matching work item, or a work item with no specification, is a contradiction the machine refuses.

When an approved plan changes (new work, changed dependencies, dropped scope), that is a **revision**, not an edit: the revision is recorded, its blast radius on already-shipped work is computed, and dependent context built against the old revision is invalidated, exactly as revising a ready specification invalidates the evidence bound to it. Intent is allowed to change; it is not allowed to change silently underneath work already done.

The plan is stewarded in the same weekly index pass that grooms specifications (section 6). There is no separate planning meeting, because the plan reports its own state.

### Stage 1: State the intent

A human describes the desired outcome. The intent should answer:

- What should become true?
- Why does it matter?
- Who or what is affected?
- What constraints must be respected?
- What would make the result unacceptable?

The intent should avoid prescribing implementation unless necessary.

Example:

> Customers must be able to retry a failed payment without creating a duplicate order.

### Stage 2: Create the specification

The intent is converted into a repository-native specification.

The specification is drafted as a dialogue, not a form. The specification agent interviews the human: what outcome matters, what constraints apply, which edge cases exist, what failure would look like. It drafts the specification from the answers, and the human edits and approves. The human never starts from a blank page, because stating intent well is the scarcest human work in the method and the dialogue is what makes it cheap.

Location:

```
/specs/<spec-id>-<short-name>.md
```

Example:

```
/specs/VELDO-0142-payment-retry-idempotency.md
```

Specifications live flat in `specs/`. Status is a field inside the file, never a directory, and the
file's field is the only authority on it. This is not a stylistic preference: every reader of the
corpus, the validator, the index generator, the frontier, the plan resolver and the push guard,
reads `specs/` flat. A specification filed one directory down is invisible to all of them, and it
fails silently rather than loudly, because an empty corpus is indistinguishable from a clean one.
Group and filter by reading the derived index, not by moving files.

A specification should contain:

```markdown
# Title

## Status

Draft | Ready | In Progress | Review | Proven | Shipped | Blocked

## Intent

What outcome should be achieved and why.

## Context

Relevant product, technical, or operational background.

## Scope

What is included.

## Out of Scope

What must not be addressed by this change.

## Acceptance Criteria

- Observable, testable requirement
- Observable, testable requirement
- Observable, testable requirement

## Constraints

Technical, security, compatibility, performance, or business constraints.

## Required Evidence

Tests, checks, screenshots, measurements, or other proof required before merge.

## Risk Classification

Low | Standard | High | Critical

## Human Approval

Required | Not Required

Reason:

## Notes

Any additional information needed by the implementing or reviewing agent.
```

The specification is committed before or with the implementation so its history remains visible.

### Stage 3: Validate the specification

Before implementation begins, an agent checks whether the specification is executable. The specification validator should identify:

- Ambiguous requirements
- Contradictory acceptance criteria
- Missing edge cases
- Missing rollback requirements
- Unclear ownership
- Requirements that cannot be tested
- Scope that is too large for one coherent change
- Risk classification that appears incorrect
- Missing repository context

For ordinary low-risk work, the validator may automatically improve formatting and propose clarifications based on repository conventions. Material product decisions must remain human-owned.

A specification should not enter implementation while its success criteria remain subjective or undefined.

### Stage 4: Implement the change

The implementing agent reads:

- The specification
- Repository-level instructions
- Relevant architecture documentation
- Existing tests
- Related source code
- Previous decisions
- Current index of active work

The implementing agent then:

1. Creates a concise implementation plan.
2. Identifies affected components.
3. Identifies risks and likely regressions.
4. Implements the smallest complete change.
5. Adds or updates tests.
6. Runs the required checks.
7. Corrects all failures.
8. Updates documentation and operational instructions.
9. Produces a structured completion report.

The implementing agent must not silently weaken tests, bypass checks, or redefine acceptance criteria to make the change pass. If the specification cannot be satisfied safely, the agent must stop and record the blocker.

### Stage 5: Build the proof package

Every implementation must produce a proof package. The proof package should contain:

```markdown
# Proof Report

## Specification

Path or identifier of the implemented specification.

## Summary

What changed.

## Acceptance Criteria Results

### Criterion 1

Status: Passed | Failed | Not Proven

Evidence:
- Test name
- Command result
- File reference
- Screenshot
- Measurement

### Criterion 2

Status: Passed | Failed | Not Proven

Evidence:
- Relevant proof

## Checks Executed

- Command
- Result
- Relevant output or artifact

## Tests Added or Modified

- Test file
- Behavior covered
- Why the test is meaningful

## Regression Analysis

Areas that could have been affected and how they were checked.

## Risk Notes

Remaining uncertainty, assumptions, or operational considerations.

## Rollback

How the change can be reverted or disabled.

## Implementation Agent

Model or agent identifier, when available.
```

The proof package may be generated as a file, pull request body, CI artifact, or machine-readable manifest. The format matters less than its availability, reproducibility, and connection to the specification.

### Stage 6: Run automated gates

The repository defines a standard gate command. Examples:

```
make verify
npm run verify
./scripts/verify.sh
task verify
```

The command should execute every mandatory repository-level check. Depending on the project, this may include:

- Formatting
- Linting
- Type checking
- Unit tests
- Integration tests
- Contract tests
- Build verification
- Dependency checks
- Security scanning
- Secret detection
- Migration validation
- Generated-code consistency
- Documentation validation
- Performance thresholds
- Test coverage requirements
- Packaging checks
- Deployment dry runs

The command must produce a clear success or failure result. A gate that frequently produces false positives or false negatives should be treated as a production defect. Slow gates should be optimized aggressively because verification speed determines delivery speed.

### Stage 7: Conduct independent agent review

A fresh-context reviewing agent evaluates the final state. The reviewing agent should not rely on the implementing agent's conclusions. It should independently inspect:

- The specification
- The diff
- The affected code
- The tests
- The proof report
- The automated gate results
- Relevant architecture and operational constraints

The review should produce a structured verdict:

```markdown
# Independent Review

## Verdict

Pass | Pass with Non-Blocking Notes | Fail | Escalate

## Specification Coverage

- Criterion 1: Satisfied | Not Satisfied | Unclear
- Criterion 2: Satisfied | Not Satisfied | Unclear

## Findings

### Blocking

Issues that prevent merge.

### Non-Blocking

Valid improvements that do not prevent the current change from shipping.

## Test Assessment

Whether the tests meaningfully demonstrate the required behavior.

## Regression Risk

Potential unintended effects.

## Security and Data Risk

Relevant concerns.

## Complexity Assessment

Whether the implementation is appropriately simple.

## Reviewer

Model or agent identifier, when available.
```

A failed review returns the change to implementation. The implementing agent addresses findings and regenerates the proof package. The reviewing agent then evaluates the revised change in a fresh or reset context.

The loop is bounded. After two failed review cycles on the same specification, a human looks before a third attempt is made. At that point the defect is almost always in the specification, ambiguous intent or untestable criteria, not in the implementation, and more machine cycles will not fix a human ambiguity.

### Stage 8: Apply the merge policy

A change may merge automatically when all of the following are true:

- The specification is valid and was approved as ready before implementation began
- Every acceptance criterion is proven
- All mandatory automated gates pass
- Independent review passes
- No unresolved blocking findings remain
- Required documentation is updated
- The change is classified as reversible
- Human approval is not required

A change requires human approval when any of the following are true:

- The risk classification requires it
- The change affects an irreversible or high-impact area
- The specification contains an explicit approval requirement
- The reviewer escalates unresolved judgment
- The proof is incomplete but a business exception is being considered
- The implementation creates a strategic, legal, financial, or security tradeoff

Human approval must be recorded in a durable, diffable, or auditable form.

One more condition guards the trunk itself: proof is valid only for the state it ran against. If the trunk has moved since the gate ran, the merged result is a state no gate has ever seen. Re-run the mandatory gate on the merge result before the merge completes, serialized so that nothing else lands in between; at low volume that is a rebase, a re-run, and an immediate merge, and at scale a merge queue automates exactly that. Two changes that each pass in isolation can still fail together, and the trunk must never contain a state that was not itself proven.

### Stage 9: Merge and observe

After merge, automated systems should deploy or prepare the change according to repository policy. The system should collect enough operational evidence to detect incorrect assumptions.

Post-merge checks may include:

- Deployment health
- Error rates
- Latency
- Conversion behavior
- Data integrity
- Queue depth
- Billing reconciliation
- Security events
- Feature-specific metrics
- User-visible failures

A change may be technically correct according to tests but wrong in production because the specification or assumptions were incomplete. Veldo therefore treats observability as part of proof, especially for changes whose real behavior depends on production conditions.

### Stage 10: Close the specification

Once the change is merged and stable, update the specification status.

Example:

```
Ready -> In Progress -> Review -> Proven -> Shipped
```

The specification, implementation, proof, review, and resulting commit should remain linked. This creates a permanent record of:

- What was intended
- What changed
- Why it changed
- How it was tested
- Who or what reviewed it
- What evidence justified shipping it

No separate handover document is required because the development record is already present in the repository.

## 4. Risk Classification

Veldo uses risk to determine the strength of the gate, not organizational hierarchy or arbitrary process.

One law governs classification: anything may raise a change's risk, and nothing may lower it. A protected-path rule, a static check, the independent reviewer, even a production observation can each push a change into a higher tier. A live change is never lowered; lowering happens only by revising the specification, a new classification decision made by the accountable human, which invalidates the evidence bound to the old revision.

### Low Risk

Examples:

- Copy changes
- Internal developer tooling
- Non-functional refactoring with strong test coverage
- Documentation
- Isolated visual corrections
- Logging improvements without sensitive data

Typical requirements:

- Standard automated gate
- Relevant tests or build
- Independent agent review
- Automatic merge

### Standard Risk

Examples:

- Ordinary product behavior
- API changes with backward compatibility
- New UI functionality
- Non-destructive data processing
- Business logic with reversible outcomes

Typical requirements:

- Full standard gate
- Acceptance tests
- Regression checks
- Independent agent review
- Automatic merge when green

### High Risk

Examples:

- Billing calculations
- Permission behavior
- Sensitive data handling
- Infrastructure configuration
- External system integrations
- Changes affecting major customer workflows
- Large-scale data transformations

Typical requirements:

- Expanded test matrix
- Security or data review
- Staging validation
- Rollback plan
- Independent review by a strong model
- Human approval

### Critical Risk

Examples:

- Money movement
- Authentication architecture
- Authorization boundaries
- Destructive migrations
- Encryption or key management
- Permanent deletion
- Core production infrastructure
- Regulatory behavior
- Changes with no reliable rollback

Typical requirements:

- Explicit human-owned specification
- Threat or failure analysis
- Multiple independent reviews
- Production simulation where possible
- Tested rollback or recovery procedure
- Human approval before execution
- Human observation during rollout when appropriate

### The Emergency Lane

When production is failing and waiting would cause real harm, Veldo does not require a specification before acting. Restore service by the fastest safe means, rolling back, disabling, diverting, or fixing forward, with a human engaged throughout. Then backfill within 24 hours: the specification describing what was intended, the proof that the shipped fix satisfies it, and an independent review of what actually went out. The emergency is recorded like any other change; only the order of the steps bends.

The lane is defined precisely because pressure is when methods break. A method with no answer at 2am teaches people to bypass it at 2am, and bypass becomes culture. And an emergency that recurs is not an emergency; it is a missing specification.

## 5. Repository Structure

A repository using Veldo should make the methodology visible and executable.

Example:

```
/
├── VELDO.md
├── README.md
├── Makefile
├── specs/                      # flat; status is a field in the file, not a directory
│   ├── index.md                # derived, never hand-edited
│   ├── TEMPLATE.md
│   └── VELDO-0142-payment-retry-idempotency.md
├── docs/
│   ├── architecture/
│   ├── decisions/
│   ├── operations/
│   ├── product/
│   └── security/
├── scripts/
│   ├── verify.sh
│   ├── review.sh
│   └── update-spec-index.sh
├── proof/
│   └── <spec-id>/
├── src/
└── tests/
```

The exact structure may vary, but every repository should provide obvious answers to these questions:

- Where are active specifications?
- How does an agent know what work is ready?
- How does an agent run the complete gate?
- Where are architecture constraints documented?
- Where are proof artifacts stored?
- How is independent review recorded?
- Which changes require human approval?
- How can a change be rolled back?
- What is currently blocked?

## 6. The Repository Index

Veldo replaces heavy project tracking with a simple diffable index.

Example:

```markdown
# Specification Index

| ID | Title | Status | Risk | Owner | Human Approval | Updated |
|---|---|---|---|---|---|---|
| VELDO-0142 | Add payment retry idempotency | Review | High | Agent | Required | 2026-07-15 |
| VELDO-0141 | Correct referral card copy | Active | Low | Agent | No | 2026-07-15 |
| VELDO-0143 | Add usage alert threshold | Ready | Standard | Unassigned | No | 2026-07-15 |
```

The index is not a second source of truth. It is a navigation layer derived from the specifications. The specification file contains the authoritative details.

The index should remain:

- Small
- Human-readable
- Machine-readable
- Diffable
- Easy for agents to update
- Free of status theater

Do not recreate Jira inside Markdown.

One vocabulary rule keeps machines and humans aligned: status names are canonical in lowercase snake form (`in_progress`) and displays may capitalize freely. The specification file's status field is always the authority, and it is the only place status lives. There are no status directories.

The index is groomed in the one recurring ritual Veldo keeps: a short weekly pass, fifteen to twenty minutes, over the index. Close what shipped, kill what went stale, adjust priorities, confirm the next ready specifications. That pass is the entire planning apparatus. If it regularly needs more than twenty minutes, the specifications are too large or the index has drifted from the truth.

## 7. Agent Roles

A single underlying AI system may perform multiple roles, but the execution contexts should remain distinct.

**Specification Agent.** Responsibilities:

- Convert human intent into a structured specification
- Identify ambiguity
- Propose acceptance criteria
- Identify likely risks
- Avoid inventing product decisions
- Mark unresolved questions explicitly

**Implementation Agent.** Responsibilities:

- Understand the specification
- Inspect repository context
- Implement the smallest complete solution
- Add meaningful tests
- Run all required checks
- Produce the proof package
- Avoid changing scope without authorization

**Verification Agent.** Responsibilities:

- Execute or inspect automated evidence
- Confirm that proof maps to acceptance criteria
- Identify weak or misleading tests
- Reproduce results where appropriate
- Refuse to mark unproven claims as passed

**Review Agent.** Responsibilities:

- Review with fresh context
- Search for defects and hidden assumptions
- Evaluate regressions
- Assess security and data risks
- Check architectural consistency
- Produce an independent verdict

**Repository Steward Agent.** Responsibilities:

- Maintain indexes
- Detect stale specifications
- Detect undocumented behavior
- Identify conflicting instructions
- Find obsolete documentation
- Propose improvements to the verification system
- Keep agent-facing repository context concise and accurate

Review lanes are not only machine lanes. Where judgment is inherently human, the human joins the loop as a reviewer, not as a process step: the design owner reviews changes that alter user-facing look, feel, or flow; a security owner reviews changes on protected security surfaces. A human reviewer produces the same structured verdict a review agent produces, with their identity and role recorded in the reviewer field, and the merge policy consumes it identically. A specification whose surface demands it simply lists the human lane in its required evidence (for example `design_review`), and the change does not merge without that verdict.

## 8. Agent Operating Instructions

When operating inside a Veldo repository, a coding agent must follow these rules. They are written for any capable agent harness; the tooling that enforces them is described in the setup guide.

**Before making changes:**

1. Read VELDO.md, the repository's agent instruction entry file (for example CLAUDE.md), and relevant repository instructions.
2. Locate the applicable specification.
3. Do not implement a draft specification unless explicitly instructed.
4. Inspect the affected code, tests, contracts, and architecture decisions.
5. Restate the acceptance criteria in operational terms.
6. Identify risks, ambiguities, and likely regressions.
7. Stop only when a material human decision is missing.

One exception exists to the specification precondition: the emergency lane (section 4). It applies only when a human declares an emergency, and the backfill debt is tracked until closed.

**During implementation:**

- Keep the change limited to the specification.
- Prefer the smallest coherent implementation.
- Preserve backward compatibility unless the specification explicitly removes it.
- Add tests that demonstrate behavior, not merely execute lines.
- Do not weaken existing checks.
- Do not delete failing tests unless the specification makes them obsolete.
- Do not modify acceptance criteria to match the implementation.
- Update documentation when behavior, interfaces, operations, or architecture change.
- Keep intermediate work buildable whenever practical.
- Record unexpected findings that affect future work.

**Before declaring completion:**

- Run the repository's canonical verification command.
- Confirm every acceptance criterion individually.
- Produce a proof report.
- List all files changed.
- Explain any implementation tradeoffs.
- Identify residual risk.
- Provide rollback instructions.
- Do not claim success when a required check was skipped.
- Mark anything not directly proven as an assumption.
- Prepare the change for independent fresh-context review.

**Prohibited behavior.** The agent must not:

- Treat generated code as inherently correct
- Claim tests passed without running them
- Hide failed checks
- Bypass required gates
- Expand scope for convenience
- Introduce speculative abstractions unrelated to the specification
- Make irreversible decisions without required approval
- Depend on undocumented chat context
- Store essential operational knowledge only in a conversation
- Approve its own implementation as the sole reviewer

## 9. Definition of Proven

A change is proven when all of the following are true:

- The specification is clear and versioned.
- Every acceptance criterion has corresponding evidence.
- The implementation is complete.
- Relevant tests pass.
- Repository-wide mandatory gates pass.
- The evidence is reproducible.
- Independent review passes.
- Risks are documented.
- Rollback or recovery is understood.
- Required human approval has been recorded.

"Works on my machine" is not proof. "The agent says it is done" is not proof. "A test passed" is not sufficient when the test does not establish the required behavior.

Proof means that the available evidence justifies shipping the change.

## 10. Definition of Done

Traditional definitions of done often describe a checklist of activities. Veldo defines done as a verified state:

> Done = intent satisfied + evidence produced + independent review passed + merge policy satisfied

A change is not done when:

- Code has been written but not tested
- Tests pass but do not cover the acceptance criteria
- Documentation is stale
- Review identified unresolved defects
- The gate was bypassed
- Required human approval is missing
- The change cannot be operated or rolled back safely
- The specification and implementation no longer agree

## 11. What Veldo Eliminates

Veldo intentionally eliminates process that exists primarily to coordinate slow human implementation. Unless a specific team need justifies them, Veldo does not use:

- Sprints
- Story points
- Velocity estimates
- Daily standups
- Sprint planning
- Sprint reviews
- Sprint retrospectives as mandatory ceremonies
- Separate development and QA phases
- Large handoff documents
- Manual status reporting
- Long-lived feature branches
- Release trains for ordinary changes
- Ticket systems as the authoritative source of work
- Approval chains for reversible low-risk changes

This does not mean communication, planning, reflection, or testing disappear. It means they occur where they create value rather than as recurring ceremonies.

Planning happens inside the specification and implementation process. Communication happens through durable repository artifacts. Testing happens continuously. Reflection happens when evidence reveals a systemic problem worth correcting.

The single recurring ritual that survives is the weekly index pass (section 6).

## 12. What Veldo Does Not Eliminate

Veldo does not eliminate:

- Product judgment
- Architecture
- Security engineering
- Testing
- Documentation
- Operational discipline
- Human accountability
- Risk management
- Design
- User research
- Strategic planning
- Incident response
- Regulatory controls

It eliminates the assumption that these activities require the process structure of twentieth-century software development.

## 13. Production Support

A method that ends at the merge is only half a method. Software that ships has to be operated, and
the same asymmetry that motivates everything above applies after release: machines can read far
more evidence far faster than a person can, and a person is the only one who should be allowed to
change a running system. Production support is built on that split.

**An incident is intent.** It enters the same way a change does, as a durable record rather than a
conversation, and it moves through declared states with the same event trail. This matters because
the alternative - an incident that lives in a chat channel and a person's memory - cannot be
reconciled afterwards, and an organisation that cannot reconcile its incidents cannot learn from
them.

**Diagnosis is derived from artifacts, by a reader that cannot write.** The responder is given
read-only access to an evidence plane: logs, metrics, traces, the specification corpus, the proof
bundles, the event log. It produces a diagnosis in which every claim cites the artifact it rests on,
so a human can check the reasoning rather than trust it. The structural property is the important
one: the responder has no execution tool at all. It is not trusted not to act; it is unable to act.

**Remediation is a proposal, and a human authorises it.** The responder proposes; it never applies.
What it proposes is checked against a whitelist of runbook actions declared in advance, each with
its parameters, its blast radius and its reversibility stated. An action nobody wrote down is not
available in an incident, which is exactly when the temptation to invent one is strongest.

**Execution is a separate organ.** The thing that can change a running system is not the thing that
decided what to change. It re-checks every precondition at the moment of execution, refuses on a
tripped kill switch or an exhausted budget or an expired authorisation, and records what it did.
Anything irreversible or data-mutating takes two keys, which is the independence rule from review
extended to the last mile.

**The numbers come out of the same event trail** as everything else, so time-to-diagnosis and
time-to-remediation are measured rather than estimated, and a recurring incident is visible as a
recurring incident rather than as a series of unrelated bad nights.

**What this does not do.** It does not remove the human from the loop, and it is not autonomous
operations. Every state change to a running system is authorised by a person, and the organ ships
inert: an adopting repository gets the contracts and the machinery, not a wired-up connection to
anything real. Turning it on against live systems is a deliberate configuration act with its own
risk, described in the setup document rather than here, and it is not a step anyone should take on
the same day they adopt the method.

## 14. Infrastructure and Release

The loop stops at the merge unless what runs the software is governed the same way the software is.
So the substrate - environments and the resources in them - is declared in the repository, and a
change to that declaration is an ordinary change: specified, proven, gated, merged, with a diff a
person can read. No console clicks, no drift between what somebody remembers provisioning and what
is actually there.

**Infrastructure changes are plan-then-apply, and the plan binds.** Comparing declaration to
declaration produces the operations that would reconcile them, and a human reads that before
anything happens. The plan carries a digest of both states it was computed from and refuses to
apply if either has moved, because a plan computed against a world that no longer exists is a guess
with a formatting convention, and applying one anyway is the precise mechanism by which
infrastructure tooling destroys things nobody asked it to touch.

**Cost is a proof element, not a surprise.** A change projects its monthly delta against the
environment's declared budget, so the number is read at review rather than discovered on a bill six
weeks later. A resource whose price nobody has declared is refused rather than counted as free,
because costing unknowns at zero is how a budget check passes the change that doubles the bill.

**Destruction is classified, and the strict direction is the default.** Deleting a stateless
resource is recoverable by re-applying the declaration; deleting a stateful one is not, and carries
the highest risk class with two independent human keys bound to that exact plan. A resource kind
nobody has classified counts as stateful until somebody says otherwise, so a type added next year
gets the careful treatment rather than sliding underneath the rule.

**Release is promotion, one environment at a time.** A proven change moves along the declared order,
carrying whatever its risk class demands - a canary, a staged rollout, a recorded approval - and it
does not move at all without a written rollback plan. A plan written after something breaks is
written by somebody panicking. A failed canary halts the promotion where it is, which is different
from failing, because halted has a known position to roll back from.

**Drift is reported in both directions, and only one of them is safe to automate.** Something
declared but not running should be created. Something running but not declared is brought to a
person, never deleted: it was made by hand for a reason, or the declaration lost it, and a tool that
tidies such things away eventually removes what production was standing on.

**Per-change environments are disposable, and disposal is verified.** An environment is created from
a declaration and torn down afterwards, and the teardown is checked against what the provider
actually still holds rather than against the fact that the destroy call returned success. Deleting a
machine commonly leaves its disk. An environment believed gone and actually running is a permanent
cost nobody looks for, because nobody inspects a thing that stopped existing.

**None of this reaches real infrastructure on its own.** Every piece above decides; acting is done
through an adapter an operator wires deliberately, and the shipped adapters do nothing. Adopting the
method does not opt a repository into managing its infrastructure, and turning that on is a separate
act with its own risk, described in the setup document.

## 15. Speed Without Recklessness

Veldo is not a license to generate and merge code indiscriminately. Its speed comes from reducing coordination latency and automating proof. The methodology is intentionally strict about correctness because implementation speed increases the potential rate of both value creation and damage.

The relationship is:

> Delivery speed = implementation speed x verification speed x decision speed

AI dramatically increases implementation speed. Repository-native specifications reduce decision and communication latency. Automated proof and independent review increase verification speed. Weak verification cancels the benefit of fast implementation.

The objective is not to move fast and break things. The objective is to move at full speed because the system can prove what it is doing.

## 16. Measuring Veldo Performance

Veldo teams should avoid productivity metrics based on human activity. Do not optimize for:

- Lines of code
- Number of commits
- Number of tickets closed
- Story points
- Agent token usage in isolation
- Number of pull requests
- Time spent coding

Measure the performance of the delivery system. Recommended metrics include:

- **Specification-to-production time.** Time from a ready specification to production deployment.
- **Proof latency.** Time required to run all mandatory checks and complete independent review.
- **First-pass proof rate.** Percentage of changes that pass the full gate without rework.
- **Escaped defect rate.** Defects discovered after a change was declared proven.
- **Reversion rate.** Percentage of changes that require rollback or urgent correction.
- **Specification failure rate.** Percentage of implementation failures caused by ambiguous or incomplete specifications.
- **Human intervention rate.** Percentage of changes requiring human involvement after the specification is approved.
- **Agent review catch rate.** Defects found by independent review before merge.
- **Mean recovery time.** Time required to detect, revert, or correct a faulty production change.
- **Verification investment.** Percentage of engineering improvements aimed at tests, gates, observability, and safe automation.
- **Human minutes per shipped change.** Total human attention consumed per shipped change: stating intent, clarifying, judging, approving. Every other metric measures the machine side; this one measures the scarce resource. For ordinary changes it should trend toward the irreducible cost of stating intent and judging the result, and no lower; it is the truest measure of whether Veldo is delivering its premise.

The ideal Veldo system becomes faster primarily by improving proof, decomposition, and repository clarity.

## 17. Failure Modes

**Vague specifications.** Symptoms:

- Agents repeatedly ask for clarification
- Implementations technically pass but miss the real need
- Reviewers disagree about success
- Scope expands during implementation

Correction:

- Improve acceptance criteria
- Add examples and counterexamples
- Separate product decisions from technical execution
- Reduce scope

**Superficial tests.** Symptoms:

- Tests mirror implementation details
- Tests pass despite broken user behavior
- Mocks eliminate meaningful system behavior
- Coverage rises while confidence does not

Correction:

- Test observable outcomes
- Add contract and integration tests
- Require tests that fail before the fix
- Have the reviewer inspect test quality

**Agent self-confirmation.** Symptoms:

- The implementing agent writes the change, evaluates it, and declares success
- Review repeats the implementation summary
- Hidden assumptions survive every stage

Correction:

- Use fresh-context review
- Use a different model where possible
- Provide the reviewer with the specification and diff, not only the implementation summary

**Human approval bottlenecks.** Symptoms:

- Green changes wait hours or days for routine approval
- Review queues grow
- Humans rubber-stamp changes without deep inspection

Correction:

- Automate merge for reversible changes
- Reserve human review for defined risk categories
- Improve automated gates instead of adding approvers

**Repository knowledge decay.** Symptoms:

- Agents rely on outdated instructions
- Different documents contradict one another
- Important decisions live only in conversations
- The same mistakes recur

Correction:

- Assign repository stewardship
- Delete or update stale instructions
- Keep durable decisions close to the affected code
- Validate documentation in CI where possible

**Oversized specifications.** Symptoms:

- Branches remain open for weeks
- Reviews become shallow
- Rollback becomes difficult
- Multiple unrelated failures block the same change

Correction:

- Decompose by independently valuable behavior
- Introduce compatibility layers
- Use feature flags
- Separate mechanical preparation from behavior changes

**Gate inflation.** Symptoms:

- Verification takes too long
- Unrelated flaky tests block delivery
- Teams begin bypassing checks
- Every change runs every possible test

Correction:

- Fix flaky tests immediately
- Parallelize checks
- Use risk-aware and change-aware test selection
- Preserve a reliable full gate
- Measure and reduce proof latency

**Letter-not-intent implementation.** Symptoms:

- Every acceptance criterion passes while the result misses what was actually wanted
- Stakeholders reject changes that are technically proven
- Criteria are satisfied in ways that serve the checklist rather than the outcome

Correction:

- Write criteria as observable outcomes, not implementation behaviors
- Have the reviewer read the Intent section and judge the change against it, not only against the criteria
- Treat a proven-but-wrong change as a specification defect and feed it back into how specifications are written

## 18. Adoption Rules

A team adopting Veldo should not begin by introducing more agents. It should begin by making the repository operable.

Recommended adoption sequence:

**Phase 1: Repository clarity**

- Create the agent instruction entry file (for example CLAUDE.md)
- Document build and test commands
- Remove contradictory instructions
- Identify authoritative architecture documentation
- Make local setup reproducible

**Phase 2: Specification discipline**

- Create the specification template
- Move active work into the repository
- Define acceptance criteria for every change
- Create the diffable specification index

**Phase 3: Canonical verification**

- Create one command that runs mandatory checks
- Remove flaky checks
- Add missing tests around high-risk behavior
- Make results easy for agents to interpret

**Phase 4: Independent review**

- Separate implementation and review contexts
- Standardize the review report
- Measure what the reviewer catches
- Escalate only genuine judgment calls

**Phase 5: Automatic merge**

- Define risk classifications
- Enable automatic merge for reversible green changes
- Require humans only for explicitly protected areas

**Phase 6: Continuous improvement**

- Measure specification-to-production time
- Measure proof latency
- Improve the slowest gate
- Automate recurring human work
- Strengthen evidence where defects escape

## 19. Minimal Veldo Implementation

A team can begin practicing Veldo with only five repository elements:

- `VELDO.md`
- the agent instruction entry file (for example `CLAUDE.md`)
- `specs/index.md`
- `specs/<spec-id>.md`
- `scripts/verify.sh`

The minimum viable process is:

1. A human states intent and approves the specification with its acceptance criteria (drafted in dialogue with an agent, or by hand where that is simpler).
2. An implementation agent changes the code and tests.
3. The agent runs `scripts/verify.sh`.
4. A fresh-context agent reviews the specification, diff, and test evidence.
5. The change merges automatically if all gates pass and no protected area is affected.

Everything else should be added only when it increases speed, confidence, or operational safety.

## 20. Veldo Manifesto

We value:

- Proven outcomes over completed tasks
- Repository truth over external coordination
- Explicit intent over inferred requirements
- Executable acceptance criteria over subjective completion
- Independent evidence over author confidence
- Small reversible changes over large coordinated releases
- Continuous delivery over artificial iterations
- Automated gates over ritual approval
- Human judgment over human labor
- Verification speed over code-generation volume

The items on the right may still have value, but the items on the left define the system.

## 21. Security by Design

An agent writes code faster than anyone reviews it, and it writes the most common shape of a thing.
Both of those are usually fine and occasionally catastrophic, because the most common shape of an
IAM policy in the training data is `Action: *`, the most common shape of an example config is a key
pasted inline, and the most common shape of a dependency addition is nobody noticing.

None of that is a reasoning failure, and none of it is fixed by a better instruction. The next task
starts with a fresh context and the same training data. What holds is a check on the artifact.

So security in this method is not a review checklist. It is a set of floors that hold without
anybody's attention, plus one lane for the judgment that no floor can reach.

### The floors

**Secrets are named, never present.** The repository holds a reference; the value is resolved at the
moment of use and never rendered. Anything credential-shaped in a diff, a generated file or an
artifact refuses, and there is no allowlist - an allowlist is how a scanner dies, one convenient
exception at a time.

**A context that never held a secret cannot leak one.** Everything an agent reads passes through one
seam and is redacted there. Not filtered from the transcript afterwards: once a value is in a
context it is in the transcript, in whatever the model quotes back, in the summary and in the
compaction. There is no recall.

**Credentials are issued for one task, scoped to what that task declared.** Scope is derived from
the declaration, never requested by the agent - an agent that hits a permission error, widens its
request and succeeds is how least privilege dies, and nobody involved was careless.

**External text enters as data, marked as data.** An issue body, a README, a dependency's docs, a
log line: all of it is text somebody outside your organisation may have written. Labelling does not
make a model impossible to fool and the method says so plainly; what it removes is the ambiguity
that makes the easy attack easy.

**A dependency arrives attached to a reason or it does not arrive.** The requirement is visibility,
not review quality. A version bump is deliberately not flagged, because a check that fires on
ordinary work gets deleted.

**Generated infrastructure is held to least privilege.** Wildcard permissions, over-broad roles and
public-exposure defaults refuse, each naming the narrower thing to do. A refusal that says only
"least privilege violation" is one somebody adds an exception for.

**Commits are signed and attributable.** The trailer says who; the signature is what makes the who
true. And a good signature is not by itself a trust decision: git reports one for any key the local
keyring holds, and the keyring is a file in the environment the agent runs in, so the fingerprint is
checked against a registry declared in the repository.

### The lane above the floors

What no rule settles is whether a change is safe. Whether this endpoint should be reachable by that
caller. Whether the new path trusts something it should not. Whether the design hands an attacker a
step they did not have yesterday.

That is judgment, so it stays with the independent reviewer as a graded dimension, exactly as
architectural fit does, and **correct-but-insecure is a legitimate rework verdict**. A change can do
precisely what its specification says and still be one you should not merge.

The dimension is designed against a specific failure. A reviewer handed "secrets clean, privilege
clean, dependencies clean, signatures valid" has been handed a comfortable green wall, and the
natural next move is to write two sentences saying the change looks fine. So the reviewer is told,
in as many words, that the floors are already enforced, not to re-grade them, and what lives above
them. A clean floor is the starting point, never the finding.

The machine never lowers. A mechanical finding forces the insecure verdict whatever the reviewer
concluded; the reviewer may overrule the machine upward and never downward.

### Migration is honest or it is theatre

A repository adopting this does not flip to fail-closed on day one. It inventories itself first -
the working tree and all reachable history, because a credential committed and then deleted is still
in every clone, every fork, and whatever CI cached the checkout. Findings are reported by reference
and never by value: an inventory that quotes what it found is a second copy of every secret, in a
file people paste into tickets.

Anything real that was reachable in history needs rotating, and rotation is a human act. The machine
surfaces named work for named people and issues nothing.

Only then does the repository declare fail-closed, and the declaration is a dated decision somebody
made with the inventory in hand - never something inferred from a scan that happened to return zero.
A scan can return zero because a path was skipped or a detector broke, and a gate armed by that
accident is worse than no gate.

## 22. The Veldo Rule

The methodology can be reduced to one rule:

> State the intent, let the machine build, require proof, and merge immediately when green.

That rule should govern every ordinary change.

The repository states what is true. The specification states what should become true. The implementation changes reality. The gate proves the result. The independent reviewer challenges the proof. The trunk records the new truth.

That is Veldo.

## Document History

Minor versions add, clarify, or extend the method; major versions restructure it or break compatibility with existing practice.

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-07-16 | Initial method |
| 1.1 | 2026-07-16 | Review additions: the emergency lane, proof freshness on a moving trunk, standing specifications, the weekly index pass, specification as dialogue, the bounded review loop, the human-minutes metric, agent operating instructions made tool-agnostic, the raise-risk-never-lower law, the letter-not-intent failure mode |
| 1.2 | 2026-07-16 | The edges: human review lanes and design review evidence, intake (reports become specifications), the repository as database rather than interface |
| 1.3 | 2026-07-16 | Revalidation fixes from an independent hostile review: merge-status and human-lane clarifications, serialized proof freshness, emergency lane generalized and recognized by the operating instructions, standing-spec instances defined, non-reproducible-bug path, risk-law tightening, status vocabulary rule, example id and entry-file consistency |
| 2.0 | 2026-07-16 | The planning layer: Stage 0 (Product Plans, the plan contract, the ordered work DAG, the ready frontier, promotion, revision impact) added ahead of Stage 1; principle 2.11 (product work is planned before it is decomposed) and the two lanes (direct and planned) stated; the core model extended with the planning layer above the per-change spine, reconciled with 2.2 (the specification stays the unit of work, now pulled from a plan in order) |
| 2.1 | 2026-08-03 | Security by design as part of the method (VELDO-1311 of PLAN-0013): new section 21 states the floors that hold without attention (secrets named not present, a context that never held a secret, task-derived credential scope, external text as data, a dependency attached to a reason, least privilege on generated infrastructure, signed attributable commits) and the one lane above them where correct-but-insecure is a legitimate rework verdict, with the green-wall failure mode it is designed against and the rule that the machine never lowers; migration stated as inventory-then-declare over reachable history, with rotation as a human act; The Veldo Rule renumbered to 22 |
