# VELDO-0362 Fix round 1

Review hardenings H1 and H2:

- Measured memory claims use 1.15 times the largest anonymous or retained-unit peak.
  The CPU rate and unmeasured default floor keep their existing semantics.
- Both resource-valid updates assert that the latest outcome names the callback worker.
  The mutant callback now names its argument `name`, preserving its local `identity` alias.
- Suite 115 injects mismatched baseline, no-op and mutant outcome names. It also checks
  the memory margin with both anonymous-only and retained-unit measurements. Existing
  expected claims and the memory-limited fixture concurrency reflect the added margin.
- Three new registered falsifiers remove the multiplier or one of the two assertions.
  The existing control-watchdog falsifier follows the assertion's new location.

`check_case.py CASE_NAME` runs one registered case with baseline and no-op controls,
using temporary production copies and the production result validator. JSON records
retain every observed row and exact applied diffs are adjacent. These are unit-level
single-case diagnostics, not native gate or benchmark receipts.

Gate 17 was running. No load generator, benchmark, full gate or full leg was run.
The earlier benchmark artifacts describe the pre-hardening implementation; they were
not regenerated and do not measure the 1.15 multiplier's performance effect.

Validation: suite 115 alone completed with 72 passed and 0 failed (the selector's
expected partial-run exit code is 2). All three new mutants and the moved watchdog
mutant failed at their designated rows; every baseline and no-op control was green.
The production validator labels these suite kills `unproven` because suite 115 has
existing wall-clock baseline sites; these diagnostics make no full-gate claim.
Wall-clock census passed with no new sites; personal setup found 0; the stale scan
found 0 stale anchors among 4,004 cases. Engine copy is byte-identical and
scripts/gate_unconfined.json is unchanged from 5058a7bdc. Source digests are retained.
