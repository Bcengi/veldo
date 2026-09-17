---
schema: veldo.spec/v1
id: VELDO-0098
title: Rollback compatibility and coordinated release qualification
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W83
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0063, VELDO-0064, VELDO-0065, VELDO-0066, VELDO-0067, VELDO-0068, VELDO-0069, VELDO-0070, VELDO-0071, VELDO-0072, VELDO-0073, VELDO-0074, VELDO-0075, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0079, VELDO-0080, VELDO-0081, VELDO-0082, VELDO-0083, VELDO-0084, VELDO-0085, VELDO-0086, VELDO-0087, VELDO-0088, VELDO-0089, VELDO-0090, VELDO-0091, VELDO-0092, VELDO-0093, VELDO-0094, VELDO-0095, VELDO-0096, VELDO-0097]
placement: [distribution, contracts, docs]
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
  - "engine/.veldo/plan.py"
  - ".veldo/plan.py"
  - "packs/*/.veldo/plan.py"
  - "engine/.veldo/release_contract.py"
  - ".veldo/release_contract.py"
  - "packs/*/.veldo/release_contract.py"
  - "engine/.veldo/control_release_qualification*.py"
  - ".veldo/control_release_qualification*.py"
  - "packs/*/.veldo/control_release_qualification*.py"
  - "engine/.veldo/control_restore*.py"
  - ".veldo/control_restore*.py"
  - "packs/*/.veldo/control_restore*.py"
  - "scripts/check_install_and_run.py"
  - "scripts/publish.py"
  - ".veldo/packs.json"
  - "engine/runtime/*"
  - ".veldo/runtime/*"
  - "packs/*/runtime/*"
  - ".claude-plugin/marketplace.json"
  - "packs/*/plugin.json"
  - "packs/claude/.claude-plugin/plugin.json"
  - "plans/PLAN-0019-dark-factory.md"
  - "scripts/suites/*_veldo_0098_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0098-rollback-coordinated-release-qualification.md"
  - "specs/index.md"
  - "proof/VELDO-0098/*"
