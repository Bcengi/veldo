"""Wait for the service's own Type=notify readiness, never its socket pathname."""
import socket
import os
import threading
import tempfile
from pathlib import Path

WAIT_HANG_SECONDS = 600


class ServiceReady:
    def __init__(self, waits):
        self.waits = waits
        self.directory = tempfile.TemporaryDirectory(prefix='vnr-')
        self.address = str(Path(self.directory.name) / 'n')
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        # A private directory held through service exit, with no release/rebind
        # window. Pathname sockets work in the gate's confined socket broker too.
        self.listener.bind(self.address)
        self.read_fd, self.write_fd = os.pipe()
        self.thread = threading.Thread(target=self.drain, name='service-notify', daemon=True)
        self.thread.start()

    def drain(self):
        announced = False
        while True:
            message = self.listener.recv(65536)
            if not message:
                return
            if not announced and b'READY=1' in message.splitlines():
                os.write(self.write_fd, b'ready')
                announced = True
            # Keep draining STATUS and STOPPING until the service has exited.

    def wait(self, process):
        ready = self.waits.Readable(self.read_fd)
        return self.waits.wait('service READY=1', lambda: ready.data == b'ready',
                               terminal=lambda: process.poll() is not None,
                               sources=[ready, self.waits.Pidfd(process)]).done

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as wake:
            wake.sendto(b'', self.listener.getsockname())
        self.thread.join(timeout=WAIT_HANG_SECONDS)
        if self.thread.is_alive():
            raise TimeoutError('service notification drain hung')
        self.listener.close()
        os.close(self.read_fd)
        os.close(self.write_fd)
        self.directory.cleanup()
