---
schema: veldo.spec/v1
id: VELDO-0040
title: Provider-neutral process supervision and descendant containment
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W25
plan_revision: 4
depends_on: [VELDO-0039]
placement: [fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/supervisor.py"
  - ".veldo/supervisor.py"
  - "packs/*/.veldo/supervisor.py"
  - "engine/.veldo/control_containment*.py"
  - ".veldo/control_containment*.py"
  - "packs/*/.veldo/control_containment*.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "packs/*/.veldo/control_launch*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/runner/veldo-runner*"
  - ".veldo/runner/veldo-runner*"
  - "packs/*/.veldo/runner/veldo-runner*"
  - "scripts/suites/*_veldo_0040_*.py"
  - "scripts/suites/*_veldo_0039_*.py"
  - "scripts/suites/*_veldo_0049_*.py"
  - "scripts/suites/*_veldo_0050_*.py"
  - "scripts/check_teeth_mutations.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0040-process-containment.md"
  - "specs/index.md"
  - "proof/VELDO-0040/*"
behavior_bearing: true
observability:
  logs: >
    Record the operation, domain, repository, unit or request identity, accepted input versions,
    outcome and named refusal without secrets.
  metrics: >
    Count accepted and refused operations and expose current pending work for this specification.
  traces: >
    Join accepted inputs, actual service observations and resulting authority records by identity.
  error_taxonomy: >
    Distinguish invalid input, missing authority, stale subject, unavailable service,
    missing evidence and unknown outcome where applicable; never label unknown as success.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Linux workers launch in a dedicated systemd/cgroup v2 group under a trusted wrapper.
      Set and completeness: On the selected real Linux profile launch a worker and ordinary
      descendants, inspect their group identity and worker/helper permissions, and refuse an
      unqualified profile before spawn. Falsifier: Launch a child outside its dispatch group; the
      group-membership observation must fail.
    falsified_by: >
      Launch a child outside its dispatch group; the group-membership observation must fail.
  - id: AC2
    text: >
      Claim: The Linux profile applies declared worker caps before launch. Set and completeness:
      Enumerate enabled profile settings for concurrency, elapsed runtime and memory/CPU/storage
      limits, inspect the actual installed controls and request an absent or invalid required
      setting; qualification must state which mechanisms bound each setting. Falsifier: Ignore the
      configured elapsed-runtime cap; a bounded live child must outlast it and fail the check.
    falsified_by: >
      Ignore the configured elapsed-runtime cap; a bounded live child must outlast it and fail the
      check.
  - id: AC3
    text: >
      Claim: Stop terminates the real worker group and exit detection uses OS notifications. Set and
      completeness: Exercise ordinary exit, cooperative stop and a signal-ignoring descendant;
      observe termination escalation, exit identity and empty group before retirement. Falsifier:
      Stop only the parent; the surviving-descendant observation must fail.
    falsified_by: >
      Stop only the parent; the surviving-descendant observation must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Provider-neutral process supervision and descendant containment. Deliver the normal function needed by the running factory journey.

## Context

W25 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## What the reviewer judges

- Normal use: on this Linux box the dispatch receiver launches each worker in its own systemd scope and
  cgroup v2 group under the trusted wrapper, with the profile's declared caps applied before the worker
  runs; a stop terminates the whole group; exits are detected from operating system notifications, and
  the group is empty before the dispatch is retired.
- Threat model: a worker and its descendants (a child started outside the group, a signal-ignoring
  descendant, a worker that outlasts its elapsed-runtime cap or its memory or CPU limits). The owner's
  account, systemd and the kernel are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); root or another
  account acting on the group; kernel or systemd defects; recovery when systemd is unavailable
  (Release 2); the Mac profile (VELDO-0124).

## Notes

