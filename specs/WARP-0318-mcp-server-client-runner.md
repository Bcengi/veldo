---
schema: veldo.spec/v1
id: WARP-0318
title: MCP server/client runner (B18 of PLAN-0003)
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0003
work: B18
plan_revision: 2
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: An MCP (Model Context Protocol) server/client runner ships at
      engine/scripts/runners/mcp/mcp_runner.py. It drives an MCP server
      over its JSON-RPC 2.0 transport (stdio by default: the server is a child
      process and messages are newline-delimited JSON-RPC, one JSON object per
      line with no embedded newlines, the MCP stdio framing), performs the MCP
      initialize handshake, then reads a fixture (a JSON list of interactions, or
      an object with an interactions list) and drives each interaction in order.
      An interaction names a method (tools/list or tools/call), optional params,
      and an expect block. The transport is a seam: a StdioTransport over a real
      subprocess is the default, and an in-memory send backed by the bundled fake
      server is the seam the selftest drives with no subprocess. With no command
      the runner spawns the bundled fake MCP server; given a launch argv it drives
      a real MCP server unchanged.
  - id: AC2
    text: The runner asserts the tool-provider contract, not merely that the
      server answered once. For tools/list it checks the offered tool set (tools
      for the exact set, order-insensitive, or tools_include for a required
      subset). For tools/call it checks the result (result_text for the exact
      concatenated text content, result_contains for a substring, is_error for the
      tool-level isError flag) or a JSON-RPC error (error_code for the integer
      code, error_contains for a substring of the message). Proxying is asserted
      like any tool call: the bundled fake server exposes a relay tool it fulfills
      by delegating to echo, and a fixture step asserts the proxied result. Every
      response is framing-checked: jsonrpc 2.0, the id echoed, and exactly one of
      result or error with a well-formed error carrying an integer code and a
      message.
  - id: AC3
    text: A bad tool call fails loud. A step that expects a successful result from
      a call the server answers with a JSON-RPC error (an unknown tool, malformed
      params, or a schema-mismatched result), or that expects a tool the server
      does not expose, is a failed step: the run exits 1 naming the interaction,
      the tool call, and the observed error. A failed handshake, a transport or
      framing violation, and a fixture with no interactions each fail the run with
      the reason named rather than crashing.
  - id: AC4
    text: No rubber-stamping. An interaction that declares no recognized assertion
      for its method (an empty expect block, a typo such as result_txt, or a
      wrong-method key such as error_code on tools/list) observes nothing and is
      reported as a named journey error, never a silent pass. Assertions observe
      the server's real response, not the runner's own narration.
  - id: AC5
    text: The passing fixture
      (engine/scripts/runners/mcp/fixtures/pass.mcp.json) exits 0 and
      the deliberately-failing fixture
      (engine/scripts/runners/mcp/fixtures/fail.mcp.json) exits 1 with
      the failure named. The passing fixture matches the tool set, calls echo and
      add and the proxied relay with the expected results, observes a tool-level
      error result as such, and observes an unknown or malformed call as a JSON-RPC
      error. The failing fixture expects a successful result from a tool the server
      does not expose, so the server answers with a JSON-RPC error and the runner
      exits 1 naming the bad tool call. test_mcp_runner.sh drives both over the
      real stdio subprocess transport and binds no port.
  - id: AC6
    text: The control logic is unit-tested in scripts/selftest.py with no live
      service, network, or container. The pure functions (envelope framing,
      tools/list and tools/call grading, and the no-rubber-stamp rejection) are
      exercised in both directions, and the runner is driven over BOTH shipped
      fixtures two ways: through an in-process handler seam (a fake send backed by
      the bundled FakeMcpServer, no subprocess) AND over the REAL stdio subprocess
      transport speaking newline-delimited JSON-RPC 2.0 (pass -> exit 0, fail ->
      exit 1 with the bad tool call named). All prior selftest cases keep passing
      and the gate stays green.
  - id: AC7
    text: The runner is generic - zero company or product names in the runner,
      fixtures, fake server, wrapper, or README - and .veldo/capabilities.yaml
      (template and repository instance, kept byte-identical) declares it status
      mechanical, honestly, because the real stdio JSON-RPC subprocess transport
      needs only the standard library and runs in the gate on this Linux box (the
      selftest drives the real subprocess transport, not only a fake driver). The
      docs-hygiene, secret, lint, and template-sync gates stay green.
