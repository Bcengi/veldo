# VELDO-0204 mutation stall repair

## Cause and recorded evidence

The coordinator lost completed work when any child failed. At reproduction commit
`260a6b32`, `scripts/check_gate_mutations.py:496` put each decoded result into a
local dictionary; line 502 returned it only after the whole batch. The caller at
lines 585-587 waited for those returns before validating results, and line 620
added worker time only while processing the completed mutant batch. One timeout
therefore discarded successful exits and could leave zero recorded worker time.
The standalone teeth driver's old `run_futures` path also waited for the entire
batch before reporting any case. Both entry points now share the fixed coordinator.

The historical concurrent capture is [before.json](before.json):

- Lines 2-5 name an authority baseline worker deadline, `wall_seconds` of
  `120.03801850881428`, 24 invocations and **zero returned results**.
- Fourteen worker records have `returncode: 0` and nonempty stdout. The other ten
  were killed (`-9`). Those 14 successful child exits were discarded by one timeout;
  they include controls, so they are not a claim of 14 rejected mutations.
- Lines 224-232 record manager capacity and peak use of 16. The retained
  [before-workers](before-workers/) files contain the actual child output.

The serial capture, [serial.json](serial.json), lines 2-13, records no error,
`wall_seconds: 17.75058045377955`, one invocation, one returned result and exit 0
for the authority baseline. [serial.stdout](serial.stdout) retains its 5,987 bytes
of structured output; [serial.stderr](serial.stderr) is empty. The 17.75 s serial
baseline versus concurrent >120 s supports shared-manager interference, rather
than an inherently over-budget serial baseline. This is historical reproduction
evidence, not a successful post-fix concurrent qualification.

## Changes

- Both entry points use `Workers` and `run_stage` in the gate coordinator. A child
  exit records its elapsed time and outcome immediately; each completed mutant is
  validated and appended to the receipt without waiting for its siblings. Final
  `worker_seconds` sums those recorded outcomes, including controls and failures.
- Timeouts preserve completed results, name the failed worker and its reason, and
  count a launched failed mutant as executed but not rejected. Cleanup checks
  siblings for successful exits before labelling still-running children cancelled.
  Outcomes include PID, return code, output directory, byte counts and error tails.
- The per-child deadline starts after `Popen` returns, not while waiting for
  admission or process creation. The overall stage budget remains bounded.
- Suites 63 and 66 reserve the user manager exclusively. Other manager consumers
  share declared slots, and unrelated work may proceed. The authority and project
  fixtures retain ownership through teardown.
- Workers persist an ownership ledger before using temporary trees or manager
  units. The parent reaps the process group, then those owned resources, before
  releasing admission. Failed cleanup retains the reservation and fails the run.
- The teeth CLI now emits the same receipt as the gate CLI. It retains `--finding`,
  `--jobs`, `--resource-capacity` and `--diff-dir`, and adds repeatable `--case` and
  `--worker-log-dir`. The gate accepts repeatable `--finding` and `--case`,
  `--resource-capacity` and `--worker-log-dir`; it has no `--jobs` flag.

Suite 98 exercises both entry points with controlled processes, including timeout,
empty output, malformed output, child exit failure, launch failure and cleanup
failure. Planted defects must be caught when they discard partial results or
completed siblings, omit a failed result, zero worker time, omit failed executions,
start deadlines before launch, release resources too early, or skip sibling reaping.
Ownership tests include a real SIGKILL and a read-only tree outside TMPDIR.
[checks.json](checks.json) records the two permitted partial suite runs. These
are focused regression results; neither the full gate nor mutation qualification
was run in this continuation.

## Exact next commands for the reviewer

Run from this worktree's repository root, in the foreground, one at a time. These
commands are for the reviewer to execute outside the restricted repair run. They
write receipts, stderr, child outputs and unit listings outside the input checkout.
The printed path identifies each run's evidence directory. Each `workers` directory
must be new; `mktemp` makes these commands repeatable.

Small subset: all **38** finding-47 authority cases (about 40):

```bash
mutation_run=$(mktemp -d /tmp/veldo-0204-small.XXXXXX)
python3 scripts/check_teeth_mutations.py --finding 47 --jobs 16 --resource-capacity systemd_user_manager=16 --worker-log-dir "$mutation_run/workers" > "$mutation_run/stdout" 2> "$mutation_run/stderr"
mutation_status=$?
systemctl --user list-units --all --no-legend --plain 'veldo-*' > "$mutation_run/units-after.txt" 2>&1
printf 'driver_exit=%s evidence=%s\n' "$mutation_status" "$mutation_run"
```

Larger subset: **300** exact case names in [large-cases.txt](large-cases.txt).
This includes all 41 containment, 38 authority and 26 project cases represented
there, plus 195 cases from other suites. Names were selected from direct registry
calls by static inspection; no mutation driver was executed to prepare this list.

```bash
mutation_run=$(mktemp -d /tmp/veldo-0204-large.XXXXXX)
mapfile -t mutation_cases < proof/VELDO-0204/mutation-stall/large-cases.txt
python3 scripts/check_teeth_mutations.py --jobs 16 --resource-capacity systemd_user_manager=16 --worker-log-dir "$mutation_run/workers" "${mutation_cases[@]/#/--case=}" > "$mutation_run/stdout" 2> "$mutation_run/stderr"
mutation_status=$?
systemctl --user list-units --all --no-legend --plain 'veldo-*' > "$mutation_run/units-after.txt" 2>&1
printf 'driver_exit=%s evidence=%s\n' "$mutation_status" "$mutation_run"
```

For each successful qualification expect driver exit 0 and the first stdout line
to decode as a JSON receipt with `status: "passed"`, `scope: "selected"`,
`registered == executed == rejected == len(results)` equal to **38** or **300**,
`invalid_results: []`, and
`drivers["check_teeth_mutations.py"]["worker_seconds"] > 0`.
`surviving_workers` and every `resources.remaining_slots` value must be zero.
Every launched child, including controls, must have a `worker_outcomes` entry;
`worker_invocations == len(worker_outcomes)`. No outcome may carry an error.
`peak_workers` must not exceed 16 and manager peak slots must not exceed 16.
The unselected review driver's registered count and worker time remain zero.

Expect no lingering `veldo-*` user units after either run: `units-after.txt` must
contain no unit rows. Also inspect the exact service/slice names in each worker's
`ownership.jsonl` and recorded cleanup, including slices whose names start with
`v` rather than `veldo-`. Pre-existing unrelated units must be identified separately,
never removed by a global prefix sweep. Any timeout, incomplete receipt, failed
cleanup or unexpected surviving unit is a failed qualification, not a rejection.
