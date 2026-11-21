# VELDO-0224 build notes

Read before editing: CLAUDE.md, VELDO.md, the full ready specification, the build queue,
case_reuse.py (Session, declaration qualification), case_trace.py (check and trace errors),
mutation_reuse.py (Session/store), check_gate_mutations.py (Workers.finish/run and run_stage),
the matching engine copies, suite 100 and suite 157, and the teeth registration/materializer.
Callers inspected: reuse_worker.py:40-103, check_teeth_mutations.py:16717-16754 (before edits),
propose_case_inputs.py (selection in main), case_inputs.py (selected), and gate_reuse.py (Store).

AC1: per-case closure failures and typed undeclared probes invalidate declaration attempts.
Every replacement uses the full frozen input tree and its own baseline, no-op and mutant.
Malformed traces, invalid controls, surviving mutants and cleanup failures remain failures.
A replacement gets a fresh-run budget, never the stale snapshot's measured budget.

AC2: a stale mark clears the reuse key, drops the snapshot and denies later lookups for that
same declaration digest. No stale result is eligible for publication. Existing result records
remain immutable.

AC3: immutable findings are stored in the private authority store's stale/ directory, beside
its authenticated results, bound to case identity, declaration digest and session run ID.
The proposer reads matching findings. mutation_reuse.mark_stale is the shared write API for
VELDO-0218's future audit; implementing that audit is out of scope. The proposer file is added
to the footprint because AC3 explicitly requires this consumer.

Validation is pending. The builder does not run the canonical gate or independent review.
All loaded validation is submitted through the external host-heavy wrapper. Test child waits
are generous 300-second hang detectors; no assertion measures machine speed.

The repeatable validation batch is `python3 proof/VELDO-0224/validate.py.txt`, invoked through
an external host-heavy wrapper by the operator. It writes sanitized text logs and compact
mutation receipts in this proof directory, and exits nonzero if any selected check fails.
Full mutation receipts stay in scratch; the retained summaries include named false rows,
control failures, result sources and coordinator validation counts. This is selected validation,
not the canonical gate. Host admission is pending as of the second implementation commit.
