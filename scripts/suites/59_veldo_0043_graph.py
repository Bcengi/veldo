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


def _s43_notes(answer):
    """The graph notes a suspended answer carries as text, parsed; {} when there are none."""
    try:
        notes = _s43_json.loads(answer.get('resume', {}).get('notes', '{}'))
    except (TypeError, ValueError, AttributeError):
        return {}
    return notes if type(notes) is dict else {}


def _s43_result(rank):
    """One supplied result as plain versioned data."""
    return {'id': 'result-rank', 'version': 1, 'digest': 'sha256:' + 'e' * 64, 'value': {'rank': rank}}


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
    reply.update(outcome='suspended', resume={'position': 'await-results', 'step': 1, 'notes': '{}'})
elif mode == 'lifecycle':
    reply.update(outcome='proposal', proposals=[
        {'type': 'priority', 'proposal_id': 'p1', 'subject': 'unit-1',
         'priority': request['supplied_results'][0]['value']['rank']}])
elif mode == 'failure':
    reply.update(outcome='failure', failure={'code': 'node_failed', 'detail': 'stub node failed'})
elif mode == 'foreign':
    reply.update(outcome='proposal', proposals=[{'type': 'priority', 'proposal_id': 'p1',
                 'subject': 'unit-1', 'priority': 1, '__class__': 'Command'}])
elif mode == 'untyped':
    reply.update(outcome='proposal', proposals=[{'proposal_id': 'p1', 'subject': 'unit-1',
                 'priority': 1}])
elif mode == 'environment':
    reply.update(outcome='suspended', resume={'position': 'environment', 'step': 0, 'notes': json.dumps({
        'environment': sorted(os.environ), 'cwd_entries': sorted(os.listdir('.')),
        'descriptors': sorted(int(fd) for fd in os.listdir('/proc/self/fd')),
        'argv': sys.argv, 'request_text': json.dumps(request, sort_keys=True)})})
elif mode == 'notes-object':
    reply.update(outcome='suspended', resume={'position': 'rank', 'step': 1, 'notes': {'handoff': {
        '__class__': 'langgraph.types.Command', 'repr': "Command(goto='rank')"}}})
elif mode == 'resume-open':
    reply.update(outcome='suspended', resume={'position': 'rank', 'step': 1, 'notes': '{}', 'graph': 'x'})
elif mode == 'resume-no-notes':
    reply.update(outcome='suspended', resume={'position': 'rank', 'step': 1})
elif mode == 'resume-bad-position':
    reply.update(outcome='suspended', resume={'position': 'a/b', 'step': 1, 'notes': '{}'})
elif mode == 'crash':
    sys.exit(3)
elif mode in ('orphan-timeout', 'orphan-exit'):
    # A node's own subprocess, left behind: it writes its marker only if it outlives the exchange.
    import subprocess, time
    delay = '0.8' if mode == 'orphan-timeout' else '0.5'
    subprocess.Popen(['/bin/sh', '-c', 'sleep ' + delay + '; : > ' + MARKERS + '/' + mode])
    if mode == 'orphan-timeout':
        time.sleep(30)
    reply.update(outcome='suspended', resume={'position': 'p', 'step': 0, 'notes': '{}'})
elif mode == 'deep-utf16':
    # U+4122 is the bytes 22 41 in UTF-16-LE: a byte scanner reads a quote there and loses sync.
    reply.update(outcome='suspended', resume={'position': 'p', 'step': 0, 'notes': '\u4122'}, pad='HOLE')
    body = json.dumps(reply, ensure_ascii=False).replace('"HOLE"', '[' * 5000 + ']' * 5000)
    sys.stdout.buffer.write(body.encode('utf-16-le'))
    sys.exit(0)
elif mode == 'deep':
    reply.update(outcome='suspended', resume='HOLE')
    sys.stdout.write(json.dumps(reply).replace('"HOLE"', '{"n":' * 20000 + '0' + '}' * 20000))
    sys.exit(0)
sys.stdout.write(json.dumps(reply))
'''


# The suite's workflows, spliced into a copy of the PRODUCTION runner after its definitions (as
# VELDO-0132 registrations would be) and installed in the domain's own checkout, where the
# production runner lives. The block refuses every network egress event after recording it
# (urllib3's import-time loopback IPv6 probe is a bind, not egress), counts the compiled graphs
# this process executes, and writes one audit record per exchange under
# /tmp/veldo-graph-43-audit/<domain uuid>/<command id>.json. It ends without interpreter
# shutdown, so a tracing mutant's exporter cannot stall on its refused retries.
_S43_RUNNER = r'''
# ---- VELDO-0043 suite workflows ----
import os as _t_os
import sqlite3 as _t_sqlite3
import subprocess as _t_sp
from pathlib import Path as _t_Path
SOCKETS = []
EGRESS = ('socket.connect', 'socket.getaddrinfo', 'socket.gethostbyname', 'socket.gethostbyname_ex',
          'socket.gethostbyaddr', 'socket.sendto', 'socket.sendmsg')


def egress(event, args):
    if event in EGRESS:
        SOCKETS.append(event)
        raise ConnectionRefusedError('network egress refused by the VELDO-0043 suite: ' + event)


