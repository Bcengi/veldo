"""PRE-FIX STAND-IN, used only by proof/VELDO-0039/red.py. It is NOT production code.

The launch path the repository had at d95a809, behind the runner interface the suite drives. It is
VELDO-0052's StationCalls.launch (opens a dispatch: a fresh identity and its VELDO-0036 worker slot)
with the station's CallHandle.invoke (the provider_request decision) and VELDO-0036's
InvocationGuard, whose launch callable spawns the configured worker argv with the configuration
passed unchanged; the launch scope closes (retires the slot) when the launch returns. Every one of
those behaviors is d95a809's module, loaded beside this file. What the suite calls the receiver is
this same path: there was no separate receiver, no durable acceptance and no launch record.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time
import uuid


def _organ(name):
    spec = importlib.util.spec_from_file_location('prefix_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


D = _organ('control_dispatch')
EL = D.EL
RT = _organ('control_reservation_runtime')
RUNNERS = {}


def process_identity(pid):
    return {'pid': pid}


class Launch:
    def __init__(self, dispatch_id, child, result, refusal=None):
        self.dispatch_id, self.child, self.result, self.refusal = dispatch_id, child, result, refusal
        self.owned, self.record = True, None

    def wait(self, timeout=None):
        if self.child is not None:
            try:
                self.child.wait(timeout=timeout or 60)
            except subprocess.TimeoutExpired:
                pass
        return None


def invoke(config_path, contract, dispatches, *, accept_seconds=30, environment=None, clock=None):
    """The d95a809 launch of one station: StationCalls.launch, then CallHandle.invoke."""
    if not isinstance(contract, dict) or contract.get('_runner') not in RUNNERS:
        return Launch(None, None, None)
    runner = RUNNERS[contract['_runner']]
    config = json.loads(Path(config_path).read_text())
    argv = config['adapters'][contract['capability']['adapter']]['argv']
    spawned = {}

    def launch(invocation, configuration):
        dispatch = guard.active[invocation]['dispatch']
        child = subprocess.Popen(list(argv), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                 env={'PATH': os.environ.get('PATH', os.defpath), 'VELDO_DISPATCH_ID': dispatch},
                                 start_new_session=True)
        child.stdin.write(json.dumps({'dispatch_id': dispatch, 'payload': contract['input']['payload'],
                                      'configuration': configuration}).encode())
        child.stdin.close()
        spawned['child'], spawned['dispatch'] = child, dispatch

    guard = RT.InvocationGuard(runner.reservations, 'codex', launch, lambda dispatch: None)
    calls = EL.StationCalls(runner.gate, {'codex': guard}, account=runner.account)
    try:
        with calls.launch(contract['station'], contract['unit'], context=contract['input']['context'], ticket=None) as handle:
            handle.invoke('codex', 'initial', 'call/' + uuid.uuid4().hex, 30, contract['capability']['configuration'],
                          now=time.time())
    except EL.Refused as error:
        return Launch(spawned.get('dispatch'), spawned.get('child'), 'refused', error.code)
    except Exception as error:  # noqa: BLE001 - d95a809 raised; the stand-in reports it
        return Launch(spawned.get('dispatch'), spawned.get('child'), 'raised:' + type(error).__name__)
    return Launch(spawned.get('dispatch'), spawned.get('child'), 'accepted')


class Runner:
    def __init__(self, gate, reservations, dispatches, receiver, *, account, clock=None):
        self.gate, self.reservations, self.dispatches, self.receiver = gate, reservations, dispatches, receiver
        self.account = account
        self.key = uuid.uuid4().hex
        RUNNERS[self.key] = self

    def prepare(self, unit, station, *, holder, source, revision, payload, adapter, configuration, deadline,
                context=None):
        """d95a809 had no preparation: opening a dispatch reserved a slot and named an identity."""
        calls = EL.StationCalls(self.gate, {'codex': RT.InvocationGuard(self.reservations, 'codex', None, None)},
                                account=self.account)
        dispatch_id = calls.open_dispatch(unit, context={'holder': holder})
        return {'dispatch_id': dispatch_id, '_runner': self.key, 'unit': unit, 'station': station,
                'input': {'payload': payload, 'context': dict(context or {}, holder=holder)},
                'capability': {'adapter': adapter, 'configuration': configuration}}

    def submit(self, unit, station, *, holder, source, revision, payload, adapter, configuration, deadline,
               context=None):
        self.gate.require(station, unit, context=dict(context or {}, holder=holder))
        contract = {'_runner': self.key, 'unit': unit, 'station': station,
                    'input': {'payload': payload, 'context': dict(context or {}, holder=holder)},
                    'capability': {'adapter': adapter, 'configuration': configuration}}
        return self.receiver(contract)

    def wait(self, launch, timeout=None):
        return launch.wait(timeout)