behavior_bearing: true
observability:
  logs: >
    Release qualification receipts identify candidate/tree, current/retained artifact and
    runtime/schema digests, observed journey set and activation or rollback authority.
  metrics: >
    Report every-pack qualification coverage, incompatible reader/writer pairs, failed rollback
    drills and missing coordinated milestone evidence.
  traces: >
    Trace reproducible publisher output through installed upgrade/rollback and full regression to
    exact accepted release-execution evidence.
  error_taxonomy: >
    Distinguish incompatible downgrade, absent retained artifact, guessed install identity,
    missing observed journey and unqualified activation.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Rollback uses the retained known-good artifact and a proven compatible reader without
      erasing new history. Set: Installed control_restore/release qualification,
      version.installed_version/drift/provenance_report and init_scaffold.scaffold/_write_stamp.
      Completeness: Freeze actual prior/current artifact, schema-reader/writer, runtime/checkpoint
      and Python/host versions from W30/W79 inventory. For every supported pair and pack, install
      current, create authoritative and pending state, stop/fence, then run the retained release
      against compatible verified history. Reject incompatible writes/downgrades and missing
      retained bytes by name. Preserve original install stamp and record upgrade/rollback as
      separate receipted acts with measured artifact digests. Falsifier: Allow the retained writer
      to modify an unsupported newer schema; rollback/incompatible-writer must detect an implicit
      destructive downgrade.
    falsified_by: >
      Allow the retained writer to modify an unsupported newer schema;
      rollback/incompatible-writer must detect an implicit destructive downgrade.
  - id: AC2
    text: >
      Claim: Coordinated release qualification requires actual complete installed regression and
      every required work outcome. Set: plan.cmd_release_check/cmd_regression/_journey_active and
      release_contract.release_report/member_digest consumed by control_release_qualification.
      Completeness: Register RJ8/RJ9 and bind RJ1-RJ10 to executable checks. Compare required work
      and journey registries to accepted exact-candidate receipts in both directions across every
      nonempty composed pack/profile set. Include W79 installation, W80 migration, W81 adoption
      and W82 combined recovery, not only source suites. Missing, stale, failed or unexecuted
      required journeys block; activation-after-owner rules cannot let this qualifying release
      skip its own RJ8/RJ9 proof. Falsifier: Treat a declared but unexecuted RJ9 as passing full
      regression; release-qualification/observed-journeys must detect the unsupported coordinated
      milestone.
    falsified_by: >
      Treat a declared but unexecuted RJ9 as passing full regression;
      release-qualification/observed-journeys must detect the unsupported coordinated milestone.
  - id: AC3
    text: >
      Claim: The qualified release is the reproducibly composed artifact actually installed and
      rolled back. Set: scripts/publish.py.tracked_files/selected/compose_packs/build/_identical,
      pack.engine_drift and scripts/check_install_and_run.py.check/install_and_run. Completeness:
      Build twice from the same tracked candidate, compare bytes/modes and authoritative
      inventory, then install exactly those artifacts without source access. Verify engine
      equality, runtime hashes/licenses, truthful version declarations via
      version.read_declaration/version_report and no leaking private build coordinates. Tamper one
      wrapper engine file or omit a retained runtime asset and require qualification refusal
      before any activation receipt. Falsifier: Permit a wrapper to shadow a canonical engine
      validator in the composed release; release-qualification/engine-shadow must detect a
      differing installed enforcement file.
    falsified_by: >
      Permit a wrapper to shadow a canonical engine validator in the composed release;
      release-qualification/engine-shadow must detect a differing installed enforcement file.
  - id: AC4
    text: >
      Claim: Activation and rollback are separate current authorized acts, never consequences of
      source landing or a stamp. Set: control_release_qualification activation/rollback commands
      using installed B command verification and E enrolled decision settlement. Completeness:
      Enumerate all activation inputs and require current
      artifact/proof/policy/membership/generation bindings. Exercise source landing alone, forged
      current stamp, stale presentation, revoked operator and altered rollback target beneath a
      retained CLI signature. Require no activation; a current authorized command with compatible
      retained material is the positive control. Remove graph checkpoints and repeat to prove
      original command results and no repeated effect. Falsifier: Activate the service merely
      because the new artifact passes plan.cmd_release_check;
      release-qualification/separate-activation must detect an unapproved operational start.
    falsified_by: >
      Activate the service merely because the new artifact passes plan.cmd_release_check;
      release-qualification/separate-activation must detect an unapproved operational start.
required_evidence: [unit, integration, journeys]
rollback: >
  Withhold activation, stop affected writers and retain current plus previous artifacts and signed
  history; perform only a proven compatible authorized rollback.
---

## Intent

Establish coordinated release readiness from installed recovery and retained-release rollback proof before authorized activation.

## Context

Package H, W83 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) governs this draft. R27/R54/R63 close PLAN-0019 adoption. The existing publisher builds artifacts and version readers report provenance; neither authorizes service activation. Rollback and activation affect critical authority. Risk is critical; required approval must bind the eventual implementation and proof. This draft records no approval or activation.

## Out of scope

Pushing this drafting branch, modifying published prose, implicit schema downgrade and declaring a release from source-only green are excluded.

## Notes

D1/D2 block release authority and replica compatibility proof; D3/D4 block installed service/clone qualification. Dmitry must name operations activation and rollback authorities, and approve the exact retained release compatibility policy before activation. No historical version is guessed: unavailable prior artifacts or unsupported schema readers block the relevant pair. Map control_release_qualification to distribution/contracts and inventory its matrices through W30 before ready. Keep install stamps separate from qualification and activation receipts, retain prior artifacts through the full proof plan and save each mutation diff with its named failing row.