This criterion universe is this Linux box only; the Mac profile is a separate Release 1
specification. Keep cgroup-backed launch/stop and configured caps; aggregate exhaustion,
escape and machine-loss qualification are Release 2.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 1: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC2/AC3
aggregate resource-exhaustion qualification and AC4 authority-loss/PID-reuse recovery moved to
Release 2; other host kinds moved to Release 4. Linux launch/caps/stop/exit remain, Mac in
0124. The criteria, declared evidence universe, Context and Notes above now carry only the
retained function. No specification status or historical proof was changed.

2026-09-24, implementation (branch build-veldo-0040): `.veldo/control_containment.py` runs each local
worker in its own systemd user scope in the profile's slice with the profile's caps installed before
the worker runs, refuses an unqualified or incomplete profile before spawn, stops cooperatively and
then over the whole group, detects exit from kernel notifications and retires only after an empty
group; the VELDO-0039 receiver calls it. Suite 63_veldo_0040_containment (20 rows), red at f5aebae,
22 mutations as finding 40; proof in proof/VELDO-0040/. Merging main required the VELDO-0049 and
VELDO-0050 suites to give their receiver this host's profile (f6d217e). The footprint names those two suites
for that reason (review, 2026-09-24).

2026-09-25, PLAN-0019 revision 4, third review: the footprint drops `control_runner*.py`, which does not
exist; the Runner is class `Runner` in `control_launch`, already in the footprint. Criteria and status
unchanged.

2026-10-02, runtime-cap investigation (fix-flake-0040): the row now names every
false conjunct and records the compared values for failed_details. The earlier
late-origin explanation was incorrect: recording running after activation
reduces the original measured gap. The original f1e1abb9 suite and production
code passed ten loaded rounds of two simultaneous suite copies plus a pinned
busy loop on each available CPU. No false conjunct or production cause was
reproduced; the closest gap was 1.6435189247131348 seconds against 2.7 seconds.
The monotonic scope-activation origin remains a correct, stricter measurement,
not an established flake fix. The existing result read retains activation,
stop and inactive timestamps before clearing the scope. Installed controls,
assertion bounds and timeouts are unchanged. Proof records observations and
limitations separately from the reviewer's gate. The current row passed normally,
in the inherited gate shell environment and in ten matching loaded rounds. The
runtime-cap-disabled mutation failed by assertion with complete diagnostics;
the historical gate red remains unreproduced and its cause unknown.

2026-10-02, measured manager-result loss (fix-flake-0040): the reviewer's gate
on cd3df736 measured a stopped descendant within the runtime bound, but an
exited dispatch with deadline_stop false, cause exit, no retained scope clocks,
and six false runtime-cap conjuncts. The cap worked; final manager evidence
was lost in conclude's early or failed final read. Stop.adapter_exited only
sets Stop.cause; the old local cause check already mapped a successfully read
timeout to runtime_cap. The precedence restructuring is a regression guard,
not the measured defect. Group.conclude now waits within SETTLE_SECONDS for failed or inactive,
bounds each show call by the remaining budget, retries tool and timestamp parse
failures, and records unknown when evidence remains unreadable. The receiver
resolves both cause sources explicitly: manager timeout and oom-kill outrank
inferred exit, while requested, deadline, usage, heartbeat and configuration
stops keep precedence. Unknown manager evidence cannot silently become exit.
Three deterministic suite 63 rows cover cap precedence after adapter exit,
settlement from deactivating and unreadable evidence; each has a registered
mutation. The live runtime-cap row and its diagnostics and bounds are retained.
Selected-suite verification and manual mutation results are in proof/VELDO-0040;
the canonical gate remains the reviewer's responsibility.

2026-10-02, proof review correction (fix-flake-0040): the precedence mutation
is named containment-resolved-exit-hides-cap to identify its role as a guard
on the restructured receiver. Explicit causes in its suite row now come from
the real request, meter, deadline and heartbeat paths through receiver begin().
The conclude-settles falsifier is also checked against the complete pre-fix
conclude rebuilt from ffb12c22 in a temporary copy. reset-failed shares the
remaining SETTLE_SECONDS budget and is skipped when no time remains. Only
suite 63 normal, gate-environment and temporary-copy checks run in this review
continuation; no load mode or canonical gate runs here.
