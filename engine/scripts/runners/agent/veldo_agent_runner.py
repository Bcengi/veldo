#!/usr/bin/env python3
"""VELDO agent-loop / tool-execution runner (reference).

Drives a real agent turn (the agent plans, calls tools, reads their results, and
answers) and asserts the OBSERVED tool invocations and their real outputs, not
the agent's narration. The property that matters for an agent is not "it replied"
but "it actually called the right tools with the right arguments in the right
order and got the real results back". An agent that narrates a tool call it never
made, or answers from a fabricated result, is the central failure mode of the
surface, and a plain output check misses it entirely.

  veldo_agent_runner.py <journey.json>

The honest core: the HARNESS owns tool execution. The agent step emits tool CALLS
(a tool name and its args) and, eventually, a final answer. It never supplies
tool RESULTS. The harness looks up each called tool in the journey registry,
executes it, records the invocation with its real returned result, and feeds that
real result back into the message history for the next step. Every assertion is
against what the harness observed and executed, so a scripted or real agent
cannot make a result up to satisfy a check.

The agent is a STEP seam: a callable step(messages) -> a dict that is either
{"tool_calls": [{"tool": name, "args": {...}}, ...]} or {"final": "answer"}. This
reference ships a deterministic fake step scripted from the journey, so the whole
loop is replayable in the gate with no live agent. An adopting repo passes
step=its own callable (which calls its real agent) and tools=its real functions,
unchanged.

Journey format (JSON):
  {
    "name": "trip lookup",
    "prompt": "What time is the museum open in the trip city?",
    "max_turns": 6,
    "tools": {
      "get_city":    {"returns": "Paris"},
      "open_hours":  {"echo": "place"}
    },
    "fake": [
      {"tool_calls": [{"tool": "get_city", "args": {}}]},
      {"tool_calls": [{"tool": "open_hours", "args": {"place": "museum"}}]},
      {"final": "The museum in Paris opens at 9."}
    ],
    "assert": {
      "expected_tool_calls": [
        {"tool": "get_city", "result_equals": "Paris"},
        {"tool": "open_hours", "args_contains": {"place": "museum"},
         "result_equals": "museum"}
      ],
      "forbidden_tools": ["delete_trip"],
      "final": [{"type": "contains", "value": "Paris"}]
    }
  }

Tool registry (each tool a deterministic canned behavior for the reference):
  {"returns": <value>}     the tool always returns <value>
  {"echo": "<arg key>"}    the tool returns the value of that arg (so a result
                           can depend on the args the agent passed)
An adopting repo passes tools={name: callable(args) -> result} of its real
functions instead.

Assertions (assert block; the journey must assert at least one of these or it is
a journey error - a check that asserts nothing is not proof):
  expected_tool_calls  an ordered list matched one-to-one against the real
                       invocations the harness executed. A wrong tool, a wrong
                       order, a missing call, or an extra call fails naming the
                       position. Each entry may assert:
                         tool            the tool name at that position
                         args_equals     the args dict exactly
                         args_contains   each given key present with an equal value
                         result_equals   the real returned result exactly
                         result_contains substring (string result), subset (dict
                                         result), membership (list result)
  forbidden_tools      tools that must never be invoked; any observed invocation
                       of one fails naming it
  final                behavioral graders on the final answer (contains,
                       not_contains, equals, regex; every grader must hold)

Exit 0 = every assertion holds. Exit 1 = the first failing assertion, an unknown
tool, a non-finalizing loop (max_turns), or an asserts-nothing journey is named.
"""
import json
import re
import sys
from pathlib import Path

DEFAULT_MAX_TURNS = 8


