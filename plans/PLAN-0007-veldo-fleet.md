---
schema: veldo.plan/v1
id: PLAN-0007
title: VELDO Fleet - elastic capability-aware parallel workers with token-paced autoscaling
kind: mvp
status: released
revision: 2
owner: dmitry
approved_by: dmitry
approved_at: 2026-07-18
risk: standard

outcomes:
  - id: O1
    becomes_true: Running many VELDO builds in parallel is one command per session -
      workers join on demand, atomically claim different ready work from the global
      frontier, and land it, with no human hand-managing worktrees, spec assignment,
      or merges. Two accounts is two vanilla sessions that self-divide the work.
    measure: two or more veldo work sessions claim distinct specs from one frontier,
      never the same one, and their results serialize onto the trunk automatically
  - id: O2
    becomes_true: An idle worker is rare - a build-blocked worker picks up other
      ready work or a pending review rather than sitting, and only waits when the
      whole system is drained.
    measure: with a dependency-narrow plan, a worker with no claimable build pulls a
      pending review or a standalone spec instead of idling
  - id: O3
    becomes_true: Work routes to the machine that can run it - a spec only lands on a
      worker whose capabilities cover its requirements, so iOS work goes to a Mac, GPU
      work to a GPU box, and shareable work spreads across whoever is free, with no
      manual machine-to-job map.
    measure: a spec requiring a capability is claimed only by a worker advertising it,
      and a capability-required spec waits when no capable worker is free
  - id: O4
    becomes_true: Workers provision the environment a build needs, isolated per run,
      while a heavy shared read-only dependency is attached once rather than duplicated
      per worker - so parallel builds are safe without standing up N copies of a large
      dataset.
    measure: two workers build against the same large read-only dataset by attaching to
      one shared instance, and a mutating build gets an isolated write layer, not a copy
  - id: O5
    becomes_true: The worker pool paces its token consumption to use the session and
      weekly budgets fully without exhausting either early, scaling up when under pace
      and throttling when ahead.
    measure: given a configured budget and window, the governor scales the active
      worker count so measured burn tracks the target rate for the tighter window

non_goals:
  - id: NG1
    text: Spawning detached or headless Claude Code processes. Workers are vanilla
      sessions a human (or an in-session launcher) starts; the coordinator never runs
      a rogue background claude. Multi-account means one human-started session per
      account, which then self-divides via the claim ledger.
  - id: NG2
    text: A hosted scheduler, a queue service, a database, or a message bus. The
      fleet coordinates through git plus the shared run registry plus a claim ledger.
  - id: NG3
    text: Querying a live remaining-token allowance. Claude Code exposes no such API;
      the governor MEASURES consumption (OpenTelemetry, per-run usage, the event
      stream) and paces against a configured budget and reset schedule, self-correcting.
  - id: NG4
    text: Duplicating a large read-only dataset per worker. Isolation means isolating
      the mutable state; heavy shared data is attached read-only or cloned copy-on-write,
      never copied wholesale per build.

constraints:
  - id: C1
    text: Every item stays proportionate and is built through VELDO itself, with the
      same gate, proof, and independent review.
  - id: C2
    text: A worker is VANILLA - a plain Claude Code session with only the VELDO plugin,
      run in the target repo or a worktree, carrying none of any assistant's own
      context. Workers are account-agnostic and reproducible.
  - id: C3
    text: Coordination state (claims, run progress) lives under the git common dir,
      shared across worktrees, outside git history; durable results land on the trunk.
      Nothing spins - a fully drained worker waits for a landing or stops cleanly.
  - id: C4
    text: Capabilities are free-form tags a worker advertises and a spec declares as
      requirements; the claim matches by requirements being a subset of capabilities,
      never a hardcoded OS or machine map, so new hardware or tools are a new tag with
      no code change.
  - id: C5
    text: A worker provisions its build environment from a definition IN the repo that
      distinguishes shared read-only dependencies (attached once, idempotent) from
      per-run mutable state (ephemeral, isolated, torn down); heavy datasets are shared
      or copy-on-write cloned, never duplicated.

feature_tree:
  - id: F1
    title: Claim and frontier - atomic capability-matched claim/release of work and the
      global claimable set across plans, bugs, and pending reviews, scoped and gated
    outcome_refs: [O1, O2, O3]
  - id: F2
    title: The worker and the lander - the veldo work loop and the serialized automatic
      merge that make the pool run hands-free
    outcome_refs: [O1, O2]
  - id: F3
    title: Environment - workers provision an isolated per-run env from a repo
      definition, attaching heavy shared read-only deps once instead of duplicating them
    outcome_refs: [O4]
  - id: F4
    title: Pacing and launch - the token governor that autoscales the pool and the
      launcher plus multi-account and grouping procedure
    outcome_refs: [O5, O1]

