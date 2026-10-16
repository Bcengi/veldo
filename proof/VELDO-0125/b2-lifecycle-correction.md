# Supplemental evidence correction

The passing partial-suite exit code is **2**, not 3 as stated in
`b2-lifecycle.md`. Both captured routing and relay processes exited 2 with zero
failed checks. `scripts/run_scope.py` defines `PARTIAL_PASSED_EXIT = 2` and
`PARTIAL_FAILED_EXIT = 1`. Counts and mutation outcomes in the original record
are unchanged. This added correction preserves the earlier evidence verbatim.

Mutation logs retain raw test output, including trailing spaces on empty
AssertionError messages. Those raw log lines account for the whitespace-check
findings; implementation and regression source have no whitespace-check findings.
