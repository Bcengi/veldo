"""Versioned MCP definitions on the authority store (VELDO-0144).

A definition is data, never executed here. Each save creates an immutable mcp_server
and advances its head. Credentials are keychain references; delivery belongs to 0158.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import time
from urllib.parse import parse_qsl, urlsplit


def organ(name):
    spec = importlib.util.spec_from_file_location('mcp_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AC = organ('authority_contract')
CM = organ('control_membership')
SS = organ('secret_scan')
KIND, HEAD_KIND, SAVE = 'mcp_server', 'mcp_server_head', 'save_mcp_server'
FIELDS = ('id', 'label', 'transport', 'command', 'arguments', 'url', 'environment', 'headers', 'hosts', 'read_only_tools')
WRITES = ('entities', 'journal', 'commands', 'nonces')


class Refused(Exception):
    def __init__(self, code, field=None):
        self.code, self.field = code, field
        super().__init__(code)


def identifier(value):
    return isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', value) is not None


def text(value):
    return isinstance(value, str) and bool(value) and len(value) <= 4096 and value.isprintable()


def reference(value):
    return isinstance(value, str) and re.fullmatch(r'keychain:[A-Za-z0-9_][A-Za-z0-9_./-]*', value) is not None


def entity(conn, identity):
    row = conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (identity,)).fetchone()
    return {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])} if row else None


def head_id(domain, server):
    return 'mcp-head:' + hashlib.sha256((domain + '/' + server).encode()).hexdigest()


def revision_id(domain, server, revision):
    return head_id(domain, server).replace('mcp-head:', 'mcp-server:') + ':' + str(revision)


def owner(conn, principal, repository, now):
    row = entity(conn, principal) if isinstance(principal, str) else None
    member = dict(row['data'], principal=principal) if row and row['kind'] == 'membership' else {}
    if (not AC.active_member(member, now)[0] or member.get('principal_type') != 'person'
            or 'project_owner' not in (member.get('roles') or [])
            or not CM.scope_covers(member.get('scope'), repository)):
        raise Refused('unauthorized:mcp_owner')


def credential_literal(value):
    """Catch authorization values and known shapes, without an entropy heuristic."""
    if isinstance(value, dict):
        return any(credential_literal(k) or credential_literal(v) for k, v in value.items())
    if isinstance(value, list):
        return any(credential_literal(v) for v in value)
    if isinstance(value, str) and re.fullmatch(r'(?:Bearer \S{16,}|Basic [A-Za-z0-9+/=]{8,})', value, re.IGNORECASE):
        return True
    return isinstance(value, str) and any(rx.search(value) for rx, _ in SS.PATTERNS)


def credential_position(d):
    """Guard named credential positions. Ordinary literals are the trusted owner's choice."""
    def named(name, query=False):
        query_name = name.lower()
        name = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
        name = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name)
        tokens = [part for part in re.split(r'[_\-.]+', name.lower()) if part]
        if not tokens or tokens[-1] in ('file', 'path', 'dir', 'name', 'port', 'url', 'host', 'id', 'callback'):
            return False
        return (any(part in ('token', 'secret', 'password', 'passwd', 'pwd', 'pass', 'apikey',
                             'credential', 'credentials', 'auth', 'bearer', 'cookie',
                             'authorization', 'authtoken', 'accesstoken', 'passphrase', 'privatekey') for part in tokens)
                or tokens[-1] in ('key', 'pat')
                or (query and query_name in ('sig', 'signature', 'code')))

    def positioned(name, value, query=False):
        return named(name, query) and not value.startswith(('/', '~/'))

    if any('literal' in item and positioned(name, item['literal']) for name, item in d['environment'].items()):
        return 'environment'
    if any('literal' in item for item in d['headers'].values()):
        return 'headers'
    if d['transport'] == 'stdio':
        for index, argument in enumerate(d['arguments']):
            if argument.startswith('-' * 2):
                name, equals, value = argument[2:].partition('=')
                if not equals:
                    if index + 1 == len(d['arguments']):
                        continue
                    value = d['arguments'][index + 1]
                    if value.startswith('-' * 2) or re.fullmatch(r'-[^-](?:=.*)?', value):
                        continue
                if positioned(name, value):
                    return 'arguments'
    if d['transport'] == 'http' and isinstance(d['url'], str):
        try:
            url = urlsplit(d['url'])
            if url.username is not None or url.password is not None:
                return 'url'
            if any(positioned(name, value, query=True) for name, value in parse_qsl(url.query, keep_blank_values=True)):
                return 'url'
        except ValueError:
            pass  # Transport validation gives malformed URLs their named refusal.
    return None


