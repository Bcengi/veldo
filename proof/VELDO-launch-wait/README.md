# Launch.wait: already exited at settle

Base: `5430e77a`, branch `veldo-launch-wait`.
Implementation and regression tests: `f8c3a898`.

`Launch.start` can settle an accepted launch from an already exited record. `wait`
now consumes that receiver's remaining messages before stopping it. The exit
record precedes `report_end`, whose order is run-end scan, space end, then the end
message. Reading through that message protects this work from the premature kill.
The existing timeout, EOF and unknown-outcome handling remain in effect.
The shipped engine copy carries the identical fix.

Two suite-78 rows exercise real re-hash refusals:

- `launch/exited-before-settle`: the test replaces the existing `_settle` method
  temporarily, waiting for the receiver process to exit first. It checks the
  exited settle, the artifact against its file and digest, failed accounting,
  exactly one artifact before exactly one exited message, and clean reap.
- `launch/record-before-report`: a fixture-only receiver entry pauses after the
  exit record, before `report_end`. The test releases it when `wait` reads the
  pipe. It checks the real scan logged this dispatch and the space-end observer completed
  before the end message was taken. The space observer records ordering; suite
  146 checks the actual ledger, census, removal and hold release. No production
  environment probe or delay is added.

Finding 60 registers `claude-launch-wait-skips-exited`, restoring the exact old
condition and requiring both new rows to reject it.

Validation on `f8c3a898`:

- Six related suites (53, 62, 78, 129, 146, 150): 158 checks passed, 0 failed.
  Exit 2 denotes a successful *partial* selftest, not a gate result.
- Finding 60: all 36 mutants freshly executed and rejected, with no reuse.
  The old-condition mutant fails exactly the two new regression rows; baseline
  and no-op controls pass all 63 observations. `teeth-summary.json` contains
  those results; `teeth.txt.gz` preserves the complete receipt and its hash.
- Loaded suite 78: 1,000 runs, 40 concurrent workers, 1,321 seconds. **0 red
  rehash rows out of 3,000**, all 2,000 regression rows green, no failed runs,
  failed rows or worker errors. Samples show 40 active workers on 20 CPUs,
  with one-minute host load averages of 44.8 to 48.7.
- Lint including the proof scripts: 1,246 Python and 40 shell files passed.

The first six-suite run had 156 passes and two canon-equality failures: both
required the same change in `engine/.veldo/control_launch.py`. That copy is now
identical; the initial failures are retained in `selftests-canon-before.txt`.
`suite-78-initial.txt` records the preliminary standalone suite run.

`run_checks.sh` runs the six related selftest suites, finding-60 teeth, and
`run_loaded.py`. Teeth use `check_gate_mutations.py`, which honors suite 78's
declared systemd host access. The batch is invoked through `myday/scripts/host_heavy.sh` under
the shared host lock and its 10 GiB scope. The load run executes the whole suite
through the mutation driver's unmutated worker 1,000 times, with 40 workers.
Every run must enumerate each of the three rehash rows and both regression rows
exactly once. `loaded.jsonl` retains compact results; `loaded-summary.json` binds
the measured production, suite and mutation-registry bytes by SHA-256.

No full verification script was run; these are targeted checks, not a gate pass.
Independent review remains pending.
