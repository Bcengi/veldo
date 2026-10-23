# VELDO-0214 host verification

Round 2 commits: implementation af8847a8 (review findings F1, F3, F4, F5), specification and local
proof d051aa13. Round 1's record (implementation 11fcdbde, host runs at d03c4fba) is this file at
commit 3c742321. The independent review of round 1 is REVIEW-claude-2026-10-23.md, unchanged.

## Local evidence

`python3 proof/VELDO-0214/local_check.py` runs suite 111 through
`scripts/selftest.py --suite 111_veldo_0214_first_use_budget` (35 passed, 0 failed: the shared
preamble's rows and the suite's nine) and drives the five registered VELDO-0214 falsifiers through
`check_teeth_mutations.materialize` and `worker`. Each baseline failed no row; each mutant failed
exactly its target rows and nothing else. See local_checks.json.

`python3 proof/VELDO-0214/hand_falsifiers.py` drives nine unregistered falsifiers for the round-2
rows the same way: each nested call site of main() dropping the budget alone, the ceiling removed,
the cap not printed, the finiteness check skipped, the prune call removed, the gone-checkout test
removed, the owner-store guard removed and its temporary-directory test removed. Each failed its
target row. See hand_falsifiers.json.

`.veldo/validate.py all`, `scripts/check_lint.sh`, `scripts/check_docs.sh`,
`scripts/check_generated.sh` and `scripts/check_template_sync.sh` exited 0 on the round-2 code
(validate.py reported only AC5 and AC6 missing from this manifest before it was updated).

## Host runs, round 2 (2026-10-23, details in host-runs.json)

Run one after another on this host, logs under /tmp/v214b:

1. Suite 101 at main d49581b4, in a temporary detached worktree of /home/dmitry/projects/veldo
   (removed afterwards): exit 1, `210 passed, 2 failed`, suite line `184 passed`. Failed rows:
   `VELDO-0208 sandbox/unavailable-refuses-before-exec` and
   `VELDO-0208 sandbox/old-abi-refuses-before-exec`. No exception.
2. Suite 111 on this branch: exit 2 (passing partial run), `35 passed, 0 failed`, 9 rows.
3. Suite 53 on this branch: exit 2 (passing partial run), `40 passed, 0 failed`, 14 rows.
4. Suite 101 on this branch: exit 1, `210 passed, 2 failed`, suite line `184 passed`, the same two
   rows. No exception. The leg-time store ~/.cache/veldo/gate-leg-seconds was listed before and
   after and is unchanged; in round 1 each run of this suite added a file to it.
5. `python3 scripts/check_teeth_mutations.py --finding 214`: exit 0,
   `mutations: passed registered=5 executed=5 reused=0 rejected=5`.

Suite 101, main against branch: the same two rows fail and 184 pass in both; the two outputs
differ only in the suite count and the skipped list, which names suite 111 on the branch. Both
outputs are committed (suite101-main-d49581b4.log, suite101-branch.log). The two sandbox rows are
therefore pre-existing at main. Round 1's `ValueError: incomplete file-read trace` did not recur in
either run at this round's load (load average 3.4 to 11 against 15 to 24 in round 1), so it is shown
neither at main nor on the branch here; both runs reached the end of the suite, including
_v208_case_input_proposal and _v208_mutation_leg, which loads the changed gate_legs.py.

.veldo/last_verify and .veldo/events.jsonl were not changed by these runs.

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
run from a checkout under the system temporary directory records nothing there and its integration
legs use the 1800s floor, by design (AC6).
