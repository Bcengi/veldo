# VELDO-0294 phase 2

Phase 2 stops at the session boundary. The build is not ready for review or
landing. No acceptance criterion is claimed passed. No heavy command ran.

Commits:

- 5a0f12c8 adds the per-phase stand-in, incremental markers and seven phase rows.
- 3d4475d9 adds token files, mark validation and replay controls, the reporter's
  ten examples, row prefixes and drain-time exhaustion fixtures.
- a2d33282 fixes unknown totals in token files and fixture interface mismatches.

All seven production modules match their runtime copies. The receiver now writes
null for a token or message total that the ledger still marks unknown. Its charge
is otherwise unchanged. A marked replay can journal an empty transition under a
new delivery command; the row checks that neither the invocation nor settlement
changes. This follows the existing ledger behavior without changing old rows.

Offline results, all under user scopes with MemoryMax=10G:

- Suite 72: 19 suite checks, 45 total checks, zero failures.
- Suite 75 after the receiver fix: 26 suite checks, 52 total, zero failures.
- Suite 58 after that fix: 10 suite checks, 36 total, zero failures.
- Suite 78 after that fix: 34 suite checks, 60 total, zero failures.
- Suite 82 remains red. Its latest run had 27 total passes and 35 failures because
  a fixture exception marks every row failed. The fake-format capture passed.

Selected green runs exit 2 by contract. These are offline diagnostics, not gate
or acceptance evidence. Compilation passed for all phase 2 touched Python files.
Personal setup reported 0 findings, with no installation found and only built-in
shapes checked. No hook or command guard rejected an invocation.

The first two suite 82 failures were fixed: a separately loaded Refused class
escaped the expected-refusal handler; source payloads need their commit compared,
not the whole contract source object; isolated projects need a project entity;
and artifact files live beside the database, not at the fixture root.

The current suite 82 failure is TypeError: int object is not iterable in its
lines(document) helper. Claude Terminal stores stream.lines as an integer count.
The design, section 3.1 around lines 239 to 240, describes it as event lines.
Codex stores its actual lines. Do not replace the required artifact usage sums
with meter counters or fake marker data. AC10 requires the artifact's usage
lines; preserve that claim. Resolve this within the allowed production modules,
retaining compatibility for existing consumers of the count. Mention the design
field-name mismatch in the implementation commit. The acceptance criteria and
footprint have not been edited.

Next phase, in order:

1. Resolve the Claude artifact usage-line mismatch and update suite 82's accessor.
   Inspect only the relevant Terminal, Metering._artifact and artifact consumers.
   Keep the existing count if consumers depend on it. Sync every production edit
   to its runtime copy before running anything. If satisfying the AC requires a
   path outside the footprint, stop and report it.
2. Run offline suite 82 and fix remaining fixture or production failures. Its new
   rows have not yet completed. The exhaustion cases must latch phase_cap before
   SIGTERM drains usage: Claude prints a 200-token assistant; Codex completes its
   second turn with 200 tokens and opens another, for 205 tokens and two completed
   turns with in_flight 1. Assert the marked settled invocation before refusal of
   continuation. Keep combined, cap-only, window-only and first-turn controls.
3. Rerun old ledger suites 58, 75 and 78 after any receiver or ledger change. Run
   suites 82, 75 and 72 against synced final modules for green baselines. Review
   new rows against design section 8 before registering mutants. Suite 75's
   existing rows remain unchanged; its added rows run after those old checks.
4. Register the nineteen mutants after green baselines. No case has been added
   yet. Check exact anchors against the final code and include VELDO-0294 in each
   expected row. Do not run teeth here.
5. Finish heavy_runs.sh. It still refuses to start without registrations and has
   not run. Check red-before parsing: copied suite 72 now intentionally expects
   the new event in old registry rows too, so the current requirement that the
   total failure count equal only the new rows needs review. Require each named
   new row to fail and account explicitly for changed old registry expectations.
   Keep old-tree fallback answers in suite 82. Summaries must stay small; do not
   retain raw output. All red-before, green-after and teeth work belongs there.
6. Add the four resource qualifications, both VELDO-0127 live captures, and suite
   86 to that script, in that order. Inspect their actual CLI options first and
   respect the Claude login lease. These captures are stale. The lead alone
   queues the script through the gate lock; do not acquire or wait on the lock.
7. Refresh the pending manifest and summaries, run proof-files and proof,
   compilation and personal setup, then commit the next handoff or finished work.

Proof-files and the pending manifest validation both passed.
No mutants, qualifications, live captures, teeth, loaded or gate runs were done.
