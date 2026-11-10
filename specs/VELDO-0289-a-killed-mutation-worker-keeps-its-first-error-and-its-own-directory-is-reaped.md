---
schema: veldo.spec/v1
id: VELDO-0289
title: A killed mutation worker is reported by its first error, with a failed cleanup or a failed meter sample recorded beside it
status: ready
risk: high
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: [VELDO-0208, VELDO-0219]
placement: [loop]
protected_paths: []
footprint:
  - "scripts/check_gate_mutations.py"
  - "engine/scripts/check_gate_mutations.py"
  - "scripts/check_teeth_mutations.py"
  - "scripts/suites/98_veldo_0204_mutation_receipts.py"
  - "scripts/suites/101_veldo_0208_landing_reuse.py"
  - "scripts/suites/115_veldo_0219_measured_admission.py"
  - "specs/VELDO-0289-a-killed-mutation-worker-keeps-its-first-error-and-its-own-directory-is-reaped.md"
  - "specs/index.md"
  - "proof/VELDO-0289/**"
behavior_bearing: true
observability:
  logs: >
    None new.
  metrics: >
    None.
  traces: >
    A worker outcome in the mutation stage receipt gains two fields. cleanup_error is present only
    when cleanup of that worker failed and holds the cleanup failure's text. measurement_error is
    present only when the worker already had an error and its meter's last sample then raised. It
    holds the sample failure's text.
  error_taxonomy: >
    No new error names. worker_cleanup_error and worker_measurement_error keep their meaning, and
    each is the outcome's error only when the worker had no earlier error. Otherwise the earlier
    error stays and the later failure is reported in cleanup_error or measurement_error.
acceptance_criteria:
  - id: AC1
    text: >
      Workers.finish keeps the first error a worker has. When the worker already has an error (a
      deadline, a cancel, a bad exit, a failed trace check) and cleanup then fails, the outcome's
      error and detail stay those of the first error, finish raises the first error, and the cleanup
      failure's text is recorded in the outcome's cleanup_error field. This holds for both cleanup
      steps: mutation_ownership.cleanup and the close of the worker's meter. When both cleanup steps
      fail, cleanup_error holds the ownership cleanup's text, and the meter close failure is appended
      after it. When the worker has no earlier error and cleanup fails, the outcome's error is
      worker_cleanup_error as today, and cleanup_error carries the same text. A worker whose cleanup
      failed keeps its resource grant and its admission grant whatever its first error was: the hold
      is decided by cleanup_error being present, not by the error's name. A worker whose cleanup
      succeeded has no cleanup_error field. When finish is handed an error and the meter's last
      sample raises, the outcome keeps the handed error, finish raises the handed error, and the sample
      failure's text is recorded in a measurement_error field. With no handed error, the outcome's error is worker_measurement_error
      as today.
    falsified_by: >
      Suite 98 row VELDO-0289 receipts/deadline-then-cleanup-failure: a worker passes its deadline
      and its cleanup then raises. The outcome's error is mutation_budget_exceeded, its detail names
      the worker deadline, cleanup_error holds the cleanup text, the error raised to the stage is
      mutation_budget_exceeded, and the worker's resources stay held. On 852f133b the same row
      reads error worker_cleanup_error with the deadline lost. A second case of the same suite 98
      row makes both steps raise and checks that cleanup_error contains both texts, the ownership
      cleanup's first. Mutation cleanup289-replaces-first-error (the cleanup error assigned over the
      first one) reds the row. Suite 98's existing mutation release-failed-cleanup is re-anchored on
      the new hold condition and still reds its cleanup fault. Suite 115 row VELDO-0289
      admission/deadline-then-sample-failure: a metered worker passes its deadline and its meter's
      sample raises only in finish's last sample. The fake Meter's sample succeeds on every call from
      the run loop and raises on its first call after check_worker has reported the deadline, so
      finish is handed mutation_budget_exceeded. The outcome's error is mutation_budget_exceeded with the worker-deadline detail
      and measurement_error holds the sample text, and the error raised to the stage is
      mutation_budget_exceeded. On 852f133b it reads worker_measurement_error.
      Mutation measure289-replaces-first-error (the sample error assigned over the handed one) reds
      the row. Both mutations are registered teeth in scripts/check_teeth_mutations.py, and each
      one's expected red is the rows this spec names for it.
  - id: AC2
    text: >
      A real worker that is killed at its deadline and whose cleanup then fails is reported as the
      timeout. This is the VELDO-0288 case: an unmetered worker makes a directory in /dev/shm, runs
      past its deadline and is killed, and cleanup refuses the directory because it is outside the
      worker's home. The outcome's error is mutation_budget_exceeded, its detail names the worker
      deadline, and cleanup_error says the ledger names resources outside this worker. The guard is
      unchanged, so the directory is still on disk after cleanup.
    falsified_by: >
      Suite 101 row VELDO-0289 ownership/timeout-then-cleanup-failure. The worker runs in the
      unconfined leg: workers.leg is set to a leg that names the fixture's suite, as
      gate_legs.mutation_leg does for the gate. The fixture makes a /dev/shm directory with
      tempfile.mkdtemp and sleeps past budget_seconds 2 in the job, and the coordinator kills it.
      The row first checks that the worker's ledger names the directory. It then checks the outcome
      as AC2 states and that the directory exists, and removes the directory itself. On 852f133b the
      row reads worker_cleanup_error with the deadline lost. Mutation
      cleanup289-replaces-first-error reds the row.
