# Veldo MCP server/client runner (reference)

A generic runner for the MCP (Model Context Protocol) surface: it drives an MCP
server over its JSON-RPC 2.0 transport and asserts the contract a tool provider
must actually honor, not just that it answered once. It performs the MCP
`initialize` handshake, then for each interaction in a fixture checks that
`tools/list` offers the expected tool set, that `tools/call` returns the expected
result for valid arguments (including a PROXIED tool the server fulfills by
delegating to another), and that an unknown tool or malformed params comes back as
a proper JSON-RPC ERROR rather than a crash or a fabricated success. Every
response is also checked for framing (JSON-RPC 2.0, the id echoed, exactly one of
result or error). It uses only the Python standard library.

MCP here is JSON-RPC 2.0 over a transport. The default transport is stdio: the
server is a child process and messages are newline-delimited JSON-RPC (one JSON
object per line, no embedded newlines), which is the MCP stdio framing.

## Use

```
mcp_runner.py <fixture.json>                  # spawn the bundled fake server over stdio
mcp_runner.py <fixture.json> <cmd> [args...]  # drive a real MCP server (its launch argv)
test_mcp_runner.sh                            # self-contained regression over both fixtures
```

With no command the runner spawns `fixtures/fake_mcp_server.py` (an echo/add/relay
server) over stdio, so it is driven end to end with no external MCP server. Give a
launch command (an argv, run without a shell) to point the same runner and the
same fixtures at a real MCP server instead.

## Fixture format

A fixture is a JSON list of interactions, or an object `{"name", "interactions":
[...]}`. The runner does the `initialize` handshake first, then drives each
interaction in order. An interaction names a method (`tools/list` or
`tools/call`), optional `params`, and an `expect` block:

```json
[
  {"name": "lists add, echo, relay", "method": "tools/list",
   "expect": {"tools": ["add", "echo", "relay"]}},
  {"name": "echo returns its text", "method": "tools/call",
   "params": {"name": "echo", "arguments": {"text": "hi"}},
   "expect": {"result_text": "hi"}},
  {"name": "relay proxies to echo", "method": "tools/call",
   "params": {"name": "relay", "arguments": {"text": "via relay"}},
   "expect": {"result_text": "via relay"}},
  {"name": "unknown tool is a JSON-RPC error", "method": "tools/call",
   "params": {"name": "nope", "arguments": {}},
   "expect": {"error_code": -32602}}
]
```

An interaction must declare at least one RECOGNIZED expectation for its method, or
it observes nothing and is reported as a named journey error (never a silent
pass). The recognized expectations:

`tools/list`
- `tools` the exact set of tool names offered (order-insensitive)
- `tools_include` each named tool must be offered (subset)

`tools/call`
- `result_text` the concatenated text content of the result equals this
- `result_contains` a substring of the concatenated text content
- `is_error` the result's `isError` flag (a tool-level failure, distinct from a
  JSON-RPC protocol error)
- `error_code` the response must be a JSON-RPC error with this integer code
- `error_contains` a substring of the JSON-RPC error message

A call the journey expects to succeed but that returns a JSON-RPC error (an
unknown tool, bad params, or a schema-mismatched result) is a failed step: the run
exits 1 naming the interaction, the tool call, and the observed error.

Exit 0 = every interaction met its contract. Exit 1 = at least one failed, with
the interaction and the exact expectation or framing violation named.

## Fixtures

`fixtures/pass.mcp.json` is a correctly-specified journey: the tool set matches,
valid calls (echo, add, and the PROXIED relay) return their expected results, a
tool-level error result is observed as such, and an unknown or malformed call is
correctly observed as a JSON-RPC error, so the runner exits 0.
`fixtures/fail.mcp.json` is the deliberately-failing journey: a step expects a
successful result from `delete_everything`, a tool the server does not expose, so
the server answers with a JSON-RPC error and the runner exits 1 naming the bad
tool call. A runner that could only ever say PASS is worse than none, so the fail
fixture is load-bearing.

```
mcp_runner.py fixtures/pass.mcp.json     # exit 0
mcp_runner.py fixtures/fail.mcp.json     # exit 1
```

## The bundled fake server

`fixtures/fake_mcp_server.py` is a minimal, faithful MCP server over JSON-RPC 2.0
with one shared core: `FakeMcpServer().handle(request) -> response` (the pure
handler the selftest drives in-process with no subprocess) and a stdio loop over
that handler (what the runner spawns by default). It models `initialize`,
`tools/list`, and `tools/call`, and both error channels: a tool-level error result
(`add` on a non-number, `isError` true) and JSON-RPC protocol errors (`-32601`
method not found, `-32602` invalid params or unknown tool, `-32002` a `tools/*`
call before `initialize`, `-32700` a non-JSON line). `relay` is a proxy tool: it
does no work of its own and re-dispatches to `echo`, so the runner can assert a
proxied result end to end. It is a test double: a consuming repo points the runner
at its own MCP server instead.

## Why this ships mechanical

The MCP stdio transport is a subprocess speaking newline-delimited JSON-RPC over
pipes, which needs only the Python standard library and no external service, so
the runner's real transport runs in the gate on an ordinary Linux box. The
selftest exercises the control logic two ways: over an in-process handler seam (a
fake `send` backed by `FakeMcpServer`, so the decision logic is proven with no
subprocess) AND over the real stdio subprocess transport driving both shipped
fixtures (pass -> exit 0, fail -> exit 1 with the bad tool call named). Because the
control logic and its real surface both run in the gate here, the capability is
declared `mechanical`. An adopting repo points the runner at its own MCP server
(its launch argv) and wires it to the contract or integration gate slot.

## Out of scope

The reference models the `tools/*` slice of MCP that a tool-provider contract
turns on (handshake, listing, calling, proxying, and the error channels). Other
MCP methods (resources, prompts, sampling, notifications beyond the ignored
`initialized` notification) and non-stdio transports (HTTP or SSE) are transports
and method families an adopting repo adds against its own server; the stdio
JSON-RPC seam and the assertion vocabulary are the same.
