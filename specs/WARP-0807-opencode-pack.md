---
schema: veldo.spec/v1
id: WARP-0807
title: OpenCode pack - CLI-cluster self-contained pack, guard fed the JSON payload
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0008
work: W7
plan_revision: 1
depends_on: [WARP-0802]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A self-contained OpenCode pack exists at packs/opencode - the full canonical engine (139
      files) copied in byte-identical, the canonical AGENTS.md, and an OpenCode driver wrapper
      (opencode.json pointing instructions at AGENTS.md, a .opencode/command loop command, the reused
      skills and agents) - a complete grab-and-go directory.
  - id: AC2
    text: The VELDO push gate holds for OpenCode with no honor-system path (NG2) - the OpenCode
      tool.execute.before hook (.opencode/veldo-guard-hook.sh, wired via opencode.json) and the git
      pre-push hook (hooks/pre-push) both feed the shared engine guard the JSON payload it parses
      (tool_input.command on stdin, the WARP-0803 fix from the start, not an env var), backed by the
      CI required status check. A push at an unproven HEAD is blocked; commands are json.dumps-safe.
  - id: AC3
    text: The pack is declared in .veldo/packs.json and the drift-check holds the opencode pack's
      engine byte-identical to the canonical source (the sixth pack); check_pack_drift and the
      selftest report it drift-free and a drifted copy fails by name.
  - id: AC4
    text: Reuse, not reinvention - the engine, AGENTS.md, skills, and agents are copied from the one
      canonical source (identical); only the thin OpenCode driver (opencode.json, the hook, the
      command, hooks/pre-push) is authored per tool.
  - id: AC5
    text: A selftest asserts the opencode pack conforms (engine drift-free) and carries its OpenCode
      wrapper (opencode.json, the guard hooks feeding the JSON payload, the command, skills, agents,
      AGENTS.md), non-tautologically. This commit also reconciles the PLAN-0008 pack-item depends_on
      (W3-W8 from WARP-0801 to WARP-0802, matching the specs and the true dependency on the
      pattern-setter), per the WARP-0806 review note.
required_evidence: [unit]
rollback: git revert; additive - a new packs/opencode tree (engine copy + OpenCode wrapper), an
  opencode entry in .veldo/packs.json, a selftest block, and this spec, plus the bundled PLAN-0008
  depends_on reconciliation; no protected path; pure stdlib, no network.
---

## Intent

W7 adds the OpenCode pack, another CLI-cluster tool. OpenCode reads AGENTS.md and uses an
opencode.json config with a tool-execution hook, so the port is a thin re-path: the canonical
AGENTS.md carries the method, opencode.json wires the instructions pointer and the before-execute
hook, and the guard is enforced the same way as every pack (git pre-push + CI, with the tool hook
for early feedback).

## Context

W7 of PLAN-0008, depends on the Claude pack (W2). Same committed-self-contained model: the engine
and AGENTS.md copied into packs/opencode, the skills and agents reused, the copy held identical by
the drift-check. The OpenCode driver is opencode.json + the hook + a command.

## Notes

The WARP-0803 enforcement fix is applied from the start: both the OpenCode tool.execute.before hook
and the git pre-push hook feed scripts/veldo-guard.sh the JSON payload it parses on stdin (the git
hook overrides git's ref-line stdin; the OpenCode hook builds the JSON with json.dumps, injection-
safe). The guaranteed gate is the git pre-push hook plus the CI required status check; the OpenCode
hook is early feedback (NG2).

EXECUTABLE-MODE FIX (from this spec's own first review): git silently SKIPS a non-executable hook,
so a committed pre-push hook at mode 644 fails OPEN (an unproven push lands) even after the documented
`git config core.hooksPath hooks`. The assembler was dropping the exec bit (shutil.copyfile) and the
authored hooks were committed 644, systemically across all packs, and engine_drift ignored mode so it
went undetected. Fixed here for the whole pack system: assemble_pack now copies mode (shutil.copy),
engine_drift is MODE-AWARE (a content-identical but non-executable engine-script copy is reported as
"mode" drift, so the gate catches it), all committed pack git pre-push hooks and guard scripts are
now executable, and the selftest asserts every pack's hook + guard is executable and that a stripped
exec bit is caught as drift. This retroactively corrects the already-shipped Cursor/Codex/Copilot/
Antigravity packs too. The server-side CI required status check was always the unaffected backstop.

This commit bundles the plan-text reconciliation the WARP-0806 review
flagged: the PLAN-0008 pack-item depends_on for W3-W8 changes from WARP-0801 (the raw engine) to
WARP-0802 (the pattern-setter that built the manifest and drift-check), matching the pack specs and
the true dependency, while W2 correctly stays on WARP-0801; the plan edit bundles into this impl
commit because a plans-only commit trips policy_check. The exact opencode.json hook schema is a
fast-moving surface; the guaranteed enforcement does not depend on it.
