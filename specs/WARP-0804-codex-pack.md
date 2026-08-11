---
schema: veldo.spec/v1
id: WARP-0804
title: Codex CLI pack - self-contained pack for the CLI cluster, guard fed the JSON payload
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0008
work: W4
plan_revision: 1
depends_on: [WARP-0802]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A self-contained Codex CLI pack exists at packs/codex - the full canonical engine (139
      files) copied in byte-identical, the canonical AGENTS.md, and a Codex driver wrapper
      (.codex/config.toml pointing at AGENTS.md and wiring the hook, the reused skills and agents) -
      a complete grab-and-go directory, per the committed-copy-per-pack decision.
  - id: AC2
    text: The VELDO push gate holds for Codex with no honor-system path (NG2) - a git pre-push hook
      (packs/codex/hooks/pre-push) and the Codex before-shell lifecycle hook (.codex/veldo-guard-hook.sh,
      wired via .codex/config.toml and .codex/hooks.json) both feed the shared engine guard
      (scripts/veldo-guard.sh) the JSON payload it parses (tool_input.command on stdin, NOT an env
      var, applying the WARP-0803 fix), backed by the CI required status check. A push at an unproven
      HEAD is blocked; a command is built with json.dumps so it cannot inject.
  - id: AC3
    text: The pack is declared in .veldo/packs.json and the drift-check holds the codex pack's engine
      byte-identical to the canonical source (the third pack, so the cross-pack drift-check now spans
      three); check_pack_drift and the selftest report it drift-free and a drifted copy fails by name.
  - id: AC4
    text: Reuse, not reinvention - the engine, AGENTS.md, skills, and agents are copied from the one
      canonical source (identical); only the thin Codex driver (.codex/config.toml, the hook script,
      the git pre-push hook, .codex/hooks.json) is authored per tool.
  - id: AC5
    text: A selftest asserts the codex pack conforms (engine drift-free) and carries its Codex wrapper
      (config.toml, the guard hooks feeding the JSON payload, the skills, the agents, AGENTS.md),
      non-tautologically (a mutated engine file in a pack copy is caught as drift, and the hooks feed
      the guard the JSON payload rather than an ignored env var).
required_evidence: [unit]
rollback: git revert; additive - a new packs/codex tree (engine copy + Codex wrapper), a codex entry
  in .veldo/packs.json, a selftest block, and this spec; no protected path; pure stdlib, no network.
---

## Intent

W4 adds the first CLI-cluster pack. Codex CLI reads AGENTS.md before any work (walking up from the
cwd, layered), so the port is a thin re-path: the canonical AGENTS.md carries the method, a
.codex/config.toml wires Codex's own knobs and the before-shell hook, and the guard is enforced the
same way as every pack - a git pre-push hook plus CI, with the tool's native hook for early feedback.

## Context

W4 of PLAN-0008, depends on the Claude pack (W2), sibling of the Cursor pack (W3). Same
committed-self-contained model: the WARP-0801 assembler copies the engine and AGENTS.md into
packs/codex, the skills and agents are reused verbatim, and the drift-check holds the copy identical
to the source. The Codex driver is the config.toml + the hook wiring.

## Notes

The enforcement fix learned in W3 is applied from the start: scripts/veldo-guard.sh reads the command
from a JSON payload on stdin (tool_input.command) and ignores any CMD env var, so both the git
pre-push hook and the Codex before-shell hook FEED the guard that JSON payload (the pre-push hook
overrides git's ref-line stdin; the Codex hook builds the JSON with json.dumps, injection-safe). The
git pre-push hook plus the CI required status check are the guaranteed gate; the .codex hook is early
feedback (NG2: enforcement is never weakened to fit a tool). The exact Codex config.toml and hook
schema are a fast-moving surface; the guaranteed enforcement (git pre-push + CI) does not depend on
the editor-hook format. The engine copy is 139 files held byte-identical by the drift-check.
