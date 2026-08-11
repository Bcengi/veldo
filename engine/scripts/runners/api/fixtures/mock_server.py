#!/usr/bin/env python3
"""A tiny stdlib HTTP server that returns known JSON.

It gives the API runner's fixtures a real endpoint to assert against with zero
external dependencies. The passing and failing fixtures are written against
exactly the responses defined here, and both the runner's unit self-test
(scripts/selftest.py) and test_api_runner.sh drive the runner against this
server. It is a test double, not a product: a consuming repo points the runner
at its own service instead.

  mock_server.py [port]      # serve on 127.0.0.1:<port> (default 8080; 0 = ephemeral)

Routes:
  GET  /health   200  {"status":"ok","version":"1.0.0","data":{...}}
  POST /echo     200  {"method":"POST","received":<parsed request body>}
  anything else  404  {"error":"not found","path":...}
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HEALTH = {
    "status": "ok",
    "version": "1.0.0",
    "data": {
        "count": 2,
        "items": [
            {"id": 1, "name": "alpha"},
            {"id": 2, "name": "beta"},
        ],
    },
}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, HEALTH)
        else:
            self._send(404, {"error": "not found", "path": self.path})

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8") if length else ""
        try:
            received = json.loads(raw) if raw else None
        except ValueError:
            received = raw
        if self.path == "/echo":
            self._send(200, {"method": "POST", "received": received})
        else:
            self._send(404, {"error": "not found", "path": self.path})

    def log_message(self, *args):
        pass  # keep the self-test output clean


def serve(port=8080):
    """Return a started-ready ThreadingHTTPServer bound to 127.0.0.1:<port>.
    Pass 0 for an OS-assigned ephemeral port (read it from server_address)."""
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    httpd = serve(port)
    print(f"mock server on http://127.0.0.1:{httpd.server_address[1]}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    main()
