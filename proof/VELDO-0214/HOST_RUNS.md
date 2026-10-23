# VELDO-0214 host verification

Round 3 commits: the fix check of round 2 (REVIEW-claude-r2-2026-10-23.md, unchanged) 33f88ca0,
implementation 844b10cc (findings F6 and F7). Round 2's record (implementation af8847a8,
specification d051aa13, host runs 2b8e4730) is this file at commit 2b8e4730; round 1's is this file
at commit 3c742321. The independent review of round 1 is REVIEW-claude-2026-10-23.md, unchanged.

## What round 3 changes

F6: the owner's leg-time store no longer refuses an authority under the system temporary
directory. The lander lays its installation down there (tempfile.mkdtemp(prefix="veldo-observation-")
/ "installed") and runs that copy's verify.sh, so with that test every land was back on the fixed
1800s. The own-list test stays, and still refuses suite 101's fixture-list driver. Suite 101's two
drivers of its temporary authority copy (through_stage and the list-read-from-the-authority run)
get a scratch HOME in their subprocess environment only, so their measurements land in a scratch
store. No environment override for the store path was added. New row
first-use-budget/installed-authority-under-temp-is-measured runs a unit and an integration stage of
a copy of the gate_legs.py under test and its own list laid down under the system temporary
directory, and requires both unit legs recorded and handed to the integration legs as "this gate
run". Mutation budget214-temporary-authority-refused restores the refusal and fails it.

F7: the row first-use-budget/leg-time-store-pruned also calls prune_times on a scratch store whose
only file, 31 days old and of a deleted checkout, is the one named to keep, and requires it to stay.
Mutation budget214-keep-not-spared removes the keep test and fails it.

## Local evidence

`python3 proof/VELDO-0214/local_check.py` runs suite 111 (36 passed, 0 failed: the shared
preamble's rows and the suite's ten) and drives the seven registered VELDO-0214 falsifiers through
`check_teeth_mutations.materialize` and `worker`. Each baseline failed no row; each mutant failed
exactly its target rows and nothing else. See local_checks.json.

`python3 proof/VELDO-0214/hand_falsifiers.py` drives nine unregistered falsifiers: each nested call
site of main() dropping the budget alone, the ceiling removed, the cap not printed, the finiteness
check skipped, the prune call removed, the gone-checkout test removed, the owner-store guard
removed and its own-list test removed (this replaces round 2's temporary-directory case, whose
test is gone). Each failed its target row. See hand_falsifiers.json.

`.veldo/validate.py all`, `scripts/check_lint.sh`, `scripts/check_docs.sh`,
`scripts/check_generated.sh` and `scripts/check_template_sync.sh` exited 0 on the round-3 code.

## Host runs, round 3 (2026-10-23, details in host-runs.json)

Run one after another on this host at 844b10cc, logs under /tmp/v214c, load average 1.6 to 5.1:

1. Suite 111: exit 2 (passing partial run), `36 passed, 0 failed`, 10 rows.
2. Suite 53: exit 2 (passing partial run), `40 passed, 0 failed`, 14 rows.
3. Suite 101: exit 1, `210 passed, 2 failed`, suite line `184 passed`. Failed rows:
   `VELDO-0208 sandbox/unavailable-refuses-before-exec` and
   `VELDO-0208 sandbox/old-abi-refuses-before-exec`. No exception. These are the same two rows that
   fail at main d49581b4 (round 2's run, suite101-main-d49581b4.log, also 184 passed), so no new
   failure. This round's output is suite101-branch.log.
4. `python3 scripts/check_teeth_mutations.py --finding 214`: exit 0,
   `mutations: passed registered=7 executed=7 reused=0 rejected=7`.

The leg-time store ~/.cache/veldo/gate-leg-seconds was listed before and after the runs: empty
both times. .veldo/last_verify and .veldo/events.jsonl were not changed by these runs.

## Pending: the repository gate

`./scripts/verify.sh` is NOT run yet; it runs separately on a quiet machine. It is the integration
evidence for AC1 and AC3. Its unit stage lines must carry each leg's time,
`unit: confined leg: pass (<s>s)`; its integration stage must print
`integration: confined leg budget input: unit confined leg <s>s, this gate run (...)` and, inside
the check, `budget per nested run: <2 x s>s, min(max(1800, 2.0 x <s>s), 21600): the unit stage's
confined leg as the authority's gate_legs.py measured it in this gate run (...)`; the unconfined
leg's budget is 1800s while its unit leg stays under 900s. GATE: GREEN is the only done.

The first gate on a host has no earlier measurement; that is expected, since its own unit stage
records one before integration runs. The leg-time store is ~/.cache/veldo/gate-leg-seconds/. A gate
run from the lander's installation under the system temporary directory records there and hands
its unit legs on like any other (AC6); its file is pruned once that installation is deleted, or at
30 days.
