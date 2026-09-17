---
schema: veldo.spec/v1
id: VELDO-0045
title: Pinned isolated runtime, dependency licenses, and distribution inventory
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W30
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0043, VELDO-0044]
placement: [distribution, enforcement, loop]
protected_paths: [scripts/verify.sh, engine/scripts/verify.sh]
footprint:
  - "engine/.veldo/pack.py"
  - ".veldo/pack.py"
  - "packs/*/.veldo/pack.py"
  - "engine/.veldo/pack_conformance.py"
  - ".veldo/pack_conformance.py"
  - "packs/*/.veldo/pack_conformance.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/control_runtime*.py"
  - ".veldo/control_runtime*.py"
  - "packs/*/.veldo/control_runtime*.py"
  - "engine/runtime/*"
  - ".veldo/runtime/*"
  - "packs/*/runtime/*"
  - ".veldo/packs.json"
  - "scripts/check_install_and_run.py"
  - "scripts/check_pack_drift.py"
  - "scripts/check_template_sync.sh"
  - "scripts/verify.sh"
  - "engine/scripts/verify.sh"
  - "packs/*/scripts/verify.sh"
  - "scripts/suites/*_veldo_0045_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0045-isolated-runtime-distribution.md"
  - "specs/index.md"
  - "proof/VELDO-0045/*"
behavior_bearing: true
observability:
  logs: >
    Installer output identifies runtime lock digest, Python compatibility, artifact hash
    verification, license disposition, and active environment.
  metrics: >
    Report locked versus installed dependency closure, inventoried versus composed assets, missing
    scaffold files, and refused partial installs.
  traces: >
    Join dependency resolution and hashes to isolated installation, composed pack digests,
    installed adapter execution, and stdlib-only gate observations.
  error_taxonomy: >
    Distinguish unsupported Python, hash mismatch, incomplete lock, missing license, undistributed
    asset, partial installation, and enforcement dependency leak.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The installer uses a complete transitive lock with hashes and license records for a
      tested Python, LangGraph, and SQLite-checkpoint combination in an isolated environment. Set:
      Every runtime distribution and supported Python profile, installed by real package tooling
      into fresh temporary environments. Completeness: Compare installed dependency metadata to
      the lock and license inventory in both directions; execute the actual adapter/checkpointer
      smoke workload. Corrupt a downloaded artifact hash, omit a transitive dependency, and
      SIGKILL installation before activation; incompatible or partial environments must never
      become active. Falsifier: Bypass locked-hash enforcement and install an otherwise valid
      altered wheel while retaining the original lock; runtime/hash-refusal must reject
      installation before activation.
    falsified_by: >
      Bypass locked-hash enforcement and install an otherwise valid altered wheel while retaining
      the original lock; runtime/hash-refusal must reject installation before activation.
  - id: AC2
    text: >
      Claim: The engine manifest, assembly, scaffolder, and explicit distribution inventory
      account for every new code and non-code asset and preserve byte-identical engine copies.
      Set: All PLAN-0019 foundation modules, runtime locks, dependency license material,
      service/helper assets, and composed packs declared in .veldo/packs.json. Completeness:
      Compare tracked canonical assets, declared dispositions, pack.engine_files, and
      init_scaffold output in both directions. Compose real packs, install each declared asset
      set, and run the installed runtime smoke workload; intentionally omit a non-code lock or
      service asset and require a named packaging failure. Falsifier: Omit the runtime lock from
      one pack composition while leaving engine Python files identical; runtime/inventory-omission
      must detect the missing installed asset.
    falsified_by: >
      Omit the runtime lock from one pack composition while leaving engine Python files identical;
      runtime/inventory-omission must detect the missing installed asset.
  - id: AC3
    text: >
      Claim: Validators, authorization, gate imports, journal replay, and recovery run using only
      stdlib Python when the execution environment is unavailable. Set: Fresh installed-artifact
      enforcement processes and a populated signed authority fixture, with runtime environment
      removed from import and executable paths. Completeness: Enumerate enforcement entry points
      from installed inventory, run their real commands and canonical gate, and exercise replay
      and recovery with a valid and corrupted journal. Require graph execution to report runtime
      unavailable without weakening independent enforcement checks. Falsifier: Add an execution
      dependency import to installed authorization and remove the isolated environment;
      runtime/enforcement-isolation must fail the real authorization command.
    falsified_by: >
      Add an execution dependency import to installed authorization and remove the isolated
      environment; runtime/enforcement-isolation must fail the real authorization command.
required_evidence: [unit, integration]
rollback: >
  Keep the previous compatible runtime and lock installable; leave an interrupted new environment
  inactive and switch back only with schema compatibility and a recorded activation receipt.
---

## Intent

Install a pinned isolated execution runtime and account for every shipped asset while keeping enforcement independent of it.

## Context

Package B, W30 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R35, R50, R53, R57-R58, R63. Package A contracts must be accepted before implementation; this draft grants no implementation or activation authority.

Unverified dependencies or omitted assets could compromise installed execution, and this footprint includes protected gate scripts. The declared risk floor is high. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

No live engine certification, release activation, or claim that source-tree tests qualify every installed journey is made.

## Notes

D1 is inherited from the adapter/checkpoint placement; D3 remains a blocker for activating packaged service and helper assets. Exact versions and licenses are findings of compatibility qualification, not assumptions in this draft. Protected gate edits may update honest dependency and license check declarations, but must not weaken checks or import third-party runtime packages into enforcement. B supplies installed smoke proof; C and H own the full floor-slice and release qualification.

