---
schema: veldo.spec/v1
id: VELDO-0059
title: Installed end-to-end floor slice with fake model and real enforcement
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W44
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058]
placement: [distribution, fleet, loop, enforcement, docs]
protected_paths: []
footprint:
  - "engine/.veldo/control_floor_slice*.py"
  - ".veldo/control_floor_slice*.py"
  - "packs/*/.veldo/control_floor_slice*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/pack.py"
  - ".veldo/pack.py"
  - "packs/*/.veldo/pack.py"
  - "scripts/check_install_and_run.py"
  - ".veldo/packs.json"
  - "plans/PLAN-0019-dark-factory.md"
  - "scripts/suites/*_veldo_0059_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0059-installed-floor-slice.md"
  - "specs/index.md"
  - "proof/VELDO-0059/*"
behavior_bearing: true
observability:
  logs: >
    Slice reports identify installed pack/runtime digests, enrolled fixture domain, journey,
    station, dispatch, and exact failure barrier.
  metrics: >
    Report RJ1-RJ4 execution coverage, actual child and receiver counts, retained reservations,
    missing installed assets, and unchanged-trunk assertions.
  traces: >
    Join admitted spec and signed fixture authority through claim, clone, construction, proof,
    separate review, candidate gate, remote confirmation, and replicated completion.
  error_taxonomy: >
    Distinguish installation omission, unqualified host, unsafe reservation/limits, station refusal,
    changed trunk on failure, and repeated publication after recovery.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: An installed composed pack drives one admitted specification from real claim to
      remotely confirmed and replicated completion with only model responses faked. Set:
      pack.assemble_pack and engine_files, init_scaffold.scaffold, scripts/check_install_and_run.py
      install_and_run, installed WorkLoop.step, Dispatcher._dispatch_build/_dispatch_review,
      Executor.run, and Lander.land with GitLandOps. Completeness: Install a declared reference pack
      into a fresh repository without source-tree imports; enumerate its actual
      modules/runtime/assets against W30 inventory. Use real control.sqlite3, OpenSSH signatures,
      locks, isolated clones/read-only pinned cache, contained builder and independent reviewer
      processes, canonical gate, policy, files, and bare remote. Run the minimal real LangGraph
      adapter with its local restricted checkpointer. Bind every station receipt and RJ1 observation
      to exact subjects. Remove a required installed asset and require failure rather than host
      fallback. Falsifier: Fall back to repository executor.py after omitting it from the installed
      pack; slice/installed-provenance must detect execution outside the installed artifact.
    falsified_by: >
      Fall back to repository executor.py after omitting it from the installed pack;
      slice/installed-provenance must detect execution outside the installed artifact.
  - id: AC2
    text: >
      Claim: The same installed slice leaves both trunk refs unchanged after a real red gate or
      rejected approval, including direct executor and review entry attempts. Set: RJ2 through
      installed Executor.run, Dispatcher._dispatch_review, GitLandOps.gate/finalize, separate
      reviewer assignment, and real signed approval fixtures consumed by installed policy.
      Completeness: Enumerate normal, direct build, and direct review entries; drive each with a
      failing candidate test and a rejected protected-path approval. Also try builder-as-reviewer
      and a later passing assertion with an unresolved objection. Record actual processes,
      candidate/proof bytes, policy result, local and remote refs. SIGKILL during the rejecting
      stage and rerun recovery; no path may grant completion or alter either trunk. Falsifier:
      Advance local trunk before candidate policy rejects approval;
      slice/rejected-approval-isolation must detect changed refs through the direct review journey.
    falsified_by: >
      Advance local trunk before candidate policy rejects approval;
      slice/rejected-approval-isolation must detect changed refs through the direct review journey.
  - id: AC3
    text: >
      Claim: Dependency or authority regression refuses execution and publication through every
      installed floor entry while B spend and containment protections remain active. Set: RJ3 across
      WorkLoop._still_claimable, Executor.run, Dispatcher._dispatch_review, and GitLandOps.finalize
      using real signed revocation/dependency commands and separate contained fake-model processes.
      Completeness: Derive entry/prerequisite coverage from W37 registrations. Change a dependency
      or authority after selection, before review, and before publication; race requests for one
      remaining reservation, withhold delayed usage, and verify hard memory, cumulative CPU-time,
      writable-byte and inode limits. SIGSTOP the checkpoint writer in a real write transaction and
      require independent holder cancellation and committed revocation within B bounds. Observe no
      denied provider request, stale launch/publication, or premature slot release; source-only
      fixtures cannot replace these installed operations. Falsifier: Cache publication eligibility
      before the real revocation commits and resume the lander afterward;
      slice/revocation-before-publication must detect the remote ref update.
    falsified_by: >
      Cache publication eligibility before the real revocation commits and resume the lander
      afterward; slice/revocation-before-publication must detect the remote ref update.
  - id: AC4
    text: >
      Claim: Restart after a lost landing acknowledgment reconciles the original exact candidate
      without second publication, and RJ1-RJ4 remain executable registered regression obligations.
      Set: RJ4 through installed GitLandOps.finalize, B recovery commands, real remote receive
      records, journal replica, and local LangGraph checkpoint state, with W40 regression
      consumption. Completeness: SIGKILL after remote ref acceptance before authority
      acknowledgment, delete graph checkpoints, restart the installed authority/adapter, and query
      remote commit and ancestry. Require one source publication attempt, recovered signed landing
      receipt/spec.shipped, and no completion from unknown or divergent observations. Compare active
      RJ1-RJ4 plan declarations to executable suite registration and observed
      candidate/environment-bound receipts; omit one journey result and require release refusal.
      Falsifier: Allocate a fresh landing dispatch after checkpoint deletion following accepted
      remote publication; slice/lost-ack-no-repeat must detect the second receive attempt.
    falsified_by: >
      Allocate a fresh landing dispatch after checkpoint deletion following accepted remote
      publication; slice/lost-ack-no-repeat must detect the second receive attempt.