sys.addaudithook(egress)
from langgraph.types import Command, StateSnapshot
import langgraph.pregel
SWITCHES = ('LANGSMITH_TRACING', 'LANGSMITH_TRACING_V2', 'LANGCHAIN_TRACING', 'LANGCHAIN_TRACING_V2')
INVOKED = []
_invoke = langgraph.pregel.Pregel.invoke


def _counting(self, *args, **kwargs):
    INVOKED.append(type(self).__module__ + '.' + type(self).__qualname__)
    return _invoke(self, *args, **kwargs)


langgraph.pregel.Pregel.invoke = _counting


def audit(request):
    import langsmith.utils
    directory = _t_Path('/tmp/veldo-graph-43-audit') / request['domain_uuid']
    directory.mkdir(parents=True, exist_ok=True)
    (directory / (request['command_id'] + '.json')).write_text(json.dumps({
        'switches': {k: _t_os.environ.get(k) for k in SWITCHES}, 'tracing': langsmith.utils.tracing_is_enabled(),
        'sockets': sorted(set(SOCKETS)), 'invoked': INVOKED, 'argv0': sys.argv[0]}))


def groom(view):
    return {'next': 'size', 'notes': {'trail': ['groom'], 'snapshot': view['snapshot']['id']}}


def size(view):
    return {'next': 'rank', 'suspend': True, 'notes': {'trail': view['notes']['trail'] + ['size']}}


def rank(view):
    return {'next': None, 'proposals': [{'type': 'priority', 'proposal_id': 'p-' + view['identity']['cycle_id'],
                                         'subject': 'unit-1', 'priority': view['supplied_results'][0]['value']['rank']}]}


def failing(view):
    return {'failure': {'code': 'missing_evidence', 'detail': 'no accepted evidence for unit-1'}}


def foreign_command(view):
    return {'next': None, 'proposals': [{'type': 'priority', 'proposal_id': 'p1', 'subject': 'unit-1',
                                         'priority': Command(goto='rank')}]}


def foreign_snapshot(view):
    return {'next': None, 'proposals': [{'type': 'completion', 'proposal_id': 'p1', 'subject': 'unit-1',
                                         'evidence': StateSnapshot({}, (), {}, None, None, None, (), ())}]}


def foreign_notes(view):
    return {'next': 'only', 'suspend': True, 'notes': {'handoff': Command(goto='rank')}}


def untyped_proposal(view):
    return {'next': None, 'proposals': [{'proposal_id': 'p1', 'subject': 'unit-1', 'priority': 1}]}


def assert_admission(view):
    return {'next': None, 'admitted': True}


def assert_priority(view):
    return {'next': None, 'priority': 99}


def assert_completion(view):
    return {'next': None, 'shipped': True}


