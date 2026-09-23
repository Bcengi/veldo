---
schema: veldo.spec/v1
id: VELDO-0124
title: Simple macOS worker lifecycle profile
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W87
plan_revision: 3
depends_on: [VELDO-0039, VELDO-0041, VELDO-0042, VELDO-0062]
placement: [project_runner, fleet]
protected_paths: []
footprint:
  - "engine/.veldo/project_runner_macos*.py"
  - ".veldo/project_runner_macos*.py"
  - "packs/*/.veldo/project_runner_macos*.py"
  - "engine/.veldo/control_host*.py"
  - ".veldo/control_host*.py"
  - "packs/*/.veldo/control_host*.py"
  - "scripts/suites/*_veldo_0124_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0124-macos-worker-profile.md"
  - "specs/index.md"
  - "proof/VELDO-0124/*"
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
      Claim: The Mac profile launches a trusted wrapper and isolated worker group under the accepted
      dispatch contract without cgroups. Set and completeness: On the actual selected Mac launch
      both qualified Claude Code and Codex configurations with an accepted clone and explicit
      engine/configuration identity; observe real worker/descendant identity and no write access to
      authority keys or store. Missing profile qualification refuses before launch. Falsifier: Mark
      an unqualified Mac profile eligible; the pre-launch qualification check must fail.
    falsified_by: >
      Mark an unqualified Mac profile eligible; the pre-launch qualification check must fail.
  - id: AC2
    text: >
      Claim: Configured concurrency and elapsed-runtime caps are enforced by the Mac supervisor. Set
      and completeness: Declare finite max_workers, per-dispatch elapsed deadline and stop
      escalation bounds in versioned profile data; attempt one worker beyond capacity and a real
      worker exceeding its deadline. Observe refused excess launch and terminated overdue worker.
      Every provider call still uses 0036/0062 pre-call spend caps. Falsifier: Ignore the elapsed
      deadline; the bounded-runtime observation must fail.
    falsified_by: >
      Ignore the elapsed deadline; the bounded-runtime observation must fail.
  - id: AC3
    text: >
      Claim: Stop and OS exit detection cover the wrapper and its ordinary descendants before slot
      retirement. Set and completeness: Exercise natural exit, cooperative stop and a signal-
      ignoring child for both engine configurations; observe OS exit notifications, bounded
      termination escalation and no live descendant before release. A lost or ambiguous outcome
      stays stopped and retains unknown charge exposure. Falsifier: Report retired after only the
      parent exits; the surviving-child observation must fail.
    falsified_by: >
      Report retired after only the parent exits; the surviving-child observation must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern while preserving accepted records, configuration
  revisions and unresolved work. No automatic rollback, retry or recovery is authorized.
---

## Intent

Run real autonomous workers on the Mac, with a small qualified lifecycle contract that does
not depend on Linux cgroups.

## Context

W87 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 2.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its 2026-09-22
scope amendments. This new specification is draft; authoring it supplies neither implementation
proof nor operational activation. Implementation still requires readiness and applicable approval.

## Out of scope

Automatic recovery, durability/scale qualification and additional host/channel types beyond
this declared concern. These belong to later releases as assigned by the plan. No existing
specification status, implementation, test, runtime policy or deployed service changes in this draft.

## Notes

Owner Telegram 28852 requires the Mac in Release 1 because iOS builds require macOS. Linux
remains the authority. This concern is the host profile, not remote transport or routing.
Declare the actual Mac/macOS version and supported Claude Code/Codex configurations before
ready; do not claim they were qualified by this draft. Aggregate descendant resource-
exhaustion, escape, PID-reuse and machine-loss recovery matrices belong to Release 2.

Use canonical engine assets and synchronize installed copies. Resolve the proposed footprint's
architecture mapping before ready, including the new UI assets where applicable; this draft does
not amend the architecture contract. Inventory every asset the selected journey installs. Compare
executable registrations to each criterion's declared universe, observe the real named interfaces,
and retain the driven negative-control diff and named failed row. Fixtures cannot certify real
platform, engine or host behavior. Required evidence labels describe future implementation proof,
not tests run by this writing revision.

## History

2026-09-22: new draft for PLAN-0019 revision 3, Release 1 stage 2, under the owner's
complete-factory MVP decisions. Simple function and its meaningful refusal checks are in this
release; recovery and robustness are Release 2, governance depth Release 3, broader hosts/channels,
installation, adoption, migration and rollback Release 4.
