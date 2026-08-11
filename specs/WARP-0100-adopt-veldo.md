---
schema: veldo.spec/v1
id: WARP-0100
title: Adopt VELDO in the VELDO home repository
status: shipped
risk: high    # floored: creates scripts/verify.sh, a protected path in the policy this spec ships
owner: dmitry
human_approval: required
lane: standalone
protected_paths: [scripts/verify.sh]
acceptance_criteria:
  - id: AC1
    text: python3 .veldo/validate.py all exits 0 (repository contracts and examples valid).
  - id: AC2
    text: ./scripts/verify.sh exits green with five required checks running real
      commands (lint syntax-checks all shipped scripts, unit runs the contract
      negative self-test, docs enforces hygiene and genericity, generated keeps
      the index derived, extra enforces template sync).
  - id: AC3
    text: scripts/update_index.py generates specs/index.md listing this specification.
  - id: AC4
    text: The docs check fails when an em-dash or a company reference is planted
      in a generic document, and passes after removal (negative demonstration).
  - id: AC5
    text: The template-sync check fails when the repository instance of
      validate.py drifts from engine, and passes after resync
      (negative demonstration).
required_evidence: [unit, operational]
rollback: git revert the adoption commits; all changes are additive files plus
  one two-character fix in docs/method.md.
---

## Intent

The VELDO home repository starts running VELDO on itself: PLAN-0001 (VELDO 1.0)
is approved and every work item in it must be delivered as a specified,
gated, proven, independently reviewed change. That is impossible without the
substrate, so the substrate lands first, as the first spec.

## Context

This repository is docs + plugin templates + plans: no product runtime, no
database, no UI. The honest gate therefore runs what is real here: syntax
lint over every shipped script, the contract-system negative self-test
(the validator is the product; a validator that accepts garbage is worse
than none), the standing docs hygiene rules (ASCII-only prose, zero company
references in generic documents), derived-index freshness, and byte-level
sync between the repository's own substrate instances and the canonical
engine it ships to everyone else.

## Out of scope

The plan contract (veldo.plan/v1) and plan index: that is WARP-0101 (W1 of
PLAN-0001). No CI wiring (W10). No doc content changes beyond the two
multiplication signs the non-ASCII sweep caught in docs/method.md.
