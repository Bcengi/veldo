# Space V1 assembly, join 1 (owner order 43607)

Baseline: 95851131e2e33964a5e9a3194062b046e5668786. Incoming:
9c9e2978c7529a2a222779994195eee63a996450 (VELDO-0343, including 0318/0327).

The candidate implementation remains the base. Signed disposition requests, owner Keep,
Save/Discard, create-only detached kept branches in the main repository, and interrupted
Discard recovery are integrated. Removal retains candidate evidence, clone, descriptor,
held and landing safeguards. No-space work protection reads committed space_failure
records through Ledger.no_space_ends, before clone/review disposal exceptions.

Retired incoming implementation fragments (behavioral supersession, not patch equivalence):
- Old control_dispatch space_end/sequence/decremented attempts: candidate 7e2d165b0 uses
  space_failure, monotonically distinct attempts, refunds and slot history. Configuration
  provenance from 3eb33166e remains. The old dispatch/launch files are not installed.
- Old admission module and Requests service cache: candidate 05b2363b3 and 29cbb785f
  provide preparation, five-run history and orphan-hold recovery; 5b882e514/f5074f543 and
  059f726d6 retain receiver and version compatibility. Candidate suites 157/159 remain.
  Distinct old no-account/worker/report assertions remain under audit before final validation.
- Old unbounded _send_once/_freed waiter retries: candidate 19c6a15c8 and 636b6385e
  retain bounded compare-and-swap, caller-version refusal and documented contention residual.
  Candidate 64af93ab5 retains replay of the caller's own hold. Suite 158 remains.
- Old acknowledge-only andon: candidate 7e2d165b0 retains signed rerun/acknowledge;
  no automatic third run is enabled. Disposition publication uses the serial worker.
- Duplicate service freeing-journal scan: disposition notifications join the candidate's
  existing space_pass journal traversal and wake behavior.

Historical receipts are not proof of this assembly. Candidate manifest/checks/README bindings
for 0316/0317/0334 remain intact. Incoming conflicting versions are preserved under
historical-space-v1 with their original revision, while noncolliding historical receipts remain.
Old suites and their assertions are retained for reconciliation, not silently deleted.
Registries are based on the candidate until the single final reconciliation after join 3.

Validation: syntax parsed for changed production modules; mirrored files synchronized.
Space suites and teeth NOT RUN: Gate 18 completion line absent at this step. No gate run.
Protected paths changed: none. gate_unconfined entry remains proposal-only.
This is an assembly checkpoint, not a landing or green receipt.
