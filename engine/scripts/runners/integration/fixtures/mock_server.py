#!/usr/bin/env python3
"""A tiny stdlib HTTP server with one conforming and one violating resource.

It gives the integration runner's fixtures a real sandbox endpoint with zero
external dependencies. One resource returns a payload that conforms to the
contract; another returns a payload that deliberately breaks it (a wrong-typed
field, a missing required field, and a forbidden internal field present), so
the failing fixture has a real contract violation to catch. It is a test
double, not a product: a consuming repo points the runner at its own sandbox
instead.

  mock_server.py [port]      # serve on 127.0.0.1:<port> (default 8080; 0 = ephemeral)

Routes (both return 200 with a fixed payload, so the outcome is deterministic):
  GET /order/1        conforming record - id (string), amount (number),
                      currency (string), status (string), items (array),
                      customer (object with id and email strings)
  GET /order/broken   deliberately violating - amount is a STRING ("42.50"),
                      currency is MISSING, and a forbidden "internal_debug"
                      field is present
  anything else       404 {"error":"not found","path":...}
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CONFORMING = {
    "id": "ord-1",
    "amount": 42.5,
    "currency": "USD",
    "status": "paid",
    "items": [{"sku": "sku-1", "qty": 2}],
    "customer": {"id": "cust-1", "email": "buyer@example.test"},
}

# BROKEN (on purpose): amount arrives as a string, currency is dropped, and an
# internal debugging field leaks into the payload. These are the drifts the
# failing fixture catches - each invisible to a happy-path 200 check.
BROKEN = {
    "id": "ord-2",
    "amount": "42.50",
    "status": "paid",
    "items": [{"sku": "sku-9", "qty": 1}],
    "customer": {"id": "cust-9", "email": "other@example.test"},
    "internal_debug": {"trace": "abc-123"},
}

ORDERS = {"1": CONFORMING, "broken": BROKEN}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path
        if path.startswith("/order/"):
            oid = path[len("/order/"):]
            order = ORDERS.get(oid)
            if order is None:
                return self._send(404, {"error": "not found", "id": oid})
            return self._send(200, order)
        self._send(404, {"error": "not found", "path": path})

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
