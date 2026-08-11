---
schema: veldo.spec/v1
id: WARP-1012
title: Restore validate.py under the module_lines budget by extracting the delegating validators
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: standalone
protected_paths: []
placement: [contracts]
footprint:
  - .veldo/validate.py
  - .veldo/validate_checks.py
  - .veldo/init_scaffold.py
  - scripts/selftest.py
  - engine/.veldo/validate.py
  - engine/.veldo/validate_checks.py
  - packs/*/.veldo/validate.py
  - packs/*/.veldo/validate_checks.py
  - specs/WARP-1012-restore-validate-under-budget.md
acceptance_criteria:
  - id: AC1
    text: >
      .veldo/validate.py is brought UNDER the architecture contract's module_lines budget (file_lines,
      max 1000). It was 1207 lines, a pre-contract module and the last governed file over the budget,
      which since WARP-1102 shipped the shape gate refuses to let any change touch (a change that
      touches an over-budget governed file fails the file_lines budget by name), blocking all future
      wiring into validate.py run_all. After the split validate.py is under 1000 lines with margin. A
      selftest line-count assertion goes RED the moment validate.py crosses the budget.
  - id: AC2
    text: >
      The extraction lands in ONE new sibling module, .veldo/validate_checks.py, which holds a cohesive,
      self-contained group: the validators that DELEGATE to the sibling contract organs (the
      architecture contract via arch.py, the placement and ready gates, decision records via
      decision.py, the adversarial decision review via decision_review.py, the decision tripwires via
      tripwire.py, the shape-fit review dimension via shape_review.py, and the read-only
      tripwire-status projection). The new module is also under the module_lines budget with wide
      margin. A selftest line-count assertion goes RED the moment it crosses the budget.
  - id: AC3
    text: >
      The public API is STABLE. validate.py loads validate_checks.py by path (the same idiom by which
      validate.py loads arch.py and decision.py, and by which shape_gate.py, entropy.py, and
      incident.py load validate.py), binds the sub-module this module's ONE front-matter parser
      (parse_yamlish) and ONE failure reporter (fail), and re-exports every moved name back into its
      own namespace. So every existing caller keeps resolving the same names on validate.py exactly as
      before: V._arch_module, V.check_arch, V.check_placement, V.load_repo_contract,
      V.placement_gate_problems, V.placement_gate_ok, V.check_ready, V._decision_module,
      V.check_decision, V.check_decisions, V._decision_review_module, V.check_decision_review,
      V.check_decision_reviews, V._tripwire_module, V.check_readings, V.check_tripwires,
      V._shape_review_module, V.check_shape_review, V._count_fail, and V.tripwire_status. The dependency
      is ONE-WAY (validate.py to validate_checks.py, never back), so there is no import cycle and no
      second parser. A selftest asserts every moved name still resolves and callables and that the
      re-exported objects ARE the sub-module's (moved, not duplicated).
  - id: AC4
    text: >
      ZERO behavior change. No validation logic, no message, and no check changed; nothing deferred was
      wired in. The output of python3 .veldo/validate.py all and of every CLI mode (spec, plan, arch,
      placement, ready, decisions, tripwires, usage, unknown-mode) is byte-identical before and after
      the split, and proof_digest is unchanged. A selftest exercises the re-exported validators over
      the real corpus and shipped examples (V.check_arch, V.load_repo_contract, V.check_decisions,
      V.check_tripwires, V.tripwire_status, V.check_decision, V.check_placement) and confirms they
      behave identically.
  - id: AC5
    text: >
      The extraction is REAL, not a copy. The delegating validators are DEFINED in
      .veldo/validate_checks.py and are NO LONGER defined in .veldo/validate.py, while the stayers (the
      one parser parse_yamlish, the reporter fail, check_spec, check_json, check_plan and the plan
      family) remain defined in validate.py. validate_checks.py loads validate.py NOWHERE (the one-way
      dependency, no cycle). Source guards in the selftest assert all of this.
  - id: AC6
    text: >
      The gate is UNBLOCKED. Before the split, a change touching the over-budget validate.py was
      refused by the shape gate's file_lines budget (naming module_lines); after the split, the shape
      gate's file_lines check yields NO finding for validate.py and the full shape gate returns no
      problems for a change set that touches validate.py. This is proven with teeth: an over-budget
      copy of validate.py (in a temporary tree, the real file never mutated) IS still refused naming
      module_lines (the pre-split state the gate blocked), and the real file on disk stays under budget.
      The change also re-points the WARP-1102 AC3 selftest assertions that had encoded validate.py as
      the grandfathered over-budget module: coverage is preserved, not deleted. The budget's teeth on a
      real governed path stay proven by WARP-1102's seeded over-budget fixture; the re-pointed
      assertions now confirm the restored validate.py is under budget, and the change-scoping
      demonstration (an empty change set flags nothing) is unchanged.
  - id: AC7
    text: >
      Byte-identical engine sync and a working scaffold. .veldo/validate.py and the new
      .veldo/validate_checks.py ship byte-identical across root, engine, and all 6 packs
      (aider, antigravity, codex, copilot, cursor, opencode): pack drift empty, pack conformance pass,
      template sync pass. The scaffolder (.veldo/init_scaffold.py, root-only) registers the new module in
      its lay-down list and its required substrate, so a freshly scaffolded repository's validate.py is
      not left broken by a missing sibling. Selftest assertions confirm the byte-identity across all 8
      engine copies and the scaffolder registration.
  - id: AC8
    text: >
      A clean dogfood and no protected path. This spec (WARP-1012) declares placement [contracts] and a
      footprint that resolves to the contracts area only (validate.py maps to contracts; validate_checks.py,
      init_scaffold.py, selftest.py, the twins, the pack globs, and the spec file resolve to no declared
      area), so its footprint touches a single area, does NOT raise the tier, and it passes the mandatory
      placement gate at risk standard with no approval. No protected path (scripts/verify.sh,
      scripts/veldo-guard.sh, .veldo/policy.yaml, .veldo/policy_check.py and their twins) is touched, the full
      gate is GREEN (selftest, contracts, generated, docs, secret scan, template sync, pack drift), and
      RULE #1 is clean (ASCII hyphen only, no em or en dash, no prose double-hyphen; hand-checked across
      every changed file).
