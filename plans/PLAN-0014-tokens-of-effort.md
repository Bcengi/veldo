---
schema: veldo.plan/v1
id: PLAN-0014
title: Tokens of Effort - estimation measured in the machine's own unit, committed as ranges, reconciled against ground truth every change, paired with human-judgment load, rolled up to budgets and dollars, advisory first
kind: mvp
status: ready
revision: 2
owner: dmitry
approved_by: dmitry
approved_at: 2026-07-22
risk: standard

outcomes:
  - id: O1
    becomes_true: >
      Measurement is formal, and the dataset builds itself. Every shipped change
      has a per-spec actuals record harvested from what the loop already records
      - tokens and cost per event, gate and review cycles, human minutes -
      stored alongside the spec's features (acceptance-criteria count, risk
      tier, protected-path touch, files touched, model identity). This is the
      TOE ground-truth corpus, and it accumulates with zero extra effort per
      change.
    measure: >
      The corpus derivation over the existing event stream produces valid
      per-spec actuals records, back-harvesting history best effort; a
      malformed record is rejected at contract time; a freshly shipped fixture
      spec appears in the corpus with tokens, cycles, minutes, and features
      populated.
  - id: O2
    becomes_true: >
      Estimation is calibration, not guessing, and it always speaks in ranges.
      A unit of work can carry a committed up-front estimate built from three
      layers, weakest to strongest: a structural proxy over mechanical spec
      features; a cheap in-session sizing pass that reads the spec and the code
      it will touch; and historical analogy against similar shipped specs in
      the corpus. False precision is impossible by schema: an estimate is a
      range, never a point.
    measure: >
      A ready fixture spec receives a committed estimate record carrying the
      range and each layer's contribution; the schema refuses a point estimate;
      the sizing pass's own token cost is recorded like any other work; with an
      empty corpus the analogy layer stands down honestly and the range widens.
  - id: O3
    becomes_true: >
      Reconciliation makes the numbers provably better instead of forever
      biased. At ship, the estimate, the actual, and the variance are stored
      with the spec's features; the estimator recalibrates from the
      accumulating feature-to-actual history; and the estimator's own accuracy
      - mean error and a calibration curve - is tracked over time, so trust in
      any given estimate is itself a measured, visibly converging number.
    measure: >
      On a seeded corpus, recalibration demonstrably reduces a planted
      systematic bias; the accuracy series and calibration curve render from
      the reconciliation records; every shipped estimated spec produces exactly
      one reconciliation record, idempotently.
  - id: O4
    becomes_true: >
      Effort is a pair with a stable unit. Human-judgment load, derived from
      the human minutes the loop already records, stands beside TOE as a
      first-class second axis, making cheap-to-build but expensive-to-approve
      work visible for the first time; and TOE can display as a normalized
      point pegged to a reference change (per D1 and D2), so planning numbers
      survive model and price shifts while raw tokens remain the recorded
      ground truth underneath.
    measure: >
      Status and dashboard surfaces show the TOE and judgment-load pair per
      spec and per plan; the normalized display recomputes when the peg or
      price changes without altering any stored actual; raw tokens remain
      queryable under every normalized number.
  - id: O5
    becomes_true: >
      Budgets are real and advisory. A plan's TOE is the sum of its items'
      ranges, a program's is the sum of its plans, and the roll-up converts to
      a dollar range at current token price - the first estimate-to-dollars
      line that is measured rather than guessed. The existing pacing machinery
      consumes the budget to inform pacing. Nothing gates: estimates and
      budgets inform decisions and never block work until a separate explicit
      human decision says otherwise (D4).
    measure: >
      A fixture plan renders its rolled-up TOE range and dollar range; the
      pacer reads the budget without modification to its own machinery; a
      conformance test proves no code path in this plan refuses, blocks, or
      delays a unit of work on estimate or budget grounds.
  - id: O6
    becomes_true: >
      Cost-to-change has an area map. The per-area aggregation of reconciled
      actuals that PLAN-0011's entropy metrics consume is exposed from the
      corpus, joining placement declarations where that plan has shipped and
      standing down honestly to git-path attribution where it has not.
    measure: >
      The aggregation renders per-area cost-to-change from the corpus when
      placements exist, falls back to path-level attribution labeled as such
      when they do not, and never fabricates an attribution.

