---
schema: veldo.spec/v1
id: VELDO-0041
title: Independent heartbeat, bounded stopping, and safe capacity retirement
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W26
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0040]
placement: [fleet, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/supervisor.py"
  - ".veldo/supervisor.py"
  - "packs/*/.veldo/supervisor.py"
  - "engine/.veldo/control_heartbeat*.py"
  - ".veldo/control_heartbeat*.py"
  - "packs/*/.veldo/control_heartbeat*.py"
  - "engine/.veldo/control_retirement*.py"
  - ".veldo/control_retirement*.py"
  - "packs/*/.veldo/control_retirement*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0041_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0041-heartbeat-and-retirement.md"
  - "specs/index.md"
  - "proof/VELDO-0041/*"
behavior_bearing: true
observability:
  logs: >
    Heartbeat and stop records identify wrapper sequence, deadline, escalation stage, observed
    containment, and accounting status.
  metrics: >
    Measure heartbeat gaps, thirty-second liveness closures, ten-second cooperative grace,
    five-second kill escalation, and quarantined slots.
  traces: >
    Join monotonic observations from wrapper and supervisor to effect fencing, OS signals, exit
    evidence, and capacity-release transaction.
  error_taxonomy: >
    Distinguish missing heartbeat, uncertain liveness, cooperative-stop timeout, surviving
    descendants, accounting pending, and cleanup incomplete.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A trusted wrapper emits ten-second heartbeats and renews claims independently of
      blocking model calls; thirty seconds without a heartbeat closes effect permission. Set: Real
      wrapper, model-response child, independent supervisor, and accepting effect process on the
      qualified profile. Completeness: Block child output and model return, then SIGSTOP the
      wrapper while leaving the effect receiver live. Observe independent monotonic timestamps,
      continued heartbeat during model silence, and permission closure at the declared
      missed-heartbeat deadline; separately retain the two-second leadership-loss bound.
      Falsifier: Emit heartbeats only after model calls return and hang the model child;
      heartbeat/independent-wrapper must detect missed wrapper heartbeats.
    falsified_by: >
      Emit heartbeats only after model calls return and hang the model child;
      heartbeat/independent-wrapper must detect missed wrapper heartbeats.
  - id: AC2
    text: >
      Claim: Cooperative stop escalates after ten seconds to containment termination and after
      five more seconds to killing remaining descendants. Set: Real cooperative, hanging,
      signal-ignoring, and grandchild-spawning workers under every qualified containment profile.
      Completeness: Request stop through the accepted control API and record adapter request plus
      actual SIGTERM and SIGKILL delivery with monotonic times. SIGSTOP the orchestrator during
      escalation and require the independent supervisor to finish within versioned policy bounds
      without waiting on model output. Falsifier: Send termination only to the parent and leave a
      SIGTERM-ignoring grandchild alive beyond the kill deadline; heartbeat/stop-escalation must
      detect it.
    falsified_by: >
      Send termination only to the parent and leave a SIGTERM-ignoring grandchild alive beyond the
      kill deadline; heartbeat/stop-escalation must detect it.
  - id: AC3
    text: >
      Claim: Retirement releases a slot only after empty containment and durable outcome,
      accounting, and resource-cleanup records; uncertainty quarantines it. Set: Real runner group
      retirement and reservation consumers across exit, accounting write, cleanup, and release
      commit. Completeness: SIGKILL the retirement process at every boundary, withhold each
      required observation, and race a new admission. Reopen SQLite and inspect the actual group
      and files; require retained capacity until all obligations are proven, with no double
      release after restart. Falsifier: Commit capacity release before accounting and kill the
      retiring process in that window; heartbeat/retirement-commit must reject reuse of the slot.
    falsified_by: >
      Commit capacity release before accounting and kill the retiring process in that window;
      heartbeat/retirement-commit must reject reuse of the slot.
required_evidence: [unit, integration]
rollback: >
  Stop new work, complete or quarantine all retirement sequences, and retain reservations until
  the prior qualified supervisor proves empty containment and accounting.
---

## Intent

Supervise worker liveness independently and release capacity only after bounded stopping and durable retirement.

## Context

Package B, W26 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R24, R43-R44, R57. Package A contracts must be accepted before implementation; this draft grants no implementation or activation authority.

Dependent supervision or early retirement could leave privileged descendants running after capacity is reassigned. The declared risk floor is critical. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

Model-output interpretation, billing qualification, and scheduling policy are outside this lifetime concern.

## Notes

D3 directly blocks the runner lifecycle profile until Dmitry ratifies it; D1 and D2 are inherited through dispatch and containment. Use real elapsed time for the default timing qualification, with an independent observer and declared measurement tolerance; fake time alone cannot prove process independence. A heartbeat says the wrapper is responsive, not that an external effect succeeded. Empty-group evidence must cover all descendants.

