---
schema: veldo.spec/v1
id: WARP-1311
title: Security by design ships - ten modules in the engine, the docs made true, and two things
  honestly marked as needing a human rather than quietly claimed as done
status: shipped
risk: standard - the modules already shipped and gated individually. What lands here is
  documentation, a version bump and a plan status. The risk is a doc that overstates what is wired,
  which is exactly the failure this plan spent ten items refusing to commit.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0013
work: W11
depends_on: [WARP-1303, WARP-1304, WARP-1306, WARP-1307, WARP-1308, WARP-1309, WARP-1310]
placement: [docs, distribution]
footprint:
  - "docs/method.md"
  - "docs/setup.md"
  - "docs/plugin.md"
  - "packs/claude/.claude-plugin/plugin.json"
  - ".claude-plugin/marketplace.json"
  - "plans/PLAN-0013-security-by-design.md"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-1311-security-by-design-release.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      ALL TEN MODULES ARE IN THE CANONICAL ENGINE AND THE PACKS CARRY THEM. Each is byte-identical
      between the repository root and `engine/`, and each matches the `ENGINE_GLOBS`
      manifest so `assemble_pack` picks it up with no manifest edit.
  - id: AC2
    text: >
      THE DOCS ARE TRUE, AND GENERIC. The method gains security by design as part of the method, the
      setup guide gains an install-state table and a five-step migration, and the plugin guide gains
      the capability reference. None of them names this repository's business, and each defers to
      `.veldo/capabilities.yaml` for status rather than asserting its own.
  - id: AC3
    text: >
      WHAT IS NOT WIRED IS NAMED AS NOT WIRED. The secret resolver resolves nothing, the credential
      issuer mints nothing, and the security reviewer raises. The setup guide says in as many words:
      wire a genuinely fresh context or leave the dimension off, but do not wire something that
      returns `secure`. A doc claiming turnkey security would be the single most dangerous artifact
      this plan could produce.
  - id: AC4
    text: >
      TWO ITEMS ARE ESCALATED, NOT PERFORMED. Wiring the inventory into `scripts/verify.sh` and
      placing the inventory record under `protected_paths` both touch protected files, so they are
      approvals rather than agent work and are recorded as such in the docs and the plan. Nothing
      here self-approves a protected-path change.
  - id: AC5
    text: >
      CAPABILITIES ARE RECORDED HONESTLY AND THE VERSION IS BUMPED ONCE. Ten `capabilities.yaml`
      entries exist, one per module, byte-identical root and template; the plugin version moves in
      BOTH places it is declared, which is the check that caught a miss earlier in this plan.
  - id: AC6
    text: >
      THE PLAN IS RELEASED WITH ITS OBSERVATION HONESTLY PENDING. Every work item is shipped and the
      full regression is green, which is the release condition. The observation window - running
      this repository migrated AND fail-closed - cannot begin until the AC4 approvals land, and the
      plan says that rather than implying the window is running.
required_evidence: [unit]
rollback: >
  Revert the doc sections, the two version strings and the plan status. No module changes, so no
  behaviour changes.
---

## Outcome

Security by design ships in the engine, the documents describe what actually happens, and the two
things a machine must not do itself are named as work for a human.

## What shipped

Ten modules. Secrets exist as references resolved at use. The gate refuses anything
credential-shaped with no allowlist mechanism at all. Agent context is redacted at the seam rather
than filtered afterwards. Credentials are issued per task, scoped to the declaration, expiring and
re-checked at use. External text arrives fenced as data. A new dependency arrives with a reason.
Generated infrastructure is held to least privilege in seven named classes. Commits are signed
against a registry the repository declares, because git's good-signature verdict is about the local
keyring. Security is a graded review dimension where correct-but-insecure sends a change back. And
the estate is inventoried, by reference, across reachable history.

## The part worth being careful about

The temptation at a release item is to write documents that make the work sound finished. Three
pieces here are seams, not implementations: the secret resolver resolves nothing until it is pointed
at a real store, the credential issuer is a fake that mints nothing, and the security reviewer
raises rather than fabricate a judgment.

A document claiming turnkey security would be the most dangerous artifact this plan could produce,
because somebody would rely on it. So each of the three is named in the install-state table, and the
setup guide says explicitly not to wire a reviewer that returns `secure`.

## Two things a machine must not do for itself

Wiring the inventory check into the gate, and putting the inventory record under `protected_paths`.
Both touch protected files. Both are exactly the kind of change where an agent approving its own
work would defeat the point of having protected paths at all, so they are escalated.

That is also why the plan is released with its observation window pending rather than running: the
window requires this repository to be fail-closed, and it is not, because that flip is a human's
dated decision.
