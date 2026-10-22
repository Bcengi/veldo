"""The socketpair transport inprocess_harness.py substitutes for the authority service's AF_UNIX socket.

start() loads the installed control_service.py from the installation's bin/ (the fixed executable install()
laid down), replaces only its CC.bind with a listener whose connections are socketpairs and its signal module
with one that records the handlers serve() installs, and runs serve() in a thread. send() is control_client.send
with the same routing (resolve_store, read_binding, build_request) and the connection made through that
listener. The kernel still reports the peer (SO_PEERCRED on a socketpair), so Authority.judge is unchanged.
"""
import importlib.util
import json
import os
import socket
import threading
import time

LISTENERS = {}


class Listener:
    def __init__(self, address):
        self.address = address
        self.r, self.w = socket.socketpair()
        self.queue = []
        self.lock = threading.Lock()
        open(address, 'w').close()

    def connect(self):
        a, b = socket.socketpair()
        with self.lock:
            self.queue.append(b)
        self.w.send(b'x')
        return a

    def accept(self):
        self.r.recv(1)
        with self.lock:
            return self.queue.pop(0), None

    def fileno(self):
        return self.r.fileno()

    def settimeout(self, seconds):
        pass

    def close(self):
        pass


class Proc:
    def __init__(self, thread, handlers):
        self.thread, self.handlers, self.pid = thread, handlers, os.getpid()

    def poll(self):
        return None if self.thread.is_alive() else 0

    def send_signal(self, number):
        self.handlers[number](number, None)

    def wait(self, timeout=None):
        self.thread.join(timeout)

    def kill(self):
        self.send_signal(15)


def start(executable, config_path, address):
    spec = importlib.util.spec_from_file_location('inprocess_service_%d' % time.monotonic_ns(), executable)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    handlers = {}
    module.signal = type('Signals', (), {'SIGTERM': 15, 'SIGINT': 2,
                                         'signal': staticmethod(lambda n, f: handlers.__setitem__(n, f))})

    def bind(where):
        LISTENERS[where] = Listener(where)
        return LISTENERS[where]
    module.CC.bind = bind
    errors = []

    def run():
        try:
            module.serve(config_path)
        except BaseException as error:
            errors.append(error)
            raise
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 30
    while address not in LISTENERS or 15 not in handlers:
        if errors or time.monotonic() > deadline:
            raise RuntimeError('the service did not start: %r' % errors)
        time.sleep(0.02)
    return Proc(thread, handlers)


def send(CC, workspace, command, enrollment, verify, sign, host, timeout=20):
    enrollment.resolve_store(workspace, verify, host)
    binding = enrollment.read_binding(workspace)
    conn = LISTENERS[CC.socket_path_for(binding)].connect()
    conn.sendall(json.dumps(CC.build_request(workspace, binding, command, sign)).encode())
    conn.shutdown(socket.SHUT_WR)
    chunks = []
    conn.settimeout(timeout)
    while True:
        chunk = conn.recv(65536)
        if not chunk:
            break
        chunks.append(chunk)
    return json.loads(b''.join(chunks))
