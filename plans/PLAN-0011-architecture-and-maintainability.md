---
schema: veldo.plan/v1
id: PLAN-0011
title: Architecture and maintainability - the intended shape becomes a contract the gate enforces, foundational decisions become adversarially reviewed human-decided units with living tripwires, and entropy is measured and restored through the loop
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
      The system's intended shape is an artifact, not a memory. A versioned
      architecture contract lives in the repository: areas and module boundaries,
      allowed dependencies, patterns in force, invariants, and budgets, machine
      elaborated and human approved, and changing the shape means changing the
      contract first, on the record, exactly the way specs are kept true.
    measure: >
      The contract file validates under the new contract check; a structurally
      invalid contract or one that left draft without a recorded human approval
      fails the gate; and this repository carries its own approved contract as the
      first instance.
  - id: O2
    becomes_true: >
      Everything mechanizable about the declared shape is enforced by the gate. A
      change that violates a dependency or import boundary, a size or complexity
      budget, a duplication limit, or a declared pattern fails scripts/verify.sh
      with the rule named, before any reviewer sees it. Architecture stops being
      taste at merge time and becomes a check that fails.
    measure: >
      A seeded violation of each rule class refuses with the rule named, removing
      the violation turns the same gate green (negative tests in the suite), and a
      repository with no contract is byte-identically unaffected.
  - id: O3
    becomes_true: >
      No change is built placeless. A spec declares, at elaboration time, where in
      the declared shape it lives and what footprint it creates, so placement is
      validated at the cheapest moment, before anything is built; and the
      independent review grades a second dimension beyond spec-conformance, where
      correct-but-does-not-fit is a legitimate rework verdict.
    measure: >
      With a contract present, a spec without a placement that resolves to a
      contract area cannot reach ready and is never claimed; a conformance test
      shows a correct-but-misfit change refused by review with a shape_fit finding.
  - id: O4
    becomes_true: >
      A foundational choice (technology, architecture style, communication shape,
      tooling) is a first-class, recorded, adversarially reviewed unit of work
      decided by a human against the stated problem class, never today's scale,
      and never made silently inside a feature's implementation. Scrutiny scales
      with reversal cost: the irreversible choices get the slowest, most
      independent judgment the policy can express.
    measure: >
      A decision record with elaborated options, per-option dead-end conditions,
      and an adversarial fresh-context verdict exists before dependent work
      proceeds; an elaboration that hits an undecided foundational choice blocks
      and surfaces the decision; no machine-decided state exists in the contract.
  - id: O5
    becomes_true: >
      Decision records are living tripwires, not memos. Each recorded assumption
      carries a measurable signal and a stated dead-end condition, and the system
      checks those signals inside normal sessions and gate runs, surfacing an
      approaching breach while there is still time to re-decide deliberately.
      Wrong foundations are caught by assumption breach, not by outage.
    measure: >
      A decision with a seeded breached signal surfaces as a named finding in the
      gate output and in veldo status, and exactly one re-decision draft appears
      for the human; the conformance test also proves nothing runs detached (no
      process outlives the session, no timer or daemon is installed).
  - id: O6
    becomes_true: >
      Entropy has a number and a response. Cost-to-change per contract area is
      derived from what the loop already records (tokens, review cycles, gate
      failures, human minutes) joined to areas through placement declarations, and
      a threshold crossing generates a restoration spec that flows through the
      normal loop, whose post-restoration measure proves the refactor paid off.
    measure: >
      The metrics derivation renders a per-area cost-to-change series from the
      existing event stream plus placements; a seeded crossing yields exactly one
      draft restoration spec that only a human can promote; and the closed loop
      reports the cost delta after the restoration ships.

