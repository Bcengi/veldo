# VELDO-0317 build evidence

Stacked on 870c43ea (VELDO-0316 and VELDO-0334). The lead owns the full gate and
independent review. Neither is claimed here.

Read before editing: CLAUDE.md, VELDO.md, engine/AGENTS.md, policy, the entire
specification and wave-3 build queue; design sections 6.7 and 8.9. Starting-tree
entry points traced in engine/.veldo: control_launch.py:344,553,776,1443,1707,
1863,2355,2412,2518,2673,3343,3770,3803,3967;
control_space_admission.py:76,181; control_dispatch.py:300,334,480,585,641,802;
control_service.py:3143,3163,3198,3427,3606,3629,3679,3773;
control_launch_work.py:203; control_space_signal.py:608,694;
control_space_reconcile.py:852. The suite manifests, requirements, 0316/0334
fixtures, mutation drivers, lint and personal-setup checks were also read.

The footprint includes dispatch accounting and the factory loop because those
callers own charged attempts and automatic repeats. The receiver collects a
bounded no-space marker from both pipes and reads all applicable pools before
census or removal. The exit transaction binds the observations and gives a
confirmed environment failure back as a refunded count on the unit's index
slot; the attempt number itself is never issued twice (fix round 1). Retry
counts come from the state the exit transaction leaves on the unit's slots,
including after restart. Unjudged ends settle usage without writing an engine
verdict. The second unconfirmed end retains its ordinary failure.

Two consecutive confirmed ends stop the automatic repeat and refuse no
dispatch. The factory loop opens one signed owner inbox request titled as an
andon; the owner's recorded answer clears it (rerun dispatches the station once
more behind admission, acknowledge closes it and leaves the unit stopped).
Existing unique-work rules keep edits through run-finished Signal. Later
payloads identify the retained worktrees the ledger still holds live.

The installed receiver reads the adjacent trusted service configuration and
constructs space wiring against the same central store, host and declarations.
An unread pool cannot confirm a full disk. As in the existing service reader,
engine-image free space has no reader here and remains unconfirmed unless a
readable filesystem pool is below its floor.

The ticket suite runs real child processes, reads both pipes through Receiver,
and exercises the real dispatch store, Runner, Line, Git worktrees, census,
Signal and removal rules. Free bytes, eligibility, account policy and the process
table are fixtures. The worker waits for stdin EOF before exiting; subprocess
hang detectors are at least 120 seconds. No new test sleeps or asserts speed.
The owner request uses the real signed inbox. Mutation baseline and no-op runs
must remain green, and each mutated run must fail its named behavioral row.

Selected selftest runs are diagnostics, not aggregate gate evidence. The first
run exposed a fixture assertion that incorrectly required deferred state.
Report mode can record due; the ticket-worktree lifecycle measures on run
finished and can leave the worktree present. The edit survived; the assertion
accepts retained ledger states and still checks the exact edit. The host-heavy wrapper serializes
loaded runs. Proof text uses relative paths or redacted roots.

The subsequent controls exposed a fixture UUID patch that also replaced the
ledger's command IDs. The patch now replaces only the launcher's UUID binding,
so deterministic dispatch order cannot collide with ledger commands. The
run-finished regression also exposed unnecessary terminal inspection on ordinary
ends. Inspection now requires both enabled space management and an observed
no-space marker. Those first diagnostics were written to ignored files and are
not in this bundle.
The new history query also duplicated the old admission mutation's SQL anchor;
qualifying its ordering column keeps that existing falsifier unambiguous.

## Completion (second builder) and fix round 1

Stacked now on 9bbf44d4 (the fix rounds of VELDO-0316 and VELDO-0334). The
second builder repaired three older mutation anchors (findings 39, 41, 141)
and bound the exit observation only when one was taken. Fix round 1 answers
the independent review (one high, one medium-high, four low) in f2ef53ce:

| Finding | Fix | Row | Falsifier (red on that row) |
|---|---|---|---|
| F1 high | attempts never repeat; refund is a separate count | ac1/rerun-accepted | space317-reissue-refunded-attempt |
| F2 medium-high | andon refuses no dispatch; owner answer clears it | ac4/later-dispatch-open, ac4/owner-clears | space317-andon-refuses-dispatch, space317-andon-never-cleared |
| F3 low | brief names only live no-space worktrees | ac3/brief-no-space-only, ac3/brief-live-only | space317-brief-any-end, space317-brief-dead-item |
| F4 low | state on the unit's index slots, read by key range | history/unit-scoped, history/bounded-read | space317-slots-unbounded |
| F5 low | unconfirmed end after a standing repeat is a new run | history/unconfirmed-new-run | space317-unconfirmed-count-carries |
| F6 low | every suite re-run on the final code tree | regressions.json | - |

Evidence, all taken on the code of f2ef53ce through the host-heavy wrapper:

- mutations.json: findings 317 (15 cases), 316 (11) and 334 (15), 41 of 41
  rejected, each with green baseline and no-op controls, none reused, no
  surviving workers. regression-mutations.json: the three older cases, 3 of 3
  rejected. Per case rows are in mutation-summary.json; the exact applied
  defects of finding 317 are in mutations/. AC1 to AC4 map to
  space317-charge-attempt, space317-text-alone, space317-remove-worktree and
  space317-third-attempt.
- regressions.json: 19 selected suites, every one run on the final tree. 17
  have zero failed rows (exit 2 is the dispatcher's partial-run exit, never
  verification); suite 159 has 51 rows. 63_veldo_0049_floor joins the list
  because the floor reads attempt order.

Two selected suites are red, and both are red on the base 9bbf44d4 as well:

- 82_veldo_0129_worker_wiring: 25 failed rows here and on the base, the same
  rows (base-9bbf44d4-82_veldo_0129_worker_wiring.txt).
- 151_veldo_0313_space_run: 13 failed rows here and 13 on the base; 11 are the
  same rows, and two on each side differ, all four of the load-dependent kind
  (a run's end still asleep on processes that hold the run). The suite does
  not call the code this ticket adds. It is outside this footprint and is left
  for the lead; it is not claimed green.

Not run: scripts/verify.sh (the lead's), the full mutation inventory, and the
full unit suite. No independent review of the fix round is claimed. Criteria
stay pending.