def grade(output, graders):
    """Apply the final-answer graders. Returns a list of failure strings; an
    empty list means every grader held. Mirrors the LLM/eval runner's graders."""
    failures = []
    for g in graders or []:
        kind = g.get("type")
        value = g.get("value")
        if kind == "contains":
            if value not in (output or ""):
                failures.append(f"final contains: answer does not contain {value!r}")
        elif kind == "not_contains":
            if value in (output or ""):
                failures.append(f"final not_contains: answer unexpectedly contains {value!r}")
        elif kind == "equals":
            if output != value:
                failures.append(f"final equals: expected {value!r}, got {output!r}")
        elif kind == "regex":
            if re.search(value, output or "") is None:
                failures.append(f"final regex: {value!r} did not match the answer")
        else:
            failures.append(f"final: unknown grader type {kind!r}")
    return failures


def build_fake_tools(registry):
    """Build deterministic tool callables from the journey registry so the loop
    is replayable with no live tools. An adopting repo passes its real callables
    instead."""
    tools = {}
    for name, spec in (registry or {}).items():
        spec = spec or {}
        if "returns" in spec:
            const = spec["returns"]
            tools[name] = (lambda c: (lambda args: c))(const)
        elif "echo" in spec:
            key = spec["echo"]
            tools[name] = (lambda k: (lambda args: (args or {}).get(k)))(key)
        else:
            tools[name] = (lambda args: None)
    return tools


def build_fake_step(script):
    """A deterministic scripted step. Returns the i-th scripted turn on the i-th
    call; once the script is exhausted it repeats the last turn, so a script
    whose last turn is a tool call models an agent that never finalizes (it will
    hit max_turns), and a script that ends in a final answer terminates."""
    turns = list(script or [])
    state = {"i": 0}

    def step(messages):
        i = state["i"]
        state["i"] = i + 1
        if not turns:
            return {"final": ""}
        return turns[i] if i < len(turns) else turns[-1]

    return step


def _asserts_nothing(assertion):
    """A journey that asserts nothing is not proof. expected_tool_calls being
    PRESENT (even as an empty list, which asserts zero calls) counts as an
    assertion; forbidden_tools and final count only when non-empty."""
    has_calls = "expected_tool_calls" in assertion
    has_forbidden = bool(assertion.get("forbidden_tools"))
    has_final = bool(assertion.get("final"))
    return not (has_calls or has_forbidden or has_final)


def _result_contains(observed, expected):
    """result_contains: substring for a string result, subset for a dict result,
    membership for a list result, equality otherwise."""
    if isinstance(observed, str) and isinstance(expected, str):
        return expected in observed
    if isinstance(observed, dict) and isinstance(expected, dict):
        return all(k in observed and observed[k] == v for k, v in expected.items())
    if isinstance(observed, list):
        needed = expected if isinstance(expected, list) else [expected]
        return all(item in observed for item in needed)
    return observed == expected


def _match_call(expected, obs, i):
    """Assert one expected entry against the observed invocation at position i.
    Returns a list of failure strings (empty means it matched)."""
    failures = []
    if "tool" in expected and obs["tool"] != expected["tool"]:
        failures.append(
            f"tool call {i}: expected tool {expected['tool']!r}, observed {obs['tool']!r}")
        return failures  # a wrong tool makes arg/result checks meaningless
    if "args_equals" in expected and obs["args"] != expected["args_equals"]:
        failures.append(
            f"tool call {i} ({obs['tool']}): args {obs['args']!r} != expected {expected['args_equals']!r}")
    if "args_contains" in expected:
        for k, v in expected["args_contains"].items():
            if (obs["args"] or {}).get(k) != v:
                failures.append(
                    f"tool call {i} ({obs['tool']}): arg {k!r}={((obs['args'] or {}).get(k))!r} != expected {v!r}")
    if "result_equals" in expected and obs["result"] != expected["result_equals"]:
        failures.append(
            f"tool call {i} ({obs['tool']}): result {obs['result']!r} != expected {expected['result_equals']!r}")
    if "result_contains" in expected and not _result_contains(obs["result"], expected["result_contains"]):
        failures.append(
            f"tool call {i} ({obs['tool']}): result {obs['result']!r} does not contain {expected['result_contains']!r}")
    return failures