non_goals:
  - id: NG1
    text: >
      No enforcement. This is a hard boundary, not a phase: nothing in this
      plan gates, blocks, deprioritizes, or refuses work based on an estimate
      or a budget. If budget caps ever become enforcing, that is a separate
      explicit founder decision (D4) and a separate spec with its own review;
      this plan ships purely advisory machinery.
  - id: NG2
    text: >
      No LLM in the mechanical path. The corpus harvest, the structural proxy,
      reconciliation, recalibration, normalization, and roll-up are
      deterministic non-LLM code; the only LLM work is the optional layer-two
      sizing pass, which runs in-session and has its own consumption recorded.
  - id: NG3
    text: >
      No per-person measurement. TOE and judgment load size work and system
      health at the spec, plan, and area level; they are never surfaced as
      individual human performance numbers, and this plan builds no view that
      ranks people.
  - id: NG4
    text: >
      No rebuild of the recording machinery. The event envelope, the metrics
      derivation, the dashboard, the budget governance, and the pacing governor
      are reused as they ship today; this plan adds schemas and derivations on
      top, not replacements.
  - id: NG5
    text: >
      No daemons. Every derivation, estimate, reconciliation, and roll-up runs
      inside normal sessions, gate runs, status invocations, and the weekly
      pass; the established posture stands.
  - id: NG6
    text: >
      No false precision, ever. Point estimates do not exist in the schema;
      early ranges are wide and say so; an estimator that has not converged
      reports its own uncertainty rather than hiding it.

constraints:
  - id: C1
    text: >
      Every item is built through VELDO itself: spec, gate, proof, independent
      fresh-context review; every derivation ships with negative tests
      (anti-vacuity), including the advisory proof that nothing blocks on a
      number.
  - id: C2
    text: >
      Raw tokens are the ground truth. Normalization is a display and planning
      layer that never rewrites recorded actuals; every actual carries the
      model identity it was measured under (handling across model changes per
      D5); recomputing a peg or price re-renders views and touches no history.
  - id: C3
    text: >
      Estimates never alter the loop's behavior. An estimate record lives
      beside the spec, not inside it: it is not an acceptance criterion, it
      does not change risk, and its absence never invalidates a spec
      (commitment scope per D3).
  - id: C4
    text: >
      Proportionality: the mechanical layers are cheap math over recorded
      data; the sizing pass is optional, small, and its cost is visible; the
      whole estimation apparatus must cost a small fraction of the work it
      sizes.
  - id: C5
    text: >
      The canon is engine: every schema, derivation, and surface
      lands in the engine, syncs byte-identical to this repository's
      instances, and stays fully generic; all machinery is runnable
      in-session.
  - id: C6
    text: >
      Cross-plan joins are soft: the per-area aggregation uses PLAN-0011's
      placement declarations where present and stands down to labeled
      path-level attribution where absent; never a hard dependency edge across
      plans, and never a fabricated join.

feature_tree:
  - id: F1
    title: The corpus - measured ground truth that builds itself
    outcome_refs: [O1]
  - id: F2
    title: The estimator - three layers, committed as ranges
    outcome_refs: [O2]
  - id: F3
    title: Reconciliation - the learning loop and the estimator's own accuracy
    outcome_refs: [O3]
  - id: F4
    title: The pair and the stable unit - judgment load and normalization
    outcome_refs: [O4]
  - id: F5
    title: Budgets - roll-up, dollars, pacing, advisory by design
    outcome_refs: [O5]
  - id: F6
    title: The area map - cost-to-change exposed for the entropy organ
    outcome_refs: [O6]
  - id: F7
    title: Release - the engine ships it and the docs are true
    outcome_refs: [O1, O5]

