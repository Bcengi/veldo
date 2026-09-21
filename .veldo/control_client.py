#!/usr/bin/env python3
"""Local clients reach the authority over authenticated IPC (PLAN-0019 W84, VELDO-0107, R20, R53).

WHAT THIS MODULE IS. The one way a process in an enrolled workspace reaches that workspace's
authority, and the authority's side of the same conversation. A request carries the workspace it
means; the serving side resolves THAT coordinate through the enrollment binding and refuses a
coordinate it does not serve. Local transport is an AF_UNIX socket. The peer is authenticated by the
kernel's own answer about who is on the other end, not by anything the peer says about itself.

THE TWO CHECKS ARE INDEPENDENT AND BOTH ARE REQUIRED.

  The TRANSPORT check asks who is connected: SO_PEERCRED, which the kernel fills in, so a client
  cannot claim a uid it does not have. Same account by design (this is the simple boundary, not a
  second OS identity), so the rule is that the peer's uid is the authority's own.

  The COMMAND check asks who authored the request and whether it is intact: the command's own
  signature, verified through a callable the caller supplies, so this module never holds key
  material. A signature that does not verify is refused even from a peer the kernel vouches for.

Collapsing the two is the mistake this module exists to refuse. A peer the kernel vouches for is a
process on this machine, not an author; a valid signature carried by an unauthenticated peer is a
replay someone picked up. Neither substitutes for the other, and the refusals are different names so
a reader can tell which one fired.

WHERE THE SOCKET IS. Derived from the binding's store path, so the address follows the record rather
than the environment. There is nothing to point at another authority: this module reads no
environment variable at all, and the workspace is a required argument exactly as it is in
control_enrollment.

WHAT IT IS NOT. No network listener, no framework, no threads, no daemon supervision. The remote
transport is a command relay to this same endpoint (VELDO-0108) and is not a second code path. What
happens when the authority is unreachable is VELDO-0109; this module reports it and does nothing
else about it. Standard library only.
"""
import json
import os
import socket
import struct
import sys

REQUEST_SCHEMA = "veldo.control_request/v1"
RESPONSE_SCHEMA = "veldo.control_response/v1"
SOCKET_NAME = "authority.sock"
REQUEST_FIELDS = ("schema", "workspace", "domain_uuid", "store_uuid", "command", "signature")
MAX_REQUEST_BYTES = 1 << 20

REFUSALS = ("malformed_request", "peer_not_authorized", "command_signature_invalid",
            "coordinate_not_served", "unenrolled_workspace", "authority_unreachable",
            "peer_identity_unavailable")


class RoutingRefused(Exception):
    """Refused, with a reason from REFUSALS and the coordinates it judged."""

    def __init__(self, reason, message, coordinates=None):
        super().__init__("%s: %s" % (reason, message))
        assert reason in REFUSALS, reason
        self.reason = reason
        self.message = message
        self.coordinates = dict(coordinates or {})


# ---------------------------------------------------------------------------------------------
# The address, which follows the binding
# ---------------------------------------------------------------------------------------------

def socket_path_for(binding):
    """Beside the store the binding names. The address is a consequence of the record, so there is
    no second place to look and nothing in the environment to point somewhere else."""
    return os.path.join(os.path.dirname(binding["store_path"]), SOCKET_NAME)


def peer_uid(conn):
    """WHO IS ON THE OTHER END, according to the kernel.

    SO_PEERCRED is filled in by the kernel from the connecting process, so unlike anything in the
    request it cannot be claimed. Returns None where the platform does not answer, and None is NOT
    "allowed": the caller refuses, because an unauthenticated peer must not become an authenticated
    one by the check being unavailable."""
    try:
        raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    except (OSError, AttributeError):
        return None
    _pid, uid, _gid = struct.unpack("3i", raw)
    return uid


# ---------------------------------------------------------------------------------------------
# The request
# ---------------------------------------------------------------------------------------------

