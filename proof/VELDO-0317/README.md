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
run exposed a fixture assertion that incorrectly required deferred state in
report mode, where the ledger correctly records due. The edit survived; the
assertion now accepts both retained states. The host-heavy wrapper serializes
loaded runs. Proof text uses relative paths or redacted roots. Full gate pending.

The subsequent controls exposed a fixture UUID patch that also replaced the
ledger's command IDs. The patch now replaces only the launcher's UUID binding,
so deterministic dispatch order cannot collide with ledger commands. The
run-finished regression also exposed unnecessary terminal inspection on ordinary
ends. Inspection now requires both enabled space management and an observed
no-space marker. The original failing diagnostics are retained in this bundle.
