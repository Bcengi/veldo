"""Separate-process transport endpoint; signed authority commands, synthetic transport and macOS OS observations.

Runs production control_worker.receive. The transport uses files because the confined suite cannot create IPC sockets;
the Apple OS backend/identity are simulated. This fixture does not qualify SSH, macOS or an engine.
"""
import importlib.util
import json
from pathlib import Path
import sys
import subprocess
import time
import uuid
import traceback
import types

import checks as T

spec = importlib.util.spec_from_file_location('v125_receiver_host', T.ROOT / 'proof/VELDO-0125/macos_event_fixture.py')
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)
config = json.loads(Path(sys.argv[1]).read_text())
request = json.loads(sys.stdin.readline())
class Backend(P.FakeOS):
    def bind_dispatch(self):
        if self.directory:
            for name in ('heartbeat.json', 'result.json'):
                value = P.M.read(self.directory / name)
                if value:
                    P.M.write(self.directory / name, dict(value, dispatch_id=request['dispatch_id']))

    def sleep(self, seconds):
        super().sleep(seconds)
        self.bind_dispatch()

    def settle(self):
        super().settle()
        self.bind_dispatch()

backend = Backend(config['fixture_facts'], temp=Path(config['fixture_temp']))
worker = T.load('control_worker')
client_module = T.load('control_worker_client')
def exchange(argv, *, input, **kwargs):
    message = Path(config['fixture_exchange']) / (uuid.uuid4().hex + '.request')
    temporary = message.with_suffix('.tmp')
    temporary.write_bytes(input)
    temporary.replace(message)
    response = message.with_suffix('.response')
    until = time.monotonic() + 10
    while not response.exists() and time.monotonic() < until:
        time.sleep(.01)
    return subprocess.CompletedProcess(argv, 0, response.read_bytes(), b'')
client_module.subprocess = types.SimpleNamespace(run=exchange, TimeoutExpired=subprocess.TimeoutExpired)
original = worker.organ
worker.organ = lambda name: types.SimpleNamespace(Supervisor=lambda profile, qualification:
    P.M.Supervisor(profile, qualification, backend=backend)) if name == 'project_runner_macos' else client_module if name == 'control_worker_client' else original(name)
original_control = worker.C.organ
worker.C.organ = lambda name: types.SimpleNamespace(identity=lambda pid: dict(backend.process, pid=pid)) \
    if name == 'project_runner_macos_os' else original_control(name)
marker = {'bootstraps': 0}
try:
    result = worker.receive(config, request)
    marker['state'] = result['record']['state']
except Exception:
    marker['error'] = traceback.format_exc()
    raise
finally:
    marker['bootstraps'] = backend.bootstraps
    Path(config['fixture_marker']).write_text(json.dumps(marker))
