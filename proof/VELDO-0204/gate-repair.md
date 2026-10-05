# Gate repair on build-veldo-0204

The starting tree is 149203fe. The gate failure supplied by the owner has two
independent causes: stale VELDO-0127 captures and unreliable containment baselines
under the mutation stage's shared systemd user manager. The temporary-directory
leak is a third defect in the test fixtures. This change does not claim a green
full gate or mutation stage; the owner's explicit execution restriction reserves
both mutation drivers and verify.sh for the reviewer.

## Admission contract

The actual stage configuration here is 16 simultaneous workers, 2,494 cases and
six baseline/noop controls for suite 63 (three production modules). There are 41
suite-63 mutants. The 3,190 workers in the supplied failure are total invocations,
not simultaneous workers. All 2,494 original mutation anchors still match once.

The suite manifest now declares resource capacities and per-suite resource demand.
Nineteen suites that create real scopes or use the real authority service declare
systemd_user_manager. Suites using a reported identity without a containment group,
or an in-process manager stand-in, do not consume this resource. This distinction
keeps their admission independent, even when they also use control_launch.py.

The default manager capacity is 16, preserving the stage's previous maximum shared
parallelism. Suite 63 declares exclusive demand because its existing notification
bounds need a manager undisturbed by sibling scopes and authority daemon reloads.
Its demand expands to the configured capacity, so at most one such case runs and
no other declared manager consumer overlaps it. Other manager consumers each use
one slot. Unrelated jobs bypass resource waiters and can fill the remaining process
or thread slots. A waiting exclusive job bars later users of its resource so it
cannot starve. No worker waits on an admission semaphore, and waiting time does not
consume its execution deadline. Baselines, noops and mutants use the same rule.

Both drivers accept `--resource-capacity systemd_user_manager=N`, with N a positive
integer. Unknown resources, invalid capacities, impossible demands and undeclared
suites fail closed. Receipts record effective capacities, peak occupied slots and
remaining slots. Failure, deadline and spawn-error paths release reservations after
owned children finish. The combined and per-worker deadlines, polling interval,
inventory, row checks and product bounds are unchanged. The policy applies within
one scheduler invocation; it does not coordinate unrelated host applications.

Exclusive demand is a conservative isolation policy, not a measured maximum safe
shared load. The serial real-suite measurement passed 83 checks. Its 68 concurrent
manager probes saw a maximum response time of 9.51 ms and NJobs of zero over 7.13
seconds. The observed high-concurrency mechanism and failure-rate curve remain
unqualified: the owner prohibited concurrent suites and mutation-driver execution,
and no exception to that restriction arrived. No product name collision was found
in the inspected code: dispatches use UUID4 identities, scopes hash those identities,
and suite slices use per-run random names. This inspection does not prove saturation.

## Cleanup and regressions

The missing ownership was in the suites, not Lander.land (which already discards
in finally). All five suite-13 allocations now use TemporaryDirectory, including
construction before the old try blocks. Suite 70's direct-stage fixture now always
discards; suites 4 and 69 also discard when a stage or observation raises.

Suite 97 drives the actual process scheduler with controlled completion at 16 worker
slots, the standalone driver's shared future-admission implementation, invalid
requirements, and failures before and after spawn. It executes the real temporary
fixture functions with construction, execution and between-stage faults. Its nine
checks pass. Bypassing process admission, reverting matrix cleanup and omitting
candidate cleanup each produce a false assertion in this suite; the exact rows are
recorded in gate-repair-regression-controls.json. The original fixture assertions
are AST-identical as multisets.

Suite 13's prerequisite closure passed 3,530 checks in 68.93 seconds and left zero
reported-prefix directories in its private TMPDIR. Suite 70 passed 57 checks in
6.44 seconds with zero candidate directories remaining. Suite 69 passed 42 checks
in 16.24 seconds. The requested engine-upgrade suite passed 59 checks in 42.97
seconds. Each selected suite exits 2 by repository contract.

## Live evidence and remaining qualification

Both VELDO-0127 engines have fresh captures, four completed real subscription runs
each, with no evidence-judge problems. The exact qualified Claude model is
claude-haiku-4-5-20251001, not the short model spelling from a commit subject.
Credential-literal and known-pattern scans have zero findings; the general entropy
scanner's pre-existing candidates are recorded separately, not called zero. Suite
86_veldo_0127_agent_configuration passed 53 checks in 37.35 seconds.

The reviewer still needs the requested concurrency curve, honest mutation-stage
baseline at the stage's real concurrency, finding 40 rejection count and wall time,
and the full gate. Neither a full mutation stage nor either driver was executed in
this work session. The existing foreground replay helper
proof/VELDO-0040/exit_notified_replay.py supports --workers and --runs for concurrent
suite-63 diagnostics; production assertion bounds must remain unchanged. The gate
has no case selector, so its full stage remains the authoritative mixed-load proof.
