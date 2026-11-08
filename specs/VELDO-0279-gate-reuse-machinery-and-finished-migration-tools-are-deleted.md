---
schema: veldo.spec/v1
id: VELDO-0279
title: The gate reuse machinery, which has never reused a result, and the finished suite-split and rename migration tools are deleted, keeping the worker bootstrap, the landing check and the case tracer
status: ready
risk: high
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: [VELDO-0267, VELDO-0271]
placement: [enforcement]
protected_paths: ["scripts/gate_reuse.py", "engine/scripts/gate_reuse.py", "scripts/mutation_reuse.py", "engine/scripts/mutation_reuse.py", "scripts/reuse_stamp.py", "engine/scripts/reuse_stamp.py", "scripts/case_reuse.py", "engine/scripts/case_reuse.py", "scripts/mutation_reuse_profiles.json", "scripts/reuse_worker.py", "engine/scripts/reuse_worker.py", ".veldo/reuse_evidence.py", "engine/.veldo/reuse_evidence.py", "scripts/check_gate_mutations.py", "engine/scripts/check_gate_mutations.py", "scripts/case_inputs.py", "engine/scripts/case_inputs.py", "scripts/verify.sh", "engine/scripts/verify.sh", "scripts/veldo-guard.sh", "engine/scripts/veldo-guard.sh", "scripts/run_scope.py", ".veldo/control_verification.py", "engine/.veldo/control_verification.py", ".veldo/policy.yaml", "scripts/mutation_case_inputs.json"]
footprint:
  - "scripts/*.py"
  - "scripts/*.json"
  - "scripts/*.sh"
  - "engine/scripts/**"
  - ".veldo/reuse_evidence.py"
  - "engine/.veldo/reuse_evidence.py"
  - ".veldo/control_verification.py"
  - "engine/.veldo/control_verification.py"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/policy.yaml"
  - "scripts/suites/**"
  - "specs/VELDO-0279-gate-reuse-machinery-and-finished-migration-tools-are-deleted.md"
  - "specs/index.md"
  - "proof/VELDO-0279/**"
behavior_bearing: true
observability:
  logs: >
    The mutation verdict line loses its reused= field; nothing else in the gate's output changes.
  metrics: >
    The stamp and gate event lose force_fresh and reused. A stamp written before this change, with those
    fields, still validates.
  traces: >
    None added; scripts/case_trace.py stays, as VELDO-0267's coverage map uses it.
  error_taxonomy: >
    Removed: every reuse refusal (unauthenticated reuse, stale reuse key, reuse sample mismatch). Kept:
    the landing check refuses any stamp or event that claims a reused result greater than zero.
acceptance_criteria:
  - id: AC1
    text: >
      Reuse is gone and every gate result is fresh. Deleted with their engine copies: gate_reuse.py,
      mutation_reuse.py, reuse_stamp.py, case_reuse.py and mutation_reuse_profiles.json; suites 99, 100 and
      101; the reuse store, its HMAC secret handling and the VELDO_GATE_FORCE_FRESH switch; their
      protected-path entries in .veldo/policy.yaml. reuse_worker.py stays as the mutation worker bootstrap
      without its reuse branches (renamed mutation_worker.py, its protected entries renamed with it), and
      reuse_evidence.py keeps only what the guard, control_verification.py and the gate still use: the
      authority identity and landing_problem, which now refuses any document claiming reuse above zero.
    falsified_by: >
      A scan row finds none of the deleted names in tracked files outside specs/, proof/ and plans/. A
      landing row hands the guard and control_verification a green stamp with reused unit 1: both refuse;
      with no reused field: both accept. Registered mutation from a green baseline: landing_problem ignores
      the reused field: the landing row goes red.
  - id: AC2
    text: >
      The finished migration tools are gone: suite_survey.py, suite_slice.py, suite_equiv.py,
      suite_extract.py, suite_labels.py, suite_attr_check.py, rename_migration.py, migrate_to_veldo.py and
      migrate_name_map.json. The rows of suites 01, 12, 13 and 24 and shared.py that exercise only them go;
      check_generated.sh stops regenerating proof/WARP-0716/crossing-state.md and the two WARP-0712 reports
      (they stay as committed history); publish.py stops naming them; requires.json is still derived by
      run_scope.py from the committed measurement, unchanged.
    falsified_by: >
      The scan row covers these names too, and a row requires requires.json regenerated after the deletion
      to be byte-identical to the one before. Registered mutation: run_scope.py's closure step is made to
      read a deleted tool: the regeneration row goes red.
  - id: AC3
    text: >
      Nothing a gate checks is lost. The proof bundle carries one line per removed suite row and mutation
      case, naming the behavior it checked and either the row that still checks it or "reuse only" or
      "migration only".
    falsified_by: >
      A table row requires the proof table to list every suite row and mutation case present at the base
      commit and absent after, by name. Registered mutation: one removed row is left out of the table: the
      table row goes red.
required_evidence: [unit]
rollback: Revert the commit; git history keeps every deleted file.
---

## Intent

Weight audit item 11: delete machinery that has never done its job and tools whose job is done.

## Context

Verified on main at afa292f0, and where the audit's fact differs:

- Sizes match: the six reuse modules are 850 lines; suites 100 and 101 are 2,817 lines and 99 is 577
  more; the migration tools are 5,495 plus 1,119 lines.
- Not all of the audit's reuse list is reuse only. reuse_worker.py is the bootstrap every mutation
  worker starts from (check_gate_mutations.py starts it for every case), and reuse_evidence.py also holds
  the authority identity and landing_problem, which the push guard (veldo-guard.sh) and
  control_verification.py call on every landing. So those two shrink and stay; the audit's "delete"
  holds for the other four modules.
- suite_slice.py and suite_survey.py are still run by check_generated.sh to re-render three committed
  reports; AC2 stops that rather than leaving the gate calling deleted tools.
- Every recorded gate event shows reuse 0 (verified on the last stamp: reused unit 0, mutation 0).

Dependencies and order, so nothing conflicts: VELDO-0267 (lands first; its AC1 clause applying reuse
rules to selected cases then has nothing to apply), then VELDO-0271 (the lead's landing order 0267,
0271, 0269; it rewrites reuse_worker.py and reuse_evidence.py for one leg), then this spec. VELDO-0222
(ready, never built) only extends reuse, and VELDO-0206 (suite reuse, ready, never built) adds it: this
spec supersedes both and they are not built. VELDO-0271 lists VELDO-0222 as a dependency and its AC3
keeps reuse under 0222's rules; the cheapest path is for the lead to drop that dependency and the reuse
clause of 0271 AC3 before 0271 is claimed, since this spec deletes reuse right after. If 0271 lands as
written, this spec deletes what it kept.

Owner approval: not required. Removing reuse removes a trust path (accepting a stored result); the
landing check becomes stricter, refusing any reuse claim. No credential, schema or infrastructure
changes. The protected paths still take the policy's approval record at landing.

## Out of scope

The mutation selection (VELDO-0267), the sandbox (VELDO-0271), the resource ledger, case_trace.py.

## What the reviewer judges

- Normal use: every gate and landing after the change.
- No gate result can come from a stored record; nothing the gate checks loses its only check.
- Out of review scope: per the template.

## History

2026-11-07: drafted by the lead from the weight audit's item 11 (Telegram 39708, 39710). A draft.

2026-11-07: ready by the lead under the owner's narrowed approval scope (Telegram 39708): test machinery and cleanup, no money, security, schema or infrastructure decision.
