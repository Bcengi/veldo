"""Exercise the supervisor's announced deadline with a held real receive hook.

Only the supervisor clock is supplied. The executor, authentication, transport and
destination checks still run normally. At the hook's arrival the clock advances
past acceptance; a supervisor that kept that deadline gets a select timeout.
"""
import os
from pathlib import Path
import select
import shlex
import contextlib
from types import SimpleNamespace
from unittest.mock import patch


WAIT_HANG_SECONDS = 600


class ReceiveWindow:
    def __init__(self, directory, executor):
        self.executor = executor
        self.at = 0.0
        self.crossed = False
        self.windows = []
        self.budget_path = Path(directory) / 'receive-budget'
        self.arrived_path = Path(directory) / 'receive-arrived'
        self.release_path = Path(directory) / 'receive-release'
        for path in (self.arrived_path, self.release_path):
            os.mkfifo(path)
        self.arrived = os.open(self.arrived_path, os.O_RDWR | os.O_NONBLOCK)
        self.release = os.open(self.release_path, os.O_RDWR | os.O_NONBLOCK)

    def hook(self):
        return ('#!/bin/sh\ncat >/dev/null\nprintf ready > %s\nread -r go < %s\n'
                % (shlex.quote(str(self.arrived_path)), shlex.quote(str(self.release_path))))

    def clock(self):
        return self.at

    @property
    def budget(self):
        return float(self.budget_path.read_text()) if self.budget_path.exists() else 0

    @contextlib.contextmanager
    def supervisor_clock(self, namespace, alias):
        # The suite's existing duration observation reads the same supplied clock
        # as call(). Restore its ordinary clock before any other row runs.
        with self, patch.dict(namespace, {alias: SimpleNamespace(monotonic=self.clock)}):
            yield self

    def select(self, readers, writers, errors, timeout):
        self.windows.append(timeout)
        while True:
            watched = list(readers) + ([] if self.crossed else [self.arrived])
            ready, writable, exceptional = select.select(watched, writers, errors, WAIT_HANG_SECONDS)
            if not (ready or writable or exceptional):
                raise TimeoutError('effect receive handshake hung')
            # Consume an announcement already on stdout before advancing at the hook.
            ordinary = [fd for fd in ready if fd != self.arrived]
            if ordinary or writable or exceptional:
                return ordinary, writable, exceptional
            os.read(self.arrived, 65536)
            self.crossed = True
            self.at += 3
            os.write(self.release, b'go\n')
            if timeout <= 3:
                return [], [], []

    def __enter__(self):
        # Observe the timeout actually handed to the real Git runner. The old
        # sleeping hook also rejected a shortened step budget; keep that tooth
        # without making the kernel spend the budget on a busy host.
        self.module_path = Path(self.executor.__file__)
        self.original_source = self.module_path.read_bytes()
        entry = b"if __name__ == '__main__':\n    main()"
        assert self.original_source.count(entry) == 1, 'executor entry moved'
        probe = ("if __name__ == '__main__':\n"
                 "    _receive_run = _git_process.run\n"
                 "    def _receive_budget(argv, **kwargs):\n"
                 "        if 'push' in argv:\n"
                 "            Path(%r).write_text(str(kwargs.get('timeout')))\n"
                 "        return _receive_run(argv, **kwargs)\n"
                 "    _git_process.run = _receive_budget\n"
                 "    main()" % str(self.budget_path)).encode()
        self.module_path.write_bytes(self.original_source.replace(entry, probe))
        self.original_time, self.original_select = self.executor.time, self.executor.select
        self.executor.time = SimpleNamespace(monotonic=self.clock)
        self.executor.select = SimpleNamespace(select=self.select)
        return self

    def __exit__(self, *_):
        self.executor.time, self.executor.select = self.original_time, self.original_select
        self.module_path.write_bytes(self.original_source)
        os.close(self.arrived)
        os.close(self.release)
