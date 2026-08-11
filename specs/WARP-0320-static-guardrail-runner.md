---
schema: veldo.spec/v1
id: WARP-0320
title: Static-invariant guardrail runner (B20 of PLAN-0003)
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0003
work: B20
plan_revision: 2
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: Given the shipped rules fixture and the clean sample tree
      (fixtures/pass), the runner finds no violation and exits 0, printing a
      clean result. The passing fixture genuinely satisfies every rule,
      including the repository layer that is allowed to import db.
  - id: AC2
    text: Given the same rules fixture and the deliberately-failing sample
      tree (fixtures/fail, whose service layer imports the db module directly),
      the runner prints the violation as file:line with the violated rule name
      (no-db-import-outside-repository) and exits 1. The exclude glob still
      allows the repository layer, so only the service file is flagged.
  - id: AC3
    text: The runner's control logic (rule loading with a loud failure on a
      malformed rule, recursive glob and exclude resolution, the per-line
      regex scan reporting the correct line number, and the exit code) is
      exercised in the repository unit self-test over both shipped fixtures and
      over a synthetic tree built in a temp dir, with no external dependency
      (stdlib only). Every assertion reflects the runner's real observed output.
  - id: AC4
    text: capabilities.yaml marks the runner status reference (a shipped
      artifact an adopting repo wires to a guardrail gate slot; the veldo repo
      does not run it as a gate check), consistent and byte-identical between
      the template instance and the repo instance. It is not marked mechanical.
required_evidence: [unit, operational]
rollback: git revert; the runner, its fixtures, and its README are additive
  files under engine/scripts/runners/guardrail/, touch none of the
  synced core, and the only gate coupling is the added selftest cases plus the
  reference capability entry.
---

## Intent

Some rules are invariants across the whole source, not properties of one call
site: the service layer never imports the database module directly, no file
carries a forbidden token, a layer boundary is never crossed. A single test
cannot catch these because the violation can appear in any file added later.
This ships a generic reference runner that turns such an invariant into a
mechanical guard: it reads a rules fixture (each rule a name, a glob, and a
forbidden pattern, with an optional exclude), scans the real source tree, and
fails the moment any file breaks a rule, printing file:line and the rule name.

## Context

B20 of PLAN-0003, feature F6 (safety surfaces), no dependencies, pulled from
the frontier. It follows the design-runner pattern (W6): stdlib-only Python
whose control logic runs in the gate's unit slot over a passing and a
deliberately-failing fixture, so the runner cannot rubber-stamp a vacuous pass.
Unlike token_lint (marked mechanical because the veldo repo has a design slot to
exercise), this runner is marked reference: the veldo repo has no
architecture-invariant slot of its own, so an adopting repo wires it to a
guardrail gate slot pointed at its own rules file and source root.

## Out of scope

Import-graph or AST-level dependency analysis (this is a line-oriented regex
guardrail, deliberately light), and wiring the runner into the veldo repo's own
gate catalog (the veldo repo has no architecture-invariant surface to guard; the
runner is exercised via selftest instead).

## Notes

The runner is stdlib-only so a reviewer reruns it with no setup. The rules file
carries the whole policy, so an adopting repo changes rules without touching the
runner. A malformed rules file exits 2 (fails loud) rather than scanning
nothing and passing green.
