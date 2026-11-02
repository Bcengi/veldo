# VELDO-0088, batch 2026-10-29 round 4: suite 92 fixture dates

Cause. Suite 92 hard-coded the grooming proposal's expiry (and the question's deadline) as
2026-10-30T17:00:00Z. After that instant the backlog's freshness check refuses the PM's groom proposal
as stale_subject:expired (engine/.veldo/control_backlog.py, _request_problems). Nothing is staged, and
nine rows fail. No engine code changed between the passing and failing gates for this. It depends only
on the clock.

Evidence. All runs held the host gate lock and used the unconfined leg exactly as gate_legs.py runs it
(all.log; the runs started 2026-11-01T00:00:18Z):

- red-d88-unconfined.log: d88b5116 (before fix rounds E and F merged). The same nine rows fail, with
  stale_subject:expired.
- red-dcf-unconfined.log: dcf7955b (batch head). The same nine rows fail, with stale_subject:expired.
- green-fix-unconfined.log: this branch. Suite 92 has 56 checks, 0 failed (exit 2 means the run was
  PARTIAL, one suite only).

Red before and green after, per row: unit/one-run-staging, unit/factory-builder-ticket,
unit/independent-review, cycle/combined-inputs, review/pm-principal, review/current-publication,
review/build-refusal, review/review-refusal, followup/setup-pm.

Fix. Both dates are now one day past the run's own clock. control_grooming_request.py sets no upper
bound on expiry, and no clause changed.

Mutations, unconfined leg, check_gate_mutations.py:
- --finding 88: registered 19, executed 19, rejected 19 (mutations-88-receipt.json).
- --case lines188-pm-receiver-authority-missing, the case that mutates the suite 92 file: registered 1,
  rejected 1 (mutations-188pm-receipt.json).
The case input registry lists files only, without digests, so no pin moved.
