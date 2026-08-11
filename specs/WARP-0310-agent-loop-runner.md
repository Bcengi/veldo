---
schema: veldo.spec/v1
id: WARP-0310
title: Agent-loop/tool-execution runner (reference) - B10 of PLAN-0003
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0003
work: B10
plan_revision: 2
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: An agent-loop runner ships at
      engine/scripts/runners/agent/veldo_agent_runner.py. It reads a
      journey (a name, a prompt, a tool registry mapping each tool name to a
      deterministic canned behavior, an optional max_turns, and an assert block)
      and drives a real agent turn through a STEP seam - a callable that, given
      the running message history, returns either a set of tool calls or a final
      answer. The HARNESS (not the agent) executes each requested tool from the
      registry, records the observed invocation (tool name, args, and the real
      returned result), feeds the real result back into the history, and loops
      until the agent returns a final answer. It exits 0 when every assertion
      holds and exits 1 with the first failing assertion named. The reference
      ships a deterministic fake step (scripted from the journey) so the control
      logic is gate-tested with no live agent; an adopting repo passes its own
      step callable (which calls its real agent) unchanged.
  - id: AC2
    text: The runner asserts the OBSERVED tool invocations and outputs, not the
      agent's narration. assert.expected_tool_calls is an ordered list matched
      one-to-one against the real invocations the harness executed - a wrong
      tool, a wrong order, a missing call, or an extra call fails naming the
      position and the mismatch. Each expected entry may assert the tool name,
      args (args_equals or args_contains), and the real result (result_equals or
      result_contains); an assertion against the harness-executed result, which
      the agent cannot fabricate because the agent never supplies tool results.
      assert.forbidden_tools names tools that must never be invoked (for example
      a destructive tool); any observed invocation of one fails naming it.
      assert.final grades the final answer with the behavioral graders contains,
      not_contains, equals, and regex (every grader must hold).
  - id: AC3
    text: The loop is honest and terminates. An agent that never returns a final
      answer within max_turns (default a small bound) fails loud with a
      did-not-finalize error rather than looping forever. A tool call naming a
      tool absent from the registry fails loud with an unknown-tool error, never
      a silent skip. A journey whose assert block asserts nothing (no
      expected_tool_calls, no forbidden_tools, and no final graders) is a journey
      error (a check that asserts nothing is not proof), failed loud.
  - id: AC4
    text: The control logic is unit-tested in scripts/selftest.py with a FAKE
      scripted step and NO live agent, mirroring the other reference runners. A
      happy journey passes (exit 0); a journey whose observed tool call diverges
      from expected_tool_calls fails naming the mismatch; a forbidden tool that
      the agent invokes fails naming it; a final that misses a grader fails; an
      agent that never finalizes hits max_turns and fails; an unknown tool fails
      loud; and an asserts-nothing journey is a journey error. Two shipped
      fixtures (a passing journey and a deliberately-failing journey) are driven
      end to end (pass -> exit 0, fail -> exit 1 with the failure named). All
      prior selftest cases keep passing and the gate stays green.
  - id: AC5
    text: The runner is generic - zero company or product names in the runner,
      fixtures, wrapper, or README - and .veldo/capabilities.yaml (template and
      repository instance, kept byte-identical) declares it status reference (a
      shipped reference wired per repo to its own agent and tools; the veldo home
      repo ships no live agent surface of its own to drive), never mechanical.
      The docs-hygiene, secret, lint, and template-sync gates stay green.
required_evidence: [unit]
rollback: git revert; B10 adds a new runner file, a fixture pair, a wrapper and a
  README under engine, a selftest block, and an honest capabilities
  entry (template and instance) - no protected gate script or enforcer is
  touched, so reverting removes the reference artifact and its unit block with no
  effect on any running gate; the prior selftest cases are unchanged.
---

## Intent

PLAN-0003 (the batteries) ships a reference runner for every common product
surface. B10 is the agent-loop / tool-execution surface. The outcome that should
become true is that a repository building on an agent (an LLM that plans, calls
tools, reads their results, and answers) can drop in a generic runner, point it
at its own agent and its own tools, and get proof that a task drives the RIGHT
tools with the RIGHT arguments in the RIGHT order and produces the right answer.
The property that matters for an agent is not "it replied" but "it actually
called the tools it claims to have called, and it got the real results back".
An agent that narrates a tool call it never made, or answers from a fabricated
result, is the central failure mode of the surface, and a plain output check
misses it entirely.

## Context

B10 of PLAN-0003, feature F2 (intelligence surfaces), pulled against plan
revision 2, with no dependency. It follows the shipped runners' pattern exactly:
a generic reference under engine/scripts/runners/, a fixture PAIR
(passing and deliberately-failing), a wrapper, a README, and a unit block that
gate-tests the control logic with a fake step and no live agent. It is the
sibling of the LLM/eval runner (WARP-0305): where that runner grades a single
model turn, this runner grades a multi-turn tool-using loop.

The honest core of the design: the HARNESS owns tool execution. The agent step
emits tool CALLS (name and args) and, eventually, a final answer; it never
supplies tool RESULTS. The harness looks up each called tool in the journey's
registry, executes it, records the invocation with its real returned result, and
feeds that real result back into the message history for the next step. Every
assertion is against what the harness observed and executed, so a scripted (or
real) agent cannot make a result up to satisfy a check. The reference tool
registry is a deterministic canned behavior per tool so the whole loop is
replayable in the gate with no live model; an adopting repo passes tools whose
callables are its real functions and a step that calls its real agent.

## Out of scope

Any specific agent framework or wire format (the runner is framework-neutral: a
step is just a callable returning tool calls or a final, and tools are just
callables). Token accounting and cost budgets, which the LLM/eval runner
(WARP-0305) already owns. Parallel or streaming tool calls within a single step
beyond an ordered list. Grounding checks that a final answer is entailed by the
tool results (the runner asserts the observed calls, their real outputs, and the
final via graders, not semantic entailment). Driving a live agent in the home
gate, because the veldo home repo ships no agent surface; the honest evidence
here is the fake-step control-logic test.

## Notes

Why reference (not mechanical): the veldo home repo has no live agent of its own,
so it cannot drive a real agent in its gate, and the honest evidence is the
fake-step unit tests, not a live run. required_evidence is [unit]. The step and
tools are seams so an adopting repo swaps in its real agent and functions with no
change to the runner. capabilities.yaml states status: reference, never
mechanical, because the veldo repo does not itself run it against a live agent.

The adversarial properties a reviewer should be able to confirm by rerunning the
selftest and driving the fixtures: (1) an observed tool call that diverges from
expected_tool_calls in name, order, args, or result is caught and named; (2) a
forbidden tool that the agent invokes fails even if the final answer looks
correct; (3) an agent that loops without finalizing hits max_turns and fails
rather than hanging; (4) an unknown tool call fails loud; (5) a journey that
asserts nothing is a journey error; (6) the result assertions are against the
harness-executed result, so a fake step that emits a plausible final cannot mask
a wrong tool result.