work:
  - item: W1
    spec: WARP-1401
    title: >
      The TOE ground-truth corpus. Formalize the per-spec actuals record:
      harvest tokens and cost from the event envelope, gate and review cycles
      from the lifecycle events, and human minutes, into a validated per-spec
      record stored with the spec's mechanical features (acceptance-criteria
      count, risk tier, protected-path touch, files touched from git, review
      cycles, model identity). Deterministic, idempotent, back-harvesting
      existing history best effort. Only the schema and aggregation are new;
      every input is already recorded today.
    feature_refs: [F1]
    depends_on: []
    order: 10
  - item: W2
    spec: WARP-1402
    title: >
      The estimate record and the structural proxy. A validated estimate record
      committed beside a spec before build - always a range, never a point,
      with per-layer contributions - and the first layer: a deterministic
      structural proxy over the spec's mechanical features (acceptance-criteria
      count, risk tier, protected-path touch, regression surface, expected
      review cycles). Commitment scope per D3; absence of an estimate never
      invalidates a spec.
    feature_refs: [F2]
    depends_on: [WARP-1401]
    order: 20
  - item: W3
    spec: WARP-1403
    title: >
      The sizing pass. The optional second layer: a small in-session agent
      reads the spec and the code it will touch and predicts a range with
      stated reasoning, recorded alongside the structural proxy. Honest about
      itself: the pass's own token cost is recorded like any other work, and
      its noise is expected - it sharpens the range, it never becomes a point.
    feature_refs: [F2]
    depends_on: [WARP-1402]
    order: 30
  - item: W4
    spec: WARP-1404
    title: >
      Historical analogy. The strongest layer: match the new spec's features to
      similar shipped specs in the corpus and predict from their recorded
      actuals, tightening as history accumulates and standing down honestly
      (with a wider range) while the corpus is small. Analogy windows respect
      model identity per D5. The combined committed range is derived from the
      layers present.
    feature_refs: [F2]
    depends_on: [WARP-1401, WARP-1402]
    order: 35
  - item: W5
    spec: WARP-1405
    title: >
      Reconciliation and the estimator's own accuracy. At ship, store the
      estimate, the actual, and the variance with the spec's features, exactly
      once, idempotently; recalibrate the estimator from the accumulating
      feature-to-actual history, correcting systematic bias; and track the
      estimator itself - mean error and a calibration curve over time - so the
      trustworthiness of estimates is a measured, visible, converging number.
    feature_refs: [F3]
    depends_on: [WARP-1402]
    order: 40
  - item: W6
    spec: WARP-1406
    title: >
      Normalization - the stable planning unit. TOE displayable as a normalized
      point pegged to a reference change (peg per D1, display unit per D2), so
      planning numbers survive model and price shifts; raw tokens remain the
      recorded ground truth underneath, and re-pegging re-renders views without
      touching a single stored actual.
    feature_refs: [F4]
    depends_on: [WARP-1401]
    order: 45
  - item: W7
    spec: WARP-1407
    title: >
      The second axis - human-judgment load. Derive the judgment-load number
      from the human minutes the loop already records and surface the pair
      (TOE, judgment load) everywhere effort is shown: the estimate record, the
      corpus, status, and the dashboard. Cheap-to-build, expensive-to-approve
      work becomes visible, which no single-axis unit ever showed.
    feature_refs: [F4]
    depends_on: [WARP-1401]
    order: 50
  - item: W8
    spec: WARP-1408
    title: >
      Budgets - roll-up, dollars, and pacing, advisory by design. A plan's TOE
      range is the sum of its items, a program's the sum of its plans; the
      roll-up converts to a dollar range at current token price; and the
      existing budget governance and pacing governor consume the numbers to
      inform pacing, reused unchanged. Ships with the advisory proof: no path
      blocks work on a number (enforcement, if ever, is D4 and a separate
      spec).
    feature_refs: [F5]
    depends_on: [WARP-1402]
    order: 55
  - item: W9
    spec: WARP-1409
    title: >
      Cost-to-change per area. Expose the per-area aggregation of reconciled
      actuals that PLAN-0011's entropy metrics consume: join placement
      declarations where that plan has shipped, stand down to git-path
      attribution labeled as such where it has not, and never fabricate a
      join. This is the soft seam between effort measurement and the
      architecture organ, declared in prose, never as a dependency edge.
    feature_refs: [F6]
    depends_on: [WARP-1401]
    order: 60
  - item: W10
    spec: WARP-1410
    title: >
      Release. Land the schemas, derivations, estimator layers, reconciliation,
      normalization, pair surfaces, and roll-up in the canonical engine so
      /veldo:init lays them down and the packs carry them; make the docs true
      (the method and setup documents gain measured estimation as shipped
      behavior, fully generic, advisory posture stated plainly); record
      capabilities honestly; bump the plugin version; mark the plan released
      once the regression is green.
    feature_refs: [F7]
    depends_on: [WARP-1403, WARP-1404, WARP-1405, WARP-1406, WARP-1407, WARP-1408, WARP-1409]
    order: 80

