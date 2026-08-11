#!/usr/bin/env python3
"""A tiny stdlib HTTP server with two authorization behaviors.

It gives the authorization runner's fixtures a real endpoint with zero external
dependencies. One resource enforces owner-scoping correctly; another is
deliberately vulnerable to an insecure direct object reference, so the failing
fixture has a real bypass to catch. It is a test double, not a product: a
consuming repo points the runner at its own service instead.

  mock_server.py [port]      # serve on 127.0.0.1:<port> (default 8080; 0 = ephemeral)

Identity: an "Authorization: Bearer <token>" header maps to a user
(alice-token -> alice, bob-token -> bob); any other or missing token is
anonymous.

Routes:
  GET /orders/<id>        secure owner-scoping:
                            anonymous          -> 401 {"error":"unauthorized"}
                            unknown id         -> 404 {"error":"not found"}
                            authenticated, not owner -> 403 {"error":"forbidden"}
                            owner              -> 200 <full record incl secret>
  GET /leaky/orders/<id>  deliberately vulnerable (insecure direct object
                          reference): requires a valid token but performs NO
                          owner check, so any authenticated caller receives any
                          record (anonymous -> 401; unknown id -> 404).
  anything else           404 {"error":"not found","path":...}
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKENS = {"alice-token": "alice", "bob-token": "bob"}
ORDERS = {
    "ord-1": {"id": "ord-1", "owner": "alice", "item": "widget",
              "secret": "owner-secret-9f3a"},
}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _user(self):
        auth = self.headers.get("Authorization") or ""
        if auth.startswith("Bearer "):
            return TOKENS.get(auth[len("Bearer "):].strip())
        return None

    def do_GET(self):
        path = self.path
        if path.startswith("/orders/"):
            oid = path[len("/orders/"):]
            user = self._user()
            if user is None:
                return self._send(401, {"error": "unauthorized"})
            order = ORDERS.get(oid)
            if order is None:
                return self._send(404, {"error": "not found"})
            if order["owner"] != user:
                return self._send(403, {"error": "forbidden"})
            return self._send(200, order)
        if path.startswith("/leaky/orders/"):
            oid = path[len("/leaky/orders/"):]
            user = self._user()
            if user is None:
                return self._send(401, {"error": "unauthorized"})
            order = ORDERS.get(oid)
            if order is None:
                return self._send(404, {"error": "not found"})
            # BUG (on purpose): no owner check, so any authenticated caller
            # reads any record. This is the bypass the failing fixture catches.
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
