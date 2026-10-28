"""Round three regressions. Kernel and ownership effects stay in scratch fixtures."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]


def cli_channel(gate, present):
    """Run the CLI entry and real stage setup, stopping at an empty inventory."""
    scheduler = gate.load(ROOT / 'scripts/gate_schedule.py')
    calls = []
    class Admission:
        events = []
        peak = {}
        capacity = {}
        def close(self):
            pass
    def authority():
        calls.append(True)
        if scheduler.CHANNEL not in os.environ:
            raise gate.Refused('worker_launch_error', 'missing test ledger channel')
        return Admission()
    environment = dict(os.environ)
    environment.pop(scheduler.CHANNEL, None)
    if present:
        environment[scheduler.CHANNEL] = 'fixture'
    with tempfile.TemporaryDirectory(prefix='v219-cli-') as temporary:
        receipt = Path(temporary) / 'receipt.json'
        assert (ROOT / 'scripts/gate_graph.json').is_file()
        with patch.dict(os.environ, environment, clear=True), \
                patch.object(sys, 'argv', [str(gate.__file__), '--case', 'fixture', '--receipt', str(receipt)]), \
                patch.object(gate, 'inventory', lambda *a: []), \
                patch.object(gate, 'worker_count', lambda *a: 40), \
                patch.object(gate, 'PARALLEL', 40), \
                patch.object(gate.Admission, 'authority', authority), \
                contextlib.redirect_stdout(io.StringIO()):
            code = gate.main()
        result = json.loads(receipt.read_text())
    return (code == 1 and result['error'] == 'incomplete_inventory'
            and calls == ([True] if present else [])
            and result['parallel_workers'] == (40 if present else 16))


def before_handoff(schedule):
    with tempfile.TemporaryDirectory(prefix='v219-before-handoff-') as temporary:
        top = Path(temporary)
        graph = json.loads((ROOT / 'scripts/gate_graph.json').read_text())
        graph['nodes'] = {'mutation': graph['nodes']['mutation']}
        (top / 'graph.json').write_text(json.dumps(graph))
        child = top / 'child.py'
        child.write_text('''import importlib.util,sys
s=importlib.util.spec_from_file_location('schedule',sys.argv[1])
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
c=m.Client()
try:
    if c.acquire('premature',0,0):
        c.release('premature')
except m.Refused as error:
    assert str(error)=='worker admission requires coordinator handoff'
finally:
    c.close()
''')
        class Meter:
            def command(self, argv):
                return argv
            def sample(self):
                return dict(cpu_seconds=.01, peak_anon_bytes=1024)
            def finish(self):
                return self.sample()
        # Mutants are single-file copies; keep their unchanged sibling modules
        # at the authority path while exercising the copied scheduler itself.
        with patch.object(schedule, 'HERE', ROOT / 'scripts'), \
                patch.object(schedule, 'command_for', lambda *a: [sys.executable, '-B', str(child), str(schedule.__file__)]), \
                contextlib.redirect_stdout(io.StringIO()):
            result = schedule.run({'mutation': 'fixture'}, top, top / 'logs', top / 'legs', top / 'receipt',
                graph_path=top / 'graph.json', declaration_path=top / 'absent',
                capacity=dict(cpu=20, memory=15*2**30, manager=16), measurement_store=top / 'times',
                meter_factory=lambda n: Meter(), guard_factory=lambda r: lambda: True)
        node = result['nodes']['mutation']
        return (result['stages']['mutation'] == 'FAIL' and node['returncode'] == 0
                and node['error'] == 'ledger_protocol: worker admission requires coordinator handoff'
                and not any(e['action'] == 'grant' and e['claimant'] == 'mutation/premature'
                            for e in result['ledger']))


def ownership_registration(owner):
    checks = []
    with tempfile.TemporaryDirectory(prefix='v219-register-') as temporary:
        top = Path(temporary)
        (top / 'scope').mkdir()
        for kind, value in [('slice', 'veldo219registration.slice'),
                            ('service', str(owner.unit_directory() / 'veldo-authority-ab.service'))]:
            for state in ('absent', 'owned', 'invalid'):
                ledger = top / 'ledger'
                ledger.write_text('' if state == 'absent' else json.dumps([kind, value]) + '\n'
                                  + ('invalid\n' if state == 'invalid' else ''))
                meter = owner.WorkerMeter('/scope', kind + state, top)
                meter.open_lifecycle()
                meter.peer.settimeout(2)
                prepared = []
                error = None
                try:
                    meter.peer.send(json.dumps(['register', kind, value]).encode())
                    with patch.object(meter, 'prepare_unit', lambda *args: prepared.append(args)):
                        try:
                            meter.lifecycle_events(top, ledger)
                        except ValueError as caught:
                            error = str(caught)
                    reply = json.loads(meter.peer.recv(65536))
                    if state == 'owned':
                        checks.append(error is None and reply == {'ok': True} and prepared == [(kind, value)])
                    else:
                        expected = 'lifecycle unit is not in the ownership ledger'
                        checks.append(error == expected and reply == {'error': expected} and not prepared)
                finally:
                    meter.peer.close()
                    meter.lifecycle.close()
    return all(checks)
