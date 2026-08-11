# Veldo agent-loop / tool-execution runner (reference)

A generic runner for an agent surface: an agent that plans, calls tools, reads
their results, and answers. It drives a real agent turn and asserts the OBSERVED
tool invocations and their real outputs, not the agent's narration. The property
that matters for an agent is not "it replied" but "it actually called the right
tools with the right arguments in the right order and got the real results back".
It uses only the Python standard library.

## Use

```
veldo_agent_runner.py <journey.json>   # exit 0 = every assertion holds
test_agent_runner.sh                  # self-contained regression
```

The harness owns tool execution. The agent step emits tool CALLS and, eventually,
a final answer; it never supplies tool RESULTS. The harness looks up each called
tool, executes it, records the invocation with its real returned result, feeds
that result back into the message history, and loops until the agent finalizes.
Every assertion is against what the harness observed and executed, so a scripted
or real agent cannot make a result up to satisfy a check.

The agent is a STEP seam: a callable `step(messages)` that returns either
`{"tool_calls": [{"tool": name, "args": {...}}, ...]}` or `{"final": "answer"}`.
This reference ships a deterministic fake step scripted from the journey, so the
whole loop is replayable in the gate with no live agent. An adopting repo passes
`step=` its own callable (which calls its real agent) and `tools=` its real
functions, unchanged.

## Journey format

```json
{
  "name": "trip lookup",
  "prompt": "What time does the museum open in the trip city?",
  "max_turns": 6,
  "tools": {
    "get_city":   {"returns": "Paris"},
    "open_hours": {"echo": "place"}
  },
  "fake": [
    {"tool_calls": [{"tool": "get_city", "args": {}}]},
    {"tool_calls": [{"tool": "open_hours", "args": {"place": "museum"}}]},
    {"final": "The museum in Paris opens at 9."}
  ],
  "assert": {
    "expected_tool_calls": [
      {"tool": "get_city", "result_equals": "Paris"},
      {"tool": "open_hours", "args_contains": {"place": "museum"}, "result_equals": "museum"}
    ],
    "forbidden_tools": ["delete_trip"],
    "final": [{"type": "contains", "value": "Paris"}]
  }
}
```

The tool registry gives each tool a deterministic canned behavior for the
reference: `{"returns": <value>}` always returns that value, and `{"echo": "<arg
key>"}` returns the value of that argument (so a result can depend on the args the
agent passed). An adopting repo passes real callables instead.

Assertions (the journey must assert at least one, or it is a journey error - a
check that asserts nothing is not proof):

- `expected_tool_calls` - an ordered list matched one-to-one against the real
  invocations the harness executed. A wrong tool, a wrong order, a missing call,
  or an extra call fails naming the position. Each entry may assert the tool
  name, `args_equals` or `args_contains`, and `result_equals` or
  `result_contains` (substring for a string result, subset for a dict result,
  membership for a list result). The result assertion is against the
  harness-executed result, which the agent cannot fabricate.
- `forbidden_tools` - tools that must never be invoked (for example a destructive
  tool); any observed invocation of one fails naming it, even when the final
  answer looks correct.
- `final` - behavioral graders on the final answer (`contains`, `not_contains`,
  `equals`, `regex`); every grader must hold.

The loop is honest and terminates: an agent that never finalizes within
`max_turns` fails loud with a did-not-finalize error rather than looping forever,
and a call to a tool absent from the registry fails loud with an unknown-tool
error rather than being silently skipped.

The `fixtures/` pair demonstrates both outcomes: `pass.journey.json` (the right
tools called in order with the right results and a correct final) exits 0, and
`fail.journey.json` (the agent invokes a forbidden destructive tool and violates
the expected sequence) exits 1 with the failures named.

## Why it is a reference

It ships working and self-tested, but a repository wires it to ITS agent and ITS
tools, then points the gate's agent or eval slot at it. The runner's control
logic - the loop, the harness-owned tool execution, the ordered call matching,
the forbidden-tool check, the termination bound, and the final graders - is
unit-tested in `scripts/selftest.py` with the deterministic fake step, so the
every-commit gate proves the logic with no live agent. The veldo home repository
ships no live agent of its own, so it does not run the runner in its own gate; it
ships it for repos that do.
