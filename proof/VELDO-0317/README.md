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
census or removal. The exit transaction binds the observations and refunds a
confirmed environment failure. A separate ordinal keeps latest-run selection
correct when charged attempt numbers repeat. Retry counts come from committed
exit order, including after restart. Unjudged ends settle usage without writing
an engine verdict. The second unconfirmed end retains its ordinary failure.

Two consecutive confirmed ends durably stop preparation for the whole unit.
The factory loop opens one signed owner inbox request titled as an andon; the
stop persists even if the request cannot be delivered. Acknowledging the request
does not automatically restart the unit. Existing unique-work rules keep edits
through run-finished Signal. Later payloads identify the retained worktrees.

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

## Completion (second builder, same branch)

The first builder stopped at 4d64112b with the implementation, the suite and the
nine registered cases committed and no run evidence. What was checked and
finished from there:

- Every registered anchor in the four changed modules was counted (423 cases).
  Three older ones no longer matched: findings 39 (dispatch-exit-lands-unit),
  41 (retire-no-sweep-on-prepare) and 141 (record-exit-uncommitted). The andon
  check in Runner.prepare now follows the configuration binding and the exit
  call keeps its closing argument, so 41 and 141 match unchanged. Finding 39
  anchors on the retire call as it now reads; its defect is the same. All three
  are rejected in regression-mutations.json.
- The first repair passed the observation to every exit; the VELDO-0308 suite's
  recorder refused the new argument (first-146-failure.txt, 3 rows). The
  argument is again bound only when an observation was taken; the suite is
  green (146_veldo_0308_run_finished.txt).
- mutations.json: findings 317, 316 and 334, 30 of 30 rejected, each with green
  baseline and no-op controls, none reused, no surviving workers. Per case rows
  are in mutation-summary.json; the exact applied defects of finding 317 are in
  mutations/. AC1 to AC4 map to space317-charge-attempt, space317-text-alone,
  space317-remove-worktree and space317-third-attempt.
- regressions.json: 18 selected suites. 16 have zero failed rows (exit 2 is the
  dispatcher's partial-run exit, never verification).

Two selected suites are red, and both are red on the base 870c43ea as well:

- 82_veldo_0129_worker_wiring: 25 failed rows here and on the base, the same
  rows (base-870c43ea-82_veldo_0129_worker_wiring.txt).
- 151_veldo_0313_space_run: 12 failed rows here, 11 on the base, 15 in an
  earlier run of this branch (first-151-run.txt). The failing set moves between
  runs; one cause printed in all three is its fixture's admit() refusing the
  expected_version argument VELDO-0334 added. The suite does not call the code
  this ticket adds. It is outside this footprint and is left for the lead; it
  is not claimed green and not shown to be unaffected beyond the base
  comparison.

Not run: scripts/verify.sh (the lead's), the full mutation inventory, and the
full unit suite. No independent review is claimed. Criteria stay pending.
