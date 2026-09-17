---
schema: veldo.spec/v1
id: VELDO-0093
title: Per-project cycle serialization and replaceable checkpoint recovery
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W78
plan_revision: 1
depends_on: [VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0088, VELDO-0089, VELDO-0090, VELDO-0091, VELDO-0092]
placement: [contracts, loop, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/frontier.py"
  - ".veldo/frontier.py"
  - "packs/*/.veldo/frontier.py"
  - "engine/.veldo/tasks.py"
  - ".veldo/tasks.py"
  - "packs/*/.veldo/tasks.py"
  - "engine/.veldo/control_project_cycle*.py"
  - ".veldo/control_project_cycle*.py"
  - "packs/*/.veldo/control_project_cycle*.py"
  - "engine/.veldo/control_graph*.py"
  - ".veldo/control_graph*.py"
  - "packs/*/.veldo/control_graph*.py"
  - "engine/.veldo/control_checkpoint*.py"
  - ".veldo/control_checkpoint*.py"
  - "packs/*/.veldo/control_checkpoint*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0093_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0093-project-cycle-serialization-checkpoint-recovery.md"
  - "specs/index.md"
  - "proof/VELDO-0093/*"
behavior_bearing: true
observability:
  logs: >
    Serialization receipts identify project/cycle holder, snapshot watermark, pending watermark,
    stable actions and recovery disposition.
  metrics: >
    Measure active cycles per project, coalesced follow-ups, stale proposals and domain/effect
    differences across checkpoint variants.
  traces: >
    Join concurrent input through one durable cycle and follow-up, then compare replacement
    adapters against the same authoritative command history.
  error_taxonomy: >
    Distinguish cycle already active, stale holder, pending relevant input, checkpoint
    ahead/behind/conflict and unresolved prior effect.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: At most one cycle per project runs, with exactly one bounded follow-up when relevant
      input remains. Set: control_project_cycle start/finish/cancel, B control_graph and
      owner/service command paths under R29. Completeness: Race real processes for one and two
      projects. Bind every cycle to project version, journal/published watermark, governing
      contract, complete snapshot and reservation. Deliver relevant and unrelated events during
      reasoning, complete/cancel/crash the holder and restart. Require one active cycle per
      project, coalesced pending watermark, no needless interruption from unrelated events and
      independent progress of owner commands and other projects. Falsifier: Key active-cycle
      uniqueness by worker rather than project; cycles/one-per-project must detect concurrent
      holders for one project.
    falsified_by: >
      Key active-cycle uniqueness by worker rather than project; cycles/one-per-project must
      detect concurrent holders for one project.
  - id: AC2
    text: >
      Claim: Repeated graphs and a deterministic replacement adapter produce identical Veldo
      transitions for identical authorized proposals. Set: Installed LangGraph and deterministic
      adapters across all registered action types, read-set predicates and failure outcomes from
      W73-W77. Completeness: Register executable RJ5/RJ6 journeys. Replay identical snapshots,
      cycle/action IDs and proposals in independent real authority fixtures, covering concurrent
      input, missing specialists, escalation, exhausted budgets and stale reads with fixed project
      version. Compare canonical domain transitions, decisions, dispatch IDs and refusal results;
      retain adapter-specific telemetry separately using explicit schema fields. Falsifier: Let
      the deterministic adapter bypass roster eligibility validation; cycles/adapter-equivalence
      must detect different domain results for the same proposal.
    falsified_by: >
      Let the deterministic adapter bypass roster eligibility validation;
      cycles/adapter-equivalence must detect different domain results for the same proposal.
  - id: AC3
    text: >
      Claim: Deleting every checkpoint changes no admission, priority, assignment, dispatch
      history, decision or completion and repeats no effect. Set: control_checkpoint storage/read
      isolation and control_project_cycle recovery, with frontier.claimable and tasks.claim_task
      consumers. Completeness: Register RJ7 and derive checkpoint tables from the installed
      inventory. Drive actual committed and uncertain dispatches, then delete all checkpoints,
      restore ahead/behind/conflicting content and remove the execution runtime. Replay verified B
      history; compare complete authoritative domain tables and observed target effect counts
      before/after. Ahead progress grants no authority; behind state receives committed results,
      conflicts are discarded/quarantined, and unknown effects remain AWAITING_AUTHORITY.
      Falsifier: Allocate a fresh dispatch when its checkpoint is missing despite a committed
      receiver record; cycles/checkpoint-deletion must detect a repeated external effect.
    falsified_by: >
      Allocate a fresh dispatch when its checkpoint is missing despite a committed receiver
      record; cycles/checkpoint-deletion must detect a repeated external effect.
required_evidence: [unit, integration, journeys]
rollback: >
  Stop affected cycle scheduling, retain pending watermarks and uncertain effects, and use
  deterministic reconciliation under current authority.
---

## Intent

Qualify serialized, restartable project reconciliation whose authority is independent of every graph checkpoint.

## Context

Package G, W78 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R29/R34 and R62 culminate in RJ5-RJ7. Checkpoint-dependent authority or duplicate dispatch makes this recovery concern critical. Risk is critical; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

Automatic host failover, checkpoint-derived completion and a separate coordination database are excluded.

## Notes

D1/D2 block the authoritative cycle/replay proof; D3/D4 block real contained worker and clone qualification. Dmitry must enroll any resuming authority needed for an uncertain effect; deleting a checkpoint cannot substitute for that ruling. W28/W29 own adapter/checkpoint mechanisms, and W78 qualifies them across project operations. Map the cycle recovery paths into effective loop/fleet areas and inventory the journey assets before ready. Require nonempty action/table/effect matrices, record SIGKILL barriers and retain exact mutation diffs with the named red rows.