non_goals:
  - id: NG1
    text: >
      No detached monitoring. The tripwire pass, the entropy derivation, and
      restoration drafting run inside normal VELDO sessions, gate runs, and the
      weekly index pass, never as daemons, timers, crontabs, or background
      processes (PLAN-0007 NG1 posture, restated). If a standing mechanism is
      ever wanted it is a separate, explicitly human-approved opt-in, off by
      default, and it is not part of this plan.
  - id: NG2
    text: >
      No machine-made foundations and no self-approval. The machine elaborates
      option spaces, attacks proposals in review, and drafts restoration and
      re-decision units; it never decides a foundational choice, never promotes
      its own drafts to ready, and never lowers a risk tier.
  - id: NG3
    text: >
      No architecture platform. No graph database, no external fitness-function
      service, no heavyweight modeling tool as a required dependency; the checks
      are stdlib-proportionate reference implementations with pluggable slots, in
      the same posture as the runner suite.
  - id: NG4
    text: >
      No rebuild of the loop. This plan fills seams in the shipped gate,
      validator, review, metrics, and plan machinery; it does not redesign them,
      and existing repositories that never adopt a contract see no behavior
      change.
  - id: NG5
    text: >
      No unmechanizable theater. A shape rule that cannot be checked mechanically
      stays in the review lane as reviewer guidance, honestly labeled in the
      contract; the gate never carries a vacuous check that cannot refuse.

constraints:
  - id: C1
    text: >
      Every item is built through VELDO itself: spec, gate, proof, independent
      fresh-context review; and every new mechanical check ships with a negative
      test proving it refuses (the anti-vacuity rule).
  - id: C2
    text: >
      Adoption-safe fail-closed: a repository without an architecture contract is
      untouched (every new check stands down), and the moment a contract exists
      the checks fail closed; partial adoption never weakens an existing gate.
  - id: C3
    text: >
      Proportionality: the contract and its checks stay cheaper than the drift
      they prevent - readable file formats, stdlib implementations, no signing or
      ledger formalism; regulated domains may extend.
  - id: C4
    text: >
      All monitoring is in-session: the tripwire and entropy passes are ordinary
      functions invoked by the gate, by veldo status, and by the weekly pass, and
      they complete within a gate run's time budget.
  - id: C5
    text: >
      The canon is engine: every new module, check, skill change, and
      contract template lands in the engine, syncs byte-identical to this
      repository's instances, and stays fully generic (no company, product, or
      project references anywhere in shipped material).
  - id: C6
    text: >
      Decisions are judged against the problem class: every decision record
      states the problem class explicitly, elaboration and review argue against
      the class rather than the current deployment, and "it is only one process
      today" is not a rationale the record may carry.

feature_tree:
  - id: F1
    title: The architecture contract - the shape of the system as a versioned, human-approved artifact
    outcome_refs: [O1]
  - id: F2
    title: Shape enforcement at the gate - mechanizable rules fail the build, not the retrospective
    outcome_refs: [O2]
  - id: F3
    title: Placement, footprint, and the shape-fit review lane
    outcome_refs: [O3]
  - id: F4
    title: Foundational decisions as first-class, adversarially reviewed, human-decided units
    outcome_refs: [O4]
  - id: F5
    title: Living tripwires - assumptions monitored in-session, breach found before outage
    outcome_refs: [O5]
  - id: F6
    title: Entropy measured and reconciled - cost-to-change per area and restoration through the loop
    outcome_refs: [O6]
  - id: F7
    title: Release - the engine ships it and the docs are true
    outcome_refs: [O1, O6]

