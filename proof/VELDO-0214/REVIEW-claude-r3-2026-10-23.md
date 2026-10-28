VERDICT: HAS DEFECTS (F8 low)

# Fix check of VELDO-0214, round 3

Reviewer: Claude (fresh context, did not write this change). Date: 2026-10-23.
Range: 2b8e4730..f83f4ff1, worktree at f83f4ff1. Scope: the round 2 findings F6 and F7, and
whether F1, F3, F4, F5, AC5 and AC6 still hold. Focused check, not a full review.

## What I ran (exit statuses read directly)

- Suite 111 through scripts/selftest.py: exit 2 (the passing PARTIAL RUN status), suite line
  `111_veldo_0214_first_use_budget 10 passed`, `36 passed, 0 failed`. The brief's "9/0" is the
  round 2 count; round 3 added the tenth row, and HOST_RUNS.md says 10.
- `scripts/check_teeth_mutations.py --finding 214`: exit 1, candidate_execution_denied (this sandbox
  cannot nest the agent-sandbox launcher). I relied on host-runs.json (7 registered, 7 executed,
  every mutant failed exactly its named rows, baseline and no-op clean) and reproduced the cases
  that matter by hand. The brief's "5 of 5" is round 2; round 3 registers 7.
- By hand, in scratch copies made by `git archive HEAD`, suite 111 per mutant (exit 1 means a row
  failed):
  - temporary-directory test put back in owner_store_refusal (the F6 regression): 9 passed, fails
    installed-authority-under-temp-is-measured only.
  - keep test removed from prune_times (F7): 9 passed, fails leg-time-store-pruned only.
  - own-list test disabled: 9 passed, fails suites-stay-out-of-the-owner-store only.
  - budget214-main-drops-the-budget, both call sites: fails measured-budget-used and
    ceiling-caps-the-budget.
- run_budget over handed values: 100 gives 1800; 10800 gives 21600 uncapped; 10800.5 and 1e9 give
  21600 with CAPPED; 1e308 gives 1800, "not a finite number of seconds"; nan, inf, -5 give 1800,
  "no usable seconds"; a string gives 1800, "not the authority's form". No traceback.
- Suite 101: exit 1 here, but it fails early at candidate/planted-suite-publication-red (the
  sandbox cannot start the nested launcher) and never reaches the unconfined-leg section, so it
  says nothing about this change. I relied on the host comparison: main d49581b4 and 844b10cc fail
  the same two sandbox rows, 184 rows passing in each.
- NOT run here: ./scripts/verify.sh.
- The scratch HOME's ~/.cache/veldo did not exist before or after these runs.

## 1. F1: holds

scripts/check_first_use.py is unchanged in this range. The registered mutant and its single-site
variants still fail the row, as above.

## 2. F3 and F6: fixed

The temporary-directory test is gone from owner_store_refusal (scripts/gate_legs.py:241), in the
engine canon and the synced copy alike (identical). What is left is the own-list test, and a real
gate run cannot fail it: the command line has no list or store option, so run_stage gets
path = DECLARATION = HERE / 'gate_unconfined.json' with HERE resolved and times = LEG_TIMES, and the
authority compared against is HERE.parent resolved. The two sides are equal for every checkout,
whatever its path looks like. The lander's installation (.veldo/lander.py:732,
.veldo/control_verification.py:276) is written as regular files from Git objects, so no symlinked
gate_unconfined.json can make the resolved paths differ. The new row
installed-authority-under-temp-is-measured runs a unit and an integration stage of a gate_legs.py
copy laid down under the system temporary directory and requires the measurement to be recorded
and handed on as "this gate run". The registered mutant budget214-temporary-authority-refused
fails it.

Could a gate's own record be refused or pruned wrongly?
- A checkout under a path that looks temporary: no longer refused. The store key is
  sha256(authority path, digest), so a temporary checkout's file is only ever read by that same
  checkout.
- A symlinked home: LEG_TIMES is compared with itself, unresolved on both sides; the authority
  is resolved before it is recorded, so the gone-checkout test checks a real path.
- Two gates at once: different checkouts or lander lands get different keys, and each keeps its
  file while its checkout exists and is younger than 30 days. A .pending file is only pruned by
  age. Two gates in the same checkout share a file and the last writer wins, but each side tells
  its own run from the other by the run path. That is a stale measurement handed on, not a
  refusal, and the budget is bounded either way.
- The only way a legitimate file goes is a checkout path that is briefly missing (for example an
  unmounted volume) during another gate's prune. The cost is one re-measurement, and the spec says
  so.

Pruning is unchanged apart from the keep test, which is now proven (F7 below). No environment
override for the store path was added. The brief's sentence "the store accepts only ... a
checkout outside the system temp directory" describes round 2; round 3 deliberately removed that
clause, and suite 101 keeps out of the owner's store from its own side.

## 3. F4: holds

min(max(1800, 2.0 x s), 21600), CAPPED printed with the uncapped figure, and a non-finite budget
falls back to 1800 by name, all as listed above.

## 4. F5: holds

The docstring paragraph at scripts/gate_legs.py:70 is now accurate: only the own-list test,
location is no test, the lander's installation file goes with the gone-checkout prune or at 30
days, and suite 101 uses a scratch HOME. One imprecision, not a defect: the lander lays its
installation under the system temporary directory only when no observations directory is
configured (mkdtemp(dir=self.observations)). The rollback names seven mutation cases, and seven
are registered.

## 5. AC5 and AC6

AC5 is unchanged, sound, and its rows prove it. AC6 is now a sound requirement: dropping the
location test is right, and the keep clause is proven by budget214-keep-not-spared. One clause
is still claimed without a row (F8).

## Findings

### F7: fixed

leg-time-store-pruned now calls prune_times on a store whose only file is 31 days old, belongs to
a deleted checkout, and is the one named as keep. It requires that file to stay. Removing the keep
test fails the row, both by hand and in the registered mutant.

### F8 (low): suite 101's scratch HOME is claimed by AC6 but no row fails without it

- Where: specs/VELDO-0214-first-use-budget-measured-from-the-unit-leg.md:106 ("A suite that
  drives a temporary authority copy over its own list keeps out of the owner's store from the
  suite side, with a scratch HOME ... (suite 101)"); scripts/suites/101_veldo_0208_landing_reuse.py:1566,
  1571 and 1597.
- Scenario: delete `home=authority_home` from through_stage and `HOME=str(authority_home)` from the
  list-read-from-the-authority driver. No expect in suite 101 or 111 reads authority_home or the
  owner's store, so every row keeps its result. A host run of suite 101 then writes one file per run
  into the owner's ~/.cache/veldo/gate-leg-seconds, keyed by the temporary copy's path. Now that the
  location test is gone, the scratch HOME is the only thing that keeps suite 101 out of the store,
  and nothing guards it. The damage is small: the file is never read by a real checkout, and the next
  gate's prune removes it once the copy is deleted. But AC6 states this as part of the requirement,
  and its completeness list does not cover it, which is the same gap F7 was.
- Fix: in suite 101, after `kept = through_stage('unit', ...)`, require that
  authority_home / '.cache/veldo/gate-leg-seconds' holds exactly one file, and that this file
  records the copy as its authority. A driver without the scratch HOME then fails that row. Add the
  row to AC6's completeness list, or a hand falsifier for it. Or reword AC6 so this clause is
  described as suite 101's practice and not as a proven property.
