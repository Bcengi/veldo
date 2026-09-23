"""VELDO-0043: the plain-data graph adapter boundary and isolated stdlib enforcement.

Only ROOT and expect come from shared.py. Production modules are copied from the literal
anchors below, which are also the mutation harness's production seam.

The graph/shape/* and graph/boundary/* rows use a deterministic stdlib stub runner and check
SHAPES and the process boundary only. The graph/runtime/* and graph/authority/* rows are the AC1
and AC2 runtime evidence: they run the actual LangGraph installed from control_graph_lock.py at
<passwd home>/.local/share/veldo/langgraph/<lock digest>/, through the production adapter and the
production runner, with the suite's own workflows registered through the runner's serve().
When that runtime is absent every runtime row FAILS BY NAME, with the install command in its
message; the suite never skips them and never installs anything.
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
elif mode == 'deep':
    reply.update(outcome='suspended', resume='HOLE')
    sys.stdout.write(json.dumps(reply).replace('"HOLE"', '{"n":' * 20000 + '0' + '}' * 20000))
    sys.exit(0)
sys.stdout.write(json.dumps(reply))
'''


# The suite's workflows, registered through the PRODUCTION runner's serve() and run by the actual
# LangGraph in the locked runtime. The audit hook records every network egress event (name
# resolution, connect, send; urllib3's import-time loopback IPv6 probe is a bind, not egress),
# refuses it so nothing is ever sent even under a tracing mutant, and,
# after the answer, the tracing switches and langsmith's own tracing verdict, one line per runner
# process.
_S43_RUNNER = r'''
import importlib.util, json, os, sqlite3, sys
from pathlib import Path
SOCKETS = []
EGRESS = ('socket.connect', 'socket.getaddrinfo', 'socket.gethostbyname', 'socket.gethostbyname_ex',
          'socket.gethostbyaddr', 'socket.sendto', 'socket.sendmsg')



def egress(event, args):
    # Recorded, then refused: no packet leaves this machine even when a mutant turns tracing on.
    if event in EGRESS:
        SOCKETS.append(event)
        raise ConnectionRefusedError('network egress refused by the VELDO-0043 suite: ' + event)


sys.addaudithook(egress)
spec = importlib.util.spec_from_file_location('veldo_graph_runner', PRODUCTION)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
from langgraph.types import Command, StateSnapshot
SWITCHES = ('LANGSMITH_TRACING', 'LANGSMITH_TRACING_V2', 'LANGCHAIN_TRACING', 'LANGCHAIN_TRACING_V2')


def audit():
    import langsmith.utils
    with open(AUDIT, 'a') as log:
        log.write(json.dumps({'switches': {k: os.environ.get(k) for k in SWITCHES},
                              'tracing': langsmith.utils.tracing_is_enabled(),
                              'sockets': sorted(set(SOCKETS))}) + '\n')



def groom(view):
    return {'next': 'size', 'notes': {'trail': ['groom'], 'snapshot': view['snapshot']['id']}}


def size(view):
    return {'next': 'rank', 'suspend': True, 'notes': {'trail': view['notes']['trail'] + ['size']}}


def rank(view):
    return {'next': None, 'proposals': [{'type': 'priority', 'proposal_id': 'p-' + view['identity']['cycle_id'],
                                         'subject': 'unit-1', 'priority': view['supplied_results'][0]['rank']}]}


def failing(view):
    return {'failure': {'code': 'missing_evidence', 'detail': 'no accepted evidence for unit-1'}}


def foreign_command(view):
    return {'next': None, 'proposals': [{'type': 'priority', 'proposal_id': 'p1', 'subject': 'unit-1',
                                         'priority': Command(goto='rank')}]}


def foreign_snapshot(view):
    return {'next': None, 'proposals': [{'type': 'completion', 'proposal_id': 'p1', 'subject': 'unit-1',
                                         'evidence': StateSnapshot({}, (), {}, None, None, None, (), ())}]}


def untyped_proposal(view):
    return {'next': None, 'proposals': [{'proposal_id': 'p1', 'subject': 'unit-1', 'priority': 1}]}


def assert_admission(view):
    return {'next': None, 'admitted': True}


def assert_priority(view):
    return {'next': None, 'priority': 99}


def assert_completion(view):
    return {'next': None, 'shipped': True}


def probe_store(view):
    # Every way a node could reach the authority: the working directory's repository, an
    # inherited descriptor, the environment, or the request. Whatever is found is written to.
    found = []
    here = Path(os.getcwd())
    for parent in (here, *here.parents):
        candidate = parent / '.git' / 'veldo' / 'control' / 'control.sqlite3'
        if candidate.is_file():
            found.append(str(candidate))
    for fd in os.listdir('/proc/self/fd'):
        try:
            target = os.readlink('/proc/self/fd/' + fd)
        except OSError:
            continue
        if target.endswith('control.sqlite3'):
            found.append(target)
    found += [value for value in os.environ.values() if 'sqlite3' in value]
    if 'sqlite3' in json.dumps(view):
        found.append('request')
    wrote = []
    for path in sorted(set(found)):
        try:
            connection = sqlite3.connect(path)
            connection.execute("UPDATE entities SET data = ? WHERE id = 'unit-1'", ('{"priority": 99}',))
            connection.commit()
            connection.close()
            wrote.append(path)
        except Exception as error:
            wrote.append(type(error).__name__)
    return {'next': 'propose', 'suspend': True, 'notes': {'found': sorted(set(found)), 'wrote': wrote}}


def propose(view):
    return {'next': None, 'proposals': [{'type': 'priority', 'proposal_id': 'p-store', 'subject': 'unit-1',
                                         'priority': view['supplied_results'][0]['rank']}]}


def one(function):
    return {'version': 1, 'entry': 'only', 'nodes': {'only': function}}


WORKFLOWS = {
    'lifecycle': {'version': 1, 'entry': 'groom', 'nodes': {'groom': groom, 'size': size, 'rank': rank}},
    'failing': one(failing), 'foreign-command': one(foreign_command),
    'foreign-snapshot': one(foreign_snapshot), 'untyped-proposal': one(untyped_proposal),
    'assert-admission': one(assert_admission), 'assert-priority': one(assert_priority),
    'assert-completion': one(assert_completion),
    'store-access': {'version': 1, 'entry': 'probe', 'nodes': {'probe': probe_store, 'propose': propose}},
}
code = runner.serve(WORKFLOWS)
audit()
sys.stdout.flush()
# No interpreter shutdown: a tracing mutant's exporter would otherwise retry its refused egress
# at exit for many seconds. The answer and the audit line are already written.
os._exit(code)
'''
_S43_SWITCHES = ('LANGSMITH_TRACING', 'LANGSMITH_TRACING_V2', 'LANGCHAIN_TRACING', 'LANGCHAIN_TRACING_V2')


def _s43_exact_plain(value):
    kind = type(value)
    if value is None or kind in (bool, int, float, str):
        return True
    if kind is list:
        return all(_s43_exact_plain(item) for item in value)
    return kind is dict and all(type(k) is str and not k.startswith('__') and _s43_exact_plain(v)
                                for k, v in value.items())


def _s43_canon(name):
    import re as _s43_re
    return _s43_re.sub(r'[-_.]+', '-', name).lower()


def _s43_census(directory):
    """(name, version) of every distribution installed in the runtime, read from its metadata."""
    import email.parser as _s43_email
    found = []
    for info in sorted(directory.glob('lib/python*/site-packages/*.dist-info')):
        meta = _s43_email.Parser().parsestr((info / 'METADATA').read_text(errors='replace'), headersonly=True)
        found.append((_s43_canon(meta['Name']), meta['Version']))
    return found


def _s43_runtime(root, repo, graph, store, snapshot):
    import pwd as _s43_pwd
    lock = _s43_load('s43_lock', repo / '.veldo/control_graph_lock.py')
    home = _s43_pwd.getpwuid(_s43_os.getuid()).pw_dir
    directory = lock.runtime_directory()
    observations = {'lock_digest': lock.digest(), 'python': lock.PYTHON,
                    'runtime_directory': str(directory)}
    runtime = graph.resolve_runtime()
    absent = ('' if runtime else ': runtime absent at ' + str(directory) + '; install it with: '
              + graph.INSTALL_COMMAND)
    # The runtime holds exactly the locked distributions: no installer's own pip, nothing unpinned.
    census = _s43_census(directory)
    observations['census_unlocked'] = sorted(set(census) - {(_s43_canon(n), v) for n, v, _, _ in lock.PACKAGES})
    expect('graph/runtime/installed' + absent, runtime is not None
           and runtime['python'] == str(_s43_Path(home) / '.local/share/veldo/langgraph' / lock.digest() / 'bin/python')
           and runtime['runner'] == str(repo / '.veldo/control_graph_langgraph.py')
           and sorted(census) == sorted((_s43_canon(n), v) for n, v, _, _ in lock.PACKAGES)
           and not (directory / 'bin/pip').exists())
    rows = ('graph/runtime/lifecycle', 'graph/runtime/plain-data', 'graph/runtime/tracing-off',
            'graph/authority/no-direct-write', 'graph/authority/typed-proposals-only')
    if runtime is None:
        for name in rows:
            expect(name + absent, False)
        return observations
    audit = root / 'runtime-audit.jsonl'
    wrapper = root / 'runtime_runner.py'
    wrapper.write_text('PRODUCTION = %r\nAUDIT = %r\n' % (str(repo / '.veldo/control_graph_langgraph.py'),
                                                          str(audit)) + _S43_RUNNER)
    adapter = graph.Adapter(dict(runtime, runner=str(wrapper)), 'domain', 'repository')
    responses = []

    def workflow(name):
        return {'id': name, 'version': 1, 'digest': 'sha256:' + 'c' * 64}

    def call(operation, *args, target=adapter):
        try:
            result = getattr(target, operation)(*args)
        except Exception as error:  # recorded as a wrong answer, never raised
            return {'refused': getattr(error, 'code', type(error).__name__)}
        responses.append(result)
        return result

    # The caller's own environment asks for LangSmith tracing; the graph child must not see it.
    saved = {name: _s43_os.environ.get(name) for name in _S43_SWITCHES}
    _s43_os.environ.update({name: 'true' for name in _S43_SWITCHES})
    try:
        # AC1: every lifecycle operation and outcome through the actual runtime.
        started = call('start', 'cycle-r1', 'command-r1', snapshot, workflow('lifecycle'))
        pending = adapter.pending()
        held = call('suspend', 'cycle-r1', 'command-r2', workflow('lifecycle'), started.get('resume'))
        advanced = call('advance', 'cycle-r1', 'command-r3', snapshot, workflow('lifecycle'),
                        held.get('resume'), [{'rank': 2}])
        second = call('start', 'cycle-r2', 'command-r4', snapshot, workflow('lifecycle'))
        canceled = call('cancel', 'cycle-r2', 'command-r5', workflow('lifecycle'), second.get('resume'))
        failed = call('start', 'cycle-r3', 'command-r6', snapshot, workflow('failing'))
        lifecycle_counts = dict(adapter.counts)
        production = call('start', 'cycle-r4', 'command-r7', snapshot, workflow('lifecycle'),
                          target=graph.Adapter(runtime, 'domain', 'repository'))
        foreign = [call('start', 'cycle-f-' + name, 'command-f-' + name, snapshot, workflow(name))
                   for name in ('foreign-command', 'foreign-snapshot')]
        untyped = call('start', 'cycle-u', 'command-u', snapshot, workflow('untyped-proposal'))

        # AC2: a real store in a real repository; the domain process runs inside it and holds an
        # open, inheritable descriptor on the store while every graph node tries to reach it.
        git = _s43_load('s43_git', ROOT / '.veldo/git_process.py')
        authority = root / 'authority-repository'
        git.run(['git', 'init', '-q', str(authority)], check=True, stdout=_s43_sp.DEVNULL)
        store_path = authority / '.git/veldo/control/control.sqlite3'
        connection = store.open_store(str(store_path))

        def command(command_id, principal, priority, version):
            return {'command_id': command_id, 'principal': principal, 'operation': 'upsert_entity',
                    'parameters': {'entity_id': 'unit-1', 'kind': 'unit', 'data': {'priority': priority}},
                    'expected_versions': {'unit-1': version}, 'artifact_digests': [], 'nonce': command_id}

        def sign(message):
            return 'stub:' + store.digest_of(message.decode('utf-8'))

        store.execute(connection, command('seed-unit-1', 'owner', 5, 0), 'dmitry', sign, 1)
        before = store.table_snapshot(connection)
        handle = _s43_os.open(store_path, _s43_os.O_RDONLY)
        _s43_os.set_inheritable(handle, True)
        previous = _s43_os.getcwd()
        _s43_os.chdir(authority)
        try:
            assertions = {name: call('start', 'cycle-' + name, 'command-' + name, snapshot, workflow(name))
                          for name in ('assert-admission', 'assert-priority', 'assert-completion')}
            probe = call('start', 'cycle-store', 'command-store-1', snapshot, workflow('store-access'))
            proposed = call('advance', 'cycle-store', 'command-store-2', snapshot, workflow('store-access'),
                            probe.get('resume'), [{'rank': 1}])
        finally:
            _s43_os.chdir(previous)
            _s43_os.close(handle)
        after = store.table_snapshot(connection)
        # Only the typed proposal reaches the separately authorized command, by the owner.
        committed = None
        for item in proposed.get('proposals', []):
            if item['type'] == 'priority' and item['subject'] == 'unit-1':
                committed = store.execute(connection, command('commit-' + item['proposal_id'], 'owner',
                                                              item['priority'], 1), 'dmitry', sign, 1)
        unit = connection.execute("SELECT version, data FROM entities WHERE id = 'unit-1'").fetchone()
        journal = connection.execute('SELECT principal, command_id FROM journal ORDER BY seq').fetchall()
        connection.close()
    finally:
        for name, value in saved.items():
            if value is None:
                _s43_os.environ.pop(name, None)
            else:
                _s43_os.environ[name] = value
    audits = [_s43_json.loads(line) for line in audit.read_text().splitlines()] if audit.is_file() else []
    pinned = dict((name, version) for name, version, _, _ in lock.PACKAGES)['langgraph']
    identity = {'name': 'langgraph', 'version': pinned}
    observations.update(started=started, held=held, advanced=advanced, canceled=canceled, failed=failed,
                        production=production, foreign=foreign, untyped=untyped, assertions=assertions,
                        probe=probe.get('resume'), proposed=proposed, unit=list(unit), journal=journal,
                        store_unchanged_by_graph=before == after, audits=audits,
                        runner_processes=sum(adapter.counts.values()))

    expect('graph/runtime/lifecycle', started.get('outcome') == 'suspended'
           and started['resume'] == {'position': 'rank', 'step': 2,
                                     'notes': {'trail': ['groom', 'size'], 'snapshot': snapshot['id']}}
           and pending == ['cycle-r1'] and held.get('resume') == started['resume']
           and advanced.get('proposals') == [{'type': 'priority', 'proposal_id': 'p-cycle-r1',
                                              'subject': 'unit-1', 'priority': 2}]
           and canceled.get('outcome') == 'canceled'
           and failed.get('failure', {}).get('code') == 'missing_evidence'
           and production.get('failure', {}).get('code') == 'unsupported_workflow'
           and lifecycle_counts == {'accepted': 6, 'refused': 0}
           and all(r.get('runtime') == identity for r in (started, held, advanced, canceled, failed, production))
           and [o['operation'] for o in adapter.observations[:6]] ==
           ['start', 'suspend', 'advance', 'start', 'cancel', 'start']
           and adapter.observations[2]['accepted_inputs'] == {'snapshot': snapshot, 'workflow': workflow('lifecycle')})
    expect('graph/runtime/plain-data', [f.get('failure', {}).get('code') for f in foreign] == ['node_failed'] * 2
           and 'langgraph.types.Command' in foreign[0]['failure']['detail']
           and 'langgraph.types.StateSnapshot' in foreign[1]['failure']['detail']
           and len(responses) == 14 and all(_s43_exact_plain(r) for r in responses))
    source = (repo / '.veldo/control_graph_langgraph.py').read_text()
    expect('graph/runtime/tracing-off', len(audits) == sum(adapter.counts.values()) == 14 and all(
               a['switches'] == {name: 'false' for name in _S43_SWITCHES} and a['tracing'] is False
               and a['sockets'] == [] for a in audits)
           and all(graph.ENVIRONMENT.get(name) == 'false' for name in _S43_SWITCHES)
           and not any(word in source for word in ('langgraph_sdk', 'RemoteGraph', 'get_client')))
    notes = probe.get('resume', {}).get('notes', {})
    expect('graph/authority/no-direct-write', before == after and notes.get('found') == []
           and notes.get('wrote') == [] and probe.get('outcome') == 'suspended')
    expect('graph/authority/typed-proposals-only',
           [a.get('failure', {}).get('code') for a in assertions.values()] == ['node_failed'] * 3
           and all(key in assertions[name]['failure']['detail'] for name, key in (
               ('assert-admission', 'admitted'), ('assert-priority', 'priority'), ('assert-completion', 'shipped')))
           and untyped == {'refused': 'invalid_response'}
           and proposed.get('proposals') == [{'type': 'priority', 'proposal_id': 'p-store', 'subject': 'unit-1',
                                              'priority': 1}]
           and committed is not None and unit[0] == 2 and _s43_json.loads(unit[1]) == {'priority': 1}
           and journal == [('owner', 'seed-unit-1'), ('owner', 'commit-p-store')])
    return observations


def _s43_run():
    started = _s43_time.monotonic()
    observations = {}
    with _s43_temp.TemporaryDirectory(prefix='graph-43-') as temporary:
        root = _s43_Path(temporary)
        # An installed repository: every .veldo asset the scaffolder installs, from the canonical
        # engine (the only template tree a frozen gate copy carries), then the production copies.
        scaffold = _s43_load('s43_scaffold', ROOT / '.veldo/init_scaffold.py')
        repo = root / 'installed'
        (repo / '.veldo').mkdir(parents=True)
        installed = [rel for rel in scaffold._FILES if rel.startswith('.veldo/')]
        missing = [rel for rel in installed if not (ROOT / 'engine' / rel).is_file()]
        for rel in installed:
            if rel not in missing:
                (repo / rel).parent.mkdir(parents=True, exist_ok=True)
                _s43_shutil.copyfile(ROOT / 'engine' / rel, repo / rel)
        for name, source in {
            'control_graph.py': ROOT / ".veldo" / "control_graph.py",
            'control_graph_isolation.py': ROOT / ".veldo" / "control_graph_isolation.py",
            'authorization.py': ROOT / ".veldo" / "authorization.py",
            'control_graph_langgraph.py': ROOT / ".veldo" / "control_graph_langgraph.py",
            'control_graph_lock.py': ROOT / '.veldo/control_graph_lock.py',
            'control_graph_install.py': ROOT / '.veldo/control_graph_install.py',
            'two_key.py': ROOT / '.veldo/two_key.py',
            'request.py': ROOT / '.veldo/request.py',
        }.items():
            _s43_shutil.copyfile(source, repo / '.veldo' / name)
        graph = _s43_load('s43_graph', repo / '.veldo/control_graph.py')
        expect('graph/installed-assets', not missing and all(
               '.veldo/' + name in installed for name in (
                   'control_graph.py', 'control_graph_isolation.py', 'control_graph_lock.py',
                   'control_graph_install.py', 'control_graph_langgraph.py')))

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

        # A request is closed, plain, versioned data: exact digests, versioned supplied results, a
        # closed resume, and no filesystem location anywhere.
        good_digest = 'sha256:' + 'd' * 64
        result = {'id': 'result-1', 'version': 1, 'digest': good_digest,
                  'value': {'rank': 2, 'link': 'https://example.com/a/b'}}
        resume_ok = {'position': 'rank', 'step': 2, 'notes': '{"trail": ["groom"]}'}
        identity = dict(cycle_id='cycle-q', command_id='command-q', domain_uuid='domain', repository_uuid='repository')
        store_like = '/home/someone/repo/.git/veldo/control/control.sqlite3'
        request_cases = {
            'accepted': dict(snapshot=snapshot, workflow=version, resume=resume_ok, supplied_results=[result]),
            'snapshot-digest-path': dict(snapshot=dict(snapshot, digest='sha256:' + store_like), workflow=version,
                                         resume=resume_ok, supplied_results=[]),
            'workflow-digest-relative': dict(snapshot=snapshot, workflow=dict(version, digest='sha256:../../.git/veldo'),
                                             resume=resume_ok, supplied_results=[]),
            'digest-uppercase': dict(snapshot=dict(snapshot, digest='sha256:' + 'B' * 64), workflow=version,
                                     resume=resume_ok, supplied_results=[]),
            'digest-short': dict(snapshot=dict(snapshot, digest='sha256:' + 'b' * 63), workflow=version,
                                 resume=resume_ok, supplied_results=[]),
            'result-unversioned': dict(snapshot=snapshot, workflow=version, resume=resume_ok,
                                       supplied_results=[{'rank': 2}]),
            'result-bad-digest': dict(snapshot=snapshot, workflow=version, resume=resume_ok,
                                      supplied_results=[dict(result, digest='sha256:x')]),
            'resume-open': dict(snapshot=snapshot, workflow=version, resume=dict(resume_ok, db='x'),
                                supplied_results=[]),
            'resume-notes-object': dict(snapshot=snapshot, workflow=version, resume=dict(resume_ok, notes={'a': 1}),
                                        supplied_results=[]),
            'path-in-result': dict(snapshot=snapshot, workflow=version, resume=resume_ok,
                                   supplied_results=[dict(result, value={'store': store_like})]),
            'path-in-notes': dict(snapshot=snapshot, workflow=version, resume=dict(resume_ok, notes='db=' + store_like),
                                  supplied_results=[]),
            'home-path-in-result': dict(snapshot=snapshot, workflow=version, resume=resume_ok,
                                        supplied_results=[dict(result, value=['~/.ssh'])]),
            'relative-path-in-result': dict(snapshot=snapshot, workflow=version, resume=resume_ok,
                                            supplied_results=[dict(result, value='../../.git/veldo')]),
        }
        answered = {}
        for name, fields in request_cases.items():
            try:
                graph.request('advance', identity, **fields)
                answered[name] = 'accepted'
            except Exception as error:
                answered[name] = getattr(error, 'code', type(error).__name__)
        sent = graph.request('advance', identity, **request_cases['accepted'])
        head = {k: sent[k] for k in ('schema', 'operation', 'cycle_id', 'command_id', 'domain_uuid', 'repository_uuid')}
        for name, evidence in (('evidence-ok', [good_digest]), ('evidence-malformed', ['sha256:not-hex']),
                               ('evidence-path', ['sha256:' + store_like])):
            raw = _s43_json.dumps(dict(head, outcome='proposal', runtime={'name': 'interface-stub', 'version': '0'},
                                       proposals=[{'type': 'completion', 'proposal_id': 'p1', 'subject': 'unit-1',
                                                   'evidence': evidence}]))
            try:
                graph.response(sent, raw.encode())
                answered[name] = 'accepted'
            except Exception as error:
                answered[name] = getattr(error, 'code', type(error).__name__)
        observations['closed_request'] = answered
        expect('graph/shape/closed-request', answered == {
            'accepted': 'accepted', 'snapshot-digest-path': 'invalid_input', 'workflow-digest-relative': 'invalid_input',
            'digest-uppercase': 'invalid_input', 'digest-short': 'invalid_input', 'result-unversioned': 'invalid_input',
            'result-bad-digest': 'invalid_input', 'resume-open': 'invalid_input', 'resume-notes-object': 'invalid_input',
            'path-in-result': 'path_in_request', 'path-in-notes': 'path_in_request',
            'home-path-in-result': 'path_in_request', 'relative-path-in-result': 'path_in_request',
            'evidence-ok': 'accepted', 'evidence-malformed': 'invalid_response', 'evidence-path': 'invalid_response'})

        # An over-deep answer is a named refusal, counted and observed, never an escaping error.
        before_counts = dict(adapter.counts)
        try:
            adapter.start('cycle-deep', 'command-deep', snapshot, dict(version, id='deep'))
            deep = 'accepted'
        except Exception as error:
            deep = getattr(error, 'code', type(error).__name__)
        observations['deep_answer'] = deep
        expect('graph/shape/deep-answer', deep == 'invalid_response'
               and adapter.counts == dict(before_counts, refused=before_counts['refused'] + 1)
               and adapter.observations[-1]['refusal'] == 'invalid_response'
               and adapter.observations[-1]['cycle_id'] == 'cycle-deep')

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
        observations['runtime'] = _s43_runtime(root, repo, graph, store, snapshot)
    observations['elapsed_seconds'] = _s43_time.monotonic() - started
    return observations


_s43_observations = _s43_run()
