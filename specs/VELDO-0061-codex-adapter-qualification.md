---
schema: veldo.spec/v1
id: VELDO-0061
title: Codex production adapter qualification
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W46
plan_revision: 1
depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059]
placement: [fleet, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/fleet.py"
  - ".veldo/fleet.py"
  - "packs/*/.veldo/fleet.py"
  - "engine/.veldo/control_runner*.py"
  - ".veldo/control_runner*.py"
  - "packs/*/.veldo/control_runner*.py"
  - "engine/.veldo/control_engine_codex*.py"
  - ".veldo/control_engine_codex*.py"
  - "packs/*/.veldo/control_engine_codex*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/runtime/codex-qualification*.json"
  - ".veldo/runtime/codex-qualification*.json"
  - "packs/*/runtime/codex-qualification*.json"
  - "scripts/suites/*_veldo_0061_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0061-codex-adapter-qualification.md"
  - "specs/index.md"
  - "proof/VELDO-0061/*"
behavior_bearing: true
observability:
  logs: >
    Codex adapter diagnostics identify binary/version, invocation and sandbox contracts, stream
    sequence, recovery finding, and refused capability.
  metrics: >
    Count accepted Codex dispatches, duplicate delivery queries, retained usage exposure, signal
    outcomes, and escaped-descendant attempts by supported profile.
  traces: >
    Trace a Codex dispatch from replicated preparation through durable receiver acceptance to
    actual process identity, output artifacts, costs, and terminal reconciliation.
  error_taxonomy: >
    Distinguish unsupported Codex protocol, missing terminal event, ambiguous spawn, unbounded
    request charge, credential separation failure, and stale generation.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The Codex production adapter implements the same R42 lifecycle as Claude without
      adding a second launch authority. Set: fleet.WorkerSpawner.spawn/retire and B runner
      registrations for every supported Codex executable version and host/helper profile.
      Completeness: Declare the supported matrix from installed manifests and compare it against
      all lifecycle rows. Invoke actual binaries with explicit accepted source/input digests and
      tool permissions, observing version validation, acceptance, boot/start identity, output
      streaming, stop, exit, recovery query, and artifact return. Unknown versions and changed
      binary digests refuse before spawn. Falsifier: Accept an unregistered Codex version at
      production launch; codex/version-refusal must observe the unexpected child.
    falsified_by: >
      Accept an unregistered Codex version at production launch; codex/version-refusal must
      observe the unexpected child.
  - id: AC2
    text: >
      Claim: The Codex decoder fails explicitly on unsupported output and usage and never converts
      process success into specification completion. Set: Real Codex terminal/stream variants,
      normal and signal exits, nonzero exits, output truncation, missing terminal records, and
      malformed or absent usage through the production result path. Completeness: Capture live
      output for every supported binary; derive parser variant coverage from the decoder
      registrations and perturb captured bytes at real transport boundaries. Read result artifacts
      in an independent validator process, compare journal facts, and preserve conservative charge
      exposure on unknown usage. A valid exit yields only the facts independently established.
      Falsifier: Map an absent usage record to zero charge on a successful Codex exit;
      codex/unknown-usage must catch released exposure or an unsupported zero-cost receipt.
    falsified_by: >
      Map an absent usage record to zero charge on a successful Codex exit; codex/unknown-usage
      must catch released exposure or an unsupported zero-cost receipt.
  - id: AC3
    text: >
      Claim: Codex recovery reuses durable dispatch identity and closes stale permissions despite
      suspended or orphaned processes. Set: Production spawn/recovery and retire calls through
      fleet.WorkerSpawner, B receiver records and real Codex process groups, with scope change and
      revocation during execution. Completeness: SIGKILL the adapter around launch and acceptance
      acknowledgment; SIGSTOP and resume the old engine across authority-generation replacement.
      Query actual containment and target acceptance with both current and stale handles,
      requiring one logical dispatch and no stale protected effect. Missing conclusive evidence
      retains AWAITING_AUTHORITY and its reservation. Falsifier: Accept an old Codex capability
      after generation replacement when the suspended process resumes; codex/resumed-stale-worker
      must detect the target operation.
    falsified_by: >
      Accept an old Codex capability after generation replacement when the suspended process
      resumes; codex/resumed-stale-worker must detect the target operation.
  - id: AC4
    text: >
      Claim: Codex tool processes cannot escape qualified containment or acquire reusable provider
      authentication, and every billable call fits an enforced maximum. Set: The enrolled
      replacements for fleet.InSessionSpawner._assemble_env/spawn and
      WorktreeInSessionStart.__call__, with Codex sandbox tools, retries, follow-on requests, and
      B reservation/credential boundaries. Completeness: Run real tool descendants that attempt
      session escape, authority/cache writes, inherited credential reads, and limit changes.
      Inspect installed aggregate memory, cumulative descendant CPU-time, writable-byte and inode
      bounds. Record provider call boundaries, pricing and hard-limit evidence, observed costs,
      and pre-call allocations; an unseparable auth mode or unenforceable maximum refuses
      qualification. Falsifier: Allow a Codex retry to enter the provider without allocating its
      maximum charge; codex/retry-charge-bound must detect a call exceeding the retained
      remainder.
    falsified_by: >
      Allow a Codex retry to enter the provider without allocating its maximum charge;
      codex/retry-charge-bound must detect a call exceeding the retained remainder.
required_evidence: [unit, integration]
rollback: >
  Remove eligibility for the affected Codex profile, fence its handles, reconcile live invocations
  and cost exposure, and retain the previous qualified adapter.
---

## Intent

Qualify Codex with the same durable lifecycle, isolation, and accounting obligations as every production worker.

## Context

Package D, W46 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A/B/C contracts govern implementation. This draft grants no implementation or activation authority.

R42-R45 and R59 prohibit certifying a binary from a claimed version or fake-provider result. Incorrect recovery or permissive tool credentials can preserve authority after fencing. The declared risk floor is critical; required approval must bind the eventual change and proof. This declaration records no approval.

## Out of scope

No new provider-neutral runner, Claude parser, project-manager graph, or production activation is included.

## Notes

D1/D2 block inherited storage and replicated dispatch, D3 blocks Linux systemd/cgroup activation, and D4 blocks worker clone/cache cutover until Dmitry rules. The guardian version is an input to verify, not a tested version. Record the actual executable digest, command arguments, terminal protocol, supported host matrix, and bounded live costs in proof. Proposed control_engine_codex modules require architecture mapping and W30 inventory before ready; synchronize canonical engine copies and qualification assets. Do not import an engine SDK into stdlib enforcement. W46 remains independent of W45 as the plan declares. Drive each mutation against the production adapter, save its diff and failed row, and restore the code before final qualification.
