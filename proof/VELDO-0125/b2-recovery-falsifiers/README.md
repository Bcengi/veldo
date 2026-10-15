# Targeted negative controls for the recovery correction

Source and regression baseline: `5b7a64f6`. Each retained diff changes both the
canonical and installed source copy. Apply just one diff, run
`python3 scripts/selftest.py --suite 106_veldo_0125_routing`, and restore both
copies before the next mutation. No full selftest or general mutation runner was
used. Selected output in each `.txt` file is copied from that invocation's actual
log, with its actual exit status. The recurring-tick raw log is also retained.

- `recurring-tick`: installs a reachable recurring timer before `next_timer`
  returns. The idle iteration row calls that method, expires timers and checks
  that zero factory passes occur. The mutation makes that exact assertion fail.
- `unknown-cleanup`: refuses to release unknown outcomes despite signed cleanup.
- `result-retry`: aborts on the first dropped result request instead of retrying.
- `result-durability`: omits the durable signed request needed for replay.
- `deliverable-loss`: supplies a fake reference without collecting generated files
  before deleting clone and scratch.
- `operator-release`: accepts the attestation without releasing the reservation.
- `deadline-wake`: frees the slot but never wakes the work blocked on that account.

These runs are PARTIAL and are not canonical gate evidence. The two earlier
recurring-tick diffs inserted unreachable code; their recorded failure claims
have been withdrawn and replaced by this reachable mutation and actual output.
