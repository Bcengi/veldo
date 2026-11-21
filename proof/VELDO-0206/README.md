# VELDO-0206 build report, fix round 1

Builder's report, not a review and not a gate result. The canonical gate was not run in this
build or in this fix round; the lead queues it. Every criterion in manifest.json is pending until
then. This round answers the review of a27ec1c4 (verdict FIX, findings 1 to 5).

## What is built

Suite result reuse in the canonical gate, by explicit qualification only, with every qualified
suite run in a process of its own.

- scripts/gate_reuse.py (engine copy identical) has three authority steps. suite-plan gives every
  qualified suite one exact key, or the named reason it has none, looks up an authenticated passing
  record for each key in the VELDO-0205 store, and makes the unit stage's output files.
  suite-settle reads the dispatcher's account back from the unit stage's output, requires a result
  for every manifest suite, computes every key again, publishes passing isolated results and writes
  the receipt. suite-stamp puts the receipt's counts and keys into the stamp's and event's fields.
- scripts/run_scope.py holds the qualifications (SUITE_REUSE, a literal the authority reads from
  its own copy with ast and never imports) and the dispatcher's plan rules. scripts/selftest.py
  starts one process per isolated suite, leaves out what the plan lets it, and prints one account
  line per suite.
- scripts/verify.sh plans, hands the plan to the unit stage only, settles and stamps.
- scripts/suites/157_veldo_0206_suite_reuse.py and finding 206 in scripts/check_teeth_mutations.py.

## Finding 1: the design chosen, and why

The review's counterexample was reproduced first on a27ec1c4 with the review's own probe
(counterexample-at-a27ec1c4.txt): the warm run reuses e and is green, the force-fresh run of the
same tree is red.

The fix is isolation, not a wider key. A suite observed in the shared namespace can see
everything every earlier suite left: names, modules, environment, working directory, process
state. A key could name the earlier suites' files, but what an earlier suite leaves depends on
that suite's own inputs, and an unqualified suite declares none. A key that did cover it would
need every earlier suite qualified, would miss on any change to any of them, and would still be
wrong the other way round: leaving a suite out removes its side effects from the suites after it.
So the key cannot be made complete for an observation made in the shared namespace.

Instead a qualified suite never sees that state:

- In every gate, reusing or not, force fresh or not, a qualified suite runs in a process of its
  own. The dispatcher starts these processes before any suite has run in it, each with the
  environment and working directory the dispatcher itself was started with. The process holds the
  shared preamble and the suite's prerequisite closure in manifest order, and nothing else.
- The suite's result in the gate is that process's result. A record is published only from such a
  run and stands in only for such a run, so a reused pass and a fresh run of the same tree are the
  same observation. A record of a shared-namespace observation is not a valid record
  (scope must be "isolated"; key, result and plan schemas moved to v2, so nothing stored by the
  earlier build can hit).
- Which suites are isolated depends on the tree and the authority only, never on the store or on
  force fresh. A suite an unqualified suite lists as its prerequisite stays in the shared
  namespace and has no key (prerequisite_of_shared). If any unqualified suite's prerequisites are
  not on record, no suite has a key (dependents_unknown).
- A qualification carries one more reviewed statement, side_effects "none": the suite leaves
  nothing outside its own process that another suite reads.
- The settlement publishes nothing observed in the shared namespace, and a qualified suite that
  ran there behind a passing stage is RED on its own.

The counterexample is row closure/state-left-by-an-earlier-suite-cannot-hide-a-failure: e fails
in the first run, after d changes, and under force fresh alike, and nothing is ever stored for it.
The same row holds the converse (d sees nothing the isolated a left) and process state (t sees
neither d's names nor d's change to the environment). Falsifier
suite206-qualified-suite-runs-in-shared-namespace turns it red.

What isolation does not cover, stated plainly: files and host state outside the repository that
one suite writes and another reads. Declared inputs are in the key and are read again at
settlement; anything else is the qualification's reviewed statements (non_file_inputs,
side_effects), as in VELDO-0205. No production suite is qualified, so nobody has made those
statements for a real suite yet.

## Findings 2 to 5 and the notes

2. Qualifications come from the authority. gate_reuse.suite_registry reads scripts/run_scope.py
   beside the gate_reuse.py that runs, never the candidate's. A candidate that adds an entry or
   declares fewer inputs changes nothing until it lands. Row closure/candidate-cannot-qualify-itself,
   falsifier suite206-candidate-qualifies-itself.
3. The plan is the unit stage's alone. verify.sh no longer exports it: veldo_planned sets it for
   the serial unit stage, or for the scheduler under the graph. The scheduler copies its
   environment to every node and is outside this footprint, so the plan is also bound to the unit
   stage's output files: the plan step makes unit.log, unit.confined.log and unit.unconfined.log
   and names their device and inode, and a dispatcher whose standard output is none of them honors
   nothing. Rows pass-only/plan-reaches-only-the-unit-stage and
   receipts/gate-hands-the-plan-to-the-unit-stage-only; falsifiers
   suite206-plan-exported-to-every-stage and suite206-plan-honored-on-any-output.
4. The settlement checks prerequisites. An isolated run must have executed exactly the suite's
   closure, in order, all fresh; otherwise it is RED and nothing is stored. A shared-namespace
   suite beside a prerequisite that was left out or ran only in its own process is RED. Row
   receipts/fresh-suite-without-its-prerequisites-is-red-and-not-stored; falsifiers
   suite206-isolated-closure-not-settled and suite206-shared-prerequisite-not-settled.
5. The keys are in the gate's receipts. The stamp and the gate event carry a suites field: the
   registered, fresh, reused, not_run and qualified counts, and for every suite that has a key the
   key beside its source. An unqualified suite has no key and is in the counts. Row
   receipts/gate-stamp-and-event-carry-exact-keys-and-counts; falsifier
   suite206-stamp-drops-suite-keys. The full per-suite receipt is still a file of the run, printed
   line by line.
