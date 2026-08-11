# VELDO 1.0 Product Planning Layer

## 1. The model

VELDO 1.0 adds one contract above the specification:

> The Product Plan is the unit of coordinated product intent. The specification remains the unit of implementation, proof, review, and merge.

The resulting flow is:

```text
Holistic intent
  -> Product Plan
  -> Ordered specification DAG
  -> Spec implementation and proof
  -> Iteration regression
  -> Release and observation
  -> Plan receipt
```

A Product Plan is not a sprint.

It has:

- No fixed duration
- No story points
- No velocity
- No branch containing all its work
- No requirement to batch ordinary merges
- No status reporting ceremony

It is a coherence envelope around a related set of small specifications. It explains why the parts belong together, what order is valid, what must remain green, and what makes the whole releasable.

VELDO therefore has two units:

| Unit | Owns |
|---|---|
| Product Plan | Product outcome, scope, decomposition, ordering, cross-cutting constraints, regression, release judgment |
| Specification | One independently implementable and provable change |

## 2. The Product Plan contract

### 2.1 Name and location

Canonical artifact name:

**Product Plan**

Schema:

```text
veldo.plan/v1
```

Recommended location:

```text
/plans/<status>/<plan-id>-<short-name>.md
```

Example:

```text
/plans/active/PLAN-0012-mobile-account-creation.md
```

Canonical statuses:

```text
draft
ready
in_progress
observing
completed
blocked
cancelled
```

Directory mapping follows the existing specification convention:

```text
plans/draft/       -> draft
plans/ready/       -> ready
plans/active/      -> in_progress
plans/observing/   -> observing
plans/completed/   -> completed
plans/blocked/     -> blocked
plans/cancelled/   -> cancelled
```

### 2.2 Product Plan template

