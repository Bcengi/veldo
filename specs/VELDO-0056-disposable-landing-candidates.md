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
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0050]
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
    Candidate construction records old remote tip, implementation and evidence commits, workspace
    identity, projection watermark, and each failed Git stage.
  metrics: >
    Count constructed candidates, merge refusals, regeneration failures, policy rejections, and
    trunk-ref changes before acceptance.
  traces: >
    Trace the serialized lock through fetch, detached candidate merge, projection materialization,
    commit, gate, and cleanup.
  error_taxonomy: >
    Distinguish fetch failure, merge conflict, forbidden union resolution, regeneration failure,
    commit failure, red gate, and rejected approval.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Lander.land and GitLandOps.sync_main/reconcile construct the whole integrated candidate
      in a dedicated detached workspace without checking out or moving local trunk. Set: Real lander
      processes, authority-backed land lock, git fetch and merge, implementation/evidence objects,
      accepted projections at a fixed watermark, and a disposable bare remote. Completeness: Run
      with trunk held by another fixture worktree, with a nondefault trunk name, and with concurrent
      landers. Record refs, HEAD, index, and working bytes in the caller and trunk workspaces.
      Verify candidate ancestry includes both implementation and evidence and every projection is
      committed before gate; SIGKILL after merge and restart without altering either trunk.
      Falsifier: Restore sync_main checkout of self.trunk before candidate construction;
      landing/detached-candidate must fail while another fixture worktree holds that branch.
    falsified_by: >
      Restore sync_main checkout of self.trunk before candidate construction;
      landing/detached-candidate must fail while another fixture worktree holds that branch.
  - id: AC2
    text: >
      Claim: GitLandOps.reconcile stops on any failed construction operation and never union-merges
      capability catalogs, self-tests, or authoritative history. Set: Actual fetch, merge, conflict
      enumeration, deterministic index/event regeneration, staging, and merge-commit operations
      reached by GitLandOps._git, reconcile, and _union_resolve_one. Completeness: Enumerate
      subprocess operations and conflict paths from implementation call sites, then inject real
      missing refs, receive/fetch failure, text and binary conflicts, failing regeneration commands,
      and a rejecting commit hook. Race projection input advancement and kill before candidate
      commit. Require failure, preserved evidence, zero gate/finalize calls on incomplete
      candidates, and unchanged trunk refs. Falsifier: Ignore a failing merge commit as current
      reconcile does and return ok; landing/failed-commit must detect progression to gate with an
      incomplete candidate.
    falsified_by: >
      Ignore a failing merge commit as current reconcile does and return ok; landing/failed-commit
      must detect progression to gate with an incomplete candidate.
  - id: AC3
    text: >
      Claim: Gate, contextual proof, review obligations, current scope, and protected-path policy
      are evaluated on the complete candidate; any refusal leaves local and remote trunk unchanged.
      Set: GitLandOps.gate/finalize invoked through Lander.land with the real canonical gate,
      installed policy checker, immutable proof, signed fixture approvals, and bare remote.
      Completeness: Run a clean positive candidate and candidates with a real red test, rejected or
      stale approval, wrong proof digest, builder as reviewer, and unresolved blocking finding.
      Compare both refs and caller/trunk bytes before and after each failure; kill during gate and
      policy evaluation and require restart to retain an unaccepted candidate, never advance trunk.
      Falsifier: Merge into local trunk before running the red candidate gate;
      landing/red-trunk-isolation must detect local trunk movement even though the push was
      withheld.
    falsified_by: >
      Merge into local trunk before running the red candidate gate; landing/red-trunk-isolation must
      detect local trunk movement even though the push was withheld.
required_evidence: [unit, integration]
rollback: >
  Stop new landing attempts, preserve candidate and lock/effect records, and discard only reconciled
  disposable workspaces. Never reset trunk to conceal a failed candidate.
---

## Intent

Build and reject landing candidates in isolation so failed verification cannot modify trunk.

## Context

Package C, W41 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A and B contracts govern this repair. This is a draft, not implementation or activation authority.

R48, R51, R58, and R76 replace the inspected lander behavior that checks out trunk, ignores some Git failures, and union-resolves shared files. This code controls source publication and is critical. The declared risk floor is critical; required approval must bind the eventual change and proof and is not recorded by this declaration.

## Out of scope

This item does not activate an authority service, publish to the project remote during qualification, or implement provider adapters.

## Notes

D1/D2 block authoritative land-lock and projection inputs; D3/D4 block qualified contained execution and isolated worker inputs. Candidate workspaces here are disposable integration workspaces, distinct from B worker clone provisioning. W42 owns exact-tip publication and recovery; W43 owns trusted external gate output. The candidate-only boundary must work before those are connected by W44, without claiming their unfinished evidence. Test Git operations only inside disposable fixture repositories. Retain before/after refs and failure outputs alongside each mutation diff. Event projection comes from ordered accepted records, never _union_resolve_one. Engine lander changes must synchronize byte-identically to repository and packs.
