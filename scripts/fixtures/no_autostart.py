"""VELDO-0113 consumer of the unchanged registry adapters and lifecycle census.

The envelope uses fixture birth slots (root, root/git-N), declared before exec.
Each slot joins a wrapper acknowledgement to the census birth and causal parent;
no executable name, address, or successful refusal exempts a birth or service.
"""
import ast
import errno
import hashlib
import hmac
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile

VERSION = 'veldo.no-autostart/v1'
HANG = 1200
STATES = ('absent', 'sigkill_socket')
ROWS = ('unavailable/no-client-starts-the-authority',
        'unavailable/no-client-hosts-a-listener',
        'unavailable/no-auto-start-needs-census')
CONSTRUCTION = 'unavailable/in-process-construction-boundary'
STORE = 'unavailable/store-write-grant'
AUTHORITY_MODULES = {
    'Dispatches': {'control_service.py', 'control_service_api.py',
                   'control_launch.py', 'control_launch_work.py'},
    'Dispatcher': {'dispatch.py'},
}
KEY = b'veldo-0113-fixture-key-not-a-credential'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def sign(data):
    return hmac.new(KEY, data, hashlib.sha256).hexdigest()


def verify(data, signature):
    return hmac.compare_digest(sign(data), signature)


def construction_census(root, inventory):
    """Scan BOTH shipped trees afresh, including untracked new production modules.

    Follow simple imported/assigned constructor aliases, and flag dynamic getattr
    of either class. Unknown registered in-process classes fail closed. Test and
    proof harnesses are outside the shipped .veldo module universe.
    """
    classes = set()
    problems, sites, files = [], [], {}
    for case in inventory:
        if case.transport != 'in_process':
            continue
        entry = case.adapter.entrypoint
        if entry == 'dispatch:veldo_dispatch':
            classes.add('Dispatcher')
        else:
            classes.add(entry.split(':', 1)[1].split('.')[0])
    if classes != set(AUTHORITY_MODULES):
        problems.append('unknown_or_missing_in_process_class')
    for tree_name in ('.veldo', 'engine/.veldo'):
        for path in sorted((root / tree_name).rglob('*.py')):
            relative = str(path.relative_to(root))
            source = path.read_text()
            files[relative] = hashlib.sha256(source.encode()).hexdigest()
            tree = ast.parse(source, relative)
            aliases = {name: name for name in classes}
            def target(node):
                if isinstance(node, ast.Name):
                    return aliases.get(node.id)
                if isinstance(node, ast.Attribute) and node.attr in classes:
                    return node.attr
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == 'getattr' and len(node.args) > 1
                        and isinstance(node.args[1], ast.Constant)):
                    return node.args[1].value if node.args[1].value in classes else None
                return None
            for _ in range(len(list(ast.walk(tree))) + 1):
                before = dict(aliases)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        for alias in node.names:
                            if alias.name in classes:
                                aliases[alias.asname or alias.name] = alias.name
                    if isinstance(node, ast.Assign) and (name := target(node.value)):
                        for assigned in node.targets:
                            if isinstance(assigned, ast.Name):
                                aliases[assigned.id] = name
                if before == aliases:
                    break
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not (name := target(node.func)):
                    continue
                site = dict(file=relative, line=node.lineno, constructor=name,
                            expression=ast.unparse(node), source_digest=files[relative])
                sites.append(site)
                if path.relative_to(root / tree_name).as_posix() not in AUTHORITY_MODULES.get(name, ()):
                    problems.append('outside_authority:' + relative + ':' + str(node.lineno))
    for name in classes:
        if not any(s['constructor'] == name for s in sites):
            problems.append('missing_construction:' + name)
    return dict(status='FAIL' if problems else 'PASS', sites=sites, problems=problems,
                inventory_digest=inventory[0].registration_digest, scanned_files=files,
                discovery='recursive AST of both shipped module trees, constructor alias closure')