```markdown
---
schema: veldo.plan/v1
id: PLAN-0000
title: <short product increment title>
kind: iteration             # iteration | mvp | release
status: draft               # draft | ready | in_progress | observing | completed | blocked | cancelled
revision: 1
owner: <human accountable for product intent>
risk: standard              # plan-wide risk floor
parent_plan: null
child_plans: []

target_users:
  - id: USER1
    description: <specific user or customer segment>

goals:
  - id: G1
    text: <product or business goal>

outcomes:
  - id: O1
    user_ref: USER1
    becomes_true: <observable user outcome>
    baseline: <current state or unknown>
    measure: <metric or observable signal>
    target: <target or qualitative threshold>
    horizon: <when the outcome will be evaluated>

guardrails:
  - id: GR1
    text: <metric or behavior that must not degrade>
    threshold: <allowed boundary>

constraints:
  - id: C1
    text: <cross-cutting product, design, technical, security, compatibility, or operational constraint>
    applies_to: [all]

non_goals:
  - id: NG1
    text: <explicitly excluded outcome or feature>

design_inputs:
  - id: D1
    source: <repository path or durable external reference>
    applies_to: [F1]

feature_tree:
  - id: F1
    parent: null
    title: <capability or journey segment>
    outcome_refs: [O1]
  - id: F1.1
    parent: F1
    title: <independently meaningful feature slice>
    outcome_refs: [O1]

work:
  - item: W1
    spec: WARP-0001
    title: <one-line specification intent>
    feature_refs: [F1.1]
    outcome_refs: [O1]
    depends_on: []
    order: 10
    risk_floor: standard
    owns_regression: [RJ1]
    exclusive_resources: []

  - item: W2
    spec: WARP-0002
    title: <one-line specification intent>
    feature_refs: [F1.1]
    outcome_refs: [O1]
    depends_on: [WARP-0001]
    order: 20
    risk_floor: standard
    owns_regression: []
    exclusive_resources: []

regression:
  journeys:
    - id: RJ1
      title: <journey that must remain green>
      protects: <existing or new user behavior>
      suite: <repository suite identifier or command>
      activation:
        when: spec_shipped       # start | spec_shipped
        spec: WARP-0001
      owner_spec: WARP-0001
      per_spec_profile: mobile_core
      release_profile: mobile_full

  device_profiles:
    mobile_core:
      - platform: ios
        device: <representative phone>
        os: <pinned version>
        execution: simulator
      - platform: android
        device: <representative phone>
        os: <pinned version>
        execution: emulator

    mobile_full:
      - platform: ios
        device: <smallest supported class>
        os: <minimum supported version>
        execution: simulator
      - platform: ios
        device: <current representative class>
        os: <latest supported version>
        execution: physical
      - platform: android
        device: <smallest supported class>
        os: <minimum supported version>
        execution: emulator
      - platform: android
        device: <current representative class>
        os: <latest supported version>
        execution: physical

release:
  milestone: <MVP, version, launch, or null>
  version: <version or null>
  mode: continuous             # continuous | coordinated
  activation: <always live, feature flag, store release, migration, or other mechanism>
  require_all_work_shipped: true
  require_full_regression: true
  rollback: <how the complete increment is disabled or reversed>
  observation:
    duration: 24h
    checks:
      - id: OBS1
        signal: <metric, log, crash, conversion, or health signal>
        threshold: <acceptable result>
        action_on_failure: <pause, disable, revert, or corrective spec>

required_human_reviews:
  - <design, security, legal, product, or none>

open_decisions: []
---

## Intent

Describe the holistic product problem, why this increment exists, and why the selected outcomes belong together.

## Current and target journey

Describe the user's current journey and the journey that should exist after the plan is released.

Include important entry points, successful paths, failure paths, and platform differences.

## Product decisions

Record the material product decisions already made:

- Behavior and tradeoffs
- Design direction
- Compatibility promises
- Rollout assumptions
- Product terminology
- Accepted limitations

## Feature breakdown rationale

Explain why the feature tree is decomposed this way.

Call out vertical slices, enabling work, feature flags, compatibility layers, migrations, and any deliberately deferred behavior.

## Ordered delivery rationale

Explain the important dependency edges and why the selected order is safe.

The `work` DAG is authoritative. This section explains it rather than creating another ordering system.

## Cross-cutting behavior

Describe constraints that every child specification must preserve, such as:

- Navigation and interaction conventions
- Accessibility
- Analytics
- Authentication and authorization
- Offline behavior
- Error handling
- Localization
- Data migration
- Performance
- Privacy and security
- Backward compatibility

## Regression rationale

Explain why the selected journeys and device profiles are sufficient to protect the increment.

Identify existing journeys protected from the start and new journeys activated by particular specifications.

## Release and observation

Describe how incremental merges remain safe, when users see the complete outcome, what is monitored, and what happens if observation fails.

## Open questions

This section must be empty before the plan becomes `ready`.

## Revision history

| Revision | Date | Change | Affected specifications | Human approval |
|---|---|---|---|---|
| 1 | <date> | Initial approved scope | All | <identity> |
```

### 2.3 Leaf plans and parent plans

Most teams should use one Product Plan containing direct specifications.

A larger MVP may use one root Product Plan and several child Product Plans. This is appropriate only when the MVP cannot be understood and reviewed coherently as one direct specification DAG.

Rules:

- An approved plan contains either direct `work` or `child_plans`, not both.
- Specifications bind to the nearest leaf plan.
- Child plans inherit root goals, constraints, non-goals, regression requirements, and release conditions.
- A child may strengthen an inherited condition but may not weaken it.
- The implementation and review contexts receive the complete plan ancestry.
- Root completion requires completed child receipts and root-level regression.

This is an exception for a genuinely large MVP, not the default startup workflow.

## 3. Binding specifications to the plan

### 3.1 Specification front matter additions

The specification schema gains these fields:

```markdown
---
schema: veldo.spec/v1
id: WARP-0001
title: <short title>
status: draft
risk: standard
owner: <human accountable for intent>
human_approval: not_required
protected_paths: []

lane: planned               # planned | standalone
plan: PLAN-0000             # null for standalone work
plan_revision: 1            # null for standalone work
plan_item: W1               # null for standalone work
outcome_refs: [O1]
feature_refs: [F1.1]
depends_on: []

acceptance_criteria:
  - id: AC1
    text: <observable, testable requirement>

required_evidence: [unit]
rollback: <how this change is reverted or disabled>
---

## Intent

What outcome should become true, and why it matters.

## Context

Relevant background: product, technical, operational.

## Out of scope

What this change must not touch.

## Notes

Anything the implementing or reviewing agent needs.
```

