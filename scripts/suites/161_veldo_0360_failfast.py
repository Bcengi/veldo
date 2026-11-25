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

    # Probe syscall flags before the live control, so a blocking mutant is rejected
    # without deadlocking the event handshake that deliberately holds a child alive.
    with patch.object(scheduler, 'child_pids', return_value={11, 99}) as children, \
            patch.object(scheduler.os, 'waitpid', return_value=(0, 0)) as reap, \
            patch.object(scheduler.os, 'kill') as kill:
        scheduler.reap_exited_children({99})
        nonblocking = reap.call_args_list == [((11, os.WNOHANG),)] and not kill.called
        row('zombie-only', nonblocking and children.call_count == 1)
    with patch.object(scheduler, 'child_pids', return_value={11}), \
            patch.object(scheduler.os, 'waitpid', side_effect=ChildProcessError):
        try:
            scheduler.reap_exited_children()
            raced = True
        except ChildProcessError:
            raced = False
        row('zombie-race', raced)

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
        self.directory = top / (name + '.cgroup'); self.directory.mkdir(exist_ok=True)
    def pids(self):
        path = top / (self.name + '.pids')
        pids = json.loads(path.read_text()) if path.exists() else []
        return pids[:1] if self.name == 'mutation' else pids
    def __truediv__(self, name): return File(self, name)
    def rglob(self, pattern): return []
    def rmdir(self):
        assert 'populated 1' not in (self / 'cgroup.events').read_text()
        self.directory.rmdir()
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
# Only the simulated filesystem needs an event adapter. Native controls keep the real helper.
load_module = s.load_module
def load(name):
    module = load_module(name)
    if name == 'mutation_ownership':
        native_wait = module.wait_for_empty
        def empty(path):
            if not isinstance(path, Group): return native_wait(path)
            if 'populated 1' not in (path / 'cgroup.events').read_text(): return
            path.__truediv__('cgroup.kill').write_text('1')
            for pid in path.pids():
                try: fd = os.pidfd_open(pid)
                except ProcessLookupError: continue
                poll = select.poll(); poll.register(fd, select.POLLIN); poll.poll(); os.close(fd)
        module.wait_for_empty = empty
    return module
s.load_module = load
if not os.environ.get('V360_NATIVE'):
    class Scope:
        def __truediv__(self, name): return self
        def glob(self, pattern):
            return [Group(p.name.removesuffix('.cgroup')) for p in top.glob(pattern + '.cgroup')]
    s.Path = lambda p: Scope() if p == '/sys/fs/cgroup' else Path(p)
# Observe the release itself, before the CLI's fallback reaper could conceal bad ordering.
release_observed = s.Ledger.release
def observe_release(self, name):
    if name == 'mutation' or name.startswith('mutation/'):
        pids_file = top / 'mutation.pids'
        pids = json.loads(pids_file.read_text()) if pids_file.exists() else []
        scope = Path('/sys/fs/cgroup') / os.environ['VELDO_GATE_SCOPE'].lstrip('/')
        groups = list(scope.glob('worker-*')) if os.environ.get('V360_NATIVE') else list(top.glob('worker-*.cgroup'))
        with (top / 'release-observations').open('a') as f:
            f.write(json.dumps(dict(name=name, gone=all(not Path('/proc/%d' % p).exists() for p in pids),
                                   removed=not groups)) + '\n')
    release_observed(self, name)
    (top / 'ledger.json').write_text(json.dumps(self.events))
s.Ledger.release = observe_release
sample = s.Meter.sample
injected = False
def fault(self):
    global injected
    if mode == 'mutation-exception' and (top / 'mutation.ready').exists() and not injected:
        injected = True
        raise OSError('fixture sampling failure')
    if mode == 'mutation-cancel' and released_red and (top / 'mutation.pids').exists():
        root = json.loads((top / 'mutation.pids').read_text())[0]
        stat = Path('/proc/%d/stat' % root)
        if stat.exists() and stat.read_text().rsplit(')', 1)[1].split()[0] != 'Z':
            (top / 'rescued').write_text('1')
            fd = os.pidfd_open(root); os.kill(root, signal.SIGKILL)
            poll = select.poll(); poll.register(fd, select.POLLIN); poll.poll(); os.close(fd)
    return sample(self)
s.Meter.sample = fault
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
               *[arg for name in (('worker', 'red') if mode == 'sibling' else ('worker', 'red', 'tail', 'load', 'mutation', 'after'))
                 for arg in ('--stage', name, 'fixture')]])
