---
schema: veldo.spec/v1
id: WARP-1110
title: Release - VELDO architecture and maintainability v1 (PLAN-0011 at 10/10), engine ships the shape organ, docs made true, plugin 3.7.0 (W10 of PLAN-0011)
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0011
work: W10
plan_revision: 2
depends_on: [WARP-1102, WARP-1104, WARP-1106, WARP-1107, WARP-1109]
protected_paths: []
placement: [distribution]
footprint:
  - specs/WARP-1110-release-architecture-maintainability.md
  - plans/PLAN-0011-architecture-and-maintainability.md
  - README.md
  - docs/plugin.md
  - docs/setup.md
  - docs/runbook.md
  - packs/claude/.claude-plugin/plugin.json
  - .claude-plugin/marketplace.json
acceptance_criteria:
  - id: AC1
    text: >
      The engine SHIPS the full PLAN-0011 shape organ and it is byte-identical across every
      copy. The eight new .veldo modules the plan grew - arch.py (W1 contract validator and W3
      placement gate), shape_gate.py (W2 gate-time enforcement), shape_review.py (W4 shape-fit
      review dimension), decision.py (W5 foundational decision record), decision_review.py (W6
      adversarial decision review), tripwire.py (W7 in-session tripwires), entropy.py (W8
      cost-to-change metrics), and restoration.py (W9 restoration-spec generation) - plus the
      shape hook already wired into scripts/verify.sh at W2, are present in engine/.veldo
      (the canonical engine) and byte-identical in this repository's own .veldo instance and in all
      six assembled packs (cursor, codex, copilot, antigravity, opencode, aider). Proven by the
      existing gate teeth: scripts/check_template_sync.sh (root versus the canon) passes, and
      scripts/check_pack_drift.py reports every pack byte-identical to the canonical source (7 packs
      including the in-place Claude pack). This item lands NO engine module change (the machinery
      landed per item at W1 through W9 under the C5 sync discipline); it asserts the synced state
      holds and does not regress.
  - id: AC2
    text: >
      /veldo:init lays down the VALIDATORS an adopter needs while the architecture CONTRACT stays
      root-only and per-repo, so a fresh init repository is adoption-safe. .veldo/init_scaffold.py
      lays down the six gate-wired and validate-wired validators (arch.py, decision.py,
      decision_review.py, shape_review.py, shape_gate.py, tripwire.py) and lists them in
      REQUIRED_SUBSTRATE, so a scaffolded repository carries the organ's enforcement; the two
      advisory CLI-only derivations (entropy.py, restoration.py) are correctly NOT in the minimal
      init substrate (they are never wired into verify.sh or validate.py run_all and depend on the
      metrics organ init does not lay) and ship in the full pack engine instead - the honest two-tier
      model (a pack lays the full engine; /veldo:init lays the minimal governance substrate). The
      architecture.yaml CONTRACT itself is NEVER shipped by init and never copied into a pack: it is
      a per-repo artifact this repository carries as its own approved first instance. Consequence,
      proven by the existing scaffold selftest: a fresh init repository has the validators but no
      architecture.yaml and no .veldo/decisions directory, so the shape gate stands down and the
      contract, decision, tripwire, and placement checks stand down (adoption-safe), and the
      scaffolded gate runs green on the empty starter plan.
  - id: AC3
    text: >
      capabilities.yaml is HONEST for the whole architecture organ, in every copy. The manifest
      carries one accurate entry per organ capability - architecture_contract, spec_placement_footprint,
      shape_gate_enforcement, shape_fit_review, foundational_decision_record, adversarial_decision_review,
      decision_tripwires, entropy_metrics, restoration_generation - each naming exactly what ships and
      what is per-repo or reference, with no capability claimed that an adopter's tree does not carry;
      the root .veldo/capabilities.yaml equals engine/.veldo/capabilities.yaml and every pack
      copy is byte-identical (the pack drift check covers .veldo/*.yaml). This item claims no new
      capability and edits none: the entries were authored per item at W1 through W9; AC3 asserts they
      are complete and honest for the release and do not over-claim.
  - id: AC4
    text: >
      The docs are made TRUE for the architecture organ, honestly and fully generic. README.md gains
      a capability bullet describing the organ; docs/plugin.md gains a new section 13 documenting what
      the plugin ships (the per-repo contract, the shape gate, placement and footprint at elaboration,
      the shape-fit review dimension, foundational decision records, adversarial decision review, the
      in-session tripwire pass, and the entropy-to-restoration loop); docs/setup.md gains section 7.8
      documenting the organ as a governance mechanism; and docs/runbook.md gains the in-session
      tripwire and entropy pass in the weekly ritual plus a cheat-sheet row. Every doc defers to
      capabilities.yaml as the machine-readable truth and states the HONEST split without over-claiming:
      the module-size budget and the engine invariants are the gate-BLOCKING mechanizable rules, while
      dependency and import boundaries, the function-length, duplication, and complexity budgets, and
      the prose patterns are REVIEW-LANE reference implementations surfaced as non-blocking notes (not
      gate refusals) at this contract revision; the architecture.yaml contract is per-repo and NOT
      shipped in the engine; the shape-fit and adversarial-decision reviewers are fail-loud reference
      seams whose LIVE reviewer prompt wiring is per-repo and still pending; and every monitoring pass
      is in-session, nothing detached. The docs check passes (no em or en dash, no non-ASCII, zero
      company or product references in docs/ and packs/claude/); the method.md foundational document is
      unchanged, consistent with every prior release.
  - id: AC5
    text: >
      The plugin version is bumped and PLAN-0011 is marked released in this same reviewed impl commit.
      packs/claude/.claude-plugin/plugin.json is 3.7.0, .claude-plugin/marketplace.json is 3.7.0, and README.md
      reads 3.7.0 (the two Document History lines that cite plugin 3.6.0 for WARP-1008 are historical and
      stay). PLAN-0011 status flips ready to released in the impl commit (plans/ is excluded from the push
      guard's evidence-only allowlist, so the plan flip cannot live in the trailing evidence commit; the
      canonical two-commit release shape from WARP-0810/WARP-1008 puts the version bump, docs, and the
      plan flip in the reviewed impl commit, and the evidence commit carries only proof/ and .veldo/). This
      spec (WARP-1110) stays status draft in the impl commit and flips to shipped in the evidence commit at
      landing; release-check therefore reports NOT releasable until WARP-1110 is shipped, which is EXPECTED
      and verified by simulating WARP-1110 shipped and re-running plan.py release-check PLAN-0011.
  - id: AC6
    text: >
      The full gate is GREEN and the release touches no protected path and no engine module. scripts/verify.sh
      is green (selftest, contracts, generated index, docs hygiene, lint, secret scan, template sync, pack drift,
      the shape gate); the shape gate's footprint-versus-diff check passes because this spec's declared footprint
      covers every path the impl commit touches (this spec, PLAN-0011, README, the three docs, and the two version
      files), and the size budget has nothing governed to bind (the changed files resolve to no contract area).
      RULE #1 is clean (ASCII hyphen only, no em or en dash, no prose double-hyphen; any double-hyphen token is a
      genuine CLI flag). No protected path is touched (scripts/verify.sh, scripts/veldo-guard.sh, .veldo/policy.yaml,
      .veldo/policy_check.py and their engine twins are untouched - the W2 shape hook is already present in
      verify.sh). Dogfood: this spec's placement [distribution] resolves to a declared contract area, and its
      footprint touches no second area, so the footprint tier floor is empty and the risk tier stays standard
      (run-check PLAN-0011 WARP-1110 clears: deps shipped, plan context current, placement resolves).
required_evidence: [unit]
rollback: >
  git revert the release commit and its evidence commit. The version bump withdraws (plugin.json, marketplace.json,
  README return to 3.6.0), PLAN-0011 returns to ready, and the shipped W1 through W9 organ keeps working unchanged -
  the release adds no behavior of its own, only makes the docs true, bumps the version, and marks the plan released.
  A repository with no architecture contract is byte-identically unaffected before and after (the adoption-safe
  posture the whole organ stands on), so removing the release needs no migration; decision records, readings,
  restoration drafts, and metric series are inert per-repo data and keep their history.
---

## Intent

This is W10 of PLAN-0011, the release. Every lane has shipped: the architecture contract and its
validator (W1), gate enforcement of the mechanizable shape rules (W2), placement and footprint at
elaboration (W3), the shape-fit review dimension (W4), the foundational decision record (W5), the
adversarial decision review (W6), the in-session decision tripwires (W7), the entropy cost-to-change
metrics (W8), and restoration-spec generation (W9). This item does what a VELDO release always does:
it confirms the machinery is landed in the canonical engine and synced byte-identical across the packs
so /veldo:init lays down what an adopter needs, it makes the documentation TRUE for the organ as shipped
behavior (fully generic), it records the version bump, and it marks the plan released. Releasing this
plan is what turns the method's "The Shape of the System" design into receipts.

## Context

- The prior plan releases (WARP-0810, WARP-0908, WARP-1008) are the canonical model for the two-commit
  shape: the reviewed IMPL commit carries the version bump, the docs, and the PLAN status flip
  (ready to released), and the trailing EVIDENCE-only commit carries proof/ and .veldo/. The plan flip
  MUST be in the impl commit because the push guard's evidence-only allowlist is proof/, .veldo/, specs/
  only - plans/ is excluded - and the evidence commit inherits the impl verdict by the parent rule.
- The machinery landed per item under constraint C5 (the canon is engine; every new module,
  check, and contract template lands in the engine and syncs byte-identical). So at this release the
  eight organ modules are already in engine/.veldo and all six packs byte-identical, the
  capabilities entries are already authored, and init_scaffold already lays the six validators; this
  item adds no engine change and asserts that synced, honest state holds.
- Current version is 3.6.0 (PLAN-0010). Bump to 3.7.0.
- Docs to make true: README (a capability bullet), docs/plugin.md (a new section 13 parallel to the
  tracker section 12), docs/setup.md (the organ as a governance mechanism, section 7.8), and
  docs/runbook.md (the in-session tripwire and entropy pass folded into the weekly ritual, plus a
  cheat-sheet row). method.md the foundational method document is unchanged, as it has been across
  every prior release.

## Out of scope

- No engine module change. The organ modules and their capabilities entries shipped at W1 through W9;
  this item does not touch them, only the docs, the version, and the plan status.
- No new capability and no method-document change. The release ships a capability set and makes the docs
  true; it does not redesign the loop (NG4) and does not change the generic method.
- No live wiring of the delegated reviewer seams. LiveShapeReviewer (W4) and LiveAdversarialReviewer (W6)
  are fail-loud reference seams; wiring a real fresh-context reviewer's prompt is a per-repo act after
  release, honestly documented as pending, never over-claimed as shipped.
- No protected-path change. The W2 shape hook is already in scripts/verify.sh; this item re-modifies no
  gate, guard, policy, or policy_check file.
- No shipping of the per-repo artifacts. The architecture.yaml contract, decision records, readings,
  re-decision drafts, and restoration drafts are per-repo; they are never copied into the engine or a
  pack, and a fresh init repository carries none of them (adoption-safe).

## Notes

- Author the reviewed impl commit in the canonical release shape from the start: the version bump, the
  docs, and the PLAN-0011 ready-to-released flip together, with WARP-1110 left status draft (it flips to
  shipped in the evidence commit at landing, the reviewer's step, not the builder's). release-check reports
  NOT releasable until WARP-1110 is shipped; that is expected, and the reviewer verifies releasability by
  simulating WARP-1110 shipped.
- Honesty (RULE #6, NG5): the docs must not over-claim. State plainly that only the module-size budget and
  the engine invariants are gate-BLOCKING, while the dependency and import boundaries, the function-length,
  duplication, and complexity budgets, and the prose patterns are REVIEW-LANE reference implementations
  surfaced as non-blocking notes at this contract revision; that the architecture.yaml contract is per-repo
  and not shipped; and that the live reviewer prompt wiring is the one piece still pending. Every doc defers
  to capabilities.yaml as the machine-readable truth.
- The footprint declared above must cover every path the impl commit touches, because the shape gate's
  footprint-versus-diff check binds a change set that names exactly one footprinted spec. specs/index.md is
  a derived artifact excluded from that check (it regenerates), and proof/ is evidence, also excluded.
- RULE #1 clean (ASCII hyphen only, no em or en dash, no prose double-hyphen; any double-hyphen token is a
  genuine CLI flag). Fully generic: no company or product reference anywhere in the shipped docs.
