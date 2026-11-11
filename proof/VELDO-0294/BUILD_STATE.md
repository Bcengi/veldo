# VELDO-0294 phase 1

Phase 1 stops after the trace and production code, as requested. The feature is
not ready for review or landing. The spec and design were read in full.

Commits: 8189b9e8 adds the ledger mark and pass-through. f0434486 adds engine
steps, receiver settlement and token files, the phase loop and safe readers, and
the journal reporter. All seven engine modules match their .veldo runtime copies.

The old suites ran before receiver changes and again afterwards, in user scopes
with MemoryMax=10G. Suite 58_veldo_0036_reservations had 10 suite checks and
36 total checks, suite 75_veldo_0062_accounts had 24 and 50, and suite
78_veldo_0160_account_pool had 34 and 60. All six runs reported zero failures.
Selected runs exit 2 by contract and are not gate evidence. An initial selector
58 was rejected as unknown; the full suite name worked. No hook or guard blocked
a command. Compilation passed for all touched modules. Personal setup reported
0 findings, with no installation found and only built-in shapes checked.

Next phase, in this order:

1. Extend suite 82's stand-in for per-phase answers and incremental markers. It
   currently returns one whole build and has no done boolean, so it needs the
   design's fixture changes before its baseline. Keep an old-tree fallback for
   red-before runs. Add all seven phase rows, including direct brief/preflight
   checks, unsafe-head variants, state-note bytes and cap controls.
2. Add suite 75's two token rows and the mark validation/replay controls. Keep
   its old rows unchanged. Add suite 72's seven settled invocation examples and
   extra boundary cases through the real ledger. Update registry expectations
   and all three row-prefix emitters. The production reporter registry now has
   run_over_tokens; suite 72 still expects the old registry.
3. Apply the review correction recorded in TRACE.md. Exhaust allowance during
   the drain after phase_cap, never on the preliminary completed turn. Cover
   combined, cap-only, window-only and exhausted policies for both engines.
4. Run the permitted offline suites 82, 75 and 72 on synced copies. Fix failures
   within the footprint. All new acceptance rows are still unexecuted.
5. Register the nineteen mutants only after green baselines. Match exact anchors
   to the code now present. Keep all heavy execution in heavy_runs.sh for the
   lead. The script has red-before scratch runs, green-after runs and each mutant,
   but refuses to start until the missing rows and registrations exist. Check its
   failure-row parsing against the completed emitters before queueing it.
6. Finalize heavy_runs.sh with qualification of four resource records followed
   by both VELDO-0127 captures, then suite 86. Inspect the actual qualification
   and live-capture CLI options first. Respect the Claude login lease. These
   captures are currently stale because their bound production modules changed.
7. Refresh the pending manifest and summaries against the final implementation
   commit. Run proof-files, proof, compilation and personal setup. The lead owns
   heavy runs and any later gate work. Do not run the gate or wait on its lock.

Do not edit acceptance criteria or the footprint. No new suite rows or mutants
were registered in phase 1. No acceptance criterion is claimed passed. The heavy
script has not run and is not ready to queue until the steps above are complete.
