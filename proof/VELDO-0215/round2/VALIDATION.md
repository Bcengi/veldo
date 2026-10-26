# VELDO-0215 round 2 diagnostics

Base: fbd62ba1aefafb92d59b47d8415bb31b982d32b5, branch
agent/codex/veldo-mutation-case-deadlines. Source hashes and compressed receipts/logs are
recorded in validation.json. This is a targeted diagnostic record, not a canonical green
gate or independent review. The user reserved the full gate; none was run. The historical
round 1 manifest and artifacts remain unchanged and do not claim validation of round 2.

## F1: scheduler bound

For each of the sequential control and mutant phases, let W be total job deadlines,
L the largest deadline, m workers, and R_r each resource's admission-chain allowance:

    phase = min(W, W/m + L + sum(R_r))
    stage = max(old count-based cap, 120 + control_phase + mutant_phase)

R_r includes slot-weighted deadlines divided by the effective capacity, plus the largest
preceding user's deadline for each request needing more than one slot. This additional
term covers partial-occupancy drain waits, including exclusive requests. The first pending
job is never barred by an earlier pending request; if a worker slot is free, that job is
waiting on a resource. Later users cannot pass its barrier. The spec derives the bound
from SuiteResources.select and Workers.run, including phase separation, multiple resources,
capacity overrides and the final active-job tail.

The full current inventory, planned fresh at 16 workers with the store as measured after
targeted validation, has 2,571 cases, 744 controls and 2,571 mutants. Its cap is
**53,800.03908249566 seconds (14.94 hours)**: 120 setup + 10,541.692777487835 controls +
43,138.34630500783 mutants. The old count-only cap is 5,142 seconds. The serial formula on
these same inputs is 403,020.9012210875 seconds (4.66 days), versus the historical round 1
401,704-second cap. There are 46 current-key allowances above the floor. The source change
invalidates historical keys as intended; no historical samples were copied to new keys.

Run `python3 proof/VELDO-0215/round2/calculate_cap.py` from the repository root to repeat
planning against the then-current store. It launches no workers, runs no gate, and writes
no store entries. full-inventory-cap.json preserves the measured inputs, phase terms and
per-resource breakdown used for the value above.

## F2: rolling peak

The authority writer retains timestamped, undominated samples within 30 days of the same
key. New smaller samples cannot reduce the live peak or renew its timestamp. A newer sample
removes older samples no larger than itself. Reads discard expired samples too; a quieter
sample becomes the peak when older larger samples expire. Legacy single samples use their
file mtime. Authority-only writes, atomic replacement and store-file pruning remain intact.

## Rows and mutants

| Row | Coverage | Mutants killed |
| --- | --- | --- |
| case-deadlines/combined-budget | Exact parallel, serial, two-phase, old-cap floor and empty bounds; real selector/reservation event simulation with capacity overrides, shared/exclusive/multi-resource demands and shortened jobs | deadline215-old-stage-cap; new deadline215-serial-stage-cap |
| case-deadlines/rolling-maximum | Quiet runs preserve live peaks; larger samples raise peaks; expired peaks fall back to surviving samples; read-time expiry; legacy migration and pruning | new deadline215-latest-sample |

All 18 finding-215 mutants were killed. The serial mutant failed combined-budget; the
latest-sample mutant failed rolling-maximum. The old count-only mutant failed combined-budget
and existing stage/worker rows. Exact failed row lists are in validation.json and the receipt.

## Commands and results

- `python3 scripts/selftest.py --suite 112_veldo_0215_case_deadlines`: 40 passed, 0 failed
  (14 own rows plus 26 shared); exit 2 is the dispatcher's required partial-run status.
- `python3 scripts/check_gate_mutations.py --finding 215 --receipt /tmp/veldo215-r2-finding215.json`:
  exit 0, 18 registered/executed/rejected, 0 reused, 23.972 seconds; no invalid results or surviving workers.
- `python3 scripts/check_gate_mutations.py --finding 60 --finding 148 --finding 215 --finding 123 --finding 204 --finding 210 --finding 214 --receipt /tmp/veldo215-r2-affected.json`:
  exit 0, 108 registered/executed/rejected, 0 reused, 379.714 seconds; no invalid results or surviving workers.
- The six existing diagnostic suites from round 1 were also run: 53_veldo_0123_mutations,
  97_veldo_0204_gate_resources, 98_veldo_0204_mutation_receipts, 99_veldo_0205_reuse,
  100_veldo_0207_case_reuse and 104_veldo_0210_mutation_workers. Initially 211 passed and
  eight suite-99 rows failed (exit 1). Its resource stub exposed only summary(), whereas the
  new budget calculation needs demand() and capacity. Replaced that stub with an empty real
  SuiteResources pool without weakening assertions. The other five suites passed unchanged.
- `python3 scripts/selftest.py --suite 99_veldo_0205_reuse`: final 55 passed, 0 failed
  (29 own plus 26 shared), including embedded count/force negative controls; expected exit 2.
- Supplemental `--finding 205` was declined (exit 1, incomplete_inventory: empty or unknown
  subset): no registered finding-205 cases exist. It launched no workers. The suite's embedded
  negative controls above supply the relevant check.
- A read-only anchor audit applied all 2,571 mutations in memory without errors.
- Changed Python parses; coordinator/engine copies are identical; git diff --check passes.

Only the suite-99 fixture and spec/proof documentation changed after the affected run; the
coordinator, suite 112 and registered mutants are the exact tested bytes. No approval is
authored. No other branch was touched and nothing was pushed.
