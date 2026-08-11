# Veldo multi-tool packs

Veldo runs natively on seven AI coding tools. There is ONE BASE, `engine/`, and each pack EXTENDS it
with what its tool needs: the base carries the gate, the guard, the validators, the whole `.veldo`
substrate, the runners and the CI workflow, and a pack carries only that tool's driver, rules and
skills. You take the base and one pack.

The seven packs:

| Pack | Tool | Native driver | Local early gate |
|------|------|---------------|------------------|
| `packs/claude` | Claude Code | plugin (role agents, pipeline skills, guard hook) | PreToolUse guard hook |
| `packs/cursor` | Cursor | `.cursor/rules` (always on) + `.cursor/hooks` | Cursor hook |
| `packs/codex` | Codex CLI | `AGENTS.md` + `.codex/config.toml` + `.codex/hooks.json` | Codex before-shell hook |
| `packs/copilot` | GitHub Copilot | `.github/copilot-instructions.md` + prompts | none (git pre-push + CI) |
| `packs/antigravity` | Antigravity CLI (`agy`) | `plugin.json` + `hooks.json` + `rules/` | agy before-tool-call hook |
| `packs/opencode` | OpenCode | `opencode.json` + `.opencode` hook + command | OpenCode tool.execute.before hook |
| `packs/aider` | Aider | `CONVENTIONS.md` + `.aider.conf.yml` | none (git pre-push + CI) |

## One engine, assembled seven ways

There is one base (`engine/`) and one canonical `AGENTS.md` carrying the method and operating
contract. A pack does NOT carry its own copy of the base, and that is deliberate: seven copies is
seven things to drift. `.veldo/pack.py` composes base plus pack into the artifact a user installs. The manifest that
declares the seven packs, and the conformance harness that drives each one, are part of the
source repository and are not shipped in the release: they describe our seven packs, not yours.

What the gate enforces is the property composition leaves open: a pack must never ship an engine file
that DIFFERS from the base. Absent is correct, because the base provides it. Different is a silent
fork, and the selftest names the pack and the file. That check is proven able to fail, against a pack
carrying one mutated engine file, rather than asserted to be present.

## The enforcement invariant (never weaker on any tool)

No change reaches the trunk without a passing, commit-bound verdict, on every tool. Each pack carries:

1. the tool's native hook for early feedback where the tool has one, and
2. a git pre-push hook (`hooks/pre-push`) that feeds the shared guard the push command and refuses a
   push whose HEAD lacks a passing commit-bound verdict, enabled once per clone with
   `git config core.hooksPath hooks`, and
3. the CI required status check (`.github/workflows/veldo-gate.yml`) as the server-side backstop that a
   local hook cannot be edited away.

For the IDE cluster (Cursor, Copilot) and for Aider (which defaults to skipping git hooks, so its
pack sets `git-commit-verify: true`), the git pre-push hook plus the CI required check are the
guaranteed gate. Every pack's push gate is proven the same way before a release: an unproven push is blocked and a
proven one allowed, in a throwaway repository built from that pack alone, with the committed hook
executable in the git index. The harness that drives it lives in the source repository rather than in
the release, because it enumerates OUR seven packs. That proof is the reason this claim is here: it
caught the Claude pack shipping no pre-push hook at all, where a human pushing from a terminal could
land an unproven commit while every other pack refused it.

## Enabling a pack

Take the base and the pack for your tool: copy `engine/` into your repository, then copy your pack
directory over it (the pack layers on top, so a pack file always wins). A published release ships
each pack already composed, so there it is one directory. Then enable the git pre-push hook once:

```
git config core.hooksPath hooks
```

Point a required status check at `.github/workflows/veldo-gate.yml`, and wire the tool's native driver
per the table above. The method and the full operating contract are in each pack's `AGENTS.md`.

The autonomous headless fleet (`veldo fleet N`) is a CLI-agent capability; an IDE pack delivers the
method, gate, and enforcement but not the fleet-worker role, by design.
