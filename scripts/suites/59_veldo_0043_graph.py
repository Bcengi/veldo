"""VELDO-0043: the plain-data graph adapter boundary and isolated stdlib enforcement.

Only ROOT and expect come from shared.py. Production modules are copied from the literal
anchors below, which are also the mutation harness's production seam.

WHAT THIS SUITE DOES NOT PROVE. AC1 and AC2 require the actual installed LangGraph runtime.
It is not installed: its dependency closure conflicts with the owner's C16 dependency rule and
needs an owner decision (proof/VELDO-0043/README.md). The graph/shape/* and graph/boundary/*
rows use a deterministic stdlib stub runner and check SHAPES and the process boundary only,
which the specification permits and which is not runtime evidence for AC1 or AC2.
"""
import importlib.util as _s43_ilu
import json as _s43_json
import os as _s43_os
from pathlib import Path as _s43_Path
import shutil as _s43_shutil
import subprocess as _s43_sp
import sys as _s43_sys
import tempfile as _s43_temp
import time as _s43_time


def _s43_load(name, path):
    spec = _s43_ilu.spec_from_file_location(name, path)
    mod = _s43_ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_S43_STUB = r'''
import json, os, sys
request = json.loads(sys.stdin.buffer.read())
mode = request['workflow']['id']
reply = {k: request[k] for k in ('schema', 'operation', 'cycle_id', 'command_id',
                                  'domain_uuid', 'repository_uuid')}
reply['runtime'] = {'name': 'interface-stub', 'version': '0'}
if request['operation'] == 'cancel':
    reply['outcome'] = 'canceled'
elif request['operation'] == 'suspend':
    reply.update(outcome='suspended', resume=request['resume'])
elif mode == 'lifecycle' and request['operation'] == 'start':
    reply.update(outcome='suspended', resume={'position': 'await-results', 'step': 1})
elif mode == 'lifecycle':
    reply.update(outcome='proposal', proposals=[
        {'type': 'priority', 'proposal_id': 'p1', 'subject': 'unit-1',
         'priority': request['supplied_results'][0]['rank']}])
elif mode == 'failure':
    reply.update(outcome='failure', failure={'code': 'node_failed', 'detail': 'stub node failed'})
elif mode == 'foreign':
    reply.update(outcome='proposal', proposals=[{'type': 'priority', 'proposal_id': 'p1',
                 'subject': 'unit-1', 'priority': 1, '__class__': 'Command'}])
elif mode == 'untyped':
    reply.update(outcome='proposal', proposals=[{'proposal_id': 'p1', 'subject': 'unit-1',
                 'priority': 1}])
elif mode == 'environment':
    reply.update(outcome='suspended', resume={
        'environment': sorted(os.environ), 'cwd_entries': sorted(os.listdir('.')),
        'descriptors': sorted(int(fd) for fd in os.listdir('/proc/self/fd')),
        'argv': sys.argv, 'request_text': json.dumps(request, sort_keys=True)})
elif mode == 'crash':
    sys.exit(3)
sys.stdout.write(json.dumps(reply))
'''


