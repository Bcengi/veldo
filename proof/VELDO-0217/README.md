# VELDO-0217 proof

Implementation commit 94fd75e6. Every loaded run was made on a scratch clone of that commit, through
the host's heavy-run wrapper. The canonical gate has not run yet; the lead queues it.

## Acceptance criteria and their rows

| AC | Rows (suite 157_veldo_0217_declarations unless noted) | Falsifier (finding 217) |
|----|------|------|
| AC1 | declarations/stale-found, proposal-records-read-digests, legacy-declaration-stale, report-complete, refused-inside-a-gate, parallel-admission; declarations/stale-found-traced (0207 strace leg) | declarations217-support-dropped fails stale-found |
| AC2 | declarations/review-conditions (14 declarations: one passes, each other fails one condition with its named reason, including a review record whose digest does not match), reviewed-flag-protected | declarations217-one-trace-enough and declarations217-proof-skipped fail review-conditions |
| AC3 | declarations/key-covers-inputs (13 edit classes, each missing exactly its declaring cases; an undeclared file and an unloaded helper miss none) | declarations217-helper-not-keyed fails key-covers-inputs |
| AC4 | declarations/non-file-refused (five fixture classes through the classifier, then through the coordinator's run_stage, where four show only in the mutant trace (the bus also in the baseline) and nothing is published but the loopback-only case), absent-socket-keyed, outside-process; declarations/non-file-real-traces (0207 strace leg, real strace) | declarations217-bus-allowed fails non-file-refused |

red-green.json is the confined drive `check_gate_mutations.py --finding 217`: passed, 5 registered,
5 executed, 5 rejected, each mutant failing exactly its target row while its baseline and no-op
pass. red-green-driver-unconfined.txt is the same check through the driver's own materialize and
worker, outside confinement.

local-tests.txt: the 0217 suite and every suite whose code this change touches or that pins the
proposer (0204, 0205, 0207, 0208, 0210, 0215, 0216, 0219, 0259, 0304). All are green.

## Real-registry runs (outside any gate)

- staleness-check.json (`--check`): all 19 confined declarations of today's file are stale
  (no_recorded_inputs). The seven of AC1 were fixed by hand on 2026-10-25 (d9a4b342), so the
  mechanical check now finds them stale because they record no input digests, not because the
  helper is missing. The stale-found row reproduces the case where the helper is missing.
- sample-proposals.json (`--case`, 5 cases, 20 traced runs, admitted 10 at once): three proposals
  completed, all runs exiting 0. effects-worker-scope shows host_socket, so it can never qualify.
  Two cases (limit-unreported, account-codex-old-tables) failed with "incomplete file-read trace":
  each SIGKILLs its own child mid-newfstatat, which the tracer counts as lost evidence. This also
  happens without this change's network tracing (one of two runs with the original filter failed),
  and the spec leaves the tracer's rules out of scope. The proposer names each such case as failed.

## Not done here

- The full proposal run (`--all`, about 1,707 cases and four traced runs each, roughly 2 to 3 hours
  on the qualification host) is the owner's act outside a gate. So is committing its declarations.
- No review batch exists (reviews/README.md gives the format). Until VELDO-0226 writes a
  sensitivity proof for a key, no case qualifies (sensitivity_unproved), as the spec requires.