required_evidence: [unit]
rollback: >
  Revert the commit. It splits the sibling-module delegating validators out of .veldo/validate.py into a
  new .veldo/validate_checks.py, re-exports them back onto validate.py (a one-way load, no import cycle),
  registers the new module in the scaffolder (.veldo/init_scaffold.py), adds a WARP-1012 selftest block,
  re-points the two WARP-1102 AC3 assertions that had encoded validate.py as the grandfathered
  over-budget module, and re-syncs validate.py and validate_checks.py byte-identical across
  engine and the 6 packs. It is a pure, behavior-preserving, API-stable refactor: reverting
  restores the single-file validate.py with no migration and nothing to unwind, since no validation
  logic, message, or output changed. A repository with no architecture contract is unaffected.
---

## Intent

Since WARP-1102 shipped, the shape gate refuses any change that touches a GOVERNED file which is over
its module_lines budget (file_lines, max 1000). This repository's own .veldo/validate.py was 1207 lines,
a pre-contract module and the last governed file over the budget. That means validate.py can no longer
be edited without failing the gate, which blocks wiring every future plan's check into validate.py
run_all. Bringing validate.py under budget is exactly the entropy loop's remedy (the W8/W9 restoration
class) working on the repository itself, and it unblocks all downstream gate-wiring.

This is a PURE, behavior-preserving, API-stable refactor: it moves a cohesive group of functions to a
new sibling module and re-exports them, changing nothing about what the validator accepts or rejects,
what it prints, or what proof_digest returns.

## Context

- The size budget binds the CHANGE, never the shipped corpus (WARP-1102, the only green-safe reading
  given the pre-contract over-budget validate.py). Restoring validate.py under budget removes the last
  grandfathered over-budget governed module.
- The group extracted is the validators that DELEGATE to the sibling contract organs (arch.py,
  decision.py, decision_review.py, tripwire.py, shape_review.py) plus the placement/ready gates and the
  tripwire-status projection: functions 718 through 1041 of the pre-split validate.py, a cohesive family
  that already loads its siblings by path.
- The load idiom is the repository's own: validate.py loads validate_checks.py the same way it loads
  arch.py and decision.py, and the same way shape_gate.py, entropy.py, and incident.py load validate.py.
  The dependency is one-way and validate.py injects its one parser and one reporter, so validate_checks.py
  ships no second parser and there is no import cycle.

## Out of scope

- No new check and no deferred wiring. This unit only moves code to get under budget; wiring any deferred
  check (incident and the like) into run_all is each plan's release job, not this refactor.
- No logic, message, or behavior change. The validator accepts and rejects exactly what it did before,
  prints exactly what it did before, and proof_digest is unchanged.
- No protected path. scripts/verify.sh, scripts/veldo-guard.sh, .veldo/policy.yaml, .veldo/policy_check.py
  and their twins are untouched. validate.py and validate_checks.py are non-protected engine modules.
- No architecture-contract edit. validate_checks.py is a new sibling that resolves to no declared area
  (the contract's contracts-area includes are exact paths); it is under budget regardless, and adding it
  to the human-approved contract is a separate governance act, not this refactor.

## Notes

- Keep the extraction byte-exact: the moved function bodies are unchanged, so behavior is preserved by
  construction. The re-export binds each moved name back onto validate.py so no caller anywhere (arch.py,
  decision.py, decision_review.py, tripwire.py, shape_gate.py, entropy.py, restoration.py, incident.py,
  plan.py, shape_review.py, selftest.py, verify.sh, policy_check.py) breaks.
- Put teeth on it: the API still resolves and behaves; both files are under budget (a line-count
  assertion that goes RED if either exceeds it); the shape gate now passes on a validate.py edit while an
  over-budget copy is still refused; and the two engine files are byte-identical across all 8 copies.
- Follow the byte-identical engine sync discipline: validate.py and validate_checks.py land in
  engine and every pack byte-identical, and the drift checks end empty. The scaffolder lays the
  new module down so a fresh repository is not left with a broken validate.py.
- RULE #1 clean (ASCII hyphen only, no em or en dash, no prose double-hyphen).