pids = json.loads((top / 'worker.pids').read_text()) if (top / 'worker.pids').exists() else []
if any(Path('/proc/%d' % pid).exists() for pid in pids): (top / 'unreaped').write_text('1')
# Rescue any defective mutant only after observing its release and final state.
if (top / 'mutation.pids').exists():
    pids = json.loads((top / 'mutation.pids').read_text())
    if any(Path('/proc/%d' % p).exists() for p in pids): (top / 'unreaped').write_text('1')
    for pid in pids:
        try: os.kill(pid, signal.SIGKILL)
        except ProcessLookupError: pass
    for pid in pids:
        try: os.waitpid(pid, 0)
        except ChildProcessError: pass
import ctypes
flag = ctypes.c_int()
ctypes.CDLL(None).prctl(37, ctypes.byref(flag), 0, 0, 0)
(top / 'adopted').write_text(str(flag.value))
raise SystemExit(code)
'''
    stage = r'''
import importlib.util, json, os, select, signal, socket, subprocess, sys
from pathlib import Path
top, name, mode = Path(__file__).parent, sys.argv[1], sys.argv[2]
source = Path(os.environ['V360_SOURCE'])
sys.path.insert(0, str(Path(os.environ['V360_SCRIPTS']) / 'suites'))
from support.waits import wait, PathAppears
spec = importlib.util.spec_from_file_location('fixture_client', source)
s = importlib.util.module_from_spec(spec); spec.loader.exec_module(s)
(top / (name + '.started')).write_text('1')
print('partial output: ' + name, flush=True)
if name == 'mutation' and mode.startswith('mutation-'):
    client = s.Client()
    (top / 'mutation.receipt').write_text('{"partial":"preserved"}')
    pids = [os.getpid()]
    for index in range(2):
        assert client.acquire('child%d' % index, 0, 0)
        group_name = 'worker-%d-fixture%d' % (os.getpid(), index)
        if os.environ.get('V360_NATIVE'):
            group = Path('/sys/fs/cgroup') / os.environ['VELDO_GATE_SCOPE'].lstrip('/') / group_name
            group.mkdir(); (group / 'nested').mkdir()
        else:
            group = top / (group_name + '.cgroup'); group.mkdir()
        program = """
import json, os, signal, subprocess, sys
from pathlib import Path
top, group, name = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
if os.environ.get('V360_NATIVE'): (group / 'nested/cgroup.procs').write_text(str(os.getpid()))
child = subprocess.Popen([sys.executable, '-c', 'import signal; signal.pause()'], start_new_session=True)
(top / (name + '.pids')).write_text(json.dumps([os.getpid(), child.pid]))
(top / (name + '.ready')).write_text('1')
signal.pause()
"""
        worker = subprocess.Popen([sys.executable, '-c', program, str(top), str(group), group_name], start_new_session=True)
        ready = top / (group_name + '.ready')
        wait('worker and descendant running', ready.exists, sources=[PathAppears(ready)])
        pids.extend(json.loads((top / (group_name + '.pids')).read_text()))
    (top / 'mutation.pids').write_text(json.dumps(pids))
    (top / 'mutation.ready').write_text('1')
    signal.pause()
elif name == 'worker' and mode == 'sibling':
    client = s.Client()
    assert client.acquire('child', 0, 0)
    parent, child = socket.socketpair()
    program = r"""
import os, socket, sys
sock = socket.socket(fileno=int(sys.argv[1]))
if os.fork(): os._exit(0)
os.setsid()
sock.sendall(str(os.getpid()).encode() + b'\n')
assert sock.recv(1) == b'!'
sock.sendall(b'Y')
"""
    middle = subprocess.Popen([sys.executable, '-c', program, str(child.fileno())], pass_fds=(child.fileno(),))
    child.close()
    helper = int(parent.makefile('rb').readline())
    middle.wait()  # Adoption is complete before the other node may finish.
    assert int(Path('/proc/%d/stat' % helper).read_text().rsplit(')', 1)[1].split()[1]) == os.getppid()
    fd = os.pidfd_open(helper)
    (top / 'worker.pids').write_text(json.dumps([os.getpid(), helper]))
    (top / 'worker.ready').write_text('1')
    wait('other node collected', lambda: (top / 'red.settled').exists(), sources=[PathAppears(top / 'red.settled')])
    try:
        parent.sendall(b'!')
        survived = parent.recv(1) == b'Y'
    except (BrokenPipeError, ConnectionResetError):
        survived = False
    parent.close()
    poll = select.poll(); poll.register(fd, select.POLLIN); poll.poll(); os.close(fd)
    client.release('child'); client.close()
    (top / 'sibling.survived').write_text(str(survived))
    raise SystemExit(0 if survived else 8)
