# VELDO-0206 build report

Builder's report, not a review and not a gate result. The canonical gate was not run in this
build; the lead queues it. Every criterion in manifest.json is pending until then.

## What was built

Suite result reuse in the canonical gate, by explicit qualification only.

- scripts/gate_reuse.py (engine copy identical) gains three authority steps. suite-plan gives
  every manifest suite one exact key, or the named reason it has none, and looks up an
  authenticated passing record for each key in the VELDO-0205 store. suite-settle reads the
  dispatcher's own account back from the unit stage's output, requires a result for every manifest
  suite, computes every key again, publishes fresh passing results and writes the receipt.
  suite-stamp puts the receipt's reused count into the stamp's reused.unit.
- scripts/run_scope.py holds the qualifications (SUITE_REUSE, a literal the authority reads with
  ast and never imports) and the dispatcher's plan rules. scripts/selftest.py leaves out only what
  the plan names and prints one account line per suite.
- scripts/verify.sh plans before the catalog, settles after it and stamps. engine/scripts/verify.sh
  only drops a caller's plan variable: the generic catalog plans nothing.
- scripts/suites/157_veldo_0206_suite_reuse.py and finding 206 in scripts/check_teeth_mutations.py.

## No production suite is qualified

SUITE_REUSE is empty. Every production suite still runs fresh in every gate and no speedup is
claimed. The suites share one mutable namespace and many reach host services; a qualification is
a reviewed statement about one suite's inputs, and none was reviewed in this build. What this
build delivers is the mechanism, its receipts in every gate, and the tests that it cannot let a
stale or partial result stand in for a fresh one.

## Decisions the reviewer and the lead should judge

1. Where qualifications live. The footprint allows no new file, and manifest.json is not a
   protected path, so qualifications are a literal in scripts/run_scope.py, which policy protects
   at floor high. Qualifying a suite is therefore an owner-approved change. Consequence: changing
   any qualification changes the dispatcher's file, so every qualified suite misses once.
2. Who decides. The confined dispatcher cannot open the store, so the authority plans and settles
   around the stage and hands the dispatcher only the names it may leave out, in
   VELDO_SUITE_REUSE, bound to one root and one run's nonce. The dispatcher removes the variable
   from its environment, so no process a suite starts inherits it.
3. What a key holds. For the suite and every member of its prerequisite closure
   (scripts/suites/requires.json): the suite file, its manifest entry, its qualification and the
   content, names and modes of every declared input. Beside them the shared preamble, the two
   dispatcher files, the authority identity, the authority's unconfined list, the declared runtime
   trees (they must cover the interpreter, its library, sh, bash and git), the named environment
   values and the root. A qualification also pins the digest of the code it reviewed; an edit to
   the suite, a prerequisite or the shared preamble is an unknown closure until reviewed again.
4. Prerequisites. A suite that runs fresh has its whole closure executed first, a reusable
   prerequisite included; that one is then reported fresh with reason prerequisite_of_fresh.
5. Never reused: a selector run, a reordered run, the unconfined leg, a suite the unconfined list
   names (whole or by rows) or that depends on one, a run at another root (the integration stage's
   copy, an unconfined leg's snapshot).
6. Landing. .veldo/reuse_evidence.py (outside this footprint, unchanged) refuses any stamp whose
   reused.unit is above 0, so a gate that reused a suite cannot land. VELDO_GATE_FORCE_FRESH=1
   reads and writes no suite record. Suite 157 asserts both.
7. The receipt. Like the mutation receipt it is a file of the run (a private temporary folder),
   printed line by line in the gate output: one line per suite with source, key and reason, and
   one count line. Only reused.unit enters the stamp and the event; adding a stamp field would
   have needed .veldo/reuse_evidence.py and run_scope's stamp shape to change together.
8. A new way to be RED. With the dispatcher as unit stage, a gate is RED when the settlement
   cannot account for every manifest suite behind a passing stage, when no plan could be made, or
   when a reused result is not the plan's. With no legs the serial unit stage's output is written
   to a file and printed when the stage ends, not streamed.
9. Trust boundary, as VELDO-0205 states it: the per-suite result is the dispatcher's own account,
   candidate code, exactly as its exit status is. A suite that forged another suite's line could
   publish a false record for that suite's key. Review of the candidate is the safeguard; this
   build adds none.

## Outside the footprint

- proof/WARP-0716/crossing-state.md is a derived survey of scripts/selftest.py that
  scripts/check_generated.sh holds fresh. The dispatcher changed, so it was regenerated.
- docs/ were not changed. The operator-facing description of the gate does not yet mention suite
  reuse; with no qualified suite nothing an operator does changes.
- .veldo/policy.yaml: nothing changed. scripts/suites/manifest.json stays unprotected, which is
  why the qualifications are not in it.

## What was run

See targeted-tests.json, teeth.json and whole-suite.json. Not run: scripts/verify.sh, the
integration stage (scripts/check_first_use.py), the mutation stage beyond finding 206, and the
gate under the graph scheduler. The graph path is covered by a row that settles scheduler-shaped
node output with the gate's own command and by reading scripts/gate_schedule.py; no scheduler ran.

## The whole-suite run was red, and why that is not this change

The whole unit suite under a real plan ended 10556 passed, 16 failed: 7 rows of
102_veldo_0210_agent_profile_runtime and 9 rows of 151_veldo_0313_space_run, on a host shared with
other builders. The settlement accounted for all 237 suites as fresh and reported the stage failed,
as it should. Suite 102 alone passes (263 passed, 0 failed). Suite 151 alone fails 9 rows on this
branch and 7 rows on the base commit 23318512 with none of this ticket's changes, a different set
each time. Those failures predate this build and were not investigated here. No whole-suite pass is
claimed.