work:
  - item: Y1
    spec: WARP-0701
    title: Claim ledger with capability matching - atomic claim, release, and
      heartbeat-expiry of a unit of work, granted only when the worker's capabilities
      cover the unit's requirements
    feature_refs: [F1]
    depends_on: []
    order: 10
  - item: Y2
    spec: WARP-0702
    title: Global claimable frontier - the claimable set across all active plans plus
      standalone and bug specs plus pending reviews, minus shipped, blocked, claimed,
      capability-mismatched, or out of the worker's scope
    feature_refs: [F1]
    depends_on: [WARP-0701]
    order: 20
  - item: Y3
    spec: WARP-0703
    title: veldo work loop - a worker advertises its capabilities and an optional scope,
      claims the next claimable unit, dispatches it (build via the executor, or a
      review), releases and hands off to the lander, repeats, waits when drained
    feature_refs: [F2]
    depends_on: [WARP-0701, WARP-0702]
    order: 30
  - item: Y4
    spec: WARP-0704
    title: Serialized lander - land a completed build to the trunk under concurrency
      with a land lock (cherry-pick, resolve, gate, proof, evidence) so workers never collide
    feature_refs: [F2]
    depends_on: [WARP-0703]
    order: 40
  - item: Y5
    spec: WARP-0705
    title: Environment provisioning - a repo env definition and a provisioner that
      attaches shared read-only deps once and gives a mutating build an isolated write
      layer (schema, copy-on-write clone, or fixture), never a wholesale copy
    feature_refs: [F3]
    depends_on: [WARP-0703]
    order: 50
  - item: Y6
    spec: WARP-0706
    title: Token pacing governor - measure burn (OTel, per-run usage, the event stream)
      against a configured session and weekly budget and scale the active worker count
    feature_refs: [F4]
    depends_on: [WARP-0703]
    order: 60
  - item: Y7
    spec: WARP-0707
    title: Fleet launcher, grouping, and multi-account procedure - veldo fleet N launches
      N vanilla in-session workers governed by the pacer with an optional scope; the
      documented per-account veldo work path and CLAUDE_CONFIG_DIR recipe
    feature_refs: [F4]
    depends_on: [WARP-0703, WARP-0704, WARP-0705, WARP-0706]
    order: 70

regression:
  journeys:
    - id: YJ1
      title: Two workers race for the same frontier and claim distinct specs; a dead
        worker's claim expires and is reclaimed; a worker is granted a claim only when
        its capabilities cover the unit's requirements
      activation: {when: after:WARP-0701}
      owner_spec: WARP-0701
      profiles: [per_spec, release]
      suite: claim ledger selftest
    - id: YJ2
      title: A build-blocked worker pulls a pending review or a standalone spec rather
        than idling; a fully drained worker waits or stops without spinning; scope and
        capability filters narrow the claimable set correctly
      activation: {when: after:WARP-0703}
      owner_spec: WARP-0703
      profiles: [release]
      suite: worker loop selftest
    - id: YJ3
      title: A shared read-only dependency is attached once for multiple workers while a
        mutating build gets an isolated write layer, and the env is torn down after
      activation: {when: after:WARP-0705}
      owner_spec: WARP-0705
      profiles: [release]
      suite: environment provisioning selftest
    - id: YJ4
      title: The governor scales the worker count so measured burn tracks the target
        rate for the tighter of the session and weekly windows
      activation: {when: after:WARP-0706}
      owner_spec: WARP-0706
      profiles: [release]
      suite: governor selftest

release:
  milestone: VELDO Fleet v1 - hands-free elastic capability-aware parallel workers, token-paced
  version: plugin 3.2.0
  mode: continuous
  require_all_work_shipped: true
  require_full_regression: true
  rollback: each item is additive and independently revertable; coordination state is
    outside git history, so removing the feature leaves no tracked residue

open_decisions: []
---

## Intent

Make running VELDO at scale hands-free. Instead of a human provisioning worktrees,
assigning specs, and merging, a worker is one command (veldo work) that claims the
next available work from the global frontier, builds it, lands it, and repeats.
Workers join on demand and self-divide the work through an atomic claim, so two
accounts are just two vanilla sessions. Work routes to the machine that can run it
by capability, not by a hand-drawn machine-to-job map. Workers provision isolated
per-run environments while a heavy shared dataset is attached once, not duplicated.
A token governor paces the pool so the session and weekly budgets are used fully
without burning out early.

## Context

The Run Lens (PLAN-0005) built the primitives this stands on: the per-run registry
under the git common dir (WARP-0501), the executor that drives a spec through the
loop (WARP-0401/0502), the status reader (WARP-0503), and the cooperative inbox
(WARP-0505). The fleet adds the capability-matched claim ledger, the global frontier,
the worker loop, the serialized lander, environment provisioning, the governor, and
the launcher on top of them. Capability matching is the fleet expression of the
existing macOS-gated iOS runner (WARP-0308) generalized to arbitrary tags (macos,
gpu, a dataset, a device). Environment provisioning extends WARP-0406. The token
governor measures consumption because Claude Code exposes no live remaining-token API.

## Out of scope

A hosted scheduler or queue, a database or message bus, any detached or headless
claude process, and duplicating a large dataset per worker. The Jira and Confluence
tracker integration is a separate plan.

## Revisions

Revision 1 (2026-07-18): created from the fleet and pacing design - elastic pull-based
workers, a global claimable frontier including pending reviews, vanilla account-agnostic
workers, a serialized lander, and a measure-not-query token governor.

Revision 2 (2026-07-18): folded in the design worked out with the founder - CAPABILITY-
AWARE claiming (workers advertise free-form capability tags, specs declare requirements,
the claim matches requirements-subset-of-capabilities so iOS work routes to a Mac, GPU
work to a GPU box, shareable work spreads; O3, C4, added to Y1/Y2/Y3); a dedicated
ENVIRONMENT item (Y5, O4, C5) for provisioning an isolated per-run env from a repo
definition that attaches heavy shared read-only deps once and gives a mutating build a
cheap isolated write layer (schema, copy-on-write clone, or fixture) rather than copying
a 75M-row dataset; and grouping via an optional scope (plan or label) on veldo work and
veldo fleet. Parity across paired repos (e.g. mobile-android and mobile-ios) is a plan
pattern - a spec per repo plus a parity regression journey - not a fleet mechanism.
