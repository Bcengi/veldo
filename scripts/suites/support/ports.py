"""The port holder (VELDO-0358, C11), lifted from engine/ui/e2e/harness.py's reserve_port.

A port chosen for a server that binds it later is kept bound until the server has bound it. Reading a
free port and releasing it at once (bind to 0, read, close) leaves it free for the whole start, and under
a loaded gate another bind to port 0 can take it, so the server's bind fails with EADDRINUSE. The
reservation stays bound, not listening, with SO_REUSEADDR, as http.server's own bind sets it: the kernel
never hands a bound port to a bind to port 0, and the server's bind to it succeeds because neither socket
listens yet. Release it once the server is up (its ready line, or its listener seen).

    hold = reserve()
    start_server(port=hold.port)
    ...the server's ready event...
    hold.release()
"""
import socket


class PortHold:
    def __init__(self, host='127.0.0.1'):
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, 0))
        self.host = host
        self.port = self.sock.getsockname()[1]

    def release(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.release()


def reserve(host='127.0.0.1'):
    return PortHold(host)
