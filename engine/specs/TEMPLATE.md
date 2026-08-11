---
schema: veldo.spec/v1
id: VELDO-0000
title: <short title>
status: draft            # draft | ready | in_progress | review | proven | shipped | blocked
risk: standard           # declared floor; policy may raise it, nothing may lower it
owner: <the human accountable for the intent>
human_approval: not_required
lane: standalone         # standalone (bug/isolated) | planned (bound to a Product Plan)
# For lane: planned, also set plan: PLAN-NNNN, work: Wn (mirrored to the plan),
# and plan_revision: N (the plan revision it was pulled against; run-check
# refuses to build against a stale revision).
# Placement and footprint (PLAN-0011 W3). When the repository carries an architecture
# contract (.veldo/architecture.yaml), a spec declares where its change lands (placement)
# and what it touches (footprint), validated against the contract's areas. MANDATORY
# once a contract exists: a spec may not reach ready and is never claimed without a
# placement that resolves to a contract area, and a footprint that crosses an area
# boundary raises the risk tier (nothing lowers it). When no contract exists, both stand
# down and the spec is unaffected. Run python3 .veldo/validate.py ready <file> before
# promoting to ready.
# placement: [<area-id>]         # one or more area ids the contract declares
# footprint: [<path-glob>, ...]  # the path globs this change is allowed to touch
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: <observable, testable requirement>
required_evidence: [unit]
rollback: <how this change is reverted or disabled>
---

## Intent

What outcome should become true, and why it matters.

## Context

Relevant background: product, technical, operational.

## Out of scope

What this change must not touch.

## Notes

Anything the implementing or reviewing agent needs.
