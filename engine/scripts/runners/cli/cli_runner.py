#!/usr/bin/env python3
"""VELDO CLI / process runner (reference).

Drives real command-line processes and asserts their observable contract: exit
code, stdout, stderr, and a wall-clock budget. It reads a fixture (a JSON list
of cases), runs each command as a real subprocess (no shell), checks every
declared expectation against what the process actually did, and prints PASS or
FAIL per case. Exit 0 = every case met its contract; exit 1 = at least one case
failed, with the failing case and the exact expectation that broke named on
stdout. A runner that could only ever say PASS is worse than none, so the
suite ships a deliberately-failing fixture that must exit 1.

  cli_runner.py <fixture.json>

A fixture is a JSON list of cases. A case:

  {
    "name": "status prints ok",          # optional label; defaults to the cmd
    "cmd": ["mytool", "status"],         # argv array, run WITHOUT a shell
    "stdin": "optional text on stdin",
    "expect": {
      "exit_code": 0,                     # exact exit status
      "stdout_contains": "ok",           # substring, or a list of substrings
      "stderr_contains": "warning",      # substring, or a list of substrings
      "stdout_equals": "ok\n",           # exact stdout match
      "max_seconds": 5                    # kill and fail if it runs longer
    }
  }

Every expectation key is optional; a case asserts only what it declares. The
control logic (running a case, evaluating expectations) is pure and driven over
the fixtures with no external dependency in scripts/selftest.py, so the runner
itself is gate-tested without needing the tool under test.
"""
import json
import subprocess
import sys
import time
from pathlib import Path


def _as_list(v):
    """A *_contains expectation may be one substring or a list of substrings."""
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def check_result(result, expect):
    """Pure predicate: given an observed result and an expect block, return the
    list of failure strings (empty = the case met its contract). No I/O here, so
    the assertion logic is trivially testable and never rubber-stamps."""
    if result.get("not_found"):
        return [f"command not found: {result.get('stderr', '').strip()}"]
    if result.get("timed_out"):
        return [f"exceeded max_seconds={expect.get('max_seconds')} (process killed)"]
    failures = []
    if "exit_code" in expect and result["exit_code"] != expect["exit_code"]:
        failures.append(f"exit_code: expected {expect['exit_code']}, got {result['exit_code']}")
    if "stdout_equals" in expect and result["stdout"] != expect["stdout_equals"]:
        failures.append(f"stdout_equals: expected {expect['stdout_equals']!r}, got {result['stdout']!r}")
    for needle in _as_list(expect.get("stdout_contains")):
        if needle not in result["stdout"]:
            failures.append(f"stdout_contains: {needle!r} not in stdout")
    for needle in _as_list(expect.get("stderr_contains")):
        if needle not in result["stderr"]:
            failures.append(f"stderr_contains: {needle!r} not in stderr")
    return failures


def run_command(cmd, stdin=None, max_seconds=None, cwd=None):
    """Run one command as a real subprocess and return its observed behavior."""
    start = time.time()
    try:
        proc = subprocess.run(
            cmd, input=stdin, capture_output=True, text=True,
            timeout=max_seconds, cwd=cwd,
        )
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "elapsed": round(time.time() - start, 3),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "exit_code": None,
            "stdout": e.stdout or "",
            "stderr": e.stderr or "",
            "elapsed": round(time.time() - start, 3),
            "timed_out": True,
        }
    except FileNotFoundError as e:
        return {
            "exit_code": None,
            "stdout": "",
            "stderr": str(e),
            "elapsed": round(time.time() - start, 3),
            "timed_out": False,
            "not_found": True,
        }


def run_case(case, cwd=None):
    """Run one case and grade it. Returns a per-case result dict."""
    if "cmd" not in case or not isinstance(case["cmd"], list) or not case["cmd"]:
        label = case.get("name") or "<no cmd>"
        return {"name": label, "passed": False,
                "failures": ["case has no 'cmd' argv list"], "result": {}}
    expect = case.get("expect", {})
    result = run_command(
        case["cmd"], stdin=case.get("stdin"),
        max_seconds=expect.get("max_seconds"), cwd=cwd,
    )
    failures = check_result(result, expect)
    label = case.get("name") or " ".join(case["cmd"])
    return {"name": label, "passed": not failures, "failures": failures, "result": result}


def run_fixture(cases, cwd=None, out=None):
    """Run every case. Returns {"passed": bool, "cases": [...]} and, when out is
    given, prints PASS/FAIL lines naming any broken expectation."""
    results = []
    all_passed = True
    for case in cases:
        r = run_case(case, cwd=cwd)
        results.append(r)
        if out is not None:
            if r["passed"]:
                print(f"PASS  {r['name']}", file=out)
            else:
                for f in r["failures"]:
                    print(f"FAIL  {r['name']}: {f}", file=out)
        if not r["passed"]:
            all_passed = False
    return {"passed": all_passed, "cases": results}


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    fixture = Path(argv[1])
    try:
        cases = json.loads(fixture.read_text())
    except Exception as e:
        print(f"cannot read fixture {fixture}: {e}")
        return 2
    if not isinstance(cases, list):
        print(f"fixture {fixture} must be a JSON list of cases")
        return 2
    summary = run_fixture(cases, cwd=str(fixture.parent), out=sys.stdout)
    total = len(summary["cases"])
    passed = sum(1 for c in summary["cases"] if c["passed"])
    print(f"cli runner: {passed}/{total} cases passed")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
