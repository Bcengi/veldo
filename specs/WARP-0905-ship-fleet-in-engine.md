---
schema: veldo.spec/v1
id: WARP-0905
title: Ship the fleet in the engine - the fleet modules and the veldo CLI become installable, honest, and drift-checked
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0009
work: W5
plan_revision: 1
protected_paths: []
depends_on: [WARP-0901, WARP-0902, WARP-0903, WARP-0904]
acceptance_criteria:
  - id: AC1
    text: The fleet's shippable dependency CLOSURE - the .veldo/*.py modules that bin/veldo and the fleet
      transitively load and that are not already shipped - is copied into the canonical engine
      engine/.veldo/, byte-identical to the repo-root originals, so (via the existing
      ENGINE_GLOBS `.veldo/*.py`) every pack carries the complete working fleet - the full-engine
      distribution that delivers the fleet to adopters. (/veldo:init, the init_scaffold minimal
      governance substrate that is proportionate by design and already lays only the gate/contracts/
      templates - not executor, metrics, events, or the runners - is intentionally NOT expanded to dump
      the full engine; the fleet is a full-toolkit capability delivered by installing a pack, not by the
      minimal scaffold. See Notes.) The closure is COMPUTED from the actual imports/_load calls (bin/veldo
      plus each module it reaches), not guessed, and it is CLOSED (every shipped module's own imports are
      either already shipped or stdlib). The non-fleet dogfood machinery (pack.py, pack_conformance.py,
      the tracker_* build machinery, release.py, and any other repo-only dogfood not in the fleet
      closure) STAYS repo-root only and is NOT shipped.
  - id: AC2
    text: bin/veldo ships into the engine at engine/bin/veldo, byte-identical to the repo-root
      bin/veldo and committed EXECUTABLE (100755), and a glob for it (e.g. bin/veldo) is added to
      ENGINE_GLOBS in .veldo/pack.py so every pack carries it and the drift-check covers it (content AND
      mode). The repo-root bin/veldo and the shipped engine/bin/veldo stay identical.
  - id: AC3
    text: The W3 account field is synced into the shipped engine/.veldo/events.py so it matches
      the repo-root .veldo/events.py (the W5 carry-forward from W3, where only the repo-root copy got the
      field); the two events.py copies are byte-identical again, so an adopter's events.py supports the
      per-account governor.
  - id: AC4
    text: ALL SEVEN packs are re-synced (re-assembled) so each pack's engine is byte-identical - content
      AND mode (exec bits preserved) - to the canonical engine source including the new fleet
      modules and bin/veldo; pack_drift_report is empty for every pack and the cross-pack conformance
      selftest (WARP-0809) passes across all seven.
  - id: AC5
    text: capabilities.yaml is HONEST about what now ships - the fleet capabilities (the dispatcher,
      work loop, worker spawner, per-account governor, in-session waiter, serialized lander, fleet env,
      account model, and the veldo CLI) are marked mechanical with homes that exist in an adopter's tree,
      in BOTH .veldo/capabilities.yaml and engine/.veldo/capabilities.yaml kept byte-identical;
      no capability entry claims a module an adopter will not have.
  - id: AC6
    text: The full gate is GREEN (selftest including the drift-check and cross-pack conformance across
      all seven packs, contracts, generated, docs, template_sync, secret_scan) and NO protected path is
      edited - only new fleet .py files, the ENGINE_GLOBS addition (pack.py is not protected), the
      capabilities entries, the events.py sync, and the re-synced pack copies. If shipping genuinely
      requires editing a protected file (scripts/verify.sh, scripts/veldo-guard.sh, .veldo/policy.yaml,
      .veldo/policy_check.py or their engine twins), STOP and flag for human approval rather
      than edit it. The veldo name is unchanged (no rename).
required_evidence: [unit]
rollback: git revert; additive - new engine module copies under engine/.veldo/ + packs/claude/
  templates/bin/veldo, a bin/veldo entry in ENGINE_GLOBS, the events.py account-field sync, the fleet
  capability entries, and the re-synced pack copies. Removing them returns to the pre-ship state; the
  repo-root dogfood fleet is untouched. No protected path; the drift-check and conformance harness prove
  no pack forked.