For a planned specification:

- `plan` is required.
- `plan_revision` is required.
- `plan_item` must exist in the plan.
- `depends_on` must exactly match the plan work item.
- `outcome_refs` and `feature_refs` must be valid plan references.
- The specification may narrow the plan but may not contradict it.
- Plan constraints and non-goals are inherited even when not copied into the specification.

For standalone work:

```yaml
lane: standalone
plan: null
plan_revision: null
plan_item: null
standalone_reason: <bug, isolated correction, maintenance, standing specification instance, or emergency backfill>
```

### 3.2 How the whole reaches each agent

The plan is not copied into every specification. Copying would create stale summaries.

Instead, `/veldo:run` builds a read-only Plan Context Bundle containing:

1. The root Product Plan, if one exists.
2. The leaf Product Plan.
3. The current specification.
4. The current plan DAG and status.
5. All inherited constraints and non-goals.
6. The active regression journeys.
7. The device profile required for the current gate.
8. Relevant design and architecture references.
9. The exact plan revision and Git hash.

The implementation agent and fresh-context review agent receive the same bundle.

The operating instruction is:

> The specification defines the local change. The Product Plan defines why the change exists, how it contributes to the whole, and what surrounding behavior it must preserve. If they conflict, stop rather than choosing one silently.

The proof report records:

```yaml
plan: PLAN-0000
plan_revision: 1
plan_commit: <git hash>
plan_item: W1
```

This makes proof reproducible against the holistic intent that governed implementation.

## 4. Decomposition as a discipline

## 4.1 Product-level dialogue

`/veldo:plan` interviews the founder or PM about the whole increment.

It asks:

| Area | Product-level questions |
|---|---|
| Problem | What product problem is worth solving now? Why together rather than as isolated changes? |
| Users | Which users are affected? Which are explicitly not targeted? |
| Current journey | What happens today from entry to completion or failure? |
| Target outcome | What should users be able to accomplish when the whole increment exists? |
| Success | What observable signal would indicate success? What must not degrade? |
| Scope | Which capabilities are required for the outcome? Which are optional or deferred? |
| Non-goals | What adjacent work must not enter this increment? |
| Design | What design decisions or sources govern the complete experience? |
| Platforms | Which web, mobile, device, OS, locale, accessibility, and offline conditions matter? |
| Cross-cutting behavior | What rules must every part preserve? |
| Risk | What could create security, financial, legal, data, or operational harm? |
| Rollout | Can parts be visible independently? Is a feature flag or compatibility layer needed? |
| Regression | Which existing journeys must remain green? Which new journeys must become permanent regression coverage? |
| Ordering | What must exist before something else can be built or safely exposed? |
| Observation | Which production signals determine whether the release remains enabled? |
| Exclusions | What result would look superficially complete but still be unacceptable? |

The product-level dialogue does not decide:

- File structure
- Component names
- Internal classes
- Low-level implementation algorithms
- Every local edge case
- Test implementation details

Those belong to specification and implementation work unless they are product constraints.

## 4.2 Specification-level dialogue

When a planned work item is pulled, `/veldo:spec` asks only about that leaf:

- What exact local behavior becomes true?
- Which inputs, outputs, states, and errors are observable?
- Which local edge cases matter?
- What must this specification not change?
- Which inherited plan constraints apply most directly?
- What proves this leaf?
- How is it disabled or reverted?
- Does the proposed scope still fit one coherent proof package?

The agent must not reopen approved product decisions during ordinary specification drafting. A material contradiction returns to `/veldo:plan revise`.

## 4.3 Decomposition rules

The planning agent converts the holistic outcome into:

```text
Goals
  -> User outcomes
  -> Capabilities and journeys
  -> Independently meaningful slices
  -> Small specifications
```

The following rules are mandatory:

1. Prefer vertical behavior slices over frontend and backend task splits.
2. Every work item must map to at least one feature and one outcome.
3. Every required feature node must be covered by work or explicitly excluded.
4. Every specification must leave the trunk correct and operational.
5. A specification may be enabling work only if it creates an independently provable contract, compatibility layer, migration state, flag, or operational capability.
6. Shared behavior belongs in plan constraints, not in several inconsistent specifications.
7. Dependencies describe shipped preconditions, not hoped-for branch coordination.
8. New regression journeys must have a named owner specification.
9. Partial user experiences must remain hidden or independently valid.
10. If one reviewer cannot understand a specification without mentally merging several sibling diffs, the decomposition is wrong.

A screen is not automatically a specification. It is a specification only if the screen is a complete, independently provable behavior slice. A multi-screen user journey should normally be planned as a Product Plan.

## 4.4 Upfront planning versus progressive pull

VELDO should plan the complete shape upfront but elaborate specifications progressively.

Before a Product Plan becomes `ready`, it must contain:

- The complete feature tree
- All currently known required work item IDs
- A one-line intent for every work item
- The dependency DAG
- Risk floors
- Regression ownership
- Release and observation conditions
- No unresolved product decisions

It does not require full specification prose and acceptance criteria for every future leaf.

The first ready frontier is elaborated immediately. Later work items are pulled into full specifications as their dependencies approach completion and upstream learning becomes available.

This balances two needs:

- The PM sees the whole before construction starts.
- Specifications do not pretend to know details that depend on discoveries not yet made.

A newly discovered required work item is not silently added. It requires a plan revision.

## 4.5 Ownership

| Decision or artifact | Accountable owner | Agent responsibility |
|---|---|---|
| Goals, users, outcomes, tradeoffs | Founder or PM | Interview, formalize, challenge ambiguity |
| Feature tree and slicing | Founder or PM approves | Propose decomposition and coverage |
| Dependency DAG | Product owner approves product order | Infer technical dependencies and validate DAG |
| Cross-cutting constraints | Relevant human owner | Discover affected surfaces and propose constraints |
| Regression journeys | Product owner approves protected behavior | Propose suites, automation, and activation points |
| Device matrix | Product and engineering owners | Propose smallest credible matrix |
| Plan readiness | Human product owner | Validate completeness mechanically |
| Specification acceptance criteria | Human intent owner | Draft and validate |
| Implementation and proof | Agent | Execute |
| Scope revision | Human product owner | Produce impact analysis |
| Release activation | Defined by risk policy | Execute gates and produce receipt |

The human owns product intent. The agent owns the completeness and internal consistency of the repository contract.

## 5. Ordering and dependencies

### 5.1 Dependency meaning

`depends_on` means:

> This specification may not begin implementation until every named specification is shipped on the current trunk.

`proven` is not enough. An unmerged branch is not a dependency.

If work needs a contract before parallel implementation can begin, create and ship a small contract or compatibility specification first.

### 5.2 Run refusal

`/veldo:run WARP-0002` refuses to start when any of these conditions is true:

- The parent plan is not `ready` or `in_progress`.
- The specification is not `ready`.
- The bound plan revision is stale and has not been explicitly carried forward.
- The work item does not exist in the plan.
- Specification dependencies differ from the plan DAG.
- Any dependency is not `shipped`.
- A dependency commit is absent from current trunk.
- The plan is blocked or cancelled.
- A required design input or human decision is missing.
- An active baseline regression suite is already red without an approved first-fix item.

The refusal reports the exact blockers and the current ready frontier.

CI repeats the dependency check before merge. The merge queue checks it again against the merge-result trunk state.

### 5.3 Parallelism

Two specifications may run in parallel only when:

- Neither depends directly or transitively on the other.
- All of each specification's dependencies are shipped.
- They do not claim the same `exclusive_resources`.
- Neither requires an unresolved output from the other.
- Each can merge and remain correct independently.

Known serialization domains can be declared as:

```yaml
exclusive_resources:
  - account_schema
  - mobile_navigation_root
```

