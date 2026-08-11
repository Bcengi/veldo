---
schema: veldo.spec/v1
id: WARP-0810
title: Release VELDO multi-tool packs v1 (PLAN-0008 at 10/10) - plugin 3.4.0
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0008
work: W10
plan_revision: 1
depends_on: [WARP-0809]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: The plugin version is bumped to 3.4.0 for the VELDO multi-tool packs v1 milestone -
      packs/claude/.claude-plugin/plugin.json is 3.4.0, the marketplace entry (.claude-plugin/marketplace.json)
      is 3.4.0, and the PLAN-0008 release.version field reads plugin 3.4.0. The method document is
      unchanged - seven packs run the same VELDO loop natively, not a change to the generic method.
  - id: AC2
    text: The seven-pack multi-tool support is recorded honestly in the capability manifest - a
      multitool_packs entry (and the W9 pack_conformance entry) is present in both
      .veldo/capabilities.yaml and the shipped engine/.veldo/capabilities.yaml, and
      .veldo/packs.json declares all seven packs (claude, cursor, codex, copilot, antigravity,
      opencode, aider).
  - id: AC3
    text: Every declared pack's engine is byte-identical (content AND mode) to the canonical source
      after this release - the six copied packs are re-synced to the edited canonical engine so
      pack_drift_report is empty for all seven and the cross-pack conformance harness passes, proving
      the release ships assembled drop-in distributions with no drift.
  - id: AC4
    text: The drop-in packs are documented - packs/README.md describes the seven packs, the one-engine
      byte-identical assembly, and the identical enforcement invariant (native hook where present, git
      pre-push everywhere, CI required status check), and README.md plus docs/plugin.md point to it.
  - id: AC5
    text: The packs/claude/ -> packs/claude rename and marketplace source repoint is DEFERRED as a separate
      human-approved change, not part of this release, because it moves the protected enforcement files
      (engine/scripts/verify.sh, engine/scripts/veldo-guard.sh,
      engine/.veldo/policy_check.py) and rewrites the .veldo/policy.yaml entries that name
      them - a protected-path change with floor high requiring human approval. This release keeps
      packs/claude/ in place as the option-B Claude pack (marketplace source ./packs/claude), and the capability
      notes state this deferral honestly. No protected path is touched by this release, so no approval
      is required.
  - id: AC6
    text: With W1-W9 already shipped and W10 (this spec) shipped, plan.py release-check PLAN-0008
      reports releasable and PLAN-0008 status is set to released. At the impl commit W10 is ready, so
      releasability is achieved when this spec flips to shipped in the evidence commit - verifiable
      independently by simulating WARP-0810 shipped and running release-check.
  - id: AC7
    text: The full gate is GREEN (selftest passes including the cross-pack conformance and drift
      checks, contracts pass, generated/docs/template_sync/secret_scan pass) and the dash and
      genericity sweeps pass on the changed documents.
required_evidence: [operational]
rollback: git revert this release commit and its evidence; the version bump withdraws and the plan
  returns to ready (the ten work items stay shipped). Each pack is an additive self-contained
  directory assembled from the canonical engine; removing one leaves the source and the other packs
  intact.
---

## Intent

Close out PLAN-0008: cut the VELDO multi-tool packs v1 milestone (plugin 3.4.0) now that all seven
packs are assembled from the one canonical engine (W1-W8) and the cross-pack conformance harness
proves, by construction, that every pack enforces the VELDO invariant with no engine drift (W9). This
is the release item, W10 - a version bump, an honest capability record of the seven-pack support, the
drop-in pack documentation, and the plan flipped to released once the release check is green.

## Context

W10 of PLAN-0008, depends on W9 (the join point). W1-W9 each shipped through the full VELDO loop with
an independent review. The one canonical engine (engine) is assembled into a self-contained
pack per tool; the drift-check holds every pack byte-identical (content and mode) and the conformance
harness proves the push gate blocks an unproven push and allows a proven one on every pack. This
release records that support (the multitool_packs capability entry and packs/README.md), bumps the
version, and marks the plan released.

The release edited the canonical engine's capabilities.yaml (the multitool_packs and pack_conformance
entries), which the drift-check then requires be propagated into every copied pack - so W10 re-syncs
the six copied packs to the edited canonical engine, exactly the discipline the drift-check exists to
enforce: edit the one source, re-assemble, prove byte-identical.

## Out of scope

The packs/claude/ -> packs/claude rename and the marketplace source repoint. It moves the protected
enforcement files and rewrites the .veldo/policy.yaml entries that name them (a floor-high
protected-path change requiring human approval), so it is deferred to a separate human-approved
change. This release keeps packs/claude/ in place as the option-B Claude pack (its engine is the canonical
source in-place, so its drift is empty and honest) with the marketplace source at ./packs/claude.
Per-tool native-marketplace publishing (a Cursor listing, a Copilot Marketplace extension) is the
founder-approved deferral NG4. Wiring the CLI packs as headless fleet workers is NG5.

## Notes

Two commits, the standard VELDO release shape: an impl commit (the version bump, the capability
entries, the re-synced packs, the docs, the plan flipped to released, and this spec at status ready)
carrying its own independent review and commit-bound verdict; then an evidence-only commit (proof/,
.veldo/, specs/ only - this spec flipped to shipped, the proof manifest, the verdict, last_verify,
events, and the regenerated index) that inherits the impl commit's verdict via the guard's parent
rule. The plan flip lives in the impl commit because plans/ is not in the evidence-only allowlist.

AC6 is the one release-specific subtlety: because W10 is itself a gating work item of PLAN-0008
(unlike WARP-0708, PLAN-0007's release, which was standalone), release-check requires WARP-0810
shipped. At the impl commit WARP-0810 is ready, so release-check reports not-yet-releasable
(WARP-0810 pending); it becomes releasable the moment this spec flips to shipped in the evidence
commit. A reviewer can verify AC6 at the impl commit by simulating WARP-0810 shipped (all other work
is already shipped) and confirming release-check then reports releasable. No protected path is touched
by this release, so policy_check requires no approval.