work:
  - item: W1
    spec: WARP-1101
    title: >
      The architecture contract artifact and its validator. A versioned contract
      file in .veldo/ (naming gated on D1) that states the system's intended shape:
      areas and module boundaries, allowed dependencies between them, patterns in
      force, invariants, and size and complexity budgets, each rule marked
      mechanizable or review-lane. Validated structurally like a plan (unknown rule
      kinds rejected at contract time), and it leaves draft only by a recorded
      human approval; changing the shape means changing the contract first, on the
      record. The proof includes authoring this repository's own contract as the
      first instance.
    feature_refs: [F1]
    depends_on: []
    order: 10
  - item: W5
    spec: WARP-1105
    title: >
      The foundational decision record. A first-class unit of work for the choices
      that pass every test while being wrong: technology, architecture style,
      communication shape, tooling. The machine elaborates the option space (the
      real options, their trade-offs, and what each one dead-ends at and when)
      against the stated problem class, never today's scale; only a human decides,
      on the record, with a reversal-cost class and assumptions carrying
      measurable signals and stated dead-end conditions. An elaboration that hits
      an undecided foundational choice blocks and surfaces the decision; no
      machine-decided state exists.
    feature_refs: [F4]
    depends_on: []
    order: 15
  - item: W2
    spec: WARP-1102
    title: >
      Gate enforcement of the mechanizable shape rules. A shape check wired into
      scripts/verify.sh that reads the contract and fails the gate on a violation:
      dependency and import boundaries, module size and complexity budgets,
      duplication detection, and declared pattern conformance. Stands down when no
      contract exists (adoption-safe) and fails closed when one does;
      stdlib-proportionate reference implementation with a pluggable per-language
      slot (tooling gated on D6), shipped with negative tests where each seeded
      violation refuses with the rule named.
    feature_refs: [F2]
    depends_on: [WARP-1101]
    order: 20
  - item: W3
    spec: WARP-1103
    title: >
      Placement and footprint at elaboration. Specs gain a placement declaration
      (which contract area the change lives in and which declared patterns it
      follows) and a footprint (what it touches, what it creates, whether a new
      module or a cross-boundary edge is born); the elaboration skill asks for
      them, and the validator refuses a ready spec without a placement that
      resolves to a contract area whenever a contract exists. A footprint that
      creates a module or crosses a boundary raises the risk tier; nothing lowers
      it.
    feature_refs: [F3]
    depends_on: [WARP-1101]
    order: 25
  - item: W4
    spec: WARP-1104
    title: >
      The shape-fit review dimension. The independent reviewer receives the
      contract and the spec's placement alongside the spec, the final diff, and
      the proof, and grades a second dimension beyond spec-conformance: does this
      change fit the declared shape. Correct-but-does-not-fit is a legitimate
      rework verdict (severity default per D4), the verdict contract carries the
      shape_fit finding, and a conformance test proves a correct-but-misfit change
      is refused.
    feature_refs: [F3]
    depends_on: [WARP-1101, WARP-1103]
    order: 30
  - item: W6
    spec: WARP-1106
    title: >
      Adversarial decision review. A fresh-context reviewer whose brief is to
      attack a proposed decision before the human decides: what breaks first at
      ten times the problem class, which future requirement class the choice
      precludes, what a mature system in this domain would choose, and whether the
      tool is proposed because it is right or because it was near. Scrutiny scales
      with the reversal-cost class through the existing risk tiers (mapping per
      D5): the irreversible choices carry the policy's highest tier, with recorded
      human approval and the most independent verdicts.
    feature_refs: [F4]
    depends_on: [WARP-1105]
    order: 35
  - item: W7
    spec: WARP-1107
    title: >
      Decision tripwires, monitored in-session. A mechanical pass over decision
      records that compares each assumption's declared signal against its current
      recorded value (signal sourcing per D3) and surfaces approaching-breach and
      breached assumptions as named findings in the gate output, in veldo status,
      and at the weekly pass. It runs only inside normal sessions and gate runs,
      never as a daemon or timer; a breach drafts exactly one re-decision unit for
      the human and never re-platforms anything itself.
    feature_refs: [F5]
    depends_on: [WARP-1105]
    order: 40
  - item: W8
    spec: WARP-1108
    title: >
      Entropy metrics - cost-to-change per area. Derive a per-area cost-to-change
      series from what the loop already records (per-event tokens and cost, gate
      failures, review cycles, human minutes) joined to contract areas through the
      placement declarations and the files each change touched, and put the static
      shape measures from the gate (duplication, complexity, boundary pressure) on
      the same per-area map. Extends the existing metrics derivation and
      dashboard; a rotting area becomes a number that trends, not an opinion.
    feature_refs: [F6]
    depends_on: [WARP-1102, WARP-1103]
    order: 50
  - item: W9
    spec: WARP-1109
    title: >
      Restoration-spec generation. A threshold crossing on a per-area entropy
      series (threshold policy per D2) generates restoration intent: the machine
      drafts a restoration spec naming the area, the crossed rule, and the
      expected post-restoration measure, as a draft that only a human promotes;
      the work then flows through the normal loop like any spec, and the
      post-restoration measure closes the loop by reporting the cost delta.
      Idempotent: re-deriving the same crossing never drafts a duplicate.
    feature_refs: [F6]
    depends_on: [WARP-1108]
    order: 60
  - item: W10
    spec: WARP-1110
    title: >
      Release. Land the new machinery in the canonical engine so /veldo:init lays
      it down and the packs carry it, make the docs true (the method and setup
      documents gain the architecture organ as shipped behavior, fully generic),
      record the capabilities honestly in the manifest, bump the plugin version,
      and mark the plan released once the regression is green.
    feature_refs: [F7]
    depends_on: [WARP-1102, WARP-1104, WARP-1106, WARP-1107, WARP-1109]
    order: 80

