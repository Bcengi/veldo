#!/usr/bin/env python3
"""VELDO performance/load runner (reference).

Drives a target under concurrency and asserts that latency percentiles,
throughput, and the error rate stay inside declared budgets. A performance
regression or a failure-under-load is a surface defect a single-request check
never sees: a target that answers one request in 5ms may fall over at
concurrency 50. This runner drives the load and turns the budgets into gate
evidence.

  veldo_perf_runner.py <journey.json>

The workload is a SEAM: a callable invoked once per request as workload(index),
which raises to signal a failed request. This reference ships deterministic
built-in workloads (selected by name), so the concurrency orchestration, the
percentile math, and the budget assertions are gate-tested with no external
target. An adopting repo imports run() and passes workload=its own callable
(which drives its real endpoint) unchanged.

Journey format (JSON):
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

Built-in workloads (an adopting repo passes its own instead):
  noop                       returns immediately
  sleep  {seconds}           sleeps a fixed time, never errors
  flaky  {every_n, seconds}  raises when index % every_n == 0, else sleeps
                             (a deterministic, timing-independent error fraction)

Budgets (each optional; every present one must hold):
  max_p50_seconds / max_p95_seconds / max_p99_seconds   latency percentiles
  min_throughput_rps                                    successful req per second
  max_error_rate                                        fraction of requests that errored

Exit 0 = every budget held. Exit 1 = each breached budget is named. A request
that raises is an error (counted, and excluded from the success percentiles so a
wave of fast failures cannot flatter the latency numbers).
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def percentile(sorted_vals, p):
    """Linear-interpolated percentile of an already-sorted list. Returns 0.0 for
    an empty list. p is 0..100."""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * (p / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = k - lo
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac


def summarize(latencies, errors, total, wall):
    """Aggregate successful-request latencies, the error count, and wall-clock
    time into the stats the budgets are checked against."""
    ok = sorted(latencies)
    return {
        "requests": total,
        "ok": len(ok),
        "errors": errors,
        "error_rate": (errors / total) if total else 0.0,
        "throughput_rps": (len(ok) / wall) if wall > 0 else 0.0,
        "p50": percentile(ok, 50),
        "p95": percentile(ok, 95),
        "p99": percentile(ok, 99),
        "max": ok[-1] if ok else 0.0,
    }


def check_budgets(stats, budgets):
    """Evaluate the latency, throughput, and error-rate budgets. Returns a list
    of failure strings; empty means every present budget held."""
    failures = []
    if not budgets:
        return failures
    for key, pctl in (("max_p50_seconds", "p50"), ("max_p95_seconds", "p95"),
                      ("max_p99_seconds", "p99")):
        if key in budgets and stats[pctl] > budgets[key]:
            failures.append(f"{key}: {stats[pctl]:.4f}s exceeds budget {budgets[key]}s")
    if "min_throughput_rps" in budgets and stats["throughput_rps"] < budgets["min_throughput_rps"]:
        failures.append(
            f"min_throughput_rps: {stats['throughput_rps']:.2f} rps is below {budgets['min_throughput_rps']}")
    if "max_error_rate" in budgets and stats["error_rate"] > budgets["max_error_rate"]:
        failures.append(
            f"max_error_rate: {stats['error_rate']:.3f} exceeds budget {budgets['max_error_rate']} "
            f"({stats['errors']}/{stats['requests']} requests failed)")
    return failures


def _builtin_workload(name, args):
    """Return a deterministic built-in workload callable workload(index). An
    adopting repo passes its own callable to run() instead of naming one here."""
    args = args or {}
    if name == "noop":
        return lambda i: None
    if name == "sleep":
        seconds = float(args.get("seconds", 0.0))
        return lambda i: time.sleep(seconds)
    if name == "flaky":
        every_n = int(args.get("every_n", 4))
        seconds = float(args.get("seconds", 0.0))

        def wl(i):
            if every_n > 0 and i % every_n == 0:
                raise RuntimeError(f"injected failure at request {i}")
            if seconds:
                time.sleep(seconds)
        return wl
    raise ValueError(f"unknown workload {name!r} (built-ins: noop, sleep, flaky)")


def run(journey, workload=None):
    """Drive the load and return a machine-readable result. workload(index) is
    the target; it raises to signal a failed request. Defaults to the journey's
    named built-in so the runner is deterministic and gate-testable."""
    result = {"perf": journey.get("name"), "passed": True, "stats": None,
              "failures": [], "error": None}
    try:
        wl = workload or _builtin_workload(journey.get("workload"), journey.get("workload_args"))
    except Exception as e:
        result["passed"] = False
        result["error"] = str(e)
        return result
    requests = int(journey.get("requests", 0))
    concurrency = max(1, int(journey.get("concurrency", 1)))

    def one(i):
        start = time.monotonic()
        try:
            wl(i)
            return (time.monotonic() - start, None)
        except Exception as e:
            return (time.monotonic() - start, str(e))

    latencies = []
    errors = 0
    wall_start = time.monotonic()
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        for lat, err in ex.map(one, range(requests)):
            if err is None:
                latencies.append(lat)
            else:
                errors += 1
    wall = time.monotonic() - wall_start

    stats = summarize(latencies, errors, requests, wall)
    result["stats"] = stats
    failures = check_budgets(stats, journey.get("budgets") or {})
    result["failures"] = failures
    if failures:
        result["passed"] = False
    return result


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    journey = json.loads(Path(sys.argv[1]).read_text())
    result = run(journey)
    if result["error"]:
        print(f"ERROR: {result['error']}")
        return 1
    s = result["stats"]
    print(f"requests {s['requests']}  ok {s['ok']}  errors {s['errors']}  "
          f"error_rate {s['error_rate']:.3f}")
    print(f"throughput {s['throughput_rps']:.2f} rps  "
          f"p50 {s['p50']:.4f}s  p95 {s['p95']:.4f}s  p99 {s['p99']:.4f}s  max {s['max']:.4f}s")
    for f in result["failures"]:
        print(f"FAIL budget - {f}")
    if result["passed"]:
        print(f"perf load PASSED: {result['perf']}")
        return 0
    print(f"perf load FAILED: {result['perf']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
