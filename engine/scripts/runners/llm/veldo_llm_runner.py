#!/usr/bin/env python3
"""VELDO LLM/eval runner (reference).

Grades a set of model-driven cases, budgets the spend and the latency, and fails
a regression when a prompt change breaks a case that used to pass. Model behavior
is the one product surface where "it ran" says nothing about "it is correct", and
a prompt edit can silently break a case far from the one it targeted. This runner
turns an eval set into gate evidence.

  veldo_llm_runner.py <journey.json>

A live model is nondeterministic and costs money, so it cannot run in an
every-commit gate. The model is therefore a PROVIDER seam: a callable that takes
a case and returns {"output": str, "cost": float, "latency": float}. This
reference ships a deterministic fake provider that returns each case's canned
"fake" block, so the grading, budgets, and regression detection are gate-tested
with no live model. An adopting repo imports run() and passes provider=its own
callable (which calls its real model) unchanged.

Journey format (JSON):
  {
    "name": "support tone eval",
    "prompt_id": "v2",
    "budgets": {"max_total_cost": 0.05, "max_total_seconds": 5, "min_pass_rate": 1.0},
    "baseline": {"prompt_id": "v1", "passed_cases": ["greeting", "refund"]},
    "cases": [
      {"id": "greeting", "input": "hi",
       "graders": [{"type": "contains", "value": "hello"}],
       "fake": {"output": "Hello, how can I help?", "cost": 0.01, "latency": 0.2}}
    ]
  }

Grader kinds (a case passes only if EVERY grader holds):
  contains       the output must contain the substring `value`
  not_contains   the output must NOT contain the substring `value`
  equals         the output must equal `value` exactly
  regex          `value` (a regular expression) must search the output

Budgets (each optional; every present one must hold):
  max_total_cost     sum of case costs must not exceed this
  max_total_seconds  sum of case latencies must not exceed this
  min_pass_rate      fraction of cases that pass must be at least this

Regression: when prompt_id differs from baseline.prompt_id, any case in
baseline.passed_cases that now fails is a regression and fails the run.

Exit 0 = every budget and the pass rate hold and no regression. Exit 1 = a
failing case, budget, or regression is named. A case with no graders is a journey
error (a case that asserts nothing is not proof).
"""
import json
import re
import sys
from pathlib import Path


def grade(output, graders):
    """Apply a case's graders to its output. Returns a list of failure strings;
    an empty list means every grader held. A case with no graders is a journey
    error (asserting nothing is not proof), reported here so it fails loud."""
    if not graders:
        return ["no graders: a case that asserts nothing is not proof"]
    failures = []
    for g in graders:
        kind = g.get("type")
        value = g.get("value")
        if kind == "contains":
            if value not in output:
                failures.append(f"contains: output does not contain {value!r}")
        elif kind == "not_contains":
            if value in output:
                failures.append(f"not_contains: output unexpectedly contains {value!r}")
        elif kind == "equals":
            if output != value:
                failures.append(f"equals: expected {value!r}, got {output!r}")
        elif kind == "regex":
            if re.search(value, output) is None:
                failures.append(f"regex: {value!r} did not match output")
        else:
            failures.append(f"unknown grader type {kind!r}")
    return failures


def fake_provider(case):
    """The default deterministic provider: return the case's canned fake block.
    An adopting repo replaces this by passing its own provider to run()."""
    fake = case.get("fake") or {}
    return {"output": fake.get("output", ""),
            "cost": float(fake.get("cost", 0.0)),
            "latency": float(fake.get("latency", 0.0))}


def check_budgets(budgets, total_cost, total_seconds, pass_rate):
    """Evaluate the total-cost, total-latency, and pass-rate budgets. Returns a
    list of failure strings; empty means every present budget held."""
    failures = []
    if not budgets:
        return failures
    if "max_total_cost" in budgets and total_cost > budgets["max_total_cost"]:
        failures.append(
            f"max_total_cost: {total_cost:.4f} exceeds budget {budgets['max_total_cost']}")
    if "max_total_seconds" in budgets and total_seconds > budgets["max_total_seconds"]:
        failures.append(
            f"max_total_seconds: {total_seconds:.4f} exceeds budget {budgets['max_total_seconds']}")
    if "min_pass_rate" in budgets and pass_rate < budgets["min_pass_rate"]:
        failures.append(
            f"min_pass_rate: pass rate {pass_rate:.3f} is below {budgets['min_pass_rate']}")
    return failures


def find_regressions(journey, passed_ids):
    """Return regression failure strings: baseline-passed cases that now fail,
    evaluated only when the current prompt differs from the baseline prompt."""
    baseline = journey.get("baseline") or {}
    base_prompt = baseline.get("prompt_id")
    cur_prompt = journey.get("prompt_id")
    if not base_prompt or base_prompt == cur_prompt:
        return []
    failures = []
    for cid in baseline.get("passed_cases") or []:
        if cid not in passed_ids:
            failures.append(
                f"regression: case {cid!r} passed under prompt {base_prompt!r} "
                f"but fails under prompt {cur_prompt!r}")
    return failures


def run(journey, provider=None):
    """Grade the eval set and return a machine-readable result.

    provider(case) -> {"output", "cost", "latency"}; defaults to the fake
    provider that returns each case's canned block, so the runner is
    deterministic and gate-testable. Reports every failing case, then the
    budgets, then any regression.
    """
    provider = provider or fake_provider
    result = {"eval": journey.get("name"), "prompt_id": journey.get("prompt_id"),
              "passed": True, "cases": [], "budgets": None,
              "regressions": [], "error": None}
    cases = journey.get("cases", [])
    total_cost = 0.0
    total_seconds = 0.0
    passed_ids = set()
    for case in cases:
        cid = case.get("id")
        try:
            resp = provider(case)
        except Exception as e:
            result["cases"].append({"case": cid, "ok": False, "failures": [f"provider error: {e}"]})
            result["passed"] = False
            continue
        total_cost += float(resp.get("cost", 0.0))
        total_seconds += float(resp.get("latency", 0.0))
        failures = grade(resp.get("output", ""), case.get("graders"))
        if failures:
            result["cases"].append({"case": cid, "ok": False, "failures": failures})
            result["passed"] = False
        else:
            result["cases"].append({"case": cid, "ok": True})
            passed_ids.add(cid)

    pass_rate = (len(passed_ids) / len(cases)) if cases else 1.0
    result["pass_rate"] = pass_rate
    result["total_cost"] = round(total_cost, 6)
    result["total_seconds"] = round(total_seconds, 6)

    budget_failures = check_budgets(journey.get("budgets"), total_cost, total_seconds, pass_rate)
    result["budgets"] = {"ok": not budget_failures, "failures": budget_failures}
    if budget_failures:
        result["passed"] = False

    regressions = find_regressions(journey, passed_ids)
    result["regressions"] = regressions
    if regressions:
        result["passed"] = False

    return result


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    journey = json.loads(Path(sys.argv[1]).read_text())
    result = run(journey)
    for c in result["cases"]:
        if c["ok"]:
            print(f"PASS case {c['case']}")
        else:
            print(f"FAIL case {c['case']}")
            for f in c["failures"]:
                print(f"     - {f}")
    print(f"pass_rate {result.get('pass_rate'):.3f}  cost {result.get('total_cost')}  "
          f"seconds {result.get('total_seconds')}")
    for f in result["budgets"]["failures"]:
        print(f"FAIL budget - {f}")
    for r in result["regressions"]:
        print(f"FAIL {r}")
    if result["passed"]:
        print(f"llm eval PASSED: {result['eval']}")
        return 0
    print(f"llm eval FAILED: {result['eval']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