regression:
  journeys:
    - id: RJ1
      title: >
        A seeded violation of each mechanizable rule class (boundary, budget,
        duplication, pattern) fails the gate with the rule named, and the clean
        tree stays green.
      activation: {when: after:WARP-1102}
      suite: shape-check negative tests under scripts/verify.sh
    - id: RJ2
      title: >
        With a contract present, a spec without a resolving placement never
        reaches ready and is never claimed; a placed spec flows to shipped
        unchanged.
      activation: {when: after:WARP-1103}
      suite: validator and frontier conformance
    - id: RJ3
      title: >
        A correct-but-misfit change is refused by independent review with a
        shape_fit finding and is reworked to fit.
      activation: {when: after:WARP-1104}
      suite: review conformance over a fixture change
    - id: RJ4
      title: >
        An elaboration that hits an undecided foundational choice blocks; a
        decided, adversarially reviewed record unblocks it; no machine-decided
        state exists.
      activation: {when: after:WARP-1106}
      suite: decision conformance
    - id: RJ5
      title: >
        A seeded assumption breach surfaces in the gate output and veldo status
        and drafts exactly one re-decision unit; re-running the pass creates no
        duplicate and spawns nothing that outlives the session.
      activation: {when: after:WARP-1107}
      suite: tripwire conformance (idempotency and no-detach)
    - id: RJ6
      title: >
        A seeded entropy crossing drafts exactly one restoration spec that only a
        human can promote, and the post-restoration delta is reported once the
        restoration ships.
      activation: {when: after:WARP-1109}
      suite: entropy-to-restoration conformance
    - id: RJ7
      title: >
        The existing gate stays green across every item (selftest, contracts,
        drift, docs, template sync), and a repository without a contract is
        byte-identically unaffected by the new checks.
      activation: {when: start}
      suite: scripts/verify.sh

release:
  milestone: >
    VELDO architecture and maintainability v1 - the intended shape is a
    human-approved contract the gate enforces, every spec declares its placement
    before build, review grades shape-fit, foundational decisions are elaborated,
    adversarially reviewed, human-decided units whose assumptions are living
    tripwires checked in-session, and per-area cost-to-change generates
    restoration work through the normal loop.
  mode: continuous
  require_all_work_shipped: true
  require_full_regression: true
  rollback: >
    Remove or leave unapproved the architecture contract and every new check
    stands down (the adoption-safe posture); git revert the plugin version bump;
    decision records and metric series are inert data and keep their history.
  observation:
    duration: >
      Run this repository under its own approved architecture contract for a
      working period: every change placed, shape-checked, and shape-reviewed, the
      tripwire pass in every gate run, and at least one entropy report derived
      from real recorded data, before the capability is recommended to adopting
      repositories.

open_decisions: []

