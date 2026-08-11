---
schema: veldo.spec/v1
id: WARP-0309
title: Suite pluggability - gate-slot wiring, honest capabilities, runner catalog (B9 of PLAN-0003)
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0003
work: B9
plan_revision: 2
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A runner catalog is added to the docs (a new section in docs/plugin.md,
      "Runner catalog and gate-slot wiring") that covers EVERY runner directory
      under engine/scripts/runners/. For each runner it gives the
      surface, the home path, the capabilities status, what the runner asserts,
      its passing/failing fixture pair, and the gate slot an adopting repo wires
      it into. The catalog extends an existing document so no new PDF or manifest
      entry is required (pdf rendering stays a manual release act).
  - id: AC2
    text: The catalog gives gate-slot wiring guidance per runner - the CHECK_
      slot in scripts/verify.sh an adopting repo points each runner at (for
      example api/contract to CHECK_contract or CHECK_integration, auth to
      CHECK_security or CHECK_contract, web journeys to CHECK_journeys, token
      lint to CHECK_token_lint, migration to CHECK_migration, performance to
      CHECK_performance, and surfaces without a dedicated canonical slot to
      CHECK_extra or a repo-declared named slot) - consistent with the intended
      slot recorded in each capabilities.yaml note.
  - id: AC3
    text: Capabilities coverage is honest and complete. Every runner directory
      has at least one .veldo/capabilities.yaml entry whose home points into it,
      and every such entry carries a non-blank status drawn from the manifest
      vocabulary (mechanical, reference, procedure, absent, control-plane). The
      catalog DEFERS to the manifest for status - it states the manifest is
      authoritative and never prints a status that contradicts capabilities.yaml
      - and it explains the reference-versus-mechanical distinction (reference =
      needs a product surface the home repo lacks, so the home gate marks that
      slot na; mechanical = control logic gate-tested end to end here).
  - id: AC4
    text: A stdlib catalog-completeness check ships at
      scripts/check_runner_catalog.py and is wired into the gate through the unit
      slot (scripts/selftest.py, CHECK_unit). It ENUMERATES every runner
      directory and fails closed unless each has a passing fixture, a
      deliberately-failing fixture, a capabilities entry with a non-blank
      vocabulary-valid status, and a gate wiring (a Python runner must be
      referenced in scripts/selftest.py; a runner with no importable module must
      ship a fixture-driving test_*.sh wrapper). It observes real files, so it
      cannot be satisfied by the docs table alone. The selftest drives it against
      the real tree AND against synthetic trees each missing one property (a
      passing fixture, a failing fixture, a capabilities entry, an in-vocabulary
      status, a selftest reference, an exercising wrapper), proving every branch
      fails closed. This is BJ1: no runner rubber-stamps or ships uncatalogued.
  - id: AC5
    text: BJ2 is documented and asserted - the home gate never invokes a surface
      runner it lacks. The catalog records that scripts/verify.sh declares every
      surface-requiring slot (journeys, ui_states, accessibility, token_lint,
      visual_baselines, contract, integration, migration, performance, security)
      na with a reason, and check_runner_catalog.py asserts mechanically that no
      required gate command (CHECK_*="required:...") in verify.sh shells a runner
      (contains runners/). The unit slot importing runner control logic in
      process with stdlib only is not driving a live surface, so the home gate
      stays hermetic - no backend, emulator, simulator, container runtime, or
      third party is needed to run it.
  - id: AC6
    text: The deliverable is generic (zero company, product, or person names and
      zero absolute host paths in the docs section, the check script, and the
      spec beyond the standard owner field) and hygienic (ASCII only, no em or en
      dash, no double hyphen). The specs index regenerates to include this spec,
      and the full gate (lint, unit, generated, docs, template sync, secret scan,
      contract validation) stays green with every prior selftest case still
      passing.
required_evidence: [unit, operational]
rollback: git revert; B9 is additive - a docs section in docs/plugin.md, a new
  stdlib script scripts/check_runner_catalog.py, a selftest block, a Document
  History row, and this spec. It touches no protected path, no synced core
  (validate.py, policy_check.py, update_index.py, veldo-guard.sh), and adds no
  new required CHECK_ slot, so reverting removes the catalog and its unit block
  with no effect on any running gate; prior selftest cases are unchanged.
---

## Intent

PLAN-0003 ships a reference runner for every common product surface. The
capstone, B9, makes the suite usable and keeps it honest. A suite of twenty-one
runners is only trustworthy if three things hold and stay held: an adopter can
find the right runner and knows which gate slot to wire it into; every runner
carries an honest status so nobody trusts a sentence the code does not back; and
no runner can ship without proof it does not rubber-stamp. B9 delivers the
catalog for the first, defers to the capability manifest for the second, and
adds a mechanical completeness check for the third, so the catalog cannot rot
and a runner added later without a proving fixture pair or a capabilities entry
turns the gate red.

## Context

B9 of PLAN-0003, feature F7 (suite pluggability), depends on all nineteen other
runner work items in the plan and closes the plan at 20/20. It follows the
shipped runners' pattern: additive files under engine and scripts,
stdlib only, control logic gate-tested in the unit slot with no live surface.
The catalog extends docs/plugin.md rather than adding a top-level document, so
no manifest or PDF entry changes (the repository treats pdf/ rendering as a
manual release act). The completeness check is wired through the existing unit
slot rather than a new CHECK_ slot, so the canonical gate catalog is untouched.

## Out of scope

Executing any runner against a live product surface in the home gate (the home
repo has none of the surfaces; that is exactly why the runners are reference and
the slots are na). Changing any runner's behavior or status - B9 reads the
manifest, it does not restate or override it. Forcing a runner into the veldo
repo's own gate (non-goal NG2 of the plan). A new top-level document or any pdf
regeneration.

## Notes

Why BJ1 is mechanical and not a doc review: a hand-maintained catalog drifts the
moment someone adds a runner and forgets the table, so completeness is enforced
by a check that enumerates the real directories and fails closed, not by a
reviewer's diligence. The check is proven adversarially in the selftest by
building synthetic runner trees that each omit one required property and
asserting the check reports it - a runner missing its passing fixture, its
failing fixture, its capabilities entry, an in-vocabulary status, its selftest
reference, or any exercising wiring all fail, so the branch that would let a
rubber-stamp through does not exist.

Why BJ2 is a property plus a cheap assertion: the home gate's hermeticity is a
standing operational fact (the surface slots are na with reasons in verify.sh),
and the one way it could silently break - a required command that shells a
runner - is caught mechanically by the same check. The unit slot importing a
runner module in process, and spawning stdlib python subprocesses or a pty for
the mechanical runners, uses only this box and stdlib, so it is not a live
surface and does not violate BJ2.

The reviewer should confirm by rerunning the selftest and the standalone check:
(1) the real tree is complete and the gate shells no runner; (2) each synthetic
omission fails closed with the property named; (3) the catalog's Status column
equals capabilities.yaml for every row; (4) the docs, secret, lint, and
template-sync gates stay green.
