---
schema: veldo.spec/v1
id: WARP-0306
title: CLI / process runner (reference)
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0003
work: B4
plan_revision: 2
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: The passing fixture passes and the runner exits 0 over it (every case
      met its declared expectation).
  - id: AC2
    text: The deliberately-failing fixture fails and the runner exits 1 over it,
      naming the failing case and the exact expectation that broke.
  - id: AC3
    text: Assertions reflect real observed process behavior - exit code, stdout,
      stderr, and a wall-clock budget read from a real subprocess, not stubbed.
  - id: AC4
    text: The control logic is unit-tested by driving the fixture pair with no
      external dependency, so the runner is gate-proven without the tool under
      test.
required_evidence: [unit, operational]
rollback: Additive under engine/scripts/runners/cli/; delete the
  directory and drop the selftest block and the capabilities entry to remove it.
  An adopting repo pins the prior plugin version to drop it.
---

## Intent

Command-line tools and long-running processes have an observable contract just
like an HTTP endpoint: the exit code, what lands on stdout, what lands on
stderr, and how long it takes. VELDO should ship a ready reference runner for
that surface so an adopting team pins its CLI's contract and catches a
regression at the gate instead of shipping it silently. This is work item B4 of
PLAN-0003 (the batteries suite), feature F5 (systems surfaces).

## Context

Follows the pattern set by the shipped web (WARP-0105) and Android (WARP-0107)
runners: a generic reference implementation under
`engine/scripts/runners/<surface>/`, a fixture PAIR (a passing fixture
and a deliberately-failing one so the runner cannot rubber-stamp), and a
selftest block that drives the control logic over those fixtures with no live
dependency. The runner reads a JSON list of cases (each a `cmd` argv array, an
optional `stdin`, and an `expect` block: `exit_code`, `stdout_contains`,
`stderr_contains`, `stdout_equals`, `max_seconds`), runs each command as a real
subprocess with no shell, asserts, prints PASS or FAIL per case, and exits 0
when all pass or 1 with the failure named. It is stdlib only, so a reviewer
reruns it with no setup; the fixtures drive commands present on any POSIX
system (echo, printf, false, cat, sh, true).

## Out of scope

Wiring the runner into the veldo repo's own gate. Per PLAN-0003 it ships marked
`reference` in `capabilities.yaml`: an adopting repo points a gate slot at its
own CLI, but the veldo repo (not itself a CLI under test) does not run it. Shell
parsing, pseudo-terminal / TUI rendering, and daemon lifecycle are separate
batteries (the terminal/TUI runner B19 and the process/daemon lifecycle runner
B13).

## Notes

Assertion evaluation lives in a pure predicate (`check_result`) with no I/O, and
`run_fixture` orchestrates the cases; the selftest drives both over the shipped
fixtures and also checks the predicate directly (a match returns clean, a
mismatch and a timeout return a failure, so there is no vacuous pass). The
operational evidence is the runner exiting 0 over the passing fixture and 1 over
the failing fixture, observed directly.
