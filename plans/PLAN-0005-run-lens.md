---
schema: veldo.plan/v1
id: PLAN-0005
title: VELDO Run Lens - live observability and interaction for a running build
kind: mvp
status: released
revision: 1
owner: dmitry
approved_by: dmitry
approved_at: 2026-07-17
risk: standard

outcomes:
  - id: O1
    becomes_true: A human can see the live state of any running VELDO build - which
      spec, which loop step, gate and test progress, the current blocked question,
      and a heartbeat - without reading the repo or CLI internals.
    measure: a read surface shows a running build's current step and heartbeat, and
      classifies it active, blocked, stale, or done
  - id: O2
    becomes_true: A human can answer a blocked build and steer or abort it, and any
      answer that changes a requirement is committed to the spec rather than left as
      hidden chat truth.
    measure: a blocked build resumes after an answer is delivered through the run
      inbox, and a steer or abort is honored at the next safe checkpoint

non_goals:
  - id: NG1
    text: A work-management console. Jira (customized) is the management surface;
      that is the tracker plan, not this one.
  - id: NG2
    text: A hosted application, a database, or a message bus. The lens is git plus
      the event stream plus a per-run folder, read on demand.
  - id: NG3
    text: Preemptive process control. Steering and abort are cooperative checkpoints
      honored by the run process that owns the build, not signals from the viewer.

constraints:
  - id: C1
    text: Every item stays proportionate and is built through VELDO itself, with the
      same gate, proof, and independent review.
  - id: C2
    text: Live run state lives OUTSIDE git history, under the git common dir so it is
      shared across worktrees; durable lifecycle milestones stay in the tracked event
      stream. High-volume live progress is never committed.
  - id: C3
    text: Token and tool-call detail is shown only when the agent runtime supplies it,
      otherwise it is shown as unknown. It is never estimated. Blocked-elapsed is shown
      separately from human_minutes.

feature_tree:
  - id: F1
    title: Run registry and run-progress events - the substrate every surface reads
    outcome_refs: [O1]
  - id: F2
    title: Instrumented run wrapper - veldo run drives a spec and emits live progress
    outcome_refs: [O1]
  - id: F3
    title: Read surfaces - veldo status json, veldo watch terminal, and a thin local
      browser view
    outcome_refs: [O1]
  - id: F4
    title: Interaction - answer a blocked build, steer, abort, and the chat surface
    outcome_refs: [O2]

work:
  - item: R1
    spec: WARP-0501
    title: Run registry and run-progress event types - per-run folder under the git
      common dir plus the run lifecycle event vocabulary
    feature_refs: [F1]
    depends_on: []
    order: 10
  - item: R2
    spec: WARP-0502
    title: veldo run wrapper - allocate a run, drive a ready spec through the executor,
      and emit run progress and heartbeats per loop step
    feature_refs: [F2]
    depends_on: [WARP-0501]
    order: 20
  - item: R3
    spec: WARP-0503
    title: veldo status json and veldo watch - read git plus events plus the run
      registry and classify each run active, blocked, stale, or done
    feature_refs: [F3]
    depends_on: [WARP-0501]
    order: 30
  - item: R4
    spec: WARP-0504
    title: Thin read-only local status server - stdlib HTTP plus SSE on localhost,
      token-gated, rendering the same read model live
    feature_refs: [F3]
    depends_on: [WARP-0503]
    order: 40
  - item: R5
    spec: WARP-0505
    title: Answer, steer, and abort - command files in the run inbox with safe-point
      handling, and the requirement-change-must-commit rule
    feature_refs: [F4]
    depends_on: [WARP-0502]
    order: 50
  - item: R6
    spec: WARP-0506
    title: Chat surface wiring - the existing assistant reads veldo status json and
      delivers answers, steers, and aborts through the same run inbox
    feature_refs: [F4]
    depends_on: [WARP-0503, WARP-0505]
    order: 60

regression:
  journeys:
    - id: RJ1
      title: A run's live state is written to the registry and read back with the
        correct classification (active, blocked, stale, done)
      activation: {when: after:WARP-0501}
      owner_spec: WARP-0501
      profiles: [per_spec, release]
      suite: run registry selftest
    - id: RJ2
      title: veldo run drives a sample spec and the reader shows its live progress and
        final state end to end
      activation: {when: after:WARP-0503}
      owner_spec: WARP-0503
      profiles: [release]
      suite: run wrapper plus reader selftest
    - id: RJ3
      title: A blocked build resumes after an answer is delivered through the run
        inbox, and an abort is honored at the next safe checkpoint
      activation: {when: after:WARP-0505}
      owner_spec: WARP-0505
      profiles: [release]
      suite: interaction selftest

release:
  milestone: VELDO Run Lens v1 - see and steer a running build, git-native
  version: plugin 3.1.0
  mode: continuous
  require_all_work_shipped: true
  require_full_regression: true
  rollback: each item is additive and independently revertable; the run folder is
    outside git history, so removing the feature leaves no tracked residue

open_decisions: []
---

## Intent

Fill the one gap neither Jira nor the specs index covers: seeing and steering a
build while it runs. A running VELDO build should write its live state to a per-run
folder and emit run-progress events, and thin read surfaces should project that so
a human can watch which spec is building, which loop step it is on, gate progress,
and any blocked question, then answer, steer, or abort it. Every piece is git-native
and proportionate: git plus the event stream plus a run folder, no hosted app.

## Context

The executor (WARP-0401) already sequences the loop steps and is the natural
producer of run-progress events. The event stream (WARP-0108) and metrics reader are
the durable substrate; this plan adds the ephemeral live layer beside them and the
surfaces that read both. The design is the reconciled output of the tracker-and-UI
research: no new management console, a small read-only Run Lens for live builds, and
the existing assistant as the interaction surface.

## Out of scope

Work management (that is the tracker plan and customized Jira). A hosted control
plane, a database, a message bus, and preemptive process control are all excluded.

## Revisions

Revision 1 (2026-07-17): created from the reconciled tracker-and-UI research. The
server-side control plane remains out of scope; this plan is the live-build lens
only. Approved to build, Run Lens first.
