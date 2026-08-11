---
schema: veldo.plan/v1
id: PLAN-0001
title: VELDO 1.0 - from spec stream to planned product development
kind: mvp
status: released
revision: 4
owner: dmitry
approved_by: dmitry
approved_at: 2026-07-16
risk: standard

outcomes:
  - id: O1
    becomes_true: A founder/PM defines a product iteration holistically (outcomes,
      feature tree, ordering, regression, release) in one dialogue, and specs are
      pulled from it in deliberate order - never as a random stream.
    measure: a real product iteration planned and delivered through the layer
  - id: O4
    becomes_true: The layer demonstrably PROJECT-MANAGES a many-screen,
      many-permutation feature - tracking the whole, refusing broken order,
      surfacing drift and blockers, computing revision impact - with less human
      coordination than before, evidenced in receipts. Until this is true, the
      training documents' conditional on the project-manager role stands.
    measure: the W12 dogfood receipt plus the human-minutes trace
  - id: O2
    becomes_true: The implementation enforces what the documents promise - the
      capability manifest's absent list for core-loop items reaches zero.
    measure: .veldo/capabilities.yaml
  - id: O3
    becomes_true: UI and mobile changes are proven by driven flows, states, and
      delivered visual evidence, with reference runners shipped, not just named.
    measure: one real UI change and one real mobile change proven end to end

non_goals:
  - id: NG1
    text: Control-plane services (bus, registries, orchestrators) - the build
      order still gates them on measured volume.
  - id: NG2
    text: Server-side merge queue - branch-protection guidance ships; the queue
      remains deferred.

constraints:
  - id: C1
    text: Proportionality rule holds - every addition must be lighter than the
      work it governs; a plan takes tens of human minutes to define.
  - id: C2
    text: Two lanes preserved - bugs and isolated work keep the direct spec path.
  - id: C3
    text: All docs stay generic; the capability manifest stays the single truth
      of implementation status.

