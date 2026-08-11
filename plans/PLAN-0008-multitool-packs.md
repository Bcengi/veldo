---
schema: veldo.plan/v1
id: PLAN-0008
title: VELDO multi-tool packs - seven self-contained packs (Claude, Cursor, Codex, Copilot, Antigravity, OpenCode, Aider) assembled from one engine, equal enforcement
kind: mvp
status: released
revision: 1
owner: dmitry
approved_by: dmitry
approved_at: 2026-07-18T15:31:50Z
risk: standard

outcomes:
  - id: O1
    becomes_true: A developer runs the full VELDO loop natively in any of the seven tools -
      Claude Code, Cursor, Codex CLI, GitHub Copilot, Antigravity CLI, OpenCode, and Aider - stating
      intent, letting the tool build, requiring proof, getting an independent verdict, and
      merging when green, using that tool's own primitives.
    measure: the cross-pack conformance selftest drives every pack through spec to gate to proof
      to verdict and passes; a fresh repo set up with each pack runs that tool's VELDO entrypoints
      and completes one loop end to end
  - id: O2
    becomes_true: The enforcement invariant is identical and never weaker on any tool - no
      change reaches the trunk without a passing commit-bound verdict and protected-path
      approval - including on tools with a weak or absent local hook (Copilot, Aider).
    measure: for every pack the conformance harness proves an unproven push is BLOCKED (a local
      hook where the tool has one, the git pre-push hook on all, and policy_check.py in CI) and a
      proven push is allowed; no pack has a green path around the invariant
  - id: O3
    becomes_true: Each pack is SELF-CONTAINED - a complete drop-in with everything in it (the
      VELDO engine plus that tool's own wrapper) so a team installs one pack and needs nothing
      else - and yet there is no drift, because every pack's engine is ASSEMBLED from ONE
      canonical source and the gate proves the assembled copies byte-identical.
    measure: each pack directory contains a full working engine (gate, policy_check, validate,
      the .veldo substrate, runners, CI) plus its wrapper; the drift-check in the gate fails if
      any pack's engine diverges from the canonical source or from the other packs
  - id: O4
    becomes_true: Each pack feels native, expressed in that tool's own configuration and command
      idiom, and Claude Code is a peer pack like the rest, not a privileged base.
    measure: each pack loads in its tool from that tool's native files only, and the Claude pack
      sits alongside the others under the same pack layout, assembled the same way

non_goals:
  - id: NG1
    text: Reimplementing the engine per tool by hand. There is ONE canonical engine source; each
      pack's engine is assembled from it, never hand-edited per pack, and the drift-check
      enforces that. Only the driver wrapper (agents, skills or commands, guard trigger, the
      tool's instruction file) is authored per pack.
  - id: NG2
    text: Weakening enforcement to fit a tool's limitations. A tool with a weak or absent local
      hook still gets the git pre-push hook plus the CI required status check; no honor-system
      path is ever introduced.
  - id: NG3
    text: Tools beyond the seven named. The pack contract and the assembler are built so an
      eighth (Windsurf, Zed, Continue, JetBrains AI) is a thin additive pack, but none are in
      scope now.
  - id: NG4
    text: Publishing each tool's native marketplace listing (a Cursor plugin listing, a Copilot
      Marketplace extension, a published Antigravity extension). The packs are assembled in this one
      repo and shipped as drop-in distributions; per-tool marketplace publishing is a deferred
      follow-on (founder-approved deferral).
  - id: NG5
    text: Wiring the CLI packs (Codex, Antigravity, OpenCode, Aider) as headless veldo fleet workers.
      This plan delivers the VELDO method, gate, and enforcement on each tool; the autonomous
      parallel headless-worker role stays a CLI-agent capability (PLAN-0007) and wiring the new
      CLI agents into it is a follow-on.

constraints:
  - id: C1
    text: Every item stays proportionate and is built through VELDO itself, with the same gate,
      proof, and independent review.
  - id: C2
    text: ONE canonical engine, self-contained packs. The tool-agnostic engine (scripts/verify.sh,
      .veldo/policy_check.py, .veldo/validate.py, the whole .veldo substrate, the runners, the CI
      workflow, capabilities.yaml) has a single canonical source; each pack is ASSEMBLED from it
      into a complete self-contained bundle (engine plus that tool's wrapper plus the canonical
      AGENTS.md), and a gate drift-check asserts every pack's assembled engine is byte-identical
      to the canonical source and to the other packs. Self-contained for the user, single source
      of truth for us, red gate the instant they diverge.
  - id: C3
    text: Enforcement is NEVER weaker on any tool than on Claude Code. Use the tool's local hook
      where it has one (Codex, Antigravity, OpenCode hooks; Cursor onPreCommit), and ALWAYS also
      install the git pre-push hook and rely on the CI required status check (policy_check.py runs
      identically server-side) as the universal backstop. For the IDE cluster (Cursor, Copilot)
      and for hook-skipping tools (Aider defaults to no-verify, so its pack must enable it) the
      git pre-push hook plus CI are what GUARANTEE parity with the CLI agents.
  - id: C4
    text: The method and operating instructions live ONCE in a canonical AGENTS.md that is
      bundled into every pack; each tool's own instruction file (CLAUDE.md, the Antigravity/agy
      instruction file, .github/copilot-instructions.md, Aider CONVENTIONS.md) references or includes it rather
      than restating it, so there is a single source of truth for the method inside each pack.
  - id: C5
    text: Each pack is NATIVE IDIOM and generic - expressed in that tool's own primitives, with
      no hardcoding to one repo's layout; a pack lays down or documents its tool config the same
      disciplined way /veldo:init lays the engine.
  - id: C6
    text: The seven targets span a CLI-vs-IDE axis, treated deliberately. The pack applies
      uniformly to all seven; ENFORCEMENT for the IDE cluster (Cursor, Copilot) and thin tools
      (Aider) rests on the git pre-push plus CI backstop; the autonomous headless FLEET-worker
      role is a CLI-agent capability only (NG5), so an IDE pack delivers method, gate, and
      enforcement but not the fleet-worker role, by design.