---

## Intent

The fleet is real and driven by a real CLI (W1-W4), but it lives only in the repo-root .veldo/ as
dogfood - an adopting team that installs a pack does NOT get it, and the honesty manifest over-claims
it. W5 ships it: the fleet's module closure and bin/veldo move into the canonical engine so every pack
carries the complete working fleet, the shipped events.py gains the account field, all seven packs are
re-synced byte-identical, and capabilities.yaml is made honest. This is what turns "the veldo repo has a
fleet" into "an adopter who installs a pack gets the fleet."

## Context

W5 of PLAN-0009, depends on W1-W4. The engine source is engine/; ENGINE_GLOBS in .veldo/pack.py
already globs `.veldo/*.py` and `.veldo/*.yaml`, so any .py added to engine/.veldo/ is
automatically engine (copied into every pack, drift-checked) - no glob edit needed for the modules.
bin/veldo is at the repo root (from W4) and there is no engine/bin/ yet, so it needs a copy
into engine/bin/veldo and a new ENGINE_GLOBS entry. The pack assembler (.veldo/pack.py
assemble_pack / engine_files, shutil.copy preserves mode) and the drift-check (WARP-0801/0802,
mode-aware) and cross-pack conformance (WARP-0809) are the safety net: re-sync the packs, and a red
gate the instant anything diverges. The fleet stays named veldo (the VELDO rename is parked; keep
internal).

## The closure (get this exactly right)

Ship exactly what the fleet needs, nothing more. Start from bin/veldo and follow every _load/import to
its transitive closure; ship the members not already in engine/.veldo/ (candidates:
accounts, claim, dispatch, executor, fleet, fleet_env, frontier, governor, lander, work, and the run
lens deps the CLI uses - runstatus, runcmd, runlog - plus anything they reach). VERIFY closure: every
shipped module's imports resolve to a shipped or stdlib module (no shipped module may import a
repo-only dogfood module like pack.py or tracker_conformance.py). Do NOT ship the non-fleet dogfood
(pack.py, pack_conformance.py, tracker_conformance/adapter/intake/mirror.py, release.py, and any other
repo-only module not in the fleet closure) - those are how VELDO builds itself, not what an adopter
runs.

## Out of scope

The docs (W6 makes the README/plugin.md/setup.md true), the opt-in external supervisor (W7 / D1), the
release version bump (W8). No rename (veldo stays veldo; VELDO is parked). No protected-path edits.

## Notes

Two-tier adoption, by design (the AC1 decision). VELDO has two ways in, and the fleet belongs to one of
them: installing a pack lays the FULL engine (all engine files, now including the fleet) - that is the
full-toolkit path, and it is how an adopter gets the fleet. /veldo:init (init_scaffold) is the OTHER
path: a minimal governance substrate, "proportionate by design" per its own docstring, that lays only
the gate, contract validator, capability manifest, and templates so a fresh repo's own gate runs green
with no product code. It already does not lay executor, metrics, events, plan, or the runners, so it
does not lay the fleet either. Expanding init_scaffold to dump the full engine would violate that
established minimal design (RULE #6 - do not bloat a proportionate component); the fleet is delivered
via the pack, not the scaffold. init_scaffold is therefore intentionally UNTOUCHED by W5, and W6 will
document the two-tier adoption model (install a pack for the fleet; /veldo:init for the governance
substrate) so the honesty holds in the docs too.

Two commits, the standard shape: an impl commit with its own independent review and commit-bound
verdict, then an evidence-only commit (proof/, .veldo/, specs/) inheriting the impl verdict via the
guard's parent rule. Note that the impl commit will be LARGE (the fleet modules copied into
engine/ AND into all seven packs) - that is expected for a distribution item; the drift-check
and conformance selftest prove the copies are byte-identical, not forks.

RULE #1: the gate's dash-sweep catches only em/en dashes, not the ASCII double-hyphen; hand-check the
new capability entries and any prose for `--`. bin/veldo and the fleet modules are copied verbatim
(already dash-clean from W1-W4). Preserve exec bits on every copy (the WARP-0807 lesson: a
non-executable committed hook/CLI fails open; keep bin/veldo and any pack hooks 100755).
