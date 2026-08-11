---
schema: veldo.spec/v1
id: WARP-0802
title: Claude pack as a peer - canonical engine, pack manifest, and drift-check wired into the gate
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0008
work: W2
plan_revision: 1
depends_on: [WARP-0801]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: ENGINE_GLOBS is finalized to cover the REAL tool-agnostic engine under the canonical
      source engine - it adds the guard script (scripts/veldo-guard.sh) and the whole
      runners tree (scripts/runners) to the existing substrate (scripts/verify.sh, scripts/*.py,
      .veldo/*.py, .veldo/*.yaml, the CI workflow, the spec/plan templates), and engine_files EXCLUDES
      build artifacts (any __pycache__ directory and any .pyc file) so the engine set is exactly the
      shipped source, never a compiled artifact.
  - id: AC2
    text: A pack manifest (.veldo/packs.json, veldo.packs/v1) declares each pack with its tool, its
      engine source, and its pack directory; it is loaded and validated (a malformed manifest is
      rejected by name), and it declares the Claude pack as the first peer - the current packs/claude/ tree
      IS the Claude pack (option B, no restructure until release), so the Claude pack's engine is the
      canonical source itself.
  - id: AC3
    text: A check (scripts/check_pack_drift.py) reads the manifest and, for every declared pack,
      reports any engine file MISSING from or DIFFERING from the canonical source via engine_drift
      (WARP-0801); an empty report is conformance and a drifted or incomplete pack fails by name. It
      is ENFORCED IN THE GATE through the selftest (the gate's unit check asserts pack_drift_report
      has no drift), not by editing the protected scripts/verify.sh; the standalone script is provided
      for a human and CI. So no pack can silently fork the engine once packs exist.
  - id: AC4
    text: The Claude pack is recognized as a peer WITHOUT restructuring the tree - packs/claude/ stays the
      Claude pack (its driver wrapper is packs/claude/agents, packs/claude/skills, packs/claude/hooks,
      packs/claude/.claude-plugin, and the guard trigger; its engine is engine; its instruction
      file is engine/AGENTS.md), and the rename to packs/claude and the marketplace repoint
      are deferred to the release (W10). No product behavior changes.
  - id: AC5
    text: A selftest gives the drift-check real teeth over a temporary tree - assembling a pack from
      the canonical engine yields engine_drift == [] (byte-identical), mutating one engine file in the
      assembled pack makes engine_drift report that file as differing, and removing one makes it
      report missing; the finalized ENGINE_GLOBS matches the real engine files (guard + runners
      present, no .pyc); and a malformed pack manifest is rejected by name - non-tautologically.
required_evidence: [unit]
rollback: git revert; additive - the finalized ENGINE_GLOBS + a __pycache__/.pyc exclusion + a
  manifest loader in .veldo/pack.py, a new .veldo/packs.json manifest, a new scripts/check_pack_drift.py,
  a selftest block enforcing no drift, one capability entry (both capabilities.yaml copies), and this
  spec; no protected path touched (the gate enforces drift via the existing selftest unit check, not
  by editing verify.sh); pure stdlib, no network.
---

## Intent

W1 (WARP-0801) built the pack engine as a pure mechanism over temporary trees; W2 wires it to the
REAL plugin engine and stands the Claude pack up as the first peer, so "each pack has everything in
it" and "one canonical engine, no drift" both hold for a real pack. It is the pattern-setter: W3
through W8 (Cursor, Codex, Copilot, Antigravity CLI, OpenCode, Aider) each add a pack that slots into
the manifest and is held byte-identical by the same drift-check.

## Context

W2 of PLAN-0008, depends on the pack engine (W1). Per the founder decision (option B), packs/claude/ stays
the Claude pack through the build and is renamed to packs/claude only at release (W10), so W2 changes
no file locations - it recognizes the existing packs/claude/ as the Claude pack and adds the manifest and
the drift-check. The canonical engine is engine (the substrate /veldo:init lays down); the
Claude pack's engine is that source itself (so its drift is trivially empty), and the drift-check
becomes load-bearing the moment W3 adds a second pack with its own engine copy.

## Notes

The WARP-0801 review noted ENGINE_GLOBS must cover the guard and the runners when wired to a real
pack; W2 does that and adds the build-artifact exclusion (a __pycache__ directory holds .pyc files
that are not source and must never be part of the byte-identical engine set). The drift-check is the
same discipline that keeps the two capabilities.yaml copies in lockstep, generalized to the whole
engine: one source of truth, assembled into self-contained packs, proven identical by the gate. The
manifest is .veldo/packs.json (structured, nested, stdlib json), following the trackers.json /
fleet_env.json precedent. The Claude pack entry points its engine at the canonical source (option B);
W3+ packs will carry an assembled engine copy that the check holds to the source. The rename to
packs/claude and the marketplace repoint are a release act (W10), not this increment.