elif name == 'worker':
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
    ready = top / ('mutation.ready' if mode.startswith('mutation-') else 'worker.ready')
    wait('worker has a grant', ready.exists, sources=[PathAppears(ready)])
    if mode == 'mutation-exception': signal.pause()
    if mode == 'mutation-killed': os.kill(json.loads((top / 'mutation.pids').read_text())[0], signal.SIGKILL)
    (top / 'red.done').write_text('1')
    raise SystemExit(0 if mode in ('green', 'sibling') else 7)
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
                                    ('not-opted-in', 'early', 'true'),
                                    ('sibling', 'sibling', ''),
                                    ('mutation-cancel', 'mutation-cancel', ''),
                                    ('mutation-killed', 'mutation-killed', ''),
                                    ('mutation-exception', 'mutation-exception', '')):
            if mode == 'sibling' and not nonblocking:
                row('sibling-survives', False)
                continue
            top = base / tag
            top.mkdir()
            (top / 'stage.py').write_text(stage)
            nodes = {'worker': [], 'red': [], 'tail': [], 'load': ['red', 'worker', 'tail'],
                     'mutation': ['load'], 'after': ['mutation']}
            if mode == 'sibling':
                nodes = dict(worker=[], red=[])
            if mode.startswith('mutation-'):
                nodes = dict(mutation=[], red=[], worker=['mutation'], tail=['mutation'],
                             load=['red', 'worker', 'tail'], after=['mutation'])
            (top / 'graph.json').write_text(json.dumps(dict(schema='veldo.gate-graph/v1',
                nodes={n: dict(depends_on=d, writes_candidate=False, manager='none', ports=[],
                    estimate=dict(source='fixture', wall_seconds=1, cpu_seconds=1,
                                  peak_cgroup_memory_bytes=1024)) for n, d in nodes.items()},
                reserve=dict(cpu=0, memory=0), mutation_floor=dict(cpu=0, memory=0))))
            env = dict(os.environ, V360_SOURCE=str(source), V360_SCRIPTS=str(ROOT / 'scripts'), VELDO_GATE_COLLECT_ALL=setting, VELDO_GATE_SCOPE='/fixture360')
            proc = subprocess.run([sys.executable, str(base / 'wrapper.py'), str(source), str(top), mode],
                                  env=env, capture_output=True, text=True)
            receipt_path = top / 'out/receipt.json'
            if mode.startswith('mutation-'):
                receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
                pids = json.loads((top / 'mutation.pids').read_text()) if (top / 'mutation.pids').exists() else []
                releases = [json.loads(line) for line in (top / 'release-observations').read_text().splitlines()] if (top / 'release-observations').exists() else []
                row(mode + '/cleanup', len(pids) == 5 and all(not Path('/proc/%d' % p).exists() for p in pids)
                    and not list(top.glob('*.cgroup')) and not (top / 'unreaped').exists())
                row(mode + '/release-order', {r['name'] for r in releases} ==
                    {'mutation', 'mutation/child0', 'mutation/child1'} and all(r['gone'] and r['removed'] for r in releases))
                row(mode + '/status', proc.returncode == 1)
                row(mode + '/partial', (top / 'mutation.receipt').exists()
                    and json.loads((top / 'mutation.receipt').read_text()) == {'partial': 'preserved'})
                if mode == 'mutation-exception':
                    row(mode + '/exception', not receipt and 'fixture sampling failure' in proc.stdout)
                elif mode == 'mutation-cancel':
                    row(mode + '/first-red', (receipt.get('first_failure') or {}).get('node') == 'red'
                        and receipt['first_failure']['returncode'] == 7 and receipt['stages']['mutation'] == 'cancelled'
                        and not (top / 'rescued').exists())
                else:
                    row(mode + '/killed', receipt.get('stages', {}).get('mutation') == 'FAIL'
                        and receipt['nodes']['mutation']['returncode'] == -9)
                continue
            if not receipt_path.exists():
                print(proc.stdout, proc.stderr)
            receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
            if mode == 'sibling':
                row('sibling-survives', proc.returncode == 0
                    and receipt.get('stages') == dict(worker='pass', red='pass')
                    and (top / 'sibling.survived').read_text() == 'True'
                    and receipt['nodes']['red']['end'] < receipt['nodes']['worker']['end'])
                continue
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

    # Exercise each cleanup boundary without timeout-based rescue or host cgroups.
    from types import SimpleNamespace
    from unittest.mock import Mock

    calls = []
    # Paths sort deepest first; a non-directory must never be removed.
    class Entry:
        def __init__(self, name, is_directory): self.name, self.directory = name, is_directory
        def __lt__(self, other): return self.name < other.name
        def is_dir(self): return self.directory
        def rmdir(self): calls.append(self.name)
    group = Mock()
    group.rglob.return_value = [Entry('a-file', False), Entry('z-nested', True)]
    group.rmdir.side_effect = lambda: calls.append('parent')
    ownership = SimpleNamespace(wait_for_empty=lambda path: calls.append('kill-and-empty'))
    with patch.object(scheduler, 'load_module', return_value=ownership):
        scheduler.empty_group(group)
    row('empty-order', calls == ['kill-and-empty', 'z-nested', 'parent'])

    for name, scope, throws, label in (('mutation', '/owned', False, 'workers'),
                                       ('red', '/owned', False, 'foreign-stage'),
                                       ('mutation', '', False, 'absent-scope'),
                                       ('mutation', '/owned', True, 'metrics-error')):
        calls = []
        meter = Mock()
        def finish():
            calls.append('node')
            if throws: raise OSError('sample unavailable')
            return {'metric': 1}
        meter.finish.side_effect = finish
        # Use a real path expression only to check the selection, never the filesystem.
        from unittest.mock import MagicMock
        root = MagicMock()
        root.__truediv__.return_value = root
        root.glob.return_value = ['worker-one', 'worker-two']
        excluded = {123, 456}
        with patch.object(scheduler, 'Path', return_value=root), \
                patch.object(scheduler, 'empty_group', side_effect=lambda p: calls.append(p)), \
                patch.object(scheduler, 'reap_exited_children', side_effect=lambda e: calls.append(('reap', e))):
            result = None
            try:
                result = scheduler.finish_node(name, dict(meter=meter, proc=SimpleNamespace(pid=123)), scope, excluded)
            except OSError:
                result = 'error'
        workers = ['worker-one', 'worker-two'] if name == 'mutation' and scope else []
        row('cleanup-' + label, calls == ['node', *workers, ('reap', excluded)]
            and result == ('error' if throws else {'metric': 1})
            and (root.glob.call_args.args == ('worker-123-*',) if workers else not root.glob.called))

    calls = []
    with patch.object(scheduler, 'child_pids', side_effect=[{11, 99}, {22, 99}, {99}, set()]), \
            patch.object(scheduler.os, 'kill', side_effect=lambda pid, sig: calls.append(('kill', pid, sig))), \
            patch.object(scheduler.os, 'waitpid', side_effect=lambda pid, flags: calls.append(('wait', pid, flags))):
        scheduler.reap_children({99})
    row('reaper-kill-before-wait', calls == [('kill', 11, 9), ('wait', 11, 0), ('kill', 22, 9), ('wait', 22, 0)])
    for boundary, error in (('kill', ProcessLookupError), ('waitpid', ChildProcessError)):
        with patch.object(scheduler, 'child_pids', side_effect=[{11}, set()]), \
                patch.object(scheduler.os, 'kill') as kill, patch.object(scheduler.os, 'waitpid') as reap:
            (kill if boundary == 'kill' else reap).side_effect = error
            try:
                scheduler.reap_children()
                ok = True
            except error:
                ok = False
        row('reaper-race-' + boundary, ok and kill.called and reap.called)

    meter = scheduler.Meter.__new__(scheduler.Meter)
    meter.finished, meter.path = None, MagicMock()
    (meter.path / 'cgroup.events').read_text.return_value = 'populated 1'
    with patch.object(meter, 'sample', side_effect=OSError('sample unavailable')), \
            patch.object(scheduler, 'empty_group') as empty:
        try:
            meter.finish()
        except OSError:
            pass
        row('meter-error-cleanup', empty.call_args == ((meter.path,),))

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