class Arguments:
    """Valid enrolled transport inputs; no store handle is handed to the client.

    Signing is the real HMAC callable supplied at the public transport seam.
    Claim state/authorization is qualified by VELDO-0112's independent live suite.
    Here every call must reach the absent/dead endpoint, never a schema shortcut.
    """
    def __init__(self, root, runtime, config):
        self.config = config
        self.client_module = runtime.load_client_module('control_claim_client')
        self.en = self.client_module.E
        self.cc = runtime.load_client_module('control_client')
        self.client = self.client_module.Client(config['workspace'], 'worker', sign, verify,
                                                'fixture-host', timeout=HANG)
        self.client.generations['unit'] = 1
        self.output, self.error = io.BytesIO(), io.StringIO()

    def arguments(self, entry, transport):
        if transport == 'relay':
            payload = self.config['payload'].encode()
            if entry == 'control_relay:main':
                return (['relay', self.config['address']],), dict(
                    stdin=io.BytesIO(payload), stdout=self.output, stderr=self.error)
            return (self.config['address'], payload), dict(timeout=HANG)
        if entry == 'control_client:send':
            return (self.config['workspace'], self.config['command'], self.en, verify,
                    sign, 'fixture-host'), dict(timeout=HANG)
        action = entry.rsplit(':', 1)[1].split('.')[-1]
        if entry.startswith('claim:'):
            return ('unit', 'worker'), dict(root=self.client)
        if action == 'request':
            return (self.client, 'renew', 'unit', 1), {}
        if action == 'use':
            return (self.client, 'unit', 1), {}
        return (self.client, 'unit', 'worker'), {}


def envelope(case, workspace):
    common = ['-C', workspace, 'rev-parse', '--git-common-dir']
    roots = ['-C', workspace, 'rev-list', '--max-parents=0', 'HEAD']
    # read_binding + workspace_identity(common, roots) + read_binding + last_seen.
    commands = [common, common, roots, common, common]
    if case.client == 'claim':
        commands.insert(0, common)  # Client.request reads its signed coordinates first.
    if case.transport == 'relay':
        commands = []
    return [dict(identity='root', parent=None, role='client')] + [
        dict(identity='root/git-' + str(i), parent='root', role='identity_lookup', argv=argv)
        for i, argv in enumerate(commands, 1)]


GIT_WRAPPER = '''#!{python}
import json, os, sys
with open({ack!r}, 'a') as sink:
    sink.write(json.dumps(dict(pid=os.getpid(), parent=os.getppid(), argv=sys.argv[1:])) + '\\n')
os.execve({git!r}, [{git!r}, *sys.argv[1:]], os.environ)
'''


def invoke(root, config):
    fixture = load(root / 'scripts/fixtures/registered_clients.py', 'autostart_registry')
    runtime = fixture.registry(root)
    inventory = fixture.cases(runtime)
    case = next(c for c in inventory if c.identity == config['case'])
    if runtime.digest() != config['inventory_digest']:
        raise ValueError('inventory_changed')
    arguments = Arguments(root, runtime, config)
    os.environ['PATH'] = config['bin'] + os.pathsep + os.environ['PATH']
    # Existing enrollment Git timeouts are 60 seconds. Only enlarge the hang
    # bound; neither invocation, arguments, output nor refusal is replaced.
    original_run = subprocess.run
    def generous_run(*args, **kwargs):
        if kwargs.get('timeout') is not None:
            kwargs['timeout'] = max(HANG, kwargs['timeout'])
        return original_run(*args, **kwargs)
    subprocess.run = generous_run
    try:
        result = case.invoke(runtime, arguments)
        refused = (case.adapter.entrypoint == 'control_relay:main' and result == 3
                   and not arguments.output.getvalue() and 'not answering' in arguments.error.getvalue())
        outcome = dict(refused=refused, reason='authority_unavailable' if refused else 'unexpected_return')
    except Exception as error:
        reason = getattr(error, 'reason', None)
        underlying = error
        while underlying.__cause__ is not None:
            underlying = underlying.__cause__
        refused = reason == 'authority_unavailable' or (
            case.adapter.entrypoint == 'control_relay:forward'
            and isinstance(error, OSError) and error.errno in (errno.ENOENT, errno.ECONNREFUSED))
        outcome = dict(refused=refused, reason='authority_unavailable' if refused else repr(error))
    print(json.dumps(dict(case=case.identity, inventory_digest=runtime.digest(), **outcome)))


