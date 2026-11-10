---
schema: veldo.spec/v1
id: VELDO-0289
title: A killed mutation worker is reported by its first error, and the directory it made outside its home is reaped even when it ran without a meter
status: draft
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
    A worker outcome in the mutation stage receipt gains one field, cleanup_error, present only when
    cleanup of that worker failed. It holds the cleanup failure's text.
  error_taxonomy: >
    No new error names. worker_cleanup_error keeps its meaning and is the outcome's error only when
    the worker had no earlier error. Otherwise the earlier error stays and the cleanup failure is
    reported in cleanup_error.
acceptance_criteria:
  - id: AC1
    text: >
      Workers.finish keeps the first error a worker has. When the worker already has an error (a
      deadline, a cancel, a bad exit, a failed trace check) and cleanup then fails, the outcome's
      error and detail stay those of the first error, finish raises the first error, and the cleanup
      failure's text is recorded in the outcome's cleanup_error field. This holds for both cleanup
      steps: mutation_ownership.cleanup and the close of the worker's meter. When the worker has no
      earlier error and cleanup fails, the outcome's error is worker_cleanup_error as today, and
      cleanup_error carries the same text. A worker whose cleanup failed keeps its resource grant and
      its admission grant whatever its first error was: the hold is decided by cleanup_error being
      present, not by the error's name. A worker whose cleanup succeeded has no cleanup_error field.
    falsified_by: >
      Suite 98 row VELDO-0289 receipts/deadline-then-cleanup-failure: a worker passes its deadline
      and its cleanup then raises. The outcome's error is mutation_budget_exceeded, its detail names
      the worker deadline, cleanup_error holds the cleanup text, the error raised to the stage is
      mutation_budget_exceeded, and the worker's resources stay held. On 852f133b the same row
      reads error worker_cleanup_error with the deadline lost. Mutation cleanup289-replaces-first-error
      (the cleanup error assigned over the first one) reds the row. Suite 98's existing mutation
      release-failed-cleanup is re-anchored on the new hold condition and still reds its cleanup
      fault.
  - id: AC2
    text: >
      A worker launched without a meter gets a birth bound of its own. The coordinator reads
      mutation_ownership.birth_clock() just before the Popen that starts the worker, keeps the
      reading for that worker, and passes it to mutation_ownership.cleanup as born_after. A worker
      with a meter keeps its meter's start as born_after, as today. scripts/mutation_ownership.py and
      its engine copy are not changed: created_since still admits a directory outside the home only
      when it is a plain directory of this user at its own resolved path whose kernel birth time is
      strictly after born_after. A directory that existed before the worker was launched is still
      refused and left untouched.
    falsified_by: >
      Suite 101 row VELDO-0289 ownership/unmetered-outside-directory-reaped: a real worker with no
      meter, in a leg that can write to /dev/shm, makes a directory there with tempfile.mkdtemp,
      leaves it and exits 0. The row first checks that the worker's ledger names the directory. The
      outcome has no error, its cleanup count includes the directory, and the directory is gone. On
      852f133b the same row ends worker_cleanup_error ("outside this worker") with the directory
      still on disk. The existing row VELDO-0208 ownership/forged-directory-red-and-untouched stays
      green: a ledger line naming a directory made before the launch is refused and the directory is
      intact. Mutation born289-no-unmetered-bound (the reading not passed to cleanup) reds the new
      row. Mutation born289-bound-zero (born_after 0 for an unmetered worker) reds the forged
      directory row. git diff 852f133b on scripts/mutation_ownership.py and
      engine/scripts/mutation_ownership.py is empty, recorded in the proof.
  - id: AC3
    text: >
      A case that times out and leaves a directory in /dev/shm is reported as the timeout and leaves
      nothing behind. For an unmetered worker killed at its deadline after it made a /dev/shm
      directory, the outcome's error is mutation_budget_exceeded, there is no cleanup_error, the
      cleanup count includes the directory, and the directory is removed. When the same worker's
      ledger also names a directory that predates it, the outcome's error is still
      mutation_budget_exceeded, cleanup_error says the ledger names resources outside this worker,
      the worker's own directory is removed and the older directory is intact.
    falsified_by: >
      Suite 101 rows VELDO-0289 ownership/timeout-leaves-outside-directory and VELDO-0289
      ownership/timeout-with-foreign-entry: the fixture makes a /dev/shm directory, in the second row
      also writes a ledger line naming a directory made before the launch, then sleeps past a
      deadline of a few seconds, and the coordinator kills it. Each row first checks that the ledger
      names the /dev/shm directory. On 852f133b the first row reads worker_cleanup_error with the
      directory still on disk. After the change both rows read as AC3 states. Mutations
      cleanup289-replaces-first-error and born289-no-unmetered-bound each red the first row.
