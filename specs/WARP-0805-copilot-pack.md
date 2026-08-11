---
schema: veldo.spec/v1
id: WARP-0805
title: GitHub Copilot pack - hook-less enforcement via git pre-push plus the CI required check
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0008
work: W5
plan_revision: 1
depends_on: [WARP-0802]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A self-contained GitHub Copilot pack exists at packs/copilot - the full canonical engine
      (139 files) copied in byte-identical, the canonical AGENTS.md, and a Copilot driver wrapper
      (.github/copilot-instructions.md always-injected, .github/prompts, .github/agents, the reused
      skills) - a complete grab-and-go directory.
  - id: AC2
    text: The VELDO invariant is enforced with NO honor-system path even though Copilot has NO local
      editor pre-push hook (the hook-less case, NG2) - the git pre-push hook (packs/copilot/hooks/pre-push)
      feeds the shared engine guard the JSON payload it parses (tool_input.command on stdin) and the
      CI required status check (.github/workflows/veldo-gate.yml, in the engine) gates the trunk
      server-side; copilot-instructions.md documents enabling both. A push at an unproven HEAD is
      blocked locally by the git hook, and the trunk cannot advance without the required CI check.
  - id: AC3
    text: The pack is declared in .veldo/packs.json and the drift-check holds the copilot pack's engine
      byte-identical to the canonical source (the fourth pack); check_pack_drift and the selftest
      report it drift-free and a drifted copy fails by name.
  - id: AC4
    text: Reuse, not reinvention - the engine, AGENTS.md, skills, and agents are copied from the one
      canonical source (identical); only the thin Copilot driver (.github/copilot-instructions.md,
      the prompt file, the git pre-push hook) is authored per tool.
  - id: AC5
    text: A selftest asserts the copilot pack conforms (engine drift-free) and carries its Copilot
      wrapper (copilot-instructions.md, the prompt, the git pre-push hook feeding the JSON payload,
      the skills, the agents, AGENTS.md), non-tautologically (a mutated engine file in a pack copy is
      caught as drift, and the pre-push hook feeds the guard the JSON payload rather than an env var).
required_evidence: [unit]
rollback: git revert; additive - a new packs/copilot tree (engine copy + Copilot wrapper), a copilot
  entry in .veldo/packs.json, a selftest block, and this spec; no protected path; pure stdlib, no network.
---

## Intent

W5 adds the pack for the tool with the weakest local hook surface: GitHub Copilot has no editor
pre-push hook. It is the proving ground for "enforcement is never weakened to fit a tool" (NG2) - a
hook-less tool still gets the git pre-push hook plus a required CI status check, so the trunk is no
less protected than for a tool with a local hook. Copilot reads AGENTS.md (the coding agent does
too) and always injects .github/copilot-instructions.md, so the method is in front of the developer
and the agent, and the gate is git-level and server-side.

## Context

W5 of PLAN-0008, depends on the Claude pack (W2), sibling of Cursor (W3) and Codex (W4). Same
committed-self-contained model: the engine and AGENTS.md copied into packs/copilot, the skills and
agents reused, the copy held identical by the drift-check. The Copilot driver is the always-injected
instructions file, a prompt file for the loop, and the git pre-push hook.

## Notes

The distinctive feature is HOOK-LESS enforcement. There is no editor hook to wire; the guaranteed
gate is (1) the git pre-push hook (hooks/pre-push), which feeds scripts/veldo-guard.sh the JSON
payload it parses on stdin (the WARP-0803 fix - not an env var the guard ignores), and (2) the CI
workflow .github/workflows/veldo-gate.yml made a REQUIRED status check in branch protection, which
gates the coding agent's PRs server-side where a local hook cannot reach. copilot-instructions.md
documents enabling both. The engine copy is 139 files held byte-identical by the drift-check. The
Copilot custom-agent (.agent.md) and prompt-file surfaces are fast-moving; the guaranteed enforcement
does not depend on them.
