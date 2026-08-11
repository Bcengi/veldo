#!/usr/bin/env python3
"""VELDO MCP (Model Context Protocol) server / client runner (reference).

Drives an MCP server over its JSON-RPC 2.0 transport and asserts the contract a
tool provider must actually honor, not just that it answered once: tools/list
offers the expected tool set, tools/call returns the expected result for valid
arguments (including a PROXIED tool the server fulfills by delegating to another,
asserted by its result like any other call), an unknown tool or malformed params
comes back as a proper JSON-RPC ERROR (not a crash and not a silent success), and
every response is well framed
(JSON-RPC 2.0, the id echoed, exactly one of result or error). A happy-path check
that a tool returned something misses the server that lists a tool it cannot run,
the one that answers an unknown tool with a fabricated success, and the one whose
framing drifts. This runner pins all of that down.

  mcp_runner.py <fixture.json> [command ...]

With no command it spawns the bundled fake MCP server (fixtures/fake_mcp_server.py,
an echo/add server) over stdio, so the runner is driven end to end with NO
external MCP server. Give a command (an argv, run without a shell) to point the
stdio transport at a real MCP server instead, unchanged; the fixture and every
assertion stay the same.

Transport seam. The control logic is a pure function of a send(request) ->
response callable. This reference ships two transports for it:
  StdioTransport   newline-delimited JSON-RPC 2.0 over a child process's stdin and
                   stdout (one JSON object per line, no embedded newlines: the MCP
                   stdio framing). This is the default and what an adopting repo
                   uses against its real server.
  in_memory_send   send() backed directly by a FakeMcpServer instance (no
                   subprocess), used by scripts/selftest.py so the control logic is
                   gate-tested with no live server, network, or container.

Fixture (JSON). A list of interactions, or an object {"name", "interactions": [...]}.
The runner performs the MCP initialize handshake first, then drives each
interaction in order. Each interaction names a method (tools/list or tools/call),
optional params, and an expect block:

  [
    {"name": "lists add and echo", "method": "tools/list",
     "expect": {"tools": ["add", "echo"]}},
    {"name": "echo returns its text", "method": "tools/call",
     "params": {"name": "echo", "arguments": {"text": "hi"}},
     "expect": {"result_text": "hi"}},
    {"name": "add sums its arguments", "method": "tools/call",
     "params": {"name": "add", "arguments": {"a": 2, "b": 3}},
     "expect": {"result_text": "5"}},
    {"name": "unknown tool is a JSON-RPC error", "method": "tools/call",
     "params": {"name": "nope", "arguments": {}},
     "expect": {"error_code": -32602}},
    {"name": "missing name is malformed params", "method": "tools/call",
     "params": {"arguments": {}},
     "expect": {"error_code": -32602}}
  ]

Expectations (an interaction must declare at least one, or it asserts nothing and
is a fixture error):
  tools/list
    tools           the exact set of tool names offered (order-insensitive)
    tools_include   each named tool must be offered (subset)
  tools/call
    result_text     the concatenated text content of the result equals this
    result_contains a substring of the concatenated text content
    is_error        the result's isError flag (a tool-level failure, distinct
                    from a JSON-RPC protocol error)
    error_code      the response must be a JSON-RPC error with this integer code
    error_contains  a substring of the JSON-RPC error message

Exit 0 = every interaction met its contract. Exit 1 = at least one failed, with
the interaction and the exact expectation or framing violation named. A runner
that could only ever say PASS is worse than none, so the suite ships a
deliberately-failing fixture (a wrong tool result and a success expected on an
unknown tool) that must exit 1.
"""
import json
import subprocess
import sys
from pathlib import Path

CLIENT_INFO = {"name": "veldo-mcp-runner", "version": "1.0.0"}
PROTOCOL_VERSION = "2025-06-18"


class TransportError(Exception):
    """A transport or framing failure (no response line, a non-JSON line, a
    closed pipe). The runner turns it into a named failure, never a crash."""


class StdioTransport:
    """Drive an MCP server over stdio: newline-delimited JSON-RPC 2.0 messages,
    one JSON object per line with no embedded newlines (the MCP stdio framing).
    Point command at the bundled fake server or a real MCP server; the seam is
    the same."""

    def __init__(self, command):
        self.proc = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1,
        )

    def send(self, request):
        line = json.dumps(request)
        if "\n" in line:
            raise TransportError("request serialized with an embedded newline (bad framing)")
        try:
            self.proc.stdin.write(line + "\n")
            self.proc.stdin.flush()
        except (BrokenPipeError, ValueError) as e:
            raise TransportError("cannot write to the server (pipe closed?): %s" % e)
        raw = self.proc.stdout.readline()
        if raw == "":
            raise TransportError("no response line: the server closed its stdout")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise TransportError("response line is not valid JSON-RPC: %s: %r" % (e, raw))

    def close(self):
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