def observed_effects(receipt, plan, acknowledgements):
    """Resolve predeclared causal slots to observed birth identities exactly once."""
    receipt = receipt if isinstance(receipt, dict) else {}
    processes = receipt.get('processes', [])
    roots = [p for p in processes if p['root']]
    allowed, bindings, errors = set(), [], []
    if len(roots) != 1:
        return dict(forbidden_births=processes, services=[], bindings=[], errors=['root_missing'])
    root = roots[0]
    allowed.add(root['identity'])
    bindings.append(dict(slot=plan[0], birth=root['identity'], parent=None))
    children = [p for p in processes if not p['root']]
    for slot, ack in zip(plan[1:], acknowledgements):
        matches = [p for p in children if p['pid'] == ack['pid'] and p['parent'] == root['identity']]
        if (len(matches) != 1 or ack['parent'] != root['pid'] or ack['argv'] != slot['argv']
                or matches[0]['identity'] in allowed):
            errors.append('launch_identity_mismatch:' + slot['identity'])
            continue
        allowed.add(matches[0]['identity'])
        bindings.append(dict(slot=slot, birth=matches[0]['identity'], parent=root['identity']))
    if len(acknowledgements) != len(plan) - 1:
        errors.append('launch_envelope_incomplete')
    return dict(forbidden_births=[p for p in children if p['identity'] not in allowed],
                services=[e for e in receipt.get('events', []) if e['kind'] == 'service'],
                bindings=bindings, errors=errors)


def evaluate(census, receipt, plan, acknowledgements, outcome):
    rows = {r['name']: dict(r) for r in census.consumer_rows(receipt, 'VELDO-0113')}
    effects = observed_effects(receipt, plan, acknowledgements)
    # A witnessed counterexample is false even on an unqualified host. Missing
    # events can prevent an absence proof; they cannot erase an observed birth.
    if effects['forbidden_births']:
        rows[ROWS[0]].update(status='FAIL', reason='forbidden_autostart')
    if effects['services']:
        rows[ROWS[1]].update(status='FAIL', reason='forbidden_autostart')
    if isinstance(receipt, dict) and receipt.get('capture_status') == 'COMPLETE' and (
            'root_missing' not in effects['errors'] and (effects['errors'] or not outcome.get('refused'))):
        rows[ROWS[0]].update(status='FAIL', reason='invalid_refusal_or_envelope')
    for row in rows.values():
        if row['status'] == 'READY':
            row.update(status='PASS', reason=None)
    return dict(rows=rows, effects=effects)


def make_dead_socket(address):
    read, write = os.pipe()
    child = os.fork()
    if child == 0:
        os.close(read)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(address)
        sock.listen(1)
        os.write(write, b'R')
        os.close(write)
        signal.pause()
        os._exit(1)
    os.close(write)
    try:
        if os.read(read, 1) != b'R':
            raise RuntimeError('dead endpoint fixture did not bind')
    finally:
        os.close(read)
        os.kill(child, signal.SIGKILL)
        _, status = os.waitpid(child, 0)
    assert os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGKILL
    return dict(pid=child, terminal_signal=signal.SIGKILL, inode=os.stat(address).st_ino)


def setup(root, scratch):
    fixture = load(root / 'scripts/fixtures/registered_clients.py', 'autostart_setup_registry')
    runtime = fixture.registry(root)
    enrollment = runtime.load_client_module('control_claim_client').E
    workspace = scratch / 'workspace'
    git = load(root / '.veldo/git_process.py', 'autostart_git')
    git.run(['git', 'init', '-q', str(workspace)], check=True, capture_output=True)
    git.run(['git', '-C', str(workspace), '-c', 'commit.gpgsign=false', 'commit', '-q',
             '--allow-empty', '-m', 'fixture'], identity=('Fixture', 'fixture@example.invalid'),
            check=True, capture_output=True)
    database = scratch / 'authority/control.sqlite3'
    database.parent.mkdir()
    binding = enrollment.enroll(str(workspace), 'domain', 'store', str(database),
                                'fixture-host', 1, sign, 'owner', '2026-11-21T00:00:00Z',
                                repository_uuid='repository')
    assert enrollment.resolve_store(str(workspace), verify, 'fixture-host') == str(database)
    cc = runtime.load_client_module('control_client')
    command = dict(operation='upsert_entity', command_id='fixture', nonce='fixture', principal='owner',
                   parameters=dict(entity_id='fixture', kind='fixture', data={'ok': True}),
                   expected_versions={'fixture': 0}, artifact_digests=[])
    payload = cc.build_request(str(workspace), binding, command, sign)
    assert not cc.request_problems(payload)
    config = dict(workspace=str(workspace), address=cc.socket_path_for(binding), command=command,
                  payload=json.dumps(payload), inventory_digest=runtime.digest())
    return fixture, runtime, binding, config, database


