---
schema: veldo.spec/v1
id: WARP-0801
title: Canonical engine, pack assembler, and drift-check - self-contained packs from one source
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0008
work: W1
plan_revision: 1
depends_on: []
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A single canonical ENGINE is defined by a manifest (.veldo/pack.py ENGINE) listing the
      tool-agnostic files a pack needs to run VELDO (the gate, policy_check, validate, the .veldo
      substrate, the runners, the CI workflow, capabilities.yaml, the spec/plan templates) - the
      files that must be identical in every pack.
  - id: AC2
    text: assemble_pack(engine_src, wrapper_src, agents_md, dest) produces a SELF-CONTAINED pack
      at dest - every engine file copied byte-for-byte from engine_src, the tool wrapper copied
      from wrapper_src, and the canonical AGENTS.md placed at dest/AGENTS.md - so an assembled
      pack is a complete drop-in with the engine and the tool's wrapper together, nothing
      external needed.
  - id: AC3
    text: engine_drift(engine_src, pack_dir) reports every engine file that is missing from a
      pack or differs from the canonical source (empty list means the pack's engine is
      byte-identical to the source), so the gate can prove no pack has drifted - self-contained
      for the user, single source of truth for us.
  - id: AC4
    text: A canonical AGENTS.md ships (the convergent cross-tool instructions file) carrying the
      VELDO method and operating contract once, tool-neutrally, so every pack bundles the same
      method and per-tool instruction files reference it rather than restating it; it is generic
      and ASCII with no em-dashes.
  - id: AC5
    text: A selftest drives the assembler and the drift-check over temporary engine, wrapper, and
      pack trees - asserting an assembled pack has the engine byte-identical plus the wrapper plus
      AGENTS.md, that engine_drift is empty on a faithful copy, and that it names a mutated engine
      file and a missing engine file - and is non-tautological (drift is empty when identical and
      non-empty when a byte changes). The full gate is GREEN.
required_evidence: [unit]
rollback: git revert; additive - a new .veldo/pack.py, a canonical AGENTS.md, a selftest block,
  one capability entry (both copies), and this spec; no protected path; pure stdlib file ops,
  no network.
---

## Intent

The foundation of the seven-pack port: one canonical engine, a mechanism to assemble a
self-contained pack from it, and a drift-check that keeps every pack byte-identical to the
source. This is how "each pack has everything in it" and "one source of truth, no drift" hold
at once - the same way the two capability files are kept in lockstep today, generalized to the
whole engine.

## Context

W1 of PLAN-0008, the root every pack item (W2 through W8) depends on. It ships the MECHANISM -
the engine manifest, the assembler, the drift-check, and the canonical AGENTS.md - gate-tested
over temporary trees; wiring it to the real plugin engine and creating the actual seven packs is
W2 (Claude as a peer) onward. The drift-check becomes a gate assertion once packs exist; here it
is proven over temp packs (a faithful one and a drifted one).

## Notes

The engine manifest is the crux: it names exactly the tool-agnostic files that must be identical
across packs, so the driver wrapper (agents, skills or commands, guard trigger, the tool's
instruction file) is everything a pack adds on top. assemble_pack and engine_drift are pure
stdlib file operations parametrized by paths, so they are deterministic and gate-tested offline
with no real packs and no network. The canonical AGENTS.md is the single home of the method and
operating contract for every tool; each pack's native instruction file (CLAUDE.md, GEMINI.md,
.github/copilot-instructions.md, Aider CONVENTIONS.md) points at it, so the method never forks.
