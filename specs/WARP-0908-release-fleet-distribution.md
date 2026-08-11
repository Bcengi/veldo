---
schema: veldo.spec/v1
id: WARP-0908
title: Release VELDO Fleet distribution v1 (PLAN-0009 at 8/8) - plugin 3.5.0
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0009
work: W8
plan_revision: 2
depends_on: [WARP-0905, WARP-0906]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: The plugin version is bumped to 3.5.0 for the VELDO Fleet distribution v1 milestone -
      packs/claude/.claude-plugin/plugin.json reads 3.5.0, the marketplace entry (.claude-plugin/marketplace.json)
      reads 3.5.0, and the PLAN-0009 release.version field reads plugin 3.5.0. The generic method
      documents are unchanged: the fleet ships as engine and packs, not a change to the VELDO method.
  - id: AC2
    text: The shipped fleet is recorded honestly in the capability manifest. Every fleet capability an
      adopter's tree carries (the dispatcher, the account registry, the in-session worker spawner, the
      per-account governor, the in-session resume waiter, the veldo CLI, the in-session resume default,
      and the opt-in external supervisor with its session-launch reference seam) is marked mechanical or
      reference with a home that resolves in the SHIPPED engine, none is over-claimed, and the repo-only
      markers from W6 stay intact. Both .veldo/capabilities.yaml and the shipped
      engine/.veldo/capabilities.yaml are byte-identical and pass the WARP-0906
      home-resolution honesty check (mechanical only where shipping code backs it in an adopter tree,
      per O5 and C6).
  - id: AC3
    text: Every declared pack's engine stays byte-identical (content AND mode) to the canonical source at
      the release. After any engine edit the six copied packs are re-synced so pack_drift_report is empty
      for all seven and the cross-pack conformance harness passes, proving the release ships assembled
      drop-in distributions with no drift.
  - id: AC4
    text: The docs point to the shipped fleet. Every fleet command named in the docs exists in the shipped
      bin/veldo (veldo work, veldo fleet N, veldo account, veldo status and watch, veldo answer/steer/abort, and
      veldo supervisor), the README fleet section describes the installable fleet as it ships, and the
      README plugin-version line reads 3.5.0 with no claim beyond what W1 through W8 ship.
  - id: AC5
    text: The packs/claude/ to packs/claude rename and the marketplace source repoint remain DEFERRED as a
      separate human-approved change, because they move the protected enforcement files
      (engine/scripts/verify.sh, engine/scripts/veldo-guard.sh,
      engine/.veldo/policy_check.py) and rewrite the .veldo/policy.yaml entries that name them (a
      protected-path change requiring human approval). This release keeps packs/claude/ in place as the option-B
      Claude pack (marketplace source ./packs/claude) and the name stays VELDO (VELDO parked). No protected path
      is touched by this release, so policy_check requires no approval.
  - id: AC6
    text: With W1 through W7 already shipped and W8 (this spec) shipped, plan.py release-check PLAN-0009
      reports releasable and PLAN-0009 status is set to released. At the impl commit W8 is ready, so
      release-check reports not-yet-releasable (WARP-0908 pending) and releasability is achieved when this
      spec flips to shipped in the evidence commit - verifiable independently by simulating WARP-0908
      shipped and running release-check.
  - id: AC7
    text: The full gate is GREEN (selftest including the fleet suites, the capabilities-honesty check, the
      pack drift check, and cross-pack conformance across all seven packs; contracts, generated, docs
      hygiene, template sync, and secret scan all pass); no protected path is edited; the index is
      regenerated; and RULE #1 is clean (no em or en dash, no prose double-hyphen).
required_evidence: [operational]
rollback: git revert the release commit and its evidence; the version bump withdraws and the plan returns
  to in_progress (the eight work items stay shipped). The release is additive - a version bump, a confirmed
  honest capability record, and the fleet docs - so reverting it leaves the shipped fleet engine and the
  seven packs intact.
---

## Intent

Close out PLAN-0009: cut the VELDO Fleet distribution v1 milestone (plugin 3.5.0) now that the fleet ships
in the canonical engine and every pack (W1 through W7) - the real dispatcher, the account model and the
in-session worker spawner, per-account pacing and the in-session resume waiter, the veldo CLI, the engine
distribution, the true docs, and the opt-in external supervisor. This is the release item, W8: a version
bump, an honest capability record of the shipped fleet, docs that point to it, and the plan flipped to
released once the release check is green.

## Context

W8 of PLAN-0009, depends on W5 (the fleet in the engine) and W6 (the docs made true). W1 through W7 each
shipped through the full VELDO loop with an independent review. The fleet modules live in engine
and are copied byte-identical into every pack; the drift-check and the cross-pack conformance harness hold
them identical (content and mode). capabilities.yaml already records the fleet honestly (W5 marked the
shipped modules mechanical, W6 added the home-resolution honesty check and the repo-only markers, W7 added
the three supervisor entries), so this release records no new claim and over-claims nothing: it bumps the
version, confirms the honest manifest, points the docs at the fleet, and marks the plan released. Because
W8 is itself a gating work item of PLAN-0009 (unlike a standalone release), release-check requires
WARP-0908 shipped.

## Out of scope

The packs/claude/ to packs/claude rename and the marketplace source repoint (a floor-high protected-path change,
deferred to a separate human-approved change). Per-tool native-marketplace publishing (NG4). The
autonomous fleet worker role on the IDE packs (NG5). Wiring a real, live session launcher behind the
supervisor reference seam (the adopter's opt-in step). The VELDO rename and open-source are parked; the
name stays VELDO.

## Notes

Two commits, the standard VELDO release shape: an impl commit (the version bump, the confirmed-honest
capability manifest, the fleet docs, and this spec at status ready) carrying its own independent review and
commit-bound verdict, then an evidence-only commit (this spec flipped to shipped, the proof manifest and
verdict, last_verify, events, the regenerated index, and the plan flipped to released) that inherits the
impl commit's verdict via the guard's parent rule.

AC6 is the release-specific subtlety: because W8 gates PLAN-0009, release-check reports not-yet-releasable
at the impl commit (WARP-0908 pending) and becomes releasable the moment this spec flips to shipped in the
evidence commit. A reviewer can verify AC6 at the impl commit by simulating WARP-0908 shipped (all other
work is already shipped) and confirming release-check then reports releasable. No protected path is touched
by this release, so policy_check requires no approval.

RULE #1: hand-check this spec, the capability confirmation, and the release note for the ASCII
double-hyphen; the gate dash-sweep catches only em and en dashes.
