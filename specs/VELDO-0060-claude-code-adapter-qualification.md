---
schema: veldo.spec/v1
id: VELDO-0060
title: Claude Code production adapter qualification
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W45
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
  - "engine/.veldo/control_engine_claude*.py"
  - ".veldo/control_engine_claude*.py"
  - "packs/*/.veldo/control_engine_claude*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/runtime/claude-qualification*.json"
  - ".veldo/runtime/claude-qualification*.json"
  - "packs/*/runtime/claude-qualification*.json"
  - "scripts/suites/*_veldo_0060_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0060-claude-code-adapter-qualification.md"
  - "specs/index.md"
  - "proof/VELDO-0060/*"
behavior_bearing: true
observability:
  logs: >
    Claude qualification records executable digest, installed version, host/helper profile,
    dispatch identity, invocation contract, and actual acceptance and exit observations.
  metrics: >
    Measure Claude launches per dispatch, observed provider charges, malformed terminal streams,
    stop latency, and unresolved invocations for each qualified profile.
  traces: >
    Join the installed Claude binary and explicit input digests to B launch intent, containment
    identity, streamed artifacts, usage allocation, and retirement receipt.
  error_taxonomy: >
    Distinguish unsupported Claude version, mismatched executable, unsafe authentication profile,
    missing terminal output, malformed usage, and uncertain recovery.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The Claude Code adapter fulfills every R42 operation through B durable runner
      acceptance with explicit accepted inputs and tool permissions. Set:
      fleet.WorkerSpawner.spawn/retire and the enrolled replacement for fleet.in_session_start,
      using actual Claude Code executables on every advertised version and host/helper profile.
      Completeness: Freeze the supported matrix from installed adapter registrations before
      qualification; compare every R42 operation to executable rows. Run version validation,
      launch, acceptance/process identity, observation streaming, cooperative stop, exit, recovery
      query, and artifact return using real processes, SQLite, signatures, and contained clones.
      Alter the executable after qualification and require pre-launch refusal. Falsifier: Skip
      executable digest verification after replacing the qualified Claude executable;
      claude/executable-binding must detect an unauthorized launch.
    falsified_by: >
      Skip executable digest verification after replacing the qualified Claude executable;
      claude/executable-binding must detect an unauthorized launch.
  - id: AC2
    text: >
      Claim: Claude terminal output becomes observed artifacts for independent validation, and
      zero exit never establishes completed work. Set: Actual Claude normal exit, nonzero exit,
      signal exit, truncated stream, absent terminal record, malformed output, and missing or
      malformed usage at the production decoder and WorkerSpawner result boundary. Completeness:
      Enumerate accepted output/usage variants from each recorded binary version. Capture real
      live streams and apply byte-level faults at the transport boundary, retaining originals and
      fault diffs. Drive the same parser and independent artifact validator as production, inspect
      authority state, and retain unknown cost exposure under B reservations when usage is
      missing. Falsifier: Treat a zero Claude exit with its terminal record removed as artifact
      acceptance; claude/missing-terminal must reject that result.
    falsified_by: >
      Treat a zero Claude exit with its terminal record removed as artifact acceptance;
      claude/missing-terminal must reject that result.
  - id: AC3
    text: >
      Claim: A retried Claude dispatch observes the original invocation or records uncertainty
      without launching another process. Set: The production spawn and recovery paths reached from
      fleet.WorkerSpawner.spawn, B launch records, real Claude descendants, receiver acceptance,
      and output persistence. Completeness: Kill the trusted adapter before and after spawn and
      before terminal receipt commit, then redeliver the original dispatch from another client.
      Correlate boot/start identity, cgroup census, durable acceptance, and actual charges;
      exercise orphan recovery, PID identity mismatch, hangs, and missing accounting. Require one
      invocation or a fenced AWAITING_AUTHORITY with retained exposure, never inference from
      silence. Falsifier: Relaunch Claude from an ambiguous launch-intent record after killing the
      adapter just after spawn; claude/ambiguous-launch must detect a second invocation.
    falsified_by: >
      Relaunch Claude from an ambiguous launch-intent record after killing the adapter just after
      spawn; claude/ambiguous-launch must detect a second invocation.
  - id: AC4
    text: >
      Claim: A live Claude invocation stays inside B credential, spend, and containment boundaries
      during tool execution and cancellation. Set: Qualified Claude profiles through
      fleet.InSessionSpawner._assemble_env/spawn/retire replacements, with real tool descendants
      and initial, retry, and follow-on billable calls. Completeness: Inspect OS access refusals
      for reusable account profiles and authority files; enforce the B maximum-charge allocation
      before each request and hard aggregate memory, descendant CPU-time, storage-byte and inode
      limits before launch. Run actual signals and a hostile tool that forks and creates a
      session; retain costs and quarantine until empty containment, outcome, accounting, and
      cleanup are proven. Profiles unable to enforce these boundaries remain disabled. Falsifier:
      Pass a reusable account profile into the Claude tool environment;
      claude/tool-credential-access must detect the forbidden read from a real tool child.
    falsified_by: >
      Pass a reusable account profile into the Claude tool environment;
      claude/tool-credential-access must detect the forbidden read from a real tool child.
required_evidence: [unit, integration]
rollback: >
  Disable the affected Claude profile, stop or quarantine its invocations, retain usage and launch
  records, and restore only a previously qualified compatible adapter.
---

## Intent

Qualify an installed Claude Code adapter against the existing runner contract using observed execution and costs.

## Context

Package D, W45 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A/B/C contracts govern implementation. This draft grants no implementation or activation authority.

R42-R45 and R59 require a real production adapter. The baseline fleet start is an in-session refusing seam, and its environment builder exposes an account profile. Unsafe replacement could expose credentials or launch ungoverned work. The declared risk floor is critical; required approval must bind the eventual change and proof. This declaration records no approval.

## Out of scope

Codex qualification, new neutral supervision machinery, and activation of production workers are separate work.

## Notes

D1 and D2 block inherited durable launch and acknowledgment; D3 blocks the production host profile, and D4 blocks isolated-clone provisioning until Dmitry rules. Resolve control_engine_claude paths and architecture mapping before ready, and inventory code and qualification profile assets through W30 with byte-identical engine copies. Record exact binary, invocation flags, terminal schema, pricing evidence, supported matrix, and finite qualification budget; no binary or safe authentication mode is presumed available. W47 owns shared provider-accounting qualification and W48 the combined governor failure matrix; this adapter must consume their underlying B predicates from its first live call. Retain each applied mutation diff and named failing row, then revert it. No fake provider or fixture cost certifies Claude.
