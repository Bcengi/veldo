---
schema: veldo.spec/v1
id: VELDO-0063
title: Production governor and lifecycle failure qualification
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W48
plan_revision: 1
depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0060, VELDO-0061, VELDO-0062]
placement: [fleet, metrics, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/fleet.py"
  - ".veldo/fleet.py"
  - "packs/*/.veldo/fleet.py"
  - "engine/.veldo/governor.py"
  - ".veldo/governor.py"
  - "packs/*/.veldo/governor.py"
  - "engine/.veldo/budget_state.py"
  - ".veldo/budget_state.py"
  - "packs/*/.veldo/budget_state.py"
  - "engine/.veldo/accounts.py"
  - ".veldo/accounts.py"
  - "packs/*/.veldo/accounts.py"
  - "engine/.veldo/control_runner*.py"
  - ".veldo/control_runner*.py"
  - "packs/*/.veldo/control_runner*.py"
  - "engine/.veldo/control_retirement*.py"
  - ".veldo/control_retirement*.py"
  - "packs/*/.veldo/control_retirement*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0063_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0063-production-governor-lifecycle.md"
  - "specs/index.md"
  - "proof/VELDO-0063/*"
behavior_bearing: true
observability:
  logs: >
    Governor decisions record accepted budget watermark, measured versus unknown burn, requested
    and admitted workers, backoff cause, and retained retirement obligations.
  metrics: >
    Measure live request charges, active/quarantined capacity, two-second fencing, heartbeat gaps,
    stop escalation, memory/CPU/storage exhaustion, and authority response latency.
  traces: >
    Correlate governor desired counts and fleet reconciliation with reservation commits, real
    engine processes, OS signals, empty groups, accounting, and resource cleanup.
  error_taxonomy: >
    Distinguish pacing backoff, unmeasured exposure, scope invalidation, revoked authority, missed
    heartbeat, exhausted resource, and incomplete retirement.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Production pacing never grants more work than durable capacity and spend permit,
      including bootstrap and backoff resumption. Set:
      governor.desired_workers/measure_per_worker_rate/AccountGovernor.desired/resume_at,
      fleet.FleetLauncher.run/reconcile, and budget_state.budget_report on every qualified
      Claude/Codex version and host profile. Completeness: Derive the engine/profile matrix from
      W45-W47 registrations and all posture/window states from governor and budget_state. Run
      concurrent live invocations with actual cost receipts across accounts/projects, exhaust each
      ceiling, remove usage, and race budget changes while waiting. Require fresh
      eligibility/reservation checks on resume, bounded bootstrap exposure, and no
      maximum-concurrency permission from unmeasured spend. Falsifier: Keep desired_workers
      bootstrap returning maximum runnable capacity when outstanding exposure is unbounded;
      governor/unknown-bootstrap must detect an additional live launch.
    falsified_by: >
      Keep desired_workers bootstrap returning maximum runnable capacity when outstanding exposure
      is unbounded; governor/unknown-bootstrap must detect an additional live launch.
  - id: AC2
    text: >
      Claim: Independent supervision closes permissions and stops actual engines within B policy
      bounds despite hangs, authority loss, scope change, or revocation. Set:
      fleet.WorkerSpawner.retire and FleetLauncher.reconcile with the installed B runner, actual
      Claude/Codex parents and descendants, and every registered stop cause. Completeness:
      Exercise normal and signal exits, hangs, SIGSTOP of engine and authority, control-channel
      loss, missed wrapper heartbeat, committed scope changes, and revoked authority. Observe
      ten-second independent heartbeats, thirty-second liveness closure, two-second leadership
      fencing, ten-second cooperative grace and five-second kill escalation with an independent
      monotonic observer and declared tolerance. Resume old processes and require stale-effect
      refusal. Falsifier: Signal only the engine parent on escalation while a real grandchild
      ignores termination; governor/descendant-stop must detect survival past the kill deadline.
    falsified_by: >
      Signal only the engine parent on escalation while a real grandchild ignores termination;
      governor/descendant-stop must detect survival past the kill deadline.
  - id: AC3
    text: >
      Claim: Real resource exhaustion remains confined to the dispatch while the authority and
      unrelated projects stay operational. Set: Every supported engine/host/helper combination and
      writable mount, with fleet admission and B aggregate memory, cumulative descendant CPU-time,
      storage-byte and inode limits. Completeness: Inventory configured limits/mounts and run
      actual engine tool descendants that fork, setsid, attempt escape or limit changes, allocate
      memory, consume CPU across exited children, fill temporary/clone/log bytes, and exhaust
      inodes. Race aggregate admission against reserved host capacity. Record closed effects,
      stopped groups, quarantined slots and continued real transactions in the authority and
      another project; missing mechanisms refuse qualification. Falsifier: Exclude captured engine
      logs from writable-storage limits; governor/log-exhaustion must detect missing confinement
      or loss of unrelated-project progress.
    falsified_by: >
      Exclude captured engine logs from writable-storage limits; governor/log-exhaustion must
      detect missing confinement or loss of unrelated-project progress.
  - id: AC4
    text: >
      Claim: Governor scale-down and restart cannot release account or host capacity until
      containment, outcome, accounting, and cleanup are durably reconciled. Set:
      fleet.InSessionSpawner.retire, AccountSpreader.release, FleetLauncher.reconcile and
      budget_state.survival/report_lines across all W45-W47 profiles, orphan recovery, and
      interrupted accounting. Completeness: Kill retirement at each durable boundary and restart
      the actual runner/governor while another client requests the slot. Hold a descendant, usage
      receipt, uncertain effect, or cleanup obligation in turn. Compare OS census, SQLite
      reservations, report watermarks, and provider charges; uncertainty retains quarantine and
      scope/revocation blocks relaunch. Recover with B evidence commands as the positive control.
      Falsifier: Release AccountSpreader capacity immediately after parent exit before
      descendant/accounting reconciliation; governor/retirement-race must catch concurrent reuse
      of the reserved slot.
    falsified_by: >
      Release AccountSpreader capacity immediately after parent exit before descendant/accounting
      reconciliation; governor/retirement-race must catch concurrent reuse of the reserved slot.
required_evidence: [unit, integration]
rollback: >
  Stop affected fleet admission, fence and retire or quarantine workers, preserve accounting and
  reservations, and restore only the prior qualified governor/profile combination.
---

## Intent

Prove production pacing and failure handling preserve bounded process lifetime, host capacity, and spending across both real engines.

## Context

Package D, W48 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A/B/C contracts govern implementation. This draft grants no implementation or activation authority.

R24, R39, R43-R45, and R59 require live combined qualification. The baseline governor permits maximum workers at zero measured rate, and fleet retirement releases accounts after a stop callback; those shortcuts cannot authorize enrolled production capacity. The declared risk floor is critical; required approval must bind the eventual change and proof. This declaration records no approval.

## Out of scope

New provider protocols, alternative host activation, and model-mediated project coordination remain separate.

## Notes

D1-D4 block this combined qualification until Dmitry ratifies authority storage, off-host acknowledgment, systemd/cgroup lifecycle, and isolated clones/cache and their dependencies qualify. The advertised engine/profile universe must equal W45-W47 qualification registrations; no skipped unavailable host row counts as passed. Use real elapsed-time observers and real provider costs within finite accepted test budgets. Pacing estimates remain advisory to the B reservation predicate, and rolling windows never erase outstanding possible charges. Resolve new runner/retirement and budget_state area mappings before ready and keep engine copies byte-identical. Save actual signals, process trees, live cost reconciliation, applied mutation diffs, and their named failures. A failed production row disables that profile; it does not relax the runner contract.
