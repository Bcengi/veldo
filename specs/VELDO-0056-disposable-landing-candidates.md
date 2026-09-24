---
schema: veldo.spec/v1
id: VELDO-0056
title: Disposable landing candidate construction and failure isolation
status: ready
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
  - "scripts/suites/04_run_status_reader_veldo.py"
  - "scripts/check_teeth_mutations.py"
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

## What the reviewer judges

- Normal use: the lander builds each landing candidate in its own detached workspace, from trunk at a
  fixed watermark, with the implementation commit, the evidence commit and the accepted projections,
  and never checks out or moves the caller's trunk, including when another worktree holds trunk and
  whatever trunk is named. Every Git failure (fetch, merge conflict, object lookup, commit) and any
  missing required evidence refuses the candidate by name. A red gate, an invalid proof, an unresolved
  finding or a rejected approval leaves local and remote trunk exactly as they were.
- Threat model: a candidate built by checking out or moving trunk; a Git failure ignored and the
  candidate gated anyway; trunk moved before the policy accepts; a candidate missing its evidence or
  projections. The owner's account, Git and the store are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); a kill or
  restart during construction and competing landers (Release 2, see History); publication and
  completion (VELDO-0057); forged rows in our own store, files planted in the installed directory and
  resource exhaustion by our own account.

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

2026-09-24 footprint, before any mutation is registered: two paths are added, each because the
change cannot be made without it. `scripts/check_teeth_mutations.py` is the registry every
criterion's negative controls are registered in (finding 56), as VELDO-0049 and VELDO-0050 did.
`scripts/suites/04_run_status_reader_veldo.py` holds WARP-0704's real-Git lander rows, which
called `GitLandOps.reconcile` directly in the caller's checkout and read the merge result from the
caller's own files: with the candidate built in its own workspace those rows now build the
candidate (sync_main, then reconcile), read the candidate, require the caller untouched, and give
each build the proof manifest the candidate now requires. Every row keeps its name and its claim.

2026-09-24 implementation: `.veldo/lander.py` (engine copy identical) builds every candidate in a
dedicated detached workspace, a new repository borrowing the caller's objects through alternates, from
the published trunk tip fetched once as its fixed watermark; it merges the implementation the proof
names, then the evidence, then commits the projections derived from the merged tree, and never checks
out, moves or fetches into the caller's trunk. Every Git step is checked and refuses by name, and missing
evidence refuses before any merge. The gate runs in the candidate; finalize asks the authority's
`CandidatePolicy` (VELDO-0050 proof, VELDO-0049 review obligations, VELDO-0052 publication over the
candidate) or, for a pre-factory land, the repository policy at the candidate, and only then pushes the
exact candidate. Suite 67 has 11 rows, each assertion row recorded red by assertion at 8995740 and at
the merged 5ba4a02 (`proof/VELDO-0056/`), with 22 finding-56 mutations. Stated there: `policy_check.py`
refuses every VELDO-0050 manifest as stale (its digest spec_revision), so a factory land asks the
authority instead; local trunk synchronization and exact-tip publication stay VELDO-0057's.