regression:
  journeys:
    - id: RJ1
      title: >
        The corpus derivation over the real event stream and a seeded fixture
        produces valid per-spec actuals records idempotently; a malformed
        record is rejected at contract time.
      activation: {when: after:WARP-1401}
      suite: corpus conformance
    - id: RJ2
      title: >
        A ready fixture spec receives a committed range with per-layer
        contributions; the schema refuses a point estimate; the analogy layer
        stands down honestly on an empty corpus.
      activation: {when: after:WARP-1404}
      suite: estimator conformance
    - id: RJ3
      title: >
        On a seeded corpus with a planted bias, recalibration measurably
        reduces the bias; the estimator's accuracy series and calibration curve
        render; each shipped estimated spec reconciles exactly once.
      activation: {when: after:WARP-1405}
      suite: reconciliation conformance
    - id: RJ4
      title: >
        A fixture plan renders its TOE and dollar ranges and the pair per item;
        the pacer consumes the budget unchanged; the advisory proof holds - no
        code path blocks, refuses, or delays work on estimate or budget
        grounds.
      activation: {when: after:WARP-1408}
      suite: budget roll-up and advisory conformance
    - id: RJ5
      title: >
        The per-area aggregation renders with placements, falls back to labeled
        path attribution without them, and fabricates nothing.
      activation: {when: after:WARP-1409}
      suite: area-map conformance
    - id: RJ6
      title: >
        The existing gate stays green across every item, and a repository that
        commits no estimates behaves exactly as before; nothing installs a
        daemon, timer, or detached process.
      activation: {when: start}
      suite: scripts/verify.sh

release:
  milestone: >
    VELDO Tokens of Effort v1 - the actuals corpus builds itself from recorded
    events, estimates are committed as calibrated ranges from three layers,
    reconciliation stores estimate-actual-variance every ship and recalibrates,
    the estimator's own accuracy is tracked and visibly converges, effort is a
    pair (TOE and human-judgment load) with a normalized stable display unit
    over raw-token ground truth, plans roll up to token and dollar ranges that
    inform pacing - all advisory, gating nothing, proven offline.
  mode: continuous
  require_all_work_shipped: true
  require_full_regression: true
  rollback: >
    Stop committing estimates and every surface stands down to plain actuals
    reporting (the corpus keeps accumulating harmlessly); git revert the plugin
    version bump; corpus, estimate, and reconciliation records are inert data
    and keep their history.
  observation:
    duration: >
      Run this repository with estimates committed on its own specs for a
      working period: corpus accumulating, reconciliation records landing at
      each ship, the accuracy curve rendering with real data, and at least one
      plan roll-up with dollar conversion reviewed by the founder, before the
      capability is recommended to adopting repositories.

open_decisions: []

