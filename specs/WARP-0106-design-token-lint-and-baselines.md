---
schema: veldo.spec/v1
id: WARP-0106
title: Design token lint and visual baseline comparator (W6 of PLAN-0001)
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0001
work: W6
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: token_lint.py fails a file that hardcodes a color (hex or rgb) or a
      px spacing value not in the token set's allow_raw list, and passes a
      file that uses only tokens; the good fixture is clean, the bad fixture
      yields raw-color and raw-space violations with file:line. Gate-tested.
  - id: AC2
    text: baseline_compare.py passes only when the fraction of differing
      pixels is within a declared tolerance (default or per-baseline), fails
      beyond it, and auto-fails on a dimension mismatch; identical renders are
      0 percent, a large change is caught, a sub-tolerance change passes.
      Gate-tested via PIL.
  - id: AC3
    text: Both tools are exercised in the repository's unit self-test (they
      are pure Python and PIL, so they run in the every-commit gate), and
      capabilities.yaml marks token_lint and baseline_comparator mechanical,
      with the per-repo slot wiring documented.
  - id: AC4
    text: The tools ship with fixtures (tokens.json, good.css, bad.css, a
      tolerance config) and a README explaining the token and visual-fidelity
      layers of the design contract, including that render-vs-approved-baseline
      is used, never a machine-diff against a design export.
required_evidence: [unit, operational]
rollback: git revert; both tools and their fixtures are additive files under
  scripts/runners/design/, touch none of the synced core, and their only gate
  coupling is added selftest cases; the 77 prior cases pass within the 84.
---

## Intent

The design contract's first and last layers become mechanical: tokens (no raw
values, so screens are on-design by construction) and visual fidelity (a
render guarded against an approved baseline within tolerance). Together with
the human design-review verdict (which approves the baseline) and the web
runner's flows and states (W5), this closes the loop from design intent to
guarded delivery, without ever machine-diffing a render against a design
export.

## Context

W6 of PLAN-0001, no dependencies, pulled from the frontier. Unlike the web
runner (W5, browser-dependent, reference), these are pure Python and PIL, so
they are genuinely mechanical here and run in the gate's unit slot. A
consuming repo points its token_lint and visual_baselines gate slots at its
own tokens, sources, and approved baselines.

## Out of scope

The human design-review verdict lane (already in the method) and the
figma-vs-render composite (veldo-visual.py). Wiring these into the veldo gate's
own token_lint/visual_baselines slots (veldo has no design system; the tools
are exercised via selftest instead).
