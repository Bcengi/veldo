---
schema: veldo.spec/v1
id: WARP-0304
title: Performance/load runner (reference) - B6 of PLAN-0003
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0003
work: B6
plan_revision: 2
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A generic performance/load runner ships at
      engine/scripts/runners/perf/veldo_perf_runner.py. It reads a load
      journey (JSON, a workload name and args, a total request count, a
      concurrency level, and budgets for latency percentiles, throughput, and
      error rate). It drives the workload the requested number of times across
      the requested number of worker threads, measures each request's latency and
      whether it errored, computes the latency percentiles (p50, p95, p99, max),
      the throughput (successful requests per wall-clock second), and the error
      rate, and asserts them against the budgets. It exits 0 when every budget
      holds and exits 1 with each breached budget named. The workload is a seam -
      the reference ships deterministic built-in workloads, and an adopting repo
      passes its own callable.
  - id: AC2
    text: The measurements are real and the budgets fail loud. A latency
      percentile over its budget fails with the measured value; a throughput
      below min_throughput_rps fails with the measured rate; and an error rate
      over max_error_rate fails with the measured rate and the count of failed
      requests. A request that raises is counted as an error, not a silent
      success, and its latency is excluded from the success percentiles so a wave
      of fast failures cannot flatter the latency numbers.
  - id: AC3
    text: A passing fixture and a deliberately-failing fixture ship under
      engine/scripts/runners/perf/fixtures/. The passing fixture drives
      a fast non-failing workload under concurrency with generous latency and
      throughput budgets and a zero error budget, and exits 0. The failing
      fixture drives a deterministically-failing workload (a fixed fraction of
      requests raise, chosen by request index so the outcome does not depend on
      timing) against a zero error budget, so the error-rate budget is breached
      and the runner exits 1 with the error rate and the failed count named.
  - id: AC4
    text: The runner's control logic is unit-tested in scripts/selftest.py with
      no external dependency - the percentile computation over known arrays, the
      summary over known latencies and errors, and check_budgets for each budget
      met and exceeded, plus the runner driven over both shipped fixtures (pass to
      exit 0, fail to exit 1 with the error rate named) and a check that the
      concurrency actually executes every request. All prior selftest cases keep
      passing and the gate stays green.
  - id: AC5
    text: The runner is generic - zero company or product names in the runner,
      fixtures, wrapper, or README - and .veldo/capabilities.yaml (template and
      repository instance, kept byte-identical) declares it status reference (a
      shipped reference an adopting repo wires to its performance gate slot with
      its own workload; the veldo repo does not run it), never mechanical. The
      docs-hygiene, secret, lint, and template-sync gates stay green.
required_evidence: [unit, operational]
rollback: git revert; B6 adds a new runner directory under engine, a
  selftest block, and an honest capabilities entry (template and instance) - no
  protected gate script or enforcer is touched, so reverting removes the
  reference artifact and its unit block with no effect on any running gate; the
  prior selftest cases are unchanged.
---

## Intent

PLAN-0003 (the batteries) ships a reference runner for every common product
surface. B6 is the performance and load surface. The outcome that should become
true is that a repository can drop in a generic runner, point it at a target,
drive that target under concurrency, and get proof that latency percentiles,
throughput, and the error rate stay inside declared budgets. Performance
regressions and failures-under-load are surface defects a single-request check
never sees: a target that answers one request in 5ms may fall over at
concurrency 50. This runner drives the load and asserts the budgets.

## Context

B6 of PLAN-0003, feature F1 (surface runners), pulled against plan revision 2,
depends on WARP-0301 (the HTTP/API runner, whose budget idea this generalizes
from one request to a population under concurrency). It follows the shipped
runners' pattern: a generic reference under engine/scripts/runners/, a
fixture PAIR, and a unit test that gate-tests the control logic. The workload is
a SEAM: a callable invoked once per request. The reference ships deterministic
built-in workloads (a fixed sleep, and a flaky one that raises on chosen request
indices) so the concurrency orchestration, the percentile math, and the budget
assertions are gate-tested with no external target, and an adopting repo passes
its own workload (which drives its real endpoint) unchanged. The fixtures keep
the gate deterministic by construction: the passing fixture pairs a fast
non-failing workload with generous latency and throughput budgets that hold on
any machine, and the failing fixture breaches a ZERO error budget with an
index-chosen failure fraction, so the pass and fail outcomes never depend on
wall-clock timing.

## Out of scope

Distributed or multi-machine load generation, ramp/soak profiles, and open-model
arrival-rate control - the reference is a fixed request count at a fixed
concurrency. Resource (CPU/memory) measurement of the target. Coordinated-
omission correction. Any real network target (the workload seam is where a repo
plugs that in). Wiring the veldo home repository's gate to this runner: the home
repo has no performance-sensitive surface of its own, so the runner ships as a
reference marked status reference and is not run in the home gate.

## Notes

A request that raises is an error: it increments the error count and its latency
is kept out of the success percentiles, so failing fast cannot make the latency
budget look good. Throughput is successful requests over wall-clock seconds.
Budgets are all optional and any present one must hold: max_p50_seconds,
max_p95_seconds, max_p99_seconds, min_throughput_rps, and max_error_rate. The
built-in workloads are selected by name (sleep, flaky, noop) with args; an
adopting repo instead imports run() and passes workload=its own callable, whose
signature is workload(request_index) and which raises to signal a failed request.
