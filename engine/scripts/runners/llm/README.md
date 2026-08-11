# Veldo LLM/eval runner (reference)

A generic evaluation runner for model-driven behavior: it grades a set of cases,
budgets the spend and the latency, and fails a regression when a prompt change
breaks a case that used to pass. Model behavior is the one product surface where
"it ran" says nothing about "it is correct", and a prompt edit can silently break
a case far from the one it targeted. It uses only the Python standard library.

## Use

```
veldo_llm_runner.py <journey.json>     # exit 0 = budgets + pass rate hold, no regression
test_llm_runner.sh                    # self-contained regression
```

A live model is nondeterministic and costs money, so it cannot run in an
every-commit gate. The model is a PROVIDER seam: a callable that takes a case and
returns `{"output": str, "cost": float, "latency": float}`. This reference ships
a deterministic fake provider that returns each case's canned `fake` block, so
the grading, budgets, and regression detection are gate-tested with no live
model. An adopting repo imports `run()` and passes `provider=` its own callable
(which calls its real model) unchanged.

## Journey format

```json
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
```

Each case declares an `id`, an `input`, behavioral `graders`, and (for the fake
provider) a `fake` block. A case passes only if EVERY grader holds:

- `contains` - the output must contain the substring `value`.
- `not_contains` - the output must NOT contain the substring `value`.
- `equals` - the output must equal `value` exactly.
- `regex` - `value` (a regular expression) must search the output.

A case with no graders is a journey error, not a pass: a case that asserts
nothing is not proof.

Budgets are totals across the set, each optional and each present one must hold:
`max_total_cost`, `max_total_seconds`, and `min_pass_rate` (the fraction of cases
that must pass).

Regression is the distinctive check. When `prompt_id` differs from
`baseline.prompt_id`, any case listed in `baseline.passed_cases` that now fails is
a regression, named with both prompt ids, and it fails the run even when the new
prompt's other cases pass - because a prompt edit that quietly breaks a working
case is exactly the defect a happy-path eval misses.

The `fixtures/` pair demonstrates both outcomes: `pass.journey.json` (all cases
pass under the new prompt, no regression, budgets met) exits 0, and
`fail.journey.json` (the new prompt regresses the `refund` case that passed under
the baseline prompt) exits 1 with the regression named.

## Why it is a reference

It ships working and self-tested, but a repository wires it to ITS eval set and
ITS model provider, then points the gate's `eval` slot at it. The runner's
control logic - the graders, the budget checks, and the regression detection - is
unit-tested in `scripts/selftest.py` with the deterministic fake provider, so the
every-commit gate proves the logic with no live model. The veldo home repository
ships no model-driven behavior of its own, so it does not run the runner in its
own gate; it ships it for repos that do.
