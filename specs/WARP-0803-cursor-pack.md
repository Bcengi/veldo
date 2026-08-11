---
schema: veldo.spec/v1
id: WARP-0803
title: Cursor pack - the first committed self-contained pack, drift-check cross-pack load-bearing
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0008
work: W3
plan_revision: 1
depends_on: [WARP-0802]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A self-contained Cursor pack exists at packs/cursor - the full canonical engine
      (engine, 139 files) is COPIED in byte-identical, plus the canonical AGENTS.md and a
      Cursor driver wrapper (.cursor/rules/veldo.mdc always-on, the skills, the agents) - so it is a
      complete grab-and-go directory ("everything in it"), per the founder decision to commit a copy
      per pack.
  - id: AC2
    text: The VELDO enforcement invariant holds for Cursor with no honor-system path (NG2) - a git
      pre-push hook (packs/cursor/hooks/pre-push) invokes the shared engine guard (scripts/veldo-guard.sh)
      and is backed by the CI required status check (.github/workflows/veldo-gate.yml, in the engine);
      a Cursor .cursor/hooks hook gives earlier in-editor feedback. Cursor has no native pre-push
      hook, so the git pre-push hook plus CI are the guaranteed gate.
  - id: AC3
    text: The pack is declared in .veldo/packs.json and the drift-check now holds the cursor pack's
      engine byte-identical to the canonical source - this is the first pack with a real committed
      engine copy, so the drift-check becomes CROSS-PACK load-bearing (not just the trivial Claude
      self-reference); check_pack_drift and the selftest report the cursor pack drift-free, and a
      drifted copy would fail by name.
  - id: AC4
    text: Reuse, not reinvention - the engine, AGENTS.md, skills, and agents in the pack are copied
      from the single canonical source (no forked substrate); only the thin Cursor driver (the .mdc
      rule and the hooks) is authored per tool. The WARP-0801 assembler produced the engine copy;
      the drift-check guarantees it stays identical.
  - id: AC5
    text: A selftest asserts the cursor pack conforms (engine drift-free) and carries its Cursor
      wrapper (the always-on rule, the guard hook, the skills, the agents, AGENTS.md), and is
      non-tautological (mutating an engine file in the pack is caught as drift). The PLAN-0008 text
      is reconciled in this commit (the W2 title to option B, every Gemini mention retargeted to
      Antigravity CLI) per the WARP-0802 review notes.
required_evidence: [unit]
rollback: git revert; additive - a new packs/cursor tree (engine copy + Cursor wrapper), a cursor
  entry in .veldo/packs.json, a selftest block, and this spec, plus the bundled PLAN-0008 text
  reconciliation; no protected path; pure stdlib, no network.
---

## Intent

The pattern-setter (W2) proved the mechanism; W3 stands up the first real peer pack for another
tool. Per the founder decision, each pack is a committed, self-contained directory - the whole
engine copied in plus that tool's thin driver - and the drift-check keeps every copy byte-identical
to the one canonical source. Cursor is the first of the six non-Claude tools, so it is where the
drift-check stops being a trivial self-reference and becomes cross-pack load-bearing.

## Context

W3 of PLAN-0008, depends on the Claude pack (W2). It uses the WARP-0801 assembler to copy the engine
and the canonical AGENTS.md into packs/cursor, then adds the Cursor driver: an always-on .cursor/rules
rule pointing at AGENTS.md and the loop, the skills (SKILL.md, reused) and agents (reused), and the
guard - a git pre-push hook invoking scripts/veldo-guard.sh plus the CI check, with a .cursor/hooks
hook for earlier feedback. Cursor converged on the AGENTS.md + .cursor/rules + SKILL.md model, so the
port is a thin re-path, not a rewrite.

## Notes

Cursor has no native pre-push hook, so the guaranteed enforcement is the git pre-push hook plus the
CI required status check (both shipped); the .cursor/hooks hook is early feedback, not the gate
(NG2: enforcement is never weakened to fit a tool). The engine copy is 139 files held byte-identical
by the drift-check - the same discipline as the two capabilities.yaml copies, now generalized to a
whole pack. This commit also reconciles the PLAN-0008 text flagged by the WARP-0802 review (the W2
title stated "restructure" but option B ships no restructure; every Gemini CLI mention is retargeted
to Antigravity CLI, since Gemini CLI folded into Antigravity in 2026 and W6 targets the agy command);
the plan edit bundles into this impl commit because a plans-only commit trips policy_check and cannot
ride an evidence-only commit.
