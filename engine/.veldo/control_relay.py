#!/usr/bin/env python3
"""The SSH command relay: carry a command to the local authority, decide nothing (VELDO-0108, R20).

WHAT THIS PROGRAM IS. The thing SSH runs on the authority's machine. It reads one request from its
standard input, writes those bytes UNCHANGED to the local IPC endpoint, and writes the endpoint's
answer UNCHANGED to its standard output, up to 1 MiB inclusive in each direction. Exceeding
either limit exits 4 with zero stdout bytes and a diagnostic on stderr.

  ssh workstation veldo-relay        # sshd runs this, with the client's bytes on stdin

WHY IT DOES SO LITTLE ON PURPOSE. The temptation is the convenient one: the relay has already
watched SSH authenticate somebody, so let it decide. SSH says WHO IS CARRYING the command. The
command's own signature says who AUTHORED it and what it may do. Collapsing those two makes every
host with relay access an authority, which is the opposite of what a relay is for. So this program
never parses the payload, never verifies a signature, never reads the enrollment binding, and never
consults the principal SSH authenticated: it cannot make an authorisation decision because it does
not have the material to make one.

ONE ENDPOINT, NOT A ROUTER. The address is given to it once, by whoever installed it beside an
authority. A relay that chose its target from the request would be making the routing decision
VELDO-0029 exists to keep in the signed binding, at the one point in the system where the binding is
not being read.

NO LISTENER. This introduces no network service. It has no bind and no listen: sshd is the network
service, already installed, already audited, and this program is a command it runs. That property is
supported by source inspection for bind/listen calls and snapshots of fixture-local pathname Unix
sockets before invocation and after relay exit. Those snapshots show no additional socket remains;
a general listener/process census is INTENDED and NOT YET DEMONSTRATED.

WHAT IT IS NOT. Not a proxy for many authorities, not a daemon, not a session. One request, one
answer, exit. Standard library only.
"""
import os
import socket
import sys

MAX_BYTES = 1 << 20
EXIT_OK = 0
EXIT_UNREACHABLE = 3
EXIT_TOO_LARGE = 4


def read_all(stream, limit=MAX_BYTES):
    """Everything on the input, up to a limit. Over the limit is an error, never a truncation: a
    request cut in half would reach the authority as a malformed one and be reported as the client's
    mistake instead of the relay's."""
    chunks, total = [], 0
    while True:
        chunk = stream.read(65536)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise ValueError("the request exceeded %d bytes" % limit)
        chunks.append(chunk)
    return b"".join(chunks)


def forward(address, payload, timeout=30.0):
    """The request's bytes to the endpoint, and the endpoint's bytes back. Nothing is parsed."""
    conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    conn.settimeout(timeout)
    try:
        conn.connect(address)
        conn.sendall(payload)
        conn.shutdown(socket.SHUT_WR)
        chunks, total = [], 0
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_BYTES:
                raise ValueError("the response exceeded %d bytes" % MAX_BYTES)
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        conn.close()


def main(argv, stdin=None, stdout=None, stderr=None):
    """Usage: control_relay.py <endpoint-socket-path>

    The endpoint is an ARGUMENT, not something read from the request or from the environment, so the
    relay cannot be pointed at another authority by the person whose command it is carrying."""
    stdin = stdin if stdin is not None else sys.stdin.buffer
    stdout = stdout if stdout is not None else sys.stdout.buffer
    stderr = stderr if stderr is not None else sys.stderr
    if len(argv) != 2:
        print("usage: control_relay.py <endpoint-socket-path>", file=stderr)
        return 64
    address = argv[1]
    try:
        payload = read_all(stdin)
    except ValueError as e:
        print("relay: %s" % e, file=stderr)
        return EXIT_TOO_LARGE
    try:
        answer = forward(address, payload)
    except OSError as e:
        # The authority is not answering. The relay says so and says nothing else: what a client does
        # about an unreachable authority is VELDO-0109, and inventing an answer here would be the
        # local fallback that item exists to forbid.
        print("relay: the authority at %s is not answering: %s" % (address, e), file=stderr)
        return EXIT_UNREACHABLE
    except ValueError as e:
        print("relay: %s" % e, file=stderr)
        return EXIT_TOO_LARGE
    stdout.write(answer)
    stdout.flush()
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv))
