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
output = Path(__file__).parent / 'fix-round2'
output.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='v360-native-') as temporary:
    base = Path(temporary)
    (base / 'wrapper.py').write_text(wrapper)
    for tag, mode, setting in (('early', 'early', ''), ('diagnostic', 'diagnostic', '1'),
                                ('green', 'green', ''), ('green-diagnostic', 'green', '1'),
                                ('sibling', 'sibling', ''),
                                ('mutation-cancel', 'mutation-cancel', ''),
                                ('mutation-killed', 'mutation-killed', ''),
                                ('mutation-exception', 'mutation-exception', '')):
        top = base / tag
        top.mkdir()
        (top / 'stage.py').write_text(strings['stage'])
        nodes = {'worker': [], 'red': [], 'tail': [], 'load': ['red', 'worker', 'tail'],
                 'mutation': ['load'], 'after': ['mutation']}
        if mode == 'sibling':
            nodes = dict(worker=[], red=[])
        if mode.startswith('mutation-'):
            nodes = dict(mutation=[], red=[], worker=['mutation'], tail=['mutation'],
                         load=['red', 'worker', 'tail'], after=['mutation'])
        (top / 'graph.json').write_text(json.dumps(dict(schema='veldo.gate-graph/v1',
            nodes={n: dict(depends_on=d, writes_candidate=False, manager='none', ports=[],
                estimate=dict(source='tiny native fixture', wall_seconds=1, cpu_seconds=1,
                              peak_cgroup_memory_bytes=1024)) for n, d in nodes.items()},
            reserve=dict(cpu=0, memory=0), mutation_floor=dict(cpu=0, memory=0))))
        env = dict(os.environ, V360_SOURCE=str(source), V360_SCRIPTS=str(ROOT / 'scripts'),
                   VELDO_GATE_COLLECT_ALL=setting, VELDO_GATE_SCOPE=scope, V360_NATIVE='1')
        proc = subprocess.run([sys.executable, str(base / 'wrapper.py'), str(source), str(top), mode],
                              env=env, capture_output=True, text=True)
        print(tag, 'exit', proc.returncode, flush=True)
        if mode.startswith('mutation-'):
            receipt_path = top / 'out/receipt.json'
            receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
            assert (top / 'mutation.pids').exists(), proc.stdout + proc.stderr
            pids = json.loads((top / 'mutation.pids').read_text())
            ledger = json.loads((top / 'ledger.json').read_text())
            grants = sorted(e['claimant'] for e in ledger if e['action'] == 'grant')
            releases = sorted(e['claimant'] for e in ledger if e['action'] == 'release')
            order = [json.loads(line) for line in (top / 'release-observations').read_text().splitlines()]
            assert proc.returncode == 1 and len(pids) == 5, proc.stdout + proc.stderr
            assert all(not Path('/proc/%d' % pid).exists() for pid in pids)
            assert not list(group.glob('worker-*')) and not list(group.glob('node-*'))
            assert not (top / 'unreaped').exists() and not (top / 'rescued').exists() and grants == releases
            assert {r['name'] for r in order} == {'mutation', 'mutation/child0', 'mutation/child1'}
            assert all(r['gone'] and r['removed'] for r in order)
            assert json.loads((top / 'mutation.receipt').read_text()) == {'partial': 'preserved'}
            if mode == 'mutation-cancel':
                assert receipt['first_failure']['node'] == 'red' and receipt['first_failure']['returncode'] == 7
                assert receipt['stages']['mutation'] == 'cancelled'
            elif mode == 'mutation-killed':
                assert receipt['stages']['mutation'] == 'FAIL' and receipt['nodes']['mutation']['returncode'] == -9
            else:
                assert not receipt and 'fixture sampling failure' in proc.stdout
            observations.append(dict(control=tag, scheduler_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                                     stages=receipt.get('stages'), first_failure=receipt.get('first_failure'),
                                     worker_pids=pids, cleanup=True, release_observations=order,
                                     grants=grants, releases=releases))
            (output / ('native-' + tag + '.json')).write_text(json.dumps(dict(receipt=receipt, ledger=ledger, releases=order), indent=2) + '\n')
            continue
        assert (top / 'out/receipt.json').exists(), proc.stdout + proc.stderr
        receipt = json.loads((top / 'out/receipt.json').read_text())
        pids = json.loads((top / 'worker.pids').read_text())
        grants = [e['claimant'] for e in receipt['ledger'] if e['action'] == 'grant']
        releases = [e['claimant'] for e in receipt['ledger'] if e['action'] == 'release']
        clean = (sorted(grants) == sorted(releases) and not list(group.glob('node-*'))
                 and all(not Path('/proc/%d' % pid).exists() for pid in pids)
                 and not (top / 'unreaped').exists())
        assert clean and 'worker/child' in grants
        assert proc.returncode == (0 if mode in ('green', 'sibling') else 1)
        if mode == 'early':
            assert receipt['stages'] == dict(worker='cancelled', red='FAIL', tail='not_started',
                                            load='not_run', mutation='not_started', after='not_started')
            assert not (top / 'mutation.started').exists()
        elif mode == 'diagnostic':
            assert receipt['stages'] == dict(worker='pass', red='FAIL', tail='pass',
                                            load='not_run', mutation='pass', after='FAIL')
        else:
            assert set(receipt['stages'].values()) == {'pass'}
        assert receipt['first_failure'] is None if mode in ('green', 'sibling') else (
            receipt['first_failure']['node'] == 'red' and receipt['first_failure']['returncode'] == 7)
        if mode == 'sibling':
            assert (top / 'sibling.survived').read_text() == 'True'
            assert receipt['stages'] == dict(worker='pass', red='pass')
            assert receipt['nodes']['red']['end'] < receipt['nodes']['worker']['end']
        observations.append(dict(control=tag, scheduler_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), stages=receipt['stages'], first_failure=receipt['first_failure'],
                                 cleanup=clean, grants=len(grants), releases=len(releases),
                                 metrics={n: {k: r.get(k) for k in ('wall_seconds', 'cpu_seconds', 'peak_anon_bytes')}
                                          for n, r in receipt['nodes'].items()}))
        (output / ('native-' + tag + '.json')).write_text(json.dumps(receipt, indent=2) + '\n')
assert observations[2]['stages'] == observations[3]['stages']
(output / 'native-controls.json').write_text(json.dumps(observations, indent=2) + '\n')
print('8 native controls passed; all worker PIDs reaped, cgroups removed, grants released', flush=True)
