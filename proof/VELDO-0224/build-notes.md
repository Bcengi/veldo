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

Selected validation passed on implementation commit 24ef7002a32b7f8748c43a62389b73022ab363d0.
The builder did not run the canonical gate or independent review.
All loaded validation is submitted through the external host-heavy wrapper. Test child waits
are generous 300-second hang detectors; no assertion measures machine speed.

The repeatable validation batch is `python3 proof/VELDO-0224/validate.py.txt`, invoked through
an external host-heavy wrapper by the operator. It writes sanitized text logs and compact
mutation receipts in this proof directory, and exits nonzero if any selected check fails.
Full mutation receipts stay in scratch; the retained summaries include named false rows,
control failures, result sources and coordinator validation counts. This is selected validation,
not the canonical gate. Host admission retained the wrapper's three-slot limit; the final
attempt used one-second slot polling after the earlier waiter repeatedly missed openings.

Final results:
- Suite 158: six ticket rows passed; 32 total including shared checks, zero failures.
- Nine affected suites: 462 total passed, zero failures. Both selected selftest commands
  returned the intentional partial-run exit 2. They are diagnostics, not a unit gate verdict.
- Finding 224: three registered, executed fresh and rejected; green baseline/no-op controls,
  each required row false for its specified regression. Retaining the snapshot verdict yields
  the helper-import worker error; retaining the stale key publishes stale cases; writing the
  candidate changes its identity. The receipt retains these concrete failure details.
- Finding 217: twelve registered, executed fresh and rejected; no invalid results.
- Lint and template sync passed. Personal setup reported zero findings using built-in shapes
  (no local installation found). Both touched specifications passed structural validation.

The initial failed batch is retained: suite 100 accidentally carried stale fixture marks into
an independent snapshot test, and suite 158 called leg_runs before its module imports installed
the scripts path in a confined mutation leg. The fixes isolate fixture marks and move that
check after module loading. The final affected suites and mutation drives above include both fixes.

Fixture boundary: the ticket suite uses the real coordinator, session, authenticated store,
materializer, worker completion, child interpreter, helper import and tree identity checks.
It supplies syscall trace text and controls Git/input discovery, runtime fingerprints, deadline
metadata and launches so it also runs inside the confined mutation leg. Suite 100 separately
exercises real traced workers. No loaded validation ran outside the external host-heavy wrapper.

## Fix round 1 (review FIX: F1, F2 and notes N1 to N5)

F1, an unavailable authority store failed the stage. Session.mark_stale now applies the in-session
effects first (key cleared, hit and snapshot dropped, reason declaration_stale, fresh rerun) and
only then tries to persist the mark. A store without signing authority (agent domain, store inside
the candidate, bad modes) leaves the entry `persisted: false` with `persist_error`; the receipt
counts these as `stale_unpersisted`. Workers.finish no longer has a stale_store_error path. An
unreachable store never becomes reuse: stale_entries now raises when the stale list or a mark
cannot be read (only a missing list is empty), and the session then runs every declared case
fresh with reason reuse_unavailable. Rows: store-unavailable-runs-fresh (deleted declared file,
helper imports and broken closure with the store inside the candidate: stage green, five fresh
validated reruns, five unpersisted, nothing written) and unreadable-marks-deny-reuse (a warm hit
as control, then the stale list replaced by a file: miss, reuse_unavailable). Falsifiers:
stale224-store-unavailable-fails (persistence failure raises again: the row is red with
"authority stale store unavailable") and stale224-unreadable-marks-reused (any OSError reads as
no marks: the row is red with the warm hit reused).

F2, prior marks were untested. Row prior-mark-denies-reuse publishes an authenticated record under
the exact current key of the reuse-qualified clean case, requires a warm hit as control, writes an
audit-style mark through mutation_reuse.mark_stale, then runs the real stage: the clean case runs
fresh with declaration_stale and key None, reused is 0, nothing is published for it, and the mark
is not written again. Falsifier stale224-prior-mark-ignored (`if False and prior is not None:`)
is red with the clean case reused.

N1: scripts/propose_case_inputs.py was added to the ready spec's protected_paths and footprint in
round 0 because AC3 requires the proposer to read the stale list. This still needs the owner's
acknowledgement at approval; this round did not change the spec.
N2: suite 100's traced undeclared-read rows no longer accept the old ValueError; only a
declaration_stale result with the snapshot released passes.
N3: runtime identity, store configuration and unreadable marks raise Unavailable inside the session:
the case runs fresh as reuse_unavailable for this gate only, and no permanent mark is written. Only
faults of the declaration itself (closure, absent inputs, runtime grants) mark it stale.
N4: a case stale from a prior mark reuses that entry (prior: true) and writes no new mark file.
N5: marks bind (identity, declaration digest), so a candidate's stale finding also turns off reuse
for the identical declaration on main until it is re-declared. Accepted as the spec's trace binding;
it only costs reuse, never correctness. Recorded, not changed.
Sibling note: Workers.run no longer launches a declared sibling of a case already found stale (it
would run untraced in the full tree); it returns a superseded declaration_stale result and the
stale case's own rerun replaces it. Row stale-sibling-not-launched drives the real Workers.run.

Validation for this round, committed before each run:
- pc2 (remote_run --share) at a57eda2a: suite224.txt 10 ticket rows, 36 passed, 0 failed;
  affected-suites.txt (98, 104, 112, 115, 157, 158) 150 passed, 0 failed.
- host_heavy at 6a89f848: sandbox-suites.txt (99, 100, 101; these need os.pidfd_open, absent on
  pc2) 337 passed, 0 failed; mutations217.json 12/12 executed fresh and rejected. Between 6a89f848
  and a57eda2a only suite 158 changed, which neither of these runs.
- host_heavy at a57eda2a: mutations224.json 6/6 executed fresh and rejected, green controls, each
  required row false for its stated reason, no invalid results.
- lint, template sync and personal setup (0 findings) at the final code.
Earlier round-1 attempts and why they were redone: suite 98 pins a unique worker-result line
that the sibling skip duplicated; a VELDO-0217 falsifier anchors the sensitivity-proof line; the
mutation leg needs suite 158 to load mutation_reuse by its production-copy anchor; the F1 mutant
first crashed the suite's later session instead of reddening its row. Each was fixed in its own
commit. The pc2 logs from the first attempt named the node's scratch directory; the batch now
replaces it and those two logs were sanitized the same way before commit.