required_evidence: [unit, integration, journeys]
rollback: >
  Keep project coordination and live worker activation disabled, preserve failed slice artifacts and
  unresolved effects, and restore only compatible installed components after reconciliation.
---

## Intent

Prove the repaired floor as an installed system before production workers, channels, or project coordination depend on it.

## Context

Package C, W44 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A and B contracts govern this repair. This is a draft, not implementation or activation authority.

R35, R43-R45, R51, R53, R58, and R76 define the first real engineering delivery slice. Incomplete integration could hide authorization or publication failures behind successful component tests. The declared risk floor is critical; required approval must bind the eventual change and proof and is not recorded by this declaration.

## Out of scope

Production engine qualification is D, real presentation/attribution/settlement and interrupted decision proof is E, project-manager behavior is G, and every-pack operational qualification is H.

## Notes

D1-D4 block this slice until Dmitry ratifies the store/replica, off-host acknowledgment, Linux systemd/cgroup runner, and isolated clones/cache respectively, and the A/B implementations qualify them. Declare the reference pack and qualified host before ready; H expands to every pack and operational recovery. Unavailable systemd, isolation, or resource limits is blocked qualification, never a mocked pass. Wire installed deterministic services and fake model bytes only; do not inject fake LoopSteps, LandOps, stores, signing, policy, or gates. Use real command signatures that bind full parameters, enforce request maxima before local fake-provider calls, and retain conservative exposure. Fixtures test policy consumption only and certify no live decision channel. Register RJ1-RJ4 in the plan when executable checks exist, preserving their activation. Save applied mutation diffs, named failing rows, process observations, and pre/post Git refs. New slice assets need W30 inventory/scaffolder coverage and byte-identical composition; resolve proposed control_floor_slice placement before ready.