feature_tree:
  - id: F1
    title: The planning layer (Product Plan contract, /veldo:plan, DAG ordering,
      plan context bundle, plan index and receipts)
    outcome_refs: [O1]
  - id: F2
    title: Planned regression (iteration journeys with activation and owners,
      per-spec vs release profiles, device matrix at plan level)
    outcome_refs: [O1, O3]
  - id: F3
    title: Web execution reference (journey runner + state capture + a11y via
      Playwright, token lint, baseline comparator with tolerances)
    outcome_refs: [O3]
  - id: F4
    title: Mobile execution reference (Android emulator driving - install,
      journeys, lifecycle re-drives, state capture, video, matrix; iOS deferred
      and stated)
    outcome_refs: [O3]
  - id: F5
    title: Event envelope v1 + metrics derivation (ids, correlation, the 15 core
      types from the loop's actual steps, human_minutes, a metrics reader)
    outcome_refs: [O2]
  - id: F6
    title: Core-loop mechanical closure remainder (ready-spec enforcement at the
      boundary, spec-revision invalidation, verdict-proof binding, approval
      self-separation, server-side wiring guidance)
    outcome_refs: [O2]
  - id: F7
    title: Docs and training integration (method Stage 0 planning, setup plan
      contract, PM training module, runbook planning chapter)
    outcome_refs: [O1]

work:
  - item: W1
    spec: WARP-0101
    title: Product Plan contract + validator (refs valid, DAG acyclic, mirroring,
      no open decisions at ready) + flat plans/ + plan index generation
    feature_refs: [F1]
    depends_on: []
    order: 10
  - item: W2
    spec: WARP-0102
    title: /veldo:plan skill (create, refine, approve, pull, revise w/ impact
      analysis, status, release) + /veldo:spec lane fields + promotion rule
    feature_refs: [F1]
    depends_on: [WARP-0101]
    order: 20
  - item: W3
    spec: WARP-0103
    title: /veldo:run plan integration - context bundle, stale-revision and
      unshipped-dependency refusal, plan hash in proof
    feature_refs: [F1]
    depends_on: [WARP-0102]
    order: 30
  - item: W4
    spec: WARP-0104
    title: Regression plan mechanics - journey activation states, owner specs,
      per-spec vs release profiles wired into the gate slots
    feature_refs: [F2]
    depends_on: [WARP-0101]
    order: 40
  - item: W5
    spec: WARP-0105
    title: Web journey/state/a11y reference runner + fixtures (incl. one
      deliberately failing)
    feature_refs: [F3]
    depends_on: []
    order: 50
  - item: W6
    spec: WARP-0106
    title: Token lint + baseline comparator references with tolerance config
    feature_refs: [F3]
    depends_on: []
    order: 60
  - item: W7
    spec: WARP-0107
    title: Android emulator reference runner (profile boot, install, journey
      driving, lifecycle re-drives, captures, video, matrix completeness)
    feature_refs: [F4]
    depends_on: [WARP-0105]
    order: 70
  - item: W8
    spec: WARP-0108
    title: Event envelope v1 emitted from the loop's real steps + human_minutes
      + metrics reader in /veldo:status
    feature_refs: [F5]
    depends_on: []
    order: 80
  - item: W9
    spec: WARP-0109
    title: Core-loop closure - ready-spec at the boundary, spec-revision
      invalidation, verdict-proof digest binding, approval self-separation,
      path-scoped approval authorization (an approval covers only the
      protected paths it names, not every protected path in the push range)
    feature_refs: [F6]
    depends_on: [WARP-0108]
    order: 90
  - item: W10
    spec: WARP-0110
    title: Server-side wiring guidance + CI check template (same gate in CI,
      branch protection recipe) as shipped artifacts
    feature_refs: [F6]
    depends_on: [WARP-0109]
    order: 100
  - item: W11
    spec: WARP-0111
    title: Method v2.0 Stage 0 + setup plan sections + PM training module +
      runbook planning chapter, all consistent with what actually shipped
    feature_refs: [F7]
    depends_on: [WARP-0103, WARP-0104]
    order: 110
  - item: W12
    spec: WARP-0112
    title: Dogfood release - a real product iteration (mobile or companion)
      planned and delivered through the layer; the 1.0 receipt
    feature_refs: [F1, F2, F3, F4]
    depends_on: [WARP-0103, WARP-0104, WARP-0105, WARP-0106, WARP-0107]
    order: 120

regression:
  journeys:
    - id: RJ1
      title: Plugin negative-test fixtures stay red where they must (fail-closed
        gate, unknown kinds, criteria coverage, policy blocks)
      activation: {when: start}
      owner_spec: WARP-0101
      profiles: [per_spec, release]
      suite: scripts/selftest.py (plugin fixtures + negative tests)
    - id: RJ2
      title: The tripdesk pilot stays conformant (gate green, verdicts bound,
        policy check passing) whenever 1.0 changes actually reach it
      activation: {when: manual}
      profiles: [release]
      suite: tripdesk scripts/verify.sh + .veldo/policy_check.py
      note: Manual trigger - template changes reach the pilot only via an
        explicit plugin upgrade in its own repository, so this runs when a
        plugin version rolls out to the pilot and again at the 1.0 release,
        not after veldo commits that ship nothing to it (rev 2). Modelled as
        activation manual in rev 3 (W4) so the mechanics agree with the note.

release:
  milestone: VELDO 1.0
  version: plugin 3.0.0, method 2.0
  mode: continuous
  require_all_work_shipped: true
  require_full_regression: true
  rollback: plugin versions are additive; a repo pins the prior plugin version
  observation:
    duration: one real iteration delivered through the layer (W12 is the
      observation, not a timer)

open_decisions: []
---

## Intent

VELDO today runs a stream of individual specifications: correct for bugs and
isolated changes, wrong for product development, which is holistic first
(outcomes, features, ordering, regression, release) and decomposed second.
The founder named it: today is 0.1-alpha. This plan is VELDO 1.0: the product
planning layer designed and built, the conformance gaps that make documents
overclaim closed mechanically, and the UI/mobile execution that product
iterations actually need shipped as reference implementations - proven by
delivering one real product iteration through the whole thing.

## Revisions

Revision 2 (2026-07-16): RJ2 activation narrowed from every change to
pilot-rollout-and-release; no scope, work, or outcome changes. Approved
basis: founder's direct question about RJ2's coupling, same day.

Revision 3 (2026-07-16, W4): regression journeys upgraded to the mechanics
contract - RJ1 gains owner_spec and profiles; RJ2's activation modelled as
manual with profiles [release] so the computed activation matches its note.
No scope, work, or outcome changes.

Revision 4 (2026-07-16, W12): decision D1 resolved. The founder chose the
companion control-tower home (backend) as the dogfood iteration, captured as
PLAN-0002 and delivered through the layer with live journeys driven against the
running backend. open_decisions is now empty, so W12 is unblocked. No scope,
work, or outcome changes to W1-W11.

## Ordered delivery rationale

The planning layer (W1-W3) and the execution references (W5-W7) are parallel
tracks; regression mechanics (W4) join them; events (W8) underpin closure
(W9-W10); docs land only after the mechanics they describe exist (W11); and
the release IS the dogfood iteration (W12) - VELDO 1.0 is done when a real
product increment has been planned, ordered, regressed, and released through
it, not when the code merges.

## Provenance

Reconciled two-model design: docs/design/05-product-planning-layer-sol.md
(Sol) merged with in-session design; deltas taken: flat plans/ directory,
validator-style enforcement rather than JSON Schema files, template kept
light per the proportionality rule.
