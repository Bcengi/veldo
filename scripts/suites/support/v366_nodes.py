"""Directory nodes, stub streams and idle children; never a native gate or suite fixture."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import types
from unittest.mock import patch


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def specimen(gate, shards):
    cases = [dict(identity='driver:c%d' % n, name='c%d' % n, driver=gate.DRIVERS[0],
                  finding=366, suite='group%d.py' % (n // 2), module='subject.py',
                  old='before', new='after', rows=['target']) for n in range(4)]
    request = dict(head='a' * 40, input_digest='inputs', inventory_digest=shards.digest(cases), session='nonce')
    checks = {n: dict(passed=True, evidence='fixture only') for n in
              ('delegation', 'landlock', 'namespaces', 'ptrace', 'pidfds', 'toolchain')}
    checks['namespaces']['no_network'] = True
    capacity = dict(cpu=8, memory=15 * 2**30, manager=16)
    quals = {h: shards.qualification(request, h, capacity, checks) for h in ('local', 'pc2')}
    tasks = {h: shards.assignment(request, h, cases[i:i+2], quals[h]) for h, i in (('local', 0), ('pc2', 2))}
    keys = dict(local=b'l' * 32, pc2=b'r' * 32)
    envelopes = {}
    for host, task in tasks.items():
        records = []
        def observation(ok):
            return dict(count=1, observations=[['fixture target', ok]], row_names=['fixture target'],
                        failed_rows=[] if ok else ['fixture target'])
        for case in task['cases']:
            record = dict(schema=gate.SCHEMA, case=case, fixture_version=gate.FIXTURE_VERSION,
                          baseline=observation(True), noop=observation(True), mutant=observation(False),
                          replacement_count=1, old_digest='old', new_digest='new', source='fresh')
            gate.validate_result(record, case)
            records.append(record)
        outcomes = [dict(name=c['identity'], mode='mutant', scratch_removed=True, elapsed=1) for c in task['cases']]
        outcomes += [dict(name=gate.control_group(task['cases'][0])+':'+m, mode=m, scratch_removed=True, elapsed=1)
                     for m in ('baseline', 'noop')]
        stage = dict(status='passed', results=records, registered=2, executed=2, rejected=2, reused=0,
                     input_digest='inputs', force_fresh=True, no_network=True, invalid_results=[], surviving_workers=0,
                     case_receipts=[dict(identity=c['identity'], validated=True, source='fresh') for c in task['cases']],
                     worker_outcomes=outcomes, worker_invocations=4, elapsed=3)
        envelopes[host] = shards.seal(keys[host], shards.result_body(task, quals[host], stage, True))
    return cases, request, quals, tasks, keys, envelopes


def checks(gate, shards, transport, root, expect, worker=None):
    def row(name, value):
        expect('VELDO-0366 shards/' + name, bool(value))
    def refuses(action):
        try:
            action()
        except (shards.Refused, gate.Refused, ValueError, KeyError, TypeError, RuntimeError):
            return True
        return False
    cases, request, quals, tasks, keys, envelopes = specimen(gate, shards)
    def aggregate(values=envelopes, assignments=tasks):
        return shards.aggregate(gate, cases, assignments, quals, values, keys, request)
    row('identity-multiset', all(refuses(lambda actual=actual: shards.exact(['a','b'], actual, 'fixture'))
        for actual in (['a'], ['a','a'], ['a','b','foreign'])))
    good = aggregate()
    row('full-cover', good['status'] == 'passed' and good['registered'] == good['executed'] == 4
        and good['scope'] == 'full' and len(good['results']) == 4 and not good['force_fresh'])
    row('missing-shard', refuses(lambda: aggregate({'local': envelopes['local']})))
    row('foreign-shard', refuses(lambda: aggregate(dict(envelopes, intruder=envelopes['pc2']))))
    for name, change in (
        ('missing-result', lambda b: b['stage']['results'].pop()),
        ('duplicate-result', lambda b: b['stage']['results'].append(copy.deepcopy(b['stage']['results'][0]))),
        ('foreign-result', lambda b: b['stage']['results'][0]['case'].update(identity='foreign')),
        ('failed-shard', lambda b: b['stage'].update(status='failed')),
        ('cancelled-shard', lambda b: b['stage'].update(status='cancelled')),
        ('survivor', lambda b: b['stage']['results'][0]['mutant'].update(
            observations=[['fixture target', True]], failed_rows=[])),
        ('control-failed', lambda b: b['stage']['results'][0]['baseline'].update(
            observations=[['fixture target', False]], failed_rows=['fixture target'])),
        ('input-mismatch', lambda b: b['stage'].update(input_digest='other')),
        ('runtime-mismatch', lambda b: b.update(runtime_digest='other')),
        ('network-boundary', lambda b: b['stage'].update(no_network=False)),
        ('assignment-mismatch', lambda b: b.update(assignment_digest='other')),
        ('cleanup-failed', lambda b: b.update(cleaned=False)),
        ('scratch-survived', lambda b: b['stage']['worker_outcomes'][0].update(scratch_removed=False)),
        ('worker-survived', lambda b: b['stage'].update(surviving_workers=1)),
        ('pending-result', lambda b: b['stage']['case_receipts'][0].update(validated=False)),
        ('missing-case-receipt', lambda b: b['stage']['case_receipts'].pop()),
        ('reused-result', lambda b: b['stage'].update(reused=1)),
        ('count-mismatch', lambda b: b['stage'].update(registered=1)),
    ):
        bad = copy.deepcopy(envelopes)
        change(bad['pc2']['body'])
        bad['pc2'] = shards.seal(keys['pc2'], bad['pc2']['body'])
        row(name, refuses(lambda: aggregate(bad)))
    bad = copy.deepcopy(envelopes)
    bad['pc2']['body']['cleaned'] = False
    row('forged-receipt', refuses(lambda: shards.open_receipt(keys['pc2'], bad['pc2'])))
    row('wrong-key', refuses(lambda: shards.open_receipt(b'z'*32, envelopes['pc2'])))
    bad = copy.deepcopy(envelopes)
    bad['pc2']['body']['request']['session'] = 'old nonce'
    bad['pc2'] = shards.seal(keys['pc2'], bad['pc2']['body'])
    row('replayed-receipt', refuses(lambda: aggregate(bad)))
    for name, change in (
        ('duplicate-assignment', lambda a: a['pc2']['cases'].append(a['local']['cases'][0])),
        ('missing-assignment', lambda a: a['pc2']['cases'].pop()),
        ('changed-definition', lambda a: a['pc2']['cases'][0].update(rows=['weaker'])),
    ):
        bad = copy.deepcopy(tasks)
        change(bad)
        row(name, refuses(lambda: aggregate(assignments=bad)))
    row('runtime-race', shards.runtime_matches(quals['pc2'], 'fixture only')
        and not shards.runtime_matches(quals['pc2'], 'changed runtime'))
    row('qualified', shards.admit(request, 'pc2', quals['pc2']) == quals['pc2'])
    outcomes = []
    for field in quals['pc2']['checks']:
        for missing in (True, False):
            bad = copy.deepcopy(quals['pc2'])
            if missing:
                del bad['checks'][field]
            else:
                bad['checks'][field]['passed'] = False
            bad['runtime_digest'] = shards.digest(bad['checks'])
            outcomes.append(refuses(lambda: shards.admit(request, 'pc2', bad)))
    row('unqualified-host', all(outcomes))
    bad_network = copy.deepcopy(quals['pc2'])
    bad_network['checks']['namespaces']['no_network'] = False
    bad_network['runtime_digest'] = shards.digest(bad_network['checks'])
    row('qualification-network', refuses(lambda: shards.admit(request, 'pc2', bad_network)))
    row('qualification-replay', refuses(lambda: shards.admit(dict(request, session='other'), 'pc2', quals['pc2'])))
    row('qualification-host', refuses(lambda: shards.admit(request, 'foreign', quals['pc2'])))
    with patch.object(shards, 'binding', return_value=dict(head=request['head'],input_digest='inputs')), \
            patch.object(gate, 'inventory', return_value=cases):
        shards.validate_assignment(gate, root, root, tasks['pc2'], quals['pc2'])
        split = copy.deepcopy(tasks['pc2']); split['cases'].pop()
        row('split-assignment-refused', refuses(lambda: shards.validate_assignment(gate, root, root, split, quals['pc2'])))
        changed = copy.deepcopy(tasks['pc2']); changed['cases'][0]['rows'] = ['weaker']
        row('definition-refused', refuses(lambda: shards.validate_assignment(gate, root, root, changed, quals['pc2'])))
    with patch.object(gate, 'read_inputs', return_value={}), patch.object(gate, 'git', side_effect=['a'*40,' M changed']):
        row('dirty-inputs-refused', refuses(lambda: shards.binding(gate, root, root)))
    capacity = dict(local=dict(cpu=8), pc2=dict(cpu=8))
    history = {c['identity']: dict(seconds=100 if c['suite']=='group0.py' else 1) for c in cases}
    assignments, costs = shards.plan(gate, cases, capacity, history, None, ['group0.py', 'group1.py'])
    row('group-cost-balance', sorted(map(len, assignments.values())) == [2, 2]
        and max(costs.values()) == 400 and min(costs.values()) == 4)
    row('controls-together', all(len({h for h, members in assignments.items() if c in members}) == 1 for c in cases)
        and all(len({gate.control_group(c) for c in members}) == 1 for members in assignments.values()))
    local_only, _ = shards.plan(gate, cases, capacity, history, None, [])
    row('native-declaration', len(local_only['local']) == 4 and not local_only['pc2'])
    with patch.object(gate, 'in_leg', return_value=True):
        confined, _ = shards.plan(gate, cases, capacity, history, None, ['group0.py', 'group1.py'])
    row('unconfined-local', len(confined['local']) == 4 and not confined['pc2'])
    scheduler = load(root / 'scripts/gate_schedule.py')
    with contextlib.redirect_stdout(io.StringIO()):
        first = scheduler.Ledger(dict(cpu=8, memory=15*2**30, manager=16))
        second = scheduler.Ledger(dict(cpu=8, memory=15*2**30, manager=16))
        claim = dict(cpu=1, memory=1, manager='exclusive', ports=[12345])
        a = first.acquire('a', claim)
        b = not first.acquire('b', claim)
        c = second.acquire('c', claim)
        first.release('a')
        second.release('c')
        port = dict(claim, manager='none')
        port_ok = first.acquire('port1', port) and not first.acquire('port2', port)
        first.release('port1')
    row('per-host-exclusions', a and b and c and port_ok and not first.held and not second.held)
    # Reuse the event-driven Workers double: actual control validation and dependency release,
    # with no native worker, process tree, manager or nested gate fixture.
    early = load(root / 'scripts/suites/support/v363_early.py')
    replay, launches, finishes = early.drive(gate)
    first = next(t for _, mode, t in launches if mode == 'mutant')
    row('early-release-retained', replay['status'] == 'passed' and first == 1
        and first < max(t for _, mode, t, _ in finishes if mode != 'mutant'))
    failed, launches, finishes = early.drive(gate, fault='survivor')
    row('fail-fast-retained', failed['status'] == 'failed' and failed['error'] == 'mutation_survived'
        and any(o.get('error') == 'worker_cancelled' for o in failed['worker_outcomes'])
        and not any(n == 'g2-c0' for n, mode, t in launches if mode == 'mutant'))
    # Direct production supervisor, with a directory-backed host and idle child substitutions.
    directory_node(transport, root, row)
    coordinator_stub(gate, shards, root, row)
    bundle_node(transport, row)
    network_checks(transport, root, row)
    worker_checks(worker or load(root/"scripts/reuse_worker.py"), row)


def coordinator_stub(gate, shards, root, row):
    cases, request, quals, tasks, keys, envelopes = specimen(gate, shards)
    old = shards.ROOT
    with tempfile.TemporaryDirectory(prefix='v366-directory-') as directory:
        top = Path(directory)
        (top / 'scripts').mkdir()
        (top / 'scripts/mutation_hosts.json').write_text(json.dumps(dict(schema='veldo.mutation-hosts/v1',
            hosts=[dict(name='pc2', ssh='stub')], remote_suites=['group0.py', 'group1.py'])))
        (top / 'scripts/gate_graph.json').write_text((root / 'scripts/gate_graph.json').read_text())
        closed, dispatched = [], []
        actual_load = shards.load
        host = types.SimpleNamespace(load=lambda: {}, inside=lambda c: dict(held=True), SCOPE_ENV='FAKE_SCOPE')
        scheduler = types.SimpleNamespace(CHANNEL='FAKE_LEDGER', capacities=lambda *a: dict(cpu=8,memory=15*2**30,manager=16))
        def loader(name):
            return {'gate_host':host, 'gate_schedule':scheduler}.get(name) or load(root / 'scripts' / (name+'.py'))
        for failure in ('unqualified', 'unreachable', 'failure', 'disconnect', 'duplicate', 'green', 'collect-all'):
            closed.clear(); dispatched.clear()
            class StubNode:
                def __init__(self, root, entry, request, key):
                    self.name, self.request, self.key = entry['name'], request, key
                    if failure == 'unreachable':
                        raise RuntimeError('unreachable fixture host')
                def qualify(self):
                    q = copy.deepcopy(quals['pc2']); q['request'] = self.request
                    if failure == 'unqualified':
                        q['checks']['toolchain']['passed'] = False
                        q['runtime_digest'] = shards.digest(q['checks'])
                    return shards.seal(self.key, q)
                def dispatch(self, task, qualified):
                    self.task, self.qualified = task, qualified
                    dispatched.append(self.name)
                def close(self):
                    closed.append(self.name)
            class StubLocal(StubNode):
                def __init__(self, root, request, key):
                    self.name, self.request, self.key = 'local', request, key
            def completed(nodes):
                if failure == 'disconnect':
                    raise RuntimeError('disconnect mid-run')
                for name, n in nodes.items():
                    members = n.task['cases']
                    own = 'local' if members[0]['identity']=='driver:c0' else 'pc2'
                    stage = copy.deepcopy(envelopes[own]['body']['stage'])
                    stage['input_digest'] = n.request['input_digest']
                    if failure in ('failure', 'collect-all') and name == 'pc2':
                        stage['status'] = 'failed'
                    envelope = shards.seal(n.key, shards.result_body(n.task, n.qualified, stage, True))
                    yield name, envelope
                    if failure == 'duplicate':
                        yield name, envelope
            fake_transport = types.SimpleNamespace(SSHNode=StubNode, LocalNode=StubLocal, completed=completed)
            with patch.object(shards, 'ROOT', top), patch.object(shards, 'load', loader), \
                    patch.object(shards, 'binding', return_value=dict(head=request['head'],input_digest='inputs')), \
                    patch.object(gate, 'inventory', return_value=cases), \
                    patch.object(gate, 'common_directory', return_value=top), \
                    patch.object(gate, 'order_history', return_value={}), \
                    patch.dict(os.environ, dict(FAKE_SCOPE='fixture', FAKE_LEDGER='fixture',
                         VELDO_GATE_COLLECT_ALL='1' if failure == 'collect-all' else '0')):
                result = shards.coordinate(gate, top, top, None, fake_transport)
            row('coordinator-'+failure, (result['status']=='passed') == (failure=='green')
                and (not dispatched if failure in ('unqualified','unreachable') else set(closed)=={'local','pc2'}))
    assert shards.ROOT == old


def directory_node(transport, root, row):
    with tempfile.TemporaryDirectory(prefix='v366-node-') as directory:
        top = Path(directory)
        ready_read, ready_write = os.pipe()
        command = [sys.executable, '-B', str(Path(__file__)), '--service', str(root), str(top), str(ready_write)]
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   pass_fds=(ready_write,))
        os.close(ready_write)
        try:
            transport.send(process.stdin, dict(key=(b'x'*32).hex(), request=dict(session='fixture'), host='fake'))
            qualified = transport.receive(process.stdout)
            transport.send(process.stdin, dict(task={'fixture': True}, qualified=qualified['body']))
            # The child emits a pipe event only after its scratch and descendant exist.
            with os.fdopen(ready_read, 'rb') as ready:
                running = transport.receive(ready)
            pid = running['descendant']
            process.stdin.close()
            process.stdin = None
            output, errors = process.communicate()
            row('disconnect-mid-run', process.returncode != 0 and b'disconnected' in errors)
            row('cancellation-pipe-drained', (top/'flushed').exists())
            row('disconnect-cleanup', (top/'cleaned').exists() and not (top/'work').exists()
                and not Path('/proc/%d' % pid).exists())
            import fcntl
            with (top/'host.lock').open('a') as handle:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                row('disconnect-lock-release', True)
        finally:
            transport.terminate(process)
            if process.stderr and not process.stderr.closed:
                detail = process.stderr.read()
                if detail:
                    print(detail.decode(), file=sys.stderr)


def service(root, top, ready_fd):
    transport = load(root / 'scripts/mutation_transport.py')
    shards = load(root / 'scripts/mutation_shards.py')
    real_popen, real_load = subprocess.Popen, transport.load
    child = [None]
    def popen(argv, **kwargs):
        if '--node' in argv:
            argv = [sys.executable, '-B', __file__, '--idle', str(top), argv[-2], str(ready_fd)]
            kwargs['pass_fds'] = (*kwargs['pass_fds'], ready_fd)
        child[0] = real_popen(argv, **kwargs)
        return child[0]
    def cleanup(state):
        (top/'cleaned').write_text('scope cleanup called')
    fake_host = types.SimpleNamespace(load=lambda: dict(lock=str(top/'host.lock')), stop_scope=cleanup)
    transport.load = lambda name: fake_host if name=='gate_host' else shards if name=='mutation_shards' else real_load(name)
    transport.ROOT = top/'tree'
    transport.PROTOCOL = sys.stdout.buffer
    with patch.object(transport.subprocess, 'Popen', popen):
        transport.serve()


def idle(top, state, ready_fd):
    transport = load(Path(__file__).resolve().parents[2] / 'mutation_transport.py')
    transport.install_signals()
    descendant = None
    work = top/'work'
    try:
        hello = transport.receive(sys.stdin.buffer)
        state.write_text('{}')
        transport.send(sys.stdout.buffer, dict(request=hello['request'], host=hello['host']))
        transport.receive(sys.stdin.buffer)
        work.mkdir()
        descendant = subprocess.Popen([sys.executable, '-I', '-S', '-c', 'import sys; print("ready",flush=True); sys.stdin.read()'],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        assert descendant.stdout.readline() == b'ready\n'
        with os.fdopen(ready_fd, 'wb') as ready:
            transport.send(ready, dict(descendant=descendant.pid))
        sys.stdin.buffer.read()
    finally:
        if descendant:
            transport.terminate(descendant)
            descendant.stdin.close(); descendant.stdout.close()
        if work.exists():
            work.rmdir()
        transport.send(sys.stdout.buffer, dict(cancelled=True, partial='x'*(128*1024)))
        (top/'flushed').write_text('partial receipt drained')


def bundle_node(transport, row):
    # A tiny committed directory node exercises the real shipping bootstrap. No gate code runs.
    with tempfile.TemporaryDirectory(prefix='v366-source-') as directory:
        root = Path(directory)
        (root/'scripts').mkdir()
        program = root/'scripts/mutation_transport.py'
        program.write_text('import json,pathlib\np=pathlib.Path(__file__).resolve()\n'
                           'print(json.dumps(dict(value="committed", scratch=str(p.parents[2]))),flush=True)\n')
        env = dict(os.environ, GIT_AUTHOR_NAME='Dmitry Grinberg', GIT_COMMITTER_NAME='Dmitry Grinberg',
                   GIT_AUTHOR_EMAIL='dmitry@example.com', GIT_COMMITTER_EMAIL='dmitry@example.com')
        def git(*args):
            return subprocess.run(['git','-C',str(root),'-c','core.hooksPath=/dev/null',*args],
                check=True,capture_output=True,env=env).stdout
        git('init','-q'); git('add','scripts/mutation_transport.py')
        git('commit','-q','-m','Directory transport fixture')
        head = git('rev-parse','HEAD').decode().strip()
        bundle = root/'source.bundle'
        git('bundle','create',str(bundle),'HEAD')
        program.write_text('raise RuntimeError("dirty bytes must never travel")\n')
        payload = json.dumps(dict(head=head,size=bundle.stat().st_size)).encode()+b'\n'+bundle.read_bytes()
        result = subprocess.run([sys.executable,'-I','-S','-c',transport.BOOTSTRAP], input=payload,
                                capture_output=True)
        packet = json.loads(result.stdout) if result.returncode == 0 else {}
        row('committed-clean-transport', result.returncode == 0 and packet.get('value') == 'committed')
        row('transport-tree-cleanup', bool(packet) and not Path(packet['scratch']).exists())
        truncated = subprocess.run([sys.executable,'-I','-S','-c',transport.BOOTSTRAP], input=payload[:-10],
                                  capture_output=True)
        row('truncated-bundle', truncated.returncode != 0 and b'truncated bundle' in truncated.stderr)


def network_checks(transport, root, row):
    def evaluate(number, family, arch=0xc000003e):
        code, index, value = transport.network_program(), 0, 0
        while index < len(code):
            op, yes, no, operand = code[index]
            if op == 0x20:
                value = {0:number, 4:arch, 16:family}[operand]
            elif op in (0x15, 0x35):
                match = value == operand if op == 0x15 else value >= operand
                index += yes if match else no
            elif op == 0x06:
                return operand
            else:
                raise AssertionError('unexpected filter opcode')
            index += 1
        raise AssertionError('filter fell through')
    allow = 0x7fff0000
    row('no-network-filter', all(evaluate(n, family) != allow for n in (41,53)
        for family in (2,10,16,17,40)) and evaluate(41,2,0) != allow
        and evaluate(0x40000029,2) != allow)
    row('scratch-unix-retained', all(evaluate(n,1) == allow for n in (41,53,42)))
    sandbox = load(root/'scripts/mutation_sandbox.py')
    fake = types.SimpleNamespace(READ=4, WRITE=2, installed_tools=lambda c: [],
        policy_module=lambda: types.SimpleNamespace(configuration=lambda p: (None,{})),
        toolchain_environment=lambda *a: None, FIXTURES=types.SimpleNamespace(ENVIRONMENT={}))
    with tempfile.TemporaryDirectory(prefix='v366-grants-') as directory:
        top = Path(directory)
        grants = sandbox.worker_grants(fake, top/'authority', top/'input', top/'scratch', None)
        exposed = [p for p, _ in grants]
        row('worker-store-separation', top/'authority' not in exposed and top/'store' not in exposed
            and top/'key' not in exposed and top/'input' in exposed and top/'scratch' in exposed)


def worker_checks(worker, row):
    with tempfile.TemporaryDirectory(prefix='v366-worker-') as directory:
        top = Path(directory)
        jobpath = top/'job.json'
        jobpath.write_text(json.dumps(dict(no_network=True)))
        events = []
        boundary = types.SimpleNamespace(close_descriptors=lambda *a,**k: events.append('descriptors'),
                                         launcher_fds=lambda: ())
        sandbox = types.SimpleNamespace(confine_in_tree=lambda *a,**k: events.append('confined'))
        network = types.SimpleNamespace(deny_network=lambda b: events.append('no-network'))
        ownership = types.SimpleNamespace(Tracker=lambda *a: types.SimpleNamespace(install=lambda: None))
        modules = dict(agent_sandbox=boundary, mutation_sandbox=sandbox, mutation_transport=network,
                       check_gate_mutations=types.SimpleNamespace(), mutation_observer=types.SimpleNamespace(),
                       mutation_ownership=ownership)
        fd = os.open(top/'ledger',os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
        try:
            with patch.object(worker, 'load', lambda path: modules[path.stem]), \
                    patch.object(worker, 'join_worker_cgroup', lambda: None), \
                    patch.object(worker, 'observe', lambda *a: events.append('candidate')), \
                    patch.object(sys, 'argv', ['worker','tree',str(top),str(fd),str(jobpath)]), \
                    patch.dict(os.environ, dict(TMPDIR=str(top))):
                worker.main()
                row('worker-network-before-code', events == ['descriptors','confined','no-network','candidate'])
                events.clear()
                sys.argv[1] = 'unconfined'
                try:
                    worker.main()
                except ValueError:
                    row('worker-unconfined-refused', 'candidate' not in events)
                else:
                    row('worker-unconfined-refused', False)
        finally:
            os.close(fd)


if __name__ == '__main__':
    if sys.argv[1]=='--service':
        service(Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4]))
    elif sys.argv[1]=='--idle':
        idle(Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4]))