resolved_decisions:
  - id: D1
    text: >
      The artifact's name and home.
    resolution: >
      Architecture contract, at .veldo/architecture.yaml, schema veldo.arch/v1
      (the recommendation). Decided by the founder 2026-07-22 via "use
      recommendations". WARP-1101 is unblocked the moment the plan leaves
      draft.
    resolved_at: 2026-07-22
  - id: D2
    text: >
      Restoration thresholds: what crossing generates a restoration spec.
    resolution: >
      Relative degradation of an area against its own trailing baseline, with
      generation starting advisory for a calibration period before its drafts
      are trusted (the recommended default). Decided by the founder 2026-07-22
      via "use recommendations".
    resolved_at: 2026-07-22
  - id: D3
    text: >
      Tripwire signal sourcing for assumptions not derivable from the
      repository or the event stream.
    resolution: >
      A small recorded-readings file updated in-session at the weekly pass
      (the stated default); W7 still supports the manual-review-with-expiry
      shape for assumptions a team prefers to declare that way. Decided by the
      founder 2026-07-22 via "use recommendations".
    resolved_at: 2026-07-22
  - id: D4
    text: >
      Shape-fit severity at the verdict.
    resolution: >
      A misfit finding blocks the merge like any blocking finding from day one
      (the recommendation: rework is cheap when construction is cheap). Decided
      by the founder 2026-07-22 via "use recommendations".
    resolved_at: 2026-07-22
  - id: D5
    text: >
      Reversal-cost mapping for foundational decisions.
    resolution: >
      Expressed through the existing risk tiers, with irreversible mapping to
      critical (two independent verdicts plus recorded human approval), as
      recommended. Decided by the founder 2026-07-22 via "use recommendations".
    resolved_at: 2026-07-22
  - id: D6
    text: >
      Duplication and complexity measurement tooling.
    resolution: >
      Stdlib-proportionate reference implementations with a pluggable
      per-language slot (the runner-suite posture), as recommended; external
      analyzers stay optional per-repo extensions, never required dependencies.
      Decided by the founder 2026-07-22 via "use recommendations".
    resolved_at: 2026-07-22
---

## Intent

VELDO's guarantees today are local to one change: the spec binds intent, the gate
proves the change, a fresh context reviews it, and a thousand locally proven
changes still cannot vouch for the foundation they sit on. Local green does not
compose into global good on its own. The failure has two classes, and they need
different organs. DECAY is rot that accumulates through many changes -
duplication, tangled dependencies, eroding boundaries - and is repairable
incrementally. WRONG FOUNDATIONS is the harder class: the wrong technology, the
wrong architecture style, the wrong tool, chosen silently inside a feature's
implementation, invisible at build time because it passes every test, and
unfixable by refactoring because the flaw is the foundation, not the code on top.
Agents are bad at both by construction: they optimize for making this spec work
with the least resistance, anchor to today's scale instead of the problem class,
pattern-match to the median of their training, and never have to live with the
choice.

This plan grows the missing organ from the method's own moves. For decay: the
intended shape becomes a versioned, human-approved architecture contract (the
same move that turned intent into the spec); everything mechanizable about it
compiles into gate checks that fail; specs declare their placement and footprint
before anything is built, the cheapest moment to prevent entropy; and the
independent review gains a shape-fit dimension where correct-but-does-not-fit is
a real rework verdict. For wrong foundations: a foundational choice becomes a
first-class unit of work - the machine elaborates the option space with each
option's dead-end conditions, an adversarial fresh-context review attacks the
proposal, a human decides against the stated problem class, scrutiny scales with
reversal cost, and the decision record is a living tripwire whose stated
assumptions are checked in-session so wrongness is caught by assumption breach
rather than outage. Entropy is then measured and reconciled: cost-to-change per
area, derived from the tokens, review cycles, and human minutes the loop already
records, generates restoration specs through the same loop that ships features,
and the post-restoration cost drop proves the refactor paid off.

Two postures bind everything here. First, nothing runs detached: every monitoring
pass is an ordinary in-session function invoked by the gate, by veldo status, or
by the weekly pass, never a daemon, timer, or background process. Second, this
plan is also a receipts plan: the method's companion writing describes this
design under "The Shape of the System" and is honest that it is design-stage;
releasing this plan is what turns that chapter from design into receipts. All
shipped material stays fully generic, in the engine, like everything else VELDO
ships.

## Data provenance - recorded today versus new instrumentation

Reused as-is, recorded by the loop today (no new instrumentation):

- Per-event tokens and cost_usd on the veldo.event/v1 envelope; the metrics
  derivation and the budget governor already read them.
- Review cycles and outcomes: review.requested, verdict.recorded, gate.passed,
  gate.failed events per spec.
- human_minutes per shipped change.
- Spec lifecycle events (spec.ready, spec.shipped, spec.blocked) and the lessons
  store.