resolved_decisions:
  - id: D1
    text: >
      The normalization peg: which reference change defines the normalized
      point.
    resolution: >
      The median standard-risk shipped spec, as the provisional peg (a corpus
      statistic, not a hand-picked spec), which the founder may later confirm
      or replace. Decided by the founder 2026-07-22 via "use recommendations"
      (start the build). WARP-1406 is unblocked the moment the plan leaves
      draft.
    resolved_by: founder via 'use recommendations' (start the build), 2026-07-22
    resolved_at: 2026-07-22
  - id: D2
    text: >
      The display unit: raw tokens, normalized points, or both.
    resolution: >
      Both, with the normalized point primary on planning surfaces and raw
      tokens always one step away. Decided by the founder 2026-07-22 via "use
      recommendations" (start the build).
    resolved_by: founder via 'use recommendations' (start the build), 2026-07-22
    resolved_at: 2026-07-22
  - id: D3
    text: >
      When estimates start being committed.
    resolution: >
      Opt-in per plan first, until the calibration curve proves itself, then
      default on later by a separate decision. Decided by the founder
      2026-07-22 via "use recommendations" (start the build).
    resolved_by: founder via 'use recommendations' (start the build), 2026-07-22
    resolved_at: 2026-07-22
  - id: D4
    text: >
      Whether budget caps ever become enforcing.
    resolution: >
      The plan ships advisory only, with no enforcing caps (NG1); flipping any
      cap to enforcing is a separate founder decision and a separate spec with
      its own review. Decided by the founder 2026-07-22 via "use
      recommendations" (start the build).
    resolved_by: founder via 'use recommendations' (start the build), 2026-07-22
    resolved_at: 2026-07-22
  - id: D5
    text: >
      Model-change handling in the corpus.
    resolution: >
      Annotate every actual with its model identity and window analogy matching
      to same-model history; normalization stays a display concern, not a
      cross-model rewrite of actuals. Decided by the founder 2026-07-22 via
      "use recommendations" (start the build).
    resolved_by: founder via 'use recommendations' (start the build), 2026-07-22
    resolved_at: 2026-07-22
---

## Intent

Every legacy estimate - story points, ideal days, t-shirt sizes - measures
human authoring effort. When an agent writes the code, human authoring time
nearly decouples from the work, and those units stop meaning anything; yet
teams still need to size, budget, and sequence work. The honest unit for the
AI age is the machine's own consumption: Tokens of Effort, the expected model
tokens to carry a unit of work from specification to a merged, proven change,
across implementation, the gate, the proof, the independent review, and every
fix-and-recheck cycle. It holds up where points never did: it is measured, not
guessed (the loop already records what every shipped change actually cost); it
converts to money; it captures the real cost drivers automatically, because a
change that needs three review cycles burns visibly more than a one-shot; and
it sums, so plans get budgets and budgets get paced.

This plan builds the whole loop of it, in the order the idea demands.
Measurement first, because it is already real: the corpus of per-spec actuals
is harvested from events the loop emits today, so the dataset builds itself
(W1 is schema and aggregation, not new telemetry). Estimation second, as a
calibration problem with three layers weakest to strongest - structural proxy,
a cheap sizing pass, historical analogy - always producing a range, never a
point. Reconciliation third, the piece that makes it a learning system instead
of a forever-biased guess: estimate committed before build, actual recorded
during, variance stored at ship beside the spec's features, the estimator
recalibrated from the accumulating history, and the estimator's own accuracy -
mean error, calibration curve - tracked so trust itself is measured and
convergence is visible. Legacy points never reconciled against a real unit, so
they never improved; TOE reconciles against ground truth every single change.
Around the core: human-judgment load from recorded human minutes as the second
axis of the pair, making cheap-to-build but expensive-to-approve work visible;
a normalized display point pegged to a reference change so planning numbers
survive model and price shifts while raw tokens stay the ground truth; and
budgets - plan and program roll-ups converting to dollar ranges at current
token price, consumed by the pacing machinery that already exists.

Two postures bind the plan. First, advisory is a hard boundary: estimates and
budgets inform, and nothing anywhere in this plan gates, blocks, or refuses
work on a number - if enforcement ever comes, it is a separate explicit
founder decision (D4) with its own spec. Second, this is a receipts plan under
the publication gate: the method's companion writing describes this design
under "Tokens of Effort" and the book does not publish ahead of the machinery;
releasing this plan turns that chapter from design into receipts, with all
shipped material fully generic in the engine and nothing running detached.