The DAG defines valid order. The `order` value only sorts the ready frontier. It does not override dependency rules.

Parallel changes still merge serially through the merge queue, with verification rerun against the merge result.

### 5.4 Derived status view

`plans/index.md` is generated from Product Plans, specifications, proof, and regression results.

Example:

```markdown
# Product Plan Index

| ID | Title | Kind | Status | Revision | Delivery | Regression | Current frontier | Owner |
|---|---|---|---|---|---|---|---|---|
| PLAN-0012 | Mobile account creation | MVP | In Progress | 3 | 4/9 shipped | 3/4 active green | WARP-0205, WARP-0206 | Founder |
```

A per-plan status renderer shows:

```text
PLAN-0012 Mobile account creation
Revision: 3
Status: in_progress

Delivery:
  shipped:     4
  in_progress: 1
  ready:       2
  blocked:     0
  planned:     2

DAG:
  WARP-0201 shipped
    -> WARP-0203 shipped
       -> WARP-0205 ready
       -> WARP-0206 ready
    -> WARP-0204 shipped
       -> WARP-0207 planned

Ready frontier:
  WARP-0205
  WARP-0206

Regression:
  active green: 3/4
  waiting for activation: RJ4
  release matrix: not run

Release blockers:
  5 specifications not shipped
  RJ4 not activated
  mobile_full not run
```

This is the VELDO burn-down:

- Count of committed specifications by state
- Current ready frontier
- DAG blockers
- Regression activation and health
- Release blockers

It contains no points, velocity, estimates, individual utilization, or manually reported percentage completion.

## 6. Regression as a planned artifact

## 6.1 Regression is designed with the product

Every Product Plan names the user journeys that must remain correct while its specifications merge.

There are two types:

### Existing invariant journeys

These use:

```yaml
activation:
  when: start
  spec: null
```

They must be green before the first plan specification begins and on every merge candidate.

### New journeys

These use:

```yaml
activation:
  when: spec_shipped
  spec: WARP-0001
owner_spec: WARP-0001
```

The owner specification must create or activate the executable regression proof. From that specification onward, the journey must remain green for every later plan merge.

A cross-feature journey that cannot exist until several prerequisites ship receives a small integration specification after those prerequisites. That specification owns the end-to-end journey and must itself have an observable proof objective.

### 6.2 Per-spec gate

For every plan specification, the gate runs:

1. The specification's required evidence.
2. The repository-wide mandatory gate.
3. Every active plan regression journey.
4. The journey's `per_spec_profile`.
5. Independent review of regression impact.

A specification cannot merge when an active plan journey is red, even if its local acceptance criteria pass.

### 6.3 Release regression gate

The release candidate gate runs on one exact trunk commit or mobile build:

- Every plan journey
- Every release suite
- The full release device profile
- Required accessibility and locale profiles
- Required human design or product journeys
- Rollback or disablement checks
- Any root-plan regression inherited by child plans

No required regression item may be marked deferred at release time. Deferral is a scope change and requires a plan revision.

### 6.4 Mobile device matrix

The device matrix belongs to the Product Plan because it protects the complete product experience, not one screen.

The plan should normally include:

- Minimum supported OS
- Latest supported OS
- Smallest supported screen class
- Current representative screen class
- Tablet when tablet is supported
- Physical devices for release-critical journeys
- Simulator or emulator coverage for per-spec speed
- Required locales, text scaling, orientation, or accessibility modes

Versions are pinned when the plan becomes ready. A mid-plan support-policy change is a plan revision.

The per-spec profile should be small and fast. The release profile should represent the full support promise.

## 7. Release and plan completion

## 7.1 Continuous delivery remains the default

A Product Plan does not normally become a release train.

With `release.mode: continuous`:

- Each proven specification merges immediately.
- Each specification may deploy immediately if its partial state is independently valid.
- Incomplete user experiences remain behind flags or compatibility layers.
- Completion creates a milestone marker on the exact proven trunk state.
- Final activation may occur after the release candidate gate.

Use `release.mode: coordinated` only when batching is inherent to the product or platform, such as:

- Mobile store submission
- Coordinated public launch
- Irreversible migration window
- Contractually fixed customer release
- Legal or regulatory activation
- Protocol or API version cut

Even in coordinated mode, specifications merge continuously. Activation or distribution is coordinated, not code integration.

## 7.2 Release candidate gate

A plan may enter release activation only when:

- The current plan revision is approved.
- Every in-scope direct specification is `shipped`.
- Every required child plan is completed, if applicable.
- Every plan work item is represented in the receipt.
- Full iteration regression is green on the exact release commit or build.
- The full device matrix is green.
- Required design, security, legal, and product reviews have passed.
- Rollback or disablement is verified.
- No unresolved revision impact or revalidation requirement remains.

The plan then moves from `in_progress` to `observing`.

## 7.3 Observation and done

Observation logically follows release activation, so VELDO uses two gates:

| Gate | Purpose |
|---|---|
| Release candidate gate | Decides whether the complete increment may be activated or marked released |
| Completion gate | Decides whether observation justifies calling the iteration done |

The completion gate requires:

- The declared observation window has elapsed.
- Every observation check is within threshold.
- No unresolved release-blocking defect remains.
- Any rollback, disablement, or corrective action has been recorded.
- The Product Plan receipt has been generated.

A low-risk internal increment may declare an observation duration of `0h`, but it must still record deployment or build health.

Long-horizon business outcomes do not keep delivery mechanically open for weeks. The receipt records them as `pending`, and later appends an outcome evaluation. Delivery completion and product-outcome validation remain distinguishable.

## 7.4 Product Plan receipt

Recommended location:

```text
/plans/receipts/PLAN-0012-r3.md
```

Format:

```markdown
---
schema: veldo.plan-receipt/v1
plan: PLAN-0012
plan_revision: 3
plan_commit: <git hash>
kind: mvp
version: 1.0.0
release_mode: continuous
release_commit: <git hash>
released_at: <timestamp>
observation_completed_at: <timestamp>
verdict: completed
specifications:
  - id: WARP-0201
    commit: <git hash>
    proof: proof/WARP-0201/
  - id: WARP-0202
    commit: <git hash>
    proof: proof/WARP-0202/
regression_runs:
  - journey: RJ1
    profile: mobile_full
    result: passed
    artifact: <path>
approvals:
  - lane: design
    reviewer: <identity>
    verdict: pass
observation:
  - check: OBS1
    result: passed
    evidence: <path or signal reference>
outcome_status:
  O1: pending
---

## Delivered outcome

What became available to users.

## Scope reconciliation

What shipped compared with the approved plan revision.

## Regression summary

The journeys, suites, devices, and versions proven.

## Rollout and observation

What was activated, where, and what happened during observation.

## Deviations

Approved deviations, corrective specifications, rollbacks, or residual limitations.

## Outcome follow-up

When and how longer-horizon outcomes will be evaluated.
```

The receipt freezes the plan revision, included proofs, release state, regression evidence, and observation verdict.

## 7.5 MVP and version cuts

- A small MVP is one Product Plan with `kind: mvp`.
- A normal product increment uses `kind: iteration`.
- A coordinated version cut uses `kind: release`.
- The same contract and gates apply to all three.
- A large MVP may use a root MVP plan with child iteration plans.
- The root receipt aggregates child receipts and runs the root regression contract.
- A version number is a release marker, not permission to create a long-lived branch.

## 8. Scope changes and revisions

A ready or active Product Plan may be changed only through:

```text
/veldo:plan revise PLAN-0012
```

The command:

1. Drafts the proposed contract change.
2. Classifies its effect.
3. Identifies affected specifications, regression journeys, dependencies, and receipts.
4. Requires human approval.
5. Increments `revision`.
6. Records the impact in revision history.
7. Updates or blocks affected work.

### 8.1 Invalidation rules

