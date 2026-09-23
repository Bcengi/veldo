---
schema: veldo.spec/v1
id: VELDO-0056
title: Disposable landing candidate construction and failure isolation
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W41
plan_revision: 3
depends_on: [VELDO-0042, VELDO-0050, VELDO-0052]
placement: [fleet, contracts]
protected_paths: []
footprint:
  - "engine/.veldo/lander.py"
  - ".veldo/lander.py"
  - "packs/*/.veldo/lander.py"
  - "scripts/suites/*_veldo_0056_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0056-disposable-landing-candidates.md"
  - "specs/index.md"
  - "proof/VELDO-0056/*"
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
      Claim: Candidate construction occurs in a dedicated detached workspace and includes
      implementation, evidence and fixed-watermark projections. Set and completeness: Use real
      fetch/merge with a bare fixture remote, another worktree holding trunk and a nondefault trunk
      name; compare caller HEAD/index/bytes/refs and candidate ancestry/tree before verification.
      Falsifier: Check out trunk in sync_main; the held-trunk detached-candidate check must fail.
    falsified_by: >
      Check out trunk in sync_main; the held-trunk detached-candidate check must fail.
  - id: AC2
    text: >
      Claim: Every required Git operation failure refuses the candidate. Set and completeness:
      Enumerate fetch, merge, object lookup and commit operations from the actual candidate path;
      provoke a real failed fetch and merge conflict plus missing required evidence, and inspect
      named failure and unmodified trunk. Falsifier: Ignore merge failure and continue to gate; the
      failed-candidate check must fail.
    falsified_by: >
      Ignore merge failure and continue to gate; the failed-candidate check must fail.
  - id: AC3
    text: >
      Claim: Rejected verification or policy leaves local and remote trunk unchanged. Set and
      completeness: Run candidate red gate, invalid proof, unresolved finding and rejected approval
      against real Git refs; compare refs/index/working bytes before and after each rejection.
      Falsifier: Move trunk before policy acceptance; the rejected-candidate ref comparison must
      fail.
    falsified_by: >
      Move trunk before policy acceptance; the rejected-candidate ref comparison must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Disposable landing candidate construction and failure isolation. Deliver the normal function needed by the running factory journey.

## Context

W41 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Build the whole candidate, including deterministic accepted projections, before the gate. Git
test operations belong in disposable fixture repositories. Keep distinct implementation and
evidence ancestry and do not check out or move the caller trunk.

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
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC1-AC3
SIGKILL/restart and competing-lander matrices moved to Release 2. Whole detached candidate,
checked Git failures and unchanged trunk on refusal remain. The criteria, declared evidence
universe, Context and Notes above now carry only the retained function. No specification
status or historical proof was changed.
