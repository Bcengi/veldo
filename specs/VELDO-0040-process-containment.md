---
schema: veldo.spec/v1
id: VELDO-0040
title: Provider-neutral process supervision and descendant containment
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W25
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0039]
placement: [fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/supervisor.py"
  - ".veldo/supervisor.py"
  - "packs/*/.veldo/supervisor.py"
  - "engine/.veldo/control_runner*.py"
  - ".veldo/control_runner*.py"
  - "packs/*/.veldo/control_runner*.py"
  - "engine/.veldo/control_containment*.py"
  - ".veldo/control_containment*.py"
  - "packs/*/.veldo/control_containment*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/runner/veldo-runner*"
  - ".veldo/runner/veldo-runner*"
  - "packs/*/.veldo/runner/veldo-runner*"
  - "scripts/suites/*_veldo_0040_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0040-process-containment.md"
  - "specs/index.md"
  - "proof/VELDO-0040/*"
behavior_bearing: true
observability:
  logs: >
    Runner events identify dispatch, systemd unit, cgroup, boot and start identities, installed
    limits, and retirement cause.
  metrics: >
    Measure aggregate memory, descendant cumulative CPU time, writable bytes and inodes,
    exhaustion events, and surviving authority capacity.
  traces: >
    Join host qualification and helper configuration to pre-launch limits, process tree
    observations, OS exit notification, and quarantine receipt.
  error_taxonomy: >
    Distinguish unsupported host, unavailable containment, unenforceable resource bound, escape
    attempt, resource exhaustion, and reused process identity.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Only a qualified Linux systemd and cgroup v2 profile launches autonomous workers,
      with one dedicated containment group and trusted wrapper per dispatch. Set: Real workers
      that fork, create new sessions, spawn grandchildren, attempt cgroup changes, reach the
      service manager, or signal the authority. Completeness: Derive attacks from each R43
      privilege boundary and execute actual descendant programs under the worker identity. Inspect
      cgroup membership and OS permission failures, require a narrowly scoped operations-installed
      helper, and refuse unsupported or partially configured host profiles before launch.
      Falsifier: Launch a grandchild outside its assigned cgroup after setsid;
      containment/session-escape must detect the surviving escaped descendant.
    falsified_by: >
      Launch a grandchild outside its assigned cgroup after setsid; containment/session-escape
      must detect the surviving escaped descendant.
  - id: AC2
    text: >
      Claim: Hard non-worker-writable aggregate memory, cumulative descendant CPU-time, and
      writable-storage byte and inode limits are installed before launch within qualified host
      capacity. Set: Every supported host/helper profile and writable mount, including temporary
      files, clone output, and captured logs. Completeness: Enumerate mounts and limit enforcement
      mechanisms from the installed profile; run real descendants that attempt to raise or evade
      each limit, including cumulative CPU use across exited children. Remove each enforcement
      mechanism and race admissions exceeding aggregate capacity; require refusal while reserving
      authority and unrelated-project resources. Falsifier: Enforce only per-process CPU limits
      and run sequential descendants whose combined CPU exceeds the dispatch budget;
      containment/aggregate-cpu must detect failure to stop the group.
    falsified_by: >
      Enforce only per-process CPU limits and run sequential descendants whose combined CPU
      exceeds the dispatch budget; containment/aggregate-cpu must detect failure to stop the
      group.
  - id: AC3
    text: >
      Claim: Exhausting any resource bound closes effect permission, stops the group, and
      quarantines its slot without exhausting the authority or unrelated projects. Set: Real
      descendant memory allocation, CPU loops, byte writes, and inode creation in each writable
      storage class. Completeness: Exhaust every registered limit on a bounded qualification host
      while a separate project and the authority perform real transactions. Verify continued
      responses, stopped descendants, retained reservation, and durable outcome/accounting/cleanup
      obligations; kill the supervisor during exhaustion and recover the same quarantine.
      Falsifier: Exclude captured logs from writable-byte limits and run a log-flooding child;
      containment/log-exhaustion must detect host exposure or missing group stop.
    falsified_by: >
      Exclude captured logs from writable-byte limits and run a log-flooding child;
      containment/log-exhaustion must detect host exposure or missing group stop.
  - id: AC4
    text: >
      Claim: Authority death, control-channel loss, and service stop retire affected groups before
      replacement scheduling; OS exit identity cannot be revived by PID reuse. Set: Real
      authority, wrapper, helper, and descendant processes, with boot identity and process-start
      identity in durable launch records. Completeness: SIGKILL authority and wrapper separately,
      break their control socket, and stop the systemd service. Observe OS exit notifications and
      empty groups before replacement acceptance; present an old PID record with mismatched start
      or boot identity and reject it as the old invocation. Falsifier: Match recovery by PID alone
      after substituting a live unrelated process with a different start identity;
      containment/pid-reuse must refuse that match.
    falsified_by: >
      Match recovery by PID alone after substituting a live unrelated process with a different
      start identity; containment/pid-reuse must refuse that match.
required_evidence: [unit, integration]
rollback: >
  Disable worker admission, close effect capabilities, stop all affected groups, and retain
  quarantined reservations until verified cleanup under the prior qualified profile.
---

## Intent

Contain real worker descendants with enforceable host resource bounds and supervision independent of the model process.

## Context

Package B, W25 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R03, R24, R43-R45, R50, R57. Package A contracts must be accepted before implementation; this draft grants no implementation or activation authority.

Containment failure could expose authority credentials or exhaust the host and unrelated projects. The declared risk floor is critical. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

Live provider qualification, cooperative stop timing, and worker cache provisioning belong to D, W26, and W27 respectively.

## Notes

D3 directly blocks implementation of the production profile and service activation until Dmitry rules; D1 and D2 are inherited from durable dispatch. Package A must activate the replacement lifecycle policy and architecture revision before ready implementation proceeds. CPU rate limiting alone does not bound cumulative CPU time, and memory limits alone do not bound disk bytes or inodes. Qualification must establish the actual mechanisms; missing mechanisms are blockers, not waived tests. The helper and its non-code assets need explicit inventory entries.