feature_tree:
  - id: F1
    title: Canonical engine, pack assembler, and canonical AGENTS.md - one source, a mechanism
      that assembles a self-contained pack from it, and a gate drift-check that keeps every pack
      byte-identical to the source
    outcome_refs: [O3, O4]
  - id: F2
    title: The seven self-contained packs - Claude (as a peer), Cursor, Codex, Copilot, Antigravity,
      OpenCode, Aider - each engine plus native wrapper, assembled from the one source
    outcome_refs: [O1, O2, O4]
  - id: F3
    title: Universal enforcement backstop - the git pre-push hook and CI required status check
      that guarantee the invariant on every pack, and carry parity for the IDE and thin tools
    outcome_refs: [O2]
  - id: F4
    title: Cross-pack conformance - a harness that drives each pack through the whole loop, proves
      the guard blocks an unproven push, and proves no pack's engine has drifted
    outcome_refs: [O1, O2, O3]
  - id: F5
    title: Release - a version bump distributing the seven-pack multi-tool support
    outcome_refs: [O1]

work:
  - item: W1
    spec: WARP-0801
    title: Canonical engine + pack assembler + canonical AGENTS.md + drift-check - designate the
      single canonical engine source, extract the tool-neutral method and operating instructions
      into a canonical AGENTS.md, define the self-contained pack layout and the pack contract, build
      the assembler that produces a pack (engine + wrapper + AGENTS.md) from the source, and add the
      gate drift-check asserting every assembled pack engine is byte-identical to the source
    feature_refs: [F1, F3]
    depends_on: []
    order: 10
  - item: W2
    spec: WARP-0802
    title: Claude pack as a peer - recognize the existing packs/claude/ as the Claude pack (its wrapper is
      agents, skills, the guard hook; its engine is the canonical source in-place) and wire the pack
      manifest + drift-check so Claude is a peer held to the engine like the rest; no restructure now,
      the rename to packs/claude is deferred to the release (W10)
    feature_refs: [F2]
    depends_on: [WARP-0801]
    order: 20
  - item: W3
    spec: WARP-0803
    title: Cursor pack (IDE cluster) - a self-contained pack with AGENTS.md, .cursor/rules/*.mdc,
      SKILL.md skills, .cursor/hooks onPreCommit mapping the guard, and MCP, plus the engine and
      the universal git pre-push hook; enforcement parity via git pre-push plus CI
    feature_refs: [F2]
    depends_on: [WARP-0802]
    order: 30
  - item: W4
    spec: WARP-0804
    title: Codex CLI pack (CLI cluster) - a self-contained pack with layered AGENTS.md,
      .codex/config.toml layers and profiles, lifecycle hooks.json mapping the guard as a local
      headless hook, skills and MCP, plus the engine and the git pre-push hook
    feature_refs: [F2]
    depends_on: [WARP-0802]
    order: 40
  - item: W5
    spec: WARP-0805
    title: GitHub Copilot pack (IDE cluster) + hook-less enforcement - a self-contained pack with
      .github/copilot-instructions.md pointing at AGENTS.md, .github/prompts/*.prompt.md,
      .github/agents/*.agent.md, and MCP; Copilot has no local hook, so enforcement is the git
      pre-push hook plus the CI required status check (ci_gate_check) as the backstop
    feature_refs: [F2, F3]
    depends_on: [WARP-0802]
    order: 50
  - item: W6
    spec: WARP-0806
    title: Antigravity CLI pack (CLI cluster) - a self-contained pack for the agy command (Gemini CLI
      folded into Antigravity CLI in 2026) referencing the canonical AGENTS.md via agy's extension
      model (config, commands, agents, hooks - the exact agy mechanism researched at build) mapping
      the guard, plus the engine and the git pre-push hook
    feature_refs: [F2]
    depends_on: [WARP-0802]
    order: 60
  - item: W7
    spec: WARP-0807
    title: OpenCode pack (CLI cluster) - a self-contained pack with AGENTS.md (project and global),
      primary and subagents, custom slash-commands, and MCP, plus the engine, a local hook where
      OpenCode supports one, and the git pre-push hook
    feature_refs: [F2]
    depends_on: [WARP-0802]
    order: 70
  - item: W8
    spec: WARP-0808
    title: Aider pack (CLI cluster, thin primitives) - a self-contained pack with CONVENTIONS.md
      carrying the method (loaded read-only via .aider.conf.yml) and the workflows as documented
      or scripted prompts; because Aider skips git hooks by default, the pack sets
      git-commit-verify true AND relies on the git pre-push hook plus CI as the real enforcement
    feature_refs: [F2, F3]
    depends_on: [WARP-0802]
    order: 80
  - item: W9
    spec: WARP-0809
    title: Cross-pack conformance selftest - a table-driven harness (part of scripts/selftest.py)
      that drives EACH pack through the full VELDO loop against its assembled engine (spec, gate,
      proof, verdict), asserts the guard BLOCKS an unproven push on each (local hook where present,
      git pre-push, and policy_check.py as CI would run it) while a proven push is allowed, and
      asserts the engine drift-check holds across all packs, so portability and no-drift are proven
      by construction
    feature_refs: [F4]
    depends_on: [WARP-0802, WARP-0803, WARP-0804, WARP-0805, WARP-0806, WARP-0807, WARP-0808]
    order: 90
  - item: W10
    spec: WARP-0810
    title: Release VELDO multi-tool packs v1 - bump the packs/claude/pack version, record the seven packs
      in the capability manifest, ship the assembled drop-in distributions, update docs, and mark
      the plan released once the release check is green
    feature_refs: [F5]
    depends_on: [WARP-0809]
    order: 100

regression:
  journeys:
    - id: RJ1
      title: The enforcement invariant holds on every pack across both clusters - an unproven push
        is blocked and a proven push allowed on all seven (local hook where present, git pre-push
        everywhere, policy_check.py in CI)
      activation: {when: after:WARP-0809}
      owner_spec: WARP-0809
      profiles: [per_spec, release]
      suite: cross-pack conformance selftest
    - id: RJ2
      title: No pack's engine has drifted - every pack's assembled engine is byte-identical to the
        canonical source and to the other packs
      activation: {when: after:WARP-0801}
      owner_spec: WARP-0801
      profiles: [per_spec, release]
      suite: engine drift-check
    - id: RJ3
      title: The existing VELDO gate stays green across every item (selftest passes, contracts pass)
        so the port never regresses the home repo
      activation: {when: start}
      profiles: [per_spec, release]
      suite: scripts/verify.sh (selftest slot)

release:
  milestone: VELDO multi-tool packs v1 - seven self-contained packs (Claude, Cursor, Codex, Copilot,
    Antigravity, OpenCode, Aider) assembled from one engine, native idiom, identical enforcement
  version: plugin 3.4.0
  mode: continuous
  require_all_work_shipped: true
  require_full_regression: true
  rollback: each pack is an additive self-contained directory assembled from the canonical engine;
    removing one pack leaves the canonical source and the other packs intact, and reverting the
    release commit withdraws the version bump
  observation:
    duration: set up each pack in a scratch repo and run its conformance journey before the version
      is defaulted on

open_decisions: []
---

## Intent

VELDO already runs as a Claude Code pack over a tool-agnostic engine (the gate, policy_check,
validate, the whole .veldo substrate, the runners, and the CI workflow are plain files plus stdlib
Python with zero Claude dependency; only the driver wrapper is Claude-specific). This plan makes
VELDO run natively on seven tools, delivered as SEVEN SELF-CONTAINED PACKS - each a complete drop-in
with everything in it - so a team installs one pack and needs nothing else. Claude Code becomes a
peer pack like the rest, not a privileged base.

The self-contained requirement is reconciled with single-source-of-truth the way the repo already
keeps its two capability files in lockstep: there is ONE canonical engine source, every pack's
engine is ASSEMBLED from it, and the gate proves the assembled copies byte-identical. Self-contained
for the user; one source for us; a red gate the instant any pack drifts.

## Decisions baked in (founder-approved 2026-07-18)

Seven packs: Claude, Cursor, Codex CLI, GitHub Copilot, Antigravity CLI, OpenCode, Aider. Self-contained
packs assembled from one canonical engine with a byte-identical drift-check. Claude is a peer pack.
Packs are assembled in this one repo and shipped as drop-in distributions; per-tool marketplace
publishing is deferred. Native-idiom adapters over the shared engine (not a lowest-common-denominator
shim). Fleet-worker wiring for the CLI packs is a follow-on (NG5).

## The CLI-vs-IDE axis

The seven span a real axis. The CLI-agent cluster - Codex, Antigravity, OpenCode, Aider, with Claude as
the base - is terminal, headless-capable, git-native. The IDE cluster - Cursor (a VS Code fork,
GUI-first) and Copilot (a VS Code extension plus CLI plus cloud agent) - is editor-first. The pack
applies uniformly to all seven; enforcement for the IDE cluster and for hook-skipping Aider rests on
the git pre-push plus CI backstop; and the autonomous headless fleet (veldo fleet N) is a CLI-agent
capability, so an IDE pack delivers the method, gate, and enforcement but not the fleet-worker role,
by design.

## Ordered delivery rationale

W1 is the root: the canonical engine, the pack assembler, the canonical AGENTS.md, and the
drift-check must exist before any pack is assembled, or a fork is baked in. The seven pack items
(W2 to W8) then proceed in PARALLEL - each is an independent wrapper over the one engine, no
cross-dependency, a natural fleet fan-out spanning both clusters. W9 (conformance) is the join point:
it cannot run until every pack exists, and it converts "ported" into a gate-enforced property (each
pack drives the loop, the guard blocks an unproven push, and no engine has drifted). W10 releases
once conformance is green.

## Revisions

Revision 1 (2026-07-18): created from the multi-tool-port design and approved by the founder - one
canonical engine assembled into seven self-contained packs (Claude as a peer), native-idiom wrappers
across the CLI and IDE clusters, a universal git-pre-push-plus-CI enforcement backstop, and a
cross-pack conformance selftest proving the loop runs, the guard blocks, and no engine drifts.