def _check_assertions(assertion, observed, final):
    """Apply forbidden_tools, expected_tool_calls (ordered one-to-one), and the
    final graders. Returns a list of failure strings."""
    failures = []
    forbidden = assertion.get("forbidden_tools") or []
    for i, obs in enumerate(observed):
        if obs["tool"] in forbidden:
            failures.append(f"forbidden tool invoked at call {i}: {obs['tool']!r}")

    if "expected_tool_calls" in assertion:
        expected = assertion["expected_tool_calls"]
        if len(expected) != len(observed):
            failures.append(
                f"expected {len(expected)} tool call(s), observed {len(observed)} "
                f"(observed: {[o['tool'] for o in observed]})")
        for i in range(min(len(expected), len(observed))):
            failures.extend(_match_call(expected[i], observed[i], i))

    failures.extend(grade(final, assertion.get("final")))
    return failures


def run(journey, step=None, tools=None):
    """Drive the agent loop and return a machine-readable result.

    step(messages) -> {"tool_calls": [...]} or {"final": str}; defaults to the
    deterministic scripted fake step. tools -> {name: callable(args) -> result};
    defaults to the deterministic fake registry. The harness executes every tool
    itself and records the real result, so assertions are against observed
    behavior, not the agent's narration.
    """
    assertion = journey.get("assert", {}) or {}
    result = {"agent": journey.get("name"), "passed": True, "observed": [],
              "final": None, "turns": 0, "failures": [], "error": None}

    if _asserts_nothing(assertion):
        result["passed"] = False
        result["error"] = "journey asserts nothing: a check that asserts nothing is not proof"
        result["failures"].append(result["error"])
        return result

    registry = tools if tools is not None else build_fake_tools(journey.get("tools", {}))
    step = step or build_fake_step(journey.get("fake", []))
    max_turns = int(journey.get("max_turns", DEFAULT_MAX_TURNS))
    observed = result["observed"]
    messages = [{"role": "user", "content": journey.get("prompt", "")}]
    final = None
    finalized = False

    for turn in range(max_turns):
        result["turns"] = turn + 1
        try:
            action = step(messages)
        except Exception as e:
            result["passed"] = False
            result["error"] = f"agent step error: {e}"
            result["failures"].append(result["error"])
            return result
        if not isinstance(action, dict):
            result["passed"] = False
            result["error"] = f"agent step returned {type(action).__name__}, expected a dict"
            result["failures"].append(result["error"])
            return result
        if "final" in action:
            final = action.get("final")
            finalized = True
            messages.append({"role": "assistant", "content": final})
            break
        calls = action.get("tool_calls") or []
        messages.append({"role": "assistant", "tool_calls": calls})
        for call in calls:
            name = call.get("tool")
            args = call.get("args", {})
            if name not in registry:
                result["passed"] = False
                result["error"] = f"unknown tool {name!r}: not in the journey tool registry"
                result["failures"].append(result["error"])
                return result
            try:
                tool_result = registry[name](args)
            except Exception as e:
                result["passed"] = False
                result["error"] = f"tool {name!r} raised: {e}"
                result["failures"].append(result["error"])
                return result
            observed.append({"tool": name, "args": args, "result": tool_result})
            messages.append({"role": "tool", "tool": name, "result": tool_result})

    if not finalized:
        result["passed"] = False
        result["error"] = f"agent did not finalize within max_turns={max_turns}"
        result["failures"].append(result["error"])
        return result

    result["final"] = final
    failures = _check_assertions(assertion, observed, final)
    if failures:
        result["passed"] = False
        result["failures"].extend(failures)
    return result


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    journey = json.loads(Path(sys.argv[1]).read_text())
    result = run(journey)
    for i, obs in enumerate(result["observed"]):
        print(f"call {i}: {obs['tool']}({obs['args']}) -> {obs['result']!r}")
    if result["final"] is not None:
        print(f"final: {result['final']!r}")
    if result["passed"]:
        print(f"agent journey PASSED: {result['agent']}")
        return 0
    for f in result["failures"]:
        print(f"FAIL - {f}")
    print(f"agent journey FAILED: {result['agent']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
