# VELDO-0261 diagnosis: three intermittent rows on the landing candidate

Candidate: commit ecacfd0a on the landing-a branch. Gate logs, home written as "~":

- ~/projects/myday/research/veldo-gate-landing-a2.log: green.
- ~/projects/myday/research/veldo-gate-landing-a3.log: mutation baseline of
  role127-delivery-comparison-skipped red on "VELDO-0127 delivery/completed".
- ~/projects/myday/research/veldo-gate-landing-a4.log: mutation baseline of
  dispatch-closed-output-killed-at-close red on "VELDO-0039 dispatch/owner-stop-other-runner" and
  "VELDO-0039 dispatch/observations".
- ~/projects/myday/research/veldo-gate-landing-a5.log: unit row "VELDO-0025 AC2 membership/one-transition".

In each red baseline the noop control of the same case, the same unmutated code, was green, so the
mutation under test is not involved. The gate lock was held for the whole diagnosis, so no suite was
run alone; everything below is from the logs and the code at ecacfd0a. Line numbers are at that commit.

## 1. Suite 87, VELDO-0127 delivery/completed: test assumption (timing under load, evidence discarded)

Observed: the red baseline's failed_details is empty. The suite's own timing line reads 70.0 s in the
green gate and 166.2, 155.8 and 164.8 s in the three red gates; the mutation ledger shows the scheduler at
19 to 20 of 20 CPU and 16 of 16 managers while this case ran (a3 lines 24382 to 24406).

Why the evidence is gone:

- proof/VELDO-0127/delivery_fixture.py:129-130 catches any exception of the whole run and records
  "raised Type: first 180 characters" through check(), which prints it (line 32).
- scripts/check_teeth_mutations.py:255 runs the suite under redirect_stdout, so the print is discarded, and
  lines 247-250 keep a detail only from text after a colon in the row name, which this row never has.
- scripts/suites/87_veldo_0127_codex_delivery.py:35-36 judges only the rows that were recorded, so every
  row after the raise is absent rather than red. The baseline failed only delivery/completed for that
  reason, not because the rest passed.

Where an exception can escape the per launch capture (delivery_fixture.py:23-27 catches only what is
passed to attempt):

- factory setup, delivery_fixture.py:44, which waits on ssh-keygen with a 20 s bound
  (proof/VELDO-0127/factory.py:52) and on the engine qualification (factory.py:155), whose bundled catalog
  and feature listing each wait 30 s (.veldo/control_engine_codex.py:550-553 and 568-571) and raise Refused;
- the configuration bind, delivery_fixture.py:64;
- the MCP credential resolve, delivery_fixture.py:76, which for every MCP bearing case runs the fixture's
  keystore double through .veldo/control_credential_keystore.py:27-28 with a 15 s bound, and raises
  Undeliverable on expiry.

Every other production call of a case (save, materialize, the receiver baseline with its observation and
listing waits) is inside attempt, so a timeout there would have red a case row with its code, which did
not happen. The escaped exception is therefore one of the three above; which one cannot be recovered
from the failed run, and the 2.4 times slower run makes a fixed child process bound the likely trigger.

Not a product race: the two worker threads each own a disjoint factory, store, fault file and module
copies, and the one module patch (delivery_fixture.py:49) is on the worker's own handoff module.

Fix (AC1): pre-register the rows, capture each case whole, keep the full exception in the row detail,
make setup its own row. No bound changes.

## 2. Suite 62, owner stop rows and observations: test assumption (fixed wait under load)

- scripts/suites/62_veldo_0039_dispatch.py:844 waits for the other runner's stopped worker with
  runner.wait(held_run, timeout=25), and line 803 does the same for dispatch/owner-stop, which also
  asserts an elapsed time below 40 s (line 824).
- When that bound runs out, .veldo/control_launch.py:1038-1051 ends the receiver and, finding the record
  still running, records the dispatch unknown. That is the specified answer to a caller's timeout, and the
  product's own default bound (line 1037-1039: the later of the contract deadline and the announced end,
  plus ACCEPT_SECONDS, 30 s at line 257) is far longer than 25 s.
- The row then reads state unknown instead of exited (line 850-853) and fails. The extra unknown dispatch
  enters Dispatches.status()'s stopped list (.veldo/control_dispatch.py:626), so dispatch/observations,
  which requires exactly three stopped dispatches (62_veldo_0039_dispatch.py:879), fails too. That is why
  the two rows fail together.

Not a product race: the stop is asked once by the holding runner and recorded by the receiver as every
end is; the only thing that changed under load is how long the end took.

Fix (AC2): wait on the record's terminal state with the product's own bound, judge the cause of the end
rather than its speed, and attribute any extra unknown dispatch in the observations row.

## 3. Suite 38, VELDO-0025 AC2 membership/one-transition: race in the test

Observed (a5 line 21760): race ['REPLIED {"seq": 5, "replayed": false}', 'REFUSED envelope_refused'];
the kill and retry legs passed. The row requires "store_refused" in the racers' output
(scripts/suites/38_veldo_0025_membership.py:353).

- .veldo/control_membership.py:420 reads the committed state outside any transaction; the envelope
  check against the CURRENT membership version runs on it (authenticate, lines 374-377, through
  .veldo/authority_contract.py:215-218).
- The commit at control_membership.py:455 begins its own transaction (.veldo/control_store.py:580) and
  refuses a moved version as stale_version (control_store.py:595-598), surfaced as store_refused
  (control_membership.py:456-457).
- So the loser is store_refused only if it read the state before the winner committed, and
  envelope_refused if it read it after. Both are the specified refusal of a stale version, the admission's
  docstring names both (control_membership.py:385-397), and in both exactly one change commits. Under load
  the two racer processes, started one after another (38_veldo_0025_membership.py:326-330), no longer
  overlapped, and the second read after the first had committed.
- The racer prints only the code (line 313), so the row could not show which check refused it.

Not a product race in the observed failure: the outcome the row protects held.

Fix (AC3): force each order deterministically, one row each, through a delegating store adapter at the
commit call and a bounded barrier the parent controls; print the full refusal.

## 4. Product defect found on the same path (AC4)

.veldo/control_store.py:579-582 turns any sqlite3.OperationalError from BEGIN IMMEDIATE into
read_only_handle. A writable handle whose busy timeout (30 s, control_store.py:409) runs out while another
writer holds the lock gets the same name as a handle that cannot write. The lock is held while the journal
record is signed inside the transaction (control_store.py:650), which in production is an OpenSSH
subprocess (the racers allow it 60 s, 38_veldo_0025_membership.py:308). The same pattern is at
control_store.py:689, 817, 875, 931, 967, 1004 and 1202. This did not cause the observed failure; the
overlapped order of AC3 is where it would surface.

## Runs

None. The gate lock (flock -n on the gates lock) was held at each check during the diagnosis, so no suite
was run alone.
