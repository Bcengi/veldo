#!/usr/bin/env python3
"""A minimal in-memory / stdio fake MCP (Model Context Protocol) server.

It gives the MCP runner's fixtures a real MCP server to drive with zero external
dependencies. It speaks JSON-RPC 2.0 and exposes three trivial tools: echo, add,
and relay (a PROXY tool the server fulfills by delegating to echo), so the runner
can be driven end to end, including a proxied tool call, with NO external MCP
server. It is a test double, not a product: a consuming repo points the runner at
its own MCP server instead.

Two ways to use it, one shared core:

  FakeMcpServer().handle(request) -> response     the pure request handler; the
      selftest drives the runner's control logic through this in-memory seam with
      no subprocess, so the gate needs no live server or container.

  fake_mcp_server.py                               a stdio loop over that handler:
      read newline-delimited JSON-RPC 2.0 messages (one JSON object per line, no
      embedded newlines, the MCP stdio framing) from stdin and write each response
      as one line to stdout. This is what the runner spawns by default and what an
      adopting repo would replace with its real MCP server command.

Protocol modeled (a faithful, small subset of MCP over JSON-RPC 2.0):
  initialize       returns protocolVersion, capabilities, serverInfo; marks the
                   session initialized. tools/* before initialize is an error
                   (code -32002), so the ordering the real protocol requires is
                   modeled and testable.
  tools/list       returns {"tools": [...]} listing add, echo, and relay.
  tools/call       params {"name", "arguments"}; returns a tool RESULT
                   ({"content": [{"type":"text","text":...}], "isError": bool}).
                   echo returns its text argument. add returns the sum of a and b
                   when both are numbers; given a non-number it returns a
                   tool-level error result (isError true), the MCP way to report a
                   tool that ran and failed (distinct from a protocol error).
                   relay is a PROXY tool: it does no work of its own and instead
                   re-dispatches to the echo tool through the same handler, so its
                   result is exactly echo's result. It models a server that
                   fulfills a tool by delegating to another (a proxy or gateway),
                   so the runner can assert the proxied result end to end.

Error channels, both exercised so neither is a silent pass:
  -32601 method not found   an unknown JSON-RPC method
  -32602 invalid params     tools/call with no name, or an unknown tool name
  -32002 not initialized    tools/* before initialize
  -32700 parse error        a line that is not valid JSON (stdio loop only)
A notification (a request with no id) is handled and gets no response.
"""
import json
import sys

PROTOCOL_VERSION = "2025-06-18"

TOOLS = [
    {
        "name": "add",
        "description": "Add two numbers a and b and return their sum.",
        "inputSchema": {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    },
    {
        "name": "echo",
        "description": "Return the text argument unchanged.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "relay",
        "description": "Proxy the text argument to the echo tool and return its result.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
]


def _is_number(x):
    """A JSON number that is not a bool (a bool is not a number here)."""
    return isinstance(x, (int, float)) and not isinstance(x, bool)


class FakeMcpServer:
    """The MCP request handler as a pure object: handle(request) -> response (or
    None for a notification). No I/O, so the runner's control logic is driven
    against it in the gate with no subprocess, network, or container."""

    def __init__(self):
        self.initialized = False

    def _ok(self, rid, result):
        return {"jsonrpc": "2.0", "id": rid, "result": result}

    def _err(self, rid, code, message):
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}

    def handle(self, request):
        if not isinstance(request, dict):
            return {"jsonrpc": "2.0", "id": None,
                    "error": {"code": -32600, "message": "invalid request: not a JSON object"}}
        rid = request.get("id")
        method = request.get("method")
        is_notification = "id" not in request
        if request.get("jsonrpc") != "2.0":
            if is_notification:
                return None
            return self._err(rid, -32600, "invalid request: jsonrpc must be '2.0'")
        if is_notification:
            # Notifications (initialized, cancelled, ...) get no response.
            return None
        if method == "initialize":
            self.initialized = True
            return self._ok(rid, {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "veldo-fake-mcp", "version": "1.0.0"},
            })
        if not self.initialized:
            return self._err(rid, -32002, "server not initialized: send initialize first")
        if method == "tools/list":
            return self._ok(rid, {"tools": TOOLS})
        if method == "tools/call":
            return self._call_tool(rid, request.get("params"))
        return self._err(rid, -32601, "method not found: %r" % method)

    def _call_tool(self, rid, params):
        if not isinstance(params, dict) or "name" not in params:
            return self._err(rid, -32602, "invalid params: 'name' is required")
        name = params.get("name")
        args = params.get("arguments") or {}
        if not isinstance(args, dict):
            return self._err(rid, -32602, "invalid params: 'arguments' must be an object")
        if name == "echo":
            if "text" not in args:
                return self._err(rid, -32602, "invalid params: echo requires 'text'")
            return self._ok(rid, {"content": [{"type": "text", "text": str(args["text"])}],
                                  "isError": False})
        if name == "add":
            a, b = args.get("a"), args.get("b")
            if _is_number(a) and _is_number(b):
                return self._ok(rid, {"content": [{"type": "text", "text": str(a + b)}],
                                      "isError": False})
            # A tool that ran and failed: an MCP tool-level error result, not a
            # JSON-RPC protocol error.
            return self._ok(rid, {"content": [{"type": "text", "text": "add requires two numbers"}],
                                  "isError": True})
        if name == "relay":
            if "text" not in args:
                return self._err(rid, -32602, "invalid params: relay requires 'text'")
            # Proxying: relay fulfills the call by DELEGATING to the echo tool
            # through the same handler and returns echo's result unchanged. The
            # response id stays this call's id, so from the client's view relay
            # is one tool whose work another tool performed.
            return self._call_tool(rid, {"name": "echo", "arguments": {"text": args["text"]}})
        return self._err(rid, -32602, "unknown tool: %r" % name)


def main():
    """Stdio loop: newline-delimited JSON-RPC 2.0, one message per line."""
    server = FakeMcpServer()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            sys.stdout.write(json.dumps(
                {"jsonrpc": "2.0", "id": None,
                 "error": {"code": -32700, "message": "parse error"}}) + "\n")
            sys.stdout.flush()
            continue
        response = server.handle(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
