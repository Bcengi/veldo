---
schema: veldo.spec/v1
id: VELDO-0129
title: Real worker adapter wiring for LiveLoop and LiveReviewer
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W92
plan_revision: 4
depends_on: [VELDO-0049, VELDO-0050, VELDO-0060, VELDO-0061]
placement: [loop, fleet]
protected_paths: []
footprint:
  - "engine/.veldo/executor.py"
  - ".veldo/executor.py"
  - "packs/*/.veldo/executor.py"
  - "engine/.veldo/dispatch.py"
  - ".veldo/dispatch.py"
  - "packs/*/.veldo/dispatch.py"
  - "engine/.veldo/control_engine*.py"
  - ".veldo/control_engine*.py"
  - "packs/*/.veldo/control_engine*.py"
  - "scripts/suites/*_veldo_0129_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0129-live-build-review-adapter-wiring.md"
  - "specs/index.md"
  - "proof/VELDO-0129/*"
behavior_bearing: true
observability:
  logs: >
    Record operation, domain/repository, actor or role, input/configuration versions,
    resulting record identity and named refusal; exclude secrets.
  metrics: >
    Count accepted/refused operations and pending work, with bounded run duration and
    charge attribution where this concern uses a worker.
  traces: >
    Correlate input request, configuration/host, dispatched work and resulting authority evidence.
  error_taxonomy: >
    Distinguish unauthenticated, unauthorized, stale version, unsupported configuration,
    unavailable service, missing evidence and unknown outcome; none is successful completion.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The installed LiveLoop.build dispatches the selected real adapter and returns bound
      implementation/evidence artifacts. Set and completeness: Install the reference distribution
      and invoke LiveLoop.build for the chosen Claude Code and Codex configurations without a
      caller-injected build callable; observe actual process invocation in an accepted isolated
      clone and compare returned commit/proof references to the dispatch. Missing configuration must
      refuse before launch. Falsifier: Leave production build dependent on an injected callable; the
      installed default-build journey must fail.
    falsified_by: >
      Leave production build dependent on an injected callable; the installed default-build journey
      must fail.
  - id: AC2
    text: >
      Claim: Both LiveLoop.review and LiveReviewer.review dispatch a fresh independent reviewer
      through the selected real adapter. Set and completeness: For each entry point and both
      configured engines, supply the exact spec, source/diff and proof in fresh context without the
      builder conversation; inspect real reviewer process, distinct eligible identity and subject-
      bound findings/verdict. Apply current policy review count and forbid self-review. Falsifier:
      Reuse the builder context for review; the fresh-context independence observation must fail.
    falsified_by: >
      Reuse the builder context for review; the fresh-context independence observation must fail.
  - id: AC3
    text: >
      Claim: Adapter outcomes feed the authoritative proof/review transition path without
      manufacturing success. Set and completeness: Exercise valid results, nonzero exit, missing
      artifact, malformed review and missing usage through the installed wiring; inspect accepted
      evidence or named refusal, retained charge exposure and no source completion from process exit
      alone. Every build/review call uses the existing pre-call reservation boundary. Falsifier:
      Convert adapter exit zero to passing review without a verdict artifact; the missing-review
      refusal check must fail.
    falsified_by: >
      Convert adapter exit zero to passing review without a verdict artifact; the missing-review
      refusal check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern while preserving accepted records, configuration
  revisions and unresolved work. No automatic rollback, retry or recovery is authorized.
---

## Intent

Installed construction and independent review call the real qualified Claude Code and Codex
adapters instead of stopping at the unimplemented model seams.

## Context

W92 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its 2026-09-22
scope amendments. This new specification is draft; authoring it supplies neither implementation
proof nor operational activation. Implementation still requires readiness and applicable approval.

## Out of scope

Automatic recovery, durability/scale qualification and additional host/channel types beyond
this declared concern. These belong to later releases as assigned by the plan. No existing
specification status, implementation, test, runtime policy or deployed service changes in this draft.

## Notes

Inspected at the revision-3 baseline: LiveLoop.build and LiveLoop.review in .veldo/executor.py
and LiveReviewer.review in .veldo/dispatch.py refuse without injected implementations. Engine
qualification alone does not connect these entry points. This concern wires the production
default; it does not relax their refusal when no qualified configuration exists.

Handed on by VELDO-0050 (its review, 2026-09-24): the proof service (.veldo/control_proof.py) is
built but no production path wires one yet, so the dispatcher's default LiveLoop stops every floor
build at proof with missing_authority:proof_service. This concern wires a ProofService into the
dispatcher's LiveLoop; makes the floor's accept_build in .veldo/dispatch.py resolve the stored
bundle rather than the committed manifest alone; makes the executor refuse, with the floor
enabled, a hook set whose accept_proof returns nothing; and has the real build adapter's proof
carry spec_revision and evidence entries that name a path and a digest.

Handed on by VELDO-0067 (its review, 2026-09-24): each production local adapter's configured argv
starts with the key custody wrapper (control_keys_custody.confined, naming the protected key
directory), so a worker cannot read an edge key file directly.

Handed on by VELDO-0042 (its reviews, 2026-09-24): the launch path calls control_clone's
record_group with the worker's VELDO-0040 group before the engine runs, and uses a new dispatch id
for every launch, because a clone whose entrance has no recorded group, or was relaunched under the
same dispatch in a second group, stays in use until the host reboots. Any unconfined Git run over a
used clone (collecting a result) treats that clone's .git/config as hostile, since a worker can write
hooks or core.fsmonitor there.

Use canonical engine assets and synchronize installed copies. Resolve the proposed footprint's
architecture mapping before ready, including the new UI assets where applicable; this draft does
not amend the architecture contract. Inventory every asset the selected journey installs. Compare
executable registrations to each criterion's declared universe, observe the real named interfaces,
and retain the driven negative-control diff and named failed row. Fixtures cannot certify real
platform, engine or host behavior. Required evidence labels describe future implementation proof,
not tests run by this writing revision.

## History

2026-09-22: new draft for PLAN-0019 revision 3, Release 1 stage 1, under the owner's
complete-factory MVP decisions. Simple function and its meaningful refusal checks are in this
release; recovery and robustness are Release 2, governance depth Release 3, broader hosts/channels,
installation, adoption, migration and rollback Release 4.
