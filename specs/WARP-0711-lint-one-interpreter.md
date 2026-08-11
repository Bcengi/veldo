---
schema: veldo.spec/v1
id: WARP-0711
title: The lint stage spawns 661 interpreters to syntax-check 662 files - do it in one process, same files,
  same per-file failure naming, measured 14.07s to 0.82s
status: shipped
risk: high - the footprint crosses the enforcement and engine areas (a gate stage plus its seven engine
  copies), and a footprint crossing never lowers the tier, so high is the floor rather than a judgement. The
  substantive reason it deserves the tier: this changes a GATE STAGE, and the failure mode is a stage that
  checks FEWER files than before while still printing pass, which is invisible by construction. That is why
  the file set is asserted EQUAL to the old stage's rather than assumed, and why a deliberately broken file in
  each language must still fail by name. It is high and not critical because the stage's contract (same
  patterns, per-path failure naming, exit semantics, no bytecode) is preserved by proof, no protected path is
  touched, scripts/verify.sh and the stage list are byte-unchanged, and nothing outside this stage is
  affected. RECORDED HUMAN APPROVAL IS NOT REQUIRED: the owner directed this optimization, the change is
  contract-preserving by assertion, and it touches no protected path - if the implementation turns out to need
  scripts/verify.sh, it STOPS and returns for approval
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: []
placement: [engine]
footprint:
  - scripts/check_lint.sh
  - engine/scripts/check_lint.sh
  - packs/*/scripts/check_lint.sh
  - scripts/selftest.py
  - proof/WARP-0711/baseline.md
  - specs/WARP-0711-lint-one-interpreter.md
  - specs/index.md
protected_paths: []
behavior_bearing: true
observability:
  logs: The stage prints its elapsed time and the count of files checked per language, so a future cost
    regression is attributable and a silently shrinking file set is visible in the count rather than only in
    the timing.
  error_taxonomy: No new failure names. A syntax failure is still reported as the stage reports it today,
    named by path on its own line, and the stage's exit status semantics are unchanged.
acceptance_criteria:
  - id: AC1
    text: >
      THE COST IS ATTRIBUTED BY MEASUREMENT, and the baseline is committed rather than quoted.
      proof/WARP-0711/baseline.md records the per-stage wall clock of the whole gate measured in a clean clone
      (selftest 102.4s, lint 14.1s, and the six remaining stages 0.6s COMBINED: validate 0.12, docs 0.08,
      generated 0.04, template sync 0.00, pack drift 0.05, shape gate 0.28), the tracked file counts (662
      Python, 172 shell), and the measured batched equivalent (0.70s Python plus 0.11s shell) with the exact
      command to reproduce each figure. It states that interpreter startup IS this stage's cost, and that
      absolute seconds are machine-specific while the ATTRIBUTION is what this item binds to.
  - id: AC2
    text: >
      THE CONTRACT IS PRESERVED EXACTLY, PROVEN RATHER THAN ASSERTED IN PROSE. The replacement checks the SAME
      file set, derived from the same git ls-files patterns, and a selftest asserts the set the new stage
      checks is EQUAL to the set the old one checked - not a superset, not a subset - because a lint stage that
      quietly checks fewer files is the cheapest possible fake speedup. Every failure is still named by path on
      its own line, the stage still exits non-zero if any file fails, and it writes no bytecode (asserted by
      checking no .pyc appears and no __pycache__ is created). TEETH: a deliberately broken Python file and a
      deliberately broken shell file are each proven to still FAIL BY NAME, so the check is proven to still
      check.
  - id: AC3
    text: >
      IT IS FASTER AND THE FIGURE IS THE REAL ONE. The stage completes in under 2 seconds against the 14.07s
      baseline, measured by the AC1 method and recorded beside it; if the real figure lands higher, the real
      figure is what the manifest states. The stage prints its own elapsed time and per-language file counts.
      Engine canon holds: check_lint.sh is re-synced byte-identical across engine and all six packs.
      No protected path is touched, scripts/verify.sh is byte-UNCHANGED and so is the stage list (this item
      makes one stage cheap, it does not change what the gate runs), the frozen safety core is byte-UNCHANGED,
      the full gate is GREEN, and RULE #1 is clean.
required_evidence: [unit]
rollback: >
  Revert the commit. The change replaces a per-file `python3 -m py_compile` loop with a single-process
  equivalent over the identical file set, plus per-language counts and a timing line, re-synced byte-identical
  across engine and the packs. Reverting restores a correct stage that costs 14 seconds instead of
  under 1, so it is a cost regression rather than a return to a good state. Nothing else reads this stage's
  output beyond its exit status, which is unchanged, so there is no migration.
---

## Intent

Dmitry, 2026-07-25: "The gate should not take this long. It should be optimized to be 10x faster." Measured,
the whole gate is 117.1 seconds, of which the selftest is 102.4 and lint is 14.1, and every other stage
COMBINED is 0.6.

This item takes the lint stage only. `scripts/check_lint.sh` runs `python3 -m py_compile` once PER TRACKED
PYTHON FILE, serially, over 662 files. Interpreter startup IS the cost. The same 662 compiles in a single
process measures 0.70 seconds, with the shell half at 0.11.

So this is 661 process spawns deleted, and nothing else: same files, same failure reporting, same exit
semantics, no bytecode. It is separated from the rest of the gate work deliberately, per the smaller-tickets
decision of the same day, because it is fully measured and trivially reviewable and should not queue behind
the parts that are neither.

## Context

- The sibling items this was split OUT of, so a reader knows the boundary: the mobile-runner clock injection
  (about 46s, prototype-measured, zero assertion impact), the repeated derivations inside the selftest
  (4,460 ast.parse calls over only 86 distinct sources, 112,451 file opens over 9,096 paths, one dashboard
  render re-run per output line), and the process-runner fixture windows, which are contested because
  shortening them trades wall clock for flakiness. Each is its own item with its own risk.
- Why the file-set equality assertion is the load-bearing one: every other property of this change is
  obvious, and the single way it could silently cheat is by checking less. Asserting equality against the old
  stage's set is cheap and closes it.
- Why the seconds are not the criterion: the machine varies. The attribution (interpreter startup dominates a
  stage that does 662 tiny compiles) does not.

## Out of scope

- The selftest stage, which holds 102.4 of the 117.1 seconds. Its work is split across the sibling items.
- Any change to scripts/verify.sh, the stage list, or the stage order. No protected path.
- Any change to what is linted: no new rule, no new file type, no formatting or style check. This item changes
  HOW the same syntax check runs, never WHAT it checks.
- Parallelism across stages.

## Notes

- Assert the file-set equality first, then optimize. If that assertion is written afterwards it will be
  written to match whatever the new code happens to do.
- Preserve the per-file failure line verbatim. Something may be parsing it.
- Do not add a formatter or a style rule while in here, however tempting; that is a different item and a
  different argument.
- The prose rule is in force: a sentence that makes a checkable claim must be backed by an assertion, or must
  not be written. And NO UNBACKED UNIVERSAL: "every file", "no bytecode" and "the same set" each need the
  assertion that enumerates them.
- RULE #1 clean (ASCII hyphen only, no em dash, no en dash, no prose double-hyphen).