## Data provenance - recorded today versus new instrumentation

Reused as-is, recorded by the loop today (no new telemetry):

- Tokens and cost_usd per event on the veldo.event/v1 envelope; the metrics
  derivation, dashboard, budget governance, and pacing governor that already
  read them.
- Gate and review cycles per spec (gate.passed, gate.failed,
  review.requested, verdict.recorded) and the spec lifecycle events.
- human_minutes per shipped change.
- Spec front matter features (acceptance criteria, risk tier, protected-path
  touch) and git history (files touched).

New instrumentation this plan introduces (schema and derivation, not
telemetry):

- The corpus record and its harvest (W1) and the estimate record with its
  range-only schema (W2).
- The three estimator layers (W2, W3, W4) - the sizing pass is the only LLM
  component, optional and self-costed.
- Reconciliation records, recalibration, and the estimator-accuracy series
  (W5).
- The normalization peg and display layer (W6), the judgment-load pair
  surfaces (W7), the roll-up and dollar conversion (W8), and the per-area
  aggregation (W9).

Cross-plan seam (soft, per C6): W9's per-area aggregation is the feed
PLAN-0011's entropy metrics consume, joining placements where that plan has
shipped and standing down to labeled path attribution where it has not.

## Ordered delivery rationale

W1 (the corpus) is the single root: every other item reads it or writes beside
it. W2 (the estimate record and structural proxy) establishes the committed
range; W3 (sizing pass) and W4 (analogy) extend it and can proceed in parallel
once W2 exists. W5 (reconciliation) needs only committed estimates and the
corpus, so it parallels W3 and W4. W6 (normalization), W7 (the pair), and W9
(the area map) hang off the corpus directly and are deliberately parallel. W8
(budgets) needs the estimate record to roll up. W10 releases once every lane
has shipped and the regression is green. The frontier after approval is W1
alone; the widest point is six parallel items (W3, W4, W5, W6, W7, W9, W8
joining as W2 lands).

## Out of scope

Any enforcement, gating, or blocking on estimates or budgets (NG1, D4);
LLM involvement outside the optional sizing pass (NG2); per-person performance
measurement (NG3); rebuilding the event, metrics, dashboard, budget, or pacing
machinery (NG4); daemons or detached processes (NG5); point estimates in any
schema (NG6). The companion book chapter itself is not work in this
repository; this plan only makes its subject true.

## Revisions

Revision 1 (2026-07-21): drafted at intake from the founder's seed
("estimations we don't even touch in the method; veldo should estimate in
tokens of effort") and the method's invention notes ("Tokens of Effort"),
in the seed's own order: measurement is already real and needs only schema;
estimation is a three-layer calibration producing ranges; reconciliation is
the estimate-to-actual learning loop with the estimator's own accuracy
tracked; normalization gives a stable planning unit over raw-token ground
truth; human-judgment load makes effort a pair; budgets roll up to dollars
and inform the existing pacer; everything advisory first. D1 through D5 are
surfaced for the founder, not resolved. Status draft: authored, not
activated; no work starts until the plan leaves draft by a recorded human
approval.

Revision 2 (2026-07-22): the founder gave the go to start the build ("start the
5 plans build") and chose "use recommendations", resolving all five open
decisions to their recommended defaults, each now recorded in
resolved_decisions above: D1 the median standard-risk shipped spec as the
provisional normalization peg, D2 both raw tokens and normalized points, D3
opt-in per plan first, D4 advisory only with no enforcing caps, D5 annotate and
window the corpus by model identity. Resolving D1 unblocks WARP-1406.
open_decisions is now empty. No scope change; recording decisions is not
approval, so status stays draft and leaving draft still requires a separate
recorded human approval.

Approved (2026-07-22): the founder approved the plan to leave draft on the go to
start the build ("start the 5 plans build"); status set to ready, approved_by
dmitry, approved_at 2026-07-22. Per the repo's approve pattern the approval
flips status and records the approver without bumping the revision. The ready
frontier (WARP-1401) is now live for pulling into specs.
