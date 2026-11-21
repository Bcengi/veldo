"""Linux fixture file transport: wait for publication events, with a hang detector."""
import ctypes
import os
import select


class FileEvents:
    def __init__(self, directory):
        libc = ctypes.CDLL(None, use_errno=True)
        self.fd = libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
        if self.fd < 0:
            raise OSError(ctypes.get_errno(), 'inotify_init1')
        # A published rename or a closed write; reads do not wake the observer.
        if libc.inotify_add_watch(self.fd, os.fsencode(directory), 0x80 | 0x8 | 0x100) < 0:
            self.close()
            raise OSError(ctypes.get_errno(), 'inotify_add_watch')

    def wait(self, extra=()):
        ready = select.select([self.fd, *extra], [], [], 120)[0]
        if not ready:
            raise TimeoutError('fixture publication hang detector')
        if self.fd in ready:
            while True:
                try:
                    os.read(self.fd, 65536)
                except BlockingIOError:
                    break
        return ready

    def close(self):
        os.close(self.fd)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
