---
schema: veldo.spec/v1
id: WARP-0709
title: Comprehensive README for team adoption - the complete VELDO front door
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: standalone
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: README.md is expanded from a brief pointer into a complete standalone orientation a
      new team member can read to understand WHAT VELDO is, WHY it exists (verification is the
      bottleneck once code generation is cheap), the one rule and the loop, and the principles -
      without having to read the full method document first.
  - id: AC2
    text: The README explains HOW the loop works in practice with the concrete repository
      artifacts a team touches - the specification as the unit of work, the canonical gate, the
      proof and the independent verdict, the evidence commit, and specs/index.md as the board -
      so the reader understands the mechanics, not just the philosophy.
  - id: AC3
    text: The README documents the CURRENT capability surface the plugin ships (deferring to
      the capability manifest as the machine-readable truth) - the gate and policy guard, the
      language/web/mobile/design runners, the Run Lens for a running build, and the VELDO Fleet
      (elastic capability-routed parallel workers with a serialized lander, shared-read-once
      environments, and a token-paced governor) - so a team knows what they get, and it names
      the plugin version.
  - id: AC4
    text: The README gives a concrete adoption path - install, init once per repo, the first
      change end to end, and running at scale with the fleet - and points to the deep documents
      (method, setup, plugin guide) for full detail rather than duplicating them.
  - id: AC5
    text: The README is generic (no company-specific content), ASCII-only with no em-dashes or
      en-dashes, and the full gate is GREEN (dash sweep, non-ASCII sweep, and the docs
      genericity sweep pass); no protected path and no other document is changed.
required_evidence: [operational]
rollback: git revert; the change is confined to README.md and this spec; no code, no protected
  path, no other document.
---

## Intent

Make the README a comprehensive front door so a new team member, or a team evaluating VELDO,
can adopt it from the repository alone. The prior README was a brief pointer; now that the
full method, the plugin, and the fleet exist, the README should stand on its own as the
complete orientation and route to the deep documents for detail.

## Context

A standalone documentation change (the founder asked, via a task, to make the VELDO
documentation as robust as it can be for team adoption, starting with the README at a
comprehensive level of detail). It reflects the now-complete system: the method, the gate and
policy, the runner catalog, the Run Lens (PLAN-0005), and the VELDO Fleet (PLAN-0007, plugin
3.2.0). The capability manifest (.veldo/capabilities.yaml) remains the machine-readable truth;
the README describes the surface and defers to it, so prose can never contradict the manifest.

## Notes

Comprehensive but navigable: the README orients and routes, it does not duplicate the 900-line
method or setup documents. It stays generic (the genericity sweep covers docs/ and packs/claude/;
the README is kept generic regardless) and ASCII-only with no em-dashes. Only README.md and
this spec change; the method document and every other doc are untouched.
