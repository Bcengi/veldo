"""The owner's memory servers as catalog MCP servers over the one memory store (VELDO-0183).

THE FOUR RECORDS (AC1). From the memory record (VELDO-0182), the servers step saves four VELDO-0144 catalog records,
each by the owner's signed command: `ava-memory` and `memory-kb`, the factory's stdio bridge (`veldo memory bridge
<part>`) to the part's store server; `knowledge-graph`, the knowledge_graph interpreter running its mcp_server.py
(whose main creates the database with init_db and serves FastMCP over stdio); `claude-mem`, its search server's
command from the manifest. memory-kb names memory_kb's JARVIS_PASSPHRASE as its credential reference when the owner
has saved that credential (VELDO-0158 delivers and redacts it). Each record is added to the `assistant` and
`assistant_codex` roles (VELDO-0177 AC2) as an `always` selection of all its tools, in a new role revision, and the
default team names the new revisions.

ONE OPENER PER STORE (AC4). One store server per ChromaDB part (control_memory_store.py) runs as a user unit beside
the authority service: the part's interpreter in the part's code directory, the only process that opens the store.
Conversations reach it through the catalog bridge, the owner's assistant through the same bridge written into its
MCP configuration (the previous bytes kept), and `veldo memory kb` through the same socket. The first start of each
store server and the rewrite of the assistant's entries each run VELDO-0182 AC4's check around them, so a switch
that loses memories stops by name; a check that runs while a store server is up reads the store through that server
(its `check` and `copy`), never by opening it again. The knowledge graph needs no server: SQLite's own locks admit one writer at a
time. claude-mem's store is written only by its own worker (VELDO-0187).

NO PAID API (AC2). The catalog refuses a record naming a paid-API switch or login (control_mcp_catalog); ava-memory's
smart add extracts with Claude Code on one of the owner's subscription accounts, chosen by the account pool
(VELDO-0160), each extraction recorded as a run on its account (`extract`).

Observations name parts, sockets, servers, revisions and runs; never memory content or a credential.
"""
import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid


def organ(name, directory=None):
    path = Path(directory or Path(__file__).parent) / (name + '.py')
    spec = importlib.util.spec_from_file_location('memory_servers_%s_%s' % (name, os.urandom(3).hex()), str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M = organ('control_memory')
Refused = M.Refused
# Each catalog server and the memory part it serves, in the order they are saved and selected.
SERVERS = (('ava-memory', 'ava_memory'), ('knowledge-graph', 'knowledge_graph'), ('claude-mem', 'claude_mem'),
           ('memory-kb', 'memory_kb'))
# The parts with a store server, and the catalog servers that bridge to them.
STORES = ('ava_memory', 'memory_kb')
BRIDGED = {'ava-memory': 'ava_memory', 'memory-kb': 'memory_kb'}
ROLES = ('assistant', 'assistant_codex')
PASSPHRASE = 'JARVIS_PASSPHRASE'
MODULE = 'control_factory_setup_memory.py'
EXTRACTIONS = 'extractions'
EXTRACT_PROMPT = ('Extract the durable facts worth remembering from the text on standard input. Answer with JSON '
                  'only: {"facts": ["one fact per string"]}.')


def store_data(definition, part):
    """The directory a store server locks and owns: mem0_memory's data directory, memory_kb's chromadb."""
    return definition['parts'][part]['data']


def socket_path(root, part):
    return str(Path(root) / 'memory' / 'stores' / (part + '.sock'))


def unit_name(part):
    return 'veldo-memory-%s.service' % part.replace('_', '-')


# ---------------------------------------------------------------------------------------------
# The catalog records and the roles' selections (AC1, AC2)
# ---------------------------------------------------------------------------------------------

def bridge_arguments(factory, root, part, server, catalog_revision=None, memory_revision=None):
    arguments = ['-B', str(Path(factory) / MODULE), 'bridge', part, '--state-root', str(root), '--server', server]
    if catalog_revision is not None:
        arguments += ['--catalog-revision', str(catalog_revision), '--memory-revision', str(memory_revision)]
    return arguments


def definitions(definition, python, factory, root, memory_revision, revisions, passphrase=None):
    """{server: catalog definition} for the four servers; `revisions` the catalog revision each will be saved as,
    named in a bridge's arguments so each call it forwards joins to it."""
    parts, host = definition['parts'], definition['host']
    found = {}
    for server, part in SERVERS:
        base = dict(id=server, label='%s (the owner\'s memory, %s)' % (server, part), transport='stdio', url=None,
                    environment={}, headers={}, hosts=[host], read_only_tools=[])
        if server in BRIDGED:
            base.update(command=python, arguments=bridge_arguments(factory, root, part, server, revisions[server],
                                                                   memory_revision))
            if server == 'memory-kb' and passphrase:
                base['environment'] = {PASSPHRASE: {'reference': passphrase}}
        elif server == 'knowledge-graph':
            base.update(command=parts[part]['interpreter'], arguments=[str(Path(parts[part]['code']) / 'mcp_server.py')])
        else:
            base.update(command=parts[part]['command'][0], arguments=list(parts[part]['command'][1:]))
        found[server] = base
    return found


def passphrase_reference(conn, domain):
    """The keystore reference of memory_kb's passphrase when the owner has saved it as a credential, else None."""
    digest = hashlib.sha256((domain + '/' + PASSPHRASE).encode()).hexdigest()
    row = conn.execute('SELECT data FROM entities WHERE id=?', ('credential:' + digest,)).fetchone()
    data = json.loads(row[0]) if row else None
    if data and not data.get('deleted') and data.get('reference') == 'keychain:veldo/' + digest:
        return data['reference']
    return None


def selections(revisions):
    """The roles' selection of each memory server: always, every tool."""
    return [{'server': server, 'revision': revisions[server], 'tools': 'all', 'load': 'always'}
            for server, _ in SERVERS]


def selected(revision, revisions):
    """A role definition's fields with the memory servers selected at `revisions`; its other selections kept."""
    names = {server for server, _ in SERVERS}
    mcp = [item for item in revision['mcp'] if item['server'] not in names] + selections(revisions)
    return dict({k: revision[k] for k in ('role', 'engine', 'native_tools', 'skills', 'instructions', 'settings')},
                mcp=mcp)


# ---------------------------------------------------------------------------------------------
# The store servers' units (AC4)
# ---------------------------------------------------------------------------------------------

def unit_text(definition, part, python, factory, root):
    entry = definition['parts'][part]
    argv = [entry['interpreter'], '-B', str(Path(factory) / 'control_memory_store.py'), part, '--code', entry['code'],
            '--data', store_data(definition, part), '--socket', socket_path(root, part), '--state-root', str(root),
            '--python', python]
    import shlex
    return ('[Unit]\nDescription=Veldo memory store server (%s), the only process that opens its store\n\n'
            '[Service]\nType=notify\nWorkingDirectory=%s\nExecStart=%s\nUMask=0077\nRestart=on-failure\n'
            'RestartSec=5\n\n[Install]\nWantedBy=default.target\n'
            % (part, entry['code'], ' '.join(shlex.quote(a) for a in argv)))


def write_private(path, data, mode=0o600):
    directory = os.path.dirname(path)
    fd, temporary = tempfile.mkstemp(dir=directory, prefix='.veldo-')
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(data)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise


def start_stores(definition, root, python, factory, runner, unit_dir, check, observe):
    """Each store server's unit, written and started; its first start inside the check (`before` with no server up,
    `after` read through the server just started)."""
    report = []
    for part in STORES:
        unit = unit_name(part)
        path = os.path.join(unit_dir, unit)
        text = unit_text(definition, part, python, factory, root)
        first = not os.path.exists(path)
        if not first and Path(path).read_text() != text:
            raise Refused('invalid_input:state_root:differs:memory_store_unit', path)
        if first:
            check(part, 'before', served=False)
            os.makedirs(unit_dir, mode=0o755, exist_ok=True)
            write_private(path, text.encode(), 0o644)
            runner.run(['daemon-reload'])
            runner.run(['enable', unit])
        code, _out, err = runner.run(['start', unit])
        if code:
            raise Refused('unavailable_service:memory_store:' + part, (err or '').strip()[:200])
        if first:
            check(part, 'after', served=True)
        event = dict(point='memory_store_server', part=part, unit=unit, socket=socket_path(root, part),
                     lock=os.path.join(store_data(definition, part), 'veldo-store.lock'),
                     outcome='started' if first else 'already_installed')
        observe(event)
        report.append(event)
    return report


# ---------------------------------------------------------------------------------------------
# The owner's assistant's MCP entries (AC4)
# ---------------------------------------------------------------------------------------------

def bridges(entry, part):
    arguments = (entry or {}).get('args') or []
    return (isinstance(arguments, list) and 'bridge' in arguments and part in arguments
            and any(isinstance(a, str) and a.endswith(MODULE) for a in arguments))


def assistant_entries(python, factory, root):
    return {server: {'command': python, 'args': bridge_arguments(factory, root, part, server)}
            for server, part in BRIDGED.items()}


def rewrite_assistant(definition, root, python, factory, check, observe):
    """The ava-memory and memory-kb entries of the assistant's MCP configuration pointed at the bridge, the previous
    bytes kept for the rollback, each rewritten part inside the check, read through its store server (up since
    start_stores); entries that already name the bridge are left alone."""
    path = definition['assistant_mcp']
    raw = Path(path).read_bytes()
    try:
        config = json.loads(raw)
    except ValueError:
        raise Refused('invalid_input:memory:assistant_mcp', path) from None
    servers = config.get('mcpServers') if isinstance(config, dict) else None
    if not isinstance(servers, dict):
        raise Refused('invalid_input:memory:assistant_mcp', path)
    wanted = assistant_entries(python, factory, root)
    changed = [server for server, part in BRIDGED.items() if not bridges(servers.get(server), part)]
    if not changed:
        event = dict(point='assistant_mcp', path=path, outcome='already_done', servers=[])
        observe(event)
        return event
    for server in changed:
        check(BRIDGED[server], 'before', served=True)
    kept_dir = Path(root) / 'memory' / 'assistant-mcp'
    kept_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    kept = kept_dir / ('previous-%s.json' % hashlib.sha256(raw).hexdigest()[:16])
    if not kept.exists():
        write_private(str(kept), raw)
    for server in changed:
        servers[server] = dict(servers.get(server) or {}, **wanted[server])
    write_private(path, (json.dumps(config, indent=2) + '\n').encode(), os.stat(path).st_mode & 0o777)
    for server in changed:
        check(BRIDGED[server], 'after', served=True)
    event = dict(point='assistant_mcp', path=path, outcome='done', servers=changed, previous=str(kept))
    observe(event)
    return event


# ---------------------------------------------------------------------------------------------
# The servers step: records, roles, units and the assistant's entries, by the owner's signed commands
# ---------------------------------------------------------------------------------------------

def owner_authenticated(store, packet):
    """The owner's signed command, authenticated as VELDO-0203's owner revisions authenticate theirs."""
    CM = store.CM
    try:
        state = CM.authenticate(store.S, store.conn, packet['envelope'], packet['command'], packet['signature'],
                                store.ids, time.time())
    except CM.MembershipRefused as error:
        raise Refused('missing_authority:owner_command:' + error.code) from None
    principal = packet['envelope']['principal']
    member = CM.AC.membership_entry(state['membership'], principal)
    if (member.get('principal_type') != 'person' or member.get('enrolled_by') != principal
            or not CM.BOOTSTRAP_ROLES <= set(member.get('roles') or [])):
        raise Refused('missing_authority:owner_command:not_factory_owner')
    return principal


def save_catalog(store, definition, python, factory, root, memory_revision, prefix, observe):
    """Each catalog record not yet saved as wanted, by the owner's signed command, through the installed engine's
    catalog writer (the code the store binds its records to); {server: revision}."""
    MC = organ('control_mcp_catalog', store.bin)
    domain, repository = store.ids['domain_uuid'], store.ids['repository_uuid']
    catalog = MC.Catalog(store.S, store.conn, domain=domain, repository=repository, signer=store.principal,
                         sign=store.sign, generation=store.generation, observe=observe)
    passphrase = passphrase_reference(store.conn, domain)
    heads = {}
    for server, _ in SERVERS:
        head = MC.entity(store.conn, MC.head_id(domain, server))
        heads[server] = head['data']['revision'] if head else 0
    current = definitions(definition, python, factory, root, memory_revision, heads, passphrase)
    following = definitions(definition, python, factory, root, memory_revision,
                            {s: r + 1 for s, r in heads.items()}, passphrase)
    revisions, saved = {}, []
    for server, _ in SERVERS:
        held = MC.entity(store.conn, MC.revision_id(domain, server, heads[server])) if heads[server] else None
        if held and {k: held['data'][k] for k in MC.FIELDS} == current[server]:
            revisions[server] = heads[server]
            continue
        command_id = '%s-mcp-%s-%d' % (prefix, server, heads[server] + 1)
        packet = store.packet('save_mcp_server', dict(definition=following[server], base=heads[server]), command_id)
        principal = owner_authenticated(store, packet)
        try:
            result = catalog.save(following[server], principal=principal, base=heads[server], command_id=command_id)
        except MC.Refused as error:
            raise Refused(error.code) from None
        revisions[server] = result['revision']
        saved.append(server)
        observe(dict(point='memory_catalog_revision', server=server, revision=result['revision'],
                     memory_revision=memory_revision))
    return revisions, saved


def save_roles(store, revisions, prefix, observe):
    """A new revision of each assistant role selecting the four servers at `revisions`, and one default team
    revision naming them; nothing when both already do."""
    CG, writer = store.revisions()
    TR = store.TR
    domain, repository = store.ids['domain_uuid'], store.ids['repository_uuid']
    head = store.conn.execute('SELECT data FROM entities WHERE id=?', (TR.HEAD,)).fetchone()
    if head is None:
        raise Refused('missing_evidence:default_team')
    base = json.loads(head[0])['revision']
    team = json.loads(store.conn.execute('SELECT data FROM entities WHERE id=?',
                                         (TR.default_id(base),)).fetchone()[0])['team']
    roles, saved = dict(team['roles']), []
    for role in ROLES:
        if role not in roles:
            raise Refused('missing_evidence:conversation_role:' + role)
        named = roles[role]['capability_configuration']['revision']
        accepted = CG.read(store.conn, domain, repository, role, named)
        wanted = selected(accepted, revisions)
        if accepted['mcp'] == wanted['mcp']:
            continue
        latest = CG.read(store.conn, domain, repository, role)['revision']
        answer = writer.apply(store.packet('save_capability_configuration', dict(definition=wanted, base=latest),
                                           '%s-memory-%s-%d' % (prefix, role, latest + 1)))
        if not answer.get('ok'):
            raise Refused(answer.get('reason') or 'unknown_outcome:memory_roles')
        roles[role] = dict(roles[role], capability_configuration={'role': role, 'revision': answer['result']['revision']})
        saved.append('configuration:%s:%d' % (role, answer['result']['revision']))
        observe(dict(point='memory_role_revision', role=role, revision=answer['result']['revision'],
                     servers=[s for s, _ in SERVERS]))
    if saved:
        answer = writer.apply(store.packet('save_default_team', dict(team=dict(team, roles=roles), base=base),
                                           '%s-memory-team-%d' % (prefix, base + 1)))
        if not answer.get('ok'):
            raise Refused(answer.get('reason') or 'unknown_outcome:memory_roles')
        saved.append('default_team:%d' % answer['result']['revision'])
    return saved


def setup_servers(root, owner_key, *, runner=None, unit_dir=None, install_root=None, python=None, factory=None,
                  host=None, observe=None):
    """The servers step: catalog records and role selections under the store's lock, written by the installed
    engine's writers (as setup's store steps write), then the store servers' units, then the assistant's entries.
    `factory` is the engine directory the bridge and store servers run from (this module's own). Returns its
    report; refused by name."""
    root = os.path.realpath(str(root))
    factory = str(Path(factory or Path(__file__).parent).resolve())
    python = python or sys.executable
    events = []

    def note(event):
        events.append(event)
        if observe:
            observe(event)

    F = organ('control_factory_setup', factory)
    CS = organ('control_service', factory)
    D = organ('control_factory_setup_dispatch', factory)
    ACT = organ('control_channel_activation', factory)
    CHECK = organ('control_memory_check', factory)
    runner = runner or CS.Systemctl()
    unit_dir = str(unit_dir or CS.default_unit_dir())
    laid = json.loads((Path(root) / 'host' / 'ingress.json').read_text())
    CC, CE = organ('control_client', factory), organ('control_enrollment', factory)
    installed = os.path.join(str(install_root or CS.default_install_root()),
                             CC.service_id(CE.read_binding(laid['workspace'])), 'bin')
    if not os.path.isfile(os.path.join(installed, 'control_mcp_catalog.py')):
        raise Refused('missing_evidence:memory_servers:installation', installed)
    lock = F.take_lock(root)
    if lock is None:
        raise Refused('invalid_input:state_root:service_running:memory_servers')
    store = None
    try:
        reader = F.organ('control_claim').S.open_store(os.path.join(root, 'authority', 'control.sqlite3'), mode='r')
        try:
            record = M.read(reader)
            if record is None:
                raise Refused('missing_evidence:memory:record')
            handed = M.handoff(reader, host or socket.gethostname())
        finally:
            reader.close()
        definition, memory_revision = handed['definition'], handed['revision']
        owner = record['owner']
        store = D.Store(installed, str(Path(root) / 'host' / 'ingress.json'), owner, ACT.ssh_signer(owner_key), lock)
        prefix = 'memory-servers-%s' % uuid.uuid4().hex[:8]
        revisions, catalog_saved = save_catalog(store, definition, python, factory, root, memory_revision, prefix, note)
        roles_saved = save_roles(store, revisions, prefix, note)
    finally:
        if store is not None:
            store.close()
        os.close(lock)

    def check(part, phase, served):
        result = CHECK.check(root, definition, part, phase, Served(root) if served else None)
        note(dict(point='memory_check', served=served, **{k: v for k, v in result.items()
                                                          if k in ('part', 'phase', 'outcome', 'count', 'sample_size',
                                                                   'copy')}))

    stores = start_stores(definition, root, python, factory, runner, unit_dir, check, note)
    assistant = rewrite_assistant(definition, root, python, factory, check, note)
    return dict(step='memory_servers', outcome='done' if catalog_saved or roles_saved or assistant['outcome'] == 'done'
                or any(s['outcome'] == 'started' for s in stores) else 'already_done',
                memory_revision=memory_revision, catalog=revisions, catalog_saved=catalog_saved, roles=roles_saved,
                stores=stores, assistant_mcp=assistant, events=events, workspace=laid.get('workspace'))


# ---------------------------------------------------------------------------------------------
# The bridge and the store's clients (AC4)
# ---------------------------------------------------------------------------------------------

class Client:
    """One connection to a part's store server."""

    def __init__(self, root, part, timeout=900):
        self.part = part
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        try:
            self.sock.connect(socket_path(root, part))
        except OSError:
            self.sock.close()
            raise Refused('unavailable_service:memory_store:' + part) from None
        self.stream = self.sock.makefile('rwb')

    def request(self, value):
        try:
            self.stream.write((json.dumps(value) + '\n').encode())
            self.stream.flush()
            line = self.stream.readline()
        except OSError:
            line = b''
        if not line:
            raise Refused('unavailable_service:memory_store:' + self.part)
        answer = json.loads(line)
        if 'error' in answer:
            raise Refused(answer['error'], answer.get('cause') or '')
        return answer

    def list(self):
        return self.request(dict(op='list'))['tools']

    def call(self, name, arguments, about=None, credentials=None):
        return self.request(dict(op='call', name=name, arguments=arguments, about=about or {},
                                 credentials=credentials or {}))

    def close(self):
        with contextlib.suppress(OSError):
            self.stream.close()
            self.sock.close()


class Served:
    """VELDO-0182's check's reads of a store its store server holds open, made by that server (AC4): the probe is
    the adapter's reader run inside it, the copy taken by it. A refusal comes back as the reason the check could
    not run, so the check refuses by name as when its own reader fails."""

    def __init__(self, root):
        self.root = root

    def ask(self, part, request):
        client = None
        try:
            client = Client(self.root, part)
            return client.request(request)
        except Refused as error:
            raise ValueError('adapter unavailable', ':'.join(filter(None, (error.code, error.detail)))) from None
        finally:
            if client is not None:
                client.close()

    def probe(self, part, entry, operation, sample=None, scratch=None):
        answer = self.ask(part, dict(op='check', operation=operation, sample=sample or []))
        return {k: answer[k] for k in ('count', 'sample', 'found') if k in answer}

    def copy(self, source, target, part):
        self.ask(part, dict(op='copy', target=str(target)))


def bridge(root, part, server, catalog_revision=None, memory_revision=None, stdin=None, stdout=None):
    """`veldo memory bridge <part>`: an MCP stdio server listing the part's store server's tools and forwarding
    each call to it. A credential the run was handed for this server (memory_kb's passphrase) goes with each call
    as its environment, never as tool input."""
    stdin, stdout = stdin or sys.stdin, stdout or sys.stdout
    client = []
    credentials = {k: os.environ[k] for k in (PASSPHRASE,) if part == 'memory_kb' and k in os.environ}
    about = dict(server=server, catalog_revision=catalog_revision, memory_revision=memory_revision,
                 run=os.environ.get('VELDO_DISPATCH_ID'))

    def store():
        if not client:
            client.append(Client(root, part))
        return client[0]

    for line in stdin:
        try:
            message = json.loads(line)
        except ValueError:
            continue
        if not isinstance(message, dict) or 'id' not in message:
            continue
        method, params = message.get('method'), message.get('params') or {}
        answer = dict(jsonrpc='2.0', id=message['id'])
        try:
            if method == 'initialize':
                answer['result'] = dict(protocolVersion=params.get('protocolVersion') or '2024-11-05',
                                        capabilities=dict(tools={}), serverInfo=dict(name=server, version='veldo'))
            elif method == 'tools/list':
                answer['result'] = dict(tools=store().list())
            elif method == 'tools/call':
                answer['result'] = store().call(params.get('name'), params.get('arguments') or {}, about, credentials)
            elif method == 'ping':
                answer['result'] = {}
            else:
                answer['error'] = dict(code=-32601, message='method not found')
        except Refused as error:
            answer['error'] = dict(code=-32000, message=error.code)
        stdout.write(json.dumps(answer) + '\n')
        stdout.flush()
    for c in client:
        c.close()
    return 0


def kb(root, subcommand, arguments):
    """`veldo memory kb <subcommand>`: memory_kb's command line, through its store server."""
    client = Client(root, 'memory_kb')
    try:
        answer = client.call(subcommand, arguments, dict(server='veldo memory kb'),
                             {k: os.environ[k] for k in (PASSPHRASE,) if k in os.environ})
    finally:
        client.close()
    return answer


# ---------------------------------------------------------------------------------------------
# Smart add on the subscription (AC2)
# ---------------------------------------------------------------------------------------------

def extract(root, text, host=None, clock=time.time):
    """The facts of `text`, extracted by Claude Code on a subscription account the account pool chooses, run in that
    account's profile with no paid-API name in its environment, and recorded as a run on that account."""
    root = Path(root)
    host = host or socket.gethostname()
    POOL, ACC = organ('control_account_pool'), organ('control_accounts')
    MC = organ('control_mcp_catalog')
    engines = json.loads((root / 'host' / 'engines.json').read_text())
    claude = (engines.get('claude_code') or {}).get('path')
    if not claude:
        raise Refused('missing_evidence:memory_extract:engine')
    conn = sqlite3.connect('file:%s?mode=ro' % (root / 'authority' / 'control.sqlite3'), uri=True, timeout=30)
    try:
        choice = POOL.choose(conn, {}, {'engine': 'claude_code', 'host': host}, clock(), lambda account: None)
        if not choice['account']:
            raise Refused(POOL.refusal(choice))
        record = ACC.read(conn, choice['account'])
    finally:
        conn.close()
    profile = (record.get('profiles') or {}).get(host)
    paid = MC.paid_api_names()
    environment = {k: os.environ[k] for k in ('PATH', 'HOME', 'LANG', 'LC_ALL', 'TZ') if k in os.environ}
    if not profile:
        raise Refused('missing_evidence:memory_extract:profile', choice['account'])
    environment[ACC.PROFILES['claude_code']] = profile
    run = 'memory-extract-' + uuid.uuid4().hex
    started = clock()
    done = subprocess.run([claude, '-p', EXTRACT_PROMPT, '--output-format', 'json', '--max-turns', '1'],
                          input=text, capture_output=True, text=True, timeout=600, env=environment)
    facts, outcome = None, 'failed'
    try:
        answer = json.loads(done.stdout)
        body = answer.get('result') or ''
        facts = json.loads(body[body.index('{'):body.rindex('}') + 1])['facts']
        if done.returncode == 0 and isinstance(facts, list) and all(isinstance(f, str) and f for f in facts):
            outcome = 'done'
    except (ValueError, KeyError, TypeError, AttributeError):
        pass
    directory = root / 'memory' / EXTRACTIONS
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    receipt = dict(schema='veldo.memory_extraction/v1', run=run, engine='claude_code', account=choice['account'],
                   host=host, started_at=started, ended_at=clock(), outcome=outcome, exit=done.returncode,
                   facts=len(facts) if outcome == 'done' else 0, selection=choice.get('trace'),
                   paid_api_names_handed=sorted(set(environment) & paid - {ACC.PROFILES['claude_code']}))
    write_private(str(directory / (run + '.json')), json.dumps(receipt, sort_keys=True).encode())
    if outcome != 'done':
        raise Refused('unavailable_service:memory_extract', run)
    return dict(facts=facts, run=dict(run=run, account=choice['account'], engine='claude_code'))


# ---------------------------------------------------------------------------------------------
# Metrics from a run's execution record (observability)
# ---------------------------------------------------------------------------------------------

def metrics(record_lines, catalog_observations=()):
    """Memory tool calls per server and tool, catalog saves refused for a paid-API name, and whether the run's
    memory servers failed to connect, from one run's execution record lines (VELDO-0141)."""
    names = {server for server, _ in SERVERS}
    calls, failed = {}, False
    for line in record_lines:
        try:
            event = json.loads(line.get('payload') or '')
        except (ValueError, AttributeError):
            continue
        if not isinstance(event, dict):
            continue
        if event.get('subtype') == 'init':
            failed = failed or any(s.get('status') != 'connected' for s in event.get('mcp_servers') or []
                                   if isinstance(s, dict) and s.get('name') in names)
        for block in ((event.get('message') or {}).get('content') or []) if event.get('type') == 'assistant' else []:
            if isinstance(block, dict) and block.get('type') == 'tool_use':
                parts = str(block.get('name')).split('__')
                if len(parts) == 3 and parts[0] == 'mcp' and parts[1] in names:
                    key = '%s/%s' % (parts[1], parts[2])
                    calls[key] = calls.get(key, 0) + 1
    refused = sum(1 for o in catalog_observations if str(o.get('refusal') or '').startswith('invalid_input:mcp_server:paid_api:'))
    return dict(memory_tool_calls=calls, catalog_paid_api_refused=refused, memory_servers_failed=int(failed))
