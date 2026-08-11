---
schema: veldo.plan/v1
id: PLAN-0004
title: VELDO 2.0 - the executable system (executor, observability, adoption)
kind: mvp
status: released
revision: 4
owner: dmitry
approved_by: dmitry
approved_at: 2026-07-16
risk: standard

outcomes:
  - id: O1
    becomes_true: A ready spec is driven through the whole loop by an executor -
      build, gate, independent review, proof, evidence commit - with the human
      only approving and steering, not hand-driving every step.
    measure: /veldo:run executes the loop end to end on a ready spec and records
      human_minutes for the run
  - id: O3
    becomes_true: The events VELDO already emits become operations - dashboards
      (cycle time, human_minutes, gate pass rate, verdicts, regression health),
      cost budgets per plan, ephemeral environments for the runners, and
      release/rollback automation.
    measure: a metrics dashboard over .veldo/events.jsonl, enforced spend budgets,
      an env-provisioning step, and a rollback drill
  - id: O4
    becomes_true: Any repo adopts VELDO in one command, and what was learned in one
      iteration carries into the next.
    measure: a veldo init scaffold and a lessons store whose entries reach review

non_goals:
  - id: NG1
    text: Building product features - VELDO 2.0 is platform infrastructure; product
      iterations run THROUGH it (that is PLAN-0002's kind of work).
  - id: NG2
    text: A bespoke hosting stack before measured need - server-side pieces prefer
      the host's native primitives (branch protection, CI) until volume justifies
      more.

constraints:
  - id: C1
    text: Every 2.0 addition stays proportionate and is itself built through VELDO
      (dogfooded), with the same gate, proof, and independent review.
  - id: C2
    text: Infrastructure that needs a founder design call (identity, hosting) is a
      recorded decision, never guessed.

feature_tree:
  - id: F1
    title: The Executor - a runtime that drives the loop from a ready spec to an
      evidence commit with human approve/steer
    outcome_refs: [O1]
  - id: F3
    title: Observability and Ops - dashboards, cost budgets, ephemeral
      environments, release/rollback automation
    outcome_refs: [O3]
  - id: F4
    title: Adoption - one-command veldo init scaffold and a cross-iteration lessons
      store
    outcome_refs: [O4]

work:
  - item: X1
    spec: WARP-0401
    title: Executor v1 - drive a ready spec through build, gate, review, proof,
      and evidence with human approve/steer and recorded human_minutes
    feature_refs: [F1]
    depends_on: []
    order: 10
  - item: X2
    spec: WARP-0402
    title: veldo init scaffold - one command stands up .veldo, the gate, capabilities
      and a starter plan in a fresh repo
    feature_refs: [F4]
    depends_on: []
    order: 20
  - item: X3
    spec: WARP-0403
    title: Lessons store - capture failure modes and regressions and surface the
      relevant ones into the review prompt
    feature_refs: [F4]
    depends_on: []
    order: 30
  - item: X4
    spec: WARP-0404
    title: Metrics dashboard - render the event-envelope metrics (cycle time,
      human_minutes, gate pass rate, verdicts, regression health) from events.jsonl
    feature_refs: [F3]
    depends_on: []
    order: 40
  - item: X5
    spec: WARP-0405
    title: Cost and token budget governance - track and enforce spend per plan and
      per spec against the event stream
    feature_refs: [F3]
    depends_on: [WARP-0404]
    order: 50
  - item: X6
    spec: WARP-0406
    title: Ephemeral environment and fixture provisioning - spin a clean env with
      seeded data for the runners to drive
    feature_refs: [F3]
    depends_on: []
    order: 60
  - item: X7
    spec: WARP-0407
    title: Release and rollback automation - staged/canary rollout, feature-flag
      hooks, and an executable rollback, shipped as reference wiring
    feature_refs: [F3]
    depends_on: []
    order: 70

regression:
  journeys:
    - id: XJ1
      title: The executor drives a sample spec through the full loop and records
        human_minutes; a broken step halts the loop, not ships it
      activation: {when: after:WARP-0401}
      owner_spec: WARP-0401
      profiles: [per_spec, release]
      suite: executor selftest plus proof
    - id: XJ2
      title: veldo init produces a repo whose gate runs green on an empty starter
        plan
      activation: {when: after:WARP-0402}
      owner_spec: WARP-0402
      profiles: [release]
      suite: init scaffold selftest
    - id: XJ3
      title: The metrics dashboard reports the same numbers the metrics reader
        derives from events.jsonl (no drift)
      activation: {when: after:WARP-0404}
      owner_spec: WARP-0404
      profiles: [release]
      suite: dashboard-vs-reader selftest

release:
  milestone: VELDO 2.0 - the executable system (executor, observability, adoption)
  version: plugin 3.0.0
  mode: continuous
  require_all_work_shipped: true
  require_full_regression: true
  rollback: each subsystem is additive and independently revertable
  observation:
    duration: 2.0 is complete when the executor, observability, and adoption
      tracks ship (the server-side control-plane track was descoped in revision 4)

open_decisions: []

budgets:
  tokens: 20000000
  cost_usd: 400.0
  per_spec:
    - spec: WARP-0405
      tokens: 4000000
      cost_usd: 80.0
---

## Intent

VELDO 1.0 is a method, contracts, and verification runners. VELDO 2.0 makes it an
executable system: an executor that drives the loop so humans approve and steer
rather than hand-drive, the observability and ops that turn the events VELDO emits
into operations, and one-command adoption with a memory that carries learnings
forward. Every piece is built through VELDO itself. (A server-side control plane
with real-identity enforcement was considered and descoped in revision 4 as
over-architecture for this problem class; see the Revisions section.)

## Context

The events (W8), the metrics reader (W8), the CI template and branch-protection
guidance (W10), the digest-bound verdicts and path-scoped approvals (W9), and
/veldo:run (W3) are the seeds each 2.0 track grows from. Two tracks - the
identity gateway and the hosted control plane - need a founder design call and
are recorded as decisions D1 and D2 rather than guessed.

## Out of scope

Product features (those run through the layer, not in it) and a bespoke hosting
stack ahead of measured need.

## Revisions

Revision 2 (2026-07-16): decision D1 resolved - the founder chose SSH-signed
approvals (the approver signs the approval with their existing SSH/git key,
verified in policy_check), the proportionate real-attestation option with no new
service. X8 (WARP-0408) is unblocked. D2 (control-plane hosting) remains open.

Revision 3 (2026-07-16): decision D2 resolved - the founder chose GitHub-native
control plane (branch protection + required-check gate using the W10 CI template,
plus GitHub's merge queue once the org plan tier is confirmed), the proportionate
option with negligible cost and no bespoke hosting stack. open_decisions is now
empty; X9 (WARP-0409) is unblocked behind its X8 dependency. The whole platform
build (PLAN-0003 + PLAN-0004) is open.

Revision 4 (2026-07-17): the founder descoped the entire server-side control-plane
and identity track (F2) as over-architecture for a fast small-team SDLC - "X8 is
overkill, I do not want to go that far." X8 (WARP-0408 SSH-signed identity gateway)
and X9 (WARP-0409 GitHub-native control plane) are removed from the work DAG, along
with feature F2 and outcome O2, before either was built. This is a proportionality
call consistent with the balance rule and the financial-transactions test:
cryptographic human attestation of every protected merge is heavier than this
problem class needs. The current approval model stands - approvals are
agent-recorded with human provenance under standing authorization, honestly labeled
in .veldo/capabilities.yaml (not identity-attested). VELDO 2.0 is therefore the
executable system across the executor (F1), observability and ops (F3), and
adoption (F4) tracks: X1-X7 shipped, 7 of the original 9 items. The release version
is plugin 3.0.0; the method document is unchanged because the generic methodology
did not change (VELDO 2.0 makes the same loop executable, it is tooling, not method).
If server-side enforcement is ever wanted, reopen this plan with a fresh decision.