def in_memory_send(server):
    """A send(request) -> response backed directly by a FakeMcpServer instance,
    no subprocess. The seam scripts/selftest.py drives so the control logic needs
    no live server."""
    def send(request):
        response = server.handle(request)
        if response is None:
            raise TransportError("server returned no response for a request")
        return response
    return send


def _content_text(result):
    """Concatenate the text of a tool result's text content items."""
    if not isinstance(result, dict):
        return ""
    parts = []
    for item in result.get("content") or []:
        if isinstance(item, dict) and item.get("type") == "text":
            parts.append(str(item.get("text", "")))
    return "".join(parts)


def validate_envelope(response, expected_id):
    """Assert JSON-RPC 2.0 framing on one response: the version, the echoed id,
    and exactly one of result or error (a well-formed error carrying an integer
    code and a message). Returns a list of framing failures (empty means the
    envelope is correct). Pure, so framing detection is unit-testable."""
    failures = []
    if not isinstance(response, dict):
        return ["framing: response is not a JSON object"]
    if response.get("jsonrpc") != "2.0":
        failures.append("framing: missing or wrong jsonrpc version (need '2.0')")
    if "id" not in response:
        failures.append("framing: response carries no id")
    elif response["id"] != expected_id:
        failures.append("framing: id mismatch (expected %r, got %r)" % (expected_id, response["id"]))
    has_result = "result" in response
    has_error = "error" in response
    if has_result and has_error:
        failures.append("framing: response carries both result and error")
    if not has_result and not has_error:
        failures.append("framing: response carries neither result nor error")
    if has_error:
        err = response["error"]
        if not isinstance(err, dict):
            failures.append("framing: error is not a JSON-RPC error object")
        else:
            code = err.get("code")
            if not isinstance(code, int) or isinstance(code, bool):
                failures.append("framing: error object needs an integer code")
            if "message" not in err:
                failures.append("framing: error object needs a message")
    return failures


def check_tools_list(expect, result):
    """Assert a tools/list result against the expectation. Returns failures."""
    if not isinstance(result, dict) or not isinstance(result.get("tools"), list):
        return ["tools/list: result carries no 'tools' array"]
    names = sorted(t.get("name") for t in result["tools"] if isinstance(t, dict))
    failures = []
    if "tools" in expect:
        want = sorted(expect["tools"])
        if names != want:
            failures.append("tools/list: expected tool set %s, observed %s" % (want, names))
    if "tools_include" in expect:
        for name in expect["tools_include"]:
            if name not in names:
                failures.append("tools/list: tool %r not offered (have %s)" % (name, names))
    return failures


def check_tools_call(expect, response):
    """Assert a tools/call response against the expectation. Returns failures.
    An error_code or error_contains expectation requires a JSON-RPC error; the
    result_* and is_error expectations require a result."""
    failures = []
    wants_error = "error_code" in expect or "error_contains" in expect
    if wants_error:
        if "error" not in response:
            failures.append("tools/call: expected a JSON-RPC error, got a result")
            return failures
        err = response["error"] if isinstance(response["error"], dict) else {}
        if "error_code" in expect and err.get("code") != expect["error_code"]:
            failures.append("tools/call error code: expected %r, got %r"
                            % (expect["error_code"], err.get("code")))
        if "error_contains" in expect and expect["error_contains"] not in str(err.get("message", "")):
            failures.append("tools/call error message: %r not in %r"
                            % (expect["error_contains"], err.get("message")))
        return failures
    if "error" in response:
        err = response["error"] if isinstance(response["error"], dict) else {}
        failures.append("tools/call: expected a result, got JSON-RPC error %r: %s"
                        % (err.get("code"), err.get("message")))
        return failures
    result = response.get("result") or {}
    text = _content_text(result)
    if "result_text" in expect and text != expect["result_text"]:
        failures.append("tools/call result_text: expected %r, got %r" % (expect["result_text"], text))
    if "result_contains" in expect and expect["result_contains"] not in text:
        failures.append("tools/call result_contains: %r not in %r" % (expect["result_contains"], text))
    if "is_error" in expect and bool(result.get("isError", False)) != bool(expect["is_error"]):
        failures.append("tools/call is_error: expected %r, got %r"
                        % (bool(expect["is_error"]), bool(result.get("isError", False))))
    return failures


_ASSERTION_KEYS = {
    "tools/list": ("tools", "tools_include"),
    "tools/call": ("result_text", "result_contains", "is_error", "error_code", "error_contains"),
}