def _stores_from(start):
    # Veldo stores reachable from a directory: a .git directory or gitdir file in its ancestry
    # (followed to the common directory), and Git's own common-directory discovery from it.
    found, start = [], _t_Path(start).resolve()
    for parent in (start, *start.parents):
        dotgit = parent / '.git'
        if dotgit.is_dir():
            found.append(dotgit / 'veldo/control/control.sqlite3')
        elif dotgit.is_file() and dotgit.read_text().startswith('gitdir:'):
            gitdir = (parent / dotgit.read_text()[7:].strip()).resolve()
            common = gitdir / 'commondir'
            base = (gitdir / common.read_text().strip()).resolve() if common.is_file() else gitdir
            found.append(base / 'veldo/control/control.sqlite3')
    try:
        out = _t_sp.run(['git', '-C', str(start), 'rev-parse', '--path-format=absolute', '--git-common-dir'],
                        capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            found.append(_t_Path(out.stdout.strip()) / 'veldo/control/control.sqlite3')
    except (OSError, _t_sp.SubprocessError):
        pass
    return [str(path) for path in found if path.is_file()]


def probe_store(view):
    # Every route the adapter could have handed the node toward the authority: the runner's own
    # location (argv[0], __file__), its working directory, its descriptors, its environment and
    # its request. Whatever is found is written to.
    found = []
    for origin in (sys.argv[0], __file__):
        found += _stores_from(_t_Path(origin).parent)
    found += _stores_from(_t_os.getcwd())
    for fd in _t_os.listdir('/proc/self/fd'):
        try:
            target = _t_os.readlink('/proc/self/fd/' + fd)
        except OSError:
            continue
        if target.endswith('control.sqlite3'):
            found.append(target)
    found += [value for value in _t_os.environ.values() if 'sqlite3' in value]
    if 'sqlite3' in json.dumps(view):
        found.append('request')
    wrote = []
    for path in sorted(set(found)):
        try:
            connection = _t_sqlite3.connect(path)
            connection.execute("UPDATE entities SET data = ? WHERE id = 'unit-1'", ('{"priority": 99}',))
            connection.commit()
            connection.close()
            wrote.append(path)
        except Exception as error:
            wrote.append(type(error).__name__)
    return {'next': 'propose', 'suspend': True, 'notes': {'found': sorted(set(found)), 'wrote': wrote}}


def propose(view):
    return {'next': None, 'proposals': [{'type': 'priority', 'proposal_id': 'p-store', 'subject': 'unit-1',
                                         'priority': view['supplied_results'][0]['value']['rank']}]}


def proc_reach(view):
    # The STATED LIMIT: the same account can read its parent through /proc. Recorded, not used.
    parent = '/proc/%d' % _t_os.getppid()
    try:
        cwd = _t_os.readlink(parent + '/cwd')
    except OSError as error:
        cwd = type(error).__name__
    descriptors = []
    try:
        for fd in _t_os.listdir(parent + '/fd'):
            try:
                target = _t_os.readlink(parent + '/fd/' + fd)
            except OSError:
                continue
            if target.endswith('control.sqlite3'):
                descriptors.append(target)
    except OSError as error:
        descriptors.append(type(error).__name__)
    return {'next': 'only', 'suspend': True,
            'notes': {'parent_cwd': cwd, 'parent_store_descriptors': sorted(set(descriptors))}}


def poison_work(view):
    # Knows only its own argv[0] (<stage>/.../runners/<digest>.py): swaps the sibling work
    # directory for a link to whatever directory the NEXT follower is in.
    work = _t_Path(sys.argv[0]).parent.parent / 'work'
    _t_os.rename(work, work.with_name('work.displaced'))
    _t_os.symlink('/proc/self/cwd', work)
    return {'next': 'only', 'suspend': True, 'notes': {}}


def poison_runners(view):
    runners = _t_Path(sys.argv[0]).parent
    _t_os.rename(runners, runners.with_name('runners.displaced'))
    _t_os.symlink('/proc/self/cwd', runners)
    return {'next': 'only', 'suspend': True, 'notes': {}}


def plant_gitfile(view):
    # Plants <stage>/runners/.git as a gitfile to a repository it learned without being handed it.
    runners = _t_Path(sys.argv[0]).parent
    target = (runners.parent / 'known-repository').read_text().strip()
    (runners / '.git').write_text('gitdir: ' + target + '\n')
    return {'next': 'only', 'suspend': True, 'notes': {}}


def script_dir_probe(view):
    # Git discovery from this child's own script directory; writes what it finds.
    found = _stores_from(_t_Path(sys.argv[0]).parent)
    for path in found:
        connection = _t_sqlite3.connect(path)
        connection.execute("UPDATE entities SET data = ? WHERE id = 'unit-1'", ('{"priority": 98}',))
        connection.commit()
        connection.close()
    return {'next': 'only', 'suspend': True, 'notes': {'wrote': len(found)}}


def descriptors(view):
    # Where this child's own stdin and stdout, handed by the adapter, live.
    return {'next': 'only', 'suspend': True,
            'notes': {'fd0': _t_os.readlink('/proc/self/fd/0'), 'fd1': _t_os.readlink('/proc/self/fd/1')}}


def cwd_probe(view):
    # Git discovery from the working directory the adapter gave this child; writes what it finds.
    found = _stores_from(_t_os.getcwd())
    for path in found:
        connection = _t_sqlite3.connect(path)
        connection.execute("UPDATE entities SET data = ? WHERE id = 'unit-1'", ('{"priority": 97}',))
        connection.commit()
        connection.close()
    return {'next': 'only', 'suspend': True, 'notes': {'wrote': len(found)}}


def one(function):
    return {'version': 1, 'entry': 'only', 'nodes': {'only': function}}


WORKFLOWS = {
    'lifecycle': {'version': 1, 'entry': 'groom', 'nodes': {'groom': groom, 'size': size, 'rank': rank}},
    'failing': one(failing), 'foreign-command': one(foreign_command),
    'foreign-snapshot': one(foreign_snapshot), 'foreign-in-notes': one(foreign_notes),
    'untyped-proposal': one(untyped_proposal),
    'assert-admission': one(assert_admission), 'assert-priority': one(assert_priority),
    'assert-completion': one(assert_completion),
    'store-access': {'version': 1, 'entry': 'probe', 'nodes': {'probe': probe_store, 'propose': propose}},
    'proc-reach': one(proc_reach), 'poison-work': one(poison_work),
    'poison-runners': one(poison_runners), 'cwd-probe': one(cwd_probe),
    'plant-gitfile': one(plant_gitfile), 'script-dir-probe': one(script_dir_probe),
    'descriptors': one(descriptors),
}
_t_request = json.loads(sys.stdin.buffer.read())
emit(_t_request, answer(_t_request, WORKFLOWS), sys.stdout)
audit(_t_request)
sys.stdout.flush()
_t_os._exit(0)
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
           and runtime['stage'] == str(_s43_Path(home) / '.local/state/veldo/graph-stage')
           and sorted(p.name for p in directory.iterdir()) == ['bin', 'include', 'lib', 'lib64', 'pyvenv.cfg',
                                                                'veldo-lock.txt']
           and sorted(census) == sorted((_s43_canon(n), v) for n, v, _, _ in lock.PACKAGES)
           and not (directory / 'bin/pip').exists())
    account_stage = _s43_Path(home) / '.local/state/veldo/graph-stage'

    def account_state():
        # The account's runtime and stage, entry by entry: the suite must leave both untouched.
        listing = {}
        for base in (directory, account_stage):
            for entry in (sorted(base.rglob('*')) if base.is_dir() else []):
                if 'site-packages' not in entry.parts:
                    listing[str(entry)] = entry.lstat().st_mtime_ns
        return listing

    account_before = account_state()
    rows = ('graph/runtime/lifecycle', 'graph/runtime/plain-data', 'graph/runtime/tracing-off',
            'graph/authority/no-direct-write', 'graph/authority/typed-proposals-only', 'graph/authority/proc-limit',
            'graph/authority/stage-links', 'graph/runtime/pyvenv-clean')
    if runtime is None:
        for name in rows:
            expect(name + absent, False)
        return observations
    # The authority: a main repository whose Git common directory holds the store, and the
    # domain's linked worktree, where the runner is installed and the domain process works.
    git = _s43_load('s43_git', ROOT / '.veldo/git_process.py')
    authority, checkout = root / 'authority-repository', root / 'domain-checkout'
    quiet = dict(check=True, stdout=_s43_sp.DEVNULL, stderr=_s43_sp.DEVNULL)
    git.run(['git', 'init', '-q', str(authority)], **quiet)
    git.run(['git', '-C', str(authority), 'commit', '-q', '--allow-empty', '-m', 'authority'],
            identity=('Veldo Suite', 'suite@example.invalid'), **quiet)
    git.run(['git', '-C', str(authority), 'worktree', 'add', '-q', '--detach', str(checkout), 'HEAD'], **quiet)
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
    production_runner = (repo / '.veldo/control_graph_langgraph.py').read_text()
    installed_runner = checkout / '.veldo/control_graph_langgraph.py'
    installed_runner.parent.mkdir()
    installed_runner.write_text(production_runner.split("\nif __name__ == '__main__':\n")[0] + '\n' + _S43_RUNNER)
    domain = 'domain-' + _s43_os.urandom(6).hex()
    audit_directory = _s43_Path('/tmp/veldo-graph-43-audit') / domain
    stage_root = root / 'stage-runtime'
    adapter = graph.Adapter(dict(runtime, runner=str(installed_runner), stage=str(stage_root)), domain,
                            'repository', evidence=graph.runtime_evidence())
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
    # The domain process works inside its checkout and holds an open, inheritable descriptor on
    # the store (besides its own connection) for every exchange.
    saved = {name: _s43_os.environ.get(name) for name in _S43_SWITCHES}
    _s43_os.environ.update({name: 'true' for name in _S43_SWITCHES})
    handle = _s43_os.open(store_path, _s43_os.O_RDONLY)
    _s43_os.set_inheritable(handle, True)
    previous = _s43_os.getcwd()
    _s43_os.chdir(checkout)
    try:
        # AC1: every lifecycle operation and outcome through the actual runtime.
        started = call('start', 'cycle-r1', 'command-r1', snapshot, workflow('lifecycle'))
        pending = adapter.pending()
        held = call('suspend', 'cycle-r1', 'command-r2', workflow('lifecycle'), started.get('resume'))
        advanced = call('advance', 'cycle-r1', 'command-r3', snapshot, workflow('lifecycle'),
                        held.get('resume'), [_s43_result(2)])
        second = call('start', 'cycle-r2', 'command-r4', snapshot, workflow('lifecycle'))
        canceled = call('cancel', 'cycle-r2', 'command-r5', workflow('lifecycle'), second.get('resume'))
        failed = call('start', 'cycle-r3', 'command-r6', snapshot, workflow('failing'))
        lifecycle_counts = dict(adapter.counts)
        # Runtime evidence is what the locked LangGraph produced: a stub's own label is refused.
        try:
            stub_answer = graph.Adapter({'python': _s43_sys.executable, 'runner': str(root / 'stub_runner.py'),
                                         'stage': str(root / 'stage')},
                                        'domain', 'repository', evidence=graph.runtime_evidence()).start(
                'cycle-stub', 'command-stub', snapshot, workflow('lifecycle'))
            stub_evidence = 'accepted: ' + stub_answer['runtime']['name']
        except Exception as error:
            stub_evidence = getattr(error, 'code', type(error).__name__)
        try:
            installed_adapter = graph.Adapter.installed('domain', 'repository', stage=str(root / 'stage-production'))
            production = call('start', 'cycle-r4', 'command-r7', snapshot, workflow('lifecycle'),
                              target=installed_adapter)
        except Exception as error:  # recorded as a wrong answer, never raised
            production = {'refused': type(error).__name__}
        foreign = [call('start', 'cycle-f-' + name, 'command-f-' + name, snapshot, workflow(name))
                   for name in ('foreign-command', 'foreign-snapshot', 'foreign-in-notes')]
        untyped = call('start', 'cycle-u', 'command-u', snapshot, workflow('untyped-proposal'))
        # AC2: nodes assert authority, search for the store, and read the parent through /proc.
        assertions = {name: call('start', 'cycle-' + name, 'command-' + name, snapshot, workflow(name))
                      for name in ('assert-admission', 'assert-priority', 'assert-completion')}
        probe = call('start', 'cycle-store', 'command-store-1', snapshot, workflow('store-access'))
        proposed = call('advance', 'cycle-store', 'command-store-2', snapshot, workflow('store-access'),
                        probe.get('resume'), [_s43_result(1)])
        reach = call('start', 'cycle-proc', 'command-proc', snapshot, workflow('proc-reach'))
        # The domain process's own temporary directory lies in its checkout: the child's stdin and
        # stdout must still be created under the stage, never there.
        scratch = checkout / '.scratch'
        scratch.mkdir()
        saved_tempdir, _s43_temp.tempdir = _s43_temp.tempdir, str(scratch)
        try:
            handed = _s43_notes(call('start', 'cycle-fds', 'command-fds', snapshot, workflow('descriptors')))
        finally:
            _s43_temp.tempdir = saved_tempdir
        # Links the adapter did not make: a node swaps <stage>/work, then <stage>/runners, for a
        # link to the next follower's working directory (the domain checkout). Each is refused by
        # name before anything is written or launched there.
        links = {}
        call('start', 'cycle-poison-w', 'command-poison-w', snapshot, workflow('poison-work'))
        links['work'] = call('start', 'cycle-after-w', 'command-after-w', snapshot, workflow('cwd-probe'))
        for name in ('work', 'runners'):
            if (stage_root / name).is_symlink():
                (stage_root / name).unlink()
            _s43_shutil.rmtree(stage_root / name, ignore_errors=True)
            if (stage_root / (name + '.displaced')).exists():
                (stage_root / (name + '.displaced')).rename(stage_root / name)
        call('start', 'cycle-poison-r', 'command-poison-r', snapshot, workflow('poison-runners'))
        try:
            installed_runner.write_text(installed_runner.read_text() + '\n# a new registration\n')
        except OSError as error:  # a node moved the checkout's runner: recorded, never raised
            links['registration'] = type(error).__name__
        links['runners'] = call('start', 'cycle-after-r', 'command-after-r', snapshot, workflow('cwd-probe'))
        links['checkout_written'] = sorted(p.name for p in checkout.iterdir()
                                           if p.name.startswith('veldo-graph-') or p.suffix == '.py')
        for name in ('work', 'runners'):
            if (stage_root / name).is_symlink():
                (stage_root / name).unlink()
                if (stage_root / (name + '.displaced')).exists():
                    (stage_root / (name + '.displaced')).rename(stage_root / name)
        # A repository planted BELOW the stage root: runners/ is judged like work/.
        (stage_root / 'known-repository').write_text(str(authority / '.git'))
        call('start', 'cycle-plant-g', 'command-plant-g', snapshot, workflow('plant-gitfile'))
        links['runners-gitfile'] = call('start', 'cycle-after-g', 'command-after-g', snapshot,
                                        workflow('script-dir-probe'))
        if (stage_root / 'runners/.git').exists():
            (stage_root / 'runners/.git').unlink()
        # A runtime whose pyvenv.cfg names a repository (created by a repository's own virtual
        # environment) is refused before launch; the installed runtime's names none.
        # The repository's own virtual environment: its python is a link out to the system one.
        (checkout / '.venv/bin').mkdir(parents=True)
        (checkout / '.venv/bin/python3').symlink_to(_s43_os.path.realpath(runtime['python']))
        fake = root / 'repository-created-runtime'
        (fake / 'bin').mkdir(parents=True)
        (fake / 'bin/python').symlink_to(_s43_os.path.realpath(runtime['python']))
        (fake / 'lib/python3.12').mkdir(parents=True)
        (fake / 'lib/python3.12/site-packages').symlink_to(next(directory.glob('lib/python*/site-packages')))
        (fake / 'pyvenv.cfg').write_text('home = /usr/bin\ninclude-system-site-packages = false\nversion = 3.12.3\n'
                                         'command = ' + str(checkout / '.venv/bin/python3') + ' -m venv ' + str(fake) + '\n')
        try:
            fake_answer = graph.Adapter(dict(runtime, python=str(fake / 'bin/python'), runner=str(installed_runner),
                                             stage=str(stage_root)), domain, 'repository',
                                        evidence=graph.runtime_evidence()).start(
                'cycle-pyvenv', 'command-pyvenv', snapshot, workflow('cwd-probe'))
            pyvenv = 'launched: ' + fake_answer.get('outcome', '')
        except Exception as error:
            pyvenv = getattr(error, 'code', type(error).__name__) + ('' if 'pyvenv' in str(error) else ' (other)')
        # Every pyvenv.cfg value is judged whole, as a path (the command line split like a shell
        # would), including a repository under a directory whose name has a space and a quoted
        # value; and the interpreter is judged at every hop of its link chain.
        spaced = root / 'my projects' / 'repo'
        spaced.mkdir(parents=True)
        git.run(['git', 'init', '-q', str(spaced)], **quiet)
        (spaced / '.venv/bin').mkdir(parents=True)
        (spaced / '.venv/bin/python3').symlink_to(_s43_os.path.realpath(runtime['python']))
        venv_python = str(spaced / '.venv/bin/python3')
        cfg_cases = {
            'command-with-space': 'command = ' + venv_python + ' -m venv /elsewhere',
            'command-quoted': 'command = "' + venv_python + '" -m venv /elsewhere',
            'home': 'home = ' + str(spaced / '.venv/bin'),
            'executable': 'executable = ' + venv_python,
            'base-prefix': 'base-prefix = ' + str(spaced / '.venv'),
        }
        cfg_judged = {}
        for name, line in list(cfg_cases.items()) + [('link-chain', 'home = /usr/bin')]:
            probe_runtime = root / ('cfg-' + name)
            (probe_runtime / 'bin').mkdir(parents=True)
            (probe_runtime / 'bin/python').symlink_to(
                checkout / '.venv/bin/python3' if name == 'link-chain' else _s43_os.path.realpath(runtime['python']))
            (probe_runtime / 'pyvenv.cfg').write_text(line + '\nversion = 3.12.3\n')
            try:
                cfg_judged[name] = bool(graph.runtime_problems({'python': str(probe_runtime / 'bin/python')}))
            except Exception as error:
                cfg_judged[name] = type(error).__name__
        # A stage inside a repository is refused before anything launches.
        try:
            graph.Adapter(dict(runtime, runner=str(installed_runner), stage=str(checkout / '.veldo')),
                          domain, 'repository').start('cycle-in-repo', 'command-in-repo', snapshot,
                                                      workflow('lifecycle'))
            in_repository = 'launched'
        except Exception as error:
            in_repository = getattr(error, 'code', type(error).__name__)
    finally:
        _s43_os.chdir(previous)
        _s43_os.close(handle)
        for name, value in saved.items():
            if value is None:
                _s43_os.environ.pop(name, None)
            else:
                _s43_os.environ[name] = value
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
    audits = []
    for observed in adapter.observations:
        record = audit_directory / (observed['command_id'] + '.json')
        audits.append(_s43_json.loads(record.read_text()) if record.is_file() else None)
    _s43_shutil.rmtree(audit_directory, ignore_errors=True)
    pinned = dict((name, version) for name, version, _, _ in lock.PACKAGES)['langgraph']
    identity = {'name': 'langgraph', 'version': pinned}
    observations.update(started=started, held=held, advanced=advanced, canceled=canceled, failed=failed,
                        production=production, foreign=foreign, untyped=untyped, assertions=assertions,
                        probe=probe.get('resume'), proposed=proposed, unit=list(unit), journal=journal, reach=reach,
                        store_unchanged_by_graph=before == after, audits=audits, stub_evidence=stub_evidence,
                        runner_processes=sum(adapter.counts.values()))

    expect('graph/runtime/lifecycle', started.get('outcome') == 'suspended'
           and started['resume'] == {'position': 'rank', 'step': 2, 'notes': _s43_json.dumps(
               {'snapshot': snapshot['id'], 'trail': ['groom', 'size']}, sort_keys=True, separators=(',', ':'))}
           and pending == ['cycle-r1'] and held.get('resume') == started['resume']
           and advanced.get('proposals') == [{'type': 'priority', 'proposal_id': 'p-cycle-r1',
                                              'subject': 'unit-1', 'priority': 2}]
           and canceled.get('outcome') == 'canceled'
           and failed.get('failure', {}).get('code') == 'missing_evidence'
           and production.get('failure', {}).get('code') == 'unsupported_workflow'
           and lifecycle_counts == {'accepted': 6, 'refused': 0}
           and all(r.get('runtime') == identity for r in (started, held, advanced, canceled, failed))
           and production.get('runtime') == {'name': 'none', 'version': ''}
           and len(audits) >= 6 and all(a and a['invoked'] == ['langgraph.graph.state.CompiledStateGraph']
                                        for a in audits[:6])
           and stub_evidence == 'missing_evidence'
           and [o['operation'] for o in adapter.observations[:6]] ==
           ['start', 'suspend', 'advance', 'start', 'cancel', 'start']
           and adapter.observations[2]['accepted_inputs'] == {'snapshot': snapshot, 'workflow': workflow('lifecycle')})
    carried = [r for r in responses if r.get('outcome') != 'failure'
               and ('langgraph.' in _s43_json.dumps(r) or '__class__' in _s43_json.dumps(r))]
    observations['langgraph_objects_in_domain_answers'] = carried
    expect('graph/runtime/plain-data', [f.get('failure', {}).get('code') for f in foreign] == ['node_failed'] * 3
           and 'langgraph.types.Command' in foreign[0]['failure']['detail']
           and 'langgraph.types.StateSnapshot' in foreign[1]['failure']['detail']
           and 'langgraph.types.Command' in foreign[2]['failure']['detail'] and not carried
           and len(responses) == 20 and all(_s43_exact_plain(r) for r in responses))
    source = (repo / '.veldo/control_graph_langgraph.py').read_text()
    present = [a for a in audits if a]
    expect('graph/runtime/tracing-off', len(present) == 20 and all(
               a['switches'] == {name: 'false' for name in _S43_SWITCHES} and a['tracing'] is False
               and a['sockets'] == [] for a in present)
           and all(graph.ENVIRONMENT.get(name) == 'false' for name in _S43_SWITCHES)
           and not any(word in source for word in ('langgraph_sdk', 'RemoteGraph', 'get_client')))
    notes = _s43_notes(probe)
    observations['stage_in_repository'] = in_repository
    observations['handed_descriptors'] = handed
    observations['stage_links'] = links
    observations['pyvenv'] = pyvenv
    observations['pyvenv_values_judged'] = cfg_judged
    cfg_paths = [token for line in (directory / 'pyvenv.cfg').read_text().splitlines()
                 for token in line.partition('=')[2].split() if token.startswith('/')]
    expect('graph/runtime/pyvenv-clean', pyvenv == 'runtime_unavailable'
           and not (audit_directory / 'command-pyvenv.json').exists() and cfg_paths
           and not any(graph.inside_repository(token) for token in cfg_paths)
           and cfg_judged == {name: True for name in list(cfg_cases) + ['link-chain']})
    expect('graph/authority/stage-links', links['work'].get('refused') == 'runtime_unavailable'
           and links['runners'].get('refused') == 'runtime_unavailable' and links['checkout_written'] == []
           and links['runners-gitfile'].get('refused') == 'runtime_unavailable'
           and before == after and account_state() == account_before)
    expect('graph/authority/no-direct-write', before == after and notes.get('found') == []
           and notes.get('wrote') == [] and probe.get('outcome') == 'suspended'
           and in_repository == 'runtime_unavailable' and not (checkout / '.veldo/veldo').exists()
           and sorted(handed) == ['fd0', 'fd1'] and all(
               value.startswith(str(stage_root.resolve() / 'work') + '/') and str(checkout) not in value
               for value in handed.values())
           and all(a['argv0'].startswith(str(stage_root.resolve() / 'runners')) for a in audits if a))
    # The stated limit (Release 2: real confinement): as the same account, a node can still read
    # the domain process through /proc. This row keeps that limit visible; it is not a pass.
    limit = _s43_notes(reach)
    observations['proc_limit'] = limit
    expect('graph/authority/proc-limit', reach.get('outcome') == 'suspended'
           and limit.get('parent_cwd') == str(checkout.resolve())
           and str(store_path.resolve()) in limit.get('parent_store_descriptors', []))
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
        for runtime in (None, {'python': str(root / 'absent/bin/python'), 'runner': str(root / 'absent.py'),
                               'stage': str(root / 'stage')}):
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
        markers = root / 'markers'
        markers.mkdir()
        stub.write_text('MARKERS = %r\n' % str(markers) + _S43_STUB)
        adapter = graph.Adapter({'python': _s43_sys.executable, 'runner': str(stub), 'stage': str(root / 'stage')},
                                'domain', 'repository')
        started_cycle = adapter.start('cycle-1', 'command-1', snapshot, version)
        pending = adapter.pending()
        suspended = adapter.suspend('cycle-1', 'command-2', version, started_cycle['resume'])
        advanced = adapter.advance('cycle-1', 'command-3', snapshot, version, suspended['resume'], [_s43_result(2)])
        adapter.start('cycle-2', 'command-4', snapshot, version)
        canceled = adapter.cancel('cycle-2', 'command-5', version, {'position': 'await-results', 'step': 1, 'notes': '{}'})
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

        # The answer is a closed schema: a resume is exactly {position, step, notes as text}.
        closed = {}
        for mode in ('lifecycle', 'notes-object', 'resume-open', 'resume-no-notes', 'resume-bad-position'):
            try:
                answer = adapter.start('cycle-c-' + mode, 'command-c-' + mode, snapshot, dict(version, id=mode))
                closed[mode] = 'accepted' if type(answer['resume']['notes']) is str else 'accepted-structure'
            except Exception as error:
                closed[mode] = getattr(error, 'code', type(error).__name__)
        observations['closed_response'] = closed
        expect('graph/shape/closed-response', closed == {
            'lifecycle': 'accepted', 'notes-object': 'invalid_response', 'resume-open': 'invalid_response',
            'resume-no-notes': 'invalid_response', 'resume-bad-position': 'invalid_response'})

        # A request is closed, plain, versioned data: exact digests, versioned supplied results, a
        # closed resume, and no filesystem location anywhere.
        good_digest = 'sha256:' + 'd' * 64
        result = {'id': 'result-1', 'version': 1, 'digest': good_digest,
                  'value': {'rank': 2, 'source_url': 'https://example.com/a/b'}}
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

        def with_value(value, **changes):
            return dict(snapshot=snapshot, workflow=version, resume=changes.get('resume', resume_ok),
                        supplied_results=[dict(result, value=value)])
        cycle = []
        cycle.append(cycle)
        request_cases.update({
            'http-then-path': with_value('http://' + store_like),
            'https-host-then-path': with_value('https://x' + store_like),
            'http-path-in-notes': with_value(1, resume=dict(resume_ok, notes=_s43_json.dumps({'u': 'http://' + store_like}))),
            'unbounded-scheme': with_value('xhttp://' + store_like),
            'file-url': with_value('file://' + store_like),
            'division-slash': with_value(store_like.replace('/', '\u2215')),
            'fullwidth-solidus': with_value(store_like.replace('/', '\uff0f')),
            'percent-encoded': with_value(store_like.replace('/', '%2F')),
            'url-field-file': with_value({'source_url': 'file://' + store_like}),
            'url-field-no-host': with_value({'source_url': 'https:///etc/passwd'}),
            'identifier-control': dict(request_cases['accepted'], _identity=dict(identity, cycle_id='a\x00\nb')),
            'identifier-dots': dict(request_cases['accepted'], _identity=dict(identity, cycle_id='..')),
            'two-megabytes': with_value(['x' * 1000] * 2000),
            'self-referential': with_value(cycle),
        })
        answered = {}
        for name, fields in request_cases.items():
            fields = dict(fields)
            asked = fields.pop('_identity', identity)
            try:
                graph.request('advance', asked, **fields)
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
            'evidence-ok': 'accepted', 'evidence-malformed': 'invalid_response', 'evidence-path': 'invalid_response',
            'http-then-path': 'path_in_request', 'https-host-then-path': 'path_in_request',
            'http-path-in-notes': 'path_in_request', 'unbounded-scheme': 'path_in_request', 'file-url': 'path_in_request',
            'division-slash': 'path_in_request', 'fullwidth-solidus': 'path_in_request',
            'percent-encoded': 'path_in_request', 'url-field-file': 'path_in_request',
            'url-field-no-host': 'path_in_request', 'identifier-control': 'invalid_input',
            'identifier-dots': 'invalid_input', 'two-megabytes': 'invalid_input', 'self-referential': 'invalid_input'})

        # Every bad shape at the stage that is not a link is a named, counted, observed refusal.
        import hashlib as _s43_hashlib
        staged_name = _s43_hashlib.sha256(stub.read_bytes()).hexdigest() + '.py'

        def plant(stage, shape):
            if shape == 'runners-file':
                _s43_shutil.rmtree(stage / 'runners')
                (stage / 'runners').write_text('x')
            elif shape == 'work-file':
                _s43_shutil.rmtree(stage / 'work')
                (stage / 'work').write_text('x')
            elif shape == 'runner-directory':
                (stage / 'runners' / staged_name).unlink()
                (stage / 'runners' / staged_name).mkdir()
            elif shape == 'root-file':
                _s43_shutil.rmtree(stage)
                stage.write_text('x')
            elif shape == 'runners-unwritable':
                (stage / 'runners' / staged_name).write_text('tampered')
                (stage / 'runners').chmod(0o500)
        shapes = {}
        for shape in ('runners-file', 'work-file', 'runner-directory', 'root-file', 'runners-unwritable'):
            stage = root / ('stage-shape-' + shape)
            shaped_adapter = graph.Adapter({'python': _s43_sys.executable, 'runner': str(stub), 'stage': str(stage)},
                                           'domain', 'repository')
            shaped_adapter.start('cycle-shape-0', 'command-shape-0', snapshot, version)
            plant(stage, shape)
            try:
                shaped_adapter.start('cycle-shape-1', 'command-shape-1', snapshot, version)
                shapes[shape] = ['launched']
            except Exception as error:
                shapes[shape] = [getattr(error, 'code', type(error).__name__), getattr(error, 'detail', str(error))[:80]]
            shapes[shape] += [shaped_adapter.counts == {'accepted': 1, 'refused': 1},
                              shaped_adapter.observations[-1]['refusal']]
            if (stage / 'runners').is_dir():
                (stage / 'runners').chmod(0o700)
        observations['stage_shapes'] = shapes
        reasons = {'runners-file': 'the stage runners is not a directory', 'work-file': 'the stage work is not a directory',
                   'runner-directory': 'the staged runner is not a file', 'root-file': 'the stage root is not a directory',
                   'runners-unwritable': 'the stage cannot be used'}
        expect('graph/authority/stage-shapes', all(
            shapes[name][0] == 'runtime_unavailable' and shapes[name][1].startswith(reason)
            and shapes[name][2] is True and shapes[name][3] == 'runtime_unavailable' for name, reason in reasons.items()))

        # The child runs in its own session and its whole process group is killed on the deadline
        # and on every exit path: nothing a node started outlives the exchange.
        orphans = {}
        stub_runtime = {'python': _s43_sys.executable, 'runner': str(stub), 'stage': str(root / 'stage')}
        for mode, deadline in (('orphan-timeout', 0.5), ('orphan-exit', 30)):
            try:
                orphans[mode] = graph.Adapter(stub_runtime, 'domain', 'repository', timeout=deadline).start(
                    'cycle-' + mode, 'command-' + mode, snapshot, dict(version, id=mode)).get('outcome')
            except Exception as error:
                orphans[mode] = getattr(error, 'code', type(error).__name__)
        _s43_time.sleep(1.0)
        orphans['outlived'] = sorted(p.name for p in markers.iterdir())
        observations['process_group'] = orphans
        expect('graph/boundary/process-group', orphans == {'orphan-timeout': 'unknown_outcome',
                                                           'orphan-exit': 'suspended', 'outlived': []})

        # An over-deep answer is a named refusal, counted and observed, never an escaping error.
        before_counts = dict(adapter.counts)
        deep, deep_details = [], []
        for mode in ('deep', 'deep-utf16'):
            try:
                adapter.start('cycle-' + mode, 'command-' + mode, snapshot, dict(version, id=mode))
                deep.append('accepted')
            except Exception as error:
                deep.append(getattr(error, 'code', type(error).__name__))
                deep_details.append(getattr(error, 'detail', ''))
        observations['deep_answer'] = [deep, deep_details]
        # The UTF-8 answer is stopped by the bounded scan itself, before any parser recursion.
        expect('graph/shape/deep-answer', deep == ['invalid_response', 'invalid_response']
               and deep_details[0] == 'answer nests deeper than 32'
               and adapter.counts == dict(before_counts, refused=before_counts['refused'] + 2)
               and [o['refusal'] for o in adapter.observations[-2:]] == ['invalid_response'] * 2
               and [o['cycle_id'] for o in adapter.observations[-2:]] == ['cycle-deep', 'cycle-deep-utf16'])

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
        environment = _s43_json.loads(adapter.start('cycle-4', 'command-7', snapshot,
                                                    dict(version, id='environment'))['resume']['notes'])
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
