---
schema: veldo.spec/v1
id: VELDO-0078
title: Backlog lifecycle and priority-controlled execution
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W63
plan_revision: 1
depends_on: [VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0076, VELDO-0077]
placement: [contracts, fleet, distribution]
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
  - "engine/.veldo/claim.py"
  - ".veldo/claim.py"
  - "packs/*/.veldo/claim.py"
  - "engine/.veldo/control_backlog*.py"
  - ".veldo/control_backlog*.py"
  - "packs/*/.veldo/control_backlog*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0078_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0078-backlog-lifecycle-priority-execution.md"
  - "specs/index.md"
  - "proof/VELDO-0078/*"
behavior_bearing: true
observability:
  logs: >
    Backlog transitions report class, request revision, phase, priority decision, decomposition
    version and first-unit claim.
  metrics: >
    Count unprioritized items, blocked interrupted phases, terminal exceptions and refused
    duplicate active units.
  traces: >
    Join intake and priority receipts to first claim, remaining decomposition units and terminal
    reconciliation.
  error_taxonomy: >
    Distinguish unresolved classification, missing priority, changed decomposition, duplicate
    active revision and unsupported DONE.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Only prioritized admitted work can create executable units eligible for scheduling.
      Set: control_backlog plus frontier.claimable, tasks.claim_answer/claim_task and
      claim.unit_id_problem over all eleven R11 states. Completeness: Compare full state-pair
      coverage with A, including RAW, QUARANTINED, PREPARED, AWAITING_GROOMING, REJECTED,
      ADMITTED, PRIORITIZED, ACTIVE, BLOCKED, DONE and CANCELED. Drive actual commands and direct
      claim paths; intake, ready spec text, model output and admission without priority must yield
      no executable unit or dispatch. Falsifier: Permit tasks.claim_task for an ADMITTED item
      without priority; backlog/admitted-not-prioritized must detect a granted claim.
    falsified_by: >
      Permit tasks.claim_task for an ADMITTED item without priority;
      backlog/admitted-not-prioritized must detect a granted claim.
  - id: AC2
    text: >
      Claim: The first claim activates the item atomically and only its approved decomposition can
      continue. Set: First and subsequent claims, one primary spec revision per engineering unit
      and exactly one owning backlog item. Completeness: Race real claim processes, crash at
      claim/item commit barriers and replay. Require one active unit per admitted spec revision
      and coherent claim/item state. Remaining approved units may run; adding a unit requires a
      new prioritization over revised decomposition, even while the item is ACTIVE. Falsifier:
      Append an executable unit to an ACTIVE item without renewed prioritization;
      backlog/decomposition-growth must detect its claim.
    falsified_by: >
      Append an executable unit to an ACTIVE item without renewed prioritization;
      backlog/decomposition-growth must detect its claim.
  - id: AC3
    text: >
      Claim: Blocked phases resume only after validated resolution, and terminal status reflects
      reconciled outcomes. Set: control_backlog completion/resumption and tasks.concluded
      consumers for every interrupted phase and terminal state. Completeness: Enumerate phases and
      unit outcomes from A; preserve interrupted phase/reason and require all required units
      completed or a signed alternative-outcome reconciliation. A produces path, canceled attempt
      or status edit cannot establish DONE. Reconsideration of rejected, done or canceled work
      creates a linked item and preserves old receipts. Falsifier: Use tasks.concluded file
      existence to mark a backlog item DONE; backlog/path-is-not-completion must detect missing
      accepted receipts.
    falsified_by: >
      Use tasks.concluded file existence to mark a backlog item DONE;
      backlog/path-is-not-completion must detect missing accepted receipts.
required_evidence: [unit, integration]
rollback: >
  Stop new backlog dispatch, retain interrupted phases and reconcile claimed units before
  restoring a compatible scheduler.
---

## Intent

Make priority a durable execution boundary and keep backlog lifecycle tied to approved units and their outcomes.

## Context

Package F, W63 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R07, R10/R11 and R61 build on C eligibility. tasks.concluded currently checks a path; enrolled backlog completion must consume accepted receipts instead. Unauthorized claims make this concern critical. Risk is critical; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

Grooming presentation and automatic defect policy evaluation are owned by W64/W65.

## Notes

D1 blocks atomic backlog/claim transitions and D2 published eligibility; D3/D4 block the inherited runner/clone execution proof. Dmitry must name or delegate the priority authority before a non-Dmitry principal can prioritize. Keep legacy TASK kinds distinct from backlog work classes. Map control_backlog under contracts/fleet and register it through W30; do not add an alternative unit-ID validator. Preserve first-claim crash tables and forbidden transition results for independent review.
