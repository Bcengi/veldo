"""Tiny real scheduler processes; simulated cgroup files, no manager, host lock or load."""


def _v360_checks():
    import importlib.util
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys
    import tempfile
    from unittest.mock import patch

    source = ROOT / "scripts" / "gate_schedule.py"
    spec = importlib.util.spec_from_file_location('v360_schedule', source)
    scheduler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scheduler)

    def row(name, ok):
        expect('VELDO-0360 failfast/' + name, ok)

    deps = {'unit': set(), 'load': {'unit'}, 'mutation': {'load'}, 'tail': {'mutation'}}
    results = {'unit': {'verdict': 'FAIL'}}
    held = []
    for name in ('load', 'mutation', 'tail'):
        answer = scheduler.held(name, deps, results)
        held.append(answer and answer[0])
        results[name] = {'verdict': answer[0] if answer else 'pass'}
    row('held-chain', held == ['not_run', 'not_started', 'not_started'])
    row('held-generic', scheduler.held('tail', {'tail': {'unit'}}, results) is not None)
    row('held-green', scheduler.held('tail', {'tail': {'unit'}}, {'unit': {'verdict': 'pass'}}) is None)
    row('held-diagnostic', scheduler.held('mutation', deps, results, True) is None
        and scheduler.held('tail', deps, results, True) is None
        and scheduler.held('mutation', deps, {'load': {'verdict': 'FAIL'}}, True) is not None)

    # The CLI sets subreaper status and reaps adopted grandchildren before publishing its receipt.
    # Its meter uses the production finish() against a simulated cgroup filesystem. cgroup.kill
    # really kills the fixture processes; cgroup.events reads their kernel process state.
    wrapper = r'''
import importlib.util, json, os, select, signal, sys
from pathlib import Path
source, top, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
spec = importlib.util.spec_from_file_location('fixture_schedule', source)
s = importlib.util.module_from_spec(spec); spec.loader.exec_module(s)
s.HERE = Path(os.environ['V360_SCRIPTS'])
sys.path.insert(0, str(Path(os.environ['V360_SCRIPTS']) / 'suites'))
from support.waits import wait, PathAppears
class File:
    def __init__(self, group, name): self.group, self.name = group, name
    def read_text(self):
        if not self.group.directory.exists(): raise FileNotFoundError('removed fixture cgroup')
        if self.name == 'memory.stat': return 'anon 1024\n'
        if self.name == 'cpu.stat': return 'usage_usec 1000\n'
        live = False
        for pid in self.group.pids():
            try: live |= Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()[0] != 'Z'
            except FileNotFoundError: pass
        return 'populated %d' % live
    def write_text(self, value):
        assert self.name == 'cgroup.kill' and value == '1'
        (top / (self.group.name + '.killed')).write_text('1')
        for pid in self.group.pids():
            try: os.kill(pid, signal.SIGKILL)
            except ProcessLookupError: pass
class Group:
    def __init__(self, name):
        self.name = name
        self.directory = top / (name + '.cgroup'); self.directory.mkdir()
    def pids(self):
        path = top / (self.name + '.pids')
        return json.loads(path.read_text()) if path.exists() else []
    def __truediv__(self, name): return File(self, name)
    def rglob(self, pattern): return []
    def rmdir(self): self.directory.rmdir()
# Rescue a defective cancellation at the next observation, so its falsifier returns a
# named red row instead of depending on a timeout. Normal cancellation needs no rescue.
released_red = False
release = s.Ledger.release
def released(self, name):
    global released_red
    release(self, name)
    if name == 'red':
        released_red = True
        (top / 'red.settled').write_text('1')
s.Ledger.release = released
class Meter(s.Meter):
    def __init__(self, scope, name):
        self.path, self.peak, self.finished = Group(name), 0, None
    def command(self, argv): return argv
    def finish(self):
        self.finishing = True
        try: return super().finish()
        finally: self.finishing = False
    def sample(self):
        if not getattr(self, 'finishing', False) and self.path.name == 'worker' and released_red and mode == 'early':
            live = [pid for pid in self.path.pids() if Path('/proc/%d/stat' % pid).exists()
                    and Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()[0] != 'Z']
            if live:
                # A killed stage may still have live descendants: normal finish owns those.
                root = self.path.pids()[0]
                if root not in live: return super().sample()
                (top / 'rescued').write_text('1')
                self.path.__truediv__('cgroup.kill').write_text('1')
                for pid in live:
                    try: fd = os.pidfd_open(pid)
                    except ProcessLookupError: continue
                    poll = select.poll(); poll.register(fd, select.POLLIN); poll.poll(); os.close(fd)
        return super().sample()
s.Meter = Meter
s.capacities = lambda *args: dict(cpu=2, memory=4 * 2**30, manager=2)
s.command_for = lambda root, stage, *args: [sys.executable, str(top / 'stage.py'), stage, mode]
s.input_guard = lambda root: lambda: True
original = s.run
def run(*args, **kwargs):
    return original(*args, **kwargs, graph_path=top / 'graph.json', declaration_path=top / 'absent',
                    measurement_store=top / 'store', guard_factory=lambda root: lambda: True)
s.run = run
code = s.main(['--root', str(top), '--directory', str(top / 'out'), '--record', str(top / 'legs'),
               '--receipt', str(top / 'mutation.receipt'),
               *[arg for name in ('worker', 'red', 'tail', 'load', 'mutation', 'after')
                 for arg in ('--stage', name, 'fixture')]])
pids = json.loads((top / 'worker.pids').read_text()) if (top / 'worker.pids').exists() else []
if any(Path('/proc/%d' % pid).exists() for pid in pids): (top / 'unreaped').write_text('1')
import ctypes
flag = ctypes.c_int()
ctypes.CDLL(None).prctl(37, ctypes.byref(flag), 0, 0, 0)
(top / 'adopted').write_text(str(flag.value))
raise SystemExit(code)
'''
    stage = r'''
import importlib.util, json, os, signal, subprocess, sys
from pathlib import Path
top, name, mode = Path(__file__).parent, sys.argv[1], sys.argv[2]
source = Path(os.environ['V360_SOURCE'])
sys.path.insert(0, str(Path(os.environ['V360_SCRIPTS']) / 'suites'))
from support.waits import wait, PathAppears
spec = importlib.util.spec_from_file_location('fixture_client', source)
s = importlib.util.module_from_spec(spec); spec.loader.exec_module(s)
(top / (name + '.started')).write_text('1')
print('partial output: ' + name, flush=True)
if name == 'worker':
    client = s.Client()
    assert client.acquire('child', 0, 0)
    child = subprocess.Popen([sys.executable, '-c', 'import signal; signal.pause()'], start_new_session=True)
    (top / 'worker.pids').write_text(json.dumps([os.getpid(), child.pid]))
    (top / 'worker.ready').write_text('1')
    if mode == 'early': signal.pause()
    else:
        wait('red stage settled', lambda: (top / 'red.settled').exists(), sources=[PathAppears(top / 'red.settled')])
        child.kill(); child.wait(); client.release('child'); client.close()
elif name == 'red':
    wait('worker has a grant', lambda: (top / 'worker.ready').exists(), sources=[PathAppears(top / 'worker.ready')])
    (top / 'red.done').write_text('1')
    raise SystemExit(0 if mode == 'green' else 7)
elif name == 'after':
    raise SystemExit(0 if mode == 'green' else 9)
elif name == 'mutation':
    (top / 'mutation.receipt').write_text('{"partial":"preserved"}')
'''
    with tempfile.TemporaryDirectory(prefix='v360-') as temporary:
        base = Path(temporary)
        (base / 'wrapper.py').write_text(wrapper)
        observations = {}
        for tag, mode, setting in (('early', 'early', ''), ('diagnostic', 'diagnostic', '1'),
                                    ('green', 'green', ''), ('green-diagnostic', 'green', '1'),
                                    ('not-opted-in', 'early', 'true')):
            top = base / tag
            top.mkdir()
            (top / 'stage.py').write_text(stage)
            nodes = {'worker': [], 'red': [], 'tail': [], 'load': ['red', 'worker', 'tail'],
                     'mutation': ['load'], 'after': ['mutation']}
            (top / 'graph.json').write_text(json.dumps(dict(schema='veldo.gate-graph/v1',
                nodes={n: dict(depends_on=d, writes_candidate=False, manager='none', ports=[],
                    estimate=dict(source='fixture', wall_seconds=1, cpu_seconds=1,
                                  peak_cgroup_memory_bytes=1024)) for n, d in nodes.items()},
                reserve=dict(cpu=0, memory=0), mutation_floor=dict(cpu=0, memory=0))))
            env = dict(os.environ, V360_SOURCE=str(source), V360_SCRIPTS=str(ROOT / 'scripts'), VELDO_GATE_COLLECT_ALL=setting)
            proc = subprocess.run([sys.executable, str(base / 'wrapper.py'), str(source), str(top), mode],
                                  env=env, capture_output=True, text=True)
            receipt_path = top / 'out/receipt.json'
            if not receipt_path.exists():
                print(proc.stdout, proc.stderr)
            receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
            observations[tag] = receipt
            row(tag + '/status', proc.returncode == (0 if mode == 'green' else 1))
            first = receipt.get('first_failure') or {}
            row(tag + '/first-red', first == {} if mode == 'green' else
                first.get('node') == 'red' and first.get('returncode') == 7 and first.get('verdict') == 'FAIL')
            ledger = receipt.get('ledger', [])
            grants = [e['claimant'] for e in ledger if e['action'] == 'grant']
            releases = [e['claimant'] for e in ledger if e['action'] == 'release']
            pids = json.loads((top / 'worker.pids').read_text()) if (top / 'worker.pids').exists() else []
            row(tag + '/cleanup', bool(pids) and sorted(grants) == sorted(releases) and 'worker/child' in grants
                and not list(top.glob('*.cgroup')) and not (top / 'unreaped').exists() and all(not Path('/proc/%d' % p).exists() for p in pids))
            row(tag + '/adoption', (top / 'adopted').exists() and (top / 'adopted').read_text() == '1')
            row(tag + '/partial', (top / 'out/red.log').exists() and (top / 'out/worker.log').exists()
                and 'partial output: red' in (top / 'out/red.log').read_text()
                and 'partial output: worker' in (top / 'out/worker.log').read_text())
            stages = receipt.get('stages', {})
            if mode == 'early':
                row(tag + '/stopped', stages == dict(worker='cancelled', red='FAIL', tail='not_started',
                    load='not_run', mutation='not_started', after='not_started')
                    and not (top / 'mutation.started').exists() and not (top / 'tail.started').exists()
                    and (top / 'worker.killed').exists() and not (top / 'rescued').exists())
            elif mode == 'diagnostic':
                row('collect-all', stages == dict(worker='pass', red='FAIL', tail='pass',
                    load='not_run', mutation='pass', after='FAIL')
                    and (top / 'mutation.receipt').exists()
                    and json.loads((top / 'mutation.receipt').read_text()) == {'partial': 'preserved'})
            else:
                row(tag + '/unchanged', set(stages.values()) == {'pass'} and not list(top.glob('*.killed')))
        row('green-identical', observations['green'].get('stages') == observations['green-diagnostic'].get('stages'))

    # A denied subreaper runs nothing. Exceptional exits still reap adopted children.
    with patch.object(scheduler.ctypes, 'CDLL') as libc, patch.object(scheduler, 'run') as run:
        libc.return_value.prctl.return_value = -1
        run.side_effect = scheduler.Refused('fixture must not run')
        row('subreaper-refused', scheduler.main(['--root', '.', '--directory', '.', '--record', 'unused',
            '--receipt', 'unused']) == 1 and not run.called)

    with patch.object(scheduler.ctypes, 'CDLL') as libc, patch.object(scheduler, 'run') as run, \
            patch.object(scheduler, 'reap_children') as reap:
        libc.return_value.prctl.return_value = 0
        run.side_effect = scheduler.Refused('fixture cleanup failure')
        row('error-cleanup', scheduler.main(['--root', '.', '--directory', '.', '--record', 'unused',
            '--receipt', 'unused']) == 1 and reap.called)


_v360_checks()