def store_probe(root, database):
    code = '''import importlib.util,json,sys,os
s=importlib.util.spec_from_file_location('store',sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
c=m.open_store(sys.argv[2],mode='rw')
c.execute('CREATE TABLE v113_non_authority_probe (value INTEGER)')
c.execute('INSERT INTO v113_non_authority_probe VALUES (1)')
print(json.dumps(dict(pid=os.getpid(),writable=c.execute('SELECT value FROM v113_non_authority_probe').fetchone()[0]==1)))
c.close()
'''
    result = subprocess.run([sys.executable, '-B', '-c', code, str(root / '.veldo/control_store.py'), str(database)],
                            capture_output=True, text=True, timeout=HANG, check=True)
    observation = json.loads(result.stdout)
    return dict(status='GAP' if observation['writable'] else 'PASS',
                reason='no_process_specific_write_grant', observation=observation)


def measure(root, census, case, config, scratch, state, fault=None):
    identity = case.identity + '/' + state
    plan = envelope(case, config['workspace'])
    ack = scratch / 'launches.jsonl'
    ack.write_text('')
    binpath = scratch / 'bin'
    binpath.mkdir(exist_ok=True)
    wrapper = binpath / 'git'
    wrapper.write_text(GIT_WRAPPER.format(python=sys.executable, ack=str(ack), git='/usr/bin/git'))
    wrapper.chmod(0o700)
    given = dict(config, case=case.identity, bin=str(binpath), envelope=plan)
    request_path = scratch / 'case.json'
    request_path.write_text(json.dumps(given))
    observation = census.census([sys.executable, '-B', str(Path(__file__).resolve()),
                                'invoke', str(root), str(request_path)],
                               identity=dict(case=identity, inventory_digest=case.registration_digest,
                                  implementation_digest=case.implementation_digest, fixture_version=VERSION,
                                  envelope_digest=digest(plan), input_digest=digest(given)),
                               cwd=root, deadline=HANG, fault=fault)
    acknowledgements = [json.loads(line) for line in ack.read_text().splitlines()]
    try:
        outcome = json.loads(observation['stdout'])
        assert outcome['case'] == case.identity and outcome['inventory_digest'] == case.registration_digest
    except (ValueError, AssertionError, KeyError):
        outcome = dict(refused=False, reason='invocation_incomplete')
    evaluated = evaluate(census, observation, plan, acknowledgements, outcome)
    return dict(identity=identity, state=state, inventory_digest=case.registration_digest,
                implementation_digest=case.implementation_digest, fixture_version=VERSION,
                input_identity=observation['input_identity'], outcome=outcome, envelope=plan,
                acknowledgements=acknowledgements, receipt=observation, **evaluated)


def protocol_controls(census):
    """Synthetic receipts test the decision boundary; never host evidence."""
    import copy
    complete = dict(schema=census.VERSION, status='COMPLETE', capture_status='COMPLETE',
        state='drained', failures=[], lost_events=0, input_identity={'synthetic': True},
        input_digest='a'*64, implementation_digest='b'*64,
        qualification=dict(status='COMPLETE', gaps=[], inventory={'exhaustive': True}),
        barriers=[{'name': name} for name in ('armed_before_exec', 'call_returned', 'descendants_drained')],
        processes=[dict(identity='100:1', pid=100, root=True, parent=None, terminal=2)], events=[])
    plan = [dict(identity='root', parent=None, role='client')]
    outcome = dict(refused=True)
    good = evaluate(census, complete, plan, [], outcome)
    controls = {'synthetic_complete_evaluates': all(r['status'] == 'PASS' for r in good['rows'].values())}
    invalid = [None, {}, {'addresses': []}, dict(complete, status='INCOMPLETE'),
               dict(complete, capture_status='INCOMPLETE'), dict(complete, lost_events=1),
               dict(complete, barriers=[]), dict(complete, processes=[])]
    # consumer_rows owns malformed receipt validation; the consumer never tries
    # to turn such a receipt into an empty process or address observation.
    for i, value in enumerate(invalid):
        rows = evaluate(census, value, plan, [], outcome)['rows']
        controls['invalid_receipt_' + str(i)] = (len(rows) == 3 and all(
            r['status'] == 'STANDS DOWN' and r['reason'] == 'census_incomplete' for r in rows.values()))
    for field in ('failures', 'qualification'):
        value = copy.deepcopy(complete)
        value[field] = ([dict(reason='lost')] if field == 'failures' else
                        dict(status='INCOMPLETE', gaps=['protocol_inventory_bounds']))
        rows = evaluate(census, value, plan, [], outcome)['rows']
        controls[field] = all(r['status'] == 'STANDS DOWN' for r in rows.values())
    return controls


