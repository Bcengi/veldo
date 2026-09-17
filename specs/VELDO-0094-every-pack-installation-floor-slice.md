---
schema: veldo.spec/v1
id: VELDO-0094
title: Every-pack runtime installation and floor-slice qualification
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W79
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0088, VELDO-0089, VELDO-0090, VELDO-0091, VELDO-0092, VELDO-0093]
placement: [distribution, contracts, enforcement]
protected_paths: []
footprint:
  - "engine/.veldo/pack.py"
  - ".veldo/pack.py"
  - "packs/*/.veldo/pack.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/version.py"
  - ".veldo/version.py"
  - "packs/*/.veldo/version.py"
  - "engine/.veldo/control_runtime*.py"
  - ".veldo/control_runtime*.py"
  - "packs/*/.veldo/control_runtime*.py"
  - "engine/.veldo/control_install_journey*.py"
  - ".veldo/control_install_journey*.py"
  - "packs/*/.veldo/control_install_journey*.py"
  - "scripts/check_install_and_run.py"
  - "scripts/publish.py"
  - ".veldo/packs.json"
  - "engine/runtime/*"
  - ".veldo/runtime/*"
  - "packs/*/runtime/*"
  - "scripts/suites/*_veldo_0094_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0094-every-pack-installation-floor-slice.md"
  - "specs/index.md"
  - "proof/VELDO-0094/*"
behavior_bearing: true
observability:
  logs: >
    Installation qualification names composed pack, executed scaffolder/runtime paths and digests,
    inventory disposition, lock and install stamp.
  metrics: >
    Report declared/composed/installed/tested pack equality, missing assets, floor-slice receipts,
    actual gate scan reach and runtime-isolation failures.
  traces: >
    Trace publisher-selected tracked bytes through pack composition and scaffolder launch to
    installed floor completion and remote-tip evidence.
  error_taxonomy: >
    Distinguish composition omission, incomplete runtime, wrong launch origin, stale stamp,
    starter-only proof and unavailable enforcement import.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every composed pack contains and installs the declared runtime and complete
      distribution inventory. Set: pack.engine_files/assemble_pack/engine_drift,
      scripts/publish.py selected/compose_packs/build and
      init_scaffold.scaffold/required_substrate/missing_substrate. Completeness: Compare W30
      authoritative asset dispositions with tracked publisher selection, actual nonempty composed
      pack set and installed bytes/modes. Include code, locks, hashes, licenses, service/helper
      configuration and checkpoint assets. Reject missing or undeclared runtime files even when
      Python engine copies match. Drive wrapper shadowing and missing pack cases; omission cannot
      shrink the expected universe. Falsifier: Remove a runtime lock from one composed pack while
      leaving its engine Python files identical; install/inventory-closure must detect the missing
      installed asset.
    falsified_by: >
      Remove a runtime lock from one composed pack while leaving its engine Python files
      identical; install/inventory-closure must detect the missing installed asset.
  - id: AC2
    text: >
      Claim: Every composed pack runs the R58 floor slice from its installed artifact with
      measured executable provenance. Set: scripts/check_install_and_run.py
      compose/composed_packs/install_and_run/check/commit_tree/gate_substance and the installed C
      W44 slice entry point. Completeness: Require declared, composed, installed and exercised
      pack-set equality. Use actual completed-process launch paths and imported module locations
      with the source checkout unavailable. Commit each disposable adopter tree, then run admitted
      spec through real Git/files/SQLite/signing/locks/containment/gate/proof/independent
      review/policy/bare-remote landing; fake only model responses. Drive red gate, rejected
      approval, stale dependency/authority and lost landing acknowledgment; require exact
      remote-tip and completion receipts, not just starter green. Falsifier: Point the launched
      floor slice at source-tree modules while reporting the installed path;
      install/actual-launch-origin must detect source-only proof.
    falsified_by: >
      Point the launched floor slice at source-tree modules while reporting the installed path;
      install/actual-launch-origin must detect source-only proof.
  - id: AC3
    text: >
      Claim: Install provenance remains attributable across first install and repeated scaffolding
      without inventing a version. Set:
      init_scaffold._template_version/_version_in/_write_stamp/scaffold and
      version.read_declaration/installed_version/drift/drift_contradictions for
      .veldo/installed.json. Completeness: Exercise every composed manifest shape, first install,
      no-op rerun from a newer pack, absent/malformed/foreign manifest and preexisting stamp.
      Require declared Veldo version, create-only original stamp and visible
      unknown/unreadable/drift states. Bind separate W30 runtime/lock qualification provenance to
      measured bytes; a version string alone cannot certify installed compatibility. Falsifier:
      Overwrite the original install stamp during a no-op rerun from a newer pack;
      install/stamp-preservation must detect fabricated installation provenance.
    falsified_by: >
      Overwrite the original install stamp during a no-op rerun from a newer pack;
      install/stamp-preservation must detect fabricated installation provenance.
  - id: AC4
    text: >
      Claim: Installed enforcement and recovery remain usable without the execution runtime. Set:
      Installed init_scaffold.missing_substrate, request.validate_record,
      authorization.is_authorized and B journal replay/recovery, reached through the qualification
      harness. Completeness: Enumerate gate/validator/authorization/replay/recovery imports
      against W30 inventory. Remove the isolated runtime, then run actual processes on valid and
      corrupt authority fixtures; require stdlib-only operation with named integrity refusals and
      graph-runtime unavailability. Reinstall a tampered dependency and require hash refusal
      before activation; execute supported Python/host profiles, naming unavailable rows as
      blocked. Falsifier: Import LangGraph from journal recovery and remove the runtime
      environment; install/stdlib-recovery must detect the broken recovery command.
    falsified_by: >
      Import LangGraph from journal recovery and remove the runtime environment;
      install/stdlib-recovery must detect the broken recovery command.
required_evidence: [unit, integration, journeys]
rollback: >
  Withdraw the affected pack qualification, retain its installed evidence and previous compatible
  artifact, and keep activation disabled until requalified.
---

## Intent

Qualify every shipped pack as an installed factory with complete assets, truthful provenance and a working floor slice.

## Context

Package H, W79 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R35/R53/R63 extend W30 distribution and C installed proof. Existing check_install_and_run measures init and a starter gate, not the full slice. Packaging omissions and false qualification warrant high risk. Risk is high; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

Live production enrollment, provider certification already owned by D and a green claim from source-only tests are excluded.

## Notes

D1/D2 block the real authority/replica slice; D3/D4 block qualified containment and isolated worker clones. Exact runtime/Python/host profiles come from W30/D proof, never guessed dependency versions. scripts/publish.py composes by copying engine files absent in the wrapper, while pack.assemble_pack overlays wrapper bytes; exercise both and reject unauthorized shadowing, preserving only declared starter transforms. Register control_install_journey and all qualification assets in distribution/contracts before ready. The existing gate scripts are invoked, not changed; suite manifest registration carries these checks. Keep launch observations, engine byte comparisons, original stamps and each negative-control diff.