def request_problems(request):
    if not isinstance(request, dict):
        return ["the request is not a mapping"]
    problems = []
    if request.get("schema") != REQUEST_SCHEMA:
        problems.append("schema must be %s (got %r)" % (REQUEST_SCHEMA, request.get("schema")))
    for field in REQUEST_FIELDS:
        if field == "schema":
            continue
        if not request.get(field):
            problems.append("missing or empty required field: %s" % field)
    if "command" in request and not isinstance(request.get("command"), dict):
        problems.append("command must be a mapping")
    return problems


def signed_bytes(request):
    """The bytes the command's signature covers: the command AND the coordinates it names.

    The coordinates are inside the signature on purpose. If only the command were signed, a valid
    command could be re-addressed to another workspace in flight and still verify, which is the
    wrong-repository write this whole package exists to stop, arriving with a good signature on it."""
    return json.dumps({k: request.get(k) for k in ("workspace", "domain_uuid", "store_uuid", "command")},
                      sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def build_request(workspace, binding, command, sign):
    """A request that names the workspace it means, signed over the command and those coordinates."""
    req = {
        "schema": REQUEST_SCHEMA,
        "workspace": os.path.realpath(os.path.abspath(str(workspace))),
        "domain_uuid": binding["domain_uuid"],
        "store_uuid": binding["store_uuid"],
        "command": command,
    }
    req["signature"] = sign(signed_bytes(req))
    return req


# ---------------------------------------------------------------------------------------------
# The client
# ---------------------------------------------------------------------------------------------

def send(workspace, command, enrollment, verify, sign, host_identity, timeout=30.0):
    """Send one command to the authority of THIS workspace and return its response.

    `workspace` is required and is the only coordinate. The binding is read from it, the address is
    derived from the binding, and the request carries the coordinate so the serving side judges the
    same one rather than inferring another."""
    try:
        store = enrollment.resolve_store(workspace, verify, host_identity)
    except enrollment.EnrollmentRefused as e:
        raise RoutingRefused("unenrolled_workspace",
                             "%s does not route anywhere: %s" % (workspace, e.message),
                             {"workspace": str(workspace), "enrollment_reason": e.reason})
    binding = enrollment.read_binding(workspace)
    address = socket_path_for(binding)
    payload = json.dumps(build_request(workspace, binding, command, sign)).encode("utf-8")
    conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    conn.settimeout(timeout)
    try:
        try:
            conn.connect(address)
        except OSError as e:
            raise RoutingRefused("authority_unreachable",
                                 "the authority for store %s is not answering at %s: %s"
                                 % (binding["store_uuid"], address, e),
                                 {"workspace": str(workspace), "address": address, "store": store})
        conn.sendall(payload)
        conn.shutdown(socket.SHUT_WR)
        chunks, total = [], 0
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_REQUEST_BYTES:
                raise RoutingRefused("malformed_request", "the response exceeded %d bytes"
                                     % MAX_REQUEST_BYTES, {"address": address})
            chunks.append(chunk)
    finally:
        conn.close()
    try:
        return json.loads(b"".join(chunks).decode("utf-8"))
    except ValueError as e:
        raise RoutingRefused("malformed_request", "the authority's response is not JSON: %s" % e,
                             {"address": address})


# ---------------------------------------------------------------------------------------------
# The authority's side
# ---------------------------------------------------------------------------------------------

class Authority:
    """Serves ONE store. Every request is judged against the store this instance serves."""

    def __init__(self, store_uuid, domain_uuid, store_path, enrollment, verify, host_identity, apply):
        self.store_uuid = store_uuid
        self.domain_uuid = domain_uuid
        self.store_path = os.path.realpath(os.path.abspath(store_path))
        self.enrollment = enrollment
        self.verify = verify
        self.host_identity = host_identity
        self.apply = apply

    def judge(self, request, uid):
        """The whole rule, as a response mapping. Both checks, in order, each named separately.

        The order matters for what a caller learns, not for what is allowed: every check must pass
        and none of them is skipped because another did."""
        # 1. WHO IS CONNECTED. The kernel's answer, and its absence is a refusal rather than a pass.
        if uid is None:
            return self._no("peer_identity_unavailable",
                            "this platform does not report the connecting process's identity, so "
                            "the peer cannot be authenticated and the request is refused")
        if uid != os.getuid():
            return self._no("peer_not_authorized",
                            "the connecting process runs as uid %d and this authority as uid %d"
                            % (uid, os.getuid()))
        # 2. IS IT A REQUEST AT ALL.
        problems = request_problems(request)
        if problems:
            return self._no("malformed_request", "; ".join(problems))
        # 3. WHO AUTHORED IT, and is it intact. Independent of the peer check above: a signature
        #    from a peer the kernel vouches for is still checked, and a good signature from a peer
        #    it does not vouch for has already been refused.
        if not self.verify(signed_bytes(request), request["signature"]):
            return self._no("command_signature_invalid",
                            "the command's signature does not verify over the command and the "
                            "coordinates it names")
        # 4. IS THIS COORDINATE MINE. Resolved from THE REQUEST's workspace, never from this
        #    process's own location: a serving process has its own current directory and its own
        #    module path, and neither of them is the caller's.
        try:
            store = self.enrollment.resolve_store(request["workspace"], self.verify,
                                                  self.host_identity)
        except self.enrollment.EnrollmentRefused as e:
            return self._no("unenrolled_workspace",
                            "%s does not route anywhere: %s" % (request["workspace"], e.message))
        if (store != self.store_path or request["store_uuid"] != self.store_uuid
                or request["domain_uuid"] != self.domain_uuid):
            return self._no("coordinate_not_served",
                            "this authority serves store %s at %s; the request names store %s "
                            "resolving to %s" % (self.store_uuid, self.store_path,
                                                 request["store_uuid"], store))
        return {"schema": RESPONSE_SCHEMA, "accepted": True,
                "store_uuid": self.store_uuid, "store_path": self.store_path,
                "result": self.apply(request["command"])}

    def _no(self, reason, message):
        assert reason in REFUSALS, reason
        return {"schema": RESPONSE_SCHEMA, "accepted": False, "reason": reason, "message": message,
                "store_uuid": self.store_uuid}


def bind(address):
    """A listening socket only this account can reach: the directory 0700 and the socket 0600.

    The mode is belt beside the SO_PEERCRED braces. It is not a substitute for it: a mode says who
    may open the file and SO_PEERCRED says who actually did."""
    os.makedirs(os.path.dirname(address), exist_ok=True)
    os.chmod(os.path.dirname(address), 0o700)
    if os.path.exists(address):
        os.unlink(address)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(address)
    os.chmod(address, 0o600)
    srv.listen(16)
    return srv


def serve_one(srv, authority):
    """Accept one connection, judge it, answer it, close it. One request per connection."""
    conn, _ = srv.accept()
    try:
        uid = peer_uid(conn)
        chunks, total = [], 0
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_REQUEST_BYTES:
                chunks = None
                break
            chunks.append(chunk)
        if chunks is None:
            response = authority._no("malformed_request",
                                     "the request exceeded %d bytes" % MAX_REQUEST_BYTES)
        else:
            try:
                request = json.loads(b"".join(chunks).decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as e:
                response = authority._no("malformed_request", "the request is not JSON: %s" % e)
            else:
                response = authority.judge(request, uid)
        conn.sendall(json.dumps(response).encode("utf-8"))
    finally:
        conn.close()
    return response


def serve_forever(srv, authority, until=None):
    """Serve until `until()` says stop. A blocked accept() is not a stop, so the caller sets a
    timeout on the socket and a timeout here is a lap of the loop rather than an error."""
    while until is None or not until():
        try:
            serve_one(srv, authority)
        except socket.timeout:
            continue
        except OSError:
            if until is not None and until():
                return
            raise


def main(argv):
    print(__doc__)
    return 64


if __name__ == "__main__":
    sys.exit(main(sys.argv))
