VERDICT: HAS DEFECTS (F1 medium, F2 medium, F3 low, F4 low, F5 low)

# Independent review of VELDO-0214: the first-use budget is measured from the unit leg

Reviewer: Claude (fresh context, did not write this change). Date: 2026-10-23.
Range: main d49581b4..3c742321, worktree at 3c742321.

## What I ran (exit statuses read directly)

- Suite 111 through scripts/selftest.py in this worktree: 31 passed, 0 failed (5 rows of the suite).
- proof/VELDO-0214/local_check.py in a scratch copy made by git archive: exit 0. Every baseline
  failed no row. Each of the four mutants failed exactly its own target row and nothing else:
  fixed-1800-restored fails measured-budget-used, caller-value-kept fails candidate-set-value-ignored,
  failed-leg-recorded fails reused-stage-uses-last-fresh, stale-docstring fails
  by-hand-uses-1800-and-says-so.
- scripts/check_template_sync.sh: exit 0. scripts/gate_legs.py and engine/scripts/gate_legs.py are
  byte-identical; both verify.sh copies unset VELDO_GATE_UNIT_SECONDS in veldo_candidate.
- An extra mutant of my own in a scratch copy (F1): suite 111 stays 5 passed.
- run_budget with a handed value of 1e308 seconds, then subprocess.run with that timeout (F4):
  budget inf, OverflowError.
- run_stage from three scratch authority copies with HOME pointed at a scratch directory (F3):
  three separate files in the leg-time store, nothing pruned.
- NOT run here: ./scripts/verify.sh, suite 101 and suite 53 (this sandbox cannot open a pty or
  nest the agent-sandbox launcher). I read host-runs.json for those.

## Question 1: can candidate code forge, raise, plant or poison the time or the variable?

The confined leg cannot. The gate profile in scripts/agent_sandbox.json writes only {worktree} and
{scratch} and lists ~/.cache/veldo under deny_read, so the confined leg can neither read nor write
the store. The variable cannot be set from outside: gate_legs._env drops a caller's value always and
sets it only for a leg, veldo_candidate unsets it on the fallback path in both copies, and
run_budget ignores by name a value outside a gate leg, a value bound to another leg or declaration
and a malformed value. A suite running in the unit leg that loads gate_legs.py with stage unit
(suite 101 does) writes under a different authority path or fixture digest, so it cannot reach the
real key; inside the confined leg the write fails, is said, and is not fatal.

The unconfined leg can. Its unit leg runs after the confined unit leg's time has been recorded, so
its code can rewrite the confined entry under the real key, give it any seconds, and even mark it
"this gate run" by copying the run's record path. The spec's first limit covers this in substance
and I agree it is harmless to the verdict: the budget only decides how long the gate waits before
CANNOT ANSWER, which is red. A larger budget can only let an honest nested run finish and be judged
on its own failures; it cannot turn a regression green. A smaller budget than 1800 is impossible
because of the floor. A stale large value left by one gate is overwritten by the next gate's passing
unit leg before its integration stage reads it; it is read only when that unit leg failed, and then
the gate is already red. The second limit (a candidate slowing its own unit leg) is likewise only
liveness. So the remaining effects are liveness only: the gate can be made to wait without bound
(F4), and the docstring overstates the guarantee (F5).

## Question 2: floor, named fallback, failed leg, reused stage

Holds. max(1800, 2.0 x s) is never below 1800 and every fallback prints the floor with a reason.
record_time runs only on code 0. measurement reads the last fresh value for the same authority, the
same declaration digest and the same leg, labelled "an earlier gate run" when the run id differs.
The reused-stage case is exercised as "unit failed, then integration", which is the only way to
reach it today since VELDO-0206 does not exist yet.

## Question 3: rows and falsifiers

Each falsifier fails exactly its row (reproduced). The rows have one gap (F1), and the integration
evidence that the spec's required_evidence and HOST_RUNS.md step 3 call for does not exist yet (F2).

## Question 4: is a file cache under the home the right store?

Yes for the location. .veldo/last_verify and .veldo/events.jsonl live in the worktree, which the
confined leg can write, so a measurement kept there would be forgeable by exactly the code the
budget is about. ~/.cache/veldo is the store the gate already denies to the confined leg (the reuse
store gate-reuse-v2 sits beside it), so it is the right trust boundary. It is not bounded (F3).

## Findings

### F1 (medium): no row proves the measured budget is the timeout of the runs main() makes

- Where: scripts/check_first_use.py:460 and scripts/check_first_use.py:468.
- Scenario: delete the third argument at both call sites, so they read
  _run_suite(tree, "mutated(...)") and _run_suite(pristine, "baseline"). Every nested run is back on
  the 1800s default, which is the exact defect this spec fixes, while main still prints "budget per
  nested run: 2277s". I applied that mutant in a scratch copy: suite 111 reports 5 passed, 0 failed.
  The row measured-budget-used calls _run_suite directly with the budget, and drives main only far
  enough to print the budget line (SELFTEST is pointed at a missing file, so main returns before any
  run). AC1's claim "it is the timeout of every nested run" is therefore unproven for the code path
  the gate uses.