- Untested branch the review named (no plan could be made): row
  receipts/gate-is-red-when-no-plan-could-be-made, falsifier suite206-unplanned-gate-not-settled.
- Where qualifications live: unchanged, a literal in protected scripts/run_scope.py, now read from
  the authority. The review's better home (a dedicated protected file) needs a new file and a
  policy entry, both outside this footprint; it belongs with the first real qualification.

## Assertions changed in suite 157, and why

No row was removed. These expectations changed because the execution model changed:

- Traces. A run with nothing on record executes a, a, b, c, e, t, then d: isolated suites first, a
  twice (its own run, and as b's prerequisite in b's process). It was a, b, c, d, e, t.
- A fresh dependent beside a reusable prerequisite. b runs fresh and executes a in b's process; a
  itself stays reused (reason hit). The reason prerequisite_of_fresh no longer exists. Mixed
  counts are 2 fresh, 4 reused, 1 published (were 3, 3, 2).
- Force fresh. The qualified suites still have keys and still run isolated; the store is neither
  read nor written. Reasons are force_fresh for the five and unqualified for d, qualified is 5
  (was 0 with every reason force_fresh).
- The stamp fields always carry suites, so the cold stamp is no longer the unchanged text.
- A run ended early in t leaves d not run as well, because the shared namespace runs last.
- A reordered full run with qualified suites is now a red settlement (they ran in the shared
  namespace). It stored and reused before.
- The run that is ended early is synchronized through a FIFO the suite opens, because the
  dispatcher's output is now a file, not a pipe. Still no sleep and no elapsed time.

## Decisions the reviewer and the lead should judge

1. Force fresh keeps isolation. Landing gates therefore run a qualified suite the same way every
   other gate does. The alternative (force fresh runs everything in the shared namespace) would
   let a non-landing green and a landing red disagree about the same tree.
2. The output binding under the graph is not driven by a real scheduler here. It rests on
   gate_schedule.py opening `directory / (name + '.log')` for writing without replacing the file,
   which the graph row checks by text. If that changes (VELDO-0358 touches the file), a dispatcher
   finds no bound output, runs every suite in the shared namespace, and the settlement is RED once
   any suite is qualified. With no qualified suite the plan names nothing and nothing changes.
3. An isolated suite's counts come back to the dispatcher in a temporary file of the run; the
   dispatcher waits for the process to exit and for nothing else, with no deadline of its own.
4. The aggregate line counts an isolated suite's own rows once. Rows of its prerequisites asserted
   again inside its process are not added; a failure there is the suite's failure.
5. Stamp size: the suites field grows by about 90 bytes per qualified suite, in the stamp and in
   each gate event.
6. Trust boundary, unchanged from VELDO-0205: the dispatcher's account is candidate code, as its
   exit status is.

## No production suite is qualified

SUITE_REUSE is empty. Every production suite runs in the shared namespace in every gate, no
process is started for any suite, and no speedup is claimed.

## Outside the footprint

- proof/WARP-0716/crossing-state.md is a derived survey of scripts/selftest.py that
  scripts/check_generated.sh holds fresh; it was regenerated again.
- scripts/gate_schedule.py and .gitignore were not changed, which is why finding 3 is closed by
  binding the plan to the output files and finding 5 by fields in the stamp, not by a new file.
- docs/ were not changed.

## What was run in this round

All through the host heavy-run wrapper, in one slot, at 6de07820 with a clean tree before and after.

| run | result |
|---|---|
| selftest --suite 157_veldo_0206_suite_reuse | 91 passed, 0 failed, exit=2 |
| selftest --suite 99_veldo_0205_reuse | 55 passed, 0 failed, exit=2 |
| selftest --suite 101_veldo_0208_landing_reuse | 216 passed, 0 failed, exit=2 |
| selftest --suite 14_warp_0717_subset_runner | 53 passed, 0 failed, exit=2 |
| selftest --suite 113_veldo_0220_gate_host | 29 passed, 0 failed, exit=2 |
| selftest --suite 114_veldo_0220_gate_scope | 27 passed, 0 failed, exit=2 |
| selftest --suite 114_veldo_0216_concurrent_stages | 52 passed, 0 failed, exit=2 |
| selftest --suite 153_veldo_0309_gate_space | 50 passed, 0 failed, exit=2 |
| selftest --suite 27_veldo_0010_evidence_provenance | 52 passed, 0 failed, exit=2 |
| check_teeth_mutations.py --finding 206 --jobs 4 | mutations: passed registered=32 executed=32 reused=0 rejected=32, exit 0 |
| the review's probe on a27ec1c4, before the fix | warm run reuses e and exits 0; forced run exits 1 |

A selected run exits 2 when green, by design. For each of the 32 falsifiers the baseline and the
no-op run fail no row and the mutant fails every row the case names; teeth.json lists them. The 22
cases of the first build are all still registered: eight had their target text moved to the new
code (dispatcher-skips-prerequisite, partial-run-published, partial-record-accepted,
unfinished-run-published, failed-run-published, selector-run-reused, force-fresh-ignored,
unauthenticated-reuse-accepted). Ten are new, one or more per finding.

Fast checks: lint, template sync, generated, personal setup (0 findings) and the four boundary
checks pass.

Not run: scripts/verify.sh, the integration stage, the mutation stage beyond finding 206, the gate
under the graph scheduler, and the whole unit suite. whole-suite.json and
whole-suite-settlement.txt are from the first build (ad8df006) and were not repeated: with no
qualified suite the dispatcher's path for a production run is the shared namespace as before, but
that is an argument, not a run.
