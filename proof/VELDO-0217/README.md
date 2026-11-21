# VELDO-0217 proof

Implementation commit 94fd75e6; fix round 1 (review FIX, F1-F6) commit a75a0516; fix round 2
(fix-check FIX, F4 half fixed) commit a7d82428. Fix round 1's loaded runs were made on a scratch clone
of a75a0516 through the host's heavy-run wrapper; fix round 2's are listed in its section. The canonical gate has not run yet; the lead queues it.

## Acceptance criteria and their rows

| AC | Rows (suite 157_veldo_0217_declarations unless noted) | Falsifier (finding 217) |
|----|------|------|
| AC1 | declarations/stale-found, proposal-records-read-digests, legacy-declaration-stale, report-complete, refused-inside-a-gate, parallel-admission; declarations/stale-found-traced (0207 strace leg) | declarations217-support-dropped fails stale-found |
| AC2 | declarations/review-conditions (14 declarations: one passes, each other fails one condition with its named reason, including a review record whose digest does not match), reviewed-flag-protected | declarations217-one-trace-enough and declarations217-proof-skipped fail review-conditions |
| AC3 | declarations/key-covers-inputs (13 edit classes, each missing exactly its declaring cases; an undeclared file and an unloaded helper miss none) | declarations217-helper-not-keyed fails key-covers-inputs |
| AC4 | declarations/worker-trace-refused, undeclared-absent-socket, incomplete-trace-demoted (the coordinator's own Workers.finish on planted publishing traces), accept-pending; declarations/accept-pending-real (0207 strace leg); declarations/non-file-refused (five fixture classes through the classifier, then through the coordinator's run_stage, where four show only in the mutant trace (the bus also in the baseline) and nothing is published but the loopback-only case), absent-socket-keyed, outside-process; declarations/non-file-real-traces (0207 strace leg, real strace) | declarations217-bus-allowed fails non-file-refused; see fix round 1 |

red-green.json is the confined drive `check_gate_mutations.py --finding 217` at a7d82428: passed, 14
registered, 14 executed, 14 rejected, each mutant failing exactly its target row while its baseline and no-op
pass. red-green-driver-unconfined.txt is the same check through the driver's own materialize and
worker, outside confinement, at a75a0516 (12 falsifiers).

local-tests.txt: the 0217 suite and every suite whose code this change touches or that pins the
proposer (0204, 0205, 0207, 0208, 0210, 0215, 0216, 0219, 0259, 0304), rerun at a75a0516. All are
green (157: 19 rows; 0207: 92 rows with accept-pending-real).

## Fix round 1: the review's findings

| Finding | Fix | Row (157 unless noted) | Falsifier (finding 217) |
|----|----|----|----|
| F1 (M) gate's own non-file check untested | a row drives the real Workers.finish (only the launch replaced by an ended process and a planted trace) through run_stage | worker-trace-refused | declarations217-worker-trace-ignored (finish returns no non-file class) |
| F2 (M) a thread left in accept made the trace incomplete | an ended thread's pending network call is complete for the file check and yielded with result '?': a pending connect is an attempt; an accept on a socket the tree never listened on is classed (unbound_loopback, network_peer or host_socket) | accept-pending; accept-pending-real (0207 strace leg: real daemon threads blocked in accept4 on own TCP and abstract sockets, synchronized on /proc syscall state; at the base tracer this trace raises) | declarations217-accept-incomplete, declarations217-foreign-accept-allowed |
| F3 (M) undeclared absent socket in a publishing run | Workers withholds publication, reason undeclared_absent_socket, when a run probes an absent socket the toolchain's absent list (the key) does not hold | undeclared-absent-socket | declarations217-absent-unkeyed |
| F4 (L) review records unprotected | policy protected path `proof/VELDO-0217/reviews/*` (floor high) in .veldo/policy.yaml, the declarations file's own pattern | review-records-protected | declarations217-reviews-unprotected |
| F5 (L) "last" gate observation | the proposer takes observations only from a passed receipt whose input_digest is the gate's input digest of the tree it traces, and records the receipt binding and its inputs; case_reuse names observation_not_current otherwise | gate-observation-current | declarations217-receipt-unchecked |
| F6 (L) incomplete trace failed the stage | IncompleteTrace keeps the case from publishing (incomplete_trace); the stage passes; other trace errors still fail it | incomplete-trace-demoted | declarations217-incomplete-fails-stage |

## Fix round 2: F4 completed

case_reuse.review_matches read the record at whatever path the declaration named, so the policy
pattern protecting proof/VELDO-0217/reviews/* could be bypassed by a record added later elsewhere.
Both guards now hold: the record path must start with proof/VELDO-0217/reviews/, and a reviewed
declaration binds the sha256 of the record's exact bytes (review_sha256), set by the owner in the
protected change that sets reviewed true. The digest is the stronger design, because it fixes what was
approved at approval time regardless of the record's location, later edits or the policy pattern, and
no declaration can be approved before its record exists; the prefix stays as defense in depth.
review_sha256 is approval, not an input, so the declaration digest and the case key leave it out.

| Row (157) | Falsifier (finding 217) |
|----|----|
| review-record-bound: a matching record at notes/anywhere.json, and a declaration whose bound digest is not its record's; both review_mismatch, neither keyed | declarations217-review-anywhere (prefix check dropped), declarations217-review-unbound (digest check dropped) |

Runs at a7d82428: the confined drive above (scratch clone, host heavy-run wrapper; the compute node's
Python has no os.pidfd_open, so the agent sandbox cannot start there); suite 157 on the compute node
(20 rows green); suite 100 green through the host wrapper (92 rows), while on the compute node its 29
real-sandbox rows fail identically at a7d82428 and at the parent 7460e9a9, for the same missing
os.pidfd_open (local-tests.txt). The other suites of fix round 1 build no review_sha256, so their case
keys and review checks are unchanged.

## Real-registry runs (outside any gate)

- staleness-check.json (`--check`): all 19 confined declarations of today's file are stale
  (no_recorded_inputs). The seven of AC1 were fixed by hand on 2026-10-25 (d9a4b342), so the
  mechanical check now finds them stale because they record no input digests, not because the
  helper is missing. The stale-found row reproduces the case where the helper is missing.
- sample-proposals.json (`--case`, 5 cases, 20 traced runs, admitted 10 at once): three proposals
  completed, all runs exiting 0. effects-worker-scope shows host_socket, so it can never qualify.
  Two cases (limit-unreported, account-codex-old-tables) failed with "incomplete file-read trace":
  each SIGKILLs its own child mid-newfstatat, which the tracer counts as lost evidence. This also
  happens without this change's network tracing (one of two runs with the original filter failed).
  The sample was made at 94fd75e6, before fix round 1; a second cause found by review (F2: a thread
  left waiting in accept or recv) is fixed since and was not rerun on the registry. The proposer
  names each such case as failed; at the gate such a trace now demotes its case (F6).

## Not done here

- The full proposal run (`--all`, about 1,707 cases and four traced runs each, roughly 2 to 3 hours
  on the qualification host) is the owner's act outside a gate. So is committing its declarations.
- No review batch exists (reviews/README.md gives the format). Until VELDO-0226 writes a
  sensitivity proof for a key, no case qualifies (sensitivity_unproved), as the spec requires.