def qualify(root, faults=('facilities', 'finalize')):
    census = load(root / 'scripts/fixtures/lifecycle_census.py', 'autostart_census')
    controls = protocol_controls(census)
    with tempfile.TemporaryDirectory(prefix='v113-') as temporary:
        scratch = Path(temporary)
        fixture, runtime, binding, config, database = setup(root, scratch)
        inventory = fixture.cases(runtime)
        construction = construction_census(root, inventory)
        store = store_probe(root, database)
        expected = sorted(c.identity + '/' + state for c in inventory for state in STATES)
        completed, cases, fault_cases = [], [], []
        for state in STATES:
            address = Path(config['address'])
            if address.exists():
                address.unlink()
            endpoint = make_dead_socket(str(address)) if state == 'sigkill_socket' else dict(absent=True)
            probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                assert probe.connect_ex(str(address)) == (errno.ENOENT if state == 'absent' else errno.ECONNREFUSED)
            finally:
                probe.close()
            for case in inventory:
                identity = case.identity + '/' + state
                if case.transport == 'in_process':
                    cases.append(dict(identity=identity, state=state, disposition='authority_component',
                                      inventory_digest=case.registration_digest,
                                      implementation_digest=case.implementation_digest,
                                      construction_status=construction['status']))
                else:
                    result = measure(root, census, case, config, scratch, state)
                    result['endpoint'] = endpoint
                    cases.append(result)
                    for fault in faults:
                        fault_result = measure(root, census, case, config, scratch, state, fault)
                        fault_result['fault'] = fault
                        fault_cases.append(fault_result)
                completed.append(identity)
        exact = expected == sorted(completed) and len(set(completed)) == len(completed)
        # Also use the dependency's independent exact-inventory validator per state.
        receipts = [fixture.receipt(runtime, inventory,
                    [i[:-len('/' + state)] for i in completed if i.endswith('/' + state)],
                    consumer=VERSION + '/' + state) for state in STATES]
        measured = [c for c in cases if 'receipt' in c]
        rows = {}
        for name in ROWS:
            statuses = [c['rows'][name]['status'] for c in measured]
            status = ('FAIL' if not exact or 'FAIL' in statuses else
                      'STANDS DOWN' if 'STANDS DOWN' in statuses else 'PASS')
            rows[name] = dict(status=status, reason='census_incomplete' if status == 'STANDS DOWN' else None)
        faults_ok = (sorted((c['identity'], c['fault']) for c in fault_cases) ==
                     sorted((c['identity'], fault) for c in measured for fault in faults) and all(
            c['receipt']['status'] == 'INCOMPLETE'
            and c['receipt']['qualification']['status'] == 'INCOMPLETE' and set(c['rows']) == set(ROWS)
            and all(r['status'] == 'STANDS DOWN' and r['reason'] == 'census_incomplete'
                    for r in c['rows'].values()) for c in fault_cases))
        if not faults_ok or not all(controls.values()):
            rows[ROWS[2]] = dict(status='FAIL', reason='incomplete_census_accepted')
        for row in rows.values():
            row['inventory_digest'] = runtime.digest()
            row['observation_receipts'] = [dict(identity=c['identity'], digest=digest(c['receipt'])) for c in measured]
        rows[CONSTRUCTION] = dict(status=construction['status'], reason=construction['problems'])
        rows[STORE] = store
        return dict(schema=VERSION, inventory_digest=runtime.digest(), expected=expected, completed=completed,
                    rows=rows, qualification='COMPLETE' if all(r['status'] == 'PASS' for r in rows.values())
                    else 'INCOMPLETE', construction=construction, cases=cases, faults=fault_cases,
                    inventory_receipts=receipts, faults_ok=faults_ok, protocol_controls=controls,
                    metrics=dict(expected=len(expected), completed=len(completed), measured=len(measured),
                        construction_cases=len(cases)-len(measured),
                        forbidden_launches=sum(len(c['effects']['forbidden_births']) for c in measured),
                        observation_failures=sum(c['receipt']['status'] != 'COMPLETE' for c in measured)))


if __name__ == '__main__':
    if sys.argv[1] == 'invoke':
        invoke(Path(sys.argv[2]), json.loads(Path(sys.argv[3]).read_text()))
    else:
        print(json.dumps(qualify(Path(sys.argv[1]))))
