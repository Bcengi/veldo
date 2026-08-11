---
schema: veldo.spec/v1
id: WARP-0806
title: Antigravity CLI (agy) pack - the plugin model, retargeted from the wound-down Gemini CLI
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0008
work: W6
plan_revision: 1
depends_on: [WARP-0802]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A self-contained Antigravity CLI (agy) pack exists at packs/antigravity - the full canonical
      engine (139 files) copied in byte-identical, the canonical AGENTS.md, and an agy plugin wrapper
      (plugin.json manifest, hooks.json, rules/veldo.md, the reused skills and agents) - a complete
      grab-and-go directory. It targets the agy command, the successor to the wound-down Gemini CLI,
      NOT Gemini CLI (which shut down 2026-06-18).
  - id: AC2
    text: The VELDO push gate holds for agy with no honor-system path (NG2) - the agy before-tool-call
      lifecycle hook (hooks.json -> veldo-guard-hook.sh) and the git pre-push hook (hooks/pre-push)
      both feed the shared engine guard the JSON payload it parses (tool_input.command on stdin, the
      WARP-0803 fix from the start, not an env var), backed by the CI required status check. A push
      at an unproven HEAD is blocked; commands are built with json.dumps so they cannot inject.
  - id: AC3
    text: The pack is declared in .veldo/packs.json and the drift-check holds the antigravity pack's
      engine byte-identical to the canonical source (the fifth pack); check_pack_drift and the
      selftest report it drift-free and a drifted copy fails by name.
  - id: AC4
    text: Reuse, not reinvention - the engine, AGENTS.md, skills, and agents are copied from the one
      canonical source (identical); only the thin agy driver (plugin.json, hooks.json,
      veldo-guard-hook.sh, rules/veldo.md, hooks/pre-push) is authored, matching agy's plugin model
      (plugin.json + hooks.json + rules/ + skills/ + agents/).
  - id: AC5
    text: A selftest asserts the antigravity pack conforms (engine drift-free) and carries its agy
      wrapper (plugin.json, hooks.json, the guard hooks feeding the JSON payload, rules, skills,
      agents, AGENTS.md), non-tautologically (a mutated engine file in a pack copy is caught as drift,
      and the hooks feed the guard the JSON payload rather than an ignored env var).
required_evidence: [unit]
rollback: git revert; additive - a new packs/antigravity tree (engine copy + agy wrapper), an
  antigravity entry in .veldo/packs.json, a selftest block, and this spec; no protected path; pure
  stdlib, no network.
---

## Intent

W6 was originally scoped for Gemini CLI, but Google folded Gemini CLI into the Antigravity CLI (the
agy command) in 2026 and shut Gemini CLI down on 2026-06-18, so this pack targets agy. agy is
agent-first and its plugin model is close to Claude's - a plugin.json manifest with optional
hooks.json, rules/, skills/, and agents/ - so the VELDO port is a clean re-path onto that model.

## Context

W6 of PLAN-0008, depends on the Claude pack (W2), a CLI-cluster sibling of Codex (W4). The agy
extension model was researched at build time (agy launched after the model's training cutoff):
a plugin is a required plugin.json plus optional mcp_config.json, hooks.json, skills/, agents/, and
rules/ directories, with JSON lifecycle hooks (before a tool call, after a model call, at loop stop).
The VELDO agy pack maps directly: plugin.json, a before-tool-call hook that gates pushes, rules/
pointing at AGENTS.md, and the reused skills and agents.

## Notes

The enforcement fix learned in W3 is applied from the start: scripts/veldo-guard.sh reads the command
from a JSON payload on stdin (tool_input.command) and ignores any env CMD, so both the agy
before-tool-call hook and the git pre-push hook FEED the guard that JSON payload (the git hook
overrides git's ref-line stdin; the agy hook builds the JSON with json.dumps, injection-safe). The
guaranteed gate is the git pre-push hook plus the CI required status check; the agy hook is early
feedback (NG2). agy's exact plugin.json and hooks.json schema is a fast-moving 2026 surface; the
guaranteed enforcement does not depend on the editor-hook format. The engine copy is 139 files held
byte-identical by the drift-check.