required_evidence: [unit, integration]
rollback: >
  Revert the commit. A cleanup failure replaces the worker's first error again, and an unmetered
  worker's directory outside its home is refused by cleanup and left on disk. New receipts no longer
  carry cleanup_error. Nothing else was stored, and mutation_ownership.py was never changed, so the
  revert touches no guard.
---

## Intent

The VELDO-0288 build ran scripts/check_teeth_mutations.py on its six teeth. One case in suite 62 passed
its 120 s deadline and the coordinator killed the worker. The result named no timeout. It said
worker_cleanup_error, and /dev/shm/v39-n63f0y_j stayed on disk. The build check of f5c14ac9 traced both
to scripts/check_gate_mutations.py, and neither is VELDO-0288's defect
(~/projects/myday/research/claude-runs/spec-veldo-0288-review-2026-11-10.md, Build check 1, part 3).
The line numbers below are at landing-c 852f133b.

The first defect loses the cause. Workers.finish is handed the worker's error, here
mutation_budget_exceeded. It kills the worker's process group (line 840) and then cleans up. When
cleanup raises, lines 895 to 897 assign a new worker_cleanup_error to the same variable and write it
over the outcome's error and detail. The meter close at lines 903 to 905 does the same. The reader of
the receipt sees a cleanup problem and has to find the timeout some other way.

The second defect is why cleanup raised at all. Each worker has a ledger, a file the coordinator owns
in which the worker records every temporary directory it makes. After the worker ends, cleanup removes
what the ledger names. A directory inside the worker's home is always the worker's. A directory outside
it, such as suite 62's fixture store in /dev/shm, is admitted only when the kernel shows it was born
after a time called born_after (mutation_ownership.py:64-75). Today born_after comes only from a meter,
the cgroup accounting object a worker gets when the stage runs under the gate's admission (lines 892
to 894). run_stage builds that admission only when it is called with admit=True (lines 1255 to 1256).
A plain check_teeth_mutations.py run has admit=False, so its workers have no meter and born_after is
None. The guard then refuses every directory outside the home, including the one the worker made
itself. In a normal run this never shows, because the suite removes its own directory before it exits.
After a kill the suite can't, so the directory is refused and stays.

## Design

finish treats the cleanup result as a second fact about the worker, not as a replacement for the
first. The outcome keeps error and detail from the first error and gains cleanup_error when cleanup
failed. Line 911 decides today whether to release the worker's resources by comparing the error's name
with worker_cleanup_error. Once the first error is kept, that test would release a timed-out worker
whose cleanup failed, so the hold moves to cleanup_error being present.

The coordinator gives an unmetered worker the same kind of bound a meter gives. It reads
mutation_ownership.birth_clock() just before the Popen at line 1025 and passes that reading to cleanup
as born_after. birth_clock reads the clock the kernel stamps a new directory's birth time from, so
anything the worker makes is born at or after the reading and nothing made before the launch is.
created_since requires a birth strictly after the bound. A directory born in the same clock tick as
the reading is therefore still refused.

mutation_ownership.py isn't edited. The rule is the same one metered workers are held to today.

## Out of scope

Any change to what the guard admits: created_since, admitted, remove_tree and cleanup in
mutation_ownership.py stay as they are. The measurement error at lines 836 to 838, which also replaces
the error finish was handed, stays as it is. The 120 s floor and the case deadlines. Suite 62 and the
VELDO-0288 fix. The /dev/shm directories already left on the host, which the lead removes by hand.

## What the reviewer judges

- The first error is the one in the outcome, in the receipt and in what finish raises, on every path
  through finish that reaches cleanup.
- A worker whose cleanup failed never gives back its resource or admission grant.
- The reading is taken before the worker can exist and is tied to that worker only.
- An unmetered worker now has what a metered worker has: a ledger line naming a directory of this
  user born after the worker's launch is admitted and removed. The reviewer confirms this is no wider
  than the metered rule and that nothing born before the launch can pass.

## History

2026-11-10: drafted from Build check 1 (f5c14ac9), part 3, of the VELDO-0288 review. Line numbers
confirmed against landing-c 852f133b.