| Change | Effect |
|---|---|
| Editorial clarification with no semantic effect | No proof invalidation; record as editorial commit |
| New future work item with no effect on shipped behavior | New revision; existing unaffected proof may be explicitly carried forward |
| Dependency or ordering change | Affected unstarted specifications return to draft; active work stops until rebound |
| Goal, outcome, non-goal, or cross-cutting constraint change | All potentially affected specifications require impact review |
| Acceptance expectation for an unshipped specification changes | Specification revision and existing proof are invalidated |
| Regression journey or device matrix strengthens | Release is blocked until the new regression requirement passes |
| Regression requirement weakens | Requires explicit human judgment and plan revision |
| Shipped work becomes inconsistent with the new plan | Historical proof remains valid for the old contract, but the plan is blocked pending revalidation, correction, or rollback |
| A shipped work item is removed from scope | It remains in history and the receipt; removal does not pretend it never shipped |

A stale plan binding never silently updates. It must be either:

- Rebound after being declared unaffected
- Revised and re-proven
- Replaced by a corrective specification
- Removed through an approved scope revision

## 9. The two lanes

## 9.1 Lane 1: Planned product work

A Product Plan is required when any of these are true:

- The intended outcome requires more than one specification.
- Several changes together create or materially alter a user journey.
- Specifications require deliberate ordering or dependencies.
- A shared design, compatibility, data, security, analytics, or rollout contract applies.
- Regression must protect behavior across several changes.
- Partial behavior must be hidden until a complete release point.
- The work defines an MVP, launch, product iteration, version, migration, or platform release.
- The PM cannot judge success by reviewing one specification and its proof in isolation.

## 9.2 Lane 2: Standalone work

A direct specification is allowed when the complete outcome fits one independently provable change and has no coordinated product release requirement.

Typical examples:

- A reproducible bug restoring previously intended behavior
- An isolated copy correction
- A small visual correction
- A local accessibility defect
- Documentation
- Internal tooling
- A reversible refactor
- A standing specification instance
- Dependency or configuration maintenance
- Emergency work and its backfill
- A genuinely single-spec enhancement

A bug may still be attached to an active Product Plan when it blocks that plan's release or concerns behavior newly introduced by the plan.

The promotion rule is simple:

> If specification dialogue discovers that the requested outcome needs sibling specifications, shared regression, coordinated activation, or product-level tradeoffs, stop and create a Product Plan before implementation.

This preserves the founder's direct bug path without allowing new products to emerge from a random stream of screen specifications.

## 10. Minimal planning weight

For a five-person startup, a normal Product Plan should usually be:

- One Markdown file
- One planning dialogue
- Roughly 3 to 12 planned specifications
- One feature tree
- One dependency DAG
- A few regression journeys
- One core and one release device profile
- One approved revision
- One generated receipt

There are no mandatory planning meetings, estimates, assignments, or reporting rituals.

The planning agent writes the artifact. The founder or PM answers questions, corrects decisions, and approves it.

A small product iteration should take tens of human minutes to define, not days of document production.

## 11. What changes where

### 11.1 Method changes

| Method location | Minimal addition |
|---|---|
| Core Model | Add: Product Plan is the unit of coordinated product intent; specification remains the unit of delivery |
| New Stage 0 | Add `Stage 0: Define the Product Plan` for planned product work |
| Stage 2 | Require plan binding for planned specifications |
| Stage 4 | Require the Plan Context Bundle before implementation |
| Stage 5 | Record plan ID, revision, item, and regression evidence in proof |
| Stage 6 | Run active plan regression for every child specification |
| Stage 9 | Add plan release candidate and observation behavior |
| Stage 10 | Close the child specification, then update derived plan status |
| Repository Index | Add generated Product Plan index and DAG view |
| Definition of Done | Add Product Plan completion definition |
| Failure Modes | Add random specification stream, stale plan binding, and unplanned regression |
| Adoption Rules | Add Product Planning after specification discipline and before automatic merge |

The new Stage 0 is:

```text
Stage 0: Define the Product Plan

Required for coordinated product work:

1. State the holistic product intent.
2. Define target users, outcomes, guardrails, and non-goals.
3. Build the feature tree.
4. Decompose it into small, independently provable specification leaves.
5. Declare the dependency DAG.
6. Define iteration regression and the device matrix.
7. Define release, rollback, and observation conditions.
8. Validate the plan.
9. Obtain human product approval.
10. Pull the first ready specification frontier.
```

