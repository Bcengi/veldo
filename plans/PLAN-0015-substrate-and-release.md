---
schema: veldo.plan/v1
id: PLAN-0015
title: The substrate and the release - environments as declared versioned artifacts, infrastructure changing through the same loop with cost in the proof and irreversibility respected, release as risk-classed promotion with a required rollback plan, drift watched in-session, environments ephemeral by declaration
kind: mvp
status: released
revision: 2
owner: dmitry
approved_by: dmitry
approved_at: 2026-07-22
risk: standard

outcomes:
  - id: O1
    becomes_true: >
      The substrate is declared, versioned, and true in the repository.
      Environments and infrastructure are declared artifacts - what exists,
      where, in which version - validated like every other contract, so the
      repository is the source of truth for what SHOULD be running, and
      changing the substrate means changing the declaration first, on the
      record.
    measure: >
      A structurally invalid substrate declaration refuses at contract time
      with the error named; the example fixtures validate; a declaration
      change flows as an ordinary spec through the loop; a repository with no
      substrate declarations is byte-identically unaffected.
  - id: O2
    becomes_true: >
      Infrastructure changes through the same loop as everything else -
      specified, proven, reviewed, gated - plus the organs its dangers demand.
      COST joins the proof: an infrastructure change carries its projected
      cost delta and the gate holds it to a declared budget, so the agent that
      quietly provisions four hundred instances is not a risk, it is a failed
      check. IRREVERSIBILITY is respected: deleting or migrating a stateful
      resource is not a git revert, so destructive actions carry the highest
      risk class, prepare-and-execute, and the two-key discipline.
    measure: >
      On fake environments: an infrastructure change without a cost delta in
      its proof refuses at the gate; a seeded over-budget delta refuses with
      the budget named; a destructive change with either key missing (recorded
      human authorization, independent confirmation verdict) refuses, and with
      both keys bound to the change it executes; a reversible in-budget change
      flows through unchanged.
  - id: O3
    becomes_true: >
      The release is a risk-classed promotion, not a ceremony. A proven change
      promotes through the declared environments with staged rollout and
      canary where its risk class demands, and a rollback plan is a required
      artifact of every promotion - no rollback plan, no promotion. All of it
      proven offline against fake environments; wiring to any real environment
      is a separate per-system human-approved act.
    measure: >
      On fake environments: a promotion without a rollback plan refuses; a
      staged rollout with canary executes in declared order and halts on a
      failed canary; the promotion, its stages, and any rollback are recorded
      on the event stream; nothing in the plan touches a real environment.
  - id: O4
    becomes_true: >
      Drift is watched, in-session, and answered through the loop. Declared
      state and actual state are compared inside normal sessions and gate runs
      (the tripwire pattern, never a daemon); a divergence surfaces as a named
      finding, and each drift drafts exactly one reconciliation unit that only
      a human promotes - reality never silently redefines the declaration.
    measure: >
      A seeded drift between a declaration and a fake actual-state snapshot
      surfaces in the gate output and status with the resource named; exactly
      one reconciliation draft appears, idempotently under re-runs; the
      conformance test proves nothing runs detached.
  - id: O5
    becomes_true: >
      Environments are cheap enough to be disposable. A per-change ephemeral
      environment is a declared, reproducible, disposable concept: created
      from the declaration, identical every time, torn down without residue,
      its lifecycle recorded. The seam is designed and proven against a fake
      provider; real provisioning sits behind the same per-system
      human-approved wiring as everything live.
    measure: >
      On the fake provider: an ephemeral environment is created from its
      declaration twice and the results are identical; teardown leaves no
      resource behind (the fake provider's ledger is empty); create, use, and
      teardown appear on the event stream; scope of the day-one reference
      implementation per D5.

non_goals:
  - id: NG1
    text: >
      No live infrastructure operations. Every item is proven offline against
      fake environments, fake providers, and fake actual-state snapshots;
      applying anything to a real environment - promotion, reconciliation,
      ephemeral provisioning - is a separate, per-system, human-approved
      enablement act outside this plan, in the same posture as the production
      responder.
  - id: NG2
    text: >
      No daemons and no detached processes. Drift comparison and every other
      pass runs inside the gate, status, and the weekly pass; if a standing
      watcher is ever wanted it is a separate, explicitly approved, opt-in,
      off-by-default component, not part of this plan.
  - id: NG3
    text: >
      No blessed infrastructure tool. The plan defines a seam with pluggable
      adapters and a fake reference implementation; whether a specific tool
      becomes the documented default is D1, and the mechanical logic never
      depends on any vendor.
  - id: NG4
    text: >
      No cost-optimization platform. The cost organ holds a change's projected
      delta to a declared budget, full stop; forecasting, optimization, and
      billing reconciliation are out of scope.
  - id: NG5
    text: >
      No machine-authorized destruction, ever. A destructive action on a
      stateful resource never executes on machine judgment alone at any
      autonomy posture; the two-key discipline has no bypass, and this plan
      never adds one.
  - id: NG6
    text: >
      No rebuild of what ships. The ephemeral seam extends the existing
      environment provisioning reference, the promotion machinery extends the
      existing release and rollback automation reference, and the risk floors
      ride the existing policy tiers; nothing is reinvented.

constraints:
  - id: C1
    text: >
      Every item is built through VELDO itself: spec, gate, proof, independent
      fresh-context review; every safety property lands as a negative test
      (anti-vacuity) - the refusals are the product.
  - id: C2
    text: >
      The declaration is the truth. Drift reconciles reality toward the
      declaration unless a human first revises the declaration through the
      loop; actual state never overwrites declared intent, and the
      reconciliation unit says which direction it moves and why.
  - id: C3
    text: >
      Fail closed: an unknown resource kind, an unresolvable environment
      reference, a missing cost delta, a missing rollback plan, or an
      unverifiable actual-state snapshot refuses; doubt never downgrades to a
      warning.
  - id: C4
    text: >
      Destructive means proven destructive handling: any action that deletes
      or migrates stateful resources carries the critical tier
      (prepare-and-execute, recorded human approval, independent verdicts per
      the existing policy) and the two-key discipline aligned with the
      production responder's pattern (soft seam, per C6).
  - id: C5
    text: >
      Secrets in substrate declarations are references only, never values,
      extending the established keep-tokens posture and aligned with the
      security plan's reference seam (soft seam, per C6); generated
      infrastructure least privilege is PLAN-0013's gate concern and is
      referenced, not duplicated, here.
  - id: C6
    text: >
      Cross-plan seams are soft and prose-declared, never dependency edges:
      the cost organ consumes PLAN-0014's budget machinery where shipped and
      a declared static budget where not; the destructive floor aligns with
      PLAN-0012's two-key pattern over today's policy tiers; drift uses the
      tripwire pattern PLAN-0011 established; each stands down honestly where
      the other plan has not shipped.
  - id: C7
    text: >
      The canon is engine: every schema, check, adapter seam, and
      skill lands in the engine, syncs byte-identical to this repository's
      instances, and stays fully generic; all machinery is runnable
      in-session.

feature_tree:
  - id: F1
    title: Substrate declarations - environments and infrastructure as versioned validated artifacts
    outcome_refs: [O1]
  - id: F2
    title: Infrastructure through the loop - cost in the proof, irreversibility respected
    outcome_refs: [O2]
  - id: F3
    title: The promotion pipeline - release as risk-classed promotion with required rollback
    outcome_refs: [O3]
  - id: F4
    title: Drift tripwires - declared versus actual, answered through the loop
    outcome_refs: [O4]
  - id: F5
    title: Ephemeral environments - declared, reproducible, disposable
    outcome_refs: [O5]
  - id: F6
    title: Release - the engine ships it and the docs are true
    outcome_refs: [O1, O3]

work:
  - item: W1
    spec: WARP-1501
    title: >
      Substrate declarations and their validator. A versioned declaration
      format for environments and infrastructure - resources, versions,
      relationships, per-environment parameters - validated structurally with
      unknown kinds rejected at contract time, plus example fixtures. The
      repository becomes the source of truth for what should be running;
      declaration changes are ordinary specs through the loop. Secrets appear
      as references only (C5).
    feature_refs: [F1]
    depends_on: []
    order: 10
  - item: W2
    spec: WARP-1502
    title: >
      The infrastructure change type. Declaration diffs flow the existing loop
      with infra-specific mechanics: a plan-then-apply separation against a
      pluggable execution seam (adapters per D1, fake reference
      implementation), the planned effect recorded in the proof, and apply
      proven offline against fake environments. Adoption-safe: repositories
      without substrate declarations are untouched.
    feature_refs: [F2]
    depends_on: [WARP-1501]
    order: 20
  - item: W3
    spec: WARP-1503
    title: >
      Cost in the proof. An infrastructure change carries its projected cost
      delta as a required proof element (source per D2: declared static
      estimates first, pricing adapters as slots), and the gate holds the
      delta to the declared budget for the affected environment - over-budget
      refuses with the budget named. Consumes PLAN-0014's budget machinery
      where shipped, a declared static budget where not (soft seam, per C6).
    feature_refs: [F2]
    depends_on: [WARP-1502]
    order: 30
  - item: W4
    spec: WARP-1504
    title: >
      The destructive-action floor. Classify substrate operations by
      reversibility; deleting or migrating stateful resources carries the
      critical tier - prepare-and-execute, recorded human approval,
      independent verdicts per today's policy - plus the two-key discipline
      aligned with the production responder's pattern: human authorization
      AND an independent fresh-context confirmation, both bound to the exact
      change. Either key missing refuses; no bypass exists.
    feature_refs: [F2]
    depends_on: [WARP-1502]
    order: 35
  - item: W5
    spec: WARP-1505
    title: >
      The promotion pipeline. Release as risk-classed promotion of proven
      changes through the declared environments: promotion gating defaults per
      risk class (table per D3), staged rollout and canary where the class
      demands, halt on failed canary, and a rollback plan as a required
      artifact of every promotion - no rollback plan, no promotion. Extends
      the existing release and rollback automation reference; promotions and
      stages recorded on the event stream; proven end to end on fake
      environments.
    feature_refs: [F3]
    depends_on: [WARP-1502]
    order: 40
  - item: W6
    spec: WARP-1506
    title: >
      Drift tripwires. A mechanical comparison of declared state against an
      actual-state snapshot (fake snapshots offline; live snapshot acquisition
      is per-system wiring outside this plan), surfaced as named findings in
      the gate output, status, and the weekly pass per D4 - the tripwire
      pattern, in-session only, never a daemon. Each drift drafts exactly one
      reconciliation unit for human promotion, idempotently, honoring C2's
      direction rule.
    feature_refs: [F4]
    depends_on: [WARP-1501]
    order: 45
  - item: W7
    spec: WARP-1507
    title: >
      The ephemeral environment seam. Per-change environments as a declared,
      reproducible, disposable concept: create from declaration, identical
      results on repeat, guaranteed teardown with a residue check against the
      fake provider's ledger, lifecycle on the event stream. Extends the
      existing ephemeral environment provisioning reference to the substrate
      declarations; day-one reference scope per D5; real provisioning stays
      behind per-system human-approved wiring.
    feature_refs: [F5]
    depends_on: [WARP-1501]
    order: 50
  - item: W8
    spec: WARP-1508
    title: >
      Release. Land the declaration schema, the change type, the cost and
      destructive-floor checks, the promotion pipeline, the drift comparator,
      and the ephemeral seam in the canonical engine so /veldo:init lays them
      down and the packs carry them; make the docs true (the method and setup
      documents gain the substrate and the release as shipped behavior, fully
      generic, live wiring documented as a separate human act); record
      capabilities honestly; bump the plugin version; mark the plan released
      once the regression is green.
    feature_refs: [F6]
    depends_on: [WARP-1503, WARP-1504, WARP-1505, WARP-1506, WARP-1507]
    order: 80

regression:
  journeys:
    - id: RJ1
      title: >
        An invalid substrate declaration refuses with the error named; the
        example fixtures validate; a repository without declarations is
        byte-identically unaffected.
      activation: {when: start}
      suite: declaration conformance and scripts/verify.sh
    - id: RJ2
      title: >
        An infrastructure change without a cost delta refuses; a seeded
        over-budget delta refuses with the budget named; an in-budget
        reversible change flows through the loop unchanged.
      activation: {when: after:WARP-1503}
      suite: cost-in-the-proof conformance (fake environments)
    - id: RJ3
      title: >
        A destructive change on a stateful resource refuses with either key
        missing and executes on the fake environment only with both keys bound
        to the change; no bypass path exists.
      activation: {when: after:WARP-1504}
      suite: destructive-floor conformance
    - id: RJ4
      title: >
        A promotion without a rollback plan refuses; a staged rollout with
        canary executes in declared order, halts on a failed canary, and lands
        its records on the event stream.
      activation: {when: after:WARP-1505}
      suite: promotion pipeline conformance (fake environments)
    - id: RJ5
      title: >
        A seeded drift surfaces in the gate and status with the resource named
        and drafts exactly one reconciliation unit, idempotently; nothing runs
        detached.
      activation: {when: after:WARP-1506}
      suite: drift tripwire conformance
    - id: RJ6
      title: >
        An ephemeral environment is created reproducibly from its declaration
        and torn down without residue on the fake provider, with the lifecycle
        recorded.
      activation: {when: after:WARP-1507}
      suite: ephemeral environment conformance

release:
  milestone: >
    VELDO substrate and release v1 - environments and infrastructure are
    declared, versioned, validated artifacts changing through the same loop as
    code, with projected cost held to budget in the proof, destructive actions
    behind the critical tier and two keys, release as risk-classed promotion
    with staged rollout, canary, and a required rollback plan, drift watched
    in-session and answered through drafted reconciliation units, and
    ephemeral per-change environments as a proven seam - all offline against
    fake environments, with live wiring a separate per-system human act.
  mode: continuous
  require_all_work_shipped: true
  require_full_regression: true
  rollback: >
    Remove or leave absent the substrate declarations and every check and
    pipeline stands down (adoption-safe posture); git revert the plugin
    version bump; declarations, promotion records, and drift findings are
    inert data and keep their history.
  observation:
    duration: >
      Run the full lifecycle on fake environments across the seeded classes -
      declaration change, in-budget and over-budget deltas, a destructive
      change under two keys, a staged canary promotion with one rollback, a
      drift reconciliation, and an ephemeral create-use-teardown - reviewed by
      the founder before any real environment wiring is considered.

open_decisions: []

resolved_decisions:
  - id: D1
    text: >
      The infrastructure seam.
    resolution: >
      A reference-only interface with pluggable adapters and a fake provider,
      with no named infrastructure-as-code tool blessed; naming a specific tool
      stays a per-repo documentation choice. Decided by the founder 2026-07-22
      via "use recommendations" (start the build).
    resolved_by: founder via 'use recommendations' (start the build), 2026-07-22
    resolved_at: 2026-07-22
  - id: D2
    text: >
      The cost-delta source.
    resolution: >
      Declared static estimates per resource kind first, offline and
      deterministic with no pricing adapters yet; provider pricing adapters stay
      a later, optional input over that floor. Decided by the founder
      2026-07-22 via "use recommendations" (start the build).
    resolved_by: founder via 'use recommendations' (start the build), 2026-07-22
    resolved_at: 2026-07-22
  - id: D3
    text: >
      Promotion gating defaults per risk class.
    resolution: >
      Ship the recommended default gating table with W5 (which classes require
      staged rollout, canary, and explicit human confirmation), as tunable
      configuration for the founder. Decided by the founder 2026-07-22 via "use
      recommendations" (start the build).
    resolved_by: founder via 'use recommendations' (start the build), 2026-07-22
    resolved_at: 2026-07-22
  - id: D4
    text: >
      Drift-check surfaces and cadence.
    resolution: >
      All three surfaces: the gate run, veldo status, and the weekly pass, with
      a per-run cost ceiling so the comparison stays within the gate's time
      budget. Decided by the founder 2026-07-22 via "use recommendations"
      (start the build).
    resolved_by: founder via 'use recommendations' (start the build), 2026-07-22
    resolved_at: 2026-07-22
  - id: D5
    text: >
      Ephemeral scope on day one.
    resolution: >
      The recommended minimum: declaration plus fake provider plus teardown
      guarantees; a real container-level adapter stays an optional per-repo
      extension. Decided by the founder 2026-07-22 via "use recommendations"
      (start the build).
    resolved_by: founder via 'use recommendations' (start the build), 2026-07-22
    resolved_at: 2026-07-22
---

## Intent

VELDO today ends at the merge, and the founder's question exposes what is
missing: release into WHERE? A change that is specified, proven, reviewed, and
landed still has no declared place to run, no path from trunk to users, and no
answer for the infrastructure underneath it all. The old world made
infrastructure someone else's department; this plan makes it code in the same
repository, moving through the same loop as everything else - specified,
proven, reviewed, gated - because at agent speed an undeclared substrate is
where the next class of silent failures lives. The repository becomes the
source of truth for what SHOULD be running, and the substrate is kept true the
way specs are: change the declaration first, on the record, then let reality
follow.

Infrastructure's special dangers get their own organs rather than a general
pass. Cost joins the proof: an infrastructure change carries its projected
cost delta and the gate holds it to a declared budget, so the agent that
quietly provisions four hundred instances is not a risk, it is a failed check
(the delta consumes the effort plan's budget machinery where shipped, a
declared static budget where not). Irreversibility is respected as physics: a
deleted database is not a git revert, so destructive actions on stateful
resources carry the critical tier - prepare-and-execute, recorded human
approval - plus the two-key discipline the production responder established,
and no bypass exists. Least privilege on generated infrastructure is already
the security plan's gate concern and is referenced, not duplicated. On that
substrate the release stops being a ceremony: promotion of proven changes
through declared environments, risk-classed, staged and canaried where the
class demands, with a rollback plan required of every promotion. Drift between
declared and actual state is watched by the same tripwire pattern the
architecture organ put on assumptions - in-session, never a daemon - and every
drift drafts a reconciliation unit a human promotes, in the direction the
declaration commands. And because construction is cheap, environments become
declared, reproducible, disposable artifacts, fresh per change where it helps.

Three postures bind the plan. Everything is proven offline against fake
environments, fake providers, and fake actual-state snapshots; wiring any of
it to a real environment is a separate per-system human-approved act, exactly
the responder's posture. Nothing runs detached: drift comparison and every
other pass lives in the gate, status, and the weekly pass. And this is a
receipts plan under the publication gate: the method's companion writing
opens its release chapter with the substrate question and does not publish
ahead of the machinery; releasing this plan turns that chapter from design
into receipts, with all shipped material fully generic in the engine.

## Data provenance - existing machinery versus new instrumentation

Reused as-is (no reinvention):

- The ephemeral environment provisioning reference and the release and
  rollback automation reference already shipped in the engine; W7 and W5
  extend them to the substrate declarations rather than rebuilding them.
- The policy tiers, including the critical tier's prepare-and-execute and
  recorded human approvals, which the destructive floor rides unchanged.
- The event stream for promotion, drift, and lifecycle records; the gate's
  check slots; the runner-suite adapter posture for pluggable seams.
- The tripwire pattern (PLAN-0011) for drift and the two-key pattern
  (PLAN-0012) for destruction - soft seams, standing down honestly where
  those plans have not shipped.

New instrumentation this plan introduces:

- The substrate declaration schema, validator, and fixtures (W1).
- The infrastructure change type with plan-then-apply against the pluggable
  execution seam and its fake provider (W2).
- The cost-delta proof element and budget check (W3) and the
  reversibility classification with the two-key execution path (W4).
- The promotion pipeline with staging, canary, halt, and required rollback
  artifacts (W5).
- The drift comparator and fake actual-state snapshot format (W6) and the
  ephemeral lifecycle extension with the residue check (W7).

## Ordered delivery rationale

W1 (the declarations) is the single root: every organ reads it. W2 (the
change type) makes declarations changeable through the loop and carries the
execution seam the rest ride on. W3 (cost), W4 (the destructive floor), and
W5 (promotion) fan out from W2 in parallel - three independent organs on one
seam. W6 (drift) and W7 (ephemeral) hang directly off the declarations and
parallel everything after W1. W8 releases once every lane has shipped and the
regression is green. The frontier after approval is W1 alone; the widest
point is five parallel items (W3, W4, W5, W6, W7).

## Out of scope

Live infrastructure operations of any kind, including live snapshot
acquisition and real provisioning (NG1); daemons or standing watchers (NG2);
blessing a specific infrastructure tool in the mechanical path (NG3, D1);
cost forecasting or optimization (NG4); any machine-only path to destructive
actions (NG5); rebuilding the provisioning, release automation, or policy
machinery this plan extends (NG6). The companion book chapter itself is not
work in this repository; this plan only makes its subject true.

## Revisions

Revision 1 (2026-07-21): drafted at intake from the founder's question
("what about infrastructure? Release into where?") and the method's release
chapter design: substrate declarations as versioned artifacts, infrastructure
as an ordinary loop change with cost in the proof and the destructive-action
floor, release as risk-classed promotion with staged rollout, canary, and a
required rollback plan, drift watched in-session by the tripwire pattern, and
ephemeral per-change environments as a declared seam. Cross-plan seams to the
effort budgets (PLAN-0014), the two-key pattern (PLAN-0012), least-privilege
infrastructure (PLAN-0013), and the tripwire pattern (PLAN-0011) are soft and
prose-declared. D1 through D5 are surfaced for the founder, not resolved.
Status draft: authored, not activated; no work starts until the plan leaves
draft by a recorded human approval.

Revision 2 (2026-07-22): the founder gave the go to start the build ("start the
5 plans build") and chose "use recommendations", resolving all five open
decisions to their recommended defaults, each now recorded in
resolved_decisions above: D1 reference-only infrastructure seam with a fake
provider and no blessed IaC tool, D2 static estimates first with no pricing
adapters yet, D3 ship the recommended promotion-gating table with W5, D4 drift
checks on the gate, status, and the weekly pass, D5 ephemeral scope as
declaration plus fake provider plus teardown guarantees. open_decisions is now
empty. No scope change; recording decisions is not approval, so status stays
draft and leaving draft still requires a separate recorded human approval.

Approved (2026-07-22): the founder approved the plan to leave draft on the go to
start the build ("start the 5 plans build"); status set to ready, approved_by
dmitry, approved_at 2026-07-22. Per the repo's approve pattern the approval
flips status and records the approver without bumping the revision. The ready
frontier (WARP-1501) is now live for pulling into specs.
