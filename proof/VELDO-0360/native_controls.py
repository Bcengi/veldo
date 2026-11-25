#!/usr/bin/env python3
"""Tiny native-cgroup controls in a caller-created private delegated service; never a gate."""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
source = ROOT / 'scripts/gate_schedule.py'
suite = ROOT / 'scripts/suites/161_veldo_0360_failfast.py'
function = next(n for n in ast.parse(suite.read_text()).body if isinstance(n, ast.FunctionDef))
strings = {n.targets[0].id: ast.literal_eval(n.value) for n in function.body
           if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
           and n.targets[0].id in ('wrapper', 'stage')}
# Change only the fixture meter boundary: run production Meter.command/sample/finish.
wrapper = strings['wrapper'].replace('s.Meter = Meter\n', '')
scope = Path('/proc/self/cgroup').read_text().split('::', 1)[1].strip()
group = Path('/sys/fs/cgroup') / scope.lstrip('/')
supervisor = group / 'control'
supervisor.mkdir()
(supervisor / 'cgroup.procs').write_text(str(os.getpid()))
(group / 'cgroup.subtree_control').write_text('+memory')
observations = []
with tempfile.TemporaryDirectory(prefix='v360-native-') as temporary:
    base = Path(temporary)
    (base / 'wrapper.py').write_text(wrapper)
    for tag, mode, setting in (('early', 'early', ''), ('diagnostic', 'diagnostic', '1'),
                                ('green', 'green', ''), ('green-diagnostic', 'green', '1')):
        top = base / tag
        top.mkdir()
        (top / 'stage.py').write_text(strings['stage'])
        nodes = {'worker': [], 'red': [], 'tail': [], 'load': ['red', 'worker', 'tail'],
                 'mutation': ['load'], 'after': ['mutation']}
        (top / 'graph.json').write_text(json.dumps(dict(schema='veldo.gate-graph/v1',
            nodes={n: dict(depends_on=d, writes_candidate=False, manager='none', ports=[],
                estimate=dict(source='tiny native fixture', wall_seconds=1, cpu_seconds=1,
                              peak_cgroup_memory_bytes=1024)) for n, d in nodes.items()},
            reserve=dict(cpu=0, memory=0), mutation_floor=dict(cpu=0, memory=0))))
        env = dict(os.environ, V360_SOURCE=str(source), V360_SCRIPTS=str(ROOT / 'scripts'),
                   VELDO_GATE_COLLECT_ALL=setting, VELDO_GATE_SCOPE=scope)
        proc = subprocess.run([sys.executable, str(base / 'wrapper.py'), str(source), str(top), mode],
                              env=env, capture_output=True, text=True)
        print(tag, 'exit', proc.returncode, flush=True)
        assert (top / 'out/receipt.json').exists(), proc.stdout + proc.stderr
        receipt = json.loads((top / 'out/receipt.json').read_text())
        pids = json.loads((top / 'worker.pids').read_text())
        grants = [e['claimant'] for e in receipt['ledger'] if e['action'] == 'grant']
        releases = [e['claimant'] for e in receipt['ledger'] if e['action'] == 'release']
        clean = (sorted(grants) == sorted(releases) and not list(group.glob('node-*'))
                 and all(not Path('/proc/%d' % pid).exists() for pid in pids)
                 and not (top / 'unreaped').exists())
        assert clean and 'worker/child' in grants
        assert proc.returncode == (0 if mode == 'green' else 1)
        if mode == 'early':
            assert receipt['stages'] == dict(worker='cancelled', red='FAIL', tail='not_started',
                                            load='not_run', mutation='not_started', after='not_started')
            assert not (top / 'mutation.started').exists()
        elif mode == 'diagnostic':
            assert receipt['stages'] == dict(worker='pass', red='FAIL', tail='pass',
                                            load='not_run', mutation='pass', after='FAIL')
        else:
            assert set(receipt['stages'].values()) == {'pass'}
        assert receipt['first_failure'] is None if mode == 'green' else (
            receipt['first_failure']['node'] == 'red' and receipt['first_failure']['returncode'] == 7)
        observations.append(dict(control=tag, scheduler_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), stages=receipt['stages'], first_failure=receipt['first_failure'],
                                 cleanup=clean, grants=len(grants), releases=len(releases),
                                 metrics={n: {k: r.get(k) for k in ('wall_seconds', 'cpu_seconds', 'peak_anon_bytes')}
                                          for n, r in receipt['nodes'].items()}))
        (Path(__file__).parent / ('native-' + tag + '.json')).write_text(json.dumps(receipt, indent=2) + '\n')
assert observations[2]['stages'] == observations[3]['stages']
(Path(__file__).parent / 'native-controls.json').write_text(json.dumps(observations, indent=2) + '\n')
print('4 native controls passed; all worker PIDs reaped, cgroups removed, grants released', flush=True)
