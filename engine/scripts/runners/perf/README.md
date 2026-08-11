# Veldo performance/load runner (reference)

A generic load runner: it drives a target under concurrency and asserts that
latency percentiles, throughput, and the error rate stay inside declared
budgets. A performance regression or a failure-under-load is a surface defect a
single-request check never sees: a target that answers one request in 5ms may
fall over at concurrency 50. It uses only the Python standard library.

## Use

```
veldo_perf_runner.py <journey.json>     # exit 0 = every budget held
test_perf_runner.sh                    # self-contained regression
```

The workload is a SEAM: a callable invoked once per request as `workload(index)`,
which raises to signal a failed request. This reference ships deterministic
built-in workloads (selected by name), so the concurrency orchestration, the
percentile math, and the budget assertions are gate-tested with no external
target. An adopting repo imports `run()` and passes `workload=` its own callable
(which drives its real endpoint) unchanged.

## Journey format

```json
{
  "name": "checkout under load",
  "workload": "sleep",
  "workload_args": {"seconds": 0.002},
  "requests": 40,
  "concurrency": 8,
  "budgets": {
    "max_p95_seconds": 0.5,
    "max_p99_seconds": 1.0,
    "min_throughput_rps": 50,
    "max_error_rate": 0.0
  }
}
```

Built-in workloads (an adopting repo passes its own instead):

- `noop` - returns immediately.
- `sleep` `{seconds}` - sleeps a fixed time, never errors.
- `flaky` `{every_n, seconds}` - raises when `index % every_n == 0`, else sleeps;
  a deterministic, timing-independent error fraction.

Budgets are all optional and every present one must hold:

- `max_p50_seconds` / `max_p95_seconds` / `max_p99_seconds` - latency percentiles.
- `min_throughput_rps` - successful requests per wall-clock second.
- `max_error_rate` - fraction of requests that errored.

A request that raises is an error: it is counted, and its latency is excluded
from the success percentiles, so a wave of fast failures cannot flatter the
latency numbers. A breached budget stops nothing mid-run but fails the run, and
every breached budget is named.

The `fixtures/` pair demonstrates both outcomes deterministically:
`pass.journey.json` pairs a fast non-failing workload under concurrency with
generous latency and throughput budgets and a zero error budget (exit 0);
`fail.journey.json` drives a workload that raises on a fixed fraction of requests
(chosen by index, so the outcome does not depend on timing) against a zero error
budget, so the error-rate budget is breached and the run exits 1 with the error
rate and the failed count named.

## Why it is a reference

It ships working and self-tested, but a repository wires it to ITS target and
ITS workload, then points the gate's `performance` slot at it with realistic
budgets. The runner's control logic - the concurrency driving, the percentile
computation, and the budget assertions - is unit-tested in `scripts/selftest.py`
with the built-in workloads, so the every-commit gate proves the logic with no
external target. The veldo home repository has no performance-sensitive surface of
its own, so it does not run the runner in its own gate; it ships it for repos
that do.
