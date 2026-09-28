"""Temporary factory used by the acceptance suite and the lead's live capture."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from types import SimpleNamespace


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def factory(ROOT, base, PRODUCTION, fake_engine=None, live=None):
    connections = []
    mods = base / 'installed' / '.veldo'
    mods.mkdir(parents=True)
    for source in sorted((ROOT / '.veldo').glob('*.py')):
        shutil.copyfile(source, mods / source.name)
    for name, source in PRODUCTION.items():
        if Path(source).is_file():
            shutil.copyfile(source, mods / name)
    S = load('v173_store', mods / 'control_store.py')
    L = load('v173_launch', mods / 'control_launch.py')
    D = L.D
    RES = D.RES
    ACC = RES.ACC
    HELPER = load('v173_helper', mods / 'accounts.py')
    EL = load('v173_eligibility', mods / 'control_eligibility.py')
    SIG = load('v173_signer', mods / 'control_signer.py')
    GP = load('v173_git', mods / 'git_process.py')
    CLM = D.CLM
    E = L.ENGINES['claude_code']
    X = L.ENGINES['codex']
    DOMAIN, REPOSITORY, HOLDER, HOST = 'domain-127', 'repository-127', 'builder-127', 'linux-host-127'
    private = base / 'private'
    private.mkdir(mode=0o700)
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(private / 'journal')],
                   check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)

    def sign(data):
        return SIG.sign_bytes(private / 'journal', data, 'veldo-journal')

    db = base / 'authority' / 'control.sqlite3'
    writer = S.open_store(str(db))
    connections.append(writer)
    serial = [0]

    def entity(identity):
        row = writer.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
        return {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])} if row else None

    def put(identity, kind, data):
        serial[0] += 1
        current = entity(identity)
        S.execute(writer, dict(command_id='setup-%d' % serial[0], principal='setup', operation='upsert_entity',
                               nonce='setup-%d' % serial[0], artifact_digests=[],
                               expected_versions={identity: current['version'] if current else 0},
                               parameters=dict(entity_id=identity, kind=kind, data=data)), 'setup', sign, 1)

    def member(principal, kind, roles):
        put(principal, 'membership', dict(principal_type=kind, roles=roles, scope=[REPOSITORY],
                                          revoked_at=None, expires_at=None))
    member('runner', 'service', ['reservation_service'])
    member('launch-receiver', 'service', ['reservation_service'])
    member('owner', 'person', ['project_owner'])
    writer.command_registry['claim_operation'] = {'transaction_transition': CLM.transition,
                                                  'writes': ('entities', 'journal', 'commands', 'nonces')}

    reservations = RES.Reservations(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                    authorize=RES.service_authority, signer='runner', sign=sign)
    BIG = dict(capacity=50, invocations=200, wall_seconds=10 ** 7)
    # The owner's account record, over a profile the local helper prepares.
    accounts = ACC.Accounts(S, writer, principal='owner', signer='owner', sign=sign)
    helper_root = base / 'helper'
    profiles = {}
    for account, provider in [('acct-c1', 'claude_code'), ('acct-x1', 'codex')]:
        HELPER.account_add(account, root=str(helper_root), provider=provider,
                           config_dir=(live or {}).get(provider + '_profile'))
        fields = HELPER.registration(account, host=HOST, root=str(helper_root))
        profiles[provider] = fields['profiles'][HOST]
        reservations.configure('policy/' + account, 'account', account, dict(BIG), now=time.time())
        accounts.register('register/' + account, fields['account'], fields['provider'], fields['label'],
                          fields['profiles'], concurrency=2, now=time.time())
    projects = set()

    def admitted(unit, proj='journey'):
        if proj not in projects:
            projects.add(proj)
            put('project:' + proj, 'project', dict(name=proj))
            reservations.configure('policy/' + proj, 'project', proj, dict(BIG), now=time.time())
        put(unit, 'execution_unit', dict(state='READY', repository_uuid=REPOSITORY, backlog_item_uuid='backlog:' + unit,
                                         requirements=[], eligible_holders=[HOLDER], project=proj,
                                         scope_digest='sha256:scope-' + unit, revision=1, depends_on=[]))
        put('backlog:' + unit, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=REPOSITORY))
        put('admission:' + unit, 'admission', dict(unit=unit, state='accepted', scope_digest='sha256:scope-' + unit))
        reservations.configure('policy/' + unit, 'unit', unit, dict(capacity=5, invocations=20, wall_seconds=10 ** 6),
                               now=time.time())
        cid = CLM.claim_id(REPOSITORY, unit)
        serial[0] += 1
        S.execute(writer, dict(command_id='claim-%d' % serial[0], principal=HOLDER, operation='claim_operation',
                               nonce='claim-%d' % serial[0], artifact_digests=[],
                               expected_versions={unit: entity(unit)['version'],
                                                  'backlog:' + unit: entity('backlog:' + unit)['version'], cid: 0},
                               parameters=dict(action='claim', unit_id=unit, backlog_item_uuid='backlog:' + unit,
                                               claim_id=cid, holder=HOLDER, generation=0, capabilities=[],
                                               repository_uuid=REPOSITORY)), HOLDER, sign, 1)
        return unit

    src = base / 'source'
    GP.run(['git', 'init', '-q', str(src)], check=True, capture_output=True)
    (src / 'README').write_text('tool registry source\n')
    GP.run(['git', '-C', str(src), 'add', 'README'], check=True, capture_output=True)
    GP.run(['git', '-C', str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'source'], check=True,
           capture_output=True, identity=('Fixture', 'fixture@example.invalid'))

    config_api = load('v127_configs', mods / 'control_agent_config.py')
    changes = []
    configurations = config_api.Configurations(S, writer, domain=DOMAIN, repository=REPOSITORY,
                                               signer='owner', sign=sign, observe=changes.append)
    catalog_module = load('v127_catalog', mods / 'control_mcp_catalog.py')
    catalog = catalog_module.Catalog(S, writer, domain=DOMAIN, repository=REPOSITORY, signer='owner', sign=sign)
    credential_module = load('v127_credentials', mods / 'control_credential.py')
    # A generated Secret Service executable. Neither this factory nor its children can reach a real keyring.
    keys = base / 'keys'
    keys.mkdir(mode=0o700)
    commands = base / 'commands'
    commands.mkdir()
    secret_tool = commands / 'secret-tool'
    secret_tool.write_text('''#!%s
import sys, hashlib
from pathlib import Path
root = Path(%r)
p = root / hashlib.sha256(sys.argv[-1].encode()).hexdigest()
if sys.argv[1] == 'store':
    p.write_bytes(sys.stdin.buffer.read())
elif sys.argv[1] == 'lookup':
    if not p.exists(): sys.exit(1)
    sys.stdout.buffer.write(p.read_bytes())
''' % (sys.executable, str(keys)))
    secret_tool.chmod(0o700)
    keystore = credential_module.KS.SecretService(str(secret_tool))
    credentials = credential_module.Credentials(S, writer, domain=DOMAIN, repository=REPOSITORY,
                                               signer='owner', sign=sign, keystore=keystore)
    values, references = {}, {}
    for name in ('jira', 'other'):
        values[name] = 'fixture-' + os.urandom(18).hex()
        result = credentials.apply(credential_module.SET, dict(id=name, base=0, label=name, value=values[name]),
                                    principal='owner', command_id='credential-' + name)
        references[name] = result['reference']
    mcp = base / 'server.py'
    mcp.write_text('''import json, os, sys
from pathlib import Path
expected = Path(sys.argv[1]).read_text()
valid = os.environ.get('ROLE_CREDENTIAL') == expected
for raw in sys.stdin:
    message = json.loads(raw)
    if 'id' not in message: continue
    if message['method'] == 'initialize':
        result = {'protocolVersion': '2024-11-05', 'capabilities': {'tools': {}},
                  'serverInfo': {'name': 'role-fixture', 'version': '1'}}
    elif message['method'] == 'tools/list':
        result = {'tools': [{'name': n, 'description': n, 'inputSchema': {'type': 'object'}}
                            for n in ('jira_search', 'jira_write')]}
    else:
        result = {'content': [{'type': 'text', 'text': 'fixture result'}]}
    answer = {'jsonrpc': '2.0', 'id': message['id']}
    answer.update(result=result) if valid else answer.update(error={'code': -32000, 'message': 'credential mismatch'})
    print(json.dumps(answer), flush=True)
''')
    for name in ('jira', 'other'):
        value_file = base / (name + '.value')
        value_file.write_text(values[name])
        value_file.chmod(0o600)
        catalog.save(dict(id=name, label=name, transport='stdio', command=sys.executable,
                          arguments=[str(mcp), str(value_file)], url=None,
                          environment={'ROLE_CREDENTIAL': {'reference': references[name]}}, headers={},
                          hosts=['linux'], read_only_tools=['jira_search']),
                     principal='owner', base=0, command_id='catalog-' + name)
    (base / 'listed.md').write_text('Use the listed role instruction.\n')
    (src / 'project.md').write_text('Use the project role instruction.\n')
    (base / 'SKILL.md').write_text('---\nname: inspect\ndescription: Inspect the task\n---\nRead the requested input.\n')
    configurations.save(dict(skill='inspect', source='factory', path='SKILL.md'), kind=config_api.KINDS[1],
                        principal='owner', base=0, command_id='skill-inspect')
    versions = base / 'versions'
    versions.mkdir()
    shipped = json.loads((ROOT / '.veldo/runtime/claude-qualification.json').read_text())
    entry = shipped['versions']['2.1.281']
    if live:
        versions = Path(live['claude']).parent
    else:
        (versions / '2.1.281').write_text(fake_engine('claude'))
        (versions / '2.1.281').chmod(0o700)
        entry = dict(entry, sha256='sha256:' + hashlib.sha256((versions / '2.1.281').read_bytes()).hexdigest(),
                     session_environment=E.session_environment(versions / '2.1.281'))
    (mods / 'runtime').mkdir()
    (mods / 'runtime/claude-qualification.json').write_text(json.dumps(dict(shipped, versions={'2.1.281': entry})))
    state = base / 'factory'
    state.mkdir(mode=0o700)
    E.pin('2.1.281', versions=str(versions), state_root=str(state))
    if live:
        vendored = Path(live['codex'])
    else:
        package = base / 'package'
        vendored = package / 'vendor/x86_64-unknown-linux-musl/bin/codex'
        vendored.parent.mkdir(parents=True)
        (package / 'package.json').write_text(json.dumps({'name': '@openai/codex', 'version': '0.154.0-linux-x64'}))
        vendored.write_text(fake_engine('codex'))
        vendored.chmod(0o700)
    codex_qualification = base / 'codex-qualification.json'
    codex_qualification.write_text(json.dumps(X.qualification(str(vendored))))
    config = base / 'receiver.json'
    wrapper = []
    slice_name = 'veldo0127-' + str(os.getpid()) + '.slice'
    runtime = '/run/user/' + str(os.getuid())
    profile = {'kind':'linux-systemd', 'slice':slice_name, 'lock':str(base / 'slice.lock'), 'concurrency':2,
               'runtime_seconds':100, 'memory_bytes':1 << 30, 'cpu_percent':200, 'file_bytes':64 << 20,
               'tasks_max':128, 'stop_grace_seconds':0.4, 'kill_grace_seconds':0.4,
               'systemd_run':'/usr/bin/systemd-run'}
    config.write_text(json.dumps({
        'store': str(db), 'journal_key': str(private / 'journal'), 'principal': 'launch-receiver',
        'workspace': str(base), 'domain': DOMAIN, 'repository': REPOSITORY, 'authority_generation': 1,
        'host': HOST, 'state_root': str(state), 'profile':profile, 'adapters': {
            'claude': {'engine': 'claude_code', 'environment': {'TZ': 'UTC'},
                       'executable': {'version': '2.1.281'}, 'argv': wrapper},
            'codex': {'engine': 'codex', 'environment': {'TZ': 'UTC'},
                      'executable': str(vendored), 'qualification': str(codex_qualification),
                      'argv': wrapper + [str(vendored)] + list(X.FLAGS)}}}))
    gate = EL.Gate(S, writer, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
    dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner', signer='runner', sign=sign)
    inherited = {'PATH': str(commands) + ':' + os.environ['PATH'], 'HOME': str(base / 'home'), 'TZ': 'UTC'}
    inherited.update(XDG_RUNTIME_DIR=runtime, DBUS_SESSION_BUS_ADDRESS='unix:path=' + runtime + '/bus')
    (base / 'home').mkdir()
    def invoke(contract):
        return L.invoke(config, contract, dispatches, accept_seconds=30, environment=inherited)
    runners = {engine: L.Runner(gate, reservations, dispatches, invoke, account=account)
               for engine, account in [('claude', 'acct-c1'), ('codex', 'acct-x1')]}
    def role(engine, name=None, deferred=False):
        return dict(role=name or engine, engine='claude_code' if engine == 'claude' else engine,
                    native_tools=[{'name': n, 'load': 'always'} for n in
                                  (['Read', 'PushNotification', 'Skill'] if engine == 'claude' else ['update_plan', 'shell'])],
                    mcp=[{'server': 'jira', 'revision': 1, 'tools': ['jira_search'], 'load': 'always'}] +
                        ([{'server': 'other', 'revision': 1, 'tools': 'all', 'load': 'when assigned'}] if deferred else []),
                    skills=[{'skill': 'inspect', 'revision': 1, 'load': 'always'}],
                    instructions=[{'source': 'factory', 'path': 'listed.md', 'load': 'always'},
                                  {'source': 'project', 'path': 'project.md', 'load': 'always'}],
                    settings={'model': 'fixture-model'} if not live else {'model': live[engine + '_model']})
    def save(definition, base_revision=0, principal='owner'):
        serial[0] += 1
        return configurations.save(definition, principal=principal, base=base_revision,
                                   command_id='role-save-' + str(serial[0]))
    def prepare(engine, unit, configuration, payload):
        return runners[engine].prepare(admitted(unit), 'build', holder=HOLDER, source=str(src), revision='HEAD',
                                       payload=payload, adapter=engine, configuration=configuration, deadline=time.time() + 90)
    def launch(engine, contract):
        previous = Path.cwd()
        try:
            os.chdir(src)
            work = invoke(contract)
        finally:
            os.chdir(previous)
        return work
    def finish(engine, work):
        return runners[engine].wait(work, timeout=100)
    return SimpleNamespace(**locals())