def _s43_run():
    started = _s43_time.monotonic()
    observations = {}
    with _s43_temp.TemporaryDirectory(prefix='graph-43-') as temporary:
        root = _s43_Path(temporary)
        # An installed repository laid by the real scaffolder, then the production copies.
        repo = root / 'installed'
        laid = _s43_sp.run([_s43_sys.executable, '-B', str(ROOT / '.veldo/init_scaffold.py'), str(repo)],
                           capture_output=True, text=True, timeout=60)
        for name, source in {
            'control_graph.py': ROOT / ".veldo" / "control_graph.py",
            'control_graph_isolation.py': ROOT / ".veldo" / "control_graph_isolation.py",
            'authorization.py': ROOT / ".veldo" / "authorization.py",
            'two_key.py': ROOT / '.veldo/two_key.py',
            'request.py': ROOT / '.veldo/request.py',
        }.items():
            _s43_shutil.copyfile(source, repo / '.veldo' / name)
        graph = _s43_load('s43_graph', repo / '.veldo/control_graph.py')
        scaffold = _s43_load('s43_scaffold', ROOT / '.veldo/init_scaffold.py')
        expect('graph/installed-assets', laid.returncode == 0 and all(
               '.veldo/' + name in scaffold._FILES for name in ('control_graph.py', 'control_graph_isolation.py')))

        # AC3: every installed enforcement entry, run with the execution environment absent.
        isolated = _s43_sp.run([_s43_sys.executable, '-B', str(repo / '.veldo/control_graph_isolation.py'),
                                '--root', str(repo)], capture_output=True, text=True, timeout=120)
        try:
            verdict = _s43_json.loads(isolated.stdout.rsplit('\n', 2)[0])
        except ValueError:
            verdict = {'passed': None, 'entries': []}
        observations['isolated'] = {'returncode': isolated.returncode, 'verdict': verdict}
        statuses = {entry['entry']: entry['status'] for entry in verdict.get('entries', [])}
        expect('graph/isolated-enforcement', isolated.returncode == 0 and verdict.get('passed') is True
               and statuses == {name: 'pass' for name in ('validator', 'shape_gate', 'policy_check',
                                                            'authorization', 'version', 'graph_start')}
               and all(not entry['refused_imports'] and not entry['static_violations']
                       for entry in verdict['entries']))

        # AC3: graph start with no runtime, and with an absent interpreter, is a named refusal.
        version = {'id': 'lifecycle', 'version': 1, 'digest': 'sha256:' + 'a' * 64}
        snapshot = {'id': 'snapshot-1', 'version': 1, 'digest': 'sha256:' + 'b' * 64}
        refusals = []
        adapter = graph.Adapter(None, 'domain', 'repository')
        for runtime in (None, {'python': str(root / 'absent/bin/python'), 'runner': str(root / 'absent.py')}):
            adapter.runtime = runtime
            try:
                adapter.start('cycle-0', 'command-0', snapshot, version)
                refusals.append('success')
            except Exception as error:  # a crash is recorded as a wrong answer, never raised
                refusals.append(getattr(error, 'code', type(error).__name__))
        observations['unavailable'] = refusals
        expect('graph/start-unavailable', refusals == ['runtime_unavailable', 'runtime_unavailable']
               and adapter.counts == {'accepted': 0, 'refused': 2} and adapter.pending() == []
               and [o['refusal'] for o in adapter.observations] == refusals)

        # Shape-only rows against a deterministic stub runner (not AC1/AC2 runtime evidence).
        stub = root / 'stub_runner.py'
        stub.write_text(_S43_STUB)
        adapter = graph.Adapter({'python': _s43_sys.executable, 'runner': str(stub)}, 'domain', 'repository')
        started_cycle = adapter.start('cycle-1', 'command-1', snapshot, version)
        pending = adapter.pending()
        suspended = adapter.suspend('cycle-1', 'command-2', version, started_cycle['resume'])
        advanced = adapter.advance('cycle-1', 'command-3', snapshot, version, suspended['resume'], [{'rank': 2}])
        adapter.start('cycle-2', 'command-4', snapshot, version)
        canceled = adapter.cancel('cycle-2', 'command-5', version, {'position': 'await-results'})
        failed = adapter.start('cycle-3', 'command-6', snapshot, dict(version, id='failure'))
        expect('graph/shape/lifecycle', started_cycle['outcome'] == 'suspended' and pending == ['cycle-1']
               and suspended['resume'] == started_cycle['resume'] and advanced['outcome'] == 'proposal'
               and advanced['proposals'] == [{'type': 'priority', 'proposal_id': 'p1', 'subject': 'unit-1',
                                               'priority': 2}]
               and canceled['outcome'] == 'canceled' and failed['failure']['code'] == 'node_failed'
               and adapter.pending() == [] and adapter.counts == {'accepted': 6, 'refused': 0}
               and adapter.observations[0]['accepted_inputs'] == {'snapshot': snapshot, 'workflow': version})
        shaped = []
        for mode in ('foreign', 'untyped', 'crash'):
            try:
                adapter.start('cycle-' + mode, 'command-' + mode, snapshot, dict(version, id=mode))
                shaped.append('success')
            except Exception as error:
                shaped.append(getattr(error, 'code', type(error).__name__))
        observations['shape_refusals'] = shaped

        class _Mapping(dict):
            pass
        plain = []
        for value in (_Mapping(a=1), {'a': object()}, {'a': float('nan')}, {1: 'x'}):
            try:
                graph.plain(value)
                plain.append('accepted')
            except Exception as error:
                plain.append(getattr(error, 'code', type(error).__name__))
        accepted_plain = graph.plain({'a': [1, 2.5, True, None, {'b': 'c'}]}) == {'a': [1, 2.5, True, None, {'b': 'c'}]}
        expect('graph/shape/plain-data', shaped == ['invalid_response', 'invalid_response', 'unknown_outcome']
               and plain == ['invalid_response'] * 4 and accepted_plain)

        # The process boundary: nothing inherited, including a real open store handle.
        store = _s43_load('s43_store', ROOT / '.veldo/control_store.py')
        store_path = root / 'authority' / 'control.sqlite3'
        store_path.parent.mkdir()
        connection = store.open_store(store_path)
        handle = _s43_os.open(store_path, _s43_os.O_RDONLY)
        _s43_os.set_inheritable(handle, True)
        environment = adapter.start('cycle-4', 'command-7', snapshot, dict(version, id='environment'))['resume']
        _s43_os.close(handle)
        connection.close()
        observations['boundary'] = {k: environment[k] for k in ('environment', 'cwd_entries', 'descriptors')}
        observations['boundary']['store_descriptor'] = handle
        expect('graph/boundary/no-store-handle', environment['environment'] == sorted(graph.ENVIRONMENT)
               and environment['cwd_entries'] == [] and environment['descriptors'][:3] == [0, 1, 2]
               and len(environment['descriptors']) <= 4 and handle not in environment['descriptors']
               and str(store_path.parent) not in environment['request_text']
               and not any(str(store_path.parent) in arg for arg in environment['argv']))
    observations['elapsed_seconds'] = _s43_time.monotonic() - started
    return observations


_s43_observations = _s43_run()