required_evidence: [unit, operational]
rollback: git revert; B18 adds a new runner file, a bundled fake server, a fixture
  pair, a wrapper and a README under engine, a selftest block, and a
  capabilities entry (template and instance) - no protected gate script or
  enforcer is touched, so reverting removes the reference artifact and its unit
  block with no effect on any running gate; the prior selftest cases are unchanged.
---

## Intent

PLAN-0003 (the batteries) ships a reference runner for every common product
surface. B18 is the MCP (Model Context Protocol) surface. The outcome that should
become true is that a repository exposing or consuming MCP tools can drive its MCP
server with a fixture and get proof of the tool-provider contract: the server
offers the tools it should, a valid call returns the expected result, a proxied
tool (one the server fulfills by delegating to another) returns the delegated
result, and a bad call comes back as a proper JSON-RPC error rather than a crash
or a fabricated success. A happy-path check that a tool returned something misses
the server that lists a tool it cannot run, the one that answers an unknown tool
with an invented success, and the one whose JSON-RPC framing drifts. This runner
pins all of that down and fails the run naming any interaction whose observed
response breaks its contract.

## Context

B18 of PLAN-0003, feature F2 (protocol and tool surfaces), pulled against plan
revision 2, with no dependency. It follows the shipped runners' pattern: a generic
reference under engine/scripts/runners/, a bundled stdlib fake server, a
fixture PAIR (a passing journey and a deliberately-failing journey), a wrapper, a
README, and a unit block that gate-tests the control logic. MCP is JSON-RPC 2.0
over a transport; the reference models the stdio transport (a subprocess, one JSON
object per line) because it is the common MCP local transport and needs only the
standard library. The transport is a seam, so the same control logic and the same
fixtures run against a real MCP server by passing its launch argv.

## Out of scope

Non-stdio MCP transports (HTTP and SSE) and MCP method families beyond the
tools/* slice a tool-provider contract turns on (resources, prompts, sampling, and
notifications beyond the ignored initialized notification): these are transports
and methods an adopting repo adds against its own server; the JSON-RPC seam and
the assertion vocabulary are unchanged. This spec adds no enforcer and touches no
protected path.

## Notes

Why mechanical (not reference): unlike the HTTP and DB runners, whose real target
surfaces the veldo home repo does not have, the MCP stdio transport is a subprocess
speaking newline-delimited JSON-RPC over pipes, which is fully realizable with the
standard library on an ordinary Linux box. The bundled fake server IS a real MCP
server, and the selftest drives both fixtures over the real stdio subprocess
transport, not only a fake driver, so the control logic AND its real surface run
in the gate here. required_evidence is [unit, operational]: unit is the selftest
control-logic block (framing, grading, and the no-rubber-stamp rejection in both
directions, plus the in-memory seam), operational is the two shipped fixtures
driven end to end over the real subprocess transport (pass -> exit 0, fail ->
exit 1 with the bad tool call named) via test_mcp_runner.sh. capabilities.yaml
states status: mechanical.

The adversarial properties a reviewer should confirm by rerunning the selftest and
driving the fixtures: (1) tools/list is graded for the exact set and for a subset,
and a missing tool fails; (2) a valid call, a proxied call (relay delegating to
echo), and a tool-level error result (add on a non-number, isError true) are each
observed correctly, distinct from a JSON-RPC protocol error; (3) a step expecting
a result from an unknown tool is caught and named, which is exactly what the
failing fixture demonstrates; (4) an interaction that declares no recognized
assertion (empty, a typo, or a wrong-method key) is a named journey error, never a
vacuous pass; (5) a failed handshake, a transport or framing violation, and an
empty fixture fail the run with the reason named rather than crashing.