def run_interaction(interaction, send, next_id):
    """Drive one interaction and grade it. Returns a per-interaction result dict."""
    name = interaction.get("name") or interaction.get("method") or "<interaction>"
    method = interaction.get("method")
    expect = interaction.get("expect") or {}
    if method not in ("tools/list", "tools/call"):
        return {"name": name, "passed": False,
                "failures": ["unknown interaction method %r (expected tools/list or tools/call)" % method]}
    if not expect:
        return {"name": name, "passed": False,
                "failures": ["interaction asserts nothing: no 'expect' block"]}
    # No rubber-stamping: an expect block that names no recognized assertion for
    # this method observes nothing and cannot pass. A typo (result_txt) or a
    # wrong-method key (error_code on tools/list) is a named journey error, not a
    # silent green.
    recognized = _ASSERTION_KEYS[method]
    if not any(k in expect for k in recognized):
        return {"name": name, "passed": False,
                "failures": ["interaction asserts nothing: expect block for %s has no recognized "
                             "assertion key (want one of %s), got %s"
                             % (method, list(recognized), sorted(expect))]}
    rid = next_id()
    request = {"jsonrpc": "2.0", "id": rid, "method": method}
    if "params" in interaction:
        request["params"] = interaction["params"]
    try:
        response = send(request)
    except TransportError as e:
        return {"name": name, "passed": False, "failures": ["transport/framing error: %s" % e]}
    failures = validate_envelope(response, rid)
    if not failures:
        if method == "tools/list":
            failures += check_tools_list(expect, response.get("result") or {})
        else:
            failures += check_tools_call(expect, response)
    return {"name": name, "passed": not failures, "failures": failures, "response": response}


def run(fixture, send):
    """Perform the MCP initialize handshake, then drive every interaction over the
    send seam. Returns {"passed", "interactions", "failures", "error"}. passed is
    False on a failed handshake, a failed interaction, a transport or framing
    error, or an asserts-nothing fixture."""
    result = {"name": None, "passed": True, "interactions": [], "failures": [], "error": None}

    if isinstance(fixture, list):
        interactions = fixture
    elif isinstance(fixture, dict):
        result["name"] = fixture.get("name")
        interactions = fixture.get("interactions")
    else:
        result["passed"] = False
        result["error"] = "fixture must be a JSON list of interactions or an object with 'interactions'"
        result["failures"].append(result["error"])
        return result

    if not isinstance(interactions, list) or not interactions:
        result["passed"] = False
        result["error"] = "fixture asserts nothing: no interactions"
        result["failures"].append(result["error"])
        return result

    counter = [0]

    def next_id():
        counter[0] += 1
        return counter[0]

    init_id = next_id()
    init_request = {"jsonrpc": "2.0", "id": init_id, "method": "initialize",
                    "params": {"protocolVersion": PROTOCOL_VERSION,
                               "capabilities": {}, "clientInfo": CLIENT_INFO}}
    try:
        init_response = send(init_request)
    except TransportError as e:
        result["passed"] = False
        result["error"] = "initialize transport/framing error: %s" % e
        result["failures"].append(result["error"])
        return result
    init_failures = validate_envelope(init_response, init_id)
    if init_failures or "result" not in init_response:
        result["passed"] = False
        detail = init_failures or ["server returned an error to initialize"]
        result["error"] = "initialize handshake failed: %s" % "; ".join(detail)
        result["failures"].append(result["error"])
        return result

    for interaction in interactions:
        r = run_interaction(interaction, send, next_id)
        result["interactions"].append(r)
        if not r["passed"]:
            result["passed"] = False
            for f in r["failures"]:
                result["failures"].append("%s: %s" % (r["name"], f))
    return result


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    fixture_path = Path(argv[1])
    try:
        fixture = json.loads(fixture_path.read_text())
    except Exception as e:
        print("cannot read fixture %s: %s" % (fixture_path, e))
        return 2
    command = argv[2:] if len(argv) > 2 else [sys.executable,
                                              str(Path(__file__).parent / "fixtures" / "fake_mcp_server.py")]
    transport = StdioTransport(command)
    try:
        result = run(fixture, transport.send)
    finally:
        transport.close()

    for it in result["interactions"]:
        print(("PASS  " if it["passed"] else "FAIL  ") + it["name"])
        for f in it["failures"]:
            print("      - %s" % f)
    if result["error"] and not result["interactions"]:
        print("ERROR: %s" % result["error"])
    total = len(result["interactions"])
    passed = sum(1 for it in result["interactions"] if it["passed"])
    print("mcp runner: %d/%d interactions passed" % (passed, total))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
