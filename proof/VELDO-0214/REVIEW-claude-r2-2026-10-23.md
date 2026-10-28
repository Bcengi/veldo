VERDICT: HAS DEFECTS (F6 medium, F7 low)

# Fix check of VELDO-0214, round 2

Reviewer: Claude (fresh context, did not write this change). Date: 2026-10-23.
Range: 3c742321..2b8e4730, worktree at 2b8e4730. Scope: the round 1 findings F1, F3, F4, F5 and the
new AC5 and AC6. Focused check, not a full review.

## What I ran (exit statuses read directly)

- Suite 111 through scripts/selftest.py: 9 passed, 0 failed (exit 2, the PARTIAL RUN status).
- scripts/check_teeth_mutations.py --finding 214: exit 1, candidate_execution_denied (this sandbox
  cannot nest the agent-sandbox launcher). I relied on host-runs.json for it and reproduced the
  cases by hand instead.
- By hand, in scratch copies made by git archive HEAD, suite 111 per mutant (exit 1 means a row failed):
  - budget214-fixed-1800-restored: fails measured-budget-used and ceiling-caps-the-budget.
  - budget214-main-drops-the-budget (both call sites): fails the same two rows.
  - my own: only the mutated call site dropped, and only the baseline call site dropped: each fails
    the same two rows.
  - my own: no ceiling (budget = max(RUN_TIMEOUT_S, derived)): fails ceiling-caps-the-budget only.
  - my own: finiteness check skipped: fails non-finite-budget-refused only.
  - my own: prune call removed, gone-checkout test removed, age test removed: each fails
    leg-time-store-pruned only.
  - my own: owner-store guard removed, temporary-directory test removed, own-list test removed:
    each fails suites-stay-out-of-the-owner-store only.
  - my own: the keep test in prune_times removed: SURVIVES, 9 passed (F7).
- run_budget over bound values: 10800 gives 21600 uncapped; 10800.5 gives 21600 with CAPPED;
  1e9 gives 21600 with CAPPED; 1e308 gives 1800, "not a finite number of seconds"; nan, inf, -5,
  0 give 1800, "no usable seconds"; a string gives 1800, "not the authority's form". No traceback.
- owner_store_refusal and run_stage driven from a copy of scripts/ laid down the way the lander
  lays down its installation (tempfile.mkdtemp(prefix="veldo-observation-") / "installed"): both
  unit legs "not recorded in the owner's store: ... is a temporary tree", and both integration
  legs "no unit ... leg measurement recorded" (F6). A checkout under a directory named tmp outside
  the system temporary directory, and one reached through a symlinked directory: both accepted.
- NOT run here: ./scripts/verify.sh, suites 101 and 53.

## 1. F1: fixed

The row now drives main() over a fixture tree whose fake nested run reports one failure, so the
mutated run and the lazy baseline run both happen, and requires labels ['mutated-spend_recorded',
'pristine'] with every timeout equal to 2276.8. The registered mutant and each single-site variant
fail it.

## 2. F3: the pruning holds; the guard refuses a legitimate gate (F6)

Pruning: only names matching the store's own pattern ([0-9a-f]{32}.json, and .pending- files by age
only) are considered; a file is removed only if older than 30 days or its recorded authority does
not exist; unreadable files are kept; errors are said and not fatal. The recorded authority is
HERE.parent with HERE resolved, so a relative path cannot be judged against the wrong cwd. A
symlinked home is harmless: LEG_TIMES is compared to itself, and the authority and the temporary
directory are both resolved. Two gates at once: each keeps its own file and never removes the
other's while that checkout exists and is younger than 30 days; a pending file of a concurrent
writer is never removed by the gone-checkout test. No environment override for the store path was
added. A gate run inside the agent sandbox has HOME and TMPDIR in its scratch, so it never sees the
owner's store.

The guard: suite 101's drivers are refused correctly (the fixture list fails the own-list test, the
temporary authority copy fails the temporary-directory test). But the temporary-directory test also
refuses the lander's own landing gate, see F6.

## 3. F4: fixed

min(max(1800, 2.0 x s), 21600), the cap printed with CAPPED and the uncapped figure, and a value
whose budget is not finite falls back to 1800 by name. main() over 1e308 returns 0 with every
nested timeout 1800 and no traceback.

## 4. F5: fixed, with one sentence made wrong by F6

The "who can touch the value" paragraph is accurate, and the rollback counts five mutation cases,
matching the five registered. The store paragraph (scripts/gate_legs.py:73) says a temporary
authority copy is a suite "testing the runner, not timing the gate"; for the lander's installation
that is false.

## 5. AC5 and AC6

AC5 is a sound requirement and its rows prove it. AC6's pruning and own-list parts are sound and
proven. Its temporary-directory clause is the requirement F6 shows to be wrong, and its "never the
file just written" clause is not proven by any row (F7).

## Findings

### F6 (medium): the landing gate's own measurement is refused, so a lander without a host installation directory is back on the fixed 1800s

- Where: scripts/gate_legs.py:245 (the temporary-directory test in owner_store_refusal), with
  .veldo/lander.py:746 and .veldo/lander.py:732; the same clause in the spec at lines 101 and 139
  and the docstring at scripts/gate_legs.py:73.
- Scenario: with no installation and no observations directory configured (both default to None,
  .veldo/control_landing_station.py:313 passes them through from the land config), the lander lays
  down the watermark's scripts/ and .veldo/ in tempfile.mkdtemp(prefix="veldo-observation-") /
  "installed" and runs that copy's scripts/verify.sh in candidate mode. VELDO_AUTHORITY is that
  directory, so gate_legs.py's authority is under the system temporary directory and its own
  gate_unconfined.json is the list. Every passing unit leg prints "not recorded in the owner's
  store: ... is a temporary tree", every integration leg gets "no unit ... leg measurement
  recorded", and check_first_use.py uses 1800s: the exact failure this spec fixes ("did not finish
  inside 1800s", CANNOT ANSWER, red) returns for every such land. At 3c742321 the same gate recorded
  its unit leg and handed it to its own integration stage in the same run. Reproduced above with a
  lander-shaped copy.
- Fix: drop the temporary-directory test; keep the own-list test, which already refuses suite
  101's fixture-list driver. Keep suite 101's temporary authority copy (through_stage,
  scripts/suites/101_veldo_0208_landing_reuse.py:1557) out of the owner's store from the suite
  side instead, for example by giving that driver a scratch HOME. The lander's per-land
  installation files are then removed by the gone-checkout prune once the observation directory
  is deleted, or by the 30-day age. Change AC6, the design text and the docstring to match, and
  add a row that runs a unit and an integration stage of an authority's own list under the
  temporary directory and requires the measurement to be handed on.

### F7 (low): "never the file just written" is claimed by AC6 but no row can fail without it

- Where: scripts/gate_legs.py prune_times (the entry.name == Path(keep).name test) and the
  leg-time-store-pruned row in scripts/suites/111_veldo_0214_first_use_budget.py.
- Scenario: remove the keep test; suite 111 stays 9 passed. The file just written is always fresh
  and its authority (the running checkout) always exists, so the row's "written file left" check
  holds whether or not the guard is there. The guard is harmless defence, but AC6 states it as a
  proven property.
- Fix: in the row, also call GL.prune_times on a scratch store with keep naming a planted file
  that is 31 days old or whose authority is gone, and require that file to stay; or drop the
  clause from AC6.