def validate(definition):
    if not isinstance(definition, dict) or set(definition) != set(FIELDS):
        raise Refused('invalid_input:server_definition')
    d = definition
    if credential_literal(d):
        raise Refused('invalid_input:server_credential_literal',
                      next(field for field in FIELDS if credential_literal(d[field])))
    valid = identifier(d['id']) and text(d['label']) and d['transport'] in ('stdio', 'http')
    for field in ('arguments', 'hosts', 'read_only_tools'):
        items = d[field]
        valid = valid and isinstance(items, list) and all(text(v) for v in items)
    valid = valid and bool(d['hosts'])
    for field in ('environment', 'headers'):
        values = d[field]
        valid = valid and isinstance(values, dict) and all(identifier(k) for k in values)
        if isinstance(values, dict):
            for value in values.values():
                # Explicit tags distinguish a literal from a reference, without guessing its shape.
                allowed = ('literal', 'reference')
                valid = valid and isinstance(value, dict) and len(value) == 1 and next(iter(value)) in allowed
                if isinstance(value, dict) and len(value) == 1:
                    kind, item = next(iter(value.items()))
                    valid = valid and (reference(item) if kind == 'reference' else isinstance(item, str))
    if not valid:
        raise Refused('invalid_input:server_definition')
    field = credential_position(d)
    if field:
        raise Refused('invalid_input:server_credential_position', field)
    if d['transport'] == 'stdio':
        valid = text(d['command']) and d['url'] is None and not d['headers']
    else:
        try:
            url = urlsplit(d['url']) if isinstance(d['url'], str) else None
            valid = (url is not None and url.scheme in ('http', 'https') and bool(url.hostname)
                     and not url.fragment
                     and d['command'] is None and d['arguments'] == [])
        except ValueError:
            valid = False
    if not valid:
        raise Refused('invalid_input:server_transport')


def transition(conn, params, before):
    owner(conn, params['principal'], params['repository'], time.time())
    validate(params['definition'])
    d, domain, base = params['definition'], params['domain'], params['base']
    for field in ('environment', 'headers'):
        for item in d[field].values():
            ref = item.get('reference')
            if ref is None:
                continue
            recorded = False
            for row in conn.execute("SELECT id, data FROM entities WHERE kind='credential'"):
                credential = json.loads(row[1])
                digest = hashlib.sha256((domain + '/' + credential['id']).encode()).hexdigest()
                if (not credential.get('deleted') and row[0] == 'credential:' + digest
                        and credential.get('reference') == ref == 'keychain:veldo/' + digest):
                    recorded = True
            if not recorded:
                raise Refused('invalid_input:server_credential_reference', field)
    hid = head_id(domain, d['id'])
    head = entity(conn, hid)
    current = head['data']['revision'] if head else 0
    if base != current:
        raise Refused('stale_version:mcp_server')
    revision = current + 1
    rid = revision_id(domain, d['id'], revision)
    if entity(conn, rid) is not None:
        raise Refused('stale_version:immutable_mcp_server')
    return {rid: {'kind': KIND, 'data': dict(d, revision=revision)},
            hid: {'kind': HEAD_KIND, 'data': {'id': d['id'], 'revision': revision}}}


class Catalog:
    def __init__(self, store, conn, *, domain, repository, signer, sign, generation=1, observe=None):
        self.S, self.conn, self.domain, self.repository = store, conn, domain, repository
        self.signer, self.sign, self.generation = signer, sign, generation
        self.observe = observe or (lambda event: None)
        self.observations = []
        store.declare_owners(conn, 'mcp_catalog', kinds={KIND: (SAVE,), HEAD_KIND: (SAVE,)}, module=__file__)
        conn.command_registry[SAVE] = {'transaction_transition': transition, 'writes': WRITES}

    def save(self, definition, *, principal, base, command_id, session=None):
        about = dict(operation=SAVE, actor=principal, command_id=command_id, session=session,
                     server=definition.get('id') if isinstance(definition, dict) else None)
        try:
            validate(definition)
            if type(base) is not int or base < 0 or not text(command_id):
                raise Refused('invalid_input:catalog_save')
            hid = head_id(self.domain, definition['id'])
            rid = revision_id(self.domain, definition['id'], base + 1)
            expected = {hid: base, rid: 0}
            params = dict(definition=definition, base=base, domain=self.domain, repository=self.repository,
                          principal=principal, session=session)
            command = dict(command_id=command_id, principal=principal, operation=SAVE, parameters=params,
                           expected_versions=expected, artifact_digests=[], nonce=command_id)
            saved = self.S.execute(self.conn, command, self.signer, self.sign, self.generation)
        except (Refused, self.S.StoreRefused) as error:
            self.record(dict(about, server=None, field=getattr(error, 'field', None),
                             outcome='refused', refusal=error.code))
            raise Refused(error.code) from None
        self.record(dict(about, outcome='saved', revision=base + 1, seq=saved['seq']))
        return dict(outcome='saved', server=definition['id'], revision=base + 1, seq=saved['seq'])

    def record(self, event):
        self.observations.append(event)
        self.observe(event)

    def metrics(self):
        refused = {}
        for row in self.observations:
            if row.get('refusal'):
                refused[row['refusal']] = refused.get(row['refusal'], 0) + 1
        return {'revisions': sum(r['outcome'] == 'saved' for r in self.observations), 'refused': refused}
