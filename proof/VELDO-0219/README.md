# VELDO-0219 implementation and ticket proof

Status: REMAINING. The coordinator implementation and targeted checks are built.
Production graph integration requires the protected dependency changes in OPEN.md.
AC4 still requires the later batch gate and its fixed-sixteen canonical control.
Nothing in this bundle claims a green canonical gate or permission to land.

The branch starts at VELDO-0216 commit 92f5d029, including VELDO-0220. Owner go is
Telegram 37209 and 37212. No other worktree or branch was edited. No code or data
was obtained from a Bcengi project.

## Acceptance checks

| Criterion | Built and checked | Falsifier |
| --- | --- | --- |
| AC1 | Worker bootstrap joins its own cgroup before candidate imports. Coordinator samples CPU and anonymous memory, including disjoint owned unit cgroups before cleanup. Passing fresh stage records all three worker measurements alongside the existing case key and time peaks. Reads and writes enforce the same 30 day window and pruning. `admission/measured-per-case`, `admission/cgroup-counters`, `admission/bootstrap-joins-before-import`, `admission/stage-receipts-and-recording`, plus `kernel_check.py`. | `admission219-slowest-rate` changes the fastest denominator to the slowest. Target red, followed by green baseline and no-op. |
| AC2 | Ordered claim fallback, largest member control claims, local manifest reservations followed by the gate ledger grant, and a safety ceiling of twice usable CPUs. Matrix checks use 4, 20 and 40 cores against 4, 16 and 31 GiB. Inventory check preserves real case identities and manifest resources, seeds previous keys in scratch storage, and compares empty storage. Oversized claims and cgroup launch errors refuse by name. | `admission219-fixed-sixteen` restores the clamp. `admission/fits-ledger` is red at 40 cores. Baseline and no-op are green. Production handoff remains blocked as OPEN.md explains. |
| AC3 | Four fixture receipts at 2, 8, 16 and measured admission preserve verdict fields and enforced deadlines. The cap uses the reserved floor, largest claims, CPU and memory charges, existing manifest charges, and the original count bound. Failed stages write no resource records. | `admission219-optimistic-m` substitutes the available worker ceiling for the conservative floor count. `admission/same-verdicts` and the actual stage receipt check turn red. Baseline and no-op are green. |
| AC4 | `qualification.py` checks a future full fresh canonical capture, candidate binding, host lock and capacities, complete outcomes, elapsed/deadline/quiet comparisons and stage metrics. | Synthetic checker inputs reject 5207 seconds and accept 3300 seconds. These are checker tests only. Neither the measured canonical gate nor its fixed-sixteen falsifier ran. |

## Evidence

`red-green.json` binds each registered drive and every source hash to the tested
commit. The three adjacent diff files retain the exact falsifying changes, made
only in disposable directories. `suite-results.json` records the two edited suite
files. Partial selftest success exits 2 by repository convention; it is not a gate
receipt. The logs include the ordinary shared preamble's negative fixture messages.

`kernel.json` records a real delegated scope, CPU-bound children holding 256 MiB,
two elapsed speeds, and a separate user unit. CPU and memory errors are below
10 percent against the independent child measurements and allocated load. The
native check creates only its own scope and uniquely named service. It never
calls the host-lock API or reads the host lock configuration. The outer command
holds the real host lock. Each service and worker cgroup is cleaned before exit.

`anchor-audit.json` checks exact occurrence counts for all existing mutation
anchors targeting the changed modules, including VELDO-0215's anchors. It runs
no other ticket's suite or falsifiers. Engine and repository copies are identical.

`red-green-before-inventory-fix.json` is retained as preliminary evidence only.
Its final source stability assertion failed after the inventory fixture changed;
it must not be used as the final source-bound receipt.

## Commands and scope

Final ticket checks and mutation drives run under the owner's blocking flock:

```
flock /home/dmitry/.local/state/core-gates/.gate.lock python3 -B proof/VELDO-0219/local_check.py
flock /home/dmitry/.local/state/core-gates/.gate.lock python3 -B proof/VELDO-0219/kernel_check.py
```

No canonical gate, other ticket suite, push or merge ran. Suite 53's existing
wiring fixtures use disposable copies of the gate with unrelated checks disabled,
no host configuration and a scratch HOME. Those are not canonical qualification.
Initial development single-file suite runs preceded the final locked proof runs;
the retained final receipts come from the blocking flock commands above.

## Measurement limits

Anonymous memory is sampled at coordinator polls, not reported as kernel total
memory or page cache. Per-root peaks are added conservatively, and nested unit
cgroups are deduplicated. Unit discovery polls the ownership ledger; a unit that
starts and disappears entirely between discovery polls can evade measurement.
Reusing a unit cgroup path within one worker can also lose an earlier incarnation.
These cases need lifecycle-bound counter capture before claiming complete unit
accounting; OPEN.md records this remaining AC1 limitation. No historical duration
or total-memory receipt is relabeled as a measured anonymous-memory record.

Protected paths changed: scripts/check_gate_mutations.py,
engine/scripts/check_gate_mutations.py, scripts/reuse_worker.py,
engine/scripts/reuse_worker.py. No other protected path changed.
