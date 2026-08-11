---
schema: veldo.spec/v1
id: WARP-0808
title: Aider pack - the thin-primitives case, git-commit-verify plus the git pre-push and CI gate
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0008
work: W8
plan_revision: 1
depends_on: [WARP-0802]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A self-contained Aider pack exists at packs/aider - the full canonical engine (139 files)
      copied in byte-identical, the canonical AGENTS.md, and an Aider driver wrapper (CONVENTIONS.md,
      .aider.conf.yml, the reused skills and agents as reference) - a complete grab-and-go directory.
  - id: AC2
    text: The VELDO invariant is enforced with no honor-system path even though Aider is thin and
      defaults to --no-verify (skips git hooks), NG2 - .aider.conf.yml sets git-commit-verify true so
      Aider stops bypassing hooks, and the load-bearing gate is the git pre-push hook
      (packs/aider/hooks/pre-push, EXECUTABLE, feeding the guard the JSON payload on stdin) plus the
      CI required status check. A push at an unproven HEAD is blocked by the git hook.
  - id: AC3
    text: The pack is declared in .veldo/packs.json and the drift-check (mode-aware) holds the aider
      pack's engine byte-identical to the canonical source (the seventh and final pack); check_pack_drift
      and the selftest report it drift-free and a drifted or non-executable copy fails by name.
  - id: AC4
    text: Reuse, not reinvention - the engine, AGENTS.md, skills, and agents are copied from the one
      canonical source (identical); only the thin Aider driver (CONVENTIONS.md, .aider.conf.yml,
      hooks/pre-push) is authored per tool.
  - id: AC5
    text: A selftest asserts the aider pack conforms (engine drift-free) and carries its Aider wrapper
      (CONVENTIONS.md, .aider.conf.yml with git-commit-verify true, the EXECUTABLE git pre-push hook
      feeding the JSON payload, the skills, the agents, AGENTS.md), non-tautologically.
required_evidence: [unit]
rollback: git revert; additive - a new packs/aider tree (engine copy + Aider wrapper), an aider entry
  in .veldo/packs.json, a selftest block, and this spec; no protected path; pure stdlib, no network.
---

## Intent

W8 is the last of the seven packs and the thinnest tool. Aider has no agent-hook framework and, by
default, commits with --no-verify (it skips git hooks), so it is the sharpest test of "enforcement is
never weaker on any tool" (NG2). The pack answers it with two moves: set git-commit-verify true so
Aider stops bypassing hooks, and make the git pre-push hook plus the CI required status check the
load-bearing gate. Aider reads AGENTS.md and CONVENTIONS.md (both loaded via .aider.conf.yml), so the
method is in context; the gate is git-level.

## Context

W8 of PLAN-0008, depends on the Claude pack (W2), the last CLI-cluster pack. Same committed-self-
contained model: the engine and AGENTS.md copied into packs/aider, the skills and agents reused as
reference (Aider has no agent runtime), the copy held identical by the mode-aware drift-check. The
Aider driver is CONVENTIONS.md + .aider.conf.yml + the git pre-push hook.

## Notes

Because Aider defaults to --no-verify, the pack must both enable git-commit-verify (so Aider does not
bypass commit-time hooks) and rely on the git pre-push hook for the push gate. The git pre-push hook
is committed EXECUTABLE (the WARP-0807 exec-mode fix: git silently skips a non-executable hook), and
it feeds scripts/veldo-guard.sh the JSON payload it parses on stdin. The guaranteed enforcement is the
git pre-push hook plus the CI required status check; there is no in-tool hook to lean on, which is the
whole point of the thin-tool case. The engine copy is 139 files held byte-identical (content AND
mode) by the drift-check. The exact .aider.conf.yml keys are a fast-moving surface; git-commit-verify
and read are documented Aider options, and the guaranteed gate does not depend on the tool config.