- Git history: the files each shipped change touched.

New instrumentation this plan introduces:

- The architecture contract itself and its approval record (W1).
- Placement and footprint declarations binding each change to a contract area
  (W3): the join key the entropy map needs. History before W3 can be
  back-attributed only best-effort through git paths.
- Static shape measures: duplication, complexity, boundary pressure (W2).
- Decision records with assumption signals, and recorded readings for signals
  not derivable from the repository or the event stream (W5, W7, D3).

Consequence for ordering: W8's cost side is derivable the day it ships from
existing records; its per-area attribution starts accumulating when W3 ships.

## Ordered delivery rationale

W1 (the contract) and W5 (the decision record) are the two roots; they are
independent artifacts and start in parallel. From W1: W2 (gate enforcement) and
W3 (placement at elaboration) fan out in parallel, and W4 (the shape-fit review)
needs both the contract and the placement it grades against. From W5: W6 (the
adversarial decision review) and W7 (the tripwire pass) fan out in parallel. W8
(entropy metrics) needs W2 for the static measures and W3 for area attribution;
W9 (restoration generation) consumes W8's series. W10 releases once every lane
has shipped and the regression is green. The frontier after approval is W1 plus
W5; the widest point is four parallel items (W2, W3, W6, W7).

## Out of scope

Detached monitors of any kind (NG1); machine-made foundational decisions or
self-promoted drafts (NG2); external architecture platforms or required heavy
analyzers (NG3); redesigning the shipped loop machinery (NG4); vacuous
unmechanizable gate checks (NG5). The companion book chapter itself is not work
in this repository; this plan only makes its subject true. Live adoption of the
contract in other repositories is a per-repo act after release, not part of this
plan.

## Revisions

Revision 1 (2026-07-21): drafted at intake from the founder's go ("plan
architecture in veldo") and the method's invention notes ("The Shape of the
System"): the two failure classes (decay and wrong foundations), the five moves
for decay (contract, gate enforcement, shape-fit review, placement before build,
entropy measured and reconciled), and the five-part mechanism for wrong
foundations (decision as unit of work, problem-class framing, adversarial
decision review, living tripwires, scrutiny scaled to reversal cost). Status
draft: authored, not activated; no work starts until the plan leaves draft by a
recorded human approval, and D1 is answered at that same moment.

Revision 2 (2026-07-22): all six decisions resolved by the founder via "use
recommendations", each recorded with its resolution above: D1 architecture
contract at .veldo/architecture.yaml (schema veldo.arch/v1), D2 relative-baseline
thresholds with an advisory calibration period, D3 in-session recorded-readings
file at the weekly pass, D4 shape-fit blocking from day one, D5 reversal cost
through the existing risk tiers with irreversible as critical, D6 stdlib
reference implementations with pluggable slots. No scope change; recording
decisions is not approval: status stays draft, and leaving draft still requires
a separate recorded human approval.

Approved (2026-07-22): the founder approved the plan to leave draft on the go to
start the build ("start the 5 plans build"); status set to ready, approved_by
dmitry, approved_at 2026-07-22. Per the repo's approve pattern the approval
flips status and records the approver without bumping the revision. All six
decisions were already resolved at revision 2, so the ready frontier (WARP-1101
and WARP-1105) is now live for pulling into specs.

Released (2026-07-22): all ten work items shipped (W1 through W9 building the
organ, W10 the release), the full regression is green, and the release milestone
above is delivered - the intended shape is a human-approved contract the gate
enforces, every spec declares its placement before build, review grades shape-fit,
foundational decisions are elaborated, adversarially reviewed, human-decided units
whose assumptions are living tripwires checked in-session, and per-area
cost-to-change generates restoration work through the normal loop. WARP-1110 (W10)
lands the version bump to plugin 3.7.0, makes the docs true (README, the Plugin
Guide section 13, the Setup companion section 7.8, and the Runbook weekly pass),
and flips this status to released in the reviewed impl commit per the canonical
release shape. Per the repo's release pattern the flip records the milestone
without bumping the revision. The observation window above now begins: this
repository runs under its own approved architecture contract before the capability
is recommended to adopting repositories.
