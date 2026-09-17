---
schema: veldo.spec/v1
id: VELDO-0049
title: Dispatch and tracker bridge consume authoritative state transitions
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W34
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048]
placement: [fleet, tracker, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/dispatch.py"
  - ".veldo/dispatch.py"
  - "packs/*/.veldo/dispatch.py"
  - "engine/.veldo/tracker_bridge.py"
  - ".veldo/tracker_bridge.py"
  - "packs/*/.veldo/tracker_bridge.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0049_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0049-authoritative-floor-transitions.md"
  - "specs/index.md"
  - "proof/VELDO-0049/*"
behavior_bearing: true
observability:
  logs: >
    Transition diagnostics name unit, station, expected version, command ID, and published
    watermark.
  metrics: >
    Count refused local status writes, pending handoffs, duplicate transition submissions, and
    review objections awaiting disposition.
  traces: >
    Join dispatcher result and tracker proposal to their signed command, accepted artifact,
    assignment, and materialized projection.
  error_taxonomy: >
    Distinguish unadmitted proposal, stale transition, proof not durable, independence failure,
    unresolved objection, and authority unavailable.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Dispatcher._dispatch_build and Dispatcher._set_status use authoritative transitions;
      only the materializer writes enrolled status projections after durable proof acceptance. Set:
      Real dispatch.py processes over an admitted specification, proof files, and
      <git-common-dir>/veldo/control/control.sqlite3, including build success, red gate, and invalid
      proof. Completeness: Enumerate status-writing call sites in dispatch.py and drive each through
      real gate and filesystem operations. SIGKILL after transition commit before projection,
      restart, and compare stored versions and published files; race identical build completions and
      require one review handoff. Falsifier: Restore the direct _set_status file write and kill
      dispatch before the authority transition; transitions/build-handoff must detect a review
      projection without its committed acceptance.
    falsified_by: >
      Restore the direct _set_status file write and kill dispatch before the authority transition;
      transitions/build-handoff must detect a review projection without its committed acceptance.
  - id: AC2
    text: >
      Claim: Dispatcher._dispatch_review and _verdict_passes consume trusted independent review
      receipts and explicit finding dispositions; a passing verdict alone cannot ship or erase an
      objection. Set: Separate real builder and reviewer processes with fixture model output, signed
      actor/assignment records, proof digests, and a real lander against a bare remote.
      Completeness: Exercise builder-as-reviewer, changed source or proof, missing review receipt,
      unresolved blocking finding followed by pass, rejected approval, and valid independent review.
      Compare authority receipts and both trunk refs before and after every attempt; review failure
      requests an authorized retry transition rather than rewriting ready. Falsifier: Let
      _verdict_passes accept a later pass while a prior blocking finding remains unresolved;
      transitions/review-objection must detect attempted publication.
    falsified_by: >
      Let _verdict_passes accept a later pass while a prior blocking finding remains unresolved;
      transitions/review-objection must detect attempted publication.
  - id: AC3
    text: >
      Claim: tracker_bridge.reconcile_promotions and FilesystemSpecStore._promote_spec cannot turn
      tracker status into enrolled admission or priority; drafting submits idempotent proposals
      through B allocation and publication. Set: reconcile_drafts, SpecStore.promote_spec,
      FilesystemSpecStore._allocate_spec_id and _write_spec, and direct promotion calls using real
      proposal files and authority clients. Completeness: Discover all bridge filesystem writers;
      race two bridge clients for one source revision and kill after alias reservation before
      materialization. Recorded input files exercise status-only, accepted current admission, stale
      signed command parameters, and absent authority. Query real SQLite, specs bytes, and source
      mapping for zero unauthorized readiness and one allocated alias. No live channel is activated.
      Falsifier: Allow _promote_spec to flip a draft when only the recorded tracker status is ready;
      transitions/tracker-status-only must detect readiness without stored admission and priority.
    falsified_by: >
      Allow _promote_spec to flip a draft when only the recorded tracker status is ready;
      transitions/tracker-status-only must detect readiness without stored admission and priority.
required_evidence: [unit, integration]
rollback: >
  Stop affected enrolled entries, preserve signed history and pending obligations, and restore the
  prior compatible consumer only after current authorization is revalidated.
---

## Intent

Make dispatch and tracker intake consume one authoritative lifecycle instead of creating readiness and completion by editing Markdown.

## Context

Package C, W34 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A and B contracts govern this repair. This is a draft, not implementation or activation authority.

R11, R31, R46, R51, R54, and R70 drive the repair. Direct file writes and verdict-only shipping can bypass admission and publication authority. The declared risk floor is critical; required approval must bind the eventual change and proof and is not recorded by this declaration.

## Out of scope

Live tracker mutations, channel settlement, project admission workflows, and production model qualification remain E, F, and D work.

## Notes

D1 and D2 block the inherited store and published transition boundary; D3 and D4 block the real runner and isolated-clone qualification used by dispatch. All four remain prerequisites through the A/B barrier. At the inspected baseline tracker_bridge.py exists only in .veldo/, so establish its canonical engine copy and explicit distribution/scaffolder disposition under W30 before installed use. Retain explicit unenrolled compatibility without allowing enrolled fallback. Proof must retain each applied falsifier diff and its failing named row, then revert it. Source-channel fixtures test consumption only; E owns presentation, attribution, settlement, and channel activation.