- Fix: in the row, let main reach the mutated run (a pristine fixture tree, a fake subprocess.run
  that records its timeout and returns a summary with one failure so the baseline run happens too)
  and require every recorded timeout to equal the budget. Register the mutant above as a fifth
  VELDO-0214 case targeting that row.

### F2 (medium): the integration evidence is missing and suite 101 did not complete on the host

- Where: proof/VELDO-0214/HOST_RUNS.md (step 3 "not yet run") and proof/VELDO-0214/host-runs.json.
- Scenario: required_evidence is [unit, integration], and HOST_RUNS.md names ./scripts/verify.sh as
  the integration evidence for AC1 and AC3; it has not been run. Suite 101, the leg runner's own
  rows, failed two sandbox rows and then aborted on an exception in _v208_case_input_proposal
  (scripts/suites/101_veldo_0208_landing_reuse.py:2164). Everything after that call never ran on any
  host, including _v208_mutation_leg (line 2331), which loads the changed gate_legs.py. The diagnosis
  that the failures predate this change is reasoned from unchanged files, not shown: there is no run
  of suite 101 at main d49581b4 on the same host.
- Fix: run suite 101 at d49581b4 on the same host and record that it fails the same two rows and the
  same exception; get a run of suite 101 that reaches _v208_mutation_leg with this change; run
  ./scripts/verify.sh and record GATE: GREEN with the leg times, the "budget input" lines and the
  check's budget line. Until then this cannot land.

### F3 (low): the leg-time store is never pruned, and suite 101 adds a file to the owner's store on every run outside the confinement

- Where: scripts/gate_legs.py:83 (LEG_TIMES), scripts/gate_legs.py:161 (record_time), and
  scripts/suites/101_veldo_0208_landing_reuse.py:1568 (through_stage with a fresh temporary
  authority).
- Scenario: the key is sha256(authority path, declaration digest), so every checkout path and every
  declaration revision leaves its own file forever. Reproduced: run_stage from three scratch
  authority copies with HOME in scratch left three files. In practice each agent worktree is its
  own authority, every edit to gate_unconfined.json orphans every existing file, and suite 101's
  through_stage copies gate_legs.py into a new temporary authority each run, so running suite 101
  by hand on the host (as host-runs.json did, twice) writes a new file into the owner's real
  ~/.cache/veldo/gate-leg-seconds each time. Small files, but unbounded, and a suite writing the
  owner's store is a hermeticity leak.
- Fix: in record_time, after the atomic replace, remove files in the store whose recorded authority
  path no longer exists or whose mtime is older than a stated age (for example 30 days). Keep suites
  out of the real store, for example by having gate_legs.py skip recording when the authority path is
  under the system temporary directory, or by giving suite 101's drivers a scratch HOME. Do not add an
  environment override for the store path: that would be a new forgery input.

### F4 (low): no ceiling on the budget; a huge stored value removes the bound, and an overflowing one crashes with a traceback

- Where: scripts/check_first_use.py:312 and scripts/gate_legs.py:188.
- Scenario: a stored seconds of 1e9 (finite, accepted by both checks) gives a budget of 2e9 s, so a
  hung nested run is never cut off and the gate never ends. A stored 1e308 passes both finiteness
  checks, 2.0 x 1e308 is inf, and subprocess.run raises OverflowError, which _run_suite does not
  catch: the check exits through a traceback rather than CANNOT ANSWER with the reason named,
  against the docstring's FAILING LOUD rule. Only the unconfined leg or the owner can write such a
  value, and both outcomes are red or hang rather than green, hence low.
- Fix: cap the budget (for example min(max(1800, 2.0 x s), a stated ceiling such as 6 hours)) and
  print the cap when it applies; reject a seconds value whose budget is not finite.

### F5 (low): the docstring overstates who can forge the value, and the spec's rollback miscounts the mutation cases

- Where: scripts/gate_legs.py:60 ("so a candidate cannot set or forge it") and
  specs/VELDO-0214-first-use-budget-measured-from-the-unit-leg.md:78 ("the three mutation cases").
- Scenario: as in question 1, candidate code in the unconfined unit leg can rewrite the confined
  entry after it is recorded and before the integration stage reads it, labelled "this gate run".
  The docstring says without qualification that a candidate cannot. The rollback names three cases;
  four are registered (manifest.json says four).
- Fix: say the candidate cannot set the variable, the confined leg cannot reach the store, and the
  unconfined leg can rewrite it with the owner's authority as VELDO-0208 already allows, bounded by
  the floor and (after F4) the ceiling. Change "three" to "four".

## Question 5: elsewhere in the range

No other defect found. The suite renumbering to 111 is consistent across manifest.json,
requires.json, the mutation registry and the proof; the leg line text change keeps suite 101's
substring checks ("unit: confined leg: pass") matching; _child_env drops the variable so the nested
suite does not inherit it.