required_evidence: [unit, integration]
rollback: >
  Revert the commit. A cleanup failure or a failed meter sample replaces the worker's first error
  again, and new receipts no longer carry cleanup_error or measurement_error. Nothing else was
  stored, and mutation_ownership.py was never changed, so the revert touches no guard.
---

## Intent

The VELDO-0288 build ran scripts/check_teeth_mutations.py on its six teeth. One case in suite 62 passed
its 120 s deadline and the coordinator killed the worker. The result named no timeout. It said
worker_cleanup_error. The build check of f5c14ac9 traced this to scripts/check_gate_mutations.py, and
it isn't VELDO-0288's defect
(~/projects/myday/research/claude-runs/spec-veldo-0288-review-2026-11-10.md, Build check 1, part 3).
The line numbers below are at landing-c 852f133b.

Workers.finish is handed the worker's error, here mutation_budget_exceeded, and loses it in three
places. For a worker with a meter, the cgroup accounting object a worker gets when the stage runs under
the gate's admission, finish first takes a last sample. When the sample raises, lines 836 to 838
assign worker_measurement_error over the handed error. finish then kills the worker's process group
(line 840) and cleans up. When cleanup raises, lines 895 to 897 assign a new worker_cleanup_error to
the same variable and write it over the outcome's error and detail. The meter close at lines 903 to
905 does the same. The reader of the receipt sees a cleanup or measurement problem and has to find the
timeout some other way.

Cleanup raised in the 0288 run because of the ledger, a file the coordinator owns in which the worker
records every temporary directory it makes. After the worker ends, cleanup removes what the ledger
names. A directory outside the worker's home, such as suite 62's fixture store in /dev/shm, is admitted
only when the kernel shows it was born after a time called born_after (mutation_ownership.py:64-75).
born_after comes only from a meter (lines 892 to 894), and a plain check_teeth_mutations.py run has
none, because run_stage builds the admission only when it is called with admit=True (lines 1255 to
1256). So the guard refused the killed worker's own directory and cleanup raised. This spec doesn't
change that refusal. It makes the receipt say that the worker timed out and that cleanup then failed.

## Design

finish treats a cleanup failure or a sample failure as a second fact about the worker, not as a
replacement for the first. The outcome keeps error and detail from the first error and gains
cleanup_error when cleanup failed, or measurement_error when the last sample raised. Line 911 decides
today whether to release the worker's resources by comparing the error's name with
worker_cleanup_error. Once the first error is kept, that test would release a timed-out worker whose
cleanup failed, so the hold moves to cleanup_error being present.

## Out of scope

Any change to what the guard admits: created_since, admitted, remove_tree and cleanup in
mutation_ownership.py stay as they are. Reaping a killed worker's own fixture directory outside its
home goes to its own spec, because a born-after bound cannot prove which worker made a directory; the
likely design gives each worker a coordinator-made fast temp root inside its own scope. The 120 s floor
and the case deadlines. Suite 62 and the VELDO-0288 fix. The /dev/shm directories already left on the
host, which the lead removes by hand.

## What the reviewer judges

- The first error is the one in the outcome, in the receipt and in what finish raises, on every path
  through finish: the last sample, the ownership cleanup and the meter close.
- A worker whose cleanup failed never gives back its resource or admission grant.
- mutation_ownership.py and its engine copy are unchanged.

## History

2026-11-10: drafted from Build check 1 (f5c14ac9), part 3, of the VELDO-0288 review. Line numbers
confirmed against landing-c 852f133b.

2026-11-10: revision 1, after the spec review returned CHANGES with six findings. The lead chose to
keep the guard's strict rule, so the unmetered birth bound and the reaping rows left this spec and
reaping goes to its own spec. The measurement error at lines 836 to 838 joined AC1. AC1 now says what
cleanup_error holds when both cleanup steps fail. The former AC3 became AC2, one row for a killed
worker whose cleanup fails, run in the unconfined leg with budget_seconds 2. The mutations are
registered teeth in scripts/check_teeth_mutations.py. Every code citation was confirmed again against
landing-c 852f133b.

2026-11-10: revision 2. Applied the two findings of the re-review of af0738bb (finish's last sample
only; finish raises the handed error). Status set to ready by the lead.