### 11.2 Setup changes

Add:

```text
/plans/index.md
/plans/draft/
/plans/ready/
/plans/active/
/plans/observing/
/plans/completed/
/plans/blocked/
/plans/cancelled/
/plans/receipts/
/.veldo/contracts/product-plan.md
/.veldo/schemas/veldo.plan.v1.schema.json
/.veldo/schemas/veldo.plan-receipt.v1.schema.json
```

Modify:

```text
/.veldo/schemas/veldo.spec.v1.schema.json
```

New specification fields:

```text
lane
plan
plan_revision
plan_item
outcome_refs
feature_refs
depends_on
standalone_reason
```

The setup validator must enforce:

- Valid plan references
- Valid outcome and feature references
- Acyclic dependency graphs
- Exact dependency mirroring
- Regression ownership
- Valid device profiles
- No open decisions at `ready`
- Complete release and observation contracts
- Valid standalone reasons
- No weakening of inherited parent-plan constraints

### 11.3 Plugin changes

Add one skill:

```text
/veldo:plan
```

Supported intents:

```text
/veldo:plan create
/veldo:plan refine PLAN-0012
/veldo:plan approve PLAN-0012
/veldo:plan pull PLAN-0012
/veldo:plan revise PLAN-0012
/veldo:plan status PLAN-0012
/veldo:plan release PLAN-0012
```

Behavior:

| Command | Result |
|---|---|
| `create` | Runs product-level interview and drafts the Product Plan |
| `refine` | Validates outcomes, decomposition, DAG, regression, and release contract |
| `approve` | Requires human product approval and moves the plan to `ready` |
| `pull` | Selects the next valid frontier item and starts specification-level dialogue |
| `revise` | Produces revision impact analysis and rebinds or blocks affected work |
| `status` | Renders plan progress, DAG, regression state, and blockers |
| `release` | Runs the release candidate gate, observation workflow, and receipt generation |

Modify `/veldo:spec`:

- Accept `plan` and `plan_item`.
- Populate inherited references and dependencies.
- Require a standalone reason when no plan is provided.
- Recommend promotion to `/veldo:plan` when multi-spec product scope is detected.

Modify `/veldo:run`:

- Resolve the Plan Context Bundle.
- Refuse stale revisions.
- Refuse unshipped dependencies.
- Refuse invalid DAG bindings.
- Run active iteration regression.
- Record the plan hash in proof.

Modify index generation:

- Add `plans/index.md`.
- Add Parent and Dependencies columns to `specs/index.md`.
- Render the ready frontier and release blockers.
- Derive all counts from repository artifacts.

### 11.4 PM training document

Add one training module named:

```text
Planning Product Increments in VELDO
```

It contains five sections:

1. **Plan versus specification**
   - When product intent requires a holistic contract
   - Why a screen list is not a product plan

2. **The product planning interview**
   - Users, outcomes, guardrails, scope, non-goals, rollout, and observation

3. **Decomposition**
   - Feature trees
   - Vertical slices
   - Dependency DAGs
   - Progressive specification pull

4. **Regression and release**
   - Protected journeys
   - Mobile device matrices
   - Release candidate and observation gates

5. **The two-lane decision**
   - When direct specifications are correct
   - When work must be promoted to a Product Plan
   - How scope revisions are handled

The PM is trained to approve product truth, not to maintain statuses or write Markdown. The agent remains the scribe.

## 12. The VELDO 1.0 planning rule

The added rule is:

> Do not begin a stream of planned product specifications until the repository contains the whole outcome, its boundaries, its decomposition, its valid order, its regression contract, and its release condition.

For bugs and genuinely isolated work:

```text
Intent -> Specification -> Implementation -> Proof -> Review -> Merge
```

For product iterations, MVPs, and releases:

```text
Holistic intent
  -> Product Plan
  -> Ordered small specifications
  -> Continuous proven merges
  -> Iteration regression
  -> Release and observation
  -> Receipt
```

This preserves VELDO's speed and small-spec law while eliminating random product construction.